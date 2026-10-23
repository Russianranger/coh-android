"""Bounded, read-only samples of this harness's ARM64 Wine client.

The debugger pauses the client briefly; its exit/timeout detaches it. Never
attach to a server or another Wine prefix. Call at most twice per M3 run.
"""
import os
from pathlib import Path
import re
import subprocess
import time


def client_pids(client, proc=Path('/proc')):
    exe = str(client.resolve() / 'CityOfHeroes.exe')
    found = []
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if entry.stat().st_uid != os.getuid():
                continue
            # Wine may rewrite argv[0]; require the exact executable mapping.
            maps = (entry / 'maps').read_text()
            if any(line.split(maxsplit=5)[-1] == exe for line in maps.splitlines()):
                found.append(int(entry.name))
        except (OSError, ValueError):
            continue
    return sorted(found)


def capture(client, evidence, label, llvm=None):
    path = evidence / ('stall-' + label + '.txt')
    lines = ['sampled_utc=' + time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())]
    pids = client_pids(client)
    lines.append('client_pids=' + repr(pids))
    if len(pids) == 1:
        pid = pids[0]
        for task in sorted(Path(f'/proc/{pid}/task').iterdir()):
            try:
                # CPU counters and wait channel distinguish a busy loader from
                # a thread waiting on Wine I/O or a lock. No memory/env dump.
                lines.append('task ' + task.name + ' ' + (task / 'stat').read_text().strip())
                lines.append('wchan ' + (task / 'wchan').read_text().strip())
            except OSError:
                pass
        command = ['sudo', '-n', 'timeout', '--kill-after=5s', '15s', 'gdb',
                   '-q', '-nx', '-nh', '-batch', '-iex', 'set auto-load off',
                   '-iex', 'set debuginfod enabled off',
                   '-iex', 'set print frame-arguments none', '-p', str(pid),
                   '-ex', 'thread apply all bt 12', '-ex', 'detach']
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        lines.extend(['debugger_exit=' + str(result.returncode), result.stdout, result.stderr])
        if llvm:
            # The PE image base is fixed by the build; Wine/system addresses
            # are excluded. Keep a bounded list for the report.
            addresses = sorted({int(x, 16) for x in re.findall(r'0x([0-9a-fA-F]+)', result.stdout)
                                if 0x140000000 <= int(x, 16) < 0x150000000})[:80]
            if addresses:
                symbols = subprocess.run([
                    str(llvm / 'bin/llvm-symbolizer'), '--obj=' + str(client / 'CityOfHeroes.exe'),
                    '--relative-address', '--functions=linkage', '--inlining=false', '--basenames',
                    *[hex(x - 0x140000000) for x in addresses]],
                    capture_output=True, text=True, timeout=20)
                lines.extend(['client_addresses=' + repr([hex(x) for x in addresses]), symbols.stdout])
    else:
        lines.append('debugger skipped: expected exactly one executable mapping')
    path.write_text('\n'.join(lines))
    return path
