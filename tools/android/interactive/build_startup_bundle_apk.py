#!/usr/bin/env python3
"""Build a narrowly allowlisted startup derivative from public 0.13.5.

The exact setup-memory DEX, 19 authored Java sources, signing identity, native
archives, graphics libraries, world/avatar assets and prepared caches are kept.
The explicit guest helpers, client runtime ZIP, normal DbServer supplement
and two verification manifests change. Native Game and DbServer each require
a separately validated source receipt; MapServer and all 20 client DLLs remain exact.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import stat
import tarfile
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

import build_setup_memory_apk as retained

ROOT = Path(__file__).resolve().parents[3]
shared = retained.shared
REPOSITORY, BRANCH, SIGNER = retained.REPOSITORY, retained.BRANCH, retained.SIGNER
DONOR_COMMIT = '31c8a1722f992e7a8334ef2256b4feaa9ca173be'
DONOR_RUNTIME_COMMIT = '6d16acf8330774e5fee4c0410c9cc56746d60b58'
RETAINED_NATIVE_COMMIT = retained.RETAINED_NATIVE_COMMIT
DONOR_RUN_ID = 37174737394
DONOR_APK_NAME = 'COH-Atlas-Gameplay-0.13.5.apk'
DONOR_APK = {'bytes': 676120510, 'sha256': 'b02cfa71498418a0fef0f5b3219a37207fcbc713fcece0c2dcc3a1019b5c3a13'}
DONOR_BUILD = {'bytes': 1480987, 'sha256': '1eaf9f7b3d7b71f7c6693cef03f79e7f4c7a7f5b9f8f061cd6769d4b9229eb5a'}
DONOR_URL = 'https://github.com/'+REPOSITORY+'/releases/download/coh-atlas-gameplay-v0.13.5/'+DONOR_APK_NAME
VERSION_NAME, VERSION_CODE = '0.13.6', 21
APK_NAME = 'COH-Atlas-Gameplay-0.13.6.apk'
REPORT_NAME = 'startup-bundle-apk-build-report.json'
NOTES_NAME = 'COH-Atlas-Gameplay-0.13.6-testing.txt'
NOTES = ROOT/'docs'/NOTES_NAME
RELEASE_TAG = 'coh-atlas-gameplay-v0.13.6'
HELPERS = frozenset({'character_creation_diagnostic.py', 'character_server_data_cache.py', 'texture_header_index.py',
    'client_interactive_diagnostic.py', 'client_startup_diagnostic.py', 'native_responsiveness_contract.py', 'local_character_server.py'})
NATIVE_ASSETS = frozenset({'startup-dbserver.exe', 'startup-dbserver-manifest.json', 'client-runtime.zip'})
REPLACED_PAYLOADS = frozenset('assets/runtime/'+name for name in HELPERS|NATIVE_ASSETS|{'client-manifest.json', 'runtime-manifest.json'})
JAVA_CHANGES = frozenset()
JAVA_ADDITIONS = frozenset()
QUALIFICATION_SCOPE = 'source_bound_startup_bundle_with_retained_setup_memory_protection'
CHECKS = ('changed_startup_paths_and_failure_guards_verified',
    'postgresql_save_emission_transaction_regression_verified',
    'retained_save_task_storage_profile_and_memory_guards_verified',
    'exact_payload_boundaries_and_actual_archive_extraction_verified')
WORKFLOW = '.github/workflows/android-startup-bundle.yml'
QUALIFICATION_SCRIPT = 'tools/android/interactive/qualify_startup_bundle.py'
SOURCE_FILES = frozenset((WORKFLOW, QUALIFICATION_SCRIPT,
    'tools/android/interactive/build_startup_bundle_apk.py',
    'tools/android/interactive/test_startup_bundle_package.py',
    'tools/android/interactive/package_startup_bundle_dbserver.py',
    'tools/android/interactive/test_startup_bundle_dbserver.py',
    'tools/android/interactive/test_startup_bundle_save.py',
    'patches/startup-bundle/0001-pg-cancelled-child-insert.patch',
    'tools/android/interactive/package_startup_bundle_client.py',
    'tools/android/interactive/test_startup_bundle_client.py',
    'patches/startup-bundle-client/0001-verified-texture-root.patch',
    'database/startup-bundle-client/overlay/Game/src/render/coh_texture_header_root.h',
    'tools/android/interactive/build_setup_memory_apk.py',
    'tools/android/interactive/qualify_setup_memory.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    '.github/workflows/android-startup-schedule.yml',
    '.github/workflows/android-setup-memory.yml',
    'android/interactive/src/main/AndroidManifest.xml', 'docs/'+NOTES_NAME,
    'docs/android-evidence/startup-bundle-0.13.5-device-result.json',
    *(('android/guest/'+name) for name in HELPERS)))
require, module, read_json = retained.require, retained.module, retained.read_json
archive_inventory = retained.archive_inventory
verify_server_archives, verify_apk_server_archives = retained.verify_server_archives, retained.verify_apk_server_archives
RETAINED_RECEIPT_FIELDS = tuple(name for name in retained.RETAINED_RECEIPT_FIELDS
    if name not in ('runtime_manifest', 'runtime_manifest_sha256', 'native_dbserver', 'native_dbserver_manifest'))


def builder(*, repaired=False):
    base = module('startup_bundle_android_builder', Path(__file__).with_name('build_apk.py'))
    if repaired: base.VERSION_NAME, base.VERSION_CODE, base.APK_NAME = VERSION_NAME, VERSION_CODE, APK_NAME
    return base


def donor_link():
    return {'run_id': DONOR_RUN_ID, 'repository_commit': DONOR_COMMIT, 'apk': DONOR_APK, 'build_report': DONOR_BUILD}


def validate_donor_receipt(path):
    base = builder(); base.checked_file(path, DONOR_BUILD)
    donor = read_json(path); qualification = donor.get('qualification', {})
    require(donor.get('format') == 1 and donor.get('repository_commit') == DONOR_COMMIT
        and donor.get('apk') == DONOR_APK_NAME and {key: donor.get(key) for key in DONOR_APK} == DONOR_APK
        and donor.get('application_id') == base.APP_ID and donor.get('version_name') == '0.13.5'
        and donor.get('version_code') == 20 and donor.get('abi') == 'arm64-v8a'
        and donor.get('signer_certificate_sha256') == SIGNER and donor.get('signing_key_created') is False
        and all(donor.get(key) is True for key in ('signature_verified', 'package_badging_verified',
            'binary_manifest_version_only_verified', 'payload_bytes_verified', 'installed_runtime_identity_preserved'))
        and all(donor.get(key) is False for key in ('native_libraries_changed', 'client_or_server_recompiled',
            'world_assets_changed', 'prepared_cache_archive_changed', 'dbserver_changed', 'graphics_driver_changed',
            'runtime_refresh_required'))
        and len(donor.get('payloads', {})) == 67 and len(donor.get('java_sources', {})) == 19
        and donor.get('server_payload_extraction_preflight', {}).get('status') == 'passed'
        and qualification.get('scope') == retained.QUALIFICATION_SCOPE
        and qualification.get('status') == 'passed' and qualification.get('tests_run') == 467
        and qualification.get('repository_commit') == DONOR_COMMIT
        and donor.get('runtime_repository_commit') == DONOR_RUNTIME_COMMIT
        and donor.get('retained_native_repository_commit') == RETAINED_NATIVE_COMMIT
        and donor.get('runtime_manifest', {}).get('repository_commit') == DONOR_RUNTIME_COMMIT
        and donor['runtime_manifest'].get('startup_only_reopen') is True
        and donor['runtime_manifest'].get('task_gate_required') is True
        and donor.get('native_dbserver', {}).get('repository_commit') == 'dee916f80e9e336f374f31228535afdbe2c928ca'
        and donor.get('server_animation_manifest', {}).get('repository_commit') == RETAINED_NATIVE_COMMIT,
        'Exact public 0.13.5 retained-memory donor receipt differs')
    return donor


def validate_donor(apk, receipt):
    base = builder(); base.checked_file(apk, DONOR_APK)
    donor = validate_donor_receipt(receipt); base.verify_packaged_payloads(apk, donor['payloads'])
    with zipfile.ZipFile(apk) as archive:
        shell = {'classes.dex': donor['recompiled_dex'], **donor['retained_android_resources']}
        require(archive_inventory(archive) == set(donor['payloads'])|set(shell)|{'AndroidManifest.xml'},
            'Unexpected donor APK inventory')
        for name, expected in shell.items():
            raw = archive.read(name)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == expected,
                'Donor Android shell differs: '+name)
        require(json.loads(archive.read('assets/runtime/runtime-manifest.json')) == donor['runtime_manifest']
            and json.loads(archive.read('assets/runtime/native-responsiveness.json')) == donor['native_responsiveness']
            and json.loads(archive.read('assets/runtime/server-animation-manifest.json')) == donor['server_animation_manifest'],
            'Donor retained runtime provenance differs')
    require(verify_apk_server_archives(apk) == donor['server_payload_extraction_preflight'],
        'Exact public donor does not pass actual guest extraction')
    with tempfile.TemporaryDirectory(prefix='coh-donor-client-') as temporary:
        path = Path(temporary)/'client-runtime.zip'
        with zipfile.ZipFile(apk) as archive, archive.open('assets/runtime/client-runtime.zip') as source, path.open('xb') as target:
            shutil.copyfileobj(source, target, 64*1024)
        with zipfile.ZipFile(path) as archive:
            donor['_client_manifest'] = json.loads(archive.read('client-package.json'))
            donor['_client_members'] = client_member_pins(archive)
        require(set(donor['_client_members']) == set(donor['_client_manifest']['files'])|{'client-package.json'}
            and donor['_client_manifest']['native_responsiveness']['receipt'] == donor['native_responsiveness'],
            'Donor client file inventory or frozen native receipt differs')
    return donor


def current_sources(donor):
    base = builder(); sources = retained.java_sources(base, ROOT/'out/no-generated-java')
    pins = {path.relative_to(ROOT).as_posix(): base.file_pin(path) for path in sources if path.is_relative_to(ROOT)}
    require(len(pins) == 19 and pins == donor['java_sources'] and not JAVA_CHANGES and not JAVA_ADDITIONS,
        'Startup bundle must retain all 19 setup-memory Java sources exactly')
    for name, expected in donor['preserved_sources'].items(): base.checked_file(ROOT/name, expected)
    base.checked_file(ROOT/'android/interactive/src/main/AndroidManifest.xml', donor['source_manifest'])
    for name, expected in donor['payloads'].items():
        if name.startswith('assets/runtime/') and (name.endswith('.py') or name.endswith('/task-gate.json')):
            if Path(name).name not in HELPERS: base.checked_file(ROOT/'android/guest'/Path(name).name, expected)
    require(HELPERS, 'Reviewed startup helper allowlist is required')
    changed = {name for name in HELPERS if base.file_pin(ROOT/'android/guest'/name) != donor['payloads']['assets/runtime/'+name]}
    require(changed == HELPERS, 'Startup bundle must change exactly the selected guest helpers')
    return pins


def client_member_pins(archive):
    entries = archive.infolist(); names = [entry.filename for entry in entries]
    require(len(names) == len(set(names)) and all('/' not in name and chr(92) not in name
        and name not in ('.', '..', '') for name in names)
        and all(not stat.S_ISLNK(entry.external_attr >> 16) for entry in entries), 'Unsafe or duplicate native client member')
    pins = {}
    for entry in entries:
        digest = hashlib.sha256(); count = 0
        require(0 < entry.file_size <= 64*1024*1024, 'Unbounded native client member')
        with archive.open(entry) as source:
            while chunk := source.read(64*1024): digest.update(chunk); count += len(chunk)
        require(count == entry.file_size, 'Truncated native client member')
        pins[entry.filename] = {'bytes': count, 'sha256': digest.hexdigest()}
    return pins


def native_builder():
    return module('startup_bundle_dbserver_package', Path(__file__).with_name('package_startup_bundle_dbserver.py'))


def client_builder():
    return module('startup_bundle_client_package', Path(__file__).with_name('package_startup_bundle_client.py'))


def validate_native(directory, client_directory, commit, donor_apk, donor):
    require(directory is not None and client_directory is not None, 'Both source-bound native bundle packages required')
    native = native_builder().validate_package(directory, commit)
    client = client_builder().validate_package(client_directory, commit)
    with zipfile.ZipFile(donor_apk) as apk, apk.open('assets/runtime/dbserver-package.tar.gz') as source:
        with tarfile.open(fileobj=source, mode='r|gz') as archive:
            raw = None
            for member in archive:
                if member.name != 'package-manifest.json': continue
                require(raw is None and member.isfile() and 0 < member.size <= 8*1024*1024, 'Invalid baseline DbServer manifest')
                raw = archive.extractfile(member).read()
    require(raw is not None, 'Baseline DbServer manifest missing')
    original = json.loads(raw); normal = original['variants']['normal']
    require(native.get('base_package_manifest_sha256') == hashlib.sha256(raw).hexdigest()
        and native.get('base_normal_executable') == normal['files']['DbServer.exe']
        and native.get('retained_normal_files') == {name: value for name, value in normal['files'].items() if name != 'DbServer.exe'}
        and native.get('base_normal_cmake_cache_sha256') == normal['cmake_cache_sha256']
        and native.get('build_input') == donor['native_dbserver']['build_input']
        and native['build_input'].get('base_wine_build_input') == original['wine_build_input']
        and native.get('base_startup_executable') == donor['payloads']['assets/runtime/startup-dbserver.exe'],
        'DbServer startup bundle changed its accepted base or manual launcher-wait lineage')
    require(client.get('retained_source_inputs') == donor['native_responsiveness']['build_inputs']
        and client.get('schema_sources_sha256') == donor['native_responsiveness']['retained_cache']['schema_sources_sha256']
        and client.get('files', {}).get('CityOfHeroes.exe') != donor['native_responsiveness']['files']['CityOfHeroes.exe'],
        'Client startup bundle changed its frozen source/schema lineage or lacks a new Game')
    return native, client


def client_manifest(donor, native):
    original = donor['_client_manifest']; expected = copy.deepcopy(original)
    expected['files']['CityOfHeroes.exe'] = native['files']['CityOfHeroes.exe']
    expected['dependency_report'] = shared.dependency_report(expected['files'])
    require(not expected['dependency_report']['unresolved'], 'New Game imports exceed exact retained DLL closure')
    expected['startup_bundle_client'] = {'manifest': native,
        'manifest_sha256': shared.native_contract.canonical_sha(native),
        'base_responsiveness_receipt_sha256': shared.native_contract.canonical_sha(donor['native_responsiveness']),
        'base_client_executable': donor['native_responsiveness']['files']['CityOfHeroes.exe']}
    shared.native_contract.client_contract(expected, donor['native_responsiveness'])
    return expected


def replace_client_archive(path, donor, native, client_directory):
    require(builder().file_pin(path) == donor['payloads']['assets/runtime/client-runtime.zip'], 'Client donor archive differs')
    updated = path.with_suffix('.candidate.zip'); require(not updated.exists(), 'Fresh client archive staging required')
    expected = client_manifest(donor, native)
    with zipfile.ZipFile(path) as original, zipfile.ZipFile(updated, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        require(client_member_pins(original) == donor['_client_members'], 'Extracted client member bytes differ')
        for entry in original.infolist():
            if entry.filename == 'client-package.json': archive.writestr(entry.filename, shared.encoded(expected))
            elif entry.filename == 'CityOfHeroes.exe': archive.write(client_directory/'CityOfHeroes.exe', entry.filename)
            else:
                with original.open(entry) as source, archive.open(entry.filename, 'w') as target:
                    shutil.copyfileobj(source, target, 64*1024)
    updated.replace(path)
    verify_client_archive(path, donor, native)


def verify_client_archive(path, donor, native):
    expected = client_manifest(donor, native)
    with zipfile.ZipFile(path) as archive:
        pins = client_member_pins(archive)
        require(set(pins) == set(donor['_client_members']) and len(pins) == 22, 'Native client member inventory changed')
        require(json.loads(archive.read('client-package.json')) == expected, 'Client package drifted beyond Game and separate startup receipt')
        require(pins['client-package.json'] == {'bytes': len(shared.encoded(expected)), 'sha256': hashlib.sha256(shared.encoded(expected)).hexdigest()},
            'Client package encoding differs')
        record = native['files']['CityOfHeroes.exe']
        require(pins['CityOfHeroes.exe'] == {'bytes': record['size'], 'sha256': record['sha256']}, 'Packaged new Game differs')
        require(all(pins[name] == pin for name, pin in donor['_client_members'].items()
            if name not in ('CityOfHeroes.exe', 'client-package.json')), 'A retained client DLL changed')
    return expected


def verification_manifests(donor, client, updates, commit):
    expected_client = copy.deepcopy(client); expected_client['files'].update(updates)
    expected_runtime = copy.deepcopy(donor['runtime_manifest']); expected_runtime['files'].update(updates)
    encoded = shared.encoded(expected_client)
    expected_runtime['files']['client-manifest.json'] = {'bytes': len(encoded), 'sha256': hashlib.sha256(encoded).hexdigest()}
    expected_runtime['repository_commit'] = commit
    expected_runtime['startup_bundle'] = {'format': 1, 'repository_commit': commit,
        'donor_repository_commit': DONOR_COMMIT, 'retained_setup_memory_repository_commit': DONOR_COMMIT,
        'retained_native_repository_commit': RETAINED_NATIVE_COMMIT,
        'native_dbserver_recompiled': True, 'native_client_recompiled': True, 'native_mapserver_recompiled': False,
        'physical_startup_timing_validated': False}
    expected_runtime['scope'] = 'Source-bound startup helper optimizations with exact retained setup-memory Android shell, native archives, prepared caches and existing private profile; physical startup timing pending'
    return expected_client, expected_runtime


def extract_and_repair(apk, donor, destination, commit, native_directory=None, client_directory=None):
    base = builder(); current_sources(donor)
    native, native_client = validate_native(native_directory, client_directory, commit, apk, donor)
    destination.mkdir(parents=True); extracted = {}
    with zipfile.ZipFile(apk) as archive:
        require(archive_inventory(archive) == set(donor['payloads'])|set(donor['retained_android_resources'])|
            {'AndroidManifest.xml', 'classes.dex'}, 'Unexpected donor APK inventory')
        for entry in archive.infolist():
            name = entry.filename
            if name == 'AndroidManifest.xml' or name.startswith('META-INF/'): continue
            target = destination/name; target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open('xb') as output: shutil.copyfileobj(source, output, 64*1024)
            extracted[name] = base.file_pin(target)
    require(all(extracted.get(name) == expected for name, expected in donor['payloads'].items()), 'Extracted donor payload bytes differ')
    assets = destination/'assets/runtime'; client = read_json(assets/'client-manifest.json')
    require(read_json(assets/'runtime-manifest.json') == donor['runtime_manifest'], 'Donor runtime manifest differs')
    for name in HELPERS:
        source = ROOT/'android/guest'/name; base.checked_file(source)
        require(0 < source.stat().st_size <= 1024*1024, 'Unbounded startup helper')
        shutil.copyfile(source, assets/name)
    for source_name, target_name in (('DbServer.exe', 'startup-dbserver.exe'),
        ('startup-dbserver-manifest.json', 'startup-dbserver-manifest.json')):
        shutil.copyfile(native_directory/source_name, assets/target_name)
    replace_client_archive(assets/'client-runtime.zip', donor, native_client, client_directory)
    updates = {name: base.file_pin(assets/name) for name in HELPERS|NATIVE_ASSETS}
    client, runtime = verification_manifests(donor, client, updates, commit)
    (assets/'client-manifest.json').write_bytes(shared.encoded(client))
    (assets/'runtime-manifest.json').write_bytes(shared.encoded(runtime))
    payloads = {name: base.file_pin(destination/name) for name in donor['payloads']}
    require({name for name in payloads if payloads[name] != donor['payloads'][name]} == REPLACED_PAYLOADS,
        'Unexpected startup payload replacement')
    preflight = verify_server_archives(assets)
    require(preflight == donor['server_payload_extraction_preflight'], 'Startup bundle changed retained archive extraction')
    return runtime, payloads, native, native_client, preflight


def repair_android_manifest(source, destination):
    base = builder(); base.verify_source_manifest(source)
    tree = ET.parse(source); manifest = tree.getroot()
    manifest.set(base.ANDROID+'versionName', VERSION_NAME); manifest.set(base.ANDROID+'versionCode', str(VERSION_CODE))
    ET.register_namespace('android', base.ANDROID[1:-1]); tree.write(destination, encoding='utf-8', xml_declaration=True)
    builder(repaired=True).verify_source_manifest(destination)


def verify_derivative(apk, donor, payloads, commit, native_directory=None, client_directory=None):
    require(set(payloads) == set(donor['payloads']) and len(payloads) == 67
        and {name for name in payloads if payloads[name] != donor['payloads'][name]} == REPLACED_PAYLOADS,
        'Candidate startup payload boundaries differ')
    native, native_client = validate_native(native_directory, client_directory, commit, apk, donor)
    base = builder(); base.verify_packaged_payloads(apk, payloads)
    with zipfile.ZipFile(apk) as archive:
        require(archive_inventory(archive) == set(payloads)|set(donor['retained_android_resources'])|
            {'AndroidManifest.xml', 'classes.dex'}, 'Unexpected candidate APK inventory')
        for name, expected in {'classes.dex': donor['recompiled_dex'], **donor['retained_android_resources']}.items():
            raw = archive.read(name)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == expected, 'Retained setup-memory Android shell differs')
        for name in HELPERS:
            require(payloads['assets/runtime/'+name] == base.file_pin(ROOT/'android/guest'/name), 'Authored startup helper differs: '+name)
        for source_name, target_name in (('DbServer.exe', 'startup-dbserver.exe'),
            ('startup-dbserver-manifest.json', 'startup-dbserver-manifest.json')):
            require(payloads['assets/runtime/'+target_name] == base.file_pin(native_directory/source_name),
                'Source-bound DbServer supplement differs')
        with tempfile.TemporaryDirectory(prefix='coh-candidate-client-') as temporary:
            path = Path(temporary)/'client-runtime.zip'
            with archive.open('assets/runtime/client-runtime.zip') as source, path.open('xb') as target:
                shutil.copyfileobj(source, target, 64*1024)
            verify_client_archive(path, donor, native_client)
        updates = {name: payloads['assets/runtime/'+name] for name in HELPERS|NATIVE_ASSETS}
        client = json.loads(archive.read('assets/runtime/client-manifest.json'))
        original_client = copy.deepcopy(client)
        for name in HELPERS|NATIVE_ASSETS: original_client['files'][name] = donor['payloads']['assets/runtime/'+name]
        raw = shared.encoded(original_client)
        require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == donor['payloads']['assets/runtime/client-manifest.json'],
            'Client manifest drifted outside source-bound updates')
        expected_client, expected_runtime = verification_manifests(donor, original_client, updates, commit)
        require(client == expected_client and json.loads(archive.read('assets/runtime/runtime-manifest.json')) == expected_runtime,
            'Runtime manifest drifted beyond startup source and asset pins')
        require(json.loads(archive.read('assets/runtime/native-responsiveness.json')) == donor['native_responsiveness']
            and json.loads(archive.read('assets/runtime/server-animation-manifest.json')) == donor['server_animation_manifest'],
            'Startup bundle relabelled retained native or animation history')
    return native, native_client


def validate_qualification(receipt, commit):
    require(receipt.get('format') == 1 and receipt.get('status') == 'passed'
        and receipt.get('scope') == QUALIFICATION_SCOPE and receipt.get('repository_commit') == commit
        and receipt.get('retained_runtime_repository_commit') == DONOR_RUNTIME_COMMIT
        and receipt.get('retained_setup_memory_repository_commit') == DONOR_COMMIT
        and receipt.get('retained_native_repository_commit') == RETAINED_NATIVE_COMMIT
        and receipt.get('donor_apk_sha256') == DONOR_APK['sha256']
        and all(receipt.get(key) is False for key in ('physical_gameplay_validated', 'physical_startup_timing_validated',
            'physical_storage_cleanup_validated', 'physical_fresh_profile_recovery_validated',
            'native_runtime_booted', 'long_prior_gameplay_milestones_repeated', 'asset_reimport_required', 'java_or_dex_recompiled'))
        and receipt.get('native_dbserver_recompiled') is bool(NATIVE_ASSETS)
        and receipt.get('native_client_recompiled') is True and receipt.get('native_mapserver_recompiled') is False
        and receipt.get('runtime_refresh_required') is True and receipt.get('previous_runtime_generation_retained') is True
        and receipt.get('setup_memory_guards_preserved') is True
        and receipt.get('postgresql_emission_fixture_verified') is True
        and receipt.get('postgresql_emission_fixtures') == ['cancelled_child_deletion_commits', 'delete_insert_replacement_commits', 'duplicate_insert_23505_rollback']
        and type(receipt.get('tests_run')) is int and receipt['tests_run'] > 0
        and set(receipt.get('checks', {})) == set(CHECKS) and all(value is True for value in receipt['checks'].values()),
        'Exact focused startup bundle qualification required')
    require(SOURCE_FILES <= set(receipt.get('source_files', {})), 'Qualification source closure incomplete')
    contract = module('startup_bundle_qualification_contract', ROOT/QUALIFICATION_SCRIPT)
    suites = receipt.get('test_suites', {}); check_suites = receipt.get('check_suites', {})
    require(set(suites) == set(contract.TEST_MODULES) and check_suites == contract.CHECK_SUITES,
        'Qualification must cover the exact startup and retained memory suite contract')
    require(all(item.get('status') == 'passed' and item.get('skipped') == 0
        and type(item.get('tests_run')) is int and item['tests_run'] > 0 for item in suites.values())
        and receipt['tests_run'] == sum(item['tests_run'] for item in suites.values()), 'Qualification suite evidence differs')
    for name, expected in receipt['source_files'].items():
        require(isinstance(name, str) and not Path(name).is_absolute() and '..' not in Path(name).parts and chr(92) not in name,
            'Unsafe qualification source path')
        builder().checked_file(ROOT/name, expected)
    return receipt


verify_signature = retained.verify_signature
verify_binary_manifest = retained.verify_binary_manifest


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
    qualified_native, qualified_client = validate_native(args.native_directory, args.client_directory, commit, args.donor_apk, donor)
    require(qualification.get('native_dbserver') == qualified_native
        and qualification.get('native_client_startup') == qualified_client, 'Native packages changed after host qualification')
    password = base.signing_password_spec(args.password_env)
    base.verify_signing_identity(args.keystore, 'coh-client-interactive', SIGNER, password)
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), 'Fresh startup bundle APK required')
    base.checked_file(args.testing_notes); require(0 < args.testing_notes.stat().st_size <= 65536, 'Bounded testing notes required')
    for tool in (args.android_jar, args.build_tools/'aapt2', args.build_tools/'zipalign', args.build_tools/'lib/apksigner.jar'):
        require(tool.is_file() and not tool.is_symlink(), 'Required Android tool missing')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-startup-bundle-', dir=args.output.parent) as temporary:
        work = Path(temporary)
        runtime, payloads, native, native_client, preflight = extract_and_repair(args.donor_apk, donor, work/'donor', commit, args.native_directory, args.client_directory)
        manifest = work/'AndroidManifest.xml'; repair_android_manifest(ROOT/'android/interactive/src/main/AndroidManifest.xml', manifest)
        resources, unsigned, aligned, signed = (work/name for name in ('resources.zip', 'unsigned.apk', 'aligned.apk', 'signed.apk'))
        base.run(args.build_tools/'aapt2', 'compile', '--dir', ROOT/'android/interactive/src/main/res', '-o', resources)
        base.run(args.build_tools/'aapt2', 'link', '-I', args.android_jar, '--manifest', manifest, '--min-sdk-version', '26', '--target-sdk-version', '35', resources, '-o', unsigned)
        with zipfile.ZipFile(unsigned) as archive:
            require(archive_inventory(archive) == {'AndroidManifest.xml', 'resources.arsc', 'res/drawable/ic_coh_client.xml'}, 'Generated Android resource inventory differs')
            for name in donor['retained_android_resources']:
                raw = archive.read(name)
                require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == donor['retained_android_resources'][name], 'Android resources changed beyond version metadata')
        with zipfile.ZipFile(unsigned, 'a', zipfile.ZIP_DEFLATED) as archive:
            base.append_payloads(archive, [(work/'donor'/name, name) for name in sorted(payloads)])
            archive.write(work/'donor/classes.dex', 'classes.dex')
        base.run(args.build_tools/'zipalign', '-f', '4', unsigned, aligned)
        base.run('java', '-jar', args.build_tools/'lib/apksigner.jar', 'sign', '--ks', args.keystore, '--ks-key-alias', 'coh-client-interactive', '--ks-pass', password, '--key-pass', password, '--out', signed, aligned)
        certificate = verify_signature(signed, args.build_tools); base.run(args.build_tools/'zipalign', '-c', '4', signed)
        current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', signed))
        verify_derivative(signed, donor, payloads, commit, args.native_directory, args.client_directory)
        verify_binary_manifest(signed, args.donor_apk, args.build_tools)
        require(verify_apk_server_archives(signed) == preflight, 'Signed startup bundle extraction differs')
        shutil.copyfile(signed, args.output)
        report = {'format': 1, 'apk': APK_NAME, **base.file_pin(args.output), 'repository_commit': commit,
            'runtime_repository_commit': commit, 'retained_runtime_repository_commit': DONOR_RUNTIME_COMMIT,
            'retained_setup_memory_repository_commit': DONOR_COMMIT,
            'retained_native_repository_commit': RETAINED_NATIVE_COMMIT, 'application_id': base.APP_ID,
            'version_name': VERSION_NAME, 'version_code': VERSION_CODE, 'abi': 'arm64-v8a',
            'signer_certificate_sha256': certificate, 'signing_key_created': False, 'signature_verified': True,
            'package_badging_verified': True, 'binary_manifest_version_only_verified': True,
            'payload_bytes_verified': True, 'payloads': payloads, 'changed_apk_payloads': sorted(REPLACED_PAYLOADS),
            'replaced_apk_payloads': sorted(REPLACED_PAYLOADS), 'added_apk_payloads': [],
            'retained_dex': donor['recompiled_dex'], 'donor': donor_link(), 'java_sources': current_sources(donor),
            'changed_java_sources': [], 'added_java_sources': [], 'preserved_sources': donor['preserved_sources'],
            'generated_manifest': base.file_pin(manifest), 'qualification': qualification,
            'qualification_receipt': base.file_pin(args.qualification), 'testing_notes': base.file_pin(args.testing_notes),
            'native_libraries_changed': False, 'client_or_server_recompiled': bool(NATIVE_ASSETS), 'java_or_dex_recompiled': False,
            'world_assets_changed': False, 'prepared_cache_archive_changed': False, 'dbserver_changed': bool(NATIVE_ASSETS),
            'graphics_driver_changed': False, 'physical_gameplay_validated': False,
            'physical_storage_cleanup_validated': False, 'physical_fresh_profile_recovery_validated': False, 'dialog_semantics_validated': False,
            'runtime_refresh_required': True, 'installed_runtime_identity_preserved': False, 'previous_runtime_generation_retained': True,
            'asset_reimport_required': False, 'setup_memory_guards_preserved': True,
            'native_dbserver_recompiled': True, 'native_client_recompiled': True, 'native_mapserver_recompiled': False,
            'runtime_manifest': runtime, 'runtime_manifest_sha256': payloads['assets/runtime/runtime-manifest.json']['sha256'],
            'native_dbserver': native, 'native_client_startup': native_client, 'native_dbserver_manifest': payloads['assets/runtime/startup-dbserver-manifest.json'],
            'scope': QUALIFICATION_SCOPE, **{name: donor[name] for name in RETAINED_RECEIPT_FIELDS}}
        (args.output.parent/REPORT_NAME).write_text(json.dumps(report, indent=2)+'\n')
        args.output.with_suffix('.apk.sha256').write_text(report['sha256']+'  '+APK_NAME+'\n')
        shutil.copyfile(args.testing_notes, args.output.parent/NOTES_NAME)
        print('Built startup bundle candidate', report['sha256'])


def verify_report(args, commit):
    base, current = builder(), builder(repaired=True)
    donor = validate_donor(args.donor_apk, args.donor_build_report)
    qualification = validate_qualification(read_json(args.qualification), commit); report = read_json(args.build_report)
    qualified_native, qualified_client = validate_native(args.native_directory, args.client_directory, commit, args.donor_apk, donor)
    require(qualification.get('native_dbserver') == qualified_native
        and qualification.get('native_client_startup') == qualified_client, 'Native packages changed after host qualification')
    require(report.get('format') == 1 and report.get('apk') == APK_NAME and report.get('repository_commit') == commit
        and report.get('runtime_repository_commit') == commit and report.get('retained_runtime_repository_commit') == DONOR_RUNTIME_COMMIT
        and report.get('retained_setup_memory_repository_commit') == DONOR_COMMIT
        and report.get('retained_native_repository_commit') == RETAINED_NATIVE_COMMIT
        and report.get('abi') == 'arm64-v8a' and report.get('scope') == QUALIFICATION_SCOPE
        and report.get('application_id') == base.APP_ID and report.get('version_name') == VERSION_NAME
        and report.get('version_code') == VERSION_CODE and report.get('signer_certificate_sha256') == SIGNER
        and report.get('signing_key_created') is False and report.get('donor') == donor_link()
        and report.get('qualification') == qualification and report.get('qualification_receipt') == base.file_pin(args.qualification)
        and report.get('java_sources') == current_sources(donor) and report.get('changed_java_sources') == []
        and report.get('added_java_sources') == [] and report.get('retained_dex') == donor['recompiled_dex']
        and report.get('preserved_sources') == donor['preserved_sources']
        and report.get('changed_apk_payloads') == sorted(REPLACED_PAYLOADS)
        and report.get('replaced_apk_payloads') == sorted(REPLACED_PAYLOADS) and report.get('added_apk_payloads') == []
        and all(report.get(key) is True for key in ('signature_verified', 'package_badging_verified', 'binary_manifest_version_only_verified',
            'payload_bytes_verified', 'previous_runtime_generation_retained', 'runtime_refresh_required', 'setup_memory_guards_preserved', 'native_client_recompiled'))
        and all(report.get(key) is False for key in ('native_libraries_changed', 'java_or_dex_recompiled', 'world_assets_changed',
            'prepared_cache_archive_changed', 'graphics_driver_changed', 'physical_gameplay_validated', 'physical_storage_cleanup_validated',
            'physical_fresh_profile_recovery_validated', 'dialog_semantics_validated', 'native_mapserver_recompiled',
            'installed_runtime_identity_preserved', 'asset_reimport_required'))
        and all(report.get(key) is bool(NATIVE_ASSETS) for key in ('client_or_server_recompiled', 'dbserver_changed', 'native_dbserver_recompiled'))
        and all(report.get(name) == donor[name] for name in RETAINED_RECEIPT_FIELDS), 'Startup bundle build receipt differs')
    base.checked_file(args.apk, report); native, native_client = verify_derivative(args.apk, donor, report['payloads'], commit, args.native_directory, args.client_directory)
    require(report.get('native_dbserver') == native and report.get('native_client_startup') == native_client
        and report.get('native_dbserver_manifest') == report['payloads']['assets/runtime/startup-dbserver-manifest.json']
        and report.get('runtime_manifest_sha256') == report['payloads']['assets/runtime/runtime-manifest.json']['sha256'], 'Runtime/native provenance differs')
    with zipfile.ZipFile(args.apk) as archive:
        require(report.get('runtime_manifest') == json.loads(archive.read('assets/runtime/runtime-manifest.json')), 'Reported runtime manifest differs')
    verify_binary_manifest(args.apk, args.donor_apk, args.build_tools)
    require(verify_apk_server_archives(args.apk) == report['server_payload_extraction_preflight'], 'Published startup bundle fails actual guest extraction')
    verify_signature(args.apk, args.build_tools); base.run(args.build_tools/'zipalign', '-c', '4', args.apk)
    current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', args.apk))
    checksum = args.apk.with_suffix('.apk.sha256')
    require(checksum.read_text() == report['sha256']+'  '+APK_NAME+'\n', 'Published checksum differs')
    public_notes = args.apk.parent/NOTES_NAME
    base.checked_file(public_notes, report['testing_notes']); base.checked_file(args.testing_notes, report['testing_notes'])
    return report, checksum, public_notes


def publish_release(api, report, assets, notes):
    require(tuple(path.name for path in assets) == (APK_NAME, APK_NAME+'.sha256', NOTES_NAME), 'Unexpected startup bundle release assets')
    builder().checked_file(assets[0], report)
    for path in ('/releases/tags/'+RELEASE_TAG, '/git/ref/tags/'+RELEASE_TAG):
        try: existing = api.request(path)
        except urllib.error.HTTPError as error:
            if error.code != 404: raise
        else:
            require(not path.startswith('/releases/'), 'Existing startup bundle release is never replaced')
            require(existing.get('object', {}).get('type') == 'commit' and existing['object'].get('sha') == report['repository_commit'], 'Existing tag points elsewhere')
    body = notes+'\n\nAPK SHA-256: `'+report['sha256']+'`.\n'
    body += '[Source-bound startup and retained-memory host qualification](https://github.com/'+REPOSITORY+'/actions/runs/'+os.environ.get('GITHUB_RUN_ID', '')+').\n'
    release = api.request('/releases', {'tag_name': RELEASE_TAG, 'target_commitish': report['repository_commit'],
        'name': 'COH Atlas Gameplay 0.13.6 — startup reuse bundle', 'body': body,
        'draft': True, 'prerelease': True, 'generate_release_notes': False, 'make_latest': 'false'}, method='POST')
    require(type(release.get('id')) is int and release.get('draft') is True and release.get('prerelease') is True and release.get('tag_name') == RELEASE_TAG, 'Unexpected created startup bundle release')
    for path in assets:
        uploaded = api.request('/releases/'+str(release['id'])+'/assets?'+urllib.parse.urlencode({'name': path.name}), path, method='POST', upload=True)
        expected = builder().file_pin(path)
        require(uploaded.get('state') == 'uploaded' and uploaded.get('name') == path.name and uploaded.get('size') == expected['bytes']
            and uploaded.get('digest') == 'sha256:'+expected['sha256'], 'Startup bundle release upload differs')
    published = api.request('/releases/'+str(release['id']), {'draft': False, 'prerelease': True, 'make_latest': 'false'}, method='PATCH')
    require(published.get('id') == release['id'] and published.get('draft') is False and published.get('prerelease') is True
        and published.get('tag_name') == RELEASE_TAG, 'Startup bundle publication did not complete')
    return published.get('html_url')


def publish(args):
    require(os.environ.get('GITHUB_REPOSITORY') == REPOSITORY and os.environ.get('GITHUB_REF') == 'refs/heads/'+BRANCH
        and os.environ.get('GITHUB_EVENT_NAME') in ('push', 'workflow_dispatch'), 'Publication requires authorized continuation branch')
    commit = builder().source_commit(os.environ.get('GITHUB_SHA')); report, checksum, public_notes = verify_report(args, commit)
    api = module('startup_bundle_github', Path(__file__).with_name('build_atlas_gameplay_apk.py'))
    print('Published startup bundle prerelease:', publish_release(api.GitHub(os.environ.get('GH_TOKEN')), report,
        (args.apk, checksum, public_notes), public_notes.read_text()))


def audit(args):
    commit = builder().source_commit(args.repository_commit); report, _, _ = verify_report(args, commit)
    print('Public APK independently verified:', report['sha256'], '67 tightly bounded payloads; retained 0.13.5 memory DEX')


def main():
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest='command', required=True)
    get = commands.add_parser('download-donor'); get.add_argument('--output', type=Path, required=True)
    create = commands.add_parser('build')
    for name in ('donor-apk', 'donor-build-report', 'qualification', 'android-jar', 'build-tools', 'keystore', 'output'):
        create.add_argument('--'+name, type=Path, required=True)
    create.add_argument('--native-directory', type=Path, required=True); create.add_argument('--client-directory', type=Path, required=True); create.add_argument('--repository-commit')
    create.add_argument('--password-env', default='COH_INTERACTIVE_KEYSTORE_PASSWORD'); create.add_argument('--testing-notes', type=Path, default=NOTES)
    for command in ('publish', 'audit-public'):
        sub = commands.add_parser(command)
        for name in ('apk', 'build-report', 'build-tools', 'qualification', 'donor-build-report', 'donor-apk'):
            sub.add_argument('--'+name, type=Path, required=True)
        sub.add_argument('--native-directory', type=Path, required=True); sub.add_argument('--client-directory', type=Path, required=True); sub.add_argument('--testing-notes', type=Path, default=NOTES)
        if command == 'audit-public': sub.add_argument('--repository-commit', required=True)
    args = parser.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path): setattr(args, key, value.absolute())
    {'download-donor': download, 'build': build, 'publish': publish, 'audit-public': audit}[args.command](args)


if __name__ == '__main__': main()
