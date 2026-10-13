"""App icon: Wangerooge-West relief (terraced elevation layers) on a sea gradient, orienteering control flag at the start (Inselheim)."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import numpy as np, rasterio
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch, FancyBboxPatch, Polygon as MPoly
from matplotlib.path import Path
from scipy.ndimage import gaussian_filter
from skimage.measure import find_contours
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from PIL import Image

src = rasterio.open(BASE + '/data/dgm_frame.tif'); Z = src.read(1); tr = src.transform
Z = np.where(np.isnan(Z), -3, Z); Zs = gaussian_filter(Z, 10)   # strong smoothing: clean, icon-like coastline
def level(th):
    m = (Zs > th).astype('uint8')
    from rasterio.features import shapes
    from shapely.geometry import shape
    g = unary_union([shape(s) for s, v in shapes(m, mask=m.astype(bool), transform=tr) if v == 1])
    g = g.buffer(0).simplify(6)
    return MultiPolygon([Polygon(p.exterior) for p in getattr(g, 'geoms', [g]) if p.area > 40000])   # no islets, no holes
LV = [(1.0, '#ead6aa'), (8.0, '#f7ecd2')]
geoms = [(level(t), c) for t, c in LV]

S = 1024
# view: west part of the island, running off the right edge
x0, x1 = 423930, 426980; cx = (x0 + x1) / 2; cy = 5960150; half = (x1 - x0) / 2
fig = plt.figure(figsize=(S / 100, S / 100), dpi=100); ax = fig.add_axes([0, 0, 1, 1]); ax.axis('off')
ax.set_xlim(cx - half, cx + half); ax.set_ylim(cy - half, cy + half); ax.set_aspect('equal')
yy, xx = np.mgrid[0:1:256j, 0:1:256j]; t = np.clip(xx * 0.45 + yy * 0.55, 0, 1)   # light top-left -> deep bottom-right
c0, c1 = np.array([0x1f, 0x8a, 0x93]) / 255, np.array([0x0b, 0x33, 0x45]) / 255
grad = c0[None, None, :] * (1 - t[..., None]) + c1[None, None, :] * t[..., None]
ax.imshow(grad, extent=(cx - half, cx + half, cy - half, cy + half), origin='upper', zorder=0)
def patch(g, **kw):
    verts, codes = [], []
    for p in getattr(g, 'geoms', [g]):
        for ring in [p.exterior] + list(p.interiors):
            c = list(ring.coords); verts += c; codes += [Path.MOVETO] + [Path.LINETO] * (len(c) - 2) + [Path.CLOSEPOLY]
    return PathPatch(Path(verts, codes), **kw)
from shapely import affinity
def smooth(g, r):   # close inlets, then open spikes; keep outer rings only
    g = g.buffer(r, quad_segs=16).buffer(-2 * r, quad_segs=16).buffer(r, quad_segs=16)
    return MultiPolygon([Polygon(p.exterior) for p in getattr(g, 'geoms', [g]) if p.area > 40000])
land = smooth(geoms[0][0], 50)
ax.add_patch(patch(affinity.translate(land.buffer(10), 18, -26), fc='#04202b', ec='none', alpha=0.35, zorder=1))   # soft drop shadow
ax.add_patch(patch(land, fc=geoms[0][1], ec='none', zorder=2))
ax.add_patch(patch(smooth(geoms[1][0], 25).intersection(land.buffer(-25)), fc=geoms[1][1], ec='none', zorder=3))
# orienteering course overprint: start triangle -> controls, magenta like a real OL course
MAG = '#e0237f'; lw = S * 0.018; m_per_px = 2 * half / S
st = (424335, 5960270); c1_ = (425250, 5960990); c2_ = (426470, 5960930)
rT, rC = 62 * m_per_px, 52 * m_per_px
import math
def seg(a, b, ra, rb):
    dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy); ux, uy = dx / L, dy / L
    return [(a[0] + ux * ra, a[1] + uy * ra), (b[0] - ux * rb, b[1] - uy * rb)]
for a, b, ra, rb in ((st, c1_, rT * 1.05, rC * 1.35), (c1_, c2_, rC * 1.35, rC * 1.35)):
    (xa, ya), (xb, yb) = seg(a, b, ra, rb)
    ax.plot([xa, xb], [ya, yb], color='white', lw=lw * 2.2, solid_capstyle='round', zorder=6, alpha=0.9)
    ax.plot([xa, xb], [ya, yb], color=MAG, lw=lw, solid_capstyle='round', zorder=7)
ang = math.atan2(c1_[1] - st[1], c1_[0] - st[0])
tri = [(st[0] + rT * math.cos(ang + k * 2 * math.pi / 3), st[1] + rT * math.sin(ang + k * 2 * math.pi / 3)) for k in range(3)]
for colr, w in (('white', lw * 2.2), (MAG, lw)):
    ax.add_patch(MPoly(tri, closed=True, fc='none', ec=colr, lw=w, joinstyle='round', zorder=6 if colr == 'white' else 7))
for c in (c1_, c2_):
    for colr, w in (('white', lw * 2.2), (MAG, lw)):
        ax.add_patch(matplotlib.patches.Circle(c, rC, fc='none', ec=colr, lw=w, zorder=6 if colr == 'white' else 7))
out = BASE + '/web/icon-1024.png'
fig.savefig(out, dpi=100); plt.close(fig)
im = Image.open(out).convert('RGB')
for sz, name in ((512, 'icon-512.png'), (192, 'icon-192.png'), (180, 'apple-touch-icon.png'), (32, 'favicon-32.png')):
    im.resize((sz, sz), Image.LANCZOS).save(BASE + '/web/' + name)
print('icons ok')
