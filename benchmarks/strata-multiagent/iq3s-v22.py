#!/usr/bin/env python3
"""AG-Bench v2.2 one-run verdict for IQ3_S (original GSQ-RCO), protocol of q3xxs-v22.py.

    python3 iq3s-v22.py           # boots the suite config (0.35/80, 128K, 0.2.1+PR-3281 engine),
                                  # runs agentic-bench.sh cap 900, scores the emitted JSONL.
Compare: Q2_0 v2.2 @ cap 900 -> 11/11 @ 1135 s (0.35/80, 0.1.44); IQ3_XXS 11/11 @ 1465 s (0.1.44).
Engine note: this arm runs the 021+PR-3281 build (the standing serve's engine); Q2_0/XXS v22 rows
were 0.1.44 — wall times carry that caveat, decode-rate continuity was established on the same knobs.
Production (strata-serve.service) is stopped for exclusivity and restored in finally; the boot-retry
with fallback fit knobs matches iq3s-probe.py.
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
SUITE = Path("/home/riccardogiorato/Desktop/github/strata-port/suite-021-iq3s-128k.json")
ENGINE = Path("/home/riccardogiorato/Desktop/github/strata-021")
AG_BENCH = Path("/home/riccardogiorato/Desktop/github/local-ai-rtx2080/benchmarks/agentic-bench.sh")
LOGF = open(HERE / "results" / f"iq3s-v22-{time.strftime('%Y%m%d-%H%M%S')}.log", "w")


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


def run_v22(tag: str, outdir: Path, over=None) -> dict | None:
    run.BASE_CONFIG = SUITE
    run.ENGINE_ROOT = ENGINE
    log(f"== v22 {tag}: boot (over={over or {}})")
    proc, load_s, props = run.start_server(1, outdir, f"v22-{tag}", over)
    stop, seen = threading.Event(), []
    t = threading.Thread(target=watch_loads, args=(stop, seen), daemon=True)
    t.start()
    label = f"strata-021-iq3s-{tag}"
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
    out = {"arm": "iq3_s", "tag": tag, "passed": passed, "wall_s": wall, "n": len(recs), "suspect": suspect}
    log(f"   {tag}: {passed}/{len(recs)} in {wall:.0f} s (suspect {suspect})")
    for x in recs:
        if not x["passed"]:
            log(f"      FAIL {x['task']} {x['wall_s']} s")
    (outdir / "v22-summary.json").write_text(json.dumps(out, indent=1) + "\n")
    return out


def main() -> int:
    outdir = HERE / "results" / f"iq3s-v22-{time.strftime('%Y%m%d-%H%M%S')}"
    outdir.mkdir(parents=True, exist_ok=True)
    stopped = subprocess.run(["systemctl", "--user", "stop", "strata-serve.service"]).returncode == 0
    log(f"production stopped: {stopped}")
    try:
        try:
            r = run_v22("r0", outdir)
        except RuntimeError as e:
            log(f"   boot failed: {e}")
            r = None
        if r is None:
            log("   retry once with fallback fit knobs (kv-resident 16384, pref 65536)")
            # only keys present in the config (the suite config has no conversation-cache flag)
            try:
                r = run_v22("r0-fitfb", outdir,
                            over={"--kv-resident": "16384",
                                  "--prefill": "auto:65536"})
            except RuntimeError as e:
                log(f"   fallback boot failed: {e}")
        return 0 if r is not None else 1
    finally:
        if stopped:
            subprocess.run(["systemctl", "--user", "start", "strata-serve.service"])
            log("production restarted")


if __name__ == "__main__":
    raise SystemExit(main())
