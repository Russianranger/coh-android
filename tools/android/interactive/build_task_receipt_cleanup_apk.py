#!/usr/bin/env python3
"""Build explicit startup-only same-profile reopening from public 0.13.3.

Only ClientRuntime/DEX, one reopen helper, its verification manifests and Android
version metadata change. All 64 other payloads and native provenance remain exact.
One setup publishes the new helper generation; assets/profile are retained.
"""
from __future__ import annotations
import argparse
import hashlib
import copy
import json
import os
import re
from pathlib import Path
import shutil
import stat
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

import build_responsiveness_apk as shared

ROOT = Path(__file__).resolve().parents[3]
REPOSITORY, BRANCH, SIGNER = shared.REPOSITORY, shared.BRANCH, shared.SIGNER
DONOR_COMMIT = 'dee916f80e9e336f374f31228535afdbe2c928ca'
RETAINED_NATIVE_COMMIT = '53c885896e9b4d838be0f36a1f09237f04c08a00'
DONOR_RUN_ID = 37167835800
DONOR_APK_NAME = 'COH-Atlas-Gameplay-0.13.3.apk'
DONOR_APK = {'bytes': 676108222, 'sha256': '2626dcabcc9d69bfd1b9ad723e9748746df77e93d565a0fb1740eeff4b516709'}
DONOR_BUILD = {'bytes': 1504652, 'sha256': 'e23644cd8d52dbd4a734c29fd3fd89364b2ff00024c6cb9a3a30721eea6df7f6'}
DONOR_URL = 'https://github.com/'+REPOSITORY+'/releases/download/coh-atlas-gameplay-v0.13.3/'+DONOR_APK_NAME
VERSION_NAME, VERSION_CODE = '0.13.4', 19
APK_NAME = 'COH-Atlas-Gameplay-0.13.4.apk'
REPORT_NAME = 'task-receipt-cleanup-apk-build-report.json'
NOTES_NAME = 'COH-Atlas-Gameplay-0.13.4-testing.txt'
NOTES = ROOT/'docs'/NOTES_NAME
RELEASE_TAG = 'coh-atlas-gameplay-v0.13.4'
JAVA_ROOT = shared.JAVA_ROOT
JAVA_CHANGES = frozenset({JAVA_ROOT+'ClientRuntime.java'})
JAVA_ADDITIONS = frozenset()
HELPERS = frozenset({'character_reopen_diagnostic.py'})
REPLACED_PAYLOADS = frozenset('assets/runtime/'+name for name in HELPERS|{'client-manifest.json', 'runtime-manifest.json'})
QUALIFICATION_SCOPE = 'startup_only_same_profile_reopen_and_prior_task_receipt_retirement'
CHECKS = ('previous_task_receipt_retirement_and_failure_guards_verified',
    'explicit_startup_only_reopen_and_historical_task_guards_verified',
    'ordinary_save_identity_and_prior_startup_guards_verified',
    'source_bound_retained_native_payloads_and_actual_archive_extraction_verified')
WORKFLOW = '.github/workflows/android-task-receipt-cleanup.yml'
QUALIFICATION_SCRIPT = 'tools/android/interactive/qualify_task_receipt_cleanup.py'
SOURCE_FILES = frozenset((WORKFLOW, QUALIFICATION_SCRIPT,
    'tools/android/interactive/build_task_receipt_cleanup_apk.py',
    'tools/android/interactive/test_task_receipt_cleanup_package.py',
    'tools/android/interactive/test_task_receipt_cleanup.py',
    'tools/android/interactive/build_storage_recovery_apk.py',
    'tools/android/interactive/build_startup_schedule_apk.py',
    'tools/android/interactive/qualify_startup_schedule.py',
    'tools/android/interactive/build_responsiveness_apk.py',
    'tools/android/interactive/build_apk.py',
    'tools/android/interactive/build_atlas_gameplay_apk.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    '.github/workflows/android-startup-schedule.yml',
    '.github/workflows/android-storage-recovery.yml',
    '.github/workflows/android-storage-cleanup.yml',
    '.github/workflows/android-task-gate.yml',
    '.github/workflows/android-client-interactive.yml',
    'android/interactive/src/main/AndroidManifest.xml',
    'android/guest/character_reopen_diagnostic.py',
    'docs/'+NOTES_NAME,
    'docs/android-evidence/startup-schedule-0.13.3-reopen-blocked.json', *JAVA_CHANGES))
require, module, read_json = shared.require, shared.module, shared.read_json
verify_server_archives, verify_apk_server_archives = shared.verify_server_archives, shared.verify_apk_server_archives
RETAINED_RECEIPT_FIELDS = ('runtime_timestamps', 'runtime_timestamps_receipt',
    'server_animation_manifest', 'server_cache_manifest', 'retained_server_cache_archive',
    'native_responsiveness', 'native_package_receipt', 'native_launcher', 'source_manifest',
    'retained_android_resources', 'server_payload_extraction_preflight',
    'native_dbserver', 'native_dbserver_manifest')


def builder(*, repaired=False):
    base = module('task_receipt_cleanup_android_builder', Path(__file__).with_name('build_apk.py'))
    if repaired: base.VERSION_NAME, base.VERSION_CODE, base.APK_NAME = VERSION_NAME, VERSION_CODE, APK_NAME
    return base


def donor_link():
    return {'run_id': DONOR_RUN_ID, 'repository_commit': DONOR_COMMIT, 'apk': DONOR_APK, 'build_report': DONOR_BUILD}


def validate_donor_receipt(path):
    base = builder(); base.checked_file(path, DONOR_BUILD)
    donor = read_json(path); qualification = donor.get('qualification', {})
    require(donor.get('format') == 1 and donor.get('repository_commit') == DONOR_COMMIT
        and donor.get('apk') == DONOR_APK_NAME and {key: donor.get(key) for key in DONOR_APK} == DONOR_APK
        and donor.get('application_id') == base.APP_ID and donor.get('version_name') == '0.13.3'
        and donor.get('version_code') == 18 and donor.get('abi') == 'arm64-v8a'
        and donor.get('signer_certificate_sha256') == SIGNER and donor.get('signing_key_created') is False
        and all(donor.get(key) is True for key in ('signature_verified', 'package_badging_verified',
            'binary_manifest_version_only_verified', 'payload_bytes_verified'))
        and len(donor.get('payloads', {})) == 67 and len(donor.get('java_sources', {})) == 18
        and donor.get('server_payload_extraction_preflight', {}).get('status') == 'passed'
        and qualification.get('scope') == 'source_bound_startup_schedule_world_reuse_and_guarded_manual_atlas_dbserver'
        and qualification.get('status') == 'passed' and qualification.get('tests_run') == 331
        and qualification.get('repository_commit') == DONOR_COMMIT
        and donor.get('runtime_repository_commit') == DONOR_COMMIT
        and donor.get('retained_native_repository_commit') == RETAINED_NATIVE_COMMIT
        and donor.get('runtime_manifest', {}).get('repository_commit') == DONOR_COMMIT
        and donor['runtime_manifest'].get('task_gate_required') is True
        and donor.get('native_dbserver', {}).get('repository_commit') == DONOR_COMMIT
        and donor.get('server_animation_manifest', {}).get('repository_commit') == RETAINED_NATIVE_COMMIT,
        'Exact public 0.13.3 retained-signer donor receipt differs')
    return donor

def archive_inventory(archive):
    entries = archive.infolist()
    names = [entry.filename for entry in entries]
    require(len(names) == len(set(names)), 'Duplicate APK member')
    require(all(not stat.S_ISLNK(entry.external_attr >> 16) for entry in entries), 'APK symlink member')
    return {name for name in names if not name.startswith('META-INF/')}


def validate_donor(apk, receipt):
    base = builder(); base.checked_file(apk, DONOR_APK)
    donor = validate_donor_receipt(receipt)
    base.verify_packaged_payloads(apk, donor['payloads'])
    with zipfile.ZipFile(apk) as archive:
        retained = {'classes.dex': donor['retained_dex'], **donor['retained_android_resources']}
        require(archive_inventory(archive) == set(donor['payloads'])|set(retained)|{'AndroidManifest.xml'},
                'Unexpected donor APK inventory')
        for name, expected in retained.items():
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


def current_java_sources(donor, generated):
    base = builder(); sources = base.java_sources(ROOT/'android/interactive/src/main', generated)
    pins = {path.relative_to(ROOT).as_posix(): base.file_pin(path) for path in sources
        if path.is_relative_to(ROOT) and not path.is_relative_to(generated)}
    require(len(pins) == 18 and set(pins) == set(donor['java_sources']) and not JAVA_ADDITIONS,
            'Startup continuation must retain all 18 authored Java sources')
    changed = {name for name in pins if pins[name] != donor['java_sources'][name]}
    require(changed == JAVA_CHANGES, 'Startup continuation changes only ClientRuntime.java')
    for name, expected in donor['preserved_sources'].items(): base.checked_file(ROOT/name, expected)
    base.checked_file(ROOT/'android/interactive/src/main/AndroidManifest.xml', donor['source_manifest'])
    for name, expected in donor['payloads'].items():
        if name.startswith('assets/runtime/') and (name.endswith('.py') or name.endswith('/task-gate.json')):
            if Path(name).name not in HELPERS: base.checked_file(ROOT/'android/guest'/Path(name).name, expected)
    require(base.file_pin(ROOT/'android/guest/character_reopen_diagnostic.py') !=
        donor['payloads']['assets/runtime/character_reopen_diagnostic.py'], 'Explicit startup-only reopen helper change required')
    return sources, pins, sorted(changed)

def validate_qualification(receipt, commit):
    require(receipt.get('format') == 1 and receipt.get('status') == 'passed'
        and receipt.get('scope') == QUALIFICATION_SCOPE and receipt.get('repository_commit') == commit
        and receipt.get('retained_runtime_repository_commit') == DONOR_COMMIT
        and receipt.get('retained_native_repository_commit') == RETAINED_NATIVE_COMMIT
        and receipt.get('donor_apk_sha256') == DONOR_APK['sha256']
        and all(receipt.get(key) is False for key in ('physical_gameplay_validated', 'physical_startup_timing_validated',
            'physical_storage_cleanup_validated', 'physical_fresh_profile_recovery_validated',
            'native_runtime_booted', 'native_client_or_server_recompiled', 'long_prior_gameplay_milestones_repeated'))
        and receipt.get('runtime_refresh_required') is True and receipt.get('previous_runtime_generation_retained') is True
        and receipt.get('asset_reimport_required') is False
        and type(receipt.get('tests_run')) is int and receipt['tests_run'] > 0
        and set(receipt.get('checks', {})) == set(CHECKS) and all(value is True for value in receipt['checks'].values()),
        'Exact focused startup continuation qualification required')
    require(SOURCE_FILES <= set(receipt.get('source_files', {})), 'Qualification source closure incomplete')
    contract = module('task_receipt_cleanup_qualification_contract', ROOT/QUALIFICATION_SCRIPT)
    suites = receipt.get('test_suites', {}); check_suites = receipt.get('check_suites', {})
    require(set(suites) == set(contract.TEST_MODULES) and check_suites == contract.CHECK_SUITES,
            'Qualification must retain the exact focused suite contract')
    require(all(item.get('status') == 'passed' and item.get('skipped') == 0
        and type(item.get('tests_run')) is int and item['tests_run'] > 0 for item in suites.values())
        and receipt['tests_run'] == sum(item['tests_run'] for item in suites.values()), 'Qualification suite evidence differs')
    for name, expected in receipt['source_files'].items():
        require(isinstance(name, str) and not Path(name).is_absolute() and '..' not in Path(name).parts
                and chr(92) not in name, 'Unsafe qualification source path')
        builder().checked_file(ROOT/name, expected)
    return receipt

def repaired_manifests(donor, client, helper_pin, commit):
    client = copy.deepcopy(client); client['files']['character_reopen_diagnostic.py'] = helper_pin
    runtime = copy.deepcopy(donor['runtime_manifest'])
    runtime['files']['character_reopen_diagnostic.py'] = helper_pin
    encoded = shared.encoded(client)
    runtime['files']['client-manifest.json'] = {'bytes': len(encoded), 'sha256': hashlib.sha256(encoded).hexdigest()}
    runtime['repository_commit'] = commit
    runtime['startup_only_reopen'] = True
    runtime['scope'] = 'Explicit same-profile startup timing without repeating the accepted task; prior native runtime, assets, caches and ordinary-save proof retained'
    return client, runtime


def extract_retained(apk, donor, destination, commit):
    base = builder(); destination.mkdir(parents=True); retained = {}
    with zipfile.ZipFile(apk) as archive:
        require(archive_inventory(archive) == set(donor['payloads'])|set(donor['retained_android_resources'])|
                {'AndroidManifest.xml', 'classes.dex'}, 'Unexpected donor APK inventory')
        for entry in archive.infolist():
            name = entry.filename
            if name == 'AndroidManifest.xml' or name.startswith('META-INF/'): continue
            target = destination/name; target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open('xb') as output: shutil.copyfileobj(source, output, 64*1024)
            retained[name] = base.file_pin(target)
    require({name: retained[name] for name in donor['payloads']} == donor['payloads'], 'Extracted donor payload bytes differ')
    assets = destination/'assets/runtime'
    require(read_json(assets/'runtime-manifest.json') == donor['runtime_manifest'], 'Donor runtime history differs')
    source = ROOT/'android/guest/character_reopen_diagnostic.py'; base.checked_file(source)
    require(0 < source.stat().st_size <= 1024*1024, 'Unbounded startup reopen helper')
    shutil.copyfile(source, assets/source.name)
    client, runtime = repaired_manifests(donor, read_json(assets/'client-manifest.json'), base.file_pin(source), commit)
    (assets/'client-manifest.json').write_bytes(shared.encoded(client))
    (assets/'runtime-manifest.json').write_bytes(shared.encoded(runtime))
    payloads = {name: base.file_pin(destination/name) for name in donor['payloads']}
    require({name for name in payloads if payloads[name] != donor['payloads'][name]} == REPLACED_PAYLOADS,
            'Only the reopen helper and two verification manifests may change')
    preflight = verify_server_archives(assets)
    require(preflight == donor['server_payload_extraction_preflight'], 'Retained native archive extraction differs')
    return runtime, payloads, retained, preflight

def repair_android_manifest(source, destination):
    base = builder(); base.verify_source_manifest(source)
    tree = ET.parse(source); manifest = tree.getroot()
    manifest.set(base.ANDROID+'versionName', VERSION_NAME); manifest.set(base.ANDROID+'versionCode', str(VERSION_CODE))
    ET.register_namespace('android', base.ANDROID[1:-1]); tree.write(destination, encoding='utf-8', xml_declaration=True)
    builder(repaired=True).verify_source_manifest(destination)


def verify_derivative(apk, donor, payloads, dex_pin, commit):
    require(set(payloads) == set(donor['payloads'])
        and {name for name in payloads if payloads[name] != donor['payloads'][name]} == REPLACED_PAYLOADS,
        'Startup continuation changed unauthorized runtime payloads')
    require(dex_pin != donor['retained_dex'], 'Startup continuation must recompile the corrected Android wrapper')
    base = builder(); base.verify_packaged_payloads(apk, payloads)
    with zipfile.ZipFile(apk) as archive:
        require(archive_inventory(archive) == set(payloads)|set(donor['retained_android_resources'])|
                {'AndroidManifest.xml', 'classes.dex'}, 'Unexpected candidate APK member')
        for name, expected in {'classes.dex': dex_pin, **donor['retained_android_resources']}.items():
            raw = archive.read(name)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == expected,
                    'Retained Android resources or corrected DEX differ')
        helper = base.file_pin(ROOT/'android/guest/character_reopen_diagnostic.py')
        require(payloads['assets/runtime/character_reopen_diagnostic.py'] == helper, 'Qualified reopen helper differs')
        client = json.loads(archive.read('assets/runtime/client-manifest.json'))
        original = copy.deepcopy(client)
        original['files']['character_reopen_diagnostic.py'] = donor['payloads']['assets/runtime/character_reopen_diagnostic.py']
        raw = shared.encoded(original)
        require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == donor['payloads']['assets/runtime/client-manifest.json'],
                'Client manifest changed beyond the one helper pin')
        expected_client, expected_runtime = repaired_manifests(donor, original, helper, commit)
        require(client == expected_client and json.loads(archive.read('assets/runtime/runtime-manifest.json')) == expected_runtime,
                'Startup-only runtime verification metadata differs')
        require(json.loads(archive.read('assets/runtime/native-responsiveness.json')) == donor['native_responsiveness']
            and json.loads(archive.read('assets/runtime/server-animation-manifest.json')) == donor['server_animation_manifest']
            and json.loads(archive.read('assets/runtime/startup-dbserver-manifest.json')) == donor['native_dbserver'],
            'Startup continuation relabelled retained native history')

def verify_signature(apk, build_tools):
    output = builder().run('java', '-jar', build_tools/'lib/apksigner.jar', 'verify', '--verbose', '--print-certs', apk)
    require('Verified using v2 scheme (APK Signature Scheme v2): true' in output
        and 'Verified using v3 scheme (APK Signature Scheme v3): true' in output,
        'Official APK v2 and v3 signature verification is required')
    return builder().verify_signer_output(output, SIGNER)


def verify_binary_manifest(candidate, donor_apk, build_tools):
    """Compare decoded actual AXML, allowing only the two version values."""
    normalized = []
    for apk in (donor_apk, candidate):
        output = builder().run(build_tools/'aapt2', 'dump', 'xmltree', apk, '--file', 'AndroidManifest.xml')
        require(len(output.encode()) <= 262144, 'Unbounded binary Android manifest')
        lines = output.splitlines()
        require(sum(':versionCode(' in line for line in lines) == 1
            and sum(':versionName(' in line for line in lines) == 1,
            'Binary Android manifest version metadata is missing or duplicated')
        result = []
        for line in lines:
            line = re.sub(r' \(line=\d+\)', '', line)
            if ':versionCode(' in line: line = line.split('=')[0]+'=VERSION_CODE'
            if ':versionName(' in line: line = line.split('=')[0]+'=VERSION_NAME'
            result.append(line)
        normalized.append(result)
    require(normalized[0] == normalized[1], 'Binary Android manifest changed beyond version metadata')


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
    password = base.signing_password_spec(args.password_env)
    base.verify_signing_identity(args.keystore, 'coh-client-interactive', SIGNER, password)
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), 'Fresh task-receipt-cleanup APK required')
    base.checked_file(args.testing_notes); require(0 < args.testing_notes.stat().st_size <= 65536, 'Bounded testing notes required')
    for tool in (args.android_jar, args.build_tools/'aapt2', args.build_tools/'zipalign', args.build_tools/'lib/d8.jar', args.build_tools/'lib/apksigner.jar'):
        require(tool.is_file() and not tool.is_symlink(), 'Required Android tool missing')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-startup-reopen-', dir=args.output.parent) as temporary:
        work = Path(temporary)
        runtime, payloads, retained, preflight = extract_retained(args.donor_apk, donor, work/'donor', commit)
        classes, generated, dex = (work/name for name in ('classes', 'generated', 'dex'))
        for folder in (classes, generated, dex): folder.mkdir()
        current_java_sources(donor, generated)
        manifest = work/'AndroidManifest.xml'; repair_android_manifest(ROOT/'android/interactive/src/main/AndroidManifest.xml', manifest)
        resources, unsigned, aligned, signed = (work/name for name in ('resources.zip', 'unsigned.apk', 'aligned.apk', 'signed.apk'))
        base.run(args.build_tools/'aapt2', 'compile', '--dir', ROOT/'android/interactive/src/main/res', '-o', resources)
        base.run(args.build_tools/'aapt2', 'link', '-I', args.android_jar, '--manifest', manifest, '--min-sdk-version', '26', '--target-sdk-version', '35', '--java', generated, resources, '-o', unsigned)
        with zipfile.ZipFile(unsigned) as archive:
            require(archive_inventory(archive) == {'AndroidManifest.xml', 'resources.arsc', 'res/drawable/ic_coh_client.xml'}, 'Generated Android resource inventory differs')
            for name in donor['retained_android_resources']:
                raw = archive.read(name)
                require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == retained[name], 'Android resources changed beyond version metadata')
        require({path.relative_to(generated).as_posix() for path in generated.rglob('*.java')} == {base.APP_ID.replace('.', '/')+'/R.java'}, 'Unexpected generated Java source')
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
        certificate = verify_signature(signed, args.build_tools)
        base.run(args.build_tools/'zipalign', '-c', '4', signed)
        current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', signed))
        verify_derivative(signed, donor, payloads, dex_pin, commit)
        verify_binary_manifest(signed, args.donor_apk, args.build_tools)
        require(verify_apk_server_archives(signed) == preflight, 'Signed startup wrapper server extraction differs')
        shutil.copyfile(signed, args.output)
        report = {'format': 1, 'apk': APK_NAME, **base.file_pin(args.output), 'repository_commit': commit,
            'runtime_repository_commit': commit, 'retained_runtime_repository_commit': DONOR_COMMIT,
            'retained_native_repository_commit': RETAINED_NATIVE_COMMIT, 'application_id': base.APP_ID,
            'version_name': VERSION_NAME, 'version_code': VERSION_CODE, 'abi': 'arm64-v8a',
            'signer_certificate_sha256': certificate, 'signing_key_created': False, 'signature_verified': True,
            'package_badging_verified': True, 'binary_manifest_version_only_verified': True,
            'payload_bytes_verified': True, 'payloads': payloads,
            'changed_apk_payloads': sorted(REPLACED_PAYLOADS), 'replaced_apk_payloads': sorted(REPLACED_PAYLOADS), 'added_apk_payloads': [],
            'runtime_manifest': runtime, 'runtime_manifest_sha256': payloads['assets/runtime/runtime-manifest.json']['sha256'],
            'recompiled_dex': dex_pin, 'donor_dex': donor['retained_dex'], 'donor': donor_link(),
            'java_sources': source_pins, 'changed_java_sources': changed_java,
            'added_java_sources': sorted(JAVA_ADDITIONS),
            'preserved_sources': {name: pin for name, pin in donor['preserved_sources'].items() if name not in JAVA_CHANGES},
            'generated_manifest': base.file_pin(manifest), 'qualification': qualification,
            'qualification_receipt': base.file_pin(args.qualification), 'testing_notes': base.file_pin(args.testing_notes),
            'native_libraries_changed': False, 'client_or_server_recompiled': False, 'java_or_dex_recompiled': True,
            'world_assets_changed': False, 'prepared_cache_archive_changed': False, 'dbserver_changed': False,
            'graphics_driver_changed': False, 'physical_gameplay_validated': False,
            'physical_storage_cleanup_validated': False, 'physical_fresh_profile_recovery_validated': False, 'dialog_semantics_validated': False,
            'native_dbserver_recompiled': False, 'native_game_or_mapserver_recompiled': False,
            'physical_startup_timing_validated': False, 'startup_only_reopen': True,
            'runtime_refresh_required': True, 'previous_runtime_generation_retained': True, 'asset_reimport_required': False,
            'scope': QUALIFICATION_SCOPE,
            **{name: donor[name] for name in RETAINED_RECEIPT_FIELDS}}
        (args.output.parent/REPORT_NAME).write_text(json.dumps(report, indent=2)+'\n')
        args.output.with_suffix('.apk.sha256').write_text(report['sha256']+'  '+APK_NAME+'\n')
        shutil.copyfile(args.testing_notes, args.output.parent/NOTES_NAME)
        print('Built startup-only same-profile candidate', report['sha256'])


def publish_release(api, report, assets, notes):
    require(tuple(path.name for path in assets) == (APK_NAME, APK_NAME+'.sha256', NOTES_NAME), 'Unexpected startup-only release assets')
    builder().checked_file(assets[0], report)
    for path in ('/releases/tags/'+RELEASE_TAG, '/git/ref/tags/'+RELEASE_TAG):
        try: existing = api.request(path)
        except urllib.error.HTTPError as error:
            if error.code != 404: raise
        else:
            require(not path.startswith('/releases/'), 'Existing startup-only release is never replaced')
            require(existing.get('object', {}).get('type') == 'commit' and existing['object'].get('sha') == report['repository_commit'], 'Existing tag points elsewhere')
    body = notes+'\n\nAPK SHA-256: `'+report['sha256']+'`.\n'
    body += '[Startup-only and retained-native host qualification](https://github.com/'+REPOSITORY+'/actions/runs/'+os.environ.get('GITHUB_RUN_ID', '')+').\n'
    release = api.request('/releases', {'tag_name': RELEASE_TAG, 'target_commitish': report['repository_commit'],
        'name': 'COH Atlas Gameplay 0.13.4 — same-profile startup timing', 'body': body,
        'draft': True, 'prerelease': True, 'generate_release_notes': False, 'make_latest': 'false'}, method='POST')
    require(type(release.get('id')) is int and release.get('draft') is True and release.get('prerelease') is True and release.get('tag_name') == RELEASE_TAG, 'Unexpected created startup-only release')
    for path in assets:
        uploaded = api.request('/releases/'+str(release['id'])+'/assets?'+urllib.parse.urlencode({'name': path.name}), path, method='POST', upload=True)
        expected = builder().file_pin(path)
        require(uploaded.get('state') == 'uploaded' and uploaded.get('name') == path.name and uploaded.get('size') == expected['bytes'] and uploaded.get('digest') == 'sha256:'+expected['sha256'], 'Startup-only release upload differs')
    published = api.request('/releases/'+str(release['id']), {'draft': False, 'prerelease': True, 'make_latest': 'false'}, method='PATCH')
    require(published.get('id') == release['id'] and published.get('draft') is False and published.get('prerelease') is True and published.get('tag_name') == RELEASE_TAG, 'Startup-only publication did not complete')
    return published.get('html_url')


def verify_report(args, commit):
    base, current = builder(), builder(repaired=True)
    donor = validate_donor(args.donor_apk, args.donor_build_report)
    qualification = validate_qualification(read_json(args.qualification), commit)
    report = read_json(args.build_report)
    with tempfile.TemporaryDirectory(prefix='coh-startup-reopen-source-') as temporary:
        _, sources, changes = current_java_sources(donor, Path(temporary))
    require(report.get('format') == 1 and report.get('apk') == APK_NAME and report.get('repository_commit') == commit
        and report.get('runtime_repository_commit') == commit
        and report.get('retained_runtime_repository_commit') == DONOR_COMMIT
        and report.get('retained_native_repository_commit') == RETAINED_NATIVE_COMMIT
        and report.get('application_id') == base.APP_ID and report.get('version_name') == VERSION_NAME
        and report.get('version_code') == VERSION_CODE and report.get('signer_certificate_sha256') == SIGNER
        and report.get('signing_key_created') is False and report.get('donor') == donor_link()
        and report.get('qualification') == qualification and report.get('qualification_receipt') == base.file_pin(args.qualification)
        and report.get('java_sources') == sources and report.get('changed_java_sources') == changes
        and report.get('added_java_sources') == sorted(JAVA_ADDITIONS)
        and report.get('donor_dex') == donor['retained_dex'] and report.get('preserved_sources') == {name: pin for name, pin in donor['preserved_sources'].items() if name not in JAVA_CHANGES}
        and report.get('changed_apk_payloads') == sorted(REPLACED_PAYLOADS) and report.get('added_apk_payloads') == []
        and report.get('replaced_apk_payloads') == sorted(REPLACED_PAYLOADS)
        and all(report.get(key) is True for key in ('signature_verified', 'package_badging_verified', 'binary_manifest_version_only_verified',
            'payload_bytes_verified', 'java_or_dex_recompiled', 'runtime_refresh_required', 'previous_runtime_generation_retained', 'startup_only_reopen'))
        and all(report.get(key) is False for key in ('native_libraries_changed', 'client_or_server_recompiled',
            'native_dbserver_recompiled', 'native_game_or_mapserver_recompiled', 'world_assets_changed',
            'prepared_cache_archive_changed', 'dbserver_changed', 'graphics_driver_changed', 'physical_gameplay_validated',
            'physical_startup_timing_validated', 'physical_storage_cleanup_validated', 'physical_fresh_profile_recovery_validated',
            'dialog_semantics_validated', 'asset_reimport_required'))
        and all(report.get(name) == donor[name] for name in RETAINED_RECEIPT_FIELDS), 'Startup continuation build receipt differs')
    base.checked_file(args.apk, report); verify_derivative(args.apk, donor, report['payloads'], report['recompiled_dex'], commit)
    with zipfile.ZipFile(args.apk) as archive:
        runtime = json.loads(archive.read('assets/runtime/runtime-manifest.json'))
    require(runtime == report.get('runtime_manifest') and report.get('runtime_manifest_sha256') ==
        report['payloads']['assets/runtime/runtime-manifest.json']['sha256'], 'Reported runtime manifest differs from APK')
    verify_binary_manifest(args.apk, args.donor_apk, args.build_tools)
    require(verify_apk_server_archives(args.apk) == report['server_payload_extraction_preflight'], 'Published startup wrapper fails actual guest extraction')
    verify_signature(args.apk, args.build_tools)
    base.run(args.build_tools/'zipalign', '-c', '4', args.apk)
    current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', args.apk))
    checksum = args.apk.with_suffix('.apk.sha256')
    require(checksum.read_text() == report['sha256']+'  '+APK_NAME+'\n', 'Published checksum differs')
    public_notes = args.apk.parent/NOTES_NAME
    base.checked_file(public_notes, report['testing_notes']); base.checked_file(args.testing_notes, report['testing_notes'])
    return report, checksum, public_notes


def publish(args):
    require(os.environ.get('GITHUB_REPOSITORY') == REPOSITORY and os.environ.get('GITHUB_REF') == 'refs/heads/'+BRANCH
        and os.environ.get('GITHUB_EVENT_NAME') in ('push', 'workflow_dispatch'), 'Publication requires authorized continuation branch')
    commit = builder().source_commit(os.environ.get('GITHUB_SHA'))
    report, checksum, public_notes = verify_report(args, commit)
    api = module('task_receipt_cleanup_github', Path(__file__).with_name('build_atlas_gameplay_apk.py'))
    print('Published startup-only prerelease:', publish_release(api.GitHub(os.environ.get('GH_TOKEN')), report,
        (args.apk, checksum, public_notes), public_notes.read_text()))


def audit(args):
    commit = builder().source_commit(args.repository_commit)
    report, _, _ = verify_report(args, commit)
    print('Public APK independently verified:', report['sha256'], '64 retained payloads; all native bytes retained')


def main():
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest='command', required=True)
    get = commands.add_parser('download-donor'); get.add_argument('--output', type=Path, required=True)
    create = commands.add_parser('build')
    for name in ('donor-apk', 'donor-build-report', 'qualification', 'android-jar', 'build-tools', 'keystore', 'output'):
        create.add_argument('--'+name, type=Path, required=True)
    create.add_argument('--repository-commit'); create.add_argument('--password-env', default='COH_INTERACTIVE_KEYSTORE_PASSWORD')
    create.add_argument('--testing-notes', type=Path, default=NOTES)
    for command in ('publish', 'audit-public'):
        sub = commands.add_parser(command)
        for name in ('apk', 'build-report', 'build-tools', 'qualification', 'donor-build-report', 'donor-apk'):
            sub.add_argument('--'+name, type=Path, required=True)
        sub.add_argument('--testing-notes', type=Path, default=NOTES)
        if command == 'audit-public': sub.add_argument('--repository-commit', required=True)
    args = parser.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path): setattr(args, key, value.absolute())
    {'download-donor': download, 'build': build, 'publish': publish, 'audit-public': audit}[args.command](args)


if __name__ == '__main__': main()
