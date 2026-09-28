# Xiaomi MiMo-V2.6-Distill-Qwen-9B · Q4_K_M · llama.cpp — agentic distill vs our 9B baseline

**Status: 🔬 lab-verified** — a Qwen3.5-9B agentic-distill finetune (MIT), measured head-to-head
against its parent model under identical flags, prompt file, and engine build.

- Weights: `bartowski/MiMo-V2.6-Distill-Qwen-9B-GGUF` → `MiMo-V2.6-Distill-Qwen-9B-Q4_K_M.gguf`
  5,841,049,120 B · sha256 `4bca6f18c73f7227…` (verified against the repo's LFS oid)
- Engine: llama.cpp `0.4.1-dev b11118 / e6ab7c1a4`, digest-pinned image as everywhere here
- Config: **identical to the Qwen3.5-9B 32K registry config** (`-c 32768 -np 1 -ngl 999 -fa on
  -b 512 -ub 512 -ctk q8_0 -ctv q8_0 --jinja`), full offload, 6.59 GB at 32K

## The MTP finding (the headline)

The distill GGUF **drops Qwen3.5's embedded nextn/MTP head**. Launching with
`--spec-type draft-mtp` fails to load: *"model doesn't contain MTP layers"* — and the
parent's head cannot be grafted back (falsified at 0.0005 acceptance, commit 327af00:
the distill drift kills single-layer heads). The recovery is the family-matched
**DFlash sidecar** (2026-09-28, section below): a 6-layer block-diffusion drafter
tolerates the drift and restores 2.4× decode.

## Measured on this box (2026-09-24, fixed code-continuation prompt, thinking off)

| Metric | MiMo-9B (no draft) | Qwen3.5-9B (d4 MTP) | Qwen3.5-9B no-draft control |
|---|---|---|---|
| Decode | **61 tok/s** | ~124 tok/s (100% accept on this prompt) | **62 tok/s** |
| Prefill (fresh prompt) | 1,681 tok/s | ~1.6K tok/s | — |
| 32K VRAM | 6.59 GB | 7.27 GB (q4_0 KV was used for 64K, not needed here) | — |

**The no-draft control settles it: MiMo is speed-identical to its parent (61 vs 62 tok/s).**
The entire decode gap to the 9B's 124 tok/s is the missing MTP head — zero per-token
architecture penalty from the distillation.

## Capabilities (harness, thinking off via `enable_thinking: false`)

| Probe | Result |
|---|---|
| Chat reasoning (trains riddle) | ✅ PASS |
| Coding (exec-verified fix) | ✅ PASS |
| OpenAI tools + continuation | ✅ PASS |

Same 3/3 profile as Qwen3.5-9B. Whether the "agentic distill" behavior actually beats the
parent on multi-step agent tasks is **not measured here** — that needs an agent-workload
benchmark, not these probes (parked in NEXT-IDEAS until such a harness is picked).

Evidence: [evidence/mimo-9b-distill-q4km-llamacpp.jsonl](../evidence/mimo-9b-distill-q4km-llamacpp.jsonl),
[evidence/mimo-9b-distill-q4km-capabilities.jsonl](../evidence/mimo-9b-distill-q4km-capabilities.jsonl)

## Reproduce

```bash
sudo docker run --gpus all -p 8080:8080 -v ~/models/mimo-9b:/models:ro -d \
  ghcr.io/ggml-org/llama.cpp:server-cuda12-b11118@sha256:bfb3264fc2166e01e2b4f9b537e45d7006d87c75021b911f132ef607f5bbced3 \
  --model /models/MiMo-V2.6-Distill-Qwen-9B-Q4_K_M.gguf --alias MiMo-9B-Distill-Q4_K_M \
  --host 0.0.0.0 --port 8080 --ctx-size 32768 --parallel 1 --n-gpu-layers 999 \
  --flash-attn on --batch-size 512 --ubatch-size 512 \
  --cache-type-k q8_0 --cache-type-v q8_0 --jinja
# no --spec-type flags: this GGUF has no MTP layers; adding draft-mtp makes the load fail
```

## The DFlash fix — spec decode RECOVERED via sidecar (2026-09-28)

The dropped MTP head is not the end of the story: a **family-matched DFlash drafter
works**. `z-lab/Qwen3.5-9B-DFlash` (1.3B, 6-layer block-diffusion, retrained for the
*parent*) as a 0.7 GB Q4_K_M sidecar drafts for the distill at **0.794 acceptance /
mean 7.31 accepted** on code — vs 0.0005 for the falsified parent-MTP-head graft. The
distill drift that kills single-layer nextn heads does not kill a 6-layer text-space
sidecar.

- Drafter: `onion515/Qwen3.5-9B-DFlash-GGUF` `qwen3.5-9b-dflash-Q4_K_M.gguf` 765,960,384 B
  · sha256 `d9999163…` (verified; vocab 248,320 → mask token inside MiMo's vocab)
- Working ctx: **8192 only** (the ~1.3 GB drafter VRAM stack pushes 16K ~200 MB over;
  n_max 12 loads but OOMs at runtime, 16 fails at load — n_max 8 is the optimum)

| Metric | control (8K, no draft) | +DFlash n4 | +DFlash n8 |
|---|---|---|---|
| Decode, code class | 56.1–56.8 tok/s | 91.9–93.2 | **134.6–138.3 (2.4×)** |
| Decode, novel class | 56.7 tok/s | 68.7 | **71.4–71.6 (1.26×)** |
| Acceptance (code/novel) | — | 0.701 / 0.407 | 0.794 / 0.271 |

Beats the parent's own 124 tok/s d4-MTP on the repetitive class. 6-prompt mixed chat
mean 84.4 tok/s (~1.5×); chain-of-thought collapses acceptance (riddle prompt 26.2).
Serial serve is 61 tok/s at the 32K recipe config (8K/ub128 costs ~7%).
**Drift column: 0/6 drafted==serial byte-identical** (both modes 6/6 self-deterministic;
`GGML_CUDA_BATCH_INVARIANT=1` is a no-op on upstream b11118 — exactness patch is
fork-only). Quality impact of the drift is an open AG-Bench re-run, not inferable from bytes.

Evidence: [evidence/mimo-9b-dflash-drafter.jsonl](../evidence/mimo-9b-dflash-drafter.jsonl)

### Reproduce the drafted serve

```bash
sudo docker run --gpus all -p 8080:8080 -v ~/models/mimo-9b:/models:ro -d \
  ghcr.io/ggml-org/llama.cpp:server-cuda12-b11118@sha256:bfb3264fc2166e01e2b4f9b537e45d7006d87c75021b911f132ef607f5bbced3 \
  --model /models/MiMo-V2.6-Distill-Qwen-9B-Q4_K_M.gguf --alias MiMo-9B-DFlash \
  --host 0.0.0.0 --port 8080 --ctx-size 8192 --parallel 1 --n-gpu-layers 999 --metrics \
  --flash-attn on --batch-size 256 --ubatch-size 128 \
  --cache-type-k q8_0 --cache-type-v q8_0 --jinja \
  --spec-type draft-dflash --spec-draft-model /models/qwen3.5-9b-dflash-Q4_K_M.gguf \
  --spec-draft-n-max 8 --spec-draft-ngl 99
```

## Verdict

Updated twice: the AG-Bench v2.1 suite (9/11, 42.5 pass/h) overturned "parent-dominated"
on capability — the distill *beats* the parent on agent efficiency; and the DFlash
sidecar (2026-09-28) overturns it on decode too: **134.6–138.3 tok/s code / 71.5 novel**
with a 0.7 GB sidecar beats the parent's 124 tok/s d4-MTP class. MiMo + DFlash is now
the fastest 9B-class thinking serve on the card — with two strings attached: practical
context is 8K (32K needs the trade-offs in NEXT-IDEAS), and drafted bytes drift vs the
no-draft path on upstream kernels (near-tie flips, quality unmeasured at bench level).

## Storage

Rotated 2026-09-24 to /mnt/archive/local-models/rtx2080-tested-2026-09/mimo-9b/
(SHA 4bca6f18… verified; the parent 9B remains the live recommendation).