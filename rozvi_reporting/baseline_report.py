"""
Generate a professional Drought Baseline Assessment report (DOCX)
modelled on the ROZVI Heat Risk Baseline report structure.

Part I  – Summary for decision-makers (Layer 1 + Layer 2)
Part II – Technical report (methods, data, results, limitations)
Appendices – glossary, parameters, reproducibility, confidence rules

Works from Layer 1 pipeline output and optional Layer 2 summary dict.
Clearly labels synthetic / illustrative runs and suppressed Layer 2 outputs.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
except ImportError as e:
    raise ImportError(
        "python-docx is required for report generation. "
        "Install with: pip install python-docx"
    ) from e


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_cell_shading(cell, hex_color: str):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_color)
    shd.set(qn("w:val"), "clear")
    tcPr.append(shd)


def _add_heading(doc: Document, text: str, level: int = 1):
    return doc.add_heading(text, level=level)


def _add_para(doc: Document, text: str, bold: bool = False, italic: bool = False, size: int = 11,
              color: Optional[RGBColor] = None):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size)
    run.font.name = "Calibri"
    if color is not None:
        run.font.color.rgb = color
    return p


def _add_table(doc: Document, headers: List[str], rows: List[List[str]]):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for p in cell.paragraphs:
            for r in p.runs:
                r.bold = True
                r.font.size = Pt(10)
                r.font.color.rgb = RGBColor(255, 255, 255)
        _set_cell_shading(cell, "1F4E79")
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = table.rows[ri + 1].cells[ci]
            cell.text = str(val)
            for p in cell.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(10)
    return table


def _confidence_rules() -> List[List[str]]:
    """Standard confidence rating rules used in every report."""
    return [
        ["High", "Real data used as intended; method validated or standard; fit diagnostics pass; local corroboration available or not required for the claim."],
        ["Medium", "Real data with known limitations (e.g. satellite blended product, moderate model fit); claim is comparative or screening-level."],
        ["Low", "Fallback, default, relative weights only, missing local census/station data, or illustrative parameters."],
        ["Not assessed", "Indicator deliberately out of scope or suppressed until evidence supports it."],
        ["Illustrative only", "Synthetic or demo inputs; numbers must not be used for decisions."],
    ]


# ---------------------------------------------------------------------------
# Main report builder
# ---------------------------------------------------------------------------

def build_drought_baseline_report(
    summary: Dict[str, Any],
    events: Optional[Dict[str, Any]] = None,
    layer2: Optional[Dict[str, Any]] = None,
    out_path: str | Path = "drought_baseline_report.docx",
    aoi_name: str = "Zimbabwe (national / analysis window)",
    aoi_note: str = "Analysis window as configured for this run",
    is_synthetic: bool = False,
    model_version: str = "0.1.0-dev",
    prepared_by: str = "Rozvi",
    extra_notes: Optional[List[str]] = None,
) -> Path:
    """
    Build a Drought Baseline Assessment DOCX (Layer 1 + optional Layer 2).

    Parameters
    ----------
    summary : dict
        layer1_summary.json content.
    events : dict, optional
        Event statistics (defaults to summary['events']).
    layer2 : dict, optional
        Layer 2 results, e.g.:
          {
            "crop": "maize",
            "zone": "IIa",
            "season_wrsi": 69.6,
            "stage_wrsi": {0: 100.0, 1: 100.0, 2: 72.5, 3: 13.1},
            "stress_days": ...,
            "suppression_mode": "generic_stress_only",
            "suppression_label": "rain-fed potential stress (upper bound if irrigated)",
            "calendar_rows": 2,
            "params_cited": False,
            "taw_mm": 100.0,
            "assumptions": "...",
            "is_demo": True,
          }
    """
    out_path = Path(out_path)
    events = events or summary.get("events") or {}
    layer2 = layer2 or {}
    has_l2 = bool(layer2)

    baseline = summary.get("baseline") or {}
    baseline_str = f"{baseline.get('start', '?')}–{baseline.get('end', '?')}"
    model = summary.get("model") or {}
    model_name = model.get("name", "ROZVI Drought Engine")
    model_ver = model.get("version", model_version)
    n_t = summary.get("n_timesteps") or len(summary.get("time", {}).get("years", []))
    spatial = summary.get("spatial") or summary.get("spatial_shape") or ["?", "?"]
    indicator_names = summary.get("indicator_names") or list((summary.get("indicators") or {}).keys())

    event_counts = {}
    for key, ev in events.items():
        if isinstance(ev, dict) and "area_mean_events" in ev:
            event_counts[key] = len(ev["area_mean_events"])
        elif isinstance(ev, list):
            event_counts[key] = len(ev)

    generated = datetime.now(timezone.utc).strftime("%d %B %Y")
    red = RGBColor(0xC0, 0x00, 0x00)

    doc = Document()

    # ----- Title -----
    title = doc.add_paragraph()
    run = title.add_run("ROZVI")
    run.bold = True
    run.font.size = Pt(28)
    run.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)

    sub = doc.add_paragraph()
    run = sub.add_run("Drought Baseline Assessment")
    run.bold = True
    run.font.size = Pt(22)

    scope = "Meteorological drought (SPI family) and event statistics"
    if has_l2:
        scope += "; agricultural water-stress indicators (Layer 2)"
    _add_para(doc, scope, italic=True, size=12)

    meta_rows = [
        ["Area of interest", aoi_name],
        ["Analysis note", aoi_note],
        ["Primary baseline", baseline_str],
        ["Precipitation source", "CHIRPS V3 (RNL) – or synthetic test stack if labelled"],
        ["Layers included", "Layer 1" + (" + Layer 2" if has_l2 else " only")],
        ["Model", f"{model_name} {model_ver}"],
        ["Report generated", generated],
        ["Prepared by", prepared_by],
    ]
    if is_synthetic:
        meta_rows.insert(0, ["DATA STATUS", "ILLUSTRATIVE / SYNTHETIC – not operational results"])
    _add_table(doc, ["Field", "Value"], meta_rows)

    if is_synthetic:
        _add_para(
            doc,
            "WARNING: This report was generated from synthetic or demo inputs designed only to "
            "exercise the software. Numbers are not real drought statistics for Zimbabwe and "
            "must not be used for decisions.",
            bold=True, color=red,
        )

    doc.add_page_break()

    # ----- How to read -----
    _add_heading(doc, "How to read this report", 1)
    _add_para(
        doc,
        "This report serves two audiences. Part I is written for decision-makers and anyone who "
        "needs the findings without the modelling detail. Part II documents the method, data, "
        "uncertainty and results so that a specialist can judge and reproduce the work."
    )
    _add_table(
        doc,
        ["If you are…", "Start here", "Then, if you want detail"],
        [
            ["A decision-maker, manager or funder", "Part I: Summary for decision-makers", "Appendix A (plain-language Q&A) and confidence table"],
            ["A planner or practitioner", "Section 1, key indicators, events, Layer 2 stress", "Section 6 (limitations) and confidence ratings"],
            ["A climate / GIS / modelling specialist", "Part II: data, methods, baseline and Layer 2 rules", "Appendices C–E (parameters, confidence rules, reproducibility)"],
        ],
    )
    _add_para(doc, f"Report prepared by {prepared_by}. Generated with ROZVI Drought Engine {model_ver}.", italic=True, size=10)

    # =====================================================================
    # PART I
    # =====================================================================
    doc.add_page_break()
    _add_heading(doc, "PART I — Summary for decision-makers", 1)

    _add_heading(doc, "1. Summary for decision-makers", 1)
    _add_heading(doc, "1.1 What this assessment is", 2)
    _add_para(
        doc,
        "This assessment characterises meteorological drought using the Standardized Precipitation "
        f"Index (SPI) family relative to a fixed climatological baseline ({baseline_str}). "
        "SPI describes how unusual monthly (or multi-month) precipitation is compared with the "
        "local baseline distribution. It does not by itself measure soil moisture, crop damage, "
        "streamflow shortage or financial loss."
    )
    if has_l2:
        _add_para(
            doc,
            "Layer 2 adds a rain-fed crop water-stress pathway (WRSI – Water Requirement Satisfaction "
            "Index) for configured crops and agro-ecological zones. WRSI is a stress indicator, not a "
            "yield forecast. Outputs are suppressed or labelled when crop parameters, soil water-holding "
            "capacity or irrigation status are missing or uncited."
        )

    _add_heading(doc, "1.2 At a glance", 2)
    glance = [
        [baseline_str, "Primary baseline period"],
        [str(n_t), "Monthly timesteps in series"],
        [f"{spatial[0]} × {spatial[1]}" if len(spatial) >= 2 else str(spatial), "Spatial grid (rows × cols)"],
        [", ".join(indicator_names[:5]) or "SPI family", "Layer 1 indicators"],
        [str(event_counts.get("spi_3", "—")), "SPI-3 events (area-mean, ≤ −1.0)"],
        [str(event_counts.get("spi_6", "—")), "SPI-6 events (area-mean, ≤ −1.0)"],
    ]
    if has_l2:
        wrsi = layer2.get("season_wrsi")
        mode = layer2.get("suppression_mode", "—")
        glance.extend([
            [f"{wrsi:.1f}%" if isinstance(wrsi, (int, float)) else str(wrsi or "—"),
             f"Season WRSI ({layer2.get('crop', 'crop')}, {layer2.get('zone', 'zone')})"],
            [str(mode), "Layer 2 suppression mode"],
        ])
    _add_table(doc, ["Value", "Metric"], [[v, lab] for v, lab in glance])

    _add_heading(doc, "1.3 Key messages", 2)
    messages = [
        f"The primary climatological baseline is {baseline_str}. All SPI values are relative to distributions fitted only on those years.",
        "SPI is a precipitation anomaly index. Negative values mean drier than the baseline; they are not automatic proof of agricultural or hydrological drought.",
        "Events are defined as runs of the chosen index at or below −1.0 for at least one month (optional one-month gap pooling). Severity is reported in index-months, not return periods.",
        "CHIRPS V3 (RNL) is the primary precipitation stream. Other products are kept as separate comparison streams and are never blindly averaged.",
        "Hazard, impact, exposure, vulnerability and financial loss are deliberately separated. This baseline report does not claim crop yield loss or monetary damage.",
    ]
    if has_l2:
        messages.append(
            "Layer 2 WRSI is a rain-fed potential stress indicator. When irrigation status is unknown, "
            "results are labelled as an upper bound on stress if the crop is actually irrigated."
        )
        if not layer2.get("params_cited", False):
            messages.append(
                "Crop/soil parameters used for Layer 2 in this run are not fully cited; suppression logic "
                "limits the claim to generic stress-only or demo status."
            )
    if is_synthetic:
        messages.insert(0, "SYNTHETIC / DEMO DATA: all numerical results in this document are illustrative only.")
    for m in messages:
        doc.add_paragraph(m, style="List Bullet")

    _add_heading(doc, "1.4 What this means in practice", 2)
    _add_para(
        doc,
        "Use the SPI time series and event catalogue to identify periods and seasons that were "
        "unusual relative to the baseline. Compare multiple accumulation windows (1, 3, 6, 12 months): "
        "a dry SPI-3 may matter for a growing season while SPI-12 speaks to longer water-resource context."
    )
    if has_l2:
        _add_para(
            doc,
            "Where Layer 2 is enabled, use season and stage WRSI to prioritise attention on crop–zone "
            "combinations under water stress, but treat uncited-parameter runs as screening signals only. "
            "Confirm with local agricultural observations before operational decisions."
        )

    # ----- Confidence table (expanded) -----
    _add_heading(doc, "1.5 How confident can you be?", 2)
    _add_para(
        doc,
        "Confidence ratings follow fixed rules (see Appendix E). They separate what the data support "
        "from what is still assumed, fallback or out of scope."
    )

    conf_rows = []
    if is_synthetic:
        conf_rows.append([
            "All numerical SPI / event / WRSI values in this document",
            "Illustrative only",
            "Synthetic or demo precipitation and/or demo crop parameters; not real Zimbabwe statistics.",
        ])
    conf_rows.extend([
        [
            "Where / when precipitation was drier than the baseline (SPI pattern)",
            "Medium–High" if not is_synthetic else "Illustrative only",
            "SPI method is standard; confidence rises with complete baseline samples, fit diagnostics and local gauge validation (MSD).",
        ],
        [
            "Absolute event counts and severity at threshold −1.0",
            "Medium" if not is_synthetic else "Illustrative only",
            "Depends on threshold choice, gap pooling, data completeness flags and spatial aggregation (area-mean vs per-cell).",
        ],
        [
            "SPEI (climatic water deficit) if present",
            "Medium" if any("spei" in str(n).lower() for n in indicator_names) else "Not assessed",
            "Requires documented PET method (FAO-56 preferred). ERA5-Land PEV is a labelled secondary stream only.",
        ],
        [
            "Agricultural / crop water stress (Layer 2 WRSI)",
            (
                "Illustrative only" if (is_synthetic or layer2.get("is_demo")) else
                "Low" if (has_l2 and not layer2.get("params_cited", False)) else
                "Medium" if has_l2 else
                "Not assessed"
            ),
            (
                "Demo Kc/TAW used; replace with cited parameters." if (is_synthetic or layer2.get("is_demo")) else
                "Parameters present but not fully cited, or irrigation status unknown → upper-bound rain-fed stress only." if has_l2 else
                "Layer 2 not included in this run. Enable only with cited calendar, Kc, TAW and irrigation status."
            ),
        ],
        [
            "Crop yield or production loss",
            "Not assessed",
            "No validated crop-specific yield response function is applied. WRSI is a stress indicator, not a yield model.",
        ],
        [
            "Hydrological / water-supply shortage",
            "Not assessed",
            "Needs streamflow, reservoir or groundwater observations; meteorological indices alone are insufficient.",
        ],
        [
            "Population exposure and social vulnerability",
            "Not assessed in this drought baseline",
            "Exposure and vulnerability are Layer 3 / risk-overlay concepts; not computed here.",
        ],
        [
            "Future climate change in drought frequency/severity",
            "Not assessed (out of scope for this baseline release)",
            "CMIP6 projections are a later phase. Baseline remains fixed at historical reference.",
        ],
        [
            "CHIRPS regional accuracy for Zimbabwe",
            "Medium" if not is_synthetic else "Illustrative only",
            "Blended satellite–gauge product; not fully independent of stations. Validate against MSD before high-stakes use.",
        ],
    ])
    _add_table(doc, ["Finding", "Confidence", "Why"], conf_rows)

    _add_heading(doc, "1.6 Recommended actions", 2)
    actions = [
        ["Complete CHIRPS V3 monthly archive for the full baseline and monitoring period", "Data completeness drives fit quality and event detection", "Immediate"],
        ["Obtain MSD station series for independent validation of SPI", "Highest-priority local evidence gap", "1–3 months"],
        ["Supply cited crop Kc, stage lengths, TAW and irrigation status for Layer 2", "Moves WRSI from demo/low confidence to defensible stress screening", "When parameters ready"],
        ["Keep hazard, impact and risk as separate published fields", "Matches ROZVI design principles and the Model Standard", "Ongoing"],
        ["Do not publish yield or financial loss from this baseline alone", "No validated response function in this release", "Ongoing"],
    ]
    _add_table(doc, ["Action", "Evidence in this report", "Suggested timing"], actions)

    # =====================================================================
    # PART II
    # =====================================================================
    doc.add_page_break()
    _add_heading(doc, "PART II — Technical report", 1)

    _add_heading(doc, "2. Study area and data", 1)
    _add_heading(doc, "2.1 Area of interest", 2)
    _add_para(doc, f"AOI: {aoi_name}. {aoi_note}.")
    _add_para(doc, f"Spatial shape of analysis array: {spatial}. Native CHIRPS grid is 0.05°; results inherit the resolution of the input stack.")

    _add_heading(doc, "2.2 Data sources and provenance", 2)
    prov = [
        ["Precipitation (primary)", "CHIRPS V3 RNL (monthly aggregates from daily)", "OK" if not is_synthetic else "SYNTHETIC",
         "Primary stream for SPI; gauge-blended satellite product"],
        ["Baseline period", baseline_str, "Configured", "Fixed within model version; distributions fitted only on these years"],
        ["Boundary", "FAO GAUL (or configured national mask)", "Configured", "Never a raw bounding box"],
        ["PET / SPEI", "Not supplied in this run" if not any("spei" in str(n).lower() for n in indicator_names) else "User-supplied or ERA5-Land derived",
         "Optional", "SPEI requires documented PET method (FAO-56 preferred)"],
    ]
    if has_l2:
        prov.extend([
            ["Crop calendar", "Shipped maize/tobacco extract (zone-aware)", "OK" if layer2.get("calendar_rows") else "LIMITED",
             f"Rows matched this run: {layer2.get('calendar_rows', 0)}"],
            ["Crop / soil parameters (Kc, TAW, p)", "Caller-supplied" if layer2.get("params_cited") else "Demo / uncited",
             "CITED" if layer2.get("params_cited") else "UNCITED / DEMO",
             "Registry refuses uncited production defaults"],
            ["Irrigation status", str(layer2.get("irrigation_status", "unknown")), "LABELLED",
             "Unknown → rain-fed upper-bound stress label"],
        ])
    _add_table(doc, ["Layer", "Source", "Status", "Detail"], prov)

    _add_heading(doc, "3. Methodology", 1)
    _add_heading(doc, "3.1 Overview", 2)
    _add_para(
        doc,
        "Layer 1 produces transparent meteorological indicators: monthly precipitation totals and anomalies, "
        "SPI at multiple accumulation windows, optional SPEI when PET is available, RDI, and event statistics. "
        "No single opaque drought score is published."
    )
    if has_l2:
        _add_para(
            doc,
            "Layer 2 adds a daily root-zone water-balance (FAO-56 style Ks) and WRSI = 100 × ΣETa / ΣETc "
            "for configured crop seasons. Stage WRSI, stress days and longest stress spell are also reported. "
            "Suppression logic blocks crop-specific claims when calendar, parameters or soil data are missing."
        )

    _add_heading(doc, "3.2 Standardized Precipitation Index (SPI)", 2)
    _add_para(
        doc,
        "For accumulation window k, monthly precipitation is summed. A mixed gamma distribution "
        "(probability mass at zero + gamma on positive values) is fitted separately for each grid cell "
        "and calendar endpoint month using only the baseline years. The cumulative probability is "
        "transformed to a standard normal variate (SPI). Conventional categories: −1.0 to −1.49 moderately dry; "
        "−1.5 to −1.99 severely dry; ≤ −2.0 extremely dry. These are interpretive labels, not automatic impact thresholds."
    )

    _add_heading(doc, "3.3 Event definition", 2)
    _add_para(
        doc,
        "Default rule: index ≤ −1.0 for at least one month. Onset at first threshold crossing; "
        "termination after the index returns above the threshold. Optional pooling of runs separated "
        "by at most one month above the threshold. Severity S = Σ max(0, u − I_t) in index-months. "
        "Return periods are not estimated in this release."
    )

    _add_heading(doc, "3.4 Baseline policy", 2)
    _add_para(
        doc,
        f"Primary baseline {baseline_str}. Sensitivity alternatives (1981–2010, 1989–2018) may be run under a new model version. "
        "Baselines are fixed within a version so that time series remain comparable as new months arrive."
    )

    if has_l2:
        _add_heading(doc, "3.5 Layer 2 – crop water stress (WRSI)", 2)
        _add_para(
            doc,
            "Daily root-zone bucket: storage increases with effective rain (taken as rain in this screening form), "
            "drains above TAW, and is depleted by ETa = Ks × Kc × ET0. Ks is the FAO-56 water-stress coefficient. "
            "WRSI is the seasonal ratio of actual to potential crop ET, expressed as a percentage (0–100). "
            "Missing forcing never becomes zero: the state becomes unknown (NaN) until re-initialised."
        )
        _add_para(
            doc,
            f"This run: crop={layer2.get('crop', '?')}, zone={layer2.get('zone', '?')}, "
            f"suppression_mode={layer2.get('suppression_mode', '?')}, "
            f"label={layer2.get('suppression_label', '—')}."
        )
        if layer2.get("assumptions"):
            _add_para(doc, f"Recorded assumptions: {layer2['assumptions']}", italic=True, size=10)

    _add_heading(doc, "4. Results of this run", 1)
    _add_heading(doc, "4.1 Layer 1 – meteorological indicators", 2)
    _add_para(doc, f"Indicators computed: {', '.join(indicator_names) or 'none listed'}.")
    if event_counts:
        _add_para(doc, "Area-mean event counts (threshold −1.0):")
        for k, n in event_counts.items():
            doc.add_paragraph(f"{k}: {n} events", style="List Bullet")
    else:
        _add_para(doc, "No event summary was attached to this summary file.")

    if has_l2:
        _add_heading(doc, "4.2 Layer 2 – agricultural water stress", 2)
        l2_rows = [
            ["Crop", str(layer2.get("crop", "—"))],
            ["Agro-ecological zone", str(layer2.get("zone", "—"))],
            ["Season WRSI (%)", f"{layer2['season_wrsi']:.1f}" if isinstance(layer2.get("season_wrsi"), (int, float)) else str(layer2.get("season_wrsi", "—"))],
            ["Suppression mode", str(layer2.get("suppression_mode", "—"))],
            ["Claim label", str(layer2.get("suppression_label", "—"))],
            ["Calendar rows matched", str(layer2.get("calendar_rows", "—"))],
            ["Parameters cited", "Yes" if layer2.get("params_cited") else "No (demo / uncited)"],
            ["TAW (mm)", str(layer2.get("taw_mm", "—"))],
        ]
        stage = layer2.get("stage_wrsi") or {}
        if stage:
            for sid, val in sorted(stage.items(), key=lambda x: int(x[0]) if str(x[0]).isdigit() else 0):
                l2_rows.append([f"Stage {sid} WRSI (%)", f"{float(val):.1f}" if val is not None else "—"])
        _add_table(doc, ["Field", "Value"], l2_rows)
        _add_para(
            doc,
            "Interpretation: WRSI near 100 indicates the crop’s water requirement was largely met under the "
            "rain-fed assumptions; low stage WRSI (especially reproductive stages) flags stress. "
            "This is not a yield loss estimate.",
            italic=True, size=10,
        )

    if extra_notes:
        _add_heading(doc, "Additional notes for this run", 2)
        for n in extra_notes:
            doc.add_paragraph(n, style="List Bullet")

    _add_heading(doc, "5. Limitations and validity", 1)
    limits = [
        "SPI describes precipitation anomaly only; it is not soil moisture, vegetation stress, streamflow or yield loss.",
        "Fit quality depends on sample size and zero-precipitation frequency; cells with incomplete baseline are flagged and may return null.",
        "Missing daily or monthly data are never replaced by zero. Completeness rules are applied before aggregation.",
        "CHIRPS is a blended product; it is not fully independent of station observations. Regional bias should be evaluated against MSD gauges.",
        "This baseline release does not include CMIP6 future projections, return periods, or asset-level financial risk.",
    ]
    if has_l2:
        limits.extend([
            "WRSI uses a simplified bucket (effective rain = rain; no runoff model; irrigation = 0 unless supplied).",
            "Uncited or demo Kc/TAW values produce only generic or illustrative stress signals; crop-specific claims are suppressed.",
            "Unknown irrigation status forces the label “rain-fed potential stress (upper bound if irrigated)”.",
            "Yield and production loss are not estimated; no validated response function is applied.",
        ])
    else:
        limits.append("Layer 2 agricultural stress indicators were not included in this run.")
    if is_synthetic:
        limits.insert(0, "SYNTHETIC / DEMO INPUTS: precipitation and/or crop parameters were generated for software testing. Do not interpret numerical results as real Zimbabwe drought history.")
    for L in limits:
        doc.add_paragraph(L, style="List Bullet")

    _add_heading(doc, "6. Recommendations for further work", 1)
    for r in [
        "Ingest the full CHIRPS V3 monthly series for Zimbabwe (1991–present) via the GEE one-file-per-month export.",
        "Validate SPI against MSD station series and document regional performance.",
        "Add SPEI using FAO-56 ET0 from ERA5-Land meteorology (primary PET stream) and keep ERA5-Land PEV as a labelled secondary stream.",
        "Replace demo Layer 2 parameters with cited FAO-56 / local Kc, stage lengths, TAW and irrigation status; re-run with crop_specific mode when evidence allows.",
        "Publish a model card with every operational release (baseline, fit diagnostics, known failure modes, Layer 2 parameter citations).",
    ]:
        doc.add_paragraph(r, style="List Bullet")

    # ----- Appendices -----
    doc.add_page_break()
    _add_heading(doc, "Appendix A. Questions and answers (plain language)", 1)
    qa = [
        ("What is SPI?",
         "The Standardized Precipitation Index tells you how unusual the rainfall total was for a given place and season compared with a long baseline. Negative SPI means drier than usual; positive means wetter."),
        ("Is a negative SPI the same as a drought emergency?",
         "No. SPI is a meteorological signal. Agricultural damage, water shortages and economic loss depend on soils, crops, reservoirs, demand and management. Those are assessed in separate layers when the data support them."),
        ("What is WRSI?",
         "The Water Requirement Satisfaction Index compares the water the crop actually used to the water it would have used without stress. It is a stress indicator (0–100%), not a yield prediction."),
        ("Why a fixed baseline?",
         "So that a value of SPI −1.5 means the same thing in 2005 and in 2025. If the baseline moved every year, the numbers would not be comparable."),
        ("Can I use this for legal or operational decisions?",
         "This is a screening-level baseline. Confirm critical decisions with local observations, agency assessments and, where needed, site measurements. Synthetic or demo runs must not be used for decisions."),
    ]
    for q, a in qa:
        _add_para(doc, q, bold=True)
        _add_para(doc, a)

    _add_heading(doc, "Appendix B. Glossary", 1)
    _add_table(
        doc,
        ["Term", "Meaning"],
        [
            ["SPI", "Standardized Precipitation Index – precipitation anomaly on a standard-normal scale"],
            ["SPEI", "Standardized Precipitation Evapotranspiration Index – uses P − PET"],
            ["Baseline", "Fixed historical period used to fit the reference distribution"],
            ["Event", "Run of months with index at or below a threshold (default −1.0)"],
            ["Severity", "Sum of deficits below the threshold, in index-months"],
            ["CHIRPS", "Climate Hazards Center InfraRed Precipitation with Stations"],
            ["RNL", "ERA5-disaggregated daily CHIRPS product (primary daily stream)"],
            ["WRSI", "Water Requirement Satisfaction Index (Layer 2 crop stress indicator)"],
            ["TAW", "Total available water in the root zone (mm)"],
            ["Kc", "Crop coefficient (FAO-56) scaling reference ET0 to crop ET"],
            ["Suppression", "Rule that blocks or downgrades Layer 2 claims when evidence is missing"],
        ],
    )

    _add_heading(doc, "Appendix C. Model parameters (this run)", 1)
    param_rows = [
        ["Primary baseline", baseline_str],
        ["SPI windows", "1, 3, 6, 12 months (as configured)"],
        ["Event threshold", "−1.0"],
        ["Minimum event duration", "1 month"],
        ["Gap pooling", "1 month (configurable)"],
        ["SPI distribution", "Mixed gamma (zero mass + 2-parameter gamma)"],
        ["Zero probability convention", "WMO-style (configurable Stagge alternative)"],
        ["Model version", model_ver],
    ]
    if has_l2:
        param_rows.extend([
            ["Layer 2 crop", str(layer2.get("crop", "—"))],
            ["Layer 2 zone", str(layer2.get("zone", "—"))],
            ["TAW (mm)", str(layer2.get("taw_mm", "—"))],
            ["Parameters cited", "Yes" if layer2.get("params_cited") else "No"],
            ["Suppression mode", str(layer2.get("suppression_mode", "—"))],
        ])
    _add_table(doc, ["Parameter", "Value"], param_rows)

    _add_heading(doc, "Appendix D. Reproducibility", 1)
    _add_para(
        doc,
        f"Software: ROZVI Drought Engine {model_ver}. Pipeline entry points: "
        "rozvi_layer1.pipeline.run_from_directory / run_from_npz; Layer 2 modules under rozvi_layer2/. "
        "Report generator: rozvi_reporting.baseline_report.build_drought_baseline_report. "
        "Unit tests: PYTHONPATH=. python -m unittest discover -s tests -v."
    )
    _add_para(
        doc,
        "Every operational release should ship a model card recording baseline, fit method, "
        "data versions, quality flags, Layer 2 parameter citations and known limitations."
    )

    _add_heading(doc, "Appendix E. Confidence rating rules", 1)
    _add_para(doc, "The confidence column in Section 1.5 is assigned using these fixed rules:")
    _add_table(doc, ["Rating", "Meaning"], _confidence_rules())
    _add_para(
        doc,
        "Ratings apply to the specific finding, not to the whole report. A run can have High confidence "
        "on SPI patterns and Not assessed on yield loss at the same time.",
        italic=True, size=10,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))
    return out_path
