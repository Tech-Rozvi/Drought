# ROZVI Drought Engine (Zimbabwe) – Complete Build

**Version:** 0.1.0-dev  
**Layers in scope:** Layer 1 (climate hazard) + Layer 2 (agricultural stress indicators)  
**Domain:** Zimbabwe (FAO GAUL 2025 ADM0 boundary)  
**Primary precipitation:** CHIRPS V3 Daily RNL (ERA5-disaggregated) via Google Earth Engine; monthly aggregates for Layer 1.

This package is a self-contained scientific implementation of the ROZVI drought methodology. It can be downloaded, tested offline with synthetic data, and then pointed at real CHIRPS exports from GEE.

---

## Design principles (non-negotiable)

- Missing data stays **NaN**, never zero. Zero rainfall is valid data.
- No synthetic observations presented as production data.
- SPI / SPEI / RDI / WRSI kept as separate physical indicators – no opaque composite score.
- GEE is used only for data acquisition; the scientific engine runs offline on exported GeoTIFFs or arrays.
- Crop/soil parameters must be cited; the registry refuses uncited defaults.
- Baseline, distribution, thresholds and event rules are versioned and recorded in every output.

---

## Quick start (offline – no data download required)

```bash
# From the package root
pip install -r requirements.txt

# Generate synthetic 1981–2020 monthly stack (8×8 cells over central Zimbabwe)
PYTHONPATH=. python scripts/make_synthetic_zimbabwe.py

# Run Layer 1 (SPI-1/3/6/12 + events)
PYTHONPATH=. python scripts/run_layer1_example.py

# Run Layer 2 demo (WRSI bucket + calendar lookup)
PYTHONPATH=. python scripts/run_layer2_example.py

# Full unit-test suite
PYTHONPATH=. python -m unittest discover -s tests -v
```

Outputs appear under `data/test/`.

---

## Real data via Google Earth Engine

1. Open the Earth Engine Code Editor.
2. Run `gee_scripts/07_export_chirps_monthly_zimbabwe.js` (adjust `startYear` / `endYear`).
3. In the Tasks tab, run the export tasks. Files land in Drive folder `ROZVI_CHIRPS_Monthly_ZWE` named `chirps-v3_0_YYYY_MM.tif`.
4. Download the folder to e.g. `data/chirps_monthly_zwe/`.
5. Run the pipeline:

```bash
PYTHONPATH=. python -c "
from rozvi_layer1.pipeline import run_from_directory
run_from_directory(
    'data/chirps_monthly_zwe',
    'data/layer1_real_output',
    baseline=(1991, 2020),
    spi_windows=(1, 3, 6, 12),
)
print('Done – see data/layer1_real_output/')
"
```

Additional GEE helpers (NDVI/EVI with QA, burned area, ERA5-Land, SoilGrids notes) are in `gee_scripts/`.

Boundary used everywhere: **FAO GAUL 2015 level 0 – Zimbabwe**.

---

## Package layout

```
rozvi_drought_engine/
├── README.md
├── requirements.txt
├── docs/
│   └── ROZVI_Drought_Model_Standard.md
├── gee_scripts/                  # Earth Engine acquisition scripts
├── rozvi_layer1/                 # Climate hazard (SPI, SPEI, RDI, events, FAO-56)
│   ├── spi.py, spei.py, rdi.py, events.py, fao56.py, monthly.py …
│   ├── chirps_io.py, io_raster.py, pipeline.py
│   └── …
├── rozvi_layer2/                 # Agricultural stress (WRSI, calendar, phenology)
│   ├── wrsi.py, season.py, calendar2.py, phenology.py, params.py …
│   └── data/                     # crop calendar + district area extracts
├── rozvi_standards/              # Indicator registry, envelope schema, config template
├── scripts/                      # Example runners + synthetic data generator
├── tests/                        # Unit + integration tests
└── data/test/                    # Created by example scripts
```

---

## What is implemented

| Component | Status |
|-----------|--------|
| SPI (mixed gamma, zero-mass, GOF flags) | Implemented + unit-tested |
| SPEI (log-logistic) | Implemented + unit-tested |
| RDI | Implemented + unit-tested |
| Event detection (run theory, gap pooling) | Implemented + unit-tested |
| FAO-56 ET0 | Implemented (reproduces Example 18) |
| Monthly aggregation / anomalies | Implemented |
| CHIRPS monthly GeoTIFF reader + stack loader | Implemented |
| Layer 1 pipeline (directory or .npz → indicators + events) | Implemented |
| WRSI daily root-zone bucket | Implemented + mass-balance tested |
| Crop calendar (maize/tobacco, AEZ-aware) | Implemented |
| Phenology / Kc stages | Implemented |
| Suppression logic (no guessing) | Implemented |
| Indicator registry + output envelope | Implemented |
| AEZ zone rasterisation + GEOGLAM maize mask | Implemented (needs real files for full test) |
| GEE export scripts (CHIRPS monthly, NDVI, burn, ERA5, SoilGrids notes) | Provided |
| PDSI / scPDSI | Specification only – not implemented |
| CMIP6 projections / return periods | Out of scope for this release |
| Production API / asset risk (Layer 3) | Out of scope |

---

## Important limitations (honest)

- Agronomic parameters (Kc, TAW, p) are **not** shipped as defaults. You must supply cited values.
- SoilGrids band choice must be the **mean** (not the Q0_95 quantile shown in the original screenshot).
- Tobacco is predominantly irrigated in recent TIMB data; rain-fed WRSI is an upper-bound stress indicator only.
- Real CHIRPS / ERA5-Land archives are large; start with a short GEE export window for testing.
- Local MSD station validation is still required for high-confidence operational use.

---

## Licence & provenance

- Code in this package: provided for ROZVI development; record commit / version in every output.
- CHIRPS, ERA5-Land, MODIS, SoilGrids, FAO GAUL: respect each provider’s terms. Commercial use of GADM / GLEAM / SoilGrids may require additional clearance.
- Never claim “validated” or “production-ready” until the acceptance checklist in the Model Standard has been executed against real data.

---

## Next steps after download

1. Run the offline examples and the unit tests.
2. Export a multi-year CHIRPS monthly stack for Zimbabwe via the GEE script.
3. Point `run_from_directory` at that folder.
4. Supply cited crop/soil parameters and enable Layer 2 seasonal runs.
5. Add local station comparison when MSD data become available.

## Drought baseline reports

After a Layer 1 run:

```bash
PYTHONPATH=. python scripts/generate_baseline_report.py \
    --summary data/test/layer1_output/layer1_summary.json \
    --out reports/Drought_Baseline_Assessment.docx
```

The report follows the same structure as the ROZVI Heat Risk Baseline Assessment
(Part I decision-maker summary, Part II technical methods, confidence table,
limitations, glossary, reproducibility appendix). Synthetic runs are clearly labelled.

