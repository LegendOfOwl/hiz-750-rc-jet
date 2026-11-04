# Değişiklik Günlüğü

Sürümleme: `0.MAJOR_ITERASYON.PATCH`. 1.0.0 sürümü, prototip uçuş testinden sonra verilecek.

## [0.4.0] - 2026-11-04 · İterasyon 3
### Değişti
- Kanat alçak konuma alındı (z −0,035 → −0,080 m), dihedral −1° → +2° (DATCOM ile gövde-kanat girişim düzeltmesi yapıldı).
- Hava alığı yarı gömülü yapıldı (x 0,85 m, dudak merkezi z 88 mm), önüne 7° rampa eklendi. Kanal 330 mm'ye uzatıldı; S-kanal ofset/uzunluk oranı 0,50'den 0,267'ye düştü.
- Kanat tek parça oldu: kutu gövdenin içinden geçiyor, 4× M6 12.9 cıvata ve çerçevelerle (x 1,006 / 1,156) bağlanıyor.
- Kanat kabuğunun kat planı yüz başına 3/1 oldu (kiriş önü / arkası). Kesit ağırlık merkezi 0,45c'ye geldi; flutter hızı 1465 km/h.
- Flap tek yarıklıya çevrildi (cf 0,25, iniş açısı 35°). Elevator cf 0,28 → 0,22.
- Kızak uzatıldı (x 1,45 m'ye kadar), kuyruk tamponu ve kızak çerçeveleri eklendi. Kuyruk çarpma açısı 12,4°.
- Yakıt tankları yeniden düzenlendi: gövde 3,63 L, kanat kutusu ortası 0,27 L, kanat kökleri 2 × 0,715 L. Toplam 5,33 L iç hacim, karın tankı kaldırıldı. Yakıt CG'si 0,955 m.
- Dolly kalkış açısı α 3°, elevator trimi −4°.
### Düzeltildi
- İterasyon 2'nin flutter değerleri (1383 ve 1356 km/h) kesit ağırlık merkezi 0,42c varsayımıyla hesaplanmıştı. Ağırlık merkezi kalem kalem hesaplandığında 0,52c çıktı; buna göre gerçek değer ~1086 km/h, yani pay neredeyse sıfırdı.
- CAD'de gövde spline'ındaki örnekleme hatası giderildi (burunda x 400–800 mm arası).
### Eklendi
- Kütle kalemleri: kanat bağlantısı (0,15 kg), motor bölgesi ısı keçesi ve G10 plaka (0,05 kg).
- Rapor: [docs/08_sonuclar_cikarimlar.md](docs/08_sonuclar_cikarimlar.md), `requirements.txt`, `.gitignore`.

## [0.3.0] · İterasyon 2
### Değişti
- Kanat öne alındı (kök hücum kenarı 1,00 → 0,92 m). Arka kiriş 0,62c → 0,55c, motor x 1,25 → 1,18 m. Statik marj %40'tan %12–30 bandına indi.
- Geri çekilir iniş takımı kaldırıldı; yerine bırakılan kalkış arabası (dolly) ve gövde altı kızak geldi. MTOW 18,3 → 16,8 kg.
- Dikey kuyruk 0,050 → 0,060 m². Yatay kuyruk iki yarıya bölündü, birleştirici yoke egzozun üstünden geçiyor.
- Negatif yük limiti −6 → −8 g.
- Yakıt gövde, karın ve kanat kökü tanklarına bölündü; toplam 5,2 L.
### Düzeltildi
- İterasyon 1'deki CAD çakışmalarının hepsi giderildi: motor ↔ kiriş, kanal ↔ kanat kutusu, yatay kuyruk ↔ egzoz.

## [0.2.0] · İterasyon 1 (ilk tam paket)
### Eklendi
- Tek veri kaynağı olarak `params.py`.
- Paralel olarak hazırlanan: CadQuery ile parametrik CAD (`cad/`), AeroSandbox ile aerodinamik ve stabilite analizi (`aero/`), yapı/flutter/servo analizi (`structures/`).
- Görev profili, kütle/CG ve elektrik bütçesi (`performance/`). Dokümanlar 02–07.
### Bulunan sorunlar
- Statik marj %40'tı. Yakıt hacmi yetersizdi. Beş geometri çakışması vardı. Ana teker kanada sığmıyordu.
- Bunların hepsi iterasyon 2'de çözüldü.

## [0.1.0] · Kavramsal boyutlandırma
### Eklendi
- `sizing.py`: ISA atmosfer, bileşen bazlı sürükleme, Korn denklemiyle dalga sürüklemesi, türbin itki modeli ve Vmax hesabı. Ayrıca motor ve kanat alanı için trade study, duyarlılık analizi.
- Motor seçimi: P300-PRO hedefi ancak sınırda karşılıyor (754 km/h), bu yüzden P400-PRO seçildi.
