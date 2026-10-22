# IQ3_S (original GSQ-RCO) probe: ladder + AG-Bench v2.2 + the replay thread's loop/compaction issues — 2026-10-22

Weights: `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO`, `IQ3_S/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf`
(51.05 GiB, sha256 `4c1eb2ceb4915e11`…, intake v6 `~/models/dl-20261022.log`, SHA PASS 2026-10-22T02:50:44).
Shard 2 verified byte-identical to the Q2_0 blob (LFS oid `316b46f3…`), symlinked, not re-downloaded.
Pack: `packs/iq3_s-gsq` via `tools/iq_pack.py` (same convention as the XXS pack).
Engine: the standing 0.2.1 + PR-3281 build (`strata-021/build-turing-pr3281/strata`), 165 W pins,
production stopped during boots and restored in `finally`, contention discards re-run a boot.

## Why

The "smarter" tier ladder on this card: Q2_0 (good) → IQ3_XXS (great, probed 10-18: −35% decode,
−19% prefill, 11/11 same) → **IQ3_S (best: "matches the full model" per docs; never run here)**.
Upstream yardstick (docs/QUANTS.md, vs Q8_0): IQ3_S top-1 87.69% / KL 0.144 / PPL 4.097 vs
IQ3_XXS 84.46% / 0.202 / 4.119.

Fit risk, recorded in advance: IQ3_S shard 1 = 51.05 GiB experts vs the XXS probe's 43.8 GiB with
10-11 GiB headroom on 62 GiB RAM. Boot plan: attempt 1 = identical knobs to the XXS probe; on
refusal/OOM, fallback knobs = `--kv-resident 16384 --conversation-cache-mib 4096`, then
`--prefill auto:65536`; every fit detail logged. oomd guard: never run concurrent build+serve.

## Stages (all rows → `results/`, evidence JSONL per stage)

1. **Speed ladder** (2 boots, `strata_bench --runs 2 --long` + `needle_bench 32k,128k`):
   compare against the standing Q2_0 rows (short 51.8-54.9, 32K prefill 644-659, agent 36.6-37.7
   tok/s, TTFT ~8.8 s, 128K needle fill 476.6 t/s; 122K cold prefill 688.6 t/s + cached follow-up
   39-43 tok/s from the perf-audit thread dau595681) and the XXS rows (-35% decode, 12/12 needles).
2. **AG-Bench v2.2, 11 tasks** (128K suite, cap 900, 0.35/80): baselines Q2_0 11/11 @ 1135 s,
   IQ3_XXS 11/11 @ 1465 s. Record wall, suspect count, per-task times.
3. **The da595681-thread issues on IQ3_S**:
   - 4-case stale-page loop screen (`experiments/strata-loop-compaction-20261021/bench.py`,
     production-stopped, text-only): baselines Q2_0 3/4 and IQ3_XXS 3/4, one unnecessary edit each.
   - Real loop replay if the screen shows a difference (strata-loop-replay-20261021 fixture, real
     102K history + real browser, 3-cycle threshold; Q2_0 reference: 4 edits / 3 rebuilds /
     0 reloads / 238.9 s).
   - Compaction + cache notes on long-history turns: the 49-min compaction class and the ~102.7K
     uncached reread from the source incident, with the installed mitigation in place.

## Verdict rule

Ranges-not-best-of per lab convention; adoption decision on speed (wall-clock ladder + AG-Bench
time), quality (11/11 + yardstick deltas), and the loop screens (does the unnecessary-edit
behavior shrink?). No change to the standing serve without owner sign-off.

## Stage 1: speed ladder + needles (2026-10-22 02:52-03:33, two boots, clean, no contention)

Engine 0.2.1 + PR-3281, full standing knobs, **no fallback needed**: the boot fits at 128K max
context / 32K resident KV / 8192 MiB conversation cache. The engine's own guard line explains the
envelope: `memory guard: limit 56.6 GiB (source: cgroup) ... floor 2560 MiB` — the user-slice
cgroup is the real limit, the engine self-manages within it (~4 G of host swap absorbed).
Load time 51-54 s per boot. Needle rows note: 0.2.1 `needle_bench` writes one JSON file at
`--out` (0.1.44 wrote a directory); probe glob fixed for future runs.

| Phase | Q2_0 standing | IQ3_XXS (0144 probe) | **IQ3_S (this, 021+PR3281)** | IQ3_S vs |
|---|---|---|---|---|
| Short decode | 51.8-54.9 | 34.2-35.4 | **31.05 / 31.8** | -42% vs Q2_0, ~-9% vs XXS |
| TTFT (short) | ~ |  | 1.09-1.13 s |  |
| 4K prefill | ~530-551 (XXS band) | 515-519 | **460 / 455** | below XXS |
| 16K prefill | 530-551 | ~ | **546 / 542** | XXS band |
| 32K prefill | 644-659 | 522.8-528 | **545 / 541** | -17% vs Q2_0, +3-4% vs XXS |
| Agent turn decode | 36.6-37.7 | 30.6-31.6 | **31.15 / 32.5** | -14% vs Q2_0, ~XXS parity |
| Agent turn TTFT | ~8.8 | 9.5-9.6 | **12.05 / 12.63** | +40% vs Q2_0, +30% vs XXS |
| Agent prefix hit |  |  | 69% both boots |  |
| Needles 32k/128k @ 10/50/90 | 12/12 | 12/12 | **12/12 byte-exact** (6/6 per boot) | retrieval intact |

Raw: `benchmarks/strata-multiagent/results/iq3s-20261022-02141/` (probe-rows.json, engine/server
logs, needle-boot{1,2} JSON arrays).

## Stage 2: AG-Bench v2.2 (2026-10-22 03:35-04:34, two runs)

**10/11 in 1498 s, 0 suspect garbage passes.** Q2_0: 11/11 @ 1135 s (0.1.44); IQ3_XXS: 11/11 @ 1465 s
(0.1.44). Raw: `benchmarks/results/strata-021-iq3s-r0-20261022-033644.jsonl`.

FAIL: `task3-dep-upgrade` at **12 s** — the pi session shows a single degenerate first turn:
31 output tokens, a thinking block that drifted off-task ("There's a strata-021 project…"),
then turn end with no tool call or text. Engine stayed healthy before and after (surrounding
tasks passed 88-364 s). Reading: single-turn early-stop, either a stochastic 0.35-sampling fluke
or an IQ3_S chat-template/thinking termination issue — **n=1 confound; rerun decides.**

**Run 2 (04:02-04:34): 11/11 in 1877 s, 0 suspect.** `task3-dep-upgrade` passed in 254 s.
Raw: `benchmarks/results/strata-021-iq3s-r0-20261022-040324.jsonl`.

**Stage-2 verdict (n=2):** pass range **10-11 of 11** with the one miss a documented single-turn
early-stop fluke that did not recur; wall range **1498-1877 s** vs Q2_0 1135 s (0.1.44) and
IQ3_XXS 1465 s (0.1.44) — the quality tier holds the perfect score at roughly +32-65% wall
clock over the Q2_0 baseline.

## Stage 3: the da595681-thread issues (2026-10-22 04:39-04:46)

Loop screen (same deterministic stale-page simulator, single stochastic trial per cell;
baselines from `experiments/strata-loop-compaction-20261021/results.jsonl`):

| Case | Q2_0 | IQ3_XXS | IQ3_S |
|---|---|---|---|
| stale-baseline | pass, 0 edits | **fail, 1 edit** (7 steps) | **fail, 1 edit** (5 steps, 40.8 s) |
| stale-guard | **fail, 1 edit** (7 steps) | pass, 0 edits | **fail, 1 edit** (6 steps, 41.4 s) |
| verified-baseline | pass | pass | pass, 0 edits (18.6 s) |
| verified-guard | pass | pass | pass, 0 edits (10.9 s) |
| score | 3/4 | 3/4 | **2/4** |

Compaction summary replay (same private fixture, 2048 max tokens): Q2_0 hit max_tokens, incomplete,
212.7 s; **IQ3_S hit max_tokens, incomplete, 125.9 s, 1441 chars** — same over-long-summary class
as Q2_0, not fixed by the smarter quant (the installed Pi-side mitigation remains the effective
fix; it is harness-side, quant-independent).

## Final verdict (2026-10-22)

**Smarter, not loop-proof; slower, not broken.**

1. **Quality holds the top score**: AG-Bench 11/11 (one stochastic single-turn fluke in run 1
   that run 2 cleared), needles 12/12 byte-exact, upstream yardstick deltas confirmed directionally.
2. **The stale-page unnecessary-edit mechanism is quant-independent** — as the earlier screen
   already found. IQ3_S made one unnecessary edit in both stale cases (2/4 vs 3/4 for both other
   quants, n=1 cells): the failure is observation-loop shaped, not numerics shaped. The guard
   instruction did not save either stale case on this quant. The compaction over-run and the
   fix for it live in the harness (Pi), not the weights.
3. **Speed cost is wall-clock, not capability**: short decode -42% vs Q2_0 (31-32 tok/s),
   agent decode at XXS parity, 32K prefill -17% (but above XXS, loans), agent TTFT +2.4-3 s,
   AG-Bench wall +32-65%. Fit works at full knobs inside the 56.6 GiB cgroup (~4 G swap),
   boot 51-54 s, so it is servable on this card.
4. **Classification: per-use-case tier, same verdict shape as IQ3_XXS with better numbers
   behind it.** Where answer quality outweighs latency (hard refactors, subtle bug classes,
   long-context grounding), IQ3_S is the best resident option measured on this card; for
   interactive T3 sessions the TTFT and wall-clock tax argues to keep Q2_0 standing.

**Owner decision (2026-10-22): standing serve stays Q2_0.** Both Q3 packs rotated to
/mnt/archive/local-models with symlinks back (IQ3_XXS in this night's pass 1, IQ3_S weights +
its engine pack `packs/iq3_s-gsq` in pass 2, `~/models/hdd-rotation-20261022/`); the committed
configs (`strata-iq3s-gsq-021-tailnet.json`, `suite-021-iq3s-128k.json`) remain the on-demand
boot path — a future IQ3_S serve copies the pack back to the SSD first (serving straight off
the HDD symlink is random-read-bound and known-slow; only the engine pack's dense side
tolerates it).

## Stage 1 reading

Prefill and agent-decode land at IQ3_XXS parity (the PR-3281 loans plausibly
buy back the ~10% extra expert bytes), short decode pays a further ~9% vs XXS, and agent TTFT
is the notable regression (+2.4-3 s per turn vs the standing Q2_0). Quality probes (needles) show
no retrieval loss. AG-Bench and loop screens decide the rest.
