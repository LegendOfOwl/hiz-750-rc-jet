"""Reassess saved CFD histories without overwriting original solver provenance."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cfd.cases import csv_rows, pick
from cfd.convergence import assess
from validation.common import digest, read_json, write_json
from validation.convergence import gci


def main():
    rows = []
    for level in ('coarse','medium','fine'):
        path = ROOT/f'validation/results/flat_plate_SA/{level}.json'
        if not path.is_file():
            rows.append(dict(level=level,status='PENDING'))
            continue
        result = read_json(path)
        if result['status'] == 'FAILED':
            rows.append(dict(level=level,status='FAILED',reason=result['reason'],raw_directory=result['raw_directory']))
            continue
        raw = Path(result['raw_directory'])
        history = csv_rows(raw/'history.csv')
        surface = csv_rows(raw/'surface_flow.csv')
        quality = assess(history)
        yp = max(pick(r,'Y_Plus') for r in surface)
        rows.append(dict(level=level,status='GATE_PASSED' if quality['iterative_converged'] and yp <= 1 else 'UNCONVERGED',
                         quality=quality,yplus_max=yp,cf=pick(history[-1],'CD'),h=result['mesh']['h'],
                         cells=result['mesh']['cells'],raw_directory=str(raw),
                         original_status=result['status'],history_sha256=digest(raw/'history.csv'),
                         original_result_sha256=digest(path)))
    conv = gci([r['h'] for r in rows[::-1]],[r['cf'] for r in rows[::-1]]) if all(r['status']=='GATE_PASSED' for r in rows) else None
    write_json(ROOT/'cfd/results/flatplate_reassessment.json',dict(
        status='REASSESSED_NOT_BENCHMARK_ACCEPTED',rows=rows,gci=conv,
        postprocessor_sha256=digest(__file__),gate_sha256=digest(ROOT/'cfd/convergence.py'),
        note='Historical solver/mesh/config provenance retained in original results. This postprocessing does not bypass study freshness checks or turn unconverged values into GCI inputs.'))
    print([(r['level'],r['status'],r.get('quality')) for r in rows])


if __name__ == '__main__': main()
