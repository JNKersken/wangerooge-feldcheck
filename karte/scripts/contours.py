"""2.5 m contours from DGM1 (smoothed), generalized; drop tiny closed rings (pits are symbols). -> data/contours.geojson"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import json, numpy as np, rasterio
from scipy.ndimage import gaussian_filter
from skimage.measure import find_contours
from shapely.geometry import LineString, mapping
src = rasterio.open(BASE + '/data/dgm_frame.tif'); z = src.read(1); tr = src.transform
v = ~np.isnan(z)
zz = np.where(v, z, -3.0)
zs = gaussian_filter(zz, 2.5)
w = gaussian_filter(v.astype(float), 2.5); zs = np.where(w > 0.5, gaussian_filter(np.where(v, z, 0), 2.5) / np.maximum(w, 1e-6), -3)
feats = []; stats = {}
for lev in np.arange(2.5, 20.01, 2.5):
    n = 0
    for c in find_contours(zs, lev):
        if len(c) < 3: continue
        pts = [tr * (cc + 0.5, rr + 0.5) for rr, cc in c]
        ln = LineString(pts).simplify(0.6)
        closed = c[0].tolist() == c[-1].tolist() or ln.coords[0] == ln.coords[-1]
        if ln.length < (40 if closed else 15): continue
        idx = abs(lev % 12.5) < 1e-6
        feats.append(dict(type='Feature', geometry=mapping(ln), properties=dict(z=float(lev), index=bool(idx), closed=bool(closed))))
        n += 1
    stats[float(lev)] = n
json.dump(dict(type='FeatureCollection', features=feats), open(BASE + '/data/contours.geojson', 'w'))
print(stats, 'gesamt', len(feats))
