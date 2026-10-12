"""Render hillshade crop (+ optional OSM paths/water) for visual inspection."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import sys; None
import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from geom import *
from shapely.geometry import box
X0,Y1=423750,5961650
hs=np.load(BASE + '/data/hillshade.npy')
x0,y0,x1,y1=[float(v) for v in sys.argv[1:5]]; out=sys.argv[5]; overlay=len(sys.argv)>6 and sys.argv[6]=='osm'
c0,c1=int(x0-X0),int(x1-X0); r0,r1=int(Y1-y1),int(Y1-y0)
w=(x1-x0)/100*1.0
fig,ax=plt.subplots(figsize=(w*0.8,(y1-y0)/100*0.8))
ax.imshow(hs[r0:r1,c0:c1],cmap='gray',extent=(x0,x1,y0,y1),vmin=0,vmax=1)
if overlay:
    clip=box(x0,y0,x1,y1)
    for wid,wy in W.items():
        t=wy['tags']
        if 'highway' in t or t.get('natural')=='water':
            g=way_geom(wid)
            if g is None or not g.intersects(clip): continue
            if g.geom_type=='Polygon': ax.plot(*g.exterior.xy,color='cyan',lw=0.8)
            else: ax.plot(*g.xy,color='red' if t['highway'] in('path','footway','steps') else 'orange',lw=0.7,alpha=0.8)
ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.tick_params(labelsize=6)
ax.set_xticks(np.arange(np.ceil(x0/100)*100,x1,100)); ax.set_yticks(np.arange(np.ceil(y0/100)*100,y1,100)); ax.grid(lw=0.2,alpha=0.4,color='y')
plt.setp(ax.get_xticklabels(),rotation=90)
plt.tight_layout(); plt.savefig(out,dpi=100)
