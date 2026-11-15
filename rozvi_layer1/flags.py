"""Quality flags carried into every derived product (bitmask, uint16)."""
from enum import IntFlag

class QF(IntFlag):
    DATA_OK = 1
    MISSING_DATA = 2
    INCOMPLETE_MONTH = 4
    LOW_SAMPLE = 8
    ZERO_INFLATED = 16
    FIT_OK = 32
    FIT_FAIL = 64
    OUT_OF_RANGE = 128
    BASELINE_INCOMPLETE = 256
    PET_UNAVAILABLE = 512
    UNIT_ERROR = 1024
    CALENDAR_ERROR = 2048
    SPATIAL_COVERAGE_INCOMPLETE = 4096
    SOURCE_UNAVAILABLE = 8192
    PROB_CLIPPED = 16384   # probability clipped to documented numerical bounds
    GOF_FAIL = 32768       # goodness-of-fit criterion not met
