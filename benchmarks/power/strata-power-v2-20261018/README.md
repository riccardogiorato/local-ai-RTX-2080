# Strata power sweep v2 and controlled context ladder · 2026-10-18

Pinned after recipe/config discovery: the fleet-record standing chat serve is
Flash-Next GSQ-RCO Q2_0 125B, locally tuned v0.1.45, calibrated tailnet config
`recipes/strata-configs/strata-q20-gsq-0145-tailnet.json`. IQ3_XXS/v0.1.44 is a
slower quality-tier alternative; Qwen3.6 A3B/v0.1.45 is a separate 16K lineage
for a future pass. Neither is substituted during this run.

One localhost server start for both phases. Config arguments and environment
remain calibrated; a run-local copy changes only host/port/log destinations.
The first JSONL records preserve config, actual model paths, binary hash, source
commit/tag, exact invocation and the loaded health response.

The corpus is fixed real repository prose and source code, not a repeated word.
Local chat-tokenizer calibration is verified against engine-reported prompt_n.
Every long request uses a distinct nonce at the beginning, requires zero reused
tokens, and retrieves a unique key buried at about 10% token depth. Requests use
temperature 0, seed 42, thinking off and an output limit of 192 tokens.

225 W ladder: two requests each at 32K, 64K, 80K, 96K and near-128K input.
The last prompt targets 130,816 tokens, leaving 256 context cells for output.
Power walk: 225/190/165/145/125/145/165/190/225 W, 60-second cooldown per
checkpoint, three short prompts plus 30,720- and 102,400-token inputs. The
ascending 145 W checkpoint adds a second 102,400-token input to check drift.

Power/SM clocks/temperature/utilization use the original 200 ms nvidia-smi
sampler. PCIe receive/transmit uses nvidia-smi dmon at 1 Hz (reported MB/s).
Windows are aligned backward from request completion using engine-reported
decode and prefill durations, excluding client/server prompt-tokenization time.
A quiet-box guard checks before every request and every two seconds, flagging
concurrent builds or preview jobs. GPU power is restored to 225 W and owned
server/samplers are stopped in cleanup. No persistent system settings change.

Reproduce from the repository root with fresh output paths:

```bash
python3 -u benchmarks/power/strata-power-sweep.py ENGINE_LOG OUTPUT.jsonl \
  --config recipes/strata-configs/strata-q20-gsq-0145-tailnet.json \
  --server-root /home/riccardogiorato/Desktop/github/strata-0145
```

The parent JSONL is the measurement evidence; this directory holds discovery,
sampler data, exact run configuration and engine/server logs. Historical
numbers are context only. All comparisons use this run's own 225 W arm.

## Result

The context ladder completed at 225 W through 130,833 actual input tokens.
All 56 measured requests completed, all 29 long-arm needle checks passed with
zero prefix reuse, and every long request generated its requested 192 tokens.
There were no quiet-box guard violations. One server PID served both phases.

**165 W is the new low-loss sweet spot for this model/build.** The 100K prefill
penalty is 1.7–2.4% for 22.3–22.9% less measured prefill board power. At 145 W,
the direction-matched penalty repeats at 4.2–4.4% (descending 677.1; ascending
679.0 and extra recheck 678.1 tok/s). This fails the requested under-4% criterion
even though the 30K penalty remains only 1.5–2.5%. All-pair bounds are 3.9–4.6%.
Initial/final 225 W 100K prefill: 706.9/709.5 tok/s, +0.4% drift.

Decode has no monotonic cap-dependent slowdown through 125 W. Retain the one
145 W ascending decode dip (37.3 tok/s), whose immediate recheck returned 48.1;
the descending 145 W sample was 47.0. The result supports host/transfer-limited
decode, rather than a claim that every individual request is invariant.

Range tables and telemetry: [tables.md](tables.md). Interpretation and
recommendation: [hardware.md](../../../hardware.md#gpu-power-limit). The
root JSONL contains the original timing, power, retrieval and cleanup records.
`analysis.json` retains both direction-matched losses and conservative all-pair
bounds. The full historical power sweep remains unchanged.

The pinned run copy `pinned-runner.py` is an audit snapshot. Reproduce using the
runner at its repository path so its repository-root resolution remains valid.

Cleanup restored 225 W, exited the server cleanly and stopped both samplers.
Standing config SHA-256 matched its pre-run value. Post-cleanup receipts are
saved in `postflight.json`.
