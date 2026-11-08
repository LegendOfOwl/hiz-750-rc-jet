# Değişiklik Günlüğü

Sürümleme: `0.MAJOR_ITERASYON.PATCH`. 1.0.0 sürümü, prototip uçuş testinden sonra verilecek.

## [0.6.0] - 2026-11-06 · İter5 yüksek doğruluk doğrulama paketi
### Eklendi
- `validation/`: sabit sürümlü host kurulum adımları, araç yoklaması, tek vaka/üç ağ runner, kaynak/executable hash'leri, Richardson/GCI ve karşılaştırma raporları.
- `cfd/`: SU2 sıkıştırılabilir SA/SST için RAE2822, düz levha ve HIZ profil koşuları; tam uçak/S-kanal için incelenmiş ağ girişi, gmsh 3B ön ağ ve recovery/DC60 postprocess.
- `fem/`: gmsh S8R konsol benchmarkı, kat planını okuyan taslak kompozit kanat, açık malzeme varsayımları, statik/modal runner ve lokal tabaka CSV'sinden Tsai–Wu.
- `thermal/`: CalculiX 1B iletim+taşınım benchmarkı ve ölçülmemiş h/k/emissiviteyle koşullu motor–keçe–kabuk senaryoları.
- `docs/10_yuksek_dogruluk_dogrulama.md`: bekleyen hata tabloları, LES/DES maliyeti, belirsizlik bütçesi ve tasarım önerileri.
- `fem/clt.py`, `fem/coupon.py`, `fem/wing_shell.py` (yeniden yazıldı), `fem/wing_post.py`, `fem/wing_review.py`, `fem/run_wing_study.py`, `fem/wing_compare.py`: bağımsız CLT referansı, 5 laminatlık kupon benchmarkı, S8R kompozit kanat kabuk modeli (dolu/boş tank, üç ağ, otomatik inceleme) ve kiriş teorisi çapraz kontrolü; sonuçlar `fem/RESULTS_iter5.md`.
- `fem/results/stiffening/`: 21 seçenekli (orta ağ) ve 4 seçenekli (ince ağ) kanat rijitleştirme çalışması.
- Motor bölgesi ısı keçesi (2 mm) ve G10 plaka kütle bütçesinde (0,05 kg); `docs/06`, `docs/07` (FMEA 9) ve termokupl kriteri güncel.
### Değişti
- `params.py` `WING` önceki iter5 çalışmasında `skin_plies` (3, 1) → **(4, 1)**, `rib_pitch = 0,043 m` ve `web_extra_plies = 1` olarak güncellendi. Düzeltilmiş kabuk FEM sonucu f_1T 295,2 Hz dolu / 302,2 Hz boş, kesit CG 0,428c.
- `MASS_ITEMS` kanat kalemi 1,75 → **2,03 kg** (kabuk 4/1 kat + kiriş + 43 mm kaburga); düzeltilmiş kabuk FEM toplam ek kütlesi +0,285 kg. **MTOW 17,16 → 17,44 kg**, yakıtsız 13,44 kg; statik marj tam yakıtta %32,8, yakıtsız %13,0 MAC (önceki `run_all.sh` kaydı).
- Flutter tasarım değeri **≈1267 km/h dolu / 1271 km/h boş** (kabuk-FEM frekans ölçeklemesi, sabit iter4 referansı); 1080 km/h gereksinime pay %17. 1350 km/h (×1,25 model payı) sağlanmıyor.
### Bulgular (FEM)
- CLT kupon benchmarkı **BENCHMARK_ACCEPTED** (5 laminat, 3 ağ, en büyük hata %1,12 < %2). Kompozit kanat **REVIEW_REQUIRED** (malzeme sabitleri varsayım).
- Taban 3/1 kabukta f_1T 272,5 Hz (1D 305,7 Hz'in %89'u): flutter ≈1185 km/h. Kaburgalar f_1T'yi belirliyor (kaburgasız 198-207 Hz). 18 g uç sehim 47,7 mm, Tsai-Wu R_min 3,66.
- Rijitleştirmede hiçbir seçenek 316 Hz (1350 km/h) hedefine ulaşmadı; ilk taramada kat eklemek kütleyle doydu (6/1 → 281 Hz). Düzeltilmiş modelde seçilen s41r043w1, 4/1 + 43 mm kaburga + web +1 kat ile f_1T 295,2 Hz (dolu) / 302,2 Hz (boş), Tsai-Wu R 4,16 (kök hariç; kök dahil 1,97, indirgemeli 1,07, kök bağlantısı iter6'da), uç sehim 43,0 mm verdi.
- 1D `fe_modal`'ın 1813 km/h sonucu bir kod hatasıydı (ilk 4 mod alınıyordu, 1T beşinci mod); düzeltildi, 1D dolu 1452 / boş 1544 km/h. **Kabuk mod şekilleriyle p-k** (`fem/shell_flutter.py`): seçilen tasarım dolu 1326 / boş 1324 km/h (tahmin; kumanda yüzeyi, kuyruk ve gövde bağlaşımı yok). Tasarım değeri ihtiyatlı 1267 km/h kalır (Grup 2 kararı). GVT kabul kriteri f_1T ≥ 230 Hz yeni modelle yeniden türetilecek.
- CalculiX 2.20 bulguları: tek iş parçacığı, SPOOLES, MASS yerine NSM, kök 1-3 ankastre.
### Doğrulama durumu
- Düz levha SA üç ağda **BENCHMARK_ACCEPTED**. İnce Cf 0,0028613, Schlichting farkı −%4,74, p 0,434, ince GCI %1,82 (p<.5 için sınırlandırılmış p, Fs=3; eski değer %0,88). MG3 ıraksamasından sonra MG0 + CFL_ADAPT ve proje kapısıyla uyumlu durma kuralı kullanıldı.
- RAE2822 **PENDING**. Yeni tek bloklu C-ağı 100c uzak alan ve 0,707 minimum köşe sinüsüne sahip. MG3 ıraksadı, kaba MG0 ıraksamadı fakat iz bölgesi residual'ları nedeniyle kapıyı geçmedi. Ara CL 0,730 (−%1,8), CD 0,01345 (+%5,9), Cp RMSE 0,092. Resmi SU2 ağıyla çözücü/cfg kabul edildi, deneysel Cp kabulü açık.
- Önceki host koşularında konsol ve 1B termal üç ağda kabul aldı; koşullu motor termal sonuçları kaydedildi. STALE kapsamı daraltıldı; `thermal_1d`, konsol ve kupon yeniden koşuldu, sayılar aynı, **BENCHMARK_ACCEPTED**. RAE2822 iz kesiti ağı düzeltildi, kaba ağ kapıyı geçti (Cp RMSE 0,098 > 0,08); üç ağ PENDING.
- Gerçek koşularla CalculiX sayı alanı uzunluğu, Lednicer profil sırası, SU2 çıktı sütunları ve düz levha köşe ağı düzeltildi. Resmi SU2 düz levha ayar/ağ kontrolü ayrıca kaydediliyor.
- B/C sınır katmanlı temiz akış hacmi/ağı ve D imalat detayları host'ta incelenmeli. 3B tetra/kompozit kanat ön modelleri DRAFT. CLT kupon benchmarkı iter5'te kabul edildi; kompozit kanat REVIEW_REQUIRED (imalat detayları ve malzeme verisi eksik).
- İter5'te params bilerek değişti ve analiz çıktıları yeniden üretildi. Karşılaştırma baseline'ı `v0.5.0` Git içeriklerine sabitlendi, güncel dosya hash'leri ayrıca listelendi.
### Düzeltildi
- `validation/convergence.py` yuvarlama kararı için iki farkın da küçük olmasını gerektiriyor. Tek küçük fark `PLATEAU_UNRESOLVED` döndürüyor ve `study.py` kupon yayılım istisnası dahil kabul vermiyor. Regresyon testleri eklendi.
- `cfd/cases.py` 3B yunuslama momentini CMy'den okuyor. 2B CMz ve mevcut Cm işaret dönüşümü korundu, eksenleri ayıran sentetik test eklendi.
- `validation/check_artifacts.cjs` ve `validation/report.py` tarihsel hash'leri `git show v0.5.0:<yol>` byte'larından alıyor, güncel analiz dosyalarını ayrı doğruluyor.
### İnceleme düzeltmeleri (2026-11-08, grup 1 zincir/doküman)
- `sizing.py` kütle ve geometriyi `params.py`'den okuyor (MTOW 17,01 → 17,44 kg; kanat yüklemesi 41,5 kg/m², T/W 2,48). V_D ve flutter gereksinimi params'tan yazılıyor (eski çıktı 1010 / 1212 km/h idi, params 900 / 1080). İniş stall kütlesi %25 yakıt (14,44 kg).
- `performance/mission.py`: kararlı tırmanma `T − D = W sin γ` ile (eski `(T−D)V/W` 490 km/h'te 183 m/s düşey hız veriyordu, toplam hızdan büyük); 144–603 km/h arasında T − D ≥ W. Dolly kalkışında yer koşusu CL'si mandal koşuluyla (L/W = 1 @ 1,2 Vs) tutarlı. Elektrik bütçesinden iniş takımı servo/retract kalemleri çıkarıldı (ort 2,3 A, tepe ~20 A).
- `aero/aero_analysis.py`: sizing sürükleme karşılaştırması sabit CD0 0,0183 yerine sizing modelinden (750 km/h'te CD0 0,0195, 212 N).
- `tools/inceleme_paketi_olustur.py`: `.claude` taranmıyor, `reviews/` raporları `01_Raporlar/Incelemeler`'e, 3 görünüş/iç yerleşim PNG'leri `04_Teknik_Cizimler`'e.
- Docs 02/03/05/06/07/08/09 ve README iter5 kütlesiyle (17,44 kg) güncellendi; doküman 09 kazanç, pay ve simülasyon tabloları `run_all.sh` çıktısından yeniden yazıldı. Doküman 06'da kanat kat planı 4/1 + 43 mm kaburga, yük testi ifadesi (nihai = %150 limit), GVT kabul ölçütü f_1T ≥ 230 Hz. Doküman 07 FMEA'ya hamle ve FC arızası eklendi, dolly açısı 3°/−4° düzeltildi. Doküman 09'da pitot fark basıncının q̄ olmadığı (M 0,61'de %10) yazıldı.

### Açık kalanlar
- Kanat tankı kullanılabilir hacmi 43 mm kaburgalarla ~5,0 L'ye inebilir (params 0,57 L/yarı, fe_modal 0,547); termal model keçeyle 126 °C, test kriteri < 120 °C.
- RAE2822 orta/ince ağ koşuları ve üç ağ kabulü (Cp ölçütü sabitlenecek, ön kenar noktası dışlanmayacak), SST ve profil taraması, GVT ve fiziksel testler.
- 316 Hz hedefi ve 1350 km/h model payı sağlanmadı. Kanat REVIEW_REQUIRED, malzeme ve termal parametre varsayımları sürüyor.
- 2026-11-08 Grup 1 incelemesinden sonra 33 regresyon testi ve `check_artifacts` PASS; düz levha, konsol, kupon ve thermal_1d güncel kodla yeniden koşuldu.
- **Uçuşa hazır değil.** Uçuş öncesi engeller (Grup 2): kuyruk/gövde bağlaşık flutter ve GVT, motor bölgesi termali (126 °C > 120 °C), FC filtreli faz payı (≈41° < 45°) ve HIL, kök sandviç kesme kıvrılması (pay 1,2–1,5), tank kullanılabilir hacmi ve dinamik görev yakıtı. Kararlar: [reviews/grup2_karar.md](reviews/grup2_karar.md).

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
