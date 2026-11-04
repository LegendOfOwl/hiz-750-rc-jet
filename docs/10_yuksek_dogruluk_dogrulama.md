# 10 — İter5 / v0.6 yüksek doğruluk doğrulaması

**İkinci tur: kısmi doğrulama tamamlandı.** Araçları Claude host üzerinde kurdu; escalation ile Python/solver çalıştırıldı. Konsol ve 1B termal üç ağda kabul aldı; altı koşullu motor termal senaryosu çözüldü. CFD pilotları yakınsamadı veya hata verdi. İlk turun sandbox engeli [tarihsel yoklamada](../validation/results/machine_probe.json) korunur; güncel kurulum [installation.json](../validation/results/installation.json) içindedir. CFD doğrulaması tamamlanmış sayılmaz.

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
| RAE2822 SA | CL, CD, Cp RMSE | bekliyor | bekliyor | bekliyor | deney verisi de bekliyor | bekliyor |
| RAE2822 SST | CL, CD, Cp RMSE | bekliyor | bekliyor | bekliyor | deney verisi de bekliyor | bekliyor |
| Düz levha SA | Cf_mean | bekliyor | bekliyor | bekliyor | bekliyor | bekliyor |
| Düz levha SST | Cf_mean | bekliyor | bekliyor | bekliyor | bekliyor | bekliyor |

**Konsol:** 1×.05×.01m, E210GPa, rho7800kg/m³, uçta1N. Euler–Bernoulli sehim ve f1, ayrıca reaksiyon dengesi. S8R ağlar10×2/20×4/40×8. [CalculiX kılavuzundaki](https://www.dhondt.de/ccx_2.22.pdf) composite desteği S8R/S6 içindir. **CLT laminat coupon benchmarkı tamamlanmadı**; konsolun doğru çıkması kompozit tabaka yönlerini doğrulamaz.

**Termal:** 100mm, k10W/(m K), bir yüzde100°C, diğer yüzde h25W/(m² K)/20°C ortam; 4/8/16DC3D8. Analitik `q''=(Th−T∞)/(L/k+1/h)`, `T(x)=Th−q''x/k`. DC3D8 bu lineer profili tam temsil edebilir. Üç ağ farkı yuvarlama düzeyindeyse p/GCI yerine **EXACT_OR_ROUNDOFF** yazılır. Bu beklenen özellik, çalıştırılmış ccx kanıtı değildir.

| Vaka | Büyüklük | Kaba | Orta | İnce | Analitik hata [%] | p / GCI ince |
|---|---|---|---|---|---|---|
| Konsol S8R | sehim [mm] / f1 [Hz] | .3734951 / 8.492973 | .3768355 / 8.442452 | .3781402 / 8.422987 | −.7382 / +.4902 (ince) | p1.3563/GCI%.2764; p1.3760/GCI%.1811 |
| 1B iletim+taşınım | Tsoğuk [K] / q'' [W/m²] | 357.15 / 1600 | 357.15 / 1600 | 357.15 / 1600 | 0 / 0 | EXACT_OR_ROUNDOFF; p/GCI tanımsız |
| Kompozit CLT coupon | ABD / sehim / f1 | uygulanmadı | uygulanmadı | uygulanmadı | yok | yok |

Richardson/GCI, üç ağda monoton yakınsama ve aynı problem tanımı gerektirir: `Fs=1.25`, her h oranı≥1.3. Eşit olmayan oranlar çözülür; salınım veya sıfır fark zorla p=2'ye çevrilmez. `h∝N^(-1/d)` yalnız tutarlı ağ ailesinde anlamlıdır; duvar/alan boyutları birlikte rafine edilir. Şok veya mod sırası değişiminde p/GCI yorumu sınırlandırılır. İterasyon/ağ yakınsaması, deneyle anlaşma ve fiziksel tasarım kabulünden ayrıdır.

## 10.3 HIZ-750 karşılaştırması

Eski sayılar depodaki JSON'lardan okunmuştur; burada tekrar hesaplanmadı. `validation/report.py` bunların SHA256'sini saklayıp yeni sonuçlarla yan yana yazar. Yeni sonuç gelmeden hata veya iyileşme yüzdesi yoktur.

| Uygulama | Mevcut yarı-ampirik değer | İter5 sonucu | Engel / sınırlama |
|---|---|---|---|
| A / profil, Re4.5e6 | NeuralFoil M0: Cd0=.0035074; Clα=6.06675/rad; Cm0≈0 | bekliyor: cl/cd/cm, SA–SST, sonik Cp | solver/RAE deney kabulü |
| B / uçak, 750km/h,300m | AeroBuildup154.353N / sizing yaklaşık210N | bekliyor: D, basınç/sürtünme payı, GCI | temiz fluid hacmi + prizmatik duvar ağı |
| C / S-kanal | η_r=.970955; DC60 yok | bekliyor: recovery/DC60/debi | dış gövde BL yutulmalı; duvar STEP'i fluid değil |
| D / dolu kanat | 1B27.459Hz, 1T305.677Hz; flutter1307.484km/h | bekliyor: sehim/S/FI/ilk5 mod | imalat detayları/katman doğrulaması ve host koşusu |
| E / motor | kabuk sıcaklığı ölçülmedi; Tg≥150°C hedefi | bekliyor: Tkabuk/keçe | k/h/ε, bypass ve açıklık |

**A:** RANS, `aero/aero_analysis.py` ile aynı kalınlığı ölçeklenmiş64A010 koordinatını kullanır. Gerçek64A007'ye geçmek ayrı geometri duyarlılığıdır. α0/1/2°, M.61/.65/.70/.725/.75 ve iki model taranmalı. Matched-Mach NeuralFoil ile eski M0 ayrı saklanır. Tam türbülans RANS ve NeuralFoil ncrit9 geçiş varsayımı cd farkının model bütçesindedir. İlk sonik Mach, Mcrit için üst sınırdır; kesin Mcrit veya drag divergence sonucu değildir.

**B:** aynı300m ISA, CL/trim, yüzey ve bileşen seti eşleştirilmeli. Referans alanS/2, yarı kuvvet×2. İç aksam/dolly çıkarılır; alık/egzozun kapalı/açık ya da motorlu seçimi raporlanır. Sade zarf D'si, alık/kızak/girişim paylarını içeren AeroBuildup ile aynı kapsam değildir. 154–210N farkı210N'e göre yaklaşık%26.5,154N'e göre yaklaşık%36'dır; paydasız “%25 hata” denmemeli. 3B tetra ön ağ otomatik olarak doğru RANS ağı sayılmaz.

**C:** debi `ENGINE.mdot_air × σ × (1+.6M²)` ve tam motor yüzünde FAN_FACE_MDOT. Uniform girişli kapalı kanal η_r=.971'in sınır tabaka yutma kısmını sınamaz. ENGINE örneklerinde recovery kütle/alan ağırlıklı ayrı; DC60 sektör alan ortalaması ve `q=0.5rho u_n²` ile hesaplanır. Ters akış/eksik disk örneklemesinde postprocess durur. Motor distorsiyon limiti verilmediğinden fiziksel kabul yazılamaz. Ayrıntılar [CFD notunda](../cfd/README.md).

**D:** [FEM notu](../fem/README.md) kat planını ve tam malzeme tablosunu verir. Depodaki UD E1=125GPa/Xt2100MPa, kumaş E55GPa/t.178mm/rho ve kayma izinleri önceliklidir; eksikler görevde verilen tipik değerlerle **varsayım (üretici verisiyle değiştirilecek)** olarak tamamlandı. FAB.G45=25GPa ile lamina G12=4.5GPa farklıdır. Rohacell E70MPa/G19MPa tek izotropik ν ile uyumlu olmadığı için ortotropik yaklaşık sabitler kullanıldı. F12 etkileşim katsayısı ölçülmedi. Bunlar hot/wet allowables değildir.

Kabuk taslağı; ince burun/TE sandviç birleşmesi, kontrol yüzeyi kesikleri, rib/cıvata esnekliği ve servo/yakıt ataleti düzeltilmeden üretim modeli değildir. Torsion indicator ön taramadır; mod şekliyle1B/1T eşleştirilmelidir. Tsai–Wu lokal tabaka CSV'sinden hesaplanabilir; CCX integration-point/tabaka eşleştirmesi kontrol edilmeden otomatik çevrilmedi. Ham FI ve KD=.544 dayanım duyarlılığı ayrıdır; KD doğrulanmış B-basis veri değildir. Buckling/debonding ve bağlantılar ayrıca incelenir.

**f1T→flutter:** sabit ataletle `GJ_yeni/GJ_eski≈(f1T_yeni/305.677)²` yalnız rijitlik taramasıdır. Örneğin ileride250Hz ölçülmesi yaklaşık.669 GJ oranına işaret eder; **FEM sonucu değildir**. Flutter hızı aynı oranla çarpılamaz: kritik3B–1T eşleşmesi, CG, mod şekli ve aerodinamik bağlaşım değişir. Yeni modal bazla aeroelastik çözüm kurulmalı. Eski1307km/h ayrıca transonik bölgede sınırlandırılmış PG düzeltmesine dayanır; statik RANS dinamik flutter doğrulaması değildir. GVT kriteri yalnız **alt frekans sınırıdır**; taramanın üst ucundan fiziksel kabul bandı çıkarılmaz.

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
| Yapı | E/G/ν/strength, core, bağ, kütle/CG, modal baz | tipik değerler; CLT coupon/GVT yok |
| Isıl | h/k/ε/gap, görüş faktörü/heat soak | ölçüm yok; koşullu senaryolar |
| Türbin | Vj/k_ram/ṁ ve distorsiyona tepki | recovery tek başına itki kalibrasyonu değildir |

Bağımsız normal dağılımlar varsayılmadı; bu kalemler körlemesine RSS ile bir güven yüzdesine çevrilmez. GCI, fiziksel model hatasının küçük olduğunu göstermez.

**Şimdiden gerekli öneri:** nominal8.5mm açıklıkla termal tasarım dondurulmasın. `cad_report.json` ön6.8mm ve minimum**5.97mm** veriyor; dış çap farkı kabuk kalınlığı düşülmeden iç açıklık değildir. Keçe/bypass için en küçük gerçek kesit kullanılmalı. `params.py` değiştirilmedi.

**Sonuç bekleyen kararlar:**

1. D ve η_r doğrulanana kadar itki payı/azami hız doğrulanmış ilan edilmesin; türbin yer/uçuş ölçümü gerekir.
2. İmalat katları/kontrol boşlukları ve frekanslar eşleştirilmeden mevcut flutter marjına dayanarak kat azaltılmasın. GVT öncesi kısıtlar gevşetilmesin.
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

Kanat kaba taslağı224 S8R/694 düğüm, açılmış DOF tahmini6246; çözülmedi. Uçak ön ağı5885, izole kanal ön ağı4727 tetra. Uçakta konik/silindirik gövde ve dörtgen kanat/kuyruk, kanalda CAD rapor kesitlerinin16 kenarlı yaklaşımı kullanıldı. Yalnız DRAFT/topoloji kontrolüdür: prizmatik BL yok, kanal dış gövde BL yutulmasını içermez. D ve η_r sonucu üretilmedi.
