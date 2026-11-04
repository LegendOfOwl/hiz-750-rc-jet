# Değişiklik Günlüğü

Sürümleme: `0.MAJOR_ITERASYON.PATCH`. 1.0.0 sürümü, prototip uçuş testinden sonra verilecek.

## [0.5.0] - 2026-11-04 · İter4: masa başı doğrulamaları
### Eklendi
- `cad/mass_properties.py`: CAD katılarından kütle, CG ve atalet tensörünü hesaplıyor (yakıt %100 / %25 / %0 ve params yakıtı için). Çıktı `cad/out/mass_properties.json`.
- `structures/fe_modal.py`: Kanat yarısı için 40 elemanlı 1D FE kirişi. Eğilme-burulma eşleşmesi, ilk 8 mod ve 4 modlu p-k flutter (Theodorsen şerit teorisi; Mach ve ok açısı düzeltmeli) hesaplanıyor. Goland kanadı ve üniform kirişle doğrulandı. Ayrıca duyarlılık analizi ve GVT kabul haritası üretiyor.
- `aero/flight_control.py` + [docs/09_ucus_kontrol.md](docs/09_ucus_kontrol.md): 4 hız × 3 yakıt durumu için doğrusal modeller. Kontrol yasaları: n_z komutlu pitch + g-limiter, yaw damper, p komutlu roll. Kararlılık payları, zaman simülasyonları (tam çubuk, hamle, rudder darbesi, damper arızası) ve kazanç tablosu (CSV).
- `performance/inlet_analysis.py`: Alığın toplam basınç kazanımı (sınır tabaka yutma + iç kayıplar) ve itkiye etkisi.
- `run_all.sh`: bütün zinciri doğru sırayla çalıştırıyor.
### Değişti
- Gövde kabuğu kütle kaleminin konumu, CAD alan merkezine göre 1,05 → 1,15 m. Bunun açtığı statik marj kaybı için 0,15 kg burun balastı eklendi (x 0,20 m). MTOW 17,16 kg.
- Gövde tankı 3,63 → 3,73 L. Kanat tankı için `wing_integral_usable_L_each = 0,57` L eklendi.
- Aileron servosu gereksinimi: ≤ 60 g ince tip (FE analizine göre flutter etkisi −%8).
- Doküman 02 ve 04 başlarındaki "iter3 kapanış" notları gövde metnine işlendi.
### Bulgular
- FE modal flutter 1307 km/h (pay %21). 2-DOF modeli (1465 km/h) %11 iyimserdi. Kritik mekanizma 3B–1T eşleşmesi.
- CAD'den hesaplanan Ixx, Roskam tahmininin %69'u; Ixz = 0,041 kg·m².
- g-limiter, boş yakıtta tam çubukta n'yi 10,05 g'de tutuyor (FC'siz 28 g). ζ_DR 0,31–0,44. GM ≥ 9,4 dB, PM ≥ 50°.
- Alık η_r = 0,970 @ 750 km/h. Eşdeğer k_ram 0,67, taban model kötümser kalıyor.
- 15 m/s kısa rüzgâr hamlesi 19–27 g üretiyor ve FC bunu azaltamıyor. Sakin hava sınırlaması korunuyor.
### Düzeltildi (PR #1 incelemesi)
- `cad/mass_properties.py`:
  - Kanat tankları artık kullanılabilir hacimle (0,57 L) dolduruluyor.
  - Tolerans bayrakları aynı yakıt kütlesinde karşılaştırılıyor.
  - "Motor yatağı" artık motor katısına değil, kendi bölgesine yerleştiriliyor.
  - Kanat bağlantısı ve bulkhead çerçeveleri artık çift sayılmıyor.
  - Çıktıya 4,0 kg yakıtın CG'si eklendi.
- `params.py`: yakıt CG'si 0,955 → 0,940 m (CAD, kullanılabilir hacimlerle). Kapasite yorumları güncellendi.
- `performance/inlet_analysis.py`:
  - Dudak gömülme derinliği sınır tabaka modeline girdi.
  - Kanal kesiti CAD raporundan, ofset params'tan okunuyor.
  - Motor debisi sizing ile aynı k_ram ve yoğunluk oranını kullanıyor.
- `structures/structures.py`:
  - `wing_section_model()` global yakıt kütlesini geri yüklüyor.
  - Kanat yakıtı için kullanılabilir hacim tercih ediliyor.
- `run_all.sh`:
  - Yorumlayıcıyı kendisi buluyor (`.venv`, `~/.hz750`, PATH).
  - Her scriptin çıktısını `logs/` altına yazıyor.
  - Hatada durup son satırları gösteriyor.

## [0.4.0] - 2026-11-04 · İterasyon 3
### Değişti
- Kanat alçak konuma alındı (z −0,035 → −0,080 m), dihedral −1° → +2° (DATCOM ile gövde-kanat girişim düzeltmesi yapıldı).
- Hava alığı yarı gömülü yapıldı (x 0,85 m, dudak merkezi z 88 mm), önüne 7° rampa eklendi. Kanal 330 mm'ye uzatıldı; S-kanal ofset/uzunluk oranı 0,50'den 0,267'ye düştü.
- Kanat tek parça oldu: kutu gövdenin içinden geçiyor, 4× M6 12.9 cıvata ve çerçevelerle (x 1,006 / 1,156) bağlanıyor.
- Kanat kabuğunun kat planı yüz başına 3/1 oldu (kiriş önü / arkası). Kesit ağırlık merkezi 0,45c'ye geldi; flutter hızı 1465 km/h.
- Flap tek yarıklıya çevrildi (cf 0,25, iniş açısı 35°). Elevator cf 0,28 → 0,22.
- Kızak uzatıldı (x 1,45 m'ye kadar), kuyruk tamponu ve kızak çerçeveleri eklendi. Kuyruk çarpma açısı 12,4°.
- Yakıt tankları yeniden düzenlendi: gövde 3,63 L, kanat kutusu ortası 0,27 L, kanat kökleri 2 × 0,715 L. Toplam 5,33 L iç hacim, karın tankı kaldırıldı. Yakıt CG'si 0,955 m.
- Dolly kalkış açısı α 3°, elevator trimi −4°.
### Düzeltildi
- İterasyon 2'nin flutter değerleri (1383 ve 1356 km/h) kesit ağırlık merkezi 0,42c varsayımıyla hesaplanmıştı. Ağırlık merkezi kalem kalem hesaplandığında 0,52c çıktı; buna göre gerçek değer ~1086 km/h, yani pay neredeyse sıfırdı.
- CAD'de gövde spline'ındaki örnekleme hatası giderildi (burunda x 400–800 mm arası).
### Eklendi
- Kütle kalemleri: kanat bağlantısı (0,15 kg), motor bölgesi ısı keçesi ve G10 plaka (0,05 kg).
- Rapor: [docs/08_sonuclar_cikarimlar.md](docs/08_sonuclar_cikarimlar.md), `requirements.txt`, `.gitignore`.

## [0.3.0] · İterasyon 2
### Değişti
- Kanat öne alındı (kök hücum kenarı 1,00 → 0,92 m). Arka kiriş 0,62c → 0,55c, motor x 1,25 → 1,18 m. Statik marj %40'tan %12–30 bandına indi.
- Geri çekilir iniş takımı kaldırıldı; yerine bırakılan kalkış arabası (dolly) ve gövde altı kızak geldi. MTOW 18,3 → 16,8 kg.
- Dikey kuyruk 0,050 → 0,060 m². Yatay kuyruk iki yarıya bölündü, birleştirici yoke egzozun üstünden geçiyor.
- Negatif yük limiti −6 → −8 g.
- Yakıt gövde, karın ve kanat kökü tanklarına bölündü; toplam 5,2 L.
### Düzeltildi
- İterasyon 1'deki CAD çakışmalarının hepsi giderildi: motor ↔ kiriş, kanal ↔ kanat kutusu, yatay kuyruk ↔ egzoz.

## [0.2.0] · İterasyon 1 (ilk tam paket)
### Eklendi
- Tek veri kaynağı olarak `params.py`.
- Paralel olarak hazırlanan: CadQuery ile parametrik CAD (`cad/`), AeroSandbox ile aerodinamik ve stabilite analizi (`aero/`), yapı/flutter/servo analizi (`structures/`).
- Görev profili, kütle/CG ve elektrik bütçesi (`performance/`). Dokümanlar 02–07.
### Bulunan sorunlar
- Statik marj %40'tı. Yakıt hacmi yetersizdi. Beş geometri çakışması vardı. Ana teker kanada sığmıyordu.
- Bunların hepsi iterasyon 2'de çözüldü.

## [0.1.0] · Kavramsal boyutlandırma
### Eklendi
- `sizing.py`: ISA atmosfer, bileşen bazlı sürükleme, Korn denklemiyle dalga sürüklemesi, türbin itki modeli ve Vmax hesabı. Ayrıca motor ve kanat alanı için trade study, duyarlılık analizi.
- Motor seçimi: P300-PRO hedefi ancak sınırda karşılıyor (754 km/h), bu yüzden P400-PRO seçildi.
