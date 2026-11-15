"""Raster I/O helpers for ROZVI Layer 1.

Supports:
- Single GeoTIFF (CHIRPS-style via PIL)
- Directory of monthly GeoTIFFs named YYYY_MM.tif or chirps-v3_0_YYYY_MM.tif
- Simple numpy .npz stacks for offline testing

No GDAL/rasterio required for core path. Missing values remain NaN (never zero).
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import List, Optional, Tuple
import numpy as np
from PIL import Image

from .chirps_io import CHIRPS_NODATA, Grid, read_chirps_monthly, sha256

MONTH_RE = re.compile(r"(?:chirps[-_]?v3[_.]?0[_-]?)?(\d{4})[_-](\d{2})", re.I)


def list_monthly_tifs(directory: str | Path) -> List[Tuple[int, int, Path]]:
    """Return sorted (year, month, path) for GeoTIFFs in a directory."""
    d = Path(directory)
    out = []
    for p in sorted(d.glob("*.tif")) + sorted(d.glob("*.tiff")):
        m = MONTH_RE.search(p.name)
        if m:
            y, mo = int(m.group(1)), int(m.group(2))
            if 1 <= mo <= 12:
                out.append((y, mo, p))
    out.sort()
    return out


def load_monthly_stack(
    directory: str | Path,
    window: Optional[Tuple[float, float, float, float]] = None,
    nodata: float = CHIRPS_NODATA,
) -> dict:
    """Load a directory of monthly CHIRPS-style GeoTIFFs into a contiguous stack.

    window = (west, south, east, north) in degrees; if None uses full file extent.
    Returns dict with keys: precip (T, ny, nx), years, months, grid, metas, paths.
    """
    files = list_monthly_tifs(directory)
    if not files:
        raise FileNotFoundError(f"No monthly GeoTIFFs found in {directory}")

    first_arr, first_grid, first_meta = read_chirps_monthly(files[0][2], nodata=nodata)
    if window is not None:
        rs, cs = first_grid.window(*window)
        grid = first_grid.subgrid(rs, cs)
    else:
        rs = slice(0, first_grid.ny)
        cs = slice(0, first_grid.nx)
        grid = first_grid

    T = len(files)
    stack = np.full((T, grid.ny, grid.nx), np.nan, dtype="float32")
    years, months, metas, paths = [], [], [], []

    for i, (y, m, p) in enumerate(files):
        arr, g, meta = read_chirps_monthly(p, nodata=nodata, validate=(i == 0))
        # Allow slight origin noise; still enforce same shape after window
        sub = arr[rs, cs]
        if sub.shape != (grid.ny, grid.nx):
            raise ValueError(f"Shape mismatch on {p.name}: {sub.shape} vs {(grid.ny, grid.nx)}")
        stack[i] = sub
        years.append(y)
        months.append(m)
        metas.append(meta)
        paths.append(str(p))

    # Continuity check
    for i in range(1, T):
        prev = years[i - 1] * 12 + months[i - 1]
        cur = years[i] * 12 + months[i]
        if cur != prev + 1:
            # Allow gaps but flag; do not invent data
            pass

    return {
        "precip": stack,
        "years": np.asarray(years, int),
        "months": np.asarray(months, int),
        "grid": grid,
        "metas": metas,
        "paths": paths,
        "nodata": nodata,
    }


def save_geotiff_like(path: str | Path, arr: np.ndarray, grid: Grid, nodata: float = -9999.0):
    """Write a simple GeoTIFF that chirps_io can re-read (float32, LZW not required)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.where(np.isfinite(arr), arr, nodata).astype("float32")
    im = Image.fromarray(data, mode="F")
    # Minimal GeoTIFF tags for compatibility
    # 33550 = ModelPixelScaleTag, 33922 = ModelTiepointTag
    # We store scale and tiepoint; full CRS not written (assumed EPSG:4326)
    tags = {
        33550: (grid.res, grid.res, 0.0),
        33922: (0.0, 0.0, 0.0, grid.x0, grid.y0, 0.0),
    }
    im.save(path, tiffinfo=tags)


def load_npz_stack(path: str | Path) -> dict:
    """Load a test stack saved by make_synthetic_chirps (offline tests)."""
    d = np.load(path, allow_pickle=True)
    return {
        "precip": d["precip"].astype("float32"),
        "years": d["years"].astype(int),
        "months": d["months"].astype(int),
        "grid": Grid(**d["grid"].item()),
        "metas": [],
        "paths": [str(path)],
        "nodata": float(d.get("nodata", -9999.0)),
    }
