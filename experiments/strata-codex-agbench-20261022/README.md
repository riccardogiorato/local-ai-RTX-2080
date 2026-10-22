# Codex CLI on the Strata Swift-IQ2_XS serve — loop trap + AG-Bench v2.2 (2026-10-22)

Owner request: "try strata model on codex to see how it compares to other harnesses we already tried today."

Codex is the one harness besides pi that upstream Strata actively designs for: the 0.2.2 release
notes keep the stateless OpenAI **Responses API** (`/v1/responses`) specifically because Codex's
compaction relies on it, `strata connect codex` ships a tested wiring (codex-cli 0.163.0), and the
docs publish its envelope estimate: "system prompt and tools take about 8.6K tokens."

## Wiring

- Lean scratch `CODEX_HOME` (`codex-home/config.toml`): Responses wire via the recording proxy
  (`http://127.0.0.1:8081/v1`), `model = strata`, `check_for_update_on_startup = false`,
  131072-token context window, auto-compact at 100K, no plugins/MCP. The owner's desktop
  `~/.codex` (full ChatGPT plugin stack: browser, computer-use, node_repl MCP with its 120 s
  startup timeout, marketplaces) is NOT used: the first direct attempt spent its entire 180 s
  budget before the first request and never reached the serve (plugin-stack startup + stdin-EOF
  wait: `codex exec` appends piped stdin to the prompt and waits for EOF — the driver passes
  `< /dev/null`). An additive `[model_providers.strata]` block sits in the owner's config with
  the proxy base URL, opt-in only; the desktop default is untouched.
- Direct binary path (`mise/installs/codex/0.163.0/bin/codex`) — the mise shim stalls
  (AG-Bench's `PI_BIN` precedent).
- Cold-envelope measured live (not the docs' 8.6K estimate): see results.

## Pre-registered predictions

- **Loop trap (same stale-CDN scenario as the four earlier cells): no loop, verify-and-stop
  class.** Codex's harness design (server-side compaction, minimal tool set) is the most pi-like
  of the four; upstream's low-8K envelope estimate suggests a lean first-place envelope. If it
  re-edits the css after the stale check, that falsifies "lean harness => loop-free" for this pair.
- **AG-Bench v2.2 (cap 900 s): 9-11/11; wall 1100-1800 s** (pi is 1051/1123 s; claude was 1645 s;
  codex's envelope should sit between pi's 2.1K and claude's 11-12.5K, so its wall should land
  between pi's and claude's — unless its desktop-free startup tax dominates, which the warm-up
  gates will show).
- **Context: cold envelope 6-9K tokens** (bracketing upstream's 8.6K claim with protocol overhead),
  peak per task under 30K on the doc-light tasks (its 32K default context window that upstream
  sets would have truncated badly; the scratch home runs 131072 like the other arms).
- Method identical to today's claude bench: per-task isolated /tmp runroots, proxy labels
  `codex-<task>`, protected-path rules, no leaks audited from captured request bodies.

## Evidence

`results/*.jsonl` (per-task rows incl. codex's own tokens-used report), `runs/<task>/`
(codex.out/err, workdir-after.tar), `proxy-out/` (per-request usage + bodies), plus the
loop-trap cell inherited from the loop-study protocol (labeled `codex-trap-iso3`, evidence
copied into `experiments/strata-loop-harnesses-20261022/runs/codex-trap-iso3/`).

## Result: 9/11 @ 1273 s — fastest harness per task, but a systematic tool-call defect

| task | wall | | task | wall |
|---|---|---|---|---|
| task1-js-bugfix | 59 s PASS | | task7-long-context | 61 s PASS |
| task2-react-fix | 78 s PASS | | task8-tb-broken-python | 374 s PASS |
| task3-dep-upgrade | 224 s PASS | | task9-tb-access-logs | 60 s PASS |
| task4-python-bugfix | **27 s PASS** | | task10-tb-bank-trans | 156 s **FAIL** |
| task5-js-to-ts | 47 s PASS | | task11-tb-assign-seats | 163 s PASS |
| task6-extra-code | 24 s **FAIL** (rerun: 23 s, same) | | **total** | **1273 s** |

- **Speed: the best on this card.** Of the 9 passing tasks, 7 finished faster than pi's or
  claude's equivalents (task4 in 27 s vs 42/74 s; task7 in 61 s vs ~124 s; task2 in 78 s vs
  116/163 s). Wall for the whole suite (1273 s) sits between pi (1051/1123) and claude (1645)
  with two extra failures included.
- **Capability: held everywhere it could execute.** Long-context ADR hunt, constraint-puzzle
  decoding, venv surgery, dep upgrades — all passed with precise file:line-cited writeups.
- **The defect: two failures (task6 twice incl. rerun, task10) share ONE signature.** The
  model emits `<function=apply_patch>...` as a raw text block — the OpenAI legacy text-call
  format — instead of a Responses tool call. `apply_patch` is not among codex's declared
  tools (it is a shell idiom the developer instructions teach for `exec_command`), so per
  Strata 0.2.2's documented rule the undeclared block stays text, nothing executes, and
  codex ends the turn (rc=0, "final answer" is the unparsed patch). The loop-trap cell showed
  the same class once (`<function=exec_measure>`) but harmlessly at the very end.
  Classification: a **model x harness tool-call convention mismatch** — Swift's SFT carries
  OpenAI-style text calls; every task where the model chose to patch files through
  `exec_command` (heredocs, sed, cat) passed. Same model, same serve, zero quant/serving
  involvement. n=1 per cell plus one confirming rerun on task6.

Context profile (recorded via the proxy): warm-turn envelope **8,912 tokens** (upstream's
"about 8.6K" estimate confirmed exactly), 4,540 of which is system (two developer items:
16,979-char codex preamble + 3,248-char skills index) + 9 tools incl. a `type=namespace`
stub for subagents (their definitions are NOT embedded — codex defers them) and a zero-desc
`web_search`. Trap peak context 19.5K; task peaks 10.6K-32.3K (task8), cumulative 48K-549K
prompt tokens per task, output 879-14.7K per task. Fastest serve walls of any harness: 26-369 s.

## Pre-registered prediction check

- Trap: PASS (no loop, single edit, self-terminated) — "lean harness => loop-free" held.
- AG-Bench rate: predicted 9-11, got 9 — bottom of the band, with the miss explained by the
  tool-call defect rather than capability.
- Wall: predicted 1100-1800 s, got 1273 — inside the band.
- Context: predicted 6-9K cold, got 8.9K (warm) / 10.3K (trap cold) — on the number.

## Classification for the standing stack

Codex + Strata Swift IQ2_XS = **fastest harness on the card, not yet trustworthy**. The
apply_patch defect is fixable harness-side (a shell wrapper that greps the final text for
`<function=apply_patch>` blocks and executes them would convert both failures into passes;
or a system-prompt line teaching Swift the correct channel). Worth fixing: at fixed wall
1273 s and the leanest envelope-to-speed ratio measured today, a defect-free codex would
rank **#2 on the card behind pi** and #1 on per-task speed. pi remains the reference client.

## Post-verdict clean reruns (2026-10-22, no task modifications)

- **task10 n=2: PASS in 160 s** (proper exec_command patching, ALL OK) — the overnight failure
  was stochastic. Frequency profile of the apply_patch defect: task6 deterministic (0/2,
  identical 24 s collapse), task10 intermittent (1/2). Ceiling: **10/11 with convention-drift
  risk**; the 9/11 n=1 row stands as the honest single-run number per lab convention.
- The AGENTS.md harness-side mitigation idea (owner vetoed: it would unbalance the cross-harness
  comparison) was recorded instead as an upstream Strata report item in NEXT-IDEAS.md Tier 3:
  their release notes list "constrained decoding for calls (item 3 of #3441)" as not done —
  exactly the mechanism that would prevent/regenerate the malformed legacy call.
