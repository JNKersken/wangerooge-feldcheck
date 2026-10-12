"""Merge OSM landmarks, bench verdicts, craters, path status -> data/points_v1.geojson + out/landmarken_v1.csv"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import sys, json, csv, math; None
from shapely.geometry import shape, Point, mapping
from geom import *
L = list(csv.DictReader(open(BASE + '/out/landmarken_v0.csv')))
bench = json.load(open(BASE + '/data/bench_dop_verdict.json'))
paths = json.load(open(BASE + '/data/path_status.json'))
C = json.load(open(BASE + '/data/craters.geojson'))['features']
crater_osm = {f['properties']['osm']: f['properties'] for f in C if f['properties']['osm']}
pts = []
CORR = {'n2322038072': (424355.6, 5960277.9, 'Kuppel im Luftbild sichtbar, 8,6 m östlich vom OSM-Punkt auf dem Nordflügel des Inselheims')}
for r in L:
    if r['osm'] in CORR:
        x, y, why = CORR[r['osm']]; lat, lon = ll(x, y)
        r['utm_e'], r['utm_n'], r['lat'], r['lon'] = round(x, 1), round(y, 1), round(lat, 6), round(lon, 6)
        r['notiz'] = (r['notiz'] + ' | ' if r['notiz'] else '') + 'Lage korrigiert: ' + why; r['status'] = 'sicher'; r['quellen'] = 'OSM + Luftbild + aloeus.de'
def st_for(r):
    k, t, o = r['kategorie'], r['typ'], r['osm']
    if k == 'Bank':
        v = bench.get(o, 'nein'); return ('sicher', 'OSM + Luftbild') if v == 'ja' else ('prüfen', 'OSM; im Luftbild ' + ('unsicher' if v == 'evtl' else 'nicht erkennbar'))
    if r['status'] == 'sicher': return 'sicher', r['quellen']
    if k in ('Unterkunft', 'Gebäude', 'Vegetation') : return 'sicher', 'OSM + Luftbild (Gebäude/Fläche sichtbar)'
    if k == 'Historisch' and t == 'Friedhof': return 'sicher', 'OSM + Luftbild'
    if k == 'Bauwerk' and t in ('lighthouse', 'tower', 'Sternwarte'): return 'sicher', r['quellen']
    if k == 'Gelände': return 'sicher', 'OSM + Höhenmodell'
    if k == 'Dünenübergang': return 'sicher', 'OSM + Luftbild'
    if k == 'Gewässer':
        c = crater_osm.get(o)
        A = float(r['notiz'].split('Fläche ')[1].split(' ')[0]) if 'Fläche' in r['notiz'] else 0
        if A > 1000: return 'sicher', 'OSM + Luftbild'
        if c and c.get('dop') == 'ja': return 'sicher', 'OSM + Luftbild'
        return 'prüfen', 'OSM; im Luftbild nicht eindeutig'
    if k == 'Einrichtung' and t in ('ferry_terminal', 'lifeboat', 'boat_storage'): return 'sicher', 'OSM + Luftbild'
    if k == 'Gastronomie': return 'prüfen', 'OSM; Betrieb nicht geprüft'
    if k in ('Buhne', 'Haltepunkt', 'Bahnübergang', 'Spielplatz', 'Sportplatz', 'Brücke'): return 'sicher', 'OSM + Luftbild'
    return 'prüfen', 'nur OSM'
for r in L:
    if r['kategorie'] == 'Gewässer' and r['osm'] in crater_osm: pass
    s, q = st_for(r)
    r['status'], r['quellen'] = s, q
    if r['kategorie'] == 'Gewässer':
        c = crater_osm.get(r['osm'])
        if c: r['notiz'] += ' | wassergefüllter Trichter?'
    pts.append(r)
# craters (DGM-based; OSM-water-only ones are already in list as Gewässer)
n = 0
for f in sorted(C, key=lambda f: (-f['properties']['y'] // 100, f['properties']['x'])):
    p = f['properties']
    if p['quelle'] == 'OSM(Wasser)' or not p.get('show', True): continue
    n += 1
    s = 'sicher' if p.get('sure') else 'prüfen'
    q = 'Höhenmodell' + (' + Luftbild' if p.get('dop') == 'ja' else '') + (' + OSM-Wasser' if p['osm'] else '')
    if p['klasse'] == 'Luftbild': q = 'Luftbild (manuell ausgewertet)'; s = 'sicher' if p['dop'] == 'ja' else 'prüfen'
    lat, lon = ll(p['x'], p['y'])
    pts.append(dict(id=f'TR{n:03d}', kategorie='Trichter', typ='Grube/Trichter', name='', lat=round(lat, 6), lon=round(lon, 6), utm_e=p['x'], utm_n=p['y'],
                    zone='', quellen=q, osm=p['osm'], osm_stand='', status=s,
                    notiz=(f"Ø {p['d']} m, Tiefe {p['tiefe']} m, Form {p['klasse']}, Luftbild {p.get('dop')}" if p['klasse'] != 'Luftbild' else f"Ø ca. {p['d']} m, im Luftbild als Grube mit Bewuchs sichtbar")))
# terrain / aerial derived points
for d in json.load(open(BASE + '/data/derived_points.json')):
    lat, lon = ll(d['x'], d['y'])
    pts.append(dict(id={'Kuppe': 'KU', 'Steilhang': 'SH', 'Busch': 'BU'}[d['kategorie']] + '000', kategorie=d['kategorie'], typ=d['typ'], name=d['name'], lat=round(lat, 6), lon=round(lon, 6),
                    utm_e=round(d['x'], 1), utm_n=round(d['y'], 1), zone='', quellen=d['quellen'], osm='', osm_stand='', status=d['status'], notiz=d['notiz'],
                    prom=d.get('prom', ''), z=d.get('z', '')))
from shapely.strtree import STRtree
_ways = [way_geom(w) for w, v in W.items() if 'highway' in v['tags']]; _ways = [g for g in _ways if g is not None]
_WT = STRtree(_ways)
for r in pts:
    if r['kategorie'] == 'Trichter':
        pt = Point(float(r['utm_e']), float(r['utm_n']))
        if _ways[_WT.nearest(pt)].distance(pt) < 1.5:
            r['status'] = 'prüfen'; r['notiz'] += ' | liegt auf einem OSM-Pfad – Pfad oder Grube ungenau'
# duplicates of the same physical object (multi-track level crossing, playground as node + area)
_drop = set()
for i, a in enumerate(pts):
    if a['kategorie'] not in ('Bahnübergang', 'Spielplatz', 'Sportplatz', 'Recycling', 'Fahrradständer', 'Hydrant'): continue
    for j in range(i + 1, len(pts)):
        b = pts[j]
        if j in _drop or b['kategorie'] != a['kategorie']: continue
        dd = math.hypot(float(a['utm_e']) - float(b['utm_e']), float(a['utm_n']) - float(b['utm_n']))
        if dd < (12 if a['kategorie'] == 'Bahnübergang' else 45) and (a['kategorie'] == 'Bahnübergang' or a['name'] == b['name'] or not b['name']):
            _drop.add(j)
pts = [r for i, r in enumerate(pts) if i not in _drop]
print('Dubletten entfernt', len(_drop))
# stable IDs: registry keyed by OSM id or crater position
import os
REG = BASE + '/data/id_registry.json'
reg = json.load(open(REG)) if os.path.exists(REG) else {}
NEWCAT = {'km-Stein', 'Bahnübergang', 'Haltepunkt', 'Buhne', 'Brücke', 'Hydrant', 'Spielplatz', 'Sportplatz', 'Fitness', 'Recycling', 'Fahrradständer', 'Umspannstation'}
def key(r): return (r['osm'] + ('#' + r['kategorie'] if r['kategorie'] in NEWCAT else '')) if (r['osm'] and r['kategorie'] != 'Trichter') else f"{ {'Trichter': 'cr', 'Kuppe': 'ku', 'Steilhang': 'sh', 'Busch': 'bu'}.get(r['kategorie'], 'xx') }:{round(float(r['utm_e']))}:{round(float(r['utm_n']))}"
pref = {}
for r in pts: pref.setdefault(r['kategorie'], ''.join(ch for ch in r['id'] if ch.isalpha()))
pref['Busch'] = 'BS'
used = {}
for k_, v_ in reg.items():
    p_ = ''.join(ch for ch in v_ if ch.isalpha()); used[p_] = max(used.get(p_, 0), int(''.join(ch for ch in v_ if ch.isdigit())))
for r in pts:
    k_ = key(r)
    if k_ not in reg:
        # crater keys may shift by a metre between runs: reuse an id within 2 m
        hit = None
        if k_[:3] in ('cr:', 'ku:', 'sh:', 'bu:'):
            _, a, c = k_.split(':')
            for kk, vv in reg.items():
                if kk[:3] == k_[:3]:
                    _, a2, c2 = kk.split(':')
                    if abs(int(a) - int(a2)) <= 2 and abs(int(c) - int(c2)) <= 2: hit = vv; break
        if hit is None:
            p_ = pref[r['kategorie']]; used[p_] = used.get(p_, 0) + 1; hit = f"{p_}{used[p_]:03d}"
        reg[k_] = hit
    r['id'] = reg[k_]
json.dump(reg, open(REG, 'w'), indent=0)
import collections as _co
_cnt = _co.Counter(r['name'] for r in pts if r['kategorie'] == 'Rettungspunkt' and r['name'])
for r in pts:
    if r['kategorie'] == 'Rettungspunkt' and _cnt[r['name']] > 1:
        r['status'] = 'prüfen'; r['notiz'] = (r['notiz'] + ' | ' if r['notiz'] else '') + f"Nr. {r['name']} ist in OSM {_cnt[r['name']]}x an verschiedenen Stellen eingetragen – vor Ort klären, welche stimmt"
I32 = rel_geom(16774424)
for r in pts:
    if r['kategorie'] == 'Trichter' and I32.contains(Point(float(r['utm_e']), float(r['utm_n']))): r['zone'] = 'Ruhezone I/32'
flds = ['id', 'kategorie', 'typ', 'name', 'status', 'quellen', 'lat', 'lon', 'utm_e', 'utm_n', 'zone', 'notiz', 'osm', 'osm_stand', 'prom', 'z']
with open(BASE + '/out/landmarken_v1.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=flds, extrasaction='ignore'); w.writeheader(); w.writerows(pts)
json.dump(dict(type='FeatureCollection', features=[dict(type='Feature', geometry=dict(type='Point', coordinates=[float(r['utm_e']), float(r['utm_n'])]),
          properties={k: r.get(k, '') for k in flds}) for r in pts]), open(BASE + '/data/points_v1.geojson', 'w'))
import collections
c = collections.Counter((r['kategorie'], r['status']) for r in pts)
for k in sorted({k for k, _ in c}): print(f"{k:14s} sicher={c[(k,'sicher')]:4d} prüfen={c[(k,'prüfen')]:4d}")
print('gesamt', len(pts), 'prüfen', sum(1 for r in pts if r['status'] == 'prüfen'))
