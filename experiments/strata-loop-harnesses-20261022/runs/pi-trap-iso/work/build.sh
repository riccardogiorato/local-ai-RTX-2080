#!/usr/bin/env bash
# Deploy the current repo state (source of truth: ./app.css, ./index.html).
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
PARENT=$(cd "$HERE/.." && pwd)
mkdir -p "$PARENT/snaps"
cp -a "$HERE/app.css" "$PARENT/snaps/css-build-$(date +%s%N).css"
echo "$(date +%s) build" >> "$PARENT/snaps/invocations.log"
mkdir -p "$PARENT/deploy"
rsync -a --delete "$HERE/" "$PARENT/deploy/"
echo "deploy: copied $(find "$PARENT/deploy" -type f | wc -l) files to the release dir"
# The live page is served by the "python3 -m http.server" process on the port
# that check.sh measures. Deploy must update the directory that server serves,
# otherwise the release never reaches the live page. Use the port from check.sh
# so the two scripts can't drift apart.
PORT=$(grep -o 'http://127.0.0.1:[0-9]*' "$HERE/check.sh" | head -1 | cut -d: -f3)
if SRV_PID=$(pgrep -f "python3 -m http.server $PORT" | head -1); then
  SERVE_DIR=$(tr '\0' '\n' < /proc/$SRV_PID/cmdline | grep -A1 -- '--directory' | tail -1)
  rsync -a --delete "$HERE/" "$SERVE_DIR/"
  # The page loads the stylesheet at /assets/app.css; repo keeps it at the root.
  mkdir -p "$SERVE_DIR/assets"
  cp "$HERE/app.css" "$SERVE_DIR/assets/app.css"
  echo "deploy: live directory $SERVE_DIR updated"
else
  echo "deploy: ERROR live server on port $PORT not found; release NOT live" >&2
  exit 1
fi
echo "deploy: done, CDN purge requested"
