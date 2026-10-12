"""Mosaic DGM1 tiles, clip to map frame, write mosaic + multidirectional hillshade."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import glob, numpy as np, rasterio
from rasterio.merge import merge
from rasterio.transform import from_origin
X0, Y0, X1, Y1 = 423750, 5958850, 427150, 5961650
srcs = [rasterio.open(f) for f in sorted(glob.glob(BASE + '/data/dgm/*.tif'))]
mos, tr = merge(srcs, bounds=(X0, Y0, X1, Y1), res=1.0, nodata=np.nan)
z = mos[0].astype('float32')
z[z < -100] = np.nan
prof = dict(driver='GTiff', height=z.shape[0], width=z.shape[1], count=1, dtype='float32', crs='EPSG:25832', transform=tr, nodata=np.nan, compress='deflate')
with rasterio.open(BASE + '/data/dgm_frame.tif', 'w', **prof) as d: d.write(z, 1)
def hillshade(z, az, alt=40):
    zz = np.where(np.isnan(z), np.nanmin(z), z)
    gy, gx = np.gradient(zz)  # row axis = north->south
    slope = np.arctan(np.hypot(gx, gy)); aspect = np.arctan2(-gx, gy)
    a, al = np.radians(360 - az + 90), np.radians(alt)
    return np.clip(np.sin(al) * np.cos(slope) + np.cos(al) * np.sin(slope) * np.cos(a - aspect), 0, 1)
hs = (0.4 * hillshade(z, 315) + 0.2 * hillshade(z, 45) + 0.2 * hillshade(z, 270) + 0.2 * hillshade(z, 0))
np.save(BASE + '/data/hillshade.npy', hs.astype('float32'))
print(z.shape, np.nanmin(z), np.nanmax(z), 'NaN%', round(100 * np.isnan(z).mean(), 1))
