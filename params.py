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
    x_lip=0.85,               # dudak konumu [m] (iter3: kanal uzatildi)
    lip_z_center=0.088,       # iter3: yari gomulu dudak merkezi z [m] -> ofset/uzunluk ~0.27, on kesit azalir
    width=0.110,
    height=0.055,             # capture ~60 cm2 (kompresor yuzu ~62 cm2); kalkista ek emis kapaklari
    diverter_h=0.006,         # sinir tabaka ayirici yuksekligi
    duct_length=0.33,         # dudaktan motor on yuzune
)

# ------------------------------------------------------------------ kanat
WING = dict(
    S=0.42, AR=5.0, taper=0.35, sweep_le=28.0,
    dihedral=2.0,             # iter3: alcak kanat (z -80 mm) girisimi icin; Cl_beta ~ -0.037 /rad @750 km/h
    incidence=0.5,
    twist_tip=-1.0,           # uca dogru washout
    airfoil_root="naca64a007",   # AeroSandbox isimlendirmesi; CAD icin koordinat uretilir
    airfoil_tip="naca64a006",
    tc_root=0.07, tc_tip=0.06,
    x_root_le=0.92,           # kok hucum kenari x (iter2: statik marj icin one alindi)
    z_root=-0.080,            # iter3: alcak kanat; ust yuzey kok ~-50 mm, S-kanal kutunun ustunden rahat iner (karin kaplamasi)
    # kontrol yuzeyleri (yari-aciklik orani eta, veter orani)
    aileron=dict(eta0=0.52, eta1=0.94, cf=0.18, defl_max_hs=4.0, defl_max_ls=18.0),
    flap=dict(eta0=0.12, eta1=0.50, cf=0.25, defl_land=35.0, type="slotted"),   # iter3: tek yarikli flap
    spar_xc=(0.20, 0.55),     # on/arka kiris (iter2: arka kiris motor onunde kalsin)
    skin_plies=(3, 1),        # iter3: kabuk kat/yuz (kiris onu, kiris arkasi) -> kesit CG 0.45c, flutter 1500 km/h
    attach=dict(type="tek parca kanat, kutu govde icinden gecer", bolts="4x M6 12.9",
                frames_x=(1.006, 1.156), front_pins_x=0.94),   # govde icinde kanat yalniz x <= 1.156
)

# ------------------------------------------------------------------ kuyruklar
HTAIL = dict(
    S=0.085, AR=4.0, taper=0.40, sweep_le=35.0,
    airfoil="naca0006", tc=0.06,
    x_root_le=1.84, z_root=0.0,
    elevator=dict(cf=0.22, defl_max_hs=1.5, defl_max_ls=20.0),   # iter3: bos yakitta asiri otorite azaltildi
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
    skid_x0=0.62, skid_x1=1.45, skid_h=0.010, skid_w=0.040,   # iter3: kuyruk carpma acisi >= 9 deg hedefi
    dolly_track=0.50, dolly_wheelbase=0.70,                   # yer ekipmani (ucusta yok)
    tail_bumper=dict(x=1.87, depth=0.022, length=0.12),     # iter3: kuyruk carpma acisi >= 9 deg (G10/celik)
    skid_frames=(0.62, 0.81, 1.006, 1.156, 1.38),
    dolly_alpha=3.0, dolly_de_trim=-4.0,                      # iter3: aero onerisi
)

# ------------------------------------------------------------------ kutle kalemleri: (ad, kutle kg, x [m], z [m])
MASS_ITEMS = [
    ("Govde kabugu (karbon prepreg)",          1.55, 1.15, 0.00),   # iter4: CAD kabuk alan merkezi (eski 1.05)
    ("Burun balasti (tungsten) / ek RX akusu",  0.15, 0.20, 0.00),   # iter4: bos yakit SM'yi %12'ye geri getirir
    ("Kanat (kabuk 3/1 kat + kiris + kaburga)", 1.75, 1.18, -0.08),
    ("Kanat baglantisi: cerceveler + 4xM6 + blok", 0.15, 1.08, -0.06),
    ("Motor bolgesi isi kecesi + G10 plaka",    0.05, 1.38, -0.07),
    ("Yatay kuyruk",                            0.30, 2.00, 0.00),
    ("Dikey kuyruk",                            0.20, 1.98, 0.14),
    ("Motor yatagi + isi kalkani",              0.35, 1.38, 0.00),
    ("Hava alik S-kanali",                      0.30, 1.07, 0.05),
    ("Egzoz borusu (bypass, Ti/celik)",         0.40, 1.88, 0.00),
    ("Yakit tanki + hopper + boru",             0.40, 0.98, 0.00),
    ("Bulkhead'ler, baglanti elemanlari",       0.50, 1.00, 0.00),
    ("Motor JetCat P400-PRO",                   ENGINE["mass"], 1.37, 0.00),
    ("ECU + pompa + valfler + GSU",             0.45, 0.65, 0.00),
    ("Servolar: aileron+flap 4x (kanat ici)",   0.48, 1.22, -0.04),   # iter4: aileron servosu <= 60 g ince tip (flutter -%8 etkisi; FE)
    ("Servolar: elevator 2x + rudder 60 kg.cm", 0.37, 1.85, 0.03),
    ("Kontrol yuzeyi balans kutleleri (W)",     0.12, 1.45, 0.00),
    ("Alici x2 + telemetri + GNSS logger",      0.20, 0.45, 0.00),
    ("Aku: RX 2S LiPo 3000 + ECU 3S 2200",      0.40, 0.35, 0.00),
    ("Pitot + hava veri sensoru + kablolar",    0.35, 0.60, 0.00),
    ("Govde alti kizak + dolly kilit mekanizmasi", 0.25, 0.96, -0.08),
    ("Kuyruk tamponu (egzoz konisi alti)",      0.04, 1.90, -0.06),
    ("Boya / dolgu / balans",                   0.35, 1.00, 0.00),
]
FUEL = dict(mass=4.0, x=0.955, z=-0.029, density=0.80,  # iter3 son: CAD ic hacimlerinden olculen yakit CG si (5.33 L kapasite)
            tanks=dict(fuselage_L=3.73, wing_integral_L_each=0.715, wing_eta=(0.06, 0.55),
                       wing_integral_usable_L_each=0.57,   # iter4: FE/yapi uzlasmasi (brut 0.715; duvar, kapak, %5 kullanilamaz, %2 dolum payi)
                       center_L=0.27,      # iter3: govde icinden gecen kanat kutusu orta tanki
                       belly_tank=False))  # alcak kanatta karin tanki yeri kalmadi; toplam 5.2 L ic hacim


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
