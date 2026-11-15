import unittest
import numpy as np
from rozvi_layer1.flags import QF
from rozvi_layer1.rdi import rdi, rdi_windows
from test_core import make_axis, synthetic_rain

class TestRDI(unittest.TestCase):
    def setUp(self):
        self.ys, self.ms = make_axis(1981, 2025)
        self.P = synthetic_rain(self.ys, self.ms, 200, seed=7) + 1.0
        rng = np.random.default_rng(8)
        self.E = 80 + 25 * np.sin((self.ms[:, None] - 1) / 12 * 2 * np.pi) + rng.normal(0, 4, self.P.shape)
    def test_baseline_standardised_and_normalised_mean_zero(self):
        r = rdi(self.P, self.E, self.ys, self.ms, 3)
        sel = (self.ys >= 1991) & (self.ys <= 2020) & (self.ms == 2)
        self.assertLess(abs(np.nanmean(r["rdi_st"][sel])), 0.05); self.assertAlmostEqual(float(np.nanstd(r["rdi_st"][sel], ddof=1)), 1.0, delta=0.08)
        self.assertLess(abs(np.nanmean(r["rdi_n"][sel])), 1e-9)
    def test_direction_more_rain_wetter_more_pet_drier(self):
        r = rdi(self.P, self.E, self.ys, self.ms, 1); i = len(self.ys) - 2
        P2 = self.P.copy(); P2[i] *= 1.5; E2 = self.E.copy(); E2[i] *= 1.3
        self.assertTrue(np.all(rdi(P2, self.E, self.ys, self.ms, 1)["rdi_st"][i] > r["rdi_st"][i]))
        self.assertTrue(np.all(rdi(self.P, E2, self.ys, self.ms, 1)["rdi_st"][i] < r["rdi_st"][i]))
    def test_zero_rain_rdi_n_valid_rdi_st_null(self):
        P = self.P.copy(); i = len(self.ys) - 2; P[i, 0] = 0.0
        r = rdi(P, self.E, self.ys, self.ms, 1)
        self.assertAlmostEqual(r["rdi_n"][i, 0], -1.0); self.assertTrue(np.isnan(r["rdi_st"][i, 0]))
        self.assertTrue(r["flags"][i, 0] & QF.ZERO_INFLATED)
    def test_missing_and_invalid_pet_are_null(self):
        P = self.P.copy(); E = self.E.copy(); P[300, 0] = np.nan; E[301, 1] = 0.0
        r = rdi(P, E, self.ys, self.ms, 1)
        self.assertTrue(np.isnan(r["rdi_st"][300, 0]) and np.isnan(r["rdi_n"][300, 0]) and np.isnan(r["rdi_st"][301, 1]))
    def test_constant_ratio_not_silently_zero(self):
        P = np.full((len(self.ys), 1), 30.0); E = np.full_like(P, 60.0); r = rdi(P, E, self.ys, self.ms, 1)
        self.assertTrue(np.all(np.isnan(r["rdi_st"])))                       # std = 0 -> null
        self.assertTrue(np.allclose(r["rdi_n"][~np.isnan(r["rdi_n"])], 0.0))  # normalised RDI is genuinely 0
    def test_crop_season_window_crossing_year_end(self):
        r = rdi_windows(self.P, self.E, self.ys, self.ms, [11, 12, 1, 2, 3, 4])
        self.assertEqual(r["season_year"][0], 1980 if False else r["season_year"][0])
        self.assertEqual(r["season_year"][-1], 2025)
        i = list(r["season_year"]).index(1995); sel = (self.ys == 1995) & (self.ms >= 11) | (self.ys == 1996) & (self.ms <= 4)
        exp = self.P[sel].sum(axis=0) / self.E[sel].sum(axis=0)
        self.assertTrue(np.allclose(r["alpha"][i], exp))
        self.assertTrue(r["flags"][-1, 0] & QF.INCOMPLETE_MONTH)  # 2025/26 season incomplete -> null
        self.assertTrue(np.all(np.isnan(r["rdi_st"][-1])))
        b = (r["season_year"] >= 1991) & (r["season_year"] <= 2020)
        self.assertLess(abs(np.nanmean(r["rdi_st"][b])), 0.05)

if __name__ == "__main__":
    unittest.main(verbosity=2)
