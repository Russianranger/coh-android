#!/usr/bin/env python3
"""Execute every retained Linux host suite from its actual source directory.

The .32 native Windows station fixture and the two full-donor FX modules have
separate mandatory owners. They cannot be discovered as ordinary fixture-free
Linux suites. This runner excludes only those three files, names their owners,
and otherwise executes all current test files while requiring every .31 file.
Existing platform-specific cases inside historical modules remain unchanged.
"""
from __future__ import annotations
import argparse
import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_MODULES = {
    'game': (
        'test_bridge_protocol.py', 'test_bridge_receipt.py', 'test_character_events.py',
        'test_game_diagnostic.py', 'test_game_evidence.py', 'test_game_hang_evidence.py',
        'test_game_loopback_bind.py', 'test_game_map_progress.py', 'test_host_game_smoke.py',
        'test_mapserver_progress.py', 'test_monorail.py', 'test_package_game_runtime.py',
        'test_package_loopback_game.py', 'test_package_mapserver_progress.py',
        'test_prepare_game_data.py', 'test_stack_probe.py', 'test_stack_probe_receipt.py'),
    'atlasgame': (
        'test_atlas_game_build_apk.py', 'test_atlas_game_prepare_assets.py',
        'test_game_acceptance.py', 'test_game_device_diagnostic.py', 'test_host_device_smoke.py',
        'test_operation_dispatch.py', 'test_prepare_server_caches.py',
        'test_qualify_published_server_caches.py', 'test_server_animations.py',
        'test_server_message_source_contract.py'),
}
REQUIRED_ADDITIONS = {'game': (), 'atlasgame': ('test_device_cleanup_lineage.py',)}
EXCLUDED_MODULES = {
    'game': {'test_map_startup_monorail_budget.py':
        'Genuine Win32/MSVC nine-case fixture: android-map-startup-native.yml native job; '
        'accepted raw binary/report required again by .32 component admission.'},
    'atlasgame': {
        'test_server_fx_catalog.py':
            'Complete authenticated public donor: all cases required by .32 publication qualification.',
        'test_server_fx_catalog_native_proof.py':
            'Complete authenticated public donor/native proof controls: all cases required by .32 publication qualification.'},
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inventory(group, *, root=ROOT):
    require(group in HISTORICAL_MODULES, 'Unknown retained host suite group')
    directory = Path(root)/'tools/android'/group
    require(directory.is_dir() and not directory.is_symlink(), 'Actual regular test directory required')
    found = {}
    for path in directory.glob('test_*.py'):
        require(path.is_file() and not path.is_symlink(), 'Linked or nonregular host test source: '+path.name)
        found[path.name] = path
    required = set(HISTORICAL_MODULES[group]) | set(REQUIRED_ADDITIONS[group])
    excluded = EXCLUDED_MODULES[group]
    require(required <= set(found), 'Retained host suite inventory is incomplete: '+', '.join(sorted(required-set(found))))
    require(set(excluded) <= set(found), 'Separately owned fixture sources are missing')
    selected = {name: found[name] for name in sorted(set(found)-set(excluded))}
    require(selected and required <= set(selected), 'Every retained host module must execute')
    return directory, selected, dict(excluded)


def load_suite(group, path):
    """Load the selected file directly, never a same-named module in tools/."""
    name = '_coh_retained_'+group+'_'+path.stem
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, 'Host source loader missing')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    before = list(sys.path)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
        require(Path(module.__file__).resolve() == path.resolve(), 'Host module source attribution differs')
        suite = unittest.defaultTestLoader.loadTestsFromModule(module)
        require(suite.countTestCases() > 0, 'Retained host suite has no scenarios: '+path.name)
        # Historical modules install their own helper paths. Retain those paths
        # for lazy production imports during that module's cases, while keeping
        # its actual directory first and restoring the caller afterward.
        search = [str(path.parent), *(entry for entry in sys.path if entry != str(path.parent))]
        return suite, search
    finally:
        sys.path[:] = before


def run(group):
    directory, selected, excluded = inventory(group)
    print('Retained host group:', group, '; actual directory:', directory, flush=True)
    for name, scope in sorted(excluded.items()):
        print('Separate mandatory owner:', group+'/'+name, ';', scope, flush=True)
    total = skipped = 0
    for name, path in selected.items():
        suite, search = load_suite(group, path)
        before = list(sys.path)
        sys.path[:] = search
        try:
            result = unittest.TextTestRunner(verbosity=2).run(suite)
        finally:
            sys.path[:] = before
        require(result.wasSuccessful(), 'Retained host suite failed: '+group+'/'+name)
        total += result.testsRun
        skipped += len(result.skipped)
        print('Retained module:', group+'/'+name, '; tests:', result.testsRun,
              '; existing platform skips:', len(result.skipped), flush=True)
    print('Retained host group passed:', group, '; modules:', len(selected),
          '; tests:', total, '; existing platform skips:', skipped, flush=True)
    return {'group': group, 'modules': len(selected), 'tests_run': total,
            'existing_platform_skips': skipped, 'separate_mandatory_modules': sorted(excluded)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', required=True, choices=sorted(HISTORICAL_MODULES))
    run(parser.parse_args().group)


if __name__ == '__main__':
    main()
