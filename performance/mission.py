"""
HIZ-750 - gorev profili, kalkis/inis, tirmanma, yakit butcesi, hava alik boyut kontrolu,
elektrik guc butcesi.

Calistir: python performance/mission.py   ->  performance/out/
sizing.py'deki itki/surukleme modelini, params.py'deki kutleleri kullanir.
"""
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import params as P          # noqa: E402
import sizing as SZ         # noqa: E402

OUT = os.path.join(ROOT, "performance", "out")
G = 9.80665

D = dict(SZ.DESIGN, engine="JetCat P400-PRO")
M_TO = P.mass_summary(1.0)["m"]
M_EMPTY = P.mass_summary(0.0)["m"]
RHO_FUEL = P.FUEL["density"]


def fuel_flow_kgs(throttle_thrust_frac):
    """Model turbinlerde yakit debisi itkiyle ~dogrusal + rolanti payi."""
    ff_max = P.ENGINE["fuel_flow_max"] * RHO_FUEL / 60.0
    ff_idle = 0.12 * ff_max
    return ff_idle + (ff_max - ff_idle) * throttle_thrust_frac


def takeoff(m, mu=0.04, CL_g=0.35, CLmax_to=0.80, h_obs=10.0, m_dolly=2.0):
    """Dolly kalkisi: ucak dolly uzerinde sabit kalkis acisinda; dolly kutlesi de hizlandirilir."""
    rho = SZ.isa(D["alt_m"], D["dT"])[0]
    S = D["S"]
    Vs = math.sqrt(2 * m * G / (rho * S * CLmax_to))
    V_lof = 1.2 * Vs
    v, x, t, dt = 0.0, 0.0, 0.0, 0.01
    while v < V_lof:
        T = SZ.thrust(D, max(v, 1.0))
        q = 0.5 * rho * v * v
        cd0 = sum(SZ.cd0_breakdown(D, max(v, 5), rho, *SZ.isa(D["alt_m"])[1:]).values())
        Dg = q * S * (cd0 + 0.03 + CL_g ** 2 / (math.pi * 0.8 * 5))  # +0.03 dolly + flap 10 deg
        L = q * S * CL_g
        a = (T - Dg - mu * (m * G - L + m_dolly * G)) / (m + m_dolly)
        v += a * dt
        x += v * dt
        t += dt
    # gecis + tirmanma ile 10 m engel (Raymer yaklasik)
    T = SZ.thrust(D, V_lof)
    gamma = math.asin(min(0.9, (T - SZ.drag(D, V_lof, m)[0] - 0.01 * 0.5 * rho * V_lof ** 2 * S) / (m * G)))
    R = (1.15 * Vs) ** 2 / (0.2 * G)
    h_tr = R * (1 - math.cos(gamma))
    if h_tr >= h_obs:
        # engel gecis yayi icinde asiliyor
        x_air = math.sqrt(R ** 2 - (R - h_obs) ** 2)
    else:
        x_air = R * math.sin(gamma) + (h_obs - h_tr) / math.tan(gamma)
    return dict(Vs=Vs, V_lof=V_lof, s_ground=x, t_ground=t, s_total=x + x_air,
                gamma_deg=math.degrees(gamma))


def landing(m, CLmax_land=0.92, mu_brake=0.40, h_obs=10.0):
    """Kizakla govde inisi (cim, mu~0.4). CLmax 30 deg flapla (aero analizi)."""
    rho = SZ.isa(D["alt_m"], D["dT"])[0]
    S = D["S"]
    Vs = math.sqrt(2 * m * G / (rho * S * CLmax_land))
    V_app = 1.3 * Vs
    V_td = 1.15 * Vs
    gamma = math.radians(4.0)
    s_air = h_obs / math.tan(gamma) + (V_app ** 2 - V_td ** 2) / (2 * G * 0.25)
    # yer kosusu: flap+gear surukleme, rolanti itki ihmal, frenli
    s_free = V_td * 1.0
    a_mean = G * (mu_brake + 0.03)
    s_brake = V_td ** 2 / (2 * a_mean)
    return dict(Vs=Vs, V_app=V_app, V_td=V_td, s_air=s_air, s_ground=s_free + s_brake,
                s_total=s_air + s_free + s_brake)


def climb_curve(m):
    Vs = np.linspace(40, 260, 120)
    roc = []
    for v in Vs:
        T = SZ.thrust(D, v)
        Dr = SZ.drag(D, v, m)[0]
        roc.append((T - Dr) * v / (m * G))
    return Vs, np.array(roc)


def turn_perf(m, V):
    """Surekli donus: T = D(n). Yapisal limit n=12 ile karsilastir."""
    rho, a, mu = SZ.isa(D["alt_m"], D["dT"])
    q = 0.5 * rho * V * V
    S = D["S"]
    cd0 = sum(SZ.cd0_breakdown(D, V, rho, a, mu).values())
    k = 1 / (math.pi * 0.8 * 5)
    T = SZ.thrust(D, V)
    CL = math.sqrt(max(0.0, (T / (q * S) - cd0) / k))
    n_sust = CL * q * S / (m * G)
    CL_inst = 0.9
    n_inst = CL_inst * q * S / (m * G)
    return n_sust, n_inst


def mission():
    """Hiz denemesi gorev profili: her bacak (ad, sure s, itki orani, ort. hiz m/s)."""
    legs = [
        ("Motor calistirma + isinma + taksi", 90, 0.08, 0),
        ("Kalkis + tirmanma (tam gaz)", 25, 1.00, 60),
        ("Isinma turu 400-550 km/h", 60, 0.45, 135),
        ("Olcum gecisi #1 (750-780 km/h)", 20, 0.78, 212),
        ("Donus (dusuk gaz, 8-10 g)", 25, 0.35, 160),
        ("Olcum gecisi #2 (ters yon)", 20, 0.78, 212),
        ("Donus", 25, 0.35, 160),
        ("Olcum gecisi #3 (yedek)", 20, 0.78, 212),
        ("Donus", 25, 0.35, 160),
        ("Olcum gecisi #4 (yedek, ters yon)", 20, 0.78, 212),
        ("Yavaslama + inis paterni", 75, 0.20, 50),
        ("Inis + taksi + motor sogutma", 60, 0.06, 0),
    ]
    rows, total = [], 0.0
    for name, t, thr, v in legs:
        f = fuel_flow_kgs(thr) * t
        total += f
        rows.append((name, t, thr, v * 3.6, f))
    return rows, total


def inlet_check():
    rho, a, _ = SZ.isa(D["alt_m"], D["dT"])
    A_cap = P.INLET["width"] * P.INLET["height"]
    mdot = P.ENGINE["mdot_air"]
    out = []
    for V in (60, 150, 208, 222):
        A_inf = mdot / (rho * V)
        out.append((V * 3.6, A_inf, A_inf / A_cap))
    # motor yuzu hizi (statik): kompresor giris capi ~0.6*D
    A_face = math.pi * (0.6 * P.ENGINE["diameter"]) ** 2 / 4
    return A_cap, A_face, out


POWER_ITEMS = [
    # (ad, ortalama A, tepe A, gerilim V)
    ("Kanatcik servolari 2x (HV)", 0.8, 6.0, 8.4),
    ("Flap servolari 2x", 0.2, 4.0, 8.4),
    ("Elevator servolari 2x", 0.6, 6.0, 8.4),
    ("Rudder servosu", 0.2, 3.0, 8.4),
    ("Burun tekeri dumen servosu", 0.1, 2.0, 8.4),
    ("Elektrikli retract + fren", 0.1, 5.0, 8.4),
    ("Alici x2 + telemetri", 0.25, 0.3, 8.4),
    ("GNSS logger + hava veri", 0.15, 0.2, 8.4),
    ("Gyro/stabilizasyon unitesi", 0.1, 0.15, 8.4),
]


def power_budget(flight_min=12.0):
    avg = sum(i[1] for i in POWER_ITEMS)
    peak = sum(i[2] for i in POWER_ITEMS)
    mAh = avg * flight_min / 60 * 1000
    return avg, peak, mAh


def main():
    os.makedirs(OUT, exist_ok=True)
    L = []
    p = L.append
    p(f"MTOW {M_TO:.2f} kg, bos (yakitsiz) {M_EMPTY:.2f} kg")
    to = takeoff(M_TO)
    p(f"Kalkis (dolly): Vs(CLmax 0.8, flap 10)={to['Vs']*3.6:.0f} km/h, V_lof={to['V_lof']*3.6:.0f} km/h, "
      f"yer kosusu {to['s_ground']:.0f} m ({to['t_ground']:.1f} s), 10 m engele {to['s_total']:.0f} m, "
      f"tirmanis acisi {to['gamma_deg']:.0f} deg")
    m_land = M_EMPTY + 0.25 * P.FUEL["mass"]
    ld = landing(m_land)
    p(f"Kizakla inis ({m_land:.1f} kg): Vs={ld['Vs']*3.6:.0f}, V_app={ld['V_app']*3.6:.0f}, "
      f"V_td={ld['V_td']*3.6:.0f} km/h; yer kosusu {ld['s_ground']:.0f} m, 10 m'den toplam {ld['s_total']:.0f} m")
    Vs_, roc = climb_curve(M_TO)
    i = int(np.argmax(roc))
    p(f"Azami tirmanma hizi {roc[i]:.0f} m/s @ {Vs_[i]*3.6:.0f} km/h (MTOW)")
    for V in (150, 208):
        ns, ni = turn_perf(M_TO, V)
        p(f"Donus @ {V*3.6:.0f} km/h: surekli n={ns:.1f} g, anlik (CL 0.9) n={ni:.0f} g -> "
          f"yapisal limit {P.N_LIMIT:.0f} g ile sinirli" if ni > P.N_LIMIT else
          f"Donus @ {V*3.6:.0f} km/h: surekli n={ns:.1f} g, anlik n={ni:.1f} g")
    rows, total = mission()
    p("\nGorev profili (hiz denemesi):")
    p(f"  {'Bacak':40s} {'sure s':>6s} {'itki%':>6s} {'km/h':>6s} {'yakit kg':>8s}")
    for r in rows:
        p(f"  {r[0]:40s} {r[1]:6.0f} {100*r[2]:6.0f} {r[3]:6.0f} {r[4]:8.3f}")
    t_tot = sum(r[1] for r in rows)
    p(f"  TOPLAM {t_tot/60:.1f} dk, yakit {total:.2f} kg ({total/RHO_FUEL:.2f} L); "
      f"tank {P.FUEL['mass']:.1f} kg -> rezerv {P.FUEL['mass']-total:.2f} kg "
      f"(%{100*(P.FUEL['mass']-total)/P.FUEL['mass']:.0f})")
    A_cap, A_face, rows_in = inlet_check()
    p(f"\nHava alik: capture alani {A_cap*1e4:.1f} cm2, kompresor yuzu ~{A_face*1e4:.0f} cm2")
    for v, a_inf, mfr in rows_in:
        p(f"  {v:4.0f} km/h: serbest akim tupu {a_inf*1e4:5.1f} cm2, MFR={mfr:.2f}")
    avg, peak, mAh = power_budget()
    p(f"\nElektrik: ort {avg:.2f} A, tepe {peak:.1f} A @ 2S HV (8.4 V); 12 dk icin {mAh:.0f} mAh "
      f"-> 2x 2S 3000 mAh LiPo (yedekli, %50+ pay)")
    txt = "\n".join(L)
    print(txt)
    with open(os.path.join(OUT, "performans_ozet.txt"), "w", encoding="utf-8") as f:
        f.write(txt + "\n")

    # grafikler
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(Vs_ * 3.6, roc, label="MTOW")
    Vs2, roc2 = climb_curve(M_EMPTY + 0.3 * P.FUEL["mass"])
    ax.plot(Vs2 * 3.6, roc2, label="%30 yakit")
    ax.set_xlabel("Hiz [km/h]"); ax.set_ylabel("Tirmanma hizi [m/s]")
    ax.set_title("Fazla guc / tirmanma performansi"); ax.grid(alpha=.3); ax.legend()
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "tirmanma.png"), dpi=130); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    t0, ts, vs, fuel_left = 0, [0], [0], [P.FUEL["mass"]]
    for r in rows:
        t0 += r[1]
        ts.append(t0); vs.append(r[3]); fuel_left.append(fuel_left[-1] - r[4])
    ax.step(np.array(ts) / 60, vs, where="pre", label="hiz [km/h]")
    ax2 = ax.twinx()
    ax2.plot(np.array(ts) / 60, fuel_left, "r-", label="kalan yakit [kg]")
    ax.set_xlabel("Zaman [dk]"); ax.set_ylabel("Hiz [km/h]"); ax2.set_ylabel("Yakit [kg]", color="r")
    ax.set_title("Hiz denemesi gorev profili"); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "gorev_profili.png"), dpi=130); plt.close(fig)


if __name__ == "__main__":
    main()
