# HIZ-750 inceleme paketi

Python 3.12 ve standart kutuphane ile calisir. Repo kokunden kullanin.

```powershell
python tools/inceleme_paketi_olustur.py --dry-run
python tools/inceleme_paketi_olustur.py
python tools/inceleme_paketi_olustur.py --hedef "D:/Inceleme/HIZ-750"
```

Varsayilan hedef `C:/Users/Urungu/Desktop/HIZ-750_Inceleme` klasorudur.
Incelemeye `00_BASLA_BURADAN/index.html` ile baslayin. HTML dizini tum
dosyalara baglanti ve PNG onizlemeleri sunar. Her klasorde `ICINDEKILER.md`
aciklamalari ve orijinal repo yollarini listeler.

## Klasorler

- `00_BASLA_BURADAN` ozet, basarim agaci ve HTML dizini
- `01_Raporlar` README, degisiklik gunlugu ve docs raporlari; `Incelemeler` alt klasoru `reviews/` raporlari
- `02_Tasarim_Parametreleri` params.py kopyasi ve AST sabit tablosu
- `03_CAD_Modeller` Montaj ve Parcalar alt klasorleri
- `04_Teknik_Cizimler` CAD DXF, PDF, SVG ve 3 gorunus/ic yerlesim PNG cizimleri
- `05_Aerodinamik`, `06_Yapi_ve_Flutter`, `07_Performans_ve_Kutle`, `08_Ucus_Kontrol`
- `09_Yuksek_Dogruluk_Dogrulama` CFD_SU2, FEM_CalculiX, Termal ve Benchmarklar
- `10_Kaynak_Kod` repo konumu ve calistirma notu
- `11_Loglar` logs klasorlerindeki tum dosyalar
- `99_Diger` eslesmeyen ciktilar, orijinal goreli yollariyla

## Esleme ve adlar

Scriptteki `REPORT_NAMES`, `MAPPING_RULES` ve `TRANSLATIONS` tablolari
kurallari tanimlar. Ucus kontrolunun `aero/out/fc_*` dosyalari ayrilir.
Bilinen modullerde adlara modul ve deney/iterasyon yolu eklenir. Sabit
terimler Turkce ASCII adlara donusturulur, deney kodlari korunur. Ornekler

- `fem/results/wing/fine_plot.png` → `FEM_Kanat_Kabuk_FEM_ince_ag_grafik.png`
- `validation/results/flat_plate_SA/study.md` → `Benchmark_Duz_Levha_SA_ag_calismasi.md`

Ad cakismalarina sayisal son ek eklenir. Cok uzun uretilen adlar kararlı
ozetle kisaltilir. Bilinmeyen ciktilarin yolları `99_Diger` altinda korunur.
Normal tarama png/svg/pdf/dxf/step/stp/stl/json/md/csv/txt uzantilarini kapsar.
inp/cfg/su2/msh/geo/dat/bdf cozum girdileri de alinir. Bilinen modullerde
bu girdiler `Ham_Girdiler` altina konur. `.git`, `__pycache__`, `.venv` ve `.claude`
taranmaz. `logs` ayri taranir. Aracin kendi README dosyasi pakete alinmaz.

Parametre dosyasi import edilmez. AST ile sabit atamalar, sabit sozlukler
ve `dict(anahtar=deger)` okunur. Hesaplanan ifadeler ve sabit olmayan
sozlukler atlanir. Kopya params.py butun kaynak degerleri icerir.

## Hedef guvenligi

Repo ile ayni, repo icinde veya repoyu kapsayan hedefler reddedilir.
Bos hedef kullanilabilir. Dolu hedef ancak bu scriptin ayni repo ve hedef
icin olusturdugu `.hiz750_paket` JSON isareti varsa yeniden kurulur.
Bu durumda onceki paketin tamami, sonradan eklenmis dosyalar dahil silinir.
Baglanti/junction iceren hedefler reddedilir. Kaynak baglantilari da
sessizce atlanmak yerine hata verir. Repo dosyalari yalniz okunur.

`--dry-run` hedefe yazmadan eslemeleri, uretilecek belgeleri ve kopya
dosyalarin sayisini/boyutunu bildirir. Normal calismadaki sayac uretilen
dizin belgeleri haric, kopyalanan kaynak dosyalarini kapsar.
Raporlar birebir kopyalandigi icin iclerindeki goreli baglantilar kaynak
repo duzenine ait olabilir. Paket ici gezinme icin HTML ve ICINDEKILER kullanin.
