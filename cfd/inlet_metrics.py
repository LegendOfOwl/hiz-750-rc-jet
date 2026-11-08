"""Motor yüzü hücre örneklerinden recovery ve DC60 (alan ağırlıklı 60° sektör)."""
import csv
import math
from pathlib import Path


def calculate(rows, pt_freestream):
    if not rows or pt_freestream <= 0:
        raise ValueError("Pozitif referans pt ve yüzey örnekleri gerekli")
    required = ("area", "rho", "un", "pt", "p", "theta_deg")
    if any(any(k not in r or not math.isfinite(r[k]) for k in required) for r in rows):
        raise ValueError("Alan, rho, normal hız, pt, p, theta_deg gerekli")
    if any(r["area"] <= 0 or r["rho"] <= 0 or r["un"] <= 0 or r["pt"] <= r["p"] for r in rows):
        raise ValueError("Ters akış/negatif alan veya basınç: yüzey ve işaretleri inceleyin")
    area = sum(r["area"] for r in rows)
    mass = sum(r["area"] * r["rho"] * r["un"] for r in rows)
    pt_mass = sum(r["area"] * r["rho"] * r["un"] * r["pt"] for r in rows) / mass
    pt_area = sum(r["area"] * r["pt"] for r in rows) / area
    q_area = sum(r["area"] * .5 * r["rho"] * r["un"] ** 2 for r in rows) / area
    # İnce ve yaklaşık eşit açısal örnekleme beklenir. Kayan pencere, 1° tarama.
    sectors = []
    for start in range(360):
        sector = [r for r in rows if (r["theta_deg"] - start) % 360 < 60]
        a = sum(r["area"] for r in sector)
        if not .14 * area <= a <= .20 * area:
            raise ValueError("60° sektör kapsaması yetersiz; tam disk/radyal örneklemeyi sıklaştırın")
        sectors.append(sum(r["area"] * r["pt"] for r in sector) / a)
    return dict(mdot_kg_s=mass, recovery_mass=pt_mass / pt_freestream,
                recovery_area=pt_area / pt_freestream,
                DC60=(pt_area - min(sectors)) / q_area,
                convention="(pt_area_mean - minimum_60deg_area_mean) / mean(0.5*rho*un^2)")


if __name__ == "__main__":
    import argparse
    import json
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("csv", type=Path)
    p.add_argument("--pt-freestream", type=float, required=True)
    a = p.parse_args()
    with a.csv.open() as stream:
        data = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(stream)]
    print(json.dumps(calculate(data, a.pt_freestream), indent=2))
