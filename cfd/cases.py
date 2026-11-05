"""SU2 sıkıştırılabilir SA/SST: 2B üretim ve denetlenmiş 3B mesh girişi.

Bu dosyada bir SU2 çözümü veya ağ kalitesi doğrulanmış kabul edilmez.
"""
import csv
import math
from pathlib import Path
import shutil

from validation.common import Blocked, ROOT, digest, read_json, require_module, run_solver, write_json


def isa(height=300):
    t = 288.15 - 0.0065 * height
    p = 101325 * (1 - 0.0065 * height / 288.15) ** 5.2559
    rho = p / (287.05 * t)
    mu = 1.458e-6 * t ** 1.5 / (t + 110.4)
    return dict(temperature=t, pressure=p, density=rho,
                sound_speed=math.sqrt(1.4 * 287.05 * t), viscosity=mu)


def coordinates(args):
    if args.case == "rae2822":
        path = Path(args.airfoil or ROOT / "validation/reference/rae2822.dat")
        if not path.is_file():
            raise Blocked("RAE2822 koordinatı yok; validation/fetch_reference.py --geometry çalıştırın.")
        points = []
        for line in path.read_text().splitlines():
            try:
                x, y = map(float, line.split())
                if -0.001 <= x <= 1.001 and abs(y) < 0.5:
                    points.append((x, y))
            except ValueError:
                continue
        if len(points) < 30:
            raise Blocked("RAE2822 DAT dosyası Selig TE-upper/LE/TE-lower sıralamasında olmalı.")
        if points[0][0] < .001 and points[-1][0] > .99:
            split = next((i for i in range(10,len(points)) if points[i][0] < .001),None)
            if split is None:
                raise Blocked("Lednicer profilinin ikinci LE noktası bulunamadı.")
            points = list(reversed(points[:split])) + points[split+1:]
        return points, {str(path): digest(path)}
    require_module("aerosandbox")
    import aerosandbox as asb
    import params as P
    # aero/aero_analysis.py:airfoil_64a ile aynı koordinat tanımı; yan etkili modül import edilmez.
    af = asb.Airfoil("naca64a010")
    af = af.scale(scale_x=1.0, scale_y=P.WING["tc_root"] / af.max_thickness())
    return [tuple(map(float, row)) for row in af.coordinates], {"geometry": "aero airfoil_64a: scaled naca64a010"}


def mesh_2d(args, work):
    require_module("gmsh")
    if args.case != "flat_plate":
        from cfd.structured_airfoil import generate
        xy, source = coordinates(args)
        return generate(args, work, xy, source)
    import gmsh
    factor = (1, 1.5, 2)[("coarse", "medium", "fine").index(args.level)]
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.NumThreads", args.threads)
        gmsh.model.add(args.case)
        geo = gmsh.model.geo
        wall, far, sym = [], [], []
        first = 2e-6 / factor
        if args.case == "flat_plate":
            # TMR benzeri M=.2, Re_x=5e6 @ x=1; üst sınır y=1, plaka x=0..2.
            xy = [(-1/3, 0), (0, 0), (2, 0), (2, 1), (0, 1), (-1/3, 1)]
            pts = [geo.addPoint(x, y, 0, .08 / factor) for x, y in xy]
            lines = [geo.addLine(pts[i], pts[(i + 1) % 6]) for i in range(6)]
            shared = geo.addLine(pts[1],pts[4])
            wall, sym, far = [lines[1]], [lines[0]], lines[2:]
            faces = [geo.addPlaneSurface([geo.addCurveLoop([lines[0],shared,lines[4],lines[5]])]),
                     geo.addPlaneSurface([geo.addCurveLoop([lines[1],lines[2],lines[3],-shared])])]
            ny = int(96*factor)
            lo,hi = 1.000001,2.
            for _ in range(80):
                r=(lo+hi)/2
                if (r-1)/(r**ny-1) > first: lo=r
                else: hi=r
            ratio=(lo+hi)/2
            for curve in (lines[2],shared): geo.mesh.setTransfiniteCurve(curve,ny+1,"Progression",ratio)
            geo.mesh.setTransfiniteCurve(lines[5],ny+1,"Progression",1/ratio)
            # Cluster both streamwise blocks at the plate leading edge,
            # like SU2's official 137x97 tensor grid (24+112 by 96).
            geo.mesh.setTransfiniteCurve(lines[0],int(24*factor)+1,"Progression",1/1.13**(1/factor))
            geo.mesh.setTransfiniteCurve(lines[4],int(24*factor)+1,"Progression",1.13**(1/factor))
            geo.mesh.setTransfiniteCurve(lines[1],int(112*factor)+1,"Progression",1.025**(1/factor))
            geo.mesh.setTransfiniteCurve(lines[3],int(112*factor)+1,"Progression",1/1.025**(1/factor))
            for face in faces:
                geo.mesh.setTransfiniteSurface(face)
                geo.mesh.setRecombine(2,face)
            surface=faces[0]
            source = {"geometry": "2D flat plate x=0..2 m"}
        geo.synchronize()
        boundary_groups = [("WALL",wall),("FARFIELD",far),("SYMMETRY",sym)]
        if args.case=="flat_plate":
            boundary_groups=[("WALL",wall),("SYMMETRY",sym),("INLET",[lines[5]]),
                             ("OUTLET",[lines[2]]),("FARFIELD",[lines[3],lines[4]])]
        for name, tags in boundary_groups:
            if tags:
                gmsh.model.addPhysicalGroup(1, tags, name=name)
        gmsh.model.addPhysicalGroup(2, faces if args.case=="flat_plate" else [surface], name="FLUID")
        gmsh.option.setNumber("Mesh.Algorithm", 6)
        gmsh.model.mesh.generate(2)
        gmsh.write(str(work / "mesh.su2"))
        gmsh.write(str(work / "mesh.msh"))
        types, tags, _ = gmsh.model.mesh.getElements(2)
        count = sum(len(t) for t in tags)
        qualities = gmsh.model.mesh.getElementQualities([int(e) for a in tags for e in a], "minSICN")
        if min(qualities) <= 0:
            raise Blocked("Sıfır/negatif ağ kalitesi; mesh düzeltilmeli.")
        # H, tüm sınır-ağ boyutlarıyla birlikte azalır; h=N^(-1/d) ayrıca kaydedilir.
        info = dict(cells=count, dimension=2, h=1 / math.sqrt(count),
                    first_layer_m=first, minimum_scaled_jacobian=float(min(qualities)),
                    source=source, mesh_sha256=digest(work / "mesh.su2"),
                    yplus_status="Çözüm sonrası gerçek y+ kontrolü zorunlu")
        write_json(work / "mesh.json", info)
        return info
    finally:
        gmsh.finalize()


def csv_rows(path):
    with Path(path).open(encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream, skipinitialspace=True)
        rows = [{k.strip().strip('"'): float(v) for k, v in row.items()} for row in reader]
    # SU2 8.2 steady RANS Buffet yardımcı sütununu NaN yazabiliyor.
    # İstenen fiziksel alanların sonluluğu pick()/residual denetiminde zorunludur.
    return rows


def pick(row, *names):
    def normalize(s):
        return "".join(c.lower() for c in s if c.isalnum())
    for name in names:
        for k, value in row.items():
            if normalize(k) == normalize(name):
                if not math.isfinite(value):
                    raise Blocked(f"Solver fiziksel alanı sonlu değil: {k}")
                return value
    raise Blocked(f"Solver CSV alanı eksik: {names}; mevcut: {tuple(row)}")


def reviewed_mesh(args, work):
    if not args.mesh or not args.mesh_review:
        raise Blocked("3B çözüm için --mesh ve --mesh-review gerekli; cfd/README.md ağ kabul adımlarına bakın.")
    review = read_json(args.mesh_review)
    if review.get("level") != args.level:
        raise Blocked("Mesh inceleme dosyası istenen ağ seviyesine ait değil.")
    if review.get("mesh_sha256") != digest(args.mesh):
        raise Blocked("Ağ inceleme kaydı SHA256 ile eşleşmiyor.")
    header, markers = {}, set()
    with Path(args.mesh).open() as stream:
        for line in stream:
            if "=" in line:
                key,value = [s.strip() for s in line.split("=",1)]
                if key in ("NDIME","NELEM"):
                    header[key] = int(value.split()[0])
                elif key == "MARKER_TAG":
                    markers.add(value)
    expected = {"WALL","FARFIELD","SYMMETRY"} if args.case == "aircraft" else {"WALL","FARFIELD","ENGINE"}
    if header.get("NDIME") != 3 or header.get("NELEM") != review.get("cells") or markers != expected:
        raise Blocked("SU2 mesh boyutu/hücre sayısı/marker listesi inceleme kaydı veya vaka ile uyuşmuyor.")
    required = ("closed_fluid_volume", "units_m", "boundary_layers", "positive_volumes", "markers_checked")
    if not all(review.get(k) is True for k in required):
        raise Blocked("3B ağ kabul kaydı eksik: " + ", ".join(required))
    if not 0 < review.get("cells", 0) <= 2_000_000:
        raise Blocked("3B CPU bütçesi: 1..2M hücre gerekli.")
    if args.case == "inlet" and not review.get("ingested_boundary_layer"):
        raise Blocked("η_r karşılaştırması için dorsal sınır tabaka yutulması modellenmeli.")
    shutil.copy2(args.mesh, work / "mesh.su2")
    review["dimension"] = 3
    review["h"] = review["cells"] ** (-1 / 3)
    return review


def configuration(args):
    import params as P
    atmo = isa()
    if args.case == "rae2822":
        mach, re, alpha, temp, length, area = .729, 6.5e6, 2.31, 288.15, 1.0, 1.0
    elif args.case == "flat_plate":
        mach, re, alpha, temp, length, area = .2, 5e6, 0.0, 300.0, 1.0, 2.0
    elif args.case == "airfoil":
        mach, re, alpha, temp, length, area = args.mach, 4.5e6, args.alpha, atmo["temperature"], 1.0, 1.0
    else:
        mach = P.V_TARGET / atmo["sound_speed"]
        length = P.FUSELAGE["length"]
        re = atmo["density"] * P.V_TARGET * length / atmo["viscosity"]
        alpha, temp, area = args.alpha, atmo["temperature"], P.WING["S"] / 2
    lines = ["SOLVER= RANS", f"KIND_TURB_MODEL= {args.model}", "MATH_PROBLEM= DIRECT", "RESTART_SOL= NO",
             f"MACH_NUMBER= {mach}", f"AOA= {alpha}", f"REYNOLDS_NUMBER= {re}",
             f"REYNOLDS_LENGTH= {length}", f"FREESTREAM_TEMPERATURE= {temp}",
             "FREESTREAM_TURBULENCEINTENSITY= 0.001", "FREESTREAM_TURB2LAMVISCRATIO= 100.0",
             f"REF_AREA= {area}", f"REF_LENGTH= {length}",
             f"REF_ORIGIN_MOMENT_X= {.25 if args.case in ('rae2822', 'airfoil') else 0}",
             "REF_ORIGIN_MOMENT_Y= 0", "REF_ORIGIN_MOMENT_Z= 0",
             "MARKER_HEATFLUX= ( WALL, 0.0 )", "MARKER_FAR= ( FARFIELD )",
             "MARKER_MONITORING= ( WALL )", "MARKER_PLOTTING= ( WALL )",
             "NUM_METHOD_GRAD= WEIGHTED_LEAST_SQUARES", "CONV_NUM_METHOD_FLOW= ROE",
             "MUSCL_FLOW= YES", "SLOPE_LIMITER_FLOW= VENKATAKRISHNAN",
             "CONV_NUM_METHOD_TURB= SCALAR_UPWIND", "MUSCL_TURB= YES",
             "TIME_DISCRE_FLOW= EULER_IMPLICIT", "TIME_DISCRE_TURB= EULER_IMPLICIT",
             "CFL_NUMBER= 10.0", "CFL_ADAPT= NO", "MGLEVEL= 0",
             "LINEAR_SOLVER= FGMRES", "LINEAR_SOLVER_PREC= ILU", "LINEAR_SOLVER_ITER= 10",
             "LINEAR_SOLVER_ERROR= 1E-6", f"ITER= {args.iterations}",
             "CONV_FIELD= DRAG", "CONV_CAUCHY_ELEMS= 100", "CONV_CAUCHY_EPS= 1e-6",
             "CONV_RESIDUAL_MINVAL= -8", "CONV_STARTITER= 100",
             "MESH_FILENAME= mesh.su2", "MESH_FORMAT= SU2", "TABULAR_FORMAT= CSV",
             "CONV_FILENAME= history", "SURFACE_FILENAME= surface_flow", "VOLUME_FILENAME= flow",
             "OUTPUT_FILES= ( RESTART, SURFACE_CSV, PARAVIEW )", "OUTPUT_WRT_FREQ= 1000",
             "WRT_RESTART_COMPACT= NO",
             "HISTORY_OUTPUT= ( ITER, RMS_RES, AERO_COEFF )",
             "VOLUME_OUTPUT= ( COORDINATES, SOLUTION, PRIMITIVE )", "OUTPUT_PRECISION= 12"]
    if args.case in ("flat_plate", "aircraft"):
        lines.append("MARKER_SYM= ( SYMMETRY )")
    if args.case=="flat_plate":
        # Resmi SU2 v8.2 TestCases/rans/flatplate/turb_SA_flatplate.cfg:
        # üst sınır statik basınç, sol sınır total conditions; farfield Riemann değil.
        lines.remove("MARKER_FAR= ( FARFIELD )")
        lines += ["MARKER_INLET= ( INLET, 302.4, 118309.784, 1.0, 0.0, 0.0 )",
                  "MARKER_OUTLET= ( OUTLET, 115056.0, FARFIELD, 115056.0 )"]
        for old,new in (("NUM_METHOD_GRAD= WEIGHTED_LEAST_SQUARES","NUM_METHOD_GRAD= GREEN_GAUSS"),
                        ("MUSCL_TURB= YES","MUSCL_TURB= NO"),
                        ("SLOPE_LIMITER_FLOW= VENKATAKRISHNAN","SLOPE_LIMITER_FLOW= NONE"),
                        # Iter5 devam: ayni ince ag MG3 + CFL 10 ile 1155. iterasyonda
                        # iraksadi; MG0 + CFL_ADAPT ile 3082. iterasyonda yakinsadi
                        # (C:/hz750run/pilot_mg0_flat_plate/solver.log). MGLEVEL= 0 kalir.
                        ("CFL_NUMBER= 10.0","CFL_NUMBER= 1.0"),
                        ("CFL_ADAPT= NO","CFL_ADAPT= YES"),
                        # Iter5 v2: SU2 DRAG-Cauchy 1e-6 ince MG0 pilotunu proje kapisindan
                        # once durdurdu (proje Cauchy100 3.4e-5, nu dususu 3.12). SU2 artik
                        # nu_tilde residual'i (mutlak -9.3; baslangic ~-5 -> >=4 mertebe) VE
                        # 1e-8 DRAG-Cauchy birlikte saglanana kadar kosar.
                        ("CONV_FIELD= DRAG","CONV_FIELD= ( RMS_NU_TILDE, DRAG )"),
                        ("CONV_CAUCHY_EPS= 1e-6","CONV_CAUCHY_EPS= 1e-8"),
                        ("CONV_RESIDUAL_MINVAL= -8","CONV_RESIDUAL_MINVAL= -9.3")):
            lines[lines.index(old)]=new
        lines.insert(lines.index("CFL_ADAPT= YES")+1,"CFL_ADAPT_PARAM= ( 0.5, 1.5, 1.0, 100.0 )")
        lines += ["MGCYCLE= V_CYCLE","MG_PRE_SMOOTH= (1,2,3,3)","MG_POST_SMOOTH= (2,2,2,2)",
                  "MG_CORRECTION_SMOOTH= (0,0,0,0)","MG_DAMP_RESTRICTION= 0.8","MG_DAMP_PROLONGATION= 0.8"]
    if args.case == "inlet":
        sigma = atmo["density"] / isa(0)["density"]
        mdot = P.ENGINE["mdot_air"] * sigma * (1 + .6 * mach ** 2)
        lines += ["ENGINE_INFLOW_TYPE= FAN_FACE_MDOT", f"MARKER_ENGINE_INFLOW= ( ENGINE, {mdot} )"]
        lines[lines.index("MARKER_PLOTTING= ( WALL )")] = "MARKER_PLOTTING= ( WALL, ENGINE )"
        # Tam kanal: yarı debi kullanılmaz; FARFIELD dış dudak/gövde hacmini de kapsar.
    if args.case in ("rae2822", "airfoil"):
        # SU2 v8.2.0 TestCases RAE2822 numerical settings (Case 6).
        # Case 6 conditions match the NPARC archive; Case 9 is a separate benchmark.
        for old,new in (("CFL_NUMBER= 10.0","CFL_NUMBER= 2.5"),
                        ("CONV_NUM_METHOD_FLOW= ROE","CONV_NUM_METHOD_FLOW= JST"),
                        ("MUSCL_FLOW= YES","MUSCL_FLOW= NO"),
                        ("MGLEVEL= 0","MGLEVEL= 3"),
                        ("MUSCL_TURB= YES","MUSCL_TURB= NO"),
                        ("LINEAR_SOLVER= FGMRES","LINEAR_SOLVER= BCGSTAB"),
                        ("LINEAR_SOLVER_ITER= 10","LINEAR_SOLVER_ITER= 20")):
            lines[lines.index(old)] = new
        lines += ["JST_SENSOR_COEFF= ( 0.5, 0.02 )", "MGCYCLE= W_CYCLE",
                  "MG_PRE_SMOOTH= (1,2,3,3)","MG_POST_SMOOTH= (0,0,0,0)",
                  "MG_CORRECTION_SMOOTH= (0,0,0,0)","MG_DAMP_RESTRICTION= 0.95","MG_DAMP_PROLONGATION= 0.95"]
        if getattr(args, "rae_scheme", "mg3") == "mg0":
            # Iter5 v2 alternatifi: MG yok + uyarlamali CFL (duz levha ile ayni ayar).
            for old,new in (("CFL_NUMBER= 2.5","CFL_NUMBER= 1.0"),("CFL_ADAPT= NO","CFL_ADAPT= YES"),
                            ("MGLEVEL= 3","MGLEVEL= 0")):
                lines[lines.index(old)] = new
            lines.insert(lines.index("CFL_ADAPT= YES")+1,"CFL_ADAPT_PARAM= ( 0.5, 1.5, 1.0, 100.0 )")
        # Durma kurali proje kapisina hizalanir (sayisal sema degismez): nu_tilde
        # residual'i <=-8.6 (baslangic ~-4.4) VE DRAG-Cauchy <=1e-8.
        for old,new in (("CONV_FIELD= DRAG","CONV_FIELD= ( RMS_NU_TILDE, DRAG )"),
                        ("CONV_CAUCHY_EPS= 1e-6","CONV_CAUCHY_EPS= 1e-8"),
                        ("CONV_RESIDUAL_MINVAL= -8","CONV_RESIDUAL_MINVAL= -8.6")):
            lines[lines.index(old)] = new
    if args.case in ("aircraft", "inlet"):
        lines += ["INIT_OPTION= TD_CONDITIONS", f"FREESTREAM_PRESSURE= {atmo['pressure']}"]
    conditions = dict(mach=mach, reynolds=re, alpha_deg=alpha, temperature_K=temp,
                      ref_length_m=length, ref_area_m2=area, atmosphere=atmo)
    if args.case in ("rae2822", "airfoil"):
        conditions["solver_scheme"] = getattr(args, "rae_scheme", "mg3")
    return "\n".join(lines) + "\n", conditions


def solve(args, work, solver):
    mesh = mesh_2d(args, work) if args.case in ("rae2822", "airfoil", "flat_plate") else reviewed_mesh(args, work)
    config, conditions = configuration(args)
    (work / "case.cfg").write_text(config, encoding="ascii")
    if args.prepare_only:
        return dict(status="PREPARED", mesh=mesh, conditions=conditions, metrics={}, quality={})
    execution = run_solver([solver, "case.cfg"], work, args.timeout, args.threads)
    rows = csv_rows(work / "history.csv")
    if len(rows) < 100:
        raise Blocked("En az 100 iterasyonluk geçmiş gerekli.")
    cd = [pick(r, "CD", "Drag") for r in rows[-100:]]
    cl = [pick(r, "CL", "Lift") for r in rows[-100:]]
    rms = [v for k, v in rows[-1].items() if k.lower().replace('_', '').startswith('rms')]
    from cfd.convergence import assess
    quality = assess(rows, args.model)
    converged = quality['iterative_converged']
    surface = csv_rows(work / "surface_flow.csv")
    yplus = max(pick(r, "Y_Plus", "yplus") for r in surface)
    metrics = dict(cl=cl[-1], cd=cd[-1], cm=pick(rows[-1], "CMz", "Moment_z"))
    if args.case in ('rae2822','airfoil'):
        metrics['cm_su2_z'] = metrics['cm']
        metrics['cm'] = -metrics['cm']  # x downstream, y up; conventional nose-up Cm
    if args.case == "aircraft":
        q = .5 * conditions["atmosphere"]["density"] * (conditions["mach"] * conditions["atmosphere"]["sound_speed"]) ** 2
        metrics["drag_N"] = 2 * q * conditions["ref_area_m2"] * cd[-1]
    if args.case == "inlet":
        import params as P
        from cfd.face_samples import samples
        from cfd.inlet_metrics import calculate
        pt_inf = conditions["atmosphere"]["pressure"] * (1 + .2*conditions["mach"]**2)**3.5
        face = samples(work / "mesh.su2", work / "surface_flow.csv")
        metrics.update(calculate(face, pt_inf))
        expected = P.ENGINE["mdot_air"] * conditions["atmosphere"]["density"] / isa(0)["density"] * (1+.6*conditions["mach"]**2)
        metrics["mdot_target_kg_s"] = expected
        converged = converged and abs(metrics["mdot_kg_s"] / expected - 1) < .01
        write_json(work / "engine_face.json", face)
    if args.case == "flat_plate":
        metrics["cf_mean"] = cd[-1]  # REF_AREA=2, tek yüzey / birim açıklık
        metrics["cf_ittc"] = .075 / (math.log10(1e7) - 2) ** 2
        metrics["cf_schlichting"] = .455 / math.log10(1e7) ** 2.58
    require_module("matplotlib")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].plot([pick(r, "CD", "Drag") for r in rows]); axes[0].set(xlabel="İterasyon", ylabel="CD")
    xs = [pick(r, "x", "x_coord") for r in surface]
    cps = [pick(r, "Pressure_Coefficient", "Cp") for r in surface]
    axes[1].scatter(xs, cps, s=2); axes[1].set(xlabel="x [m]", ylabel="Cp"); axes[1].invert_yaxis()
    fig.tight_layout(); fig.savefig(work / "plot.png", dpi=140); plt.close(fig)
    write_json(work / "surface.json", surface)
    if args.case == "airfoil":
        af_points, _ = coordinates(args)
        import aerosandbox as asb
        import numpy as np
        af = asb.Airfoil(name="validation64a007", coordinates=np.asarray(af_points))
        nf = af.get_aero_from_neuralfoil(alpha=args.alpha, Re=4.5e6, mach=args.mach, model_size="large")
        nf0 = af.get_aero_from_neuralfoil(alpha=args.alpha, Re=4.5e6, mach=0, model_size="large")
        write_json(work / "neuralfoil.json", {key: {k: float(np.asarray(v).reshape(-1)[0]) for k, v in value.items() if k in ("CL", "CD", "CM")}
                                             for key, value in (("matched_mach", nf), ("legacy_M0", nf0))})
        # Cp* kritik sonik değer; bu M'de sonic varsa Mcrit <= M (aralık taramasıyla sınırla).
        m = conditions["mach"]
        cp_star = 2 / (1.4 * m*m) * (((1 + .2*m*m) / 1.2) ** 3.5 - 1)
        metrics.update(cp_min=min(cps), cp_sonic=cp_star, sonic_on_surface=min(cps) <= cp_star)
    errors = {}
    if args.case == "flat_plate":
        from validation.convergence import error
        errors["cf_mean"] = error(metrics["cf_mean"], metrics["cf_schlichting"])
    return dict(status="COMPUTED" if converged and yplus <= 1 else "UNCONVERGED", metrics=metrics,
                errors=errors,
                quality=dict(quality, iterative_converged=converged, yplus_max=yplus),
                mesh=mesh, conditions=conditions, execution=execution,
                limitations=["Türbülanslı RANS; geçiş, pürüzlülük ve model-form hatası ayrıca incelenmeli.",
                             "inlet DC60 için motor yüzü örneklemesi ve cfd/inlet_metrics.py gerekir."])
