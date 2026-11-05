"""Dependency-free SU2 2D topology/spacing audit; no solver acceptance implied."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path


def audit(path):
    lines = iter(Path(path).read_text().splitlines())
    cells, points, markers = [], {}, {}
    for line in lines:
        if '=' not in line:
            continue
        key, value = map(str.strip, line.split('=', 1))
        if key == 'NDIME' and int(value) != 2:
            raise ValueError('Only 2D meshes supported')
        if key == 'NELEM':
            for _ in range(int(value)):
                row = list(map(int, next(lines).split()))
                n = {5: 3, 9: 4}[row[0]]
                cells.append((row[0], row[1:1+n]))
        elif key == 'NPOIN':
            for i in range(int(value.split()[0])):
                row = next(lines).split()
                # Some official 2D meshes retain a zero z column before ID.
                points[int(row[-1]) if len(row) > 2 else i] = tuple(map(float, row[:2]))
        elif key == 'MARKER_TAG':
            count = int(next(lines).split('=')[1])
            markers[value] = [list(map(int, next(lines).split()))[1:3] for _ in range(count)]
    areas = []
    corner_sines = []
    edges = Counter()
    for _, ids in cells:
        xy = [points[i] for i in ids]
        areas.append(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(xy, xy[1:]+xy[:1]))/2)
        for i,b in enumerate(xy):
            a,c = xy[i-1],xy[(i+1)%len(xy)]
            ux,uy = b[0]-a[0],b[1]-a[1]
            vx,vy = c[0]-b[0],c[1]-b[1]
            norm = math.hypot(ux,uy)*math.hypot(vx,vy)
            corner_sines.append((ux*vy-uy*vx)/norm if norm else 0.)
        edges.update(tuple(sorted((a,b))) for a,b in zip(ids, ids[1:]+ids[:1]))
    boundary = Counter(tuple(sorted(e)) for values in markers.values() for e in values)
    xs = sorted(set(p[0] for p in points.values()))
    ys = sorted(set(p[1] for p in points.values()))
    wall_ids = {i for name, es in markers.items() if name.lower() in ('wall','airfoil') for e in es for i in e}
    wall_steps = [math.dist(points[a],points[b]) for a,b in edges
                  if (a in wall_ids) != (b in wall_ids) and edges[(a,b)] == 2]
    return dict(path=str(path), cells=len(cells), nodes=len(points),
                element_types=dict(Counter(t for t,_ in cells)), minimum_signed_area=min(areas),
                nonpositive_cells=sum(a <= 0 for a in areas),
                minimum_corner_sine=min(corner_sines),
                nonpositive_corners=sum(s <= 0 for s in corner_sines),
                nonmanifold_edges=sum(n > 2 for n in edges.values()),
                boundary_mismatches=sum(boundary[e] != 1 for e,n in edges.items() if n == 1)
                    + sum(edges[e] != 1 for e in boundary),
                markers={k: len(v) for k,v in markers.items()},
                bounds=[min(xs),max(xs),min(ys),max(ys)],
                unique_x=len(xs), unique_y=len(ys),
                first_y_values=ys[:6], last_y_values=ys[-4:],
                minimum_wall_connected_edge=min(wall_steps) if wall_steps else None)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('meshes', nargs='+', type=Path)
    a = p.parse_args()
    print(json.dumps([audit(m) for m in a.meshes], indent=2))
