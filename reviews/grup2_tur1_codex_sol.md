İnceleme tabanı: yerel `0e0de7f`. Dosya yazmadım; test veya çözücü çalıştırmadım. Aşağıdaki test sonuçları kayıtlı incelemelere aittir.

## K1 — İter5 değişiklikleri

**KARAR: Kazanımları koru; kabul iddialarını ve bazı kuralları değiştir.**

| Değişiklik | Karar ve gerekçe | Risk / güven |
|---|---|---|
| s41r043w1 rijitleştirmesi | **Tut, geçici tasarım olarak.** +0,285 kg karşılığında iyileşme var; tank hacmi ve sandviç kararlılığı kapanmadan dondurma. | Sistem etkileri açık / orta |
| `fe_modal` düzeltmesi | **Tut.** Burulma modunun çözüm dışında kalması ve kök takibi hataları gideriliyor. | GVT haritasında aynı kontroller gerekli / yüksek |
| Kabuk p-k | **Tut, geliştirme modeli olarak.** Frekans ölçeklemesinden daha fazla fizik içeriyor. | Bağımsız doğrulama ve kumanda serbestlikleri eksik / orta |
| GCI kuralı | **Değiştir.** Plato reddini ve artırılmış güvenlik katsayısını tut; mertebe sınırlamasının dayanağını bağımsız incelet. | Karma mertebeli ayrıklaştırmada belirsizlik küçümsenebilir / orta |
| STALE kapsamı | **Tut, bağımlılık kapsamını denetle.** İlgisiz değişikliklerin benchmarkları eskitmesi önlenmeli; gerçek girdiler kapsam dışında kalmamalı. | Eksik bağımlılık izleme / orta |
| Sizing–params bağlantısı | **Tut.** Tek veri kaynağı ve zincir tutarlılığı sağlıyor. | Türetilmiş raporların eskimesi / yüksek |
| İnceleme paketi | **Tut, yeniden üret.** Düzeltilmiş eşleme yararlı; yalnız dry-run yapılmış. | Dağıtılan paketin kaynakla ayrışması / yüksek |

Kaynaklar: [yapı incelemesi](</C:/Users/Urungu/Desktop/Yeni klasör/reviews/grup1_yapi_fem.md>), [CFD incelemesi](</C:/Users/Urungu/Desktop/Yeni klasör/reviews/grup1_cfd_dogrulama.md>), [zincir incelemesi](</C:/Users/Urungu/Desktop/Yeni klasör/reviews/grup1_zincir_dokuman.md>).

## K2 — Flutter tasarım değeri

**KARAR:** Şimdilik **1267 km/h’yi kanada ait ihtiyatlı çalışma değeri** olarak koru; **1324 km/h’yi koşullu kabuk p-k tahmini** olarak birlikte raporla. İkisi de bütün uçağın doğrulanmış flutter sınırı değildir.

**Gerekçe:** Kabuk p-k’da kesit distorsiyonu, kumanda hareketleri ve kuyruk/gövde bağlaşımı eksik; kritik sonuç Mach düzeltmesinin tavan bölgesinde. Daha küçük sonucu seçmek bu eksikleri güvenli biçimde sınırlamaz. **1080 km/h** gereksinim olarak korunmalı; **1350 km/h** ek model payı hedefi olabilir, mevcut kanıtla zorunlu kabul şartı yapılamaz. Sabit frekans hedefi yerine doğrulanmış flutter zarfı kullanılmalı. [Kaynak](</C:/Users/Urungu/Desktop/Yeni klasör/reviews/grup1_yapi_fem.md>).

**Risk:** Kanat sonucundan uçak güvenliği çıkarılması. **Güven:** Orta.

## K3 — Servo konumu ve balans

**KARAR:** Önce FEM ile doğrula; ilk aday servoyu öne almak olsun. Uç balansını şimdilik uygulama.

**Gerekçe:** **1427/1403 km/h** servo ve **1446/1424 km/h** balans sonuçları Ritz tahminidir; balans **yarı kanat başına 30 g** ekler. Gerçek servo montajı, bağlantı esnekliği ve dönme ataleti yeniden modellenmeli; bütün kütle/CG/kontrol zinciri güncellenmeli. [Kaynak](</C:/Users/Urungu/Desktop/Yeni klasör/reviews/grup1_yapi_fem.md>).

**Risk:** Tahmini kazancın gerçek montajda kaybolması. **Güven:** Önceliklendirmede yüksek, sayısal kazançta düşük.

## K4 — Tank hacmi

**KARAR:** Görev yeterliliğini kabul etme; önce gerçek kullanılabilir hacmi ve dinamik görev yakıtını hesapla. Kaburga aralığını yakıt kazanmak için hemen büyütme.

**Gerekçe:** Yaklaşık **5,0 L**, `params.py` içindeki **4,0 kg / 0,80 kg/L** yükün yalnız nominal hacmine eşit. Kaburgalar, dolum payı, kullanılamayan yakıt ve transfer düzeni kapanmamış; görevde dönüş sonrası hızlanma yakıtı da eksik. Açık doğrulanırsa önce gövde tankı/yerleşim veya görev profili değerlendirilmeli. [Kaynak](</C:/Users/Urungu/Desktop/Yeni klasör/reviews/grup1_zincir_dokuman.md>), [params.py](</C:/Users/Urungu/Desktop/Yeni klasör/params.py>).

**Risk:** Yakıt kesilmesi ve farklı boşalma sırasıyla CG değişimi. **Güven:** Yetersiz kanıt kararında yüksek.

## K5 — Açık riskler

| Konu | Karar, çözüm ve uçuş engeli | Güven |
|---|---|---|
| Termal | **Şimdi.** **126,1 °C**, **<120 °C** kriterini sağlamıyor. Soğutma–yalıtım–açıklık birlikte tasarlansın; sıcak malzeme verisi, termokupl ve stop sonrası ölçümle kapatılsın. **Uçuş engeli.** | Yüksek |
| FC filtreleri | **Şimdi.** Yaklaşık **41°**, **45°** hedefinin altında bir kestirim; gerçek dijital zincirle yeniden çözüm ve HIL gerekli. **Uçuş engeli.** | Yüksek |
| Kuyruk flutter | **Şimdi.** HT **310–360 Hz**, VT **250–320 Hz** aralıkları gereksinim taraması; ölçülmüş modlar değil. Bağlaşık model ve GVT gerekli. **Uçuş engeli.** | Yüksek |
| Sandviç kararlılığı | **Şimdi.** **1,2–1,5** payı kaba ve indirgeme katsayısız. Çekirdek kaymasını temsil eden alt model ve kupon testi gerekli. **Yüksek hızlı uçuş engeli.** | Yüksek |
| RAE Cp ölçütü | **Şimdi.** Ön kenarı topluca dışlama. Önce veri ve eşleştirme yöntemini incele; tam veri RMSE’sini koru, dışlamalı sonucu duyarlılık olarak ver. **Doğrulama zinciri engeli; tek başına doğrudan uçuş kriteri değil.** | Yüksek |

Sayısal kaynaklar: [CFD](</C:/Users/Urungu/Desktop/Yeni klasör/reviews/grup1_cfd_dogrulama.md>), [yapı](</C:/Users/Urungu/Desktop/Yeni klasör/reviews/grup1_yapi_fem.md>), [disiplinler arası inceleme](</C:/Users/Urungu/Desktop/Yeni klasör/reviews/grup1_codex_disiplinlerarasi.md>).

## K6 — Yol haritası ve iter6

**KARAR:** Plan geniş, fakat kabul kanıtı ve bağımlılık sırası eksik. Her işe sorumlu, giriş koşulu, kabul ölçütü ve kapanış kanıtı ekle. İlk beş iş:

1. Bütün uçak aeroservoelastik model, servo ölçümü ve GVT planı — bulgular **1, 3**.
2. Gerçek FC zinciri, düşük hız, kazanım geçişleri, arızalar, hava verisi, aşırı hız ve birleşik hamle/manevra — **2, 4, 11–14, 18**.
3. Tank–transfer–CG–sloshing ile dinamik görev/yakıt hesabı — **7, 9, 10, 15**.
4. Termal koruma, sandviç kararlılığı ve kök bağlantısı kapanışı — **8** ve yapı bulguları.
5. Takılı motor/alık doğrulaması; RAE orta/ince devam koşuları, sabitlenmiş Cp ölçütü, ardından profil/SST ve uygulanabilir kaynak bütçesiyle 3B CFD — **5, 6**.

**16–17** için kayıtlı düzeltmeleri entegre kaynakta teyit et. [Kaynak](</C:/Users/Urungu/Desktop/Yeni klasör/reviews/grup1_codex_disiplinlerarasi.md>).

**Risk:** Belge güncellemesinin fiziksel kapanış sayılması. **Güven:** Yüksek.

## K7 — Birleştirme ve yayın

**KARAR:** Şimdi koşulsuz onay verme. Kısa entegrasyon kapanışı sonrası, kapsamı açık bir araştırma sürümü olarak birleştirme/yayın mümkün.

**Ön koşullar:** Kesin commit üzerinde gerekli regresyonlar, artefakt kontrolü, kaynak/girdi hash tutarlılığı, güncel durum raporu ve yeniden üretilmiş inceleme paketi. Eski “kabuk p-k açık”, “benchmark STALE” ifadeleri temizlenmeli.

Güncel kayıtlarda RAE **PENDING**, orta/ince **BLOCKED**; motor termali **REVIEW_REQUIRED**. `Infinity` sorunu giderilmiş, JSON okunabiliyor. Bunlar tamamlanmış yüksek doğruluk veya uçuş kabulü diye sunulmamalı. Fiziksel engellerin tamamı kod birleştirme şartı değildir. [Kaynak](</C:/Users/Urungu/Desktop/Yeni klasör/CHANGELOG.md>).

**Risk:** Sürüm etiketinin doğrulanmış uçak izlenimi vermesi. **Güven:** Yüksek.

**Genel hüküm: İter5’i koru; entegrasyon kanıtını tamamlayarak yayımla, bütün uçak ve kritik sistem doğrulamaları kapanmadan uçuş onayı verme.**

