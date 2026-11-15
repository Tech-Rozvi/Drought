#!/usr/bin/env python3
"""Generate a small synthetic monthly precipitation stack for offline testing.

Mimics a 8 x 8 cell window over central Zimbabwe (0.05°), 1981-2020,
with realistic seasonal cycle and interannual variability.
No real observations are fabricated as production data; this is test-only.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rozvi_layer1.chirps_io import Grid
from rozvi_layer1.io_raster import save_geotiff_like


def main(out_dir: str = "data/test/synthetic_chirps_monthly"):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Rough central Zimbabwe window
    # 28.0E – 28.4E, 18.4S – 18.0S  (8 x 8 cells at 0.05°)
    x0, y0, res, nx, ny = 28.0, -18.0, 0.05, 8, 8
    grid = Grid(x0, y0, res, nx, ny)

    years = list(range(1981, 2021))
    months = list(range(1, 13))
    T = len(years) * 12

    # Seasonal cycle (mm/month) – wet Nov–Mar, dry May–Sep
    clim = np.array([
        120, 110, 80, 40, 15, 5, 3, 4, 10, 40, 90, 130  # Jan..Dec
    ], dtype="float32")

    rng = np.random.default_rng(42)
    stack = np.zeros((T, ny, nx), dtype="float32")
    y_list, m_list = [], []

    t = 0
    for y in years:
        # Simple ENSO-like year factor
        year_fac = 1.0 + 0.25 * np.sin(2 * np.pi * (y - 1981) / 7.0)
        for m in months:
            base = clim[m - 1] * year_fac
            noise = rng.normal(0, 0.3 * base + 2.0, size=(ny, nx))
            # Occasional dry spell
            if rng.random() < 0.08:
                noise -= 0.6 * base
            val = np.clip(base + noise, 0.0, None)
            stack[t] = val.astype("float32")
            y_list.append(y)
            m_list.append(m)
            t += 1

    # Single npz for fast loading (primary offline path)
    npz_path = out / "synthetic_stack.npz"
    np.savez_compressed(
        npz_path,
        precip=stack,
        years=np.asarray(y_list, int),
        months=np.asarray(m_list, int),
        grid=dict(x0=x0, y0=y0, res=res, nx=nx, ny=ny),
        nodata=-9999.0,
    )

    # Write a short subset of GeoTIFFs for directory-loader tests (12 months only)
    tif_dir = out / "sample_tifs"
    tif_dir.mkdir(exist_ok=True)
    for i in range(12):  # first year only
        fname = tif_dir / f"chirps-v3_0_{y_list[i]:04d}_{m_list[i]:02d}.tif"
        save_geotiff_like(fname, stack[i], grid)

    print(f"Wrote {npz_path} (shape {stack.shape}, mean {stack.mean():.1f} mm/month)")
    print(f"Wrote 12 sample GeoTIFFs under {tif_dir}")
    return str(npz_path)



if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/test/synthetic_chirps_monthly")
