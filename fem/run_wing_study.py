"""Kanat üç ağ x (dolu, boş) zinciri: hazırla -> otomatik inceleme -> incelenmiş deck ile çöz -> GCI.

python fem/run_wing_study.py [--fuel full empty] [--levels coarse medium fine]
CCX ortam değişkeni (veya validation/tools.local.json) gerekli; cantilever benchmarkı kabul edilmiş olmalı.
Benchmarklar da --threads 1 ile koşulmalı (aşağıdaki nota bakın).
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from validation.common import LEVELS, read_json  # noqa: E402


def run(args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.run([sys.executable, str(ROOT / "validation/run_case.py"), *args], cwd=ROOT, env=env,
                          capture_output=True, text=True, encoding="utf-8")
    print(proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else proc.stderr[-500:])
    return proc.returncode


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fuel", nargs="+", default=["full", "empty"], choices=("full", "empty"))
    p.add_argument("--levels", nargs="+", default=list(LEVELS), choices=LEVELS)
    a = p.parse_args()
    from validation.study import save_study
    for fuel in a.fuel:
        name = "wing" + ("" if fuel == "full" else "_empty")
        variant = os.environ.get("HZ750_VARIANT")
        result_dir = (ROOT / "fem/results/stiffening" / (name + "_" + variant.replace(".", "p").replace("-", "m"))
                      if variant else ROOT / "fem/results" / name)
        for level in a.levels:
            run(["wing", "--prepare-only", "--level", level, "--wing-fuel", fuel])
            prepared = Path(read_json(result_dir / f"{level}.json")["raw_directory"])
            review = prepared / "review.json"
            subprocess.run([sys.executable, str(ROOT / "fem/wing_review.py"), str(prepared), "--level", level,
                            "--output", str(review)], cwd=ROOT, check=False)
            shutil.copy2(review, result_dir / f"{level}_mesh_review.json")
            # CCX 2.20 Windows: çok iş parçacıklı sonuç hesabı (CCX_NPROC_RESULTS/OMP>1) bazı elemanlarda
            # bozuk gerilme ve tekrarlanamayan frekans üretti (iter5 bulgusu); tek iş parçacığı zorunlu.
            run(["wing", "--level", level, "--wing-fuel", fuel, "--deck", str(prepared / "case.inp"),
                 "--mesh-review", str(review), "--threads", "1"])
        print(fuel, save_study(result_dir)["status"])


if __name__ == "__main__":
    main()
