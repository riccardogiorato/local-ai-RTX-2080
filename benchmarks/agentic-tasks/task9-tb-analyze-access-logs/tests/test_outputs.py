# Ported from terminal-bench(original-tasks)/analyze-access-logs (MIT).
# Plain-python oracle, workdir-relative paths (upstream used /app/*).
import re, sys
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
report = BASE / "report.txt"

def check(name, cond, msg):
    if not cond: print(f"FAIL {name}: {msg}"); sys.exit(1)
    print(f"ok {name}")

check("exists", report.exists(), "report.txt missing")
content = report.read_text().strip()
m = re.search(r"Total requests:\s*(\d+(?:\.\d+)?)$", content, re.M)
check("total_line", bool(m), "missing 'Total requests: <number>' line")
check("total_2000", m and float(m.group(1)) == 2000, f"got {m.group(1) if m else None}, want 2000")
m = re.search(r"Unique IP addresses:\s*(\d+(?:\.\d+)?)$", content, re.M)
check("ips_line", bool(m), "missing 'Unique IP addresses: <number>' line")
check("ips_273", m and float(m.group(1)) == 273, f"got {m.group(1) if m else None}, want 273")
check("top_header", "Top 3 URLs:" in content, "missing 'Top 3 URLs:' header")
top_urls = re.findall(r"^  (\S+): (\d+)$", content, re.M)
check("top3_count", len(top_urls) == 3, f"want 3 top-URL lines, got {len(top_urls)}")
counts = sorted((int(c) for _, c in top_urls), reverse=True)
check("top3_sorted", counts == sorted(counts, reverse=True) and counts[0] >= counts[-1], "top URLs not ordered by count")
m = re.search(r"404 errors:\s*(\d+(?:\.\d+)?)$", content, re.M)
check("404_line", bool(m), "missing '404 errors: <number>' line")
print("ALL OK")
