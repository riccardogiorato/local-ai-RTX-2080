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
  local task_dir="$1" task_name
  task_name=$(basename "$task_dir")
  local work="/tmp/agentic-run/${LABEL}/${task_name}"
  rm -rf "$work"; mkdir -p "$work"
  # copy sources but not node_modules/locks — deps install on demand
  rsync -a --exclude node_modules --exclude package-lock.json --exclude .build "$task_dir/" "$work/"
  local t0=$SECONDS
  ( cd "$work" && timeout "$CAP" pi --provider llamacpp-local --model local-model \
      --mode json --no-session \
      -p "$(cat "$work/TASK.md")" ) > "$work/pi-session.jsonl" 2>"$work/pi-errors.log"
  local wall=$((SECONDS - t0))
  local passed=false
  if ( cd "$work" && bash verify.sh >/dev/null 2>&1 ); then passed=true; fi
  AG_OUT="$OUT" python3 - "$task_name" "$LABEL" "$wall" "$passed" "$work" <<'EOF'
import json, sys, os
task, label, wall, passed, work = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4] == 'true', sys.argv[5]
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
row = {"model": label, "task": task, "passed": passed, "wall_s": wall,
      "tool_calls": tool_calls, "finish": str(finish)}
with open(out, 'a') as f: f.write(json.dumps(row) + '\n')
print(json.dumps(row))
EOF
}

echo "AG-Bench model=$LABEL cap=${CAP}s"
# Warm-up gate: a trivial pi invocation must complete before the batch runs.
# Empirically, the first pi batch launched right after a container swap can hang
# client-side with zero-byte sessions; a successful warm-up clears it.
# WARM_TIMEOUT can be raised for thinking-mode models that spend minutes of
# reasoning tokens on a trivial turn (observed: MiMo ~3.7K tokens on "say OK").
WARM_TIMEOUT="${WARM_TIMEOUT:-90}"
WARM_OK=""
for attempt in 1 2 3; do
  if timeout "$WARM_TIMEOUT" pi --provider llamacpp-local --model local-model \
      --mode json --no-session -p "Reply with the single word OK." \
      > /tmp/agentic-warmup.jsonl 2>/dev/null; then
    WARM_OK="yes"; echo "warm-up attempt $attempt: ok"; break
  else
    echo "warm-up attempt $attempt: failed/timed out (90s) — retrying"; sleep 5
  fi
done
[ -n "$WARM_OK" ] || { echo "AG-BENCH model=$LABEL ABORTED: warm-up never passed, refusing to burn the task batch in silence"; exit 2; }
for entry in "$TASKS_DIR"/task*/; do
  run_task "$entry"
done
echo "DONE — results in $OUT"