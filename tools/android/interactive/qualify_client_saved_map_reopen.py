#!/usr/bin/env python3
"""Qualify direct saved-map startup, report recovery and bounded cache reuse from exact public .33."""
import argparse
import ast
import contextlib
import importlib
import io
import json
import os
import subprocess
from pathlib import Path
import sys
import tempfile
import time
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'tools/android'),
    str(ROOT/'tools/android/dbserver'), str(ROOT/'tools'), str(ROOT/'android/guest'),
    str(ROOT/'database/postgresql/tests'), str(ROOT/'tools/android/game'), str(ROOT/'tools/android/atlasgame')]
import build_client_saved_map_reopen_apk as derivative
import qualify_client_map_startup as previous
import qualify_startup_schedule as closure

import qualify_client_report_loading as published
RETAINED_TEST_MODULES = published.TEST_MODULES
NEW_TEST_MODULES = ('test_client_saved_map_reopen_package', 'test_saved_map_startup',
    'test_saved_map_window_java', 'test_saved_map_postgresql')
TEST_MODULES = RETAINED_TEST_MODULES + NEW_TEST_MODULES
# Immutable packaging producers and the unchanged prior certificate contract
# retain original evidence. All changed guest/UI,
# report, SQL, native-byte/reader and runtime preparation suites execute here.
RETAINED_CONTRACT_MODULES = frozenset({
    'test_client_receipt_repair_package', 'test_client_animation_repair_package',
    'test_client_profile_recovery_package', 'test_client_map_startup_package',
    'test_client_report_loading_package', 'test_map_startup_animation_certificate'})
CHECK_SUITES = {
    'retained_regressions_and_postgresql_verified': list(RETAINED_TEST_MODULES),
    'actual_runtime_asset_installers_verified': ['test_client_saved_map_reopen_package', 'test_runtime_asset_preflight'],
    'full_startup_orchestration_verified': ['test_full_startup_preflight', 'test_client_saved_map_reopen_package',
        'test_shared_collision_input_proof'],
    'report_finalization_and_recovery_verified': ['test_client_report_lifecycle_java',
        'test_client_report_recovery_java', 'test_client_report_controls_java', 'test_completed_guest_report_java',
        'test_profile_failure_presentation', 'test_storage_ui', 'test_storage_recovery_ui', 'test_storage_audit'],
    'saved_map_startup_and_preservation_verified': ['test_saved_map_startup', 'test_saved_map_window_java',
        'test_saved_map_postgresql', 'test_character_zoning', 'test_character_reopen_guest',
        'test_kings_row_runtime_dependencies', 'test_character_monorail', 'test_monorail_native_package'],
    'bounded_cache_reuse_verified': ['test_server_worktree_reuse', 'test_collision_input_snapshot',
        'test_shared_collision_input_proof', 'test_map_startup_observation', 'test_map_startup_cache_reuse'],
    'exact_033_native_graphics_and_assets_verified': ['test_client_saved_map_reopen_package',
        'test_client_render_queue_contract', 'test_client_gpu_profile', 'test_client_gpu_repair_package',
        'test_external_assets', 'test_asset_pack_import', 'test_animation_runtime_compatibility',
        'test_map_startup_native_contract', 'test_map_startup_animation_certificate'],
}


def validate_suite_inventory():
    derivative.require(RETAINED_TEST_MODULES == published.TEST_MODULES
        and len(RETAINED_TEST_MODULES) == 196 and TEST_MODULES[:196] == RETAINED_TEST_MODULES
        and len(set(TEST_MODULES)) == len(TEST_MODULES)
        and RETAINED_CONTRACT_MODULES <= set(RETAINED_TEST_MODULES)
        and set(CHECK_SUITES) == set(derivative.CHECKS)
        and all(suites and set(suites) <= set(TEST_MODULES) for suites in CHECK_SUITES.values()),
        'Every .33 suite and every current saved-map/report/cache/SQL/retention gate is required')


def source_paths(donor):
    names = set(donor['qualification']['source_files']) | set(derivative.SOURCE_FILES)
    names.update(Path(importlib.import_module(name).__file__).relative_to(ROOT).as_posix() for name in TEST_MODULES)
    names.update(path.relative_to(ROOT).as_posix() for path in (ROOT/'android/guest').glob('*.py'))
    return sorted(closure.source_closure(names))


def retained_contract_result(name, donor):
    derivative.require(name in RETAINED_CONTRACT_MODULES,
        'Only unchanged source-bound historical contracts may retain prior results')
    original = donor['qualification']['test_suites'][name]
    derivative.require(original.get('status') == 'passed' and original.get('skipped') == 0
        and type(original.get('tests_run')) is int and original['tests_run'] > 0,
        'Authenticated .33 historical suite result is invalid: '+name)
    source = Path(importlib.import_module(name).__file__).relative_to(ROOT).as_posix()
    original_pin = donor['qualification']['source_files'][source]
    derivative.builder().checked_file(ROOT/source, original_pin)
    # Inherited evidence is source-bound to the original complete .33 closure.
    # Changes are only admitted through the finite current source boundary,
    # every other source is already checked against the authenticated donor.
    return {'tests_run': original['tests_run'], 'status': 'passed', 'skipped': 0,
        'source_scope': 'accepted_033_immutable_source_bound_contract',
        'source_repository_commit': derivative.DONOR_COMMIT,
        'tests_executed_in_current_run': False, 'donor_suite_result': original,
        'donor_build_report': derivative.DONOR_BUILD,
        'original_suite_source': {source: original_pin},
        'original_qualification_source_closure': derivative.pin(derivative.shared.encoded(
            donor['qualification']['source_files'])),
        'native_producer_relabelled': False}


def current_suite_test_count(name):
    derivative.require(name in TEST_MODULES and name not in RETAINED_CONTRACT_MODULES,
                       'Only pinned current qualification suites may supply current test counts')
    suite = unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(name))
    count = suite.countTestCases()
    derivative.require(type(count) is int and count > 0, 'Current suite has no loader scenarios: '+name)
    return count


def validate_current_suite_result(name, row):
    derivative.require(row.get('source_scope') == 'current_034_candidate_sources'
        and row.get('tests_executed_in_current_run') is True and row.get('status') == 'passed'
        and type(row.get('skipped')) is int and row['skipped'] == 0
        and type(row.get('tests_run')) is int and row['tests_run'] == current_suite_test_count(name),
        'Current pinned suite requires its exact loader scenario count and no skips: '+name)
    return row


def configure_native_contract_fixture(apk):
    """Authenticate the existing .31 parser fixture without rebuilding it.

    The current serialized full-preflight suite exercises the typed native
    reader with its historical .31 package. Its animation inputs are supplied
    separately by the unchanged, authenticated Assets 1.0.0 fixture closure.
    This donor is a test input, never the shipping .34 runtime donor.
    """
    apk = Path(apk)
    derivative.builder().checked_file(apk, derivative.previous.DONOR_APK)
    apk = apk.resolve()
    os.environ['COH_MAP_STARTUP_TEST_DONOR_APK'] = str(apk)
    return {'role': 'existing_public_031_native_parser_fixture_only',
        'apk': derivative.previous.DONOR_APK, 'current_suites': ['test_full_startup_preflight', 'test_map_startup_native_contract',
            'test_map_startup_cache_reuse'],
        'shipping_runtime_donor_changed': False, 'native_binary_rebuilt': False}


def regressions(donor):
    validate_suite_inventory(); results = {}
    early = ('test_full_startup_preflight', 'test_runtime_asset_preflight')
    execution = tuple(name for name in NEW_TEST_MODULES if name != 'test_client_saved_map_reopen_package') + \
        early + tuple(name for name in RETAINED_TEST_MODULES if name not in RETAINED_CONTRACT_MODULES
                      and name not in early) + \
        tuple(sorted(RETAINED_CONTRACT_MODULES)) + ('test_client_saved_map_reopen_package',)
    derivative.require(len(execution) == len(TEST_MODULES) and set(execution) == set(TEST_MODULES),
                       'Every retained/current qualification suite must be attributed exactly once')
    for name in execution:
        if name in RETAINED_CONTRACT_MODULES:
            row = retained_contract_result(name, donor)
        else:
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
                suite = unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(name))
                derivative.require(suite.countTestCases() > 0, name+' has no scenarios')
                result = unittest.TextTestRunner(stream=captured, verbosity=2).run(suite)
            output = captured.getvalue()
            derivative.require(len(output.encode()) <= 262144, 'Unbounded qualification output: '+name)
            derivative.require(result.wasSuccessful() and not result.skipped, name+' failed or skipped:\n'+output)
            row = {'tests_run': result.testsRun, 'status': 'passed', 'skipped': 0,
                'source_scope': 'current_034_candidate_sources', 'tests_executed_in_current_run': True}
        print(name+': '+str(row['tests_run'])+' passed; no skips; '+row['source_scope'], flush=True)
        results[name] = row
    return results


def encoded_receipt(value):
    # Preserve authenticated native producer LF/CRLF receipt key order.
    return json.dumps(value, indent=2, allow_nan=False)+'\n'


def qualify(args):
    if hasattr(time, 'tzset'):
        os.environ['TZ'] = 'UTC'
        time.tzset()
    validate_suite_inventory()
    base = derivative.builder()
    commit = base.source_commit(args.repository_commit)
    derivative.require_source_identity(commit)
    donor = derivative.validate_donor(args.donor_apk, args.donor_build_report)
    native_contract_fixture = configure_native_contract_fixture(args.native_contract_donor_apk)
    os.environ['COH_MAP_STARTUP_ASSET_CACHE'] = str(args.asset_directory.resolve())
    os.environ['COH_PROFILE_RECOVERY_ASSET_CACHE'] = str(args.asset_directory.resolve())
    os.environ['COH_SAVED_MAP_REOPEN_TEST_DONOR_APK'] = str(args.donor_apk.resolve())
    os.environ['COH_SAVED_MAP_REOPEN_TEST_DONOR_REPORT'] = str(args.donor_build_report.resolve())
    os.environ['COH_SAVED_MAP_REOPEN_TEST_SOURCE_COMMIT'] = commit
    import build_client_profile_recovery_apk as original_dependency
    derivative.builder().checked_file(args.dependency_donor_apk, original_dependency.DONOR_APK)
    os.environ['COH_PROFILE_RECOVERY_TEST_DONOR_APK'] = str(args.dependency_donor_apk.resolve())
    import build_client_animation_repair_apk as original_animation
    derivative.builder().checked_file(args.animation_donor_apk, original_animation.DONOR_APK)
    os.environ['COH_ANIMATION_TEST_DONOR_APK'] = str(args.animation_donor_apk.resolve())
    import qualify_runtime_asset_preflight as assets
    import qualify_full_startup_preflight as full_assets
    payloads = assets.ensure_assets(args.asset_directory)
    full_assets.extra_inputs(payloads)
    os.environ['COH_FX_TEST_CLIENT_CACHES'] = str(payloads/'client-caches.zip')
    os.environ['COH_MAP_STARTUP_TEST_ANIMATIONS'] = str(payloads/'server-animations.pigg')
    os.environ['COH_MAP_STARTUP_TEST_ANIMATION_MANIFEST'] = str(payloads/'server-animation-manifest.json')
    os.environ['COH_ANIMATION_REPAIR_ASSET_CACHE'] = str(args.asset_directory.resolve())
    java = derivative.current_sources(donor)
    paths = source_paths(donor)
    derivative.require_committed_sources(commit, paths)
    pins = {name: base.file_pin(ROOT/name) for name in source_paths(donor)}
    # Fail small regression, SQL and donor-wiring gates before repeating
    # the complete preparation. The package suite and final preparation both
    # remain mandatory and are independently admitted below.
    results = regressions(donor)
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
    saved_map = importlib.import_module('test_saved_map_postgresql')
    saved_map_proof = saved_map.qualification_inventory()
    derivative.require(saved_map.REQUIRE_POSTGRESQL is True
        and saved_map.POSTGRES_FIXTURES_RUN == saved_map.REQUIRED_POSTGRES_FIXTURES,
        'All strict read-only saved-map PostgreSQL fixtures must execute currently')
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
        'native_contract_test_fixture': native_contract_fixture,
        'native_dependency_test_fixture': {'role': 'original_public_030_native_dependency_fixture_only',
            'apk': original_dependency.DONOR_APK, 'repository_commit': original_dependency.DONOR_COMMIT,
            'current_suites': ['test_kings_row_runtime_dependencies'],
            'shipping_runtime_donor_changed': False, 'native_binary_rebuilt': False},
        'native_animation_test_fixture': {'role': 'original_public_029_animation_compatibility_fixture_only',
            'apk': original_animation.DONOR_APK, 'repository_commit': original_animation.DONOR_COMMIT,
            'current_suites': ['test_animation_runtime_compatibility'],
            'shipping_runtime_donor_changed': False, 'native_binary_rebuilt': False},
        'source_files': pins, 'test_suites': results, 'check_suites': CHECK_SUITES,
        'checks': checks, 'tests_run': sum(value['tests_run'] for value in results.values()),
        'current_tests_run': sum(value['tests_run'] for value in results.values() if value['tests_executed_in_current_run']),
        'inherited_tests_retained': sum(value['tests_run'] for value in results.values() if not value['tests_executed_in_current_run']),
        'current_suites_run': sum(value['tests_executed_in_current_run'] for value in results.values()),
        'inherited_suites_retained': sum(not value['tests_executed_in_current_run'] for value in results.values()),
        'postgresql_emission_fixtures': sorted(save.POSTGRES_FIXTURES_RUN),
        'postgresql_levelup_fixtures': sorted(levelup.POSTGRES_FIXTURES_RUN),
        'postgresql_profile_eligibility_fixtures': sorted(profile.POSTGRES_FIXTURES_RUN),
        'postgresql_saved_map_fixtures': sorted(saved_map.POSTGRES_FIXTURES_RUN),
        'saved_map_postgresql_proof': saved_map_proof,
        'java_sources': java, 'changed_java_sources': derivative.changed_java_sources(donor),
        'donor_dex': donor['recompiled_dex'],
        'external_asset_pack': donor['external_asset_pack'],
        'native_build_provenance': donor['native_build_provenance'],
        'map_startup_component': preflight['map_startup_component'],
        'package_preflight': preflight,
        **dict.fromkeys(derivative.FALSE_FLAGS, False),
        **dict.fromkeys(derivative.TRUE_FLAGS, True),
        'claim_scope': 'Current host qualification executes every changed saved-map/report/cache/SQL scope, '
            'all applicable retained regressions and actual packaged fresh-create/reopen Atlas/Kings preparation. '
            'Five immutable historical packaging suites and unchanged certificate regression retain authenticated .33 source-bound results; nested '
            '.32 native producers keep their original identities and are never rebuilt or relabelled. '
            'Native reader/dependency/animation regression suites execute with original authenticated fixture inputs. '
            'Strict isolated PostgreSQL saved-map fixtures do not read or mutate the physical THORHERO database. '
            'No host gate establishes physical Kings Row direct reopen, graphics, save/export, startup speed or travel.',



    }
    derivative.validate_qualification(receipt, commit, donor)
    derivative.require(not args.output.exists() and not args.output.is_symlink(),
                       'Fresh qualification output required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded_receipt(receipt))
    print('Qualified saved-map/report/cache continuation:', receipt['current_tests_run'],
          'current host scenarios;', receipt['inherited_tests_retained'],
          'unchanged donor scenarios retained; physical Thor retest pending', flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository-commit', required=True)
    for name in ('donor-apk', 'donor-build-report', 'native-contract-donor-apk', 'dependency-donor-apk', 'animation-donor-apk', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--asset-directory', type=Path, default=ROOT/'out/map-startup-assets')
    qualify(parser.parse_args())


if __name__ == '__main__': main()
