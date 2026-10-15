#!/usr/bin/env python3
"""Qualify changed startup paths and source-bound Game/DbServer-only layers."""
import argparse
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
import build_startup_bundle_apk as derivative
import qualify_setup_memory as prior
import qualify_startup_schedule as closure

TEST_MODULES = prior.TEST_MODULES + ('test_startup_bundle_package', 'test_startup_bundle_client',
    'test_startup_bundle_dbserver', 'test_startup_bundle_save')
CHECK_SUITES = {
    'postgresql_save_emission_transaction_regression_verified': ['test_startup_bundle_save'],
    'changed_startup_paths_and_failure_guards_verified': ['test_startup_bundle_client',
        'test_startup_bundle_dbserver', 'test_startup_bundle_save', 'test_texture_header_index',
        'test_character_readiness', 'test_server_worktree_reuse', 'test_native_client_upgrade'],
    'retained_save_task_storage_profile_and_memory_guards_verified': list(prior.TEST_MODULES),
    'exact_payload_boundaries_and_actual_archive_extraction_verified': ['test_startup_bundle_package',
        'test_startup_bundle_client', 'test_startup_bundle_dbserver',
        'test_classify_interactive_change', 'test_classify_storage_cleanup_change'],
}
# Native client acceptance was originally part of the separately qualified frozen
# responsiveness pass. Its extended guest contract is now touched and rerun.
TEST_MODULES += ('test_native_client_upgrade',)


def source_paths(donor):
    names = set(prior.source_paths(donor)) | set(derivative.SOURCE_FILES)
    names.update(Path(importlib.import_module(name).__file__).relative_to(ROOT).as_posix() for name in TEST_MODULES)
    for directory in ('database/startup-bundle-client', 'patches/startup-bundle', 'patches/startup-bundle-client'):
        names.update(path.relative_to(ROOT).as_posix() for path in (ROOT/directory).rglob('*') if path.is_file())
    # Native staging dynamically invokes source factories and reads exact
    # immutable snapshot inputs; preserve every file referenced by both layers.
    client = derivative.client_builder(); dbserver = derivative.native_builder()
    names.update('upstream/ouroboros/'+name for name in client.texture.FILES)
    names.update('upstream/ouroboros/'+name for name in set(dbserver.PATCHED_FILES)|set(dbserver.retained.PATCHED_FILES)|{'DBServer/src/container_merge.c'})
    return sorted(closure.source_closure(names))


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
        derivative.require(result.wasSuccessful() and not result.skipped, name+' failed or skipped required checks:\n'+output)
        print(name+': '+str(result.testsRun)+' passed; no skips', flush=True)
        results[name] = {'tests_run': result.testsRun, 'status': 'passed', 'skipped': 0}
    return results


def qualify(args):
    if hasattr(time, 'tzset'): os.environ['TZ'] = 'UTC'; time.tzset()
    base = derivative.builder(); commit = base.source_commit(args.repository_commit)
    donor = derivative.validate_donor(args.donor_apk, args.donor_build_report)
    java = derivative.current_sources(donor)
    native, client = derivative.validate_native(args.native_directory, args.client_directory, commit, args.donor_apk, donor)
    pins = {name: base.file_pin(ROOT/name) for name in source_paths(donor)}
    results = regressions()
    save = importlib.import_module('test_startup_bundle_save')
    pg_fixtures = {'cancelled_child_deletion_commits', 'duplicate_insert_23505_rollback', 'delete_insert_replacement_commits'}
    derivative.require(save.REQUIRE_POSTGRESQL is True and save.POSTGRES_FIXTURES_RUN == pg_fixtures,
        'Formal qualification requires all three real PostgreSQL transaction fixtures')
    for name, expected in pins.items(): base.checked_file(ROOT/name, expected)
    checks = {name: all(results[suite]['status'] == 'passed' and results[suite]['skipped'] == 0
        and results[suite]['tests_run'] > 0 for suite in suites) for name, suites in CHECK_SUITES.items()}
    checks['exact_payload_boundaries_and_actual_archive_extraction_verified'] &= (
        len(donor['payloads']) == 67 and donor['server_payload_extraction_preflight']['status'] == 'passed')
    receipt = {'format': 1, 'status': 'passed' if all(checks.values()) else 'failed',
        'scope': derivative.QUALIFICATION_SCOPE, 'repository_commit': commit,
        'retained_runtime_repository_commit': derivative.DONOR_RUNTIME_COMMIT,
        'retained_setup_memory_repository_commit': derivative.DONOR_COMMIT,
        'retained_native_repository_commit': derivative.RETAINED_NATIVE_COMMIT,
        'donor_apk_sha256': derivative.DONOR_APK['sha256'], 'donor': derivative.donor_link(),
        'source_files': pins, 'test_suites': results, 'check_suites': CHECK_SUITES,
        'tests_run': sum(item['tests_run'] for item in results.values()), 'checks': checks,
        'physical_gameplay_validated': False, 'physical_startup_timing_validated': False,
        'physical_storage_cleanup_validated': False, 'physical_fresh_profile_recovery_validated': False,
        'native_runtime_booted': False, 'long_prior_gameplay_milestones_repeated': False,
        'runtime_refresh_required': True, 'previous_runtime_generation_retained': True, 'asset_reimport_required': False,
        'setup_memory_guards_preserved': True, 'java_or_dex_recompiled': False,
        'native_dbserver_recompiled': True, 'native_client_recompiled': True, 'native_mapserver_recompiled': False,
        'native_dbserver': native, 'native_client_startup': client,
        'postgresql_emission_fixture_verified': True, 'postgresql_emission_fixtures': sorted(save.POSTGRES_FIXTURES_RUN),
        'retained_baseline_payloads_verified': 67, 'authored_java_sources_verified': len(java), 'changed_java_sources': [],
        'server_payload_extraction_preflight': donor['server_payload_extraction_preflight'],
        'performance_claim_scope': 'Host and native source checks qualify fast server definition-cache reuse, '
            'verified root texture lookup, bounded missing-texture reports and PG cancelled-child SQL emission. '
            'The exact setup-memory DEX and retained native dependency closure remain conserved. No device timing is established.',
        'preserved_state': 'Only Game and the normal manual-Atlas DbServer supplements are recompiled. '
            'MapServer, Android runtime/graphics libraries, native archive baselines, prepared cache and world/avatar bytes retain '
            'their exact public 0.13.5 identity. Existing private profile, completed task and imported assets remain retained.'}
    derivative.validate_qualification(receipt, commit)
    derivative.require(not args.output.exists() and not args.output.is_symlink(), 'Fresh startup bundle qualification output required')
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(receipt, indent=2)+'\n')
    print('Qualified startup bundle:', receipt['tests_run'], 'host checks; device timing pending')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--repository-commit', required=True)
    for name in ('donor-apk', 'donor-build-report', 'native-directory', 'client-directory', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    qualify(parser.parse_args())


if __name__ == '__main__': main()
