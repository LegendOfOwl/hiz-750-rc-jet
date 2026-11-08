"""HIZ-750 - yatay/dikey kuyruk icin KABA 2-DOF flutter tahmini (iter5 inceleme, Grup 1).

Amac: kuyruk flutter'i icin bir yapisal model yok (docs/04: yalniz elevator balansi ve yatay kuyruk egilme
frekansi ~154 Hz). Bu betik tipik kesit (Hodges & Pierce k-yontemi, structures.flutter_speed) ile, %70
yari aciklikta, ok acisina dik kesitte (V_n = V cosL, b_n = b cosL, M_n <= 0.9 Prandtl-Glauert) V_F'yi
BILINMEYEN parametrelerin bir araliginda tarar ve 1080 km/h (1.2 V_D) ve 1350 km/h (x1.25 model payi) icin
GEREKEN kuyruk burulma frekansini verir. Bu bir tasarim degeri DEGILDIR; GVT/FE icin hedef uretir.

Varsayimlar (hepsi dogrulanmamis):
  * Yuzey kutlesi: params MASS_ITEMS (yatay 0.30 kg, dikey 0.20 kg); %70'i yuzey, aciklikta uniform
    (kalan boru/soket/balans koke yakin). Kesit atalet yaricapi^2 r^2 = 0.25 b^2 (ince sandvic yuzey).
  * EA %35c (tek boru/kiris), kesit CG %40-50c araliginda taranir (balansli elevator/rudder).
  * Egilme frekansi: yatay 154 Hz (structures.elevator_flutter_check), dikey 0.7x (govde esnekligi ve
    daha uzun kok veteri belirsiz: 60-150 Hz taranir).
  * Kok ankastre, govde rijit, kumanda yuzeyi serbestligi YOK (balans + rijit baglanti varsayimi).
Bu nedenle sonuc govde-kuyruk-kumanda bagli flutter icin bir alt sinir DEGILDIR (bkz. docs/04 / Grup 1 raporu).

Calistir: python structures/kuyruk_flutter.py  ->  structures/out/kuyruk_flutter.json
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import structures as ST  # noqa: E402
from params import HTAIL, VTAIL, MASS_ITEMS, V_FLUTTER_REQ, surface_geom, vtail_geom  # noqa: E402

TARGETS_KMH = (V_FLUTTER_REQ * 3.6, V_FLUTTER_REQ * 3.6 * ST.FLUTTER_MODEL_FACTOR)


def vf_kmh(m_span, c, sweep_ea_deg, x_ea, x_cg, r2_b, f_b, f_t):
    cl = math.cos(math.radians(sweep_ea_deg))
    b = 0.5 * c * cl                               # dik kesit yari veter
    m = m_span * cl                                # dik kesit birim boy kutlesi
    mu = m / (math.pi * ST.RHO0 * b ** 2)
    a = (x_ea - 0.5) / 0.5
    xa = (x_cg - x_ea) * c * cl / b
    ra2 = r2_b + xa ** 2                           # EA etrafinda
    wa, wh = 2 * math.pi * f_t, 2 * math.pi * f_b
    V = 200.0
    for _ in range(40):
        Mn = min(V * cl / ST.A_SOUND, 0.9)
        Uf, _, _ = ST.flutter_speed(mu, a, xa, ra2, wh / wa, math.sqrt(1 - Mn ** 2))
        Vn = Uf * b * wa
        Vnew = Vn / cl
        if not math.isfinite(Vnew) or abs(Vnew - V) < 0.5:
            V = Vnew
            break
        V = 0.5 * (V + Vnew)
    return V * 3.6, mu


FT_GRID = np.arange(100.0, 801.0, 10.0)


def required_ft(vgrid, target):
    """Izgarada V_F >= hedef olan ve ustundeki her f_T'de oyle kalan en kucuk f_T (f_T < f_B bolgesindeki
    yapay yuksek V_F'ler sayilmaz). Saglanamiyorsa None."""
    ok = np.asarray(vgrid) >= target
    if not ok[-1]:
        return None
    k = len(ok) - 1
    while k > 0 and ok[k - 1]:
        k -= 1
    return float(FT_GRID[k])


def surface(name, m_total, span, c_ref, sweep_le, taper_cr_ct, f_bends):
    cr, ct = taper_cr_ct
    sweep_ea = math.degrees(math.atan(math.tan(math.radians(sweep_le)) - 0.35 * (cr - ct) / span))
    m_span = 0.7 * m_total / span
    rows = []
    for xcg in (0.40, 0.45, 0.50):
        for fb in f_bends:
            args = (m_span, c_ref, sweep_ea, 0.35, xcg, 0.25 * (0.5 * c_ref * math.cos(math.radians(sweep_ea))) ** 2
                    / (0.5 * c_ref * math.cos(math.radians(sweep_ea))) ** 2, fb)
            vgrid = [vf_kmh(*args, ft)[0] for ft in FT_GRID]
            req = [required_ft(vgrid, t) for t in TARGETS_KMH]
            vf = {ft: round(vf_kmh(*args, ft)[0]) for ft in (150, 250, 350, 500)}
            rows.append(dict(xcg=xcg, f_bend_Hz=fb, mu=round(vf_kmh(*args, 300)[1], 1),
                             f_t_req_1080_Hz=req[0], f_t_req_1350_Hz=req[1], Vf_kmh_vs_ft=vf))
    return dict(name=name, m_surface_kg=m_total, span_m=span, c70_m=c_ref, sweep_ea_deg=sweep_ea, rows=rows)


def main():
    m_h = next(i[1] for i in MASS_ITEMS if i[0].startswith("Yatay kuyruk")) / 2   # yari kuyruk
    m_v = next(i[1] for i in MASS_ITEMS if i[0].startswith("Dikey kuyruk"))
    hg, vg = surface_geom(HTAIL), vtail_geom()
    sh = hg["b"] / 2
    c70h = hg["cr"] + 0.7 * (hg["ct"] - hg["cr"])
    c70v = vg["cr"] + 0.7 * (vg["ct"] - vg["cr"])
    res = dict(note=__doc__.split("\n\n")[1], targets_kmh=TARGETS_KMH,
               htail=surface("yatay kuyruk (yari)", m_h, sh, c70h, HTAIL["sweep_le"], (hg["cr"], hg["ct"]), (100.0, 154.0)),
               vtail=surface("dikey kuyruk", m_v, vg["h"], c70v, VTAIL["sweep_le"], (vg["cr"], vg["ct"]), (60.0, 108.0, 150.0)))
    os.makedirs(ST.OUT, exist_ok=True)
    with open(os.path.join(ST.OUT, "kuyruk_flutter.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    for k in ("htail", "vtail"):
        s = res[k]
        print(f"{s['name']}: m {s['m_surface_kg']:.3f} kg, aciklik {s['span_m']:.3f} m, c70 {s['c70_m']:.3f} m, "
              f"EA ok {s['sweep_ea_deg']:.1f} deg")
        for r in s["rows"]:
            fmt = lambda v: f"{v:.0f}" if v else "-"
            print(f"   xcg {r['xcg']:.2f} f_B {r['f_bend_Hz']:.0f} Hz mu {r['mu']}: gereken f_T 1080 -> "
                  f"{fmt(r['f_t_req_1080_Hz'])} Hz, 1350 -> {fmt(r['f_t_req_1350_Hz'])} Hz | V_F(f_T) {r['Vf_kmh_vs_ft']}")


if __name__ == "__main__":
    main()
