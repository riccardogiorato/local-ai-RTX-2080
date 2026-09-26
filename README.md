# RTX 2080 Local AI Lab — every model tested on one 8 GB Turing card

![GPU](https://img.shields.io/badge/GPU-TU104%20%C2%B7%208%20GB%20%C2%B7%20448%20GB%2Fs-lightgrey) ![method](https://img.shields.io/badge/measurements-reproducible-blue) ![status](https://img.shields.io/badge/recipes-docker%20digest--pinned-informational)

An archive of local LLM experiments on a single known GPU: for every model we try, this repo
records **the model variant, the exact OpenWeights source and revision, the runtime and its
version, the launch settings (context, KV cache, sampler, speculative/decoding options), the
measured results, raw evidence, and a copy-paste command that reproduces it.** Failures and
resource boundaries are recorded with the same care as wins — the OOM map of an 8 GB card is
half the value.

Public benchmarks chase new flagships on 24 GB+ cards. This ledger answers the opposite
question: **what can a 2018 Turing card actually run, today, with current runtimes — and where
does each model stop?** Some results promote into
[0xsero/local-ai-registry](https://github.com/0xsero/local-ai-registry) (recipes that pass its
acceptance contract); that pipeline is one downstream of this lab, not its purpose.

> Method rules live in [hardware.md](hardware.md). Short version: server-reported rates only,
> ranges over repeated runs (no best-of), speeds compared only on the same prompt file, thinking
> off by default. Treat decode deltas < 15% across different prompt classes as noise.

## Test queue

What we plan to run on this card, in order — status updates as they're measured. Everything not
listed here is parked with reasons in [NEXT-IDEAS.md](NEXT-IDEAS.md).

| # | Model / variant | Class | Weights | Status |
|---|---|---|---|---|
| 1 | Qwen3.5-4B / 9B MTP Q4_K_M | chat · coding · tools | unsloth MTP GGUFs, pinned revisions | ✅ [tested](#tested-so-far) · registry-validated |
| 2 | Qwen3.8-27B dense, IQ2_XS ≈2.5 bpw cram + embedded-MTP DT control | measured 4.2–5.3 tok/s, all capability probes pass, partial-offload boundary mapped ✅ [recipe](recipes/qwen38-27b-iq2-llamacpp.md) (weights on archive drive) | ✅ tested |
| 3 | ThinkingCap-Qwen3.8-27B · Q2_K (holooo) — measured: **9.57 tok/s** with embedded MTP d2 (2× the old IQ2_S cram), acceptance 0.995, capability 3/3 thinking-off AND thinking-on ✅ [recipe](recipes/thinkingcap-27b-q2k-llamacpp.md) | 27B thinking-verbosity finetune, dense (non-ternary) | ✅ tested |
| 4 | GLM-OCR Q4_K_M + mmproj Q8_0 (the [local-ocr](https://github.com/riccardogiorato/local-ocr) stack, ported to Linux docker) | measured: receipt 0.455 s warm (410 tok/s decode), 100% GT extraction, 2.86 GB VRAM ✅ [recipe](recipes/glm-ocr-q4km-llamacpp.md) | ✅ tested |
| 5 | Gemma 4 E4B QAT + matching MTP drafter (~4 GB) — measured: **181 tok/s MTP d2** (vs Windows-lab 145), 2.7K tok/s prefill, **128K ctx fully resident** ✅ [recipe](recipes/gemma-4-e4b-qat-llamacpp.md) | edge-class agentic — thinking model | ✅ tested |
| 6 | MiMo-V2.6-Distill-Qwen-9B (Qwen3.5-9B finetune, MIT) — 61 tok/s; MTP head dropped by the distill, speed-identical to parent no-draft ✅ [recipe](recipes/mimo-9b-distill-q4km-llamacpp.md) | agentic distill vs our 9B baseline | ✅ tested |
| 7 | kev-0.5b ([jaredpalmer/kev](https://github.com/jaredpalmer/kev)) — CUDA-on-SM75 works first-try, 146 MiB VRAM, 240 ms/3 questions ✅ [recipe](recipes/kev-05b-serve.md) | typed-decision, single forward pass | ✅ tested |
| 8 | laya (convaiinnovations, 421M) — 27 ms/3 questions (fastest on this card) but 2.66 GB VRAM; routing trails kev on both probes ✅ [recipe](recipes/laya-serve.md) | typed-decision, `pip install laya` | ✅ tested |
| 10 | GLiNER 2.5 multi-v1 (fastino, 287M) — measured: **21.8 ms GPU / 78.3 ms CPU** per extraction, 7 structural passes (en+it NER, zero-shot labels, relations, records), 1650 MiB VRAM ✅ [recipe](recipes/gliner25-multi-v1-serve.md) | typed-extraction (non-LLM utility tier, kev/laya class) | ✅ tested |
| 11 | Xing4.0-29B-A4B (TeleAI) — jmarceno DYN-DIQ4XS-GU2XXS 12.04 GiB @ `6d745c62` · shuxiaoqiong/llama.cpp xing4_0-port fork — 29B/A4B MLA MoE, mHC hyper-connections, MTP; experts-on-CPU class | big-MoE candidate (A3B-class recipe, second 30B-class run) | ⏳ queued |

| 9 | Bonsai-2 27B ternary PTQ1_0 + MTP graft — measured: **59.3/49.9 tok/s fully resident** (5–6× the other 27Bs), 3/3 probes thinking-off, AG-Bench 4/6 ✅ [recipe](recipes/ternary-bonsai2-27b-ptq1_0-llamacpp-fork.md) | 1.75 bpw ternary of dense Qwen3.8-27B, fork runtime | ✅ tested |

New candidates get added here before they're downloaded; each becomes a `recipes/` file the day
it runs. Retests of retired entries also live in the queue — engines move fast and a "won't fit"
from three months ago is worth re-measuring.

**Storage rotation:** the SSD is a workbench, not an archive. Once a model is tested and its
recipe + evidence are committed, its weights move off the SSD to the archive drive (HDD) —
recorded in the recipe — so the workbench never fills up.

## Tested so far

| Recipe | Runtime | Context | Decode (short-fill) | Prefill | Status |
|---|---|---|---|---|---|
| [recipes/qwen35-4b-mtp-q4km-llamacpp.md](recipes/qwen35-4b-mtp-q4km-llamacpp.md) | llama.cpp (docker) | up to 128K | ~182 tok/s | ~2.3K tok/s | ✅ registry-validated · recommended |
| [recipes/qwen35-9b-mtp-q4km-llamacpp.md](recipes/qwen35-9b-mtp-q4km-llamacpp.md) | llama.cpp (docker) | up to 64K (q4_0 KV) | ~124 tok/s | ~1.6K tok/s | ✅ registry-validated · alternate |
| [recipes/qwen38-27b-iq2-llamacpp.md](recipes/qwen38-27b-iq2-llamacpp.md) | llama.cpp (docker, partial offload ngl 48/42) | 8K | ~4.2–5.3 tok/s | ~275–280 tok/s | 🔬 lab-verified · prior slow-smart slot |
| [recipes/thinkingcap-27b-q2k-llamacpp.md](recipes/thinkingcap-27b-q2k-llamacpp.md) | llama.cpp (docker · partial offload ngl 40/ub 128 · embedded MTP d2) | 8K | **9.57 tok/s** (acceptance 0.995) | 239 tok/s (no-draft) | 🔬 lab-verified · slow-smart slot champion |
| [recipes/glm-ocr-q4km-llamacpp.md](recipes/glm-ocr-q4km-llamacpp.md) | llama.cpp (docker · vision) | 12K | 375–410 tok/s (OCR decode) | image prefill 340–2,175 tok/s | 🔬 lab-verified · OCR stack |
| [recipes/gemma-4-e4b-qat-llamacpp.md](recipes/gemma-4-e4b-qat-llamacpp.md) | llama.cpp (docker · external MTP drafter d2) | up to **128K** | **181 tok/s** (2.04× no-draft) | ~2.8K tok/s | 🔬 lab-verified · fast-resident slot · thinking model |
| [recipes/mimo-9b-distill-q4km-llamacpp.md](recipes/mimo-9b-distill-q4km-llamacpp.md) | llama.cpp (docker, no MTP — head dropped by distill) | 32K | 61 tok/s | ~1.7K tok/s | 🔬 lab-verified · parent-dominated |
| [recipes/kev-05b-serve.md](recipes/kev-05b-serve.md) | Python/torch serve (CUDA on SM75) | n/a | 240–256 ms / 3 questions | — | 🔬 lab-verified · 146 MiB router |
| [recipes/laya-serve.md](recipes/laya-serve.md) | Python/torch serve (ModernBERT-large) | n/a | **27 ms** / 3 questions | — | 🔬 lab-verified · 2.66 GB router |
| [recipes/ternary-bonsai2-27b-ptq1_0-llamacpp-fork.md](recipes/ternary-bonsai2-27b-ptq1_0-llamacpp-fork.md) | llama.cpp fork host build (PrismML/sudoingX @ 285542d) | 8K | **55.3 / 49.1 tok/s** (MTP **d2** after the d-depth A/B; full offload) | — | 🔬 lab-verified · fast-27B slot champion |
| [recipes/swift15-27b-iq2xs-mtp-llamacpp.md](recipes/swift15-27b-iq2xs-mtp-llamacpp.md) | llama.cpp (docker · cram ngl 40 · MTP d2) | 8K | 4.4 / 4.3 tok/s (acc 0.745) | 275 tok/s class | 🔬 lab-verified · quant-bound (IQ2_XS tax) |
| [recipes/lfm25-8b-a1b-dspark-llamacpp.md](recipes/lfm25-8b-a1b-dspark-llamacpp.md) | llama.cpp (docker · resident MoE · DSpark sidecar d4) | 32K | **221 / 200 tok/s** (fastest on card) | ~500 tok/s | 🔬 lab-verified · speed-slot record · AG-Bench 0/6 |
| [recipes/qwen35-35b-a3b-cpuexperts-llamacpp.md](recipes/qwen35-35b-a3b-cpuexperts-llamacpp.md) | llama.cpp (docker · MoE, experts in RAM · MTP head d4) | 8K | 9.3 / 8.5 tok/s steady (1.5 in deep agent turns) | 3.65–6.47 tok/s | 🔬 lab-verified · first 35B on card (4.57 GB!) · AG-Bench 3/6 @ cap 900 |
| [evidence only, no recipe](evidence/gemma12b-qat-mtp.jsonl) | llama.cpp (docker · 6.70 GB pair → ngl 45 + Q4 MTP head) | 8K | 29.4 / 43.5 tok/s (acc 0.92/0.70) | ~90 tok/s | 🔬 lab-verified · 12 GB-class model wanting 8 GB · AG-Bench 3/6 |
| [recipes/gliner25-multi-v1-serve.md](recipes/gliner25-multi-v1-serve.md) | gliner2 2.0.0 + torch 2.14 (venv, CUDA) | 4K window | **21.8 ms / extraction** (GPU fp16) | — | 🔬 lab-verified · schema-extraction tier · en+it passes |

Every recipe file records: the exact OpenWeights artifact (repository, revision, SHA-256), the
runtime image digest, full launch settings (context size, KV precision, batch/ubatch, sampler
constraints, speculative decoding), measured decode/prefill/TTFT/VRAM at each configuration,
capability probe results, and raw evidence links.

## Why the details matter to someone with a different card

- **Reproduction is exact.** Pinned revisions + digest-pinned images + literal command = same
  compute for anyone, anywhere. Nothing is measured against a moving target.
- **Boundaries generalize better than speeds.** The context ceilings, OOM maps, and
  KV-precision trade-offs on a known GPU inform every 8 GB card; raw tok/s only transfers to
  your clock speeds.
- **Honest attribution.** When a number moves, the repo records *why* — prompt class, engine
  build, thinking mode — not just the delta. See
  [notes/findings-2026-09-23.md](notes/findings-2026-09-23.md) for worked examples.

## Requirements (per recipe, checked before any run)

| Component | Detail |
|---|---|
| Hardware | NVIDIA GeForce RTX 2080 — TU104, Turing SM75, 8 GB GDDR6, 448 GB/s ([fingerprint](hardware.md)) |
| Host | Linux with Docker; host RAM ≥ 16 GB is sufficient (weights are mmap'd) |
| Docker | NVIDIA Container Toolkit, GPU passthrough verified in a container |
| Model files | Pinned OpenWeights revisions, SHA-256 verified before load |
| Runtime image | Digest-pinned per recipe (engine images vary by recipe — never a mutable tag) |
| CLI tools | `docker`, `curl` |
| Hugging Face token | Optional — pinned public revisions; `HF_TOKEN` helps with rate limits |

## Repository layout

```text
recipes/         one file per model+variant+runtime: identity, settings, results, reproduce commands
measurements/    dated matrices with per-run provenance
prompts/         fixed benchmark prompts — speeds are only comparable within the same file
evidence/        raw JSONL: acceptance harness output, capability probes, timing logs
notes/           empirical rules, attributions, open questions
registry/        cross-links for the subset that promotes into local-ai-registry
hardware.md      the one machine behind every number
```

## How a recipe is born

1. Add the candidate to the queue above (with the exact weights source and why it's interesting).
2. Fetch pinned revision, verify the SHA-256, pick the runtime image by digest.
3. Probe the resource boundary first (ctx × KV precision × VRAM), then measure speed and
   capabilities on fixed prompts, thinking off.
4. Write `recipes/<model>.md` with the full settings table, results, evidence links — including
   what failed.
5. If the launch satisfies the registry contract, run its acceptance harness and cross-link from
   `registry/`.

## Notes

- Prefill numbers always come from fresh prompts — cache-hit `prompt_per_second` reads are garbage.
- Engine choice is per-model and recorded per-recipe: llama.cpp is not assumed, and non-registry
  runtimes (custom forks, host builds, OCR pipelines) get the same rigor as `lab-verified` entries.
- Retests beat reputation: "too slow" verdicts age badly when engines ship +5% per month.

## Credits

- OpenWeights model authors and quantizers, credited per recipe (unsloth, and the model orgs).
- Runtimes by their upstream projects (llama.cpp and friends), always pinned by digest.
- Acceptance contract and validation: [0xsero/local-ai-registry](https://github.com/0xsero/local-ai-registry).
- Benchmark prompts inherited from the prior Windows lab on this same card.