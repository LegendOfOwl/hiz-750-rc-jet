# Grup 1 inceleme: sistem zinciri tutarlılığı ve dokümanlar

**Tarih:** 2026-11-08 · **Dal:** `iter5/yuksek-dogruluk` (taban `8e3c14c`, kaydedilmemiş değişikliklerle) · **İnceleyen:** grup 1 zincir/doküman ajanı
**Kapsam:** `params.py` (yalnız kesin hata), `sizing.py`, `aero/`, `performance/`, `cad/`, `tools/`, docs 02, 03, 05–09, README, CHANGELOG, BASARIM_AGACI. Ek iş: `reviews/grup1_codex_disiplinlerarasi.md` maddelerinin bu alana düşenleri.

**Genel doğrulama:**
- `PY=C:/Users/Urungu/.hz750/Scripts/python.exe bash run_all.sh` → `tamam` (10 script, çıkış 0). Sonra `performance/mission.py` ve `aero/aero_analysis.py` düzeltme sonrası tek başına yeniden koşuldu (çıkış 0), loglar güncel.
- `python -m unittest validation.test_validation validation.test_cfd_mesh` → **33 test OK**.
- Önceki loglarla fark: `aero_flight_control`, `cad_mass_properties`, `performance_inlet_analysis`, `structures_structures` birebir aynı (params değişmedi). `sizing`, `performance_mission`, `aero_aero_analysis` yalnız düzeltilen satırlarda değişti. `structures_fe_modal` değişti: başka bir ajanın `structures/fe_modal.py` değişikliğinden (1D V_F 1813 → 1452 km/h); benim alanım değil, aşağıda not edildi.

## 1. Soru: sizing params kütlesine bağlanmalı mı?

**Evet, bağlandı.** `sizing.py` sabit `m_struct = 6.76` ile MTOW'u 17,01 kg (iter3) veriyordu; kanat +0,28 kg sonrası 0,43 kg eksikti. Vmax'a etkisi yok denecek kadar küçük (CL ≈ 0,011, CDi ihmal edilebilir: 878 km/h aynı), ama kanat yüklemesi, T/W, stall, kök momenti ve `inlet_analysis`/`mission`'ın kullandığı `SZ.DESIGN` kütlesi yanlıştı ve "tek veri kaynağı" kuralını çiğniyordu. Kütle ve geometri artık `params`'tan okunuyor.

## 2. Düzeltilenler

| # | Dosya:satır | Sorun | Düzeltme | Doğrulama |
|---|---|---|---|---|
| D1 | `sizing.py:22-27, 46-69` | Kütle (17,01 kg) ve geometri sabit yazılı, params'tan kopuk | `import params as PRM`; `m_struct` = params yakıtsız − motor − sistemler, `m_fuel`, S, AR, taper, ok, t/c, gövde, kuyruklar params'tan | `logs/sizing.log`: MTOW 17,44, yakıtsız 13,44, W/S 41,5, T/W 2,48, Vmax 878 km/h |
| D2 | `sizing.py:232-235` | "VD = 1,15·Vmax = 1010, flutter 1,2·VD = 1212 km/h" yazıyordu; params ve tüm dokümanlar V_D 900, gereksinim 1080 km/h | `PRM.V_D`, `PRM.V_FLUTTER_REQ` basılıyor (1,15·Vmax bilgi olarak) | log: "VD=900 km/h … 1.2*VD=1080 km/h" |
| D3 | `sizing.py:203-204, 215` | Stall kütlesi `1,15·m_dry` ("boş + %15 yakıt" etiketiyle uyumsuz) | İniş kütlesi aero/mission ile aynı: yakıtsız + %25 yakıt (14,44 kg) | log: Vs 79 km/h |
| D4 | `sizing.py:297` | 3 görünüş çiziminde kanat kökü `0,42·L` | `params.WING["x_root_le"]` | `out/uc_gorunus.png` yeniden üretildi |
| D5 | `performance/mission.py` `climb_curve` | **Codex #17 doğrulandı.** `ROC = (T−D)V/W` → 490 km/h'te (136 m/s) 183 m/s düşey hız, fiziksel olarak imkânsız (T/W > 1 bölgesi) | Kararlı tırmanış: `T − D(L = W cos γ) = W sin γ`, `ROC = V sin γ`, sin γ ≤ 1; T−D ≥ W aralığı ayrıca raporlanıyor | log: "168 m/s @ 610 km/h, γ 83°; 144–603 km/h arasında T−D ≥ W". docs/05 güncellendi |
| D6 | `performance/mission.py` `takeoff` | **Codex #16 doğrulandı.** `CL_g = 0,35`, `V_lof = 1,2 Vs` (CLmax 0,80) → bırakmada L/W = 0,63; mandal koşulu L/W ≥ 1 ve aero analizi (126 km/h'te CL 0,54, dolly α ≈ 2° < params 3°) ile çelişik | `CL_g` varsayılanı `CLmax_to/1,2²` (bırakmada L = W) | log: yer koşusu 33 m (1,9 s), 140 m; değişim küçük (sürtünme payı) |
| D7 | `performance/mission.py` `POWER_ITEMS` | Elektrik bütçesinde "burun tekeri dümen servosu" ve "elektrikli retract + fren" vardı; iter2'den beri iniş takımı yok | Kalemler çıkarıldı | log: ort 2,30 A, tepe 19,6 A (eski 2,50 / 26,6) |
| D8 | `aero/aero_analysis.py:416-420` | sizing karşılaştırması sabit `CD0 0,0183 → 198 N`; sizing modeli 750 km/h'te CD0 0,0195, 212 N veriyor | Değer `sizing.drag()`'dan hesaplanıyor | log: "sizing.py CD0=0.0195 → D=212 N; AeroBuildup farkı %−27" |
| D9 | `tools/inceleme_paketi_olustur.py` | `.claude` (yerel ajan ayarları) taranıyordu; `reviews/` eşlemesi yoktu (99_Diger); 3 görünüş/iç yerleşim PNG'leri CAD model klasörüne düşüyordu, DXF/PDF eşleri teknik çizimde | `.claude` SKIP'e; `reviews/*` → `01_Raporlar/Incelemeler`; `cad` 3view/inboard PNG → `04_Teknik_Cizimler`; `tools/README.md` güncellendi | `--dry-run`: 687 dosya, 3view/inboard PNG → 04, 99_Diger yalnız `requirements.txt` |
| D10 | `docs/09_ucus_kontrol.md` §1.1, §1.4, §3, §4.1–4.4, §5.2 | **Bütün tablolar iter4 kütlesiyle (17,16 kg, Ixx 0,387) kalmıştı**; log/CSV 17,44 kg ile üretilmiş. Ör. kazanç Kff 750/%100 0,207 → 0,222, Kr 0,0097 → 0,0111; FC'siz tepe 28,4 → 26,3 g; kritik nokta 800/%100 yerine 750/%100 yaw PM 49,9° | Tablolar `fc_sonuclar.json` ve `fc_kazanc_tablosu.csv`'den yeniden yazıldı; metindeki gradyan (0,074 → 0,081 °/g), ζ aralıkları, Kr formülü, hamle negatif tepe (−11…−13 g < −8 g limit) düzeltildi | `logs/aero_flight_control.log` ile satır satır karşılaştırıldı |
| D11 | `docs/09` §5.2 kural 1 | **Codex #11 doğrulandı.** "q̄ = ½ρV² (pitot farkı doğrudan)". 750 km/h, 300 m ISA: M 0,614, q̄ 25,83 kPa, q_c 28,36 kPa (%9,8 fark) | Sıkıştırılabilir Mach dönüşümü ve q̄ = (γ/2)pM² yazıldı | bağımsız aritmetik (ISA + izentropik bağıntı) |
| D12 | `docs/02` | MTOW 17,16, SM %31,7/12,5, yakıt CG 0,955, trim, flap Vs, dolly 125 km/h, flare, kontrol otoritesi 7,5/24,6 g, sizing 198 N, yanal mod tablosu eski | Hepsi `logs/aero_aero_analysis.log` değerleriyle güncellendi (SM %32,8/19,0/13,0, 7,1/23,2 g, 126 km/h, 212 N …) | log karşılaştırması |
| D13 | `docs/05` | MTOW 17,0/13,0, W/S 40,5, T/W 2,55, kalkış 32/137 m, iniş 14,0 kg, tırmanma 188 m/s, SM %31,9/12,6, η_r tablosu (iter4 kodu), elektrik 2,5/27 A, tank 5,33 L, yaw damper K 0,006 (gecikmesiz) | Loglardan güncellendi; tank hacmi açık maddesi (bkz. Ö1) eklendi | log karşılaştırması |
| D14 | `docs/03` kütle bölümü | Yalnız iter4 öncesi tablo (17,01 kg, Δx +10 mm) vardı | İter5 güncel tablo eklendi (17,44 kg, Ixx 0,405, Δx ≤ 1,4 mm); eski tablolar "tarihsel" etiketli | `logs/cad_mass_properties.log` |
| D15 | `docs/06` §6.1, §6.3 | Kanat "3/1 kat, kesit CG 0,45c" (eski); yük testi "nihai yükün %150'si" (yanlış: nihai = %150 limit); GVT'de kabul ölçütü yok, "telefon ivmeölçeri yeterli" (f_1T ~295 Hz için yetersiz) | 4/1 + 43 mm kaburga + web +1, 0,428c, 2,03 kg; nihai = %150 limit (18 g, ayrı test kanadı); GVT f_1T ≥ 230 Hz, ≥ 2 kHz örnekleme; termal kriter notu | — |
| D16 | `docs/07` | MTOW 18,3 kg; T/W 2,4; FMEA 12 dolly 6°/−6° (params 3°/−4°); FMEA 15 "3/1 korunmalı"; satır sırası; hamle ve FC arızası FMEA'da yok | Düzeltildi; FMEA 16 (kısa hamle, +19…+27 / −11…−13 g) ve 17 (FC/IMU/damper arızası) eklendi; FMEA 9'a termal açık notu | — |
| D17 | `docs/08` | v0.5.0 sayıları (MTOW 17,16, SM %12,6–31,9, flutter 1307, kanat 1,74 kg, yakıt 5,33 L), iter5 sütunu ve yol haritası yok | Özet, iterasyon tablosu (v0.6 sütunu), doğrulama tablosu (CFD, termal, bütün uçak flutter, hava verisi) ve §5 yol haritası yeniden yazıldı | — |
| D18 | `README.md` | Atalet 0,378/2,79/3,08 (eski), alık Vmax 897 (log 898), temas 87–95 (log 88–97), ζ_DR 0,31–0,44 (log 0,33–0,44), PM ≥ 50° (log 49,9°), "motorla kabuk arası 8,5 mm" (CAD min 5,97 mm) | Güncellendi | log karşılaştırması |
| D19 | `CHANGELOG.md`, `BASARIM_AGACI.md` | Ağaç §2'de MTOW 17,16 / SM %12,5 | Güncellendi; CHANGELOG [0.6.0] altına inceleme düzeltmeleri ve açık maddeler, ağaca günlük kaydı | — |

## 3. Kontrol listesi sonuçları (brief maddeleri)

1. **params sayıları:** MTOW 17,44 kg, CG 1,148 (params) / 1,147 (CAD), SM %32,8–13,0, CAD atalet 0,405/2,794/3,110/0,043 kg·m² artık loglarda ve 02/03/05/08/09/README'de aynı. `docs/04` (benim değil) §0-§14 "params, iter3 kapanış: MTOW 17,01 kg, yakıt CG 0,955" satırları tarihsel olarak duruyor; başlıkta iter5 notu var, sorun değil.
2. **Kanat +0,285 kg yan etkileri:** CAD kütle özellikleri ✅ (zincir 2026-11-06'da koşulmuştu, bugün tekrar aynı sonuç), atalet ✅, FC kazançları ✅ (log/CSV doğru, **doküman 09 eskiydi → D10**), g-limiter ✅ 10,03/10,05 g, kalkış/dolly ✅ (126 km/h; mission CL tutarsızlığı → D6), yakıt bütçesi ✅ (kütle bağımsız; **tank hacmi kaburgalardan etkileniyor → Ö1**), Vmax ✅ 878 km/h (kütleye duyarsız). **sizing eskiydi → D1.**
3. **Doküman–log tutarsızlıkları:** D10–D19.
4. **Termal karar:** Keçe zorunluluğu FMEA 9 ve test planında var, ama **kriter ile model çelişiyor**: test kriteri iç kabuk < 120 °C; koşullu modelin en kötü yer senaryosu 2 mm keçeyle 126,1 °C. Doküman 06 ve 07'ye not eklendi; karar açık (Ö2).
5. **İnceleme paketi:** eşleme kuralları doğru çalışıyor (dry-run 687 dosya); D9'daki üç iyileştirme yapıldı. Paket yeniden üretilmedi.
6. **Yol haritası:** §5 ve docs/08 §5.

## 4. Öneriler

| # | Önem | Öneri | Gerekçe | Tahmini iş |
|---|---|---|---|---|
| Ö1 | **P1** | Kanat tankı kullanılabilir hacmini 43 mm kaburgalarla gerçek iç geometriden yeniden hesapla; `params.FUEL["tanks"]["wing_integral_usable_L_each"]` (0,57) ve yakıt CG'sini güncelle; gerekirse yakıt yükünü veya gövde tankını gözden geçir | **Codex #9 doğrulandı:** `structures/out/fe_sonuclar.json` V_usable 0,547 L/yarı (params 0,57); `tank_volume()` yalnız 1 orta kaburga düşüyor, tank açıklığında (~355 mm) ~8 kaburga var → kabaca −0,05 L/yarı daha. Toplam ~5,0 L = 4,0 kg yükle sıfır pay. params'ı değiştirmedim: doğru değer kaburga delik oranına bağlı, 0,54 de eksik sayım; bu bir tasarım kararı (FEM/CAD sahibi) | 0,5 gün + zincir koşusu |
| Ö2 | **P1** | Termal: keçe kalınlığı/bypass soğutma/yüksek Tg reçine kararı, ölçümden önce 120 °C kriterinin model ile uyumu | 2 mm keçe en kötü senaryoda 126 °C; keçe hava aralığını 3,97 mm'ye indiriyor ve soğutma debisini azaltabilir (model sabit h). Ayrıca docs/06 gövde kabuğu "prepreg + 120 °C kür": bu kür tipik olarak Tg ≈ 120–135 °C verir, motor bölgesi için Tg ≥ 150 °C post-cure ayrıca şart koşulmalı. Isı keçesi + G10 kalemi 0,05 kg: 2 mm seramik keçe (~0,155 m², ~130 kg/m³) tek başına ~0,04 kg, G10 plaka ile toplam ~0,1 kg olabilir | 1 gün |
| Ö3 | P1 | Kontrol paylarına sensör/anti-alias/notch filtreleri ve veri gecikmesi eklenip yeniden çözülsün (Codex #2'ye katılıyorum) | 750/%100 yaw PM 49,9°; 25 Hz birinci derece filtre ~9° → ~41° < 45° hedef. Doküman 09 §6 "karşılar" diyor, sayısal olarak doğru değil | 1 gün |
| Ö4 | P2 | `flight_control.py` optimizasyon sonuçlarındaki sayısal uçlar: 800/%0 Kp_p = 0,0002 (diğer noktalar ~0,003), 750/%0 ve 800/%25 Knz ≈ 0, 800/%0 fugoid nan, damperli Dutch roll ζ_sim nan (ikinci tepe yok). Kazanç tablosu düzgünleştirilmeli (docs/09 §5.2 kural 3 bunu kabul ediyor) | Programlanmış kazançta ara noktalarda sıçrama; Codex #14 ile aynı yönde | 1 gün |
| Ö5 | P2 | V_D gerekçesi: V_D 900 km/h, tam gaz Vmax tahmini 878 (kötümser) – 898 km/h (alık modeli); yani V_D ≈ Vmax. 800 km/h limiti ECU gaz yüzdesiyle, hava hızıyla değil (Codex #12'ye katılıyorum) | Gaz sınırı arızasında veya dalışta V_D aşılabilir; flutter gereksinimi 1080 km/h hâlâ 1,2·898'in üstünde | tasarım kararı |
| Ö6 | P2 | `aero_analysis.py` [5] dinamik modlar hâlâ Roskam ataletiyle (Ixx 0,572); CAD (0,405) varken onu kullanmalı (doküman 09 CAD kullanıyor, doküman 02 iki farklı sayı gösteriyor) | Tutarlılık | 1 saat |
| Ö7 | P3 | `mission.py` kalkış etiketi "flap 10" ve +0,03 dolly sürüklemesi, aero analizinin flap 18° kalkış konfigürasyonu ile uyumsuz; `sizing.py` `CLmax_land` 1,15 (aero nominal 1,11) | Küçük tutarsızlıklar | 1 saat |
| Ö8 | P3 | `validation/report.py` `drag_sizing_approx_N=210` sabit (benim alanım değil); sizing modelinden okunmalı (212 N) | Tek veri kaynağı kuralı | 15 dk |
| Ö9 | P3 | `params.py` yorum satırı "f_1T 272.5 -> 294.9 Hz" (düzeltilmiş değer 295,2 Hz) | Yalnız yorum; params'a dokunmadım | 1 dk |

### Codex disiplinler arası maddeleri (alanıma düşenler)

| Codex # | Değerlendirme |
|---|---|
| 2 Sensör filtreleri | **Katılıyorum** (Ö3). Doküman 09 §6 metni sayısal olarak iyimser. |
| 3 Servo dinamik cevabı | **Katılıyorum.** 25 Hz / 600 °/s sabit, yükten bağımsız; rudder %13 tork payı. Servo tork-hız ve dinamik rijitlik ölçümü yol haritasına eklendi. |
| 4 Manevra + hamle | **Katılıyorum.** Kestirim kaba (doğrusal ölçekleme) ama yön doğru: 10 g manevrada 3 m/s hamle bile 12 g'yi aşabilir. Ek olarak kısa hamlenin negatif tepesi (−11…−13 g) −8 g limitini aşıyor; doküman 09 ve FMEA 16'ya yazıldı. Hız/yakıta bağlı manevra limiti önerilir. |
| 5 Takılı motor itkisi | **Katılıyorum.** `thrust()` yalnız σ ve k_ram; giriş toplam sıcaklığı (≈308 K) ve düzeltilmiş devir yok. %41 pay modele bağlı; itki standı + alık takılı test yol haritasında. |
| 6 Alık–motor eşleşmesi | **Kısmen katılıyorum.** Debi `mdot_air·σ·(1+k_ram M²)` ile atanıyor, çalışma noktası çözülmüyor; distorsiyon yok. "0,75 kg/s %12 yüksek" iddiasını doğrulayamadım (üretici verisine erişmedim); motor varyantı netleştirilmeli. |
| 7 Yakıt transferi | **Katılıyorum.** Doküman 05'te transfer mekanizması (basınçlandırma/pompa) tanımsız; 250 ml hopper tam gazda ~11 s. Yakıt sistemi testi yol haritasına eklendi. |
| 8 Termal | **Katılıyorum** (Ö2); boru ısıl uzaması (3,6 mm) için kayar mesnet önerisi yerinde. |
| 9 Tank hacmi | **Doğrulandı** (Ö1). params değiştirilmedi, doküman 05'e açık madde olarak yazıldı. |
| 10 Yakıt CG / sloshing | **Katılıyorum.** `mass_properties.py` tankların eşit oranda boşaldığını varsayıyor; doküman 05 ise kanat/orta tankın gövde tankına boşaldığını söylüyor (yani gerçek sıra farklı). Tank bazında CG zarfı gerekli. |
| 11 Pitot q | **Doğrulandı ve düzeltildi** (D11). |
| 12 ECU gaz ≠ hız sınırı | **Katılıyorum** (Ö5). |
| 13 Servo arıza senaryosu | **Katılıyorum.** `fail_*` yalnız nötrde kilitlenme; sapmış kilitlenme ve tek elevator arızası eklenmeli. |
| 14 Kazanç geçişleri | **Katılıyorum** (Ö4). Düşük hız kontrol yasası F1 ön koşulu olmalı (docs/08 §5). |
| 15 Görev profili | **Katılıyorum.** Bacak hızları/gazları bağımsız; dönüşte %35 itki sürüklemeyi karşılamıyor, yani hız düşer ve sonraki hızlanma yakıtı sayılmıyor. 4 geçişte %6 rezerv bu yüzden iyimser olabilir. |
| 16 Dolly | **Doğrulandı ve düzeltildi** (D6). |
| 17 Tırmanma | **Doğrulandı ve düzeltildi** (D5). |
| 18 İtki momenti trimde | **Katılıyorum, etki küçük.** z_cg −15,6 mm, motor ekseni z = 0 → 300 N·0,0156 m ≈ 4,7 N·m; 750 km/h'te q·S·c ≈ 3,4 kN·m, ΔCm ≈ 0,0014 (≈0,05° elevator). Düşük hızda ve motor durmasında daha önemli. |

## 5. Yol haritasına eklenmesi gerekenler (fiziksel prototip öncesi)

Doküman 08 §5'e işlendi. Özet sıra:
1. **Masa başı kapanışlar:** bütün uçak aeroservoelastik model (kuyruk, kumanda yüzeyleri, servo/bağlantı esnekliği); kabuk mod şekilli p-k; tank hacmi ve tank bazında yakıt CG zarfı; filtreli kontrol payları, değişken kazançlı simülasyon, 350 km/h altı kontrol yasası; takılı motor modeli; manevra+hamle yük zarfı; RAE/SST/3B CFD; thermal_1d yeniden koşum.
2. **Malzeme kuponları** (hot/wet Tg dahil).
3. **Türbin motor testi:** itki standı; alık + S-kanal + egzoz takılı net itki; motor yüzü basınç tarağı; keçeli termokupl ölçümü.
4. **Alık rüzgâr tüneli** (veya araç üstü) testi: MFR 0,5–2,5, η_r, distorsiyon, yan kapaklar.
5. **Statik yük testi:** kanat limit/nihai (ayrı test kanadı), kanat-gövde bağlantısı, kuyruk bağlantısı, kızak darbesi, GJ.
6. **GVT:** serbest-serbest bütün uçak, dolu/boş, kumanda yüzeyi modları, ≥ 2 kHz örnekleme.
7. **Servo testi** (gerçek yükte tork-hız, boşluk, dinamik rijitlik) ve **HIL** (gerçek FC, filtreler, arıza ve mod geçişleri).
8. **Yakıt sistemi** (sızdırmazlık, transfer, hopper, negatif g) ve **dolly** ayrılma testi.
9. **Ölçekli/hız limitli öncü uçak** (≤ 500 km/h).
10. **Uçuş zarfı genişletme F1–F6**; hız koruması ölçülen hava hızıyla.
11. **Mevzuat:** SHGM İHA1 kaydı ve pilot sertifikası, 2026 lisans rejimi kontrolü, saha/hava sahası izni, sigorta, Guinness/FAI kanıt gereksinimleri, motor alımında son kullanıcı beyanı.

## 6. Doğrulayamadıklarım

- Kanat tankı gerçek kullanılabilir hacmi (kaburga delik oranı ve sayısı CAD'de tanımlı değil); yalnız kaba kestirim.
- Codex #6'daki P400-PRO-LN debi değeri (üretici sayfasına erişmedim).
- Termal maddeler için yeniden koşum yapmadım (thermal_1d STALE, alanım değil).
- `structures/fe_modal.py`'de başka ajanın yaptığı değişiklik (1D V_F 1813 → 1452 km/h) run_all koşusuna girdi; doğruluğunu incelemedim, docs/04/10'daki "1D 1813 km/h" ifadeleri o ajanın işi bitince güncellenmeli.
- İnceleme paketini yeniden üretmedim (yalnız `--dry-run`).
- Doküman 09 sayıları `fc_sonuclar.json` ile eşleştirildi; flight_control simülasyonlarını bağımsız olarak yeniden hesaplamadım.
