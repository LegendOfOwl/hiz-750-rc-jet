"""Full precision native control diagnostics; never a three-grid acceptance."""
import argparse
import csv
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cfd.cases import csv_rows, pick, coordinates
from cfd.convergence import assess
from cfd.mesh_audit import audit
from validation.common import read_json,write_json,digest
from validation.study import compare_reference


def wall_contour(path, marker='AIRFOIL'):
    """Follow actual wall connectivity; avoid a different coordinate database."""
    points, edges = {}, []
    lines = iter(Path(path).read_text().splitlines())
    for line in lines:
        if line.startswith('NPOIN='):
            for i in range(int(line.split('=')[1].split()[0])):
                row = next(lines).split()
                points[int(row[-1]) if len(row)>2 else i] = tuple(map(float,row[:2]))
        if line.startswith('MARKER_TAG='):
            name = line.split('=')[1].strip()
            count = int(next(lines).split('=')[1])
            values = [list(map(int,next(lines).split()))[1:3] for _ in range(count)]
            if name == marker: edges = values
    neighbors = {}
    for a,b in edges:
        neighbors.setdefault(a,[]).append(b); neighbors.setdefault(b,[]).append(a)
    if not neighbors or any(len(v)!=2 for v in neighbors.values()):
        raise ValueError('Wall is not a closed single contour')
    te = max(neighbors,key=lambda i:points[i][0])
    ids = [te]; previous = None; current = te
    while True:
        nxt = next(n for n in neighbors[current] if n != previous)
        if nxt == te: break
        if nxt in ids: raise ValueError('Repeated wall node')
        ids.append(nxt); previous,current = current,nxt
    xy = [points[i] for i in ids]+[points[te]]
    le = min(range(len(xy)),key=lambda i:xy[i][0])
    if sum(y for _,y in xy[:le+1])/len(xy[:le+1]) < sum(y for _,y in xy[le:])/len(xy[le:]):
        xy.reverse()
    return xy


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('record',type=Path)
    a = p.parse_args()
    record = read_json(a.record)
    work = Path(record['raw_directory'])
    rows = csv_rows(work/'history.csv')
    surface = csv_rows(work/'surface_flow.csv')
    quality = assess(rows)
    quality['yplus_max'] = max(pick(r,'Y_Plus') for r in surface) if 'Y_Plus' in surface[0] else None
    info = dict(status='NATIVE_DIAGNOSTIC_ONLY',original_record_sha256=digest(a.record),
                raw_directory=str(work),quality=quality,metrics=dict(cl=pick(rows[-1],'CL'),
                cd=pick(rows[-1],'CD'),cm=-pick(rows[-1],'CMz'),cm_su2_z=pick(rows[-1],'CMz')),
                mesh=audit(next(work.glob('mesh*.su2'))),
                history_sha256=digest(work/'history.csv'),surface_sha256=digest(work/'surface_flow.csv'),
                benchmark_accepted=False)
    if a.record.stem == 'rae2822_native':
        xy = wall_contour(work/'mesh_RAE2822_turb.su2')
        derived = work/'derived'
        derived.mkdir(exist_ok=True)
        write_json(derived/'geometry.json',xy)
        q = pick(rows[-1],'RefForce')  # official REF_AREA=1
        p_inf = 2*q/(1.4*.729**2)
        converted = []
        for r in surface:
            if 'Pressure_Coefficient' in r:
                cp = pick(r,'Pressure_Coefficient')
            else:
                rho = pick(r,'Density')
                kinetic = (pick(r,'Momentum_x')**2+pick(r,'Momentum_y')**2)/(2*rho)
                pressure = .4*(pick(r,'Energy')-kinetic)
                cp = (pressure-p_inf)/q
            converted.append(dict(x=pick(r,'x'),y=pick(r,'y'),Pressure_Coefficient=cp))
        with (derived/'surface_flow.csv').open('w',newline='') as stream:
            writer = csv.DictWriter(stream,fieldnames=list(converted[0]))
            writer.writeheader(); writer.writerows(converted)
        info['surface_note'] = 'Cp reconstructed where absent: ideal gas gamma=1.4, dimensional conservative energy; q=RefForce/REF_AREA, p_inf=2q/(gamma M^2). Original CSV preserved. y+ absent from native CSV, not inferred.'
        info['moment_convention'] = 'Conventional nose-up Cm = -SU2 CMz for x downstream, y up; raw CMz retained.'
        info['moment_reference'] = dict(x_over_c=.25,y_over_c=0.,z_over_c=0.,reference_chord=1.)
        info.update(case='rae2822',conditions=dict(mach=.729,reynolds=6.5e6,alpha_deg=2.31))
        info.update(compare_reference(info,read_json(ROOT/'validation/reference/rae2822.local.json'),derived,allow_partial_cp=True))
    write_json(a.record.with_name(a.record.stem+'_assessment.json'),info)
    print(info['quality'],info.get('errors'),info.get('cp_rmse'))


if __name__ == '__main__': main()
