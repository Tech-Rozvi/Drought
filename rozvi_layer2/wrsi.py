"""Layer 2 water-requirement core: daily root-zone bucket (FAO-56 Ks) and the Water Requirement
Satisfaction Index, WRSI = 100 * sum(ETa) / sum(WR), WR = ETc = Kc * ET0 (FAO / FEWS NET form).

NO crop or soil defaults are supplied: Kc series, total available water (TAW, mm), depletion
fraction p and initial storage must be passed explicitly (and cited) by the caller.
Simplifications, recorded in every result: effective rain = rain (no surface-runoff model); water
above TAW drains; irrigation = 0 (rain-fed upper-bound stress); Ks computed from storage after
the day's rain. Missing forcing never becomes zero: state is unknown afterwards (NaN) until the
caller re-initialises. Output is a stress indicator, NOT a yield or loss estimate.
"""
import numpy as np

def bucket_daily(precip, et0, kc, taw, p, s0_fraction):
    P = np.asarray(precip, float); E = np.asarray(et0, float); Kc = np.asarray(kc, float)
    if not (P.shape == E.shape == Kc.shape):
        raise ValueError("precip, et0 and kc must share shape (time first)")
    taw = np.asarray(taw, float); p = np.asarray(p, float)
    if np.any(taw <= 0) or np.any((p <= 0) | (p >= 1)) or not (0 <= s0_fraction <= 1):
        raise ValueError("invalid TAW, depletion fraction p or initial fraction")
    T = P.shape[0]; cs = P.shape[1:]
    S = np.broadcast_to(taw * s0_fraction, cs).astype(float).copy()
    out = {k: np.full(P.shape, np.nan) for k in ("etc", "eta", "ks", "storage", "drainage")}
    for t in range(T):
        pt, et, kt = P[t], E[t], Kc[t]
        bad = ~(np.isfinite(pt) & np.isfinite(et) & np.isfinite(kt) & np.isfinite(S))
        Sn = S + np.where(bad, 0.0, pt)
        drain = np.maximum(0.0, Sn - taw); Sn = Sn - drain
        etc = kt * et
        ks = np.minimum(1.0, Sn / ((1.0 - p) * taw))
        eta = np.minimum(ks * etc, Sn)
        Sn = Sn - eta
        S = np.where(bad, np.nan, Sn)
        for key, val in (("etc", etc), ("eta", eta), ("ks", ks), ("storage", S), ("drainage", drain)):
            out[key][t] = np.where(bad, np.nan, val)
    out["initial_storage"] = taw * s0_fraction
    out["assumptions"] = ("effective rain = rain; no surface runoff; drainage above TAW; irrigation = 0; "
                          "Ks from post-rain storage; rain-fed potential stress (upper bound if irrigated)")
    return out

def wrsi(eta, etc, season_mask=None):
    """WRSI (%) over the selected days. Any missing day in the season -> NaN (never partial)."""
    eta = np.asarray(eta, float); etc = np.asarray(etc, float)
    if season_mask is not None:
        m = np.asarray(season_mask, bool); eta = eta[m]; etc = etc[m]
    with np.errstate(invalid="ignore", divide="ignore"):
        w = 100.0 * eta.sum(axis=0) / etc.sum(axis=0)
    complete = np.isfinite(eta).all(axis=0) & np.isfinite(etc).all(axis=0) & (etc.sum(axis=0) > 0)
    return np.where(complete, np.clip(w, 0.0, 100.0), np.nan)

def wrsi_by_stage(eta, etc, stage_ids):
    stage_ids = np.asarray(stage_ids)
    return {int(s): wrsi(eta, etc, stage_ids == s) for s in np.unique(stage_ids) if s >= 0}
