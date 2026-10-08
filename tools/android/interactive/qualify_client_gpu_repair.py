#!/usr/bin/env python3
"""Qualify the .21 targeted probe/cleanup repair with all .20 gameplay guards."""
import argparse
import importlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'tools/android'),
    str(ROOT/'tools/android/dbserver'), str(ROOT/'tools'), str(ROOT/'android/guest')]
import build_client_gpu_repair_apk as derivative
import qualify_client_gpu_profile as previous
import qualify_startup_schedule as closure

RETAINED_TEST_MODULES = previous.TEST_MODULES
TEST_MODULES = RETAINED_TEST_MODULES + ('test_client_gpu_repair_package', 'test_client_renderer_performance_report', 'test_client_gpu_repair_evidence')
CHECK_SUITES = {
    'owned_cleanup_and_actual_screen_presentation_probe_guards_verified': [
        'test_client_gpu_profile', 'test_coh_gpu_probe_native', 'test_client_gpu_repair_package',
        'test_client_renderer_performance_report', 'test_client_gpu_repair_evidence'],
    'retained_gameplay_postgresql_and_recovery_guards_verified': list(RETAINED_TEST_MODULES),
    'exact_retained_donor_payload_source_signer_and_probe_only_gpu_repair_verified': [
        'test_client_gpu_repair_package', 'test_client_gpu_profile_package',
        'test_client_gpu_runtime_package', 'test_coh_vulkan_gpu_probe'],
}


def validate_suite_inventory():
    derivative.require(RETAINED_TEST_MODULES == previous.TEST_MODULES and len(RETAINED_TEST_MODULES) == 96
        and TEST_MODULES[:96] == RETAINED_TEST_MODULES and len(TEST_MODULES) == 99
        and len(set(TEST_MODULES)) == len(TEST_MODULES) and set(CHECK_SUITES) == set(derivative.CHECKS)
        and all(values and set(values) <= set(TEST_MODULES) for values in CHECK_SUITES.values()), 'Exact retained/new repair suite inventory required')


def source_paths(donor):
    names = set(donor['qualification']['source_files']) | set(derivative.SOURCE_FILES)
    names.update(Path(importlib.import_module(name).__file__).relative_to(ROOT).as_posix() for name in TEST_MODULES)
    return sorted(closure.source_closure(names))


def regressions():
    validate_suite_inventory()
    # Reuse the bounded executor without modifying the immutable .20 contract.
    results = {}
    import contextlib
    import io
    import unittest
    for name in TEST_MODULES:
        suite = unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(name))
        derivative.require(suite.countTestCases() > 0, name+' has no scenarios')
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            result = unittest.TextTestRunner(stream=captured, resultclass=previous.DetailedResult, verbosity=2).run(suite)
        output = captured.getvalue()
        derivative.require(len(output.encode()) <= 262144, 'Unbounded qualification output: '+name)
        derivative.require(result.wasSuccessful() and not result.skipped, name+' failed or skipped:\n'+output)
        print(name+': '+str(result.testsRun)+' passed; no skips', flush=True)
        results[name] = {'tests_run': result.testsRun, 'status': 'passed', 'skipped': 0}
    return results


def qualify(args):
    if hasattr(time, 'tzset'): os.environ['TZ'] = 'UTC'; time.tzset()
    validate_suite_inventory(); base = derivative.builder(); commit = base.source_commit(args.repository_commit)
    donor = derivative.validate_donor(args.donor_apk, args.donor_build_report, args.client_directory, args.donor_gpu_directory)
    _, java, changed = derivative.current_java_sources(donor, ROOT/'out/no-generated-java')
    native = derivative.validate_retained_native(args.client_directory, donor)
    gpu = derivative.validate_gpu(args.gpu_directory, commit, args.donor_gpu_directory, args.probe_directory)
    pins = {name: base.file_pin(ROOT/name) for name in source_paths(donor)}
    results = regressions()
    save = importlib.import_module('test_startup_bundle_save')
    derivative.require(save.REQUIRE_POSTGRESQL is True and save.POSTGRES_FIXTURES_RUN ==
        {'cancelled_child_deletion_commits', 'duplicate_insert_23505_rollback', 'delete_insert_replacement_commits'}, 'All retained real PostgreSQL emission fixtures required')
    repaired = importlib.import_module('test_levelup_ui_repair_dbserver')
    derivative.require(repaired.REQUIRE_POSTGRESQL is True and repaired.POSTGRES_FIXTURES_RUN == repaired.REQUIRED_POSTGRES_FIXTURES,
        'All retained real PostgreSQL level-up fixtures required')
    for name, expected in pins.items(): base.checked_file(ROOT/name, expected)
    checks = {name: all(results[suite]['status'] == 'passed' and results[suite]['skipped'] == 0
        and results[suite]['tests_run'] > 0 for suite in suites) for name, suites in CHECK_SUITES.items()}
    receipt = {'format': 1, 'status': 'passed' if all(checks.values()) else 'failed', 'scope': derivative.QUALIFICATION_SCOPE,
        'repository_commit': commit, 'runtime_repository_commit': commit, 'donor': derivative.donor_link(),
        'source_files': pins, 'test_suites': results, 'check_suites': CHECK_SUITES, 'checks': checks,
        'tests_run': sum(value['tests_run'] for value in results.values()), 'java_sources': java,
        'changed_java_sources': changed, 'retained_java_sources_verified': 17,
        'postgresql_emission_fixtures': sorted(save.POSTGRES_FIXTURES_RUN),
        'postgresql_levelup_fixtures': sorted(repaired.POSTGRES_FIXTURES_RUN),
        'server_payload_extraction_preflight': donor['server_payload_extraction_preflight'],
        'baseline_payloads_verified': 77, 'immutable_visual_and_beacon_payloads_verified': True,
        'native_client_renderer_attribution': native, 'client_gpu_runtime': gpu,
        'installed_runtime_identity_preserved': False,
        **dict.fromkeys(derivative.FALSE_FLAGS, False), **dict.fromkeys(derivative.TRUE_FLAGS, True),
        'performance_claim_scope': 'Hosted qualification proves the bounded owned cleanup guard, real screen-pixel '
            'presentation prerequisite, current WGL probe source/Win32 proof and helper, exact retained Mesa '
            'driver/native Vulkan probe/base ABI and all original GPU producer history. Game/20 DLLs/17 Java/'
            'resources/servers/save rules/prepared assets/Wine/FEX/rootfs/display remain exact. '
            'Only ClientAcceptance/ClientRuntime Java and DEX are recompiled for the bounded current-session evidence repair. '
            'Actual Game hardware rendering, FPS, temperature, visual correctness and black-glitch resolution require Thor testing.'}
    derivative.validate_qualification(receipt, commit)
    derivative.require(not args.output.exists() and not args.output.is_symlink(), 'Fresh qualification output required')
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
    print('Qualified targeted GPU repair:', receipt['tests_run'], 'host scenarios; physical Game performance pending')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--repository-commit', required=True)
    for name in ('donor-apk', 'donor-build-report', 'client-directory', 'gpu-directory', 'donor-gpu-directory', 'probe-directory', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    qualify(parser.parse_args())


if __name__ == '__main__': main()
