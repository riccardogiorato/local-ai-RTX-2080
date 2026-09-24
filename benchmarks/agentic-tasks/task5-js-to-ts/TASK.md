# Task: migrate src/inventory.js to TypeScript

Maintainer task: convert `src/inventory.js` into typed TypeScript:

1. Create `src/inventory.ts` fully typed (strict mode is on): define the
   `Item` interface, type both functions' parameters and return values,
   remove the `.js` file after migrating.
2. `src/index.ts` imports `./inventory.js` (module ESM convention) — update
   the import if needed, but its behavior must not change.
3. `npx tsc -p tsconfig.json` must typecheck with zero errors.

You may edit/create files under `src/` only. Do not modify `tsconfig.json`
or `verify.sh`.

Verify: `bash verify.sh`.