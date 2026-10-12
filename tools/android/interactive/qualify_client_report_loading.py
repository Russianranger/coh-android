#!/usr/bin/env python3
"""Qualify recoverable reports and bounded warm preparation from exact public .32."""
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
import build_client_report_loading_apk as derivative
import qualify_client_map_startup as previous
import qualify_startup_schedule as closure

RETAINED_TEST_MODULES = previous.TEST_MODULES
NEW_TEST_MODULES = ('test_client_report_loading_package', 'test_client_report_controls_java',
    'test_collision_input_snapshot', 'test_shared_collision_input_proof', 'test_map_startup_observation',
    'test_qualify_map_startup_prerequisites')
TEST_MODULES = RETAINED_TEST_MODULES + NEW_TEST_MODULES
# These suites belong to immutable historical package/native producers. Their
# successful .32 results are carried from the exact authenticated donor receipt;
# no historical build, fixture or publication is rerun or relabelled as current.
# Current .33 byte-retention and actual packaged preparation are independent.
RETAINED_CONTRACT_MODULES = frozenset({
    'test_client_receipt_repair_package', 'test_client_animation_repair_package',
    'test_client_profile_recovery_package', 'test_client_map_startup_package',
    'test_animation_runtime_compatibility', 'test_map_startup_native_contract',
    'test_map_startup_animation_certificate', 'test_kings_row_runtime_dependencies',
    'test_map_startup_cache_reuse'})
# These two historical binary-fixture suites exercise unchanged methods within
# a guest module whose other preparation/observation methods now change. Pin
# the actual retained source blocks as well as their original suite evidence.
RETAINED_GUEST_BLOCKS = {
    'test_kings_row_runtime_dependencies': (
        'LocalCharacterServer.copy_kings_native_dependencies', 'install_manual_atlas_dbserver',
        'manual_atlas_wait_contract', 'digest_json', 'STARTUP_BUNDLE_ROLE', 'LEVELUP_UI_REPAIR_ROLE', 'require'),
    'test_map_startup_cache_reuse': ('LocalCharacterServer.data_cache_native_package', 'require'),
}
CHECK_SUITES = {
    'retained_regressions_and_postgresql_verified': list(RETAINED_TEST_MODULES),
    'actual_runtime_asset_installers_verified': ['test_client_report_loading_package', 'test_runtime_asset_preflight'],
    'full_startup_orchestration_verified': ['test_full_startup_preflight', 'test_client_report_loading_package',
        'test_shared_collision_input_proof'],
    'report_finalization_and_recovery_verified': ['test_client_report_lifecycle_java',
        'test_client_report_recovery_java', 'test_client_report_controls_java', 'test_profile_failure_presentation'],
    'warm_preparation_reuse_verified': ['test_collision_input_snapshot', 'test_shared_collision_input_proof',
        'test_map_startup_observation', 'test_atlas_beacon_package', 'test_beacon_runtime_profiles',
        'test_map_startup_cache_reuse', 'test_qualify_map_startup_prerequisites'],
    'exact_032_native_graphics_and_assets_verified': ['test_client_report_loading_package',
        'test_client_render_queue_contract', 'test_client_gpu_profile', 'test_client_gpu_repair_package',
        'test_external_assets', 'test_asset_pack_import'],
}


def validate_suite_inventory():
    derivative.require(RETAINED_TEST_MODULES == previous.TEST_MODULES
        and len(RETAINED_TEST_MODULES) == 190 and TEST_MODULES[:190] == RETAINED_TEST_MODULES
        and len(set(TEST_MODULES)) == len(TEST_MODULES)
        and RETAINED_CONTRACT_MODULES <= set(RETAINED_TEST_MODULES)
        and set(CHECK_SUITES) == set(derivative.CHECKS)
        and all(suites and set(suites) <= set(TEST_MODULES) for suites in CHECK_SUITES.values()),
        'Every retained .32 suite and all current report/preparation/retention gates are required')


def source_paths(donor):
    names = set(donor['qualification']['source_files']) | set(derivative.SOURCE_FILES)
    names.update(Path(importlib.import_module(name).__file__).relative_to(ROOT).as_posix() for name in TEST_MODULES)
    names.update(path.relative_to(ROOT).as_posix() for path in (ROOT/'android/guest').glob('*.py'))
    return sorted(closure.source_closure(names))


def source_block(raw, qualified_name):
    text = raw.decode('utf-8'); nodes = ast.parse(text).body
    for label in qualified_name.split('.'):
        matches = [node for node in nodes if (
            isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == label)
            or (isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
                and target.id == label for assignment in node.targets for target in ast.walk(assignment)))]
        derivative.require(len(matches) == 1, 'Exactly one retained source block required: '+qualified_name)
        node = matches[0]
        nodes = node.body if isinstance(node, ast.ClassDef) else []
    return ast.get_source_segment(text, node).encode()


def local_dependency_blocks(raw, roots):
    """Close unchanged helper behavior over every referenced module binding.

    The selected class method bodies are pinned directly. Their global helper,
    constant, alias and import dependencies are recursively pinned as complete
    original source statements. External guest modules remain full-byte donor
    pins in the builder's current_sources admission; no producer is rebuilt.
    """
    text = raw.decode('utf-8'); tree = ast.parse(text); bindings = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names = [node.name]
        elif isinstance(node, ast.Assign):
            names = [item.id for target in node.targets for item in ast.walk(target)
                     if isinstance(item, ast.Name) and isinstance(item.ctx, ast.Store)]
        elif isinstance(node, ast.Import):
            names = [item.asname or item.name.split('.')[0] for item in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [item.asname or item.name for item in node.names]
        else:
            continue
        for name in names:
            derivative.require(name not in bindings, 'Ambiguous retained module dependency: '+name)
            bindings[name] = node
    pending = list(roots); found = {}
    while pending:
        name = pending.pop()
        if name in found:
            continue
        if '.' in name:
            raw_block = source_block(raw, name)
            node = ast.parse(raw_block.decode()).body[0]
        else:
            derivative.require(name in bindings, 'Missing retained module dependency: '+name)
            node = bindings[name]; raw_block = ast.get_source_segment(text, node).encode()
        found[name] = raw_block
        local = {item.id for item in ast.walk(node)
                 if isinstance(item, ast.Name) and isinstance(item.ctx, ast.Store)}
        local.update(item.arg for item in ast.walk(node) if isinstance(item, ast.arg))
        for item in ast.walk(node):
            if isinstance(item, (ast.Import, ast.ImportFrom)):
                local.update(alias.asname or (alias.name.split('.')[0] if isinstance(item, ast.Import)
                             else alias.name) for alias in item.names)
        # Imports are complete dependency statements themselves. For functions
        # and values, bind every free name that resolves in this module.
        references = {item.id for item in ast.walk(node)
                      if isinstance(item, ast.Name) and isinstance(item.ctx, ast.Load)} - local
        pending.extend(sorted((references & set(bindings)) - set(found)))
    return found


def retained_guest_block_pins(name, donor):
    names = RETAINED_GUEST_BLOCKS.get(name, ())
    if not names:
        return {}
    with zipfile.ZipFile(donor['_apk_path']) as archive:
        original = archive.read('assets/runtime/local_character_server.py')
    current = (ROOT/'android/guest/local_character_server.py').read_bytes()
    old = local_dependency_blocks(original, names)
    new = local_dependency_blocks(current, names)
    derivative.require(set(old) == set(new), 'Historical binary-fixture dependency closure changed')
    for label in old:
        derivative.require(old[label] == new[label], 'Historical binary-fixture behavior changed: '+label)
    return {label: derivative.pin(old[label]) for label in sorted(old)}


def retained_contract_result(name, donor):
    original = donor['qualification']['test_suites'][name]
    derivative.require(original.get('status') == 'passed' and original.get('skipped') == 0
        and type(original.get('tests_run')) is int and original['tests_run'] > 0,
        'Authenticated .32 historical suite result is invalid: '+name)
    source = Path(importlib.import_module(name).__file__).relative_to(ROOT).as_posix()
    derivative.builder().checked_file(ROOT/source, donor['qualification']['source_files'][source])
    return {'tests_run': original['tests_run'], 'status': 'passed', 'skipped': 0,
        'source_scope': 'accepted_032_retained_contract', 'source_repository_commit': derivative.DONOR_COMMIT,
        'tests_executed_in_current_run': False, 'donor_suite_result': original,
        'donor_build_report': derivative.DONOR_BUILD,
        'unchanged_guest_source_blocks': retained_guest_block_pins(name, donor)}


def current_suite_test_count(name):
    derivative.require(name in TEST_MODULES and name not in RETAINED_CONTRACT_MODULES,
                       'Only pinned current qualification suites may supply current test counts')
    suite = unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(name))
    count = suite.countTestCases()
    derivative.require(type(count) is int and count > 0, 'Current suite has no loader scenarios: '+name)
    return count


def validate_current_suite_result(name, row):
    derivative.require(row.get('source_scope') == 'current_033_candidate_sources'
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
    This donor is a test input, never the shipping .33 runtime donor.
    """
    apk = Path(apk)
    derivative.builder().checked_file(apk, derivative.previous.DONOR_APK)
    apk = apk.resolve()
    os.environ['COH_MAP_STARTUP_TEST_DONOR_APK'] = str(apk)
    return {'role': 'existing_public_031_native_parser_fixture_only',
        'apk': derivative.previous.DONOR_APK, 'current_suites': ['test_full_startup_preflight'],
        'shipping_runtime_donor_changed': False, 'native_binary_rebuilt': False}


def regressions(donor):
    validate_suite_inventory(); results = {}
    early = ('test_full_startup_preflight', 'test_runtime_asset_preflight')
    execution = tuple(name for name in NEW_TEST_MODULES if name != 'test_client_report_loading_package') + \
        early + tuple(name for name in RETAINED_TEST_MODULES if name not in RETAINED_CONTRACT_MODULES
                      and name not in early) + \
        tuple(sorted(RETAINED_CONTRACT_MODULES)) + ('test_client_report_loading_package',)
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
                'source_scope': 'current_033_candidate_sources', 'tests_executed_in_current_run': True}
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
    os.environ['COH_REPORT_LOADING_TEST_DONOR_APK'] = str(args.donor_apk.resolve())
    os.environ['COH_REPORT_LOADING_TEST_DONOR_REPORT'] = str(args.donor_build_report.resolve())
    os.environ['COH_REPORT_LOADING_TEST_SOURCE_COMMIT'] = commit
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
        'source_files': pins, 'test_suites': results, 'check_suites': CHECK_SUITES,
        'checks': checks, 'tests_run': sum(value['tests_run'] for value in results.values()),
        'current_tests_run': sum(value['tests_run'] for value in results.values() if value['tests_executed_in_current_run']),
        'inherited_tests_retained': sum(value['tests_run'] for value in results.values() if not value['tests_executed_in_current_run']),
        'current_suites_run': sum(value['tests_executed_in_current_run'] for value in results.values()),
        'inherited_suites_retained': sum(not value['tests_executed_in_current_run'] for value in results.values()),
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
        'claim_scope': 'Host qualification executes current report/lifecycle/UI and preparation reuse repairs, '
            'all applicable retained regressions, real PostgreSQL fixtures and full actual packaged fresh-create/reopen '
            'and Atlas/Kings cold/reuse preparation. Nine immutable historical package/native suites retain their '
            'authenticated .32 results with explicit donor attribution and are not rerun or claimed as current execution. '
            'For the two native dependency/data-generation fixture suites, the current guest methods and their '
            'local contract helpers must remain byte-identical to the actual donor APK source blocks. '
            'Independent actual .33 packaging verifies every retained native/GPU/Wine/FEX/asset byte and receipt order. '
            'No native binary or asset pack is rebuilt. Host tests do not establish physical report export, '
            'MapServer startup gains, gameplay, save/reopen or round-trip monorail validation.',


    }
    derivative.validate_qualification(receipt, commit, donor)
    derivative.require(not args.output.exists() and not args.output.is_symlink(),
                       'Fresh qualification output required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded_receipt(receipt))
    print('Qualified report recovery and warm preparation:', receipt['current_tests_run'],
          'current host scenarios;', receipt['inherited_tests_retained'],
          'unchanged donor scenarios retained; physical Thor retest pending', flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository-commit', required=True)
    for name in ('donor-apk', 'donor-build-report', 'native-contract-donor-apk', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--asset-directory', type=Path, default=ROOT/'out/map-startup-assets')
    qualify(parser.parse_args())


if __name__ == '__main__': main()
