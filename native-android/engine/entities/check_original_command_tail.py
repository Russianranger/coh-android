#!/usr/bin/env python3
"""Qualify original application reads with private UI shims and saved INITIAL tails."""
import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value
def digest(data):
    return hashlib.sha256(data).hexdigest()
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--replay', type=Path)
    parser.add_argument('--begin', type=int)
    args = parser.parse_args()
    assert bool(args.replay) == (args.begin is not None)
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=False)
    generator = module('command_original_generate', HERE / 'prepare_original_command_tail.py')
    generated, source = generator.generate(ROOT)
    assert generated == (HERE / 'original_command_tail.inc').read_text()
    legacy = module('command_native_run', HERE / 'check_original_costume_receive.py')
    paths = [HERE / name for name in ('coh_original_command_tail.c', 'coh_original_command_tail.h',
        'original_command_tail.inc', 'prepare_original_command_tail.py', 'test_original_command_tail.c',
        'check_original_command_tail.py', 'command-tail-entry-contract.json', '../replication/coh_replication.c', '../replication/coh_replication.h')]
    hashes = {path.resolve(): digest(path.read_bytes()) for path in paths}
    result = {'passed': True, 'source': source, 'modes': {},
        'scope': 'Original source handlers and actual command termination; no actor/UI/filesystem publication or READY/ACK.',
        'source_safety_shims': 'Pinned call-line guards cover contact/task indices, signed counts, Karma StatsSent[9], UI vars and bitmap spans. Friends substitutes NULL display labels and private ordering; all original packet reads remain. Fixed UI/audio sinks publish nothing.'}
    flags = ['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-pedantic',
             '-fno-pie', '-no-pie', '-fstack-usage']
    sources = [HERE / name for name in ('test_original_command_tail.c', 'coh_original_command_tail.c',
                                       '../replication/coh_replication.c')]
    for mode, options in [('release', []), ('asan', ['-O1', '-g', '-fsanitize=address']),
            ('ubsan', ['-O1', '-g', '-fsanitize=undefined', '-fno-sanitize-recover=all'])]:
        binary = work / mode
        legacy.run([*flags, *options, *sources, '-o', binary], work, mode + '-compile')
        command = [binary] + ([args.replay, str(args.begin)] if args.replay else [])
        result['modes'][mode] = json.loads(legacy.run(command, work, mode + '-run',
            {**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0:halt_on_error=1', 'UBSAN_OPTIONS': 'halt_on_error=1'}))
    assert len({json.dumps(value, sort_keys=True) for value in result['modes'].values()}) == 1
    frames = []
    for file in work.glob('release-*.su'):
        if 'test_original_command_tail' in file.name:
            continue
        for line in file.read_text().splitlines():
            name, size, kind = line.split('\t')
            if 'coh_replication.c:' in name and name.rsplit(':', 1)[-1] not in ('valid', 'coh_rep_read', 'coh_rep_pack'):
                continue
            frames.append({'function': name, 'bytes': int(size), 'kind': kind})
    frame_sum = sum(frame['bytes'] for frame in frames)
    assert frame_sum <= 16384
    result['memory'] = {'workspace_bytes': result['modes']['release']['workspace_bytes'],
        'report_bytes': result['modes']['release']['report_bytes'], 'heap_allocations': 0, 'private_context_bytes': result['modes']['release']['context_bytes'],
        'stack_reserve': 16384, 'closed_native_frame_sum': frame_sum, 'frames': frames,
        'initial_aggregate_limit': 8388608, 'decoded_message_limit': 4194304,
        'ordinary_message_limit': 16384, 'RSS_PSS': None}
    if args.replay:
        replay = args.replay.read_bytes()
        assert replay[:8] == b'COHIRP01' and int.from_bytes(replay[8:12], 'little') == 88
        assert int.from_bytes(replay[12:16], 'little') == len(replay) - 88
        assert digest(replay[88:]) == replay[56:88].hex()
        assert 0 <= args.begin < int.from_bytes(replay[16:24], 'little') <= (len(replay) - 88) * 8
        result['saved_initial_replay'] = {'file_sha256': digest(replay), 'payload_sha256': digest(replay[88:]),
            'begin_bit': args.begin, 'logical_bits': int.from_bytes(replay[16:24], 'little'),
            'raw_input_committed': False, 'Thor_latest_session_verified': False}
    result['inputs_sha256'] = {str(path.relative_to(ROOT)): value for path, value in hashes.items()}
    assert hashes == {path: digest(path.read_bytes()) for path in hashes}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': True, 'modes': result['modes'], 'stack': frame_sum}))
if __name__ == '__main__':
    main()
