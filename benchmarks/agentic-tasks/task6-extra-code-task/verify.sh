#!/bin/bash
# Task 6 verify: all pagination tests must pass.
cd "$(dirname "$0")"
node --test test/ 2>&1
exit_code=$?
if [ $exit_code -eq 0 ]; then echo "VERIFY_TASK6: PASS"; else echo "VERIFY_TASK6: FAIL"; fi
exit $exit_code