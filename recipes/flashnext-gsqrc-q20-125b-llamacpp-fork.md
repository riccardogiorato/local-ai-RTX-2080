# Flash-Next GSQ-RCO Q2_0 (ISTA-DASLab, 2.40 bpw) · patched llama.cpp — the reasoning-intact 125B boundary

**Status: 🔬 lab-verified (probe tier)** — the first ≥2.2 bpw sub-40 GB Flash-Next
artifact, and the reasoning chain SURVIVES where the 1.80 bpw UltraLite's broke.
Not agentic-usable yet (no MTP heads exist for this model; novel-prefill class
is crippled by the PLE shard).

- Weights: `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF` Q2_0 tier
  (backbone 37,623,740,192 B sha256 `69820c02…` + PLE shard 28,800,138,432 B
  sha256 `316b46f3…`, both verified). GSQ = Gumbel-Softmax Quantization,
  RCO = Riemannian Constrained Optimization (per-tensor type assignment);
  standard GGUF — runs unmodified on the qwen4exp-patched runtime.
- Engine: llama.cpp `250b61446` (the UltraLite's patched qwen4exp fork — no
  physical-repack patch needed for this artifact; llama.cpp splits auto-load
  from shard 1)
- Node: no MTP/nextn tensors exist anywhere for Flash-Next (as of 2026-10-01).

## The boundary record (why this recipe exists)

| Tier | bpw | Reasoning chain | Decode | Class |
|---|---|---|---|---|
| UltraLite 37GiB | 1.80 | **BROKEN** (EOS-at-reasoning-close; thinking/coding/retrieval empty) | 12.5 tok/s | boundary-fail |
| **GSQ-RCO Q2_0** | 2.40 | **INTACT** — all four probe classes answer correctly | 8.1–8.3 tok/s | boundary-pass |

The sub-2 bpw wall is now confirmed from both sides: compression class alone
determines whether the 125B's reasoning chain survives on this stack.

## Measured (2026-10-01, probes + measure-decode, pinned temp0/seed42)

| Phase | Value |
|---|---|
| Reasoning probes (riddle / code / retrieval / general) | **4/4 PASS**, healthy completion lengths |
| Decode (code / novel) | 7.9–8.1 / 8.1–8.3 tok/s |
| Prefill (code / novel) | 140–151 / **8.8–9.5 t/s** ← the crippled class |
| Context served | 4096 (46 GiB RAM hosts 37.6 hot + PLE on mmap) |

Novel-prefill ~9 t/s is PLE-shard random access through mmap: a
4K-token novel prompt costs minutes — agent-hostile, and why no AG-Bench
run was made. Community caveat: HF discussion 14 reports quality
degradation vs official Alibaba weights; probes disagreed but treat quality
claims with single-session caution.

## Reproduce

```bash
systemd-run --user --scope -p MemoryMax=42G \
  llama.cpp-qwen4exp/build/bin/llama-server \
  --model …Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf \
  --alias local-model --host 127.0.0.1 --port 8080 \
  -c 4096 -b 512 -ub 512 -np 1 --jinja --metrics \
  --temperature 0 --seed 42
```

Chat requests **must pass** `chat_template_kwargs {"enable_thinking": false}`
(same requirement as the UltraLite run).

## What would unlock the agentic tier

A Flash-Next MTP head GGUF anywhere in the ~4 GB class (agentionai published
MTP heads for other families) would put spec decode on this artifact; the
maths then are RAM (the PLE shard competes with the drafter) and the
novel-prefill wall. Watch jmarceno/agentionai/z-lab.

Evidence: [evidence/flashnext-gsqrc-q20-reasoning.jsonl](../evidence/flashnext-gsqrc-q20-reasoning.jsonl) ·
measurements/flashnext-gsq-rco-q20-2026-10-01.txt · prior boundary-fail:
[recipes/flashnext-ultralite-125b-llamacpp-fork.md](flashnext-ultralite-125b-llamacpp-fork.md)

## Storage

SSD workbench copy at `~/models/flashnext-gsq-rco/` (66.4 GB pair + sha.txt);
rotate to `/mnt/archive/local-models/` when the SSD needs the space.