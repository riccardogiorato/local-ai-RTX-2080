#!/bin/bash
# AG-Bench: run Pi coding agent exclusively on a local llama-server model
# across the task set, record pass/fail + wall time per task to JSONL.
#
# Usage: bash agentic-bench.sh <model-label> <seconds-cap-per-task>
# Prereq: llama-server up on :8080 with --alias local-model; pi installed;
#         ~/.pi/agent/models.json has llamacpp-local/local-model.
set -u
LABEL="$1"          # e.g. qwen35-9b, gemma-e4b, thinkingcap-27b
CAP="${2:-600}"
BENCH_DIR="$(cd "$(dirname "$0")" && pwd)"
TASKS_DIR="$BENCH_DIR/agentic-tasks"
OUT="$BENCH_DIR/results/${LABEL}-$(date +%Y%m%d-%H%M%S).jsonl"
mkdir -p "$BENCH_DIR/results" /tmp/agentic-run

run_task() {
  restore_master_if_dirty
  local task_dir="$1" task_name
  task_name=$(basename "$task_dir")
  local work="/tmp/agentic-run/${LABEL}/${task_name}"
  rm -rf "$work"; mkdir -p "$work"
  # copy sources but not node_modules/locks — deps install on demand
  rsync -a --exclude node_modules --exclude package-lock.json --exclude .build --exclude "service*.rc" "$task_dir/" "$work/"
  # task-side service bootstrap (e.g. ancient-puzzle decryptor): sourced from
  # the MASTER dir so secrets/infra stay out of the agent's workdir.
  if [ -f "$task_dir/service.rc" ]; then
    ( . "$task_dir/service.rc" ) || echo "WARN: service.rc failed for $task_name"
  fi
  local t0=$SECONDS
  # zero-byte retry: a pi session can die pre-header with an empty pi-session.jsonl
  # (startup stall observed ~1/75 manual rate, root cause still open — NEXT-IDEAS
  # Tier 1 pi-hang item). Retry the task once; if the retry is also zero-byte,
  # let it fall through to verify (honest fail) and flag it in the row.
  local zero_byte_retry=0
  for attempt in 1 2; do
    ( cd "$work" && PI_OFFLINE=${PI_OFFLINE:-1} timeout "$CAP" pi --provider llamacpp-local --model local-model \
        --mode json --no-session \
        -p "$(cat "$work/TASK.md")" < /dev/null ) > "$work/pi-session.jsonl" 2>"$work/pi-errors.log"
    [ -s "$work/pi-session.jsonl" ] && break
    if [ "$attempt" = "1" ]; then
      zero_byte_retry=1
      echo "WARN: $task_name produced a ZERO-BYTE pi session — retrying task once" >&2
      restore_master_if_dirty
      sleep 5
    else
      echo "WARN: $task_name zero-byte after retry — recording as failed" >&2
    fi
  done
  if [ -f "$task_dir/service-cleanup.rc" ]; then
    ( . "$task_dir/service-cleanup.rc" ) || true
  fi
  local wall=$((SECONDS - t0))
  local passed=false
  if ( cd "$work" && bash verify.sh >/dev/null 2>&1 ); then passed=true; fi
  # PROTECTED-CHECK: rule violations = fail regardless of verify (models edit tests/protected)
  if ( cd "$work" && git diff --quiet -- tests/ 2>/dev/null &&        [ -z "$(find protected -newer verify.sh -type f 2>/dev/null | head -1)" ] ); then :; else
    if [ -d "$work/tests" ] || [ -d "$work/protected" ]; then
      ( cd "$work" && sha_check="$( (git -C "$task_dir" rev-parse 2>/dev/null || echo x) )" ; true )
      # simpler + deterministic: compare against the pristine master copies
      bad=0
      for pd in tests protected; do
        [ -d "$work/$pd" ] || continue
        if ! diff -r --brief "$task_dir/$pd" "$work/$pd" >/dev/null 2>&1; then bad=1; fi
      done
      [ "$bad" = "1" ] && { passed=false; echo "NOTE: $task_name FAILED the protected-paths check (tests/or protected modified)"; }
    fi
  fi
  AG_OUT="$OUT" python3 - "$task_name" "$LABEL" "$wall" "$passed" "$work" "$zero_byte_retry" <<'EOF'
import json, sys, os
task, label, wall, passed, work, zero_byte_retry = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4] == 'true', sys.argv[5], sys.argv[6] == '1'
out = os.environ['AG_OUT']
tool_calls = 0
finish = "unknown"
with open(os.path.join(work, 'pi-session.jsonl')) as f:
    for line in f:
        try: ev = json.loads(line)
        except Exception: continue
        t = ev.get('type') or ev.get('event') or ''
        if 'tool' in str(t).lower(): tool_calls += 1
        if ev.get('stop') or ev.get('finish'): finish = ev.get('stop') or ev.get('finish')
suspect = passed and tool_calls == 0 and wall < 30
row = {"model": label, "task": task, "passed": passed, "wall_s": wall, "suspect_garbage_pass": suspect,
      "tool_calls": tool_calls, "finish": str(finish),
      "zero_byte_retry": zero_byte_retry}
with open(out, 'a') as f: f.write(json.dumps(row) + '\n')
print(json.dumps(row))
EOF
}

echo "AG-Bench model=$LABEL cap=${CAP}s"
# master-source integrity: heard from the LFM run — models can escape the work dir and
# edit task sources in the repo. Hash everything now; re-check BEFORE each task and restore
# from git if a previous run trampled them.
MASTER_INTEGRITY=/tmp/agentic-master-hashes.$$.txt
(cd "$TASKS_DIR" && find task* -type f ! -path '*/node_modules/*' | sort | xargs sha256sum) > "$MASTER_INTEGRITY" 2>/dev/null
restore_master_if_dirty() {
  (cd "$(dirname "$TASKS_DIR")" && git diff --quiet -- benchmarks/agentic-tasks/ 2>/dev/null) && return 0
  echo "WARN: master task sources were modified during the bench — restoring from git" >&2
  (cd "$(dirname "$TASKS_DIR")" && git checkout -- benchmarks/agentic-tasks/ 2>/dev/null)
  (cd "$TASKS_DIR" && find task* -type f ! -path '*/node_modules/*' | sort | xargs sha256sum) > "$MASTER_INTEGRITY" 2>/dev/null
}
# slots-readiness gate (see NOTE above)
for i in $(seq 1 90); do
  curl -s --max-time 3 localhost:8080/slots 2>/dev/null | grep -q '"id"' && { echo "slots ready after $((i*2))s"; break; }
  sleep 2
done
# NOTE: gate readiness on /slots, not /health — draft-context models (DSpark etc.)
# answer /health while still in "Loading model" and 503 every completion for ~30-60s.

# Warm-up gate: a trivial pi invocation must complete before the batch runs.
# Empirically, the first pi batch launched right after a container swap can hang
# client-side with zero-byte sessions; a successful warm-up clears it.
# WARM_TIMEOUT can be raised for thinking-mode models that spend minutes of
# reasoning tokens on a trivial turn (observed: MiMo ~3.7K tokens on "say OK").
# WARM_BYPASS=1 skips the gate after the attempts fail: for always-thinking
# agentic distills (MiMo), the trivial "say OK" turn can sample into a fabricated
# whole-mission runaway (observed 2026-09-28: watch/audio brand pages, playwright
# screenshots) that never terminates — a warm-up property, not a serve fault.
# Only use it after verifying the serve directly (/v1/chat completions sane);
# task outcomes are unaffected because real TASK.md prompts anchor the model.
# PREFLIGHT (2026-10-07): pi exits 0 even on connection errors, so a dead serve
# produces garbage rows (one even "passed" a lenient verifier). Refuse to run.
if ! curl -s -m 10 http://127.0.0.1:8080/health >/dev/null 2>&1; then
  echo "AG-BENCH ABORTED: no serve on 127.0.0.1:8080/health (preflight) - not burning the batch"
  exit 3
fi
WARM_TIMEOUT="${WARM_TIMEOUT:-90}"
WARM_BYPASS="${WARM_BYPASS:-0}"
WARM_OK=""
for attempt in 1 2 3; do
  if PI_OFFLINE=${PI_OFFLINE:-1} timeout "$WARM_TIMEOUT" pi --provider llamacpp-local --model local-model \
      --mode json --no-session -p "Reply with the single word OK." < /dev/null \
      > /tmp/agentic-warmup.jsonl 2>/dev/null; then
    if grep -q '"stopReason":"stop"' /tmp/agentic-warmup.jsonl 2>/dev/null; then
      WARM_OK="yes"; echo "warm-up attempt $attempt: ok (model replied)"; break
    else
      echo "warm-up attempt $attempt: pi exited but NO model reply (connection error class) - retrying"
    fi
  else
    echo "warm-up attempt $attempt: failed/timed out (90s) — retrying"; sleep 5
  fi
done
if [ -z "$WARM_OK" ]; then
  if [ "$WARM_BYPASS" = "1" ]; then
    echo "WARM-UP GATE BYPASSED (WARM_BYPASS=1, model=$LABEL) — serve sanity must be verified by direct probe and recorded in evidence"
  else
    echo "AG-BENCH model=$LABEL ABORTED: warm-up never passed, refusing to burn the task batch in silence"; exit 2
  fi
fi
# TASK_RE: optional bash-regex filter on task dir names (e.g. TASK_RE='task(7|8|9|10|11)'
# to run only the v2.1 additions). Default runs the whole suite.
TASK_RE="${TASK_RE:-task.*}"
for entry in "$TASKS_DIR"/task*/; do
  [[ "$(basename "$entry")" =~ $TASK_RE ]] || continue
  run_task "$entry"
done
echo "DONE — results in $OUT"