# 04 – Yapı, Flutter ve Kontrol Yüzeyleri (İterasyon 3)

> **İter3 kapanış güncellemesi (ana entegrasyon):** Bu analizden sonra params'a işlenen değişiklikler: kanat kökü z **−0,080 m**, dihedral +2,0°, kanat bağlantısı kalemi (0,15 kg), ısı keçesi kalemi, yakıt CG'si 0,955 m, MTOW **17,01 kg**. Script bu değerlerle yeniden çalıştırıldı. **Güncel sonuçlar:** kat planı 3/1 (kiriş önü/arkası, yüz başına), kanat **1,74 kg**, **flutter 1465 km/h** (gereksinim 1080 km/h, **pay %36**), diverjans 3290 km/h. Elevator balans kütlesi 18 g. Metinde bunlardan farklı ara değerler varsa güncel olan `structures/out/sonuclar.json`'dur.


**Kaynaklar:**
- Script: [`structures/structures.py`](../structures/structures.py). Girdi `params.py`; çıktılar `structures/out/`; tüm sayılar `structures/out/sonuclar.json`.
- Arşiv: `structures/structures_iter1.py`, `structures/structures_iter2.py`, `structures/out_iter1/`, `structures/out_iter2/`, `structures/04_yapi_flutter_iter{1,2}.md`.

**Tasarım durumu:** MTOW **16,81 kg**, W/S = 393 Pa, alçak kanat (z_root = −65 mm), tek parça kanat, kızakla iniş.

## 0. Değişiklik özeti

| Konu | İter 1 | İter 2 | **İter 3** |
|---|---|---|---|
| MTOW | 18,30 kg | 16,77 kg | 16,81 kg |
| Kanat konumu | orta-alçak, z = −35 mm | aynı | **alçak, z = −65 mm** |
| Gövde yanı / açıkta kalan kanat kökü y₀ | 82,5 mm | 82,5 mm | **50,8 mm** (alçak kanatta gövde dar) |
| Kanat bağlantısı | 2 bıçak + pim | aynı | **Tek parça kanat, gövde içinden geçen kutu, kiriş çerçevelerine 4 × M6** |
| Burulma hücresi | tüm profil | hücum kenarı → arka kiriş (0,55c) | aynı |
| Kesit ağırlık merkezi x_cg | 0,43c varsayım | 0,42c varsayım | **hesaplanıyor: 0,45c** (3/1 kat; 2/2 katta 0,52c) |
| Kabuk kat planı (yüz başına; kiriş önü / kiriş arkası) | 2/2 | 2/2 | **3/1** |
| Kanat kütlesi | 1,49 kg | 1,47 kg | **1,65 kg** (bütçe 1,75) |
| Flutter | 1495 km/h | 1383 km/h | **1500 km/h** (kritik: tank dolu, η 0,70) |
| Diverjans | 1973 km/h | 2840 km/h | 3364 km/h |
| Kanat tankı (yarı) | – | 0,39 L (η ≤ 0,40) | **0,57 L** (η 0,06–0,55, y₀ küçüldü) + isteğe bağlı merkez tank 0,27 L |
| Flap | düz, c_f 0,22 / 30° | aynı | **tek yarıklı, c_f 0,25 / 35°**, dış menteşe |
| Elevator | c_f 0,28, ±3° | aynı | **c_f 0,22, ±1,5°**: servo 9 kg·cm, balans 18 g |
| Kızak | x 0,62–1,30 | aynı | **x 0,62–1,45**, 5 çerçeve, σ 466 → 385 MPa |
| Kuyruk çarpma açısı | – | 2,6° | **3,2°**: hedef 9° sağlanamıyor, **kuyruk tamponu şart** |

> **İter 2 düzeltmesi (önemli):** İter 2'de kesit ağırlık merkezi 0,42c varsayılmıştı. İter 3'te kesit kütle bileşenlerinden hesaplandı: kabuk çevresi, kapaklar, web'ler, kaburgalar ve hinge hattındaki aileron balans kütlesi. 2/2 kat planında sonuç **0,52c**. Bu durumda iter 2 tasarımının flutter hızı 1383 değil **~1090 km/h** çıkıyor (gereksinim 1080; payı neredeyse yok).
>
> Çözüm, kütleyi elastik eksenin önüne kaydırmak: **kiriş önü kabuk 3 kat/yüz, kiriş arkası (firar kenarı bölgesi) 1 kat/yüz**. Sonuç: x_cg = 0,45c, flutter 1500 km/h, kanat 0,04 kg daha hafif (2/2'nin 1,61 kg'ına karşı 1,65 kg; 3/3'ün 2,02 kg'ından çok daha hafif).

## 1. Tasarım kriterleri

| Kriter | Değer |
|---|---|
| Limit yük faktörü | +12 / −8 g |
| Nihai emniyet katsayısı | 1,5 (nihai +18 / −12 g) |
| V_C (ECU limiti) / V_D | 800 / 900 km/h |
| V_FE (flap açık azami hız) | 150 km/h |
| Flutter / diverjans | ≥ 1,2·V_D = 1080 km/h; kat seçiminde ek ×1,25 model payı (≥ 1350 km/h) |

## 2. Malzeme ve izin değerleri

| Malzeme | Kullanım | Özellikler |
|---|---|---|
| T700S/epoksi UD 200 g/m² | Kapaklar, longeronlar | E₁ 125 GPa, Xt/Xc 2100/1200 MPa, kat kalınlığı 0,20 mm |
| T300 dokuma 160 g/m², ±45 | Kabuk, web | E 55 GPa, G₄₅ 25 GPa, kat kalınlığı 0,178 mm |
| 200 g/m² dokuma (quasi-izotrop) | Gövde, çerçeveler | E 45 GPa, kat kalınlığı 0,22 mm |
| Rohacell 51 IG-F | Çekirdek | 2 mm (tank kaburgası 3 mm) |
| Cam 48 g/m² + yakıta dayanıklı epoksi | Tank iç kaplaması | ≈ 0,15 kg/m² |

**İzin değerleri:**
- Düşürme faktörü 0,544.
- UD kapak 500 MPa (4000 µε birim şekil değiştirme limiti).
- Gövde 180 MPa.
- Boru 400 MPa.

**Sıcaklık sınırı (iter 3, motor bölgesi):**
- Oda sıcaklığında kürlenmiş epoksinin Tg değeri yaklaşık 60–80 °C; 80 °C'de sonradan kürlenmiş olanınki ~100–120 °C.
- **Kullanım sıcaklığı ≤ Tg − 30 °C** olmalı.
- x = 1,18–1,57 m arası (motor) ve arka gövde için **Tg ≥ 150 °C** reçine gerekli. Seçenekler:
  - 120–180 °C'de kürlenen havacılık prepregi;
  - yüksek Tg'li epoksi sistemi (ör. 150 °C'de son kürlü);
  - egzoz borusu yakını için BMI veya siyanat ester.

## 3. V-n diyagramı

![V-n](../structures/out/vn_diyagrami.png)

| Büyüklük | Değer |
|---|---|
| V_S / V_A | 91 / 316 km/h |
| CLα / K_g | 4,62 /rad / 0,79 |
| CS-23 hamlesi @ V_C | n = 20,4: 12 g'yi aşar → **operasyonel sınır: sadece sakin havada yüksek hız** |
| Operasyonel hamle @ V_C | 7,62 m/s → +10,7 / −8,7 g. −8,7 g, −8 g limitinin %9 üstünde; nihai −13 g simetrik kiriş kapasitesi içinde. Uçuş kartına not edilmeli. |

## 4. Kanat yükleri (nihai, n = 18)

![Kanat yükleri](../structures/out/kanat_yukleri.png)

| Durum | M(y = 0) [N·m] | M(y₀ = 51 mm) [N·m] | V(y = 0) [N] | T_kök [N·m] |
|---|---|---|---|---|
| A: rahatlatma yok (referans) | 454 | 382 | 1484 | 24,2 |
| **B: MTOW, kanat tankı dolu (2 × 0,47 kg)** | **437** | **369** | **1400** | 25,6 |
| C: kanat tankı boş | 428 | 360 | 1400 | 25,0 |

- Yakıt rahatlatması %4; B durumu belirleyici.
- Alçak kanatta gövde dar olduğundan açıkta kalan kök iç tarafa kaydı (y₀ 82 → 51 mm). Bu yüzden gövde yanındaki moment 333 → 369 N·m oldu.

## 5. Kanat yapısı

### 5.1 Kat planı: kiriş önü 3, kiriş arkası 1 kat/yüz

![Kat planı](../structures/out/kiris_kat_plani.png)

| y [m] | Veter [m] | Kutu yüksekliği [mm] | M_ult [N·m] | Kapak genişliği [mm] | UD kat | Web katı | GJ [N·m²] |
|---|---|---|---|---|---|---|---|
| 0,000 (merkez kutu) | 0,429 | 20,9 | 437 | 50 | 3 | 3 | 7324 |
| 0,051 (gövde yanı) | 0,410 | 19,4 | 369 | 48 | 3 | 3 | 6244 |
| 0,153 | 0,370 | 16,5 | 253 | 43 | 2 | 3 | 4441 |
| 0,251 | 0,333 | 13,7 | 164 | 39 | 2 | 3 | 3093 |
| 0,353 | 0,293 | 11,0 | 94 | 34 | 2 | 3 | 2038 |
| 0,451 | 0,255 | 8,5 | 46 | 30 | 2 | 3 | 1294 |
| 0,553 | 0,216 | 6,0 | 16 | 25 | 2 | 2 | 718 |
| 0,652 | 0,178 | 3,6 | 2 | 21 | 2 | 2 | 387 |

- **Kabuk, kiriş önü (hücum kenarı → 0,55c):** her yüzde 3 kat ±45 karbon (dış ve iç yüz) + 2 mm Rohacell. Burulma hücresi budur.
- **Kabuk, kiriş arkası (0,55c → firar kenarı, flap/aileron dahil):** her yüzde 1 kat ±45 + 2 mm Rohacell. Bu bölge burulma taşımaz.
- Kiriş kapakları kademeli kesilir (ply drop), her kat 15–20 mm kaydırılır.
- **Kanat kütlesi:** 1,65 kg; merkez kutu, tank kaburgaları ve sızdırmazlık dahil.

### 5.2 Entegre yakıt tankı

| Tankın dış sınırı η₁ | 0,40 | **0,55 (params)** | 0,60 | 0,70 |
|---|---|---|---|---|
| İç hacim / yarı kanat [L] | 0,47 | **0,57–0,59** | 0,62 | 0,67 |

- Yarı kanat başına **0,57 L (0,45 kg)**. params'taki 0,9 L hâlâ fiziksel olarak mümkün değil.
- **Yeni seçenek, merkez tank:** Gövde içinden geçen kutu (y = ±51 mm) da tank olabilir: **+0,27 L (0,22 kg)**.
  - Avantaj: tek parça kanatta sol, merkez ve sağ tek bir tank olur; bir tarafın boşalmasından doğan dengesizlik ortadan kalkar.
  - Gereksinim: merkez kutuda kanat bağlantı cıvataları için sızdırmaz burçlar (Al burç + O-ring), çıkış nipeli merkezde.
  - Toplam kanat yakıtı 2 × 0,57 + 0,27 = **1,41 L (1,13 kg)**. Gövde tankı 2,87 kg olur.
- **Yapı kontrolleri:**
  - Tasarım basıncı limit 10 kPa, nihai 15 kPa.
  - Kabuk paneli: yüz 25,6 MPa, çekirdek 0,36 MPa. Uygun.
  - Sızdırmazlık ve test (iter 2'den aynen): cam + yakıta dayanıklı epoksi kaplama, fileto köşeler, 15 kPa'da 30 dk test (**20 kPa'yı aşmayın**).

## 6. Flutter ve diverjans

**Yöntem:**
- Theodorsen 2 serbestlik dereceli tipik kesit, k-yöntemi; Prandtl–Glauert düzeltmesi.
- Doğrulama: U_F = 2,184 (referans ≈ 2,17).
- Frekanslar Rayleigh yöntemiyle; kanat y₀ = 51 mm'de ankastre.
- **İter 3 değişiklikleri:**
  - kesit ağırlık merkezi ve ataleti, bileşenlerden her istasyonda ayrı hesaplanıyor;
  - y₀ = 51 mm, yani daha uzun açıkta kalan yarı açıklık (muhafazakâr).

| Kat (ön/arka) | Kanat [kg] | x_cg (η 0,7) | f_h [Hz] | f_α [Hz] | V_F (tank dolu, η 0,70) | V_div [km/h] |
|---|---|---|---|---|---|---|
| 1/1 | 1,21 | 0,53c | 42 | 198 | 917 ✗ | 2009 |
| 2/1 | 1,43 | 0,48c | 37 | 263 | 1177 (pay %9) | 2793 |
| 2/2 (iter 2) | 1,61 | 0,52c | 34 | 229 | 1086 ✗ (pay %1) | 2793 |
| **3/1 (seçilen)** | **1,65** | **0,45c** | **34** | **301** | **1500** | **3364** |
| 3/3 | 2,02 | 0,52c | 30 | 241 | 1262 | 3364 |
| 4/4 | 2,42 | 0,52c | 28 | 246 | 1427 | 3822 |

**Seçilen 3/1 kat planında dört durum:**

| Durum | V_F [km/h] | x_α |
|---|---|---|
| Tank dolu, η 0,70 | 1500 | 0,30 |
| Tank boş, η 0,70 | 1554 | 0,30 |
| Tank dolu, η 0,25 | 2346 | 0,19 |
| Tank boş, η 0,25 | 2137 | 0,23 |

Bu durumlarda μ = 16, a = −0,40 (elastik eksen 0,30c), r_α² = 0,43, f_h/f_α = 0,11.

![V-g](../structures/out/flutter_Vg.png)
![GJ duyarlılık](../structures/out/flutter_GJ_duyarlilik.png)

**Sonuçlar:**
- Flutter hızı **1500 km/h**; gereksinim 1080 km/h, pay %39. Diverjans 3364 km/h.
- Bulgu: flutter'ı belirleyen etken kütle dağılımı (x_α), burulma rijitliği daha az belirleyici. Kat eklemek her zaman işe yaramıyor: 3/3 ve 4/4, 3/1'den kötü.
- **İmalat gereksinimi:**
  - Firar kenarı bölgesine gereksiz kütle eklenmemeli (dolgu, boya birikmesi, kablo).
  - Aileron balans kütleleri **zorunlu**. Hinge hattındaki 23 g bu hesaba dahil.
  - Servolar mümkün olduğunca kiriş önüne (0,2–0,35c) yerleştirilmeli.

## 7. Alçak kanat bağlantısı (iter 3)

**Geometri:**
- Kanat orta düzlemi z = −65 mm.
- Kök kutu bölgesinde üst yüzey z = −51 mm, alt yüzey z = −79 mm (gövde alt kabuğu −82,5 mm).
- Gövde yan yüzü y = ±51 mm (orta düzlemde); üst yüzey hizasında ±64 mm.

### 7.1 Seçenek karşılaştırması

| | **A: tek parça kanat, gövde içinden geçen kutu (önerilen)** | B: iki yarı + karbon bıçak + yan çerçeve |
|---|---|---|
| Yük yolu | Kiriş kapakları süreklidir; kök momenti (437 N·m) kanat içinde kalır. Gövdeye yalnız kesme ve yunuslama kuvvetleri aktarılır. | 369 N·m bıçaklarla yan çerçevelere aktarılır. Alçak kanatta gövde yan duvarı sığ ve eğik (y = 51–64 mm), çerçeve tabanı dar. |
| Kütle (bağlantı + merkez) | ~0,22 kg | ~0,28 kg |
| Taşıma | 1,45 m tek parça: araca sığar | Sökülebilir |
| Ek fayda | Merkez tank +0,27 L; dengesizlik yok | – |
| Risk | Gövde altında 236 mm kesik: longeron gerekir | Bıçak kutusu kök kaburgası ve tank duvarıyla çakışır |

**Karar: A.** Kanat kutusu gövdenin içinden yalnız **hücum kenarı → arka kiriş** (x = 0,92–1,156 m) arasında geçer.

Kanadın arka kiriş gerisi (0,55c → firar kenarı) gövde yanında (y = ±51 mm) kök kaburgasıyla biter. Sebebi: x > 1,18 m'de motor alt kenarı (z ≈ −74 mm) ile kanat firar kenarı bölgesi çakışırdı. **CAD notu:** gövde alt kabuğu x > 1,156 m'de süreklidir.

### 7.2 Bağlantı yükleri (nihai)

Gövdenin kanattan taşıdığı kütle 14,11 kg (kanat ve kanat yakıtı hariç), ağırlık merkezi x = 1,155 m. Kuyruk yükü ±976 N nihai (V_D).

| Bağlantı düzeni | Durum | Ön bağlantı [N] | Arka bağlantı [N] |
|---|---|---|---|
| **A1:** kiriş çerçeveleri, x = 1,006 / 1,156 (aralık 150 mm) | kuyruk aşağı | −5247 (çekme) | 8714 |
| | kuyruk yukarı | 5276 | −3762 |
| A2: hücum kenarı pimi 0,96 + firar kenarı cıvatası 1,32 (aralık 360 mm) | kuyruk aşağı | −612 | 4079 |
| | kuyruk yukarı | 2892 | −1377 |

**A2 yükleri yarıya indirir**, ancak x = 1,32 m'deki çerçeve motorun etrafından geçmek zorunda. Orada motor ile kabuk arasında yalnız 8,5 mm radyal derinlik var; çerçeve gerekli rijitliği taşıyamaz. **Bu nedenle A1 önerilir.** Motor ≥ 0,15 m arkaya alınırsa A2 yeniden değerlendirilir.

**A1 boyutlandırması:**

| Eleman | Gereksinim / seçim |
|---|---|
| Cıvatalar | **4 × M6 12.9** (her çerçevede 2, y = ±35 mm). En kötü çekme 5,6 kN (yunuslama + −12 g + dikey kuyruk yuvarlanma momenti 178 N·m); M6 kapasitesi 17,2 kN. Alttan takılır, gövde içinde Al barrel-nut. |
| Kanat hard point'leri | Cıvata başına yatak kalınlığı ≥ 4,3 mm. Kutu içinde kapaklar arası G10/Al blok (20 × 30 mm) + kiriş web'inde lokal ±45 takviye (≥ 4 mm, kesme 5,2 kN). |
| Kiriş çerçeveleri (x = 1,006 ve 1,156) | Halka momenti 0,08·F·R = 57 N·m. **25 mm radyal derinlik, 3,1 mm karbon** (veya 6 mm sandviç). Üstteki S-kanal geçişi için çerçeve üst yarısında kanal kesiği + çevresel takviye. |
| Hücum kenarı yataklama | x ≈ 0,94 m'de 2 × Ø5 çelik pim, gövde tankı arka duvar çerçevesine. Konumlama ve sürtünme yükü için. |
| Gövde alt kesiği (x 0,92–1,156) | Kesikte M = 1203 N·m. Longeronsuz 4715 µε (✗). **2 × 30 mm² UD longeron** (3 × 10 mm şerit, kesik kenarlarında, z = −51 mm, kesiğin ±60 mm ötesine uzanan) → ≈ 2100 µε. |
| Karın kaplaması | Kanatla birlikte sökülen ince kabuk (1 kat 160 g/m² + 1 mm köpük). Yük taşımaz. Kızağın kanat altı bölümü bu kaplama yerine kanat merkez kutusuna cıvatalanır. |

## 8. Tek yarıklı flap (iter 3)

**Geometri ve yükler:**
- c_f = 0,25c = 86 mm, S_f = 236 cm²/flap, 35° açık, V_FE = 150 km/h.
- Normal kuvvet katsayısı C_n = 1,6 (flap alanına göre; tek yarıklı flap 35°, hamle payı dahil).
- N = 40 N limit, 60 N nihai (flap başına).

**Yatak düzeni:**
- Dış menteşe (drop-hinge), flap başına 2 braket.
- Pivot noktası flap hücum kenarının 0,10 c_f önünde, profil alt yüzeyinin 0,06c altında; bu da 35°'de yarık oluşturur.

| Büyüklük | Değer |
|---|---|
| Braket yükü (nihai, ±%25 eşitsizlik) | 38 N/braket. Pim Ø3 çelik, çift kesme kapasitesi 6,8 kN. Braket 7075-T6 Al 2 mm veya 3 mm karbon; kirişe değil **arka kirişe cıvatalı kaburga ayağına** bağlanır. |
| Menteşe momenti (açık, V_FE) | 1,55 N·m → servo **24 kg·cm** |
| Kapalı tutma momenti, 800 km/h / 900 km/h | 1,08 / 0,62 N·m → 16,9 / 9,7 kg·cm |
| Önerilen mekanizma | **Ölü nokta (over-center) kol**: flap kapalıyken servo yük görmez. Flap mekanik dayanağa ön yüklü durur (yüksek hızda boşluk = 0). |
| Servo | Ortak 45 kg·cm tip yeterli (gereken 25 kg·cm sınıfı) |
| Kontrol yüzeyi flutter'ı | Flaplar yüksek hızda dayanakta ön yüklü olduğu için balans gerekmez (tablodaki 39 g uygulanmaz). Ön yük ≥ 2 × 1,08 N·m. |
| Braket kaporta (fairing) | Dış menteşeler sürüklemenin kaynağı. Bkz. aero dokümanı. |

## 9. Kontrol yüzeyleri: menteşe momentleri, servolar, balans

| Yüzey | c_f [mm] | S_f [cm²] | M_h @800 km/h [N·m] | M_h @V_D [N·m] | M_h @V_A [N·m] | Gereken servo [kg·cm] | Servo | Balans kütlesi |
|---|---|---|---|---|---|---|---|---|
| Aileron | 41 | 124 | 1,12 | 1,39 | 0,66 | 21,9 | 45 (ortak) | 23 g |
| **Elevator (c_f 0,22, ±1,5°)** | **34** | **89** | **0,40** | **0,57** | **0,43** | **8,9** | 45 (ortak) | **18 g** |
| Rudder | 62 | 179 | 2,40 | 3,39 | 1,68 | 53,2 | **60** | 31 g |
| Flap (yarıklı) | 86 | 236 | 1,08 (tutma) | 0,62 | 1,55 (V_FE) | 24,3 | 45 (ortak) | – |

**Elevator flutter (iter 3):**
- %100 statik balans → 18 g tungsten, hücum kenarına 7 mm kolla. Yüzey kütlesi 9 g.
- Yatay kuyruk yarısının eğilme frekansı tahmini **~154 Hz** (boru soketinde ankastre kiriş).
- Gereken elevator dönme frekansı ≥ 1,5 × min(f_kuyruk, 3·f_kanat) ≈ **150 Hz** → bağlantı rijitliği ≥ 2,4 N·m/rad.
  - 3 mm karbon itme çubuğu, 10 mm kol: ~1700 N·m/rad. **Yeter, yeter ki boşluk ≤ 0,1° olsun.**
- c_f'nin 0,28 → 0,22'ye inmesi balans kütlesini ve menteşe momentini azalttı; flutter açısından olumlu.
- Elevator **ses altı titreşim (buzz)**: M < 0,8'de risk düşük. Ancak menteşe boşluğu sızdırmaz (sealed gap) olmalı ve firar kenarı keskin.

## 10. Gövde altı kızak (iter 3: x 0,62–1,45 m)

**Enerji ve yük:**
- İniş kütlesi 13,21 kg, batma hızı 1,5 m/s → E = 14,9 J.
- Tasarım durumu kısa çim (25 mm strok): **9,2 g limit**, F_ult = 1783 N.
- Sert pistte 22,9 g → **yalnız çim pist**.
- Kayma mesafesi ≈ 71 m.

| Kontrol | İter 2 | **İter 3** |
|---|---|---|
| Çerçeveler | 0,62 / 0,96 / 1,30 | **0,62 / 0,81 / 1,006 / 1,156 / 1,38** (kiriş çerçeveleri + motor yatağı çerçevesi) |
| En büyük açıklık / arka konsol | 0,34 m / – | 0,224 m / 0,07 m |
| Kızak kirişi σ (40 × 10 mm, 1 mm UD kapaklar) | 466 MPa | **385 MPa** (izin 500) |
| Çerçeve halka gerilmesi | 104 MPa | 105 MPa (izin 180) |
| Kızak kütlesi | 205 g | 246 g (params 0,25 kg ile uyumlu) |
| Kuyruk çarpma açısı | 2,6° | **3,2°** |

**Kuyruk çarpması:** Hedeflenen 9° bu gövdeyle **sağlanamıyor**. Kızak arka ucu (x = 1,45) ile egzoz konisi alt kenarı arasındaki düşey fark yalnız 36 mm, yatay mesafe 0,65 m. 9° için ~100 mm düşey fark gerekir.

Bu nedenle **x ≈ 1,90 m'de kuyruk tamponu zorunlu**:
- 15 mm yükseklik, değiştirilebilir Kevlar/UHMW blok;
- limit yükü ~475 N;
- yatay kuyruk boru çerçevesini paylaşır.

Teker koyma için ~5–8° gerekiyor; uçak önce tampona, sonra kızağa oturur.

**Motor altı ısı (x 1,18–1,45):**
- Motor alt kenarı ile gövde kabuğu arasında ~8,5 mm boşluk var.
- Motor gövdesinin yanma odası bölgesinde dış yüzey sıcaklığı ~150–250 °C olabilir. **Doğrulanmadı;** ilk motor çalıştırmada termokupl ile ölçülmeli.

**Gereksinimler:**
1. Gövde iç yüzüne x 1,15–1,60 bölgesinde alüminize cam keçe (1,5–2 mm) + alüminyum folyo.
2. Kızak ve gövde alt kabuğu bu bölgede **Tg ≥ 150 °C** reçine. Kızak aramid sarımı 150 °C'ye dayanır; reçine sınırlar.
3. Aşınma plakası UHMW-PE (sınır ~80 °C) bu bölgede **kullanılmamalı** → x > 1,15'te **G10/FR4** (≤ 130 °C) ya da 0,5 mm paslanmaz çelik plaka.
4. Bypass soğutma havası motor altından akmalı (egzoz borusu bypass'ı).
5. Kontrol için sıcaklık gösterge etiketleri (60/80/100/120 °C), ilk uçuşlarda motor altı kabuğa yapıştırılır.

## 11. Gövde, motor yatağı, yatay kuyruk kökü

| Kontrol | Sonuç |
|---|---|
| Arka gövde eğilmesi | 1203 N·m @ x 1,16. Kabuk en fazla 3 kat 200 g/m² (x 1,15–1,6), kesik bölgesinde longeron (§7). |
| Motor yatağı | 4 × M4 12.9; her cıvata kesme 350 N, çekme 173 N |
| Yatay kuyruk kökü (iki yarı) | M = 48 N·m, T = 32 N·m (her yarı, nihai) |
| Yatay kuyruk boru ve pim | **D14 × 2 karbon boru (241 MPa)**, yüksek Tg. Ø4 insidans pimi (341 N). Yatak kuvveti 687 N, 100 mm geçme boyu. |
| Kuyruk tamponu çerçevesi | Yatay kuyruk boru çerçevesiyle ortak (x ≈ 1,90) |

## 12. Test planı

1. **Kupon testleri:**
   - UD ve ±45 laminelerin E ve kopma birim uzaması.
   - Tank kaplamasının kerosene uyumu: 2 hafta daldırma sonrası ILSS kaybı < %10.
   - **Yüksek Tg reçine numunelerinde 150 °C'de basma testi.**
2. **Tank sızdırmazlık testi:** 15 kPa, 30 dk. Ardından 24 saat yakıtla bekletme.
3. **Kanat statik yük testi:** %67 → %100 → %150. Nihai yükte toplam 2,97 kN, yarım kanat başına ~151 kg kum. Kanat **bağlantı cıvatalarından** (A1 çerçeve düzeni ile aynı bağlantı noktalarından) mesnetlenir.
4. **Bağlantı testi:** Yunuslama kuvvet çifti ön/arka çerçevede 5,2 / 8,7 kN nihai. Cıvata yatağında kalıcı deformasyon olmamalı.
5. **Burulma testi:** Kök GJ ≥ %80 × 7324 N·m².
6. **GVT (tank dolu/boş):**
   - f_h ≈ 34 Hz, f_α ≥ 240 Hz (hesabın %80'i).
   - Kontrol yüzeyi dönme frekansı: aileron ≥ 51 Hz, elevator ≥ 150 Hz.
7. **Kızak düşürme testi:** 115 mm yükseklikten çime; n ≤ 9 g. Ayrıca **kuyruk-önce** düşürme ile tampon yükü ölçülür.
8. **Motor bölgesi sıcaklık ölçümü:** Yer çalıştırmasında tam gazda 3 dk; kabuk iç ve dış sıcaklığı ≤ Tg − 30 °C olmalı.
9. **Uçuş zarfı genişletme:** 400 → 800 km/h, her adımda +50 km/h. Kanat ucu ivmeölçeri ve darbe girişi ile sönüm izlenir. **GVT yapılmadan 600 km/h üstü yasak.**

## 13. Açık sorunlar ve params.py önerileri

| # | Konu | Öneri |
|---|---|---|
| 1 | Kat planı / kesit ağırlık merkezi | Yeni kalem: `WING["skin_plies"]=(3, 1)` (kiriş önü/arkası, yüz başına). `MASS_ITEMS` kanat 1,75 kg kalabilir (hesap 1,65 kg). |
| 2 | Kanat tankı 0,57 L/yarı (params 0,9 L) | `wing_integral_L_each = 0.57`. İsteğe bağlı `center_L = 0.27`. Toplam 4,0 kg için `fuselage_L`: merkez tank yoksa **3,86 L** (3,09 kg), varsa **3,59 L** (2,87 kg). |
| 3 | Kanat bağlantısı | Tek parça kanat + gövde içinden geçen kutu. `WING["attach"]=dict(type="carry-through", bolts="4xM6 12.9", x_frames=(1.006, 1.156), le_pins_x=0.94)`. Yeni kütle kalemi: 2 kiriş çerçevesi + longeronlar + hard point'ler ≈ 0,15 kg, x ≈ 1,08. |
| 4 | Kanat firar kenarı / motor çakışması | Gövde içinde kanat yalnız arka kirişe kadar (x ≤ 1,156); CAD'de gövde alt kabuğu x > 1,156 sürekli |
| 5 | Kuyruk çarpma açısı 3,2° (hedef 9° mümkün değil) | `GEAR["tail_bumper"]=dict(x=1.90, h=0.015)`, kütle 0,04 kg |
| 6 | Kızak çerçeveleri | `GEAR["skid_frames"]=(0.62, 0.81, 1.006, 1.156, 1.38)` |
| 7 | Motor bölgesi ısı | Malzeme notu: x 1,15–1,60 bölgesinde Tg ≥ 150 °C reçine, G10/çelik aşınma plakası, ısı keçesi (+0,05 kg) |
| 8 | Flap mekanizması | Ölü nokta kollu servo, dayanak ön yükü ≥ 2,2 N·m |
| 9 | Servolar | Aileron/elevator/flap 45 kg·cm (elevator için 15 kg·cm bile yeterli), rudder 60 kg·cm |
| 10 | Operasyonel −8,7 g hamle | Uçuş kartı notu |
