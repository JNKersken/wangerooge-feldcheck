import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import sys, json; None
import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from shapely.geometry import shape, box
from geom import *
X0,Y1=423750,5961650
hs=np.load(BASE + '/data/hillshade.npy')
x0,y0,x1,y1=[float(v) for v in sys.argv[1:5]]; out=sys.argv[5]
c0,c1=int(x0-X0),int(x1-X0); r0,r1=int(Y1-y1),int(Y1-y0)
fig,ax=plt.subplots(figsize=((x1-x0)/100*1.1,(y1-y0)/100*1.1))
ax.imshow(hs[r0:r1,c0:c1],cmap='gray',extent=(x0,x1,y0,y1),vmin=0.2,vmax=1)
clip=box(x0,y0,x1,y1)
D=json.load(open(BASE + '/data/depressions.geojson'))
for f in D['features']:
    g=shape(f['geometry'])
    if not g.intersects(clip): continue
    p=f['properties']
    ax.plot(*g.exterior.xy,color='red' if p['kandidat'] else 'yellow',lw=1.0)
for wid,wy in W.items():
    t=wy['tags']
    if t.get('natural')=='water':
        g=way_geom(wid)
        if g is not None and g.intersects(clip) and g.geom_type=='Polygon': ax.plot(*g.exterior.xy,color='cyan',lw=0.8,ls='--')
    if t.get('highway') in ('path','footway','track','steps'):
        g=way_geom(wid)
        if g is not None and g.intersects(clip) and g.geom_type=='LineString': ax.plot(*g.xy,color='blue',lw=0.5,alpha=0.6)
ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.tick_params(labelsize=6)
ax.set_xticks(np.arange(np.ceil(x0/100)*100,x1,100)); ax.set_yticks(np.arange(np.ceil(y0/100)*100,y1,100)); ax.grid(lw=0.3,alpha=0.5,color='lime')
plt.tight_layout(); plt.savefig(out,dpi=90)
