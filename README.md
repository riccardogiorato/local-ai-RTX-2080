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

Ranked by AG-Bench v2.1 score (11 canary-verified tasks), then by efficiency.

| Rank | Model | Score | Decode / Prefill | Context | VRAM / RAM | Spec decoder |
|---|---|---|---|---|---|---|
| 1 | [MiMo-9B](https://huggingface.co/bartowski/MiMo-V2.6-Distill-Qwen-9B-GGUF) | **9/11** | 52 t/s / 1.7K | 32K (8K +DFlash) | 5.5 GB / 1 GB | **DFlash d8 sidecar → 135–138 t/s code** (2026-09-28; bench re-run pending) |
| 1 | [Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B) | **9/11** | 100 t/s / 1.6K | 64K | 5.5 GB / 1 GB | MTP d4 |
| 3 | [Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B) | **8/11** | 150 t/s / 2.3K | **128K** | 2.6 GB / 1 GB | MTP d4 |
| 4 | [A3B IQ2_XXS](https://huggingface.co/Qwen/Qwen3.5-35B-A3B) | **8/11** | 40 t/s / 1K | 32K+ | 4.6 GB / 12 GB | MTP d4 ext |
| 5 | [Bonsai-64K](https://huggingface.co/sudoingx/Ternary-Bonsai-2-27B-PTQ1_0-MTP-GGUF) | **8/11** | 17 t/s / 520 | 64K | 6.0 GB / 2 GB | graft d2 |
| 5 | [Xing-29B](https://huggingface.co/XingChen-AGI/Xing4.0-29B-A4B) | **8/11** | 25 t/s / 346 | 8K | 4.0 GB / 12 GB | MTP d2 |
| 5 | [Bonsai-8K](https://huggingface.co/sudoingx/Ternary-Bonsai-2-27B-PTQ1_0-MTP-GGUF) | **5/11** | **55 t/s** / 520 | 8K | 7.3 GB / 1 GB | graft d2 |
| 8 | [Gemma-E4B](https://huggingface.co/google/gemma-4-E4B-it-qat-q4_0-unquantized) | n/a\* | **181 t/s** / 2.8K | **128K** | 4.3 GB / 1 GB | MTP d2 ext |
| 9 | [LFM2.5 DSpark](https://huggingface.co/LiquidAI/LFM2.5-8B-A1B) | 0/11 | **221 t/s** / 500 | 32K | resident | DSpark d4 |
| 10 | [ThinkCap-27B](https://huggingface.co/holooo/ThinkingCap-Qwen3.8-27B-Q2_K-GGUF) | 4/6 | 9.6 t/s / 239 | 32K | 7.4 GB / 6 GB | MTP d2 |

*\*Gemma-E4B not yet benched on v2.1; scored 3/6 on the original suite.*

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