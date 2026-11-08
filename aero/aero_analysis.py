"""
HIZ-750 - aerodinamik ve stabilite analizi (AeroSandbox 4.2 + NeuralFoil).

Calistir:  C:/Users/Urungu/.hz750/Scripts/python aero/aero_analysis.py
Ciktilar:  aero/out/*.png, aero/out/sonuclar.json, aero/out/ozet.txt

Geometri ve kutleler params.py'den okunur (degistirilmez).
"""
import json
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import aerosandbox as asb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import params as P  # noqa: E402

OUT = os.path.join(ROOT, "aero", "out")
os.makedirs(OUT, exist_ok=True)
G = 9.80665
LOG = []


def log(s=""):
    print(s)
    LOG.append(s)


# ======================================================================
# 1. Profiller
# ======================================================================
def airfoil_64a(tc):
    """NACA 64A010 koordinatlarini kalinlikca olcekleyerek 64A0xx uretir."""
    base = asb.Airfoil("naca64a010")
    af = base.scale(scale_x=1.0, scale_y=tc / base.max_thickness())
    af.name = f"naca64a0{round(tc * 100):02d}"
    return af


AF = {
    "naca64a007": airfoil_64a(0.07),
    "naca64a006": airfoil_64a(0.06),
    "naca0006": asb.Airfoil("naca0006"),
}


def airfoil_polars():
    alphas = np.linspace(-4, 16, 81)
    cases = [(1.5e6, 0.09, "kalkis/inis ~110 km/h"), (4.5e6, 0.0, "750 km/h (M=0 NeuralFoil)")]
    res = {}
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.5))
    for name, af in AF.items():
        res[name] = {}
        for Re, mach, lbl in cases:
            a = af.get_aero_from_neuralfoil(alpha=alphas, Re=Re, mach=mach, model_size="large")
            cl, cd, cm = np.array(a["CL"]), np.array(a["CD"]), np.array(a["CM"])
            # Cl_max: ilk lokal maksimum (stall oncesi)
            i = int(np.argmax(cl[alphas <= 15]))
            cla = np.polyfit(np.radians(alphas[(alphas >= -2) & (alphas <= 4)]),
                             cl[(alphas >= -2) & (alphas <= 4)], 1)[0]
            res[name][f"{Re:.1e}"] = dict(Clmax=float(cl[i]), alpha_Clmax=float(alphas[i]),
                                          Cd0=float(np.interp(0, alphas, cd)),
                                          Cm0=float(np.interp(0, alphas, cm)),
                                          Cl_alpha_per_rad=float(cla))
            ls = "-" if Re > 2e6 else "--"
            axs[0].plot(alphas, cl, ls, label=f"{name} Re={Re:.1e}")
            axs[1].plot(cd, cl, ls, label=f"{name} Re={Re:.1e}")
            axs[2].plot(alphas, cm, ls, label=f"{name} Re={Re:.1e}")
    axs[0].set_xlabel("alfa [deg]"); axs[0].set_ylabel("Cl")
    axs[1].set_xlabel("Cd"); axs[1].set_ylabel("Cl"); axs[1].set_xlim(0, 0.03)
    axs[2].set_xlabel("alfa [deg]"); axs[2].set_ylabel("Cm c/4")
    for a in axs:
        a.grid(alpha=.3)
    axs[0].legend(fontsize=7)
    fig.suptitle("Profil polarlari (NeuralFoil, n_crit=9)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "profil_polarlari.png"), dpi=120)
    plt.close(fig)
    return res


# ======================================================================
# 2. Ucak modeli
# ======================================================================
def lerp(a, b, t):
    return a + (b - a) * t


def build_wing(deflections=None):
    d = deflections or {}
    w = P.WING
    g = P.wing_geom()
    b2 = g["b"] / 2
    tl = math.tan(math.radians(w["sweep_le"]))
    td = math.tan(math.radians(w["dihedral"]))
    etas = sorted({0.0, w["flap"]["eta0"], w["flap"]["eta1"], w["aileron"]["eta0"],
                   w["aileron"]["eta1"], 1.0})
    xsecs = []
    for e in etas:
        y = e * b2
        c = lerp(g["cr"], g["ct"], e)
        tc = lerp(w["tc_root"], w["tc_tip"], e)
        cs = []
        if w["flap"]["eta0"] <= e < w["flap"]["eta1"]:
            cs.append(asb.ControlSurface("flap", symmetric=True, deflection=d.get("flap", 0.0),
                                         hinge_point=1 - w["flap"]["cf"]))
        if w["aileron"]["eta0"] <= e < w["aileron"]["eta1"]:
            cs.append(asb.ControlSurface("aileron", symmetric=False, deflection=d.get("aileron", 0.0),
                                         hinge_point=1 - w["aileron"]["cf"]))
        xsecs.append(asb.WingXSec(
            xyz_le=[w["x_root_le"] + y * tl, y, w["z_root"] + y * td],
            chord=c, twist=w["incidence"] + w["twist_tip"] * e,
            airfoil=airfoil_64a(tc), control_surfaces=cs))
    return asb.Wing(name="Kanat", symmetric=True, xsecs=xsecs)


def build_htail(deflections=None):
    d = deflections or {}
    h = P.HTAIL
    g = P.surface_geom(h)
    b2 = g["b"] / 2
    tl = math.tan(math.radians(h["sweep_le"]))
    cs = [asb.ControlSurface("elevator", symmetric=True, deflection=d.get("elevator", 0.0),
                             hinge_point=1 - h["elevator"]["cf"])]
    xsecs = [asb.WingXSec(xyz_le=[h["x_root_le"], 0, h["z_root"]], chord=g["cr"],
                          airfoil=AF["naca0006"], control_surfaces=cs),
             asb.WingXSec(xyz_le=[h["x_root_le"] + b2 * tl, b2, h["z_root"]], chord=g["ct"],
                          airfoil=AF["naca0006"])]
    return asb.Wing(name="Yatay kuyruk", symmetric=True, xsecs=xsecs)


def build_vtail(deflections=None):
    d = deflections or {}
    v = P.VTAIL
    g = P.vtail_geom()
    tl = math.tan(math.radians(v["sweep_le"]))
    cs = [asb.ControlSurface("rudder", symmetric=True, deflection=d.get("rudder", 0.0),
                             hinge_point=1 - v["rudder"]["cf"])]
    xsecs = [asb.WingXSec(xyz_le=[v["x_root_le"], 0, v["z_root"]], chord=g["cr"],
                          airfoil=AF["naca0006"], control_surfaces=cs),
             asb.WingXSec(xyz_le=[v["x_root_le"] + g["h"] * tl, 0, v["z_root"] + g["h"]],
                          chord=g["ct"], airfoil=AF["naca0006"])]
    return asb.Wing(name="Dikey kuyruk", symmetric=False, xsecs=xsecs)


def fus_radius(x):
    f = P.FUSELAGE
    L, R = f["length"], f["d_max"] / 2
    x0, x1 = f["x_dmax_start"], f["x_dmax_end"]
    if x <= x0:
        t = x / x0
        return R * math.sqrt(max(0.0, 1 - (1 - t) ** 2)) * (0.15 + 0.85 * t ** 0.35) / 1.0 if t > 0 else 0.0
    if x <= x1:
        return R
    t = (x - x1) / (L - x1)
    return lerp(R, f["d_tail"] / 2, t ** 1.3)


def build_fuselage():
    xs = np.concatenate([np.linspace(0, P.FUSELAGE["x_dmax_start"], 15),
                         np.linspace(P.FUSELAGE["x_dmax_start"], P.FUSELAGE["length"], 12)[1:]])
    return asb.Fuselage(name="Govde",
                        xsecs=[asb.FuselageXSec(xyz_c=[x, 0, 0], radius=fus_radius(x)) for x in xs])


def airplane(defl=None, xyz_ref=None):
    wg = P.wing_geom()
    return asb.Airplane(name=P.NAME, xyz_ref=xyz_ref or [P.mass_summary()["x_cg"], 0, 0],
                        wings=[build_wing(defl), build_htail(defl), build_vtail(defl)],
                        fuselages=[build_fuselage()],
                        s_ref=P.WING["S"], c_ref=wg["mac"], b_ref=wg["b"])


def opp(V, alt=300.0, alpha=0.0, beta=0.0, p=0.0, q=0.0, r=0.0):
    return asb.OperatingPoint(atmosphere=asb.Atmosphere(altitude=alt), velocity=V,
                              alpha=alpha, beta=beta, p=p, q=q, r=r)


def ab(ap, op, deriv=False):
    a = asb.AeroBuildup(airplane=ap, op_point=op, xyz_ref=ap.xyz_ref, model_size="large")
    if deriv:
        return a.run_with_stability_derivatives(alpha=True, beta=True, p=True, q=True, r=True)
    return a.run()


def f(x):
    return float(np.asarray(x).reshape(-1)[0])


# ======================================================================
# Analiz
# ======================================================================
def main():
    out = {}
    wg = P.wing_geom()
    mac, Sref, b = wg["mac"], P.WING["S"], wg["b"]
    mfull, mempty = P.mass_summary(1.0), P.mass_summary(0.0)
    atm = asb.Atmosphere(altitude=300.0)
    rho = f(atm.density())
    log(f"=== {P.NAME} aerodinamik/stabilite ===")
    log(f"Kanat MAC={mac:.4f} m, x_MAC_LE={wg['x_mac_le']:.4f} m, S={Sref} m2, b={b:.3f} m")

    # ---- 1. profiller
    pol = airfoil_polars()
    out["profiller"] = pol
    log("\n[1] Profil ozet (NeuralFoil):")
    for n, d in pol.items():
        for re, v in d.items():
            log(f"   {n:11s} Re={re}: Clmax={v['Clmax']:.2f} @ {v['alpha_Clmax']:.1f} deg, "
                f"Cd0={v['Cd0']:.5f}, Cm0={v['Cm0']:+.4f}, Cla={v['Cl_alpha_per_rad']:.2f}/rad")
    a_ = 340.0
    for tc in (0.06, 0.07):
        # Korn ile 2B kritik Mach (Cl~0) + Prandtl-Glauert
        log(f"   t/c={tc:.2f}: 2B M_dd(Korn, Cl=0)~{0.87 - tc:.2f}; 3B c/4 ok acisi ile ~"
            f"{0.87/math.cos(math.radians(23.5)) - tc/math.cos(math.radians(23.5))**2:.2f}")
    beta_pg = math.sqrt(1 - (P.V_TARGET / a_) ** 2)
    log(f"   750 km/h M={P.V_TARGET/a_:.3f}: Prandtl-Glauert Cl_alpha artisi x{1/beta_pg:.2f} (2B)")

    # ---- 2. boylamsal
    V = P.V_TARGET
    ap_full = airplane(xyz_ref=[mfull["x_cg"], 0, mfull["z_cg"]])
    d0 = ab(ap_full, opp(V, alpha=0.5), deriv=True)
    x_np = f(d0["x_np"])
    CLa = f(d0["CLa"])
    Cma = f(d0["Cma"])
    Cmq = f(d0["Cmq"])
    sm_full = (x_np - mfull["x_cg"]) / mac
    sm_empty = (x_np - mempty["x_cg"]) / mac
    # dusuk hiz NP
    d_ls = ab(ap_full, opp(30.0, alpha=4.0), deriv=True)
    x_np_ls = f(d_ls["x_np"])
    log("\n[2] Boylamsal kararlilik (AeroBuildup, 750 km/h, alfa 0.5 deg):")
    log(f"   CL_alpha={CLa:.3f} /rad   Cm_alpha={Cma:.3f} /rad   Cm_q={Cmq:.2f} /rad")
    log(f"   Notr nokta x_np={x_np:.4f} m (%{100*(x_np-wg['x_mac_le'])/mac:.1f} MAC); "
        f"dusuk hizda x_np={x_np_ls:.4f} m")
    log(f"   Tam yakit CG x={mfull['x_cg']:.4f} -> statik marj %{100*sm_full:.1f} MAC")
    log(f"   Bos yakit CG x={mempty['x_cg']:.4f} -> statik marj %{100*sm_empty:.1f} MAC")

    # VLM capraz kontrol (govdesiz)
    ap_vlm = asb.Airplane(name="vlm", xyz_ref=[mfull["x_cg"], 0, 0],
                          wings=[build_wing(), build_htail(), build_vtail()],
                          s_ref=Sref, c_ref=mac, b_ref=b)
    vlm = asb.VortexLatticeMethod(ap_vlm, opp(V, alpha=0.5), spanwise_resolution=12,
                                  chordwise_resolution=8)
    dv = vlm.run_with_stability_derivatives(alpha=True, beta=False, p=False, q=False, r=False)
    x_np_vlm = f(dv["x_np"])
    log(f"   VLM (govdesiz, M=0) CL_alpha={f(dv['CLa']):.3f}/rad, x_np={x_np_vlm:.4f} m "
        f"(govde destabilize etkisi ~{100*(x_np_vlm-x_np)/mac:.1f}% MAC)")

    # elevator etkinligi
    def coeffs(alpha, de=0.0, V=V, ref=mfull, defl_extra=None):
        dd = {"elevator": de}
        if defl_extra:
            dd.update(defl_extra)
        ap = airplane(defl=dd, xyz_ref=[ref["x_cg"], 0, ref["z_cg"]])
        r = ab(ap, opp(V, alpha=alpha))
        return f(r["CL"]), f(r["CD"]), f(r["Cm"])

    CL0, CD0a, Cm0 = coeffs(0.0)
    CLe, _, Cme = coeffs(0.0, de=2.0)
    CLde = (CLe - CL0) / math.radians(2.0)
    Cmde = (Cme - Cm0) / math.radians(2.0)
    log(f"   CL_de={CLde:.3f}/rad  Cm_de={Cmde:.3f}/rad  (2 deg sonlu fark)")

    def trim(V, ref, defl_extra=None, alt=300.0):
        rho_ = f(asb.Atmosphere(altitude=alt).density())
        W = ref["m"] * G
        CLreq = W / (0.5 * rho_ * V ** 2 * Sref)
        # 2x2 lineer cozum (alfa, de) iki iterasyon
        a, de = 0.5, 0.0
        for _ in range(3):
            c0 = coeffs(a, de, V, ref, defl_extra)
            ca = coeffs(a + 1.0, de, V, ref, defl_extra)
            cd = coeffs(a, de + 1.0, V, ref, defl_extra)
            J = np.array([[ca[0] - c0[0], cd[0] - c0[0]], [ca[2] - c0[2], cd[2] - c0[2]]])
            rhs = np.array([CLreq - c0[0], -c0[2]])
            da, dde = np.linalg.solve(J, rhs)
            a, de = a + da, de + dde
        c = coeffs(a, de, V, ref, defl_extra)
        return dict(alpha=a, de=de, CL=c[0], CD=c[1], Cm=c[2], CLreq=CLreq,
                    D=0.5 * rho_ * V ** 2 * Sref * c[1])

    t750f = trim(V, mfull)
    t750e = trim(V, mempty)
    log("\n   Trim (yuksek hiz):")
    for n, t in [("750 km/h tam yakit", t750f), ("750 km/h bos", t750e)]:
        log(f"   {n:28s}: alfa={t['alpha']:+.2f} deg  de={t['de']:+.2f} deg  CL={t['CL']:.4f}  "
            f"CD={t['CD']:.5f}  D={t['D']:.0f} N")

    # ---- iter3: tek yarikli flap - ampirik model (AeroBuildup'in buyuk sapma flap verisi kullanilmaz)
    fl = P.WING["flap"]
    clmax2d = pol["naca64a007"]["1.5e+06"]["Clmax"]
    sw_c4 = math.atan(math.tan(math.radians(P.WING["sweep_le"])) - (wg["cr"] - wg["ct"]) / (2 * b))
    CLmax_clean = 0.9 * clmax2d * math.cos(sw_c4)

    def area_frac(e0, e1):
        lam = P.WING["taper"]
        A = lambda e: e - (1 - lam) * e ** 2 / 2
        return (A(e1) - A(e0)) / A(1.0)
    Sflap = area_frac(fl["eta0"], fl["eta1"])
    sw_h = math.atan(math.tan(math.radians(P.WING["sweep_le"])) - (1 - fl["cf"]) * (wg["cr"] - wg["ct"]) / (b / 2))
    th_f = math.acos(2 * fl["cf"] - 1)
    tau_f = 1 - (th_f - math.sin(th_f)) / math.pi          # ince profil flap etkinligi
    cla2d = pol["naca64a007"]["1.5e+06"]["Cl_alpha_per_rad"]
    # Dcl_max (2B): nominal Raymer tek yarikli 1.3*c'/c (c'/c=1.05); muhafazakar 0.9*cf/0.25
    DCLMAX2D = dict(nominal=1.3 * 1.05, muhafazakar=0.9 * fl["cf"] / 0.25)

    def flap_model(delta, case="nominal"):
        """delta [deg] -> dCLmax, dCL0 (sabit alfa), dCm0 (kanat / kanat+kuyruk downwash), dCD."""
        sc = min(1.0, delta / 35.0) ** 0.8              # sapma olcegi (35 deg ~ tam etki)
        dclmax = DCLMAX2D[case] * sc
        dCLmax = 0.9 * dclmax * Sflap * math.cos(sw_h)
        eta = 0.75 if delta <= 20 else 0.75 - 0.2 * (delta - 20) / 15   # yarikli flap etkinlik kaybi
        dcl0 = cla2d * tau_f * eta * math.radians(delta)
        dCL0 = 0.9 * dcl0 * Sflap * math.cos(sw_h)
        # moment: 2B dCm_c/4 ~ -0.28 dcl (yerel veter) + flap merkezinin MAC c/4 onunde olmasi
        y_fl = (fl["eta0"] + fl["eta1"]) / 2 * b / 2
        c_fl = wg["cr"] - (wg["cr"] - wg["ct"]) * y_fl / (b / 2)
        x_c4_fl = P.WING["x_root_le"] + y_fl * math.tan(math.radians(P.WING["sweep_le"])) + 0.25 * c_fl
        dCm_w = dCL0 * (-0.28 * c_fl / mac + (wg["x_ac"] - x_c4_fl) / mac)
        # kuyruk: flap kaynakli ek downwash -> burun yukari
        d_eps = 2 * dCL0 / (math.pi * P.WING["AR"])
        dCm_t = +a_t * 0.9 * Vh_ * d_eps
        dCD = 0.0074 * fl["cf"] * Sflap * max(0.0, delta - 10)    # Raymer 12.61 (yarikli)
        return dict(dCLmax=dCLmax, dCL0=dCL0, dCm_w=dCm_w, dCm_t=dCm_t, dCm=dCm_w + dCm_t, dCD=dCD)

    # yatay kuyruk egimi (Helmbold) ve hacim katsayisi
    hg_ = P.surface_geom(P.HTAIL)
    A_t = P.HTAIL["AR"]
    sw_half_t = math.atan(math.tan(math.radians(P.HTAIL["sweep_le"])) - (hg_["cr"] - hg_["ct"]) / hg_["b"])
    a_t = 2 * math.pi * A_t / (2 + math.sqrt(4 + A_t ** 2 * (1 + math.tan(sw_half_t) ** 2)))
    Vh_ = P.HTAIL["S"] * (hg_["x_ac"] - mfull["x_cg"]) / (Sref * mac)

    rho0 = f(asb.Atmosphere(altitude=0).density())
    land = P.mass_summary(0.25)          # inis %25 yakit
    trim_pen = 0.05

    def lin_model(ref, Vl=28.0, alt=0.0):
        """Dusuk hiz temiz lineer model (AeroBuildup), alfa=4 deg etrafinda."""
        c00 = coeffs(4.0, 0.0, Vl, ref)
        ca = coeffs(6.0, 0.0, Vl, ref)
        ce = coeffs(4.0, -4.0, Vl, ref)
        return dict(CL0=c00[0] - (ca[0] - c00[0]) / 2 * 4, CLa=(ca[0] - c00[0]) / 2,
                    Cm0=c00[2] - (ca[2] - c00[2]) / 2 * 4, Cma=(ca[2] - c00[2]) / 2,
                    CLde=(ce[0] - c00[0]) / -4, Cmde=(ce[2] - c00[2]) / -4,
                    CD4=c00[1], CDa=(ca[1] - c00[1]) / 2)   # turevler /deg

    def trim_lin(lm, CLreq, dCL=0.0, dCm=0.0):
        A = np.array([[lm["CLa"], lm["CLde"]], [lm["Cma"], lm["Cmde"]]])
        rhs = np.array([CLreq - lm["CL0"] - dCL, -lm["Cm0"] - dCm])
        a, de = np.linalg.solve(A, rhs)
        return float(a), float(de)

    lm_land = lin_model(land)
    lm_full = lin_model(mfull)
    flapres = {}
    log("\n   Tek yarikli flap (cf=%.2f, eta %.2f-%.2f, Sflap/S=%.2f, tau=%.2f, Helmbold a_t=%.2f/rad):"
        % (fl["cf"], fl["eta0"], fl["eta1"], Sflap, tau_f, a_t))
    for case in ("nominal", "muhafazakar"):
        fm_l = flap_model(fl["defl_land"], case)
        fm_t = flap_model(18.0, case)
        CLmax_l = CLmax_clean + fm_l["dCLmax"] - trim_pen
        CLmax_t = CLmax_clean + fm_t["dCLmax"] - trim_pen
        Vs_l = math.sqrt(2 * land["m"] * G / (rho0 * Sref * CLmax_l))
        Vs_t = math.sqrt(2 * mfull["m"] * G / (rho0 * Sref * CLmax_t))
        flapres[case] = dict(fm_land=fm_l, fm_to=fm_t, CLmax_land=CLmax_l, CLmax_to=CLmax_t,
                             Vs_land=Vs_l, Vs_to=Vs_t)
        log(f"   [{case}] 2B Dcl_max={DCLMAX2D[case]:.2f}: flap {fl['defl_land']:.0f} deg dCLmax=+{fm_l['dCLmax']:.3f}, "
            f"dCL0=+{fm_l['dCL0']:.3f}, dCm0 kanat={fm_l['dCm_w']:+.3f} / +kuyruk downwash={fm_l['dCm']:+.3f}, "
            f"dCD=+{fm_l['dCD']:.4f}")
        log(f"   [{case}] CLmax temiz={CLmax_clean:.2f} -> inis {CLmax_l:.2f} (trimli), kalkis(18 deg) {CLmax_t:.2f}; "
            f"Vs inis ({land['m']:.1f} kg)={Vs_l*3.6:.0f} km/h, Vs kalkis ({mfull['m']:.1f} kg)={Vs_t*3.6:.0f} km/h, "
            f"temas 1.1Vs={1.1*Vs_l*3.6:.0f} km/h")
    Vs_land = flapres["nominal"]["Vs_land"]
    Vs_to = flapres["muhafazakar"]["Vs_to"]       # dolly birakma muhafazakar degere gore
    CLmax_land = flapres["nominal"]["CLmax_land"]

    # yaklasma trimi 1.3 Vs (nominal), %25 yakit
    Vapp = 1.3 * Vs_land
    fmL = flapres["nominal"]["fm_land"]
    CLapp = land["m"] * G / (0.5 * rho0 * Vapp ** 2 * Sref)
    a_app, de_app = trim_lin(lm_land, CLapp, fmL["dCL0"], fmL["dCm"])
    a_appc, de_appc = trim_lin(lm_land, CLapp)
    CD_app_clean = lm_land["CD4"] + lm_land["CDa"] * (a_appc - 4)
    CD_app = CD_app_clean + fmL["dCD"]
    q_app = 0.5 * rho0 * Vapp ** 2
    tapp = dict(V=Vapp, alpha=a_app, de=de_app, CL=CLapp, CD=CD_app, D=q_app * Sref * CD_app)
    tapp_clean = dict(V=Vapp, alpha=a_appc, de=de_appc, CL=CLapp, CD=CD_app_clean, D=q_app * Sref * CD_app_clean)
    log(f"   Yaklasma 1.3Vs={Vapp*3.6:.0f} km/h (%25 yakit): flap {fl['defl_land']:.0f}: alfa={a_app:+.2f} de={de_app:+.2f} "
        f"CD={CD_app:.4f} D={tapp['D']:.0f} N | flapsiz: alfa={a_appc:+.2f} de={de_appc:+.2f} D={tapp_clean['D']:.0f} N")

    # ---- 3. yanal/yon
    Cnb, Clb, CYb = f(d0["Cnb"]), f(d0["Clb"]), f(d0["CYb"])
    Clp, Cnr, Cmq_, Cnp, Clr = f(d0["Clp"]), f(d0["Cnr"]), f(d0["Cmq"]), f(d0["Cnp"]), f(d0["Clr"])
    vg = P.vtail_geom()
    hg = P.surface_geom(P.HTAIL)
    Vv = P.VTAIL["S"] * (vg["x_ac"] - mfull["x_cg"]) / (Sref * b)
    Vh = P.HTAIL["S"] * (hg["x_ac"] - mfull["x_cg"]) / (Sref * mac)
    d_ls_lat = d_ls
    log("\n[3] Yanal/yon kararlilik (750 km/h):")
    log(f"   Cn_beta={Cnb:+.4f}/rad  Cl_beta={Clb:+.4f}/rad  CY_beta={CYb:+.3f}/rad")
    log(f"   Dusuk hiz (alfa 4): Cn_beta={f(d_ls_lat['Cnb']):+.4f}  Cl_beta={f(d_ls_lat['Clb']):+.4f}")
    log(f"   Kuyruk hacim katsayilari: V_h={Vh:.3f}  V_v={Vv:.4f}")
    log(f"   Sonum: Cl_p={Clp:.3f}  Cn_r={Cnr:.4f}  Cm_q={Cmq_:.2f}")

    # ---- 4. surukleme
    q = 0.5 * rho * V ** 2
    log("\n[4] Surukleme (750 km/h, trim):")
    log(f"   AeroBuildup CD={t750f['CD']:.5f} (CL={t750f['CL']:.4f}) -> D={t750f['D']:.0f} N")
    # iter5 inceleme: sizing.py degeri sabit 0.0183 yerine sizing modelinden hesaplanir (750 km/h'te CD0 ~0.0195)
    import sizing as SZ  # noqa: E402
    D_sz, i_sz = SZ.drag(SZ.DESIGN, V, mfull["m"])
    CD_sz = D_sz / (q * Sref)
    log(f"   sizing.py CD0={i_sz['CD0']:.4f} (CD={CD_sz:.4f}) -> D={D_sz:.0f} N ; AeroBuildup farki %{100*(t750f['CD']/CD_sz-1):+.0f}")
    log(f"   +%12 alik/egzoz/bosluk payi eklenmis gercekci itki ihtiyaci ~{1.12*t750f['D']:.0f} N")

    # polar grafigi
    al = np.linspace(-2, 6, 9)
    cls, cds, cms = [], [], []
    for a in al:
        r = ab(ap_full, opp(V, alpha=a))
        cls.append(f(r["CL"])); cds.append(f(r["CD"])); cms.append(f(r["Cm"]))
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.2))
    axs[0].plot(al, cls, "o-"); axs[0].set_xlabel("alfa [deg]"); axs[0].set_ylabel("CL")
    axs[1].plot(cds, cls, "o-"); axs[1].set_xlabel("CD"); axs[1].set_ylabel("CL")
    axs[2].plot(al, cms, "o-"); axs[2].set_xlabel("alfa [deg]"); axs[2].set_ylabel("Cm (tam yakit CG)")
    for a in axs:
        a.grid(alpha=.3)
    fig.suptitle("Ucak polari - 750 km/h, de=0 (AeroBuildup)")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "ucak_polari_750.png"), dpi=120); plt.close(fig)

    # ---- 5. dinamik modlar (klasik yaklasimlar)
    m = mfull["m"]
    L = P.FUSELAGE["length"]
    Ixx = m * (0.25 * b / 2) ** 2 * 4 / 4  # Roskam R_x~0.25 (b/2 normlu degil -> b*Rx/2)
    Ixx = m * (b * 0.25 / 2) ** 2
    Iyy = m * (L * 0.38 / 2) ** 2
    Izz = m * ((b + L) / 2 * 0.52 / 2) ** 2
    Ix_ = Ixx
    log("\n[5] Dinamik modlar (750 km/h, tam yakit; Roskam atalet yaricaplari):")
    log(f"   Ixx~{Ixx:.3f}  Iyy~{Iyy:.3f}  Izz~{Izz:.3f} kg.m2 (tahmini)")
    # kisa periyot
    Za = -(CLa + t750f["CD"]) * q * Sref / (m * V)
    Ma = Cma * q * Sref * mac / Iyy
    Mq = Cmq * q * Sref * mac ** 2 / (2 * V * Iyy)
    Cmad = 0.3 * Cmq   # alfa-dot ~ %30 Cmq (yaklasik)
    Mad = Cmad * q * Sref * mac ** 2 / (2 * V * Iyy)
    wn_sp = math.sqrt(max(1e-9, Za * Mq - Ma))
    z_sp = -(Mq + Mad + Za) / (2 * wn_sp)
    log(f"   Kisa periyot: wn={wn_sp:.1f} rad/s ({wn_sp/(2*math.pi):.2f} Hz), sonum zeta={z_sp:.2f}")
    # dutch roll
    Nb = Cnb * q * Sref * b / Izz
    Nr = Cnr * q * Sref * b ** 2 / (2 * V * Izz)
    Yb = CYb * q * Sref / m
    wn_dr = math.sqrt(max(1e-9, Nb + Yb * Nr / V))
    z_dr = -(Nr + Yb / V) / (2 * wn_dr)
    # roll modu
    Lp = Clp * q * Sref * b ** 2 / (2 * V * Ixx)
    tau_r = -1 / Lp
    log(f"   Dutch roll: wn={wn_dr:.1f} rad/s ({wn_dr/(2*math.pi):.2f} Hz), zeta={z_dr:.3f}")
    log(f"   Roll modu zaman sabiti tau={tau_r*1000:.0f} ms")
    # spiral (Cl_beta*Cn_r - Cn_beta*Cl_r > 0 ise kararli)
    spiral = Clb * Cnr - Cnb * Clr
    log(f"   Spiral kriteri Clb*Cnr - Cnb*Clr = {spiral:+.5f} ({'kararli' if spiral > 0 else 'kararsiz (yavas, pilot duzeltir)'})")

    # ---- 6. kontrol otoritesi (iter2 yuksek hiz limitleri)
    LIM = dict(aileron=2.0, elevator=1.5, rudder=2.0)
    # aileron
    ap_a = airplane(defl={"aileron": LIM["aileron"]},
                    xyz_ref=[mfull["x_cg"], 0, mfull["z_cg"]])
    r_a = ab(ap_a, opp(V, alpha=t750f["alpha"]))
    r_0 = ab(ap_full, opp(V, alpha=t750f["alpha"]))
    dCl_a = f(r_a["Cl"]) - f(r_0["Cl"])
    # asb ControlSurface symmetric=False: sag/sol zit sapma -> Cl uretir
    if abs(dCl_a) < 1e-6:
        # analitik yedek: serit teorisi
        tau = 0.42  # cf=0.18 icin flap etkinligi
        al_ = P.WING["aileron"]
        y0, y1 = al_["eta0"] * b / 2, al_["eta1"] * b / 2
        cr, ct = wg["cr"], wg["ct"]
        c = lambda y: cr - (cr - ct) * y / (b / 2)
        ys = np.linspace(y0, y1, 50)
        Cl_da = 2 * 5.5 * tau / (Sref * b) * np.trapezoid(c(ys) * ys, ys)
        dCl_a = Cl_da * math.radians(LIM["aileron"])
        src = "serit teorisi"
    else:
        src = "AeroBuildup"
    pb2V = -dCl_a / Clp
    p_rate = pb2V * 2 * V / b
    p_rate_800 = p_rate * P.V_OPER_MAX / V
    log("\n[6] Kontrol otoritesi (yuksek hiz limitleri: aileron +-2, elevator +-1.5, rudder +-2 deg):")
    log(f"   Aileron +-{LIM['aileron']:.0f} deg @750: dCl={dCl_a:+.5f} ({src}) "
        f"-> pb/2V={abs(pb2V):.3f}, p={abs(math.degrees(p_rate)):.0f} deg/s "
        f"(@800: {abs(math.degrees(p_rate_800)):.0f} deg/s)")
    # elevator g (tam ve bos yakit; SM farkli)
    de = LIM["elevator"]
    elev = {}
    for nme, ms in [("tam", mfull), ("bos", mempty)]:
        ap_ = airplane(xyz_ref=[ms["x_cg"], 0, ms["z_cg"]])
        d_ = ab(ap_, opp(V, alpha=0.3), deriv=True)
        Cma_ = f(d_["Cma"])
        c0 = coeffs(0.3, 0.0, V, ms)
        c1 = coeffs(0.3, 1.0, V, ms)
        Cmde_ = (c1[2] - c0[2]) / math.radians(1.0)
        CLde_ = (c1[0] - c0[0]) / math.radians(1.0)
        dalpha = -Cmde_ * math.radians(de) / Cma_
        dCL = CLa * dalpha + CLde_ * math.radians(de)
        dn = abs(dCL) * q * Sref / (ms["m"] * G)
        dn800 = dn * (P.V_OPER_MAX / V) ** 2
        elev[nme] = dict(dn=dn, dn800=dn800, grad=de / dn)
        log(f"   Elevator +-{de} deg @750 ({nme} yakit): ~{dn:.1f} g (@800: {dn800:.1f} g), "
            f"gradyan {de/dn:.3f} deg/g (limit {P.N_LIMIT:.0f} g)")
    dn = elev["tam"]["dn"]
    # rudder -> kararli sapma acisi
    c_r0 = ab(ap_full, opp(V, alpha=t750f["alpha"]))
    ap_rd = airplane(defl={"rudder": LIM["rudder"]}, xyz_ref=[mfull["x_cg"], 0, mfull["z_cg"]])
    c_r1 = ab(ap_rd, opp(V, alpha=t750f["alpha"]))
    Cn_dr = (f(c_r1["Cn"]) - f(c_r0["Cn"])) / math.radians(LIM["rudder"])
    beta_ss = -Cn_dr * math.radians(LIM["rudder"]) / Cnb
    ny = abs(CYb * beta_ss) * q * Sref / (m * G)
    log(f"   Rudder +-{LIM['rudder']:.0f} deg @750: Cn_dr={Cn_dr:+.4f}/rad -> kararli sapma "
        f"{abs(math.degrees(beta_ss)):.2f} deg, yanal yuk ~{ny:.2f} g")

    # ---- 6b. yaw damper (Dutch roll sonumu)
    Ndr = Cn_dr * q * Sref * b / Izz          # [1/s^2 per rad]
    zeta_t = 0.30
    Nr_req = -(2 * zeta_t * wn_dr) - Yb / V   # ayni wn varsayimi
    dNr = Nr_req - Nr
    K_yd = dNr / Ndr                          # rad rudder / (rad/s yaw rate) ; negatif isaret: r>0 -> dr<0
    log(f"\n   Yaw damper: hedef zeta_DR={zeta_t}; gerekli dN_r={dNr:+.2f} 1/s -> "
        f"K = {abs(K_yd):.4f} s (rudder deg / yaw rate deg/s) @750 km/h")
    log(f"   1 deg rudder ~ {1/abs(K_yd):.0f} deg/s yaw rate'te; dusuk hizda kazanc ~(750/V)^2 "
        f"ile olceklenmeli (hiza bagli kazanc). Yikanan (washout) filtre tau~1 s, rudder siniri +-2 deg.")

    # ---- 6c. dolly kalkisi (iter2): sabit alfa, birakma hizi, trim elevatoru (tam yakit)
    Vrel = 1.20 * Vs_to
    fmT = flapres["muhafazakar"]["fm_to"]
    CLrel = mfull["m"] * G / (0.5 * rho0 * Vrel ** 2 * Sref)
    to = {}
    for case in ("nominal", "muhafazakar"):
        fm = flapres[case]["fm_to"]
        a_, de_ = trim_lin(lm_full, CLrel, fm["dCL0"], fm["dCm"])
        a2, de2 = trim_lin(lm_full, CLrel, fm["dCL0"], fm["dCm_w"])   # kuyruk downwash kredisi yok
        to[case] = dict(alpha=a_, de=de_, de_nodw=de2, alpha_nodw=a2)
    to_ = to["nominal"]
    to.update(alpha=to_["alpha"], de=to_["de"], CL=CLrel)
    log("\n   Dolly kalkisi (tam yakit, flap 18 deg, deniz seviyesi):")
    log(f"   Vs_TO (muhafazakar)={Vs_to*3.6:.0f} km/h; birakma hizi 1.2Vs = {Vrel*3.6:.0f} km/h ({Vrel:.1f} m/s), CL={CLrel:.3f}")
    for case in ("nominal", "muhafazakar"):
        t_ = to[case]
        log(f"   [{case} flap] dolly alfa={t_['alpha']:+.2f} deg, trim de={t_['de']:+.2f} deg "
            f"(downwash kredisiz: alfa={t_['alpha_nodw']:+.2f}, de={t_['de_nodw']:+.2f})")

    # ---- 6d. kizakla inis flare (%25 yakit CG, flap 35)
    de_max = -P.HTAIL["elevator"]["defl_max_ls"]
    # yer etkisi: h/b ~ (kizak->kanat ~0.09 m)/b ; downwash azalmasi (Wetmore-Turner yaklasimi)
    h_w = 0.09 + 0.25 * P.wing_geom()["mac"] * math.sin(math.radians(9))
    hb = h_w / b
    phi_ge = (16 * hb) ** 2 / (1 + (16 * hb) ** 2)   # McCormick: yer etkisinde kalan downwash orani
    k_ge = 1 - phi_ge                  # downwash'un yok olan orani
    deps_da = 0.40                      # serbest havada d(eps)/d(alfa) (ok acili, AR 5)
    flare = {}
    log(f"\n   Kizakla inis flare (%25 yakit, flap {fl['defl_land']:.0f}; h/b={hb:.3f}, yer etkisinde downwash "
        f"%{100*k_ge:.0f} azalir):")
    log(f"   Inis kutlesi {land['m']:.2f} kg, CG x={land['x_cg']:.3f}, SM %{100*(x_np-land['x_cg'])/mac:.1f}")
    for case in ("nominal", "muhafazakar"):
        fm = flapres[case]["fm_land"]
        V_td = 1.10 * flapres[case]["Vs_land"]
        CL_td = land["m"] * G / (0.5 * rho0 * V_td ** 2 * Sref)
        a_td, de_td = trim_lin(lm_land, CL_td, fm["dCL0"], fm["dCm_w"])   # kotumser: downwash kredisi yok
        eps = deps_da * CL_td / (lm_land["CLa"] * 57.2958)                  # rad
        dCm_ge = -a_t * 0.9 * Vh_ * k_ge * eps
        dde_ge = -dCm_ge / lm_land["Cmde"]                                   # deg (- = yukari)
        de_tot = de_td + dde_ge
        flare[case] = dict(V_td_kmh=V_td * 3.6, CL_td=CL_td, alpha_td=a_td, de_td=de_td,
                           dde_ge=dde_ge, de_total=de_tot, margin=de_tot - de_max)
        log(f"   [{case}] temas {V_td*3.6:.0f} km/h CL={CL_td:.3f}: alfa={a_td:+.2f} deg, de={de_td:+.2f} deg; "
            f"yer etkisi payi {dde_ge:+.2f} deg -> toplam {de_tot:+.2f} deg (limit {de_max:.0f}, pay {de_tot-de_max:.1f} deg)")
    M_net = None
    t_td = flare["nominal"]
    V_td = t_td["V_td_kmh"] / 3.6
    CL_td = t_td["CL_td"]

    out.update(dict(
        x_np=x_np, x_np_lowspeed=x_np_ls, x_np_vlm_nofus=x_np_vlm,
        SM_full=sm_full, SM_empty=sm_empty, CLa=CLa, Cma=Cma, Cmq=Cmq, CLde=CLde, Cmde=Cmde,
        trim_750_full=t750f, trim_750_empty=t750e, trim_app_flap=tapp, trim_app_clean=tapp_clean,
        CLmax_clean=CLmax_clean, CLmax_land=CLmax_land, Vs_land_kmh=Vs_land * 3.6, Vs_to_kmh=Vs_to * 3.6,
        Cnb=Cnb, Clb=Clb, CYb=CYb, Clp=Clp, Cnr=Cnr, Vh=Vh, Vv=Vv,
        D_750=t750f["D"], sp_wn=wn_sp, sp_zeta=z_sp, dr_wn=wn_dr, dr_zeta=z_dr, roll_tau=tau_r,
        spiral=spiral, roll_rate_dps=abs(math.degrees(p_rate)), elev_g=dn, rotation_moment=M_net,
        inertia=dict(Ixx=Ixx, Iyy=Iyy, Izz=Izz),
    ))

    # ---- 8. iter3: alcak kanat Cl_beta (DATCOM govde-kanat duzeltmesi) + dihedral secimi + yanal 4x4 modlar
    log("\n[8] Alcak kanat - Cl_beta ve dihedral secimi:")
    A_w = P.WING["AR"]
    z_w = -P.WING["z_root"]                       # govde ekseninin altinda (+)
    D_f = P.FUSELAGE["d_max"]
    dClb_zw = 1.2 * math.sqrt(A_w) * (z_w / b) * (2 * D_f / b)   # DATCOM 5.2.1.1 (/rad), alcak kanat -> +
    log(f"   DATCOM govde-kanat ΔCl_beta(z_w={z_w*1000:.0f} mm, D={D_f*1000:.0f} mm) = {dClb_zw:+.4f}/rad (destabilize)")
    G0 = P.WING["dihedral"]

    def lat_derivs(gamma, Vx, alpha, ref):
        P.WING["dihedral"] = gamma
        try:
            ap_ = airplane(xyz_ref=[ref["x_cg"], 0, ref["z_cg"]])
            d_ = ab(ap_, opp(Vx, alt=0.0 if Vx < 60 else 300.0, alpha=alpha), deriv=True)
        finally:
            P.WING["dihedral"] = G0
        return {k: f(d_[k]) for k in ("CYb", "Clb", "Cnb", "Clp", "Cnp", "Clr", "Cnr")}

    hs_cond = (V, t750f["alpha"], mfull)
    ls_cond = (Vapp, a_appc, land)          # yaklasma (flapsiz alfa; flap Cl_beta'yi biraz artirir)
    der = {}
    for gm in (0.0, 2.0):
        der[("hs", gm)] = lat_derivs(gm, *hs_cond)
        der[("ls", gm)] = lat_derivs(gm, *ls_cond)
    slope_hs = (der[("hs", 2.0)]["Clb"] - der[("hs", 0.0)]["Clb"]) / 2.0
    slope_ls = (der[("ls", 2.0)]["Clb"] - der[("ls", 0.0)]["Clb"]) / 2.0
    slope_th = -lm_land["CLa"] * 57.2958 * (1 + 2 * P.WING["taper"]) / (6 * (1 + P.WING["taper"])) / 57.2958
    log(f"   dCl_beta/dGamma: AeroBuildup {slope_hs:+.4f} (750) / {slope_ls:+.4f} (yaklasma) /rad/deg; "
        f"serit teorisi {slope_th:+.4f}")

    def clb_tot(gm, reg):
        return der[(reg, 0.0)]["Clb"] + dClb_zw + (slope_hs if reg == "hs" else slope_ls) * gm

    rows = []
    for gm in (-1.0, 0.0, 1.0, 2.0, 3.0):
        rows.append((gm, clb_tot(gm, "hs"), clb_tot(gm, "ls")))
        log(f"   Gamma={gm:+.0f} deg: Cl_beta 750 km/h={clb_tot(gm,'hs'):+.4f}  yaklasma={clb_tot(gm,'ls'):+.4f} /rad")
    target = -0.035   # bant (-0.02..-0.04) icinde; yaklasmada spiral ikilenme suresini uzatmak icin bandin stabil yarisi
    G_req = (target - der[("hs", 0.0)]["Clb"] - dClb_zw) / slope_hs
    G_rec = round(min(3.0, max(-1.0, G_req)) * 2) / 2
    log(f"   Hedef Cl_beta={target} (750 km/h) icin gereken dihedral = {G_req:+.2f} deg -> onerilen {G_rec:+.1f} deg "
        f"(750: {clb_tot(G_rec,'hs'):+.4f}, yaklasma: {clb_tot(G_rec,'ls'):+.4f})")

    def lat_modes(dd, Clb_, Vx, ref, rho_, dNr=0.0):
        mq = 0.5 * rho_ * Vx ** 2
        m_ = ref["m"]
        Ix = m_ * (b * 0.25 / 2) ** 2
        Iz = m_ * ((b + L) / 2 * 0.52 / 2) ** 2
        Yb_ = dd["CYb"] * mq * Sref / m_
        Lb_ = Clb_ * mq * Sref * b / Ix
        Nb_ = dd["Cnb"] * mq * Sref * b / Iz
        k = mq * Sref * b ** 2 / (2 * Vx)
        Lp_, Lr_ = dd["Clp"] * k / Ix, dd["Clr"] * k / Ix
        Np_, Nr_ = dd["Cnp"] * k / Iz, dd["Cnr"] * k / Iz + dNr
        Am = np.array([[Yb_ / Vx, 0.0, -1.0, G / Vx],
                       [Lb_, Lp_, Lr_, 0.0],
                       [Nb_, Np_, Nr_, 0.0],
                       [0.0, 1.0, 0.0, 0.0]])
        ev = np.linalg.eigvals(Am)
        cplx = [e for e in ev if abs(e.imag) > 1e-6]
        real = sorted([e.real for e in ev if abs(e.imag) <= 1e-6])
        dr = cplx[0] if cplx else complex(0, 0)
        wn = abs(dr)
        zeta = -dr.real / wn if wn > 0 else float("nan")
        roll = real[0] if real else float("nan")
        spir = real[-1] if real else float("nan")
        return dict(wn=wn, zeta=zeta, roll_tau=-1 / roll, spiral_eig=spir,
                    spiral_t=(math.log(2) / abs(spir)) if spir != 0 else float("inf"),
                    Nr_unit=Iz, Ndr_k=mq * Sref * b / Iz)

    rho_hs = rho
    lat = {}
    log("   Yanal modlar (4x4 durum matrisi [beta,p,r,phi]; Ixz=0):")
    for gm in sorted({0.0, 1.0, 1.5, 2.0, G_rec}):
        for reg, (Vx, ax_, ref) in (("hs", hs_cond), ("ls", ls_cond)):
            dd = der[(reg, 0.0)]
            rr = rho_hs if reg == "hs" else rho0
            res = lat_modes(dd, clb_tot(gm, reg), Vx, ref, rr)
            lat[(gm, reg)] = res
            spiral_txt = (f"kararli (yari sure {res['spiral_t']:.0f} s)" if res["spiral_eig"] < 0
                          else f"kararsiz (ikilenme {res['spiral_t']:.0f} s)")
            log(f"   Gamma={gm:+.1f} {('750 km/h' if reg=='hs' else 'yaklasma')}: DR wn={res['wn']:.1f} rad/s "
                f"zeta={res['zeta']:.3f}, roll tau={res['roll_tau']*1000:.0f} ms, spiral {spiral_txt}")
    # yaw damper (onerilen dihedral, 750 km/h): zeta=0.30 icin dNr bisection
    dd = der[("hs", 0.0)]
    lo_, hi_ = 0.0, -60.0
    for _ in range(50):
        mid = 0.5 * (lo_ + hi_)
        if lat_modes(dd, clb_tot(G_rec, "hs"), V, mfull, rho_hs, dNr=mid)["zeta"] < 0.30:
            lo_ = mid
        else:
            hi_ = mid
    dNr_req = 0.5 * (lo_ + hi_)
    Ndr_hs = Cn_dr * lat[(G_rec, "hs")]["Ndr_k"]
    K_yd4 = abs(dNr_req / Ndr_hs)
    yd = lat_modes(dd, clb_tot(G_rec, "hs"), V, mfull, rho_hs, dNr=dNr_req)
    log(f"   Yaw damper (Gamma={G_rec:+.1f}, 750 km/h, 4x4): zeta 0.30 icin dN_r={dNr_req:+.2f} 1/s -> "
        f"K={K_yd4:.4f} deg rudder/(deg/s); damperli DR wn={yd['wn']:.1f} rad/s")
    ddl = der[("ls", 0.0)]
    K_ls = K_yd4 * (V / Vapp) ** 2           # hiza bagli kazanc: K ~ (V_hs/V)^2
    dNr_ls = -K_ls * Cn_dr * lat[(G_rec, "ls")]["Ndr_k"]
    yl = lat_modes(ddl, clb_tot(G_rec, "ls"), Vapp, land, rho0, dNr=dNr_ls)
    yl_half = lat_modes(ddl, clb_tot(G_rec, "ls"), Vapp, land, rho0, dNr=dNr_ls / 2)
    K_yd_ls = K_ls
    log(f"   Yaw damper yaklasmada ({Vapp*3.6:.0f} km/h) K=K_hs*(V_hs/V)^2={K_ls:.3f} deg/(deg/s): DR zeta "
        f"{lat[(G_rec,'ls')]['zeta']:.3f} -> {yl['zeta']:.3f} (yari kazancla {yl_half['zeta']:.3f}); "
        f"spiral {'kararli' if yl['spiral_eig']<0 else 'kararsiz'} ({yl['spiral_t']:.0f} s)")
    out["dihedral"] = dict(K_yd_ls=K_yd_ls, dClb_zw=dClb_zw, slope_hs=slope_hs, slope_ls=slope_ls, G_req=G_req, G_rec=G_rec,
                           table=rows, lat={f"{k[0]:+.1f}_{k[1]}": v for k, v in lat.items()},
                           yaw_damper_K=K_yd4, dNr_req=dNr_req)

    # statik marj vs CG grafigi
    xs = np.linspace(wg["x_mac_le"], wg["x_mac_le"] + 0.6 * mac, 50)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(100 * (xs - wg["x_mac_le"]) / mac, 100 * (x_np - xs) / mac)
    ax.axhspan(8, 15, color="g", alpha=.15, label="hedef %8-15")
    for nme, ms in [("tam yakit", mfull), ("bos", mempty)]:
        ax.axvline(100 * (ms["x_cg"] - wg["x_mac_le"]) / mac, ls="--", label=f"CG {nme}")
    ax.axvline(100 * (x_np - wg["x_mac_le"]) / mac, color="r", label="notr nokta")
    ax.set_xlabel("CG [% MAC]"); ax.set_ylabel("Statik marj [% MAC]")
    ax.grid(alpha=.3); ax.legend(fontsize=8)
    ax.set_title("Statik marj - CG konumu (750 km/h)")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "statik_marj.png"), dpi=120); plt.close(fig)

    # geometri gorunumu
    try:
        ap_full.draw_three_view(show=False)
        plt.savefig(os.path.join(OUT, "asb_uc_gorunus.png"), dpi=110)
        plt.close("all")
    except Exception as e:  # cizim opsiyonel
        log(f"   (uc gorunus cizilemedi: {e})")

    # ---- 7. yakit durumuna gore statik marj (iter2)
    log("\n[7] Yakit durumuna gore CG ve statik marj (x_np=%.4f m):" % x_np)
    smt = []
    for ff in (1.0, 0.75, 0.5, 0.25, 0.0):
        ms = P.mass_summary(ff)
        sm = (x_np - ms["x_cg"]) / mac
        smt.append(dict(fuel_frac=ff, m=ms["m"], x_cg=ms["x_cg"], SM=sm))
        log(f"   yakit %{100*ff:3.0f}: m={ms['m']:.2f} kg  x_cg={ms['x_cg']:.4f} m "
            f"(%{100*(ms['x_cg']-wg['x_mac_le'])/mac:.1f} MAC)  SM=%{100*sm:.1f}")
    out["SM_yakit_tablosu"] = smt
    out.update(dict(limits_hs=LIM, roll_rate_800_dps=abs(math.degrees(p_rate_800)), elev=elev,
                    Cn_dr=Cn_dr, beta_ss_deg=abs(math.degrees(beta_ss)), yaw_damper_K=abs(K_yd),
                    dolly=dict(V_release_kmh=Vrel * 3.6, CL=CLrel, cases={k: to[k] for k in ("nominal", "muhafazakar")}),
                    flare=dict(m=land["m"], x_cg=land["x_cg"], hb=hb, k_ge=k_ge, cases=flare),
                    flap=flapres))

    with open(os.path.join(OUT, "sonuclar.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=float)
    with open(os.path.join(OUT, "ozet.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
