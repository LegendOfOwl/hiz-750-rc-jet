# 03 — CAD modeli ve teknik çizimler (iterasyon 3, kapanış)

Model tamamen parametrik. Bütün ölçüler [`params.py`](../params.py)'den okunuyor; CAD içinde birim **mm**. Koordinatlar: x burundan arkaya, y sağ kanada doğru, z yukarı. Önceki iterasyonların parametreleri [`params_iter1.py`](../params_iter1.py) ve [`params_iter2.py`](../params_iter2.py) dosyalarında. Bütün sayısal sonuçlar [`cad/out/cad_report.json`](../cad/out/cad_report.json)'da.

## Yeniden üretme

```bash
C:/Users/Urungu/.hz750/Scripts/python cad/build_cad.py
```

Script: [`cad/build_cad.py`](../cad/build_cad.py). Çalışması yaklaşık 25 saniye sürüyor; çıktı günlüğü `cad/out/build_log.txt`'e yazılıyor. Dışa aktarma önce `C:/Users/Urungu/.hz750` altındaki kısa yollu geçici bir klasöre yazıyor, sonra dosyayı yerine taşıyor. Sebebi, OCP'nin Windows'taki uzun yol sınırına takılması.

## İterasyon 3 değişiklik özeti

| Konu | İterasyon 2 | İterasyon 3 kapanış (CAD karşılığı) |
|---|---|---|
| Kanat | z_root −35 mm, −1° anhedral | **Alçak kanat**: z_root −80 mm, **+1,5° dihedral**. Kutu üst yüzeyi kökte z = −64,7 mm |
| Kanat bağlantısı | Kanat kutusu ayrı parça; gövde içinde kanat modellenmiyordu | **Tek parça kanat** (`attach`). Kutu gövdenin içinden geçiyor. Gövde içinde kanat yalnız x ≤ 1156 mm'de var (yeni parça `wing_center`); bunun gerisinde 1,5 mm'lik kesintisiz alt kabuk motorun altından geçiyor. Çerçeveler x 1006 ve 1156 mm'de |
| Çerçeveler | – | Yeni parça `frames`, 4 mm kalınlık, 5 mm radyal derinlik. Kanat bağlantı çerçeveleri tam halka; kızak çerçeveleri (x 620 / 810 / 1380) alt yay (±55°). Kanal, kanat kutusu ve kanatla kesiliyor |
| Karın kaplaması | – | `belly_fairing`: x 860–1459 mm, düz taban z = −96,0 mm. **Gövde altından 13,5 mm derin**, 777 cm³ |
| S-kanal | Dudak 0,95, ofset/uzunluk 0,50 | Dudak 0,85, uzunluk 330 mm, **yarı gömülü dudak**: merkez z = 88 mm, dudağın 22 mm'si gövde yüzeyinin altında. Dudak önünde 7°'lik rampa (x 671–850 mm, 22 mm derin, yan duvarlı). Diverter kaldırıldı. 10 kesit; alan doğrusal artıyor |
| Kanal ↔ kabuk | Kabuk kanalın iç hacmiyle kesiliyordu | Kabuk kanalın **dış** hacmiyle kesiliyor; kanal duvarı, deldiği kabuğun yerini alıyor |
| Flap | Düz menteşeli, cf 0,22 | **Tek yarıklı**, cf 0,25; 2,5 mm yarık + ayrı dış menteşe hattı |
| Elevatör | cf 0,28 | cf 0,22 |
| Yakıt | Gövde + 2 kanat tankı | Gövde + 2 kanat tankı + **kanat kutusu orta tankı** (`tank_center`). Bütün değerler **iç hacim**: kanat tankları 2,6 mm kabuk / 1,5 mm web / 3 mm kaburga düşülerek, gövde tankı 1 mm duvar düşülerek |
| Kızak / tampon | Kızak x 620–1300 mm | Kızak x 620–1450 mm. **Kuyruk tamponu** (yeni parça `tail_bumper`): x 1810–1930 mm, gövde altından 22 mm derin |
| Gövde spline'ı | Burnun x 400–800 mm aralığında örnek noktası yoktu; dış yüzey analitik ogive eğrisinden biraz sapıyordu | Örnekleme ogive boyunca sıklaştırıldı; dış yüzey artık analitik eğriye uyuyor |

## Üretilen dosyalar (`cad/out/`)

| Dosya | İçerik |
|---|---|
| `HIZ750_assembly.step` | Uçuş konfigürasyonu montajı (renkli) |
| `HIZ750_on_dolly.step` | Uçak + kalkış arabası |
| `step/*.step`, `stl/*.stl` | 27 parça. Yeni: `wing_center`, `tank_center`, `tail_bumper`, `frames`. Diğerleri: `fuselage`, `inlet_duct`, `wing_panels`, `wing_box`, `belly_fairing`, `tank_wing_L/R`, `aileron_L/R`, `flap_L/R`, `htail`, `elevator_L/R`, `ht_carry_yoke`, `vtail`, `rudder`, `engine`, `exhaust_pipe`, `tank_fuselage`, `skid`, `dolly`. `diverter` artık yok (yarı gömülü dudak) |
| `HIZ750_3view.dxf` / `.png` / `.pdf` | Ölçülendirilmiş 3 görünüş: kızak, tampon, karın kaplaması, flap menteşe hattı, kuyruk çarpma çizgisi |
| `HIZ750_inboard.png` / `.pdf` | İç yerleşim: gerçek kanal kesitleri, bütün tanklar, karın kaplaması, tampon |
| `HIZ750_iso.png` | İzometrik render |
| `cad_report.json` | Bütün sayısal sonuçlar |

![3 görünüş](../cad/out/HIZ750_3view.png)
![iç yerleşim](../cad/out/HIZ750_inboard.png)
![izometrik](../cad/out/HIZ750_iso.png)

## Profiller

- **Kanat: NACA 64A007 (kök) → 64A006 (uç).** Kaynak: Abbott & von Doenhoff tablosundaki NACA 64A010 ordinatları, t/c'ye göre doğrusal ölçekleniyor; ara noktalar √x uzayında PCHIP ile interpole ediliyor. Firar kenarına 0,3 mm kalınlık eklendi.
- **Kuyruklar: NACA 0006.**
- **Tank iç yüzeyi:** aynı kesitlerin kalınlığı her yüzde 2,6 mm azaltılarak üretiliyor (yüzeye dik ofset yaklaşımı).
- **Kabuk kat sayısı:** params'taki `skin_plies = (3, 1)` yapı analizinin girdisi. CAD'de kabuk kalınlığı yalnızca tank iç hacmini hesaplarken kullanılıyor (2,6 mm sandviç).

## 1. S-kanal

| Büyüklük | Değer | Hedef |
|---|---|---|
| Uzunluk (dudak 850 → motor yüzü 1180 mm) | 330 mm | |
| Düşey ofset (dudak merkezi z 88 → 0 mm) | 88 mm | |
| **Ofset / uzunluk** | **0,267** | ≤ 0,30 ✓ |
| Alan: dudak → motor yüzü | 60,5 → 125,0 cm² (oran 2,07) | |
| **Eşdeğer difüzör yarı açısı** | ortalama **3,33°**, en çok **3,95°** | ≤ 7° ✓ |
| **En dik duvar açısı** | **25,6°**: taban, x 974–1015 mm (S-bükümünün ortası) | |
| Son segment (x 1158 → 1180) | taban 11,4°, tavan 0,8° | iterasyon 3a'da 41,7° idi |
| Kanat kutusu bölgesinde kanal iç tabanı | ≥ −58,7 mm | |
| Dudak önü rampa | 7°, 179 mm uzun, 22 mm derin | |

**Kesit tablosu** (merkez düzlem; a = yarı genişlik, b = yarı yükseklik, mm):

| x | Şekil | Merkez z | a | b | Taban | Tavan | Alan (cm²) |
|---|---|---|---|---|---|---|---|
| 850,0 | dikdörtgen | 88,0 | 55,0 | 27,5 | 60,5 | 115,5 | 60,5 |
| 891,2 | elips | 84,2 | 56,0 | 39,0 | 45,3 | 123,2 | 68,6 |
| 932,5 | elips | 74,2 | 57,0 | 42,8 | 31,5 | 117,0 | 76,6 |
| 973,8 | elips | 60,2 | 58,0 | 46,4 | 13,7 | 106,6 | 84,7 |
| 1015,0 | elips | 44,0 | 59,0 | 50,0 | −6,0 | 94,0 | 92,7 |
| 1056,2 | elips | 27,8 | 60,0 | 53,4 | −25,6 | 81,3 | 100,8 |
| 1097,5 | elips | 13,8 | 61,1 | 56,8 | −43,0 | 70,5 | 108,9 |
| 1138,8 | elips | 3,8 | 62,1 | 60,0 | −56,2 | 63,7 | 116,9 |
| 1158,2 | elips (arka kiriş + 2) | 2,1 | 63,2 | 60,7 | −58,7 | 62,8 | 120,7 |
| 1180,0 | daire (motor yüzü) | 0,0 | 63,1 | 63,1 | −63,1 | 63,1 | 125,0 |

Taban kısıtı bu iterasyonda devreye girmedi: kanal, kanat kutusunun üstünden doğal smoothstep eğrisiyle geçiyor. Kalan 18–26°'lik taban eğimi S-bükümünün kendi geometrisinden geliyor: ofset/uzunluk 0,267 için smoothstep'in en dik eğimi 1,5 × 88 / 330 → 21,8° (merkez hattı), tabanda alan artışıyla birlikte 25,6°. Dorsal çıkıntı: kanalın gövde dışında kalan kısmı (ön kirişin gerisinde) 7,0 cm³; çıkıntının en yüksek noktası z = 125 mm, yani gövde üstünden ~43 mm yukarıda (iterasyon 3a'da ~70 mm idi).

## 2. Yakıt tankları (bütün değerler iç hacim)

| Tank | İç hacim | Ağırlık merkezi x | params hedefi |
|---|---|---|---|
| Gövde (x 751–1003 mm) | **3,630 L** | 0,868 m | 3,63 L |
| Kanat, sağ / sol (η 0,06–0,55) | **0,715 L / 0,715 L** | 1,151 m | 0,65 L |
| Kanat kutusu orta tankı (\|y\| ≤ 40,5 mm) | **0,274 L** | 1,082 m | 0,27 L |
| **Toplam** | **5,335 L** | | ≥ 5,2 L ✓ (yakıt 5,0 L) |
| **Yakıt CG'si** | **x = 0,955 m**, **z = −0,029 m** | | params x 0,957 / z −0,02 |

Kanat tankının iç hacmi, tanım farkına göre (yarı kanat başına):

| Tank tanımı | CAD iç hacmi |
|---|---|
| η 0,06–0,55 (params, modellenen) | 0,715 L |
| η 0,06–0,40 | 0,577 L |
| Gövde yanı → η 0,40 (yapı ajanı 0,39 L) | 0,456 L |
| Gövde yanı → η 0,55 | 0,594 L |

Gövde tankı params'taki alt sınır olan 3,63 L'de tutuldu. Kanat tankları params'taki 0,65 L yerine 0,715 L çıktığı için toplam 5,335 L oldu.

## 3. Yer geometrisi

| Büyüklük | Değer | Hedef |
|---|---|---|
| **Kuyruk çarpma açısı (tampon dahil)**: tampon arka-alt köşesi (x 1930, z −93,4) etrafında | **12,4°**. Temas noktası kuyruk konisinin ucu (x 2100, z −56) | ≥ 9° ✓ |
| Kızak sonu → tampon temas açısı | −0,15°. Tampon tabanı kızak taban çizgisiyle neredeyse aynı düzlemde (0,9 mm aşağıda); uçak yerde kızak + tampon üzerinde yatay duruyor | |
| **Dolly üzerinde yer açıklığı, 3°** (`dolly_alpha`; arka teker temas noktası x 1502 etrafında burun yukarı) | **86,5 mm** (en alçak nokta: tampon, x 1930) | |
| Dolly üzerinde, 0° / 6° | 106,5 mm (x 945) / 63,7 mm (x 1930) | |
| **Karın kaplaması derinliği** | **13,5 mm** (taban z −96,0; gövde altı −82,5) | |

## 4. Çakışma kontrolü (mm³)

**Bütün çakışma kontrolleri 0.** Kontrol edilen çiftler:
- **Motor ↔** kabuk, kanat kutusu, kanal, kanadın arka alt kabuğu.
- **Kanal ↔** kanat kutusu, kabuk.
- **Gövde içindeki kanat (`wing_center`) ↔** motor, kanal, gövde tankı.
- **Tanklar:**
  - gövde tankı ↔ kanal, kutu, kabuk, rampa;
  - kanat tankları ↔ kanal, motor;
  - orta tank ↔ kanal, motor.
- **Çerçeveler ↔** motor, tanklar, kanal, kabuk.
- **Kuyruk:**
  - yatay kuyruk + taşıyıcı çerçeve ↔ egzoz;
  - taşıyıcı çerçeve ↔ kabuk (saplama delikleri açık);
  - dikey kuyruk ↔ egzoz.
- **Alt taraf:**
  - kızak ↔ kabuk;
  - tampon ↔ kabuk;
  - karın kaplaması ↔ tank, kızak, kanat;
  - dolly ↔ uçak;
  - flap ↔ panel (yarık açık).

Raporda sıfır olmayan tek kalem 7,0 cm³: dorsal çıkıntıdaki kanal duvarının gövde dışında kalan hacmi. Bu bir çakışma değil, tasarım gereği.

Diğer ölçümler:
- Motor–gövde iç yüzeyi radyal boşluğu: en az 5,97 mm.
- Arka kiriş → motor yüzü: 23,8 mm.
- Islak alan: gövde 0,916, açıkta kalan kanat 0,838, yatay kuyruk 0,122, dikey kuyruk 0,117, kızak ~0,043 m².

## Kalan notlar ve params önerileri (CAD ajanı params.py'yi değiştirmedi)

1. `FUEL["tanks"]["wing_integral_L_each"]`: CAD iç hacmi η 0,06–0,55 için 0,715 L. Params 0,65 L diyor. Bölme payı ve ara bölme dahil edilen değer 0,65 L ise sorun yok; ama kapasite toplamı bu durumda 5,2 L değil 5,33 L'dir.
2. `FUEL["x"] = 0.955`, `FUEL["z"] = -0.029` (ölçülen değerler; params'ta 0,957 / −0,02).
3. Rampa x 671'de başlıyor; ECU (x 0,65) rampanın 21 mm önünde ve merkez düzlemde z = 0'da. Rampa tabanı (z ≥ 60 mm) ile ECU arasında çakışma yok, ama ECU'ya üstten erişim rampa yüzünden kısıtlı.
4. Dorsal çıkıntı yaklaşık 43 mm; sürükleme hesabında ön kesit alanı ≈ 114 × 43 ≈ 49 cm² (gövde kesitinin %23'ü) olarak alınmalı.
