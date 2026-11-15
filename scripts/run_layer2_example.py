#!/usr/bin/env python3
"""Example: Layer 2 WRSI / crop-season stress on synthetic daily series (offline).

Uses the existing calendar, phenology and WRSI modules. No real soil/crop
parameters are invented as production defaults; the demo supplies minimal
illustrative values only for the test run and labels them clearly.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rozvi_layer2.phenology import kc_curve
from rozvi_layer2.wrsi import bucket_daily, wrsi, wrsi_by_stage
from rozvi_layer2.calendar2 import load_calendar, lookup
from rozvi_layer2.suppression import check_inputs


def main():
    # Illustrative parameters ONLY (NOT production defaults).
    # Replace with cited FAO-56 / local values before any operational use.
    gp_days = 140
    fractions = [0.15, 0.30, 0.35, 0.20]
    kc_ini, kc_mid, kc_end = 0.30, 1.15, 0.50
    taw = 100.0          # mm – replace with SoilGrids-derived TAW
    p_dep = 0.55
    s0_frac = 0.70

    rng = np.random.default_rng(7)
    n = gp_days
    rain = np.clip(rng.normal(4.5, 3.0, n), 0, None).astype(float)
    rain[90:] *= 0.15    # late-season dry spell
    et0 = np.full(n, 5.2)

    kc, stage_ids = kc_curve(gp_days, fractions, kc_ini, kc_mid, kc_end)

    bucket = bucket_daily(rain, et0, kc, taw=taw, p=p_dep, s0_fraction=s0_frac)
    season_wrsi = wrsi(bucket["eta"], bucket["etc"])
    stage_w = wrsi_by_stage(bucket["eta"], bucket["etc"], stage_ids)

    print("Season WRSI (%):", round(float(np.asarray(season_wrsi).item()), 1))
    print("Stage WRSI:", {k: round(float(np.asarray(v).item()), 1) for k, v in stage_w.items()})
    print("Assumptions:", bucket["assumptions"])

    # Calendar (real extract shipped with package)
    rows = load_calendar()
    cal = lookup(rows, crop="maize", zone="IIa")
    print("Maize Zone IIa calendar matches:", len(cal) if cal else 0)

    mode = check_inputs(
        calendar_rows=bool(cal),
        params_ok=False,          # demo values are uncited
        taw_available=True,
        irrigation_status="unknown",
        zone_mapped=True,
        forcing_complete=True,
    )
    print("Suppression mode:", mode["mode"], "| label:", mode.get("label"))
    print("Demo complete. Cite and replace Kc/TAW/p before operational use.")


if __name__ == "__main__":
    main()
