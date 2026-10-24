"""Bounded Linux process evidence; does not change exit-code acceptance."""
import json
from pathlib import Path
import signal
import subprocess
import threading
import time


def memory_events():
    try:
        lines = Path('/proc/self/cgroup').read_text().splitlines()
        relative = next(line[3:] for line in lines if line.startswith('0::'))
        # The runner normally uses cgroup v2. Missing/hidden counters are
        # reported as unavailable, never interpreted as proof of no OOM.
        path = Path('/sys/fs/cgroup') / relative.lstrip('/') / 'memory.events'
        return dict(available=True, path=str(path), counters={k: int(v) for k, v in
                    (line.split() for line in path.read_text().splitlines())})
    except (OSError, ValueError, StopIteration):
        return dict(available=False)


def sample(pid, start):
    result = dict(seconds=round(time.monotonic() - start, 3))
    try:
        status = Path(f'/proc/{pid}/status').read_text()
        for line in status.splitlines():
            key, _, value = line.partition(':')
            if key in ('VmRSS', 'VmHWM', 'VmSize', 'Threads', 'State'):
                result[key] = value.strip()
    except OSError:
        result['process_status_unavailable'] = True
    try:
        for line in Path('/proc/meminfo').read_text().splitlines():
            key, _, value = line.partition(':')
            if key in ('MemAvailable', 'SwapFree'):
                result[key] = value.strip()
    except OSError:
        pass
    return result


def run(command, *, evidence, timeout, **kwargs):
    start = time.monotonic()
    record = dict(timeout_seconds=timeout, memory_events_before=memory_events(), samples=[])
    stopped = threading.Event()
    proc = subprocess.Popen(command, **kwargs)
    record['pid'] = proc.pid

    def observe():
        for _ in range(min(int(timeout) + 2, 602)):
            record['samples'].append(sample(proc.pid, start))
            if stopped.wait(1):
                break

    thread = threading.Thread(target=observe, daemon=True)
    thread.start()
    try:
        proc.wait(timeout=timeout)
        return subprocess.CompletedProcess(command, proc.returncode)
    except subprocess.TimeoutExpired:
        record['host_timeout_kill'] = True
        proc.kill()
        proc.wait()
        raise
    finally:
        stopped.set()
        thread.join(timeout=3)
        record.update(elapsed_seconds=round(time.monotonic() - start, 3), returncode=proc.returncode,
                      memory_events_after=memory_events())
        if proc.returncode is not None and proc.returncode < 0:
            record['signal'] = signal.Signals(-proc.returncode).name
        evidence.write_text(json.dumps(record, indent=2) + '\n')
