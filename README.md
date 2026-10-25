# RTX 2080 Local AI Lab

25 models tested on one **RTX 2080 with 8 GB VRAM**. Measured speeds, working
recipes, and the tuning that makes larger models usable on a 2018 Turing GPU.

[Benchmark dashboard](benchmarks/index.html) · [All models tested](TESTED.md) ·
[Hardware](hardware.md) · [Next experiments](NEXT-IDEAS.md)

## Top models on this card

Measured throughput in tokens per second. Prefill entries include the input size;
decode entries identify the workload. Model links open the full recipe and results.

| Model | Prefill, tok/s | Decode, tok/s |
|---|---:|---:|
| [Nemotron 3.5 Bolt E4B UD-Q4_K_XL · DFlash d4](experiments/bolt-64k-engines-20261024/README.md) | **2,386 at 2.1K** | **190.2 code / 86.1 long prose** |
| [Qwen3.8 Flash-Next 125B Q2_0 · tuned Strata 0.1.45](recipes/flashnext-gsqrc-q20-125b-strata.md) | **695.4 at 32K** | **47.1 chat** |
| [Ternary Bonsai 2 9B](recipes/ternary-bonsai2-9b-pq20-mtp-llamacpp-fork.md) | 1,553 at 25K | 115.1 code / 82.2–82.6 prose |
| [Qwen3.5 4B](recipes/qwen35-4b-mtp-q4km-llamacpp.md) | 2,327 at 2.8K | 181.8–182.2 code |
| [Qwen3.5 9B](recipes/qwen35-9b-mtp-q4km-llamacpp.md) | 1,578 at 2.6K | 124.5–124.8 code |
| [Gemma 4 E4B QAT](recipes/gemma-4-e4b-qat-llamacpp.md) | 2,762 at 2.1K | 181.1–181.7 code |
| [MiMo 9B](recipes/mimo-9b-distill-q4km-llamacpp.md) | 1,681, fresh prompt | 61, no draft |
| [Qwen3.5 35B A3B IQ2_XXS](recipes/qwen35-35b-a3b-cpuexperts-llamacpp.md) | 1,038–1,044, fresh prompt | 40, warm decode |
| [Flash-Next Coder 125B IQ1_M](recipes/flashnext-gsqrc-coder-iq1m-125b-strata.md) | — | 21.7–27.4 |

## Latest addition: Nemotron 3.5 Bolt E4B

**2026-10-24:** the Bolt row uses pinned llama.cpp **b11804**, DFlash d4,
and a **65,536-token context allocation**. Rates are means of two measured runs
with warmups excluded; the decode figures use short inputs, not a filled 64K
history. [Measurement details and raw summary](experiments/bolt-64k-engines-20261024/summary.json).

Earlier **b11118** runs scored **10/11 on AG-Bench v2.2 twice**, taking
**341 and 357 seconds**. That suite has not been rerun on b11804; its speed
results and the historical agentic score are separate evidence.
[Agentic results and launch script](experiments/nemotron-bolt-e4b-20261023/README.md).

## Strata tuning for the RTX 2080

**2026-10-18:** Flash-Next 125B runs with **128K context** on this 8 GB card.
Our tuned Strata 0.1.45 configuration improved repeated 32K prefill from
**644.8 to 695.4 tok/s (+7.8%)** and short chat decode from
**42.9 to 47.1 tok/s (+9.8%)** against stock on the same machine.
A separate 121,776-token coding-history replay reached **696.1 tok/s**, up from
580.6 tok/s (**+19.9%**).

We tuned Strata's exact-attention CUDA scorer for the RTX 2080's TU104 GPU,
using smaller blocks of 32 queries and 128 threads, alongside Strata's existing
Turing optimizations. Streaming the KV cache keeps 32K tokens resident on the
GPU while supporting 128K context. Both model shards now live on NVMe storage,
which also cut cold loading from roughly 389 to 39 seconds.

[Performance report](experiments/strata-0145-agbench-20261018/README.md) ·
[CUDA tuning and real-prompt measurements](experiments/rtx2080-prefill-20261018/README.md) ·
[AG-Bench results](benchmarks/README.md)

## Reproduce a result

Each model recipe records the model files, checksums, runtime, launch command,
and measurements. Raw runs live in `experiments/evidence/` and `benchmarks/results/`.

| Location | Contents |
|---|---|
| [recipes/](recipes/) | **Run a model:** setup, configurations, and launch commands |
| [benchmarks/](benchmarks/) | **Compare models:** reusable tests, prompts, dashboard, and scores |
| [experiments/](experiments/) | **Inspect the evidence:** tuning investigations, raw results, and older measurements |
| [docs/](docs/) | **Understand the findings:** research notes, registry history, and archived illustrations |
| [systemd/](systemd/) | **Manage this machine:** installed serving services and helper scripts |

Start with [TESTED.md](TESTED.md) for the model inventory and
[hardware.md](hardware.md) for the hardware and measurement method.
Raw evidence is under `experiments/evidence/`, older measurement records under
`experiments/measurements/`, and shared test inputs under `benchmarks/prompts/`.

## Credits

- Model authors and quantizers: Qwen, Google, PrismML, unsloth, and the other model organizations linked in each recipe.
- Runtimes: [llama.cpp](https://github.com/ggml-org/llama.cpp), Strata, and the forks linked in each recipe.
- Agent tasks: [Terminal-Bench](https://github.com/laude-institute/terminal-bench), MIT licensed.
- Acceptance contract: [local-ai-registry](https://github.com/0xsero/local-ai-registry).
