"""Decide whether crop-specific Layer 2 outputs may be produced. Suppress rather than guess."""
from .flags2 import L2Flag

def check_inputs(calendar_rows, params_ok, taw_available, irrigation_status, zone_mapped=True, forcing_complete=True):
    """Returns dict(mode, reasons). mode: 'crop_specific' | 'generic_stress_only' | 'suppressed'.
    irrigation_status is carried as a label; unknown irrigation never blocks the rain-fed upper-bound
    indicator but forces the 'rain-fed potential stress (upper bound if irrigated)' label."""
    reasons = []
    if not zone_mapped:
        return dict(mode="suppressed", reasons=[L2Flag.ZONE_UNMAPPED], label=None)
    if not calendar_rows:
        reasons.append(L2Flag.CROP_CALENDAR_UNAVAILABLE)
    if not params_ok:
        reasons.append(L2Flag.CROP_PARAMETERS_UNCITED)
    if not taw_available:
        reasons.append(L2Flag.SOIL_UNAVAILABLE)
    if not forcing_complete:
        reasons.append(L2Flag.FORCING_INCOMPLETE)
    label = "rain-fed potential stress (upper bound if irrigated)"
    if irrigation_status in (None, "unknown"):
        reasons.append(L2Flag.IRRIGATION_UNKNOWN)
    crop_blockers = {L2Flag.CROP_CALENDAR_UNAVAILABLE, L2Flag.CROP_PARAMETERS_UNCITED,
                     L2Flag.SOIL_UNAVAILABLE, L2Flag.FORCING_INCOMPLETE}
    blocked = [r for r in reasons if r in crop_blockers]
    mode = "crop_specific" if not blocked else "generic_stress_only"
    return dict(mode=mode, reasons=reasons, label=label)
