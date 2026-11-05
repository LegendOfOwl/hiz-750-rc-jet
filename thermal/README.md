# Termal model ve koşu

İkinci turda benchmark üç ağda analitik çözümle eşleşti (Tsoğuk357.15K, q1600W/m²). Altı motor250°C senaryosu da üç ağda çözüldü. 5.97mm açıklıkta h_bypass15/h_dış100 için kabuk61.71°C (keçesiz) /46.67°C (2mm); bypass0/h_dış10 yer senaryosunda149.82°C /126.10°C bulundu. Sonuçlar ölçülmemiş katsayılara bağlıdır; Tg150°C karşısında keçesiz yer senaryosunda güvenilir pay yoktur. Ayrıntı ve nominal8.5mm sonuçları doküman10 §10.6'da.

`thermal_1d`: 100 mm katı, k=10 W/(m K), sıcak yüz 100°C; soğuk yüz h=25 W/(m² K), ortam 20°C; diğer yüzler yalıtılmış. Analitik akı `(100−20)/(.1/10+1/25)`, sıcaklık lineerdir. Üç ağ 4/8/16 DC3D8. Tam lineer temsilde GCI'nin tanımsız kalması beklenir; tablo bunu EXACT_OR_ROUNDOFF olarak gösterir. Bu sayılar problem tanımıdır, çalıştırılmış solver sonucu değildir.

```powershell
& $py validation/run_case.py thermal_1d --study
& $py validation/run_case.py engine_thermal --study --motor-C 250 --felt-mm 2 --thermal-inputs thermal/scenarios.example.json
```

Motor uygulaması, 10×10 mm yerel yama için **1B kararlı katman modeli**: motor → hava açıklığı/ışınım → keçe → karbon kabuk → dış taşınım/ışınım. 3B motor bölmesi/CHT analizi değildir. Hava aralığı k_air/g ile iletim, bypass ise ayrıca h_bypass taşınımıdır; verilen iki katkı aynı iç yüzeye eşdeğer sink/h olarak yazılır. Radyasyon CalculiX *RADIATE (Kelvin, sigma açık) ile çözülür. Isı dengesi ve aynı sınır koşullarının bağımsız skaler çözümüyle karşılaştırılır. Yan yüzler yalıtılmıştır; metal bağlantı ısı köprüleri, egzoz görüş faktörü ve transiyent ısı birikimi yoktur.

[scenarios.example.json](scenarios.example.json) **ölçülmemiş örnek varsayımlar** içerir: açıklık8.5 mm, kabuk1.5 mm, k_shell=.5, k_felt=.06 W/(m K), h_bypass=15, h_external=100 W/(m² K), bypass50°C, dış ortam20°C, etkin iç emissivite .7. Bunlar CFD/üretici ölçümü değildir ve konfigürasyon seçilmeden varsayılan sonuç üretilmez.

Önerilen tarama: motor150/200/250°C; keçe0/1/2/3 mm; h_bypass0/15/50; dış taşınım10 (yer çalıştırması)/100 (uçuş); emissivite.1/.7/.9; açıklık8.5/**5.97** mm. Ayrı input JSON'ları kullanın; dosya SHA256'si senaryo kimliğine girer. Keçe kalan açıklıktan düşülür; yalıtımın bypass debisini azaltması bu 1B modelde hesaplanmaz. Keçe kalınlığını artırırken h_bypass sabit tutmak iyimser olabilir.

`cad_report.json` minimum radyal açıklığı **5.97 mm**, ön açıklığı6.8 mm veriyor; 8.5 mm gerçek iç açıklık olarak doğrulanmış değil. Önce CAD kesitinde 1.5 mm kabuk kalınlığı ve motor zarfını kontrol edin. Kalın keçe için fiziken kalan hava aralığı zorunlu.

Kabuk iç sıcaklığı sonuçları gelmeden bir keçe kalınlığı önerilmiyor. Tg≥150°C, 150°C'de sürekli emniyetli çalışma demek değildir: üreticinin hot/wet Tg, sürekli servis sıcaklığı ve sıcaklıkta basma/kayma izinleri gerekir. Termokuplla yer çalışma/stop sonrası heat soak ölçümüyle h/k/emissivite aralığı daraltılmalı. Kaba analitik/network sonuçlar da bu ölçümün yerini tutmaz.
