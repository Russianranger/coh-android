#!/usr/bin/env python3
"""Qualify isolated offline prerequisites; never qualify a shipping successor.

The published .32 guide and immutable native/publication proofs retain their
exact historical bytes. Authorized production changes elsewhere on the branch
are recorded, not certified or prohibited by this host-only prototype lane.
"""
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
OFFLINE_BASE = '66a273d4f8cc3e7e4a9180c12a60385f30de454f'
MODULES = ('test_map_startup_observer_source', 'test_map_startup_bounded_stream',
           'test_analyze_enhancement_persistence', 'test_qualify_map_startup_prerequisites')
SOURCE_FILES = (
    'tools/prepare_map_startup_observer_source.py',
    'tools/test_map_startup_observer_source.py',
    'tools/test_map_startup_bounded_stream.py',
    'tools/android/interactive/analyze_enhancement_persistence.py',
    'tools/android/interactive/test_analyze_enhancement_persistence.py',
    'tools/qualify_map_startup_prerequisites.py',
    'tools/test_qualify_map_startup_prerequisites.py',
    '.github/workflows/map-startup-prerequisites.yml',
)
SOURCE_DIRS = ('database/map-startup-observer', 'database/map-startup-physics/qualification')
PROTOTYPE_FILES = frozenset(SOURCE_FILES) | frozenset({
    'database/map-startup-observer/README.md',
    'database/map-startup-observer/overlay/libs/UtilitiesLib/src/utils/coh_map_bin_observer.h',
    'database/map-startup-physics/qualification/host-prerequisite-evidence.json',
    'database/map-startup-physics/qualification/owned_bounded_stream.h',
    'database/map-startup-physics/qualification/nx_owned_bounded_stream.h',
    'database/map-startup-physics/qualification/bounded_stream_fixture.cpp',
})
BOUNDARY_FILES = {
    'docs/COH-Atlas-Gameplay-0.13.32-testing.txt': BASE,
    'docs/android-evidence/client-map-startup-0.13.32-native.json': BASE,
    'docs/android-evidence/client-map-startup-0.13.32-publication.json': BASE,
    'docs/android-evidence/map-startup-prerequisites-20261012.json': OFFLINE_BASE,
}
PRODUCTION_ROOTS = ('android', 'upstream', 'patches', 'tools', 'database', '.github/workflows')
DEPENDENCY_FILES = (
    'tools/map_startup_namespace_certificate.py',
    'tools/test_map_startup_namespace_certificate.py',
    'upstream/ouroboros/libs/UtilitiesLib/src/utils/textparser.c',
    'upstream/ouroboros/libs/UtilitiesLib/src/utils/FolderCache.c',
    'upstream/ouroboros/libs/UtilitiesLib/src/utils/FolderCacheNode.c',
    'upstream/ouroboros/libs/UtilitiesLib/src/utils/file.c',
    'upstream/ouroboros/libs/UtilitiesLib/src/utils/structInternals.c',
    'upstream/ouroboros/Common/seq/seqload.c',
    'upstream/ouroboros/Common/fxinfo.c',
    'upstream/ouroboros/3rdparty/PhysX/SDKs/Foundation/include/NxStream.h',
    'upstream/ouroboros/3rdparty/PhysX/SDKs/Foundation/include/NxSimpleTypes.h',
    'upstream/ouroboros/3rdparty/PhysX/SDKs/Foundation/include/Nx.h',
    'docs/schema-generation-evidence/accepted-36088012666.zip',
    'upstream/ouroboros/MapServer/src/container/containerloadsave.c',
    'upstream/ouroboros/MapServer/src/entity/character_db.c',
)


def checked_record(path):
    if not path.is_file() or path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError('Missing or linked prerequisite input: ' + str(path))
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def production_changes(names):
    """Observe changed/add/delete source paths; prototype ownership is finite."""
    result = {}
    for name in sorted(set(names) - PROTOTYPE_FILES):
        path = ROOT / name
        if path.is_symlink() or any(p.is_symlink() for p in path.parents):
            # A foreign source may be linked; record the link without following
            # it or granting qualification authority to its target.
            result[name] = {'state': 'linked', 'qualified_by_this_lane': False}
        elif path.is_file():
            result[name] = {'state': 'present', **checked_record(path),
                            'qualified_by_this_lane': False}
        elif not path.exists():
            result[name] = {'state': 'deleted', 'qualified_by_this_lane': False}
        else:
            raise ValueError('Changed source is not a regular file: ' + name)
    return result


def frozen_sources():
    """Freeze historical evidence while observing, never approving, production."""
    names = subprocess.check_output(
        ['git', 'diff', '--name-only', BASE, '--', *PRODUCTION_ROOTS], cwd=ROOT, text=True).splitlines()
    names += subprocess.check_output(
        ['git', 'ls-files', '--others', '--exclude-standard', '--', *PRODUCTION_ROOTS],
        cwd=ROOT, text=True).splitlines()
    boundary = {}
    for name, commit in BOUNDARY_FILES.items():
        expected = subprocess.check_output(['git', 'show', commit + ':' + name], cwd=ROOT)
        observed = checked_record(ROOT / name)
        if observed != {'bytes': len(expected), 'sha256': hashlib.sha256(expected).hexdigest()}:
            raise ValueError('Immutable published .32 guide/proof or historical prerequisite evidence changed: ' + name)
        boundary[name] = {'baseline_commit': commit, **observed}
    changed = production_changes(names)
    return {'baseline_commit': BASE, 'immutable_published_evidence_unchanged': True,
            'existing_production_sources_unchanged': not changed,
            'production_changes_observed': bool(changed),
            'changed_production_sources': changed, 'immutable_evidence_pins': boundary,
            'published_guide_sha256': boundary['docs/COH-Atlas-Gameplay-0.13.32-testing.txt']['sha256'],
            'successor_shipping_qualified': False,
            'production_change_policy': 'observe_only_requires_separate_shipping_owner_acceptance'}


def source_pins():
    paths = {ROOT / name for name in (*PROTOTYPE_FILES, *DEPENDENCY_FILES)}
    for directory in SOURCE_DIRS:
        current = {path.relative_to(ROOT).as_posix() for path in (ROOT / directory).rglob('*')
                   if path.is_file() or path.is_symlink()}
        if not current <= PROTOTYPE_FILES:
            raise ValueError('Unreviewed offline prototype input: ' + ', '.join(sorted(current - PROTOTYPE_FILES)))
    result = {}
    for path in sorted(paths):
        result[path.relative_to(ROOT).as_posix()] = checked_record(path)
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
    frozen = frozen_sources()
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
        'qualification_authority': 'isolated_offline_prerequisites_only',
        'production_changes_observed': frozen['production_changes_observed'],
        'successor_shipping_qualified': False,
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
