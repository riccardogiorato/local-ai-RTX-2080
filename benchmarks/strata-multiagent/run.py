#!/usr/bin/env python3
"""Concurrent coding agents on one Strata server: 1, 2 and 4 agents at once over the same work.

The work is four of the coding-agent sessions of Strata's tools/agent_turns_bench.py (tool calls whose results are the
engine repository's real files), cut where the conversation passes ~45K tokens: 17 turns, ~2K to ~44K tokens of
context. Every arm runs the same four sessions; only how many run at once and how many batch slots the server has
change:

  seq      parallel 1, the four sessions one after the other (the single-agent baseline)
  p2       parallel 2, two sessions at a time (two waves)
  p4       parallel 4, all four at once
  p1x2     parallel 1, two sessions at a time (more agents than slots)

An agent replays its scripted session: request, wait for the full answer, 1 s of simulated tool time, next request
(the next turn's prompt is the scripted history, so the prefix is shared turn to turn as in a real agent). Thinking
off, temperature 0, 256 new tokens max. Each request is streamed; the client measures time to first token and
latency, the engine reports prompt/decode rates and cached tokens.

    python3 run.py --rounds 2 [--arms seq,p2,p4,p1x2]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ENGINE_ROOT = Path("/home/riccardogiorato/Desktop/github/strata-0144")
BASE_CONFIG = REPO / "recipes/strata-configs/strata-q20-gsq-0144-tailnet.json"
PORT = 8080
THINK_S = 1.0
MAX_NEW = 256
# session name -> number of turns kept (context stays under ~45K tokens)
KEEP = {"expert-cache": 5, "tokenizer-fr": 5, "cuda-kernel": 3, "installer-fr": 2}
# name -> (server slots, agents at once, engine arg overrides). 8 GB of VRAM: 2 slots at 128K only fit with a smaller
# VRAM-resident KV window (the engine floors it at 20480 cells), 4 slots only fit at 48K context.
ARMS = {"seq": (1, 1, {}), "p2": (2, 2, {"--kv-resident": "16384"}),
        "p4": (4, 4, {"--kv-resident": "16384", "--max-context": "49152", "--prefill": "auto:49152"}),
        "p1x2": (1, 2, {})}

sys.path.insert(0, str(ENGINE_ROOT / "tools"))
import agent_turns_bench as atb  # noqa: E402
from strata_bench import digest  # noqa: E402


def chat(base: str, key: str, messages: list, max_tokens: int, think: bool = False, tools=None) -> dict:
    """strata_bench.chat, but a tool-call delta counts as the first token (an agent turn is often only a tool call)."""
    body = {"model": "strata", "stream": True, "max_tokens": max_tokens, "temperature": 0, "messages": messages,
            "reasoning_effort": "none", "chat_template_kwargs": {"enable_thinking": False}}
    if tools:
        body["tools"] = tools
    req = urllib.request.Request(base + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    first, text, usage, timings, err, pieces = None, [], None, None, None, 0
    try:
        with urllib.request.urlopen(req, timeout=3600) as r:
            for raw in r:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                d = line[5:].strip()
                if d == "[DONE]":
                    break
                try:
                    j = json.loads(d)
                except ValueError:
                    continue
                if j.get("error"):
                    err = str(j["error"])[:300]
                for ch in j.get("choices") or []:
                    dl = ch.get("delta") or {}
                    piece = (dl.get("content") or "") + (dl.get("reasoning_content") or "")
                    if piece or dl.get("tool_calls"):
                        if first is None:
                            first = time.perf_counter() - t0
                        pieces += 1
                        text.append(dl.get("content") or "")
                if j.get("usage"):
                    usage = j["usage"]
                if j.get("timings"):
                    timings = j["timings"]
    except Exception as e:                              # noqa: BLE001
        err = repr(e)[:300]
    return {"first": first, "total": time.perf_counter() - t0, "text": "".join(text), "usage": usage,
            "timings": timings, "err": err, "pieces": pieces}


def sessions() -> list[tuple[str, list[list[dict]]]]:
    by = {}
    for tag, msgs in atb.turns():
        name, i = tag.rsplit(".", 1)
        if name in KEEP and int(i) < KEEP[name]:
            by.setdefault(name, []).append(msgs)
    return [(n, by[n]) for n in KEEP]


def busy_cpu() -> str | None:
    # by process name: a shell whose command line merely mentions "ninja" (a tail -f filter) is not a build
    out = subprocess.run(["ps", "-eo", "pid=,comm=,args="], capture_output=True, text=True).stdout
    heavy = {"clang", "clang++", "cc1plus", "cc1", "ninja", "make", "nvcc", "cicc", "ptxas", "cargo", "rustc"}
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        comm, args = parts[1], parts[2]
        if comm in heavy or (comm in ("node", "bun") and ("vite" in args or "next dev" in args)):
            return f"{parts[0]} {args}"
    return None


def wait_quiet(log) -> None:
    quiet_since = None
    while True:
        b = busy_cpu() or (f"load average {os.getloadavg()[0]:.1f}" if os.getloadavg()[0] > 3 else None)
        if b:
            if quiet_since is not None or not getattr(wait_quiet, "said", False):
                log(f"waiting: CPU-heavy process running: {b[:120]}")
                wait_quiet.said = True
            quiet_since = None
        else:
            quiet_since = quiet_since or time.time()
            if time.time() - quiet_since >= 60:
                wait_quiet.said = False
                return
        time.sleep(10)


def gpu_mem() -> int:
    return int(subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                              capture_output=True, text=True).stdout.strip() or 0)


def start_server(slots: int, outdir: Path, label: str, over: dict | None = None):
    cfg = json.loads(BASE_CONFIG.read_text())
    for k, v in (over or {}).items():
        cfg["args"][cfg["args"].index(k) + 1] = v
    cfg["host"] = "127.0.0.1"
    cfg["port"] = PORT
    cfg["log"] = str(outdir / f"{label}.engine.log")
    if slots > 1:
        cfg["parallel"] = slots
    cpath = outdir / f"{label}.config.json"
    cpath.write_text(json.dumps(cfg, indent=2) + "\n")
    srv_log = open(outdir / f"{label}.server.log", "w")
    proc = subprocess.Popen([sys.executable, "-m", "serve.server", "--engine", "strata", "--config", str(cpath),
                             "--host", "127.0.0.1", "--port", str(PORT)], cwd=ENGINE_ROOT, stdout=srv_log,
                            stderr=subprocess.STDOUT, start_new_session=True)
    t0 = time.time()
    while True:
        if proc.poll() is not None:
            raise RuntimeError(f"server exited {proc.returncode}; see {label}.server.log")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=3) as r:
                h = json.load(r)
            if h.get("loaded"):
                break
        except (OSError, ValueError):
            pass
        if time.time() - t0 > 1800:
            raise RuntimeError("server not ready in 30 min")
        time.sleep(3)
    props = {}
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/props", timeout=10) as r:
            props = json.load(r)
    except (OSError, ValueError):
        pass
    return proc, round(time.time() - t0, 1), props


def stop_server(proc) -> None:
    proc.terminate()
    try:
        proc.wait(90)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    for _ in range(60):
        if gpu_mem() < 100:
            break
        time.sleep(3)


def run_agent(base: str, name: str, turns: list[list[dict]], rows: list, lock, arm: str, rnd: int, t_arm: float,
              abort=None):
    for i, msgs in enumerate(turns):
        if abort is not None and abort.is_set():
            return
        t_send = time.time() - t_arm
        r = chat(base, "", msgs, MAX_NEW, think=False, tools=atb.TOOLS)
        d = digest(r)
        d.update(arm=arm, round=rnd, session=name, turn=i, t_send=round(t_send, 2))
        with lock:
            rows.append(d)
        if not d["ok"]:
            return
        time.sleep(THINK_S)


def run_arm(arm: str, rnd: int, work, outdir: Path, out, log) -> dict:
    slots, agents, over = ARMS[arm]
    label = f"{arm}-r{rnd}"
    wait_quiet(log)
    log(f"== {label}: {slots} slot(s), {agents} agent(s) at once; starting server")
    proc, load_s, props = start_server(slots, outdir, label, over)
    log(f"   ready in {load_s} s, total_slots={props.get('total_slots')}, VRAM {gpu_mem()} MiB")
    base = f"http://127.0.0.1:{PORT}"
    try:
        # warm-up, discarded (the same as strata_bench)
        chat(base, "", [{"role": "user", "content": "Say OK."}], 8)
        rows, lock = [], threading.Lock()
        load_samples, stop = [], threading.Event()

        abort, hits = threading.Event(), []

        def sample():
            while not stop.is_set():
                load_samples.append(os.getloadavg()[0])
                b = busy_cpu()
                if b:
                    hits.append(b)
                    abort.set()
                stop.wait(5)
        st = threading.Thread(target=sample, daemon=True)
        st.start()
        t0 = time.time()
        queue = list(work)
        qlock = threading.Lock()

        def worker():
            while True:
                with qlock:
                    if not queue:
                        return
                    name, turns = queue.pop(0)
                run_agent(base, name, turns, rows, lock, arm, rnd, t0, abort)
        th = [threading.Thread(target=worker) for _ in range(agents)]
        for t in th:
            t.start()
        for t in th:
            t.join()
        wall = time.time() - t0
        stop.set()
        if hits:
            log(f"   CONTENDED, discarded and rerun: {hits[0][:120]}")
            return None
        for d in sorted(rows, key=lambda x: x["t_send"]):
            out.write(json.dumps(d) + "\n")
        out.flush()
        bad = [d for d in rows if not d["ok"]]
        summary = {"arm": arm, "round": rnd, "slots": slots, "agents": agents, "overrides": over, "wall_s": round(wall, 1),
                   "requests": len(rows), "errors": len(bad), "load_s": load_s,
                   "generated": sum(d["generated_tokens"] or 0 for d in rows),
                   "loadavg_max": round(max(load_samples), 2) if load_samples else None,
                   "contended": None}
        out.write(json.dumps({"summary": summary}) + "\n")
        out.flush()
        log(f"   done: {len(rows)} requests in {wall:.0f} s, {len(bad)} errors, load max {summary['loadavg_max']}"
            + (f"; first error {bad[0]['err']}" if bad else ""))
        return summary
    finally:
        stop_server(proc)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--arms", default="seq,p2,p4,p1x2")
    ap.add_argument("--out", default=str(HERE / "results"))
    a = ap.parse_args()
    outdir = Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = open(outdir / f"multiagent-{stamp}.jsonl", "w")
    logf = open(outdir / f"multiagent-{stamp}.log", "w")

    def log(s):
        line = f"{time.strftime('%H:%M:%S')} {s}"
        print(line, flush=True)
        logf.write(line + "\n")
        logf.flush()
    work = sessions()
    log("sessions: " + ", ".join(f"{n} ({len(t)} turns)" for n, t in work))
    arms = a.arms.split(",")
    for rnd in range(a.rounds):
        for arm in (arms if rnd % 2 == 0 else arms[::-1]):
            for attempt in range(20):
                if run_arm(arm, rnd, work, outdir, out, log) is not None:
                    break
    log("ALL-DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
