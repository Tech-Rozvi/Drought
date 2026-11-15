"""Drought-event detection by run theory on a monthly index series (one cell or area mean).

Event = run of consecutive valid months with index <= threshold (default -1.0), at least
min_duration months. Optional gap pooling: two runs separated by at most `gap_pool` valid months
above the threshold are merged (default 0 = off). A missing (NaN) month never belongs to an event
and never bridges a gap. Severity S = sum(max(0, u - I_t)) in index-months. Duration counts every
month from onset to termination inclusive (pooled gap months included); below_threshold_months
counts only months <= threshold. Frequency is NOT a return period.
"""
import numpy as np

def detect_events(index, years, months, threshold=-1.0, min_duration=1, gap_pool=0):
    x = np.asarray(index, float); n = len(x)
    below = np.isfinite(x) & (x <= threshold)
    runs = []; i = 0
    while i < n:
        if below[i]:
            j = i
            while j + 1 < n and below[j + 1]:
                j += 1
            runs.append([i, j]); i = j + 1
        else:
            i += 1
    merged = []
    for r in runs:
        if merged and gap_pool > 0:
            gap = slice(merged[-1][1] + 1, r[0])
            gseg = x[gap]
            if 0 < len(gseg) <= gap_pool and np.all(np.isfinite(gseg)):
                merged[-1][1] = r[1]; continue
        merged.append(list(r))
    events = []
    for a, b in merged:
        seg = x[a:b + 1]; fin = np.isfinite(seg)
        nb = int(np.sum(fin & (seg <= threshold)))
        if nb < min_duration:
            continue
        events.append(dict(
            event_id=len(events) + 1,
            onset=(int(years[a]), int(months[a])), termination=(int(years[b]), int(months[b])),
            duration_months=int(b - a + 1), below_threshold_months=nb,
            peak_intensity=float(np.nanmin(seg)),
            severity_index_months=float(np.sum(np.maximum(0.0, threshold - seg[fin]))),
            data_completeness=float(fin.mean()),
            quality="DATA_OK" if fin.all() else "MISSING_DATA"))
    return events
