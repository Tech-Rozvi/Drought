"""Natural Region (agro-ecological zone) raster on a given grid window from the AEZ shapefile.
Rule: cell centre inside polygon. Codes: 0 = unmapped (no zone polygon; never filled from neighbours),
-1 = overlap between two zone polygons (flagged, not resolved silently), 1..7 = zones in ZONE_CODES."""
import numpy as np
from rozvi_layer1.shp import read_polygons, read_dbf, centre_mask

ZONE_CODES = {"Region I": 1, "Region IIa": 2, "Region IIb": 3, "Region III": 4, "Region IV": 5, "Region Va": 6, "Region Vb": 7}
CODE_NAMES = {v: k for k, v in ZONE_CODES.items()}

def zone_raster(shp_path, dbf_path, xs, ys):
    polys = read_polygons(shp_path); rows = read_dbf(dbf_path)
    unknown = [r["gez_name"] for r in rows if r["gez_name"] not in ZONE_CODES]
    if unknown:
        raise ValueError(f"unrecognised zone names {unknown}")
    count = np.zeros((len(ys), len(xs)), int); code = np.zeros((len(ys), len(xs)), int)
    for r, p in zip(rows, polys):
        m = centre_mask(p, xs, ys); count += m; code = np.where(m & (code == 0), ZONE_CODES[r["gez_name"]], code)
    return np.where(count > 1, -1, code), count

def zone_name(code):
    return CODE_NAMES.get(int(code))
