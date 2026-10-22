#!/usr/bin/env bash
# One full stale-trap run: scaffold a fresh scratch repo + stale server for <harness>,
# run the agent against it through the recording proxy, stop the server, keep evidence.
# Usage: run-trap.sh <pi|opencode|grok|claude> <port>
set -u
H="$1"; PORT="$2"
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$HERE/runs/$H-trap"
rm -rf "$ROOT"; mkdir -p "$ROOT"
python3 "$HERE/scaffold.py" "$ROOT" "$PORT"
# the "live page": frozen old asset, never restarted, nothing the agent can redeploy
( setsid python3 -m http.server "$PORT" --bind 127.0.0.1 \
    --directory "$ROOT/stale" > "$ROOT/stale-server.log" 2>&1 < /dev/null & )
for i in $(seq 1 20); do
  curl -s --max-time 2 "http://127.0.0.1:$PORT/assets/app.css?v=1" | grep -q "height: 163px" && break
  sleep 0.5
done
curl -s "http://127.0.0.1:$PORT/assets/app.css?v=1" | grep -q "height: 163px" || { echo "stale server failed to start on $PORT"; exit 3; }
echo "stale server up on $PORT, serving the 163px asset"
bash "$HERE/run-one.sh" "$H-trap" "$ROOT/work" "$ROOT/work/TASK.md"
RC=$?
PID=$(ss -tlnp 2>/dev/null | grep ":$PORT " | grep -oP 'pid=\K[0-9]+' | head -1)
[ -n "$PID" ] && kill "$PID"
echo "trap $H rc=$RC"
echo "---- first check.sh output this run would see: quote=163px (frozen) ----"
cat "$ROOT/snaps/invocations.log" 2>/dev/null || echo "(no build/check invocations)"
exit $RC
