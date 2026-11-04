# CFD uygulamaları

Runner: `python validation/run_case.py <case> --level coarse --model SA|SST`.
İkinci turda SU2/gmsh escalation ile çalıştırıldı. Kaba pilotlar yakınsamadığı için tasarım karşılaştırmasında kabul edilmez; [results/status.json](results/status.json) koşu dizinlerini gösterir. `validation/run_native_su2.py`, resmi v8.2 config+137×97 ağını ayrıca sınar. Bu kontrol tek ağdır, GCI/deney kabulü değildir.

## 2B vakalar

Gerçek ikinci tur kontrolleri: düz levhada BL uç köşe quads yerine iki transfinite blok kullanıldı. Resmi SU2 ayarları total inlet/static outlet, Green–Gauss, MG3 ve MUSCL_TURB=NO ile ayrıca denendi; kendi ağında FGMRES hatası verdi. Resmi config+resmi137×97 ağ6000 iterasyonda tamamlandı (Cf=.002849; Schlichting farkı−%5.151), ancak tek ağ sonucu üç-ağ kabulü değildir. RAE/profil pilotları UNCONVERGED olarak kaydedildi; CFD kabul eşiği değiştirilmedi.

- `rae2822`: M=.729, Re=6.5e6, α=2.31°, T=288.15 K; düzeltilmiş Case 6. Sayısal deney verisi [referans şablonuna](../validation/reference/rae2822.example.json) kaynak gösterilerek girilmeli. Daha farklı M=.8, sabit CL=.724 olan optimizasyon tutorial'ı bu doğrulama vakasıyla aynı değildir.
- `flat_plate`: M=.2, Re_x=5e6 @ x=1 m; duvar x=0..2 m, üst sınır y=1 m, giriş önünde simetri x=−.25..0. Cf_mean=CD (`REF_AREA=2 m²`, birim açıklık); Schlichting `.455/(log10(Re_L))^2.58`, ITTC `.075/(log10(Re_L)−2)^2`, Re_L=1e7. Bunlar tam türbülanslı ortalama Cf korelasyonlarıdır; noktasal `.0592/Re_x^.2` ile karıştırılmaz. [NASA TMR](https://tmbwg.github.io/turbmodels/flatplate.html) ile benzer koşulludur, aynı ağ/BC replikası değildir.
- `airfoil`: projenin `airfoil_64a()` tanımıyla aynı **kalınlığı ölçeklenmiş 64A010**. Gerçek 64A007 diye yeni bir koordinat seti varsayılmaz. M=.61–.75, Re=4.5e6, α=0–2°. Birim normalize veterle Re/M eşleştirilir; buradan tam uçak kuvveti çıkarılmaz. `neuralfoil.json` hem aynı Mach hem eski M=0 değerini kaydeder. Tam türbülans RANS ile ncrit=9 geçişli NeuralFoil farkı sayısal hata değildir.

gmsh 2B duvar katmanı ilk yüksekliği kaba 2e−6 c, orta 1e−6 c, ince .5e−6 c; katman bölgesi .025c, büyüme oranı da rafine edilir. Profil uzak sınırı 30c; ayrıca 60c alan testi önerilir. `y+max≤1`, tüm RMS log residual <−6 ve son 100 iterasyonda ΔCD<1e−5 / ΔCL<1e−4 olmadan sonuç COMPUTED olamaz. Eşik sağlanmazsa iterasyon artırın/ağı düzeltin. Yoğunluk residual'ının −8'e gelmesi tek başına yeterli değildir.

Mcrit: yüzey Cp_min, sonik Cp* ile karşılaştırılır. Sonik nokta görülen ilk Mach bir **üst sınır**, önceki subsonik nokta alt sınırdır; bütün tarama subsonikse Mcrit>.75 denebilir, kesin bir Mcrit=.75 sonucu verilemez. Mcrit ile drag divergence farklıdır. Cp karşılaştırması shock yakınında noktaları/pürüzlülük/transition varsayımını da incelemeli.

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
