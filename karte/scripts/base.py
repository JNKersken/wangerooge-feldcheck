"""Project-wide constants for all scripts: project root, map frame, sheet order, Ruhezone relation, version.
Root = folder above scripts/ (override with env WANGEROOGE_BASE)."""
import os, json
BASE = os.environ.get('WANGEROOGE_BASE') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAME = (423750, 5958850, 427150, 5961650)            # map frame UTM32 (EPSG:25832): x0, y0, x1, y1
DETAIL_ORDER = ['detail_west', 'detail_mitte', 'detail_ost', 'detail_sued']   # Blatt 1..4
SHEET_ORDER = ['uebersicht'] + DETAIL_ORDER
RUHEZONE_REL = 16774424                                # OSM relation of Nationalpark-Ruhezone I/32
GH_REPO = 'JNKersken/wangerooge-feldcheck'
_V = json.load(open(os.path.join(BASE, 'data', 'version.json'), encoding='utf-8'))
VERSION, VERSION_DATE = _V['version'], _V['datum']    # one version for map, list and app (edit data/version.json)
OSM_DATE, DGM_YEAR, DOP_DATE = _V['osm_stand'], _V['dgm_jahr'], _V['dop_datum']   # data dates shown on map and list
def de_date(iso): return '.'.join(reversed(iso.split('-')))
# North on the map: the map is drawn in the UTM grid (grid north up). Angles clockwise from grid north, for the map centre,
# Oct 2026: true north +0.9° (meridian convergence, EPSG:25832), magnetic north +4.6° (WMM2025 declination +3.7°, grows ~0.15°/year).
GRID_TO_TRUE = 0.9
GRID_TO_MAG = 4.6
MAG_YEAR = 2026
SOURCES = (f'Daten: © OpenStreetMap-Mitwirkende (ODbL, Stand {de_date(OSM_DATE)}) · LGLN (2026) DGM1 ({DGM_YEAR}) & DOP20 '
           f'({de_date(DOP_DATE)}), CC BY 4.0 · Version {VERSION} vom {de_date(VERSION_DATE)}')
