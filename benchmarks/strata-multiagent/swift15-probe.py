#!/usr/bin/env python3
"""SwiftIQ2XS probe-boots vs the standing Q2_0 rows, same 0.2.1 + PR-3281 engine + chat knobs.

    python3 swift15-probe.py            # N boots (default 2) of the swift15 chat config, each:
                                      #   strata_bench --runs 2 --long  (short/4K/16K/32K/agent rows)
                                      #   needle_bench 32k,128k @ depths 10,50,90
Rows land in results/swift15-<tag>/ as JSON + JSONL evidence; contention discards and reruns a boot.
Production (strata-serve.service) is stopped for GPU/RAM exclusivity and restored in finally.
RAM guard: the boot aborts (and falls back to smaller fit knobs once) if MemAvailable drops
under 2 GiB while loading; oomd guard per lab ops notes.
Compare against: recipes/flashnext-gsqrc-q20-125b-strata.md (Q2_0 rows) and the XXS probe rows.
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
CFG = HERE.parents[1] / "recipes/strata-configs/strata-swift15-iq2xs-gsq-021-tailnet.json"
ENGINE = Path("/home/riccardogiorato/Desktop/github/strata-021")
STRATA_BENCH = ENGINE / "tools/strata_bench.py"
NEEDLE = ENGINE / "tools/needle_bench.py"
FIT_FALLBACK = {"--kv-resident": "16384", "--conversation-cache-mib": "4096"}


def mem_available_gib() -> float:
    with open("/proc/meminfo") as f:
        mi = {l.split(":")[0]: int(l.split()[1]) for l in f}
    return mi["MemAvailable"] / 2**30


def watch_loads(stop, seen, low_ram):
    while not stop.is_set():
        if run.busy_cpu():
            seen.append(run.busy_cpu())
        if mem_available_gib() < 2.0:
            low_ram.append(mem_available_gib())
        stop.wait(10)


def one_boot(tag: str, outdir: Path, log, over=None) -> dict | None:
    run.BASE_CONFIG = CFG
    run.ENGINE_ROOT = ENGINE
    log(f"== swift15 {tag}: boot (mem available {mem_available_gib():.1f} GiB, over={over or {}})")
    proc, load_s, props = run.start_server(1, outdir, f"swift15-{tag}", over)
    stop, seen, low_ram = threading.Event(), [], []
    t = threading.Thread(target=watch_loads, args=(stop, seen, low_ram), daemon=True)
    t.start()
    try:
        if low_ram:
            log(f"   CONTENDED low RAM during boot: {low_ram}; DISCARDED")
            return None
        rdir = outdir / f"speed-{tag}"
        subprocess.run([sys.executable, str(STRATA_BENCH), "--url", f"http://127.0.0.1:{run.PORT}",
                        "--runs", "2", "--long", "--out", str(rdir), "--quiet"],
                       check=True, capture_output=True, text=True)
        ndir = outdir / f"needle-{tag}"
        subprocess.run([sys.executable, str(NEEDLE), "--url", f"http://127.0.0.1:{run.PORT}",
                        "--lengths", "32k,128k", "--depths", "10,50,90", "--out", str(ndir)],
                       check=True, capture_output=True, text=True)
        # 0.2.1 needle_bench writes a single JSON file at --out (an array of rows);
        # 0.1.44 wrote a directory. Accept either.
        if ndir.is_dir():
            ndir = sorted(ndir.glob("*.json"))[-1]
        else:
            ndir = ndir.parent / f"needle-{tag}"
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
           "agent_hit": r["agent"]["hit_pct"]["median"], "load_s": load_s}
    nj = sorted(ndir.glob("*.json"))
    if nj:
        row["needle"] = json.loads(nj[-1].read_text())
    log(f"   {tag}: load {load_s:.0f}s, short {row['short']} tok/s, 4K {row['4k']:.0f}, 16K {row['16k']:.0f}, "
        f"32K {row['32k']:.0f} t/t, agent ttft {row['agent_ttft']} s, agent decode {row['agent_decode']} tok/s, "
        f"hit {row['agent_hit']:.0f}%")
    return row


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--boots", type=int, default=2)
    ap.add_argument("--out", default=str(HERE / "results" / "swift15-20261022-02141"))
    a = ap.parse_args()
    outdir = Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)
    logf = open(outdir / "probe.log", "a")

    def log(msg):
        print(msg)
        logf.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        logf.flush()

    # production exclusivity: stop the systemd serve, restore in finally
    stopped = subprocess.run(["systemctl", "--user", "stop", "strata-serve.service"]).returncode == 0
    log(f"production stopped: {stopped}; port check: "
        f"{subprocess.run(['ss', '-tln'], capture_output=True, text=True).stdout.count(':8080 ')}")
    rows = []
    try:
        for i in range(a.boots):
            tag = f"boot{i + 1}"
            row = None
            try:
                row = one_boot(tag, outdir, log)
            except RuntimeError as e:
                log(f"   boot failed: {e}")
            if row is None and i == 0:
                log("   first boot failed/thrashed: one retry with fallback fit knobs "
                    f"{FIT_FALLBACK} + pref auto:65536")
                try:
                    row = one_boot(tag + "-fitfb", outdir, log,
                                   over=dict(FIT_FALLBACK, **{"--prefill": "auto:65536"}))
                except RuntimeError as e:
                    log(f"   fallback boot also failed: {e}")
            if row:
                rows.append(row)
        if rows:
            (outdir / "probe-rows.json").write_text(json.dumps(rows, indent=2) + "\n")
            log(f"wrote {len(rows)} rows to {outdir}/probe-rows.json")
            return 0
        log("NO ROWS; probe aborted (production restored by finally)")
        return 1
    finally:
        if stopped:
            subprocess.run(["systemctl", "--user", "start", "strata-serve.service"])
            log("production restarted")


if __name__ == "__main__":
    raise SystemExit(main())
