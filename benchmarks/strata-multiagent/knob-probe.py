#!/usr/bin/env python3
"""ABBA short-decode probe of two engine-flag sets (pcie-frac / adapt-swaps) on one engine.

    python3 knob-probe.py  cur:--pcie-frac=0.20,--adapt-swaps=160  cand:--pcie-frac=0.35,--adapt-swaps=80

Same engine and config as the standing chat server; each arm is a full server boot (ABBA, 2 rounds =
8 boots, ~1 h total). Per boot: one warm-up, then 6 short chats (192 new tokens, calibrate's own
prompts, temperature 0, thinking off); the row is the engine-reported decode tok/s, median with range.
Boots that a CPU build (ninja/clang++) lands on are discarded and rerun (run.py's guard).
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run  # noqa: E402  (start_server/stop_server/wait_quiet/chat with the guard built in)


def decode_rows(base: str, n: int) -> list[float]:
    sys.path[:0] = ["/home/riccardogiorato/Desktop/github/strata-0144/tools"]
    from strata_bench import chat
    from calibrate import PROMPTS
    out = []
    for i in range(n):
        for p in PROMPTS:
            r = chat(base, "", [{"role": "user", "content": p}], 192)
            d = r.get("timings") or {}
            if r.get("err") is None and r.get("first") is not None and d.get("predicted_per_second"):
                out.append(d["predicted_per_second"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("arms", nargs="+", help="LABEL:key=value,... (keys are engine flags already in the config)")
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--chats", type=int, default=6, help="per-repetition chat rounds × 3 prompts")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "results"))
    a = ap.parse_args()
    arms = []
    for s in a.arms:
        label, _, kv = s.partition(":")
        arms.append((label, {k.split("=", 1)[0]: k.split("=", 1)[1] for k in kv.split(",") if "=" in k}))
    outdir = Path(a.out)
    tag = time.strftime("%Y%m%d-%H%M%S")
    logf = open(outdir / f"knob-{tag}.log", "w")

    def log(s):
        line = f"{time.strftime('%H:%M:%S')} {s}"
        print(line, flush=True)
        logf.write(line + "\n")
        logf.flush()
    res = {n: [] for n, _ in arms}
    plan = []
    for rnd in range(a.rounds):
        plan += [(rnd, arm) for arm in (arms if rnd % 2 == 0 else arms[::-1])]
    evidence = open(outdir / f"knob-{tag}.jsonl", "w")
    for rnd, (label, over) in plan:
        while True:
            run.wait_quiet(log)
            log(f"== round {rnd} {label} {over}: boot")
            try:
                proc, load_s, props = run.start_server(1, outdir, f"knob-{label}-{tag}-{rnd}-{len(res[label])}", over)
            except Exception as e:                              # noqa: BLE001
                log(f"   boot failed ({e!r}); retrying")
                continue
            try:
                t0 = time.time()
                rows = decode_rows(f"http://127.0.0.1:{run.PORT}", a.chats)
                blo = run.busy_cpu()
                if blo or len(rows) < a.chats * 2:
                    log(f"   CONTENDED ({(blo or 'undersized ' + str(len(rows)))[:100]}): discard")
                    continue
                med = statistics.median(rows)
                res[label].append((med, round(time.time() - t0, 1), load_s))
                evidence.write(json.dumps({"round": rnd, "arm": label, "over": over, "median": med,
                                           "rows": [round(x, 1) for x in rows]}) + "\n")
                evidence.flush()
                log(f"   {label}: decode median {med:.1f} ({min(rows):.1f}-{max(rows):.1f}), n={len(rows)}")
                break
            finally:
                run.stop_server(proc)
    evidence.close()
    first = arms[0][0]
    for label, _ in arms:
        meds = [m for m, _, _ in res[label]]
        if label == first:
            log(f"{label}: medians {['%.1f' % m for m in meds]}")
        else:
            r = [b / a for (a, _, _), (b, _, _) in zip(res[first], res[label])]
            log(f"{label}: medians {['%.1f' % m for m in meds]}  vs {first}: x{statistics.median(r):.3f}"
                f" (x{min(r):.2f} to x{max(r):.2f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())