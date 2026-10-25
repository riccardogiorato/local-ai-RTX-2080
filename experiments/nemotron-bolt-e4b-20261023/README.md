# Nemotron 3.5 Bolt E4B UD-Q4_K_XL · llama.cpp — first pass (2026-10-23)

> **2026-10-24 follow-up:** the runner now defaults to pinned **b11804**; the
> live serve is 64K / DFlash d4, unchanged UD-Q4_K_XL weights. New measurements:
> 188 tok/s code at 64K; 190 tok/s d4 and 209–211 tok/s d7 at 8K.
> Both tested ngram stacks add no prose speed and slow code; ngram stays off.
> [Full comparison, probes, and rollback command](../bolt-engine-ngram-20261024/README.md).
> The original measurements and 10/11 n=2 agentic result below remain **b11118**
> evidence; the full agentic suite has not been rerun on b11804. AD-Q4_K_M is
> excluded by the owner's request, superseding the optional A/B note below.

Model GA'd today: NVIDIA's GRPO post-train of **Gemma-4-E4B-it** (same skeleton
as `recipes/gemma-4-e4b-qat-llamacpp.md`, the card's 181 tok/s fast-resident slot,
7/11 AG-Bench v2.1). 8B total / 4B effective, Mamba-hybrid, 64K context cap,
OpenMDW-1.1, knowledge cutoff 2026-05.

- Main: `unsloth/NVIDIA-Nemotron-3.5-Bolt-E4B-GGUF` → `NVIDIA-Nemotron-3.5-Bolt-E4B-UD-Q4_K_XL.gguf`
  4,758,125,760 B · sha256 `b19f200ff71cc336…` (verified at intake, `dl-20261023-bolt.sh` v8)
- Drafter: `dflash-NVIDIA-Nemotron-3.5-Bolt-E4B-Q8_0.gguf` 398,892,256 B · sha256 `9a63662ae8395b8b…`
- Engine: llama.cpp pinned `server-cuda12-b11118@sha256:bfb3264f…` (same digest as the
  Gemma QAT recipe). CHECK PASSED (2026-10-23): b11118's llama-server help lists
  `--spec-type …,draft-dflash,draft-dspark,…` — no engine deviation needed.
- Serve: port 8080, `--alias local-model`, key: `run-bolt.sh <stage>` (nodraft |
  dflash-d4 | dflash-d7 | stop; `BOLT_CTX` env, default 8192). Standing Strata
  serve untouched throughout (it was down for the owner's opencode sweep during
  the whole session; Bolt never shared the card with it).

## Measured on this box (2026-10-23, temperature 0, server-reported rates, 2 runs per class)

| Config | Decode (code) | Decode (prose isolation) | Prefill (code, 8K ctx) | VRAM |
|---|---|---|---|---|
| No draft, 8K ctx | **73.2-73.7 tok/s** | 75.6-75.9 tok/s | 2,449-2,535 tok/s | 3,418 MiB |
| DFlash d4, 8K ctx | **157.4-158.2 tok/s** | 75.05-75.48 tok/s | 2,304-2,360 tok/s | 5,022 MiB |
| DFlash d7, 8K ctx | **172.5-173.0 tok/s** | 57.9 tok/s | 2,343-2,354 tok/s | 5,022 MiB |
| DFlash d4, **64K ctx** | (not re-measured; serve of record) | — | — | **5,824 MiB** |

DFlash acceptance (code / prose): d4 **0.99, mean_len 4.92** / 0.24, mean_len 2.0;
d7 **0.982, mean_len 7.76** / 0.155, mean_len 2.09.

**The DFlash d7 claim is verified on the code class**: acceptance 0.982 with mean
accepted length 7.76 means essentially every 7-token draft is fully accepted.
2.35x over no-draft at d7. But the pursuit is code-only: prose-class acceptance
collapses (0.24 / 0.155), making d4 a wash on prose (75.05-75.48 vs 75.6-75.9
no-draft) and d7 a regression (57.9, -23%). Recommended serve depth is a workload
choice: **d4 as default** (zero prose cost, 2.15x code), d7 for pure-code sessions,
no-draft never (nothing is gained).

Cold boot: health at ~62 s (64K d4), first request pays ~50 s CUDA-graph compile
(vs 20-26 s on the Gemma QAT twin).

**64K is the true context ceiling** (model spec: input and output both capped 64K;
this test booted it fully resident with the drafter at 5,824 MiB, ~2.3 GB card
headroom). The twin's 128K does not carry over except if NVIDIA ships a longer-
window revision.

## Pre-registered checks vs outcomes

1. Resident footprint band 3.0-3.6 GB @ 8K: **HIT** (3,418 MiB).
2. No-draft decode band 70-100 tok/s: **HIT**, low side (73.2-75.9; the 4.76 GB
   UD file vs the QAT twin's 4.22 GB costs ~17% decode against Gemma's 88.85).
3. DFlash d4/d7 vs no-draft, thresholds >=1.8x / 1.2-1.8x / <1.2x: **code class
   healthy** (2.15x / 2.35x); prose class <1.2x (d4 wash, d7 negative). The 1.8x+
   read applies to code workloads only.
4. Capability probes (note: the past trains-riddle text was never recorded in-repo,
   so the reasoning probe here is the canonical river-crossing puzzle, verifiable):
   river ON 1500: **PASS** (goat-first, 7 crossings, 1011 tokens); river ON 300:
   budget fail (all 300 tokens reasoning, content empty; same budget class as the
   twin); river OFF: **PASS at 153 tokens** (base Gemma failed its own probe
   thinking-off; no direct comparison across riddles, but the non-thinking path is
   functional here); median exec-verified fix: **PASS on retest** (the model emits
   raw code without a markdown fence; first probe row failed extraction only,
   retest row records both); OpenAI tools + continuation: **PASS** (clean
   getCurrentWeather call, arguments {"city":"Rome"}, continuation correct).
5. AG-Bench v2.2 n=2, prediction band 8-11: **HIT at 10/11, both rounds, identical
   pass sets** — r1 341 s, r2 357 s suite wall. Sole fail task2 both rounds (SSR
   markup contract, deterministic 0/2, math correct both times). Evidence:
   `benchmarks/results/nemotron-bolt-e4b-20261023-scored.jsonl` (r1) and
   `nemotron-bolt-e4b-r2-20261023-scored.jsonl` (r2), each a merged audited set
   (the tasks-1-9 run + the tasks-10-11 rerun; one garbage literal-glob row excluded
   per round, same serve session, sequential in time; the multi-word glob trap is
   now fixed in agentic-bench.sh).

## Verdict

**10/11 v2.2, n=2 at 341/357 s wall with identical pass sets, the fastest suite
wall ever measured on this card** (n confirmed: r2 ran same serve, same settings,
~4 min after r1). About 3.0-3.3x faster than the Swift IQ2_XS standing serve's
11/11 n=2 walls (1051/1123 s); per-task walls 13-87 s. The fleet hypothesis is
confirmed: the GRPO post-train lifts the agentic tier from the base's 7/11 into
the 9-11 band on this exact skeleton, reproducibly. The one miss, task2, is
deterministic (0/2): the correct total (17.50 EUR) rendered as split React text
nodes; SSR `<!-- -->` markers broke the markup contract regex. Math right, markup
contract wrong, both rounds: signature recorded in both scored.jsonl audit rows.

Where it sits in the fleet:

| | Bolt E4B | Gemma 4 E4B QAT (base) | Ternary Bonsai 2 9B | Swift 1.5 FN IQ2_XS (standing) |
|---|---|---|---|---|
| AG-Bench v2.2 | **10/11 @ 341/357 s** (n=2) | 7/11 (v2.1 era) | 11/11 @ 22.8 min | **11/11 @ 1051/1123 s** (n=2) |
| Decode (code) | 157-173 tok/s d4/d7 | 181 tok/s MTP d2 | 115 tok/s | 41-42.5 agent decode |
| Context | 64K resident @ 5.8 GB | 128K @ 5.81 GB | 128K, free 4-slot | 128K serve |
| Class | fast agentic resident | fast thinking chat | perfect-rate 9B | slow-smart reference |

Bolt E4B is the strongest fast-tier candidate tested on this card: near-perfect-
rate agentic at interactive speed, tools-clean, 64K resident in 71% of VRAM.
The n=2 confirmation ran (identical 10/11, pass sets equal) and the task2 retry
question is closed: deterministic SSR-contract miss, not stochastic. Remaining
open item is the Strata gap (recorded Tier 3, NEXT-IDEAS.md): the pack declares
`gemma4`, Strata's importer scope ends at gemma3, so Bolt's 64K window cannot use
Strata's conversation-cache/streamed-KV machinery — and the stress-trio
compaction FAIL stands as an engine-stack limitation row, not a model verdict.

## Wiring added (all additive, no task edits)

- `benchmarks/agentic-bench.sh`: `PI_PROVIDER` env (default `strata`, past
  behavior unchanged) and `TASKS_GLOB` env (space-separated dir globs each ending
  in `/`; default `task*-/`). The trailing-slash-in-var requirement is a bash
  splitting trap documented in the script comment.
- `~/.pi/agent/models.json`: new `llamacpp-local` provider (openai-completions,
  `127.0.0.1:8080/v1`), alongside the standing `strata` entry.
- `probe-bolt.py` (this dir): capability probe harness, evidence rows appended
  to `experiments/evidence/nemotron-bolt-e4b-llamacpp.jsonl`.

## Stress trio (task12-14, same serve, 2026-10-23 23:31)

| Task | Pass | Wall | Tool executions | Note |
|---|---|---|---|---|
| task12 attractor-loop | ✗ | 110 s | 68, **all distinct** (no repeated-call attractor) | scored contract: quality 59.3 < 72 threshold |
| task13 hang-recovery | ✓ | 48 s | 23 | |
| task14 compaction-constraints | ✗ | 251 s | 26 | verify: FAIL tests, large session (~27K jsonl lines) |

Stress row 1/3 n=1 on `nemotron-bolt-e4b-stress12-14-20261023-233119.jsonl` (raw).
Classification: task12's high turn count (69 turns in 110 s) is exploration-heavy but
not a pathological loop — every tool execution was unique. task14 is the compaction
class where Strata's conversation cache does work the raw llama.cpp serve does not;
an honest fail row for this engine stack. These three tasks are the owner's new
stress bench (untracked task dirs, STRESS-TASKS.md), not part of the v2.2 bench of
record; this row exists for the stress comparison table, not the leaderboard.

## Speed-plan campaign (2026-10-24: 4 levers, 1 closed by spec, 1 killed on external evidence, 1 mixed, 1 negative)

| Lever | Result | Rows |
|---|---|---|
| 1. Draft depth beyond 7 | **d7 is the plateau by design.** d10: 168.4-171.9 tok/s, d14: 167.6-172.7 — acceptance 0.982 / mean_len 7.76 IDENTICAL at d7/d10/d14. NVIDIA's tech report (p.12) confirms: the DFlash drafter "drafts seven [tokens]" of an 8-token block, AL ceiling 8. Deeper `--spec-draft-n-max` only adds verification tax. Our "draft-starved" hypothesis falsified; lever closed. | `results-decode-dflash-d10.txt`, `results-decode-dflash-d14.txt` |
| 2. Lighter quant (Q3 class) | **Killed on external evidence without a local run.** AtomicChat's published fidelity table for this exact model: imatrix Q4_K_M 90-91% top-1 (KL ~0.09-0.10), Q3/IQ3 tier collapses to 78-86% top-1 (KL 0.17-0.51), their IQ3_XXS withdrawn at 74.6%. They also flag the model as "unusually sensitive to quantization" (even Q8_0 only ~96% top-1). Bolt's value is its 10/11 agentic reliability; a ~10% decode gain is not worth that trade. | external: AtomicChat repo readme KL table |
| 3. KV cache q8_0 | **Mixed, per-workload toggle.** Code: -2.6% (153.3-153.6 vs 157.4-158.2 f16 baseline); prose: +8-9% (81.65-81.75 vs 75.05-75.48, acceptance 0.297/mean 2.22 vs 0.24/2.0); 64K + drafter resident 5,550 MiB (saves ~274 MiB vs f16's 5,824). Worth it for prose-weight or deep-context serving; skip for code serving. | `results-decode-dflash-d4-kvq8.txt` |
| 4. Prefill ubatch (-ub 1024 / 2048) | **Negative.** -ub 1024: prefill unchanged (2,379 vs 2,449-2,534 baseline, within run noise) and decode unchanged; -ub 2048: **OOM** (4.2 GB compute buffer will not fit beside the 5.0 GB resident serve on 8 GB). The twin's 2.76K prefill is not reachable via ubatch at this footprint. Closed. | `results-decode-dflash-d4-ub1024.txt`; ub2048 crash in chain log |

Tech-report cross-check (companion pages + PDF sec. 8/9): the only real remaining speed paths on
this stack are a newer engine build (official cites b11459/b11808; ours b11118 predates both)
and the untested ngram-stack wildcard for prose; the NVFP4-drafter path in the report is
Blackwell-native (N/A on Turing), and the 1.21x-vs-MTP claim is RTX 5070 / same-quant based —
on this card the comparison is confounded by quant files (twin 4.22 GB QAT vs Bolt 4.76 GB UD)
and does not transfer. AtomicChat's AD-Q4_K_M (5.06 GB, KL 0.0912 vs our UD's 0.0960, their
meas.) is the one marginal file-level alternative; a swap now would confound the settled
n=2 bench row, so it stays an optional A/B. Their table also shows NVIDIA's own official
Q4_K_M as the fidelity outlier (KL 0.2411, top-1 84%) — benchmark-score gains at Q4 in
NVIDIA's report coexist with much worse next-token fidelity per this third-party measurement.

## Evidence

- `results-decode-nodraft.txt`, `results-decode-dflash-d4.txt`,
  `results-decode-dflash-d7.txt` — raw measurement rows (ranges, no best-of)
- `experiments/evidence/nemotron-bolt-e4b-llamacpp.jsonl` — capability probes
- `benchmarks/results/nemotron-bolt-e4b-20261023-231401.jsonl` (raw, tasks 1-9
  + one garbage glob row), `nemotron-bolt-e4b-tasks1011-20261023-232016.jsonl`
  (raw, tasks 10-11), `nemotron-bolt-e4b-20261023-scored.jsonl` (audited merge)
- Intake: `~/models/dl-20261023-bolt.log`

## Status

- [x] Model + drafter downloaded, SHA-verified (intake v8, done 22:29)
- [x] b11118 draft-dflash support check: PASSED
- [x] Serve, footprint, decode + prefill measured (no-draft, d4, d7)
- [x] 64K boot verified with drafter (5,824 MiB)
- [x] Capability probes
- [x] AG-Bench v2.2 n=2: 10/11 both rounds, identical pass sets (341/357 s)
- [x] Stress trio row (1/3, separate from the bench of record)
- [x] Verdict written. TESTED.md row added. Strata `gemma4` gap filed as
      Tier 3 upstream blocker. task2 confirmed deterministic 0/2.
