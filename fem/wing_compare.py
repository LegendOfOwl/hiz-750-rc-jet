"""Kanat S8R sonuçlarının çapraz kontrolü: basit kiriş teorisi, fe_modal 1D FE ve flutter ölçeklemesi.

Çıktı: fem/results/wing_compare.json, fem/results/wing_compare.png
  * Kiriş: aynı yük (Schrenk 18 g, atalet rahatlatması yok, kök y=.035) ile w'' = M/EI iki biçimde:
      (a) y boyunca düz kiriş (akış yönü kök, ok yok) ve (b) ok açılı EA kirişi, dik kök: w'' = M/(EI cos^3 L).
    EI iki kaynaktan: structures 1D EI(y) ve kabuk kesitinden (aynı laminat tanımı) hesaplanan EI(y).
  * fe_modal: dolu/boş 1B..1T; flutter structures/out/fe_sonuclar.json gvt.grid (f_B, f_T ölçek ızgarası)
    üzerinde iki doğrusal ara değerleme; ızgara dışı (0.7-1.5) ekstrapolasyon yapılmaz.
"""
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from validation.common import read_json, write_json  # noqa: E402
from validation.convergence import gci  # noqa: E402


def section_ei(nodes_data, model):
    """Kabuk modelinin akış yönü kesit EI(y): tabaka E_span (UD E1, ±45 kumaş CLT Ex, çekirdek E)."""
    from structures import structures as ST
    from fem.clt import engineering_constants
    mats = model["materials"]
    e_span = {"UD": mats["UD"]["E1"], "CORE": mats["CORE"]["E1"],
              "FAB": engineering_constants([(mats["FAB"], 1e-3, 45.)])["Ex"]}
    g = model["geometry"]
    kinds = nodes_data["kinds"]
    layers = nodes_data["layers"]
    center = nodes_data["center"]
    strips = {}
    for t, s in nodes_data["strips"].items():
        strips.setdefault(s, []).append(t)
    rows = []
    for s, ts in sorted(strips.items()):
        ea = eaz = eaz2 = 0.
        y = None
        for t in ts:
            kind = kinds[t]
            if kind == "RIB":
                continue
            xc, yy, eta = center[t]
            y = yy
            c = float(ST.chord(yy))
            area = nodes_data["areas"][t]
            if kind.startswith(("CAP", "SKIN")):
                # şerit genişliği: alan / şerit boyu (eleman açıklık boyu)
                side = 1 if eta > 0 else -1
                z = g["z_root"] + math.tan(math.radians(g["dihedral_deg"])) * yy + side * float(ST.yt64(xc, ST.tc(yy))) * c
                zc = z
                for mname, tt in reversed(layers[t]):
                    if mname.startswith("NSM"):
                        continue
                    zm = zc - side * tt / 2
                    zc -= side * tt
                    w = area / nodes_data["span_len"][str(s)]
                    e = e_span[mname]
                    ea += e * w * tt
                    eaz += e * w * tt * zm
                    eaz2 += e * w * tt * zm * zm
            else:  # web: düşey şerit, alan/şerit boyu = yükseklik
                h = area / nodes_data["span_len"][str(s)]
                z0 = g["z_root"] + math.tan(math.radians(g["dihedral_deg"])) * yy
                zm = z0 + eta * float(ST.yt64(xc, ST.tc(yy))) * c
                tt = sum(v for m, v in layers[t] if not m.startswith("NSM"))
                e = e_span["FAB"]
                ea += e * tt * h
                eaz += e * tt * h * zm
                eaz2 += e * tt * (h * zm * zm + h ** 3 / 12)
        zna = eaz / ea
        rows.append((y, eaz2 - ea * zna * zna))
    return sorted(rows)


def beam_deflection(ys, moment, ei, cos3=1.):
    curv = moment / (ei * cos3)
    slope = np.concatenate([[0.], np.cumsum(.5 * (curv[1:] + curv[:-1]) * np.diff(ys))])
    return np.concatenate([[0.], np.cumsum(.5 * (slope[1:] + slope[:-1]) * np.diff(ys))])


def bilinear(fac, grid, fb, ft):
    fac = np.asarray(fac)
    grid = np.asarray(grid)  # grid[j(fT), i(fB)]
    if not (fac[0] <= fb <= fac[-1] and fac[0] <= ft <= fac[-1]):
        return None
    i = min(np.searchsorted(fac, fb) - 1, len(fac) - 2) if fb > fac[0] else 0
    j = min(np.searchsorted(fac, ft) - 1, len(fac) - 2) if ft > fac[0] else 0
    tb = (fb - fac[i]) / (fac[i + 1] - fac[i])
    tt = (ft - fac[j]) / (fac[j + 1] - fac[j])
    return float((1 - tt) * ((1 - tb) * grid[j][i] + tb * grid[j][i + 1])
                 + tt * ((1 - tb) * grid[j + 1][i] + tb * grid[j + 1][i + 1]))


def main():
    import params as P
    from structures import structures as ST
    out = {}
    fe = read_json(ROOT / "structures/out/fe_sonuclar.json")
    lam = math.radians(fe["model"]["sweep_EA_deg"])
    res = {}
    for key, folder in (("dolu", "wing"), ("bos", "wing_empty")):
        rows = {lv: read_json(ROOT / "fem/results" / folder / f"{lv}.json") for lv in ("coarse", "medium", "fine")}
        res[key] = rows
    fine = res["dolu"]["fine"]
    raw = Path(fine["raw_directory"])
    model = read_json(raw / "wing_model.json")
    nodes_data = read_json(raw / "wing_nodes.json")
    # şerit boyları
    g = model["geometry"]
    ny = model["mesh"]["ny"]
    yf = np.linspace(g["y_root"], g["b2"], ny + 1)
    nodes_data["span_len"] = {str(j): float(yf[j + 1] - yf[j]) for j in range(ny)}
    shell_ei = section_ei(nodes_data, model)
    base = ST.wing_section_model()
    ys = np.linspace(g["y_root"], g["b2"], 801)
    q = np.interp(ys, ST.YS, ST.schrenk(P.N_LIMIT * P.SF))
    moment = np.array([np.trapezoid(q[k:] * (ys[k:] - ys[k]), ys[k:]) for k in range(len(ys))])
    ei_1d = np.interp(ys, ST.YS, base["ws"]["EI"])
    ei_sh = np.interp(ys, [r[0] for r in shell_ei], [r[1] for r in shell_ei])
    cos3 = math.cos(lam) ** 3
    beams = {"1D_EI_duz": beam_deflection(ys, moment, ei_1d), "1D_EI_ok": beam_deflection(ys, moment, ei_1d, cos3),
             "kabuk_EI_duz": beam_deflection(ys, moment, ei_sh), "kabuk_EI_ok": beam_deflection(ys, moment, ei_sh, cos3)}
    w_fe = fine["metrics"]["tip_deflection_m"]
    profile = fine["quality"]["static_profile"]
    out["static"] = dict(
        load="Schrenk 12g x 1.5 = 18 g, atalet rahatlatması yok, kök y=.035 m",
        root_moment_Nm=float(moment[0]), root_moment_structures_relief_y0_Nm=float(base["M"][0]),
        tip_deflection_fe_m={lv: res["dolu"][lv]["metrics"]["tip_deflection_m"] for lv in res["dolu"]},
        tip_deflection_beam_m={k: float(v[-1]) for k, v in beams.items()},
        fe_over_beam={k: w_fe / float(v[-1]) for k, v in beams.items()},
        ei_root_Nm2=dict(structures_1D=float(ei_1d[0]), shell_section=float(ei_sh[0])),
        ei_ratio_shell_to_1D=[dict(y=float(y), ratio=float(e / np.interp(y, ST.YS, base["ws"]["EI"])))
                              for y, e in shell_ei[::max(1, ny // 8)]],
        convergence_tip=gci([1 / 32, 1 / 16, 1 / 8], [res["dolu"][lv]["metrics"]["tip_deflection_m"]
                                                     for lv in ("fine", "medium", "coarse")]))
    # 1D kapak gerilmesi (structures yaklaşımı) kritik FE noktasında
    crit = fine["quality"]["tsai_wu_critical_ex_root"]
    yc = crit["y"]
    ws = base["ws"]
    h_eff = float(np.interp(yc, ST.YS, ws["h_box"] - ws["n_ud"] * ST.MAT["UD"]["t_ply"]))
    m_c = float(np.interp(yc, ys, moment))
    out["static"]["cap_stress_check"] = dict(
        y=yc, fe_ud_s11_Pa=crit["s11"], beam_1D_EI_Pa=-ST.MAT["UD"]["E1"] * m_c * h_eff / 2 / float(np.interp(yc, ST.YS, ws["EI"])),
        beam_shell_EI_Pa=-ST.MAT["UD"]["E1"] * m_c * h_eff / 2 / float(np.interp(yc, ys, ei_sh)),
        note="Kiriş: sigma = E1 M (h_eff/2)/EI; h_eff structures kapak kolu.")
    # modal karşılaştırma
    gvt = fe["gvt"]
    modal = {}
    for key in ("dolu", "bos"):
        rows = res[key]
        fe_f = {lv: rows[lv]["metrics"] for lv in rows}
        f1b = {lv: fe_f[lv].get("f_1B_Hz") for lv in rows}
        f1t = {lv: fe_f[lv].get("f_1T_Hz") for lv in rows}
        ref = gvt[key]
        rb, rt = f1b["fine"] / ref["f1B"], f1t["fine"] / ref["f1T"]
        vf_grid = bilinear(gvt[key]["fac"], gvt[key]["grid"], rb, rt)
        vf_t_only = float(np.interp(rt, gvt[key]["fac"], gvt[key]["Vf_vs_fT"])) if 0.7 <= rt <= 1.5 else None
        modal[key] = dict(
            shell_fine=dict(f1B=f1b["fine"], f2B=fe_f["fine"].get("f_2B_Hz"), f1T=f1t["fine"],
                            f1IP=fe_f["fine"].get("f_1IP_Hz"),
                            first5=[(m["f_Hz"], m["label"]) for m in rows["fine"]["quality"]["modes"][:5]]),
            fe_modal_1D=dict(f=ref["f"], names=ref["names"], Vf_kmh=ref["Vf_vs_fT"][3]),
            ratio_f1B=rb, ratio_f1T=rt,
            gci_f1B=gci([1 / 32, 1 / 16, 1 / 8], [f1b[lv] for lv in ("fine", "medium", "coarse")]),
            gci_f1T=gci([1 / 32, 1 / 16, 1 / 8], [f1t[lv] for lv in ("fine", "medium", "coarse")]),
            Vf_scaled_fT_only_kmh=vf_t_only, Vf_scaled_fB_fT_kmh=vf_grid,
            gvt_acceptance_f1T_min_Hz=230., f1T_meets_gvt_230=f1t["fine"] >= 230.,
            fT_min_fac_1080=ref["fT_min_fac_1080"], fT_min_fac_1350=ref["fT_min_fac_1350"],
            f1T_needed_for_1350_Hz=ref["fT_min_fac_1350"] * ref["f1T"])
    out["modal"] = modal
    out["notes"] = ["Flutter değerleri yalnız frekans ölçeklemesidir (fe_modal mod şekilleri/kütlesi sabit). "
                    "Kabuk mod şekilleri ve kütle dağılımıyla aeroelastik çözüm yeniden yapılmalı.",
                    "Kiriş referansı lineer Euler-Bernoulli; kesit distorsiyonu, kayma gecikmesi ve kök üçgeni etkisi yok."]
    write_json(ROOT / "fem/results/wing_compare.json", out)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.4))
    axs[0].plot([r["y"] for r in profile], [1e3 * r["w_ea"] for r in profile], "k-", lw=2, label="S8R kabuk (ince)")
    for k, v in beams.items():
        axs[0].plot(ys, 1e3 * v, "--", label=f"kiriş {k}")
    axs[0].set(xlabel="y [m]", ylabel="w [mm]", title="18 g nihai statik sehim")
    axs[0].legend(fontsize=7)
    axs[1].plot([r[0] for r in shell_ei], [r[1] for r in shell_ei], "k-", label="kabuk kesiti EI")
    axs[1].plot(ST.YS, base["ws"]["EI"], "r--", label="structures 1D EI")
    axs[1].set(xlabel="y [m]", ylabel="EI [N m^2]", yscale="log", title="Eğilme rijitliği")
    axs[1].legend(fontsize=8)
    for key, mk in (("dolu", "o"), ("bos", "s")):
        fac = np.array(gvt[key]["fac"])
        axs[2].plot(fac * gvt[key]["f1T"], gvt[key]["Vf_vs_fT"], mk + "-", label=f"fe_modal V_F(f_1T), {key}")
        m = modal[key]
        if m["Vf_scaled_fT_only_kmh"]:
            axs[2].plot(m["shell_fine"]["f1T"], m["Vf_scaled_fT_only_kmh"], "k" + mk, ms=10,
                        label=f"kabuk f_1T, {key}")
    axs[2].axhline(1080, color="r", lw=.8)
    axs[2].axhline(1350, color="r", lw=.8, ls="--")
    axs[2].axvline(230, color="gray", lw=.8, ls=":")
    axs[2].set(xlabel="f_1T [Hz]", ylabel="V_F [km/h]", title="Flutter: f_1T ölçeklemesi (1080/1350 km/h)")
    axs[2].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(ROOT / "fem/results/wing_compare.png", dpi=130)
    plt.close(fig)
    print(json.dumps(dict(static=out["static"]["fe_over_beam"], modal={k: (v["ratio_f1B"], v["ratio_f1T"],
                     v["Vf_scaled_fT_only_kmh"], v["Vf_scaled_fB_fT_kmh"]) for k, v in modal.items()}), indent=1))


if __name__ == "__main__":
    main()
