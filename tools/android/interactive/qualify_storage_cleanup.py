#!/usr/bin/env python3
"""Exercise storage cleanup and all retained 0.13.0 host guards.

The exact public runtime is conserved, so its native qualification is retained
by immutable identity. No native generation, gameplay or physical test repeats.
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
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'tools/android'), str(ROOT/'tools'), str(ROOT/'android/guest')]
import build_storage_cleanup_apk as derivative
import build_apk as base
import qualify_task_gate as retained
import qualify_startup_caches as closure

NEW_SUITES = (('test_storage_cleanup_package', 22), ('test_storage_audit', 36),
              ('test_storage_ui', 15), ('test_classify_storage_cleanup_change', 3))
CHECK_SUITES = {
    'bounded_storage_inventory_and_protected_paths_verified': ('test_storage_audit',),
    'owned_cleanup_identity_and_failure_guards_verified': ('test_storage_audit', 'test_storage_cleanup_package'),
    'storage_ui_idle_session_and_export_guards_verified': ('test_storage_ui', 'test_session_budget_guest', 'test_session_budget_java'),
    'retained_task_input_save_and_cache_guards_verified': tuple(name for name, _ in retained.TEST_MODULES),
    'all_runtime_payloads_and_actual_archive_extraction_verified':
        ('test_storage_cleanup_package', 'test_classify_storage_cleanup_change', 'task_retained_tar_extractor_regressions'),
}


def source_paths():
    names = set(retained.source_paths()) | set(derivative.SOURCE_FILES)
    for name, _ in NEW_SUITES:
        names.add(Path(importlib.import_module(name).__file__).relative_to(ROOT).as_posix())
    return sorted(closure.host_python_closure(names))


def regressions():
    results = retained.regressions()
    for name, minimum in NEW_SUITES:
        suite = unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(name))
        derivative.require(suite.countTestCases() >= minimum, name+' lost required coverage')
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            result = unittest.TextTestRunner(stream=captured, verbosity=2).run(suite)
        output = captured.getvalue()
        derivative.require(len(output.encode()) <= 262144, 'Unbounded qualification output: '+name)
        derivative.require(result.wasSuccessful() and not result.skipped,
                           name+' failed or skipped required checks:\n'+output)
        print(name+': '+str(result.testsRun)+' passed; no skips', flush=True)
        results[name] = {'tests_run': result.testsRun, 'status': 'passed', 'skipped': 0}
    return results


def qualify(args):
    if hasattr(time, 'tzset'):
        os.environ['TZ'] = 'UTC'; time.tzset()
    commit = base.source_commit(args.repository_commit)
    donor = derivative.validate_donor(args.donor_apk, args.donor_build_report)
    _, java, changed = derivative.current_java_sources(donor, ROOT/'out/no-generated-java')
    pins = {name: base.file_pin(ROOT/name) for name in source_paths()}
    results = regressions()
    for name, expected in pins.items(): base.checked_file(ROOT/name, expected)
    checks = {name: all(results.get(suite, {}).get('status') == 'passed'
                       and results[suite]['skipped'] == 0 and results[suite]['tests_run'] > 0 for suite in suites)
              for name, suites in CHECK_SUITES.items()}
    checks['all_runtime_payloads_and_actual_archive_extraction_verified'] &= (
        donor['server_payload_extraction_preflight']['status'] == 'passed'
        and len(donor['payloads']) == 65)
    receipt = {'format': 1, 'status': 'passed' if all(checks.values()) else 'failed',
        'scope': derivative.QUALIFICATION_SCOPE, 'repository_commit': commit,
        'runtime_repository_commit': derivative.DONOR_COMMIT,
        'donor_apk_sha256': derivative.DONOR_APK['sha256'], 'donor': derivative.donor_link(),
        'source_files': pins, 'test_suites': results, 'check_suites': CHECK_SUITES,
        'tests_run': sum(item['tests_run'] for item in results.values()), 'checks': checks,
        'physical_gameplay_validated': False, 'physical_startup_timing_validated': False,
        'physical_storage_cleanup_validated': False, 'native_runtime_booted': False,
        'native_client_or_server_recompiled': False, 'long_prior_gameplay_milestones_repeated': False,
        'retained_payloads_verified': len(donor['payloads']), 'authored_java_sources_verified': len(java),
        'changed_java_sources': changed, 'added_java_sources': sorted(derivative.JAVA_ADDITIONS),
        'server_payload_extraction_preflight': donor['server_payload_extraction_preflight'],
        'performance_claim_scope': 'Host checks establish storage inventory bounds, protected paths, '
            'owned cleanup and idle-session guards, plus all prior task/input/save/cache host guards. '
            'Exact 0.13.0 native/runtime bytes and prior native qualification remain retained. '
            'Device storage totals and actual recovered space require the device audit.',
        'preserved_state': 'Current private profile, imported assets, PostgreSQL data, exact 93 server '
            'caches, animation pack and runtime manifests retain all public 0.13.0 bytes. '
            'No runtime refresh, reimport or accepted physical test repeats are required.'}
    derivative.validate_qualification(receipt, commit)
    derivative.require(not args.output.exists() and not args.output.is_symlink(), 'Fresh storage qualification output required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2)+'\n')
    print('Qualified storage candidate:', receipt['tests_run'], 'host checks; physical cleanup pending')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository-commit', required=True)
    for name in ('donor-apk', 'donor-build-report', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    qualify(parser.parse_args())


if __name__ == '__main__': main()
