"""Kabuk modelini kuracak kişi için mevcut kat planını/yükleri doğrudan modelden dışa aktarır."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from validation.common import provenance, write_json


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    from structures import structures as ST
    import params as P
    base = ST.wing_section_model()
    ws = base["ws"]
    stations = []
    for i, y in enumerate(ST.YS):
        stations.append(dict(y_m=float(y), chord_m=float(ST.chord(y)), tc=float(ST.tc(y)),
                             cap_width_m=float(ws["w_cap"][i]), n_ud=int(ws["n_ud"][i]),
                             n_web=int(ws["n_web"][i]), EI_Nm2=float(ws["EI"][i]), GJ_Nm2=float(ws["GJ"][i]),
                             xcg_c=float(ws["xcg"][i]), mass_kg_m=float(ws["mprime"][i]),
                             fuel_kg_m=float(base["fuel_per_span"][i]),
                             ultimate_lift_N_m=float(ST.schrenk(P.N_LIMIT * P.SF)[i])))
    write_json(args.output, dict(status="MODEL_INPUTS_ONLY", provenance=provenance(), material=ST.MAT,
                                wing=P.WING, root_clamp_y_m=.035, ultimate_n=P.N_LIMIT * P.SF,
                                mass_summary=P.mass_summary(), stations=stations,
                                missing=["UD/FAB: E2, E3, G12, G13, G23, nu12, nu13, nu23, Yt, Yc, S12, F12", "CORE: E, nu", "Yapıştırıcı/bağlantı ve tabaka oryantasyonlarının imalat tanımı"]))


if __name__ == "__main__":
    main()
