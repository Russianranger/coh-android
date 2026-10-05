#!/usr/bin/env python3
"""Qualify the original UI append, native Atlas graph and retained save/runtime guards."""
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
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'tools/android'), str(ROOT/'tools/android/dbserver'),
    str(ROOT/'tools'), str(ROOT/'android/guest')]
import build_ui_beacon_apk as derivative
import qualify_reopen_startup_repair as previous
import qualify_startup_schedule as closure

# Historical publication package tests require obsolete APKs and exclusively test
# their closed release boundaries. Their sources and all shipped bytes are pinned
# below; the new boundary suite covers this candidate's actual extraction instead.
RETAINED_TEST_MODULES = tuple(name for name in previous.TEST_MODULES
    if name not in ('test_levelup_ui_repair_package', 'test_reopen_startup_repair_package'))
TEST_MODULES = RETAINED_TEST_MODULES + ('test_client_ui_sweep_assets', 'test_atlas_beacon_package',
    'test_beacon_runtime_profiles', 'test_generate_atlas_beacons', 'test_prepare_atlas_beacon_generator_source', 'test_ui_beacon_package')
CHECK_SUITES = {
    'missing_only_original_ui_and_all_previous_encoded_streams_verified': ['test_client_ui_sweep_assets',
        'test_client_visual_assets', 'test_client_ui_repair_assets', 'test_texture_header_index'],
    'authentic_atlas_beacon_provenance_and_installation_verified': ['test_atlas_beacon_package',
        'test_beacon_runtime_profiles', 'test_generate_atlas_beacons', 'test_prepare_atlas_beacon_generator_source', 'test_ui_beacon_package'],
    'retained_gameplay_training_postgresql_preload_and_cache_guards_verified': list(RETAINED_TEST_MODULES)+['test_beacon_runtime_profiles'],
    'exact_payload_boundaries_android_shell_and_actual_server_extraction_verified': ['test_ui_beacon_package',
        'test_classify_interactive_change', 'test_classify_storage_cleanup_change'],
}


def source_paths(donor):
    names = set(donor['qualification']['source_files']) | set(derivative.SOURCE_FILES)
    names.update(Path(importlib.import_module(name).__file__).relative_to(ROOT).as_posix() for name in TEST_MODULES)
    visual = json.loads(derivative.visual_builder().manifest_bytes(ROOT/'assets/client-ui-sweep-manifest.json'))
    names.update(visual['source_files'])
    return sorted(closure.source_closure(names))


def regressions():
    results = {}
    for name in TEST_MODULES:
        suite = unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(name))
        derivative.require(suite.countTestCases() > 0, name+' has no scenarios')
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            result = unittest.TextTestRunner(stream=captured, verbosity=2).run(suite)
        output = captured.getvalue()
        derivative.require(len(output.encode()) <= 262144, 'Unbounded qualification output: '+name)
        derivative.require(result.wasSuccessful() and not result.skipped, name+' failed or skipped checks:\n'+output)
        print(name+': '+str(result.testsRun)+' passed; no skips', flush=True)
        results[name] = {'tests_run': result.testsRun, 'status': 'passed', 'skipped': 0}
    return results


def qualification_checks(results):
    registered = set(TEST_MODULES)
    derivative.require(len(registered) == len(TEST_MODULES) and set(results) == registered and set(CHECK_SUITES) == set(derivative.CHECKS)
        and all(suites and set(suites) <= registered for suites in CHECK_SUITES.values()), 'Exact suite inventory required')
    return {name: all(results[suite]['status'] == 'passed' and results[suite]['skipped'] == 0 and results[suite]['tests_run'] > 0
        for suite in suites) for name, suites in CHECK_SUITES.items()}


def qualify(args):
    if hasattr(time, 'tzset'): os.environ['TZ'] = 'UTC'; time.tzset()
    base = derivative.builder(); commit = base.source_commit(args.repository_commit)
    donor = derivative.validate_donor(args.donor_apk, args.donor_build_report); java = derivative.current_sources(donor)
    visual = derivative.validate_visual_package(args.visual_directory); conservation = derivative.validate_visual_superset(donor, visual)
    streams = derivative.verify_visual_streams(args.donor_apk, args.visual_directory, donor)
    beacons = derivative.validate_beacons(args.beacon_directory, commit, donor)
    pins = {name: base.file_pin(ROOT/name) for name in source_paths(donor)}
    results = regressions(); save = importlib.import_module('test_startup_bundle_save')
    derivative.require(save.REQUIRE_POSTGRESQL is True and save.POSTGRES_FIXTURES_RUN ==
        {'cancelled_child_deletion_commits', 'duplicate_insert_23505_rollback', 'delete_insert_replacement_commits'}, 'All retained real PostgreSQL fixtures required')
    repaired = importlib.import_module('test_levelup_ui_repair_dbserver')
    derivative.require(repaired.REQUIRE_POSTGRESQL is True and repaired.POSTGRES_FIXTURES_RUN == repaired.REQUIRED_POSTGRES_FIXTURES,
        'Every real PostgreSQL level-up fixture required')
    for name, pin in pins.items(): base.checked_file(ROOT/name, pin)
    checks = qualification_checks(results)
    receipt = {'format': 1, 'status': 'passed' if all(checks.values()) else 'failed', 'scope': derivative.QUALIFICATION_SCOPE,
        'repository_commit': commit, 'donor': derivative.donor_link(), 'source_files': pins, 'test_suites': results,
        'check_suites': CHECK_SUITES, 'checks': checks, 'tests_run': sum(item['tests_run'] for item in results.values()),
        'retained_java_sources': java, 'visual_package': visual, 'visual_superset': conservation,
        'visual_original_streams': streams, 'atlas_beacons': beacons,
        'postgresql_emission_fixtures': sorted(save.POSTGRES_FIXTURES_RUN), 'postgresql_levelup_fixtures': sorted(repaired.POSTGRES_FIXTURES_RUN),
        **{key: False for key in ('physical_gameplay_validated', 'physical_client_timing_validated', 'physical_visual_assets_validated',
            'native_dbserver_recompiled', 'native_client_recompiled', 'native_mapserver_recompiled', 'java_or_dex_recompiled', 'asset_reimport_required')},
        'performance_claim_scope': 'Exact original UI leaves and native-generated Atlas beacon evidence plus complete retained runtime/save tests. '
            'Host-only generation does not modify the shipped MapServer. New physical UI, pathing and timing validation remain pending.'}
    derivative.validate_qualification(receipt, commit)
    derivative.require(not args.output.exists() and not args.output.is_symlink(), 'Fresh qualification output required')
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(receipt, indent=2)+'\n')
    print('Qualified UI/Atlas candidate:', receipt['tests_run'], 'host scenarios; physical validation pending'); return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository-commit', required=True)
    for name in ('donor-apk', 'donor-build-report', 'visual-directory', 'beacon-directory', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    qualify(parser.parse_args())


if __name__ == '__main__': main()
