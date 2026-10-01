"""Foreground timeout and resource recording for repair checks."""
from __future__ import annotations

import argparse
import json
import os
import resource
import signal
import subprocess
import sys
import time
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--label', required=True)
parser.add_argument('--timeout', type=float, required=True)
parser.add_argument('command', nargs=argparse.REMAINDER)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
logs = root / 'docs/repair_logs'
logs.mkdir(exist_ok=True)
command = args.command[1:] if args.command[0] == '--' else args.command
started = time.perf_counter()
peak_mb = None
measurement_errors = set()
status = 'completed'
env = os.environ.copy()
env.update({'MPLBACKEND': 'Agg', 'MPLCONFIGDIR': str(root / '.cache/matplotlib'),
            'TMPDIR': str(root / '.cache/tmp'), 'PIP_CACHE_DIR': str(root / '.cache/pip'),
            'XDG_CACHE_HOME': str(root / '.cache')})
Path(env['TMPDIR']).mkdir(parents=True, exist_ok=True)
with (logs / f'{args.label}.log').open('w') as log:
    proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, cwd=root, env=env, start_new_session=True)
    (logs / f'{args.label}_pid.json').write_text(json.dumps({'wrapper_pid': os.getpid(), 'child_pid': proc.pid}))
    def interrupt(signum, frame):
        del signum, frame
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=10)
        raise KeyboardInterrupt
    signal.signal(signal.SIGINT, interrupt)
    signal.signal(signal.SIGTERM, interrupt)
    while proc.poll() is None:
        if time.perf_counter() - started > args.timeout:
            status = 'timeout'
            os.killpg(proc.pid, signal.SIGTERM)
            break
        try:
            result = subprocess.run(['top', '-l', '1', '-pid', str(proc.pid), '-stats', 'pid,mem'],
                capture_output=True, text=True, timeout=5, check=True)
            for line in result.stdout.splitlines():
                fields = line.split()
                if fields and fields[0] == str(proc.pid):
                    token = fields[-1].rstrip('+-')
                    factor = {'K': 1 / 1024, 'M': 1, 'G': 1024}.get(token[-1])
                    if factor is not None:
                        footprint = float(token[:-1]) * factor
                        peak_mb = max(peak_mb or 0, footprint)
                        if footprint >= 12 * 1024:
                            status = 'memory_stop'
                            os.killpg(proc.pid, signal.SIGTERM)
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            measurement_errors.add(str(exc))
        time.sleep(1)
    try:
        code = proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        code = proc.wait()
usage = resource.getrusage(resource.RUSAGE_CHILDREN)
rss_bytes = usage.ru_maxrss if sys.platform == 'darwin' else usage.ru_maxrss * 1024
record = {'command': command, 'exit_code': code, 'status': status,
    'runtime_seconds': time.perf_counter() - started, 'timeout_seconds': args.timeout,
    'peak_top_mem_mb': peak_mb, 'top_errors': sorted(measurement_errors),
    'child_max_rss_bytes': rss_bytes,
    'rss_limitation': 'Maximum child resident memory; not compressed/swapped footprint or aggregate process memory.'}
(logs / f'{args.label}_status.json').write_text(json.dumps(record, indent=2))
print(json.dumps(record))
raise SystemExit(code if code else (0 if status == 'completed' else 1))
