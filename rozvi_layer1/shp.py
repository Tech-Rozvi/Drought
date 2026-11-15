"""Minimal ESRI shapefile polygon reader and cell-centre mask (even-odd rule)."""
import struct
import numpy as np

def read_polygons(path):
    with open(path, "rb") as fh:
        d = fh.read()
    stype, = struct.unpack("<i", d[32:36])
    if stype not in (5, 15, 25):
        raise ValueError(f"not a polygon shapefile (type {stype})")
    pos = 100; out = []
    while pos < len(d):
        _, clen = struct.unpack(">2i", d[pos:pos + 8]); pos += 8
        body = d[pos:pos + clen * 2]; pos += clen * 2
        st, = struct.unpack("<i", body[:4])
        if st == 0:
            out.append([]); continue
        nparts, npts = struct.unpack("<2i", body[36:44])
        parts = list(struct.unpack(f"<{nparts}i", body[44:44 + 4 * nparts])) + [npts]
        pts = np.frombuffer(body, dtype="<f8", count=2 * npts, offset=44 + 4 * nparts).reshape(-1, 2)
        out.append([pts[parts[i]:parts[i + 1]] for i in range(nparts)])
    return out

def centre_mask(rings, xs, ys):
    """True where the cell centre lies inside the polygon (even-odd; holes handled)."""
    x1 = np.concatenate([r[:-1, 0] for r in rings]); y1 = np.concatenate([r[:-1, 1] for r in rings])
    x2 = np.concatenate([r[1:, 0] for r in rings]); y2 = np.concatenate([r[1:, 1] for r in rings])
    mask = np.zeros((len(ys), len(xs)), dtype=bool)
    for j, y in enumerate(ys):
        c = ((y1 <= y) & (y2 > y)) | ((y2 <= y) & (y1 > y))
        if not c.any():
            continue
        xi = np.sort(x1[c] + (y - y1[c]) * (x2[c] - x1[c]) / (y2[c] - y1[c]))
        for a, b in zip(xi[0::2], xi[1::2]):
            mask[j, (xs >= a) & (xs < b)] = True
    return mask

def bounds(rings):
    a = np.concatenate(rings)
    return a[:, 0].min(), a[:, 1].min(), a[:, 0].max(), a[:, 1].max()

def read_dbf(path, encoding="latin1"):
    """Return list of attribute dicts (strings) from a .dbf file."""
    with open(path, "rb") as fh:
        d = fh.read()
    n, hl, rl = struct.unpack("<xxxxIHH", d[:12])
    fields = []; p = 32
    while d[p] != 0x0D:
        fields.append((d[p:p + 11].split(b"\0")[0].decode(), d[p + 16])); p += 32
    out = []
    for i in range(n):
        r = d[hl + i * rl + 1: hl + (i + 1) * rl]; o = 0; row = {}
        for name, ln in fields:
            row[name] = r[o:o + ln].decode(encoding).strip(); o += ln
        out.append(row)
    return out
