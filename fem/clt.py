"""Klasik laminat teorisi (CLT): ABD, eşdeğer mühendislik sabitleri ve tabaka gerilmesi.

Bağımsız referans; CalculiX kupon benchmarkı (fem/coupon.py) bu fonksiyonlarla karşılaştırılır.
Birimler SI. Tabaka listesi alt yüzden (−normal) üst yüze (+normal) sıralıdır; CalculiX
*SHELL SECTION, COMPOSITE kart sırası ile aynı varsayım kupon testinde doğrulanır.
"""
import math

import numpy as np


def q_matrix(m):
    """Tabaka eksenlerinde düzlem gerilme indirgenmiş rijitlik Q [Pa]."""
    e1, e2, nu12, g12 = m["E1"], m["E2"], m["nu12"], m["G12"]
    nu21 = nu12 * e2 / e1
    d = 1 - nu12 * nu21
    if d <= 0 or min(e1, e2, g12) <= 0:
        raise ValueError("Pozitif tanımlı lamina gerekli")
    return np.array([[e1 / d, nu12 * e2 / d, 0.], [nu12 * e2 / d, e2 / d, 0.], [0., 0., g12]])


def transformation(theta_deg):
    """Gerilme dönüşümü T: sigma_12 = T sigma_xy (mühendislik kaymasıyla değil tensör kaymasıyla)."""
    c, s = math.cos(math.radians(theta_deg)), math.sin(math.radians(theta_deg))
    return np.array([[c * c, s * s, 2 * c * s], [s * s, c * c, -2 * c * s], [-c * s, c * s, c * c - s * s]])


def q_bar(m, theta_deg):
    """Laminat eksenlerinde dönmüş rijitlik; theta x'ten 1-eksenine pozitif (sağ el, +z normal)."""
    t = transformation(theta_deg)
    r = np.diag([1., 1., 2.])
    return np.linalg.inv(t) @ q_matrix(m) @ r @ t @ np.linalg.inv(r)


def transverse_shear(m, theta_deg):
    """Laminat eksenlerinde enine kayma rijitliği [[Q44, Q45], [Q45, Q55]] (yz, xz)."""
    c, s = math.cos(math.radians(theta_deg)), math.sin(math.radians(theta_deg))
    g13, g23 = m.get("G13", m["G12"]), m.get("G23", m["G12"])
    q44 = g23 * c * c + g13 * s * s
    q55 = g13 * c * c + g23 * s * s
    q45 = (g13 - g23) * c * s
    return np.array([[q44, q45], [q45, q55]])


def abd(layers, z_ref=None):
    """layers: [(malzeme dict, kalınlık, açı_deg), ...] alt -> üst.

    z_ref: referans yüzeyin alt yüzden yüksekliği; None = orta düzlem. ABD bu yüzeye göredir.
    Dönüş: A, B, D (3x3) ve toplam kalınlık h.
    """
    h = sum(t for _, t, _ in layers)
    z0 = h / 2 if z_ref is None else z_ref
    a, b, d = np.zeros((3, 3)), np.zeros((3, 3)), np.zeros((3, 3))
    z = -z0
    for m, t, theta in layers:
        q = q_bar(m, theta)
        z1 = z + t
        a += q * (z1 - z)
        b += q * (z1 ** 2 - z ** 2) / 2
        d += q * (z1 ** 3 - z ** 3) / 3
        z = z1
    return a, b, d, h


def abd_matrix(layers, z_ref=None):
    a, b, d, _ = abd(layers, z_ref)
    return np.block([[a, b], [b, d]])


def engineering_constants(layers):
    """Membran eşdeğer sabitleri (serbest eğrilik, N yükü): Ex, Ey, Gxy, nuxy ve D11, d11."""
    a, b, d, h = abd(layers)
    compliance = np.linalg.inv(np.block([[a, b], [b, d]]))
    return dict(Ex=1 / (h * compliance[0, 0]), Ey=1 / (h * compliance[1, 1]), Gxy=1 / (h * compliance[2, 2]),
                nuxy=-compliance[0, 1] / compliance[0, 0], D11=d[0, 0], d11=compliance[3, 3],
                D11_beam=1 / compliance[3, 3], h=h)


def shear_stiffness(layers, sandwich_core=None):
    """Kiriş enine kayma rijitliği (birim genişlik) [N/m], xz yönü.

    sandwich_core None: eşdeğer tek katman, k=5/6 ile sum(Q55 t).
    sandwich_core=(çekirdek indeksi): klasik sandviç S = G_c d^2 / c (ASTM D7250).
    """
    if sandwich_core is None:
        return 5 / 6 * sum(transverse_shear(m, th)[1, 1] * t for m, t, th in layers)
    zs = np.cumsum([0.] + [t for _, t, _ in layers])
    i = sandwich_core
    m, c, th = layers[i]
    upper = zs[-1] - zs[i + 1]
    lower = zs[i]
    d = c + (upper + lower) / 2
    return transverse_shear(m, th)[1, 1] * d * d / c


def three_point_deflection(layers, load, span, width, sandwich_core=None):
    """Basit mesnetli dar şerit, orta noktaya P: P L^3/(48 b/d11) + P L/(4 b S)."""
    props = engineering_constants(layers)
    bend = load * span ** 3 / (48 * width * props["D11_beam"])
    shear = load * span / (4 * width * shear_stiffness(layers, sandwich_core))
    return bend + shear, bend, shear


def ply_stresses(layers, n_load, m_load=(0., 0., 0.), z_ref=None):
    """Her tabakanın ortasında tabaka eksenlerinde (s11, s22, s12) [Pa]; N [N/m], M [N]."""
    a, b, d, h = abd(layers, z_ref)
    strain = np.linalg.solve(np.block([[a, b], [b, d]]), np.r_[n_load, m_load])
    e0, k = strain[:3], strain[3:]
    z = -(h / 2 if z_ref is None else z_ref)
    out = []
    for m, t, theta in layers:
        zm = z + t / 2
        eps = e0 + zm * k
        sigma = q_bar(m, theta) @ eps
        out.append(transformation(theta) @ sigma)
        z += t
    return out, strain
