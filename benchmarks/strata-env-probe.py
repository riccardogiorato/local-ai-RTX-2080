#!/usr/bin/env python3
"""Same-config ABBA release probe; runs one resident engine at a time.

Usage: python benchmarks/strata-release-probe.py CONFIG OLD_EXE NEW_EXE OUTPUT
Requires the existing Strata checkout and tokenizer referenced by CONFIG.
"""
import json
import os
import sys
import threading
import time
from pathlib import Path

cfg_path, output, arms_json = sys.argv[1:]
cfg = json.loads(Path(cfg_path).read_text())
root = Path(cfg["cwd"])
sys.path[:0] = [str(root), str(root / "tools")]
from serve.server import StrataEngine, child_env
from calibrate import chat_ids, close, PROMPTS
import strata_tokenizer as ST

tpath = Path(cfg["tokenizer"])
vocab = json.loads((tpath / "vocab.json").read_text())
toks = [None] * len(vocab)
for token, index in vocab.items():
    toks[index] = token
tok = ST.Tokenizer(toks, (tpath / "merges.txt").read_text().split("\n"),
                   json.loads((tpath / "token_type.json").read_text()))
short = [(f"short-{i}", chat_ids(tok, prompt), 192) for i, prompt in enumerate(PROMPTS)]
filler = "The archive records routine weather observations. The sky was clear and the wind was light.\n"
long_text = ("Remember this exact archive password: violet-harbor-731.\n" + filler * 1800
             + "\nWhat is the archive password? Reply with only the password.")
long_ids = chat_ids(tok, long_text)
stream_text = ("Remember this exact archive password: violet-harbor-731.\n" + filler * 2400
               + "\nState the archive password, then explain how to merge two sorted lists in Python.")
stream_ids = chat_ids(tok, stream_text)

def record(row):
    with Path(output).open("a") as file:
        file.write(json.dumps(row) + "\n")
    print(json.dumps({k: v for k, v in row.items() if k not in ("text", "ids", "info")}), flush=True)

arms = json.loads(arms_json)
for boot, arm_spec in enumerate(arms):
    arm, extra = arm_spec[0], arm_spec[1]
    argmods = arm_spec[2] if len(arm_spec) > 2 else {}
    exe = cfg["exe"]
    run_args = list(cfg["args"])
    for flag, val in argmods.items():
        if flag in run_args: run_args[run_args.index(flag) + 1] = val
        else: run_args += [flag, val]
    env = child_env(cfg)
    env.update(extra)
    started = time.monotonic()
    print(f"Loading boot {boot}: {arm}", flush=True)
    eng = StrataEngine(exe, run_args, cwd=cfg["cwd"],
                       log=str(Path(output).with_suffix(f".boot{boot}.log")), env=env)
    try:
        record({"event": "boot", "boot": boot, "arm": arm, "exe": exe, "env_extra": extra, "arg_mods": argmods,
                "load_s": round(time.monotonic() - started, 2), "info": eng.info})
        # Warm both the weights and adaptive cache before measured short prompts.
        for _, ids, limit in short:
            list(eng.generate(ids, limit, {"temperature": 0}, threading.Event()))
        cases = short + [("long-needle", long_ids, 64)]
        if os.environ.get("STREAM_ONLY"):
            cases = [("streamed-needle-code", stream_ids, 192)]
        for name, ids, limit in cases:
            ts = time.monotonic()
            generated = [t for t in eng.generate(ids, limit, {"temperature": 0}, threading.Event())
                         if t is not None]
            last = dict(eng.last)
            ms = last.get("decode_ms", 0)
            record({"event": "sample", "boot": boot, "arm": arm, "case": name,
                    "input_tokens": len(ids), "wall_s": round(time.monotonic() - ts, 3),
                    "decode_tps": round(len(generated) / (ms / 1000), 3) if ms else None,
                    "text": tok.decode(generated), "ids": generated, "timings": last})
    finally:
        close(eng)
