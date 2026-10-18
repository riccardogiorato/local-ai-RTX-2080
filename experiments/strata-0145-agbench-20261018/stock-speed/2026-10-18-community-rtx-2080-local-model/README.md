# Community benchmark on NVIDIA GeForce RTX 2080

Measured on 2026-10-18 with `tools/strata_bench.py` (suite 1, 3 runs per test, medians with ranges). Speeds are the engine's own timings; first-token times are measured by the client over HTTP. Speed only: no correctness check was run.

## Hardware and software

- GPU and VRAM: NVIDIA GeForce RTX 2080, 8 GiB VRAM
- CPU: Intel(R) Core(TM) i5-9600K CPU @ 3.70GHz (6 cores, 6 threads); installed RAM: 62.6 GiB; storage: not measured
- OS: Linux 7.2.5-3-omarchy; GPU driver: 610.57.04; CUDA: not read
- Strata: project 0.1.45, commit 477ac13c; engine 0.1.45
- Background workloads and power limits: not recorded

## Model and configuration

- Model and quantization: local-model
- Context: 131072 tokens; parallel slots: 1
- Settings: the install's own configuration, unchanged; thinking off for the suite; temperature 0

## Method

Run by `python tools/strata_bench.py --long` against the HTTP API of a Strata server (already running); model loading is not timed. One warm-up chat and a 1K prompt are discarded first. Every prompt starts with a unique tag, so the conversation cache cannot help the fresh-prompt tests.

- short chat: the three questions of `tools/ab_engine.py`, up to 100 new tokens, 3 runs
- 4K / 16K prompts: generated word lists sized by a calibration request, 24 new tokens, 3 fresh prompts each
- agent session: system prompt and four tools, then 5 turns that each add about 1500 words of a project file and continue from the model's own earlier answers (the way agent clients resend a conversation), 64 new tokens per turn, 3 sessions; the cache numbers come from the answer's usage (`cached_tokens`) and timings (`prompt_n`)
- concurrency (when run): N requests sent at the same moment, total tokens over the wall time of the burst, latency over all requests

## Results

| Configuration | Actual prompt tokens | Reused tokens | Generated tokens | Runs | Prompt tok/s median and range | Decode tok/s median and range | TTFT seconds median and range |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| short chat | 46 (43-51) | 0 | 100 (100-100) | 9 | not measured | 42.9 (41.7-53.8) | 0.85 (0.73-0.99) |
| 4K prompt, fresh | 4019 (4019-4019) | 0 (0-0) | 24 cap | 3 | 660.6 (656.4-661.4) | not measured | 6.12 (6.11-6.16) |
| 16K prompt, fresh | 16058 (16058-16058) | 0 (0-0) | 24 cap | 3 | 657.8 (657.7-658.5) | not measured | 24.45 (24.42-24.45) |
| 32K prompt, fresh | 32049 (32049-32049) | 0 (0-0) | 24 cap | 3 | 644.8 (642.0-644.8) | not measured | 49.75 (49.75-49.97) |
| agent session, follow-up turns | 14491 (14487-14578) at the last turn | see below | up to 64 | 3 | see below | 43.0 (23.9-50.3) | 5.56 (3.13-6.26) |

Ranges are the lowest and highest of the runs; `Runs` counts requests that returned a token.

### Agent session (conversation cache)

Cache hit over the follow-up turns: 68.7 % (68.6-68.7); earlier-turn tokens read again per session: 4 (4-74) (earlier turns that the cache did not hold; the 13719 (13719-13719) new tokens of the files are read once); first turn (nothing cached) first token: 2.10 s (2.10-2.15).

| Turn (run 1) | Prompt tokens | Reused | Read | Prompt tok/s | First token (s) | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 609 | 0 | 609 | 294.4 | 2.098 | 29.0 |
| 1 | 3748 | 626 | 3122 | 520.2 | 6.035 | 40.4 |
| 2 | 5281 | 3811 | 1470 | 467.8 | 3.177 | 41.3 |
| 3 | 8714 | 5274 | 3440 | 553.0 | 6.257 | 43.3 |
| 4 | 11622 | 8760 | 2862 | 525.4 | 5.487 | 46.3 |
| 5 | 14578 | 11679 | 2899 | 519.4 | 5.618 | 38.5 |

Per-request data: `results.json`. Engine log lines from the start: `engine-log-excerpt.txt` (when this run started the server).

## Correctness and limitations

Not measured: this is a speed suite. The conversation uses the model's own replies, so token counts differ a little between runs. Machine details come from the server, `nvidia-smi`/`rocm-smi` and the OS; background load and power limits are not recorded. Total time of the suite: 380 s.
