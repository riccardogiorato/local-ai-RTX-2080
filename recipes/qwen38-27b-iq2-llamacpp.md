# Qwen3.8-27B · IQ2_XS-class (≈2.5 bpw) · llama.cpp

**Status: 🔬 lab-verified** — pinned custom low-bpw artifacts; partial GPU/CPU offload is inherent
to this class, so no registry contract applies. The intelligence-ceiling entry for this card.

Two artifacts, both ≈8 GiB, both from the low-bpw wave tracked in the prior lab:

| artifact | size | SHA-256 (prefix) | MTP | source |
|---|---|---|---|---|
| `Qwen3.8-27B-DT-IQ2_S.gguf` | 8.810 GB | `993c276e2cc4ab90…` (verified) | **embedded (draft-mtp d2)** | Draw Things bpw-2.48 build |
| `Qwen3.8-27B-GSQ-RCO-IQ2_XS.gguf` | 8.423 GB | archive copy | none | GSQ-RCO IQ2_XS build |

Engine: llama.cpp `0.4.1-dev b11118 / e6ab7c1a4`, image digest-pinned as everywhere in this repo.

## Residency — partial offload is mandatory on a busy desktop

With the Linux desktop consuming ~625 MiB, full offload (`-ngl 999`) cannot allocate:
the DT file needs a 7.65 GiB weights buffer and dies at cudaMalloc; GSQ needs 8.13 GiB.
Both load at reduced layer counts. This mirrors the prior Windows lab, which ran its best
profiles at `-ngl 51` — with a lighter Windows desktop, three layers more fit than here.

| config | ngl | ctx | KV | VRAM | free | decode | prefill | MTP accept |
|---|---|---|---|---|---|---|---|---|
| DT-IQ2_S embedded-MTP d2 | **48** | 8K | q4_0 | 7.69 GB | 100 MiB | **4.63–5.27 tok/s** | 280 tok/s | 114/168 ≈ 0.68 |
| GSQ-RCO IQ2_XS (no draft) | 42 | 8K | q4_0 | 6.58 GB | 1.2 GB | **4.2–4.5 tok/s** | 275 tok/s | — |
| DT-IQ2_S + 32K ctx | 44/46 | 32K | q4_0 | ⚠️ allocator crash at both tested splits; 8K-class is the working envelope tonight | | | | |

Remaining flags (translated from the prior Windows `best-balanced` profile): `-c 8192 -np 1
-b 512 -ub 256 --cache-ram 0 --load-mode none --fit off --no-warmup --backend-sampling
--prio 1 --poll 100` (draft: `--spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-ngl all
--prio-draft 1 --poll-draft 1`). `-ub 256` vs the Windows `512` and `--prio 1` vs `2` are
Linux-container adaptations; measured effect is within run-to-run noise for decode.

## Comparison to the prior Windows lab (same card, files, prompt)

| profile | Windows (lab build, ngl 51) | Linux (b11118, ngl 48) |
|---|---|---|
| DT-IQ2_S MTP d2 balanced | 6.52 tok/s decode · 222 tok/s prefill | 4.63–5.27 tok/s · 280 tok/s |
| MTP-off control | 3.95 tok/s | (GSQ no-draft runs 4.2–4.5 tok/s at ngl 42) |

Decode is lower here **because of the layer split, not the OS**: this desktop costs ~625 MiB and
pushed three layers to CPU; the CPU band is in the critical path at every token. Prefill improved
+26%. A lighter desktop (or fewer GPUs' worth of shell) recovers the Windows profile — the
Windows lab's own numbers prove the same machine reaches 6.5+ with `ngl 51`.

## Capabilities (2026-09-27, thinking default, capability harness)

| Probe | Result |
|---|---|
| Multi-fact reasoning (train-transit comparison) | ✅ pass |
| Coding: fix buggy function, output executed against cases | ✅ pass |
| OpenAI tools: `get_weather("Turin")` + round-tripped tool result | ✅ pass |

All three pass — the profile of the card where the 4B (below) fails the reasoning probe.
This is the slow-but-smart slot: ~5 tok/s, but the strongest reasoning measured on this card.

Evidence: [evidence/qwen38-27b-iq2s-llamacpp-capabilities.jsonl](../evidence/qwen38-27b-iq2s-llamacpp-capabilities.jsonl)

## Reproduce (DT profile)

```bash
sudo docker run --gpus all -p 8080:8080 -v ~/models/qwen38-27b:/models:ro -d \
  ghcr.io/ggml-org/llama.cpp:server-cuda12-b11118@sha256:bfb3264fc2166e01e2b4f9b537e45d7006d87c75021b911f132ef607f5bbced3 \
  --model /models/Qwen3.8-27B-DT-IQ2_S.gguf --alias Qwen3.8-27B-IQ2S-MTP \
  --host 0.0.0.0 --port 8080 --n-gpu-layers 48 --ctx-size 8192 --parallel 1 \
  --batch-size 512 --ubatch-size 256 --flash-attn on \
  --cache-type-k q4_0 --cache-type-v q4_0 --cache-ram 0 --jinja --no-warmup --fit off \
  --load-mode none --backend-sampling --prio 1 --poll 100 \
  --spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-ngl all --prio-draft 1 --poll-draft 1
```

## Notes

- The Qwen3.8 architecture (GDN/recurrent hybrid) reserves a fixed ~337 MiB **rs cache** on GPU
  regardless of batch/context — it is the allocation that fails first when the card is tight,
  before KV or compute buffers. Budget it in every fit calculation.
- `--prio 2` needs elevated scheduling permissions inside the container (warning logged);
  `--prio 1` is the working value without extra capabilities.
- Weights live on the archive drive; the SSD workbench copy is removed after testing
  (storage rotation rule).