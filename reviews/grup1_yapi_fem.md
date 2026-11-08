# Grup 1 inceleme — YAPI, FEM, FLUTTER

İnceleme tabanı: `iter5/yuksek-dogruluk` (`8e3c14c`) ve çalışma ağacı. Kapsam: `fem/`, `structures/`,
`docs/04_yapi_flutter.md`, `docs/10` §10.7. `params.py` değiştirilmedi. Commit yapılmadı.

## Özet

1. **1D `fe_modal` 1813 km/h ve düz V_F(f_T) eğrisi bir kod hatasıydı.** Flutter çözümü sabit "ilk 4 mod"u
   alıyordu; 4/1 kat planında dolu tankta 1T beşinci mod (4B 309,1 Hz < 1T 327,3 Hz). Burulma modu çözüme
   girmediği için sonuç yalnız eğilme modlarının yapay flutter'ıydı ve f_T çarpanı hiçbir moda
   uygulanmıyordu (eğri düz). Düzeltildi: 1D dolu **1452**, boş **1544** km/h.
2. **Kabuk mod şekilleriyle p-k kuruldu** (`fem/shell_flutter.py`). Seçilen s41r043w1: dolu **1326**,
   boş **1324** km/h (f_1T-ölçekli 1267/1271). 3/1 tabanda iki yöntem aynı (1174 vs 1185). Ölçekleme
   seçilen tasarım için %4–5 muhafazakâr, çünkü CG'nin 0,451c → 0,428c kaymasını görmüyor.
3. **316 Hz hedefi yanlış ölçüt.** Kabuk p-k ile 1350 km/h için f_1T ≈ 301 Hz (dolu) / 308 Hz (boş) yeter.
   Ayrıca kütle balansı f_1T'yi düşürüp V_F'yi artırıyor. Aileron servosunu kiriş önüne almak (+0 kg)
   V_F'yi ≈1427/1403 km/h'ye çıkarıyor (Ritz tahmini).
4. **Burkulma** (hiç bakılmamıştı): CCX doğrusal burkulma çarpanı 8,9 (nihai), fakat çekirdek kayması
   temsil edilmiyor. Elle yapılan kayma kıvrılması kontrolü kök yakını ön sandviç panelde payı **≈1,2–1,5**
   buluyor (P1).
5. **Tüm uçak flutter'ı (Codex P1 #1) doğru.** Kaba 2-DOF kuyruk taraması eklendi: 1080 km/h için yatay
   kuyruk burulma frekansı ≈310–360 Hz, dikey kuyruk ≈250–320 Hz gerekir. Bu frekanslar hiçbir yerde
   hesaplanmamış.

## Düzeltilenler

| # | Dosya:yer | Sorun | Düzeltme | Doğrulama |
|---|---|---|---|---|
| D1 | `structures/fe_modal.py` `N_MODES_FLUTTER`, `flutter_mode_count()`, `analyse()` | Sabit 4 mod. 4/1'de dolu tankta 1T 5. mod → çözüm dışı → 1813 km/h (yalnız eğilme modları + ok açısı eğim terimi), V_F(f_T) düz. **Asıl sebep budur; "kritik mod değişti" yorumu yanlıştı.** | En az 8 mod ve en az 2 burulma modu (sıralamadan bağımsız). `modes(fe, 16)`. GVT ızgarası `r["n_modes"]` kullanır. Mod yakınsama tablosu 4/6/8/10. | Mod sayısı: 4 → 1813, 5 → 1506, 6 → 1501, 8 → 1452, 10 → 1455, 12 → 1458, 14 → 1459 km/h (dolu). Boş: 1656 / 1604 / 1593 / 1544 / 1544 / 1545 / 1546. Uniform kiriş ve Goland doğrulaması değişmedi (137,3/136,9/137,0 m/s). V_F(f_T) dolu artık 1164 → 1654 km/h (çarpan 0,7 → 1,5). |
| D2 | `structures/fe_modal.py` `pk_fresh()`, `first_crossing()`, `analyse()` | `pk_sweep` kök takibi yakın frekanslı modlarda dal değiştiriyor. Örnek: "adım C" 3839 km/h; iz takibi olmadan 1776 km/h. Kabuk modlarında s41r043w1 dolu M_n tavanında 2554 km/h (gerçek değer ≈1326). | İz takibi olmayan p-k: her V'de mod frekanslarından ve önceki V'nin köklerinden yeniden başlatılır, en büyük g alınır. `analyse` iki sonucu karşılaştırır ve düşük olanı alır; `Vf_fresh_kmh` ve `tracking_ok` alanlarını JSON'a yazar. | Temel dolu/boş iki yöntemde aynı (1452/1544). Adım C 3839 → 1776. |
| D3 | `structures/out/fe_sonuclar.json` + `fe_*.png` | Hatalı 1D sonuç | D1+D2 ile `fe_modal.py` yeniden koşuldu | Yukarıdaki sayılar. `logs/structures_fe_modal.log` güncellenmedi (`run_all.sh` yazar). |
| D4 | `docs/04_yapi_flutter.md` §15.3, §15.4, §15.5 | Doküman 1813'ü "kritik mod değişti" diye açıklıyordu. Kabuk p-k "açık iş" görünüyordu. 316 Hz ölçütü. Burkulma notu yoktu. | Hata açıklaması, düzeltilmiş 1D sayıları, kabuk p-k tablosu, kuyruk taraması ve burkulma notu eklendi. **Tasarım değeri ≈1267 km/h olarak bırakıldı** (karar koordinatörün). | — |
| D5 | `docs/10` §10.7.3 "1D modelin sınırı", §10.7.4 madde 2 ve 4 | Aynı | Aynı | — |

Yeni dosyalar (inceleme aracı ve çıktısı):
- `fem/shell_flutter.py` → `fem/results/shell_flutter.json`. Kabuk modlarıyla p-k, varyant tablosu,
  `--selftest`, `--options` (kütle seçenekleri için Ritz + 1T ölçeği).
- `structures/kuyruk_flutter.py` → `structures/out/kuyruk_flutter.json`. Kaba 2-DOF kuyruk taraması.

Testler: `python -m unittest validation.test_validation validation.test_cfd_mesh` → **33 test, OK**.

## Kabuk p-k yöntemi ve sonuçları

**Dönüşüm.** CCX `*FREQUENCY` özvektörleri M-normalizedir. Katılım çarpanlarıyla kontrol edildi: ilk 10 modun
z yönündeki etkin kütle toplamı 1,31 kg; yarı kanat kütlesi ≈1,47 kg. Modun kutu düğümlerine uydurulmuş
w_EA(y) ve θ = ∂z/∂x değerleri `fine.json` dosyasında saklıdır. Bunlar EA'ya dik kesit serbestliklerine
dönüştürüldü: w, w' = cosΛ·dw/dy, φ = α_s/cosΛ + tanΛ·w' (α_s = −θ). Aerodinamik, fe_modal'ın
şerit-Theodorsen modeli (Prandtl-Glauert, Mach eşleştirme, M_n ≤ 0,9). Düzlem içi mod dışarıda bırakıldı.

**Self-test.** Aynı dönüşüm 1D modlara uygulandı ve fe_modal V_F'si yeniden üretildi: dolu −%0,004,
boş −%0,012.

Sonuçlar (Mach eşleştirmeli, g = 0, 6 düzlem dışı mod; iz takipli ve iz takipsiz çözümün düşüğü):

| Varyant | f_1T-ölçekli (eski) dolu / boş | **Kabuk p-k dolu / boş** | sabit M 0,88 dolu / boş |
|---|---|---|---|
| s31 | 1185 / 1194 | 1174 / 1169 | 1301 / 1292 |
| s31r043 | 1227 / 1242 | 1192 / 1183 | — |
| s41r043 | 1261 / 1265 | 1326 / 1311 | 1493 / 1494 |
| **s41r043w1** | **1267 / 1271** | **1326 / 1324** | **1507 / 1509** |
| s51r043w1 | 1285 / 1283 | 1458 / 1460 | 1658 / 1665 |

(Kesin değerler `fem/results/shell_flutter.json` içinde. 4 → 8 mod farkı seçilen tasarımda ≤ %1,5.)

**f_1T ölçeklemesi savunulabilir mi?** Kısmen.
- 3/1 tabanda kabuk p-k ile aynı sonucu veriyor (%1). Frekans dışındaki her şey iter4 ile aynı kaldığı sürece
  birinci mertebe bir tahmin olarak geçerli.
- Varyantlar kesit CG'sini ve kütleyi değiştirince yöntem bu etkiyi göremiyor. 4/1 kabuk CG'yi öne aldığı
  için ölçekleme muhafazakâr kalıyor (−%4–5). Ters yönde bir değişiklik (ağır arka kabuk, servo geriye)
  iyimser sonuç verirdi.
- Kabuk modlarında 1T ile 3B güçlü bağlaşımlı ve frekansları yakın (295/308 Hz). Ölçekleme bunu da temsil
  etmiyor.

**Kabuk p-k'nın sınırları.**
- Şerit teorisi kullanılıyor; uç kaybı yok, kontrol yüzeyi serbestliği yok.
- Mod şekli kutu düğümlerinin doğrusal uydurmasından geliyor. 1D kesit kütlesiyle hesaplanan
  genelleştirilmiş kütle eğilme modlarında 0,83–0,90, burulma modlarında 0,68–0,79 çıkıyor. Yani burulma
  modlarının kinetik enerjisinin %20–30'u kesit distorsiyonunda ve arka bölgede; bu kısım aerodinamiğe
  girmiyor.
- Kritik nokta V_cap = 1194 km/h'nin üstünde, M_n tavanında. Burada PG çarpanı 2,3; bu tanım iter4 ile
  aynı ama fiziksel değil.

## 316 Hz hedefine (asıl hedef 1350 km/h) başka yollar — yalnız hesap, params değişmedi

Yöntem: kabuk modları (9 düzlem dışı mod) taban alınarak Rayleigh-Ritz kütle değişikliği hesaplandı;
noktasal kütlenin dönme ataleti dahil edilmedi. Yöntem 1D modelde kesin çözümle karşılaştırıldı.
V_F farkı: servo öne −%1,3, 60 g servo −%0,5, uç kütlesi +%1,6.

| Seçenek (yarı kanat) | Δm | f_1T dolu / boş [Hz] | **V_F dolu / boş [km/h]** |
|---|---|---|---|
| Temel s41r043w1 | 0 | 295,2 / 302,2 | 1325 / 1324 |
| A: aileron servosu x/c .60 → .15 (y .34, ön kiriş önü; profil kalınlığı ≈15 mm, ince servo gerekir) | 0 | ≈274 / 282 | **1427 / 1403** |
| B: aileron servosu 60 g | −0,06 | 296 / 304 | 1351 / 1355 |
| C: aileron servosu köke (y .10) + tork çubuğu (çubuk kütlesi yok) | 0 | 296 / 305 | 1391 / 1375 |
| D: flap servosu x/c .65 → .15 | 0 | 294 / 302 | 1326 / 1325 (etkisiz) |
| E1: uç hücum kenarına 30 g balans (y .70, x/c .05) | +0,03 | ≈277 / 289 | 1446 / 1424 |
| A + E1 | +0,03 | — | 1541 / 1470 |
| Yalnız burulma modları ×1,02 / ×1,04 | — | 301 / 308 | 1363 / 1350; ×1,04: 1402 / 1376 |

Notlar:
- E2 (60 g uç kütlesi) 1527/1467 km/h veriyor; f_1T 267/279 Hz. 1T ölçeğinde ×1,10 dolu noktası da (1443 < 1491) mod değişimi gösteriyor. Ritz tabanı için büyük bir
  değişiklik, güvenilmez.
- A+E1'deki "f_1T 448" etiketi otomatik burulma tespitinin hatası; yok sayılmalı.
- 1D (düzeltilmiş) servo duyarlılığı aynı yönde: 60 g servo dolu 1520 / boş 1486; köke alma 1659 / 1396.
  1D modelde boş tank tersine dönüyor; bu, Ritz/1D ayrışmasının da ölçüsü.
- **Kiriş konumu:** her değişiklik kabuk ağını değiştirir (`spar_xc` params'ta). Bu inceleme kapsamında
  yeniden çözülmedi.
- **Öneri:** ölçütü "f_1T ≥ 316 Hz" yerine "kabuk p-k V_F ≥ 1350 km/h" yapın. A (servoyu öne almak, kütle
  maliyeti yok) en iyi aday; FEM ile servo konumu değiştirilerek doğrulanmalı. GVT alt sınırı (230 Hz)
  ayrıca kabuk p-k ile yeniden türetilmeli.

## Diğer bulgular (kod incelemesi)

**wing_shell.py — doğru bulunanlar:**
- Malzeme sabitleri: kumaş ±45 G = E/(2+2ν) ≈ 26,2 GPa ≈ structures G45 = 25 GPa; Ex(±45) = 15,6 GPa.
- Tsai-Wu formülü ve F12 = −0,5·√(F11·F22).
- OFFSET = 0,5 ve normal yönleri (malzeme içe).
- Schrenk yükünün integrali (iki yüz × 0,5 q).
- Kaldıraç `*EQUATION` kinematiği (w = w_h + λ(w_h − w_r)).

**wing_shell.py — küçük konular:**
- (P3) Kaburga ek kütlesi `e = m_t − m_base·min(1, 8/n)` tank kaburgasının yarısını "ek" sayıyor.
  Fark ≈0,5·(tank − hafif kaburga) ≈ birkaç gram.
- (P3) `need2` 1D kesit ataletini r² = c²/12 ile alıyor (structures `section_inertia` ile tutarlı); atalet
  oranı 0,85–0,94.

**structures.py:**
- GJ: Bredt tek hücre, kabuk 2·n_face kat, arka web (n_web + web_extra), G45. Ek web katı GJ'ye yalnız arka
  web üzerinden giriyor; kütleye iki web ×1,3 olarak giriyor. **Tutarlı.**
- (P3) Kaburga kütlesi `m_ribs = 0,08·c/cr·(0,086/pitch)` kök kaburgası başına ≈6,9 g veriyor; kabuk
  modelindeki hafif kaburga ≈3,4 g. 1D muhafazakâr.
- (P3) EI'deki kabuk terimi `12e9·2·w·t_skin/2` iki yüzeyin yalnız birini sayıyor; bu bilinçli bir
  muhafazakârlık gibi görünüyor ama yorumu yok.

**Tsai-Wu ve kök tekilliği:**
- İlk kaburga bölmesinin dışlanması makul.
- (P2) Kök bölmesi değeri ağla birlikte düşüyor (2,89 → 1,88). Gerçek kök detayı (cıvata/çerçeve
  esnekliği, alt model) olmadan kökte dayanım kanıtı yok.
- Kumaş S12 = 80 MPa bir izin değeri, dayanım değil; muhafazakâr.

**Çekirdek kayması:** 27 kPa ve yakınsamıyor. Kabuk genişlemesi zigzag'ı temsil etmiyor. Elle yüz kırışması
kontrolü σ_wr ≈ 0,5·(Ef·Ec·Gc)^(1/3) ≈ 137 MPa; yüz gerilmesi ≈32 MPa (R ≈ 4,3). Sorun yok.

**Burkulma (yeni):**
- CCX `*BUCKLE` (s41r043w1 orta ağ, nihai 18 g): çarpanlar 8,9 / 14,5 / 15,1. İlk mod uçta menteşe web'i
  ve arka panelde.
- Genişletilmiş kabuk tek elemanlı kalınlıkta çekirdek kayma esnekliğini temsil etmediği için bu değer
  iyimser.
- Elle kontrol, ön sandviç panel (4 kat ±45 / 2 mm Rohacell 51, 43 mm × ≈100 mm, ε ≈ 2,06·10⁻³ nihai):
  - Euler N ≈ 307 kN/m.
  - Kayma kıvrılması sınırı G_c·h²/t_c ≈ 70 kN/m.
  - Birleşik N_cr ≈ 57 kN/m; uygulanan ≈46 kN/m.
  - **R ≈ 1,2–1,5, KD'siz.** P1.
- Deck: scratchpad'de (`buck.inp`, ilk 30931 satır + `*BUCKLE`).

## Öneriler

| Önem | Öneri | Gerekçe | Tahmini iş |
|---|---|---|---|
| P1 | Sandviç panel burkulması / kayma kıvrılması: katmanlı katı (C3D20R, çekirdek ayrı eleman) alt modeli ya da sandviç teorisiyle tüm paneller; gerekirse 3 mm çekirdek (crimping ∝ h²/t_c, ≈+%25) | Elle kontrolde R ≈ 1,2–1,5. Kabuk FEM bu modu göremiyor. | 1–2 gün |
| P1 | Tüm uçak aeroelastik modeli: kuyruk FE (yatay/dikey burulma frekansı), gövde eğilme/burulma, elevator/rudder dönme ve servo/bağlantı esnekliği; serbest-serbest GVT | Codex P1 #1 doğru. 2-DOF tarama 1080 km/h için kuyruk f_T ≈250–360 Hz gerektiriyor; hiç hesaplanmadı. Kanat 2-DOF'u FE'ye göre %20 iyimserdi, kuyruk gereksinimi daha yüksek olabilir. | 1 hafta |
| P1 | Flutter ölçütü: "f_1T ≥ 316 Hz" yerine kabuk p-k V_F ≥ 1350 km/h; tasarım değerinin 1267'den 1324'e (dolu/boş min.) taşınması koordinatör kararı | Ölçekleme CG/kütle etkisini görmüyor; kütle balansı f_1T'yi düşürürken V_F'yi artırıyor | Karar + doküman |
| P2 | Seçenek A (aileron servosu ön kiriş önüne) FEM ile çözülsün (`wing_shell.py` servo konumu şu an sabit; env/params seçeneği gerekir) | Ritz ile +100 km/h, kütle maliyeti yok | 0,5 gün |
| P2 | Kabuk p-k'yı güçlendirme: kesit distorsiyonunu da içeren şekil (veter yönünde 2. derece uydurma), kontrol yüzeyi DOF, DLM/panel aerodinamiği; GVT alt sınırını (230 Hz) kabuk p-k ile yeniden türetme | Genelleştirilmiş kütle 0,68–0,79 (burulma); strip teori | 2–3 gün |
| P2 | `fe_modal` GVT ızgarası hâlâ iz takipli `flutter_solve` kullanıyor; ızgarada da iz-takipsiz kontrol | D2 hatası ızgara noktalarında da olabilir | 0,5 gün (koşu 15+ dk) |
| P2 | Kök bölgesi: cıvata/çerçeve esnekliğiyle alt model; Tsai-Wu ve çekirdek kayması yakınsaması | Kök bölmesinde R düşüyor, yakınsamıyor | 1–2 gün |
| P3 | 1D kaburga kütlesi ve EI kabuk terimi yorumları; tank kaburgası ek kütle sayımı | Küçük tutarsızlıklar | 1 saat |

## Yol haritasına eklenmesi gerekenler

1. Sandviç panel burkulması ve kayma kıvrılması analizi; kupon testi (kenar basma) ile.
2. Kuyruk ve gövde FE modal + bağlaşık flutter; elevator/rudder/aileron dönme rijitliği ölçümü (servo +
   bağlantı); serbest-serbest GVT ile mod şekli (MAC) eşleştirmesi.
3. Flutter kabul ölçütünün kabuk p-k V_F'ye taşınması ve GVT frekans sınırlarının bu modelle yeniden
   türetilmesi.
4. Servo yerleşimi ve kütle balansı tasarım çalışması (FEM ile).
5. FEM kayıtları `STALE`: `params.py` ve `validation/` çalışma zamanı dosyaları başka ajanlarca
   değiştirildi. Entegrasyondan önce `run_case.py cantilever|coupon --study --threads 1`,
   `fem/run_wing_study.py` ve `fem/stiffening_study.py` yeniden koşulmalı. Ardından `fem/shell_flutter.py`
   da yeniden koşulmalı (kabuk modlarını `fine.json`'dan okur).

## Doğrulayamadıklarım

- Kabuk p-k sonucunun bağımsız bir referansla doğrulanması: yalnız 1D gidiş-dönüş testi ve 3/1'de
  ölçeklemeyle tutarlılık var. Sonuç kutu uydurmasına ve şerit teorisine bağlı.
- Ritz seçenekleri FEM ile yeniden çözülmedi (yalnız 1D kesin çözümle sınandı). Kiriş konumu değişikliği
  hiç hesaplanmadı.
- Kuyruk tahmini: kütle, EA ve CG konumları, burulma ve eğilme frekansları varsayım. Sonuç bir gereksinim
  taramasıdır, flutter hızı değildir.
- Malzeme sabitleri (UD E1 125 GPa, kumaş G12, dayanımlar) ölçülmemiş; FEM sonuçlarının hepsi buna bağlı.
- FEM kanat/rijitleştirme çalışmaları yeniden koşulmadı (kayıtlar zaten STALE; paralel ajanlar `validation/`
  ve `cfd/` dosyalarını değiştirmeye devam ediyor).
- Elle burkulma kontrolü kaba (panel boyutu, kenar koşulları, yük paylaşımı). FE alt modeliyle
  doğrulanmalı.
