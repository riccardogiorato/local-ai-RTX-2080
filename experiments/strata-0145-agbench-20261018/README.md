# Strata v0.1.45 · full AG-Bench and dashboard verification

## Verified results · 2026-10-18

| Measurement | Stock v0.1.45 | Optimized |
|---|---:|---:|
| Audited verifier passes | 11/11 | 11/11 |
| Task wall, excluding flagged task8 | 771 s | 577 s |
| Full 11-task wall | 1,190 s | 998 s |
| Generated tokens, all 11 tasks | 37,761 | 39,427 |
| Tool executions, all 11 tasks | 130 | 119 |
| Aggregate decode, all 11 tasks | 47.68 tok/s | 52.67 tok/s |
| Standard short decode | 42.9 tok/s | 47.1 tok/s |
| Standard 4K prefill | 660.6 tok/s | 677.2 tok/s |
| Standard 16K prefill | 657.8 tok/s | 697.1 tok/s |
| Standard 32K prefill | 644.8 tok/s | 695.4 tok/s |
| Scripted agent first token | 5.562 s | 5.218 s |
| Scripted agent decode | 43.0 tok/s | 45.3 tok/s |

The ten tasks outside task8's issues took **25.2% less elapsed time** in this
one paired run; full-suite time fell 16.1%. Different agent trajectories, package
operations and output lengths contribute to task time, so neither percentage is
an isolated kernel gain. The repeated fixed probes showed **+7.8% 32K prefill**
and **+9.8% short decode throughput** for the combined configuration.

Optimized means the custom exact-scorer tile (`STRATA_SCORES_TURING=2`) plus
Strata's existing `STRATA_SM75_PERF=1` options. This comparison does not isolate
the custom tile; see the earlier kernel experiment for its separate A/B arm.
Both full suites and both three-repetition speed suites completed. There were
no speed-request failures, agent transport errors or detected competing builds.
Original source manifests, protected task inputs and verifier hashes matched.
Task8's environment directory was retained, and its repair commands were reviewed.

Task8 already passes its verifier before agent work; its optimized agent also
inspected retained stock logs. It remains visible in raw results and full-suite
counters, but is excluded from the headline task-time comparison. The tool-reference
audit found no confirmed cross-run reads in the other ten tasks. That review is
not an OS sandbox or an exhaustive information-flow proof. Fixing and isolating
this fixture should precede a future quality leaderboard claim.

Engine counters above exclude each arm's initial warmup. Original totals are
retained in `results.json` under `including_warmup`; no raw result row was rewritten.
Aggregate decode is generated tokens divided by reported decode seconds, across
different trajectories. The scripted agent medians pool follow-up turns across
three sessions; other probes repeat each fixed input three times.

Evidence: `results.json`, `metadata.json`, `original-task-manifest.json`,
`cross-run-access-audit.json`, `task8-baseline.json`, `resource-samples.jsonl`,
per-task Pi/verifier logs and `stock-speed/` / `optimized-speed/` reports.


The frozen AG-Bench v2.2 harness runs all 11 established tasks, 900 s per task,
against stock v0.1.45 and the locally optimized configuration. Both arms use the
same 128K context, int8 KV with 32K resident cells, calibrated speculative/cache
settings and verified NVMe files. Only the executable and Turing opt-ins differ.

Pi 1.3.0 is used for both arms in an isolated agent directory, with request-level
temperature 0 and seed 42. No extensions, MCP connections or model fallback.
The provider uses the existing AG-Bench OpenAI-compatible protocol. The Pi
thinking setting is off; `reasoning_effort` is omitted, retaining the server's
default reasoning behavior in both arms. Older leaderboard runs used older Pi
versions, so the same-day matched comparison is the primary evidence.

The established shell harness is frozen in `agentic.frozen.sh` with minimal
plumbing changes: isolated port/provider, a pristine task mirror, controller
readiness, verifier log retention and removal of its automatic git restoration.
Source fixtures are hashed before and after each arm. Protected task inputs,
tests and verifiers are independently audited. Task8 is allowed to repair its
virtualenv; its tests/wheels and the virtualenv directory identity are checked.
Original raw rows are retained, and audited results are stored separately.

A fresh server then runs `tools/strata_bench.py --runs 3 --long` for each arm,
covering short decode, 4K/16K/32K prefill and a scripted multi-turn agent workload.
Resource samples record GPU utilization/clocks and external CPU build activity.

The dashboard is generated from `results.json` and the standard speed reports.
It does not substitute prefill-only results for overall task performance. Agent
trajectories and generated-token counts can differ even with fixed sampling;
one paired full suite is an observation, not a universal speed guarantee.

The previous uncommitted dashboard files are backed up as `before-index.html`,
`before-dashboard.svg`, and `before-dashboard.png`. The user authorized replacing
the fragrance-page HTML with the benchmark dashboard.

## Fixture limitation found during the run

A disposable copy of the untouched task8 fixture already passes all three verifier
checks before any agent work (`task8-baseline.json`). Both arms still run the
established 11-task suite unchanged, but task8 cannot establish repair ability.
Dashboard totals are **verifier passes**, with this task explicitly flagged.
Its time remains in the suite wall total, and a separate total excluding task8
will be reported. The source fixture is preserved for comparability.

The optimized task8 agent also inspected the retained stock task8 work directory
and its Pi logs. This cross-run exposure makes its paired timing unsuitable for
a clean speed claim. The dashboard's time-change headline therefore **excludes
task8**, while retaining all 11 raw rows and verifier results. Completed traces
for the other ten tasks are checked for cross-run access.

## Dashboard verification

Desktop (1440 px) and mobile (375 px) rendering passed in the installed Chromium
browser. Both score cards, the 11-row task table, 11 chart rows, headline values
and All/Failures filters were checked; no JavaScript runtime errors or global
horizontal overflow occurred. Screenshots: `dashboard-desktop.png` and
`dashboard-mobile.png`; assertions: `dashboard-qa.json`. T3's preview tools were
tried first but could not finish their initial browser download, so QA used
`verify-dashboard-cdp.py` against installed Chromium without extra downloads.
