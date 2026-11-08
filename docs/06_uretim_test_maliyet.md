# 06 · Üretim, Test Planı ve Malzeme Listesi

## 6.1 Üretim yöntemi

| Parça | Yöntem | Malzeme |
|---|---|---|
| Kalıp masterları (plug) | CNC freze (MDF/tooling board) veya FDM baskı + dolgu, astar, 1200 kum zımpara, cila | STEP dosyaları `cad/out/` klasöründen |
| Dişi kalıplar | Kalıp jelkotu + cam/epoksi kalıp laminatı, 2 parça (sağ/sol gövde, üst/alt kanat) | Kalıp epoksisi (Tg > 120 °C) |
| Gövde kabuğu | Vakum torbalı ıslak laminasyon veya prepreg + fırın kürü (120 °C) | 160 g/m² karbon twill ±45 + 0/90; motor bölgesinde ek kat + ısı kalkanı |
| Kanat (tek parça) | Sandviç kabuk + içine yapıştırılmış kutu kiriş, kalıpta kapama; kökte entegre tank bölmeleri; **43 mm aralıklı ara kaburgalar** | Kabuk (iter5): **ön kirişin önünde 4 kat, arkasında 1 kat ±45 karbon / yüz** (kesit CG'si 0,428c, flutter için kritik). UD kiriş kapakları, ±45 kiriş gövdesi **+1 ek ±45 kat (web)**, 2 mm Rohacell. Kanat kütle bütçesi 2,03 kg (`params.MASS_ITEMS`); tartıda aşılırsa flutter yeniden değerlendirilir |
| Kontrol yüzeyleri | Kabukla birlikte kalıplanıp kesilir; iç Kevlar menteşe veya pimli menteşe | Kütle dengesi için kurşun/tungsten hücum kenarında |
| Kuyruklar | Kanatla aynı yöntem, daha ince (%6) | |
| Kanat bağlantısı | Kanat kutusu gövde içinden geçer; x 1,006 / 1,156 m'deki çerçevelere 4× M6 12.9 civata + ön pimler (x 0,94) | 25 mm derinlikte, 3,1 mm karbon çerçeveler; gövde alt kesiğine 2 × 30 mm² UD takviye |
| Motor bölgesi alt kabuğu | Isı keçesi + G10/çelik aşınma plakası (kızak) | Reçine Tg ≥ 150 °C |
| Motor yatağı | CNC 6061/7075 Al kelepçe + karbon ön bulkhead | |
| Egzoz borusu | Hazır bypass boru (Ø105) veya Ti levhadan kaynak | |

Yüzey kalitesi kritik: duyarlılık analizinde laminer akış etkisi +30 km/h. Kalıp yüzeyi aynalı olmalı. Montaj sonrası tüm ek yerleri dolgu ve zımpara ile pürüzsüz yapılmalı; menteşe boşlukları bant ile kapatılmalı.

## 6.2 Malzeme ve maliyet listesi (tahmini, 2026 fiyatları)

| Kalem | Adet | Tahmini fiyat |
|---|---|---|
| JetCat P400-PRO (ECU, GSU, pompa dahil set) | 1 | ~€5.000–6.000 *(doğrulanmadı)* |
| Bypass egzoz borusu | 1 | ~€250 |
| HV servo 45 kg·cm (metal dişli, boşluksuz) + 1× 60 kg·cm rudder | 7 | ~€150 × 7 = €1.050 |
| Kalkış arabası (dolly) + bırakma mandalı, kızak + aşınma plakası | 1 set | ~€250 |
| Kumanda + 2 alıcı + telemetri sensörleri | 1 | ~€1.500 |
| Güç dağıtıcı (yedekli) + aküler | 1 | ~€500 |
| GNSS logger + pitot/hava hızı sensörü + gyro | 1 | ~€500 |
| Karbon kumaş, UD, Rohacell, epoksi, vakum malzemesi | — | ~€1.500 |
| Kalıp malzemesi + CNC/baskı | — | ~€1.500–3.000 |
| Yakıt sistemi (tank, hopper, valf, filtre, hatlar) | — | ~€200 |
| Yer ekipmanı (yangın söndürücü, yakıt istasyonu, radar tabancası) | — | ~€500 |
| **Toplam** | | **~€12.500–15.500** |

## 6.3 Yer testleri
1. **Malzeme numunesi:** Her laminasyon partisinden 3 adet çekme/kesme numunesi.
2. **Kanat yük testi:** Ters çevrilmiş kanata Schrenk dağılımına göre kum torbası. Önce %100 limit yük (12 g × yarı-kanat payı), sonra **nihai yük (limit yükün %150'si, 18 g)**. Uç sehimi ölçülür ve analizle karşılaştırılır (kabuk FEM, 18 g: 43,0 mm). Nihai yüke çıkılan test kanadı uçuşta kullanılmaz; uçacak kanat için kanıt testi limit yükte bırakılır.
3. **Burulma rijitliği testi:** Uca moment uygulanır, dönme açısı ölçülür. Sonuç GJ'dir ve flutter modelini günceller.
4. **GVT (yer titreşim testi):** Uçak lastik ipe asılır, darbe çekici + ivmeölçer ile ölçülür. 1. burulma 250–300 Hz bandında beklendiği için örnekleme ≥ 2 kHz olmalı (telefon ivmeölçeri bu bant için yetersiz). Kanat 1. eğilme ve 1. burulma frekansları ile kontrol yüzeyi dönme frekansları belirlenir; dolu ve boş tankla ayrı ölçülür. Ölçülen frekanslar flutter analizine girilir. **Kabul: f_1T ≥ 230 Hz** (docs/04; kabuk FEM tahmini 295 Hz dolu / 302 Hz boş) ve burulma/eğilme frekans oranı ≥ 2,5. GVT yapılmadan 600 km/h üstüne çıkılmaz.
5. **Kontrol yüzeyi boşluk testi:** Servo kilitliyken yüzey ucuna 1 N kuvvet uygulanır; sapma ≤ 0,1° olmalı.
6. **Motor yer çalıştırması:** Tutucu bağlantıyla tam gaz 2 dk; 2 mm ısı keçesi takılı olmalı. Motorun en dar aralık bölgesine (x ≈ 1,2–1,3 m, aralık 5,97 mm) termokupl konur. Kabuk iç yüzeyi **< 120 °C** olmalı; bu sınır Tg 150 °C'ye 30 °C pay bırakır. Ölçülen değer, termal modelin (docs/10) varsayılan taşınım katsayılarını kalibre eder. **Not (iter5 inceleme):** Koşullu termal modelin en kötü yer senaryosu (bypass yok, h_dış 10 W/m²K, kararlı hal) 2 mm keçeyle bile **126,1 °C** veriyor; yani bu kriter modelin kötümser ucunda sağlanmıyor. 2 dk'lık koşu kararlı hale ulaşmayabilir ve h/k/ε ölçülmedi; kriter aşılırsa koşu durdurulur ve keçe kalınlığı, bypass soğutma debisi veya yüksek Tg'li reçine kararı yeniden verilir (açık tasarım kararı, docs/07 FMEA 9). Yakıt sistemi negatif g simülasyonu (uçak ters çevrilerek) yapılır.
7. **Fail-safe ve menzil testi:** Motor çalışırken kumanda menzil testi; sinyal kesilince fail-safe davranışı doğrulanır.

## 6.4 Uçuş zarfı genişletme planı

| Faz | Hız limiti (ECU gaz sınırı) | Amaç | Geçiş kriteri |
|---|---|---|---|
| F1 | 350 km/h | İlk uçuş, trim, CG doğrulama, inişler | 3 temiz sorti; trim değerleri analizle ±1° uyumlu |
| F2 | 500 km/h | Gyro kazanç ayarı, hız modu testi | Titreşim/buzz yok (kayıtlı IMU spektrumu temiz) |
| F3 | 600 km/h | Yakıt tüketim kalibrasyonu, termal kontrol | |
| F4 | 680 km/h | Yüksek q'da kontrol hassasiyeti | |
| F5 | 750 km/h | Ölçüm hattı denemesi | |
| F6 | 780–800 km/h | Rekor denemesi | |

- Her faz arasında kontrol yüzeyi boşluk testi tekrarlanır ve IMU titreşim kaydı incelenir.
- **Herhangi bir buzz, titreşim veya ani trim değişikliğinde** bir önceki faza dönülür.
- Hız artışları **+50–70 km/h** adımlarla yapılır. Flutter, hızla birlikte aniden başlar; güvenli payı yalnızca adım adım genişletme verir.

## 6.5 Ölçüm yöntemi (rekor denemesi)
- Guinness/FAI tarzı: 200 m'lik ölçüm hattı, iki yönde geçiş, ortalama hız. Rüzgar etkisi bu şekilde iptal edilir.
- Zaman kapısı olarak iki adet yüksek hızlı kamera (≥ 240 fps) kullanılır; hatta ayrıca radar ve GNSS logger kaydı tutulur.
- Bağımsız gözlemci ve video kaydı bulunur. Guinness başvurusu önceden yapılır, kanıt gereksinimleri Guinness'ten alınır.
