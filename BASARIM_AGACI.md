# HIZ-750 Başarım Ağacı (devir notu)

> Farklı bir sohbete veya başka bir yapay zekâya devir için yazıldı. Projenin nereye geldiğini, her sonucun nasıl elde edildiğini, nelerin yanlış çıktığını ve sırada ne olduğunu anlatır.
> **Son güncelleme:** 2026-11-04 · dal `iter5/yuksek-dogruluk` · son commit `1e280cc`
> **Güncelleme kuralı:** Her kilometre taşında (bir analiz kabul edildiğinde, yama alındığında, PR açıldığında, sürüm çıktığında) ve en az her çalışma oturumunun sonunda güncellenir. En yeni bilgi "Şu an" bölümündedir.

İşaretler: ✅ bitti ve doğrulandı · 🟡 bitti ama koşullu ya da yalnızca masa başı · 🔄 sürüyor · ⏳ bekliyor · ❌ yanlış çıktı veya terk edildi

---

## 0. Önce bunu oku

**Hedef:** 750 km/h ölçüm hızında uçan türbinli bir RC jet İHA. CAD, analizler ve dokümantasyon birlikte yürüyor. Kullanıcı Türkçe yazıyor ve iş tamamlanana kadar döngüde kalınmasını istiyor.

**Repo:** `C:/Users/Urungu/Desktop/Yeni klasör`. GitHub'da `LegendOfOwl/hiz-750-rc-jet`, herkese açık.

**Dallar ve sürümler:**
- `main` = v0.5.0, yayımlandı.
- Çalışma dalı `iter5/yuksek-dogruluk` (v0.6 taslağı).
- Etiketler: v0.4.0, v0.5.0.

**Ana kurallar:**
- Tek veri kaynağı `params.py`. Analizler ve CAD değerlerini buradan okur; sayılar başka bir yere sabit yazılmaz.
- Bütün zincir `run_all.sh` ile yeniden üretilir. Bu dosya LF satır sonu ister (`.gitattributes`).
- `main`'e birleştirmek için kullanıcıdan **açıkça** onay alınır.
- Kullanıcı Codex'in kullanılmasına izin verdi (aşağıdaki Codex köprüsü bölümüne bak). Limit bitmek üzereyse yeni bir sürüme başlanmaz.

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
    ├─ ✅ Termal 1B benchmark (3 ağ) kabul
    ├─ 🟡 Motor bölmesi termal → 2 mm ısı keçesi ZORUNLU (h/k/ε ölçülmedi)
    ├─ ✅ FEM CLT kupon benchmark (5 laminat, 3 ağ, hata ≤ %1,12 < %2)
    ├─ 🟡 FEM kompozit kanat kabuk (7168 S8R, dolu/boş tank; REVIEW_REQUIRED — malzeme sabitleri varsayım)
    │   ├─ f_1B 39,5 Hz, f_1T 272,5 Hz (1D fe_modal 305,7 Hz → kabuk %11 düşük; GVT ≥ 230 Hz yine OK)
    │   ├─ 18 g uç sehim 47,7 mm; min Tsai-Wu R 3,66 (KD 0,544 ile 1,99), arka kiriş kapağı
    │   ├─ ⚠️ Flutter (f_1T ölçekleme) 1307 → ≈1185 km/h: 1080 OK, 1,25 model payı (1350) YOK → f_1T ≥ 316 Hz gerek
    │   └─ ⚠️ Kaburgalar f_1T'yi belirliyor (kaburgasız 198–207 Hz < 230)
    ├─ 🔄 CFD doğrulama (Codex 5HV4)
    │   ├─ 🟡 Düz levha kaba ağ: kapıyı geçti (Cf 0,002854, y+max 0,49)
    │   ├─ 🔄 Düz levha orta ağ: ν̃ 3,07 mertebe düştü, devam koşusu
    │   ├─ ❌ Düz levha ince ağ: 1202. iterasyonda ıraksadı → yeniden koşulacak
    │   ├─ ❌ RAE2822 Case 6 kendi ağımız: 1430. iterasyonda ıraksadı
    │   ├─ 🟡 Düz levha orta ağ: 7 restart sonrası kapıyı geçti (Cf 0,0028585, Schlichting'e −%4,8)
    │   ├─ 🟡 Resmi SU2 RAE2822 cfg+ağ native: iteratif kapı ✅, CL −%2,6 / CD +%5,9 / Cm +%2,3 → çözücü/cfg referansı KABUL; Cp RMSE 0,098 > 0,08 → deney Cp kabulü YOK (SA şok konumu)
    │   ├─ ❌ ILU + LINEAR_SOLVER_ERROR 1e-6 pilotları: ikisi de yine ıraksadı (RAE 1452, düz levha 1155. iter) → bu ayar sebep DEĞİL
    │   ├─ 🔄 MGLEVEL 0 + CFL_ADAPT (1→100) pilotları — ortak faktör multigrid mi? (`C:/hz750run/pilot_mg0_*`)
    │   ├─ ⏳ NACA 64A007 M0,61 (3 ağ) ↔ NeuralFoil + Kármán-Tsien
    │   └─ ⏳ (zaman kalırsa) 3B sınır tabaka ağları
    ├─ ⏳ Codex yamasının incelenip alınması
    ├─ ⏳ docs/10, README, CHANGELOG [0.6.0] entegrasyonu
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
| Gecikmiş onay cevabı "rejected by user" sayıldı | Codex köprüsü | 10 dk zaman aşımı. Gerekirse Codex'ten isteği yeniden yollaması istenir |

---

## 4. Açık riskler ve varsayımlar

- **Rüzgâr hamlesi:** 15 m/s'lik kısa hamle 19–27 g üretiyor ve FC bunu azaltamıyor. Uçuşlar yalnızca sakin havada yapılır.
- **Zorunlu testler:** GVT (f_1T ≥ 230 Hz), türbin itki modeli, alık basınç kazanımı, yer koşusunda termokupl ölçümü.
- **Kontrol yasası** 350 km/h altı için yok.
- **Termal model:** h, k ve ε ölçülmedi; sonuçlar koşullu.
- **Varsayımlar:** 300 m irtifa, ISA, rüzgârsız hava; ölçüm hızı 750 km/h, operasyonel limit 800 km/h. Tam liste `docs/08` "Varsayımlar" tablosunda.

---

## 5. Codex köprüsü (yerel ayar)

- Değişen dosya: `C:/Users/Urungu/.claude/mods/claudex/scripts/appserver.mjs`. Orijinali: `appserver.mjs.bak-orig`.
- Aç/kapa: `~/.claude/mods/claudex/claude-approves.json` içinde `{"enabled": true}`.
- Codex'in sandbox dışındaki her isteği Claude'a `approve-...` sorusu olarak gelir. Cevap `mcp__claudex__tell` ile verilir:
  - **ALLOW:** salt okuma, analiz ve worktree içine yazım. Kapsamı belli çözücü koşuları da bu sınıfa girer.
  - **DENY:** yanlış vaka, kapsam dışı iş, gerekçesi olmayan indirme.
- Codex'e verilen talimatlar:
  - Salt okuma işlerini önce kendi sandbox'ında denesin.
  - Onayı yalnızca çözücü başlatırken, süreç durdururken ve bir şey indirirken istesin.
  - İlerlemeyi en fazla 15 dakikada bir kontrol etsin.
  - `docs/10`, README ve CHANGELOG'a dokunmasın; özetini `cfd/RESULTS_iter5.md`'ye yazsın.
- Codex'in worktree'si: `C:/Users/Urungu/.claude/claudex/worktrees/5HV4`.

---

## 6. Şu an ve sıradakiler

**Şu an (2026-11-04, 22:20):**
1. 🔄 Codex 5HV4 kullanım limitine takılıp durdu (yeniden açılma 23:26). İşi Claude devraldı. Codex'in kodu ve sonuçları hâlâ yalnız `C:/Users/Urungu/.claude/claudex/worktrees/5HV4` içinde (özet: `cfd/RESULTS_iter5.md`), ana repoya alınmadı. ILU/1e-6 pilotları bu worktree'de koşuyor; loglar `C:/hz750run/logs/pilot_*_ilu.log`. Pilot yakınsarsa ıraksamanın sebebi eski ayardı, yine ıraksarsa ağ.
2. ✅ FEM alt ajanı bitti, commit 692fdd3 (özet `fem/RESULTS_iter5.md`). **Tasarım kararı bekliyor:** 1350 km/h flutter payı için f_1T'yi 272 → ≥316 Hz'e çıkarmak (kabuk katı/kaburga/kiriş) ya da model payını yeniden tanımlamak. Not: `study.py` kaynak SHA'larını tutuyor; Codex cfd yaması alınınca cantilever, coupon ve kanat çalışmaları sırayla yeniden koşulmalı.

**Sıradakiler:**
1. Codex yamasını incele ve al (`mcp__claudex__apply`).
2. FEM ve CFD sonuçlarını `docs/10`, README ve CHANGELOG [0.6.0]'a işle. f_1T değişirse flutter ve GVT ölçütlerini güncelle.
3. Ağır analizler bitince `run_all.sh`'yi koş; çıktılar tutarlı mı kontrol et.
4. PR aç (iter5 → main). Birleştirmek için kullanıcı onayı al.
5. v0.6.0 etiketi ve GitHub Release.
6. Sonraki iterasyon adayları (başlamadan önce kullanıcıya sor):
   - 3B tam uçak RANS
   - S-kanal DC60
   - 350 km/h altı kontrol yasası
   - Hamle yükü azaltma

---

## 7. Güncelleme günlüğü
- 2026-11-04: İlk sürüm (v0.6 taslağı; CFD ve FEM sürüyor).
- 2026-11-04 22:20: Resmi RAE native sonuçları ve ikili kabul kararı işlendi; Codex limiti doldu, CFD'yi Claude devraldı.
- 2026-11-04: ILU pilotları ıraksadı (hipotez çürüdü), MG0 testi başladı. FEM bitti: kupon kabul, kanat f_1T 272,5 Hz, flutter ≈1185 km/h.
