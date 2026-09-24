#!/bin/bash
# Task 4 verify: pytest suite must pass (pytest provided via uv, no system install).
cd "$(dirname "$0")"
uv run --quiet --with pytest python -m pytest test_metrics.py -q 2>&1
exit_code=$?
if [ $exit_code -eq 0 ]; then echo "VERIFY_TASK4: PASS"; else echo "VERIFY_TASK4: FAIL"; fi
exit $exit_code