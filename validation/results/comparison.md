# İter5 karşılaştırma (otomatik)

Tarihsel baseline v0.5.0 Git içeriklerinden okunur. Güncel analiz dosyalarının SHA256 değerleri comparison.json içindeki current alanında ayrıca listelenir. Solver çalışmaları aşağıda önceki rapor üretiminin durumlarıyla korunmuştur.

| Büyüklük | v0.5.0 modeli | İter5 |
|---|---|---|
| D @750 [N] | 154.353 / yaklaşık 210 | bekliyor |
| η_r | 0.970955 | bekliyor |
| DC60 | eski modelde yok | bekliyor |
| 1B adayı / 1T adayı [Hz], tank dolu | 27.459 / 305.677 | bekliyor / bekliyor |
| Flutter [km/h], tank dolu | 1307.484 | bekliyor; yeni modal aeroelastik çözüm gerekli |
| Kabuk iç yüzeyi [°C] | ölçülmedi | 58.7665 (engine_thermal_T250_F0_1ed7ca8299, COMPUTED); 149.815 (engine_thermal_T250_F0_679b6a3875, COMPUTED); 61.7091 (engine_thermal_T250_F0_803b2f042b, COMPUTED); 44.3923 (engine_thermal_T250_F2_1ed7ca8299, COMPUTED); 126.1 (engine_thermal_T250_F2_679b6a3875, COMPUTED); 46.6741 (engine_thermal_T250_F2_803b2f042b, COMPUTED) |

## Solver çalışmaları

- [validation\results\cantilever](cantilever/study.md): BENCHMARK_ACCEPTED
- [validation\results\flat_plate_SA](flat_plate_SA/study.md): PENDING
- [validation\results\rae2822_SA](rae2822_SA/study.md): PENDING
- [validation\results\thermal_1d](thermal_1d/study.md): BENCHMARK_ACCEPTED
- [cfd\results\airfoil_SA_M0p6100_A0p0000](../../cfd/results/airfoil_SA_M0p6100_A0p0000/study.md): PENDING
- [fem\results\wing](../../fem/results/wing/study.md): PENDING
- [thermal\results\engine_thermal_T250_F0_1ed7ca8299](../../thermal/results/engine_thermal_T250_F0_1ed7ca8299/study.md): REVIEW_REQUIRED
- [thermal\results\engine_thermal_T250_F0_679b6a3875](../../thermal/results/engine_thermal_T250_F0_679b6a3875/study.md): REVIEW_REQUIRED
- [thermal\results\engine_thermal_T250_F0_803b2f042b](../../thermal/results/engine_thermal_T250_F0_803b2f042b/study.md): REVIEW_REQUIRED
- [thermal\results\engine_thermal_T250_F2_1ed7ca8299](../../thermal/results/engine_thermal_T250_F2_1ed7ca8299/study.md): REVIEW_REQUIRED
- [thermal\results\engine_thermal_T250_F2_679b6a3875](../../thermal/results/engine_thermal_T250_F2_679b6a3875/study.md): REVIEW_REQUIRED
- [thermal\results\engine_thermal_T250_F2_803b2f042b](../../thermal/results/engine_thermal_T250_F2_803b2f042b/study.md): REVIEW_REQUIRED
