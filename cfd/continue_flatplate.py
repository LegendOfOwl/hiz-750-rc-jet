"""Continue saved flatplate solutions until BOTH reviewer gates pass, <=2h/level.

Original history/config/result hashes are retained. Each SU2 chunk uses DRAG
Cauchy; the outer loop prevents an early native exit from bypassing nu decay.
"""
import argparse
import csv
from copy import deepcopy
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cfd.cases import csv_rows, pick
from cfd.convergence import assess
from validation.common import digest, read_json, write_json, work_directory, run_solver
from validation.convergence import error
from validation.study import save_study


def setting(cfg, key, value):
    lines = [s for s in cfg.splitlines() if s.split('=',1)[0].strip() != key]
    return '\n'.join(lines)+f'\n{key}= {value}\n'


def process(level, solver, timeout):
    directory = ROOT/'validation/results/flat_plate_SA'
    original_path = directory/f'{level}.json'
    original = read_json(original_path)
    if original['status'] not in ('COMPUTED','UNCONVERGED') or not original.get('execution'):
        raise ValueError('Original solver failed; a successfully completed, provenance-verified restart is required')
    result = deepcopy(original)
    source = Path(original['raw_directory'])
    work = work_directory('flatplate_continue_'+level,{})
    for name in ('mesh.su2','restart.dat','surface_flow.csv'):
        shutil.copy2(source/name,work/name)
    history = csv_rows(source/'history.csv')
    quality = assess(history)
    original_history_length = len(history)
    cfg = (source/'case.cfg').read_text()
    for key,value in (('RESTART_SOL','YES'),('SOLUTION_FILENAME','restart.dat'),
                      ('CONV_FIELD','DRAG'),('CONV_CAUCHY_ELEMS','100'),
                      ('CONV_CAUCHY_EPS','1e-6'),('ITER','1000')):
        cfg = setting(cfg,key,value)
    started = time.monotonic()
    chunks = []
    try:
        if digest(solver) != original['execution']['executable_sha256']:
            raise ValueError('Solver binary changed since original run')
        while not quality['iterative_converged']:
            index = len(chunks)
            chunk = work/f'chunk_{index}'
            chunk.mkdir()
            for name in ('mesh.su2','restart.dat'):
                shutil.copy2(work/name,chunk/name)
            (chunk/'case.cfg').write_text(cfg,encoding='ascii')
            remaining = int(timeout-(time.monotonic()-started))
            if remaining <= 0:
                raise TimeoutError('Continuation budget exhausted')
            execution = run_solver([solver,'case.cfg'],chunk,remaining,1)
            new = csv_rows(chunk/'history.csv')
            history.extend(new)
            quality = assess(history)
            for name in ('restart.dat','surface_flow.csv'):
                shutil.copy2(chunk/name,work/name)
            chunks.append(dict(raw_directory=str(chunk),rows=len(new),execution=execution,
                               config_sha256=digest(chunk/'case.cfg')))
            print(level,index,quality,flush=True)
        surface = csv_rows(work/'surface_flow.csv')
        yp = max(pick(r,'Y_Plus') for r in surface)
        result.update(status='COMPUTED' if yp <= 1 else 'UNCONVERGED',
                      quality=dict(quality,yplus_max=yp))
        result['metrics'].update(cl=pick(history[-1],'CL'),cd=pick(history[-1],'CD'),
                                 cm=pick(history[-1],'CMz'),cf_mean=pick(history[-1],'CD'))
        result['errors']['cf_mean'] = error(result['metrics']['cf_mean'],result['metrics']['cf_schlichting'])
    except Exception as exc:
        result.update(status='UNCONVERGED',reason=f'{type(exc).__name__}: {exc}',quality=quality)
    with (work/'history.csv').open('w',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=list(history[0]))
        writer.writeheader(); writer.writerows(history)
    (work/'case.cfg').write_text(cfg,encoding='ascii')
    for name in ('cf_mean','cd'):
        result['metrics'][name] = pick(history[-1],'CD')
    result['metrics'].update(cl=pick(history[-1],'CL'),cm=pick(history[-1],'CMz'))
    result['errors']['cf_mean'] = error(result['metrics']['cf_mean'],result['metrics']['cf_schlichting'])
    write_json(directory/f'{level}_surface.json',csv_rows(work/'surface_flow.csv'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax = plt.subplots()
    ax.plot([pick(r,'CD') for r in history])
    ax.axvline(original_history_length-1,color='gray',linestyle='--',label='original end')
    ax.set(xlabel='Cumulative solver iterations',ylabel='Cf mean'); ax.legend()
    fig.tight_layout(); fig.savefig(directory/f'{level}_plot.png',dpi=140); plt.close(fig)
    shutil.copy2(work/'case.cfg',directory/f'{level}_case.cfg')
    result.update(raw_directory=str(work),restart_chain=chunks,
                  original_result=original,original_result_sha256=digest(original_path),
                  original_history_sha256=digest(source/'history.csv'),
                  original_history_rows=original_history_length,
                  original_restart_sha256=digest(source/'restart.dat'),
                  solver_code_sha256=original['code_sha256'],
                  postprocessing_note='code_sha256 below identifies current reassessment/continuation code; original solver-generation provenance is preserved in original_result/solver_code_sha256.',
                  continuation_elapsed_s=time.monotonic()-started)
    # Track the postprocessing workflow separately from the retained original.
    result['code_sha256'] = {str(p.relative_to(ROOT)):digest(p) for p in
                             (ROOT/'cfd/continue_flatplate.py',ROOT/'cfd/convergence.py',ROOT/'validation/study.py',ROOT/'validation/convergence.py')}
    for name in ('surface_flow.csv','history.csv'):
        result[name+'_sha256'] = digest(work/name)
    write_json(original_path,result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--solver',required=True)
    p.add_argument('--timeout',type=int,default=7200)
    a = p.parse_args()
    if not 0 < a.timeout <= 7200:
        p.error('timeout must be <=7200')
    results = []
    for level in ('coarse','medium','fine'):
        try:
            results.append(process(level,a.solver,a.timeout))
        except Exception as exc:
            # An unusable/missing restart must not erase a previous failure.
            failure = dict(status='FAILED',level=level,reason=f'{type(exc).__name__}: {exc}')
            write_json(ROOT/f'validation/results/flat_plate_SA/{level}_continuation_failure.json',failure)
            results.append(failure)
            print(failure,flush=True)
    print(save_study(ROOT/'validation/results/flat_plate_SA')['status'])
    return int(any(r['status'] != 'COMPUTED' for r in results))


if __name__ == '__main__': sys.exit(main())
