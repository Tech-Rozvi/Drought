"""Interpretation classes. SPI/SPEI/RDI_st use the standard McKee et al. (1993) classes. Classes for
other indicators (WRSI, PDSI) must be adopted from a cited source and added here; none are invented."""
import math
def spi_class(v):
    if v is None or (isinstance(v, float) and math.isnan(v)): return None
    if v >= 2.0: return "extremely wet"
    if v >= 1.5: return "very wet"
    if v >= 1.0: return "moderately wet"
    if v > -1.0: return "near normal"
    if v > -1.5: return "moderately dry"
    if v > -2.0: return "severely dry"
    return "extremely dry"
