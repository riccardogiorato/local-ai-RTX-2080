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

What we plan to run on this card, in rough order — status updates as they're measured:

| # | Model / variant | Class | Weights | Status |
|---|---|---|---|---|
| 1 | Qwen3.5-4B / 9B MTP Q4_K_M | chat · coding · tools | unsloth MTP GGUFs, pinned revisions | ✅ [tested](#tested-so-far) · registry-validated |
| 2 | Ternary Bonsai-2 27B (PTQ1_0 / PQ2_0) + MTP drafters | ternary 27B experiment | on NVMe | 🧪 queued |
| 3 | low-bpw 27B MoE cram (IQ2_XS-class) | what a 27B costs on 8 GB | on archive drive | 🧪 queued |
| 4 | Gemma 4 E4B QAT + matching MTP drafter | edge-class agentic | needs download (~4 GB) | 🧪 queued |
| 5 | OCR/vision: Q8/Q4 OCR models + mmproj adapters | document OCR | on archive drive | 🧪 queued |
| 6 | Qwen2.5-Coder 7B Instruct Q4_K_M | code-specific legacy retest | in HF cache backup | 📋 backlog |
| 7 | MiniCPM5-2B DSpark | tiny-class sanity | in HF cache backup | 📋 backlog |

New candidates get added here before they're downloaded; each becomes a `recipes/` file the day
it runs. Retests of retired entries also live in the queue — engines move fast and a "won't fit"
from three months ago is worth re-measuring.

## Tested so far

| Recipe | Runtime | Context | Decode (short-fill) | Prefill | Status |
|---|---|---|---|---|---|
| [recipes/qwen35-4b-mtp-q4km-llamacpp.md](recipes/qwen35-4b-mtp-q4km-llamacpp.md) | llama.cpp (docker) | up to 128K | ~182 tok/s | ~2.3K tok/s | ✅ registry-validated · recommended |
| [recipes/qwen35-9b-mtp-q4km-llamacpp.md](recipes/qwen35-9b-mtp-q4km-llamacpp.md) | llama.cpp (docker) | up to 64K (q4_0 KV) | ~124 tok/s | ~1.6K tok/s | ✅ registry-validated · alternate |

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