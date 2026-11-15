# ROZVI Drought Model Standard (RDMS) v1.0 — Zimbabwe

Applies to Layer 1 (climate hazard) and Layer 2 (maize and tobacco impact). Layer 3 is out of scope. Words MUST, MUST NOT, SHOULD follow RFC 2119. Machine-readable parts live in `rozvi_standards/` (indicator registry, output-envelope schema, config template) and are enforced by tests.

## 1. Principles (non-negotiable)
1. Real, traceable data only; no fabricated or synthetic production data. Test vectors are confined to tests and marked `is_test_vector`.
2. Missing is null, never zero. Zero rainfall is a valid value, not missing.
3. Every value carries quality flags, baseline, source, version and uncertainty. A value without them MUST NOT be released.
4. Indicators stay separate and interpretable. No composite or single drought-risk score.
5. Stress indicators are not damage. No yield, production or financial loss without independently validated response functions.
6. Sources are never blended (CHIRPS vs ERA5-Land; the three SPEI streams stay separate).
7. A failed gate or failed dependency stays visible; partial runs are labelled PARTIAL, never published as complete.

## 2. Model identity and versioning
- **model_version** = MAJOR.MINOR.PATCH. MAJOR: any change to a scientific method, baseline, distribution, PET method, threshold or crop parameter set. MINOR: new indicator, source or output. PATCH: bug fix with no change to published values beyond numerical noise (documented tolerance 1e-6).
- A MAJOR change MUST pass regression comparison against the previous release with a written review of every changed indicator.
- Each release records: git commit, model_version, config hash, data-manifest ids, environment lockfile hash, test report, gate status, model card.
- Baselines are fixed within a model version (new data do not change fitted distributions). Config `config_version` follows the same rule.
- `processing_run_id` is unique per run; releases reference the run ids they were built from. Re-running identical inputs and config MUST reproduce identical outputs.

## 3. Naming
- Indicator ids: lower_snake_case with scale suffix, e.g. `spi_3`, `spei_12`, `rdi_st_6`, `wrsi_season`. Only ids in the registry may appear in outputs.
- Stream ids: `CHIRPS_V3`, `ERA5_LAND`, `CHIRPS_V3+FAO56_ET0_ERA5L`, `ERA5L_P+FAO56_ET0_ERA5L`, `CHIRPS_V3+ERA5L_PEV`, `CHIRPS_V3_RNL+FAO56_ET0_ERA5L` (Layer 2 forcing). The primary SPEI stream is the FAO-56 one.
- Crops: `maize`, `tobacco` (source-file spellings "Corn", "Tobbaco" are mapped by an explicit alias table).
- Seasons are labelled by sowing year, e.g. `2019/20` = sown 2019.
- Files: `{indicator}_{stream}_{baseline}_{start}_{end}_v{model_version}.{ext}`.

## 4. Units and conventions
- Precipitation and evaporation in mm; ET0 in mm/day; radiation in MJ m⁻² d⁻¹ after conversion; temperature °C; pressure kPa; wind m s⁻¹ at 2 m (converted from 10 m, FAO-56 Eq. 47).
- Time: UTC calendar day; monthly = calendar month; leap years honoured; no shifting to local time without a recorded method.
- ERA5-Land accumulations: value at 00:00 of day D+1 is the total of day D; ECMWF sign convention for evaporation is recorded and handled explicitly.
- CRS EPSG:4326, native grids preserved (CHIRPS 0.05°, ERA5-Land 0.1°). Any working grid is a recorded decision. Resampling does not create information and MUST be declared.
- Nodata: declared in config and manifest (CHIRPS −9999, not declared in file); NaN in memory; never 0.
- Boundary: GADM 4.1 ADM0, centre-in-polygon for gridded masks, area-weighted for polygon queries; full rectangular windows are stored with a separate mask.

## 5. Data and provenance
- Immutable raw files with SHA-256; machine-readable data manifest and a separate processing manifest.
- Every input records provider, product, version, DOI, URL, retrieval time, licence, units, grid, time coverage, convention.
- Licence status is explicit; unresolved commercial use is a visible flag (currently: GADM, CHIRPS V3 terms, crop-area map, ERA5-Land redistribution).
- Preliminary or forecast values MUST be flagged (`FORCING_PRELIMINARY`) and MUST NOT enter baselines or event records.
- Bad input is quarantined with an error report, not repaired.
- No secrets in code or logs; credentials via environment variables.

## 6. Baselines
- Primary 1991–2020; sensitivity 1981–2010 and 1989–2018. Per cell and calendar endpoint month: sample count, completeness, zero frequency, fit, convergence, goodness of fit recorded.
- Minimum samples (default 25 of 30). Never use future data to fit past values. Never invent a climatology.
- Daily-derived monthly totals: completeness ≥ 90% (configurable); months between threshold and 100% are lower-bound sums and flagged MISSING_DATA.

## 7. Index standards
- **SPI** (k = 1, 3, 6, 12): accumulation requires all months valid; per endpoint-month mixed gamma (zero mass + gamma), Thom ML fit; KS goodness-of-fit (documented criterion, permissive because parameters are estimated); probability bounds 1e-6 (|SPI| ≤ 4.7534, PROB_CLIPPED flagged). Zero-accumulation convention (`wmo` H(0)=q vs `stagge` mid-probability) is a recorded release decision; the config value is null until chosen.
- **SPEI** (k = 3, 6, 12): D = P − PET; three-parameter log-logistic by PWM; requires β > 1; failed fit → null + FIT_FAIL; PET must be FAO-56 ET0 (primary) or an explicitly labelled stream.
- **RDI**: α_k = ΣP/ΣPET; normalised and standardised (lognormal); zero rain → standardised null.
- **Events**: index ≤ −1.0 (also reported at −1.5, −2.0); optional one-month gap pooling (versioned, sensitivity-tested; never bridges missing months); severity in index-months; frequency is not a return period; no return periods in this release.
- **Interpretation classes** for SPI/SPEI/RDI_st: McKee et al. (1993) classes in `rozvi_standards/classes.py`. Classes for WRSI and PDSI MUST be taken from a cited source before use; none are invented.
- **Layer 2**: daily root-zone bucket with FAO-56 Ks; crop parameters (Kc, stage fractions, depletion fraction, rooting depth) MUST carry a citation (table and edition) and the engine refuses to run without it; sowing-date × growing-period ensemble with spread; outputs labelled "rain-fed potential stress (upper bound if irrigated)" while irrigation is unknown; crop outputs suppressed where calendar, soil, parameters or forcing are missing. Vegetation anomaly outputs use the wording "consistent with possible water stress" and cover natural vegetation only.

## 8. Quality flags
- Layer 1 bit flags (uint16): DATA_OK, MISSING_DATA, INCOMPLETE_MONTH, LOW_SAMPLE, ZERO_INFLATED, FIT_OK, FIT_FAIL, OUT_OF_RANGE, BASELINE_INCOMPLETE, PET_UNAVAILABLE, UNIT_ERROR, CALENDAR_ERROR, SPATIAL_COVERAGE_INCOMPLETE, SOURCE_UNAVAILABLE, PROB_CLIPPED, GOF_FAIL.
- Layer 2 string flags: CROP_CALENDAR_UNAVAILABLE, ZONE_UNMAPPED, ZONE_V_SPLIT_UNKNOWN, IRRIGATION_UNKNOWN, SOIL_UNAVAILABLE, SOIL_PARAMETER_UNCERTAIN, CROP_PARAMETERS_UNCITED, PHENOLOGY_ASSUMED, FORCING_INCOMPLETE, FORCING_PRELIMINARY, DISAGGREGATION_SENSITIVE.
- Rules: a non-null value MUST carry DATA_OK; a null value MUST carry at least one explanatory flag; flags propagate to every derived product.

## 9. Output envelope
Every point, polygon or raster-derived record MUST validate against `output_envelope.schema.json` and `rozvi_standards.envelope.validate`: schema_version, model_version, processing_run_id, geometry, period, indicator (registry id), units (matching the registry), value (nullable), source_dataset, dataset_version, baseline, spatial_support, quality_flags, uncertainty, validation_status (V0–V5), provenance (manifest id), is_test_vector (false). Layer 2 adds crop, zone, season, stage, sowing_date_member, irrigation_status, suppression_reason. Example values MUST NOT be served as results.

## 10. Maturity and claims
Validation levels: V0 specified; V1 implemented; V2 unit and invariant tested; V3 verified against a reference implementation or published cases; V4 compared with independent observations; V5 operational with monitoring.
- Current honest status: Layer 1 SPI, SPEI, RDI, monthly processing, events and Layer 2 bucket/WRSI are **V2**; FAO-56 ET0 core is **V3 on one published example**; nothing is V4 (no station or yield data supplied); PDSI and vegetation anomaly are **V0 (blocked)**.
- Permitted wording: "implemented", "tested", "validated against X (metrics)". Forbidden: "accurate", "validated", "production-ready" without the corresponding level and evidence; any statement of yield or loss.
- ERA5-Drought comparison is a benchmark, not independent validation (ERA5-dependent); CHIRPS-derived tables (e.g. the WFP admin table) are cross-checks, not validation.

## 11. Testing and release gates
- Unit, invariant, integration and regression tests as listed in the Layer 1 prompt; real-data integration tests where files exist; reruns reproducible; failed ingestion cannot publish success.
- Gates: (1) data integrity, (2) scientific correctness, (3) geospatial correctness, (4) software reliability, (5) validation coverage and gaps, (6) documentation; Layer 2 adds (7) parameter provenance, (8) suppression logic, (9) no yield or loss claims. A failed gate stays visible in the release record.
- Release package: model card, dataset register, methodology, limitations, version history, commit, test report.

## 12. Change control
Any change to config values listed in §7, baselines, PET method, thresholds or crop parameters is a MAJOR change. Changes are proposed in writing with expected effect, reviewed, regression-tested and logged in the release history. Deprecations are announced one MINOR version ahead.

## 13. Open decisions the standard cannot resolve (tracked as null in the config template)
SPI zero-accumulation convention; initial soil-water fraction; crop parameter file and its citations; soil water-holding capacity source; boundary checksum/licence; irrigation status; Water Requirement Index definition; PDSI variant; interpretation classes for WRSI/PDSI.
