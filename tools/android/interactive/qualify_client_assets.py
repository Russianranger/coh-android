#!/usr/bin/env python3
"""Qualify external assets and Kings Row while preserving every retained .27 gate."""
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
    str(ROOT/'tools'), str(ROOT/'android/guest'), str(ROOT/'database/postgresql/tests'),str(ROOT/'tools/android/game')]
import build_client_assets_apk as derivative
import qualify_client_recovery as previous
import qualify_startup_schedule as closure

RETAINED_TEST_MODULES = previous.TEST_MODULES
NEW_TEST_MODULES = ('test_external_assets','test_asset_pack_import','test_storage_files','test_client_assets_package','test_client_monorail_java','test_shared_asset_inputs',
    'test_kings_row_beacons','test_monorail_native_package','test_prepare_kings_row_beacon_generator_source',
    'test_character_monorail','test_monorail_observer','test_zone_asset_package','test_zones_world_assets','test_classify_client_assets_change','test_zones_audio_assets')
TEST_MODULES = RETAINED_TEST_MODULES + NEW_TEST_MODULES
CHECK_SUITES = {
    'external_asset_import_storage_and_monorail_guards_verified':list(NEW_TEST_MODULES),
    'retained_gameplay_postgresql_gpu_cleanup_and_recovery_guards_verified':list(RETAINED_TEST_MODULES),
    'exact_027_native_graphics_assets_and_reviewed_shell_verified':[
        'test_client_assets_package','test_client_render_queue_contract','test_setup_copy_memory',
        'test_setup_io_memory','test_client_gpu_profile','test_client_gpu_repair_package'],
}


def validate_suite_inventory():
    derivative.require(RETAINED_TEST_MODULES == previous.TEST_MODULES and len(RETAINED_TEST_MODULES) == 128
        and TEST_MODULES[:128] == RETAINED_TEST_MODULES and len(TEST_MODULES) == 128+len(NEW_TEST_MODULES)
        and len(set(TEST_MODULES)) == len(TEST_MODULES) and set(CHECK_SUITES) == set(derivative.CHECKS)
        and all(values and set(values) <= set(TEST_MODULES) for values in CHECK_SUITES.values()),
        'All retained .27 suites and current external asset/storage/monorail gates required')


def source_paths(donor):
    names = set(donor['qualification']['source_files']) | set(derivative.SOURCE_FILES)
    import package_monorail_native, generate_kings_row_beacons
    names.update(package_monorail_native.SOURCE_FILES)
    names.update(generate_kings_row_beacons.SOURCE_FILES)
    names.add('tools/android/game/test_monorail.py')
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
    import tempfile
    with tempfile.TemporaryDirectory(prefix='coh-assets-qualification-') as temporary:
        runtime,payloads,preflight = derivative.extract_and_repair(args.donor_apk,donor,Path(temporary)/'donor',commit,args.asset_directory,args.monorail_directory,args.native_commit)
    asset_manifest = derivative.asset_contract(args.asset_directory,verify_volumes=True)
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
        'retained_java_sources_verified':derivative.DONOR_JAVA_COUNT-len(derivative.JAVA_CHANGES),'authored_java_sources_verified':derivative.DONOR_JAVA_COUNT+len(derivative.JAVA_ADDITIONS),
        'postgresql_emission_fixtures':sorted(save.POSTGRES_FIXTURES_RUN),
        'postgresql_levelup_fixtures':sorted(repaired.POSTGRES_FIXTURES_RUN),
        'server_payload_extraction_preflight':preflight,'external_asset_pack':asset_manifest,'baseline_payloads_verified':derivative.BASELINE_PAYLOAD_COUNT,
        'native_client_render_queue':native,'native_build_provenance':donor['native_build_provenance'],
        'publication_provenance':derivative.publication_provenance(commit),'client_gpu_runtime':donor['client_gpu_runtime'],
        'actual_native_ancestry_validation':ancestry,'client_assets':derivative.recovery_contract(),
        'runtime_profile':dict(derivative.RECOVERY_PROFILE),
        **dict.fromkeys(derivative.FALSE_FLAGS,False),**dict.fromkeys(derivative.TRUE_FLAGS,True),
        'claim_scope':'Host qualification covers versioned external asset volumes, bounded import, inode storage accounting, '
            'retained regressions and native MapServer monorail provenance. Game, graphics and DbServer remain exact. '
            'Physical Kings Row travel, preparation duration, FPS and final character save still require device evidence.'}


    derivative.validate_qualification(receipt,commit,donor)
    derivative.require(not args.output.exists() and not args.output.is_symlink(),'Fresh qualification output required')
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print('Qualified external assets and monorail:',receipt['tests_run'],'host scenarios; physical Kings Row travel and loading latency remain pending')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--repository-commit',required=True)
    for name in ('donor-apk','donor-build-report','retained-client-directory','asset-directory','monorail-directory','output'): parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--native-commit',required=True)
    qualify(parser.parse_args())


if __name__ == '__main__': main()
