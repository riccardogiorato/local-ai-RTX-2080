# Qwen3.5 4B / 9B MTP on llama.cpp for the RTX 2080 8 GB

![llama.cpp](https://img.shields.io/badge/llama.cpp-b11118-blue) ![model](https://img.shields.io/badge/model-Qwen3.5--4B%20%2F%209B%20Q4__K__M-informational) ![arch](https://img.shields.io/badge/GPU-TU104%20%C2%B7%208%20GB-lightgrey)

Every number in this repo was measured on this exact card — no ports from other GPUs, no vendor
specs, no unbenched claims. Both recipes are **validated** in
[0xsero/local-ai-registry](https://github.com/0xSero/local-ai-registry) (`rtx-2080-8gb`, the first
Turing card there) and re-derived here with the lab context ceilings the registry contract does
not carry. Raw JSONL for every run is in [`evidence/`](evidence/); the fixed benchmark prompt is
[`prompts/code-continuation.txt`](prompts/code-continuation.txt).

> **Rule of thumb:** treat decode deltas < 15% between unaligned prompt classes as noise.
> On this card decode speed is dominated by MTP draft acceptance (1.00 on repetitive
> continuation, 0.5–0.75 on novel prose), so compare only on the same prompt file. See
> [notes/findings-2026-09-23.md](notes/findings-2026-09-23.md).

## Requirements

| Component | Detail |
|---|---|
| Hardware | NVIDIA GeForce RTX 2080 — TU104, Turing SM75, 8 GB GDDR6, 448 GB/s ([fingerprint](hardware.md)) |
| Host | Any Linux with Docker; host RAM ≥ 16 GB is enough (peak host usage is the mmap'd weights) |
| Docker | NVIDIA Container Toolkit installed, GPU passthrough working (`nvidia-smi` visible in a container) |
| Model files | `Qwen3.5-{4B,9B}-Q4_K_M.gguf` from the pinned revisions in the recipe — SHA-256 verified before load |
| Engine image | `ghcr.io/ggml-org/llama.cpp:server-cuda12-b11118@sha256:bfb3264f…f7bbced3` (digest-pinned) |
| CLI tools | `docker`, `curl` |
| Hugging Face token | `HF_TOKEN` in `~/.bashrc` for rate limits — the pinned revisions are public, so it is optional |

## Quick start (9B, 64K context — what we run on this box daily)

```bash
# 1. fetch the exact pinned artifact and verify it (must print e8dd94817e95…232841fe)
hf download unsloth/Qwen3.5-9B-MTP-GGUF Qwen3.5-9B-Q4_K_M.gguf \
   --revision 9716a636ee4bddc3fed678220b7a33dd2a4160ae --local-dir ~/models/qwen35-9b-mtp
sha256sum ~/models/qwen35-9b-mtp/Qwen3.5-9B-Q4_K_M.gguf

# 2. start the server (fully GPU-resident, 7.27 GB, MTP depth 4)
sudo docker run --gpus all -p 8080:8080 -v ~/models/qwen35-9b-mtp:/models:ro -d \
  ghcr.io/ggml-org/llama.cpp:server-cuda12-b11118@sha256:bfb3264fc2166e01e2b4f9b537e45d7006d87c75021b911f132ef607f5bbced3 \
  --model /models/Qwen3.5-9B-Q4_K_M.gguf --alias Qwen3.5-9B-MTP-Q4_K_M \
  --host 0.0.0.0 --port 8080 --ctx-size 65536 --parallel 1 --n-gpu-layers 999 \
  --flash-attn on --batch-size 512 --ubatch-size 512 \
  --cache-type-k q4_0 --cache-type-v q4_0 --jinja \
  --spec-type draft-mtp --spec-draft-n-max 4

# 3. confirm the model is served (~60 s cold start, then ~124 tok/s short fill)
curl -s http://127.0.0.1:8080/v1/models | jq '.data[0].id'

# 4. stop
sudo docker rm -f $(sudo docker ps -q --filter ancestor=ghcr.io/ggml-org/llama.cpp:server-cuda12-b11118@sha256:bfb3264fc2166e01e2b4f9b537e45d7006d87c75021b911f132ef607f5bbced3)
```

The 4B recipe and every alternative configuration (32K/128K, q8_0 KV) are in
[recipes/](recipes/) as full copy-paste commands.

## Which one to use

| You want | Recipe | Context | Short-fill decode | Residency |
|---|---|---|---|---|
| Fast chat, light coding, huge context | [4B](recipes/qwen35-4b-mtp-q4km-llamacpp.md) | up to **128K** q8_0 KV | **182 tok/s** | 7.15 GB |
| Reasoning, real coding, tools | [9B](recipes/qwen35-9b-mtp-q4km-llamacpp.md) | up to **64K** q4_0 KV | **124 tok/s** | 7.27 GB |

Registry equivalents: the 4B is `recommended` for `rtx-2080-8gb`, the 9B is the plugin alternate —
the same split we run ourselves.

## Configuration

| Variable | Default | Notes |
|---|---|---|
| `--ctx-size` | 65536 (9B) / 32768 (4B) | Allocation is free at short fill — measured identical decode at 32K/64K/128K. What you allocate costs VRAM only. |
| `--cache-type-k/-v` | q4_0 (9B@64K) / q8_0 | **9B at 64K only fits with q4_0 KV** — q8_0 OOMs at load. Zero measured decode penalty from q4_0 under flash attention. |
| `--spec-type draft-mtp --spec-draft-n-max 4` | on | Embedded nextn MTP head, no separate drafter model. Acceptance is prompt-class dependent (see rule of thumb). |
| `--flash-attn` | on | Required for the KV-precision games above. |
| `--batch-size/--ubatch-size` | 512/512 | Does **not** change decode (measured 112.8 vs 113.7 tok/s); trims TTFT 100→71 ms. Kept for lab convention. |
| `--parallel` | 1 | Default 4 slots quadruples the KV allocation; always pin to 1 on this card. |
| Thinking | ON (template default) | Send `chat_template_kwargs {"enable_thinking": false}` for deterministic coding/agent use. The 4B fails a multi-fact reasoning check with it off; the 9B passes. |

## Measured on this box

Decode (tok/s, server-reported `timings.predicted_per_second`, 2–3 runs, ranges not best-of;
fixed 1,987-token continuation prompt, thinking off):

| Model | CTX | KV | Short-fill | Filled |
|---|---|---|---|---|
| 4B | 32K | q8_0 | **181.8–182.2** | — |
| 4B | 128K | q8_0 | **181.7–181.9** | 76.7 @94K |
| 9B | 32K | q8_0 | **124.5–124.8** | — |
| 9B | 64K | q4_0 | **124.2–124.4** | 78.8 @37K |
| 9B | 64K | q8_0 | ⚠️ OOM at load | — |

Prefill (fresh prompts): 4B 2,327 → 2,241 t/s @2.8K→11.7K; 9B 1,578 → 1,529.
Cold start: 51.6 s (4B) / 56.8 s (9B) to "model loaded"; first request pays CUDA-graph compile
(17 tok/s in logs) before steady state — report warmed numbers for speed claims.

**Windows-parity 1:1** (same card previously ran the Windows lab; same flags, same prompt,
era-matched build `b10481`): Linux 173.3–173.6 vs Windows 172.3–173.5 tok/s — **tie at ±0.1%**,
no docker penalty. Current `b11118` is the real upgrade: **+5%** (4B → 182) to **+7%** (9B →
117→125 across builds).

Method notes: single boot, warmup request discarded, ranges over 2–3 runs, `chat_template_kwargs`
thinking-off for comparability. Full matrix with per-run provenance:
[measurements/2026-09-23-qwen35-mtp-linux-matrix.md](measurements/2026-09-23-qwen35-mtp-linux-matrix.md).

## Thinking & tool calling

Chat template ships thinking ON. For coding/agents disable it per request (see Configuration).
Tool calls are plain OpenAI `tools`: both models were probed with a real
`get_weather("Turin")` call round-tripped to a correct natural-language answer, and the 9B
additionally drove opencode's build agent (bash tools executing) through this exact server.
Capability evidence: [evidence/](evidence/) — 9B passes a multi-fact reasoning check the 4B fails.

## Using the API

```bash
curl -s http://127.0.0.1:8080/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model": "Qwen3.5-9B-MTP-Q4_K_M",
  "messages": [{"role": "user", "content": "Reply OK."}],
  "max_tokens": 64, "temperature": 0,
  "chat_template_kwargs": {"enable_thinking": false}
}' | jq '.choices[0].message.content'
```

Works as a custom model in opencode / T3 Code via an `@ai-sdk/openai-compatible` provider pointed
at `http://127.0.0.1:8080/v1` — that is how it runs on this machine.

## Repository layout

```text
recipes/         one file per model+quant+runtime, with copy-paste docker launches
measurements/    dated raw matrices with per-run provenance
prompts/         the fixed benchmark prompt — compare only on the same file
evidence/        raw JSONL: acceptance harness output, capability probes
notes/           empirical rules and open questions
registry/        cross-links to the local-ai-registry records
```

## Notes

- Cache-hit prefill numbers are worthless: llama.cpp logs `prompt_per_second` over only the
  non-cached tokens; every prefill number here used a fresh prompt.
- The 4B at 128K fits because its KV is GQA-small; don't generalize to other 8 GB cards without
  running their ceiling probes.
- Future models (Gemma 4 E4B QAT + drafter, Bonsai 2, GLM-OCR) land in `recipes/` as
  `lab-verified` entries — including the ones that can never qualify for the registry.

## Credits

- GGUFs by [unsloth](https://huggingface.co/unsloth) (Qwen3.5 MTP builds with the embedded nextn head)
- Engine by [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp), upstream docker images
- Registry contract and validation by [0xsero/local-ai-registry](https://github.com/0xsero/local-ai-registry)
- Benchmark prompt inherited from the prior Windows lab on this same card