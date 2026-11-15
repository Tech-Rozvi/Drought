"""GEOGLAM-BACS v1.0 percent-crop rasters (0.05 deg, WGS84, uint16, 10000 = 100 %). The file declares
nodata = 99 although 99 is also a valid-looking percentage (0.99 %): the declared value is honoured
(NaN + counted), never treated as zero crop. Only maize exists in BACS (no tobacco mask)."""
import numpy as np
from PIL import Image
from rozvi_layer1.chirps_io import Grid

BACS_GRID = Grid(-180.0, 90.0, 0.05, 7200, 3600)

def read_bacs_fraction(path, west, south, east, north, nodata=99):
    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(path); t = im.tag_v2
    tie = t.get(33922); sc = t.get(33550)
    if im.size != (7200, 3600) or abs(sc[0] - 0.05) > 1e-6 or abs(tie[3] + 180.0) > 1e-9 or abs(tie[4] - 90.0) > 1e-6:
        raise ValueError("unexpected BACS grid (GRID ERROR)")
    rs, cs = BACS_GRID.window(west, south, east, north)
    arr = np.array(im)[rs, cs].astype("float64")
    frac = np.where(arr == nodata, np.nan, arr / 10000.0)
    if np.nanmax(frac) > 1.0 + 1e-9:
        raise ValueError("fraction above 100 % (UNIT_ERROR)")
    return frac, BACS_GRID.subgrid(rs, cs), int((arr == nodata).sum())

def cell_area_ha(lat_centres, res=0.05):
    lat = np.deg2rad(np.asarray(lat_centres, float))
    return (res * 111.32 * np.cos(lat)) * (res * 110.57) * 100.0   # approximate spherical cell area, ha
