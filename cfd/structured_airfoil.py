"""Single-block structured C-grid for sharp-TE airfoils (iter5 v2).

Wall-normal marching from the C-curve (lower wake -> airfoil -> upper wake)
with smoothed marching directions, geometric layer growth and a ~100c far
field.  Replaces the four-block transfinite 30c grid whose TFI lines left the
wall obliquely (minimum corner sine .277) and whose far field was 3x smaller
than the official SU2 RAE2822 mesh (+/-100c).

Pure numpy; SU2 ASCII mesh is written directly (no gmsh dependency).
Coarse/medium/fine share the same mapping functions; all index counts and
spacings scale with factor 1/1.5/2 (h ratios 1.5/1.333).
"""
import math

from validation.common import Blocked, digest, write_json
from cfd.mesh_audit import audit

# Coarse-level design values; finer levels divide spacings / multiply counts.
FARFIELD_C = 100.0      # wall-to-far-field marching distance and wake length [c]
SURFACE_CELLS = 128     # per side (lower, upper)
WAKE_CELLS = 48
NORMAL_CELLS = 96
FIRST_LAYER = 2e-6      # [c]; Re=6.5e6, Cf~.003-.006 -> y+ ~.5-.7 on coarse
LE_SPACING = 1e-3       # surface arc spacing at LE [c]
TE_SPACING = 4e-3       # surface arc spacing at TE = first wake cell [c]
WAKE_FAN_DEG = 45.0    # wake/outlet ray tilt at the downstream end
SMOOTHING_PASSES = 150  # coarse ray-angle smoothing passes (x factor**2; monotone)
# Wake-cut normal spacing (iter5 v3).  The v2 grid kept the wall spacing 2e-6c on
# both sides of the wake cut up to 100c (streamwise 0.004-15c -> aspect ratio
# 1e3-1e7); the residual peaks of the unconverged MG0 run sat on that cut at
# x~1.2-2c.  The wake first spacing a_k now ramps from the wall value by at most
# WAKE_RAMP per wake cell (WAKE_RAMP**(1/factor) on finer levels) towards
# ds_k/WAKE_ASPECT and is blended into the unchanged geometric layer series:
# d_j = d0_j + j*(a_k-first) (first cell a_k; spacing growth stays <= the wall
# series ratio).  The added offset varies slowly between neighbouring rays, so the
# j-lines do not tilt near the TE (an earlier per-ray geometric series did: .20).
WAKE_ASPECT = 100.0     # target streamwise/normal spacing ratio on the wake cut
WAKE_RAMP = 1.5         # max growth of the wake first spacing per wake cell (coarse)


def geometric_ratio(first, length, n):
    """r with first*(r**n-1)/(r-1) == length."""
    if first*n >= length:
        raise Blocked('Spacing too large for requested length')
    lo, hi = 1.0+1e-12, 2.0
    for _ in range(200):
        r = (lo+hi)/2
        if first*(r**n-1)/(r-1) < length: lo = r
        else: hi = r
    return (lo+hi)/2


def two_sided(n, ds0, ds1):
    """Vinokur tanh distribution on [0,1] with end spacings ds0, ds1 (normalized)."""
    import numpy as np
    b = 1/(n*math.sqrt(ds0*ds1))
    if b <= 1:
        raise Blocked('Requested end spacings too coarse for two-sided stretching')
    lo, hi = 1e-9, 50.
    for _ in range(200):
        dy = (lo+hi)/2
        if math.sinh(dy)/dy < b: lo = dy
        else: hi = dy
    dy = (lo+hi)/2
    a = math.sqrt(ds1/ds0)
    u = np.arange(n+1)/n
    t = .5*(1+np.tanh(dy*(u-.5))/math.tanh(dy/2))
    s = t/(a+(1-a)*t)
    s[0], s[-1] = 0., 1.
    return s


def surface_points(xy, factor):
    """Lower TE->LE and upper LE->TE points from the Selig contour (TE-upper first)."""
    import numpy as np
    from scipy.interpolate import CubicSpline
    pts = np.asarray(xy+[xy[0]], float)
    chord = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
    ile = int(np.argmin(pts[:, 0]))
    spline = CubicSpline(chord, pts)
    def side(t0, t1, n):
        t = np.linspace(t0, t1, 20001)
        p = spline(t)
        arc = np.r_[0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))]
        return t, p, arc
    out = []
    for t0, t1, ds0, ds1 in ((chord[-1], chord[ile], TE_SPACING, LE_SPACING),   # lower TE->LE
                             (chord[ile], 0., LE_SPACING, TE_SPACING)):      # upper LE->TE
        t, p, arc = side(t0, t1, None)
        n = int(SURFACE_CELLS*factor)
        s = two_sided(n, ds0/factor/arc[-1], ds1/factor/arc[-1])*arc[-1]
        out.append(np.column_stack([np.interp(s, arc, p[:, 0]), np.interp(s, arc, p[:, 1])]))
    lower, upper = out
    lower[0] = upper[-1] = pts[0]
    lower[-1] = upper[0] = pts[ile]
    return lower, upper


def build(xy, factor):
    """Return (X[j,i], Y[j,i], info) for the C-grid; i along C-curve, j off-wall."""
    import numpy as np
    lower, upper = surface_points(xy, factor)
    te = lower[0]
    nw, nj = int(WAKE_CELLS*factor), int(NORMAL_CELLS*factor)
    first = FIRST_LAYER/factor
    wr = geometric_ratio(TE_SPACING/factor, FARFIELD_C, nw)
    wake_x = te[0]+np.r_[0, np.cumsum((TE_SPACING/factor)*wr**np.arange(nw))]
    wake = np.column_stack([wake_x, np.full(nw+1, te[1])])
    curve = np.vstack([wake[::-1], lower[1:], upper[1:], wake[1:]])
    count = len(curve)
    rr = geometric_ratio(first, FARFIELD_C, nj)
    distance = np.r_[0, np.cumsum(first*rr**np.arange(nj))]
    # Straight rays along wall normals whose angle is made monotone along the
    # C-curve (clockwise turning).  Monotone directions fan out and cannot
    # cross; in the concave TE notch / lower aft cusp the rays stay parallel
    # instead of converging (deviation from the true normal is a few degrees).
    tangent = np.empty_like(curve)
    tangent[1:-1] = curve[2:]-curve[:-2]
    tangent[0] = curve[1]-curve[0]; tangent[-1] = curve[-1]-curve[-2]
    angle = np.unwrap(np.arctan2(tangent[:, 0], -tangent[:, 1]))   # left normal (-ty, tx)
    angle += -math.pi/2-angle[0]
    ile = nw+len(lower)-1
    # Wake rays fan downstream (0 at TE -> WAKE_FAN_DEG at the outlet end) so the
    # wake columns widen with distance instead of staying TE-spacing wide up to
    # 100c (aspect ratio ~1e3-1e4 in the inviscid far field otherwise).
    fan = math.radians(WAKE_FAN_DEG)*np.arange(nw+1)/nw
    angle[:nw+1] = -math.pi/2+fan[::-1]
    angle[count-nw-1:] = -1.5*math.pi-fan
    angle[:ile+1] = np.minimum.accumulate(angle[:ile+1])
    angle[ile:] = np.maximum.accumulate(angle[ile:][::-1])[::-1]
    for _ in range(int(round(SMOOTHING_PASSES*factor**2))):
        angle[1:-1] = .5*angle[1:-1]+.25*(angle[:-2]+angle[2:])
    direction = np.column_stack([np.cos(angle), np.sin(angle)])
    # Per-ray layer distances; wake rays get the relaxed wake-cut spacing.
    D = np.repeat(distance[:, None], count, axis=1)
    te_ds = TE_SPACING/factor
    k = np.arange(nw+1)                       # wake node index from TE (k=0: TE)
    local_ds = te_ds*wr**np.maximum(k-1, 0)   # streamwise spacing of the cell ending at node k
    wake_first = np.minimum(first*WAKE_RAMP**(k/factor), first+(local_ds-te_ds)/WAKE_ASPECT)
    wake_first[0] = first
    jj = np.arange(nj+1)[:, None]
    wake_D = distance[:, None]+jj*(wake_first[None, :]-first)
    D[:, :nw+1] = wake_D[:, ::-1]             # lower wake: i=0 is the far end
    D[:, count-nw-1:] = wake_D                # upper wake: i=count-nw-1 is the TE
    X = curve[None, :, 0]+D*direction[None, :, 0]
    Y = curve[None, :, 1]+D*direction[None, :, 1]
    raw = np.arctan2(tangent[:, 0], -tangent[:, 1])
    deviation = np.abs(np.angle(np.exp(1j*(angle-raw))))
    info = dict(first_layer_m=first, radial_growth=rr, wake_growth=wr,
                surface_cells_per_side=int(SURFACE_CELLS*factor), wake_cells=nw, normal_cells=nj,
                le_spacing=LE_SPACING/factor, te_spacing=TE_SPACING/factor,
                farfield_distance_c=FARFIELD_C, wake_length_c=FARFIELD_C,
                wake_aspect_target=WAKE_ASPECT, wake_ramp=WAKE_RAMP,
                wake_first_spacing_end=float(wake_first[-1]),
                max_wall_ray_deviation_deg=float(np.degrees(deviation[nw:len(curve)-nw]).max()))
    return X, Y, nw, info


def write_su2(path, X, Y, nw):
    nj1, ni = X.shape
    I = ni-1
    ids = {}
    coords = []
    for j in range(nj1):
        for i in range(ni):
            if j == 0 and i >= I-nw:
                ids[(j, i)] = ids[(0, I-i)]   # upper wake cut == lower wake cut
                continue
            ids[(j, i)] = len(coords)
            coords.append((X[j, i], Y[j, i]))
    cells = [(ids[(j, i)], ids[(j, i+1)], ids[(j+1, i+1)], ids[(j+1, i)])
             for j in range(nj1-1) for i in range(I)]
    wall = [(ids[(0, i)], ids[(0, i+1)]) for i in range(nw, I-nw)]
    far = ([(ids[(nj1-1, i)], ids[(nj1-1, i+1)]) for i in range(I)]
           + [(ids[(j, 0)], ids[(j+1, 0)]) for j in range(nj1-1)]
           + [(ids[(j, I)], ids[(j+1, I)]) for j in range(nj1-1)])
    lines = ['NDIME= 2', f'NELEM= {len(cells)}']
    lines += [f'9 {a} {b} {c} {d} {k}' for k, (a, b, c, d) in enumerate(cells)]
    lines.append(f'NPOIN= {len(coords)}')
    lines += [f'{x:.15e} {y:.15e} {k}' for k, (x, y) in enumerate(coords)]
    lines += ['NMARK= 2', 'MARKER_TAG= WALL', f'MARKER_ELEMS= {len(wall)}']
    lines += [f'3 {a} {b}' for a, b in wall]
    lines += ['MARKER_TAG= FARFIELD', f'MARKER_ELEMS= {len(far)}']
    lines += [f'3 {a} {b}' for a, b in far]
    path.write_text('\n'.join(lines)+'\n', encoding='ascii')
    return len(cells)


def quality(X, Y):
    """Max adjacent-cell size ratios along j (wall normal) and i (C-line)."""
    import numpy as np
    dj = np.hypot(np.diff(X, axis=0), np.diff(Y, axis=0))
    di = np.hypot(np.diff(X, axis=1), np.diff(Y, axis=1))
    gj = dj[1:]/dj[:-1]
    gi = di[:, 1:]/di[:, :-1]
    gi = np.maximum(gi, 1/gi)
    # Cell aspect ratio (long side / short side, midline lengths).
    li = .5*(di[1:]+di[:-1])
    lj = .5*(dj[:, 1:]+dj[:, :-1])
    ar = np.maximum(li, lj)/np.minimum(li, lj)
    return dict(max_normal_growth=float(gj.max()), max_streamwise_growth=float(gi.max()),
                max_streamwise_growth_wall=float(gi[0].max()), max_aspect_ratio=float(ar.max()))


def generate(args, work, xy, source):
    factor = (1, 1.5, 2)[('coarse', 'medium', 'fine').index(args.level)]
    if math.dist(xy[0], xy[-1]) > 1e-8:
        raise Blocked('C-grid requires a closed sharp trailing edge; geometry is not modified silently.')
    xy = [tuple(p) for p in xy[:-1]]
    write_json(work/'geometry.json', xy+[xy[0]])
    X, Y, nw, info = build(xy, factor)
    write_su2(work/'mesh.su2', X, Y, nw)
    checks = audit(work/'mesh.su2')
    if checks['nonpositive_cells'] or checks['nonpositive_corners'] or checks['boundary_mismatches'] or checks['nonmanifold_edges']:
        raise Blocked('Invalid C-grid orientation/connectivity: '+str(checks))
    checks.update(info)
    checks.update(quality(X, Y))
    checks.update(dimension=2, h=1/math.sqrt(checks['cells']), source=source,
                  mesh_sha256=digest(work/'mesh.su2'),
                  topology='single-block C-grid, wall-normal marching, shared wake cut, ~100c far field',
                  yplus_status='Actual solution y+ required')
    write_json(work/'mesh.json', checks)
    return checks
