"""Merge the rendered sheets into the two deliverable PDFs (colour + black/white)."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
from pypdf import PdfWriter
SHEETS = ('uebersicht', 'detail_west', 'detail_mitte', 'detail_ost', 'detail_sued')
for m, tag in (('color', 'Farbe'), ('bw', 'SW')):
    w = PdfWriter()
    for sh in SHEETS: w.append(f'{BASE}/out/maps/{sh}_{m}.pdf')
    w.write(f'{BASE}/out/Wangerooge_West_OL_v1_{tag}.pdf'); print('geschrieben', f'out/Wangerooge_West_OL_v1_{tag}.pdf')
