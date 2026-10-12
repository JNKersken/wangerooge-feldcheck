"""Clean vector map symbols (no jitter). Family 'B' (Silhouette) is the production set; 'A'/'C' kept for comparison sheets.
Coordinates in symbol units: 1 unit = 1 mm on paper at size=1; symbols fit roughly in [-0.9, 0.9].
draw(ax, kind, x, y, m, color, fam='B', size=1, paper=..., variant=None)
Freistellung: pass 1 draws the WHOLE symbol in paper colour, slightly fattened (outer contour only);
pass 2 draws the symbol itself on top - so no white lines appear inside the symbol."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import math
import numpy as np
from matplotlib.patches import Polygon as MPoly, Circle
from matplotlib import font_manager as fm
import matplotlib.patheffects as pe

FD = BASE + '/fonts/'
try: fm.fontManager.addfont(FD + 'PTSerif-Bold.ttf')
except Exception: pass
SERIFB = fm.FontProperties(fname=FD + 'PTSerif-Bold.ttf')
PT = 72 / 25.4          # points per mm
KNOCK_MM = 0.15         # width of the paper contour around a symbol (each side)
KNOCK_ALPHA = 1.0       # opaque paper contour; it sits below ALL symbols, so it never covers another symbol
from shapely.geometry import LineString as _LS, Polygon as _PG, Point as _PT, MultiPolygon as _MP
from shapely.ops import unary_union as _UU
from matplotlib.path import Path as _Path
from matplotlib.patches import PathPatch as _PP
from matplotlib.textpath import TextPath as _TP

def _poly_path(g):
    verts, codes = [], []
    for p in getattr(g, 'geoms', [g]):
        if p.is_empty or p.geom_type != 'Polygon': continue
        for ring in [p.exterior] + list(p.interiors):
            c = list(ring.coords); verts += c; codes += [_Path.MOVETO] + [_Path.LINETO] * (len(c) - 2) + [_Path.CLOSEPOLY]
    return _Path(verts, codes) if verts else None

def halo_patch(ax, geom, paper, z, alpha=None):
    """One merged paper contour (single artist -> uniform transparency, no darker overlaps)."""
    pa = _poly_path(geom)
    if pa is not None: ax.add_patch(_PP(pa, fc=paper, ec='none', alpha=KNOCK_ALPHA if alpha is None else alpha, zorder=z))

def ink_area(kind, size=1.0, fam='B', variant=None):
    """Inked area in mm^2 at the given size: large = flächig (goes to the bottom), small = fein (on top)."""
    gs = []
    for sh in shapes(kind, fam, variant):
        t = sh[0]
        if isinstance(sh[-1], str) and sh[-1] == 'neg': continue
        if t == 'L': gs.append(_LS([(px * size, py * size) for px, py in sh[1]]).buffer(sh[2] * size / 2))
        elif t == 'P':
            pg = _PG([(px * size, py * size) for px, py in sh[1]]).buffer(0)
            gs.append(pg.buffer((sh[3] or 0) * size / 2) if sh[2] else pg.exterior.buffer(max(sh[3], 0.05) * size / 2))
        elif t == 'C':
            cx, cy, r, fill, wmm = sh[1:6]; c = _PT(cx * size, cy * size).buffer(r * size, 16)
            gs.append(c.buffer((wmm or 0) * size / 2) if fill else c.exterior.buffer(max(wmm, 0.05) * size / 2))
        elif t == 'T': gs.append(_PT(0, 0).buffer(0.3 * size))
    return _UU(gs).area if gs else 0.0

def _text_path(txt, h_mm, x, y, m):
    """Text as a vector path, cap height ~h_mm, centred on (x, y) in map units."""
    tp = _TP((0, 0), txt, size=h_mm * 1.15, prop=SERIFB); bb = tp.get_extents()
    v = tp.vertices.copy(); v[:, 0] = x + (v[:, 0] - (bb.x0 + bb.x1) / 2) * m; v[:, 1] = y + (v[:, 1] - (bb.y0 + bb.y1) / 2) * m
    return _Path(v, tp.codes)

def _text_geom(txt, h_mm, x, y, m):
    pa = _text_path(txt, h_mm, x, y, m); polys = [ _PG(p) for p in pa.to_polygons() if len(p) >= 3]
    # outer rings minus holes (even-odd)
    g = None
    for p in sorted(polys, key=lambda q: -q.area):
        p = p.buffer(0)
        g = p if g is None else g.symmetric_difference(p)
    return g if g is not None else _PT(x, y).buffer(0.01)

def knock_geom(kind, x, y, m, size=1.0, fam='B', variant=None, extra_mm=None):
    """Outline of the whole symbol, fattened by the knockout width, in map units."""
    sc = m * size; k = (KNOCK_MM if extra_mm is None else extra_mm) * max(0.8, min(size, 1.3)) * m
    P = lambda pts: [(x + px * sc, y + py * sc) for px, py in pts]
    gs = []
    for sh in shapes(kind, fam, variant):
        t = sh[0]
        if isinstance(sh[-1], str) and sh[-1] == 'neg': continue
        if t == 'L': gs.append(_LS(P(sh[1])).buffer(sh[2] * size * m / 2 + k, 12))
        elif t == 'P':
            pg = _PG(P(sh[1])); pg = pg if pg.is_valid else pg.buffer(0)
            gs.append(pg.buffer((sh[3] or 0) * size * m / 2 + k, 12))
        elif t == 'C':
            cx, cy, r, fill, wmm = sh[1:6]; gs.append(_PT(x + cx * sc, y + cy * sc).buffer(r * sc + (wmm or 0) * size * m / 2 + k, 16))
        elif t == 'T':
            gs.append(_text_geom(sh[1], sh[2] * size, x, y, m).buffer(k, 8))
    return _UU(gs)

def _arc(cx, cy, r, a0, a1, n=24):
    t = np.radians(np.linspace(a0, a1, n)); return list(zip(cx + r * np.cos(t), cy + r * np.sin(t)))

def _flame():
    t = np.linspace(0, 1, 30)
    left = [(-0.42 * math.sin(math.pi * s) ** 0.9 - 0.05 * s, -0.7 + 1.45 * s) for s in t]
    right = [(0.42 * math.sin(math.pi * s) ** 0.9 - 0.02 * s, -0.7 + 1.45 * s) for s in t[::-1]]
    return left + right

def shapes(kind, fam='B', variant=None):
    """Primitives: ('L', pts, w_mm[, role]) line · ('P', pts, fill, w_mm[, role]) polygon · ('C', cx, cy, r, fill, w_mm[, role]) circle · ('T', txt, size_mm[, role]).
    role 'neg' = negative space (paper colour, drawn on top, part of the motif) · 'green'/'brown'/'blue' = fixed colours."""
    A, B, C = fam == 'A', fam == 'B', fam == 'C'
    if B and variant is None: variant = {'gate': 'gatter', 'fitness': 'diag'}.get(kind)   # chosen 12.10.2026
    w = 0.17 if A else (0.24 if B else 0.18)
    S = []
    if kind == 'bench':
        if C: S += [('L', [(-0.45, -0.45), (0.45, 0.45)], 0.18), ('L', [(-0.45, 0.45), (0.45, -0.45)], 0.18)]
        elif variant == 'side': S += [('L', [(-0.75, 0.0), (0.55, 0.0)], w * 1.3), ('L', [(0.55, 0.0), (0.75, 0.65)], w), ('L', [(-0.6, 0.0), (-0.6, -0.5)], w), ('L', [(0.4, 0.0), (0.4, -0.5)], w)]
        elif B: S += [('P', [(-0.85, 0.02), (0.85, 0.02), (0.85, 0.3), (-0.85, 0.3)], True, 0), ('L', [(-0.6, 0.05), (-0.6, -0.5)], 0.26), ('L', [(0.6, 0.05), (0.6, -0.5)], 0.26)]
        else: S += [('L', [(-0.85, 0.15), (0.85, 0.15)], 0.22), ('L', [(-0.6, 0.15), (-0.6, -0.45)], w), ('L', [(0.6, 0.15), (0.6, -0.45)], w)]
    elif kind == 'rescue':
        if C: S += [('C', 0, 0, 0.42, False, 0.18)]
        elif B: S += [('P', [(-0.58, -0.58), (0.58, -0.58), (0.58, 0.58), (-0.58, 0.58)], True, 0), ('L', [(-0.34, 0), (0.34, 0)], 0.2, 'neg'), ('L', [(0, -0.34), (0, 0.34)], 0.2, 'neg')]
        else: S += [('P', [(-0.6, -0.6), (0.6, -0.6), (0.6, 0.6), (-0.6, 0.6)], False, w), ('L', [(-0.33, 0), (0.33, 0)], w * 1.25), ('L', [(0, -0.33), (0, 0.33)], w * 1.25)]
    elif kind == 'shelter':
        if C: S += [('P', [(-0.55, -0.4), (0, 0.45), (0.55, -0.4)], False, 0.18)]
        else: S += [('P', [(-0.85, -0.05), (0, 0.65), (0.85, -0.05)], B, w), ('L', [(-0.55, -0.05), (-0.55, -0.6)], w), ('L', [(0.55, -0.05), (0.55, -0.6)], w)]
    elif kind == 'gate' and variant in ('gatter', 'luecke', 'schranke', 'bogen'):
        if variant == 'gatter':     # field gate: frame with diagonal brace
            S += [('L', [(-0.72, -0.5), (-0.72, 0.5)], 0.24), ('L', [(0.72, -0.5), (0.72, 0.5)], 0.24),
                  ('L', [(-0.72, 0.36), (0.72, 0.36)], 0.17), ('L', [(-0.72, -0.3), (0.72, -0.3)], 0.17), ('L', [(-0.72, -0.3), (0.72, 0.36)], 0.17)]
        elif variant == 'luecke':   # gap in a fence: two posts, fence stubs outside
            S += [('L', [(-0.95, 0), (-0.4, 0)], 0.15), ('L', [(0.4, 0), (0.95, 0)], 0.15),
                  ('P', [(-0.5, -0.42), (-0.28, -0.42), (-0.28, 0.42), (-0.5, 0.42)], True, 0), ('P', [(0.28, -0.42), (0.5, -0.42), (0.5, 0.42), (0.28, 0.42)], True, 0)]
        elif variant == 'schranke': # barrier: post + boom with a negative stripe
            S += [('P', [(-0.75, -0.62), (-0.5, -0.62), (-0.5, 0.3), (-0.75, 0.3)], True, 0), ('C', -0.625, 0.36, 0.17, True, 0), ('L', [(-0.5, 0.2), (0.88, 0.2)], 0.22)]
        else:                       # archway: block with arched opening
            S += [('P', [(-0.72, -0.6), (-0.3, -0.6)] + _arc(0, -0.05, 0.3, 180, 0, 14) + [(0.3, -0.6), (0.72, -0.6), (0.72, 0.6), (-0.72, 0.6)], True, 0)]
    elif kind == 'fitness' and variant in ('kettle', 'diag', 'discs', 'figur'):
        if variant == 'kettle':     # kettlebell
            S += [('C', 0, -0.22, 0.48, True, 0), ('L', _arc(0, 0.2, 0.3, 200, -20, 16), 0.2)]
        elif variant == 'diag':     # dumbbell at 45 degrees
            r = lambda pts: [((px - py) * 0.7071, (px + py) * 0.7071) for px, py in pts]
            S += [('L', r([(-0.45, 0), (0.45, 0)]), 0.2), ('P', r([(-0.78, -0.36), (-0.46, -0.36), (-0.46, 0.36), (-0.78, 0.36)]), True, 0), ('P', r([(0.46, -0.36), (0.78, -0.36), (0.78, 0.36), (0.46, 0.36)]), True, 0)]
        elif variant == 'discs':    # barbell with round plates
            S += [('L', [(-0.85, 0), (0.85, 0)], 0.16), ('C', -0.5, 0, 0.3, True, 0), ('C', 0.5, 0, 0.3, True, 0)]
        else:                       # star-jump figure
            S += [('C', 0, 0.58, 0.18, True, 0), ('L', [(-0.6, 0.48), (0, 0.12), (0.6, 0.48)], 0.17), ('L', [(0, 0.12), (0, -0.12)], 0.2), ('L', [(-0.45, -0.72), (0, -0.12), (0.45, -0.72)], 0.17)]
    elif kind == 'gate':
        if C: S += [('L', [(-0.5, -0.4), (-0.5, 0.4)], 0.18), ('L', [(0.5, -0.4), (0.5, 0.4)], 0.18)]
        else: S += [('L', [(-0.55, -0.45), (-0.55, 0.45)], w * 1.2), ('L', [(0.55, -0.45), (0.55, 0.45)], w * 1.2), ('L', [(-0.55, 0.1), (0.55, 0.1)], w)]
    elif kind == 'info':
        if C: S += [('P', [(-0.4, -0.4), (0.4, -0.4), (0.4, 0.4), (-0.4, 0.4)], False, 0.18)]
        else: S += [('P', [(-0.55, -0.02), (0.55, -0.02), (0.55, 0.62), (-0.55, 0.62)], B, w), ('L', [(0, -0.02), (0, -0.7)], w)]
    elif kind == 'flag':
        S += [('L', [(0, -0.7), (0, 0.7)], w), ('P', [(0, 0.65), (0.6, 0.65), (0.75, 0.48), (0.6, 0.31), (0, 0.31)], B, w * 0.9),
              ('P', [(0, 0.2), (-0.6, 0.2), (-0.75, 0.03), (-0.6, -0.14), (0, -0.14)], B, w * 0.9)]
    elif kind == 'fire':
        if variant == 'drop': S += [('P', _flame(), B, w)]
        else:
            fl = [(0.0, 0.75), (0.28, 0.32), (0.36, 0.02), (0.22, -0.22), (0.0, -0.3), (-0.22, -0.22), (-0.36, 0.02), (-0.24, 0.3), (-0.08, 0.2)]
            S += [('P', fl, B, w), ('L', [(-0.6, -0.72), (0.6, -0.42)], w * 1.1), ('L', [(-0.6, -0.42), (0.6, -0.72)], w * 1.1)]
    elif kind == 'picnic':
        S += [('L', [(-0.85, 0.35), (0.85, 0.35)], w * 1.4 if B else 0.22), ('L', [(-0.35, 0.35), (-0.65, -0.55)], w), ('L', [(0.35, 0.35), (0.65, -0.55)], w), ('L', [(-0.9, -0.12), (0.9, -0.12)], w)]
    elif kind == 'mast':
        S += [('L', [(0, -0.75), (0, 0.75)], w), ('P', [(-0.4, -0.75), (0, 0.25), (0.4, -0.75)], False, w * 0.8)]
    elif kind == 'memorial':
        lw = 0.3 if B else w * 1.2
        S += [('L', [(0, -0.75), (0, 0.75)], lw), ('L', [(-0.42, 0.3), (0.42, 0.3)], lw)]
    elif kind == 'toilet':
        S += [('T', 'WC', 0.95)]
    elif kind == 'ring':
        S += [('C', 0, 0, 0.45, False, 0.28)] if B else [('C', 0, 0, 0.5, False, w), ('C', 0, 0, 0.25, False, w * 0.8)]
    elif kind == 'tree':
        S += [('C', 0, 0, 0.55, B, w * 1.2, 'green')]
    elif kind == 'lighthouse':
        S += [('P', [(-0.32, -0.75), (-0.17, 0.35), (0.17, 0.35), (0.32, -0.75)], B, w), ('P', [(-0.2, 0.35), (0.2, 0.35), (0.2, 0.6), (-0.2, 0.6)], True, 0)]
        for a in (150, 90, 30): S += [('L', [(0.38 * math.cos(math.radians(a)), 0.5 + 0.38 * math.sin(math.radians(a))), (0.75 * math.cos(math.radians(a)), 0.5 + 0.75 * math.sin(math.radians(a)))], 0.14)]
    elif kind == 'observatory':
        S += [('P', _arc(0, -0.15, 0.68, 0, 180) + [(-0.68, -0.15)], B, w), ('L', [(-0.85, -0.15), (0.85, -0.15)], w), ('L', [(0.12, 0.05), (0.62, 0.7)], w * 1.2)]
    elif kind == 'food':
        if (variant or 'cup') == 'cup': S += [('P', [(-0.55, 0.5), (-0.42, -0.5), (0.42, -0.5), (0.55, 0.5)], B, w), ('L', _arc(0.6, 0.05, 0.25, -80, 80, 12), w)]
        else: S += [('L', [(-0.3, -0.75), (-0.3, 0.75)], w * 1.2), ('L', [(-0.5, 0.75), (-0.5, 0.25), (-0.1, 0.25), (-0.1, 0.75)], w), ('P', [(0.32, -0.75), (0.32, 0.75), (0.55, 0.45), (0.55, 0.0), (0.32, 0.0)], B, w)]
    elif kind == 'peak':
        S += [('P', [(-0.75, -0.5), (0, 0.65), (0.75, -0.5)], B, w)]
        if not B: S += [('C', 0, -0.08, 0.1, True, 0)]
    elif kind == 'ferry':
        S += [('L', [(0, -0.6), (0, 0.6)], w), ('L', [(-0.32, 0.35), (0.32, 0.35)], w), ('L', _arc(0, -0.1, 0.55, 200, 340, 16), w), ('C', 0, 0.7, 0.13, False, w * 0.8)]
    elif kind == 'pit':
        S += [('L', [(-0.6, 0.45), (0, -0.45), (0.6, 0.45)], 0.24 if B else 0.2, 'brown')]
    # ---------- new landmark kinds (B style) ----------
    elif kind == 'milestone':      # small stele
        S += [('P', [(-0.28, -0.6), (0.28, -0.6), (0.28, 0.35), (0, 0.6), (-0.28, 0.35)], True, 0)]
    elif kind == 'railx':          # level crossing: St. Andrew's cross
        S += [('L', [(-0.5, -0.5), (0.5, 0.5)], 0.2), ('L', [(-0.5, 0.5), (0.5, -0.5)], 0.2)]
    elif kind == 'station':        # stop: filled disc with negative H
        S += [('C', 0, 0, 0.6, True, 0), ('L', [(-0.25, -0.3), (-0.25, 0.3)], 0.16, 'neg'), ('L', [(0.25, -0.3), (0.25, 0.3)], 0.16, 'neg'), ('L', [(-0.25, 0), (0.25, 0)], 0.16, 'neg')]
    elif kind == 'hydrant':
        S += [('P', [(-0.3, -0.6), (0.3, -0.6), (0.3, 0.25), (-0.3, 0.25)], True, 0), ('P', _arc(0, 0.25, 0.3, 0, 180, 12) + [(-0.3, 0.25)], True, 0),
              ('L', [(-0.5, -0.05), (0.5, -0.05)], 0.2)]
    elif kind == 'playground':     # swing
        S += [('L', [(-0.75, -0.6), (-0.45, 0.55), (0.45, 0.55), (0.75, -0.6)], 0.2), ('L', [(0.0, 0.55), (0.0, -0.2)], 0.12), ('L', [(-0.18, -0.2), (0.18, -0.2)], 0.2)]
    elif kind == 'fitness':        # dumbbell
        S += [('L', [(-0.5, 0), (0.5, 0)], 0.18), ('P', [(-0.75, -0.35), (-0.5, -0.35), (-0.5, 0.35), (-0.75, 0.35)], True, 0), ('P', [(0.5, -0.35), (0.75, -0.35), (0.75, 0.35), (0.5, 0.35)], True, 0)]
    elif kind == 'recycling':      # container with lid
        S += [('P', [(-0.55, -0.55), (0.55, -0.55), (0.62, 0.25), (-0.62, 0.25)], True, 0), ('L', [(-0.68, 0.42), (0.68, 0.42)], 0.18)]
    elif kind == 'bike':           # bicycle stand: two wheels
        S += [('C', -0.42, -0.15, 0.3, False, 0.16), ('C', 0.42, -0.15, 0.3, False, 0.16), ('L', [(-0.42, -0.15), (-0.05, 0.35), (0.42, -0.15)], 0.14)]
    elif kind == 'substation':     # lightning bolt
        S += [('P', [(0.12, 0.75), (-0.4, -0.05), (-0.02, -0.05), (-0.18, -0.75), (0.4, 0.1), (0.02, 0.1)], True, 0)]
    elif kind == 'summit':         # OL knoll: brown dot
        S += [('C', 0, 0, 0.32, True, 0, 'brown')]
    elif kind == 'bush':           # distinct bush: green dot
        S += [('C', 0, 0, 0.36, True, 0, 'green')]
    # ---------- kinds for on-site (field) entries ----------
    elif kind == 'boulder':        # Findling: irregular filled stone
        S += [('P', [(-0.6, -0.4), (-0.45, 0.25), (-0.05, 0.5), (0.45, 0.35), (0.62, -0.1), (0.4, -0.45)], True, 0)]
    elif kind == 'post':           # Pfahl/Pfosten: short thick post with cap
        S += [('L', [(0, -0.6), (0, 0.45)], 0.32), ('C', 0, 0.55, 0.16, True, 0)]
    elif kind == 'flagpole':
        S += [('L', [(-0.25, -0.75), (-0.25, 0.75)], 0.18), ('P', [(-0.25, 0.75), (0.55, 0.55), (-0.25, 0.3)], True, 0)]
    elif kind == 'sign':           # generic small sign: plate on post
        S += [('P', [(-0.42, 0.05), (0.42, 0.05), (0.42, 0.6), (-0.42, 0.6)], True, 0), ('L', [(0, 0.05), (0, -0.7)], 0.2)]
    elif kind == 'rzsign':         # Ruhezone sign: plate on post, purple
        S += [('P', [(-0.5, 0.0), (0.5, 0.0), (0.5, 0.62), (-0.5, 0.62)], True, 0, 'purple'), ('L', [(0, 0.0), (0, -0.7)], 0.2, 'purple')]
    elif kind == 'rzpost':
        S += [('L', [(0, -0.6), (0, 0.5)], 0.32, 'purple'), ('C', 0, 0.58, 0.16, True, 0, 'purple')]
    elif kind == 'beachaccess':    # numbered beach access: short steps
        S += [('L', [(-0.6, -0.55), (-0.2, -0.55), (-0.2, -0.15), (0.2, -0.15), (0.2, 0.25), (0.6, 0.25)], 0.22)]
    elif kind == 'dot':
        S += [('C', 0, 0, 0.25, True, 0)]
    return S

def draw(ax, kind, x, y, m, color, fam='B', size=1.0, paper='#fffdf7', variant=None, z=9, brown='#b0662a', green='#3f9b4a', knock=True, gray=None, halo_z=None):
    sc = m * size
    P = lambda pts: [(x + px * sc, y + py * sc) for px, py in pts]
    lwpt = lambda wmm: max(0.1, wmm * size * PT)
    kpt = KNOCK_MM * 2 * PT * max(0.8, min(size, 1.3))
    prims = shapes(kind, fam, variant)
    def colour(role):
        if role == 'neg': return paper
        if role == 'brown': return color if gray else brown
        if role == 'green': return color if gray else green
        if role == 'purple': return color if gray else '#9b3fb5'
        return color
    if knock: halo_patch(ax, knock_geom(kind, x, y, m, size, fam, variant), paper, (z - 0.05) if halo_z is None else halo_z)
    for pas in (2,):
        for sh in prims:
            t = sh[0]
            role = sh[-1] if isinstance(sh[-1], str) and sh[-1] in ('neg', 'brown', 'green', 'purple') else None
            if role == 'neg' and pas == 1: continue
            col = paper if pas == 1 else colour(role)
            zz = (z - 0.05) if pas == 1 else (z + (0.1 if role == 'neg' else 0))
            if t == 'L':
                q = np.array(P(sh[1])); lw = lwpt(sh[2]) + (kpt if pas == 1 else 0)
                ax.plot(q[:, 0], q[:, 1], color=col, lw=lw, solid_capstyle='round', solid_joinstyle='round', zorder=zz)
            elif t == 'P':
                fill, wmm = sh[2], sh[3]; lw = (lwpt(wmm) if wmm else 0.0) + (kpt if pas == 1 else 0)
                ax.add_patch(MPoly(P(sh[1]), closed=True, fc=col if (fill or pas == 1) else 'none', ec=col, lw=lw, joinstyle='round', zorder=zz))
            elif t == 'C':
                cx, cy, r, fill, wmm = sh[1:6]; lw = (lwpt(wmm) if wmm else 0.0) + (kpt if pas == 1 else 0)
                ax.add_patch(Circle((x + cx * sc, y + cy * sc), r * sc, fc=col if (fill or pas == 1) else 'none', ec=col, lw=lw, zorder=zz))
            elif t == 'T':
                ax.add_patch(_PP(_text_path(sh[1], sh[2] * size, x, y, sc / size if size else m), fc=col, ec='none', zorder=zz))

def draw_dots(ax, x0, y, n, m, color, paper='#fffdf7', d_mm=0.42, gap_mm=0.16, z=11):
    """Group count as dots, left edge at x0, vertically centred on y. Layout: 2→2x1, 3→3x1, 4→2x2, 5→3+2, 6→3x2."""
    rows = [[n]] if n <= 3 else ([[2, 2]] if n == 4 else [[3, n - 3]])
    rows = rows[0]
    pitch = (d_mm + gap_mm) * m; r = d_mm / 2 * m
    nrow = len(rows); y_top = y + (nrow - 1) * pitch / 2; cs = []
    for ri, cnt in enumerate(rows):
        for ci in range(cnt): cs.append((x0 + r + ci * pitch, y_top - ri * pitch))
    halo_patch(ax, _UU([_PT(cx, cy).buffer(r + 0.1 * m, 12) for cx, cy in cs]), paper, z - 0.05)
    for cx, cy in cs: ax.add_patch(Circle((cx, cy), r, fc=color, ec='none', zorder=z))

def dots_size(n, d_mm=0.42, gap_mm=0.16):
    cols = n if n <= 3 else (2 if n == 4 else 3); rows = 1 if n <= 3 else 2
    return cols * d_mm + (cols - 1) * gap_mm, rows * d_mm + (rows - 1) * gap_mm

KINDS = [('bench', 'Bank'), ('rescue', 'SOS-Schild'), ('shelter', 'Schutzhütte'), ('gate', 'Tor / Durchlass'), ('info', 'Infotafel'), ('flag', 'Wegweiser'),
         ('fire', 'Feuerstelle'), ('picnic', 'Picknicktisch'), ('memorial', 'Gedenkstätte'), ('ring', 'Rettungsring'), ('toilet', 'WC'),
         ('food', 'Gastronomie'), ('lighthouse', 'Leuchtturm'), ('observatory', 'Sternwarte'), ('peak', 'Aussichtsdüne'), ('ferry', 'Anleger'),
         ('mast', 'Mast / Pegel'), ('tree', 'Einzelbaum'), ('pit', 'Grube / Trichter')]
NEW_KINDS = [('milestone', 'km-Stein Inselbahn'), ('railx', 'Bahnübergang'), ('station', 'Haltepunkt'), ('hydrant', 'Hydrant'), ('playground', 'Spielplatz'),
             ('fitness', 'Fitnessgerät'), ('recycling', 'Recycling'), ('bike', 'Fahrradständer'), ('substation', 'Umspannstation'), ('summit', 'Dünenkuppe'), ('bush', 'Markanter Busch')]
