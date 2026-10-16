"""Merge the rendered sheets into the two deliverable PDFs (colour + black/white)."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE, SHEET_ORDER, VERSION
from pypdf import PdfWriter
from pypdf.generic import ArrayObject, ByteStringObject
import hashlib
for m, tag in (('color', 'Farbe'), ('bw', 'SW')):
    w = PdfWriter()
    for sh in SHEET_ORDER: w.append(f'{BASE}/out/maps/{sh}_{m}.pdf')
    w.add_metadata({'/Title': f'Wangerooge West – OL-Karte {VERSION} ({tag})'})
    fid = ByteStringObject(hashlib.md5(b''.join(open(f'{BASE}/out/maps/{sh}_{m}.pdf', 'rb').read() for sh in SHEET_ORDER)).digest())
    w._ID = ArrayObject([fid, fid])   # file id from the content instead of a random one: same sheets -> same file
    w.write(f'{BASE}/out/Wangerooge_West_OL_v1_{tag}.pdf'); print('geschrieben', f'out/Wangerooge_West_OL_v1_{tag}.pdf')
