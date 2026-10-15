#!/usr/bin/env python3
"""Build a source-bound startup derivative of the immutable public 0.13.2 APK.

Retain every donor native archive, world/avatar asset, cache and Android DEX.
Only four guest helpers, their verification manifests, and two independently
receipted guarded DbServer assets can change. The installed profile keeps its
original DbServer package identity; its baseline archive is never rewritten.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile

import build_storage_recovery_apk as retained
import build_responsiveness_apk as shared

ROOT = Path(__file__).resolve().parents[3]
REPOSITORY, BRANCH, SIGNER = shared.REPOSITORY, shared.BRANCH, shared.SIGNER
DONOR_COMMIT = 'c0d10f8cd873449962f5a723d489b9ead18642d0'
RETAINED_NATIVE_COMMIT = '53c885896e9b4d838be0f36a1f09237f04c08a00'
DONOR_RUN_ID = 37147463123
DONOR_APK_NAME = 'COH-Atlas-Gameplay-0.13.2.apk'
DONOR_APK = {'bytes': 675301138, 'sha256': '28e3eda8dbc3982bc42d42dee6ab4f35e985d96af31bff4a2c691b806a207e1f'}
DONOR_BUILD = {'bytes': 1461453, 'sha256': '33028c44f9dd733fd0bf862f4c5d176c5f96081ddaf28e56634f5bdbdfeb41ef'}
DONOR_URL = 'https://github.com/'+REPOSITORY+'/releases/download/coh-atlas-gameplay-v0.13.2/'+DONOR_APK_NAME
VERSION_NAME, VERSION_CODE = '0.13.3', 18
APK_NAME = 'COH-Atlas-Gameplay-0.13.3.apk'
REPORT_NAME = 'startup-schedule-apk-build-report.json'
NOTES_NAME = 'COH-Atlas-Gameplay-0.13.3-testing.txt'
NOTES = ROOT/'docs'/NOTES_NAME
RELEASE_TAG = 'coh-atlas-gameplay-v0.13.3'
HELPERS = frozenset(('atlas_world_assets.py', 'character_creation_diagnostic.py', 'local_character_server.py', 'local_login_server.py'))
NATIVE_ASSETS = frozenset(('startup-dbserver.exe', 'startup-dbserver-manifest.json'))
ADDED_PAYLOADS = frozenset('assets/runtime/'+name for name in NATIVE_ASSETS)
REPLACED_PAYLOADS = frozenset('assets/runtime/'+name for name in HELPERS|{'client-manifest.json', 'runtime-manifest.json'})
QUALIFICATION_SCOPE = 'source_bound_startup_schedule_world_reuse_and_guarded_manual_atlas_dbserver'
CHECKS = ('world_supplement_reuse_identity_and_invalidation_verified',
    'atlas_first_texture_schedule_and_failure_cleanup_verified',
    'guarded_native_manual_atlas_launcher_wait_verified',
    'retained_save_task_storage_profile_and_cache_guards_verified',
    'source_bound_payload_and_actual_archive_extraction_verified')
WORKFLOW = '.github/workflows/android-startup-schedule.yml'
QUALIFICATION_SCRIPT = 'tools/android/interactive/qualify_startup_schedule.py'
NATIVE_SCRIPT = 'tools/android/interactive/package_startup_dbserver.py'
SOURCE_FILES = frozenset((WORKFLOW, QUALIFICATION_SCRIPT, NATIVE_SCRIPT,
    '.github/workflows/android-storage-recovery.yml',
    '.github/workflows/android-storage-cleanup.yml',
    '.github/workflows/android-task-gate.yml',
    '.github/workflows/android-client-interactive.yml',
    'tools/android/interactive/build_startup_schedule_apk.py',
    'tools/android/interactive/test_startup_schedule_package.py',
    'tools/android/interactive/test_startup_schedule.py',
    'tools/android/interactive/test_world_asset_reuse.py',
    'tools/android/interactive/test_atlas_world_assets.py',
    'tools/android/interactive/test_local_launcher_wait.py',
    'tools/android/interactive/build_storage_recovery_apk.py',
    'tools/android/interactive/build_responsiveness_apk.py',
    'tools/android/interactive/build_apk.py',
    'tools/android/interactive/build_atlas_gameplay_apk.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'android/interactive/src/main/AndroidManifest.xml',
    'docs/'+NOTES_NAME, *(('android/guest/'+name) for name in HELPERS)))
SOURCE_FILES |= frozenset({'docs/android-evidence/startup-schedule-0.13.3-baseline.json'})
RETAINED_RECEIPT_FIELDS = tuple(name for name in retained.RETAINED_RECEIPT_FIELDS
    if name not in ('runtime_manifest', 'runtime_manifest_sha256'))
require, module, read_json = shared.require, shared.module, shared.read_json
verify_server_archives, verify_apk_server_archives = shared.verify_server_archives, shared.verify_apk_server_archives
archive_inventory = retained.archive_inventory
verify_binary_manifest = retained.verify_binary_manifest


def builder(*, repaired=False):
    base = module('startup_schedule_android_builder', Path(__file__).with_name('build_apk.py'))
    if repaired: base.VERSION_NAME, base.VERSION_CODE, base.APK_NAME = VERSION_NAME, VERSION_CODE, APK_NAME
    return base


def native_builder():
    return module('startup_schedule_dbserver_builder', ROOT/NATIVE_SCRIPT)


def donor_link():
    return {'run_id': DONOR_RUN_ID, 'repository_commit': DONOR_COMMIT, 'apk': DONOR_APK, 'build_report': DONOR_BUILD}


def validate_donor_receipt(path):
    base = builder(); base.checked_file(path, DONOR_BUILD)
    donor = read_json(path); qualification = donor.get('qualification', {})
    require(donor.get('format') == 1 and donor.get('repository_commit') == DONOR_COMMIT
        and donor.get('apk') == DONOR_APK_NAME and {key: donor.get(key) for key in DONOR_APK} == DONOR_APK
        and donor.get('application_id') == base.APP_ID and donor.get('version_name') == '0.13.2'
        and donor.get('version_code') == 17 and donor.get('abi') == 'arm64-v8a'
        and donor.get('signer_certificate_sha256') == SIGNER and donor.get('signing_key_created') is False
        and all(donor.get(key) is True for key in ('signature_verified', 'package_badging_verified',
            'binary_manifest_version_only_verified', 'payload_bytes_verified'))
        and all(donor.get(key) is False for key in ('native_libraries_changed', 'client_or_server_recompiled',
            'world_assets_changed', 'prepared_cache_archive_changed', 'dbserver_changed', 'graphics_driver_changed'))
        and len(donor.get('payloads', {})) == 65 and len(donor.get('java_sources', {})) == 18
        and donor.get('server_payload_extraction_preflight', {}).get('status') == 'passed'
        and qualification.get('scope') == retained.QUALIFICATION_SCOPE and qualification.get('status') == 'passed'
        and qualification.get('tests_run') == 489 and qualification.get('repository_commit') == DONOR_COMMIT
        and donor.get('runtime_repository_commit') == RETAINED_NATIVE_COMMIT
        and donor.get('runtime_manifest', {}).get('repository_commit') == RETAINED_NATIVE_COMMIT
        and donor['runtime_manifest'].get('task_gate_required') is True
        and donor.get('server_animation_manifest', {}).get('repository_commit') == RETAINED_NATIVE_COMMIT,
        'Exact public 0.13.2 retained-signer donor receipt differs')
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
    return donor


def current_sources(donor):
    """Bind the exact donor shell and every guest helper outside the allowlist."""
    base = builder()
    sources = base.java_sources(ROOT/'android/interactive/src/main', ROOT/'out/no-generated-java')
    pins = {path.relative_to(ROOT).as_posix(): base.file_pin(path) for path in sources if path.is_relative_to(ROOT)}
    require(len(pins) == 18 and pins == donor['java_sources'], 'Startup derivative must retain all 18 authored Java sources')
    for name, expected in donor['preserved_sources'].items():
        if name not in {'android/guest/'+helper for helper in HELPERS}: base.checked_file(ROOT/name, expected)
    base.checked_file(ROOT/'android/interactive/src/main/AndroidManifest.xml', donor['source_manifest'])
    for name, expected in donor['payloads'].items():
        if name.startswith('assets/runtime/') and (name.endswith('.py') or name.endswith('/task-gate.json')):
            if Path(name).name not in HELPERS: base.checked_file(ROOT/'android/guest'/Path(name).name, expected)
    changed = {name for name in HELPERS if base.file_pin(ROOT/'android/guest'/name) != donor['payloads']['assets/runtime/'+name]}
    require(changed == HELPERS, 'Startup derivative must change exactly the four authorized helpers')
    return pins


def validate_native(directory, commit, donor_apk):
    """Bind supplemental dependency and base records to the actual public archive."""
    native = native_builder().validate_package(directory, commit)
    with zipfile.ZipFile(donor_apk) as apk, apk.open('assets/runtime/dbserver-package.tar.gz') as source:
        with tarfile.open(fileobj=source, mode='r|gz') as archive:
            raw = None
            for member in archive:
                if member.name != 'package-manifest.json': continue
                require(raw is None and member.isfile() and 0 < member.size <= 8*1024*1024,
                        'Invalid baseline DbServer package manifest')
                raw = archive.extractfile(member).read()
    require(raw is not None, 'Baseline DbServer package manifest missing')
    original = json.loads(raw); normal = original['variants']['normal']
    require(native.get('base_package_manifest_sha256') == hashlib.sha256(raw).hexdigest()
        and native.get('base_normal_executable') == normal['files']['DbServer.exe']
        and native.get('retained_normal_files') == {name: value for name, value in normal['files'].items() if name != 'DbServer.exe'}
        and native.get('base_normal_cmake_cache_sha256') == normal['cmake_cache_sha256']
        and native.get('build_input', {}).get('base_wine_build_input') == original['wine_build_input'],
        'Supplemental native receipt differs from actual retained baseline DbServer')
    return native


def validate_qualification(receipt, commit):
    require(receipt.get('format') == 1 and receipt.get('status') == 'passed'
        and receipt.get('scope') == QUALIFICATION_SCOPE and receipt.get('repository_commit') == commit
        and receipt.get('retained_native_repository_commit') == RETAINED_NATIVE_COMMIT
        and receipt.get('donor_apk_sha256') == DONOR_APK['sha256']
        and all(receipt.get(key) is False for key in ('physical_gameplay_validated', 'physical_startup_timing_validated',
            'physical_storage_cleanup_validated', 'physical_fresh_profile_recovery_validated',
            'native_runtime_booted', 'long_prior_gameplay_milestones_repeated'))
        and receipt.get('native_dbserver_recompiled') is True and receipt.get('native_game_or_mapserver_recompiled') is False
        and type(receipt.get('tests_run')) is int and receipt['tests_run'] > 0
        and set(receipt.get('checks', {})) == set(CHECKS) and all(value is True for value in receipt['checks'].values()),
        'Exact focused startup-schedule qualification is required')
    require(SOURCE_FILES <= set(receipt.get('source_files', {})), 'Qualification source closure incomplete')
    suites = receipt.get('test_suites', {}); check_suites = receipt.get('check_suites', {})
    contract = module('startup_schedule_qualification_contract', ROOT/QUALIFICATION_SCRIPT)
    require(set(suites) == set(contract.TEST_MODULES) and check_suites == contract.CHECK_SUITES,
            'Qualification must cover the exact focused startup suite contract')
    require(set(check_suites) == set(CHECKS) and suites and all(isinstance(names, list) and names
        and all(name in suites and suites[name].get('status') == 'passed' and suites[name].get('skipped') == 0
            and type(suites[name].get('tests_run')) is int and suites[name]['tests_run'] > 0 for name in names)
        for names in check_suites.values()), 'Focused qualification suite evidence is incomplete')
    require(receipt['tests_run'] == sum(item['tests_run'] for item in suites.values()), 'Qualification test count differs')
    for name, expected in receipt['source_files'].items():
        require(isinstance(name, str) and not Path(name).is_absolute() and '..' not in Path(name).parts
                and '\\' not in name, 'Unsafe qualification source path')
        builder().checked_file(ROOT/name, expected)
    return receipt


def verification_manifests(donor, client, updates, commit):
    expected_client = copy.deepcopy(client); expected_client['files'].update(updates)
    expected_runtime = copy.deepcopy(donor['runtime_manifest']); expected_runtime['files'].update(updates)
    expected_runtime['files']['client-manifest.json'] = {'bytes': len(shared.encoded(expected_client)),
        'sha256': hashlib.sha256(shared.encoded(expected_client)).hexdigest()}
    expected_runtime['repository_commit'] = commit
    expected_runtime['startup_schedule'] = {'format': 1, 'repository_commit': commit,
        'donor_repository_commit': DONOR_COMMIT, 'retained_native_repository_commit': RETAINED_NATIVE_COMMIT,
        'native_dbserver_manifest': updates['startup-dbserver-manifest.json'],
        'physical_startup_timing_validated': False}
    expected_runtime['scope'] = 'Guarded manual Atlas DbServer startup, validated world supplement reuse and Atlas-first texture scheduling; retained baseline native archives, caches, world/avatar assets and Android shell; physical startup timing pending'
    return expected_client, expected_runtime


def extract_and_repair(apk, donor, destination, commit, native_directory):
    base = builder(); current_sources(donor)
    native = validate_native(native_directory, commit, apk)
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
    require(read_json(assets/'runtime-manifest.json') == donor['runtime_manifest'], 'Donor runtime verification manifest differs')
    for name in HELPERS:
        source = ROOT/'android/guest'/name; base.checked_file(source)
        require(0 < source.stat().st_size <= 1024*1024, 'Unbounded startup helper')
        shutil.copyfile(source, assets/name)
    for source_name, target_name in (('DbServer.exe', 'startup-dbserver.exe'),
                                   ('startup-dbserver-manifest.json', 'startup-dbserver-manifest.json')):
        require(not (assets/target_name).exists(), 'Supplemental startup DbServer collides with donor')
        shutil.copyfile(native_directory/source_name, assets/target_name)
    updates = {name: base.file_pin(assets/name) for name in HELPERS|NATIVE_ASSETS}
    client, runtime = verification_manifests(donor, client, updates, commit)
    (assets/'client-manifest.json').write_bytes(shared.encoded(client))
    (assets/'runtime-manifest.json').write_bytes(shared.encoded(runtime))
    payloads = {name: base.file_pin(destination/name) for name in set(donor['payloads'])|ADDED_PAYLOADS}
    require({name for name in donor['payloads'] if payloads[name] != donor['payloads'][name]} == REPLACED_PAYLOADS,
            'Unexpected startup helper or manifest replacement')
    preflight = verify_server_archives(assets)
    require(preflight == donor['server_payload_extraction_preflight'], 'Startup derivative changed retained archive extraction')
    return runtime, payloads, native, preflight


def repair_android_manifest(source, destination):
    retained.repair_android_manifest(source, destination)
    # The retained helper generates 0.13.2; apply our two version-only values.
    import xml.etree.ElementTree as ET
    base = builder(); tree = ET.parse(destination); manifest = tree.getroot()
    manifest.set(base.ANDROID+'versionName', VERSION_NAME); manifest.set(base.ANDROID+'versionCode', str(VERSION_CODE))
    ET.register_namespace('android', base.ANDROID[1:-1]); tree.write(destination, encoding='utf-8', xml_declaration=True)
    builder(repaired=True).verify_source_manifest(destination)


def verify_derivative(apk, donor, payloads, commit, native_directory):
    require(set(payloads) == set(donor['payloads'])|ADDED_PAYLOADS
        and {name for name in donor['payloads'] if payloads[name] != donor['payloads'][name]} == REPLACED_PAYLOADS,
        'Candidate startup payload boundaries differ')
    native = native_builder().validate_package(native_directory, commit)
    base = builder(); base.verify_packaged_payloads(apk, payloads)
    with zipfile.ZipFile(apk) as archive:
        require(archive_inventory(archive) == set(payloads)|set(donor['retained_android_resources'])|
                {'AndroidManifest.xml', 'classes.dex'}, 'Unexpected candidate APK inventory')
        for name, expected in {'classes.dex': donor['recompiled_dex'], **donor['retained_android_resources']}.items():
            raw = archive.read(name)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == expected, 'Retained Android shell differs')
        for name in HELPERS:
            require(payloads['assets/runtime/'+name] == base.file_pin(ROOT/'android/guest'/name), 'Authored startup helper differs: '+name)
        for source_name, target_name in (('DbServer.exe', 'startup-dbserver.exe'),
                                       ('startup-dbserver-manifest.json', 'startup-dbserver-manifest.json')):
            require(payloads['assets/runtime/'+target_name] == base.file_pin(native_directory/source_name),
                    'Source-bound supplemental native asset differs: '+target_name)
        updates = {name: payloads['assets/runtime/'+name] for name in HELPERS|NATIVE_ASSETS}
        # Recover the donor client manifest from the retained runtime pin metadata.
        client = json.loads(archive.read('assets/runtime/client-manifest.json'))
        original_client = copy.deepcopy(client)
        for name in HELPERS: original_client['files'][name] = donor['payloads']['assets/runtime/'+name]
        for name in NATIVE_ASSETS: original_client['files'].pop(name, None)
        require({'bytes': len(shared.encoded(original_client)), 'sha256': hashlib.sha256(shared.encoded(original_client)).hexdigest()}
            == donor['payloads']['assets/runtime/client-manifest.json'], 'Client manifest drifted outside source-bound updates')
        expected_client, expected_runtime = verification_manifests(donor, original_client, updates, commit)
        require(client == expected_client and json.loads(archive.read('assets/runtime/runtime-manifest.json')) == expected_runtime,
                'Runtime manifest drifted beyond startup source and asset pins')
        require(json.loads(archive.read('assets/runtime/native-responsiveness.json')) == donor['native_responsiveness']
            and json.loads(archive.read('assets/runtime/server-animation-manifest.json')) == donor['server_animation_manifest'],
            'Startup derivative relabelled retained native or animation history')
    return native


def verify_signature(apk, build_tools):
    return retained.verify_signature(apk, build_tools)


def download(args):
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh donor download required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(DONOR_URL, timeout=120) as source, args.output.open('xb') as target:
        total = 0
        while chunk := source.read(1024*1024):
            total += len(chunk); require(total <= DONOR_APK['bytes'], 'Oversized donor download'); target.write(chunk)
    builder().checked_file(args.output, DONOR_APK)


def build(args):
    base, current = builder(), builder(repaired=True)
    commit = base.source_commit(args.repository_commit)
    donor = validate_donor(args.donor_apk, args.donor_build_report)
    qualification = validate_qualification(read_json(args.qualification), commit)
    java = current_sources(donor); native = validate_native(args.native_directory, commit, args.donor_apk)
    require(qualification.get('native_dbserver') == native, 'Qualification native build differs')
    password = base.signing_password_spec(args.password_env)
    base.verify_signing_identity(args.keystore, 'coh-client-interactive', SIGNER, password)
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), 'Fresh startup APK required')
    base.checked_file(args.testing_notes); require(0 < args.testing_notes.stat().st_size <= 65536, 'Bounded testing notes required')
    for tool in (args.android_jar, args.build_tools/'aapt2', args.build_tools/'zipalign', args.build_tools/'lib/apksigner.jar'):
        require(tool.is_file() and not tool.is_symlink(), 'Required Android tool missing')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-startup-', dir=args.output.parent) as temporary:
        work = Path(temporary)
        runtime, payloads, native, preflight = extract_and_repair(args.donor_apk, donor, work/'donor', commit, args.native_directory)
        manifest = work/'AndroidManifest.xml'; repair_android_manifest(ROOT/'android/interactive/src/main/AndroidManifest.xml', manifest)
        resources, unsigned, aligned, signed, generated = (work/name for name in ('resources.zip', 'unsigned.apk', 'aligned.apk', 'signed.apk', 'generated'))
        base.run(args.build_tools/'aapt2', 'compile', '--dir', ROOT/'android/interactive/src/main/res', '-o', resources)
        base.run(args.build_tools/'aapt2', 'link', '-I', args.android_jar, '--manifest', manifest, '--min-sdk-version', '26', '--target-sdk-version', '35', '--java', generated, resources, '-o', unsigned)
        with zipfile.ZipFile(unsigned) as archive:
            require(archive_inventory(archive) == {'AndroidManifest.xml', 'resources.arsc', 'res/drawable/ic_coh_client.xml'}, 'Generated Android resource inventory differs')
            for name, expected in donor['retained_android_resources'].items():
                raw = archive.read(name)
                require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == expected, 'Android resources changed beyond version metadata')
        with zipfile.ZipFile(unsigned, 'a', zipfile.ZIP_DEFLATED) as archive:
            base.append_payloads(archive, [(work/'donor'/name, name) for name in sorted(payloads)])
            archive.write(work/'donor/classes.dex', 'classes.dex')
        base.run(args.build_tools/'zipalign', '-f', '4', unsigned, aligned)
        base.run('java', '-jar', args.build_tools/'lib/apksigner.jar', 'sign', '--ks', args.keystore, '--ks-key-alias', 'coh-client-interactive', '--ks-pass', password, '--key-pass', password, '--out', signed, aligned)
        certificate = verify_signature(signed, args.build_tools); base.run(args.build_tools/'zipalign', '-c', '4', signed)
        current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', signed))
        verify_derivative(signed, donor, payloads, commit, args.native_directory)
        verify_binary_manifest(signed, args.donor_apk, args.build_tools)
        require(verify_apk_server_archives(signed) == preflight, 'Signed startup APK retained archive extraction differs')
        shutil.copyfile(signed, args.output)
        report = {'format': 1, 'apk': APK_NAME, **base.file_pin(args.output), 'repository_commit': commit,
            'runtime_repository_commit': commit, 'retained_native_repository_commit': RETAINED_NATIVE_COMMIT,
            'application_id': base.APP_ID, 'version_name': VERSION_NAME, 'version_code': VERSION_CODE, 'abi': 'arm64-v8a',
            'signer_certificate_sha256': certificate, 'signing_key_created': False, 'signature_verified': True,
            'package_badging_verified': True, 'binary_manifest_version_only_verified': True, 'payload_bytes_verified': True,
            'payloads': payloads, 'changed_apk_payloads': sorted(REPLACED_PAYLOADS|ADDED_PAYLOADS),
            'replaced_apk_payloads': sorted(REPLACED_PAYLOADS), 'added_apk_payloads': sorted(ADDED_PAYLOADS),
            'runtime_manifest': runtime, 'runtime_manifest_sha256': payloads['assets/runtime/runtime-manifest.json']['sha256'],
            'native_dbserver': native, 'native_dbserver_manifest': base.file_pin(args.native_directory/'startup-dbserver-manifest.json'),
            'retained_dex': donor['recompiled_dex'], 'donor_dex': donor['recompiled_dex'], 'donor': donor_link(),
            'java_sources': java, 'changed_java_sources': [], 'added_java_sources': [],
            'preserved_sources': {name: pin for name, pin in donor['preserved_sources'].items() if name not in {'android/guest/'+helper for helper in HELPERS}},
            'generated_manifest': base.file_pin(manifest), 'qualification': qualification,
            'qualification_receipt': base.file_pin(args.qualification), 'testing_notes': base.file_pin(args.testing_notes),
            'native_libraries_changed': False, 'native_game_or_mapserver_recompiled': False, 'native_dbserver_recompiled': True,
            'java_or_dex_recompiled': False, 'world_assets_changed': False, 'prepared_cache_archive_changed': False,
            'baseline_dbserver_archive_changed': False, 'graphics_driver_changed': False,
            'physical_gameplay_validated': False, 'physical_startup_timing_validated': False,
            'physical_storage_cleanup_validated': False, 'physical_fresh_profile_recovery_validated': False,
            'runtime_refresh_required': True, 'previous_runtime_generation_retained': True, 'asset_reimport_required': False,
            'scope': QUALIFICATION_SCOPE, **{name: donor[name] for name in RETAINED_RECEIPT_FIELDS}}
        (args.output.parent/REPORT_NAME).write_text(json.dumps(report, indent=2)+'\n')
        args.output.with_suffix('.apk.sha256').write_text(report['sha256']+'  '+APK_NAME+'\n')
        shutil.copyfile(args.testing_notes, args.output.parent/NOTES_NAME)
        print('Built source-bound startup candidate', report['sha256'])


def verify_report(args, commit):
    base, current = builder(), builder(repaired=True)
    donor = validate_donor(args.donor_apk, args.donor_build_report)
    qualification = validate_qualification(read_json(args.qualification), commit)
    java = current_sources(donor); native = validate_native(args.native_directory, commit, args.donor_apk)
    report = read_json(args.build_report)
    require(report.get('format') == 1 and report.get('apk') == APK_NAME and report.get('repository_commit') == commit
        and report.get('runtime_repository_commit') == commit and report.get('retained_native_repository_commit') == RETAINED_NATIVE_COMMIT
        and report.get('application_id') == base.APP_ID and report.get('version_name') == VERSION_NAME and report.get('version_code') == VERSION_CODE
        and report.get('signer_certificate_sha256') == SIGNER and report.get('signing_key_created') is False
        and report.get('donor') == donor_link() and report.get('native_dbserver') == native and qualification.get('native_dbserver') == native
        and report.get('native_dbserver_manifest') == base.file_pin(args.native_directory/'startup-dbserver-manifest.json')
        and report.get('qualification') == qualification and report.get('qualification_receipt') == base.file_pin(args.qualification)
        and report.get('java_sources') == java and report.get('changed_java_sources') == [] and report.get('added_java_sources') == []
        and report.get('retained_dex') == donor['recompiled_dex'] and report.get('donor_dex') == donor['recompiled_dex']
        and report.get('preserved_sources') == {name: pin for name, pin in donor['preserved_sources'].items() if name not in {'android/guest/'+helper for helper in HELPERS}}
        and report.get('changed_apk_payloads') == sorted(REPLACED_PAYLOADS|ADDED_PAYLOADS)
        and report.get('replaced_apk_payloads') == sorted(REPLACED_PAYLOADS) and report.get('added_apk_payloads') == sorted(ADDED_PAYLOADS)
        and all(report.get(key) is True for key in ('signature_verified', 'package_badging_verified', 'binary_manifest_version_only_verified',
            'payload_bytes_verified', 'native_dbserver_recompiled', 'runtime_refresh_required', 'previous_runtime_generation_retained'))
        and all(report.get(key) is False for key in ('native_libraries_changed', 'native_game_or_mapserver_recompiled', 'java_or_dex_recompiled',
            'world_assets_changed', 'prepared_cache_archive_changed', 'baseline_dbserver_archive_changed', 'graphics_driver_changed',
            'physical_gameplay_validated', 'physical_startup_timing_validated', 'physical_storage_cleanup_validated',
            'physical_fresh_profile_recovery_validated', 'asset_reimport_required'))
        and all(report.get(name) == donor[name] for name in RETAINED_RECEIPT_FIELDS), 'Startup build receipt differs')
    base.checked_file(args.apk, report)
    verify_derivative(args.apk, donor, report['payloads'], commit, args.native_directory)
    with zipfile.ZipFile(args.apk) as archive:
        runtime = json.loads(archive.read('assets/runtime/runtime-manifest.json'))
    require(runtime == report.get('runtime_manifest') and report.get('runtime_manifest_sha256') == report['payloads']['assets/runtime/runtime-manifest.json']['sha256'],
            'Reported runtime verification metadata differs from APK')
    verify_binary_manifest(args.apk, args.donor_apk, args.build_tools)
    require(verify_apk_server_archives(args.apk) == donor['server_payload_extraction_preflight'], 'Published startup APK fails retained guest extraction')
    verify_signature(args.apk, args.build_tools); base.run(args.build_tools/'zipalign', '-c', '4', args.apk)
    current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', args.apk))
    checksum = args.apk.with_suffix('.apk.sha256')
    require(checksum.read_text() == report['sha256']+'  '+APK_NAME+'\n', 'Published checksum differs')
    public_notes = args.apk.parent/NOTES_NAME
    base.checked_file(public_notes, report['testing_notes']); base.checked_file(args.testing_notes, report['testing_notes'])
    return report, checksum, public_notes


def publish_release(api, report, assets, notes):
    require(tuple(path.name for path in assets) == (APK_NAME, APK_NAME+'.sha256', NOTES_NAME), 'Unexpected startup release assets')
    builder().checked_file(assets[0], report)
    for path in ('/releases/tags/'+RELEASE_TAG, '/git/ref/tags/'+RELEASE_TAG):
        try: existing = api.request(path)
        except urllib.error.HTTPError as error:
            if error.code != 404: raise
        else:
            require(not path.startswith('/releases/'), 'Existing startup release is never replaced')
            require(existing.get('object', {}).get('type') == 'commit' and existing['object'].get('sha') == report['repository_commit'], 'Existing tag points elsewhere')
    body = notes+'\n\nAPK SHA-256: `'+report['sha256']+'`.\n'
    body += '[Startup source and native build qualification](https://github.com/'+REPOSITORY+'/actions/runs/'+os.environ.get('GITHUB_RUN_ID', '')+').\n'
    release = api.request('/releases', {'tag_name': RELEASE_TAG, 'target_commitish': report['repository_commit'],
        'name': 'COH Atlas Gameplay 0.13.3 — Atlas-first startup scheduling', 'body': body,
        'draft': True, 'prerelease': True, 'generate_release_notes': False, 'make_latest': 'false'}, method='POST')
    require(type(release.get('id')) is int and release.get('draft') is True and release.get('prerelease') is True and release.get('tag_name') == RELEASE_TAG, 'Unexpected created startup release')
    for path in assets:
        uploaded = api.request('/releases/'+str(release['id'])+'/assets?'+urllib.parse.urlencode({'name': path.name}), path, method='POST', upload=True)
        expected = builder().file_pin(path)
        require(uploaded.get('state') == 'uploaded' and uploaded.get('name') == path.name and uploaded.get('size') == expected['bytes'] and uploaded.get('digest') == 'sha256:'+expected['sha256'], 'Startup release upload differs')
    published = api.request('/releases/'+str(release['id']), {'draft': False, 'prerelease': True, 'make_latest': 'false'}, method='PATCH')
    require(published.get('id') == release['id'] and published.get('draft') is False and published.get('prerelease') is True and published.get('tag_name') == RELEASE_TAG, 'Startup publication did not complete')
    return published.get('html_url')


def publish(args):
    require(os.environ.get('GITHUB_REPOSITORY') == REPOSITORY and os.environ.get('GITHUB_REF') == 'refs/heads/'+BRANCH
        and os.environ.get('GITHUB_EVENT_NAME') in ('push', 'workflow_dispatch'), 'Publication requires authorized continuation branch')
    commit = builder().source_commit(os.environ.get('GITHUB_SHA'))
    report, checksum, public_notes = verify_report(args, commit)
    api = module('startup_schedule_github', Path(__file__).with_name('build_atlas_gameplay_apk.py'))
    print('Published startup prerelease:', publish_release(api.GitHub(os.environ.get('GH_TOKEN')), report,
        (args.apk, checksum, public_notes), public_notes.read_text()))


def audit(args):
    report, _, _ = verify_report(args, builder().source_commit(args.repository_commit))
    print('Public APK independently verified:', report['sha256'], 'all baseline native archives and Android shell retained')


def main():
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest='command', required=True)
    get = commands.add_parser('download-donor'); get.add_argument('--output', type=Path, required=True)
    create = commands.add_parser('build')
    for name in ('donor-apk', 'donor-build-report', 'qualification', 'native-directory', 'android-jar', 'build-tools', 'keystore', 'output'):
        create.add_argument('--'+name, type=Path, required=True)
    create.add_argument('--repository-commit'); create.add_argument('--password-env', default='COH_INTERACTIVE_KEYSTORE_PASSWORD')
    create.add_argument('--testing-notes', type=Path, default=NOTES)
    for command in ('publish', 'audit-public'):
        sub = commands.add_parser(command)
        for name in ('apk', 'build-report', 'build-tools', 'qualification', 'native-directory', 'donor-build-report', 'donor-apk'):
            sub.add_argument('--'+name, type=Path, required=True)
        sub.add_argument('--testing-notes', type=Path, default=NOTES)
        if command == 'audit-public': sub.add_argument('--repository-commit', required=True)
    args = parser.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path): setattr(args, key, value.absolute())
    {'download-donor': download, 'build': build, 'publish': publish, 'audit-public': audit}[args.command](args)


if __name__ == '__main__': main()
