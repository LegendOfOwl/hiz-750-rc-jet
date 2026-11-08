# HIZ-750 iter5 CFD — çalışma kaydı

**Güncel durum (iter5 v3, en alttaki bölüm, 2026-11-08):** düz levha SA üç ağda BENCHMARK_ACCEPTED, sınırlandırılmış p ve Fs=3 ile ince GCI %1.82 (eski Fs=1.25 değeri %0.88). RAE2822 iz kesiti ağı düzeltildi; kaba ağ MG0 ile 4292 iterasyonda proje kapısını geçti (CL −%3.07, CD −%0.75, Cp RMSE .098 > .08). Orta/ince 2 saatlik koşu sınırında BLOCKED (orta 7765 iterasyonda ν̃ düşüşü 3.62/4); üç ağ çalışması PENDING. Aşağıdaki ilk bölümler tarihsel kayıttır.

## Ağ ve ayar teşhisi

[Ağ denetimi](../validation/results/flatplate_mesh_audit.json): resmi SU2 137×97 ağı 13056 quad, ilk duvar aralığı 2.00465e−6 m; eski transfinite gmsh ağı 14400 quad, aralık 2.00022e−6 m. İkisinde de negatif alan, nonmanifold kenar veya sınır marker eşleşme hatası bulunmadı. Dolayısıyla önceki FGMRES hatasını negatif hacme veya bozuk SU2 dosya biçimine bağlayan kanıt yoktur. İlk karma BL ağında ayrıca üçgen/quad geçişi ve çok küçük köşe hücreleri vardı.

Yeni düz levha iki transfinite blok, 24+112 boyuna /96 normal hücre; boyuna ön kenar sıklaştırması, giriş x=−1/3 ve LU-SGS kullanır. Eski ağın boyuna dağılımı uniform ve önkoşullayıcısı ILU idi. Birden çok ayar birlikte değiştiğinden tek bir nedene bağımsız nedensellik atfedilmez. Alan x=−1/3..2, y=0..1; INLET/OUTLET/FARFIELD/WALL/SYMMETRY markerları korunur.

RAE/profil dört transfinite quad bloklu C-ağı: ortak wake çizgisi, 30c uzak alan, 33792/76032/135168 hücre; h oranları 1.5/1.333. Pozitif alan ve sınır bağlantısı denetlendi. Diverge olan kaba RAE ağının minimum köşe sinüsü .2772, ince düz levhanınki 1.0; negatif köşe yok ([denetim](../validation/results/diverged_mesh_audit.json)). Bu denetim uzak alan bağımsızlığı veya gerçek y+ yerine geçmez. SU2 merkezî JST ile MUSCL_FLOW=YES geçersizdi; MUSCL_FLOW=NO düzeltildi. Case 6 için resmi SU2 v8.2 MG3/W-cycle/CFL2.5 ayarları denendi.

[Satır karşılaştırması](../validation/results/rae2822_config_comparison.json) önemli bir farkı ortaya koydu: üretilen cfg LU_SGS kullanırken resmi cfg önkoşullayıcıyı belirtmiyor. [SU2 v8.2 CConfig.cpp](https://raw.githubusercontent.com/su2code/SU2/v8.2.0/Common/src/CConfig.cpp) gerçek varsayılanı **ILU** yapıyor; aynı dosyadaki eski açıklama LU_SGS dediği için ilk varsayım yanlıştı. Düz levha pilotundaki linear error=.01, resmi varsayılan=1e−6 farkı da var. Bunlar kontrollü yeniden koşum gerektiren aday nedenlerdir; tek başına nedensellik kanıtı değildir. Resmi RAE ağı C-tipi transfinite değil, 18042 üçgen+4800 quad ve ±100c uzak alan içerir ([resmi ağ](../validation/results/rae2822_native_mesh_audit.json)); üretilen ağın ±30c alanından da farklıdır.

## Düz levha SA

Güncel kapı, Claude'un bu turdaki talimatıyla: son100 adımda ortalama mutlak CD değişimi /ortalama |CD| <1e−6; başlangıçtan yoğunluk ve ν̃ residual düşüşü ≥4 mertebe; y+max≤1. Enerji yalnız bilgi olarak raporlanır. Eski kayıtların tüm-RMS<−6 değerlendirmesi ayrı yeniden değerlendirmede (`cfd/results/flatplate_reassessment.json` (dosya kayıp: Codex worktree silindi, yeniden üretilmedi)) korunur.

| Ağ | Hücre | Cf | Bağıl Cauchy100 | ρ/ν̃ düşüşü | y+max | Durum |
|---|---:|---:|---:|---:|---:|---|
| kaba | 13056 | .0028541914 | 7.10e−8 | 5.728/4.743 | .494 | güncel kapı geçti |
| orta | 29376 | .0028584677 | 1.129e−7 | 5.681/4.118 | .3435 | yedi restart sonrası kapı geçti |
| ince | 52224 | geçerli sonuç yok | — | — | — | 1202. iterasyonda residual>10²⁰, FAILED |

Kaba Cf'nin Schlichting (.003003713) farkı yaklaşık −%4.98; orta farkı −%4.84. Resmi tek ağın tarihsel Cf=.002849 değeri ekran yuvarlamasıdır. Üç kapıyı geçen sonuç olmadan GCI veya BENCHMARK_ACCEPTED yoktur: **GCI=null / çalışma PENDING (ince ağ başarısız)**. Devam runner'ı her native DRAG-Cauchy çıkışında birleşik geçmişi denetler; residual düşüşü sağlanmadıysa kendi restart'ından devam eder, her ağ için toplam7200s sınırını korur. Orta ağ devamı 82.25s sürdü; özgün sonuç ve hashleri yeni kaydın içinde korundu. İnce ağın ilk solver koşusu başarısız ve executable provenance kaydı yoktu; devam denemesi başarısız kayıt alanlarına takıldı ve solver başlatılmadı. Sonraki sürüm bunu açık preflight hatasıyla reddeder; ince ağın kendi çözümünden geçerli bir devam elde edildiği iddia edilmez.

## RAE2822

Claude yönlendirmesiyle hedef **Case 6**, M=.729, α=2.31°, Re=6.5e6; ilk istenen Case 9 bu çalışmada tamamlanmadı. [NASA NPARC](https://www.grc.nasa.gov/www/wind/valid/raetaf/raetaf01/raetaf01.html) deney Cp verisi, işaret dönüşümünü gösteren cfpost komutu ve sayfa byte'ları referans manifestinde (`validation/reference/rae2822.local.json` (dosya kayıp: Codex worktree silindi, yeniden üretilmedi)) SHA256 ile kayıtlıdır. Arşiv −Cp sakladığından işaret ters çevrildi.

CL=.743, CD=.0127, CM≈−.095: **secondary: literatürden aktarılan değer, birincil dosya doğrulanmadı**; Cook/McDonald/Firmin, AGARD AR-138 (1979), reviewer tarafından sağlandı. Cp RMSE birincil ölçüt, CL/CD ikincil ölçüttür. Eşikler Cp RMSE≤.08, |CL hatası|≤%5, |CD hatası|≤%15, GCI≤%5; olası kabul etiketi “BENCHMARK_ACCEPTED (CL/CD ikincil kaynak)”. NASA forces.lis sayısal WIND çıktısıdır ve deneysel CL/CD olarak kullanılmadı.

MG0 kaba koşusu izinle durduruldu; tarihsel kayıt: `validation/results/rae2822_SA/mg0_stopped.json` (dosya kayıp: Codex worktree silindi, yeniden üretilmedi). MG3 kaba SA 1430. iterasyonda residual>10²⁰ ile **FAILED**, 444.67s. Orta/ince yalnız PREPARED; kaba yakınsamadan solver başlatılmadı. SST henüz çalıştırılmadı. Üretilen RAE'de geçerli CL/CD/Cp hatası yoktur. Resmi cfg+resmi ağ native kontrolü ayrı yürütülüyor; sonuçları üç-ağ kabulü yerine geçmez.

## Proje profili / NeuralFoil

[Baz tablosu](results/neuralfoil_baseline.json) α=0/1/2°, M=0/.61/.65/.70/.75, Re=4.5e6 için CL/CD/CM içerir. Geometri aero_analysis.py ile aynı kalınlığı ölçeklenmiş64A010; bağımsız gerçek64A007 koordinatı değildir. Kaba C-ağı hazırlandı. RAE doğrulaması tamamlanmadığından bu tablo RANS karşılaştırması veya Mcrit doğrulaması değildir. Geçişli NeuralFoil ile tam türbülanslı RANS farkı yalnız sayısal hata sayılamaz.

## Açıklar ve kontroller

Üç-ağ flatplate GCI, RAE kaba yakınsama/orta-ince/SST, profil RANS/α/Mcrit taraması ve 3B prizmalı RANS açık.

## Iter5 devam bulguları

Bu bölüm Codex oturumu kapandıktan sonra ham çıktılardan (C:/hz750run) eklendi; yeni solver koşusu başlatılmadı.

**a. Resmi SU2 RAE2822 cfg + resmi ağ (native kontrol, `rae2822_native_aztl93ur`).** İteratif kapı geçti: bağıl Cauchy100 2.74e−9, ρ/ν̃ düşüşü 6.30/4.77 mertebe. CL=.7236 (ikincil referans .743'e göre −%2.61), CD=.013449 (.0127'ye göre +%5.90). Ham SU2 CMz=+.0928; x akış yönü, y yukarı iken burun-yukarı Cm=−CMz=−.0928 (moment referansı x/c=.25, y/c=0); Cm hatası +%2.27 (ikincil −.095'e göre). Gerçek duvar konturu üzerinden tam kapsamda Cp RMSE=.0984 > .08 eşiği. Native CSV y+ içermediğinden y+ doğrulanmadı. **Karar: çözücü/cfg referansı olarak KABUL; deney Cp kabulü YOK** (BENCHMARK_ACCEPTED değildir).

**b. ILU + 1e−6 pilotları da ıraksadı.** Resmi varsayılan önkoşullayıcı (ILU) ve LINEAR_SOLVER_ERROR=1e−6 ile tekrarlanan koşular da “Residual >10²⁰” ile durdu: kendi C-ağımızda RAE kaba MG3 `rae2822_SA_coarse_pzqpay41` 1452. iterasyonda, düz levha ince MG3/CFL10 `flat_plate_SA_fine_2_dofqdq` 1155. iterasyonda. Önkoşullayıcı/lineer tolerans farkı ıraksamanın sebebi değildir.

**c. MG0 pilotları (MGLEVEL=0, CFL_ADAPT=YES, CFL_ADAPT_PARAM=(0.5, 1.5, 1.0, 100.0), CFL_NUMBER=1.0).**

| Pilot | Ağ | Sonuç | Son değerler |
|---|---|---|---|
| `pilot_mg0_flat_plate` | düz levha ince, 52224 quad (MG3'te ıraksayan ağın aynısı) | SU2 DRAG-Cauchy ölçütüyle 3082. iterasyonda yakınsadı (Cauchy[CD]=9.99e−7) | Cf=.0029177, y+max=.269 |
| `pilot_mg0_rae2822` | kendi RAE C-ağımız kaba, 33792 quad | 20000 iterasyonda ıraksamadı ama yakınsamadı | log ρ=−4.73, Cauchy[CD]=7.5e−5, CL=.696, CD=.0157 |

Düz levha için ıraksamayı MG3 + CFL 10 kombinasyonu tetikliyordu; `cfd/cases.py` düz levha ayarları pilotla aynı olacak şekilde MGLEVEL=0, CFL_ADAPT=YES, CFL_ADAPT_PARAM=(0.5, 1.5, 1.0, 100.0), CFL_NUMBER=1.0 yapıldı (üretilen cfg pilot `case.cfg` ile satır satır aynı). RAE ayarlarına dokunulmadı. Not: pilotun proje kapısına (`cfd/convergence.py`) göre değerlendirmesi henüz geçmiyor: bağıl Cauchy100=3.4e−5 (>1e−6), ν̃ düşüşü 3.12 mertebe (<4). Yani SU2'nin kendi durma ölçütü sağlandı, proje kapısı sağlanmadı; ince ağ düz levha sonucu GCI girdisi olarak henüz kullanılamaz, devam koşusu gerekir.

RAE'de aynı MG0/CFL ayarları ıraksamayı önledi ancak yakınsama sağlamadı; resmi cfg+resmi ağ aynı çözücüyle yakınsadığı için kalan sorun **AĞ**dır: kendi C-ağımız ±30c uzak alan (resmi ağ ±100c) ve minimum köşe sinüsü .277 (resmi ağ .371) ([denetim](../validation/results/diverged_mesh_audit.json), [resmi ağ](../validation/results/rae2822_native_mesh_audit.json)). Sonraki adım: uzak alanı büyütülmüş ve iz/firar kenarı köşe kalitesi iyileştirilmiş C-ağı. Deneysel/model-form belirsizlikleri ve uzak alan duyarlılığı ayrıca incelenmeli. Bu tur yeni yazılım kurulmadı; mevcut SU2 8.2.0, gmsh4.15.2, Python3.12 kullanıldı. 16 unittest geçti; Python derleme denetimi geçti. Artefakt kontrolündeki CRLF okuma hatası düzeltildi; rapor son kontrolü koşular tamamlanınca tekrarlanır.

## Iter5 v2: düz levha kabulü ve yeni RAE C-ağı (bu tur)

Bu turda kod değişti: `cfd/structured_airfoil.py` (yeni C-ağı), `cfd/cases.py` (düz levha ve profil durma kuralı, `--rae-scheme`), `validation/run_case.py` (`--rae-scheme mg3|mg0`), `validation/fetch_reference.py` (`--from-dir`), `validation/test_cfd_mesh.py` (+3 test). Eşikler değişmedi.

### Düz levha SA: BENCHMARK_ACCEPTED

Önce ince MG0 pilotu restart'tan devam ettirildi (`C:/hz750run/pilot_fp_fine_continue`, 2808 ek iterasyon): birleşik geçmişte proje kapısı geçti (bağıl Cauchy100 3.49e−7, ρ/ν̃ düşüşü 5.37/5.13). SU2'nin 1e−6 DRAG-Cauchy duruşunun erken olduğu görüldü: Cf .0029177 → .0028613 (−%1.9). Bu yüzden düz levha cfg'sinde durma kuralı `CONV_FIELD= ( RMS_NU_TILDE, DRAG )`, `CONV_RESIDUAL_MINVAL= -9.3` (başlangıç ν̃ ≈ −4.9…−5.1 → ≥4 mertebe), `CONV_CAUCHY_EPS= 1e-8` yapıldı. Sayısal şema değişmedi: ROE+MUSCL, GREEN_GAUSS, MGLEVEL=0, CFL 1 + CFL_ADAPT (0.5, 1.5, 1.0, 100.0), FGMRES+ILU, lineer hata 1e−6. Üç ağ aynı kodla ve aynı cfg ile `run_case.py flat_plate --study --threads 1 --iterations 30000` ile sıfırdan yeniden koşuldu (restart zinciri yok):

| Ağ | Hücre | Cf_mean | Schlichting farkı | Bağıl Cauchy100 | ρ / ν̃ düşüşü | y+max | Süre | Durum |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| kaba | 13056 | .0028542517 | −%4.98 | 3.50e−7 | 5.28 / 4.97 | .494 | 146 s | COMPUTED |
| orta | 29376 | .0028586462 | −%4.83 | 3.49e−7 | 5.33 / 5.06 | .344 | 490 s | COMPUTED |
| ince | 52224 | .0028613266 | −%4.74 | 3.49e−7 | 5.37 / 5.13 | .269 | 1095 s | COMPUTED |

Richardson/GCI (h oranları 1.333/1.5): monoton, gözlenen mertebe p=.434, Richardson Cf=.0028815, **ince GCI %0.88** (<%5). İnce Cf'nin ITTC (.003) farkı −%4.62, Schlichting (.0030037) farkı −%4.74 (<%15). [Çalışma](../validation/results/flat_plate_SA/study.md): **BENCHMARK_ACCEPTED**. Not: p=.43 düşük; üç nokta asimptotik bölgeyi tek başına kanıtlamaz ve korelasyon farkı deney doğrulaması değildir. İlk çalışmanın sayıları (kaba .0028541914, orta .0028584677) farklı cfg/kapıyla elde edilmişti; bu tablo onların yerine geçer. Ham klasörler: `C:/hz750run/flat_plate_SA_coarse_arw5q73i`, `…_medium_43xadtg5`, `…_fine_zcht2836`.

### RAE2822 ağı: yeni tek bloklu C-ağı

`structured_airfoil.py` yeniden yazıldı (gmsh yok, numpy/scipy). C-eğrisi = alt iz → alt yüzey → üst yüzey → üst iz; yüzey noktaları iki taraflı tanh (Vinokur) dağılımı (LE 1e−3c, TE 4e−3c), iz geometrik (TE aralığından 100c'ye). Her C-noktasından düz ışın çıkar; ışın açısı duvar normalinden alınır, C-eğrisi boyunca monoton yapılır (alt yarıda kümülatif min, üst yarıda kümülatif maks) ve monotonluğu koruyan düzleştirmeyle (150×factor² geçiş) yumuşatılır; monoton açılı ışınlar yelpazelenir ve kesişemez. İz ışınları TE'de dikeyden çıkış ucunda 45°'ye yelpazelenir (iz sütunlarının 100c boyunca TE genişliğinde kalmasını önler). Katman mesafeleri tüm ışınlarda aynı geometrik dizi: ilk hücre 2e−6c/factor, toplam 100c. Uzak alan ±100c (ön −100c, üst/alt ±100c, çıkış ucu x≈101…172c).

| Ağ | Quad | Yüzey hücre/taraf | İz | Normal | İlk hücre [c] | Normal büyüme | İz büyüme | Boyuna komşu oranı (duvar / tüm) | Min köşe sinüsü |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| kaba | 33792 | 128 | 48 | 96 | 2e−6 | 1.182 | 1.193 | 1.19 / 1.25 | .707 |
| orta | 76032 | 192 | 72 | 144 | 1.33e−6 | 1.117 | 1.125 | 1.12 / 1.16 | .707 |
| ince | 135168 | 256 | 96 | 192 | 1e−6 | 1.087 | 1.092 | 1.09 / 1.12 | .707 |

Min köşe sinüsü .707 yalnız çıkış ucundaki 45° iz ışınlarında; duvar komşuluğunda ≥.97 (iz yelpazesiz ilk sürümde tüm ağ .971). Işının gerçek duvar normalinden en büyük sapması 11.8° (TE çentiği/alt firar içbükeyi). Negatif alan/köşe, nonmanifold kenar, sınır uyumsuzluğu yok. Önceki dört bloklu ağ: .277 ve 30c; resmi SU2 ağı: .371 ve 100c. [Denetim](../validation/results/rae2822_v2_mesh_audit.json). Kaba ağda "boyuna ≤1.2" duvarda sağlanıyor; uzak alan iz yelpazesinde 1.25'e çıkıyor (orta/ince ≤1.16). Gerçek y+max (1000. iterasyon) kaba ağda .81.

Geometri: `validation/reference/rae2822.dat` (gitignore) kayıptı; önceki koşunun `geometry.json`'undan (ayrıştırılmış Selig noktaları, 129 nokta) yeniden yazıldı; kaynak ve hash'ler `rae2822.source.json`'da (özgün UIUC dosya SHA256 1b1f9575…; başlık farklı olduğundan yeni dosyanın hash'i farklı).

### NASA NPARC referansı yeniden üretildi

`cp.exp.gen`, `cfpost.cp.com`, `raetaf01.html` https://www.grc.nasa.gov/www/wind/valid/raetaf/raetaf01/ adresinden repo dışında ayrı klasöre (`C:/hz750run/download_nparc_raetaf01`) indirildi ve `python -I validation/fetch_reference.py --experiment --from-dir …` ile işlendi. SHA256: cp.exp.gen 498b8ccc63348bc5b1007f5c5d61cdd24283159a728f1f56c17b8ba73ed3658b, cfpost.cp.com 021a86151d540c6b02b6e5b574a482c73949029b23717845f1a058ee072dadda, raetaf01.html 7e026dbabb65ef98132c8c52b46f199c03013b01fdbfd9f21dc7b1422330c7fd. Üst dal 54, alt dal 50 nokta; dosya −Cp sakladığı (üst yüzeyde +1.2) için işaret ters çevrildi. CL/CD/CM ikincil kaynak (değişmedi). Çıktı: `validation/reference/rae2822.local.json`.

### RAE2822 kaba koşuları: kapı geçmedi, PENDING

| Koşu | Ayar | Sonuç |
|---|---|---|
| `pilot_v2_rae_coarse_mg3` (yelpazesiz ağ) | resmi MG3 W-cycle, CFL 2.5, JST | 1352. iterasyonda residual>1e20, FAILED ([kayıt](../validation/results/rae2822_SA/pilot_v2_mg3_coarse.json)) |
| `rae2822_SA_coarse_mc7fsy5j` (son ağ, runner) | resmi MG3 | ~1339. iterasyonda residual>1e20, FAILED ([kayıt](../validation/results/rae2822_SA/pilot_v2b_mg3_coarse_failed.json)) |
| `rae2822_SA_coarse_8g8g3qfq` (yelpazesiz ağ, runner) | MG0 + CFL_ADAPT | ρ residual ≈−4.75'te durağan; ~2100 iterasyonda durduruldu |
| `rae2822_SA_coarse_gr1q2bko` (son ağ, runner) | MG0 + CFL_ADAPT, ITER 30000, 7200 s | rapor yazılırken **çalışıyordu**; ara durum aşağıda |

Son koşunun ara görüntüsü ([anlık kayıt](../validation/results/rae2822_SA/coarse_mg0_snapshot.json), 1844. iterasyon; Cp 1000. iterasyon yüzeyinden): CL=.7299 (ikincil .743'e −%1.76), CD=.013447 (+%5.89), Cm hatası +%4.29, **Cp RMSE=.0924** (104 nokta, tam kapsam; eşik .08), y+max .81. Proje kapısı geçmiyor: bağıl Cauchy100 1.65e−5, ρ düşüşü 2.78, ν̃ düşüşü −.18 mertebe. 7946. iterasyonda ρ −4.88, CL .7222, CD .01287 (hâlâ kayıyor). Sonuç düzeyi resmi ağ+resmi cfg ile (CL .7236, CD .013449, Cp RMSE .0984) aynı; fiziksel çözüm makul ama iteratif yakınsama yok. Koşu bitince runner sonucu `validation/results/rae2822_SA/coarse.json`'a yazılacak; 30000 iterasyon 7200 s'ye sığmazsa runner BLOCKED (süre) kaydeder. Bu koşu paralel FEM commit'inden (c09dead, fem/*.py) önce başladığından kaydı üç-ağ çalışmasında STALE sayılır; yeniden koşulmalı.

Tanı (`C:/hz750run/pilot_v2b_rae_resid`, MG0 restart'tan 30 iterasyon, hacim residual çıktısı): ρ, momentum, enerji ve ν̃ residual tepeleri iz kesiti üzerinde (y=0, x≈1.2–2.0c) toplanıyor. İz kesitinin iki yanındaki hücreler duvar değeri 2e−6c kalınlığında, boyuna 0.004–15c (en-boy oranı 1e3–1e7). İz-kesiti ilk aralığını x ile büyüten bir deneme köşe sinüsünü .20'ye düşürdü (ışınlar arası katman eğimi) ve geri alındı. Resmi ağ hibrittir (iz bölgesi üçgen) ve aynı çözücüyle MG3'te yakınsar.

**Karar:** RAE kendi-ağ çalışması **PENDING**: kaba ağ proje kapısını geçmediği için orta/ince koşulmadı; GCI ve Cp/CL/CD kabulü yok. Eşikler değiştirilmedi.

### Açık kalanlar

1. RAE iz kesiti: iz bölgesinde normal dağılımı x ile gevşeten ama katman eğimini sınırlayan bir ağ (ayrı iz bloğu + eliptik/hiperbolik düzgünleştirme) ya da iz bölgesinde hibrit ağ. Ardından MG3 ve MG0 kaba yeniden; geçerse orta/ince + study.
2. `rae2822_SA_coarse_gr1q2bko` sonucu bittiğinde ayrıca kaydedilmeli (STALE).
3. SST düz levha/RAE, profil (64A010) taraması, Mcrit: değişmedi, açık.
4. `thermal_1d` çalışması params.py değişikliği nedeniyle STALE (bu turla ilgisiz); cantilever, coupon ve flat_plate güncel kodla kabul durumunda.

## Iter5 v3 (2026-11-08): iz kesiti ağı, RAE kaba kapı, GCI ve STALE kuralları

Bu tur grup 1 incelemesinde yapıldı ([inceleme raporu](../reviews/grup1_cfd_dogrulama.md)). Kod değişiklikleri: `cfd/structured_airfoil.py` (iz kesiti ağı), `validation/convergence.py` (GCI emniyet katsayısı), `validation/study.py` ve `validation/run_case.py` (STALE kapsamı), testler (33 test geçti). Kabul eşikleri değişmedi.

### v2 MG0 kaba koşusunun sonucu (`rae2822_SA_coarse_gr1q2bko`)

30000 iterasyon, 7064 s. **UNCONVERGED:** bağıl Cauchy100 1.46e−7 sağlandı ama ρ düşüşü 3.55, ν̃ düşüşü 0.30 mertebe (<4); enerji residual'ı başlangıçtan beri ancak 3.5 mertebe düştü (log +0.004). Residual'lar 30000 iterasyon boyunca yaklaşık 0.03 mertebe/1000 iterasyon hızla düşüyordu; bu hızla ν̃ kapısı ~185000 iterasyon isterdi. Son değerler CL .72019, CD .012629, Cp RMSE .0980. Kayıt ayrıca **STALE**: koşu başladıktan sonra `validation/convergence.py`, `study.py` ve `cfd/cases.py` değişti (0208319). Arşiv: [v2_mg0_coarse_unconverged.json](../validation/results/rae2822_SA/v2_mg0_coarse_unconverged.json).

### İz kesiti ağı

v2'de bütün ışınlar aynı katman dizisini kullandığı için iz kesitinin iki yanındaki hücreler 2e−6c kalınlığında, 0.004–15c uzunluğundaydı (en-boy 1e3–1e7). v3'te iz düğümü k için ilk aralık `a_k = min(first·1.5^(k/factor), first + (ds_k − ds_TE)/100)` ve katman mesafesi `d_j = d0_j + j·(a_k − first)`. TE'de a=first, TE'den ~0.3c sonra iz kesiti en-boy oranı ≈100, iz ucunda a=.162/.111/.084c (kaba/orta/ince). Toplamsal karışım normal büyümeyi duvar dizisinin oranında tutar (1.18/1.12/1.09). Dış katmanlar korunduğu için TE yakınında katman eğimi oluşmaz; v2'de denenen ışın başına ayrı geometrik dizi köşe sinüsünü .20'ye düşürmüştü. Min köşe sinüsü .655 (yalnız 100c'deki 45° çıkış yelpazesinde; v2 .707); negatif alan/köşe, nonmanifold kenar ve sınır uyumsuzluğu yok. Hücre sayıları değişmedi (33792/76032/135168). Uzak alan çıkış ucu x≈183c.

### RAE2822 kaba koşuları (v3 ağı)

| Koşu | Ayar | Sonuç |
|---|---|---|
| `rae2822_SA_coarse_ifc9r858` (runner) | resmi MG3 W-cycle, CFL 2.5 | 1590. iterasyonda residual > 1e20, **FAILED** ([kayıt](../validation/results/rae2822_SA/pilot_v3_mg3_coarse_failed.json)). İz düzeltmesi MG3 ıraksamasını gidermedi. |
| `pilot_v3_rae_coarse_mg0` (pilot, runner dışı) | MG0 + CFL_ADAPT | ~4150 iterasyonda proje kapısı; SU2 durma ölçütüyle bitti |
| `rae2822_SA_coarse_yw4jh4om` (runner) | MG0 + CFL_ADAPT, aynı ağ/cfg | **COMPUTED**, 4292 iterasyon, 2411 s |

Kaba resmi kayıt ([coarse.json](../validation/results/rae2822_SA/coarse.json)): bağıl Cauchy100 4.0e−9, ρ/ν̃ düşüşü 7.82/4.18 mertebe, enerji 7.8 mertebe, y+max .81. CL .72018 (ikincil .743'e −%3.07), CD .012605 (.0127'ye −%0.75), Cm −.0886 (+%6.7), **Cp RMSE .0982 > .08**. Aynı ağ ailesinde v2'nin yakınsamamış değerleri (CL .72019, CD .012629) yakınsamış sonuca çok yakındı; v3'ün katkısı sonucu değil, iteratif yakınsamayı (30000 → 4292 iterasyon) sağlamaktır.

**Cp RMSE neden yüksek:** hatanın büyük kısmı tek bir deney noktasından geliyor. NASA `cp.exp.gen` üst dalında x/c=.0002 noktası Cp −.42 veriyor; komşuları x/c=.0008'de +.10 ve x/c=0'da +.83. Bu durma noktasında fiziksel değil, bozuk bir basınç deliği gibi görünüyor. Ayrıca x'e göre enterpolasyon bu bölgede kötü koşullu (x ≈ s²). x/c<.002 olan noktalar dışarıda bırakılınca RMSE .048 (96 nokta) oluyor; geri kalan en büyük hata şok konumu (x/c .525–.575, CFD şoku ~.02c önde). Bu bir **ölçüt tanımı** sorunu; eşik ve değerlendirme kümesi bu turda değiştirilmedi, karar için incelemeye bırakıldı (inceleme raporu Ö0).

### Orta ve ince ağ

| Ağ | Koşu | İterasyon (7200 s) | Cauchy100 | ρ / ν̃ düşüşü | CL | CD | Durum |
|---|---|---:|---:|---|---:|---:|---|
| orta (76032) | `rae2822_SA_medium_fukf2y92` | 7765 | 1.6e−8 | 7.08 / 3.62 | .72754 | .012466 | **BLOCKED (süre)** |
| ince (135168) | `rae2822_SA_fine_ifxhcl0i` | 4384 | 4.5e−6 | 4.17 / 1.31 | .73211 | .012523 | **BLOCKED (süre)** |

İkisi de kaba koşuyla paralel ve diğer ajanların FEM işleriyle paylaşılan makinede, tek iş parçacığıyla koştu (orta ≈1.1, ince ≈0.6 iterasyon/s; yük yokken kaba ağ ≈4 iterasyon/s). Orta ağ kapıya çok yaklaştı (ν̃ düşüşü 3.62/4), ince ağ uzak. Son değerler yakınsamış sayılmaz ve GCI'ye girmez. **Üç ağ çalışması PENDING.** Sonraki adım: makine boşken orta ağı tek başına yeniden koşmak (tahmin 1–1.5 saat) ve ince ağ için 2 saat sınırına sığmayacağından restart'tan devam eden bir RAE runner'ı (düz levhadaki `cfd/continue_flatplate.py` gibi, kapı birleşik geçmişte) yazmak. Proje kuralı (tek koşu ≤2 saat) bu tur aşılmadı.

### Düz levha: GCI emniyet katsayısı

Gözlenen mertebe p=.434, formal 2'den çok uzak. Fs=1.25 asimptotik bölgedeki üç ağ çözümleri içindir. CFD vakalarında |p−2|/2 > .1 olduğunda artık `p_kullanılan = min(max(.5, p), 2)` ve `Fs = 3` (Roache; Oberkampf & Roy 2010). Üç ağ aynı kod ve cfg ile yeniden koşuldu (kaynak değişikliği nedeniyle STALE idi); Cf değerleri bitwise aynı çıktı (.0028542517/.0028586462/.0028613266). **İnce GCI %1.82** (önceki %0.88), Richardson .0028815; durum **BENCHMARK_ACCEPTED** korunur. Düşük p'nin olası nedenleri: ortalama Cf'ye giren ön kenar tekilliği ve birinci mertebe ν̃ konveksiyonu (MUSCL_TURB=NO).

### Kapı ve STALE zinciri

`study.evaluate` artık bir kaydı yalnız vakanın çalışma anında import ettiği kaynaklar değişince eskimiş sayar: `validation/{__init__,common,convergence,run_case,study}.py` + alan klasörü (`cfd/`; termalde `thermal/` + `fem/cases.py`). Testler, rapor/indirme araçları ve başka alanın dosyaları kaydı eskitmez. Benchmarklar `params.py`'ye ve uçak tasarım dosyalarına bağlanmaz. Eskimiş kayıt çalışma eksikken de STALE gösterilir (önceden PENDING'in arkasında kalıyordu). Önkoşul zinciri (airfoil/aircraft/inlet ← rae2822 + flat_plate; engine_thermal ← thermal_1d) ve aynı solver hash'i kuralı değişmedi.

`thermal_1d` yeniden koşuldu: **BENCHMARK_ACCEPTED** (357.15 K, 1600 W/m², EXACT_OR_ROUNDOFF). Altı motor termal senaryosu yeniden koşuldu; sayılar docs/10 §10.6 tablosuyla aynı.
