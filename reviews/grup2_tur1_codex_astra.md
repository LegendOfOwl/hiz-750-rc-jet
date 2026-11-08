## K1 — İter5 değişiklikleri faydalı mı?

**KARAR: Evet; aşağıdaki koşullarla korunsun.** Yalnızca dosyaları ve Git kayıtlarını okudum; dosya yazmadım, test çalıştırmadım. Değerlendirme yerel `0e0de7f` kaydına dayanıyor.

- **s41r043w1: TUT, geçici tasarım tabanı olarak.** Ek **0,285 kg**, rijitlik ve kesit CG’sinde fayda sağlıyor; tank hacmi ve sandviç kararlılığı kapanmadan imalat onayı verilmemeli. [Yapı raporu](</C:/Users/Urungu/Desktop/Yeni klasör/reviews/grup1_yapi_fem.md>), [CHANGELOG](</C:/Users/Urungu/Desktop/Yeni klasör/CHANGELOG.md>)
- **fe_modal düzeltmesi: TUT.** Burulma modunun çözüm dışında kalmasını düzeltiyor. Kök takibi kontrolü GVT taramasına da taşınmalı.
- **Kabuk p-k: TUT.** Daha temsilî analiz; bağımsız fiziksel doğrulama yerine geçmez.
- **GCI kuralı: TUT; gerekçesini tamamla.** Plato reddi ve düşük mertebede ihtiyatlı belirsizlik hesabı faydalı; kullanılan kaynak ve formal mertebe seçimi doğrulanmalı.
- **STALE kapsamı: TUT.** İlgisiz değişiklikleri ayırmak doğru; gerçek bağımlılıkların kapsam dışında kalmadığı sınanmalı.
- **Sizing–params bağlantısı: TUT.** Tasarım zincirindeki eski kütle/geometri kullanımını gideriyor.
- **İnceleme paketi: TUT; yeniden üret.** Eşleme düzeltilmiş, teslim paketi henüz yenilenmemiş. [Zincir raporu](</C:/Users/Urungu/Desktop/Yeni klasör/reviews/grup1_zincir_dokuman.md>), [CFD raporu](</C:/Users/Urungu/Desktop/Yeni klasör/reviews/grup1_cfd_dogrulama.md>)

**Risk:** Yazılım iyileşmesini tasarım kabulü saymak. **Güven: yüksek.**

## K2 — Flutter tasarım değeri

**KARAR: Geçici kanat tasarım değeri 1267 km/h kalsın; 1324 km/h, kabuk p-k tahmini olarak ayrıca raporlansın.** İkisi de bütün uçağın doğrulanmış flutter sınırı değildir. Kabuk p-k’da kumanda serbestlikleri eksik; kritik sonuç yapay Mach tavanının üzerinde oluşuyor. Küçük olanı seçmek de kanıtlanmış fiziksel alt sınır sağlamaz. [Yapı raporu](</C:/Users/Urungu/Desktop/Yeni klasör/reviews/grup1_yapi_fem.md>)

**1080 km/h gereksinimi korunsun. 1350 km/h**, belirsizlik azaltılana kadar iç tasarım hedefi olarak tutulsun; zorunlu fiziksel eşik olduğu gösterilmemiştir. Bu sayıya ulaşmak uğruna doğrulanmamış kütle eklenmesin. **316 Hz** evrensel hedefi terk edilsin; mevcut **230 Hz** GVT alt sınırı yeni modelle yeniden türetilsin, tek başına uçuş kabulü olmasın. [Yapı belgesi §15](</C:/Users/Urungu/Desktop/Yeni klasör/docs/04_yapi_flutter.md:602>)

**Risk:** Eksik mekanizmaları sayısal payla örtmek. **Güven: orta.**

## K3 — Servo konumu ve balans

**KARAR: Önce FEM doğrulaması; ilk aday servoyu öne almak.** Ritz sonuçları servo için **1427/1403**, uç balansı için **1446/1424 km/h** dolu/boş tahminleridir. **30 g, yarı kanat başınadır.** Bunlar uygulanmış tasarım sonucu değildir. [Yapı raporu](</C:/Users/Urungu/Desktop/Yeni klasör/reviews/grup1_yapi_fem.md>)

Servo yerleşimi, bağlantı rijitliği, boşluk, gerçek kütle/atalet ve kısmi yakıt durumları birlikte çözülmeli. Yeni montajın kütlesi bilinmeden “kütle maliyeti yok” kabul edilmemeli. Uç balansı ikinci seçenek kalsın.

**Risk:** Burulma faydasına karşı eğilme, yerel bağlantı ve kontrol sorunları. **Güven: orta.**

## K4 — Tank hacmi ve kaburgalar

**KARAR: Göreve yeterlilik gösterilmemiştir; şimdilik kaburga aralığı korunsun.** Yaklaşık **5,0 L**, kesin kullanılabilir hacim değildir; kaburga ve web kayıpları eksik temsil ediliyor. Görev hesabında yeniden hızlanma yakıtı ve rezerv de kapanmamış. [Zincir raporu](</C:/Users/Urungu/Desktop/Yeni klasör/reviews/grup1_zincir_dokuman.md>)

Önce gerçek iç geometri, kullanılamayan yakıt, transfer düzeni ve dinamik görev bütçesi hesaplanmalı. Eksik kapasite doğrulanırsa önce tank yerleşimi veya görev revizyonu değerlendirilsin; kaburgayı seyrekleştirmek ancak yapı/flutter karşılaştırmasıyla seçilsin.

**Risk:** Kapasiteyi artırırken rijitliği kaybetmek; yeterli hacim varken beslemenin kesilmesi. **Güven: yüksek.**

## K5 — Diğer açık riskler

**KARAR: Hepsi şimdi ele alınmalı.** Sayısal dayanaklar [yapı](</C:/Users/Urungu/Desktop/Yeni klasör/reviews/grup1_yapi_fem.md>), [disiplinlerarası](</C:/Users/Urungu/Desktop/Yeni klasör/reviews/grup1_codex_disiplinlerarasi.md>) ve [CFD](</C:/Users/Urungu/Desktop/Yeni klasör/reviews/grup1_cfd_dogrulama.md>) raporlarındadır.

| Konu | Çözüm ve gerekçe | Risk / uçuş öncesi engel / güven |
|---|---|---|
| Termal: **126,1°C; kriter <120°C** | Soğutma, keçe, sıcak açıklık ve duruş sonrası ısınmayı birlikte çöz; termokupla doğrula. | Malzeme/bağlantı kaybı / **Evet** / yüksek |
| FC: yaklaşık **41°; hedef 45°** | Gerçek filtre, gecikme ve yüklü servo modeliyle yeniden çöz, HIL yap. Mevcut sayı kestirimdir. | Kararsızlık / **Evet** / yüksek |
| Kuyruk: **HT 310–360, VT 250–320 Hz** | Bunlar ölçülen frekanslar değil, kaba gereksinim taraması. Bağlaşık FE ve bütün uçak GVT gerekli. | Bilinmeyen flutter / **Evet** / yüksek |
| Sandviç: **1,2–1,5 pay** | Çekirdek kaymasını içeren alt model, kusur/sıcaklık etkileri ve panel deneyi. | Yerel kararlılık kaybı / **Evet** / yüksek |
| RAE Cp dışlaması | Noktayı yalnız kabul sağlıyor diye çıkarma. Veri kaynağı ve eşleme incelensin; tam-küme sonuçları korunsun, alternatif değerlendirme ayrıca raporlansın. | Yanlış CFD kabulü / **Bu CFD’ye dayalı uçuş kararı için evet** / yüksek |

## K6 — Yol haritası

**KARAR: Yön doğru, kapanış ölçütleri ve bağımlılıklar eksik.** İter6’nın ilk beş işi:

1. **Kanıt tabanını sabitle:** Güncel kaynak–sonuç eşlemesi, STALE değerlendirmesi, regresyonlar ve çelişen belgeler.
2. **Yapı/aeroelastik kapanış:** Sandviç, kök bağlantısı, kuyruk–gövde–kumanda bağlaşımı, servo rijitliği ve birleşik manevra/hamle yükleri.
3. **Kontrol kapanışı:** Filtreler, hava verisi, aşırı hız, arızalar, kazanç geçişleri, düşük hız ve itki momenti.
4. **Yakıt/görev kapanışı:** Hacim, transfer, tank bazlı CG/atalet, sloshing, hızlanma ve rezerv; dolly ayrılmasının fiziksel doğrulaması.
5. **Motor–alِık–termal kapanış:** Takılı itki/debi, distorsiyon, sıcak durum; RAE sonrası profil ve uçak CFD karşılaştırması.

Bu sıra [Astra’nın 18 bulgusunu](</C:/Users/Urungu/Desktop/Yeni klasör/reviews/grup1_codex_disiplinlerarasi.md>) kapsar. Pitot, dolly ve tırmanma düzeltmeleri kod/belge ilerlemesidir; sistem doğrulaması tamamlanmış sayılmamalı.

**Risk:** İş listesini kabul kanıtı sanmak. **Güven: yüksek.**

## K7 — Birleştirme ve yayın

**KARAR: PR #2 mevcut haliyle koşulsuz hazır değil; v0.6.0 şimdi yayımlanmasın.**

Önkoşullar: son kaynak durumunda test/artefakt kanıtı, kanat sonuçlarının güncelliği, yenilenmiş inceleme paketi ve tutarlı durum belgeleri. Özellikle [CHANGELOG](</C:/Users/Urungu/Desktop/Yeni klasör/CHANGELOG.md>) hâlâ düzeltilmiş modal hatayı ve tamamlanan işleri eski ifadelerle anlatıyor. Eski `Infinity` bulgusu güncel JSON’da görünmüyor; yeniden açık hata saymıyorum.

Bunlar kapanınca açık mühendislik risklerini taşıyan **araştırma sürümü** birleştirilebilir; uçuş uygunluğu verilmez. **Risk:** Yayının doğrulanmış tasarım olarak okunması. **Güven: yüksek.**

**Genel hüküm: İter5 korunsun; sonraki kararın odağı daha yüksek kanat flutter sayısı değil, bütün uçağın yapı–kontrol–yakıt–termal kanıt zincirini kapatmak olsun.**

