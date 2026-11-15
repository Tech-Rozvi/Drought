import numpy as np

def ks_statistic(sorted_sample, cdf_vals, n):
    """One-sample KS statistic. sorted_sample/cdf_vals: (N_max, C) with NaN padding at the end;
    n: valid count per column. Returns D per column (NaN where n == 0)."""
    N = sorted_sample.shape[0]
    r = np.arange(1, N + 1)[:, None]
    valid = r <= n[None, :]
    with np.errstate(invalid="ignore", divide="ignore"):
        dplus = np.where(valid, r / n[None, :] - cdf_vals, -np.inf).max(axis=0)
        dminus = np.where(valid, cdf_vals - (r - 1) / n[None, :], -np.inf).max(axis=0)
    D = np.maximum(dplus, dminus)
    return np.where(n > 0, D, np.nan)
