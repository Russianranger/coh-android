"""Bounded, read-only samples of this harness's ARM64 Wine client.

The debugger pauses the client briefly; its exit/timeout detaches it. Never
attach to a server or another Wine prefix. Call at most twice per M3 run.
"""
import os
import json
from pathlib import Path
import re
import subprocess
import time
from arm64_wine_context import WINE_COMMIT


# PE unwind metadata is not always understood by Linux gdb. Sample the ARM64
# frame chain as supplementary evidence, never as a guaranteed stack unwind.
FRAME_SAMPLE = '''
import gdb, struct
inferior = gdb.selected_inferior()
for thread in inferior.threads()[:64]:
    try:
        thread.switch()
        pc, lr, fp, sp = [int(gdb.parse_and_eval('$' + name)) for name in ('pc','x30','x29','sp')]
        print('arm64-registers thread=%s pc=%#x lr=%#x fp=%#x sp=%#x' % (thread.ptid,pc,lr,fp,sp))
        for depth in range(8):
            if fp % 16 or not sp <= fp < sp + 1024*1024:
                break
            parent, ret = struct.unpack('<QQ', bytes(inferior.read_memory(fp,16)))
            print('arm64-frame depth=%d fp=%#x return=%#x' % (depth,fp,ret))
            if parent <= fp:
                break
            fp = parent
    except (gdb.error, ValueError) as exc:
        print('arm64-frame unavailable: ' + str(exc))
'''

# Read only the helper source we ship, never an inferior-provided script.
WINE_FRAME_SAMPLE = (Path(__file__).with_name('arm64_wine_context.py').read_text() + '''
for thread in inferior.threads()[:64]:
    try:
        thread.switch()
        teb = int(gdb.parse_and_eval('$x18'))
        saved = saved_context(inferior.read_memory, teb)
        print('wine-saved-context thread=%s frame=%#x pc=%#x lr=%#x fp=%#x sp=%#x' %
              (thread.ptid,saved['frame'],saved['pc'],saved['lr'],saved['fp'],saved['sp']))
        for depth, (fp, ret) in enumerate(saved['frames']):
            print('wine-saved-frame depth=%d fp=%#x return=%#x' % (depth,fp,ret))
    except (gdb.error, ValueError, struct.error) as exc:
        print('wine-saved-context unavailable: ' + str(exc))
''')


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
        sample = FRAME_SAMPLE
        runtime_lock = Path(__file__).resolve().parents[2] / 'android/runtime-lock.json'
        if json.loads(runtime_lock.read_text())['wine']['wine_commit'] == WINE_COMMIT:
            sample += '\n' + WINE_FRAME_SAMPLE
        else:
            lines.append('Wine saved context skipped: source layout pin differs')
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
                   '-ex', 'thread apply all bt 12',
                   '-ex', 'python exec(' + repr(sample) + ')', '-ex', 'detach']
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
