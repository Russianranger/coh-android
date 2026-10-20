#!/usr/bin/env python3
"""Focused original ACK/READY callback, payload lifetime and bounded UDP window."""
import argparse
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
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, default=ROOT, help='Read-only pinned original source checkout for sparse local worktrees.')
    parser.add_argument('--bounded', action='store_true', help='Next diagnostic opt-in:20s and one same-ID accepted retry.')
    args = parser.parse_args()
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=False)
    request = module('continuation_request', HERE / 'check_request_tx.py')
    preservation = request.preservation()
    sources = request.sources() + [HERE / 'coh_initial_send.c', HERE / 'test_initial_continuation.c']
    db = module('continuation_db_source', HERE.parent / 'dbclient/check.py')
    original, db_source = db.oracle(args.source_root.resolve(), work)
    db.fixtures(original, work)
    groups = module('continuation_groups_source', HERE.parent / 'replication/groups_oracle.py')
    fixtures, groups_source = groups.produce_fixtures(args.source_root.resolve(), work / 'groups')
    fixture = next(row for row in fixtures if row['name'] == 'minimal_world_packed')
    payload = bytes.fromhex(fixture['payload_hex'])
    (work / 'groups-fixtures.h').write_text('static const unsigned char source_groups_minimal_world_packed[]={' + ','.join(map(str, payload)) + '};\n#define source_groups_minimal_world_packed_bits ' + str(fixture['payload_bits']) + 'u\n')
    flags = ['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-DCOH_FRAME_CAPTURE_DIAGNOSTIC=1', '-I' + str(ROOT / 'native-android/include'), '-I' + str(work), '-fno-pie', '-no-pie', '-fstack-usage']
    if args.bounded:
        flags += ['-DCOH_BOUNDED_CONTINUATION_DIAGNOSTIC=1']
    dependency = subprocess.run([*flags, '-MM', *map(str, sources)], cwd=ROOT, capture_output=True, text=True, check=True)
    frozen = {Path(__file__).resolve()}
    for line in dependency.stdout.replace('\\\n', ' ').splitlines():
        for name in shlex.split(line.split(':', 1)[1]):
            path = Path(name).resolve()
            if path.is_relative_to(ROOT):
                frozen.add(path)
    pins = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(frozen)}
    result = {'passed': True, 'source_sha256': pins, 'original_db_fixture': db_source, 'original_groups_fixture': groups_source, 'request_tx_preservation': preservation, 'modes': {}, 'bounded_next_diagnostic': args.bounded, 'scope': 'Actual local OS UDP with a synthetic completion callback. Actual full saved-packet qualification is separate. No real server, actor publication or post-initial raw payload export.'}
    environment = {**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0:halt_on_error=1', 'UBSAN_OPTIONS': 'halt_on_error=1:print_stacktrace=1'}
    for mode, options in [('release', ['-O2']), ('asan', ['-O1', '-g', '-fsanitize=address']), ('ubsan', ['-O1', '-g', '-fsanitize=undefined', '-fno-sanitize-recover=all'])]:
        objects = []
        for index, source in enumerate(sources):
            target = work / (mode + str(index) + '.o')
            extra = ['-O0'] if source.name in ('coh_protocol.c', 'coh_blowfish.c') else []
            compile = subprocess.run([*flags, *options, *extra, '-c', str(source), '-o', str(target)], cwd=ROOT, capture_output=True, text=True)
            (work / (mode + str(index) + '-compile.log')).write_text(compile.stdout + compile.stderr)
            if compile.returncode:
                raise RuntimeError(mode + ' compile failed: ' + str(source))
            objects.append(target)
        binary = work / mode
        subprocess.run([*flags, *options, *map(str, objects), '-Wl,--wrap=malloc,--wrap=calloc,--wrap=free,--wrap=coh_net_udp_owned_release,--wrap=sendto', '-lcrypto', '-lz', '-lm', '-o', str(binary)], cwd=ROOT, capture_output=True, text=True, check=True)
        run = subprocess.run([str(binary)], cwd=ROOT, env=environment, capture_output=True, text=True, timeout=90)
        (work / (mode + '-run.log')).write_text(run.stdout + run.stderr)
        if run.returncode:
            raise RuntimeError(mode + ' execution failed; see ' + str(work / (mode + '-run.log')))
        result['modes'][mode] = json.loads(run.stdout)
    assert len({json.dumps(value, sort_keys=True) for value in result['modes'].values()}) == 1
    assert pins == {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(frozen)}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': True, 'modes': result['modes']}))


if __name__ == '__main__':
    main()
