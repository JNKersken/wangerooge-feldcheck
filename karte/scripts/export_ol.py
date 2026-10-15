"""Export for orienteering and GPS software -> out/ol/
- Wangerooge_West_Posten.xml   IOF XML 3.0 CourseData: every 'sicher' landmark as a possible control (Purple Pen, OCAD, Condes …),
                               start = Inselheim Rüstringen / Sternwarte
- Wangerooge_West_Landmarken.gpx  all landmarks as waypoints (GPS devices, phone apps)
- Wangerooge_West_Landmarken.kml  all landmarks in folders per category (Google Earth, QGIS)
- <blatt>.jpg + .jgw + .prj      map sheet (colour, map frame only) with world file, EPSG:25832 (QGIS, OCAD, OpenOrienteering Mapper)
- <blatt>.kmz                    the same sheet as KML ground overlay (MapRun, Google Earth)
Needs the rendered PNGs from run_all.sh (out/maps/<blatt>_color.png). Same input -> byte-identical files."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from base import BASE, FRAME, SHEET_ORDER, VERSION, VERSION_DATE
import json, os, io, zipfile
from xml.sax.saxutils import escape
from PIL import Image
from pyproj import Geod, Transformer, Proj
import feld_text as FT, render_map as RM

OUT = BASE + '/out/ol'; os.makedirs(OUT, exist_ok=True)
Image.MAX_IMAGE_PIXELS = None
TO_LL = Transformer.from_crs('EPSG:25832', 'EPSG:4326', always_xy=True)
STAMP = VERSION_DATE + 'T12:00:00'
ZIP_TIME = tuple(int(v) for v in VERSION_DATE.split('-')) + (12, 0, 0)
x = lambda s: escape(str(s or ''), {'"': '&quot;'})

pts = []
for f in json.load(open(BASE + '/data/points_v1.geojson', encoding='utf-8'))['features']:
    p = f['properties']; e, n = f['geometry']['coordinates']
    title, hint = FT.title_hint(p)
    lon, lat = TO_LL.transform(e, n)
    pts.append(dict(p=p, e=e, n=n, lat=round(lat, 7), lon=round(lon, 7), title=title or p['kategorie'], hint=hint))
pts.sort(key=lambda q: q['p']['id'])

# ---------- IOF XML 3.0 ----------
SCALE = 5000; mm = 1000.0 / SCALE   # map position in mm at 1:5.000, origin = lower left corner of the map frame, y up
W_mm, H_mm = (FRAME[2] - FRAME[0]) * mm, (FRAME[3] - FRAME[1]) * mm
def control(q, kind='Control', cid=None):
    return (f'    <Control type="{kind}">\n      <Id>{x(cid or q["p"]["id"])}</Id>\n      <Name>{x(q["title"])}</Name>\n'
            f'      <Position lng="{q["lon"]}" lat="{q["lat"]}"/>\n'
            f'      <MapPosition x="{(q["e"] - FRAME[0]) * mm:.2f}" y="{(q["n"] - FRAME[1]) * mm:.2f}" unit="mm"/>\n    </Control>\n')
start = next((q for q in pts if q['p']['kategorie'] == 'Bauwerk' and q['p']['typ'] == 'Sternwarte'), None)
xml = ['<?xml version="1.0" encoding="UTF-8"?>\n',
       f'<CourseData xmlns="http://www.orienteering.org/datastandard/3.0" iofVersion="3.0" createTime="{STAMP}" creator="wangerooge-feldcheck {VERSION}">\n',
       '  <Event>\n    <Name>Wangerooge West</Name>\n  </Event>\n  <RaceCourseData>\n',
       f'    <Map>\n      <Scale>{SCALE}</Scale>\n      <MapPositionTopLeft x="0" y="{H_mm:.2f}" unit="mm"/>\n'
       f'      <MapPositionBottomRight x="{W_mm:.2f}" y="0" unit="mm"/>\n    </Map>\n']
if start: xml.append(control(start, 'Start', 'S1'))
xml += [control(q) for q in pts if q['p']['status'] == 'sicher']
xml.append('  </RaceCourseData>\n</CourseData>\n')
open(OUT + '/Wangerooge_West_Posten.xml', 'w', encoding='utf-8').write(''.join(xml))

# ---------- GPX ----------
def desc(q):
    s = [q['hint'], 'sicher' if q['p']['status'] == 'sicher' else 'noch zu prüfen', q['p']['vor_ort']]
    return ' · '.join(t for t in s if t)
gpx = ['<?xml version="1.0" encoding="UTF-8"?>\n',
       '<gpx version="1.1" creator="wangerooge-feldcheck" xmlns="http://www.topografix.com/GPX/1/1">\n',
       f'  <metadata>\n    <name>Wangerooge West – Landmarken {VERSION}</name>\n    <time>{STAMP}Z</time>\n  </metadata>\n']
for q in pts:
    gpx.append(f'  <wpt lat="{q["lat"]}" lon="{q["lon"]}">\n    <name>{x(q["p"]["id"] + " " + q["title"])}</name>\n'
               f'    <desc>{x(desc(q))}</desc>\n    <type>{x(q["p"]["kategorie"])}</type>\n  </wpt>\n')
gpx.append('</gpx>\n')
open(OUT + '/Wangerooge_West_Landmarken.gpx', 'w', encoding='utf-8').write(''.join(gpx))

# ---------- KML ----------
kml = ['<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2">\n<Document>\n',
       f'  <name>Wangerooge West – Landmarken {VERSION}</name>\n',
       '  <Style id="sicher"><IconStyle><color>ff553f4a</color><scale>0.8</scale><Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon></IconStyle></Style>\n',
       '  <Style id="pruefen"><IconStyle><color>ffffffff</color><scale>0.8</scale><Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon></IconStyle></Style>\n']
for kat in sorted({q['p']['kategorie'] for q in pts}):
    kml.append(f'  <Folder>\n    <name>{x(kat)}</name>\n')
    for q in pts:
        if q['p']['kategorie'] != kat: continue
        kml.append(f'    <Placemark>\n      <name>{x(q["title"])}</name>\n      <description>{x(q["p"]["id"] + " · " + desc(q))}</description>\n'
                   f'      <styleUrl>#{"sicher" if q["p"]["status"] == "sicher" else "pruefen"}</styleUrl>\n'
                   f'      <Point><coordinates>{q["lon"]},{q["lat"]}</coordinates></Point>\n    </Placemark>\n')
    kml.append('  </Folder>\n')
kml.append('</Document>\n</kml>\n')
open(OUT + '/Wangerooge_West_Landmarken.kml', 'w', encoding='utf-8').write(''.join(kml))

# ---------- georeferenced sheets ----------
PRJ = Proj('EPSG:25832').crs.to_wkt('WKT1_ESRI')
geod = Geod(ellps='GRS80')
n_img = 0
for name in SHEET_ORDER:
    png = f'{BASE}/out/maps/{name}_color.png'
    if not os.path.exists(png): print('fehlt:', png); continue
    lay = RM.sheet_layout(name); x0, y0, x1, y1 = lay['bbox']
    im = Image.open(png).convert('RGB'); px_mm = im.size[0] / lay['pw']
    box_px = (round(lay['mx'] * px_mm), round((lay['ph'] - lay['my'] - lay['mh']) * px_mm),
              round((lay['mx'] + lay['mw']) * px_mm), round((lay['ph'] - lay['my']) * px_mm))
    im = im.crop(box_px); w, h = im.size
    buf = io.BytesIO(); im.save(buf, 'JPEG', quality=82, optimize=True); jpg = buf.getvalue()
    open(f'{OUT}/{name}.jpg', 'wb').write(jpg)
    sx, sy = (x1 - x0) / w, (y1 - y0) / h   # metres per pixel
    open(f'{OUT}/{name}.jgw', 'w').write(f'{sx:.6f}\n0.0\n0.0\n{-sy:.6f}\n{x0 + sx / 2:.3f}\n{y1 - sy / 2:.3f}\n')
    open(f'{OUT}/{name}.prj', 'w').write(PRJ)
    # KML ground overlay: unrotated box around the centre, then turned by the meridian convergence (grid north vs. true north)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; lon, lat = TO_LL.transform(cx, cy)
    f_ = Proj('EPSG:25832').get_factors(lon, lat); k = f_.meridional_scale   # UTM metres per ground metre
    north = geod.fwd(lon, lat, 0, (y1 - y0) / 2 / k)[1]; south = geod.fwd(lon, lat, 180, (y1 - y0) / 2 / k)[1]
    east = geod.fwd(lon, lat, 90, (x1 - x0) / 2 / k)[0]; west = geod.fwd(lon, lat, 270, (x1 - x0) / 2 / k)[0]
    rot = -f_.meridian_convergence   # KML: counter-clockwise; the grid is turned clockwise against true north west of 9° E
    doc = (f'<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2">\n<Document>\n'
           f'  <name>Wangerooge West – {x(lay["sub"])}</name>\n  <GroundOverlay>\n    <name>{x(lay["sub"])}</name>\n'
           f'    <Icon><href>{name}.jpg</href></Icon>\n    <LatLonBox>\n      <north>{north:.7f}</north>\n      <south>{south:.7f}</south>\n'
           f'      <east>{east:.7f}</east>\n      <west>{west:.7f}</west>\n      <rotation>{rot:.4f}</rotation>\n    </LatLonBox>\n'
           f'  </GroundOverlay>\n</Document>\n</kml>\n')
    with zipfile.ZipFile(f'{OUT}/{name}.kmz', 'w', zipfile.ZIP_DEFLATED) as z:
        for fn, data in (('doc.kml', doc.encode('utf-8')), (f'{name}.jpg', jpg)):
            zi = zipfile.ZipInfo(fn, ZIP_TIME); zi.compress_type = zipfile.ZIP_DEFLATED; z.writestr(zi, data)
    n_img += 1
print('OL-Export:', sum(1 for q in pts if q['p']['status'] == 'sicher'), 'Posten (IOF XML),', len(pts), 'Landmarken (GPX/KML),', n_img, 'Blätter georeferenziert')
