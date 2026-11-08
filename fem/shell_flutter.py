"""Kabuk FEM mod şekilleriyle modal p-k flutter (iter5 inceleme, Grup 1).

`fem/stiffening_study.py` flutter hızını yalnız f_1T oranıyla sabit iter4 1D eğrisinden ölçekliyordu
(kütle, CG, mod şekli ve bağlaşım değişimi yok). Bu betik CalculiX S8R kanat çözümünün kütle-normalize
modlarını (CCX *FREQUENCY özvektörleri M-normalize; katılım çarpanı toplamı yarı kanat kütlesinin altında,
kontrol aşağıda) `structures/fe_modal.py`'nin şerit-Theodorsen aerodinamiğine aktarır:

  * Kabuk modu, açıklık istasyonlarında kutu düğümlerine uydurulmuş w_EA(y) ve θ(y) = ∂z/∂x (akış yönü)
    olarak `fine.json` -> quality.modes[].shape içinde saklıdır (fem/wing_post.Section.fit).
  * 1D kiriş serbestlikleri (EA'ya dik kesit): w, w' = dw/ds = cosΛ dw/dy, φ (burun yukarı, EA etrafında).
    Akış yönü hücum açısı α_s = -θ = φ cosΛ - w' sinΛ  =>  φ = α_s / cosΛ + tanΛ w'.
  * Genelleştirilmiş kütle I (M-normalize), rijitlik diag(ω²) kabuk frekanslarından; aerodinamik
    `fe_modal.modal_aero` (her şerit noktasında birim B), Mach eşleştirmeli p-k `fe_modal.flutter_solve`.
  * Düzlem içi modlar (aerodinamik yükü yok) dışarıda bırakılır.

Doğrulama: aynı dönüşüm 1D fe_modal modlarına uygulanınca (kabuk istasyonlarında örneklenip yeniden
kurulunca) fe_modal'ın kendi V_F'si yeniden üretilmelidir (`--selftest`).

Çalıştır:  python fem/shell_flutter.py [--variants s31 s41r043w1 ...] [--selftest]
Çıktı:     fem/results/shell_flutter.json
Sınır: şerit teorisi (uç kaybı yok, kontrol yüzeyi serbestliği yok), kabuk mod şekli kutu düğümlerinin
doğrusal uydurmasıdır (kesit distorsiyonu ve veter yönü eğilmesi aerodinamiğe girmez).
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.interpolate import CubicSpline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "structures"))
import fe_modal as F  # noqa: E402
import structures as ST  # noqa: E402

STIFF = ROOT / "fem" / "results" / "stiffening"


def strip_beam():
    """Şerit aerodinamiği için 1D kiriş geometrisi (yalnız b_n, b_s, s, ağırlıklar kullanılır)."""
    base = ST.wing_section_model()
    sec = F.section_data(base, fuel=True)
    beam = F.beam_from_section(sec)
    fe = F.build_fe(beam)
    return fe, beam


def shapes_to_dofs(fe, beam, ys, w, theta):
    """İstasyon verisi (y, w_EA, θ=∂z/∂x) -> her şerit noktasında (w, w', φ)."""
    cl, tl = beam["cosL"], beam["tanL"]
    order = np.argsort(ys)
    ys, w, theta = np.asarray(ys)[order], np.asarray(w)[order], np.asarray(theta)[order]
    ys, idx = np.unique(ys, return_index=True)
    w, theta = w[idx], theta[idx]
    sw, st = CubicSpline(ys, w), CubicSpline(ys, theta)
    s = fe["strips"]["s"]
    y = beam["y_of_s"](s)
    wv = sw(y)
    wp = sw(y, 1) * cl                       # dw/ds
    alpha_s = -st(y)
    phi = alpha_s / cl + tl * wp
    return np.stack([wv, wp, phi], axis=1)   # (ns, 3)


def modal_problem(fe, beam, dofs_per_mode, omegas, b_ref, slope=True):
    ns = len(fe["strips"]["s"])
    nm = len(dofs_per_mode)
    Phi = np.zeros((3 * ns, nm))
    for j, d in enumerate(dofs_per_mode):
        Phi[:, j] = d.reshape(-1)
    fe2 = dict(fe, strips=dict(fe["strips"], B=np.repeat(np.eye(3)[None], ns, axis=0),
                               idx=np.arange(3 * ns).reshape(ns, 3)))
    Dq = F.modal_aero(fe2, dict(Phi=Phi), nm, b_ref, slope=slope)
    return Dq


pk_fresh = F.pk_fresh
first_crossing = F.first_crossing


def solve_fresh(fe, beam, dofs, omegas, b_ref, M_fixed=None):
    """Mach eşleştirmeli (M_n <= 0.9 tavanlı) iz-takipsiz flutter hızı [km/h]; M_fixed verilirse sabit Mach."""
    Dq = modal_problem(fe, beam, dofs, omegas, b_ref)
    cl = beam["cosL"]
    Vs = np.arange(600.0, 3000.0, 10.0) / 3.6
    if M_fixed is not None:
        g = pk_fresh(omegas, Dq, F.beta_of(0, cl, M_fixed), b_ref, Vs)
        v0, v2 = first_crossing(Vs, g), first_crossing(Vs, g, .02)
        return (v0 or math.inf) * 3.6, (v2 or math.inf) * 3.6
    # eşleştirme: her V'de kendi beta'sı (tavan M_n = 0.9) -> g(V) tek eğri
    g = pk_fresh(omegas, Dq, lambda V: F.beta_of(V, cl), b_ref, Vs)
    v0, v2 = first_crossing(Vs, g), first_crossing(Vs, g, .02)
    return (v0 or math.inf) * 3.6, (v2 or math.inf) * 3.6


def point_vector(stations, y, xc):
    """Her mod için (y, x/c) noktasındaki düşey yer değiştirme: w_EA + θ (x - x_EA)."""
    out = []
    c = float(ST.chord(y))
    for ys, w, th in stations:
        out.append(float(np.interp(y, ys, w) + np.interp(y, ys, th) * (xc - ST.X_EA) * c))
    return np.array(out)


def ritz_mass_change(stations, dofs, omegas, changes):
    """Kütle değişikliği (kütle [kg, + ekle / - çıkar], y, x/c) listesi -> Rayleigh-Ritz (kabuk modları taban).
    M' = I + Σ m v vᵀ (noktasal kütle, dönme ataleti yok), K = diag(ω²). Döner: yeni ω, yeni (w,w',φ)."""
    from scipy.linalg import eigh
    n = len(omegas)
    Mp = np.eye(n)
    for m, y, xc in changes:
        v = point_vector(stations, y, xc)
        Mp += m * np.outer(v, v)
    lam, Psi = eigh(np.diag(np.asarray(omegas) ** 2), Mp)
    new = [sum(Psi[j, i] * dofs[j] for j in range(n)) for i in range(n)]
    new_st = [(stations[0][0], sum(Psi[j, i] * stations[j][1] for j in range(n)),
               sum(Psi[j, i] * stations[j][2] for j in range(n))) for i in range(n)]
    return np.sqrt(lam), new, new_st


def torsion_index(stations, beam):
    """Modun burulma payı (wing_post.classify ile aynı ölçü: θ c/2 karesi / (w² + θ² c²/4))."""
    out = []
    for ys, w, th in stations:
        c = ST.chord(ys)
        t = np.sum((th * c / 2) ** 2)
        out.append(float(t / (t + np.sum(w ** 2))))
    return np.array(out)


def solve(fe, beam, dofs, omegas, b_ref, g_s=(0.0, 0.02)):
    Dq = modal_problem(fe, beam, dofs, omegas, b_ref)
    Vf, wf, br, beta, cur = F.flutter_solve(np.asarray(omegas), Dq, b_ref, beam["cosL"], curves=True)
    out = dict(Vf_kmh=Vf * 3.6 if math.isfinite(Vf) else None,
               ff_Hz=wf / 2 / math.pi if math.isfinite(Vf) else None, branch=int(br), beta=beta)
    out["Vf_g02_kmh"] = F.find_flutter(*cur, g_s=0.02)[0] * 3.6
    return out


def generalized_mass_1d(fe, beam, dofs, strips_model):
    """Tanılama: kabuk modelinin şerit kütlesi (1D eşleme kütlesi + yakıt) ile ∫(m w² - 2 S w φ + I φ²) ds.
    M-normalize mod için ~1 beklenir (yalnız rijit kesit varsayımı; düzlem içi/kesit içi kinetik enerji yok)."""
    st = fe["strips"]
    cl = beam["cosL"]
    y = beam["y_of_s"](st["s"])
    ym = np.array([r["y"] for r in strips_model])
    dy = np.gradient(ym)
    mps = np.array([(r["m_struct_1d"] + r["fuel"]) for r in strips_model]) / dy
    xcg = np.array([(r["m_struct_1d"] * r["xcg_1d"] + r["fuel"] * ST.X_FUEL_C) / (r["m_struct_1d"] + r["fuel"])
                    for r in strips_model])
    c = ST.chord(y)
    m = np.interp(y, ym, mps)
    x = np.interp(y, ym, xcg)
    S = m * (x - ST.X_EA) * c
    I = m * (c ** 2 / 12 + ((x - ST.X_EA) * c) ** 2)
    w, phi = dofs[:, 0], dofs[:, 2]
    # akış yönü şerit -> dik kesit: m cosΛ, S cos²Λ, I cos³Λ (fe_modal.section_data ile aynı)
    gm = float(np.sum(st["w"] * (m * cl * w ** 2 - 2 * S * cl ** 2 * w * phi + I * cl ** 3 * phi ** 2)))
    for _, ms, ysv, xcs in F.SERVOS:            # kabuk modelindeki iki servo (NSM) noktasal kütle
        sv = (ysv - beam["y_clamp"]) / cl
        d = (xcs - ST.X_EA) * float(ST.chord(ysv)) * cl
        gm += ms * (np.interp(sv, st["s"], w) - d * np.interp(sv, st["s"], phi)) ** 2
    return gm


def selftest(fe, beam, b_ref):
    """1D fe_modal modlarını kabuk istasyonu biçimine (w_EA, θ) çevirip yeniden kur; V_F aynı olmalı."""
    base = ST.wing_section_model()
    res = {}
    for fuel in (True, False):
        sec = F.section_data(base, fuel=fuel, m_fuel_half=0.432)
        r = F.analyse(sec, want_curves=True)
        md, fe1, beam1 = r["_md"], r["_fe"], r["_beam"]
        nm = r["n_modes"]
        sn = fe1["sn"]
        y_nodes = beam1["y_of_s"](sn)
        dofs = []
        for j in range(nm):
            ph = md["Phi"][:, j]
            w, wp, phi = ph[0::3], ph[1::3], ph[2::3]
            theta = -(phi * beam1["cosL"] - wp * math.sin(math.atan(beam1["tanL"])))
            dofs.append(shapes_to_dofs(fe, beam, y_nodes, w, theta))
        out = solve(fe, beam, dofs, md["omega"][:nm], b_ref)
        res["dolu" if fuel else "bos"] = dict(fe_modal_Vf_kmh=r["Vf_kmh"], reconstructed_Vf_kmh=out["Vf_kmh"],
                                             rel_diff=out["Vf_kmh"] / r["Vf_kmh"] - 1, n_modes=nm)
    return res


def variant_modes(path, n_oop):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    modes = d["quality"]["modes"]
    sel = [m for m in modes if m["fractions"]["inplane"] < .5][:n_oop]
    return d, sel


def run_variant(fe, beam, b_ref, name, folder, n_oop=(4, 6, 8)):
    out = {}
    for fuel_key, sub in (("dolu", f"wing_{name}"), ("bos", f"wing_empty_{name}")):
        path = STIFF / sub / "fine.json"
        if not path.is_file():
            continue
        d, _ = variant_modes(path, 99)
        model = json.loads((STIFF / sub / "fine_wing_model.json").read_text(encoding="utf-8"))
        row = dict(source=str(path.relative_to(ROOT)).replace("\\", "/"))
        for n in n_oop:
            _, sel = variant_modes(path, n)
            dofs = [shapes_to_dofs(fe, beam, [s["y"] for s in m["shape"]], [s["w"] for s in m["shape"]],
                                   [s["theta"] for s in m["shape"]]) for m in sel]
            om = [2 * math.pi * m["f_Hz"] for m in sel]
            r = solve(fe, beam, dofs, om, b_ref)          # fe_modal iz takipli (karşılaştırma)
            v0, v2 = solve_fresh(fe, beam, dofs, om, b_ref)
            vm0, vm2 = solve_fresh(fe, beam, dofs, om, b_ref, M_fixed=F.V_REQ / F.A_SND)
            vt = r["Vf_kmh"] or math.inf
            # iki çözüm de kök kaçırabilir (iz takibi dal değiştirir, taze başlatma kökü bulamayabilir):
            # muhafazakâr olarak düşük olan alınır (fe_modal.analyse ile aynı kural)
            r = dict(Vf_kmh=min(v0, vt), Vf_fresh_kmh=v0, Vf_g02_kmh=v2, Vf_Mfix088_kmh=vm0, tracking_pk=r)
            r["modes"] = [f"{m['mode']}:{m['label']} {m['f_Hz']:.1f}" for m in sel]
            if n == n_oop[0]:
                row["generalized_mass_check"] = [round(generalized_mass_1d(fe, beam, dd, model["strips"]), 3)
                                                 for dd in dofs]
            row[f"n{n}"] = r
        out[fuel_key] = row
    return out


MS = F.M_SERVO
OPTIONS = {   # kütle değişiklikleri (kg, y, x/c): params DEĞİŞMEZ, yalnız öneri hesabı
    "A: aileron servosu x/c .60 -> .15 (aynı y, ön kiriş önü)": [(-MS, .34, .60), (MS, .34, .15)],
    "B: aileron servosu 60 g ince servo": [(-.06, .34, .60)],
    "C: aileron servosu köke (y .10, x/c .65) + tork çubuğu (çubuk kütlesi yok)": [(-MS, .34, .60), (MS, .10, .65)],
    "D: flap servosu x/c .65 -> .15": [(-MS, .10, .65), (MS, .10, .15)],
    "A+D": [(-MS, .34, .60), (MS, .34, .15), (-MS, .10, .65), (MS, .10, .15)],
    "E1: uç hücum kenarı balans 30 g (y .70, x/c .05)": [(.03, .70, .05)],
    "E2: uç hücum kenarı balans 60 g (y .70, x/c .05)": [(.06, .70, .05)],
    "A+E1": [(-MS, .34, .60), (MS, .34, .15), (.03, .70, .05)],
}


def options_study(fe, beam, b_ref, variant="s41r043w1", n_basis=9, n_flutter=8):
    """Kabuk modları tabanında Rayleigh-Ritz kütle değişikliği seçenekleri + 1T frekans ölçeği (1350 için).
    Ritz yöntemi 1D modelde kesin çözümle karşılaştırıldı (V_F farkı ≤ %1.6, raporda)."""
    out = {}
    for fuel_key, sub in (("dolu", f"wing_{variant}"), ("bos", f"wing_empty_{variant}")):
        _, sel = variant_modes(STIFF / sub / "fine.json", n_basis)
        stations = [(np.array([s["y"] for s in m["shape"]]), np.array([s["w"] for s in m["shape"]]),
                     np.array([s["theta"] for s in m["shape"]])) for m in sel]
        dofs = [shapes_to_dofs(fe, beam, *st) for st in stations]
        om = np.array([2 * math.pi * m["f_Hz"] for m in sel])
        rows = {}
        for name, ch in {"temel": [], **OPTIONS}.items():
            w, nd, nst = ritz_mass_change(stations, dofs, om, ch)
            ti = torsion_index(nst, beam)
            f1t = float(w[int(np.argmax(ti[:5]))] / 2 / math.pi)
            v0, v2 = solve_fresh(fe, beam, nd[:n_flutter], w[:n_flutter], b_ref)
            vt = solve(fe, beam, nd[:n_flutter], w[:n_flutter], b_ref)["Vf_kmh"] or math.inf
            v0 = min(v0, vt)
            rows[name] = dict(dm_kg=sum(c[0] for c in ch), f_Hz=[round(x / 2 / math.pi, 1) for x in w[:5]],
                              f1T_Hz=round(f1t, 1), Vf_kmh=round(v0), Vf_g02_kmh=round(v2))
            print(fuel_key, name, rows[name])
        # 1T ölçeği: burulma payı > .5 olan modların frekansı çarpanla; 1350 km/h için gereken çarpan
        ti = torsion_index(stations, beam)
        scale = {}
        for fac in (1.0, 1.02, 1.04, 1.06, 1.08, 1.10):
            sc = np.where(ti > .5, fac, 1.0)
            scale[fac] = round(solve_fresh(fe, beam, dofs[:n_flutter], (om * sc)[:n_flutter], b_ref)[0])
        rows["torsion_scale_Vf_kmh"] = scale
        print(fuel_key, "1T ölçeği", scale)
        out[fuel_key] = rows
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", nargs="*", default=["s31", "s31r043", "s41r043", "s41r043w1", "s51r043w1"])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--options", action="store_true", help="s41r043w1 kütle seçenekleri (Ritz) ve 1T ölçeği")
    ap.add_argument("--out", default=str(ROOT / "fem" / "results" / "shell_flutter.json"))
    a = ap.parse_args()
    fe, beam = strip_beam()
    b_ref = F.b_ref_default()
    res = dict(method=__doc__.split("\n\n")[1].strip(), b_ref=b_ref, cosL=beam["cosL"], tanL=beam["tanL"])
    if a.selftest:
        res["selftest_1d_roundtrip"] = selftest(fe, beam, b_ref)
        print("selftest", res["selftest_1d_roundtrip"])
    res["variants"] = {}
    for v in a.variants:
        res["variants"][v] = run_variant(fe, beam, b_ref, v, STIFF)
        for k, r in res["variants"][v].items():
            print(v, k, {n: (round(r[n]["Vf_kmh"]), round(r[n]["Vf_Mfix088_kmh"]),
                             round(r[n]["tracking_pk"]["Vf_kmh"] or 0))
                         for n in r if n.startswith("n")}, "gm", r.get("generalized_mass_check"))
    if a.options:
        res["options_s41r043w1"] = options_study(fe, beam, b_ref)
    Path(a.out).write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()
