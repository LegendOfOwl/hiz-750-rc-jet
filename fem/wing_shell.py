"""Parametrik S8R kompozit kanat yarısı (iter5 düzeltilmiş model).

Taslaktan farklar (fem/RESULTS_iter5.md):
  * Burun: x/c=.01'de 6 kat (iki yüzün birleşimi) kumaş burun web'i; x/c<.01 kütle olarak 1D'den.
    (x/c=0'a kadar kapalı burun denendi: orta/ince ağda uç bölgesinde burun yarıçapı ~0.6 mm < 1.07 mm
    laminat -> CCX genişletilmiş katıda "nonpositive jacobian".)
  * Sabit arka yapı arka kirişten menteşe hattına (x/c=.75) kadar; menteşe web'i (2 kat ±45 kumaş)
    arka hücreyi kapatır. x/c>.75 (flap/aileron, firar kenarı) yalnız kütle olarak temsil edilir.
  * Sandviç bölgeleri: çekirdek yalnız yerel profil derinliği iki sandviç + 2 mm boşluğa izin verdiği
    elemanlarda; burun ve ince arka bölgede yüzler birleşik monolitik laminattır (çakışma yok).
  * *ORIENTATION eleman başına yüzeye teğet: 1-ekseni kiriş (sabit x/c) doğrultusu, 3-ekseni
    eleman normali. Kumaş katlar bu eksene ±45 (dokuma E1=E2 olduğundan tek tabaka 45°).
    Web'ler ±45 kumaş (taslakta web 0° idi ve 1-3 düzlemi web düzlemindeydi -> G=G13 hatası).
  * Web'ler OFFSET=0 (orta düzlem); kabuklar OFFSET=0.5 (OML referans, malzeme içe), ilk tabaka içte.
  * Schrenk nihai yükü (12 g x 1.5) üst/alt kabuğa yarı yarıya, veter boyunca 3(1-x)^2 dağılımıyla
    (basınç merkezi ~.25c) tutarlı düğüm kuvvetleri olarak (Gauss 3x3) uygulanır; atalet rahatlatması yok.
  * Kütle: her açıklık şeridinde kabuk kütlesi + kalan kütle 1D modelin (structures) m'(y), kesit CG(y)
    ve kesit ataletine eşlenir (iki veter kolonu NSM). Yakıt kiriş arası kabuklara alan başına düzgün.
  * Kök y=.035 m (cıvata hattı, fe_modal ile aynı) tüm düğümlerde öteleme 1-3 (genişletilmiş düğümler
    dahil -> ankastre).
  * Kaburgalar (taslakta yoktu): 0.086 m aralık (structures m_ribs'ten), uç kapama ve tank kapama
    kaburgası dahil 8 adet; kesit distorsiyonunu sınırlar (1D Bredt GJ kesitin korunduğunu varsayar).
Çözücü: *STATIC/*FREQUENCY SOLVER=SPOOLES (PaStiX kupon testinde gürültülüydü).
"""
import math

import numpy as np

from validation.common import Blocked, digest, require_module, write_json

X_HINGE = .75          # sabit yapı arka sınırı / menteşe web'i
X_NOSE = .01           # burun kapama web'i (x/c<.01 kütle; uçta burun yarıçapı < laminat kalınlığı)
LEVER_X_MAX = .95      # menteşe gerisi kaldıraç kütlesinin en arka konumu (x/c)
N_HINGE_PLIES = 2      # menteşe web'i kat sayısı (varsayım)
CORE_CLEARANCE = 2e-3  # sandviç için iki iç yüz arasında gereken asgari boşluk [m]
N_MODES = 10


def materials():
    from structures import structures as ST
    ud, fab, core = ST.MAT["UD"], ST.MAT["FAB"], ST.MAT["CORE"]
    common = dict(E2=9e9, E3=9e9, nu12=.30, nu13=.30, nu23=.30,
                  G12=5e9, G13=5e9, G23=9e9/2.6, Yt=50e6, Yc=200e6, S12=80e6)
    result = dict(
        UD=dict(common, E1=ud["E1"], rho=ud["rho"], Xt=ud["Xt"], Xc=ud["Xc"]),
        FAB=dict(E1=fab["E"], E2=fab["E"], E3=9e9, nu12=.05, nu13=.3, nu23=.3,
                 G12=4.5e9, G13=4.5e9, G23=4.5e9, rho=fab["rho"],
                 Xt=600e6, Xc=600e6, Yt=600e6, Yc=600e6, S12=fab["tau_allow"]),
        CORE=dict(E1=70e6, E2=70e6, E3=70e6, G12=19e6, G13=19e6, G23=19e6,
                  nu12=.3, nu13=.3, nu23=.3, rho=core["rho"], S_core=.8e6))
    for name in ("UD", "FAB"):
        m = result[name]
        m["F12"] = -.5 / math.sqrt(m["Xt"] * m["Xc"] * m["Yt"] * m["Yc"])
    return result


def material_cards(mats):
    cards = []
    for name, m in mats.items():
        cards += [f"*MATERIAL, NAME={name}", "*ELASTIC, TYPE=ENGINEERING CONSTANTS",
                  ", ".join(f"{m[k]:.10e}" for k in ("E1", "E2", "E3", "nu12", "nu13", "nu23", "G12", "G13")),
                  f"{m['G23']:.10e}", "*DENSITY", f"{m['rho']:.10e}"]
    return cards


def quad8_shape(xi, eta):
    """Abaqus/CCX S8R düğüm sırası: köşeler (-1,-1),(1,-1),(1,1),(-1,1), kenar ortaları 5-8."""
    n = np.empty(8)
    for k, (a, b) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        n[k] = .25 * (1 + a * xi) * (1 + b * eta) * (a * xi + b * eta - 1)
    n[4] = .5 * (1 - xi * xi) * (1 - eta)
    n[5] = .5 * (1 + xi) * (1 - eta * eta)
    n[6] = .5 * (1 - xi * xi) * (1 + eta)
    n[7] = .5 * (1 - xi) * (1 - eta * eta)
    return n


def chord_load_shape(x):
    """Veter yük biçimi g(x)=3(1-x)^2, integral 1, merkez .25c (yumuşak, Gauss ile integrallenebilir)."""
    return 3 * (1 - x) ** 2


def geometry(level):
    import params as P
    from structures import structures as ST
    factor = 2 ** ("coarse", "medium", "fine").index(level)
    xf, xr = P.WING["spar_xc"]
    cap_half = .025 / P.wing_geom()["cr"]
    knots = [X_NOSE, .04, .10, xf - cap_half, xf, xf + cap_half, .33, .42, xr - cap_half, xr, xr + cap_half,
             .65, X_HINGE]
    xx = sorted({a + (b - a) * i / factor for a, b in zip(knots, knots[1:]) for i in range(factor + 1)})
    ny = 8 * factor
    yf = np.linspace(.035, ST.B2, ny + 1)
    return dict(factor=factor, xx=xx, yf=yf, ny=ny, xf=xf, xr=xr, cap_half=cap_half, knots=knots)


def prepare(args, work):
    require_module("gmsh")
    require_module("numpy")
    import gmsh
    import params as P
    from structures import structures as ST
    from fem.cases import set_lines
    fuel_state = getattr(args, "wing_fuel", "full") or "full"
    base = ST.wing_section_model()
    ws, mat = base["ws"], materials()
    g = geometry(args.level)
    xx, yf, ny, xf, xr, cap_half = g["xx"], g["yf"], g["ny"], g["xf"], g["xr"], g["cap_half"]
    y0, b2 = .035, ST.B2
    sweep = math.tan(math.radians(P.WING["sweep_le"]))
    dihedral = math.tan(math.radians(P.WING["dihedral"]))
    t_ud, t_fab, t_core = ST.MAT["UD"]["t_ply"], ST.MAT["FAB"]["t_ply"], ST.MAT["CORE"]["t"]
    nodes, lookup = {}, {}
    elements, kinds, layers_of, orient_of, offset_of, strip_of, center_of = {}, {}, {}, {}, {}, {}, {}

    def position(xc, y, eta):
        c = float(ST.chord(y))
        return np.array([P.WING["x_root_le"] + sweep * y + xc * c, y,
                         P.WING["z_root"] + dihedral * y + eta * float(ST.yt64(xc, ST.tc(y))) * c])

    def node(xc, y, eta):
        point = position(xc, y, eta)
        key = tuple(round(float(v), 10) for v in point)
        if key not in lookup:
            lookup[key] = len(nodes) + 1
            nodes[lookup[key]] = [float(v) for v in point]
        return lookup[key]

    def frame(mapping, u, v, du, dv):
        """Eleman merkezinde teğet çerçeve: a = açıklık (v) teğeti, n = normal (u x v sırası)."""
        tu = (mapping(u + du, v) - mapping(u - du, v)) / (2 * du)
        tv = (mapping(u, v + dv) - mapping(u, v - dv)) / (2 * dv)
        return tu, tv

    orientations = {}

    def orientation(a, b):
        key = tuple(round(float(x), 4) for x in (*a, *b))
        if key not in orientations:
            orientations[key] = f"OR{len(orientations)+1}"
        return orientations[key]

    def add(conn, kind, layers, offset, strip, a_span, normal, centre, diag_only=False):
        tag = len(elements) + 1
        elements[tag] = conn
        kinds[tag] = kind
        a = a_span - np.dot(a_span, normal) * normal
        a /= np.linalg.norm(a)
        b = np.cross(normal, a)
        span_name = orientation(a, b)
        diag_name = orientation((a + b) / math.sqrt(2), (b - a) / math.sqrt(2))
        layers_of[tag] = [(m, t, diag_name if o == "DIAG" else span_name) for m, t, o in layers]
        orient_of[tag] = dict(span=[*a], normal=[*normal])
        offset_of[tag] = offset
        strip_of[tag] = strip
        center_of[tag] = centre
        return tag

    def quad_conn(mapping, u0, u1, v0, v1, reverse):
        uv = ((u0, v0), (u1, v0), (u1, v1), (u0, v1), ((u0+u1)/2, v0), (u1, (v0+v1)/2), ((u0+u1)/2, v1), (u0, (v0+v1)/2))
        conn = [mapping(u, v) for u, v in uv]
        if reverse:
            conn = [conn[i] for i in (0, 3, 2, 1, 7, 6, 5, 4)]
        return conn

    sandwich_report = []
    # Kat planı ve sandviç/monolitik kararı KABA hücre (düğüm aralığı x kaburga bölmesi) üzerinden verilir:
    # üç ağ aynı geometriyi/laminatı çözer (GCI için şart). Kat düşümleri kaburga hatlarında.
    knots, yc = g["knots"], np.linspace(y0, b2, 9)
    for j, (ya, yb) in enumerate(zip(yf, yf[1:])):
        ym = (ya + yb) / 2
        bay = min(int((ym - y0) / (yc[1] - yc[0])), 7)
        y_lo, y_hi = yc[bay], yc[bay + 1]
        ym_c = (y_lo + y_hi) / 2
        nud = int(round(float(np.interp(ym_c, ST.YS, ws["n_ud"]))))
        nw = int(round(float(np.interp(ym_c, ST.YS, ws["n_web"]))))
        for xa, xb in zip(xx, xx[1:]):
            xm = (xa + xb) / 2
            k0 = max(i for i in range(len(knots) - 1) if knots[i] <= xm)
            x_lo, x_hi = knots[k0], knots[k0 + 1]
            xm_c = (x_lo + x_hi) / 2
            nf = P.WING["skin_plies"][0 if xm_c <= xr else 1]
            cap = min(abs(xm_c - xf), abs(xm_c - xr)) < cap_half
            ud_layer = [("UD", nud * t_ud, "SPAN")] if cap else []
            sandwich = ud_layer + [("FAB", nf * t_fab, "DIAG"), ("CORE", t_core, "SPAN"), ("FAB", nf * t_fab, "DIAG")]
            depth = 2 * float(ST.yt64(xm, ST.tc(ym))) * float(ST.chord(ym))
            depth_min = min(2 * float(ST.yt64(xq, ST.tc(yq))) * float(ST.chord(yq))
                            for xq in (x_lo, x_hi) for yq in (y_lo, y_hi))
            t_sand = sum(t for _, t, _ in sandwich)
            use_core = depth_min - 2 * t_sand >= CORE_CLEARANCE and x_lo >= .03
            layers = sandwich if use_core else ud_layer + [("FAB", 2 * nf * t_fab, "DIAG")]
            t_lam = sum(t for _, t, _ in layers)
            kind = ("CAP" if cap else "SKIN") + ("_F" if xm_c <= xr else "_A") + ("" if use_core else "_MONO")
            sandwich_report.append(dict(strip=j, xc=xm, depth=depth, t_laminate=t_lam, core=use_core,
                                        gap=depth - 2 * t_lam))
            for side in (1, -1):
                mapping = (lambda s: (lambda u, v: node(u, v, s)))(side)
                pos = (lambda s: (lambda u, v: position(u, v, s)))(side)
                conn = quad_conn(mapping, xa, xb, ya, yb, side < 0)
                tu, tv = frame(pos, xm, ym, 1e-6, 1e-6)
                normal = np.cross(tu, tv) * side
                normal /= np.linalg.norm(normal)
                add(conn, kind, layers, .5, j, tv, normal, [xm, ym, side])
        nose_plies = 2 * P.WING["skin_plies"][0]
        for xweb, label, plies in ((X_NOSE, "WEB_N", nose_plies), (xf, "WEB_F", nw), (xr, "WEB_R", nw),
                                   (X_HINGE, "WEB_H", N_HINGE_PLIES)):
            zs = np.linspace(-1, 1, 2 * g["factor"] + 1)
            for za, zb in zip(zs, zs[1:]):
                mapping = (lambda xw: (lambda v, z: node(xw, v, z)))(xweb)
                pos = (lambda xw: (lambda v, z: position(xw, v, z)))(xweb)
                conn = quad_conn(mapping, ya, yb, za, zb, False)
                tv, tz = frame(pos, ym, (za + zb) / 2, 1e-6, 1e-6)
                normal = np.cross(tv, tz)
                normal /= np.linalg.norm(normal)
                add(conn, label, [("FAB", plies * t_fab, "DIAG")], 0., j, tv, normal, [xweb, ym, (za + zb) / 2])
    # ---- kaburgalar: tank kapama kaburgası (Y_T1'e en yakın şerit sınırı) ve uç kapama kaburgası.
    # Kesit şekil bozulmasını (distorsiyon) sınırlar; 1D Bredt GJ kesitin korunduğunu varsayar.
    # Sandviç: 2 kat kumaş / 3 mm çekirdek / 2 kat kumaş (structures tank kaburgası ile aynı), OFFSET=0.
    # Ara kaburgalar: structures m_ribs = 0.08 c/cr kg/m ~ kökte 7-8 g'lık sandviç kaburga / ~0.09 m aralık
    # demektir; kaba şerit sınırlarında (her ağda aynı konum, 0.086 m aralık) hafif kaburga
    # (1 kat / 2 mm / 1 kat). Tank kapama kaburgası Y_T1'e en yakın kaba sınırda, 2 kat / 3 mm / 2 kat.
    coarse_rows = [g["factor"] * i for i in range(1, 9)]
    tank_row = min(coarse_rows, key=lambda k: abs(yf[k] - ST.Y_T1))
    zs = np.linspace(-1, 1, 2 * g["factor"] + 1)
    for k in coarse_rows:
        rib_layers = ([("FAB", 2 * t_fab, "DIAG"), ("CORE", 3e-3, "SPAN"), ("FAB", 2 * t_fab, "DIAG")]
                      if k == tank_row else [("FAB", t_fab, "DIAG"), ("CORE", t_core, "SPAN"), ("FAB", t_fab, "DIAG")])
        yr = float(yf[k])
        for xa, xb in zip(xx, xx[1:]):
            for za, zb in zip(zs, zs[1:]):
                mapping = (lambda yy: (lambda u, z: node(u, yy, z)))(yr)
                pos = (lambda yy: (lambda u, z: position(u, yy, z)))(yr)
                conn = quad_conn(mapping, xa, xb, za, zb, False)
                tu, tz = frame(pos, (xa + xb) / 2, (za + zb) / 2, 1e-6, 1e-6)
                normal = np.cross(tu, tz)
                normal /= np.linalg.norm(normal)
                add(conn, "RIB", rib_layers, 0., min(k, ny - 1), tu, normal, [(xa + xb) / 2, yr, (za + zb) / 2])
    expanded = 9 * len(nodes)
    if expanded > 200_000:
        raise Blocked("Tahmini açılmış kanat DOF >200k; ağ boyutu azaltılmalı.")
    root = [n for n, p in nodes.items() if abs(p[1] - y0) < 1e-9]
    tip = [n for n, p in nodes.items() if abs(p[1] - b2) < 1e-9]

    # ---- eleman alanları (3x3 Gauss)
    def element_area(conn):
        p = np.array([nodes[n] for n in conn])
        gp = (-math.sqrt(.6), 0., math.sqrt(.6))
        gw = (5 / 9, 8 / 9, 5 / 9)
        area = 0.
        for xi, wx in zip(gp, gw):
            for et, we in zip(gp, gw):
                d = 1e-6
                dxi = (quad8_shape(xi + d, et) - quad8_shape(xi - d, et)) @ p / (2 * d)
                det = (quad8_shape(xi, et + d) - quad8_shape(xi, et - d)) @ p / (2 * d)
                area += wx * we * np.linalg.norm(np.cross(dxi, det))
        return float(area)

    areas = {t: element_area(c) for t, c in elements.items()}
    # ---- yapısal olmayan kütle (NSM): CCX 2.20 kompozit kabuk düğümüne MASS elemanı kabul etmiyor
    # ("changekon: element type unknown: MASS"). Kütle, eleman başına iç tarafa eklenen 10 um, rijitliği
    # ihmal edilebilir (1 MPa) bir NSM tabakasıyla [kg/m^2] verilir.
    nsm = {}
    skin_elems = {t for t in elements if kinds[t].startswith("CAP") or kinds[t].startswith("SKIN")}
    tank = {}
    columns = {}
    for t in skin_elems:
        xm = center_of[t][0]
        columns.setdefault(strip_of[t], {}).setdefault(round(xm, 9), []).append(t)
        if xf <= xm <= xr:
            tank.setdefault(strip_of[t], []).append(t)

    def element_x1x2(t):
        m = areas[t] * sum(tt * mat[name]["rho"] for name, tt, _ in layers_of[t])
        return m

    strip_shell = np.zeros(ny)
    strip_x1 = np.zeros(ny)
    strip_x2 = np.zeros(ny)
    for t in elements:
        m = element_x1x2(t)
        xc = center_of[t][0]
        strip_shell[strip_of[t]] += m
        strip_x1[strip_of[t]] += m * xc
        strip_x2[strip_of[t]] += m * xc * xc
    fuel_total = 0.
    strips = []
    bays = []
    levers = []
    one_d = []
    for j, (ya, yb) in enumerate(zip(yf, yf[1:])):
        ys = np.linspace(ya, yb, 21)
        m_struct = float(np.trapezoid(np.interp(ys, ST.YS, ws["mprime"]), ys))
        xcg = float(np.trapezoid(np.interp(ys, ST.YS, ws["mprime"] * ws["xcg"]), ys)) / m_struct
        fuel = float(np.trapezoid(np.interp(ys, ST.YS, base["fuel_per_span"]), ys)) if fuel_state == "full" else 0.
        one_d.append((m_struct, xcg, fuel))
    # Kütle eşlemesi kaburga bölmesi (kaba şerit = factor ince şerit) düzeyinde: ince ağda kaburgalı
    # şeridin kabuk kütlesi 1D şerit kütlesini aşabildiğinden, bölme toplamı, CG ve atalet eşlenir;
    # kalan kütle bölme içinde 1D m' oranında dağıtılır.
    f = g["factor"]
    for bay in range(ny // f):
        js = list(range(bay * f, (bay + 1) * f))
        m1 = sum(one_d[k][0] for k in js)
        need1 = sum(one_d[k][0] * one_d[k][1] for k in js) - sum(strip_x1[k] for k in js)
        need2 = sum(one_d[k][0] * (one_d[k][1] ** 2 + 1 / 12) for k in js) - sum(strip_x2[k] for k in js)
        shell = sum(strip_shell[k] for k in js)
        residual = m1 - shell
        xA = xB = None
        mA = mB = 0.
        lever = False
        if residual > 0:
            xbar = need1 / residual
            d = math.sqrt(max(need2 / residual - xbar ** 2, 0.))
            cols = sorted(columns[js[0]])
            xA = min(cols, key=lambda v: abs(v - max(xbar - d, cols[0])))
            # Kontrol yüzeyi/firar kenarı kütlesi menteşe gerisinde: kaldıraç kütlesi (rijit kol, denklem).
            xB_target = min(xbar + d, LEVER_X_MAX)
            lever = xB_target > X_HINGE
            xB = xB_target if lever else min(cols, key=lambda v: abs(v - xB_target))
            if not (xA <= xbar <= xB) or xB <= xA:
                xA = max([v for v in cols if v <= xbar] or [cols[0]])
                if not lever:
                    xB = min([v for v in cols if v >= xbar] or [cols[-1]])
            mB = residual * (xbar - xA) / (xB - xA) if xB > xA else 0.
            mA = residual - mB
        x1m = sum(strip_x1[k] for k in js) + mA * (xA or 0) + mB * (xB or 0)
        x2m = sum(strip_x2[k] for k in js) + mA * (xA or 0) ** 2 + mB * (xB or 0) ** 2
        mm = shell + max(residual, 0.)
        t1 = sum(one_d[k][0] * one_d[k][1] for k in js)                    # 1D birinci moment (c birimi)
        t2 = sum(one_d[k][0] * (one_d[k][1] ** 2 + 1 / 12) for k in js)    # 1D ikinci moment
        i_1d = t2 - t1 ** 2 / m1
        i_model = x2m - x1m ** 2 / mm
        bay_row = dict(bay=bay, m_struct_1d=m1, m_shell=float(shell), residual=float(residual),
                       residual_cols=[xA, xB], residual_masses=[mA, mB], lever=lever,
                       xcg_1d=float(t1 / m1), xcg_model=float(x1m / mm),
                       inertia_ratio_model_to_1d=float(i_model / i_1d),
                       note=None if residual > 0 else "Kabuk kütlesi 1D bölme kütlesini aşıyor; negatif kütle eklenmedi.")
        for k in js:
            share = one_d[k][0] / m1
            ya, yb = yf[k], yf[k + 1]
            y = (ya + yb) / 2
            for xc_col, mcol, is_lever in ((xA, mA * share, False), (xB, mB * share, lever)):
                if xc_col is None or mcol <= 0:
                    continue
                if is_lever:
                    levers.append(dict(strip=k, y=y, xc=xc_col, mass=mcol))
                    continue
                es = columns[k][xc_col]
                area = sum(areas[t] for t in es)
                for t in es:
                    nsm[t] = nsm.get(t, 0.) + mcol / area
            fuel = one_d[k][2]
            if fuel > 0:
                area = sum(areas[t] for t in tank[k])
                for t in tank[k]:
                    nsm[t] = nsm.get(t, 0.) + fuel / area
                fuel_total += fuel
            strips.append(dict(strip=k, bay=bay, y=y, m_struct_1d=one_d[k][0], m_shell=float(strip_shell[k]),
                               xcg_1d=one_d[k][1], fuel=fuel))
        bays.append(bay_row)
    servo_item = next(item for item in P.MASS_ITEMS if "kanat ici" in item[0].lower())
    servo_mass = servo_item[1] / 4
    servos = []
    for y_s, xc_s in ((.34, .6), (.10, .65)):
        pair = []
        for side in (1, -1):
            t = min((t for t in skin_elems if center_of[t][2] == side),
                    key=lambda t: (center_of[t][0] - xc_s) ** 2 * float(ST.chord(y_s)) ** 2 + (center_of[t][1] - y_s) ** 2)
            nsm[t] = nsm.get(t, 0.) + servo_mass / 2 / areas[t]
            pair.append(t)
        servos.append(dict(y=y_s, xc=xc_s, mass=servo_mass, elements=pair,
                           element_centers=[center_of[t] for t in pair]))
    T_NSM = 1e-5
    nsm_materials = {}
    for t, mu in nsm.items():
        key = f"{mu:.6e}"
        if key not in nsm_materials:
            nsm_materials[key] = f"NSM{len(nsm_materials)+1}"
        layers_of[t] = [(nsm_materials[key], T_NSM, layers_of[t][0][2])] + layers_of[t]
    nsm_total = float(sum(mu * areas[t] for t, mu in nsm.items()))
    lever_total = float(sum(lv["mass"] for lv in levers))

    # ---- Schrenk nihai yükü: tutarlı düğüm kuvvetleri (üst/alt yarı yarıya)
    q_ult = ST.schrenk(P.N_LIMIT * P.SF)
    # int_{x_n}^{x_h} 3(1-x)^2 dx: burun (x<.01) ve menteşe gerisi payı sabit yapıya yeniden dağıtılır,
    # toplam şerit kaldırması korunur.
    g_total = (1 - X_NOSE) ** 3 - (1 - X_HINGE) ** 3
    gp, gw = (-math.sqrt(.6), 0., math.sqrt(.6)), (5 / 9, 8 / 9, 5 / 9)
    loads = {}
    for t, conn in elements.items():
        if not (kinds[t].startswith("CAP") or kinds[t].startswith("SKIN")):
            continue
        p = np.array([nodes[n] for n in conn])
        for xi, wx in zip(gp, gw):
            for et, we in zip(gp, gw):
                nvec = quad8_shape(xi, et)
                d = 1e-6
                dxi = (quad8_shape(xi + d, et) - quad8_shape(xi - d, et)) @ p / (2 * d)
                det = (quad8_shape(xi, et + d) - quad8_shape(xi, et - d)) @ p / (2 * d)
                planform = abs(dxi[0] * det[1] - dxi[1] * det[0])      # dX dY
                X = nvec @ p
                yq = X[1]
                cq = float(ST.chord(yq))
                xcq = (X[0] - P.WING["x_root_le"] - sweep * yq) / cq
                pz = .5 * float(np.interp(yq, ST.YS, q_ult)) / cq * chord_load_shape(xcq) / g_total
                for k, n in enumerate(conn):
                    loads[n] = loads.get(n, 0.) + wx * we * planform * pz * nvec[k]
    ys_fine = np.linspace(y0, b2, 4001)
    lift_target = float(np.trapezoid(np.interp(ys_fine, ST.YS, q_ult), ys_fine))
    moment_target = float(np.trapezoid(np.interp(ys_fine, ST.YS, q_ult) * (ys_fine - y0), ys_fine))

    # ---- deck
    data = ["*HEADING", f"HIZ750 iter5 S8R composite half wing, level {args.level}, fuel {fuel_state}. SI; "
            "assumed orthotropic constants (fem/README.md).", "*NODE, NSET=NALL"]
    data += [f"{n}, {p[0]:.10e}, {p[1]:.10e}, {p[2]:.10e}" for n, p in nodes.items()]
    data += ["*ELEMENT, TYPE=S8R, ELSET=EALL"]
    data += [f"{n}, " + ", ".join(map(str, conn)) for n, conn in elements.items()]
    data += ["*NSET, NSET=ROOT"] + set_lines(root) + ["*NSET, NSET=TIP"] + set_lines(tip)
    for label in sorted(set(kinds.values())):
        data += [f"*ELSET, ELSET={label}"] + set_lines([t for t, k in kinds.items() if k == label])
    data += material_cards({k: v for k, v in mat.items()})
    for key, name in nsm_materials.items():
        data += [f"*MATERIAL, NAME={name}", "*ELASTIC", "1e6, 0.", "*DENSITY", f"{float(key) / T_NSM:.6e}"]
    for key, name in orientations.items():
        data += [f"*ORIENTATION, NAME={name}", ", ".join(f"{v:.6f}" for v in key)]
    grouped = {}
    for tag, layers in layers_of.items():
        grouped.setdefault((tuple(layers), offset_of[tag]), []).append(tag)
    section_list = []
    for i, ((layers, offset), tags) in enumerate(grouped.items()):
        data += [f"*ELSET, ELSET=SEC{i}"] + set_lines(tags)
        data += [f"*SHELL SECTION, ELSET=SEC{i}, COMPOSITE, OFFSET={offset}"]
        data += [f"{t:.10e}, , {name}, {o}" for name, t, o in layers]
        section_list.append(i)
    # Kaldıraç kütleleri: CCX 2.20 kompozit kabuklu modelde MASS elemanı kabul etmiyor; 2 mm C3D8 küp
    # (yoğunluk = m/V, rijitliği yok sayılır), 8 düğümün her biri *EQUATION ile şerit ortasındaki menteşe
    # ve arka kiriş düğümlerine bağlı: u,v = menteşe ortalaması; w = w_h + lambda (w_h - w_r),
    # lambda = (x - x_h)/(x_h - x_r). Böylece kütle rijit kol üzerinde ve kanada rijitlik katmaz.
    next_node, next_el = max(nodes) + 1, len(elements) + 1
    lever_eqs = []
    for i, lv in enumerate(levers):
        ym = lv["y"]
        hu, hl = (lookup[tuple(round(float(v), 10) for v in position(X_HINGE, ym, e))] for e in (1, -1))
        ru, rl = (lookup[tuple(round(float(v), 10) for v in position(xr, ym, e))] for e in (1, -1))
        lam = (lv["xc"] - X_HINGE) / (X_HINGE - xr)
        centre = position(lv["xc"], ym, 0.)
        ids = []
        for dz in (-1, 1):
            for dy, dx in ((-1, -1), (-1, 1), (1, 1), (1, -1)):
                p = centre + 1e-3 * np.array([dx, dy, dz])
                data_nodes = f"{next_node}, {p[0]:.10e}, {p[1]:.10e}, {p[2]:.10e}"
                lever_eqs.append(("NODE", data_nodes))
                ids.append(next_node)
                next_node += 1
        lv.update(element=next_el, nodes=ids, hinge_nodes=[hu, hl], spar_nodes=[ru, rl], lam=lam)
        for n in ids:
            for dof in (1, 2):
                lever_eqs.append(("EQ", [(n, dof, 1.), (hu, dof, -.5), (hl, dof, -.5)]))
            lever_eqs.append(("EQ", [(n, 3, 1.), (hu, 3, -(1 + lam) / 2), (hl, 3, -(1 + lam) / 2),
                                     (ru, 3, lam / 2), (rl, 3, lam / 2)]))
        next_el += 1
    if levers:
        data += ["*NODE, NSET=LEVERNODES"] + [txt for kind, txt in lever_eqs if kind == "NODE"]
        for lv in levers:
            name = f"LEV{lv['element']}"
            data += [f"*ELEMENT, TYPE=C3D8, ELSET={name}", f"{lv['element']}, " + ", ".join(map(str, lv["nodes"])),
                     f"*MATERIAL, NAME={name}", "*ELASTIC", "1e3, 0.", "*DENSITY", f"{lv['mass'] / 8e-9:.8e}",
                     f"*SOLID SECTION, ELSET={name}, MATERIAL={name}"]
        for kind, terms in lever_eqs:
            if kind != "EQ":
                continue
            flat = [f"{a}, {b}, {c:.12e}" for a, b, c in terms]
            data += ["*EQUATION", str(len(terms))] + [", ".join(flat[k:k + 4]) for k in range(0, len(flat), 4)]
    # Kök: tüm düğümlerde öteleme 1-3; CCX bunu genişletilmiş (alt/orta/üst) düğümlerin hepsine uygular,
    # kesit dönemez -> ankastre. 1-6 kullanıldığında CCX düğüm başına rijit "knot" üretti ve ROOT RF
    # toplamı uygulanan yükün %17'sini kaybetti (knot referans düğümleri sette değil); 1-3 ile denge kesin.
    data += ["*BOUNDARY", "ROOT, 1, 3", "*STEP", "*STATIC, SOLVER=SPOOLES", "*CLOAD"]
    data += [f"{n}, 3, {f:.10e}" for n, f in loads.items() if f != 0.]
    data += ["*NODE PRINT, NSET=NALL", "U", "*NODE PRINT, NSET=ROOT, TOTALS=ONLY", "RF",
             "*EL PRINT, ELSET=EALL, GLOBAL=NO", "S",
             "*NODE FILE", "U", "*EL FILE", "S", "*END STEP",
             "*STEP", f"*FREQUENCY, SOLVER=SPOOLES", str(N_MODES),
             "*NODE PRINT, NSET=NALL", "U", "*NODE FILE", "U", "*END STEP"]
    (work / "case.inp").write_text("\n".join(data) + "\n", encoding="ascii")
    gmsh.initialize()
    try:
        gmsh.model.add("wing_shell")
        gmsh.model.addDiscreteEntity(2, 1)
        gmsh.model.mesh.addNodes(2, 1, list(nodes), [v for p in nodes.values() for v in p])
        gmsh.model.mesh.addElementsByType(1, 16, list(elements), [n for conn in elements.values() for n in conn])
        gmsh.write(str(work / "mesh.msh"))
    finally:
        gmsh.finalize()
    shell_mass = float(sum(strip_shell))
    pm_total = nsm_total + lever_total
    target_mass = float(sum(r["m_struct_1d"] for r in strips)) + fuel_total + 2 * servo_mass
    mesh = dict(level=args.level, ny=ny, cells=len(elements), nodes=len(nodes), h=1 / ny,
                expanded_dof_estimate=expanded, orientations=len(orientations), sections=len(grouped),
                nsm_materials=len(nsm_materials), nsm_mass_kg=nsm_total, lever_mass_kg=lever_total,
                levers=len(levers), shell_mass_kg=shell_mass,
                total_half_mass_kg=shell_mass + pm_total, target_half_mass_kg=target_mass,
                relative_mass_difference=(shell_mass + pm_total) / target_mass - 1,
                fuel_kg=fuel_total, fuel_state=fuel_state, ultimate_force_N=float(sum(loads.values())),
                ultimate_force_target_N=lift_target, root_moment_target_Nm=moment_target,
                mesh_sha256=digest(work / "mesh.msh"), deck_sha256=digest(work / "case.inp"),
                element="S8R_COMPOSITE")
    model = dict(mesh=mesh, materials=mat, geometry=dict(knots=g["knots"], x_hinge=X_HINGE, xf=xf, xr=xr,
                 cap_half_xc=cap_half, y_root=y0, b2=b2, sweep_le_deg=P.WING["sweep_le"],
                 dihedral_deg=P.WING["dihedral"], x_root_le=P.WING["x_root_le"], z_root=P.WING["z_root"]),
                 strips=strips, bays=bays, servos=servos, levers=levers, n_modes=N_MODES,
                 sandwich_summary=dict(elements_core=sum(1 for r in sandwich_report if r["core"]),
                                       elements_monolithic=sum(1 for r in sandwich_report if not r["core"]),
                                       min_gap_m=min(r["gap"] for r in sandwich_report)),
                 assumptions="Görevde verilen tipik değerler; üretici/sıcak-nem verisi bekleniyor",
                 limitations=["ST.yt64 yaklaşık kesiti; gerçek profil, kaburgalar, cıvata esnekliği yok.",
                              "x/c>.75 kontrol yüzeyi/firar kenarı yalnız kütle; menteşe web'i 2 kat varsayımı.",
                              "Web'ler OML'den OML'ye; kabuk kalınlığıyla küçük örtüşme (web yüksekliği fazla).",
                              "Statikte atalet rahatlatması yok; konservatif 18g Schrenk kaldırması.",
                              "Kabuk genişlemesi sandviç çekirdek kaymasını (zigzag) temsil etmez (kupon notu)."])
    write_json(work / "wing_model.json", model)
    write_json(work / "wing_nodes.json", dict(nodes=nodes, kinds=kinds, strips=strip_of, layers={
        t: [[m, tt] for m, tt, _ in v] for t, v in layers_of.items()}, orient=orient_of, center=center_of,
        root=root, tip=tip, loads=loads, nsm_kg_m2=nsm, areas=areas))
    return {}, mesh


def _eta(point, xc, P, ST, sweep, dihedral):
    """Düğümün profil yarı kalınlığına göre konumu (+1 üst, -1 alt)."""
    y = point[1]
    c = float(ST.chord(y))
    half = float(ST.yt64(xc, ST.tc(y))) * c
    if half <= 0:
        return 0.
    return (point[2] - P.WING["z_root"] - dihedral * y) / half
