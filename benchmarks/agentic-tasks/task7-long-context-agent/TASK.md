# Task: make the gateway spec-compliant

The `src/gateway.js` module violates the project's documented API contract.
The authoritative specification lives somewhere in `docs/` — a series of
architecture decision records (ADRs). Somewhere in those ADRs the exact
required header names and the exhaustion behavior are specified (mind the
ADR series' internal supersession notes — later decisions may override
earlier ones).

Rules:
- You may only edit `src/gateway.js`. Do not modify tests or docs.
- All tests must pass.

Verify: `bash verify.sh`.
