#!/usr/bin/env python3
"""Qualify explicit profile recovery and the complete actual packaged preparation paths."""
import argparse
import contextlib
import importlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'tools/android'),
    str(ROOT/'tools/android/dbserver'), str(ROOT/'tools'), str(ROOT/'android/guest'),
    str(ROOT/'database/postgresql/tests'), str(ROOT/'tools/android/game')]
import build_client_profile_recovery_apk as derivative
import qualify_client_animation_repair as previous
import qualify_startup_schedule as closure

RETAINED_TEST_MODULES = previous.TEST_MODULES
NEW_TEST_MODULES = ('test_character_profile_eligibility', 'test_profile_failure_presentation',
                    'test_full_startup_preflight', 'test_client_profile_recovery_package',
                    'test_character_guest', 'test_character_host', 'test_character_reopen_host', 'test_login_guest', 'test_storage_ui',
                    'test_character_logout_position', 'test_character_server_logs', 'test_client_asset_closure_limits',
                    'test_client_attempt_retry', 'test_contact_capture', 'test_graphics_profile', 'test_guest',
                    'test_host_transport', 'test_login_host', 'test_process_exit_history', 'test_rfb_buffered_input',
                    'test_runtime_timestamps', 'test_server_message_cache_format', 'test_session_budget_java',
                    'test_startup_cache_integration', 'test_stationary_contact_evidence', 'test_task_gate_java',
                    'test_task_gate_native_contract', 'test_kings_row_runtime_dependencies')
TEST_MODULES = RETAINED_TEST_MODULES + NEW_TEST_MODULES
CHECK_SUITES = {
    'retained_regressions_and_postgresql_verified': list(RETAINED_TEST_MODULES),
    'actual_runtime_asset_installers_verified': ['test_animation_runtime_compatibility', 'test_runtime_asset_preflight',
        'test_client_animation_repair_package', 'test_client_profile_recovery_package'],
    'full_startup_orchestration_verified': ['test_full_startup_preflight', 'test_client_profile_recovery_package',
        'test_kings_row_runtime_dependencies',
        'test_character_guest', 'test_character_host', 'test_character_reopen_host', 'test_login_guest'],
    'additional_runtime_and_lifecycle_verified': list(NEW_TEST_MODULES[4:]),
    'profile_recovery_eligibility_and_ui_verified': ['test_character_profile_eligibility',
        'test_fresh_profile_recovery', 'test_storage_recovery_ui', 'test_storage_ui', 'test_profile_failure_presentation'],
    'exact_030_native_graphics_and_assets_verified': [
        'test_client_profile_recovery_package', 'test_client_animation_repair_package', 'test_animation_runtime_compatibility',
        'test_kings_row_runtime_dependencies',
        'test_client_receipt_repair_package', 'test_game_receipt_order', 'test_client_render_queue_contract',
        'test_client_gpu_profile', 'test_client_gpu_repair_package', 'test_external_assets', 'test_asset_pack_import'],
}


def validate_suite_inventory():
    derivative.require(RETAINED_TEST_MODULES == previous.TEST_MODULES
        and len(RETAINED_TEST_MODULES) == 149
        and TEST_MODULES[:149] == RETAINED_TEST_MODULES and len(TEST_MODULES) == 177
        and len(set(TEST_MODULES)) == len(TEST_MODULES)
        and set(CHECK_SUITES) == set(derivative.CHECKS)
        and all(suites and set(suites) <= set(TEST_MODULES) for suites in CHECK_SUITES.values()),
        'Every retained .30 suite and all five profile/Kings/full preparation suites and twenty-three additional lifecycle/runtime/UI suites are required')


def source_paths(donor):
    import qualify_runtime_asset_preflight as asset_preflight
    names = set(donor['qualification']['source_files']) | set(derivative.SOURCE_FILES)
    names.update(asset_preflight.SOURCE_FILES)
    import qualify_full_startup_preflight as startup
    names.update(startup.SOURCE_FILES)
    names.update(path.relative_to(ROOT).as_posix() for path in (ROOT/'android/guest').glob('*.py'))
    names.update(Path(importlib.import_module(name).__file__).relative_to(ROOT).as_posix()
                 for name in TEST_MODULES)
    animation = importlib.import_module('test_animation_runtime_compatibility')
    names.update('upstream/ouroboros/' + name for name in animation.ANIMATION_SOURCES)
    names.update({'docs/source-manifest.json', 'tools/prepare_monorail_source.py',
        'tools/android/atlasgame/test_server_animations.py',
        'tools/android/atlasgame/prepare_server_animations.py'})
    # These source inputs are read by the retained native transfer contract.
    transfer = importlib.import_module('character_transfer').source_contract()
    names.add('upstream/i24/data/server/db/maps.db')
    names.update('upstream/ouroboros/' + name for name in transfer['source_sha256'])
    return sorted(closure.source_closure(names))


@contextlib.contextmanager
def suite_donor_environment(name, historical_donor_apk):
    # The retained native compatibility gate authenticates the original .29
    # whole APK; the process-deterministic installer gate authenticates .30.
    # They intentionally share a historical environment name, so bound the
    # .29 override to its one suite and restore the candidate donor afterward.
    key = 'COH_ANIMATION_TEST_DONOR_APK'
    previous = os.environ.get(key)
    if name == 'test_animation_runtime_compatibility':
        os.environ[key] = str(historical_donor_apk.resolve())
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = previous


def regressions(historical_donor_apk):
    validate_suite_inventory()
    results = {}
    for name in TEST_MODULES:
        captured = io.StringIO()
        with suite_donor_environment(name, historical_donor_apk), \
                contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            suite = unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(name))
            derivative.require(suite.countTestCases() > 0, name + ' has no scenarios')
            result = unittest.TextTestRunner(stream=captured, verbosity=2).run(suite)
        output = captured.getvalue()
        derivative.require(len(output.encode()) <= 262144,
                           'Unbounded qualification output: ' + name)
        derivative.require(result.wasSuccessful() and not result.skipped,
                           name + ' failed or skipped:\n' + output)
        print(name + ': ' + str(result.testsRun) + ' passed; no skips', flush=True)
        results[name] = {'tests_run': result.testsRun, 'status': 'passed', 'skipped': 0}
    return results


def qualify(args):
    if hasattr(time, 'tzset'):
        os.environ['TZ'] = 'UTC'
        time.tzset()
    validate_suite_inventory()
    base = derivative.builder()
    commit = base.source_commit(args.repository_commit)
    donor = derivative.validate_donor(args.donor_apk, args.donor_build_report)
    base.checked_file(args.historical_donor_apk, derivative.previous.DONOR_APK)
    os.environ['COH_RECEIPT_REPAIR_TEST_DONOR_APK'] = str(args.historical_donor_apk.resolve())
    os.environ['COH_PROFILE_RECOVERY_TEST_DONOR_APK'] = str(args.donor_apk.resolve())
    os.environ['COH_PROFILE_RECOVERY_TEST_DONOR_REPORT'] = str(args.donor_build_report.resolve())
    os.environ['COH_ANIMATION_TEST_DONOR_APK'] = str(args.donor_apk.resolve())
    os.environ['COH_ANIMATION_TEST_DONOR_REPORT'] = str(args.donor_build_report.resolve())
    os.environ['COH_PROFILE_RECOVERY_ASSET_CACHE'] = str(args.asset_directory.resolve())
    os.environ['COH_ANIMATION_REPAIR_ASSET_CACHE'] = str(args.asset_directory.resolve())
    java = derivative.current_sources(donor)
    pins = {name: base.file_pin(ROOT/name) for name in source_paths(donor)}
    # Fail small regression, SQL and donor-wiring gates before repeating
    # the complete preparation. The package suite and final preparation both
    # remain mandatory and are independently admitted below.
    results = regressions(args.historical_donor_apk)
    save = importlib.import_module('test_startup_bundle_save')
    derivative.require(save.REQUIRE_POSTGRESQL is True and save.POSTGRES_FIXTURES_RUN == {
        'cancelled_child_deletion_commits', 'duplicate_insert_23505_rollback',
        'delete_insert_replacement_commits'}, 'All three real PostgreSQL emission fixtures required')
    levelup = importlib.import_module('test_levelup_ui_repair_dbserver')
    derivative.require(levelup.REQUIRE_POSTGRESQL is True
        and levelup.POSTGRES_FIXTURES_RUN == levelup.REQUIRED_POSTGRES_FIXTURES
        and len(levelup.POSTGRES_FIXTURES_RUN) == 4,
        'All four real PostgreSQL level-up fixtures required')
    profile = importlib.import_module('test_character_profile_eligibility')
    derivative.require(profile.REQUIRE_POSTGRESQL is True
        and profile.POSTGRES_FIXTURES_RUN == profile.REQUIRED_POSTGRES_FIXTURES
        and len(profile.POSTGRES_FIXTURES_RUN) == 14,
        'All fourteen real PostgreSQL empty-profile recovery and preservation fixtures required')
    with tempfile.TemporaryDirectory(prefix='coh-animation-qualification-') as temporary:
        runtime, payloads, preflight = derivative.extract_and_repair(
            args.donor_apk, donor, Path(temporary)/'donor', commit)
        derivative.payload_boundaries(payloads, donor)
    # Exercise actual candidate guest helpers and complete original payloads.
    # This is real asset preparation, not a claim of native process/device boot.
    proof = preflight['runtime_assets']
    derivative.require(proof.get('status') == 'passed'
        and proof.get('scope') == 'actual_packaged_guest_external_asset_installers'
        and proof.get('fresh_create_payload_verified') is True
        and proof.get('saved_reopen_payload_verified') is True
        and proof.get('animation_count') == 5878
        and proof.get('atlas_cold_and_reuse_verified') is True
        and proof.get('kings_cold_and_reuse_verified') is True
        and proof.get('prepared_caches_verified') is True
        and proof.get('native_runtime_booted') is False
        and proof.get('physical_execution_validated') is False,
        'Complete actual packaged animation/cache/Atlas/Kings preparation required')
    full = preflight['full_startup']
    derivative.require(full.get('status') == 'passed'
        and full.get('scope') == 'actual_packaged_guest_full_startup_orchestration'
        and all(full.get(name) is True for name in ('full_private_worktree_mirror_executed',
            'full_prepare_runtime_executed', 'fresh_create_cold_preparation_verified',
            'saved_reopen_warm_preparation_verified', 'full_kings_row_cold_and_reuse_preparation_verified'))
        and full.get('native_runtime_booted') is False
        and full.get('physical_execution_validated') is False
        and full.get('process_and_sql_boundary') == 'not_executed',
        'Complete actual guest preparation orchestration and truthful process boundary required')
    for name, expected in pins.items():
        base.checked_file(ROOT/name, expected)
    checks = {name: all(results[suite]['status'] == 'passed'
        and results[suite]['skipped'] == 0 and results[suite]['tests_run'] > 0
        for suite in suites) for name, suites in CHECK_SUITES.items()}
    receipt = {
        'format': 1, 'status': 'passed' if all(checks.values()) else 'failed',
        'scope': derivative.QUALIFICATION_SCOPE, 'repository_commit': commit,
        'runtime_repository_commit': commit, 'donor': derivative.donor_link(),
        'historical_test_donor': derivative.historical_test_donor_link(),
        'source_files': pins, 'test_suites': results, 'check_suites': CHECK_SUITES,
        'checks': checks, 'tests_run': sum(value['tests_run'] for value in results.values()),
        'postgresql_emission_fixtures': sorted(save.POSTGRES_FIXTURES_RUN),
        'postgresql_levelup_fixtures': sorted(levelup.POSTGRES_FIXTURES_RUN),
        'postgresql_profile_eligibility_fixtures': sorted(profile.POSTGRES_FIXTURES_RUN),
        'java_sources': java, 'changed_java_sources': sorted(derivative.JAVA_CHANGES),
        'donor_dex': donor['retained_dex'],
        'external_asset_pack': donor['external_asset_pack'],
        'native_build_provenance': donor['native_build_provenance'],
        'package_preflight': preflight,
        **dict.fromkeys(derivative.FALSE_FLAGS, False),
        **dict.fromkeys(derivative.TRUE_FLAGS, True),
        'claim_scope': 'Host qualification executes the complete actual packaged fresh-create and saved-reopen '
            'preparation including original reference worktree mirroring and Atlas/Kings cold/reuse installers. '
            'Real PostgreSQL fixtures and compiled Java dispatch tests enforce explicit empty-profile recovery '
            'without relaxing saved-character acceptance. Only reviewed Java/DEX and two guest helpers change; '
            'native Game/DbServer/MapServer, renderer, Android resources and Assets 1.0.0 remain exact. '
            'Native process boot and physical Thor creation, entry, save/reopen and travel still require device evidence.',

    }
    derivative.validate_qualification(receipt, commit, donor)
    derivative.require(not args.output.exists() and not args.output.is_symlink(),
                       'Fresh qualification output required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print('Qualified explicit profile recovery and full preparation:', receipt['tests_run'],
          'host scenarios; physical Thor retest pending', flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository-commit', required=True)
    for name in ('donor-apk', 'donor-build-report', 'historical-donor-apk', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--asset-directory', type=Path, default=ROOT/'out/profile-recovery-assets')
    qualify(parser.parse_args())


if __name__ == '__main__':
    main()
