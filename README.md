# local-ai-RTX-2080

Measured local LLM recipes for the **NVIDIA GeForce RTX 2080 8 GB (TU104, Turing SM75)** on Linux.

This is a measurements ledger, not a model registry. Every number here was produced by a real run on this exact card, with the exact command recorded next to it. Nothing is inferred, ported from other GPUs, or quoted from vendor specs.

## Why a separate repo

[0xsero/local-ai-registry](https://github.com/0xsero/local-ai-registry) only accepts recipes that pass its acceptance contract (digest-pinned docker launch, `accept_recipe.py` on the exact card, derived `validated` status). That contract makes the registry trustworthy — and excludes most of what an 8 GB Turing owner actually wants to know: which configs OOM, where the context ceiling is, what a KV-cache precision change costs, and how models behave that can never validate (custom runtimes, OCR pipelines, host builds).

This repo records **all of it**: the qualified recipes (cross-linked to their registry records), the lab-verified ones, and the failures.

## Rules

1. **Measured only.** A number enters this repo only with the command that produced it.
2. **One recipe = one file** in `recipes/`, named `<model>-<quant>-<runtime>`; variants (context, KV type) live inside the recipe as measured configurations, not as separate claims.
3. Each recipe carries registry-compatible fields where they exist (HF repo, full revision, artifact SHA-256, image digest, argv array), so promoting a qualifying recipe into the registry is copy-adapt, not re-derivation.
4. **Status vocabulary:**
   - ✅ `registry-validated` — promoted and validated in local-ai-registry
   - 🔬 `lab-verified` — measured here; cannot or will not qualify for the registry
   - ⚠️ `boundary` — a limit or failure that is itself the finding (OOM maps, cliffs)
   - 📦 `retired` — superseded; kept for history
5. Raw evidence (JSONL of every run) lives in `evidence/`, dated; fixed prompts in `prompts/` so results stay comparable over time.

## The machine

See [hardware.md](hardware.md). Summary: RTX 2080 8 GB · i5-9600K (6c/6t) · 16 GB RAM · Arch/Omarchy · driver and CUDA pinned per measurement date. Desktop baseline VRAM usage ~520 MiB is subtracted from every residency number.

## Ledger

| Date | What | Result |
|---|---|---|
| 2026-09-23 | Qwen3.5-9B Q4_K_M MTP — ctx ceiling probes | 64K fits **only** with q4_0 KV (7.27 GB); 64K-q8_0 OOMs |
| 2026-09-23 | Qwen3.5-4B Q4_K_M MTP — ctx ceiling probes | 128K with q8_0 KV resident (7.15 GB), zero short-fill decode cost vs 32K |
| 2026-09-23 | Windows-parity 1:1 (two llama.cpp builds, fixed prompt) | Era build ties Windows ±0.1%; current build +5–20% |
| 2026-09-23 | Capability probes | 9B: chat+coding+tools(+continuation) all pass; 4B: coding+tools pass, reasoning riddle fails with thinking off |

## Relationship to local-ai-registry

Two recipes from this ledger are validated in the registry (4B recommended, 9B alternate for `rtx-2080-8gb`). `registry/` holds the cross-links and PR references.