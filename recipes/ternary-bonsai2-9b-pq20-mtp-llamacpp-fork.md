# Ternary-Bonsai-2-9B · PQ2_0 + built-in MTP (2.42 GB) · PrismML fork

**Status: 🔬 lab-verified — the new best 9B on this card, and the first 11/11
AG-Bench v2.2 run by a llama.cpp model.** PrismML's ternary compression of
Qwen3.5-9B (hybrid attention: 24 linear + 8 full-attention layers → cheap KV,
262K claimed), Qwen3.5-9B MTP head built into the served file.

- Weights: `prism-ml/Ternary-Bonsai-2-9B-gguf` — main
  `Ternary-Bonsai-2-9B-PQ2_0-MTP-Q8_0.gguf` 2.68 GB · sha256 `c79fcdfa…`;
  drafter `…-DFlash2-Q8_0.gguf` 1.57 GB · `95149abd…`; vision
  `…-mmproj-Q8_0.gguf` 0.62 GB · `e0cb6f69…` (all repo-SHA256SUMS-verified;
  SSD: `~/models/bonsai2-9b-dflash2/`, archive copy:
  `/mnt/archive/local-models/bonsai2-9b-dflash2/` sha-verified)
- Runtime: **not upstream llama.cpp** — PQ2_0/MTP/DFlash2 are fork types
  (upstream reads only this repo's Q2_0 packing). Built from a tarball of
  `PrismML-Eng/llama.cpp` branch **prism** (snapshot 2026-10-16, tarball
  sha256 `f5bc2360…`), host build, `CMAKE_CUDA_ARCHITECTURES=75`,
  `GGML_CUDA_FA=ON`, target `llama-server` — clean first try on SM75.
  (Fetch note: on a ~370 KB/s line `git clone` dies mid-pack and cannot
  resume; the branch tarball over `curl -C -` survives.)

## Measured on this box (2026-10-16)

| Metric | Value | Family context |
|---|---|---|
| Decode code-continuation / acceptance | **115.1 tok/s** · 0.927 · len 2.88 | 27B sibling: 55.3 · 0.74 |
| Decode novel prose / acceptance | **82.2–82.6 tok/s** · 0.468 · len 1.94 | 27B sibling: 49.1 · 0.55 |
| Filled 25K → prefill / decode-after | 1553 t/s (16 s) / 114.1 t/s | |
| Filled 50K → prefill / decode-after | 1346–1355 t/s (37 s) / 69.5–70.7 t/s | |
| Filled 101K → prefill / decode-after | **1068–1073 t/s (94 s) / 65.2–65.5 t/s** | first native-128K 9B on this card |
| AG-Bench v2.2 (128K serve) | **11/11**, wall 617 s, 64.1 pass/h | prior best on card: 10/11 |
| Multi-slot (4 concurrent, -np 4) | wall equals the 1-slot queue; per-client rates stay solo-class; acceptance 0.655 in batch | Strata-125B collapsed 36→8-9 t/s |
| Vision (mmproj Q8_0), receipt GT | 3.2 s cold, 779 t/s image prefill, 98.8 t/s decode, **5/6 GT** ("TOTALLE" header typo; every line item + total exact) | GLM-OCR 6/6 on same image |
| VRAM | 4.5 GB @ 32K f16 KV · 7.4 GB @ 128K K-q8/V-f16 · 6.1 GB @ 64K + mmproj | |

## Runtime quirks found on SM75 (cost real debugging time)

1. `--metrics` is **off by default** on this fork's server — add it or the
   decode harness gets empty spec counters.
2. **KV quant asymmetry**: `-ctk q8_0 -ctv q8_0` loads fine but the first big
   prefill aborts — `flash_attn_ext_f16 has no device code compatible with
   CUDA arch 750` for the q8_0-V variant, then CUDA launch failure → server
   death. **K-only q8_0 (`-ctk q8_0`, V stays f16) works** and is what makes
   128K fit in 8 GB next to the MTP context.
3. 128K f16 KV does not fit at all (cudaMalloc failure at load); 128K + mmproj
   doesn't fit either → vision serve drops to 64K.
4. **On-GPU KV context ceiling: 136K (K-q8_0) / 160K (K-q4_0)** (probed
   2026-10-16): q8_0-K loads to 139264 @ 7619 MiB, 147456 fails; q4_0-K
   loads to 163840 @ 7759 MiB, 192K fails even without the MTP drafter.
   262K is out of reach on 8 GB with any supported quant set — V cannot
   leave f16 on SM75. **q4_0-K is the recommend fit for the 128K serve**:
   same-fill A/B at 101K shows identical prefill (1068–1076 vs 1068–1073
   t/s), +2% decode-after-fill (66.6–66.7 vs 65.2–65.5 t/s), needle
   retrieval perfect in all runs, 524 MiB less VRAM (6847 vs 7371). On
   the precision concern: no measurable needle loss, and the fork ships
   `--kv-mean-center` (q4_0-K-only, softmax-invariant calibrated bias,
   see docs/kv-mean-center.md + tools/kv-mean-center) to recover further
   fidelity if real-corpus degradation ever shows up.
4. Bare `/completion` on huge prose prompts ends in instant EOS (0 predicted)
   — use `/v1/chat/completions` (or a chat template) for long-context probes.

## Drafter A/B: DFlash2 vs MTP d2 (32K)

| Arm | code | acc / len | novel | acc / len |
|---|---|---|---|---|
| MTP d2 | 115.1 | 0.93 / 2.88 | 82.4 | 0.47 / 1.94 |
| DFlash2 block drafter | 113.5–113.8 | 0.94 / **3.82** | 71.5 | 0.41 / 2.22 |

Matches the model card's own billing: DFlash2 pays nothing on code, −13% on
novel prose, and its drafts run deeper on copy-heavy prompts. **MTP d2 stays
the serve default on this card.** (A/B ran the DFlash2 drafter against the
MTP-bundled main — accepted by the fork — not the card-prescribed plain
PQ2_0 main; the pairing difference is recorded as an open item.)

## Capabilities

| Probe | Result |
|---|---|
| coding (exec-verified) | ✅ (fence-wrapped despite "only code") |
| tools + JSON precision | ✅ / ✅ |
| chat reasoning thinking OFF | ❌ wrong, muddled — unlike the 27B sibling, which passes |
| chat reasoning thinking ON | ✅ |
| long-context needle @ 25K/50K/101K | ✅ ✅ ✅ (all runs) |
| vision (receipt/dense-label/describe) | ✅ near-OCR-grade |

AG-Bench ran with the template's default thinking ON (as served); the same
harness and default were used for every model on the v2.2 board.

## Multi-agent verdict

This is the first measured model on this card where **server-side slots are
free**: 4 concurrent clients, 4 slots — same wall as the 4-client queue
(4.6 s), per-client decode at solo-class rates, speculative decoding still
active in batch mode (acceptance 0.66). The Strata-125B "never multi-slot"
verdict came from CPU-expert eviction; a fully GPU-resident 2.4 GB model
has nothing to evict. For parallel agent clients, `-np 4` is safe here.
Cost caveat: each interleaving agent still breaks the other's conversation
prefix cache (queue findings from the Strata session carry over: keep
turns short or accept re-prefill).

## Reproduce

```bash
# text serve (32K fast config, 4.5 GB VRAM):
llama-server -m ~/models/bonsai2-9b-dflash2/Ternary-Bonsai-2-9B-PQ2_0-MTP-Q8_0.gguf \
  --alias local-model --host 127.0.0.1 --port 8080 -ngl 99 -fa on -c 32768 \
  --spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-n-min 0 --spec-draft-p-min 0 \
  --jinja --metrics
# 128K long-context config (6.8 GB VRAM): add -c 131072 -ctk q4_0   (K only; q4 beats q8 here)
# 4-slot agents: add --parallel 4                                     (fits under either -ctk)
# vision (64K + mmproj, 6.1 GB): add -c 65536 -ctk q8_0 \
#   --mmproj ~/models/bonsai2-9b-dflash2/Ternary-Bonsai-2-9B-mmproj-Q8_0.gguf
```

Evidence: [evidence/ternary-bonsai2-9b.jsonl](../evidence/ternary-bonsai2-9b.jsonl) ·
[decode](../benchmarks/results/bonsai9b-mtp-d2-20261016.jsonl) ·
[longctx](../benchmarks/results/bonsai9b-longctx-20261016.jsonl) ·
[AG-Bench](../benchmarks/results/bonsai9b-128k-v22-20261016-041429.jsonl) ·
[multislot](../benchmarks/results/bonsai9b-multislot-20261016.jsonl) ·
[vision](../benchmarks/results/bonsai9b-vision-20261016.jsonl) ·
[dflash A/B](../benchmarks/results/bonsai9b-dflash-drafter-20261016.jsonl)

## Verdict

Adopt: this is the card's best coding-agent serve today — perfect v2.2 score
at 64 pass/h, 115 t/s decode, real 128K context, free multi-slot, and it
even carries vision. Deductions: reasoning needs thinking-ON (slower turns),
V-cache can't be quantized on SM75 with FA (K-only q8_0), and 128K + vision
don't co-fit. The 27B sibling stays the no-thinking pick; everything else on
the card serves slower.

## Storage

SSD workbench copies at `~/models/bonsai2-9b-dflash2/` while the slot is
active; archive originals at `/mnt/archive/local-models/bonsai2-9b-dflash2/`
(sha-verified first copy, 2026-10-16). Rotate off SSD when superseded.