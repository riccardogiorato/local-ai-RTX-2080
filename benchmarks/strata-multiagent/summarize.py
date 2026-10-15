#!/usr/bin/env python3
"""Per-arm table of a run.py results file: wall for all four sessions, per-turn latency, first token, decode, cache."""
import json
import statistics
import sys
from collections import defaultdict


def rng(v, nd=1):
    v = [x for x in v if x is not None]
    if not v:
        return "n/a"
    return f"{statistics.median(v):.{nd}f} ({min(v):.{nd}f}-{max(v):.{nd}f})"


rows, sums = defaultdict(list), defaultdict(list)
for line in open(sys.argv[1]):
    d = json.loads(line)
    if "summary" in d:
        sums[d["summary"]["arm"]].append(d["summary"])
    else:
        rows[d["arm"]].append(d)

print("| Arm | Slots | Agents at once | Wall, 4 sessions (s) | Turn latency (s) | First token (s) | Decode tok/s | "
      "Cache hit % | Errors | Max load |")
print("|---|---|---|---|---|---|---|---|---|---|")
for arm in ("seq", "p2", "p4", "p1x2"):
    if arm not in sums:
        continue
    r, s = rows[arm], sums[arm]
    ok = [x for x in r if x["ok"]]
    follow = [x for x in ok if x["turn"] > 0]
    hit = sum(x["reused_tokens"] or 0 for x in follow) / max(1, sum(x["prompt_tokens"] or 0 for x in follow)) * 100
    walls = " / ".join(f"{x['wall_s']:.0f}" for x in s)
    print(f"| {arm} | {s[0]['slots']} | {s[0]['agents']} | {walls} | {rng([x['total_s'] for x in ok])} | "
          f"{rng([x['ttft_s'] for x in ok])} | {rng([x['decode_tps'] for x in ok])} | {hit:.0f} | "
          f"{sum(x['errors'] for x in s)} | {max(x['loadavg_max'] or 0 for x in s):.1f} |")
