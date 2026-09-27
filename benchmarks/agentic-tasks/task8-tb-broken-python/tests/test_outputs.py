# Ported from terminal-bench(original-tasks)/broken-python (MIT). Plain-python
# oracle (no pytest dependency); offline-deterministic pip via bundled wheel.
import subprocess, sys
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
VENV_PY = BASE / "protected" / "venv" / "bin" / "python"

def check(name, cond, msg):
    if not cond:
        print(f"FAIL {name}: {msg}"); sys.exit(1)
    print(f"ok {name}")

r = subprocess.run([str(VENV_PY), "-m", "pip", "--version"], capture_output=True, text=True)
check("pip_version", r.returncode == 0, "pip is not working in the venv")
r = subprocess.run([str(VENV_PY), "-m", "pip", "install", "--no-index", "--find-links",
                    str(BASE / "wheels"), "six"], capture_output=True, text=True)
check("pip_install", r.returncode == 0, "pip still cannot install packages")
r2 = subprocess.run([str(VENV_PY), "-c", "import six; print(six.__version__)"], capture_output=True, text=True)
check("import_six", r2.returncode == 0 and r2.stdout.strip(), "installed package not importable")
print("ALL OK")
