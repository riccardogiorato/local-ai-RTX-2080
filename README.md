# RTX 2080 Local AI Lab — 25 models tested on one 8 GB Turing card

![GPU](https://img.shields.io/badge/GPU-TU104%20%C2%B7%208%20GB%20%C2%B7%20448%20GB%2Fs-lightgrey) ![models](https://img.shields.io/badge/models_tested-25-blue) ![method](https://img.shields.io/badge/measurements-reproducible-blue) ![recipes](https://img.shields.io/badge/recipes-docker%20digest--pinned-informational)

**What can a 2018 Turing card run today?** For every model we test, this repo records the
exact artifact (repo, revision, SHA-256), the runtime (digest-pinned), the launch settings, the
measured results, raw evidence, and a copy-paste reproduce command. Failures are recorded
with the same care as wins.

**Full test history →** [TESTED.md](TESTED.md) (all 25 models, v2.1-era scores, recipes, and details).
**Untested backlog →** [NEXT-IDEAS.md](NEXT-IDEAS.md).
**AG-Bench v2.2 suite (11 tasks, 900 s cap) →** [benchmarks/README.md](benchmarks/README.md).

**Strata update (2026-10-13):** v0.1.44 adopted: speed parity with v0.1.43 (short decode 51.8 vs 52.8 tok/s, 32K prefill 657 both), AG-Bench v2.2 **10/11 at 709 s** (the miss is the flaky bank task, which passed 2/2 repeats on 0.1.44 and 1/2 on 0.1.43). Earlier, **(2026-10-11):** v0.1.43 adopted: AG-Bench v2.2 **11/11**, short decode 49.8 → 52.5 tok/s over v0.1.42 (same calibrated chat settings). Earlier, **(2026-10-10):** v0.1.42 adopted with the existing calibrated
chat settings. Full same-day v2.2 comparison: v0.1.41 11/11 at 871 s,
v0.1.42 10/11 at 815 s; aggregate decode 37 → 44 tok/s. The missed bank task
passed a controlled repeat. [Results, scoring correction and limits](benchmarks/README.md#strata-0141-vs-0142-2026-10-10).

> Method rules live in [hardware.md](hardware.md). Short version: server-reported rates only,
> ranges over repeated runs (no best-of), speeds compared only on the same prompt file, thinking
> off by default. Treat decode deltas < 15% across prompt classes as noise.

## Fair-context run (2026-10-12)

Same v2.2 suite, but each model at its largest useful context instead of the 32K default, so long-prompt tasks
(task9 is ~40K tokens) stop failing on capacity. One run per model on llama.cpp b11562 / Strata, DDR4-3200.

| Model | Context | v2.2 | Suite wall | p/h | Misses |
|---|---|---|---|---|---|
| Qwen3.5-9B | 64K | **11/11** | 532 s | **74.4** | none |
| Qwen3.8-Flash-Next Q2_0 125B (Strata 0.1.43) | 128K | **11/11** | 1097 s | 36.1 | none |
| A3B IQ2_XXS 35B | 64K | **11/11** | 1175 s | 33.7 | none |
| Flash-Next Coder IQ1_M 125B (Strata 0.1.38) | 32K | **11/11** | 1689 s | 23.4 | none |
| Qwen3.5-4B | 128K | **10/11** | 1219 s | 29.5 | task2 |
| MiMo-9B | 64K | **9/11** | 2703 s | 12.0 | task9, task11 |

With enough context, four models reach 11/11, and Qwen3.5-9B does it fastest. The 32K ceiling explained the 9B and
A3B task9 misses below. Caveats: single runs; the Strata 128K run was cut at 9 tasks by a harness timeout and its last two
tasks finished on the same live server ([merged rows](benchmarks/results/strata-q20-128k-0143-v22-20261012-171801-merged.jsonl));
the Qwen-4B row is the clean stock re-run (an earlier run overlapped a CPU stress test: 10/11 @ 1326 s).
Raw: `benchmarks/results/*-64k-* / *-128k-* / *-32k-*-20261012-*`, [runner log](benchmarks/results/fairctx-ram3200-20261012.runner.log).

## Top models on this card

Ranked by **AG-Bench v2.2** (900 s per task, the two broken checkers fixed), then by efficiency. The five llama.cpp models were all re-run same-day on one fresh build (b11562); the Strata models run their own engine. v2.1-era scores for every model stay in [TESTED.md](TESTED.md) and git history.

| Rank | Model | v2.2 | Suite wall | p/h | Engine | Notes |
|---|---|---|---|---|---|---|
| 1 | [Qwen3.8-Flash-Next GSQ-RCO Q2_0 125B](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF) | **11/11** | 1009 s | 39.2 | Strata 0.1.43 | only perfect run on the card; 10/11 on 0.1.42 @ 815 s |
| 1 | [Ternary-Bonsai-2-9B PQ2_0+MTP](https://huggingface.co/prism-ml/Ternary-Bonsai-2-9B-gguf) | **11/11** | 617 s | **64.1** | prism fork (llama.cpp) | fastest perfect run; native 128K, 115 t/s decode, free 4-slot, vision |
| 2 | [Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B) | **10/11** | 444 s | 81.1 | llama.cpp b11562 | miss: task10 |
| 2 | [Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B) | **10/11** | 515 s | 69.9 | llama.cpp b11562 | miss: task9, a 40K-token prompt past its 32K ctx (capacity, not quality) |
| 2 | [MiMo-9B](https://huggingface.co/bartowski/MiMo-V2.6-Distill-Qwen-9B-GGUF) (32K, no draft) | **10/11** | 1062 s | 33.9 | llama.cpp b11562 | miss: task11 |
| 2 | [A3B IQ2_XXS 35B](https://huggingface.co/Qwen/Qwen3.5-35B-A3B) | **10/11** | 2078 s | 17.3 | llama.cpp b11562 | miss: task9, same 32K-ctx ceiling artifact |
| 6 | [Gemma-E4B](https://huggingface.co/google/gemma-4-E4B-it-qat-q4_0-unquantized) (d3, 128K) | **9/11** | 368 s | **88.0** | llama.cpp b11562 | efficiency record on the card |
| 6 | [Qwen3.8-Flash-Next GSQ-RCO Coder IQ1_M 125B](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF) | **9/11** | 2329 s | 13.9 | Strata 0.1.38 | 22-27 tok/s decode class |

p/h = AG-Bench passes per hour of suite wall time. Decode/prefill speeds and full caveats live in each model's recipe.

**What v2.2 is:** 900 s per task (was 600) plus two fixed checkers. task2 expected an impossible total (18.00 EUR; the inputs sum to 17.50) and task5's TypeScript check never ran on current npm (1 pass in 64 runs); both had been failing every model since September. The longer cap changed no Strata outcome (every miss ended well before 600 s), the checker fixes are what moved scores. Same pi harness, same 11 tasks. Raw and corrected rows are both in `benchmarks/results/` (`*-v22-*` and `*-v22-fixed-*`).

**Not yet re-run under v2.2** (v2.1-era scores in [TESTED.md](TESTED.md)): Bonsai-64K 9/11 (needs the PrismML fork), Xing-29B 8/11, Bonsai-8K 5/11, ThinkCap-27B 4/6, LFM2.5 DSpark 0/11.

**Also on card:** GLM-OCR · kev · laya · GLiNER 2.5 · [d1-3B](recipes/d1-3b-decision-llamacpp.md) · [EmbeddingGemma-2](recipes/embeddinggemma-2-llamacpp.md) · [Saluki 27B](recipes/saluki-27b-iq2mix-llamacpp.md) (utility tier: vision, routing, schema extraction, decisions, embeddings; Saluki tested, not adopted)

## Key findings from 25 models

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
