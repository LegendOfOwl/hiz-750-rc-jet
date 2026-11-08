"""Kanat S8R çözümünün son işlemi: uç sehim, kök reaksiyonu, tabaka Tsai-Wu oranı, mod sınıflandırması.

Tabaka gerilmeleri *EL PRINT GLOBAL=NO çıktısındandır: her tabaka 8 integration point (2x2 düzlem x
2 kalınlık), alttan (iç) üste; yerel 1-2 eksenleri tabakanın *ORIENTATION'ı. Bu eşleme CLT kupon
benchmarkında (validation/results/coupon) doğrulandı.
"""
import math

import numpy as np

from fem.cases import node_blocks, numeric
from fem.coupon import element_stresses


def all_frequencies(text):
    active, values = False, []
    for line in text.splitlines():
        compact = "".join(line.lower().split())
        if "eigenvalueoutput" in compact:
            active = True
        elif active and line.strip()[:1].isdigit():
            fields = numeric(line)
            if len(fields) >= 4:
                values.append(fields[3])
        elif active and values and line.strip():
            break
    return values


def total_force(text):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if "total force" in line.lower():
            for nxt in lines[i + 1:i + 5]:
                vals = numeric(nxt)
                if len(vals) >= 3:
                    return vals[:3]
    return None


def tsai_wu_ratio(s1, s2, s12, m):
    """Yük çarpanı R: FI(R*sigma)=1. R<1 hasar; güvenlik payı R-1."""
    f1, f2 = 1 / m["Xt"] - 1 / m["Xc"], 1 / m["Yt"] - 1 / m["Yc"]
    f11, f22, f66 = 1 / (m["Xt"] * m["Xc"]), 1 / (m["Yt"] * m["Yc"]), 1 / m["S12"] ** 2
    lin = f1 * s1 + f2 * s2
    quad = f11 * s1 * s1 + f22 * s2 * s2 + f66 * s12 * s12 + 2 * m["F12"] * s1 * s2
    if quad <= 0:
        return math.inf if lin <= 0 else 1 / lin
    return (-lin + math.sqrt(lin * lin + 4 * quad)) / (2 * quad)


class Section:
    """Bir açıklık istasyonundaki kutu düğümleri: w = a + theta (x - x_EA) en küçük kareler."""

    def __init__(self, model, nodes_data):
        g = model["geometry"]
        import params as P
        from structures import structures as ST
        self.sweep = math.tan(math.radians(g["sweep_le_deg"]))
        self.x_le, self.ST = g["x_root_le"], ST
        self.xf, self.xr = g["xf"], g["xr"]
        self.nodes = {int(k): v for k, v in nodes_data["nodes"].items()}
        stations = {}
        for n, p in self.nodes.items():
            c = float(ST.chord(p[1]))
            xc = (p[0] - self.x_le - self.sweep * p[1]) / c
            if self.xf - 1e-7 <= xc <= self.xr + 1e-7:
                stations.setdefault(round(p[1], 8), []).append(n)
        self.stations = sorted((y, ns) for y, ns in stations.items() if len(ns) >= 4)
        self.x_ea = {y: self.x_le + self.sweep * y + .30 * float(ST.chord(y)) for y, _ in self.stations}

    def fit(self, u):
        rows = []
        for y, ns in self.stations:
            x = np.array([self.nodes[n][0] for n in ns]) - self.x_ea[y]
            w = np.array([u[n][2] for n in ns])
            A = np.c_[np.ones_like(x), x]
            coef, *_ = np.linalg.lstsq(A, w, rcond=None)
            resid = w - A @ coef
            c = float(self.ST.chord(y))
            rows.append(dict(y=y, w_ea=float(coef[0]), theta=float(coef[1]), ux=float(np.mean([u[n][0] for n in ns])),
                             c=c, resid_rms=float(np.sqrt(np.mean(resid ** 2)))))
        return rows


def sign_changes(values, tol=.05):
    v = np.asarray(values)
    big = np.abs(v) > tol * np.max(np.abs(v)) if np.max(np.abs(v)) > 0 else np.zeros_like(v, bool)
    s = np.sign(v[big])
    return int(np.sum(s[1:] != s[:-1])) if len(s) > 1 else 0


def classify(rows):
    b = sum(r["w_ea"] ** 2 for r in rows)
    t = sum((r["theta"] * r["c"] / 2) ** 2 for r in rows)
    ip = sum(r["ux"] ** 2 for r in rows)
    loc = sum(r["resid_rms"] ** 2 for r in rows)
    total = b + t + ip + loc
    frac = dict(bending=b / total, torsion=t / total, inplane=ip / total, local=loc / total)
    kind = max(frac, key=frac.get)
    if kind == "bending":
        label = f"{sign_changes([r['w_ea'] for r in rows]) + 1}B"
    elif kind == "torsion":
        label = f"{sign_changes([r['theta'] for r in rows]) + 1}T"
    elif kind == "inplane":
        label = f"{sign_changes([r['ux'] for r in rows]) + 1}İB (düzlem içi)"
    else:
        label = "LOKAL (panel)"
    return label, frac


def postprocess(text, model, nodes_data):
    mats = model["materials"]
    g = model["geometry"]
    Y_EXCLUDE = g["y_root"] + (g["b2"] - g["y_root"]) / 8   # ilk kaburga bölmesinin dış sınırı [m]
    blocks = node_blocks(text, "displacements")
    nn = len(nodes_data["nodes"])
    full = [b for b in blocks if len(b) >= nn]
    if not full:
        raise RuntimeError("Tüm düğüm yer değiştirme bloğu yok")
    static, modal = full[0], full[1:]
    sec = Section(model, nodes_data)
    rows = sec.fit(static)
    tip = rows[-1]
    tip_nodes = [int(n) for n in nodes_data["tip"]]
    metrics = dict(tip_deflection_m=tip["w_ea"], tip_w_max_m=max(abs(static[n][2]) for n in tip_nodes),
                   tip_twist_deg=math.degrees(tip["theta"]))
    rf = total_force(text)
    applied = sum(nodes_data["loads"].values())
    root_set = {str(n) for n in nodes_data["root"]}
    # CCX RF, kısıtlı düğüme doğrudan uygulanan dış yükü içermez; denge için eklenir.
    on_root = sum(v for k, v in nodes_data["loads"].items() if k in root_set)
    quality = dict(root_reaction_N=rf, applied_force_N=applied, load_on_root_nodes_N=on_root,
                   force_balance_relative=abs(abs(rf[2]) + on_root - applied) / applied if rf else None)
    # ---- tabaka gerilmeleri
    stress = element_stresses(text)
    kinds = {int(k): v for k, v in nodes_data["kinds"].items()}
    strips = {int(k): v for k, v in nodes_data["strips"].items()}
    layers = {int(k): v for k, v in nodes_data["layers"].items()}
    centers = {int(k): v for k, v in nodes_data["center"].items()}
    kd = .544
    worst = dict(all=None, ex_root=None)
    worst_kd = worst_kd_ex = None
    core_tau_ex = None
    cap_s11 = {}
    core_tau = None
    by_kind = {}
    for (e, ip), s in stress.items():
        k = (ip - 1) // 8
        if e not in layers or k >= len(layers[e]):
            continue
        mname = layers[e][k][0]
        if mname.startswith("NSM"):
            continue  # yapısal olmayan kütle tabakası
        if mname == "CORE":
            tau = math.hypot(s[4], s[5])
            if core_tau is None or tau > core_tau["tau"]:
                core_tau = dict(tau=tau, element=e, kind=kinds[e], y=centers[e][1], xc=centers[e][0])
            if centers[e][1] > Y_EXCLUDE and (core_tau_ex is None or tau > core_tau_ex["tau"]):
                core_tau_ex = dict(tau=tau, element=e, kind=kinds[e], y=centers[e][1], xc=centers[e][0])
            continue
        m = mats[mname]
        r = tsai_wu_ratio(s[0], s[1], s[3], m)
        item = dict(R=r, element=e, ip=ip, layer=k + 1, material=mname, kind=kinds[e], strip=strips[e],
                    y=centers[e][1], xc=centers[e][0], s11=s[0], s22=s[1], s12=s[3])
        if worst["all"] is None or r < worst["all"]["R"]:
            worst["all"] = item
        # Kök ankastre tekilliği: ilk kaburga bölmesi (y < .035 + .0862 m, her ağda aynı bölge) hariç.
        if centers[e][1] > Y_EXCLUDE and (worst["ex_root"] is None or r < worst["ex_root"]["R"]):
            worst["ex_root"] = item
        mk = dict(m)
        for name in ("Xt", "Xc", "Yt", "Yc", "S12"):
            mk[name] *= kd
        mk["F12"] = m["F12"] / kd ** 2
        rk = tsai_wu_ratio(s[0], s[1], s[3], mk)
        if worst_kd is None or rk < worst_kd["R"]:
            worst_kd = dict(item, R=rk)
        if centers[e][1] > Y_EXCLUDE and (worst_kd_ex is None or rk < worst_kd_ex["R"]):
            worst_kd_ex = dict(item, R=rk)
        kb = by_kind.setdefault(kinds[e], dict(R_min=math.inf))
        if r < kb["R_min"]:
            kb.update(R_min=r, y=centers[e][1], xc=centers[e][0], material=mname, layer=k + 1)
        if mname == "UD":
            key = "root_bay" if centers[e][1] <= Y_EXCLUDE else "outboard"
            cur = cap_s11.setdefault(key, dict(max=-math.inf, min=math.inf))
            cur["max"], cur["min"] = max(cur["max"], s[0]), min(cur["min"], s[0])
    metrics.update(tsai_wu_R_min=worst["all"]["R"], tsai_wu_R_min_ex_root=worst["ex_root"]["R"],
                   tsai_wu_R_min_kd=worst_kd["R"], tsai_wu_R_min_kd_ex_root=worst_kd_ex["R"],
                   ud_cap_s11_min_outboard_Pa=cap_s11["outboard"]["min"],
                   core_shear_max_ex_root_Pa=core_tau_ex["tau"])
    quality.update(tsai_wu_critical=worst["all"], tsai_wu_critical_ex_root=worst["ex_root"],
                   tsai_wu_critical_kd=worst_kd, tsai_wu_critical_kd_ex_root=worst_kd_ex,
                   tsai_wu_by_region=by_kind, ud_cap_s11_Pa=cap_s11, y_exclude_root_m=Y_EXCLUDE,
                   core_shear_max=core_tau, core_shear_max_ex_root=core_tau_ex,
                   core_shear_allow_Pa=mats["CORE"].get("S_core"))
    # ---- modlar
    freqs = all_frequencies(text)
    modes = []
    for i, (f, block) in enumerate(zip(freqs, modal)):
        mrows = sec.fit(block)
        label, frac = classify(mrows)
        modes.append(dict(mode=i + 1, f_Hz=f, label=label, fractions=frac,
                          shape=[dict(y=r["y"], w=r["w_ea"], theta=r["theta"], ux=r["ux"]) for r in mrows]))
    for i, f in enumerate(freqs[:5]):
        metrics[f"f{i+1}_Hz"] = f
    named = {}
    for md in modes:
        named.setdefault(md["label"], md["f_Hz"])
    for lab, key in (("1B", "f_1B_Hz"), ("2B", "f_2B_Hz"), ("3B", "f_3B_Hz"), ("1T", "f_1T_Hz")):
        if lab in named:
            metrics[key] = named[lab]
    ip = [md for md in modes if "İB" in md["label"]]
    if ip:
        metrics["f_1IP_Hz"] = ip[0]["f_Hz"]
    return metrics, quality, modes, rows


def plot(work, modes, rows, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 3, figsize=(13, 4))
    y = [r["y"] for r in rows]
    axs[0].plot(y, [1e3 * r["w_ea"] for r in rows], "k-")
    axs[0].set(xlabel="y [m]", ylabel="w (EA, .30c) [mm]", title="Nihai 18g statik sehim")
    ax2 = axs[0].twinx()
    ax2.plot(y, [math.degrees(r["theta"]) for r in rows], "r--")
    ax2.set_ylabel("burulma [deg]", color="r")
    for md in modes[:6]:
        sh = md["shape"]
        ys = [s["y"] for s in sh]
        w = np.array([s["w"] for s in sh])
        th = np.array([s["theta"] * float(r["c"]) / 2 for s, r in zip(sh, rows)]) if len(sh) == len(rows) else np.array([s["theta"] for s in sh])
        sc = max(np.max(np.abs(w)), np.max(np.abs(th)), 1e-30)
        axs[1].plot(ys, w / sc, label=f"{md['mode']}: {md['f_Hz']:.0f} Hz {md['label']}")
        axs[2].plot(ys, th / sc, label=f"{md['mode']}: {md['label']}")
    axs[1].set(xlabel="y [m]", ylabel="w_EA (normalize)", title="Mod şekli: eğilme")
    axs[2].set(xlabel="y [m]", ylabel="theta c/2 (normalize)", title="Mod şekli: burulma")
    axs[1].legend(fontsize=7)
    fig.suptitle(title, fontsize=10)
    fig.tight_layout()
    fig.savefig(work / "plot.png", dpi=130)
    plt.close(fig)
