# Task: fix the pagination helper

`lib/paginate.js` is subtly wrong (off-by-one class bugs). The test suite in
`test/` defines the exact contract, including sorting and edge cases.

Rules:
- You may only edit `lib/paginate.js`. Do not modify the tests.
- All tests must pass.

Verify: `bash verify.sh`.