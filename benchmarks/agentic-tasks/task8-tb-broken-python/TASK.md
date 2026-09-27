# Task: repair the broken Python environment

The virtualenv at `protected/venv` in this directory is broken — `pip` (and its
packaging friends) can no longer install anything. Diagnose and repair the
environment so that pip works again.

Rules:
- You may not modify anything under `wheels/` or `tests/` or rename/delete the
  venv wholesale and recreate it from scratch — REPAIR it in place (recreating
  the venv is a valid unix move but defeats the exercise; the oracle checks
  the same interpreter path works).
- Success: `protected/venv/bin/python -m pip --version` works.

Verify: `bash verify.sh`.
