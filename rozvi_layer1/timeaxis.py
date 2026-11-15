import numpy as np

def check_monthly_contiguous(years, months):
    years = np.asarray(years, int); months = np.asarray(months, int)
    idx = years * 12 + (months - 1)
    if len(idx) and not np.all(np.diff(idx) == 1):
        raise ValueError("monthly series must be contiguous, sorted and without duplicates (CALENDAR_ERROR)")
    return idx

def accumulate(x, k):
    """X_k(t) = sum of the current and preceding k-1 months. NaN anywhere in window -> NaN."""
    x = np.asarray(x, float)
    T = x.shape[0]
    out = np.full(x.shape, np.nan)
    if T >= k:
        s = np.zeros((T - k + 1,) + x.shape[1:])
        for j in range(k):
            s = s + x[j:T - k + 1 + j]
        out[k - 1:] = s
    return out
