#!/usr/bin/env python3
"""Package the recovery shell over the exact, physically accepted public .26 runtime.

The accepted Game, its original native proof, servers, GPU driver/probes, assets,
and graphics recipe are immutable inputs. Only explicitly reviewed Java and
guest control helpers are compiled/replaced. Historical producers are imported
without changing their global contracts or relabelling their receipts.
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
import subprocess
import tempfile
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile

import build_client_recovery_apk as previous
import package_external_assets as packs

ROOT, require, module, shared = previous.ROOT, previous.require, previous.module, previous.shared
REPOSITORY, BRANCH, SIGNER = previous.REPOSITORY, previous.BRANCH, previous.SIGNER
retained, engine = previous.retained, previous.engine
read_json, read_json_value, pin = previous.read_json, previous.read_json_value, previous.pin
native_producer = previous.native_producer
DONOR_COMMIT, DONOR_RUN_ID = '31fe36f64bd23648afc4ec3ba729e7f44dd7f40b', 38103463724
DONOR_APK_NAME = 'COH-Atlas-Gameplay-0.13.27.apk'
DONOR_APK = {'bytes': 1560390578, 'sha256': '25afcd1c4d4afb55990e295a5fdcf4daab18389d461f2ffaf7d9455676edd49f'}
DONOR_REPORT_NAME = 'client-recovery-apk-build-report.json'
DONOR_BUILD = {'bytes': 5653405, 'sha256': '1d92f170cceabaa185f6c5a135d30d28fcdbcd5ac167eba9355d5b67e74bc596'}
DONOR_EVIDENCE_ID = 11688289908
DONOR_EVIDENCE = {'bytes': 1310663, 'sha256': '3be26bff3c9e9191534fa9e08fcff10d25ae7873621cf82de54ae94cf437075f'}
DONOR_EVIDENCE_ARCHIVE = 'published-0.13.27-packaging-evidence.zip'
DONOR_EVIDENCE_NAMES = frozenset({DONOR_REPORT_NAME, DONOR_APK_NAME+'.sha256', 'COH-Atlas-Gameplay-0.13.27-testing.txt'})
DONOR_URL = 'https://github.com/'+REPOSITORY+'/releases/download/coh-atlas-gameplay-v0.13.27/'+DONOR_APK_NAME
NATIVE_COMMIT, NATIVE_RUN_ID = 'c512e912a004b66886a7667640aa1a967e95de64', 37988347729
NATIVE_ARTIFACT_ID = 11645013072
NATIVE_ARTIFACT = {'bytes': 4056854, 'sha256': '9fc53a1e7f939a25ffdd0eb7feebe1dd13089f31ee4c8bc25002fcdae354c4e7'}
NATIVE_MANIFEST = {'bytes': 89634, 'sha256': '3d7bc219573c1ba0dba2819c4d74902ccc8379b499061491d00a46c7dd030f9a'}
DONOR_GAME = {'bytes': 9499648, 'sha256': '5f9597fac6e5c4eb2bf6ab091a8b2b5d71c341371da04dc135cef7e5fe00010b'}
VERSION_NAME, VERSION_CODE = '0.13.28', 43
APK_NAME, REPORT_NAME = 'COH-Atlas-Gameplay-0.13.28.apk', 'client-assets-apk-build-report.json'
NOTES_NAME = 'COH-Atlas-Gameplay-0.13.28-testing.txt'
NOTES, RELEASE_TAG = ROOT/'docs'/NOTES_NAME, 'coh-atlas-gameplay-v0.13.28'
WORKFLOW = '.github/workflows/android-client-assets.yml'
QUALIFICATION_SCRIPT = 'tools/android/interactive/qualify_client_assets.py'
QUALIFICATION_SCOPE = 'versioned_external_assets_stock_monorail_kings_row_storage_repair_retaining_game_0_13_25'
RECOVERY_PROFILE = {'character_zoning_enabled':True, 'startup_only_reopen':False, 'task_gate_required':False}
JAVA_ROOT = 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/'
ZONING_JAVA_ROOT = 'android/zoning/src/main/java/io/github/russianranger/cohclientinteractive/'
RECOVERY_JAVA_ROOT = 'android/recovery/src/main/java/io/github/russianranger/cohclientinteractive/'
APP_JAVA_ROOT = 'android/app/src/main/java/io/github/russianranger/cohdiagnostic/'
JAVA_CHANGES = frozenset({*(JAVA_ROOT+name+'.java' for name in ('ClientActivity','ClientRuntime',
    'ClientAcceptance','ClientSessionBudget','StorageAudit','StorageFiles')),
    ZONING_JAVA_ROOT+'ClientZoning.java', APP_JAVA_ROOT+'DiagnosticRuntime.java'})
JAVA_ADDITIONS = frozenset(APP_JAVA_ROOT+name+'.java' for name in ('AssetPackArchive','AssetPackStore'))
RETAINED_JAVA_ADDITIONS = previous.RETAINED_JAVA_ADDITIONS|previous.JAVA_ADDITIONS
HELPERS = frozenset({'character_zoning.py','character_reopen_diagnostic.py','game_diagnostic.py',
    'client_startup_diagnostic.py','character_creation_diagnostic.py',
    'atlas_world_assets.py','client_visual_assets.py','atlas_beacon_package.py',
    'character_avatar_assets.py','client_animation_package.py','local_character_server.py',
    'character_session_budget.py','server_cache_package.py'})
ADDED_HELPERS = frozenset({'native_monorail_events.py','native_monorail_contract.py',
    'zone_asset_package.py','kings_row_beacon_package.py'})
BASELINE_PAYLOAD_COUNT, DONOR_JAVA_COUNT = 79, 22
REPLACED_PAYLOADS = frozenset('assets/runtime/'+name for name in HELPERS|{
    'client-manifest.json','runtime-manifest.json','game-package.tar.gz'})
ADDED_PAYLOADS = frozenset('assets/runtime/'+name for name in ADDED_HELPERS|{
    'asset-pack-manifest.json','kings-row-beacon-lock.json'})
EXTERNAL_PAYLOADS = frozenset('assets/'+name for name in packs.BASE_FILES)
CHECKS = ('external_asset_import_storage_and_monorail_guards_verified',
    'retained_gameplay_postgresql_gpu_cleanup_and_recovery_guards_verified',
    'exact_027_native_graphics_assets_and_reviewed_shell_verified')
SOURCE_FILES = frozenset({WORKFLOW, QUALIFICATION_SCRIPT,
    'tools/android/interactive/build_client_assets_apk.py',
    'tools/android/interactive/package_external_assets.py',
    'tools/android/interactive/test_external_assets.py',
    'tools/android/interactive/test_client_assets_package.py',
    'tools/android/interactive/test_asset_pack_import.py',
    'tools/android/interactive/test_storage_files.py',
    'tools/android/interactive/test_storage_audit.py',
    'tools/android/interactive/test_runtime_setup_reuse.py',
    'tools/android/interactive/audit_kings_row_foundation.py',
    'tools/android/interactive/prepare_zones_world_assets.py',
    '.github/workflows/android-kings-row-native.yml',
    'tools/android/interactive/test_character_zoning.py',
    'tools/android/interactive/test_client_zoning_java.py',
    'docs/'+NOTES_NAME,
    *JAVA_CHANGES, *JAVA_ADDITIONS, *('android/guest/'+name for name in HELPERS|ADDED_HELPERS)})
REVIEWED_DONOR_SOURCE_CHANGES = SOURCE_FILES | frozenset({'docs/HANDOFF.md'})
FALSE_FLAGS = tuple(name for name in previous.FALSE_FLAGS if name not in {
    'native_mapserver_recompiled','world_assets_changed','asset_reimport_required'})
TRUE_FLAGS = previous.TRUE_FLAGS + ('native_mapserver_recompiled','world_assets_changed',
    'external_asset_pack_required','all_asset_volumes_required_for_fresh_install')
RETAINED_FIELDS = tuple(name for name in previous.RETAINED_FIELDS if name != 'server_payload_extraction_preflight') + ('client_recovery',)
ASSET_RELEASE_TAG = 'coh-assets-v'+packs.VERSION


def builder(*, repaired=False):
    result = previous.builder()
    if repaired: result.VERSION_NAME, result.VERSION_CODE, result.APK_NAME = VERSION_NAME, VERSION_CODE, APK_NAME
    return result


def typed_equal(left, right):
    return json.dumps(left, sort_keys=True, separators=(',', ':'), allow_nan=False) == json.dumps(
        right, sort_keys=True, separators=(',', ':'), allow_nan=False)


def donor_link():
    return {'run_id': DONOR_RUN_ID, 'repository_commit': DONOR_COMMIT, 'apk': DONOR_APK,
        'build_report': DONOR_BUILD, 'build_report_artifact_id': DONOR_EVIDENCE_ID,
        'build_report_artifact_zip': DONOR_EVIDENCE}


def donor_evidence_members(path):
    builder().checked_file(path, DONOR_EVIDENCE)
    with zipfile.ZipFile(path) as archive:
        require(retained.archive_inventory(archive) == DONOR_EVIDENCE_NAMES, 'Exact authenticated .27 evidence ZIP required')
        result = {}
        for entry in archive.infolist():
            require(not entry.is_dir() and 0 < entry.file_size <= 16*1024**2, 'Unsafe donor evidence member')
            result[entry.filename] = pin(archive.read(entry))
        return result


def validate_donor_receipt(path):
    expected = donor_evidence_members(path.parent/DONOR_EVIDENCE_ARCHIVE)[DONOR_REPORT_NAME]
    require(expected == DONOR_BUILD, 'Authenticated raw .27 receipt pin differs')
    builder().checked_file(path, expected); donor = read_json(path); q = donor.get('qualification', {})
    require(type(donor.get('format')) is int and donor['format'] == 1
        and donor.get('repository_commit') == donor.get('runtime_repository_commit') == DONOR_COMMIT
        and donor.get('apk') == DONOR_APK_NAME and {key:donor.get(key) for key in DONOR_APK} == DONOR_APK
        and donor.get('application_id') == builder().APP_ID and donor.get('version_name') == '0.13.27'
        and type(donor.get('version_code')) is int and donor['version_code'] == 42
        and donor.get('abi') == 'arm64-v8a' and donor.get('signer_certificate_sha256') == SIGNER
        and donor.get('signing_key_created') is False and len(donor.get('payloads', {})) == BASELINE_PAYLOAD_COUNT
        and len(donor.get('java_sources', {})) == DONOR_JAVA_COUNT and q.get('status') == 'passed'
        and q.get('repository_commit') == DONOR_COMMIT and q.get('scope') == previous.QUALIFICATION_SCOPE
        and q.get('tests_run') == 1845 and len(q.get('test_suites', {})) == 128
        and all(value.get('status') == 'passed' and value.get('skipped') == 0 for value in q['test_suites'].values())
        and all(donor.get(key) is True for key in ('signature_verified', 'package_badging_verified',
            'binary_manifest_version_only_verified', 'payload_bytes_verified'))
        and donor.get('java_or_dex_recompiled') is True
        and donor.get('retained_native_repository_commit') == NATIVE_COMMIT
        and donor.get('native_client_compiled_in_current_publication_run') is False
        and typed_equal(donor.get('runtime_profile'),RECOVERY_PROFILE)
        and all(donor['runtime_manifest'].get(name) is value for name,value in RECOVERY_PROFILE.items()),
        'Exact independently authenticated published .27 donor required')
    native = donor.get('native_build_provenance', {})
    require(native.get('repository_commit') == NATIVE_COMMIT and native.get('run_id') == NATIVE_RUN_ID
        and native.get('game') == DONOR_GAME and native.get('native_manifest') == NATIVE_MANIFEST
        and native.get('raw_producer_preserved') is True
        and native.get('compiled_in_current_publication_run') is False, 'Original accepted .25 native identity differs')
    return donor


def validate_retained_sources(donor):
    for name, expected in donor['qualification']['source_files'].items():
        require(type(name) is str and not Path(name).is_absolute() and '..' not in Path(name).parts
            and chr(92) not in name, 'Unsafe retained source path')
        if name not in REVIEWED_DONOR_SOURCE_CHANGES: builder().checked_file(ROOT/name, expected)
    # Compiled native sources are never covered by the reviewed Java/guest scope.
    for name, expected in donor['native_build_provenance']['source_files'].items():
        builder().checked_file(ROOT/name, expected)


def current_java_sources(donor, generated):
    base = builder(); sources = retained.retained.java_sources(base, generated)
    for name in sorted(RETAINED_JAVA_ADDITIONS|JAVA_ADDITIONS):
        source = ROOT/name; base.checked_file(source)
        require(source not in sources and re.findall(r'^package\s+([A-Za-z0-9_.]+)\s*;',source.read_text(),re.M) == [name.split('/java/')[1].rsplit('/',1)[0].replace('/','.')],
            'Explicit recovery Java addition must have the exact package and appear once')
        sources.append(source)
    pins = {path.relative_to(ROOT).as_posix():base.file_pin(path) for path in sources
        if path.is_relative_to(ROOT) and not path.is_relative_to(generated)}
    require(set(pins) == set(donor['java_sources']) | JAVA_ADDITIONS, 'Unexpected authored Java inventory')
    changed = {name for name in donor['java_sources'] if pins[name] != donor['java_sources'][name]}
    require(changed == JAVA_CHANGES, 'Java changes exceed reviewed recovery scope')
    for name, expected in donor['preserved_sources'].items():
        if name not in donor['java_sources']: base.checked_file(ROOT/name, expected)
    base.checked_file(ROOT/'android/interactive/src/main/AndroidManifest.xml', donor['source_manifest'])
    for name, expected in donor['payloads'].items():
        if name.startswith('assets/runtime/') and name.endswith('.py'):
            current = ROOT/'android/guest'/Path(name).name
            if Path(name).name in HELPERS:
                require(base.file_pin(current) != expected, 'Reviewed guest helper must actually change: '+name)
            else: base.checked_file(current, expected)
    require(all('assets/runtime/'+name not in donor['payloads'] for name in ADDED_HELPERS), 'Added helper already exists in donor')
    validate_retained_sources(donor)
    return sources, pins, sorted(changed)


def validate_retained_native(directory, donor):
    directory = Path(directory); base = builder()
    base.checked_file(directory/native_producer().MANIFEST, NATIVE_MANIFEST)
    base.checked_file(directory/'CityOfHeroes.exe', DONOR_GAME)
    native = native_producer().validate_package(directory, NATIVE_COMMIT)
    require(typed_equal(native, donor['native_client_render_queue'])
        and native['run_url'] == 'https://github.com/'+REPOSITORY+'/actions/runs/'+str(NATIVE_RUN_ID),
        'Original native Game, CMake and Win32 proof required without relabelling')
    for name, expected in donor['native_build_provenance']['source_files'].items(): base.checked_file(ROOT/name, expected)
    return native


def validate_donor(apk, receipt, retained_client_directory):
    base = builder(); base.checked_file(apk, DONOR_APK); donor = validate_donor_receipt(receipt)
    native = validate_retained_native(retained_client_directory, donor)
    base.verify_packaged_payloads(apk, donor['payloads'])
    with zipfile.ZipFile(apk) as archive:
        shell = {'classes.dex':donor['recompiled_dex'], **donor['retained_android_resources']}
        require(retained.archive_inventory(archive) == set(donor['payloads'])|set(shell)|{'AndroidManifest.xml'}, 'Exact .26 APK inventory required')
        for name, expected in shell.items(): require(pin(archive.read(name)) == expected, 'Donor Android shell differs: '+name)
        require(typed_equal(read_json_value(archive.read('assets/runtime/runtime-manifest.json')), donor['runtime_manifest']), 'Donor runtime manifest differs')
        donor['_client_verification'] = read_json_value(archive.read('assets/runtime/client-manifest.json'))
        with archive.open('assets/runtime/client-runtime.zip') as source, tempfile.TemporaryFile() as target:
            shutil.copyfileobj(source, target, 1024*1024); target.seek(0)
            with zipfile.ZipFile(target) as client:
                package = read_json_value(client.read('client-package.json'))
                record = shared.native_contract.client_contract(package, donor['immutable_donor_provenance']['native_responsiveness'])
                members = engine.startup.startup.client_member_pins(client)
                dlls = donor['immutable_donor_provenance']['native_responsiveness']['retained_native_files']['client']
                require(typed_equal(record, native['files']['CityOfHeroes.exe'])
                    and members.get('CityOfHeroes.exe') == DONOR_GAME
                    and len(dlls) == 20 and set(members) == set(dlls)|{'CityOfHeroes.exe','client-package.json'}
                    and all(members[name] == {'bytes':expected['size'],'sha256':expected['sha256']} for name,expected in dlls.items())
                    and typed_equal(package['client_render_queue']['manifest'], native), 'Actual native Game/DLL/provenance closure differs')
                donor['_native_client_manifest'] = package
    require(retained.verify_apk_server_archives(apk) == donor['server_payload_extraction_preflight'], 'Retained server extraction differs')
    validate_retained_sources(donor)
    donor['_apk_path'] = apk
    return donor


def validate_actual_native_ancestry(donor, native):
    # Reconstruct the immutable .24 parent view from authenticated .25 records;
    # this runs the production typed reader and adversarial ancestry checks.
    ancestor = copy.deepcopy(donor['_native_client_manifest'])
    ancestor.pop('client_render_queue')
    ancestor['files']['CityOfHeroes.exe'] = copy.deepcopy(native['base_client_executable'])
    ancestor['dependency_report'] = shared.dependency_report(ancestor['files'])
    inherited = dict(donor, _native_client_manifest=ancestor)
    contract = module('recovery_actual_native_ancestry', ROOT/'tools/android/interactive/test_client_render_queue_contract.py')
    return contract.validate_actual_native_ancestry(inherited, native)


def publication_provenance(commit):
    owner = os.environ.get('GITHUB_RUN_ID')
    require(owner is None or re.fullmatch('[1-9][0-9]*', owner), 'Exact publication owner required')
    return {'format':1, 'repository_commit':commit,
        'run_url':'https://github.com/'+REPOSITORY+'/actions/runs/'+owner if owner else None,
        'donor_apk_repository_commit':DONOR_COMMIT, 'retained_native_repository_commit':NATIVE_COMMIT,
        'retained_native_run_id':NATIVE_RUN_ID, 'native_producer_relabelled':False}


def recovery_contract():
    return {'format':1, 'changed_guest_helpers':sorted(HELPERS), 'added_guest_helpers':sorted(ADDED_HELPERS),
        **RECOVERY_PROFILE, 'character_monorail_enabled':True, 'station_map_ids':[1,5],
        'asset_pack_id':packs.PACK_ID,'asset_pack_version':packs.VERSION,
        'scope':'Versioned external asset volumes, storage repair and stock Kings Row monorail preparation',
        'native_Game_sha256':DONOR_GAME['sha256'],'native_Game_changed_from_public_0_13_27':False,
        'native_Game_build_repeated':False,'native_MapServer_rebuilt':True,'graphics_settings_changed':False,
        'physical_recovery_validated':False,'physical_preparation_speedup_validated':False,
        'physical_kings_row_zoning_validated':False}


def asset_contract(directory, *, verify_volumes=False):
    directory = Path(directory); manifest = packs.validate_manifest(read_json(directory/packs.MANIFEST))
    require(manifest['version'] == packs.VERSION and set(manifest['volumes']) == {'base','reference','zones'}
        and set(manifest['volumes']['base']) == packs.BASE_FILES
        and manifest['volumes']['reference'] == [packs.REFERENCE_FILE], 'Exact versioned asset layout required')
    if verify_volumes:
        for volume in manifest['volumes']:
            packs.verify_volume(directory/packs.volume_filename(packs.VERSION,volume),manifest,volume)
    return manifest


def verification_manifests(donor, updates, commit, asset_manifest, monorail):
    require(set(updates) == HELPERS|ADDED_HELPERS|{'game-package.tar.gz','asset-pack-manifest.json','kings-row-beacon-lock.json'},
        'Exact reviewed helper, native MapServer, lock and asset descriptor inputs required')
    client = copy.deepcopy(donor['_client_verification']); client['files'].update(updates)
    runtime = copy.deepcopy(donor['runtime_manifest']); runtime['files'].update(updates)
    # Imported original archives retain their accepted pins; the new complete zone
    # supplements are independently bound by the APK-owned asset manifest.
    for name, expected in asset_manifest['files'].items():
        if name.startswith('runtime/'):
            runtime['files'][name[8:]] = expected
            client['files'][name[8:]] = expected
    runtime['files']['client-manifest.json'] = pin(shared.encoded(client))
    runtime.update(repository_commit=commit,scope=QUALIFICATION_SCOPE,character_monorail_enabled=True)
    runtime.update(RECOVERY_PROFILE)
    runtime['external_asset_pack'] = {'format':1,'id':packs.PACK_ID,'version':packs.VERSION,
        'manifest_sha256':updates['asset-pack-manifest.json']['sha256'],
        'manifest_bytes':updates['asset-pack-manifest.json']['bytes'], 'release_tag':ASSET_RELEASE_TAG}
    runtime['client_monorail'] = {**recovery_contract(),'repository_commit':commit,
        'donor_apk_repository_commit':DONOR_COMMIT,'mapserver_native_build':monorail,
        'publication_provenance':publication_provenance(commit)}
    return client,runtime


def payload_boundaries(payloads, donor):
    require(set(payloads) == (set(donor['payloads'])-EXTERNAL_PAYLOADS)|ADDED_PAYLOADS,
        'Only explicit external assets may leave the APK; exact new helpers and descriptor required')
    require({name for name in set(donor['payloads'])-EXTERNAL_PAYLOADS
        if payloads[name] != donor['payloads'][name]} == REPLACED_PAYLOADS,
        'Native Game, graphics, DbServer, settings and retained payloads must remain exact')


def extract_and_repair(apk, donor, destination, commit, asset_directory, native_directory, native_commit):
    destination.mkdir(parents=True); base = builder()
    with zipfile.ZipFile(apk) as archive:
        require(retained.archive_inventory(archive) == set(donor['payloads'])|set(donor['retained_android_resources'])|{'AndroidManifest.xml','classes.dex'}, 'Unexpected donor inventory')
        for entry in archive.infolist():
            if entry.filename == 'AndroidManifest.xml' or entry.filename in EXTERNAL_PAYLOADS or entry.filename.startswith('META-INF/'): continue
            target = destination/entry.filename; target.parent.mkdir(parents=True,exist_ok=True)
            with archive.open(entry) as source,target.open('xb') as output: shutil.copyfileobj(source,output,1024*1024)
    require(all(base.file_pin(destination/name) == expected for name,expected in donor['payloads'].items()
        if name not in EXTERNAL_PAYLOADS),'Extracted .27 donor differs')
    assets = destination/'assets/runtime'; descriptor = asset_contract(asset_directory)
    for name in HELPERS|ADDED_HELPERS: shutil.copyfile(ROOT/'android/guest'/name,assets/name)
    shutil.copyfile(Path(asset_directory)/packs.MANIFEST,assets/packs.MANIFEST)
    shutil.copyfile(Path(asset_directory)/'kings-row-beacon-lock.json',assets/'kings-row-beacon-lock.json')
    import package_monorail_native as bridge
    monorail,game = bridge.patch_game(assets,native_directory,commit,native_commit)
    updates = {name:base.file_pin(assets/name) for name in HELPERS|ADDED_HELPERS|{
        'game-package.tar.gz','asset-pack-manifest.json','kings-row-beacon-lock.json'}}
    client,runtime = verification_manifests(donor,updates,commit,descriptor,monorail)
    for name,value in (('client-manifest.json',client),('runtime-manifest.json',runtime)): (assets/name).write_bytes(shared.encoded(value))
    payloads = {name:base.file_pin(destination/name) for name in sorted((set(donor['payloads'])-EXTERNAL_PAYLOADS)|ADDED_PAYLOADS)}
    payload_boundaries(payloads,donor)
    preflight = retained.verify_server_archives(assets)
    for name in ('dbserver-package.tar.gz','dbserver-schema.tar.gz'):
        require(preflight['archives'][name] == donor['server_payload_extraction_preflight']['archives'][name], 'Unchanged DbServer archive differs')
    return runtime,payloads,preflight


def verify_derivative(apk, donor, payloads, dex_pin, commit, asset_directory, native_directory, native_commit):
    base = builder(); payload_boundaries(payloads,donor)
    require(dex_pin != donor['recompiled_dex'],'Reviewed Java shell must compile a new DEX')
    base.verify_packaged_payloads(apk,payloads)
    with tempfile.TemporaryDirectory(prefix='coh-assets-audit-') as temporary:
        runtime,expected,preflight = extract_and_repair(apk=donor['_apk_path'],donor=donor,destination=Path(temporary)/'donor',
            commit=commit,asset_directory=asset_directory,native_directory=native_directory,native_commit=native_commit)
        require(payloads == expected,'Reconstructed exact donor plus reviewed changes differs')
    with zipfile.ZipFile(apk) as archive:
        shell = {'classes.dex':dex_pin,**donor['retained_android_resources']}
        require(retained.archive_inventory(archive) == set(payloads)|set(shell)|{'AndroidManifest.xml'},'Small APK inventory differs')
        for name,expected in shell.items(): require(pin(archive.read(name)) == expected,'Candidate DEX/resources differ')
    require(retained.verify_apk_server_archives(apk) == preflight,'Candidate native server extraction differs')
    return runtime


def validate_qualification(q, commit, donor):
    require(type(q.get('format')) is int and q['format'] == 1 and q.get('status') == 'passed'
        and q.get('scope') == QUALIFICATION_SCOPE and q.get('repository_commit') == q.get('runtime_repository_commit') == commit
        and typed_equal(q.get('donor'), donor_link()) and typed_equal(q.get('checks'),dict.fromkeys(CHECKS,True))
        and q.get('native_build_provenance') == donor['native_build_provenance']
        and q.get('publication_provenance') == publication_provenance(commit)
        and typed_equal(q.get('runtime_profile'),RECOVERY_PROFILE)
        and typed_equal(q.get('client_assets'),recovery_contract())
        and typed_equal(q.get('actual_native_ancestry_validation'),previous.previous.previous.ACTUAL_NATIVE_ANCESTRY_CHECKS)
        and typed_equal(q.get('native_client_render_queue'),donor['native_client_render_queue'])
        and q.get('server_payload_extraction_preflight',{}).get('status') == 'passed'
        and q.get('client_gpu_runtime') == donor['client_gpu_runtime']
        and q.get('baseline_payloads_verified') == BASELINE_PAYLOAD_COUNT
        and q.get('changed_java_sources') == sorted(JAVA_CHANGES) and q.get('added_java_sources') == sorted(JAVA_ADDITIONS)
        and q.get('retained_java_sources_verified') == DONOR_JAVA_COUNT-len(JAVA_CHANGES)
        and q.get('authored_java_sources_verified') == DONOR_JAVA_COUNT+len(JAVA_ADDITIONS)
        and all(q.get(name) is False for name in FALSE_FLAGS)
        and all(q.get(name) is True for name in TRUE_FLAGS), 'Exact truthful recovery qualification required')
    contract = module('recovery_qualification_contract', ROOT/QUALIFICATION_SCRIPT); contract.validate_suite_inventory()
    suites = q.get('test_suites', {})
    require(set(suites) == set(contract.TEST_MODULES) and q.get('check_suites') == contract.CHECK_SUITES
        and all(value.get('status') == 'passed' and type(value.get('skipped')) is int and value['skipped'] == 0
            and type(value.get('tests_run')) is int and value['tests_run'] > 0 for value in suites.values())
        and type(q.get('tests_run')) is int and q['tests_run'] == sum(value['tests_run'] for value in suites.values()),
        'Complete retained and focused suites must pass without skips')
    require(set(q.get('source_files', {})) == set(contract.source_paths(donor)), 'Exact current qualified source closure required')
    for name,expected in q['source_files'].items():
        require(type(name) is str and not Path(name).is_absolute() and '..' not in Path(name).parts and chr(92) not in name, 'Unsafe qualified source')
        builder().checked_file(ROOT/name, expected)
    require(q.get('postgresql_emission_fixtures') == ['cancelled_child_deletion_commits','delete_insert_replacement_commits','duplicate_insert_23505_rollback']
        and q.get('postgresql_levelup_fixtures') == sorted(retained.levelup_postgresql_fixtures()), 'All seven retained real PostgreSQL fixtures required')
    return q


def repair_android_manifest(source, destination):
    base = builder(); base.verify_source_manifest(source); tree = ET.parse(source)
    tree.getroot().set(base.ANDROID+'versionName', VERSION_NAME); tree.getroot().set(base.ANDROID+'versionCode',str(VERSION_CODE))
    ET.register_namespace('android',base.ANDROID[1:-1]); tree.write(destination,encoding='utf-8',xml_declaration=True)
    builder(repaired=True).verify_source_manifest(destination)


def compile_java(base, android_jar, classes, sources):
    """Keep actual SDK diagnostics when the historical captured runner fails."""
    try:
        return base.run('java','-m','jdk.compiler/com.sun.tools.javac.Main','--release','8',
            '-cp',android_jar,'-d',classes,*sources)
    except subprocess.CalledProcessError as failure:
        # The retained runner merges stderr into stdout. Do not silently lose
        # the only compiler explanation when its checked subprocess fails.
        diagnostic = failure.output or failure.stderr or ''
        raw = diagnostic if isinstance(diagnostic,bytes) else diagnostic.encode('utf-8',errors='replace')
        print('Android SDK Java compilation failed; captured compiler diagnostics:',flush=True)
        print(raw[:65536].decode('utf-8',errors='replace'),flush=True)
        if len(raw)>65536: print('[compiler diagnostics truncated after 65536 bytes]',flush=True)
        raise


def build(args):
    base, current = builder(), builder(repaired=True); commit = base.source_commit(args.repository_commit)
    donor = validate_donor(args.donor_apk,args.donor_build_report,args.retained_client_directory)
    q = validate_qualification(read_json(args.qualification),commit,donor)
    require(q.get('external_asset_pack') == asset_contract(args.asset_directory,verify_volumes=True),'Qualified asset manifest differs')
    password = base.signing_password_spec(args.password_env)
    base.verify_signing_identity(args.keystore,'coh-client-interactive',SIGNER,password)
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(),'Fresh recovery APK required')
    base.checked_file(args.testing_notes); require(0 < args.testing_notes.stat().st_size <= 65536,'Bounded testing notes required')
    for tool in (args.android_jar,args.build_tools/'aapt2',args.build_tools/'zipalign',args.build_tools/'lib/d8.jar',args.build_tools/'lib/apksigner.jar'):
        require(tool.is_file() and not tool.is_symlink(),'Required Android SDK tool missing')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-recovery-',dir=args.output.parent) as temporary:
        work = Path(temporary); runtime,payloads,preflight = extract_and_repair(args.donor_apk,donor,work/'donor',commit,args.asset_directory,args.monorail_directory,args.native_commit)
        classes,generated,dex = (work/name for name in ('classes','generated','dex'))
        for folder in (classes,generated,dex): folder.mkdir()
        manifest = work/'AndroidManifest.xml'; repair_android_manifest(ROOT/'android/interactive/src/main/AndroidManifest.xml',manifest)
        resources,unsigned,aligned,signed = (work/name for name in ('resources.zip','unsigned.apk','aligned.apk','signed.apk'))
        base.run(args.build_tools/'aapt2','compile','--dir',ROOT/'android/interactive/src/main/res','-o',resources)
        base.run(args.build_tools/'aapt2','link','-I',args.android_jar,'--manifest',manifest,'--min-sdk-version','26','--target-sdk-version','35','--java',generated,resources,'-o',unsigned)
        with zipfile.ZipFile(unsigned) as archive:
            require(retained.archive_inventory(archive) == {'AndroidManifest.xml',*donor['retained_android_resources']},'Unexpected generated Android inventory')
            for name,expected in donor['retained_android_resources'].items(): require(pin(archive.read(name)) == expected,'Android resources changed beyond version')
        require({path.relative_to(generated).as_posix() for path in generated.rglob('*.java')} == {base.APP_ID.replace('.','/')+'/R.java'},'Unexpected generated Java source')
        sources,java,changed = current_java_sources(donor,generated)
        require(q.get('java_sources') == java,'Java changed after qualification')
        compile_java(base,args.android_jar,classes,sources)
        class_jar = work/'classes.jar'
        with zipfile.ZipFile(class_jar,'w',zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(classes.rglob('*.class')): archive.write(path,path.relative_to(classes).as_posix())
        base.run('java','-cp',args.build_tools/'lib/d8.jar','com.android.tools.r8.D8','--min-api','26','--lib',args.android_jar,'--output',dex,class_jar)
        require({path.name for path in dex.iterdir()} == {'classes.dex'},'Unexpected DEX output')
        dex_pin = base.file_pin(dex/'classes.dex')
        with zipfile.ZipFile(unsigned,'a',zipfile.ZIP_DEFLATED) as archive:
            base.append_payloads(archive,[(work/'donor'/name,name) for name in sorted(payloads)])
            archive.write(dex/'classes.dex','classes.dex')
        base.run(args.build_tools/'zipalign','-f','4',unsigned,aligned)
        base.run('java','-jar',args.build_tools/'lib/apksigner.jar','sign','--ks',args.keystore,'--ks-key-alias','coh-client-interactive','--ks-pass',password,'--key-pass',password,'--out',signed,aligned)
        certificate = retained.verify_signature(signed,args.build_tools); base.run(args.build_tools/'zipalign','-c','4',signed)
        current.verify_badging(base.run(args.build_tools/'aapt2','dump','badging',signed))
        verify_derivative(signed,donor,payloads,dex_pin,commit,args.asset_directory,args.monorail_directory,args.native_commit); retained.verify_binary_manifest(signed,args.donor_apk,args.build_tools)
        shutil.copyfile(signed,args.output)
        report = {'format':1,'apk':APK_NAME,**base.file_pin(args.output),'repository_commit':commit,'runtime_repository_commit':commit,
            'retained_runtime_repository_commit':DONOR_COMMIT,'retained_native_repository_commit':NATIVE_COMMIT,
            'application_id':base.APP_ID,'version_name':VERSION_NAME,'version_code':VERSION_CODE,'abi':'arm64-v8a',
            'scope':QUALIFICATION_SCOPE,'donor':donor_link(),'signer_certificate_sha256':certificate,'signing_key_created':False,
            'signature_verified':True,'package_badging_verified':True,'binary_manifest_version_only_verified':True,'payload_bytes_verified':True,
            'external_asset_pack':asset_contract(args.asset_directory),'server_payload_extraction_preflight':preflight,
            'payloads':payloads,'changed_apk_payloads':sorted(REPLACED_PAYLOADS),'added_apk_payloads':sorted(ADDED_PAYLOADS),
            'baseline_payloads_verified':BASELINE_PAYLOAD_COUNT,'retained_baseline_payloads_verified':BASELINE_PAYLOAD_COUNT-len(REPLACED_PAYLOADS)-len(EXTERNAL_PAYLOADS),
            'recompiled_dex':dex_pin,'donor_dex':donor['recompiled_dex'],'java_sources':java,'changed_java_sources':changed,
            'added_java_sources':sorted(JAVA_ADDITIONS),'retained_java_sources_verified':DONOR_JAVA_COUNT-len(JAVA_CHANGES),
            'authored_java_sources_verified':DONOR_JAVA_COUNT+len(JAVA_ADDITIONS),'generated_manifest':base.file_pin(manifest),
            'qualification':q,'qualification_receipt':base.file_pin(args.qualification),'testing_notes':base.file_pin(args.testing_notes),
            'publication_provenance':publication_provenance(commit),'client_assets':recovery_contract(),
            'runtime_profile':dict(RECOVERY_PROFILE),
            'runtime_manifest':runtime,'runtime_manifest_sha256':payloads['assets/runtime/runtime-manifest.json']['sha256'],
            **dict.fromkeys(FALSE_FLAGS,False),**dict.fromkeys(TRUE_FLAGS,True),**{name:donor[name] for name in RETAINED_FIELDS}}
        (args.output.parent/REPORT_NAME).write_bytes(shared.encoded(report))
    shutil.copyfile(args.testing_notes,args.output.parent/NOTES_NAME)
    args.output.with_suffix('.apk.sha256').write_text(report['sha256']+'  '+APK_NAME+'\n')
    verify_report(argparse.Namespace(**vars(args),apk=args.output,build_report=args.output.parent/REPORT_NAME),commit)
    print('Qualified recovery APK:',args.output,report['sha256']); return report


def verify_report(args,commit):
    base,current = builder(),builder(repaired=True)
    donor = validate_donor(args.donor_apk,args.donor_build_report,args.retained_client_directory)
    q = validate_qualification(read_json(args.qualification),commit,donor); report = read_json(args.build_report)
    _,java,changed = current_java_sources(donor,ROOT/'out/no-generated-java')
    assets=asset_contract(args.asset_directory,verify_volumes=True)
    require(report.get('external_asset_pack') == q.get('external_asset_pack') == assets,'Asset compatibility differs after qualification')
    require(type(report.get('format')) is int and report['format'] == 1 and report.get('apk') == APK_NAME
        and report.get('repository_commit') == report.get('runtime_repository_commit') == commit
        and report.get('retained_runtime_repository_commit') == DONOR_COMMIT and report.get('retained_native_repository_commit') == NATIVE_COMMIT
        and report.get('donor') == donor_link() and report.get('scope') == QUALIFICATION_SCOPE
        and report.get('application_id') == base.APP_ID and report.get('version_name') == VERSION_NAME
        and type(report.get('version_code')) is int and report['version_code'] == VERSION_CODE and report.get('abi') == 'arm64-v8a'
        and report.get('signer_certificate_sha256') == SIGNER and report.get('signing_key_created') is False
        and typed_equal(report.get('qualification'),q) and report.get('qualification_receipt') == base.file_pin(args.qualification)
        and report.get('publication_provenance') == publication_provenance(commit) and typed_equal(report.get('client_assets'),recovery_contract())
        and typed_equal(report.get('runtime_profile'),RECOVERY_PROFILE)
        and report.get('java_sources') == q.get('java_sources') == java and report.get('changed_java_sources') == changed
        and report.get('added_java_sources') == sorted(JAVA_ADDITIONS) and report.get('retained_java_sources_verified') == DONOR_JAVA_COUNT-len(JAVA_CHANGES)
        and report.get('authored_java_sources_verified') == DONOR_JAVA_COUNT+len(JAVA_ADDITIONS) and report.get('donor_dex') == donor['recompiled_dex']
        and report.get('changed_apk_payloads') == sorted(REPLACED_PAYLOADS) and report.get('added_apk_payloads') == sorted(ADDED_PAYLOADS)
        and report.get('baseline_payloads_verified') == BASELINE_PAYLOAD_COUNT and report.get('retained_baseline_payloads_verified') == BASELINE_PAYLOAD_COUNT-len(REPLACED_PAYLOADS)-len(EXTERNAL_PAYLOADS)
        and all(typed_equal(report.get(name),donor[name]) for name in RETAINED_FIELDS)
        and all(report.get(name) is False for name in FALSE_FLAGS)
        and all(report.get(name) is True for name in TRUE_FLAGS+('signature_verified','package_badging_verified','binary_manifest_version_only_verified','payload_bytes_verified')),
        'Exact recovery publication receipt differs')
    base.checked_file(args.apk,report); runtime = verify_derivative(args.apk,donor,report['payloads'],report['recompiled_dex'],commit,args.asset_directory,args.monorail_directory,args.native_commit)
    require(typed_equal(report.get('runtime_manifest'),runtime)
        and report.get('runtime_manifest_sha256') == report['payloads']['assets/runtime/runtime-manifest.json']['sha256'],'Runtime provenance differs')
    retained.verify_binary_manifest(args.apk,args.donor_apk,args.build_tools); retained.verify_signature(args.apk,args.build_tools)
    base.run(args.build_tools/'zipalign','-c','4',args.apk); current.verify_badging(base.run(args.build_tools/'aapt2','dump','badging',args.apk))
    checksum = args.apk.with_suffix('.apk.sha256'); require(checksum.read_text() == report['sha256']+'  '+APK_NAME+'\n','Checksum differs')
    notes = args.apk.parent/NOTES_NAME; base.checked_file(notes,report['testing_notes']); base.checked_file(args.testing_notes,report['testing_notes'])
    return report,checksum,notes


bounded_download, authenticated_artifact_download = previous.bounded_download, previous.authenticated_artifact_download


def download_donor_evidence(args):
    require(not args.output.exists() and not args.output.is_symlink(),'Fresh donor evidence directory required'); args.output.mkdir(parents=True)
    target = args.output/DONOR_EVIDENCE_ARCHIVE
    authenticated_artifact_download(DONOR_EVIDENCE_ID,target,DONOR_EVIDENCE)
    members = donor_evidence_members(target)
    with zipfile.ZipFile(target) as archive:
        for name in sorted(members):
            target = args.output/name; target.write_bytes(archive.read(name)); builder().checked_file(target,members[name])
    validate_donor_receipt(args.output/DONOR_REPORT_NAME)
    print('Authenticated exact published .26 packaging evidence')


def download_retained_native(args):
    require(not args.output.exists() and not args.output.is_symlink(),'Fresh native evidence directory required')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-recovery-native-',dir=args.output.parent) as temporary:
        archive_path = Path(temporary)/'original-native.zip'
        authenticated_artifact_download(NATIVE_ARTIFACT_ID,archive_path,NATIVE_ARTIFACT)
        with zipfile.ZipFile(archive_path) as archive:
            require(retained.archive_inventory(archive) == {'CityOfHeroes.exe','CMakeCache.txt',native_producer().MANIFEST,native_producer().CHECKS},'Exact original native artifact inventory required')
            args.output.mkdir()
            for entry in archive.infolist():
                require(not entry.is_dir() and 0 < entry.file_size <= 32*1024**2,'Unbounded retained native member')
                (args.output/entry.filename).write_bytes(archive.read(entry))
    builder().checked_file(args.output/native_producer().MANIFEST,NATIVE_MANIFEST)
    builder().checked_file(args.output/'CityOfHeroes.exe',DONOR_GAME)
    native = native_producer().validate_package(args.output,NATIVE_COMMIT)
    require(native['run_url'] == 'https://github.com/'+REPOSITORY+'/actions/runs/'+str(NATIVE_RUN_ID),'Original native owner differs')
    print('Reused original Game and native proof; no native compilation')


# Private publication-only delegate, so every old release keeps its own guard.
_publication = module('client_recovery_private_publication',Path(previous.previous.previous.__file__))
for _name in ('APK_NAME','REPORT_NAME','NOTES_NAME','RELEASE_TAG','DONOR_COMMIT','DONOR_APK_NAME','DONOR_APK','NOTES'):
    setattr(_publication,_name,globals()[_name])
validate_existing_release,download_public = _publication.validate_existing_release,_publication.download_public


def prepare_assets(args):
    donor = validate_donor_receipt(args.donor_build_report); builder().checked_file(args.donor_apk,DONOR_APK)
    expected = read_json(ROOT/'assets/reference-inputs-receipt.json')
    builder().checked_file(args.reference_archive,{'bytes':expected['archive_bytes'],'sha256':expected['archive_sha256']})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-asset-staging-',dir=args.output.parent) as temporary:
        inputs = packs.stage_donor_assets(args.donor_apk,donor['payloads'],Path(temporary)/'base')
        inputs[packs.REFERENCE_FILE] = args.reference_archive
        zones = {}
        for directory,names in ((args.zones_directory,('zones-world-supplement.zip','zones-world-supplement-manifest.json')),
            (args.beacons_directory,('kings-row-beacons.zip','kings-row-beacon-manifest.json'))):
            for name in names:
                source = directory/name; builder().checked_file(source)
                zones['runtime/'+name] = source
        import prepare_zones_world_assets as world
        world.verify_archive(args.zones_directory/'zones-world-supplement.zip',read_json(args.zones_directory/'zones-world-supplement-manifest.json'))
        import kings_row_beacon_package as beacon
        document,lock = beacon.read_manifest(args.beacons_directory/beacon.MANIFEST,args.beacons_directory/beacon.LOCK)
        require(builder().file_pin(args.beacons_directory/beacon.ARCHIVE) == lock['archive'],'Native beacon ZIP differs from qualified lock')
        inputs.update(zones)
        manifest,report = packs.build(inputs,args.output,zones=zones)
    shutil.copyfile(args.beacons_directory/beacon.LOCK,args.output/beacon.LOCK)
    print('Built independently versioned asset pack',manifest['version'],report['volumes'])
    return report


def asset_release_members(directory):
    directory = Path(directory); manifest = asset_contract(directory)
    names = []
    for volume in sorted(manifest['volumes']):
        name = packs.volume_filename(packs.VERSION,volume); names.extend((name,name+'.sha256'))
    names += [packs.MANIFEST,'asset-pack-build-report.json']
    return [directory/name for name in names]


def download_public_assets(args):
    report=read_json(args.build_report); manifest=packs.validate_manifest(read_json(args.manifest))
    require(report.get('format') == 1 and report.get('asset_pack_version') == packs.VERSION
        and report.get('asset_manifest') == builder().file_pin(args.manifest)
        and report.get('all_payloads_streamed_and_verified') is True,'Exact asset publication report required')
    require(not args.output.exists() and not args.output.is_symlink(),'Fresh public asset download directory required')
    args.output.mkdir(parents=True)
    prefix='https://github.com/'+REPOSITORY+'/releases/download/'+ASSET_RELEASE_TAG+'/'
    for name,expected in ((packs.MANIFEST,builder().file_pin(args.manifest)),
            ('asset-pack-build-report.json',builder().file_pin(args.build_report))):
        bounded_download(prefix+name,args.output/name,expected)
    expected_names={packs.volume_filename(packs.VERSION,volume) for volume in manifest['volumes']}
    require(set(report.get('volumes',{})) == expected_names,'Exact published volume inventory required')
    for name,expected in report['volumes'].items():
        path=args.output/name; bounded_download(prefix+name,path,expected)
        checksum=(expected['sha256']+'  '+name+'\n').encode()
        bounded_download(prefix+name+'.sha256',args.output/(name+'.sha256'),pin(checksum))
        packs.verify_volume(path,manifest)
    shutil.copyfile(args.lock,args.output/'kings-row-beacon-lock.json')
    print('All actual public asset volumes and per-member hashes verified')


def publish_asset_release(api,directory,commit):
    manifest = asset_contract(directory,verify_volumes=True); members = asset_release_members(directory)
    pins = {path.name:builder().file_pin(path) for path in members}
    try: existing = api.request('/releases/tags/'+ASSET_RELEASE_TAG)
    except urllib.error.HTTPError as error:
        if error.code != 404: raise
    else:
        require(existing.get('draft') is False and existing.get('tag_name') == ASSET_RELEASE_TAG,
            'Existing asset release incomplete; never overwrite it')
        published = {entry['name']:entry for entry in existing.get('assets',[])}
        require(set(published) == set(pins) and all(published[name].get('size') == record['bytes']
            and published[name].get('digest') == 'sha256:'+record['sha256'] for name,record in pins.items()),
            'Asset version already exists with different bytes; create a new asset version')
        return existing['html_url']
    body = ('Independent COH Assets '+packs.VERSION+'. Import all three versioned volumes once: Base, Reference and Zones. '
        'Later APK releases will explicitly state whether this exact pack can be reused. '
        'This pack retains the accepted Atlas assets and adds audited frozen-source zone resources and qualified Kings Row graph. '
        'Asset inclusion does not physically qualify every other zone.\n\n' +
        '\n'.join(name+': `'+record['sha256']+'`' for name,record in pins.items() if name.endswith('.zip')))
    release = api.request('/releases',{'tag_name':ASSET_RELEASE_TAG,'target_commitish':commit,
        'name':'COH Assets '+packs.VERSION,'body':body,'draft':True,'prerelease':True,'generate_release_notes':False,'make_latest':'false'},method='POST')
    require(type(release.get('id')) is int and release.get('draft') is True,'Unexpected asset draft')
    for path in members:
        uploaded = api.request('/releases/'+str(release['id'])+'/assets?'+urllib.parse.urlencode({'name':path.name}),path,method='POST',upload=True)
        require(uploaded.get('state') == 'uploaded' and uploaded.get('name') == path.name and uploaded.get('size') == pins[path.name]['bytes']
            and uploaded.get('digest') == 'sha256:'+pins[path.name]['sha256'],'Asset upload differs')
    result = api.request('/releases/'+str(release['id']),{'draft':False,'prerelease':True,'make_latest':'false'},method='PATCH')
    require(result.get('draft') is False and result.get('tag_name') == ASSET_RELEASE_TAG,'Asset publication incomplete')
    return result['html_url']


def publish_release(api,report,assets,notes):
    require(tuple(path.name for path in assets) == (APK_NAME,APK_NAME+'.sha256',NOTES_NAME),'Unexpected release assets')
    builder().checked_file(assets[0],report)
    for path in ('/releases/tags/'+RELEASE_TAG,'/git/ref/tags/'+RELEASE_TAG):
        try: existing = api.request(path)
        except urllib.error.HTTPError as error:
            if error.code != 404: raise
        else:
            require(not path.startswith('/releases/'),'Existing release is never replaced')
            require(existing.get('object',{}).get('type') == 'commit' and existing['object'].get('sha') == report['repository_commit'],'Existing tag points elsewhere')
    previous.previous.previous.previous.require_current_release_head(api,report['repository_commit'])
    release = api.request('/releases',{'tag_name':RELEASE_TAG,'target_commitish':report['repository_commit'],
        'name':'COH Atlas Gameplay 0.13.28 — external assets and Kings Row monorail',
        'body':notes+'\n\nAPK SHA-256: `'+report['sha256']+'`.\n[Hosted qualification](https://github.com/'+REPOSITORY+'/actions/runs/'+os.environ.get('GITHUB_RUN_ID','')+').\n',
        'draft':True,'prerelease':True,'generate_release_notes':False,'make_latest':'false'},method='POST')
    require(type(release.get('id')) is int and release.get('draft') is True and release.get('tag_name') == RELEASE_TAG,'Unexpected draft release')
    for path in assets:
        uploaded = api.request('/releases/'+str(release['id'])+'/assets?'+urllib.parse.urlencode({'name':path.name}),path,method='POST',upload=True)
        expected = builder().file_pin(path)
        require(uploaded.get('state') == 'uploaded' and uploaded.get('name') == path.name and uploaded.get('size') == expected['bytes']
            and uploaded.get('digest') == 'sha256:'+expected['sha256'],'Release upload differs')
    previous.previous.previous.previous.require_current_release_head(api,report['repository_commit'])
    result = api.request('/releases/'+str(release['id']),{'draft':False,'prerelease':True,'make_latest':'false'},method='PATCH')
    require(result.get('id') == release['id'] and result.get('draft') is False and result.get('prerelease') is True and result.get('tag_name') == RELEASE_TAG,'Publication incomplete')
    return result.get('html_url')


def publish(args):
    require(os.environ.get('GITHUB_REPOSITORY') == REPOSITORY and os.environ.get('GITHUB_REF') == 'refs/heads/'+BRANCH
        and os.environ.get('GITHUB_EVENT_NAME') in ('push','workflow_dispatch'),'Publication requires continuation branch')
    commit = builder().source_commit(os.environ.get('GITHUB_SHA')); report,checksum,notes = verify_report(args,commit)
    api = module('recovery_github',Path(__file__).with_name('build_atlas_gameplay_apk.py'))
    client = api.GitHub(os.environ.get('GH_TOKEN'))
    print('Published asset pack:',publish_asset_release(client,args.asset_directory,commit))
    print('Published APK:',publish_release(client,report,(args.apk,checksum,notes),notes.read_text()))


def main():
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest='command',required=True)
    for name in ('download-donor','download-donor-evidence','download-retained-native'):
        command = commands.add_parser(name); command.add_argument('--output',type=Path,required=True)
    command = commands.add_parser('download-public-assets')
    for name in ('build-report','manifest','lock','output'):command.add_argument('--'+name,type=Path,required=True)
    command = commands.add_parser('prepare-assets')
    for name in ('donor-apk','donor-build-report','reference-archive','zones-directory','beacons-directory','output'):
        command.add_argument('--'+name,type=Path,required=True)
    command = commands.add_parser('download-public'); command.add_argument('--output',type=Path,required=True); command.add_argument('--build-report',type=Path,required=True)
    for name in ('build','audit','publish'):
        command = commands.add_parser(name)
        for value in ('donor-apk','donor-build-report','retained-client-directory','qualification','build-tools','asset-directory','monorail-directory'): command.add_argument('--'+value,type=Path,required=True)
        command.add_argument('--native-commit',required=True)
        command.add_argument('--testing-notes',type=Path,default=NOTES); command.add_argument('--repository-commit',default=os.environ.get('GITHUB_SHA'))
        if name == 'build':
            command.add_argument('--android-jar',type=Path,required=True); command.add_argument('--keystore',type=Path,required=True)
            command.add_argument('--password-env',default='COH_INTERACTIVE_KEYSTORE_PASSWORD'); command.add_argument('--output',type=Path,required=True)
        else:
            command.add_argument('--apk',type=Path,required=True); command.add_argument('--build-report',type=Path,required=True)
    args = parser.parse_args()
    if args.command == 'download-donor': bounded_download(DONOR_URL,args.output,DONOR_APK)
    elif args.command == 'download-donor-evidence': download_donor_evidence(args)
    elif args.command == 'download-retained-native': download_retained_native(args)
    elif args.command == 'download-public': download_public(args)
    elif args.command == 'prepare-assets': prepare_assets(args)
    elif args.command == 'download-public-assets': download_public_assets(args)
    elif args.command == 'build': build(args)
    elif args.command == 'publish': publish(args)
    else: print('Fresh-process candidate verified:',verify_report(args,builder().source_commit(args.repository_commit))[0]['sha256'])


if __name__ == '__main__': main()
