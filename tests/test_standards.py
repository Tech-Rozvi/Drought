import unittest, importlib, copy
from scipy.special import ndtri
from rozvi_standards.registry import load_registry, indicator, load_config_template, required_nulls
from rozvi_standards.classes import spi_class
from rozvi_standards.envelope import validate
from rozvi_layer1.flags import QF

def good():
    return dict(schema_version="1.0.0", model_version="0.1.0-dev", processing_run_id="run-TEST", geometry={"type": "Point", "coordinates": [31.05, -17.83]},
                period={"start": "2020-01", "end": "2020-01"}, indicator="spi_3", units="index", value=-1.2, source_dataset="CHIRPS_V3", dataset_version="3.0",
                baseline={"start": 1991, "end": 2020, "version": "b1"}, spatial_support={"native_resolution_deg": 0.05, "crs": "EPSG:4326"},
                quality_flags=["DATA_OK", "FIT_OK"], uncertainty={"note": "fit n=30"}, validation_status="V2", provenance={"manifest_id": "m-1"}, is_test_vector=False)

class TestStandards(unittest.TestCase):
    def test_registry_integrity(self):
        r = load_registry(); ids = [i["id"] for i in r["indicators"]]; self.assertEqual(len(ids), len(set(ids)))
        for i in r["indicators"]:
            self.assertIn(i["validation_level"], r["validation_levels"]); self.assertTrue(i["units"]); self.assertTrue(i["must_not_be_interpreted_as"])
            if i["status"].startswith("blocked"): self.assertEqual(i["validation_level"], "V0")
    def test_implemented_indicators_resolve_to_code(self):
        for i in load_registry()["indicators"]:
            if i["status"].startswith("implemented"):
                mod, fn = i["implementation"].rsplit(".", 1)
                self.assertTrue(callable(getattr(importlib.import_module(mod), fn)), i["id"])
    def test_spi_range_matches_probability_bounds(self):
        self.assertAlmostEqual(indicator("spi_3")["theoretical_range"][1], float(ndtri(1 - 1e-6)), places=3)
    def test_flag_set_covers_required_names(self):
        need = "DATA_OK MISSING_DATA INCOMPLETE_MONTH LOW_SAMPLE ZERO_INFLATED FIT_OK FIT_FAIL OUT_OF_RANGE BASELINE_INCOMPLETE PET_UNAVAILABLE UNIT_ERROR CALENDAR_ERROR SPATIAL_COVERAGE_INCOMPLETE SOURCE_UNAVAILABLE".split()
        self.assertTrue(set(need) <= {f.name for f in QF})
    def test_spi_classes_and_event_threshold_consistent(self):
        self.assertEqual(spi_class(-1.0), "moderately dry"); self.assertEqual(spi_class(-0.99), "near normal"); self.assertEqual(spi_class(-1.5), "severely dry")
        self.assertEqual(spi_class(-2.0), "extremely dry"); self.assertEqual(spi_class(2.0), "extremely wet"); self.assertIsNone(spi_class(float("nan")))
    def test_config_template_lists_open_decisions(self):
        n = required_nulls(load_config_template())
        for k in ("spi.zero_prob", "layer2.s0_fraction", "layer2.params_file", "layer2.taw_source", "domain.boundary_checksum"): self.assertIn(k, n)
    def test_envelope_valid_and_each_violation_caught(self):
        self.assertEqual(validate(good()), [])
        e = good(); del e["baseline"]; self.assertTrue(validate(e))
        e = good(); e["units"] = "mm"; self.assertTrue(any("units" in x for x in validate(e)))
        e = good(); e["value"] = None; e["quality_flags"] = []; self.assertTrue(validate(e))
        e = good(); e["quality_flags"] = ["FIT_OK"]; self.assertTrue(any("DATA_OK" in x for x in validate(e)))
        e = good(); e["value"] = 9.0; self.assertTrue(any("range" in x for x in validate(e)))
        e = good(); e["is_test_vector"] = True; self.assertTrue(validate(e))
        e = good(); e["validation_status"] = "validated"; self.assertTrue(validate(e))
        e = good(); e["indicator"] = "magic_score"; self.assertTrue(validate(e))
        e = good(); e["indicator"] = "wrsi_season"; e["units"] = "%"; e["value"] = 80.0; e["irrigation_status"] = "unknown"
        self.assertTrue(any("IRRIGATION_UNKNOWN" in x for x in validate(e)))
        e["quality_flags"] = ["DATA_OK", "IRRIGATION_UNKNOWN"]; self.assertEqual(validate(e), [])
if __name__ == "__main__":
    unittest.main(verbosity=2)
