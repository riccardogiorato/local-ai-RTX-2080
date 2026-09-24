# kev-0.5b ([jaredpalmer/kev](https://github.com/jaredpalmer/kev)) · Python/torch serve — typed decision model

**Status: 🔬 lab-verified** — kev is not a llama.cpp model: it's Qwen2.5-0.5B + LoRA + a pointer
head, block-causal, non-autoregressive (one forward pass per question set). This recipe records
the Python serving stack, which upstream documents only for Apple Silicon — **CUDA is untested
upstream**; here it works on SM75 first-try.

- Weights: `Qwen/Qwen2.5-0.5B` base + `run` artifacts (LoRA `adapter_model.safetensors`
  35,235,088 B · sha256 `04facd5e97cebce2…` + pointer head `head.pt` 1,839,295 B · sha256
  `0d59bd4608e38f32…`), staged at `kev/runs/kev`
- Runtime: kev @ commit `cc954f2`, `python -m kev.serve --run runs/kev`, uvicorn/FastAPI on
  **port 8008** (README quickstart implies 8009 — actual default differs)
- Env: Python 3.12.14 (torch 2.8.0 has no cp314 wheels — `uv python install 3.12 &&
  uv sync --extra serve --python 3.12`), torch 2.8.0+cu128
- API: `POST /v1/systemone` — TypeSafe request/response; `choice`, `noul`, and `score`
  question types in one request

## Measured on this box (2026-09-24)

| Case | Wall (curl) | Server latency | Notes |
|---|---|---|---|
| 3-question request, cold | 0.300 s | 256 ms | first request after load |
| 3-question request, warm ×6 | 0.210–0.248 s | 237–256 ms | **byte-identical answers across all repeats** |
| Routing sanity (billing-state control) | 0.248 s | 246 ms | flips department→billing (0.86), frustration shifts 0.99→1.26 — non-degenerate |

Deterministic: repeated identical requests return identical answers and probabilities.

**VRAM: 146 MiB GPU** (plus ~3.0 GB host RSS for torch). Upstream quotes ~160 ms for a
six-question request on an M5; we see 237–256 ms for three questions on the 2080 — slower but
the same order, and the GPU is basically idle (2% util during a probe; the pass is tiny).

### Routing verdict on the README's own example

The README's shoes example (late delivery + wrong size + double charge) routes to
`returns` (0.95) — defensible (wrong size dominates) but debatable; a human might triage to
billing. The scoring/noul outputs are well-behaved. Treat kev as a cheap deterministic
router/scorer that leaves nearly the whole GPU free, not as a judge.

Evidence: [evidence/kev-05b-serve.jsonl](../evidence/kev-05b-serve.jsonl)

## Reproduce

```bash
git clone https://github.com/jaredpalmer/kev && cd kev
# download the run artifacts (kev-0.5b) into runs/kev — adapter + head + tokenizer
uv python install 3.12          # torch 2.8.0 has no cp314 wheels
uv sync --extra serve --python 3.12
source .venv/bin/activate
python -m kev.serve --run runs/kev   # serves on http://127.0.0.1:8008

curl localhost:8008/v1/systemone -H 'content-type: application/json' -d '{
  "state": "…", "model": "kev-latest",
  "questions": { "department": {"type": "choice", "instructions": "…", "criteria": {…}},
                 "escalate":   {"type": "noul", "instructions": "…"},
                 "frustration": {"type": "score", "instructions": "…", "criteria": ["Calm","Frustrated","Very angry"]} }}'
```

## Notes

- CUDA-on-SM75 worked with **zero flags or code changes** — torch picked the GPU automatically.
- The kev venv is the torch host for the other Python-runtime tests in this queue
  (laya installs into the same venv to share the 846 MB torch download).
- No registry contract applies (custom Python runtime, not a llama.cpp/vLLM serve) —
  lab-recorded only, per repo policy for non-registry runtimes.

## Storage

Artifacts are 52 MB total and the card barely knows kev is there — kept on SSD in the kev repo
working tree (exception to the rotation rule; cheap and actively used by the serve command).