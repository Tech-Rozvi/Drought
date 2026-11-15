"""Monthly precipitation totals from daily data, completeness control and anomalies.

P_month = sum(valid daily observations). Missing is never zero. A month is accepted only if
valid_days / expected_days >= min_completeness (default 0.90). Between the threshold and 100%
the value is the plain sum of valid days (NOT scaled up) and is therefore a lower bound; it is
flagged MISSING_DATA and the valid fraction is returned.
"""
import calendar
import numpy as np
from .flags import QF

def monthly_totals(daily, dates, min_completeness=0.90):
    daily = np.asarray(daily, dtype="float64")
    dates = np.asarray(dates).astype("datetime64[D]")
    if daily.shape[0] != dates.shape[0]:
        raise ValueError("daily and dates length mismatch")
    if len(np.unique(dates)) != len(dates):
        raise ValueError("duplicate timestamps in daily series (quarantine the input)")
    if np.any(np.diff(dates.astype("int64")) < 0):
        raise ValueError("dates are not sorted ascending")
    if np.any(daily[np.isfinite(daily)] < 0):
        raise ValueError("negative precipitation present (QF.OUT_OF_RANGE); quarantine the input")
    ym = dates.astype("datetime64[M]")
    months = np.unique(ym)
    cell_shape = daily.shape[1:]
    total = np.full((len(months),) + cell_shape, np.nan)
    frac = np.zeros((len(months),) + cell_shape)
    flags = np.zeros((len(months),) + cell_shape, dtype=np.uint16)
    yrs = months.astype("datetime64[Y]").astype(int) + 1970
    mos = (months.astype(int) % 12) + 1
    for i, m in enumerate(months):
        sel = ym == m
        expected = calendar.monthrange(int(yrs[i]), int(mos[i]))[1]
        block = daily[sel]
        valid = np.isfinite(block)
        nvalid = valid.sum(axis=0)
        f = nvalid / expected
        frac[i] = f
        ok = f >= min_completeness
        s = np.where(valid, block, 0.0).sum(axis=0)
        total[i] = np.where(ok, s, np.nan)
        fl = np.full(cell_shape, int(QF.DATA_OK), dtype=np.uint16)
        fl = np.where(f < 1.0, fl | int(QF.MISSING_DATA), fl)
        fl = np.where(~ok, (fl & ~np.uint16(QF.DATA_OK)) | int(QF.INCOMPLETE_MONTH), fl)
        flags[i] = fl.astype(np.uint16)
    return dict(total=total, valid_fraction=frac, flags=flags, years=yrs, months=mos)

def climatology(total, years, months, baseline, min_samples):
    """Per calendar month mean over valid baseline years; NaN where fewer than min_samples."""
    total = np.asarray(total, float)
    b0, b1 = baseline
    clim = np.full((12,) + total.shape[1:], np.nan)
    n = np.zeros((12,) + total.shape[1:], dtype=int)
    for m in range(1, 13):
        sel = (months == m) & (years >= b0) & (years <= b1)
        blk = total[sel]
        v = np.isfinite(blk)
        n[m - 1] = v.sum(axis=0)
        s = np.where(v, blk, 0.0).sum(axis=0)
        with np.errstate(invalid="ignore", divide="ignore"):
            mean = s / n[m - 1]
        clim[m - 1] = np.where(n[m - 1] >= min_samples, mean, np.nan)
    return clim, n

def anomalies(total, years, months, baseline=(1991, 2020), min_samples=25, min_clim_mm=1.0):
    """Absolute (mm) and percentage anomalies. Percent only where climatology >= min_clim_mm."""
    total = np.asarray(total, float)
    clim, n = climatology(total, years, months, baseline, min_samples)
    c = clim[months - 1]
    anom = total - c
    with np.errstate(invalid="ignore", divide="ignore"):
        pct = np.where(c >= min_clim_mm, 100.0 * anom / c, np.nan)
    return dict(anomaly_mm=anom, anomaly_pct=pct, climatology=clim, baseline_n=n,
                baseline=baseline)
