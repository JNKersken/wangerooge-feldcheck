"""Extract landmark list v0 from OSM for the map frame -> CSV + GeoJSON."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import sys, csv, json, math
None
from geom import *
from shapely.geometry import box, mapping
F = box(423750, 5958850, 427150, 5961650)
I32 = rel_geom(16774424)
SICHER = {  # second independent source for prominent objects
 'w59869587': 'Wikipedia-Koordinate (4 m Abw.)', 'r5634075': 'aloeus.de: Zum Westen 32', 'n2322038072': 'aloeus.de / NWZ',
 'n282494436': 'DJH / gruppenhaus.de', 'w165518794': 'Wikipedia: Leuchtturm hinter Dünen im Westen', 'n1274835526': 'Wikipedia/Fährinfo',
 'n1431099411': 'TracesOfWar: Fußweg zum Westen 5', 'w48648249': 'gruppenhaus.de (Westkap)'}
rows = []; feats = []
def add(cat, typ, name, oid, geom, note='', osm=None):
    if geom is None or not geom.intersects(F): return
    p = geom if geom.geom_type == 'Point' else geom.representative_point()
    lat, lon = ll(p.x, p.y)
    o = osm or {}
    src = 'OSM' + (' + ' + SICHER[oid] if oid in SICHER else '')
    zone = 'Ruhezone I/32' if I32.contains(p) else ''
    rows.append(dict(id='', kategorie=cat, typ=typ, name=name or '', lat=round(lat, 6), lon=round(lon, 6),
        utm_e=round(p.x, 1), utm_n=round(p.y, 1), zone=zone, quellen=src, osm=oid, osm_stand=(o.get('ts') or '')[:10],
        status='sicher' if oid in SICHER else 'prüfen', notiz=note))
    feats.append(dict(type='Feature', geometry=mapping(geom), properties=dict(cat=cat, typ=typ, name=name or '', osm=oid)))
def nm(t): return t.get('name', '')
for nid, n in N.items():
    t = n['tags']; 
    if not t: continue
    p = Point(xy(nid)); oid = f'n{nid}'
    a = t.get('amenity'); tr = t.get('tourism'); mm = t.get('man_made'); hw = t.get('highway'); br = t.get('barrier')
    if a == 'bench':
        add('Bank', 'Bank', nm(t), oid, p, ', '.join(f'{k}={v}' for k, v in t.items() if k in ('backrest', 'material', 'seats', 'direction', 'check_date')), n)
    elif a == 'shelter': add('Bauwerk', 'Schutzhütte', nm(t), oid, p, t.get('shelter_type', ''), n)
    elif a in ('restaurant', 'cafe', 'fast_food', 'bar', 'pub'): add('Gastronomie', a, nm(t), oid, p, '', n)
    elif tr in ('hostel', 'hotel'): add('Unterkunft', tr, nm(t), oid, p, '', n)
    elif mm == 'observatory': add('Bauwerk', 'Sternwarte', nm(t), oid, p, '', n)
    elif mm in ('flagpole', 'mast', 'antenna', 'monitoring_station', 'surveillance'): add('Kleinobjekt', mm, nm(t), oid, p, '', n)
    elif t.get('natural') == 'tree': add('Baum', 'Einzelbaum', nm(t), oid, p, ', '.join(f'{k}={v}' for k, v in t.items() if k in ('leaf_type', 'genus', 'species', 'height', 'circumference')), n)
    elif t.get('natural') == 'peak': add('Gelände', 'Düne (Gipfel)', nm(t), oid, p, 'ele=' + t.get('ele', '?'), n)
    elif hw == 'emergency_access_point':
        import re as _re
        num = t.get('ref') or (_re.search(r'(\d+)', t.get('name', '')) or [None, ''])[1]
        add('Rettungspunkt', 'SOS-Schild', num, oid, p, (t.get('note', '') + (' | OSM-Hinweis: ' + t['fixme'] if 'fixme' in t else '')).strip(' |'), n)
    elif br in ('gate', 'lift_gate', 'turnstile', 'cycle_barrier', 'coupure', 'bollard', 'chain'): add('Durchgang', br, nm(t), oid, p, '', n)
    elif tr == 'information' and t.get('information') in ('board', 'guidepost', 'map'): add('Kleinobjekt', 'Infotafel' if t.get('information') == 'board' else 'Wegweiser', nm(t), oid, p, '', n)
    elif tr in ('picnic_site', 'viewpoint', 'artwork') or t.get('leisure') in ('firepit', 'picnic_table'): add('Kleinobjekt', tr or t.get('leisure'), nm(t), oid, p, '', n)
    elif 'historic' in t: add('Historisch', t.get('memorial', t['historic']), nm(t), oid, p, t.get('description', ''), n)
    elif t.get('railway') == 'milestone':
        km = t.get('railway:position', '').replace('.', ',')
        add('km-Stein', 'km-Stein Inselbahn', km, oid, p, f'Kilometerstein Inselbahn, km {km}', n)
    elif t.get('railway') in ('crossing', 'level_crossing'): add('Bahnübergang', t['railway'], nm(t), oid, p, 'Weg kreuzt die Inselbahn', n)
    elif t.get('railway') == 'station': add('Haltepunkt', 'Haltepunkt Inselbahn', nm(t), oid, p, '', n)
    elif t.get('emergency') == 'fire_hydrant': add('Hydrant', t.get('fire_hydrant:type', 'Hydrant'), t.get('ref', ''), oid, p, ', '.join(f'{k}={v}' for k, v in t.items() if k.startswith('fire_hydrant')), n)
    elif t.get('leisure') == 'playground': add('Spielplatz', 'Spielplatz', nm(t), oid, p, '', n)
    elif t.get('leisure') == 'fitness_station': add('Fitness', 'Fitnessgerät', nm(t), oid, p, '', n)
    elif a == 'recycling': add('Recycling', 'Recycling', nm(t), oid, p, ', '.join(k[10:] for k, v in t.items() if k.startswith('recycling:') and v == 'yes'), n)
    elif a == 'bicycle_parking': add('Fahrradständer', 'Fahrradständer', nm(t), oid, p, t.get('capacity', ''), n)
    elif t.get('power') == 'substation': add('Umspannstation', 'Umspannstation', nm(t), oid, p, '', n)
    elif a in ('ferry_terminal', 'toilets', 'lifeboat', 'boat_storage') or t.get('emergency') in ('lifeguard', 'life_ring', 'siren', 'fire_water_pond'): add('Einrichtung', a or t.get('emergency'), nm(t), oid, p, '', n)
import rasterio as _rio
_dgm = _rio.open(BASE + '/data/dgm_frame.tif'); _Z = _dgm.read(1)
def _z(x, y):
    try:
        r, c = _dgm.index(x, y); v = _Z[r, c]; return -9 if v != v else float(v)
    except Exception: return -9
for wid, w in W.items():
    t = w['tags']
    if t.get('man_made') == 'groyne' and t.get('name', '').startswith('Buhne'):
        g = way_geom(wid)
        if g is None or g.geom_type != 'LineString': continue
        a0, a1 = Point(g.coords[0]), Point(g.coords[-1])
        land = a0 if _z(a0.x, a0.y) >= _z(a1.x, a1.y) else a1
        if F.contains(land): add('Buhne', 'Buhne (Landseite)', t['name'].replace('Buhne ', ''), f'w{wid}', land, f"{t['name']}, Länge {round(g.length)} m; Punkt = landseitiges Ende", w)
    elif t.get('bridge') == 'yes' and ('highway' in t or 'railway' in t):
        g = way_geom(wid)
        if g is not None: add('Brücke', 'Brücke', nm(t), f'w{wid}', g.interpolate(0.5, normalized=True), f"{t.get('highway', t.get('railway'))}-Brücke, {round(g.length)} m", w)
    elif t.get('tunnel') == 'culvert':
        g = way_geom(wid)
        if g is not None: add('Brücke', 'Durchlass', nm(t), f'w{wid}', g.interpolate(0.5, normalized=True), 'Rohrdurchlass unter dem Weg', w)
    elif t.get('leisure') in ('playground', 'pitch', 'fitness_station'):
        g = way_geom(wid)
        if g is not None and g.geom_type == 'Polygon':
            add({'playground': 'Spielplatz', 'pitch': 'Sportplatz', 'fitness_station': 'Fitness'}[t['leisure']], t.get('sport', t['leisure']), nm(t), f'w{wid}', g.representative_point(), f'{g.area:.0f} m²', w)
for wid, w in W.items():
    t = w['tags']; oid = f'w{wid}'
    if not t: continue
    g = way_geom(wid)
    if g is None: continue
    if t.get('natural') == 'water' or t.get('water'):
        if g.geom_type != 'Polygon': continue
        A = g.area; P = g.length; circ = 4 * math.pi * A / P**2 if P else 0; d = 2 * math.sqrt(A / math.pi)
        cand = 'Kandidat Bombentrichter (rund, klein) – DGM-Check' if (A < 600 and circ > 0.75) else ''
        add('Gewässer', t.get('water', 'Tümpel'), nm(t), oid, g, f'Fläche {A:.0f} m², Ø≈{d:.0f} m, Rundheit {circ:.2f}. {cand}', w)
    elif t.get('highway') == 'steps':
        add('Dünenübergang', 'Treppe', nm(t), oid, g, f"Länge {g.length:.0f} m, {t.get('surface', '')}", w)
    elif t.get('man_made') in ('lighthouse', 'tower') or t.get('building') in ('bunker',) or 'military' in t or 'ruins' in t:
        add('Bauwerk', t.get('man_made') or 'Bunker', nm(t), oid, g, t.get('description', ''), w)
    elif t.get('tourism') in ('hostel', 'hotel') or (t.get('building') and nm(t)):
        add('Unterkunft' if t.get('tourism') else 'Gebäude', t.get('tourism', t.get('building')), nm(t), oid, g, '', w)
    elif t.get('landuse') == 'forest' or t.get('natural') == 'wood':
        add('Vegetation', 'Wäldchen', nm(t), oid, g, f'{g.area/1e4:.2f} ha', w)
    elif t.get('landuse') == 'cemetery':
        add('Historisch', 'Friedhof', nm(t), oid, g, '', w)
    elif t.get('amenity') in ('restaurant', 'cafe'):
        add('Gastronomie', t['amenity'], nm(t), oid, g, '', w)
for rid, r in R.items():
    t = r['tags']
    if t.get('man_made') == 'observatory' or t.get('tourism') == 'hostel':
        add('Unterkunft', 'Jugendheim + Sternwarte', nm(t), f'r{rid}', rel_geom(rid), 'Start', r)
order = ['Unterkunft', 'Bauwerk', 'Gastronomie', 'Historisch', 'Gebäude', 'Einrichtung', 'Gelände', 'Gewässer', 'Baum', 'Vegetation', 'Dünenübergang', 'Durchgang', 'Rettungspunkt', 'Bank', 'Kleinobjekt',
         'km-Stein', 'Bahnübergang', 'Haltepunkt', 'Buhne', 'Brücke', 'Hydrant', 'Spielplatz', 'Sportplatz', 'Fitness', 'Recycling', 'Fahrradständer', 'Umspannstation']
pref = dict(Unterkunft='U', Bauwerk='B', Gastronomie='G', Historisch='H', Gebäude='GB', Einrichtung='E', Gelände='T', Gewässer='W', Baum='BA', Vegetation='V', Dünenübergang='D', Durchgang='DG', Rettungspunkt='R', Bank='BK', Kleinobjekt='K',
            **{'km-Stein': 'KM', 'Bahnübergang': 'BU', 'Haltepunkt': 'HP', 'Buhne': 'BH', 'Brücke': 'BR', 'Hydrant': 'HY', 'Spielplatz': 'SP', 'Sportplatz': 'SPO', 'Fitness': 'FI', 'Recycling': 'RE', 'Fahrradständer': 'FR', 'Umspannstation': 'US'})
rows.sort(key=lambda r: (order.index(r['kategorie']), -r['utm_n'] // 100, r['utm_e']))
cnt = {}
for r in rows:
    cnt[r['kategorie']] = cnt.get(r['kategorie'], 0) + 1; r['id'] = f"{pref[r['kategorie']]}{cnt[r['kategorie']]:03d}"
with open(BASE + '/out/landmarken_v0.csv', 'w', newline='', encoding='utf-8') as f:
    wr = csv.DictWriter(f, fieldnames=list(rows[0].keys())); wr.writeheader(); wr.writerows(rows)
json.dump(dict(type='FeatureCollection', features=feats), open(BASE + '/out/landmarken_v0.geojson', 'w'))
print(len(rows)); print({k: cnt.get(k, 0) for k in order})
