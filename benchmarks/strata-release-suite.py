#!/usr/bin/env python3
"""Run identical full AG-Bench suites against two Strata engines sequentially."""
import json
import argparse
import hashlib
import os
import signal
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
server_root = Path('/home/riccardogiorato/Desktop/github/strata-0142')
pi_bin = Path('/home/riccardogiorato/.local/share/mise/installs/pi/1.0.4/pi/pi')
shimdir = Path(tempfile.mkdtemp(prefix='strata-pi-'))
(shimdir / 'pi').symlink_to(pi_bin)
env = dict(os.environ, PATH=str(shimdir) + ':' + os.environ['PATH'], PI_OFFLINE='1')
env.pop('TASK_RE', None)
outdir = repo / 'benchmarks/results'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--task-re', help='Optional task subset for diagnostic repeats')
parser.add_argument('--arms', default='0141,0142', help='Comma-separated 0141,0142,0142-tail-off,0143,0143-tail-off,0144,0144-tail-off')
parser.add_argument('--suffix', default='ab-v22-20261010')
parser.add_argument('--pcie-frac', help='Pin PCIe share for controlled diagnostic repeats')
opts = parser.parse_args()
if opts.task_re:
    env['TASK_RE'] = opts.task_re

for version in opts.arms.split(','):
    if version not in ('0141', '0142', '0142-tail-off', '0143', '0143-tail-off', '0144', '0144-tail-off'):
        raise ValueError(f'Unknown arm: {version}')
    cfg = repo / 'recipes/strata-configs/strata-q20-gsq-0141-bench-reference.json'
    label = f'strata-{version}-{opts.suffix}'
    config = json.loads(cfg.read_text())
    engine_version = version.split('-tail')[0]
    config['exe'] = f'/home/riccardogiorato/Desktop/github/strata-{engine_version}/build-turing-{engine_version}/strata'
    config['log'] = str(outdir / f'{label}.engine.log')
    if opts.pcie_frac:
        config['args'] += ['--pcie-frac', opts.pcie_frac]
    if version.endswith('-tail-off'):
        config['env'] = dict(config.get('env', {}), STRATA_ROUTE_TAIL_SKIP='0')
    cfg = Path(f'/tmp/{label}.json')
    cfg.write_text(json.dumps(config, indent=2) + '\n')
    print(f'START {label}', flush=True)
    with (outdir / f'{label}.server.log').open('w') as server_log:
        server = subprocess.Popen([sys.executable, '-m', 'serve.server', '--engine', 'strata',
                                   '--config', str(cfg), '--host', '127.0.0.1', '--port', '8080'],
                                  cwd=Path(f'/home/riccardogiorato/Desktop/github/strata-{engine_version}'), stdout=server_log, stderr=subprocess.STDOUT,
                                  start_new_session=True, env=env)
        try:
            for _ in range(180):
                if server.poll() is not None:
                    raise RuntimeError(f'Server exited {server.returncode}; inspect {label}.server.log')
                try:
                    with urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2) as response:
                        health = json.load(response)
                    if health.get('loaded'):
                        break
                except (OSError, ValueError):
                    pass
                time.sleep(2)
            else:
                raise RuntimeError('Server readiness timed out')
            metadata = {'version': version, 'config': json.loads(cfg.read_text()),
                        'server_root': str(server_root), 'health': health, 'cap_s': 900,
                        'task_re': opts.task_re,
                        'harness_sha256': hashlib.sha256((repo / 'benchmarks/agentic-bench.sh').read_bytes()).hexdigest(),
                        'pi_version': subprocess.check_output([str(pi_bin), '--version'], text=True).strip()}
            (outdir / f'{label}.metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
            print(f'READY {label}', flush=True)
            # Keep dirname-based task paths, but freeze the shell source for this run.
            with tempfile.NamedTemporaryFile(mode='w', dir=repo / 'benchmarks',
                                             prefix='.strata-bench-', suffix='.sh', delete=False) as snapshot:
                snapshot.write((repo / 'benchmarks/agentic-bench.sh').read_text())
            try:
                with (outdir / f'{label}.runner.log').open('w') as runner_log:
                    subprocess.run(['bash', snapshot.name, label, '900'], cwd=repo, env=env,
                                   stdout=runner_log, stderr=subprocess.STDOUT, check=True)
            finally:
                Path(snapshot.name).unlink(missing_ok=True)
            print(f'DONE {label}', flush=True)
        finally:
            try:
                os.killpg(server.pid, signal.SIGTERM)
                server.wait(timeout=30)
            except subprocess.TimeoutExpired:
                os.killpg(server.pid, signal.SIGKILL)
                server.wait()
            except ProcessLookupError:
                pass
print('BOTH SUITES COMPLETE', flush=True)
shutil.rmtree(shimdir)
