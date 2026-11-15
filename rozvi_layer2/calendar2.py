"""Crop calendar lookup (maize, tobacco) from the normalised workbook extract.

Zone handling is explicit: the OCHA map has 'V' while the calendar has 'Va' (maize only); applying
the Va calendar to all of V carries ZONE_V_SPLIT_UNKNOWN. Zone I and any zone absent from the
calendar return no rows (CROP_CALENDAR_UNAVAILABLE) - no calendar is borrowed from another zone.
Tobacco field-stage sowing: the file rows start 1 Jun but the file's own comment says transplanting
starts 1 Sep. variant='comment' uses 1 Sep (default, flagged PHENOLOGY_ASSUMED); variant='file'
uses the rows as written. Seedbed rows are returned separately and are not water-balance modelled.
"""
import csv, os
from datetime import date
from .flags2 import L2Flag

DATA = os.path.join(os.path.dirname(__file__), "data", "crop_calendar_maize_tobacco_zimbabwe.csv")

def load_calendar(path=DATA):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))

def normalise_zone(z):
    z = str(z).strip().upper().replace("ZONE", "").replace("REGION", "").strip()
    return {"2A": "IIA", "2B": "IIB", "3": "III", "4": "IV", "1": "I", "5": "V", "5A": "VA", "5B": "VB"}.get(z, z)

def lookup(rows, crop, zone, stage=None, tobacco_variant="comment"):
    z = normalise_zone(zone); flags = []
    zk = z
    if crop == "maize" and z == "V":   # legacy unsplit label only; the real AEZ shapefile distinguishes Va and Vb
        zk = "VA"; flags.append(L2Flag.ZONE_V_SPLIT_UNKNOWN)
    sel = [r for r in rows if r["crop"] == crop and normalise_zone(r["zone"]) == zk]
    if crop == "tobacco":
        want = stage or "field"
        sel = [r for r in sel if r["stage_label"] == want]
        if want == "field" and tobacco_variant == "comment":
            sel = [r for r in sel if (int(r["sow_start_month"]), int(r["sow_start_day"])) == (9, 1)]
            flags.append(L2Flag.PHENOLOGY_ASSUMED)
    if not sel:
        return [], [L2Flag.CROP_CALENDAR_UNAVAILABLE]
    return sel, flags

def sowing_dates(row, season_year, step_days=10):
    s = date(season_year, int(row["sow_start_month"]), int(row["sow_start_day"]))
    e = date(season_year, int(row["sow_end_month"]), int(row["sow_end_day"]))
    out = []; d = s
    from datetime import timedelta
    while d <= e:
        out.append(d); d += timedelta(days=step_days)
    if out[-1] != e:
        out.append(e)
    return out

def growing_period_range(row):
    return int(row["growing_period_min_days"]), int(row["growing_period_max_days"])
