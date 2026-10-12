#!/usr/bin/env python3
"""Qualify certified startup, repaired acceptance and complete packaged preparation."""
import argparse
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

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'tools/android'),
    str(ROOT/'tools/android/dbserver'), str(ROOT/'tools'), str(ROOT/'android/guest'),
    str(ROOT/'database/postgresql/tests'), str(ROOT/'tools/android/game'), str(ROOT/'tools/android/atlasgame')]
import build_client_map_startup_apk as derivative
import qualify_client_profile_recovery as previous
import qualify_startup_schedule as closure

RETAINED_TEST_MODULES = previous.TEST_MODULES
NEW_TEST_MODULES = ('test_client_map_startup_package', 'test_kings_preparation_budgets',
    'test_device_cleanup_lineage', 'test_complete_asset_stage_acceptance',
    'test_server_fx_catalog', 'test_map_startup_animation_certificate',
    'test_map_startup_namespace_certificate', 'test_server_fx_catalog_native_proof',
    'test_prepare_server_fx_catalog_observer_source', 'test_completed_guest_report_java',
    'test_map_startup_monorail_budget', 'test_map_startup_native_contract', 'test_map_startup_cache_reuse')
TEST_MODULES = RETAINED_TEST_MODULES + NEW_TEST_MODULES
HISTORICAL_PACKAGE_MODULES = frozenset({'test_client_receipt_repair_package',
    'test_client_animation_repair_package', 'test_client_profile_recovery_package'})
CHECK_SUITES = {
    'retained_regressions_and_postgresql_verified': list(RETAINED_TEST_MODULES),
    'actual_runtime_asset_installers_verified': ['test_client_map_startup_package', 'test_runtime_asset_preflight'],
    'full_startup_orchestration_verified': ['test_full_startup_preflight', 'test_client_map_startup_package',
        'test_map_startup_cache_reuse'],
    'kings_preparation_budgets_and_cleanup_verified': ['test_kings_preparation_budgets',
        'test_device_cleanup_lineage', 'test_complete_asset_stage_acceptance',
        'test_completed_guest_report_java'],
    'native_animation_and_fx_component_fixtures_verified': ['test_server_fx_catalog',
        'test_map_startup_animation_certificate', 'test_map_startup_namespace_certificate',
        'test_client_map_startup_package', 'test_server_fx_catalog_native_proof',
        'test_prepare_server_fx_catalog_observer_source', 'test_map_startup_monorail_budget',
        'test_map_startup_native_contract'],
    'exact_031_game_graphics_and_assets_verified': ['test_client_map_startup_package',
        'test_client_render_queue_contract', 'test_client_gpu_profile', 'test_client_gpu_repair_package',
        'test_external_assets', 'test_asset_pack_import'],
}


def validate_suite_inventory():
    derivative.require(RETAINED_TEST_MODULES == previous.TEST_MODULES
        and len(RETAINED_TEST_MODULES) == 177
        and TEST_MODULES[:177] == RETAINED_TEST_MODULES
        and len(set(TEST_MODULES)) == len(TEST_MODULES)
        and HISTORICAL_PACKAGE_MODULES <= set(RETAINED_TEST_MODULES)
        and set(CHECK_SUITES) == set(derivative.CHECKS)
        and all(suites and set(suites) <= set(TEST_MODULES) for suites in CHECK_SUITES.values()),
        'Every retained .31 suite and all current startup/preparation/native/asset gates are required')


def source_paths(donor):
    import qualify_runtime_asset_preflight as asset_preflight
    names = set(donor['qualification']['source_files']) | set(derivative.SOURCE_FILES)
    names.update(asset_preflight.SOURCE_FILES)
    names.update(path.relative_to(ROOT).as_posix() for path in (ROOT/'database/map-startup').rglob('*') if path.is_file())
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
    key = 'COH_ANIMATION_TEST_DONOR_APK'
    prior = os.environ.get(key)
    if name == 'test_animation_runtime_compatibility':
        os.environ[key] = str(historical_donor_apk.resolve())
    try:
        yield
    finally:
        if prior is None: os.environ.pop(key, None)
        else: os.environ[key] = prior


def validate_historical_source(directory, donor):
    directory = Path(directory).resolve()
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=directory, text=True).strip()
    derivative.require(head == derivative.DONOR_COMMIT, 'Exact frozen .31 Git source checkout required')
    subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--'], cwd=directory, check=True)
    for name, expected in donor['qualification']['source_files'].items():
        derivative.builder().checked_file(directory/name, expected)
    return directory


def stage_historical_source(directory, donor):
    """Use an actual Git worktree containing exactly the authenticated sources.

    The complete .31 checkout is 2.30 GB, while its 9,901 qualified source
    files total 126.99 MB. Sparse checkout preserves HEAD/index attribution
    without duplicating immutable game data already supplied by the asset
    fixture. Every historical source pin is checked before and after tests.
    """
    directory = Path(directory).resolve()
    derivative.require(donor.get('repository_commit') == derivative.DONOR_COMMIT,
                       'Historical source inventory must belong to public .31')
    if directory.exists():
        return validate_historical_source(directory, donor)
    names = set(donor['qualification']['source_files']) | {'.gitattributes'}
    derivative.require(all(type(name) is str and not Path(name).is_absolute()
        and '..' not in Path(name).parts and '\\' not in name for name in names),
        'Unsafe historical source inventory')
    subprocess.run(['git', 'worktree', 'add', '--detach', '--no-checkout', str(directory),
                    derivative.DONOR_COMMIT], cwd=ROOT, check=True)
    subprocess.run(['git', '-C', str(directory), 'sparse-checkout', 'init', '--no-cone'], check=True)
    def literal(name):
        for old, new in (('*', '\\*'), ('?', '\\?'), ('[', '\\['), (']', '\\]')):
            name = name.replace(old, new)
        return '/'+name
    subprocess.run(['git', '-C', str(directory), 'sparse-checkout', 'set', '--no-cone', '--stdin'],
        input='\n'.join(literal(name) for name in sorted(names))+'\n', text=True, check=True)
    # A fresh --no-checkout worktree has no populated index. Materialize it only
    # after the complete finite sparse inventory is installed.
    subprocess.run(['git', '-C', str(directory), 'read-tree', '-mu', 'HEAD'], check=True)
    return validate_historical_source(directory, donor)


def historical_package_suite(name, directory):
    """Keep earlier package source/payload contracts intact in a fresh process."""
    script = r'''import contextlib,importlib,io,json,sys,unittest
from pathlib import Path
root=Path(sys.argv[1]); name=sys.argv[2]
sys.path[:0]=[str(root/'tools/android/interactive'),str(root/'tools/android'),str(root/'tools'),
 str(root/'android/guest'),str(root/'tools/android/dbserver'),str(root/'database/postgresql/tests'),
 str(root/'tools/android/game')]
stream=io.StringIO()
with contextlib.redirect_stdout(stream),contextlib.redirect_stderr(stream):
 suite=unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(name))
 result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
output=stream.getvalue()
assert len(output.encode())<=262144,'Historical suite output exceeds bound'
assert suite.countTestCases()>0 and result.wasSuccessful() and not result.skipped,output
print('COH_HISTORICAL_RESULT_V1='+json.dumps({'tests_run':result.testsRun,'status':'passed','skipped':0}))
'''
    completed = subprocess.run([sys.executable, '-c', script, str(directory), name], cwd=directory,
        capture_output=True, text=True, timeout=1800, check=False)
    derivative.require(len(completed.stdout.encode()) <= 262144
        and len(completed.stderr.encode()) <= 262144 and completed.returncode == 0,
        'Frozen historical package suite failed: '+name+'\n'+completed.stdout+completed.stderr)
    rows = [line[len('COH_HISTORICAL_RESULT_V1='):] for line in completed.stdout.splitlines()
            if line.startswith('COH_HISTORICAL_RESULT_V1=')]
    derivative.require(len(rows) == 1, 'Exactly one historical suite result required')
    record = json.loads(rows[0])
    derivative.require(record.get('status') == 'passed' and record.get('skipped') == 0
        and type(record.get('tests_run')) is int and record['tests_run'] > 0,
        'Historical package scenarios did not pass without skips')
    return dict(record, source_scope='frozen_031_historical_package_contract',
                source_repository_commit=derivative.DONOR_COMMIT)


def current_suite(name, payloads):
    imported = importlib.import_module(name)
    if name == 'test_map_startup_animation_certificate':
        # The five genuine Windows fixtures ran in the authenticated native
        # producer. This Linux gate reruns all seven full-byte/source tests,
        # requiring zero skips rather than presenting skipped Windows tests as
        # qualification. Raw Windows evidence is separately mandatory.
        imported.PIGG = payloads/'server-animations.pigg'
        imported.MANIFEST = payloads/'server-animation-manifest.json'
        result = unittest.TestSuite()
        for cls in (imported.SourceTests, imported.FullCertificateTests):
            result.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
        return result
    return unittest.defaultTestLoader.loadTestsFromModule(imported)


def regressions(historical_donor_apk, historical_source, payloads):
    validate_suite_inventory()
    heavy = tuple(name for name in TEST_MODULES if name in HISTORICAL_PACKAGE_MODULES) + ('test_client_map_startup_package',)
    execution = tuple(name for name in NEW_TEST_MODULES if name not in heavy) + \
        tuple(name for name in RETAINED_TEST_MODULES if name not in heavy) + heavy
    derivative.require(len(execution) == len(TEST_MODULES)
        and set(execution) == set(TEST_MODULES), 'Every qualification suite must execute exactly once')
    results = {}
    for name in execution:
        if name in HISTORICAL_PACKAGE_MODULES:
            row = historical_package_suite(name, historical_source)
        else:
            captured = io.StringIO()
            with suite_donor_environment(name, historical_donor_apk), \
                    contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
                suite = current_suite(name, payloads)
                derivative.require(suite.countTestCases() > 0, name+' has no scenarios')
                result = unittest.TextTestRunner(stream=captured, verbosity=2).run(suite)
            output = captured.getvalue()
            derivative.require(len(output.encode()) <= 262144, 'Unbounded qualification output: '+name)
            derivative.require(result.wasSuccessful() and not result.skipped, name+' failed or skipped:\n'+output)
            row = {'tests_run': result.testsRun, 'status': 'passed', 'skipped': 0,
                   'source_scope': 'current_032_candidate_sources'}
        print(name+': '+str(row['tests_run'])+' passed; no skips; '+row['source_scope'], flush=True)
        results[name] = row
    return results


def encoded_receipt(value):
    return json.dumps(value, indent=2, allow_nan=False)+'\n'


def qualify(args):
    if hasattr(time, 'tzset'):
        os.environ['TZ'] = 'UTC'
        time.tzset()
    validate_suite_inventory()
    base = derivative.builder()
    commit = base.source_commit(args.repository_commit)
    donor = derivative.validate_donor(args.donor_apk, args.donor_build_report)
    base.checked_file(args.historical_donor_apk, derivative.previous.previous.DONOR_APK)
    base.checked_file(args.profile_donor_apk, derivative.previous.DONOR_APK)
    base.checked_file(args.profile_donor_build_report, derivative.previous.DONOR_BUILD)
    historical_source = validate_historical_source(args.historical_source, donor)
    os.environ['COH_RECEIPT_REPAIR_TEST_DONOR_APK'] = str(args.historical_donor_apk.resolve())
    os.environ['COH_PROFILE_RECOVERY_TEST_DONOR_APK'] = str(args.profile_donor_apk.resolve())
    os.environ['COH_PROFILE_RECOVERY_TEST_DONOR_REPORT'] = str(args.profile_donor_build_report.resolve())
    os.environ['COH_ANIMATION_TEST_DONOR_APK'] = str(args.profile_donor_apk.resolve())
    os.environ['COH_ANIMATION_TEST_DONOR_REPORT'] = str(args.profile_donor_build_report.resolve())
    os.environ['COH_MAP_STARTUP_ASSET_CACHE'] = str(args.asset_directory.resolve())
    os.environ['COH_PROFILE_RECOVERY_ASSET_CACHE'] = str(args.asset_directory.resolve())
    os.environ['COH_MAP_STARTUP_TEST_DONOR_APK'] = str(args.donor_apk.resolve())
    os.environ['COH_MAP_STARTUP_TEST_DONOR_REPORT'] = str(args.donor_build_report.resolve())
    os.environ['COH_MAP_STARTUP_TEST_INPUTS'] = str(args.map_startup_inputs.resolve())
    os.environ['COH_MAP_STARTUP_TEST_SOURCE_COMMIT'] = commit
    import qualify_runtime_asset_preflight as assets
    import qualify_full_startup_preflight as full_assets
    payloads = assets.ensure_assets(args.asset_directory)
    full_assets.extra_inputs(payloads)
    os.environ['COH_FX_TEST_CLIENT_CACHES'] = str(payloads/'client-caches.zip')
    os.environ['COH_MAP_STARTUP_TEST_ANIMATIONS'] = str(payloads/'server-animations.pigg')
    os.environ['COH_MAP_STARTUP_TEST_ANIMATION_MANIFEST'] = str(payloads/'server-animation-manifest.json')
    os.environ['COH_ANIMATION_REPAIR_ASSET_CACHE'] = str(args.asset_directory.resolve())
    java = derivative.current_sources(donor)
    pins = {name: base.file_pin(ROOT/name) for name in source_paths(donor)}
    # Fail small regression, SQL and donor-wiring gates before repeating
    # the complete preparation. The package suite and final preparation both
    # remain mandatory and are independently admitted below.
    results = regressions(args.historical_donor_apk, historical_source, payloads)
    validate_historical_source(historical_source, donor)
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
            args.donor_apk, donor, Path(temporary)/'donor', commit, args.map_startup_inputs)
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
        'java_sources': java, 'changed_java_sources': derivative.changed_java_sources(donor),
        'donor_dex': donor['recompiled_dex'],
        'external_asset_pack': donor['external_asset_pack'],
        'native_build_provenance': donor['native_build_provenance'],
        'map_startup_component': preflight['map_startup_component'],
        'package_preflight': preflight,
        **dict.fromkeys(derivative.FALSE_FLAGS, False),
        **dict.fromkeys(derivative.TRUE_FLAGS, True),
        'claim_scope': 'Host qualification executes the complete actual packaged fresh-create and saved-reopen '
            'preparation including original reference worktree mirroring and Atlas/Kings cold/reuse installers. '
            'Real PostgreSQL fixtures and compiled Java dispatch tests enforce explicit empty-profile recovery '
            'without relaxing saved-character acceptance. Reviewed Android acceptance/DEX, preparation helpers, the certified MapServer and private server FX change; '
            'native Game/DbServer, renderer, Android resources and Assets 1.0.0 remain exact. Historical package suites execute frozen .31 sources; all other suites execute current candidate sources. Native fixtures have separate authenticated producer ownership. '
            'Native process boot and physical Thor creation, entry, save/reopen and travel still require device evidence.',

    }
    derivative.validate_qualification(receipt, commit, donor, args.map_startup_inputs)
    derivative.require(not args.output.exists() and not args.output.is_symlink(),
                       'Fresh qualification output required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded_receipt(receipt))
    print('Qualified certified MapServer startup and full preparation:', receipt['tests_run'],
          'host scenarios; physical Thor retest pending', flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository-commit', required=True)
    for name in ('donor-apk', 'donor-build-report', 'historical-donor-apk', 'profile-donor-apk',
                 'profile-donor-build-report', 'historical-source', 'map-startup-inputs', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--asset-directory', type=Path, default=ROOT/'out/map-startup-assets')
    qualify(parser.parse_args())


if __name__ == '__main__':
    main()
