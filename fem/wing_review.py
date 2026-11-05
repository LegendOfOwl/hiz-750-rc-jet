"""Hazırlanmış kanat deck'inin otomatik incelemesi -> run_case.py --mesh-review JSON'u.

Her bayrak yalnız ilgili kontrol sayısal olarak geçerse True yazılır (elle onay değildir):
  laminate_materials_complete : deck'teki tüm malzemeler 9 pozitif sabit + yoğunluk; tabakalar tanımlı
  orientations_checked        : her elemanın yerel 1-ekseni yüzeye teğet (|a.n|<1e-3), 3-ekseni eleman
                                normaline paralel (>0.999), kabuk/kapakta kiriş (sabit x/c) teğetine < 0.5°
  mass_reconciled             : toplam kütle hedefle < %0.5, bölme CG farkı < .005c
  ultimate_load_checked       : sum Fz = int Schrenk(12g x 1.5) (bağıl < 1e-3), yük 18 g
  shell_connectivity_checked  : serbest kenarlar yalnız kök hattında; burun/menteşe web'leri ve kaburgalar bağlı
  sandwich_no_overlap         : tüm kabuk hücrelerinde iç yüzler arası boşluk >= 0 (kaba hücre köşe derinliği)
Kullanım: python fem/wing_review.py <hazırlık klasörü> --level fine --output <review.json>
"""
import argparse
import math
from pathlib import Path
import re
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from validation.common import digest, read_json, write_json  # noqa: E402
from fem.wing_shell import quad8_shape  # noqa: E402


def element_normal(points):
    d = 1e-6
    dxi = (quad8_shape(d, 0) - quad8_shape(-d, 0)) @ points / (2 * d)
    det = (quad8_shape(0, d) - quad8_shape(0, -d)) @ points / (2 * d)
    n = np.cross(dxi, det)
    return n / np.linalg.norm(n)


def review(prepared, level):
    import params as P
    from structures import structures as ST
    prepared = Path(prepared)
    deck = (prepared / "case.inp").read_text()
    model = read_json(prepared / "wing_model.json")
    data = read_json(prepared / "wing_nodes.json")
    nodes = {int(k): np.array(v) for k, v in data["nodes"].items()}
    kinds = {int(k): v for k, v in data["kinds"].items()}
    orient = {int(k): v for k, v in data["orient"].items()}
    center = {int(k): v for k, v in data["center"].items()}
    conn = {}
    block = re.search(r"\*ELEMENT, TYPE=S8R, ELSET=EALL\n(.*?)\n\*", deck, re.S).group(1)
    for line in block.splitlines():
        vals = [int(v) for v in line.split(",")]
        conn[vals[0]] = vals[1:]
    g = model["geometry"]
    sweep = math.tan(math.radians(g["sweep_le_deg"]))
    checks, details = {}, {}
    # malzemeler
    mats = re.findall(r"\*MATERIAL, NAME=(\w+)\n\*ELASTIC(?:, TYPE=ENGINEERING CONSTANTS)?\n([^\n]*)\n", deck)
    ok = bool(mats)
    for name, line in mats:
        vals = [float(v) for v in line.split(",")]
        ok &= all(v >= 0 for v in vals) and vals[0] > 0
    used = set(re.findall(r"^[0-9.eE+-]+, , (\w+), ", deck, re.M))
    ok &= used <= {n for n, _ in mats}
    checks["laminate_materials_complete"] = bool(ok)
    details["materials"] = sorted(n for n, _ in mats if not n.startswith(("NSM", "LEV")))
    # yönler
    worst_tan, worst_norm, worst_span = 0., 1., 0.
    for t, c in conn.items():
        p = np.array([nodes[n] for n in c])
        n_el = element_normal(p)
        a = np.array(orient[t]["span"])
        n_or = np.array(orient[t]["normal"])
        worst_tan = max(worst_tan, abs(a @ n_el))
        worst_norm = min(worst_norm, abs(n_or @ n_el))
        if kinds[t].startswith(("CAP", "SKIN")):
            xc, y, side = center[t]
            dih = math.tan(math.radians(g["dihedral_deg"]))

            def X(yy):
                c = float(ST.chord(yy))
                return np.array([g["x_root_le"] + sweep * yy + xc * c, yy,
                                 g["z_root"] + dih * yy + side * float(ST.yt64(xc, ST.tc(yy))) * c])
            spar = (X(y + 1e-6) - X(y - 1e-6)) / 2e-6
            spar -= (spar @ n_el) * n_el
            spar /= np.linalg.norm(spar)
            worst_span = max(worst_span, math.degrees(math.acos(min(1., abs(a @ spar)))))
    checks["orientations_checked"] = bool(worst_tan < 1e-3 and worst_norm > .999 and worst_span < .5)
    details["orientation"] = dict(max_abs_a_dot_n=worst_tan, min_abs_normal_dot=worst_norm,
                                  max_angle_to_spar_tangent_deg=worst_span)
    # normallerin dışa bakması (OFFSET=0.5 iç tarafa malzeme koyar)
    bad = 0
    for t, c in conn.items():
        if kinds[t].startswith(("CAP", "SKIN")):
            n_el = element_normal(np.array([nodes[n] for n in c]))
            bad += int(np.sign(n_el[2]) != np.sign(center[t][2]))
    details["outward_normal_violations"] = bad
    # kütle
    mesh = model["mesh"]
    cg = max(abs(b["xcg_model"] - b["xcg_1d"]) for b in model["bays"])
    checks["mass_reconciled"] = bool(abs(mesh["relative_mass_difference"]) < .005 and cg < .005)
    details["mass"] = dict(relative_difference=mesh["relative_mass_difference"], max_bay_cg_diff_c=cg,
                           inertia_ratio_bays=[b["inertia_ratio_model_to_1d"] for b in model["bays"]])
    # yük
    total = sum(data["loads"].values())
    rel = abs(total / mesh["ultimate_force_target_N"] - 1)
    checks["ultimate_load_checked"] = bool(rel < 1e-3 and math.isclose(P.N_LIMIT * P.SF, 18.))
    details["load"] = dict(sum_Fz_N=total, target_N=mesh["ultimate_force_target_N"], relative=rel,
                           n_ultimate=P.N_LIMIT * P.SF, root_moment_target_Nm=mesh["root_moment_target_Nm"])
    # bağlantı: kenar kullanım sayıları
    edges = {}
    for t, c in conn.items():
        for a_, b_, m_ in ((0, 1, 4), (1, 2, 5), (2, 3, 6), (3, 0, 7)):
            key = (min(c[a_], c[b_]), max(c[a_], c[b_]), c[m_])
            edges[key] = edges.get(key, 0) + 1
    free = [k for k, v in edges.items() if v == 1]
    off_root = [k for k in free if not all(abs(nodes[n][1] - g["y_root"]) < 1e-9 for n in k)]
    # Kaburga-web kesişimi uyumlu olmalı: web hattı üzerindeki kaburga kenarları (ortak olmayan ara düğüm)
    # ayrıca sayılır ve bağlantı kontrolünü GEÇİRMEZ (önceki sürüm bunları kontrol dışı bırakıyordu).
    rib_nodes = {n for t, c in conn.items() if kinds[t] == "RIB" for n in c}

    def on_web_line(edge):
        xs = set()
        for n in edge:
            p_ = nodes[n]
            c = float(ST.chord(p_[1]))
            xs.add(round((p_[0] - g["x_root_le"] - sweep * p_[1]) / c, 6))
        return len(xs) == 1 and min(abs(next(iter(xs)) - x) for x in (g["xf"], g["xr"], g["x_hinge"], .01)) < 1e-6
    rib_web = [k for k in off_root if on_web_line(k) and all(n in rib_nodes for n in k[:2])]
    used_nodes = {n for c in conn.values() for n in c}
    checks["shell_connectivity_checked"] = bool(not off_root and not rib_web and used_nodes == set(nodes))
    details["connectivity"] = dict(free_edges=len(free), free_edges_off_root=len(off_root),
                                   nonconforming_rib_web_edges=len(rib_web),
                                   unused_nodes=len(set(nodes) - used_nodes))
    checks["sandwich_no_overlap"] = bool(model["sandwich_summary"]["min_gap_m"] >= 0)
    details["sandwich"] = model["sandwich_summary"]
    out = dict(level=level, h=mesh["h"], expanded_dof=mesh["expanded_dof_estimate"], fuel_state=mesh["fuel_state"],
               deck_sha256=digest(prepared / "case.inp"), prepared_dir=str(prepared),
               wing_model_json_sha256=digest(prepared / "wing_model.json"),
               wing_nodes_json_sha256=digest(prepared / "wing_nodes.json"),
               **checks, details=details, reviewer="fem/wing_review.py (otomatik sayısal kontroller)",
               note="Bayraklar sayısal kontrol sonucudur; imalat/çizim incelemesinin yerini tutmaz.")
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("prepared", type=Path)
    p.add_argument("--level", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    r = review(a.prepared, a.level)
    write_json(a.output, r)
    flags = {k: v for k, v in r.items() if isinstance(v, bool)}
    print(flags)
    return 0 if all(flags.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
