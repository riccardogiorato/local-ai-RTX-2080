# Community benchmark on NVIDIA GeForce RTX 2080

Measured on 2026-10-15 with `tools/strata_bench.py` (suite 1, 2 runs per test, medians with ranges). Speeds are the engine's own timings; first-token times are measured by the client over HTTP. Speed only: no correctness check was run.

## Hardware and software

- GPU and VRAM: NVIDIA GeForce RTX 2080, 8 GiB VRAM
- CPU: Intel(R) Core(TM) i5-9600K CPU @ 3.70GHz (6 cores, 6 threads); installed RAM: 62.6 GiB; storage: not measured
- OS: Linux 7.2.5-3-omarchy; GPU driver: 610.57.04; CUDA: not read
- Strata: project 0.1.44, commit ed4773eb; engine 0.1.44
- Background workloads and power limits: not recorded

## Model and configuration

- Model and quantization: local-model
- Context: 131072 tokens; parallel slots: 1
- Settings: the install's own configuration, unchanged; thinking off for the suite; temperature 0

## Method

Run by `python tools/strata_bench.py --long --runs 2` against the HTTP API of a Strata server (already running); model loading is not timed. One warm-up chat and a 1K prompt are discarded first. Every prompt starts with a unique tag, so the conversation cache cannot help the fresh-prompt tests.

- short chat: the three questions of `tools/ab_engine.py`, up to 100 new tokens, 2 runs
- 4K / 16K prompts: generated word lists sized by a calibration request, 24 new tokens, 2 fresh prompts each
- agent session: system prompt and four tools, then 5 turns that each add about 1500 words of a project file and continue from the model's own earlier answers (the way agent clients resend a conversation), 64 new tokens per turn, 2 sessions; the cache numbers come from the answer's usage (`cached_tokens`) and timings (`prompt_n`)
- concurrency (when run): N requests sent at the same moment, total tokens over the wall time of the burst, latency over all requests

## Results

| Configuration | Actual prompt tokens | Reused tokens | Generated tokens | Runs | Prompt tok/s median and range | Decode tok/s median and range | TTFT seconds median and range |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| short chat | 46 (43-51) | 0 | 100 (100-100) | 6 | not measured | 44.6 (42.7-54.7) | 0.87 (0.80-1.04) |
| 4K prompt, fresh | 4019 (4019-4019) | 0 (0-0) | 24 cap | 2 | 655.4 (655.2-655.6) | not measured | 6.17 (6.17-6.17) |
| 16K prompt, fresh | 16058 (16058-16058) | 0 (0-0) | 24 cap | 2 | 661.9 (659.5-664.3) | not measured | 24.30 (24.21-24.39) |
| 32K prompt, fresh | 32049 (32049-32049) | 0 (0-0) | 24 cap | 2 | 647.2 (645.7-648.7) | not measured | 49.57 (49.45-49.69) |
| agent session, follow-up turns | 14503 (14499-14507) at the last turn | see below | up to 64 | 2 | see below | 34.9 (21.4-44.6) | 5.80 (3.13-6.25) |

Ranges are the lowest and highest of the runs; `Runs` counts requests that returned a token.

### Agent session (conversation cache)

Cache hit over the follow-up turns: 68.5 % (68.4-68.7); earlier-turn tokens read again per session: 74 (4-144) (earlier turns that the cache did not hold; the 13730 (13730-13730) new tokens of the files are read once); first turn (nothing cached) first token: 2.09 s (2.05-2.13).

| Turn (run 1) | Prompt tokens | Reused | Read | Prompt tok/s | First token (s) | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 609 | 0 | 609 | 290.6 | 2.128 | 27.7 |
| 1 | 3750 | 628 | 3122 | 513.9 | 6.108 | 34.2 |
| 2 | 5283 | 3743 | 1540 | 493.1 | 3.164 | 44.4 |
| 3 | 8727 | 5276 | 3451 | 556.2 | 6.246 | 21.4 |
| 4 | 11595 | 8733 | 2862 | 526.6 | 5.473 | 31.0 |
| 5 | 14499 | 11600 | 2899 | 480.8 | 6.069 | 25.4 |

Per-request data: `results.json`. Engine log lines from the start: `engine-log-excerpt.txt` (when this run started the server).

## Correctness and limitations

Not measured: this is a speed suite. The conversation uses the model's own replies, so token counts differ a little between runs. Machine details come from the server, `nvidia-smi`/`rocm-smi` and the OS; background load and power limits are not recorded. Total time of the suite: 254 s.
