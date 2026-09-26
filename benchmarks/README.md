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

### Final leaderboard (2026-09-24 evening, first round)

| Rank | Model | Pass | Style |
|---|---|---|---|
| 1 | Qwen3.5-9B MTP d4 | **5/6** | methodical iterating |
| 2= | Qwen3.5-4B MTP d4 | 4/6 | fast + solid; best value at ~20 s/task |
| 2= | ThinkingCap-Qwen3.8-27B Q2_K | 4/6 | slow-smart survives the loop |
| 2= | MiMo-V2.6-9B distill | 4/6 | hybrid failure modes |
| 5 | Gemma 4 E4B QAT | 3/6 | fast-tokens, early exits |

Harness resolutions this round: `PI_OFFLINE=1` eliminates pi's startup-network hang
(cancelled two whole batches before its discovery); warm-up gate env-tunable;
`--temperature 0 --seed 42` server-side for the last two runs (first three ran on
pi defaults — noted above). Caveats: thinking mode = pi default for all (models
vary in reasoning verbosity); tool_calls counter still overcounts streaming events.

### Late addition: dense Qwen3.8-27B baseline (2026-09-24 night)

| Model | Pass | Wall s/task (passing) |
|---|---|---|
| Qwen3.8-27B-DT-IQ2_S MTP d2 (8K cram, ngl 48) | **4/6** | 85–620 |

Fails the same two tasks as its ThinkingCap finetune (React contract, TS migration) at
roughly 2× the wall time (4.6–5.3 tok/s vs the finetune's 9.6): the Q2_K-choice finding
from decode tests carries over to agent loops — pick the finetune's Q2_K build, not the
IQ2_S one, when the file class is available. SSD copy of the DT file deleted after the
bench (archive original SHA 993c276e… stands).

### Overnight additions (2026-09-25): Bonsai unparked, legacy retried

| Model | Pass | Wall s/task (passing) |
|---|---|---|
| Ternary-Bonsai-2-27B PTQ1_0+MTP (fork @ 285542d, full offload 8K) | **4/6** | 14–95 |

Ties the 27B family (same React/TS failures) at 5–6× their speed — the "ternary too dumb"
verdict is refuted on this bench.

### Night-final additions (2026-09-25 morning): Swift Bonsai 2 + MiniCPM-DSpark

| Model | Pass | Decode (rep/novel) | Notes |
|---|---|---|---|
| Swift-Bonsai-2-27B Katana MTP (owner-approved; UkisAI reasoning-efficiency finetune) | **4/6** | 57 / 48 tok/s | identical pass-set + failures to vanilla Bonsai-2 — the efficiency finetune costs nothing on this scaffold; walls 17–105 s |
| MiniCPM5-2B + DSpark drafter (d4) | 2/6 | ~60 / 180.5 tok/s | DSpark works: acceptance 0.43–0.71, mean 2.7–3.8; novel-class at 180 tok/s is the fastest tiny-model decode measured here — the Windows-era "DSpark made it slower" inverts on b11118 for novel text |

Infra truth found in the small hours: a draft-context server answers /health during
"Loading model" and 503s completions for 30–60 s — every prior 'wedge' was this window.
The runner now gates on /slots readiness. One batch of results (mislabeled
swift-bonsai2-katana, actually measured MiniCPM due to a port hijack) was re-adopted
under its true name after verification.

### Sprint additions (2026-09-25): Swift1.5-27B + backlog runs

| Model | Pass | Decode | Note |
|---|---|---|---|
| Swift-1.5-27B GSQ-RCO IQ2_XS-mtp (cram ngl 40) | **3/6** | 4.4/4.3 tok/s, acc 0.745 | unique family failure: python task; IQ2_XS-on-CPU is the limiter |
| ThinkingCap Q2K @32K KV-RAM (ngl 41, cap 480) | 4/6 | 7.6/6.0 tok/s (decode) | identical fail set to its 8K profile: family failures are reasoning-style, not context limits |
| ↳ reproduced 2026-09-26 @ngl 38 / cap 600 | **4/6** | same four passes, same two failures (js 600s-cap/27 calls, React ❌, date-fns 600s-cap/43, python 131s, TS ❌, pagination 292s) | double-confirmed. Serving boundary learned: ngl 41 fits at load (7646 MiB) but its agent-context graph recapture can CUDA-OOM when ambient desktop VRAM is high — first attempt crashed after task1 (kept as INVALID); ngl 38 (7236 MiB) survives soak at 12K-token fills. ngl 41 is a morning-config, ngl 38 is the safe default |

### LFM2.5-8B-A1B + DSpark (2026-09-25): speed-record 0/6

| Model | Pass | Decode | Note |
|---|---|---|---|
| LFM2.5-8B-A1B Q4_K_M + DSpark d4 (32K, full offload) | **0/6** | **221/200 tok/s** | record decode AND record-low bench — 3 tasks engaged zero tools |

**Harness hazard (standing):** this batch's task6 run escaped the work dir and edited the
master task source in the repo (git-reverted; nothing committed). The runner now restores
task sources from git before each task. Workdir isolation is NOT enforced by the harness —
treat unseen-final-score runs with one extra `git status` on the repo.

### Gemma-4-12B QAT + MTP head (2026-09-25)

| Model | Pass | Decode | Note |
|---|---|---|---|
| Gemma-4-12B QAT Q4_K_XL + Q4_0 MTP head d2 (ngl 45, 6.70 GB pair) | **3/6** | 29.4 tok/s (acc 0.92) | one-size-up E4B does not fit: even the Q4 head forces 2 layers off GPU; differs from E4B by additionally failing pagination |

### Qwen3.5-35B-A3B experts-on-CPU (2026-09-25): the first 35B on this card

| Model | Pass | Decode | Note |
|---|---|---|---|
| Qwen3.5-35B-A3B UD-Q3_K_M + MTP-ONLY head d4, `--override-tensor exps=CPU` (4.57 GB GPU) | **3/6** (@ cap 900) | 9.3 / 8.5 steady → **1.5 in deep turns** | acc 0.77/0.61 (mean 3.4-4.1); 16GB-RAM handicap vs the recipe's 28-32 GB baseline; becomes the smart-slot champion if this box grows RAM |

### Morning additions (2026-09-26): Xing4.0-29B-A4B + Bonsai-2 d2

| Model | Pass | Decode | Note |
|---|---|---|---|
| Ternary-Bonsai-2-27B PTQ1_0+MTP **@ d2** | **4/6** | 55.3 / 49.1 tok/s (acc 0.74/0.55) | the d-depth A/B's winner; identical pass set to d1 — pure speed upgrade (+13% repetitive) |
| Xing4.0-29B-A4B DYN 3.31 bpw (xing4_0-port fork, experts-on-CPU) | **3/6** | 6.8 / 5.4–6.3 tok/s (acc 0.91/0.73) | 4.0 GB VRAM; **fast-exit failure style** (opposite of A3B's cap-grinding); passes 2–17× faster than A3B's — date-fns in 46 s |

### UBBoost-arc re-runs (2026-09-26): prefill boost flips a task outcome

| Model | Config | Pass | Pass walls | Reading |
|---|---|---|---|---|
| Xing4.0-29B-A4B | -b/-ub 4096 (2.4× prefill) | 3/6 (same) | 477→264 s (−45%) | faster, not smarter; date-fns slower on strategy variance (45 vs 23 calls) |
| **Qwen3.5-35B-A3B** | -b/-ub 4096 (2.4× prefill) | **4/6 (up from 3/6)** | 2199→1254 s (−43%) | **pagination FLIPPED** — first 35B 4/6; freed time-budget bought the first pagination pass |
