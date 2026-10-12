"""Dark round blobs in open meadow (DOP, LoG) -> crater candidates in Westgroden etc. Appends to craters.geojson."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import sys, json, math; None
import numpy as np
from skimage.feature import blob_log
from rasterio.transform import from_origin
from rasterio.features import rasterize
from shapely.geometry import Point, mapping
from shapely.ops import unary_union
from geom import *; from dop import crop
mead=[]
for wid,w in W.items():
    t=w['tags']
    if t.get('landuse') in ('meadow','grass') or t.get('natural')=='grassland':
        g=way_geom(wid)
        if g is not None and g.geom_type=='Polygon' and g.area>2e4: mead.append(g)
M=unary_union(mead)
ditch=unary_union([way_geom(wid).buffer(5) for wid,w in W.items() if w['tags'].get('waterway') or 'highway' in w['tags'] or w['tags'].get('barrier')] )
C=json.load(open(BASE + '/data/craters.geojson'))
have=[(f['properties']['x'],f['properties']['y']) for f in C['features']]
new=0
TS=250; RES=0.5
bx0,by0,bx1,by1=M.bounds
for tx in np.arange(bx0,bx1,TS):
  for ty in np.arange(by0,by1,TS):
    x0,y0,x1,y1=tx,ty,tx+TS,ty+TS
    from shapely.geometry import box as _b
    poly=M.intersection(_b(x0,y0,x1,y1))
    if poly.is_empty or poly.area<2000: continue
    img=crop(x0,y0,x1,y1,RES).astype(float); H,Wd=img.shape[:2]; tr=from_origin(x0,y1,RES,RES)
    L=img.mean(2); inside=rasterize([(poly.buffer(-8),1)],out_shape=(H,Wd),transform=tr,fill=0).astype(bool)
    if inside.sum()<500: continue
    med=np.median(L[inside])
    dark=np.clip(med-L,0,None); dark[~inside]=0
    blobs=blob_log(dark/max(dark.max(),1), min_sigma=3, max_sigma=11, num_sigma=5, threshold=0.12)
    for r,c,sg in blobs:
        x,y=tr*(c+0.5,r+0.5); d=2*math.sqrt(2)*sg*RES
        p=Point(x,y)
        if ditch.contains(p) or d<4 or d>25: continue
        rr,cc=int(r),int(c); rad=max(2,int(sg*1.0))
        core=L[max(0,rr-rad):rr+rad+1,max(0,cc-rad):cc+rad+1].mean()
        if med-core<35: continue
        # shape test on dark region around the blob
        from skimage.measure import label as _lab, regionprops as _rp
        w0=max(0,rr-30); w1=max(0,cc-30); win=(dark[w0:rr+31,w1:cc+31]>25)
        lb=_lab(win); cl=lb[rr-w0,cc-w1]
        if cl==0: continue
        rp=[q for q in _rp(lb) if q.label==cl][0]
        Am=rp.area*RES*RES; circ=4*math.pi*rp.area/max(rp.perimeter,1)**2
        if not (8<=Am<=350) or circ<0.55 or rp.eccentricity>0.85: continue
        d=2*math.sqrt(Am/math.pi)
        if any(math.hypot(x-a,y-b)<max(5,d*0.6) for a,b in have): continue
        have.append((x,y)); new+=1
        C['features'].append(dict(type='Feature',geometry=mapping(p.buffer(d/2)),properties=dict(x=round(x,1),y=round(y,1),d=round(d,1),tiefe='',z_boden='',cv='',uni='',td='',klasse='Luftbild',quelle='Luftbild',osm='',dop='ja',dop_dL=round(med-core,1),dop_dG='')))
json.dump(C,open(BASE + '/data/craters.geojson','w'))
print('neue Wiesentrichter aus Luftbild:',new)
