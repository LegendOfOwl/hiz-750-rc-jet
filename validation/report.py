"""Mevcut yarı-ampirik dosyaları ve iter5 durumlarını yan yana raporlar; sonuç icat etmez."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from validation.common import digest, read_json, write_json
from validation.study import save_study


def main():
    paths = ("aero/out/sonuclar.json", "structures/out/fe_sonuclar.json", "performance/out/alik_sonuclar.json", "cad/out/cad_report.json")
    aero, fe, inlet, cad = [read_json(ROOT / p) for p in paths]
    base = dict(kind="EXISTING_SEMI_EMPIRICAL_NOT_ITER5_RESULTS",
                source_sha256={p: digest(ROOT / p) for p in paths},
                drag_aerobuildup_N=aero["D_750"], drag_sizing_approx_N=210,
                neuralfoil_M0_Re4p5e6=aero["profiller"]["naca64a007"]["4.5e+06"],
                fe_full=fe["base"]["dolu"], fe_empty=fe["base"]["bos"],
                inlet_750=min(inlet, key=lambda r: abs(r["V"] * 3.6 - 750)),
                clearance_cad_mm=cad["engine_radial_clearance_mm"])
    studies = {}
    for folder in ("validation", "cfd", "fem", "thermal"):
        for directory in (ROOT / folder / "results").glob("*"):
            if directory.is_dir() and any(directory.glob("coarse.json")):
                studies[str(directory.relative_to(ROOT))] = save_study(directory)
    write_json(ROOT / "validation/results/comparison.json", dict(baseline=base, studies=studies, design_accepted=False))
    def latest(case, metric):
        candidates = []
        for folder in ("cfd", "fem", "thermal"):
            for path in (ROOT/folder/"results").glob("*/fine.json"):
                row = read_json(path)
                if row.get("case") == case and metric in row.get("metrics", {}) and row["status"] in ("COMPUTED", "REVIEW_REQUIRED", "DIAGNOSTIC"):
                    candidates.append(f"{row['metrics'][metric]:.6g} ({row['case_id']}, {row['status']})")
        return "; ".join(candidates) or "bekliyor"
    lines = ["# İter5 karşılaştırma (otomatik)", "", "Mevcut sonuçlar yeni solver sonucu değildir.", "",
             "| Büyüklük | Mevcut model | İter5 |", "|---|---|---|",
             f"| D @750 [N] | {aero['D_750']:.3f} / yaklaşık 210 | {latest('aircraft','drag_N')} |",
             f"| η_r | {base['inlet_750']['eta_r']:.6f} | {latest('inlet','recovery_mass')} |",
             f"| DC60 | eski modelde yok | {latest('inlet','DC60')} |",
             f"| 1B adayı / 1T adayı [Hz], tank dolu | {fe['gvt']['dolu']['f1B']:.3f} / {fe['gvt']['dolu']['f1T']:.3f} | {latest('wing','f1_Hz')} / {latest('wing','f1T_provisional_Hz')} |",
             f"| Flutter [km/h], tank dolu | {fe['base']['dolu']['Vf_kmh']:.3f} | bekliyor; yeni modal aeroelastik çözüm gerekli |",
             f"| Kabuk iç yüzeyi [°C] | ölçülmedi | {latest('engine_thermal','shell_inner_C')} |", "",
             "## Solver çalışmaları", ""]
    for name, study in studies.items():
        import os
        relative = Path(os.path.relpath(ROOT/name/"study.md", ROOT/"validation/results")).as_posix()
        lines.append(f"- [{name}]({relative}): {study['status']}")
    (ROOT / "validation/results/comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
