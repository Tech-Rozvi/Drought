#!/usr/bin/env python3
"""Example: run Layer 1 on synthetic Zimbabwe data (fully offline).

Usage (from package root):
  PYTHONPATH=. python scripts/make_synthetic_zimbabwe.py
  PYTHONPATH=. python scripts/run_layer1_example.py
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rozvi_layer1.pipeline import run_from_npz, run_from_directory


def main():
    root = Path(__file__).resolve().parents[1]
    synth_dir = root / "data" / "test" / "synthetic_chirps_monthly"
    npz = synth_dir / "synthetic_stack.npz"
    out = root / "data" / "test" / "layer1_output"

    if not npz.exists():
        print("Synthetic data not found – generating …")
        from scripts.make_synthetic_zimbabwe import main as gen
        gen(str(synth_dir))

    print("Running Layer 1 from .npz …")
    result = run_from_npz(
        npz, out,
        baseline=(1991, 2020),
        spi_windows=(1, 3, 6, 12),
        event_threshold=-1.0,
    )
    print("Indicators:", list(result["indicators"].keys()))
    print("Events (spi_3 area-mean):", len(result["events"].get("spi_3", {}).get("area_mean_events", [])))
    print("Wrote", out / "layer1_summary.json", "and layer1_indicators.npz")

    # Demonstrate directory loader on the 12-month sample
    sample = synth_dir / "sample_tifs"
    if sample.exists():
        print("\nRunning Layer 1 from sample GeoTIFF directory (12 months) …")
        out2 = root / "data" / "test" / "layer1_output_dir"
        try:
            result2 = run_from_directory(
                sample, out2,
                baseline=(1991, 2020),
                spi_windows=(1, 3),
            )
            print("Directory run indicators:", list(result2["indicators"].keys()))
        except Exception as e:
            print("Directory run note (short series expected):", e)
    print("Done. Inspect data/test/layer1_output*/ for results.")


if __name__ == "__main__":
    main()
