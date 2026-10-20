#!/usr/bin/env python3
"""Qualify decoded costume capture against existing whole original senders."""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=ROOT)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=False)
    legacy = module('snapshot_original_sender', HERE / 'check_original_costume_receive.py')
    generator = module('snapshot_original_source', HERE / 'prepare_original_costume_receive.py')
    slots = module('snapshot_slot_sender', HERE / 'check_client_costume_slots.py')
    generated, provenance = generator.generate(args.source_root)
    assert generated == (HERE / 'original_costume_receive.inc').read_text()
    literal, literal_source = legacy.fixtures(args.source_root, work, generator.extract)
    archive = HERE / 'qualification/costume-builder-20261017/offline-primary-slots.bin.gz'
    raw = gzip.decompress(archive.read_bytes())
    assert len(raw) == 641477 and hashlib.sha256(raw).hexdigest() == slots.RAW_SHA
    raw_path = work / 'client-slots.bin'
    raw_path.write_bytes(raw)
    _, tables = slots.projection(raw)
    indexed, _, indexed_source = slots.indexed_sender(work, legacy, tables)
    flags = ['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic', '-fno-pie', '-no-pie', '-fstack-usage']
    sources = [HERE / 'coh_original_costume_receive.c', HERE / '../replication/coh_replication.c', HERE / 'test_costume_snapshot.c']
    dependency = subprocess.run([*flags, '-M', *map(str, sources)], capture_output=True, text=True, check=True)
    inputs = {Path(__file__).resolve(), archive, HERE / 'check_original_costume_receive.py', HERE / 'check_client_costume_slots.py'}
    for line in dependency.stdout.replace('\\\n', ' ').splitlines():
        for token in shlex.split(line.split(':', 1)[1]):
            path = Path(token).resolve()
            if path.is_relative_to(ROOT):
                inputs.add(path)
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(inputs)}
    result = {'passed': True, 'source': provenance, 'literal_sender': literal_source,
              'indexed_sender': indexed_source, 'input_sha256': hashes, 'modes': {},
              'scope': 'Lossless pointer-free output of one complete original costume body; no actor publication, guessed bodytype, runtime asset substitution or physical packet replay.'}
    env = {**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0:halt_on_error=1', 'UBSAN_OPTIONS': 'halt_on_error=1:print_stacktrace=1'}
    for mode, options in [('release', ['-O2']), ('asan', ['-O1', '-g', '-fsanitize=address']),
                          ('ubsan', ['-O1', '-g', '-fsanitize=undefined', '-fno-sanitize-recover=all'])]:
        binary = work / mode
        command = [*flags, *options, *map(str, sources), '-lcrypto', '-lm', '-o', str(binary)]
        legacy.run(command, work, mode + '-compile')
        text = legacy.run([binary, raw_path, literal, indexed], work, mode + '-run', env)
        result['modes'][mode] = json.loads(text)
    assert len({json.dumps(row, sort_keys=True) for row in result['modes'].values()}) == 1
    frames = []
    for path in work.glob('release-*.su'):
        for line in path.read_text().splitlines():
            name, size, kind = line.split('\t')
            if 'coh_original_costume_receive.c:' in name or 'original_costume_receive.inc:' in name or name.rsplit(':', 1)[-1] in ('valid', 'coh_rep_read', 'coh_rep_pack'):
                frames.append({'function': name.rsplit(':', 1)[-1], 'bytes': int(size), 'kind': kind})
    assert sum(row['bytes'] for row in frames) < 4096
    result['memory'] = {'snapshot_bytes': result['modes']['release']['snapshot_bytes'],
                        'workspace_bytes': 65536, 'stack_reserve': 4096,
                        'conservative_native_frame_sum': sum(row['bytes'] for row in frames),
                        'native_frames': frames, 'heap_allocations_in_capture': 0,
                        'initial_aggregate_limit': 8388608, 'device_RSS_PSS': None}
    assert hashes == {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(inputs)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': True, 'modes': result['modes'], 'snapshot_bytes': result['memory']['snapshot_bytes'],
                      'stack_frame_sum': result['memory']['conservative_native_frame_sum']}))


if __name__ == '__main__':
    main()
