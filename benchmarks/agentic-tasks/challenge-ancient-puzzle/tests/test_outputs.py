# Ported from terminal-bench(original-tasks)/ancient-puzzle (MIT). Plain-python.
import sys
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
results = BASE / "results.txt"
expected = "What is etched, endures.\n"
if not results.exists():
    print("FAIL exists: results.txt was not created"); sys.exit(1)
print("ok exists")
if results.read_text() != expected:
    print(f"FAIL content: got {results.read_text()!r}, want {expected!r}"); sys.exit(1)
print("ok content")
print("ALL OK")
