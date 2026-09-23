# GLM-OCR (0.9B VLM) · Q4_K_M + mmproj-Q8_0 · llama.cpp — document OCR

**Status: 🔬 lab-verified** — the [local-ocr](https://github.com/riccardogiorato/local-ocr)
stack (developed on Windows against this same GPU) ported to Linux docker, with the serving
pair rebuilt through the identical chain.

- Decoder: `zai-org/GLM-OCR` → f16 GGUF → **Q4_K_M (548 MB)** (converted f16 inherited from the
  prior lab's archive; conversion chain reproduced in the pinned image)
- Vision tower: f16 mmproj → **Q8_0 (469 MB)** — the mmproj-Q4_K_M variant stays rejected
  (destroys dense labels; prior-lab finding, still true)
- Engine: llama.cpp `0.4.1-dev b11118 / e6ab7c1a4`, digest-pinned ggml-org server image
- Config: `-c 12288 -np 1 -fa on --jinja`, full offload — from local-ocr's measured serve profile
- VRAM: **2.86 GB** — leaves the card free for a text model alongside

## Measured on this box (Linux, b11118 docker, synthetic GT-known images)

| Case | Wall end-to-end | Decode | Prompt (image) rate | Quality |
|---|---|---|---|---|
| Receipt — first image (cold) | 37.1 s ⚠️ | 391 tok/s | 47 tok/s | first-request init: clip load + graph compile — **always warm up** (local-ocr's serve script does this with a startup image) |
| Receipt — warm | **0.455 s** | 409.8 tok/s | 340 tok/s | **100% GT match** — all line items, prices, total (22.50) extracted verbatim |
| Dense bilingual label | 2.13 s | 374.9 tok/s | 2,175 tok/s | clean extraction, **no degeneration** at this prompt |

Prior Windows lab numbers (real 3 MP photos): receipt-class 1.0–1.5 s, dense label 7–9 s with
~2,200 output tokens; decode floor 310 tok/s (Q4). The Linux port decodes **+25–32% faster**
(375–410 vs 310 tok/s) and completes the smaller synthetic images faster than the Windows
wall-clock baseline at equivalent image sizes.

Evidence: [evidence/glm-ocr-linux-docker.jsonl](../evidence/glm-ocr-linux-docker.jsonl)
(raw timing rows; full extraction transcript in `evidence/` alongside).

## Reproduce

```bash
sudo docker run --gpus all -p 8080:8080 -v ~/models/glm-ocr:/models:ro -d \
  ghcr.io/ggml-org/llama.cpp:server-cuda12-b11118@sha256:bfb3264fc2166e01e2b4f9b537e45d7006d87c75021b911f132ef607f5bbced3 \
  --model /models/GLM-OCR-Q4_K_M.gguf --mmproj /models/mmproj-Q8_0.gguf \
  --alias GLM-OCR --host 0.0.0.0 --port 8080 \
  --ctx-size 12288 --parallel 1 --n-gpu-layers 999 --flash-attn on --jinja
# warm up with any image before timing (first request pays ~37 s of init)
```

## Notes

- Rebuilding the pair on Linux: `convert_hf_to_gguf.py <src> --mmproj --outtype f16` +
  `llama-quantize … Q8_0` works in the pinned image; the **decoder** tokenizer conversion hits
  `TokenizersBackend` (not imported by the image's transformers) — workaround: quantize the
  archived f16 decoder instead of re-converting, or patch tokenizer_class. Recorded so the
  next build does not re-trip on it.
- The KFC/CIAO real-photo GT sets from the prior campaign did not survive the machine
  migration; a new GT-known image regression set is a TODO (synthetic receipt + dense-label
  used here, rendered with ImageMagick — included in the recipe's test assets).