import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import sys; None
from geom import *
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shapely.geometry import box
xmin,ymin,xmax,ymax = [float(v) for v in sys.argv[1:5]]; outp=sys.argv[5]; dpi=int(sys.argv[6]) if len(sys.argv)>6 else 150
clip=box(xmin,ymin,xmax,ymax)
fig,ax=plt.subplots(figsize=((xmax-xmin)/250,(ymax-ymin)/250))
def draw(g,**kw):
    if g is None or g.is_empty: return
    g=g.intersection(clip)
    if g.is_empty: return
    gs=getattr(g,'geoms',[g])
    for x in gs:
        if x.geom_type=='Polygon':
            ax.fill(*x.exterior.xy, **{k:v for k,v in kw.items() if k in('fc','alpha','ec','lw','zorder','hatch')})
        elif x.geom_type in('LineString','LinearRing'):
            ax.plot(*x.xy, **{k:v for k,v in kw.items() if k in('color','lw','ls','zorder','alpha')})
        elif x.geom_type=='Point':
            ax.plot(x.x,x.y,**{k:v for k,v in kw.items() if k in('marker','color','ms','zorder','mfc','mec')})
area_style={('natural','heath'):dict(fc='#d9b3d9'),('natural','scrub'):dict(fc='#9fd39f'),('natural','grassland'):dict(fc='#e6f2c2'),
 ('natural','sand'):dict(fc='#f5e6a8'),('natural','beach'):dict(fc='#fff3b0'),('natural','wetland'):dict(fc='#bfe3e0'),('landuse','forest'):dict(fc='#5fae5f'),
 ('landuse','meadow'):dict(fc='#e6f2c2'),('landuse','grass'):dict(fc='#e6f2c2'),('natural','water'):dict(fc='#5fa8e0'),('landuse','residential'):dict(fc='#eeeeee'),('leisure','park'):dict(fc='#d0ecd0')}
for wid,w in W.items():
    t=w['tags']
    for (k,v),st in area_style.items():
        if t.get(k)==v:
            g=way_geom(wid); 
            if g is not None and g.geom_type=='Polygon': draw(g,ec='none',lw=0,zorder=1,**st)
for rid,r in R.items():
    t=r['tags']
    for (k,v),st in area_style.items():
        if t.get(k)==v and t.get('type')=='multipolygon':
            g=rel_geom(rid); draw(g,ec='none',lw=0,zorder=1,**st)
for wid,w in W.items():
    t=w['tags']
    if 'building' in t:
        g=way_geom(wid)
        if g is not None and g.geom_type=='Polygon': draw(g,fc='#555',ec='none',zorder=3)
    if t.get('natural')=='coastline': draw(way_geom(wid),color='b',lw=1,zorder=2)
    if t.get('man_made')=='dyke': draw(way_geom(wid),color='#8b4513',lw=1.5,zorder=2)
    if t.get('man_made') in('groyne','breakwater','pier'): draw(way_geom(wid),color='#333',lw=1,zorder=2)
    if 'waterway' in t and t['waterway']!='fairway': draw(way_geom(wid),color='#3a7fd0',lw=0.6,zorder=2)
    if t.get('railway') in ('narrow_gauge',): draw(way_geom(wid),color='k',lw=1,ls='--',zorder=4)
    h=t.get('highway')
    if h:
        g=way_geom(wid)
        st={'path':dict(color='#d00',lw=0.7,ls=(0,(3,2))),'footway':dict(color='#d00',lw=0.9),'track':dict(color='#a0522d',lw=1.2,ls=(0,(6,2))),
            'steps':dict(color='m',lw=2.0),'pedestrian':dict(color='#666',lw=1.5),'residential':dict(color='#444',lw=1.5),'service':dict(color='#777',lw=1),'unclassified':dict(color='#222',lw=1.8)}.get(h,dict(color='orange',lw=1))
        if g is not None and g.geom_type=='LineString': draw(g,zorder=5,**st)
    if t.get('barrier') in ('fence','wall'): draw(way_geom(wid),color='k',lw=0.5,zorder=4)
for rid in (16774424,16774626,16774603):
    for tp,ref,role in R[rid]['members']:
        if tp=='way' and ref in W: draw(way_geom(ref),color='#c000c0',lw=2.5,alpha=0.6,zorder=6)
for nid,n in N.items():
    t=n['tags']; p=Point(xy(nid))
    if t.get('amenity')=='bench': draw(p,marker='s',color='#000',ms=2.5,zorder=7)
    elif t.get('natural')=='tree': draw(p,marker='o',color='darkgreen',ms=4,zorder=7)
    elif t.get('amenity') in('shelter',): draw(p,marker='^',color='#000',ms=5,zorder=7)
    elif t.get('amenity') in('restaurant','cafe','fast_food','bar','pub'): draw(p,marker='*',color='orange',ms=6,zorder=7)
    elif t.get('barrier')=='gate': draw(p,marker='x',color='k',ms=4,zorder=7)
    elif t.get('tourism')=='information': draw(p,marker='i' if False else 'P',color='blue',ms=4,zorder=7)
    elif t.get('highway')=='emergency_access_point': draw(p,marker='D',color='red',ms=3,zorder=7)
    elif t.get('natural')=='peak': draw(p,marker='^',color='brown',ms=7,zorder=7)
ax.set_xlim(xmin,xmax); ax.set_ylim(ymin,ymax); ax.set_aspect('equal')
ax.set_xticks(range(int(xmin)//500*500+500,int(xmax),500)); ax.set_yticks(range(int(ymin)//500*500+500,int(ymax),500)); ax.grid(lw=0.3,alpha=0.5)
ax.tick_params(labelsize=5)
plt.tight_layout(); plt.savefig(outp,dpi=dpi)
