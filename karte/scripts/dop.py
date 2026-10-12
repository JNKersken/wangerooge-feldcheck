"""Read DOP20 RGB crops for arbitrary UTM32 bbox across tiles."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import glob, numpy as np, rasterio
from rasterio.windows import from_bounds
TILES = {}
for f in glob.glob(BASE + '/data/dop/*.tif'):
    p = f.split('/')[-1].split('_'); TILES[(int(p[2]), int(p[3]))] = f
def crop(x0, y0, x1, y1, res=0.2):
    """Return HxWx3 uint8 array for bbox at given resolution (multiples of 0.2 via decimation)."""
    step = max(1, int(round(res / 0.2)))
    W = int(round((x1 - x0) / 0.2)); H = int(round((y1 - y0) / 0.2))
    out = np.full((H, W, 3), 255, np.uint8)
    for e in range(int(x0 // 1000), int((x1 - 1e-6) // 1000) + 1):
        for n in range(int(y0 // 1000), int((y1 - 1e-6) // 1000) + 1):
            f = TILES.get((e, n))
            if not f: continue
            bx0, by0, bx1, by1 = max(x0, e * 1000), max(y0, n * 1000), min(x1, e * 1000 + 1000), min(y1, n * 1000 + 1000)
            if bx1 <= bx0 or by1 <= by0: continue
            with rasterio.open(f) as s:
                win = from_bounds(bx0, by0, bx1, by1, transform=s.transform)
                a = s.read(window=win.round_offsets().round_lengths()).transpose(1, 2, 0)
            c0 = int(round((bx0 - x0) / 0.2)); r0 = int(round((y1 - by1) / 0.2))
            out[r0:r0 + a.shape[0], c0:c0 + a.shape[1]] = a[:H - r0, :W - c0]
    return out[::step, ::step]
