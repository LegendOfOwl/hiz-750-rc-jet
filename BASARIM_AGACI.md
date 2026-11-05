# HIZ-750 Başarım Ağacı (devir notu)

> Farklı bir sohbete veya başka bir yapay zekâya devir için yazıldı. Projenin nereye geldiğini, her sonucun nasıl elde edildiğini, nelerin yanlış çıktığını ve sırada ne olduğunu anlatır.
> **Son güncelleme:** 2026-11-06 · dal `iter5/yuksek-dogruluk` · son kayıtlı commit `e1170e7`
> **Güncelleme kuralı:** Her kilometre taşında (bir analiz kabul edildiğinde, yama alındığında, PR açıldığında, sürüm çıktığında) ve en az her çalışma oturumunun sonunda güncellenir. En yeni bilgi "Şu an" bölümündedir.

İşaretler: ✅ bitti ve doğrulandı · 🟡 bitti ama koşullu ya da yalnızca masa başı · 🔄 sürüyor · ⏳ bekliyor · ❌ yanlış çıktı veya terk edildi

---

## 0. Önce bunu oku

**Hedef:** 750 km/h ölçüm hızında uçan türbinli bir RC jet İHA. CAD, analizler ve dokümantasyon birlikte yürüyor. Kullanıcı Türkçe yazıyor ve iş tamamlanana kadar döngüde kalınmasını istiyor.

**Repo:** `C:/Users/Urungu/Desktop/Yeni klasör`. GitHub'da `LegendOfOwl/hiz-750-rc-jet`, herkese açık.

**Dallar ve sürümler:**
- `main` = v0.5.0, yayımlandı.
- Çalışma dalı `iter5/yuksek-dogruluk` (v0.6.0 kapanışı, CHANGELOG tarihi 2026-11-06).
- Etiketler: v0.4.0, v0.5.0.

**Ana kurallar:**
- Tek veri kaynağı `params.py`. Analizler ve CAD değerlerini buradan okur; sayılar başka bir yere sabit yazılmaz.
- Bütün zincir `run_all.sh` ile yeniden üretilir. Bu dosya LF satır sonu ister (`.gitattributes`).
- `main`'e birleştirmek için kullanıcıdan **açıkça** onay alınır.
- Güncel çalışma aracı `codex-cli`. Kapanış düzeltmeleri repo kökünde yürütülür.

**Python ortamı:** `C:/Users/Urungu/.hz750/Scripts/python.exe`. Kısa yolun sebebi: OCP/CadQuery uzun Windows yollarında DLL hatası veriyor.

**Kurulu araçlar** (`C:/hz750tools`, SHA256 değerleri `installation.json` içinde):

| Araç | Yol / not |
|---|---|
| SU2 8.2.0 | `SU2/win64/bin/SU2_CFD.exe` |
| CalculiX 2.20 | `CalculiX/calculix_2.20_4win/ccx_static.exe` |
| gmsh 4.15.2 | Python ortamında |
| CadQuery 2.8, AeroSandbox 4.2.10 (NeuralFoil), ezdxf | Python ortamında |
| Ham çözücü çıktıları | `C:/hz750run`, repoya girmez |

---

## 1. Başarım ağacı

```
HIZ-750
├─ ✅ v0.1 Kavramsal boyutlandırma (sizing.py)
│   └─ ✅ Motor: P300 sınırda (754 km/h) → P400-PRO seçildi
├─ ✅ v0.2 İter1: ilk tam paket (CAD + aero + yapı + performans + doküman 02–07)
├─ ✅ v0.3 İter2: statik marj, çakışmalar, takım → dolly + kızak
├─ ✅ v0.4.0 İter3: alçak kanat, yarı gömülü alık, tek parça kanat, 3/1 kabuk
├─ ✅ v0.5.0 İter4: masa başı doğrulamalar (PR #1 birleşti, release yayımlandı)
│   ├─ ✅ CAD'den kütle/CG/atalet
│   ├─ ✅ FE modal p-k flutter (Goland ile doğrulandı) → 1307 km/h
│   ├─ ✅ Uçuş kontrol: g-limiter 10,05 g, yaw damper ζ 0,31–0,44
│   ├─ 🟡 Alık η_r 0,971 (yarı ampirik, test ister)
│   └─ ✅ PR #1 incelemesinde 9 bulgu → hepsi düzeltildi
└─ 🔄 v0.6.0 İter5: yüksek doğruluk (SU2 / CalculiX / gmsh)
    ├─ ✅ Araç kurulumu (host, SHA256 kayıtlı)
    ├─ ✅ FEM konsol benchmark (S8R, 3 ağ) kabul
    ├─ ⚠️ Termal 1B benchmark (3 ağ) tarihsel kabul; params değişikliği nedeniyle STALE, yeniden koşulmalı
    ├─ 🟡 Motor bölmesi termal → 2 mm ısı keçesi ZORUNLU (h/k/ε ölçülmedi)
    ├─ ✅ FEM CLT kupon benchmark (5 laminat, 3 ağ, hata ≤ %1,12 < %2)
    ├─ 🟡 FEM kompozit kanat kabuk (7168 S8R, dolu/boş tank; REVIEW_REQUIRED — malzeme sabitleri varsayım)
    │   ├─ f_1B 39,5 Hz, f_1T 272,5 Hz (1D fe_modal 305,7 Hz → kabuk %11 düşük; GVT ≥ 230 Hz yine OK)
    │   ├─ 18 g uç sehim 47,7 mm; min Tsai-Wu R 3,66 (KD 0,544 ile 1,99), arka kiriş kapağı
    │   ├─ ⚠️ Flutter (f_1T ölçekleme) 1307 → ≈1185 km/h: 1080 OK, 1,25 model payı (1350) YOK → f_1T ≥ 316 Hz gerek
    │   ├─ ⚠️ Kaburgalar f_1T'yi belirliyor (kaburgasız 198–207 Hz < 230)
    │   └─ 🟡 Rijitleştirme: ilk tarama 21 orta / 4 ince seçenek; inceleme sonrası 5 varyant yeniden çözüldü. Seçilen s41r043w1 (4/1 kat + 43 mm kaburga + web +1 kat), f_1T 295,2 Hz dolu / 302,2 Hz boş, Vf ≈1267 / 1271 km/h, 1080 km/h gereksinime %17 pay, toplam +0,285 kg, kesit CG 0,428c, Tsai-Wu R 4,16, uç sehim 43,0 mm. 316 Hz hedefine ulaşılamadı. Önceki params/zincir yenilemesiyle MTOW 17,44 kg, statik marj %13,0–32,8.
    │       └─ ⚠️ 1D fe_modal yeni kat planıyla Vf 1813 km/h veriyor ve Vf(f_T) eğrisi düz (kritik mod değişti) → 1D sonuç GÜVENİLMEZ/iyimser. Tasarım değeri kabuk-FEM ölçekli **≈1267 km/h** (sabit iter4 referansı). Kabuk mod şekilleriyle p-k çözümü açık iş
    ├─ 🔄 CFD doğrulama
    │   ├─ ✅ Düz levha SA, üç ağ BENCHMARK_ACCEPTED; ince Cf 0,0028613, Schlichting −%4,74, p 0,434, ince GCI %0,88
    │   ├─ ✅ Düz levha MG3 ıraksaması sonrası MG0 + CFL_ADAPT ve proje kapısıyla uyumlu durma kuralıyla üç ağ kapıyı geçti
    │   ├─ 🟡 Resmi SU2 RAE ağı+cfg çözücü kontrolü kabul; CL −%2,6, CD +%5,9; Cp RMSE 0,0984 > 0,08, deney Cp kabulü açık
    │   ├─ ⚠️ RAE2822 PENDING (iz bölgesi); yeni tek bloklu C-ağı 100c, min köşe sinüsü 0,707; MG3 ıraksadı, MG0 ıraksamıyor ama kaba kapı geçmedi
    │   │   └─ Ara CL 0,730 (−%1,8), CD 0,01345 (+%5,9), Cp RMSE 0,092; residual x≈1,2–2c iz kesitinde, orta/ince ve GCI bekliyor
    │   ├─ ⏳ SST ve profil α/Mach taraması
    │   └─ ⏳ 3B sınır tabaka ağları
    ├─ ✅ İnceleme kapanış düzeltmeleri kodlandı, GCI plato reddi / 3B CMy / v0.5.0 baseline; Python regresyonları erişim nedeniyle çalıştırılamadı
    ├─ ✅ docs/10, README, CHANGELOG [0.6.0] ve başarım ağacı güncellendi (2026-11-06)
    ├─ ⏳ PR → kullanıcı onayı → birleştirme
    └─ ⏳ v0.6.0 etiketi ve release
```

---

## 2. Neler, nasıl başarıldı

| Başarım | Nasıl | Dosya / kanıt |
|---|---|---|
| Vmax, itki payı | Raymer bileşen sürüklemesi, Korn dalga sürüklemesi, türbin itki modeli. 750 km/h'te itki payı %40–90; kötümser modelle Vmax ~878 km/h | `sizing.py`, `docs/08` |
| Stabilite, trim | AeroSandbox ile nötr nokta ve modlar; DATCOM ile gövde-kanat Cl_β | `aero/aero_analysis.py`, `docs/02` |
| CAD | CadQuery'de parametrik model: 27 parça STEP/STL, montaj, DXF/PDF çizimler | `cad/build_cad.py`, `docs/03` |
| Kütle, CG, atalet | CAD katılarından hesaplandı. MTOW 17,16 kg, yakıt CG'si 0,940 m, statik marj %12,5–32,8 | `cad/mass_properties.py` |
| Flutter | Önce 2-DOF Theodorsen, sonra 1D FE kiriş ile modal p-k (Goland kanadıyla doğrulandı). 1307 km/h, gereken 1080 km/h, pay %21. GVT kabul ölçütü: f_1T ≥ 230 Hz | `structures/fe_modal.py`, `docs/04` |
| Yükler | Schrenk dağılımı, Bredt-Batho burulma | `structures/structures.py` |
| Kontrol yasası | n_z komutlu pitch + g-limiter, yaw damper, p komutlu roll. GM ≥ 9,4 dB, PM ≥ 50° | `aero/flight_control.py`, `docs/09` |
| Alık | Sınır tabaka yutma + iç kayıplar ile η_r 0,971 | `performance/inlet_analysis.py` |
| Görev, yakıt, elektrik | Görev profili, yakıt ve elektrik bütçeleri | `performance/mission.py`, `docs/05` |
| Üretim, test, maliyet, risk | Test planı ve FMEA | `docs/06`, `docs/07` |
| Yüksek doğruluk paketi | Sabit sürümlü araçlar, 3 ağlık çalışmalar, Richardson/GCI, karşılaştırma raporları | `validation/`, `cfd/`, `fem/`, `thermal/`, `docs/10` |
| Isı keçesi kararı | CalculiX motor-keçe-kabuk modeli, 5,97 mm aralık, yer koşusu. Keçesiz kabuk 149,8 °C ≈ Tg 150 °C; 2 mm keçeyle 126,1 °C | `thermal/`, `params.py`, `docs/06` (termokupl: iç kabuk < 120 °C), `docs/07` (FMEA 9) |

---

## 3. Yanlış çıkanlar ve dersler

| Ne yanlıştı | Nasıl fark edildi | Düzeltme / ders |
|---|---|---|
| Statik marj %40 (İter1) | Stabilite analizi | Kanat öne alındı, arka kiriş 0,55c'ye çekildi |
| 5 CAD çakışması, ana teker kanada sığmıyor | CAD montajı | Takım yerine dolly + kızak; yatay kuyruk ikiye bölündü |
| İter2 flutter değerleri (1383/1356 km/h) iyimser | Kesit ağırlık merkezi kalem kalem hesaplandı: 0,52c (varsayım 0,42c) | Gerçek değer ~1086 km/h. Kabuk 3/1 yapıldı. **Ders:** varsayılan ağırlık merkezi kullanılmaz |
| 2-DOF flutter %11 iyimser | FE modal p-k | 1307 km/h kabul edildi |
| Gövde kabuğu CG'si yanlış (1,05 m) | CAD alan merkezi | 1,15 m'ye taşındı, +0,15 kg burun balastı |
| Fuselage spline örnekleme hatası | CAD burun geometrisi | Düzeltildi |
| PR #1'de 9 bulgu: kullanılmayan tank hacmi, eşit olmayan yakıtla kıyas, eski yakıt CG'si, kullanılmayan `bury`, sabit yazılmış A_FACE, döngüsel k_ram, global yan etki, paylaşılan katılar, sabit yollar | Kod incelemesi | Hepsi düzeltildi. **Ders:** her yeni analiz `params.py` ve CAD raporundan okumalı |
| Uzun yol yüzünden CadQuery DLL hatası | Kurulum | Ortam `~/.hz750`'ye taşındı |
| `install_tools.ps1` pip'in stderr çıktısını hata saydı | Kurulum | gmsh aslında kurulmuştu. SU2'nin iç içe zip'i elle açıldı |
| Codex RAE2822 için Case 9 koşullarını kullanıyordu | Onay incelemesi | Reddedildi, Case 6'ya geçildi |
| "Bütün RMS < −6" yakınsama kapısı aşırı katıydı | Koşular | Yeni kapı: CD Cauchy 1e-6/100 iterasyon + ρ ve ν̃'de ≥ 4 mertebe düşüş; enerji residual'ı yalnızca bilgi amaçlı |
| **SU2'de LINEAR_SOLVER_PREC varsayılanı LU_SGS sanıldı; gerçek değer ILU** (CConfig.cpp sat. 1699; eski doc comment yanıltıcı). Pilot koşuda LINEAR_SOLVER_ERROR 0,01 kullanıldı (resmi varsayılan 1e-6) | Codex'in SU2 v8.2.0 kaynak incelemesi | Iraksamaların muhtemel sebebi. Resmi cfg ile satır satır karşılaştırılıyor |
| Resmi ağ dosyasının nokta satırları x/y/z/ID biçiminde; denetim betiği yanlış okuyordu | Ağ denetimi | Son sütun ID olarak okunuyor, test eklendi |
| "ILU/1e-6 ıraksamayı açıklar" hipotezi | Resmi ayarlarla pilot: ikisi de aynı biçimde (önce ~4 mertebe düşüş, sonra ani patlama) ıraksadı | Hipotez çürütüldü. Ortak faktör MGLEVEL 3 ve sabit CFL; sırada MG0 + CFL_ADAPT testi |
| 1D fe_modal burulma frekansı iyimser (%11) | Kabuk FEM | Flutter payı %21'den ~%10'a indi; kabuk mod şekilleriyle aeroelastik çözüm gerek |
| CalculiX 2.20: çok iş parçacığı sahte gerilme, PaStiX gürültü/askı, kompozit kabukta MASS elemanı çalışmıyor, kökte 1-6 kısıtı yük kaybettiriyor | FEM alt ajanı kupon/konsol koşuları | `--threads 1`, SPOOLES, NSM tabakası + `*EQUATION` kütleleri, 1-3 ankastre |
| Taslak kanatta web'ler 0° (G 4,5 GPa) | FEM incelemesi | ±45 kumaşa çevrildi |
| Codex 5HV4 worktree'si commit edilmeden claudex tarafından silindi (2026-11-05 23:00), patch dosyası da yok | Entegrasyon denemesi | Kod, Codex oturum kaydındaki FileChange kayıtlarından (`~/.codex/sessions/2026/11/04/rollout-...21-40-43...jsonl`) kurtarılıyor. **Ders:** dış ajan işi bitince hemen ana repoya commit'le; worktree'ye güvenme. Codex CLI sandbox'ı workspace dışını okuyamıyor, dosyaları önce workspace'e kopyala |
| Kurtarma sonucu | Opus ajanı | 47 kod değişikliğinin hepsi kurtarıldı ve birleştirildi, 21 test geçti. Çözücü sonuç JSON'ları ve NASA referans dosyaları kayıp (ham çıktılar `C:/hz750run`'da). RAE native değerleri yalnız `cfd/RESULTS_iter5.md` ve bu ağaçta kayıtlı; `fetch_reference --experiment` (indirme) + `postprocess_native` ile yeniden üretilebilir. `check_artifacts.cjs` baseline hash'leri 320f1ef zincir yenilemesinden beri eski |
| Rijitleştirme sonucu (294,9 Hz, 1266 km/h) doğrulanmamış modelden geldi | Codex Sol çapraz incelemesi (12 bulgu) | P1'ler: seçilen ince ağda sandviç çakışması (−0,17 mm) ve 160 uyumsuz kaburga–web kenarı inceleme kapısından kaçtı; ek web/kaburga kütlesi iki kez sayılıyor; flutter ölçeklemesi değişken bir dosyaya bağlı. P2: structures main() 4/1'i analiz etmiyor, CCX varsayılan 4 iş parçacığı, kupon önkoşul değil, GCI tek sıfır farkı yakınsama sayıyor, 3B CFD'de CMz (sapma) okunuyor, check_artifacts hash'leri eski. FEM tarafı: 9 bulgunun 9u doğru çıktı, düzeltildi ve yeniden çözüldü (c09dead); seçim değişmedi, sayılar ±%0,1; validation/CFD maddeleri CFD ajanı bitince. **Ders:** inceleme kapısı başarısızsa çözüm durdurulmalı; FEM sonucu kabulden önce mutlaka ayrı ajana kontrol ettirilmeli |
| Gecikmiş onay cevabı "rejected by user" sayıldı | Codex köprüsü | 10 dk zaman aşımı. Gerekirse Codex'ten isteği yeniden yollaması istenir |

---

## 4. Açık riskler ve varsayımlar

- **Rüzgâr hamlesi:** 15 m/s'lik kısa hamle 19–27 g üretiyor ve FC bunu azaltamıyor. Uçuşlar yalnızca sakin havada yapılır.
- **Zorunlu testler:** GVT (f_1T ≥ 230 Hz), türbin itki modeli, alık basınç kazanımı, yer koşusunda termokupl ölçümü.
- **Kontrol yasası** 350 km/h altı için yok.
- **Termal model:** h, k ve ε ölçülmedi; sonuçlar koşullu.
- **Varsayımlar:** 300 m irtifa, ISA, rüzgârsız hava; ölçüm hızı 750 km/h, operasyonel limit 800 km/h. Tam liste `docs/08` "Varsayımlar" tablosunda.

---

## 5. Güncel çalışma aracı

Çalışma repo kökünde codex-cli ile yürütülüyor. Claudex köprüsü ve 5HV4 worktree'si önceki oturumların tarihsel kayıtlarıdır. Kurtarılan CFD değişiklikleri ana çalışma dalına alındı, son CFD paketi e1170e7 kaydında.

---

## 6. Şu an ve sıradakiler

**Şu an (2026-11-06)**

- Düzeltilmiş s41r043w1 seçimi geçerli. f_1T 295,2 / 302,2 Hz, ölçekli flutter ≈1267 / 1271 km/h, toplam ek kütle +0,285 kg, Tsai-Wu R 4,16, uç sehim 43,0 mm. 316 Hz hedefi sağlanmadı, kabuk mod şekilleriyle p-k açık.
- Düz levha SA üç ağda BENCHMARK_ACCEPTED, ince GCI %0,88 ve p 0,434. RAE2822 PENDING, residual iz bölgesinde. MG0 ıraksamayı önledi, iteratif kapı ve deney Cp kabulü bekliyor.
- GCI tek-fark platosu kabulden çıkarıldı, 3B CFD yunuslama momenti CMy'ye bağlandı. Tarihsel baseline v0.5.0 Git byte'larına sabitlendi, güncel analiz dosyaları ayrı listelendi.
- README, CHANGELOG [0.6.0] ve docs/10 güncellendi. Sürüm kaydı 2026-11-06 tarihli. Commit, etiket ve push bu kapanışta yapılmadı.
- Python erişim engeli nedeniyle yeni regresyonlar ve solver yeniden koşumları bu oturumda çalıştırılamadı. Hash karşılaştırmasında düz levha, konsol ve kupon kayıtlarının kaynakları farklı, yeniden değerlendirmede STALE sonucu bekleniyor. Kayıtlı benchmark kabulü kaynak koşusuna aittir. thermal_1d ayrıca params değişikliği nedeniyle STALE.

**Sıradakiler**

1. RAE iz bloğu ağı. İz kesiti normal dağılımı gevşetilip katman eğimi sınırlanmalı, kaba MG3/MG0 ardından kapı geçerse orta/ince koşulmalı.
2. Kabuk mod şekilleriyle p-k flutter çözümü.
3. thermal_1d yeniden koşusu (params nedeniyle STALE).
4. SST ve profil taraması.
5. GVT ve fiziksel testler.

---

## 7. Güncelleme günlüğü
- 2026-11-04: İlk sürüm (v0.6 taslağı; CFD ve FEM sürüyor).
- 2026-11-04 22:20: Resmi RAE native sonuçları ve ikili kabul kararı işlendi; Codex limiti doldu, CFD'yi Claude devraldı.
- 2026-11-04: ILU pilotları ıraksadı (hipotez çürüdü), MG0 testi başladı. FEM bitti: kupon kabul, kanat f_1T 272,5 Hz, flutter ≈1185 km/h.
- 2026-11-06: İter5 kapanışı. Düzeltilmiş FEM sayıları, düz levha SA kabulü (GCI %0,88), RAE iz bölgesi PENDING ve thermal_1d STALE işlendi. GCI plato reddi, 3B CMy ve tarihsel v0.5.0 baseline düzeltmeleri yapıldı. Güncel araç codex-cli, sıradaki beş iş yenilendi. Python regresyonları erişim engeli nedeniyle çalıştırılamadı.
- 2026-11-06: PR https://github.com/LegendOfOwl/hiz-750-rc-jet/pull/2 açıldı (iter5 → main). Birleştirme ve v0.6.0 release kullanıcı onayı bekliyor (otomatik birleştirme izin sınıflandırıcısı tarafından engellendi). İnceleme paketi: C:/Users/Urungu/Desktop/HIZ-750_Inceleme (`tools/inceleme_paketi_olustur.py` ile yeniden üretilir).
