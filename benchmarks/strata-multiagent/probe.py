import sys, json, run, re
from pathlib import Path
slots, res = int(sys.argv[1]), sys.argv[2]
ctx = sys.argv[3] if len(sys.argv) > 3 else "131072"
out = Path("results/probe").resolve(); out.mkdir(parents=True, exist_ok=True)
orig = run.BASE_CONFIG
cfg = json.loads(orig.read_text()); a = cfg["args"]; a[a.index("--kv-resident")+1] = res; a[a.index("--max-context")+1] = ctx; a[a.index("--prefill")+1] = "auto:" + ctx
tmp = out / f"base-{res}.json"; tmp.write_text(json.dumps(cfg)); run.BASE_CONFIG = tmp
label = f"probe-b{slots}-r{res}-c{ctx}"
try:
    p, t, props = run.start_server(slots, out, label)
    print("READY", t, props.get("total_slots"), run.gpu_mem())
    run.stop_server(p)
except Exception as e:
    print("FAIL", e)
log = (out / f"{label}.engine.log").read_text()
for l in log.splitlines():
    if re.search(r"slot sessions|expert cache auto|no VRAM|KV streaming|verify: needs|chunk of", l): print("  ", l[:220])
