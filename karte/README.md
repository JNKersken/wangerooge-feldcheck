# Kartenkette Wangerooge West

Alles, was die OL-Karte, die Landmarkenliste und die Feldcheck-Web-App erzeugt: Rohdaten, Skripte, Schriften, Vorlagen und die aktuellen Ergebnisse.

## Schnellstart

```bash
cd karte
python3 -m pip install -r requirements.lock   # genau die Versionen, mit denen auch GitHub Actions rechnet (Python 3.13)
./run_all.sh            # ca. 2–3 Minuten
FULL=1 ./run_all.sh     # rechnet zusätzlich Trichter-, Pfad- und Sandanalyse neu
python3 -m unittest discover -s tests && python3 scripts/check.py   # Regeln und Zusammenhang prüfen
```

Ergebnisse:

| Datei | Inhalt |
|---|---|
| `out/Wangerooge_West_OL_v1_Farbe.pdf` / `_SW.pdf` | Übersicht 1:15.000 + Blätter 1–4 (1:5.000 / 1:7.500) mit Lupen |
| `out/Wangerooge_West_Landmarken_v1.xlsx` | Landmarkenliste mit Status, Quellen, Koordinaten, Notizen vor Ort |
| `out/ol/Wangerooge_West_Posten.xml` | IOF XML 3.0: alle sicheren Landmarken als mögliche Posten (Purple Pen, OCAD, Condes), Start Sternwarte |
| `out/ol/*.gpx`, `out/ol/*.kml` | alle Landmarken als Wegpunkte (GPS-Geräte, Google Earth, QGIS) |
| `out/ol/<blatt>.jpg` + `.jgw` + `.prj` | Blatt (Farbe, nur Kartenfeld) mit Weltdatei, EPSG:25832 – als Hintergrund in QGIS, OCAD, OpenOrienteering Mapper |
| `out/ol/<blatt>.kmz` | Blatt als KML-Bodenüberlagerung (MapRun, Google Earth) |
| Repo-Wurzel (`index.html`, `t*.png`, `data.json` …) | Feldcheck-Web-App für GitHub Pages (GPS, offline) |
| Repo-Wurzel `karten/*.svg`, `karten/layers.json` | Blätter als Ebenen-SVG für „Karte als PDF“ in der App |

## Karte als PDF in der App

`render_map.py` schreibt neben PDF/PNG ein SVG, in dem jedes Kartenelement einer Ebene zugeordnet ist (`id="L-<ebene>-<n>"`, Liste in `render_map.LAYERS`).
Die App lädt diese SVGs, blendet abgewählte Ebenen aus und baut das PDF direkt im Browser (jsPDF + svg2pdf.js, `web/lib/`).
Neue Ebene: Schlüssel in `LAYERS` ergänzen und die Zeichenbefehle in `with tag(S, '<schlüssel>'):` einschließen.

`run_all.sh` schreibt die Web-App direkt in die Repo-Wurzel. Danach committen und pushen, GitHub Pages veröffentlicht automatisch.

Prüfen vor Ort: „Fehlt“ fragt nach – „nicht gefunden“ (bleibt in der Karte, zweimal von verschiedenen Handys = fehlt) oder
„sicher weg“. Verschiebungen über 40 m (bei GPS über 3× Genauigkeit) werden einmal rückgefragt. Mit GPS zeigt die Karte
Richtung und Entfernung zum gewählten Objekt (mit Kompass relativ zum Handy) und meldet unter 20 m „Fast da“.
Ruhezone: `build_site.py` bestimmt für jedes Objekt dort den nächsten Punkt auf einem Weg (`wp`, `wd`); liegt es mehr als
40 m (`RZ_SIGHT`) abseits, ist es nur per Luftbild prüfbar und zählt nicht zu den offenen Punkten im Gelände.
Menü → Anzeigen → „Sonnenmodus“ schaltet auf volle Flächen und starken Kontrast.

Offline: Kacheln und PDF-Daten (Blatt-SVGs farbig und SW, `lib/`) werden über ihren Inhalt adressiert (`t3_1_2.png?v=<hash>`,
Liste `OFFLINE` in `index.html` und `KEEP` in `sw.js`, beide von `build_site.py`). Die Caches `fc-tiles` und `fc-pdf` überleben
App-Updates; der Service Worker wirft beim Wechsel nur weg, was nicht mehr gebraucht wird, und die App lädt Geändertes nach,
wenn „Offline speichern“ einmal benutzt wurde.

## Feldcheck-Briefkasten (Einsendungen aus der App)

1. Helfer tippen in der App im Menü (•••) auf „Ans Kartenteam senden“. Die App legt eine JSON-Datei in den Zweig `eingang`
   (`karte/data/feldcheck/eingang/<zeit>_<name>_<zufall>.json`) und meldet das per `repository_dispatch`.
   Gesendet wird nur, was seit dem letzten Senden neu ist; zurückgenommene Bewertungen gehen als `zurueck`,
   gelöschte neue Objekte als `geloescht` mit. Ohne Netz wartet die Sendung und geht von selbst raus, sobald Netz da ist
   (Zähler am •••-Knopf). Jedes Handy hat eine zufällige Geräte-ID (`geraet_id`).
   Dafür braucht jedes Handy einen eigenen Fine-grained-Token (nur dieses Repo, „Contents: Read and write“);
   der Einladungslink `…/#key=<token>&name=<name>[&gebiet=detail_west]` richtet das Handy ein und wird danach aus der
   Adresszeile entfernt. Der Regelsatz auf `main` verhindert, dass ein Token direkt in `main` schreibt.
2. Der Workflow `.github/workflows/feldcheck.yml` legt zuerst abgelehnte Einsendungen beiseite (Dateien aus Vorschlägen,
   die ohne Merge geschlossen wurden → `eingang/abgelehnt/`), holt dann alle Einsendungen, die noch nicht in `main` sind,
   rechnet die ganze Kette neu (`run_all.sh`), erzeugt Bericht und Vorschaubilder (`feldcheck_report.py`)
   und legt den Pull Request `feldcheck-update` an (bzw. aktualisiert ihn). Er läuft bei jeder Meldung, nach jedem
   Schließen des Vorschlags, täglich und von Hand; jeder Lauf erledigt alles, was ansteht.
3. Zusammenführen (Merge) = freigeben: Karten, Liste und App in `main` sind aktualisiert, GitHub Pages veröffentlicht.
   Schließen ohne Merge = ablehnen: die Einsendungen wandern nach `eingang/abgelehnt/` und kommen mit dem nächsten
   Vorschlag nach `main` – dort sorgt `feldcheck_merge.py` dafür, dass sie nicht wieder auftauchen.
4. Die App vergleicht beim Start `data.json → feld` (pro Gerät: übernommen `v`/`n`, abgelehnt `x`) mit ihren lokalen
   Einträgen und räumt Übernommenes und Abgelehntes auf.

Einarbeitung (`feldcheck_merge.py` → `build_layers.py`): Jede Einsendung und jeder Eintrag wird einzeln geprüft;
Fehlerhaftes wird übersprungen und im Bericht genannt. Pro Gerät zählt der jüngste Eintrag je Objekt, über alle Geräte
der jüngste. „passt“ → sicher, Quelle „Feldbegehung“; „fehlt“ → entfernt; „woanders“ → neue Lage, sicher – eine
korrigierte Lage bleibt auch, wenn später jemand bestätigt. „nicht gefunden“ bleibt in der Karte und gilt erst als
„fehlt“, wenn zwei Geräte es nicht gefunden haben. Notizen landen in `vor_ort` (App, Liste). Neue Objekte bekommen die
ID `F<id>`, neue Pfade landen in `data/feldcheck_pfade.geojson`, Pfad-Urteile in `data/path_status_v1.json`, das
Protokoll in `data/feldcheck_log.json`.

Öffentlich erscheinen nur Kürzel der Helfer („A. M.“). Die Einsendungen selbst liegen im Zweig `eingang` dieses öffentlichen
Repos – oder, nach [BRIEFKASTEN.md](BRIEFKASTEN.md), in einem privaten Eingangs-Repo (`briefkasten.json` in der Repo-Wurzel
sagt der App und dem Workflow, wohin). Vor jedem Vorschlag prüft der Workflow Regeln, Daten und App (Status „Feldcheck-Prüfung“)
und listet Auffälliges mit Kartenausschnitt; Pull Requests von Hand prüft `.github/workflows/check.yml`.

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
| `lupen.json` | Lupen über alle Blätter (wird bei jedem Lauf neu berechnet) |
| `lupen_buchstaben.json` | welcher Buchstabe zu welchem Lupen-Gebiet gehört – nicht löschen: so behält jede Lupe ihren Buchstaben, neue Gebiete bekommen noch nie benutzte Buchstaben |
| `version.json` | Version und Datenstände für Karte, Liste und App |

## Ablauf (`run_all.sh`)

1. `load_osm.py` – OSM einlesen → `data/osm.pkl`
2. `dgm_prep.py` – DGM-Kacheln mosaikieren und zuschneiden → `data/dgm_frame.tif`
3. `contours.py` – Höhenlinien 2,5 m
4. *(FULL)* `craters2.py`, `crater_dop.py`, `craters_manual.py`, `path_check.py`, `sand.py`
5. `landmarks_v0.py` – Landmarken aus OSM (Bänke, SOS-Schilder, Buhnen, km-Steine …)
6. `derived_landmarks.py` – Dünenkuppen und Steilhänge aus dem Höhenmodell
7. `build_layers.py` – alles zusammenführen (mit `feldcheck_merge.py` für die Einsendungen), Status sicher/prüfen, stabile IDs → `data/points_v1.geojson`
8. `render_map.build_lupen_registry()` – Lupen-Bereiche über alle Blätter, Buchstaben aus `data/lupen_buchstaben.json`
9. `render_map.py <blatt> <color|bw> <pdf> [png] [dpi] [svg]` – Blätter rendern (PDF, PNG, Ebenen-SVG)
10. `merge_pdfs.py` – Gesamt-PDFs
11. `export_ol.py` – Export für OL- und GPS-Software → `out/ol/`
12. `build_site.py --tiles` – Feldcheck-Daten, Kartenkacheln, Ebenen-SVGs, Web-App (Wurzel) und Artefakt-Seite (`web/site/`)
13. `make_xlsx.py` – Landmarkenliste

## Wo man was einstellt

| Was | Wo |
|---|---|
| Blattschnitte, Maßstäbe | `scripts/render_map.py` → `SHEETS` |
| Farben, Liniendicken (Höhenlinien, Gruben …) | `scripts/render_map.py` → `PAL`, `layer_contours` |
| Symbole | `scripts/symbols2.py` → `shapes()` |
| Ortsnamen-Beschriftungen | `scripts/render_map.py` → `LABELS` |
| Lupen-Regeln, manuelle Lupe Westanleger | `scripts/render_map.py` → `OVERLAP_NEW`, `MANUAL_LUPEN` |
| Feldcheck-Oberfläche | `web/page_template.html` |
| Texte in der App („Was du suchst“, „Wo“, „Warum prüfen“) | `scripts/feld_text.py` |
| Einführung (Tour beim Start) | `web/page_template.html` → `TOUR_STEPS` |
| App-Logo | `scripts/app_icon.py` → `web/icon-*.png`, `web/apple-touch-icon.png` |

Hilfsskripte ohne Einfluss auf die Ergebnisse: `view_*.py`, `symbol_*.py`, `family_demo.py`, `overview.py`, `trails.py`, `depressions.py`, `lrm.py`, `craters.py`, `meadow_craters.py` (frühere Varianten der Trichtererkennung).

## Schriften

Caveat, Patrick Hand, PT Serif – SIL Open Font License (`fonts/licenses/`). Leaflet 1.9.4 – BSD-2-Clause. jsPDF 2.5.2 und svg2pdf.js 2.2.4 – MIT (`web/lib/`).

## Nordrichtung

Die Karte ist im UTM-Gitter gezeichnet (Gitternord oben). Die Nordlinien und der Nordpfeil zeigen nach magnetisch Nord:
`base.GRID_TO_MAG` = 4,6° östlich Gitternord (Missweisung nach WMM2025 für 2026 +3,7°, Meridiankonvergenz +0,9°).
Die Missweisung wächst um etwa 0,15° pro Jahr – bei einer neuen Ausgabe Wert und `MAG_YEAR` in `base.py` anpassen.
Derselbe Winkel korrigiert in der App die Kompassrichtung.

Gleiche Eingaben ergeben gleiche Dateien (PDF ohne Zeitstempel, Excel mit festen Zeiten, SVG mit festen IDs) –
ein Lauf ohne neue Daten ändert im Repo nichts.
