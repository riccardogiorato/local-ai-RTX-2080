# RTX 2080 Local AI Lab — 25 models tested on one 8 GB Turing card

![GPU](https://img.shields.io/badge/GPU-TU104%20%C2%B7%208%20GB%20%C2%B7%20448%20GB%2Fs-lightgrey) ![models](https://img.shields.io/badge/models_tested-25-blue) ![method](https://img.shields.io/badge/measurements-reproducible-blue) ![recipes](https://img.shields.io/badge/recipes-docker%20digest--pinned-informational)

**What can a 2018 Turing card run today?** For every model we test, this repo records the
exact artifact (repo, revision, SHA-256), the runtime (digest-pinned), the launch settings, the
measured results, raw evidence, and a copy-paste reproduce command. Failures are recorded
with the same care as wins.

**Full test history →** [TESTED.md](TESTED.md) (all 25 models, recipes, and details).
**Untested backlog →** [NEXT-IDEAS.md](NEXT-IDEAS.md).
**AG-Bench v2.1 suite (11 tasks, canary-verified) →** [benchmarks/README.md](benchmarks/README.md).

> Method rules live in [hardware.md](hardware.md). Short version: server-reported rates only,
> ranges over repeated runs (no best-of), speeds compared only on the same prompt file, thinking
> off by default. Treat decode deltas < 15% across prompt classes as noise.

## Top 10 models on this card

Ranked by AG-Bench v2.1 score (11 canary-verified tasks), then by efficiency.

| Rank | Model | Score | p/h | Decode / Prefill | Ctx | V/R GB | Spec |
|---|---|---|---|---|---|---|---|
| 1 | [MiMo-9B](https://huggingface.co/bartowski/MiMo-V2.6-Distill-Qwen-9B-GGUF) | **8–9/11** ⁽¹⁾ | 42.5 | 52 / 1.7K | 32K | 5.5 / 1 | **DFlash d8** ⁽²⁾ |
| 1 | [Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B) | **9/11** | 37.9 | 100 / 1.6K | 64K | 5.5 / 1 | MTP d4 |
| 1 | **Flash-Next GSQ-RCO Coder 125B** ⁽⁷⁾ | **9/11** | 15.7 | 22–27 / 175 | 16K | 4.6 / 31 | Strata MTP d4 ⁽⁷⁾ |
| 1 | **Strata-Q20 Flash-Next 125B** ⁽⁶⁾ | **8–10/11** | 28.4 | **36–41 / 740** | 16K (128K per ctx ladder) | 4.5 / 34 | Strata MTP d6 |
| 3 | [Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B) | **8/11** | 30.3 | 150 / 2.3K | **128K** | 2.6 / 1 | MTP d4 |
| 3 | [A3B IQ2_XXS](https://huggingface.co/Qwen/Qwen3.5-35B-A3B) | **9/11** ⁽⁴⁾ | 14.9 | 40 / 1K | 32K+ | 4.6 / 12 | MTP d4 ext |
| 3 | [Bonsai-64K](https://huggingface.co/sudoingx/Ternary-Bonsai-2-27B-PTQ1_0-MTP-GGUF) | **9/11** ⁽⁵⁾ | 8.5 | 15 / 350 | 64K | 6.0 / 2 | graft d2 + lookup |
| 3 | [Xing-29B](https://huggingface.co/XingChen-AGI/Xing4.0-29B-A4B) | **8/11** | 5.8 | 25 / 346 | 8K | 4.0 / 12 | MTP d2 |
| 7 | [Gemma-E4B](https://huggingface.co/google/gemma-4-E4B-it-qat-q4_0-unquantized) | **7/11** | **93.3** ⁽³⁾ | **181** / 2.8K | **128K** | 4.3 / 1 | MTP d3 ext |
| 8 | [Bonsai-8K](https://huggingface.co/sudoingx/Ternary-Bonsai-2-27B-PTQ1_0-MTP-GGUF) | **5/11** | 29.7 | **55** / 520 | 8K | 7.3 / 1 | graft d2 |
| 9 | [LFM2.5 DSpark](https://huggingface.co/LiquidAI/LFM2.5-8B-A1B) | 0/11 | — | **221** / 500 | 32K | resident | DSpark d4 |
| 10 | [ThinkCap-27B](https://huggingface.co/holooo/ThinkingCap-Qwen3.8-27B-Q2_K-GGUF) | 4/6 | — | 9.6 / 239 | 32K | 7.4 / 6 | MTP d2 |

Units: decode/prefill = t/s / tok/s · p/h = AG-Bench passes per hour · V/R = VRAM/DRAM GB.

⁽¹⁾ 9/11 replicated as 8/11 unpinned — always-thinking distills move ±1 task between runs; treat 1-task margins as bands. Pinned (temp 0/seed 42) runs cost the heavy iterative tasks (task11 fails pinned, passes unpinned).
⁽²⁾ [DFlash-Q2_K/Q4_K_M sidecar](recipes/mimo-9b-distill-q4km-llamacpp.md) → 138 t/s @8K, 94 @16K; 16K pair: score preserved, 1.66× wall. 32K+drafter net-negative for agents (q4_0-KV tax).
⁽³⁾ Card efficiency record: 270s for the full suite at **d3** (2026-10-01, identical pass set to the d2 era's 302s — depth crown from the MTP-depth sweep; d4 gains nothing). Original-suite 3/6 superseded.
⁽⁴⁾ Pinned re-bench 2026-10-01 (temp0/seed42): 9/11 @ 2176 s, fails {task5-TS, task8}; 8–9 band (task9 flipped pass vs the unpinned 8/11 row; task2-React passed, second family occurrence). `--cache-ram 32G` variant measured −24% suite wall but −1 score → not adopted.
⁽⁵⁾ 2026-10-01 pinned+lookup run (reconstructed 64K serve: `-c 65536 --no-kv-offload` + lookup-prompt,draft-mtp d2): 9/11 @ 3791 s — third fleet-tie score, the one on the byte-exact fork binary; fails {task2-React, task5-TS}; task8 cracked at a 600 s cap-grind. 8–9 band, single run; unpinned 64K row superseded.
⁽⁶⁾ Qwen3.8-Flash-Next 125B on the Strata engine: band 8–10/11 (n=4 same-config runs, 2026-10-02/04) — the 10/11 run is the HIGHEST SCORE EVER MEASURED ON THIS CARD (only task5-TS failed; React and the fleet-discriminator task8 both solved). Engine progression 2026-10-04, one variable at a time: 0.1.33-era → v0.1.38 gave **decode 36–41 tok/s (was 31–33), acceptance 0.75** (8/11 @ 23.6 min); v0.1.39 (byte-budget ring + f-139b speedups) held the identical fail set {React, TS, broken-python} at 8/11, wall 22.9 min, acceptance 0.75–0.81 — adopted as the lab standard config. A/B probes (evidence: strata_0139_ab_probes) show the new knobs (ring, top-k guard, nowait, decay≠0.7, k8v4) are all flat-or-worse on this card: upstream defaults win for the third engine version running. Suffix-draft windows hit 43/43 and 63/63 acceptance in-bench. int8 KV; prefill auto:16384. Serve config (tracked verbatim): recipes/strata-configs/strata-q20-gsq-0139.json (v0.1.39 binary, worktree strata-0139); full recipe: recipes/flashnext-gsqrc-q20-125b-strata.md; evidence/strata-q20-sm75-port.jsonl.
⁽⁷⁾ The pruning-vs-quantization answer (2026-10-04, single run): the 50%-expert-pruned Coder (256/512 experts, ~1.89 bpw effective, survivors at IQ1_M, 58.4 GB) scores **9/11** — inside the full-quantized Q2_0 base's 8–10 band, first attempt. Same fails as the day's base run for react-fix/js-to-ts, and it PASSED task8, which that base run failed (band-internal flip). But it decodes **22–27 tok/s vs the base's 36–41** — equal quality, ~35–40% slower. **Verdict: at the same size class, squeeze-everything beats delete-half** — pruning bought neither quality nor speed on this card. Secondary finding: the base's Q2_0 MTP head survives expert-pruning intact (acceptance 0.70–0.80 on the pruned model — same-family heads tolerate the changed hidden states; recall cross-family grafts scored 0.000). Serve: packs/iq1m-coder (302 native tensors, 1.37 GiB arena) + upstream's expert-profile-coder.bin (48×256) + the shared PLE shard hardlink-deduped against the base (sha 316b46f, 28.8 GB). Vision probe pending (mmproj sha drifted upstream since our fetch). Evidence: evidence/strata-q20-sm75-port.jsonl (coder_iq1m_125b_chain); results/strata-coder-iq1m-125b-20261004-133816.jsonl.

**Also on card:** GLM-OCR · kev · laya · GLiNER 2.5 (utility tier: vision, routing, schema extraction)

## Key findings from 24 models

- **The sub-2 bpw wall**: below ~2 bits-per-weight, LLM reasoning chains break (tested twice: IQ1_S loops-to-nothing, Flash-Next-125B thinks-to-EOS) while surface tasks survive. Curated ternary (Bonsai at 1.75 bpw) is the exception.
- **Context ceiling > compression quality**: Bonsai's score jumped 5/11 → 8/11 just from context (8K→64K), no quant change. The "dumb model" was a smart model in a small room.
- **MTP heads bind to their base's hidden-state distribution**: trained heads from one quant family score 0.000 acceptance on a different base (graft experiment). Native embedded heads scale cleanly.
- **Bigger ubatch = faster prefill on RAM-bound models** (the UBBoost claim, reproduced): A3B +24% prefill at `-ub 4096` (measured on our card).
- **The 4B ties the 35B** on the expanded suite — the raw-capability class compresses.

## Repo structure

```text
recipes/         one file per model: identity, settings, results, commands
evidence/        raw JSONL per model
benchmarks/      AG-Bench v2.1 suite (11 tasks, canary-calibrated) + results
TESTED.md        every model tested, with full details
NEXT-IDEAS.md    untested backlog + blocked-with-triggers
hardware.md      the machine behind every number
```

## Credits

- OpenWeights model authors and quantizers — [unsloth](https://unsloth.ai), [PrismML](https://prism.ml), and the model orgs (Qwen, Google, LFM, Xiaomi, TeleAI, fastino, convaiinnovations, jaredpalmer)
- Runtimes — [llama.cpp](https://github.com/ggml-org/llama.cpp) and the forks that made ternary/Xing4 runnable ([sudoingX](https://github.com/sudoingX/llama.cpp), [shuxiaoqiong](https://github.com/shuxiaoqiong/llama.cpp))
- Terminal-bench tasks (MIT) — ported into our suite as tasks 8–12 ([laude-institute/terminal-bench](https://github.com/laude-institute/terminal-bench))
- Acceptance contract — [0xsero/local-ai-registry](https://github.com/0xsero/local-ai-registry)