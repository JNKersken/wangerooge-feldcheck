"""Hand-drawn style orienteering map renderer (A4 PDF/PNG).
Usage: render_map.py <sheet> <color|bw> <out.pdf> [png]
Sheets defined in SHEETS. All symbol sizes are in paper millimetres."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import sys, os, json, math, hashlib
None
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Polygon as MPoly
import matplotlib.patheffects as pe
from shapely.geometry import box, shape, LineString, Point, Polygon, MultiLineString
from shapely.ops import unary_union
from shapely import affinity
from scipy.ndimage import gaussian_filter
from skimage.measure import find_contours
import rasterio
from geom import *
import symbols2
USE_B = True

FD = BASE + '/fonts/'
for f in ('Caveat-Medium.ttf', 'Caveat-Bold.ttf', 'PatrickHand.ttf'): fm.fontManager.addfont(FD + f)
HAND = fm.FontProperties(fname=FD + 'Caveat-Medium.ttf')
HANDB = fm.FontProperties(fname=FD + 'Caveat-Bold.ttf')
PRINT = fm.FontProperties(fname=FD + 'PatrickHand.ttf')
for f in ('PTSerif-Bold.ttf', 'PTSerif-Regular.ttf'): fm.fontManager.addfont(FD + f)
SERIF = fm.FontProperties(fname=FD + 'PTSerif-Bold.ttf')

SHEETS = {
    'uebersicht': dict(bbox=(423750, 5958850, 427150, 5961650), scale=15000, orient='L', title='Wangerooge West', sub='Übersicht'),
    'detail_west': dict(bbox=(423950, 5960080, 425335, 5960970), scale=5000, orient='L', title='Wangerooge West', sub='Blatt 1 · Westen & Westgroden'),
    'detail_mitte': dict(bbox=(424735, 5960450, 426120, 5961340), scale=5000, orient='L', title='Wangerooge West', sub='Blatt 2 · Norddünen Mitte'),
    'detail_sued': dict(bbox=(424160, 5958870, 425570, 5960850), scale=7500, orient='P', title='Wangerooge West', sub='Blatt 4 · Inselheim bis Westanleger'),
    'detail_ost': dict(bbox=(425765, 5960380, 427150, 5961270), scale=5000, orient='L', title='Wangerooge West', sub='Blatt 3 · Norddünen Ost'),
}
SEA_Z = 0.5
HALO_A = 0.55   # semi-transparent text halo: covered linework stays faintly visible
PAL = {
    'color': dict(ink='#1d1d1f', gray='#9b9b9b', brown='#b0662a', blue='#2f7fc1', water='#d3e9f6', sea='#e3f0f8', open='#fbefb8',
                  green='#3f9b4a', purple='#9b3fb5', sand='#c9a86a', paper='#fffdf7', marsh='#5aa0d0', count='#8e1b1b', contour='#dcb48f', pit='#d4a37e'),
    'bw': dict(ink='#111111', gray='#8a8a8a', brown='#555555', blue='#333333', water='#e6e6e6', sea='#f0f0f0', open='#ffffff',
               green='#444444', purple='#555555', sand='#777777', paper='#ffffff', marsh='#555555', count='#000000', contour='#b2b2b2', pit='#7c7c7c'),
}

# ---------- map layers: every drawn artist gets an SVG id "L-<layer>-<n>" so the web app can switch layers on/off ----------
LAYERS = [  # (key, label, group)
    ('contours', 'Höhenlinien', 'Gelände'), ('summits', 'Dünenkuppen mit Höhe', 'Gelände'), ('steep', 'Steilhänge', 'Gelände'), ('pits', 'Gruben / Bombentrichter', 'Gelände'),
    ('sea', 'Meer / Watt', 'Flächen & Wasser'), ('water', 'Tümpel, Gräben, Salzwiese', 'Flächen & Wasser'), ('open', 'Offene Wiese', 'Flächen & Wasser'),
    ('veg', 'Gebüsch / Wäldchen', 'Flächen & Wasser'), ('sand', 'Sand / Strand', 'Flächen & Wasser'), ('ruhezone', 'Ruhezone', 'Flächen & Wasser'),
    ('roads', 'Straßen / Hauptwege', 'Wege & Bauwerke'), ('paths', 'Fußwege, Pfade, Treppen, Stege', 'Wege & Bauwerke'), ('rail', 'Inselbahn mit Haltepunkten & km-Steinen', 'Wege & Bauwerke'),
    ('buildings', 'Gebäude & Sportplätze', 'Wege & Bauwerke'), ('structures', 'Deiche, Zäune, Buhnen', 'Wege & Bauwerke'),
    ('bench', 'Bänke', 'Punkte'), ('rescue', 'SOS-Schilder mit Nummer', 'Punkte'), ('shelter', 'Schutzhütten', 'Punkte'), ('gate', 'Tore / Durchlässe', 'Punkte'),
    ('info', 'Infotafeln, Wegweiser, Gedenkstätten', 'Punkte'), ('landmarks', 'Leuchttürme, Sternwarte, Aussichtsdüne, Gastronomie', 'Punkte'),
    ('facilities', 'WC, Rettungsringe, Feuerstellen, Spiel & Sport', 'Punkte'), ('small', 'Hydranten, Container, Fahrradständer, Trafo', 'Punkte'),
    ('field', 'Findlinge, Pfähle, Schilder (vor Ort erfasst)', 'Punkte'),
    ('labels', 'Ortsnamen', 'Karte'), ('north', 'Nordlinien', 'Karte'), ('lupen', 'Lupen (Ausschnittvergrößerungen)', 'Karte'), ('sheetindex', 'Blattschnitte (nur Übersicht)', 'Karte'),
]
KIND_LAYER = dict(bench='bench', rescue='rescue', shelter='shelter', gate='gate', info='info', flag='info', memorial='info',
                  lighthouse='landmarks', observatory='landmarks', peak='landmarks', food='landmarks',
                  toilet='facilities', ring='facilities', fire='facilities', picnic='facilities', playground='facilities', fitness='facilities', mast='facilities', tree='facilities', dot='facilities', ferry='landmarks',
                  hydrant='small', recycling='small', bike='small', substation='small', milestone='rail', railx='rail', station='rail',
                  groyne='structures', summit='summits', pit='pits', bush='veg',
                  rzsign='ruhezone', rzpost='ruhezone', beachaccess='paths', boardwalk='paths', boulder='field', post='field', flagpole='field', sign='field',
                  pond='water', steeppt='steep', sandfence='structures')
_TAGN = [0]
class _Tag:
    """Tag every artist added to ax inside the block (nested tags win; ids stay stable within one render)."""
    def __init__(self, ax, key): self.ax, self.key = ax, key
    def _lists(self): a = self.ax; return (a.lines, a.patches, a.collections, a.texts, a.images)
    def __enter__(self): self.n = [len(l) for l in self._lists()]; return self
    def __exit__(self, *exc):
        for lst, n0 in zip(self._lists(), self.n):
            for art in list(lst)[n0:]:
                if not (art.get_gid() or '').startswith('L-'):
                    _TAGN[0] += 1; art.set_gid(f'L-{self.key}-{_TAGN[0]}')
def tag(S, key): return _Tag(S.ax, key)

def mix(c, paper, t):
    """Blend colour c towards paper by fraction t (0 = unchanged)."""
    if not t: return c
    from matplotlib.colors import to_rgb, to_hex
    a, b = to_rgb(c), to_rgb(paper)
    return to_hex(tuple(a[i] * (1 - t) + b[i] * t for i in range(3)))

class Sheet:
    def __init__(s, name, mode):
        cfg = SHEETS[name]; s.cfg = cfg; s.mode = mode; s.P = PAL[mode]
        s.x0, s.y0, s.x1, s.y1 = cfg['bbox']; s.scale = cfg['scale']
        s.pw, s.ph = (297, 210) if cfg['orient'] == 'L' else (210, 297)
        s.m = s.scale / 1000.0  # metres per paper-mm
        s.mw, s.mh = (s.x1 - s.x0) / s.m, (s.y1 - s.y0) / s.m  # map size in mm
        s.fig = plt.figure(figsize=(s.pw / 25.4, s.ph / 25.4))
        s.fig.patch.set_facecolor(s.P['paper'])
        if name == 'uebersicht':
            s.mx, s.my = 8, (s.ph - s.mh) / 2
        elif cfg['orient'] == 'L':
            s.mx, s.my = (s.pw - s.mw) / 2, 22
        else:
            s.mx, s.my = (s.pw - s.mw) / 2, 22
        s.ax = s.fig.add_axes([s.mx / s.pw, s.my / s.ph, s.mw / s.pw, s.mh / s.ph])
        s.ax.set_xlim(s.x0, s.x1); s.ax.set_ylim(s.y0, s.y1); s.ax.set_aspect('equal'); s.ax.axis('off')
        s.ax.set_facecolor(s.P['paper'])
        s.clip = box(s.x0, s.y0, s.x1, s.y1)
        s.pt = 25.4 / 72  # mm per point
        s.dense = s.scale <= 7500
        s.wobf = 0.3   # positional accuracy: wobble max ~0.1 mm on paper

    # ---------- hand-drawn primitives ----------
    def rng(s, key):
        return np.random.default_rng(int(hashlib.md5(str(key).encode()).hexdigest()[:8], 16))
    def wob(s, coords, key, amp=0.22, step=1.2):
        """Resample line every `step` mm and add smooth perpendicular wobble of `amp` mm (scaled by s.wobf)."""
        amp = amp * getattr(s, 'wobf', 1.0)
        c = np.asarray(coords, float)
        if len(c) < 2: return c
        seg = np.hypot(*np.diff(c, axis=0).T); L = seg.sum()
        if L == 0: return c
        st = min(step * s.m, L / 18); n = max(2, int(L / st) + 1)
        d = np.concatenate([[0], np.cumsum(seg)]); t = np.linspace(0, L, n)
        x = np.interp(t, d, c[:, 0]); y = np.interp(t, d, c[:, 1])
        dx, dy = np.gradient(x), np.gradient(y); nn = np.hypot(dx, dy) + 1e-9; nx, ny = -dy / nn, dx / nn
        r = s.rng(key); off = np.zeros(n)
        for k in range(3):
            wl = (8 + 14 * r.random()) * s.m * (k + 1) ** -0.6
            off += np.sin(2 * np.pi * t / wl + r.random() * 6.28) * amp * s.m / (k + 1)
        return np.column_stack([x + nx * off, y + ny * off])
    def line(s, coords, key, color, lw, amp=0.22, ls='-', alpha=1, double=True, z=3, dashes=None):
        c = s.wob(coords, key, amp)
        kw = dict(color=color, lw=lw, alpha=alpha, solid_capstyle='round', zorder=z)
        if dashes: kw['dashes'] = dashes
        else: kw['ls'] = ls
        s.ax.plot(c[:, 0], c[:, 1], **kw)
        if double and lw >= 0.5:
            c2 = s.wob(coords, str(key) + 'b', amp * 0.8)
            kw2 = dict(kw); kw2['lw'] = lw * 0.45; kw2['alpha'] = alpha * 0.55
            s.ax.plot(c2[:, 0], c2[:, 1], **kw2)
    def geomlines(s, g):
        if g.is_empty: return []
        if g.geom_type == 'LineString': return [g]
        if g.geom_type == 'Polygon': return [LineString(g.exterior.coords)] + [LineString(i.coords) for i in g.interiors]
        return [q for p in getattr(g, 'geoms', []) for q in s.geomlines(p)]
    def gline(s, g, key, color, lw, **kw):
        g = g.intersection(s.clip.buffer(5))
        for i, ln in enumerate(s.geomlines(g)):
            if ln.length > 0: s.line(list(ln.coords), f'{key}-{i}', color, lw, **kw)
    def fill(s, g, color, alpha=1, z=1):
        g = g.intersection(s.clip.buffer(5))
        for p in getattr(g, 'geoms', [g]):
            if p.geom_type != 'Polygon' or p.is_empty: continue
            c = s.wob(list(p.exterior.coords), 'f%.0f_%.0f_%.0f' % (p.bounds[0], p.bounds[1], p.area), 0.3)   # deterministic wobble
            s.ax.add_patch(MPoly(c, closed=True, fc=color, ec='none', alpha=alpha, zorder=z))
    def hatch(s, g, key, color, spacing=1.3, angle=45, lw=0.35, z=2, alpha=1, cross=False):
        g = g.intersection(s.clip.buffer(5))
        if g.is_empty: return
        gx0, gy0, gx1, gy1 = g.bounds; cx, cy = (gx0 + gx1) / 2, (gy0 + gy1) / 2; R = math.hypot(gx1 - gx0, gy1 - gy0) / 2 + 5
        sp = spacing * s.m
        for a in ([angle, angle + 90] if cross else [angle]):
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            k = 0
            for o in np.arange(-R, R, sp):
                ln = LineString([(cx - R * ca - o * sa, cy - R * sa + o * ca), (cx + R * ca - o * sa, cy + R * sa + o * ca)])
                for q in s.geomlines(ln.intersection(g)):
                    if q.length > 0.8 * s.m: s.line(list(q.coords), f'{key}h{a}{k}', color, lw, amp=0.12, double=False, z=z, alpha=alpha)
                    k += 1
    def stipple(s, g, key, color, dens=1.4, z=2, size=0.5):
        g = g.intersection(s.clip)
        if g.is_empty: return
        r = s.rng(key); A = g.area / s.m ** 2; n = int(A * dens / 4)
        gx0, gy0, gx1, gy1 = g.bounds
        xs = r.uniform(gx0, gx1, n * 2); ys = r.uniform(gy0, gy1, n * 2)
        from shapely import contains_xy
        ok = contains_xy(g, xs, ys)
        s.ax.scatter(xs[ok][:n], ys[ok][:n], s=size, c=color, lw=0, zorder=z)
    # ---------- symbols (paper mm) ----------
    def sym(s, kind, x, y, color, key, size=1.0, rot=0, z=9, light=0.0, halo_z=None):
        if USE_B:
            gray = color.lower() in ('#9b9b9b', '#8a8a8a')
            mx = lambda c: mix(c, s.P['paper'], light)
            symbols2.draw(s.ax, kind, x, y, s.m, mx(color), 'B', size, paper=s.P['paper'], gray=gray, brown=mx(s.P['pit'] if kind == 'pit' else s.P['brown']), green=mx(s.P['green']), z=z, halo_z=halo_z)
            return
        return s.sym_old(kind, x, y, color, key, size, rot)
    def sym_old(s, kind, x, y, color, key, size=1.0, rot=0):
        m = s.m * size; r = s.rng(key); j = lambda: 0.0
        P = lambda pts: [(x + (px * math.cos(rot) - py * math.sin(rot)) * m + j(), y + (px * math.sin(rot) + py * math.cos(rot)) * m + j()) for px, py in pts]
        def pl(pts, lw=0.6, closed=False, fillc=None):
            q = P(pts)
            if closed: q = q + [q[0]]
            q = np.array(q)
            if fillc: s.ax.add_patch(MPoly(q, closed=True, fc=fillc, ec='none', zorder=8))
            s.ax.plot(q[:, 0], q[:, 1], color=color, lw=lw, zorder=9, solid_capstyle='round', solid_joinstyle='round')
        def circ(rad, lw=0.6, fillc=None, cx=0, cy=0):
            t = np.linspace(0, 2 * np.pi, 22); pl([(cx + rad * math.cos(a) * (1 + 0.06 * math.sin(3 * a + r.random())), cy + rad * math.sin(a)) for a in t], lw, False, fillc)
        if kind == 'pit': pl([(-0.75, 0.55), (0, -0.55), (0.75, 0.55)], 0.75)
        elif kind == 'pitwater': circ(0.7, 0.7, fillc=s.P['water'])
        elif kind == 'bench':
            pl([(-0.9, 0.15), (0.9, 0.15)], 0.9); pl([(-0.65, 0.15), (-0.65, -0.45)], 0.6); pl([(0.65, 0.15), (0.65, -0.45)], 0.6)
        elif kind == 'shelter': pl([(-0.9, -0.4), (0, 0.6), (0.9, -0.4)], 0.7); pl([(-0.6, -0.4), (0.6, -0.4)], 0.5)
        elif kind == 'rescue':
            circ(0.85, 0.5); pl([(-0.45, 0), (0.45, 0)], 0.7); pl([(0, -0.45), (0, 0.45)], 0.7)
        elif kind == 'gate': pl([(-0.6, -0.15), (0.6, -0.15)], 0.5); pl([(-0.6, 0.15), (0.6, 0.15)], 0.5)
        elif kind == 'info': pl([(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)], 0.5, True); pl([(0, -0.3), (0, 0.15)], 0.6); pl([(0, 0.3), (0, 0.32)], 0.8)
        elif kind == 'fire': pl([(-0.5, -0.4), (0, 0.6), (0.5, -0.4), (-0.5, -0.4)], 0.6)
        elif kind == 'picnic': pl([(-0.8, 0.3), (0.8, 0.3)], 0.8); pl([(-0.5, 0.3), (-0.7, -0.5)], 0.5); pl([(0.5, 0.3), (0.7, -0.5)], 0.5)
        elif kind == 'peak': pl([(-0.8, -0.5), (0, 0.7), (0.8, -0.5)], 0.7, True); circ(0.12, 0.8)
        elif kind == 'memorial': pl([(0, -0.8), (0, 0.8)], 0.7); pl([(-0.45, 0.35), (0.45, 0.35)], 0.7)
        elif kind == 'lighthouse':
            circ(0.45, 0.7, fillc=color)
            for a in range(0, 360, 45): pl([(0.75 * math.cos(math.radians(a)), 0.75 * math.sin(math.radians(a))), (1.25 * math.cos(math.radians(a)), 1.25 * math.sin(math.radians(a)))], 0.5)
        elif kind == 'tower': circ(0.6, 0.7); pl([(-1.0, 0), (1.0, 0)], 0.5); pl([(0, -1.0), (0, 1.0)], 0.5)
        elif kind == 'observatory':
            t = np.linspace(0, np.pi, 12); pl([(0.75 * math.cos(a), -0.1 + 0.75 * math.sin(a)) for a in t], 0.7); pl([(-0.9, -0.1), (0.9, -0.1)], 0.7); pl([(0.1, 0.5), (0.7, 1.0)], 0.6)
        elif kind == 'food':  # cup
            pl([(-0.55, 0.45), (-0.45, -0.45), (0.45, -0.45), (0.55, 0.45)], 0.6); t = np.linspace(-1.2, 1.2, 8); pl([(0.55 + 0.3 * math.cos(a), 0.05 + 0.25 * math.sin(a)) for a in t], 0.5)
        elif kind == 'bunker': pl([(-0.6, -0.6), (0.6, -0.6), (0.6, 0.6), (-0.6, 0.6)], 0.6, True); pl([(-0.6, -0.6), (0.6, 0.6)], 0.5); pl([(-0.6, 0.6), (0.6, -0.6)], 0.5)
        elif kind == 'toilet': s.ax.text(x, y, 'WC', fontproperties=PRINT, fontsize=4.2 * size, color=color, ha='center', va='center', zorder=9)
        elif kind == 'ferry': pl([(0, 0.7), (0, -0.6)], 0.6); t = np.linspace(np.pi * 1.1, np.pi * 1.9, 8); pl([(0.6 * math.cos(a), -0.1 + 0.6 * math.sin(a)) for a in t], 0.6); pl([(-0.35, 0.35), (0.35, 0.35)], 0.5)
        elif kind == 'ring': circ(0.55, 0.5); circ(0.25, 0.4)
        elif kind == 'tree': circ(0.6, 0.6); circ(0.08, 0.8)
        elif kind == 'flag': pl([(0, -0.7), (0, 0.7)], 0.5); pl([(0, 0.7), (0.6, 0.45), (0, 0.2)], 0.5)
        elif kind == 'mast': pl([(-0.4, -0.7), (0, 0.7), (0.4, -0.7)], 0.5); pl([(-0.2, -0.1), (0.2, -0.1)], 0.4)
        elif kind == 'dot': circ(0.3, 0.6, fillc=color)
    def halo(s, x, y, rad_mm=1.15):
        if USE_B: return
        t = np.linspace(0, 2 * np.pi, 30)
        s.ax.add_patch(MPoly(np.column_stack([x + rad_mm * s.m * np.cos(t), y + rad_mm * s.m * np.sin(t)]), closed=True, fc=s.P['paper'], ec=s.P['ink'], lw=0.3, zorder=8.5))
    def label(s, x, y, txt, size=7, dx=1.6, dy=0.0, color=None, ha='left', bold=False, rot=0, z=12):
        s.ax.text(x + dx * s.m, y + dy * s.m, txt, fontproperties=HANDB if bold else HAND, fontsize=size, color=color or s.P['ink'],
                  ha=ha, va='center', zorder=z, rotation=rot,
                  path_effects=[pe.withStroke(alpha=HALO_A, linewidth=2.2, foreground=s.P['paper'])])

# ======================= layers =======================
_BASE = {}
def base_geom():
    if not _BASE:
        z = rasterio.open(BASE + '/data/dgm_frame.tif'); Z = z.read(1); tr = z.transform
        zz = np.where(np.isnan(Z), -3, Z); zs = gaussian_filter(zz, 3)
        sea = []
        for c in find_contours(zs, SEA_Z):
            pts = [tr * (cc + 0.5, rr + 0.5) for rr, cc in c]
            if len(pts) > 20: sea.append(LineString(pts))
        from rasterio.features import shapes
        low = (zs < SEA_Z).astype('uint8')
        lowg = unary_union([shape(g) for g, v in shapes(low, mask=low.astype(bool), transform=tr) if v == 1]).simplify(2).buffer(0)
        _BASE['lowg'] = lowg; _BASE['sea'] = sea
    return _BASE['lowg'], _BASE['sea']

def layer_base(S):
    P = S.P
    lowg, sea = base_geom()
    with tag(S, 'sea'):
        S.fill(lowg, P['sea'], z=0.5)
        for i, ln in enumerate(sea):
            if ln.length > 60 and ln.intersects(S.clip): S.gline(ln, f'shore{i}', P['blue'], 0.45, amp=0.3)
    S.lowg = lowg

def osm_polys(pred):
    out = []
    for wid, w in W.items():
        if pred(w['tags']):
            g = way_geom(wid)
            if g is not None and g.geom_type == 'Polygon' and g.is_valid: out.append((f'w{wid}', g))
    for rid, r in R.items():
        if r['tags'].get('type') == 'multipolygon' and pred(r['tags']):
            g = rel_geom(rid)
            if g is not None: out.append((f'r{rid}', g.buffer(0)))
    return out

def layer_areas(S):
    P = S.P
    with tag(S, 'open'):
        for k, g in osm_polys(lambda t: t.get('landuse') in ('meadow', 'grass', 'greenery') or t.get('natural') == 'grassland' or t.get('leisure') in ('park', 'pitch')):
            S.fill(g, P['open'], z=0.8)
    SA = json.load(open(BASE + '/data/sand.geojson'))['features']
    with tag(S, 'sand'):
        for i, f in enumerate(SA):
            g = shape(f['geometry'])
            if g.intersects(S.lowg) and g.intersection(S.lowg).area > 0.95 * g.area: continue  # sandbanks in the Watt
            if g.intersects(S.clip): S.stipple(g, f'sand{i}', P['sand'], dens=2.2 if S.dense else 1.3, size=0.45 if S.dense else 0.3)
    with tag(S, 'veg'):
        for k, g in osm_polys(lambda t: t.get('natural') == 'scrub'):
            S.hatch(g, k, P['green'], spacing=1.6, angle=50, lw=0.3, z=1.5, alpha=0.8)
        for k, g in osm_polys(lambda t: t.get('landuse') == 'forest' or t.get('natural') == 'wood'):
            S.hatch(g, k, P['green'], spacing=1.1, angle=50, lw=0.35, z=1.5, cross=True, alpha=0.9)
    with tag(S, 'water'):
        for k, g in osm_polys(lambda t: t.get('natural') == 'wetland' or t.get('wetland')):
            if g.area > 5e5: continue  # huge tidal-flat relations
            g = g.difference(S.lowg)
            S.hatch(g, k, P['marsh'], spacing=1.6, angle=0, lw=0.3, z=1.4, alpha=0.5)
        for k, g in osm_polys(lambda t: t.get('natural') == 'water'):
            if g.area < 15: continue
            S.fill(g, P['water'], z=1.6); S.gline(g, k, P['blue'], 0.45, amp=0.12, double=False, z=1.7)
    with tag(S, 'info'):
        for k, g in osm_polys(lambda t: t.get('landuse') == 'cemetery'):
            S.gline(g, k, P['ink'], 0.4, amp=0.15, double=False, z=2)
            c = g.representative_point()
            for dx in (-1, 1): S.sym('memorial', c.x + dx * 2 * S.m, c.y, P['ink'], k + str(dx), 0.8)

def layer_contours(S):
    P = S.P
    C = json.load(open(BASE + '/data/contours.geojson'))['features']
    lab_done = 0
    with tag(S, 'contours'): _contour_lines(S, C)

def _contour_lines(S, C):
    P = S.P
    for i, f in enumerate(C):
        g = shape(f['geometry']); idx = f['properties']['index']
        if not g.intersects(S.clip): continue
        if not S.dense and g.length < 60: continue
        S.gline(g, f'ct{i}', P['contour'], 0.6 if idx else 0.34, amp=0.18, double=False, z=2.2)
    # spot heights: highest dunes
    pk = []
    for f in C:
        if f['properties']['z'] >= 12.5 and f['properties']['closed']:
            g = shape(f['geometry']); c = g.centroid
            if S.clip.contains(c): pk.append((f['properties']['z'], c))

def layer_ruhezone(S):
    P = S.P
    g = rel_geom(16774424)
    if g is None: return
    band = g.difference(g.buffer(-3.2 * S.m))
    with tag(S, 'ruhezone'):
        S.hatch(band, 'rz', P['purple'], spacing=1.4, angle=-60, lw=0.35, z=2.5, alpha=0.6)
        S.gline(g, 'rzb', P['purple'], 0.9, amp=0.25, dashes=(4, 2.5), z=2.6, double=False)

_PS = {}
def way_layer(t):
    if t.get('man_made') in ('dyke', 'groyne', 'breakwater', 'pier') or t.get('barrier') in ('fence', 'wall'): return 'structures'
    if t.get('waterway'): return 'water'
    if t.get('railway'): return 'rail'
    h = t.get('highway')
    if h in ('unclassified', 'residential', 'pedestrian', 'service', 'track'): return 'roads'
    return 'paths'

def layer_lines(S):
    for wid, w in W.items():
        with tag(S, way_layer(w['tags'])): _lines(S, {wid: w})
    fp = BASE + '/data/feldcheck_pfade.geojson'   # trails recorded in the field (GPS or tapped)
    if os.path.exists(fp):
        with tag(S, 'paths'):
            for f in json.load(open(fp))['features']:
                g = shape(f['geometry'])
                if g.intersects(S.clip): S.gline(g, f['properties']['id'], S.P['ink'], 0.6, amp=0.22, z=4, dashes=(1.8, 1.4), double=False)

def _lines(S, WW):
    P = S.P; ps = _PS.get('ps') or _PS.setdefault('ps', json.load(open(BASE + '/data/path_status_v1.json' if os.path.exists(BASE + '/data/path_status_v1.json') else BASE + '/data/path_status.json')))
    for wid, w in WW.items():
        t = w['tags']; key = f'w{wid}'
        g = None
        def G():
            return way_geom(wid)
        if t.get('man_made') == 'dyke':
            g = G();  g and S.gline(g, key, P['brown'], 1.1, amp=0.25, z=2.3)
        elif t.get('man_made') in ('groyne', 'breakwater', 'pier'):
            g = G(); g and S.gline(g, key, P['ink'], 0.8 if t['man_made'] == 'pier' else 0.55, amp=0.15, z=2.3)
        elif t.get('waterway') in ('ditch', 'stream', 'drain'):
            g = G(); g and S.gline(g, key, P['blue'], 0.4, amp=0.12, double=False, z=2.1)
        elif t.get('barrier') in ('fence', 'wall'):
            g = G()
            if g is not None:
                S.gline(g, key, P['ink'], 0.35, amp=0.1, double=False, z=3)
                gi = g.intersection(S.clip)
                for q in S.geomlines(gi):
                    for d in np.arange(2 * S.m, q.length, 4 * S.m):
                        p = q.interpolate(d); p2 = q.interpolate(min(q.length, d + 0.5 * S.m)); ang = math.atan2(p2.y - p.y, p2.x - p.x)
                        S.ax.plot([p.x, p.x - 0.6 * S.m * math.sin(ang)], [p.y, p.y + 0.6 * S.m * math.cos(ang)], color=P['ink'], lw=0.35, zorder=3)
        elif t.get('railway') in ('narrow_gauge', 'rail'):
            g = G()
            if g is not None:
                S.gline(g, key, P['ink'], 0.7, amp=0.12, z=3.2, double=False)
                for q in S.geomlines(g.intersection(S.clip)):
                    for d in np.arange(1.5 * S.m, q.length, 3.5 * S.m):
                        p = q.interpolate(d); p2 = q.interpolate(min(q.length, d + 0.5 * S.m)); ang = math.atan2(p2.y - p.y, p2.x - p.x)
                        h = 0.55 * S.m
                        S.ax.plot([p.x - h * math.sin(ang), p.x + h * math.sin(ang)], [p.y + h * math.cos(ang), p.y - h * math.cos(ang)], color=P['ink'], lw=0.45, zorder=3.2)
        elif 'highway' in t:
            g = G()
            if g is None or g.geom_type != 'LineString' or not g.intersects(S.clip): continue
            h = t['highway']; st = ps.get(str(wid), {}).get('status', 'sicher')
            if st == 'entfernt': continue   # field check: not there
            if getattr(S, 'field', False) and st != 'sicher': continue
            st = 'sicher'; col = P['ink']   # map = final look; open questions live on the field-check page
            surf = t.get('surface', '')
            if h in ('unclassified', 'residential', 'pedestrian') :
                S.gline(g, key, col, 1.6, amp=0.2, z=4)
            elif h == 'service' or h == 'track':
                S.gline(g, key, col, 1.0, amp=0.22, z=4, dashes=(5, 1.3) if h == 'track' and surf not in ('asphalt', 'concrete', 'paving_stones') else None)
            elif h == 'steps':
                S.gline(g, key, col, 0.6, amp=0.1, z=4, double=False)
                for q in S.geomlines(g.intersection(S.clip)):
                    for d in np.arange(0, q.length + 0.01, max(0.6 * S.m, q.length / 4)):
                        p = q.interpolate(d); p2 = q.interpolate(min(q.length, d + 0.3)); p1 = q.interpolate(max(0, d - 0.3)); ang = math.atan2(p2.y - p1.y, p2.x - p1.x)
                        hh = 0.7 * S.m
                        S.ax.plot([p.x - hh * math.sin(ang), p.x + hh * math.sin(ang)], [p.y + hh * math.cos(ang), p.y - hh * math.cos(ang)], color=col, lw=0.55, zorder=4)
            elif h == 'footway' or surf in ('paving_stones', 'asphalt', 'concrete', 'concrete:plates', 'wood', 'sett', 'compacted', 'shell_crumbs', 'shell', 'pebblestone'):
                S.gline(g, key, col, 0.85, amp=0.2, z=4, dashes=(4, 1.6) if st != 'sicher' else None)
            elif surf in ('sand', 'grass', 'dirt', 'ground', 'unpaved', '') or t.get('informal') == 'yes':
                S.gline(g, key, col, 0.6, amp=0.22, z=4, dashes=(1.8, 1.4), double=False)
            else:
                S.gline(g, key, col, 0.7, amp=0.2, z=4, dashes=(3, 1.5), double=False)

def layer_extras(S):
    P = S.P
    # steep banks: brown line + ticks downslope (OL earth bank)
    _st = tag(S, 'steep'); _st.__enter__()
    for i, f in enumerate(json.load(open(BASE + '/data/steep_lines.geojson'))['features']):
        g = shape(f['geometry'])
        if not g.intersects(S.clip): continue
        c = np.array(g.coords); S.ax.plot(c[:, 0], c[:, 1], color=P['brown'], lw=1.0, solid_capstyle='butt', zorder=2.4)
        dx, dy = f['properties']['dx'], f['properties']['dy']
        for d_ in np.arange(0.4 * S.m, g.length, 1.0 * S.m):
            q = g.interpolate(d_); S.ax.plot([q.x, q.x + dx * 0.7 * S.m], [q.y, q.y + dy * 0.7 * S.m], color=P['brown'], lw=0.6, zorder=2.4)
    _st.__exit__(None, None, None)
    for wid, w in W.items():
        t = w['tags']
        with tag(S, 'buildings' if t.get('leisure') == 'pitch' else 'paths'): _extra_way(S, wid, t)

def _extra_way(S, wid, t):
    P = S.P
    if True:
        if t.get('bridge') == 'yes' or t.get('tunnel') == 'culvert':
            g = way_geom(wid)
            if g is None or g.geom_type != 'LineString' or not g.intersects(S.clip): return
            col = P['ink'] if t.get('bridge') == 'yes' else P['blue']
            L_ = max(g.length, 2.2 * S.m); mid = g.interpolate(0.5, normalized=True)
            a_ = g.interpolate(max(0, g.length / 2 - 0.1)); b_ = g.interpolate(min(g.length, g.length / 2 + 0.1)); ang = math.atan2(b_.y - a_.y, b_.x - a_.x)
            ux, uy = math.cos(ang), math.sin(ang); nx_, ny_ = -uy, ux; half = min(L_, 4 * S.m) / 2; off = 0.75 * S.m
            for sgn in (1, -1):   # bracket on each side: )(
                xs = [mid.x - ux * half + sgn * nx_ * (off + 0.35 * S.m), mid.x - ux * half + sgn * nx_ * off, mid.x + ux * half + sgn * nx_ * off, mid.x + ux * half + sgn * nx_ * (off + 0.35 * S.m)]
                ys = [mid.y - uy * half + sgn * ny_ * (off + 0.35 * S.m), mid.y - uy * half + sgn * ny_ * off, mid.y + uy * half + sgn * ny_ * off, mid.y + uy * half + sgn * ny_ * (off + 0.35 * S.m)]
                S.ax.plot(xs, ys, color=col, lw=0.55, zorder=4.2, solid_joinstyle='miter')
        if t.get('surface') == 'wood' and t.get('highway') in ('path', 'footway'):
            g = way_geom(wid)
            if g is None or g.geom_type != 'LineString' or not g.intersects(S.clip): return
            for sgn in (1, -1):
                o = g.parallel_offset(0.45 * S.m, 'left' if sgn > 0 else 'right')
                for q in getattr(o, 'geoms', [o]):
                    if q.length > 0: S.ax.plot(*q.xy, color=P['ink'], lw=0.4, zorder=4.1)
        if t.get('leisure') == 'pitch':
            g = way_geom(wid)
            if g is not None and g.geom_type == 'Polygon' and g.intersects(S.clip): S.ax.plot(*g.exterior.xy, color=P['ink'], lw=0.35, zorder=2.6)

def layer_buildings(S):
    with tag(S, 'buildings'): _buildings(S)
def _buildings(S):
    P = S.P
    for rid, rr in R.items():   # multipolygon buildings (e.g. Inselheim Rüstringen)
        if 'building' in rr['tags']:
            g = rel_geom(rid)
            if g is None or not g.intersects(S.clip): continue
            for q in getattr(g, 'geoms', [g]):
                c = S.wob(list(q.exterior.coords), f'r{rid}', 0.12, step=0.8)
                S.ax.add_patch(MPoly(c, closed=True, fc=P['ink'], ec=P['ink'], lw=0.3, alpha=0.88, zorder=5))
    for wid, w in W.items():
        t = w['tags']
        if 'building' not in t or t.get('building') in ('roof',): continue
        g = way_geom(wid)
        if g is None or g.geom_type != 'Polygon' or not g.intersects(S.clip): continue
        c = S.wob(list(g.exterior.coords), wid, 0.12, step=0.8)
        S.ax.add_patch(MPoly(c, closed=True, fc=P['ink'], ec=P['ink'], lw=0.3, alpha=0.88, zorder=5))

def layer_points(S):
    P = S.P
    F = json.load(open(BASE + '/data/points_v1.geojson'))['features']
    # craters (Trichter rows of points_v1: field-check removals/moves already applied there)
    placed = []; pits = []
    CR = [f for f in F if f['properties']['kategorie'] == 'Trichter']
    for f in sorted(CR, key=lambda f: -float(f['properties'].get('d') or 5)):
        p = f['properties']; x, y = f['geometry']['coordinates']; dd = float(p.get('d') or 5)
        if not S.clip.contains(Point(x, y)): continue
        sure = p['status'] == 'sicher'
        if not S.dense:
            if dd < 8 or any(math.hypot(x - a, y - b) < 2.2 * S.m for a, b in placed): continue
        if getattr(S, 'field', False) and not sure: continue
        placed.append((x, y))
        pits.append(dict(kind='pit', x=x, y=y, size=0.95 if S.dense else 0.8, n=1, sure=True, members=[dict(p=dict(id=p['id'], name=''))]))
    items = []
    for f in F:
        p = f['properties']; x, y = f['geometry']['coordinates']
        if not S.clip.contains(Point(x, y)): continue
        if getattr(S, 'field', False) and p['status'] != 'sicher': continue
        sk = sym_kind(p, S)
        if sk: items.append(dict(x=x, y=y, p=p, kind=sk[0], size=sk[1], group=sk[2], sure=True))
    S.drawn = group_items(S, items)
    stack_levels(S, pits)
    with tag(S, 'pits'):
        for d in pits:
            S.sym('pit', d['x'], d['y'], P['brown'], d['members'][0]['p']['id'], d['size'], z=d['z'], light=d['light'], halo_z=HALO_Z)
    S.numreq = []
    for d in S.drawn:
        with tag(S, KIND_LAYER.get(d['kind'], 'facilities')): draw_item(S, d)
    place_numbers(S)

SINGLE = {'lighthouse', 'observatory', 'food', 'peak', 'ferry'}
HALFW = dict(bench=0.85, rescue=0.6, shelter=0.85, gate=0.6, info=0.55, flag=0.75, fire=0.6, picnic=0.9, mast=0.4, memorial=0.45, toilet=0.75, ring=0.55, dot=0.3, tree=0.6,
             milestone=0.3, groyne=0.15, railx=0.5, station=0.6, hydrant=0.5, playground=0.75, fitness=0.75, recycling=0.65, bike=0.75, substation=0.4, summit=0.32, bush=0.36,
             boulder=0.6, post=0.3, flagpole=0.55, sign=0.45, rzsign=0.5, rzpost=0.3, beachaccess=0.6, pond=0.5, steeppt=0.7, sandfence=0.85, boardwalk=0.8)
def draw_roman(S, x, y, n, color, h_mm=1.25):
    """Straight vector roman numeral with continuous top/bottom bars (clock style), left edge at x, centred on y."""
    txt = roman(n); m = S.m; h = h_mm * m; wI, wV = 0.32 * h, 0.62 * h; gap = 0.12 * h
    xs = x; segs = []
    for ch in txt:
        if ch == 'I': segs.append([(xs + wI / 2, y - h / 2), (xs + wI / 2, y + h / 2)]); xs += wI + gap
        elif ch == 'V': segs += [[(xs, y + h / 2), (xs + wV / 2, y - h / 2)], [(xs + wV / 2, y - h / 2), (xs + wV, y + h / 2)]]; xs += wV + gap
        elif ch == 'X': segs += [[(xs, y + h / 2), (xs + wV, y - h / 2)], [(xs, y - h / 2), (xs + wV, y + h / 2)]]; xs += wV + gap
    x1 = xs - gap
    segs += [[(x - 0.06 * h, y + h / 2), (x1 + 0.06 * h, y + h / 2)], [(x - 0.06 * h, y - h / 2), (x1 + 0.06 * h, y - h / 2)]]
    for sg in segs:
        S.ax.plot([sg[0][0], sg[1][0]], [sg[0][1], sg[1][1]], color=color, lw=0.55, solid_capstyle='butt', zorder=11)
def roman(n):
    out = ''
    for v, r in ((10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')):
        while n >= v: out += r; n -= v
    return out
def sym_kind(p, S):
    k, t = p['kategorie'], p['typ']; sz = 1.0 if S.dense else 0.85
    if k == 'Bank': return ('bench', sz, True)
    if k == 'Rettungspunkt': return ('rescue', sz * 0.9, True)
    if k == 'Bauwerk' and t == 'Schutzhütte': return ('shelter', sz, True)
    if k == 'Bauwerk' and t == 'lighthouse': return ('lighthouse', 1.0, False)
    if k == 'Bauwerk' and t == 'Sternwarte': return ('observatory', 0.95, False)
    if k == 'Durchgang': return ('gate', sz * 0.9, True)
    if k == 'Kleinobjekt':
        kind = {'Infotafel': 'info', 'Wegweiser': 'flag', 'firepit': 'fire', 'picnic_site': 'picnic', 'picnic_table': 'picnic', 'monitoring_station': 'mast', 'mast': 'mast', 'antenna': 'mast', 'flagpole': 'flag'}.get(t, 'dot')
        return (kind, sz * 0.9, True) if (S.dense or kind in ('fire', 'picnic')) else None
    if k == 'Gastronomie': return ('food', sz * 0.85, False)
    if k == 'Historisch' and t in ('war_memorial', 'memorial'): return ('memorial', sz, True)
    if k == 'Gelände': return ('peak', 1.0, False)
    if k == 'Einrichtung':
        kind = {'toilets': 'toilet', 'life_ring': 'ring', 'ferry_terminal': 'ferry'}.get(t)
        return (kind, sz, kind != 'ferry') if kind and (S.dense or kind == 'ferry') else None
    if k == 'Baum': return ('tree', sz, True)
    NEWK = {'km-Stein': 'milestone', 'Bahnübergang': 'railx', 'Haltepunkt': 'station', 'Hydrant': 'hydrant', 'Spielplatz': 'playground', 'Fitness': 'fitness',
            'Recycling': 'recycling', 'Fahrradständer': 'bike', 'Umspannstation': 'substation', 'Busch': 'bush'}
    if k in NEWK:
        if not S.dense and k not in ('Haltepunkt', 'km-Stein'): return None
        return (NEWK[k], sz * (0.8 if k == 'Bahnübergang' else 1.0), k not in ('Haltepunkt',))
    if k == 'Buhne': return ('groyne', sz, False) if S.dense else None
    if k == 'Feldobjekt': return (t, sz, True) if (S.dense or t in ('rzsign', 'boulder')) else None
    if k == 'Kuppe':
        if not S.dense and float(p.get('prom') or 0) < 4: return None
        return ('summit', sz, False)
    return None

def group_items(S, items):
    """Same-kind symbols closer than GROUP_MM on paper merge into one group symbol (count shown). Insets never group."""
    if getattr(S, 'inset', False): 
        return [dict(x=i['x'], y=i['y'], kind=i['kind'], size=i['size'], n=1, sure=i['sure'], members=[i]) for i in items]
    d = 2.2 * S.m; out = []
    by = {}
    for i in items: by.setdefault(i['kind'] if i['group'] else id(i), []).append(i)
    for key, lst in by.items():
        n = len(lst); parent = list(range(n))
        def f_(a):
            while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
            return a
        for a in range(n):
            for b in range(a + 1, n):
                if math.hypot(lst[a]['x'] - lst[b]['x'], lst[a]['y'] - lst[b]['y']) < d: parent[f_(a)] = f_(b)
        comp = {}
        for a in range(n): comp.setdefault(f_(a), []).append(lst[a])
        for mem in comp.values():
            out.append(dict(x=sum(m['x'] for m in mem) / len(mem), y=sum(m['y'] for m in mem) / len(mem), kind=mem[0]['kind'], size=mem[0]['size'],
                            n=len(mem), sure=all(m['sure'] for m in mem), members=mem))
    return out

def item_draw_args(S, d):
    """(kind, x, y, size) exactly as draw_item paints the symbol."""
    k = d['kind']; f = 1.3 if getattr(S, 'inset', False) else 1.0
    if k == 'pit': return k, d['x'], d['y'], d['size']
    if k == 'lighthouse': return k, d['x'], d['y'], 1.0
    if k == 'observatory': return k, d['x'], d['y'] - 0.1 * S.m, 0.95
    if k == 'peak': return k, d['x'], d['y'], 1.0
    return k, d['x'], d['y'], d['size'] * f

LIGHT_STEPS = (0.0, 0.2, 0.34, 0.45)   # brightness per stacking level (bottom = darkest)
HALO_Z = 8.9   # all paper contours lie below every symbol body -> overlapping symbols share one outline, none covers another
_INK = {}
def stack_levels(S, extra=()):
    """Overlapping symbols: flächige/large ones at the bottom, fine/small ones on top, each level a bit lighter."""
    D = [d for d in list(S.drawn) + list(extra) if d['kind'] != 'groyne']
    for d in D: d['z'], d['light'] = 9.0, 0.0
    gs = []
    for d in D:
        k, x, y, sz = item_draw_args(S, d)
        gs.append(symbols2.knock_geom(k, x, y, S.m, sz, extra_mm=0.08))
    n = len(D); nb = {i: set() for i in range(n)}
    from shapely.strtree import STRtree
    if not n: return
    tr = STRtree(gs)
    for i, g in enumerate(gs):
        for j in tr.query(g):
            j = int(j)
            if j != i and g.intersects(gs[j]): nb[i].add(j)
    seen = set()
    for i in range(n):
        if i in seen or not nb[i]: continue
        comp, st = [], [i]
        while st:
            a = st.pop()
            if a in seen: continue
            seen.add(a); comp.append(a); st += list(nb[a])
        def ink(a):
            k, _, _, sz = item_draw_args(S, D[a]); key = (k, round(sz, 2))
            if key not in _INK: _INK[key] = symbols2.ink_area(k, sz)
            return _INK[key]
        comp.sort(key=lambda a: (-ink(a), -gs[a].area, -D[a]['y']))   # flächig first (bottom), fine on top
        level = {}
        for a in comp:   # level = 1 + highest level among already placed overlapping neighbours
            lv = max([level[b] + 1 for b in nb[a] if b in level] or [0])
            level[a] = lv
        for r, a in enumerate(comp):
            D[a]['z'] = 9.0 + 0.2 * r; D[a]['light'] = LIGHT_STEPS[min(level[a], len(LIGHT_STEPS) - 1)]

def draw_item(S, d):
    P = S.P; x, y, k = d['x'], d['y'], d['kind']; col = P['ink'] if d['sure'] else P['gray']
    if getattr(S, 'inset', False): d = dict(d, size=d['size'] * 1.3)
    key = d['members'][0]['p']['id']; zz, lt = d.get('z', 9.0), d.get('light', 0.0)
    if k == 'lighthouse': S.sym('lighthouse', x, y, P['ink'], key, 1.0, z=zz, light=lt, halo_z=HALO_Z); return
    if k == 'observatory': S.sym('observatory', x, y - 0.1 * S.m, P['ink'], key, 0.95, z=zz, light=lt, halo_z=HALO_Z); return
    if k == 'food': S.sym('food', x, y, col, key, d['size'], z=zz, light=lt, halo_z=HALO_Z); return
    if k == 'peak': S.sym('peak', x, y, P['ink'], key, 1.0, z=zz, light=lt, halo_z=HALO_Z); return
    if k == 'tree': col = P['green'] if d['sure'] else P['gray']
    p0 = d['members'][0]['p']
    if k == 'groyne':   # name letter at the landward end of the groyne
        S.numreq.append(dict(d=d, kind='sos', col=col, txt=p0['name'])); return
    S.sym(k, x, y, col, key, d['size'], z=zz, light=lt, halo_z=HALO_Z)
    if d['n'] > 1: S.numreq.append(dict(d=d, kind='roman', col=P['count']))
    elif k == 'rescue' and S.dense and p0['name']: S.numreq.append(dict(d=d, kind='sos', col=col))
    elif k == 'milestone' and p0['name']: S.numreq.append(dict(d=d, kind='sos', col=col, txt=p0['name']))
    elif k == 'summit' and S.dense and (float(p0.get('z') or 0) >= 14 or float(p0.get('prom') or 0) >= 4): S.numreq.append(dict(d=d, kind='sos', col=P['brown'], txt=str(round(float(p0['z'])))))

def roman_width(n, h):
    t = roman(n); wI, wV, gap = 0.32 * h, 0.62 * h, 0.12 * h
    return sum(wI if c == 'I' else wV for c in t) + gap * (len(t) - 1) + 0.12 * h

def sym_halfw(d):
    k = d['kind']
    if k in ('lighthouse', 'observatory'): return 0.95 if USE_B else 1.25
    if k in ('food', 'peak'): return 0.8 if USE_B else 1.0
    return HALFW.get(k, 0.6) * d['size'] * (1.3 if False else 1.0)

def place_numbers(S):
    """Put group numerals / SOS numbers right next to their symbol, choosing the side that touches no other symbol or number."""
    m = S.m; ins = 1.3 if getattr(S, 'inset', False) else 1.0
    feet = []
    for d in S.drawn:
        hw = sym_halfw(d) * ins
        feet.append((d, box(d['x'] - hw * m, d['y'] - hw * m, d['x'] + hw * m, d['y'] + hw * m)))
    blds = [g for g in (way_geom(w) for w, v in W.items() if 'building' in v['tags']) if g is not None and g.geom_type == 'Polygon' and g.intersects(S.clip)]
    placed = []
    for rq in S.numreq:
        d = rq['d']; x, y = d['x'], d['y']; hw = sym_halfw(d) * ins; g = 0.18
        if rq['kind'] == 'roman' and d['n'] <= 6:
            w, h = symbols2.dots_size(d['n'])
        elif rq['kind'] == 'roman':
            h = (1.2 if S.dense else 1.05); w = roman_width(d['n'], h)
        else:
            txt = rq.get('txt') or d['members'][0]['p']['name']; h = 1.25; w = 0.98 * len(txt) + 0.1
        cands = [(hw + g, 0), (-(hw + g) - w, 0), (-w / 2, hw + g + h / 2), (-w / 2, -(hw + g + h / 2)),
                 (hw * 0.6, hw * 0.6 + h / 2 + g), (hw * 0.6, -(hw * 0.6 + h / 2 + g)), (-(hw * 0.6) - w, hw * 0.6 + h / 2 + g), (-(hw * 0.6) - w, -(hw * 0.6 + h / 2 + g))]
        best = None
        for i, (ox, oy) in enumerate(cands):
            bx = box(x + ox * m, y + oy * m - h / 2 * m, x + (ox + w) * m, y + oy * m + h / 2 * m)
            c = sum(f.intersection(bx).area for dd, f in feet if dd is not d) / (m * m) * 4
            c += sum(p.intersection(bx).area for p in placed) / (m * m) * 6
            c += sum(b.intersection(bx).area for b in blds if b.intersects(bx)) / (m * m) * 0.5
            c += 0.02 * i
            if best is None or c < best[0]: best = (c, ox, oy, bx)
            if c < 0.03: break
        _, ox, oy, bx = best; placed.append(bx)
        _tg = tag(S, KIND_LAYER.get(d['kind'], 'facilities')); _tg.__enter__()
        if rq['kind'] == 'roman' and d['n'] <= 6:
            symbols2.draw_dots(S.ax, x + ox * m, y + oy * m, d['n'], m, rq['col'], paper=S.P['paper'])
        elif rq['kind'] == 'roman':
            draw_roman(S, x + ox * m + 0.06 * h * m, y + oy * m, d['n'], rq['col'], h)
        else:
            _t = S.ax.text(x + ox * m, y + oy * m, rq.get('txt') or d['members'][0]['p']['name'], fontproperties=SERIF, fontsize=4.8, color=rq['col'], ha='left', va='center_baseline', zorder=10); _t._sos = True
        _tg.__exit__(None, None, None)

# ======================= insets ("Lupen") =======================
def find_hotspots(S):
    D = [d for d in S.drawn]; n = len(D); thr = 2.2 * S.m; parent = list(range(n))
    def f_(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for a in range(n):
        for b in range(a + 1, n):
            if math.hypot(D[a]['x'] - D[b]['x'], D[a]['y'] - D[b]['y']) < thr: parent[f_(a)] = f_(b)
    comp = {}
    for a in range(n): comp.setdefault(f_(a), []).append(D[a])
    hs = []
    for c in comp.values():
        mem = [m for d in c for m in d['members']]
        if len(c) >= 3 or any(d['n'] >= 4 for d in c) or (len(c) >= 2 and len(mem) >= 4):
            hs.append(mem)
    hs.sort(key=len, reverse=True)
    # merge hotspots closer than 40 m (e.g. both clusters at the Westanleger)
    merged = []
    for h in hs:
        cx, cy = np.mean([m['x'] for m in h]), np.mean([m['y'] for m in h])
        for g in merged:
            gx, gy = np.mean([m['x'] for m in g]), np.mean([m['y'] for m in g])
            if math.hypot(cx - gx, cy - gy) < 70: g.extend(h); break
        else: merged.append(list(h))
    return merged

def plan_inset(mem):
    xs = np.array([m['x'] for m in mem]); ys = np.array([m['y'] for m in mem])
    ds = [math.hypot(xs[i] - xs[j], ys[i] - ys[j]) for i in range(len(xs)) for j in range(i + 1, len(xs))]
    ds = [d for d in ds if d > 0.3] or [10.0]
    dmin = min(ds)
    need = dmin * 1000 / 2.6   # scale at which the closest two symbols (1.3x size in the Lupe) stand apart
    sc = next((v for v in (1000, 750, 500) if v <= need), 500)
    while True:
        m = sc / 1000; mg = max(3, 4.5 * m)
        w = max(22, (np.ptp(xs) + 2 * mg) / m); h = max(18, (np.ptp(ys) + 2 * mg) / m)
        if (w <= 75 and h <= 65) or sc >= 4000: break
        sc = 1000 if sc < 1000 else int(sc * 1.5)
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    return dict(scale=sc, w=w, h=h, bbox=(cx - w * m / 2, cy - h * m / 2, cx + w * m / 2, cy + h * m / 2), cx=cx, cy=cy, n=len(mem))

def free_area(S, placed, allow_rz=False):
    free = S.lowg
    if allow_rz:   # off-limits Ruhezone interior away from any path (nobody runs there)
        rz_ = rel_geom(16774424)
        if rz_ is not None:
            ways_ = unary_union([way_geom(w).buffer(8 * S.m) for w, v in W.items() if ('highway' in v['tags'] or v['tags'].get('railway')) and way_geom(w) is not None and way_geom(w).intersects(S.clip)])
            free = free.union(rz_.difference(ways_))
        # open beach between waterline and dune foot (only sand there, no landmarks)
        beach = [shape(f['geometry']).buffer(0) for f in json.load(open(BASE + '/data/sand.geojson'))['features']]
        beach = [g for g in beach if g.intersects(S.clip) and g.buffer(6).intersects(S.lowg)]
        if beach:
            ways2 = unary_union([way_geom(w).buffer(3 * S.m) for w, v in W.items() if ('highway' in v['tags'] or v['tags'].get('railway') or v['tags'].get('man_made') == 'dyke') and way_geom(w) is not None and way_geom(w).intersects(S.clip)])
            free = free.union(unary_union(beach).difference(ways2))
    free = free.intersection(S.clip.buffer(-3 * S.m)).buffer(-2.5 * S.m)
    na = box(S.x1 - 16 * S.m, S.y1 - 22 * S.m, S.x1, S.y1); free = free.difference(na)
    rz = rel_geom(16774424)
    if rz is not None: free = free.difference(rz.boundary.buffer(4 * S.m))
    for wid, w in W.items():
        if w['tags'].get('man_made') in ('groyne', 'pier', 'breakwater') or w['tags'].get('railway'):
            g = way_geom(wid)
            if g is not None and g.intersects(S.clip): free = free.difference(g.buffer(2.5 * S.m))
    for txt, x, y, *_ in LABELS:
        if S.clip.contains(Point(x, y)): free = free.difference(Point(x, y).buffer(12 * S.m))
    try:   # actual placed label boxes
        S.fig.canvas.draw(); rend = S.fig.canvas.get_renderer(); inv = S.ax.transData.inverted()
        for t in S.ax.texts:
            if not t.get_text().strip(): continue
            bb = t.get_window_extent(rend); (a0, b0), (a1, b1) = inv.transform((bb.x0, bb.y0)), inv.transform((bb.x1, bb.y1))
            free = free.difference(box(min(a0, a1), min(b0, b1), max(a0, a1), max(b0, b1)).buffer(1.5 * S.m))
    except Exception: pass
    for r in placed: free = free.difference(r.buffer(4 * S.m))
    return free

def _candidates(S, I, allow_rz, maxn=80):
    ck = '_free_rz' if allow_rz else '_free'
    if not hasattr(S, ck): setattr(S, ck, free_area(S, [], allow_rz))
    free = getattr(S, ck)
    if free.is_empty: return []
    from shapely.prepared import prep
    pf = prep(free); W_, H_ = (I['w'] + 2) * S.m, (I['h'] + 2) * S.m
    fx0, fy0, fx1, fy1 = free.bounds; step = 2.0 * S.m; out = []
    for x in np.arange(fx0, fx1 - W_, step):
        for y in np.arange(fy0, fy1 - H_, step):
            r = box(x, y, x + W_, y + H_)
            if pf.contains(r): out.append(r)
    hp = Point(I['cx'], I['cy'])
    if I.get('side') == 'west': out = [r for r in out if r.bounds[2] <= I['bbox'][0]]
    out.sort(key=lambda r: r.distance(hp))
    # thin out: keep candidates that are not near-duplicates
    keep = []
    for r in out:
        if all(r.centroid.distance(k.centroid) > 5 * S.m for k in keep): keep.append(r)
        if len(keep) >= maxn: break
    return keep

def _margin_candidates(S, I):
    """Lupen strip in the bottom page margin between title and scale bar (landscape detail sheets)."""
    if S.cfg.get('orient') != 'L' or getattr(S, 'inset', False) or not S.cfg.get('sub', '').startswith('Blatt'): return []
    gx = lambda xmm: S.x0 + (xmm - S.mx) * S.m; gy = lambda ymm: S.y0 + (ymm - S.my) * S.m
    W_, H_ = (I['w'] + 2) * S.m, (I['h'] + 2) * S.m
    out = []
    for xm in np.arange(114, 222 - (I['w'] + 2) + 0.01, 2.0):
        y0 = gy(1.0); 
        if y0 + H_ > gy(S.my - 0.5): continue
        out.append(box(gx(xm), y0, gx(xm) + W_, y0 + H_))
    return out

def _segments_cross(a, b, c, d):
    def ccw(p, q, r): return (r[1] - p[1]) * (q[0] - p[0]) > (q[1] - p[1]) * (r[0] - p[0])
    return ccw(a, c, d) != ccw(b, c, d) and ccw(a, b, c) != ccw(a, b, d)

def place_all(S, plans):
    """Joint placement: each inset near ITS hotspot, never nearer to another hotspot, no crossing links, no overlaps."""
    import itertools, random
    cands = []
    boxes_ = [box(*I['bbox']).buffer(2 * S.m) for I in plans]
    for I in plans:
        c = [(r, 1.0) for r in _candidates(S, I, False)] + [(r, 1.1) for r in _candidates(S, I, True)]
        c += [(r, 1.25) for r in _margin_candidates(S, I)]
        c = [t for t in c if not any(t[0].intersects(bx) for bx in boxes_)]   # never over an indicator
        hp = Point(I['cx'], I['cy']); c.sort(key=lambda t: t[0].distance(hp) * t[1]); cands.append(c[:60])
    hps = [Point(I['cx'], I['cy']) for I in plans]
    best = (float('inf'), None)
    n_ = len(plans)
    if n_ <= 5: orders = list(itertools.permutations(range(n_)))
    else:
        rnd = random.Random(7); base = sorted(range(n_), key=lambda i: len(cands[i]))
        orders = [tuple(base)] + [tuple(rnd.sample(range(n_), n_)) for _ in range(250)]
    def cost_of(i, r, w):
        d = r.distance(hps[i]) * w
        own = r.distance(hps[i]); other = min([r.distance(hps[j]) for j in range(len(plans)) if j != i] or [float('inf')])
        return d + (400 * S.m if other < own else 0)
    for order in orders:
        chosen = [None] * len(plans); total = 0
        for i in order:
            pick = None
            for r, w in cands[i]:
                if any(chosen[j] is not None and r.distance(chosen[j]) < 3 * S.m for j in range(len(plans))): continue
                c = cost_of(i, r, w)
                if pick is None or c < pick[0]: pick = (c, r)
                if c <= r.distance(hps[i]) * w: break   # nearest valid and owned
            if pick is None: continue
            chosen[i] = pick[1]; total += pick[0]
        # crossing penalty between hotspot->inset links
        pts = [(hps[i].coords[0], chosen[i].centroid.coords[0]) for i in range(len(plans)) if chosen[i] is not None]
        for a in range(len(pts)):
            for b in range(a + 1, len(pts)):
                if _segments_cross(pts[a][0], pts[a][1], pts[b][0], pts[b][1]): total += 300 * S.m
        total += 1e6 * sum(plans[i].get('prio', 1.0) for i, c in enumerate(chosen) if c is None)
        if total < best[0]: best = (total, chosen)
    return best[1] or [None] * len(plans)

def sub_sheet(S, bbox, scale, rect):
    T = Sheet.__new__(Sheet); T.cfg = S.cfg; T.mode = S.mode; T.P = S.P; T.fig = S.fig
    T.x0, T.y0, T.x1, T.y1 = bbox; T.scale = scale; T.m = scale / 1000; T.dense = True; T.wobf = S.wobf; T.inset = True
    T.pw, T.ph = S.pw, S.ph
    rx0, ry0, rx1, ry1 = rect.bounds   # rect in parent ground coords -> page mm
    mm = lambda gx, gy: (S.mx + (gx - S.x0) / S.m, S.my + (gy - S.y0) / S.m)
    a = mm(rx0 + 1 * S.m, ry0 + 1 * S.m); b = mm(rx1 - 1 * S.m, ry1 - 1 * S.m)
    T.ax = S.fig.add_axes([a[0] / S.pw, a[1] / S.ph, (b[0] - a[0]) / S.pw, (b[1] - a[1]) / S.ph], zorder=30)
    T.ax.set_xlim(T.x0, T.x1); T.ax.set_ylim(T.y0, T.y1); T.ax.set_aspect('equal'); T.ax.axis('off')
    T.clip = box(*bbox)
    return T

# ---- Lupen across all sheets: one letter per area, counted on from Blatt 1 to Blatt 4
LUPEN_REG = BASE + '/data/lupen.json'
DETAIL_ORDER = ['detail_west', 'detail_mitte', 'detail_ost', 'detail_sued']   # Blatt 1..4
MANUAL_LUPEN = {   # hand-set areas: bbox (UTM), scale options (largest zoom first), preferred side for the inset
    'detail_sued': [dict(bbox=(425328, 5959196, 425432, 5959298), scales=(1500, 2000), side='west', name='Westanleger')],
}
def _plan_from_bbox(bbox, scale):
    m = scale / 1000; x0, y0, x1, y1 = bbox
    return dict(scale=scale, w=(x1 - x0) / m, h=(y1 - y0) / m, bbox=tuple(bbox), cx=(x0 + x1) / 2, cy=(y0 + y1) / 2, n=0)

RELEVANT = {'bench', 'rescue', 'shelter', 'gate', 'info', 'peak', 'lighthouse', 'observatory', 'food', 'memorial', 'fire', 'picnic',
            'playground', 'fitness', 'toilet', 'ring', 'flag', 'tree'}   # OL-relevant; pure Kleinkram stacks (hydrant+container) need no Lupe
OVERLAP_NEW = 0.30   # body overlap (share of the smaller symbol) from which a pair gets its own Lupe
OVERLAP_MIN = 0.12   # ... from which an existing Lupe is also shown on a further sheet
FRAME = (423750, 5958850, 427150, 5961650)

def needed_groups(S, thr=None):
    """Member lists that need a Lupe on this sheet: dense hotspots + overlapping symbol pairs (with an OL-relevant symbol)."""
    thr = OVERLAP_MIN if thr is None else thr
    groups = [h for h in find_hotspots(S) if any(q['kind'] in RELEVANT for q in h)]
    D = [d for d in S.drawn if d['kind'] != 'groyne']
    body = [symbols2.knock_geom(*item_draw_args(S, d)[:3], S.m, item_draw_args(S, d)[3], extra_mm=0.0) for d in D]
    par = list(range(len(D)))
    def f_(a):
        while par[a] != a: par[a] = par[par[a]]; a = par[a]
        return a
    for i in range(len(D)):
        for j in range(i + 1, len(D)):
            if not body[i].intersects(body[j]): continue
            if body[i].intersection(body[j]).area < thr * min(body[i].area, body[j].area): continue
            if D[i]['kind'] in RELEVANT or D[j]['kind'] in RELEVANT: par[f_(i)] = f_(j)
    comp = {}
    for i in range(len(D)): comp.setdefault(f_(i), []).append(i)
    for c in comp.values():
        if len(c) >= 2: groups.append([m for a in c for m in D[a]['members']])
    return groups

def _clamp_plan(I):
    x0, y0, x1, y1 = I['bbox']; dx = max(0, FRAME[0] - x0) - max(0, x1 - FRAME[2]); dy = max(0, FRAME[1] - y0) - max(0, y1 - FRAME[3])
    I['bbox'] = (x0 + dx, y0 + dy, x1 + dx, y1 + dy); I['cx'] += dx; I['cy'] += dy
    return I

def build_lupen_registry():
    """Pre-pass over Blatt 1-4: collect areas that need a Lupe, merge the same area across sheets, letters A, B, C ... once."""
    areas = []   # dict(mem={id: item}, sheets=[...], manual)
    for name in DETAIL_ORDER:
        for M in MANUAL_LUPEN.get(name, []):
            areas.append(dict(mem={}, sheets=[name], manual=M))
    weak = []   # (sheet, group) that only justify showing an existing Lupe
    for name in DETAIL_ORDER:
        S = Sheet(name, 'color'); layer_points(S)
        strong = needed_groups(S, OVERLAP_NEW); sids = [{q['p']['id'] for q in g} for g in strong]
        weak += [(name, g) for g in needed_groups(S, OVERLAP_MIN) if {q['p']['id'] for q in g} not in sids]
        for g in strong:
            cx, cy = np.mean([q['x'] for q in g]), np.mean([q['y'] for q in g]); ids = {q['p']['id'] for q in g}
            hit = None
            for a in areas:
                if a['manual']:
                    if box(*a['manual']['bbox']).buffer(10).contains(Point(cx, cy)): hit = a; break
                    continue
                xs = [q['x'] for q in a['mem'].values()] + [q['x'] for q in g]; ys = [q['y'] for q in a['mem'].values()] + [q['y'] for q in g]
                ax_, ay_ = np.mean([q['x'] for q in a['mem'].values()]), np.mean([q['y'] for q in a['mem'].values()])
                if (ids & set(a['mem'])) or (math.hypot(cx - ax_, cy - ay_) < 45 and np.ptp(xs) <= 60 and np.ptp(ys) <= 50): hit = a; break
            if hit is None: hit = dict(mem={}, sheets=[], manual=None); areas.append(hit)
            for q in g: hit['mem'].setdefault(q['p']['id'], q)
            if name not in hit['sheets']: hit['sheets'].append(name)
        plt.close(S.fig)
    for name, g in weak:   # a Lupe that exists anyway also appears where its symbols still touch
        ids = {q['p']['id'] for q in g}
        for a in areas:
            if not a['manual'] and (ids & set(a['mem'])) and name not in a['sheets']: a['sheets'].append(name)
    out = []
    for a in areas:
        plan = _plan_from_bbox(a['manual']['bbox'], a['manual']['scales'][0]) if a['manual'] else _clamp_plan(plan_inset(list(a['mem'].values())))
        kinds = sorted({q['kind'] for q in a['mem'].values()})
        out.append(dict(sheets=sorted(a['sheets'], key=DETAIL_ORDER.index), plan=plan, manual=a['manual'], n=len(a['mem']), kinds=kinds))
    out.sort(key=lambda e: (DETAIL_ORDER.index(e['sheets'][0]), -e['plan']['cy'], e['plan']['cx']))
    for i, e in enumerate(out): e['L'] = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[i]
    json.dump(out, open(LUPEN_REG, 'w'), indent=1)
    for o in out: print(o['L'], o['sheets'], o['plan']['scale'], [round(v) for v in o['plan']['bbox']], 'manuell' if o['manual'] else (o['n'], o['kinds']))
    return out

def draw_insets(S, name):
    if not name.startswith('detail'): return []
    reg = json.load(open(LUPEN_REG)) if os.path.exists(LUPEN_REG) else build_lupen_registry()
    mine = [e for e in reg if name in e['sheets']]; done = []
    plans = []
    for e in mine:
        if e['manual']:   # largest zoom that still finds free space on the preferred side
            for sc in e['manual']['scales']:
                I = _plan_from_bbox(e['manual']['bbox'], sc); I['side'] = e['manual'].get('side')
                if _candidates(S, I, False, 5) or _candidates(S, I, True, 5): break
            plans.append(I)
        else: plans.append(dict(e['plan']))
        # priority when space is short: Lupen not shown on another sheet and severe stacks (Aussichtsdüne, Leuchtturm, Hütte) first
        plans[-1]['prio'] = (2.0 if len(e['sheets']) == 1 else 1.0) + (0.6 if set(e.get('kinds', [])) & {'peak', 'lighthouse', 'shelter'} else 0) + 0.1 * min(e.get('n', 2), 6) + (5 if e['manual'] else 0)
    rects = place_all(S, plans) if plans else []
    # Lupen in the margin strip: left -> right in letter order (only swaps equal sizes)
    mg = [i for i in range(len(plans)) if rects[i] is not None and rects[i].bounds[3] < S.y0]
    if len(mg) > 1 and len({(round(plans[i]['w'], 1), round(plans[i]['h'], 1)) for i in mg}) == 1:
        slots = sorted([rects[i] for i in mg], key=lambda r: r.bounds[0])
        for i, r in zip(sorted(mg, key=lambda i: mine[i]['L']), slots): rects[i] = r
    miss = [mine[i]['L'] for i in range(len(plans)) if rects[i] is None]
    if miss: print('  Lupen ohne Platz:', miss)
    for i in [i for i in range(len(plans)) if rects[i] is not None]:
        I, r, L = plans[i], rects[i], mine[i]['L']
        done.append((L, I, r))
        T = sub_sheet(S, I['bbox'], I['scale'], r); T.ax.set_gid(f'L-lupen-ax{L}')
        T.ax.add_patch(MPoly([(T.x0, T.y0), (T.x1, T.y0), (T.x1, T.y1), (T.x0, T.y1)], closed=True, fc=S.P['paper'], ec='none', zorder=0.1))
        T.lowg = S.lowg
        with tag(T, 'sea'): T.fill(S.lowg, S.P['sea'], z=0.5)
        layer_areas(T); layer_contours(T); layer_ruhezone(T); layer_lines(T); layer_buildings(T); layer_points(T)
        T.line([(T.x0, T.y0), (T.x1, T.y0), (T.x1, T.y1), (T.x0, T.y1), (T.x0, T.y0)], 'if' + L, S.P['purple'], 1.2, amp=0.1, z=40, double=False)
        T.ax.add_patch(MPoly([(T.x0, T.y1 - 3.8 * T.m), (T.x1, T.y1 - 3.8 * T.m), (T.x1, T.y1), (T.x0, T.y1)], closed=True, fc=S.P['paper'], ec='none', alpha=0.9, zorder=39))
        T.ax.text(T.x0 + 1.4 * T.m, T.y1 - 1.9 * T.m, f'{L}  1 : {I["scale"]:,}'.replace(',', '.'), fontproperties=HANDB, fontsize=7.5, color=S.P['purple'], ha='left', va='center', zorder=41)
        sbm = 5 if I['scale'] <= 500 else (10 if I['scale'] <= 1000 else (20 if I['scale'] <= 2000 else 50))
        T.ax.add_patch(MPoly([(T.x0, T.y0), (T.x1, T.y0), (T.x1, T.y0 + 3.2 * T.m), (T.x0, T.y0 + 3.2 * T.m)], closed=True, fc=S.P['paper'], ec='none', alpha=0.9, zorder=39))
        bx, by = T.x0 + 1.5 * T.m, T.y0 + 1.6 * T.m
        T.ax.plot([bx, bx + sbm], [by, by], color=S.P['ink'], lw=1.1, zorder=41, solid_capstyle='butt')
        for xx in (bx, bx + sbm): T.ax.plot([xx, xx], [by - 0.5 * T.m, by + 0.5 * T.m], color=S.P['ink'], lw=0.6, zorder=41)
        T.ax.text(bx + sbm + 1.2 * T.m, by, f'{sbm} m', fontproperties=SERIF, fontsize=5.5, ha='left', va='center', zorder=41, color=S.P['ink'])
        # indicator on the main map + leader line
        x0, y0, x1, y1 = I['bbox']
        _tg = tag(S, 'lupen'); _tg.__enter__()
        S.ax.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], color=S.P['purple'], lw=0.7, zorder=7.5, solid_joinstyle='miter')
        S.fig.canvas.draw(); rend = S.fig.canvas.get_renderer()
        others = [t.get_window_extent(rend) for t in S.ax.texts if t.get_text().strip()]
        from matplotlib.transforms import Bbox
        for dd in S.drawn:
            hw_ = sym_halfw(dd) * S.m; (p0, q0), (p1, q1) = S.ax.transData.transform((dd['x'] - hw_, dd['y'] - hw_)), S.ax.transData.transform((dd['x'] + hw_, dd['y'] + hw_))
            others.append(Bbox([[p0, q0], [p1, q1]]))
        xm_, ym_ = (x0 + x1) / 2, (y0 + y1) / 2; best_ = None
        for k_, (lx_, ly_, ha_, va_) in enumerate(((x0 - 0.12 * S.m, y1 + 0.05 * S.m, 'right', 'bottom'), (x1 + 0.12 * S.m, y1 + 0.05 * S.m, 'left', 'bottom'),
                                     (x0 - 0.12 * S.m, y0 - 0.05 * S.m, 'right', 'top'), (x1 + 0.12 * S.m, y0 - 0.05 * S.m, 'left', 'top'),
                                     (xm_, y1 + 0.1 * S.m, 'center', 'bottom'), (xm_, y0 - 0.1 * S.m, 'center', 'top'),
                                     (x0 - 0.2 * S.m, ym_, 'right', 'center'), (x1 + 0.2 * S.m, ym_, 'left', 'center'))):
            tl = S.ax.text(lx_, ly_, L, fontproperties=SERIF, fontsize=6.5, color=S.P['purple'], ha=ha_, va=va_, zorder=26)
            bb_ = tl.get_window_extent(rend); c_ = sum(1 for o in others if bb_.overlaps(o)) + 0.01 * k_
            if best_ is None or c_ < best_[0]:
                if best_ is not None: best_[1].remove()
                best_ = (c_, tl)
            else: tl.remove()
            if c_ < 0.5: break
        _tg.__exit__(None, None, None)
    return done

LABELS = [  # (text, x, y, dx_mm, dy_mm, size_overview, size_detail, bold)
    ('Inselheim Rüstringen\nmit Sternwarte', 424331, 5960262, -1.6, 0.4, 7, 8.5, True),
    ('Westturm (DJH)', 424731, 5960172, 2.4, -2.2, 7, 8.5, True),
    ('Neuer Leuchtturm', 424713, 5960773, 2.3, 0.5, 7, 8.5, True),
    ('Westanleger', 425328, 5959005, 2.3, 0, 7, 8.5, True),
    ('Westkap', 424225, 5960443, -1.5, 2.6, 6, 7.5, False),
    ('Schalksmühle', 424394, 5960317, 2.0, 1.4, 5.5, 7, False),
    ('Gutenbergheim', 424484, 5960217, 1.5, -1.8, 5.5, 7, False),
    ('Westeroog', 424595, 5960215, 1.0, 2.2, 5.5, 7, False),
    ('Jan Seedorf', 425927, 5961076, 2.6, 0.8, 6, 7.5, False),
    ('Kriegsgräberstätte', 426643, 5961034, 1.8, 1.6, 6, 7.5, False),
    ('Aussichtsdüne 17 m', 426895, 5961133, -1.2, 3.0, 6, 7.5, False),
    ('W E S T G R O D E N', 424950, 5960470, 0, 0, 9, 13, False),
    ('Westlagune', 425500, 5960180, 0, 0, 6.5, 8, False),
    ('Salinenbucht', 425629, 5960255, 0, -2.5, 6.5, 8, False),
    ('Ruhezone I/32', 425120, 5959650, 0, 0, 7, 9, False),
    ('Strand', 425600, 5961265, 0, 0, 7, 9, False),
    ('Straße zum Westen', 425350, 5960862, 0, 1.6, 5.5, 7.5, False),
    ('Bielefelder Haus', 426822, 5961042, 1.5, -1.8, 5.5, 7, False),
    ('Standort alter Westturm', 424272, 5960834, 2.2, 0.0, 5.5, 7, False),
]
def layer_labels(S):
    with tag(S, 'labels'): _labels(S)
def _labels(S):
    """Place labels; try the configured offset first, then alternatives, avoiding other texts and symbols."""
    P = S.P
    OV = {'Inselheim Rüstringen\nmit Sternwarte': (-2.0, -2.6, 'right'), 'Westturm (DJH)': (2.4, -2.6, 'left')}
    S.fig.canvas.draw(); rend = S.fig.canvas.get_renderer(); trd = S.ax.transData
    occupied = [t.get_window_extent(rend) for t in S.ax.texts if t.get_text().strip()]
    sym_px = [trd.transform((d['x'], d['y'])) for d in getattr(S, 'drawn', [])]
    blds_ = [g for g in (way_geom(w) for w, v in W.items() if 'building' in v['tags']) if g is not None and g.geom_type == 'Polygon' and g.intersects(S.clip)]
    blds_ += [g for g in (rel_geom(r) for r, v in R.items() if 'building' in v['tags']) if g is not None and g.intersects(S.clip)]
    from shapely.strtree import STRtree as _ST
    _bt = _ST(blds_) if blds_ else None
    inv = trd.inverted()
    lines_ = [g for g in (way_geom(w) for w, v in W.items() if v['tags'].get('highway') or v['tags'].get('railway') == 'narrow_gauge') if g is not None and g.intersects(S.clip)]
    _lt = _ST(lines_) if lines_ else None
    def gbox(bb):
        (a0, b0), (a1, b1) = inv.transform((bb.x0, bb.y0)), inv.transform((bb.x1, bb.y1))
        return box(min(a0, a1), min(b0, b1), max(a0, a1), max(b0, b1))
    def penalty(bb):
        axb = S.ax.get_window_extent(rend)
        out_ = bb.x0 < axb.x0 + 2 or bb.x1 > axb.x1 - 2 or bb.y0 < axb.y0 + 2 or bb.y1 > axb.y1 - 2
        p_ = sum(1 for o in occupied if bb.padded(3).overlaps(o)) * 2 + sum(1 for (px, py) in sym_px if bb.contains(px, py)) + (10 if out_ else 0)
        gb = gbox(bb)
        if _bt is not None: p_ += sum(blds_[i].intersection(gb).area for i in _bt.query(gb)) / max(gb.area, 1) * 6
        if _lt is not None: p_ += sum(lines_[i].intersection(gb).length for i in _lt.query(gb)) / max(gb.length, 1) * 1.5
        return p_
    for txt, x, y, dx, dy, so, sd, b in LABELS:
        if not S.clip.contains(Point(x, y)): continue
        sz = sd if S.dense else so
        if not S.dense and so <= 5.5: continue
        if 'Inselheim' in txt and S.scale >= 7500: txt = 'Inselheim\nRüstringen\nmit Sternwarte'; sz = 7.5
        col = P['purple'] if txt.startswith('Ruhezone') else (P['blue'] if txt in ('Westlagune', 'Salinenbucht') else P['ink'])
        rot = 18 if txt.startswith('Straße') else 0
        if not S.dense and txt in OV: dx, dy, ha = OV[txt]
        else: ha = 'center' if dx == 0 and dy == 0 else ('right' if dx < 0 else 'left')
        cands = [(dx, dy, ha)]
        if ha == 'center':   # area labels: small shifts only
            cands += [(dx + ox_, dy + oy_, ha) for ox_, oy_ in ((0, 1.5), (0, -1.5), (2.5, 0), (-2.5, 0), (2.5, 1.5), (-2.5, -1.5), (0, 3), (0, -3), (5, 0), (-5, 0))]
        if ha != 'center':
            for rr in (1.8, 3.5, 6.0):
                for ang in range(0, 360, 30):
                    cx_ = rr * math.cos(math.radians(ang)); cy_ = rr * math.sin(math.radians(ang))
                    ha_ = 'left' if cx_ > 0.5 else ('right' if cx_ < -0.5 else 'center')
                    cands.append((cx_ if abs(cx_) > 0.5 else 0.01, cy_, ha_))
        best = None
        for (cx_, cy_, ha_) in cands:
            t = S.ax.text(x + cx_ * S.m, y + cy_ * S.m, txt, fontproperties=HANDB if b else HAND, fontsize=sz, color=col, ha=ha_, va='center', zorder=12, rotation=rot,
                          path_effects=[pe.withStroke(alpha=HALO_A, linewidth=2.2, foreground=P['paper'])])
            bb = t.get_window_extent(rend)
            bad = penalty(bb)
            if best is None or bad < best[0]:
                if best is not None: best[1].remove()
                best = (bad, t, bb)
            else: t.remove()
            bad += 0.04 * (abs(cx_) + abs(cy_)) if (cx_, cy_, ha_) != (dx, dy, ha) else 0
            if bad < 0.05: break
        if best[0] > 1.5 and ha != 'center' and hasattr(S, 'lowg'):
            # fallback: put the label on open water nearby and draw a thin leader to the object
            t0 = best[1]; wbb = best[2]; gw = gbox(wbb); Wg, Hg = gw.bounds[2] - gw.bounds[0], gw.bounds[3] - gw.bounds[1]
            sea_ok = S.lowg.intersection(S.clip.buffer(-2 * S.m)); found = None
            for rr in np.arange(3, 11, 1.0):
                for ang in range(0, 360, 15):
                    cx_ = x + rr * S.m * math.cos(math.radians(ang)); cy_ = y + rr * S.m * math.sin(math.radians(ang))
                    gb2 = box(cx_ - Wg / 2, cy_ - Hg / 2, cx_ + Wg / 2, cy_ + Hg / 2)
                    if not sea_ok.contains(gb2): continue
                    (p0x, p0y), (p1x, p1y) = trd.transform((gb2.bounds[0], gb2.bounds[1])), trd.transform((gb2.bounds[2], gb2.bounds[3]))
                    if any(not (p1x < o.x0 or p0x > o.x1 or p1y < o.y0 or p0y > o.y1) for o in occupied): continue
                    found = (cx_, cy_, gb2); break
                if found: break
            if found:
                t0.remove(); cx_, cy_, gb2 = found
                t = S.ax.text(cx_, cy_, txt, fontproperties=HANDB if b else HAND, fontsize=sz, color=col, ha='center', va='center', zorder=12,
                              path_effects=[pe.withStroke(alpha=HALO_A, linewidth=2.2, foreground=P['paper'])])
                from shapely.ops import nearest_points
                q = nearest_points(gb2.buffer(0.6 * S.m), Point(x, y))[0]
                S.ax.plot([q.x, x], [q.y, y], color=col, lw=0.45, zorder=11.5)
                best = (0, t, t.get_window_extent(rend))
        occupied.append(best[2])

def layer_northlines(S):
    with tag(S, 'north'): _northlines(S)
def _northlines(S):
    P = S.P; sp = 250 if S.dense else 500
    for x in np.arange(math.ceil(S.x0 / sp) * sp, S.x1, sp):
        S.line([(x, S.y0), (x, S.y1)], f'nl{x}', P['blue'] if S.mode == 'color' else '#999999', 0.35, amp=0.08, double=False, z=6, alpha=0.6)

def layer_sheet_index(S):
    with tag(S, 'sheetindex'): _sheet_index(S)
def _sheet_index(S):
    P = S.P
    for i, (k, lab) in enumerate((('detail_west', 'Blatt 1'), ('detail_mitte', 'Blatt 2'), ('detail_ost', 'Blatt 3'), ('detail_sued', 'Blatt 4'))):
        x0, y0, x1, y1 = SHEETS[k]['bbox']
        S.line([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], 'si' + k, P['purple'], 0.6, amp=0.1, double=False, z=15, dashes=(2, 2), alpha=0.75)
        S.ax.text(x0 + 1.2 * S.m, y1 - 1.0 * S.m, lab, fontproperties=HANDB, fontsize=7, color=P['purple'], ha='left', va='top', zorder=16,
                  bbox=dict(boxstyle='square,pad=0.08', fc=S.P['paper'], ec='none', alpha=0.8))

def frame_and_margin(S, name):
    P = S.P; ax = S.ax
    # sketchy frame around map
    S.line([(S.x0, S.y0), (S.x1, S.y0), (S.x1, S.y1), (S.x0, S.y1), (S.x0, S.y0)], 'frame', P['ink'], 1.0, amp=0.15, z=20)
    fig = S.fig; pw, ph = S.pw, S.ph
    def T(xmm, ymm, txt, size, bold=False, ha='left', va='baseline', color=None, font=None):
        fig.text(xmm / pw, ymm / ph, txt, fontproperties=font or (HANDB if bold else HAND), fontsize=size, ha=ha, va=va, color=color or P['ink'])
    # scale bar drawn in a small axes
    def scalebar(xmm, ymm, length_m):
        a = fig.add_axes([xmm / pw, ymm / ph, (length_m / S.m) / pw, 4 / ph]); a.axis('off'); a.set_xlim(0, length_m); a.set_ylim(0, 1)
        n = 5 if length_m >= 500 else 4
        for i in range(n):
            x0 = i * length_m / n; x1 = (i + 1) * length_m / n
            a.add_patch(MPoly([(x0, 0.35), (x1, 0.35), (x1, 0.6), (x0, 0.6)], fc=P['ink'] if i % 2 == 0 else P['paper'], ec=P['ink'], lw=0.5))
        a.text(0, 0.9, '0', fontproperties=HAND, fontsize=7, ha='center'); a.text(length_m, 0.9, f'{length_m} m', fontproperties=HAND, fontsize=7, ha='center')
    cfg = S.cfg
    if name == 'uebersicht':
        lx = S.mx + S.mw + 6; ty = ph - 14
        T(lx, ty, cfg['title'], 22, True); T(lx, ty - 7, 'Orientierungslauf-Karte', 11)
        T(lx, ty - 13, f'1 : {S.scale:,}'.replace(',', '.') + '  ·  Äquidistanz 2,5 m', 9.5)
        scalebar(lx, ty - 22, 500)
        legend(S, lx, ty - 30)
    else:
        T(S.mx, 12, cfg['title'] + '  –  ' + cfg['sub'], 15, True)
        T(S.mx, 6.5, f'1 : {S.scale:,}'.replace(',', '.') + '  ·  Äquidistanz 2,5 m  ·  Nordlinien 250 m', 8.5)
        scalebar(S.mx + S.mw - 60, 8, 250)
    T(pw - 4, 3 if name == 'uebersicht' else ph - 5, 'Daten: © OpenStreetMap-Mitwirkende (ODbL) · LGLN (2026) DGM1 & DOP20 (19.10.2025), CC BY 4.0 · Version 1.4 vom 12.10.2026',
      5, ha='right', font=PRINT, color=P['gray'])
    # north arrow
    nx, ny = (S.mx + S.mw - 8, S.my + S.mh - 14) if name != 'uebersicht' else (S.mx + S.mw - 9, S.my + S.mh - 16)
    a = fig.add_axes([nx / pw, ny / ph, 7 / pw, 12 / ph]); a.axis('off'); a.set_xlim(-1, 1); a.set_ylim(-1, 1.6)
    a.add_patch(MPoly([(0, 1.0), (-0.45, -0.6), (0, -0.25), (0.45, -0.6)], fc=P['ink'], ec=P['ink'], lw=0.5))
    a.text(0, 1.3, 'N', fontproperties=HANDB, fontsize=10, ha='center', va='center', color=P['ink'])

LEG_LAYER = dict(road='roads', foot='paths', path='paths', board='paths', steps='paths', bridge='paths', rail='rail', railx='rail', fence='structures', dyke='structures',
                 cont='contours', steep='steep', summit='summits', pit='pits', water='water', open='open', scrub='veg', forest='veg', sand='sand', rz='ruhezone',
                 bld='buildings', pitch='buildings', lupe='lupen', group='bench', groyne='structures')
def legend(S, lx, ty, width=54):
    P = S.P; fig = S.fig; pw, ph = S.pw, S.ph
    cols = [[
        ('road', 'Straße / Hauptweg'), ('foot', 'befestigter Weg'), ('path', 'Pfad'), ('board', 'Holzsteg'),
        ('steps', 'Treppe / Übergang'), ('rail', 'Inselbahn'), ('railx', 'Bahnübergang'), ('bridge', 'Brücke / Durchlass'), ('fence', 'Zaun'),
        ('dyke', 'Deich'), ('cont', 'Höhenlinie 2,5 m'), ('steep', 'Steilhang'), ('summit', 'Kuppe, Höhe m'), ('pit', 'Grube / Trichter'),
        ('water', 'Tümpel / Wasser'), ('open', 'offene Wiese'), ('scrub', 'Gebüsch'), ('forest', 'Wäldchen'), ('sand', 'Sand / Strand'),
        ('rz', 'Ruhezone'), ('bld', 'Gebäude'), ('pitch', 'Sportplatz'), ('lupe', 'Lupe (1:1.000)'),
    ], [
        ('bench', 'Bank'), ('group', 'Anzahl (ab 7 römisch)'), ('rescue', 'SOS-Schild + Nr.'), ('shelter', 'Schutzhütte'), ('gate', 'Tor / Durchlass'),
        ('info', 'Infotafel'), ('food', 'Gastronomie'), ('lighthouse', 'Leuchtturm'), ('observatory', 'Sternwarte'), ('peak', 'Aussichtsdüne'),
        ('memorial', 'Gedenkstätte'), ('milestone', 'km-Stein Bahn'), ('station', 'Haltepunkt Bahn'), ('groyne', 'Buhne + Name'), ('hydrant', 'Hydrant'),
        ('playground', 'Spielplatz'), ('fitness', 'Fitnessgerät'), ('recycling', 'Container'), ('bike', 'Fahrradständer'), ('substation', 'Trafostation'),
        ('toilet', 'WC'), ('ring', 'Rettungsring'), ('fire', 'Feuerstelle'), ('picnic', 'Picknickplatz'),
    ]]
    h = 4.3; NR = max(len(c) for c in cols); col_w = width / 2
    a = fig.add_axes([lx / pw, (ty - h * NR - 2) / ph, width / pw, (h * NR + 2) / ph]); a.axis('off')
    a.set_xlim(0, width); a.set_ylim(-h * NR - 2, 2)
    M = Sheet.__new__(Sheet); M.ax = a; M.m = 1.0; M.P = P; M.mode = S.mode; M.wobf = 0.3
    for ci, items in enumerate(cols):
        for r, (k, txt) in enumerate(items):
            x = ci * col_w; y = -r * h - 1.5
            _tg = _Tag(a, LEG_LAYER.get(k, KIND_LAYER.get(k, 'facilities'))); _tg.__enter__()
            sx, ex = x + 0.5, x + 6.5; cx = (sx + ex) / 2
            def ln(color, lw, dashes=None, amp=0.18):
                M.line([(sx, y), (ex, y)], k, color, lw, amp=amp, dashes=dashes, double=lw >= 0.5)
            def box_(fc, ec='none', lw=0.4, alpha=1):
                a.add_patch(MPoly([(sx, y - 0.9), (ex, y - 0.9), (ex, y + 0.9), (sx, y + 0.9)], fc=fc, ec=ec, lw=lw, alpha=alpha))
            if k == 'road': ln(P['ink'], 1.6)
            elif k == 'foot': ln(P['ink'], 0.85)
            elif k == 'path': ln(P['ink'], 0.6, (1.8, 1.4))
            elif k == 'pathg': ln(P['gray'], 0.6, (1.8, 1.4))
            elif k == 'board':
                ln(P['ink'], 0.85)
                for dy_ in (0.45, -0.45): a.plot([sx, ex], [y + dy_, y + dy_], color=P['ink'], lw=0.4)
            elif k == 'steps':
                ln(P['ink'], 0.6)
                for xx in np.linspace(sx + 1, ex - 1, 4): a.plot([xx, xx], [y - 0.7, y + 0.7], color=P['ink'], lw=0.55)
            elif k in ('rail', 'railx'):
                ln(P['ink'], 0.7)
                for xx in np.linspace(sx + 1, ex - 1, 3): a.plot([xx, xx], [y - 0.55, y + 0.55], color=P['ink'], lw=0.45)
                if k == 'railx': M.sym('railx', cx, y, P['ink'], k, 0.8)
            elif k == 'bridge':
                ln(P['ink'], 0.85)
                for sg in (1, -1):
                    a.plot([cx - 2.0, cx - 1.6, cx + 1.6, cx + 2.0],
                           [y + sg * 1.1, y + sg * 0.75, y + sg * 0.75, y + sg * 1.1], color=P['ink'], lw=0.55)
            elif k == 'fence':
                ln(P['ink'], 0.35)
                for xx in np.linspace(sx + 1, ex - 1, 3): a.plot([xx, xx], [y, y + 0.6], color=P['ink'], lw=0.35)
            elif k == 'dyke': ln(P['brown'], 1.1)
            elif k == 'cont': ln(P['contour'], 0.34)
            elif k == 'steep':
                a.plot([sx + 0.5, ex - 0.5], [y + 0.4, y + 0.4], color=P['brown'], lw=1.0, solid_capstyle='butt')
                for xx in np.arange(sx + 0.9, ex - 0.4, 1.0): a.plot([xx, xx], [y + 0.4, y - 0.3], color=P['brown'], lw=0.6)
            elif k == 'summit':
                M.sym('summit', cx - 1.2, y, P['brown'], k)
                a.text(cx - 0.6, y, '12', fontproperties=SERIF, fontsize=4.8, color=P['brown'], ha='left', va='center_baseline')
            elif k == 'pit': M.sym('pit', cx, y, P['brown'], k)
            elif k == 'water': box_(P['water'], P['blue'], 0.45)
            elif k == 'open': box_(P['open'])
            elif k in ('scrub', 'forest'):
                for xx in np.arange(sx - 2, ex, 1.6 if k == 'scrub' else 1.1):
                    x0_, x1_ = max(sx, xx), min(ex, xx + 1.8)
                    a.plot([x0_, x1_], [y - 0.9 + (x0_ - xx), y - 0.9 + (x1_ - xx)], color=P['green'], lw=0.3)
                    if k == 'forest': a.plot([x0_, x1_], [y + 0.9 - (x0_ - xx), y + 0.9 - (x1_ - xx)], color=P['green'], lw=0.3)
            elif k == 'sand':
                rr = np.random.default_rng(1); a.scatter(rr.uniform(sx, ex, 22), rr.uniform(y - 0.9, y + 0.9, 22), s=0.35, c=P['sand'], lw=0)
            elif k == 'rz':
                for xx in np.arange(sx, ex - 0.9, 1.6):
                    a.plot([xx, xx + 1.0], [y + 0.9, y - 0.9], color=P['purple'], lw=0.3, alpha=0.6)
                a.plot([sx, ex], [y - 0.9, y - 0.9], color=P['purple'], lw=0.9, dashes=(4, 2.5))
            elif k == 'bld': a.add_patch(MPoly([(sx + 1.5, y - 0.8), (ex - 1.5, y - 0.8), (ex - 1.5, y + 0.8), (sx + 1.5, y + 0.8)], fc=P['ink'], ec='none', alpha=0.88))
            elif k == 'pitch': a.add_patch(MPoly([(sx + 0.8, y - 0.8), (ex - 0.8, y - 0.8), (ex - 0.8, y + 0.8), (sx + 0.8, y + 0.8)], fc='none', ec=P['ink'], lw=0.35))
            elif k == 'lupe':
                a.add_patch(MPoly([(sx + 1.6, y - 0.9), (ex - 0.6, y - 0.9), (ex - 0.6, y + 0.9), (sx + 1.6, y + 0.9)], fc='none', ec=P['purple'], lw=0.8))
                a.text(sx + 1.3, y, 'A', fontproperties=SERIF, fontsize=5.5, ha='right', va='center', color=P['purple'])
            elif k == 'group':
                M.sym('bench', cx - 1.2, y, P['ink'], k); symbols2.draw_dots(a, cx - 0.1, y, 3, 1.0, P['count'], paper=P['paper'])
            elif k == 'rescue':
                M.sym('rescue', cx - 1.0, y, P['ink'], k, 0.9)
                a.text(cx - 0.3, y, '54', fontproperties=SERIF, fontsize=4.8, color=P['ink'], ha='left', va='center_baseline')
            elif k == 'milestone':
                M.sym('milestone', cx - 1.0, y, P['ink'], k)
                a.text(cx - 0.5, y, '2,4', fontproperties=SERIF, fontsize=4.8, color=P['ink'], ha='left', va='center_baseline')
            elif k == 'groyne':
                a.plot([sx, ex - 2.2], [y - 0.3, y - 0.3], color=P['ink'], lw=0.55)
                a.text(ex - 1.9, y, 'H', fontproperties=SERIF, fontsize=4.8, color=P['ink'], ha='left', va='center_baseline')
            elif k == 'observatory': M.sym('observatory', cx, y, P['ink'], k, 0.85)
            elif k in ('lighthouse',): M.sym(k, cx, y, P['ink'], k, 0.85)
            else: M.sym(k, cx, y, P['ink'], k)
            a.text(ex + 0.9, y, txt, fontproperties=HAND, fontsize=7.0, va='center', color=P['ink'])
            _tg.__exit__(None, None, None)
    yb = ty - h * NR - 5.5
    fig.text(lx / pw, yb / ph, 'Ruhezone: Wege nicht verlassen!', fontproperties=HANDB, fontsize=7.2, color=P['purple'])

def render(name, mode, out, png=None):
    S = Sheet(name, mode)
    layer_base(S); layer_areas(S); layer_contours(S); layer_ruhezone(S); layer_lines(S); layer_buildings(S)
    layer_extras(S); layer_points(S); layer_northlines(S); layer_labels(S)
    if name == 'uebersicht': layer_sheet_index(S)
    S.insets = draw_insets(S, name)
    for t in list(S.ax.texts):   # SOS numbers inside a Lupe indicator are shown in the Lupe itself
        if getattr(t, '_sos', False) and any(I['bbox'][0] <= t.get_position()[0] - 1.5 * S.m <= I['bbox'][2] and I['bbox'][1] <= t.get_position()[1] <= I['bbox'][3] for _, I, _ in S.insets): t.remove()
    frame_and_margin(S, name)
    try:
        S.fig.canvas.draw(); rend = S.fig.canvas.get_renderer()
        txts = [t for t in S.ax.texts if t.get_text().strip()]
        bbs = [(t.get_text(), t.get_window_extent(rend).expanded(1.0, 1.0)) for t in txts]
        hits = []
        for i in range(len(bbs)):
            for j in range(i + 1, len(bbs)):
                if bbs[i][1].overlaps(bbs[j][1]) and not (bbs[i][0] == bbs[j][0] == 'WC'): hits.append((bbs[i][0], bbs[j][0]))
        # insets covering main-map labels
        for ax2 in S.fig.axes:
            if ax2 is S.ax or ax2.get_zorder() < 30: continue
            ib = ax2.get_window_extent(rend)
            for tx, bb in bbs:
                if ib.overlaps(bb): hits.append(('LUPE', tx))
        tr_ = S.ax.transData
        for d in getattr(S, 'drawn', []):
            px, py = tr_.transform((d['x'], d['y']))
            for tx, bb in bbs:
                if bb.contains(px, py) and tx not in (roman(d['n']), d['members'][0]['p'].get('name', ''), 'WC'): hits.append(('SYMBOL ' + d['kind'], tx))
        if hits: print('  QA-Überlappungen:', hits[:30])
    except Exception as e: print('QA failed', e)
    print(name, mode, 'Lupen:', [(L, I['scale'], I['n']) for L, I, r in S.insets], 'Gruppen:', sum(1 for d in S.drawn if d['n'] > 1))
    S.fig.savefig(out, facecolor=S.P['paper'])
    if png: S.fig.savefig(png, dpi=DPI, facecolor=S.P['paper'])
    if SVG_OUT: save_svg(S, SVG_OUT)
    plt.close(S.fig)

SVG_OUT = None
def save_svg(S, path):
    """Layered SVG for the web app: groups carry ids L-<layer>-<n>; text as paths (no fonts needed)."""
    import matplotlib as _mpl
    with _mpl.rc_context({'svg.fonttype': 'path', 'svg.hashsalt': 'wangerooge', 'svg.id': 'wangerooge'}):
        S.fig.savefig(path, format='svg', facecolor=S.P['paper'], metadata={'Date': None})
    # bake glyph scale transforms into the path data: svg2pdf (PDF export in the app) drops some <use>d glyphs that carry their own transform
    import re
    def _bake(m):
        sc = float(m.group(3))
        d = re.sub(r'-?\d+(?:\.\d+)?(?:e-?\d+)?', lambda n: ('%.4f' % (float(n.group(0)) * sc)).rstrip('0').rstrip('.'), m.group(2))
        return f'<path id="{m.group(1)}" d="{d}"/>'
    txt = open(path).read()
    txt = re.sub(r'<path id="([^"]+)" d="([^"]*)"\s*transform="scale\(([\d.e-]+)\)"\s*/>', _bake, txt)
    open(path, 'w').write(txt)

def render_check(bbox, png, scale=5000, pxm=2.5):
    """QA: map symbols/lines over the DOP20 aerial image at true positions."""
    from dop import crop
    SHEETS['check'] = dict(bbox=bbox, scale=scale, orient='L', title='', sub='')
    S = Sheet.__new__(Sheet); S.cfg = SHEETS['check']; S.mode = 'color'; S.P = dict(PAL['color']); S.P['paper'] = '#ffffff'
    S.x0, S.y0, S.x1, S.y1 = bbox; S.scale = scale; S.m = scale / 1000; S.dense = True; S.wobf = 0.3
    S.mw, S.mh = (S.x1 - S.x0) / S.m, (S.y1 - S.y0) / S.m
    S.fig = plt.figure(figsize=(S.mw / 25.4, S.mh / 25.4))
    S.ax = S.fig.add_axes([0, 0, 1, 1]); S.ax.set_xlim(S.x0, S.x1); S.ax.set_ylim(S.y0, S.y1); S.ax.set_aspect('equal'); S.ax.axis('off')
    S.clip = box(*bbox)
    S.ax.imshow(crop(*bbox, 0.4), extent=(S.x0, S.x1, S.y0, S.y1), zorder=0, alpha=0.85)
    S.lowg = Polygon()
    layer_lines(S)
    for wid, w in W.items():
        if 'building' in w['tags']:
            g = way_geom(wid)
            if g is not None and g.geom_type == 'Polygon' and g.intersects(S.clip): S.ax.plot(*g.exterior.xy, color='yellow', lw=0.6, zorder=5)
    layer_points(S); layer_labels(S)
    S.fig.savefig(png, dpi=pxm * S.m * 25.4); plt.close(S.fig)

def render_field(png, pxm=2):
    """Whole frame as one big image for the field-check web map (no margins/legend, only certain items)."""
    SHEETS['feld'] = dict(bbox=(423750, 5958850, 427150, 5961650), scale=5000, orient='L', title='', sub='')
    S = Sheet.__new__(Sheet); cfg = SHEETS['feld']; S.cfg = cfg; S.mode = 'color'; S.P = PAL['color']
    S.x0, S.y0, S.x1, S.y1 = cfg['bbox']; S.scale = 5000; S.m = 5.0; S.field = True; S.dense = True; S.wobf = 0.3
    S.mw, S.mh = (S.x1 - S.x0) / S.m, (S.y1 - S.y0) / S.m
    S.fig = plt.figure(figsize=(S.mw / 25.4, S.mh / 25.4)); S.fig.patch.set_facecolor(S.P['paper'])
    S.ax = S.fig.add_axes([0, 0, 1, 1]); S.ax.set_xlim(S.x0, S.x1); S.ax.set_ylim(S.y0, S.y1); S.ax.set_aspect('equal'); S.ax.axis('off')
    S.clip = box(S.x0, S.y0, S.x1, S.y1)
    layer_base(S); layer_areas(S); layer_contours(S); layer_ruhezone(S); layer_lines(S); layer_buildings(S); layer_extras(S); layer_points(S); layer_labels(S)
    dpi = pxm * S.m * 25.4
    S.fig.savefig(png, dpi=dpi, facecolor=S.P['paper']); plt.close(S.fig)

if __name__ == '__main__':
    name, mode, out = sys.argv[1:4]; png = sys.argv[4] if len(sys.argv) > 4 else None
    DPI = int(sys.argv[5]) if len(sys.argv) > 5 else 110
    SVG_OUT = sys.argv[6] if len(sys.argv) > 6 else None
    render(name, mode, out, png)
