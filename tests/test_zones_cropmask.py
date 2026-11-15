import os, unittest, zipfile, tempfile, glob
import numpy as np
from rozvi_layer1.shp import read_polygons, centre_mask, bounds
from rozvi_layer1.chirps_io import Grid
from rozvi_layer2.zones import zone_raster, ZONE_CODES
from rozvi_layer2.cropmask import read_bacs_fraction, cell_area_ha

UP = os.environ.get("ROZVI_UPLOADS", "/mnt/user-data/uploads")
RES = os.environ.get("ROZVI_RESEARCH", "/tmp/res/Research ")
AEZ = os.path.join(RES, "aez", "Agro_Ecological_Zones"); BACS = os.path.join(RES, "bacs", "Percent_Maize.tif")
GADM = os.path.join(UP, "gadm41_ZWE_shp.zip")

@unittest.skipUnless(os.path.exists(AEZ + ".shp") and os.path.exists(GADM), "AEZ shapefile or GADM absent")
class TestZones(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.mkdtemp()
        with zipfile.ZipFile(GADM) as z: z.extract("gadm41_ZWE_0.shp", tmp)
        cls.zim = read_polygons(os.path.join(tmp, "gadm41_ZWE_0.shp"))[0]
        g = Grid(-20.0, 40.0, 0.05, 1500, 1600); rs, cs = g.window(*bounds(cls.zim)); sub = g.subgrid(rs, cs)
        cls.sub = sub; cls.xs, cls.ys = sub.x_centres(), sub.y_centres()
        cls.mask = centre_mask(cls.zim, cls.xs, cls.ys)
        cls.zr, cls.cnt = zone_raster(AEZ + ".shp", AEZ + ".dbf", cls.xs, cls.ys)
    def test_seven_zones_present_and_split_V(self):
        present = set(np.unique(self.zr)) - {0, -1}
        self.assertEqual(present, set(ZONE_CODES.values()))
    def test_coverage_of_national_mask(self):
        inside = self.mask; cov = ((self.cnt > 0) & inside).sum() / inside.sum()
        self.assertGreater(cov, 0.998)                                 # 15 of 13,380 boundary cells have no zone polygon
        self.assertEqual(int(((self.cnt == 0) & inside).sum()), 15)    # real, recorded gap: flagged unmapped, never filled
        self.assertEqual(int((self.cnt > 1).sum()), 2)                 # real overlap cells: coded -1
        self.assertEqual(int((self.zr == -1).sum()), 2)
    def test_zone_cell_counts_are_stable(self):
        counts = {k: int((self.zr == v).sum()) for k, v in ZONE_CODES.items()}
        self.assertTrue(all(c > 100 for c in counts.values())); self.assertGreater(counts["Region IV"], counts["Region I"])

@unittest.skipUnless(os.path.exists(AEZ + ".shp") and os.path.exists(BACS) and os.path.exists(GADM), "inputs absent")
class TestMaizeMask(unittest.TestCase):
    def test_bacs_on_zimbabwe_window(self):
        tmp = tempfile.mkdtemp()
        with zipfile.ZipFile(GADM) as z: z.extract("gadm41_ZWE_0.shp", tmp)
        zim = read_polygons(os.path.join(tmp, "gadm41_ZWE_0.shp"))[0]
        w = bounds(zim); frac, sub, ndv = read_bacs_fraction(BACS, *w)
        m = centre_mask(zim, sub.x_centres(), sub.y_centres())
        self.assertEqual(frac.shape, m.shape); self.assertEqual(int(m.sum()), 13380)
        self.assertEqual(int(np.isnan(frac[m]).sum()), 19)       # declared nodata (99) honoured, not zero
        area = (frac * cell_area_ha(sub.y_centres())[:, None])[m]
        total_mha = float(np.nansum(area)) / 1e6
        self.assertAlmostEqual(total_mha, 1.466, delta=0.02)     # GEOGLAM-BACS mapped maize ~1.47 Mha (district map says 3.1 Mha)
        zr, _ = zone_raster(AEZ + ".shp", AEZ + ".dbf", sub.x_centres(), sub.y_centres())
        self.assertGreater(np.nansum(np.where(zr == 5, frac, 0)), np.nansum(np.where(zr == 1, frac, 0)))
if __name__ == "__main__":
    unittest.main(verbosity=2)
