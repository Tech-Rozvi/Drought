"""Output envelope builder/validator (subset of the JSON Schema: required keys, types, enums, nulls).
Use the `jsonschema` package against data/output_envelope.schema.json in production."""
import json, os
from .registry import indicator, D

TYPES = {"string": str, "object": dict, "array": list, "number": (int, float), "null": type(None), "boolean": bool}

def _ok_type(v, t):
    ts = t if isinstance(t, list) else [t]
    if isinstance(v, bool) and "boolean" not in ts: return False
    return any(isinstance(v, TYPES[x]) for x in ts)

def validate(env):
    with open(os.path.join(D, "output_envelope.schema.json")) as fh:
        sch = json.load(fh)
    errs = [f"missing required field: {k}" for k in sch["required"] if k not in env]
    for k, spec in sch["properties"].items():
        if k not in env: continue
        v = env[k]
        if "const" in spec and v != spec["const"]: errs.append(f"{k} must be {spec['const']!r}")
        if "enum" in spec and v not in spec["enum"]: errs.append(f"{k} not in allowed values")
        if "type" in spec and not _ok_type(v, spec["type"]): errs.append(f"{k} has wrong type")
        if isinstance(v, dict) and "required" in spec:
            errs += [f"{k}.{r} missing" for r in spec["required"] if r not in v]
    if errs: return errs
    try: reg = indicator(env["indicator"])
    except KeyError as e: return [str(e)]
    if env["units"] != reg["units"]: errs.append(f"units '{env['units']}' != registry '{reg['units']}'")
    flags = env["quality_flags"]
    if env["value"] is None and not flags: errs.append("null value requires explanatory quality_flags")
    if env["value"] is not None:
        if "DATA_OK" not in flags: errs.append("non-null value requires DATA_OK flag")
        lo, hi = reg["theoretical_range"]
        if (lo is not None and env["value"] < lo - 1e-9) or (hi is not None and env["value"] > hi + 1e-9): errs.append("value outside theoretical range for indicator")
    if reg["layer"] == "L2" and env.get("irrigation_status") in (None, "unknown") and "IRRIGATION_UNKNOWN" not in flags:
        errs.append("Layer 2 output with unknown irrigation must carry IRRIGATION_UNKNOWN")
    return errs
