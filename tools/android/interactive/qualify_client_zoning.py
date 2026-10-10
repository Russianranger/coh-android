#!/usr/bin/env python3
"""Qualify owned Atlas instance zoning while preserving all .25 regression gates."""
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
    str(ROOT/'tools'), str(ROOT/'android/guest'), str(ROOT/'database/postgresql/tests')]
import build_client_zoning_apk as derivative
import qualify_client_render_queue as previous
import qualify_startup_schedule as closure

RETAINED_TEST_MODULES = previous.TEST_MODULES
NEW_TEST_MODULES = ('test_character_zoning','test_client_zoning_java','test_client_zoning_package',
    'test_prepare_resume_client_source','test_character_transfer')
TEST_MODULES = RETAINED_TEST_MODULES + NEW_TEST_MODULES
CHECK_SUITES = {
    'owned_zoning_transfer_recovery_and_input_guards_verified':list(NEW_TEST_MODULES),
    'retained_gameplay_postgresql_gpu_cleanup_and_recovery_guards_verified':list(RETAINED_TEST_MODULES),
    'exact_025_native_graphics_assets_and_reviewed_shell_verified':[
        'test_client_zoning_package','test_client_render_queue_contract','test_setup_copy_memory',
        'test_setup_io_memory','test_client_gpu_profile','test_client_gpu_repair_package'],
}


def validate_suite_inventory():
    derivative.require(RETAINED_TEST_MODULES == previous.TEST_MODULES and len(RETAINED_TEST_MODULES) == 117
        and TEST_MODULES[:117] == RETAINED_TEST_MODULES and len(TEST_MODULES) == 122
        and len(set(TEST_MODULES)) == len(TEST_MODULES) and set(CHECK_SUITES) == set(derivative.CHECKS)
        and all(values and set(values) <= set(TEST_MODULES) for values in CHECK_SUITES.values()),
        'All retained .25 suites and focused current zoning/source-transfer gates required')


def source_paths(donor):
    names = set(donor['qualification']['source_files']) | set(derivative.SOURCE_FILES)
    names.update(Path(importlib.import_module(name).__file__).relative_to(ROOT).as_posix() for name in TEST_MODULES)
    # The unchanged native map contract reads these non-import source inputs.
    transfer = importlib.import_module('character_transfer').source_contract()
    names.add('upstream/i24/data/server/db/maps.db')
    names.update('upstream/ouroboros/'+name for name in transfer['source_sha256'])
    return sorted(closure.source_closure(names))


def regressions():
    validate_suite_inventory(); results = {}
    for name in TEST_MODULES:
        suite = unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(name))
        derivative.require(suite.countTestCases() > 0,name+' has no scenarios')
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured),contextlib.redirect_stderr(captured):
            result = unittest.TextTestRunner(stream=captured,verbosity=2).run(suite)
        output = captured.getvalue()
        derivative.require(len(output.encode()) <= 262144,'Unbounded qualification output: '+name)
        derivative.require(result.wasSuccessful() and not result.skipped,name+' failed or skipped:\n'+output)
        print(name+': '+str(result.testsRun)+' passed; no skips',flush=True)
        results[name] = {'tests_run':result.testsRun,'status':'passed','skipped':0}
    return results


def qualify(args):
    if hasattr(time,'tzset'): os.environ['TZ'] = 'UTC'; time.tzset()
    validate_suite_inventory(); base = derivative.builder(); commit = base.source_commit(args.repository_commit)
    donor = derivative.validate_donor(args.donor_apk,args.donor_build_report,args.retained_client_directory)
    _,java,changed = derivative.current_java_sources(donor,ROOT/'out/no-generated-java')
    native = derivative.validate_retained_native(args.retained_client_directory,donor)
    ancestry = derivative.validate_actual_native_ancestry(donor,native)
    pins = {name:base.file_pin(ROOT/name) for name in source_paths(donor)}
    results = regressions()
    save = importlib.import_module('test_startup_bundle_save')
    derivative.require(save.REQUIRE_POSTGRESQL is True and save.POSTGRES_FIXTURES_RUN ==
        {'cancelled_child_deletion_commits','duplicate_insert_23505_rollback','delete_insert_replacement_commits'},
        'All retained real PostgreSQL emission fixtures required')
    repaired = importlib.import_module('test_levelup_ui_repair_dbserver')
    derivative.require(repaired.REQUIRE_POSTGRESQL is True and repaired.POSTGRES_FIXTURES_RUN == repaired.REQUIRED_POSTGRES_FIXTURES,
        'All retained real PostgreSQL level-up fixtures required')
    for name,expected in pins.items(): base.checked_file(ROOT/name,expected)
    checks = {name:all(results[suite]['status'] == 'passed' and results[suite]['skipped'] == 0 and results[suite]['tests_run'] > 0
        for suite in suites) for name,suites in CHECK_SUITES.items()}
    receipt = {'format':1,'status':'passed' if all(checks.values()) else 'failed','scope':derivative.QUALIFICATION_SCOPE,
        'repository_commit':commit,'runtime_repository_commit':commit,'donor':derivative.donor_link(),
        'source_files':pins,'test_suites':results,'check_suites':CHECK_SUITES,'checks':checks,
        'tests_run':sum(value['tests_run'] for value in results.values()),'java_sources':java,
        'changed_java_sources':changed,'added_java_sources':sorted(derivative.JAVA_ADDITIONS),
        'retained_java_sources_verified':19-len(derivative.JAVA_CHANGES),'authored_java_sources_verified':19+len(derivative.JAVA_ADDITIONS),
        'postgresql_emission_fixtures':sorted(save.POSTGRES_FIXTURES_RUN),
        'postgresql_levelup_fixtures':sorted(repaired.POSTGRES_FIXTURES_RUN),
        'server_payload_extraction_preflight':donor['server_payload_extraction_preflight'],'baseline_payloads_verified':77,
        'native_client_render_queue':native,'native_build_provenance':donor['native_build_provenance'],
        'publication_provenance':derivative.publication_provenance(commit),'client_gpu_runtime':donor['client_gpu_runtime'],
        'actual_native_ancestry_validation':ancestry,'client_zoning':derivative.zoning_contract(),
        **dict.fromkeys(derivative.FALSE_FLAGS,False),**dict.fromkeys(derivative.TRUE_FLAGS,True),
        'claim_scope':'Host qualification covers owned Atlas instance transfer controls, identity/endpoint/readiness and '
            'interruption guards, unchanged original Game/Win32/source proofs and native transfer callsite fixtures, '
            'retained graphics/server/assets and all seven real PostgreSQL persistence fixtures. User-observed .25 FPS '
            'improvement is recorded separately. Physical .26 round-trip, save/reopen and transition duration require AYN Thor testing.'}
    derivative.validate_qualification(receipt,commit,donor)
    derivative.require(not args.output.exists() and not args.output.is_symlink(),'Fresh qualification output required')
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print('Qualified Atlas instance zoning:',receipt['tests_run'],'host scenarios; physical transfer remains pending')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--repository-commit',required=True)
    for name in ('donor-apk','donor-build-report','retained-client-directory','output'): parser.add_argument('--'+name,type=Path,required=True)
    qualify(parser.parse_args())


if __name__ == '__main__': main()
