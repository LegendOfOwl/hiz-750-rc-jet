"""Four transfinite quad blocks, conformal wake seam, 30-chord C boundary."""
import math

from validation.common import Blocked, digest, write_json
from cfd.mesh_audit import audit


def generate(args, work, xy, source):
    import gmsh
    factor = (1, 1.5, 2)[('coarse','medium','fine').index(args.level)]
    if math.dist(xy[0], xy[-1]) > 1e-8:
        raise Blocked('C-grid requires a closed sharp trailing edge; geometry is not modified silently.')
    xy = xy[:-1]
    ile = min(range(len(xy)), key=lambda i: xy[i][0])
    write_json(work/'geometry.json', xy+[xy[0]])
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.NumThreads', args.threads)
        gmsh.model.add('c_grid')
        g = gmsh.model.geo
        pts = [g.addPoint(x,y,0) for x,y in xy]
        upper = g.addSpline(pts[:ile+1])  # TE -> LE
        lower = g.addSpline(pts[ile:]+[pts[0]])  # LE -> TE
        te, le = pts[0], pts[ile]
        cx, cy = xy[0]
        top = g.addPoint(cx,cy+30,0)
        front = g.addPoint(cx-30,cy,0)
        bottom = g.addPoint(cx,cy-30,0)
        end = g.addPoint(cx+30,cy,0)
        endtop = g.addPoint(cx+30,cy+30,0)
        endbottom = g.addPoint(cx+30,cy-30,0)
        arcup = g.addCircleArc(top,te,front)
        arclow = g.addCircleArc(front,te,bottom)
        radialup = g.addLine(te,top)
        radialle = g.addLine(le,front)
        radiallow = g.addLine(te,bottom)
        wake = g.addLine(te,end)
        aftup = g.addLine(end,endtop)
        aftlow = g.addLine(end,endbottom)
        topwake = g.addLine(top,endtop)
        bottomwake = g.addLine(bottom,endbottom)
        loops = [[upper,radialle,-arcup,-radialup],
                 [lower,radiallow,-arclow,-radialle],
                 [wake,aftup,-topwake,-radialup],
                 [radiallow,bottomwake,-aftlow,-wake]]
        loops[:2] = [[-c for c in reversed(loop)] for loop in loops[:2]]
        surfaces = [g.addPlaneSurface([g.addCurveLoop(loop)]) for loop in loops]
        for c in (upper,lower,arcup,arclow):
            g.mesh.setTransfiniteCurve(c,int(128*factor)+1,'Bump',.08)
        for c in (wake,topwake,bottomwake):
            g.mesh.setTransfiniteCurve(c,int(48*factor)+1,'Progression',1.12**(1/factor))
        n = int(96*factor)
        first = 2e-6/factor
        lo,hi = 1.,2.
        for _ in range(80):
            r = (lo+hi)/2
            if 30*(r-1)/(r**n-1) > first: lo=r
            else: hi=r
        for c in (radialup,radialle,radiallow,aftup,aftlow):
            g.mesh.setTransfiniteCurve(c,n+1,'Progression',(lo+hi)/2)
        for s in surfaces:
            g.mesh.setTransfiniteSurface(s)
            g.mesh.setRecombine(2,s)
        g.synchronize()
        gmsh.model.addPhysicalGroup(1,[upper,lower],name='WALL')
        gmsh.model.addPhysicalGroup(1,[arcup,arclow,topwake,bottomwake,aftup,aftlow],name='FARFIELD')
        gmsh.model.addPhysicalGroup(2,surfaces,name='FLUID')
        gmsh.model.mesh.generate(2)
        gmsh.write(str(work/'mesh.su2'))
        gmsh.write(str(work/'mesh.msh'))
        info = audit(work/'mesh.su2')
        if info['nonpositive_cells'] or info['nonpositive_corners'] or info['boundary_mismatches'] or info['nonmanifold_edges']:
            raise Blocked('Invalid C-grid orientation/connectivity: '+str(info))
        info.update(dimension=2,h=1/math.sqrt(info['cells']),first_layer_m=first,
                    radial_growth=(lo+hi)/2,source=source,mesh_sha256=digest(work/'mesh.su2'),
                    topology='four-block transfinite C-grid, shared wake',
                    yplus_status='Actual solution y+ required')
        write_json(work/'mesh.json',info)
        return info
    finally:
        gmsh.finalize()
