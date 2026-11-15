import json, os
D = os.path.join(os.path.dirname(__file__), "data")
def load_registry():
    with open(os.path.join(D, "indicator_registry.json")) as f: return json.load(f)
def indicator(id):
    for i in load_registry()["indicators"]:
        if i["id"] == id: return i
    raise KeyError(f"indicator '{id}' is not in the registry")
def load_config_template():
    with open(os.path.join(D, "model_config.template.json")) as f: return json.load(f)
def required_nulls(cfg, path=""):
    """Config keys still null: the engine must refuse to run stages that need them."""
    out = []
    for k, v in cfg.items():
        p = f"{path}.{k}" if path else k
        if isinstance(v, dict): out += required_nulls(v, p)
        elif v is None: out.append(p)
    return out
