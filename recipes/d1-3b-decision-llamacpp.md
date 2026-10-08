# d1-3B (LiquidAI) decision model, llama.cpp `/v1/systemone` on SM75

**Status: lab-verified, utility tier.** A 3.1B multimodal decision model (LFM2.5-VL-3B base): you send
a state (text, JSON, images) and typed questions (`noul` yes/no, `choice`, `score`) and it returns
probabilities in one forward pass with zero generated tokens. Not a chat or coding model.

- Weights: `LiquidAI/d1-3B-GGUF` `d1-3B-Q8_0.gguf` 2,874,781,280 B sha256 `2f0942d5…ba77d`,
  `d1-3B-Q4_K_M.gguf` 1,674,456,672 B sha256 `16aff27e…22402`, `mmproj-d1-3B-Q8_0.gguf` 583,109,728 B
  sha256 `2505920c…2e92a` (all verified against the HF manifest)
- Runtime: llama.cpp **build 11514 (`de7fa0a3c`), built from source** for sm75. d1 support landed in
  #30110 (2026-10-07 20:04); the newest Docker nightly (b11459) predates it and fails with
  `unsupported decision model type: lfm2-d1`, and the 2026-10-08 nightly failed to publish.

```bash
cmake -S . -B build-sm75 -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=75 -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF
cmake --build build-sm75 --target llama-server -j 6
./build-sm75/bin/llama-server --model d1-3B-Q8_0.gguf --mmproj mmproj-d1-3B-Q8_0.gguf \
  --ctx-size 32768 --n-gpu-layers 999 --flash-attn on --batch-size 4096 --ubatch-size 4096 --parallel 8
curl http://127.0.0.1:8080/v1/systemone -H 'Content-Type: application/json' \
  -d '{"state":"I was charged twice, please refund one.","questions":{"refund":{"type":"noul","instructions":"Is the customer asking for a refund?"}}}'
```

## Measured (2026-10-09, warm, median / p90 of 20 calls)

| | Q8_0 | Q4_K_M | Liquid's RTX 4090 bf16 |
|---|---|---|---|
| VRAM (model + mmproj, ctx 32K, 8 slots) | 4.6 GB | 3.5 GB | |
| 1 question | 15.8 / 15.9 ms | 14.1 / 14.2 ms | 8 ms (16 ms without CUDA graphs) |
| 3 questions, one request | 62.7 ms | 55.1 ms | 21 ms |
| 2,973-token state | 507 ms | 552 ms | 102 ms (3.4K tokens) |
| 384 px image | 80.5 ms | 75.9 ms | 17 ms |
| Throughput, 8 concurrent clients | 100 decisions/s | 100 decisions/s | 475/s packed |
| Accuracy, 30 labeled text decisions | 28/30 | 28/30 | |
| Accuracy, 4 image yes/no | 4/4 (P 0.99 / 0.01) | 4/4 | |

- Misses (both tiers): "17 + 25 = 42" judged incorrect at P(yes) 0.44, and German language ID. Both
  were low-confidence calls, so the probabilities flagged them.
- Q4_K_M vs Q8_0: mean |ΔP(gold)| 0.010 (max 0.13) over the 30 items, identical answers, so Q4_K_M is
  the tier to run here: 1.1 GB less VRAM, slightly faster on short states.
- llama.cpp answers the 3 questions of one request one after another (about 3x the single-question
  time), unlike the HF `system_one` path that answers them in one pass.

Evidence: [evidence/d1-3b.jsonl](../evidence/d1-3b.jsonl)
