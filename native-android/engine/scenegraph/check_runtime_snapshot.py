#!/usr/bin/env python3
"""Host-only source snapshot admission. Never starts a server or publishes a world."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import struct
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def run(command, **kwargs):
    result = subprocess.run(list(map(str, command)), capture_output=True,
                            text=True, timeout=180, **kwargs)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(65536):
            value.update(block)
    return value.hexdigest()


def module(path):
    spec = importlib.util.spec_from_file_location('runtime_snapshot_source_oracle', path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source-root', type=Path, default=ROOT)
    p.add_argument('--producer-root', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--sanitize', action='store_true')
    p.add_argument('--fixtures-output', type=Path)
    p.add_argument('--catalog', type=Path)
    p.add_argument('--snapshot', type=Path)
    for name in ('catalog-sha256', 'snapshot-sha256', 'source-sha256', 'run-sha256'):
        p.add_argument('--' + name)
    p.add_argument('--asset-generation', type=int)
    a = p.parse_args()
    actual = [a.catalog, a.snapshot, a.catalog_sha256, a.snapshot_sha256,
              a.source_sha256, a.run_sha256, a.asset_generation]
    if any(x is not None for x in actual) and not all(x is not None for x in actual):
        p.error('Actual snapshot requires both paths, four independently trusted digests, and asset generation')
    if a.catalog:
        for value in actual[2:6]:
            if not re.fullmatch('[0-9a-f]{64}', value) or value == '0' * 64:
                p.error('SHA256 pins must be nonzero lowercase hexadecimal')
        if not 0 < a.asset_generation <= 0xffffffff:
            p.error('Invalid asset generation')
        if not 0 < a.catalog.stat().st_size <= 32 * 1024**2 or not 0 < a.snapshot.stat().st_size <= 16 * 1024**2:
            p.error('Actual input exceeds its bounded byte envelope')
        if sha(a.catalog) != a.catalog_sha256 or sha(a.snapshot) != a.snapshot_sha256:
            raise ValueError('Actual captured bytes do not match independent digest pins')
    producer = (a.producer_root or a.source_root).resolve() / 'native-android/engine/scenecatalog-server'
    producer_files = [producer / name for name in (
        'snapshot_oracle.py', 'test_snapshot.c', 'source_snapshot.inc')]
    producer_files += [producer.parent / 'scenecatalog/source_export.inc']
    sources = [HERE / 'runtime_snapshot.c', HERE / 'tests/runtime_matrix_bridge.c',
               HERE / 'tests/test_runtime_snapshot.c',
               HERE.parent / 'scenecatalog/coh_scenecatalog.c',
               HERE.parent / 'replication/coh_replication.c',
               HERE.parent / 'replication/coh_groups.c']
    native_files = [*sources, HERE / 'runtime_snapshot.h', HERE / 'coh_scenegraph.c',
                    HERE / 'coh_scenegraph.h', HERE / 'check_runtime_snapshot.py',
                    HERE.parent / 'scenecatalog/coh_scenecatalog.h',
                    HERE.parent / 'replication/coh_replication.h',
                    HERE.parent / 'replication/coh_groups.h',
                    HERE.parent / 'coh_contracts.h']
    original_helpers = [a.source_root / path for path in (
        'native-android/engine/replication/groups_oracle.py',
        'native-android/engine/replication/groups-source-pins.json',
        'native-android/engine/replication/tests/groups_oracle_harness.c',
        'native-android/engine/replication/tests/groups_oracle_shim.h',
        'native-android/tools/protocol_fixture/prepare.py')]
    initial = {path: sha(path) for path in [*producer_files, *native_files, *original_helpers]}
    native_hashes = {str(path.relative_to(ROOT)): initial[path] for path in native_files}
    producer_hashes = {str(path.relative_to(producer.parent.parent.parent)): initial[path] for path in producer_files}
    with tempfile.TemporaryDirectory(prefix='coh-runtime-snapshot-') as temporary:
        work = Path(temporary)
        oracle = module(producer / 'snapshot_oracle.py')
        original, source_oracle = oracle.prepare(a.source_root.resolve(), work)
        original_binary = work / 'original'
        run(['cc', '-std=c99', '-O0', '-fno-strict-aliasing', '-w', '-I' + str(producer),
             '-I' + str(a.source_root / 'native-android/include'), original, '-lm', '-lz', '-o', original_binary])
        producer_checks = json.loads(run([original_binary, work]))
        fixture_paths = sorted(work.glob('snapshot-*.cohcat'))
        if len(fixture_paths) < 8:
            raise ValueError('Original producer did not emit required paired fixtures')
        expected_path = work / 'fixture-expected.json'
        expected = {}
        if not expected_path.is_file():
            raise ValueError('Missing original source fixture expectation manifest')
        manifest = json.loads(expected_path.read_text())
        if manifest.get('schema') != 1 or not isinstance(manifest.get('fixtures'), list):
            raise ValueError('Malformed source fixture expectation manifest')
        for row in manifest['fixtures']:
            key = 'snapshot-' + str(row['id'])
            if key in expected or type(row['expected_status']) is not int or not 0 <= row['expected_status'] <= 7:
                raise ValueError('Duplicate or invalid fixture expectation')
            expected[key] = row['expected_status']
        if any(expected.get('snapshot-' + str(i)) != value for i, value in enumerate((0, 0, 0, 0, 1, 4, 0, 0))):
            raise ValueError('Required root/future/cycle/depth source controls changed')
        fixtures = []
        for catalog in fixture_paths:
            snapshot = catalog.with_suffix('.cohrts')
            raw = catalog.read_bytes()
            fixtures.append({'catalog': catalog.name, 'snapshot': snapshot.name,
                             'catalog_sha256': sha(catalog), 'snapshot_sha256': sha(snapshot),
                             'asset_generation': struct.unpack_from('<I', raw, 20)[0],
                             'expected_status': expected.get(catalog.stem, 0)})
        if set(expected) != {path.stem for path in fixture_paths}:
            raise ValueError('Fixture expectation manifest does not cover exact corpus')
        if a.fixtures_output:
            a.fixtures_output.mkdir(parents=True, exist_ok=True)
            for fixture in fixtures:
                for key in ('catalog', 'snapshot'):
                    shutil.copyfile(work / fixture[key], a.fixtures_output / fixture[key])
        modes = [('release', ['-O2', '-fstack-usage'])]
        if a.sanitize:
            modes += [('asan', ['-O1', '-g', '-fno-omit-frame-pointer', '-fsanitize=address', '-no-pie']),
                      ('ubsan', ['-O1', '-g', '-fno-omit-frame-pointer', '-fsanitize=undefined', '-fno-sanitize-recover=all'])]
        checks, captured = {}, {}
        binaries = {}
        for mode, extra in modes:
            binary = work / mode
            run([os.environ.get('CC', 'cc'), '-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic',
                 '-I' + str(HERE), *extra, *sources, '-Wl,--wrap=malloc,--wrap=calloc,--wrap=free',
                 '-lm', '-lcrypto', '-o', binary])
            binaries[mode] = sha(binary)
            environment = {**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0:halt_on_error=1',
                           'UBSAN_OPTIONS': 'halt_on_error=1:print_stacktrace=1'}
            rows = []
            for fixture in fixtures:
                rows.append(json.loads(run([binary, work / fixture['catalog'], work / fixture['snapshot'],
                    fixture['asset_generation'], fixture['catalog_sha256'], fixture['snapshot_sha256'],
                    '11' * 32, '22' * 32, fixture['expected_status'], '--test'], env=environment)))
            checks[mode] = rows
            by_name = {fixture['catalog']: row for fixture, row in zip(fixtures, rows)}
            if by_name['snapshot-1.cohcat']['reachable_external'] != 2 or by_name['snapshot-2.cohcat']['reachable_external'] != 1:
                raise ValueError('Source pointer-incidence/reachability control disagrees')
            if by_name['snapshot-2.cohcat']['external'][0]['reachable'] != 0:
                raise ValueError('Unreachable source future was treated as root reachable')
            if 'snapshot-7.cohcat' in by_name and by_name['snapshot-7.cohcat']['maximum_depth'] != 128:
                raise ValueError('Original depth boundary control disagrees')
            if a.catalog:
                captured[mode] = json.loads(run([binary, a.catalog, a.snapshot, a.asset_generation,
                    a.catalog_sha256, a.snapshot_sha256, a.source_sha256, a.run_sha256, 0], env=environment))
        if any(value != checks['release'] for value in checks.values()):
            raise ValueError('Native qualification modes disagree')
        if captured and any(value != captured['release'] for value in captured.values()):
            raise ValueError('Captured snapshot qualification modes disagree')
        if initial != {path: sha(path) for path in initial}:
            raise ValueError('A source or checker changed during qualification')
        if a.catalog and (sha(a.catalog) != a.catalog_sha256 or sha(a.snapshot) != a.snapshot_sha256):
            raise ValueError('Capture changed during qualification')
        for fixture in fixtures:
            if sha(work / fixture['catalog']) != fixture['catalog_sha256'] or sha(work / fixture['snapshot']) != fixture['snapshot_sha256']:
                raise ValueError('Source fixture changed during qualification')
        stack_frames = []
        for path in sorted(work.glob('release-*.su')):
            for line in path.read_text().splitlines():
                if '/runtime_snapshot.c:' in line or '/runtime_matrix_bridge.c:' in line:
                    location, size, bound = line.split('\t')
                    stack_frames.append({'function': location.rsplit(':', 1)[-1],
                                         'bytes': int(size), 'bound': bound})
        if not stack_frames:
            raise ValueError('Compiler did not emit diagnostic stack reservations evidence')
        result = {'schema': 'coh-runtime-snapshot-native-qualification-v1', 'passed': True,
                  'scope': 'same-boundary original-runtime source snapshot diagnostic; no received GROUPS or live world',
                  'source_oracle': source_oracle, 'producer_checks': producer_checks,
                  'native_source_sha256': native_hashes, 'producer_source_sha256': producer_hashes,
                  'original_helper_sha256': {str(path.relative_to(a.source_root)): initial[path] for path in original_helpers},
                  'fixtures': fixtures, 'checks': checks, 'binary_sha256': binaries,
                  'native_diagnostic_stack_frames': stack_frames,
                  'actual_snapshot_qualified': bool(captured), 'captured': captured,
                  'graph_published': False, 'groups_received': False, 'world_authority': False,
                  'assets_admitted': False, 'actor_admitted': False, 'android_executed': False,
                  'physical_thor_accepted': False, 'allocation_failure_cleanup_checked': True,
                  'leak_sanitizer': False, 'memory_scope': 'named native inputs, pool, decoded record, output, stack reservations and 256KiB caller/crypto/test reserve; not process RSS'}
        if captured:
            result['capture_pins'] = {'asset_generation': a.asset_generation, 'catalog_sha256': a.catalog_sha256,
                                     'snapshot_sha256': a.snapshot_sha256, 'source_sha256': a.source_sha256,
                                     'run_sha256': a.run_sha256}
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'passed': True, 'output': str(a.output), 'fixtures': len(fixtures),
                          'checks': sum(row['checks'] for row in checks['release']),
                          'actual_snapshot_qualified': bool(captured)}))


if __name__ == '__main__':
    main()
