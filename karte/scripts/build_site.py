"""Field-check site: data.json from points_v1 + tile pyramid from the field render + index.html from the template."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import sys, json, math, os; None
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
BASE = BASE + ''; SITE = BASE + '/web/site'
F = json.load(open(BASE + '/data/points_v1.geojson'))['features']
# paths still to check (OSM ways barely visible in the aerial image), rebuilt from path_status.json
from geom import W, way_geom
from shapely.geometry import box as _box
_F = _box(423750, 5958850, 427150, 5961650)
_paths = []
for wid, st in json.load(open(BASE + '/data/path_status_v1.json' if os.path.exists(BASE + '/data/path_status_v1.json') else BASE + '/data/path_status.json')).items():
    if st.get('status') != 'prüfen' or int(wid) not in W: continue
    t = W[int(wid)]['tags']; g = way_geom(int(wid))
    if g is None or g.geom_type != 'LineString': continue
    g = g.intersection(_F)
    if g.is_empty or g.geom_type != 'LineString': continue
    _paths.append(dict(id=f'PF{wid}', k='Pfad', t=t.get('highway', ''), n=t.get('name', ''), s='prüfen', c=[[round(x, 1), round(y, 1)] for x, y in g.coords],
                       no=f"Belag {t.get('surface', 'unbekannt')}, Länge {round(g.length)} m, {st.get('why', '')}", q='OSM; im Luftbild kaum sichtbar'))
old = dict(paths=_paths); os.makedirs(SITE, exist_ok=True)
def nice_name(p):
    k, n = p['kategorie'], p['name']
    if k == 'Rettungspunkt' and n: return f'SOS-Schild Nr. {n}'
    if k == 'Kuppe' and n: return f'Dünenkuppe {n} m'
    if k == 'km-Stein' and n: return f'km-Stein {n}'
    if k == 'Buhne' and n: return f'Buhne {n}'
    if k == 'Haltepunkt' and n: return f'Haltepunkt {n}'
    return n
items = []
for f in F:
    p = f['properties']; e, n = f['geometry']['coordinates']
    items.append(dict(id=p['id'], k=p['kategorie'], t=p['typ'], n=nice_name(p), s=p['status'], e=round(e, 1), nn=round(n, 1), q=p['quellen'], no=(p.get('notiz') or '')[:260], z=p.get('zone', '')))
json.dump(dict(items=items, paths=old['paths'], merged=[i['id'] for i in items if i['id'].startswith('F')] + [f['properties']['id'] for f in (json.load(open(BASE + '/data/feldcheck_pfade.geojson'))['features'] if os.path.exists(BASE + '/data/feldcheck_pfade.geojson') else [])]),
          open(SITE + '/data.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('items', len(items), 'paths', len(old['paths']))
if '--tiles' in sys.argv:
    import render_map
    full = BASE + '/web/feld_full.png'
    render_map.render_field(full, 2)
    im = Image.open(full).convert('RGB'); W2, H2 = im.size; print('full', im.size)
    T = 512; PAPER = (255, 253, 247); cnt = 0
    for z in (1, 0, -1, -2):
        f_ = 2 ** z / 2; w, h = round(W2 * f_), round(H2 * f_)
        lv = im if f_ == 1 else im.resize((w, h), Image.LANCZOS)
        for tx in range(math.ceil(w / T)):
            for ty in range(math.ceil(h / T)):
                tile = Image.new('RGB', (T, T), PAPER); tile.paste(lv.crop((tx * T, ty * T, min(w, tx * T + T), min(h, ty * T + T))), (0, 0))
                tile.quantize(96, method=Image.Quantize.MEDIANCUT).save(f'{SITE}/t{z + 2}_{tx}_{ty}.png', optimize=True); cnt += 1
    print('tiles', cnt)
tpl = open(BASE + '/web/page_template.html').read().replace('/*LEAFLET*/', open(BASE + '/web/leaflet.min.css').read())
# 1) claude.ai artifact (no GPS there)
open(SITE + '/index.html', 'w').write(tpl.replace('<!--LEAFLETJS-->', '<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js"></script>').replace('/*ISAPP*/false', 'false'))
print('index.html ok')
# 2) standalone web app (own domain, e.g. GitHub Pages): GPS, offline, home-screen app
import shutil, glob
APP = os.environ.get('APP_OUT') or BASE + '/web/app'; os.makedirs(APP, exist_ok=True)
for f in glob.glob(APP + '/t*.png'): os.remove(f)
for f in glob.glob(SITE + '/t*.png') + [SITE + '/data.json']: shutil.copy(f, APP)
for f in ('sw.js', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png', 'apple-touch-icon.png', 'favicon-32.png'): shutil.copy(BASE + '/web/' + f, APP)
shutil.copy(BASE + '/fonts/leaflet/package/dist/leaflet.js', APP + '/leaflet.js')
json.dump(sorted(os.path.basename(f) for f in glob.glob(APP + '/t*.png')), open(APP + '/tiles.json', 'w'))
body = tpl.replace('<!--LEAFLETJS-->', '<script src="leaflet.js"></script>').replace('/*ISAPP*/false', 'true')
cut = body.index('</style>') + len('</style>')
head = ('<!doctype html><html lang="de"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes">'
        '<meta name="apple-mobile-web-app-title" content="Feldcheck"><meta name="apple-mobile-web-app-status-bar-style" content="default">'
        '<meta name="theme-color" content="#fffdf7"><link rel="manifest" href="manifest.webmanifest"><link rel="apple-touch-icon" href="apple-touch-icon.png">'
        '<link rel="icon" href="favicon-32.png" sizes="32x32"><link rel="icon" href="icon-192.png" sizes="192x192"><style>:root{color-scheme:light}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>')
open(APP + '/index.html', 'w').write(head + body[:cut] + '</head><body>' + body[cut:] + '</body></html>')
open(APP + '/.nojekyll', 'w').write('')
# layered map SVGs + layer list for "Karte als PDF" in the app
import datetime, render_map
K = APP + '/karten'; os.makedirs(K, exist_ok=True)
sheets = []
for name in ('uebersicht', 'detail_west', 'detail_mitte', 'detail_ost', 'detail_sued'):
    cfg = render_map.SHEETS[name]; files = {}
    for m in ('color', 'bw'):
        src = f'{BASE}/out/svg/{name}_{m}.svg'
        if os.path.exists(src): shutil.copy(src, f'{K}/{name}_{m}.svg'); files[m] = f'karten/{name}_{m}.svg'
    if files: sheets.append(dict(id=name, title=cfg['sub'], scale=cfg['scale'], orient=cfg['orient'], files=files, kb=round(os.path.getsize(f'{K}/{name}_color.svg') / 1024) if 'color' in files else 0))
json.dump(dict(stand=datetime.date.today().isoformat(), sheets=sheets, layers=[dict(key=k, label=l, group=g) for k, l, g in render_map.LAYERS]),
          open(K + '/layers.json', 'w'), ensure_ascii=False, indent=1)
for f in ('jspdf.umd.min.js', 'svg2pdf.umd.min.js', 'qrcode.js'):
    if os.path.exists(BASE + '/web/lib/' + f): os.makedirs(APP + '/lib', exist_ok=True); shutil.copy(BASE + '/web/lib/' + f, APP + '/lib/' + f)
print('karten', len(sheets), 'Blätter')
print('app ok', len(os.listdir(APP)), 'Dateien')
