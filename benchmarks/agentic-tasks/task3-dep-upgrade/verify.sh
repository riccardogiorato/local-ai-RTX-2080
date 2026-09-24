#!/bin/bash
# Task 3 verify: date-fns upgraded to v4+ AND all tests pass on the new API.
cd "$(dirname "$0")"
export LC_ALL=C
[ -d node_modules/date-fns ] || npm install --no-audit --no-fund --silent >/dev/null 2>&1
node --test test/ 2>&1
exit_code=$?
if [ $exit_code -eq 0 ]; then echo "VERIFY_TASK3: PASS"; else echo "VERIFY_TASK3: FAIL"; fi
exit $exit_code