"""CHIRPS V3 monthly GeoTIFF reader (PIL; no GDAL needed). Nodata is NOT declared inside the files,
so it is configured explicitly here and recorded in the returned metadata."""
from dataclasses import dataclass
import hashlib
import numpy as np
from PIL import Image

CHIRPS_NODATA = -9999.0
EXPECTED = dict(shape=(1600, 1500), res=0.05, x0=-20.0, y0=40.0)

@dataclass(frozen=True)
class Grid:
    x0: float; y0: float; res: float; nx: int; ny: int
    def x_centres(self): return self.x0 + (np.arange(self.nx) + 0.5) * self.res
    def y_centres(self): return self.y0 - (np.arange(self.ny) + 0.5) * self.res
    def window(self, west, south, east, north):
        c0 = int(np.floor((west - self.x0) / self.res)); c1 = int(np.ceil((east - self.x0) / self.res))
        r0 = int(np.floor((self.y0 - north) / self.res)); r1 = int(np.ceil((self.y0 - south) / self.res))
        if c0 < 0 or r0 < 0 or c1 > self.nx or r1 > self.ny:
            raise ValueError("requested window outside grid (SPATIAL_COVERAGE_INCOMPLETE)")
        return slice(r0, r1), slice(c0, c1)
    def subgrid(self, rs, cs):
        return Grid(self.x0 + cs.start * self.res, self.y0 - rs.start * self.res, self.res,
                    cs.stop - cs.start, rs.stop - rs.start)

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def read_chirps_monthly(path, nodata=CHIRPS_NODATA, validate=True, strict_africa=False):
    """Read a monthly precipitation GeoTIFF.

    validate=True checks georeferencing tags exist.
    strict_africa=True additionally enforces the full CHIRPS Africa tile shape/origin
    (use only for original CHC Africa downloads). Windowed or synthetic tiles pass with
    strict_africa=False (default).
    """
    im = Image.open(path)
    tags = im.tag_v2
    scale = tags.get(33550); tie = tags.get(33922)
    arr = np.array(im, dtype="float32")
    if validate:
        if scale is None or tie is None:
            raise ValueError("GeoTIFF georeferencing tags missing")
        if strict_africa:
            if arr.shape != EXPECTED["shape"]:
                raise ValueError(f"unexpected shape {arr.shape} (UNIT/GRID ERROR)")
            if not (abs(scale[0] - EXPECTED["res"]) < 1e-9 and abs(scale[1] - EXPECTED["res"]) < 1e-9):
                raise ValueError(f"unexpected pixel scale {scale[:2]}")
            if not (abs(tie[3] - EXPECTED["x0"]) < 1e-9 and abs(tie[4] - EXPECTED["y0"]) < 1e-9):
                raise ValueError(f"unexpected origin {tie[3:5]}")
    nd = arr == np.float32(nodata)
    vals = np.where(nd, np.nan, arr).astype("float32")
    if np.isfinite(vals).any() and np.nanmin(vals) < 0:
        raise ValueError("negative precipitation after nodata removal (OUT_OF_RANGE)")
    res = float(scale[0]) if scale is not None else EXPECTED["res"]
    if abs(res - EXPECTED["res"]) < 1e-6:
        res = EXPECTED["res"]
    x0 = float(tie[3]) if tie is not None else EXPECTED["x0"]
    y0 = float(tie[4]) if tie is not None else EXPECTED["y0"]
    grid = Grid(x0, y0, res, arr.shape[1], arr.shape[0])
    meta = dict(path=str(path), sha256=sha256(path), nodata_value=nodata,
                nodata_declared_in_file=(42113 in tags), nodata_cells=int(nd.sum()),
                crs_assumed="EPSG:4326 (geographic keys not re-parsed)", units="mm/month (provider convention)")
    return vals, grid, meta
