import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import sys,json; None
import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from dop import crop
x0,y0,x1,y1=[float(v) for v in sys.argv[1:5]]; out=sys.argv[5]; res=float(sys.argv[6]); g=float(sys.argv[7])
img=crop(x0,y0,x1,y1,res)
fig,ax=plt.subplots(figsize=(img.shape[1]/100,img.shape[0]/100)); ax.imshow(img,extent=(x0,x1,y0,y1))
for x in np.arange(np.ceil(x0/g)*g,x1,g): ax.axvline(x,color='yellow',lw=0.4,alpha=0.6); ax.text(x+1,y1-6,str(int(x))[-3:],color='yellow',fontsize=6)
for y in np.arange(np.ceil(y0/g)*g,y1,g): ax.axhline(y,color='yellow',lw=0.4,alpha=0.6); ax.text(x0+1,y+1,str(int(y))[-3:],color='yellow',fontsize=6)
for f in json.load(open(BASE + '/data/craters.geojson'))['features']:
    p=f['properties']
    if x0<p['x']<x1 and y0<p['y']<y1: ax.add_patch(plt.Circle((p['x'],p['y']),max(2.5,float(p['d'])/2),fill=False,color='cyan',lw=0.8))
ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.axis('off'); plt.subplots_adjust(0,0,1,1); plt.savefig(out,dpi=100)
