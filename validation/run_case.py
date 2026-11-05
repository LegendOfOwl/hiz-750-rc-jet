"""Tek vaka/üç ağ runner: python validation/run_case.py <case> --level coarse."""
import argparse
import os
from copy import copy
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from validation.common import (Blocked, LEVELS, digest, executable, provenance, read_json,
                               status_plot, work_directory, write_json)

CASES = {
    "rae2822": ("validation", "cfd", (), "15–90 dk/ağ/model; tahmin"),
    "flat_plate": ("validation", "cfd", (), "5–30 dk/ağ/model; tahmin"),
    "cantilever": ("validation", "fem", (), "<2 dk/ağ; tahmin"),
    "coupon": ("validation", "fem", (), "<1 dk/ağ; CLT kompozit kabuk kuponu"),
    "thermal_1d": ("validation", "thermal", (), "<1 dk/ağ; tahmin"),
    "airfoil": ("cfd", "cfd", ("rae2822", "flat_plate"), "10–60 dk/nokta/ağ/model; tahmin"),
    "aircraft": ("cfd", "cfd", ("rae2822", "flat_plate"), "1–6 saat/ağ; pilot koşuyla ölçülmeli"),
    "inlet": ("cfd", "cfd", ("rae2822", "flat_plate"), "1–4 saat/ağ; pilot koşuyla ölçülmeli"),
    "wing": ("fem", "fem", ("cantilever",), "5–30 dk/ağ; <200k açılmış DOF; tahmin"),
    "engine_thermal": ("thermal", "thermal", ("thermal_1d",), "<2 dk/senaryo/ağ; tahmin"),
}


def case_id(args):
    key = args.case
    if CASES[args.case][1] == "cfd":
        key += "_" + args.model
    if args.case == "airfoil":
        key += f"_M{args.mach:.4f}_A{args.alpha:.4f}"
    if args.case == "aircraft":
        key += f"_A{args.alpha:.4f}"
    if args.case == "wing" and getattr(args, "wing_fuel", "full") == "empty":
        key += "_empty"
    if args.case == "wing" and os.environ.get("HZ750_VARIANT"):
        key += "_" + os.environ["HZ750_VARIANT"]   # rijitleştirme seçeneği (fem/wing_shell.options)
    if args.case == "engine_thermal":
        key += f"_T{args.motor_C:g}_F{args.felt_mm:g}"
        if args.thermal_inputs and args.thermal_inputs.is_file():
            key += "_" + digest(args.thermal_inputs)[:10]
    return key.replace(".", "p").replace("-", "m")


def result_dir(args):
    if args.case == "wing" and os.environ.get("HZ750_VARIANT"):
        return ROOT / "fem/results/stiffening" / case_id(args)
    return ROOT / CASES[args.case][0] / "results" / case_id(args)


def gate(args):
    from validation.study import evaluate
    for benchmark in CASES[args.case][2]:
        key = benchmark + ("_" + args.model if CASES[args.case][1] == "cfd" else "")
        directory = ROOT / "validation/results" / key
        summary = evaluate(directory)
        if summary["status"] != "BENCHMARK_ACCEPTED":
            raise Blocked(f"Önce {key} üç ağ + referans kabulü gerekli ({summary['status']}); "
                          "yalnız ayar denemesi için --diagnostic kullanılabilir.")
        path = directory / "fine.json"
        # Aynı toolchain gereklidir; başka bir solver build'inin kabulü taşınamaz.
        target = executable("SU2_CFD" if CASES[args.case][1] == "cfd" else "CCX", args.tool_config)
        if read_json(path).get("execution", {}).get("executable_sha256") != digest(target):
            raise Blocked(f"{key} başka solver build'i ile çalışmış; benchmarkları tekrarlayın.")


def run_one(args):
    directory = result_dir(args)
    directory.mkdir(parents=True, exist_ok=True)
    # Başarısız yeniden koşum eski başarı grafiğini bırakmaz; yalnız bilinen dosyalar temizlenir.
    artifacts = ("plot.png", "case.cfg", "case.inp", "mesh.json", "surface.json", "geometry.json", "engine_face.json", "neuralfoil.json", "assumptions.json", "temperature_profile.json", "wing_model.json")
    for name in (*artifacts, "status.svg"):
        (directory / f"{args.level}_{name}").unlink(missing_ok=True)
    source_files = [ROOT/p for p in ("structures/structures.py","structures/fe_modal.py","aero/aero_analysis.py",
                                    "performance/inlet_analysis.py","cad/out/cad_report.json")]
    result = dict(case=args.case, case_id=case_id(args), level=args.level, status="BLOCKED", metrics={},
                  reason=None, design_accepted=False, provenance=provenance(source_files), estimated_runtime=CASES[args.case][3],
                  diagnostic=args.diagnostic, raw_directory=None,
                  code_sha256={str(p.relative_to(ROOT)): digest(p) for folder in ("validation", "cfd", "fem", "thermal")
                               for p in sorted((ROOT / folder).glob("*.py"))},
                  input_sha256={k: digest(v) for k in ("airfoil", "reference", "mesh", "mesh_review", "deck", "thermal_inputs")
                                if (v := getattr(args, k, None)) and Path(v).is_file()})
    started = time.monotonic()
    work = None
    try:
        if CASES[args.case][2] and not args.diagnostic and not args.prepare_only:
            gate(args)
        solver = None if args.prepare_only else executable("SU2_CFD" if CASES[args.case][1] == "cfd" else "CCX", args.tool_config)
        work = work_directory(case_id(args) + "_" + args.level, args.tool_config)
        result["raw_directory"] = str(work)
        kind = CASES[args.case][1]
        if kind == "cfd":
            from cfd.cases import solve
        elif kind == "fem":
            from fem.cases import solve
        else:
            from thermal.cases import solve
        result.update(solve(args, work, solver))
        if args.reference and result["status"] in ("COMPUTED", "UNCONVERGED"):
            from validation.study import compare_reference
            result.update(compare_reference(result, read_json(args.reference), work))
        if args.diagnostic and result["status"] == "COMPUTED":
            result["status"] = "DIAGNOSTIC"
    except Blocked as exc:
        result.update(status="BLOCKED", reason=str(exc))
    except Exception as exc:
        result.update(status="FAILED", reason=f"{type(exc).__name__}: {exc}")
        import traceback
        if work:
            (work / "exception.txt").write_text(traceback.format_exc(), encoding="utf-8")
    finally:
        result["elapsed_s"] = time.monotonic() - started
        result["artifacts"] = []
        if work:
            for name in artifacts:
                source = work / name
                if source.is_file():
                    target = directory / f"{args.level}_{name}"
                    shutil.copy2(source, target)
                    result["artifacts"].append(str(target.relative_to(ROOT)))
        write_json(directory / f"{args.level}.json", result)
        if not (directory / f"{args.level}_plot.png").is_file():
            status_plot(directory / f"{args.level}_status.svg", f"{args.case} / {args.level}: {result['status']}",
                        result.get("reason") or "Çözüm henüz çalıştırılmadı.")
        print(f"{result['status']}: {case_id(args)} / {args.level}: {result.get('reason') or directory}")
    return result


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("case", choices=CASES)
    p.add_argument("--level", choices=LEVELS, default="coarse")
    p.add_argument("--study", action="store_true", help="Sırayla üç ağ + GCI/hata tablosu")
    p.add_argument("--model", choices=("SA", "SST"), default="SA")
    p.add_argument("--alpha", type=float, default=0.0)
    p.add_argument("--mach", type=float, default=.61)
    p.add_argument("--motor-C", type=float, default=250.)
    p.add_argument("--felt-mm", type=float, default=0.)
    p.add_argument("--wing-fuel", choices=("full", "empty"), default="full", help="Kanat tankı dolu/boş kütle")
    p.add_argument("--tools", type=Path, default=ROOT / "validation/tools.local.json")
    for flag in ("airfoil", "reference", "mesh", "mesh-review", "deck", "thermal-inputs"):
        p.add_argument("--" + flag, type=Path)
    p.add_argument("--diagnostic", action="store_true", help="Benchmark kapısını atlar; sonuç doğrulama kabulü alamaz")
    p.add_argument("--prepare-only", action="store_true", help="Solver çağırmadan mesh/deck üretir")
    p.add_argument("--iterations", type=int, default=6000)
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--timeout", type=int, default=7200)
    return p


def main():
    args = parser().parse_args()
    args.tool_config = read_json(args.tools) if args.tools.is_file() else {}
    if args.case == "airfoil" and not (.61 <= args.mach <= .75 and 0 <= args.alpha <= 2):
        raise SystemExit("Profil çalışma aralığı M=.61–.75, alpha=0–2 derece.")
    if args.timeout <= 0 or args.threads <= 0 or args.iterations < 100:
        raise SystemExit("Pozitif süre/thread ve >=100 iterasyon gerekli.")
    results = []
    for level in LEVELS if args.study else (args.level,):
        run_args = copy(args)
        run_args.level = level
        results.append(run_one(run_args))
    if args.study:
        from validation.study import save_study
        summary = save_study(result_dir(args))
        print("Çalışma:", summary["status"])
    # BLOCKED ayrı dönüş kodu; log otomasyonunda başarısızlık saklanmaz.
    return 1 if any(r["status"] in ("FAILED", "UNCONVERGED") for r in results) else 2 if any(r["status"] == "BLOCKED" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
