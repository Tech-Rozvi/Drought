import os, unittest, zipfile, tempfile, csv
import numpy as np
from rozvi_layer2.params import CropParams, ParameterError, load_params
from rozvi_layer2.phenology import kc_curve, stage_lengths
from rozvi_layer2.calendar2 import load_calendar, lookup, sowing_dates, growing_period_range
from rozvi_layer2.flags2 import L2Flag
from rozvi_layer2.season import run_season, run_ensemble, longest_run
from rozvi_layer2.suppression import check_inputs
from rozvi_layer2.weighting import weighted_mean, weighted_fraction_below

# TEST-ONLY parameter values (not agronomic recommendations)
TEST = dict(kc_ini=0.4, kc_mid=1.15, kc_end=0.5, stage_fractions=(0.2, 0.25, 0.3, 0.25), depletion_p=0.55, source="unit-test vector")

class TestParams(unittest.TestCase):
    def test_missing_or_uncited_parameters_block(self):
        with self.assertRaises(ParameterError): load_params({}, "maize")
        bad = dict(TEST); bad["source"] = ""
        with self.assertRaises(ParameterError): load_params({"maize": bad}, "maize")
        bad = dict(TEST); bad["kc_mid"] = None
        with self.assertRaises(ParameterError): load_params({"maize": bad}, "maize")
    def test_valid_and_range_checks(self):
        p = load_params({"maize": TEST}, "maize"); self.assertEqual(p.kc_mid, 1.15)
        bad = dict(TEST); bad["stage_fractions"] = (0.5, 0.5, 0.5, 0.5)
        with self.assertRaises(ParameterError): load_params({"maize": bad}, "maize")

class TestPhenology(unittest.TestCase):
    def test_stage_lengths_sum_exactly(self):
        for gp in (90, 111, 150, 157, 160): self.assertEqual(stage_lengths(gp, TEST["stage_fractions"]).sum(), gp)
    def test_kc_curve_shape(self):
        kc, st = kc_curve(150, TEST["stage_fractions"], 0.4, 1.15, 0.5)
        self.assertEqual(len(kc), 150); self.assertEqual(kc[0], 0.4); self.assertAlmostEqual(kc.max(), 1.15)
        self.assertAlmostEqual(kc[-1], 0.5); self.assertTrue(np.all(np.diff(st) >= 0)); self.assertEqual(set(st), {0, 1, 2, 3})

class TestCalendar(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.rows = load_calendar()
    def test_maize_zone_windows(self):
        r, f = lookup(self.rows, "maize", "Zone IIa"); self.assertEqual(len(r), 1); self.assertEqual(growing_period_range(r[0]), (150, 160))
        r, f = lookup(self.rows, "maize", "III"); self.assertEqual(growing_period_range(r[0]), (120, 140))
    def test_unavailable_zones_do_not_borrow(self):
        for crop, zone in (("maize", "I"), ("tobacco", "I"), ("tobacco", "V"), ("tobacco", "Va")):
            r, f = lookup(self.rows, crop, zone); self.assertEqual(r, []); self.assertEqual(f, [L2Flag.CROP_CALENDAR_UNAVAILABLE])
    def test_legacy_unsplit_V_uses_Va_with_flag(self):
        r, f = lookup(self.rows, "maize", "V"); self.assertEqual(len(r), 1); self.assertIn(L2Flag.ZONE_V_SPLIT_UNKNOWN, f)
    def test_real_aez_names_and_Vb_has_no_calendar(self):
        r, f = lookup(self.rows, "maize", "Region IIa"); self.assertEqual(len(r), 1)
        r, f = lookup(self.rows, "maize", "Region Va"); self.assertEqual(len(r), 1); self.assertNotIn(L2Flag.ZONE_V_SPLIT_UNKNOWN, f)
        r, f = lookup(self.rows, "maize", "Region Vb"); self.assertEqual(r, []); self.assertEqual(f, [L2Flag.CROP_CALENDAR_UNAVAILABLE])
    def test_tobacco_variants(self):
        r, f = lookup(self.rows, "tobacco", "IIa"); self.assertEqual(len(r), 1)
        self.assertEqual((r[0]["sow_start_month"], r[0]["sow_start_day"]), ("9", "1")); self.assertIn(L2Flag.PHENOLOGY_ASSUMED, f)
        r2, f2 = lookup(self.rows, "tobacco", "IIa", tobacco_variant="file"); self.assertEqual(len(r2), 2)
        rs, _ = lookup(self.rows, "tobacco", "IIa", stage="seedbed", tobacco_variant="file"); self.assertTrue(all(x["growing_period_max_days"] == "60" for x in rs))
    def test_sowing_dates_cover_window(self):
        r, _ = lookup(self.rows, "maize", "IIa"); d = sowing_dates(r[0], 2019, 10)
        self.assertEqual(str(d[0]), "2019-11-01"); self.assertEqual(str(d[-1]), "2019-12-15")

def forcing(rain, n_days=500, cells=3):
    dates = np.arange(np.datetime64("2019-06-01"), np.datetime64("2019-06-01") + np.timedelta64(n_days, "D"))
    return dates, np.full((n_days, cells), rain), np.full((n_days, cells), 5.0)

class TestSeason(unittest.TestCase):
    params = CropParams("maize", **TEST).validate()
    taw = np.full(3, 120.0)
    def test_wet_season_wrsi_100_dry_lower(self):
        d, P, E = forcing(15.0); r, f = run_season(d, P, E, "2019-11-15", 140, self.params, self.taw, 1.0)
        self.assertTrue(np.allclose(r["wrsi"], 100.0)); self.assertTrue(np.all(r["stress_days"] == 0))
        d, P, E = forcing(0.0); r, f = run_season(d, P, E, "2019-11-15", 140, self.params, self.taw, 0.5)
        self.assertTrue(np.all(r["wrsi"] < 60)); self.assertTrue(np.all(r["stress_days"] > 50)); self.assertTrue(np.all(r["longest_stress_spell"] > 50))
        self.assertTrue(np.all(r["wrsi_by_stage"][0] > r["wrsi_by_stage"][3]))
    def test_season_crossing_year_end(self):
        d, P, E = forcing(3.0); r, f = run_season(d, P, E, "2019-12-15", 150, self.params, self.taw, 0.8)
        self.assertIsNotNone(r); self.assertEqual(r["gp_days"], 150)
    def test_incomplete_forcing_returns_flag_not_value(self):
        d, P, E = forcing(3.0, n_days=100); r, f = run_season(d, P, E, "2019-11-15", 140, self.params, self.taw, 0.8)
        self.assertIsNone(r); self.assertEqual(f, [L2Flag.FORCING_INCOMPLETE])
    def test_missing_rain_day_gives_null_season(self):
        d, P, E = forcing(3.0); P[200, 1] = np.nan
        r, f = run_season(d, P, E, "2019-11-15", 140, self.params, self.taw, 0.8)
        self.assertTrue(np.isnan(r["wrsi"][1])); self.assertFalse(np.isnan(r["wrsi"][0])); self.assertEqual(r["stress_days"][1], -1)
    def test_ensemble_members_and_spread(self):
        d, P, E = forcing(2.0); sows = [f"2019-11-{x:02d}" for x in (1, 11, 21)] + ["2019-12-01", "2019-12-11"]
        s, m = run_ensemble(d, P, E, sows, (150, 160), self.params, self.taw, 0.7)
        self.assertEqual(s["n_members"], 10); self.assertTrue(np.all(s["wrsi_max"] >= s["wrsi_median"])); self.assertTrue(np.all(s["wrsi_median"] >= s["wrsi_min"]))
        self.assertTrue(np.all(s["wrsi_spread"] >= 0))
    def test_longest_run(self):
        m = np.array([[1], [1], [0], [1], [1], [1], [0]], bool); self.assertEqual(longest_run(m)[0], 3)

class TestSuppression(unittest.TestCase):
    def test_modes(self):
        rows, _ = lookup(load_calendar(), "maize", "IIa")
        ok = check_inputs(rows, True, True, "unknown"); self.assertEqual(ok["mode"], "crop_specific"); self.assertIn(L2Flag.IRRIGATION_UNKNOWN, ok["reasons"])
        self.assertIn("upper bound", ok["label"])
        self.assertEqual(check_inputs([], True, True, "unknown")["mode"], "generic_stress_only")
        self.assertEqual(check_inputs(rows, False, True, "unknown")["mode"], "generic_stress_only")
        self.assertEqual(check_inputs(rows, True, False, "unknown")["mode"], "generic_stress_only")
        self.assertEqual(check_inputs(rows, True, True, "unknown", zone_mapped=False)["mode"], "suppressed")

class TestWeighting(unittest.TestCase):
    def test_invalid_cells_excluded_and_reported(self):
        r = weighted_mean([10, np.nan, 30], [1, 5, 3]); self.assertAlmostEqual(r["mean"], 25.0); self.assertAlmostEqual(r["valid_weight_fraction"], 4 / 9)
        self.assertTrue(np.isnan(weighted_mean([np.nan], [1])["mean"]))
        f = weighted_fraction_below([50, 80, np.nan], [1, 1, 2], 60); self.assertAlmostEqual(f["fraction"], 0.5); self.assertAlmostEqual(f["valid_weight_fraction"], 0.5)

UP = os.environ.get("ROZVI_UPLOADS", "/mnt/user-data/uploads")
@unittest.skipUnless(os.path.exists(os.path.join(UP, "crop_type_stats_province.zip")), "province file absent")
class TestCropAreaFiles(unittest.TestCase):
    def test_province_equals_district_aggregate(self):
        from rozvi_layer1.shp import read_dbf
        tmp = tempfile.mkdtemp()
        with zipfile.ZipFile(os.path.join(UP, "crop_type_stats_province.zip")) as z: z.extractall(tmp)
        with zipfile.ZipFile(os.path.join(UP, "Distrit_level_crop_type_area__Ha_.zip")) as z: z.extractall(tmp)
        prov = read_dbf(os.path.join(tmp, "crop_type_stats_province.dbf")); dist = read_dbf(os.path.join(tmp, "Distrit_level_crop_type_area_(Ha).dbf"))
        for crop in ("MAIZE", "TOBACCO"):
            self.assertAlmostEqual(sum(float(r[crop]) for r in prov), sum(float(r[crop]) for r in dist), delta=5)  # same data, not independent
            for p in prov:
                s = sum(float(r[crop]) for r in dist if r["admin1Name"] == p["admin1Name"])
                self.assertAlmostEqual(s, float(p[crop]), delta=5, msg=(crop, p["admin1Name"]))
if __name__ == "__main__":
    unittest.main(verbosity=2)
