"""Üç ağlı Richardson/GCI; monoton olmayan veya sıfır farkta sonuç uydurmaz."""
import math


def gci(h, q, formal_order=None):
    """h ve q fine, medium, coarse sıralı; eşit olmayan oranlar desteklenir.

    GCI güvenlik katsayısı 1.25 (Roache, üç ağ, gözlenen p). formal_order verilirse
    ve gözlenen mertebe ondan %10'dan fazla saparsa (asimptotik bölge kanıtlanmamış)
    Roy/Oberkampf-Roy (2010) ve Roache önerisiyle muhafazakâr tahmin kullanılır:
    p_kullanılan = min(max(0.5, p_gözlenen), p_formal), Fs = 3.
    Bağıl GCI sıfıra yakın büyüklükte tanımsızdır. GCI fiziksel model/deney hatası değildir.
    """
    if len(h) != 3 or len(q) != 3 or not all(math.isfinite(v) for v in (*h, *q)):
        raise ValueError("Üç sonlu h ve q gerekli")
    if not 0 < h[0] < h[1] < h[2]:
        raise ValueError("h: fine < medium < coarse olmalı")
    r21, r32 = h[1] / h[0], h[2] / h[1]
    if min(r21, r32) < 1.3:
        return dict(status="INSUFFICIENT_REFINEMENT", reason="h oranı < 1.3")
    d21, d32 = q[1] - q[0], q[2] - q[1]
    scale = max(max(abs(x) for x in q), 1e-30)
    if max(abs(d21), abs(d32)) < 1e-10 * scale:
        return dict(status="EXACT_OR_ROUNDOFF", reason="Farklar sıfır/yuvarlama düzeyinde; p ve GCI tanımsız")
    if min(abs(d21), abs(d32)) < 1e-10 * scale:
        return dict(status="PLATEAU_UNRESOLVED", reason="Yalnız bir ağ farkı yuvarlama düzeyinde; yakınsama çözümlenemedi")
    if d21 * d32 <= 0:
        return dict(status="OSCILLATORY", reason="Monoton yakınsama yok")
    ratio = d32 / d21

    def residual(p):
        return r21 ** p * math.expm1(p * math.log(r32)) / math.expm1(p * math.log(r21)) - ratio

    low, high = 0.05, 10.0
    if residual(low) * residual(high) >= 0:
        return dict(status="NO_OBSERVED_ORDER", reason="0.05 < p < 10 içinde pozitif mertebe bulunamadı")
    for _ in range(80):
        mid = (low + high) / 2
        if residual(low) * residual(mid) <= 0:
            high = mid
        else:
            low = mid
    p = (low + high) / 2
    correction = (q[0] - q[1]) / (r21 ** p - 1)
    order_used, safety = p, 1.25
    if formal_order is not None and abs(p - formal_order) > .1 * formal_order:
        order_used, safety = min(max(.5, p), formal_order), 3.0
    absolute = safety * abs((q[0] - q[1]) / (r21 ** order_used - 1))
    return dict(status="ESTIMATED", observed_order=p, richardson=q[0] + correction,
                formal_order=formal_order, order_used=order_used, safety_factor=safety,
                fine_gci_absolute=absolute,
                fine_gci_pct=100 * absolute / abs(q[0]) if abs(q[0]) > 1e-12 * scale else None,
                r21=r21, r32=r32,
                warning="Üç nokta asimptotik bölgeyi tek başına kanıtlamaz; şok/mod takibi ayrıca incelenmeli.")


def error(value, reference):
    return dict(absolute=value - reference,
                percent=100 * (value - reference) / abs(reference) if reference != 0 else None)
