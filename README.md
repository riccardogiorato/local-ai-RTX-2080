# RTX 2080 Local AI Lab — 24 models tested on one 8 GB Turing card

![GPU](https://img.shields.io/badge/GPU-TU104%20%C2%B7%208%20GB%20%C2%B7%20448%20GB%2Fs-lightgrey) ![models](https://img.shields.io/badge/models_tested-24-blue) ![method](https://img.shields.io/badge/measurements-reproducible-blue) ![recipes](https://img.shields.io/badge/recipes-docker%20digest--pinned-informational)

**What can a 2018 Turing card run today?** For every model we test, this repo records the
exact artifact (repo, revision, SHA-256), the runtime (digest-pinned), the launch settings, the
measured results, raw evidence, and a copy-paste reproduce command. Failures are recorded
with the same care as wins.

**Full test history →** [TESTED.md](TESTED.md) (all 24 models, recipes, and details).
**Untested backlog →** [NEXT-IDEAS.md](NEXT-IDEAS.md).
**AG-Bench v2.1 suite (11 tasks, canary-verified) →** [benchmarks/README.md](benchmarks/README.md).

> Method rules live in [hardware.md](hardware.md). Short version: server-reported rates only,
> ranges over repeated runs (no best-of), speeds compared only on the same prompt file, thinking
> off by default. Treat decode deltas < 15% across prompt classes as noise.

## Top 10 models on this card

Ranked by AG-Bench v2.1 score (11 tasks, canary-calibrated), then by efficiency (passes/hour).

| # | Model | Score | Decode | Prefill | Context | VRAM | RAM | Spec decoder | The slot it holds |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **MiMo-9B distill** | **9/11** | 52 tok/s | 1,700 t/s | 32 K | 5.5 GB | ~1 GB | none (head dropped) | 🏆 efficiency king — React in 155 s |
| 1 | **Qwen3.5-9B** MTP d4 | **9/11** | 100 tok/s | 1,600 t/s | 64 K | 5.5 GB | ~1 GB | embedded MTP d4 | 🏆 ceiling-setter — the methodical agent |
| 3 | **Qwen3.5-4B** MTP d4 | **8/11** | 150 tok/s | 2,300 t/s | **128 K** | **2.6 GB** | ~1 GB | embedded MTP d4 | value king — fastest agent, 128K in 2.6 GB |
| 4 | **A3B IQ2_XXS** @32K | **8/11** | 40 tok/s | 1,040 t/s | 32 K (v-212 K) | 4.6 GB | 11.8 GB | external MTP d4 | deep-thinker — 35B for 4.6 GB VRAM |
| 5 | **Bonsai-2 64K** ternary | **8/11** | 17 tok/s | ~520 t/s | 64 K | 6.0 GB | +2 GB KV | graft d2 | ternary compression proven intact |
| 6 | **Xing4.0-29B** @ub4096 | **8/11** | 25 tok/s | 346 t/s | 8 K | **4.0 GB** | ~12 GB | embedded MTP d2 | dark horse MoE — 29B in 4 GB |
| 7 | **Bonsai-2 8K** ternary | **5/11** | **55 tok/s** | ~520 t/s | 8 K | 7.3 GB | ~1 GB | graft d2 | fast-answer slot — quick, shallow |
| 8 | **Gemma-E4B** QAT d2 | 3/6→8/11* | 181 tok/s | 2,800 t/s | **128 K** | 4.3 GB | ~1 GB | external MTP d2 | fast-resident + huge context |
| 9 | **LFM2.5-8B** +DSpark | 0/6→0/11 | **221 tok/s** ⚡ | ~500 t/s | 32 K | full-res | ~1 GB | DSpark d4 | speed record — thinking-first, not agent |
| 10 | **ThinkingCap-27B** Q2_K | 4/6 | 9.6 tok/s | 239 t/s | 8 / 32 K | 7.4 GB | ~6 GB | embedded MTP d2 | slow-smart — verified verbosity scaling |

*\*Gemma-E4B scored 3/6 on the original suite; not yet benched on v2.1.*

**Also on card:** GLM-OCR (vision, 0.455 s receipts) · kev / laya (typed-decision routers, 22–240 ms) · GLiNER 2.5 (schema extraction, 21.8 ms) · Bonsai-2 8K fast-mode.

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