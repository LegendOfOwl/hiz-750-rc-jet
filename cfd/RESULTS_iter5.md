# HIZ-750 iter5 CFD — çalışma kaydı

Bu çalışma henüz CFD doğrulamasını kapatmadı. Düz levhada iki ağ güncel yakınsama kapısını geçti, ince ağ ve üretilen RAE kaba ağı diverge oldu. docs/10, kök README/CHANGELOG, params, FEM ve thermal kaynakları değiştirilmedi.

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
