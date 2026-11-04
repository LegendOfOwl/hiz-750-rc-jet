"""
HIZ-750 - yapi, flutter ve kontrol yuzeyi analizi (iterasyon 3).

iter3: alcak kanat (z_root -0.065) -> tek parca kanat, govde icinden gecen kutu (carry-through),
kiris cercevelerine civatali baglanti + karin kaplamasi; tek yarikli flap ray/mentese yukleri;
elevator cf 0.22; kizak 1.45 m'ye uzadi (motor alti isi). iter2: structures_iter2.py / out_iter2/.

iter2: tek hucre hucum kenari -> arka kiris (0.55c), EA 0.30c, kanat koku entegre yakit
tanki (yakit egilme rahatlatmasi, tam/bos flutter), govde alti kizak inisi, iki parcali
yatay kuyruk kok baglantisi. iter1 hali: structures_iter1.py / out_iter1/.

Calistir:  C:/Users/Urungu/.hz750/Scripts/python structures/structures.py
Ciktilar:  structures/out/*.png + structures/out/sonuclar.json + konsol ozeti

Bolumler:
  1. V-n diyagrami (manevra + ruzgar hamlesi, CS-23 Pratt formulu)
  2. Schrenk acikliksal yuk, kesme / egilme / burulma (nihai)
  3. Kiris kapak + gövde (web) + kabuk kat plani, EI / GJ, kanat kutlesi
  4. Govde kabugu, motor yatagi, kanat-govde baglantisi
  5. Flutter (Theodorsen 2-DOF tipik kesit, k-yontemi), diverjans, kontrol yuzeyi balansi
  6. Mentese momentleri (ince profil teorisi) ve servo secimi
Tum varsayimlar bu dosyada sabit olarak belgelidir; params.py degistirilmez.
"""
import json
import math
import os
import sys

import numpy as np
from scipy.special import hankel2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from params import (WING, HTAIL, VTAIL, FUSELAGE, ENGINE, MASS_ITEMS, FUEL, GEAR, V_OPER_MAX, V_D,  # noqa: E402
                    V_FLUTTER_REQ, N_LIMIT, N_NEG, SF, wing_geom, surface_geom, vtail_geom,
                    mass_summary)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
G = 9.80665
RHO0 = 1.225
A_SOUND = 340.3
RES = {}
# Rayleigh (ust sinir frekans) + tipik kesit yaklasimi belirsizligi icin ek carpan
FLUTTER_MODEL_FACTOR = 1.25

# ------------------------------------------------------------------ malzeme (T700/epoksi, vakum torba, oda/60C kur)
MAT = dict(
    UD=dict(E1=125e9, Xt=2100e6, Xc=1200e6, rho=1550.0, t_ply=0.20e-3,   # 200 g/m2 UD, Vf~0.55
            note="T700S/epoksi UD 200 g/m2"),
    FAB=dict(E=55e9, G45=25e9, rho=1500.0, t_ply=0.178e-3, areal_dry=0.160,  # 160 g/m2 dokuma, Vf~0.5
             tau_allow=80e6, note="T300 3K dokuma 160 g/m2, +-45 yonlu"),
    FAB200=dict(E_qi=45e9, rho=1500.0, t_ply=0.22e-3, note="200 g/m2 dokuma, quasi-izotrop govde"),
    CORE=dict(rho=52.0, t=2.0e-3, note="Rohacell 51 IG-F 2 mm"),
)
# tasarim izin degerleri: deneysel/cevre (0.80) x imalat (0.80) x istatistik B-basis (0.85) = 0.544
KD = 0.80 * 0.80 * 0.85
EPS_ALLOW = 0.0040                           # nihai yukte izin verilen birim sekil degistirme
SIG_CAP = min(EPS_ALLOW * MAT["UD"]["E1"], KD * MAT["UD"]["Xc"])   # = 500 MPa (basma kapagi)
SIG_FUS = 0.0040 * MAT["FAB200"]["E_qi"]                          # = 180 MPa

wg = wing_geom()
B2 = wg["b"] / 2
# alcak kanat: kanat orta duzlemi z_root'da govde yan yuzu yari genisligi (acikta kalan kanat koku)
Y0 = math.sqrt(max((FUSELAGE["d_max"] / 2) ** 2 - WING["z_root"] ** 2, 0.02 ** 2))
X_EA = 0.30                                  # elastik eksen: tek hucre (HK -> arka kiris) kesme merkezi
XS_F, XS_R = WING["spar_xc"]
X_SEC_CG = 0.42                              # yapisal kesit agirlik merkezi (kabuk+kiris+dengeli aileron)
# entegre kanat tanki (her yari)
_T = FUEL.get("tanks", {})
ETA_T = _T.get("wing_eta", (0.06, 0.40))
Y_T0 = max(ETA_T[0] * B2, Y0)
Y_T1 = ETA_T[1] * B2
M_WT_HALF_PARAMS = _T.get("wing_integral_L_each", 0.9) * FUEL["density"]
M_WT_HALF = M_WT_HALF_PARAMS               # main() icinde gercek tank kapasitesiyle sinirlanir
X_FUEL_C = 0.5 * (XS_F + XS_R)              # tank yakit agirlik merkezi (veter orani)
MS = mass_summary(1.0)
M_TO = MS["m"]
W = M_TO * G
S = WING["S"]


def chord(y):
    return wg["cr"] * (1 - (1 - WING["taper"]) * y / B2)


def tc(y):
    return WING["tc_root"] + (WING["tc_tip"] - WING["tc_root"]) * y / B2


def lift_slope(M, AR=WING["AR"], sweep_half=None):
    """DATCOM kanat CL_alpha [1/rad]."""
    if sweep_half is None:
        # yari-veter ok acisi
        tan_le = math.tan(math.radians(WING["sweep_le"]))
        sweep_half = math.atan(tan_le - 0.5 * (wg["cr"] - wg["ct"]) / B2)
    beta2 = 1 - M * M
    eta = 0.95
    return 2 * math.pi * AR / (2 + math.sqrt(4 + AR ** 2 * beta2 / eta ** 2 *
                                             (1 + math.tan(sweep_half) ** 2 / beta2)))


# ================================================================== 1. V-n
def vn_diagram():
    CLmax, CLmin = 1.0, -0.7
    VS = math.sqrt(2 * W / (RHO0 * S * CLmax))
    VA = VS * math.sqrt(N_LIMIT)
    VC, VD = V_OPER_MAX, V_D
    a = lift_slope(VC / A_SOUND)
    cbar = S / wg["b"]
    mu = 2 * (W / S) / (RHO0 * cbar * a * G)
    Kg = 0.88 * mu / (5.3 + mu)

    def ngust(U, V):
        return Kg * RHO0 * U * V * a / (2 * W / S)

    gusts = {"CS-23 (15.24/7.62 m/s)": (15.24, 7.62), "Operasyonel sinir (7.62/3.81 m/s)": (7.62, 3.81)}
    V = np.linspace(0, VD, 400)
    npos = np.minimum(RHO0 * V ** 2 * S * CLmax / (2 * W), N_LIMIT)
    nneg = np.maximum(RHO0 * V ** 2 * S * CLmin / (2 * W), N_NEG)
    # CS-23: negatif cizgi VC'den VD'de 0'a dogrusal
    nneg = np.where(V > VC, N_NEG * (VD - V) / (VD - VC), nneg)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(V * 3.6, npos, "b", lw=2, label="Manevra zarfi")
    ax.plot(V * 3.6, nneg, "b", lw=2)
    ax.plot([VD * 3.6, VD * 3.6], [0, N_LIMIT], "b", lw=2)
    res = {}
    for (name, (Uc, Ud)), col in zip(gusts.items(), ("r", "g")):
        nc, nd = ngust(Uc, VC), ngust(Ud, VD)
        ax.plot([0, VC * 3.6, VD * 3.6], [1, 1 + nc, 1 + nd], col + "--", label=f"Hamle {name}")
        ax.plot([0, VC * 3.6, VD * 3.6], [1, 1 - nc, 1 - nd], col + "--")
        res[name] = dict(n_VC=1 + nc, n_VD=1 + nd, n_VC_neg=1 - nc)
    for v, lab in ((VS, "VS"), (VA, "VA"), (VC, "VC"), (VD, "VD")):
        ax.axvline(v * 3.6, color="k", lw=.5, ls=":")
        ax.text(v * 3.6, N_LIMIT + 0.6, lab, ha="center", fontsize=8)
    ax.set_xlabel("EAS [km/h]")
    ax.set_ylabel("Yuk faktoru n")
    ax.set_title(f"HIZ-750 V-n diyagrami (m={M_TO:.1f} kg, W/S={W/S:.0f} Pa)")
    ax.set_ylim(-14, 20)
    ax.grid(alpha=.3)
    ax.legend(fontsize=8, loc="lower left")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "vn_diyagrami.png"), dpi=130)
    plt.close(fig)
    RES["vn"] = dict(VS=VS, VA=VA, VC=VC, VD=VD, CLa=a, mu_g=mu, Kg=Kg, gust=res)
    return RES["vn"]


# ================================================================== 2. aciklik yukleri
NY = 200
YS = np.linspace(0, B2, NY)


def schrenk(n, Wt=None):
    Wt = W if Wt is None else Wt
    c = chord(YS)
    ce = 4 * S / (math.pi * wg["b"]) * np.sqrt(np.clip(1 - (YS / B2) ** 2, 0, 1))
    cs = 0.5 * (c + ce)
    return n * Wt * cs / S            # [N/m], yari kanat integrali = nW/2


def fuel_per_span(m_half=None):
    """Entegre tank yakiti [kg/m]: kutu alani ~ c^2 ile orantili, Y_T0..Y_T1 arasi."""
    m_half = M_WT_HALF if m_half is None else m_half
    f = np.where((YS >= Y_T0) & (YS <= Y_T1), chord(YS) ** 2, 0.0)
    return f * m_half / np.trapezoid(f, YS)


def integrate_out(f):
    """F(y) = int_y^{b/2} f dy"""
    out = np.zeros_like(f)
    for i in range(NY - 2, -1, -1):
        out[i] = out[i + 1] + 0.5 * (f[i] + f[i + 1]) * (YS[i + 1] - YS[i])
    return out


def thin_airfoil_flap(E, alpha=0.0, delta=1.0, nterms=400):
    """Ince profil teorisi: flap veter orani E icin cl, cm_c/4, Ch (mentese, veter E*c ile).
    Isaret: delta pozitif = firar kenari asagi, Ch pozitif = firar kenarini asagi iten."""
    th_h = math.acos(1 - 2 * (1 - E))          # menteseye karsilik gelen Glauert acisi
    A0 = alpha + delta * (math.pi - th_h) / math.pi
    n = np.arange(1, nterms + 1)
    An = 2 * delta / math.pi * np.sin(n * th_h) / n
    cl = math.pi * (2 * A0 + An[0])
    cm4 = -math.pi / 4 * (An[0] - An[1])
    th = np.linspace(th_h, math.pi - 1e-6, 4000)
    xi = 0.5 * (1 - np.cos(th))
    dcp = 4 * (A0 * (1 + np.cos(th)) / np.sin(th) + (An[:, None] * np.sin(n[:, None] * th)).sum(0))
    dxi = 0.5 * np.sin(th)
    xh = 1 - E
    integ = dcp * (xi - xh) * dxi
    mh = np.trapezoid(integ, th)
    Ch = -mh / E ** 2
    return cl, cm4, Ch


def span_loads(plot=True):
    """Uc yukleme durumu: (A) MTOW, yakit rahatlatmasi yok (iter1 yontemi, referans),
    (B) MTOW + kanat tanki dolu (yakit ataleti egilmeyi azaltir),
    (C) kanat tanklari bos, govde tanki dolu (rahatlatma yok, W daha dusuk).
    Boyutlandirma zarfi = max(B, C)."""
    n_ult = N_LIMIT * SF
    c = chord(YS)
    mf = fuel_per_span()
    W_C = W - 2 * M_WT_HALF * G
    cases = {
        "A: MTOW, rahatlatma yok (iter1)": (n_ult, W, np.zeros(NY)),
        "B: MTOW, kanat tanki dolu": (n_ult, W, mf),
        "C: kanat tanki bos": (n_ult, W_C, np.zeros(NY)),
    }
    qD = 0.5 * RHO0 * V_D ** 2
    cm0 = -0.005
    ail = WING["aileron"]
    cl_d, cm_d, _ = thin_airfoil_flap(ail["cf"], 0.0, 1.0)
    eff = 0.70
    d = math.radians(ail["defl_max_hs"])
    in_ail = (YS >= ail["eta0"] * B2) & (YS <= ail["eta1"] * B2)
    dT = np.where(in_ail, qD * c ** 2 * eff * (cm_d + cl_d * (X_EA - 0.25)) * d, 0.0)

    def torsion(n, Wt, mfc, extra=0.0):
        # kaldirma c/4'te (EA onunde -> burun yukari), yakit atalet yuku EA arkasinda (burun asagi)
        return integrate_out(schrenk(n, Wt) * (X_EA - 0.25) * c - n * G * mfc * (X_FUEL_C - X_EA) * c
                             + qD * c ** 2 * cm0 + extra)

    out = {}
    for name, (n, Wt, mfc) in cases.items():
        q = schrenk(n, Wt) - n * G * mfc
        V = integrate_out(q)
        M = integrate_out(V)
        T1 = torsion(n, Wt, mfc)
        T2 = SF * torsion(2 / 3 * N_LIMIT, Wt, mfc, dT)
        out[name] = dict(V=V, M=M, T1=T1, T2=T2)
    kB, kC = "B: MTOW, kanat tanki dolu", "C: kanat tanki bos"
    V = np.maximum(out[kB]["V"], out[kC]["V"])
    M = np.maximum(out[kB]["M"], out[kC]["M"])
    T = np.max(np.abs(np.array([out[k][t] for k in (kB, kC) for t in ("T1", "T2")])), axis=0)
    if not plot:   # iter4: fe_modal.py yardimcisi grafik yazmadan cagirir
        return out, V, M, T
    fig, axs = plt.subplots(3, 1, figsize=(8, 9), sharex=True)
    for name, o in out.items():
        axs[0].plot(YS, o["V"], label=name)
        axs[1].plot(YS, o["M"], label=name)
        axs[2].plot(YS, o["T1"], label=f"{name[:1]}: n_ult @VD")
        axs[2].plot(YS, o["T2"], ls="--", label=f"{name[:1]}: aileron + 2/3 n_lim")
    axs[0].set_ylabel("Kesme V [N]")
    axs[1].set_ylabel("Egilme M [N.m]")
    axs[2].set_ylabel("Burulma T [N.m]")
    axs[0].legend(fontsize=7)
    axs[2].legend(fontsize=6, ncol=2)
    for a in axs:
        a.axvline(Y0, color="k", ls=":", lw=.7)
        a.axvspan(Y_T0, Y_T1, color="orange", alpha=.12)
        a.grid(alpha=.3)
    axs[2].set_xlabel("y [m] (turuncu = entegre tank, nokta cizgi = govde yan yuzu)")
    axs[0].set_title(f"Yari kanat nihai yukleri (Schrenk, n_ult={n_ult:.0f})")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "kanat_yukleri.png"), dpi=130)
    plt.close(fig)
    i0 = np.searchsorted(YS, Y0)
    RES["loads"] = dict(n_ult=n_ult, V_root=V[0], M_root=M[0], V_side=V[i0], M_side=M[i0],
                        T_root_case1=float(max(abs(out[k]["T1"][0]) for k in (kB, kC))),
                        T_root_case2=float(max(abs(out[k]["T2"][0]) for k in (kB, kC))),
                        cl_delta=cl_d, cm_delta=cm_d,
                        cases={k: dict(M_root=float(o["M"][0]), M_side=float(o["M"][i0]),
                                       V_root=float(o["V"][0]),
                                       T_root=float(max(abs(o["T1"][0]), abs(o["T2"][0]))))
                               for k, o in out.items()})
    return None, V, M, T


# ================================================================== 3. kiris + kabuk
def yt64(x, t_c):
    """64A-benzeri kalinlik dagilimi (max 0.40c): NACA 4-serisi formulu x ekseninde gerilerek.
    Donus: yari kalinlik / veter."""
    x = np.asarray(x, dtype=float)
    xp = np.where(x <= 0.4, x * 0.3 / 0.4, 0.3 + (x - 0.4) * 0.7 / 0.6)
    return 5 * t_c * (0.2969 * np.sqrt(xp) - 0.1260 * xp - 0.3516 * xp ** 2 + 0.2843 * xp ** 3
                      - 0.1036 * xp ** 4)


def cell_props(t_c, x_end=None):
    """Tek hucre (hucum kenari -> x_end), c=1: kabuk cevresi, kapali alan, arka web yuksekligi."""
    x_end = XS_R if x_end is None else x_end
    x = np.linspace(0, 1, 400) ** 2 * x_end
    yt = yt64(x, t_c)
    per = 2 * np.sum(np.hypot(np.diff(x), np.diff(yt)))
    area = 2 * np.trapezoid(yt, x)
    return per, area, 2 * float(yt64(x_end, t_c))


def size_wing(M, V, T, n_face_plies, n_aft=None):
    ud, fab, core = MAT["UD"], MAT["FAB"], MAT["CORE"]
    c = chord(YS)
    t_c = tc(YS)
    t_face = n_face_plies * fab["t_ply"]
    t_skin = 2 * t_face                                 # iki yuz toplam (kesme tasiyan)
    hf = 2 * yt64(XS_F, t_c) * c
    hr = 2 * yt64(XS_R, t_c) * c
    h_box = 0.5 * (hf + hr) - 2 * (2 * t_face + core["t"])   # kapaklar arasi net
    w_cap = np.clip(0.050 * c / wg["cr"], 0.010, 0.050)
    A_req = np.zeros(NY)
    n_ud = np.zeros(NY, dtype=int)
    for i in range(NY):
        A = 1e-6
        for _ in range(20):
            t_cap = A / (2 * w_cap[i])
            h_eff = max(h_box[i] - t_cap, 1e-3)
            A = M[i] / (h_eff * SIG_CAP)
        A_req[i] = A
        n_ud[i] = max(2, math.ceil(A / (2 * w_cap[i]) / ud["t_ply"]))
    t_cap = n_ud * ud["t_ply"]
    A_cap = 2 * w_cap * t_cap                           # bir yuzey (on+arka kiris)
    h_eff = h_box - t_cap
    EI = ud["E1"] * 2 * A_cap * (h_eff / 2) ** 2
    EI += 12e9 * 2 * ((XS_R - XS_F) * c) * t_skin / 2 * (h_eff / 2) ** 2
    n_web = np.zeros(NY, dtype=int)
    for i in range(NY):
        for nw in range(2, 12):
            tw = nw * fab["t_ply"]
            tau = abs(V[i]) / (2 * h_box[i] * tw)
            tau_cr = 5.0 * fab["E"] * 0.8 * (tw / h_box[i]) ** 2
            if tau <= fab["tau_allow"] * 0.8 and tau <= tau_cr:
                break
        n_web[i] = nw
    # burulma: tek hucre HK -> arka kiris, Bredt-Batho (kabuk + arka web); kiris arkasi kabuk
    # kontrol yuzeyi kesikleri nedeniyle burulma tasimaz kabul edilir (iter1'de tum profil sayilmisti)
    cp = np.array([cell_props(t) for t in t_c])
    per, ar, hw = cp[:, 0] * c, cp[:, 1] * c ** 2, cp[:, 2] * c
    t_web = n_web * fab["t_ply"]
    GJ = 4 * ar ** 2 * fab["G45"] / (per / t_skin + hw / t_web)
    tau_skin = T / (2 * ar * t_skin)
    per_full = np.array([cell_props(t, 1.0)[0] for t in t_c]) * c
    sel = YS >= Y0
    yy = YS[sel]
    # kesit kutle bilesenleri ve agirlik merkezi (iter3): kiris arkasi kabuk n_aft kat/yuz olabilir
    n_aft = n_face_plies if n_aft is None else n_aft
    lam = lambda n: 2 * n * fab["areal_dry"] / 0.60 + core["rho"] * core["t"] + 0.10
    m_sk_f = lam(n_face_plies) * per
    m_sk_a = lam(n_aft) * (per_full - per)
    m_caps = 2 * A_cap * ud["rho"]
    m_webs = 2 * n_web * fab["t_ply"] * h_box * fab["rho"] * 1.3
    m_ribs = 0.08 * c / wg["cr"]
    ail = WING["aileron"]
    in_ail = (YS >= ail["eta0"] * B2) & (YS <= ail["eta1"] * B2)
    m_bal = np.where(in_ail, 0.023 / ((ail["eta1"] - ail["eta0"]) * B2), 0.0)
    x_sk_f = 0.30 * XS_R / 0.55                           # HK -> arka kiris kabuk cevresi agirlik merkezi
    x_sk_a = 0.5 * (XS_R + 1.0)
    num = (m_sk_f * x_sk_f + m_sk_a * x_sk_a + m_caps * 0.5 * (XS_F + XS_R) + m_webs * 0.5 * (XS_F + XS_R)
           + m_ribs * 0.45 + m_bal * (1 - ail["cf"] - 0.02))
    mtot = m_sk_f + m_sk_a + m_caps + m_webs + m_ribs + m_bal
    xcg = num / mtot
    mprime = mtot[sel]
    m_half = np.trapezoid(mprime, yy)
    # entegre tank: 2 kapali kaburga/yari (sandvic) + ic sizdirmazlik kaplamasi + donanim
    rib_area = np.interp([Y_T0, Y_T1], YS, (XS_R - XS_F) * c * h_box)
    m_tank_ribs = 2 * float(np.sum(rib_area)) * (2 * 2 * fab["areal_dry"] / 0.6 + core["rho"] * 3e-3)
    tank_w = np.where((YS >= Y_T0) & (YS <= Y_T1), (XS_R - XS_F) * c, 0.0)
    m_seal = 2 * np.trapezoid(tank_w * 2 * 0.15, YS)  # ust+alt ic yuz: 48 g cam + epoksi ~0.15 kg/m2
    m_tank_hw = 2 * 0.030                               # klunk, cikis/havalandirma nipeli, kapak
    m_joiner = 2 * 0.012 * 0.016 * 0.30 * ud["rho"]
    m_wing = 2 * m_half + m_joiner + 0.12 + m_tank_ribs + m_seal + m_tank_hw
    # tank ic hacmi (yari): kiris arasi net kesit - kapaklar - web'ler, %5 bolme/kaburga kaybi
    A_in = (XS_R - XS_F) * c * h_box - 2 * A_cap - 2 * t_web * h_box
    V_tank_half = 0.95 * np.trapezoid(np.where((YS >= Y_T0) & (YS <= Y_T1), A_in, 0.0), YS)
    return dict(n_face=n_face_plies, n_aft=n_aft, xcg=xcg, t_skin=t_skin, h_box=h_box, w_cap=w_cap, n_ud=n_ud, n_web=n_web,
                EI=EI, GJ=GJ, mprime=np.interp(YS, yy, mprime), m_wing=m_wing,
                tau_skin_max=float(np.max(np.abs(tau_skin))), A_req=A_req, Aenc=ar,
                V_tank_half_L=V_tank_half * 1e3, m_tank_extra=m_tank_ribs + m_seal + m_tank_hw)


def section_inertia(m_s, c, mf, xcg=X_SEC_CG):
    """Kesit kutlesi, EA'ya gore statik moment ve atalet (yapi + yakit, yakit rijit kabul)."""
    I_s = m_s * (c ** 2 / 12 + ((xcg - X_EA) * c) ** 2)
    I_f = mf * (((X_FUEL_C - X_EA) * c) ** 2 + ((XS_R - XS_F) * c) ** 2 / 12)
    S_a = m_s * (xcg - X_EA) * c + mf * (X_FUEL_C - X_EA) * c
    return m_s + mf, S_a, I_s + I_f


def rayleigh_freqs(ws, fuel=False):
    yy = YS[YS >= Y0]
    L = B2 - Y0
    EI = np.interp(yy, YS, ws["EI"])
    GJ = np.interp(yy, YS, ws["GJ"])
    ms = np.interp(yy, YS, ws["mprime"])
    mf = np.interp(yy, YS, fuel_per_span()) if fuel else np.zeros_like(yy)
    m, _, Ia = section_inertia(ms, chord(yy), mf, np.interp(yy, YS, ws["xcg"]))
    k = math.pi / (2 * L)
    phi_b = 1 - np.cos(k * (yy - Y0))
    d2phi = k ** 2 * np.cos(k * (yy - Y0))
    phi_t = np.sin(k * (yy - Y0))
    dphi_t = k * np.cos(k * (yy - Y0))
    wh = math.sqrt(np.trapezoid(EI * d2phi ** 2, yy) / np.trapezoid(m * phi_b ** 2, yy))
    wa = math.sqrt(np.trapezoid(GJ * dphi_t ** 2, yy) / np.trapezoid(Ia * phi_t ** 2, yy))
    return wh, wa


# ================================================================== 5. flutter
def theodorsen(k):
    H1, H0 = hankel2(1, k), hankel2(0, k)
    return H1 / (H1 + 1j * H0)


def k_method(mu, a, xa, ra2, sigma, ks=None, beta=1.0):
    """Hodges & Pierce tipik kesit k-yontemi. Donus: (k, V/(b*wa), g) dizileri, 2 kok."""
    if ks is None:
        ks = np.logspace(math.log10(0.02), math.log10(3.0), 600)[::-1]
    out = []
    for k in ks:
        C = theodorsen(k)
        Lh = 1 - 2j * C / k
        La = 0.5 - 1j * (1 + 2 * C) / k - 2 * C / k ** 2
        Mh = 0.5
        Ma = 3 / 8 - 1j / k
        f = 1 / beta
        A = np.array([[mu + f * Lh, mu * xa + f * (La - Lh * (0.5 + a))],
                      [mu * xa + f * (Mh - Lh * (0.5 + a)),
                       mu * ra2 + f * (Ma - (La + Mh) * (0.5 + a) + Lh * (0.5 + a) ** 2)]])
        B = np.diag([mu * sigma ** 2, mu * ra2])
        Z = np.linalg.eigvals(np.linalg.solve(B, A))
        Z = Z[np.argsort(Z.real)]
        row = []
        for z in Z:
            wr = 1 / math.sqrt(max(z.real, 1e-12))      # w/wa
            g = z.imag / z.real
            row.append((wr / k, g, wr))
        out.append(row)
    return ks, np.array(out)


def flutter_speed(mu, a, xa, ra2, sigma, beta=1.0):
    ks, res = k_method(mu, a, xa, ra2, sigma, beta=beta)
    best = None
    for j in range(2):
        U, g = res[:, j, 0], res[:, j, 1]
        for i in range(len(U) - 1):
            if g[i] < 0 <= g[i + 1] or g[i] > 0 >= g[i + 1]:
                if (g[i + 1] - g[i]) * (U[i + 1] - U[i]) > 0:  # U artarken g pozitife geciyor
                    t = -g[i] / (g[i + 1] - g[i])
                    Uf = U[i] + t * (U[i + 1] - U[i])
                    if best is None or Uf < best[0]:
                        best = (Uf, j)
    return (best[0] if best else float("inf")), ks, res


def section_params(ws, wh, wa, eta=0.70, fuel=False):
    y = Y0 + eta * (B2 - Y0)
    c = chord(y)
    b = c / 2
    ms = float(np.interp(y, YS, ws["mprime"]))
    mf = float(np.interp(y, YS, fuel_per_span())) if fuel else 0.0
    xcg = float(np.interp(y, YS, ws["xcg"]))
    m, S_a, Ia = section_inertia(ms, c, mf, xcg)
    return dict(y=y, xcg=xcg, c=c, b=b, m=m, m_fuel=mf, mu=m / (math.pi * RHO0 * b ** 2), a=(X_EA - 0.5) / 0.5,
                xa=S_a / (m * b), ra2=Ia / (m * b ** 2), wh=wh, wa=wa, sigma=wh / wa)


def flutter_dimensional(sp):
    """Sikistirilabilirlik (Prandtl-Glauert) ile iteratif boyutlu flutter hizi."""
    V = 250.0
    for _ in range(30):
        M = min(V / A_SOUND, 0.9)
        beta = math.sqrt(1 - M * M)
        Uf, _, _ = flutter_speed(sp["mu"], sp["a"], sp["xa"], sp["ra2"], sp["sigma"], beta)
        Vn = Uf * sp["b"] * sp["wa"]
        if abs(Vn - V) < 0.5:
            break
        V = 0.5 * (V + Vn)
    return Vn


def divergence(ws):
    """Duz (oksuz) kanat icin muhafazakar burulma diverjansi (Rayleigh)."""
    yy = YS[YS >= Y0]
    L = B2 - Y0
    GJ = np.interp(yy, YS, ws["GJ"])
    c = chord(yy)
    e = (X_EA - 0.25) * c
    a2d = 2 * math.pi * 0.9
    k = math.pi / (2 * L)
    num = np.trapezoid(GJ * (k * np.cos(k * (yy - Y0))) ** 2, yy)
    den = np.trapezoid(a2d * e * c * np.sin(k * (yy - Y0)) ** 2, yy)
    q_div = num / den
    # sikistirilabilirlik: q_div / ... iteratif (a2d/beta)
    V = math.sqrt(2 * q_div / RHO0)
    for _ in range(20):
        beta = math.sqrt(max(1 - (V / A_SOUND) ** 2, 0.2))
        V = math.sqrt(2 * q_div * beta / RHO0)
    # ok acisi etkisi (ileri ok yok; geri ok diverjansi pratikte ortadan kaldirir)
    return V


def validate_k_method():
    """Hodges & Pierce Ornek: a=-1/5, e=-1/10, mu=20, r2=6/25, sigma=2/5 -> U_F ~ 2.17"""
    Uf, _, _ = flutter_speed(20.0, -0.2, 0.1, 6 / 25, 0.4)
    RES["flutter_validation"] = dict(U_F=Uf, reference=2.17)
    return Uf


def control_surface_balance():
    """Aileron/elevator/rudder statik balans ve dondurme frekansi gereksinimi."""
    out = {}
    lam_cs = 2 * (MAT["FAB"]["areal_dry"] / 0.6) + MAT["CORE"]["rho"] * MAT["CORE"]["t"] * 0.5 + 0.08
    wa_wing = RES["flutter"]["wa"]
    surfaces = []
    ail = WING["aileron"]
    span_a = (ail["eta1"] - ail["eta0"]) * B2
    c_mid = chord((ail["eta0"] + ail["eta1"]) / 2 * B2)
    surfaces.append(("Aileron (her biri)", span_a, ail["cf"] * c_mid))
    hg = surface_geom(HTAIL)
    surfaces.append(("Elevator (her biri)", hg["b"] / 2 - 0.03, HTAIL["elevator"]["cf"] * hg["mac"]))
    vg = vtail_geom()
    surfaces.append(("Rudder", vg["h"] - 0.02, VTAIL["rudder"]["cf"] * vg["mac"]))
    fl = WING["flap"]
    surfaces.append(("Flap (her biri)", (fl["eta1"] - fl["eta0"]) * B2,
                     fl["cf"] * chord((fl["eta0"] + fl["eta1"]) / 2 * B2)))
    for name, span, cf in surfaces:
        area = span * cf
        m = area * lam_cs * 2 * 0.5 + 0.004 * span / 0.1 * 0.5    # iki yuz kabuk (planform*2) + mentese
        m = area * (2 * MAT["FAB"]["areal_dry"] / 0.6 + MAT["CORE"]["rho"] * MAT["CORE"]["t"]) * 2 * 0.55 \
            + 0.003
        x_cg = 0.40 * cf                          # mentese arkasi
        S_stat = m * x_cg                         # statik moment [kg.m]
        arm = 0.20 * cf                           # balans kutlesi kolu (mentese onu, burun icinde)
        m_bal = S_stat / arm                      # %100 statik balans icin
        I_h = m * (x_cg ** 2 + cf ** 2 / 12)
        # %100 statik balans ile burulma-kontrol yuzeyi ataletsel baglasimi kalkar; kalan gereksinim:
        # dondurme frekansi >= 1.5 x kanat egilme frekansi (egilme-aileron baglasimini ayirmak icin)
        w_req = 1.5 * RES["flutter"]["wh"]
        K_req = I_h * w_req ** 2                  # [N.m/rad]
        out[name] = dict(span=span, cf=cf, area=area, mass=m, S_static=S_stat, m_balance=m_bal,
                         arm=arm, I_hinge=I_h, f_req_Hz=w_req / (2 * math.pi), K_req=K_req)
    RES["cs_balance"] = out
    return out


# ================================================================== 6. mentese momentleri
def hinge_moments():
    out = {}
    vn = RES["vn"]
    cases = [("V_oper 800 km/h", V_OPER_MAX, "hs", N_LIMIT),
             ("V_D 900 km/h", V_D, "hs", 1.0 + RES["vn"]["gust"]["Operasyonel sinir (7.62/3.81 m/s)"]["n_VD"] - 1),
             ("V_A", vn["VA"], "ls", N_LIMIT)]
    eff = 0.70                                 # ince profil -> gercek (viskoz, bosluk, 3B)
    ail, fl = WING["aileron"], WING["flap"]
    hg, vg = surface_geom(HTAIL), vtail_geom()
    surfs = {
        "Aileron": dict(cf_ratio=ail["cf"], span=(ail["eta1"] - ail["eta0"]) * B2,
                        c=chord((ail["eta0"] + ail["eta1"]) / 2 * B2), hs=ail["defl_max_hs"],
                        ls=ail["defl_max_ls"], alpha_src="wing", n_serv=1),
        "Elevator": dict(cf_ratio=HTAIL["elevator"]["cf"], span=hg["b"] / 2 - 0.03, c=hg["mac"],
                         hs=HTAIL["elevator"]["defl_max_hs"], ls=HTAIL["elevator"]["defl_max_ls"],
                         alpha_src="tail", n_serv=1),
        "Rudder": dict(cf_ratio=VTAIL["rudder"]["cf"], span=vg["h"] - 0.02, c=vg["mac"],
                       hs=VTAIL["rudder"]["defl_max_hs"], ls=VTAIL["rudder"]["defl_max_ls"],
                       alpha_src="tail", n_serv=1),
        "Flap": dict(cf_ratio=fl["cf"], span=(fl["eta1"] - fl["eta0"]) * B2,
                     c=chord((fl["eta0"] + fl["eta1"]) / 2 * B2), hs=0.0, ls=fl["defl_land"],
                     alpha_src="flap", n_serv=1),
    }
    horn_ratio = 1.3    # kontrol kolu / servo kolu uzunluk orani (servo torkunu azaltir, hassasiyeti arttirir)
    for name, s in surfs.items():
        E = s["cf_ratio"]
        _, _, Ch_d = thin_airfoil_flap(E, 0.0, 1.0)
        _, _, Ch_a = thin_airfoil_flap(E, 1.0, 0.0)
        cf = E * s["c"]
        Sf = s["span"] * cf
        rows = {}
        for cname, V, regime, n in cases:
            if name == "Flap":
                if regime != "ls":
                    continue
                V = 150 / 3.6               # V_FE
                n = 2.0
            M = V / A_SOUND
            beta = math.sqrt(1 - M * M)
            q = 0.5 * RHO0 * V * V
            d = math.radians(s["hs"] if regime == "hs" else s["ls"])
            if s["alpha_src"] == "wing" or s["alpha_src"] == "flap":
                alpha = min(n * W / (q * S) / lift_slope(M), math.radians(12))
            else:
                alpha = math.radians(2.5) if regime == "hs" else math.radians(10.0)   # hamle 1.75 deg + trim
            Ch = eff / beta * (abs(Ch_a) * alpha + abs(Ch_d) * d)
            Mh = q * Sf * cf * Ch
            T_servo = 2.0 * Mh / horn_ratio
            rows[cname if name != "Flap" else "V_FE 150 km/h"] = dict(q=q, Ch=Ch, Mh=Mh, T_servo_Nm=T_servo,
                                                                      T_servo_kgcm=T_servo * 10.197)
        Tmax = max(r["T_servo_kgcm"] for r in rows.values())
        cls = next(c for c in (15, 25, 35, 45, 60, 70, 90, 120) if c >= Tmax)
        out[name] = dict(Ch_delta=Ch_d, Ch_alpha=Ch_a, cf=cf, Sf=Sf, cases=rows, T_req_kgcm=Tmax,
                         servo_class_kgcm=cls)
    RES["hinge"] = out
    RES["hinge_meta"] = dict(eff=eff, horn_ratio=horn_ratio, sf_servo=2.0)
    return out


# ================================================================== 4. govde
def fuselage_checks():
    n_ult = N_LIMIT * SF
    x_front_spar = WING["x_root_le"] + WING["spar_xc"][0] * wg["cr"]
    x_rear_spar = WING["x_root_le"] + WING["spar_xc"][1] * wg["cr"]
    # kuyruk yuku VD'de: CL_t = 0.2 (hamle + elevator), limit
    qD = 0.5 * RHO0 * V_D ** 2
    hg = surface_geom(HTAIL)
    L_t = qD * HTAIL["S"] * 0.20
    vg = vtail_geom()
    L_v = qD * VTAIL["S"] * 0.20
    xs = np.linspace(x_rear_spar, FUSELAGE["length"], 120)
    Mb = []
    items = [(n, m, x) for n, m, x, z in MASS_ITEMS if "Kanat" not in n and "Govde kabugu" not in n]
    for x in xs:
        mm = sum(m * G * n_ult * (xi - x) for _, m, xi in items if xi > x)
        # govde kabugu kutlesi duzgun yayili
        m_shell = 1.55 / FUSELAGE["length"]
        mm += m_shell * G * n_ult * (FUSELAGE["length"] - x) ** 2 / 2
        if hg["x_ac"] > x:
            mm += SF * L_t * (hg["x_ac"] - x)
        Mb.append(mm)
    Mb = np.array(Mb)
    # on govde
    xf = np.linspace(0, x_front_spar, 120)
    Mf = []
    # govde tanki = toplam - kanat tanklari; konumu toplam yakit CG'sini (params FUEL x) saglayacak sekilde
    x_wt = WING["x_root_le"] + 0.5 * (Y_T0 + Y_T1) * math.tan(math.radians(WING["sweep_le"])) \
        + X_FUEL_C * chord(0.5 * (Y_T0 + Y_T1))
    m_fuel = FUEL["mass"] - 2 * M_WT_HALF
    x_ft = (FUEL["mass"] * FUEL["x"] - 2 * M_WT_HALF * x_wt) / m_fuel
    RES["fuel_split"] = dict(m_fus=m_fuel, x_fus=x_ft, m_wing_each=M_WT_HALF, x_wing=x_wt)
    for x in xf:
        mm = sum(m * G * n_ult * (x - xi) for _, m, xi in items if xi < x)
        if x_ft < x:
            mm += m_fuel * G * n_ult * (x - x_ft)
        Mf.append(mm)
    Mf = np.array(Mf)
    r = FUSELAGE["d_max"] / 2

    def r_at(x):
        L = FUSELAGE["length"]
        if x < FUSELAGE["x_dmax_start"]:
            return r * math.sqrt(max(1 - ((FUSELAGE["x_dmax_start"] - x) / FUSELAGE["x_dmax_start"]) ** 2, 0.02))
        if x > FUSELAGE["x_dmax_end"]:
            return r - (r - FUSELAGE["d_tail"] / 2) * (x - FUSELAGE["x_dmax_end"]) / (L - FUSELAGE["x_dmax_end"])
        return r

    E = MAT["FAB200"]["E_qi"]
    req = []
    for xarr, marr in ((xs, Mb), (xf, Mf)):
        for x, M in zip(xarr, marr):
            R = r_at(x)
            for npl in range(2, 12):
                t = npl * MAT["FAB200"]["t_ply"]
                sig = M / (math.pi * R ** 2 * t)
                sig_cr = 0.3 * E * t / R            # knockdown dahil silindir burkulmasi
                if sig <= SIG_FUS and sig <= sig_cr:
                    break
            req.append((x, M, npl, sig / 1e6))
    req = np.array(req)
    # en kritik
    i = int(np.argmax(req[:, 2] * 1000 + req[:, 1]))
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(xs, Mb, "r", label="Arka govde (kuyruk yuku + kutle)")
    ax.plot(xf, Mf, "b", label="On govde (kutle)")
    ax.set_xlabel("x [m]")
    ax.set_ylabel("Nihai egilme momenti [N.m]")
    ax2 = ax.twinx()
    ax2.step(req[:, 0][np.argsort(req[:, 0])], req[:, 2][np.argsort(req[:, 0])], "k--", where="mid", lw=.8)
    ax2.set_ylabel("Gereken kat (200 g/m2)")
    ax.legend(fontsize=8)
    ax.grid(alpha=.3)
    ax.set_title("Govde egilmesi (n_ult=18 + 1.5 x VD kuyruk yuku)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "govde_egilme.png"), dpi=130)
    plt.close(fig)
    # motor yatagi
    me = ENGINE["mass"]
    Fz = me * G * n_ult
    Fy = me * G * 4.5 * SF
    Fx = ENGINE["F0"] * SF
    wn = 2 * math.pi * 100000 / 60                  # ~100k rpm (P400 tahmini)
    I_rot = 1.5e-4                                  # rotor ataleti tahmini [kg.m2]
    q_pitch = N_LIMIT * G / V_OPER_MAX
    M_gyro = I_rot * wn * max(q_pitch, 3.0)         # 3 rad/s yalpa/yunuslama orani
    # 4 civata, 2 rayda, aralik 0.12 m (x) x 0.10 m (y)
    F_bolt_shear = math.hypot(Fz, Fy) / 4 + Fx / 4
    F_bolt_tension = (Fz * 0.05) / (2 * 0.12) + M_gyro / (2 * 0.10)
    # kanat baglantisi: iki karbon bicak birlestirici + 2 x M5 arka pim
    M_side = RES["loads"]["M_side"]
    V_side = RES["loads"]["V_side"]
    h_j = 0.016                                      # govde yaninda kutu yuksekligi ~19 mm
    b_j_req = 6 * M_side / (SIG_CAP * h_j ** 2) / 2   # iki bicak paylasir
    F_pin = V_side / 2 + abs(RES["loads"]["T_root_case2"]) / (0.25 * wg["cr"])
    d_pin = 5e-3
    shear_cap = 0.6 * 800e6 * math.pi * d_pin ** 2 / 4  # 8.8 celik civata
    t_bearing = F_pin / (d_pin * 400e6 * KD)
    RES["fuselage"] = dict(_M_aft_curve=(xs.tolist(), Mb.tolist()), L_tail_limit=L_t, L_vtail_limit=L_v, M_aft_max=float(Mb.max()), M_fwd_max=float(Mf.max()),
                           critical_x=float(req[i, 0]), plies_max=int(req[:, 2].max()),
                           sigma_crit_MPa=float(req[i, 3]),
                           engine_mount=dict(Fz=Fz, Fy=Fy, Fx=Fx, M_gyro=M_gyro, F_bolt_shear=F_bolt_shear,
                                             F_bolt_tension=F_bolt_tension),
                           wing_attach=dict(M_side=M_side, V_side=V_side, joiner_h=h_j, joiner_b_req=b_j_req,
                                            F_pin=F_pin, pin_shear_cap=shear_cap, t_bearing_req=t_bearing))
    return RES["fuselage"]



# ================================================================== 7. entegre tank, kizak, yatay kuyruk koku

def low_wing_attach():
    """Alcak kanat: (A) tek parca kanat, kutu govde icinden gecer (carry-through), kiris cercevelerine
    civatali; (B) karsilastirma: iki yari + karbon bicak + yan cerceve. Ayrica govde alt kesigi kontrolu."""
    n_ult = N_LIMIT * SF
    R = FUSELAGE["d_max"] / 2
    zr = WING["z_root"]
    t_root = WING["tc_root"] * wg["cr"]
    z_up, z_lo = zr + 0.5 * 0.9 * t_root, zr - 0.5 * 0.9 * t_root   # kutu bolgesinde ust/alt yuzey
    y_up = math.sqrt(R ** 2 - z_up ** 2)
    x_fs = WING["x_root_le"] + XS_F * wg["cr"]
    x_rs = WING["x_root_le"] + XS_R * wg["cr"]
    # govde (kanat ve kanat yakiti haric) kutle ve CG
    items = [(n, m, x) for n, m, x, z in MASS_ITEMS if not n.startswith("Kanat")]
    split = RES["fuel_split"]
    m_f = sum(i[1] for i in items) + split["m_fus"]
    x_f = (sum(i[1] * i[2] for i in items) + split["m_fus"] * split["x_fus"]) / m_f
    # kuyruk yuku (V_D, limit) +- ; nihai
    Lt = SF * RES["fuselage"]["L_tail_limit"]
    hg = surface_geom(HTAIL)
    cases = {}
    for sgn, nm in ((+1, "kuyruk yuku asagi"), (-1, "kuyruk yuku yukari")):
        Fz = n_ult * m_f * G + sgn * Lt                      # kanattan govdeye aktarilacak toplam (asagi)
        Mfs = n_ult * m_f * G * (x_f - x_fs) + sgn * Lt * (hg["x_ac"] - x_fs)
        R_r = Mfs / (x_rs - x_fs)
        R_f = Fz - R_r
        cases[nm] = dict(Fz=Fz, R_front=R_f, R_rear=R_r)
    R_max_A1 = max(max(abs(c["R_front"]), abs(c["R_rear"])) for c in cases.values())
    # A2 (onerilen): yunuslama momenti HK pimi (x~0.96) ile firar kenari kok civatasi (x~1.32) arasinda
    x_a, x_b = WING["x_root_le"] + 0.04, WING["x_root_le"] + 0.40
    cases2 = {}
    for sgn, nm in ((+1, "kuyruk yuku asagi"), (-1, "kuyruk yuku yukari")):
        Fz = n_ult * m_f * G + sgn * Lt
        Ma = n_ult * m_f * G * (x_f - x_a) + sgn * Lt * (hg["x_ac"] - x_a)
        R_b = Ma / (x_b - x_a)
        cases2[nm] = dict(Fz=Fz, R_LE=Fz - R_b, R_TE=R_b)
    R_max = max(max(abs(c["R_LE"]), abs(c["R_TE"])) for c in cases2.values())
    # yanal: dikey kuyruk yan kuvveti (V_D, CL 0.2) -> yuvarlanma momenti civata ciftine
    vg = vtail_geom()
    Fv = SF * RES["fuselage"]["L_vtail_limit"]
    arm_v = (VTAIL["z_root"] + vg["z_mac"]) - zr
    M_roll = Fv * arm_v
    bolt_dy = 0.070                                           # civata yanal araligi
    # negatif g (n = -8 limit, -12 nihai): civatalar cekmede
    R_neg = R_max * abs(N_NEG) / N_LIMIT
    F_bolt_t = max(R_max, R_neg) / 2 + M_roll / bolt_dy / 2
    F_bolt_t_A1 = max(R_max_A1, R_max_A1 * abs(N_NEG) / N_LIMIT) / 2 + M_roll / bolt_dy / 2
    F_bolt_s = math.hypot(Fv / 4, 0.25 * (SF * 0.0074 * 0.5 * RHO0 * V_D ** 2 * S))
    A_s5 = 14.2e-6
    cap_t = 0.7 * 1220e6 * A_s5                               # M5 12.9 cekme (on yuk dahil)
    # carry-through kutu: kok momenti sabit (M_root) -> kapaklar y=0 istasyonunda boyutlandi
    M_ct = RES["loads"]["M_root"]
    # cerceveler (kiris cerceveleri): halka, civata noktasal yukleri 2 noktada
    M_ring = 0.08 * R_max * R
    h_fr = 0.018
    t_fr = 6 * M_ring / (SIG_FUS * h_fr ** 2)             # gereken cerceve kalinligi (karbon, 18 mm derinlik)
    sig_fr = SIG_FUS
    # govde alt kesigi (kiris cerceveleri arasi, z < z_up acik): ust yay + 2 UD longeron
    M_cut = float(np.interp(x_rs, *RES["fuselage"]["_M_aft_curve"]))
    t_sh = 3 * MAT["FAB200"]["t_ply"]
    phi_c = math.acos(z_up / R)
    ph = np.linspace(-phi_c, phi_c, 400)
    zs = R * np.cos(ph)
    ds = R * (ph[1] - ph[0])
    E_s, E_l = MAT["FAB200"]["E_qi"], MAT["UD"]["E1"]
    long_rows = []
    for A_l in (0.0, 20e-6, 40e-6, 60e-6, 80e-6, 120e-6):
        EA = E_s * t_sh * ds * len(zs) + 2 * E_l * A_l
        zc = (E_s * t_sh * ds * zs.sum() + 2 * E_l * A_l * z_up) / EA
        EI = E_s * t_sh * ds * ((zs - zc) ** 2).sum() + 2 * E_l * A_l * (z_up - zc) ** 2
        eps = M_cut * max(abs(z_up - zc), abs(R - zc)) / EI
        long_rows.append(dict(A_mm2=A_l * 1e6, eps=eps, sig_shell_MPa=eps * E_s / 1e6, ok=eps <= EPS_ALLOW))
    A_long = next((r["A_mm2"] for r in long_rows if r["ok"]), None)
    # secenek B (iki yari, bicak): alcak kanatta bicaklar govde altindan gecer; govde yaninda kutu
    # yuksekligi ~19 mm, yan cerceve tabani dar (y_up) -> bicak momenti cerceve tabanina tasinir
    hj = 0.016
    b_j = 6 * RES["loads"]["M_side"] / (SIG_CAP * hj ** 2) / 2
    m_joiner = 2 * 0.012 * 0.016 * 0.30 * MAT["UD"]["rho"] + 2 * 0.05   # bicak + 2 kok kaburgasi/yuva
    m_ct = 2 * Y0 * float(np.interp(0.0, YS, RES["_ws_mprime"])) + 4 * 0.010 + 0.04   # kutu + 4 civata ucu + kaplama
    RES["low_wing"] = dict(z_upper=z_up, z_lower=z_lo, y_upper_side=y_up, Y0=Y0, x_fs=x_fs, x_rs=x_rs,
                           m_fus=m_f, x_fus_cg=x_f, cases_A1=cases, R_max_A1=R_max_A1, F_bolt_t_A1=F_bolt_t_A1,
                           cases=cases2, x_LE_pin=x_a, x_TE_bolt=x_b, t_frame_req=t_fr, R_max=R_max, M_roll=M_roll, F_vtail_ult=Fv,
                           F_bolt_tension=F_bolt_t, F_bolt_shear=F_bolt_s, bolt_cap_t=cap_t, M_carry=M_ct,
                           M_ring=M_ring, sig_frame_MPa=sig_fr / 1e6, M_cut=M_cut, longerons=long_rows,
                           A_long_req_mm2=A_long, optionB=dict(joiner_b=b_j, m=m_joiner), optionA_m=m_ct,
                           center_tank_L=RES["_ct_tank_L"])
    return RES["low_wing"]


def flap_slotted():
    """Tek yarikli flap: acik (V_FE) normal kuvvet, ray/dis mentese yukleri, servo; kapali (V_C/V_D) tutma momenti."""
    fl = WING["flap"]
    span = (fl["eta1"] - fl["eta0"]) * B2
    c = chord((fl["eta0"] + fl["eta1"]) / 2 * B2)
    cf = fl["cf"] * c
    Sf = span * cf
    V_FE = 150 / 3.6
    q = 0.5 * RHO0 * V_FE ** 2
    Cn = 1.6           # tek yarikli flap 35 deg normal kuvvet katsayisi (flap alanina; hamle payi dahil)
    N_lim = Cn * q * Sf
    N_ult = SF * N_lim
    x_cp = 0.35 * cf   # flap HK'den basinc merkezi
    # dis mentese (drop hinge): pivot flap HK'nin 0.10 cf onunde, 0.06 c altinda
    arm = x_cp + 0.10 * cf
    Mh_lim = N_lim * arm
    horn_ratio = 1.3
    T_servo = 2.0 * Mh_lim / horn_ratio
    n_brk = 2
    F_brk = N_ult / n_brk * 1.25          # ic/dis braket paylasimi esit degil (+%25)
    d_pin = 3e-3
    pin_cap = 0.6 * 800e6 * math.pi * d_pin ** 2 / 4 * 2   # cift kesme
    # kapali flap, yuksek hiz: plain-flap Ch_alpha ile tutma momenti (dayanak + servo on yuku)
    _, _, Ch_a = thin_airfoil_flap(fl["cf"], 1.0, 0.0)
    rows = {}
    for nm, V, n in (("V_oper 800 km/h", V_OPER_MAX, N_LIMIT), ("V_D 900 km/h", V_D, 6.5)):
        qq = 0.5 * RHO0 * V ** 2
        beta = math.sqrt(1 - (V / A_SOUND) ** 2)
        alpha = n * W / (qq * S) / lift_slope(V / A_SOUND)
        Mh = qq * Sf * cf * 0.7 / beta * abs(Ch_a) * alpha
        rows[nm] = dict(Mh=Mh, T_hold_kgcm=2 * Mh / horn_ratio * 10.197)
    T_req = max(T_servo * 10.197, max(r["T_hold_kgcm"] for r in rows.values()))
    RES["flap"] = dict(span=span, cf=cf, Sf=Sf, q_FE=q, Cn=Cn, N_lim=N_lim, N_ult=N_ult, Mh_lim=Mh_lim,
                       T_servo_kgcm=T_servo * 10.197, F_bracket_ult=F_brk, pin_cap=pin_cap, retracted=rows,
                       T_req_kgcm=T_req)
    RES["hinge"]["Flap"] = dict(Ch_delta=float("nan"), Ch_alpha=Ch_a, cf=cf, Sf=Sf,
                                cases={"V_FE 150 km/h (yarikli, 35 deg)": dict(q=q, Mh=Mh_lim,
                                                                             T_servo_kgcm=T_servo * 10.197),
                                       **{k + " (kapali, tutma)": dict(Mh=v["Mh"], T_servo_kgcm=v["T_hold_kgcm"])
                                          for k, v in rows.items()}},
                                T_req_kgcm=T_req,
                                servo_class_kgcm=next(c for c in (15, 25, 35, 45, 60) if c >= T_req))
    return RES["flap"]


def elevator_flutter_check():
    """Elevator: %100 statik balans + dondurme frekansi; yatay kuyruk egilme frekansi tahmini (yari kuyruk,
    boru soketinde ankastre, uniform kiris)."""
    hg = surface_geom(HTAIL)
    L = hg["b"] / 2 - 0.06
    m_half = 0.30 / 2 + 0.06
    EI = 0.5 * MAT["UD"]["E1"] * 2 * (0.6 * hg["cr"] * 0.4e-3) * (0.9 * HTAIL["tc"] * hg["cr"] / 2) ** 2
    f_tail = 1.875 ** 2 / (2 * math.pi) * math.sqrt(EI / (m_half / L * L ** 4))
    el = RES["cs_balance"]["Elevator (her biri)"]
    w_req = 2 * math.pi * 1.5 * min(f_tail, RES["flutter"]["f_bend_Hz"] * 3)
    K_req = el["I_hinge"] * w_req ** 2
    RES["elevator_flutter"] = dict(f_tail_bend_Hz=f_tail, EI_root=EI, f_req_Hz=w_req / (2 * math.pi),
                                   K_req=K_req, m_balance=el["m_balance"], mass=el["mass"])
    return RES["elevator_flutter"]


def tank_checks(ws):
    """Entegre kanat tanki: hacim, tasarim basinci, panel/kaburga kontrolu, yanal dengesizlik."""
    fab, core = MAT["FAB"], MAT["CORE"]
    rho_f = FUEL["density"] * 1000
    yc = 0.5 * (Y_T0 + Y_T1)
    c = chord(yc)
    w_box = (XS_R - XS_F) * c
    h = float(np.interp(yc, YS, ws["h_box"]))
    L_span = Y_T1 - Y_T0
    p_static = {
        "dikey 18 g (h=kutu yuks.)": rho_f * 18 * G * h,
        "yanal/aciklik: yuvarlanma p=10 rad/s": rho_f * (10 ** 2) * 0.5 * (Y_T1 ** 2 - Y_T0 ** 2),
        "boyuna: kizak inisi 5 g x kutu genisligi": rho_f * 5 * G * w_box,
        "egzoz/sicaklik buhar basinci + havalandirma tikanmasi": 10e3,
    }
    p_lim = max(p_static.values())
    p_ult = SF * p_lim
    # kabuk paneli (kiris arasi, kaburgalar arasi): basit mesnetli sandvic plaka, kisa kenar = w_box
    a, b = L_span / 2, w_box                            # orta bolme kaburgasi ile (2 bolme)
    beta = 0.1 if a / b >= 2 else 0.0479 * (a / b) ** 2 + 0.0 + 0.06
    Mpl = beta * p_ult * b ** 2                        # [N.m/m]
    t_f = ws["n_face"] * fab["t_ply"]
    sig_face = Mpl / (t_f * (core["t"] + t_f))
    tau_core = p_ult * b / 2 / (core["t"] + t_f)        # cekirdek kesmesi (Rohacell 51: ~0.8 MPa)
    # tank kaburgasi: kutu kesitini kapatan sandvic, 3 mm cekirdek, kenar mesnetli
    Mrib = 0.125 * p_ult * min(w_box, h) ** 2 * 2
    sig_rib = Mrib / (2 * fab["t_ply"] * (3e-3 + 2 * fab["t_ply"]))
    # yanal dengesizlik (bir tank bos)
    dM_roll = M_WT_HALF * G * (yc)
    RES["tank"] = dict(V_half_L=ws["V_tank_half_L"], V_req_L=M_WT_HALF / FUEL["density"], y0=Y_T0, y1=Y_T1,
                       w_box=w_box, h_box=h, p_cases=p_static, p_lim=p_lim, p_ult=p_ult, sig_face_MPa=sig_face / 1e6,
                       tau_core_MPa=tau_core / 1e6, sig_rib_MPa=sig_rib / 1e6, dM_roll=dM_roll,
                       m_tank_extra=ws["m_tank_extra"])
    return RES["tank"]


def skid_checks():
    """Govde alti kizak inisi: 95 km/h, dikey batma 1.5 m/s, ini kutlesi bos + %10 yakit."""
    m_land = mass_summary(0.10)["m"]
    vs = 1.5
    E = 0.5 * m_land * vs ** 2                      # L = W kabul (CS-23.473) -> yalniz dikey KE
    eta = 0.5                                       # kopuk/kizak + zemin enerji verimi
    strokes = {"sert pist (kizak 10 mm kopuk)": 0.010, "kisa cim (10 mm + 15 mm zemin)": 0.025,
               "cim + 20 mm EPP ped": 0.045}
    n_land = {k: E / (eta * d) / (m_land * G) for k, d in strokes.items()}
    n_design = n_land["kisa cim (10 mm + 15 mm zemin)"]
    F_lim = n_design * m_land * G
    F_ult = SF * F_lim
    mu = 0.5
    V_td = 95 / 3.6
    slide = V_td ** 2 / (2 * mu * G)
    # kizak kirisi: cerceveler arasi aciklik, orta noktada tekil yuk (kuyruk-asagi temas en kotu)
    L_sk = GEAR["skid_x1"] - GEAR["skid_x0"]
    x_fs = WING["x_root_le"] + XS_F * wg["cr"]
    x_rs = WING["x_root_le"] + XS_R * wg["cr"]
    frames = sorted({GEAR["skid_x0"], 0.81, round(x_fs, 3), round(x_rs, 3), 1.38})
    frames = [f for f in frames if GEAR["skid_x0"] <= f <= GEAR["skid_x1"]]
    n_frames = len(frames)
    span = max(np.diff(frames))
    overhang = GEAR["skid_x1"] - frames[-1]
    Mb = max(F_ult * span / 4, F_ult * overhang)   # aciklik ortasi veya arka uc konsol temasi
    w, hsk = GEAR["skid_w"], GEAR["skid_h"]
    t_ud = 1.0e-3                                   # ust/alt UD karbon kapak
    I = 2 * w * t_ud * ((hsk - t_ud) / 2) ** 2
    sig_sk = Mb * (hsk / 2) / I
    # surtunme (mu*F) kizagi geriye iten kesme -> baglanti civatalari
    F_drag = mu * F_ult
    n_bolts = 6
    F_bolt = math.hypot(F_drag, F_ult / n_frames) / n_bolts * 2
    # cerceve (halka) noktasal radyal yuk, Roark: M_max ~ 0.08 F R
    R = FUSELAGE["d_max"] / 2
    M_ring = 0.08 * F_ult * R
    t_fr, h_fr = 3e-3, 0.015
    sig_ring = M_ring / (t_fr * h_fr ** 2 / 6)
    q_shell = F_ult / (math.pi * R)
    t_shell = 2 * MAT["FAB200"]["t_ply"]
    tau_shell = q_shell / t_shell
    # alt kabuk lokal basinc (kizak genisligi uzerinde dagilmis, %50 temas uzunlugu)
    p_belly = F_ult / (w * 0.5 * L_sk)
    # kuyruk carpma acisi: kizak arka ucu -> egzoz konisi alt kenari
    zb = -FUSELAGE["d_max"] / 2 - hsk
    z_tail = -FUSELAGE["d_tail"] / 2
    theta_tail = math.degrees(math.atan((z_tail - zb) / (FUSELAGE["length"] - GEAR["skid_x1"])))
    CL_td = 2 * m_land * G / (RHO0 * V_td ** 2 * S)
    m_skid = (2 * w * t_ud * 1550 + 2 * hsk * 0.6e-3 * 1400 + w * hsk * 52) * L_sk \
        + w * L_sk * 1.5e-3 * 1850 + 0.02
    RES["skid_frames"] = dict(frames=frames, span=span, overhang=overhang)
    RES["skid"] = dict(m_land=m_land, E=E, n_land=n_land, n_design=n_design, F_lim=F_lim, F_ult=F_ult,
                       slide_m=slide, span=span, M_skid=Mb, sig_skid_MPa=sig_sk / 1e6, F_bolt=F_bolt,
                       M_ring=M_ring, sig_ring_MPa=sig_ring / 1e6, tau_shell_MPa=tau_shell / 1e6,
                       p_belly_kPa=p_belly / 1e3, theta_tail_deg=theta_tail, CL_td=CL_td, m_skid=m_skid)
    return RES["skid"]


def htail_root():
    """Iki parcali yatay kuyruk: her yari kok baglantisi (ana boru + insidans pimi)."""
    qD = 0.5 * RHO0 * V_D ** 2
    hg = surface_geom(HTAIL)
    L_half = qD * HTAIL["S"] * 0.20 / 2
    L_ult = SF * L_half
    x_root = HTAIL["x_root_le"]
    L = FUSELAGE["length"]
    r = FUSELAGE["d_max"] / 2
    r_root = r - (r - FUSELAGE["d_tail"] / 2) * (x_root + 0.1 - FUSELAGE["x_dmax_end"]) / (L - FUSELAGE["x_dmax_end"])
    s_exp = hg["b"] / 2 - r_root
    y_cp = 0.43 * s_exp                         # acikta kalan yari aciklik basinc merkezi (kokten)
    M_root = L_ult * y_cp
    x_rod = x_root + 0.30 * hg["cr"]
    x_cp = hg["x_ac"]
    _, _, Ch_d = thin_airfoil_flap(HTAIL["elevator"]["cf"], 0.0, 1.0)
    Mh_el = RES["hinge"]["Elevator"]["cases"]["V_D 900 km/h"]["Mh"]
    T_root = L_ult * (x_cp - x_rod) + SF * Mh_el
    pin_arm = 0.45 * hg["cr"]
    F_pin = T_root / pin_arm
    sig_allow_tube = 400e6
    tubes = []
    for D, t in ((0.010, 0.0015), (0.012, 0.0015), (0.012, 0.002), (0.014, 0.002)):
        d = D - 2 * t
        Z = math.pi * (D ** 4 - d ** 4) / (32 * D)
        tubes.append(dict(D=D * 1e3, t=t * 1e3, sigma_MPa=M_root / Z / 1e6, ok=M_root / Z <= sig_allow_tube,
                          m_per_m=math.pi / 4 * (D ** 2 - d ** 2) * 1550))
    d_pin = 4e-3
    pin_cap = 0.6 * 800e6 * math.pi * d_pin ** 2 / 4
    t_br = F_pin / (d_pin * 400e6 * KD)
    # boru gecme boyu (kuyruk yarisinda): yatak cifti kuvveti
    L_sock = 0.10
    F_sock = M_root / (0.7 * L_sock)
    RES["htail_root"] = dict(L_half_lim=L_half, L_half_ult=L_ult, s_exp=s_exp, y_cp=y_cp, M_root=M_root,
                             T_root=T_root, x_rod=x_rod, F_pin=F_pin, pin_cap=pin_cap, t_bearing=t_br,
                             tubes=tubes, L_socket=L_sock, F_socket=F_sock)
    return RES["htail_root"]



def wing_section_model(n_face=None, n_aft=None):
    """iter4 yardimcisi (structures/fe_modal.py): main()'deki on boyutlandirma -> tank kapasitesi ->
    yakit rahatlatmali yuk -> size_wing adimlarini grafik/json yazmadan tekrarlar. Geriye uyumlu:
    main() akisini degistirmez. Kat plani verilmezse params WING["skin_plies"] kullanilir.
    Donus: ws (size_wing sozlugu: EI, GJ, mprime, xcg ... YS izgarasinda), yakit dagilimi ve sabitler."""
    global M_WT_HALF
    if n_face is None or n_aft is None:
        n_face, n_aft = WING.get("skin_plies", (3, 1))
    M_WT_HALF = 0.0
    _, V0, M0, T0 = span_loads(plot=False)
    ws_pre = size_wing(M0, V0, T0, 2)
    M_WT_HALF = min(M_WT_HALF_PARAMS, ws_pre["V_tank_half_L"] * FUEL["density"])
    _, V, M, T = span_loads(plot=False)
    ws = size_wing(M, V, T, n_face, n_aft)
    return dict(ws=ws, ws_pre=ws_pre, YS=YS, m_fuel_half=M_WT_HALF, fuel_per_span=fuel_per_span(),
                M=M, V=V, T=T, Y0=Y0, B2=B2, X_EA=X_EA, X_FUEL_C=X_FUEL_C, Y_T0=Y_T0, Y_T1=Y_T1)


# ================================================================== ana akis
def tank_capacity_table(ws_pre):
    """Tank dis siniri eta1'e gore ic hacim (yari kanat) [L]."""
    c = chord(YS)
    A_in = (XS_R - XS_F) * c * ws_pre["h_box"] - 2 * 2 * ws_pre["w_cap"] * ws_pre["n_ud"] * MAT["UD"]["t_ply"]         - 2 * ws_pre["n_web"] * MAT["FAB"]["t_ply"] * ws_pre["h_box"]
    rows = []
    for e1 in (0.40, 0.50, 0.60, 0.70):
        sel = (YS >= Y_T0) & (YS <= e1 * B2)
        rows.append(dict(eta1=e1, V_L=0.95 * np.trapezoid(np.where(sel, A_in, 0.0), YS) * 1e3))
    return rows


def main():
    global M_WT_HALF
    os.makedirs(OUT, exist_ok=True)
    vn_diagram()
    # 1. on boyutlandirma (rahatlatmasiz) -> gercek tank kapasitesi -> rahatlatma yakiti
    M_WT_HALF = 0.0
    _, V0, M0, T0 = span_loads()
    ws_pre = size_wing(M0, V0, T0, 2)
    cap_L = ws_pre["V_tank_half_L"]
    M_WT_HALF = min(M_WT_HALF_PARAMS, cap_L * FUEL["density"])
    RES["tank_capacity"] = dict(V_half_L=cap_L, m_half_eff=M_WT_HALF, m_half_params=M_WT_HALF_PARAMS,
                                table=tank_capacity_table(ws_pre))
    Lp, V, M, T = span_loads()
    Uval = validate_k_method()

    # kat plani secimi: flutter >= V_FLUTTER_REQ saglayan en az kat
    trials = []
    chosen = None
    for nf, na in ((1, 1), (2, 1), (2, 2), (3, 1), (3, 3), (4, 4)):
        ws = size_wing(M, V, T, nf, na)
        combos = {}
        for fuel in (True, False):
            wh_, wa_ = rayleigh_freqs(ws, fuel)
            for eta in (0.70, 0.25):   # 0.25: tank icinde (y~0.24 m)
                sp_ = section_params(ws, wh_, wa_, eta, fuel)
                combos[(fuel, eta)] = (flutter_dimensional(sp_), sp_, wh_, wa_)
        key = min(combos, key=lambda k: combos[k][0])
        Vf, sp, wh, wa = combos[key]
        Vdiv = divergence(ws)
        trials.append(dict(n_face=nf, n_aft=na, xcg70=float(np.interp(Y0 + 0.7 * (B2 - Y0), YS, ws["xcg"])), m_wing=ws["m_wing"], f_h=wh / 2 / math.pi, f_a=wa / 2 / math.pi,
                           V_flutter_kmh=Vf * 3.6, V_div_kmh=Vdiv * 3.6,
                           critical=f"{'tank dolu' if key[0] else 'tank bos'}, eta={key[1]:.2f}",
                           combos={f"{'dolu' if k[0] else 'bos'}_eta{k[1]:.2f}": dict(
                               V_kmh=v[0] * 3.6, f_h=v[2] / 2 / math.pi, f_a=v[3] / 2 / math.pi,
                               mu=v[1]["mu"], xa=v[1]["xa"], ra2=v[1]["ra2"]) for k, v in combos.items()}))
        if chosen is None and Vf >= V_FLUTTER_REQ * FLUTTER_MODEL_FACTOR and Vdiv >= V_FLUTTER_REQ:
            chosen = (ws, wh, wa, sp, Vf, Vdiv)
    if chosen is None:
        chosen = (ws, wh, wa, sp, Vf, Vdiv)
    ws, wh, wa, sp, Vf, Vdiv = chosen
    RES["layup_trials"] = trials
    RES["flutter"] = dict(**{k: float(v) for k, v in sp.items()}, V_flutter=Vf, V_flutter_kmh=Vf * 3.6,
                          V_div_kmh=Vdiv * 3.6, f_bend_Hz=wh / 2 / math.pi, f_tors_Hz=wa / 2 / math.pi,
                          V_req_kmh=V_FLUTTER_REQ * 3.6)
    stations = [0.0, Y0, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, B2 * 0.98]
    tab = []
    for y in stations:
        i = min(np.searchsorted(YS, y), NY - 1)
        tab.append(dict(y=float(YS[i]), c=float(chord(YS[i])), h_box_mm=float(ws["h_box"][i] * 1e3),
                        M=float(M[i]), V=float(V[i]), w_cap_mm=float(ws["w_cap"][i] * 1e3), n_ud=int(ws["n_ud"][i]),
                        n_web=int(ws["n_web"][i]), EI=float(ws["EI"][i]), GJ=float(ws["GJ"][i])))
    RES["wing_struct"] = dict(n_face_plies=ws["n_face"], n_aft_plies=ws["n_aft"], t_skin_mm=ws["t_skin"] * 1e3, m_wing=ws["m_wing"],
                              m_wing_params=[i[1] for i in MASS_ITEMS if i[0].startswith("Kanat")][0], tau_skin_max_MPa=ws["tau_skin_max"] / 1e6, stations=tab,
                              SIG_CAP_MPa=SIG_CAP / 1e6, KD=KD)

    # flutter V-g grafigi (secilen) + GJ duyarlilik
    M_f = min(Vf / A_SOUND, 0.9)
    _, ks, res = flutter_speed(sp["mu"], sp["a"], sp["xa"], sp["ra2"], sp["sigma"], math.sqrt(1 - M_f ** 2))
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 7), sharex=True)
    for j, lab in ((0, "mod 1"), (1, "mod 2")):
        Vd = res[:, j, 0] * sp["b"] * sp["wa"] * 3.6
        a1.plot(Vd, res[:, j, 1], label=lab)
        a2.plot(Vd, res[:, j, 2] * sp["wa"] / 2 / math.pi, label=lab)
    for a in (a1, a2):
        a.axvline(V_FLUTTER_REQ * 3.6, color="r", ls=":", label="gereksinim 1.2 VD")
        a.axvline(Vf * 3.6, color="k", ls="--", label=f"flutter {Vf*3.6:.0f} km/h")
        a.grid(alpha=.3)
    a1.axhline(0, color="k", lw=.5)
    a1.set_ylim(-0.6, 0.3)
    a1.set_ylabel("Gereken yapisal sonum g")
    a2.set_ylabel("Frekans [Hz]")
    a2.set_xlabel("Hiz [km/h]")
    a2.set_xlim(0, 2000)
    a1.legend(fontsize=8)
    a1.set_title(f"Kanat V-g (k-yontemi, kritik durum: {[t for t in trials if t['n_face'] == ws['n_face'] and t['n_aft'] == ws['n_aft']][0]['critical']}, "
                 f"{ws['n_face']}/{ws['n_aft']} kat/yuz)", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "flutter_Vg.png"), dpi=130)
    plt.close(fig)

    facs = np.linspace(0.3, 3.0, 25)
    vfs = []
    for f in facs:
        wa_f = wa * math.sqrt(f)
        sp_f = dict(sp, wa=wa_f, sigma=wh / wa_f)
        vfs.append(flutter_dimensional(sp_f) * 3.6)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(facs, vfs, "b-o", ms=3)
    ax.axhline(V_FLUTTER_REQ * 3.6, color="r", ls=":", label="gereksinim 1080 km/h")
    ax.axhline(V_D * 3.6, color="orange", ls=":", label="VD 900 km/h")
    for t in trials:
        pass
    ax.axvline(1.0, color="k", lw=.5)
    ax.set_xlabel("GJ / GJ_secilen")
    ax.set_ylabel("Flutter hizi [km/h]")
    ax.set_title("Flutter hizinin burulma rijitligine duyarliligi")
    ax.grid(alpha=.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "flutter_GJ_duyarlilik.png"), dpi=130)
    plt.close(fig)
    RES["gj_sensitivity"] = [dict(f=float(f), V=float(v)) for f, v in zip(facs, vfs)]

    # kiris kat dagilimi grafigi
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.step(YS, ws["n_ud"], where="mid", label="UD kapak kati (her kapak)")
    ax.step(YS, ws["n_web"], where="mid", label="+-45 web kati (her web)")
    ax.set_xlabel("y [m]")
    ax.set_ylabel("Kat sayisi")
    ax2 = ax.twinx()
    ax2.plot(YS, ws["GJ"], "g--", label="GJ")
    ax2.plot(YS, ws["EI"], "m--", label="EI")
    ax2.set_yscale("log")
    ax2.set_ylabel("Rijitlik [N.m2]")
    ax.legend(loc="upper center", fontsize=8)
    ax2.legend(loc="upper right", fontsize=8)
    ax.axvline(Y0, color="k", ls=":")
    ax.grid(alpha=.3)
    ax.set_title("Kanat kiris kat plani ve rijitlik dagilimi")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "kiris_kat_plani.png"), dpi=130)
    plt.close(fig)

    fuselage_checks()
    control_surface_balance()
    hinge_moments()
    tank_checks(ws)
    skid_checks()
    htail_root()
    RES["_ws_mprime"] = ws["mprime"]
    c0 = chord(0.0)
    A_in0 = (XS_R - XS_F) * c0 * ws["h_box"][0] - 2 * 2 * ws["w_cap"][0] * ws["n_ud"][0] * MAT["UD"]["t_ply"] \
        - 2 * ws["n_web"][0] * MAT["FAB"]["t_ply"] * ws["h_box"][0]
    RES["_ct_tank_L"] = 0.9 * A_in0 * 2 * Y0 * 1e3
    low_wing_attach()
    flap_slotted()
    elevator_flutter_check()
    for k in ("_ws_mprime",):
        RES.pop(k, None)

    def conv(o):
        if isinstance(o, dict):
            return {k: conv(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [conv(v) for v in o]
        if isinstance(o, (np.floating, np.integer, np.bool_)):
            return o.item()
        if isinstance(o, np.ndarray):
            return o.tolist()
        return o
    with open(os.path.join(OUT, "sonuclar.json"), "w", encoding="utf-8") as f:
        json.dump(conv(RES), f, indent=1, ensure_ascii=False)

    # konsol ozeti
    vn, ld, fl = RES["vn"], RES["loads"], RES["flutter"]
    print(f"k-yontemi dogrulama U_F={Uval:.3f} (referans ~2.17)")
    print(f"V-n: VS={vn['VS']*3.6:.0f} VA={vn['VA']*3.6:.0f} km/h, CLa={vn['CLa']:.2f}, Kg={vn['Kg']:.2f}")
    for k, v in vn["gust"].items():
        print(f"   hamle {k}: n(VC)={v['n_VC']:.1f}  n(VD)={v['n_VD']:.1f}")
    print(f"Nihai kok: V={ld['V_root']:.0f} N  M={ld['M_root']:.0f} N.m ; govde yaninda M={ld['M_side']:.0f} N.m ; "
          f"T={ld['T_root_case1']:.1f}/{ld['T_root_case2']:.1f} N.m")
    for t in trials:
        print(f"   kat/yuz={t['n_face']}/{t['n_aft']} xcg70={t['xcg70']:.3f}: kanat {t['m_wing']:.2f} kg, f_h={t['f_h']:.0f} Hz f_a={t['f_a']:.0f} Hz, "
              f"Vf={t['V_flutter_kmh']:.0f} km/h ({t['critical']}), Vdiv={t['V_div_kmh']:.0f} km/h")
        for k, v in t["combos"].items():
            print(f"        {k}: Vf={v['V_kmh']:.0f} f_h={v['f_h']:.0f} f_a={v['f_a']:.0f} mu={v['mu']:.1f} "
                  f"xa={v['xa']:.2f} ra2={v['ra2']:.2f}")
    print(f"Secilen: {RES['wing_struct']['n_face_plies']}/{RES['wing_struct']['n_aft_plies']} kat/yuz, kanat {RES['wing_struct']['m_wing']:.2f} kg; "
          f"flutter {fl['V_flutter_kmh']:.0f} km/h, diverjans {fl['V_div_kmh']:.0f} km/h")
    print("Istasyonlar:")
    for s in tab:
        print(f"   y={s['y']:.3f} c={s['c']:.3f} h={s['h_box_mm']:.1f}mm M={s['M']:.0f} V={s['V']:.0f} "
              f"w_cap={s['w_cap_mm']:.0f}mm UD={s['n_ud']} web={s['n_web']} GJ={s['GJ']:.0f}")
    for k, v in RES["loads"]["cases"].items():
        print(f"   yuk durumu {k}: M_kok={v['M_root']:.0f} M_yan={v['M_side']:.0f} V={v['V_root']:.0f} T={v['T_root']:.1f}")
    tk, sk, ht = RES["tank"], RES["skid"], RES["htail_root"]
    print(f"Tank: ic hacim/yari {tk['V_half_L']:.2f} L (gereken {tk['V_req_L']:.2f} L), p_ult={tk['p_ult']/1e3:.1f} kPa, "
          f"yuz {tk['sig_face_MPa']:.1f} MPa, cekirdek {tk['tau_core_MPa']:.2f} MPa, kaburga {tk['sig_rib_MPa']:.1f} MPa, "
          f"ek kutle {tk['m_tank_extra']*1e3:.0f} g, dengesizlik {tk['dM_roll']:.2f} N.m")
    print(f"Kizak: m_land={sk['m_land']:.2f} kg E={sk['E']:.1f} J n={ {k: round(v, 1) for k, v in sk['n_land'].items()} }, "
          f"F_ult={sk['F_ult']:.0f} N, kayma {sk['slide_m']:.0f} m, kizak sigma={sk['sig_skid_MPa']:.0f} MPa, "
          f"halka {sk['sig_ring_MPa']:.0f} MPa, kabuk tau={sk['tau_shell_MPa']:.1f} MPa, p={sk['p_belly_kPa']:.0f} kPa, "
          f"kuyruk carpma acisi {sk['theta_tail_deg']:.1f} deg, CL_td={sk['CL_td']:.2f}, kizak kutle {sk['m_skid']*1e3:.0f} g")
    print(f"Y.kuyruk koku: L_ult/yari={ht['L_half_ult']:.0f} N, M={ht['M_root']:.1f} N.m, T={ht['T_root']:.1f} N.m, "
          f"pim {ht['F_pin']:.0f} N (cap {ht['pin_cap']:.0f}), yatak t>={ht['t_bearing']*1e3:.2f} mm, soket {ht['F_socket']:.0f} N")
    for tb in ht["tubes"]:
        print(f"      boru D{tb['D']:.0f}x{tb['t']:.1f}: {tb['sigma_MPa']:.0f} MPa {'OK' if tb['ok'] else 'X'} {tb['m_per_m']*1e3:.0f} g/m")
    print(f"Yakit dagilimi: {RES['fuel_split']}")
    lw = RES["low_wing"]
    print(f"Alcak kanat: Y0={lw['Y0']*1e3:.1f} mm, ust yuzey z={lw['z_upper']*1e3:.0f} mm (yan {lw['y_upper_side']*1e3:.0f} mm), "
          f"govde m={lw['m_fus']:.2f} kg x={lw['x_fus_cg']:.3f}")
    for k, v in lw["cases"].items():
        print(f"   A2 {k}: Fz={v['Fz']:.0f} N  R_HK={v['R_LE']:.0f}  R_FK={v['R_TE']:.0f}")
    for k, v in lw["cases_A1"].items():
        print(f"   A1 {k}: R_on={v['R_front']:.0f}  R_arka={v['R_rear']:.0f}")
    print(f"   A1 civata {lw['F_bolt_t_A1']:.0f} N; A2 cerceve t_req={lw['t_frame_req']*1e3:.1f} mm")
    print(f"   M_roll={lw['M_roll']:.0f} N.m (Fv_ult {lw['F_vtail_ult']:.0f} N), civata cekme {lw['F_bolt_tension']:.0f} N "
          f"(M5 12.9 {lw['bolt_cap_t']:.0f}), kesme {lw['F_bolt_shear']:.0f} N; cerceve sigma {lw['sig_frame_MPa']:.0f} MPa; "
          f"carry-through M={lw['M_carry']:.0f}; kesik M={lw['M_cut']:.0f} -> longeron {lw['A_long_req_mm2']} mm2; "
          f"secenekA m={lw['optionA_m']*1e3:.0f} g, B m={lw['optionB']['m']*1e3:.0f} g; merkez tank {lw['center_tank_L']:.2f} L")
    for r_ in lw["longerons"]:
        print(f"      A={r_['A_mm2']:.0f} mm2 eps={r_['eps']*1e6:.0f} ue")
    fl_ = RES["flap"]
    print(f"Flap: Sf={fl_['Sf']*1e4:.0f} cm2 N_lim={fl_['N_lim']:.0f} N N_ult={fl_['N_ult']:.0f}, Mh={fl_['Mh_lim']:.2f} N.m, "
          f"servo {fl_['T_servo_kgcm']:.1f} kg.cm, kapali {[round(v['T_hold_kgcm'],1) for v in fl_['retracted'].values()]}, "
          f"braket {fl_['F_bracket_ult']:.0f} N (pim {fl_['pin_cap']:.0f})")
    ef = RES["elevator_flutter"]
    print(f"Elevator flutter: f_tail={ef['f_tail_bend_Hz']:.0f} Hz, f_req={ef['f_req_Hz']:.0f} Hz, K_req={ef['K_req']:.2f}, "
          f"balans {ef['m_balance']*1e3:.0f} g")
    print(f"Kizak cerceveleri: {RES['skid_frames']}")
    print(f"Tank kapasitesi: {RES['tank_capacity']}")
    fu = RES["fuselage"]
    print(f"Govde: Mmax arka={fu['M_aft_max']:.0f} on={fu['M_fwd_max']:.0f} N.m, kritik x={fu['critical_x']:.2f}, "
          f"max kat={fu['plies_max']}")
    print(f"   motor yatagi civata kesme={fu['engine_mount']['F_bolt_shear']:.0f} N, cekme={fu['engine_mount']['F_bolt_tension']:.0f} N")
    wa_ = fu["wing_attach"]
    print(f"   kanat baglanti: M={wa_['M_side']:.0f} N.m, bicak genisligi (her biri) {wa_['joiner_b_req']*1e3:.1f} mm, "
          f"pim yuku {wa_['F_pin']:.0f} N (M5 kapasite {wa_['pin_shear_cap']:.0f} N), yatak t>={wa_['t_bearing_req']*1e3:.2f} mm")
    for k, v in RES["cs_balance"].items():
        print(f"   {k}: m={v['mass']*1e3:.0f} g, balans {v['m_balance']*1e3:.0f} g @ {v['arm']*1e3:.0f} mm, "
              f"f_req={v['f_req_Hz']:.0f} Hz, K_req={v['K_req']:.1f} N.m/rad")
    for k, v in RES["hinge"].items():
        print(f"   {k}: Chd={v['Ch_delta']:.3f} Cha={v['Ch_alpha']:.3f} -> servo {v['T_req_kgcm']:.1f} kg.cm "
              f"-> sinif {v['servo_class_kgcm']} kg.cm")


if __name__ == "__main__":
    main()
