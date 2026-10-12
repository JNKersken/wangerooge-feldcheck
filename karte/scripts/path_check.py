"""Per OSM way: is it visible in DOP? Compare brightness/texture on the line vs parallel offsets (+-3.5 m).
Paved/major ways count as certain. Output data/path_status.json {wayid: {...}}"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import sys, json; None
import numpy as np
from shapely.geometry import box
from geom import *; from dop import TILES
import rasterio
from shapely.geometry import LineString
srcs={k:rasterio.open(f) for k,f in TILES.items()}
def sample(pts):
    out=np.full((len(pts),3),np.nan)
    for i,(x,y) in enumerate(pts):
        s=srcs.get((int(x//1000),int(y//1000)))
        if s is None: continue
        r,c=s.index(x,y)
        if 0<=r<5000 and 0<=c<5000:
            out[i]=s.read(window=((max(0,r-2),r+3),(max(0,c-2),c+3))).reshape(3,-1).mean(1)
    return out
F=box(423750,5958850,427150,5961650)
PAVED={'asphalt','paving_stones','concrete','concrete:plates','concrete:lanes','sett','paved','wood','metal','unhewn_cobblestone','pebblestone','shell_crumbs','shell','compacted'}
res={}
for wid,w in W.items():
    t=w['tags']; h=t.get('highway')
    if not h: continue
    g=way_geom(wid)
    if g is None or g.geom_type!='LineString' or not g.intersects(F): continue
    gi=g.intersection(F)
    if gi.geom_type!='LineString' or gi.length<3: 
        res[wid]=dict(status='sicher',why='kurz/fest'); continue
    if h in ('unclassified','residential','service','track','pedestrian','steps') or t.get('surface') in PAVED:
        res[wid]=dict(status='sicher',why='befestigt/Hauptweg'); continue
    d=np.arange(0,gi.length,1.0); on=[]; offL=[]; offR=[]
    for s in d:
        p=gi.interpolate(s); q=gi.interpolate(min(gi.length,s+0.5)); p0=gi.interpolate(max(0,s-0.5))
        dx,dy=q.x-p0.x,q.y-p0.y; n=np.hypot(dx,dy) or 1; nx,ny=-dy/n,dx/n
        on.append((p.x,p.y)); offL.append((p.x+3.5*nx,p.y+3.5*ny)); offR.append((p.x-3.5*nx,p.y-3.5*ny))
    A,B,C=sample(on),sample(offL),sample(offR)
    LA,LB,LC=A.mean(1),B.mean(1),C.mean(1)
    vis=((LA-LB>8)&(LA-LC>8))|((np.abs(LA-LB)>15)&(np.abs(LA-LC)>15))   # brighter than both sides, or strongly different
    frac=float(np.nanmean(vis)) if len(vis) else 0
    res[wid]=dict(status='sicher' if frac>=0.45 else 'prüfen',why=f'Luftbild sichtbar {frac:.0%}',frac=round(frac,2),len=round(gi.length))
json.dump({str(k):v for k,v in res.items()},open(BASE + '/data/path_status.json','w'))
import collections
c=collections.Counter(v['status'] for v in res.values()); L=collections.Counter()
for k,v in res.items(): L[v['status']]+=way_geom(int(k)).intersection(F).length
print(c, {k:round(v/1000,2) for k,v in L.items()})
