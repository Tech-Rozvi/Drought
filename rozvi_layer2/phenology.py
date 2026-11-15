"""Daily Kc curve (FAO-56 four-stage shape) and stage ids from a growing period in days."""
import numpy as np

def stage_lengths(gp_days, fractions):
    """Largest-remainder rounding so the four stage lengths sum exactly to gp_days."""
    raw = np.asarray(fractions, float) * gp_days
    base = np.floor(raw).astype(int); rem = gp_days - base.sum()
    order = np.argsort(-(raw - base))
    for i in order[:rem]:
        base[i] += 1
    if np.any(base < 1):
        raise ValueError("growing period too short for four stages")
    return base

def kc_curve(gp_days, fractions, kc_ini, kc_mid, kc_end):
    """Returns (kc[gp], stage_id[gp]) with stage 0 initial, 1 development, 2 mid, 3 late."""
    L = stage_lengths(gp_days, fractions)
    kc = np.empty(gp_days); st = np.empty(gp_days, dtype=int); i = 0
    kc[i:i + L[0]] = kc_ini; st[i:i + L[0]] = 0; i += L[0]
    kc[i:i + L[1]] = kc_ini + (kc_mid - kc_ini) * (np.arange(1, L[1] + 1) / L[1]); st[i:i + L[1]] = 1; i += L[1]
    kc[i:i + L[2]] = kc_mid; st[i:i + L[2]] = 2; i += L[2]
    kc[i:i + L[3]] = kc_mid + (kc_end - kc_mid) * (np.arange(1, L[3] + 1) / L[3]); st[i:i + L[3]] = 3
    return kc, st
