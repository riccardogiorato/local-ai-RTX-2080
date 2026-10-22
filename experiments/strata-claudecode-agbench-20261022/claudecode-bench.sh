#!/bin/bash
# AG-Bench v2.2 x Claude Code: run the 11-task suite through Claude Code against
# the standing Strata serve (Swift IQ2_XS), recorded via the loop-study proxy
# (PROXY_OUT_DIR points the capture into this experiment). Same task copy rules,
# cap, verify.sh and protected-path checks as benchmarks/agentic-bench.sh (pi).
# After the loop findings, each task gets its own empty /tmp runroot so no
# sibling task, benchmark infra, or answer-key material sits within a cwd escape.
# Usage: bash claudecode-bench.sh <label> <seconds-cap> [TASK_RE]
set -u
LABEL="$1"
CAP="${2:-900}"
TASK_RE="${3:-task.*}"
LAB=/home/riccardogiorato/Desktop/github/local-ai-rtx2080
TASKS_DIR="$LAB/benchmarks/agentic-tasks"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/results/${LABEL}-$(date +%Y%m%d-%H%M%S).jsonl"
mkdir -p "$HERE/results" "$HERE/runs"
PROXY=http://127.0.0.1:8081

restore_master_if_dirty() {
  ( cd "$LAB" && git diff --quiet -- benchmarks/agentic-tasks/ 2>/dev/null ) && return 0
  echo "WARN: master task sources were modified during the bench — restoring from git" >&2
  ( cd "$LAB" && git checkout -- benchmarks/agentic-tasks/ 2>/dev/null )
}

# preflight: the serve must be alive and answering
curl -s -m 10 -H "Authorization: Bearer local" http://127.0.0.1:8080/v1/models >/dev/null || {
  echo "ABORTED: no serve on 127.0.0.1:8080"; exit 3; }
# and the recording proxy must be up
curl -s -m 5 "$PROXY/_label" -d "{\"harness\":\"claudecode-warm\"}" >/dev/null || {
  echo "ABORTED: proxy not on $PROXY"; exit 4; }

# warm-up: one trivial claude turn must complete before the batch burns
WARM_OK=""
for attempt in 1 2 3; do
  WROOT=$(mktemp -d /tmp/agbench-claude-warm-XXXXXX)
  mkdir -p "$WROOT/work" "$WROOT/claude-config"
  ( cd "$WROOT/work" && timeout 120 env \
      CLAUDE_CONFIG_DIR="$WROOT/claude-config" \
      ANTHROPIC_BASE_URL="$PROXY" \
      ANTHROPIC_API_KEY=local ANTHROPIC_AUTH_TOKEN=local \
      ANTHROPIC_MODEL=local-model \
      ANTHROPIC_SMALL_FAST_MODEL=local-model \
      ANTHROPIC_DEFAULT_HAIKU_MODEL=local-model \
      ANTHROPIC_DEFAULT_SONNET_MODEL=local-model \
      ANTHROPIC_DEFAULT_OPUS_MODEL=local-model \
      CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
      DISABLE_TELEMETRY=1 \
      claude -p "Reply with the single word OK." --model local-model \
      --dangerously-skip-permissions --output-format json ) \
      > "$WROOT/warm.json" 2>"$WROOT/warm.err"
  grep -q '"subtype":"success"' "$WROOT/warm.json" 2>/dev/null && WARM_OK="yes" && break
  echo "warm-up attempt $attempt failed:"; tail -2 "$WROOT/warm.err" 2>/dev/null
  sleep 5
done
[ -n "$WARM_OK" ] || { echo "ABORTED: claude warm-up never passed"; exit 2; }
echo "warm-up ok"

run_task() {
  restore_master_if_dirty
  local task_dir="$1" task_name
  task_name=$(basename "$task_dir")
  # isolated runroot: only this task's workdir and its private claude config
  local ROOT="/tmp/agbench-claude-${task_name}-$$"
  rm -rf "$ROOT"; mkdir -p "$ROOT/work" "$ROOT/claude-config"
  rsync -a --exclude node_modules --exclude package-lock.json \
        --exclude .build --exclude "service*.rc" "$task_dir/" "$ROOT/work/"
  if [ -f "$task_dir/service.rc" ]; then ( . "$task_dir/service.rc" ) || echo "WARN: service.rc failed"; fi
  if [ -f "$task_dir/service-cleanup.rc" ]; then ( . "$task_dir/service-cleanup.rc" ) || true; fi
  # tag so proxy rows map to this task
  curl -s "$PROXY/_label" -d "{\"harness\":\"claudecode-$task_name\"}" >/dev/null
  local t0=$SECONDS
  ( cd "$ROOT/work" && timeout "$CAP" env \
      CLAUDE_CONFIG_DIR="$ROOT/claude-config" \
      ANTHROPIC_BASE_URL="$PROXY" \
      ANTHROPIC_API_KEY=local ANTHROPIC_AUTH_TOKEN=local \
      ANTHROPIC_MODEL=local-model \
      ANTHROPIC_SMALL_FAST_MODEL=local-model \
      ANTHROPIC_DEFAULT_HAIKU_MODEL=local-model \
      ANTHROPIC_DEFAULT_SONNET_MODEL=local-model \
      ANTHROPIC_DEFAULT_OPUS_MODEL=local-model \
      CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
      DISABLE_TELEMETRY=1 \
      claude -p "$(cat "$ROOT/work/TASK.md")" --model local-model \
      --dangerously-skip-permissions --max-turns 64 --output-format json ) \
      > "$ROOT/result.json" 2>"$ROOT/claude.err"
  local rc=$?
  local wall=$((SECONDS - t0))
  # keep full evidence (transcript json + stderr) inside the experiment
  local DEST="$HERE/runs/$task_name"
  rm -rf "$DEST"; mkdir -p "$DEST"
  cp -a "$ROOT/result.json" "$ROOT/claude.err" "$ROOT/claude-config" "$DEST/" 2>/dev/null
  ( cd "$ROOT/work" && tar cf "$DEST/workdir-after.tar" . 2>/dev/null )
  rm -f "$DEST/claude-config"/*.lock 2>/dev/null
  local passed=false note=""
  if ( cd "$ROOT/work" && bash verify.sh >/dev/null 2>&1 ); then passed=true; fi
  # PROTECTED-CHECK (same rule as pi's bench; task8's immutables are tests/ + wheels/)
  local protected_dirs=(tests protected)
  [ "$task_name" = "task8-tb-broken-python" ] && protected_dirs=(tests wheels)
  local bad=0
  for pd in "${protected_dirs[@]}"; do
    [ -d "$ROOT/work/$pd" ] || continue
    diff -r --brief "$task_dir/$pd" "$ROOT/work/$pd" >/dev/null 2>&1 || bad=1
  done
  if [ "$bad" = "1" ]; then
    if [ "$passed" = "true" ]; then passed=false; note="protected-paths modified"; fi
  fi
  [ -f "$task_dir/service-cleanup.rc" ] && ( . "$task_dir/service-cleanup.rc" ) || true
  rm -rf "$ROOT"
  AG_OUT="$OUT" TASK="$task_name" LABEL="$LABEL" WALL="$wall" PASSED="$passed" \
  RC="$rc" NOTE="$note" RESULT_JSON="$DEST/result.json" python3 - <<'EOF'
import json, os, sys
task, label = os.environ['TASK'], os.environ['LABEL']
wall, passed = int(os.environ['WALL']), os.environ['PASSED'] == 'true'
rc, note = int(os.environ['RC']), os.environ['NOTE']
num_turns, subtype, result_text = None, 'n/a', ''
try:
    r = json.load(open(os.environ['RESULT_JSON']))
    num_turns = r.get('num_turns'); subtype = r.get('subtype') or 'n/a'
    result_text = str(r.get('result'))[:2000]
except Exception:
    pass
suspect = passed and (num_turns == 0 or num_turns is None) and wall < 30
row = {"model": label, "task": task, "passed": passed, "wall_s": wall,
       "suspect_garbage_pass": suspect, "claude_rc": rc, "num_turns": num_turns,
       "claude_subtype": subtype, "note": note, "final_answer_head": result_text[:200]}
with open(os.environ['AG_OUT'], 'a') as f:
    f.write(json.dumps(row) + '\n')
print(json.dumps(row))
EOF
  echo "---- $task_name: passed=$passed wall=${wall}s rc=$rc $note"
}

echo "AG-Bench x Claude Code model=$LABEL cap=${CAP}s filter=$TASK_RE"
for entry in "$TASKS_DIR"/task*/; do
  [[ "$(basename "$entry")" =~ $TASK_RE ]] || continue
  run_task "$entry"
done
echo "DONE — results in $OUT"