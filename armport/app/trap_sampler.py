"""Which guest tasks wait on PRoot, and at which system call (CI host side, read-only).

Thor 0.13.67 (export 20261111-035325): PRoot's one tracer thread had used 647 s of CPU
by the time the character was in the world (990 s after the guest started) and kept
using about half a core there; every traced task that makes a filtered system call
stops until that thread has served it. The phone report cannot say which calls those
are. This sampler runs on the CI host, outside PRoot, so reading /proc costs the guest
nothing: in short bursts it reads the state of every task below the guest's first
process and, for a task in a tracing stop, the system call it is stopped at.

Each window prints one line, `TRAP_SAMPLER_V1 {json}`, to the job log (run artifacts
cannot be downloaded from a development session; job logs can). Nothing is changed in
any process. An unreadable entry is counted, never fatal.
"""
import json
import os
from pathlib import Path
import threading
import time

ENV = 'COH_TRAP_SAMPLER'
MARK = 'TRAP_SAMPLER_V1 '
TASK_LIMIT = 4096
TOP = 12


def requested():
    value = os.environ.get(ENV, '')
    if value not in ('', '0', '1'):
        raise ValueError(ENV + ' must be empty, 0 or 1')
    return value == '1'


def stat_fields(text):
    """(comm, state, parent pid) of a /proc/<pid>/stat or task stat line."""
    left, right = text.index('('), text.rindex(')')
    rest = text[right + 2:].split()
    return text[left + 1:right], rest[0], int(rest[1])


def program(proc, pid, comm):
    """The program a process runs: its command line's first word, else its name."""
    try:
        first = (proc / str(pid) / 'cmdline').read_bytes().split(b'\0', 1)[0].decode(errors='replace')
    except OSError:
        first = ''
    name = first.replace('\\', '/').rsplit('/', 1)[-1].strip()
    return (name or comm)[:24]


def tracer_of(proc, pid):
    try:
        for line in (proc / str(pid) / 'status').read_text(errors='replace').splitlines()[:64]:
            if line.startswith('TracerPid:'):
                return int(line.split(':', 1)[1])
    except (OSError, ValueError):
        pass
    return 0


def descendants(proc, root):
    """The guest's processes: those below `root` (root included) and every process traced
    by a tracer found there. Wine starts a program through two forks, so a Windows
    program's parent is init, not its starter; PRoot still traces it."""
    parents, names = {}, {}
    with os.scandir(proc) as entries:
        for entry in entries:
            if not entry.name.isdigit():
                continue
            try:
                comm, _, parent = stat_fields((Path(entry.path) / 'stat').read_text(errors='replace'))
            except (OSError, ValueError):
                continue
            parents[int(entry.name)], names[int(entry.name)] = parent, comm
    children = {}
    for pid, parent in parents.items():
        children.setdefault(parent, []).append(pid)
    found, pending = [], [root]
    while pending and len(found) < TASK_LIMIT:
        pid = pending.pop()
        if pid in names and pid not in found:
            found.append(pid)
            pending.extend(children.get(pid, ()))
    below = set(found)
    traced = {pid: tracer_of(proc, pid) for pid in names}
    tracers = {traced[pid] for pid in below if traced[pid] > 0}
    found.extend(sorted(pid for pid, tracer in traced.items() if tracer in tracers and pid not in below)
                 [:TASK_LIMIT - len(found)])
    return {pid: names[pid] for pid in found}


def sample(proc, pids, programs, window):
    """One round: every task's state; the system call of each task in a tracing stop."""
    for pid in pids:
        try:
            tasks = os.listdir(proc / str(pid) / 'task')
        except OSError:
            window['unreadable'] += 1
            continue
        for task in tasks[:TASK_LIMIT]:
            base = proc / str(pid) / 'task' / task
            try:
                _, state, _ = stat_fields((base / 'stat').read_text(errors='replace'))
            except (OSError, ValueError):
                window['unreadable'] += 1
                continue
            name = programs[pid]
            states = window['states'].setdefault(name, {})
            states[state] = states.get(state, 0) + 1
            if state != 't':
                continue
            try:
                number = (base / 'syscall').read_text(errors='replace').split(None, 1)[0]
            except (OSError, IndexError):
                number = 'unreadable'
            key = name + ' ' + number
            window['stops'][key] = window['stops'].get(key, 0) + 1


def summary(window, started, now):
    """One bounded line for the job log."""
    stops = sorted(window['stops'].items(), key=lambda item: (-item[1], item[0]))
    states = {name: counts for name, counts in sorted(
        window['states'].items(), key=lambda item: -sum(item[1].values()))[:TOP]}
    return {'t': round(now - started, 1), 'utc': time.strftime('%H:%M:%SZ', time.gmtime()),
            'rounds': window['rounds'], 'processes': window['processes'],
            'stopped_tasks': sum(window['stops'].values()), 'stops': stops[:TOP],
            'other_stops': sum(count for _, count in stops[TOP:]),
            'states': states, 'unreadable': window['unreadable']}


class TrapSampler(threading.Thread):
    """Bursts of `rounds` samples `gap` seconds apart; one printed line per `window` seconds."""

    def __init__(self, root_pid, label, *, proc=Path('/proc'), window=60.0, pause=5.0, rounds=20, gap=0.02,
                 emit=None):
        super().__init__(name='trap-sampler', daemon=True)
        self.root_pid, self.label, self.proc = root_pid, label, Path(proc)
        self.window_seconds, self.pause, self.rounds, self.gap = window, pause, rounds, gap
        self.emit = emit or (lambda line: print(line, flush=True))
        self.stopping = threading.Event()
        self.lines = 0

    @staticmethod
    def empty():
        return {'rounds': 0, 'processes': 0, 'states': {}, 'stops': {}, 'unreadable': 0}

    def burst(self, window):
        pids = descendants(self.proc, self.root_pid)
        programs = {pid: program(self.proc, pid, comm) for pid, comm in pids.items()}
        window['processes'] = max(window['processes'], len(pids))
        for _ in range(self.rounds):
            sample(self.proc, pids, programs, window)
            window['rounds'] += 1
            if self.stopping.wait(self.gap):
                break

    def flush(self, window, started):
        if window['rounds']:
            self.emit(MARK + json.dumps(dict(summary(window, started, time.monotonic()), session=self.label),
                                        separators=(',', ':')))
            self.lines += 1

    def run(self):
        started = edge = time.monotonic()
        window = self.empty()
        while not self.stopping.is_set():
            try:
                self.burst(window)
            except Exception as error:      # read-only evidence: never the reason a session fails
                window['unreadable'] += 1
                window['error'] = type(error).__name__
            if time.monotonic() - edge >= self.window_seconds:
                self.flush(window, started)
                window, edge = self.empty(), time.monotonic()
            self.stopping.wait(self.pause)
        self.flush(window, started)

    def finish(self):
        self.stopping.set()
        self.join(timeout=10)
        return {'requested': True, 'lines': self.lines, 'scope': 'CI host /proc samples of the guest process tree'}
