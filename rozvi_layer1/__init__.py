"""ROZVI Drought Engine - Layer 1 (climate hazard). Scientific core, numpy/scipy only."""
__version__ = "0.1.0-dev"

from . import spi, spei, rdi, events, monthly, fao56, flags, timeaxis, fitdiag
from .pipeline import run_layer1, run_from_directory, run_from_npz
from .io_raster import load_monthly_stack, load_npz_stack, list_monthly_tifs
