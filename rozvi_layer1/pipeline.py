"""Layer 1 end-to-end pipeline: monthly precip -> SPI / SPEI / RDI / events.

Works on:
- directory of monthly GeoTIFFs (from GEE export or CHC)
- synthetic .npz stacks for offline testing

All outputs carry quality flags. Missing stays NaN. Never invents data.
"""
from __future__ import annotations
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple
import json
import numpy as np

from . import spi as spi_mod
from . import spei as spei_mod
from . import events as events_mod
from . import rdi as rdi_mod
from . import monthly as monthly_mod
from .io_raster import load_monthly_stack, load_npz_stack, Grid
from .timeaxis import check_monthly_contiguous


def run_layer1(
    precip: np.ndarray,
    years: np.ndarray,
    months: np.ndarray,
    grid: Optional[Grid] = None,
    baseline: Tuple[int, int] = (1991, 2020),
    spi_windows: Sequence[int] = (1, 3, 6, 12),
    spei_windows: Sequence[int] = (3, 6, 12),
    pet: Optional[np.ndarray] = None,
    event_threshold: float = -1.0,
    zero_prob: str = "wmo",
    model_version: str = "0.1.0-dev",
) -> Dict:
    """Compute Layer 1 indicators.

    precip, pet: (T, ny, nx) float arrays, NaN = missing.
    Returns dict of arrays + metadata. Large arrays kept under indicators[*]['data'].
    """
    precip = np.asarray(precip, dtype="float32")
    years = np.asarray(years, int)
    months = np.asarray(months, int)
    check_monthly_contiguous(years, months)

    orig_shape = precip.shape[1:]
    T = precip.shape[0]
    # Core functions accept (T, ...) and preserve trailing dims

    result = {
        "schema_version": "1.0.0",
        "model": {"name": "ROZVI Drought Engine Layer 1", "version": model_version},
        "baseline": {"start": int(baseline[0]), "end": int(baseline[1])},
        "time": {"years": years.tolist(), "months": months.tolist()},
        "spatial_shape": list(orig_shape),
        "indicators": {},
        "events": {},
        "quality": {},
    }

    # Precipitation anomaly
    try:
        anom = monthly_mod.anomalies(precip, years, months, baseline=baseline)
        result["indicators"]["precip_anomaly_mm"] = {
            "data": anom,
            "units": "mm",
            "description": "P - mean(P | calendar month, baseline)",
        }
    except Exception as e:
        result["quality"]["precip_anomaly"] = f"skipped: {e}"

    # SPI family
    for k in spi_windows:
        out = spi_mod.spi(
            precip, years, months, k=k, baseline=baseline, zero_prob=zero_prob
        )
        key = f"spi_{k}"
        result["indicators"][key] = {
            "data": out["spi"],
            "flags": out["flags"],
            "units": "standard_deviation",
            "window_months": k,
            "zero_prob": zero_prob,
            "config": out.get("config"),
        }
        # Events on area-mean series (1-D) for summary; per-cell events can be added later
        mean_series = np.nanmean(out["spi"].reshape(T, -1), axis=1)
        ev = events_mod.detect_events(
            mean_series, years, months,
            threshold=event_threshold, min_duration=1, gap_pool=1
        )
        result["events"][key] = {"area_mean_events": ev, "threshold": event_threshold}

    # SPEI (requires PET of same shape)
    if pet is not None:
        pet = np.asarray(pet, dtype="float32")
        if pet.shape != precip.shape:
            raise ValueError("pet shape must match precip")
        for k in spei_windows:
            out = spei_mod.spei(
                precip, pet, years, months, k=k, baseline=baseline
            )
            key = f"spei_{k}"
            result["indicators"][key] = {
                "data": out["spei"],
                "flags": out["flags"],
                "units": "standard_deviation",
                "window_months": k,
                "pet_source": "user_supplied",
            }
            mean_series = np.nanmean(out["spei"].reshape(T, -1), axis=1)
            ev = events_mod.detect_events(
                mean_series, years, months,
                threshold=event_threshold, min_duration=1, gap_pool=1
            )
            result["events"][key] = {"area_mean_events": ev, "threshold": event_threshold}

        # RDI (example k=3)
        try:
            rdi_out = rdi_mod.rdi(precip, pet, years, months, k=3, baseline=baseline)
            result["indicators"]["rdi_3"] = {
                "data": {kk: vv for kk, vv in rdi_out.items()
                         if isinstance(vv, np.ndarray)},
                "units": "ratio / standardised",
            }
        except Exception as e:
            result["quality"]["rdi"] = f"skipped: {e}"
    else:
        result["quality"]["spei"] = "PET not supplied; SPEI and RDI skipped"

    if grid is not None:
        result["grid"] = {
            "x0": grid.x0, "y0": grid.y0, "res": grid.res,
            "nx": grid.nx, "ny": grid.ny,
        }
    return result


def run_from_directory(
    precip_dir: str | Path,
    out_dir: str | Path,
    window: Optional[Tuple[float, float, float, float]] = None,
    pet_dir: Optional[str | Path] = None,
    **kwargs,
) -> Dict:
    """Load monthly GeoTIFFs, run Layer 1, write summary JSON + .npz of indicators."""
    data = load_monthly_stack(precip_dir, window=window)
    pet = None
    if pet_dir is not None:
        pet_data = load_monthly_stack(pet_dir, window=window)
        pet = pet_data["precip"]

    result = run_layer1(
        data["precip"], data["years"], data["months"],
        grid=data["grid"], pet=pet, **kwargs
    )

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    arrays = {}
    for name, ind in result["indicators"].items():
        if "data" in ind:
            d = ind["data"]
            if isinstance(d, np.ndarray):
                arrays[name] = d
            elif isinstance(d, dict):
                for sub, arr in d.items():
                    if isinstance(arr, np.ndarray):
                        arrays[f"{name}_{sub}"] = arr
        if "flags" in ind and isinstance(ind["flags"], np.ndarray):
            arrays[f"{name}_flags"] = ind["flags"]
    np.savez_compressed(out / "layer1_indicators.npz", **arrays)

    summary = {k: v for k, v in result.items() if k != "indicators"}
    summary["indicator_names"] = list(result["indicators"].keys())
    summary["n_timesteps"] = int(data["precip"].shape[0])
    summary["spatial"] = list(data["precip"].shape[1:])
    with open(out / "layer1_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    return result


def run_from_npz(npz_path: str | Path, out_dir: str | Path, **kwargs) -> Dict:
    data = load_npz_stack(npz_path)
    result = run_layer1(
        data["precip"], data["years"], data["months"],
        grid=data["grid"], **kwargs
    )
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    arrays = {}
    for name, ind in result["indicators"].items():
        if "data" in ind and isinstance(ind["data"], np.ndarray):
            arrays[name] = ind["data"]
        if "flags" in ind and isinstance(ind["flags"], np.ndarray):
            arrays[f"{name}_flags"] = ind["flags"]
    np.savez_compressed(out / "layer1_indicators.npz", **arrays)
    summary = {k: v for k, v in result.items() if k != "indicators"}
    summary["indicator_names"] = list(result["indicators"].keys())
    with open(out / "layer1_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    return result
