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

### Determinism rules (measured 2026-10-01, see evidence/promptcache-ubatch-drift.jsonl)

- **Pin `cache_prompt` for any same-prompt byte comparison** — the flag itself
  perturbs the greedy trajectory (deterministically: 331 vs 584 bytes on the same
  prompt, reproduced across independent serve sessions), even when the whole
  prompt is re-prefilled either way.
- **Cached prefix-resumption is bit-neutral**: a growing conversation continued
  with `cache_prompt:true` produces byte-identical output to a fresh full prefill
  of the same prompt — AG-Bench agent-loop noise from prompt-cache reuse is
  cleared on this stack. (Amended late 2026-10-01: stable per pair, but repeated
  cached re-requests on drafted E4B show ~1/6 flips across suites — 5/6 vs the
  fresh class's 6/6.)
- **Ubatch is a retired non-issue**: 128/512/2048 produce identical greedy bytes
  (TensorFold's MLX prefill-grid concern does not transfer to the CUDA build).
- **⚠️ Server-side `--temperature 0 --seed 42` is an ANTI-PIN on upstream-docker
  servers** (b1118 measured): it destroys same-prompt reproducibility (0/6 with
  the flags vs 6/6 without, all configs, serial included — outputs differ at
  style level). The bonsai2 FORK honors the same flags byte-exactly. Upstream
  benches must pin at REQUEST level (temp 0, consistent cache_prompt) and pass
  NO server temperature/seed flags. The 2026-10-01 upstream "pinned" rows
  (E4B d3, A3B×2, Xing official) are valid samples but NOT greedy-deterministic
  references — see evidence/e4b-selfrepro-attribution.jsonl.
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

### 48 GB RAM era (2026-09-27): context, not reasoning, was the family limit

| Model | Config | Pass | Headline |
|---|---|---|---|
| **Qwen3.5-35B-A3B** | ctx 32K · 2400 MT/s · threads 6 · ub 4096 | **5/6** — ties the Qwen 9B for #1 | **React passes for the first time in the family history** (742 s / 60 calls); js 819→63 s across three configs; TS remains the lone family failure (fast-exit). Also: the 2400 four-DIMM retrain passed the full previous-crash gauntlet (bench + 31K fill + concurrent 25 GB download, zero MCE/reboots) |

## AG-Bench v2 scoring (2026-09-28) — retroactive, no re-runs

Response to the ledger's own critique: pass-count alone ignores time-to-complete,
and 6 tasks is a thin sample. v2 adds two computed-over-existing-results columns
(both derivable from the same rows, so every historical result stays comparable):

- **Total wall** — sum of wall_s across the whole suite, failed tasks counted
  at their cap. "Time to complete the suite, made explicit."
- **Efficiency** — passes per hour of suite wall. Normalizes for decode class:
  slow-smart and fast-slob each get one honest number.

Retro-v2 table (best run per model per the original-6):

| Model | Pass | Total wall | Efficiency |
|---|---|---|---|
| qwen35-9b-mtp | 5/6 | **8.5 min** | 35.2 pass/h |
| qwen35-35b-a3b @32K/2400 | 5/6 | 20.6 min | 14.6 pass/h |
| qwen35-4b-mtp | 4/6 | 6.1 min | **39.5 pass/h** |
| bonsai2-ptq10-d2 | 4/6 | 6.2 min | 38.8 pass/h |
| ternary-bonsai2-27b (d1 era) | 4/6 | 6.7 min | 35.8 pass/h |
| swift-bonsai2-katana | 4/6 | 7.5 min | 32.2 pass/h |
| mimo-9b-distill | 4/6 | 14.8 min | 16.2 pass/h |
| thinkingcap-27b-q2k (8K profile) | 4/6 | 33.6–37.5 min | ~6.4 pass/h |
| qwen38-27b-dt-iq2s | 4/6 | 42.4 min | 5.7 pass/h |
| a3b @ub4096 (8K era) | 4/6 | 64.8 min | 3.7 pass/h |
| gemma4-e4b-qat-mtp | 3/6 | **2.6 min** | **69.7 pass/h** (fails fastest) |
| gemma12b-qat-mtp | 3/6 | 13.3 min | 13.6 pass/h |
| xing4 @ub4096 | 3/6 | 16.3 min | 11.1 pass/h |
| swift15-27b-iq2xs | 3/6 | 40.1 min | 4.5 pass/h |
| a3b first run (16GB era) | 3/6 | 81.7 min | 2.2 pass/h |
| minicpm5-2b-dspark | 2/6 | 2.4 min | 50.3 pass/h(?— tiny set bias) |

Readings: the 9B completes the full suite in less time than the A3B spends on
TWO tasks — total-wall makes the "co-leader" relationship honest (same score,
2.4x the time). The 4B is the efficiency king among 4-passers. Gemma-E4B is
the fastest per anything but caps early. The 48 GB/32K era quadrupled A3B
efficiency (2.2 → 14.6) — the single largest config-driven efficiency gain in
the ledger.

### Task-set expansion (v2.1, in progress)

Six new task classes to double sample breadth, staged as task7–12:
7. **long-context agent task** — a requirement buried deep in a repo's docs
   must be found AND applied (the class the 6-task set never measures; the
   A3B@32K's differentiator)
8. multi-file refactor (API rename across modules)
9. failing-test triage ("make it green, don't touch tests")
10. git-workflow (bisect-style: revert the offending change, fix forward)
11. API-integration against a local mock server
12. config/library migration (e.g. eslint flat-config)
CHALLENGE (unscored): ancient-puzzle — demoted 2026-09-28 (owner call):
the canary itself needed 10.5 min; every current-fleet candidate would
flat-line at cap. Stays in-repo as a milestone marker; scored v2.1 suite
is the 6 originals + tasks 7-11 = 11 scored tasks.

Scoring for v2.1 runs: the same three columns over 12 tasks; original-6 subset
reported alongside for continuity with every historical row.

## Canary calibration run (2026-09-28): strong-model passability confirmed 6/6

Full 6-task v2.1 suite solved by GLM-5.3 subagents, one per task, with
oracle-blind rules (no tests/ reads, no service-source reads), judged only
by verify.sh from the parent session:

| # | Task | Verdict | Solve time | Notes |
|---|---|---|---|---|
| 7 | long-context-agent | ✅ ALL OK | 77 s | found the ADR-0014.md file titled ADR-0042 — the positioning-vs-naming trap resolved correctly |
| 8 | tb-broken-python | ✅ ALL OK | 40 s | root cause + intended repair (ensurepip) + self-imposed install round-trip |
| 9 | tb-analyze-access-logs | ✅ ALL OK | 16 s | GT match, zero ambiguity |
| 10 | tb-bank-trans-filter | ✅ ALL OK | 33 s | 9-row GT cluster incl. account-typo row; decoy companies rejected |
| 11 | tb-assign-seats | ✅ ALL OK | 77 s | matched the port-time brute-force CSP result exactly |
| 12 | tb-ancient-puzzle | ✅ ALL OK | ~10.5 min | FULL decode chain (glyph filter → weight-sum 819 → AES zip passcode 00819 → ECHOES-OF-CYPRESS → service); decryptor isolation held; agent derived the passcode via PBKDF2 verification bytes when 7z wasn't installed — genuine puzzle-solving under constraint |

Protected-paths integrity held on all six. Interpretation: the suite is a
calibrated measurement instrument — any candidate model score is a real
capability measurement, not a harness artifact. Reference frame: the canary
operates with full-frontier compute and no token budget; the 8 GB fleet
works at 5-90 tok/s under fixed caps, so cross-class comparisons are honest
apples-to-oranges, never apples-to-harness-bugs.

### Tier-1 v2.1 sweep (2026-09-28): the new-suite leaderboard

Final board on the 11-task canary-verified suite:

| Model | Pass | Total wall | Efficiency |
|---|---|---|---|
| **Qwen3.5-9B d4** | **9/11** | **14.2 min** | **37.9 pass/h** |
| Qwen3.5-4B d4 | 8/11 | 15.8 min | 30.3 pass/h |
| **Qwen3.5-35B-A3B @32K** (Q3_K_M) | 8/11 | 21.0 min | 22.9 pass/h |
| **Qwen3.5-35B-A3B @32K** (IQ2_XXS) | 8/11 | 37.1 min | 12.9 pass/h |
| Bonsai-2 d2 | 5/11 | 10.1 min | 29.7 pass/h |

Readings: the 4B ties the 35B-A3B on score at half the wall — the raw-
capability class compresses. IQ2_XXS holds the same 8/11 as Q3_K_M on
IQ2_XXS with +11% decode / +24% prefill and becomes the recommended pack.
The A3B's long-context differentiator (task7) is matched by all three 32K+
models (9B/A3B/4B) — it is the 8K ceiling of the fast tier (Bonsai) and
the React/TS class that separates them, not deep retrieval alone.

### Pinned-era rows (2026-10-01, temp0/seed42 + drift pins — new baseline rows, not deltas vs unpinned)

| Model | Pass | Total wall | Efficiency | Notes |
|---|---|---|---|---|
| **A3B IQ2_XXS @32K** | **9/11** | 2176 s | 14.9 p/h | fleet-best tie; fails {task5, task8}; task9 flip + React pass vs 09-28 row |
| A3B IQ2_XXS + `--cache-ram 32G` | 8/11 | 1657 s | — | −24% wall, −1 score (task9 fast-exit flip) → not adopted |
| **Gemma-E4B d3** | **7/11** | 270 s | **93.3 p/h** | new card efficiency record; identical pass set to d2 |
| **Bonsai-8K lookup-prompt,draft-mtp d2** | **7/11** (6-7 band) | 582 s | 43.4 p/h | 5/11 unpinned era → task8 passed in both lookup runs; task7/11 runs flip (tool-side variance) |
| Xing4 official IQ4_NL | 4/11 | 1925 s | — | mHC-on-SM75 first-try record (0.933 code acc); task8 pass; long-grind style; community pack stays recommended |

Run-order variance warning (measured today): same-config 5-task vs 11-task
runs flipped task7 and task11 — the bench has tool-side nondeterminism
beyond serve pins; single-run ±1 is the floor of certainty.

### Drift-pinned 5-task baseline (1.3, fresh 2026-10-01)

The v2.1-subset (tasks 7–11) baselines with drift status stamped, per the
TensorFold recommendation — recorded on the recipes as-served before any
exactness work lands. Task-subset scores extracted from the v2.1 runs
(TASK_RE filter now built into the runner):

| Model (v2.1 era) | t7 | t8 | t9 | t10 | t11 | Drift status (survey + today) |
|---|---|---|---|---|---|---|
| MiMo-9B (serial-era row) | P | f | P | P | P | drifted with DFlash drafter; serial reproducible |
| Qwen3.5-9B | P | f | P | P | P | drafted 1/6 byte-identical; serial reproducible |
| Qwen3.5-4B | P | f | P | P | P | drafted 3/6 |
| A3B IQ2_XXS @32K | P | f | P | P | P | not yet drift-tested |
| A3B IQ3_XXS @32K | P | f | f | P | P | not yet drift-tested |
| Bonsai-2 d2 (unpinned 09-28) | f | f | P | f | P | **6/6 byte-exact with BATCH_INVARIANT** (re-confirmed 10-01) |
| Bonsai-64K | P | f | P | P | P | same fork+env → exact-class |
| Xing-29B @ub4096 | P | f | P | P | P | not yet drift-tested (Tier 2 item) |
| Gemma-E4B d2 | P | f | f | P | P | **non-self-reproducible drafted (4/6)** — treat single-run scores ±noise |

Fresh hard reference (2026-10-01, temp0/seed42 + `GGML_CUDA_BATCH_INVARIANT=1`,
cap 600): **bonsai2-d2-driftpin-5t: 2/5** (task8 56 s, task9 28 s) — with the
pinning-flip caveat: pinned ≠ unpinned row (task11→fail, task7→fail, task8→pass
vs the 2026-09-28 unpinned run) — a pinned run is its own baseline row. Drill
rules: models marked "not yet Drift-tested" that sit near a task boundary
should re-run marginal tasks before trusting pass/fail; E4B single-run scores
are ±noise by construction.
Task8 (tb-broken-python) fails across the entire 8 GB fleet while strong
models solve it in ≤40 s — it is the suite's capability discriminator, like
React/TS for the original 6.

### Results-ledger reconciliation (2026-10-01)

Every batch in `results/` accounted for, or explicitly marked invalid:

- `qwen25-coder-7b-q4km-20260925-010549.jsonl` — **INVALID, no leaderboard
  row by design.** The server never left its not-ready window (pre-/slots-gate
  era): all 6 tasks failed in 1–43 s with 0 tool calls. The batch measures the
  503 window, not the model. Qwen2.5-Coder-7B has never had a real AG-Bench row;
  the /slots readiness gate (added 2026-09-25) prevents this batch class.
- `qwen35-35b-a3b-mtp-20260925-194626.jsonl` — this IS the "a3b first run
  (16GB era)" row of the retro-v2 table (3/6, walls sum 4899 s = 81.7 min,
  2.2 pass/h): a complete 6-task run, not a partial. The 2026-09-25 A3B section
  and the "js 819→63 s across three configs" note both reference it. Listed
  here to break the label-swap trap: the `-mtp` suffix is the label, the run
  is the section's Q3_K_M d4 experts-on-CPU first attempt.
