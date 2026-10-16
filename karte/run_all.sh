#!/usr/bin/env bash
# Gesamte Kette: OSM + Höhenmodell + Luftbild -> Landmarken -> Karten-PDFs, Landmarkenliste, Feldcheck-Web-App.
# Aufruf aus beliebigem Ordner:  ./run_all.sh          (schnell, nutzt die abgelegten Analyse-Ergebnisse)
#                                FULL=1 ./run_all.sh   (rechnet auch Trichter-, Pfad- und Sandanalyse neu, dauert länger)
set -euo pipefail
cd "$(dirname "$0")"
FULL=${FULL:-0}
JOBS=${JOBS:-4}
step(){ echo; echo "=== $* ==="; }

step "OSM einlesen";            python3 scripts/load_osm.py data/map.osm data/osm.pkl
step "Höhenmodell zuschneiden"; python3 scripts/dgm_prep.py
step "Höhenlinien 2,5 m";       python3 scripts/contours.py
if [ "$FULL" = 1 ]; then
  step "Trichter aus Höhenmodell"; python3 scripts/craters2.py
  step "Trichter im Luftbild prüfen"; python3 scripts/crater_dop.py
  step "Manuelle Trichter";      python3 scripts/craters_manual.py
  step "Pfade im Luftbild prüfen"; python3 scripts/path_check.py
  step "Sandflächen";            python3 scripts/sand.py
fi
step "Landmarken aus OSM";      python3 scripts/landmarks_v0.py
step "Kuppen und Steilhänge";   python3 scripts/derived_landmarks.py
step "Ebenen zusammenführen";   python3 scripts/build_layers.py
step "Lupen über alle Blätter"; rm -f data/lupen.json; python3 -W ignore -c "import sys; sys.path.insert(0, 'scripts'); import render_map as R; R.build_lupen_registry()"
step "Blätter rendern"
mkdir -p out/maps out/svg
for m in color bw; do for sh in uebersicht detail_west detail_mitte detail_ost detail_sued; do echo "$sh $m"; done; done \
  | xargs -P "$JOBS" -n 2 bash -c 'set -o pipefail; python3 -W ignore scripts/render_map.py "$0" "$1" "out/maps/$0_$1.pdf" "out/maps/$0_$1.png" 200 "out/svg/$0_$1.svg" | tail -1'   # a failing sheet stops the run
step "PDFs zusammenfügen";      python3 scripts/merge_pdfs.py
step "Export für OL-Software";  python3 -W ignore scripts/export_ol.py
step "Feldcheck: Daten, Kacheln, Web-App"; APP_OUT="${APP_OUT:-$(cd .. && pwd)}" python3 -W ignore scripts/build_site.py --tiles
step "Landmarkenliste (Excel)"; python3 scripts/make_xlsx.py
echo; echo "Fertig. Karten: out/*.pdf · Liste: out/Wangerooge_West_Landmarken_v1.xlsx · OL-Export: out/ol/ · Web-App: Repo-Wurzel (GitHub Pages)"
