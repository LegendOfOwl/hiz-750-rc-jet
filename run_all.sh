#!/usr/bin/env bash
# HIZ-750: tum analiz ve CAD zincirini sirayla yeniden calistirir.
# Kullanim: bash run_all.sh   (PY degiskeniyle python yolu degistirilebilir)
set -e
cd "$(dirname "$0")"
PY="${PY:-C:/Users/Urungu/.hz750/Scripts/python}"
export PYTHONIOENCODING=utf-8
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
    echo "=== $s"
    "$PY" "$s" > /dev/null
done
echo "tamam"
