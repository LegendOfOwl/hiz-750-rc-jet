"""Parametrik S8R kanat ön modeli: ST kesit geometrisi, kapaklar, web, sandviç.

İmalat detaylı CAD FEM değildir. İlk host koşusunda mod/bağlantı/normal kontrolü gerekir.
"""
import math

from validation.common import Blocked, digest, require_module, write_json


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
                  nu12=.3, nu13=.3, nu23=.3, rho=core["rho"]))
    for name in ("UD", "FAB"):
        m = result[name]
        m["F12"] = -.5 / math.sqrt(m["Xt"] * m["Xc"] * m["Yt"] * m["Yc"])
    return result


def material_cards(mats):
    cards = []
    for name, m in mats.items():
        cards += [f"*MATERIAL, NAME={name}", "*ELASTIC, TYPE=ENGINEERING CONSTANTS",
                  ", ".join(str(m[k]) for k in ("E1", "E2", "E3", "nu12", "nu13", "nu23", "G12", "G13")),
                  str(m["G23"]), "*DENSITY", str(m["rho"])]
    return cards


def prepare(args, work):
    require_module("gmsh")
    require_module("numpy")
    import gmsh
    import numpy as np
    import params as P
    from structures import structures as ST
    from fem.cases import set_lines
    base = ST.wing_section_model()
    ws, mat = base["ws"], materials()
    factor = 2 ** ("coarse", "medium", "fine").index(args.level)
    ny = 8 * factor
    y0, b2 = .035, ST.B2
    yf = np.linspace(y0, b2, ny+1)
    xf, xr = P.WING["spar_xc"]
    cap_half = .025 / P.wing_geom()["cr"]
    knots = sorted({.005, .05, xf-cap_half, xf, xf+cap_half, .25, .375,
                    xr-cap_half, xr, xr+cap_half, .75, 1.})
    xx = sorted({a + (b-a)*i/factor for a, b in zip(knots, knots[1:]) for i in range(factor+1)})
    nodes, lookup, elements, sections, strip_mass = {}, {}, {}, {}, [0.]*ny
    sweep = math.tan(math.radians(P.WING["sweep_le"]))
    dihedral = math.tan(math.radians(P.WING["dihedral"]))

    def node(xc, y, eta):
        c = float(ST.chord(y))
        point = (P.WING["x_root_le"]+sweep*y+xc*c, y,
                 P.WING["z_root"]+dihedral*y+eta*float(ST.yt64(xc, ST.tc(y)))*c)
        key = tuple(round(v, 11) for v in point)
        if key not in lookup:
            lookup[key] = len(nodes)+1
            nodes[lookup[key]] = point
        return lookup[key]

    def area(conn):
        p = [np.asarray(nodes[n]) for n in conn[:4]]
        return float((np.linalg.norm(np.cross(p[1]-p[0], p[2]-p[0]))
                      + np.linalg.norm(np.cross(p[2]-p[0], p[3]-p[0])))/2)

    def quad(mapping, u0, u1, v0, v1, layers, strip, reverse=False):
        uv = ((u0,v0), (u1,v0), (u1,v1), (u0,v1), ((u0+u1)/2,v0),
              (u1,(v0+v1)/2), ((u0+u1)/2,v1), (u0,(v0+v1)/2))
        conn = [mapping(u,v) for u,v in uv]
        if reverse:
            conn = [conn[i] for i in (0,3,2,1,7,6,5,4)]
        tag = len(elements)+1
        elements[tag] = conn
        sections[tag] = layers
        strip_mass[strip] += area(conn) * sum(t*mat[name]["rho"] for name,t,_ in layers)

    for j, (ya,yb) in enumerate(zip(yf, yf[1:])):
        ym = (ya+yb)/2
        nud = int(round(float(np.interp(ym, ST.YS, ws["n_ud"]))))
        nw = int(round(float(np.interp(ym, ST.YS, ws["n_web"]))))
        for xa, xb in zip(xx, xx[1:]):
            xm = (xa+xb)/2
            nf = P.WING["skin_plies"][0 if xm <= xr else 1]
            layers = []
            if min(abs(xm-xf), abs(xm-xr)) < cap_half:
                layers += [("UD", nud*ST.MAT["UD"]["t_ply"], "SPAN")]
            layers += [("FAB", nf*ST.MAT["FAB"]["t_ply"], "DIAG"),
                       ("CORE", ST.MAT["CORE"]["t"], "SPAN"),
                       ("FAB", nf*ST.MAT["FAB"]["t_ply"], "DIAG")]
            for side in (1, -1):
                quad(lambda x,y: node(x,y,side), xa,xb,ya,yb,layers,j,side < 0)
        for xweb in (.005, xf, xr):
            for za, zb in zip(np.linspace(-1,1,2*factor+1), np.linspace(-1,1,2*factor+1)[1:]):
                quad(lambda y,z: node(xweb,y,z), ya,yb,za,zb,
                     [("FAB", nw*ST.MAT["FAB"]["t_ply"], "SPAN")], j)
    # Bu tahmin shell 3B açılımı için yaklaşık 3 translasyon x 3 kat düğüm sayısıdır.
    if 9*len(nodes) > 200_000:
        raise Blocked("Tahmini açılmış kanat DOF >200k; ağ boyutu azaltılmalı.")
    root = [n for n,p in nodes.items() if abs(p[1]-y0) < 1e-9]
    tip = [n for n,p in nodes.items() if abs(p[1]-b2) < 1e-9]

    def attach(xc, y):
        # Üst/alt iki mevcut düğüme eşit dağıtılır: net z CG yaklaşık orta düzlemde.
        return [
            min(nodes, key=lambda n: ((nodes[n][0]-(P.WING['x_root_le']+sweep*y+xc*float(ST.chord(y))))**2
                                     +(nodes[n][1]-y)**2
                                     +(nodes[n][2]-(P.WING['z_root']+dihedral*y+side*float(ST.yt64(xc,ST.tc(y)))*float(ST.chord(y))))**2))
            for side in (1,-1)]

    point_masses, loads = {}, {}
    target_mass = 0.
    for j, (ya,yb) in enumerate(zip(yf,yf[1:])):
        y, dy = (ya+yb)/2, yb-ya
        structural = float(np.interp(y, ST.YS, ws["mprime"])) * dy
        fuel = float(np.interp(y, ST.YS, base["fuel_per_span"])) * dy
        target_mass += structural + fuel
        # Pozitif fark: kaburga/boya/donanım gibi 1D modeldeki yapısal olmayan rijitlik katkısız kütle.
        residual = max(0., structural-strip_mass[j])
        for n in attach(.375,y):
            point_masses[n] = point_masses.get(n,0.) + (residual+fuel)/2
        force = float(np.interp(y, ST.YS, ST.schrenk(P.N_LIMIT*P.SF))) * dy
        for n in attach(.25,y):
            loads[n] = loads.get(n,0.) + force/2
    servo_item = next(item for item in P.MASS_ITEMS if "kanat ici" in item[0].lower())
    for y, xc in ((.34,.6),(.10,.65)):
        for n in attach(xc,y):
            point_masses[n] = point_masses.get(n,0.) + servo_item[1]/8
        target_mass += servo_item[1]/4
    data = ["*HEADING", "HIZ750 iter5 provisional shell wing. SI; assumed orthotropic constants.", "*NODE, NSET=NALL"]
    data += [f"{n}, {p[0]:.10e}, {p[1]:.10e}, {p[2]:.10e}" for n,p in nodes.items()]
    data += ["*ELEMENT, TYPE=S8R, ELSET=EALL"]
    data += [f"{n}, " + ", ".join(map(str,conn)) for n,conn in elements.items()]
    data += ["*NSET, NSET=ROOT"] + set_lines(root) + ["*NSET, NSET=TIP"] + set_lines(tip)
    data += material_cards(mat)
    # Span yönü local-1; DIAG dokuma iki fiber ailesi span'a ±45°.
    span = np.array([sweep,1.,dihedral]); span /= np.linalg.norm(span)
    chord = np.array([1.,0.,0.]); chord -= np.dot(chord,span)*span; chord /= np.linalg.norm(chord)
    for name, a, b in (("SPAN",span,chord),("DIAG",(span+chord)/math.sqrt(2),(chord-span)/math.sqrt(2))):
        data += [f"*ORIENTATION, NAME={name}", ", ".join(map(str, [*a,*b]))]
    grouped = {}
    for tag,layers in sections.items():
        grouped.setdefault(tuple(layers),[]).append(tag)
    for i, (layers,tags) in enumerate(grouped.items()):
        data += [f"*ELSET, ELSET=SEC{i}"] + set_lines(tags)
        data += [f"*SHELL SECTION, ELSET=SEC{i}, COMPOSITE, OFFSET=0.5"]
        data += [f"{t:.10e}, , {name}, {orientation}" for name,t,orientation in layers]
    for i,(n,mass) in enumerate(point_masses.items(),start=len(elements)+1):
        data += [f"*ELEMENT, TYPE=MASS, ELSET=M{i}", f"{i}, {n}", f"*MASS, ELSET=M{i}", f"{mass:.10e}"]
    data += ["*BOUNDARY", "ROOT, 1, 6", "*STEP", "*STATIC", "*CLOAD"]
    data += [f"{n}, 3, {force:.10e}" for n,force in loads.items()]
    data += ["*NODE PRINT, NSET=TIP", "U", "*NODE PRINT, NSET=ROOT", "RF", "*EL PRINT, ELSET=EALL, GLOBAL=NO", "S",
             "*NODE FILE", "U", "*EL FILE", "S", "*END STEP", "*STEP", "*FREQUENCY", "8",
             "*NODE PRINT, NSET=NALL", "U", "*NODE FILE", "U", "*END STEP"]
    (work/"case.inp").write_text("\n".join(data)+"\n",encoding="ascii")
    gmsh.initialize()
    try:
        gmsh.model.add("wing_shell")
        gmsh.model.addDiscreteEntity(2,1)
        gmsh.model.mesh.addNodes(2,1,list(nodes),[v for p in nodes.values() for v in p])
        gmsh.model.mesh.addElementsByType(1,16,list(elements),[n for conn in elements.values() for n in conn])
        gmsh.write(str(work/"mesh.msh"))
    finally:
        gmsh.finalize()
    mass = sum(strip_mass)+sum(point_masses.values())
    mesh = dict(cells=len(elements), nodes=len(nodes), h=1/math.sqrt(len(elements)), expanded_dof_estimate=9*len(nodes),
                shell_mass_kg=sum(strip_mass), total_half_mass_kg=mass, target_half_mass_kg=target_mass,
                relative_mass_difference=mass/target_mass-1, ultimate_force_N=sum(loads.values()),
                mesh_sha256=digest(work/"mesh.msh"), element="S8R_COMPOSITE")
    write_json(work/"wing_model.json", dict(mesh=mesh, nodes=nodes, materials=mat,
                 sections={str(k):v for k,v in sections.items()}, assumptions="Task-supplied typical values; manufacturer/hot-wet data pending",
                 limitations=["ST.yt64 yaklaşık kesiti; gerçek profil, mafsal kesikleri, rib ve cıvata esnekliği yok.",
                              "Burun .005c düz web ile kapatıldı; bütün arka kabuk bağlı. Kontrol yüzeyi kesikleri eklenmeli.",
                              "Statikte kütle ataleti rahatlatması yok; konservatif 18g Schrenk kaldırması.",
                              "Yakıt ve servo nodal kütleleri yaklaşık; 1T için kütle dağılımı kontrol edilmeli."]))
    return {}, mesh
