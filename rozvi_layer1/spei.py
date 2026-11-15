"""SPEI: three-parameter log-logistic fitted by probability-weighted moments (Vicente-Serrano et
al. 2010). D = P - PET accumulated over k months; each calendar endpoint month fitted separately
on baseline years only. PET must be FAO-56 ET0 (primary stream) or a separately labelled PET
stream; this module does not choose or substitute PET.

  w_s = (1/N) sum_i (1 - F_i)^s D_(i),  F_i = (i - 0.35)/N   (D sorted ascending)
  beta  = (2 w1 - w0) / (6 w1 - w0 - 6 w2)
  alpha = (w0 - 2 w1) beta / (Gamma(1+1/beta) Gamma(1-1/beta))
  gamma = w0 - alpha Gamma(1+1/beta) Gamma(1-1/beta)
  F(x)  = [1 + (alpha/(x-gamma))^beta]^-1 ;  SPEI = Phi^-1(F)
Not a z-score. Fit requires beta > 1, alpha > 0. Failed fit -> NaN + QF.FIT_FAIL.
"""
import numpy as np
from scipy.special import gamma as G, ndtri
from .flags import QF
from .timeaxis import accumulate, check_monthly_contiguous
from .fitdiag import ks_statistic

def _cdf(x, alpha, beta, gam):
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        t = x - gam
        return np.where(t > 0, 1.0 / (1.0 + (alpha / t) ** beta), 0.0)

def fit_loglogistic_pwm(B, min_samples=25, ks_coeff=1.36):
    valid = np.isfinite(B)
    n = valid.sum(axis=0)
    srt = np.sort(np.where(valid, B, np.nan), axis=0)
    N = B.shape[0]
    r = np.arange(1, N + 1)[:, None]
    with np.errstate(invalid="ignore", divide="ignore"):
        F = (r - 0.35) / n[None, :]
        inb = r <= n[None, :]
        w = []
        for s in (0, 1, 2):
            term = np.where(inb, (1 - F) ** s * np.nan_to_num(srt), 0.0)
            w.append(term.sum(axis=0) / n)
        w0, w1, w2 = w
        beta = (2 * w1 - w0) / (6 * w1 - w0 - 6 * w2)
        g = G(1 + 1 / beta) * G(1 - 1 / beta)
        alpha = (w0 - 2 * w1) * beta / g
        gam = w0 - alpha * g
        cdf = _cdf(srt, alpha[None, :], beta[None, :], gam[None, :])
        D = ks_statistic(srt, cdf, n)
        dcrit = ks_coeff / np.sqrt(n)
    ok = (n >= min_samples) & np.isfinite(beta) & (beta > 1) & np.isfinite(alpha) & (alpha > 0) & np.isfinite(gam)
    gof_ok = np.isfinite(D) & (D <= dcrit)
    return dict(n=n, alpha=alpha, beta=beta, gamma=gam, ks_D=D, ks_crit=dcrit, fit_ok=ok, gof_ok=gof_ok)

def spei(precip_monthly, pet_monthly, years, months, k, baseline=(1991, 2020), min_samples=25,
         p_eps=1e-6, ks_coeff=1.36, enforce_gof=True):
    P = np.asarray(precip_monthly, float); E = np.asarray(pet_monthly, float)
    if P.shape != E.shape:
        raise ValueError("precipitation and PET must share shape and monthly period (CALENDAR_ERROR)")
    years = np.asarray(years, int); months = np.asarray(months, int)
    check_monthly_contiguous(years, months)
    cell_shape = P.shape[1:]
    D = (P - E).reshape(P.shape[0], -1)          # NaN in either input -> NaN (never zero)
    acc = accumulate(D, k)
    T, C = acc.shape
    out = np.full((T, C), np.nan)
    flags = np.zeros((T, C), dtype=np.uint16)
    prm = {key: np.full((12, C), np.nan) for key in ("alpha", "beta", "gamma", "n", "ks_D")}
    for m in range(1, 13):
        idx = np.where(months == m)[0]
        inb = idx[(years[idx] >= baseline[0]) & (years[idx] <= baseline[1])]
        fit = fit_loglogistic_pwm(acc[inb], min_samples, ks_coeff)
        for key in prm:
            prm[key][m - 1] = fit[key]
        usable = fit["fit_ok"] & (fit["gof_ok"] if enforce_gof else True)
        a = acc[idx]; finite = np.isfinite(a)
        Fv = _cdf(a, fit["alpha"][None, :], fit["beta"][None, :], fit["gamma"][None, :])
        clipped = finite & usable[None, :] & ((Fv < p_eps) | (Fv > 1 - p_eps))
        val = ndtri(np.clip(Fv, p_eps, 1 - p_eps))
        good = finite & usable[None, :]
        out[idx] = np.where(good, val, np.nan)
        f = np.zeros(a.shape, dtype=np.uint16)
        f |= np.where(good, np.uint16(QF.DATA_OK | QF.FIT_OK), np.uint16(0)).astype(np.uint16)
        f |= np.where(~finite, np.uint16(QF.MISSING_DATA), np.uint16(0)).astype(np.uint16)
        f |= np.where(finite & ~usable[None, :], np.uint16(QF.FIT_FAIL), np.uint16(0)).astype(np.uint16)
        f |= np.where(finite & (fit["n"][None, :] < min_samples),
                      np.uint16(QF.LOW_SAMPLE | QF.BASELINE_INCOMPLETE), np.uint16(0)).astype(np.uint16)
        f |= np.where(finite & fit["fit_ok"][None, :] & ~fit["gof_ok"][None, :],
                      np.uint16(QF.GOF_FAIL), np.uint16(0)).astype(np.uint16)
        f |= np.where(clipped, np.uint16(QF.PROB_CLIPPED), np.uint16(0)).astype(np.uint16)
        flags[idx] = f
    flags[:k - 1] |= np.uint16(QF.MISSING_DATA)
    shp = (P.shape[0],) + cell_shape
    return dict(spei=out.reshape(shp), flags=flags.reshape(shp),
                params={key: v.reshape((12,) + cell_shape) for key, v in prm.items()},
                config=dict(k=k, baseline=baseline, distribution="3-parameter log-logistic",
                            fitting="unbiased PWM, F_i=(i-0.35)/N", min_samples=min_samples,
                            p_eps=p_eps, ks_coeff=ks_coeff, enforce_gof=enforce_gof,
                            validation="NOT yet validated against a reference implementation"))
