"""
HIZ-750 - hava alik / S-kanal toplam basinc kazanimi (pressure recovery) ve itki etkisi.

Calistir: python performance/inlet_analysis.py  ->  performance/out/alik_*.png, alik_ozet.txt

Yontem (yari-ampirik, CFD yerine):
  1. Govde sinir tabakasi (turbulans, 1/7 ust profil), dudak onundeki 7 derece rampa ile kalinlasma
  2. Yari gomulu dudagin yuttugu sinir tabaka -> kutle-agirlikli toplam basinc kaybi
  3. Ic kayiplar: dudak (MFR'ye bagli), surtunme (f L/Dh), S-bukum (K_s, ofset/uzunluk'a bagli),
     difuzor (verim eta_d) - hepsi dudak ici dinamik basinc ile olceklenir
  4. Itki etkisi: model turbojette sabit RPM'de kutle debisi ~ pt2, itki ~ pt2 kabulu
     -> sizing.py'deki k_ram esdegeri
Girdi: params.py (INLET, ENGINE), cad/out/cad_report.json (varsa kanal geometrisi).
"""
import json
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import params as P   # noqa: E402
import sizing as SZ  # noqa: E402

OUT = os.path.join(ROOT, "performance", "out")
GAM = 1.4

I = P.INLET
A_CAP = I["width"] * I["height"]
A_FACE = 125e-4                       # CAD: motor yuzundeki kanal kesiti [m2]
L_DUCT = I["duct_length"]
OFFSET = 0.088                         # CAD: dudak merkezi - motor ekseni dikey ofseti [m]
R_FUS = P.FUSELAGE["d_max"] / 2
BURY = R_FUS - (I["lip_z_center"] - I["height"] / 2)   # dudak alt kenarinin govde yuzeyinin altinda kalan kismi [m]
RAMP_THICKENING = 1.5                  # 7 deg rampada sinir tabaka kalinlasmasi (ampirik, NACA gomulu alik verisi araligi 1.3-1.8)


def pt_over_p(M):
    return (1 + (GAM - 1) / 2 * M * M) ** (GAM / (GAM - 1))


def boundary_layer(V, x, nu):
    Re = V * x / nu
    return 0.37 * x / Re ** 0.2


def ingested_recovery(Minf, delta, h_cap, bury):
    """Dudak kesitinin alt `bury`+... kismina giren sinir tabakanin kutle-agirlikli pt orani.
    Dudak alt kenari rampa tabanina (duvar) yakin kabul edilir: kesitte y=0 duvar."""
    y = np.linspace(1e-5, h_cap, 2000)
    u = np.where(y < delta, (y / delta) ** (1 / 7), 1.0)
    # statik basinc sabit, sicaklik Crocco-Busemann ile adyabatik duvar yaklasimi
    T_ratio = 1 + (GAM - 1) / 2 * Minf ** 2 * (1 - u ** 2)    # T/T_inf
    M_loc = Minf * u / np.sqrt(T_ratio)
    rho_ratio = 1 / T_ratio
    w = rho_ratio * u                                        # kutle akisi agirligi
    pt_loc = pt_over_p(M_loc) / pt_over_p(Minf)
    return float(np.trapezoid(w * pt_loc, y) / np.trapezoid(w, y)), float(np.trapezoid(w, y) / h_cap)


def internal_losses(MFR, Minf):
    """Ic kayiplari serbest akim dinamik basincina orani (Delta pt / q_inf) olarak."""
    q_ratio_lip = MFR ** 2          # dudak ici q / q_inf (sikistirilamaz yaklasim)
    K_lip = 0.02 if MFR <= 1.0 else 0.02 + 0.25 * (MFR - 1.0) ** 2   # MFR>1: dudak ayrilmasi (kalkis)
    Dh = 4 * A_CAP / (2 * (I["width"] + I["height"]))
    f = 0.020
    AR = A_FACE / A_CAP
    K_fric = f * L_DUCT / Dh * (1 + 1 / AR ** 2) / 2          # ortalama kesit hizi
    K_s = 0.06 * (OFFSET / L_DUCT / 0.3) ** 2                  # S-bukum (Wellborn/ESDU tipi veri araligi 0.03-0.08 @ o/L 0.3)
    eta_d = 0.90
    K_diff = (1 - eta_d) * (1 - 1 / AR ** 2)
    K_tot = K_lip + K_fric + K_s + K_diff
    return K_tot * q_ratio_lip, dict(K_lip=K_lip, K_fric=K_fric, K_s=K_s, K_diff=K_diff, AR=AR, Dh=Dh)


def analyse(V):
    D = SZ.DESIGN
    rho, a, mu = SZ.isa(D["alt_m"], D["dT"])
    nu = mu / rho
    M = V / a
    delta0 = boundary_layer(V, I["x_lip"], nu)
    delta = delta0 * RAMP_THICKENING
    mdot = P.ENGINE["mdot_air"] * (1 + 0.6 * M * M)           # ram ile debi artisi (sizing ile tutarli)
    MFR = mdot / (rho * V * A_CAP)
    eta_bl, mass_frac = ingested_recovery(M, delta, I["height"], BURY)
    dpt_q, k = internal_losses(MFR, M)
    q = 0.5 * GAM * M * M          # q / p
    eta_int = 1 - dpt_q * q / pt_over_p(M)
    eta_r = eta_bl * eta_int
    ram_ideal = pt_over_p(M)
    ram_eff = eta_r * ram_ideal
    k_eff = (ram_eff - 1) / (M * M) if M > 0.05 else float("nan")
    return dict(V=V, M=M, delta0=delta0, delta=delta, MFR=MFR, eta_bl=eta_bl, eta_int=eta_int,
                eta_r=eta_r, ram_ideal=ram_ideal, ram_eff=ram_eff, k_ram_eff=k_eff, **k)


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = [analyse(v / 3.6) for v in (150, 300, 450, 600, 750, 800)]
    L = []
    p = L.append
    p(f"Capture {A_CAP*1e4:.1f} cm2, motor yuzu {A_FACE*1e4:.0f} cm2 (AR {A_FACE/A_CAP:.2f}), "
      f"kanal {L_DUCT*1000:.0f} mm, ofset/uzunluk {OFFSET/L_DUCT:.3f}, dudak gomulme {BURY*1000:.0f} mm")
    p(f"{'km/h':>5} {'M':>5} {'d_SL mm':>8} {'MFR':>5} {'eta_SL':>7} {'eta_ic':>7} {'eta_r':>7} "
      f"{'ram ideal':>9} {'ram eff':>8} {'k_ram':>6}")
    for r in rows:
        p(f"{r['V']*3.6:5.0f} {r['M']:5.3f} {r['delta']*1000:8.1f} {r['MFR']:5.2f} {r['eta_bl']:7.4f} "
          f"{r['eta_int']:7.4f} {r['eta_r']:7.4f} {r['ram_ideal']:9.4f} {r['ram_eff']:8.4f} {r['k_ram_eff']:6.3f}")
    r750 = rows[4]
    p(f"\nIc kayip katsayilari (dudak ici q'ya gore) @750: lip {r750['K_lip']:.3f}, surtunme {r750['K_fric']:.3f}, "
      f"S-bukum {r750['K_s']:.3f}, difuzor {r750['K_diff']:.3f}")
    # sizing'e etkisi
    base = dict(SZ.DESIGN, engine="JetCat P400-PRO")
    v_base = SZ.vmax(base) * 3.6
    k_new = r750["k_ram_eff"]
    cases = [("sizing tabani (k_ram 0.60, kayip %4)", base),
             (f"alik analizi (k_ram {k_new:.2f}, egzoz kaybi %2)", dict(base, k_ram=k_new, inlet_loss=0.02)),
             ("kotumser (+%2 pt kaybi)", dict(base, k_ram=(r750['ram_eff'] * 0.98 - 1) / r750['M'] ** 2, inlet_loss=0.02))]
    p("\nVmax etkisi:")
    for name, d in cases:
        v = SZ.vmax(d) * 3.6
        t750 = SZ.thrust(d, 750 / 3.6)
        p(f"  {name:45s} Vmax {v:4.0f} km/h ({v-v_base:+.0f}), T@750 {t750:4.0f} N")
    txt = "\n".join(L)
    print(txt)
    with open(os.path.join(OUT, "alik_ozet.txt"), "w", encoding="utf-8") as f:
        f.write(txt + "\n")
    with open(os.path.join(OUT, "alik_sonuclar.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1)

    Vs = np.linspace(80, 900, 60)
    rr = [analyse(v / 3.6) for v in Vs]
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.plot(Vs, [r["eta_r"] for r in rr], label="toplam $\\eta_r$")
    ax.plot(Vs, [r["eta_bl"] for r in rr], "--", label="sinir tabaka yutma")
    ax.plot(Vs, [r["eta_int"] for r in rr], ":", label="ic kayiplar")
    ax.axvline(750, color="r", ls=":", lw=1)
    ax.set_xlabel("Hiz [km/h]"); ax.set_ylabel("$p_{t2}/p_{t\\infty}$")
    ax.set_title("Alik toplam basinc kazanimi (yari-ampirik)"); ax.grid(alpha=.3); ax.legend()
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "alik_kazanim.png"), dpi=130); plt.close(fig)


if __name__ == "__main__":
    main()
