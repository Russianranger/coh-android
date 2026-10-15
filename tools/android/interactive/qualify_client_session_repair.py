#!/usr/bin/env python3
"""Qualify the .23 guest session repair while retaining all 105 .22 guards."""
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
import build_client_session_repair_apk as derivative
import qualify_client_render_pipeline as previous
import qualify_startup_schedule as closure

RETAINED_TEST_MODULES = previous.TEST_MODULES
NEW_TEST_MODULES = ('test_client_session_repair_package', 'test_client_session_repair_java')
TEST_MODULES = RETAINED_TEST_MODULES + NEW_TEST_MODULES
CHECK_SUITES = {
    'owned_session_budget_and_instrumentation_isolation_verified': [
        'test_session_budget_guest', 'test_character_reopen_guest',
        'test_client_render_pipeline_guest', 'test_client_session_repair_package',
        'test_client_session_repair_java'],
    'retained_gameplay_postgresql_gpu_cleanup_and_recovery_guards_verified': list(RETAINED_TEST_MODULES),
    'exact_retained_Game_android_shell_and_successful_gpu_bytes_verified': [
        'test_client_session_repair_package', 'test_client_render_pipeline_package',
        'test_client_render_pipeline_contract', 'test_client_gpu_repair_package',
        'test_client_gpu_runtime_package', 'test_client_gpu_profile', 'test_coh_gpu_probe_native'],
}

def validate_suite_inventory():
    derivative.require(RETAINED_TEST_MODULES == previous.TEST_MODULES and len(RETAINED_TEST_MODULES) == 105
        and TEST_MODULES[:105] == RETAINED_TEST_MODULES and len(TEST_MODULES) == 107
        and len(set(TEST_MODULES)) == len(TEST_MODULES) and set(CHECK_SUITES) == set(derivative.CHECKS)
        and all(values and set(values) <= set(TEST_MODULES) for values in CHECK_SUITES.values()),
        'Every retained .22 guard and exact .23 session repair suite is required')


def source_paths(donor):
    names = set(donor['qualification']['source_files']) | set(derivative.SOURCE_FILES) | set(derivative.native_producer().SOURCE_FILES)
    names.update(Path(importlib.import_module(name).__file__).relative_to(ROOT).as_posix() for name in TEST_MODULES)
    return sorted(closure.source_closure(names))


def regressions():
    validate_suite_inventory(); results = {}
    for name in TEST_MODULES:
        suite = unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(name))
        derivative.require(suite.countTestCases() > 0, name+' has no scenarios')
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            result = unittest.TextTestRunner(stream=captured, resultclass=previous.previous.previous.DetailedResult, verbosity=2).run(suite)
        output = captured.getvalue()
        derivative.require(len(output.encode()) <= 262144, 'Unbounded qualification output: '+name)
        derivative.require(result.wasSuccessful() and not result.skipped, name+' failed or skipped:\n'+output)
        print(name+': '+str(result.testsRun)+' passed; no skips', flush=True)
        results[name] = {'tests_run': result.testsRun, 'status': 'passed', 'skipped': 0}
    return results


def qualify(args):
    if hasattr(time, 'tzset'): os.environ['TZ'] = 'UTC'; time.tzset()
    validate_suite_inventory(); base = derivative.builder(); commit = base.source_commit(args.repository_commit)
    donor = derivative.validate_donor(args.donor_apk, args.donor_build_report)
    java = derivative.current_sources(donor); native = derivative.validate_native(args.client_directory, commit, donor)
    # This validates the actual external donor ancestry and full new guest wrapper,
    # including its real Win32 proof, before fixture suites can claim qualification.
    actual_ancestry = importlib.import_module('test_client_render_pipeline_contract').validate_actual_native_ancestry(donor, native)
    package = derivative.client_manifest(donor, native)
    derivative.require(package['client_renderer_attribution'] == donor['_native_client_manifest']['client_renderer_attribution'],
        'Existing native renderer producer history changed')
    pins = {name: base.file_pin(ROOT/name) for name in source_paths(donor)}
    results = regressions()
    save = importlib.import_module('test_startup_bundle_save')
    derivative.require(save.REQUIRE_POSTGRESQL is True and save.POSTGRES_FIXTURES_RUN ==
        {'cancelled_child_deletion_commits', 'duplicate_insert_23505_rollback', 'delete_insert_replacement_commits'},
        'All retained real PostgreSQL emission fixtures required')
    repaired = importlib.import_module('test_levelup_ui_repair_dbserver')
    derivative.require(repaired.REQUIRE_POSTGRESQL is True and repaired.POSTGRES_FIXTURES_RUN == repaired.REQUIRED_POSTGRES_FIXTURES,
        'All retained real PostgreSQL level-up fixtures required')
    for name, expected in pins.items(): base.checked_file(ROOT/name, expected)
    checks = {name: all(results[suite]['status'] == 'passed' and results[suite]['skipped'] == 0 and results[suite]['tests_run'] > 0
        for suite in suites) for name, suites in CHECK_SUITES.items()}
    receipt = {'format': 1, 'status': 'passed' if all(checks.values()) else 'failed', 'scope': derivative.QUALIFICATION_SCOPE,
        'repository_commit': commit, 'runtime_repository_commit': commit, 'donor': derivative.donor_link(),
        'source_files': pins, 'test_suites': results, 'check_suites': CHECK_SUITES, 'checks': checks,
        'tests_run': sum(value['tests_run'] for value in results.values()), 'java_sources': java,
        'changed_java_sources': [], 'retained_java_sources_verified': 19,
        'postgresql_emission_fixtures': sorted(save.POSTGRES_FIXTURES_RUN),
        'postgresql_levelup_fixtures': sorted(repaired.POSTGRES_FIXTURES_RUN),
        'server_payload_extraction_preflight': donor['server_payload_extraction_preflight'],
        'baseline_payloads_verified': 77, 'immutable_visual_and_beacon_payloads_verified': True,
        'native_client_render_pipeline': native, 'retained_native_client_renderer_attribution': donor['native_client_renderer_attribution'],
        'client_gpu_runtime': donor['client_gpu_runtime'], 'actual_external_donor_and_full_guest_wrapper_verified': True,
        'actual_native_ancestry_validation': actual_ancestry,
        'native_build_provenance': derivative.native_build_provenance(),
        'publication_provenance': derivative.publication_provenance(commit),
        **dict.fromkeys(derivative.FALSE_FLAGS, False), **dict.fromkeys(derivative.TRUE_FLAGS, True),
        'client_session_repair': derivative.session_repair_contract(),
        'performance_claim_scope': 'Hosted checks prove the conservative owned presentation budget and Reopen-only '
            'render pipeline instrumentation opt-out, retained completed Game Win32 proof and original source/run provenance, '
            'exact retained twenty DLLs, nineteen authored Java sources and Android DEX/resources, successful .21 Mesa '
            'driver/WGL/Vulkan probes, all server/save/recovery rules, prepared assets/cache/schema and Software fallback. '
            'The .21 GPU device milestone is accepted. No sustained .23 FPS gain or physical movement repair is claimed '
            'until the focused Thor Reopen test confirms it.'}
    derivative.validate_qualification(receipt, commit)
    derivative.require(not args.output.exists() and not args.output.is_symlink(), 'Fresh qualification output required')
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
    print('Qualified guest session repair:', receipt['tests_run'], 'host scenarios; sustained physical gains pending')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--repository-commit', required=True)
    for name in ('donor-apk', 'donor-build-report', 'client-directory', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    qualify(parser.parse_args())


if __name__ == '__main__': main()
