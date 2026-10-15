#!/usr/bin/env python3
"""Flag A/B on the tests we usually report: strata_bench speeds (short, 4/16/32K, agent) and AG-Bench v2.2.

    python3 bench-ab.py            # speed phase (4 boots, ABBA) then v2.2 phase (2 runs)

Speed phase: chat config (128K), boots old flags (--pcie-frac 0.20 --adapt-swaps 160) vs new flags
(0.35/80); each boot runs tools/strata_bench.py --url ... --runs 2 --long (the community-suite
methodology, 32K prompt included) into its own results folder.
v2.2 phase: the 128K suite config (suite-0143-128k.json), same two flag sets, one agentic-bench.sh
run each (cap 900), scored from the emitted JSONL.
Boots a CPU build lands on are discarded and rerun (run.py's guard); mid-suite contamination is
recorded (load samples + builds seen) so the rows can be audited.
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
CHAT = Path("/home/riccardogiorato/Desktop/github/local-ai-rtx2080/recipes/strata-configs/strata-q20-gsq-0144-tailnet.json")
SUITE = Path("/home/riccardogiorato/Desktop/github/strata-port/suite-0143-128k.json")
STRATA_BENCH = Path("/home/riccardogiorato/Desktop/github/strata-0144/tools/strata_bench.py")
AG_BENCH = Path("/home/riccardogiorato/Desktop/github/local-ai-rtx2080/benchmarks/agentic-bench.sh")
ARMS = {"old": {"--pcie-frac": "0.20", "--adapt-swaps": "160"},
        "new": {"--pcie-frac": "0.35", "--adapt-swaps": "80"}}


def watch_loads(stop, seen):
    while not stop.is_set():
        if run.busy_cpu():
            seen.append(run.busy_cpu())
        stop.wait(10)


def run_speed(tag: str, arm: str, outdir: Path, log) -> dict | None:
    run.BASE_CONFIG = CHAT
    log(f"== speed {tag} {arm} {ARMS[arm]}: boot")
    proc, load_s, props = run.start_server(1, outdir, f"speed-{arm}-{tag}", ARMS[arm])
    stop, seen = threading.Event(), []
    t = threading.Thread(target=watch_loads, args=(stop, seen), daemon=True)
    t.start()
    try:
        rdir = outdir / f"speed-{arm}-{tag}"
        subprocess.run([sys.executable, str(STRATA_BENCH), "--url", f"http://127.0.0.1:{run.PORT}",
                         "--runs", "2", "--long", "--out", str(rdir), "--quiet"],
                        check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        log(f"   strata_bench failed: {e.stderr[-200:]!r}")
        return None
    finally:
        stop.set()
        run.stop_server(proc)
    if seen:
        log(f"   CONTENDED during suite: {seen[0][:100]}; DISCARDED")
        return None
    import glob as _glob
    rfile = sorted(_glob.glob(str(rdir / "*" / "results.json")))[-1]
    r = json.loads(Path(rfile).read_text())["results"]
    row = {"arm": arm, "tag": tag,
           "short": r["chat"]["decode_tps"]["median"], "ttft": r["chat"]["ttft_s"]["median"],
           "4k": r["prompts"]["4K"]["prompt_tps"]["median"], "16k": r["prompts"]["16K"]["prompt_tps"]["median"],
           "32k": r["prompts"]["32K"]["prompt_tps"]["median"],
           "agent_ttft": r["agent"]["turn_ttft_s"]["median"], "agent_decode": r["agent"]["turn_decode_tps"]["median"],
           "agent_hit": r["agent"]["hit_pct"]["median"]}
    log(f"   {arm}: short {row['short']} tok/s, 4K {row['4k']:.0f}, 16K {row['16k']:.0f}, 32K {row['32k']:.0f} t/t, "
        f"agent ttft {row['agent_ttft']} s, agent decode {row['agent_decode']} tok/s, hit {row['agent_hit']:.0f}%")
    return row


def run_v22(tag: str, arm: str, outdir: Path, log) -> dict | None:
    run.BASE_CONFIG = SUITE
    log(f"== v2.2 {tag} {arm} {ARMS[arm]}: boot")
    proc, load_s, props = run.start_server(1, outdir, f"v22-{arm}-{tag}", ARMS[arm])
    stop, seen = threading.Event(), []
    t = threading.Thread(target=watch_loads, args=(stop, seen), daemon=True)
    t.start()
    try:
        label = f"strata-0144-flags-{arm}-{tag}"
        r = subprocess.run(["bash", str(AG_BENCH), label, "900"], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        log(f"   agentic-bench failed: {e.stderr[-200:]!r}")
        return None
    finally:
        stop.set()
        run.stop_server(proc)
    rows = [l for l in r.stdout.splitlines() if l.endswith("}") and '"task"' in l]
    recs = [json.loads(l) for l in rows]
    if not recs:
        import glob
        f = sorted(glob.glob(f"/home/riccardogiorato/Desktop/github/local-ai-rtx2080/benchmarks/results/{label}-*.jsonl"))[-1]
        recs = [json.loads(l) for l in open(f)]
    passed, wall, suspect = sum(x["passed"] for x in recs), sum(x["wall_s"] for x in recs), \
        sum(bool(x.get("suspect_garbage_pass")) for x in recs)
    out = {"arm": arm, "tag": tag, "passed": passed, "wall_s": wall, "n": len(recs), "suspect": suspect,
           "contended": bool(seen), "first_contention": (seen[0][:120] if seen else None)}
    log(f"   {arm}: {passed}/{len(recs)} in {wall:.0f} s" + (f"  CONTENDED: {seen[0][:80]}" if seen else ""))
    for x in recs:
        if not x["passed"]:
            log(f"      FAIL {x['task']} {x['wall_s']} s")
    return out


def main() -> int:
    outdir = HERE / "results" / "flags-ab"
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    logf = open(outdir / f"flags-ab-{stamp}.log", "w")

    def log(s):
        line = f"{time.strftime('%H:%M:%S')} {s}"
        print(line, flush=True)
        logf.write(line + "\n")
        logf.flush()
    speed = []
    # speed phase, ABBA: old new | new old
    for rnd, arm in enumerate(("old", "new", "new", "old")):
        while True:
            run.wait_quiet(log)
            r = run_speed(f"r{rnd}", arm, outdir, log)
            if r is not None:
                speed.append(r)
                out = {"speed": speed, "v22": []}
                (outdir / f"flags-ab-{stamp}.json").write_text(json.dumps(out, indent=1) + "\n")
                break
    log("speed phase medians:")
    for arm in ("old", "new"):
        v = [s["short"] for s in speed if s["arm"] == arm]
        k = [s["32k"] for s in speed if s["arm"] == arm]
        log(f"  {arm}: short {v}, 32K prefill {k}")
    # v2.2 phase: one run per arm, old first (established row), then new
    for arm in ("old", "new"):
        while True:
            run.wait_quiet(log)
            r = run_v22(arm, arm, outdir, log)
            if r is not None:
                out["v22"].append(r)
                (outdir / f"flags-ab-{stamp}.json").write_text(json.dumps(out, indent=1) + "\n")
                break
    log("ALL-DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())