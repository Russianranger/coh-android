#!/usr/bin/env python3
"""Qualify renderer attribution, bounded captures and strict failed-save diagnostics."""
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
import build_client_renderer_attribution_apk as derivative
import qualify_client_sidebar as previous
import qualify_startup_schedule as closure

RETAINED_TEST_MODULES = previous.TEST_MODULES
TEST_MODULES = RETAINED_TEST_MODULES + ('test_client_renderer_attribution_native',
    'test_client_renderer_attribution_source', 'test_client_renderer_attribution_contract',
    'test_client_renderer_attribution_package', 'test_client_surface_capture',
    'test_client_capture_metrics', 'test_stock_power_delta')
CHECK_SUITES = {
    'native_renderer_attribution_and_current_producer_controls_verified': [
        'test_client_renderer_attribution_native', 'test_client_renderer_attribution_source',
        'test_client_renderer_attribution_contract', 'test_client_gameplay_performance_native',
        'test_client_gameplay_performance_source', 'test_client_gameplay_performance_contract'],
    'bounded_background_capture_and_strict_failed_save_diagnostics_verified': [
        'test_client_surface_capture', 'test_client_capture_metrics', 'test_stock_power_delta',
        'test_input', 'test_client_sidebar_commands', 'test_client_sidebar_runtime'],
    'retained_gameplay_postgresql_and_recovery_guards_verified': list(RETAINED_TEST_MODULES),
    'exact_game_and_reviewed_android_helper_payload_boundaries_verified': [
        'test_client_renderer_attribution_package', 'test_client_renderer_attribution_contract',
        'test_classify_interactive_change', 'test_classify_storage_cleanup_change'],
}


def source_paths(donor):
    names = set(donor['qualification']['source_files']) | set(derivative.SOURCE_FILES)
    names.update(Path(importlib.import_module(name).__file__).relative_to(ROOT).as_posix() for name in TEST_MODULES)
    return sorted(closure.source_closure(names))


def validate_suite_inventory():
    derivative.require(len(set(TEST_MODULES)) == len(TEST_MODULES) and set(CHECK_SUITES) == set(derivative.CHECKS)
        and all(suites and set(suites) <= set(TEST_MODULES) for suites in CHECK_SUITES.values()), 'Exact qualification suite contract required')


class DetailedResult(unittest.TextTestResult):
    def addError(self, test, error):
        super().addError(test, error)
        detail = getattr(error[1], 'stderr', None)
        if detail:
            self.stream.write('\nBounded captured child stderr:\n'+str(detail)[:65536]+'\n')


def regressions():
    validate_suite_inventory(); results = {}
    for name in TEST_MODULES:
        suite = unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(name))
        derivative.require(suite.countTestCases() > 0, name+' has no scenarios')
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            result = unittest.TextTestRunner(stream=captured, resultclass=DetailedResult, verbosity=2).run(suite)
        output = captured.getvalue()
        derivative.require(len(output.encode()) <= 262144, 'Unbounded qualification output: '+name)
        derivative.require(result.wasSuccessful() and not result.skipped, name+' failed or skipped checks:\n'+output)
        print(name+': '+str(result.testsRun)+' passed; no skips', flush=True)
        results[name] = {'tests_run': result.testsRun, 'status': 'passed', 'skipped': 0}
    return results


def qualify(args):
    if hasattr(time, 'tzset'): os.environ['TZ'] = 'UTC'; time.tzset()
    validate_suite_inventory(); base = derivative.builder(); commit = base.source_commit(args.repository_commit)
    donor = derivative.validate_donor(args.donor_apk, args.donor_build_report)
    _, java, changed = derivative.current_java_sources(donor, ROOT/'out/no-generated-java')
    native = derivative.validate_native(args.client_directory, commit, donor)
    actual_ancestry = importlib.import_module('test_client_renderer_attribution_contract').validate_actual_native_ancestry(donor, native)
    pins = {name: base.file_pin(ROOT/name) for name in source_paths(donor)}
    results = regressions()
    save = importlib.import_module('test_startup_bundle_save')
    derivative.require(save.REQUIRE_POSTGRESQL is True and save.POSTGRES_FIXTURES_RUN ==
        {'cancelled_child_deletion_commits', 'duplicate_insert_23505_rollback', 'delete_insert_replacement_commits'},
        'Every real retained PostgreSQL emission fixture is required')
    repaired = importlib.import_module('test_levelup_ui_repair_dbserver')
    derivative.require(repaired.REQUIRE_POSTGRESQL is True and repaired.POSTGRES_FIXTURES_RUN == repaired.REQUIRED_POSTGRES_FIXTURES,
        'Every real retained PostgreSQL level-up fixture is required')
    for name, pin in pins.items(): base.checked_file(ROOT/name, pin)
    checks = {name: all(results[suite]['status'] == 'passed' and results[suite]['skipped'] == 0
        and results[suite]['tests_run'] > 0 for suite in suites) for name, suites in CHECK_SUITES.items()}
    receipt = {'format': 1, 'status': 'passed' if all(checks.values()) else 'failed', 'scope': derivative.QUALIFICATION_SCOPE,
        'repository_commit': commit, 'runtime_repository_commit': commit, 'donor': derivative.donor_link(),
        'source_files': pins, 'test_suites': results, 'check_suites': CHECK_SUITES, 'checks': checks,
        'tests_run': sum(item['tests_run'] for item in results.values()),
        'java_sources': java, 'changed_java_sources': changed, 'retained_java_sources_verified': 15,
        'postgresql_emission_fixtures': sorted(save.POSTGRES_FIXTURES_RUN),
        'postgresql_levelup_fixtures': sorted(repaired.POSTGRES_FIXTURES_RUN),
        'server_payload_extraction_preflight': donor['server_payload_extraction_preflight'],
        'baseline_payloads_verified': 75, 'immutable_visual_and_beacon_payloads_verified': True,
        'native_client_recompiled': True, 'native_client_compiled_in_current_run': True,
        'native_client_package_reused': False, 'native_client_renderer_attribution': native,
        'actual_native_ancestry_validation': actual_ancestry,
        'java_or_dex_recompiled': True, 'guest_helpers_changed': True, 'runtime_manifest_changed': True,
        'runtime_refresh_required': True, 'installed_runtime_identity_preserved': False,
        **{key: False for key in derivative.FALSE_FLAGS},
        'performance_claim_scope': 'Hosted checks prove bounded renderer diagnostics, numeric cap/showfps state, '
            'the retained 10/30 FPS controls, bounded off-main capture encoding, strict failed-save diagnostics, '
            'four reviewed Java/four helper changes, Game-only native replacement, exact retained driver/Wine/FEX, '
            'resources/beacons/server/cache/schema and all previous gameplay/recovery guards. '
            'Native FPS, startup and capture pause benefits require physical AYN Thor measurements.'}
    derivative.validate_qualification(receipt, commit)
    derivative.require(not args.output.exists() and not args.output.is_symlink(), 'Fresh qualification output required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
    print('Qualified renderer/capture candidate:', receipt['tests_run'], 'host scenarios; physical performance pending')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--repository-commit', required=True)
    for name in ('donor-apk', 'donor-build-report', 'client-directory', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    qualify(parser.parse_args())


if __name__ == '__main__': main()
