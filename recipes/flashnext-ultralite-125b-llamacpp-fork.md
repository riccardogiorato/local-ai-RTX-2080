# Qwen3.8-Flash-Next-125B UltraLite (0xKitkat, 1.80 bpw) — first 125B on this card

**Status: 🔬 lab-verified boundary record** — the largest model class ever served
here (125B total / ~6B active MoE, Qwen4-experimental architecture), at
**12.5 tok/s steady** on DDR4-2400 — but the 1.8 bpw repack breaks the reasoning
chain, so this is a *frontier-shaped, mid-tier-behaving* artifact. The run maps
the 8 GB + 48 GB recipe class for 30GB+ artifacts — and the sub-2 bpw wall.

- Weights: `0xKitkat/Qwen3.8-Flash-Next-125B-UltraLite-37GiB-GGUF` @ `4f38b5eb`,
  3 shards, 39.7 GB total (per-shard SHAs verified; manifest included)
- Runtime: **patched llama.cpp** — base `250b61446` + the release's
  `patches/qwen4exp-under40.patch` (applies clean; needed for the padded Q1_0
  physical layout of the 29 GB PLE n-gram table). Built host-side,
  `CMAKE_CUDA_ARCHITECTURES=75`. Repo: `~/Desktop/github/llama.cpp-qwen4exp`
- The patch's structural removals + mixed Q1_0/Q2_0 crush = **no thinking mode**
  (emits EOS at reasoning close; `--jinja` mandatory, `--reasoning-preserve`
  doesn't repair it), and coding degrades — riddle/tools/coherence fine
  (thinking-off path)

## The recipe

```bash
systemd-run --user --scope -p MemoryMax=42G \
  llama.cpp-qwen4exp/build/bin/llama-server \
  --model …Qwen3.8-Flash-Next-125B-UltraLite-37GiB-00001-of-00003.gguf \
  --alias local-model --host 127.0.0.1 --port 8080 \
  -c 4096 -b 512 -ub 512 -np 1 --jinja --metrics
```

No tensor overrides: mmap places the 37 GiB in the 46 GiB page cache; the
loader defaults park the shared layers + KV in ~6.6 GiB VRAM. Chat requests
**must pass `chat_template_kwargs {"enable_thinking": false}`** — the default
thinking path is the broken one (empty answers).

## Measured (2026-09-27, 2400 MT/s era)

| Phase | Value |
|---|---|
| Decode (both classes) | **12.0–12.5 tok/s** — faster than the dense-27B ThinkingCap cram (9.57) |
| Prefill (code/novel) | 218–233 / ~18 tok/s |
| VRAM | 6.6 GiB + ~37 GiB page cache |
| Cold first answer | 5.1 s (37 GiB streaming in) |
| AG-Bench | deferred — pi lacks per-request thinking-kwargs plumbing; default path flatlines |

## The science

- **Two records**: first 125B-class serve on an 8 GB card; the 0.0502 GB/param
  efficiency point of the whole ledger.
- **The sub-2 bpw wall, mapped twice in one night** (IQ1_S: reasoning loops to
  empty answers; this: EOS-at-reasoning-close): at today's quant state, below
  ~2 bpw the reasoning chain breaks *even on frontier architectures*, while
  surface tasks survive. Bonsai's 1.75 bpw ternary is the known exception —
  curated quantization ≠ crushed quantization.
- **The 78 GB question your RAM decision hinges on: answered.** This 37 GB
  artifact genuinely needs >32 GB (the PLE table's random access pattern reads
  the whole file continuously). 48 GB at 2400 runs it; 32 GB at 3200 would
  stream it from SSD.

## Retry triggers

1. An UltraLite v2 or any sub-40 GB artifact at ≥2.2 bpw **with MTP and intact
   reasoning** → immediate re-run, recipe slot candidate
2. Strata's Q2_0-GSQ-RCO quality tier → needs sm_80+ (filed separately)
3. AG-Bench with forced-off thinking (pi proxy injecting the kwarg) if the
   non-thinking numbers are wanted anyway

Evidence: [evidence/flashnext-ultralite-125b.jsonl](../evidence/flashnext-ultralite-125b.jsonl)