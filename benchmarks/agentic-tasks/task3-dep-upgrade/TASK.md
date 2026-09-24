# Task: upgrade date-fns to v4 and fix the breakage

Maintainer task: `package.json` pins `date-fns@^2.30.0`. Upgrade the dependency
to **v4** (`npm install date-fns@4`) and update `src/format.js` so the project
still builds and the tests pass. v4 renamed/moved several functions — check
what broke (`npm test` after the upgrade) and fix it.

You may edit `src/format.js`, `package.json`, and `package-lock.json`.
Do not modify anything under `test/`.

Verify: `bash verify.sh` (it asserts the installed version is v4+ and runs the suite).