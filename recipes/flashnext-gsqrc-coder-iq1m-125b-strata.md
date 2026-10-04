# Flash-Next GSQ-RCO Coder IQ1_M (ISTA-DASLab, 50% expert-pruned) · Strata v0.1.38 — the pruning answer

**Status: 🧪 lab-tested (bench tier)** — the published analog of the pruning-vs-quantization
question. Short answer: **equal quality, ~35-40% slower decode — squeeze-everything wins
at this size class.**

- Weights: `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` IQ1_M — shard-1
  29,608,446,496 B sha256 `e11083ba…` (50% expert-pruned: 256/512 routed experts,
  ~1.89 bpw effective), shard-2 28,800,138,432 B sha256 `316b46f3…` — **byte-identical
  to the base's PLE n-gram shard** (hardlink dedupe, 28.8 GB saved on SSD).
- Engine: Strata v0.1.38 (worktree strata-0138), pack `packs/iq1m-coder`
  (1079 tensors, 302 native, 1.37 GiB arena), shipped `data/expert-profile-coder.bin`
  (48×256 — the base profile 48×512 is REJECTED at load), `--ple-io mmap`, kv int8,
  `--spec 4 --spec-min-p 0.5 --prefill auto:16384 --mtp mtp/rt`.
- mmproj note: our copy of `mmproj-Qwen3.8-Flash-Next-BF16.gguf` (sha `19ef347e…`) does NOT
  match either DASLab repo's current `b1a82259…` — the projector was re-uploaded after our
  fetch (or the old v1-era copy is corrupt at same size). Vision probe pending a verified copy.

## Measured (2026-10-04, single run, cap 600)

| Phase | Value |
|---|---|
| 4 probes (riddle / code / CoT / factual) | **4/4 PASS** — reasoning chain INTACT at ~1.89 bpw effective |
| AG-Bench | **9/11** @ 2061 s (15.7 p/h) — inside the full-quant base's 8–10 band; fails {task2-React, task5-TS}; PASSED task8 (which the same-day base run failed — band flip) |
| Decode | 21.7–27.4 tok/s (base Q2_0: 36–41) |
| MTP acceptance (base's Q2_0 head over pruned weights) | **0.70–0.80** — same-family head survives expert-pruning (cross-family grafts scored 0.000) |
| Context / footprints | 16K · 4.6 GB VRAM · ~31 GB DRAM-class |

## The verdict

Pruning half the experts and keeping survivors at IQ1_M scores like the full-quantized
Q2_0-GSQ+RCO base but decodes a third slower in this serving (expert-cache economics +
IQ1_M dequant cost). Neither quality NOR speed gained — the compressed-full model stays
the record row. The one pruning win: hardware diversity (small machines that can't host
512-expert routing at all can host this).

## Reproduce

```bash
cd ~/Desktop/github/strata-port
python3 -m serve.server --engine strata --config strata-coder-iq1m.json --port 8080
bash ../local-ai-rtx2080/benchmarks/agentic-bench.sh strata-coder-iq1m-125b 600
```

Evidence: [evidence/strata-q20-sm75-port.jsonl](../evidence/strata-q20-sm75-port.jsonl)
(coder_iq1m_125b_chain — verbatim probes + per-task rows) ·
results/strata-coder-iq1m-125b-20261004-133816.jsonl · baseline: the base's
⁽⁶⁾ row on the same engine the same day.

## Storage

`~/models/flashnext-coder/` (59.2 GB incl. the hardlinked PLE shard); rotate to
`/mnt/archive/local-models/` when space is needed.