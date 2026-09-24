# Ternary-Bonsai-2-27B · PTQ1_0 (1.75 bpw) + grafted MTP · PrismML-lineage llama.cpp fork

**Status: 🔬 lab-verified — and the verdict overturner.** Parked for a week on
"ternary might be too dumb" community reports; benched on insistence of actual
measurement, and the data says otherwise: Bonsai-2 ties its dense 27B family on every
test we can run while being **5–6× faster than every other 27B measured on this card.**

- Weights: PrismML's ternary compression of **dense Qwen3.8-27B** `(−1,0,+1)` trits
  packed at 1.75 bpw — main `PTQ1_0.gguf` 5.54 GB · sha256 `53107f53…`; served file is
  the **MTP graft** (`sudoingx/Ternary-Bonsai-2-27B-PTQ1_0-MTP-GGUF` lineage: the
  Qwen3.8-27B multi-token-prediction head grafted as block 64) 5.96 GB · sha256
  `ec03ef6e…`; source repo claims 84.78 avg on 14 thinking benchmarks vs 72.59 for a
  conventional IQ2_XXS
- Runtime: **NOT upstream llama.cpp and NOT docker** — PTQ1_0 is tensor-type enum 143
  (fork-only); upstream b11118 refuses the file at the tensor-info table. Runtime is
  `sudoingX/llama.cpp` branch **bonsai2** @ `285542d98d37…` (PrismML fork lineage with
  the improved ternary batch-verify kernel), built as a host binary with
  `CMAKE_CUDA_ARCHITECTURES=75` — **builds and runs on SM75 first try**

## Measured on this box (2026-09-25)

| Metric | Value | Family context |
|---|---|---|
| Decode repetitive / acceptance | **59.3 tok/s** / 1.000 (len 2.0) | ThinkingCap Q2_K: 9.57; dense DT-IQ2_S: 4.6–5.3 |
| Decode novel prose / acceptance | **49.9 tok/s** / 0.659 (len 1.66) | ThinkingCap: 6.6; dense: n/a |
| VRAM | **7.31 GB full offload** (8K ctx + drafter) | every other 27B needs CPU sacrifice |
| Context ceiling (with MTP) | 8K (32K KV alloc fails at load) | |

The only **fluid-offload 27B on this card**: no CPU in the decode path.

## Capabilities

| Probe | Result |
|---|---|
| chat reasoning (thinking OFF) | ✅ — joins ThinkingCap as the only two models passing this probe without thinking (Qwen3.5-4B and Gemma-off fail it) |
| coding (exec-verified) | ✅ |
| tools + continuation | ✅ |
| chat reasoning (thinking ON) | ✅ — "Less, because the Florence-to-Rome train takes 90 minutes (09:15 to 10:45)…" in 3.9 s |

## AG-Bench: **4/6**

Passes JS bugfix (41 s), **date-fns upgrade** (95 s), python bugfix (14 s), pagination
(64 s); fails the same two tasks as its dense Qwen3.8-27B siblings (React markup
contract, JS→TS migration) — a family trait, not a ternary one.

Evidence: [evidence/ternary-bonsai2-27b-ptq1_0.jsonl](../evidence/ternary-bonsai2-27b-ptq1_0.jsonl),
[benchmarks/results/ternary-bonsai2-27b-20260925-002214.jsonl](../benchmarks/results/ternary-bonsai2-27b-20260925-002214.jsonl)

## Reproduce

```bash
git clone --depth 1 -b bonsai2 https://github.com/sudoingX/llama.cpp && cd llama.cpp
cmake -S . -B build -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=75
cmake --build build -j6 --target llama-server          # pinned: 285542d98d37…

GGML_CUDA_BATCH_INVARIANT=1 ./build/bin/llama-server \
  --model ~/models/bonsai-27b/Ternary-Bonsai-2-27B-PTQ1_0-MTP-Q8_0.gguf --alias Bonsai2-MTP \
  --host 0.0.0.0 --port 8080 -ngl 99 -fa on -c 8192 -np 1 -ctk q4_0 -ctv q4_0 --jinja \
  --reasoning-effort medium --spec-type draft-mtp --spec-draft-n-max 1
```

## Verdict

If you can accept the fork runtime and 8K context: **this is the best 27B experience on
the card, full stop** — 50–60 tok/s, fully resident, ties the family on intelligence.
For 32K context or upstream-engine purity, fall back to ThinkingCap Q2_K (9.57 tok/s
with the same family fail signature) or the dense cram.

## Storage

Both files restored 2026-09-25 from (and originals kept at)
`/mnt/archive/local-models/{bonsai-2,bonsai-2-mtp}/`; SSD workbench copies live at
`~/models/bonsai-27b/` while the slot is actively used, and rotate back when
superseded.