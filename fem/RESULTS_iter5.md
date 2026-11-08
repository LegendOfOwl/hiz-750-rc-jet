# HIZ-750 iter5 — Yapısal FEM sonuçları (CLT kupon + S8R kompozit kanat)

Durum: **CLT kupon benchmarkı BENCHMARK_ACCEPTED**, **konsol benchmarkı BENCHMARK_ACCEPTED** (SPOOLES, tek iş
parçacığı ile yeniden koşuldu), **kanat REVIEW_REQUIRED** (varsayımsal malzeme sabitleri, imalat detayı yok;
tasarım kabulü değildir). Araç: CalculiX 2.20 (`ccx_static.exe`), gmsh 4.15.2, Python 3.12. Ham çözümler
`C:/hz750run` altında; repoda deck, özet JSON ve grafikler.

Yeniden üretim:

```powershell
$env:CCX="C:/hz750tools/CalculiX/calculix_2.20_4win/ccx_static.exe"
& $py validation/run_case.py cantilever --study --threads 1
& $py validation/run_case.py coupon --study --threads 1
& $py fem/run_wing_study.py        # dolu + boş tank, üç ağ, otomatik inceleme -> --deck/--mesh-review
& $py fem/wing_compare.py          # kiriş çapraz kontrolü, fe_modal, flutter ölçeklemesi
& $py -m unittest validation.test_validation validation.test_cfd_mesh   # inceleme sonrası 28 test, hepsi geçti
```

## 0. Çözücü bulguları (önemli)

1. **Çok iş parçacıklı sonuç hesabı güvenilmez.** CCX 2.20 Windows yapısında `OMP_NUM_THREADS/CCX_NPROC_RESULTS=4`
   ile aynı kanat deck'i bir elemanda ~1 GPa sahte gerilme ve tekrarlanamayan frekanslar (4. mod 283.3 ↔ 282.8 Hz)
   verdi. Tek iş parçacığında sonuç temiz ve tekrarlanabilir. Tüm iter5 koşuları `--threads 1`.
2. **PaStiX (varsayılan) gürültülü/askıda.** Serbest yüzen kupon sisteminde %1–%100 salınım üretti, konsol orta
   ağ *FREQUENCY adımında askıda kaldı. Kupon, konsol ve kanat `SOLVER=SPOOLES` kullanır; konsol benchmarkı bu
   çözücüyle yeniden kabul edildi (sehim −0.74 %, f1 +0.49 %, GCI < 0.3 %).
3. **MASS elemanı kompozit kabuklu modelde çalışmıyor** (`changekon: element type unknown: MASS`). Yapısal olmayan
   kütle, 10 µm/1 MPa NSM tabakası ve menteşe gerisi için *EQUATION'lı kaldıraç küpleriyle (C3D8) verildi.
4. **Kök BC 1-6 kullanıldığında** CCX düğüm başına "knot" üretti ve ROOT RF toplamı yükün %17'sini kaybetti;
   1-3 (genişletilmiş düğümlerin hepsi) ankastredir ve denge 2·10⁻⁷ bağıl hatayla kapanır.
5. *EL PRINT istekleri sonraki adıma taşınır (mod gerilmeleri basılır); son işlem yalnız statik adımı okur.

## 1. CLT kupon benchmarkı (`validation/results/coupon`)

Referans `fem/clt.py` (bağımsız CLT; 5 birim testi). Her laminat için tek deck'te TX/TY (kare levha, minimum
kısıt, homojen durum), SH (Nxy) ve B3 (dar şerit üç nokta eğilme; mesnet/yük hatları *EQUATION ile düzgün
çizgisel tepki, antiklastik/burulma serbest). Ölçüm yük giriş kenarlarından uzak orta yarıda. D11 ölçümü
L/8–L/4–3L/8 ikinci farkı (kayma terimi düşer), referans dar kiriş b/d11. Ağlar: membran 4/8/16², B3 8/16/32 × 4/8/16.
Kabul: üç ağın her biri |hata| ≤ %2 ve GCI ≤ %5 (yuvarlama düzeyinde salınımda üç ağ yayılımı ≤ %0.5).

İnce ağ hatası (CCX − CLT), parantezde üç ağ bağıl yayılımı:

| Laminat (alt→üst) | Ex | Ey | Gxy | D11 (b/d11) | 3N sehim | maks. tabaka σ |
|---|---|---|---|---|---|---|
| UD [0]5 | 0.000 % | 0.000 % | 0.000 % | 0.000 % | −0.007 % | 0.00 % |
| UD [+45/−45]s | −0.001 % | −0.001 % | +0.054 % | +0.004 % | −0.153 % | 0.00 % |
| Ön kabuk sandviç FAB45(3)/Rohacell 2 mm/FAB45(3) | +0.003 % | +0.003 % | +0.001 % | 0.000 % | −0.039 % | 0.03 % |
| Kök kapak UD(3)/FAB45(3)/çekirdek/FAB45(3), OFFSET=0.5, simetrik değil | +0.062 % | +0.014 % | +0.007 % | −0.023 % | −0.001 % | **1.12 %** (yayılım 0.46 %) |
| Web FAB45(3) | 0.000 % | 0.000 % | 0.000 % | 0.000 % | −0.286 % | 0.00 % |

En büyük hata %1.12 (simetrik olmayan kapak laminatında UD'ye komşu kumaş tabakası, sandviç yük girişi
sönümü). **Tümü %2 içinde → BENCHMARK_ACCEPTED.** Ayrıca doğrulanan yorumlar:
* Tabaka sırası alttan (−normal) üste; *EL PRINT GLOBAL=NO her tabaka için 8 integration point (2×2 düzlem × 2
  kalınlık) ve tabakanın kendi 1-2 eksenleri.
* OFFSET=0.5 → malzeme referans yüzeyin −normal tarafında (genişletilmiş z ∈ [−h, 0] ölçüldü). Kabuk düğüm
  çıktısı ve düğüm kuvvetleri orta yüzeydedir.
* **Sınır:** CCX kabuk genişlemesi sandviç çekirdek kaymasını (zigzag) temsil etmez; 3N sehim eşdeğer tek katmana
  uyar, sandviç teorisi ön kabukta +3.3 %, kapakta +7.3 % daha büyük sehim verir. Global kanat eğilmesi membran
  baskın olduğundan etkisi küçük; yerel panel/çekirdek kayması değerlendirmesi bu modelle yapılamaz.
* Not: 2 eleman genişlikli B3 şeridinde CCX anlamsız sonuç verdi (denklem/knot etkileşimi); en az 4 eleman kullanıldı.

## 2. Kanat modeli düzeltmeleri (`fem/wing_shell.py`)

| Taslak | Düzeltme |
|---|---|
| Tek global *ORIENTATION; 3-ekseni yüzey normali değil | Eleman başına teğet çerçeve: 1 = kiriş (sabit x/c) teğeti, 3 = eleman normali (kontrol: sapma < 2·10⁻⁶°) |
| Web kumaşı 0°, local-2 web normali → web düzleminde G=G13=4.5 GPa | Web ±45 kumaş, web düzleminde (G≈26 GPa); OFFSET=0 |
| .005c düz burun web'i; tam kapalı burun denenince uçta burun yarıçapı 0.6 mm < 1.07 mm laminat → negatif Jacobian | x/c=.01'de 6 kat burun web'i (yüzlerin birleşimi) |
| Arka kabuk firar kenarına açık | Sabit yapı x/c ≤ .75, 2 kat ±45 menteşe web'i; kontrol yüzeyi kütlesi kaldıraçla |
| Sandviç her yerde (çakışma) | Çekirdek yalnız iç boşluk ≥ 2 mm olan kaba hücrelerde; diğerleri monolitik (min boşluk +0.54 mm) |
| Kaburga yok (kesit distorsiyonu, 1T ≈ 200 Hz) | 8 sandviç kaburga, 0.086 m aralık (structures m_ribs'ten), uç ve tank kapama dahil |
| Nokta kuvvetler .25c'de iki düğümde | Schrenk 18 g, veterde 3(1−x)² (CP ~.25c), üst/alt yarı yarıya, Gauss 3×3 tutarlı kuvvetler; ΣFz hedefle 9·10⁻⁶ |
| MASS elemanı (CCX'te çalışmıyor), CG/atalet eşlenmemiş | Kaburga bölmesi başına kütle, CG tam, atalet 1D'nin %85–94'ü; yakıt kirişler arası kabukta düzgün |
| Kök 1-6 | 1-3 (yukarıya bakın) |

Kat planı ve sandviç kararı kaba hücreler üzerinden verilir (kat düşümleri kaburga hatlarında); böylece üç ağ
aynı geometriyi çözer. Ağ: açıklık 8/16/32, veter 13/26/52 kabuk elemanı/yüz; ince ağ 7168 S8R,
**CCX denklem sayısı 139 840** (≤ 200k). İnce ağ çözümü ~75 s. Otomatik inceleme `fem/wing_review.py`
(malzeme, yön, kütle, yük, bağlantı, çakışma — 6/6 geçti, `*_mesh_review.json`).

Malzeme: UD E1 = 125 GPa, kumaş E = 55 GPa (**structures.py MAT**; görev metnindeki 135/60 GPa değil — fe_modal ile
tutarlılık için repo değeri korundu, frekanslar ~√E ile ölçeklenir: 135 GPa ile ~+%4), diğerleri fem/README.md tablosu.

## 3. Statik sonuç (nihai 18 g Schrenk, atalet rahatlatması yok)

Kök momenti (y=.035) 411.9 N·m (structures yakıt rahatlatmalı y=0 değeri 447 N·m). Kuvvet dengesi 1.7·10⁻⁷.

| Büyüklük | Kaba / orta / ince | Yakınsama |
|---|---|---|
| Uç sehim (EA .30c) [mm] | 47.69 / 47.73 / 47.69 | salınımlı, yayılım 0.08 % |
| Uç burulma (akış yönü) [°] | 2.019 / 2.032 / 2.031 | salınımlı, 0.6 % |
| Tsai-Wu R_min, ilk kaburga bölmesi hariç (y > .121 m) | 3.684 / 3.517 / 3.661 | salınımlı, 4.6 % |
| Aynı, KD = .544 dayanımla | 2.004 / 1.913 / 1.992 | salınımlı |
| Tsai-Wu R_min, kök bölmesi dahil | 2.89 / 2.26 / 1.88 | **yakınsamıyor** (ankastre tekilliği) |
| UD kapak σ11 min (dış bölge) [MPa] | −237 / −250 / −257 | p = 0.78, GCI 5.0 % |

* **En kritik bölge (kökten uzak):** arka kiriş kapağının ön yarısı, y ≈ 0.15 m, UD basma σ11 = −224 MPa →
  **R = 3.66 (güvenlik payı +266 %)**; KD ile R = 1.99 (+99 %). Bölgesel R_min: arka kapak 1.88*, ön kapak 2.78,
  arka kabuk 2.67, arka web 3.16, menteşe web'i 3.32, ön kabuk 4.1 (*arka kapak kök bölmesinde, tekil).
* Kök bölmesindeki en düşük değer (R = 1.88, arka kapak iç kumaş yüzü) ağla düşüyor; rijit ankastre tekilliğidir,
  tasarım değeri olarak kullanılmamalı. Gerçek kök cıvata/çerçeve esnekliğiyle ayrıca incelenmeli.
* Çekirdek kayma gerilmesi (kök dışı) en çok 27 kPa (kaburga) — ağla artıyor (17/23/27 kPa), yakınsamadı;
  Rohacell 51 varsayılan 0.8 MPa dayanımın çok altında, ancak çekirdek kayması bu kabuk modelinde zayıf temsil ediliyor.
* Burkulma, yapıştırıcı ve cıvata kontrol edilmedi.

## 4. Modal sonuç (ilk 5 mod, ince ağ; etiketler kutu düğümlerine w = a + θ(x−x_EA) uydurmasıyla)

| Mod | Dolu tank [Hz] | Boş tank [Hz] | Şekil (eğilme/burulma/düzlem içi enerji payı, dolu) |
|---|---|---|---|
| 1 | 39.51 | 40.36 | 1B (0.98/0.02/0) |
| 2 | 124.80 | 136.95 | 2B (0.90/0.10/0) |
| 3 | **272.54** | **280.86** | **1T** (0.18/0.82/0) |
| 4 | 284.40 | 292.27 | 1. düzlem içi eğilme (0/0/0.99) |
| 5 | 296.61 | 319.98 | 3B, burulma bağlaşımlı (0.67/0.33/0) |

Üç ağ: f_1T dolu 277.69 / 273.01 / 272.54 (p = 3.3, **GCI 0.02 %**), boş 285.49 / 281.87 / 280.86 (GCI 0.17 %);
f_2B monoton (GCI < 0.02 %); f_1B salınımlı (39.55 / 39.33 / 39.51, yayılım 0.55 %, GCI tanımsız); 3B ve
düzlem içi mod salınımlı (yayılım ≤ 1.3 %). 1D modelde düzlem içi mod yoktur; ok açısı nedeniyle 3B ve üst modlar
güçlü eğilme-burulma bağlaşımlıdır. Mod şekilleri: `fem/results/wing/fine_plot.png`.

**Duyarlılık (tanılama, eski kütle eşlemesiyle):** yalnız tank+uç kaburgasıyla f_1T ≈ 198–207 Hz idi; ara
kaburgalar olmadan kesit distorsiyonu 1T'yi %25 düşürüyor ve GVT kriteri (230 Hz) sağlanmıyor. Kaburga
aralığı varsayımı f_1T için birinci derece etkendir.

## 5. fe_modal 1D ile karşılaştırma ve flutter

| | 1D fe_modal dolu | Kabuk dolu | Oran | 1D boş | Kabuk boş | Oran |
|---|---|---|---|---|---|---|
| f_1B [Hz] | 27.46 | 39.51 | 1.44 | 27.99 | 40.36 | 1.44 |
| f_2B [Hz] | 84.26 | 124.80 | 1.48 | 92.75 | 136.95 | 1.48 |
| f_1T [Hz] | 305.68 | 272.54 | **0.89** | 316.64 | 280.86 | **0.89** |

* **Eğilme:** kabuk kesitinin EI'si 1D EI'nin 1.64 (kök) – 3.2 (y = .56 m) katı. structures EI yalnız kirişler
  arası kabuğu, 12 GPa yüz modülünü ve kapak koluyla aynı z'yi kullanıyor; kabukta burun (0–.2c) ve arka sabit kabuk
  (.55–.75c) da eğilme taşıyor, ±45 kumaş yüz Ex = 15.6 GPa ve dış yüz OML'de. 1D EI muhafazakâr.
* **Burulma:** kütle, CG ve (%85–94) atalet eşlendiği halde f_1T %11 düşük. Olası nedenler: kaburgalar arası kesit
  distorsiyonu ve sandviç yüzlerde kayma esnekliği (Bredt rijit kesit varsayar), akış yönü kök ve ok açısının
  burulma-eğilme bağlaşımı, sarkan kontrol yüzeyi kütlesi. f_1T, GVT kabul kriterini (≥ 230 Hz) %18 payla sağlıyor.
* **Flutter etkisi** (`gvt.Vf_vs_fT`, yalnız f_1T ölçeği, f_B nominal; doğrusal ara değerleme):
  - Dolu: f_1T oranı 0.892 → **V_F ≈ 1185 km/h** (1D 1307 km/h, −%9.4)
  - Boş: oran 0.887 → **V_F ≈ 1194 km/h** (1D 1329 km/h, −%10.2)
  - 1080 km/h gereksinimi sağlanıyor (+%10), **1350 km/h (1.25 model payı) hedefi sağlanmıyor**; bunun için
    dolu tankta f_1T ≥ 316 Hz gerekir (fe_modal fT_min_fac_1350 = 1.033).
  - f_B'nin de 1.44× ölçeklendiği iki boyutlu ızgara değeri güvenilir değil: dolu ızgara f_B ≥ 1.4 bölgesinde mod
    değişimli tekil bir nokta içeriyor (2422 km/h) ve iki doğrusal sonuç 1634 km/h çıkıyor; boşta 1338 km/h.
    Izgaranın düzgün bölgesinde f_B artışı V_F'yi yalnız %1–3 artırıyor. Raporlanan değer f_1T-ölçekli olandır.
  - Bu yalnız frekans ölçeklemesidir; kabuk mod şekilleri (güçlü bağlaşım, düzlem içi mod), kütle dağılımı ve
    gerçek kesit özellikleriyle modal aeroelastik çözüm yeniden yapılmalı.

## 6. Kiriş teorisiyle çapraz kontrol (`fem/results/wing_compare.json/.png`)

Aynı yük, kök y = .035, Euler-Bernoulli w'' = M/EI:

| Kiriş | EI kaynağı | Uç sehim [mm] | FE / kiriş |
|---|---|---|---|
| düz (akış yönü kök, ok yok) | structures 1D | 88.8 | 0.54 |
| ok açılı EA (dik kök, cos³Λ, Λ_EA = 22.6°) | structures 1D | 112.8 | 0.42 |
| düz | kabuk kesiti | 42.0 | 1.13 |
| ok açılı EA | kabuk kesiti | 53.4 | 0.89 |

1D EI ile fark %46–58 (> %15). **Nedeni EI farkı** (yukarıda): kabuk kesitinin EI'si ile hesaplanan kiriş FE'yi
iki idealizasyonun arasına alır (−%11 / +%13, ikisi de %15 içinde); akış yönü kök, dik kökten rijit olduğundan
beklenen konum budur. Kapak gerilmesi y = .154 m: FE −224 MPa, kiriş (kabuk EI) −206 MPa (%9), kiriş (1D EI) −399 MPa.
Yani structures kapak gerilmesi/sehimi muhafazakâr, burulma frekansı ise iyimser.

## 7. Varsayımlar

* Malzeme: structures.py MAT + fem/README.md tamamlama değerleri (E2, G, ν, Yt/Yc/S12, F12 = −.5√…); ölçülmemiş.
  Kumaş S12 = 80 MPa izin değeri dayanım olarak kullanıldı. Tsai-Wu KD = .544 yalnız duyarlılık.
* Kaburga aralığı 0.086 m (1 kat/2 mm/1 kat), tank kaburgası 2/3 mm/2; menteşe web'i 2 kat; burun x/c < .01 ve
  x/c > .75 yalnız kütle; kaldıraç kütlesi x/c ≤ .95.
* Kütle 1D m'(y), kesit CG ve kesit ataletine bölme başına eşlendi (atalet %85–94; tam eşleşme için kaldıraç .95c'yi
  geçmeli). Yakıt 0.456 kg/yarı (0.57 L × 0.8), Y_T0–Y_T1 arasında c² ile, kirişler arası kabukta düzgün; 2 servo × 0.12 kg.
* Web'ler OML'den OML'ye (kabuk kalınlığıyla örtüşme), kök tam ankastre (cıvata/çerçeve esnekliği yok), lineer statik.

## 8. Kalan açıklar

1. Kaburga yerleşimi/laminatı ve menteşe web'i imalat tanımıyla doğrulanmalı (f_1T'ye birinci derece etki).
2. Kabuk mod şekilleriyle flutter (fe_modal'a kabuk modlarını aktaran veya doğrudan kabuk-aero modeli); 1350 km/h
   hedefi için f_1T artırımı (ör. kumaş kat sayısı/±45 yüzde, kapalı arka hücre, kaburga sıklığı) değerlendirilmeli.
3. Malzeme üretici/kupon verisi (E1 125 vs 135 GPa, kumaş G12, dayanımlar, sıcak-nem); B-basis allowables.
4. Burkulma (kabuk panel, web kayma), çekirdek kayması/kırışma (zigzag gerektirir), yapıştırıcı ve kök cıvata hattı.
5. Kök bölmesi Tsai-Wu ve çekirdek kayması yakınsamadı; gerçek kök detayıyla yeniden.
6. GVT ile mod etiketleri ve f_1T doğrulanmalı (kriter ≥ 230 Hz; model 272.5 Hz dolu).
7. `validation/study.py` kayıt bütünlüğü cfd/*.py dahil tüm runner kaynaklarının SHA'sını tuttuğundan, paralel CFD
   değişiklikleri bu çalışmaları "STALE" yapabilir; entegrasyondan önce `run_case.py cantilever/coupon --study --threads 1`
   ve `fem/run_wing_study.py` yeniden koşulmalı.

## 9. Rijitleştirme (düzeltilmiş)

İlk rijitleştirme çalışması (21 seçenek orta ağ, 4 seçenek ince ağ; seçilen s41r043w1: f_1T 294,9 Hz, V_F ≈1266 km/h)
bir çapraz incelemede doğrulanmamış bir modelden geldiği için yeniden yapıldı. **Bulgular ve düzeltmeler:**

| # | Bulgu | Doğrulama | Düzeltme |
|---|---|---|---|
| 1 | Sandviç çakışma bayrağı zorunlu değil, inceleme başarısızlığı yok sayılıyor | Doğru: s41r043w1 ince ağ `sandwich_no_overlap=false`, boşluk −0,17 mm (eleman merkezinde; kaba hücre köşesinde −0,62 mm). Neden: uç bölgede burun hücresi (x/c .01–.04) monolitik 2×4 kat = 1,42 mm/yüz, profil derinliği 2,23 mm | `fem/cases.py` `REQUIRED_REVIEW_FLAGS` tüm 6 bayrak; `fem/run_wing_study.py` inceleme/hazırlık/çözüm başarısızsa durur (çıkış kodu ≠ 0); monolitik hücrede kat geçişi: üst+alt kalınlık kaba hücrenin en küçük derinliğini aşamaz (sığmayan kat düşülür, s41r043w1'de uçtaki burun hücrelerinde 8 → 6 kat); boşluk muhafazakâr hücre-köşe derinliğiyle raporlanır (şimdi her ağda +0,095 mm) |
| 2 | İnce ağda kaburga–web bağlantısı uyumsuz | Doğru: 16 kaburgada ince ağda kaburga 4, web 8 eleman yüksekliğinde; 160 ortak olmayan kenar, `wing_review.py` bunları kontrol dışı bırakıyordu | Web ve kaburga aynı dikey bölüntüyü paylaşır (>8 kaburgada ikisi de 4 eleman; ≤ 8 kaburgada 2·factor); uyumsuz kenar artık bağlantı kontrolünü geçirmez (0 kenar). Tam yükseklik (8 eleman, 257 k DOF, bütçe dışı tanılama) ile fark: f_1T 295,10 vs 295,16 Hz (%0,02) |
| 3 | Web/kaburga ek kütlesi iki kez sayılıyor | Doğru (yalnız yeniden koşuda): params 4/1+0.043+web 1'e geçince `ST.wing_section_model` 1D m'(y)'ye ek web/kaburga kütlesini kattı, kabuk `extra` yine ekledi: yarı kanat 1,0366 → 1,0789 kg (+42 g). Kayıtlı ilk sonuçlar eski params ile koşulduğundan bu hatayı içermiyordu | 1D referans açık iter4 tabanında çağrılır (`web_extra=0, rib_pitch=0.086`, `REF_*` sabitleri); seçenek artışları yalnız kabuk `extra`'da. `structures.size_wing/wing_section_model` bu iki değeri argüman olarak alır |
| 4 | Flutter ölçeklemesinin referansı değişken | Doğru: güncel `structures/out/fe_sonuclar.json` (4/1) dolu eğrisi düz → 1813 km/h; iter4 eğrisiyle 1266 km/h | Sabit referans `fem/reference/fe_sonuclar_iter4_v0.5.0.json` = `git v0.5.0:structures/out/fe_sonuclar.json` (blob c39752e3), **SHA256 933f5d7dad5cad1f993170ce3dfd3640cc15bf7f417681e65ad200b59b75f0a3** (LF); eşleşmezse durur, özete `flutter_reference` olarak yazılır |
| 5 | Varyantlar params'tan değer devralıyor | Doğru: güncel params ile s31 = 16 kaburga + web 1 olurdu | Her varyant dört seçeneği açık tanımlar (`_v()`); varyant koşusunda eksik seçenek `Blocked`; test `test_variants_define_every_option_explicitly` |
| 6 | `structures.py main()` 4/1'i analiz etmiyor | Doğru: log "Secilen: 3/1 … 1.83 kg" | Tasarım `WING["skin_plies"]`'tan (`RES["layup_design"]`), aday taraması (4/1 eklendi) ayrı ve "bilgi" olarak (`RES["layup_candidate_1d"]`); log: "Tasarim (params WING): 4/1 …, kanat (1D) 2.07 kg (params kalemi 2.03 kg)" |
| 7 | 21,6 mm kaburga orta ağda temsil edilmiyor | Doğru: orta ağda 32 kaburga 16 satıra yuvarlanıp fiilen 43 mm oluyordu (kaba ağda 43 mm de 86 mm oluyordu) | `rib_rows()`: ny kaburga sayısına bölünmüyorsa `Blocked`. 43 mm orta/ince, 21,6 mm yalnız ince, 65 mm hiçbir ağda temsil edilemez (eski r065 varyantları geçersiz) |
| 8 | CCX çok iş parçacığıyla koşabiliyor | Doğru: `--threads` varsayılanı 4 | `run_case.py`: fem/thermal (CCX) vakalarında threads = 1 sabit; `provenance.solver_threads` (used/requested) |
| 9 | Kanat kapısı kuponu önkoşul saymıyor | Doğru | `CASES["wing"]` önkoşulları `("cantilever", "coupon")` |

Cantilever ve kupon benchmarkları bu kodla yeniden koşuldu (`--study --threads 1`): ikisi de BENCHMARK_ACCEPTED.
Not: önceki 21 seçeneğin kayıtlı sonuçları düzeltme öncesi modeldendir; yalnız aşağıdaki 5 varyant yeniden çözüldü.

**Sonuçlar** (`fem/results/stiffening/summary_fine_corrected.json`, `summary_medium_corrected.json`; dolu/boş tank,
inceleme 6/6, SPOOLES, tek iş parçacığı; yük güncel MTOW 17,44 kg ile). V_F: sabit iter4 eğrisi üzerinde f_1T ölçeği.
Kütle artışı yarı kanat, s31'e göre. CG: kabuk modeli kesit CG, η = 0,70.

| Varyant | f_1T dolu ince (orta) [Hz] | f_1T boş ince (orta) [Hz] | V_F dolu / boş [km/h] | Δm/yarı [kg] | CG | Tsai-Wu R (y>.121) | Uç sehim [mm] |
|---|---|---|---|---|---|---|---|
| s31 (3/1, 8 kaburga, web+0) | 272,56 (273,03) | 280,87 (281,88) | 1185 / 1194 | 0 | 0,451c | 3,60 | 48,5 |
| s31r043 (3/1, 16 kaburga) | 284,77 (285,15) | 295,03 (296,92) | 1227 / 1242 | 0,018 | 0,450c | 3,70 | 48,0 |
| s41r043 (4/1, 16 kaburga, web+0) | 293,74 (293,98) | 300,71 (302,77) | 1261 / 1265 | 0,136 | 0,429c | 4,13 | 43,2 |
| **s41r043w1 (seçilen)** | **295,16** (295,46) | **302,17** (304,17) | **1267 / 1271** | **0,143** | **0,428c** | **4,16** | **43,0** |
| s51r043w1 | 299,95 (300,06) | 305,23 (306,33) | 1285 / 1283 | 0,261 | 0,412c | 5,03 | 38,4 |

* **Ağ yakınsaması:** orta → ince f_1T farkı dolu −%0,10 (s41r043w1), boş −%0,66; s31 −%0,17. 43 mm kaburga kaba ağda
  temsil edilemediği için üç ağlı GCI yoktur (iki ağ farkı raporlanır). Dikey bölüntü duyarlılığı %0,02 (yukarıda).
* **GVT kriteri f_1T ≥ 230 Hz:** seçilen tasarım dolu 295,2 Hz / boş 302,2 Hz ile sağlıyor (%28 pay).
* **316 Hz (1350 km/h) hedefi:** hiçbir varyant sağlamıyor (`choice = null`); en yakını s51r043w1 299,95 Hz.
* **Seçim değişmedi (s41r043w1):** web+0 (s41r043) 6,6 g/yarı daha hafif ama 1,4 Hz (V_F −6 km/h) düşük; web katının
  verimi (0,21 Hz/g) kabuk 3/1→4/1 adımından (0,08 Hz/g) iyi. s51r043w1 +118 g/yarı ile yalnız +4,8 Hz.
  params değişmedi; kanat kalemi 2,03 kg geçerli (kabuk FEM yarı kanat yapısal kütle 1,0379 kg; s31 0,8953 kg;
  toplam artış 2 × 0,143 = 0,285 kg).
* **Düzeltmenin etkisi (seçilen, ince, dolu):** f_1T 294,89 → 295,16 Hz, boş 301,8 → 302,2 Hz, V_F 1266 → 1267 km/h,
  Tsai-Wu 4,23 → 4,16, uç sehim 42,3 → 43,0 mm (ikincisi kısmen MTOW 17,16 → 17,44 kg yük artışından). Yani incelemenin
  bulduğu hatalar sonucu değiştirmedi; ancak artık kapı (6/6 bayrak) ve sabit referansla doğrulanmış durumda.
* 1D `fe_modal` (güncel params) dolu eğrisi hâlâ düz (1813 km/h); flutter tasarım değeri kabuk-FEM ölçekli **≈1267 km/h**.

Yeniden üretim: `python fem/stiffening_study.py --level medium|fine --only s31 s41r043w1 s41r043 s31r043 s51r043w1
--out summary_<level>_corrected` (önce `run_case.py cantilever|coupon --study --threads 1`; paralel CFD kod
değişiklikleri benchmarkları STALE yapar ve kanat kapısı bloklar).

## Dosyalar

* Kod: `fem/clt.py`, `fem/coupon.py`, `fem/wing_shell.py` (yeniden yazıldı), `fem/wing_post.py`, `fem/wing_review.py`,
  `fem/run_wing_study.py`, `fem/wing_compare.py`; `fem/cases.py`, `validation/run_case.py` (coupon vakası, `--wing-fuel`),
  `validation/study.py` (coupon kabul kuralı), `validation/test_validation.py` (5 CLT/ayrıştırıcı testi).
* Sonuç: `validation/results/coupon/`, `validation/results/cantilever/` (yeniden), `fem/results/wing/` (dolu),
  `fem/results/wing_empty/` (boş), `fem/results/wing_compare.json`, `fem/results/wing_compare.png`.
