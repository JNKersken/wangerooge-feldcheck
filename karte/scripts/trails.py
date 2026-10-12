"""Trail candidates from DOP: bright thin ridges (sato) in vegetated dune areas, minus known OSM ways.
Usage: trails.py x0 y0 x1 y1 out.geojson [preview.png]"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import sys, json; None
import numpy as np
from skimage.filters import sato
from skimage.morphology import skeletonize, remove_small_objects, binary_dilation, disk
from skimage.measure import label, regionprops
from rasterio.features import rasterize
from rasterio.transform import from_origin
from shapely.geometry import LineString, MultiPoint, mapping, box
from geom import *; from dop import crop
x0,y0,x1,y1=[float(v) for v in sys.argv[1:5]]; RES=0.4
img=crop(x0,y0,x1,y1,RES).astype(float); H,Wd=img.shape[:2]
tr=from_origin(x0,y1,RES,RES)
L=img.mean(2)/255; exg=(2*img[...,1]-img[...,0]-img[...,2])/255
rid=sato(L,sigmas=[1.0,1.5,2.0],black_ridges=False)
veg=[];known=[]
for wid,w in W.items():
    t=w['tags']; g=way_geom(wid)
    if g is None: continue
    if t.get('natural') in ('heath','scrub','grassland') and g.geom_type=='Polygon': veg.append(g)
    if 'highway' in t or 'railway' in t or t.get('barrier') or t.get('waterway') or 'building' in t: known.append(g.buffer(3.0))
for rid_,r in R.items():
    if r['tags'].get('natural') in ('scrub','wood','heath'):
        g=rel_geom(rid_); 
        if g is not None: veg.append(g)
vm=rasterize([(g,1) for g in veg],out_shape=(H,Wd),transform=tr,fill=0).astype(bool)
km=rasterize([(g,1) for g in known],out_shape=(H,Wd),transform=tr,fill=0).astype(bool)
thr=np.percentile(rid[vm],97) if vm.any() else 1
m=(rid>thr)&vm&~km&(L>np.percentile(L[vm],55))
m=remove_small_objects(m,30)
sk=skeletonize(m)
lab=label(sk,connectivity=2); feats=[]
for r in regionprops(lab):
    n=r.area*RES
    if n<18: continue
    cc=r.coords; ext=max(np.ptp(cc[:,0]),np.ptp(cc[:,1]))*RES
    if ext<14: continue   # compact blobs, not lines
    pts=[tr*(c+0.5,rw+0.5) for rw,c in cc]
    # order points along principal axis for a simple polyline
    P=np.array(pts); u=np.linalg.svd(P-P.mean(0))[2][0]; o=np.argsort((P-P.mean(0))@u)
    ln=LineString(P[o]).simplify(1.5)
    feats.append(dict(type='Feature',geometry=mapping(ln),properties=dict(len=round(n,1))))
json.dump(dict(type='FeatureCollection',features=feats),open(sys.argv[5],'w'))
print('Kandidaten',len(feats),'Gesamtlänge %.0f m'%sum(f['properties']['len'] for f in feats))
if len(sys.argv)>6:
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(Wd/100,H/100)); ax.imshow(img.astype('uint8'),extent=(x0,x1,y0,y1))
    for g in known: 
        if g.intersects(box(x0,y0,x1,y1)): ax.plot(*g.exterior.xy,color='red',lw=0.4)
    for f in feats:
        c=np.array(f['geometry']['coordinates']); ax.plot(c[:,0],c[:,1],color='cyan',lw=1.5)
    ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.axis('off'); plt.subplots_adjust(0,0,1,1); plt.savefig(sys.argv[6],dpi=100)
