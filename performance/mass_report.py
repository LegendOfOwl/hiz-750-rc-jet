"""params.py kutle kalemlerinden kutle/CG tablosu (Markdown) ve CG zarfi grafigi uretir."""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import params as P  # noqa: E402

OUT = os.path.join(ROOT, "performance", "out")


def main():
    os.makedirs(OUT, exist_ok=True)
    wg = P.wing_geom()
    rows = ["| Kalem | Kutle [kg] | x [m] | z [m] | Moment [kg.m] |", "|---|---:|---:|---:|---:|"]
    for name, m, x, z in P.MASS_ITEMS:
        rows.append(f"| {name} | {m:.2f} | {x:.3f} | {z:.3f} | {m*x:.3f} |")
    rows.append(f"| Yakit ({P.FUEL['mass']/P.FUEL['density']:.1f} L) | {P.FUEL['mass']:.2f} | "
                f"{P.FUEL['x']:.3f} | {P.FUEL['z']:.3f} | {P.FUEL['mass']*P.FUEL['x']:.3f} |")
    full, empty = P.mass_summary(1.0), P.mass_summary(0.0)
    pct = lambda x: 100 * (x - wg["x_mac_le"]) / wg["mac"]
    rows.append(f"| **MTOW** | **{full['m']:.2f}** | **{full['x_cg']:.3f}** | {full['z_cg']:.3f} | |")
    rows.append("")
    rows.append(f"MAC = {wg['mac']:.3f} m, MAC hucum kenari x = {wg['x_mac_le']:.3f} m.  "
                f"CG tam yakit %{pct(full['x_cg']):.1f} MAC, yakitsiz %{pct(empty['x_cg']):.1f} MAC.")
    md = "\n".join(rows)
    with open(os.path.join(OUT, "kutle_tablosu.md"), "w", encoding="utf-8") as f:
        f.write(md + "\n")
    print(md)

    fr = [i / 20 for i in range(21)]
    ms = [P.mass_summary(f) for f in fr]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot([pct(m["x_cg"]) for m in ms], [m["m"] for m in ms], "o-", ms=3)
    ax.set_xlabel("CG [% MAC]")
    ax.set_ylabel("Kutle [kg]")
    ax.set_title("CG zarfi (yakit tuketimi boyunca)")
    ax.grid(alpha=.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "cg_zarfi.png"), dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    main()
