"""Crater detection by radial-rise test around local minima (robust when pits sit inside larger basins).
For each local min of smoothed DGM: in 16 directions the terrain must rise >= RISE within R metres."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import sys, json, csv, math; None
import numpy as np, rasterio
from scipy.ndimage import gaussian_filter, minimum_filter, map_coordinates
from rasterio.features import rasterize
from shapely.geometry import Point, Polygon, mapping
from geom import *
RISE, R, NDIR, NEED = 0.45, 12, 16, 14
src = rasterio.open(BASE + '/data/dgm_frame.tif'); z = src.read(1); tr = src.transform
zs = gaussian_filter(np.where(np.isnan(z), -5, z), 1.0)
excl = []
for wid, w in W.items():
    t = w['tags']; g = way_geom(wid)
    if g is None: continue
    if 'building' in t and g.geom_type == 'Polygon': excl.append(g.buffer(3))
    if t.get('highway') in ('unclassified', 'residential', 'service', 'track') or t.get('railway') or t.get('waterway') or t.get('man_made') in ('dyke', 'groyne', 'pier', 'breakwater'): excl.append(g.buffer(4))
from scipy.ndimage import label as _lab
low = np.isnan(z) | (zs < 1.2)
lab_, _n = _lab(low)
edge = set(np.unique(np.concatenate([lab_[0], lab_[-1], lab_[:, 0], lab_[:, -1]]))) | set(np.unique(lab_[np.isnan(z)]))
edge.discard(0)
sea = np.isin(lab_, list(edge))          # only low ground connected to the sea / Watt
ex = rasterize([(g, 1) for g in excl], out_shape=z.shape, transform=tr, fill=0).astype(bool) | sea
mins = (zs == minimum_filter(zs, size=7)) & ~ex
rr, cc = np.nonzero(mins)
ang = np.linspace(0, 2 * np.pi, NDIR, endpoint=False); rad = np.arange(1, R + 1, 0.5)
out = []
for r0, c0 in zip(rr, cc):
    z0 = zs[r0, c0]
    pr = r0 - np.outer(np.sin(ang), rad); pc = c0 + np.outer(np.cos(ang), rad)
    prof = map_coordinates(zs, [pr.ravel(), pc.ravel()], order=1, mode='nearest').reshape(NDIR, -1) - z0
    rise = prof.max(axis=1)
    if (rise >= RISE).sum() < NEED: continue
    # rim radius per direction: first radius reaching 80% of that direction's max rise
    rim = np.array([rad[np.argmax(p >= 0.8 * m)] for p, m in zip(prof, rise)])
    d = 2 * float(np.median(rim)); depth = float(np.median(rise))
    rt = np.sort(rim)[:12]   # trimmed: ignore the 4 directions that run into neighbouring pits
    cv = float(np.std(rt) / np.mean(rt)); uni = float(np.sort(rise)[1] / np.median(rise))
    # wall steepness: rise reached within rim radius
    if d < 3 or d > 26: continue
    x, y = tr * (c0 + 0.5, r0 + 0.5)
    poly = Polygon([(x + rm * math.cos(a), y + rm * math.sin(a)) for rm, a in zip(rim, ang)])
    out.append(dict(x=round(x, 1), y=round(y, 1), d=round(d, 1), tiefe=round(depth, 2), z_boden=round(float(z0), 2), cv=round(cv, 2), uni=round(uni, 2), td=round(depth / d, 3), poly=poly))
# classify: crater-like = round rim (low cv) + rise in all directions (uni) + steep bowl (td)
for o in out:
    if o['cv'] <= 0.22 and o['uni'] >= 0.6 and o['td'] >= 0.09: o['klasse'] = 'deutlich'
    elif o['cv'] <= 0.28 and o['uni'] >= 0.45 and o['td'] >= 0.035: o['klasse'] = 'wahrscheinlich'
    else: o['klasse'] = ''
out = [o for o in out if o['klasse']]
# dedupe: keep deepest within 5 m
out.sort(key=lambda o: -o['tiefe']); keep = []
for o in out:
    if all(math.hypot(o['x'] - k['x'], o['y'] - k['y']) > max(5, 0.6 * k['d']) for k in keep): keep.append(o)
# link OSM ponds
ponds = [(f'w{wid}', way_geom(wid)) for wid, w in W.items() if w['tags'].get('natural') == 'water']
ponds = [(i, g) for i, g in ponds if g is not None and g.geom_type == 'Polygon' and g.area < 800]
for k in keep:
    k['osm'] = next((i for i, g in ponds if g.buffer(2).contains(Point(k['x'], k['y']))), '')
    k['quelle'] = 'DGM+OSM(Wasser)' if k['osm'] else 'DGM'
used = {k['osm'] for k in keep}
for i, g in ponds:
    circ = 4 * math.pi * g.area / g.length**2
    if i not in used and circ > 0.7:
        c = g.centroid; keep.append(dict(x=round(c.x, 1), y=round(c.y, 1), d=round(2 * math.sqrt(g.area / math.pi), 1), tiefe='', z_boden='', cv='', uni='', td='', klasse='Wasser', poly=g, osm=i, quelle='OSM(Wasser)'))
json.dump(dict(type='FeatureCollection', features=[dict(type='Feature', geometry=mapping(k['poly']), properties={a: b for a, b in k.items() if a != 'poly'}) for k in keep]),
          open(BASE + '/data/craters.geojson', 'w'))
with open(BASE + '/data/craters.csv', 'w', newline='') as f:
    flds = ['x', 'y', 'd', 'tiefe', 'z_boden', 'cv', 'uni', 'td', 'klasse', 'quelle', 'osm']; wr = csv.DictWriter(f, fieldnames=flds); wr.writeheader()
    for k in keep: wr.writerow({a: k[a] for a in flds})
import collections
print('Kandidaten', len(keep), collections.Counter(k['quelle'] for k in keep))
print(collections.Counter(k['klasse'] for k in keep)); print('Ø-Verteilung', sorted(collections.Counter(int(k['d'] // 4 * 4) for k in keep).items()))
