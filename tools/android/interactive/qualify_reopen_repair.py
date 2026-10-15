#!/usr/bin/env python3
"""Qualify extraction repair using shipped guest and bounded Java consumers."""
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
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'tools/android'), str(ROOT/'tools/android/game'),
               str(ROOT/'tools'), str(ROOT/'android/guest')]
import build_reopen_repair_apk as derivative
import build_apk as base
import qualify_startup_perf as prior

TEST_MODULES = (
    ('test_reopen_repair_package', 11), ('test_archive', 18),
    ('test_process_exit_history', 4),
    ('test_responsiveness_package', 14), ('test_native_client_upgrade', 5),
    ('test_character_reopen_guest', 14), ('test_character_guest', 16),
    ('test_server_worktree_reuse', 10), ('test_session_budget_guest', 13),
    ('test_session_budget_java', 5), ('test_ground_repair', 8),
)


def source_paths():
    # Reuse the complete native/source closure without rerunning unchanged
    # native or physical gameplay milestones.
    inherited = derivative.CORE.module('coh_reopen_repair_qualification_sources',
                                      Path(__file__).with_name('qualify_responsiveness.py'))
    inherited.derivative = derivative
    inherited.TEST_MODULES = TEST_MODULES
    return inherited.source_paths()


def regressions():
    results = {}
    for name, minimum in TEST_MODULES:
        loaded = importlib.import_module(name)
        suite = unittest.defaultTestLoader.loadTestsFromModule(loaded)
        derivative.require(suite.countTestCases() >= minimum, name+' lost required repair coverage')
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            result = unittest.TextTestRunner(verbosity=2).run(suite)
        derivative.require(result.wasSuccessful() and not result.skipped, name+' failed or skipped repair checks')
        output = captured.getvalue()
        if output: print(output, end='')
        results[name] = {'tests_run': result.testsRun, 'status': 'passed', 'skipped': 0}
    return results


def qualify(args):
    if hasattr(time, 'tzset'):
        os.environ['TZ'] = 'UTC'; time.tzset()
    commit = base.source_commit(args.repository_commit)
    donor = derivative.validate_donor(args.donor_apk, args.donor_build_report)
    reproduction = derivative.reproduce_prior_archive_failure(args.prior_apk)
    _, java, changed = derivative.current_java_sources(donor, ROOT/'out/no-generated-java')
    for name, pin in donor['payloads'].items():
        if name.startswith('assets/runtime/') and name.endswith('.py') and Path(name).name not in derivative.HELPERS:
            base.checked_file(ROOT/'android/guest'/Path(name).name, pin)
    pins = {name: base.file_pin(ROOT/name) for name in source_paths()}
    results = regressions()
    for name, pin in pins.items(): base.checked_file(ROOT/name, pin)
    policy_tests = importlib.import_module('test_session_budget_guest')
    reopen_tests = importlib.import_module('test_character_reopen_guest')
    prior.verify_policy(policy_tests, reopen_tests)
    receipt = {'format': 1, 'status': 'passed', 'scope': derivative.QUALIFICATION_SCOPE,
        'repository_commit': commit, 'donor_apk_sha256': derivative.DONOR_APK['sha256'],
        'source_files': pins, 'test_suites': results,
        'tests_run': sum(value['tests_run'] for value in results.values()),
        'checks': {name: True for name in derivative.CHECKS}, 'policy': prior.POLICY,
        'physical_gameplay_validated': False, 'native_runtime_booted': False,
        'donor': derivative.donor_link(), 'prior_archive_failure': reproduction,
        'retained_payloads_verified': len(donor['payloads']),
        'authored_java_sources_verified': len(java), 'changed_java_sources': changed,
        'native_source_receipts': {key: getattr(importlib.import_module(module_name), expected_name)()
            for key, (module_name, _, expected_name) in derivative.native_package.INPUTS.items()},
        'native_build_reuse_required': {'run_id': derivative.NATIVE_RUN_ID, 'repository_commit': derivative.NATIVE_COMMIT},
        'performance_measurement': 'No new timing or FPS claim; reduced refresh allocations verified under bounded Java heap',
        'native_game_or_mapserver_recompiled': False, 'long_prior_gameplay_milestones_repeated': False}
    derivative.validate_qualification(receipt, commit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2)+'\n')
    print('Qualified reopen/refresh repair:', receipt['tests_run'], 'focused checks')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository-commit', required=True)
    for name in ('donor-apk', 'donor-build-report', 'prior-apk', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    qualify(parser.parse_args())


if __name__ == '__main__': main()
