# 02: Aerodinamik ve Stabilite Analizi (İterasyon 3, iter4 kütle güncellemesiyle)

**Kaynak script:** `aero/aero_analysis.py`. Tekrar çalıştırmak için:

```bash
C:/Users/Urungu/.hz750/Scripts/python aero/aero_analysis.py
```

**Araçlar:** AeroSandbox 4.2.10.
- AeroBuildup: bileşen bazlı, NeuralFoil profil verisi + gövde.
- VLM: çapraz kontrol.
- DATCOM: gövde-kanat girişimi.
- Raymer: flap modeli (ampirik).
- 4×4 yanal durum matrisi.

**Girdi (`params.py`, güncel):**
- Kanat kökü x = 0,92 m, z = −0,080 m (alçak kanat), dihedral **+2,0°**.
- MTOW 17,16 kg (iter4: gövde kabuğu CG'si CAD alan merkezine, x = 1,15 m'ye kaydı; burunda 0,15 kg balast / ek RX aküsü eklendi).
- CG tam yakıtta x = 1,152 m, boşta x = 1,212 m. Yakıt CG'si 0,955 m (CAD iç hacimlerinden ölçüldü).
- MAC 0,312 m, x_MAC_LE = 1,082 m.

**Ham sonuçlar:** `aero/out/ozet.txt`, `aero/out/sonuclar.json`. Uçuş kontrol tasarımı (kontrol yasaları, paylar, kazanç tablosu) ayrıca `docs/09_ucus_kontrol.md`'de.

## Değişiklik özeti (iter1 → güncel)

| Konu | İter1 | İter2 | Güncel (iter3 + iter4 kütle) |
|---|---|---|---|
| Kanat kökü x / z | 1,00 / −0,035 | 0,92 / −0,035 | 0,92 / **−0,080 (alçak kanat)** |
| Dihedral | −1° | −1° | **+2,0°** |
| Flap | Düz, cf 0,22, 30° | Düz, cf 0,22, 30° | **Tek yarıklı, cf 0,25, 35°** |
| Elevator cf / yüksek hız limiti | 0,28 / ±3° | 0,28 / ±1,5° | **0,22 / ±1,5°** |
| Dikey kuyruk | 0,050 m² | 0,060 m² | 0,060 m² |
| Kalkış / iniş | Tekerlek | Dolly + kızak | Dolly + kızak (kızak 1,45 m'ye uzadı) |
| MTOW | 18,30 kg | 16,77 kg | **17,16 kg** |
| x_np | 1,318 m | 1,251 m | **1,251 m** |
| SM tam / %25 / boş | %40 / – / %29 | %31 / %21 / %16 | **%31,7 / %18,3 / %12,5** |
| Cl_β @ 750 (girişim dahil) | – | – | **−0,0375** (Γ = +2°) |
| Vs iniş (nominal) | 89 km/h | 86 km/h | **80 km/h** |

İter2 notlarındaki açık maddeler birleştirildi:
- **Flap ΔCD:** ampirik değer artık Raymer'in yarıklı flap formülüyle (0,021) hesaplanıyor; önceki 0,05–0,08 aralığının yerini aldı.
- **Boş yakıtta elevator otoritesi:** cf 0,22 ile de 12 g limiti aşılıyor (24,6 g). Çözüm g-limiter'lı uçuş kontrolcüsü; bkz. §6 ve doküman 09.
- **Dutch roll sönümü:** Yaw damper gereksinimi doğrulandı ve 4×4 modelle yeniden hesaplandı.
- **İniş hızı:** Yarıklı flapla düştü.

**SM bilinçli olarak yüksek tutuldu.** Gerekçeler:
- Dolly kalkışında rotasyon gerekmiyor.
- Yüksek SM, yüksek hızda elevator hassasiyetini azaltıyor.

![AeroSandbox üç görünüş](../aero/out/asb_uc_gorunus.png)

## 1. Profiller

Kanat kökünde NACA 64A007, ucunda 64A006 var (64A010 koordinatları kalınlıkça ölçeklendi). Kuyruklarda NACA 0006 kullanılıyor.

| Profil | Re | Cl_max | α(Cl_max) | Cd0 | Cm0 | Cl_α [/rad] |
|---|---|---|---|---|---|---|
| 64A007 | 1,5e6 | 0,75 | 15° | 0,0037 | 0 | 6,18 |
| 64A007 | 4,5e6 | 1,14 | 11,5° | 0,0035 | 0 | 6,07 |
| 64A006 | 1,5e6 | 0,77 | 15° | 0,0035 | 0 | 6,31 |
| 0006 | 1,5e6 | 0,83 | 8,2° | 0,0035 | 0 | 6,38 |

![profil polarları](../aero/out/profil_polarlari.png)

- **Mach etkisi:** 750 km/h'te M = 0,61. Prandtl-Glauert'e göre Cl_α ×1,27 artar.
- **Sıkışabilirlik:** Korn'a göre ok açılı kanadın M_dd değeri ≈ 0,87; dalga sürüklemesi yok.

## 2. Boylamsal kararlılık

| Büyüklük | Değer |
|---|---|
| CL_α (750 km/h) | 4,92 /rad (VLM, gövdesiz: 4,40) |
| Cm_α (tam yakıt CG) | −1,56 /rad |
| Cm_q | −10,2 /rad |
| CL_δe / Cm_δe (cf 0,22) | 0,62 / −1,61 /rad (iter2'de cf 0,28: 0,75 / −1,94) |
| **x_np** | **1,251 m** (%54,1 MAC; düşük hızda 1,244 m) |

### Yakıt durumuna göre statik marj

| Yakıt | m [kg] | x_cg [m] | CG [%MAC] | SM [%MAC] |
|---|---|---|---|---|
| %100 | 17,16 | 1,152 | 22,4 | **31,7** |
| %75 | 16,16 | 1,164 | 26,3 | 27,8 |
| %50 | 15,16 | 1,178 | 30,7 | 23,3 |
| %25 (iniş) | 14,16 | 1,193 | 35,8 | **18,3** |
| %0 | 13,16 | 1,212 | 41,6 | **12,5** |

İter4'te gövde kabuğu CG'si CAD'e göre 1,05 m'den 1,15 m'ye kaydı. Bu kayma boş SM'yi düşürecekti; burun balastı (0,15 kg, x = 0,20 m) eklenerek boş yakıtta SM **%12,5**'te tutuldu. Değer hedef bandın (%8–15) içinde.

![statik marj](../aero/out/statik_marj.png)

### Yüksek hız trimi

| Durum | α | δe | CL | CD | D |
|---|---|---|---|---|---|
| 750 km/h, tam yakıt | +0,09° | +0,08° | 0,0155 | 0,0142 | 154 N |
| 750 km/h, boş | +0,03° | +0,21° | 0,0119 | 0,0142 | 154 N |

## 3. Tek yarıklı flap (cf 0,25, η 0,12–0,50)

**Model girdileri:**
- Flaplı alan oranı S_flap/S = 0,45; ince profil etkinliği τ = 0,61.
- Kuyruk eğimi (Helmbold) a_t = 3,66 /rad.
- AeroBuildup'ın büyük sapmadaki flap verisi kullanılmadı.

**Ampirik bağıntılar:**
- **ΔCL_max:** 0,9 · Δcl_max · (S_flap/S) · cos Λ_menteşe.
  - Nominal: Raymer tek yarıklı, Δcl_max = 1,3 · c′/c = 1,37.
  - Muhafazakâr: 0,9 · cf/0,25 = 0,90.
- **ΔCL0 (sabit α):** cl_α · τ · η · δ, η = 0,75 → 0,55 (35°'de).
- **ΔCm0:**
  - Kanat katkısı: −0,28·Δcl (yerel veter) + flap yük merkezinin MAC c/4'ün önünde olmasından gelen kol.
  - Kuyruk katkısı: ek downwash → burun yukarı.
- **ΔCD:** Raymer 12.61, yarıklı flap için F = 0,0074.

| Büyüklük | Flap 35° (iniş) | Flap 18° (kalkış) |
|---|---|---|
| ΔCL_max nominal / muhafazakâr | +0,54 / +0,35 | ~+0,32 / +0,21 |
| ΔCL0 | +0,50 | – |
| ΔCm0 kanat / kanat + kuyruk downwash | −0,098 / +0,012 | – |
| ΔCD | +0,021 | – |

| Durum | Nominal | Muhafazakâr |
|---|---|---|
| CL_max temiz | 0,62 | 0,62 |
| CL_max iniş (trimli) | **1,11** | 0,92 |
| Vs iniş (14,2 kg) | **80 km/h** | 87 km/h |
| Temas (1,1 Vs) | **87 km/h** | 96 km/h |
| CL_max kalkış (18°, trimli) | 0,89 | 0,78 |
| Vs kalkış (17,2 kg) | 98 km/h | 104 km/h |

**Yaklaşma** (1,3 Vs = 103 km/h, %25 yakıt):

| Konfigürasyon | α | δe | CD | D |
|---|---|---|---|---|
| Flap 35° | +1,4° | −1,6° | 0,088 | 19 N |
| Flapsız | +8,4° | −4,1° | – | 14 N |

## 4. Yön ve yanal kararlılık: alçak kanat ve dihedral

### 4.1 Gövde-kanat girişimi

AeroBuildup, kanadın gövdeye göre dikey konumunun Cl_β'ya etkisini modellemiyor. Bu yüzden DATCOM 5.2.1.1 düzeltmesi eklendi:

ΔCl_β = 1,2 · √A · (z_w/b) · (2D/b) = **+0,034 /rad**. Hesap z_w = 80 mm (gövde ekseninin altı), D = 165 mm ile yapıldı. Alçak kanatta bu etki destabilize edici.

Dihedral etkinliği:
- AeroBuildup: 750 km/h'te −0,0150 /rad/°, yaklaşmada −0,0084 /rad/°.
- Şerit teorisi: −0,0158 /rad/°.

| Γ | Cl_β @ 750 km/h | Cl_β yaklaşma (103 km/h) |
|---|---|---|
| −1° | +0,008 (kararsız) | −0,017 |
| 0° | −0,008 | −0,026 |
| +1° | −0,023 | −0,034 |
| **+2° (uygulandı)** | **−0,0375** | **−0,043** |
| +3° | −0,052 | −0,051 |

750 km/h'te Cl_β = −0,035 hedefi için gereken dihedral +1,84°; params'ta **+2,0°** uygulandı. AeroBuildup'ın ham Cl_β değeri Γ = +2°'de −0,071 /rad; DATCOM düzeltmesiyle −0,0375 /rad.

Diğer yanal türevler (750 km/h, tam yakıt CG):
- Cn_β = +0,063 /rad, düşük hızda +0,115 /rad.
- CY_β = −0,33 /rad.
- Cl_p = −0,52, Cn_r = −0,148.
- Kuyruk hacimleri: V_h = 0,53, V_v = 0,076.

### 4.2 Yanal modlar (4×4: [β, p, r, φ], Ixz = 0, Roskam atalet tahminleri)

| Γ | Koşul | Dutch roll ωn / ζ | Roll τ | Spiral |
|---|---|---|---|---|
| 0° | 750 km/h | 16,5 rad/s / 0,096 | 20 ms | Kararsız, T2 = 362 s |
| 0° | Yaklaşma | 3,3 / 0,083 | 185 ms | **Kararsız, T2 = 7 s** |
| +1° | 750 km/h | 16,4 / 0,100 | 20 ms | Kararlı (yarılanma 540 s) |
| +1° | Yaklaşma | 3,4 / 0,074 | 183 ms | Kararsız, T2 = 8 s |
| +1,5° | 750 km/h | 16,3 / 0,101 | 20 ms | Kararlı (yarılanma 237 s) |
| +1,5° | Yaklaşma | 3,4 / 0,070 | 183 ms | Kararsız, T2 = 9 s |
| **+2°** | 750 km/h | **16,3 / 0,103** (2,6 Hz) | 20 ms | Kararlı (yarılanma 151 s) |
| **+2°** | Yaklaşma | **3,4 / 0,066** | 182 ms | Kararsız, T2 = 10 s |

**Seçim: Γ = +2,0°.** Gerekçeler:
- 750 km/h'te Cl_β = −0,0375; hedef bandın (−0,02…−0,04) kararlı yarısında.
- Yüksek hızda spiral kararlı.
- Yaklaşmada spiral ikilenme süresi 10 s. MIL-F-8785C ölçeğinde Level 2 sınırında; gyro ile kabul edilebilir.
- Daha fazla dihedral spirali az iyileştiriyor, ama Dutch roll sönümünü düşürüyor ve 750 km/h'te Cl_β'yı banttan çıkarıyor.

CAD ataletleriyle (Ixx 0,387, Izz 3,03, Ixz +0,041 kg·m²) hesaplanan güncel yanal modlar doküman 09'da. Ixx'in Roskam tahmininden ~%30 düşük çıkması roll modunu hızlandırıyor; Dutch roll sönümü yine ~0,1 düzeyinde.

### 4.3 Yaw damper

| Koşul | Kazanç K [° rudder / (°/s) yaw rate] | Sonuç |
|---|---|---|
| 750 km/h, Γ = +2° (ζ hedefi 0,30) | **0,0060** | ΔN_r = −6,5 1/s |
| 103 km/h, K = K_hs·(V_hs/V)² = 0,31 | 0,31 | ζ 0,066 → 0,44 |
| 103 km/h, yarım kazanç (0,16) | 0,16 | ζ ≈ 0,65 (spiral de kararlı) |

**Uygulama:**
- Kazanç planlaması (V_hs/V)^1…2 ile yapılmalı, düşük hızda 0,15–0,3 ile sınırlanmalı.
- Washout filtresi τ ≈ 1 s; rudder otoritesi ±2°.
- Bu tablo gecikmesiz, sürekli zamanlı kaba hesap. Servo + 50 Hz döngü gecikmesi dahil tasarım ve kazanç programı doküman 09'da.

## 5. Sürükleme kontrolü

| Kaynak | CD (750 km/h) | D |
|---|---|---|
| AeroBuildup (trim) | 0,0142 | 154 N |
| sizing.py | 0,0183 | 198 N |
| AeroBuildup + %12 pay | – | ~173 N |

P400-PRO 750 km/h'te ~300 N veriyor; **itki payı %50'nin üzerinde**.

## 6. Dinamik modlar ve kontrol otoritesi

| Mod (750 km/h, tam yakıt) | Değer |
|---|---|
| Kısa periyot | 45,5 rad/s (7,2 Hz), ζ = 0,30 |
| Dutch roll | 16,5 rad/s (2,6 Hz), ζ = 0,097 |
| Roll modu | τ = 20 ms |
| Spiral | Kararlı (§4.2) |

Bu bölümdeki atalet tahminleri (Roskam): Ixx ≈ 0,56, Iyy ≈ 2,73, Izz ≈ 3,65 kg·m². CAD (iter4, params yakıtı 4,0 kg): Ixx 0,387, Iyy 2,729, Izz 3,030, Ixz +0,041 kg·m². Doküman 09 CAD değerlerini kullanır.

| Kontrol (yüksek hız limitleri) | 750 km/h | 800 km/h | Değerlendirme |
|---|---|---|---|
| Aileron ±2° | **352 °/s** (pb/2V 0,021) | 375 °/s | Yeterli |
| Elevator ±1,5°, cf 0,22, tam yakıt | **7,5 g** (0,200°/g) | 8,5 g | Limitin (12 g) altında |
| Elevator ±1,5°, cf 0,22, boş | **24,6 g** (0,061°/g) | 27,9 g | **Limit aşılıyor**, aşağıya bak |
| Rudder ±2° | 8,1° sapma, 3,0 g yanal | – | Pilot girdisi ±0,5–1° olmalı; ±2° damper otoritesi |

**Neden cf düşürmek yetmedi:** Elevator veter oranını 0,28'den 0,22'ye düşürmek Cm_δe'yi yalnız %18 azalttı. Aynı dönemde boş yakıtta SM %16'dan %12,5'e indiği için ulaşılabilir g azalmadı, aksine 24 g'den 25 g'ye arttı.

**Çözüm: uçuş kontrolcüsünde g-limiter.** Normal ivme (n_z) komutlu iç döngü, komut |n| ≤ 10 g'de doyuruluyor, kazançlar hız ve yakıtla planlanıyor (doküman 09). Yedek önlemler:
- Elevator limitinin yakıt ve hızla planlanması: boş yakıt, yüksek hız ±0,6°; %40 yakıt ±1,0°.
- Ölçüm turları ≥ %40 yakıtla bitirilmeli.

### 6.1 Dolly kalkışı (tam yakıt, flap 18°, deniz seviyesi)

| Büyüklük | Değer |
|---|---|
| Vs kalkış (muhafazakâr) | 104 km/h |
| Bırakma hızı (1,2 Vs) | **125 km/h** (34,8 m/s), CL = 0,54 |
| Dolly sabit hücum açısı | **α ≈ +2,0°** (downwash kredisi olmadan +2,5°) |
| Bırakmada trim elevatörü | **δe ≈ −2,9°** (downwash kredisi olmadan −6,0°) |

Flap 18°'nin ΔCL0 katkısı yüksek olduğu için dolly açısı iter2'deki 6°'den 2°'ye düştü. Önerilen ayar (params'ta uygulandı):
- Dolly açısı **+3°**, CL payı için.
- Elevator trimi **−4°**; iki model arasında.
- Mandal L/W ≥ 1,0'da açılmalı.

### 6.2 Kızakla iniş flare (%25 yakıt, flap 35°)

**Koşullar:**
- Kütle 14,16 kg, CG x = 1,193 m, SM %18,3.
- Yer etkisi: h/b = 0,071 (McCormick); kuyruktaki downwash %44 azalıyor.
- Kötümser varsayım: kuyruk downwash kredisi kullanılmadı.

| Durum | Temas hızı | CL | α | δe trim | Yer etkisi payı | Toplam δe | Pay (limit −20°) |
|---|---|---|---|---|---|---|---|
| Nominal flap | 87 km/h | 0,91 | +5,6° | −7,0° | −2,5° | **−9,5°** | 10,5° |
| Muhafazakâr flap | 96 km/h | 0,76 | +3,5° | −6,4° | −2,1° | **−8,5°** | 11,5° |

**Flare için elevatör yeterli.** Temas açısı ≈ 4–6°. Kızağın 1,45 m'ye uzatılmasıyla hedeflenen ≥ 9° kuyruk çarpma açısı bu değerin rahatça üstünde.

## 7. Öneriler ve durum

1. **Dihedral +2,0°** params'ta uygulandı (§4.2).
2. **Elevator:** cf 0,22 kalabilir; kalkış ve flare'de bol pay var. Asıl çözüm yazılımda: g-limiter'lı n_z komut döngüsü (doküman 09). `HTAIL["elevator"]["defl_max_hs"]` 1,0'a düşürülse bile boşta 800 km/h'te ~19 g; limitör yine gerekir.
3. **Yaw damper zorunlu.** Gecikme dahil kazanç programı doküman 09'da. Damper arızasında ölçüm turu yapılmamalı.
4. **Dolly:** α = +3°, δe trim −4°, bırakma ≥ 125 km/h.
5. **Yakıt CG'si** CAD'den alındı (0,955 m). Kütle kalemleri değişirse script yeniden çalıştırılmalı.

## Varsayımlar ve sınırlar
- AeroBuildup sonuçları yarı-ampirik. Gövde-kanat girişimi için DATCOM ΔCl_β ayrıca eklendi; diğer girişimler (Cn_β'ya gövde katkısı dışında) yok.
- Flap modeli tamamen ampirik. Nominal ve muhafazakâr ikilisi belirsizlik aralığını gösteriyor.
- Bu dokümandaki yanal modlar 4×4 modelle hesaplandı; Ixz = 0, atalet momentleri Roskam tahmini. CAD ataletli hesap doküman 09'da. Düşük hızda yaw damperli mod ayrışması kazanca duyarlı.
- Yer etkisi McCormick bağıntısıyla hesaplandı; kızak-kanat yüksekliği yaklaşık 0,09 m varsayıldı.
- Boylamsal dinamikte Cm_α̇ = 0,3·Cm_q varsayıldı.
