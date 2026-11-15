"""Integration tests on REAL files (skipped if absent). Set ROZVI_UPLOADS to the data folder."""
import os, unittest, zipfile, tempfile
import numpy as np
from rozvi_layer1.chirps_io import read_chirps_monthly
from rozvi_layer1.shp import read_polygons, centre_mask, bounds

UP = os.environ.get("ROZVI_UPLOADS", "/mnt/user-data/uploads")
F = {"1981-01": "chirps-v3_0_1981_01.tif", "1982-03": "chirps-v3_0_1982_03.tif", "1983-06": "chirps-v3_0_1983_06.tif"}
GADM = os.path.join(UP, "gadm41_ZWE_shp.zip")

@unittest.skipUnless(all(os.path.exists(os.path.join(UP, f)) for f in F.values()) and os.path.exists(GADM), "real data absent")
class TestRealData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        with zipfile.ZipFile(GADM) as z: z.extract("gadm41_ZWE_0.shp", cls.tmp)
        cls.rings = read_polygons(os.path.join(cls.tmp, "gadm41_ZWE_0.shp"))[0]
        cls.data = {k: read_chirps_monthly(os.path.join(UP, v)) for k, v in F.items()}
    def test_grid_and_nodata_metadata(self):
        for k, (v, g, meta) in self.data.items():
            self.assertEqual(v.shape, (1600, 1500)); self.assertEqual(g.res, 0.05)
            self.assertFalse(meta["nodata_declared_in_file"])      # must be configured, not assumed
            self.assertEqual(meta["nodata_cells"], 1155006)
            self.assertEqual(len(meta["sha256"]), 64)
    def test_boundary_inside_window_and_nodata_free(self):
        v, g, _ = self.data["1981-01"]
        w = bounds(self.rings); rs, cs = g.window(*w); sub = g.subgrid(rs, cs)
        self.assertEqual((rs.stop - rs.start, cs.stop - cs.start), (137, 158))
        m = centre_mask(self.rings, sub.x_centres(), sub.y_centres())
        self.assertAlmostEqual(int(m.sum()), 13380, delta=10)     # independent point-in-polygon count: 13,380
        for k, (v, g, _) in self.data.items():
            block = v[rs, cs]
            self.assertFalse(np.isnan(block[m]).any(), k)         # no missing values inside Zimbabwe
            self.assertGreaterEqual(float(block[m].min()), 0.0)
    def test_rainfall_plausible_and_zero_not_missing(self):
        means = {}
        for k, (v, g, _) in self.data.items():
            rs, cs = g.window(*bounds(self.rings)); sub = g.subgrid(rs, cs)
            m = centre_mask(self.rings, sub.x_centres(), sub.y_centres()); means[k] = float(v[rs, cs][m].mean())
        self.assertGreater(means["1981-01"], 100); self.assertLess(means["1983-06"], 15)
        print("\nZimbabwe (centre-in-polygon) mean monthly rainfall, mm:", {k: round(x, 1) for k, x in means.items()})
if __name__ == "__main__":
    unittest.main(verbosity=2)
