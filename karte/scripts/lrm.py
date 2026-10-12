"""Local relief model: z - lowpass(z). Pits negative, mounds positive."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import numpy as np, rasterio
from scipy.ndimage import gaussian_filter
z = rasterio.open(BASE + '/data/dgm_frame.tif').read(1)
v = ~np.isnan(z); zz = np.where(v, z, 0)
w = gaussian_filter(v.astype(float), 12); lp = gaussian_filter(zz, 12) / np.maximum(w, 1e-6)
lrm = np.where(v, z - lp, np.nan)
np.save(BASE + '/data/lrm.npy', lrm.astype('float32'))
