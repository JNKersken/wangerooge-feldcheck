"""Field-check app: data.json from points_v1, tile pyramid from the field render, layered sheet SVGs for the PDF export,
the web app (index.html, sw.js, …) into APP_OUT (repo root) and the claude.ai artifact page into web/site."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from base import BASE, FRAME, SHEET_ORDER, DETAIL_ORDER, VERSION, VERSION_DATE
import sys, json, math, os, re, glob, shutil, hashlib, datetime
from PIL import Image
from shapely.geometry import box
from geom import W, way_geom
import feld_text as FT, render_map as RM
Image.MAX_IMAGE_PIXELS = None
SITE = BASE + '/web/site'; os.makedirs(SITE, exist_ok=True)
APP = os.environ.get('APP_OUT') or BASE + '/web/app'; os.makedirs(APP, exist_ok=True)
TILE_RE = re.compile(r'^t\d+_\d+_\d+\.png$')
rd = lambda p: json.load(open(p, encoding='utf-8'))
def sub(text, old, new, count=1):
    """Template placeholder replacement that fails loudly when the placeholder is missing or ambiguous."""
    n = text.count(old)
    if n != count: raise SystemExit(f'build_site: Platzhalter {old!r} {n}× gefunden, erwartet {count}×')
    return text.replace(old, new)

# ---------- data.json ----------
F = rd(BASE + '/data/points_v1.geojson')['features']
frame = box(*FRAME)
paths = []   # OSM ways still to check (barely visible in the aerial image)
pstat = BASE + '/data/path_status_v1.json'
for wid, st in rd(pstat if os.path.exists(pstat) else BASE + '/data/path_status.json').items():
    if st.get('status') != 'prüfen' or int(wid) not in W: continue
    g = way_geom(int(wid))
    if g is None or g.geom_type != 'LineString': continue
    g = g.intersection(frame)
    if g.is_empty or g.geom_type != 'LineString': continue
    ti, hint, why = FT.path_texts(W[int(wid)]['tags'], g.length, st.get('why', ''))
    paths.append(dict(id=f'PF{wid}', k='Pfad', t=W[int(wid)]['tags'].get('highway', ''), n=ti, f=hint, w=why, s='prüfen',
                      c=[[round(x, 1), round(y, 1)] for x, y in g.coords], no='', q='OSM; im Luftbild kaum sichtbar'))
ANCH = FT.anchors_from([(f['properties'], f['geometry']['coordinates']) for f in F], RM.LABELS)
items = []
for f in F:
    p = f['properties']; e, n = f['geometry']['coordinates']
    ti, hint = FT.title_hint(p)
    it = dict(id=p['id'], k=p['kategorie'], t=p['typ'], n=ti, f=hint, w=FT.why(p), wo=FT.where(e, n, ANCH, (p['name'] or '').strip()), s=p['status'],
              e=round(e, 1), nn=round(n, 1), q=p['quellen'], no=FT.description(p), z=p.get('zone', ''))
    if p.get('nf'): it['nf'] = int(p['nf'])
    items.append(it)
for p in paths: p['wo'] = FT.where(*p['c'][len(p['c']) // 2], ANCH)
fpaths = rd(BASE + '/data/feldcheck_pfade.geojson')['features'] if os.path.exists(BASE + '/data/feldcheck_pfade.geojson') else []
stand_fc = rd(BASE + '/data/feldcheck_stand.json') if os.path.exists(BASE + '/data/feldcheck_stand.json') else {}
last_t = max([t for d in stand_fc.values() for k, kind in d.items() if k != 'x' for t in kind.values()], default=0)
stand_fc = {k: v for k, v in stand_fc.items() if k.startswith('d-')}   # public file: device ids only, no helper names
from zoneinfo import ZoneInfo
stand = max(VERSION_DATE, datetime.datetime.fromtimestamp(last_t / 1000, ZoneInfo('Europe/Berlin')).date().isoformat() if last_t else VERSION_DATE)
areas = [dict(id=n, title=RM.SHEETS[n]['sub'], bbox=list(RM.SHEETS[n]['bbox'])) for n in DETAIL_ORDER]   # working areas for helpers
data = dict(version=VERSION, stand=stand, items=items, paths=paths, feld=stand_fc, sheets=areas,
            merged=[i['id'] for i in items if i['id'].startswith('F') and 'Feldbegehung' in (i['q'] or '')] + [f['properties']['id'] for f in fpaths])
json.dump(data, open(SITE + '/data.json', 'w'), ensure_ascii=False, separators=(',', ':'), sort_keys=True)
print('items', len(items), 'paths', len(paths))

# ---------- tiles (only with --tiles) ----------
if '--tiles' in sys.argv:
    full = BASE + '/web/feld_full.png'
    RM.render_field(full, 2)
    im = Image.open(full).convert('RGB'); W2, H2 = im.size; print('full', im.size)
    for f in glob.glob(SITE + '/t*.png'):
        if TILE_RE.match(os.path.basename(f)): os.remove(f)
    T = 512; PAPER = (255, 253, 247); cnt = 0
    for z in (1, 0, -1, -2):
        f_ = 2 ** z / 2; w, h = round(W2 * f_), round(H2 * f_)
        lv = im if f_ == 1 else im.resize((w, h), Image.LANCZOS)
        for tx in range(math.ceil(w / T)):
            for ty in range(math.ceil(h / T)):
                tile = Image.new('RGB', (T, T), PAPER); tile.paste(lv.crop((tx * T, ty * T, min(w, tx * T + T), min(h, ty * T + T))), (0, 0))
                tile.quantize(96, method=Image.Quantize.MEDIANCUT).save(f'{SITE}/t{z + 2}_{tx}_{ty}.png', optimize=True); cnt += 1
    print('tiles', cnt)

# ---------- page template ----------
tpl = sub(open(BASE + '/web/page_template.html', encoding='utf-8').read(), '/*LEAFLET*/', open(BASE + '/web/leaflet.min.css').read())
tpl = sub(tpl, "const APP_VERSION = '';", f"const APP_VERSION = '{VERSION}';")
# 1) claude.ai artifact (no GPS, no offline)
open(SITE + '/index.html', 'w').write(sub(sub(tpl, '<!--LEAFLETJS-->', '<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js"></script>'), '/*ISAPP*/false', 'false'))

# 2) web app (GitHub Pages): tiles, data, layered SVGs, libraries, service worker.
#    Offline: tiles and PDF data are addressed by content ('t3_1_2.png?v=<hash>'), so a new map version only replaces
#    what changed; the service worker drops stale copies when it takes over (list in sw.js), the app re-downloads.
for f in glob.glob(APP + '/t*.png'):
    if TILE_RE.match(os.path.basename(f)): os.remove(f)
tiles = sorted(f for f in glob.glob(SITE + '/t*.png') if TILE_RE.match(os.path.basename(f)))
for f in tiles + [SITE + '/data.json']: shutil.copy(f, APP)
for f in ('manifest.webmanifest', 'icon-192.png', 'icon-512.png', 'apple-touch-icon.png', 'favicon-32.png'): shutil.copy(BASE + '/web/' + f, APP)
shutil.copy(BASE + '/fonts/leaflet/package/dist/leaflet.js', APP + '/leaflet.js')
K = APP + '/karten'; os.makedirs(K, exist_ok=True)
sheets = []
for name in SHEET_ORDER:
    cfg = RM.SHEETS[name]; files = {}
    for m in ('color', 'bw'):
        src = f'{BASE}/out/svg/{name}_{m}.svg'
        if os.path.exists(src): shutil.copy(src, f'{K}/{name}_{m}.svg'); files[m] = f'karten/{name}_{m}.svg'
    if files: sheets.append(dict(id=name, title=cfg['sub'], bbox=list(cfg['bbox']), files=files))
json.dump(dict(stand=stand, version=VERSION, sheets=sheets, layers=[dict(key=k, label=l, group=g) for k, l, g in RM.LAYERS]),
          open(K + '/layers.json', 'w'), ensure_ascii=False, indent=1)
os.makedirs(APP + '/lib', exist_ok=True)
for f in ('jspdf.umd.min.js', 'svg2pdf.umd.min.js', 'qrcode.js'): shutil.copy(BASE + '/web/lib/' + f, APP + '/lib/' + f)
for f in glob.glob(K + '/*'):   # sheets no longer built
    if os.path.basename(f) != 'layers.json' and not any(f.endswith(v) for s in sheets for v in s['files'].values()): os.remove(f)
off_files = [os.path.basename(f) for f in tiles] + sorted(os.path.relpath(f, APP) for f in glob.glob(K + '/*') + glob.glob(APP + '/lib/*.js'))
OFFLINE = dict(files={p: hashlib.md5(open(APP + '/' + p, 'rb').read()).hexdigest()[:10] for p in off_files},
               bytes=sum(os.path.getsize(APP + '/' + p) for p in off_files))
off_json = json.dumps(OFFLINE, separators=(',', ':'), sort_keys=True)
body = sub(sub(sub(tpl, '<!--LEAFLETJS-->', '<script src="leaflet.js"></script>'), '/*ISAPP*/false', 'true'), 'const OFFLINE = null;', f'const OFFLINE = {off_json};')
cut = body.index('</style>') + len('</style>')
head = ('<!doctype html><html lang="de"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes">'
        '<meta name="apple-mobile-web-app-title" content="Feldcheck"><meta name="apple-mobile-web-app-status-bar-style" content="default">'
        '<meta name="theme-color" media="(prefers-color-scheme: light)" content="#f2f2f5"><meta name="theme-color" media="(prefers-color-scheme: dark)" content="#1c1c1e">'
        '<link rel="manifest" href="manifest.webmanifest"><link rel="apple-touch-icon" href="apple-touch-icon.png">'
        '<link rel="icon" href="favicon-32.png" sizes="32x32"><link rel="icon" href="icon-192.png" sizes="192x192">'
        '<style>:root{color-scheme:light dark}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>')
html = head + body[:cut] + '</head><body>' + body[cut:] + '</body></html>'
open(APP + '/index.html', 'w').write(html)
sw_tpl = open(BASE + '/web/sw.js').read()
CORE = 'fc-core-' + hashlib.md5((html + open(APP + '/data.json').read() + sw_tpl).encode()).hexdigest()[:8]
keep = json.dumps(sorted(f'{p}?v={h}' for p, h in OFFLINE['files'].items()), separators=(',', ':'))
sw = sub(sub(sw_tpl, "const CORE = 'fc-core'", f"const CORE = '{CORE}'"), 'const KEEP = [];', f'const KEEP = {keep};')
open(APP + '/sw.js', 'w').write(sw)
open(APP + '/.nojekyll', 'w').write('')
if os.path.exists(APP + '/tiles.json'): os.remove(APP + '/tiles.json')   # tile list now lives in the app (OFFLINE)
print('Cache', CORE, '| offline', len(off_files), 'Dateien', round(OFFLINE['bytes'] / 1e6, 1), 'MB | Blätter', len(sheets), '| App', len(os.listdir(APP)), 'Dateien')
