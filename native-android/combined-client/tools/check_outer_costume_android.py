#!/usr/bin/env python3
"""New-profile actual JNI outer receiver, selected capture and bounded report."""
import argparse
import ctypes as C
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import struct
from client_slots_input import prepare_client_slots
from check_bodypart_continuation import PROBES
from report_diagnostic_contract import separate_report_extension

ROOT = Path(__file__).resolve().parents[3]
TOOLS = Path('native-android/combined-client/tools')


def rare_fixture(work):
    """One independent whole-source prefix/tail/buff composition for JNI."""
    engine = ROOT / 'native-android/engine/entities'
    modules = []
    for name in ('check', 'check_very_rare_tail', 'check_teammate_buffs'):
        spec = importlib.util.spec_from_file_location('jni_rare_' + name, engine / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules.append(module)
    entity, tail, buffs = modules
    for name in ('entity', 'tail', 'buffs'):
        (work / name).mkdir()
    elib, *epins = entity.oracle(ROOT, work / 'entity')
    tlib, tproof = tail.oracle(work / 'tail')
    blib, bproof = buffs.oracle(work / 'buffs')
    pr = (C.c_uint8 * 32768)(); pb = C.c_uint32(); ps = C.c_uint32()
    pex = (C.c_uint8 * elib.original_rare_size())()
    elib.original_rare(0, 0, 0, pr, C.byref(pb), C.byref(ps), pex)
    tr = (C.c_uint8 * 262144)(); tb = C.c_uint32(); ts = C.c_uint32()
    tn = (C.c_uint8 * tlib.tail_observation_size())(); to = (C.c_uint8 * tlib.tail_observation_size())()
    tlib.tail_original(0, 0, 0, tr, C.byref(tb), C.byref(ts), tn, to)
    br = (C.c_uint8 * 1048576)(); bb = C.c_uint32(); bs = C.c_uint32()
    bn = (C.c_uint32 * 32768)(); bo = (C.c_uint32 * 32768)(); nc = C.c_uint32(); oc = C.c_uint32()
    blib.buffs_original(0, 0, 0, br, C.byref(bb), C.byref(bs), bn, C.byref(nc), bo, C.byref(oc))
    bits = [(raw[i // 8] >> (i % 8)) & 1 for raw, begin, end in ((pr, ps.value, pb.value), (tr, ts.value, tb.value), (br, bs.value, bb.value)) for i in range(begin, end)]
    data = bytearray((len(bits) + 7) // 8)
    for at, value in enumerate(bits):
        data[at // 8] |= value << (at % 8)
    path = work / 'rare-source-fixture.bin'
    path.write_bytes(struct.pack('<I', len(bits)) + data)
    return path, {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bits': len(bits),
                  'prefix_source_pins': epins[0], 'tail_source': tproof, 'buff_source': bproof}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--replay', type=Path, help='Optional retained physical INITIAL replay; no network I/O')
    parser.add_argument('--bounded', action='store_true', help='Compile next diagnostic delivery/accounting opt-in.')
    parser.add_argument('--fallback', action='store_true', help='Compile diagnostic known-handler partial-tail ACK and 30s observation opt-in.')
    args = parser.parse_args()
    args.bounded = args.bounded or args.fallback
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=False)
    metadata = prepare_client_slots(work / 'assets')
    raw = (work / 'assets' / metadata['asset']).read_bytes()
    original = work / 'offset-asset.bin'
    original.write_bytes(b'P' * 37 + raw)
    actual_inputs = set()
    actual_source = None
    if args.replay:
        from actual_initial_fixture import prepare
        actual_source, actual_inputs = prepare(ROOT, work, args.replay.resolve(), args.bounded, args.fallback)
        suffix, suffix_source = args.replay.resolve(), {'scope': 'Rare suffix is present in the authentic retained INITIAL replay.'}
    else:
        suffix, suffix_source = rare_fixture(work)
    flags = ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic', '-fno-pie', '-no-pie', '-fstack-usage',
             '-DCOH_INTEROP_REQUEST_TX=1', '-DCOH_INTEROP_CLIENT_SLOTS=1', '-DCOH_FRAME_CAPTURE_DIAGNOSTIC=1',
             '-I', str(TOOLS / 'test-include'), '-I', 'native-android/combined-client/diagnostics/interop-adapter-20261018/test-include',
             '-I', 'native-android/engine/initial-capture', '-I', 'native-android/engine/entities',
             '-I', 'native-android/engine/session', '-I', 'native-android/include']
    if args.bounded:
        flags += ['-DCOH_BOUNDED_CONTINUATION_DIAGNOSTIC=1']
    if args.fallback:
        flags += ['-DCOH_INITIAL_ACK_FALLBACK_DIAGNOSTIC=1']
    sources = [TOOLS / ('test_actual_initial_android.c' if args.replay else 'test_outer_costume_android.c'),
               *[Path('native-android/engine/initial-capture/coh_initial_' + name + '_probe.c') for name in PROBES],
               Path('native-android/engine/initial-capture/coh_local_bodypart_default.c'),
               Path('native-android/engine/entities/coh_original_costume_receive.c'),
               Path('native-android/engine/entities/coh_original_ent_costume.c'),
               Path('native-android/engine/entities/coh_original_taskforce_receive.c'),
               Path('native-android/engine/entities/coh_original_rare_receive.c'),
               Path('native-android/engine/entities/coh_very_rare_tail.c'),
               Path('native-android/engine/entities/coh_teammate_buffs.c'),
               Path('native-android/engine/entities/coh_original_command_tail.c'),
               Path('native-android/engine/entities/coh_entities.c'), Path('native-android/engine/replication/coh_replication.c')]
    tail_sources = {
        'entities': ['coh_original_initial_tail.c', 'coh_character_outer.c', 'coh_character_tail.c', 'coh_character_creation.c', 'coh_character_initial.c', 'coh_character_prefix.c', 'coh_character_ui.c'],
        'character-data': ['coh_character_data.c'], 'entity-control': ['coh_entity_control.c'],
        'entity-globals': ['coh_power_info.c', 'coh_entity_globals.c', 'coh_badges.c'],
        'entity-inventory': ['coh_inventory.c', 'coh_invention.c', 'coh_inventory_phase.c'],
        'entity-team': ['coh_team.c'], 'entity-superstats': ['coh_superstats.c'], 'entity-social': ['coh_social.c'],
        'entity-attributes': ['coh_attrib_monitor.c'], 'entity-dynamic': ['coh_dynamic.c'], 'entity-view': ['coh_view.c']}
    sources += [Path('native-android/engine') / directory / name for directory, names in tail_sources.items() for name in names]
    if args.replay:
        flags += ['-I', str(work)]
    dependency = subprocess.run([*flags, '-M', *map(str, sources)], cwd=ROOT, capture_output=True, text=True, check=True)
    frozen = actual_inputs | ({ROOT / TOOLS / 'actual_initial_fixture.py'} if args.replay else set()) | {Path(__file__).resolve(), ROOT / TOOLS / 'report_diagnostic_contract.py', ROOT / TOOLS / 'client_slots_input.py', ROOT / metadata['source'], ROOT / 'native-android/combined-client/app/src/main/java/org/coh/nativecombined/InteropNative.java'}
    for line in dependency.stdout.replace('\\\n', ' ').splitlines():
        for name in shlex.split(line.split(':', 1)[1]):
            path = Path(name)
            path = (path if path.is_absolute() else ROOT / path).resolve()
            if path.is_relative_to(ROOT):
                frozen.add(path)
    pins = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(frozen)}
    result = {'passed': True, 'bounded_next_diagnostic': args.bounded, 'partial_tail_diagnostic': args.fallback, 'modes': {}, 'inputs_sha256': pins, 'rare_source_fixture': suffix_source,
              'scope': ('Authentic saved Thor packet through shipping JNI observer/owner with original source-static shortcuts, test-owned selection and transport/JNI/Android asset doubles; no live authentication, actual network sends or Android ABI claim.' if args.replay else 'Shipping new-profile JNI observer, with Android asset/JNI/transport doubles and source-layout sender header composition; no physical packet, Android ABI, actor or ACK claim.')}
    if args.replay:
        result['actual_source_fixture'] = actual_source
    env = {**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0:halt_on_error=1', 'UBSAN_OPTIONS': 'halt_on_error=1:print_stacktrace=1'}
    for mode, options in [('release', ['-O2']), ('asan', ['-O1', '-g', '-fsanitize=address']), ('ubsan', ['-O1', '-g', '-fsanitize=undefined', '-fno-sanitize-recover=all'])]:
        binary = work / mode
        wrap = '-Wl,--wrap=calloc,--wrap=free,--wrap=open,--wrap=close,--wrap=read,--wrap=__read_chk,--wrap=mmap,--wrap=munmap'
        if args.replay:
            wrap += ',--wrap=socket,--wrap=sendto'
        command = [*flags, *options, *map(str, sources), wrap, '-lcrypto', '-lm', '-lz', '-o', str(binary)]
        with (work / (mode + '-compile.log')).open('wb') as log:
            subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
        execution = subprocess.run([binary, original, suffix], cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
        (work / (mode + '-run.log')).write_text(execution.stdout + execution.stderr)
        if execution.returncode:
            raise RuntimeError(mode + ' execution failed; see ' + str(work / (mode + '-run.log')))
        result['modes'][mode] = json.loads(execution.stdout)
    assert len({json.dumps(row, sort_keys=True) for row in result['modes'].values()}) == 1
    frames = []
    rare_frames = []
    parser_frames = {'valid', 'coh_rep_read', 'coh_rep_pack', 'stats_leaf', 'character_stats',
                     'coh_ent_character_stats', 'fail', 'check_reader', 'coh_ent_target', 'target',
                     'coh_ent_status_effects', 'status_effects', 'coh_ent_inventory_sizes', 'inventory_sizes'}
    observer_frame = 0
    rare_names = {'valid', 'coh_rep_read', 'coh_rep_pack', 'coh_ent_rare_prefix', 'check_reader', 'stage',
                  'read_n', 'pack', 'flag', 'scalar', 'opt_pack', 'opt_bits', 'auto_bits', 'string', 'require', 'fail', 'clear_failure'}
    for path in work.glob('release-*.su'):
        for line in path.read_text().splitlines():
            location, size, kind = line.split('\t')
            function = location.rsplit(':', 1)[-1]
            if 'interop_network.c:' in location and function == 'observe':
                observer_frame = int(size)
            if ('coh_original_rare_receive.c:' in location or 'coh_very_rare_tail.c:' in location
                    or 'coh_teammate_buffs.c:' in location or
                    (('coh_entities.c:' in location or 'coh_replication.c:' in location) and function in rare_names)):
                assert kind in ('static', 'dynamic,bounded')
                rare_frames.append({'function': function, 'bytes': int(size), 'kind': kind})
            if ('coh_original_ent_costume.c:' in location or 'coh_original_taskforce_receive.c:' in location
                    or 'coh_original_costume_receive.c:' in location or 'original_ent_costume_receive.inc:' in location
                    or 'original_taskforce_receive.inc:' in location or 'original_costume_receive.inc:' in location
                    or function in parser_frames):
                assert kind in ('static', 'dynamic,bounded')
                frames.append({'function': function, 'bytes': int(size), 'kind': kind})
    closure = sum(row['bytes'] for row in frames)
    reserve = result['modes']['release']['stack_reserve']
    assert observer_frame and closure + observer_frame <= reserve
    rare_closure = sum(row['bytes'] for row in rare_frames)
    assert rare_closure + observer_frame <= reserve
    result['memory'] = {'initial_observer_domain_limit': 8388608,
                        'interop_owner_bytes': result['modes']['release']['interop_owner_bytes'],
                        'host_fixture_mapping_index_bytes': 643072 + 134144,
                        'conservative_parser_frame_sum': closure, 'observer_frame': observer_frame,
                        'accounted_stack_reserve': reserve, 'frames': frames,
                        'rare_parser_frame_sum': rare_closure, 'rare_frames': rare_frames,
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
    suffix_row = {'costume_outer': [0, 28, 100, 10000, 10000, 9999, 1, 1, 0, 0],
                  'selected_costume': [1, 0, 4, 28, 9999], 'costume_next': 'later very-rare entity fields',
                  'costume_next_kind': 'implementation remaining',
                  'power_customization': [1, 1, 1, 343, 0, 42, 5000, 9000], 'initial_tail': [1, 1, 1],
                  'inventory_words': [9900, 9950, 1, 4, 1],
                  'rare_suffix': [0, 4, 10000, 10038, 10038, 1, 1], 'initial_suffix_next': 'entity list sentinel'}
    assert separate_report_extension(suffix_row) == {}
    for field, bad in [('inventory_words', [1, 2, 1, 4, 5]), ('rare_suffix', [0, 4, 10000, 10038, 10038, 0, 1]),
                       ('initial_suffix_next', 'READY')]:
        row = {**suffix_row, field: bad}
        try:
            separate_report_extension(row)
        except ValueError:
            pass
        else:
            raise AssertionError('Malformed initial suffix progress accepted')
    if args.bounded:
        bounded = {'initial_command_tail': [0, 10, 10, 11, 1, 1, 0], 'initial_packet_complete': True,
                   'initial_continuation': [1, 1, 1, 1, 1, 1, 0, 2, 1, 1], 'completion_status': 0,
                   'post_position': [0, 0, 0, 0, 0, 0, 0], 'initial_next': 'post-update window complete',
                   'post_commands': [[2, 1, 10, 80, 10, 10]], 'continuation_policy': [20000, 1],
                   'continuation_time_basis': 'owner_monotonic_ms', 'continuation_abort': '20-second deadline',
                   'post_totals': [2, 20, 160, 0, 1, 10, 80, 119, 120, 0, 1, 118, 20117],
                   'ack_delivery': [117, 118, 500, 16, 128, 3, 2, 1, 1, 0, 64, 0, 0],
                   'ready_delivery': [117, 120, 120, 16, 128, 2, 1, 0, 1, 0, 32, 0, 0]}
        assert separate_report_extension(bounded) == {}
        assert separate_report_extension({**bounded, 'ack_delivery': [117, 118, 500, 16, 128, 4294967295, 2, 1, 4294967295, 0, 64, 0, 1]}) == {}
        assert separate_report_extension({key: value for key, value in bounded.items() if key not in
               {'continuation_policy', 'continuation_time_basis', 'continuation_abort', 'post_totals', 'ack_delivery', 'ready_delivery'}}) == {}
        for field, bad in [('post_totals', [2, 19, 160, 0, 1, 10, 80, 119, 120, 0, 1, 118, 20117]),
                           ('post_totals', [2, 20, 160, 0, 1, 10, 80, 119, 120, 0, 1, 119, 20117]),
                           ('ack_delivery', [117, 118, 500, 16, 128, 4, 3, 2, 1, 0, 96, 0, 0]),
                           ('ready_delivery', [117, 120, 120, 16, 128, 2, 0, 0, 1, 0, 32, 0, 0]),
                           ('continuation_abort', 'success'), ('continuation_policy', [10000, 8])]:
            try:
                separate_report_extension({**bounded, field: bad})
            except ValueError:
                pass
            else:
                raise AssertionError('Malformed bounded continuation metadata accepted')
    if args.fallback:
        partial = {**bounded, 'initial_command_tail': [2, 10, 20, 1, 0, 0, 343],
                   'initial_packet_complete': False, 'initial_bits': 30,
                   'initial_continuation': [0, 1, 1, 1, 1, 1, 0, 2, 1, 1],
                   'ack_permitted': False, 'initial_partial_tail': [1, 1, 0, 1, 343, 10, 11, 20, 10, 1],
                   'post_observation': [30000, 120, 1, 0]}
        assert separate_report_extension(partial) == {'initial_bits': 30, 'ack_permitted': False}
        observed = {**partial, 'continuation_abort': '30-second observation complete',
                    'post_observation': [30000, 120, 1, 1],
                    'post_totals': [2, 20, 160, 0, 1, 10, 80, 119, 120, 0, 1, 118, 30120]}
        assert separate_report_extension(observed) == {'initial_bits': 30, 'ack_permitted': False}
        for field, bad in [('initial_partial_tail', [1, 1, 1, 1, 343, 10, 11, 20, 10, 1]),
                           ('initial_partial_tail', [1, 0, 0, 1, 343, 10, 11, 20, 10, 1]),
                           ('initial_partial_tail', [0, 1, 0, 1, 343, 10, 11, 20, 10, 1]),
                           ('initial_partial_tail', [1, 1, 0, 1, 342, 10, 11, 20, 10, 1]),
                           ('initial_partial_tail', [1, 1, 0, 1, 343, 12, 11, 20, 10, 1]),
                           ('initial_partial_tail', [1, 1, 0, 1, 343, 10, 11, 20, 9, 1]),
                           ('initial_packet_complete', True), ('ack_permitted', True),
                           ('initial_continuation', [1, 1, 1, 1, 1, 1, 0, 2, 1, 1]),
                           ('post_observation', [30000, 120, 1, 1]),
                           ('post_observation', [30000, 119, 1, 0]),
                           ('post_observation', [30000, 120, 3, 0])]:
            try:
                separate_report_extension({**partial, field: bad})
            except ValueError:
                pass
            else:
                raise AssertionError('Malformed diagnostic fallback metadata accepted')
    assert pins == {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(frozen)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': True, 'modes': result['modes']}))


if __name__ == '__main__':
    main()
