# All tested models — the complete ledger

Every model, variant, and configuration tested on this card, with links to the
recipe and raw evidence. Failures are recorded with the same care as wins.

**Total models/variants tested: 24** (plus 6 blocked-with-triggers in [NEXT-IDEAS.md](NEXT-IDEAS.md))

## Test queue (historical — all resolved)

| # | Model / variant | Class | Result | Status |
|---|---|---|---|---|
| 1 | Qwen3.5-4B / 9B MTP Q4_K_M | chat · coding · tools | ✅ tested | ✅ [tested](#tested-so-far) · registry-validated |
| 2 | Qwen3.8-27B dense, IQ2_XS ≈2.5 bpw cram + embedded-MTP DT control | slow-smart 27B | 4.2–5.3 tok/s, 3/3 probes | ✅ [recipe](recipes/qwen38-27b-iq2-llamacpp.md) |
| 3 | ThinkingCap-Qwen3.8-27B · Q2_K (holooo) | 27B thinking finetune | **9.57 tok/s** with MTP d2, acc 0.995, 3/3 | ✅ [recipe](recipes/thinkingcap-27b-q2k-llamacpp.md) |
| 4 | GLM-OCR Q4_K_M + mmproj Q8_0 | vision OCR | 0.455 s warm, 100% GT, 2.86 GB VRAM | ✅ [recipe](recipes/glm-ocr-q4km-llamacpp.md) |
| 5 | Gemma 4 E4B QAT + MTP drafter | edge-class thinking | **181 tok/s** MTP d2, 128K resident | ✅ [recipe](recipes/gemma-4-e4b-qat-llamacpp.md) |
| 6 | MiMo-V2.6-Distill-Qwen-9B | agentic distill | 61 tok/s, head dropped; 4/6 → **9/11** on v2.1 | ✅ [recipe](recipes/mimo-9b-distill-q4km-llamacpp.md) |
| 7 | kev-0.5b | typed-decision router | 240 ms/3 questions, 146 MiB VRAM | ✅ [recipe](recipes/kev-05b-serve.md) |
| 8 | laya typed-decisions + multilingual | typed-decision router | 27 ms (typed) / **22 ms** (multilingual, beats kev in Italian) | ✅ [recipe](recipes/laya-serve.md) |
| 9 | Bonsai-2 27B ternary PTQ1_0 + MTP graft d2 | fast-27B ternary | **55.3 tok/s** fully-resident, 4/6 → **8/11** at 64K | ✅ [recipe](recipes/ternary-bonsai2-27b-ptq1_0-llamacpp-fork.md) |
| 10 | GLiNER 2.5 multi-v1 (fastino, 287M) | typed-extraction | **21.8 ms GPU / 78.3 ms CPU** per extraction | ✅ [recipe](recipes/gliner25-multi-v1-serve.md) |
| 11 | Xing4.0-29B-A4B (TeleAI) | big-MoE candidate | **4.0 GB VRAM for a 29B**, 8/11 on v2.1 | ✅ [recipe](recipes/xing4-29b-a4b-dyn-llamacpp-fork.md) |
| 12 | Qwen3.8-27B UD-IQ1_S | 1-bit wall evidence | 19.7 tok/s, reasoning BROKEN at 1.84 bpw | ✅ evidence-only |
| 13 | Qwen3.8-Flash-Next-125B UltraLite | 125B boundary record | 12.5 tok/s, thinking/coding/deep-retrieval all broken at 1.8 bpw | ✅ [recipe](recipes/flashnext-ultralite-125b-llamacpp-fork.md) |

## Additional tested variants

| # | Model / variant | Result | Status |
|---|---|---|---|
| 14 | Swift1.5-27B GSQ-RCO IQ2_XS | 4.4 tok/s, acc 0.745, 3/6 | ✅ [recipe](recipes/swift15-27b-iq2xs-mtp-llamacpp.md) |
| 15 | LFM2.5-8B-A1B + DSpark d4 | **221/200 tok/s** (speed record), 0/6 agent | ✅ [recipe](recipes/lfm25-8b-a1b-dspark-llamacpp.md) |
| 16 | Qwen3.5-35B-A3B (Q3_K_M pack) | 8/11 on v2.1, 22.9 pass/h | ✅ [recipe](recipes/qwen35-35b-a3b-cpuexperts-llamacpp.md) |
| 17 | Qwen3.5-35B-A3B (IQ2_XXS pack) ⭐ recommended | 8/11, **40 tok/s** (new: +11% decode, +24% prefill) | ✅ same recipe (updated) |
| 18 | Gemma-12B QAT + Q4 MTP head | 29.4/43.5 tok/s, 3/6 | ✅ evidence-only |
| 19 | MiniCPM5-2B + DSpark drafter | 2/6 on original-6, 180 tok/s novel class | ✅ evidence-only |

## Full technical details

| Recipe | Runtime | Context | Decode | Prefill | Status |
|---|---|---|---|---|---|
| [qwen35-4b-mtp-q4km](recipes/qwen35-4b-mtp-q4km-llamacpp.md) | docker b11118 | up to 128K | ~182 tok/s | ~2.3K tok/s | ✅ registry-validated |
| [qwen35-9b-mtp-q4km](recipes/qwen35-9b-mtp-q4km-llamacpp.md) | docker b11118 | up to 64K (q4_0 KV) | ~124 tok/s | ~1.6K tok/s | ✅ registry-validated |
| [qwen38-27b-iq2](recipes/qwen38-27b-iq2-llamacpp.md) | docker b11118 · partial ngl 48/42 | 8K | ~4.2–5.3 tok/s | ~275–280 tok/s | 🔬 lab-verified |
| [thinkingcap-27b-q2k](recipes/thinkingcap-27b-q2k-llamacpp.md) | docker b11118 · ngl 40 · MTP d2 | 8K / 32K KV-RAM | **9.57 tok/s** (acc 0.995) | 239 tok/s | 🔬 lab-verified |
| [glm-ocr-q4km](recipes/glm-ocr-q4km-llamacpp.md) | docker b11118 · vision | 12K | 375–410 tok/s (OCR) | image prefill | 🔬 lab-verified |
| [gemma-4-e4b-qat](recipes/gemma-4-e4b-qat-llamacpp.md) | docker b11118 · MTP d2 | up to **128K** | **181 tok/s** | ~2.8K tok/s | 🔬 lab-verified |
| [mimo-9b-distill](recipes/mimo-9b-distill-q4km-llamacpp.md) | docker b11118 · no MTP | 32K | 61 tok/s | ~1.7K tok/s | 🔬 lab-verified |
| [kev-05b](recipes/kev-05b-serve.md) | Python/torch CUDA | n/a | 240–256 ms / 3 q | — | 🔬 lab-verified |
| [laya-serve](recipes/laya-serve.md) | Python/torch CUDA | n/a | 22–27 ms / 3 q | — | 🔬 lab-verified |
| [ternary-bonsai2-27b](recipes/ternary-bonsai2-27b-ptq1_0-llamacpp-fork.md) | fork host build @ 285542d | 8K (64K `--no-kv-offload`) | **55.3 / 49.1 tok/s** (d2) | ~520 tok/s | 🔬 lab-verified |
| [swift15-27b-iq2xs](recipes/swift15-27b-iq2xs-mtp-llamacpp.md) | docker b11118 · ngl 40 · MTP d2 | 8K | 4.4 / 4.3 tok/s | 275 tok/s | 🔬 lab-verified |
| [lfm25-8b-a1b-dspark](recipes/lfm25-8b-a1b-dspark-llamacpp.md) | docker b11118 · DSpark d4 | 32K | **221 / 200 tok/s** | ~500 tok/s | 🔬 lab-verified |
| [qwen35-35b-a3b-cpuexperts](recipes/qwen35-35b-a3b-cpuexperts-llamacpp.md) | docker b11118 · experts in RAM | 32K | 40 tok/s (IQ2_XXS) / 36 (Q3_K_M) | 1040 / 840 tok/s | 🔬 lab-verified |
| [gemma12b-qat-mtp](evidence/gemma12b-qat-mtp.jsonl) | docker b11118 · ngl 45 + Q4 head | 8K | 29.4 / 43.5 tok/s | ~90 tok/s | 🔬 evidence-only |
| [gliner25-multi-v1](recipes/gliner25-multi-v1-serve.md) | gliner2 2.0 + torch (venv) | 4K window | **21.8 ms** / extraction | — | 🔬 lab-verified |
| [xing4-29b-a4b-dyn](recipes/xing4-29b-a4b-dyn-llamacpp-fork.md) | fork host @ 63c16fb | 8K | 25 tok/s (ub4096 warm) | **346 tok/s** | 🔬 lab-verified |
| [qwen38-27b-udiq1s](evidence/qwen38-27b-udiq1s.jsonl) | docker b11118 · full resident | 8K | 19.7 tok/s no-draft | ~505 tok/s | 🔬 evidence-only |
| [flashnext-ultralite-125b](recipes/flashnext-ultralite-125b-llamacpp-fork.md) | patched qwen4exp @ 250b61446 | 128K claim | 12.5 tok/s | 218–233 tok/s | 🔬 boundary record |

## Blocked (see NEXT-IDEAS.md for triggers)

| Model | Block reason |
|---|---|
| Swift Flash-Next 65 GB | 65 GB doesn't fit 46 GB RAM |
| OrcaSAQ 2-bit | exl3 needs sm_80+ |
| Diffusion Gemma 26B | no GGUF, exceeds 8 GB |
| trymirai Qwen3.8-27B-S | uzu Mac-only, vLLM needs sm_80+, no GGUF |
| PQ2_0-MTP tier | needs 11 GB+ VRAM (or 76 GB->8GB sub-GGUF) |
| fafastmobel 23.8 GB | sm_120a-only kernels, NVFP4 Ada/Blackwell |
| Strata engine | sm_80+ (TF32 MMA; soft gate per survey — port work is the blocker) |