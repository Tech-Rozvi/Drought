"""Unit and scientific-invariant tests. Synthetic vectors here are TEST-ONLY inputs."""
import unittest, calendar
import numpy as np
from scipy.special import ndtri
from rozvi_layer1.flags import QF
from rozvi_layer1.monthly import monthly_totals, anomalies
from rozvi_layer1.timeaxis import accumulate, check_monthly_contiguous
from rozvi_layer1.spi import spi
from rozvi_layer1.spei import spei, fit_loglogistic_pwm
from rozvi_layer1.events import detect_events

def make_axis(y0, y1):
    ys, ms = [], []
    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            ys.append(y); ms.append(m)
    return np.array(ys), np.array(ms)

def synthetic_rain(years, months, ncell, seed=0, dry_zero_prob=0.0):
    rng = np.random.default_rng(seed)
    scale = np.where(np.isin(months, [12, 1, 2, 3]), 40.0, np.where(np.isin(months, [6, 7, 8]), 2.0, 15.0))
    p = rng.gamma(4.0, scale[:, None] / 4.0, size=(len(months), ncell))
    if dry_zero_prob:
        dry = np.isin(months, [6, 7, 8])
        z = rng.random(p.shape) < dry_zero_prob
        p = np.where(dry[:, None] & z, 0.0, p)
    return p

class TestMonthly(unittest.TestCase):
    def dates(self, y, m):
        n = calendar.monthrange(y, m)[1]
        return np.arange(np.datetime64(f"{y}-{m:02d}-01"), np.datetime64(f"{y}-{m:02d}-01") + np.timedelta64(n, 'D'))
    def test_sum_and_leap_year(self):
        d = self.dates(2020, 2); r = monthly_totals(np.full(len(d), 2.0), d)
        self.assertEqual(len(d), 29); self.assertAlmostEqual(r["total"][0], 58.0)
        d = self.dates(2021, 2); r = monthly_totals(np.full(len(d), 2.0), d)
        self.assertAlmostEqual(r["total"][0], 56.0)
    def test_zero_rain_is_valid_not_missing(self):
        d = self.dates(2020, 7); r = monthly_totals(np.zeros(len(d)), d)
        self.assertEqual(r["total"][0], 0.0); self.assertTrue(r["flags"][0] & QF.DATA_OK)
    def test_fully_missing_month_is_null_not_zero(self):
        d = self.dates(2020, 7); r = monthly_totals(np.full(len(d), np.nan), d)
        self.assertTrue(np.isnan(r["total"][0])); self.assertTrue(r["flags"][0] & QF.INCOMPLETE_MONTH)
    def test_completeness_threshold(self):
        d = self.dates(2020, 1); x = np.ones(31)
        x[:3] = np.nan  # 28/31 = 0.903 -> accepted, flagged MISSING_DATA, value = sum of valid (lower bound)
        r = monthly_totals(x, d); self.assertAlmostEqual(r["total"][0], 28.0)
        self.assertTrue(r["flags"][0] & QF.MISSING_DATA)
        x[:4] = np.nan  # 27/31 = 0.871 -> rejected
        r = monthly_totals(x, d); self.assertTrue(np.isnan(r["total"][0]))
    def test_absent_dates_count_as_missing(self):
        d = self.dates(2020, 1)[:20]; r = monthly_totals(np.ones(20), d)
        self.assertTrue(np.isnan(r["total"][0]))
    def test_duplicates_and_negatives_rejected(self):
        d = self.dates(2020, 1); d2 = np.concatenate([d, d[:1]])
        with self.assertRaises(ValueError): monthly_totals(np.ones(len(d2)), d2)
        x = np.ones(len(d)); x[3] = -1
        with self.assertRaises(ValueError): monthly_totals(x, d)
    def test_constant_climatology_gives_zero_anomaly(self):
        ys, ms = make_axis(1981, 2000); tot = np.full((len(ys), 3), 50.0)
        a = anomalies(tot, ys, ms, baseline=(1991, 2000), min_samples=8)
        self.assertTrue(np.allclose(a["anomaly_mm"], 0)); self.assertTrue(np.allclose(a["anomaly_pct"], 0))
    def test_pct_anomaly_null_where_climatology_unstable(self):
        ys, ms = make_axis(1981, 2000); tot = np.zeros((len(ys), 1))
        a = anomalies(tot, ys, ms, baseline=(1991, 2000), min_samples=8)
        self.assertTrue(np.all(np.isnan(a["anomaly_pct"])))
        self.assertTrue(np.allclose(a["anomaly_mm"], 0))

class TestAccumulation(unittest.TestCase):
    def test_window_sum_and_nan(self):
        x = np.arange(1., 9.)[:, None]; a = accumulate(x, 3)
        self.assertTrue(np.all(np.isnan(a[:2]))); self.assertEqual(a[2, 0], 6.0); self.assertEqual(a[7, 0], 21.0)
        x[4] = np.nan; a = accumulate(x, 3)
        self.assertTrue(np.all(np.isnan(a[4:7])))
    def test_non_contiguous_rejected(self):
        with self.assertRaises(ValueError): check_monthly_contiguous([2000, 2000], [1, 3])

class TestSPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ys, cls.ms = make_axis(1981, 2025)
        cls.p = synthetic_rain(cls.ys, cls.ms, 200, seed=1, dry_zero_prob=0.3)
    def test_baseline_is_standardised_per_endpoint_month(self):
        for k in (1, 3, 6):
            r = spi(self.p, self.ys, self.ms, k)
            for m in range(1, 13):
                sel = (self.ms == m) & (self.ys >= 1991) & (self.ys <= 2020)
                v = r["spi"][sel]
                if m < k and k > 1:  # still fine (history before 1991 exists)
                    pass
                zi = np.nanmean(r["params"]["q"][m - 1]) >= 0.05  # zero-inflated months: see dedicated test
                if zi: continue
                self.assertLess(abs(np.nanmean(v)), 0.15, (k, m))
                self.assertGreater(np.nanstd(v), 0.85, (k, m)); self.assertLess(np.nanstd(v), 1.15, (k, m))
    def test_sign_convention_and_monotonic(self):
        r = spi(self.p, self.ys, self.ms, 1)
        m = 1; idx = np.where(self.ms == m)[0]
        base = idx[(self.ys[idx] >= 1991) & (self.ys[idx] <= 2020)]
        med = np.median(self.p[base], axis=0)
        i = idx[-1]  # January 2025, outside baseline
        wet = self.p[i] > np.quantile(self.p[base], 0.9, axis=0)
        dry = self.p[i] < np.quantile(self.p[base], 0.1, axis=0)
        self.assertTrue(np.all(r["spi"][i][wet] > 0)); self.assertTrue(np.all(r["spi"][i][dry] < 0))
        p2 = self.p.copy(); p2[i] = p2[i] * 1.5 + 5
        r2 = spi(p2, self.ys, self.ms, 1)
        self.assertTrue(np.all(r2["spi"][i] >= r["spi"][i] - 1e-12))  # more rain never drier
        self.assertTrue(np.array_equal(r2["spi"][:i], r["spi"][:i], equal_nan=True))  # baseline untouched
    def test_zero_accumulation_handled_via_mass(self):
        r = spi(self.p, self.ys, self.ms, 1)
        m = 7; idx = np.where(self.ms == m)[0]
        q = r["params"]["q"][m - 1]
        self.assertTrue(np.nanmean(q) > 0.2 and np.nanmean(q) < 0.4)
        zero = (self.p[idx] == 0) & np.isfinite(r["spi"][idx])
        self.assertTrue(zero.any())
        expect = np.broadcast_to(ndtri(np.clip(q, 1e-6, 1 - 1e-6)), zero.shape)
        self.assertTrue(np.allclose(r["spi"][idx][zero], expect[zero]))
        self.assertTrue(np.all(np.isfinite(r["spi"][idx][zero])))
        fl = r["flags"][idx][zero]; qq = np.broadcast_to(q, zero.shape)[zero]
        self.assertTrue(np.all((fl & QF.ZERO_INFLATED > 0)[qq >= 0.10]))
    def test_stagge_midprobability_removes_zero_bias(self):
        w = spi(self.p, self.ys, self.ms, 1, zero_prob="wmo")["spi"]
        g = spi(self.p, self.ys, self.ms, 1, zero_prob="stagge")["spi"]
        sel = (self.ms == 7) & (self.ys >= 1991) & (self.ys <= 2020)
        self.assertGreater(np.nanmean(w[sel]), 0.1)            # documented bias of H(0)=q
        self.assertLess(abs(np.nanmean(g[sel])), 0.1)          # mid-probability convention is ~unbiased
        with self.assertRaises(ValueError): spi(self.p, self.ys, self.ms, 1, zero_prob="x")
    def test_all_zero_series_returns_null_with_flag(self):
        p = np.zeros((len(self.ys), 1)); r = spi(p, self.ys, self.ms, 3)
        self.assertTrue(np.all(np.isnan(r["spi"]))); self.assertTrue(np.all(r["flags"][5:] & QF.FIT_FAIL))
    def test_constant_series_is_not_silently_zero(self):
        p = np.full((len(self.ys), 1), 30.0); r = spi(p, self.ys, self.ms, 1)
        self.assertTrue(np.all(np.isnan(r["spi"]))); self.assertTrue(np.all(r["flags"] & QF.FIT_FAIL))
    def test_insufficient_baseline_samples(self):
        ys, ms = make_axis(1981, 1995); p = synthetic_rain(ys, ms, 3, seed=2)
        r = spi(p, ys, ms, 1)  # only 5 baseline years (1991-1995)
        self.assertTrue(np.all(np.isnan(r["spi"]))); self.assertTrue(np.all(r["flags"] & QF.LOW_SAMPLE))
    def test_missing_input_stays_missing(self):
        p = self.p.copy(); i = 300; p[i, 0] = np.nan
        r = spi(p, self.ys, self.ms, 1)
        self.assertTrue(np.isnan(r["spi"][i, 0])); self.assertTrue(r["flags"][i, 0] & QF.MISSING_DATA)
        r3 = spi(p, self.ys, self.ms, 3)  # windows containing the gap are missing
        self.assertTrue(np.all(np.isnan(r3["spi"][i:i + 3, 0])))
    def test_probability_clipping_bounds(self):
        p = self.p.copy(); i = len(self.ys) - 12; p[i, 0] = 1e7
        r = spi(p, self.ys, self.ms, 1)
        self.assertAlmostEqual(r["spi"][i, 0], ndtri(1 - 1e-6), places=6)
        self.assertTrue(r["flags"][i, 0] & QF.PROB_CLIPPED)
    def test_each_endpoint_month_has_own_distribution(self):
        r = spi(self.p, self.ys, self.ms, 1)
        a = r["params"]["beta"]; self.assertGreater(np.nanmean(a[0]) / np.nanmean(a[6]), 5)  # Jan vs Jul scale
    def test_rerun_is_reproducible(self):
        a = spi(self.p, self.ys, self.ms, 6)["spi"]; b = spi(self.p, self.ys, self.ms, 6)["spi"]
        self.assertTrue(np.array_equal(a, b, equal_nan=True))

class TestSPEI(unittest.TestCase):
    def test_parameter_recovery(self):
        rng = np.random.default_rng(3); u = rng.random((20000, 1))
        a0, b0, g0 = 50.0, 4.0, -100.0
        x = g0 + a0 * (u / (1 - u)) ** (1 / b0)
        f = fit_loglogistic_pwm(x, min_samples=25)
        self.assertTrue(f["fit_ok"][0])
        self.assertAlmostEqual(f["beta"][0], b0, delta=0.4); self.assertAlmostEqual(f["alpha"][0], a0, delta=5.0)
        self.assertAlmostEqual(f["gamma"][0], g0, delta=10.0)
        self.assertLess(f["ks_D"][0], 0.02)
    def setUp(self):
        self.ys, self.ms = make_axis(1981, 2025)
        self.P = synthetic_rain(self.ys, self.ms, 300, seed=4)
        rng = np.random.default_rng(5)
        self.E = 60 + 20 * np.sin((self.ms[:, None] - 1) / 12 * 2 * np.pi) + rng.normal(0, 3, self.P.shape)
    def test_baseline_standardised(self):
        r = spei(self.P, self.E, self.ys, self.ms, 3)
        sel = (self.ys >= 1991) & (self.ys <= 2020) & (self.ms == 4)
        self.assertLess(abs(np.nanmean(r["spei"][sel])), 0.15)
        self.assertGreater(np.nanstd(r["spei"][sel]), 0.8); self.assertLess(np.nanstd(r["spei"][sel]), 1.2)
    def test_more_pet_means_drier_and_more_rain_wetter(self):
        r = spei(self.P, self.E, self.ys, self.ms, 1); i = len(self.ys) - 3
        E2 = self.E.copy(); E2[i] += 40
        b = spei(self.P, E2, self.ys, self.ms, 1)["spei"][i]; a = r["spei"][i]; ok = np.isfinite(a) & np.isfinite(b)
        self.assertGreater(ok.mean(), 0.9)  # remaining cells are legitimate FIT_FAIL nulls
        self.assertTrue(np.all(b[ok] <= a[ok] + 1e-12))
        P2 = self.P.copy(); P2[i] += 40
        c = spei(P2, self.E, self.ys, self.ms, 1)["spei"][i]; ok = np.isfinite(a) & np.isfinite(c)
        self.assertTrue(np.all(c[ok] >= a[ok] - 1e-12))
    def test_missing_pet_gives_null_not_zero(self):
        E = self.E.copy(); E[100, 0] = np.nan
        r = spei(self.P, E, self.ys, self.ms, 1); self.assertTrue(np.isnan(r["spei"][100, 0]))
    def test_shape_mismatch_rejected(self):
        with self.assertRaises(ValueError): spei(self.P, self.E[:-1], self.ys, self.ms, 1)
    def test_constant_demand_balance_fails_safely(self):
        P = np.full((len(self.ys), 1), 30.0); E = np.full_like(P, 20.0)
        r = spei(P, E, self.ys, self.ms, 1)
        self.assertTrue(np.all(np.isnan(r["spei"]))); self.assertTrue(np.all(r["flags"] & QF.FIT_FAIL))

class TestEvents(unittest.TestCase):
    x = [0, -1.2, -1.5, 0.2, -1.1, -0.5, -2.0, np.nan, -1.3]
    ys = [2000] * 9; ms = list(range(1, 10))
    def test_no_pooling(self):
        ev = detect_events(self.x, self.ys, self.ms)
        self.assertEqual(len(ev), 4)
        self.assertEqual(ev[0]["onset"], (2000, 2)); self.assertEqual(ev[0]["termination"], (2000, 3))
        self.assertEqual(ev[0]["duration_months"], 2); self.assertAlmostEqual(ev[0]["severity_index_months"], 0.7)
        self.assertAlmostEqual(ev[0]["peak_intensity"], -1.5)
        self.assertAlmostEqual(ev[2]["severity_index_months"], 1.0)
        self.assertAlmostEqual(ev[3]["severity_index_months"], 0.3)
    def test_gap_pooling_never_bridges_missing(self):
        ev = detect_events(self.x, self.ys, self.ms, gap_pool=1)
        self.assertEqual(len(ev), 2)
        self.assertEqual(ev[0]["duration_months"], 6); self.assertEqual(ev[0]["below_threshold_months"], 4)
        self.assertAlmostEqual(ev[0]["severity_index_months"], 1.8)
        self.assertEqual(ev[1]["onset"], (2000, 9))
    def test_min_duration(self):
        ev = detect_events(self.x, self.ys, self.ms, min_duration=2); self.assertEqual(len(ev), 1)
    def test_threshold_is_inclusive(self):
        ev = detect_events([-1.0, 0.0], [2000, 2000], [1, 2]); self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0]["severity_index_months"], 0.0)

if __name__ == "__main__":
    unittest.main(verbosity=2)
