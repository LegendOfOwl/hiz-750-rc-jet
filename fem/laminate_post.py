"""Doğrulanmış lokal tabaka gerilme CSV'sinden Tsai-Wu ve knockdown taraması.

CSV: element,layer,material,s11,s22,s12 (Pa). Global gerilmeler girdi olamaz.
CCX integration-point/layer eşleştirmesi host'ta kontrol edilmeden DAT otomatik çevrilmez.
"""
import argparse
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from validation.common import digest, read_json, write_json
from fem.cases import tsai_wu


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("csv",type=Path)
    p.add_argument("--model",type=Path,required=True,help="Runner coarse_wing_model.json")
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--knockdown",type=float,default=.544,help="structures.py KD; yalnız duyarlılık")
    a = p.parse_args()
    if not 0 < a.knockdown <= 1:
        raise SystemExit("0 < knockdown <= 1 gerekli")
    model = read_json(a.model)
    values = []
    with a.csv.open() as stream:
        for row in csv.DictReader(stream):
            if row["material"] == "CORE":
                continue  # Köpük hasarı Tsai-Wu ile değerlendirilmez.
            mat = model["materials"][row["material"]]
            stress = [float(row[k]) for k in ("s11","s22","s12")]
            knocked = dict(mat)
            for name in ("Xt","Xc","Yt","Yc","S12"):
                knocked[name] *= a.knockdown
            knocked["F12"] /= a.knockdown**2
            values.append(dict(element=int(row["element"]),layer=int(row["layer"]),
                               tsai_wu_raw=tsai_wu(*stress,mat), tsai_wu_knockdown=tsai_wu(*stress,knocked)))
    if not values:
        raise SystemExit("Fiber tabakası gerilme verisi yok")
    write_json(a.output,dict(status="PROVISIONAL_MATERIAL_ASSUMPTIONS", csv_sha256=digest(a.csv),
                             model_sha256=digest(a.model), max_tsai_wu_raw=max(r["tsai_wu_raw"] for r in values),
                             max_tsai_wu_knockdown=max(r["tsai_wu_knockdown"] for r in values),
                             design_accepted=False, critical=max(values,key=lambda r:r["tsai_wu_knockdown"])))


if __name__ == "__main__":
    main()
