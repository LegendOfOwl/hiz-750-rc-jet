# 08 · Proje Raporu: Sonuçlar ve Çıkarımlar

**Proje:** HIZ-750, 750 km/h ölçüm hızı hedefli türbinli RC jet İHA
**Sürüm:** v0.6.0 (iterasyon 3 + iter4 masa başı doğrulamaları + iter5 yüksek doğruluk) · **Tarih:** 2026-11-08 (iter5 inceleme güncellemesi)
**Kapsam:** Kavramsal tasarım + ön tasarım. Analizler, parametrik CAD ve dokümantasyon hazır; imalat ve test yapılmadı.

## 1. Yönetici özeti

Hedef olan 750 km/h, türbinli RC uçaklarda dünya rekoru seviyesinde (Herbrich 2017: 749,2 km/h). Üç tasarım iterasyonu sonunda:

- **Performans:** JetCat P400-PRO motorla 750 km/h'te **%40–90 itki payı** hesaplandı. Kötümser modelle azami hız ~878 km/h; operasyonel limit 800 km/h.
- **Kararlılık:** Statik marj %13,0–32,8 MAC (iter5). Yaw damper, g-limiter ve hıza göre değişen kumanda kazancı **zorunlu**.
- **Yapı (iter5):** Kompozit kabuk FEM (CalculiX) 1D modelin burulma frekansını %11 iyimser buldu. Kanat rijitleştirildi (4/1 kat, 43 mm kaburga, web +1 kat; kanat 2,03 kg). Flutter tasarım değeri **≈1267 km/h** (kabuk-FEM frekans ölçeklemesi), gereksinim 1080 km/h, pay %17; ×1,25 model payı (1350 km/h) sağlanmıyor. Önceki değerler: iter4 1D FE modal 1307 km/h, 2-DOF 1465 km/h. Ok açılı kanatta diverjans yok. Kanadın bütün uçak (kuyruk, kumanda yüzeyleri, gövde) aeroservoelastik çözümü yok.
- **Kontrol (iter4, iter5 kütlesiyle yeniden üretildi):** g-limiter, boş yakıtta n'yi 10,05 g'de tutuyor (FC'siz 26–31 g). Yaw damper ζ_DR 0,33–0,44. Tüm zarfta GM ≥ 9,4 dB, PM ≥ 49,9° (sensör filtreleri modelde yok).
- **Geometri:** CAD'de parçalar arası çakışma yok. Kullanılabilir yakıt 5,14 L (brüt 5,43 L; iter5 kaburgalarıyla ~5,0 L'ye inebilir, açık), kuyruk çarpma açısı 12,4°, S-kanal ofset/uzunluk oranı 0,27.
- **Kütle ve mevzuat:** MTOW 17,44 kg. Türkiye'de İHA1 sınıfında (< 25 kg).
- **Termal (iter5):** Motor–kabuk en dar aralığı 5,97 mm; 2 mm ısı keçesi zorunlu. Koşullu model en kötü yer senaryosunda keçeyle 126 °C veriyor, test kriteri < 120 °C: ölçümle kapanması gereken açık madde.

**Sonuç:** Tasarım kâğıt üzerinde kapanıyor, ancak yalnız masa başı ve koşullu modellerle. Hedefe ulaşmanın önündeki asıl risk aerodinamik değil, **uygulama kalitesi ve doğrulanmamış alt sistemler**: bütün uçak flutter'ı (boşluk, kütle dağılımı, servo rijitliği), takılı motorun gerçek itkisi, hava alığı verimi, motor bölmesi sıcaklığı ve yüzey kalitesi. Bunlar ancak yer ve uçuş testleriyle doğrulanabilir (§5).

## 2. Tasarımın iterasyonlarla evrimi

| Büyüklük | v0.1 Kavramsal | v0.2 İter1 | v0.3 İter2 | v0.4 İter3 | **v0.6 İter5** |
|---|---|---|---|---|---|
| Motor | P400-PRO | P400-PRO | P400-PRO | P400-PRO | P400-PRO |
| MTOW [kg] | 17,3 | 18,3 | 16,8 | 17,0 | **17,44** |
| Kanat yeri (kök LE x / z) [m] | 0,88 / — | 1,00 / −0,035 | 0,92 / −0,035 | 0,92 / −0,080 | 0,92 / −0,080 |
| Dihedral | 0° | −1° | −1° | +2° | +2° |
| Kalkış / iniş | tekerli | retract tekerli | dolly + kızak | dolly + kızak + tampon | dolly + kızak + tampon |
| Yakıt [L] | 3,75 | 5,0 (tanklar sığmadı) | 5,2 | 5,33 (iç hacim) | **5,14 kullanılabilir** (~5,0 açık) |
| Nötr nokta [m] | — | 1,318 | 1,251 | 1,251 | 1,251 |
| Statik marj tam/boş [%MAC] | — | 39,7 / 29,4 ✗ | 29,5 / 12,4 | 31,9 / 12,6 | **32,8 / 13,0** |
| Flutter [km/h] | — | 1495* | 1356* (gerçekte ~1086 ✗) | 1465 (2-DOF; iter4 FE 1307) | **≈1267** (kabuk FEM ölçekli) |
| S-kanal ofset/uzunluk | — | çakışıyor ✗ | 0,50 ✗ | 0,27 | 0,27 |
| Kuyruk çarpma açısı | — | — | 2,6° ✗ | 12,4° | 12,4° |
| CAD çakışması | — | 5 sorun ✗ | 0 | 0 | 0 |
| Kanat kütlesi / kat planı | — | — | — | 1,75 kg, 3/1 | **2,03 kg, 4/1 + 43 mm kaburga + web +1** |

\* İter1 ve iter2'nin flutter değerleri, kesit ağırlık merkezi 0,42c varsayıldığı için iyimserdi (bkz. §3, çıkarım 3).

## 3. Temel çıkarımlar (lessons learned)

1. **Bu hızda sürüklemeyi yüzey sürtünmesi belirliyor.** 750 km/h'te CL ≈ 0,015, indüklenmiş sürükleme ihmal edilebilir. Hızı artıran şey ıslak alanı küçültmek ve yüzeyi cilalamak. Laminer akış kazancı +30 km/h, kötü hava alığı ve boşlukların kaybı −40 km/h. Herbrich'in 7,5 kg'lık ve ~180 N'luk uçağı da bunu gösteriyor.
2. **Aerodinamik merkezi %25 MAC kabul etmek yanıltıcı oldu.** Kuyruk ve gövde etkisiyle nötr nokta %50–54 MAC çıktı. İter1'deki kanat yeri, statik marjı %40 yaptı. Ağırlık merkezi kararını AeroSandbox ile hesaplanan nötr noktaya göre vermek gerekiyor.
3. **Flutter, kesitin ağırlık merkezine son derece duyarlı.** Ağırlık merkezi 0,42c'den 0,52c'ye kayınca flutter hızı 1383'ten ~1086 km/h'e düştü. Kat eklemek çözmüyor (4/4 kat bile 1427 km/h). Çözüm, kütleyi öne almak: kabuk kiriş önünde 3, arkasında 1 kat. **İmalatta boya ve dolgu kanadın arka kısmına yığılmamalı.**
4. **Motor gövdenin içindeyse hava kanalı, kanat kutusu ve yakıt aynı hacmi paylaşıyor.** Konfigürasyonu asıl şekillendiren bu çakışmalardı: tank yerleşimi, kanadın yüksekliği, S-kanal. CAD'deki otomatik çakışma kontrolü bu sorunları erken yakaladı.
5. **Bu sınıfta iniş takımı pahalı.** 25 mm kalınlıktaki kanada teker sığmıyor ve takım 1,5 kg ağırlık getiriyor. Rekor modellerindeki dolly + kızak yaklaşımı bu tasarıma da uydu. Bedeli: yalnız çim iniş, kuyruk tamponu ve dolly mekanizması.
6. **Yüksek dinamik basınç (q = 26–37 kPa) kontrolü yazılım sorununa çeviriyor.** Pasif önlemler yetmedi: elevator veterini küçültmek boş yakıtta 25 g'yi önlemedi. Ayrıca Dutch roll sönümü ζ ≈ 0,10'da kaldı. G-limiter, yaw damper ve hıza/yakıta göre değişen kumanda limitleri tasarımın parçası sayılmalı.
7. **Tek veri kaynağı (`params.py`) ve yeniden çalıştırılabilir scriptler iterasyonu hızlandırdı.** Bir parametre değişikliği CAD, aero, yapı ve performansın tamamına ~1 dakikada yayılıyor. İterasyonları da üç paralel alt-ajan (CAD, aero, yapı) ve bir entegrasyon döngüsü olarak yürüttük.

## 4. Doğrulama durumu

| Konu | Yöntem | Güven | Doğrulama yolu |
|---|---|---|---|
| Sürükleme | Bileşen yöntemi (Raymer) + AeroBuildup; ikisi arasında %25 fark | Orta | Uçuş telemetrisi (itki-hız) |
| Kütle / atalet | CAD katıları + nokta kütleler (iter4) | Orta–yüksek | Tartı, CG ölçümü, bifilar sarkaç ile atalet ölçümü |
| Uçuş kontrol yasası | Doğrusal modeller, 20 ms gecikme, servo modeli (iter4) | Orta | Donanım-döngüde (HIL) test, F1–F2 kazanç ayarı |
| Türbin itkisinin hızla düşüşü | Basit `Vj`/`k_ram` modeli | **Düşük** | Uçuşta EGT/RPM/hız ile kalibrasyon |
| Hava alığı ram kazancı | Yarı-ampirik η_r = 0,970 (iter4) | Düşük–orta | Yer testinde motor yüzü basınç taraması |
| Stabilite türevleri | AeroBuildup + VLM + DATCOM | Orta–yüksek | F1–F2 uçuşlarında trim karşılaştırması |
| Yapı yükleri | Schrenk + kiriş teorisi | Yüksek | %150 kum torbası yük testi |
| Flutter (kanat) | Kabuk FEM (iter5, REVIEW_REQUIRED; malzeme sabitleri varsayım) + iter4 p-k eğrisinde frekans ölçekleme | Düşük–orta | **GVT zorunlu: f_1T ≥ 230 Hz**; kabuk mod şekilleriyle p-k açık |
| Flutter (bütün uçak: kuyruk, kumanda yüzeyleri, gövde) | Çözülmedi (yalnız frekans kestirimleri) | **Düşük** | Serbest-serbest GVT + bütün uçak aeroservoelastik model |
| CFD doğrulama | SU2: düz levha SA kabul (GCI %0,88), RAE2822 PENDING | Orta (2B) | RAE üç ağ, SST, 3B uçak/alık CFD |
| Motor bölmesi sıcaklığı | CalculiX 1B koşullu model (h/k/ε ölçülmedi) | Düşük | Yer çalıştırmasında termokupl, iç kabuk < 120 °C |
| Hava verisi (q) | Kazanç programı q̄ ile; pitot q_c ≠ q̄ (M 0,61'de %10) | Orta | Statik basınçla Mach dönüşümü, uçuşta hava verisi kalibrasyonu |
| Geometri / sığma | CadQuery katı model, çakışma hacmi | Yüksek | Kalıp öncesi kontrol |

## 5. Öneriler ve yol haritası

1. **Masa başı (tamamlananlar):**
   - ✅ Atalet momentleri CAD'den hesaplandı, dinamik modlar güncellendi (v0.5.0; iter5 kütlesiyle yeniden üretildi).
   - ✅ Kanat FE modal ve flutter analizi (v0.5.0), kompozit kabuk FEM ve rijitleştirme (v0.6.0).
   - ✅ g-limiter ve yaw damper tasarımı ve simülasyonu (v0.5.0).
   - ✅ Alığın yarı-ampirik basınç kazanımı (v0.5.0), düz levha SA CFD benchmarkı (v0.6.0).
2. **Masa başı (açık, prototipten önce):**
   - Kabuk mod şekilleriyle p-k flutter; **bütün uçak** (yatay/dikey kuyruk, elevator/rudder/aileron, gövde, servo ve bağlantı esnekliği) aeroservoelastik modeli.
   - Kanat tankı kullanılabilir hacmi 43 mm kaburgalarla yeniden (≈5,0 L; `params.FUEL` ve yakıt CG'si), tank bazında yakıt CG zarfı ve besleme sırası, yakıt transfer/hopper basınç bütçesi.
   - Sensör filtresi, IMU gecikmesi ve notch filtreli kontrol payları; değişken kazançlı zaman simülasyonu; 350 km/h altı kontrol yasası (F1 ön koşulu); manevra + hamle birleşik yük zarfı.
   - Takılı motor modeli: düzeltilmiş debi/devir, giriş sıcaklığı, alık-motor çalışma noktası; itki ekseni momenti trimde.
   - RAE2822 üç ağ kabulü, SST/profil taraması, S-kanal ve 3B uçak CFD; `thermal_1d` yeniden koşumu.
   - Görev profili: hız-irtifa-yük faktörü-yakıt birlikte entegre (dönüş ve yeniden hızlanma yakıtı).
3. **Prototip öncesi fiziksel testler (sırasıyla):**
   - **Malzeme kuponları:** CLT/kabuk modeli için E1, E2, G12, mukavemet; hot/wet Tg ve sıcaklıkta dayanım (motor bölgesi reçinesi).
   - **Türbin motor testi (itki standı):** Statik itki, yakıt debisi, EGT/RPM; alık + S-kanal + egzoz takılıyken net itki kaybı; motor yüzü basınç tarağı (η_r, distorsiyon); ısı keçesi ile termokupl ölçümü (< 120 °C).
   - **Alık rüzgâr tüneli testi (veya araç üstü/çekili test):** MFR 0,5–2,5 aralığında η_r, distorsiyon, yan emiş kapakları; `inlet_analysis.py` kalibrasyonu.
   - **Statik yük testi:** Kanat limit (12 g) ve nihai (18 g, ayrı test kanadı) yük, kanat-gövde bağlantısı (4× M6, çerçeveler), yatay kuyruk bağlantısı, kızak darbe yükü; burulma rijitliği (GJ).
   - **GVT:** Serbest-serbest bütün uçak, dolu/boş tank, kumanda yüzeyi dönme modları; f_1T ≥ 230 Hz kanat ölçütü + bütün uçak mod eşleştirmesi; boşluk testi (≤ 0,1°).
   - **Servo testi:** Gerçek kol oranı ve menteşe yüküyle tork-hız, boşluk, dinamik rijitlik, düşük gerilim/sıcaklık; sonuç kontrol ve flutter modellerine.
   - **HIL (donanım-döngüde):** Gerçek FC, IMU filtreleri, 50/200 Hz döngü; arıza senaryoları (servo kilitlenmesi farklı sapmalarda, sensör kaybı), mod geçişleri.
   - **Yakıt sistemi:** Tank sızdırmazlık (15 kPa), transfer ve hopper beslemesi, negatif g, sıcak yakıt.
   - **Dolly testi:** Mandal L/W ≥ 1 ayrılma, yer koşusu (motorlu, düşük hız).
4. **Ölçekli/hız limitli öncü uçak:** P300-PRO ile veya ECU sınırlı (≤ 500 km/h) test uçağı; itki modeli, kontrol yasası ve hava verisi kalibrasyonu.
5. **Prototip uçuş zarfı genişletme:** F1–F6 (doküman 06 §6.4). GVT ve HIL olmadan 600 km/h üstüne çıkılmaz; her fazda telemetriyle itki-hız, trim ve titreşim kontrolü; hız sınırı ECU gaz yüzdesi değil, ölçülen hava hızı (aşırı hız koruması) üzerinden.
6. **Mevzuat ve operasyon:** SHGM İHA1 kaydı ve pilot sertifikası; 2026 lisans rejimi (P0/P1/P2) güncel metinden kontrol; izinli saha ve uçuş izni (NOTAM/hava sahası); saha güvenlik planı (seyirci ≥ 150 m, kaçış yönü); sigorta; Guinness/FAI ölçüm kanıt gereksinimleri; motor alımında son kullanıcı beyanı.
7. **İterasyon 6 adayları:**
   - Ölçümlerle `k_ram`, `Vj` ve itki modelinin güncellenmesi.
   - Hücum kenarı droop ile iniş hızını < 85 km/h yapmak.
   - Gövde çapını 155 mm'ye indirme fizibilitesi (sürükleme −%8 civarı, motor boşluğu kritik).
   - V_D (900 km/h) gerekçesi: tam gazda Vmax tahmini 878–898 km/h, yani V_D ≈ Vmax; aşırı hız koruması veya V_D artışı değerlendirilmeli.

## 6. Projenin varsayımları (düzeltilebilir)

| # | Varsayım | Nerede |
|---|---|---|
| 1 | Ölçüm 300 m irtifada, ISA, rüzgarsız; ölçüm hızı 750, operasyonel limit 800 km/h | `params.py`, `sizing.py` |
| 2 | Motor JetCat P400-PRO; itki ve yakıt değerleri üretici veri sayfasından | `params.py` |
| 3 | Türbin modelinde Vj = 540 m/s, k_ram = 0,6, alık kaybı %4 (ölçülmedi) | `sizing.py` |
| 4 | Yapı: limit +12/−8 g, emniyet katsayısı 1,5, V_D 900 km/h, flutter payı 1,2·V_D | `params.py` |
| 5 | Malzeme: T700/epoksi UD, 160 g/m² ±45 karbon, Rohacell 2 mm; knock-down faktörleri 04'te | `structures.py` |
| 6 | Türkiye'de İHA1 kuralları geçerli, uçuş izinli bir model uçak sahasında | 07 |
| 7 | Pilot deneyimli türbin pilotu; kalkış asfaltta, iniş çimde | 05, 07 |
| 8 | Fiyatlar 2026 tahmini; motor fiyatı doğrulanmadı | 06 |
