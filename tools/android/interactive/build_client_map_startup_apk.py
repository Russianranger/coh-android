#!/usr/bin/env python3
"""Publish .32 from public .31 and a separately authenticated MapServer build.

Only a source-certified SERVER animation validator, a qualified private server
FX projection and reviewed preparation/cleanup helpers change. Game, DbServer,
graphics, Wine/FEX, Android resources and Assets 1.0.0 are retained. Native
component fixtures and complete actual preparation are independent gates;
physical Thor startup, travel and save/reopen remain unqualified here.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile

import build_client_profile_recovery_apk as previous

ROOT, require, module, shared = previous.ROOT, previous.require, previous.module, previous.shared
REPOSITORY, BRANCH, SIGNER, retained = previous.REPOSITORY, previous.BRANCH, previous.SIGNER, previous.retained
read_json, pin, typed_equal = previous.read_json, previous.pin, previous.typed_equal
bounded_download, authenticated_artifact_download = previous.bounded_download, previous.authenticated_artifact_download
DONOR_COMMIT, DONOR_RUN_ID = '74fe247be85173e618f1af2c8af71b1316de4cd8', 38178515521
DONOR_APK_NAME = 'COH-Atlas-Gameplay-0.13.31.apk'
DONOR_APK = {'bytes': 41203812, 'sha256': 'e56df1bcf2210aff131ba80189b1b2dee760f27066e3ee26e09c5fea1654ad80'}
DONOR_REPORT_NAME = 'client-profile-recovery-apk-build-report.json'
DONOR_BUILD = {'bytes': 3735704, 'sha256': '267370f03ac8a57dcdc75705534670f3cacf198674f8fd1ba2edd89e94baf756'}
DONOR_EVIDENCE_ID = 11718575367
DONOR_EVIDENCE = {'bytes': 44957561, 'sha256': '51bcbab8e17efec06786d6e1609c330d050034469666cdc7958a1741d1b018ac'}
DONOR_EVIDENCE_ARCHIVE = 'published-0.13.31-packaging-evidence.zip'
DONOR_EVIDENCE_NAMES = frozenset({DONOR_REPORT_NAME, DONOR_APK_NAME, DONOR_APK_NAME+'.sha256',
    'COH-Atlas-Gameplay-0.13.31-testing.txt'})
DONOR_URL = 'https://github.com/'+REPOSITORY+'/releases/download/coh-atlas-gameplay-v0.13.31/'+DONOR_APK_NAME
DONOR_PUBLIC_AUDIT_ID = 11718088819
DONOR_PUBLIC_AUDIT = {'bytes': 637, 'sha256': '5e75520fc5f775ca2fd41c66daa8a35625bdc6c386965bbc6cdab017b72a6110'}
DONOR_PUBLIC_AUDIT_RECEIPT = {'bytes': 830, 'sha256': '520fff8982e15ead500a34efefe53a43e7ea84c9fbf940075621f55862bcbb7d'}
ASSET_BUILD = {'bytes': 1228, 'sha256': '4eb80545f875218a6a7b087a71823de0024a37444c877412579ce53878d6c3f7'}
VERSION_NAME, VERSION_CODE = '0.13.32', 47
APK_NAME, REPORT_NAME = 'COH-Atlas-Gameplay-0.13.32.apk', 'client-map-startup-apk-build-report.json'
NOTES_NAME, RELEASE_TAG = 'COH-Atlas-Gameplay-0.13.32-testing.txt', 'coh-atlas-gameplay-v0.13.32'
NOTES = ROOT/'docs'/NOTES_NAME
WORKFLOW = '.github/workflows/android-client-map-startup.yml'
QUALIFICATION_SCRIPT = 'tools/android/interactive/qualify_client_map_startup.py'
QUALIFICATION_SCOPE = 'certified_mapserver_startup_and_kings_preparation_retaining_031_game_gpu_and_assets'
GUEST_SOURCE_CHANGES = frozenset('android/guest/'+name for name in (
    'local_character_server.py', 'character_zoning.py', 'game_device_diagnostic.py',
    'native_monorail_contract.py', 'atlas_beacon_package.py',
    'server_animation_package.py', 'server_cache_package.py'))
ADDED_GUEST_SOURCES = frozenset('android/guest/'+name for name in (
    'server_fx_catalog.py', 'native_map_startup_contract.py'))
COMPONENT_PAYLOADS = frozenset({'server-fx-catalog.bin', 'server-fx-catalog-manifest.json',
    'map-startup-manifest.json'})
ADDED_PAYLOADS = frozenset('assets/runtime/'+Path(name).name for name in ADDED_GUEST_SOURCES) | \
    frozenset('assets/runtime/'+name for name in COMPONENT_PAYLOADS)
REPLACED_PAYLOADS = frozenset('assets/runtime/'+Path(name).name for name in GUEST_SOURCE_CHANGES) | \
    frozenset('assets/runtime/'+name for name in ('game-package.tar.gz', 'client-manifest.json', 'runtime-manifest.json'))
CHECKS = ('retained_regressions_and_postgresql_verified', 'actual_runtime_asset_installers_verified',
          'full_startup_orchestration_verified', 'kings_preparation_budgets_and_cleanup_verified',
          'native_animation_and_fx_component_fixtures_verified',
          'exact_031_game_graphics_and_assets_verified')
FALSE_FLAGS = ('native_client_recompiled', 'native_dbserver_recompiled',
    'graphics_driver_changed', 'wine_or_fex_changed',
    'world_assets_changed', 'asset_reimport_required', 'native_runtime_booted', 'save_acceptance_relaxed',
    'physical_recovery_validated', 'physical_kings_row_zoning_validated', 'physical_fps_gain_validated',
    'physical_map_startup_speedup_validated', 'sub_30_second_map_startup_validated')
TRUE_FLAGS = ('retained_android_resources_verified', 'retained_game_and_dbserver_verified',
    'external_assets_1_0_0_reused', 'serialized_game_receipts_verified', 'runtime_refresh_required',
    'guest_helpers_changed', 'actual_runtime_asset_installers_verified', 'java_or_dex_recompiled',
    'full_startup_orchestration_verified', 'native_mapserver_recompiled',
    'native_animation_and_fx_component_fixtures_verified')
SOURCE_FILES = frozenset({WORKFLOW, QUALIFICATION_SCRIPT,
    'docs/android-evidence/client-map-startup-0.13.32-native.json',
    '.github/workflows/android-map-startup-native.yml',
    '.github/workflows/android-game.yml', '.github/workflows/android-map-progress.yml',
    '.github/workflows/android-atlas-game.yml', 'tools/android/run_retained_host_contracts.py',
    'tools/android/interactive/classify_client_map_startup_change.py',
    'tools/android/interactive/build_client_map_startup_apk.py',
    'tools/android/interactive/test_client_map_startup_package.py',
    'tools/android/interactive/package_map_startup_native.py',
    'tools/android/interactive/map_startup_inputs.py',
    'tools/android/interactive/qualify_runtime_asset_preflight.py',
    'tools/android/interactive/test_runtime_asset_preflight.py',
    'tools/android/interactive/qualify_full_startup_preflight.py',
    'tools/android/interactive/test_full_startup_preflight.py',
    'tools/android/interactive/test_character_profile_eligibility.py',
    'tools/android/interactive/test_profile_failure_presentation.py',
    'tools/android/interactive/test_kings_row_runtime_dependencies.py',
    'tools/android/interactive/qualify_runtime_timestamps.py',
    'tools/android/atlasgame/prepare_server_fx_catalog.py',
    'tools/android/atlasgame/prepare_server_fx_control_fixture.py',
    'tools/android/atlasgame/test_server_fx_catalog.py',
    'tools/android/atlasgame/test_device_cleanup_lineage.py',
    'tools/android/interactive/test_kings_preparation_budgets.py',
    'tools/android/interactive/test_complete_asset_stage_acceptance.py',
    'tools/android/interactive/test_completed_guest_report_java.py',
    'tools/prepare_map_startup_source.py', 'tools/prepare_server_fx_catalog_observer_source.py',
    'tools/map_startup_animation_certificate.py', 'tools/test_map_startup_animation_certificate.py',
    'tools/map_startup_namespace_certificate.py', 'tools/test_map_startup_namespace_certificate.py',
    'tools/map_startup_monorail_budget.py', 'tools/test_map_startup_monorail_budget.py',
    'tools/android/game/test_map_startup_monorail_budget.py',
    'tools/android/interactive/test_map_startup_native_contract.py',
    'tools/android/interactive/test_map_startup_cache_reuse.py',
    'tools/android/interactive/fixtures/monorail-game-package-0.13.31.json',
    'docs/android-evidence/client-map-startup-0.13.31-device-result.json',
    'tools/android/interactive/release-client-map-startup-0.13.32.json', 'docs/'+NOTES_NAME})
REVIEWED_JAVA_CHANGES = frozenset('android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/'+name+'.java'
    for name in ('ClientAcceptance', 'ClientRuntime')) | frozenset({
    'android/recovery/src/main/java/io/github/russianranger/cohclientinteractive/ClientReports.java'})
SOURCE_FILES |= REVIEWED_JAVA_CHANGES | GUEST_SOURCE_CHANGES | ADDED_GUEST_SOURCES
REVIEWED_DONOR_SOURCE_CHANGES = GUEST_SOURCE_CHANGES | REVIEWED_JAVA_CHANGES | frozenset({
    '.github/workflows/android-game.yml', '.github/workflows/android-map-progress.yml',
    '.github/workflows/android-atlas-game.yml',
    'tools/android/interactive/classify_client_profile_recovery_change.py',
    'tools/android/interactive/classify_client_animation_repair_change.py',
    'tools/android/interactive/classify_client_receipt_repair_change.py',
    'tools/android/interactive/classify_client_assets_change.py',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py'})
REVIEWED_DONOR_SOURCE_CHANGES |= frozenset({
    'tools/android/interactive/qualify_runtime_asset_preflight.py',
    'tools/android/interactive/qualify_full_startup_preflight.py',
    'tools/android/interactive/test_runtime_asset_preflight.py',
    'tools/android/interactive/test_full_startup_preflight.py'})


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


def historical_test_donor_link():
    return {'source_repository_commit': DONOR_COMMIT,
        'profile_package_donor': previous.donor_link(),
        'receipt_and_animation_donor': previous.historical_test_donor_link()}


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
        and {name for name in java if java[name] != donor['java_sources'][name]} <= REVIEWED_JAVA_CHANGES
        and any(name.endswith('/ClientAcceptance.java') and java[name] != donor['java_sources'][name] for name in java),
        'Complete-asset acceptance repair is required; only the three reviewed acceptance/report Java sources may change')
    for name, expected in donor['java_sources'].items():
        if name not in REVIEWED_JAVA_CHANGES: base.checked_file(ROOT/name, expected)
    for name, expected in donor['payloads'].items():
        if name.startswith('assets/runtime/') and name.endswith('.py'):
            source = 'android/guest/'+Path(name).name
            if source not in GUEST_SOURCE_CHANGES: base.checked_file(ROOT/source, expected)
    for name, expected in donor['qualification']['source_files'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts and '\\' not in name,
                'Unsafe retained source path')
        if name not in REVIEWED_DONOR_SOURCE_CHANGES: base.checked_file(ROOT/name, expected)
    for name, expected in donor['native_build_provenance']['source_files'].items():
        base.checked_file(ROOT/name, expected)
    base.checked_file(ROOT/'android/interactive/src/main/AndroidManifest.xml', donor['qualification']['source_files']['android/interactive/src/main/AndroidManifest.xml'])
    return java


def changed_java_sources(donor):
    return sorted(name for name, expected in current_sources(donor).items()
                  if expected != donor['java_sources'][name])


def replacement_payloads(donor):
    """Require each actual source difference and both exact enclosing manifests."""
    changed = {'assets/runtime/'+name for name in (
        'game-package.tar.gz', 'client-manifest.json', 'runtime-manifest.json')}
    for source in GUEST_SOURCE_CHANGES:
        target = 'assets/runtime/'+Path(source).name
        if builder().file_pin(ROOT/source) != donor['payloads'][target]: changed.add(target)
    require({'assets/runtime/local_character_server.py', 'assets/runtime/character_zoning.py',
             'assets/runtime/game_device_diagnostic.py'} <= changed,
            'Actual Kings preparation, orchestration and cleanup repairs are required')
    return frozenset(changed)


def validate_donor(apk, receipt):
    base = builder(); base.checked_file(apk, DONOR_APK); base.checked_file(receipt, DONOR_BUILD)
    donor = read_json(receipt)
    require(donor['repository_commit'] == donor['runtime_repository_commit'] == DONOR_COMMIT
        and donor['apk'] == DONOR_APK_NAME and donor['version_name'] == '0.13.31' and donor['version_code'] == 46
        and {k: donor[k] for k in ('bytes', 'sha256')} == DONOR_APK
        and donor['signer_certificate_sha256'] == SIGNER and donor['signature_verified'] is True
        and donor['external_asset_release_tag'] == 'coh-assets-v1.0.0' and donor['asset_pack_version'] == '1.0.0'
        and donor['publication_provenance']['run_url'] == 'https://github.com/'+REPOSITORY+'/actions/runs/'+str(DONOR_RUN_ID),
        'Exact accepted public .31 donor identity required')
    require(len(donor['payloads']) == 69, 'Exact .31 payload inventory required')
    with zipfile.ZipFile(apk) as archive:
        shell = {'classes.dex': donor['recompiled_dex'], **donor['retained_android_resources']}
        require(retained.archive_inventory(archive) == set(donor['payloads']) | set(shell) | {'AndroidManifest.xml'},
                'Donor APK inventory differs')
        for name, expected in {**donor['payloads'], **shell}.items():
            require(pin(archive.read(name)) == expected, 'Donor APK member differs: '+name)
        donor['_client_verification'] = json.loads(archive.read('assets/runtime/client-manifest.json'))
        require(typed_equal(json.loads(archive.read('assets/runtime/runtime-manifest.json')), donor['runtime_manifest']),
                'Donor runtime receipt differs from authenticated bytes')
    donor['_apk_path'] = Path(apk)
    with zipfile.ZipFile(apk) as archive:
        require(json.loads(archive.read('assets/runtime/asset-pack-manifest.json')) == donor['external_asset_pack'],
                'Retained asset descriptor differs')
    current_sources(donor)
    return donor


def payload_boundaries(payloads, donor):
    require(set(payloads) == set(donor['payloads']) | ADDED_PAYLOADS
        and len(payloads) == 69 + len(ADDED_PAYLOADS)
        and {name for name in donor['payloads'] if payloads[name] != donor['payloads'][name]}
            == replacement_payloads(donor),
        'Only certified MapServer packaging, reviewed guest repairs and five new startup/FX payloads may change')


def verification_manifests(donor, helper_pins, commit, component, game):
    import package_map_startup_native as native
    require(set(helper_pins) == {Path(name).name for name in GUEST_SOURCE_CHANGES | ADDED_GUEST_SOURCES}
        | COMPONENT_PAYLOADS | {'game-package.tar.gz'}, 'Exact reviewed runtime/startup inputs required')
    helper_pins = {name: helper_pins[name] for name in sorted(helper_pins)}
    client = copy.deepcopy(donor['_client_verification'])
    client['files'].update(helper_pins)
    runtime = copy.deepcopy(donor['runtime_manifest'])
    runtime['files'].update(helper_pins)
    runtime['files']['client-manifest.json'] = pin(shared.encoded(client))
    runtime.update(repository_commit=commit, scope=QUALIFICATION_SCOPE)
    runtime['client_bundle']['local_server']['mapserver'].update(native.runtime_binding(component, game, commit))
    runtime['client_bundle']['local_server']['mapserver']['archive_pin'] = helper_pins['game-package.tar.gz']
    runtime['client_map_startup'] = {'format': 1, 'repository_commit': commit,
        'donor_repository_commit': DONOR_COMMIT, 'publication_provenance': publication_provenance(commit),
        'reviewed_runtime_inputs': helper_pins, 'map_startup_component': component,
        **dict.fromkeys(FALSE_FLAGS, False), **dict.fromkeys(TRUE_FLAGS, True)}
    require(runtime['external_asset_pack'] == donor['runtime_manifest']['external_asset_pack'],
            'Existing installed asset descriptor must remain exact')
    return client, runtime


def actual_asset_preflight(assets):
    import qualify_runtime_asset_preflight as preflight
    asset_cache = Path(os.environ.get('COH_MAP_STARTUP_ASSET_CACHE', ROOT/'out/map-startup-assets'))
    return preflight.preflight(assets, preflight.ensure_assets(asset_cache))


def actual_startup_preflight(assets):
    import qualify_runtime_asset_preflight as asset_preflight
    import qualify_full_startup_preflight as startup
    asset_cache = Path(os.environ.get('COH_MAP_STARTUP_ASSET_CACHE', ROOT/'out/map-startup-assets'))
    return startup.preflight(assets, asset_preflight.ensure_assets(asset_cache))


def extract_and_repair(apk, donor, destination, commit, inputs_directory, *, execute_preflight=True):
    import package_map_startup_native as native
    component = native.validate_component_inputs(inputs_directory, commit)
    destination = Path(destination); destination.mkdir(parents=True)
    base = builder()
    with zipfile.ZipFile(apk) as archive:
        for name in sorted(set(donor['payloads']) | {'classes.dex'} | set(donor['retained_android_resources'])):
            target = destination/name; target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(name) as source, target.open('xb') as output:
                shutil.copyfileobj(source, output, 1024*1024)
    for name, expected in donor['payloads'].items(): base.checked_file(destination/name, expected)
    assets = destination/'assets/runtime'
    helper_pins = {}
    for source in sorted(GUEST_SOURCE_CHANGES | ADDED_GUEST_SOURCES):
        target = assets/Path(source).name
        base.checked_file(ROOT/source)
        target.write_bytes((ROOT/source).read_bytes())
        helper_pins[target.name] = base.file_pin(target)
    for name in sorted(COMPONENT_PAYLOADS):
        target = assets/name
        shutil.copyfile(Path(inputs_directory)/name, target)
        helper_pins[name] = base.file_pin(target)
    actual_component, game = native.patch_game(assets, inputs_directory, commit)
    require(typed_equal(actual_component, component), 'Native component changed during packaging')
    helper_pins['game-package.tar.gz'] = base.file_pin(assets/'game-package.tar.gz')
    client, runtime = verification_manifests(donor, helper_pins, commit, component, game)
    for name, value in (('client-manifest.json', client), ('runtime-manifest.json', runtime)):
        (assets/name).write_bytes(shared.encoded(value))
    payloads = {name: base.file_pin(destination/name) for name in sorted(set(donor['payloads']) | ADDED_PAYLOADS)}
    payload_boundaries(payloads, donor)
    server = retained.verify_server_archives(assets)
    for name in ('dbserver-package.tar.gz', 'dbserver-schema.tar.gz'):
        require(server['archives'][name] == donor['package_preflight']['server_archives']['archives'][name],
                'Exact .31 DbServer/schema archives changed')
    preflight = {'server_archives': server, 'map_startup_component': component}
    if execute_preflight:
        preflight.update(runtime_assets=actual_asset_preflight(assets), full_startup=actual_startup_preflight(assets))
    return runtime, payloads, preflight


def validate_qualification(q, commit, donor, inputs_directory):
    import package_map_startup_native as native
    component = native.validate_component_inputs(inputs_directory, commit)
    contract = module('map_startup_qualification_contract', ROOT/QUALIFICATION_SCRIPT)
    contract.validate_suite_inventory()
    require(type(q.get('format')) is int and q['format'] == 1
        and q.get('status') == 'passed' and q.get('scope') == QUALIFICATION_SCOPE
        and q.get('repository_commit') == q.get('runtime_repository_commit') == commit
        and q.get('donor') == donor_link()
        and typed_equal(q.get('map_startup_component'), component)
        and typed_equal(q.get('historical_test_donor'), historical_test_donor_link())
        and q.get('java_sources') == current_sources(donor)
        and q.get('donor_dex') == donor['recompiled_dex']
        and q.get('changed_java_sources') == changed_java_sources(donor)
        and q.get('external_asset_pack') == donor['external_asset_pack']
        and q.get('native_build_provenance') == donor['native_build_provenance']
        and q.get('check_suites') == contract.CHECK_SUITES and set(q.get('checks', {})) == set(CHECKS)
        and all(q['checks'][name] is True for name in CHECKS)
        and all(q.get(name) is False for name in FALSE_FLAGS)
        and all(q.get(name) is True for name in TRUE_FLAGS), 'Exact MapServer startup/retained .31 qualification required')
    suites = q.get('test_suites', {})
    require(set(suites) == set(contract.TEST_MODULES) and all(row.get('status') == 'passed'
        and row.get('skipped') == 0 and type(row.get('tests_run')) is int and row['tests_run'] > 0
        for row in suites.values()) and q.get('tests_run') == sum(row['tests_run'] for row in suites.values()),
        'Every retained and current regression suite must pass without skips')
    for name, row in suites.items():
        if name in contract.HISTORICAL_PACKAGE_MODULES:
            require(row.get('source_scope') == 'frozen_031_historical_package_contract'
                and row.get('source_repository_commit') == DONOR_COMMIT,
                'Historical fixed package scenarios require their authenticated .31 source scope')
        else:
            require(row.get('source_scope') == 'current_032_candidate_sources',
                    'Current candidate scenarios cannot be replaced by historical fixture results')
    require(q.get('postgresql_emission_fixtures') == sorted((
        'cancelled_child_deletion_commits', 'duplicate_insert_23505_rollback', 'delete_insert_replacement_commits'))
        and q.get('postgresql_levelup_fixtures') == sorted(retained.levelup_postgresql_fixtures()),
        'All seven real PostgreSQL fixtures required')
    import test_character_profile_eligibility as profile
    require(q.get('postgresql_profile_eligibility_fixtures') == sorted(profile.REQUIRED_POSTGRES_FIXTURES)
        and len(q['postgresql_profile_eligibility_fixtures']) == 14,
        'All fourteen PostgreSQL recovery/preservation fixtures required')
    require(set(q.get('source_files', {})) == set(contract.source_paths(donor)), 'Exact qualified source closure required')
    for name, expected in q['source_files'].items(): builder().checked_file(ROOT/name, expected)
    require(type(q.get('package_preflight')) is dict, 'Actual serialized package preflight required')
    full = q['package_preflight'].get('full_startup', {})
    import qualify_full_startup_preflight as startup
    startup.validate_proof(full)
    require(full.get('status') == 'passed' and full.get('scope') == 'actual_packaged_guest_full_startup_orchestration'
        and all(full.get(name) is True for name in ('full_private_worktree_mirror_executed',
            'full_prepare_runtime_executed', 'fresh_create_cold_preparation_verified',
            'saved_reopen_warm_preparation_verified', 'full_kings_row_cold_and_reuse_preparation_verified'))
        and full.get('native_runtime_booted') is False and full.get('physical_execution_validated') is False
        and full.get('process_and_sql_boundary') == 'not_executed',
        'Full host preparation proof required; native process/device boot cannot be claimed')
    return q


def verify_derivative(apk, donor, payloads, dex_pin, commit, inputs_directory):
    base = builder(); payload_boundaries(payloads, donor); base.verify_packaged_payloads(apk, payloads)
    require(dex_pin != donor['recompiled_dex'] and set(dex_pin) == {'bytes', 'sha256'},
            'Reviewed complete-asset acceptance Java must produce changed DEX')
    with zipfile.ZipFile(apk) as archive:
        shell = {'classes.dex': dex_pin, **donor['retained_android_resources']}
        require(retained.archive_inventory(archive) == set(payloads) | set(shell) | {'AndroidManifest.xml'},
                'Candidate APK inventory differs')
        for name, expected in shell.items(): require(pin(archive.read(name)) == expected, 'Candidate DEX/resources differ: '+name)
    with tempfile.TemporaryDirectory(prefix='coh-profile-audit-') as temporary:
        runtime, expected, preflight = extract_and_repair(donor['_apk_path'], donor, Path(temporary)/'donor', commit, inputs_directory,
                                                       execute_preflight=False)
        require(payloads == expected, 'Reconstructed public .31 plus exact certified MapServer/FX/helpers differs')
    require(retained.verify_apk_server_archives(apk) == preflight['server_archives'], 'Actual APK server extraction differs')
    # Exercise actual helpers extracted from the final APK against the retained
    # public asset bytes, independently of the reconstructed expected hashes.
    with tempfile.TemporaryDirectory(prefix='coh-profile-actual-') as temporary, zipfile.ZipFile(apk) as archive:
        directory = Path(temporary)
        for name in sorted(payloads):
            if name.startswith('assets/runtime/'):
                target = directory/Path(name).name
                target.write_bytes(archive.read(name))
        # The complete heavyweight preparation runs on actual candidate bytes.
        # Hash reconstruction above remains separate and need not mirror the
        # original 173k imported leaves a second time in this same audit.
        preflight.update(runtime_assets=actual_asset_preflight(directory),
                         full_startup=actual_startup_preflight(directory))
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
    donor = validate_donor(args.donor_apk, args.donor_build_report)
    q = validate_qualification(read_json(args.qualification), commit, donor, args.map_startup_inputs)
    password = base.signing_password_spec(args.password_env)
    base.verify_signing_identity(args.keystore, 'coh-client-interactive', SIGNER, password)
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), 'Fresh .32 APK required')
    base.checked_file(args.testing_notes); require(0 < args.testing_notes.stat().st_size <= 65536, 'Bounded testing notes required')
    for tool in (args.android_jar, args.build_tools/'aapt2', args.build_tools/'zipalign', args.build_tools/'lib/d8.jar', args.build_tools/'lib/apksigner.jar'):
        require(tool.is_file() and not tool.is_symlink(), 'Required Android SDK tool missing')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-profile-build-', dir=args.output.parent) as temporary:
        work = Path(temporary)
        runtime, payloads, preflight = extract_and_repair(args.donor_apk, donor, work/'donor', commit, args.map_startup_inputs,
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
        _, signed_preflight = verify_derivative(signed, donor, payloads, dex_pin, commit, args.map_startup_inputs)
        require_signed_preflight(signed_preflight, q)
        preflight = signed_preflight
        retained.verify_binary_manifest(signed, args.donor_apk, args.build_tools)
        shutil.copyfile(signed, args.output)
        report = {'format': 1, 'apk': APK_NAME, **base.file_pin(args.output), 'repository_commit': commit,
            'runtime_repository_commit': commit, 'retained_runtime_repository_commit': DONOR_COMMIT,
            'application_id': base.APP_ID, 'version_name': VERSION_NAME, 'version_code': VERSION_CODE,
            'abi': 'arm64-v8a', 'scope': QUALIFICATION_SCOPE, 'donor': donor_link(), 'map_startup_component': q['map_startup_component'],
            'signer_certificate_sha256': certificate, 'signing_key_created': False, 'signature_verified': True,
            'package_badging_verified': True, 'binary_manifest_version_only_verified': True, 'payload_bytes_verified': True,
            'payloads': payloads, 'changed_apk_payloads': sorted(replacement_payloads(donor)), 'added_apk_payloads': sorted(ADDED_PAYLOADS),
            'baseline_payloads_verified': 69, 'retained_baseline_payloads_verified': 69-len(replacement_payloads(donor)),
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
    # The signed bytes were fully prepared above. The workflow then performs
    # fresh-process report/signature/DEX/full-preparation admission before
    # uploading an accepted artifact or publishing; repeating that complete
    # mirror inside this same build would add no independent evidence.
    base.checked_file(args.output, report)
    return report


def verify_report(args, commit):
    base, current = builder(), builder(repaired=True)
    donor = validate_donor(args.donor_apk, args.donor_build_report)
    q = validate_qualification(read_json(args.qualification), commit, donor, args.map_startup_inputs); report = read_json(args.build_report)
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
        and report.get('baseline_payloads_verified') == 69 and report.get('retained_baseline_payloads_verified') == 69-len(replacement_payloads(donor))
        and all(report.get(name) is False for name in FALSE_FLAGS)
        and all(report.get(name) is True for name in TRUE_FLAGS+('signature_verified', 'package_badging_verified',
            'binary_manifest_version_only_verified', 'payload_bytes_verified')), 'Exact .32 certified MapServer/preparation receipt differs')
    base.checked_file(args.apk, report)
    with tempfile.TemporaryDirectory(prefix='coh-profile-independent-dex-') as temporary:
        _, dex, _ = compile_shell(args, donor, q, Path(temporary))
        require(report.get('recompiled_dex') == base.file_pin(dex), 'Independent reviewed Java DEX compilation differs')
    runtime, preflight = verify_derivative(args.apk, donor, report['payloads'], report['recompiled_dex'], commit, args.map_startup_inputs)
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


def download_donor_evidence(args):
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh donor evidence directory required')
    args.output.mkdir(parents=True); target = args.output/DONOR_EVIDENCE_ARCHIVE
    authenticated_artifact_download(DONOR_EVIDENCE_ID, target, DONOR_EVIDENCE)
    with zipfile.ZipFile(target) as archive:
        require(retained.archive_inventory(archive) == DONOR_EVIDENCE_NAMES, 'Exact .31 evidence inventory required')
        for entry in archive.infolist():
            require(not entry.is_dir() and 0 < entry.file_size <= 64*1024**2, 'Bounded flat evidence required')
            (args.output/entry.filename).write_bytes(archive.read(entry))
    builder().checked_file(args.output/DONOR_REPORT_NAME, DONOR_BUILD)
    audit = args.output/'published-0.13.31-public-byte-audit.zip'
    authenticated_artifact_download(DONOR_PUBLIC_AUDIT_ID, audit, DONOR_PUBLIC_AUDIT)
    with zipfile.ZipFile(audit) as archive:
        require(retained.archive_inventory(archive) == {'client-profile-recovery-public-byte-audit.json'}, 'Exact accepted public audit required')
        target = args.output/'client-profile-recovery-public-byte-audit.json'; target.write_bytes(archive.read(target.name))
    builder().checked_file(target, DONOR_PUBLIC_AUDIT_RECEIPT)
    receipt = read_json(target)
    require(receipt['status'] == 'passed' and receipt['repository_commit'] == DONOR_COMMIT
        and receipt['run_id'] == DONOR_RUN_ID and receipt['public_apk_verified'] is True
        and receipt['actual_runtime_asset_installers_verified'] is True
        and receipt['unchanged_assets_1_0_0_metadata_verified'] is True, 'Accepted .31 public-byte proof differs')
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
    require(os.environ.get('GITHUB_REPOSITORY') == REPOSITORY and os.environ.get('GITHUB_REF') == 'refs/heads/'+BRANCH
        and os.environ.get('GITHUB_EVENT_NAME') in ('push', 'workflow_dispatch'), 'Publication requires continuation branch')
    commit = builder().source_commit(os.environ.get('GITHUB_SHA')); report, checksum, notes = verify_report(args, commit)
    client = module('profile_repair_github', Path(__file__).with_name('build_atlas_gameplay_apk.py')).GitHub(os.environ.get('GH_TOKEN'))
    verify_asset_release(client, args.donor_build_report.parent)
    try: client.request('/releases/tags/'+RELEASE_TAG)
    except urllib.error.HTTPError as error:
        if error.code != 404: raise
    else: raise ValueError('Existing .32 release is never replaced')
    module('profile_repair_head_guard', Path(__file__).with_name('build_client_sidebar_apk.py')).require_current_release_head(client, commit)
    release = client.request('/releases', {'tag_name': RELEASE_TAG, 'target_commitish': commit,
        'name': 'COH Atlas Gameplay 0.13.32 — certified MapServer startup and Kings preparation repair',
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
        for field in ('donor-apk', 'donor-build-report', 'qualification', 'build-tools', 'android-jar', 'map-startup-inputs'):
            command.add_argument('--'+field, type=Path, required=True)
        command.add_argument('--repository-commit', default=os.environ.get('GITHUB_SHA'))
        command.add_argument('--testing-notes', type=Path, default=NOTES)
        if name == 'build':
            for field in ('keystore', 'output'): command.add_argument('--'+field, type=Path, required=True)
            command.add_argument('--password-env', default='COH_INTERACTIVE_KEYSTORE_PASSWORD')
        else:
            for field in ('apk', 'build-report'): command.add_argument('--'+field, type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'download-donor': bounded_download(DONOR_URL, args.output, DONOR_APK)
    elif args.command == 'download-donor-evidence': download_donor_evidence(args)
    elif args.command == 'download-public': download_public(args)
    elif args.command == 'verify-assets':
        api = module('profile_repair_asset_reader', Path(__file__).with_name('build_atlas_gameplay_apk.py')).GitHub(os.environ.get('GH_TOKEN'))
        print(json.dumps(verify_asset_release(api, args.donor_build_report.parent), sort_keys=True))
    elif args.command == 'build': build(args)
    elif args.command == 'publish': publish(args)
    else: print('Independent exact .32 audit passed:', verify_report(args, builder().source_commit(args.repository_commit))[0]['sha256'])


if __name__ == '__main__': main()
