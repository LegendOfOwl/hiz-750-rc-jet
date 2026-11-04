"""Kanat rijitleştirme seçenek çalışması (S8R kabuk modeli, params değiştirilmeden).

Seçenekler fem/wing_shell.options() ortam değişkenleriyle geçirilir; her seçenek dolu+boş tank için
fem/run_wing_study.py ile (hazırla -> otomatik inceleme -> --deck, --threads 1, SPOOLES) koşulur.
  python fem/stiffening_study.py --level medium            # tüm seçenekler
  python fem/stiffening_study.py --level fine --only s41   # seçilenin ince ağ doğrulaması
Özet: fem/results/stiffening/summary_<level>.json ve .png
V_F: structures/out/fe_sonuclar.json gvt[dolu|bos].Vf_vs_fT üzerinde f_1T(kabuk)/f_1T(1D taban) ölçeği
(yalnız frekans ölçeklemesi; kütle/mod şekli değişimi içermez). Hedef: dolu f_1T >= 316 Hz (1350 km/h).
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from validation.common import read_json, write_json  # noqa: E402

VARIANTS = {
    "s31": dict(HZ750_SKIN_PLIES="3,1"),                       # taban (params)
    "s41": dict(HZ750_SKIN_PLIES="4,1"),
    "s51": dict(HZ750_SKIN_PLIES="5,1"),
    "s32": dict(HZ750_SKIN_PLIES="3,2"),
    "s42": dict(HZ750_SKIN_PLIES="4,2"),
    "s31w1": dict(HZ750_SKIN_PLIES="3,1", HZ750_WEB_EXTRA="1"),
    "s31r065": dict(HZ750_SKIN_PLIES="3,1", HZ750_RIB_PITCH="0.065"),
    "s41w1": dict(HZ750_SKIN_PLIES="4,1", HZ750_WEB_EXTRA="1"),
    "s41r065": dict(HZ750_SKIN_PLIES="4,1", HZ750_RIB_PITCH="0.065"),
    # Ek keşif (ana adaylar hedefe yetmezse sınırı görmek için)
    "s51w1r065": dict(HZ750_SKIN_PLIES="5,1", HZ750_WEB_EXTRA="1", HZ750_RIB_PITCH="0.065"),
    "s61": dict(HZ750_SKIN_PLIES="6,1"),
    "s31w2": dict(HZ750_SKIN_PLIES="3,1", HZ750_WEB_EXTRA="2"),
    "s31rp2": dict(HZ750_SKIN_PLIES="3,1", HZ750_RIB_PLIES="2"),
    "s31r043": dict(HZ750_SKIN_PLIES="3,1", HZ750_RIB_PITCH="0.043"),
    # Kombinasyonlar (tek kaldıraçlar hedefe yetmediği için)
    "s31r043w1": dict(HZ750_SKIN_PLIES="3,1", HZ750_RIB_PITCH="0.043", HZ750_WEB_EXTRA="1"),
    "s41r043": dict(HZ750_SKIN_PLIES="4,1", HZ750_RIB_PITCH="0.043"),
    "s41r043w1": dict(HZ750_SKIN_PLIES="4,1", HZ750_RIB_PITCH="0.043", HZ750_WEB_EXTRA="1"),
    "s51r043w1": dict(HZ750_SKIN_PLIES="5,1", HZ750_RIB_PITCH="0.043", HZ750_WEB_EXTRA="1"),
    "s41r043rp2w1": dict(HZ750_SKIN_PLIES="4,1", HZ750_RIB_PITCH="0.043", HZ750_RIB_PLIES="2", HZ750_WEB_EXTRA="1"),
    # Yalnız ince ağda temsil edilebilen sık kaburga (her ince şerit sınırı, 0.0216 m)
    "s31r022": dict(HZ750_SKIN_PLIES="3,1", HZ750_RIB_PITCH="0.0216"),
    "s41r022w1": dict(HZ750_SKIN_PLIES="4,1", HZ750_RIB_PITCH="0.0216", HZ750_WEB_EXTRA="1"),
}
F1T_TARGET = 316.0


def collect(name, level):
    from structures import structures as ST
    fe = read_json(ROOT / "structures/out/fe_sonuclar.json")["gvt"]
    row = dict(variant=name, env=VARIANTS[name], level=level)
    for fuel, key, folder in (("dolu", "full", f"wing_{name}"), ("bos", "empty", f"wing_empty_{name}")):
        r = read_json(ROOT / "fem/results/stiffening" / folder / f"{level}.json")
        if r["status"] != "REVIEW_REQUIRED":
            row[fuel] = dict(status=r["status"], reason=r.get("reason"))
            continue
        m, q = r["metrics"], r["quality"]
        ratio = m["f_1T_Hz"] / fe[fuel]["f1T"]
        vf = float(np.interp(ratio, fe[fuel]["fac"], fe[fuel]["Vf_vs_fT"])) if 0.7 <= ratio <= 1.5 else None
        modes = [(round(x["f_Hz"], 2), x["label"]) for x in q["modes"][:5]]
        row[fuel] = dict(f1B=m["f_1B_Hz"], f1T=m["f_1T_Hz"], f2B=m.get("f_2B_Hz"), modes=modes,
                         f1T_ratio_to_1D=ratio, Vf_kmh=vf, tip_deflection_m=m["tip_deflection_m"],
                         tsai_wu_R_ex_root=m["tsai_wu_R_min_ex_root"])
        if key == "full":
            mesh = q["model_mesh"]
            bays = q["bays"]
            mass = [b["m_struct_1d"] for b in bays]
            cg = sum(b["xcg_model"] * w for b, w in zip(bays, mass)) / sum(mass)
            y70 = .7 * ST.B2
            ybay = np.linspace(.035, ST.B2, 9)
            i70 = min(int((y70 - .035) / (ybay[1] - ybay[0])), 7)
            sp = [int(v) for v in VARIANTS[name]["HZ750_SKIN_PLIES"].split(",")]
            ws = ST.wing_section_model(*sp)["ws"]
            row.update(structural_half_mass_kg=mesh["structural_half_mass_kg"], n_ribs=mesh["n_ribs"],
                       xcg_shell_mass_weighted_c=cg, xcg_shell_eta70_c=bays[i70]["xcg_model"],
                       xcg_1D_eta70_c=float(np.interp(y70, ST.YS, ws["xcg"])),
                       option_extra_mass_kg=mesh["option_extra_mass_kg"])
    return row


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--level", default="medium", choices=("coarse", "medium", "fine"))
    p.add_argument("--only", nargs="*")
    p.add_argument("--collect-only", action="store_true")
    a = p.parse_args()
    names = a.only or list(VARIANTS)
    for name in names:
        if a.collect_only:
            break
        env = dict(os.environ, HZ750_VARIANT=name, PYTHONIOENCODING="utf-8")
        for k in ("HZ750_SKIN_PLIES", "HZ750_WEB_EXTRA", "HZ750_RIB_PITCH", "HZ750_RIB_PLIES"):
            env.pop(k, None)
        env.update(VARIANTS[name])
        subprocess.run([sys.executable, str(ROOT / "fem/run_wing_study.py"), "--levels", a.level], cwd=ROOT,
                       env=env, check=False, stdout=subprocess.DEVNULL)
    rows = [collect(n, a.level) for n in names]
    base = next((r for r in rows if r["variant"] == "s31"), None)
    for r in rows:
        if base and "structural_half_mass_kg" in r:
            r["mass_increase_kg"] = r["structural_half_mass_kg"] - base["structural_half_mass_kg"]
        d = r.get("dolu", {})
        r["meets_f1T_316"] = bool(d.get("f1T", 0) >= F1T_TARGET)
        r["meets_cg_045"] = bool(r.get("xcg_shell_eta70_c", 1) <= .45)
    ok = [r for r in rows if r["meets_f1T_316"] and r["meets_cg_045"]
          and (not base or r["xcg_shell_eta70_c"] <= base["xcg_shell_eta70_c"] + 1e-9)]
    choice = min(ok, key=lambda r: r["structural_half_mass_kg"])["variant"] if ok else None
    out = dict(level=a.level, target_f1T_full_Hz=F1T_TARGET, rule="hedefi sağlayan, CG'yi geri kaydırmayan en hafif",
               choice=choice, rows=rows)
    folder = ROOT / "fem/results/stiffening"
    write_json(folder / f"summary_{a.level}.json", out)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for r in rows:
        if "dolu" in r and "f1T" in r["dolu"] and "mass_increase_kg" in r:
            ax.plot(1e3 * r["mass_increase_kg"], r["dolu"]["f1T"], "o")
            ax.annotate(f"{r['variant']} (CG {r['xcg_shell_eta70_c']:.3f}c)", (1e3 * r["mass_increase_kg"], r["dolu"]["f1T"]),
                        fontsize=7, xytext=(3, 3), textcoords="offset points")
    ax.axhline(F1T_TARGET, color="r", lw=.8, label="hedef 316 Hz (1350 km/h)")
    ax.set(xlabel="Yarı kanat yapısal kütle artışı [g]", ylabel="f_1T dolu [Hz]", title=f"Rijitleştirme seçenekleri ({a.level})")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(folder / f"summary_{a.level}.png", dpi=130)
    plt.close(fig)
    for r in rows:
        d, b = r.get("dolu", {}), r.get("bos", {})
        print(r["variant"], {k: (round(v, 4) if isinstance(v, float) else v) for k, v in dict(
            f1B=d.get("f1B"), f1T=d.get("f1T"), f1B_e=b.get("f1B"), f1T_e=b.get("f1T"), dm=r.get("mass_increase_kg"),
            cg=r.get("xcg_shell_eta70_c"), Vf=d.get("Vf_kmh"), Vf_e=b.get("Vf_kmh")).items()})
    print("seçim:", choice)


if __name__ == "__main__":
    main()
