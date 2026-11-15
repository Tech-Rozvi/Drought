"""Run the daily water balance over crop seasons: sowing-date x growing-period ensemble.

The calendar gives windows, not actual planting dates, so the engine reports the spread across the
sowing window (and across the min/max growing period) as uncertainty. Output is a stress indicator
(WRSI, ETa/ETc, stress days) - never a yield or loss estimate.
"""
import numpy as np
from .wrsi import bucket_daily, wrsi, wrsi_by_stage
from .phenology import kc_curve
from .flags2 import L2Flag

def longest_run(mask):
    """Longest run of True along axis 0 (vectorised over cells)."""
    run = np.zeros(mask.shape[1:], int); best = np.zeros(mask.shape[1:], int)
    for t in range(mask.shape[0]):
        run = np.where(mask[t], run + 1, 0); best = np.maximum(best, run)
    return best

def run_season(dates, precip, et0, sow_date, gp_days, params, taw, s0_fraction):
    dates = np.asarray(dates).astype("datetime64[D]"); sow = np.datetime64(sow_date, "D")
    idx = np.where(dates == sow)[0]
    if len(idx) != 1 or idx[0] + gp_days > len(dates) or dates[idx[0] + gp_days - 1] - sow != np.timedelta64(gp_days - 1, "D"):
        return None, [L2Flag.FORCING_INCOMPLETE]          # season not fully covered by contiguous forcing
    sl = slice(idx[0], idx[0] + gp_days)
    kc, stage = kc_curve(gp_days, params.stage_fractions, params.kc_ini, params.kc_mid, params.kc_end)
    P = precip[sl]; E = et0[sl]; K = np.broadcast_to(kc.reshape((-1,) + (1,) * (P.ndim - 1)), P.shape)
    b = bucket_daily(P, E, K, taw, params.depletion_p, s0_fraction)
    ok = np.isfinite(b["eta"]).all(axis=0)
    out = dict(sow_date=str(sow), gp_days=gp_days,
               wrsi=wrsi(b["eta"], b["etc"]),
               wrsi_by_stage=wrsi_by_stage(b["eta"], b["etc"], stage),
               stress_days=np.where(ok, (b["ks"] < 1.0 - 1e-9).sum(axis=0), -1),
               longest_stress_spell=np.where(ok, longest_run(b["ks"] < 1.0 - 1e-9), -1),
               season_rain_mm=np.where(np.isfinite(P).all(axis=0), P.sum(axis=0), np.nan),
               season_etc_mm=np.where(ok, b["etc"].sum(axis=0), np.nan),
               min_storage_fraction=np.where(ok, b["storage"].min(axis=0) / taw, np.nan),
               assumptions=b["assumptions"])
    return out, []

def run_ensemble(dates, precip, et0, sow_dates, gp_range, params, taw, s0_fraction):
    members = []; flags = set()
    for sd in sow_dates:
        for gp in sorted(set(gp_range)):
            m, f = run_season(dates, precip, et0, sd, gp, params, taw, s0_fraction)
            flags.update(f)
            if m is not None:
                members.append(m)
    if not members:
        return dict(n_members=0, flags=sorted(flags, key=str)), members
    W = np.stack([m["wrsi"] for m in members])
    summ = dict(n_members=len(members), wrsi_min=np.nanmin(W, axis=0), wrsi_median=np.nanmedian(W, axis=0),
                wrsi_max=np.nanmax(W, axis=0), wrsi_spread=np.nanmax(W, axis=0) - np.nanmin(W, axis=0),
                flags=sorted(flags, key=str))
    return summ, members
