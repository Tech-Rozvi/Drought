import unittest
import numpy as np
from rozvi_layer1.fao56 import svp, slope_svp, psychrometric_constant, wind_2m, et0_daily

class TestFAO56(unittest.TestCase):
    def test_example18_published_values(self):  # FAO-56 Example 18, Brussels, 6 July
        es = (svp(21.5) + svp(12.3)) / 2
        self.assertAlmostEqual(es, 1.997, delta=0.005)
        self.assertAlmostEqual(float(slope_svp(16.9)), 0.122, delta=0.001)
        p = 101.3 * ((293 - 0.0065 * 100) / 293) ** 5.26
        self.assertAlmostEqual(p, 100.1, delta=0.1)
        self.assertAlmostEqual(float(psychrometric_constant(p)), 0.0666, delta=0.0005)
        et0 = et0_daily(rn=13.28, t_mean_c=16.9, u2=2.078, es=es, ea=1.409, p_kpa=p)
        self.assertAlmostEqual(float(et0), 3.88, delta=0.05)
    def test_wind_2m_factor(self):
        self.assertAlmostEqual(float(wind_2m(1.0, 10.0)), 0.748, delta=0.002)
    def test_nan_propagates(self):
        self.assertTrue(np.isnan(et0_daily(np.nan, 20.0, 2.0, 2.3, 1.2, 90.0)))
    def test_more_net_radiation_more_et0(self):
        self.assertGreater(et0_daily(14.0, 25.0, 2.0, 3.2, 1.5, 90.0), et0_daily(10.0, 25.0, 2.0, 3.2, 1.5, 90.0))
if __name__ == "__main__":
    unittest.main()
