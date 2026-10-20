#!/usr/bin/env bash
# Wait (max 90 s) until the boot power-limit unit has applied 165 W, like rtx2080-power-limit.service does.
# Falls through after the timeout so the serve is never blocked forever by a failed limit apply.
for i in $(seq 1 90); do
  pl=$(nvidia-smi --query-gpu=power.limit --format=csv,noheader,nounits 2>/dev/null | head -1 | awk '{printf "%d", $1}')
  [ -n "$pl" ] && [ "$pl" -le 165 ] && exit 0
  sleep 1
done
echo "power limit not at 165 W after 90 s (current: ${pl:-unreadable}); starting serve anyway" >&2
exit 0
