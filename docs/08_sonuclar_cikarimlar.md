# 08 · Proje Raporu: Sonuçlar ve Çıkarımlar

**Proje:** HIZ-750, 750 km/h ölçüm hızı hedefli türbinli RC jet İHA
**Sürüm:** v0.4.0 (iterasyon 3) · **Tarih:** 2026-11-04
**Kapsam:** Kavramsal tasarım + ön tasarım. Analizler, parametrik CAD ve dokümantasyon hazır; imalat ve test yapılmadı.

## 1. Yönetici özeti

Hedef olan 750 km/h, türbinli RC uçaklarda dünya rekoru seviyesinde (Herbrich 2017: 749,2 km/h). Üç tasarım iterasyonu sonunda:

- **Performans:** JetCat P400-PRO motorla 750 km/h'te **%40–90 itki payı** hesaplandı. Kötümser modelle azami hız ~878 km/h; operasyonel limit 800 km/h.
- **Kararlılık:** Statik marj %12,6–31,9 MAC. Yaw damper, g-limiter ve hıza göre değişen kumanda kazancı **zorunlu**.
- **Yapı:** Flutter hızı 1465 km/h, gereksinim 1080 km/h (pay %36). Diverjans 3290 km/h. Kanat 1,74 kg.
- **Geometri:** CAD'de parçalar arası çakışma yok. Yakıt 5,33 L, kuyruk çarpma açısı 12,4°, S-kanal ofset/uzunluk oranı 0,27.
- **Kütle ve mevzuat:** MTOW 17,0 kg. Türkiye'de İHA1 sınıfında (< 25 kg).

**Sonuç:** Tasarım kâğıt üzerinde kapanıyor. Hedefe ulaşmanın önündeki asıl risk aerodinamik değil, **uygulama kalitesi**: flutter (boşluk, kütle dağılımı), hava alığı verimi ve yüzey kalitesi. Bunlar ancak yer ve uçuş testleriyle doğrulanabilir.

## 2. Tasarımın iterasyonlarla evrimi

| Büyüklük | v0.1 Kavramsal | v0.2 İter1 | v0.3 İter2 | **v0.4 İter3** |
|---|---|---|---|---|
| Motor | P400-PRO | P400-PRO | P400-PRO | P400-PRO |
| MTOW [kg] | 17,3 | 18,3 | 16,8 | **17,0** |
| Kanat yeri (kök LE x / z) [m] | 0,88 / — | 1,00 / −0,035 | 0,92 / −0,035 | **0,92 / −0,080** |
| Dihedral | 0° | −1° | −1° | **+2°** |
| Kalkış / iniş | tekerli | retract tekerli | dolly + kızak | dolly + kızak + tampon |
| Yakıt [L] | 3,75 | 5,0 (tanklar sığmadı) | 5,2 | **5,33 (iç hacim)** |
| Nötr nokta [m] | — | 1,318 | 1,251 | 1,251 |
| Statik marj tam/boş [%MAC] | — | 39,7 / 29,4 ✗ | 29,5 / 12,4 | **31,9 / 12,6** |
| Flutter [km/h] | — | 1495* | 1356* (gerçekte ~1086 ✗) | **1465** |
| S-kanal ofset/uzunluk | — | çakışıyor ✗ | 0,50 ✗ | **0,27** |
| Kuyruk çarpma açısı | — | — | 2,6° ✗ | **12,4°** |
| CAD çakışması | — | 5 sorun ✗ | 0 | **0** |

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
| Türbin itkisinin hızla düşüşü | Basit `Vj`/`k_ram` modeli | **Düşük** | Uçuşta EGT/RPM/hız ile kalibrasyon |
| Hava alığı ram kazancı | Tahmin | **Düşük** | Yer testinde motor yüzü basınç taraması |
| Stabilite türevleri | AeroBuildup + VLM + DATCOM | Orta–yüksek | F1–F2 uçuşlarında trim karşılaştırması |
| Yapı yükleri | Schrenk + kiriş teorisi | Yüksek | %150 kum torbası yük testi |
| Flutter | 2-DOF Theodorsen, ders kitabı örneğiyle doğrulandı | Orta (frekanslar tahmin) | **GVT zorunlu** |
| Geometri / sığma | CadQuery katı model, çakışma hacmi | Yüksek | Kalıp öncesi kontrol |

## 5. Öneriler ve yol haritası

1. **Kısa vade (masa başı):**
   - S-kanal CFD'si (OpenFOAM veya SimScale)
   - Kanat ve gövde FEM'i (CalculiX)
   - Atalet momentlerini CAD'den alıp dinamik mod analizini güncellemek
   - Uçuş kontrol yazılımının (g-limiter, yaw damper) simülasyonu
2. **Prototip öncesi:**
   - P300-PRO ile ölçekli ya da hız limitli (≤ 500 km/h) bir test uçağı
   - Ram kazancı ve itki modelini motor yer testlerinde ölçmek
3. **Prototip:**
   - Kalıp, yük testi, GVT
   - F1–F6 uçuş zarfı genişletme planı (bkz. 06)
4. **İterasyon 4 adayları:**
   - Ölçümlerle `k_ram` ve `Vj` güncellemesi
   - Hücum kenarı droop ile iniş hızını < 85 km/h yapmak
   - Gövde çapını 155 mm'ye indirme fizibilitesi (sürükleme −%8 civarı, motor boşluğu kritik)
   - Yaklaşma hızında yaw damper kazanç tablosu

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
