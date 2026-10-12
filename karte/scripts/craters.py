"""Crater candidates from local relief model (LRM<thr), shape-filtered; masks buildings/roads/watt.
Merges OSM water polygons that are round & small. Output: data/craters.geojson/csv"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import sys, json, csv, math; None
import numpy as np, rasterio
from rasterio.features import rasterize, shapes
from skimage.measure import label, regionprops
from shapely.geometry import shape, mapping, Point
from shapely.ops import unary_union
from geom import *
src = rasterio.open(BASE + '/data/dgm_frame.tif'); z = src.read(1); tr = src.transform
from scipy.ndimage import grey_closing
from skimage.morphology import disk
zz = np.where(np.isnan(z), -5, z)
th = grey_closing(zz, footprint=disk(10)) - zz   # black top-hat: pits narrower than ~20 m
np.save(BASE + '/data/tophat.npy', th.astype('float32'))
lrm = -th
excl = []
for wid, w in W.items():
    t = w['tags']; g = way_geom(wid)
    if g is None: continue
    if 'building' in t and g.geom_type == 'Polygon': excl.append(g.buffer(2))
    if t.get('highway') in ('unclassified', 'residential', 'service', 'track') or t.get('railway') or t.get('waterway') or t.get('man_made') in ('dyke', 'groyne', 'pier', 'breakwater'):
        excl.append(g.buffer(4))
mask_ex = rasterize([(g, 1) for g in excl], out_shape=z.shape, transform=tr, fill=0).astype(bool)
mask_ex |= np.isnan(z) | (z < 1.2)   # sea / watt below ~MHW
pit = (th > 0.30) & ~mask_ex
lab = label(pit, connectivity=1)
rows = []; feats = []
for r in regionprops(lab, intensity_image=-np.nan_to_num(lrm)):
    A = r.area
    if A < 12 or A > 700: continue
    P = r.perimeter or 1; circ = min(1, 4 * math.pi * A / P**2); deq = 2 * math.sqrt(A / math.pi)
    depth = float(r.intensity_max)
    if circ < 0.55 or r.eccentricity > 0.85 or depth < 0.45 or r.solidity < 0.8: continue
    m = (lab[r.slice] == r.label).astype('uint8')
    st = tr * rasterio.Affine.translation(r.slice[1].start, r.slice[0].start)
    g = max((shape(q) for q, v in shapes(m, mask=m.astype(bool), transform=st) if v == 1), key=lambda q: q.area)
    c = g.centroid
    rows.append(dict(x=round(c.x, 1), y=round(c.y, 1), d=round(deq, 1), tiefe=round(depth, 2), rund=round(circ, 2), quelle='DGM', osm=''))
    feats.append((g, rows[-1]))
# OSM water polygons: round & small -> crater (water-filled); attach to DGM hit if overlapping
for wid, w in W.items():
    t = w['tags']
    if t.get('natural') != 'water': continue
    g = way_geom(wid)
    if g is None or g.geom_type != 'Polygon': continue
    A = g.area; circ = 4 * math.pi * A / g.length**2
    if A > 700 or circ < 0.7: continue
    hit = [i for i, (fg, _) in enumerate(feats) if fg.intersects(g)]
    if hit:
        for i in hit: feats[i][1]['quelle'] = 'DGM+OSM(Wasser)'; feats[i][1]['osm'] = f'w{wid}'
    else:
        c = g.centroid; deq = 2 * math.sqrt(A / math.pi)
        rows.append(dict(x=round(c.x, 1), y=round(c.y, 1), d=round(deq, 1), tiefe='', rund=round(circ, 2), quelle='OSM(Wasser)', osm=f'w{wid}'))
        feats.append((g, rows[-1]))
json.dump(dict(type='FeatureCollection', features=[dict(type='Feature', geometry=mapping(g), properties=p) for g, p in feats]),
          open(BASE + '/data/craters.geojson', 'w'))
with open(BASE + '/data/craters.csv', 'w', newline='') as f:
    wr = csv.DictWriter(f, fieldnames=list(rows[0].keys())); wr.writeheader(); wr.writerows(rows)
import collections
print(len(rows), collections.Counter(r['quelle'] for r in rows))
print('Durchmesser-Verteilung', sorted(collections.Counter(int(r['d'] // 5 * 5) for r in rows).items()))
