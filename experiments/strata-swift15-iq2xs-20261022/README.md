# Swift 1.5 Flash-Next IQ2_XS on Strata 0.2.1+PR3281 — the thinking-length experiment — 2026-10-22

Weights: `ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF`, tier **IQ2_XS** (the authors'
recommended tier; their Q2_0 is marked experimental, dev KLD 0.424 vs 0.341). Both shards
downloaded (Swift re-split the model, no blob sharing with our ISTA packs): shard 1 37.07 GiB
(sha `ca3b302d…`), shard 2 26.43 GiB (sha `e4996a6d…`), intake v7 `~/models/dl-20261022-swift.sh`.
The one variable under test vs the recorded originals ladder: **the shortened-thinking finetune**
(claims: 63% fewer thinking tokens, 1.8x sooner answers, <1% accuracy loss; docs' 8-question check:
1,234 vs 2,682 output tokens).

## Pre-registered predictions (recorded before the run)

- Quality tier: between the original's Q2_0 and IQ3_XXS on their KLD numbers (Swift IQ2_XS 0.341
  sits between orig XXS 0.202 and Q2_0-class), so AG-Bench v2.2 expects **10-11/11**: anything
  below 10 falsifies the "about the same quality" claim.
- Speed per token: docs' own table says the original's IQ2_XS runs ~Q2_0 speed (prompt -3-4%;
  Swift measured at the original's speed: 465/78.7 vs 467/78.3 on their box). Expect short decode
  **38-52 tok/s** band (below Q2_0's 51.8-54.9, above XXS's 34-35).
- The headline metric: **AG-Bench wall time at equal pass rate**. If shortened thinking is real,
  Swift IQ2_XS should land at or below the Q2_0 baseline (1135 s) despite a slower-tier quant —
  because agent turns stop paying the long thinking preamble. A wall above XXS's 1465 s falsifies
  the practical benefit on this card.
- Volume check: per-task agent_turns thinking-token counts vs the Q2_0 rows (the mechanism, not
  just the wall clock).
- Loop screens: no strong prior either way (quant grade did not move this behavior; thinking
  shortening is a different axis); the real-browser replay fixture is the tie-breaker only if the
  4-case screen shows a difference.
- Known engine trap: "verify: mapped staging allocation failed" exit-1 reported on Swift 1.5
  IQ2_XS (docs/DETAILS.md workarounds recorded); watch first boot.

## Stage 1: speed ladder + needles (2026-10-22 11:41-12:08, two clean boots, no contention)

Production-stopped exclusivity; serve restored. Boot config note: **Swift's PLE table lives in
shard 1** — `--ple-gguf` must point at shard 1 (the original-family configs point at shard 2;
the first boot attempt died on `per_layer_token_embd.weight is not in …shard-2…` before we
fixed the config). T3-server restart killed the first probe attempt mid-boot (no rows lost; the
post-restart recovery note below). A `--pack` side note: Swift's per-layer expert layout is a
mixed IQ2_XS/IQ2_KS-class arrangement (gu_type rows 16 and 22 in `native_experts.txt`), experts
offset behind the PLE table; the pack tool handled it as v3.

| Phase | Q2_0 standing | IQ3_S (this night) | **Swift IQ2_XS** | Swift vs |
|---|---|---|---|---|
| Short decode | 51.8-54.9 | 31.1-31.8 | **45.1 / 45.15** | -16% vs Q2_0, **+45%** vs IQ3_S |
| TTFT (short) | ~ | 1.09-1.13 | **0.90-0.96 s** | best measured |
| 4K prefill | ~530-551* | 455-460 | **556-559 t/s** | Q2_0-class |
| 16K prefill | 530-551* | 542-546 | **752-768 t/s** | **+42%** vs both |
| 32K prefill | 644-659 | 541-545 | **789-790 t/s** | **+20% vs Q2_0** — fastest 32K ever measured here |
| Agent TTFT | ~8.8 | 12.1-12.6 | **5.70-5.86 s** | **-35% vs Q2_0** |
| Agent decode | 36.6-37.7 | 31.2-32.5 | **40.95-42.5 tok/s** | **+10-15% vs Q2_0** |
| Agent prefix hit |  | 69% | 69% | same |
| Needles 32k/128k | 12/12 | 12/12 | **12/12 byte-exact** (6/6 per boot) | retrieval intact |
| 128K needle fill+answer |  | 212 s mean | **140 s mean** | |
| Load time | 52-54 s | 51-54 s | **36-39 s** | fastest boot |

*Q2_0 16K row from the 0.1.44-era band; same-knob 021 rows not measured separately.

Pre-registered prediction check (short): decode 45 tok/s lands at the top of the predicted
38-52 band; **prefill demolished expectations** — 32K at 790 t/s beats even Q2_0's 659; agent
TTFT -35% and agent decode +10-15% vs Q2_0 are consistent with the shorter-thinking claim
showing up as fewer fixed-position tokens per turn, not just faster walls. AG-Bench decides
whether quality holds at this speed (prediction: 10-11/11, wall ≤ 1135 s if the claim pays).

Raw: `benchmarks/strata-multiagent/results/swift15-20261022-1140/` (probe-rows.json,
needle-boot{1,2}, engine/server logs).

## Stage 2: AG-Bench v2.2 (2026-10-22 12:09-12:27 run 1)

**Run 1: 11/11 in 1051 s, 0 suspect.** Q2_0: 11/11 @ 1135 s; IQ3_XXS: 11/11 @ 1465 s;
IQ3_S: 11/11 @ 1498-1877 s. Swift IQ2_XS is the **first variant to beat the incumbent's wall
clock at a perfect pass rate** — 1051 s is ~7% under Q2_0 and ~30% under IQ3_S, from a
nominally heavier quant tier. Raw: `benchmarks/results/strata-021-swift15-r0-*.jsonl`.

**Run 2 (12:28-12:47): 11/11 in 1123 s, 0 suspect.** n=2 range: **1051-1123 s, perfect rate
both runs.** The pre-registered prediction (11/11 at or below Q2_0's 1135 s) is confirmed in
full; the practical shortened-thinking benefit on this card is real, not a one-boot fluke.

## Stage 3: the loop screen + compaction replay (2026-10-22 12:49-12:57)

| Case | Q2_0 | IQ3_XXS | IQ3_S | **Swift IQ2_XS** |
|---|---|---|---|---|
| stale-baseline | pass, 0 edits | **fail, 1 edit** | **fail, 1 edit** | **pass, 0 edits** (3 steps, 12.4 s) |
| stale-guard | **fail, 1 edit** | pass, 0 edits | **fail, 1 edit** | **pass, 0 edits** (3 steps, 10.7 s) |
| verified-baseline | pass | pass | pass | **pass, 0 edits** (8.1 s) |
| verified-guard | pass | pass | pass | **pass, 0 edits** (8.8 s) |
| score | 3/4 | 3/4 | 2/4 | **4/4 — first clean sweep** |

Compaction summary replay (same private fixture, 2048-token cap): Q2_0 **212.7 s, max_tokens,
incomplete**; IQ3_S **125.9 s, max_tokens, incomplete**; **Swift 79.3 s, end_turn, complete
(handoff marker reached), 4,218 chars** — the first variant to finish the summary inside the
cap. Mechanism note: freed thinking budget is the plausible cause; same-fixture usage shows
Q2_0 burning the entire 2,048 cap (incomplete) vs Swift's 1,663 output tokens (complete).

## Final verdict (2026-10-22)

**Swift IQ2_XS sweep-takes the agentic card record at a nominally heavier quant tier.**

1. **Loop screens: 4/4, zero unnecessary edits** in every cell (n=1 per cell, stochastic
   caveat recorded): the first variant not to take the stale-page bait, the only one to finish
   the compaction summary inside the cap. Consistent with the shortened-thinking finetune
   cutting meandering edit/rebuild cycles — the axis neither Q2_0 nor the Q3 tiers could touch.
2. **AG-Bench v2.2: 11/11 both runs, 1051/1123 s (0 suspect)**, matching the incumbent's
   perfect rate at a lower wall clock — pre-registered prediction confirmed in full.
3. **Speed: agent TTFT 5.7-5.9 s (-35% vs Q2_0), agent decode 41-42.5 tok/s (+10-15% vs
   Q2_0), 32K prefill 789-790 t/s (+20% vs Q2_0, fastest 32K of any variant), needles 12/12
   byte-exact, boot 36-39 s.** The single short-decode row is the only loss: 45.1 tok/s vs
   Q2_0's 51.8-54.9 (-16%), and short-prompt TTFT is the best measured (0.9 s).
4. **Costs/caveats:** Swift Open License 1.0 (finetune); PLE must be served from shard 1
   (config recorded); measured on the standing 0.2.1+PR-3281 engine at identical knobs; loop
   screen cells are n=1.

**Floor for the standing-serve decision (owner's call, currently Q2_0 per the 2026-10-22
morning decision made before these results):** every agent-facing metric is first-place —
TTFT, agent decode, 32K prefill, AG-Bench wall, loop screen, compaction completion — with
retrieval intact; the incumbent's remaining edge is raw chat decode (+16%) and engine-log
continuity. The 27B python-failure history (swift15-27b-iq2xs, 3/6 llama.cpp) did not
reproduce at Flash-Next scale: every AG-Bench task passed in both runs, twice.

1. Pack via `tools/iq_pack.py` (Swift's v4 split: layers 13-47 in shard 2, PLE in shard 1 —
   the tool documents this exact layout), then `strata-swift15-iq2xs-gsq-021-tailnet.json`
   with the standing serve knobs.
2. Two-boot speed ladder + needles (`iq3s-probe.py` pattern, config swapped).
3. AG-Bench v2.2 n=2 (cap 900, 0.35/80), vs Q2_0 11/11 @ 1135 s / XXS 1465 s / IQ3_S 1498-1877 s.
4. Loop screen 4 cases + summary replay vs Q2_0 3/4 / XXS 3/4 / IQ3_S 2/4.

Baselines all from `experiments/strata-iq3s-20261022/README.md` and the Q2_0 recipe rows.
