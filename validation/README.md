# İter5 / v0.6 doğrulama paketi

**2. tur: araçlar host'ta Claude tarafından kuruldu; escalation ile Python/solver çalışıyor.** İlk turun sandbox engeli [tarihsel yoklamada](results/machine_probe.json) korunuyor. Konsol ve 1B termal üç ağda benchmark kabulü aldı; motor termal senaryoları çözüldü. CFD denemeleri henüz doğrulanmış sonuç değildir. [Kurulum kaydı](results/installation.json) ve gerçek seviye JSON'ları saklanır. Kurulumu Codex yapmadı.

`params.py` salt okunur girdidir. Yeni malzeme/ısı transferi varsayımları bu pakette tutulur. Eski zincir `bash run_all.sh` değişmedi; birkaç saat sürebilen doğrulama koşuları ayrı çağrılır.

## Host kurulumu (Windows 11)

[tools.lock.json](tools.lock.json) sürümleri sabitler: SU2 **8.2.0**, CalculiX Windows paketi **2.20**, gmsh **4.15.2**. İkinci turda bu araçlar host kurulum kaydı ve gerçek koşularla erişilebilir bulundu. SU2 8.2.0, 8.1.0'a göre SST düzeltmeleri içerdiğinden seçildi ([resmi sürüm notu](https://github.com/su2code/SU2/releases/tag/v8.2.0)). Python3.12.10; paket sürümleri her sonuç JSON'unda kaydedilir.

PowerShell, depo kökünde:

```powershell
$py = 'C:/Users/Urungu/.hz750/Scripts/python.exe'
& $py --version
./validation/install_tools.ps1 -Python $py -Destination C:/hz750tools
```

`install_tools.ps1` PATH, registry veya kalıcı execution policy ayarını değiştirmez. Script çalıştırma politikası engelliyorsa aşağıdaki indirme/kurma işlemlerini komut olarak uygulayın; kalıcı politika değişikliği gerekli değildir.

- SU2: sabit resmi [v8.2.0 release API](https://api.github.com/repos/su2code/SU2/releases/tags/v8.2.0) içindeki tek serial Windows x64 ZIP indirilir; MPI/AD arşivi seçilmez. Varlık adı web arayüzünde doğrulanamadığından bir dosya adı tahmin edilmedi. API tek paket seçemezse installer durur; [release sayfasından](https://github.com/su2code/SU2/releases/tag/v8.2.0) doğru arşivi alın. Çözülen **tam indirme URL'si + SHA256** `C:/hz750tools/installation.json` içine yazılır. `latest` kullanılmaz.
- CalculiX: [sabit resmi Windows arşivi](https://www.dhondt.de/calculix_2.20_4win.zip), `C:/hz750tools/CalculiX` altına açılır. Bu adres [PrePoMax resmi indirme sayfasında](https://prepomax.fs.um.si/downloads/) da veriliyor. DLL'leri executable yanında tutun; banner'daki gerçek ccx sürümünü ilk koşuda kaydedin. Kılavuz için [CalculiX](https://www.calculix.de/) ve [2.22 başvuru kılavuzu](https://www.dhondt.de/ccx_2.22.pdf); 2.20 ile kart uyumu benchmark ile sınanmalı.
- gmsh: `& $py -m pip install gmsh==4.15.2`. [Resmi Python paketi](https://pypi.org/project/gmsh/4.15.2/), [sabit Windows SDK](https://gmsh.info/bin/Windows/gmsh-4.15.2-Windows64-sdk.zip). Projenin mevcut bağımlılıklarını tekrar kurmak gerekmez.

İndirme byte'ları bu worktree'de doğrulanamadı; önceden doğrulanmış bir binary hash'i sunulmuyor. İlk host kurulum kaydını koruyun. Executable'ları bulup [tools.example.json](tools.example.json) dosyasını `tools.local.json` adıyla kopyalayın ve gerçek yolları girin. Alternatif: yalnız bu PowerShell oturumunda `$env:SU2_CFD='C:/.../SU2_CFD.exe'`, `$env:CCX='C:/.../ccx.exe'`, `$env:HZ750_WORK='C:/hz750run'`. PATH gerekmez.

```powershell
& $py -c "import gmsh, numpy, scipy, matplotlib, aerosandbox; print(gmsh.__version__)"
& $py -m unittest validation.test_validation -v
& $py -m compileall -q validation cfd fem thermal
# Bu oturumda mevcut Node ile çalışan veri/ağ/link denetimi (Python testinin yerine geçmez):
node validation/check_artifacts.cjs
```

## Önce benchmark

```powershell
& $py validation/fetch_reference.py --geometry
# validation/reference/rae2822.example.json dosyasından rae2822.local.json oluşturun.
# AGARD/NASA sayısal Cp, CL, CD ve deney belirsizliğini kaynakla doldurun.
& $py validation/run_case.py thermal_1d --study
& $py validation/run_case.py cantilever --study
& $py validation/run_case.py flat_plate --study --model SA
& $py validation/run_case.py rae2822 --study --model SA --reference validation/reference/rae2822.local.json
& $py validation/run_case.py flat_plate --study --model SST
& $py validation/run_case.py rae2822 --study --model SST --reference validation/reference/rae2822.local.json
```

`--study` kaba → orta → ince koşar. Tek seviye: `--level coarse|medium|fine`. Her case aynı CLI ile çalışır. RAE geometrisi UIUC'den gelir; **geometri deney verisi değildir**. Kaynak/koşul eşleştirmesi ve Cp digitizasyonu henüz yapılmadı. Sayısal bir referans sağlanmadan RAE kabul alamaz. ONERA M6 eklenmedi; ikinci CFD kontrolü düz levhadır. Kompozit CLT coupon benchmarkı henüz yok; kanat sonuçları bu yüzden ve malzeme varsayımları nedeniyle inceleme gerektirir.

| Vaka | Kaba / orta / ince | Tahmini süre (tek ağ/model) |
|---|---|---|
| `flat_plate` | 160/320/640 duvar aralığı + rafine BL/alan | 5–30 dk |
| `rae2822`, `airfoil` | üst/alt 128/256/512 aralık + rafine BL/alan | 10–90 dk |
| `cantilever` | 10×2 / 20×4 / 40×8 S8R | <2 dk |
| `thermal_1d` | 4 / 8 / 16 DC3D8 | <1 dk |
| `aircraft` | incelenmiş üç ağ; her biri ≤2M hücre | 1–6 saat |
| `inlet` | incelenmiş üç ağ; her biri ≤2M hücre | 1–4 saat |
| `wing` | taslak mapped S8R, 8/16/32 span aralığı; açılmış DOF tahmini ≤200k | 5–30 dk |
| `engine_thermal` | her katmanda 4 / 8 / 16 DC3D8 | <2 dk |

Süreler ölçülmüş benchmark değildir. İlk kaba koşunun `elapsed_s` ve bellek kullanımıyla bütçeyi güncelleyin. `--threads 4`, varsayılan `--iterations 6000`, `--timeout 7200` saniyedir. 3B için gerektiğinde `--timeout 21600`. Bütçe aşımı BLOCKED olur; kısmi alan tamamlanmış sonuç sayılmaz.

## HIZ-750 koşuları

```powershell
& $py validation/run_case.py airfoil --study --alpha 0 --mach .61 --model SA
& $py validation/run_case.py airfoil --study --alpha 1 --mach .61 --model SST
& $py validation/run_case.py airfoil --study --alpha 2 --mach .75 --model SST
# Mcrit aralığı için M=.61,.65,.70,.725,.75 ve alpha=0,1,2; SA/SST ayrı.
& $py validation/run_case.py aircraft --level coarse --alpha .086072746 --mesh C:/hz750run/aircraft/coarse.su2 --mesh-review C:/hz750run/aircraft/coarse.review.json
& $py validation/run_case.py inlet --level coarse --mesh C:/hz750run/inlet/coarse.su2 --mesh-review C:/hz750run/inlet/coarse.review.json
& $py validation/run_case.py wing --level coarse --prepare-only
# Üretilen taslak deck'i fiziksel olarak düzeltip inceleyin; sonra:
& $py validation/run_case.py wing --level coarse --deck C:/hz750run/wing/coarse.inp --mesh-review C:/hz750run/wing/coarse.review.json
& $py validation/run_case.py engine_thermal --study --motor-C 250 --felt-mm 2 --thermal-inputs thermal/scenarios.example.json
& $py validation/report.py
```

3B/kanat harici girdileri her seviyeye özgüdür: `--study` aynı mesh/deck'i üç farklı seviye diye etiketlemek için kullanılmaz. Üç ayrı komut sonrasında `& $py validation/study.py cfd/results/aircraft_SA_A0p0861` gibi doğru çıktı klasörüne collector çağırın. Ayrıntılar: [CFD](../cfd/README.md), [FEM](../fem/README.md), [termal](../thermal/README.md).

Benchmark kapısı aynı solver executable SHA256'si, aynı `params.py` ve runner kaynaklarıyla geçerli olmalıdır. Kurulum ayarı denemesi için `--diagnostic` kullanılabilir; bu sonuç benchmark kabulü alamaz. `--prepare-only` solver çağırmadan mesh/deck üretir. Kanat taslağı normal üretim çözümü olarak otomatik çalıştırılmaz.

## Çıktı sözleşmesi ve kabul

**Eskime (STALE) kuralı (iter5 v3):** `study.evaluate` bir kaydı, vakanın çalışma anında import ettiği kaynaklar değiştiyse eskimiş sayar: `validation/{__init__,common,convergence,run_case,study}.py` + vaka alanı (`cfd/`, `fem/`; termalde `thermal/` + `fem/cases.py`). Testler, rapor/indirme araçları ve başka alanın dosyaları kaydı eskitmez. Benchmarklar (rae2822, flat_plate, cantilever, coupon, thermal_1d) `params.py`'yi ve uçak tasarım dosyalarını okumadığından bunlara bağlanmaz; uygulama vakaları bağlanır. Üç ağ tamamlanmamış olsa bile eskimiş bir kayıt STALE olarak gösterilir.

`<alan>/results/<case_id>/<level>.json`: durum, metrikler, süre, kaynak/params/executable hash'leri, paket sürümleri ve ham çalışma klasörü. Küçük deck/config, yüzey örnekleri ve PNG grafik kopyalanır. BLOCKED durumunda sayısız bir SVG durum kartı yazılır. Mesh'ler/solver alanları kısa `C:/hz750run/...` altında kalır; `.gitignore` büyük `.msh/.su2/.frd/.vtu/restart` dosyalarını dışlar. Küçük bir gerçek giriş ağı [thermal_1d_coarse.msh](meshes/thermal_1d_coarse.msh) olarak saklandı; bu bir çözüm değildir.

`study.json/.md`: üç seviye, Richardson limiti, gözlenen mertebe, mutlak/bağıl GCI ve varsa referans hatası. `report.py` mevcut yarı-ampirik dosyaları yeni çıktılarla yan yana yazar; tasarım kabulünü otomatik vermez. Doküman 10'daki sabit tablolar host sonuçları incelendikten sonra güncellenmeli.

- `BLOCKED`: araç/girdi/ön benchmark eksik veya süre sınırı.
- `FAILED`: program/solver hata verdi; ham log/exception inceleyin.
- `PREPARED`: yalnız mesh/deck üretildi.
- `UNCONVERGED`: residual/kuvvet/y+/enerji dengesi şartı sağlanmadı.
- `COMPUTED`: sayısal seviye kontrolü sağlandı; fiziksel doğrulama iddiası değildir.
- `REVIEW_REQUIRED` / `DIAGNOSTIC`: nicel sonuç inceleme/varsayımlarla koşulludur.
- `BENCHMARK_ACCEPTED`: üç seviyeli çalışma ve tanımlı referans eşikleri sağlandı; uçuş/tasarım kabulü değildir.

GCI: `Fs=1.25`, `h∝N^(-1/d)`, her oran ≥1.3, eşit olmayan oranlar destekli. CFD vakalarında (formal mertebe 2) gözlenen p formal değerden %10'dan fazla saparsa Roache/Roy önerisiyle muhafazakâr tahmin kullanılır: `p_kullanılan=min(max(0.5,p),2)`, `Fs=3` (iter5 v3; düz levhada p=.434 olduğundan GCI %0.88 yerine ≈%1.8). Tüm duvar/alan boyutları birlikte rafine edilmeli. Şok konumu ve mod geçişi asimptotik varsayımı bozabilir. Sıfır farkta `EXACT_OR_ROUNDOFF`, salınımda `OSCILLATORY`; zorla p=2 atanmaz. 1B sabit-k iletim + taşınım çözümü lineerdir ve DC3D8 bunu tam temsil edebilir: üç ağda hata yuvarlama düzeyindeyse GCI sayısı tanımsız kalması doğrudur.

Ön kabul eşikleri: konsol sehim/f1 %2; termal %0.1 (mutlak K ve akı hatası da raporlanır); RAE CL %5, CD %15, Cp RMSE .08; düz levha Cf korelasyon farkı %15; GCI %5. Bunlar mevzuat/sertifikasyon sınırları değildir. Deney belirsizliği ve model formu ayrıca değerlendirilir. CLI kodları: 0 koşu tamamlandı, 1 FAILED/UNCONVERGED, 2 BLOCKED; çalışma kabulünü ayrıca `study.json.status` üzerinden okuyun.

## Bu worktree'de uygulanan kontroller

[checks.json](results/checks.json) komut ve sonuçları kaydeder. İkinci turda escalation ile Python unittest ve compileall çalıştı; termal/konsol çözüldü. İlk turdaki çalıştırılamayan test kayıtları tarihsel engeldir. Node/PowerShell denetimleri nümerik doğruluk testlerinin yerine geçmez. Konsol kartlarında `.10e` biçimi CalculiX'in 20 karakterlik alan sınırını aşmaz. RAE okuyucusu UIUC Lednicer sırasını Selig sırasına çevirir. SU2 yardımcı Buffet=NaN sütunu kabul ölçütüne sokulmaz; istenen fiziksel alanlarda NaN/Inf hâlâ engeldir.
