import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import sys; None
import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import box
from geom import *; from dop import crop
x0,y0,x1,y1=[float(v) for v in sys.argv[1:5]]; out=sys.argv[5]; res=float(sys.argv[6]) if len(sys.argv)>6 else 0.2
opts=sys.argv[7] if len(sys.argv)>7 else 'osm'
img=crop(x0,y0,x1,y1,res)
fig,ax=plt.subplots(figsize=(img.shape[1]/100,img.shape[0]/100))
ax.imshow(img,extent=(x0,x1,y0,y1))
clip=box(x0,y0,x1,y1)
if 'osm' in opts:
    for wid,wy in W.items():
        t=wy['tags']; 
        if not ('highway' in t or 'building' in t): continue
        g=way_geom(wid)
        if g is None or not g.intersects(clip): continue
        if g.geom_type=='Polygon': ax.plot(*g.exterior.xy,color='yellow',lw=0.6)
        else: ax.plot(*g.xy,color='red',lw=0.6,alpha=0.7)
    for nid,n in N.items():
        t=n['tags']
        if t.get('amenity')=='bench':
            x,y=xy(nid)
            if clip.contains(Point(x,y)): ax.plot(x,y,'s',mfc='none',mec='cyan',ms=8,mew=1)
ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.axis('off')
plt.subplots_adjust(0,0,1,1); plt.savefig(out,dpi=100)
