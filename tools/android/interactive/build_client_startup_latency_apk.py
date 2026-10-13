#!/usr/bin/env python3
"""Exact public .35 derivative for client and zoning startup latency, progression save checks.

Game/Db/Map archives, FX/catalog/certificate, GPU, Wine/FEX, Android resources
and Assets 1.0.0 retain exact donor bytes. Reviewed guest sources and enclosing manifests change; the qualified .35 PE32 launcher remains byte-identical. All changed scopes and strict SQL execute currently;
historical packaging contracts retain their exact original source identities.
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
DONOR_COMMIT, DONOR_RUN_ID = '6136171e842eb69807636dbad9aedff0af6c5887', 38326347301
DONOR_APK_NAME = 'COH-Atlas-Gameplay-0.13.35.apk'
DONOR_APK = {'bytes': 42064404, 'sha256': '6d8b74782186561a30d201400cbfddeb7ce81d2d471477950c1c4da69eafae31'}
DONOR_REPORT_NAME = 'client-manual-session-apk-build-report.json'
DONOR_BUILD = {'bytes': 10001934, 'sha256': '2b5828c41ef613d8b75d4bf600b930a2d390a326f8e1b6e3639b6519dcfbc744'}
DONOR_EVIDENCE_ID = 11782530752
DONOR_EVIDENCE = {'bytes': 52078623, 'sha256': '790edabf3e00facb0d76817b4de23862cca965af0a96bda1848664e5d878dba6'}
DONOR_EVIDENCE_ARCHIVE = 'published-0.13.35-packaging-evidence.zip'
DONOR_EVIDENCE_NAMES = frozenset({DONOR_REPORT_NAME, DONOR_APK_NAME, DONOR_APK_NAME+'.sha256',
    'COH-Atlas-Gameplay-0.13.35-testing.txt', 'client-manual-session-apk-audit.json'})
DONOR_URL = 'https://github.com/'+REPOSITORY+'/releases/download/coh-atlas-gameplay-v0.13.35/'+DONOR_APK_NAME
DONOR_PUBLIC_AUDIT_ID = 11783555735
DONOR_PUBLIC_AUDIT = {'bytes': 818, 'sha256': '180dbc1186a7a45c13839d66e0762a700d46bf1f3fb27f905ca3ac790d7326bf'}
DONOR_PUBLIC_AUDIT_RECEIPT = {'bytes': 1563, 'sha256': 'c4c6f2233eaf255e46e3afccf523ff042755836225763b09fbf95fcbd8b99284'}
ASSET_BUILD = previous.ASSET_BUILD
VERSION_NAME, VERSION_CODE = '0.13.36', 51
APK_NAME, REPORT_NAME = 'COH-Atlas-Gameplay-0.13.36.apk', 'client-startup-latency-apk-build-report.json'
CLIENT_APK_AUDIT_NAME = 'client-startup-latency-apk-audit.json'
NOTES_NAME, RELEASE_TAG = 'COH-Atlas-Gameplay-0.13.36-testing.txt', 'coh-atlas-gameplay-v0.13.36'
NOTES = ROOT/'docs'/NOTES_NAME
WORKFLOW = '.github/workflows/android-client-startup-latency.yml'
QUALIFICATION_SCRIPT = 'tools/android/interactive/qualify_client_startup_latency.py'
QUALIFICATION_SCOPE = 'startup_latency_and_progression_save_checks_retaining_exact_035_native_graphics_assets'
MARKER = 'tools/android/interactive/release-client-startup-latency-0.13.36.json'
REVIEWED_JAVA_CHANGES = frozenset()
GUEST_SOURCE_CHANGES = frozenset('android/guest/'+name+'.py' for name in (
    'atlas_beacon_package', 'character_server_data_cache', 'character_zoning',
    'character_creation_diagnostic', 'client_gpu_profile', 'kings_row_beacon_package',
    'local_character_server', 'task_gate_evidence'))
NATIVE_SOURCE_FILES = frozenset({
    'android/native/client-launcher.c',
    'tools/android/interactive/manual_launcher_contract.py',
    'tools/android/interactive/package_manual_launcher.py',
    'tools/android/interactive/qualify_manual_launcher_windows.py'})
NATIVE_PAYLOAD = 'assets/runtime/client-launcher.exe'
ADDED_PAYLOADS = frozenset()
CHECKS = ('retained_regressions_and_postgresql_verified', 'actual_runtime_asset_installers_verified',
    'full_startup_orchestration_verified', 'report_finalization_and_recovery_verified',
    'saved_map_startup_and_preservation_verified', 'bounded_cache_reuse_verified',
    'client_gpu_startup_reuse_verified', 'lawful_progression_save_checks_verified',
    'manual_session_and_capture_verified', 'text_entry_transport_verified',
    'native_launcher_lifecycle_verified', 'minimal_db_native_compatibility_verified',
    'exact_035_game_db_map_graphics_and_assets_verified')
FALSE_FLAGS = ('native_client_recompiled', 'native_mapserver_recompiled', 'native_dbserver_recompiled',
    'graphics_driver_changed', 'wine_or_fex_changed', 'world_assets_changed', 'asset_reimport_required',
    'native_runtime_booted', 'save_acceptance_relaxed', 'physical_recovery_validated',
    'physical_kings_row_zoning_validated', 'physical_kings_row_reopen_validated', 'physical_fps_gain_validated',
    'physical_map_startup_speedup_validated', 'sub_30_second_map_startup_validated',
    'sub_five_minute_total_startup_validated', 'sub_one_minute_client_start_validated',
    'native_client_launcher_recompiled', 'manual_session_policy_changed', 'java_or_dex_recompiled',
    'dynamic_mapserver_integration_shipped')
TRUE_FLAGS = ('retained_android_resources_verified', 'retained_game_and_dbserver_verified',
    'retained_client_game_and_mapserver_verified', 'external_assets_1_0_0_reused',
    'serialized_game_receipts_verified', 'runtime_refresh_required', 'guest_helpers_changed',
    'actual_runtime_asset_installers_verified', 'exact_035_dex_retained',
    'full_startup_orchestration_verified', 'retained_032_map_startup_component_verified',
    'all_native_member_bytes_retained', 'native_client_launcher_windows_fixture_verified',
    'native_client_launcher_qualification_inherited', 'actual_retained_minimal_db_host_fixture_verified')
REVIEWED_TEST_CHANGES = frozenset('tools/android/interactive/'+name+'.py' for name in (
    'test_character_map_data', 'test_client_gpu_profile', 'test_shared_collision_input_proof',
    'test_character_zoning', 'test_client_preload_launch', 'test_saved_map_preparation',
    'test_saved_map_startup', 'test_saved_map_postgresql', 'test_saved_map_preparation_proof',
    'test_character_reopen_guest', 'test_character_monorail',
    'test_classify_storage_cleanup_change'))
ROUTING_SOURCE_CHANGES = frozenset({
    'tools/android/interactive/classify_client_animation_repair_change.py',
    'tools/android/interactive/classify_client_profile_recovery_change.py',
    'tools/android/interactive/classify_client_map_startup_change.py'})
HOST_FIXTURE_SOURCE_CHANGES = frozenset({
    'tools/android/interactive/qualify_saved_map_preparation.py'})
RESEARCH_SOURCE_FILES = frozenset({
    '.github/workflows/android-native-startup-profile.yml',
    'tools/prepare_native_cg_profile_source.py', 'tools/test_native_cg_profile_source.py',
    'tools/package_native_startup_profile.py', 'tools/qualify_native_startup_profile.py',
    'tools/test_qualify_native_startup_profile.py',
    'database/native-startup-profile/overlay/coh_native_cg_profile.h'})
SOURCE_FILES = frozenset({WORKFLOW, QUALIFICATION_SCRIPT, MARKER, 'docs/'+NOTES_NAME,
    'tools/android/interactive/build_client_startup_latency_apk.py',
    'tools/android/interactive/test_client_startup_latency_package.py',
    'tools/android/interactive/classify_client_startup_latency_change.py',
    'tools/android/interactive/qualify_startup_latency_preparation.py',
    'tools/android/interactive/test_startup_latency_preparation_proof.py',
    'tools/android/interactive/test_saved_gameplay_lifecycle.py',
    'tools/android/interactive/fixtures/thor-save-lifecycle-0.13.35-20261013.json',
    'tools/android/interactive/test_manual_launcher_contract.py',
    'tools/android/interactive/qualify_saved_map_preparation.py',
    'tools/android/interactive/test_saved_map_preparation_proof.py',
    'tools/android/interactive/qualify_minimal_db_runtime.py',
    'tools/android/interactive/test_minimal_db_runtime_contract.py',
    'tools/android/interactive/fixtures/minimal-db-native-inputs-0.13.34.json'}) | REVIEWED_JAVA_CHANGES | GUEST_SOURCE_CHANGES | REVIEWED_TEST_CHANGES | ROUTING_SOURCE_CHANGES | HOST_FIXTURE_SOURCE_CHANGES | NATIVE_SOURCE_FILES | RESEARCH_SOURCE_FILES
REVIEWED_DONOR_SOURCE_CHANGES = REVIEWED_JAVA_CHANGES | GUEST_SOURCE_CHANGES | REVIEWED_TEST_CHANGES | ROUTING_SOURCE_CHANGES | HOST_FIXTURE_SOURCE_CHANGES


# The completed .35 documentation commit appended install/acceptance guidance
# after the immutable APK source was frozen. Retain that exact later document;
# its historical release proof remains bound to the original published bytes.
POST_PUBLICATION_DONOR_DOCUMENTS = {
    'docs/COH-Atlas-Gameplay-0.13.35-testing.txt': {
        'bytes': 6339, 'sha256': '33b31399af97dae9cd20432dbb5a50af53f033eb2ee130da3cefc874089349bc'}}
POST_PUBLICATION_DONOR_DOCUMENTS_COMMIT = 'b9e81b0cb772bea5de7394b55702b7c4d55e49f2'


def load_minimal_db_proof(path, commit):
    import qualify_minimal_db_runtime as minimal
    value = minimal.validate_proof(read_json(path), commit)
    require(str(value['run_id']) == os.environ.get('GITHUB_RUN_ID'),
        'Current publication must consume its own genuine retained minimal Db fixture')
    return value


def validate_native_launcher(directory, commit):
    import manual_launcher_contract as native
    directory = Path(directory)
    build, qualification = read_json(directory/native.MANIFEST_NAME), read_json(directory/native.QUALIFICATION_NAME)
    native.validate_qualification(qualification, build, directory/native.EXE_NAME, DONOR_COMMIT)
    require(build['run_id'] == DONOR_RUN_ID and qualification['run_id'] == DONOR_RUN_ID,
        'Retained launcher must keep the exact audited .35 source and native fixture owner')
    return {'build': build, 'qualification': qualification}


def extract_retained_launcher(apk, donor, destination):
    import manual_launcher_contract as native
    destination = Path(destination)
    require(not destination.exists() and not destination.is_symlink(), 'Fresh retained-helper staging required')
    destination.mkdir(parents=True)
    proof = donor['native_launcher']
    with zipfile.ZipFile(apk) as archive:
        raw = archive.read(NATIVE_PAYLOAD)
    require(pin(raw) == donor['payloads'][NATIVE_PAYLOAD] == proof['build']['executable'],
        'Inherited Windows proof must authenticate actual retained helper bytes')
    (destination/native.EXE_NAME).write_bytes(raw)
    (destination/native.MANIFEST_NAME).write_bytes(native.encoded(proof['build']))
    (destination/native.QUALIFICATION_NAME).write_bytes(native.encoded(proof['qualification']))
    validate_native_launcher(destination, DONOR_COMMIT)
    return proof


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
        'native_producer_relabelled': False, 'asset_release_republished': False,
        'retained_post_publication_documentation_commit': POST_PUBLICATION_DONOR_DOCUMENTS_COMMIT,
        'retained_post_publication_documents': POST_PUBLICATION_DONOR_DOCUMENTS}


def current_sources(donor):
    base = builder()
    java = {name: base.file_pin(ROOT/name) for name in donor['java_sources']}
    require(len(java) == 24 and set(java) == set(donor['java_sources'])
        and {name for name in java if java[name] != donor['java_sources'][name]} == REVIEWED_JAVA_CHANGES,
        'Exactly the reviewed .36 Java source changes are required')
    for name, expected in donor['payloads'].items():
        if name.startswith('assets/runtime/') and name.endswith('.py'):
            source = 'android/guest/'+Path(name).name
            if source not in GUEST_SOURCE_CHANGES: base.checked_file(ROOT/source, expected)
    for name, expected in donor['qualification']['source_files'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts and '\\' not in name,
                'Unsafe retained source path')
        if name in POST_PUBLICATION_DONOR_DOCUMENTS:
            base.checked_file(ROOT/name, POST_PUBLICATION_DONOR_DOCUMENTS[name])
        elif name not in REVIEWED_DONOR_SOURCE_CHANGES: base.checked_file(ROOT/name, expected)
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
            'Each reviewed saved-map/cache guest helper must actually change')
    return frozenset(changed)


def validate_donor(apk, receipt):
    base = builder(); base.checked_file(apk, DONOR_APK); base.checked_file(receipt, DONOR_BUILD)
    donor = read_json(receipt)
    require(donor['repository_commit'] == donor['runtime_repository_commit'] == DONOR_COMMIT
        and donor['apk'] == DONOR_APK_NAME and donor['version_name'] == '0.13.35' and donor['version_code'] == 50
        and {key: donor[key] for key in ('bytes', 'sha256')} == DONOR_APK
        and donor['signer_certificate_sha256'] == SIGNER and donor['signature_verified'] is True
        and donor['external_asset_release_tag'] == 'coh-assets-v1.0.0' and donor['asset_pack_version'] == '1.0.0'
        and donor['publication_provenance']['run_url'] == 'https://github.com/'+REPOSITORY+'/actions/runs/'+str(DONOR_RUN_ID),
        'Exact accepted public .35 donor identity required')
    require(len(donor['payloads']) == 74 and donor['native_mapserver_recompiled'] is False
        and donor['all_native_member_bytes_retained'] is False
        and donor['native_client_launcher_recompiled'] is True
        and donor['retained_032_map_startup_component_verified'] is True
        and donor['qualification']['donor']['repository_commit'] == '46904ced3d7efb6218ecf92d9e44ad597d3146d0'
        and donor['donor'] == donor['qualification']['donor'],
        'Exact retained .35 payload/native ancestry inventory required')
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


def payload_boundaries(payloads, donor, native):
    require(set(payloads) == set(donor['payloads']) and len(payloads) == 74
        and {name for name in payloads if payloads[name] != donor['payloads'][name]} == replacement_payloads(donor),
        'Only reviewed guest helpers and enclosing manifests may change; all native bytes remain exact')
    require(payloads[NATIVE_PAYLOAD] == native['build']['executable'], 'Actual payload must retain original .35 Windows-qualified launcher')


def verification_manifests(donor, helper_pins, commit, native):
    require(set(helper_pins) == {Path(name).name for name in GUEST_SOURCE_CHANGES},
            'Exact reviewed guest helper pins required')
    require(helper_pins == {Path(name).name: builder().file_pin(ROOT/name) for name in GUEST_SOURCE_CHANGES},
            'Reviewed helper pins must match actual candidate source bytes')
    helper_pins = {name: helper_pins[name] for name in sorted(helper_pins)}
    updates = dict(helper_pins, **{'client-launcher.exe': native['build']['executable']})
    client = copy.deepcopy(donor['_client_verification']); client['files'].update(updates)
    runtime = copy.deepcopy(donor['runtime_manifest']); runtime['files'].update(updates)
    runtime['files']['client-manifest.json'] = pin(shared.encoded(client))
    runtime.update(repository_commit=commit, scope=QUALIFICATION_SCOPE)
    runtime['client_startup_latency'] = {'format': 1, 'repository_commit': commit,
        'donor_repository_commit': DONOR_COMMIT, 'publication_provenance': publication_provenance(commit),
        'reviewed_guest_inputs': helper_pins, 'native_launcher': native,
        **dict.fromkeys(FALSE_FLAGS, False), **dict.fromkeys(TRUE_FLAGS, True)}
    require(typed_equal(runtime['client_manual_session'], donor['runtime_manifest']['client_manual_session'])
        and typed_equal(runtime['client_saved_map_reopen'], donor['runtime_manifest']['client_saved_map_reopen'])
        and typed_equal(runtime['client_report_loading'], donor['runtime_manifest']['client_report_loading'])
        and typed_equal(runtime['client_map_startup'], donor['runtime_manifest']['client_map_startup'])
        and typed_equal(runtime['client_bundle'], donor['runtime_manifest']['client_bundle'])
        and runtime['external_asset_pack'] == donor['runtime_manifest']['external_asset_pack'],
        'Existing native ancestry and installed asset descriptor must remain exact')
    return client, runtime


actual_asset_preflight = previous.actual_asset_preflight
def actual_startup_preflight(assets):
    import qualify_runtime_asset_preflight as originals
    import qualify_startup_latency_preparation as selected
    asset_cache = Path(os.environ.get('COH_MAP_STARTUP_ASSET_CACHE', ROOT/'out/map-startup-assets'))
    return selected.preflight(assets, originals.ensure_assets(asset_cache))


def add_actual_preflight(preflight, assets):
    snapshot = actual_startup_preflight(assets)
    preflight.update(runtime_assets=actual_asset_preflight(assets),
        full_startup=snapshot['full_startup'], saved_map_startup_preflight=snapshot)
    return preflight


def extract_and_repair(apk, donor, destination, commit, native_directory, native, *, execute_preflight=True):
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
    launcher = assets/'client-launcher.exe'
    launcher.write_bytes((Path(native_directory)/'client-launcher.exe').read_bytes())
    require(builder().file_pin(launcher) == native['build']['executable'], 'Exact retained .35 launcher bytes required')
    client, runtime = verification_manifests(donor, helper_pins, commit, native)
    for name, value in (('client-manifest.json', client), ('runtime-manifest.json', runtime)):
        (assets/name).write_bytes(shared.encoded(value))
    payloads = {name: base.file_pin(destination/name) for name in sorted(donor['payloads'])}
    payload_boundaries(payloads, donor, native)
    server = retained.verify_server_archives(assets)
    require(typed_equal(server, donor['package_preflight']['server_archives']),
            'Every accepted .32 Game/Map/DbServer/schema archive must remain exact')
    preflight = {'server_archives': server, 'map_startup_component': copy.deepcopy(donor['map_startup_component'])}
    if execute_preflight:
        add_actual_preflight(preflight, assets)
    return runtime, payloads, preflight


def validate_qualification(q, commit, donor, native, minimal_db):
    contract = module('startup_latency_qualification_contract', ROOT/QUALIFICATION_SCRIPT)
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
        and typed_equal(q.get('native_launcher'), native)
        and typed_equal(q.get('minimal_db_native'), minimal_db)
        and q.get('check_suites') == contract.CHECK_SUITES and set(q.get('checks', {})) == set(CHECKS)
        and all(q['checks'][name] is True for name in CHECKS)
        and all(q.get(name) is False for name in FALSE_FLAGS)
        and all(q.get(name) is True for name in TRUE_FLAGS),
        'Exact current client/map/progression qualification and retained .35 native authority required')
    suites = q.get('test_suites', {})
    require(set(suites) == set(contract.TEST_MODULES) and all(row.get('status') == 'passed'
        and row.get('skipped') == 0 and type(row.get('tests_run')) is int and row['tests_run'] > 0
        for row in suites.values()) and type(q.get('tests_run')) is int
        and q.get('tests_run') == sum(row['tests_run'] for row in suites.values()),
        'Every retained and current regression suite must pass without skips')
    for name, row in suites.items():
        if name in contract.RETAINED_CONTRACT_MODULES:
            require(typed_equal(row, contract.retained_contract_result(name, donor)),
                'Historical unchanged contracts require exact accepted .35 source-bound evidence')
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
    import test_saved_map_postgresql as saved_map
    require(q.get('postgresql_saved_map_fixtures') == sorted(saved_map.REQUIRED_POSTGRES_FIXTURES)
        and len(q['postgresql_saved_map_fixtures']) == 17,
        'All seventeen current read-only saved-map SQL fixtures required')
    saved_map.validate_qualification_inventory(q.get('saved_map_postgresql_proof'))
    require(set(q.get('source_files', {})) == set(contract.source_paths(donor)),
            'Exact qualified source closure required')
    require_committed_sources(commit, sorted(q['source_files']))
    for name, expected in q['source_files'].items(): builder().checked_file(ROOT/name, expected)
    expected_native_fixture = {'role': 'existing_public_031_native_parser_fixture_only',
        'apk': previous.DONOR_APK,
        'current_suites': ['test_full_startup_preflight', 'test_map_startup_native_contract',
            'test_map_startup_cache_reuse'],
        'shipping_runtime_donor_changed': False, 'native_binary_rebuilt': False}
    import build_client_profile_recovery_apk as original_dependency
    expected_dependency_fixture = {'role': 'original_public_030_native_dependency_fixture_only',
        'apk': original_dependency.DONOR_APK, 'repository_commit': original_dependency.DONOR_COMMIT,
        'current_suites': ['test_kings_row_runtime_dependencies'],
        'shipping_runtime_donor_changed': False, 'native_binary_rebuilt': False}
    import build_client_animation_repair_apk as original_animation
    expected_animation_fixture = {'role': 'original_public_029_animation_compatibility_fixture_only',
        'apk': original_animation.DONOR_APK, 'repository_commit': original_animation.DONOR_COMMIT,
        'current_suites': ['test_animation_runtime_compatibility'],
        'shipping_runtime_donor_changed': False, 'native_binary_rebuilt': False}
    require(typed_equal(q.get('native_animation_test_fixture'), expected_animation_fixture)
        and typed_equal(q.get('native_contract_test_fixture'), expected_native_fixture)
        and typed_equal(q.get('native_dependency_test_fixture'), expected_dependency_fixture),
        'Original native fixture donor identities and current reader/dependency scope required')
    require(type(q.get('package_preflight')) is dict, 'Actual serialized package preflight required')
    require(typed_equal(q['package_preflight'].get('server_archives'), donor['package_preflight']['server_archives'])
        and typed_equal(q['package_preflight'].get('map_startup_component'), donor['map_startup_component']),
        'Accepted .32 native archive and component provenance must remain exact')
    import qualify_startup_latency_preparation as selected
    selected_proof = selected.validate_proof(q['package_preflight'].get('saved_map_startup_preflight'))
    require(typed_equal(selected_proof['full_startup'], q['package_preflight'].get('full_startup')),
        'Historical full-input control must be clearly bound to current selected-map preparation proof')
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


def verify_derivative(apk, donor, payloads, dex_pin, commit, native_directory, native, *, execute_preflight=True):
    base = builder(); payload_boundaries(payloads, donor, native); base.verify_packaged_payloads(apk, payloads)
    require(dex_pin == donor['recompiled_dex'] and set(dex_pin) == {'bytes', 'sha256'},
            'Unchanged Java must retain the exact authenticated .35 DEX')
    with zipfile.ZipFile(apk) as archive:
        shell = {'classes.dex': dex_pin, **donor['retained_android_resources']}
        require(retained.archive_inventory(archive) == set(payloads) | set(shell) | {'AndroidManifest.xml'},
                'Candidate APK inventory differs')
        for name, expected in shell.items(): require(pin(archive.read(name)) == expected, 'Candidate DEX/resources differ: '+name)
    with tempfile.TemporaryDirectory(prefix='coh-startup-latency-reconstruction-') as temporary:
        runtime, expected, preflight = extract_and_repair(donor['_apk_path'], donor, Path(temporary)/'donor', commit, native_directory, native,
                                                       execute_preflight=False)
        require(payloads == expected, 'Reconstructed public .35 plus reviewed helpers differs')
    require(retained.verify_apk_server_archives(apk) == preflight['server_archives'],
            'Actual signed APK native archive extraction differs')
    # Execute the final signed APK's actual guest bytes independently of the
    # expected-hash reconstruction, retaining nested receipt key order.
    if execute_preflight:
        with tempfile.TemporaryDirectory(prefix='coh-startup-latency-actual-') as temporary, zipfile.ZipFile(apk) as archive:
            directory = Path(temporary)
            for name in sorted(payloads):
                if name.startswith('assets/runtime/'):
                    (directory/Path(name).name).write_bytes(archive.read(name))
            add_actual_preflight(preflight, directory)
    return runtime, preflight


def repair_android_manifest(source, destination):
    base = builder(); base.verify_source_manifest(source); tree = ET.parse(source)
    tree.getroot().set(base.ANDROID+'versionName', VERSION_NAME)
    tree.getroot().set(base.ANDROID+'versionCode', str(VERSION_CODE))
    ET.register_namespace('android', base.ANDROID[1:-1]); tree.write(destination, encoding='utf-8', xml_declaration=True)
    builder(repaired=True).verify_source_manifest(destination)


def compile_shell(args, donor, q, work):
    """Change only version metadata; retain exact .35 DEX and Android resources."""
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
    java = current_sources(donor)
    require(not REVIEWED_JAVA_CHANGES and q['java_sources'] == java and q['changed_java_sources'] == [],
            'Guest-only successor must retain every authenticated Java source')
    dex_path = dex/'classes.dex'
    with zipfile.ZipFile(donor['_apk_path']) as archive:
        dex_path.write_bytes(archive.read('classes.dex'))
    base.checked_file(dex_path, donor['recompiled_dex'])
    return unsigned, dex_path, java


def require_signed_preflight(preflight, qualification):
    require(typed_equal(preflight, qualification['package_preflight']),
            'Actual signed APK qualification differs')


def build(args):
    base, current = builder(), builder(repaired=True); commit = base.source_commit(args.repository_commit)
    require_source_identity(commit)
    donor = validate_donor(args.donor_apk, args.donor_build_report)
    native = validate_native_launcher(args.native_directory, commit)
    minimal_db = load_minimal_db_proof(args.minimal_db_proof, commit)
    q = validate_qualification(read_json(args.qualification), commit, donor, native, minimal_db)
    password = base.signing_password_spec(args.password_env)
    base.verify_signing_identity(args.keystore, 'coh-client-interactive', SIGNER, password)
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), 'Fresh .36 APK required')
    base.checked_file(args.testing_notes); require(0 < args.testing_notes.stat().st_size <= 65536, 'Bounded testing notes required')
    for tool in (args.android_jar, args.build_tools/'aapt2', args.build_tools/'zipalign', args.build_tools/'lib/d8.jar', args.build_tools/'lib/apksigner.jar'):
        require(tool.is_file() and not tool.is_symlink(), 'Required Android SDK tool missing')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-startup-latency-build-', dir=args.output.parent) as temporary:
        work = Path(temporary)
        runtime, payloads, preflight = extract_and_repair(args.donor_apk, donor, work/'donor', commit, args.native_directory, native,
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
        # The signed assembly must reconstruct every qualified template byte, including the retained DEX.
        # The mandatory fresh-process audit below performs the full preparation
        # on final signed APK bytes; repeating it within this build adds no
        # independent evidence and causes needless multi-gigabyte I/O.
        _, signed_preflight = verify_derivative(signed, donor, payloads, dex_pin, commit, args.native_directory, native, execute_preflight=False)
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
            'native_launcher': native, 'minimal_db_native': minimal_db, 'qualification': q, 'qualification_receipt': base.file_pin(args.qualification),
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
    native = validate_native_launcher(args.native_directory, commit)
    minimal_db = load_minimal_db_proof(args.minimal_db_proof, commit)
    q = validate_qualification(read_json(args.qualification), commit, donor, native, minimal_db); report = read_json(args.build_report)
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
        and typed_equal(report.get('native_launcher'), native)
        and typed_equal(report.get('minimal_db_native'), minimal_db)
        and report.get('external_asset_release_tag') == donor['external_asset_release_tag']
        and report.get('asset_pack_version') == donor['asset_pack_version']
        and report.get('external_asset_pack') == donor['external_asset_pack']
        and report.get('changed_apk_payloads') == sorted(replacement_payloads(donor))
        and report.get('added_apk_payloads') == sorted(ADDED_PAYLOADS)
        and report.get('baseline_payloads_verified') == 74 and report.get('retained_baseline_payloads_verified') == 74-len(replacement_payloads(donor))
        and all(report.get(name) is False for name in FALSE_FLAGS)
        and all(report.get(name) is True for name in TRUE_FLAGS+('signature_verified', 'package_badging_verified',
            'binary_manifest_version_only_verified', 'payload_bytes_verified')), 'Exact .36 client/map startup and save-check receipt differs')
    base.checked_file(args.apk, report)
    with tempfile.TemporaryDirectory(prefix='coh-startup-latency-independent-dex-') as temporary:
        _, dex, _ = compile_shell(args, donor, q, Path(temporary))
        require(report.get('recompiled_dex') == base.file_pin(dex), 'Independent exact retained Java DEX differs')
    runtime, preflight = verify_derivative(args.apk, donor, report['payloads'], report['recompiled_dex'], commit, args.native_directory, native,
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


def require_committed_sources(commit, names):
    require(type(names) in (list, tuple, set, frozenset) and names
        and all(type(name) is str and not Path(name).is_absolute()
            and '..' not in Path(name).parts and '\\' not in name for name in names),
        'Exact safe committed source inventory required')
    # Resolve the commit's tree once and batch-read blobs. The full inherited
    # producer/source closure contains thousands of files; spawning git once
    # per source would add avoidable qualification and audit overhead.
    tree = subprocess.check_output(['git', 'ls-tree', '-rz', commit], cwd=ROOT)
    committed = {}
    for raw in tree.split(b'\0'):
        if not raw: continue
        metadata, path = raw.split(b'\t', 1)
        mode, kind, identity = metadata.split(b' ')
        committed[path.decode()] = mode, kind, identity
    ordered = sorted(names)
    require(set(ordered) <= set(committed), 'Every qualified source must exist in the checked-out commit')
    require(all(committed[name][0] in (b'100644', b'100755') and committed[name][1] == b'blob'
        for name in ordered), 'Qualified sources must be committed regular blobs')
    objects = b''.join(committed[name][2]+b'\n' for name in ordered)
    output = subprocess.run(['git', 'cat-file', '--batch'], input=objects, capture_output=True,
        cwd=ROOT, check=True).stdout
    cursor = 0
    for name in ordered:
        newline = output.index(b'\n', cursor)
        identity, kind, length = output[cursor:newline].split(b' ')
        require(identity == committed[name][2] and kind == b'blob', 'Committed source object differs')
        start, length = newline+1, int(length)
        require(output[start:start+length] == (ROOT/name).read_bytes(),
            'Qualified source differs from committed identity: '+name)
        cursor = start+length
        require(output[cursor:cursor+1] == b'\n', 'Committed source stream differs')
        cursor += 1
    require(cursor == len(output), 'Unexpected committed source data')


def require_source_identity(commit):
    require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == commit,
            'Audit and assembly require their exact checked-out source commit')
    require(subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--'], cwd=ROOT, check=False).returncode == 0,
            'Tracked source changed after committed qualification')
    require_committed_sources(commit, SOURCE_FILES)
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
        'donor': donor_link(), 'exact_donor_dex_retained': report['recompiled_dex'],
        'qualified_source_closure': pin(shared.encoded(report['qualification']['source_files'])),
        'candidate_payload_inventory': pin(shared.encoded(report['payloads'])),
        'reviewed_guest_inputs': {Path(name).name: report['payloads']['assets/runtime/'+Path(name).name]
            for name in sorted(GUEST_SOURCE_CHANGES)},
        'runtime_manifest_sha256': report['runtime_manifest_sha256'],
        'inherited_native_launcher': pin(shared.encoded(report['native_launcher'])),
        'current_retained_minimal_db_fixture': pin(shared.encoded(report['minimal_db_native'])),
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
    print('Independent exact .36 signed APK audit passed:', report['sha256'])
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
    audit = args.output/'published-0.13.35-public-byte-audit.zip'
    authenticated_artifact_download(DONOR_PUBLIC_AUDIT_ID, audit, DONOR_PUBLIC_AUDIT)
    with zipfile.ZipFile(audit) as archive:
        require(retained.archive_inventory(archive) == {'client-manual-session-public-byte-audit.json'}, 'Exact accepted public audit required')
        target = args.output/'client-manual-session-public-byte-audit.json'; target.write_bytes(archive.read(target.name))
    builder().checked_file(target, DONOR_PUBLIC_AUDIT_RECEIPT)
    receipt = read_json(target)
    require(receipt['status'] == 'passed' and receipt['repository_commit'] == DONOR_COMMIT
        and receipt['run_id'] == DONOR_RUN_ID and receipt['public_apk_verified'] is True
        and receipt['actual_runtime_asset_installers_verified'] is True
        and receipt['unchanged_assets_1_0_0_metadata_verified'] is True, 'Accepted .35 public-byte proof differs')
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
        'Reviewed .36 publication marker must explicitly enable the qualified successor')
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
    else: raise ValueError('Existing .36 release is never replaced')
    module('profile_repair_head_guard', Path(__file__).with_name('build_client_sidebar_apk.py')).require_current_release_head(client, commit)
    release = client.request('/releases', {'tag_name': RELEASE_TAG, 'target_commitish': commit,
        'name': 'COH Atlas Gameplay 0.13.36 — client and zoning startup latency, progression save checks',
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
    command = commands.add_parser('extract-retained-launcher')
    command.add_argument('--donor-apk', type=Path, required=True)
    command.add_argument('--donor-build-report', type=Path, required=True)
    command.add_argument('--output', type=Path, required=True)
    command = commands.add_parser('verify-assets'); command.add_argument('--donor-build-report', type=Path, required=True)
    for name in ('build', 'audit', 'publish'):
        command = commands.add_parser(name)
        for field in ('donor-apk', 'donor-build-report', 'qualification', 'build-tools', 'android-jar', 'native-directory', 'minimal-db-proof'):
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
    elif args.command == 'extract-retained-launcher':
        donor = validate_donor(args.donor_apk, args.donor_build_report)
        extract_retained_launcher(args.donor_apk, donor, args.output)
    elif args.command == 'verify-assets':
        api = module('startup_latency_asset_reader', Path(__file__).with_name('build_atlas_gameplay_apk.py')).GitHub(os.environ.get('GH_TOKEN'))
        print(json.dumps(verify_asset_release(api, args.donor_build_report.parent), sort_keys=True))
    elif args.command == 'build': build(args)
    elif args.command == 'publish': publish(args)
    else: audit(args, builder().source_commit(args.repository_commit))


if __name__ == '__main__': main()
