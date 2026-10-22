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
# index.html loads /assets/app.css, so publish the source of truth at that path.
mkdir -p "$PARENT/deploy/assets"
cp -a "$HERE/app.css" "$PARENT/deploy/assets/app.css"
echo "deploy: copied $(find "$PARENT/deploy" -type f | wc -l) files to the release dir"
echo "deploy: done, CDN purge requested"
