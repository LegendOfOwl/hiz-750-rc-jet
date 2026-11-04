"""CalculiX kabuk konsol benchmarkı ve denetlenmiş laminat kanat girişi."""
import math
import re
from pathlib import Path
import shutil

from validation.common import Blocked, ROOT, digest, read_json, require_module, run_solver
from validation.convergence import error

NUMBER = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[EeDd][-+]?\d+)?"


def set_lines(items):
    items = list(items)
    return [", ".join(map(str, items[i:i+16])) for i in range(0, len(items), 16)]


def numeric(line):
    return [float(v.replace("D", "E").replace("d", "e")) for v in re.findall(NUMBER, line)]


def node_blocks(text, heading):
    """*NODE PRINT blokları; tüm mod/step blokları ayrı tutulur."""
    blocks, current = [], None
    for line in text.splitlines():
        if heading.lower() in line.lower():
            current = {}
            blocks.append(current)
        elif current is not None:
            values = numeric(line)
            if len(values) >= 2 and re.match(r"^\s*\d+\s", line):
                current[int(values[0])] = values[1:]
            elif current and line.strip():
                current = None
    return [b for b in blocks if b]


def frequencies(text):
    active, values = False, []
    for line in text.splitlines():
        compact = "".join(line.lower().split())
        if "eigenvalueoutput" in compact:
            active = True
        elif active and re.match(r"^\s*\d+\s", line):
            fields = numeric(line)
            if len(fields) >= 4:
                values.append(fields[3])  # mode, eigenvalue, rad/s, cycles/s, imaginary
        elif active and values and line.strip():
            break
    if len(values) < 5 or any(x <= 0 for x in values[:5]):
        raise Blocked("CalculiX DAT içinden ilk 5 pozitif frekans okunamadı; banner/çıktı biçimini kontrol edin.")
    return values[:5]


def beam_mesh(args, work):
    require_module("gmsh")
    import gmsh
    factor = 2 ** ("coarse", "medium", "fine").index(args.level)
    nx, ny = 10 * factor, 2 * factor
    gmsh.initialize()
    try:
        gmsh.model.add("cantilever")
        geo = gmsh.model.geo
        pts = [geo.addPoint(x, y, 0) for x, y in ((0, -.025), (1, -.025), (1, .025), (0, .025))]
        edges = [geo.addLine(pts[i], pts[(i + 1) % 4]) for i in range(4)]
        face = geo.addPlaneSurface([geo.addCurveLoop(edges)])
        for i, edge in enumerate(edges):
            geo.mesh.setTransfiniteCurve(edge, (nx if i % 2 == 0 else ny) + 1)
        geo.mesh.setTransfiniteSurface(face)
        geo.mesh.setRecombine(2, face)
        geo.synchronize()
        gmsh.option.setNumber("Mesh.SecondOrderIncomplete", 1)
        gmsh.model.mesh.generate(2)
        gmsh.model.mesh.setOrder(2)
        gmsh.write(str(work / "mesh.msh"))
        tags, xyz, _ = gmsh.model.mesh.getNodes()
        nodes = {int(tag): tuple(float(c) for c in xyz[3*i:3*i+3]) for i, tag in enumerate(tags)}
        et, en = gmsh.model.mesh.getElementsByType(16)  # gmsh quad8 == Abaqus S8R node ordering
        if not len(et):
            raise Blocked("gmsh quad8 (tip16) üretmedi; ikinci mertebe incompleteness kontrol edilmeli.")
        elements = {int(tag): [int(c) for c in en[8*i:8*i+8]] for i, tag in enumerate(et)}
        tip, root = [t for t, p in nodes.items() if abs(p[0] - 1) < 1e-9], [t for t, p in nodes.items() if abs(p[0]) < 1e-9]
        _, edge_nodes = gmsh.model.mesh.getElementsByType(8, edges[1])
        forces = dict.fromkeys(tip, 0.0)
        for i in range(0, len(edge_nodes), 3):
            n1, n2, nm = map(int, edge_nodes[i:i+3])
            length = math.dist(nodes[n1], nodes[n2])
            for tag, weight in ((n1, 1/6), (n2, 1/6), (nm, 2/3)):
                forces[tag] += length / .05 * weight  # toplam tip yükü 1 N
        return nodes, elements, tip, root, forces
    finally:
        gmsh.finalize()


def beam_input(args, work):
    nodes, elements, tip, root, forces = beam_mesh(args, work)
    data = ["*HEADING", "HIZ750 verification: 1m x .05m x .01m steel cantilever, SI", "*NODE, NSET=NALL"]
    data += [f"{tag}, {x:.10e}, {y:.10e}, {z:.10e}" for tag, (x, y, z) in nodes.items()]
    data += ["*ELEMENT, TYPE=S8R, ELSET=EALL"]
    data += [str(tag) + ", " + ", ".join(map(str, conn)) for tag, conn in elements.items()]
    data += ["*NSET, NSET=ROOT"] + set_lines(root) + ["*NSET, NSET=TIP"] + set_lines(tip)
    data += ["*MATERIAL, NAME=STEEL", "*ELASTIC", "210e9, .3", "*DENSITY", "7800",
             "*SHELL SECTION, ELSET=EALL, MATERIAL=STEEL", ".01", "*BOUNDARY", "ROOT, 1, 6",
             "*STEP", "*STATIC, SOLVER=SPOOLES", "*CLOAD"]
    data += [f"{n}, 3, {-f:.10e}" for n, f in forces.items()]
    data += ["*NODE PRINT, NSET=TIP", "U", "*NODE PRINT, NSET=ROOT", "RF",
             "*NODE FILE", "U", "*EL FILE", "S", "*END STEP",
             "*STEP", "*FREQUENCY, SOLVER=SPOOLES", "5", "*NODE FILE", "U", "*END STEP"]
    (work / "case.inp").write_text("\n".join(data) + "\n", encoding="ascii")
    ei = 210e9 * .05 * .01 ** 3 / 12
    exact = dict(tip_deflection_m=1 / (3 * ei),
                 f1_Hz=1.875104068711961 ** 2 / (2 * math.pi) * math.sqrt(ei / (7800 * .05 * .01)))
    mesh = dict(cells=len(elements), nodes=len(nodes), dimension=2, h=1 / math.sqrt(len(elements)),
                nominal_dof=6 * len(nodes), element="S8R", mesh_sha256=digest(work / "mesh.msh"))
    return exact, mesh


def wing_input(args, work):
    if not args.deck:
        from fem.wing_shell import prepare
        prepared = prepare(args, work)
        if not args.prepare_only and not args.diagnostic:
            raise Blocked("DRAFT kanat deck'i üretildi. İnce burun/TE sandviç çakışmaları, mafsal kesikleri, kütle ve bağlantılar incelenip --deck/--mesh-review ile verilmeli; yalnız ön koşu için --diagnostic.")
        return prepared
    if not args.mesh_review:
        raise Blocked("Harici kanat deck'i için --mesh-review gerekli.")
    review = read_json(args.mesh_review)
    if "*INCLUDE" in Path(args.deck).read_text().upper():
        raise Blocked("Kanat deck kendi içinde kapalı olmalı; *INCLUDE içeriğini tek dosyada birleştirin.")
    if review.get("deck_sha256") != digest(args.deck):
        raise Blocked("Kanat deck SHA256 inceleme kaydıyla eşleşmiyor.")
    for key in ("laminate_materials_complete", "orientations_checked", "mass_reconciled", "ultimate_load_checked", "shell_connectivity_checked"):
        if review.get(key) is not True:
            raise Blocked(f"Kanat FEM incelemesi eksik: {key}")
    if not 0 < review.get("expanded_dof", 0) <= 200_000:
        raise Blocked("Kabukların ccx 3B açılımı dahil DOF bütçesi 200k.")
    if review.get("level") != args.level or not isinstance(review.get("h"), (int, float)) or review["h"] <= 0:
        raise Blocked("Kanat inceleme dosyasında doğru level ve pozitif h gerekli.")
    shutil.copy2(args.deck, work / "case.inp")
    # İncelenen hazırlık klasöründen model/düğüm verisi (SHA eşleşmeli) son işlem için kopyalanır.
    for name in ("wing_model.json", "wing_nodes.json"):
        source = Path(review.get("prepared_dir", "")) / name
        if not source.is_file() or digest(source) != review.get(name.replace(".", "_") + "_sha256"):
            raise Blocked(f"İnceleme kaydındaki {name} bulunamadı veya SHA256 eşleşmiyor.")
        shutil.copy2(source, work / name)
    if review.get("fuel_state") != getattr(args, "wing_fuel", "full"):
        raise Blocked("İnceleme kaydının yakıt durumu --wing-fuel ile aynı olmalı.")
    return {}, review


def solve(args, work, solver):
    if args.case == "coupon":
        from fem.coupon import solve as coupon_solve
        return coupon_solve(args, work, solver)
    exact, mesh = beam_input(args, work) if args.case == "cantilever" else wing_input(args, work)
    if args.prepare_only:
        return dict(status="PREPARED", mesh=mesh, metrics={}, references=exact, quality={})
    execution = run_solver([solver, "-i", "case"], work, args.timeout, args.threads)
    text = (work / "case.dat").read_text(errors="replace")
    blocks = node_blocks(text, "displacements")
    if not blocks:
        raise Blocked("DAT içinde *NODE PRINT displacement yok.")
    fs = frequencies(text)
    metrics = dict(tip_deflection_m=max(abs(u[2]) for u in blocks[0].values()), f1_Hz=fs[0])
    metrics.update({f"f{i+1}_Hz":f for i,f in enumerate(fs)})
    errors = {k: error(metrics[k], ref) for k, ref in exact.items()}
    quality = {}
    if args.case == "cantilever":
        rf = node_blocks(text, "forces")
        reaction = sum(u[2] for u in rf[0].values()) if rf else None
        quality = dict(force_balance_relative=abs(reaction - 1) if reaction is not None else None)
        accepted = reaction is not None and abs(reaction - 1) < .005
    elif (work / "wing_nodes.json").is_file():
        from fem.wing_post import plot as wing_plot, postprocess as wing_postprocess
        model = read_json(work / "wing_model.json")
        nodes_data = read_json(work / "wing_nodes.json")
        wing_metrics, wing_quality, modes, rows = wing_postprocess(text, model, nodes_data)
        metrics = wing_metrics
        coupon = ROOT / "validation/results/coupon/study.json"
        coupon_status = read_json(coupon)["status"] if coupon.is_file() else "MISSING"
        log = (work / "solver.log").read_text(errors="replace").splitlines()
        equations = [int(log[i + 1]) for i, line in enumerate(log[:-1])
                     if "number of equations" in line and log[i + 1].strip().isdigit()]
        quality = dict(wing_quality, modes=modes, static_profile=rows, coupon_benchmark=coupon_status,
                       ccx_equations=max(equations) if equations else None,
                       relative_mass_difference=model["mesh"]["relative_mass_difference"], model_mesh=model["mesh"],
                       bays=model["bays"], levers=len(model.get("levers", [])),
                       mode_classification="AUTOMATIC_SHAPE_FIT (kutu düğümleri w=a+theta x; incelenmeli)")
        wing_plot(work, modes, rows, f"Kanat S8R {args.level}, yakıt {getattr(args, 'wing_fuel', 'full')}")
        # Kanat sonucu kupon kabulü olsa da tasarım kabulü değildir: varsayımsal malzeme, imalat detayı yok.
        status = "REVIEW_REQUIRED"
        return dict(status=status, mesh=mesh, metrics=metrics, frequencies_Hz=[m["f_Hz"] for m in modes],
                    references={}, errors={}, execution=execution, quality=quality,
                    limitations=["Malzeme sabitleri varsayım; Tsai-Wu dayanımları katalog/B-basis değildir.",
                                 "Lineer statik; burkulma, yapıştırıcı, cıvata, hasar ilerlemesi yok.",
                                 "Mod etiketleri otomatik şekil uydurmasıdır; GVT ile doğrulanmalı."])
    else:
        accepted = False  # wing_nodes.json olmadan kanat son işlemi yapılamaz.
    require_module("matplotlib")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(range(1, 6), fs, "o-"); ax.set(xlabel="Mod sırası", ylabel="Frekans [Hz]")
    fig.tight_layout(); fig.savefig(work / "plot.png", dpi=140); plt.close(fig)
    return dict(status="COMPUTED" if accepted else "REVIEW_REQUIRED", mesh=mesh, metrics=metrics,
                frequencies_Hz=fs, references=exact, errors=errors, execution=execution, quality=quality,
                limitations=["İlk frekans otomatik olarak 1T değildir. Kanatta mod şekilleri incelenmeli.",
                             "Lineer statik çözüm burkulma, yapıştırıcı, cıvata veya hasar ilerlemesini doğrulamaz."])


def tsai_wu(sigma1, sigma2, tau12, material):
    """Tabaka lokal düzlem gerilmeleri; dayanımlar pozitif, F12 ölçülen katsayı [Pa^-2]."""
    xt, xc, yt, yc, shear, f12 = [material[k] for k in ("Xt", "Xc", "Yt", "Yc", "S12", "F12")]
    if min(xt, xc, yt, yc, shear) <= 0 or abs(f12) >= 1 / math.sqrt(xt * xc * yt * yc):
        raise ValueError("Pozitif dayanımlar ve pozitif tanımlı Tsai-Wu etkileşimi gerekli")
    return ((1 / xt - 1 / xc) * sigma1 + (1 / yt - 1 / yc) * sigma2
            + sigma1 ** 2 / (xt * xc) + sigma2 ** 2 / (yt * yc)
            + tau12 ** 2 / shear ** 2 + 2 * f12 * sigma1 * sigma2)
