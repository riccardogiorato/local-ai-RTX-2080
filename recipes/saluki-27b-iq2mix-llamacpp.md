# Underdog Saluki 27B 1.0 (ConwayResearch) IQ2-mix, llama.cpp on SM75

**Status: tested, not adopted.** Qwen3.8-27B squeezed to 7.89 GB (built on ISTA-DASLab's GSQ-RCO quant),
tuned for tool calling, Apache-2.0. Plain GGUF for stock llama.cpp.

- Files: `ConwayResearch/Underdog-Saluki-27B-1.0` `Underdog-Saluki-27B-1.0-IQ2-mix.gguf` 7,898,369,152 B
  sha256 `4a673518…`; `Kujira/Underdog-Saluki-27B-1.0-MTP-GGUF` `...-IQ2-mix-MTP.gguf` 8,349,689,920 B
  `98f6ebb5…` (Saluki weights + Qwen3.8-27B's own MTP head); `mmproj-...-Q8_0.gguf` `2e0b88b6…`. All verified.
- No smaller Saluki exists; it is already the smallest GSQ-RCO 27B (the rest start at 8.42 GB).
- Runtime: llama.cpp b11514 (`de7fa0a3c`), built from source for sm75.

## Measured (2026-10-09, 8 GB, desktop on the iGPU)

| Setup | VRAM | Decode | Notes |
|---|---|---|---|
| `-ngl 64` (all layers) | | | out of memory at load |
| `-ngl 60`, 16K, q8_0 KV | 7.8 GB | | out of memory on the first request (cuBLAS workspace) |
| auto-fit (no `-ngl`) | 6.6 GB | 6.1 tok/s | auto-fit is conservative |
| `-ngl 56`, 16K, q8_0 KV | 7.4 GB | 8.8-9.1 tok/s | |
| `-ngl 58`, 16K, q8_0 KV | 7.6 GB | 9.4-10.1 tok/s | |
| **`-ngl 59`, 16K, q4_0 KV** | 7.4 GB | **10.4-10.8 tok/s** | best short-prompt decode |
| `-ngl 57`, 16K, q4_0 KV, 3,240-token prompt | 7.5 GB | 9.1 tok/s | prefill 416 tok/s; the stable long-prompt setup |
| 32K context (ngl 51-58) | 7.2-7.7 GB | 1.0 tok/s | collapses; 16K is the practical max |
| MTP, `-ngl 48-52`, q4_0, draft 2 | 7.1-7.3 GB | 3.2-6.8 tok/s | acceptance 52-83%, but ~10 layers move to the CPU: slower than no MTP |

AG-Bench v2.2 (cap 900 s, thinking off, `-ngl 57`, 16K): **stopped after 2 tasks, 0/2** (task11 timed out at
900 s, which the Strata champion solves in 70-110 s; task10 failed in 43 s with 5 tool calls). Not continued: the
Strata Flash-Next 125B already scores 11/11 @ 1280 s at ~35 tok/s with 128K context, so Saluki could at best
tie on this suite while running ~4x slower. Its one advantage is ~1 GB of system RAM instead of ~34 GB.
Partial rows: `benchmarks/results/saluki-27b-iq2mix-v22-PARTIAL-stopped-*.jsonl`.

```bash
llama-server -m Underdog-Saluki-27B-1.0-IQ2-mix.gguf --jinja -fa on -c 16384 -np 1 -ngl 57 \
  -ctk q4_0 -ctv q4_0 --reasoning off
```
