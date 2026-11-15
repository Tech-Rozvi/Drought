"""FAO-56 Penman-Monteith reference evapotranspiration (ET0), daily timestep.

Inputs are daily means/totals in the units below. Radiation terms are supplied
as net radiation Rn (ERA5-Land: surface_net_solar + surface_net_thermal, J m-2 -> MJ m-2 d-1).
Not a substitute for any other PET method: this is the FAO-56 grass reference ET0.
All functions are vectorised (numpy) and return NaN where inputs are NaN.
"""
import numpy as np

def svp(t_c):
    """Saturation vapour pressure (kPa) at temperature t_c (degC), FAO-56 Eq.11."""
    return 0.6108 * np.exp(17.27 * t_c / (t_c + 237.3))

def slope_svp(t_c):
    """Slope of saturation vapour pressure curve (kPa/degC), Eq.13."""
    return 4098.0 * svp(t_c) / (t_c + 237.3) ** 2

def psychrometric_constant(p_kpa):
    """gamma (kPa/degC), Eq.8 with lambda = 2.45 MJ/kg."""
    return 0.000665 * p_kpa

def wind_2m(u_z, z=10.0):
    """Wind speed at 2 m from measurement height z, Eq.47."""
    return u_z * 4.87 / np.log(67.8 * z - 5.42)

def ea_from_dewpoint(td_c):
    """Actual vapour pressure (kPa) = saturation vapour pressure at dewpoint, Eq.14."""
    return svp(td_c)

def et0_daily(rn, t_mean_c, u2, es, ea, p_kpa, g=0.0):
    """ET0 (mm/day). rn, g in MJ m-2 d-1; t_mean_c degC; u2 m/s; es, ea, p_kpa kPa. Eq.6.

    NOTE for the ERA5-Land pipeline: es must be the mean of es(Tmax) and es(Tmin) (Eq.12)
    when daily extremes are available (hourly data allow this); using es(Tmean) biases es low.
    """
    delta = slope_svp(t_mean_c)
    gamma = psychrometric_constant(p_kpa)
    num = 0.408 * delta * (rn - g) + gamma * 900.0 / (t_mean_c + 273.0) * u2 * (es - ea)
    den = delta + gamma * (1.0 + 0.34 * u2)
    return num / den
