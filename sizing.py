"""
750 km/h RC jet - kavramsal boyutlandirma ve performans hesabi.

Calistir:  python sizing.py
Ciktilar:  out/ klasorune grafikler + konsola ozet tablo.

Yontem:
  - ISA atmosfer
  - Bilesen bazli parazit surukleme (Raymer: Cf * FF * Q * Swet / Sref)
  - Korn denklemi ile surukleme diverjans Mach'i, Lock 4. kuvvet dalga suruklemesi
  - Basit turbojet itki dususu modeli: F(V) = F0 * (1 - V/Vj) * (1 + kram*M^2)
  - Tmax(V) = D(V) dengesinden azami yatay hiz
Tum varsayimlar DESIGN sozlugunde; degistirip tekrar calistirin.
"""
import math
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

G = 9.80665
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")

# ---------------------------------------------------------------- motorlar
# F0 [N] statik itki, m [kg] motor kutlesi, ff [kg/min] tam gazda yakit
# Vj [m/s] tahmini ozgul itki ~ nozul cikis hizi (kucuk turbojetlerde 450-600)
ENGINES = {
# Kaynak: JetCat/Kingtech veri sayfalari (2026). Vj tahmin, olculmedi.
    "Xicoy X240": dict(F0=240.0, m=1.82, ff=0.60, Vj=500.0),
    "JetCat P300-PRO": dict(F0=300.0, m=2.73, ff=0.78, Vj=520.0),
    "JetCat P400-PRO": dict(F0=425.0, m=4.05, ff=1.11, Vj=540.0),
    "Kingtech K-450G4+": dict(F0=450.0, m=4.00, ff=1.10, Vj=540.0),
}

# ---------------------------------------------------------------- tasarim
DESIGN = dict(
    name="HIZ-750",
    engine="JetCat P400-PRO",
    # agirlik dokumu [kg]
    m_struct=6.76,      # iter3: params MTOW 17.01 kg ile esitlendi      # govde+kanat+kuyruk (karbon/epoksi prepreg)
    m_systems=2.2,     # servolar, aku, alici, telemetri, GNSS logger, ECU, pompa, valf
    m_gear=0.0,        # iter2: inis takimi yok (dolly + kizak; kizak m_struct icinde)
    m_fuel=4.0,        # ~5.0 L Jet-A1/kerosen (0.80 kg/L)
    # kanat
    S=0.42,            # referans alan [m^2]
    AR=5.0,
    taper=0.35,
    sweep_le=28.0,     # hucum kenari ok acisi [deg]
    tc=0.07,           # kok kalinlik orani (ince, NACA 64A007 tipi)
    xc_max=0.40,       # max kalinlik konumu
    kappa_a=0.87,      # Korn teknoloji faktoru (konvansiyonel kesit)
    e=0.80,
    CLmax_land=1.15,   # kanatcik/flap ile
    # govde (donel cisim yaklasimi)
    L_fus=2.10,
    d_fus=0.165,
    # kuyruk (V-kuyruk yok; konvansiyonel H+V, ince %6)
    S_ht=0.085,
    S_vt=0.060,
    tc_tail=0.06,
    c_tail=0.20,
    # ilave suruklemeler (hava alik, egzoz, antenler, mentese bosluklari) oran
    misc_frac=0.15,    # iter3: yari gomulu dorsal alik (~49 cm2 on kesit) + tasma payi (kotumser birakildi)
    # itki modeli
    k_ram=0.60,        # dinamik basinc kazanci (hava alik verimine bagli)
    inlet_loss=0.04,   # hava alik + egzoz borusu itki kaybi
    # ortam
    alt_m=300.0,
    dT=0.0,            # ISA sicaklik sapmasi [K]
)


def isa(h, dT=0.0):
    T = 288.15 - 0.0065 * h + dT
    p = 101325.0 * (1 - 0.0065 * h / 288.15) ** 5.2559
    rho = p / (287.05 * T)
    a = math.sqrt(1.4 * 287.05 * T)
    mu = 1.458e-6 * T ** 1.5 / (T + 110.4)
    return rho, a, mu


def cf_turb(Re, M):
    return 0.455 / (math.log10(Re) ** 2.58 * (1 + 0.144 * M * M) ** 0.65)


def geom(d):
    S, AR, lam = d["S"], d["AR"], d["taper"]
    b = math.sqrt(S * AR)
    cr = 2 * S / (b * (1 + lam))
    ct = lam * cr
    mac = 2 / 3 * cr * (1 + lam + lam * lam) / (1 + lam)
    # yari-veter ceyrek ok acisi
    tan_le = math.tan(math.radians(d["sweep_le"]))
    tan_c4 = tan_le - (cr - ct) / (2 * b) * 1.0  # 0.25*(cr-ct)/(b/2)
    sweep_c4 = math.atan(tan_c4)
    tan_tmax = tan_le - d["xc_max"] * (cr - ct) / (b / 2)
    sweep_tmax = math.atan(tan_tmax)
    # govdeyle ortulen kanat alani dusulur
    S_exp = S - cr * d["d_fus"]
    return dict(b=b, cr=cr, ct=ct, mac=mac, sweep_c4=sweep_c4,
                sweep_tmax=sweep_tmax, S_exp=S_exp)


def mass(d):
    eng = ENGINES[d["engine"]]
    return d["m_struct"] + d["m_systems"] + d["m_gear"] + d["m_fuel"] + eng["m"]


def cd0_breakdown(d, V, rho, a, mu):
    g = geom(d)
    M = V / a
    S = d["S"]
    out = {}
    # kanat
    Re = rho * V * g["mac"] / mu
    tc = d["tc"]
    FF = (1 + 0.6 / d["xc_max"] * tc + 100 * tc ** 4) * \
         (1.34 * M ** 0.18 * math.cos(g["sweep_tmax"]) ** 0.28)
    Swet = 2 * (1 + 0.2 * tc) * g["S_exp"]
    out["kanat"] = cf_turb(Re, M) * FF * 1.0 * Swet / S
    # govde
    f = d["L_fus"] / d["d_fus"]
    Re = rho * V * d["L_fus"] / mu
    FF = 1 + 60 / f ** 3 + f / 400
    Swet = math.pi * d["d_fus"] * d["L_fus"] * (1 - 2 / f) ** (2 / 3) * (1 + 1 / f ** 2)
    out["govde"] = cf_turb(Re, M) * FF * 1.0 * Swet / S
    # kuyruklar
    Re = rho * V * d["c_tail"] / mu
    tc = d["tc_tail"]
    FF = (1 + 0.6 / 0.3 * tc + 100 * tc ** 4) * (1.34 * M ** 0.18 * 0.95)
    for k in ("S_ht", "S_vt"):
        Swet = 2 * (1 + 0.2 * tc) * d[k]
        out["yatay kuyruk" if k == "S_ht" else "dikey kuyruk"] = \
            cf_turb(Re, M) * FF * 1.04 * Swet / S
    base = sum(out.values())
    out["diger (alik/egzoz/bosluk)"] = base * d["misc_frac"]
    return out


def m_dd(d, CL):
    g = geom(d)
    c = math.cos(g["sweep_c4"])
    return d["kappa_a"] / c - d["tc"] / c ** 2 - CL / (10 * c ** 3)


def drag(d, V, m=None):
    rho, a, mu = isa(d["alt_m"], d["dT"])
    m = mass(d) if m is None else m
    W = m * G
    q = 0.5 * rho * V * V
    S = d["S"]
    CL = W / (q * S)
    cd0 = sum(cd0_breakdown(d, V, rho, a, mu).values())
    cdi = CL * CL / (math.pi * d["e"] * d["AR"])
    M = V / a
    Mdd = m_dd(d, CL)
    Mcr = Mdd - (0.1 / 80) ** (1 / 3)
    cdw = 20 * (M - Mcr) ** 4 if M > Mcr else 0.0
    return q * S * (cd0 + cdi + cdw), dict(CL=CL, CD0=cd0, CDi=cdi, CDw=cdw,
                                           M=M, Mdd=Mdd, Mcr=Mcr, q=q)


def thrust(d, V):
    eng = ENGINES[d["engine"]]
    rho, a, _ = isa(d["alt_m"], d["dT"])
    sigma = rho / 1.225
    M = V / a
    F = eng["F0"] * sigma * (1 - V / eng["Vj"]) * (1 + d["k_ram"] * M * M)
    return F * (1 - d["inlet_loss"])


def vmax(d, m=None):
    lo, hi = 50.0, 330.0
    f = lambda V: thrust(d, V) - drag(d, V, m)[0]
    if f(hi) > 0:
        return hi
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def report(d):
    g = geom(d)
    eng = ENGINES[d["engine"]]
    m = mass(d)
    m_dry = m - d["m_fuel"]
    rho, a, mu = isa(d["alt_m"], d["dT"])
    rho0 = isa(0)[0]
    V = vmax(d)
    Vlight = vmax(d, m_dry + 0.3 * d["m_fuel"])
    D, info = drag(d, V)
    bd = cd0_breakdown(d, V, rho, a, mu)
    Vs = math.sqrt(2 * m_dry * 1.15 * G / (rho0 * d["S"] * d["CLmax_land"]))
    endurance = d["m_fuel"] / eng["ff"]
    lines = []
    P = lines.append
    P(f"=== {d['name']}  /  motor: {d['engine']} ===")
    P(f"Kanat: b={g['b']:.3f} m  S={d['S']:.3f} m2  AR={d['AR']}  cr={g['cr']:.3f}  ct={g['ct']:.3f}  "
      f"MAC={g['mac']:.3f} m  Lambda_c/4={math.degrees(g['sweep_c4']):.1f} deg  t/c={d['tc']}")
    P(f"Govde: L={d['L_fus']} m  d={d['d_fus']} m  (incelik {d['L_fus']/d['d_fus']:.1f})")
    P(f"Kutle: MTOW={m:.2f} kg  bos+%15 yakit inis={m_dry*1.15:.2f} kg  yakit={d['m_fuel']} kg")
    P(f"Kanat yuklemesi: {m/d['S']:.1f} kg/m2   T/W statik: {eng['F0']/(m*G):.2f}")
    P(f"Stall (inis agirligi, deniz sev.): {Vs:.1f} m/s = {Vs*3.6:.0f} km/h ; yaklasma 1.3Vs = {1.3*Vs*3.6:.0f} km/h")
    P(f"--- Azami yatay hiz (h={d['alt_m']:.0f} m, dT={d['dT']:+.0f} K) ---")
    P(f"Vmax (tam yakit)   = {V:.1f} m/s = {V*3.6:.0f} km/h  (M={V/a:.3f})")
    P(f"Vmax (%30 yakit)   = {Vlight:.1f} m/s = {Vlight*3.6:.0f} km/h")
    P(f"Vmax'ta: T=D={D:.0f} N  q={info['q']/1000:.1f} kPa  CL={info['CL']:.4f}  "
      f"CD0={info['CD0']:.5f}  CDi={info['CDi']:.6f}  CDw={info['CDw']:.6f}")
    P(f"Korn Mdd={info['Mdd']:.3f}  Mcrit~{info['Mcr']:.3f}  (uçuş M={info['M']:.3f})")
    P("CD0 dagilimi:")
    for k, v in bd.items():
        P(f"   {k:28s} {v:.5f}  ({100*v/info['CD0']:.0f}%)")
    P(f"Tam gaz yakit suresi: {endurance:.1f} dk")
    # yuk
    n_lim = 12.0
    R = V * V / (G * math.sqrt(n_lim ** 2 - 1))
    P(f"--- Yapisal ---")
    P(f"Limit yuk n={n_lim:.0f}g, nihai {1.5*n_lim:.0f}g; Vmax'ta {n_lim:.0f}g donus yaricapi {R:.0f} m")
    P(f"Tasarim dalis hizi VD=1.15*Vmax={1.15*V*3.6:.0f} km/h -> flutter marji hedefi 1.2*VD={1.38*V*3.6:.0f} km/h")
    # kok egilme momenti (eliptik dagilim, yari kanat yuku merkezi 4/(3pi)*b/2)
    Mroot = n_lim * 1.5 * m * G / 2 * (4 / (3 * math.pi)) * g["b"] / 2
    P(f"Nihai kok egilme momenti ~ {Mroot:.0f} N.m (spar boyutlandirma girdisi)")
    hinge_q = info["q"]
    P(f"Vmax dinamik basinci {hinge_q/1000:.1f} kPa -> aileron mentese momenti hesabi gerekli (bkz. rapor)")
    return "\n".join(lines), V


def plot_curves(d):
    Vs = np.linspace(40, 300, 300)
    T = [thrust(d, v) for v in Vs]
    D = [drag(d, v)[0] for v in Vs]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(Vs * 3.6, T, label=f"Kullanilabilir itki ({d['engine']})")
    ax.plot(Vs * 3.6, D, label="Gereken itki (surukleme)")
    for name in ENGINES:
        if name == d["engine"]:
            continue
        dd = dict(d, engine=name)
        ax.plot(Vs * 3.6, [thrust(dd, v) for v in Vs], "--", alpha=.6, label=f"itki: {name}")
    ax.axvline(750, color="r", ls=":", label="hedef 750 km/h")
    V = vmax(d)
    ax.plot(V * 3.6, thrust(d, V), "ko")
    ax.annotate(f"{V*3.6:.0f} km/h", (V * 3.6, thrust(d, V)), textcoords="offset points", xytext=(-60, 10))
    ax.set_xlabel("Hiz [km/h]")
    ax.set_ylabel("Kuvvet [N]")
    ax.set_title(f"{d['name']} - itki/surukleme dengesi")
    ax.grid(alpha=.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "itki_surukleme.png"), dpi=130)
    plt.close(fig)


def plot_sweep(d):
    """Kanat alani ve motor secimine gore Vmax haritasi."""
    Ss = np.linspace(0.30, 0.65, 15)
    fig, ax = plt.subplots(figsize=(8, 5))
    for name in ENGINES:
        vs = []
        for S in Ss:
            dd = dict(d, S=S, engine=name)
            # yapi kutlesini alanla olcekle (~ 9 kg/m2 kanat + sabit govde)
            dd["m_struct"] = d["m_struct"] + 9.0 * (S - d["S"])
            vs.append(vmax(dd) * 3.6)
        ax.plot(Ss, vs, marker="o", ms=3, label=name)
    ax.axhline(750, color="r", ls=":")
    ax.set_xlabel("Kanat alani S [m2]")
    ax.set_ylabel("Vmax [km/h]")
    ax.set_title("Kanat alani - motor secimi trade study")
    ax.grid(alpha=.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "trade_S_motor.png"), dpi=130)
    plt.close(fig)


def plot_3view(d):
    g = geom(d)
    b2, cr, ct = g["b"] / 2, g["cr"], g["ct"]
    L, dia = d["L_fus"], d["d_fus"]
    x_le = 0.42 * L  # kanat kok hucum kenari
    dx_tip = math.tan(math.radians(d["sweep_le"])) * b2
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 5), gridspec_kw=dict(width_ratios=[1.3, 1]))
    # ust gorunus
    for s in (1, -1):
        a1.fill([x_le, x_le + dx_tip, x_le + dx_tip + ct, x_le + cr],
                [0, s * b2, s * b2, 0], color="#8aa", ec="k")
        # yatay kuyruk
        ht_b2 = math.sqrt(d["S_ht"] * 4.0) / 2
        ht_cr = 2 * d["S_ht"] / (2 * ht_b2 * 1.4)
        xh = L - ht_cr - 0.05
        a1.fill([xh, xh + 0.6 * ht_b2, xh + 0.6 * ht_b2 + 0.4 * ht_cr, xh + ht_cr],
                [0, s * ht_b2, s * ht_b2, 0], color="#aac", ec="k")
    xs = np.linspace(0, L, 200)
    r = dia / 2 * np.clip(np.sqrt(np.sin(np.pi * np.clip(xs / L * 0.95 + 0.0, 0, 1)) ), 0, 1)
    r[xs > 0.85 * L] = np.maximum(r[xs > 0.85 * L], 0.035)
    a1.fill_between(xs, -r, r, color="#ccc", ec="k")
    a1.set_aspect("equal")
    a1.set_title(f"Ust gorunus  b={g['b']:.2f} m, L={L:.2f} m")
    a1.grid(alpha=.2)
    # yan gorunus
    a2.fill_between(xs, -r, r, color="#ccc", ec="k")
    vt_h = math.sqrt(d["S_vt"] * 1.6)
    vt_cr = 2 * d["S_vt"] / (vt_h * 1.4)
    xv = L - vt_cr - 0.02
    a2.fill([xv, xv + 0.9 * vt_h, xv + 0.9 * vt_h + 0.4 * vt_cr, xv + vt_cr],
            [r.max() * 0.5, r.max() * 0.5 + vt_h, r.max() * 0.5 + vt_h, r.max() * 0.5], color="#aac", ec="k")
    a2.plot([x_le, x_le + cr], [0, 0], "k", lw=3)
    a2.annotate("NACA ust hava alik\n(govde ustu, kanat arkasi)", (0.55 * L, r.max()), xytext=(0.2 * L, 0.35),
                arrowprops=dict(arrowstyle="->"), fontsize=8)
    a2.set_aspect("equal")
    a2.set_title("Yan gorunus")
    a2.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "uc_gorunus.png"), dpi=130)
    plt.close(fig)


def sensitivity(d):
    rows = []
    base = vmax(d) * 3.6
    cases = [
        ("dT +15 K (sicak yaz)", dict(dT=15.0)),
        ("rakim 1000 m", dict(alt_m=1000.0)),
        ("misc surukleme %25", dict(misc_frac=0.25)),
        ("Vj -10% (motor modeli kotumser)", None),
        ("k_ram = 0.3", dict(k_ram=0.3)),
        ("t/c 0.09", dict(tc=0.09)),
        ("yuzey %20 laminer (cilali)", "lam"),
    ]
    for name, mod in cases:
        if mod is None:
            saved = ENGINES[d["engine"]]["Vj"]
            ENGINES[d["engine"]]["Vj"] = saved * 0.9
            v = vmax(d) * 3.6
            ENGINES[d["engine"]]["Vj"] = saved
        elif mod == "lam":
            v = vmax(dict(d, misc_frac=d["misc_frac"] - 0.08)) * 3.6
        else:
            v = vmax(dict(d, **mod)) * 3.6
        rows.append(f"   {name:34s} {v:6.0f} km/h  ({v-base:+.0f})")
    return "Duyarlilik (taban {:.0f} km/h):\n".format(base) + "\n".join(rows)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    txt, V = report(DESIGN)
    print(txt)
    print(sensitivity(DESIGN))
    for name in ENGINES:
        print(f"Motor {name:18s}: Vmax = {vmax(dict(DESIGN, engine=name))*3.6:.0f} km/h")
    plot_curves(DESIGN)
    plot_sweep(DESIGN)
    plot_3view(DESIGN)
    with open(os.path.join(OUT, "ozet.txt"), "w", encoding="utf-8") as f:
        f.write(txt + "\n" + sensitivity(DESIGN) + "\n")
    print(f"Grafikler: {OUT}")
