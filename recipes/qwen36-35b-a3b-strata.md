# Qwen3.6-35B-A3B UD-Q4_K_XL · Strata 0.1.45 — the first qwen36 row and a perfect v2.2

## Runtime: Strata v0.1.45 (2026-10-17)

Stock tag `v0.1.45` built for sm_75 (worktree `strata-0145`, two builds: `build-turing-0145`
standard and `build-turing-0145-kq` with `STRATA_MMQ_KQUANTS=ON`; ggml pin unchanged at
`llamacpp-3cf03257`). This release is upstream's Qwen3.6 engine-speed release: the qwen35
engine path got rewritten decode/prompt kernels, bit-exact against the old ones
(`STRATA_Q36_VERIFY=1`).

Weights: Unsloth `Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf` (22.85 GB, sha256 `55983c5a75a1ab96...`,
found pre-staged on /mnt/archive from 2026-10-15; no re-download needed) plus `mmproj-F16.gguf`
(0.9 GB, unused so far: vision off in this config). SSD copy in `~/models/qwen36-35b-a3b/`.

## Why the standard build, not the kq one (NEXT-IDEAS plan falsified on 8 GB)

The plan's "second sm_75 build with `STRATA_MMQ_KQUANTS=ON`" assumed room for the kquants
int8 MMQ prompt path. Measured: both builds ship `libstrata_kq.so` next to the binary and the
engine auto-loads it; the path needs a **fixed 1159 MiB staging pair** (two full expert layers,
int8) that a card with 4.4 GiB dense + fp32 KV can never spare. With the plugin loaded every
boot dies with "not enough VRAM left for the hybrid experts' buffers and slots (1159 MiB
needed, 682-692 MiB free)". Fix: move `libstrata_kq.so` aside in the standard build dir
(kept as `libstrata_kq.so.disabled`); the engine then runs "the native grouped kernels" FP16
prompt path, identical to upstream's own RTX 3060 hybrid runs. The kq build dir stays intact
for a future bigger card.

**Serve config** ([strata-qwen36-a3b-tailnet.json](strata-configs/strata-qwen36-a3b-0145-tailnet.json)):
`--native <gguf> --max-context 16384 --prefill auto --mtp 2 --expert-slots 10`, host
100.110.49.114 (bench runs bind 127.0.0.1:8080 per the harness convention), `--port` passed on
the CLI (config's port key is ignored; pass 8080).

## The co-fit ladder on 8 GB (all measured)

| Attempt | Verdict |
|---|---|
| 32K ctx, no expert budget | cudaMalloc OOM at boot |
| 32K ctx, `--expert-vram 4.5` | OOM: staging + fp32 KV (1.44 GB/32K) don't fit with dense |
| 16K ctx, `--expert-vram 1.0` | "1159 MiB needed, 692 free" (plugin staging again) |
| 16K ctx, kq plugin disabled, `--expert-vram 0.6` | boots: 2/256 experts per layer (0.15 GiB), rest pinned in RAM |
| `--expert-vram 2.5` → `4.5` | placement saturates at 5/256 (0.37 GiB): budget past ~2 GiB changes nothing |
| `--expert-slots 10` | **10/256 per layer (0.73 GiB)**; the explicit flag beats the budget knob |
| `--expert-slots 10` + `--prefill 1024` | boots, 5 slots only, decode drops: reverted |
| `--prefill 2048` + `--expert-slots 4` | "428 MiB needed, 311 free": chunk and slots compete for the same tail |

Standing config: **16K ctx, chunk auto (→512), 10 slots, 0.91 GiB headroom**. KV is fp32 on this
engine path (45 KB/token, 11 layers incl. the MTP block) so 64K+ contexts are unreachable on
the card (upstream's own recommendation for ≤16 GB cards is 32K, which co-fit needs the
experts' room).

## Speeds (i5-9600K + 8 GB, hybrid: 18.75 GiB experts pinned in host RAM)

| Probe | Range (not best-of) |
|---|---|
| Solo greedy decode (MTP on, 57-59% drafts accepted) | 30.7-32.6 tok/s |
| Solo decode, default sampling (drafts off) | 21.8-25.2 tok/s |
| 8 concurrent chats (batch, no drafts) | 22.5-30.2 tok/s each (~200 tok/s aggregate) |
| Prefill 1.8K | 89-109 tok/s |
| Prefill 11.2K | 88.3 tok/s (cuBLAS chunks + 6-thread CPU expert pool) |

The wall is the CPU expert pool: an i5-9600K has 6 physical cores (no SMT, non-hybrid, so
`--pool-workers` stays at the engine's own 6). Chunk size 512 vs 1024 changed nothing (each
expert read already batches rows); upstream's 3060-class numbers (60-85 tok/s decode, 2000
prefill) came from 20 CPU threads and 37/256 slots. Up vs Qwen3.5-35B-A3B IQ2_XXS on llama.cpp
(40 tok/s, 1040 prefill): decode faster, prefill ~10x slower.

**Trap: the model card's sampling kills MTP.** `MODEL_CARD_SAMPLING["qwen35moe"]` injects
`temperature 0.7/1.0, top_p, top_k 20, presence_penalty 1.5` when a request doesn't override;
`presence_penalty` forces `needs_logits()` in the engine and the request loses its drafts
(0 of 0) and ~25% speed. Greedy = `"temperature":0, "presence_penalty":0, "frequency_penalty":0`
in the request.

## AG-Bench v2.2: **11/11 at 1368 s (28.9 pass/h, 900 s cap)**

First Qwen3.6 row on the bench, and the first perfect Strata-engine run on this card.
All 11 passed with `suspect_garbage_pass: false`:
task10 (215 s, the notorious bank filter that overflowed 16K on Flash-Next 0.1.44, passed
first try), task11 148 s, task1 98 s, task2 137 s, task3 84 s, task4 67 s, task5 103 s,
task6 165 s, task7-long-context 132 s, task8 130 s, task9 89 s.
Raw: `benchmarks/results/qwen36-35b-a3b-strata-0145-20261017-113931.jsonl`.
Needle sanity: `violet-harbor-731` retrieved from 10.5K of context; OpenAI tool-call round trip
correct. Harness ran with thinking-default sampling (pi's plain requests), i.e. not the greedy
drafts path.

## Reproduce

```bash
cd ~/Desktop/github/strata-0145
python3 -m serve.server --engine strata --config strata-qwen36-a3b-tailnet.json --port 8080
bash $THIS_REPO/benchmarks/agentic-bench.sh qwen36-35b-a3b-strata 900   # serve bound to 127.0.0.1:8080 for runs
```

## Storage

SSD: `~/models/qwen36-35b-a3b/` (23.7 GB pair + sha); archive: `/mnt/archive/local-models/qwen36-35b-a3b/`.
Evidence: [experiments/evidence/qwen36-35b-a3b-strata.jsonl](../experiments/evidence/qwen36-35b-a3b-strata.jsonl).