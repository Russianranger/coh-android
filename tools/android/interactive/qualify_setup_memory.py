#!/usr/bin/env python3
"""Qualify bounded runtime setup while conserving exact public runtime identity."""
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
import build_setup_memory_apk as derivative
import qualify_task_receipt_cleanup as prior
import qualify_startup_schedule as closure

TEST_MODULES = prior.TEST_MODULES + ('test_setup_memory_package', 'test_setup_memory_guard',
    'test_setup_service', 'test_archive')
CHECK_SUITES = {
    'bounded_setup_heap_and_streaming_archive_guards_verified': ['test_setup_memory_guard', 'test_archive'],
    'setup_service_oom_cancellation_checkpoint_and_failure_guards_verified': ['test_setup_service', 'test_runtime_setup_reuse'],
    'retained_startup_task_save_storage_and_profile_guards_verified': list(prior.TEST_MODULES),
    'exact_runtime_identity_payloads_and_actual_archive_extraction_verified': ['test_setup_memory_package',
        'test_archive', 'test_classify_interactive_change', 'test_classify_storage_cleanup_change'],
}


def source_paths(donor):
    names = set(prior.source_paths(donor)) | set(derivative.SOURCE_FILES)
    names.update(Path(importlib.import_module(name).__file__).relative_to(ROOT).as_posix() for name in TEST_MODULES)
    # Tar extraction host fixtures are dynamically selected by filename.
    names.update(path.relative_to(ROOT).as_posix() for path in (ROOT/'tools/android/java').rglob('*.java'))
    return sorted(closure.source_closure(names))


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
    checks['exact_runtime_identity_payloads_and_actual_archive_extraction_verified'] &= (
        len(donor['payloads']) == 67 and donor['server_payload_extraction_preflight']['status'] == 'passed')
    receipt = {'format': 1, 'status': 'passed' if all(checks.values()) else 'failed',
        'scope': derivative.QUALIFICATION_SCOPE, 'repository_commit': commit,
        'runtime_repository_commit': derivative.DONOR_COMMIT,
        'retained_native_repository_commit': derivative.RETAINED_NATIVE_COMMIT,
        'donor_apk_sha256': derivative.DONOR_APK['sha256'], 'donor': derivative.donor_link(),
        'source_files': pins, 'test_suites': results, 'check_suites': CHECK_SUITES,
        'tests_run': sum(item['tests_run'] for item in results.values()), 'checks': checks,
        'physical_gameplay_validated': False, 'physical_startup_timing_validated': False,
        'physical_storage_cleanup_validated': False, 'physical_fresh_profile_recovery_validated': False,
        'physical_setup_memory_validated': False, 'native_runtime_booted': False,
        'native_client_or_server_recompiled': False, 'long_prior_gameplay_milestones_repeated': False,
        'runtime_refresh_required': False, 'installed_runtime_identity_preserved': True, 'asset_reimport_required': False,
        'retained_payloads_verified': 67, 'authored_java_sources_verified': len(java),
        'changed_java_sources': changed, 'added_java_sources': sorted(derivative.JAVA_ADDITIONS),
        'server_payload_extraction_preflight': donor['server_payload_extraction_preflight'],
        'performance_claim_scope': 'Host scenarios exercise bounded Java heap guard behavior, streaming archive '
            'extraction, cancellation, owned checkpoint/exit evidence and service failure cleanup. '
            'They do not establish physical Android memory pressure or prevention of an OS process kill.',
        'preserved_state': 'All 67 payloads, runtime/client manifests, native executables, archives, caches '
            'and installed generation identity retain exact public 0.13.4 bytes. No additional runtime '
            'generation, asset reimport, native build or profile recreation is required.'}
    derivative.validate_qualification(receipt, commit)
    derivative.require(not args.output.exists() and not args.output.is_symlink(), 'Fresh setup-memory qualification output required')
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(receipt, indent=2)+'\n')
    print('Qualified setup-memory candidate:', receipt['tests_run'], 'host checks; physical memory observation pending')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository-commit', required=True)
    for name in ('donor-apk', 'donor-build-report', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    qualify(parser.parse_args())


if __name__ == '__main__': main()
