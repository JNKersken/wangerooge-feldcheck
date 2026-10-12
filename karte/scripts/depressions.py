"""Detect closed depressions (crater candidates) in DGM1: sink-fill by morphological reconstruction,
label depth>thr regions, compute shape metrics, write GeoJSON + CSV."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import numpy as np, rasterio, json, csv, math
from skimage.morphology import reconstruction
from skimage.measure import label, regionprops
from shapely.geometry import shape, mapping, Point
from rasterio.features import shapes
src = rasterio.open(BASE + '/data/dgm_frame.tif'); z = src.read(1); tr = src.transform
valid = ~np.isnan(z)
zf = np.where(valid, z, -10.0)  # NaN (sea) as low outlet
seed = zf.copy(); seed[1:-1, 1:-1] = zf.max()
filled = reconstruction(seed, zf, method='erosion')
depth = np.where(valid, filled - zf, 0)
np.save(BASE + '/data/sinkdepth.npy', depth.astype('float32'))
lab = label(depth > 0.25, connectivity=2)
rows = []; feats = []
for r in regionprops(lab, intensity_image=depth):
    A = r.area
    if A < 8 or A > 5000: continue
    dmax = r.intensity_max
    if dmax < 0.4: continue
    P = r.perimeter or 1; circ = min(1.0, 4 * math.pi * A / P**2)
    deq = 2 * math.sqrt(A / math.pi)
    cy, cx = r.centroid; x, y = tr * (cx + 0.5, cy + 0.5)
    zmin = float(np.nanmin(z[r.slice][r.image])); zrim = zmin + dmax
    # crater score: round, 4-30 m, depth/diam ratio
    ratio = dmax / deq
    is_cand = (circ > 0.55 and 4 <= deq <= 30 and ratio > 0.04 and r.eccentricity < 0.85)
    mask = (lab[r.slice] == r.label).astype('uint8')
    sub_tr = tr * rasterio.Affine.translation(r.slice[1].start, r.slice[0].start)
    geoms = [shape(g) for g, v in shapes(mask, mask=mask.astype(bool), transform=sub_tr) if v == 1]
    g = max(geoms, key=lambda q: q.area)
    rows.append(dict(x=round(x, 1), y=round(y, 1), flaeche=int(A), d_eq=round(deq, 1), tiefe=round(float(dmax), 2), z_boden=round(zmin, 2),
                     rund=round(circ, 2), exz=round(float(r.eccentricity), 2), t_d=round(ratio, 3), kandidat=bool(is_cand)))
    feats.append(dict(type='Feature', geometry=mapping(g), properties=rows[-1]))
json.dump(dict(type='FeatureCollection', features=feats), open(BASE + '/data/depressions.geojson', 'w'))
with open(BASE + '/data/depressions.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print('Senken gesamt', len(rows), 'Trichter-Kandidaten', sum(r['kandidat'] for r in rows))
import collections
print(collections.Counter((round(r['d_eq']/5)*5) for r in rows if r['kandidat']))
