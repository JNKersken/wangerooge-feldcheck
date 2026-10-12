"""Contact sheet of DOP crops (12x12 m) centred on each OSM bench in frame, labelled with landmark IDs."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import sys, csv; None
import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from dop import crop
rows=[r for r in csv.DictReader(open(BASE + '/out/landmarken_v0.csv')) if r['kategorie']==sys.argv[1]]
start=int(sys.argv[3]) if len(sys.argv)>3 else 0; rows=rows[start:start+30]
n=len(rows); cols=6; rws=(n+cols-1)//cols; H=6.0
fig,axs=plt.subplots(rws,cols,figsize=(cols*2.6,rws*2.75))
for ax in np.ravel(axs): ax.axis('off')
for ax,r in zip(np.ravel(axs),rows):
    x,y=float(r['utm_e']),float(r['utm_n'])
    img=crop(x-H,y-H,x+H,y+H)
    ax.imshow(img,extent=(-H,H,-H,H),interpolation='lanczos')
    ax.add_patch(plt.Circle((0,0),1.5,fill=False,color='cyan',lw=0.8))
    ax.set_title(f"{r['id']} {r['notiz'][:22]}",fontsize=7)
plt.tight_layout(); plt.savefig(sys.argv[2],dpi=80)
