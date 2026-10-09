#!/usr/bin/env python3
"""Run every current retained gameplay suite plus the new guest-only boundary."""
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
import build_thor_performance_apk as derivative
import qualify_ui_beacon as previous
import qualify_startup_schedule as closure

# The closed 0.13.14 package suite insists that this candidate retain the old
# guest AST. Its exact donor boundary and all 75 released payload pins are now
# checked against actual public 0.13.14 bytes by this candidate's boundary.
RETAINED_TEST_MODULES = tuple(name for name in previous.TEST_MODULES if name != 'test_ui_beacon_package')
TEST_MODULES = RETAINED_TEST_MODULES + ('test_character_map_data', 'test_thor_performance_package', 'test_thor_performance_report')
CHECK_SUITES = {
    'performance_caches_and_lightweight_diagnostics_verified': ['test_server_worktree_reuse',
        'test_character_readiness', 'test_character_server', 'test_character_map_data', 'test_thor_performance_report'],
    'retained_ui_beacon_gameplay_postgresql_and_recovery_guards_verified': list(RETAINED_TEST_MODULES),
    'exact_guest_only_payload_shell_source_and_server_extraction_verified': ['test_thor_performance_package',
        'test_classify_interactive_change', 'test_classify_storage_cleanup_change'],
}


def source_paths(donor):
    names = set(donor['qualification']['source_files']) | set(derivative.SOURCE_FILES)
    names.update(Path(importlib.import_module(name).__file__).relative_to(ROOT).as_posix() for name in TEST_MODULES)
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


def qualify(args):
    if hasattr(time, 'tzset'): os.environ['TZ'] = 'UTC'; time.tzset()
    base = derivative.builder(); commit = base.source_commit(args.repository_commit)
    donor = derivative.validate_donor(args.donor_apk, args.donor_build_report); java = derivative.current_sources(donor)
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
    derivative.require(len(set(TEST_MODULES)) == len(TEST_MODULES) and set(CHECK_SUITES) == set(derivative.CHECKS)
        and all(suites and set(suites) <= set(TEST_MODULES) for suites in CHECK_SUITES.values()), 'Exact qualification suite contract required')
    checks = {name: all(results[suite]['status'] == 'passed' and results[suite]['skipped'] == 0
        and results[suite]['tests_run'] > 0 for suite in suites) for name, suites in CHECK_SUITES.items()}
    receipt = {'format': 1, 'status': 'passed' if all(checks.values()) else 'failed', 'scope': derivative.QUALIFICATION_SCOPE,
        'repository_commit': commit, 'donor': derivative.donor_link(), 'source_files': pins,
        'test_suites': results, 'check_suites': CHECK_SUITES, 'checks': checks,
        'tests_run': sum(item['tests_run'] for item in results.values()), 'retained_java_sources': java,
        'postgresql_emission_fixtures': sorted(save.POSTGRES_FIXTURES_RUN),
        'postgresql_levelup_fixtures': sorted(repaired.POSTGRES_FIXTURES_RUN),
        'server_payload_extraction_preflight': donor['server_payload_extraction_preflight'],
        'baseline_payloads_verified': 75, 'immutable_visual_and_beacon_payloads_verified': True,
        **{key: False for key in derivative.FALSE_FLAGS},
        'performance_claim_scope': 'Hosted checks prove safe guest-only staging and event-driven diagnostics changes, '
            'exact native/renderer/Wine/FEX/UI/beacon payload conservation and all retained save/recovery guards. '
            'Physical startup and FPS improvement require the next AYN Thor measurement.'}
    derivative.validate_qualification(receipt, commit)
    derivative.require(not args.output.exists() and not args.output.is_symlink(), 'Fresh qualification output required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
    print('Qualified performance candidate:', receipt['tests_run'], 'host scenarios; physical performance pending')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--repository-commit', required=True)
    for name in ('donor-apk', 'donor-build-report', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    qualify(parser.parse_args())


if __name__ == '__main__': main()
