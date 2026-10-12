"""Append manually identified (aerial image) craters in the Westgroden meadow."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import json
from shapely.geometry import Point, mapping
C = json.load(open(BASE + '/data/craters.geojson'))
C['features'] = [f for f in C['features'] if f['properties']['klasse'] != 'Luftbild']
manual = [(424620, 5960550, 7, 'ja'), (424627, 5960522, 7, 'ja'), (424666, 5960529, 8, 'ja'), (424775, 5960479, 8, 'ja'), (424765, 5960411, 22, 'evtl')]
have = [(f['properties']['x'], f['properties']['y']) for f in C['features']]
for x, y, d, v in manual:
    if any(((x - a) ** 2 + (y - b) ** 2) ** .5 < 5 for a, b in have): continue
    C['features'].append(dict(type='Feature', geometry=mapping(Point(x, y).buffer(d / 2)), properties=dict(x=x, y=y, d=d, tiefe='', z_boden='', cv='', uni='', td='', klasse='Luftbild', quelle='Luftbild (manuell)', osm='', dop=v, dop_dL='', dop_dG='', sure=(v == 'ja'), show=True)))
json.dump(C, open(BASE + '/data/craters.geojson', 'w')); print('Trichter gesamt', len(C['features']))
