#!/bin/bash
# Task 2 verify: PricingTable must SSR-render to the exact markup contract.
cd "$(dirname "$0")"
if ! command -v node >/dev/null; then echo "VERIFY_TASK2: FAIL (no node)"; exit 1; fi
[ -d node_modules/react ] || npm install --no-audit --no-fund --silent >/dev/null 2>&1
node render-check.mjs
exit_code=$?
if [ $exit_code -eq 0 ]; then
  echo "VERIFY_TASK2: PASS"
else
  echo "VERIFY_TASK2: FAIL"
fi
exit $exit_code