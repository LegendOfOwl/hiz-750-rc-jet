"""Yalnız coarse DRAFT: basitleştirilmiş dış zarf ve izole kanal fluid STEP'i.

Kanat/kuyruk kesiti dörtgen, gövde konik-silindirik; tasarım CFD'si değildir.
Kanal CAD raporundan 16 kenarlı kesit loft'u; dış sınır tabaka yutulması yoktur.
"""
import argparse
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from validation.common import read_json,write_json,digest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("case",choices=("aircraft","inlet"))
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    import gmsh
    import params as P
    a.output.mkdir(parents=True,exist_ok=True)
    gmsh.initialize()
    try:
        gmsh.model.add(a.case+"_DRAFT")
        occ=gmsh.model.occ
        def wire(points):
            pts=[occ.addPoint(*v) for v in points]
            return occ.addWire([occ.addLine(pts[i],pts[(i+1)%len(pts)]) for i in range(len(pts))])
        if a.case=="inlet":
            report=read_json(ROOT/"cad/out/cad_report.json")
            wires=[]
            for sec in report["inlet"]["sections"]:
                x,z,ra,rb=[sec[k]/1000 for k in ("x","zc","a","b")]
                points=[]
                for i in range(16):
                    th=2*math.pi*i/16
                    if sec["kind"]=="r":
                        scale=max(abs(math.cos(th)),abs(math.sin(th)))
                    else: scale=1
                    points.append((x,ra*math.cos(th)/scale,z+rb*math.sin(th)/scale))
                wires.append(wire(points))
            volume=occ.addThruSections(wires,makeSolid=True,makeRuled=False)
            limits=None
        else:
            r=P.FUSELAGE["d_max"]/2
            bodies=[(3,occ.addCone(0,0,0,.25,0,0,0,r)),
                    (3,occ.addCylinder(.25,0,0,1.2,0,0,r)),
                    (3,occ.addCone(1.45,0,0,P.FUSELAGE["length"]-1.45,0,0,r,P.FUSELAGE["d_tail"]/2))]
            def horizontal(surface):
                g=P.surface_geom(surface)
                wires=[]
                for y,c in ((0,g["cr"]),(g["b"]/2,g["ct"])):
                    x=surface["x_root_le"]+y*math.tan(math.radians(surface["sweep_le"]))
                    z=surface["z_root"]
                    t=surface.get("tc_root",surface.get("tc",.06))*c
                    wires.append(wire([(x,y,z-t/2),(x+c,y,z-t/2),(x+c,y,z+t/2),(x,y,z+t/2)]))
                return occ.addThruSections(wires,makeSolid=True)
            bodies+=horizontal(P.WING)+horizontal(P.HTAIL)
            v=P.VTAIL; g=P.vtail_geom()
            wires=[]
            for z,c in ((v["z_root"],g["cr"]),(v["z_root"]+g["h"],g["ct"])):
                x=v["x_root_le"]+(z-v["z_root"])*math.tan(math.radians(v["sweep_le"]))
                t=v["tc"]*c
                wires.append(wire([(x,-t/2,z),(x+c,-t/2,z),(x+c,t/2,z),(x,t/2,z)]))
            bodies+=occ.addThruSections(wires,makeSolid=True)
            solid,_=occ.fuse([bodies[0]],bodies[1:])
            limits=(-5,8,0,5,-5,5)
            box=occ.addBox(-5,0,-5,13,5,10)
            volume,_=occ.cut([(3,box)],solid)
        occ.synchronize()
        if len(volume)!=1: raise RuntimeError("Tek fluid hacmi oluşmadı")
        gmsh.write(str(a.output/"fluid.step"))
        # STEP round-trip yüzey tag'lerini yeniden numaralayabilir. Map'i export
        # öncesindeki OCC tag'lerinden değil, runner'ın okuyacağı STEP'ten çıkar.
        gmsh.clear()
        gmsh.model.add(a.case+"_roundtrip")
        occ=gmsh.model.occ
        occ.importShapes(str(a.output/"fluid.step"))
        occ.synchronize()
        volume=gmsh.model.getEntities(3)
        markers={}
        for dim,tag in gmsh.model.getBoundary(volume,oriented=False):
            b=gmsh.model.getBoundingBox(dim,tag)
            if a.case=="inlet":
                lo=P.INLET["x_lip"]; hi=P.ENGINE["x_front"]
                name="INLET" if abs(b[0]-lo)<1e-5 and abs(b[3]-lo)<1e-5 else "ENGINE" if abs(b[0]-hi)<1e-5 and abs(b[3]-hi)<1e-5 else "WALL"
            elif abs(b[1])<1e-5 and abs(b[4])<1e-5: name="SYMMETRY"
            elif any(abs(b[k]-v)<1e-5 and abs(b[k+3]-v)<1e-5 for k,v in ((0,-5),(0,8),(1,5),(2,-5),(2,5))): name="FARFIELD"
            else: name="WALL"
            markers.setdefault(name,[]).append(tag)
        write_json(a.output/"markers.json",markers)
        write_json(ROOT/"cfd/results"/(a.case+"_draft.json"),dict(status="GEOMETRY_DRAFT_ONLY",fluid_step_sha256=digest(a.output/"fluid.step"),
                   markers=markers,raw_directory=str(a.output),boundary_layers=False,design_accepted=False,
                   limitations=__doc__))
    finally: gmsh.finalize()


if __name__=="__main__": main()
