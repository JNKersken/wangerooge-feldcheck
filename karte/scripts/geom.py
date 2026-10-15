"""Geometry helpers: build shapely geometries in UTM32 (EPSG:25832) from parsed OSM."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import pickle
from pyproj import Transformer
from shapely.geometry import Point, LineString, Polygon, MultiPolygon
from shapely.ops import polygonize, unary_union, linemerge
T = Transformer.from_crs(4326, 25832, always_xy=True)
TI = Transformer.from_crs(25832, 4326, always_xy=True)
D = pickle.load(open(BASE + '/data/osm.pkl', 'rb'))
N, W, R = D['nodes'], D['ways'], D['rels']
def xy(nid):
    n = N[nid]; return T.transform(n['lon'], n['lat'])
def way_geom(wid):
    w = W[wid]; pts = [xy(n) for n in w['nds'] if n in N]
    if len(pts) < 2: return None
    closed = w['nds'][0] == w['nds'][-1] and len(pts) >= 4
    area_keys = ('building','landuse','natural','leisure','amenity','water','tourism','man_made','wetland','place','military')
    is_area = closed and (w['tags'].get('area') == 'yes' or any(k in w['tags'] for k in area_keys)) and not (w['tags'].get('natural') in ('coastline','tree_row','cliff') or 'highway' in w['tags'] and w['tags'].get('area')!='yes' or w['tags'].get('man_made') in ('dyke','groyne','breakwater','embankment') or 'barrier' in w['tags'])
    return Polygon(pts) if is_area else LineString(pts)
def rel_geom(rid):
    r = R[rid]; outer, inner = [], []
    for t, ref, role in r['members']:
        if t == 'way' and ref in W:
            g = LineString([xy(n) for n in W[ref]['nds'] if n in N]) if len([n for n in W[ref]['nds'] if n in N])>=2 else None
            if g is None: continue
            (inner if role == 'inner' else outer).append(g)
    po = list(polygonize(unary_union(outer))) if outer else []
    pi = list(polygonize(unary_union(inner))) if inner else []
    if not po: return None
    g = unary_union(po)
    if pi: g = g.difference(unary_union(pi))
    return g
def ruhezone():
    """Ruhezone I/32 as polygon, or None if the relation is missing from the OSM extract."""
    from base import RUHEZONE_REL
    return rel_geom(RUHEZONE_REL) if RUHEZONE_REL in R else None
def ll(x, y):
    lon, lat = TI.transform(x, y); return lat, lon
