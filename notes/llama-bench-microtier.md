# llama-bench micro-tier rows (2026-09-26) — internet-comparable numbers

The ledger's decode/prefill figures are **server-reported rates on our fixed prompt
classes** — internally consistent but not directly comparable with public llama-bench
tables. These rows close that gap: plain `llama-bench` invocation, no speculative
decoding (llama-bench has no spec support in either build), 2 repeats, ± shown.

Flags shared by all rows: `-ngl 99 -fa on -p 512 -n 32,128 -r 2`.

| Model | Build | KV | pp512 tok/s | tg32 tok/s | tg128 tok/s |
|---|---|---|---|---|---|
| Ternary-Bonsai-2-27B PTQ1_0-MTP (1.75 bpw) | fork @ 285542d, `GGML_CUDA_BATCH_INVARIANT=1` | q4_0 | **574.8 ± 14.0** | **43.74 ± 0.31** | **44.39 ± 0.06** |
| Qwen3.5-4B Q4_K_M | xing4_0-port @ 63c16fb (upstream-lineage bench) | f16 | **2669.3 ± 105.1** | **104.0 ± 0.7** | **105.5 ± 0.15** |
| Qwen3.5-9B Q4_K_M | xing4_0-port @ 63c16fb | f16 | **1754.6 ± 47.1** | **65.2 ± 0.4** | **65.8 ± 0.07** |

Read-across to the server-class numbers (why both exist):

- 9B no-draft tg128 = 65.8 → its server-measured MTP d4 = ~124 tok/s: the
  embedded-head speculation nearly doubles it — the multiplier is the interesting
  cross-engine number, and only the server method can see it.
- 4B same story: 105.5 no-draft vs ~182 server-measured with MTP.
- Bonsai-2's no-draft 44.4 → 55.3 at d2 (+24%): the #218 verify kernel is what makes
  d2 profitable; per-token verification here is cheaper than the dense models' — the
  ternary mat-vec cap pays inside the verify batch too.

The docker `full-cuda-b11118` image's `/app/llama-bench` is a multi-call wrapper that
misdispatches (prints the convert/quantize usage) — the host-built fork binary is the
working path; recorded so nobody re-fights that wrapper.