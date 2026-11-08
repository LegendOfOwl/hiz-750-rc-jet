# 10 — İter5 / v0.6 yüksek doğruluk doğrulaması

**v0.6.0 · 2026-11-06, CFD/termal kısmı 2026-11-08 incelemesiyle güncellendi.** Düz levha SA üç ağda BENCHMARK_ACCEPTED (p 0,434; düşük p nedeniyle Fs=3 ile ince GCI %1,82, eski Fs=1,25 değeri %0,88). RAE2822 iz kesiti ağı düzeltildi, kaba ağ proje kapısını geçti (CL −%3,07, CD −%0,75, Cp RMSE 0,098 > 0,08); orta/ince ağ 2 saatlik koşu sınırında tamamlanamadı (BLOCKED), üç ağ çalışması PENDING. Konsol önceki host koşusunda kabul aldı. `thermal_1d` 2026-11-08'de yeniden koşuldu ve BENCHMARK_ACCEPTED; altı koşullu motor termal senaryosu yeniden çözüldü, sayılar değişmedi. İlk turun sandbox engeli [tarihsel yoklamada](../validation/results/machine_probe.json), araç kurulum kaydı [installation.json](../validation/results/installation.json) içindedir.

CLT kupon benchmarkı kabul edildi (BENCHMARK_ACCEPTED), kompozit kanat kabuk modeli çözüldü (REVIEW_REQUIRED) ve kanat rijitleştirilerek `params.py` güncellendi. İnceleme sonrası s41r043w1 sonucu f_1T 295,2 / 302,2 Hz ve ölçekli flutter ≈1267 / 1271 km/h (dolu / boş), toplam ek kütle +0,285 kg, Tsai-Wu R 4,16, uç sehim 43,0 mm (§10.7). 316 Hz hedefine ulaşılamadı.

İter5 params ve analiz çıktıları yenilendi. Tarihsel karşılaştırma `v0.5.0` Git içeriklerine sabitlendi, güncel dosyaların hash'leri ayrıca kaydedildi. Bu kapanış oturumunda Python erişim engeli nedeniyle regresyon testleri ve çözücü yeniden koşumları yapılamadı. Hash karşılaştırmasında düz levha, konsol ve kupon kayıtlarının kaynakları farklı, yeniden değerlendirmede STALE sonucu bekleniyor. Bu dokümandaki kabul ifadeleri kayıtlı koşulara aittir. [Kurulum ve komutlar](../validation/README.md).

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

**RAE2822 Case6** M=.729, Re=6.5e6, α=2.31°, T=288.15K, adyabatik no-slip duvar. Ham tünel M=.725/α=2.92° ile düzeltilmiş hesap koşulları ayrı tutulur. NASA NPARC Cp referansı üst dalda 54, alt dalda 50 noktayla yeniden üretildi, kaynak −Cp işareti dönüştürüldü ve hash'ler kaydedildi. CL/CD ikincil kaynak, deney belirsizliği belirsiz. Resmi SU2 ağı+cfg çözücü kontrolü kabul aldı, Cp RMSE 0,0984 > 0,08 nedeniyle deneysel Cp kabulü açık. [CFD kaynak ve koşu kaydı](../cfd/RESULTS_iter5.md).

**Düz levha:** [NASA TMR](https://tmbwg.github.io/turbmodels/flatplate.html) koşullarına benzer M=.2, Re_x=5e6 @1m, L=2m. Tam türbülanslı ortalama Cf, Schlichting ve ITTC ile karşılaştırılır. Bu ağ/BC TMR'nin birebir replikası değildir; korelasyon farkı tek başına deney doğrulaması sayılmaz. ONERA M6 ve ayrıca deneysel S-kanal benchmarkı eklenmedi.

| Vaka / model | Büyüklük | Kaba | Orta | İnce | Referansla hata [%] | p / GCI ince |
|---|---|---|---|---|---|---|
| RAE2822 SA | CL, CD, Cp RMSE | .72018 / .012605 / .0982 (v3 iz ağı, MG0, 4292 iter, kapı geçti) | BLOCKED (süre; 7765 iter, ν̃ düşüşü 3.62/4; CL .7275, CD .01247) | BLOCKED (süre; 4384 iter, ν̃ düşüşü 1.31/4) | CL −3.07, CD −0.75 (kaba); Cp RMSE > .08 | PENDING (§10.6.2) |
| RAE2822 SST | CL, CD, Cp RMSE | bekliyor | bekliyor | bekliyor | NASA Cp mevcut, SST karşılaştırması bekliyor | bekliyor |
| Düz levha SA | Cf_mean | .0028542517 | .0028586462 | .0028613266 | Schlichting −4.74, ITTC −4.62 (ince) | p .434 (kullanılan .5, Fs 3) / GCI %1.82 — BENCHMARK_ACCEPTED (iter5 v3 yeniden koşu, §10.6.2) |
| Düz levha SST | Cf_mean | bekliyor | bekliyor | bekliyor | bekliyor | bekliyor |

**Konsol:** 1×.05×.01m, E210GPa, rho7800kg/m³, uçta1N. Euler–Bernoulli sehim ve f1, ayrıca reaksiyon dengesi. S8R ağlar10×2/20×4/40×8. [CalculiX kılavuzundaki](https://www.dhondt.de/ccx_2.22.pdf) composite desteği S8R/S6 içindir. Konsolun doğru çıkması kompozit tabaka yönlerini tek başına doğrulamaz; **CLT laminat kupon benchmarkı iter5'te tamamlandı ve kabul edildi** (§10.7.1, en büyük hata %1,12).

**Termal:** 100mm, k10W/(m K), bir yüzde100°C, diğer yüzde h25W/(m² K)/20°C ortam; 4/8/16DC3D8. Analitik `q''=(Th−T∞)/(L/k+1/h)`, `T(x)=Th−q''x/k`. DC3D8 bu lineer profili tam temsil edebilir. Üç ağ farkı yuvarlama düzeyindeyse p/GCI yerine **EXACT_OR_ROUNDOFF** yazılır. Bu beklenen özellik, çalıştırılmış ccx kanıtı değildir.

| Vaka | Büyüklük | Kaba | Orta | İnce | Analitik hata [%] | p / GCI ince |
|---|---|---|---|---|---|---|
| Konsol S8R | sehim [mm] / f1 [Hz] | .3734951 / 8.492973 | .3768355 / 8.442452 | .3781402 / 8.422987 | −.7382 / +.4902 (ince) | p1.3563/GCI%.2764; p1.3760/GCI%.1811 |
| 1B iletim+taşınım (2026-11-08 yeniden koşu) | Tsoğuk [K] / q'' [W/m²] | 357.15 / 1600 | 357.15 / 1600 | 357.15 / 1600 | 0 / 0 | EXACT_OR_ROUNDOFF; p/GCI tanımsız; BENCHMARK_ACCEPTED |
| Kompozit CLT kupon (5 laminat) | Ex, Ey, Gxy, D11, 3N sehim, tabaka σ | membran 4/8/16², B3 8/16/32×4/8/16 | (üç ağ) | (üç ağ) | en büyük \|hata\| %1,12 (< %2) | BENCHMARK_ACCEPTED; GCI ≤ %5, ayrıntı §10.7.1 (iter5 ile güncellendi) |

Richardson/GCI, üç ağda monoton yakınsama ve aynı problem tanımı gerektirir: `Fs=1.25`, her h oranı≥1.3. CFD vakalarında gözlenen p formal mertebe 2'den %10'dan fazla saparsa `p_kullanılan=min(max(.5,p),2)` ve `Fs=3` kullanılır (Roache; Oberkampf & Roy 2010). Eşit olmayan oranlar çözülür; salınım veya sıfır fark zorla p=2'ye çevrilmez. `h∝N^(-1/d)` yalnız tutarlı ağ ailesinde anlamlıdır; duvar/alan boyutları birlikte rafine edilir. Şok veya mod sırası değişiminde p/GCI yorumu sınırlandırılır. İterasyon/ağ yakınsaması, deneyle anlaşma ve fiziksel tasarım kabulünden ayrıdır.

## 10.3 HIZ-750 karşılaştırması

Tarihsel sayılar `git show v0.5.0:<yol>` JSON içeriklerinden alınır. `validation/report.py` bu byte'ların SHA256'sini baseline'a, güncel dosyaların hash'lerini ayrı `current` alanına yazar. Aşağıdaki karşılaştırmanın referansı v0.5.0'dır.

| Uygulama | v0.5.0 yarı-ampirik değer | İter5 sonucu | Engel / sınırlama |
|---|---|---|---|
| A / profil, Re4.5e6 | NeuralFoil M0: Cd0=.0035074; Clα=6.06675/rad; Cm0≈0 | bekliyor: cl/cd/cm, SA–SST, sonik Cp | solver/RAE deney kabulü |
| B / uçak, 750km/h,300m | AeroBuildup154.353N / sizing yaklaşık210N | bekliyor: D, basınç/sürtünme payı, GCI | temiz fluid hacmi + prizmatik duvar ağı |
| C / S-kanal | η_r=.970955; DC60 yok | bekliyor: recovery/DC60/debi | dış gövde BL yutulmalı; duvar STEP'i fluid değil |
| D / dolu kanat | 1B27.459Hz, 1T305.677Hz; flutter1307.484km/h | düzeltilmiş s41r043w1, 4/1 + 43 mm + web+1; 1T 295,2 Hz, flutter ≈1267 km/h, ek kütle +0,285 kg toplam, Tsai-Wu R 4,16, uç sehim 43,0 mm (§10.7) | REVIEW_REQUIRED; 316 Hz hedefi sağlanmadı, malzeme varsayım, kabuk mod şekilleriyle p-k açık |
| E / motor | kabuk sıcaklığı ölçülmedi; Tg≥150°C hedefi | tarihsel koşullu sonuçlar §10.6; 5,97 mm, yer/bypass yok, 2 mm keçeyle 126,10°C | thermal_1d STALE; k/h/ε ölçülmedi, fiziksel kabul açık |

**A:** RANS, `aero/aero_analysis.py` ile aynı kalınlığı ölçeklenmiş64A010 koordinatını kullanır. Gerçek64A007'ye geçmek ayrı geometri duyarlılığıdır. α0/1/2°, M.61/.65/.70/.725/.75 ve iki model taranmalı. Matched-Mach NeuralFoil ile eski M0 ayrı saklanır. Tam türbülans RANS ve NeuralFoil ncrit9 geçiş varsayımı cd farkının model bütçesindedir. İlk sonik Mach, Mcrit için üst sınırdır; kesin Mcrit veya drag divergence sonucu değildir.

**B:** aynı300m ISA, CL/trim, yüzey ve bileşen seti eşleştirilmeli. Referans alanS/2, yarı kuvvet×2. İç aksam/dolly çıkarılır; alık/egzozun kapalı/açık ya da motorlu seçimi raporlanır. Sade zarf D'si, alık/kızak/girişim paylarını içeren AeroBuildup ile aynı kapsam değildir. 154–210N farkı210N'e göre yaklaşık%26.5,154N'e göre yaklaşık%36'dır; paydasız “%25 hata” denmemeli. 3B tetra ön ağ otomatik olarak doğru RANS ağı sayılmaz.

**C:** debi `ENGINE.mdot_air × σ × (1+.6M²)` ve tam motor yüzünde FAN_FACE_MDOT. Uniform girişli kapalı kanal η_r=.971'in sınır tabaka yutma kısmını sınamaz. ENGINE örneklerinde recovery kütle/alan ağırlıklı ayrı; DC60 sektör alan ortalaması ve `q=0.5rho u_n²` ile hesaplanır. Ters akış/eksik disk örneklemesinde postprocess durur. Motor distorsiyon limiti verilmediğinden fiziksel kabul yazılamaz. Ayrıntılar [CFD notunda](../cfd/README.md).

**D:** [FEM notu](../fem/README.md) kat planını ve tam malzeme tablosunu verir. Depodaki UD E1=125GPa/Xt2100MPa, kumaş E55GPa/t.178mm/rho ve kayma izinleri önceliklidir; eksikler görevde verilen tipik değerlerle **varsayım (üretici verisiyle değiştirilecek)** olarak tamamlandı. FAB.G45=25GPa ile lamina G12=4.5GPa farklıdır. Rohacell E70MPa/G19MPa tek izotropik ν ile uyumlu olmadığı için ortotropik yaklaşık sabitler kullanıldı. F12 etkileşim katsayısı ölçülmedi. Bunlar hot/wet allowables değildir.

Kabuk taslağı; ince burun/TE sandviç birleşmesi, kontrol yüzeyi kesikleri, rib/cıvata esnekliği ve servo/yakıt ataleti düzeltilmeden üretim modeli değildir. Torsion indicator ön taramadır; mod şekliyle1B/1T eşleştirilmelidir. Tsai–Wu lokal tabaka CSV'sinden hesaplanabilir; CCX integration-point/tabaka eşleştirmesi kontrol edilmeden otomatik çevrilmedi. Ham FI ve KD=.544 dayanım duyarlılığı ayrıdır; KD doğrulanmış B-basis veri değildir. Buckling/debonding ve bağlantılar ayrıca incelenir.

f_1T ile flutter taraması, sabit ataletle `GJ_yeni/GJ_eski≈(f1T_yeni/305.677)²` rijitlik yaklaşımını kullanır. Kritik 3B–1T eşleşmesi, CG, mod şekli ve aerodinamik bağlaşım değişebilir. Düzeltilmiş s41r043w1 için f_1T 295,2 / 302,2 Hz, sabit iter4 eğrisi üzerindeki ölçekli V_F ≈1267 / 1271 km/h'dir (dolu / boş). Kabuk mod şekilleriyle p-k çözümü açık. GVT kabul ölçütü f_1T ≥ 230 Hz alt sınırıdır (§10.7).

**E:** motor150–250°C, keçe0–3mm, bypass h0/15/50, emissivite.1/.7/.9 ve yer/uçuş dış taşınımı taranmalı. Model yerel1B kararlı iletim+taşınım+ışınımdır; 3B termal/CHT değildir. Bağımsız skaler enerji dengesi aynı BC'yi kontrol eder, h/ε'nin gerçek olduğunu kanıtlamaz. Keçe açıklığı/soğutma debisini azaltabilir. Tg150°C, sürekli servis sıcaklığı izni değildir; üretici hot/wet ve sıcaklıkta dayanım değerleri gerekir. [Termal not](../thermal/README.md).

## 10.4 LES/DES maliyeti

GPU yokluğu tek başına engel değildir;3B çözünürlük ve zaman ortalaması asıl maliyettir. ν≈1.5e−5m²/s ve uτ≈5–10m/s mertebesinde y+1 için ilk mesafe birkaç mikrometredir. Δx+50–100 ve Δz+15–30, metre kare mertebesindeki yüzey ve normal katmanlarla kabaca **10^8–10^10 hücre** gerektirebilir. Bu HIZ ağ sayımı değil büyüklük tahminidir; [Choi–Moin LES grid ölçeklemesi](https://doi.org/10.1063/1.3676783) yüksek Reynolds maliyetini açıklar.

Örnek maliyet (ölçüm değil): N=10^8, Δt=1e−6s,0.5s fiziksel süre, adımda10 iç iterasyon, hücre güncellemesi1e−7s varsayımıyla `N×(0.5/Δt)×10×1e−7≈5e7s`, yaklaşık579gün. 200–1000byte/hücre ile bu düşük N bile20–100GB, daha büyük ağlar TB ölçeğindedir. CPU paralelleşmesi azaltabilir. Bu makinede ölçülen 2B hız (seri SU2 8.2.0, yük yokken): 33792 hücre ≈0.24 s/iterasyon, yani ≈7e−6 s/hücre/iterasyon; 3B'de daha yüksektir. Kurulu SU2 seri (MPI'sız) olduğundan 2M hücrelik 3B RANS bile 30–40 s/iterasyon, binlerce iterasyonla günler sürer; 3B iş öncesinde MPI sürümü gerekir. DDES duvar maliyetini azaltır, fakat ayrılmış alık/wake için3B çözünürlük ve çok sayıda zaman adımı gerekir;≤2M bütçesiyle güvenilir DES iddia edilmez.

2B zamana bağlı SA/SST, URANS'tır;3B türbülans kaskadını çözen LES değildir. “Quasi-LES” animasyonu doğrulama kanıtı diye üretilmedi. CPU bütçesi önce doğrulanmış2B ve sınır katmanlı kaba-orta3B RANS'a ayrılır.

## 10.5 Belirsizlik bütçesi ve kararlar

| Kalem | Bütçe yöntemi | Şimdiki durum |
|---|---|---|
| İteratif/ağ | residual+kuvvet/ısı dengesi, üç ağ GCI | düz levha SA ince GCI %1,82 (Fs 3); RAE kaba kapı geçti, üç ağ GCI bekliyor; seçilen kanatta iki ağ farkı, üç ağ GCI yok |
| CFD model formu | SA–SST, geçiş/pürüzlülük, domain | fark bilinmiyor; ortak RANS yanlılığı kapsanmaz |
| Geometri/trim | profil, alık/kızak/motor, aynı CL | B/C topoloji/ağ hazırlığı |
| Deney | AGARD koşulları, Cp digitizasyonu/tünel düzeltmesi | NASA Cp mevcut, CL/CD ikincil; deney belirsizliği belirsiz, Cp kabulü açık |
| Yapı | E/G/ν/strength, core, bağ, kütle/CG, modal baz | tipik değerler; CLT kupon kabul (iter5), GVT yok |
| Isıl | h/k/ε/gap, görüş faktörü/heat soak | ölçüm yok; koşullu senaryolar |
| Türbin | Vj/k_ram/ṁ ve distorsiyona tepki | recovery tek başına itki kalibrasyonu değildir |

Bağımsız normal dağılımlar varsayılmadı; bu kalemler körlemesine RSS ile bir güven yüzdesine çevrilmez. GCI, fiziksel model hatasının küçük olduğunu göstermez.

Termal açıklık için `cad_report.json` ön 6,8 mm ve minimum **5,97 mm** veriyor. Keçe/bypass hesabı en küçük gerçek kesitle eşleştirilmeli. `thermal_1d` 2026-11-08'de yeniden koşuldu (BENCHMARK_ACCEPTED); motor termal senaryoları aynı sayıları verdi.

**Sonuç bekleyen kararlar:**

1. D ve η_r doğrulanana kadar itki payı/azami hız doğrulanmış ilan edilmesin; türbin yer/uçuş ölçümü gerekir.
2. Kat planı 4/1, kaburga 43 mm, web +1 kat ile düzeltilmiş flutter tasarım değeri ≈1267 km/h. 1350 km/h payı sağlanmıyor. İmalat katları, kontrol boşlukları ve frekanslar GVT ile eşleştirilmeli (§10.7.3).
3. Kabuk içi/keçe altı termokupl, motor yüzeyi ve stop sonrası heat soak kaydı alınsın; reçine/keçe sıcaklıkta izin değerleriyle seçilsin.
4. RAE iz kesiti ağı düzeltildi ve kaba ağ kapıyı geçti; orta/ince, Cp RMSE ölçüt tanımı (ön kenar deney noktası, §10.6.2), SA–SST ve profil taraması tamamlanınca sonuç, hata ve GCI tabloları güncellenmeli.

Paket deney düzenini ve izlenebilir engel kayıtlarını kurar. Host koşuları ve fiziksel model incelemesi bitmeden yüksek doğruluk doğrulaması tamamlanmış değildir.

## 10.6 İkinci tur gerçek koşuları (tarihsel)

Tam hata tabloları: [konsol](../validation/results/cantilever/study.md), [1B termal](../validation/results/thermal_1d/study.md). Python regresyonları13/13 ve compileall geçti. Gerçek koşularla CalculiX'in sayı alanı, Lednicer/Selig sırası, sıfır kaliteli düz levha köşeleri ve SU2 yardımcı Buffet NaN çıktısı düzeltildi. Fiziksel NaN ve yakınsama ölçütleri gevşetilmedi.

İlk turdaki RAE2822 ve profil pilotları UNCONVERGED kaldı. Kendi düz levha ağındaki ilk denemelerde salınım veya FGMRES hatası görüldü. Daha sonraki düz levha kabulü ve yeniden üretilen NASA Cp referansı §10.6.1'de kayıtlıdır.

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

### 10.6.2 İter5 v3 CFD (2026-11-08 incelemesi): iz kesiti ağı, GCI ve STALE kuralları

Ayrıntı: [cfd/RESULTS_iter5.md](../cfd/RESULTS_iter5.md) son bölüm ve [inceleme raporu](../reviews/grup1_cfd_dogrulama.md).

**v2 RAE kaba koşusu:** 30000 iterasyon MG0 sonunda UNCONVERGED (ρ düşüşü 3.55, ν̃ düşüşü 0.30 < 4) ve kaynaklar sonradan değiştiği için STALE; arşivlendi.

**İz kesiti ağı:** v2'de iz kesitinin iki yanındaki hücreler 2e−6c kalınlığında, 0.004–15c uzunluğundaydı (en-boy 1e3–1e7). v3'te iz ilk aralığı TE'de duvar değerinden başlayıp iz hücresi başına en çok 1.5 kat büyüyerek ds/100'e gider ve duvar katman dizisine toplamsal olarak eklenir. Normal büyüme 1.18/1.12/1.09, min köşe sinüsü .655 (yalnız 100c çıkış yelpazesinde), hücre sayıları aynı.

**RAE kaba (v3):** resmi MG3 W-cycle hâlâ ıraksıyor (1590. iterasyon). MG0+CFL_ADAPT 4292 iterasyonda proje kapısını geçti: Cauchy100 4.0e−9, ρ/ν̃ düşüşü 7.82/4.18, y+max .81. CL .72018 (−%3.07), CD .012605 (−%0.75), Cm −.0886 (+%6.7), Cp RMSE .0982 (> .08). Cp RMSE'nin çoğu NASA verisindeki tek bir ön kenar noktasından geliyor (üst dal x/c=.0002, Cp −.42; komşuları +.10 ve +.83). x/c<.002 noktaları dışlanınca RMSE kendi ağımızda .048, resmi SU2 ağında .038 olur. Değerlendirme kümesi kabulü belirlediği için değiştirilmedi; karar incelemeye bırakıldı.

**RAE orta/ince:** aynı ayarla, paylaşılan makinede paralel koşuldu ve 7200 s sınırında BLOCKED oldu: orta 7765 iterasyonda Cauchy100 1.6e−8, ρ/ν̃ düşüşü 7.08/3.62 (kapıya çok yakın), ince 4384 iterasyonda 4.17/1.31. Üç ağ çalışması PENDING, GCI yok. Orta ağ makine boşken tek başına yeniden koşulmalı; ince ağ için restart'tan devam eden runner gerekir.

**GCI kuralı:** gözlenen p formal mertebeden %10'dan fazla saparsa p_kullanılan=min(max(.5,p),2), Fs=3. Düz levha üç ağ yeniden koşuldu (Cf bitwise aynı); ince GCI %0.88 → %1.82, BENCHMARK_ACCEPTED korunur.

**STALE kuralı:** kayıt yalnız vakanın çalışma anında import ettiği kaynaklar değişince eskir; testler, rapor araçları ve başka alanın dosyaları eskitmez; benchmarklar params ve uçak tasarım dosyalarına bağlanmaz. thermal_1d, cantilever ve coupon yeniden koşuldu (üçü de BENCHMARK_ACCEPTED, sayılar aynı); motor termal senaryoları aynı sayıları verdi.

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

**İlk çalışma (tarihsel).** Seçilen s41r043w1 için 294,9 / 301,8 Hz, ≈1266 km/h, Tsai-Wu R 4,23 ve uç sehim 42,3 mm raporlanmıştı. Güncel tasarım aşağıdaki inceleme sonrası düzeltilmiş sonuçlara dayanır. Seçim `params.py`'ye (`WING`, `skin_plies=(4,1)`, `rib_pitch=0.043`, `web_extra_plies=1`) işlendi. Kanat kütle kalemi 2,03 kg, MTOW 17,44 kg, statik marj %13,0–32,8. [Doküman 04 §15.2a](04_yapi_flutter.md).

**İnceleme sonrası düzeltildi (çapraz inceleme, 9 FEM bulgusu):** ilk çalışmada seçilen ince ağda sandviç çakışması (−0,17 mm) ve 160 uyumsuz kaburga–web kenarı inceleme kapısından kaçmıştı (çakışma bayrağı zorunlu değildi, inceleme başarısızlığı yok sayılıyordu); yeniden koşuda web/kaburga ek kütlesi iki kez sayılacaktı; flutter ölçeği güncel (değişken) `fe_sonuclar.json`'a bağlıydı; varyantlar params'tan değer devralıyordu; 21,6 mm kaburga orta ağda fiilen 43 mm idi; CCX varsayılanı 4 iş parçacığıydı ve kanat kapısı kuponu önkoşul saymıyordu. Hepsi düzeltildi (bulgu tablosu: [`fem/RESULTS_iter5.md`](../fem/RESULTS_iter5.md) §9): 6 bayrak zorunlu ve başarısızlıkta zincir durur, monolitik burun/uç hücrelerinde kat geçişi, web ve kaburga aynı dikey bölüntü, tek yerde kütle sayımı, sabit iter4 flutter referansı (`fem/reference/fe_sonuclar_iter4_v0.5.0.json`, SHA256 933f5d7d…), temsil edilemeyen kaburga aralığı reddedilir, CCX vakalarında tek iş parçacığı (provenance'a yazılır), kanat önkoşulu konsol + kupon. Konsol ve kupon benchmarkları yeniden BENCHMARK_ACCEPTED. Düzeltilmiş modelle s31, s31r043, s41r043, s41r043w1, s51r043w1 orta ve ince ağda, dolu/boş tankta çözüldü (inceleme 6/6): seçilen s41r043w1 f_1T **295,2 Hz** dolu / **302,2 Hz** boş (orta ağ 295,5 / 304,2; tam yükseklik web/kaburga tanılamasıyla fark %0,02), V_F **≈1267 km/h** dolu / 1271 km/h boş, Tsai-Wu R 4,16, uç sehim 43,0 mm (MTOW 17,44 kg yüküyle), ek kütle +0,285 kg toplam (yarı kanat tablosunda yuvarlanmış +0,143 kg; eski değerler 294,9 / 301,8 Hz, 1266 km/h, 4,23, 42,3 mm). Web+0 (s41r043) 1,4 Hz düşük ve yalnız 6,6 g/yarı hafif; **seçim değişmedi**, params ve 2,03 kg kanat kalemi aynı. 316 Hz'e yine hiçbir varyant ulaşmıyor (en yakın s51r043w1 300,0 Hz). Kabuk modeli GVT alt sınırının (≥ 230 Hz) %28 üzerinde, fiziksel GVT bekliyor. Yukarıdaki ilk çalışma sayıları tarihsel kayıttır.

**1D modelin sınırı (Grup 1 incelemesiyle düzeltildi):** `fe_modal`'ın 1813 km/h (boşta 1656) sonucu ve düz V_F(f_T) eğrisi bir kod hatasıydı: flutter çözümü ilk 4 modu alıyordu, 4/1 kat planında dolu tankta 1T beşinci moddur (327,3 Hz) ve çözüme girmiyordu. Mod kümesi en az 8 mod / 2 burulma moduna çıkarıldı ve iz-takipsiz p-k kontrolü eklendi; düzeltilmiş 1D sonuç dolu 1452 / boş 1544 km/h. **Kabuk mod şekilleriyle p-k** (`fem/shell_flutter.py`, `fem/results/shell_flutter.json`; dönüşüm 1D modlarla %0,01 içinde sınandı): seçilen s41r043w1 dolu 1326 / boş 1324 km/h, 3/1 tabanda 1174 / 1169 km/h (f_1T-ölçekli 1185 / 1194). Ölçekleme 3/1'de tutarlı, seçilen tasarımda %4–5 muhafazakâr (CG kayması yok sayılıyor). Flutter tasarım değeri muhafazakâr olarak kabuk-FEM ölçekli ≈1267 km/h bırakıldı; 1350 km/h için kabuk p-k ile f_1T ≈ 301 Hz (dolu) / 308 Hz (boş) yeterli. Bu değerler yalnız kanadındır; kuyruk/gövde/kumanda bağlaşımı açık (doküman 04 §15.3).

### 10.7.4 FEM için kalan açıklar

1. Kaburga yerleşimi/laminatı ve menteşe web'i imalat tanımıyla doğrulanmalı (f_1T'ye birinci derece etki).
2. Kabuk mod şekilleriyle p-k flutter kuruldu (şerit teorisi, kutu uydurması; dolu/boş 1326/1324 km/h). Kalan: kontrol yüzeyi serbestliği, kesit distorsiyonunun aerodinamiğe katılması (genelleştirilmiş kütle kontrolü burulma modlarında 0,68–0,79), kuyruk ve gövde ile tüm uçak modeli, serbest-serbest GVT.
3. Malzeme üretici/kupon verisi (E1 125 vs 135 GPa, kumaş G12, dayanımlar, sıcak-nem), B-basis allowable.
4. Burkulma: CCX doğrusal burkulma (orta ağ, s41r043w1) nihai yükte çarpan 8,9 verdi, ancak çekirdek kayması temsil edilmediği için sandviç panelde iyimser; elle kayma kıvrılması dahil kök yakını ön panel payı ≈1,2–1,5. Çekirdek kayması/kırışma (zigzag gerekir), yapıştırıcı ve kök cıvata hattı; kök bölmesi Tsai-Wu ve çekirdek kayması yakınsamadı.
5. GVT: kabul kriteri f_1T ≥ 230 Hz korunur; kabuk tasarım hedefi ≈295 Hz ve üstü (model dolu 295,2 Hz; inceleme sonrası düzeltildi, eski 294,9 Hz).
6. `validation/study.py` kayıt bütünlüğü cfd/*.py dahil runner kaynaklarının SHA'sını tuttuğundan paralel CFD değişiklikleri bu çalışmaları "STALE" yapabilir; entegrasyondan önce `run_case.py cantilever/coupon --study --threads 1` ve `fem/run_wing_study.py` yeniden koşulmalı.
