#!/usr/bin/env python3
"""Qualify explicit startup-only reopening without repeating accepted task work.

The donor's native qualification is inherited by exact public byte identity.
Focused host checks cover stale receipt retirement, ordinary-save retention,
the opt-in startup route and the previously qualified startup/storage paths.
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
import build_task_receipt_cleanup_apk as derivative
import qualify_startup_schedule as startup

TEST_MODULES = startup.TEST_MODULES + ('test_task_receipt_cleanup_package', 'test_task_receipt_cleanup')
CHECK_SUITES = {
    'previous_task_receipt_retirement_and_failure_guards_verified': ['test_task_receipt_cleanup'],
    'explicit_startup_only_reopen_and_historical_task_guards_verified': ['test_task_receipt_cleanup', 'test_task_gate_evidence', 'test_character_reopen_guest'],
    'ordinary_save_identity_and_prior_startup_guards_verified': [name for name in startup.TEST_MODULES
        if name not in ('test_startup_schedule_package', 'test_classify_interactive_change', 'test_classify_storage_cleanup_change')],
    'source_bound_retained_native_payloads_and_actual_archive_extraction_verified': [
        'test_task_receipt_cleanup_package', 'test_startup_schedule_package',
        'test_classify_interactive_change', 'test_classify_storage_cleanup_change'],
}


def source_paths(donor):
    names = set(startup.source_paths(donor)) | set(derivative.SOURCE_FILES)
    names.update(Path(importlib.import_module(name).__file__).relative_to(ROOT).as_posix() for name in TEST_MODULES)
    return sorted(startup.source_closure(names))


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
        derivative.require(result.wasSuccessful() and not result.skipped, name+' failed or skipped required checks:\n'+output)
        print(name+': '+str(result.testsRun)+' passed; no skips', flush=True)
        results[name] = {'tests_run': result.testsRun, 'status': 'passed', 'skipped': 0}
    return results


def qualify(args):
    if hasattr(time, 'tzset'): os.environ['TZ'] = 'UTC'; time.tzset()
    base = derivative.builder(); commit = base.source_commit(args.repository_commit)
    donor = derivative.validate_donor(args.donor_apk, args.donor_build_report)
    _, java, changed = derivative.current_java_sources(donor, ROOT/'out/no-generated-java')
    pins = {name: base.file_pin(ROOT/name) for name in source_paths(donor)}
    results = regressions()
    for name, expected in pins.items(): base.checked_file(ROOT/name, expected)
    checks = {name: all(results[suite]['status'] == 'passed' and results[suite]['skipped'] == 0
        and results[suite]['tests_run'] > 0 for suite in suites) for name, suites in CHECK_SUITES.items()}
    checks['source_bound_retained_native_payloads_and_actual_archive_extraction_verified'] &= (
        len(donor['payloads']) == 67 and donor['server_payload_extraction_preflight']['status'] == 'passed')
    receipt = {'format': 1, 'status': 'passed' if all(checks.values()) else 'failed',
        'scope': derivative.QUALIFICATION_SCOPE, 'repository_commit': commit,
        'retained_runtime_repository_commit': derivative.DONOR_COMMIT,
        'retained_native_repository_commit': derivative.RETAINED_NATIVE_COMMIT,
        'donor_apk_sha256': derivative.DONOR_APK['sha256'], 'donor': derivative.donor_link(),
        'source_files': pins, 'test_suites': results, 'check_suites': CHECK_SUITES,
        'tests_run': sum(item['tests_run'] for item in results.values()), 'checks': checks,
        'physical_gameplay_validated': False, 'physical_startup_timing_validated': False,
        'physical_storage_cleanup_validated': False, 'physical_fresh_profile_recovery_validated': False,
        'native_runtime_booted': False, 'native_client_or_server_recompiled': False,
        'long_prior_gameplay_milestones_repeated': False, 'runtime_refresh_required': True,
        'previous_runtime_generation_retained': True, 'asset_reimport_required': False,
        'retained_baseline_payloads_verified': 67, 'authored_java_sources_verified': len(java),
        'changed_java_sources': changed, 'server_payload_extraction_preflight': donor['server_payload_extraction_preflight'],
        'performance_claim_scope': 'Host checks establish prior task receipt retirement, explicit startup-only '
            'selection, retained guest freshness and ordinary-save guards. No device timing or task repeat is claimed.',
        'preserved_state': 'All native executables, archives, source receipts, world/avatar assets and caches '
            'retain exact public 0.13.3 bytes. Existing THORHERO profile and completed task remain retained. '
            'One Setup runtime installs the changed reopen helper; prior generation remains available for rollback.'}
    derivative.validate_qualification(receipt, commit)
    derivative.require(not args.output.exists() and not args.output.is_symlink(), 'Fresh startup-only qualification output required')
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(receipt, indent=2)+'\n')
    print('Qualified startup-only candidate:', receipt['tests_run'], 'host checks; device timing pending')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository-commit', required=True)
    for name in ('donor-apk', 'donor-build-report', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    qualify(parser.parse_args())


if __name__ == '__main__': main()
