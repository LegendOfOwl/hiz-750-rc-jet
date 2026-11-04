# Yapısal FEM

## Konsol doğrulaması

`python validation/run_case.py cantilever --study`: 1×.05×.01 m konsol, E=210 GPa, ν=.3, rho=7800 kg/m³. Uç kenarında tutarlı quadratic kenar yükü toplam 1 N, root tam ankastre. gmsh quad8 → CalculiX S8R; 20/80/320 eleman. Sehim `F L³/(3EI)`, f1 `1.875104²/(2π L²) sqrt(EI/(rho A))`. İlk beş frekans (eğilme/in-plane/torsion karışık olabilir), reaksiyon dengesi, sehim ve GCI kaydedilir. Euler–Bernoulli referansıyla küçük shear/Poisson kök farkı beklenir; bu farkı daha fazla ağla yok etmek zorunlu değildir.

Bu benchmark isotropiktir. **CLT laminat coupon benchmarkı henüz uygulanmadı**; aynı solverın konsolda doğru sonuç vermesi kompozit tabaka yönlerini doğrulamaz. Bir sonraki mekanik kabul adımı, [CalculiX composite S8R/S6 örnekleri](https://www.dhondt.de/ccx_2.22.pdf) ile ABD matrisi/kiriş limiti karşılaştırmasıdır. S4 composite kullanılmaz.

## Kanat için girdiler ve taslak

```powershell
& $py fem/export_wing_inputs.py --output C:/hz750run/wing_inputs.json
& $py validation/run_case.py wing --prepare-only --level coarse
```

`wing_shell.py`, `structures.py.wing_section_model()` içindeki n_ud(y), n_web(y), kapak genişliği, kabuk planı, yakıt/mass dağılımını okur. Kiriş önü (x≤arka kiriş .55c) / arkası için 3/1 kat **sandviç yüzü**, iki yüz arasında 2 mm Rohacell kullanılır. UD kapaklar iki kirişte üst-alt iç yüzdedir; kumaş span'a ±45° dokuma, UD span yönündedir. Kabuk S8R COMPOSITE; web'ler kumaş; normal ve offset görsel olarak kontrol edilmeli.

Üretilen model **DRAFT**: ST.yt64 yaklaşık kesiti, .005c düz burun web'i, tüm arka kabuk bağlı; gerçek kontrol yüzeyi kesikleri, kaburgalar, yapıştırıcı, cıvata esnekliği yok. İnce burun/TE'de sonlu kalınlıklı sandviçlerin fiziksel çakışması özellikle kontrol edilmeli; bu bölgelerde gerçek imalat geçişi olmadan deck tasarım modeli olamaz. Runner bunu normal koşuda BLOCKED bırakır. Yalnız ayar denemesi için `--diagnostic` ile çözmek mümkündür; sonuç geçerli kanat doğrulaması sayılmaz.

Taslak malzeme sabitleri, görevde verilen tipik değerlerle **varsayım (üretici verisiyle değiştirilecek)** olarak tamamlandı. `params.py` veya `structures.py` değiştirilmedi. Depoda olan sabitler önceliklidir:

| Malzeme | Depodan korunan | Tamamlama varsayımı |
|---|---|---|
| UD | E1=125 GPa, rho=1550, t=.20 mm, Xt=2100/Xc=1200 MPa | E2=E3=9 GPa; G12=G13=5, G23=3.46 GPa; ν12=ν13=ν23=.30; Yt=50, Yc=200, S12=80 MPa |
| Kumaş | E1=E2=55 GPa, rho=1500, t=.178 mm; kayma izin 80 MPa | G12=4.5 GPa; E3=9, G13=G23=4.5 GPa; ν12=.05, ν13=ν23=.30; Xt=Xc=Yt=Yc=600 MPa |
| Rohacell | rho=52, t=2 mm | E1=E2=E3=70 MPa, tüm G=19 MPa, ν=.30; izotropik E–G bağıntısı dayatılmayan ortotropik yaklaşım |

`MAT.FAB.G45=25 GPa` global ±45 dokumanın etkin kayma yaklaşımıdır; **lamina G12** sanılıp 25 GPa girilmez. Tam 3B ortotropik sabitler ölçülmedi. F12=`−.5 sqrt(F11 F22)` bir etkileşim varsayımıdır. Bunlar katalog allowables veya B-basis veri değildir. [Toray T700S](https://www.toraycma.com/products/fibers/t700s/) fiber datası tek başına kürlenmiş laminat allowables sağlamaz.

Root y=.035 m (eski FE ile aynı), 18g Schrenk kaldırması; statikte atalet rahatlatması yok (konservatif toplam kaldırma). Modalde yakıt ve 2 servo kütlesi eklenir. Pozitif kabuk–1D kütle farkı kaburga/boya/donanım için rijitliksiz kütle olarak eklenir; kabuk fazla ağırsa negatif kütleyle düzeltme yapılmaz, fark raporlanır. Geometrik/atalet dağılımı ve %kütle farkı host'ta incelenmeli. Yakıt dolu/boş modeller ayrı deck olarak karşılaştırılmalı; otomatik taslak doludur.

## İncelenmiş modelin koşulması

```powershell
& $py validation/run_case.py wing --level coarse --deck C:/hz750run/wing/coarse.inp --mesh-review C:/hz750run/wing/coarse.review.json
# medium/fine aynı geometri, kat planı, kütle ve yükle ayrı çalıştırılır.
& $py validation/study.py fem/results/wing
```

[wing_review.example.json](wing_review.example.json) üretim onayı değildir. Deck kendi içinde kapalı olmalı; *INCLUDE dosyaları birleştirilmeli. Ölçü SI, S8R/S6, NALL/TIP/ROOT setleri, statik *NODE PRINT TIP U/ROOT RF, *EL PRINT GLOBAL=NO S, ardından *FREQUENCY 5 veya 8, NALL U istenir. Gerçek ccx açılmış DOF sayısı ≤200k kontrol edilir. `h` üç mesh için aynı tanımdaki karakteristik uzunluktur. Taslak materyal senaryosunu kabul edilebilir varsayımla kullanmak, üretici verisi doğrulaması değildir.

Modal DAT ve şekillerden 1B/1T **mod şekliyle** eşleştirilir; ilk/4. frekans otomatik etiket değildir. Otomatik torsion indicator yalnız ön taramadır. Beş frekans için GCI raporlanır, ancak mod geçişinde sıra bazlı GCI geçersiz olabilir. Kök singularity gerilmesi yerine kökten uzakta tabaka gerilmesi, kapak/web/skin strain ve burkulma ayrı incelenmeli.

Tsai–Wu için stress çıktısının her tabakasını kendi 1–2 ekseninde CSV'ye aktarın: `element,layer,material,s11,s22,s12` (Pa). CalculiX integration-point→layer sırası **incelenmeden** otomatik varsayılmadı. Ardından:

```powershell
& $py fem/laminate_post.py C:/hz750run/ply_stress.csv --model fem/results/wing/coarse_wing_model.json --output fem/results/wing/tsai_wu.json
```

Ham FI ve KD=.544 duyarlılığı ayrı yazılır; köpüğe fiber Tsai–Wu uygulanmaz. Kopma, mikroburkulma, çekirdek kayması, debonding ve fastener testleri bu criterion ile kapsanmaz. f1T farkından flutter hızı doğrudan ölçeklenemez; yeni kütle/rijitlik/mod şekilleriyle aeroelastik çözüm yeniden gerekir.
