"""Open sand areas from DOP (bright, low saturation), 1 m grid, excluding buildings/paved ways -> data/sand.geojson"""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import sys, json; None
import numpy as np, rasterio
from rasterio.features import rasterize, shapes
from rasterio.transform import from_origin
from scipy.ndimage import uniform_filter, binary_opening, binary_closing
from shapely.geometry import shape, mapping
from geom import *; from dop import crop
X0,Y0,X1,Y1=423750,5958850,427150,5961650
img=crop(X0,Y0,X1,Y1,1.0).astype(float)   # decimated to 1 m
H,Wd=img.shape[:2]; tr=from_origin(X0,Y1,1.0,1.0)
mx=img.max(2); mn=img.min(2); L=img.mean(2); sat=(mx-mn)/(mx+1e-6)
Ls=uniform_filter(L,3); Ss=uniform_filter(sat,3)
sand=(Ls>165)&(Ss<0.22)
z=rasterio.open(BASE + '/data/dgm_frame.tif').read(1)
sand&=~np.isnan(z)[:H,:Wd]
ex=[]
for wid,w in W.items():
    t=w['tags']; g=way_geom(wid)
    if g is None: continue
    if 'building' in t and g.geom_type=='Polygon': ex.append(g.buffer(2))
    if 'highway' in t and t.get('surface') not in ('sand',) : ex.append(g.buffer(2.5))
    if t.get('man_made') in ('pier','groyne','breakwater'): ex.append(g.buffer(3))
exm=rasterize([(g,1) for g in ex],out_shape=(H,Wd),transform=tr,fill=0).astype(bool)
sand&=~exm
sand=binary_closing(binary_opening(sand,iterations=1),iterations=2)
feats=[]
for g,v in shapes(sand.astype('uint8'),mask=sand,transform=tr):
    p=shape(g).buffer(1).buffer(-1).simplify(1.5)
    if p.area>=150: feats.append(dict(type='Feature',geometry=mapping(p),properties=dict(a=round(p.area))))
json.dump(dict(type='FeatureCollection',features=feats),open(BASE + '/data/sand.geojson','w'))
print(len(feats),'Flächen', round(sum(f['properties']['a'] for f in feats)/1e4,1),'ha')
