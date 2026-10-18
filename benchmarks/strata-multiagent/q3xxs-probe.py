#!/usr/bin/env python3
"""IQ3_XXS probe-boots vs the standing Q2_0 numbers, same 0.1.44 engine + chat knobs.

    python3 q3xxs-probe.py            # N boots (default 2) of the q3xxs chat config, each:
                                      #   strata_bench --runs 2 --long  (short/4K/16K/32K/agent rows)
                                      #   needle_bench 32k,128k @ depths 10,50,90
Rows land in results/q3xxs-<tag>/ as JSON + JSONL evidence; contention discards and reruns a boot.
Compare against: recipes/flashnext-gsqrc-q20-125b-strata.md (Q2_0 rows on the identical config).
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
Q3CFG = HERE.parents[1] / "recipes/strata-configs/strata-q3xxs-gsq-0144-tailnet.json"
STRATA_BENCH = Path("/home/riccardogiorato/Desktop/github/strata-0144/tools/strata_bench.py")
NEEDLE = Path("/home/riccardogiorato/Desktop/github/strata-0144/tools/needle_bench.py")


def watch_loads(stop, seen):
    while not stop.is_set():
        if run.busy_cpu():
            seen.append(run.busy_cpu())
        stop.wait(10)


def one_boot(tag: str, outdir: Path, log) -> dict | None:
    run.BASE_CONFIG = Q3CFG
    log(f"== q3xxs {tag}: boot")
    proc, load_s, props = run.start_server(1, outdir, f"q3xxs-{tag}", None)
    stop, seen = threading.Event(), []
    t = threading.Thread(target=watch_loads, args=(stop, seen), daemon=True)
    t.start()
    try:
        rdir = outdir / f"speed-{tag}"
        subprocess.run([sys.executable, str(STRATA_BENCH), "--url", f"http://127.0.0.1:{run.PORT}",
                        "--runs", "2", "--long", "--out", str(rdir), "--quiet"],
                       check=True, capture_output=True, text=True)
        ndir = outdir / f"needle-{tag}"
        subprocess.run([sys.executable, str(NEEDLE), "--url", f"http://127.0.0.1:{run.PORT}",
                        "--lengths", "32k,128k", "--depths", "10,50,90", "--out", str(ndir)],
                       check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        log(f"   probe failed: {e.stderr[-300:]!r}")
        return None
    finally:
        stop.set()
        run.stop_server(proc)
    if seen:
        log(f"   CONTENDED during boot: {seen[0][:100]}; DISCARDED")
        return None
    import glob as _glob
    rfile = sorted(_glob.glob(str(rdir / "*" / "results.json")))[-1]
    r = json.loads(Path(rfile).read_text())["results"]
    row = {"boot": tag,
           "short": r["chat"]["decode_tps"]["median"], "ttft": r["chat"]["ttft_s"]["median"],
           "4k": r["prompts"]["4K"]["prompt_tps"]["median"], "16k": r["prompts"]["16K"]["prompt_tps"]["median"],
           "32k": r["prompts"]["32K"]["prompt_tps"]["median"],
           "agent_ttft": r["agent"]["turn_ttft_s"]["median"], "agent_decode": r["agent"]["turn_decode_tps"]["median"],
           "agent_hit": r["agent"]["hit_pct"]["median"]}
    nj = sorted(ndir.glob("*.json"))
    if nj:
        row["needle"] = json.loads(nj[-1].read_text())
    log(f"   {tag}: short {row['short']} tok/s, 4K {row['4k']:.0f}, 16K {row['16k']:.0f}, 32K {row['32k']:.0f} t/t, "
        f"agent ttft {row['agent_ttft']} s, agent decode {row['agent_decode']} tok/s, hit {row['agent_hit']:.0f}%")
    return row


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--boots", type=int, default=2)
    ap.add_argument("--out", default=str(HERE / "results"))
    a = ap.parse_args()
    outdir = Path(a.out) / f"q3xxs-{time.strftime('%Y%m%d-%H%M%S')}"
    outdir.mkdir(parents=True, exist_ok=True)
    logf = open(outdir / "probe.log", "w")

    def log(s):
        line = f"{time.strftime('%H:%M:%S')} {s}"
        print(line, flush=True)
        logf.write(line + "\n")
        logf.flush()

    rows = []
    ev = open(outdir / "evidence.jsonl", "a")
    for b in range(a.boots):
        while True:
            run.wait_quiet(log)
            r = one_boot(f"b{b}", outdir, log)
            if r is not None:
                rows.append(r)
                ev.write(json.dumps(r) + "\n")
                ev.flush()
                break
    log("q3xxs ranges:")
    for k in ("short", "32k", "agent_decode", "agent_ttft"):
        v = [r[k] for r in rows]
        log(f"  {k}: {['%.1f' % x for x in v]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())