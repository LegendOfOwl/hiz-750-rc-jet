# Grup 2 karar ekibi brief'i

**Proje:** HIZ-750, türbinli RC jet İHA, hedef 750 km/h. Dal `iter5/yuksek-dogruluk`, [PR #2](https://github.com/LegendOfOwl/hiz-750-rc-jet/pull/2) açık, birleştirilmedi.

**Önce oku:**
- `BASARIM_AGACI.md`
- `reviews/grup1_zincir_dokuman.md`
- `reviews/grup1_yapi_fem.md`
- `reviews/grup1_cfd_dogrulama.md`
- `reviews/grup1_codex_disiplinlerarasi.md`
- `CHANGELOG.md` [0.6.0]

Gerekirse şunlara da bak: `docs/04_yapi_flutter.md` §15, `docs/10_yuksek_dogruluk_dogrulama.md`, `params.py`.

**Rolün:** karar verici. Görevin düzeltme yapmak değil, karar vermek. Her kararı gerekçesiyle ver; kanıt yetersizse bunu açıkça söyle. Sayı uydurma; dayandığın her sayının dosyasını göster.

## Karar verilecek sorular
Her soru için: **KARAR / gerekçe / risk / güven (düşük-orta-yüksek)**.

- **K1. PR #2'deki iter5 değişiklikleri faydalı mı?** Her değişiklik için tut / geri al / değiştir de: kanat rijitleştirme s41r043w1 (+0.285 kg), fe_modal düzeltmesi, kabuk p-k, GCI kuralı, STALE kapsamı, sizing'in params'a bağlanması, inceleme paketi.
- **K2. Flutter tasarım değeri:** 1267 km/h (f_1T ile ölçekli, ihtiyatlı) mi kullanılsın, 1324 km/h (kabuk mod şekilleriyle p-k) mı? Gereksinim 1080 km/h; 1350 km/h hedefi gerekli mi?
- **K3. Kütle ve atalet dengesi:** aileron servosunu öne almak (≈1427 km/h) ya da uca 30 g balans koymak (≈1446 km/h). Yapılsın mı, yoksa önce FEM ile doğrulansın mı?
- **K4. Tank hacmi ve kaburga aralığı:** 43 mm kaburgayla yakıt hacmi yaklaşık 5.0 L oldu; görev için yeterli mi? Kaburga aralığı mı değişsin, tank mı?
- **K5. Diğer açık riskler:** termal (126 °C, kriter <120 °C), FC filtresi faz payı (41°, hedef 45°), kuyruk flutter'ı (HT 310–360 Hz, VT 250–320 Hz bilinmiyor), sandviç kesme kıvrılması payı (1.2–1.5), RAE Cp RMSE ölçütü (ön kenar noktasının dışlanması). Her biri için:
  - şimdi mi, sonra mı;
  - nasıl çözülsün;
  - **uçuş öncesi engel** mi.
- **K6. Plan ve yol haritası yeterli mi?** Eksik adımları (Codex Astra'nın 18 bulgusu dahil) önceliklendir. Sonraki iterasyonun (iter6) ilk 5 işini belirle.
- **K7. PR #2 birleştirmeye hazır mı? v0.6.0 yayımlanmalı mı?** Ön koşulların neler?

## Çıktı
`## K1 ... ## K7` başlıklarıyla en fazla yaklaşık 900 kelime. En sona tek satırlık bir genel hüküm yaz.
