"""Standardized Precipitation Index (mixed gamma, explicit zero handling).

For accumulation window k: X_k(t) = sum of monthly P over t-k+1..t (all months must be valid).
Calendar endpoint month m has its own distribution, fitted only on baseline years.
  q   = (# zero accumulations) / n                      (probability mass at zero)
  G   = Gamma(alpha, beta) fitted to the positive baseline accumulations
  H(x)= q + (1-q) G(x)                                  (H(0) = q; zero_prob="wmo", default)
  Option zero_prob="stagge": H(0) = (n0+1)/(2(n+1)), the mid-probability of the zero mass, which
  removes the positive bias of the baseline mean in zero-inflated months. With "wmo" the SPI of all
  zero accumulations is the same value Phi^-1(q); baseline mean SPI is then > 0 when q is large.
  SPI = Phi^-1( clip(H, eps, 1-eps) )
Gamma parameters: closed-form ML approximation (Thom 1958):
  A = ln(mean) - mean(ln x);  alpha = (1 + sqrt(1 + 4A/3)) / (4A);  beta = mean / alpha.
Never borrows parameters from other cells. Failed fit -> NaN + QF.FIT_FAIL.
SPI is a precipitation anomaly index, not soil moisture, crop damage or water availability.
"""
import numpy as np
from scipy.special import gammainc, ndtri
from .flags import QF
from .timeaxis import accumulate, check_monthly_contiguous
from .fitdiag import ks_statistic

def fit_gamma_mixed(B, min_samples=25, min_positive=10, ks_coeff=1.36, zero_inflated_q=0.10):
    """B: (nb, C) baseline accumulations for one endpoint month (NaN = missing)."""
    valid = np.isfinite(B)
    n = valid.sum(axis=0)
    zero = valid & (B == 0)
    n0 = zero.sum(axis=0)
    pos = valid & (B > 0)
    npos = pos.sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        q = np.where(n > 0, n0 / n, np.nan)
        Bp = np.where(pos, B, 1.0)
        mean = np.where(npos > 0, np.where(pos, B, 0.0).sum(axis=0) / npos, np.nan)
        meanlog = np.where(npos > 0, np.where(pos, np.log(Bp), 0.0).sum(axis=0) / npos, np.nan)
        A = np.log(mean) - meanlog
        alpha = (1 + np.sqrt(1 + 4 * A / 3)) / (4 * A)
        beta = mean / alpha
    ok = (n >= min_samples) & (npos >= min_positive) & np.isfinite(A) & (A > 1e-9) \
        & np.isfinite(alpha) & np.isfinite(beta) & (alpha > 0) & (beta > 0)
    # goodness of fit on the positive part (parameters estimated from same data -> permissive test)
    srt = np.sort(np.where(pos, B, np.nan), axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        cdf = gammainc(alpha[None, :], srt / beta[None, :])
    D = ks_statistic(srt, cdf, npos)
    with np.errstate(invalid="ignore", divide="ignore"):
        dcrit = ks_coeff / np.sqrt(npos)
    gof_ok = np.isfinite(D) & (D <= dcrit)
    return dict(n=n, n_zero=n0, n_pos=npos, q=q, alpha=alpha, beta=beta, ks_D=D, ks_crit=dcrit,
                fit_ok=ok, gof_ok=gof_ok, zero_inflated=(q >= zero_inflated_q))

def spi(monthly, years, months, k, baseline=(1991, 2020), min_samples=25, min_positive=10,
        p_eps=1e-6, ks_coeff=1.36, enforce_gof=True, zero_prob="wmo"):
    if zero_prob not in ("wmo", "stagge"):
        raise ValueError("zero_prob must be 'wmo' or 'stagge'")
    x = np.asarray(monthly, float)
    years = np.asarray(years, int); months = np.asarray(months, int)
    check_monthly_contiguous(years, months)
    cell_shape = x.shape[1:]
    X = x.reshape(x.shape[0], -1)
    acc = accumulate(X, k)
    T, C = acc.shape
    out = np.full((T, C), np.nan)
    flags = np.zeros((T, C), dtype=np.uint16)
    P = {key: np.full((12, C), np.nan) for key in ("q", "alpha", "beta", "n", "n_zero", "n_pos", "ks_D")}
    for m in range(1, 13):
        idx = np.where(months == m)[0]
        inb = idx[(years[idx] >= baseline[0]) & (years[idx] <= baseline[1])]
        fit = fit_gamma_mixed(acc[inb], min_samples, min_positive, ks_coeff)
        for key in P:
            P[key][m - 1] = fit[key]
        usable = fit["fit_ok"] & (fit["gof_ok"] if enforce_gof else True)
        a = acc[idx]
        finite = np.isfinite(a)
        with np.errstate(invalid="ignore", divide="ignore"):
            G = gammainc(fit["alpha"][None, :], np.where(a > 0, a, 0.0) / fit["beta"][None, :])
            H = fit["q"][None, :] + (1 - fit["q"][None, :]) * np.where(a > 0, G, 0.0)
            if zero_prob == "stagge":  # mid-probability of the zero mass (Stagge et al. 2015)
                H0 = (fit["n_zero"][None, :] + 1.0) / (2.0 * (fit["n"][None, :] + 1.0))
                H = np.where(a == 0, H0, H)
        clipped = finite & usable[None, :] & ((H < p_eps) | (H > 1 - p_eps))
        Hc = np.clip(H, p_eps, 1 - p_eps)
        val = ndtri(Hc)
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
        f |= np.where(finite & fit["zero_inflated"][None, :], np.uint16(QF.ZERO_INFLATED), np.uint16(0)).astype(np.uint16)
        f |= np.where(clipped, np.uint16(QF.PROB_CLIPPED), np.uint16(0)).astype(np.uint16)
        flags[idx] = f
    # first k-1 steps have an incomplete accumulation window
    flags[:k - 1] |= np.uint16(QF.MISSING_DATA)
    shp = (x.shape[0],) + cell_shape
    return dict(spi=out.reshape(shp), flags=flags.reshape(shp),
                params={key: v.reshape((12,) + cell_shape) for key, v in P.items()},
                config=dict(k=k, baseline=baseline, distribution="mixed gamma (zero mass + 2-parameter gamma)",
                            fitting="Thom ML approximation", zero_prob=zero_prob, min_samples=min_samples,
                            min_positive=min_positive, p_eps=p_eps, ks_coeff=ks_coeff,
                            enforce_gof=enforce_gof))
