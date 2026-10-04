#!/usr/bin/env python3
"""Build the bounded 0.13.8 client follow-up from exact public 0.13.7 bytes.

Two Android acceptance classes are recompiled; setup memory protection and
17 other authored Java sources remain byte exact. Only Game receives the
source-bound copy and BIN profiling layer. DbServer, MapServer, DLLs, server
caches, graphics closure and existing world/avatar packs are conserved.
Existing visual payload names are replaced by an append-only leaf superset;
the frozen runtime verification bound is not widened.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

import build_startup_bundle_apk as startup

ROOT = Path(__file__).resolve().parents[3]
retained, shared = startup.retained, startup.shared
REPOSITORY, BRANCH, SIGNER = startup.REPOSITORY, startup.BRANCH, startup.SIGNER
DONOR_COMMIT = '0da09e771cb472f4ec897c39b90cef675d007edf'
DONOR_RUNTIME_COMMIT = '7b48762de0748e443a2df60c6e4b59e22b365e35'
RETAINED_SETUP_MEMORY_COMMIT = '31c8a1722f992e7a8334ef2256b4feaa9ca173be'
RETAINED_NATIVE_COMMIT = startup.RETAINED_NATIVE_COMMIT
DONOR_RUN_ID = 37198877717
DONOR_APK_NAME = 'COH-Atlas-Gameplay-0.13.7.apk'
DONOR_APK = {'bytes': 700131607, 'sha256': 'ab21dc2e8a6ebecea0edf694187da83787f808a396d686e0d8312565f8373fc7'}
DONOR_BUILD = {'bytes': 3263448, 'sha256': '48fac5edde017731cbd9331300af9ffb80d2c1973eb4a946f7e29546c30d8de9'}
DONOR_URL = 'https://github.com/'+REPOSITORY+'/releases/download/coh-atlas-gameplay-v0.13.7/'+DONOR_APK_NAME
VERSION_NAME, VERSION_CODE = '0.13.8', 23
APK_NAME = 'COH-Atlas-Gameplay-0.13.8.apk'
REPORT_NAME = 'client-loading-apk-build-report.json'
NOTES_NAME = 'COH-Atlas-Gameplay-0.13.8-testing.txt'
NOTES = ROOT/'docs'/NOTES_NAME
RELEASE_TAG = 'coh-atlas-gameplay-v0.13.8'
HELPERS = frozenset({'client_visual_assets.py', 'native_responsiveness_contract.py', 'client_startup_diagnostic.py',
    'texture_header_index.py', 'character_creation_diagnostic.py'})
ADDED_HELPERS = frozenset()
VISUAL_ASSETS = frozenset({'client-visual-assets.zip', 'client-visual-manifest.json'})
NATIVE_ASSETS = frozenset({'client-runtime.zip'})
REPLACED_PAYLOADS = frozenset('assets/runtime/'+name for name in HELPERS|VISUAL_ASSETS|NATIVE_ASSETS|{'client-manifest.json', 'runtime-manifest.json'})
ADDED_PAYLOADS = frozenset()
JAVA_PREFIX = 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/'
JAVA_CHANGES = frozenset({JAVA_PREFIX+'ClientRuntime.java', JAVA_PREFIX+'ClientAcceptance.java'})
QUALIFICATION_SCOPE = 'bounded_client_binary_loading_lod_and_enemy_visual_assets_with_retained_0_13_7_server_identity'
CHECKS = ('client_animation_mount_and_failure_guards_verified',
    'missing_only_visual_assets_and_texture_index_binding_verified',
    'retained_save_task_storage_profile_and_memory_guards_verified',
    'android_visual_stage_acceptance_verified',
    'source_bound_client_binary_loading_verified',
    'exact_payload_boundaries_and_actual_archive_extraction_verified')
WORKFLOW = '.github/workflows/android-client-loading.yml'
QUALIFICATION_SCRIPT = 'tools/android/interactive/qualify_client_loading.py'
SOURCE_FILES = frozenset((WORKFLOW, QUALIFICATION_SCRIPT,
    'tools/android/interactive/build_client_loading_apk.py',
    'tools/android/interactive/test_client_loading_package.py',
    'tools/android/interactive/test_client_stage_acceptance.py',
    'tools/android/interactive/fixtures/client-stage-0.13.7.json',
    'tools/android/interactive/package_client_loading_native.py',
    'tools/android/interactive/test_client_loading_native.py',
    'tools/android/interactive/test_client_loading_contract.py',
    'patches/client-loading/0001-known-length-string-copy-and-profile.patch',
    'upstream/ouroboros/libs/UtilitiesLib/src/utils/textparser.c',
    'tools/android/interactive/prepare_client_visual_assets.py',
    'tools/android/interactive/client_visual_geometry.py',
    'tools/android/interactive/test_client_visual_assets.py',
    'tools/android/interactive/test_client_animation_package.py',
    'tools/android/interactive/test_client_visual_schedule.py',
    'tools/android/interactive/test_server_worktree_reuse.py',
    'tools/inspect_piggs.py', '.gitignore',
    'assets/client-visual-manifest.json', 'assets/catalog.json',
    'assets/reference-inputs-manifest.json', 'docs/source-manifest.json',
    'upstream/ouroboros/Common/seq/animtrack.c', 'upstream/ouroboros/Common/seq/animtrack.h',
    'upstream/ouroboros/Common/seq/seqload.c',
    'upstream/ouroboros/libs/UtilitiesLib/src/utils/file.c',
    'upstream/ouroboros/libs/UtilitiesLib/src/utils/piglib.c',
    'upstream/ouroboros/libs/UtilitiesLib/src/utils/FolderCache.c',
    'upstream/ouroboros/libs/UtilitiesLib/src/utils/FolderCacheNode.c',
    'upstream/ouroboros/libs/UtilitiesLib/src/utils/PigFileWrapper.c',
    'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/piglib_internal.h',
    'assets/character-avatar-defaults-manifest.json', 'assets/atlas-world-supplement-manifest.json',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    '.github/workflows/android-startup-bundle.yml',
    'android/interactive/src/main/AndroidManifest.xml', 'docs/'+NOTES_NAME,
    'docs/android-evidence/client-visual-0.13.7-device-result.json',
    *JAVA_CHANGES,
    *(('android/guest/'+name) for name in HELPERS|ADDED_HELPERS)))
require, module, read_json = startup.require, startup.module, startup.read_json
archive_inventory = startup.archive_inventory
verify_server_archives, verify_apk_server_archives = startup.verify_server_archives, startup.verify_apk_server_archives
RETAINED_RECEIPT_FIELDS = tuple(name for name in retained.RETAINED_RECEIPT_FIELDS
    if name not in ('runtime_manifest', 'runtime_manifest_sha256')) + ('native_client_startup',)


def builder(*, repaired=False):
    base = module('client_loading_android_builder', Path(__file__).with_name('build_apk.py'))
    if repaired: base.VERSION_NAME, base.VERSION_CODE, base.APK_NAME = VERSION_NAME, VERSION_CODE, APK_NAME
    return base


def donor_link():
    return {'run_id': DONOR_RUN_ID, 'repository_commit': DONOR_COMMIT, 'apk': DONOR_APK, 'build_report': DONOR_BUILD}


def validate_donor_receipt(path):
    builder().checked_file(path, DONOR_BUILD)
    donor = read_json(path); qualification = donor.get('qualification', {})
    require(donor.get('format') == 1 and donor.get('repository_commit') == DONOR_COMMIT
        and donor.get('runtime_repository_commit') == DONOR_COMMIT
        and donor.get('apk') == DONOR_APK_NAME and {key: donor.get(key) for key in DONOR_APK} == DONOR_APK
        and donor.get('application_id') == builder().APP_ID and donor.get('version_name') == '0.13.7'
        and donor.get('version_code') == 22 and donor.get('abi') == 'arm64-v8a'
        and donor.get('signer_certificate_sha256') == SIGNER and donor.get('signing_key_created') is False
        and all(donor.get(key) is True for key in ('signature_verified', 'package_badging_verified',
            'binary_manifest_version_only_verified', 'payload_bytes_verified', 'setup_memory_guards_preserved'))
        and len(donor.get('payloads', {})) == 71 and len(donor.get('java_sources', {})) == 19
        and donor.get('server_payload_extraction_preflight', {}).get('status') == 'passed'
        and qualification.get('scope') == 'client_animation_reuse_missing_only_visual_assets_and_retained_0_13_6_native_identity' and qualification.get('status') == 'passed'
        and qualification.get('tests_run') == 633 and qualification.get('repository_commit') == DONOR_COMMIT
        and qualification.get('postgresql_emission_fixture_verified') is True
        and donor.get('retained_setup_memory_repository_commit') == RETAINED_SETUP_MEMORY_COMMIT
        and donor.get('retained_native_repository_commit') == RETAINED_NATIVE_COMMIT
        and donor.get('runtime_manifest', {}).get('repository_commit') == DONOR_COMMIT
        and donor['runtime_manifest'].get('startup_only_reopen') is True
        and donor['runtime_manifest'].get('task_gate_required') is True
        and donor.get('native_dbserver', {}).get('repository_commit') == DONOR_RUNTIME_COMMIT
        and donor.get('native_client_startup', {}).get('repository_commit') == DONOR_RUNTIME_COMMIT,
        'Exact public 0.13.7 client visual donor receipt differs')
    return donor


def validate_retained_native_sources(donor):
    # The whole published receipt is fixed by DONOR_BUILD. Additionally prevent
    # an unreviewed native/schema/source edit from hiding behind retained bytes.
    native_names = {name for name in donor['qualification']['source_files'] if
        (name.startswith(('patches/', 'database/', 'upstream/')) or
        name in ('tools/android/interactive/package_startup_bundle_client.py',
            'tools/android/interactive/package_startup_bundle_dbserver.py',
            'android/guest/native_responsiveness_contract.py', 'android/guest/character_server_data_cache.py',
            'android/guest/local_character_server.py'))
        and name not in {'android/guest/'+helper for helper in HELPERS}}
    require(native_names, 'Retained native source closure missing')
    for name in native_names: builder().checked_file(ROOT/name, donor['qualification']['source_files'][name])
    return sorted(native_names)


def validate_donor(apk, receipt):
    base = builder(); base.checked_file(apk, DONOR_APK)
    donor = validate_donor_receipt(receipt); base.verify_packaged_payloads(apk, donor['payloads'])
    with zipfile.ZipFile(apk) as archive:
        shell = {'classes.dex': donor['retained_dex'], **donor['retained_android_resources']}
        require(archive_inventory(archive) == set(donor['payloads'])|set(shell)|{'AndroidManifest.xml'},
            'Unexpected donor APK inventory')
        for name, expected in shell.items():
            raw = archive.read(name)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == expected,
                'Donor Android shell differs: '+name)
        for name, field in (('runtime-manifest.json', 'runtime_manifest'),
                ('native-responsiveness.json', 'native_responsiveness'),
                ('server-animation-manifest.json', 'server_animation_manifest'),
                ('startup-dbserver-manifest.json', 'native_dbserver')):
            require(json.loads(archive.read('assets/runtime/'+name)) == donor[field], 'Donor retained provenance differs: '+name)
        donor['_client_verification'] = json.loads(archive.read('assets/runtime/client-manifest.json'))
        donor['_visual_manifest'] = json.loads(archive.read('assets/runtime/client-visual-manifest.json'))
        require(donor['_visual_manifest'] == donor['visual_package']['manifest']
            and donor['_visual_manifest']['file_count'] == 290,
            'Exact public donor visual inventory differs')
        with archive.open('assets/runtime/client-runtime.zip') as source, tempfile.TemporaryFile() as target:
            shutil.copyfileobj(source, target, 64*1024); target.seek(0)
            with zipfile.ZipFile(target) as client:
                manifest = json.loads(client.read('client-package.json'))
                shared.native_contract.client_contract(manifest, donor['native_responsiveness'])
                require(manifest.get('startup_bundle_client', {}).get('manifest') == donor['native_client_startup'],
                    'Retained native Game receipt differs')
                donor['_client_members'] = startup.client_member_pins(client)
                donor['_client_manifest'] = manifest
    require(verify_apk_server_archives(apk) == donor['server_payload_extraction_preflight'],
        'Exact public donor does not pass actual guest extraction')
    validate_retained_native_sources(donor)
    return donor


def current_java_sources(donor, generated):
    base = builder(); sources = retained.java_sources(base, generated)
    pins = {path.relative_to(ROOT).as_posix(): base.file_pin(path) for path in sources
        if path.is_relative_to(ROOT) and not path.is_relative_to(generated)}
    require(len(pins) == 19 and set(pins) == set(donor['java_sources']),
        'Client follow-up must retain the exact 19 authored Java source inventory')
    require({name for name in pins if pins[name] != donor['java_sources'][name]} == JAVA_CHANGES,
        'Only ClientRuntime and ClientAcceptance Java sources may change')
    for name, expected in donor['preserved_sources'].items(): base.checked_file(ROOT/name, expected)
    base.checked_file(ROOT/'android/interactive/src/main/AndroidManifest.xml', donor['source_manifest'])
    for name, expected in donor['payloads'].items():
        if name.startswith('assets/runtime/') and (name.endswith('.py') or name.endswith('/task-gate.json')):
            if Path(name).name not in HELPERS: base.checked_file(ROOT/'android/guest'/Path(name).name, expected)
    require({name for name in HELPERS if base.file_pin(ROOT/'android/guest'/name) !=
        donor['payloads']['assets/runtime/'+name]} == HELPERS, 'Exact selected client helpers must change')
    validate_retained_native_sources(donor)
    return sources, pins, sorted(JAVA_CHANGES)


def current_sources(donor):
    return current_java_sources(donor, ROOT/'out/no-generated-java')[1]


def visual_builder():
    return module('client_loading_asset_producer', Path(__file__).with_name('prepare_client_visual_assets.py'))


def visual_guest():
    return module('client_loading_guest_contract', ROOT/'android/guest/client_visual_assets.py')


def validate_visual_package(directory):
    require(directory is not None and directory.is_dir() and not directory.is_symlink(), 'Verified visual asset package required')
    for name in VISUAL_ASSETS: builder().checked_file(directory/name)
    producer = visual_builder()
    producer.verify(directory/'client-visual-assets.zip', directory/'client-visual-manifest.json', root=ROOT)
    manifest = read_json(directory/'client-visual-manifest.json')
    require(manifest == read_json(ROOT/'assets/client-visual-manifest.json'), 'Visual supplement source manifest differs')
    require(visual_guest().package(directory) == manifest, 'Guest visual constants or manifest contract differs')
    return {'format': 1, 'manifest': manifest, 'files': {name: builder().file_pin(directory/name) for name in sorted(VISUAL_ASSETS)}}


def validate_visual_superset(donor, visual):
    previous = donor['_visual_manifest']['files']; current = visual['manifest']['files']
    require(set(previous) <= set(current) and all(current[name] == pin for name, pin in previous.items()),
        'Client visual update must preserve every prior 0.13.7 leaf byte pin')
    require(len(current) > len(previous), 'Client visual follow-up must add qualified missing leaves')
    return {'previous_files_retained': len(previous), 'new_files': len(current)-len(previous),
        'previous_files_sha256': donor['_visual_manifest']['files_sha256']}


def verify_retained_world_geometry(apk, visual):
    with tempfile.TemporaryDirectory(prefix='coh-retained-world-proof-') as temporary, zipfile.ZipFile(apk) as archive:
        target = Path(temporary)/'atlas-world-supplement.zip'
        with archive.open('assets/runtime/atlas-world-supplement.zip') as source, target.open('xb') as output:
            shutil.copyfileobj(source, output, 64*1024)
        visual_builder().verify_preserved_world_geometry(target, visual['manifest'])
    return True


def verification_manifests(donor, client, updates, commit):
    # Build and publication run in separate interpreters. New verification
    # members must have deterministic insertion order before the retained
    # non-sorted JSON encoder calculates client/runtime payload hashes.
    updates = {name: updates[name] for name in sorted(updates)}
    expected_client = copy.deepcopy(client); expected_client['files'].update(updates)
    expected_runtime = copy.deepcopy(donor['runtime_manifest']); expected_runtime['files'].update(updates)
    require(set(expected_client['files']) == set(client['files']) and len(expected_client['files']) <= 64,
        'Client follow-up cannot add verification payload names')
    require(set(expected_runtime['files']) == set(donor['runtime_manifest']['files'])
        and len(expected_runtime['files']) == 64, 'Runtime manifest must retain the frozen 64-member inventory')
    encoded = shared.encoded(expected_client)
    expected_runtime['files']['client-manifest.json'] = {'bytes': len(encoded), 'sha256': hashlib.sha256(encoded).hexdigest()}
    expected_runtime['repository_commit'] = commit
    expected_runtime['client_loading'] = {'format': 1, 'repository_commit': commit,
        'donor_repository_commit': DONOR_COMMIT, 'retained_setup_memory_repository_commit': RETAINED_SETUP_MEMORY_COMMIT,
        'retained_native_repository_commit': RETAINED_NATIVE_COMMIT,
        'native_dbserver_recompiled': False, 'native_client_recompiled': True, 'native_mapserver_recompiled': False,
        'physical_client_timing_validated': False, 'physical_visual_assets_validated': False,
        'existing_server_cache_and_save_fix_preserved': True}
    expected_runtime['scope'] = 'Client visual leaf superset, source-bound Game copy/BIN profiling layer and Android stage acceptance correction with exact retained 0.13.7 server/DLL bytes; physical timing and visual review pending'
    return expected_client, expected_runtime


def client_builder():
    return module('client_loading_native_producer', Path(__file__).with_name('package_client_loading_native.py'))


def validate_native(directory, commit, donor):
    require(directory is not None, 'Source-bound client loading native package required')
    native = client_builder().validate_package(directory, commit)
    require(native.get('base_client_executable') == donor['native_client_startup']['files']['CityOfHeroes.exe']
        and native.get('retained_source_inputs') == donor['native_responsiveness']['build_inputs']
        and native.get('schema_sources_sha256') == donor['native_responsiveness']['retained_cache']['schema_sources_sha256']
        and native.get('files', {}).get('CityOfHeroes.exe') != donor['native_client_startup']['files']['CityOfHeroes.exe'],
        'Client loading layer changed frozen source/schema lineage or immediate donor Game')
    return native


def client_manifest(donor, native):
    expected = copy.deepcopy(donor['_client_manifest'])
    expected['files']['CityOfHeroes.exe'] = native['files']['CityOfHeroes.exe']
    expected['dependency_report'] = shared.dependency_report(expected['files'])
    require(not expected['dependency_report']['unresolved'], 'New Game imports exceed retained 20 DLL closure')
    expected['client_loading'] = {'manifest': native, 'manifest_sha256': shared.native_contract.canonical_sha(native),
        'base_startup_client_manifest_sha256': shared.native_contract.canonical_sha(donor['native_client_startup']),
        'base_client_executable': donor['native_client_startup']['files']['CityOfHeroes.exe']}
    shared.native_contract.client_contract(expected, donor['native_responsiveness'])
    return expected


def replace_client_archive(path, donor, native, directory):
    require(builder().file_pin(path) == donor['payloads']['assets/runtime/client-runtime.zip'], 'Client donor archive differs')
    output = path.with_suffix('.candidate.zip'); require(not output.exists(), 'Fresh native client staging required')
    expected = client_manifest(donor, native)
    with zipfile.ZipFile(path) as previous, zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        require(startup.client_member_pins(previous) == donor['_client_members'], 'Extracted client member bytes differ')
        for entry in previous.infolist():
            if entry.filename == 'client-package.json': archive.writestr(entry.filename, shared.encoded(expected))
            elif entry.filename == 'CityOfHeroes.exe': archive.write(directory/'CityOfHeroes.exe', entry.filename)
            else:
                with previous.open(entry) as source, archive.open(entry.filename, 'w') as target: shutil.copyfileobj(source, target, 64*1024)
    output.replace(path); verify_client_archive(path, donor, native)


def verify_client_archive(path, donor, native):
    expected = client_manifest(donor, native)
    with zipfile.ZipFile(path) as archive:
        pins = startup.client_member_pins(archive)
        require(set(pins) == set(donor['_client_members']) and len(pins) == 22, 'Native client member inventory changed')
        require(json.loads(archive.read('client-package.json')) == expected, 'Client package drifted beyond third loading layer')
        raw = shared.encoded(expected)
        require(pins['client-package.json'] == {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}, 'Client package encoding differs')
        record = native['files']['CityOfHeroes.exe']
        require(pins['CityOfHeroes.exe'] == {'bytes': record['size'], 'sha256': record['sha256']}, 'Packaged new Game differs')
        require(all(pins[name] == pin for name, pin in donor['_client_members'].items()
            if name not in ('CityOfHeroes.exe', 'client-package.json')), 'Retained client DLL changed')
    return expected


def extract_and_repair(apk, donor, destination, commit, visual_directory=None, client_directory=None):
    base = builder(); current_sources(donor); visual = validate_visual_package(visual_directory)
    validate_visual_superset(donor, visual)
    native = validate_native(client_directory, commit, donor)
    destination.mkdir(parents=True)
    with zipfile.ZipFile(apk) as archive:
        require(archive_inventory(archive) == set(donor['payloads'])|set(donor['retained_android_resources'])|
            {'AndroidManifest.xml', 'classes.dex'}, 'Unexpected donor APK inventory')
        for entry in archive.infolist():
            if entry.filename == 'AndroidManifest.xml' or entry.filename.startswith('META-INF/'): continue
            target = destination/entry.filename; target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open('xb') as output: shutil.copyfileobj(source, output, 64*1024)
    require(all(base.file_pin(destination/name) == pin for name, pin in donor['payloads'].items()), 'Extracted donor payload bytes differ')
    assets = destination/'assets/runtime'
    for name in HELPERS|ADDED_HELPERS:
        source = ROOT/'android/guest'/name; base.checked_file(source)
        require(0 < source.stat().st_size <= 1024*1024, 'Unbounded client guest helper')
        shutil.copyfile(source, assets/name)
    for name in VISUAL_ASSETS: shutil.copyfile(visual_directory/name, assets/name)
    visual_builder().verify_preserved_world_geometry(assets/'atlas-world-supplement.zip', visual['manifest'])
    replace_client_archive(assets/'client-runtime.zip', donor, native, client_directory)
    updates = {name: base.file_pin(assets/name) for name in HELPERS|ADDED_HELPERS|VISUAL_ASSETS|NATIVE_ASSETS}
    client, runtime = verification_manifests(donor, donor['_client_verification'], updates, commit)
    (assets/'client-manifest.json').write_bytes(shared.encoded(client))
    (assets/'runtime-manifest.json').write_bytes(shared.encoded(runtime))
    payloads = {name: base.file_pin(destination/name) for name in set(donor['payloads'])|ADDED_PAYLOADS}
    require({name for name in donor['payloads'] if payloads[name] != donor['payloads'][name]} == REPLACED_PAYLOADS,
        'Unexpected client payload replacement')
    preflight = verify_server_archives(assets)
    require(preflight == donor['server_payload_extraction_preflight'], 'Client asset derivative changed retained server extraction')
    return runtime, payloads, visual, preflight, native


def verify_derivative(apk, donor, payloads, dex_pin, commit, visual_directory=None, client_directory=None):
    require(set(payloads) == set(donor['payloads'])|ADDED_PAYLOADS and len(payloads) == 71 and not ADDED_PAYLOADS
        and {name for name in donor['payloads'] if payloads[name] != donor['payloads'][name]} == REPLACED_PAYLOADS,
        'Candidate client payload boundaries differ')
    visual = validate_visual_package(visual_directory)
    native = validate_native(client_directory, commit, donor)
    validate_visual_superset(donor, visual)
    base = builder(); base.verify_packaged_payloads(apk, payloads)
    require(dex_pin != donor['retained_dex'], 'Android acceptance correction must recompile its DEX')
    with zipfile.ZipFile(apk) as archive:
        require(archive_inventory(archive) == set(payloads)|set(donor['retained_android_resources'])|
            {'AndroidManifest.xml', 'classes.dex'}, 'Unexpected candidate APK inventory')
        for name, expected in {'classes.dex': dex_pin, **donor['retained_android_resources']}.items():
            raw = archive.read(name)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == expected, 'Retained memory-protected Android shell differs')
        for name in HELPERS|ADDED_HELPERS:
            require(payloads['assets/runtime/'+name] == base.file_pin(ROOT/'android/guest'/name), 'Authored client helper differs: '+name)
        for name in VISUAL_ASSETS:
            require(payloads['assets/runtime/'+name] == base.file_pin(visual_directory/name), 'Verified visual asset differs: '+name)
        with tempfile.TemporaryDirectory(prefix='coh-client-loading-audit-') as temporary:
            path = Path(temporary)/'client-runtime.zip'
            with archive.open('assets/runtime/client-runtime.zip') as source, path.open('xb') as target: shutil.copyfileobj(source, target, 64*1024)
            verify_client_archive(path, donor, native)
        updates = {name: payloads['assets/runtime/'+name] for name in HELPERS|ADDED_HELPERS|VISUAL_ASSETS|NATIVE_ASSETS}
        expected_client, expected_runtime = verification_manifests(donor, donor['_client_verification'], updates, commit)
        require(json.loads(archive.read('assets/runtime/client-manifest.json')) == expected_client
            and json.loads(archive.read('assets/runtime/runtime-manifest.json')) == expected_runtime,
            'Runtime manifest drifted beyond client source and asset pins')
        for name, field in (('native-responsiveness.json', 'native_responsiveness'),
                ('server-animation-manifest.json', 'server_animation_manifest'),
                ('startup-dbserver-manifest.json', 'native_dbserver')):
            require(json.loads(archive.read('assets/runtime/'+name)) == donor[field], 'Retained native/history receipt changed: '+name)
    require(verify_apk_server_archives(apk) == donor['server_payload_extraction_preflight'], 'Candidate actual server extraction differs')
    return visual


def validate_qualification(receipt, commit):
    require(receipt.get('format') == 1 and receipt.get('status') == 'passed'
        and receipt.get('scope') == QUALIFICATION_SCOPE and receipt.get('repository_commit') == commit
        and receipt.get('retained_runtime_repository_commit') == DONOR_COMMIT
        and receipt.get('retained_setup_memory_repository_commit') == RETAINED_SETUP_MEMORY_COMMIT
        and receipt.get('retained_native_repository_commit') == RETAINED_NATIVE_COMMIT
        and receipt.get('donor_apk_sha256') == DONOR_APK['sha256']
        and all(receipt.get(key) is False for key in ('physical_gameplay_validated', 'physical_client_timing_validated',
            'physical_visual_assets_validated', 'native_runtime_booted', 'long_prior_gameplay_milestones_repeated',
            'asset_reimport_required', 'native_dbserver_recompiled', 'native_mapserver_recompiled'))
        and receipt.get('native_client_recompiled') is True
        and receipt.get('java_or_dex_recompiled') is True
        and receipt.get('changed_java_sources') == sorted(JAVA_CHANGES)
        and receipt.get('retained_java_sources') == 17
        and receipt.get('retained_world_lod_geometry_verified') is True
        and receipt.get('runtime_refresh_required') is True and receipt.get('previous_runtime_generation_retained') is True
        and receipt.get('setup_memory_guards_preserved') is True and receipt.get('retained_server_cache_and_save_fix_verified') is True
        and receipt.get('postgresql_emission_fixture_verified') is True
        and receipt.get('postgresql_emission_fixtures') == ['cancelled_child_deletion_commits', 'delete_insert_replacement_commits', 'duplicate_insert_23505_rollback']
        and type(receipt.get('tests_run')) is int and receipt['tests_run'] > 0
        and set(receipt.get('checks', {})) == set(CHECKS) and all(value is True for value in receipt['checks'].values()),
        'Exact client asset qualification required')
    require(SOURCE_FILES <= set(receipt.get('source_files', {})), 'Qualification source closure incomplete')
    contract = module('client_loading_qualification_contract', ROOT/QUALIFICATION_SCRIPT)
    suites = receipt.get('test_suites', {})
    require(set(suites) == set(contract.TEST_MODULES) and receipt.get('check_suites') == contract.CHECK_SUITES,
        'Qualification must cover exact client and retained memory suite contract')
    require(all(item.get('status') == 'passed' and item.get('skipped') == 0 and type(item.get('tests_run')) is int
        and item['tests_run'] > 0 for item in suites.values())
        and receipt['tests_run'] == sum(item['tests_run'] for item in suites.values()), 'Qualification suite evidence differs')
    for name, expected in receipt['source_files'].items():
        require(isinstance(name, str) and not Path(name).is_absolute() and '..' not in Path(name).parts and chr(92) not in name,
            'Unsafe qualification source path')
        builder().checked_file(ROOT/name, expected)
    return receipt


verify_signature = retained.verify_signature
verify_binary_manifest = retained.verify_binary_manifest


def repair_android_manifest(source, destination):
    base = builder(); base.verify_source_manifest(source)
    tree = ET.parse(source); manifest = tree.getroot()
    manifest.set(base.ANDROID+'versionName', VERSION_NAME); manifest.set(base.ANDROID+'versionCode', str(VERSION_CODE))
    ET.register_namespace('android', base.ANDROID[1:-1]); tree.write(destination, encoding='utf-8', xml_declaration=True)
    builder(repaired=True).verify_source_manifest(destination)


def download(args):
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh donor download required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(DONOR_URL, timeout=120) as source, args.output.open('xb') as target:
        total = 0
        while chunk := source.read(1024*1024):
            total += len(chunk); require(total <= DONOR_APK['bytes'], 'Oversized donor download'); target.write(chunk)
    builder().checked_file(args.output, DONOR_APK)


def build(args):
    base, current = builder(), builder(repaired=True); commit = base.source_commit(args.repository_commit)
    donor = validate_donor(args.donor_apk, args.donor_build_report)
    qualification = validate_qualification(read_json(args.qualification), commit)
    visual = validate_visual_package(args.visual_directory); conservation = validate_visual_superset(donor, visual)
    native = validate_native(args.client_directory, commit, donor)
    require(qualification.get('native_client_loading') == native, 'Native client changed after host qualification')
    require(qualification.get('visual_package') == visual, 'Visual asset package changed after host qualification')
    password = base.signing_password_spec(args.password_env)
    base.verify_signing_identity(args.keystore, 'coh-client-interactive', SIGNER, password)
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), 'Fresh client asset APK required')
    base.checked_file(args.testing_notes); require(0 < args.testing_notes.stat().st_size <= 65536, 'Bounded testing notes required')
    for tool in (args.android_jar, args.build_tools/'aapt2', args.build_tools/'zipalign', args.build_tools/'lib/apksigner.jar', args.build_tools/'lib/d8.jar'):
        require(tool.is_file() and not tool.is_symlink(), 'Required Android tool missing')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-client-loading-', dir=args.output.parent) as temporary:
        work = Path(temporary)
        classes, generated, dex = (work/name for name in ('classes', 'generated', 'dex'))
        for directory in (classes, generated, dex): directory.mkdir()
        runtime, payloads, visual, preflight, native = extract_and_repair(args.donor_apk, donor, work/'donor', commit, args.visual_directory, args.client_directory)
        manifest = work/'AndroidManifest.xml'; repair_android_manifest(ROOT/'android/interactive/src/main/AndroidManifest.xml', manifest)
        resources, unsigned, aligned, signed = (work/name for name in ('resources.zip', 'unsigned.apk', 'aligned.apk', 'signed.apk'))
        base.run(args.build_tools/'aapt2', 'compile', '--dir', ROOT/'android/interactive/src/main/res', '-o', resources)
        base.run(args.build_tools/'aapt2', 'link', '-I', args.android_jar, '--manifest', manifest, '--min-sdk-version', '26', '--target-sdk-version', '35', '--java', generated, resources, '-o', unsigned)
        with zipfile.ZipFile(unsigned) as archive:
            require(archive_inventory(archive) == {'AndroidManifest.xml', 'resources.arsc', 'res/drawable/ic_coh_client.xml'}, 'Generated Android resource inventory differs')
            for name in donor['retained_android_resources']:
                raw = archive.read(name)
                require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == donor['retained_android_resources'][name], 'Android resources changed beyond version metadata')
        require({path.relative_to(generated).as_posix() for path in generated.rglob('*.java')} ==
            {base.APP_ID.replace('.', '/')+'/R.java'}, 'Unexpected generated Java source')
        sources, source_pins, changed_java = current_java_sources(donor, generated)
        base.run('java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8', '-cp', args.android_jar, '-d', classes, *sources)
        class_jar = work/'classes.jar'
        with zipfile.ZipFile(class_jar, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(classes.rglob('*.class')): archive.write(path, path.relative_to(classes).as_posix())
        base.run('java', '-cp', args.build_tools/'lib/d8.jar', 'com.android.tools.r8.D8', '--min-api', '26', '--lib', args.android_jar, '--output', dex, class_jar)
        require({path.name for path in dex.iterdir()} == {'classes.dex'}, 'Unexpected DEX output')
        dex_pin = base.file_pin(dex/'classes.dex')
        with zipfile.ZipFile(unsigned, 'a', zipfile.ZIP_DEFLATED) as archive:
            base.append_payloads(archive, [(work/'donor'/name, name) for name in sorted(payloads)])
            archive.write(dex/'classes.dex', 'classes.dex')
        base.run(args.build_tools/'zipalign', '-f', '4', unsigned, aligned)
        base.run('java', '-jar', args.build_tools/'lib/apksigner.jar', 'sign', '--ks', args.keystore, '--ks-key-alias', 'coh-client-interactive', '--ks-pass', password, '--key-pass', password, '--out', signed, aligned)
        certificate = verify_signature(signed, args.build_tools); base.run(args.build_tools/'zipalign', '-c', '4', signed)
        current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', signed))
        verify_derivative(signed, donor, payloads, dex_pin, commit, args.visual_directory, args.client_directory)
        verify_binary_manifest(signed, args.donor_apk, args.build_tools)
        shutil.copyfile(signed, args.output)
        report = {'format': 1, 'apk': APK_NAME, **base.file_pin(args.output), 'repository_commit': commit,
            'runtime_repository_commit': commit, 'retained_runtime_repository_commit': DONOR_COMMIT,
            'retained_setup_memory_repository_commit': RETAINED_SETUP_MEMORY_COMMIT,
            'retained_native_repository_commit': RETAINED_NATIVE_COMMIT, 'application_id': base.APP_ID,
            'version_name': VERSION_NAME, 'version_code': VERSION_CODE, 'abi': 'arm64-v8a',
            'signer_certificate_sha256': certificate, 'signing_key_created': False, 'signature_verified': True,
            'package_badging_verified': True, 'binary_manifest_version_only_verified': True,
            'payload_bytes_verified': True, 'payloads': payloads, 'changed_apk_payloads': sorted(REPLACED_PAYLOADS|ADDED_PAYLOADS),
            'replaced_apk_payloads': sorted(REPLACED_PAYLOADS), 'added_apk_payloads': sorted(ADDED_PAYLOADS),
            'recompiled_dex': dex_pin, 'donor_dex': donor['retained_dex'], 'donor': donor_link(), 'java_sources': source_pins,
            'changed_java_sources': changed_java, 'added_java_sources': [], 'preserved_sources': donor['preserved_sources'],
            'generated_manifest': base.file_pin(manifest), 'qualification': qualification,
            'qualification_receipt': base.file_pin(args.qualification), 'testing_notes': base.file_pin(args.testing_notes),
            'native_libraries_changed': False, 'client_or_server_recompiled': True, 'java_or_dex_recompiled': True,
            'world_assets_changed': False, 'prepared_cache_archive_changed': False, 'dbserver_changed': False,
            'graphics_driver_changed': False, 'physical_gameplay_validated': False, 'physical_client_timing_validated': False,
            'physical_visual_assets_validated': False, 'runtime_refresh_required': True, 'installed_runtime_identity_preserved': False,
            'previous_runtime_generation_retained': True, 'asset_reimport_required': False, 'setup_memory_guards_preserved': True,
            'native_dbserver_recompiled': False, 'native_client_recompiled': True, 'native_mapserver_recompiled': False,
            'retained_server_cache_and_save_fix_verified': True, 'visual_package': visual, 'visual_superset': conservation,
            'retained_java_sources': 17,
            'native_client_loading': native,
            'runtime_manifest': runtime, 'runtime_manifest_sha256': payloads['assets/runtime/runtime-manifest.json']['sha256'],
            'scope': QUALIFICATION_SCOPE, **{name: donor[name] for name in RETAINED_RECEIPT_FIELDS}}
        (args.output.parent/REPORT_NAME).write_text(json.dumps(report, indent=2)+'\n')
        args.output.with_suffix('.apk.sha256').write_text(report['sha256']+'  '+APK_NAME+'\n')
        shutil.copyfile(args.testing_notes, args.output.parent/NOTES_NAME)
        print('Built client asset candidate', report['sha256'])


def verify_report(args, commit):
    base, current = builder(), builder(repaired=True)
    donor = validate_donor(args.donor_apk, args.donor_build_report)
    qualification = validate_qualification(read_json(args.qualification), commit); report = read_json(args.build_report)
    visual = validate_visual_package(args.visual_directory); conservation = validate_visual_superset(donor, visual)
    native = validate_native(args.client_directory, commit, donor)
    require(qualification.get('native_client_loading') == native, 'Native client changed after host qualification')
    require(qualification.get('visual_package') == visual, 'Visual asset package changed after host qualification')
    require(report.get('format') == 1 and report.get('apk') == APK_NAME and report.get('repository_commit') == commit
        and report.get('runtime_repository_commit') == commit and report.get('retained_runtime_repository_commit') == DONOR_COMMIT
        and report.get('retained_setup_memory_repository_commit') == RETAINED_SETUP_MEMORY_COMMIT
        and report.get('retained_native_repository_commit') == RETAINED_NATIVE_COMMIT
        and report.get('abi') == 'arm64-v8a' and report.get('scope') == QUALIFICATION_SCOPE
        and report.get('application_id') == base.APP_ID and report.get('version_name') == VERSION_NAME
        and report.get('version_code') == VERSION_CODE and report.get('signer_certificate_sha256') == SIGNER
        and report.get('signing_key_created') is False and report.get('donor') == donor_link()
        and report.get('qualification') == qualification and report.get('qualification_receipt') == base.file_pin(args.qualification)
        and report.get('java_sources') == current_sources(donor) and report.get('changed_java_sources') == sorted(JAVA_CHANGES)
        and report.get('added_java_sources') == [] and report.get('donor_dex') == donor['retained_dex']
        and report.get('retained_java_sources') == 17 and report.get('visual_superset') == conservation
        and report.get('preserved_sources') == donor['preserved_sources']
        and report.get('changed_apk_payloads') == sorted(REPLACED_PAYLOADS|ADDED_PAYLOADS)
        and report.get('replaced_apk_payloads') == sorted(REPLACED_PAYLOADS) and report.get('added_apk_payloads') == sorted(ADDED_PAYLOADS)
        and all(report.get(key) is True for key in ('signature_verified', 'package_badging_verified', 'binary_manifest_version_only_verified',
            'payload_bytes_verified', 'previous_runtime_generation_retained', 'runtime_refresh_required', 'setup_memory_guards_preserved',
            'retained_server_cache_and_save_fix_verified', 'java_or_dex_recompiled', 'client_or_server_recompiled', 'native_client_recompiled'))
        and all(report.get(key) is False for key in ('native_libraries_changed',
            'world_assets_changed', 'prepared_cache_archive_changed', 'dbserver_changed', 'graphics_driver_changed',
            'physical_gameplay_validated', 'physical_client_timing_validated', 'physical_visual_assets_validated',
            'native_dbserver_recompiled', 'native_mapserver_recompiled',
            'installed_runtime_identity_preserved', 'asset_reimport_required'))
        and report.get('visual_package') == visual and report.get('native_client_loading') == native
        and all(report.get(name) == donor[name] for name in RETAINED_RECEIPT_FIELDS),
        'Client asset build receipt differs')
    base.checked_file(args.apk, report); verify_derivative(args.apk, donor, report['payloads'], report['recompiled_dex'], commit, args.visual_directory, args.client_directory)
    require(report.get('runtime_manifest_sha256') == report['payloads']['assets/runtime/runtime-manifest.json']['sha256'], 'Runtime provenance differs')
    with zipfile.ZipFile(args.apk) as archive:
        require(report.get('runtime_manifest') == json.loads(archive.read('assets/runtime/runtime-manifest.json')), 'Reported runtime manifest differs')
    verify_binary_manifest(args.apk, args.donor_apk, args.build_tools)
    verify_signature(args.apk, args.build_tools); base.run(args.build_tools/'zipalign', '-c', '4', args.apk)
    current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', args.apk))
    checksum = args.apk.with_suffix('.apk.sha256')
    require(checksum.read_text() == report['sha256']+'  '+APK_NAME+'\n', 'Published checksum differs')
    public_notes = args.apk.parent/NOTES_NAME
    base.checked_file(public_notes, report['testing_notes']); base.checked_file(args.testing_notes, report['testing_notes'])
    return report, checksum, public_notes


def publish_release(api, report, assets, notes):
    require(tuple(path.name for path in assets) == (APK_NAME, APK_NAME+'.sha256', NOTES_NAME), 'Unexpected client asset release assets')
    builder().checked_file(assets[0], report)
    for path in ('/releases/tags/'+RELEASE_TAG, '/git/ref/tags/'+RELEASE_TAG):
        try: existing = api.request(path)
        except urllib.error.HTTPError as error:
            if error.code != 404: raise
        else:
            require(not path.startswith('/releases/'), 'Existing client asset release is never replaced')
            require(existing.get('object', {}).get('type') == 'commit' and existing['object'].get('sha') == report['repository_commit'], 'Existing tag points elsewhere')
    body = notes+'\n\nAPK SHA-256: `'+report['sha256']+'`.\n'
    body += '[Source-bound client asset and retained-memory host qualification](https://github.com/'+REPOSITORY+'/actions/runs/'+os.environ.get('GITHUB_RUN_ID', '')+').\n'
    release = api.request('/releases', {'tag_name': RELEASE_TAG, 'target_commitish': report['repository_commit'],
        'name': 'COH Atlas Gameplay 0.13.8 — client loading and model repair', 'body': body,
        'draft': True, 'prerelease': True, 'generate_release_notes': False, 'make_latest': 'false'}, method='POST')
    require(type(release.get('id')) is int and release.get('draft') is True and release.get('prerelease') is True and release.get('tag_name') == RELEASE_TAG, 'Unexpected created client asset release')
    for path in assets:
        uploaded = api.request('/releases/'+str(release['id'])+'/assets?'+urllib.parse.urlencode({'name': path.name}), path, method='POST', upload=True)
        expected = builder().file_pin(path)
        require(uploaded.get('state') == 'uploaded' and uploaded.get('name') == path.name and uploaded.get('size') == expected['bytes']
            and uploaded.get('digest') == 'sha256:'+expected['sha256'], 'Client asset release upload differs')
    published = api.request('/releases/'+str(release['id']), {'draft': False, 'prerelease': True, 'make_latest': 'false'}, method='PATCH')
    require(published.get('id') == release['id'] and published.get('draft') is False and published.get('prerelease') is True
        and published.get('tag_name') == RELEASE_TAG, 'Client asset publication did not complete')
    return published.get('html_url')


def publish(args):
    require(os.environ.get('GITHUB_REPOSITORY') == REPOSITORY and os.environ.get('GITHUB_REF') == 'refs/heads/'+BRANCH
        and os.environ.get('GITHUB_EVENT_NAME') in ('push', 'workflow_dispatch'), 'Publication requires authorized continuation branch')
    commit = builder().source_commit(os.environ.get('GITHUB_SHA')); report, checksum, public_notes = verify_report(args, commit)
    api = module('client_loading_github', Path(__file__).with_name('build_atlas_gameplay_apk.py'))
    print('Published client asset prerelease:', publish_release(api.GitHub(os.environ.get('GH_TOKEN')), report,
        (args.apk, checksum, public_notes), public_notes.read_text()))


def audit(args):
    commit = builder().source_commit(args.repository_commit); report, _, _ = verify_report(args, commit)
    print('Public APK independently verified:', report['sha256'], 'Game-only loading layer, retained 0.13.7 server/DLL bytes and 17 memory-protected Android sources')


def main():
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest='command', required=True)
    get = commands.add_parser('download-donor'); get.add_argument('--output', type=Path, required=True)
    create = commands.add_parser('build')
    for name in ('donor-apk', 'donor-build-report', 'qualification', 'visual-directory', 'client-directory', 'android-jar', 'build-tools', 'keystore', 'output'):
        create.add_argument('--'+name, type=Path, required=True)
    create.add_argument('--repository-commit'); create.add_argument('--password-env', default='COH_INTERACTIVE_KEYSTORE_PASSWORD')
    create.add_argument('--testing-notes', type=Path, default=NOTES)
    for command in ('publish', 'audit-public'):
        sub = commands.add_parser(command)
        for name in ('apk', 'build-report', 'build-tools', 'qualification', 'donor-build-report', 'donor-apk', 'visual-directory', 'client-directory'):
            sub.add_argument('--'+name, type=Path, required=True)
        sub.add_argument('--testing-notes', type=Path, default=NOTES)
        if command == 'audit-public': sub.add_argument('--repository-commit', required=True)
    args = parser.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path): setattr(args, key, value.absolute())
    {'download-donor': download, 'build': build, 'publish': publish, 'audit-public': audit}[args.command](args)


if __name__ == '__main__': main()
