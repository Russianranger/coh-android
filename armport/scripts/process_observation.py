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


def exit_marker_seen(path):
    """Read only a bounded tail; a torn or unrelated record is not a witness."""
    try:
        with path.open('rb') as stream:
            stream.seek(0, 2)
            size = stream.tell()
            stream.seek(max(0, size - 8192))
            data = stream.read(8192)
        lines = data.split(b'\n')[:-1]
        # When the tail starts in the middle of a row, discard that row even
        # if its suffix happens to look like JSON.
        if size > 8192:
            lines = lines[1:]
        for line in lines:
            try:
                row = json.loads(line)
                if isinstance(row, dict) and row.get('stage') == 'replay.exit.begin':
                    return True
            except (ValueError, UnicodeError):
                pass
    except OSError:
        pass
    return False


def task_sample(pid, start, proc_root=Path('/proc')):
    """Passive /proc evidence only: no debugger, signal, environment or memory."""
    result = dict(seconds=round(time.monotonic() - start, 3), tasks=[])
    try:
        tasks = sorted((proc_root / str(pid) / 'task').iterdir(), key=lambda p: int(p.name))
        result['task_count'] = len(tasks)
        result['truncated'] = len(tasks) > 64
        for task in tasks[:64]:
            row = dict(tid=int(task.name))
            for name, bound in (('stat', 4096), ('wchan', 256)):
                try:
                    with (task / name).open() as stream:
                        row[name] = stream.read(bound).strip()
                except OSError as error:
                    row[name + '_unavailable'] = error.errno
            result['tasks'].append(row)
    except OSError as error:
        result['unavailable'] = error.errno
    return result


def run(command, *, evidence, timeout, exit_trace=None, **kwargs):
    start = time.monotonic()
    record = dict(timeout_seconds=timeout, memory_events_before=memory_events(), samples=[])
    if exit_trace is not None:
        record['exit_observation'] = dict(marker_seen=False, samples=[],
                                         scope='passive_linux_tasks_not_signal_sender')
    stopped = threading.Event()
    proc = subprocess.Popen(command, **kwargs)
    record['pid'] = proc.pid

    def observe():
        next_sample = start
        # The Wine server's exit timer can be shorter than one second. Poll
        # the existing exit witness at 20 Hz, retaining ordinary memory
        # samples at 1 Hz and at most 40 task samples after the witness.
        interval = 0.05 if exit_trace is not None else 1
        for _ in range(int(min(timeout + 2, 602) / interval) + 1):
            now = time.monotonic()
            if now >= next_sample and len(record['samples']) < 602:
                record['samples'].append(sample(proc.pid, start))
                next_sample = now + 1
            if exit_trace is not None:
                observation = record['exit_observation']
                if not observation['marker_seen'] and exit_marker_seen(exit_trace):
                    observation.update(marker_seen=True, seconds=round(now - start, 3))
                if observation['marker_seen'] and len(observation['samples']) < 40:
                    observation['samples'].append(task_sample(proc.pid, start))
            if stopped.wait(interval):
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
