# AG-Bench — local-model agentic coding eval (Pi Code harness)

**What this measures** that the capability probes don't: multi-step agent survival —
can the model explore a repo, run a failing test suite, read real output, edit the right
file, and iterate until `verify.sh` passes — inside a real coding-agent harness.

## Harness

- **Pi Coding Agent** (`@earendil-works/pi-coding-agent`, pinned by `pi --version` in each
  result header) — minimal agent with `read`/`write`/`edit`/`bash` tools, headless
  `--mode json --print`, `--no-session` (every run starts clean).
- **Model serving**: llama.cpp server (digest-pinned per recipe) on `127.0.0.1:8080`,
  launched with `--alias local-model`; Pi provider `llamacpp-local` in
  `~/.pi/agent/models.json`. **No fallback model** — if the local model fails, the task fails.
- Same task dirs for every model (rsync copy, deps reinstall on demand), same wall-clock cap
  (default 600 s/task), temperature 0.

## Task set (6, all deterministic verifiers)

| # | Task | Class | Verify |
|---|---|---|---|
| 1 | shopping-cart bugfix (3 seeded bugs) | JS debugging | `node --test` green |
| 2 | PricingTable React component fix to a markup contract | React/markup | SSR render + assertions |
| 3 | date-fns v2→v4 dependency upgrade + API fix | maintainer | installed version ≥4 + tests |
| 4 | metrics.py bugfix (the lab's original distance-function probe, agenticized) | Python | pytest green |
| 5 | inventory.js → inventory.ts strict migration | TS migration | `tsc` clean |
| 6 | pagination helper off-by-one bugs (edge cases) | algorithms | `node --test` green |

TASK.md in each dir is the prompt the agent receives. `verify.sh` is the judge; the agent
may not edit tests/verifiers.

## Metrics recorded (results/*.jsonl)

`model, task, passed, wall_s, tool_calls, finish` — pass rate out of 6 is the headline;
wall_s and tool_calls reveal flailing (many calls, no progress) vs. surgical solves.

## Run

```bash
# 1. serve the model under test with the fixed alias
sudo docker run --gpus all -p 8080:8080 -v <model-dir>:/models:ro -d <digest-pinned image> \
  --model /models/<gguf> --alias local-model <recipe flags>
# 2. run the bench (label = model name used in results)
bash benchmarks/agentic-bench.sh <model-label> [seconds-cap]
```

## Honesty rules

- A task failed by agent-error (crash, refusal, syntax scramble) is a failed task —
  the same judgment a human maintainer would make about the model.
- Ranking by pass rate alone is incomplete: report wall time alongside, and remember
  decode class matters (novel-prose speeds in `prompts/decode-isolation.txt` runs are the
  realistic agent-workload class, not the repetitive best case).
## Results (2026-09-24, RTX 2080 8GB, pi 0.87.1, llama.cpp b11118)

| Model | Pass | Wall s/task (passing) | Failure style |
|---|---|---|---|
| Qwen3.5-9B MTP d4 (32K, registry config) | **5/6** | 14–199 | one flail (220 s React, overrun) |
| ThinkingCap-Qwen3.8-27B Q2_K MTP d2 (8K cram) | **4/6** | 115–295 | flails on the two template-heavy tasks |
| Gemma 4 E4B QAT MTP d2 (8K) | **3/6** | 18–33 | premature stop: narrates fixes, quits mid-task |

Readings:
- Slow-smart wins agent loops more than raw speed: the 27B at ~10 tok/s beats the
  181 tok/s Gemma because it keeps working until verify passes.
- Micro-probe capability (3/3 for all three) does not predict agent survival;
  the split is in loop discipline, per-task iteration and early termination.
- Two zero-byte-silent batches (one Gemma, one ThinkingCap) were pi-side transients
  after container swaps — kept as `INVALID-*` files; the runner now warm-up gates.
- Temperature is NOT pinned by the runner (pi default); one task (Gemma cart)
  flipped pass→fail across runs. Pin it before treating ranks as final.
