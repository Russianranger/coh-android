#!/usr/bin/env python3
"""New-profile actual JNI outer receiver, selected capture and bounded report."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
from client_slots_input import prepare_client_slots
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
    original = work / 'offset-asset.bin'
    original.write_bytes(b'P' * 37 + raw)
    flags = ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic', '-fno-pie', '-no-pie', '-fstack-usage',
             '-DCOH_INTEROP_REQUEST_TX=1', '-DCOH_INTEROP_CLIENT_SLOTS=1', '-DCOH_FRAME_CAPTURE_DIAGNOSTIC=1',
             '-I', str(TOOLS / 'test-include'), '-I', 'native-android/combined-client/diagnostics/interop-adapter-20261018/test-include',
             '-I', 'native-android/engine/initial-capture', '-I', 'native-android/engine/entities',
             '-I', 'native-android/engine/session', '-I', 'native-android/include']
    sources = [TOOLS / 'test_outer_costume_android.c',
               *[Path('native-android/engine/initial-capture/coh_initial_' + name + '_probe.c') for name in PROBES],
               Path('native-android/engine/initial-capture/coh_local_bodypart_default.c'),
               Path('native-android/engine/entities/coh_original_costume_receive.c'),
               Path('native-android/engine/entities/coh_original_ent_costume.c'),
               Path('native-android/engine/entities/coh_original_taskforce_receive.c'),
               Path('native-android/engine/entities/coh_entities.c'), Path('native-android/engine/replication/coh_replication.c')]
    dependency = subprocess.run([*flags, '-M', *map(str, sources)], cwd=ROOT, capture_output=True, text=True, check=True)
    frozen = {Path(__file__).resolve(), ROOT / TOOLS / 'report_diagnostic_contract.py', ROOT / TOOLS / 'client_slots_input.py', ROOT / metadata['source'], ROOT / 'native-android/combined-client/app/src/main/java/org/coh/nativecombined/InteropNative.java'}
    for line in dependency.stdout.replace('\\\n', ' ').splitlines():
        for name in shlex.split(line.split(':', 1)[1]):
            path = Path(name)
            path = (path if path.is_absolute() else ROOT / path).resolve()
            if path.is_relative_to(ROOT):
                frozen.add(path)
    pins = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(frozen)}
    result = {'passed': True, 'modes': {}, 'inputs_sha256': pins,
              'scope': 'Shipping new-profile JNI observer, with Android asset/JNI/transport doubles and source-layout sender header composition; no physical packet, Android ABI, actor or ACK claim.'}
    env = {**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0:halt_on_error=1', 'UBSAN_OPTIONS': 'halt_on_error=1:print_stacktrace=1'}
    for mode, options in [('release', ['-O2']), ('asan', ['-O1', '-g', '-fsanitize=address']), ('ubsan', ['-O1', '-g', '-fsanitize=undefined', '-fno-sanitize-recover=all'])]:
        binary = work / mode
        command = [*flags, *options, *map(str, sources), '-Wl,--wrap=calloc,--wrap=free,--wrap=open,--wrap=close,--wrap=read,--wrap=__read_chk,--wrap=mmap,--wrap=munmap', '-lcrypto', '-lm', '-o', str(binary)]
        with (work / (mode + '-compile.log')).open('wb') as log:
            subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
        execution = subprocess.run([binary, original, original], cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
        (work / (mode + '-run.log')).write_text(execution.stdout + execution.stderr)
        if execution.returncode:
            raise RuntimeError(mode + ' execution failed; see ' + str(work / (mode + '-run.log')))
        result['modes'][mode] = json.loads(execution.stdout)
    assert len({json.dumps(row, sort_keys=True) for row in result['modes'].values()}) == 1
    frames = []
    parser_frames = {'valid', 'coh_rep_read', 'coh_rep_pack', 'stats_leaf', 'character_stats',
                     'coh_ent_character_stats', 'fail', 'check_reader', 'coh_ent_target', 'target',
                     'coh_ent_status_effects', 'status_effects', 'coh_ent_inventory_sizes', 'inventory_sizes'}
    observer_frame = 0
    for path in work.glob('release-*.su'):
        for line in path.read_text().splitlines():
            location, size, kind = line.split('\t')
            function = location.rsplit(':', 1)[-1]
            if 'interop_network.c:' in location and function == 'observe':
                observer_frame = int(size)
            if ('coh_original_ent_costume.c:' in location or 'coh_original_taskforce_receive.c:' in location
                    or 'coh_original_costume_receive.c:' in location or 'original_ent_costume_receive.inc:' in location
                    or 'original_taskforce_receive.inc:' in location or 'original_costume_receive.inc:' in location
                    or function in parser_frames):
                assert kind in ('static', 'dynamic,bounded')
                frames.append({'function': function, 'bytes': int(size), 'kind': kind})
    closure = sum(row['bytes'] for row in frames)
    reserve = result['modes']['release']['stack_reserve']
    assert observer_frame and closure + observer_frame <= reserve
    result['memory'] = {'initial_observer_domain_limit': 8388608,
                        'interop_owner_bytes': result['modes']['release']['interop_owner_bytes'],
                        'host_fixture_mapping_index_bytes': 643072 + 134144,
                        'conservative_parser_frame_sum': closure, 'observer_frame': observer_frame,
                        'accounted_stack_reserve': reserve, 'frames': frames,
                        'maximum_java_replay_payload_bytes': 65624, 'device_RSS_PSS': None,
                        'complete_process_memory_claim': False}
    for selected in ([0, 0, 0, 0, 0], [1, 9, 8, 28, 10000]):
        assert separate_report_extension({'costume_outer': [0, 15, 100, 10000, 10000, 9999, 1, 1, 0, 0], 'selected_costume': selected, 'costume_next': 'entity suffix', 'costume_next_kind': 'source field', 'power_customization': [0, 1, 0, 0, 0, 0, 9999, 10000], 'initial_tail': [0, 0, 0]}) == {}
    for field, value in [('costume_outer', [0, 15, 100, 10000, 10000, 9999, 1, 1, 1, 0]), ('selected_costume', [1, 0, 9, 28, 10000]), ('selected_costume', [0, 0, 1, 28, 10000]), ('costume_next', 'READY')]:
        row = {'costume_outer': [0, 15, 100, 10000, 10000, 9999, 1, 1, 0, 0], 'selected_costume': [1, 0, 1, 28, 10000], 'costume_next': 'entity suffix', 'costume_next_kind': 'source field', 'power_customization': [0, 1, 0, 0, 0, 0, 9999, 10000], 'initial_tail': [0, 0, 0]}
        row[field] = value
        try:
            separate_report_extension(row)
        except ValueError:
            pass
        else:
            raise AssertionError('Malformed original outer progress accepted')
    assert pins == {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(frozen)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': True, 'modes': result['modes']}))


if __name__ == '__main__':
    main()
