#!/bin/bash
# Task 5 verify: src/inventory.js must be migrated to src/inventory.ts,
# with the import updated in index.ts, and tsc must typecheck cleanly.
cd "$(dirname "$0")"
[ -f src/inventory.ts ] || { echo "VERIFY_TASK5: FAIL (src/inventory.ts missing)"; exit 1; }
[ ! -f src/inventory.js ] || { echo "VERIFY_TASK5: FAIL (old .js still present)"; exit 1; }
npx --yes typescript@5 tsc -p tsconfig.json 2>&1
exit_code=$?
if [ $exit_code -eq 0 ]; then echo "VERIFY_TASK5: PASS"; else echo "VERIFY_TASK5: FAIL"; fi
exit $exit_code