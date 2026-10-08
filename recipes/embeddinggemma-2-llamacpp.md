# EmbeddingGemma-2 (unsloth GGUF) embeddings, llama.cpp on SM75

**Status: lab-verified, utility tier.** Google's embedding model (768-dim, normalized), for search and
retrieval. Text measured here; the repo also ships image/audio projectors (`mmproj-*`), not tested yet.

- Weights: `unsloth/embeddinggemma-2-GGUF`, six tiers all verified against the HF manifest:
  BF16 557,950,240 B `f315cbbb…8aa4f` · F16 `0d435086…d0901` · Q8_0 309,855,520 B `6f1bd4ac…bc` ·
  UD-Q6_K_XL 248,812,032 B · UD-Q5_K_XL 210,055,680 B · UD-Q4_K_XL 175,673,856 B `ea905fd0…19493`
- Runtime: llama.cpp b11459 Docker (`server-cuda` @ `sha256:fff6185e…264f4`)

```bash
llama-server --model embeddinggemma-2-Q8_0.gguf --embedding --ctx-size 8192 --parallel 4 \
  --batch-size 8192 --ubatch-size 8192 --n-gpu-layers 999 --flash-attn on
# queries: "task: search result | query: <q>"   documents: "title: none | text: <doc>"
```

## Measured (2026-10-09)

Retrieval test: 149 chunks (~220 words) of this repo's own markdown; each query is a 12-word span from
the middle of its chunk. Agreement columns are against BF16.

| Tier | Size | VRAM | Query latency (median) | recall@1 | MRR | cos to BF16 (mean / min) | top-10 overlap |
|---|---|---|---|---|---|---|---|
| BF16 | 558 MB | 1.48 GB | 13.1 ms | 0.403 | 0.537 | 1 / 1 | 1.000 |
| F16 | 558 MB | 1.48 GB | 8.1 ms | 0.403 | 0.535 | 1.00000 / 0.99999 | 0.998 |
| Q8_0 | 310 MB | 1.37 GB | 9.4 ms | 0.409 | 0.539 | 0.99983 / 0.99968 | 0.981 |
| UD-Q6_K_XL | 249 MB | 1.34 GB | 9.6 ms | 0.416 | 0.541 | 0.99919 / 0.99868 | 0.950 |
| UD-Q5_K_XL | 210 MB | 1.32 GB | 9.7 ms | 0.389 | 0.532 | 0.99816 / 0.99626 | 0.917 |
| UD-Q4_K_XL | 176 MB | 1.30 GB | 9.0 ms | 0.416 | 0.535 | 0.99371 / 0.98635 | 0.850 |

- Retrieval quality is flat across tiers (differences are noise at 149 queries). The vectors drift
  steadily as the tier shrinks: Q8_0 keeps 98% of BF16's top-10 neighbours, Q4 85%. **Q8_0 is the
  default**; Q4 if 130 MB matters.
- BF16 is the slowest single query (Turing has no native BF16); use F16 or Q8_0 instead.
- Throughput tops out near **12.7 docs/s, ~6.5K tok/s** (~510-token docs, Q8_0, `--parallel 4`,
  8 concurrent requests); one 128-doc request on one slot gives 4.5 docs/s. It is the same for every
  tier, so the ceiling is server scheduling, not weights.

Evidence: [evidence/embeddinggemma-2.jsonl](../evidence/embeddinggemma-2.jsonl)
