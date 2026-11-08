# Grup 1 inceleme: CFD ve doğrulama altyapısı

**Kapsam:** `cfd/`, `validation/` (kod ve sonuçlar), `thermal/` sonuçları, `docs/10` CFD bölümleri (§10.7 hariç).
**Dal:** `iter5/yuksek-dogruluk` (commit yapılmadı). **Tarih:** 2026-11-08.
**Testler:** `python -m unittest validation.test_validation validation.test_cfd_mesh` → 33 test OK (önce 31; +2 yeni + 1 genişletilmiş test).

## Özet

| Konu | Bulgu | Sonuç |
|---|---|---|
| 1. RAE kaba v2 koşusu | 30000 iter MG0: UNCONVERGED (ρ düşüşü 3.55, ν̃ düşüşü 0.30 < 4; enerji residual'ı +0.004'te). Kayıt ayrıca STALE (koşu sonrası `validation/convergence.py`, `study.py`, `cfd/cases.py` değişti). | Kapı geçmiyor. Arşivlendi: `validation/results/rae2822_SA/v2_mg0_coarse_unconverged.json` |
| 2. İz bölgesi ağı | İz kesitinde duvar aralığı (2e−6c) 100c boyunca taşınıyordu (en-boy 1e3–1e7). İz ilk aralığı artık TE'den uzaklaştıkça ds/100'e rampalanıyor. | Kaba ağ MG0 ile 4292 iterasyonda **kapıyı geçti** (v2: 30000'de geçmedi). CL −%3.07, CD −%0.75, Cp RMSE .098 > .08. Orta/ince 2 saat sınırında BLOCKED; üç ağ PENDING. |
| 3. Düz levha GCI | p=.434, formal 2'den çok uzak; Fs=1.25 bu durumda uygun değil. Roy/Roache kuralı uygulandı: p_kullanılan=.5, Fs=3 → ince GCI %1.82 (önceden %0.88). | Üç ağ yeniden koşuldu (bitwise aynı Cf); %1.82 < %5, **BENCHMARK_ACCEPTED korunur** |
| 4. Kapı / hash zinciri | STALE denetimi çok genişti (testler, rapor aracı, başka alanın dosyaları, params ve uçak tasarım dosyaları benchmarkı eskitiyordu); eksik çalışmada eskimiş kayıt PENDING'in arkasında saklanıyordu. | Düzeltildi. thermal_1d, 6 motor termal senaryosu, cantilever ve coupon yeniden koşuldu; dördü de BENCHMARK_ACCEPTED, sayılar değişmedi |
| 5. Uçak tasarımına bağlantı | Gerekli. Raymer buildup'ın Cf bileşeni düz levhayla kısmen doğrulandı; form faktörü, sıkıştırılabilirlik düzeltmesi, Mcrit ve 3B Q/misc payı doğrulanmadı. | Öneri + yol haritası |
| 6. LES/DES | Bu tasarım soruları için gerekmez; tek gerekçeli kullanım alık S-kanalı dinamik distorsiyonu. Bu makinede (seri SU2) uygulanamaz. | Öneri |

## Düzeltilenler

### D1. RAE C-ağı iz kesiti en-boy oranı (P1)
- **Dosya:** `cfd/structured_airfoil.py:27-38` (yeni sabitler `WAKE_ASPECT=100`, `WAKE_RAMP=1.5`), `:132-144` (ışın başına katman mesafesi), `:195-202` (`max_aspect_ratio` raporu).
- **Sorun:** Tüm ışınlar aynı geometrik katman dizisini (ilk hücre 2e−6c) kullanıyordu. İz ışınlarında bu, iz kesitinin iki yanında 2e−6c kalınlığında, 0.004–15c uzunluğunda hücreler demekti (en-boy 1e3–1e7). v2 MG0 koşusunun residual tepeleri x≈1.2–2c iz kesitinde toplanıyordu.
- **Düzeltme:** İz düğümü k için ilk aralık `a_k = min(first·1.5^(k/factor), first + (ds_k − ds_TE)/100)`; katman mesafesi `d_j = d0_j + j·(a_k − first)`. TE'de a=first (duvar ağıyla süreklilik), uzak izde a≈ds/100. Toplamsal karışım normal büyümeyi duvar dizisinin oranında tutar (≤1.18 kaba); dış katmanlar korunduğundan TE yakınında katman eğimi oluşmaz. Önceki "her ışına ayrı geometrik dizi" denemesi köşe sinüsünü .20'ye düşürmüştü; bu yöntemde min köşe sinüsü .655 (yalnız 100c çıkış ucundaki 45° yelpaze sütunlarında; v2'de .707).
- **Ağ ölçüleri (kaba/orta/ince):** 33792/76032/135168 quad (değişmedi); normal büyüme 1.18/1.12/1.09; iz kesiti en-boy oranı TE'de 2000 (yüzeyle aynı), TE'den ~0.3c sonra ≈100; iz ucu ilk aralığı .162/.111/.084c; uzak alan çıkış ucu x≈183c.
- **Doğrulama:** `validation/test_cfd_mesh.py` C-ağı testine iz kesiti en-boy (<2·WAKE_ASPECT) ve min köşe sinüsü ≥.6 eklendi; 33 test OK. Çözücü: `run_case.py rae2822 --level coarse --rae-scheme mg0 --iterations 30000 --threads 1 --reference validation/reference/rae2822.local.json` → **COMPUTED** (`C:/hz750run/rae2822_SA_coarse_yw4jh4om`, 4292 iterasyon, 2411 s): bağıl Cauchy100 4.0e−9, ρ/ν̃ düşüşü 7.82/4.18, enerji 7.8 mertebe (v2'de 3.5), y+max .81; CL .72018, CD .012605, Cm −.0886, Cp RMSE .0982. Aynı ağda resmi MG3 W-cycle hâlâ ıraksıyor (1590. iterasyon, `pilot_v3_mg3_coarse_failed.json`). Orta ve ince ağ (`--level medium/fine`, `--timeout 7200`) paylaşılan makinede 7200 s'de **BLOCKED (süre)**: orta 7765 iterasyonda Cauchy100 1.6e−8, ρ/ν̃ düşüşü 7.08/3.62 (kapıya yakın), CL .72754, CD .012466; ince 4384 iterasyonda 4.17/1.31. `study.py validation/results/rae2822_SA` → PENDING.

### D2. Düşük gözlenen mertebede GCI emniyet katsayısı (P1)
- **Dosya:** `validation/convergence.py:5-48` (`gci(h, q, formal_order=None)`), `validation/study.py:94,159-160`.
- **Sorun:** Fs=1.25 Roache'un üç ağ ve asimptotik bölgedeki (gözlenen p formal mertebeye yakın) çözümler için önerisidir. Düz levhada p=.434 (formal 2) iken Fs=1.25 ile verilen %0.88, hata bandını olduğundan dar gösteriyordu.
- **Düzeltme:** CFD vakalarında (formal mertebe 2) |p−2|/2 > .1 ise `p_kullanılan = min(max(.5, p), 2)`, `Fs = 3` (Roache 1998; Oberkampf & Roy 2010 §8.7, Roy 2005). Richardson değeri gözlenen p ile raporlanmaya devam eder; `order_used`, `safety_factor`, `formal_order` alanları eklendi. FEM/termal vakalara formal mertebe verilmedi (onların sahibi değilim; davranış değişmedi).
- **Sonuç:** Düz levha ince GCI %0.88 → %1.82 (p_kullanılan .5, Fs 3). Hâlâ <%5 → **BENCHMARK_ACCEPTED korunur**. Alternatif Eça–Hoekstra (p<.5 için U=3·max fark) %0.74 verir; seçilen kural daha muhafazakârdır. Eşik (%5) değişmedi.
- **Doğrulama:** `test_low_observed_order_uses_bounded_order_and_fs3` (iter5 düz levha sayılarıyla, Fs=3 formülü elle) ve p≈2'de Fs 1.25'in korunduğu kontrol. Düz levha üç ağ, kaynak değişikliği nedeniyle STALE olduğu için `run_case.py flat_plate --study --threads 1 --iterations 30000` ile yeniden koşuldu: Cf .0028542517/.0028586462/.0028613266 (önceki koşuyla bitwise aynı), süreler 174/682/1811 s, Cauchy100 ≈3.5e−7, ρ/ν̃ düşüşü ≥5.28/4.97 → `study.json` BENCHMARK_ACCEPTED, GCI %1.817.

### D3. STALE kapsamı ve PENDING arkasında saklanan eskimiş kayıt (P1)
- **Dosya:** `validation/study.py:79-121` (`VALIDATION_RUNTIME`, `SOURCE_SCOPE`, `BENCHMARKS`, `relevant_source`, `stale_reason`), `:124-148` (evaluate sırası, kapsamlı code_sha256 tutarlılığı), `validation/run_case.py:76-80`.
- **Sorunlar:**
  1. `code_sha256` `validation/ cfd/ fem/ thermal/` altındaki **bütün** `.py` dosyalarını içeriyordu ve hepsi karşılaştırılıyordu. Bir test dosyası, `report.py` ya da başka alanın dosyası (örn. bu inceleme sırasında FEM ajanının değiştirdiği `fem/shell_flutter.py`) değişince düz levha/RAE/thermal_1d benchmarkları STALE oluyor, bağlı uygulama kapıları (airfoil, engine_thermal) bloke oluyordu. Oturum başında beş benchmarkın beşi de bu nedenle STALE'di (`validation/convergence.py`, `study.py`, `report.py`, iki test dosyası, `cfd/cases.py`).
  2. Benchmarklar `params.py`'yi ve `provenance.inputs` içindeki uçak dosyalarını (`structures.py`, `fe_modal.py`, `aero_analysis.py`, `inlet_analysis.py`, `cad_report.json`) okumadığı halde bunlara bağlanıyordu. thermal_1d'nin "params nedeniyle STALE" durumu fiziksel bir değişiklik değildi.
  3. Üç ağ tamamlanmamışsa `evaluate` eskime denetimine hiç girmeden PENDING dönüyordu; eskimiş RAE kaba kaydı görünmüyordu.
- **Düzeltme:** Kayıt yalnız vakanın çalışma anında import ettiği kaynaklara göre eskir: `validation/{__init__,common,convergence,run_case,study}.py` + alan klasörü (`cfd/`, `fem/`; termalde `thermal/` + `fem/cases.py`); `test_*.py` hariç. Benchmarklar params ve uçak dosyalarına bağlanmaz, uygulama vakaları (airfoil, aircraft, inlet, wing, engine_thermal) bağlanmaya devam eder; `run_case` benchmarklar için bu dosyaları artık kaydetmez. Eskimiş kayıt, çalışma eksik olsa da STALE olarak gösterilir. Bilinmeyen vaka için eski (muhafazakâr) davranış korunur.
- **Doğrulama:** `test_stale_record_is_reported_even_when_study_incomplete` (benchmark params'a bağlanmaz, airfoil bağlanır, test/rapor/fem dosyası CFD'yi eskitmez, `cfd/cases.py` eskitir). Yeni kapsamla thermal_1d yeniden koşuldu: **BENCHMARK_ACCEPTED** (357.15 K, 1600 W/m², EXACT_OR_ROUNDOFF).

### D4. Motor termal senaryoları yeniden koşuldu
- Altı senaryo (`thermal/results/engine_thermal_T250_F{0,2}_{1ed7ca8299,679b6a3875,803b2f042b}`) params nedeniyle STALE idi. İlk yeniden koşu denemem thermal_1d'nin geçici STALE durumu (FEM ajanının `fem/shell_flutter.py` değişikliği) yüzünden BLOCKED kayıt üretti; D3 sonrası thermal_1d yeniden kabul alınca altısı yeniden koşuldu. Hepsi COMPUTED; çalışma durumu REVIEW_REQUIRED (önceki gibi; analitik referans yok). Sayılar docs/10 §10.6 tablosuyla birebir aynı: kabuk içi 58.77/44.39, 61.71/46.67, 149.82/126.10 °C; sıcak keçe yüzü 109.33/117.70/184.96 °C.
- Not: `scenarios.example.json` çalışma kopyası CRLF, kayıtlı hash (1ed7ca…) LF içeriğe ait. Aynı case_id'yi korumak için koşu sırasında dosya geçici olarak Git blob'u (LF) ile yazıldı, ardından `git checkout` ile geri alındı (öneri Ö6).

### D4b. cantilever ve coupon benchmarkları yeniden koşuldu
- `validation/results/cantilever` ve `coupon` (validation/ altında, sonuçları benim alanım) 0208319'daki `convergence.py`/`study.py` değişikliği ve bu turdaki değişiklikler nedeniyle STALE idi; kanat (wing) kapısını bloke ediyordu. `run_case.py cantilever --study` ve `run_case.py coupon --study` (CCX tek iş parçacığı) → ikisi de **BENCHMARK_ACCEPTED**, sayılar önceki kayıtla aynı (sehim .3781402 mm, f1 8.422987 Hz). FEM sahibi bilgilendirilmeli: `fem/` altındaki her değişiklik bu iki kaydı yeniden eskitir (doğru davranış).

### D5. Belgeler
- `cfd/RESULTS_iter5.md`: yeni "Iter5 v3" bölümü (v2 sonucu, iz ağı, MG3/MG0 koşuları, GCI kuralı, STALE kuralı).
- `docs/10` §10.2, §10.5, §10.6.1 ve giriş özetinin CFD/termal kısımları güncellendi (§10.7'ye dokunulmadı).
- `cfd/README.md` ağ tanımı, `validation/README.md` GCI ve STALE kuralı güncellendi.

## Öneriler

| # | Önem | Öneri | Gerekçe | Tahmini iş |
|---|---|---|---|---|
| Ö0 | P1 | RAE Cp RMSE ölçütünün değerlendirme kümesine karar verin (ön kenar deney noktası) | Cp RMSE .098'in çoğu tek noktadan: NASA `cp.exp.gen` üst dalında x/c=.0002, Cp −.42 (komşuları x/c=.0008'de +.10, x/c=0'da +.83). Durma noktasında fiziksel değil, bozuk bir basınç deliği gibi görünüyor; ayrıca x'e göre enterpolasyon ön kenarda kötü koşullu (x≈s²). x/c<.002 noktaları (8 nokta) çıkarılınca: v3 kaba ağ .0982 → **.048**, resmi SU2 ağı+cfg .0984 → **.038**. İkisi de .08'in altına iner; kalan en büyük hata şok konumu (CFD şoku ~.02c önde, SA için bilinen davranış). Eşik değişmeden kabulü belirleyen bir değerlendirme kümesi kararı olduğu için kendim değiştirmedim. Seçenekler: (a) x/c<.002 dışlama ve gerekçesi, (b) yay uzunluğuna göre karşılaştırma, (c) aykırı nokta kuralı. | 1 saat + RAE yeniden değerlendirme |
| Ö1 | P1 | 3B CFD için SU2'nin MPI'lı Windows sürümünü (MS-MPI) kur ve hash'le | Kurulu SU2 seri. Ölçülen hız: 33792 hücrede ~0.24 s/iter (yük yokken), yani ~7e−6 s/hücre/iter. 2M hücrelik 3B RANS ~30–40 s/iter, 5000–20000 iter → 2–9 gün. docs/10'daki "1–6 saat/ağ" tahmini seri çözücüyle gerçekçi değil. | 0.5 gün |
| Ö2 | P1 | Profil (A) taraması: 64A007 (gerçek koordinat + mevcut ölçeklenmiş 64A010 ayrı), M .61/.65/.70/.725/.75, α 0/1/2, SA (+SST), RAE kabul sonrası | Raymer buildup'ın kanat FF=(1+0.6/x_t·t/c+100(t/c)⁴)·1.34M^0.18 terimi M=.614'te FF'yi ~%23 artırıyor; bunu doğrulayan tek adım 2B RANS c_d = 2·Cf·FF karşılaştırması. NeuralFoil CD'si M=0–.70 arasında birebir sabit (.0038018); sıkıştırılabilirlik etkisini içermiyor, RANS ile karşılaştırma yapılmadan Mach etkisi için kullanılamaz. Cp_min → Karman–Tsien ile Mcrit ve M .70/.75'te drag-rise Korn κ_A=.87 varsayımını doğrular. | 2B: ağ başına ~1 saat (kaba), 15 nokta × 3 ağ ≈ 2–3 gün seri |
| Ö3 | P1 | Düz levhayı M=.61 ve uçuş Re'sinde (gövde Re≈2.8e7) ayrıca koş | Kabul edilen düz levha M=.2, Re 5e6. Buildup'taki `(1+0.144M²)^-0.65` sıkıştırılabilirlik düzeltmesi ve yüksek Re Cf'si doğrulanmadı. Düz levha SA, Schlichting'den %4.7 düşük; buildup Cf'si bu yönde ~%5 muhafazakâr olabilir. | 0.5 gün |
| Ö4 | P2 | `cfd/convergence.assess` ν̃ düşüşünü iterasyon 0 yerine ilk N iterasyondaki tepe residual'dan ölç | RAE'de ν̃ residual iterasyon 0'da −4.42, 10. iterasyonda −6.22, 100'de −4.06; "iter 0'dan düşüş" başlangıç alanına bağlı ve vaka ile değişiyor. Bu bir kapı tanımı değişikliği; eşik (4 mertebe) aynı kalsa da kabulü etkileyebilir, tasarım kararı. | 1 saat + yeniden değerlendirme |
| Ö5 | P2 | Düz levha p=.434'ün nedenini ayır: Cf_mean yerine x=.97 noktasal Cf (TMR karşılaştırma noktası) ve MUSCL_TURB=YES ile ikinci mertebe türbülans | Ön kenar tekilliği ve birinci mertebe ν̃ konveksiyonu (MUSCL_TURB=NO) gözlenen mertebeyi düşürür. RAE de MUSCL_TURB=NO; formal mertebe akış için 2, türbülans için 1. | 0.5 gün |
| Ö6 | P2 | Girdi hash'lerini satır sonundan bağımsız yap (`.gitattributes` içine `*.json -text` ya da hash öncesi `\r\n`→`\n`) | `thermal/scenarios.example.json` çalışma kopyası CRLF, kayıtlı hash LF; aynı girdi farklı case_id üretiyor. | 30 dk |
| Ö7 | P2 | `report.py` tüm alanların `study.json/md` dosyalarını yeniden yazıyor | Başka ajanların sahibi olduğu `fem/results/*/study.*` dosyalarını değiştirir; bu yüzden bu oturumda çalıştırmadım. Alan filtresi (`--folder`) eklenmeli. | 30 dk |
| Ö8 | P2 | RAE MG3 W-cycle bu yapısal ağda hâlâ ıraksıyor (v3 ağda 1590. iterasyon); MG0 tek seçenek. Çok seviyeli yapısal ağda aglomerasyon kalitesi ya da JST/MG sönümleme ayrıca incelenmeli | Resmi hibrit ağ MG3 ile yakınsıyor; fark ağ topolojisinde. MG0 orta/ince ağlarda yakınsama süresini çok uzatıyor. | 1 gün |
| Ö9 | P3 | `airfoil_SA_M0p6100_A0p0000/coarse.json` eski ağdan kalma UNCONVERGED (cd .0249, NeuralFoil'in ~7 katı); tarihsel kayıt olarak işaretlenmeli | Yanıltıcı olabilir; artık STALE de. | 10 dk |

### Konu 5: CFD sonuçlarının uçak tasarımına bağlanması
Bağlanmalı, çünkü itki payı ve azami hız kararı sürüklemeye dayanıyor. Bugünkü durum: `sizing.py` Raymer bileşen buildup'ı (tam türbülanslı Cf · FF · Q · Swet/S + %15 misc) ve AeroBuildup (154 N) birbirinden ~%26–36 farklı. Doğrulama zincirindeki adımlar:

1. **Cf (sürtünme):** düz levha SA ile kısmen doğrulandı (M .2, Re 5e6). Eksik: uçuş Mach'ı ve Re'si (Ö3).
2. **Kanat form faktörü ve Mach terimi:** doğrulanmadı. 2B profil RANS'ı (Ö2) M=.61'de doğrudan c_d = 2·Cf·FF'yi sınar. RAE kabulü bunun önkoşulu (kapı zinciri doğru kurulmuş).
3. **Mcrit / dalga sürüklemesi:** `sizing.m_dd` Korn formülü + `Mcr = Mdd − (0.1/80)^(1/3)`; 750 km/h, 300 m'de M≈.614. 7% kalınlıkta kanat için Mcrit bu Mach'ın oldukça üstünde olmalı; ama gövde burnu, kanopi ve alık dudağı yerel süpersonik bölgeyi kanattan önce oluşturabilir. 2B profil taraması kanat için yeterli; gövde/alık için 3B gerekir.
4. **Girişim (Q) ve misc %15:** yalnız 3B RANS (B) sınar. Eksik adım: 3B ağda prizmatik sınır tabaka ve "temiz akışkan hacmi"nin yanı sıra **buildup ile aynı kapsamda karşılaştırma tanımı** (kızak/alık/egzoz açık-kapalı, aynı CL, aynı Sref). Plan bunu docs/10 §10.3 B'de söylüyor ama Ö1 olmadan 3B zaman bütçesi gerçekçi değil.
5. **Geçiş:** buildup tam türbülanslı, NeuralFoil ncrit=9 geçişli; bu fark sayısal hata değil model farkıdır ve belirsizlik bütçesinde ayrı kalem olmalı.

### Konu 6: LES/DES gerekli mi
**Gerekmez.** Tasarımın CFD'den beklediği büyüklükler (seyirde sürükleme, Mcrit, profil kutupları, alık recovery'si) yapışık akışta zamandan bağımsız büyüklüklerdir ve RANS'ın kapsamındadır. LES/DES yalnız şu sorular için gerekçeli olur: alık S-kanalının **dinamik** distorsiyonu (yüksek α/β'da dudak ayrılması), egzoz–gövde taban akışı, buffet. Bunlar seyir tasarımını değil marjları ilgilendirir ve önce yer/uçuş testiyle (termokupl, motor kayıtları) ele alınabilir.

Maliyet (docs/10 §10.4 hesabı kontrol edildi, doğru: N=1e8, 5e5 adım × 10 iç iterasyon × 1e−7 s ≈ 5e7 s ≈ 579 gün): bu makinede ölçülen 2B hızı (~7e−6 s/hücre/iter seri) 3B'de daha yüksek. İzole S-kanal DDES için ~1–3e7 hücre ve ~2e4 fiziksel adım × 10 iç iterasyon ≈ 2e5 iterasyon → seri ~1–4 yıl, 16 çekirdek MPI ile bile aylar. **Öneri:** LES/DES'i yol haritasından çıkarmak değil, "3B RANS doğrulandıktan ve uçuş/yer verisi alık distorsiyonu sorununu gösterirse" koşuluna bağlamak; kullanıcıya RANS'ın neden yeterli olduğunu açıkça yazmak.

## Yol haritasına eklenmesi gerekenler
1. SU2 MPI kurulumu ve 3B zaman bütçesinin ölçümle yeniden yazılması (Ö1). 3B B/C işinin önkoşulu.
2. Düz levha M=.61 / yüksek Re koşusu (Ö3); buildup Cf bileşeninin kapanışı.
3. RAE üç ağ kabulünden sonra profil taraması ve buildup kanat FF/Mcrit karşılaştırma tablosu (Ö2).
4. Buildup ile 3B RANS'ın "aynı kapsam" tanımı (bileşen listesi, Sref, CL, açık/kapalı alık) yazılı olarak sabitlenmeli; ardından B.
5. Kapı tanımı gözden geçirmesi: ν̃ düşüş tabanı (Ö4), STALE kapsamı (D3) için FEM sahibiyle uzlaşma.
6. SST düz levha ve RAE (model-form belirsizliği için en ucuz adım).

## Doğrulayamadıklarım
- RAE orta ve ince ağ: 2 saatlik koşu sınırına sığmadı (BLOCKED); üç ağ GCI'si ve RAE kabul kararı yok. Orta ağ yük yokken ~1–1.5 saatte, ince ağ yalnız restart zinciriyle tamamlanabilir.
- `node validation/check_artifacts.cjs` çalıştırıldı ama **FAIL**: `fem/results/shell_flutter.json` içinde geçersiz JSON (`"Vf_g02_kmh": Infinity`). Dosya FEM alanının, düzeltmedim. Benim değiştirdiğim dosyalarda sondaki boşluk denetimi temiz.
- Sahibi olmadığım belgeler eski sayıları taşıyor ve güncellenmeli: `README.md:122`, `CHANGELOG.md:26`, `BASARIM_AGACI.md:60,71,74-75,154,157,163` (GCI %0,88 → %1,82; thermal_1d artık STALE değil; RAE kaba kapı geçti).
- `report.py` (karşılaştırma tablosu) çalıştırılmadı (Ö7).
- MG0 pilot koşusu (`C:/hz750run/pilot_v3_rae_coarse_mg0`) ve iptal edemediğim v3 MG3 koşusu ayrı işlem olarak çalıştı; işlemleri durdurma izni verilmedi, bu yüzden MG3 kendi ıraksamasına kadar çalıştı.
- Roache/Roy kuralının kaynak sayfa numaraları kendi bilgimden; bu oturumda birincil kaynağı açmadım.
