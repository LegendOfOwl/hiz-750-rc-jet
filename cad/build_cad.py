"""
HIZ-750 parametrik CAD modeli + teknik cizimler.

Calistir (cadquery venv):
    C:/Users/Urungu/.hz750/Scripts/python cad/build_cad.py

Tum olculer params.py'den okunur; CAD icinde birim mm'dir.
Ciktilar cad/out/ altina yazilir:
    step/*.step, stl/*.stl, HIZ750_assembly.step,
    HIZ750_3view.dxf/.png/.pdf, HIZ750_inboard.png/.pdf, HIZ750_iso.png,
    cad_report.json
"""
import json
import math
import os
import shutil
import sys
import tempfile

import numpy as np
from scipy.interpolate import PchipInterpolator

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import params as P  # noqa: E402

import cadquery as cq  # noqa: E402
from cadquery import Vector as V  # noqa: E402

OUT = os.path.join(ROOT, "cad", "out")
MM = 1000.0
T_SKIN = 1.5           # govde duvar kalinligi [mm]
T_DUCT = 2.0           # alik kanali duvari [mm]
T_TE = 0.3             # firar kenari min. kalinligi [mm]
ENG_CLEAR = 3.0        # motor - govde ic yuzeyi min. radyal bosluk hedefi [mm]
T_TANK_SKIN = 2.6      # kanat tanki: sandvic kabuk kalinligi [mm] (yapi ajani kat plani)
T_TANK_WEB = 1.5       # kanat tanki: kiris web kalinligi [mm]
T_TANK_RIB = 3.0       # kanat tanki: uc kaburga kalinligi [mm]
FLAP_SLOT = 2.5        # yarikli flap: panel - flap burnu arasi veter yonlu bosluk [mm]
RAMP_DEG = 7.0         # yari gomulu dudak onundeki rampa acisi [deg]
WING_LOWER_SKIN = 1.5  # govde icinde arka kiris gerisinde kalan kanat alt kabugu [mm]
FRAME_T = 4.0          # cerceve kalinligi (x yonu) [mm]
FRAME_D = 5.0          # cerceve radyal derinligi [mm]
WING_INFO = {}
RAMP_INFO = {}

# ====================================================================== profiller
# NACA 64A010 ordinatlari (Abbott & von Doenhoff, Theory of Wing Sections, App. I).
# 64A00x kalinlik dagilimi = 64A010 * (t/c / 0.10)  (simetrik seri icin standart olcekleme
# yaklasimi; gercek 64A00x ordinatlariyla fark < %1 c mertebesinde, kavramsal CAD icin yeterli).
_X64 = np.array([0, .5, .75, 1.25, 2.5, 5, 7.5, 10, 15, 20, 25, 30, 35, 40, 45, 50,
                 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]) / 100
_Y64 = np.array([0, .804, .969, 1.225, 1.688, 2.327, 2.805, 3.199, 3.813, 4.272, 4.606,
                 4.837, 4.968, 4.995, 4.894, 4.684, 4.388, 4.021, 3.597, 3.127, 2.623,
                 2.103, 1.582, 1.062, .541, .021]) / 100
# burun yaricapina uygun interpolasyon icin sqrt(x) uzayinda PCHIP
_I64 = PchipInterpolator(np.sqrt(_X64), _Y64)


def half_thickness(name, x):
    """Normalize yari kalinlik y_t(x/c). name: 'naca64a007', 'naca0006' ..."""
    name = name.lower()
    if name.startswith("naca64a"):
        tc = int(name[-3:]) / 100.0
        return _I64(np.sqrt(x)) * tc / 0.10
    if name.startswith("naca00"):
        tc = int(name[-2:]) / 100.0
        return 5 * tc * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x ** 2
                         + 0.2843 * x ** 3 - 0.1036 * x ** 4)
    raise ValueError(name)


def airfoil(name, n=45):
    """Ust (TE->LE) ve alt (LE->TE) normalize koordinatlar, kosinus dagilim."""
    b = np.linspace(0, math.pi, n)
    x = 0.5 * (1 - np.cos(b))
    yt = half_thickness(name, x)
    up = np.column_stack([x[::-1], yt[::-1]])
    lo = np.column_stack([x[1:], -yt[1:]])
    return up, lo


def section_area_factor(name):
    x = np.linspace(0, 1, 400)
    return 2 * np.trapezoid(half_thickness(name, x), x)


# ====================================================================== yardimcilar
def sect_wire(name, c, xle, ystat, z0, twist_deg, plane="xz", te=T_TE, toff=0.0):
    """Bir kesit teli. plane='xz': kanat/yatay kuyruk (aciklik y), 'xy': dikey kuyruk (aciklik z)."""
    up, lo = airfoil(name)
    a = math.radians(twist_deg)
    pts = []
    sgn = np.concatenate([np.ones(len(up)), -np.ones(len(lo))])
    for (X, Z), sg in zip(np.vstack([up, lo]), sgn):
        Z = Z + sg * 0.5 * te / c * X
        dx, dz = (X - 0.25) * c, Z * c
        if toff:                       # ic yuzey: kabuk kalinligi kadar iceri (dik ofset yaklasimi)
            dz = sg * max(abs(dz) - toff, 0.15)
        rx = dx * math.cos(a) + dz * math.sin(a)
        rz = -dx * math.sin(a) + dz * math.cos(a)
        px = xle + 0.25 * c + rx
        if plane == "xz":
            pts.append(V(px, ystat, z0 + rz))
        else:
            pts.append(V(px, rz, ystat))
    sp = cq.Edge.makeSpline(pts)
    ln = cq.Edge.makeLine(pts[-1], pts[0])
    return cq.Wire.assembleEdges([sp, ln])


def plan(xle0, c0, sweep, b_half, taper):
    """Planform fonksiyonlari (mm): x_le(s), c(s) yari-aciklik s [0..b_half]."""
    ct = taper * c0
    t = math.tan(math.radians(sweep))
    return (lambda s: xle0 + s * t), (lambda s: c0 + (ct - c0) * s / b_half)


def prism(pts_xy, z0=-400, h=800):
    return cq.Workplane("XY").workplane(offset=z0).polyline(pts_xy).close().extrude(h).val()


def prism_xz(pts_xz, y0=-400, h=800):
    """XZ duzleminde poligon, y boyunca ekstruzyon (dikey kuyruk icin)."""
    wp = cq.Workplane("XZ", origin=(0, 0, 0)).polyline(pts_xz).close().extrude(-h)
    return wp.val().translate(V(0, y0, 0))


def box(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cyl_x(r, x0, x1, y=0, z=0):
    return cq.Solid.makeCylinder(r, x1 - x0, V(x0, y, z), V(1, 0, 0))


def vol(s):
    try:
        return s.Volume()
    except Exception:
        return 0.0


def inter_vol(a, b):
    try:
        return vol(a.intersect(b))
    except Exception:
        return float("nan")


def export(shape, path, **kw):
    """Uzun yol sorununa karsi once kisa gecici klasore yaz, sonra tasi."""
    tmpd = tempfile.mkdtemp(prefix="hz", dir="C:/Users/Urungu/.hz750")
    tmp = os.path.join(tmpd, "o" + os.path.splitext(path)[1])
    cq.exporters.export(shape, tmp, **kw)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    shutil.move(tmp, path)
    shutil.rmtree(tmpd, ignore_errors=True)


# ====================================================================== govde profili
F = P.FUSELAGE
R = F["d_max"] / 2 * MM
LN = F["x_dmax_start"] * MM
XT = F["x_dmax_end"] * MM
L = F["length"] * MM
RT = F["d_tail"] / 2 * MM
RHO = (R ** 2 + LN ** 2) / (2 * R)


def r_fus(x):
    """Govde dis yaricapi [mm], x [mm]."""
    x = np.asarray(x, dtype=float)
    r = np.where(x <= LN, np.sqrt(np.clip(RHO ** 2 - (LN - x) ** 2, 0, None)) + R - RHO, R)
    s = np.clip((x - XT) / (L - XT), 0, 1)
    r = np.where(x > XT, R - (R - RT) * s ** 2, r)
    return np.where(x > L, RT, r)


def build_fuselage():
    # burun: ucta sik (1-cos), ogive boyunca LN'ye kadar; sonra sabit kesit + kuyruk konisi
    xs = np.concatenate([LN * (1 - np.cos(np.linspace(0, math.pi / 2, 36))),
                         np.linspace(LN, L, 27)[1:]])
    xs = np.unique(np.round(xs, 3))
    pts = [(float(x), float(r_fus(x))) for x in xs]
    outer = (cq.Workplane("XY").moveTo(0, 0).spline(pts[1:], includeCurrent=True)
             .lineTo(L, 0).close().revolve(360, (0, 0, 0), (1, 0, 0)).val())
    x0 = 30.0
    xi = xs[xs > x0]
    ipts = [(float(x), float(r_fus(x) - T_SKIN)) for x in xi]
    ipts.append((L + 20, RT - T_SKIN))
    inner = (cq.Workplane("XY").moveTo(x0, 0).lineTo(x0, float(r_fus(x0) - T_SKIN))
             .spline(ipts, includeCurrent=True).lineTo(L + 20, 0).close()
             .revolve(360, (0, 0, 0), (1, 0, 0)).val())
    return outer, inner


# ====================================================================== hava alik
def rect_wire(x, cy, cz, w, h):
    return cq.Wire.makePolygon([V(x, cy + w / 2, cz + h / 2), V(x, cy - w / 2, cz + h / 2),
                                V(x, cy - w / 2, cz - h / 2), V(x, cy + w / 2, cz - h / 2)],
                               close=True)


def ell4_wire(x, cz, a, b):
    """Elips (y yari ekseni a, z yari ekseni b) - 4 ceyrek spline kenar (rect/daire ile uyumlu)."""
    edges = []
    for k in range(4):
        angs = np.radians(np.linspace(45 + 90 * k, 135 + 90 * k, 9))
        pts = [V(x, a * math.cos(t), cz + b * math.sin(t)) for t in angs]
        edges.append(cq.Edge.makeSpline(pts))
    return cq.Wire.assembleEdges(edges)


def circ4_wire(x, cz, r):
    return ell4_wire(x, cz, r, r)


def wing_box_top_z():
    """Kok kesitte kanat kutusu (kirisler arasi) ust yuzeyinin en yuksek z'si [mm]."""
    W = P.WING
    cr = P.wing_geom()["cr"] * MM
    xs = np.linspace(W["spar_xc"][0], W["spar_xc"][1], 30)
    zt = half_thickness(W["airfoil_root"], xs).max() * cr + 0.5 * T_TE
    # gelis acisi (ceyrek veter etrafinda burun yukari) on kiris ucunu kaldirir
    zt += (0.25 - W["spar_xc"][0]) * cr * math.sin(math.radians(W["incidence"]))
    return W["z_root"] * MM + zt


def build_inlet(x_box_rear):
    """Dorsal alik + S-kanal (iter3). Kesitler: dudakta dikdortgen, sonra elipsler, motor yuzunde
    daire. Alan dudaktan motor yuzune lineer artar (sabit esdeger konik acisi); merkez hatti
    smoothstep ile iner; kanat kutusu bolgesinde (x <= arka kiris) kanal ic tabani kutu ustunun
    >= 4 mm ustunde tutulur ve elips govde ic yuzeyine sigacak sekilde a/b secilir."""
    I = P.INLET
    w, h = I["width"] * MM, I["height"] * MM
    x_lip = I["x_lip"] * MM
    x_face = P.ENGINE["x_front"] * MM
    z_lip = (I["lip_z_center"] * MM if I.get("lip_z_center") is not None
             else R + I["diverter_h"] * MM + h / 2)
    r_face = 0.85 * P.ENGINE["diameter"] / 2 * MM      # kompresor girisi ~ %85 motor capi
    t = T_DUCT
    z_floor = wing_box_top_z() + 4.0 + t               # ic taban alt siniri (kutu bolgesi)
    r_in = R - T_SKIN - 0.5
    A0, A1 = w * h, math.pi * r_face ** 2
    xs = list(np.linspace(x_lip, x_face, 9))
    x_c = x_box_rear + 2.0
    if x_lip < x_c < x_face - 4:
        xs = sorted(set([round(v, 3) for v in xs] + [round(x_c, 3)]))
    secs, table = [], []
    for k, x in enumerate(xs):
        tt = (x - x_lip) / (x_face - x_lip)
        A = A0 + (A1 - A0) * tt
        if k == 0:
            a, b, zc, kind = w / 2, h / 2, z_lip, "r"
        elif k == len(xs) - 1:
            a, b, zc, kind = r_face, r_face, 0.0, "e"
        else:
            kind = "e"
            zc_des = z_lip * (1 - (3 * tt ** 2 - 2 * tt ** 3))
            a = w / 2 + (r_face - w / 2) * tt
            b = A / (math.pi * a)
            zc = zc_des
            if x <= x_c + 0.01 and zc - b < z_floor:
                # kisitli kesit: taban z_floor'da; govdeye en iyi sigan a'yi sec
                best = None
                for a_try in np.arange(0.85 * w / 2, 0.95 * r_in - t, 0.5):
                    b_try = A / (math.pi * a_try)
                    zc_try = z_floor + b_try
                    th = np.linspace(0, math.pi, 60)
                    rmax = np.max(np.hypot((a_try + t) * np.cos(th), zc_try + (b_try + t) * np.sin(th)))
                    if best is None or rmax < best[0]:
                        best = (rmax, a_try, b_try, zc_try)
                _, a, b, zc = best
        secs.append((x, kind, zc, a, b))
        A_true = (2 * a) * (2 * b) if kind == "r" else math.pi * a * b
        table.append(dict(x=round(x, 1), kind=kind, zc=round(zc, 1), a=round(a, 1), b=round(b, 1),
                          floor=round(zc - b, 1), ceil=round(zc + b, 1), area_cm2=round(A_true / 100, 1)))

    def wires(dt):
        out = []
        for x, kind, cz, a, b in secs:
            out.append(rect_wire(x, 0, cz, 2 * (a + dt), 2 * (b + dt)) if kind == "r"
                       else ell4_wire(x, cz, a + dt, b + dt))
        return out
    inner = cq.Solid.makeLoft(wires(0.0), True)
    outer = cq.Solid.makeLoft(wires(t), True)
    duct = outer.cut(inner)
    duct = duct.cut(box(x_lip - 20, x_lip + 1, -w / 2 + 0.2, w / 2 - 0.2,
                        z_lip - h / 2 + 0.2, z_lip + h / 2 - 0.2))
    duct = duct.cut(cyl_x(r_face - 0.2, x_face - 1, x_face + 10))
    zb = z_lip - h / 2 - t
    ramp = ramp_wall = None
    if zb > R:
        # diverter: lip altinda one sivri kama
        div = (cq.Workplane("XY").workplane(offset=R - 4)
               .polyline([(x_lip - 25, 0), (x_lip + 60, 22), (x_lip + 60, -22)]).close()
               .extrude(zb - (R - 4) + 0.5).val())
    else:
        # yari gomulu dudak: dudak altina govde yuzeyinden inen rampa (RAMP_DEG), yan duvarli
        div = None
        z_lo = z_lip - h / 2
        Lr = (R - z_lo) / math.tan(math.radians(RAMP_DEG))
        xr0 = x_lip - Lr
        rpts = [(xr0, float(r_fus(xr0)) + 40), (xr0, float(r_fus(xr0)) - 0.01), (x_lip, z_lo),
                (x_lip + 2, z_lo), (x_lip + 2, R + 40)]
        ramp = prism_xz(rpts, y0=-w / 2, h=w)
        rpts2 = [(xr0 - 2, float(r_fus(xr0)) + 40), (xr0 - 2, float(r_fus(xr0)) - T_SKIN - 0.5),
                 (x_lip, z_lo - T_SKIN), (x_lip + 4, z_lo - T_SKIN), (x_lip + 4, R + 40)]
        ramp_box = prism_xz(rpts2, y0=-w / 2 - T_SKIN, h=w + 2 * T_SKIN)
        ramp_wall = ramp_box.cut(ramp).cut(inner)
        RAMP_INFO.update(x0=round(xr0, 1), length=round(Lr, 1), depth=round(R - z_lo, 1), deg=RAMP_DEG)
    # duvar acilari (merkez duzlem, ruled loft -> kesitler arasi lineer) ve esdeger difuzor acisi
    seg = []
    for p_, q_ in zip(table[:-1], table[1:]):
        dx = q_["x"] - p_["x"]
        req0 = math.sqrt(p_["area_cm2"] * 100 / math.pi)
        req1 = math.sqrt(q_["area_cm2"] * 100 / math.pi)
        seg.append(dict(x0=p_["x"], x1=q_["x"],
                        floor_deg=round(math.degrees(math.atan2(q_["floor"] - p_["floor"], dx)), 1),
                        ceil_deg=round(math.degrees(math.atan2(q_["ceil"] - p_["ceil"], dx)), 1),
                        side_deg=round(math.degrees(math.atan2(q_["a"] - p_["a"], dx)), 1),
                        diffuser_half_deg=round(math.degrees(math.atan2(req1 - req0, dx)), 2)))
    info = dict(capture_area_cm2=round(A0 / 100, 1), face_area_cm2=round(A1 / 100, 1),
                area_ratio=round(A1 / A0, 3), vertical_offset_mm=round(z_lip, 1),
                length_mm=round(x_face - x_lip, 1), offset_to_length=round(z_lip / (x_face - x_lip), 3),
                z_floor_min_in_box_mm=round(z_floor, 1),
                max_wall_angle_deg=max(max(abs(g["floor_deg"]), abs(g["ceil_deg"]), abs(g["side_deg"]))
                                       for g in seg),
                max_diffuser_half_angle_deg=max(g["diffuser_half_deg"] for g in seg),
                mean_diffuser_half_angle_deg=round(math.degrees(math.atan2(
                    math.sqrt(A1 / math.pi) - math.sqrt(A0 / math.pi), x_face - x_lip)), 2),
                sections=table, segments=seg)
    info["lip_buried_mm"] = round(max(0.0, R - (z_lip - h / 2)), 1)
    info["ramp"] = dict(RAMP_INFO)
    return duct, inner, outer, div, info, ramp, ramp_wall


# ====================================================================== kaldirma yuzeyleri
def lifting_surface(d, b_half, cr, sweep, dihedral, twist_tip, inc, xle0, z0, af_root, af_tip,
                    n=5, toff=0.0):
    xle, c = plan(xle0, cr, sweep, b_half, d["taper"])
    wires = []
    for k in range(n):
        s = b_half * k / (n - 1)
        name = af_root if k < n - 1 else af_tip
        # kalinlik koke/uca dogru lineer: ara kesitlerde kok profilini kullan, uc kesit uc profil
        if af_root != af_tip and 0 < k < n - 1:
            tr, tt = int(af_root[-3:]), int(af_tip[-3:])
            name = af_root[:-3] + "%03d" % round(tr + (tt - tr) * k / (n - 1))
        tw = inc + twist_tip * s / b_half
        wires.append(sect_wire(name, c(s), xle(s), s, z0 + s * math.tan(math.radians(dihedral)), tw,
                               toff=toff))
    right = cq.Solid.makeLoft(wires, True)
    return right, xle, c


def cs_prism(xle, c, cf, s0, s1, side=1, over=6.0, fwd=0.0):
    """Kontrol yuzeyi kesme prizmasi (plan gorunuste mentese hatti -> TE). fwd: hatti one kaydir [mm]."""
    h0 = xle(s0) + (1 - cf) * c(s0) - fwd
    h1 = xle(s1) + (1 - cf) * c(s1) - fwd
    t0 = xle(s0) + c(s0) + over
    t1 = xle(s1) + c(s1) + over
    return prism([(h0, side * s0), (t0, side * s0), (t1, side * s1), (h1, side * s1)])


def build_wing(fus_outer):
    W = P.WING
    g = P.wing_geom()
    bh, cr = g["b"] / 2 * MM, g["cr"] * MM
    right, xle, c = lifting_surface(W, bh, cr, W["sweep_le"], W["dihedral"], W["twist_tip"],
                                    W["incidence"], W["x_root_le"] * MM, W["z_root"] * MM,
                                    W["airfoil_root"], W["airfoil_tip"])
    left = right.mirror("XZ")
    full = right.fuse(left).clean()
    # kanat kutusu (on-arka kiris arasi). Govde icinde (|y|<R) kirisler govde eksenine dik,
    # kok kiris konumlarinda duz merkez gecis kutusu; disarida ok acili.
    f0, f1 = W["spar_xc"]
    xf, xr = (lambda s: xle(s) + f0 * c(s)), (lambda s: xle(s) + f1 * c(s))
    box_pl = [(xf(0), 0), (xf(0), R), (xf(R), R), (xf(bh), bh), (xr(bh), bh), (xr(R), R),
              (xr(0), R), (xr(0), 0)]
    wbox_r = right.intersect(prism(box_pl))
    wbox = wbox_r.fuse(wbox_r.mirror("XZ")).clean()
    # entegre kanat koku yakit tanklari: IC bosluk = kabuk (sandvic 2.6 mm) ici, kiris web'leri
    # (1.5 mm) arasi, uc kaburgalar (3 mm) arasi
    e0, e1 = P.FUEL["tanks"]["wing_eta"]
    right_in = lifting_surface(W, bh, cr, W["sweep_le"], W["dihedral"], W["twist_tip"], W["incidence"],
                               W["x_root_le"] * MM, W["z_root"] * MM, W["airfoil_root"], W["airfoil_tip"],
                               toff=T_TANK_SKIN)[0]
    tw_ = T_TANK_WEB
    box_in = [(xf(0) + tw_, 0), (xf(0) + tw_, R), (xf(R) + tw_, R), (xf(bh) + tw_, bh), (xr(bh) - tw_, bh),
              (xr(R) - tw_, R), (xr(0) - tw_, R), (xr(0) - tw_, 0)]
    cav_r = right_in.intersect(prism(box_in))

    def wing_cavity(eta0, eta1, y_start=None):
        y0 = (eta0 * bh if y_start is None else y_start) + T_TANK_RIB
        y1 = eta1 * bh - T_TANK_RIB
        return cav_r.intersect(box(-1e3, 4e3, y0, y1, -400, 400))
    wtanks = {}
    cav = wing_cavity(e0, e1)
    wtanks["tank_wing_R"] = cav
    wtanks["tank_wing_L"] = cav.mirror("XZ")
    if P.FUEL["tanks"].get("center_L"):
        # gove icinden gecen kanat kutusu orta tanki: |y| <= eta0*bh - kaburga (tek hacim)
        yc = e0 * bh - T_TANK_RIB
        cc = cav_r.intersect(box(-1e3, 4e3, 0, yc, -400, 400))
        wtanks["tank_center"] = cc.fuse(cc.mirror("XZ")).clean()
    wing_tank_cmp = {}
    for lab, args in ((f"eta {e0:.2f}-{e1:.2f} (params)", (e0, e1, None)),
                      ("eta 0.06-0.40", (0.06, 0.40, None)),
                      ("govde yani (y=R)-eta 0.40 (yapi ajani tanimi)", (0.0, 0.40, R)),
                      ("govde yani (y=R)-eta 0.55", (0.0, 0.55, R))):
        wing_tank_cmp[lab] = round(vol(wing_cavity(*args)) / 1e6, 3)
    # karin kaplamasi: alcak kanat kokunun govde altindan tasan kismini duz tabanla kapatir
    x_le0, x_te0 = xle(0), xle(0) + c(0)
    zb_f = min(W["z_root"] * MM - 0.5 * W["tc_root"] * c(0), -R) - 1.0
    fpts = [(x_le0 - 60, -R + 12), (x_le0 + 25, zb_f), (x_te0 - 10, zb_f), (x_te0 + 110, -R + 12),
            (x_te0 + 110, -R + 30), (x_le0 - 60, -R + 30)]
    fairing = prism_xz(fpts, y0=-0.75 * R, h=1.5 * R).cut(fus_outer).cut(full)
    exposed = full.cut(fus_outer)
    parts = {}
    # tek parca kanat: govde icinde kanat yalniz x <= arka kiris (attach), daha geride yalniz
    # kesintisiz alt kabuk (WING_LOWER_SKIN kalinliginda) motorun altindan gecer
    x_cut = P.WING.get("attach", {}).get("frames_x", (None, xr(0) / MM))[1] * MM
    inside = full.intersect(fus_outer)
    fwd_in = inside.intersect(box(-1e3, x_cut, -R - 5, R + 5, -400, 400)).cut(wbox)
    aft_in = inside.intersect(box(x_cut, 4e3, -R - 5, R + 5, -400, 400))
    skin_aft = aft_in.cut(aft_in.translate(V(0, 0, WING_LOWER_SKIN)))
    parts["wing_center"] = fwd_in.fuse(skin_aft).clean()
    WING_INFO["wing_cut_x_mm"] = round(x_cut, 1)
    A, Fl = W["aileron"], W["flap"]
    cuts = []
    for side, tag in ((1, "R"), (-1, "L")):
        pa = cs_prism(xle, c, A["cf"], A["eta0"] * bh, A["eta1"] * bh, side)
        pf = cs_prism(xle, c, Fl["cf"], Fl["eta0"] * bh, Fl["eta1"] * bh, side)
        parts["aileron_" + tag] = exposed.intersect(pa)
        parts["flap_" + tag] = exposed.intersect(pf)
        # tek yarikli flap: kanat panelinden flap onunde FLAP_SLOT mm'lik yarik/cove bosaltilir
        pf_cut = cs_prism(xle, c, Fl["cf"], Fl["eta0"] * bh - 1.0, Fl["eta1"] * bh + 1.0, side,
                          fwd=FLAP_SLOT) if Fl.get("type") == "slotted" else pf
        cuts += [pa, pf_cut]
    panel = exposed
    for p_ in cuts:
        panel = panel.cut(p_)
    parts["wing_panels"] = panel
    parts["wing_box"] = wbox
    parts["belly_fairing"] = fairing
    parts.update(wtanks)
    # flap dis mentese hatti (yarikli flap: flap burnunun %10 cf gerisinde, alt yuzeyin 8 mm altinda)
    hinge = []
    for eta in (Fl["eta0"], Fl["eta1"]):
        s_ = eta * bh
        xh = xle(s_) + (1 - 0.9 * Fl["cf"]) * c(s_)
        xc_ = 1 - 0.9 * Fl["cf"]
        zh = (W["z_root"] * MM + s_ * math.tan(math.radians(W["dihedral"]))
              - float(half_thickness(W["airfoil_root"], np.array([xc_]))[0]) * c(s_) - 8.0)
        hinge.append((round(xh, 1), round(s_, 1), round(zh, 1)))
    WING_INFO["fairing_depth_below_fuselage_mm"] = round(-R - zb_f, 1)
    WING_INFO.update(tank_cmp_L=wing_tank_cmp, flap_hinge_mm=hinge, flap_slot_mm=FLAP_SLOT,
                     fairing_bottom_z_mm=round(zb_f, 1), fairing_x_mm=(round(x_le0 - 60, 1), round(x_te0 + 110, 1)))
    return parts, full, exposed, xle, c, bh


def build_htail(fus_outer):
    H = P.HTAIL
    g = P.surface_geom(H)
    bh, cr = g["b"] / 2 * MM, g["cr"] * MM
    right, xle, c = lifting_surface(H, bh, cr, H["sweep_le"], 0.0, 0.0, 0.0,
                                    H["x_root_le"] * MM, H["z_root"] * MM, H["airfoil"], H["airfoil"], n=2)
    full = right.fuse(right.mirror("XZ")).clean()
    exposed = full.cut(fus_outer)
    E = H["elevator"]
    s0 = float(r_fus(xle(0) + c(0))) + 5.0
    parts = {}
    panel = exposed
    for side, tag in ((1, "R"), (-1, "L")):
        pe = cs_prism(xle, c, E["cf"], s0, 0.97 * bh, side)
        parts["elevator_" + tag] = exposed.intersect(pe)
        panel = panel.cut(pe)
    parts["htail"] = panel
    if H.get("split"):
        # iter2: iki yari. Govde ici: egzoz borusu ustunden gecen yarim halka cerceve +
        # her yariya giren y-eksenli saplama (stub) rod'lari.
        rp = F["exhaust_pipe_d"] / 2 * MM
        s_side = float(r_fus(xle(0) + 0.3 * c(0)))
        xc = xle(s_side) + 0.30 * c(s_side)
        r_in = float(np.min(r_fus(np.linspace(xc - 15, xc + 15, 7)))) - T_SKIN
        r_o, r_i, wx = r_in - 2.0, rp + 3.5, 26.0
        ring = cyl_x(r_o, xc - wx / 2, xc + wx / 2).cut(cyl_x(r_i, xc - wx, xc + wx))
        ring = ring.cut(box(xc - wx, xc + wx, -r_o - 5, r_o + 5, -r_o - 5, -4.0))
        rod_r = min(3.0, 0.35 * H["tc"] * c(s_side))
        y_out = s_side + 0.45 * (bh - s_side)
        stubs = [cq.Solid.makeCylinder(rod_r, y_out - r_i - 1, V(xc, sd * (r_i + 1), H["z_root"] * MM),
                                       V(0, sd, 0)) for sd in (1, -1)]
        parts["ht_carry_yoke"] = ring.fuse(stubs[0]).fuse(stubs[1]).clean()
        full = exposed            # ucusta govde icinde yatay kuyruk yok
    return parts, full, xle, c, bh


def build_vtail(fus_outer):
    Vt = P.VTAIL
    g = P.vtail_geom()
    h, cr = g["h"] * MM, g["cr"] * MM
    z0 = Vt["z_root"] * MM
    xle, c = plan(Vt["x_root_le"] * MM, cr, Vt["sweep_le"], h, Vt["taper"])
    wires = [sect_wire(Vt["airfoil"], c(s), xle(s), z0 + s, 0.0, 0.0, plane="xy") for s in (0, h)]
    full = cq.Solid.makeLoft(wires, True)
    exposed = full.cut(fus_outer)
    Rr = Vt["rudder"]
    zs0 = float(r_fus(xle(0) + c(0))) + 5.0 - z0
    zs1 = 0.95 * h
    hh0, hh1 = xle(zs0) + (1 - Rr["cf"]) * c(zs0), xle(zs1) + (1 - Rr["cf"]) * c(zs1)
    pr = prism_xz([(hh0, z0 + zs0), (xle(zs0) + c(zs0) + 6, z0 + zs0),
                   (xle(zs1) + c(zs1) + 6, z0 + zs1), (hh1, z0 + zs1)])
    return {"vtail": exposed.cut(pr), "rudder": exposed.intersect(pr)}, full, xle, c, h, z0


# ====================================================================== ic sistemler
def tank_inner_volume(shp, t=1.5):
    """Entegre tank ic hacmi ~ dis hacim - yuzey alani * duvar kalinligi [mm3]."""
    return max(vol(shp) - shp.Area() * t, 0.0)


def build_internal(fus_outer, duct_outer, wing_box, x_front_spar, wing_tank_L, fairing, wing_full=None,
                   ramp_cut=None):
    E = P.ENGINE
    re = E["diameter"] / 2 * MM
    x0 = E["x_front"] * MM
    x1 = x0 + E["length"] * MM
    engine = cyl_x(re, x0, x1).fuse(
        cq.Solid.makeCone(re * 0.75, 45.0, 30, V(x1, 0, 0), V(1, 0, 0))).clean()
    rp = F["exhaust_pipe_d"] / 2 * MM
    x_p0 = x1 + 15
    pipe = cyl_x(rp, x_p0, L + 5).cut(cyl_x(rp - 1.0, x_p0 - 1, L + 10))

    # govde ana tanki: arka ucu on kirisin 3 mm onunde; on ucu toplam hedef hacme gore cozulur
    target_L = (P.FUEL["tanks"]["fuselage_L"] + 2 * P.FUEL["tanks"]["wing_integral_L_each"]
                + P.FUEL["tanks"].get("center_L", 0.0))
    # opsiyonel govde alti (belly) tanki: merkez gecis kutusunun altinda, kirisler arasi
    belly, belly_note = None, "params'ta kapali"
    if P.FUEL["tanks"].get("belly_tank"):
        zbot = wing_box.intersect(box(x_front_spar, x_front_spar + 400, -R, R, -300, 300)).BoundingBox().zmin
        depth = (zbot - 3) - (-R + T_SKIN + 4)
        if depth < 8.0:
            belly_note = ("yer yok: kanat kutusu alti z=%.1f mm, govde ic tabani z=%.1f mm "
                          "(alcak kanat) -> karin tanki modellenmedi" % (zbot, -R + T_SKIN))
        else:
            x_rs = x_front_spar + (P.WING["spar_xc"][1] - P.WING["spar_xc"][0]) * P.wing_geom()["cr"] * MM
            belly = box(x_front_spar + 3, x_rs - 3, -R, R, -R, zbot - 3).intersect(
                cyl_x(R - T_SKIN - 4, x_front_spar, x_rs))
            wing_tank_L += tank_inner_volume(belly, 1.0) / 1e6
            belly_note = "modellendi"
    need_fus_L = max(target_L - wing_tank_L, P.FUEL["tanks"]["fuselage_L"])
    tx1 = x_front_spar - 3.0

    def fus_tank(tx0):
        r1 = float(r_fus(tx0)) - T_SKIN - 6.0
        t = (cq.Workplane("YZ").workplane(offset=tx0).circle(r1).extrude(tx1 - tx0)
             .edges().fillet(18).val())
        t = t.cut(duct_outer).cut(wing_box)
        if wing_full is not None:
            t = t.cut(wing_full)
        if ramp_cut is not None:
            t = t.cut(ramp_cut)
        # cerceve halkalari icin radyal pay zaten var (tank r = r_ic - 6 mm)
        return t

    lo, hi = 300.0, tx1 - 60.0
    for _ in range(14):
        mid = 0.5 * (lo + hi)
        if tank_inner_volume(fus_tank(mid), 1.0) / 1e6 > need_fus_L:
            lo = mid
        else:
            hi = mid
    tank_f = fus_tank(lo)

    # govde alti kizak
    G_ = P.GEAR
    sx0, sx1 = G_["skid_x0"] * MM, G_["skid_x1"] * MM
    sh, sw = G_["skid_h"] * MM, G_["skid_w"] * MM
    skid = box(sx0, sx1, -sw / 2, sw / 2, -R - sh, -R + 30).cut(fus_outer).cut(fairing)
    # kuyruk tamponu
    tb = G_.get("tail_bumper")
    bumper = None
    if tb:
        bx, bl, bd = tb["x"] * MM, tb["length"] * MM, tb["depth"] * MM
        zbb = -float(r_fus(bx)) - bd
        bumper = box(bx - bl / 2, bx + bl / 2, -12, 12, zbb, -float(r_fus(bx)) + 10).cut(fus_outer)
    # cerceveler: kanat baglanti cerceveleri tam halka, kizak cerceveleri alt yay (+-55 deg)
    att = [x * MM for x in P.WING.get("attach", {}).get("frames_x", ())]
    frames = None
    for fx in sorted(set([round(x * MM, 1) for x in G_.get("skid_frames", ())] + [round(a, 1) for a in att])):
        ro = float(np.min(r_fus(np.linspace(fx - FRAME_T, fx + FRAME_T, 9)))) - T_SKIN - 0.4
        ring = cyl_x(ro, fx - FRAME_T / 2, fx + FRAME_T / 2).cut(cyl_x(ro - FRAME_D, fx - 5, fx + 5))
        if not any(abs(fx - a) < 1 for a in att):
            ring = ring.intersect(box(fx - 5, fx + 5, -ro, ro, -ro - 1, -ro * math.cos(math.radians(55))))
        frames = ring if frames is None else frames.fuse(ring)
    if frames is not None:
        frames = frames.cut(duct_outer).cut(wing_box)
        if wing_full is not None:
            frames = frames.cut(wing_full)
    # dolly (yer ekipmani, ucusta yok)
    zg = -R - sh - 110.0
    tr, wb = G_["dolly_track"] * MM, G_["dolly_wheelbase"] * MM
    xc = P.mass_summary(1.0)["x_cg"] * MM
    wd = 100.0
    dol = []
    for dxw in (-wb / 2, wb / 2):
        for sd in (1, -1):
            dol.append(cq.Solid.makeCylinder(wd / 2, 30, V(xc + dxw, sd * tr / 2 - 15, zg + wd / 2), V(0, 1, 0)))
        dol.append(cq.Solid.makeCylinder(8, tr, V(xc + dxw, -tr / 2, zg + wd / 2), V(0, 1, 0)))
    for sd in (1, -1):
        dol.append(cyl_x(10, xc - wb / 2 - 30, xc + wb / 2 + 30, y=sd * 0.3 * tr, z=zg + wd / 2 + 18))
    for cx in (sx0 + 60, sx1 - 60):
        dol.append(box(cx - 25, cx + 25, -0.3 * tr - 10, 0.3 * tr + 10, zg + wd / 2 + 8, -R - sh))
    dolly = dol[0]
    for d in dol[1:]:
        dolly = dolly.fuse(d)
    extra = {}
    if belly is not None:
        extra["tank_belly"] = belly
    if bumper is not None:
        extra["tail_bumper"] = bumper
    if frames is not None:
        extra["frames"] = frames
    return dict(engine=engine, exhaust_pipe=pipe, tank_fuselage=tank_f, skid=skid, **extra),         dict(dolly=dolly), dict(zg=zg, r_engine=re, x_eng=(x0, x1), r_pipe=rp, x_pipe0=x_p0,
                                tank_fus_x=(lo, tx1), need_fus_L=need_fus_L, target_L=target_L,
                                belly_note=belly_note)


# ====================================================================== cizimler
def draw_3view(ctx):
    import ezdxf
    from ezdxf import units
    doc = ezdxf.new("R2010", setup=True)
    doc.units = units.MM
    for nm, col, lt in (("OUTLINE", 7, "CONTINUOUS"), ("HIDDEN", 8, "DASHED"),
                        ("CENTER", 1, "CENTER"), ("DIM", 5, "CONTINUOUS"),
                        ("CS", 3, "CONTINUOUS"), ("MARK", 1, "CONTINUOUS"), ("TEXT", 7, "CONTINUOUS")):
        doc.layers.add(nm, color=col, linetype=lt)
    msp = doc.modelspace()
    ov = {"dimlfac": 1.0, "dimtxt": 14, "dimasz": 9, "dimexe": 4, "dimexo": 3, "dimdec": 0, "dimgap": 3}

    def pl(pts, layer="OUTLINE", closed=False, dx=0, dy=0):
        msp.add_lwpolyline([(x + dx, y + dy) for x, y in pts], close=closed, dxfattribs={"layer": layer})

    def ln(p, q, layer="OUTLINE", dx=0, dy=0):
        msp.add_line((p[0] + dx, p[1] + dy), (q[0] + dx, q[1] + dy), dxfattribs={"layer": layer})

    def txt(s, p, h=14, dx=0, dy=0, layer="TEXT"):
        msp.add_text(s, height=h, dxfattribs={"layer": layer}).set_placement((p[0] + dx, p[1] + dy))

    def dim(base, p1, p2, angle=0, dx=0, dy=0, text="<>"):
        d = msp.add_linear_dim(base=(base[0] + dx, base[1] + dy), p1=(p1[0] + dx, p1[1] + dy),
                               p2=(p2[0] + dx, p2[1] + dy), angle=angle, text=text,
                               dimstyle="EZDXF", override=ov, dxfattribs={"layer": "DIM"})
        d.render()

    def adim(base, center, p1, p2, dx=0, dy=0):
        try:
            d = msp.add_angular_dim_3p(base=(base[0] + dx, base[1] + dy),
                                       center=(center[0] + dx, center[1] + dy),
                                       p1=(p2[0] + dx, p2[1] + dy), p2=(p1[0] + dx, p1[1] + dy),
                                       dimstyle="EZDXF", override=dict(ov, dimdec=1),
                                       dxfattribs={"layer": "DIM"})
            d.render()
        except Exception as e:  # pragma: no cover
            txt("aci: %s" % e, base, dx=dx, dy=dy)

    def cross(p, s=14, dx=0, dy=0):
        ln((p[0] - s, p[1]), (p[0] + s, p[1]), "MARK", dx, dy)
        ln((p[0], p[1] - s), (p[0], p[1] + s), "MARK", dx, dy)
        msp.add_circle((p[0] + dx, p[1] + dy), s * 0.6, dxfattribs={"layer": "MARK"})

    W, H, Vt = P.WING, P.HTAIL, P.VTAIL
    g, gh, gv = P.wing_geom(), P.surface_geom(H), P.vtail_geom()
    xle, c, bh = ctx["w_xle"], ctx["w_c"], ctx["w_bh"]
    hxle, hc, hbh = ctx["h_xle"], ctx["h_c"], ctx["h_bh"]
    vxle, vc, vh, vz0 = ctx["v_xle"], ctx["v_c"], ctx["v_h"], ctx["v_z0"]
    xs = np.linspace(0, L, 120)
    rs = r_fus(xs)

    # ---------------- UST GORUNUS (x saga, y yukari)
    pl(list(zip(xs, rs)) + list(zip(xs[::-1], -rs[::-1])), closed=True)
    ln((-40, 0), (L + 60, 0), "CENTER")
    for sd in (1, -1):
        s0 = R
        pl([(xle(s0), sd * s0), (xle(bh), sd * bh), (xle(bh) + c(bh), sd * bh),
            (xle(s0) + c(s0), sd * s0)], closed=False)
        ln((xle(0), 0), (xle(s0), sd * s0), "HIDDEN")
        ln((xle(0) + c(0), 0), (xle(s0) + c(s0), sd * s0), "HIDDEN")
        for cs in (W["aileron"], W["flap"]):
            a0, a1 = cs["eta0"] * bh, cs["eta1"] * bh
            hp = lambda s: xle(s) + (1 - cs["cf"]) * c(s)
            pl([(xle(a0) + c(a0), sd * a0), (hp(a0), sd * a0), (hp(a1), sd * a1),
                (xle(a1) + c(a1), sd * a1)], "CS")
        f0, f1 = W["spar_xc"]
        for f in (f0, f1):
            ln((xle(0) + f * c(0), 0), (xle(bh) + f * c(bh), sd * bh), "HIDDEN")
        hh = WING_INFO.get("flap_hinge_mm")
        if hh:
            ln((hh[0][0], sd * hh[0][1]), (hh[1][0], sd * hh[1][1]), "HIDDEN")
        hs0 = float(r_fus(hxle(0)))
        pl([(hxle(hs0), sd * hs0), (hxle(hbh), sd * hbh), (hxle(hbh) + hc(hbh), sd * hbh),
            (hxle(hs0) + hc(hs0), sd * hs0)])
        e0 = float(r_fus(hxle(0) + hc(0))) + 5
        hp = lambda s: hxle(s) + (1 - H["elevator"]["cf"]) * hc(s)
        pl([(hxle(e0) + hc(e0), sd * e0), (hp(e0), sd * e0), (hp(0.97 * hbh), sd * 0.97 * hbh),
            (hxle(0.97 * hbh) + hc(0.97 * hbh), sd * 0.97 * hbh)], "CS")
    # MAC, AC, CG
    ym = g["y_mac"] * MM
    ln((g["x_mac_le"] * MM, ym), (g["x_mac_le"] * MM + g["mac"] * MM, ym), "MARK")
    txt("MAC %.0f" % (g["mac"] * MM), (g["x_mac_le"] * MM + 20, ym + 8), 11)
    cross((g["x_ac"] * MM, ym), 8)
    txt("AC (%%25 MAC)", (g["x_ac"] * MM + 12, ym - 22), 10)
    cgf, cge = P.mass_summary(1.0), P.mass_summary(0.0)
    for cgd, lab, off in ((cgf, "CG dolu", 26), (cge, "CG bos", -40)):
        cross((cgd["x_cg"] * MM, 0), 10)
        pct = 100 * (cgd["x_cg"] - g["x_mac_le"]) / g["mac"]
        txt("%s x=%.0f (%%%.1f MAC)" % (lab, cgd["x_cg"] * MM, pct), (cgd["x_cg"] * MM - 120, off), 10)
    # olculer
    dim((0, -bh - 90), (0, 0), (L, 0))
    dim((L + 140, 0), (xle(bh) + c(bh), bh), (xle(bh) + c(bh), -bh), angle=90)
    dim((0, -bh - 40), (xle(0), 0), (xle(0) + c(0), 0))
    txt("kok veteri (y=0)", (xle(0), -bh - 30), 10)
    dim((0, bh + 40), (xle(bh), bh), (xle(bh) + c(bh), bh))
    dim((0, -bh - 140), (0, 0), (xle(0), 0))
    dim((hxle(hbh) - 200, 0), (hxle(hbh) + hc(hbh), hbh), (hxle(hbh) + hc(hbh), -hbh), angle=90)
    adim((xle(R) + 70, R + 150), (xle(R), R), (xle(R), R + 300),
         (xle(R) + 300 * math.sin(math.radians(W["sweep_le"])), R + 300 * math.cos(math.radians(W["sweep_le"]))))
    adim((hxle(hs0) + 50, hs0 + 110), (hxle(hs0), hs0), (hxle(hs0), hs0 + 200),
         (hxle(hs0) + 200 * math.sin(math.radians(H["sweep_le"])), hs0 + 200 * math.cos(math.radians(H["sweep_le"]))))
    txt("UST GORUNUS", (0, bh + 100), 22)

    # ---------------- YAN GORUNUS (x saga, z yukari), dy kaydir
    DY = -bh - 600
    pl(list(zip(xs, rs)) + list(zip(xs[::-1], -rs[::-1])), closed=True, dy=DY)
    ln((-40, 0), (L + 60, 0), "CENTER", dy=DY)
    I = P.INLET
    zl = R + I["diverter_h"] * MM
    xl = I["x_lip"] * MM
    zt = zl + I["height"] * MM + T_DUCT
    pl([(xl, zl), (xl, zt), (xl + 130, zt - 6), (P.ENGINE["x_front"] * MM - 10, R)], dy=DY)
    zv0 = float(r_fus(vxle(0))) - vz0
    pts = [(vxle(zv0), vz0 + zv0), (vxle(vh), vz0 + vh), (vxle(vh) + vc(vh), vz0 + vh),
           (vxle(zv0) + vc(zv0), vz0 + zv0)]
    pl(pts, dy=DY)
    r0 = float(r_fus(vxle(0) + vc(0))) + 5 - vz0
    hp = lambda s: vxle(s) + (1 - Vt["rudder"]["cf"]) * vc(s)
    pl([(vxle(r0) + vc(r0), vz0 + r0), (hp(r0), vz0 + r0), (hp(0.95 * vh), vz0 + 0.95 * vh),
        (vxle(0.95 * vh) + vc(0.95 * vh), vz0 + 0.95 * vh)], "CS", dy=DY)
    # kanat uc profili + kok (gizli)
    for s, lay in ((bh, "OUTLINE"), (0, "HIDDEN")):
        up, lo = airfoil(W["airfoil_tip"] if s else W["airfoil_root"])
        zz = W["z_root"] * MM + s * math.tan(math.radians(W["dihedral"]))
        pts = [(xle(s) + X * c(s), zz + Z * c(s)) for X, Z in np.vstack([up, lo])]
        pl(pts, lay, closed=True, dy=DY)
    # motor, egzoz (gizli)
    e = ctx["int"]
    x0, x1 = e["x_eng"]
    re = e["r_engine"]
    pl([(x0, re), (x1, re), (x1, -re), (x0, -re)], "HIDDEN", closed=True, dy=DY)
    pl([(e["x_pipe0"], e["r_pipe"]), (L, e["r_pipe"])], "HIDDEN", dy=DY)
    pl([(e["x_pipe0"], -e["r_pipe"]), (L, -e["r_pipe"])], "HIDDEN", dy=DY)
    # kizak + dolly (yer ekipmani, kesikli) + zemin
    zg = e["zg"]
    G_ = P.GEAR
    sx0, sx1, sh = G_["skid_x0"] * MM, G_["skid_x1"] * MM, G_["skid_h"] * MM
    xsk = np.linspace(sx0, sx1, 40)
    pl([(x, -float(r_fus(x))) for x in xsk] + [(sx1, -R - sh), (sx0, -R - sh)], closed=True, dy=DY)
    xc, wb = e["dolly_xc"], G_["dolly_wheelbase"] * MM
    for dxw in (-wb / 2, wb / 2):
        msp.add_circle((xc + dxw, zg + 50 + DY), 50, dxfattribs={"layer": "HIDDEN"})
    pl([(xc - wb / 2 - 30, zg + 68), (xc + wb / 2 + 30, zg + 68)], "HIDDEN", dy=DY)
    for cx in (sx0 + 60, sx1 - 60):
        pl([(cx - 25, zg + 58), (cx - 25, -R - sh), (cx + 25, -R - sh), (cx + 25, zg + 58)], "HIDDEN", dy=DY)
    txt("dolly (yer ekipmani, kalkista birakilir)", (xc - 200, zg - 30), 10, dy=DY)
    fx0, fx1 = WING_INFO["fairing_x_mm"]
    fzb = WING_INFO["fairing_bottom_z_mm"]
    pl([(fx0, -float(r_fus(fx0)) + 0.5), (fx0 + 85, fzb), (fx1 - 120, fzb), (fx1, -float(r_fus(fx1)) + 0.5)],
       dy=DY)
    gr = ctx.get("ground")
    if gr:
        p0, p1 = gr["strike_pivot_mm"], gr["tail_strike_contact_mm"]
        ln(p0, p1, "MARK", dy=DY)
        if "tail_bumper" in ctx["parts"]:
            bbt = ctx["parts"]["tail_bumper"].BoundingBox()
            pl([(bbt.xmin, -float(r_fus(bbt.xmin))), (bbt.xmin, bbt.zmin), (bbt.xmax, bbt.zmin),
                (bbt.xmax, -float(r_fus(bbt.xmax)))], dy=DY)
            txt("kuyruk tamponu", (bbt.xmin - 20, bbt.zmin - 25), 10, dy=DY)
        txt("kuyruk carpma %.1f deg (hedef 9)" % gr["tail_strike_deg"], (p0[0] + 40, p0[1] - 40), 10, dy=DY)
    ln((0, zg), (L, zg), "CENTER", dy=DY)
    txt("zemin", (20, zg + 6), 10, dy=DY)
    dim((L + 80, 0), (L - 30, vz0 + vh), (L - 30, zg), angle=90, dy=DY)
    dim((-60, 0), (LN, R), (LN, -R), angle=90, dy=DY)
    dim((0, vz0 + vh + 60), (0, 0), (xl, zl), dy=DY)
    txt("alik dudagi", (xl - 40, vz0 + vh + 75), 10, dy=DY)
    dim((0, zg - 70), (sx0, -R - sh), (sx1, -R - sh), dy=DY)
    txt("kizak", (sx0, zg - 55), 10, dy=DY)
    adim((vxle(zv0) + 60, vz0 + zv0 + 130), (vxle(zv0), vz0 + zv0), (vxle(zv0), vz0 + zv0 + 200),
         (vxle(zv0) + 200 * math.sin(math.radians(Vt["sweep_le"])),
          vz0 + zv0 + 200 * math.cos(math.radians(Vt["sweep_le"]))), dy=DY)
    for cgd in (cgf, cge):
        cross((cgd["x_cg"] * MM, cgd["z_cg"] * MM), 8, dy=DY)
    txt("YAN GORUNUS", (0, vz0 + vh + 130), 22, dy=DY)

    # ---------------- ON GORUNUS (y saga, z yukari)
    DX, DY2 = L + 900, 0
    msp.add_circle((DX, DY2), R, dxfattribs={"layer": "OUTLINE"})
    tr, tt = W["tc_root"] * c(R), W["tc_tip"] * c(bh)
    zr = W["z_root"] * MM
    an = math.tan(math.radians(W["dihedral"]))
    for sd in (1, -1):
        pl([(sd * R, zr + R * an + tr / 2), (sd * bh, zr + bh * an + tt / 2),
            (sd * bh, zr + bh * an - tt / 2), (sd * R, zr + R * an - tr / 2)], dx=DX, dy=DY2)
        hs = float(r_fus(hxle(0)))
        th = H["tc"] * hc(hs)
        pl([(sd * hs, th / 2), (sd * hbh, H["tc"] * hc(hbh) / 2), (sd * hbh, -H["tc"] * hc(hbh) / 2),
            (sd * hs, -th / 2)], dx=DX, dy=DY2)
        e_ = G_["dolly_track"] / 2 * MM * sd
        msp.add_lwpolyline([(e_ - 15 + DX, zg + DY2), (e_ + 15 + DX, zg + DY2),
                            (e_ + 15 + DX, zg + 100 + DY2), (e_ - 15 + DX, zg + 100 + DY2)],
                           close=True, dxfattribs={"layer": "HIDDEN"})
    tv0, tv1 = Vt["tc"] * vc(zv0), Vt["tc"] * vc(vh)
    pl([(-tv0 / 2, vz0 + zv0), (-tv1 / 2, vz0 + vh), (tv1 / 2, vz0 + vh), (tv0 / 2, vz0 + zv0)],
       closed=True, dx=DX, dy=DY2)
    w_ = I["width"] * MM / 2 + T_DUCT
    pl([(-w_, zl), (-w_, zt), (w_, zt), (w_, zl)], closed=True, dx=DX, dy=DY2)
    msp.add_circle((DX, DY2), e["r_pipe"], dxfattribs={"layer": "HIDDEN"})
    ln((-bh - 40, 0), (bh + 40, 0), "CENTER", dx=DX, dy=DY2)
    ln((-bh, zg), (bh, zg), "CENTER", dx=DX, dy=DY2)
    dim((0, zg - 80), (-bh, zr + bh * an), (bh, zr + bh * an), dx=DX, dy=DY2)
    pl([(-G_["skid_w"] * MM / 2, -R + 2), (-G_["skid_w"] * MM / 2, -R - G_["skid_h"] * MM),
        (G_["skid_w"] * MM / 2, -R - G_["skid_h"] * MM), (G_["skid_w"] * MM / 2, -R + 2)], dx=DX, dy=DY2)
    pl([(-G_["dolly_track"] / 2 * MM, zg + 68), (G_["dolly_track"] / 2 * MM, zg + 68)], "HIDDEN", dx=DX, dy=DY2)
    dim((0, zg - 40), (-G_["dolly_track"] / 2 * MM, zg), (G_["dolly_track"] / 2 * MM, zg), dx=DX, dy=DY2)
    adim((R + 260, zr + R * an + 30), (R, zr + R * an), (R + 400, zr + R * an),
         (R + 400, zr + R * an + 400 * an), dx=DX, dy=DY2)
    txt("anhedral %.1f deg" % W["dihedral"], (R + 300, zr - 40), 11, dx=DX, dy=DY2)
    txt("ON GORUNUS", (-bh, vz0 + vh + 60), 22, dx=DX, dy=DY2)

    # ---------------- baslik blogu
    tb = [
        "HIZ-750  -  3 GORUNUS (kavramsal)   olcek 1:1, birim mm",
        "b=%.0f  S=%.3f m2  AR=%.1f  cr=%.0f  ct=%.0f  MAC=%.0f  LE ok=%.0f deg"
        % (g["b"] * MM, W["S"], W["AR"], g["cr"] * MM, g["ct"] * MM, g["mac"] * MM, W["sweep_le"]),
        "Profil kok %s / uc %s, kuyruk %s   MTOW=%.2f kg   motor %s"
        % (W["airfoil_root"].upper(), W["airfoil_tip"].upper(), H["airfoil"].upper(),
           cgf["m"], P.ENGINE["model"]),
        "Yesil: kontrol yuzeyleri (aileron %.0f-%.0f%% b/2, flap %.0f-%.0f%% b/2)  kesikli: kirisler/gizli"
        % (100 * W["aileron"]["eta0"], 100 * W["aileron"]["eta1"], 100 * W["flap"]["eta0"], 100 * W["flap"]["eta1"]),
    ]
    TX, TY = L + 200, DY - 300
    pl([(TX - 20, TY + 40), (TX + 1900, TY + 40), (TX + 1900, TY - 4 * 32 - 10), (TX - 20, TY - 4 * 32 - 10)],
       closed=True)
    for i, s in enumerate(tb):
        txt(s, (TX, TY - i * 32), 16 if i == 0 else 13)

    dxf = os.path.join(OUT, "HIZ750_3view.dxf")
    doc.saveas(dxf)
    from ezdxf.addons.drawing import matplotlib as ezmpl
    for ext in ("png", "pdf"):
        ezmpl.qsave(msp, os.path.join(OUT, "HIZ750_3view." + ext), bg="#FFFFFF", dpi=220,
                    size_inches=(17, 11))
    return dxf


def draw_inboard(ctx):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle, Polygon
    xs = np.linspace(0, L, 300)
    rs = r_fus(xs)
    fig, ax = plt.subplots(figsize=(17, 6.5))
    ax.fill_between(xs, -rs, rs, color="#eeeeee", ec="k", lw=1.2)
    ax.plot(xs, rs - T_SKIN, "k", lw=.4)
    ax.plot(xs, -rs + T_SKIN, "k", lw=.4)
    e = ctx["int"]
    x0, x1 = e["x_eng"]
    re = e["r_engine"]
    ax.add_patch(Rectangle((x0, -re), x1 - x0, 2 * re, fc="#d9a066", ec="k", label="Motor P400-PRO"))
    ax.add_patch(Rectangle((e["x_pipe0"], -e["r_pipe"]), L - e["x_pipe0"], 2 * e["r_pipe"],
                           fc="#bbbbbb", ec="k", alpha=.7, label="Egzoz borusu"))
    # alik kanali: gercek ic loft'un x dilimlerindeki z sinirlari (merkez duzlem)
    din = ctx["duct_in"]
    bbd = din.BoundingBox()
    xd, zlo, zhi = [], [], []
    for x in np.linspace(bbd.xmin + 0.5, bbd.xmax - 0.5, 36):
        sl = din.intersect(box(x - 0.5, x + 0.5, -2, 2, -300, 300))
        if vol(sl) > 0:
            b_ = sl.BoundingBox()
            xd.append(x); zlo.append(b_.zmin); zhi.append(b_.zmax)
    ax.fill_between(xd, zlo, zhi, color="#9ecae1", ec="b", label="Hava alik S-kanali (ic)")
    # tanklar
    bb = ctx["parts"]["tank_fuselage"].BoundingBox()
    ax.add_patch(Rectangle((bb.xmin, bb.zmin), bb.xlen, bb.zlen, fc="#fdd49e", ec="k", alpha=.85,
                           label="Yakit: govde tanki (%.2f L)" % ctx["vols"]["tank_fuselage"]))
    bbf = ctx["parts"]["belly_fairing"].BoundingBox()
    ax.add_patch(Rectangle((bbf.xmin, bbf.zmin), bbf.xlen, -R - bbf.zmin + 4, fc="#c6c9cc", ec="k",
                           label="Karin kaplamasi (fairing)"))
    gr = ctx.get("ground")
    if gr:
        p0, p1 = gr["strike_pivot_mm"], gr["tail_strike_contact_mm"]
        ax.plot([p0[0], p1[0]], [p0[1], p1[1]], "m:", lw=1)
        if "tail_bumper" in ctx["parts"]:
            bbt = ctx["parts"]["tail_bumper"].BoundingBox()
            ax.add_patch(Rectangle((bbt.xmin, bbt.zmin), bbt.xlen, bbt.zlen, fc="#333", ec="k",
                                   label="Kuyruk tamponu"))
        if "tank_center" in ctx["parts"]:
            bbc = ctx["parts"]["tank_center"].BoundingBox()
            ax.add_patch(Rectangle((bbc.xmin, bbc.zmin), bbc.xlen, bbc.zlen, fc="#fdae6b", ec="k", alpha=.8,
                                   label="Yakit: kanat kutusu orta tanki (%.2f L)" % ctx["vols"]["tank_center"]))
        ax.annotate("kuyruk carpma %.1f$^\\circ$" % gr["tail_strike_deg"], p1, xytext=(-90, -16),
                    textcoords="offset points", color="m", fontsize=8)
    bb = ctx["parts"]["tank_wing_R"].BoundingBox()
    ax.add_patch(Rectangle((bb.xmin, bb.zmin), bb.xlen, bb.zlen, fc="none", ec="#e6550d", hatch="///",
                           lw=1.2, label="Yakit: kanat koku entegre tank izdusumu (2x%.2f L)"
                           % ctx["vols"]["tank_wing_R"]))
    # kanat kok profili + kirisler
    W = P.WING
    up, lo = airfoil(W["airfoil_root"])
    cr = P.wing_geom()["cr"] * MM
    xr = W["x_root_le"] * MM
    zr = W["z_root"] * MM
    pts = np.array([(xr + X * cr, zr + Z * cr) for X, Z in np.vstack([up, lo])])
    ax.add_patch(Polygon(pts, closed=True, fc="#8aa", ec="k", alpha=.8, label="Kanat koku"))
    for f in W["spar_xc"]:
        ax.plot([xr + f * cr] * 2, [zr - 14, zr + 14], "k", lw=3)
    # kizak + dolly + yatay kuyruk cercevesi
    G_ = P.GEAR
    zg = e["zg"]
    sx0, sx1, sh = G_["skid_x0"] * MM, G_["skid_x1"] * MM, G_["skid_h"] * MM
    ax.add_patch(Rectangle((sx0, -R - sh), sx1 - sx0, sh, fc="#333", ec="k", label="Kizak"))
    xc, wb = e["dolly_xc"], G_["dolly_wheelbase"] * MM
    for dxw in (-wb / 2, wb / 2):
        ax.add_patch(Circle((xc + dxw, zg + 50), 50, fc="none", ec="#666", ls="--"))
    ax.plot([xc - wb / 2 - 30, xc + wb / 2 + 30], [zg + 68] * 2, "--", color="#666", label="Dolly (yer ekipmani)")
    if "ht_carry_yoke" in ctx["parts"]:
        bb = ctx["parts"]["ht_carry_yoke"].BoundingBox()
        ax.add_patch(Rectangle((bb.xmin, 0), bb.xlen, bb.zmax, fc="#636363", ec="k", alpha=.7,
                               label="Y.kuyruk tasiyici cerceve (egzoz ustu)"))
    ax.axhline(zg, color="g", lw=.8, ls="--")
    # kutle kalemleri
    for i, (nm, m, x, z) in enumerate(P.MASS_ITEMS):
        ax.plot(x * MM, z * MM, "o", ms=3 + 2.5 * m, mfc="none", mec="r")
        ax.annotate("%d" % (i + 1), (x * MM, z * MM), fontsize=7, color="r",
                    xytext=(3, 3 + (i % 3) * 6), textcoords="offset points")
    for fr, lab in ((1.0, "CG dolu"), (0.0, "CG bos")):
        cg = P.mass_summary(fr)
        ax.plot(cg["x_cg"] * MM, cg["z_cg"] * MM, marker="P", ms=12, color="m")
        ax.annotate(lab, (cg["x_cg"] * MM, cg["z_cg"] * MM), xytext=(-20, -28 if fr else 18),
                    textcoords="offset points", color="m", fontsize=9)
    legend_items = "\n".join("%2d %s (%.2f kg)" % (i + 1, n, m) for i, (n, m, x, z) in enumerate(P.MASS_ITEMS))
    ax.text(1.01, 1.0, legend_items, transform=ax.transAxes, fontsize=7, va="top", family="monospace")
    ax.set_aspect("equal")
    ax.set_xlim(-30, L + 60)
    ax.set_ylim(zg - 20, 200)
    ax.set_xlabel("x [mm] (burun ucundan)")
    ax.set_ylabel("z [mm]")
    ax.set_title("HIZ-750 ic yerlesim (inboard profile) - merkez duzlem kesiti")
    ax.grid(alpha=.25)
    ax.legend(loc="lower left", fontsize=7, ncol=3)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(OUT, "HIZ750_inboard." + ext), dpi=170)
    plt.close(fig)


def render_iso(parts, colors):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from stl import mesh as stlmesh
    light = np.array([0.4, -0.5, 0.8])
    light /= np.linalg.norm(light)
    fig = plt.figure(figsize=(14, 9))
    ax = fig.add_subplot(111, projection="3d")
    tmpd = tempfile.mkdtemp(prefix="hzr", dir="C:/Users/Urungu/.hz750")
    for name, shp in parts.items():
        if name in ("engine", "tank_fuselage", "tank_wing_R", "tank_wing_L", "tank_belly", "exhaust_pipe",
                    "wing_box", "ht_carry_yoke", "tank_center", "wing_center", "frames"):
            continue
        fn = os.path.join(tmpd, "r.stl")
        cq.exporters.export(shp, fn, tolerance=1.5, angularTolerance=0.4)
        m = stlmesh.Mesh.from_file(fn)
        n = m.normals / (np.linalg.norm(m.normals, axis=1)[:, None] + 1e-12)
        sh = 0.35 + 0.65 * np.abs(n @ light)
        base = np.array(matplotlib.colors.to_rgb(colors.get(name, "#bbbbbb")))
        fc = np.clip(base[None, :] * sh[:, None], 0, 1)
        pc = Poly3DCollection(m.vectors, facecolors=fc, edgecolors="none", linewidths=0)
        ax.add_collection3d(pc)
    shutil.rmtree(tmpd, ignore_errors=True)
    bh = P.wing_geom()["b"] / 2 * MM
    ax.set_xlim(0, L)
    ax.set_ylim(-L / 2, L / 2)
    ax.set_zlim(-L / 4, L / 4)
    ax.set_box_aspect((1, 1, 0.5), zoom=1.35)
    ax.view_init(elev=24, azim=-128)
    ax.set_axis_off()
    ax.set_title("HIZ-750 izometrik gorunus (b=%.0f mm, L=%.0f mm)" % (2 * bh, L))
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "HIZ750_iso.png"), dpi=150)
    plt.close(fig)


# ====================================================================== ana akis
def main():
    os.makedirs(OUT, exist_ok=True)
    print("govde...")
    fus_outer, fus_inner = build_fuselage()
    print("kanat...")
    wparts, wing_full, wing_exp, wxle, wc, wbh = build_wing(fus_outer)
    f0, f1 = P.WING["spar_xc"]
    x_fs, x_rs = wxle(0) + f0 * wc(0), wxle(0) + f1 * wc(0)
    print("alik...")
    duct, duct_in, duct_out, diverter, inlet_info, ramp, ramp_wall = build_inlet(x_rs)
    if ramp is not None:
        ramp_wall = ramp_wall.intersect(fus_outer)     # rampa taban/yan duvari govde zarfi icinde kalir
        fus_outer_r = fus_outer.cut(ramp)
    else:
        fus_outer_r = fus_outer
    # kanal duvari govde kabugunu deldigi yerde kabugun yerini alir (birlesim: kanal disi kabuktan cikarilir)
    fus_shell = fus_outer_r.cut(fus_inner).cut(duct_out)
    if ramp_wall is not None:
        fus_shell = fus_shell.fuse(ramp_wall.cut(duct_out)).clean()
    print("kuyruk...")
    hparts, ht_full, hxle, hc, hbh = build_htail(fus_outer)
    vparts, vt_full, vxle, vc, vh, vz0 = build_vtail(fus_outer)
    print("ic sistemler...")
    wt_L = {k: vol(wparts[k]) / 1e6 for k in ("tank_wing_R", "tank_wing_L", "tank_center") if k in wparts}
    ramp_cut = None
    if ramp is not None:
        ramp_cut = ramp.fuse(ramp_wall)
    iparts, gparts, iinfo = build_internal(fus_outer, duct_out, wparts["wing_box"], x_fs,
                                           sum(wt_L.values()), wparts["belly_fairing"], wing_full, ramp_cut)
    iinfo["dolly_xc"] = P.mass_summary(1.0)["x_cg"] * MM

    if "ht_carry_yoke" in hparts:          # saplama rod delikleri
        fus_shell = fus_shell.cut(hparts["ht_carry_yoke"])
    parts = {"fuselage": fus_shell, "inlet_duct": duct}
    if diverter is not None:
        parts["diverter"] = diverter
    parts.update(wparts)
    parts.update(hparts)
    parts.update(vparts)
    parts.update(iparts)

    colors = {"fuselage": "#d0d4d8", "inlet_duct": "#9ecae1", "diverter": "#555555",
              "wing_panels": "#e8e8e8", "wing_box": "#222222", "aileron_R": "#e34a33",
              "aileron_L": "#e34a33", "flap_R": "#fdae6b", "flap_L": "#fdae6b", "htail": "#e8e8e8",
              "elevator_R": "#e34a33", "elevator_L": "#e34a33", "vtail": "#e8e8e8", "rudder": "#e34a33",
              "engine": "#d9a066", "exhaust_pipe": "#888888", "tank_fuselage": "#fdd49e",
              "tank_wing_R": "#fdae6b", "tank_wing_L": "#fdae6b", "skid": "#333333",
              "ht_carry_yoke": "#636363", "dolly": "#2c7fb8", "belly_fairing": "#c6c9cc",
              "wing_center": "#9aa3a8", "tank_center": "#fdae6b", "tail_bumper": "#333333",
              "frames": "#555555"}

    print("disa aktarim...")
    for old in ("tank_main", "tank_saddle", "gear") + (() if diverter is not None else ("diverter",)):
        for sub, ext in (("step", ".step"), ("stl", ".stl")):
            fp = os.path.join(OUT, sub, old + ext)
            if os.path.exists(fp):
                os.remove(fp)
    assy = cq.Assembly(name="HIZ750")
    for n, s_ in list(parts.items()) + list(gparts.items()):
        export(s_, os.path.join(OUT, "step", n + ".step"))
        export(s_, os.path.join(OUT, "stl", n + ".stl"), tolerance=0.2, angularTolerance=0.15)
        if n in parts:
            assy.add(s_, name=n, color=cq.Color(*matplotlib_rgb(colors.get(n, "#bbbbbb"))))
    tmpd = tempfile.mkdtemp(prefix="hza", dir="C:/Users/Urungu/.hz750")
    tmp = os.path.join(tmpd, "a.step")
    assy.export(tmp)
    shutil.move(tmp, os.path.join(OUT, "HIZ750_assembly.step"))
    assy_g = cq.Assembly(name="HIZ750_on_dolly")
    assy_g.add(assy, name="ucak")
    assy_g.add(gparts["dolly"], name="dolly", color=cq.Color(*matplotlib_rgb(colors["dolly"])))
    tmp = os.path.join(tmpd, "g.step")
    assy_g.export(tmp)
    shutil.move(tmp, os.path.join(OUT, "HIZ750_on_dolly.step"))
    shutil.rmtree(tmpd, ignore_errors=True)

    # ------------------------------------------------ hacim / CG / alan / cakisma kontrolu
    print("kontroller...")
    vols = {"tank_fuselage": tank_inner_volume(parts["tank_fuselage"], 1.0) / 1e6}
    if "tank_belly" in parts:
        vols["tank_belly"] = tank_inner_volume(parts["tank_belly"], 1.0) / 1e6
    vols.update(wt_L)
    fuel_L = P.FUEL["mass"] / P.FUEL["density"]
    tank_need = (P.FUEL["tanks"]["fuselage_L"] + 2 * P.FUEL["tanks"]["wing_integral_L_each"]
                 + P.FUEL["tanks"].get("center_L", 0.0))
    tank_tot = sum(vols.values())
    cen = {k: parts[k].Center() for k in vols}
    # yakit tanklara hacimle orantili dagitildi varsayimi (kapasite > yakit hacmi)
    cx = sum(cen[k].x * vols[k] for k in vols) / tank_tot / MM
    cz = sum(cen[k].z * vols[k] for k in vols) / tank_tot / MM
    fus_wet = (fus_outer.Area() - math.pi * RT ** 2) / 1e6
    af = section_area_factor(P.WING["airfoil_root"])
    wing_wet = (wing_exp.Area() - 2 * af * wc(R) ** 2) / 1e6
    hs0 = float(r_fus(hxle(0)))
    ht_exp = parts["htail"].fuse(parts["elevator_R"]).fuse(parts["elevator_L"])
    ht_wet = (ht_exp.Area() - 2 * section_area_factor(P.HTAIL["airfoil"]) * hc(hs0) ** 2) / 1e6
    vt_exp = parts["vtail"].fuse(parts["rudder"])
    vt_wet = (vt_exp.Area() - section_area_factor(P.VTAIL["airfoil"]) * vc(0) ** 2) / 1e6
    x0, x1 = iinfo["x_eng"]
    xe = np.linspace(x0, x1, 60)
    clear = r_fus(xe) - T_SKIN - iinfo["r_engine"]
    i_min = int(np.argmin(clear))
    pipe_solid = cyl_x(iinfo["r_pipe"], iinfo["x_pipe0"], L)
    ht_all = ht_exp.fuse(parts["ht_carry_yoke"]) if "ht_carry_yoke" in parts else ht_full
    duct_aft = duct.intersect(box(x_fs, L, -R, R, -R, R))
    wing_tanks = parts["tank_wing_R"].fuse(parts["tank_wing_L"])
    checks = {
        "engine_vs_fuselage_wall": inter_vol(parts["engine"], fus_shell),
        "engine_vs_wing_box": inter_vol(parts["engine"], parts["wing_box"]),
        "engine_vs_inlet_duct": inter_vol(parts["engine"], duct),
        "duct_vs_wing_box": inter_vol(duct, parts["wing_box"]),
        "dorsal_hump_duct_wall_outside_fuselage_aft_of_front_spar": vol(duct_aft.cut(fus_inner)),
        "htail_and_yoke_vs_exhaust_pipe": inter_vol(ht_all, pipe_solid),
        "ht_yoke_vs_fuselage_wall": inter_vol(parts["ht_carry_yoke"], fus_shell)
        if "ht_carry_yoke" in parts else 0.0,
        "vtail_vs_exhaust_pipe": inter_vol(vt_full, pipe_solid),
        "tank_fuselage_vs_duct": inter_vol(parts["tank_fuselage"], duct),
        "tank_fuselage_vs_wing_box": inter_vol(parts["tank_fuselage"], parts["wing_box"]),
        "tank_fuselage_vs_fuselage_wall": inter_vol(parts["tank_fuselage"], fus_shell),
        "tank_wing_vs_duct": inter_vol(wing_tanks, duct),
        "tank_center_vs_duct_engine": inter_vol(parts["tank_center"], duct.fuse(parts["engine"]))
        if "tank_center" in parts else 0.0,
        "wing_center_vs_engine": inter_vol(parts["wing_center"], parts["engine"]),
        "wing_center_vs_duct": inter_vol(parts["wing_center"], duct),
        "wing_center_vs_tank_fuselage": inter_vol(parts["wing_center"], parts["tank_fuselage"]),
        "frames_vs_engine_tanks_duct": inter_vol(parts["frames"], parts["engine"].fuse(parts["tank_fuselage"])
                                                 .fuse(duct)) if "frames" in parts else 0.0,
        "frames_vs_fuselage_wall": inter_vol(parts["frames"], fus_shell) if "frames" in parts else 0.0,
        "tail_bumper_vs_fuselage_wall": inter_vol(parts["tail_bumper"], fus_shell)
        if "tail_bumper" in parts else 0.0,
        "tank_fuselage_vs_inlet_ramp": inter_vol(parts["tank_fuselage"], ramp_cut) if ramp_cut is not None else 0.0,
        "engine_vs_wing_lower_skin_aft": inter_vol(parts["engine"], parts["wing_center"].intersect(
            box(x_rs, 4e3, -R, R, -R, R))),
        "tank_wing_vs_engine": inter_vol(wing_tanks, parts["engine"]),
        "skid_vs_fuselage_wall": inter_vol(parts["skid"], fus_shell),
        "dolly_vs_aircraft_outer": inter_vol(gparts["dolly"], fus_outer.fuse(wing_full)),
        "fairing_vs_tank_fuselage": inter_vol(parts["belly_fairing"], parts["tank_fuselage"]),
        "fairing_vs_skid": inter_vol(parts["belly_fairing"], parts["skid"]),
        "fairing_vs_wing_panels": inter_vol(parts["belly_fairing"], parts["wing_panels"]),
        "flap_vs_wing_panels": inter_vol(parts["flap_R"].fuse(parts["flap_L"]), parts["wing_panels"]),
        "duct_vs_fuselage_wall_aft_of_x_box_front": inter_vol(
            duct.intersect(box(x_fs, L, -R, R, -R, R)), fus_shell),
    }
    # kuyruk carpma acisi ve dolly uzerinde 6 deg yer acikligi (dis yuzey mesh noktalari, xz duzlemi)
    ext_names = [k for k in parts if k not in ("engine", "exhaust_pipe", "tank_fuselage", "tank_wing_R",
                                               "tank_wing_L", "tank_belly", "tank_center", "wing_box",
                                               "ht_carry_yoke", "inlet_duct", "wing_center", "frames")]
    pts = np.vstack([np.array([(v.x, v.z) for v in parts[k].tessellate(2.0, 0.5)[0]]) for k in ext_names])
    sx1, szb = P.GEAR["skid_x1"] * MM, -R - P.GEAR["skid_h"] * MM
    skid_pivot = (sx1, szb)
    tbp = P.GEAR.get("tail_bumper")
    both_contact_deg = None
    if tbp and "tail_bumper" in parts:
        bbb = parts["tail_bumper"].BoundingBox()
        piv = (bbb.xmax, bbb.zmin)
        both_contact_deg = round(math.degrees(math.atan2(bbb.zmin - szb, bbb.xmin - sx1)), 2)
        sx1, szb = piv
    aft = pts[pts[:, 0] > sx1 + 1]
    ang = np.degrees(np.arctan2(aft[:, 1] - szb, aft[:, 0] - sx1))
    i_s = int(np.argmin(ang))
    # dolly: arka teker temas noktasi etrafinda ucak+dolly birlikte theta kadar burun yukari
    xw = iinfo["dolly_xc"] + P.GEAR["dolly_wheelbase"] * MM / 2
    zg = iinfo["zg"]

    def clearance(theta):
        th = math.radians(theta)
        dx, dz = pts[:, 0] - xw, pts[:, 1] - zg
        zr = zg - dx * math.sin(th) + dz * math.cos(th)     # burun yukari: one dogru noktalar yukselir
        j = int(np.argmin(zr))
        return round(float(zr[j] - zg), 1), round(float(pts[j, 0]), 1)
    # ayni duzlemde, kizaksiz sertlesmis tail skid icin onerilen kizak sonu (aci >= 9 deg)
    need_x1 = None
    for x1c in np.arange(sx1, L, 5.0):
        a2 = pts[pts[:, 0] > x1c + 1]
        if len(a2) == 0 or np.degrees(np.arctan2(a2[:, 1] - szb, a2[:, 0] - x1c)).min() >= 9.0:
            need_x1 = float(x1c)
            break
    ground = dict(
        tail_strike_deg=round(float(ang[i_s]), 2), tail_strike_target_deg=9.0,
        tail_strike_contact_mm=(round(float(aft[i_s, 0]), 1), round(float(aft[i_s, 1]), 1)),
        skid_aft_end_mm=skid_pivot, strike_pivot_mm=(round(sx1, 1), round(szb, 1)),
        skid_to_bumper_contact_deg=both_contact_deg,
        skid_x1_needed_for_9deg_mm=need_x1,
        skid_depth_at_needed_x1_mm=(round(float(szb + r_fus(need_x1)), 1) * -1) if need_x1 else None,
        dolly_rear_wheel_contact_mm=(round(xw, 1), round(zg, 1)),
        dolly_clearance_0deg=clearance(0.0),
        dolly_clearance_alpha=dict(alpha_deg=P.GEAR.get("dolly_alpha", 3.0),
                                   clearance_mm_at_x=clearance(P.GEAR.get("dolly_alpha", 3.0))),
        dolly_clearance_6deg=clearance(6.0),
    )
    # kutle kalemi noktalari bir hacmin icine dusuyor mu (yerlesim uyarisi)
    inside = []
    for nm, m, x, z in P.MASS_ITEMS:
        pt = V(x * MM, 0, z * MM)
        for k in ("tank_fuselage", "engine", "inlet_duct", "wing_box"):
            try:
                if parts[k].isInside(pt):
                    inside.append(dict(item=nm, x_m=x, z_m=z, inside=k))
            except Exception:
                pass
    ctr = iinfo["tank_fus_x"]
    rep = dict(
        iteration="3-kapanis",
        units="mm3 (cakisma) / L / m2",
        params_snapshot=dict(MTOW=round(P.mass_summary(1.0)["m"], 3), fuel_kg=P.FUEL["mass"],
                             fuel_L=fuel_L, inlet_w=P.INLET["width"], inlet_h=P.INLET["height"],
                             wing_x_root_le=P.WING["x_root_le"], spar_xc=P.WING["spar_xc"],
                             engine_x_front=P.ENGINE["x_front"], inlet_x_lip=P.INLET["x_lip"]),
        tank_volumes_L={k: round(v, 3) for k, v in vols.items()},
        tank_total_L=round(tank_tot, 3), tank_target_L=round(tank_need, 3),
        tank_ok=tank_tot >= tank_need - 1e-3,
        tank_fuselage_x_mm=(round(ctr[0], 1), round(ctr[1], 1)),
        tank_centroids_x_m={k: round(cen[k].x / MM, 4) for k in vols},
        fuel_cg_x_m=round(cx, 4), fuel_cg_z_m=round(cz, 4), fuel_cg_target_x_m=P.FUEL["x"],
        fuel_cg_ok=abs(cx - P.FUEL["x"]) <= 0.02,
        wetted_area_m2=dict(fuselage=round(fus_wet, 4), wing_exposed=round(wing_wet, 4),
                            htail=round(ht_wet, 4), vtail=round(vt_wet, 4),
                            skid_approx=round(parts["skid"].Area() / 2e6, 4)),
        part_volumes_cm3={k: round(vol(s_) / 1e3, 1) for k, s_ in list(parts.items()) + list(gparts.items())},
        engine_radial_clearance_mm=dict(min=round(float(clear.min()), 2),
                                        at_x=round(float(xe[i_min]), 1),
                                        front=round(float(clear[0]), 2), target=ENG_CLEAR),
        interference_mm3={k: round(v, 1) for k, v in checks.items()},
        ground_geometry=ground,
        wing_tank_inner_L_per_side=WING_INFO["tank_cmp_L"],
        wing_tank_walls_mm=dict(skin=T_TANK_SKIN, web=T_TANK_WEB, rib=T_TANK_RIB),
        structures_agent_value_L_per_side=0.39,
        belly_tank=iinfo["belly_note"],
        flap=dict(type=P.WING["flap"].get("type"), cf=P.WING["flap"]["cf"], slot_mm=FLAP_SLOT,
                  hinge_line_mm=WING_INFO["flap_hinge_mm"]),
        wing_inside_fuselage_cut_x_mm=WING_INFO["wing_cut_x_mm"],
        belly_fairing=dict(bottom_z_mm=WING_INFO["fairing_bottom_z_mm"], x_mm=WING_INFO["fairing_x_mm"],
                           depth_below_fuselage_mm=WING_INFO["fairing_depth_below_fuselage_mm"],
                           volume_cm3=round(vol(parts["belly_fairing"]) / 1e3, 1)),
        mass_items_inside_volumes=inside,
        spars_root_x_mm=dict(front=round(x_fs, 1), rear=round(x_rs, 1)), engine_front_x_mm=x0,
        engine_to_rear_spar_gap_mm=round(x0 - x_rs, 1),
        wing_box_top_z_mm=round(wing_box_top_z(), 2),
        inlet=inlet_info,
    )
    with open(os.path.join(OUT, "cad_report.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2, ensure_ascii=False)
    print(json.dumps(rep, indent=2, ensure_ascii=False))

    ctx = dict(w_xle=wxle, w_c=wc, w_bh=wbh, h_xle=hxle, h_c=hc, h_bh=hbh, v_xle=vxle, v_c=vc,
               v_h=vh, v_z0=vz0, int=iinfo, parts=parts, vols=vols, duct_in=duct_in)
    print("cizimler...")
    ctx["ground"] = ground
    draw_3view(ctx)
    draw_inboard(ctx)
    ctx["ground"] = ground
    render_iso(dict(parts, dolly=gparts["dolly"]), colors)
    print("tamam:", OUT)


def matplotlib_rgb(hexs):
    hexs = hexs.lstrip("#")
    return tuple(int(hexs[i:i + 2], 16) / 255 for i in (0, 2, 4))


if __name__ == "__main__":
    main()
