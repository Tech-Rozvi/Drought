"""Reconnaissance Drought Index (Tsakiris & Vangelis 2005): ratio of accumulated precipitation to
accumulated evaporative demand.

  alpha_k(t) = sum_{k months} P / sum_{k months} PET
  RDI_n  = alpha / mean(alpha) - 1                    (normalised)
  RDI_st = (ln alpha - mean(ln alpha)) / std(ln alpha)  (standardised, lognormal assumption)
Baseline statistics per calendar endpoint month, baseline years only (std with ddof=1).
PET must be FAO-56 ET0 (primary) or an explicitly labelled alternative; this module does not
choose PET. alpha = 0 (no rain) is valid for RDI_n (= -1) but RDI_st is null (ln 0) with
ZERO_INFLATED; PET <= 0 makes the ratio invalid (null). Season-window variant: rdi_windows().
"""
import numpy as np
from scipy.special import ndtri  # noqa: F401  (kept for API symmetry)
from .flags import QF
from .timeaxis import accumulate, check_monthly_contiguous

def _stats(alpha_b, min_samples):
    v = np.isfinite(alpha_b); n = v.sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(v, alpha_b, 0).sum(axis=0) / n
        pos = v & (alpha_b > 0)
        allpos = (pos.sum(axis=0) == n) & (n > 0)
        ly = np.where(pos, np.log(np.where(pos, alpha_b, 1.0)), 0.0)
        ymean = ly.sum(axis=0) / n
        var = np.where(pos, (ly - ymean) ** 2, 0.0).sum(axis=0) / (n - 1)
        ystd = np.sqrt(var)
    ok_n = n >= min_samples
    ok_st = ok_n & allpos & np.isfinite(ystd) & (ystd > 1e-9)
    ok_n_idx = ok_n & np.isfinite(mean) & (mean > 0)
    return dict(n=n, mean=mean, ymean=ymean, ystd=ystd, ok_n=ok_n_idx, ok_st=ok_st, allpos=allpos)

def _finish(alpha, idxs, years, baseline_mask_fn, min_samples, out_n, out_st, flags, par):
    for slot, idx in enumerate(idxs):
        inb = baseline_mask_fn(idx)
        st = _stats(alpha[inb], min_samples)
        for key in ("n", "mean", "ymean", "ystd"):
            par[key][slot] = st[key]
        a = alpha[idx]; fin = np.isfinite(a)
        with np.errstate(invalid="ignore", divide="ignore"):
            rn = a / st["mean"][None, :] - 1.0
            rs = (np.log(np.where(a > 0, a, np.nan)) - st["ymean"][None, :]) / st["ystd"][None, :]
        good_n = fin & st["ok_n"][None, :]
        good_s = fin & st["ok_st"][None, :] & (a > 0)
        out_n[idx] = np.where(good_n, rn, np.nan); out_st[idx] = np.where(good_s, rs, np.nan)
        f = np.zeros(a.shape, dtype=np.uint16)
        f |= np.where(good_n | good_s, np.uint16(QF.DATA_OK), np.uint16(0)).astype(np.uint16)
        f |= np.where(~fin, np.uint16(QF.MISSING_DATA), np.uint16(0)).astype(np.uint16)
        f |= np.where(fin & ~good_s, np.uint16(QF.FIT_FAIL), np.uint16(0)).astype(np.uint16)
        f |= np.where(fin & (st["n"][None, :] < min_samples), np.uint16(QF.LOW_SAMPLE | QF.BASELINE_INCOMPLETE), np.uint16(0)).astype(np.uint16)
        f |= np.where(fin & ((a == 0) | ~st["allpos"][None, :]), np.uint16(QF.ZERO_INFLATED), np.uint16(0)).astype(np.uint16)
        flags[idx] = f

def rdi(precip_monthly, pet_monthly, years, months, k, baseline=(1991, 2020), min_samples=25):
    P = np.asarray(precip_monthly, float); E = np.asarray(pet_monthly, float)
    if P.shape != E.shape:
        raise ValueError("precipitation and PET must share shape and period (CALENDAR_ERROR)")
    years = np.asarray(years, int); months = np.asarray(months, int)
    check_monthly_contiguous(years, months)
    cs = P.shape[1:]; Pf = P.reshape(P.shape[0], -1); Ef = np.where(E > 0, E, np.nan).reshape(P.shape[0], -1)
    with np.errstate(invalid="ignore", divide="ignore"):
        alpha = accumulate(Pf, k) / accumulate(Ef, k)
    T, C = alpha.shape
    out_n = np.full((T, C), np.nan); out_st = np.full((T, C), np.nan); flags = np.zeros((T, C), np.uint16)
    par = {key: np.full((12, C), np.nan) for key in ("n", "mean", "ymean", "ystd")}
    idxs = [np.where(months == m)[0] for m in range(1, 13)]
    _finish(alpha, idxs, years, lambda idx: idx[(years[idx] >= baseline[0]) & (years[idx] <= baseline[1])],
            min_samples, out_n, out_st, flags, par)
    flags[:k - 1] |= np.uint16(QF.MISSING_DATA)
    shp = (T,) + cs
    return dict(rdi_n=out_n.reshape(shp), rdi_st=out_st.reshape(shp), alpha=alpha.reshape(shp), flags=flags.reshape(shp),
                params={key: v.reshape((12,) + cs) for key, v in par.items()},
                config=dict(k=k, baseline=baseline, standardisation="lognormal (ln alpha), ddof=1",
                            validation="NOT yet validated against a reference implementation"))

def rdi_windows(precip_monthly, pet_monthly, years, months, window_months, baseline=(1991, 2020), min_samples=20):
    """Season-window RDI, e.g. window_months=[11,12,1,2,3,4] for a maize season. A window that crosses
    the year end is labelled by its starting year. All window months must be present and valid."""
    P = np.asarray(precip_monthly, float); E = np.asarray(pet_monthly, float)
    if P.shape != E.shape:
        raise ValueError("precipitation and PET must share shape and period")
    years = np.asarray(years, int); months = np.asarray(months, int)
    check_monthly_contiguous(years, months)
    wm = list(window_months); start = wm[0]
    if len(set(wm)) != len(wm) or any(m < 1 or m > 12 for m in wm):
        raise ValueError("invalid window months")
    cross = any(wm[i + 1] < wm[i] for i in range(len(wm) - 1))
    sy = np.where(months >= start, years, years - 1) if cross else years.copy()
    seasons = np.unique(sy[np.isin(months, wm)])
    cs = P.shape[1:]; Pf = P.reshape(P.shape[0], -1); Ef = np.where(E > 0, E, np.nan).reshape(P.shape[0], -1)
    alpha = np.full((len(seasons), Pf.shape[1]), np.nan); complete = np.zeros(len(seasons), bool)
    for i, s in enumerate(seasons):
        sel = (sy == s) & np.isin(months, wm)
        if sel.sum() == len(wm):
            complete[i] = True
            with np.errstate(invalid="ignore", divide="ignore"):
                alpha[i] = Pf[sel].sum(axis=0) / Ef[sel].sum(axis=0)
    out_n = np.full(alpha.shape, np.nan); out_st = np.full(alpha.shape, np.nan)
    flags = np.zeros(alpha.shape, np.uint16)
    par = {key: np.full((1, alpha.shape[1]), np.nan) for key in ("n", "mean", "ymean", "ystd")}
    idx = np.arange(len(seasons))
    _finish(alpha, [idx], seasons, lambda ix: ix[(seasons[ix] >= baseline[0]) & (seasons[ix] <= baseline[1])],
            min_samples, out_n, out_st, flags, par)
    flags[~complete] |= np.uint16(QF.INCOMPLETE_MONTH)
    shp = (len(seasons),) + cs
    return dict(season_year=seasons, rdi_n=out_n.reshape(shp), rdi_st=out_st.reshape(shp), alpha=alpha.reshape(shp),
                flags=flags.reshape(shp), window_months=wm,
                params={key: v.reshape((1,) + cs) for key, v in par.items()})
