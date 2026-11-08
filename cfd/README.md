# CFD uygulamaları

Güncel sonuçlar: [RESULTS_iter5.md](RESULTS_iter5.md). Solver exit-success fiziksel doğrulama kabulü değildir.

## 2B vakalar

Runner: `python validation/run_case.py flat_plate --study --model SA`. RAE önce yalnız kaba ağda çalıştırılır; yakınsarsa orta/ince ayrıca başlatılır. Ağ başına sınır 7200 s.

- Düz levha: resmi SU2 137×97 topolojisine benzer iki transfinite quad blok; giriş x=−1/3, plaka x=0..2, üst y=1. Ön kenarda boyuna sıklaştırma kullanılır. Ağlar 13056/29376/52224 hücre; h oranları 1.5/1.333. İlk katman 2e−6/1.333e−6/1e−6 m. **Çözücü ayarı (iter5 v2):** ROE+MUSCL, GREEN_GAUSS, MGLEVEL=0 (multigrid yok), CFL_NUMBER=1, CFL_ADAPT=YES, CFL_ADAPT_PARAM=(0.5, 1.5, 1.0, 100.0), FGMRES + **ILU** önkoşullayıcı, LINEAR_SOLVER_ERROR=1e−6. MG3+CFL10 ince ağı ıraksatıyordu. SU2 durma ölçütü CONV_FIELD=(RMS_NU_TILDE, DRAG): ν̃ residual'ı ≤−9.3 (başlangıç ≈−5 → ≥4 mertebe) VE DRAG-Cauchy ≤1e−8; yalnız DRAG-Cauchy 1e−6 proje kapısından erken durduruyordu. Üç ağ aynı cfg ile koşulur.
- RAE2822: Claude yönlendirmesiyle **Case 6**, M=.729, α=2.31°, Re=6.5e6. NASA NPARC Cp birincil; AGARD'a atfedilen CL=.743/CD=.0127/CM=−.095 ikincildir, birincil integral dosya doğrulanmadı. `python validation/fetch_reference.py --experiment` kaynakları ve hashleri üretir. Olası kabul etiketi `BENCHMARK_ACCEPTED (CL/CD ikincil kaynak)` olur. Case 9 ayrı çalışmadır.
- Profil C-ağı (RAE ve proje profili, `structured_airfoil.py`, iter5 v2): tek bloklu yapısal C-ağı; duvar normalinden düz ışınlar (ışın açısı C-eğrisi boyunca monoton yapılır → ışınlar kesişmez; TE çentiği ve alt firar içbükeyinde normalden en çok ≈12° sapma), uzak alan ve iz uzunluğu 100c, iz ışınları çıkışa doğru 45° yelpazelenir, iz kesiti ortak düğümlü. Kaba/orta/ince 33792/76032/135168 quad; yüzey 128/192/256 hücre/taraf, iz 48/72/96, normal 96/144/192; ilk hücre 2e−6/1.33e−6/1e−6 c; normal büyüme 1.18/1.12/1.09, iz 1.19/1.12/1.09, boyuna komşu oranı ≤1.2; min köşe sinüsü .655 (yalnız 100c'deki 45° iz çıkış yelpazesinde; duvar yakınında ≥.97). İter5 v3: iz kesiti ilk aralığı TE'de duvar değerinden başlayıp iz hücresi başına en çok 1.5 kat büyüyerek ds/100'e gider (`WAKE_ASPECT`, `WAKE_RAMP`); v2'deki 1e3–1e7 en-boy oranlı iz hücreleri kalktı. RAE: resmi MG3 ayarı bu ağda hâlâ ıraksar (1590. iterasyon); `--rae-scheme mg0` (MG0+CFL_ADAPT) kaba ağda 4292 iterasyonda proje kapısını geçer (RESULTS_iter5.md, iter5 v3). gmsh gerekmez (numpy/scipy). Kapalı keskin TE gerekir; geometri sessizce değiştirilmez. Proje profili geometrisi `aero/aero_analysis.py` ile aynı kalınlığı ölçeklenmiş 64A010; bağımsız gerçek 64A007 koordinatı değildir.

Bu turdaki Claude talimatıyla yakınsama: son 100 adımda ortalama mutlak CD adımı / ortalama |CD| <1e−6 ve başlangıçtan rho ile ν̃ residual düşüşü ≥4 mertebe; y+max≤1. SST'de k/omega düşüşleri ayrı aranır. Enerji residual'ı bilgi olarak raporlanır. SU2 DRAG Cauchy duruşu residual düşüşünü tek başına garanti etmez; postprocessor ayrıca denetler. Eski tüm-RMS<−6 kapısı tarihsel kayıtlarda bulunabilir. `cfd/reassess.py` özgün kaynak kayıtlarını değiştirmeden geçmişleri yeniden değerlendirir.

GCI yalnız üç yakınsamış, tutarlı ağla hesaplanır. CL hata sınırı %5, CD %15, Cp RMSE .08 ve ince GCI %5 korunur. `cfd/neuralfoil_baseline.py` M0/eş-Mach bazlarını hesaplar; bu tablo RANS doğrulaması değildir. Mcrit için yakınsamış Cp_min/Cp* taraması gerekir.

## 3B hazırlık: B ve C

İkinci turda `draft_domains.py` ile iki **coarse DRAFT** üretildi: dış zarf5885, kanal4727 tetra. Dış zarfta konik/silindirik gövde ve dörtgen kanat/kuyruk vardır; izole kanalda CAD rapor kesitleri16 kenarla yaklaştırılır. Bunlar uçuş CAD'inin birebir fluid modeli değildir; RANS koşulmadı. `*_draft.json` dosyaları ham klasörleri/hash'leri kaydeder. STEP round-trip sonrasında yüzey tag'leri yeniden çıkarılır; export öncesi tag'ler yeniden kullanılmaz.

Montaj STEP'i dolly, tank, motor gibi iç katılar içerir; akış bölgesi değildir. `inlet_duct.step` de katı **kanal duvarıdır**, iç akış hacmi değildir. Otomatik temizleme ve 3B prizma katmanı bu pakette tamamlanmadı. Hacim/topoloji işlemlerini host'ta inceleyin; yalnız tetra ağ üretilmesini doğru RANS ağı saymayın.

```powershell
& $py cfd/prepare_3d.py C:/hz750run/fluid.step --scale .001 --output C:/hz750run/mesh
# surfaces.json'da görülen yüzey tag'leriyle bir marker map JSON oluşturun:
# ör. {"WALL":[...],"FARFIELD":[...],"SYMMETRY":[...]}
& $py cfd/prepare_3d.py C:/hz750run/fluid.step --scale .001 --output C:/hz750run/mesh --markers C:/hz750run/map.json
```

Bu çıktı **DRAFT_NOT_RANS_READY**: duvar prizması yoktur ve runner tarafından incelenmiş ağ yerine kabul edilmez. STEP'in birimi `--scale` ile açık verilir. 2M hücre aşılırsa SU2 ağı yazılmaz. Mesh'i gmsh SDK/GUI ile sınır katmanlı hale getirip [mesh_review.example.json](mesh_review.example.json) kopyasını gerçek SHA256, seviye, hücre sayısı ve denetim bulgularıyla doldurun. Örnek dosyadaki false alanları inceleme yapılmadan true yapmayın. Üç ağ aynı geometri/domain ve aynı inceltme ailesine ait olmalı.

**B / aircraft:** gövde+kanat+iki kuyruk birleşmiş watertight dış zarf, y≥0 yarı model; iç aksam ve dolly çıkarılır. WALL, FARFIELD, SYMMETRY (y=0), dış sınır en az ~10 gövde boyu; boş inlet/egzoz delikleri varsa kapatma veya motor akış koşulu açıkça seçilmeli. Geometri sadeleştirmesini basınç/sürtünme/eksik bileşen bütçesiyle raporlayın. `REF_AREA=S/2`; raporlanan kuvvet iki katıyla tam uçaktır. 300 m ISA, params V_TARGET; α eski trim≈.086° ile başlanır, aynı CL ve trim korunmadan D=154 N karşılaştırması eşdeğer değildir. SA/SST ve iki uzak alan boyutu kontrol edilmeli. İsimsiz yansıyan yüzeyler veya açık uçlar kabul edilmez.

**C / inlet:** tam kanal + dudak öncesi dış gövde akışı. FARFIELD, WALL, ENGINE; yarım debi kullanılmaz. Girişte yalnız uniform toplam basınç verip kanal kaybını hesaplamak, eski modeldeki sınır tabaka yutma kaybını sınamaz. Dış hacim dudak/rampadan önce en az alığın x konumuna kadar gövde sınır tabakasını geliştirmeli veya doğrulanmış bir profili taşımak gerekir. İnceleme kaydında `ingested_boundary_layer` bunu belgeler. Motor debisi params `mdot_air × σ × (1+.6 M²)`; SU2 `FAN_FACE_MDOT`, tüm motor yüzü. Sayısal debi hedefe %1 içinde gelmeli.

`face_samples.py`, ENGINE üçgen/quad yüzeylerinden rho, u_n, p_t örnekler. Motor diski x-sabit ve merkezi y=z=0 kabul edilir. Geri akış varsa postprocessor durur; değerleri kırpıp sahte recovery üretmez. pt/p ideal gazdan gelir. Recovery kütle ağırlıklı ve alan ağırlıklı ayrı yazılır. DC60 sözleşmesi:

`(alan-ortalama pt − en düşük 60° sektör alan-ortalama pt) / alan-ortalama(0.5 rho u_n²)`.

1° kayan sektör taraması, tam disk ve yeterli açısal/radyal örnekleme gerekir. Farklı literatür DC60 tanımlarının payda/ağırlıklarıyla doğrudan eşitlik iddia edilmez. Bu paket DC60 için deneysel S-kanal benchmarkı içermez; sonuç model/şema duyarlılığı ve motor üreticisi distorsiyon limitiyle birlikte incelenmelidir.
