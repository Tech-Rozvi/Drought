"""Area/crop-weighted summaries that never use invalid cells and always report valid fraction."""
import numpy as np

def weighted_mean(values, weights):
    v = np.asarray(values, float); w = np.asarray(weights, float)
    ok = np.isfinite(v) & np.isfinite(w) & (w > 0)
    tot = np.nansum(np.where(np.isfinite(w) & (w > 0), w, 0.0))
    if ok.sum() == 0 or tot == 0:
        return dict(mean=np.nan, valid_weight_fraction=0.0, n_valid=0)
    return dict(mean=float((v[ok] * w[ok]).sum() / w[ok].sum()), valid_weight_fraction=float(w[ok].sum() / tot), n_valid=int(ok.sum()))

def weighted_fraction_below(values, weights, threshold):
    v = np.asarray(values, float); w = np.asarray(weights, float); ok = np.isfinite(v) & np.isfinite(w) & (w > 0)
    if ok.sum() == 0:
        return dict(fraction=np.nan, valid_weight_fraction=0.0)
    return dict(fraction=float(w[ok][v[ok] < threshold].sum() / w[ok].sum()),
                valid_weight_fraction=float(w[ok].sum() / np.nansum(np.where(w > 0, w, 0.0))))
