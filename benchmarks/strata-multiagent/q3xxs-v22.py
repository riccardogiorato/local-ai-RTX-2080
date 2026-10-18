#!/usr/bin/env python3
"""AG-Bench v2.2 one-run verdict for IQ3_XXS, protocol of bench-ab.py's v22 phase.

    python3 q3xxs-v22.py           # boots the suite config (0.35/80, 128K), runs agentic-bench.sh cap 900,
                                    # scores the emitted JSONL, re-runs on contention.
Compare: Q2_0 v2.2 @ cap 900 -> 11/11, 1025 s (0.20/160) / 1135 s (0.35/80), 0.1.44.
"""
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run  # noqa: E402

HERE = Path(__file__).resolve().parent
SUITE = Path("/home/riccardogiorato/Desktop/github/strata-port/suite-0144-q3xxs-128k.json")
AG_BENCH = Path("/home/riccardogiorato/Desktop/github/local-ai-rtx2080/benchmarks/agentic-bench.sh")
LOGF = open(HERE / "results" / f"q3xxs-v22-{time.strftime('%Y%m%d-%H%M%S')}.log", "w")


def log(s):
    line = f"{time.strftime('%H:%M:%S')} {s}"
    print(line, flush=True)
    LOGF.write(line + "\n")
    LOGF.flush()


def watch_loads(stop, seen):
    while not stop.is_set():
        if run.busy_cpu():
            seen.append(run.busy_cpu())
        stop.wait(10)


def run_v22(tag: str, outdir: Path) -> dict | None:
    run.BASE_CONFIG = SUITE
    log(f"== v22 {tag}: boot")
    proc, load_s, props = run.start_server(1, outdir, f"v22-{tag}", None)
    stop, seen = threading.Event(), []
    t = threading.Thread(target=watch_loads, args=(stop, seen), daemon=True)
    t.start()
    label = f"strata-0144-q3xxs-{tag}"
    try:
        r = subprocess.run(["bash", str(AG_BENCH), label, "900"], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        log(f"   agentic-bench failed: {e.stderr[-300:]!r}")
        return None
    finally:
        stop.set()
        run.stop_server(proc)
    if seen:
        log(f"   CONTENDED: {seen[0][:120]}; DISCARDED")
        return None
    rows = [l for l in r.stdout.splitlines() if l.endswith("}") and '"task"' in l]
    recs = [json.loads(l) for l in rows]
    if not recs:
        import glob
        f = sorted(glob.glob(f"/home/riccardogiorato/Desktop/github/local-ai-rtx2080/benchmarks/results/{label}-*.jsonl"))[-1]
        recs = [json.loads(l) for l in open(f)]
    passed, wall, suspect = sum(x["passed"] for x in recs), sum(x["wall_s"] for x in recs), \
        sum(bool(x.get("suspect_garbage_pass")) for x in recs)
    out = {"arm": "iq3_xxs", "tag": tag, "passed": passed, "wall_s": wall, "n": len(recs), "suspect": suspect}
    log(f"   {tag}: {passed}/{len(recs)} in {wall:.0f} s (suspect {suspect})")
    for x in recs:
        if not x["passed"]:
            log(f"      FAIL {x['task']} {x['wall_s']} s")
    (outdir / "v22-summary.json").write_text(json.dumps(out, indent=1) + "\n")
    return out


def main() -> int:
    outdir = HERE / "results" / f"q3xxs-v22-{time.strftime('%Y%m%d-%H%M%S')}"
    outdir.mkdir(parents=True, exist_ok=True)
    while True:
        run.wait_quiet(log)
        r = run_v22("r0", outdir)
        if r is not None:
            return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())