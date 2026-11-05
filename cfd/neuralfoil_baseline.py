"""Matched Mach and legacy M=0 baselines; no RANS acceptance implied."""
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cfd.cases import coordinates
from validation.common import provenance, write_json


def main():
    import aerosandbox as asb
    import numpy as np
    xy, source = coordinates(SimpleNamespace(case='airfoil'))
    af = asb.Airfoil(name='project_scaled_64a010', coordinates=np.asarray(xy))
    rows = []
    for alpha in (0,1,2):
        for mach in (0,.61,.65,.70,.75):
            result = af.get_aero_from_neuralfoil(alpha=alpha, Re=4.5e6, mach=mach, model_size='large')
            rows.append(dict(alpha_deg=alpha,mach=mach,reynolds=4.5e6,
                             **{k:float(np.asarray(result[k]).reshape(-1)[0]) for k in ('CL','CD','CM')}))
    write_json(ROOT/'cfd/results/neuralfoil_baseline.json',dict(
        status='BASELINE_ONLY',provenance=provenance(),geometry=source,rows=rows,
        note='Same project scaled 64A010; not independently sourced NACA64A007. NeuralFoil transition assumptions differ from fully turbulent RANS. No converged RANS comparison or Mcrit bound is established.'))


if __name__ == '__main__':
    main()
