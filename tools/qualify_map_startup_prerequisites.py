#!/usr/bin/env python3
"""Qualify offline MapServer prerequisites without rebuilding published .32."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import io
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASE = '005bc8eaa5d88744706de19ca37cb3f8a8053c7d'
MODULES = ('test_map_startup_observer_source', 'test_map_startup_bounded_stream',
           'test_analyze_enhancement_persistence')
SOURCE_FILES = (
    'tools/prepare_map_startup_observer_source.py',
    'tools/test_map_startup_observer_source.py',
    'tools/test_map_startup_bounded_stream.py',
    'tools/android/interactive/analyze_enhancement_persistence.py',
    'tools/android/interactive/test_analyze_enhancement_persistence.py',
    'tools/qualify_map_startup_prerequisites.py',
    '.github/workflows/map-startup-prerequisites.yml',
)
SOURCE_DIRS = ('database/map-startup-observer', 'database/map-startup-physics/qualification')


def frozen_sources():
    """Reject modifications to existing production code relative to .32."""
    names = subprocess.check_output(
        ['git', 'diff', '--name-only', BASE, '--', 'android', 'upstream',
         'patches', 'tools', 'database', '.github/workflows'], cwd=ROOT, text=True).splitlines()
    retained = []
    for name in names:
        exists = subprocess.run(['git', 'cat-file', '-e', BASE + ':' + name],
                                cwd=ROOT, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL).returncode == 0
        if exists:
            retained.append(name)
    if retained:
        raise ValueError('Offline prerequisite lane changed existing .32 code: ' + ', '.join(retained))
    guide = 'docs/COH-Atlas-Gameplay-0.13.32-testing.txt'
    qualified = subprocess.check_output(['git', 'show', BASE + ':' + guide], cwd=ROOT)
    if (ROOT / guide).read_bytes() != qualified:
        raise ValueError('Published .32 guide must retain its qualified bytes')
    return {'baseline_commit': BASE, 'existing_production_sources_unchanged': True,
            'published_guide_sha256': hashlib.sha256(qualified).hexdigest()}


def source_pins():
    paths = {ROOT / name for name in SOURCE_FILES}
    for directory in SOURCE_DIRS:
        paths.update(path for path in (ROOT / directory).rglob('*') if path.is_file())
    result = {}
    for path in sorted(paths):
        if not path.is_file() or path.is_symlink() or any(p.is_symlink() for p in path.parents):
            raise ValueError('Missing or linked prerequisite input: ' + str(path))
        raw = path.read_bytes()
        result[path.relative_to(ROOT).as_posix()] = {
            'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    return result


def qualify(output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/android/interactive')]
    frozen = frozen_sources()
    pins = source_pins()
    suites = []
    component_evidence = {}
    for module in MODULES:
        log = io.StringIO()
        started = time.monotonic()
        suite = unittest.defaultTestLoader.loadTestsFromName(module)
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
        elapsed = time.monotonic() - started
        log_path = output.parent / (module + '.log')
        log_path.write_text(log.getvalue(), encoding='utf-8')
        row = {'module': module, 'tests_run': result.testsRun, 'failures': len(result.failures),
               'errors': len(result.errors), 'skipped': len(result.skipped),
               'unexpected_successes': len(result.unexpectedSuccesses),
               'expected_failures': len(result.expectedFailures),
               'elapsed_seconds': round(elapsed, 3), 'log': log_path.name,
               'passed': result.wasSuccessful() and result.testsRun > 0 and not result.skipped
                   and not result.expectedFailures}
        suites.append(row)
        if module == 'test_map_startup_bounded_stream':
            component_evidence['bounded_stream'] = importlib.import_module(module).evidence(result)
        print(json.dumps(row), flush=True)
        if not row['passed']:
            print(log.getvalue(), file=sys.stderr)
    unchanged = pins == source_pins()
    frozen_sources()
    document = {
        'format': 1, 'role': 'offline_map_startup_prerequisite_qualification',
        'status': 'passed' if unchanged and all(x['passed'] for x in suites) else 'failed',
        'repository_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                                                     text=True).strip(),
        'working_tree_source_pins': pins, 'sources_unchanged_during_tests': unchanged,
        'frozen_release_boundary': frozen, 'suites': suites,
        'component_evidence': component_evidence,
        'suites_run': len(suites), 'tests_run': sum(x['tests_run'] for x in suites),
        'skipped': sum(x['skipped'] for x in suites),
        'scope': [
            'Source-staged SERVER freshness observer and extracted native stock-equivalence fixtures',
            'Owned bounded stream core and actual SDK-header adapter on the host, without PhysX SDK execution',
            'Offline enhancement snapshot comparison, without SQL writes or device-session authentication'],
        'shipping_native_binary_rebuilt': False, 'apk_built_or_published': False,
        'asset_pack_rebuilt': False, 'freshness_bypass_enabled': False,
        'cooked_mesh_cache_enabled': False, 'physical_thor_tested': False,
        'performance_improvement_established': False,
        'remaining_gates': [
            'Native Win32/Wine observer execution and paired physical .32 measurements',
            'Complete native effective-provider and immutable-generation authority before per-BIN certificates',
            'PhysX SDK load/failure handling, exact geometry/SDK/cooking keys and Atlas/Kings collision parity',
            'Physical persistence, both monorail directions, saved Kings reopen and complete report/cleanup'],
    }
    output.write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    value = qualify(args.output)
    print(json.dumps({'status': value['status'], 'tests_run': value['tests_run'],
                      'suites_run': value['suites_run'], 'physical_thor_tested': False}))
    return 0 if value['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
