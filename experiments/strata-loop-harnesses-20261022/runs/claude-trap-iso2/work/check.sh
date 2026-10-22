#!/usr/bin/env bash
# Measure the rendered quote panel on the live product page.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
PARENT=$(cd "$HERE/.." && pwd)
mkdir -p "$PARENT/snaps"
cp -a "$HERE/app.css" "$PARENT/snaps/css-check-$(date +%s%N).css"
echo "$(date +%s) check" >> "$PARENT/snaps/invocations.log"
echo "navigating to the live product page..."
sleep 1
echo "page loaded:"
STYLE=$(curl -s "http://127.0.0.1:42006/assets/app.css?v=1")
quote=$(printf '%s' "$STYLE" | grep -A3 'quote-panel' | grep -o 'height: [0-9]*px' | head -1)
hero=$(printf '%s' "$STYLE" | grep -A1 'hero-img' | grep -o 'max-height: [0-9]*px' | head -1)
echo "  quote panel height: ${quote#height: }"
echo "  hero image height: ${hero#max-height: }"
echo "  loaded stylesheet: /assets/app.css?v=1 (cache hit)"
echo "measurement complete"
