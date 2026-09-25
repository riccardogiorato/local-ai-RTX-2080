# GLiNER 2.5 multi-v1 (fastino) — schema-based extraction, pip/PyTorch on SM75

**Status: 🔬 lab-verified** — first typed-extraction model on the ledger: one 287M
multilingual encoder that does entities, classification, relations, and structured
records, with **label definitions passed in the request** (zero-shot labels). Same
utility tier as kev/laya: a Python serve, not llama.cpp — and like kev, CUDA-on-SM75
works first-try.

- Weights: `fastino/gliner2.5-multi-v1` @ `12fc40399dae672ce840c5e3c50a92340bff3c8c`
  (pinned revision) — `model.safetensors` 1.15 GB, sha256
  `c1ff4ec0bc00031c15530b8f3c33d3677f27949e6a0cb52e1247a6224b6c5395` (verified)
- Runtime: `pip install "gliner2[local]" protobuf` in a Python 3.14 venv —
  gliner2 2.0.0 + torch 2.14.0+cu130. **The `[local]` extra misses `protobuf` on
  py3.14** (tokenizer import dies); documented here because the install is part of
  the recipe.
- License: Apache-2.0. Architecture: mDeBERTa-v3-base encoder + BoundaryExtractor
  (sparse start/end pairing, any span length ≤ 4096-token window)
- Paper: arXiv 2507.18546

## The recipe

```python
from gliner2 import AutoExtractor

model = AutoExtractor.from_pretrained(
    "/path/to/gliner2.5-multi-v1",   # pinned local dir, not the moving default
    map_location="cuda",             # or "cpu" — see co-residency note
    quantize=True,                   # fp16 on GPU (0.57 GB weights)
)

model.extract_entities(text, ["company", "person", "product", "location"],
                       include_confidence=True)
model.classify_text(text, {"sentiment": ["positive", "negative", "neutral"]})
model.extract_relations("Alice works for Acme in Paris.",
                        ["works_for", "located_in"], include_spans=True)
# structured records: model.create_schema().structure(...) ... model.extract(...)
```

`AutoExtractor` only — `GLiNER2.from_pretrained` is the legacy span loader and will
not dispatch this checkpoint.

## Measured (2026-09-25)

| Mode | Load | Warm latency (4-label NER) | Footprint |
|---|---|---|---|
| GPU fp16 (`quantize=True`) | 6.9 s | **21.8 ms median** (n=10) | **1650 MiB** process VRAM (torch-allocated 1464 MiB) |
| CPU F32 | 4.3 s | **78.3 ms median** (n=10) | 0 VRAM |

| Probe | Result |
|---|---|
| English NER (4 labels) | ✅ 4/4 exact spans, confidence 0.99+ |
| Italian NER (multilingual claim) | ✅ 4/4 (`Roma`→product at 0.551 — genuinely ambiguous token, correct family) |
| Zero-shot medical labels w/ descriptions | ✅ 3/3 (0.94–0.99) |
| Multilabel aspect classification | ✅ exact match to documented expected output |
| Single-label sentiment, mixed sentence | ⚠️ **divergent**: we get `positive`, model card documents `negative` for the same sentence — mixed-polarity bends positive at default threshold |
| Relations | ✅ 2/2 exact edges + half-open spans |
| Structured records (anchor field) | ✅ exact, instance identity preserved |

## Why it's interesting on an 8 GB card

The whole pitch is **one model instead of per-schema fine-tunes** — entity types,
label descriptions, and task heads travel with the request. At 287M it is never the
VRAM-constrained citizen: GPU mode costs 1.65 GB for 22 ms answers, and CPU mode
(78 ms, zero VRAM) is the co-residency option — it can run **beside a full-VRAM LLM
slot** as a live schema-extraction microservice. Utility-tier scoreboard:
laya 27 ms/3-question probe (2.66 GB), kev 240 ms/3-question (146 MiB) — different
task class, but GLiNER is the first doing open-vocabulary schema extraction at all.

Known cosmetic issues (no effect on results): encoder falls back to
`attn_implementation='eager'` (DebertaV2 lacks sdpa in transformers);
`torch.jit.script` FutureWarning on py3.14.

## Reproduce

```bash
mkdir gliner2.5-multi-v1 && cd gliner2.5-multi-v1
python3 -m venv venv && venv/bin/pip install "gliner2[local]" protobuf
# fetch pinned revision:
curl -sL -o model.safetensors \
  "https://huggingface.co/fastino/gliner2.5-multi-v1/resolve/12fc40399dae672ce840c5e3c50a92340bff3c8c/model.safetensors"
# (+ config.json, encoder_config/, tokenizer.json, tokenizer_config.json from same SHA)
sha256sum model.safetensors   # c1ff4ec0bc00031c…
```

Probe harness: `probe_gliner.py` archived with the weights (verbatim output rows in
evidence).

## Storage

Whole dir is 6.7 GB (weights 1.15 GB + py3.14/torch venv) — rotates to the archive
per the storage rule once its slot isn't current. Rebuild is two commands (above).

Evidence: [evidence/gliner25-multi-v1.jsonl](../evidence/gliner25-multi-v1.jsonl)