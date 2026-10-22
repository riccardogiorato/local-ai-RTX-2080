#!/bin/bash
# AG-Bench v2.2 x Codex CLI: the 11-task suite through codex exec on the Strata
# Swift-IQ2_XS serve, via the recording proxy (Responses wire). Same task copy rules,
# cap, verify.sh and protected-path checks as the pi bench of record; same shape as
# the claude one (per-task isolated /tmp runroots). The lean scratch CODEX_HOME
# (no desktop plugins/MCP) is used so the measurement matches upstream's tested
# configuration ("system prompt and tools take about 8.6K tokens").
# Usage: bash codex-bench.sh <label> <seconds-cap> [TASK_RE]
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
CODEX_BIN="$HOME/.local/share/mise/installs/codex/0.163.0/bin/codex"
[ -x "$CODEX_BIN" ] || CODEX_BIN=codex
CHOME="$HERE/codex-home"

restore_master_if_dirty() {
  ( cd "$LAB" && git diff --quiet -- benchmarks/agentic-tasks/ 2>/dev/null ) && return 0
  echo "WARN: master task sources were modified during the bench — restoring from git" >&2
  ( cd "$LAB" && git checkout -- benchmarks/agentic-tasks/ 2>/dev/null )
}

curl -s -m 10 -H "Authorization: Bearer local" http://127.0.0.1:8080/v1/models >/dev/null || {
  echo "ABORTED: no serve on 127.0.0.1:8080"; exit 3; }
curl -s -m 5 "$PROXY/_label" -d '{"harness":"codex-warm"}' >/dev/null || {
  echo "ABORTED: proxy not on $PROXY"; exit 4; }

# warm-up gate (same rule: a trivial turn must complete before the batch burns)
WROOT=$(mktemp -d /tmp/agbench-codex-warm-XXXXXX)
mkdir -p "$WROOT/work"
( cd "$WROOT/work" && CODEX_HOME="$CHOME" STRATA_API_KEY=local \
    timeout 240 "$CODEX_BIN" exec --skip-git-repo-check \
    "Reply with the single word OK." < /dev/null ) > "$WROOT/warm.txt" 2>&1
grep -q "^OK" "$WROOT/warm.txt" 2>/dev/null || { echo "ABORTED: codex warm-up failed:"; tail -5 "$WROOT/warm.txt"; exit 2; }
rm -rf "$WROOT"
echo "warm-up ok"

run_task() {
  restore_master_if_dirty
  local task_dir="$1" task_name
  task_name=$(basename "$task_dir")
  local ROOT="/tmp/agbench-codex-${task_name}-$$"
  rm -rf "$ROOT"; mkdir -p "$ROOT/work"
  rsync -a --exclude node_modules --exclude package-lock.json \
        --exclude .build --exclude "service*.rc" "$task_dir/" "$ROOT/work/"
  # MITIGATE=1: harness-side fix candidate for the apply_patch-as-text defect (Swift emits
  # OpenAI-legacy text calls; codex's Responses wire only parses declared tools). Codex
  # injects an AGENTS.md from the repo root into its instructions.
  if [ "${MITIGATE:-0}" = "1" ]; then
    cat > "$ROOT/work/AGENTS.md" <<'EOF'
# Tool-calling note (harness-mitigation experiment 2026-10-22)

`apply_patch` is NOT a separate tool in this environment. To edit files, use the
shell tool (exec_command): write files with shell commands, or run apply_patch as
a shell command inside the shell tool. Never emit `<function=apply_patch>` blocks
or any other `<function=NAME>` markup - it is not parsed and nothing will execute.
EOF
  fi
  if [ -f "$task_dir/service.rc" ]; then ( . "$task_dir/service.rc" ) || echo "WARN: service.rc failed"; fi
  if [ -f "$task_dir/service-cleanup.rc" ]; then ( . "$task_dir/service-cleanup.rc" ) || true; fi
  curl -s "$PROXY/_label" -d "{\"harness\":\"codex-$task_name\"}" >/dev/null
  local t0=$SECONDS
  ( cd "$ROOT/work" && CODEX_HOME="$CHOME" STRATA_API_KEY=local \
      timeout "$CAP" "$CODEX_BIN" exec --skip-git-repo-check \
      "$(cat "$ROOT/work/TASK.md")" < /dev/null ) > "$ROOT/codex.out" 2>"$ROOT/codex.err"
  local rc=$?
  local wall=$((SECONDS - t0))
  local DEST="$HERE/runs/$task_name"
  rm -rf "$DEST"; mkdir -p "$DEST"
  cp -a "$ROOT/codex.out" "$ROOT/codex.err" "$DEST/"
  ( cd "$ROOT/work" && tar cf "$DEST/workdir-after.tar" --exclude node_modules . 2>/dev/null )
  local passed=false note=""
  if ( cd "$ROOT/work" && bash verify.sh >/dev/null 2>&1 ); then passed=true; fi
  local protected_dirs=(tests protected)
  [ "$task_name" = "task8-tb-broken-python" ] && protected_dirs=(tests wheels)
  local bad=0
  for pd in "${protected_dirs[@]}"; do
    [ -d "$ROOT/work/$pd" ] || continue
    diff -r --brief "$task_dir/$pd" "$ROOT/work/$pd" >/dev/null 2>&1 || bad=1
  done
  if [ "$bad" = "1" ] && [ "$passed" = "true" ]; then passed=false; note="protected-paths modified"; fi
  [ -f "$task_dir/service-cleanup.rc" ] && ( . "$task_dir/service-cleanup.rc" ) || true
  rm -rf "$ROOT"
  AG_OUT="$OUT" TASK="$task_name" LABEL="$LABEL" WALL="$wall" PASSED="$passed" \
  RC="$rc" NOTE="$note" OUTFILE="$DEST/codex.out" python3 - <<'EOF'
import json, os, re
task, label = os.environ['TASK'], os.environ['LABEL']
wall, passed = int(os.environ['WALL']), os.environ['PASSED'] == 'true'
rc, note = int(os.environ['RC']), os.environ['NOTE']
tokens_used = None
head = ''
try:
    txt = open(os.environ['OUTFILE']).read()
    m = re.search(r'tokens used\s+([0-9,]+)', txt)
    if m: tokens_used = int(m.group(1).replace(',', ''))
    head = txt[-1200:]
except Exception:
    pass
suspect = passed and tokens_used is not None and tokens_used < 4000 and wall < 30
row = {"model": label, "task": task, "passed": passed, "wall_s": wall,
       "suspect_garbage_pass": suspect, "codex_rc": rc, "tokens_used": tokens_used,
       "note": note, "answer_tail_head": head[:200]}
with open(os.environ['AG_OUT'], 'a') as f:
    f.write(json.dumps(row) + '\n')
print(json.dumps(row))
EOF
  echo "---- $task_name: passed=$passed wall=${wall}s rc=$rc $note"
}

echo "AG-Bench x Codex model=$LABEL cap=${CAP}s filter=$TASK_RE"
for entry in "$TASKS_DIR"/task*/; do
  [[ "$(basename "$entry")" =~ $TASK_RE ]] || continue
  run_task "$entry"
done
echo "DONE — results in $OUT"