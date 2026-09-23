# Hardware fingerprint

All recipes in this repo run on this machine. If a number here is cited elsewhere, these are the conditions behind it.

## GPU

| Field | Value | Source |
|---|---|---|
| Model | NVIDIA GeForce RTX 2080 | nvidia-smi |
| Chip | TU104 (Turing, SM75) | NVIDIA Turing whitepaper; videocardz spec DB |
| VRAM | 8,192 MiB GDDR6 | nvidia-smi |
| Bandwidth | 448 GB/s | notebookcheck spec DB |
| CUDA cores | 2,944 | notebookcheck spec DB |
| Driver | 610.57.04 (KMD), CUDA UMD 13.3 | nvidia-smi |
| Toolkit | CUDA 13.3.1 (pacman) | pacman |

## Host

| Field | Value |
|---|---|
| CPU | Intel Core i5-9600K — 6 cores / 6 threads @ 3.70 GHz |
| RAM | 16 GB (zram swap 15.5 GB) |
| OS | Arch Linux / Omarchy (kernel 7.2.3-arch1-3), Wayland |
| Desktop baseline VRAM | ~520 MiB (Hyprland + shell) — subtracted from residency numbers |
| Container runtime | Docker via sudo; nvidia-container-toolkit (CDI mode) installed 2026-09-23 |

## Measurement conventions

- Decode/prefill rates are **server-reported** (`timings.predicted_per_second`, `timings.prompt_per_second` from llama.cpp streaming responses), not client wall-clock.
- "Short-fill" means a ≈2 K-token prompt in a large assigned context; "filled" probes prefill a context-sized prompt to the stated length before measuring decode.
- TTFT = first content token (first streamed delta with non-empty `content`).
- Every speed run repeats at least 2–3 times; the range is reported, never a single best-of run.
- Thinking (`enable_thinking`) is disabled for all comparative/capability measurements unless the row says otherwise; the Qwen3.5 chat template enables it by default.