"""CalculiX DC3D8: analitik 1B benchmark ve parametrik motor/kabuk ısıl tarama.

Motor çalışması 1B yerel katman modelidir; 3B CHT veya bypass CFD sonucu değildir.
"""
import math

from validation.common import Blocked, digest, read_json, require_module, run_solver, write_json
from validation.convergence import error
from fem.cases import node_blocks, set_lines


def stack_mesh(layers, factor):
    """Yalıtılmış yan yüzlü 10x10 mm alan; x doğrultusunda katmanlı DC3D8."""
    nodes, elements, groups = {}, {}, {}
    xplanes, kplanes = [0.0], []
    for name, thickness, conductivity in layers:
        count = 4 * factor
        x0 = xplanes[-1]
        xplanes += [x0 + thickness * i / count for i in range(1, count + 1)]
        kplanes += [(name, conductivity)] * count
    yz = ((0, 0), (.01, 0), (.01, .01), (0, .01))
    for i, x in enumerate(xplanes):
        for j, (y, z) in enumerate(yz):
            nodes[4*i + j + 1] = (x, y, z)
    # Abaqus brick: alt z düzlemi 1-4, üst z düzlemi 5-8; x-y sağ elli.
    for i, (name, _) in enumerate(kplanes):
        a, b = 4*i, 4*(i+1)
        elements[i+1] = [a+1, b+1, b+2, a+2, a+4, b+4, b+3, a+3]
        groups.setdefault(name, []).append(i+1)
    return nodes, elements, groups, xplanes


def energy_solution(layers, case):
    """Aynı Robin/radyasyon modelinin bağımsız skaler enerji dengesi (Kelvin)."""
    resistance = sum(t/k for _, t, k in layers)
    sigma, eps = 5.670374419e-8, case["emissivity_effective"]
    hgap, hb, he = case["k_air"] / case["gap_m"], case["h_bypass"], case["h_external"]
    hot, bypass, ext = case["motor_K"], case["bypass_K"], case["external_K"]

    def inner(t):
        return hgap * (hot - t) + hb * (bypass - t) + eps * sigma * (hot ** 4 - t ** 4)

    def outer(t):
        return he * (t - ext) + case["emissivity_external"] * sigma * (t ** 4 - ext ** 4)

    def bisect(fun, lo, hi):
        if fun(lo) * fun(hi) > 0:
            raise ValueError("Isıl denge kökü sınırlandırılamadı")
        for _ in range(100):
            mid = (lo + hi) / 2
            if fun(mid) > 0:
                hi = mid
            else:
                lo = mid
        return (lo + hi) / 2

    lo, hi = min(hot, bypass, ext), max(hot, bypass, ext)
    def balance(tout):
        tin = tout + resistance * outer(tout)
        return outer(tout) - inner(tin)
    tout = bisect(balance, lo, hi)
    q = outer(tout)
    tin = tout + resistance * q
    shell_inner = tin - q * sum(t/k for name, t, k in layers if name != "SHELL")
    return dict(inner_K=tin, outer_K=tout, shell_inner_K=shell_inner, heat_flux_W_m2=q)


def prepare(args, work):
    factor = 2 ** ("coarse", "medium", "fine").index(args.level)
    if args.case == "thermal_1d":
        layers = [("SLAB", .1, 10.0)]
        thot, tinf, h = 373.15, 293.15, 25.0
        q = (thot - tinf) / (.1 / 10 + 1/h)
        exact = dict(outer_K=tinf + q / h, heat_flux_W_m2=q)
        scenario = None
    else:
        if not args.thermal_inputs:
            raise Blocked("Motor termalinde ölçülmemiş h/k/emissivite var; --thermal-inputs thermal/scenarios.example.json ile açık varsayım seçin.")
        scenario = read_json(args.thermal_inputs)
        # Taramadaki sıcaklık/keçe varyantı CLI'da açıkça seçilir; params.py'ye yazılmaz.
        scenario["motor_K"] = args.motor_C + 273.15
        scenario["gap_m"] = scenario["clearance_m"] - args.felt_mm / 1000
        if scenario["gap_m"] <= 0 or args.felt_mm < 0:
            raise Blocked("Keçe motor-kabuk açıklığına sığmıyor.")
        for key in ("k_air", "k_shell", "k_felt", "h_external", "shell_thickness_m"):
            if not math.isfinite(scenario[key]) or scenario[key] <= 0:
                raise ValueError(f"Pozitif sonlu ısıl girdi gerekli: {key}")
        if scenario["h_bypass"] < 0 or not 0 < scenario["emissivity_effective"] <= 1 or not 0 <= scenario["emissivity_external"] <= 1:
            raise ValueError("Geçersiz h_bypass/emissivite")
        layers = []
        if args.felt_mm:
            layers += [("FELT", args.felt_mm / 1000, scenario["k_felt"])]
        layers += [("SHELL", scenario["shell_thickness_m"], scenario["k_shell"])]
        exact = energy_solution(layers, scenario)
        write_json(work / "assumptions.json", scenario)
    nodes, elements, groups, planes = stack_mesh(layers, factor)
    end = len(planes) - 1
    data = ["*HEADING", "HIZ750 local steady 1D heat transfer; SI and Kelvin", "*NODE, NSET=NALL"]
    data += [f"{n}, {x:.10e}, {y:.10e}, {z:.10e}" for n, (x, y, z) in nodes.items()]
    data += ["*ELEMENT, TYPE=DC3D8, ELSET=EALL"]
    data += [f"{n}, " + ", ".join(map(str, conn)) for n, conn in elements.items()]
    for name, _, conductivity in layers:
        data += [f"*ELSET, ELSET={name}"] + set_lines(groups[name])
        data += [f"*MATERIAL, NAME=MAT_{name}", "*CONDUCTIVITY", str(conductivity),
                 f"*SOLID SECTION, ELSET={name}, MATERIAL=MAT_{name}"]
    data += ["*NSET, NSET=HOT", "1, 2, 3, 4", "*NSET, NSET=COLD",
             ", ".join(str(4*end + j) for j in range(1, 5)),
             "*PHYSICAL CONSTANTS, ABSOLUTE ZERO=0, STEFAN BOLTZMANN=5.670374419e-8",
             "*INITIAL CONDITIONS, TYPE=TEMPERATURE", "NALL, 293.15"]
    if scenario is None:
        data += ["*BOUNDARY", f"HOT, 11, 11, {thot}"]
    data += ["*STEP, INC=1000", "*HEAT TRANSFER, STEADY STATE", "1., 1.", "*FILM"]
    if scenario is None:
        data += [f"{len(elements)}, F4, {tinf}, {h}"]  # x+ face4; x- face6
    else:
        hg = scenario["k_air"] / scenario["gap_m"]
        hb = scenario["h_bypass"]
        sink = (hg * scenario["motor_K"] + hb * scenario["bypass_K"]) / (hg + hb)
        data += [f"1, F6, {sink}, {hg+hb}",
                 f"{len(elements)}, F4, {scenario['external_K']}, {scenario['h_external']}",
                 "*RADIATE", f"1, R6, {scenario['motor_K']}, {scenario['emissivity_effective']}"]
        if scenario["emissivity_external"]:
            data += [f"{len(elements)}, R4, {scenario['external_K']}, {scenario['emissivity_external']}"]
    data += ["*NODE PRINT, NSET=NALL", "NT", "*NODE FILE", "NT", "*EL FILE", "HFL", "*END STEP"]
    (work / "case.inp").write_text("\n".join(data) + "\n", encoding="ascii")
    # Küçük, yeniden üretilebilir Gmsh 2.2 mesh; solver bağımsız görsel inceleme için.
    msh = ["$MeshFormat", "2.2 0 8", "$EndMeshFormat", "$Nodes", str(len(nodes))]
    msh += [f"{n} {x} {y} {z}" for n, (x, y, z) in nodes.items()]
    msh += ["$EndNodes", "$Elements", str(len(elements))]
    msh += [f"{n} 5 0 " + " ".join(map(str, conn)) for n, conn in elements.items()]
    msh += ["$EndElements"]
    (work / "mesh.msh").write_text("\n".join(msh) + "\n", encoding="ascii")
    mesh = dict(cells=len(elements), nodes=len(nodes), dimension=1, h=planes[-1] / len(elements),
                element="DC3D8", mesh_sha256=digest(work / "mesh.msh"))
    return exact, mesh, scenario, layers, planes


def solve(args, work, solver):
    exact, mesh, scenario, layers, planes = prepare(args, work)
    if args.prepare_only:
        return dict(status="PREPARED", metrics={}, references=exact, mesh=mesh, quality={})
    execution = run_solver([solver, "-i", "case"], work, args.timeout, args.threads)
    blocks = node_blocks((work / "case.dat").read_text(errors="replace"), "temperatures")
    if not blocks:
        raise Blocked("CalculiX NT sıcaklık tablosu bulunamadı.")
    temperatures = blocks[-1]
    profile = [sum(temperatures[4*i+j][0] for j in range(1, 5))/4 for i in range(len(planes))]
    if scenario is None:
        q = 25 * (profile[-1] - 293.15)
    else:
        q = (scenario["h_external"] * (profile[-1] - scenario["external_K"])
             + scenario["emissivity_external"] * 5.670374419e-8 * (profile[-1] ** 4 - scenario["external_K"] ** 4))
    metrics = dict(outer_K=profile[-1], heat_flux_W_m2=q)
    conduction_q = (profile[0] - profile[-1]) / sum(t/k for _, t, k in layers)
    balance = abs(conduction_q - q) / max(abs(q), 1e-12)
    if scenario is not None:
        i = 4 * (2 ** ("coarse", "medium", "fine").index(args.level)) if args.felt_mm else 0
        metrics.update(inner_K=profile[0], shell_inner_K=profile[i], shell_inner_C=profile[i] - 273.15)
    require_module("matplotlib")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot([x * 1000 for x in planes], [t - 273.15 for t in profile], "o-")
    ax.set(xlabel="Katman kalınlığı [mm]", ylabel="Sıcaklık [°C]")
    fig.tight_layout(); fig.savefig(work / "plot.png", dpi=140); plt.close(fig)
    write_json(work / "temperature_profile.json", dict(x_m=planes, temperature_K=profile))
    return dict(status="COMPUTED" if balance < .005 else "UNCONVERGED", mesh=mesh, metrics=metrics,
                references=exact, errors={k: error(metrics[k], v) for k, v in exact.items()},
                quality=dict(heat_balance_relative=balance), execution=execution,
                assumptions=scenario, design_accepted=False,
                limitations=["Motor: yerel 1B kararlı durum, verilen h ve emissiviteyle koşullu sonuç.",
                             "Tg çalışma sıcaklığı izni değildir; hot/wet dayanım ve üretici limiti gerekli."])
