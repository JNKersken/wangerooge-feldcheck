# Kartenkette Wangerooge West

Alles, was die OL-Karte, die Landmarkenliste und die Feldcheck-Web-App erzeugt: Rohdaten, Skripte, Schriften, Vorlagen und die aktuellen Ergebnisse.

## Schnellstart

```bash
cd karte
python3 -m pip install -r requirements.txt
./run_all.sh            # ca. 2–3 Minuten
FULL=1 ./run_all.sh     # rechnet zusätzlich Trichter-, Pfad- und Sandanalyse neu
```

Ergebnisse:

| Datei | Inhalt |
|---|---|
| `out/Wangerooge_West_OL_v1_Farbe.pdf` / `_SW.pdf` | Übersicht 1:15.000 + Blätter 1–4 (1:5.000 / 1:7.500) mit Lupen |
| `out/Wangerooge_West_Landmarken_v1.xlsx` | Landmarkenliste mit Status, Quellen, Koordinaten |
| Repo-Wurzel (`index.html`, `t*.png`, `data.json` …) | Feldcheck-Web-App für GitHub Pages (GPS, offline) |
| Repo-Wurzel `karten/*.svg`, `karten/layers.json` | Blätter als Ebenen-SVG für „Karte als PDF“ in der App |

## Karte als PDF in der App

`render_map.py` schreibt neben PDF/PNG ein SVG, in dem jedes Kartenelement einer Ebene zugeordnet ist (`id="L-<ebene>-<n>"`, Liste in `render_map.LAYERS`).
Die App lädt diese SVGs, blendet abgewählte Ebenen aus und baut das PDF direkt im Browser (jsPDF + svg2pdf.js, `web/lib/`).
Neue Ebene: Schlüssel in `LAYERS` ergänzen und die Zeichenbefehle in `with tag(S, '<schlüssel>'):` einschließen.

`run_all.sh` schreibt die Web-App direkt in die Repo-Wurzel. Danach committen und pushen, GitHub Pages veröffentlicht automatisch.

## Feldcheck-Briefkasten (Einsendungen aus der App)

1. Helfer tippen in der App „Mehr → Briefkasten → Senden“. Die App legt eine JSON-Datei in den Zweig `eingang`
   (`karte/data/feldcheck/eingang/<zeit>_<name>_<zufall>.json`) und meldet das per `repository_dispatch`.
   Dafür braucht jedes Handy einen eigenen Fine-grained-Token (nur dieses Repo, „Contents: Read and write“);
   der Einladungslink `…/#key=<token>&name=<name>` richtet das Handy ein und wird danach aus der Adresszeile entfernt.
2. Der Workflow `.github/workflows/feldcheck.yml` holt alle Einsendungen, die noch nicht in `main` sind,
   rechnet die ganze Kette neu (`run_all.sh`), erzeugt Bericht und Vorschaubilder (`feldcheck_report.py`)
   und legt den Pull Request `feldcheck-update` an (bzw. aktualisiert ihn). Zusätzlich läuft er täglich und von Hand.
3. Zusammenführen (Merge) = freigeben: Karten, Liste und App in `main` sind aktualisiert, GitHub Pages veröffentlicht.
   Schließen ohne Merge = ablehnen: die Einsendungen wandern nach `eingang/abgelehnt/` und werden nicht mehr angefasst.

Einarbeitung (`build_layers.py`): pro Objekt gilt die jüngste Einsendung. „passt“ → sicher, Quelle „Feldbegehung“;
„fehlt“ → entfernt; „woanders“ → neue Lage, sicher. Neue Objekte bekommen die ID `F<id>`, neue Pfade landen in
`data/feldcheck_pfade.geojson`, Pfad-Urteile in `data/path_status_v1.json`, das Protokoll in `data/feldcheck_log.json`.

Hinweis: Das Repo ist öffentlich – Einsendungen (Name, Notizen) sind darin für alle lesbar.

## Rohdaten (`data/`)

| Ordner/Datei | Quelle | Lizenz |
|---|---|---|
| `map.osm` | OpenStreetMap, API-Export des Kartenrahmens | ODbL, © OpenStreetMap-Mitwirkende |
| `dgm/dgm1_32_*_1_ni_2022.tif` | LGLN Digitales Geländemodell DGM1 (1 m), 2022 | CC BY 4.0, © LGLN |
| `dop/dop20rgb_32_*_ni_2025-10-19.tif` | LGLN Digitale Orthophotos DOP20 (20 cm), Befliegung 19.10.2025 | CC BY 4.0, © LGLN |

Kartenrahmen: UTM32 (EPSG:25832) E 423750–427150, N 5958850–5961650.
Kacheln nachladen: LGLN-Kachelnamen wie oben, z. B. über die STAC-Dienste `dgm.stac.lgln.niedersachsen.de` und `dop.stac.lgln.niedersachsen.de`.

## Abgelegte Analyse-Ergebnisse (`data/`)

Diese Dateien sind Ergebnis längerer oder teils manueller Schritte. `run_all.sh` nutzt sie, `FULL=1` erzeugt die automatischen davon neu.

| Datei | Herkunft |
|---|---|
| `craters.geojson/.csv` | Bombentrichter: `craters2.py` (Höhenmodell) → `crater_dop.py` (Luftbild) → `craters_manual.py` (manuelle Ergänzungen) |
| `path_status.json` | Sichtbarkeit jedes OSM-Wegs im Luftbild (`path_check.py`) |
| `sand.geojson` | offene Sandflächen aus dem Luftbild (`sand.py`) |
| `bench_dop_verdict.json` | manuelle Sichtprüfung der Bänke im Luftbild (Kontaktabzug aus `bench_sheet.py`) |
| `id_registry.json` | stabile Landmarken-IDs – nicht löschen, sonst ändern sich IDs |
| `lupen.json` | Lupen-Buchstaben über alle Blätter (wird bei jedem Lauf neu berechnet) |

## Ablauf (`run_all.sh`)

1. `load_osm.py` – OSM einlesen → `data/osm.pkl`
2. `dgm_prep.py` – DGM-Kacheln mosaikieren und zuschneiden → `data/dgm_frame.tif`
3. `contours.py` – Höhenlinien 2,5 m
4. *(FULL)* `craters2.py`, `crater_dop.py`, `craters_manual.py`, `path_check.py`, `sand.py`
5. `landmarks_v0.py` – Landmarken aus OSM (Bänke, SOS-Schilder, Buhnen, km-Steine …)
6. `derived_landmarks.py` – Dünenkuppen und Steilhänge aus dem Höhenmodell
7. `build_layers.py` – alles zusammenführen, Status sicher/prüfen, stabile IDs → `data/points_v1.geojson`
8. `render_map.build_lupen_registry()` – Lupen-Bereiche und Buchstaben über alle Blätter
9. `render_map.py <blatt> <color|bw> …` – Blätter rendern (PDF + PNG)
10. `merge_pdfs.py` – Gesamt-PDFs
11. `build_site.py --tiles` – Feldcheck-Daten, Kartenkacheln, Ebenen-SVGs, Web-App (Wurzel) und Artefakt-Seite (`web/site/`)
12. `make_xlsx.py` – Landmarkenliste

## Wo man was einstellt

| Was | Wo |
|---|---|
| Blattschnitte, Maßstäbe | `scripts/render_map.py` → `SHEETS` |
| Farben, Liniendicken (Höhenlinien, Gruben …) | `scripts/render_map.py` → `PAL`, `layer_contours` |
| Symbole | `scripts/symbols2.py` → `shapes()` |
| Ortsnamen-Beschriftungen | `scripts/render_map.py` → `LABELS` |
| Lupen-Regeln, manuelle Lupe Westanleger | `scripts/render_map.py` → `OVERLAP_NEW`, `MANUAL_LUPEN` |
| Feldcheck-Oberfläche | `web/page_template.html` |
| App-Logo | `scripts/app_icon.py` → `web/icon-*.png`, `web/apple-touch-icon.png` |

Hilfsskripte ohne Einfluss auf die Ergebnisse: `view_*.py`, `symbol_*.py`, `family_demo.py`, `overview.py`, `trails.py`, `depressions.py`, `lrm.py`, `craters.py`, `meadow_craters.py` (frühere Varianten der Trichtererkennung).

## Schriften

Caveat, Patrick Hand, PT Serif – SIL Open Font License (`fonts/licenses/`). Leaflet 1.9.4 – BSD-2-Clause. jsPDF 2.5.2 und svg2pdf.js 2.2.4 – MIT (`web/lib/`).
