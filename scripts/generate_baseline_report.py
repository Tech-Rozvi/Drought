#!/usr/bin/env python3
"""Generate a Drought Baseline Assessment DOCX (Layer 1 + optional Layer 2)."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rozvi_reporting.baseline_report import build_drought_baseline_report


def _demo_layer2() -> dict:
    return {
        "crop": "maize",
        "zone": "IIa",
        "season_wrsi": 69.6,
        "stage_wrsi": {0: 100.0, 1: 100.0, 2: 72.5, 3: 13.1},
        "suppression_mode": "generic_stress_only",
        "suppression_label": "rain-fed potential stress (upper bound if irrigated)",
        "calendar_rows": 2,
        "params_cited": False,
        "taw_mm": 100.0,
        "irrigation_status": "unknown",
        "assumptions": (
            "effective rain = rain; no surface runoff; drainage above TAW; irrigation = 0; "
            "Ks from post-rain storage; rain-fed potential stress (upper bound if irrigated)"
        ),
        "is_demo": True,
    }


def main():
    p = argparse.ArgumentParser(description="ROZVI Drought Baseline Report generator")
    p.add_argument("--summary", default=None, help="Path to layer1_summary.json")
    p.add_argument("--layer2-json", default=None, help="Optional path to Layer 2 results JSON")
    p.add_argument("--no-demo-layer2", action="store_true", help="Disable demo Layer 2")
    p.add_argument("--out", default="data/test/Drought_Baseline_Assessment_Report.docx")
    p.add_argument("--aoi", default="Zimbabwe (analysis window)")
    p.add_argument("--synthetic", action="store_true", help="Force synthetic/illustrative label")
    args = p.parse_args()

    root = Path(__file__).resolve().parents[1]
    summary_path = Path(args.summary) if args.summary else root / "data/test/layer1_output/layer1_summary.json"

    if not summary_path.exists():
        print(f"Summary not found: {summary_path}")
        print("Run scripts/run_layer1_example.py first (or supply --summary).")
        sys.exit(1)

    with open(summary_path) as f:
        summary = json.load(f)

    layer2 = None
    if args.layer2_json:
        with open(args.layer2_json) as f:
            layer2 = json.load(f)
    elif not args.no_demo_layer2:
        layer2 = _demo_layer2()

    is_synth = (
        args.synthetic
        or "synthetic" in str(summary_path).lower()
        or "test" in str(summary_path).lower()
        or (layer2 or {}).get("is_demo", False)
    )

    out = Path(args.out)
    if not out.is_absolute():
        out = root / out

    path = build_drought_baseline_report(
        summary=summary,
        events=summary.get("events"),
        layer2=layer2,
        out_path=out,
        aoi_name=args.aoi,
        aoi_note="Grid and period as recorded in the Layer 1 summary for this run.",
        is_synthetic=is_synth,
        prepared_by="Rozvi",
    )
    print(f"Wrote {path}")
    print("Layers:", "Layer 1 + Layer 2" if layer2 else "Layer 1 only")
    print("Synthetic/demo label:", is_synth)


if __name__ == "__main__":
    main()
