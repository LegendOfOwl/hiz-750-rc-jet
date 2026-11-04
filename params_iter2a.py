"""
HIZ-750 - tek dogru kaynak (single source of truth) geometri ve kutle parametreleri.

Tum CAD, analiz ve dokumantasyon scriptleri bu dosyayi import eder:
    import sys; sys.path.insert(0, <proje koku>); from params import *

Koordinat sistemi (govde ekseni):
    x : burun ucundan arkaya [m]
    y : sag kanada dogru [m]
    z : yukari [m]
Birimler SI (m, kg, N, s). Acilar derece.
"""
import math

NAME = "HIZ-750"
V_TARGET = 750 / 3.6          # [m/s] hedef olcum hizi
V_OPER_MAX = 800 / 3.6        # [m/s] ECU gaz limitiyle operasyonel azami
V_D = 900 / 3.6               # [m/s] tasarim dalis hizi (yapi/flutter)
V_FLUTTER_REQ = 1.2 * V_D     # [m/s] flutter'siz olmasi gereken hiz
N_LIMIT = 12.0                # limit yuk faktoru
N_NEG = -8.0                  # iter2: 800 km/h negatif hamle (yapi analizi)
SF = 1.5                      # nihai emniyet katsayisi

# ------------------------------------------------------------------ motor
ENGINE = dict(
    model="JetCat P400-PRO",
    F0=425.0,                 # statik itki [N]
    mass=4.05,                # [kg] (ECU, pompa haric)
    diameter=0.1484,          # [m]
    length=0.385,             # [m]
    fuel_flow_max=1.392,      # [L/min]
    mdot_air=0.75,            # [kg/s] tahmini hava debisi (P550: 0.93)
    x_front=1.18,             # motor on yuzu x konumu [m]
)

# ------------------------------------------------------------------ govde
FUSELAGE = dict(
    length=2.10,
    d_max=0.165,
    x_dmax_start=0.80,        # sabit kesit bolgesi baslangic
    x_dmax_end=1.45,
    nose_shape="ogive",       # 0..0.80 m ogive
    d_tail=0.112,             # kuyruk konisi cikis (egzoz) capi
    exhaust_pipe_d=0.105,
)

# ------------------------------------------------------------------ hava alik (dorsal, kanat arkasi, S-kanal)
INLET = dict(
    type="dorsal pitot-tipi, diverterli",
    x_lip=0.95,               # dudak konumu [m] (iter2: kanal kanat kutusu ustunden gecer)
    width=0.110,
    height=0.055,             # capture ~60 cm2 (kompresor yuzu ~62 cm2); kalkista ek emis kapaklari
    diverter_h=0.006,         # sinir tabaka ayirici yuksekligi
    duct_length=0.23,         # dudaktan motor on yuzune
)

# ------------------------------------------------------------------ kanat
WING = dict(
    S=0.42, AR=5.0, taper=0.35, sweep_le=28.0,
    dihedral=-1.0,            # hafif anhedral (ok acisinin dihedral etkisini dengeler)
    incidence=0.5,
    twist_tip=-1.0,           # uca dogru washout
    airfoil_root="naca64a007",   # AeroSandbox isimlendirmesi; CAD icin koordinat uretilir
    airfoil_tip="naca64a006",
    tc_root=0.07, tc_tip=0.06,
    x_root_le=0.92,           # kok hucum kenari x (iter2: statik marj icin one alindi)
    z_root=-0.035,            # orta-alcak kanat
    # kontrol yuzeyleri (yari-aciklik orani eta, veter orani)
    aileron=dict(eta0=0.52, eta1=0.94, cf=0.18, defl_max_hs=4.0, defl_max_ls=18.0),
    flap=dict(eta0=0.12, eta1=0.50, cf=0.22, defl_land=30.0),
    spar_xc=(0.20, 0.55),     # on/arka kiris (iter2: arka kiris motor onunde kalsin)
)

# ------------------------------------------------------------------ kuyruklar
HTAIL = dict(
    S=0.085, AR=4.0, taper=0.40, sweep_le=35.0,
    airfoil="naca0006", tc=0.06,
    x_root_le=1.84, z_root=0.0,
    elevator=dict(cf=0.28, defl_max_hs=3.0, defl_max_ls=20.0),
    all_moving=False,
    split=True,               # iter2: iki yari, egzoz borusu ustunden gecen baglanti rod'u
)
VTAIL = dict(
    S=0.060, AR=1.6, taper=0.40, sweep_le=40.0,   # tek dikey, AR yari-aciklik tanimi (h^2/S)
    airfoil="naca0006", tc=0.06,
    x_root_le=1.76, z_root=0.06,     # iter2: S buyudu, uc govde sonunu asmasin
    rudder=dict(cf=0.30, defl_max_hs=3.0, defl_max_ls=20.0),
)

# ------------------------------------------------------------------ kalkis/inis (iter2: secenek B)
# Ana tekerler 25 mm kalinlikli kanada sigmadigi ve govde alti motorla dolu oldugu icin
# geri cekilir takim kaldirildi: birakilan kalkis arabasi (dolly) + govde alti kizak ile inis.
GEAR = dict(
    type="dolly + skid",
    skid_x0=0.62, skid_x1=1.30, skid_h=0.010, skid_w=0.040,   # Kevlar/karbon kizak
    dolly_track=0.50, dolly_wheelbase=0.70,                   # yer ekipmani (ucusta yok)
)

# ------------------------------------------------------------------ kutle kalemleri: (ad, kutle kg, x [m], z [m])
MASS_ITEMS = [
    ("Govde kabugu (karbon prepreg)",          1.55, 1.05, 0.00),
    ("Kanat (kabuk+kiris+kaburga)",             1.75, 1.18, -0.03),
    ("Yatay kuyruk",                            0.30, 2.00, 0.00),
    ("Dikey kuyruk",                            0.20, 1.98, 0.14),
    ("Motor yatagi + isi kalkani",              0.35, 1.38, 0.00),
    ("Hava alik S-kanali",                      0.30, 1.07, 0.05),
    ("Egzoz borusu (bypass, Ti/celik)",         0.40, 1.88, 0.00),
    ("Yakit tanki + hopper + boru",             0.40, 0.98, 0.00),
    ("Bulkhead'ler, baglanti elemanlari",       0.50, 1.00, 0.00),
    ("Motor JetCat P400-PRO",                   ENGINE["mass"], 1.37, 0.00),
    ("ECU + pompa + valfler + GSU",             0.45, 0.75, 0.00),
    ("Servolar (7 adet HV 45-60 kg.cm)",        0.85, 1.30, -0.02),
    ("Kontrol yuzeyi balans kutleleri (W)",     0.12, 1.45, 0.00),
    ("Alici x2 + telemetri + GNSS logger",      0.20, 0.45, 0.00),
    ("Aku: RX 2S LiPo 3000 + ECU 3S 2200",      0.40, 0.35, 0.00),
    ("Pitot + hava veri sensoru + kablolar",    0.35, 0.60, 0.00),
    ("Govde alti kizak + dolly kilit mekanizmasi", 0.25, 0.96, -0.08),
    ("Boya / dolgu / balans",                   0.35, 1.00, 0.00),
]
FUEL = dict(mass=4.0, x=1.00, z=-0.01, density=0.80,   # iter2: govde ana tank (x~0.70-1.00) + kanat koku entegre tanklar
            tanks=dict(fuselage_L=3.4, wing_integral_L_each=0.9, wing_eta=(0.06, 0.40)))


def wing_geom(w=WING):
    S, AR, lam = w["S"], w["AR"], w["taper"]
    b = math.sqrt(S * AR)
    cr = 2 * S / (b * (1 + lam))
    ct = lam * cr
    mac = 2 / 3 * cr * (1 + lam + lam ** 2) / (1 + lam)
    y_mac = b / 6 * (1 + 2 * lam) / (1 + lam)
    x_mac_le = w["x_root_le"] + y_mac * math.tan(math.radians(w["sweep_le"]))
    return dict(b=b, cr=cr, ct=ct, mac=mac, y_mac=y_mac, x_mac_le=x_mac_le,
                x_ac=x_mac_le + 0.25 * mac)


def surface_geom(s):
    """Kuyruklar icin ayni tanim; dikey kuyrukta b = yukseklik (tek yan)."""
    return wing_geom(dict(s))


def vtail_geom(v=VTAIL):
    h = math.sqrt(v["S"] * v["AR"])
    cr = 2 * v["S"] / (h * (1 + v["taper"]))
    ct = v["taper"] * cr
    lam = v["taper"]
    mac = 2 / 3 * cr * (1 + lam + lam ** 2) / (1 + lam)
    z_mac = h / 3 * (1 + 2 * lam) / (1 + lam)
    x_mac_le = v["x_root_le"] + z_mac * math.tan(math.radians(v["sweep_le"]))
    return dict(h=h, cr=cr, ct=ct, mac=mac, z_mac=z_mac, x_mac_le=x_mac_le,
                x_ac=x_mac_le + 0.25 * mac)


def mass_summary(fuel_frac=1.0):
    m = sum(i[1] for i in MASS_ITEMS) + FUEL["mass"] * fuel_frac
    x = (sum(i[1] * i[2] for i in MASS_ITEMS) + FUEL["mass"] * fuel_frac * FUEL["x"]) / m
    z = (sum(i[1] * i[3] for i in MASS_ITEMS) + FUEL["mass"] * fuel_frac * FUEL["z"]) / m
    return dict(m=m, x_cg=x, z_cg=z)


if __name__ == "__main__":
    wg = wing_geom()
    print("Kanat:", {k: round(v, 4) for k, v in wg.items()})
    print("Y.kuyruk:", {k: round(v, 4) for k, v in surface_geom(HTAIL).items()})
    print("D.kuyruk:", {k: round(v, 4) for k, v in vtail_geom().items()})
    for f in (1.0, 0.0):
        ms = mass_summary(f)
        print(f"yakit {f:.0%}: m={ms['m']:.2f} kg  x_cg={ms['x_cg']:.3f} m  "
              f"(%{100*(ms['x_cg']-wg['x_mac_le'])/wg['mac']:.1f} MAC)")
