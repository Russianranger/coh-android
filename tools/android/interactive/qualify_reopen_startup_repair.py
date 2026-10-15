#!/usr/bin/env python3
"""Qualify the narrow native startup correction with all retained gameplay tests."""
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
import build_reopen_startup_repair_apk as derivative
import qualify_levelup_ui_repair as prior
import qualify_startup_schedule as closure

TEST_MODULES = prior.TEST_MODULES + ('test_reopen_startup_repair_package', 'test_reopen_dbserver_thread_name')
CHECK_SUITES = {
    'native_startup_formatting_and_postgresql_contracts_verified': ['test_reopen_dbserver_thread_name', 'test_levelup_ui_repair_dbserver', 'test_startup_bundle_save'],
    'all_public_ui_client_server_cache_and_android_payloads_retained': ['test_reopen_startup_repair_package', 'test_client_ui_repair_assets',
        'test_client_preload_launch', 'test_classify_storage_cleanup_change', 'test_classify_interactive_change'],
    'current_typed_native_producer_and_guest_witness_verified': ['test_levelup_ui_repair_contract', 'test_levelup_ui_repair_dbserver',
        'test_reopen_startup_repair_package'],
    'retained_gameplay_save_training_and_preload_regressions_verified': list(prior.TEST_MODULES),
}


def source_paths(donor):
    names = set(donor['qualification']['source_files']) | set(derivative.SOURCE_FILES)
    names.update(Path(importlib.import_module(name).__file__).relative_to(ROOT).as_posix() for name in TEST_MODULES)
    producer = derivative.prior.native_builder(); names.update(producer.SOURCE_FILES)
    names.update('upstream/ouroboros/'+name for name in producer.expected_receipt()['source_sha256'])
    fixture = importlib.import_module('test_reopen_dbserver_thread_name')
    names.update('upstream/ouroboros/'+getattr(fixture, name) for name in
        ('THREAD_SOURCE', 'QUICK_SOURCE', 'ESTRING_SOURCE', 'ESTRING_HEADER', 'TASK_SOURCE'))
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


def qualification_checks(results):
    registered = set(TEST_MODULES)
    derivative.require(len(registered) == len(TEST_MODULES) and set(results) == registered and
        set(CHECK_SUITES) == set(derivative.CHECKS) and
        all(suites and set(suites) <= registered for suites in CHECK_SUITES.values()), 'Exact suite inventory required')
    return {name: all(results[suite]['status'] == 'passed' and results[suite]['skipped'] == 0 and
        results[suite]['tests_run'] > 0 for suite in suites) for name, suites in CHECK_SUITES.items()}


def qualify(args):
    if hasattr(time, 'tzset'): os.environ['TZ'] = 'UTC'; time.tzset()
    base = derivative.builder(); commit = base.source_commit(args.repository_commit)
    donor = derivative.validate_donor(args.donor_apk, args.donor_build_report)
    java = derivative.current_sources(donor)
    native = derivative.validate_native(args.dbserver_directory, commit, donor)
    pins = {name: base.file_pin(ROOT/name) for name in source_paths(donor)}
    results = regressions()
    save = importlib.import_module('test_startup_bundle_save')
    derivative.require(save.REQUIRE_POSTGRESQL is True and save.POSTGRES_FIXTURES_RUN ==
        {'cancelled_child_deletion_commits', 'duplicate_insert_23505_rollback', 'delete_insert_replacement_commits'},
        'All three real PostgreSQL retained fixtures required')
    repaired = importlib.import_module('test_levelup_ui_repair_dbserver')
    derivative.require(repaired.REQUIRE_POSTGRESQL is True and repaired.POSTGRES_FIXTURES_RUN == repaired.REQUIRED_POSTGRES_FIXTURES,
        'Every real PostgreSQL level-up fixture required')
    formatter = importlib.import_module('test_reopen_dbserver_thread_name')
    derivative.require(formatter.THREAD_NAME_FIXTURES_RUN == formatter.REQUIRED_THREAD_NAME_FIXTURES,
        'Every compiled production thread-name formatting fixture required')
    for name, pin in pins.items(): base.checked_file(ROOT/name, pin)
    checks = qualification_checks(results)
    receipt = {'format': 1, 'status': 'passed' if all(checks.values()) else 'failed', 'scope': derivative.QUALIFICATION_SCOPE,
        'repository_commit': commit, 'donor': derivative.donor_link(), 'source_files': pins,
        'test_suites': results, 'check_suites': CHECK_SUITES, 'checks': checks,
        'tests_run': sum(item['tests_run'] for item in results.values()),
        'native_dbserver_compiled_in_current_run': True, 'native_dbserver_package_reused': False,
        'native_client_recompiled': False, 'native_mapserver_recompiled': False, 'java_or_dex_recompiled': False,
        'asset_reimport_required': False, 'physical_reopen_validated': False, 'physical_gameplay_validated': False,
        'physical_client_timing_validated': False, 'physical_visual_assets_validated': False,
        'native_levelup_ui_repair': native, 'authored_java_sources_verified': len(java),
        'retained_baseline_payloads_verified': 72, 'retained_visual_leaves': 9613,
        'all_published_ui_resources_retained': True,
        'guest_witness_delta': derivative.validate_guest_delta(donor['_server_guest_source'], (ROOT/'android/guest'/derivative.GUEST).read_bytes()),
        'startup_thread_name_fixtures': sorted(formatter.THREAD_NAME_FIXTURES_RUN),
        'postgresql_emission_fixtures': sorted(save.POSTGRES_FIXTURES_RUN),
        'postgresql_levelup_fixtures': sorted(repaired.POSTGRES_FIXTURES_RUN),
        'performance_claim_scope': 'Compiled production startup formatting and real PostgreSQL fixtures plus full host regressions. '
            'The published UI, Game, MapServer, caches, Java, DEX and resources retain byte identity. Physical reopen, training and timing remain pending.'}
    derivative.validate_qualification(receipt, commit)
    derivative.require(not args.output.exists() and not args.output.is_symlink(), 'Fresh qualification output required')
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(receipt, indent=2)+'\n')
    print('Qualified native startup repair:', receipt['tests_run'], 'host scenarios; physical validation pending')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository-commit', required=True)
    for name in ('donor-apk', 'donor-build-report', 'dbserver-directory', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    qualify(parser.parse_args())


if __name__ == '__main__': main()
