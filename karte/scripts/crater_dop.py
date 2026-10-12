"""DOP contrast check for crater candidates: inner disc vs surrounding ring (brightness/greenness)."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import sys, json, csv, math; None
import numpy as np
from dop import crop
C=json.load(open(BASE + '/data/craters.geojson'))
for f in C['features']:
    p=f['properties']; x,y,d=p['x'],p['y'],float(p['d']); r=max(2.5,d/2)
    R=r*2.0
    img=crop(x-R,y-R,x+R,y+R).astype(float)
    H,Wd=img.shape[:2]; yy,xx=np.mgrid[0:H,0:Wd]; cy,cx=(H-1)/2,(Wd-1)/2
    dist=np.hypot(yy-cy,xx-cx)*0.2
    inn=dist<=r*0.7; ring=(dist>r*1.15)&(dist<=R)
    L=img.mean(2); exg=2*img[...,1]-img[...,0]-img[...,2]
    dL=L[ring].mean()-L[inn].mean(); dG=exg[inn].mean()-exg[ring].mean()
    # texture difference also counts (crater bowl edge shadow)
    p['dop_dL']=round(float(dL),1); p['dop_dG']=round(float(dG),1)
    p['dop']= 'ja' if (dL>12 or dG>10) else ('evtl' if (dL>6 or dG>5) else 'nein')
for f in C['features']:
    p=f['properties']
    p['sure'] = bool(p['klasse']=='deutlich' or p.get('dop')=='ja')
    p['show'] = not (p['klasse']=='wahrscheinlich' and p.get('dop')=='nein')
json.dump(C,open(BASE + '/data/craters.geojson','w'))
import collections
print(collections.Counter((f['properties']['klasse'],f['properties']['dop']) for f in C['features']))
