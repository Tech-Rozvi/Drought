"""Crop parameter registry. NO values are shipped: every parameter must be supplied with a citation.
Kc values, stage fractions and depletion fraction must come from FAO-56 (Tables 11, 12, 22) or a
cited regional source; the engine refuses to run with missing or uncited parameters."""
import json
from dataclasses import dataclass

class ParameterError(ValueError):
    pass

REQUIRED = ("kc_ini", "kc_mid", "kc_end", "stage_fractions", "depletion_p", "source")

@dataclass(frozen=True)
class CropParams:
    crop: str
    kc_ini: float
    kc_mid: float
    kc_end: float
    stage_fractions: tuple        # (initial, development, mid, late), sums to 1
    depletion_p: float
    source: str                   # citation: table, edition, page
    def validate(self):
        if not self.source or not str(self.source).strip():
            raise ParameterError("crop parameters must carry a citation (CROP_PARAMETERS_UNCITED)")
        for k in ("kc_ini", "kc_mid", "kc_end"):
            if not (0.0 < getattr(self, k) < 2.0):
                raise ParameterError(f"{k} out of range")
        if not (0.0 < self.depletion_p < 1.0):
            raise ParameterError("depletion_p must be in (0,1)")
        f = self.stage_fractions
        if len(f) != 4 or any(x <= 0 for x in f) or abs(sum(f) - 1.0) > 1e-6:
            raise ParameterError("stage_fractions must be 4 positive values summing to 1")
        return self

def load_params(path_or_dict, crop):
    d = path_or_dict
    if not isinstance(d, dict):
        with open(path_or_dict) as fh:
            d = json.load(fh)
    block = d.get(crop)
    if not block:
        raise ParameterError(f"no parameter block for crop '{crop}' (blocked: supply cited FAO-56 values)")
    missing = [k for k in REQUIRED if block.get(k) in (None, "", [])]
    if missing:
        raise ParameterError(f"missing parameters for {crop}: {missing} (CROP_PARAMETERS_UNCITED)")
    return CropParams(crop=crop, kc_ini=float(block["kc_ini"]), kc_mid=float(block["kc_mid"]),
                      kc_end=float(block["kc_end"]), stage_fractions=tuple(block["stage_fractions"]),
                      depletion_p=float(block["depletion_p"]), source=str(block["source"])).validate()
