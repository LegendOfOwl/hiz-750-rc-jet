"""
HIZ-750 - iterasyon 4: kanat yarisi 1D sonlu eleman (FE) modal analizi + modal flutter.

Kapsam
  1. structures.py kesit ozellikleri (EI(y), GJ(y), m'(y), kesit CG(y), kesit ataleti, EA 0.30c, entegre
     tank yakiti) structures.wing_section_model() ile yeniden kullanilir (ayni kat plani, ayni yuk adimlari).
     Kanat yarisi, gercek baglanti hattinda (tek parca kanat, kiris cercevelerinde 4 x M6, y = +-35 mm)
     ankastre, ok acili elastik eksen boyunca 1D kiris: Euler-Bernoulli egilme (w, w') + St-Venant burulma
     (phi), CG-EA ofsetinden kutle eslesmesi, Hermite/lineer elemanlar (40 eleman, 4 nokta Gauss).
     Kesit verileri akis yonu seritlerinde tanimlidir; elastik eksene dik kesite donusum:
       m_s = m'cosL, S_s = S'cos^2 L, I_s = I'cos^3 L, GJ_n = GJ cosL, EI_n = EI (kapaklar kiris boyunca).
     Aileron balans kutlesi (23 g) structures kesit kutlesinde; aileron/flap servolari (MASS_ITEMS 0.48 kg/4)
     noktasal kutle olarak eklenir.
  2. Modal flutter: ilk 8 mod (en az 2 burulma modu garanti), serit teorisi + Theodorsen (dik kesit, V_n = V cosL, b_n = b cosL),
     ok acisinin egilme-egimi terimi (alpha_eff = phi - tanL w', Barmby/Bisplinghoff), Prandtl-Glauert
     (M_n = M cosL, M_n <= 0.9), k-yontemi + Mach eslestirme (match-point). Diverjans: FE statik
     aeroelastik ozdeger problemi. Tank dolu/bos.
  3. Dogrulama: ankastre uniform kiris (analitik egilme/burulma), Goland kanadi (~137 m/s, ~70 rad/s).
  4. Duyarlilik: kesit CG 0.42/0.45/0.48/0.52c x GJ 0.8/1.0/1.2; 2-DOF ile karsilastirma.
  5. GVT hedef tablosu ve kabul frekans araliklari (modal frekans olcekleme haritasi).
  6. Kanat entegre tank hacmi uzlasmasi (CAD 0.715 L vs structures 0.57-0.58 L) ve kullanilabilir hacim.

Calistir:  C:/Users/Urungu/.hz750/Scripts/python structures/fe_modal.py
Ciktilar:  structures/out/fe_*.png, structures/out/fe_sonuclar.json  (params.py degistirilmez)
"""
import json
import math
import os
import sys

import numpy as np
from scipy.linalg import eigh
from scipy.optimize import linear_sum_assignment, brentq
from scipy.special import hankel2
from scipy.interpolate import PchipInterpolator
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import structures as ST  # noqa: E402
from params import WING, FUEL, MASS_ITEMS, V_D, V_FLUTTER_REQ  # noqa: E402

OUT = ST.OUT
RHO = ST.RHO0
A_SND = ST.A_SOUND
B2 = ST.B2
X_EA = ST.X_EA
A_EA = (X_EA - 0.5) / 0.5                     # Theodorsen 'a' (EA konumu, yari veter birimi)
V_REQ = V_FLUTTER_REQ
MODEL_FACTOR = ST.FLUTTER_MODEL_FACTOR        # 1.25 (kat secimindeki ek pay, bilgi amacli)

# ------------------------------------------------------------------ geometri / model varsayimlari
Y_CLAMP = 0.035          # ankastre hat: kiris cercevelerindeki 4 x M6 civata, y = +-35 mm (structures bolt_dy/2)
NE = 40                  # eleman sayisi
NGAUSS = 4
N_MODES_FLUTTER = 8      # iter5 inceleme: 4 mod 4/1 kat planinda (dolu) 1T'yi (5. mod) disarida birakiyordu ->
                         # yalniz egilme modlariyla sahte 1813 km/h ve f_T'den bagimsiz duz V_F(f_T) egrisi.
                         # 8 modda dolu/bos 1D sonuc yakinsadi (8 -> 14 mod fark < %0.5).
MIN_TORSION_MODES = 2


def flutter_mode_count(md, nm):
    """Flutter mod kumesi: en az nm mod ve en az MIN_TORSION_MODES burulma modu (siralamadan bagimsiz)."""
    idx = [i for i, t in enumerate(md["tors"]) if t > 0.5]
    if len(idx) >= MIN_TORSION_MODES:
        nm = max(nm, idx[MIN_TORSION_MODES - 1] + 1)
    return min(nm, len(md["omega"]))
_tan_le = math.tan(math.radians(WING["sweep_le"]))
TAN_EA = _tan_le - X_EA * (ST.wg["cr"] - ST.wg["ct"]) / B2
LAM_EA = math.atan(TAN_EA)                    # elastik eksen ok acisi
M_SERVO = [i[1] for i in MASS_ITEMS if i[0].startswith("Servolar: aileron")][0] / 4   # 0.12 kg/servo
# (ad, kutle, y [m], x/c): aileron servosu tank disinda (tank eta<=0.55 kirisler arasini dolduruyor) ->
# arka kiris gerisinde, aileron menteşesinin onunde; flap servosu flap ic ucunda. Kutle butcesi x=1.22 ile uyumlu.
SERVOS = [("aileron servosu", M_SERVO, 0.34, 0.60), ("flap servosu", M_SERVO, 0.10, 0.65)]
KS = np.logspace(math.log10(4.0), math.log10(0.004), 500)   # indirgenmis frekans taramasi (yuksek k -> dusuk V)
RES = {}


def chord(y):
    return ST.chord(y)


# ================================================================== kesit verisi
def section_data(base, fuel=True, m_fuel_half=None, xcg_shift=0.0, gj_fac=1.0, sweep=True):
    """structures kesit ozellikleri -> elastik eksene dik kiris ozellikleri (birim s uzunlugu basina)."""
    ws, YS = base["ws"], base["YS"]
    c = chord(YS)
    xcg = ws["xcg"] + xcg_shift
    ms = ws["mprime"]
    mf = ST.fuel_per_span(m_fuel_half) if fuel else np.zeros_like(YS)
    m, S_a, Ia = ST.section_inertia(ms, c, mf, xcg)          # akis yonu, birim y, EA etrafinda
    cl = math.cos(LAM_EA) if sweep else 1.0
    return dict(y=YS, c=c, m=m * cl, S=S_a * cl ** 2, I=Ia * cl ** 3, EI=ws["EI"].copy(),
                GJ=ws["GJ"] * gj_fac * cl, bn=0.5 * c * cl, bs=0.5 * c, cosL=cl,
                tanL=(TAN_EA if sweep else 0.0), xcg=xcg, mf=mf, ms=ms, sweep=sweep)


def beam_from_section(sec, y_clamp=Y_CLAMP, servos=SERVOS):
    cl = sec["cosL"]
    L = (B2 - y_clamp) / cl
    f = {k: (lambda s, a=sec[k]: np.interp(y_clamp + s * cl, sec["y"], a))
         for k in ("EI", "GJ", "m", "S", "I", "bn", "bs")}
    pm = []
    for name, m, y, xc in (servos or []):
        if y <= y_clamp:
            continue
        d = (xc - X_EA) * chord(y) * cl
        pm.append((name, (y - y_clamp) / cl, m, d))
    return dict(L=L, f=f, a=A_EA, tanL=sec["tanL"], cosL=cl, y_of_s=lambda s: y_clamp + s * cl,
                point_masses=pm, y_clamp=y_clamp)


# ================================================================== 1D FE
def _shape(xi, Le):
    Nw = np.array([1 - 3 * xi ** 2 + 2 * xi ** 3, Le * (xi - 2 * xi ** 2 + xi ** 3), 0.0,
                   3 * xi ** 2 - 2 * xi ** 3, Le * (-xi ** 2 + xi ** 3), 0.0])
    dNw = np.array([(-6 * xi + 6 * xi ** 2) / Le, 1 - 4 * xi + 3 * xi ** 2, 0.0,
                    (6 * xi - 6 * xi ** 2) / Le, -2 * xi + 3 * xi ** 2, 0.0])
    ddNw = np.array([(-6 + 12 * xi) / Le ** 2, (-4 + 6 * xi) / Le, 0.0,
                     (6 - 12 * xi) / Le ** 2, (-2 + 6 * xi) / Le, 0.0])
    Nf = np.array([0, 0, 1 - xi, 0, 0, xi])
    dNf = np.array([0, 0, -1 / Le, 0, 0, 1 / Le])
    return Nw, dNw, ddNw, Nf, dNf


def build_fe(beam, ne=NE):
    """Global DOF: dugum i -> (w, w', phi) = 3i..3i+2. w yukari, phi burun yukari (EA etrafinda)."""
    L = beam["L"]
    sn = np.linspace(0, L, ne + 1)
    nd = 3 * (ne + 1)
    K = np.zeros((nd, nd))
    Kt = np.zeros((nd, nd))
    M = np.zeros((nd, nd))
    gx, gw = np.polynomial.legendre.leggauss(NGAUSS)
    gx, gw = 0.5 * (gx + 1), 0.5 * gw
    f = beam["f"]
    strips = dict(s=[], w=[], B=[], idx=[], bn=[], bs=[])
    for e in range(ne):
        Le = sn[e + 1] - sn[e]
        idx = np.arange(3 * e, 3 * e + 6)
        Ke = np.zeros((6, 6))
        Kte = np.zeros((6, 6))
        Me = np.zeros((6, 6))
        for xi, wgt in zip(gx, gw):
            s = sn[e] + xi * Le
            Nw, dNw, ddNw, Nf, dNf = _shape(xi, Le)
            wt = wgt * Le
            Ke += wt * f["EI"](s) * np.outer(ddNw, ddNw)
            Kte += wt * f["GJ"](s) * np.outer(dNf, dNf)
            Me += wt * (f["m"](s) * np.outer(Nw, Nw) - f["S"](s) * (np.outer(Nw, Nf) + np.outer(Nf, Nw))
                        + f["I"](s) * np.outer(Nf, Nf))
            strips["s"].append(s)
            strips["w"].append(wt)
            strips["B"].append(np.vstack([Nw, dNw, Nf]))
            strips["idx"].append(idx)
            strips["bn"].append(float(f["bn"](s)))
            strips["bs"].append(float(f["bs"](s)))
        K[np.ix_(idx, idx)] += Ke + Kte
        Kt[np.ix_(idx, idx)] += Kte
        M[np.ix_(idx, idx)] += Me
    for name, s, m, d in beam["point_masses"]:
        e = min(int(s / (L / ne)), ne - 1)
        Le = sn[e + 1] - sn[e]
        Nw, _, _, Nf, _ = _shape((s - sn[e]) / Le, Le)
        v = Nw - d * Nf
        idx = np.arange(3 * e, 3 * e + 6)
        M[np.ix_(idx, idx)] += m * np.outer(v, v) + m * 0.015 ** 2 * np.outer(Nf, Nf)
    for k in strips:
        strips[k] = np.array(strips[k])
    free = np.arange(3, nd)                      # kok dugumu ankastre
    return dict(K=K, Kt=Kt, M=M, sn=sn, free=free, strips=strips, beam=beam, nd=nd)


def modes(fe, n=8):
    fr = fe["free"]
    w2, V = eigh(fe["K"][np.ix_(fr, fr)], fe["M"][np.ix_(fr, fr)])
    Phi = np.zeros((fe["nd"], len(w2)))
    Phi[fr, :] = V
    Phi = Phi[:, :n]
    om = np.sqrt(np.abs(w2[:n]))
    tors = np.array([Phi[:, i] @ fe["Kt"] @ Phi[:, i] / (Phi[:, i] @ fe["K"] @ Phi[:, i]) for i in range(n)])
    names = []
    nb = nt = 0
    for t in tors:
        if t > 0.5:
            nt += 1
            names.append(f"{nt}T (burulma)")
        else:
            nb += 1
            names.append(f"{nb}B (egilme)")
    return dict(omega=om, f=om / 2 / math.pi, Phi=Phi, tors=tors, names=names)


# ================================================================== aerodinamik (serit, Theodorsen)
def theodorsen(k):
    H1, H0 = hankel2(1, k), hankel2(0, k)
    return H1 / (H1 + 1j * H0)


def modal_aero(fe, md, nm, b_ref, ks=KS, slope=True):
    """Dq(k): modal aerodinamik 'ek kutle' matrisi (beta=1). K q(1+ig) = w^2 (I + Dq/beta) q."""
    st = fe["strips"]
    beam = fe["beam"]
    Phi = md["Phi"][:, :nm]
    T = np.einsum("sab,sbj->saj", st["B"], Phi[st["idx"], :])          # (ns, 3, nm): (w, w', phi)
    bn, bs, wt = st["bn"], st["bs"], st["w"]
    kk = ks[:, None] * bs[None, :] / b_ref                                # yerel indirgenmis frekans
    C = theodorsen(kk)
    a = beam["a"]
    ap = 0.5 + a
    Lh = 1 - 2j * C / kk
    La = 0.5 - 1j * (1 + 2 * C) / kk - 2 * C / kk ** 2
    Mh = 0.5
    Ma = 3 / 8 - 1j / kk
    la = La - Lh * ap
    mh = Mh - Lh * ap
    ma = Ma - (La + Mh) * ap + Lh * ap ** 2
    sl = (2 * C / kk ** 2) * beam["tanL"] * (1.0 if slope else 0.0)
    pr = math.pi * RHO
    D = np.zeros(kk.shape + (3, 3), dtype=complex)
    D[..., 0, 0] = pr * bn ** 2 * Lh
    D[..., 0, 1] = -pr * bn ** 3 * sl
    D[..., 0, 2] = -pr * bn ** 3 * la
    D[..., 2, 0] = -pr * bn ** 3 * mh
    D[..., 2, 1] = -pr * bn ** 4 * ap * sl
    D[..., 2, 2] = pr * bn ** 4 * ma
    return np.einsum("s,sai,ksab,sbj->kij", wt, T, D, T)


def k_sweep(om, Dq, beta, b_ref, ks=KS, fscale=None):
    nm = len(om)
    om2 = (om if fscale is None else om * fscale) ** 2
    A = (np.eye(nm)[None] + Dq / beta) / om2[None, :, None]
    Z = np.linalg.eigvals(A)
    Zt = np.zeros_like(Z)
    order = np.argsort(-Z[0].real)
    Zt[0] = Z[0][order]
    for i in range(1, len(ks)):
        cost = np.abs(Zt[i - 1][:, None] - Z[i][None, :]) / np.abs(Zt[i - 1])[:, None]
        r, c = linear_sum_assignment(cost)
        Zt[i] = Z[i][c]
    re = np.clip(Zt.real, 1e-16, None)
    w = 1 / np.sqrt(re)
    g = Zt.imag / re
    V = w * b_ref / ks[:, None]
    return V, g, w


def find_flutter(V, g, w, g_s=0.0, vmax=6000 / 3.6):
    best = None
    for j in range(V.shape[1]):
        for i in range(V.shape[0] - 1):
            if V[i + 1, j] > V[i, j] and V[i, j] < vmax and (g[i, j] - g_s) < 0 <= (g[i + 1, j] - g_s):
                t = (g_s - g[i, j]) / (g[i + 1, j] - g[i, j])
                Vf = V[i, j] + t * (V[i + 1, j] - V[i, j])
                wf = w[i, j] + t * (w[i + 1, j] - w[i, j])
                if best is None or Vf < best[0]:
                    best = (Vf, wf, j)
    return best if best else (float("inf"), float("nan"), -1)


def beta_of(V, cosL, M_fixed=None):
    Mn = (M_fixed if M_fixed is not None else V / A_SND) * cosL
    return math.sqrt(1 - min(Mn, 0.9) ** 2)


VS_PK = np.arange(20.0, 4000.0, 10.0) / 3.6     # p-k hiz izgarasi [m/s]


def pk_sweep(om, Dq, beta, b_ref, Vs=VS_PK, ks=KS, fscale=None):
    """p-k yontemi (Hassig): her V ve her mod icin  [s^2 I + K - w^2 Dq(k)/beta] q = 0,
    k = w b_ref / V yakinsayana kadar. Donus: V, g = 2 Re(s)/Im(s), w  (n_V x n_mod)."""
    nm = len(om)
    om_s = om if fscale is None else om * fscale
    K = np.diag(om_s ** 2)
    lk = np.log(ks[::-1])
    Dr = Dq[::-1] / beta

    def Dk(k):
        x = min(max(math.log(k), lk[0]), lk[-1])
        i = min(max(int(np.searchsorted(lk, x)), 1), len(lk) - 1)
        t = (x - lk[i - 1]) / (lk[i] - lk[i - 1])
        return Dr[i - 1] * (1 - t) + Dr[i] * t
    Sx = np.zeros((len(Vs), nm), dtype=complex)

    def roots(w, V):
        lam = np.linalg.eigvals(-(K - w ** 2 * Dk(w * b_ref / V)))
        sr = np.sqrt(lam.astype(complex))
        return np.where(sr.imag < 0, -sr, sr)

    def track(V, s_pred, exclude=None):
        w = max(s_pred.imag, 1e-3)
        sj = s_pred
        for _ in range(100):
            sr = roots(w, V)
            d = np.abs(sr - s_pred)
            if exclude is not None:
                d = d + 1e9 * (np.abs(sr - exclude) < 1e-6 * abs(exclude))
            sj = sr[int(np.argmin(d))]
            wn = max(sj.imag, 1e-3)
            if abs(wn - w) < 1e-7 * w:
                break
            w = 0.5 * (w + wn) if _ > 30 else wn
        return sj
    for iv, V in enumerate(Vs):
        for i in range(nm):
            if iv == 0:
                s_pred = complex(-0.01 * om_s[i], om_s[i])
            elif iv == 1:
                s_pred = Sx[0, i]
            else:
                s_pred = 2 * Sx[iv - 1, i] - Sx[iv - 2, i]      # dogrusal ongoru (kok takibi)
            Sx[iv, i] = track(V, s_pred)
        # iki iz ayni koke dustuyse ongoruye daha uzak olani ikinci en yakin koke tasi
        for i in range(nm):
            for j in range(i + 1, nm):
                if abs(Sx[iv, i] - Sx[iv, j]) < 1e-4 * abs(Sx[iv, i]) and iv >= 2:
                    pi = 2 * Sx[iv - 1, i] - Sx[iv - 2, i]
                    pj = 2 * Sx[iv - 1, j] - Sx[iv - 2, j]
                    m_ = i if abs(Sx[iv, i] - pi) > abs(Sx[iv, j] - pj) else j
                    pm = pi if m_ == i else pj
                    Sx[iv, m_] = track(V, pm, exclude=Sx[iv, i + j - m_])
    W = Sx.imag
    G = 2 * Sx.real / np.maximum(Sx.imag, 1e-9)
    return np.repeat(Vs[:, None], nm, axis=1), G, W


def pk_fresh(om, Dq, beta, b_ref, Vs, ks=KS):
    """İz takibinden bağımsız p-k: her V'de her mod frekansından VE önceki V'nin köklerinden yeniden
    başlatılan sabit nokta yinelemesi; yakınsayan farklı köklerin en büyük g'si. pk_sweep'in kök
    takibi yakın 1T/3B frekanslarında dal değiştirebiliyor (s41r043w1 dolu, M_n tavanında 2554 km/h)."""
    K = np.diag(np.asarray(om) ** 2)
    lk = np.log(ks[::-1])
    D0 = Dq[::-1]
    bfun = beta if callable(beta) else (lambda V: beta)     # Mach eslestirme: beta(V)
    cur = {}

    def Dk(k):
        x = min(max(math.log(k), lk[0]), lk[-1])
        i = min(max(int(np.searchsorted(lk, x)), 1), len(lk) - 1)
        t = (x - lk[i - 1]) / (lk[i] - lk[i - 1])
        return (D0[i - 1] * (1 - t) + D0[i] * t) / cur["b"]

    def converge(V, s0):
        w, s = max(s0.imag, 1e-3), s0
        for it in range(200):
            lam = np.linalg.eigvals(-(K - w ** 2 * Dk(w * b_ref / V)))
            sr = np.sqrt(lam.astype(complex))
            sr = np.where(sr.imag < 0, -sr, sr)
            s = sr[int(np.argmin(np.abs(sr - s)))]
            wn = max(s.imag, 1e-3)
            if abs(wn - w) < 1e-8 * w:
                return s
            w = 0.5 * (w + wn) if it > 30 else wn
        return s
    gmax, prev = [], []
    for V in Vs:
        cur["b"] = bfun(V)
        starts = [complex(-0.01 * o, o) for o in om] + prev
        roots = []
        for s0 in starts:
            s = converge(V, s0)
            if all(abs(s - r) > 1e-5 * abs(s) for r in roots):
                roots.append(s)
        prev = roots
        gmax.append(max(2 * r.real / max(r.imag, 1e-9) for r in roots))
    return np.array(gmax)


def first_crossing(Vs, g, g_s=0.0):
    for i in range(len(Vs) - 1):
        if g[i] < g_s <= g[i + 1]:
            return float(Vs[i] + (g_s - g[i]) / (g[i + 1] - g[i]) * (Vs[i + 1] - Vs[i]))
    return None


def flutter_solve(om, Dq, b_ref, cosL, g_s=0.0, M_fixed=None, fscale=None, mach=True, method="pk",
                  curves=False):
    """Mach eslestirmeli (match-point) flutter. beta(V) = sqrt(1 - M_n^2), M_n = V cosL / a <= 0.9.
    V_F(beta(V)) - V monoton azalan -> once tavan beta ile cozulur, tutarsizsa Brent ile kok bulunur.
    Donus: Vf, wf, dal, beta (+ egriler)."""
    sweep = pk_sweep if method == "pk" else k_sweep
    cache = {}

    def solve(beta):
        cache["c"] = sweep(om, Dq, beta, b_ref, fscale=fscale)
        return find_flutter(*cache["c"], g_s=g_s)

    def ret(r, b):
        return (*r, b, cache["c"]) if curves else (*r, b)
    if not mach:
        return ret(solve(1.0), 1.0)
    if M_fixed is not None:
        b = beta_of(0.0, cosL, M_fixed)
        return ret(solve(b), b)
    V_cap = 0.9 * A_SND / cosL
    b_cap = beta_of(V_cap, cosL)
    r = solve(b_cap)
    if r[0] >= V_cap:
        return ret(r, b_cap)

    def h(V):
        v = solve(beta_of(V, cosL))[0]
        return (v if math.isfinite(v) else 1e5) - V
    Vm = brentq(h, 1.0, V_cap, xtol=0.3)
    b = beta_of(Vm, cosL)
    return ret(solve(b), b)


def divergence_fe(fe, slope=True):
    """Statik aeroelastik: K u = (q_n/beta) Ka u (serit, a0 = 2pi). Mach eslestirmeli."""
    st, beam = fe["strips"], fe["beam"]
    nd = fe["nd"]
    Ka = np.zeros((nd, nd))
    tl = beam["tanL"] * (1.0 if slope else 0.0)
    ap = 0.5 + beam["a"]
    for B, idx, bn, wt in zip(st["B"], st["idx"], st["bn"], st["w"]):
        r = 2 * bn * 2 * math.pi * np.array([0.0, -tl, 1.0])     # kaldirma / (q_n) : (w, w', phi)
        D = np.zeros((3, 3))
        D[0] = r
        D[2] = bn * ap * r
        Ka[np.ix_(idx, idx)] += wt * B.T @ D @ B
    fr = fe["free"]
    lam = np.linalg.eigvals(np.linalg.solve(fe["K"][np.ix_(fr, fr)], Ka[np.ix_(fr, fr)]))
    lam = lam[(np.abs(lam.imag) < 1e-6 * np.abs(lam).max()) & (lam.real > 0)].real
    if lam.size == 0:
        return float("inf")
    q_eff = 1 / lam.max()
    cl = beam["cosL"]
    V = math.sqrt(2 * q_eff / RHO) / cl
    for _ in range(40):
        V = math.sqrt(2 * q_eff * beta_of(V, cl) / RHO) / cl
    return V if V < 2.0e4 / 3.6 else float("inf")     # > 20000 km/h: pratikte diverjans yok


# ================================================================== tam analiz zinciri
def b_ref_default():
    return 0.5 * chord(ST.Y0 + 0.70 * (B2 - ST.Y0))


def analyse(sec, y_clamp=Y_CLAMP, servos=SERVOS, slope=True, nm=N_MODES_FLUTTER, mach=True,
            want_curves=False):
    beam = beam_from_section(sec, y_clamp, servos)
    fe = build_fe(beam)
    md = modes(fe, 16)
    nm = flutter_mode_count(md, nm)
    b_ref = b_ref_default()
    Dq = modal_aero(fe, md, nm, b_ref, slope=slope)
    om = md["omega"][:nm]
    Vf, wf, br, beta, cur = flutter_solve(om, Dq, b_ref, beam["cosL"], mach=mach, curves=True)
    Vf2 = find_flutter(*cur, g_s=0.02)[0]          # ayni beta ile g_s = 0.02
    # iter5 inceleme: pk_sweep kok takibi yakin frekansli modlarda dal degistirebiliyor (ornek: adim C
    # 3839 km/h, iz-takipsiz 1776 km/h). Iz-takipsiz kontrol (her V'de kendi beta'si); dusuk olan alinir.
    Vs = np.arange(300.0, 4000.0, 10.0) / 3.6
    cl = beam["cosL"]
    gmax = pk_fresh(om, Dq, (lambda V: beta_of(V, cl)) if mach else 1.0, b_ref, Vs)
    Vfresh = first_crossing(Vs, gmax) or float("inf")
    tracking_ok = (not math.isfinite(Vf) and not math.isfinite(Vfresh)) or abs(Vfresh / Vf - 1) < 0.02
    if Vfresh < Vf:
        Vf, wf, br = Vfresh, float("nan"), -1
    Vfix, _, _, _ = flutter_solve(om, Dq, b_ref, beam["cosL"], M_fixed=V_REQ / A_SND, mach=mach)
    Vdiv = divergence_fe(fe, slope)
    r = dict(f_Hz=md["f"].tolist(), names=md["names"], tors=md["tors"].tolist(), Vf=Vf, Vf_kmh=Vf * 3.6,
             ff_Hz=wf / 2 / math.pi, branch=br, Vf_g02_kmh=Vf2 * 3.6, Vf_Mfix_kmh=Vfix * 3.6,
             Vdiv_kmh=Vdiv * 3.6, beta=beta, n_modes=nm, Vf_fresh_kmh=Vfresh * 3.6, tracking_ok=bool(tracking_ok))
    if want_curves:
        r["_curves"] = cur
        r["_fe"], r["_md"], r["_Dq"], r["_bref"], r["_beam"] = fe, md, Dq, b_ref, beam
    return r


# ================================================================== dogrulama
def uniform_beam(L=1.0, EI=1.0, GJ=1.0, m=1.0, I=1.0):
    f = dict(EI=lambda s: EI + 0 * s, GJ=lambda s: GJ + 0 * s, m=lambda s: m + 0 * s, S=lambda s: 0 * s,
             I=lambda s: I + 0 * s, bn=lambda s: 0.5 + 0 * s, bs=lambda s: 0.5 + 0 * s)
    return dict(L=L, f=f, a=0.0, tanL=0.0, cosL=1.0, y_of_s=lambda s: s, point_masses=[], y_clamp=0.0)


def validate_uniform():
    md = modes(build_fe(uniform_beam(), 20), 30)
    bend = sorted(w for w, t in zip(md["omega"], md["tors"]) if t < 0.5)[:3]
    tors = sorted(w for w, t in zip(md["omega"], md["tors"]) if t >= 0.5)[:2]
    bl = [1.875104, 4.694091, 7.854757]
    ex_b = [x ** 2 for x in bl]
    ex_t = [math.pi / 2, 3 * math.pi / 2]
    return dict(bending=[dict(fe=b, exact=e, err_pct=100 * (b / e - 1)) for b, e in zip(bend, ex_b)],
                torsion=[dict(fe=b, exact=e, err_pct=100 * (b / e - 1)) for b, e in zip(tors, ex_t)])


def goland_beam(I_about="cg"):
    """Goland (1945) kanadi: L=6.096 m, c=1.8288 m, EA %33c, CG %43c, m=35.71 kg/m, I=8.64 kg.m,
    EI=9.77e6, GJ=0.987e6 N.m2. Literatur (serit teorisi): V_F ~ 137 m/s, w_F ~ 70 rad/s;
    frekanslar 49.6 / 97.0 / 248 rad/s."""
    c, m, I0 = 1.8288, 35.71, 8.64
    d = 0.10 * c
    I = I0 + m * d ** 2 if I_about == "cg" else I0
    f = dict(EI=lambda s: 9.77e6 + 0 * s, GJ=lambda s: 0.987e6 + 0 * s, m=lambda s: m + 0 * s,
             S=lambda s: m * d + 0 * s, I=lambda s: I + 0 * s, bn=lambda s: c / 2 + 0 * s,
             bs=lambda s: c / 2 + 0 * s)
    return dict(L=6.096, f=f, a=-0.34, tanL=0.0, cosL=1.0, y_of_s=lambda s: s, point_masses=[], y_clamp=0.0)


def validate_goland():
    out = {}
    for about in ("cg", "ea"):
        fe = build_fe(goland_beam(about), 30)
        md = modes(fe, 8)
        out[about] = dict(omega=md["omega"][:4].tolist(), names=md["names"][:4])
    # literatur frekanslarina (49.6/97.0/248) en yakin tanim
    ref = np.array([49.6, 97.0, 248.0])
    about = min(out, key=lambda a: np.sum((np.sort(out[a]["omega"])[:3] / ref - 1) ** 2))
    fe = build_fe(goland_beam(about), 30)
    md = modes(fe, 8)
    curves = {}
    for nm in (2, 4, 6):
        Dq = modal_aero(fe, md, nm, 0.9144, slope=False)
        Vk, gk, wk = k_sweep(md["omega"][:nm], Dq, 1.0, 0.9144)
        V, g, w = pk_sweep(md["omega"][:nm], Dq, 1.0, 0.9144, Vs=np.arange(5.0, 300.0, 1.0))
        Vf, wf, br = find_flutter(V, g, w)
        Vfk, wfk, _ = find_flutter(Vk, gk, wk)
        out[f"flutter_{nm}modes"] = dict(Vf=Vf, wf=wf, Vf_k=Vfk, wf_k=wfk)
        curves[nm] = (V, g, w)
    out["I_definition"] = about
    out["reference"] = dict(Vf=137.2, wf=70.7, omega=[49.6, 97.0, 248.0])
    V, g, w = curves[4]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7, 6.5), sharex=True)
    for j in range(V.shape[1]):
        a1.plot(V[:, j], g[:, j], label=f"dal {j+1}")
        a2.plot(V[:, j], w[:, j], label=f"dal {j+1}")
    for a in (a1, a2):
        a.axvline(137.2, color="r", ls=":", label="Goland referans 137 m/s")
        a.grid(alpha=.3)
        a.set_xlim(0, 250)
    a1.set_ylim(-0.5, 0.2)
    a1.axhline(0, color="k", lw=.5)
    a1.set_ylabel("g")
    a2.set_ylabel("w [rad/s]")
    a2.set_ylim(0, 300)
    a2.set_xlabel("V [m/s]")
    a1.legend(fontsize=8)
    a1.set_title(f"Dogrulama: Goland kanadi, FE + serit Theodorsen, p-k, 4 mod -> V_F = "
                 f"{out['flutter_4modes']['Vf']:.1f} m/s, w_F = {out['flutter_4modes']['wf']:.1f} rad/s",
                 fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fe_dogrulama_goland.png"), dpi=130)
    plt.close(fig)
    return out


# ================================================================== tank hacmi uzlasmasi
_X64 = np.array([0, .5, .75, 1.25, 2.5, 5, 7.5, 10, 15, 20, 25, 30, 35, 40, 45, 50,
                 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]) / 100
_Y64 = np.array([0, .804, .969, 1.225, 1.688, 2.327, 2.805, 3.199, 3.813, 4.272, 4.606,
                 4.837, 4.968, 4.995, 4.894, 4.684, 4.388, 4.021, 3.597, 3.127, 2.623,
                 2.103, 1.582, 1.062, .541, .021]) / 100        # NACA 64A010 (Abbott & von Doenhoff), CAD ile ayni
_I64 = PchipInterpolator(np.sqrt(_X64), _Y64)


def _yt(xc, t_c):
    return _I64(np.sqrt(xc)) * t_c / 0.10


def tank_volume(base, eta=(0.06, 0.55), t_wall=2.6e-3, t_web=1.5e-3, t_rib=3.0e-3, tc_mode="params",
                caps=False, n_mid_ribs=0, shape="profile"):
    """Yari kanat tank ic hacmi [L]. tc_mode 'cad': CAD loft kesitleri (64A007,007,006,006,006 @ s/bh
    = 0,.25,.5,.75,1; aralarda dogrusal); 'params': t/c koke->uca dogrusal (structures)."""
    ws, YS = base["ws"], base["YS"]
    y0, y1 = eta[0] * B2 + t_rib, eta[1] * B2 - t_rib
    yy = np.linspace(y0, y1, 300)
    xf, xr = ST.XS_F, ST.XS_R
    A = np.zeros_like(yy)
    for i, y in enumerate(yy):
        c = chord(y)
        if tc_mode == "cad":
            t_c = np.interp(y / B2, [0, .25, .5, .75, 1], [.07, .07, .06, .06, .06])
        else:
            t_c = ST.tc(y)
        x = np.linspace(xf * c + t_web, xr * c - t_web, 200)
        if shape == "profile":
            h = 2 * np.clip(_yt(x / c, t_c) * c - t_wall, 0, None)
        else:                                  # structures: dikdortgen, kiris yukseklikleri ortalamasi
            hm = 0.5 * (2 * _yt(xf, t_c) * c + 2 * _yt(xr, t_c) * c) - 2 * t_wall
            h = np.full_like(x, hm)
        A[i] = np.trapezoid(h, x)
        if caps:
            j = min(np.searchsorted(YS, y), len(YS) - 1)
            A[i] -= 2 * 2 * ws["w_cap"][j] * ws["n_ud"][j] * ST.MAT["UD"]["t_ply"]
    V = np.trapezoid(A, yy)
    if n_mid_ribs:
        ym = 0.5 * (y0 + y1)
        V -= n_mid_ribs * np.interp(ym, yy, A) * t_rib
    return V * 1e3


def tank_reconciliation(base):
    ws = base["ws"]
    fab = ST.MAT["FAB"]
    nf = ws["n_face"]
    t_face = nf * fab["t_ply"]
    t_seal = 0.15e-3
    t_skin_true = 2 * t_face + ST.MAT["CORE"]["t"] + t_seal           # sandvic kabuk + ic kaplama
    j = np.searchsorted(base["YS"], 0.5 * (ST.Y_T0 + ST.Y_T1))
    t_web_true = ws["n_web"][j] * fab["t_ply"] + t_seal
    t_rib_true = 3e-3 + 4 * fab["t_ply"] + t_seal                      # 3 mm cekirdek + 2x2 kat
    rows = []
    rows.append(("CAD raporu (cad_report.json, eta 0.06-0.55)", 0.715,
                 "CAD kati modeli: dis profil 2.6 mm iceri ofset, web 1.5 mm, uc kaburga 3 mm"))
    v1 = tank_volume(base, tc_mode="cad")
    rows.append(("CAD tanimi bu scriptte yeniden kuruldu (64A0xx, CAD loft t/c)", v1,
                 "dogrulama: CAD hacmini tekrar uretir"))
    v2 = tank_volume(base, tc_mode="params")
    rows.append(("+ t/c dogrusal 7->6 % (params/structures; CAD loftu eta 0.25'e kadar %7 tutuyor)", v2,
                 "CAD kesit yuvarlamasi (007,007,006..) icte kalin, eta>0.4'te ince: tank icinde net etki ~0"))
    v3 = tank_volume(base, t_wall=t_skin_true, t_web=t_web_true, t_rib=t_rib_true, tc_mode="params")
    rows.append((f"+ gercek duvarlar: kabuk {t_skin_true*1e3:.2f} mm (3 kat x2 + 2 mm kopuk + kaplama), "
                 f"web {t_web_true*1e3:.2f} mm, kaburga {t_rib_true*1e3:.2f} mm", v3, ""))
    v4 = tank_volume(base, t_wall=t_skin_true, t_web=t_web_true, t_rib=t_rib_true, tc_mode="params", caps=True)
    rows.append(("+ kiris kapaklari (UD, 2-3 kat, kutu genisliginin ~%65'i)", v4, ""))
    v5 = tank_volume(base, t_wall=t_skin_true, t_web=t_web_true, t_rib=t_rib_true, tc_mode="params", caps=True,
                     n_mid_ribs=1) - 0.010
    rows.append(("+ 1 orta bolme kaburgasi (tank_checks 2 bolme) + klunk/boru/nipel 10 cm3", v5,
                 "= fiziksel ic hacim (en iyi tahmin)"))
    v_rect = tank_volume(base, t_wall=t_skin_true - t_seal, t_web=ws["n_web"][j] * fab["t_ply"],
                         t_rib=0.0, eta=(ST.Y_T0 / B2, ST.Y_T1 / B2), tc_mode="params", caps=True,
                         shape="rect")
    rows.append(("structures tanimi (dikdortgen kutu, kiris yuks. ortalamasi, x0.95) - karsilastirma",
                 0.95 * v_rect, f"structures json: {ws['V_tank_half_L']:.3f} L (yt64 profil yaklasimi)"))
    unusable, fill = 0.05, 0.02
    usable = v5 * (1 - unusable - fill)
    rows.append((f"Kullanilabilir: fiziksel - %{unusable*100:.0f} kullanilamaz (ince duz tank, klunk) "
                 f"- %{fill*100:.0f} dolum/kabarcik payi", usable, "ONERILEN"))
    rec = math.floor(usable * 100) / 100
    return dict(rows=[dict(step=a, V_L=float(b), note=c) for a, b, c in rows], V_phys_L=v5, V_usable_L=usable,
                recommended_L=rec, m_recommended_kg=rec * FUEL["density"], t_skin_mm=t_skin_true * 1e3,
                params_L=FUEL["tanks"]["wing_integral_L_each"], structures_L=ws["V_tank_half_L"],
                structures_cap_L=base["ws_pre"]["V_tank_half_L"])


# ================================================================== grafikler
def plot_modes(fe, md, title, fn, n=5):
    beam = fe["beam"]
    sn = fe["sn"]
    y = beam["y_of_s"](sn)
    cref = chord(ST.Y0 + 0.7 * (B2 - ST.Y0))
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 7), sharex=True)
    for i in range(n):
        ph = md["Phi"][:, i]
        w, th = ph[0::3], ph[2::3]
        sc = max(np.abs(w).max(), np.abs(th * cref).max())
        sgn = np.sign(w[-1] if abs(w[-1]) > 1e-9 * sc else th[-1])
        lab = f"Mod {i+1}: {md['names'][i]} {md['f'][i]:.1f} Hz"
        a1.plot(y, sgn * w / sc, label=lab)
        a2.plot(y, sgn * th * cref / sc, label=lab)
    a1.set_ylabel("Egilme w / max (EA uzerinde)")
    a2.set_ylabel("Burulma phi * c_ref / max")
    a2.set_xlabel("y [m] (ankastre hat y = %.3f m)" % beam["y_clamp"])
    for a in (a1, a2):
        a.axhline(0, color="k", lw=.5)
        a.grid(alpha=.3)
    a1.legend(fontsize=8)
    a1.set_title(title, fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, fn), dpi=130)
    plt.close(fig)


def plot_vg(cases, fn):
    fig, axs = plt.subplots(2, 2, figsize=(11, 7.5), sharex=True)
    for col, (lab, r) in enumerate(cases):
        V, g, w = r["_curves"]
        for j in range(V.shape[1]):
            axs[0, col].plot(V[:, j] * 3.6, g[:, j], label=f"dal {j+1} ({r['names'][j]})")
            axs[1, col].plot(V[:, j] * 3.6, w[:, j] / 2 / math.pi)
        for a in axs[:, col]:
            a.axvline(V_REQ * 3.6, color="r", ls=":", label="gereksinim 1.2 V_D = 1080")
            a.axvline(V_D * 3.6, color="orange", ls=":", label="V_D 900")
            if math.isfinite(r["Vf_kmh"]):
                a.axvline(r["Vf_kmh"], color="k", ls="--", label=f"flutter {r['Vf_kmh']:.0f} km/h")
            a.grid(alpha=.3)
            a.set_xlim(0, 4000)
        axs[0, col].axhline(0, color="k", lw=.5)
        axs[0, col].axhline(0.02, color="g", lw=.5, ls="--")
        axs[0, col].set_ylim(-0.6, 0.3)
        axs[1, col].set_ylim(0, 450)
        axs[0, col].set_title(f"{lab}: V_F = {r['Vf_kmh']:.0f} km/h ({r['ff_Hz']:.0f} Hz), "
                              f"V_div = {r['Vdiv_kmh']:.0f} km/h", fontsize=9)
        axs[1, col].set_xlabel("Hiz [km/h] (Mach eslestirmeli beta, M_n<=0.9)")
        axs[0, col].legend(fontsize=7, loc="lower left")
    axs[0, 0].set_ylabel("Gereken yapisal sonum g")
    axs[1, 0].set_ylabel("Frekans [Hz]")
    fig.suptitle("HIZ-750 kanat modal flutter (FE %d mod, serit Theodorsen, p-k yontemi, ok acisi dahil)" % cases[0][1]["n_modes"],
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, fn), dpi=130)
    plt.close(fig)


# ================================================================== ana akis
def main():
    os.makedirs(OUT, exist_ok=True)
    base = ST.wing_section_model()
    ws = base["ws"]
    RES["model"] = dict(y_clamp=Y_CLAMP, Y0_structures=ST.Y0, n_elem=NE, n_modes_flutter=N_MODES_FLUTTER,
                        sweep_EA_deg=math.degrees(LAM_EA), cosL=math.cos(LAM_EA), a=A_EA, b_ref=b_ref_default(),
                        layup=[ws["n_face"], ws["n_aft"]], m_wing_kg=ws["m_wing"],
                        servos=[dict(name=n, m=m, y=y, xc=xc) for n, m, y, xc in SERVOS],
                        m_fuel_half_structures=base["m_fuel_half"])

    # ---- dogrulama
    RES["validation_uniform"] = validate_uniform()
    RES["validation_goland"] = validate_goland()

    # ---- tank hacmi (FE 'dolu' durumunda onerilen kullanilabilir yakit kullanilir)
    tank = tank_reconciliation(base)
    RES["tank"] = tank
    m_fuel = tank["m_recommended_kg"]
    RES["model"]["m_fuel_half_FE"] = m_fuel

    # ---- temel durum: dolu / bos
    base_cases = {}
    for fuel in (True, False):
        sec = section_data(base, fuel=fuel, m_fuel_half=m_fuel)
        r = analyse(sec, want_curves=True)
        base_cases["dolu" if fuel else "bos"] = r
    for k, r in base_cases.items():
        plot_modes(r["_fe"], r["_md"], f"HIZ-750 yari kanat FE modlari (tank {k}, 3/1 kat, EA ok {math.degrees(LAM_EA):.1f} deg)",
                   f"fe_mod_sekilleri_{k}.png")
    plot_vg([("Tank dolu", base_cases["dolu"]), ("Tank bos", base_cases["bos"])], "fe_flutter_Vg.png")
    # mod sayisi yakinsamasi
    conv = {}
    for nm in (4, 6, 8, 10):
        sec = section_data(base, fuel=True, m_fuel_half=m_fuel)
        conv[nm] = analyse(sec, nm=nm)["Vf_kmh"]
    RES["mode_convergence_dolu"] = conv

    # ---- 2-DOF (structures) referansi
    two = {}
    for fuel in (True, False):
        wh, wa = ST.rayleigh_freqs(ws, fuel)
        sp = ST.section_params(ws, wh, wa, 0.70, fuel)
        two["dolu" if fuel else "bos"] = dict(Vf_kmh=ST.flutter_dimensional(sp) * 3.6, f_h=wh / 2 / math.pi,
                                              f_a=wa / 2 / math.pi, xcg=sp["xcg"], xa=sp["xa"], mu=sp["mu"])
    RES["two_dof"] = two

    # ---- farki adim adim aciklama (tank dolu)
    steps = []
    sec_ns = section_data(base, fuel=True, sweep=False)          # structures yakit kutlesi (0.49 kg)
    steps.append(("A: 2-DOF tipik kesit (structures, eta 0.70, Rayleigh frekanslari)", dict(
        Vf_kmh=two["dolu"]["Vf_kmh"], Vdiv_kmh=ST.divergence(ws) * 3.6,
        f_Hz=[two["dolu"]["f_h"], float("nan"), two["dolu"]["f_a"]])))
    steps.append(("B: FE, structures ile ayni varsayimlar (ok yok, y0 = %.0f mm, servo yok, yakit %.2f kg)"
                  % (ST.Y0 * 1e3, base["m_fuel_half"]),
                  analyse(sec_ns, y_clamp=ST.Y0, servos=[], slope=False)))
    steps.append(("C: + ankastre hat civata hattinda (y = 35 mm)", analyse(sec_ns, servos=[], slope=False)))
    sec_sw = section_data(base, fuel=True, sweep=True)
    steps.append(("D: + ok acisi: dik kesit kutle/GJ, V_n = V cosL, M_n = M cosL", analyse(sec_sw, servos=[], slope=False)))
    steps.append(("E: + ok acisi egilme-egimi terimi (alpha = phi - tanL w')", analyse(sec_sw, servos=[], slope=True)))
    steps.append(("F: + aileron/flap servolari (2 x 0.12 kg/yari)", analyse(sec_sw, slope=True)))
    sec_b = section_data(base, fuel=True, m_fuel_half=m_fuel)
    steps.append(("G: + onerilen kullanilabilir tank yakiti (%.2f kg/yari) = TEMEL" % m_fuel,
                  analyse(sec_b, slope=True)))
    RES["steps"] = [dict(step=a, Vf_kmh=b["Vf_kmh"], Vdiv_kmh=b["Vdiv_kmh"],
                         f_Hz=[float(x) for x in b["f_Hz"][:3]]) for a, b in steps]

    # ---- servo konumu duyarliligi
    serv = []
    for lab, sv in (("temel: aileron servosu y 0.34, 0.60c", SERVOS),
                    ("aileron servosu 0.06 kg (ince kanat servosu)", [("a", 0.06, 0.34, 0.60), SERVOS[1]]),
                    ("aileron servosu koke (y 0.10, 0.65c) + tork cubugu", [("a", M_SERVO, 0.10, 0.65), SERVOS[1]]),
                    ("aileron servosu aileron ortasinda (y 0.53, 0.65c)", [("a", M_SERVO, 0.53, 0.65), SERVOS[1]])):
        rr = {}
        for fuel in (True, False):
            rr["dolu" if fuel else "bos"] = analyse(section_data(base, fuel=fuel, m_fuel_half=m_fuel), servos=sv)["Vf_kmh"]
        serv.append(dict(case=lab, **rr))
    RES["servo_sensitivity"] = serv

    # ---- duyarlilik: CG ve GJ
    x70 = float(np.interp(ST.Y0 + 0.7 * (B2 - ST.Y0), base["YS"], ws["xcg"]))
    sens = []
    for xt in (0.42, 0.45, 0.48, 0.52):
        for gf in (0.8, 1.0, 1.2):
            row = dict(xcg=xt, gj=gf)
            for fuel in (True, False):
                key = "dolu" if fuel else "bos"
                sec = section_data(base, fuel=fuel, m_fuel_half=m_fuel, xcg_shift=xt - x70, gj_fac=gf)
                r = analyse(sec)
                row[f"fe_{key}"] = r["Vf_kmh"]
                row[f"fe_{key}_div"] = r["Vdiv_kmh"]
                row[f"fe_{key}_f"] = r["f_Hz"][:3]
                ws2 = dict(ws, xcg=ws["xcg"] + xt - x70)
                wh, wa = ST.rayleigh_freqs(ws2, fuel)
                wa *= math.sqrt(gf)
                sp = ST.section_params(ws2, wh, wa, 0.70, fuel)
                row[f"two_{key}"] = ST.flutter_dimensional(sp) * 3.6
            sens.append(row)
    RES["sensitivity"] = sens
    RES["xcg70_base"] = x70
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    xs = [0.42, 0.45, 0.48, 0.52]
    for ax, key in zip(axs, ("dolu", "bos")):
        for gf, ls in ((0.8, ":"), (1.0, "-"), (1.2, "--")):
            ax.plot(xs, [r[f"fe_{key}"] for r in sens if r["gj"] == gf], "b" + ls, marker="o",
                    label=f"FE modal, GJ x{gf}")
            ax.plot(xs, [r[f"two_{key}"] for r in sens if r["gj"] == gf], "m" + ls, marker="s", ms=4,
                    label=f"2-DOF, GJ x{gf}")
        ax.axhline(V_REQ * 3.6, color="r", ls=":", label="gereksinim 1080 km/h")
        ax.axhline(V_REQ * 3.6 * MODEL_FACTOR, color="r", lw=.6, ls="-.", label="x1.25 model payi 1350")
        ax.axvline(x70, color="k", lw=.5)
        ax.set_xlabel("Kesit CG x/c (eta 0.70'ta; tum aciklik ayni kaydirma)")
        ax.set_title(f"Tank {key}", fontsize=10)
        ax.grid(alpha=.3)
    axs[0].set_ylabel("Flutter hizi [km/h]")
    axs[0].set_ylim(600, 2600)
    axs[1].legend(fontsize=7, ncol=2)
    fig.suptitle("Flutter hizinin kesit CG ve GJ duyarliligi (FE modal vs 2-DOF)", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fe_duyarlilik.png"), dpi=130)
    plt.close(fig)

    # ---- GVT: modal frekans olcekleme haritasi
    gvt = {}
    fac = np.round(np.arange(0.7, 1.501, 0.1), 3)   # 1.0 izgarada
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
    for ax, key in zip(axs, ("dolu", "bos")):
        r = base_cases[key]
        md, Dq, bref, beam = r["_md"], r["_Dq"], r["_bref"], r["_beam"]
        nmf = r["n_modes"]
        om = md["omega"][:nmf]
        is_t = md["tors"][:nmf] > 0.5
        grid = np.zeros((len(fac), len(fac)))
        for i, fb in enumerate(fac):
            for j, ft in enumerate(fac):
                sc = np.where(is_t, ft, fb)
                grid[j, i] = flutter_solve(om, Dq, bref, beam["cosL"], fscale=sc)[0] * 3.6
        f1b = md["f"][0]
        f1t = [f for f, t in zip(md["f"], md["tors"]) if t > 0.5][0]
        X, Y = np.meshgrid(fac * f1b, fac * f1t)
        cs = ax.contourf(X, Y, np.clip(grid, 0, 3000), levels=np.arange(600, 3001, 200), cmap="RdYlGn")
        c1 = ax.contour(X, Y, grid, levels=[V_REQ * 3.6, V_REQ * 3.6 * MODEL_FACTOR], colors=["k", "k"],
                        linestyles=["-", "--"])
        ax.clabel(c1, fmt={V_REQ * 3.6: "1080", V_REQ * 3.6 * MODEL_FACTOR: "1350"}, fontsize=8)
        ax.plot(f1b, f1t, "k*", ms=12, label="FE tahmini")
        ax.set_xlabel("1B egilme frekansi [Hz]")
        ax.set_title(f"Tank {key}: V_F [km/h] (1B/2B birlikte, 1T ayri olceklendi)", fontsize=9)
        ax.legend(fontsize=8)
        fig.colorbar(cs, ax=ax)
        # kabul sinirlari
        i1 = np.argmin(np.abs(fac - 1.0))
        col_t = grid[:, i1]            # f_B nominal, f_T degisken
        row_b = grid[i1, :]

        def fmin(vals, target):
            """f_T olcek carpani: bunun ustunde V_F >= hedef kalir (dogrusal ara degerleme)."""
            v = np.where(np.isfinite(vals), vals, 1e5)
            ok = v >= target
            if ok.all():
                return float(fac[0])
            k = int(np.where(~ok)[0][-1])
            if k == len(fac) - 1:
                return float("nan")
            return float(fac[k] + (target - v[k]) / (v[k + 1] - v[k]) * (fac[k + 1] - fac[k]))
        gvt[key] = dict(f1B=float(f1b), f1T=float(f1t), f=[float(x) for x in md["f"][:5]], names=md["names"][:5],
                        fT_min_fac_1080=fmin(col_t, V_REQ * 3.6),
                        fT_min_fac_1350=fmin(col_t, V_REQ * 3.6 * MODEL_FACTOR),
                        fB_min_fac_1080=fmin(row_b, V_REQ * 3.6),
                        Vf_vs_fT=col_t.tolist(), Vf_vs_fB=row_b.tolist(), fac=fac.tolist(),
                        grid=grid.tolist())
    axs[0].set_ylabel("1T burulma frekansi [Hz]")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fe_gvt_harita.png"), dpi=130)
    plt.close(fig)
    RES["gvt"] = gvt

    # ---- kaydet
    RES["base"] = {k: {kk: vv for kk, vv in r.items() if not kk.startswith("_")} for k, r in base_cases.items()}

    def conv_(o):
        if isinstance(o, dict):
            return {str(k): conv_(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [conv_(v) for v in o]
        if isinstance(o, (np.floating, np.integer, np.bool_)):
            return o.item()
        if isinstance(o, np.ndarray):
            return conv_(o.tolist())
        if isinstance(o, float) and not math.isfinite(o):
            return None
        return o
    with open(os.path.join(OUT, "fe_sonuclar.json"), "w", encoding="utf-8") as f:
        json.dump(conv_(RES), f, indent=1, ensure_ascii=False)

    # ---- konsol ozeti
    m = RES["model"]
    print(f"Model: ankastre y={m['y_clamp']} m, EA ok {m['sweep_EA_deg']:.1f} deg, {NE} eleman, yakit/yari FE "
          f"{m['m_fuel_half_FE']:.3f} kg (structures {m['m_fuel_half_structures']:.3f})")
    vu = RES["validation_uniform"]
    print("Dogrulama uniform:", [round(x["err_pct"], 4) for x in vu["bending"] + vu["torsion"]], "% hata")
    vg = RES["validation_goland"]
    print(f"Goland: I tanimi {vg['I_definition']}, w = {vg[vg['I_definition']]['omega']}, "
          f"V_F(2/4/6 mod) = {vg['flutter_2modes']['Vf']:.1f}/{vg['flutter_4modes']['Vf']:.1f}/"
          f"{vg['flutter_6modes']['Vf']:.1f} m/s (p-k), w_F = {vg['flutter_4modes']['wf']:.1f} rad/s; k-yontemi "
          f"{vg['flutter_4modes']['Vf_k']:.1f} m/s {vg['flutter_4modes']['wf_k']:.1f} rad/s; diger tanim "
          f"{vg['cg' if vg['I_definition']=='ea' else 'ea']['omega']}")
    for k, r in base_cases.items():
        print(f"Tank {k}: f = {[round(x, 1) for x in r['f_Hz'][:6]]} Hz {r['names'][:5]}")
        print(f"   V_F = {r['Vf_kmh']:.0f} km/h ({r['ff_Hz']:.0f} Hz, dal {r['branch']}), g=0.02: {r['Vf_g02_kmh']:.0f}, "
              f"M sabit 0.88: {r['Vf_Mfix_kmh']:.0f}, V_div = {r['Vdiv_kmh']:.0f} km/h")
    print("Mod yakinsamasi (dolu):", conv)
    print("2-DOF:", {k: round(v["Vf_kmh"]) for k, v in two.items()})
    for s in RES["steps"]:
        print(f"   {s['step']}: Vf={s['Vf_kmh']:.0f} Vdiv={s['Vdiv_kmh']:.0f} f={[round(x,1) for x in s['f_Hz']]}")
    for s in serv:
        print(f"   servo {s['case']}: dolu {s['dolu']:.0f} bos {s['bos']:.0f}")
    print(f"Duyarlilik (x70 temel {x70:.3f}):")
    rnd = lambda L: [round(x) if math.isfinite(x) else None for x in L]
    for r in sens:
        print(f"   xcg {r['xcg']:.2f} GJ x{r['gj']}: FE dolu {r['fe_dolu']:.0f} bos {r['fe_bos']:.0f} | "
              f"2-DOF dolu {r['two_dolu']:.0f} bos {r['two_bos']:.0f} | f1B,f2,f3 {[round(x) for x in r['fe_dolu_f']]}")
    for k, v in gvt.items():
        print(f"GVT {k}: f1B {v['f1B']:.1f} f1T {v['f1T']:.1f}; fT_min/fT (1080) {v['fT_min_fac_1080']}, (1350) "
              f"{v['fT_min_fac_1350']}; Vf(fB) {rnd(v['Vf_vs_fB'])}")
        print(f"     Vf(fT) {rnd(v['Vf_vs_fT'])}")
    print("Tank:")
    for r in tank["rows"]:
        print(f"   {r['V_L']:.3f} L  {r['step']}  {r['note']}")
    print(f"   oneri {tank['recommended_L']:.2f} L ({tank['m_recommended_kg']:.3f} kg)")


if __name__ == "__main__":
    main()
