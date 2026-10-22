# AG-Bench v2.2 through Claude Code on the Strata Swift-IQ2_XS serve — 2026-10-22

Owner request: "Can we run our bench on strata Claude code to see how it compares on multiple tasks?"

Same 11 tasks, same cap (900 s per task), same verify.sh + protected-paths rules, same standing
serve (Swift 1.5 Flash-Next IQ2_XS on Strata 0.2.2) as the pi-based AG-Bench v2.2 of record.
The only variable: the harness — Claude Code (`claude -p`, `--dangerously-skip-permissions`,
`--max-turns 64`) instead of pi. All requests go through the loop-study recording proxy
(`PROXY_OUT_DIR` = this experiment's `proxy-out/`), so per-task token usage and request bodies
are captured with Strata's own usage numbers.

Baselines (pi on this serve, commit 04ac37c): **11/11 @ 1051 and 1123 s (n=2), 0 suspect**;
Q2_0/pi: 11/11 @ 1135 s (0.1.44 era).

## Pre-registered predictions (recorded before the run)

- **Pass rate: 9-11/11.** Claude Code solved the trap cell correctly and writes precise code;
  the losses if any should be wall-cap shaped (task2 react/npm-install, task5 TS conversion,
  task3 dep-upgrade, task7 long-context are the cap-risk set), not capability shaped. Anything
  below 9 falsifies "harnesses shape the cost, not the likelihood" for real multi-step tasks.
- **Wall clock: 2.5-6x pi's.** The loop-study measured claude burning 32 turns / 377 s of serve
  wall on a two-step trap that pi closed in 4 turns / ~100 s. If the average task lands under
  250 s I will have underestimated its startup efficiency; if several tasks hit the 900 s cap,
  the ceiling prediction (total > 5000 s) wins.
- **Context: cold envelope 11-12.5K tokens** (as measured in the loop study), peak per task far
  higher on the doc-heavy tasks (task7). Total output tokens predicted 2x-3x pi's per-task
  output (pi ~750 tok/task average per the 8,345 total on the trap ~11 turns).
- **Cross-task leakage**: each task runs in its own empty /tmp runroot (no sibling tasks, no
  benchmark infra in reach). The proxy capture is audited post-run for out-of-task reads
  (same content-marker method as the loop study); any contamination voids the affected row.
- Claude's internal calls (title generation, topic detection, count_tokens) all pin to
  `local-model` too — they land on the same card and are included in wall/cost accounting.

## Method notes

- The driver (`claudecode-bench.sh`) copies pi's bench rules exactly: rsync without
  node_modules/locks (deps install on demand), zero-byte-run retry NOT inherited (claude exits
  with structured JSON; a rc≠0 or missing result.json row is recorded as-is), protected paths
  `tests/` + `protected/` (task8: `tests/` + `wheels/`) compared against pristine master.
- Per-task evidence: `runs/<task>/{result.json, claude.err, workdir-after.tar, claude-config/}`,
  proxy rows labeled `claudecode-<task>`, results JSONL in `results/`.
- The suite runs in two halves (tasks 1-6, then 7-11) for background-time-budget reasons;
  the batch is single-threaded (one task at a time on the card).

## Result: 11/11 @ 1645 s — the first harness to join pi at a perfect AG-Bench rate on this card

| task | wall | turns | | task | wall | turns |
|---|---|---|---|---|---|---|
| task1-js-bugfix | 73 s | 9 | | task7-long-context | 124 s | 18 |
| task2-react-fix | 163 s | 13 | | task8-tb-broken-python | 256 s | 31 |
| task3-dep-upgrade | 251 s | 18 | | task9-tb-access-logs | 74 s | 10 |
| task4-python-bugfix | 42 s | 7 | | task10-tb-bank-trans | 282 s | 18 |
| task5-js-to-ts | 125 s | 11 | | task11-tb-assign-seats | 139 s | 16 |
| task6-extra-code | 116 s | 8 | | **total (11)** | **1645 s** | 159 |

**vs pi on the same serve (commit 04ac37c): pi 11/11 @ 1051/1123 s (n=2). Claude Code matches
the perfect rate at +47-57% wall clock** — 149.5 s/task average vs pi's ~95-102. Not one task
approached the 900 s cap; the turn ceiling actually used was 31 (task8) of the 64 allowed.

Per-task context cost from the proxy capture (all requests pinned to the card, internal claude
calls included): peak context 12.4K (task4) to 38.9K (task10), cumulative prompt-ctx processed
117K-440K tokens per task, output 844-9,930 tokens per task (~55.8K output total for the suite).
Zero cross-task leakage, zero master-dir escapes (audited from captured request bodies, same
method as the loop study); no protected-path violations; writeups were precise (task11 even
flagged the pickle trust issue unprompted).

## Pre-registered prediction check

- **Pass rate: predicted 9-11, got 11/11** — top of the band, "harnesses shape the cost, not the
  likelihood" holds for real multi-step tasks too.
- **Wall clock: predicted 2.5-6x pi, actual +47-57%** — falsified in the good direction. The
  loop study's 32-turn trap profile did not transfer: on structured tasks claude's thoroughness
  is self-funding (7-18 turns on 9 of 11 tasks).
- **Cold envelope 11-12.5K: confirmed** (task4's first request: 12,439 effective tokens).
- Output-volume 2x-3x pi per task: not measurable (pi's bench rows carry no token capture) —
  recorded as open, with the claude side at ~5.1K output tokens/task average.

## Classification

Claude Code + Strata Swift IQ2_XS is a **fully working second harness** on this box: perfect
pass rate, honest verbose reports, no loop surfaces, at ~1.5x pi's wall. Cost profile:
~12-40K-token task contexts (the price of its system prompt + tool corpus on a 41 tok/s-class
agent decode) and ~2x pi's expected output volume. For the standing serve nothing changes: pi remains
the reference client; claude code is the "explain-everything" alternative when wall clock
matters less than report quality.
