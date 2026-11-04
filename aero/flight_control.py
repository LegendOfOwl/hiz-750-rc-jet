"""
HIZ-750 - ucus kontrol (FC) on tasarimi: dogrusal modeller, kontrol yasalari, kararlilik paylari,
zaman simulasyonlari ve kazanc programi (gain schedule).

Calistir:  C:/Users/Urungu/.hz750/Scripts/python aero/flight_control.py
Ciktilar:  aero/out/fc_*.png, fc_sonuclar.json, fc_ozet.txt, fc_kazanc_tablosu.csv

Yontem
- Stabilite/kontrol turevleri AeroSandbox AeroBuildup (aero_analysis.py'deki ucak modeli) ile
  her (hiz x yakit) noktasinda trim alfa/elevator etrafinda; Cl_beta'ya DATCOM govde-kanat
  duzeltmesi eklenir (aero_analysis [8] ile ayni).
- Kutle/atalet: cad/out/mass_properties.json varsa ondan (m, CG, Ixx, Iyy, Izz, Ixz), yoksa
  params.mass_summary + Roskam atalet yaricaplari (aero_analysis [5] ile ayni).
- Boylamsal 4 durum [u, alfa, q, theta], yanal 4 durum [beta, p, r, phi] (kararlilik eksenleri).
- Servo: 1. derece (25 Hz), hiz limiti 600 deg/s, yuzey limitleri; kontrolcu 50 Hz ayrik,
  bir ornek (20 ms) hesap gecikmesi + ZOH. Paylar ayrik (z) acik cevrim fonksiyonundan,
  dongu aktuator girisinde kirilarak (diger donguler kapali) hesaplanir.

params.py DEGISTIRILMEZ.
"""
import csv
import json
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.linalg import expm
from scipy.optimize import minimize
from scipy.signal import find_peaks

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import params as P  # noqa: E402
import aero_analysis as AA  # noqa: E402  (ucak modeli, AeroBuildup sarmalayicilari)

OUT = os.path.join(ROOT, "aero", "out")
os.makedirs(OUT, exist_ok=True)
MP_JSON = os.path.join(ROOT, "cad", "out", "mass_properties.json")
G = 9.80665
D2R, R2D = math.pi / 180, 180 / math.pi
LOG = []

# ---------------------------------------------------------------- tasarim sabitleri
ALT = 300.0                          # aero_analysis ile ayni irtifa
SPEEDS_KMH = (350, 550, 750, 800)
FUELS = (1.0, 0.25, 0.0)
T_LOOP = 0.02                        # 50 Hz dongu
SERVO_BW_HZ = 25.0
TAU_S = 1 / (2 * math.pi * SERVO_BW_HZ)
SERVO_RATE = 600 * D2R               # rad/s
LIM_HS = dict(de=1.5, da=2.0, dr=2.0)       # hiz modu yuzey limitleri [deg] (>= 750 km/h)
LIM_LS = dict(de=P.HTAIL["elevator"]["defl_max_ls"], da=P.WING["aileron"]["defl_max_ls"],
              dr=P.VTAIL["rudder"]["defl_max_ls"])
V_HS_REF = 750 / 3.6
N_MAX, N_MIN = 10.0, -6.0            # g-limiter komut doyumu (yapi: +12 / -8 limit)
P_MAX = 300 * D2R                    # roll rate komut siniri
TAU_WO = 1.0                         # yaw damper washout [s]
ZETA_DR_TARGET = 0.30
ZETA_DR_DESIGN = 0.40                # tasarim hedefi (0.30 ustunde pay)
GM_REQ, PM_REQ = 6.0, 45.0
CMAD_RATIO = 0.3                     # Cm_alfadot = 0.3 Cm_q (aero_analysis ile ayni)
GUST_U = 15.0                        # m/s
GUST_L_SHORT = 25 * P.wing_geom()["mac"]   # 1-cos tam boy = 2H, H = 12.5 MAC (CS-23)
GUST_L_LONG = 100.0


def log(s=""):
    print(s)
    LOG.append(s)


def limits(V):
    """Dinamik basincla olceklenen yuzey limiti: >=750 km/h hiz modu, alcak hizda (750/V)^2 ile
    buyur, alcak hiz mekanik limitinde kirpilir. [deg]"""
    k = max(1.0, (V_HS_REF / V) ** 2)
    return {c: min(LIM_HS[c] * k, LIM_LS[c]) for c in LIM_HS}


# ======================================================================
# Kutle ozellikleri
# ======================================================================
def roskam_inertia(m):
    b = P.wing_geom()["b"]
    L = P.FUSELAGE["length"]
    return dict(Ixx=m * (b * 0.25 / 2) ** 2, Iyy=m * (L * 0.38 / 2) ** 2,
                Izz=m * ((b + L) / 2 * 0.52 / 2) ** 2, Ixz=0.0)


def _frac_from_key(k):
    s = str(k).lower().replace("%", "").replace("pct", "").replace("fuel", "").replace("yakit", "").strip("_ ")
    if s in ("full", "tam", "dolu"):
        return 1.0
    if s in ("empty", "bos", "dry"):
        return 0.0
    try:
        v = float(s)
    except ValueError:
        return None
    return v / 100 if v > 1.0 else v


def _parse_case(d):
    g = lambda *ks: next((d[k] for k in ks if k in d), None)
    m = g("m", "mass", "mass_kg")
    cg = g("cg_m", "cg", "CG")
    if isinstance(cg, dict):
        x, z = cg.get("x"), cg.get("z")
    elif cg is not None:
        x, z = cg[0], cg[2]
    else:
        x, z = g("x_cg"), g("z_cg")
    I = d.get("inertia", d)
    Ixx, Iyy, Izz, Ixz = (I.get(k) for k in ("Ixx", "Iyy", "Izz", "Ixz"))
    if None in (m, x, z, Ixx, Iyy, Izz):
        return None
    return dict(m=float(m), x_cg=float(x), z_cg=float(z), Ixx=float(Ixx), Iyy=float(Iyy),
                Izz=float(Izz), Ixz=float(Ixz or 0.0))


def load_mass_props():
    """{fuel_frac: dict(m, x_cg, z_cg, Ixx, Iyy, Izz, Ixz, src)}"""
    res = {}
    src = "Roskam (params.mass_summary + R_x=0.25, R_y=0.38, R_z=0.52; Ixz=0)"
    if os.path.exists(MP_JSON):
        with open(MP_JSON, encoding="utf-8") as fh:
            data = json.load(fh)
        cases = data.get("cases", data)
        parsed = {}
        for k, v in cases.items():
            if not isinstance(v, dict):
                continue
            # yakit orani params yakit kutlesine (FUEL['mass']) gore: CAD '100%' = tank kapasitesi olabilir
            fr = (float(v["fuel_kg"]) / P.FUEL["mass"]) if "fuel_kg" in v else _frac_from_key(k)
            if fr is None:
                continue
            fr = round(fr, 4)
            c = _parse_case(v)
            if c:
                parsed[fr] = c
        if parsed:
            frs = sorted(parsed)
            for ff in FUELS:
                if ff in parsed:
                    c = dict(parsed[ff])
                else:               # dogrusal ara degerleme
                    lo = max([f_ for f_ in frs if f_ <= ff], default=frs[0])
                    hi = min([f_ for f_ in frs if f_ >= ff], default=frs[-1])
                    t = 0 if hi == lo else (ff - lo) / (hi - lo)
                    c = {k: parsed[lo][k] + t * (parsed[hi][k] - parsed[lo][k]) for k in parsed[lo]}
                c["src"] = "CAD (cad/out/mass_properties.json)"
                res[ff] = c
            return res, "CAD (cad/out/mass_properties.json, cases %s)" % ", ".join(
                f"{100*f_:.0f}%" for f_ in frs)
    for ff in FUELS:
        ms = P.mass_summary(ff)
        c = dict(ms)
        c.update(roskam_inertia(ms["m"]))
        c["src"] = "Roskam"
        res[ff] = c
    return res, src


# ======================================================================
# Aerodinamik turevler (AeroBuildup)
# ======================================================================
def dclb_datcom():
    b = P.wing_geom()["b"]
    return 1.2 * math.sqrt(P.WING["AR"]) * (-P.WING["z_root"] / b) * (2 * P.FUSELAGE["d_max"] / b)


def aero_point(V, ms):
    """Trim + stabilite/kontrol turevleri (AeroBuildup)."""
    ref = [ms["x_cg"], 0, ms["z_cg"]]
    Sref = P.WING["S"]
    rho = AA.f(AA.asb.Atmosphere(altitude=ALT).density())
    qb = 0.5 * rho * V ** 2
    CLreq = ms["m"] * G / (qb * Sref)

    def coeffs(alpha, de=0.0, da=0.0, dr=0.0):
        ap = AA.airplane(defl={"elevator": de, "aileron": da, "rudder": dr}, xyz_ref=ref)
        r = AA.ab(ap, AA.opp(V, alt=ALT, alpha=alpha))
        return {k: AA.f(r[k]) for k in ("CL", "CD", "CY", "Cl", "Cm", "Cn")}

    a, de = 0.5, 0.0
    for _ in range(4):
        c0 = coeffs(a, de)
        ca = coeffs(a + 1.0, de)
        cd = coeffs(a, de + 1.0)
        J = np.array([[ca["CL"] - c0["CL"], cd["CL"] - c0["CL"]], [ca["Cm"] - c0["Cm"], cd["Cm"] - c0["Cm"]]])
        da_, dde = np.linalg.solve(J, [CLreq - c0["CL"], -c0["Cm"]])
        a, de = a + da_, de + dde
    c0 = coeffs(a, de)
    ap = AA.airplane(defl={"elevator": de}, xyz_ref=ref)
    dd = AA.ab(ap, AA.opp(V, alt=ALT, alpha=a), deriv=True)
    d = {k: AA.f(dd[k]) for k in ("CLa", "CDa", "Cma", "CLq", "Cmq", "CYb", "Clb", "Cnb",
                                   "CYp", "Clp", "Cnp", "CYr", "Clr", "Cnr")}
    d["Clb_ab"] = d["Clb"]
    d["Clb"] = d["Clb"] + dclb_datcom()
    # kontrol turevleri (sonlu fark, /rad)
    ep, em = coeffs(a, de + 1.0), coeffs(a, de - 1.0)
    for k in ("CL", "CD", "Cm"):
        d[k + "de"] = (ep[k] - em[k]) / (2 * D2R)
    ca_ = coeffs(a, de, da=1.0)
    cr_ = coeffs(a, de, dr=1.0)
    sa = math.copysign(1.0, ca_["Cl"] - c0["Cl"])     # isaret: da>0 -> +Cl (saga yatis)
    sr = math.copysign(1.0, cr_["Cn"] - c0["Cn"])     # isaret: dr>0 -> +Cn (burun saga)
    for k in ("CY", "Cl", "Cn"):
        d[k + "da"] = sa * (ca_[k] - c0[k]) / D2R
        d[k + "dr"] = sr * (cr_[k] - c0[k]) / D2R
    d.update(CL0=c0["CL"], CD0=c0["CD"], Cmad=CMAD_RATIO * d["Cmq"])
    return dict(V=V, rho=rho, qbar=qb, alpha=a, de_trim=de, CLreq=CLreq, der=d,
                asb_sign_aileron=sa, asb_sign_rudder=sr)


# ======================================================================
# Durum-uzay modelleri
# ======================================================================
def long_plant(pt, ms):
    """x=[u, alfa, q, theta]; u=[de]; w=[w_gust (m/s, yukari +)];
    y=[dn (g), q, alfa, u, theta]."""
    V, qb, d = pt["V"], pt["qbar"], pt["der"]
    S, c = P.WING["S"], P.wing_geom()["mac"]
    m, Iy = ms["m"], ms["Iyy"]
    kL = qb * S
    hc = c / (2 * V)
    Lx = kL * np.array([2 * d["CL0"] / V, d["CLa"], d["CLq"] * hc, 0.0])
    Lu, Lw = kL * d["CLde"], kL * d["CLa"] / V
    Dx = kL * np.array([2 * d["CD0"] / V, d["CDa"], 0.0, 0.0])
    Du, Dw = kL * d["CDde"], kL * d["CDa"] / V
    Mx = kL * c * np.array([0.0, d["Cma"], d["Cmq"] * hc, 0.0])
    Mu, Mw = kL * c * d["Cmde"], kL * c * d["Cma"] / V
    Mad = kL * c * d["Cmad"] * hc
    adx = np.array([0.0, 0.0, 1.0, 0.0]) - Lx / (m * V)
    adu, adw = -Lu / (m * V), -Lw / (m * V)
    A = np.zeros((4, 4)); B = np.zeros((4, 1)); Bw = np.zeros((4, 1))
    A[0] = -Dx / m + G * np.array([0, 1, 0, -1]); B[0, 0] = -Du / m; Bw[0, 0] = -Dw / m
    A[1] = adx; B[1, 0] = adu; Bw[1, 0] = adw
    A[2] = (Mx + Mad * adx) / Iy; B[2, 0] = (Mu + Mad * adu) / Iy; Bw[2, 0] = (Mw + Mad * adw) / Iy
    A[3, 2] = 1.0
    C = np.zeros((5, 4)); D = np.zeros((5, 1)); Dwm = np.zeros((5, 1))
    C[0] = Lx / (m * G); D[0, 0] = Lu / (m * G); Dwm[0, 0] = Lw / (m * G)
    C[1, 2] = C[2, 1] = C[3, 0] = C[4, 3] = 1.0
    return dict(A=A, B=B, Bw=Bw, C=C, D=D, Dw=Dwm, y=["dn", "q", "alpha", "u", "theta"],
                u=["de"], meas=[0, 1])


def stab_inertia(ms, alpha):
    a = alpha * D2R
    Ix, Iz, Ixz = ms["Ixx"], ms["Izz"], ms["Ixz"]
    c2, s2 = math.cos(a) ** 2, math.sin(a) ** 2
    Ixs = Ix * c2 + Iz * s2 - Ixz * math.sin(2 * a)
    Izs = Ix * s2 + Iz * c2 + Ixz * math.sin(2 * a)
    Ixzs = 0.5 * (Ix - Iz) * math.sin(2 * a) + Ixz * math.cos(2 * a)
    return Ixs, Izs, Ixzs


def lat_plant(pt, ms):
    """x=[beta, p, r, phi]; u=[da, dr]; y=[p, r, beta, phi, ny (g)]."""
    V, qb, d = pt["V"], pt["qbar"], pt["der"]
    S, b = P.WING["S"], P.wing_geom()["b"]
    m = ms["m"]
    hb = b / (2 * V)
    kY, kM = qb * S, qb * S * b
    Yx = kY * np.array([d["CYb"], d["CYp"] * hb, d["CYr"] * hb, 0.0])
    Yu = kY * np.array([d["CYda"], d["CYdr"]])
    Lx = kM * np.array([d["Clb"], d["Clp"] * hb, d["Clr"] * hb, 0.0])
    Lu = kM * np.array([d["Clda"], d["Cldr"]])
    Nx = kM * np.array([d["Cnb"], d["Cnp"] * hb, d["Cnr"] * hb, 0.0])
    Nu = kM * np.array([d["Cnda"], d["Cndr"]])
    Ix, Iz, Ixz = stab_inertia(ms, pt["alpha"])
    Mi = np.linalg.inv(np.array([[Ix, -Ixz], [-Ixz, Iz]]))
    PN = Mi @ np.vstack([Lx, Nx]); PNu = Mi @ np.vstack([Lu, Nu])
    A = np.zeros((4, 4)); B = np.zeros((4, 2))
    A[0] = Yx / (m * V) + np.array([0, 0, -1, G / V]); B[0] = Yu / (m * V)
    A[1:3] = PN; B[1:3] = PNu
    A[3, 1] = 1.0
    C = np.zeros((5, 4)); D = np.zeros((5, 2))
    C[0, 1] = C[1, 2] = C[2, 0] = C[3, 3] = 1.0
    C[4] = Yx / (m * G); D[4] = Yu / (m * G)
    return dict(A=A, B=B, Bw=np.zeros((4, 1)), C=C, D=D, Dw=np.zeros((5, 1)),
                y=["p", "r", "beta", "phi", "ny"], u=["da", "dr"], meas=[0, 1])


def modes_long(A):
    ev = np.linalg.eigvals(A)
    cp = sorted([e for e in ev if e.imag > 1e-6], key=lambda e: -abs(e))
    out = {}
    for name, e in zip(("sp", "ph"), cp):
        out[name] = dict(wn=abs(e), zeta=-e.real / abs(e))
    if "ph" not in out:    # fugoid iki gercel kok olabilir
        out["ph"] = dict(wn=float("nan"), zeta=float("nan"))
    return out


def modes_lat(A):
    ev = np.linalg.eigvals(A)
    cp = [e for e in ev if e.imag > 1e-6]
    re = sorted([e.real for e in ev if abs(e.imag) <= 1e-6])
    dr = cp[0] if cp else complex(np.nan, np.nan)
    spir = re[-1] if re else float("nan")
    return dict(dr=dict(wn=abs(dr), zeta=-dr.real / abs(dr)),
                roll_tau=-1 / re[0] if re else float("nan"),
                spiral_eig=spir, spiral_t2=math.log(2) / abs(spir) if spir else float("inf"))


# ======================================================================
# Ayrik zaman: tesis + servo + gecikme + kontrolcu
# ======================================================================
def c2d(A, B, T):
    n, m = B.shape
    M = np.zeros((n + m, n + m))
    M[:n, :n] = A * T; M[:n, n:] = B * T
    E = expm(M)
    return E[:n, :n], E[:n, n:]


def aug_servo(pl):
    """surekli tesis + 1. derece servo: xa=[x, s]; giris u_c (servo komutu) ve w."""
    A, B, Bw = pl["A"], pl["B"], pl["Bw"]
    n, m = B.shape
    Aa = np.zeros((n + m, n + m)); Aa[:n, :n] = A; Aa[:n, n:] = B; Aa[n:, n:] = -np.eye(m) / TAU_S
    Ba = np.zeros((n + m, m)); Ba[n:] = np.eye(m) / TAU_S
    Bwa = np.zeros((n + m, Bw.shape[1])); Bwa[:n] = Bw
    Ca = np.hstack([pl["C"], pl["D"]])
    return Aa, Ba, Bwa, Ca


class Ctrl:
    """Dogrusal ayrik kontrolcu: xc+ = Ac xc + Bcy y + Bcr r ; v = Cc xc + Dcy y + Dcr r."""

    def __init__(self, Ac, Bcy, Bcr, Cc, Dcy, Dcr, integ=(), names=None):
        self.Ac, self.Bcy, self.Bcr, self.Cc, self.Dcy, self.Dcr = [np.atleast_2d(np.asarray(x, float))
                                                                    for x in (Ac, Bcy, Bcr, Cc, Dcy, Dcr)]
        self.integ = list(integ)
        self.names = names


def pitch_ctrl(kff, knz, ki, kq, tau_f, T=T_LOOP):
    """de = -kff*nf - knz*(nf - dn) - ki*int(nf - dn) + kq*q   [rad, g, rad/s]
    (aerodinamik isaret: de>0 firar kenari asagi = burun asagi)"""
    af = math.exp(-T / tau_f)
    Ac = [[af, 0.0], [T, 1.0]]
    Bcy = [[0.0, 0.0], [-T, 0.0]]
    Bcr = [[1 - af], [0.0]]
    Cc = [[-kff - knz, -ki]]
    Dcy = [[knz, kq]]
    Dcr = [[0.0]]
    return Ctrl(Ac, Bcy, Bcr, Cc, Dcy, Dcr, integ=[1])


def lat_ctrl(kffa, kpa, kia, tau_fa, kr, tau_wo=TAU_WO, T=T_LOOP):
    """da = kffa*pf + kpa*(pf - p) + kia*int(pf - p) ; dr = -kr*(r - LP(r))  (washout)
    isaret: da>0 saga yatis momenti, dr>0 burun saga momenti."""
    af = math.exp(-T / tau_fa)
    aw = math.exp(-T / tau_wo)
    Ac = [[af, 0, 0], [T, 1, 0], [0, 0, aw]]
    Bcy = [[0, 0], [-T, 0], [0, 1 - aw]]
    Bcr = [[1 - af], [0], [0]]
    Cc = [[kffa + kpa, kia, 0], [0, 0, kr]]
    Dcy = [[-kpa, 0], [0, -kr]]
    Dcr = [[0], [0]]
    return Ctrl(Ac, Bcy, Bcr, Cc, Dcy, Dcr, integ=[1])


def closed_loop(pl, ctl, T=T_LOOP, brk=None):
    """Ayrik kapali cevrim. Durumlar z=[xa, dly(m), xc]. brk=i: i. aktuator kanalinda kirilir
    (giris: dly_i'ye enjeksiyon, cikis: kontrolcu ciktisi v_i)."""
    Aa, Ba, Bwa, Ca = aug_servo(pl)
    Ad, Bd = c2d(Aa, np.hstack([Ba, Bwa]), T)
    m = Ba.shape[1]
    Bdu, Bdw = Bd[:, :m], Bd[:, m:]
    Cy = Ca[pl["meas"]]
    na, nc = Ad.shape[0], ctl.Ac.shape[0]
    N = na + m + nc
    Acl = np.zeros((N, N))
    Acl[:na, :na] = Ad; Acl[:na, na:na + m] = Bdu
    Vrow = np.hstack([ctl.Dcy @ Cy, np.zeros((m, m)), ctl.Cc])
    Acl[na:na + m] = Vrow
    Acl[na + m:, :na] = ctl.Bcy @ Cy; Acl[na + m:, na + m:] = ctl.Ac
    Br = np.zeros((N, ctl.Bcr.shape[1])); Br[na:na + m] = ctl.Dcr; Br[na + m:] = ctl.Bcr
    Bw = np.zeros((N, Bdw.shape[1])); Bw[:na] = Bdw
    Cout = np.hstack([Ca, np.zeros((Ca.shape[0], m + nc))])
    if brk is None:
        return dict(A=Acl, Br=Br, Bw=Bw, C=Cout, na=na, m=m)
    Ab = Acl.copy(); Ab[na + brk] = 0.0
    Bin = np.zeros((N, 1)); Bin[na + brk, 0] = 1.0
    Cv = Vrow[brk:brk + 1]
    return dict(A=Ab, B=Bin, C=Cv)


def margins(pl, ctl, brk, T=T_LOOP, nw=1500):
    ol = closed_loop(pl, ctl, T, brk)
    lam, Vm = np.linalg.eig(ol["A"])
    Vi = np.linalg.solve(Vm, ol["B"])
    cv = ol["C"] @ Vm
    w = np.logspace(-2, math.log10(math.pi / T * 0.999), nw)
    z = np.exp(1j * w * T)
    H = (cv[0][None, :] / (z[:, None] - lam[None, :])) @ Vi[:, 0]
    L = -H
    mag = np.abs(L); ph = np.angle(L, deg=True)
    pms, wcs = [], []
    for i in np.where(np.diff(np.sign(mag - 1.0)) != 0)[0]:
        t = (1 - mag[i]) / (mag[i + 1] - mag[i])
        phi = ph[i] + t * (ph[i + 1] - ph[i]) if abs(ph[i + 1] - ph[i]) < 180 else ph[i]
        pms.append(180 - abs(phi)); wcs.append(w[i])
    gms, wps = [], []
    im = L.imag
    for i in np.where(np.diff(np.sign(im)) != 0)[0]:
        if L.real[i] < 0 and L.real[i + 1] < 0:
            t = im[i] / (im[i] - im[i + 1])
            mg = mag[i] + t * (mag[i + 1] - mag[i])
            gms.append(-20 * math.log10(mg)); wps.append(w[i])
    pm = min(pms) if pms else float("inf")
    gm_up = min([g for g in gms if g > 0], default=float("inf"))
    gm_lo = max([g for g in gms if g < 0], default=-float("inf"))
    gm = min(gm_up, -gm_lo)
    return dict(GM=gm, GM_up=gm_up, GM_lo=gm_lo, PM=pm,
                wc=wcs[int(np.argmin(pms))] if pms else float("nan"),
                wp=wps[int(np.argmin(np.abs(gms)))] if gms else float("nan"), w=w, L=L)


def cl_eigs_s(pl, ctl, T=T_LOOP):
    cl = closed_loop(pl, ctl, T)
    z = np.linalg.eigvals(cl["A"])
    # |z|=1 tam: roll integratoru + phi korunum modu (p hatasi integrali = yatis tutma), notr
    stable = bool(np.max(np.abs(z)) < 1.0 + 1e-9)
    zz = z[np.abs(z) > 1e-8]
    return np.log(zz.astype(complex)) / T, stable


def pick_mode(s, wn_ref, lo=0.3, hi=3.0):
    """Referans frekans bandindaki salinimli modlar icinden EN AZ sonumlu olan (muhafazakar)."""
    c = [e for e in s if e.imag > 0.05 * abs(e) and lo * wn_ref < abs(e) < hi * wn_ref]
    if not c:
        return float("nan"), float("nan")
    e = min(c, key=lambda e: -e.real / abs(e))
    return abs(e), -e.real / abs(e)


def step_lin(pl, ctl, ych, nstep, T=T_LOOP, r_amp=1.0):
    cl = closed_loop(pl, ctl, T)
    x = np.zeros(cl["A"].shape[0]); ys = np.zeros(nstep)
    r = np.full(cl["Br"].shape[1], r_amp)
    for k in range(nstep):
        ys[k] = cl["C"][ych] @ x
        x = cl["A"] @ x + cl["Br"] @ r
    return ys


# ======================================================================
# Kontrolcu tasarimi
# ======================================================================
def scale_eff(pl, k):
    """kontrol etkinligi belirsizligi: B ve D (yuzey -> cikis) k ile olceklenir"""
    q = dict(pl)
    q["B"] = pl["B"] * k
    q["D"] = pl["D"] * k
    return q


UNC = (1.0, 0.7, 1.4)          # tasarimda kullanilan etkinlik carpanlari (nominal, -%30, +%40)


def sp_dc(pl):
    """Kisa periyot (alfa, q) yaklasimiyla de -> dn statik kazanc [g/rad] (manevra gradyani)."""
    A, B, C, D = pl["A"][1:3, 1:3], pl["B"][1:3], pl["C"][0, 1:3], pl["D"][0]
    return float((-(C @ np.linalg.solve(A, B)) + D).item())


def design_pitch(pl, V):
    gdc = sp_dc(pl)                        # g/rad (negatif: de>0 -> burun asagi)
    Gn = 1 / abs(gdc)                      # rad/g
    kq_scale = Gn * V / G
    T = T_LOOP
    nst = int(2.0 / T)
    tt = np.arange(nst) * T
    wsp = modes_long(pl["A"])["sp"]["wn"]

    def unpack(x):
        kq = kq_scale * math.exp(x[0]); knz = Gn * math.exp(x[1]); ki = Gn * math.exp(x[2])
        tau_f = 0.04 + 0.5 / (1 + math.exp(-x[3]))
        kff = Gn - kq * G / V              # feedforward: kararli hal elevatoru (q geri beslemesi telafili)
        return kff, knz, ki, kq, tau_f

    def cost(x, detail=False):
        kff, knz, ki, kq, tau_f = unpack(x)
        ctl = pitch_ctrl(kff, knz, ki, kq, tau_f)
        J = 0.0
        for kk in UNC:
            plk = scale_eff(pl, kk)
            s, st = cl_eigs_s(plk, ctl)
            if not st:
                return 1e6
            mg = margins(plk, ctl, 0, nw=400)
            y = step_lin(plk, ctl, 0, nst)
            os_ = max(0.0, y.max() - 1.0)
            J += float(np.sum(tt * np.abs(1.0 - y)) * T) / len(UNC)
            J += 20 * max(0.0, os_ - (0.03 if kk == 1.0 else 0.08)) ** 2 * 100
            J += 5 * max(0.0, GM_REQ + 0.5 - mg["GM"]) ** 2 + 0.05 * max(0.0, PM_REQ + 3 - mg["PM"]) ** 2
            if kk == 1.0:
                _, zsp = pick_mode(s, wsp, 0.3, 3.0)
                if not math.isnan(zsp):
                    J += 0.5 * max(0.0, 0.55 - zsp) ** 2
        return J

    best = None
    for a in np.linspace(-4.5, -0.5, 6):
        for bb in (-6.0, -2.5, -1.0):
            for c in np.linspace(0.0, 3.5, 6):
                for d in (-1.5, 0.0, 1.5):
                    J = cost([a, bb, c, d])
                    if best is None or J < best[0]:
                        best = (J, [a, bb, c, d])
    r = minimize(cost, best[1], method="Nelder-Mead", options=dict(maxiter=500, xatol=1e-3, fatol=1e-5))
    x = r.x if r.fun < best[0] else best[1]
    kff, knz, ki, kq, tau_f = unpack(x)
    return dict(kff=kff, knz=knz, ki=ki, kq=kq, tau_f=tau_f, Gn=Gn)


def design_roll(pl, kr, V):
    A, B = pl["A"], pl["B"]
    Lp, Lda = A[1, 1], B[1, 0]
    kffa = -Lp / Lda                       # rad / (rad/s)
    T = T_LOOP
    nst = int(1.0 / T)
    tt = np.arange(nst) * T

    def unpack(x):
        kpa = kffa * math.exp(x[0]); kia = kffa * math.exp(x[1])
        tau_fa = 0.03 + 0.25 / (1 + math.exp(-x[2]))
        return kpa, kia, tau_fa

    def cost(x):
        kpa, kia, tau_fa = unpack(x)
        ctl = lat_ctrl(kffa, kpa, kia, tau_fa, kr)
        J = 0.0
        for kk in UNC:
            plk = scale_eff(pl, kk)
            _, st = cl_eigs_s(plk, ctl)
            if not st:
                return 1e6
            mg = margins(plk, ctl, 0, nw=400)
            y = step_lin(plk, ctl, 0, nst)
            os_ = max(0.0, y.max() - 1.0)
            J += float(np.sum(tt * np.abs(1.0 - y)) * T) / len(UNC)
            J += 2000 * max(0.0, os_ - (0.05 if kk == 1.0 else 0.10)) ** 2
            J += 5 * max(0.0, GM_REQ + 0.5 - mg["GM"]) ** 2 + 0.05 * max(0.0, PM_REQ + 3 - mg["PM"]) ** 2
        return J

    best = None
    for a in np.linspace(-4, 0.5, 7):
        for bb in np.linspace(-2, 3, 6):
            for c in (-1.5, 0.0, 1.5):
                J = cost([a, bb, c])
                if best is None or J < best[0]:
                    best = (J, [a, bb, c])
    r = minimize(cost, best[1], method="Nelder-Mead", options=dict(maxiter=300, xatol=1e-3, fatol=1e-5))
    x = r.x if r.fun < best[0] else best[1]
    kpa, kia, tau_fa = unpack(x)
    return dict(kffa=kffa, kpa=kpa, kia=kia, tau_fa=tau_fa)


def design_yd(pl, wn_dr, roll):
    """Yaw damper kazanci: zeta_DR >= 0.40 veren en kucuk K; paylar saglanmazsa paylari saglayan
    en yuksek zeta."""
    Ndr = pl["B"][2, 1]
    kscale = 2 * wn_dr / abs(Ndr)          # rad/(rad/s): zeta'yi ~1 artiran mertebe
    ks = kscale * np.logspace(-2.5, 0.5, 60)
    rows = []
    for k in ks:
        ctl = lat_ctrl(roll["kffa"], roll["kpa"], roll["kia"], roll["tau_fa"], k)
        s, st = cl_eigs_s(pl, ctl)
        if not st:
            rows.append((k, float("nan"), 0, 0)); continue
        _, z = pick_mode(s, wn_dr, 0.3, 3.5)
        mg = margins(pl, ctl, 1, nw=500)
        rows.append((k, z, mg["GM"], mg["PM"]))
    ok = [r for r in rows if r[2] >= GM_REQ and r[3] >= PM_REQ and not math.isnan(r[1])]
    hit = [r for r in ok if r[1] >= ZETA_DR_DESIGN]
    if hit:
        return hit[0][0], rows
    if ok:
        return max(ok, key=lambda r: r[1])[0], rows
    return ks[0], rows


# ======================================================================
# Dogrusal olmayan zaman simulasyonu (servo hiz/konum limiti, 50 Hz ayrik FC, 20 ms gecikme)
# ======================================================================
def simulate(pl, ctl, trim_u, lim, t_end, r_fun=None, w_fun=None, pilot_fun=None, ctrl_on=True,
             fail=None, dt=5e-4, T=T_LOOP):
    """trim_u: trim yuzey sapmalari [rad] (mutlak limit icin); lim: [rad] kanal limitleri.
    pilot_fun(t)-> dogrudan yuzey komutu ilavesi [rad]; fail(t)-> kanal maskesi (True=donmus)."""
    A, B, Bw, C, D, Dw = (pl[k] for k in ("A", "B", "Bw", "C", "D", "Dw"))
    n, m = B.shape
    Phi, Gam = c2d(A, np.hstack([B, Bw]), dt)
    Gu, Gw = Gam[:, :m], Gam[:, m:]
    x = np.zeros(n); s = np.zeros(m); uc = np.zeros(m); vprev = np.zeros(m)
    xc = np.zeros(ctl.Ac.shape[0])
    trim_u = np.asarray(trim_u, float); lim = np.asarray(lim, float)
    nT = int(round(T / dt)); N = int(round(t_end / dt))
    rec_t, rec_y, rec_s = [], [], []
    frozen = None
    for k in range(N + 1):
        t = k * dt
        w = np.atleast_1d(w_fun(t)) if w_fun else np.zeros(Bw.shape[1])
        y = C @ x + D @ s + Dw @ w
        if k % nT == 0:
            r = np.atleast_1d(r_fun(t)) if r_fun else np.zeros(ctl.Bcr.shape[1])
            pil = np.atleast_1d(pilot_fun(t)) if pilot_fun else np.zeros(m)
            if ctrl_on:
                ym = y[pl["meas"]]
                v = ctl.Cc @ xc + ctl.Dcy @ ym + ctl.Dcr @ r + pil
                vs = np.clip(trim_u + v, -lim, lim) - trim_u
                xn = ctl.Ac @ xc + ctl.Bcy @ ym + ctl.Bcr @ r
                if np.any(np.abs(vs - v) > 1e-12):
                    for i in ctl.integ:
                        xn[i] = xc[i]                          # anti-windup (kosullu integrasyon)
                xc = xn
                uc = vprev.copy(); vprev = vs
            else:
                uc = np.clip(trim_u + pil, -lim, lim) - trim_u
            if fail is not None:
                msk = np.asarray(fail(t), bool)
                if msk.any():
                    if frozen is None:
                        frozen = s.copy()
                    uc = np.where(msk, frozen, uc)
        ds = np.clip((uc - s) / TAU_S, -SERVO_RATE, SERVO_RATE)
        s = np.clip(trim_u + s + ds * dt, -lim, lim) - trim_u
        if k % 4 == 0:
            rec_t.append(t); rec_y.append(y.copy()); rec_s.append(s + trim_u)
        x = Phi @ x + Gu @ s + Gw @ w
    return np.array(rec_t), np.array(rec_y), np.array(rec_s)


def gust_fun(V, L, U=GUST_U, t0=0.2):
    def w(t):
        xg = V * (t - t0)
        return U / 2 * (1 - math.cos(2 * math.pi * xg / L)) if 0 <= xg <= L else 0.0
    return w


def zeta_from_decay(t, sig, t_start):
    i0 = np.searchsorted(t, t_start)
    x = sig[i0:] - np.mean(sig[-max(5, len(sig) // 10):])
    pk, _ = find_peaks(np.abs(x))
    pk = [p for p in pk if abs(x[p]) > 0.02 * np.max(np.abs(x))]
    pos = [p for p in pk if x[p] > 0]
    if len(pos) < 2:
        return float("nan")
    dlt = math.log(x[pos[0]] / x[pos[1]])
    return dlt / math.sqrt(4 * math.pi ** 2 + dlt ** 2)


# ======================================================================
# Ana akis
# ======================================================================
def fmt_m(v, nd=1):
    return "inf" if v == float("inf") else f"{v:.{nd}f}"


def main():
    mp, mp_src = load_mass_props()
    wg = P.wing_geom()
    log(f"=== {P.NAME} ucus kontrol on tasarimi ===")
    log(f"Kutle/atalet kaynagi: {mp_src}")
    for ff in FUELS:
        c = mp[ff]
        log(f"   yakit %{100*ff:3.0f}: m={c['m']:.2f} kg x_cg={c['x_cg']:.4f} z_cg={c['z_cg']:+.4f} m  "
            f"Ixx={c['Ixx']:.3f} Iyy={c['Iyy']:.3f} Izz={c['Izz']:.3f} Ixz={c['Ixz']:+.4f} kg.m2")
    log(f"Servo: 1. derece {SERVO_BW_HZ:.0f} Hz (tau={1000*TAU_S:.1f} ms), hiz limiti {SERVO_RATE*R2D:.0f} deg/s; "
        f"dongu {1/T_LOOP:.0f} Hz, 1 ornek gecikme ({1000*T_LOOP:.0f} ms) + ZOH")
    log(f"DATCOM govde-kanat dCl_beta = {dclb_datcom():+.4f}/rad (tum noktalara eklendi)")

    pts = {}
    log("\n[1] Trim, turevler ve acik cevrim modlar (AeroBuildup, h=300 m):")
    for Vk in SPEEDS_KMH:
        V = Vk / 3.6
        for ff in FUELS:
            ms = mp[ff]
            pt = aero_point(V, ms)
            plo, pla = long_plant(pt, ms), lat_plant(pt, ms)
            ml, mla = modes_long(plo["A"]), modes_lat(pla["A"])
            pt.update(ms=ms, plo=plo, pla=pla, ml=ml, mla=mla, lim=limits(V))
            pts[(Vk, ff)] = pt
            d = pt["der"]
            log(f"   {Vk} km/h %{100*ff:3.0f}: a={pt['alpha']:+.2f} de={pt['de_trim']:+.2f} deg | "
                f"CLa={d['CLa']:.2f} Cma={d['Cma']:+.3f} Cmq={d['Cmq']:.2f} Cmde={d['Cmde']:+.3f} | "
                f"Cnb={d['Cnb']:+.4f} Clb={d['Clb']:+.4f} Clp={d['Clp']:.3f} Cnr={d['Cnr']:+.4f} "
                f"Clda={d['Clda']:+.4f} Cndr={d['Cndr']:+.4f}")
            log(f"        SP wn={ml['sp']['wn']:.1f} rad/s ({ml['sp']['wn']/2/math.pi:.2f} Hz) z={ml['sp']['zeta']:.2f}; "
                f"fugoid wn={ml['ph']['wn']:.3f} z={ml['ph']['zeta']:.3f}; DR wn={mla['dr']['wn']:.1f} "
                f"({mla['dr']['wn']/2/math.pi:.2f} Hz) z={mla['dr']['zeta']:.3f}; roll tau={1000*mla['roll_tau']:.0f} ms; "
                f"spiral {'kararli' if mla['spiral_eig'] < 0 else 'kararsiz'} T={mla['spiral_t2']:.0f} s; "
                f"manevra gradyani {R2D/abs(sp_dc(plo)):.3f} deg/g")

    # ---------------------------------------------------------- tasarim
    log("\n[2] Kontrolcu tasarimi (her nokta; ayrik 50 Hz, gecikme dahil):")
    for key, pt in pts.items():
        V = pt["V"]
        pc = design_pitch(pt["plo"], V)
        wdr = pt["mla"]["dr"]["wn"]
        roll0 = dict(kffa=-pt["pla"]["A"][1, 1] / pt["pla"]["B"][1, 0], kpa=0.0, kia=0.0, tau_fa=0.05)
        kr, _ = design_yd(pt["pla"], wdr, roll0)
        roll = design_roll(pt["pla"], kr, V)
        kr, sweep = design_yd(pt["pla"], wdr, roll)
        roll = design_roll(pt["pla"], kr, V)
        ctl_p = pitch_ctrl(pc["kff"], pc["knz"], pc["ki"], pc["kq"], pc["tau_f"])
        ctl_l = lat_ctrl(roll["kffa"], roll["kpa"], roll["kia"], roll["tau_fa"], kr)
        mp_ = margins(pt["plo"], ctl_p, 0)
        ma_ = margins(pt["pla"], ctl_l, 0)
        mr_ = margins(pt["pla"], ctl_l, 1)
        s_p, st_p = cl_eigs_s(pt["plo"], ctl_p)
        s_l, st_l = cl_eigs_s(pt["pla"], ctl_l)
        _, z_sp_cl = pick_mode(s_p, pt["ml"]["sp"]["wn"], 0.3, 3.0)
        wdr_cl, z_dr_cl = pick_mode(s_l, wdr, 0.3, 3.5)
        ctl_nod = lat_ctrl(roll["kffa"], roll["kpa"], roll["kia"], roll["tau_fa"], 0.0)
        s_n, _ = cl_eigs_s(pt["pla"], ctl_nod)
        _, z_dr_nod = pick_mode(s_n, wdr, 0.3, 3.5)
        y = step_lin(pt["plo"], ctl_p, 0, 100)
        yp = step_lin(pt["pla"], ctl_l, 0, 50)
        tr = lambda yy: next((i * T_LOOP for i, v in enumerate(yy) if v >= 0.9), float("nan"))
        pt.update(pc=pc, roll=roll, kr=kr, ctl_p=ctl_p, ctl_l=ctl_l, m_pitch=mp_, m_roll=ma_, m_yaw=mr_,
                  stable=st_p and st_l, z_sp_cl=z_sp_cl, z_dr_cl=z_dr_cl, wdr_cl=wdr_cl, z_dr_nod=z_dr_nod,
                  os_n=max(0, y.max() - 1), t90_n=tr(y), os_p=max(0, yp.max() - 1), t90_p=tr(yp), yd_sweep=sweep)
        Vk, ff = key
        log(f"   {Vk} km/h %{100*ff:3.0f}: PITCH Kff={pc['kff']*R2D:.3f} Knz={pc['knz']*R2D:.3f} deg/g "
            f"Ki={pc['ki']*R2D:.3f} deg/(g s) Kq={pc['kq']:.4f} deg/(deg/s) tau_f={pc['tau_f']:.3f} s -> "
            f"GM={fmt_m(mp_['GM'])} dB PM={fmt_m(mp_['PM'])} deg, t90={pt['t90_n']:.2f} s os=%{100*pt['os_n']:.1f}, "
            f"zeta_SP={z_sp_cl:.2f}")
        log(f"        YAW Kr={kr:.4f} deg/(deg/s) -> zeta_DR {pt['mla']['dr']['zeta']:.3f} -> {z_dr_cl:.3f} "
            f"(damper kapali, roll dongusu acik: {z_dr_nod:.3f}); GM={fmt_m(mr_['GM'])} dB PM={fmt_m(mr_['PM'])} deg")
        log(f"        ROLL Kff={roll['kffa']:.4f} Kp={roll['kpa']:.4f} deg/(deg/s) Ki={roll['kia']:.4f} deg/deg "
            f"tau_f={roll['tau_fa']:.3f} s -> GM={fmt_m(ma_['GM'])} dB PM={fmt_m(ma_['PM'])} deg, "
            f"t90={pt['t90_p']:.2f} s os=%{100*pt['os_p']:.1f}; kararli={pt['stable']}")

    # ---------------------------------------------------------- pay tablosu
    log("\n[3] Kararlilik paylari (hedef GM >= 6 dB, PM >= 45 deg; 20 ms gecikme + ZOH + servo dahil):")
    log("   V [km/h] yakit | pitch GM/PM | roll GM/PM | yaw GM/PM | zeta_DR acik->kapali | durum")
    allok = True
    for (Vk, ff), pt in pts.items():
        ok = all(m_["GM"] >= GM_REQ and m_["PM"] >= PM_REQ for m_ in (pt["m_pitch"], pt["m_roll"], pt["m_yaw"]))
        ok = ok and pt["z_dr_cl"] >= ZETA_DR_TARGET and pt["stable"]
        allok &= ok
        pt["ok"] = ok
        log(f"   {Vk:4d} %{100*ff:3.0f} | {fmt_m(pt['m_pitch']['GM'])}/{fmt_m(pt['m_pitch']['PM'],0)} | "
            f"{fmt_m(pt['m_roll']['GM'])}/{fmt_m(pt['m_roll']['PM'],0)} | {fmt_m(pt['m_yaw']['GM'])}/"
            f"{fmt_m(pt['m_yaw']['PM'],0)} | {pt['mla']['dr']['zeta']:.3f}->{pt['z_dr_cl']:.3f} | "
            f"{'OK' if ok else 'HEDEF DISI'}")
    log(f"   Tum zarf hedefleri: {'SAGLANDI' if allok else 'SAGLANMADI (yukariya bak)'}")

    # 200 Hz duyarlilik (ayni kazanclar)
    log("\n   Duyarlilik: ayni kazanclarla dongu 200 Hz (5 ms gecikme) olsaydi (750/800 km/h bos):")
    sens = {}
    for key in ((750, 0.0), (800, 0.0)):
        pt = pts[key]
        pc, ro = pt["pc"], pt["roll"]
        cp2 = pitch_ctrl(pc["kff"], pc["knz"], pc["ki"], pc["kq"], pc["tau_f"], T=0.005)
        cl2 = lat_ctrl(ro["kffa"], ro["kpa"], ro["kia"], ro["tau_fa"], pt["kr"], T=0.005)
        m1, m2, m3 = margins(pt["plo"], cp2, 0, T=0.005), margins(pt["pla"], cl2, 0, T=0.005), \
            margins(pt["pla"], cl2, 1, T=0.005)
        sens[key] = dict(pitch=(m1["GM"], m1["PM"]), roll=(m2["GM"], m2["PM"]), yaw=(m3["GM"], m3["PM"]))
        log(f"   {key[0]} km/h: pitch {fmt_m(m1['GM'])} dB/{fmt_m(m1['PM'],0)} deg, roll {fmt_m(m2['GM'])}/"
            f"{fmt_m(m2['PM'],0)}, yaw {fmt_m(m3['GM'])}/{fmt_m(m3['PM'],0)}")

    # ---------------------------------------------------------- simulasyonlar
    log("\n[4] Zaman simulasyonlari (dogrusal olmayan servo, anti-windup, 50 Hz FC):")
    sims = {}
    # (a) tam cubuk cekme
    fig, axs = plt.subplots(2, 2, figsize=(12, 7), sharex=True)
    for j, Vk in enumerate((750, 800)):
        for ff, col in ((0.0, "C3"), (1.0, "C0")):
            pt = pts[(Vk, ff)]
            lim = pt["lim"]["de"] * D2R
            trim = [pt["de_trim"] * D2R]
            rf = lambda t: (N_MAX - 1.0) if 0.2 <= t < 2.2 else 0.0
            t, y, s = simulate(pt["plo"], pt["ctl_p"], trim, [lim], 3.0, r_fun=rf)
            n = 1 + y[:, 0]
            npk = n.max()
            os_pct = 100 * (npk - N_MAX) / (N_MAX - 1)
            # FC'siz dogrudan tam cubuk (elevator limiti)
            t2, y2, s2 = simulate(pt["plo"], pt["ctl_p"], trim, [lim], 3.0, ctrl_on=False,
                                  pilot_fun=lambda t: [(-lim - trim[0]) if 0.2 <= t < 2.2 else 0.0])
            n2 = 1 + y2[:, 0]
            sims[f"pull_{Vk}_{int(100*ff)}"] = dict(n_peak=npk, overshoot_pct=os_pct, n_ss=float(n[int(len(n) * 0.6)]),
                                                     de_min=float(s[:, 0].min() * R2D), n_peak_noFC=float(n2.max()))
            log(f"   Tam cubuk cekme {Vk} km/h %{100*ff:.0f} yakit: FC'li n_tepe={npk:.2f} g (asim "
                f"%{os_pct:+.1f}, komut {N_MAX:.0f} g), min de={s[:,0].min()*R2D:+.2f} deg; FC'siz (de=-{pt['lim']['de']:.1f}) "
                f"n_tepe={n2.max():.1f} g")
            axs[0, j].plot(t, n, col, label=f"FC, %{100*ff:.0f} yakit")
            axs[0, j].plot(t2, n2, col + "--", alpha=.6, label=f"FC'siz, %{100*ff:.0f}")
            axs[1, j].plot(t, s[:, 0] * R2D, col, label=f"%{100*ff:.0f} yakit")
        axs[0, j].axhline(N_MAX, color="k", ls=":", lw=1); axs[0, j].axhline(P.N_LIMIT, color="r", ls=":", lw=1)
        axs[0, j].set_title(f"{Vk} km/h tam cubuk cekme (n_komut={N_MAX:.0f} g)")
        axs[0, j].set_ylabel("n [g]"); axs[1, j].set_ylabel("elevator [deg]"); axs[1, j].set_xlabel("t [s]")
        axs[0, j].set_ylim(0, 32)
        for a in axs[:, j]:
            a.grid(alpha=.3); a.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fc_cubuk_cekme.png"), dpi=110); plt.close(fig)

    # (b) dikey ruzgar hamlesi
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.2))
    for j, (Lg, lbl) in enumerate(((GUST_L_SHORT, f"kisa ({GUST_L_SHORT:.1f} m = 25 MAC)"),
                                   (GUST_L_LONG, f"uzun ({GUST_L_LONG:.0f} m)"))):
        for Vk in (750, 800):
            for ff, ls in ((0.0, "-"), (1.0, "--")):
                pt = pts[(Vk, ff)]
                lim = pt["lim"]["de"] * D2R; trim = [pt["de_trim"] * D2R]
                wf = gust_fun(pt["V"], Lg)
                res = {}
                for on in (True, False):
                    t, y, s = simulate(pt["plo"], pt["ctl_p"], trim, [lim], 1.5, w_fun=wf, ctrl_on=on)
                    n = 1 + y[:, 0]
                    res[on] = (n.max(), n.min())
                    if ff == 0.0:
                        axs[j].plot(t, n, ("C3" if Vk == 800 else "C0") + ("-" if on else ":"),
                                    label=f"{Vk} km/h bos {'FC' if on else 'kontrolsuz'}")
                key = f"gust_{'short' if j == 0 else 'long'}_{Vk}_{int(100*ff)}"
                sims[key] = dict(n_peak_fc=res[True][0], n_peak_open=res[False][0],
                                 n_min_fc=res[True][1], n_min_open=res[False][1], L=Lg)
                log(f"   Hamle {GUST_U:.0f} m/s 1-cos {lbl} {Vk} km/h %{100*ff:.0f}: n_tepe kontrolsuz={res[False][0]:.1f} g, "
                    f"FC'li={res[True][0]:.1f} g")
        axs[j].axhline(P.N_LIMIT, color="r", ls=":", lw=1)
        axs[j].set_title(f"{GUST_U:.0f} m/s yukari hamle, {lbl}")
        axs[j].set_xlabel("t [s]"); axs[j].set_ylabel("n [g]"); axs[j].grid(alpha=.3); axs[j].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fc_hamle.png"), dpi=110); plt.close(fig)

    # (c) rudder darbesi -> Dutch roll
    fig, axs = plt.subplots(2, 2, figsize=(12, 7), sharex=True)
    for j, Vk in enumerate((750, 800)):
        for ff in (0.0, 1.0):
            pt = pts[(Vk, ff)]
            lim = [pt["lim"]["da"] * D2R, pt["lim"]["dr"] * D2R]
            pul = lambda t: [0.0, 1.0 * D2R if 0.2 <= t < 0.3 else 0.0]
            out = {}
            for on, nm in ((True, "damperli"), (False, "dampersiz")):
                ctl = pt["ctl_l"] if on else lat_ctrl(pt["roll"]["kffa"], pt["roll"]["kpa"], pt["roll"]["kia"],
                                                      pt["roll"]["tau_fa"], 0.0)
                t, y, s = simulate(pt["pla"], ctl, [0, 0], lim, 2.5, pilot_fun=pul)
                zt = zeta_from_decay(t, y[:, 2], 0.35)
                out[nm] = dict(zeta_sim=zt, beta_max=float(np.abs(y[:, 2]).max() * R2D),
                               ny_max=float(np.abs(y[:, 4]).max()))
                if ff == 0.0:
                    axs[0, j].plot(t, y[:, 2] * R2D, label=f"{nm}")
                    axs[1, j].plot(t, s[:, 1] * R2D, label=f"rudder {nm}")
            sims[f"dr_{Vk}_{int(100*ff)}"] = out
            log(f"   Rudder darbesi 1 deg/0.1 s {Vk} km/h %{100*ff:.0f}: zeta (sim, log dekrement) damperli="
                f"{out['damperli']['zeta_sim']:.2f}, dampersiz={out['dampersiz']['zeta_sim']:.2f}; beta_max "
                f"{out['damperli']['beta_max']:.2f}/{out['dampersiz']['beta_max']:.2f} deg")
        axs[0, j].set_title(f"{Vk} km/h bos yakit: 1 deg x 0.1 s rudder darbesi")
        axs[0, j].set_ylabel("beta [deg]"); axs[1, j].set_ylabel("rudder [deg]"); axs[1, j].set_xlabel("t [s]")
        for a in axs[:, j]:
            a.grid(alpha=.3); a.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fc_dutch_roll.png"), dpi=110); plt.close(fig)

    # (d) servo arizasi: rudder servosu donuk (damper devre disi) + roll manevrasi
    fig, axs = plt.subplots(1, 3, figsize=(14, 4))
    for Vk, col in ((750, "C0"), (800, "C3")):
        pt = pts[(Vk, 0.0)]
        lim = [pt["lim"]["da"] * D2R, pt["lim"]["dr"] * D2R]
        rf = lambda t: P_MAX if 0.2 <= t < 0.5 else (-P_MAX if 0.8 <= t < 1.1 else 0.0)
        out = {}
        for nm, fl in (("normal", None), ("ariza", lambda t: [False, True])):
            t, y, s = simulate(pt["pla"], pt["ctl_l"], [0, 0], lim, 3.0, r_fun=rf, fail=fl)
            out[nm] = dict(beta_max=float(np.abs(y[:, 2]).max() * R2D), ny_max=float(np.abs(y[:, 4]).max()),
                           p_max=float(np.abs(y[:, 0]).max() * R2D), phi_max=float(np.abs(y[:, 3]).max() * R2D),
                           beta_rms_after=float(np.sqrt(np.mean((y[t > 1.2, 2] * R2D) ** 2))))
            ls = "-" if nm == "normal" else "--"
            axs[0].plot(t, y[:, 0] * R2D, col + ls, label=f"{Vk} {nm}")
            axs[1].plot(t, y[:, 2] * R2D, col + ls, label=f"{Vk} {nm}")
            axs[2].plot(t, y[:, 4], col + ls, label=f"{Vk} {nm}")
        sims[f"fail_{Vk}"] = out
        log(f"   Servo arizasi (rudder donuk, damper yok) {Vk} km/h bos, +-300 deg/s yatis: beta_max "
            f"{out['normal']['beta_max']:.2f} -> {out['ariza']['beta_max']:.2f} deg, ny_max "
            f"{out['normal']['ny_max']:.2f} -> {out['ariza']['ny_max']:.2f} g, t>1.2 s beta_rms "
            f"{out['normal']['beta_rms_after']:.3f} -> {out['ariza']['beta_rms_after']:.3f} deg")
    for a, yl in zip(axs, ("p [deg/s]", "beta [deg]", "n_y [g]")):
        a.set_ylabel(yl); a.set_xlabel("t [s]"); a.grid(alpha=.3); a.legend(fontsize=7)
    axs[0].set_title("Roll komutu +-300 deg/s"); axs[1].set_title("Yanal kayma"); axs[2].set_title("Yanal yuk")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fc_servo_ariza.png"), dpi=110); plt.close(fig)

    # ---------------------------------------------------------- ozet grafikler
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.2))
    for ff, mk in ((1.0, "o"), (0.25, "s"), (0.0, "^")):
        V_ = list(SPEEDS_KMH)
        axs[0].plot(V_, [pts[(v, ff)]["mla"]["dr"]["zeta"] for v in V_], marker=mk, ls="-", color="0.6", label=f"acik %{100*ff:.0f}")
        axs[0].plot(V_, [pts[(v, ff)]["z_dr_cl"] for v in V_], marker=mk, ls="-", label=f"damperli %{100*ff:.0f}")
        axs[1].plot(V_, [pts[(v, ff)]["m_pitch"]["GM"] for v in V_], marker=mk, ls="-", label=f"pitch %{100*ff:.0f}")
        axs[1].plot(V_, [pts[(v, ff)]["m_roll"]["GM"] for v in V_], marker=mk, ls="--", label=f"roll %{100*ff:.0f}")
        axs[1].plot(V_, [pts[(v, ff)]["m_yaw"]["GM"] for v in V_], marker=mk, ls=":", label=f"yaw %{100*ff:.0f}")
        axs[2].plot(V_, [pts[(v, ff)]["m_pitch"]["PM"] for v in V_], marker=mk, ls="-", label=f"pitch %{100*ff:.0f}")
        axs[2].plot(V_, [pts[(v, ff)]["m_roll"]["PM"] for v in V_], marker=mk, ls="--", label=f"roll %{100*ff:.0f}")
        axs[2].plot(V_, [pts[(v, ff)]["m_yaw"]["PM"] for v in V_], marker=mk, ls=":", label=f"yaw %{100*ff:.0f}")
    axs[0].axhline(ZETA_DR_TARGET, color="r", ls=":"); axs[0].set_ylabel("zeta_DR"); axs[0].set_title("Dutch roll sonumu")
    axs[1].axhline(GM_REQ, color="r", ls=":"); axs[1].set_ylabel("GM [dB]"); axs[1].set_title("Kazanc payi")
    axs[2].axhline(PM_REQ, color="r", ls=":"); axs[2].set_ylabel("PM [deg]"); axs[2].set_title("Faz payi")
    for a in axs:
        a.set_xlabel("V [km/h]"); a.grid(alpha=.3); a.legend(fontsize=6, ncol=2)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fc_paylar.png"), dpi=110); plt.close(fig)

    # Nyquist/Bode ornek: 750 km/h bos
    pt = pts[(750, 0.0)]
    fig, axs = plt.subplots(2, 1, figsize=(8, 7), sharex=True)
    for m_, nm in ((pt["m_pitch"], "pitch (elevator)"), (pt["m_roll"], "roll (aileron)"), (pt["m_yaw"], "yaw damper (rudder)")):
        axs[0].semilogx(m_["w"], 20 * np.log10(np.abs(m_["L"])), label=nm)
        axs[1].semilogx(m_["w"], np.unwrap(np.angle(m_["L"])) * R2D, label=nm)
    axs[0].axhline(0, color="k", lw=.8); axs[1].axhline(-180, color="k", lw=.8)
    axs[0].set_ylabel("|L| [dB]"); axs[1].set_ylabel("faz [deg]"); axs[1].set_xlabel("w [rad/s]")
    axs[0].set_title("Acik cevrim L(e^jwT), aktuator girisinde kirik - 750 km/h bos yakit (50 Hz, 20 ms)")
    axs[0].set_ylim(-60, 60)
    for a in axs:
        a.grid(alpha=.3, which="both"); a.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fc_bode_750_bos.png"), dpi=110); plt.close(fig)

    # ---------------------------------------------------------- kazanc tablosu
    hdr = ["V_kmh", "yakit_pct", "Kff_nz_deg_per_g", "Knz_deg_per_g", "Ki_nz_deg_per_g_s", "Kq_deg_per_dps",
           "tau_f_nz_s", "Kr_yd_deg_per_dps", "tau_wo_s", "Kff_p_deg_per_dps", "Kp_p_deg_per_dps",
           "Ki_p_deg_per_deg", "tau_f_p_s", "lim_de_deg", "lim_da_deg", "lim_dr_deg", "de_trim_deg",
           "GM_pitch_dB", "PM_pitch_deg", "GM_roll_dB", "PM_roll_deg", "GM_yaw_dB", "PM_yaw_deg", "zeta_DR_cl"]
    rows = []
    for (Vk, ff), pt in pts.items():
        pc, ro = pt["pc"], pt["roll"]
        rows.append([Vk, int(100 * ff), pc["kff"] * R2D, pc["knz"] * R2D, pc["ki"] * R2D, pc["kq"], pc["tau_f"],
                     pt["kr"], TAU_WO, ro["kffa"], ro["kpa"], ro["kia"], ro["tau_fa"], pt["lim"]["de"],
                     pt["lim"]["da"], pt["lim"]["dr"], pt["de_trim"], pt["m_pitch"]["GM"], pt["m_pitch"]["PM"],
                     pt["m_roll"]["GM"], pt["m_roll"]["PM"], pt["m_yaw"]["GM"], pt["m_yaw"]["PM"], pt["z_dr_cl"]])
    with open(os.path.join(OUT, "fc_kazanc_tablosu.csv"), "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(hdr)
        for r in rows:
            wr.writerow([r[0], r[1]] + [f"{v:.5g}" for v in r[2:]])
    log("\n[5] Kazanc tablosu -> aero/out/fc_kazanc_tablosu.csv (isaret kurallari docs/09_ucus_kontrol.md)")
    log("   V %yak | Kff  Knz [deg/g]  Ki [deg/(g s)]  Kq [deg/(deg/s)] tau_f | Kr [deg/(deg/s)] | "
        "Kff_p Kp_p [deg/(deg/s)] Ki_p [deg/deg] | limit e/a/r")
    for r in rows:
        log(f"   {r[0]:3d} {r[1]:3d} | {r[2]:.3f} {r[3]:.3f} {r[4]:.3f} {r[5]:.4f} {r[6]:.3f} | {r[7]:.4f} | "
            f"{r[9]:.4f} {r[10]:.4f} {r[11]:.4f} | {r[13]:.1f}/{r[14]:.1f}/{r[15]:.1f}")

    # ---------------------------------------------------------- JSON
    def clean(v):
        if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
            return None
        return v
    js = dict(mass_source=mp_src, mass=mp, servo=dict(bw_hz=SERVO_BW_HZ, rate_dps=SERVO_RATE * R2D),
              loop_hz=1 / T_LOOP, delay_s=T_LOOP, limits_hs=LIM_HS, n_cmd=[N_MIN, N_MAX], p_max_dps=P_MAX * R2D,
              tau_wo=TAU_WO, dclb_datcom=dclb_datcom(), all_targets_met=allok, points=[], sims=sims,
              sens_200Hz={f"{k[0]}_{int(100*k[1])}": v for k, v in sens.items()}, gain_table=dict(header=hdr, rows=rows))
    for (Vk, ff), pt in pts.items():
        js["points"].append(dict(
            V_kmh=Vk, fuel=ff, alpha=pt["alpha"], de_trim=pt["de_trim"], qbar=pt["qbar"], der=pt["der"],
            modes_long=pt["ml"], modes_lat={k: v for k, v in pt["mla"].items()},
            A_long=pt["plo"]["A"].tolist(), B_long=pt["plo"]["B"].tolist(), A_lat=pt["pla"]["A"].tolist(),
            B_lat=pt["pla"]["B"].tolist(), pitch=pt["pc"], roll=pt["roll"], Kr=pt["kr"],
            margins={k: dict(GM=clean(pt[k]["GM"]), PM=clean(pt[k]["PM"]), wc=clean(pt[k]["wc"]))
                     for k in ("m_pitch", "m_roll", "m_yaw")},
            zeta_dr_cl=pt["z_dr_cl"], zeta_dr_nodamper=pt["z_dr_nod"], zeta_sp_cl=pt["z_sp_cl"],
            step_nz=dict(os=pt["os_n"], t90=pt["t90_n"]), step_p=dict(os=pt["os_p"], t90=pt["t90_p"]),
            ok=pt["ok"], limits=pt["lim"]))
    with open(os.path.join(OUT, "fc_sonuclar.json"), "w", encoding="utf-8") as fh:
        json.dump(js, fh, indent=1, default=lambda o: clean(float(o)) if np.isscalar(o) else str(o))
    with open(os.path.join(OUT, "fc_ozet.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
