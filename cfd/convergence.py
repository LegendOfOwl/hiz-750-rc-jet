"""Reviewer-authorized QoI/residual-drop gate; energy is informational."""
import math


def assess(rows, model='SA'):
    from cfd.cases import pick
    if len(rows) < 101:
        return dict(iterative_converged=False, reason='101 history rows required')
    q = [pick(r,'CD','Drag') for r in rows[-101:]]
    denominator = sum(abs(v) for v in q[1:])
    cauchy = sum(abs(b-a) for a,b in zip(q,q[1:]))/denominator if denominator else None
    fields = ('rms[Rho]','rms[nu]') if model == 'SA' else ('rms[Rho]','rms[k]','rms[omega]')
    drops = {name: pick(rows[0],name)-pick(rows[-1],name) for name in fields}
    residuals = {k:v for k,v in rows[-1].items() if k.strip().lower().startswith('rms')}
    return dict(iterative_converged=all(math.isfinite(v) for v in residuals.values()) and cauchy is not None and cauchy < 1e-6 and min(drops.values()) >= 4,
                drag_relative_cauchy_100=cauchy,residual_drop_decades=drops,
                final_log_residuals=residuals,
                max_log_residual=max(residuals.values()),
                gate='mean absolute CD step / mean absolute CD < 1e-6 over last 100 steps; rho and turbulence residual drop >=4 decades from iteration 0; energy informational')
