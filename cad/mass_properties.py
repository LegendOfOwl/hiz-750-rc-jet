"""
HIZ-750 - CAD tabanli kutle ozellikleri (iter4, masa basi dogrulama).

params.MASS_ITEMS kalemleri cad/out/step/*.step katilarina eslenir; her katinin
hacim-agirlikli (birim yogunluk) agirlik merkezi ve atalet tensoru OCP GProp ile
hesaplanir ve kalem kutlesine olceklenir. Katisi olmayan kalemler params (x, z)
konumunda kucuk homojen kutu (analitik) olarak eklenir; y konumlari asagida.
Yakit: tank ic hacimleri x 0.80 kg/L, %100 / %25 / %0 doluluk (her tanktan ayni oran).

Cikti: cad/out/mass_properties.json
Eksenler: CAD (x burundan arkaya, y sag kanat, z yukari), sonuclar [m], [kg m^2],
CG etrafinda. Ixz = +int(x z dm) (ucus dinamigi isareti); govde ucus ekseninde
(x ileri, z asagi) iki eksen birden ters dondugu icin Ixz isareti aynidir.

    C:/Users/Urungu/.hz750/Scripts/python cad/mass_properties.py
"""
import json
import os
import sys

import numpy as np
import cadquery as cq
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import params as P  # noqa: E402

STEP = os.path.join(ROOT, "cad", "out", "step")
OUT = os.path.join(ROOT, "cad", "out", "mass_properties.json")
MM = 1e-3
T_TANK_WALL_MM = 1.0       # build_cad.tank_inner_volume(tank_fuselage, 1.0) ile ayni
FILLS = (1.0, 0.25, 0.0)

_cache = {}


def load(name):
    if name not in _cache:
        _cache[name] = cq.importers.importStep(os.path.join(STEP, name + ".step")).val()
    return _cache[name]


def gprops(shape, kind="volume"):
    """Birim yogunlukla (V [mm3] veya A [mm2], merkez [mm], tensor CG etrafinda [mm^5 / mm^4])."""
    g = GProp_GProps()
    w = shape.wrapped
    if kind == "volume":
        BRepGProp.VolumeProperties_s(w, g)
    else:
        BRepGProp.SurfaceProperties_s(w, g)
    c = g.CentreOfMass()
    M = g.MatrixOfInertia()
    J = np.array([[M.Value(i, j) for j in (1, 2, 3)] for i in (1, 2, 3)])
    return g.Mass(), np.array([c.X(), c.Y(), c.Z()]), J


class Body:
    """Kutle m [kg], CG r [m], kendi CG'si etrafinda tensor J [kg m^2] (gercek tensor, J13 = -int xz)."""

    def __init__(self, name, m, r, J, src):
        self.name, self.m, self.r, self.J, self.src = name, m, np.asarray(r, float), np.asarray(J, float), src


def solid_body(item, m, parts, kind="volume", shape=None):
    shp = shape if shape is not None else _fuse([load(p) for p in parts])
    q, c, J = gprops(shp, kind)
    # birim yogunluk -> rho = m / q ;  J [mm^5] * rho [kg/mm^3] -> kg mm^2 -> *1e-6 m^2
    Jm = J * (m / q) * 1e-6
    return Body(item, m, c * MM, Jm, "+".join(parts) + ("" if kind == "volume" else " (yuzey)")), q


def _fuse(shapes):
    s = shapes[0]
    for t in shapes[1:]:
        s = s.fuse(t)
    return s.clean() if len(shapes) > 1 else s


def box_body(item, m, r, dims, src="nokta/kutu"):
    a, b, c = dims
    J = m / 12 * np.diag([b * b + c * c, a * a + c * c, a * a + b * b])
    return Body(item, m, r, J, src + f" {a*1e3:.0f}x{b*1e3:.0f}x{c*1e3:.0f} mm")


def combine(bodies, name="toplam"):
    m = sum(b.m for b in bodies)
    r = sum(b.m * b.r for b in bodies) / m
    J = np.zeros((3, 3))
    for b in bodies:
        d = b.r - r
        J += b.J + b.m * (np.dot(d, d) * np.eye(3) - np.outer(d, d))
    return Body(name, m, r, J, "")


def report(b):
    J = b.J
    return dict(m=round(b.m, 4), cg_m=[round(v, 5) for v in b.r],
                Ixx=round(J[0, 0], 4), Iyy=round(J[1, 1], 4), Izz=round(J[2, 2], 4),
                Ixz=round(-J[0, 2], 4), Ixy=round(-J[0, 1], 5), Iyz=round(-J[1, 2], 5))


# ----------------------------------------------------------------------- kalem -> katı eslemesi
# Not: wing_box (kiris arasi kutu) tum aciklik boyunca wing_panels ile ust uste biner ve
# kanat tanklarini da icerir; bu yuzden kanat icin panels U center U box birlesimi alinir.
WING_PARTS = ["wing_panels", "wing_center", "wing_box", "aileron_L", "aileron_R", "flap_L", "flap_R"]
SOLID_MAP = {
    "Govde kabugu": ["fuselage"],
    "Kanat (": WING_PARTS,
    "Yatay kuyruk": ["htail", "elevator_L", "elevator_R", "ht_carry_yoke"],
    "Dikey kuyruk": ["vtail", "rudder"],
    "Motor yatagi": ["engine"],                  # yatak + kalkan motor boyunca dagilir varsayimi
    "Hava alik": ["inlet_duct"],
    "Egzoz": ["exhaust_pipe"],
    "Bulkhead": ["frames"],                       # 5 cerceve halkasi (kizak + kanat baglanti)
    "Motor JetCat": ["engine"],
    "Govde alti kizak": ["skid"],
    "Kuyruk tamponu": ["tail_bumper"],
}
SURFACE_MAP = {
    "Yakit tanki + hopper": ["tank_fuselage"],    # tank duvari = govde tanki yuzeyi (alan agirlikli)
}
# Kanat baglantisi: frames katisinin kanat baglanti cerceveleri (x 1.006 / 1.156) bolgesi
ATTACH_X_MM = (960.0, 1200.0)

# Katisi olmayan kalemler: (y dagilimi listesi [(y [m], pay)], kutu olculeri [m], not)
POINT_MAP = {
    "Motor bolgesi isi kecesi": ([(0.0, 1.0)], (0.30, 0.10, 0.01), "motor alti plaka"),
    "ECU + pompa": ([(0.0, 1.0)], (0.10, 0.07, 0.05), "merkez hatti"),
    "Servolar: aileron+flap": ([(+0.22, .25), (-0.22, .25), (+0.50, .25), (-0.50, .25)],
                               (0.04, 0.03, 0.012), "flap servolari +-0.22 m, aileron +-0.50 m"),
    "Servolar: elevator": ([(+0.035, 1 / 3), (-0.035, 1 / 3), (0.0, 1 / 3)], (0.04, 0.02, 0.04),
                           "elevator 2x y=+-0.035 m, rudder y=0"),
    "Kontrol yuzeyi balans": ([(+0.53, .5), (-0.53, .5)], (0.06, 0.01, 0.01),
                              "aileron orta acikligi y=+-0.53 m (elevator/rudder balansi ihmal)"),
    "Alici x2": ([(0.0, 1.0)], (0.08, 0.05, 0.03), "merkez hatti"),
    "Aku": ([(0.0, 1.0)], (0.12, 0.05, 0.04), "merkez hatti (2 paket ust uste)"),
    "Burun balasti": ([(0.0, 1.0)], (0.06, 0.04, 0.03), "burun, merkez hatti"),
    "Pitot + hava veri": ([(0.0, 1.0)], (0.60, 0.06, 0.04), "kablo demeti 0.6 m boyunca"),
    "Boya / dolgu": ([(0.0, 1.0)], (1.80, 0.16, 0.16), "nokta kutle (govde boyu kutu); gercekte islak alana dagilir"),
}

FUEL_TANKS = ["tank_fuselage", "tank_center", "tank_wing_L", "tank_wing_R"]


def match(name, table):
    for k, v in table.items():
        if name.startswith(k):
            return v
    return None


def build_items():
    bodies, rows = [], []
    for name, m, x, z in P.MASS_ITEMS:
        sol, srf, pt = match(name, SOLID_MAP), match(name, SURFACE_MAP), match(name, POINT_MAP)
        if name.startswith("Kanat baglantisi"):
            fr = load("frames")
            cut = fr.intersect(cq.Solid.makeBox(ATTACH_X_MM[1] - ATTACH_X_MM[0], 400, 400,
                                                cq.Vector(ATTACH_X_MM[0], -200, -200)))
            b, q = solid_body(name, m, ["frames[x960-1200]"], shape=cut)
        elif sol:
            b, q = solid_body(name, m, sol)
        elif srf:
            b, q = solid_body(name, m, srf, kind="surface")
        elif pt:
            ys, dims, note = pt
            subs = [box_body(name, m * w, (x, y, z), dims) for y, w in ys]
            b = combine(subs, name)
            b.src = f"kutu {dims[0]*1e3:.0f}x{dims[1]*1e3:.0f}x{dims[2]*1e3:.0f} mm, {note}"
        else:
            raise KeyError("eslesmeyen kalem: " + name)
        bodies.append(b)
        rows.append(dict(item=name, m=m, x_params=x, z_params=z, x_cad=round(b.r[0], 4),
                         y_cad=round(b.r[1], 4), z_cad=round(b.r[2], 4),
                         dx_mm=round((b.r[0] - x) * 1e3, 1), dz_mm=round((b.r[2] - z) * 1e3, 1),
                         src=b.src))
    return bodies, rows


def fuel_tanks():
    tanks = {}
    for t in FUEL_TANKS:
        s = load(t)
        V, c, J = gprops(s)
        if t == "tank_fuselage":       # dis katı; ic hacim = V - A*t (build_cad ile ayni)
            A = gprops(s, "surface")[0]
            Vin = V - A * T_TANK_WALL_MM
        else:                           # kanat/orta tanklari zaten ic bosluk katisi
            Vin = V
        tanks[t] = dict(V_L=Vin * 1e-6, c=c * MM, J_unit=J, V_solid=V)
    return tanks


def fuel_bodies(tanks, frac):
    out = []
    for t, d in tanks.items():
        m = d["V_L"] * P.FUEL["density"] * frac
        if m <= 0:
            continue
        out.append(Body("yakit:" + t, m, d["c"], d["J_unit"] * (m / d["V_solid"]) * 1e-6, t))
    return out


def roskam(m):
    """aero/aero_analysis.py [5] bolumundeki tahminin aynisi (salt okunur kopya)."""
    b = P.wing_geom()["b"]
    L = P.FUSELAGE["length"]
    return dict(Ixx=m * (b * 0.25 / 2) ** 2, Iyy=m * (L * 0.38 / 2) ** 2,
                Izz=m * ((b + L) / 2 * 0.52 / 2) ** 2, Rx=0.25, Ry=0.38, Rz=0.52)


def main():
    bodies, rows = build_items()
    dry = combine(bodies, "kuru")
    tanks = fuel_tanks()
    cap_L = sum(d["V_L"] for d in tanks.values())
    cap_kg = cap_L * P.FUEL["density"]

    cases = {}
    for f in FILLS:
        cases[f"{int(f*100)}%"] = (f, combine(bodies + fuel_bodies(tanks, f), f"yakit {f:.0%}"))
    # params esdegeri: params FUEL["mass"] (4.0 kg) kadar yakit, ayni oranla
    f_par = P.FUEL["mass"] / cap_kg
    cases["params_4.0kg"] = (f_par, combine(bodies + fuel_bodies(tanks, f_par), "params yakit"))

    res, checks = {}, {}
    for key, (f, b) in cases.items():
        r = report(b)
        r["fuel_frac_of_capacity"] = round(f, 4)
        r["fuel_kg"] = round(f * cap_kg, 4)
        # params karsilastirmasi: ayni yakit KUTLESI icin mass_summary
        ms = P.mass_summary(f * cap_kg / P.FUEL["mass"])
        ms_nom = P.mass_summary(f) if key != "params_4.0kg" else ms
        r["check"] = dict(
            params_same_fuel_mass=dict(m=round(ms["m"], 4), x_cg=round(ms["x_cg"], 5), z_cg=round(ms["z_cg"], 5)),
            dm_pct=round(100 * (b.m - ms["m"]) / ms["m"], 3),
            dx_mm=round((b.r[0] - ms["x_cg"]) * 1e3, 2),
            dz_mm=round((b.r[2] - ms["z_cg"]) * 1e3, 2),
            params_nominal_frac=dict(m=round(ms_nom["m"], 4), x_cg=round(ms_nom["x_cg"], 5),
                                     dm_pct=round(100 * (b.m - ms_nom["m"]) / ms_nom["m"], 3),
                                     dx_mm=round((b.r[0] - ms_nom["x_cg"]) * 1e3, 2)),
        )
        r["check"]["ok_mass_1pct"] = bool(abs(r["check"]["params_nominal_frac"]["dm_pct"]) <= 1.0)
        r["check"]["ok_xcg_5mm"] = bool(abs(r["check"]["params_nominal_frac"]["dx_mm"]) <= 5.0)
        rk = roskam(b.m)
        r["roskam_same_mass"] = {k: round(v, 4) for k, v in rk.items()}
        r["ratio_cad_over_roskam"] = {k: round(r[k] / rk[k], 3) for k in ("Ixx", "Iyy", "Izz")}
        # CAD'den esdeger (Roskam tanimli) boyutsuz atalet yaricaplari
        bw, L = P.wing_geom()["b"], P.FUSELAGE["length"]
        r["Rbar_cad"] = dict(Rx=round(2 * np.sqrt(r["Ixx"] / b.m) / bw, 3),
                             Ry=round(2 * np.sqrt(r["Iyy"] / b.m) / L, 3),
                             Rz=round(4 * np.sqrt(r["Izz"] / b.m) / (bw + L), 3))
        res[key] = r
    # aero_analysis'in kullandigi deger: m = mass_summary(1.0)["m"]
    m_aero = P.mass_summary(1.0)["m"]
    rk_aero = roskam(m_aero)
    aero_cmp = {k: dict(aero=round(rk_aero[k], 4), cad_100=res["100%"][k], cad_params=res["params_4.0kg"][k],
                        ratio_100=round(res["100%"][k] / rk_aero[k], 3),
                        ratio_params=round(res["params_4.0kg"][k] / rk_aero[k], 3))
                for k in ("Ixx", "Iyy", "Izz")}
    aero_cmp["Ixz"] = dict(aero=0.0, cad_100=res["100%"]["Ixz"], cad_params=res["params_4.0kg"]["Ixz"])

    # kanat icin alan agirlikli alternatif (duyarlilik)
    wing_item = next(i for i in P.MASS_ITEMS if i[0].startswith("Kanat ("))
    wb_s, _ = solid_body("kanat-yuzey", wing_item[1], ["wing_panels", "aileron_L", "aileron_R", "flap_L", "flap_R"],
                         kind="surface")
    wb_v = next(b for b in bodies if b.name.startswith("Kanat ("))
    sens = dict(wing_volume=dict(r=[round(v, 4) for v in wb_v.r], Ixx_self=round(wb_v.J[0, 0], 4)),
                wing_surface_exposed=dict(r=[round(v, 4) for v in wb_s.r], Ixx_self=round(wb_s.J[0, 0], 4)))

    out = dict(
        iteration="4 - masa basi dogrulama",
        script="cad/mass_properties.py",
        units=dict(length="m", mass="kg", inertia="kg m^2"),
        axes="CAD: x burundan arkaya, y sag, z yukari; tensor CG etrafinda. Ixz=+int(xz dm) "
             "(ucus ekseninde x ileri/z asagi iken de ayni isaret). Ixy, Iyz ~0 (simetri).",
        fuel=dict(density_kg_L=P.FUEL["density"], capacity_L=round(cap_L, 4), capacity_kg=round(cap_kg, 4),
                  params_fuel_kg=P.FUEL["mass"],
                  tanks={t: dict(V_L=round(d["V_L"], 4), cg_m=[round(v, 4) for v in d["c"]])
                         for t, d in tanks.items()},
                  model="her tanktan ayni oranda bosalma; yakit tank katisinin hacim merkezinde ve "
                        "olceklenmis tensoruyla (serbest yuzey / dibe cokme ihmal)"),
        cases=res,
        dry=report(dry),
        aero_roskam_comparison=aero_cmp,
        wing_weighting_sensitivity=sens,
        items=rows,
    )
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)

    # ---------------------------------------------------------------- konsol ozeti
    print(f"{'kalem':44s} {'m':>5s} {'x_par':>6s} {'x_cad':>6s} {'dx mm':>6s} {'dz mm':>6s}  kaynak")
    for r in rows:
        print(f"{r['item'][:44]:44s} {r['m']:5.2f} {r['x_params']:6.3f} {r['x_cad']:6.3f} "
              f"{r['dx_mm']:6.1f} {r['dz_mm']:6.1f}  {r['src']}")
    print(f"\nyakit kapasitesi {cap_L:.3f} L = {cap_kg:.3f} kg; tanklar:",
          {t: round(d['V_L'], 3) for t, d in tanks.items()})
    for k, r in res.items():
        c = r["check"]
        print(f"[{k:12s}] m={r['m']:.3f} cg=({r['cg_m'][0]:.4f},{r['cg_m'][1]:.4f},{r['cg_m'][2]:.4f}) "
              f"Ixx={r['Ixx']:.3f} Iyy={r['Iyy']:.3f} Izz={r['Izz']:.3f} Ixz={r['Ixz']:.4f} | "
              f"ayni yakit: dm={c['dm_pct']:+.2f}% dx={c['dx_mm']:+.1f} mm dz={c['dz_mm']:+.1f} mm | "
              f"nominal: dm={c['params_nominal_frac']['dm_pct']:+.2f}% dx={c['params_nominal_frac']['dx_mm']:+.1f} mm"
              f" | CAD/Roskam {r['ratio_cad_over_roskam']} Rbar {r['Rbar_cad']}")
    print("aero karsilastirma:", json.dumps(aero_cmp))
    print("kanat duyarlilik:", json.dumps(sens))
    print("->", OUT)


if __name__ == "__main__":
    main()
