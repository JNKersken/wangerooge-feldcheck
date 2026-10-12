"""Terrain/aerial derived landmarks: dune summits, steep banks, distinct bushes, sand fences.
Outputs data/derived_points.json (list of point dicts) + data/steep_lines.geojson + data/sandfence.geojson"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import sys, json, math; None
import numpy as np, rasterio
from scipy.ndimage import gaussian_filter, maximum_filter, label, uniform_filter
from skimage.measure import regionprops
from rasterio.features import rasterize
from rasterio.transform import from_origin
from shapely.geometry import Point, LineString, mapping, box
from shapely.ops import unary_union
from geom import *
from dop import crop
F = box(423750, 5958850, 427150, 5961650)
src = rasterio.open(BASE + '/data/dgm_frame.tif'); z = src.read(1); tr = src.transform
zz = np.where(np.isnan(z), -5, z)
def excl_mask(shape, transform, road_buf=3.0, extra=()):
    gs = []
    for wid, w in W.items():
        t = w['tags']; g = way_geom(wid)
        if g is None: continue
        if 'building' in t and g.geom_type == 'Polygon': gs.append(g.buffer(2))
        if t.get('highway') in ('unclassified', 'residential', 'service', 'track', 'pedestrian') or t.get('railway') or t.get('man_made') in ('dyke', 'pier', 'groyne', 'breakwater'): gs.append(g.buffer(road_buf))
    gs += list(extra)
    return rasterize([(g, 1) for g in gs], out_shape=shape, transform=transform, fill=0).astype(bool)
EX = excl_mask(z.shape, tr, 3.0, [way_geom(w).buffer(10) for w, v in W.items() if v['tags'].get('man_made') == 'dyke' and way_geom(w) is not None])
out = []
# ---- 1) dune summits
zs = gaussian_filter(zz, 2)
BLD10 = rasterize([(way_geom(w).buffer(12), 1) for w, v in W.items() if 'building' in v['tags'] and way_geom(w) is not None and way_geom(w).geom_type == 'Polygon']
                  + [(way_geom(w), 1) for w, v in W.items() if v['tags'].get('landuse') in ('residential', 'commercial', 'industrial', 'allotments') and way_geom(w) is not None and way_geom(w).geom_type == 'Polygon'],
                  out_shape=z.shape, transform=tr, fill=0).astype(bool)
mx = (zs == maximum_filter(zs, size=41)) & (zs > 4) & ~EX & ~BLD10
summits = []
for r, c in zip(*np.nonzero(mx)):
    w = zs[max(0, r - 30):r + 31, max(0, c - 30):c + 31]
    prom = float(zs[r, c] - np.percentile(w, 20))
    if prom < 2.0: continue
    # real knoll: terrain must drop >=1.2 m within 25 m in (almost) every direction (excludes dyke crests / ridges)
    from scipy.ndimage import map_coordinates
    ang = np.linspace(0, 2 * np.pi, 16, endpoint=False); rad = np.arange(2, 26, 1.0)
    pr = r - np.outer(np.sin(ang), rad); pc = c + np.outer(np.cos(ang), rad)
    drop = zs[r, c] - map_coordinates(zs, [pr.ravel(), pc.ravel()], order=1, mode='nearest').reshape(16, -1).min(1)
    if (drop >= 1.2).sum() < 15: continue
    x, y = tr * (c + 0.5, r + 0.5)
    summits.append((x, y, float(z[r, c]), prom))
summits.sort(key=lambda s: -s[2]); keep = []
for s in summits:
    if all(math.hypot(s[0] - k[0], s[1] - k[1]) > 25 for k in keep): keep.append(s)
for x, y, h, prom in keep:
    out.append(dict(kategorie='Kuppe', typ='Dünenkuppe', name=f'{h:.0f}', x=x, y=y, status='sicher', quellen='Höhenmodell (LiDAR 2022)',
                    notiz=f'Höhe {h:.1f} m NHN, ragt {prom:.1f} m über die Umgebung', prom=round(prom, 1), z=round(h, 1)))
print('Kuppen', len(keep))
# ---- 2) steep banks (>35°)
SHORE = unary_union([way_geom(w) for w, v in W.items() if v['tags'].get('natural') == 'coastline' and way_geom(w) is not None])
gy, gx = np.gradient(gaussian_filter(zz, 1.5)); sl = np.degrees(np.arctan(np.hypot(gx, gy)))
steep = (sl > 35) & (zz > 1.5) & ~EX
lab, n = label(steep); lines = []
for rp in regionprops(lab):
    if rp.area < 15: continue
    cc = rp.coords
    # skip sea walls / Deckwerk: steep faces whose foot lies at beach level next to the shore
    zfoot = float(np.nanmin(zs[max(0, cc[:, 0].min() - 6):cc[:, 0].max() + 7, max(0, cc[:, 1].min() - 6):cc[:, 1].max() + 7]))
    if zfoot < 3.0: continue
    _p = Point(*(tr * (cc[:, 1].mean() + 0.5, cc[:, 0].mean() + 0.5)))
    if SHORE.distance(_p) < 70: continue   # promenade / sea wall faces along the shore
    pts = np.array([tr * (c + 0.5, r + 0.5) for r, c in cc])
    mu = pts.mean(0); u = np.linalg.svd(pts - mu)[2][0]; proj = (pts - mu) @ u
    a, b = mu + u * proj.min(), mu + u * proj.max()
    if np.hypot(*(b - a)) < 6: continue
    # downslope direction: mean of -gradient (row axis points south)
    dx = -float(np.mean(gx[cc[:, 0], cc[:, 1]])); dy = float(np.mean(gy[cc[:, 0], cc[:, 1]]))
    nrm = math.hypot(dx, dy) or 1
    # shift line to the top edge (half the region width upslope)
    wid = float(np.ptp((pts - mu) @ np.array([-u[1], u[0]]))) / 2
    off = np.array([-dx / nrm, -dy / nrm]) * wid * 0.6
    ln = LineString([tuple(a + off), tuple(b + off)])
    h = float(np.nanmax(z[cc[:, 0], cc[:, 1]]) - np.nanmin(z[cc[:, 0], cc[:, 1]]))
    lines.append(dict(type='Feature', geometry=mapping(ln), properties=dict(dx=dx / nrm, dy=dy / nrm, len=round(ln.length, 1), h=round(h, 1))))
    mid = ln.interpolate(0.5, normalized=True)
    out.append(dict(kategorie='Steilhang', typ='Steilhang / Abbruchkante', name='', x=mid.x, y=mid.y, status='sicher', quellen='Höhenmodell (LiDAR 2022)',
                    notiz=f'Länge {ln.length:.0f} m, Höhenunterschied {h:.1f} m, steiler als 35°'))
json.dump(dict(type='FeatureCollection', features=lines), open(BASE + '/data/steep_lines.geojson', 'w'))
print('Steilhänge', len(lines))
BUSHES = False
# ---- 3) distinct bushes (DOP): dark-green compact blobs in open terrain, isolated
veg = []
for wid, w in W.items():
    t = w['tags']
    if t.get('natural') in ('scrub', 'wood', 'water', 'wetland') or t.get('landuse') in ('forest', 'residential', 'allotments', 'cemetery') or t.get('leisure'):
        g = way_geom(wid)
        if g is not None and g.geom_type == 'Polygon': veg.append(g.buffer(4))
for rid, r in R.items():
    if r['tags'].get('natural') in ('scrub', 'wood') or r['tags'].get('landuse') == 'forest':
        g = rel_geom(rid)
        if g is not None: veg.append(g.buffer(4))
RES = 0.4; bushes = []
for tx in (range(423750, 427150, 500) if BUSHES else []):
    for ty in range(5958850, 5961650, 500):
        img = crop(tx, ty, tx + 500, ty + 500, RES).astype(float); H_, W_ = img.shape[:2]
        trd = from_origin(tx, ty + 500, RES, RES)
        R_, G_, B_ = img[..., 0], img[..., 1], img[..., 2]; L = img.mean(2)
        exg = 2 * G_ - R_ - B_
        Lm = uniform_filter(L, 41)
        cand = (exg > 12) & (L < Lm - 18) & (G_ >= R_)
        ex = excl_mask((H_, W_), trd, 3.0, veg)
        zt = rasterio.open(BASE + '/data/dgm_frame.tif')
        cand &= ~ex
        lab2, _ = label(cand)
        for rp in regionprops(lab2):
            A = rp.area * RES * RES
            if A < 4 or A > 70 or rp.eccentricity > 0.9 or rp.solidity < 0.75: continue
            r0, c0 = rp.centroid; x, y = trd * (c0 + 0.5, r0 + 0.5)
            # z must be above sea (not in Watt)
            rr, cc_ = src.index(x, y)
            if not (0 <= rr < z.shape[0] and 0 <= cc_ < z.shape[1]) or not (z[rr, cc_] > 1.5): continue
            bushes.append((x, y, A))
# isolation: no other bush (or veg polygon) within 10 m
veg_u = unary_union(veg) if veg else None
iso = []
for i, (x, y, A) in enumerate(bushes):
    if any(j != i and math.hypot(x - bx, y - by) < 10 for j, (bx, by, _) in enumerate(bushes)): continue
    if veg_u is not None and veg_u.distance(Point(x, y)) < 6: continue
    iso.append((x, y, A))
for x, y, A in iso:
    out.append(dict(kategorie='Busch', typ='Markanter Busch', name='', x=x, y=y, status='prüfen', quellen='Luftbild (19.10.2025)',
                    notiz=f'einzeln stehender Busch, ca. {2 * math.sqrt(A / math.pi):.0f} m Durchmesser'))
print('Büsche', len(bushes), 'davon markant/isoliert', len(iso))
json.dump(out, open(BASE + '/data/derived_points.json', 'w'))
