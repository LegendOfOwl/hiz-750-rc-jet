**ASTRA hükmü:** Astra/Sol’un entegrasyon kapanışı yaklaşımı doğru. GCI’nin düşük-p sınırlamasını ise geri almak gerekmiyor. İnceleme `0e0de7f` üzerindedir; dosya yazmadım, test/çözücü çalıştırmadım.

**Sayısal doğrulama**

- **Üç üyenin ortak değerleri doğru:** +0,285 kg, yarım kanattaki 0,142562 kg artışın iki katı; ölçekli flutter **1266,904/1270,561 km/h**, Tsai-Wu **4,15954**. [summary_fine_corrected.json:129](</C:/Users/Urungu/Desktop/Yeni klasör/fem/results/stiffening/summary_fine_corrected.json:129>), aynı dosya:166–170. Ancak R değeri **kök bölgesi hariçtir**.
- Kabuk p-k **1325,969/1324,138 km/h**; Astra/Sol/Sonnet’in yuvarlamaları doğru. [shell_flutter.json:488](</C:/Users/Urungu/Desktop/Yeni klasör/fem/results/shell_flutter.json:488>), aynı dosya:560.
- Astra/Sol’un servo **1427/1403**, balans **1446/1424 km/h** değerleri kayıtlı Ritz tahminleriyle aynı. [shell_flutter.json:777](</C:/Users/Urungu/Desktop/Yeni klasör/fem/results/shell_flutter.json:777>), aynı dosya:842,904,969.
- Sonnet’in düzeltilmiş **1452 km/h**, **17,44 kg**, **4,69 L** değerleri doğru: [fe_sonuclar.json:273](</C:/Users/Urungu/Desktop/Yeni klasör/structures/out/fe_sonuclar.json:273>), [performans_ozet.txt:1](</C:/Users/Urungu/Desktop/Yeni klasör/performance/out/performans_ozet.txt:1>), aynı dosya:22.
- Termal **126,1004°C** doğrulandı; sınır **<120°C**. [fine.json:11](</C:/Users/Urungu/Desktop/Yeni klasör/thermal/results/engine_thermal_T250_F2_679b6a3875/fine.json:11>), [docs/06:43](</C:/Users/Urungu/Desktop/Yeni klasör/docs/06_uretim_test_maliyet.md:43>). **≈41°**, kayıtlı **49,948°** faz payına varsayılan filtrenin eklenmesiyle yapılan kestirimdir; ölçüm değildir. [fc_sonuclar.json:1349](</C:/Users/Urungu/Desktop/Yeni klasör/aero/out/fc_sonuclar.json:1349>).
- HT **310–360**, VT **250–320 Hz** gereksinim taramaları; **1,2–1,5** sandviç payı elle hesaplanmış, indirgemesiz tahmindir. Üyelerin nitelendirmesi doğru. [kuyruk_flutter.json:18](</C:/Users/Urungu/Desktop/Yeni klasör/structures/out/kuyruk_flutter.json:18>), [grup1_yapi_fem.md:149](</C:/Users/Urungu/Desktop/Yeni klasör/reviews/grup1_yapi_fem.md:149>).

**Ayrışmalarda hüküm**

- **GCI:** Düşük-p dalı GCI-OR yaklaşımına uygundur: `min(max(0.5,p),p_formal)`, Fs=3. [Kod:46](</C:/Users/Urungu/Desktop/Yeni klasör/validation/convergence.py:46>), [Phillips, §3.2.2](https://vtechworks.lib.vt.edu/bitstream/handle/10919/31504/Phillips_TS_T_2012.pdf). Burada Astra/Sonnet’in “tut” oyu doğru; Sol’un kaynak/formal-mertebe denetimi talebi yerinde. **p=0,434462 → 0,5; GCI=%1,816606** doğrulandı. [study.json:75](</C:/Users/Urungu/Desktop/Yeni klasör/validation/results/flat_plate_SA/study.json:75>). Sınırlama tek başına belirsizliği artırmaz: aynı verilerle Fs=3 ve sınırlanmamış p yaklaşık **%2,111** verir.
- **K7:** Şimdi değil, entegrasyon kapanışından sonra. Tam liste: kesin kaynak commit’i; `run_all.sh`; regresyonlar ve modal/kök-takibi kontrolleri; bağımlılık/hash/STALE denetimi; etkilenen benchmarkların, kanat/rijitleştirme ve ardından kabuk p-k sonuçlarının yenilenmesi; durum/karşılaştırma raporları; artefakt kontrolü; tutarlı belgeler; yeniden üretilmiş inceleme paketi; açık engelleri belirten sürüm notu; birleştirme öncesi kullanıcı onayı. **`run_all.sh` FEM/p-k doğrulama zincirini kapsamıyor.** [run_all.sh:17](</C:/Users/Urungu/Desktop/Yeni klasör/run_all.sh:17>). Tarihsel 1813 silinmek yerine “hatalı/eski” olarak korunmalı.
- **K4:** Astra/Sol doğru: **yeterliliği kanıtlanmamış**. Yaklaşık hacim ve eksik dinamik görev hesabı “yetersiz” hükmüne yetmez.
- **1240 ve %15:** Kabul eşiği olarak benimsemiyorum. 1,15×1080=1242 aritmetiği güvenlik gerekçesi değildir; rezerv görevden türetilmeli. Sonnet’in “1350 yalnız tam uçak hedefidir” ifadesi kaynakla uyuşmuyor: kanat için de model-pay hedefidir. [docs/04:604](</C:/Users/Urungu/Desktop/Yeni klasör/docs/04_yapi_flutter.md:604>).
- **Balans:** Evet, **30 g/yarım kanat; toplam 60 g**, montaj hariç. [grup1_yapi_fem.md:89](</C:/Users/Urungu/Desktop/Yeni klasör/reviews/grup1_yapi_fem.md:89>).

**Ortak kör nokta:** Standart sorti **iki geçiş, nominal rezerv ≈%31**; **%6 dört geçişe** ait. Üçü de bu ayrımı karara taşımamış. Bu, kapasite kararını değiştirir; yeterliliği tek başına kanıtlamaz. [docs/05:59](</C:/Users/Urungu/Desktop/Yeni klasör/docs/05_sistemler_performans.md:59>).

**Nihai oy**

- **K1:** Kazanımları tut; kapsam ve kanıt zincirini tamamla.
- **K2:** 1267 geçici çalışma değeri; 1080 gereksinim, 1350 hedef; fiziksel alt sınır iddiası yok.
- **K3:** Önce servo seçeneğinin FEM doğrulaması; balans beklesin.
- **K4:** Yeterlilik kanıtlanmamış; 43 mm korunsun.
- **K5:** Kritik fiziksel riskler uçuş engeli; RAE değerlendirme kuralı şimdi sabitlensin.
- **K6:** Öncelik: entegrasyon, aeroservoelastik, kontrol, yakıt/görev, termal-motor kapanışı.
- **K7:** Şimdi hayır; entegrasyon sonrası açık sınırlamalarla araştırma sürümü.

