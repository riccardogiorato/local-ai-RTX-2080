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

## Draft-depth A/B (2026-09-26) — d2 is the new serve depth

The recipe inherited `--spec-draft-n-max 1` from pre-#218 economics; with the
batch-verify kernel at our pin (285542d = the PR #218 head), d-depth was re-A/B'd
on SM75 with the shared harness (`benchmarks/measure-decode.sh`, 2 runs × both
prompt classes, temp 0):

| depth | code-continuation | novel prose | acceptance (code/novel) |
|---|---|---|---|
| d1 (old) | 49.0 tok/s | 48.6 tok/s | 0.81 / 0.73 |
| **d2 (new)** | **55.3 tok/s** | **49.1 tok/s** | 0.74 / 0.55 |
| d3 | 51.3 tok/s | 43.4 tok/s | 0.63 / 0.46 |

d2 = **+12.9% on repetitive, novel flat** (under the harness accounting); d3 pays
more than it gains. AG-Bench at d2: **4/6, identical pass set** to the d1 bench —
the upgrade is pure speed. Reproduce line below now carries `--spec-draft-n-max 2`.

## Trained-head-on-PTQ1_0 — FALSIFIED, cause proven by control (2026-09-26)

ProCreations' head *trained on hidden states* (849 MB BF16 safetensors,
`7a4a18b2…`) spliced onto our PTQ1_0 base (byte-level head swap, all 15 tensors
verified) → main model coherent, wiring verified identical to their runtime (the
Hadamard-inverse patch is already in our fork lineage), yet MTP acceptance
**exactly 0.000**. The control run on their own PQ2_0-MTP combined file accepts
at **0.717/0.585** on the same fork — proving the head binds to the PQ2_0
hidden-state distribution it was trained on and does not transfer to PTQ1_0 at
all. Their TRAINING.md confirms: features were collected from the PQ2_0 base.
**PTQ1_0 keeps the raw Qwen3.8-27B graft at d2.** Also measured while there:
PQ2_0-MTP partial offload on 8 GB (ngl 46, ctx 4096) decodes at **2.2 tok/s** —
the PQ2_0 tier stays blocked on this card, more brutally than predicted.

Splice-tooling note (for anyone re-attempting): GGUF tensor data offsets are
**relative to the aligned start of the data section**, not absolute file
positions — treating them as absolute corrupts the header region (caught by a
generation-coherence probe; script kept with the archive).

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
  --reasoning-effort medium --spec-type draft-mtp --spec-draft-n-max 2
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