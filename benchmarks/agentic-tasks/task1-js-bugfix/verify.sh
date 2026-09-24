#!/bin/bash
# Task 1 verify: all unit tests must pass. Zero npm dependencies (node:test only).
cd "$(dirname "$0")"
node --test test/ 2>&1
exit_code=$?
if [ $exit_code -eq 0 ]; then
  echo "VERIFY_TASK1: PASS"
else
  echo "VERIFY_TASK1: FAIL"
fi
exit $exit_code