# Grup 2: Karar ekibinin nihai kararı (2026-11-08)

**Ekip ve bakış açıları:**
- Codex Astra: yapı ve aeroelastik.
- Codex Sol: süreç, risk ve CFD.
- Claude Sonnet: uçuş güvenliği ve pratiklik.

**Yöntem:** Tur 1'de her üye bağımsız karar verdi. Tur 2'de üyeler birbirlerinin dayandığı sayıları kaynak dosyalarda doğruladı ve ayrıştıkları noktalarda hüküm verdi. Aşağıdaki sentez ekip lideri Claude Opus'a ait; kararlar oybirliğiyle alındı.

**Belgeler:**
- Brief: [grup2_brief.md](grup2_brief.md)
- Tur 1: [Astra](grup2_tur1_codex_astra.md), [Sol](grup2_tur1_codex_sol.md), [Sonnet](grup2_tur1_claude_sonnet.md)
- Tur 2: [Astra](grup2_tur2_codex_astra.md), [Sol](grup2_tur2_codex_sol.md), [Sonnet](grup2_tur2_claude_sonnet.md)

## Kararlar

| # | Karar | Oy |
|---|---|---|
| K1 | İter5 değişikliklerinin **hepsi tutulur**. s41r043w1 bir *geçici tasarım tabanıdır*; tank ve sandviç kapanmadan imalat onayı verilmez. Kabuk p-k sonucu "tahmin" diye etiketlenir. GCI kuralı tutulur, formal mertebe (2) gerekçesi tamamlanır. İnceleme paketi yeniden üretilir. | 3/3 |
| K2 | **Kanat çalışma değeri 1267 km/h** olarak kalır. 1324 km/h ayrıca kabuk p-k tahmini olarak raporlanır. **Gereksinim 1080 km/h**, model payı hedefi 1350 km/h. Hiçbiri bütün uçağın flutter sınırı değildir. 316 Hz hedefi bırakılır. GVT eşiği (230 Hz) yeni modelle yeniden türetilir. | 3/3 |
| K3 | **Önce FEM.** İlk aday aileron servosunu öne almaktır (Ritz tahmini 1427/1403 km/h). Uç balansı (30 g yarım kanat başına, toplam 60 g; tahmin 1446/1424 km/h) yedek seçenektir. Hiçbiri henüz CAD'e işlenmez. | 3/3 |
| K4 | Tankın **yeterliliği kanıtlanmadı** (yetersiz olduğu da gösterilmedi). Kaburga aralığı 43 mm'de kalır. Önce kullanılabilir hacim (kaburga, dolum payı, kullanılamayan yakıt) ve dinamik görev yakıtı hesaplanır. Not: %6 rezerv 4 geçişli sorti içindir; standart 2 geçişli sortide rezerv ≈%31 (docs/05). | 3/3 |
| K5 | Uçuş öncesi engeller ve durumları:<br>• **Kuyruk/gövde bağlaşık flutter ve GVT:** en büyük engel.<br>• **Motor bölgesi termali:** 126,1 °C > 120 °C; koşullu senaryo, termokupl testi gerekli.<br>• **FC faz payı:** ≈41° bir kestirim (filtresiz kayıtlı değer 49,9°); HIL gerekli.<br>• **Kök sandviç kesme kıvrılması:** pay 1,2–1,5.<br>• **RAE Cp ölçütü:** kabul öncesinde sabitlenir. Dışlanacak küme 8 nokta; yalnız kabul sağlasın diye hiçbir nokta dışlanmaz. Bu, doğrulama zinciri için bir engeldir. | 3/3 |
| K6 | İter6'nın ilk beş işi aşağıda. Her işe sorumlu, giriş koşulu, kabul ölçütü ve kapanış kanıtı eklenir. | 3/3 |
| K7 | **Şu an birleştirilmez.** Entegrasyon kapanışından sonra, "uçuşa hazır değil" uyarısı taşıyan bir **araştırma sürümü** olarak birleştirilip v0.6.0 yayımlanabilir. **Son adım kullanıcının açık onayıdır.** | 3/3 |

## Görüş değiştirenler
- **Sonnet, K7:** "şimdi birleştirilebilir" görüşünden "kapanıştan sonra" görüşüne geçti. Gerekçe: CHANGELOG'da eski 1813 km/h ve STALE ifadeleri kalmıştı.
- **Sonnet, K4:** "yetersiz" yerine "kanıtlanmadı" dedi. Ayrıca önerdiği kanat ≥1240 km/h ve %15 rezerv eşiklerini **geri çekti**; kaynakları yoktu.
- **Sol, GCI:** p'nin 0,5'e sınırlanmasına itirazını daralttı. Sınırlama Oberkampf–Roy ve Phillips'teki GCI-OR yaklaşımına uyuyor. Sınırlanmamış p ve Fs=3 ile sonuç %2,11, sınırlanmış p ile %1,82.

## Çapraz sorguda bulunan yeni noktalar
1. **Tsai-Wu R 4,16 değeri kök bölgesi hariç.** Tam değerler:
   - kök dahil minimum 1,973;
   - indirgemeli kök dahil 1,073;
   - indirgemeli kök hariç 2,263.

   Kaynak: `fem/results/stiffening/wing_s41r043w1/fine.json:10-13`. Kökteki değer büyük olasılıkla ankastre sınır koşulunun yarattığı tekillikten geliyor; ama **kök bağlantısının ayrı bir tasarımı ve analizi gerekiyor** (iter6, iş 4).
2. `run_all.sh` FEM ve kabuk p-k zincirini çalıştırmıyor. Bu zincir `fem/run_wing_study.py` ve `fem/shell_flutter.py` ile ayrıca koşuluyor (CCX ile saatler sürüyor). Bu durum belgelendi.
3. GCI'nin "p formal mertebeye %10 yakın" dalı formal p yerine gözlenen p'yi kullanıyor. Düşük öncelikli bir yöntem uyumu konusu.
4. Kör noktalar:
   - 1080 km/h'nin kaynağı (V_D × 1,2 mi?) belgelenmeli.
   - Tankların boşalma sırasına göre CG ve flutter değişimi incelenmeli.
   - Yakıt yoğunluğunun sıcaklıkla değişimi hesaba katılmalı.
   - Aşırı hız sınırı kuyruk flutter'ına göre tanımlanmalı.

## İter6: ilk beş iş (öncelik sırasıyla)
1. **Kuyruk, gövde ve kumanda yüzeyleri için bağlaşık aeroservoelastik model ve serbest-serbest GVT planı.** Servo-FEM doğrulaması da burada; Astra'nın inceleme bulguları 1 ve 3.
2. **Gerçek FC zinciri:** filtre, gecikme, yüklü servo, hava verisi, aşırı hız ve arızalar; manevra + hamle yük zarfı; HIL. Bulgular 2, 4, 11–14 ve 18.
3. **Yakıt ve görev:** kullanılabilir hacim, transfer, tank bazında CG, sloshing, yeniden hızlanma yakıtı ve rezerv. Bulgular 7, 9, 10 ve 15.
4. **Termal koruma, kök sandviç kararlılığı ve kök bağlantısı.** Kök Tsai-Wu değeri de bu işte kapanacak. Bulgu 8.
5. **Takılı motor ve alık doğrulaması:** RAE orta/ince ağ koşuları sabitlenmiş Cp ölçütüyle; ardından profil/SST taraması ve 3B CFD. Bulgular 5 ve 6.

## Entegrasyon kapanış listesi (K7 ön koşulları)
Durumlar 2026-11-08 itibarıyladır.

- [x] 33 regresyon testi ve `check_artifacts` PASS (0e0de7f ve sonrası).
- [x] Benchmarklar güncel kodla yeniden koşuldu: düz levha, konsol, kupon, thermal_1d.
- [x] CHANGELOG, README, BASARIM_AGACI ve docs/10'daki eski ifadeler temizlendi (1813 km/h "kod hatası" diye korundu; "Python erişim engeli" ve "STALE bekleniyor" ifadeleri kaldırıldı).
- [x] Sürüm notunda uçuş öncesi engeller ve "uçuşa hazır değil" uyarısı yer alıyor.
- [x] Tsai-Wu kök notu dokümanlara eklendi.
- [x] İnceleme paketi yeniden üretildi.
- [x] `run_all.sh` tam zincir koşusu (2026-11-08, 9 dk, çıkış 0, JSON sayıları değişmedi; `logs/run_all_grup2.log`).
- [ ] **Kullanıcının açık onayı** (birleştirme ve v0.6.0 etiketi).
