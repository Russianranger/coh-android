#!/usr/bin/env python3
"""Qualify per-row PostgreSQL saves, exact UI leaves and interactive preloading.

Retained source/visual scenarios and new appearance/package suites all use the
actual candidate guest contract. Historical source proofs remain intact; their
stale package identity is refused by the new exact manifest pin.
"""
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
import build_levelup_ui_repair_apk as derivative
import qualify_client_startup_followup as prior
import qualify_startup_schedule as closure

RETAINED_TEST_MODULES = tuple(name for name in prior.TEST_MODULES
    if name != 'test_client_startup_followup_package')
TEST_MODULES = RETAINED_TEST_MODULES + ('test_levelup_ui_repair_dbserver',
    'test_client_ui_repair_assets',
    'test_levelup_ui_repair_contract', 'test_levelup_ui_repair_package',
    'test_client_preload_launch', 'test_training_save')
CHECK_SUITES = {
    'postgres_levelup_attribmod_transaction_repair_verified': ['test_levelup_ui_repair_dbserver', 'test_startup_bundle_save'],
    'missing_only_ui_assets_and_retained_visual_streams_verified': ['test_client_ui_repair_assets',
        'test_client_visual_assets', 'test_client_appearance_assets', 'test_texture_header_index'],
    'owned_native_reward_delta_and_strict_save_rows_verified': ['test_combat_reward_save', 'test_training_save',
        'test_character_reopen_guest', 'test_task_gate_integration', 'test_ground_repair'],
    'retained_save_task_storage_profile_and_memory_guards_verified': list(RETAINED_TEST_MODULES),
    'exact_payload_boundaries_and_actual_archive_extraction_verified': ['test_levelup_ui_repair_package',
        'test_client_ui_repair_assets', 'test_classify_interactive_change', 'test_classify_storage_cleanup_change'],
    'source_bound_dbserver_levelup_repair_verified': ['test_levelup_ui_repair_dbserver',
        'test_levelup_ui_repair_contract', 'test_levelup_ui_repair_package', 'test_startup_bundle_dbserver'],
    'interactive_dependency_preload_launch_verified': ['test_client_preload_launch',
        'test_client_startup_followup_native', 'test_client_startup_followup_contract'],
}



def source_paths(donor):
    names = set(donor['qualification']['source_files']) | set(derivative.SOURCE_FILES)
    names.update(Path(importlib.import_module(name).__file__).relative_to(ROOT).as_posix() for name in TEST_MODULES)
    names.update(derivative.validate_retained_native_sources(donor))
    native = derivative.native_builder()
    names.update(native.SOURCE_FILES)
    names.update('upstream/ouroboros/'+name
        for name in native.expected_receipt()['source_sha256'])
    # Both baseline proofs and all new material/costume/FX source witnesses
    # must be pinned, including inputs selected dynamically by the producers.
    for filename in ('client-visual-manifest.json', 'client-appearance-manifest.json', 'client-ui-repair-manifest.json'):
        value = derivative.read_json(ROOT/'assets'/filename)
        names.update(value['source_files'])
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
        derivative.require(result.wasSuccessful() and not result.skipped,
            name+' failed or skipped required checks:\n'+output)
        print(name+': '+str(result.testsRun)+' passed; no skips', flush=True)
        results[name] = {'tests_run': result.testsRun, 'status': 'passed', 'skipped': 0}
    return results


def qualification_checks(results):
    registered = set(TEST_MODULES)
    derivative.require(len(registered) == len(TEST_MODULES) and set(results) == registered,
        'Client qualification requires the complete unique registered suite inventory')
    derivative.require(set(CHECK_SUITES) == set(derivative.CHECKS)
        and all(suites and set(suites) <= registered for suites in CHECK_SUITES.values()),
        'Every client qualification check must reference registered required suites')
    return {name: all(results[suite]['status'] == 'passed' and results[suite]['skipped'] == 0
        and results[suite]['tests_run'] > 0 for suite in suites) for name, suites in CHECK_SUITES.items()}


def qualify(args):
    if hasattr(time, 'tzset'): os.environ['TZ'] = 'UTC'; time.tzset()
    base = derivative.builder(); commit = base.source_commit(args.repository_commit)
    donor = derivative.validate_donor(args.donor_apk, args.donor_build_report)
    java = derivative.current_sources(donor)
    visual = derivative.validate_visual_package(args.visual_directory)
    conservation = derivative.validate_visual_superset(donor, visual)
    streams = derivative.verify_visual_streams(args.donor_apk, args.visual_directory, donor)
    native = derivative.validate_native(args.dbserver_directory, commit, donor)
    derivative.verify_retained_world_geometry(args.donor_apk, visual)
    pins = {name: base.file_pin(ROOT/name) for name in source_paths(donor)}
    results = regressions()
    save = importlib.import_module('test_startup_bundle_save')
    derivative.require(save.REQUIRE_POSTGRESQL is True and save.POSTGRES_FIXTURES_RUN ==
        {'cancelled_child_deletion_commits', 'duplicate_insert_23505_rollback', 'delete_insert_replacement_commits'},
        'Formal qualification requires all three real PostgreSQL transaction fixtures')
    repaired_save = importlib.import_module('test_levelup_ui_repair_dbserver')
    derivative.require(repaired_save.REQUIRE_POSTGRESQL is True and repaired_save.POSTGRES_FIXTURES_RUN ==
        repaired_save.REQUIRED_POSTGRES_FIXTURES, 'Formal qualification requires every real PostgreSQL level-up fixture')
    for name, expected in pins.items(): base.checked_file(ROOT/name, expected)
    checks = qualification_checks(results)
    receipt = {'format': 1, 'status': 'passed' if all(checks.values()) else 'failed',
        'scope': derivative.QUALIFICATION_SCOPE, 'repository_commit': commit,
        'retained_runtime_repository_commit': derivative.DONOR_COMMIT,
        'retained_setup_memory_repository_commit': derivative.RETAINED_SETUP_MEMORY_COMMIT,
        'retained_native_repository_commit': derivative.RETAINED_NATIVE_COMMIT,
        'donor_apk_sha256': derivative.DONOR_APK['sha256'], 'donor': derivative.donor_link(),
        'source_files': pins, 'test_suites': results, 'check_suites': CHECK_SUITES,
        'tests_run': sum(item['tests_run'] for item in results.values()), 'checks': checks,
        'physical_gameplay_validated': False, 'physical_client_timing_validated': False,
        'physical_visual_assets_validated': False, 'native_runtime_booted': False,
        'long_prior_gameplay_milestones_repeated': False, 'runtime_refresh_required': True,
        'previous_runtime_generation_retained': True, 'asset_reimport_required': False,
        'setup_memory_guards_preserved': True, 'java_or_dex_recompiled': False,
        'native_dbserver_recompiled': True, 'native_client_recompiled': False, 'native_mapserver_recompiled': False,
        'native_source_commit': donor['native_source_commit'], 'native_source_provenance': donor['native_source_provenance'],
        'native_dbserver_compiled_in_current_run': True, 'native_dbserver_package_reused': False,
        'native_levelup_ui_repair': native,
        'native_client_startup_followup': donor['native_client_startup_followup'],
        'visual_package': visual, 'visual_superset': conservation, 'visual_original_streams': streams,
        'retained_world_lod_geometry_verified': True, 'retained_server_cache_and_save_fix_verified': True,
        'postgresql_emission_fixture_verified': True, 'postgresql_emission_fixtures': sorted(save.POSTGRES_FIXTURES_RUN),
        'postgresql_levelup_fixtures': sorted(repaired_save.POSTGRES_FIXTURES_RUN),
        'retained_baseline_payloads_verified': 71, 'authored_java_sources_verified': len(java),
        'changed_java_sources': [], 'retained_java_sources': 19,
        'server_payload_extraction_preflight': donor['server_payload_extraction_preflight'],
        'performance_claim_scope': 'Host and real PostgreSQL scenarios qualify per-row physical child witnesses, '
            'commit-before-ACK conservation, finite original UI texture dependencies and activation of the '
            'already qualified Game metadata preload on the saved-character route. Physical level-up, '
            'UI appearance and timing remain pending.',
        'preserved_state': 'The exact public 0.13.11 Game, twenty client DLLs, MapServer, server archives/caches, '
            '9490 decoded and stored visual streams, nineteen Java sources, DEX/resources, imported assets, '
            'private profile and reward/save rules retain identity. Only the new owned DbServer reader layer, '
            'bounded UI texture append, typed guest bindings and interactive environment change.' }
    derivative.validate_qualification(receipt, commit)
    derivative.require(not args.output.exists() and not args.output.is_symlink(), 'Fresh client qualification output required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2)+'\n')
    print('Qualified level-up/UI candidate:', receipt['tests_run'], 'host checks; physical timing and visuals pending')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository-commit', required=True)
    for name in ('donor-apk', 'donor-build-report', 'visual-directory', 'dbserver-directory', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    qualify(parser.parse_args())


if __name__ == '__main__': main()
