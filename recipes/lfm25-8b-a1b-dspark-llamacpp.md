# LFM2.5-8B-A1B · Q4_K_M + DSpark sidecar · llama.cpp — the speed-slot record, an agent-slot failure

**Status: 🔬 lab-verified** — the registry's 8 GB-class star (276.3 tok/s claimed on RTX 3070
Ti), first resident-MoE recipe on this card, and the debut of the sidecar class we could
never fit before (186 MB drafter vs DFlash2's 1.9 GB). Both halves of the verdict land in
the extremes.

- Main: `LiquidAI/LFM2.5-8B-A1B-GGUF` Q4_K_M 5,146,246,231 B · sha256 `4923ec14f06b968b…`
- Drafter: `LiquidAI/LFM2.5-8B-A1B-DSpark-GGUF` Q4_K_M 199,686,568 B · sha256 `017278ec44096718`
  — a 0.19 GB DSpark sidecar: the size class the DFlash2 campaign proved this card needed
- Engine: llama.cpp `0.4.1-dev b11118 / e6ab7c1a4`, digest-pinned docker

## Measured (2026-09-25, 32K full-resident, 7.05 GB incl. sidecar)

| Class | Decode | DSpark acceptance (mean len) |
|---|---|---|
| Repetitive | **221.3 tok/s** | 0.489 / 0.540 (2.93 / 3.16) |
| Novel prose | **200.4 tok/s** | 0.447 (2.79) |

**Both classes clear 200 tok/s — the fastest text decode ever measured on this card**
(1.22× Gemma E4B's repetitive 181; 1.33× its novel 151). Prefill steady ~500 tok/s.

## Capabilities — 3/3, always-thinking caveat

chat ✓ (trains riddle correct), coding ✓ (exec-verified), tools ✓ + continuation. **Its
template ignores `enable_thinking: false`** — reasoning always produced; needs ≥600-token
budgets. The 300-token harness probe fails on budget, not reasoning quality.

## AG-Bench: **0/6** — the record low, and the mechanism owns the trade

3 of 6 tasks: never picks up a tool (2–9 s, zero calls) — it reasons, closes the turn, done.
The engaged 3 don't reach green within cap. **Fastest decode + always-thinking = the card's
first true non-agent.**

### Harness-hazard finding (persistent)

The task6 run **escaped its work directory** and edited the master task source in the repo
(absolute-path edit; git-reverted immediately, nothing committed). The runner now
restores task sources from git around every task (`restore_master_if_dirty` in
`agentic-bench.sh`); recorded in `benchmarks/README.md`.

Evidence: [evidence/lfm25-8b-a1b-q4km-dspark.jsonl](../evidence/lfm25-8b-a1b-q4km-dspark.jsonl),
[benchmarks/results/lfm25-8b-a1b-q4km-dspark-20260925-173454.jsonl](../benchmarks/results/lfm25-8b-a1b-q4km-dspark-20260925-173454.jsonl)

## Reproduce

```bash
sudo docker run --gpus all -p 8080:8080 -v ~/models/lfm25-8b-a1b:/models:ro -d \
  ghcr.io/ggml-org/llama.cpp:server-cuda12-b11118@sha256:bfb3264fc2166e01e2b4f9b537e45d7006d87c75021b911f132ef607f5bbced3 \
  --model /models/LFM2.5-8B-A1B-Q4_K_M.gguf --alias local-model \
  --host 0.0.0.0 --port 8080 --ctx-size 32768 --parallel 1 --n-gpu-layers 999 \
  --flash-attn on --cache-type-k q8_0 --cache-type-v q8_0 --jinja \
  --temperature 0 --seed 42 \
  --spec-type draft-dspark --spec-draft-model /models/LFM2.5-8B-A1B-DSpark-Q4_K_M.gguf \
  --spec-draft-n-max 4
```

## Verdict and slots

- **Speed slot: new record** — bulk generation, drafting assistance, fast chat, long-context
  summarization: the fastest resident option measured on 8 GB.
- **Agent slot: disqualified** — thinking-first burns agent turns deciding instead of acting.
- The **0.19 GB sidecar class finally works here** — the path the DFlash2 campaign identified.

## Storage

SSD `~/models/lfm25-8b-a1b/` (~4.99 GB) while in active use; rotates per the storage rule.