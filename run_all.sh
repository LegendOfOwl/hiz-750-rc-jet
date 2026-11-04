#!/usr/bin/env bash
# HIZ-750: tum analiz ve CAD zincirini sirayla yeniden calistirir.
# Kullanim: bash run_all.sh
#   PY=/yol/python bash run_all.sh   -> belirli bir yorumlayici
# PY verilmezse sirayla: ./.venv, ~/.hz750 (kisa yollu Windows venv'i), sonra PATH'teki python.
# Her scriptin ciktisi logs/<script>.log dosyasina yazilir.
set -e
cd "$(dirname "$0")"
if [ -z "${PY:-}" ]; then
    for cand in .venv/Scripts/python .venv/bin/python "$HOME/.hz750/Scripts/python" "$HOME/.hz750/bin/python"; do
        if [ -x "$cand" ] || [ -x "$cand.exe" ]; then PY="$cand"; break; fi
    done
fi
PY="${PY:-python}"
export PYTHONIOENCODING=utf-8
mkdir -p logs
for s in \
    sizing.py \
    cad/build_cad.py \
    cad/mass_properties.py \
    performance/mission.py \
    performance/mass_report.py \
    performance/inlet_analysis.py \
    aero/aero_analysis.py \
    aero/flight_control.py \
    structures/structures.py \
    structures/fe_modal.py
do
    log="logs/$(echo "$s" | tr '/' '_' | sed 's/\.py$//').log"
    echo "=== $s  ->  $log"
    if ! "$PY" "$s" > "$log" 2>&1; then
        echo "HATA: $s basarisiz, son satirlar:"; tail -20 "$log"; exit 1
    fi
done
echo "tamam"
