#!/usr/bin/env bash
# Isolated-layout trap run for the definitive four-harness comparison.
# The runroot lives alone under /tmp (tmpfs): no experiment files within reach of
# cwd escapes, so harnesses cannot read the trap's README, the proxy, or each
# other's transcripts. Same trap mechanics as run-trap.sh.
# Usage: run-trap2.sh <pi|opencode|grok|claude> <port> <suffix>
set -u
H="$1"; PORT="$2"; SUFFIX="${3:-iso}"
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="/tmp/loopexp-$SUFFIX/$H-trap"
rm -rf "$ROOT"; mkdir -p "$ROOT"
python3 "$HERE/scaffold.py" "$ROOT" "$PORT"
( cd / && setsid python3 -m http.server "$PORT" --bind 127.0.0.1 \
    --directory "$ROOT/stale" > "$ROOT/stale-server.log" 2>&1 < /dev/null & )
for i in $(seq 1 20); do
  curl -s --max-time 2 "http://127.0.0.1:$PORT/assets/app.css?v=1" | grep -q "height: 163px" && break
  sleep 0.5
done
curl -s "http://127.0.0.1:$PORT/assets/app.css?v=1" | grep -q "height: 163px" || { echo "stale server failed to start on $PORT"; exit 3; }
echo "stale server up on $PORT (isolated root $ROOT)"
bash "$HERE/run-one.sh" "$H-trap-$SUFFIX" "$ROOT/work" "$ROOT/work/TASK.md"
RC=$?
PID=$(ss -tlnp 2>/dev/null | grep ":$PORT " | grep -oP 'pid=\K[0-9]+' | head -1)
[ -n "$PID" ] && kill "$PID"
# preserve evidence inside the experiment dir (the /tmp runroot dies with the machine)
DEST="$HERE/runs/$H-trap-$SUFFIX"
rm -rf "$DEST"; mkdir -p "$DEST"
cp -a "$ROOT/snaps" "$ROOT/stale-server.log" "$DEST/" 2>/dev/null
cp -a "$ROOT/work" "$DEST/" 2>/dev/null
cp -a "$ROOT"/*.out "$ROOT"/*.err "$DEST/" 2>/dev/null
rm -rf "$ROOT"
echo "trap $H-$SUFFIX rc=$RC"
exit $RC
