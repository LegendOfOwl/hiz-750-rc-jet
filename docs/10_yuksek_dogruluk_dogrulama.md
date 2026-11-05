# 10 — İter5 / v0.6 yüksek doğruluk doğrulaması

**İkinci tur: kısmi doğrulama tamamlandı.** Araçları Claude host üzerinde kurdu; escalation ile Python/solver çalıştırıldı. Konsol ve 1B termal üç ağda kabul aldı; altı koşullu motor termal senaryosu çözüldü. CFD pilotları yakınsamadı veya hata verdi. İlk turun sandbox engeli [tarihsel yoklamada](../validation/results/machine_probe.json) korunur; güncel kurulum [installation.json](../validation/results/installation.json) içindedir. CFD doğrulaması tamamlanmış sayılmaz.

**İter5 FEM güncellemesi:** CLT kupon benchmarkı kabul edildi (BENCHMARK_ACCEPTED), kompozit kanat kabuk modeli çözüldü (REVIEW_REQUIRED) ve kanat rijitleştirilerek `params.py` güncellendi (ayrıntı §10.7). Aşağıdaki "params.py değişmedi" ifadesi ilk turlara aittir; iter5 sonunda `WING` kat planı değişmiştir.

Kurulum ve komutlar: [validation/README.md](../validation/README.md). `params.py`, eski analizler ve `run_all.sh` değişmedi. v0.6, v0.5 bulgularını doğrulanmış ürün verisi olarak yükselten bir sürüm değildir.

## 10.1 Araçlar ve çalışma sırası

| Araç | Sabit hedef sürüm | Bu worktree'deki durum | Kullanım |
|---|---|---|---|
| SU2 | 8.2.0 serial Windows x64 | kurulu; SA pilotları çalıştı | sıkıştırılabilir SA/SST; SST henüz koşulmadı |
| gmsh Python API | 4.15.2 | kurulu; ağlar üretildi | 2B BL, kabuk; 3B tetra **ön ağ** |
| CalculiX ccx | resmi Windows 2.20 arşivi | kurulu; benchmarklar çözüldü | S8R/S6 statik/modal ve ısı transferi |
| Python | 3.12.10 | escalation ile erişildi | runner/postprocess/unittest |
| OpenFOAM | seçilmedi | WSL kullanılamıyor | ileride alternatif |

Sürümler [resmi SU2 release](https://github.com/su2code/SU2/releases/tag/v8.2.0), [gmsh](https://gmsh.info/) ve [CalculiX/PrePoMax](https://prepomax.fs.um.si/downloads/) üzerinden sabitlendi. Executable hash'i ve gerçek banner host'ta kaydedilecek. İndirme byte'ları bu oturumda doğrulanmadı; hedef sürüm kurulu sürüm diye raporlanmadı.

Önce üç seviyede konsol ve 1B termal; sonra SA **ve ayrı SST** için düz levha ve RAE2822; kabul sonrası A/B/C/D/E. Her alanın benchmarkı kendi uygulamasının ön koşuludur; aynı executable SHA256'si, kaynak ve params hash'leri aranır. `--diagnostic` kabul kapısını geçirmez.

İlk kaba koşularla süre/bellek ölçülmeli. Tahmini bütçe: 2B5–90dk/ağ/model; B≤2M hücre ve1–6saat/ağ; C≤2M ve1–4saat/ağ; D≤200k açılmış DOF ve5–30dk/ağ; termal<2dk/ağ. Bunlar ölçüm değildir. Üç ağ × üç α × beş Mach × iki model tüm tarama süresini büyütür; bütün işin birkaç saatte biteceği vaat edilmiyor.

## 10.2 Benchmarklar ve hata tabloları

**RAE2822 Case6:** M=.729, Re=6.5e6, α=2.31°, T=288.15K; adyabatik no-slip duvar. [SU2 referans konfigürasyonu](https://github.com/su2code/SU2/blob/master/TestCases/rans/rae2822/turb_SST_RAE2822.cfg) ve [NASA RAE arşivi](https://www.grc.nasa.gov/www/wind/valid/rae2822/rae2822.html) izlenir. Ham tünel M=.725/α=2.92° ile düzeltilmiş hesap koşulları karıştırılmamalı. Sayısal Cp/CL/CD, kaynak ve deney belirsizliğiyle henüz alınmadı/digitize edilmedi. Null referanslar sahte deney sayılarıyla doldurulmadı. M=.8/sabit CL=.724 optimizasyon tutorial'ı bu vaka değildir.

**Düz levha:** [NASA TMR](https://tmbwg.github.io/turbmodels/flatplate.html) koşullarına benzer M=.2, Re_x=5e6 @1m, L=2m. Tam türbülanslı ortalama Cf, Schlichting ve ITTC ile karşılaştırılır. Bu ağ/BC TMR'nin birebir replikası değildir; korelasyon farkı tek başına deney doğrulaması sayılmaz. ONERA M6 ve ayrıca deneysel S-kanal benchmarkı eklenmedi.

| Vaka / model | Büyüklük | Kaba | Orta | İnce | Referansla hata [%] | p / GCI ince |
|---|---|---|---|---|---|---|
| RAE2822 SA | CL, CD, Cp RMSE | yakınsamadı (yeni 100c C-ağı; MG3 ıraksadı, MG0 ρ≈−4.8'de durağan; ara CL .730/CD .01345/Cp RMSE .092) | koşulmadı | koşulmadı | NASA Cp yeniden üretildi; kabul yok | PENDING (§10.6.1) |
| RAE2822 SST | CL, CD, Cp RMSE | bekliyor | bekliyor | bekliyor | deney verisi de bekliyor | bekliyor |
| Düz levha SA | Cf_mean | .0028542517 | .0028586462 | .0028613266 | Schlichting −4.74, ITTC −4.62 (ince) | p .434 / GCI %0.88 — BENCHMARK_ACCEPTED (iter5 v2, §10.6.1) |
| Düz levha SST | Cf_mean | bekliyor | bekliyor | bekliyor | bekliyor | bekliyor |

**Konsol:** 1×.05×.01m, E210GPa, rho7800kg/m³, uçta1N. Euler–Bernoulli sehim ve f1, ayrıca reaksiyon dengesi. S8R ağlar10×2/20×4/40×8. [CalculiX kılavuzundaki](https://www.dhondt.de/ccx_2.22.pdf) composite desteği S8R/S6 içindir. Konsolun doğru çıkması kompozit tabaka yönlerini tek başına doğrulamaz; **CLT laminat kupon benchmarkı iter5'te tamamlandı ve kabul edildi** (§10.7.1, en büyük hata %1,12).

**Termal:** 100mm, k10W/(m K), bir yüzde100°C, diğer yüzde h25W/(m² K)/20°C ortam; 4/8/16DC3D8. Analitik `q''=(Th−T∞)/(L/k+1/h)`, `T(x)=Th−q''x/k`. DC3D8 bu lineer profili tam temsil edebilir. Üç ağ farkı yuvarlama düzeyindeyse p/GCI yerine **EXACT_OR_ROUNDOFF** yazılır. Bu beklenen özellik, çalıştırılmış ccx kanıtı değildir.

| Vaka | Büyüklük | Kaba | Orta | İnce | Analitik hata [%] | p / GCI ince |
|---|---|---|---|---|---|---|
| Konsol S8R | sehim [mm] / f1 [Hz] | .3734951 / 8.492973 | .3768355 / 8.442452 | .3781402 / 8.422987 | −.7382 / +.4902 (ince) | p1.3563/GCI%.2764; p1.3760/GCI%.1811 |
| 1B iletim+taşınım | Tsoğuk [K] / q'' [W/m²] | 357.15 / 1600 | 357.15 / 1600 | 357.15 / 1600 | 0 / 0 | EXACT_OR_ROUNDOFF; p/GCI tanımsız |
| Kompozit CLT kupon (5 laminat) | Ex, Ey, Gxy, D11, 3N sehim, tabaka σ | membran 4/8/16², B3 8/16/32×4/8/16 | (üç ağ) | (üç ağ) | en büyük \|hata\| %1,12 (< %2) | BENCHMARK_ACCEPTED; GCI ≤ %5, ayrıntı §10.7.1 (iter5 ile güncellendi) |

Richardson/GCI, üç ağda monoton yakınsama ve aynı problem tanımı gerektirir: `Fs=1.25`, her h oranı≥1.3. Eşit olmayan oranlar çözülür; salınım veya sıfır fark zorla p=2'ye çevrilmez. `h∝N^(-1/d)` yalnız tutarlı ağ ailesinde anlamlıdır; duvar/alan boyutları birlikte rafine edilir. Şok veya mod sırası değişiminde p/GCI yorumu sınırlandırılır. İterasyon/ağ yakınsaması, deneyle anlaşma ve fiziksel tasarım kabulünden ayrıdır.

## 10.3 HIZ-750 karşılaştırması

Eski sayılar depodaki JSON'lardan okunmuştur; burada tekrar hesaplanmadı. `validation/report.py` bunların SHA256'sini saklayıp yeni sonuçlarla yan yana yazar. Yeni sonuç gelmeden hata veya iyileşme yüzdesi yoktur.

| Uygulama | Mevcut yarı-ampirik değer | İter5 sonucu | Engel / sınırlama |
|---|---|---|---|
| A / profil, Re4.5e6 | NeuralFoil M0: Cd0=.0035074; Clα=6.06675/rad; Cm0≈0 | bekliyor: cl/cd/cm, SA–SST, sonik Cp | solver/RAE deney kabulü |
| B / uçak, 750km/h,300m | AeroBuildup154.353N / sizing yaklaşık210N | bekliyor: D, basınç/sürtünme payı, GCI | temiz fluid hacmi + prizmatik duvar ağı |
| C / S-kanal | η_r=.970955; DC60 yok | bekliyor: recovery/DC60/debi | dış gövde BL yutulmalı; duvar STEP'i fluid değil |
| D / dolu kanat | 1B27.459Hz, 1T305.677Hz; flutter1307.484km/h | iter5 (kabuk FEM, 3/1): 1B 39,51 Hz, 1T 272,54 Hz, uç sehim 47,7 mm, Tsai-Wu R 3,66, flutter ≈1185 km/h; seçilen 4/1 + 43 mm tasarım: 1T 294,9 Hz, ≈1266 km/h (§10.7) | REVIEW_REQUIRED: malzeme sabitleri varsayım, imalat detayı yok; kabuk mod şekilleriyle p-k yok |
| E / motor | kabuk sıcaklığı ölçülmedi; Tg≥150°C hedefi | bekliyor: Tkabuk/keçe | k/h/ε, bypass ve açıklık |

**A:** RANS, `aero/aero_analysis.py` ile aynı kalınlığı ölçeklenmiş64A010 koordinatını kullanır. Gerçek64A007'ye geçmek ayrı geometri duyarlılığıdır. α0/1/2°, M.61/.65/.70/.725/.75 ve iki model taranmalı. Matched-Mach NeuralFoil ile eski M0 ayrı saklanır. Tam türbülans RANS ve NeuralFoil ncrit9 geçiş varsayımı cd farkının model bütçesindedir. İlk sonik Mach, Mcrit için üst sınırdır; kesin Mcrit veya drag divergence sonucu değildir.

**B:** aynı300m ISA, CL/trim, yüzey ve bileşen seti eşleştirilmeli. Referans alanS/2, yarı kuvvet×2. İç aksam/dolly çıkarılır; alık/egzozun kapalı/açık ya da motorlu seçimi raporlanır. Sade zarf D'si, alık/kızak/girişim paylarını içeren AeroBuildup ile aynı kapsam değildir. 154–210N farkı210N'e göre yaklaşık%26.5,154N'e göre yaklaşık%36'dır; paydasız “%25 hata” denmemeli. 3B tetra ön ağ otomatik olarak doğru RANS ağı sayılmaz.

**C:** debi `ENGINE.mdot_air × σ × (1+.6M²)` ve tam motor yüzünde FAN_FACE_MDOT. Uniform girişli kapalı kanal η_r=.971'in sınır tabaka yutma kısmını sınamaz. ENGINE örneklerinde recovery kütle/alan ağırlıklı ayrı; DC60 sektör alan ortalaması ve `q=0.5rho u_n²` ile hesaplanır. Ters akış/eksik disk örneklemesinde postprocess durur. Motor distorsiyon limiti verilmediğinden fiziksel kabul yazılamaz. Ayrıntılar [CFD notunda](../cfd/README.md).

**D:** [FEM notu](../fem/README.md) kat planını ve tam malzeme tablosunu verir. Depodaki UD E1=125GPa/Xt2100MPa, kumaş E55GPa/t.178mm/rho ve kayma izinleri önceliklidir; eksikler görevde verilen tipik değerlerle **varsayım (üretici verisiyle değiştirilecek)** olarak tamamlandı. FAB.G45=25GPa ile lamina G12=4.5GPa farklıdır. Rohacell E70MPa/G19MPa tek izotropik ν ile uyumlu olmadığı için ortotropik yaklaşık sabitler kullanıldı. F12 etkileşim katsayısı ölçülmedi. Bunlar hot/wet allowables değildir.

Kabuk taslağı; ince burun/TE sandviç birleşmesi, kontrol yüzeyi kesikleri, rib/cıvata esnekliği ve servo/yakıt ataleti düzeltilmeden üretim modeli değildir. Torsion indicator ön taramadır; mod şekliyle1B/1T eşleştirilmelidir. Tsai–Wu lokal tabaka CSV'sinden hesaplanabilir; CCX integration-point/tabaka eşleştirmesi kontrol edilmeden otomatik çevrilmedi. Ham FI ve KD=.544 dayanım duyarlılığı ayrıdır; KD doğrulanmış B-basis veri değildir. Buckling/debonding ve bağlantılar ayrıca incelenir.

**f1T→flutter:** sabit ataletle `GJ_yeni/GJ_eski≈(f1T_yeni/305.677)²` yalnız rijitlik taramasıdır. Örneğin ileride250Hz ölçülmesi yaklaşık.669 GJ oranına işaret eder; **FEM sonucu değildir**. Flutter hızı aynı oranla çarpılamaz: kritik3B–1T eşleşmesi, CG, mod şekli ve aerodinamik bağlaşım değişir. Yeni modal bazla aeroelastik çözüm kurulmalı. *(iter5 ile güncellendi: kabuk FEM f_1T = 272,5 Hz (3/1) ve seçilen 4/1 + 43 mm tasarımda 294,9 Hz buldu; yalnız frekans ölçeklemesiyle V_F ≈ 1185 → ≈1266 km/h. Kabuk mod şekilli p-k hâlâ açık; §10.7.)* Eski1307km/h ayrıca transonik bölgede sınırlandırılmış PG düzeltmesine dayanır; statik RANS dinamik flutter doğrulaması değildir. GVT kriteri yalnız **alt frekans sınırıdır**; taramanın üst ucundan fiziksel kabul bandı çıkarılmaz.

**E:** motor150–250°C, keçe0–3mm, bypass h0/15/50, emissivite.1/.7/.9 ve yer/uçuş dış taşınımı taranmalı. Model yerel1B kararlı iletim+taşınım+ışınımdır; 3B termal/CHT değildir. Bağımsız skaler enerji dengesi aynı BC'yi kontrol eder, h/ε'nin gerçek olduğunu kanıtlamaz. Keçe açıklığı/soğutma debisini azaltabilir. Tg150°C, sürekli servis sıcaklığı izni değildir; üretici hot/wet ve sıcaklıkta dayanım değerleri gerekir. [Termal not](../thermal/README.md).

## 10.4 LES/DES maliyeti

GPU yokluğu tek başına engel değildir;3B çözünürlük ve zaman ortalaması asıl maliyettir. ν≈1.5e−5m²/s ve uτ≈5–10m/s mertebesinde y+1 için ilk mesafe birkaç mikrometredir. Δx+50–100 ve Δz+15–30, metre kare mertebesindeki yüzey ve normal katmanlarla kabaca **10^8–10^10 hücre** gerektirebilir. Bu HIZ ağ sayımı değil büyüklük tahminidir; [Choi–Moin LES grid ölçeklemesi](https://doi.org/10.1063/1.3676783) yüksek Reynolds maliyetini açıklar.

Örnek maliyet (ölçüm değil): N=10^8, Δt=1e−6s,0.5s fiziksel süre, adımda10 iç iterasyon, hücre güncellemesi1e−7s varsayımıyla `N×(0.5/Δt)×10×1e−7≈5e7s`, yaklaşık579gün. 200–1000byte/hücre ile bu düşük N bile20–100GB, daha büyük ağlar TB ölçeğindedir. CPU paralelleşmesi azaltabilir; bu makinede performans ölçülmedi. DDES duvar maliyetini azaltır, fakat ayrılmış alık/wake için3B çözünürlük ve çok sayıda zaman adımı gerekir;≤2M bütçesiyle güvenilir DES iddia edilmez.

2B zamana bağlı SA/SST, URANS'tır;3B türbülans kaskadını çözen LES değildir. “Quasi-LES” animasyonu doğrulama kanıtı diye üretilmedi. CPU bütçesi önce doğrulanmış2B ve sınır katmanlı kaba-orta3B RANS'a ayrılır.

## 10.5 Belirsizlik bütçesi ve kararlar

| Kalem | Bütçe yöntemi | Şimdiki durum |
|---|---|---|
| İteratif/ağ | residual+kuvvet/ısı dengesi, üç ağ GCI | koşu yok, sayısallaştırılmadı |
| CFD model formu | SA–SST, geçiş/pürüzlülük, domain | fark bilinmiyor; ortak RANS yanlılığı kapsanmaz |
| Geometri/trim | profil, alık/kızak/motor, aynı CL | B/C topoloji/ağ hazırlığı |
| Deney | AGARD koşulları, Cp digitizasyonu/tünel düzeltmesi | sayısal veri/belirsizliği bekliyor |
| Yapı | E/G/ν/strength, core, bağ, kütle/CG, modal baz | tipik değerler; CLT kupon kabul (iter5), GVT yok |
| Isıl | h/k/ε/gap, görüş faktörü/heat soak | ölçüm yok; koşullu senaryolar |
| Türbin | Vj/k_ram/ṁ ve distorsiyona tepki | recovery tek başına itki kalibrasyonu değildir |

Bağımsız normal dağılımlar varsayılmadı; bu kalemler körlemesine RSS ile bir güven yüzdesine çevrilmez. GCI, fiziksel model hatasının küçük olduğunu göstermez.

**Şimdiden gerekli öneri:** nominal8.5mm açıklıkla termal tasarım dondurulmasın. `cad_report.json` ön6.8mm ve minimum**5.97mm** veriyor; dış çap farkı kabuk kalınlığı düşülmeden iç açıklık değildir. Keçe/bypass için en küçük gerçek kesit kullanılmalı. `params.py` değiştirilmedi.

**Sonuç bekleyen kararlar:**

1. D ve η_r doğrulanana kadar itki payı/azami hız doğrulanmış ilan edilmesin; türbin yer/uçuş ölçümü gerekir.
2. İmalat katları/kontrol boşlukları ve frekanslar eşleştirilmeden mevcut flutter marjına dayanarak kat azaltılmasın. GVT öncesi kısıtlar gevşetilmesin. *(iter5: kat planı 4/1, kaburga 43 mm, web +1 kat'a yükseltildi; flutter tasarım değeri ≈1266 km/h, 1350 km/h payı sağlanmıyor; §10.7.3.)*
3. Kabuk içi/keçe altı termokupl, motor yüzeyi ve stop sonrası heat soak kaydı alınsın; reçine/keçe sıcaklıkta izin değerleriyle seçilsin.
4. RAE deney verisi, iki model/üç ağ ve solver banner'ları tamamlanınca tablolara gerçek sonuç/hata/GCI işlenip v0.6 tekrar incelensin.

Paket deney düzenini ve izlenebilir engel kayıtlarını kurar. Host koşuları ve fiziksel model incelemesi bitmeden yüksek doğruluk doğrulaması tamamlanmış değildir.

## 10.6 İkinci tur gerçek koşuları

Tam hata tabloları: [konsol](../validation/results/cantilever/study.md), [1B termal](../validation/results/thermal_1d/study.md). Python regresyonları13/13 ve compileall geçti. Gerçek koşularla CalculiX'in sayı alanı, Lednicer/Selig sırası, sıfır kaliteli düz levha köşeleri ve SU2 yardımcı Buffet NaN çıktısı düzeltildi. Fiziksel NaN ve yakınsama ölçütleri gevşetilmedi.

RAE2822 6000 iterasyonda CL=.695162, CD=.0140953, y+max=.795; **UNCONVERGED** (maksimum log residual−2.444). Profil M=.61/α=0 pilotu1000 iterasyonda **UNCONVERGED**; tasarım karşılaştırmasına alınmadı. RAE deney referansı eksik; CFD için üç-ağ GCI veya deney hata yüzdesi üretilmedi. Kendi düz levha ağındaki denemeler salınım veya FGMRES hatası verdi; eski salınımlı koşu kimliği doğrulanarak durduruldu.

Resmi SU2 v8.2 config + resmi137×97 ağ kontrolü6000 iterasyonu394.53s'de tamamladı. Son ekran Cf=.002849; Schlichting .003003713'e göre fark−%5.151 (ekran yuvarlatmalı). Yoğunluk log residual−8.411, SA−10.159. Bu tek ağ/korelasyon kontrolüdür; kendi gmsh ailesi için GCI veya RAE deney kabulü değildir. CL=−.188287; referans basınç/tek yüzey kuvvet tanımı incelenmeden fiziksel kaldırma diye kullanılmaz. Kaynak URL/hash ve son ekran satırı [ayrı kayıtta](../validation/results/flatplate_native.json).

Motor250°C için ince ağ sonuçları (ölçülmemiş h/k/ε varsayımları; her senaryo üç ağda çözüldü):

| Açıklık [mm] | h_bypass / h_dış [W/(m² K)] | Keçe [mm] | Kabuk içi [°C] | Sıcak keçe yüzü [°C] |
|---|---|---|---|---|
| 8.50 | 15 / 100 | 0 | 58.77 | — |
| 8.50 | 15 / 100 | 2 | 44.39 | 109.33 |
| 5.97 | 15 / 100 | 0 | 61.71 | — |
| 5.97 | 15 / 100 | 2 | 46.67 | 117.70 |
| 5.97 | 0 / 10 | 0 | 149.82 | — |
| 5.97 | 0 / 10 | 2 | 126.10 | 184.96 |

Yer/bypass yok senaryosunda keçesiz149.82°C, nominal Tg150°C'ye yalnız0.18°C uzaklıktadır; güvenlik payı değildir. Ölçülmemiş taşınım/görüş faktörü/heat-soak nedeniyle üretici hot/wet verisi ve termokupl ölçümü olmadan keçe veya servis kabulü verilmez.

*(Kanat kaba taslağı iter5'te 7168 S8R'li modelle değiştirildi ve çözüldü, bkz. §10.7.)* Kanat kaba taslağı224 S8R/694 düğüm, açılmış DOF tahmini6246; çözülmedi. Uçak ön ağı5885, izole kanal ön ağı4727 tetra. Uçakta konik/silindirik gövde ve dörtgen kanat/kuyruk, kanalda CAD rapor kesitlerinin16 kenarlı yaklaşımı kullanıldı. Yalnız DRAFT/topoloji kontrolüdür: prizmatik BL yok, kanal dış gövde BL yutulmasını içermez. D ve η_r sonucu üretilmedi.

### 10.6.1 İter5 v2 CFD: düz levha kabulü, yeni RAE ağı

Ayrıntı ve ham klasörler: [cfd/RESULTS_iter5.md](../cfd/RESULTS_iter5.md) son bölüm.

**Düz levha SA — BENCHMARK_ACCEPTED.** Resmi ağ+cfg RAE kontrolü (CL −%2.6, CD +%5.9) çözücüyü doğruladıktan sonra düz levha üç ağı aynı ayarla sıfırdan koşuldu: ROE+MUSCL, MGLEVEL=0, CFL 1 + CFL_ADAPT (0.5, 1.5, 1.0, 100), FGMRES+ILU, 1e−6. SU2'nin DRAG-Cauchy 1e−6 duruşu proje kapısından önce geliyordu (ince ağda Cf .0029177 → yakınsamış .0028613), bu yüzden durma kuralı ν̃ residual ≤−9.3 ve DRAG-Cauchy ≤1e−8 yapıldı. Üç ağ da proje kapısını geçti (bağıl Cauchy100 ≈3.5e−7, ρ/ν̃ düşüşü ≥5.28/4.97, y+max .49/.34/.27). Cf kaba/orta/ince .0028542517/.0028586462/.0028613266; monoton, p=.434, Richardson .0028815, ince GCI %0.88. İnce ağın Schlichting farkı −%4.74, ITTC farkı −%4.62. Düşük gözlenen mertebe ve korelasyon karşılaştırması nedeniyle bu, deney doğrulaması değil sayısal/korelasyon kabulüdür.

**RAE2822 kendi ağı — PENDING.** `cfd/structured_airfoil.py` tek bloklu C-ağıyla değiştirildi: monoton açılı duvar-normali ışınları, 100c uzak alan/iz, iz ışınları çıkışa doğru 45° yelpaze, ilk hücre 2e−6c/factor, normal büyüme 1.18/1.12/1.09, minimum köşe sinüsü .707 (duvar yakınında ≥.97; eski ağ .277, resmi ağ .371), 33792/76032/135168 quad ([denetim](../validation/results/rae2822_v2_mesh_audit.json)). NASA NPARC Cp dosyaları ayrı klasöre yeniden indirildi, SHA256'ları kaydedildi ve `python -I` ile işlendi. Resmi MG3 ayarı bu ağda ~1340. iterasyonda ıraksadı. MG0+CFL_ADAPT ıraksamadı ama ρ residual'ı ≈−4.7…−4.9'da durağan kaldı. Ara değerler CL .730 (ikincil referansa −%1.8), CD .01345 (+%5.9), Cp RMSE .092 (>.08), y+max .81 ve resmi ağ sonucuyla aynı düzeydedir. Residual iz kesitinde (x≈1.2–2c) toplanıyor (2e−6c kalınlığında, en-boy oranı 1e3–1e7 iz hücreleri). Kaba ağ kapıyı geçmediğinden orta/ince koşulmadı; GCI ve kabul yok. Eşikler korunur (Cp RMSE ≤.08, |CL| ≤%5, |CD| ≤%15, GCI ≤%5). Sonraki adım: iz bölgesinde normal dağılımı gevşetilmiş, katman eğimi sınırlı bir iz bloğu veya hibrit iz ağı.

## 10.7 İter5 FEM sonuçları: CLT kupon, konsol, kompozit kanat ve rijitleştirme (iter5 ile güncellendi)

Ayrıntı ve yeniden üretim komutları: [`fem/RESULTS_iter5.md`](../fem/RESULTS_iter5.md); yapı tasarımına etkisi [doküman 04 §15](04_yapi_flutter.md). Araç: CalculiX 2.20 (`ccx_static.exe`), gmsh 4.15.2, Python 3.12; tüm koşular `--threads 1`, çözücü SPOOLES. Bu bölüm 10.1-10.6'daki "bekliyor/uygulanmadı" ifadelerini FEM için günceller; CFD satırları bu bölümün kapsamı dışındadır.

**Çözücü bulguları:** (1) CCX 2.20 Windows yapısında çok iş parçacıklı sonuç hesabı güvenilmez (bir elemanda ~1 GPa sahte gerilme, tekrarlanamayan frekanslar); (2) varsayılan PaStiX gürültülü/askıda, SPOOLES kullanıldı ve konsol benchmarkı bu çözücüyle yeniden kabul edildi (sehim −%0,74, f1 +%0,49, GCI < %0,3); (3) kompozit kabuklu modelde MASS elemanı çalışmıyor, yapısal olmayan kütle 10 µm/1 MPa NSM tabakası ve `*EQUATION`'lı kaldıraç küpleriyle verildi; (4) kökte 1-6 kısıtı yük kaybettirdi, 1-3 ankastre kullanıldı (denge 2·10⁻⁷).

### 10.7.1 CLT kupon benchmarkı: BENCHMARK_ACCEPTED

Referans bağımsız CLT (`fem/clt.py`). Her laminat için TX/TY, SH ve dar şerit üç nokta eğilme (B3); membran ağları 4/8/16², B3 ağları 8/16/32 × 4/8/16. Kabul: üç ağın her birinde |hata| ≤ %2 ve GCI ≤ %5. İnce ağ hatası (CCX − CLT):

| Laminat | Ex | Ey | Gxy | D11 | 3N sehim | maks. tabaka σ |
|---|---|---|---|---|---|---|
| UD [0]5 | 0,000 % | 0,000 % | 0,000 % | 0,000 % | −0,007 % | 0,00 % |
| UD [+45/−45]s | −0,001 % | −0,001 % | +0,054 % | +0,004 % | −0,153 % | 0,00 % |
| Ön kabuk sandviç FAB45(3)/Rohacell 2 mm/FAB45(3) | +0,003 % | +0,003 % | +0,001 % | 0,000 % | −0,039 % | 0,03 % |
| Kök kapak UD(3)/FAB45(3)/çekirdek/FAB45(3), OFFSET 0,5, simetrik değil | +0,062 % | +0,014 % | +0,007 % | −0,023 % | −0,001 % | **1,12 %** |
| Web FAB45(3) | 0,000 % | 0,000 % | 0,000 % | 0,000 % | −0,286 % | 0,00 % |

En büyük hata %1,12 (simetrik olmayan kapak laminatında UD'ye komşu kumaş tabakası); hepsi %2 içinde. Doğrulanan yorumlar: tabaka sırası alttan (−normal) üste; her tabaka için 8 integration point; OFFSET = 0,5 malzemeyi referans yüzeyin −normal tarafına koyar. **Sınır:** CCX kabuk genişlemesi sandviç çekirdek kaymasını (zigzag) temsil etmez; sandviç teorisi ön kabukta +%3,3, kapakta +%7,3 daha büyük sehim verir, yerel panel/çekirdek kayması bu modelle değerlendirilemez. 2 eleman genişlikli B3 şeridinde CCX anlamsız sonuç verdi, en az 4 eleman kullanıldı. Yani 10.2'deki "konsolun doğru çıkması tabaka yönlerini doğrulamaz" endişesi kupon testleriyle giderildi.

### 10.7.2 Kompozit kanat kabuk modeli: REVIEW_REQUIRED

Model düzeltmeleri (eleman başına teğet çerçeve, ±45 web, 8 sandviç kaburga, tutarlı Gauss yükleri, kütle/CG eşlemesi) ve 6/6 geçen otomatik inceleme: `fem/wing_shell.py`, `fem/wing_review.py`. Ağ: açıklık 8/16/32, veter 13/26/52; ince ağ 7168 S8R, CCX denklem sayısı 139 840 (≤ 200k), ince ağ çözümü ≈75 s. Malzeme sabitleri ölçülmemiş varsayımdır (UD E1 = 125 GPa, kumaş E = 55 GPa repo değerleri), bu yüzden kanat tasarım kabulü değil **REVIEW_REQUIRED**.

Statik (nihai 18 g Schrenk, kök momenti 411,9 N·m, kuvvet dengesi 1,7·10⁻⁷), 3/1 taban:

| Büyüklük | Kaba / orta / ince | Yakınsama |
|---|---|---|
| Uç sehim [mm] | 47,69 / 47,73 / 47,69 | salınımlı, yayılım %0,08 |
| Uç burulma [°] | 2,019 / 2,032 / 2,031 | salınımlı, %0,6 |
| Tsai-Wu R_min (y > 0,121 m) | 3,684 / 3,517 / 3,661 | salınımlı, %4,6 |
| Aynı, KD = 0,544 ile | 2,004 / 1,913 / 1,992 | salınımlı |
| Tsai-Wu R_min, kök bölmesi dahil | 2,89 / 2,26 / 1,88 | **yakınsamıyor** (ankastre tekilliği) |

Kritik bölge arka kiriş kapağının ön yarısı (y ≈ 0,15 m, σ11 = −224 MPa, R = 3,66). Kök bölmesi değeri tasarım değeri değildir. Çekirdek kayma gerilmesi en çok 27 kPa ve ağla artıyor (yakınsamadı). Burkulma, yapıştırıcı ve cıvata kontrol edilmedi.

Modal (ince ağ, dolu / boş tank): 1B 39,51 / 40,36 Hz, 2B 124,80 / 136,95 Hz, **1T 272,54 / 280,86 Hz**, 4. mod 1. düzlem içi eğilme 284,40 / 292,27 Hz, 5. mod 3B (burulma bağlaşımlı) 296,61 / 319,98 Hz. f_1T GCI: dolu %0,02, boş %0,17. 1D fe_modal ile kıyas (dolu): 1B 27,46 (oran 1,44), 2B 84,26 (1,48), 1T 305,68 (**0,89**); kabuk eğilmede çok daha rijit, burulmada %11 daha yumuşak. Kiriş teorisi çapraz kontrolü: 1D EI ile FE/kiriş = 0,54 (düz) ve 0,42 (ok açılı), kabuk EI ile 1,13 ve 0,89; yani fark EI farkındandır (structures kapak gerilmesi/sehimi muhafazakâr, burulma frekansı iyimser).

**Flutter etkisi (yalnız f_1T ölçeği):** 3/1 tabanda dolu ≈1185 km/h, boş ≈1194 km/h (1D 1307 / 1329). 1080 km/h gereksinimi sağlanıyor, 1350 km/h (×1,25 payı) için f_1T ≥ 316 Hz gerekir ve sağlanmıyor. Bu frekans ölçeklemesidir; kabuk mod şekilleriyle p-k çözümü açık iştir.

### 10.7.3 Rijitleştirme çalışması ve seçilen tasarım

21 seçenek orta ağda, 4 seçenek ince ağda çözüldü (`fem/results/stiffening/summary_medium.json`, `summary_fine.json`; dolu ve boş tank). Hedef f_1T ≥ 316 Hz (dolu) ve kesit CG ≤ 0,45c: **hiçbir seçenek hedefe ulaşmadı** (`choice = null`). Kat eklemek kütleyle doyuyor (4/1 279 Hz, 5/1 281 Hz, 6/1 281 Hz, kütle +0,12 / +0,24 / +0,35 kg yarı kanat başına); en verimli kaldıraç ara kaburga aralığı (3/1'de 86 → 43 mm: 273,0 → 285,1 Hz, yalnız +0,018 kg/yarı).

Seçilen **s41r043w1**: kabuk 4/1 kat + 43 mm kaburga aralığı + web'e +1 ±45 kat. İnce ağ sonuçları: f_1T **294,9 Hz** dolu / **301,8 Hz** boş (taban 272,5 / 280,9), V_F ≈ **1266 km/h** (1080 km/h gereksinime %17 pay; 1350'ye ulaşılamadı), ek kütle ≈ +0,28 kg toplam, kesit CG 0,451c → 0,428c, Tsai-Wu R_min 4,23, 18 g uç sehim 42,3 mm. Seçenek tablosunun tamamı [doküman 04 §15.2](04_yapi_flutter.md)'dedir. Seçim `params.py`'ye (`WING`: `skin_plies=(4,1)`, `rib_pitch=0.043`, `web_extra_plies=1`) işlendi; kanat kütle kalemi 2,03 kg, MTOW 17,16 → 17,44 kg, statik marj %13,0-32,8.

**İnceleme sonrası düzeltildi (çapraz inceleme, 9 FEM bulgusu):** ilk çalışmada seçilen ince ağda sandviç çakışması (−0,17 mm) ve 160 uyumsuz kaburga–web kenarı inceleme kapısından kaçmıştı (çakışma bayrağı zorunlu değildi, inceleme başarısızlığı yok sayılıyordu); yeniden koşuda web/kaburga ek kütlesi iki kez sayılacaktı; flutter ölçeği güncel (değişken) `fe_sonuclar.json`'a bağlıydı; varyantlar params'tan değer devralıyordu; 21,6 mm kaburga orta ağda fiilen 43 mm idi; CCX varsayılanı 4 iş parçacığıydı ve kanat kapısı kuponu önkoşul saymıyordu. Hepsi düzeltildi (bulgu tablosu: [`fem/RESULTS_iter5.md`](../fem/RESULTS_iter5.md) §9): 6 bayrak zorunlu ve başarısızlıkta zincir durur, monolitik burun/uç hücrelerinde kat geçişi, web ve kaburga aynı dikey bölüntü, tek yerde kütle sayımı, sabit iter4 flutter referansı (`fem/reference/fe_sonuclar_iter4_v0.5.0.json`, SHA256 933f5d7d…), temsil edilemeyen kaburga aralığı reddedilir, CCX vakalarında tek iş parçacığı (provenance'a yazılır), kanat önkoşulu konsol + kupon. Konsol ve kupon benchmarkları yeniden BENCHMARK_ACCEPTED. Düzeltilmiş modelle s31, s31r043, s41r043, s41r043w1, s51r043w1 orta ve ince ağda, dolu/boş tankta çözüldü (inceleme 6/6): seçilen s41r043w1 f_1T **295,2 Hz** dolu / **302,2 Hz** boş (orta ağ 295,5 / 304,2; tam yükseklik web/kaburga tanılamasıyla fark %0,02), V_F **≈1267 km/h** dolu / 1271 km/h boş, Tsai-Wu R 4,16, uç sehim 43,0 mm (MTOW 17,44 kg yüküyle), ek kütle +0,143 kg/yarı (eski değerler 294,9 / 301,8 Hz, 1266 km/h, 4,23, 42,3 mm). Web+0 (s41r043) 1,4 Hz düşük ve yalnız 6,6 g/yarı hafif; **seçim değişmedi**, params ve 2,03 kg kanat kalemi aynı. 316 Hz'e yine hiçbir varyant ulaşmıyor (en yakın s51r043w1 300,0 Hz). GVT kriteri (≥ 230 Hz) %28 payla sağlanıyor. Yukarıdaki ilk çalışma sayıları tarihsel kayıttır.

**1D modelin sınırı:** yeni kat planıyla `fe_modal` dolu tankta 1813 km/h (boşta 1656) verir ve V_F(f_T) eğrisi düz kalır (kritik mod değişti); bu sonuç güvenilmez ve iyimserdir. Flutter tasarım değeri kabuk-FEM ölçekli ≈1267 km/h'dir (inceleme sonrası düzeltildi, eski ≈1266).

### 10.7.4 FEM için kalan açıklar

1. Kaburga yerleşimi/laminatı ve menteşe web'i imalat tanımıyla doğrulanmalı (f_1T'ye birinci derece etki).
2. Kabuk mod şekilleriyle p-k flutter (güçlü eğilme-burulma bağlaşımı, düzlem içi mod) kurulmalı; 1267 km/h yalnız frekans ölçeklemesidir.
3. Malzeme üretici/kupon verisi (E1 125 vs 135 GPa, kumaş G12, dayanımlar, sıcak-nem), B-basis allowable.
4. Burkulma, çekirdek kayması/kırışma (zigzag gerekir), yapıştırıcı ve kök cıvata hattı; kök bölmesi Tsai-Wu ve çekirdek kayması yakınsamadı.
5. GVT: kabul kriteri f_1T ≥ 230 Hz korunur; kabuk tasarım hedefi ≈295 Hz ve üstü (model dolu 295,2 Hz; inceleme sonrası düzeltildi, eski 294,9 Hz).
6. `validation/study.py` kayıt bütünlüğü cfd/*.py dahil runner kaynaklarının SHA'sını tuttuğundan paralel CFD değişiklikleri bu çalışmaları "STALE" yapabilir; entegrasyondan önce `run_case.py cantilever/coupon --study --threads 1` ve `fem/run_wing_study.py` yeniden koşulmalı.
