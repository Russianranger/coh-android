#!/usr/bin/env python3
"""Qualify startup scheduling, supplement reuse and retained state boundaries.

The Windows job separately compiles the native guard and normal DbServer.
These focused host scenarios prove source/asset identity, ordering, cancellation
and retained save/storage/cache behavior. They do not establish device timings.
"""
import argparse
import ast
import contextlib
import importlib
import io
import json
import os
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'tools/android'),
               str(ROOT/'tools/android/dbserver'), str(ROOT/'tools'), str(ROOT/'android/guest')]
import build_startup_schedule_apk as derivative

# Focus on touched startup paths and state they could affect. Native Game,
# MapServer and all baseline archive qualification are inherited by exact bytes.
TEST_MODULES = ('test_startup_schedule_package', 'test_startup_schedule',
    'test_world_asset_reuse', 'test_atlas_world_assets', 'test_local_launcher_wait',
    'test_character_readiness', 'test_character_server', 'test_character_reopen_guest',
    'test_ground_repair', 'test_task_gate_integration', 'test_task_gate_evidence',
    'test_runtime_setup_reuse', 'test_fresh_profile_recovery', 'test_storage_recovery_ui',
    'test_storage_audit', 'test_wine_refresh', 'test_server_worktree_reuse',
    'test_server_cache_package', 'test_texture_header_index', 'test_session_budget_guest',
    'test_stable_worktree_identity', 'test_classify_interactive_change',
    'test_classify_storage_cleanup_change')
CHECK_SUITES = {
    'world_supplement_reuse_identity_and_invalidation_verified': ['test_world_asset_reuse', 'test_atlas_world_assets'],
    'atlas_first_texture_schedule_and_failure_cleanup_verified': ['test_startup_schedule', 'test_character_readiness', 'test_texture_header_index'],
    'guarded_native_manual_atlas_launcher_wait_verified': ['test_local_launcher_wait', 'test_startup_schedule_package'],
    'retained_save_task_storage_profile_and_cache_guards_verified': [
        'test_character_server', 'test_character_reopen_guest', 'test_ground_repair',
        'test_task_gate_integration', 'test_task_gate_evidence', 'test_session_budget_guest',
        'test_runtime_setup_reuse', 'test_fresh_profile_recovery', 'test_storage_recovery_ui',
        'test_storage_audit', 'test_wine_refresh', 'test_server_worktree_reuse',
        'test_server_cache_package', 'test_stable_worktree_identity'],
    'source_bound_payload_and_actual_archive_extraction_verified': [
        'test_startup_schedule_package', 'test_classify_interactive_change', 'test_classify_storage_cleanup_change'],
}


def source_closure(names):
    """Pin local static imports and explicitly listed dynamically loaded files."""
    found = set(names); visited = set()
    queue = [ROOT/name for name in found if name.endswith('.py')]
    directories = tuple(ROOT/name for name in ('tools', 'tools/android', 'tools/android/interactive',
        'tools/android/client', 'tools/android/dbserver', 'tools/android/game', 'tools/android/atlasgame', 'android/guest'))
    while queue:
        path = queue.pop()
        if path in visited: continue
        visited.add(path)
        for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
            if isinstance(node, ast.Import): modules = [item.name for item in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module: modules = [node.module]
            else: continue
            for name in modules:
                for directory in (path.parent, *directories):
                    candidate = directory/(name.replace('.', '/')+'.py')
                    if candidate.is_file():
                        relative = candidate.relative_to(ROOT).as_posix()
                        if relative not in found: found.add(relative); queue.append(candidate)
    return found


def source_paths(donor):
    names = set(derivative.SOURCE_FILES)
    names.update(donor['java_sources']); names.update(donor['preserved_sources'])
    names.update(path.relative_to(ROOT).as_posix() for path in
        (ROOT/'android/interactive/src/main/res').rglob('*') if path.is_file())
    names.update('android/guest/'+Path(name).name for name in donor['payloads']
        if name.startswith('assets/runtime/') and (name.endswith('.py') or name.endswith('/task-gate.json')))
    names.update(Path(importlib.import_module(name).__file__).relative_to(ROOT).as_posix() for name in TEST_MODULES)
    native = derivative.native_builder()
    names.add(native.PATCH)
    names.update(native.OVERLAY+'/'+name for name in native.OVERLAY_FILES)
    names.update(('docs/source-manifest.json', 'upstream-lock.json',
        'tools/prepare_wine_dbserver_source.py', 'tools/android/dbserver/package_dbserver.py',
        'database/wine-dbserver/odbc32-exports.json',
        'database/wine-dbserver/tests/loopback_portable_windows.h',
        'docs/android-evidence/dbserver-package-36460867428.json',
        native.wine.PATCH,
        'patches/postgresql/0001-dbserver-postgresql.patch'))
    for directory in ('database/wine-dbserver/overlay', 'database/postgresql/overlay'):
        names.update(path.relative_to(ROOT).as_posix() for path in (ROOT/directory).rglob('*') if path.is_file())
    # Native staging receipts recompute the exact patched source closure.
    names.update('upstream/ouroboros/'+name for name in native.wine.WINE_FILES)
    names.update('upstream/ouroboros/'+name for name in native.expected_receipt()['base_wine_build_input']['postgresql_build_input']['patched_sha256'])
    return sorted(source_closure(names))


def regressions():
    results = {}
    for name in TEST_MODULES:
        suite = unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(name))
        derivative.require(suite.countTestCases() > 0, name+' has no focused scenarios')
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            result = unittest.TextTestRunner(stream=captured, verbosity=2).run(suite)
        output = captured.getvalue()
        derivative.require(len(output.encode()) <= 262144, 'Unbounded qualification output: '+name)
        derivative.require(result.wasSuccessful() and not result.skipped,
            name+' failed or skipped required checks:\n'+output)
        print(name+': '+str(result.testsRun)+' passed; no skips', flush=True)
        results[name] = {'tests_run': result.testsRun, 'status': 'passed', 'skipped': 0}
    return results


def qualify(args):
    if hasattr(time, 'tzset'): os.environ['TZ'] = 'UTC'; time.tzset()
    base = derivative.builder(); commit = base.source_commit(args.repository_commit)
    donor = derivative.validate_donor(args.donor_apk, args.donor_build_report)
    java = derivative.current_sources(donor)
    native = derivative.validate_native(args.native_directory, commit, args.donor_apk)
    pins = {name: base.file_pin(ROOT/name) for name in source_paths(donor)}
    results = regressions()
    for name, expected in pins.items(): base.checked_file(ROOT/name, expected)
    checks = {name: all(results[suite]['status'] == 'passed' and results[suite]['skipped'] == 0
        and results[suite]['tests_run'] > 0 for suite in suites) for name, suites in CHECK_SUITES.items()}
    checks['source_bound_payload_and_actual_archive_extraction_verified'] &= (
        donor['server_payload_extraction_preflight']['status'] == 'passed' and len(donor['payloads']) == 65)
    receipt = {'format': 1, 'status': 'passed' if all(checks.values()) else 'failed',
        'scope': derivative.QUALIFICATION_SCOPE, 'repository_commit': commit,
        'retained_native_repository_commit': derivative.RETAINED_NATIVE_COMMIT,
        'donor_apk_sha256': derivative.DONOR_APK['sha256'], 'donor': derivative.donor_link(),
        'source_files': pins, 'test_suites': results, 'check_suites': CHECK_SUITES,
        'tests_run': sum(item['tests_run'] for item in results.values()), 'checks': checks,
        'native_dbserver': native, 'native_dbserver_recompiled': True, 'native_game_or_mapserver_recompiled': False,
        'physical_gameplay_validated': False, 'physical_startup_timing_validated': False,
        'physical_storage_cleanup_validated': False, 'physical_fresh_profile_recovery_validated': False,
        'native_runtime_booted': False, 'long_prior_gameplay_milestones_repeated': False,
        'retained_baseline_payloads_verified': len(donor['payloads']), 'authored_java_sources_verified': len(java),
        'changed_java_sources': [], 'server_payload_extraction_preflight': donor['server_payload_extraction_preflight'],
        'runtime_refresh_required': True, 'previous_runtime_generation_retained': True, 'asset_reimport_required': False,
        'performance_claim_scope': 'Host checks establish Atlas-first ordering, safe independent-work overlap, '
            'world supplement reuse identity and bounded failure cleanup. The separately built DbServer '
            'can bypass only the unused launcher wait under the explicit verified native configuration. '
            'No device startup duration or seconds saved is established.',
        'preserved_state': 'The exact installed baseline DbServer package identity, Game, MapServer, '
            'world/avatar assets, all prepared caches and existing private profile remain retained. '
            'One Setup runtime creates the updated manifest generation; the preceding generation remains '
            'available for rollback and reviewed storage cleanup. Reimport and database recreation are unnecessary.'}
    derivative.validate_qualification(receipt, commit)
    derivative.require(not args.output.exists() and not args.output.is_symlink(), 'Fresh startup qualification output required')
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(receipt, indent=2)+'\n')
    print('Qualified startup candidate:', receipt['tests_run'], 'focused host checks; device timing pending')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository-commit', required=True)
    for name in ('donor-apk', 'donor-build-report', 'native-directory', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    qualify(parser.parse_args())


if __name__ == '__main__': main()
