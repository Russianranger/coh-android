#!/usr/bin/env python3
"""Qualify the .30 animation/native bridge and actual packaged asset installers."""
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
import build_client_animation_repair_apk as derivative
import qualify_client_receipt_repair as previous
import qualify_startup_schedule as closure

RETAINED_TEST_MODULES = previous.TEST_MODULES
NEW_TEST_MODULES = ('test_animation_runtime_compatibility', 'test_runtime_asset_preflight',
                    'test_client_animation_repair_package')
TEST_MODULES = RETAINED_TEST_MODULES + NEW_TEST_MODULES
CHECK_SUITES = {
    'retained_regressions_and_postgresql_verified': list(RETAINED_TEST_MODULES),
    'actual_runtime_asset_installers_verified': list(NEW_TEST_MODULES),
    'exact_029_native_graphics_and_assets_verified': [
        'test_client_animation_repair_package', 'test_animation_runtime_compatibility',
        'test_client_receipt_repair_package', 'test_game_receipt_order',
        'test_client_render_queue_contract', 'test_client_gpu_profile',
        'test_client_gpu_repair_package', 'test_external_assets', 'test_asset_pack_import'],
}


def validate_suite_inventory():
    derivative.require(RETAINED_TEST_MODULES == previous.TEST_MODULES
        and len(RETAINED_TEST_MODULES) == 146
        and TEST_MODULES[:146] == RETAINED_TEST_MODULES and len(TEST_MODULES) == 149
        and len(set(TEST_MODULES)) == len(TEST_MODULES)
        and set(CHECK_SUITES) == set(derivative.CHECKS)
        and all(suites and set(suites) <= set(TEST_MODULES)
                for suites in CHECK_SUITES.values()),
        'Every retained .29 suite and all three animation/runtime asset repair suites are required')


def source_paths(donor):
    import qualify_runtime_asset_preflight as asset_preflight
    names = set(donor['qualification']['source_files']) | set(derivative.SOURCE_FILES)
    names.update(asset_preflight.SOURCE_FILES)
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


def regressions():
    validate_suite_inventory()
    results = {}
    for name in TEST_MODULES:
        suite = unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(name))
        derivative.require(suite.countTestCases() > 0, name + ' has no scenarios')
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
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
    os.environ['COH_RECEIPT_REPAIR_TEST_DONOR_APK'] = str(args.donor_apk.resolve())
    os.environ['COH_RECEIPT_REPAIR_TEST_DONOR_REPORT'] = str(args.donor_build_report.resolve())
    os.environ['COH_ANIMATION_TEST_DONOR_APK'] = str(args.donor_apk.resolve())
    os.environ['COH_ANIMATION_TEST_DONOR_REPORT'] = str(args.donor_build_report.resolve())
    os.environ['COH_ANIMATION_REPAIR_ASSET_CACHE'] = str(args.asset_directory.resolve())
    java = derivative.current_sources(donor)
    pins = {name: base.file_pin(ROOT/name) for name in source_paths(donor)}
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
    results = regressions()
    save = importlib.import_module('test_startup_bundle_save')
    derivative.require(save.REQUIRE_POSTGRESQL is True and save.POSTGRES_FIXTURES_RUN == {
        'cancelled_child_deletion_commits', 'duplicate_insert_23505_rollback',
        'delete_insert_replacement_commits'}, 'All three real PostgreSQL emission fixtures required')
    levelup = importlib.import_module('test_levelup_ui_repair_dbserver')
    derivative.require(levelup.REQUIRE_POSTGRESQL is True
        and levelup.POSTGRES_FIXTURES_RUN == levelup.REQUIRED_POSTGRES_FIXTURES
        and len(levelup.POSTGRES_FIXTURES_RUN) == 4,
        'All four real PostgreSQL level-up fixtures required')
    for name, expected in pins.items():
        base.checked_file(ROOT/name, expected)
    checks = {name: all(results[suite]['status'] == 'passed'
        and results[suite]['skipped'] == 0 and results[suite]['tests_run'] > 0
        for suite in suites) for name, suites in CHECK_SUITES.items()}
    receipt = {
        'format': 1, 'status': 'passed' if all(checks.values()) else 'failed',
        'scope': derivative.QUALIFICATION_SCOPE, 'repository_commit': commit,
        'runtime_repository_commit': commit, 'donor': derivative.donor_link(),
        'source_files': pins, 'test_suites': results, 'check_suites': CHECK_SUITES,
        'checks': checks, 'tests_run': sum(value['tests_run'] for value in results.values()),
        'postgresql_emission_fixtures': sorted(save.POSTGRES_FIXTURES_RUN),
        'postgresql_levelup_fixtures': sorted(levelup.POSTGRES_FIXTURES_RUN),
        'java_sources': java, 'retained_dex': donor['retained_dex'],
        'external_asset_pack': donor['external_asset_pack'],
        'native_build_provenance': donor['native_build_provenance'],
        'package_preflight': preflight,
        **dict.fromkeys(derivative.FALSE_FLAGS, False),
        **dict.fromkeys(derivative.TRUE_FLAGS, True),
        'claim_scope': 'Host qualification executes actual candidate guest asset installers '
            'against the authenticated .29 donor native binaries and complete retained '
            'animation/cache/beacon assets, including Atlas and Kings Row cold/reuse cases. '
            'The exact qualified monorail binary gains an explicit animation compatibility '
            'bridge; guest save acceptance, native binaries, DEX/resources, graphics and '
            'Assets 1.0.0 remain exact. No native runtime or physical Thor boot is claimed. '
            'Physical creation, entry, save/reopen and Kings Row travel require device evidence.',
    }
    derivative.validate_qualification(receipt, commit, donor)
    derivative.require(not args.output.exists() and not args.output.is_symlink(),
                       'Fresh qualification output required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print('Qualified packaged animation/native compatibility:', receipt['tests_run'],
          'host scenarios; physical Thor retest pending', flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository-commit', required=True)
    for name in ('donor-apk', 'donor-build-report', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--asset-directory', type=Path, default=ROOT/'out/animation-repair-assets')
    qualify(parser.parse_args())


if __name__ == '__main__':
    main()
