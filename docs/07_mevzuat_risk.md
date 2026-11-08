# 07 · Mevzuat, Güvenlik ve Risk Analizi

## 7.1 Mevzuat

| Bölge | Kural | HIZ-750 için anlamı |
|---|---|---|
| Türkiye (SHT-İHA Rev-05) | İHA1: 4–25 kg. iha.shgm.gov.tr'de kayıt + pilot sertifikası. İHA2 (≥ 25 kg) tescil ister | MTOW 17,44 kg (iter5), İHA1 sınıfında. Uçuş için izinli bölge/model uçak sahası ve ilgili uçuş izinleri gerekir. 2026'da bildirilen yeni P0/P1/P2 lisans rejimini güncel metinden kontrol et |
| AB (2019/947) | Open kategori < 25 kg; kulüp izni (Art. 16) ile istisnalar | AB'deki bir yarışmada kulüp/dernek izni gerekebilir |
| ABD (AMA 510-D) | Türbin itkisi ≤ 222 N, T/W ≤ 0,9 | HIZ-750 (425 N, T/W 2,5) AMA kurallarına uymaz |
| İhracat/satış | Büyük türbinlerin bazıları "kısıtlı satış" | Satın alma öncesi bayiden son kullanıcı beyanı vs. istenebilir |

> Bu proje sivil bir hobi ve hız rekoru modelidir. Bir uçuş sahasında görsel menzil içinde, kalabalıktan uzakta uçurulmalıdır.

## 7.2 Saha güvenliği
- Ölçüm hattı seyirci ve pit alanına **paralel değil, ondan uzaklaşan** bir yönde olmalı. Seyirci hattına minimum 150 m mesafe bırakılmalı.
- 750 km/h'te 1 saniyelik kontrol kaybı 208 m demek. Uçuş yönü, kayıp durumunda uçağın boş alana gideceği şekilde seçilmeli.
- Türbin: CO₂ söndürücü hazır olmalı, yakıt ikmali motor kapalıyken yapılmalı, egzoz arkasında 5 m kimse durmamalı.
- Uçuş ekibi: pilot + gözcü (spotter) + telemetri operatörü + ölçüm görevlisi.

## 7.3 FMEA (hata türleri ve etkileri, özet)

Puanlar: Ş = şiddet, O = olasılık, T = tespit edilebilirlik (1–10). RPN = Ş × O × T.

| # | Hata türü | Etkisi | Ş | O | T | RPN | Önlem |
|---|---|---|---|---|---|---|---|
| 1 | Kontrol yüzeyi flutter'ı | Yapı kaybı, düşüş | 10 | 4 | 6 | 240 | Kütle dengesi, sıfır boşluk, GVT, kademeli zarf genişletme |
| 2 | Kanat eğilme-burulma flutter'ı / diverjans | Yapı kaybı | 10 | 2 | 5 | 100 | GJ yeterliliği (bkz. 04), ±45 kabuk katları, burulma testi |
| 3 | Sinyal kaybı (RF) | Kontrolsüz uçuş | 10 | 3 | 3 | 90 | Çift alıcı, fail-safe, menzil testi, ölçüm hattı pilota yakın |
| 4 | Motor alevinin sönmesi (flame-out) | Motorsuz iniş | 7 | 3 | 2 | 42 | Hopper, yakıt rezervi, negatif g testi; süzülerek iniş pratiği |
| 5 | Yakıt bitmesi | Motorsuz iniş | 7 | 3 | 2 | 42 | Telemetri alarmı (%20), sorti başına 2 geçiş kuralı |
| 6 | Hava alığı tıkanması / yabancı madde girişi | Motor hasarı | 8 | 2 | 4 | 64 | Pist temizliği, alık ızgarası (ince tel), yer çalıştırma kontrolü |
| 7 | Servo / güç kaybı | Kontrol kaybı | 10 | 2 | 3 | 60 | Yedekli güç dağıtıcı, çift akü, servo akım telemetrisi |
| 8 | Aşırı g (pilot kaynaklı) | Kanat kırılması | 10 | 3 | 4 | 120 | Hız modunda sapma limitleri, gyro g-limiti, eğitim |
| 9 | Isıl hasar (egzoz/gövde) | Yapı zayıflaması, yangın | 8 | 3 | 4 | 96 | Bypass borusu, **2 mm ısı keçesi zorunlu** (iter5 termal: 5,97 mm aralıkta keçesiz yer çalıştırmasında kabuk 149,8 °C ≈ Tg 150 °C; keçeyle 126 °C), yer çalıştırma süresi sınırlı, termal kamera / termokupl kontrolü. **Açık:** keçeli 126 °C, docs/06 test kriterini (iç kabuk < 120 °C) modelin kötümser ucunda sağlamıyor; h/k/ε ölçülmeden O = 3 iyimser olabilir, termokupl ölçümünden sonra puan güncellenir |
| 10 | Kızakla sert/yanlış açılı iniş (kuyruk çarpması, sert zemin) | Kuyruk/gövde hasarı | 6 | 4 | 2 | 48 | Yalnız çim şerit, kuyruk tamponu (x = 1,90 m), değiştirilebilir aşınma plakası, flare pratiği |
| 12 | Dolly'den erken/geç ayrılma | Kalkışta kaza | 8 | 3 | 3 | 72 | L/W ≥ 1 mandalı, sabit 3° dolly açısı, elevator trim −4° (`params.GEAR`, docs/02 §6.1), bırakma ≥ 126 km/h, düz asfalt |
| 13 | Dutch roll / yön salınımı (düşük sönüm) | Ölçüm geçişinde kontrol zorluğu | 6 | 4 | 3 | 72 | Yaw damper zorunlu, rudder pilot girdisi ±0,5–1° |
| 14 | Hava alığı akış düzgünsüzlüğü / sınır tabaka yutma (yarı gömülü dudak) | İtki kaybı, kompresör stall'u | 6 | 2 | 4 | 48 | İter3: ofset/uzunluk 0,27, difüzör ≤ 4°. Yer testinde motor yüzü basınç taraması |
| 11 | Görsel takip kaybı | Kontrolsüz uçuş | 10 | 3 | 3 | 90 | Kontrast boya, gözcü, ölçüm hattı ≤ 250 m mesafede |
| 15 | Kanat flutter'ı (kesit CG'si kayarsa, kütle bütçesi aşılırsa) | Yapı kaybı | 10 | 2 | 5 | 100 | Kat planı 4/1 + 43 mm kaburga + web +1 kat korunmalı (iter5; kesit CG 0,428c, f_1T ≈ 295 Hz); kanat kütlesi 2,03 kg bütçesiyle tartılır; aileron balansı, boya/dolgu kanat arkasına yığılmamalı; GVT f_1T ≥ 230 Hz |
| 16 | Kısa, sert rüzgâr hamlesi (15 m/s, ~8 m) | Limit yükün aşılması (+19…+27 g / −11…−13 g), kanat kırılması | 10 | 2 | 6 | 120 | FC hamle yükünü sınırlayamıyor (docs/09 §4.2). Ölçüm turu yalnız sakin havada (türbülans < 3–4 m/s), uçuş kartında sınırlama; hamle alleviation ancak ≥ 200 Hz döngüyle |
| 17 | Uçuş kontrol (IMU/FC) veya yaw damper arızası | Yüksek hızda g aşımı (FC'siz tam çubuk 26–31 g), Dutch roll salınımı | 10 | 2 | 3 | 60 | Arıza algılama + otomatik gaz kısma (docs/09 §4.4), doğrudan modda elevator ±0,3°, dampersiz ölçüm turu yapılmaz, HIL testi |

En yüksek risk **flutter**dır. Bu sınıftaki model kayıplarının çoğu kontrol yüzeyi boşluğu veya yetersiz servodan kaynaklanır. Belge 04'teki gereksinimler pazarlıksız uygulanmalıdır.

## 7.4 Pilot gereksinimi
- Türbinli jette en az 50+ saat deneyim ve yüksek hızlı (> 400 km/h) jet deneyimi.
- Bir simülatörde (ör. RealFlight / PhoenixRC benzeri) yüksek hız profilleri prova edilmeli: ölçüm hattı hizalaması, yüksek hızda yumuşak dönüşler.
