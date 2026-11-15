import unittest
import numpy as np
from rozvi_layer2.wrsi import bucket_daily, wrsi, wrsi_by_stage

class TestWRSI(unittest.TestCase):
    def run_bucket(self, rain, s0=1.0, taw=100.0, n=120):
        P = np.full((n, 1), rain); E = np.full((n, 1), 5.0); K = np.full((n, 1), 1.0)
        return bucket_daily(P, E, K, np.array([taw]), np.array([0.5]), s0), P
    def test_mass_balance_closes(self):
        rng = np.random.default_rng(1); P = rng.gamma(0.3, 12, (150, 4)); E = np.full((150, 4), 5.0); K = np.full((150, 4), 1.1)
        r = bucket_daily(P, E, K, np.full(4, 120.0), np.full(4, 0.55), 0.6)
        dS = r["storage"][-1] - r["initial_storage"]
        resid = dS - (P.sum(0) - r["eta"].sum(0) - r["drainage"].sum(0))
        self.assertTrue(np.allclose(resid, 0, atol=1e-8))
        self.assertTrue(np.all(r["storage"] >= -1e-9) and np.all(r["storage"] <= 120.0 + 1e-9))
        self.assertTrue(np.all(r["eta"] <= r["etc"] + 1e-12)); self.assertTrue(np.all((r["ks"] >= 0) & (r["ks"] <= 1)))
    def test_ample_rain_gives_wrsi_100_and_drought_lowers_it(self):
        wet, _ = self.run_bucket(8.0); dry, _ = self.run_bucket(0.0); mid, _ = self.run_bucket(2.5)
        self.assertAlmostEqual(float(wrsi(wet["eta"], wet["etc"])[0]), 100.0)
        w_dry = float(wrsi(dry["eta"], dry["etc"])[0]); w_mid = float(wrsi(mid["eta"], mid["etc"])[0])
        self.assertLess(w_dry, w_mid); self.assertLess(w_mid, 100.0); self.assertGreater(w_dry, 0.0)
    def test_less_initial_water_means_lower_wrsi(self):
        a, _ = self.run_bucket(0.0, s0=1.0); b, _ = self.run_bucket(0.0, s0=0.3)
        self.assertGreater(float(wrsi(a["eta"], a["etc"])[0]), float(wrsi(b["eta"], b["etc"])[0]))
    def test_missing_rain_never_becomes_zero(self):
        P = np.full((60, 1), 3.0); P[20, 0] = np.nan; E = np.full((60, 1), 5.0); K = np.ones((60, 1))
        r = bucket_daily(P, E, K, np.array([100.0]), np.array([0.5]), 0.8)
        self.assertTrue(np.isnan(r["storage"][20:, 0]).all()); self.assertFalse(np.isnan(r["storage"][:20, 0]).any())
        self.assertTrue(np.isnan(wrsi(r["eta"], r["etc"])[0]))  # incomplete season -> null, not partial
    def test_stage_wrsi_and_validation(self):
        dry, _ = self.run_bucket(0.0, n=60); stages = np.array([0] * 20 + [1] * 20 + [2] * 20)
        st = wrsi_by_stage(dry["eta"], dry["etc"], stages)
        self.assertGreater(float(st[0][0]), float(st[2][0]))   # early stage has stored water; late stage is stressed
        with self.assertRaises(ValueError): bucket_daily(np.ones((3, 1)), np.ones((3, 1)), np.ones((3, 1)), np.array([-1.0]), np.array([0.5]), 1.0)
if __name__ == '__main__':
    unittest.main(verbosity=2)
