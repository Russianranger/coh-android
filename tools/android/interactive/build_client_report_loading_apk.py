#!/usr/bin/env python3
"""Exact public .32 derivative for recoverable reports and bounded warm preparation.

No native archive, FX/catalog/certificate, GPU, Wine/FEX, Android resource or
Assets 1.0.0 byte changes. Only four reviewed Java sources and three guest
helpers plus enclosing manifests may change. Host gates do not claim Thor
performance; the published donor's native producer ownership remains opaque.
"""
from __future__ import annotations
import argparse
import copy
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile

import build_client_map_startup_apk as previous

ROOT, require, module, shared = previous.ROOT, previous.require, previous.module, previous.shared
REPOSITORY, BRANCH, SIGNER, retained = previous.REPOSITORY, previous.BRANCH, previous.SIGNER, previous.retained
read_json, pin, typed_equal = previous.read_json, previous.pin, previous.typed_equal
bounded_download, authenticated_artifact_download = previous.bounded_download, previous.authenticated_artifact_download
DONOR_COMMIT, DONOR_RUN_ID = '6c4d1d74f34ecdea8fabcf6238368bf72003878f', 38205495073
DONOR_APK_NAME = 'COH-Atlas-Gameplay-0.13.32.apk'
DONOR_APK = {'bytes': 42031636, 'sha256': '8995ecef2622a7720b0ef296b0960a79cc2e914a5da2a9078379ff66732b2839'}
DONOR_REPORT_NAME = 'client-map-startup-apk-build-report.json'
DONOR_BUILD = {'bytes': 8175633, 'sha256': '88428c1423185d1e8c2efd7821f4fbbd742bbf85b79d82dd6d85ad169ddc0d04'}
DONOR_EVIDENCE_ID = 11728362979
DONOR_EVIDENCE = {'bytes': 50222978, 'sha256': 'f5d4215efed83ae5c72fd569780abaa4b4d86e71cf34f9c0fb1049a9369be563'}
DONOR_EVIDENCE_ARCHIVE = 'published-0.13.32-packaging-evidence.zip'
DONOR_EVIDENCE_NAMES = frozenset({DONOR_REPORT_NAME, DONOR_APK_NAME, DONOR_APK_NAME+'.sha256',
    'COH-Atlas-Gameplay-0.13.32-testing.txt'})
DONOR_URL = 'https://github.com/'+REPOSITORY+'/releases/download/coh-atlas-gameplay-v0.13.32/'+DONOR_APK_NAME
DONOR_PUBLIC_AUDIT_ID = 11729652485
DONOR_PUBLIC_AUDIT = {'bytes': 701, 'sha256': '5217deb28e07a8b531c90d0e7af2e09e75389d397de579899f568d4496a6d95b'}
DONOR_PUBLIC_AUDIT_RECEIPT = {'bytes': 1080, 'sha256': '8af498476f28b82e3d615649cc1cce3514390f7a883086e3dd03069c65e3298a'}
ASSET_BUILD = previous.ASSET_BUILD
VERSION_NAME, VERSION_CODE = '0.13.33', 48
APK_NAME, REPORT_NAME = 'COH-Atlas-Gameplay-0.13.33.apk', 'client-report-loading-apk-build-report.json'
CLIENT_APK_AUDIT_NAME = 'client-report-loading-apk-audit.json'
NOTES_NAME, RELEASE_TAG = 'COH-Atlas-Gameplay-0.13.33-testing.txt', 'coh-atlas-gameplay-v0.13.33'
NOTES = ROOT/'docs'/NOTES_NAME
WORKFLOW = '.github/workflows/android-client-report-loading.yml'
QUALIFICATION_SCRIPT = 'tools/android/interactive/qualify_client_report_loading.py'
QUALIFICATION_SCOPE = 'report_finalization_and_warm_preparation_repair_retaining_exact_032_native_gpu_and_assets'
MARKER = 'tools/android/interactive/release-client-report-loading-0.13.33.json'
REVIEWED_JAVA_CHANGES = frozenset('android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/'+name+'.java'
    for name in ('ClientActivity', 'ClientService', 'ClientRuntime')) | frozenset({
    'android/recovery/src/main/java/io/github/russianranger/cohclientinteractive/ClientReports.java'})
GUEST_SOURCE_CHANGES = frozenset('android/guest/'+name for name in (
    'atlas_beacon_package.py', 'kings_row_beacon_package.py', 'local_character_server.py'))
ADDED_PAYLOADS = frozenset()
CHECKS = ('retained_regressions_and_postgresql_verified', 'actual_runtime_asset_installers_verified',
    'full_startup_orchestration_verified', 'report_finalization_and_recovery_verified',
    'warm_preparation_reuse_verified', 'exact_032_native_graphics_and_assets_verified')
FALSE_FLAGS = ('native_client_recompiled', 'native_mapserver_recompiled', 'native_dbserver_recompiled',
    'graphics_driver_changed', 'wine_or_fex_changed', 'world_assets_changed', 'asset_reimport_required',
    'native_runtime_booted', 'save_acceptance_relaxed', 'physical_recovery_validated',
    'physical_kings_row_zoning_validated', 'physical_fps_gain_validated',
    'physical_map_startup_speedup_validated', 'sub_30_second_map_startup_validated')
TRUE_FLAGS = ('retained_android_resources_verified', 'all_native_member_bytes_retained',
    'retained_game_and_dbserver_verified', 'external_assets_1_0_0_reused',
    'serialized_game_receipts_verified', 'runtime_refresh_required', 'guest_helpers_changed',
    'actual_runtime_asset_installers_verified', 'java_or_dex_recompiled',
    'full_startup_orchestration_verified', 'retained_032_map_startup_component_verified')
REVIEWED_TEST_CHANGES = frozenset('tools/android/interactive/'+name+'.py' for name in (
    'test_client_report_lifecycle_java', 'test_client_report_recovery_java',
    'test_client_report_controls_java', 'test_collision_input_snapshot',
    'test_shared_collision_input_proof', 'test_profile_failure_presentation',
    'test_map_startup_observation',
    'test_storage_ui', 'test_storage_recovery_ui', 'test_fresh_profile_recovery',
    'test_classify_storage_cleanup_change'))
ROUTING_SOURCE_CHANGES = frozenset({
    'tools/android/interactive/classify_client_animation_repair_change.py',
    'tools/android/interactive/classify_client_profile_recovery_change.py',
    'tools/android/interactive/classify_client_map_startup_change.py',
    'tools/qualify_map_startup_prerequisites.py',
    'tools/test_qualify_map_startup_prerequisites.py',
    '.github/workflows/map-startup-prerequisites.yml'})
SOURCE_FILES = frozenset({WORKFLOW, QUALIFICATION_SCRIPT, MARKER, 'docs/'+NOTES_NAME,
    'tools/android/interactive/build_client_report_loading_apk.py',
    'tools/android/interactive/test_client_report_loading_package.py',
    'tools/android/interactive/classify_client_report_loading_change.py'}) | REVIEWED_JAVA_CHANGES | GUEST_SOURCE_CHANGES | REVIEWED_TEST_CHANGES | ROUTING_SOURCE_CHANGES
REVIEWED_DONOR_SOURCE_CHANGES = REVIEWED_JAVA_CHANGES | GUEST_SOURCE_CHANGES | REVIEWED_TEST_CHANGES | ROUTING_SOURCE_CHANGES

def builder(*, repaired=False):
    result = previous.builder()
    if repaired:
        result.VERSION_NAME, result.VERSION_CODE, result.APK_NAME = VERSION_NAME, VERSION_CODE, APK_NAME
    return result


def donor_link():
    return {'run_id': DONOR_RUN_ID, 'repository_commit': DONOR_COMMIT, 'apk': DONOR_APK,
        'build_report': DONOR_BUILD, 'build_report_artifact_id': DONOR_EVIDENCE_ID,
        'build_report_artifact_zip': DONOR_EVIDENCE,
        'public_byte_audit_artifact_id': DONOR_PUBLIC_AUDIT_ID,
        'public_byte_audit_artifact_zip': DONOR_PUBLIC_AUDIT}


def publication_provenance(commit):
    owner = os.environ.get('GITHUB_RUN_ID')
    require(owner is None or re.fullmatch('[1-9][0-9]*', owner), 'Exact publication owner required')
    return {'format': 1, 'repository_commit': commit, 'donor_repository_commit': DONOR_COMMIT,
        'run_url': 'https://github.com/'+REPOSITORY+'/actions/runs/'+owner if owner else None,
        'native_producer_relabelled': False, 'asset_release_republished': False}


def current_sources(donor):
    base = builder()
    java = {name: base.file_pin(ROOT/name) for name in donor['java_sources']}
    require(len(java) == 24 and set(java) == set(donor['java_sources'])
        and {name for name in java if java[name] != donor['java_sources'][name]} == REVIEWED_JAVA_CHANGES,
        'Exactly the four reviewed report/lifecycle/control Java repairs are required')
    for name, expected in donor['payloads'].items():
        if name.startswith('assets/runtime/') and name.endswith('.py'):
            source = 'android/guest/'+Path(name).name
            if source not in GUEST_SOURCE_CHANGES: base.checked_file(ROOT/source, expected)
    for name, expected in donor['qualification']['source_files'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts and '\\' not in name,
                'Unsafe retained source path')
        if name not in REVIEWED_DONOR_SOURCE_CHANGES: base.checked_file(ROOT/name, expected)
    # Native producer recipes keep their original ownership. We do not rerun,
    # recompute or relabel the .32 native/FX component under current helpers.
    for name, expected in donor['native_build_provenance']['source_files'].items():
        base.checked_file(ROOT/name, expected)
    base.checked_file(ROOT/'android/interactive/src/main/AndroidManifest.xml',
        donor['qualification']['source_files']['android/interactive/src/main/AndroidManifest.xml'])
    return java


def changed_java_sources(donor):
    return sorted(name for name, expected in current_sources(donor).items()
                  if expected != donor['java_sources'][name])


def replacement_payloads(donor):
    changed = {'assets/runtime/client-manifest.json', 'assets/runtime/runtime-manifest.json'}
    for source in GUEST_SOURCE_CHANGES:
        target = 'assets/runtime/'+Path(source).name
        if builder().file_pin(ROOT/source) != donor['payloads'][target]: changed.add(target)
    require({Path(name).name for name in changed} >= {Path(name).name for name in GUEST_SOURCE_CHANGES},
            'Each reviewed preparation/telemetry guest helper must actually change')
    return frozenset(changed)


def validate_donor(apk, receipt):
    base = builder(); base.checked_file(apk, DONOR_APK); base.checked_file(receipt, DONOR_BUILD)
    donor = read_json(receipt)
    require(donor['repository_commit'] == donor['runtime_repository_commit'] == DONOR_COMMIT
        and donor['apk'] == DONOR_APK_NAME and donor['version_name'] == '0.13.32' and donor['version_code'] == 47
        and {key: donor[key] for key in ('bytes', 'sha256')} == DONOR_APK
        and donor['signer_certificate_sha256'] == SIGNER and donor['signature_verified'] is True
        and donor['external_asset_release_tag'] == 'coh-assets-v1.0.0' and donor['asset_pack_version'] == '1.0.0'
        and donor['publication_provenance']['run_url'] == 'https://github.com/'+REPOSITORY+'/actions/runs/'+str(DONOR_RUN_ID),
        'Exact accepted public .32 donor identity required')
    require(len(donor['payloads']) == 74 and donor['native_mapserver_recompiled'] is True
        and donor['native_animation_and_fx_component_fixtures_verified'] is True,
        'Exact certified .32 payload/native component inventory required')
    with zipfile.ZipFile(apk) as archive:
        shell = {'classes.dex': donor['recompiled_dex'], **donor['retained_android_resources']}
        require(retained.archive_inventory(archive) == set(donor['payloads']) | set(shell) | {'AndroidManifest.xml'},
                'Donor APK inventory differs')
        for name, expected in {**donor['payloads'], **shell}.items():
            require(pin(archive.read(name)) == expected, 'Donor APK member differs: '+name)
        donor['_client_verification'] = json.loads(archive.read('assets/runtime/client-manifest.json'))
        require(typed_equal(json.loads(archive.read('assets/runtime/runtime-manifest.json')), donor['runtime_manifest']),
                'Donor runtime receipt differs from authenticated bytes')
        require(json.loads(archive.read('assets/runtime/asset-pack-manifest.json')) == donor['external_asset_pack'],
                'Retained asset descriptor differs')
    donor['_apk_path'] = Path(apk)
    require(retained.verify_apk_server_archives(apk) == donor['package_preflight']['server_archives'],
            'Authenticated .32 native archive receipt differs')
    current_sources(donor)
    return donor


def payload_boundaries(payloads, donor):
    require(set(payloads) == set(donor['payloads']) and len(payloads) == 74
        and {name for name in payloads if payloads[name] != donor['payloads'][name]} == replacement_payloads(donor),
        'Only reviewed guest helpers and their two enclosing manifests may change')


def verification_manifests(donor, helper_pins, commit):
    require(set(helper_pins) == {Path(name).name for name in GUEST_SOURCE_CHANGES},
            'Exact three reviewed guest helper pins required')
    require(helper_pins == {Path(name).name: builder().file_pin(ROOT/name) for name in GUEST_SOURCE_CHANGES},
            'Reviewed helper pins must match actual candidate source bytes')
    helper_pins = {name: helper_pins[name] for name in sorted(helper_pins)}
    client = copy.deepcopy(donor['_client_verification']); client['files'].update(helper_pins)
    runtime = copy.deepcopy(donor['runtime_manifest']); runtime['files'].update(helper_pins)
    runtime['files']['client-manifest.json'] = pin(shared.encoded(client))
    runtime.update(repository_commit=commit, scope=QUALIFICATION_SCOPE)
    runtime['client_report_loading'] = {'format': 1, 'repository_commit': commit,
        'donor_repository_commit': DONOR_COMMIT, 'publication_provenance': publication_provenance(commit),
        'reviewed_guest_inputs': helper_pins,
        **dict.fromkeys(FALSE_FLAGS, False), **dict.fromkeys(TRUE_FLAGS, True)}
    require(typed_equal(runtime['client_map_startup'], donor['runtime_manifest']['client_map_startup'])
        and typed_equal(runtime['client_bundle'], donor['runtime_manifest']['client_bundle'])
        and runtime['external_asset_pack'] == donor['runtime_manifest']['external_asset_pack'],
        'Existing native ancestry and installed asset descriptor must remain exact')
    return client, runtime


actual_asset_preflight = previous.actual_asset_preflight
actual_startup_preflight = previous.actual_startup_preflight


def extract_and_repair(apk, donor, destination, commit, *, execute_preflight=True):
    destination = Path(destination); destination.mkdir(parents=True)
    base = builder()
    with zipfile.ZipFile(apk) as archive:
        for name in sorted(set(donor['payloads']) | {'classes.dex'} | set(donor['retained_android_resources'])):
            target = destination/name; target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(name) as source, target.open('xb') as output:
                shutil.copyfileobj(source, output, 1024*1024)
    for name, expected in donor['payloads'].items(): base.checked_file(destination/name, expected)
    assets = destination/'assets/runtime'; helper_pins = {}
    for source in sorted(GUEST_SOURCE_CHANGES):
        target = assets/Path(source).name; base.checked_file(ROOT/source)
        target.write_bytes((ROOT/source).read_bytes()); helper_pins[target.name] = base.file_pin(target)
    client, runtime = verification_manifests(donor, helper_pins, commit)
    for name, value in (('client-manifest.json', client), ('runtime-manifest.json', runtime)):
        (assets/name).write_bytes(shared.encoded(value))
    payloads = {name: base.file_pin(destination/name) for name in sorted(donor['payloads'])}
    payload_boundaries(payloads, donor)
    server = retained.verify_server_archives(assets)
    require(typed_equal(server, donor['package_preflight']['server_archives']),
            'Every accepted .32 Game/Map/DbServer/schema archive must remain exact')
    preflight = {'server_archives': server, 'map_startup_component': copy.deepcopy(donor['map_startup_component'])}
    if execute_preflight:
        preflight.update(runtime_assets=actual_asset_preflight(assets), full_startup=actual_startup_preflight(assets))
    return runtime, payloads, preflight


def validate_qualification(q, commit, donor):
    contract = module('report_loading_qualification_contract', ROOT/QUALIFICATION_SCRIPT)
    contract.validate_suite_inventory()
    require(type(q.get('format')) is int and q['format'] == 1 and q.get('status') == 'passed'
        and q.get('scope') == QUALIFICATION_SCOPE
        and q.get('repository_commit') == q.get('runtime_repository_commit') == commit
        and q.get('donor') == donor_link()
        and typed_equal(q.get('map_startup_component'), donor['map_startup_component'])
        and q.get('java_sources') == current_sources(donor)
        and q.get('donor_dex') == donor['recompiled_dex']
        and q.get('changed_java_sources') == changed_java_sources(donor)
        and q.get('external_asset_pack') == donor['external_asset_pack']
        and q.get('native_build_provenance') == donor['native_build_provenance']
        and q.get('check_suites') == contract.CHECK_SUITES and set(q.get('checks', {})) == set(CHECKS)
        and all(q['checks'][name] is True for name in CHECKS)
        and all(q.get(name) is False for name in FALSE_FLAGS)
        and all(q.get(name) is True for name in TRUE_FLAGS),
        'Exact report/loading and retained .32 qualification required')
    suites = q.get('test_suites', {})
    require(set(suites) == set(contract.TEST_MODULES) and all(row.get('status') == 'passed'
        and row.get('skipped') == 0 and type(row.get('tests_run')) is int and row['tests_run'] > 0
        for row in suites.values()) and type(q.get('tests_run')) is int
        and q.get('tests_run') == sum(row['tests_run'] for row in suites.values()),
        'Every retained and current regression suite must pass without skips')
    for name, row in suites.items():
        if name in contract.RETAINED_CONTRACT_MODULES:
            require(typed_equal(row, contract.retained_contract_result(name, donor)),
                'Historical package/native results require exact accepted .32 donor attribution')
        else:
            contract.validate_current_suite_result(name, row)
    require(type(q.get('current_tests_run')) is int and type(q.get('inherited_tests_retained')) is int
        and q.get('current_tests_run') == sum(row['tests_run'] for row in suites.values()
            if row['tests_executed_in_current_run'])
        and q.get('inherited_tests_retained') == sum(row['tests_run'] for row in suites.values()
            if not row['tests_executed_in_current_run']),
        'Current execution and inherited evidence counts must remain separate')
    require(type(q.get('current_suites_run')) is int and type(q.get('inherited_suites_retained')) is int
        and q['current_suites_run'] == len(contract.TEST_MODULES)-len(contract.RETAINED_CONTRACT_MODULES)
        and q['inherited_suites_retained'] == len(contract.RETAINED_CONTRACT_MODULES),
        'Current suite execution and unchanged producer evidence must remain separate')
    require(q.get('postgresql_emission_fixtures') == sorted((
        'cancelled_child_deletion_commits', 'duplicate_insert_23505_rollback', 'delete_insert_replacement_commits'))
        and q.get('postgresql_levelup_fixtures') == sorted(retained.levelup_postgresql_fixtures()),
        'All seven real PostgreSQL fixtures required')
    import test_character_profile_eligibility as profile
    require(q.get('postgresql_profile_eligibility_fixtures') == sorted(profile.REQUIRED_POSTGRES_FIXTURES)
        and len(q['postgresql_profile_eligibility_fixtures']) == 14,
        'All fourteen PostgreSQL recovery/preservation fixtures required')
    require(set(q.get('source_files', {})) == set(contract.source_paths(donor)),
            'Exact qualified source closure required')
    for name, expected in q['source_files'].items(): builder().checked_file(ROOT/name, expected)
    require(type(q.get('package_preflight')) is dict, 'Actual serialized package preflight required')
    require(typed_equal(q['package_preflight'].get('server_archives'), donor['package_preflight']['server_archives'])
        and typed_equal(q['package_preflight'].get('map_startup_component'), donor['map_startup_component']),
        'Accepted .32 native archive and component provenance must remain exact')
    full = q['package_preflight'].get('full_startup', {})
    import qualify_full_startup_preflight as startup
    startup.validate_proof(full)
    require(full.get('status') == 'passed' and full.get('scope') == 'actual_packaged_guest_full_startup_orchestration'
        and all(full.get(name) is True for name in ('full_private_worktree_mirror_executed',
            'full_prepare_runtime_executed', 'fresh_create_cold_preparation_verified',
            'saved_reopen_warm_preparation_verified', 'full_kings_row_cold_and_reuse_preparation_verified'))
        and full.get('native_runtime_booted') is False and full.get('physical_execution_validated') is False
        and full.get('process_and_sql_boundary') == 'not_executed',
        'Full host preparation required; native process and Thor boot cannot be claimed')
    return q


def verify_derivative(apk, donor, payloads, dex_pin, commit, *, execute_preflight=True):
    base = builder(); payload_boundaries(payloads, donor); base.verify_packaged_payloads(apk, payloads)
    require(dex_pin != donor['recompiled_dex'] and set(dex_pin) == {'bytes', 'sha256'},
            'Reviewed report/lifecycle Java must produce changed DEX')
    with zipfile.ZipFile(apk) as archive:
        shell = {'classes.dex': dex_pin, **donor['retained_android_resources']}
        require(retained.archive_inventory(archive) == set(payloads) | set(shell) | {'AndroidManifest.xml'},
                'Candidate APK inventory differs')
        for name, expected in shell.items(): require(pin(archive.read(name)) == expected, 'Candidate DEX/resources differ: '+name)
    with tempfile.TemporaryDirectory(prefix='coh-report-loading-reconstruction-') as temporary:
        runtime, expected, preflight = extract_and_repair(donor['_apk_path'], donor, Path(temporary)/'donor', commit,
                                                       execute_preflight=False)
        require(payloads == expected, 'Reconstructed public .32 plus reviewed helpers differs')
    require(retained.verify_apk_server_archives(apk) == preflight['server_archives'],
            'Actual signed APK native archive extraction differs')
    # Execute the final signed APK's actual guest bytes independently of the
    # expected-hash reconstruction, retaining nested receipt key order.
    if execute_preflight:
        with tempfile.TemporaryDirectory(prefix='coh-report-loading-actual-') as temporary, zipfile.ZipFile(apk) as archive:
            directory = Path(temporary)
            for name in sorted(payloads):
                if name.startswith('assets/runtime/'):
                    (directory/Path(name).name).write_bytes(archive.read(name))
            preflight.update(runtime_assets=actual_asset_preflight(directory), full_startup=actual_startup_preflight(directory))
    return runtime, preflight


def repair_android_manifest(source, destination):
    base = builder(); base.verify_source_manifest(source); tree = ET.parse(source)
    tree.getroot().set(base.ANDROID+'versionName', VERSION_NAME)
    tree.getroot().set(base.ANDROID+'versionCode', str(VERSION_CODE))
    ET.register_namespace('android', base.ANDROID[1:-1]); tree.write(destination, encoding='utf-8', xml_declaration=True)
    builder(repaired=True).verify_source_manifest(destination)


def compile_shell(args, donor, q, work):
    """Compile exactly the authenticated donor Java inventory plus reviewed edits."""
    base = builder()
    manifest = work/'AndroidManifest.xml'
    repair_android_manifest(ROOT/'android/interactive/src/main/AndroidManifest.xml', manifest)
    resources, unsigned = work/'resources.zip', work/'unsigned.apk'
    classes, generated, dex = (work/name for name in ('classes', 'generated', 'dex'))
    for directory in (classes, generated, dex): directory.mkdir()
    base.run(args.build_tools/'aapt2', 'compile', '--dir', ROOT/'android/interactive/src/main/res', '-o', resources)
    base.run(args.build_tools/'aapt2', 'link', '-I', args.android_jar, '--manifest', manifest,
        '--min-sdk-version', '26', '--target-sdk-version', '35', '--java', generated, resources, '-o', unsigned)
    with zipfile.ZipFile(unsigned) as archive:
        require(retained.archive_inventory(archive) == {'AndroidManifest.xml', *donor['retained_android_resources']},
                'Generated Android inventory differs')
        for name, expected in donor['retained_android_resources'].items():
            require(pin(archive.read(name)) == expected, 'Android resources changed')
    require({path.relative_to(generated).as_posix() for path in generated.rglob('*.java')} ==
        {base.APP_ID.replace('.', '/')+'/R.java'}, 'Unexpected generated Java source')
    java = current_sources(donor)
    require(q['java_sources'] == java and q['changed_java_sources'] == changed_java_sources(donor),
            'Java changed after qualification')
    sources = [ROOT/name for name in sorted(java)] + sorted(generated.rglob('*.java'))
    base.run('java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8', '-cp',
        args.android_jar, '-d', classes, *sources)
    class_jar = work/'classes.jar'
    with zipfile.ZipFile(class_jar, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(classes.rglob('*.class')): archive.write(path, path.relative_to(classes).as_posix())
    base.run('java', '-cp', args.build_tools/'lib/d8.jar', 'com.android.tools.r8.D8', '--min-api', '26',
        '--lib', args.android_jar, '--output', dex, class_jar)
    require({path.name for path in dex.iterdir()} == {'classes.dex'}, 'Unexpected DEX output')
    dex_path = dex/'classes.dex'
    require(base.file_pin(dex_path) != donor['recompiled_dex'], 'Reviewed Java DEX did not change')
    return unsigned, dex_path, java


def require_signed_preflight(preflight, qualification):
    require(typed_equal(preflight, qualification['package_preflight']),
            'Actual signed APK qualification differs')


def build(args):
    base, current = builder(), builder(repaired=True); commit = base.source_commit(args.repository_commit)
    require_source_identity(commit)
    donor = validate_donor(args.donor_apk, args.donor_build_report)
    q = validate_qualification(read_json(args.qualification), commit, donor)
    password = base.signing_password_spec(args.password_env)
    base.verify_signing_identity(args.keystore, 'coh-client-interactive', SIGNER, password)
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), 'Fresh .33 APK required')
    base.checked_file(args.testing_notes); require(0 < args.testing_notes.stat().st_size <= 65536, 'Bounded testing notes required')
    for tool in (args.android_jar, args.build_tools/'aapt2', args.build_tools/'zipalign', args.build_tools/'lib/d8.jar', args.build_tools/'lib/apksigner.jar'):
        require(tool.is_file() and not tool.is_symlink(), 'Required Android SDK tool missing')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-report-loading-build-', dir=args.output.parent) as temporary:
        work = Path(temporary)
        runtime, payloads, preflight = extract_and_repair(args.donor_apk, donor, work/'donor', commit,
                                                       execute_preflight=False)
        require(typed_equal(preflight['server_archives'], q['package_preflight']['server_archives']),
                'Qualified native server archives differ')
        unsigned, dex, java = compile_shell(args, donor, q, work)
        dex_pin = base.file_pin(dex)
        aligned, signed = work/'aligned.apk', work/'signed.apk'
        with zipfile.ZipFile(unsigned, 'a', zipfile.ZIP_DEFLATED) as archive:
            base.append_payloads(archive, [(work/'donor'/name, name) for name in sorted(payloads)])
            archive.write(dex, 'classes.dex')
        base.run(args.build_tools/'zipalign', '-f', '4', unsigned, aligned)
        base.run('java', '-jar', args.build_tools/'lib/apksigner.jar', 'sign', '--ks', args.keystore,
            '--ks-key-alias', 'coh-client-interactive', '--ks-pass', password, '--key-pass', password, '--out', signed, aligned)
        certificate = retained.verify_signature(signed, args.build_tools)
        base.run(args.build_tools/'zipalign', '-c', '4', signed)
        current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', signed))
        # The signed assembly must reconstruct every qualified template byte.
        # The mandatory fresh-process audit below performs the full preparation
        # on final signed APK bytes; repeating it within this build adds no
        # independent evidence and causes needless multi-gigabyte I/O.
        _, signed_preflight = verify_derivative(signed, donor, payloads, dex_pin, commit, execute_preflight=False)
        require(typed_equal(signed_preflight['server_archives'], q['package_preflight']['server_archives'])
            and typed_equal(signed_preflight['map_startup_component'], q['map_startup_component']),
            'Signed assembly retained native/component boundaries differ')
        preflight = copy.deepcopy(q['package_preflight'])
        retained.verify_binary_manifest(signed, args.donor_apk, args.build_tools)
        shutil.copyfile(signed, args.output)
        report = {'format': 1, 'apk': APK_NAME, **base.file_pin(args.output), 'repository_commit': commit,
            'runtime_repository_commit': commit, 'retained_runtime_repository_commit': DONOR_COMMIT,
            'application_id': base.APP_ID, 'version_name': VERSION_NAME, 'version_code': VERSION_CODE,
            'abi': 'arm64-v8a', 'scope': QUALIFICATION_SCOPE, 'donor': donor_link(), 'map_startup_component': donor['map_startup_component'],
            'signer_certificate_sha256': certificate, 'signing_key_created': False, 'signature_verified': True,
            'package_badging_verified': True, 'binary_manifest_version_only_verified': True, 'payload_bytes_verified': True,
            'payloads': payloads, 'changed_apk_payloads': sorted(replacement_payloads(donor)), 'added_apk_payloads': sorted(ADDED_PAYLOADS),
            'baseline_payloads_verified': 74, 'retained_baseline_payloads_verified': 74-len(replacement_payloads(donor)),
            'donor_dex': donor['recompiled_dex'], 'recompiled_dex': dex_pin, 'java_sources': java,
            'changed_java_sources': changed_java_sources(donor), 'added_java_sources': [],
            'retained_java_sources_verified': len(java)-len(changed_java_sources(donor)),
            'retained_android_resources': donor['retained_android_resources'], 'native_build_provenance': donor['native_build_provenance'],
            'client_gpu_runtime': donor['client_gpu_runtime'], 'external_asset_release_tag': donor['external_asset_release_tag'],
            'asset_pack_version': donor['asset_pack_version'], 'external_asset_pack': donor['external_asset_pack'],
            'qualification': q, 'qualification_receipt': base.file_pin(args.qualification),
            'testing_notes': base.file_pin(args.testing_notes), 'package_preflight': preflight,
            'publication_provenance': publication_provenance(commit), 'runtime_manifest': runtime,
            'runtime_manifest_sha256': payloads['assets/runtime/runtime-manifest.json']['sha256'],
            **dict.fromkeys(FALSE_FLAGS, False), **dict.fromkeys(TRUE_FLAGS, True)}
        (args.output.parent/REPORT_NAME).write_bytes(shared.encoded(report))
    shutil.copyfile(args.testing_notes, args.output.parent/NOTES_NAME)
    args.output.with_suffix('.apk.sha256').write_text(report['sha256']+'  '+APK_NAME+'\n')
    # This is an unaccepted signed candidate until the fresh-process audit
    # executes its actual full preparation and writes the exact audit receipt.
    base.checked_file(args.output, report)
    return report


def verify_report(args, commit, *, execute_preflight=True):
    require_source_identity(commit)
    base, current = builder(), builder(repaired=True)
    donor = validate_donor(args.donor_apk, args.donor_build_report)
    q = validate_qualification(read_json(args.qualification), commit, donor); report = read_json(args.build_report)
    require(report.get('format') == 1 and report.get('apk') == APK_NAME
        and report.get('repository_commit') == report.get('runtime_repository_commit') == commit
        and report.get('retained_runtime_repository_commit') == DONOR_COMMIT
        and report.get('donor') == donor_link()
        and typed_equal(report.get('map_startup_component'), q['map_startup_component'])
        and report.get('scope') == QUALIFICATION_SCOPE
        and report.get('application_id') == base.APP_ID and report.get('version_name') == VERSION_NAME
        and report.get('version_code') == VERSION_CODE and report.get('abi') == 'arm64-v8a'
        and report.get('signer_certificate_sha256') == SIGNER and report.get('signing_key_created') is False
        and typed_equal(report.get('qualification'), q) and report.get('qualification_receipt') == base.file_pin(args.qualification)
        and report.get('publication_provenance') == publication_provenance(commit)
        and report.get('donor_dex') == donor['recompiled_dex'] and report.get('java_sources') == q['java_sources']
        and report.get('changed_java_sources') == changed_java_sources(donor) and report.get('added_java_sources') == []
        and report.get('retained_java_sources_verified') == 24-len(changed_java_sources(donor))
        and report.get('retained_android_resources') == donor['retained_android_resources']
        and report.get('native_build_provenance') == donor['native_build_provenance']
        and report.get('client_gpu_runtime') == donor['client_gpu_runtime']
        and report.get('external_asset_release_tag') == donor['external_asset_release_tag']
        and report.get('asset_pack_version') == donor['asset_pack_version']
        and report.get('external_asset_pack') == donor['external_asset_pack']
        and report.get('changed_apk_payloads') == sorted(replacement_payloads(donor))
        and report.get('added_apk_payloads') == sorted(ADDED_PAYLOADS)
        and report.get('baseline_payloads_verified') == 74 and report.get('retained_baseline_payloads_verified') == 74-len(replacement_payloads(donor))
        and all(report.get(name) is False for name in FALSE_FLAGS)
        and all(report.get(name) is True for name in TRUE_FLAGS+('signature_verified', 'package_badging_verified',
            'binary_manifest_version_only_verified', 'payload_bytes_verified')), 'Exact .33 report/loading repair receipt differs')
    base.checked_file(args.apk, report)
    with tempfile.TemporaryDirectory(prefix='coh-report-loading-independent-dex-') as temporary:
        _, dex, _ = compile_shell(args, donor, q, Path(temporary))
        require(report.get('recompiled_dex') == base.file_pin(dex), 'Independent reviewed Java DEX compilation differs')
    runtime, preflight = verify_derivative(args.apk, donor, report['payloads'], report['recompiled_dex'], commit,
                                           execute_preflight=execute_preflight)
    if not execute_preflight:
        require(typed_equal(preflight['server_archives'], q['package_preflight']['server_archives'])
            and typed_equal(preflight['map_startup_component'], q['map_startup_component']),
            'Lightweight publication retained native/component boundaries differ')
        preflight = copy.deepcopy(q['package_preflight'])
    require(typed_equal(report.get('runtime_manifest'), runtime) and typed_equal(report.get('package_preflight'), preflight)
        and typed_equal(q['package_preflight'], preflight)
        and report.get('runtime_manifest_sha256') == report['payloads']['assets/runtime/runtime-manifest.json']['sha256'],
        'Actual serialized repair/provenance differs')
    retained.verify_binary_manifest(args.apk, args.donor_apk, args.build_tools)
    retained.verify_signature(args.apk, args.build_tools); retained.verify_signature(args.donor_apk, args.build_tools)
    base.run(args.build_tools/'zipalign', '-c', '4', args.apk)
    current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', args.apk))
    checksum = args.apk.with_suffix('.apk.sha256')
    require(checksum.read_text() == report['sha256']+'  '+APK_NAME+'\n', 'Checksum differs')
    notes = args.apk.parent/NOTES_NAME
    base.checked_file(notes, report['testing_notes']); base.checked_file(args.testing_notes, report['testing_notes'])
    return report, checksum, notes


def source_tree(commit):
    require(type(commit) is str and re.fullmatch('[0-9a-f]{40}', commit), 'Exact audit commit required')
    value = subprocess.check_output(['git', 'rev-parse', commit+'^{tree}'], cwd=ROOT, text=True).strip()
    require(re.fullmatch('[0-9a-f]{40}', value), 'Exact audit source tree required')
    return value


def require_source_identity(commit):
    require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == commit,
            'Audit and assembly require their exact checked-out source commit')
    require(subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--'], cwd=ROOT, check=False).returncode == 0,
            'Tracked source changed after committed qualification')
    return source_tree(commit)


def audit_record(report, build_report_pin, qualification_pin):
    """Bind an already completed actual signed-byte audit to all its authorities.

    This receipt is emitted only after verify_report executes full actual
    preparation. Metadata alone never substitutes for the signed-byte audit.
    """
    require(report['apk'] == APK_NAME and report['version_name'] == VERSION_NAME
        and report['version_code'] == VERSION_CODE and report['donor'] == donor_link(),
        'Expected exact successor/donor audit identity')
    for value in (build_report_pin, qualification_pin):
        require(type(value) is dict and set(value) == {'bytes', 'sha256'}
            and type(value['bytes']) is int and 0 < value['bytes'] <= 256*1024**2
            and type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']),
            'Bounded exact audit receipt pin required')
    return {'format': 1, 'status': 'passed', 'scope': 'actual_signed_apk_independent_host_audit',
        'repository_commit': report['repository_commit'], 'repository_tree': source_tree(report['repository_commit']),
        'apk': {key: report[key] for key in ('apk', 'bytes', 'sha256', 'version_name', 'version_code')},
        'build_report': build_report_pin, 'qualification_receipt': qualification_pin,
        'donor': donor_link(), 'independently_recompiled_dex': report['recompiled_dex'],
        'qualified_source_closure': pin(shared.encoded(report['qualification']['source_files'])),
        'candidate_payload_inventory': pin(shared.encoded(report['payloads'])),
        'reviewed_guest_inputs': {Path(name).name: report['payloads']['assets/runtime/'+Path(name).name]
            for name in sorted(GUEST_SOURCE_CHANGES)},
        'runtime_manifest_sha256': report['runtime_manifest_sha256'],
        'retained_native_server_archives': pin(shared.encoded(report['package_preflight']['server_archives'])),
        'retained_map_startup_component': pin(shared.encoded(report['map_startup_component'])),
        'retained_external_assets': pin(shared.encoded(report['external_asset_pack'])),
        'actual_package_preflight': pin(shared.encoded(report['package_preflight'])),
        'actual_runtime_asset_installers_verified': True, 'full_startup_orchestration_verified': True,
        'signature_and_version_only_manifest_verified': True, 'exact_native_and_payload_boundaries_verified': True,
        'native_runtime_booted': False, 'physical_execution_validated': False,
        'live_database_and_saved_character_executed': False, 'process_and_sql_boundary': 'not_executed',
        'physical_map_startup_speedup_validated': False, 'sub_30_second_map_startup_validated': False}


def validate_audit_record(value, report, build_report_pin, qualification_pin):
    require(typed_equal(value, audit_record(report, build_report_pin, qualification_pin)),
            'Exact accepted signed APK/source/manifest/qualification/donor audit receipt required')
    return value


def audit(args, commit):
    report, _, _ = verify_report(args, commit)
    base = builder()
    value = audit_record(report, base.file_pin(args.build_report), base.file_pin(args.qualification))
    require(not args.audit_receipt.exists() and not args.audit_receipt.is_symlink(), 'Fresh independent audit receipt required')
    args.audit_receipt.parent.mkdir(parents=True, exist_ok=True)
    args.audit_receipt.write_bytes(shared.encoded(value))
    validate_audit_record(read_json(args.audit_receipt), report, base.file_pin(args.build_report), base.file_pin(args.qualification))
    print('Independent exact .33 signed APK audit passed:', report['sha256'])
    return value


def download_donor_evidence(args):
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh donor evidence directory required')
    args.output.mkdir(parents=True); target = args.output/DONOR_EVIDENCE_ARCHIVE
    authenticated_artifact_download(DONOR_EVIDENCE_ID, target, DONOR_EVIDENCE)
    with zipfile.ZipFile(target) as archive:
        require(retained.archive_inventory(archive) == DONOR_EVIDENCE_NAMES, 'Exact .32 evidence inventory required')
        for entry in archive.infolist():
            require(not entry.is_dir() and 0 < entry.file_size <= 64*1024**2, 'Bounded flat evidence required')
            (args.output/entry.filename).write_bytes(archive.read(entry))
    builder().checked_file(args.output/DONOR_REPORT_NAME, DONOR_BUILD)
    audit = args.output/'published-0.13.32-public-byte-audit.zip'
    authenticated_artifact_download(DONOR_PUBLIC_AUDIT_ID, audit, DONOR_PUBLIC_AUDIT)
    with zipfile.ZipFile(audit) as archive:
        require(retained.archive_inventory(archive) == {'client-map-startup-public-byte-audit.json'}, 'Exact accepted public audit required')
        target = args.output/'client-map-startup-public-byte-audit.json'; target.write_bytes(archive.read(target.name))
    builder().checked_file(target, DONOR_PUBLIC_AUDIT_RECEIPT)
    receipt = read_json(target)
    require(receipt['status'] == 'passed' and receipt['repository_commit'] == DONOR_COMMIT
        and receipt['run_id'] == DONOR_RUN_ID and receipt['public_apk_verified'] is True
        and receipt['actual_runtime_asset_installers_verified'] is True
        and receipt['unchanged_assets_1_0_0_metadata_verified'] is True, 'Accepted .32 public-byte proof differs')
    bounded_download('https://github.com/'+REPOSITORY+'/releases/download/coh-assets-v1.0.0/asset-pack-build-report.json',
                     args.output/'asset-pack-build-report.json', ASSET_BUILD)


_publication = module('profile_repair_private_publication', Path(previous._publication.__file__))
for _name in ('APK_NAME', 'REPORT_NAME', 'NOTES_NAME', 'RELEASE_TAG', 'DONOR_COMMIT', 'DONOR_APK_NAME', 'DONOR_APK', 'NOTES'):
    setattr(_publication, _name, globals()[_name])
validate_existing_release, download_public = _publication.validate_existing_release, _publication.download_public


def verify_asset_release(api, directory):
    directory = Path(directory); builder().checked_file(directory/'asset-pack-build-report.json', ASSET_BUILD)
    report = read_json(directory/'asset-pack-build-report.json')
    expected = dict(report['volumes'], **report['audit_files'])
    expected['asset-pack-manifest.json'] = report['asset_manifest']
    expected['asset-pack-build-report.json'] = ASSET_BUILD
    for name, value in report['volumes'].items():
        expected[name+'.sha256'] = pin((value['sha256']+'  '+name+'\n').encode())
    release = api.request('/releases/tags/coh-assets-v1.0.0')
    require(release.get('draft') is False and release.get('tag_name') == 'coh-assets-v1.0.0', 'Retained asset release unavailable')
    assets = {row['name']: row for row in release.get('assets', [])}
    require(len(assets) == len(release.get('assets', [])) and set(assets) == set(expected)
        and all(assets[name].get('size') == value['bytes'] and assets[name].get('digest') == 'sha256:'+value['sha256']
                and assets[name].get('state') == 'uploaded' for name, value in expected.items()),
        'Published Assets 1.0.0 metadata changed; this repair must not replace assets')
    return {'release_tag': 'coh-assets-v1.0.0', 'original_public_byte_audit_artifact_id': 11708366753,
            'unchanged_public_asset_metadata_verified': True, 'asset_release_republished': False}


def publish(args):
    marker = read_json(ROOT/MARKER)
    require(marker.get('publish_enabled') is True and marker.get('version') == VERSION_NAME
        and marker.get('version_code') == VERSION_CODE and marker.get('donor_commit') == DONOR_COMMIT,
        'Reviewed .33 publication marker must explicitly enable the qualified successor')
    require(os.environ.get('GITHUB_REPOSITORY') == REPOSITORY and os.environ.get('GITHUB_REF') == 'refs/heads/'+BRANCH
        and os.environ.get('GITHUB_EVENT_NAME') in ('push', 'workflow_dispatch'), 'Publication requires continuation branch')
    commit = builder().source_commit(os.environ.get('GITHUB_SHA'))
    report, checksum, notes = verify_report(args, commit, execute_preflight=False)
    validate_audit_record(read_json(args.audit_receipt), report,
        builder().file_pin(args.build_report), builder().file_pin(args.qualification))
    client = module('profile_repair_github', Path(__file__).with_name('build_atlas_gameplay_apk.py')).GitHub(os.environ.get('GH_TOKEN'))
    verify_asset_release(client, args.donor_build_report.parent)
    try: client.request('/releases/tags/'+RELEASE_TAG)
    except urllib.error.HTTPError as error:
        if error.code != 404: raise
    else: raise ValueError('Existing .33 release is never replaced')
    module('profile_repair_head_guard', Path(__file__).with_name('build_client_sidebar_apk.py')).require_current_release_head(client, commit)
    release = client.request('/releases', {'tag_name': RELEASE_TAG, 'target_commitish': commit,
        'name': 'COH Atlas Gameplay 0.13.33 — report recovery and warm preparation repair',
        'body': notes.read_text()+'\n\nAPK SHA-256: `'+report['sha256']+'`.\n',
        'draft': True, 'prerelease': True, 'generate_release_notes': False, 'make_latest': 'false'}, method='POST')
    require(type(release.get('id')) is int and release.get('draft') is True, 'Expected new APK draft')
    for path in (args.apk, checksum, notes):
        expected = builder().file_pin(path)
        uploaded = client.request('/releases/'+str(release['id'])+'/assets?'+urllib.parse.urlencode({'name': path.name}),
                                  path, method='POST', upload=True)
        require(uploaded.get('state') == 'uploaded' and uploaded.get('name') == path.name
            and uploaded.get('size') == expected['bytes'] and uploaded.get('digest') == 'sha256:'+expected['sha256'],
            'Uploaded APK release member differs')
    module('profile_repair_head_guard', Path(__file__).with_name('build_client_sidebar_apk.py')).require_current_release_head(client, commit)
    result = client.request('/releases/'+str(release['id']), {'draft': False, 'prerelease': True, 'make_latest': 'false'}, method='PATCH')
    validate_existing_release(result)
    print('Published APK only; existing Assets 1.0.0 retained:', result['html_url'])


def main():
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest='command', required=True)
    for name in ('download-donor', 'download-donor-evidence'):
        command = commands.add_parser(name); command.add_argument('--output', type=Path, required=True)
    command = commands.add_parser('download-public')
    command.add_argument('--output', type=Path, required=True); command.add_argument('--build-report', type=Path, required=True)
    command = commands.add_parser('verify-assets'); command.add_argument('--donor-build-report', type=Path, required=True)
    for name in ('build', 'audit', 'publish'):
        command = commands.add_parser(name)
        for field in ('donor-apk', 'donor-build-report', 'qualification', 'build-tools', 'android-jar'):
            command.add_argument('--'+field, type=Path, required=True)
        command.add_argument('--repository-commit', default=os.environ.get('GITHUB_SHA'))
        command.add_argument('--testing-notes', type=Path, default=NOTES)
        if name == 'build':
            for field in ('keystore', 'output'): command.add_argument('--'+field, type=Path, required=True)
            command.add_argument('--password-env', default='COH_INTERACTIVE_KEYSTORE_PASSWORD')
        else:
            for field in ('apk', 'build-report'): command.add_argument('--'+field, type=Path, required=True)
            command.add_argument('--audit-receipt', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'download-donor': bounded_download(DONOR_URL, args.output, DONOR_APK)
    elif args.command == 'download-donor-evidence': download_donor_evidence(args)
    elif args.command == 'download-public': download_public(args)
    elif args.command == 'verify-assets':
        api = module('report_loading_asset_reader', Path(__file__).with_name('build_atlas_gameplay_apk.py')).GitHub(os.environ.get('GH_TOKEN'))
        print(json.dumps(verify_asset_release(api, args.donor_build_report.parent), sort_keys=True))
    elif args.command == 'build': build(args)
    elif args.command == 'publish': publish(args)
    else: audit(args, builder().source_commit(args.repository_commit))


if __name__ == '__main__': main()
