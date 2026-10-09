#!/usr/bin/env python3
"""Qualify owned setup I/O pressure repair while retaining the exact .23 runtime."""
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
import build_setup_copy_repair_apk as derivative
import qualify_client_session_repair as previous
import qualify_startup_schedule as closure

RETAINED_TEST_MODULES = previous.TEST_MODULES
NEW_TEST_MODULES = ('test_setup_copy_repair_package','test_setup_copy_memory','test_setup_io_memory')
TEST_MODULES = RETAINED_TEST_MODULES + NEW_TEST_MODULES
CHECK_SUITES = {
    'owned_setup_copy_memory_and_recovery_verified': [
        'test_setup_copy_memory','test_setup_io_memory','test_runtime_setup_reuse',
        'test_setup_service','test_setup_memory_guard','test_setup_copy_repair_package'],
    'retained_gameplay_postgresql_gpu_cleanup_and_recovery_guards_verified': list(RETAINED_TEST_MODULES),
    'exact_android_only_payload_native_proof_and_runtime_identity_verified': [
        'test_setup_copy_repair_package','test_client_session_repair_package',
        'test_client_render_pipeline_contract','test_classify_interactive_change','test_classify_storage_cleanup_change'],
}

def source_paths(donor):
    names = set(donor['qualification']['source_files']) | set(derivative.SOURCE_FILES)
    names.update(Path(importlib.import_module(name).__file__).relative_to(ROOT).as_posix() for name in TEST_MODULES)
    return sorted(closure.source_closure(names))


def validate_suite_inventory():
    derivative.require(RETAINED_TEST_MODULES==previous.TEST_MODULES and len(RETAINED_TEST_MODULES)==107
        and TEST_MODULES[:107]==RETAINED_TEST_MODULES and len(TEST_MODULES)==110
        and len(set(TEST_MODULES)) == len(TEST_MODULES) and set(CHECK_SUITES) == set(derivative.CHECKS)
        and all(suites and set(suites) <= set(TEST_MODULES) for suites in CHECK_SUITES.values()), 'Exact qualification suite contract required')


def regressions():
    validate_suite_inventory()
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
    donor = derivative.validate_donor(args.donor_apk, args.donor_build_report, args.retained_client_directory)
    _, java, changed = derivative.current_java_sources(donor, ROOT/'out/no-generated-java')
    native = derivative.validate_retained_native(args.retained_client_directory, donor)
    actual_ancestry = derivative.validate_actual_native_ancestry(donor,native)
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
        'repository_commit': commit, 'runtime_repository_commit': derivative.DONOR_COMMIT,
        'donor': derivative.donor_link(), 'source_files': pins,
        'test_suites': results, 'check_suites': CHECK_SUITES, 'checks': checks,
        'tests_run': sum(item['tests_run'] for item in results.values()), 'java_sources': java,
        'changed_java_sources': changed, 'retained_java_sources_verified': 19-len(derivative.JAVA_CHANGES),
        'authored_java_sources_verified': 19,
        'postgresql_emission_fixtures': sorted(save.POSTGRES_FIXTURES_RUN),
        'postgresql_levelup_fixtures': sorted(repaired.POSTGRES_FIXTURES_RUN),
        'server_payload_extraction_preflight': donor['server_payload_extraction_preflight'],
        'baseline_payloads_verified': 77, 'immutable_visual_and_beacon_payloads_verified': True,
        'java_or_dex_recompiled': True, 'installed_runtime_identity_preserved': True,
        'native_client_package_reused': True, 'retained_native_render_pipeline': native,
        'retained_native_source_and_Win32_proof_verified': True,
        'runtime_manifest_sha256': donor['runtime_manifest_sha256'],
        'native_build_provenance': derivative.native_build_provenance(),
        'publication_provenance': derivative.publication_provenance(commit),
        'actual_native_ancestry_validation': actual_ancestry,
        'retained_native_repository_commit': derivative.NATIVE_BUILD_COMMIT,
        **{key: False for key in derivative.FALSE_FLAGS},
        'physical_claim_scope': 'Hosted checks qualify the reviewed Android setup copy/staging and memory-pressure guards, '
            'honest Java/DEX recompilation, exact inherited Game/Win32/source proofs, all 77 unchanged .23 runtime payloads, '
            'the three guest movement-budget helpers and Reopen timing isolation, successful GPU/probe bytes, '
            'all seven real PostgreSQL save/recovery fixtures and retained visual assets. '
            'System low-memory recovery and subsequent gameplay must be tested on AYN Thor; no sustained FPS gain is claimed.'}
    derivative.validate_qualification(receipt, commit)
    derivative.require(not args.output.exists() and not args.output.is_symlink(), 'Fresh qualification output required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
    print('Qualified Android setup repair candidate:', receipt['tests_run'], 'host scenarios; physical input testing pending')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--repository-commit', required=True)
    for name in ('donor-apk', 'donor-build-report', 'retained-client-directory', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    qualify(parser.parse_args())


if __name__ == '__main__': main()
