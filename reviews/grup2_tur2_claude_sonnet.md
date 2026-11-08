# Grup 2 Tur 2: Claude Sonnet (çapraz sorgu)

## Görüş değişiklikleri
- **K7:** Codex üyelerine katılıyorum; kısa bir entegrasyon kapanışından sonra birleştirilsin. Gerekçe: `CHANGELOG.md` dosyasında eski "1813 km/h açık iş" ve "Python erişim engeli / STALE bekleniyor" ifadeleri hâlâ duruyordu.
- **K4:** "Yetersiz" yerine "yeterliliği kanıtlanmadı" diyorum. `params.py:134`'e göre 4,0 kg / 0,80 kg/L = 5,0 L, yani bu değer yakıtın nominal hacmi. Kaburgalar, dolum payı ve kullanılamayan yakıt düşülünce kullanılabilir hacim daha az kalır. Önceki "%5–6 rezerv" hesabım iyimserdi.

## Geri çekilen eşikler
- **Kanat için ≥1240 km/h:** Geri çekiyorum. 1080 km/h, 1,44 × 750 km/h'dir; içinde zaten pay olabilir, yani payı iki kez sayma riski var. FAR/CS-23 maddesini doğrulayamadım.
- **%15 yakıt rezervi:** Yalnızca geçici bir planlama hedefi. Gerçek rezerv dinamik görev profilinden türetilmeli.

## Kör noktalar
- 1080 km/h'nin kaynağı ne: V_D mi, yoksa pay dahil bir değer mi? K2 buna bağlı.
- Tankların boşalma sırasına göre CG ve flutter değişir. "Dolu" ve "boş" yalnızca iki uç durum.
- Yakıt yoğunluğunun sıcaklıkla değişimi ve buharlaşma, yani yakıt ile termal arasındaki etkileşim.
- Aşırı hız sınırının kuyruk flutter'ına göre tanımlanması.

## Nihai oy
| Karar | Oy |
|---|---|
| K1 | Hepsi tutulsun; inceleme paketi yeniden üretilsin. |
| K2 | Kanat çalışma değeri 1267 km/h; kabuk p-k tahmini 1324 km/h; gereksinim 1080 km/h; iç hedef 1350 km/h. |
| K3 | Önce FEM; ilk aday servoyu öne almak. Uç balansı yedek seçenek. |
| K4 | Yeterliliği kanıtlanmadı. Kaburga aralığı 43 mm kalsın. |
| K5 | Termal, FC, kuyruk ve sandviç uçuş engeli. RAE ölçütü sabitlensin, ön kenar noktası dışlanmasın. |
| K6 | Önce kuyruk–gövde, FC, yakıt, termal/sandviç ve servo FEM; ardından CFD. |
| K7 | Entegrasyon kapanışından sonra araştırma sürümü olarak birleştirilsin. Kullanıcının onayı gerekli. |
