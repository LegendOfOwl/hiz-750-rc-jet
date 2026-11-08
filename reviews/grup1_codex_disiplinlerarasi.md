**750 km/h hedefi fiziksel olarak makul, fakat mevcut analizlerle doğrulanmış değil. En zayıf halka, kuyruk–gövde–kontrol yüzeyleri–servo–uçuş kontrolcüsünün birlikte aeroelastik davranışı.** Performans açısından en büyük belirsizlik ise takılı motorun gerçek net itkisi.

İnceleme tabanı: `iter5/yuksek-dogruluk`, **`8e3c14c`**. Başarım ağacını, istenen dosyaları ve ilgili `main...HEAD` değişikliklerini okudum. Dosya değiştirmedim. Python başlatılamadı; aşağıdaki ek sayılar bağımsız aritmetik kontrollerdir. İnceleme sırasında diğer ajanların yaptığı kaydedilmemiş değişiklikleri bu sürümün doğrulaması saymadım.

**P1:** yüksek hızlı uçuş kararını engelleyen açık. **P2:** tasarım veya doğrulama zincirinde giderilmesi gereken hata. Belirsiz etkileri ayrıca işaretledim.

1. **P1 — Kanat flutter sonucu, bütün uçağın flutter sınırı değil.**  
   **Yer:** [docs/04 §9, §14.1, §15.4](</C:/Users/Urungu/Desktop/Yeni klasör/docs/04_yapi_flutter.md>), [docs/09 §6](</C:/Users/Urungu/Desktop/Yeni klasör/docs/09_ucus_kontrol.md>).  
   **Sorun:** Gövde rijit; aileron dönme serbestliği dışarıda. Elevator için frekans/rijitlik kestirimi var, fakat yatay kuyruk–elevator ve dikey kuyruk–rudder–gövde bağlaşık flutter çözümü yok.  
   **Etki:** ≈1267 km/h, bu eksik mekanizmalar için alt sınır sağlamaz. Eski kanat modelinden gelen **230 Hz GVT eşiği** de bütün uçak için kabul ölçütü olamaz.  
   **Adım:** Gerçek bağlantı ve kumanda esnekliklerini içeren bütün uçak modal/aeroservoelastik modeli; serbest-serbest GVT ile frekans, mod şekli ve sönüm eşleştirmesi. **Eksik mekanizmaların kritik hızı bilinmiyor.**

2. **P1 — Sensör filtreleri mevcut faz payını hedefin altına indirebilir.**  
   **Yer:** [docs/09 §6](</C:/Users/Urungu/Desktop/Yeni klasör/docs/09_ucus_kontrol.md>), [fc_sonuclar.json:1347](</C:/Users/Urungu/Desktop/Yeni klasör/aero/out/fc_sonuclar.json:1347>).  
   **Sorun:** Filtreler modelde yok; belge, 10–15° faz kaybının karşılanabileceğini söylüyor.  
   **Etki:** Güncel kayıtta 750 km/h/tam yakıt yaw faz payı **49,95°**, hedef **45°**. Birinci dereceden 25 Hz filtre bile mevcut kesişim frekansında yaklaşık **9,2°** geciktirir; pay kabaca **41°** olur. Kesin değer yeniden çözülmeli.  
   **Adım:** IMU filtreleri, veri taşıma gecikmesi, örnekleme ve titreşim süzme dahil gerçek dijital zincirle payları yeniden hesaplayıp HIL’de doğrulayın.

3. **P1 — Servo tork yeterliliği, varsayılan dinamik cevabı kanıtlamıyor.**  
   **Yer:** [flight_control.py:49](</C:/Users/Urungu/Desktop/Yeni klasör/aero/flight_control.py:49>), [docs/04 §9](</C:/Users/Urungu/Desktop/Yeni klasör/docs/04_yapi_flutter.md>).  
   **Sorun:** 25 Hz bant genişliği ve 600°/s yüzey hızı, aerodinamik yükten bağımsız sabit. Flutter değerlendirmesi de itme çubuğu rijitliğine dayanıyor; servo dişlisi, montaj ve mafsalların seri esnekliği dahil değil.  
   **Etki:** Rudder seçimi 53,2 kg·cm gereksinime karşı 60 kg·cm: yalnız **%13 nominal pay**. Bu, yük altında hız ve rijitlik payı değildir.  
   **Adım:** Seçilecek servoyu gerçek kol oranı, menteşe yükü, düşük besleme gerilimi ve sıcaklıkta ölçün; tork–hız, boşluk ve dinamik rijitliği kontrol/flutter modellerine taşıyın.

4. **P1 — “Sakin hava” sınırı, manevra ile birleşince yeterli değil.**  
   **Yer:** [docs/09 §4.2](</C:/Users/Urungu/Desktop/Yeni klasör/docs/09_ucus_kontrol.md>), [fc_sonuclar.json:2341](</C:/Users/Urungu/Desktop/Yeni klasör/aero/out/fc_sonuclar.json:2341>).  
   **Sorun:** Hamle analizi 1 g etrafında; 10 g komut sınırıyla eşzamanlı hamle değerlendirilmemiş.  
   **Etki:** Kayıtlı 15 m/s kısa hamle, 750 km/h/boş yakıtta **24,72 g** üretiyor. Doğrusal ölçeklemede 3 m/s yaklaşık **+4,74 g artış** demek; 10 g manevrayla yaklaşık **14,7 g**, yani 12 g limitinin üzerinde. Bu bir birleşik yük kestirimidir.  
   **Adım:** Hız, yakıt ve hamleye bağlı manevra sınırı oluşturun; manevra+hamle, negatif yük ve elastik yük dağılımını birlikte değerlendirin.

5. **P1 — Takılı motorun hız ve sıcaklıkla değişen itkisi doğrulanmamış.**  
   **Yer:** [sizing.py, `thrust()`](</C:/Users/Urungu/Desktop/Yeni klasör/sizing.py>), [inlet_analysis.py:95](</C:/Users/Urungu/Desktop/Yeni klasör/performance/inlet_analysis.py:95>).  
   **Sorun:** Yoğunluk çarpanı ve `k_ram`, kompresör giriş toplam sıcaklığı, düzeltilmiş devir/debi ve sıcaklık sınırlamasının yerini tutmuyor. Basınç kazanımından doğrudan itki kazanımı çıkarılıyor.  
   **Etki:** 750 km/h, 300 m ISA’da giriş toplam sıcaklığı yaklaşık **308 K**; statik havadan **21,6 K yüksek**. Mevcut model **299 N**, sürükleme yaklaşık **212 N** veriyor; itkinin yaklaşık **%29 azalması** bu payı tüketir. Bunun gerçekleşeceğini söylemiyorum; sınırlandırılmamış belirsizlik budur.  
   **Adım:** Motor varyantını sabitleyin; düzeltilmiş debi/devir ve sıcaklık sınırlarıyla takılı motor modeli kurup ölçümle kalibre edin. [NASA’nın düzeltilmiş debi tanımı](https://www.grc.nasa.gov/www/BGH/wcora.html) toplam basınç **ve** sıcaklık gerektirir.

6. **P1 — Alık recovery hesabı, motorla uyumluluk değerlendirmesi değil.**  
   **Yer:** [inlet_analysis.py:87](</C:/Users/Urungu/Desktop/Yeni klasör/performance/inlet_analysis.py:87>), [docs/10 §10.3-C](</C:/Users/Urungu/Desktop/Yeni klasör/docs/10_yuksek_dogruluk_dogrulama.md>).  
   **Sorun:** Debi varsayılan motor talebinden atanıyor; motor–kanal çalışma noktası birlikte çözülmüyor. Ortalama recovery, distorsiyon ve motor kararlılık sınırını belirlemiyor.  
   **Etki:** Kod 750 km/h’te yaklaşık **0,894 kg/s** istiyor. Başlangıçtaki 0,75 kg/s tahmini, güncel P400-PRO-LN üretici değerinden **%12 yüksek**; kesin varyant kontrol edilmeli. Kalkışta yardımcı kapakların açılması ve yan kaymada distorsiyon ayrıca belirsiz.  
   **Adım:** Debi–recovery–distorsiyon–taşma sürüklemesini gaz, hız, hücum açısı ve yan kayma boyunca eşleştirin; motorun kabul sınırını üreticiden alın. [JetCat verisi](https://www.jetcat.de/de/productdetails/produkte/jetcat/produkte/Professionell/p400%20pro), [NASA alık değerlendirmesi](https://www.grc.nasa.gov/www/k-12/airplane/tunmodinlt.html).

7. **P1 — Yakıt transferi ve pompa emiş koşulları kapanmamış. — Koşullu bulgu**  
   **Yer:** [docs/05 §5.4](</C:/Users/Urungu/Desktop/Yeni klasör/docs/05_sistemler_performans.md>).  
   **Sorun:** Alçak kanat tanklarının gövde tankına boşalacağı yazılı; bunu sağlayan basınçlandırma, transfer pompası veya emiş düzeni tanımlı değil. “Festo 4 mm” de iç çapı belirtmiyor.  
   **Etki:** 250 ml hopper, 1,392 L/dk debide ideal olarak yalnız **10,8 s** besler. Örnek olarak 2,5 mm iç çaplı 1 m hatta, Darcy katsayısı 0,03 alınırsa kayıp **≈107 kPa**; 4 mm iç çapta **≈10 kPa**. Gerçek hat hesabı için ölçüler eksik.  
   **Adım:** Tank–havalandırma–valf–hopper–pompa şemasını ve basınç bütçesini tamamlayın; düşük doluluk, sıcak yakıt ve manevra koşullarında kesintisiz debiyi doğrulayın.

8. **P1 — Isıl koruma, soğutma ve sıcak durum geometrisi birlikte çözülmemiş.**  
   **Yer:** [thermal/cases.py:33](</C:/Users/Urungu/Desktop/Yeni klasör/thermal/cases.py:33>), [docs/10 §10.6](</C:/Users/Urungu/Desktop/Yeni klasör/docs/10_yuksek_dogruluk_dogrulama.md>), [docs/06 §6.3](</C:/Users/Urungu/Desktop/Yeni klasör/docs/06_uretim_test_maliyet.md>).  
   **Sorun:** 2 mm keçe, koşullu yer senaryosunda bile **126,1°C** veriyor; kabul sınırı **120°C**. Keçe kalan açıklığı 5,97’den **3,97 mm’ye** indiriyor; soğutma debisi buna bağlı çözülmüyor.  
   **Etki:** Isı köprüleri, stop sonrası ısı birikimi ve termal genleşme de dışarıda. Örneğin 0,525 m paslanmaz boruda ΔT=400 K ve α=17×10⁻⁶/K varsayımı **3,6 mm uzama** verir; bu montaj için ihmal edilebilir değil.  
   **Adım:** Bypass akışı, sıcak bağlantılar ve kayar mesnetleri birlikte değerlendirin; sıcak malzeme özellikleriyle yapıyı kontrol edin. Son belge düzeltmesi bu açığı kabul etmiş, fiziksel olarak kapatmamış.

9. **P2 — Yeni kat ve kaburga planının yakıt kapasitesine etkisi zincire aktarılmamış.**  
   **Yer:** [fe_modal.py:527](</C:/Users/Urungu/Desktop/Yeni klasör/structures/fe_modal.py:527>), [fe_sonuclar.json:166](</C:/Users/Urungu/Desktop/Yeni klasör/structures/out/fe_sonuclar.json:166>), `params.py/FUEL`.  
   **Sorun:** Güncel çıktı kullanılabilir hacmi **0,5467 L**, öneriyi **0,54 L/yarı kanat** buluyor; params hâlâ 0,57 L kullanıyor. Hacim fonksiyonu ayrıca yalnız **bir orta kaburga** düşüyor; 43 mm aralıklı düzeni ve ek web katını tam yansıtmıyor.  
   **Etki:** Belgede kullanılan gövde/merkez tank kayıp paylarıyla toplam yaklaşık **4,95–4,97 L**; gereken 5 L’nin altında, yeni kaburgalar henüz tam düşülmeden.  
   **Adım:** Gerçek iç geometriyle kapasiteyi yeniden hesaplayıp yakıt yükü, CG, görev ve modal kütleleri birlikte güncelleyin.

10. **P2 — Yakıt CG’si ve sloshing, yalnız toplam yakıt oranıyla temsil edilemez.**  
    **Yer:** [mass_properties.py:201](</C:/Users/Urungu/Desktop/Yeni klasör/cad/mass_properties.py:201>), [docs/03, yakıt varsayımları](</C:/Users/Urungu/Desktop/Yeni klasör/docs/03_cad.md>).  
    **Sorun:** Bütün tanklar eşit oranda boşalıyor kabul edilmiş; gerçek besleme sırası farklı olabilir. Kısmi dolulukta sıvı rijit kütle olarak tutuluyor.  
    **Etki:** Kalan 2 kg yakıt yalnız gövde tankındaysa, sabit x=0,940 m varsayımına göre uçak CG’si yaklaşık **9,7 mm, yani %3,1 MAC** öne kayar. Sloshing’in kontrol modlarıyla etkileşiminin yönü ve büyüklüğü bilinmiyor.  
    **Adım:** Tank başına yakıt durumlarını izleyin; normal boşalma, dengesizlik ve transfer arızası zarflarını oluşturun. Kısmi doluluk için bölme/sıvı hareketi modeli ve deney ekleyin. [NASA sloshing–kontrol etkileşimi](https://www.nas.nasa.gov/SC15/demos/demo12.html).

11. **P2 — Pitot fark basıncı doğrudan dinamik basınç sayılmış.**  
    **Yer:** [docs/09 §5.2, programlama kuralları](</C:/Users/Urungu/Desktop/Yeni klasör/docs/09_ucus_kontrol.md>).  
    **Sorun:** “q üzerinden, pitot farkı doğrudan” ifadesi M≈0,61’de geçerli değil.  
    **Etki:** 750 km/h, 300 m ISA’da **q≈25,83 kPa**, pitot toplam–statik farkı **≈28,36 kPa**: **%9,8 fark**. Sıkıştırılamaz hız dönüşümü yaklaşık **%4,8**, yani **36 km/h** fazla gösterir.  
    **Adım:** Statik basınçla sıkıştırılabilir Mach dönüşümü yapın; TAS/EAS/q tanımlarını ayırın. Kazanç programı ve hız sınırları aynı kalibre edilmiş hava verisini kullanmalı.

12. **P2 — ECU gaz sınırı, hava hızı sınırı sağlamaz.**  
    **Yer:** [params.py:17](</C:/Users/Urungu/Desktop/Yeni klasör/params.py:17>), [docs/09 §4.4](</C:/Users/Urungu/Desktop/Yeni klasör/docs/09_ucus_kontrol.md>).  
    **Sorun:** 800 km/h operasyon limiti ve arıza sonrası 550 km/h, gaz karşılığıyla ifade edilmiş. Dalma, kütle, sürükleme ve motor gecikmesi dahil hız koruması yok.  
    **Etki:** 750’den 800 km/h’e çıkmak için gereken kinetik enerji artışı, kayıpsız durumda yalnız **≈30,5 m irtifa kaybına** eşdeğer.  
    **Adım:** Ölçülen hava hızı, hızlanma, uçuş yolu ve motor tepki süresiyle aşırı hız/geri kazanım zarfı tanımlayın; sabit gaz yüzdesini hız garantisi olarak kullanmayın.

13. **P2 — Servo arızası yalnız nötrde kilitlenme olarak denenmiş.**  
    **Yer:** [flight_control.py:863](</C:/Users/Urungu/Desktop/Yeni klasör/aero/flight_control.py:863>).  
    **Sorun:** Rudder arızası t=0’da, başlangıç sapması sıfırken etkinleşiyor. Bu, manevra sırasında sapmış yüzeyin kilitlenmesini veya kontrolsüz son konuma gitmesini sınamıyor.  
    **Etki:** “Damper kaybı yapısal tehlike değil” sonucu bu özel senaryoya ait. Aynı çalışmada yalnız 1° kısa rudder darbesi yaklaşık **6° yan kayma tepesi** üretebiliyor.  
    **Adım:** Farklı sapma ve zamanlarda kilitlenme, tek elevator arızası, sensör sapması ve güç kaybını ekleyin; algılama ve moda geçiş süresini aynı simülasyonda doğrulayın.

14. **P2 — Noktasal kazanç doğrulaması, geçişlerin kararlılığını kanıtlamıyor.**  
    **Yer:** [docs/09 §5.2–§6](</C:/Users/Urungu/Desktop/Yeni klasör/docs/09_ucus_kontrol.md>), [flight_control.py:51](</C:/Users/Urungu/Desktop/Yeni klasör/aero/flight_control.py:51>).  
    **Sorun:** 12 noktadaki paylardan ara noktalarda da payların korunacağı sonucu çıkarılmış. Bu matematiksel olarak garanti değil. Ayrıca 350 km/h altı tasarlanmamış.  
    **Etki:** Yakıtla Kff birkaç kat değişiyor; yanlış yakıt tahmini, integral durumu ve mod geçişi büyük komut sıçraması yaratabilir. İlk uçuşun kalkış/inişi de doğrulanan aralığın dışında.  
    **Adım:** Sık hız–CG–atalet taraması, değişen kazançlarla zaman simülasyonu ve kesintisiz mod geçişi doğrulaması yapın; düşük hız kontrolünü F1’in ön koşulu yapın.

15. **P2 — Görev profili enerji ve yakıt hesabını birbirinden koparıyor.**  
    **Yer:** [mission.py:111](</C:/Users/Urungu/Desktop/Yeni klasör/performance/mission.py:111>).  
    **Sorun:** Bacak hızları ve gaz oranları bağımsız atanıyor; hızlanma/yavaşlama çözülmüyor.  
    **Etki:** Kodun kendi modeliyle 160 m/s, 15 kg, 8–10 g dönüşte sürükleme **≈145–155 N**; %35 itki **≈111 N**. Başlangıç yavaşlaması **≈2,3–3,0 m/s²**. Dolayısıyla 25 saniyelik sabit hızlı dönüş ve sonraki hızlanmanın yakıt bütçesi doğrulanmış değil.  
    **Adım:** Hız, irtifa, yük faktörü ve yakıtı birlikte entegre edin; ölçüm geçişine yeniden hızlanmayı ve iniş rezervini açıkça hesaplayın.

16. **P2 — Dolly bırakma koşulu, kalkış hesabının kendi kaldırmasıyla uyuşmuyor.**  
    **Yer:** [mission.py:38](</C:/Users/Urungu/Desktop/Yeni klasör/performance/mission.py:38>).  
    **Sorun:** `CL_g=0.35`, `CLmax_to=0.80`, bırakma hızı `1.2 Vs`; fakat mandal koşulu L/W≥1.  
    **Etki:** Hesaplanan bırakma anında **L/W=1,2²×0,35/0,80=0,63**. Aynı CL ile L=W için hız yaklaşık **%26 daha yüksek**, yaklaşık 159 km/h gerekir. Gerçek dolly açısındaki CL farklı olabilir; mevcut iki hesap birbirini doğrulamıyor.  
    **Adım:** Flap, dolly açısı ve elevator trimi için aynı aerodinamik veriyi kullanın; bırakmayı zaman/hız kestiriminden değil doğrulanmış kuvvet ve ayrılma koşulundan hesaplayın.

17. **P2 — Raporlanan azami tırmanma hızı fiziksel olarak olanaksız.**  
    **Yer:** [mission.py:86](</C:/Users/Urungu/Desktop/Yeni klasör/performance/mission.py:86>), `performance/out/performans_ozet.txt`.  
    **Sorun:** `(T−D)V/W` bütün fazla gücü kararlı tırmanmaya atıyor; yüksek T/W’de uçuş yolu ve ivmelenme denklemleri çözülmüyor.  
    **Etki:** Çıktı **490 km/h =136,1 m/s** toplam hızda **183 m/s düşey hız** veriyor. Düşey bileşen toplam hızdan büyük olamaz.  
    **Adım:** Kararlı tırmanmada `T−D=W sinγ`, `L=W cosγ`; ivmelenen durumda enerji ve hareket denklemlerini birlikte çözün. Yalnız sonucu V’ye kırpmak yeterli düzeltme değildir.

18. **P2 — Gaz değişiminin trim momenti kontrol modelinde yok. — Etki koşullu**  
    **Yer:** [flight_control.py:177](</C:/Users/Urungu/Desktop/Yeni klasör/aero/flight_control.py:177>), [flight_control.py:224](</C:/Users/Urungu/Desktop/Yeni klasör/aero/flight_control.py:224>).  
    **Sorun:** Trim yalnız aerodinamik momenti sıfırlıyor; motor ekseni ile CG arasındaki düşey uzaklıktan gelen itki momenti dahil değil.  
    **Etki:** Yaklaşık 14 mm uzaklık ve 300 N itki **4,2 N·m** moment üretir. Gaz kısma, motor durması ve düşük hız triminde bunun etkisi araştırılmamış. Takılı itki bileşkesinin gerçek doğrultusu ölçülmeli.  
    **Adım:** İtki kuvveti/momenti ve motor dinamiğini trim ile uçuş dinamiğine ekleyin; özellikle otomatik gaz kısma ve motor durması geçişlerini yeniden değerlendirin.

**Hedef değerlendirmesi:** Mevcut 299 N itki ve 212 N sürükleme tahmini yaklaşık **87 N, %41 pay** bırakıyor; bu, 750 km/h’i araştırmaya değer kılıyor. Ancak bu payın gerçekliği motor–alık–egzoz eşleşmesine bağlı. Uçuşa geçişi belirleyen kritik çalışma ise daha yüksek kanat frekansı elde etmekten önce **bütün uçağın aeroelastik modeli ile gerçek servo/sensör zincirini birlikte doğrulamak** olmalı.