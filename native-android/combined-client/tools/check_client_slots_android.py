#!/usr/bin/env python3
"""Exercise the actual JNI slot mapping, accounting and cleanup with API doubles."""
import argparse
import hashlib
import json
import os
import shlex
from pathlib import Path
import subprocess
from client_slots_input import prepare_client_slots, RAW_BYTES, RAW_SHA256
from check_bodypart_continuation import PROBES
from report_diagnostic_contract import separate_report_extension

ROOT = Path(__file__).resolve().parents[3]
TOOLS = Path('native-android/combined-client/tools')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=False)
    metadata = prepare_client_slots(work / 'assets')
    raw = (work / 'assets' / metadata['asset']).read_bytes()
    assert len(raw) == RAW_BYTES and hashlib.sha256(raw).hexdigest() == RAW_SHA256
    original = work / 'offset-asset.bin'
    changed = work / 'offset-corrupt.bin'
    original.write_bytes(b'P' * 37 + raw)
    corrupt = bytearray(raw)
    corrupt[20] ^= 1  # First authentic string spelling; keep the raw grammar valid.
    changed.write_bytes(b'P' * 37 + corrupt)
    flags = ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic', '-fno-pie', '-no-pie',
             '-fstack-usage', '-DCOH_INTEROP_REQUEST_TX=1', '-DCOH_INTEROP_CLIENT_SLOTS=1',
             '-I', str(TOOLS / 'test-include'), '-I', 'native-android/combined-client/diagnostics/interop-adapter-20261018/test-include',
             '-I', 'native-android/engine/initial-capture', '-I', 'native-android/engine/entities',
             '-I', 'native-android/engine/session', '-I', 'native-android/include']
    sources = [TOOLS / 'test_client_slots_android.c',
               *[Path('native-android/engine/initial-capture/coh_initial_' + name + '_probe.c') for name in PROBES],
               Path('native-android/engine/initial-capture/coh_local_bodypart_default.c'),
               Path('native-android/engine/entities/coh_original_costume_receive.c'),
               Path('native-android/engine/entities/coh_entities.c'), Path('native-android/engine/replication/coh_replication.c')]
    env = {**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0:halt_on_error=1',
           'UBSAN_OPTIONS': 'halt_on_error=1:print_stacktrace=1'}
    dependency = subprocess.run([*flags, '-M', *map(str, sources)], cwd=ROOT,
                                capture_output=True, text=True, check=True)
    frozen = {Path(__file__).resolve(), ROOT / TOOLS / 'client_slots_input.py',
              ROOT / TOOLS / 'prepare.py', ROOT / TOOLS / 'report_diagnostic_contract.py',
              ROOT / TOOLS / 'check_bodypart_continuation.py', ROOT / metadata['source']}
    for line in dependency.stdout.replace('\\\n', ' ').splitlines():
        for name in shlex.split(line.split(':', 1)[1]):
            path = Path(name)
            path = (path if path.is_absolute() else ROOT / path).resolve()
            if path.is_relative_to(ROOT):
                frozen.add(path)
    pins = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(frozen)}
    result = {'passed': True, 'modes': {}, 'asset': metadata,
              'inputs_sha256': pins,
              'scope': 'Shipping JNI mmap/offset/index/receiver/cleanup code with Android API and transport doubles; source-layout packet, no physical packet replay or Android ABI claim.'}
    for mode, options in [('release', ['-O2']), ('asan', ['-O1', '-g', '-fsanitize=address']),
                          ('ubsan', ['-O1', '-g', '-fsanitize=undefined', '-fno-sanitize-recover=all'])]:
        binary = work / mode
        command = [*flags, *options, *map(str, sources),
                   '-Wl,--wrap=calloc,--wrap=free,--wrap=open,--wrap=close,--wrap=read,--wrap=__read_chk,--wrap=mmap,--wrap=munmap',
                   '-lcrypto', '-lm', '-o', str(binary)]
        with (work / (mode + '-compile.log')).open('wb') as log:
            subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
        execution = subprocess.run([str(binary), str(original), str(changed)], cwd=ROOT, env=env,
                                   capture_output=True, text=True, timeout=90)
        (work / (mode + '-run.log')).write_text(execution.stdout + execution.stderr)
        if execution.returncode:
            raise RuntimeError(mode + ' execution failed; see ' + str(work / (mode + '-run.log')))
        result['modes'][mode] = json.loads(execution.stdout)
    assert len({json.dumps(row, sort_keys=True) for row in result['modes'].values()}) == 1
    frames = []
    for path in work.glob('release-*.su'):
        for line in path.read_text().splitlines():
            function, size, kind = line.split('\t')
            if 'interop_network.c:' in function:
                frames.append({'function': function.rsplit(':', 1)[-1], 'bytes': int(size), 'kind': kind})
    # The receiver's full original source frame closure has its own 4 KiB check.
    assert all(row['bytes'] <= 4096 for row in frames if 'configureClientSlots' in row['function'])
    result['native_stack_frames'] = frames
    # The additive source-resource projection remains strict and scalar-only.
    for value in ([0, 641477, 134144, 643072], [0, 0, 0, 0], [3, 0, 0, 0]):
        assert separate_report_extension({'client_slots': value}) == {}
    for value in ([0, 641477, 0, 643072], [1, 641477, 134144, 643072], [0, 0, 0, 1], [0, 1, 1, 1], [0, 0, 0]):
        try:
            separate_report_extension({'client_slots': value})
        except ValueError:
            pass
        else:
            raise AssertionError('Malformed client slot resource projection accepted')
    for value in ([0, 0], [2, 1], [10, 10]):
        assert separate_report_extension({'costume_bodies': value}) == {}
    for value in ([1, 2], [11, 0], [1], [True, 0]):
        try:
            separate_report_extension({'costume_bodies': value})
        except ValueError:
            pass
        else:
            raise AssertionError('Malformed costume body count accepted')
    assert pins == {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(frozen)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': True, 'modes': result['modes']}))


if __name__ == '__main__':
    main()
