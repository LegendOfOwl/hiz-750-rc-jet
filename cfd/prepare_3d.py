"""Temiz FLUID STEP hacmini gmsh ile incele/ön ağla; duvar katmanını doğrulamaz.

Montaj STEP'i akış hacmi değildir. Katılar/duvar kalınlıkları otomatik olarak akış bölgesine çevrilmez.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from validation.common import Blocked, digest, read_json, write_json, require_module


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("step", type=Path, help="Tek kapalı akış hacmi, uçak katısı değil")
    p.add_argument("--output", type=Path, required=True, help="Kısa ASCII klasör")
    p.add_argument("--scale", type=float, required=True, help="STEP mm ise .001, m ise 1")
    p.add_argument("--markers", type=Path, help="Fiziksel ad -> yüzey tag listesi JSON")
    p.add_argument("--level", choices=("coarse", "medium", "fine"), default="coarse")
    p.add_argument("--size", type=float, default=.04, help="Kaba en büyük hücre boyu [m]")
    a = p.parse_args()
    require_module("gmsh")
    import gmsh
    a.output.mkdir(parents=True, exist_ok=True)
    gmsh.initialize()
    try:
        gmsh.model.add("fluid")
        occ = gmsh.model.occ
        occ.importShapes(str(a.step.resolve()))
        volumes = occ.getEntities(3)
        if len(volumes) != 1:
            raise Blocked("Tek temiz akış hacmi gerekli; tüm montajı hacim ağına çevirmeyin.")
        occ.dilate(volumes, 0, 0, 0, a.scale, a.scale, a.scale)
        occ.synchronize()
        surfaces = gmsh.model.getBoundary(volumes, oriented=False)
        write_json(a.output / "surfaces.json", {str(tag): list(gmsh.model.getBoundingBox(2, tag)) for dim, tag in surfaces})
        if not a.markers:
            print("Yüzey envanteri yazıldı; fiziksel grupları --markers ile verin.")
            return
        groups = read_json(a.markers)
        tags = [int(t) for values in groups.values() for t in values]
        if set(tags) != {t for _, t in surfaces} or len(tags) != len(set(tags)):
            raise Blocked("Her sınır yüzeyi tam bir fiziksel gruba atanmalı.")
        for name, values in groups.items():
            gmsh.model.addPhysicalGroup(2, values, name=name)
        gmsh.model.addPhysicalGroup(3, [volumes[0][1]], name="FLUID")
        size = a.size / 1.5 ** ("coarse", "medium", "fine").index(a.level)
        box = gmsh.model.getBoundingBox(3, volumes[0][1])
        far_size = max(size*10, max(box[i+3]-box[i] for i in range(3))/10)
        # Uzak alanı duvar boyuyla doldurmak milyarlarca hücre üretebilir.
        # Bu yalnız boyut alanıdır, duvar-normal prizma katmanı değildir.
        if not groups.get("WALL"):
            raise Blocked("WALL yüzey grubu gerekli.")
        distance = gmsh.model.mesh.field.add("Distance")
        gmsh.model.mesh.field.setNumbers(distance,"SurfacesList",groups["WALL"])
        threshold = gmsh.model.mesh.field.add("Threshold")
        for key,value in (("InField",distance),("SizeMin",size),("SizeMax",far_size),
                          ("DistMin",size*2),("DistMax",max(.5,far_size))):
            gmsh.model.mesh.field.setNumber(threshold,key,value)
        gmsh.model.mesh.field.setAsBackgroundMesh(threshold)
        gmsh.option.setNumber("Mesh.MeshSizeFromPoints",0)
        gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary",0)
        gmsh.option.setNumber("Mesh.MeshSizeMax", far_size)
        gmsh.option.setNumber("Mesh.MeshSizeMin", size)
        gmsh.option.setNumber("General.NumThreads", 4)
        gmsh.model.mesh.generate(3)
        _, es, _ = gmsh.model.mesh.getElements(3)
        cells = sum(len(e) for e in es)
        gmsh.write(str(a.output / "draft.msh"))
        if cells <= 2_000_000:
            gmsh.write(str(a.output / "draft.su2"))
        write_json(a.output / "draft.json", dict(status="DRAFT_NOT_RANS_READY", cells=cells,
                   step_sha256=digest(a.step), units_m=True, boundary_layers=False,
                   note="İzotrop tetra ön ağ. RANS için y+~1 prizmatik duvar katmanı ayrıca üretilmeli/denetlenmeli. 2M aşılırsa SU2 mesh yazılmaz."))
    finally:
        gmsh.finalize()


if __name__ == "__main__":
    main()
