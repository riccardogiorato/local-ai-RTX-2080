# Ported from terminal-bench(original-tasks)/assign-seats (MIT). Plain-python.
import sys
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent

def check(name, cond, msg):
    if not cond: print(f"FAIL {name}: {msg}"); sys.exit(1)
    print(f"ok {name}")

results = BASE / "results.txt"
check("exists", results.exists(), "results.txt missing")
content = results.read_text().strip()
actual = sorted(line.strip().lower() for line in content.splitlines() if line.strip())
expected = sorted(["alice, bob", "alice, ethan"])
check("pairs", sorted(actual) == expected, f"got {actual}, want {expected}")
print("ALL OK")
