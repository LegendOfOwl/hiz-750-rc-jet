# Grup 2 Tur 1: Claude Sonnet (uçuş güvenliği / pratiklik bakışı)

## K1. PR #2 değişiklikleri faydalı mı?
**KARAR: hepsi tutulsun; iki madde değiştirilerek.**

| Değişiklik | Karar | Gerekçe / koşul |
|---|---|---|
| Kanat s41r043w1 (+0,285 kg) | TUT | Kabuk p-k 1326/1324 km/h, Tsai-Wu R 4,16. Kuyruk ve sandviç açık olduğu için "son tasarım" sayılmaz. |
| fe_modal düzeltmesi | TUT | Gerçek kod hatası düzeltildi (1813 → 1452 km/h). |
| Kabuk p-k | TUT | Şerit teorisi; uç kaybı ve kontrol yüzeyi yok. "Tahmin" diye etiketlensin. |
| GCI kuralı | TUT | Fs=3, düz levha GCI %1,82. Daha temkinli. |
| STALE daraltma | TUT (koşullu) | Gerçek bağımlılığa dayandığı tek seferlik kontrol edilsin. |
| Sizing → params | TUT | MTOW 17,44 kg; tek veri kaynağı ilkesine uygun. |
| İnceleme paketi | DEĞİŞTİR | Betik repoda kalsın; masaüstü çıktısı repoya girmesin ve güncel sayılarla yeniden üretilsin. |

Güven: orta-yüksek.

## K2. Flutter tasarım değeri
**KARAR: tasarım değeri 1267 km/h kalsın.** 1324 km/h bilgi değeri olarak raporlansın.
- Gereksinim 1080 km/h. 1350 km/h tam uçak için hedeftir, kanat için zorunlu değil.
- Önerilen kanat alt sınırı ≈1240 km/h (1,15 × 1080). Bu bir öneri, projede kayıtlı bir kural değil.
- Gerekçe: kuyruk ve gövde modelde yok. Ölçekleme ihtiyatlı çıkıyor.

Güven: orta.

## K3. Servo / balans
**KARAR: önce FEM ile doğrula, CAD'e henüz işleme.**
- Servo öne alma (A seçeneği) FEM ile çözülsün. Bunun için `wing_shell.py`'ye servo konumu parametresi eklensin.
- Balans kütlesi yedek plan olarak kalsın.
- Engel: profil ≈15 mm kalınlıkta, ince servo gerekiyor; ön kenar tankıyla çakışma olabilir.

Güven: orta.

## K4. Tank / kaburga
**KARAR: kaburga aralığı 43 mm'de kalsın, tank hacmi yeniden hesaplansın.**
- Görev yakıtı 4,69 L, tank ≈5,0 L, rezerv %5–6. Dönüş itki açığı ve yeniden hızlanma yakıtı hesaba katılmadığı için bu rezerv iyimser.
- Öneriler:
  1. `tank_volume()` kaburga ve delik payıyla yeniden yazılsın.
  2. Hacim yetmezse gövde ya da orta tank uzatılsın, CG etkisiyle birlikte.
- Türbin için önerilen rezerv en az %15 (öneri).

## K5. Riskler

| Risk | Ne zaman | Uçuş öncesi engel mi? |
|---|---|---|
| Termal 126 °C | Şimdi | EVET; yer termokupl testi yapılmalı |
| FC faz payı 41° | Şimdi | EVET; HIL testi yapılmalı |
| Kuyruk flutter | Şimdi | EVET; en büyük engel |
| Sandviç kıvrılma | Şimdi | EVET |
| RAE Cp RMSE | Sonra | Hayır |

RAE ölçütü baştan tanımlanmalı; ön kenar noktası sonradan dışlanmasın.

## K6. iter6 ilk 5 iş
1. Kuyruk + gövde FE modal analizi ve bağlaşık flutter; serbest-serbest GVT planı.
2. Tank hacmi, yakıt CG'si ve CG zarfı.
3. Filtreli FC payları; manevra + hamle yük zarfı.
4. Termal çözüm; sandviç alt modeli.
5. Servo A seçeneğinin FEM doğrulaması; takılı motor ve alık modeli planı.

CFD işleri (RAE/SST/3B) bunların altında kalsın.

## K7. PR / v0.6.0
**KARAR: birleştirilebilir.** v0.6.0, "uçuşa hazır değil" uyarısıyla yayımlansın. Kullanıcının açık onayı gerekli.

Ön koşullar:
- `run_all.sh` ve testler son commit'te koşulmuş olmalı.
- BASARIM_AGACI'ndaki "Python erişimi yok" ifadeleri güncellensin.
- CHANGELOG'da "tam uçak flutter analizi yok" uyarısı yer alsın.
- Eski 1813 km/h sayısı dokümanlarda kalmasın.
- Sürüm notunda uçuş öncesi engeller listelensin.

**Genel hüküm:** iter5 paketi birleştirmeye değer. Kuyruk flutter'ı, termal, FC faz payı ve tank rezervi kapanmadan HIZ-750 uçuşa hazır sayılmaz.
