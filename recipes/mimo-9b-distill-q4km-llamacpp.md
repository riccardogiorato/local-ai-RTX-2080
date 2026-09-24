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
`--spec-type draft-mtp` fails to load: *"model doesn't contain MTP layers"*. No speculative
decoding exists for this finetune today — and no external drafter applies (its weights are
its own after distillation).

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

## Verdict

If you want a 9B-class thinker at 61 tok/s with no drafter and can't run the parent's MTP
path, MiMo is a drop-in — but on this engine the parent strictly dominates: same weights
class, same capability profile, 2× decode via embedded MTP. The distill only makes sense
where its specific agentic behavior is what you want (unmeasured here) or where the target
runtime can't speculate anyway.

## Storage

Per the rotation rule the 5.4 GB Q4_K_M moves to the archive drive after this recipe was
committed (its parent stays live as the recommended 9B).