#!/usr/bin/env python3
"""Build the Android recovery shell from immutable public 0.13.1.

All 65 guest/native/runtime payloads, manifests, assets and prepared caches are
retained byte for byte. Existing native qualification is inherited by identity;
this wrapper update does not rebuild or refresh the runtime.
"""
from __future__ import annotations
import argparse
import hashlib
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
DONOR_COMMIT = '5252595717a1965a76251d4110725185bbcbbe20'
RUNTIME_COMMIT = '53c885896e9b4d838be0f36a1f09237f04c08a00'
DONOR_RUN_ID = 37129906760
DONOR_APK_NAME = 'COH-Atlas-Gameplay-0.13.1.apk'
DONOR_APK = {'bytes': 675288850, 'sha256': '7652106de29838389b012aee802ccb784c6fc956dffe66d566773e1eb40bd9d3'}
DONOR_BUILD = {'bytes': 1458675, 'sha256': '0a9a2b26c97ab27d9eb512a6c18020d7d8a2c2d167b0b4e982f2ba5621a40d77'}
DONOR_URL = 'https://github.com/'+REPOSITORY+'/releases/download/coh-atlas-gameplay-v0.13.1/'+DONOR_APK_NAME
VERSION_NAME, VERSION_CODE = '0.13.2', 17
APK_NAME = 'COH-Atlas-Gameplay-0.13.2.apk'
REPORT_NAME = 'storage-recovery-apk-build-report.json'
NOTES_NAME = 'COH-Atlas-Gameplay-0.13.2-testing.txt'
NOTES = ROOT/'docs'/NOTES_NAME
RELEASE_TAG = 'coh-atlas-gameplay-v0.13.2'
JAVA_ROOT = shared.JAVA_ROOT
JAVA_CHANGES = frozenset({*(JAVA_ROOT+name+'.java' for name in ('ClientRuntime', 'ClientActivity', 'ClientService', 'StorageAudit', 'StorageFiles')),
    'android/app/src/main/java/io/github/russianranger/cohdiagnostic/DiagnosticRuntime.java'})
JAVA_ADDITIONS = frozenset()
QUALIFICATION_SCOPE = 'bounded_storage_recovery_fresh_profile_and_retained_0130_runtime'
CHECKS = ('bounded_streaming_storage_and_protected_paths_verified',
    'explicit_fresh_character_creation_recovery_verified',
    'same_runtime_setup_reuse_and_growth_diagnostics_verified',
    'owned_cleanup_identity_and_failure_guards_verified',
    'storage_ui_idle_session_and_export_guards_verified',
    'retained_task_input_save_and_cache_guards_verified',
    'all_runtime_payloads_and_actual_archive_extraction_verified')
WORKFLOW = '.github/workflows/android-storage-recovery.yml'
QUALIFICATION_SCRIPT = 'tools/android/interactive/qualify_storage_recovery.py'
SOURCE_FILES = frozenset((WORKFLOW, QUALIFICATION_SCRIPT,
    '.github/workflows/android-storage-cleanup.yml',
    'tools/android/interactive/build_storage_recovery_apk.py',
    'tools/android/interactive/test_storage_recovery_package.py',
    'tools/android/interactive/test_storage_audit.py',
    'tools/android/interactive/build_storage_cleanup_apk.py',
    'tools/android/interactive/qualify_storage_cleanup.py',
    'tools/android/interactive/test_storage_cleanup_package.py',
    'tools/android/interactive/test_fresh_profile_recovery.py',
    'tools/android/interactive/test_runtime_setup_reuse.py',
    'tools/android/interactive/test_storage_recovery_ui.py',
    'tools/android/interactive/test_storage_ui.py',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/qualify_task_gate.py',
    'tools/android/interactive/build_task_gate_apk.py',
    'tools/android/interactive/build_responsiveness_apk.py',
    'tools/android/interactive/build_apk.py',
    'tools/android/interactive/build_atlas_gameplay_apk.py',
    '.github/workflows/android-task-gate.yml',
    'tools/android/interactive/classify_interactive_change.py',
    'android/interactive/src/main/AndroidManifest.xml',
    'docs/'+NOTES_NAME, *JAVA_CHANGES, *JAVA_ADDITIONS))
require, module, read_json = shared.require, shared.module, shared.read_json
verify_server_archives, verify_apk_server_archives = shared.verify_server_archives, shared.verify_apk_server_archives
RETAINED_RECEIPT_FIELDS = ('runtime_manifest', 'runtime_manifest_sha256', 'runtime_timestamps',
    'runtime_timestamps_receipt', 'server_animation_manifest', 'server_cache_manifest',
    'retained_server_cache_archive', 'native_responsiveness', 'native_package_receipt',
    'native_launcher', 'source_manifest', 'retained_android_resources',
    'server_payload_extraction_preflight')


def builder(*, repaired=False):
    base = module('storage_recovery_android_builder', Path(__file__).with_name('build_apk.py'))
    if repaired: base.VERSION_NAME, base.VERSION_CODE, base.APK_NAME = VERSION_NAME, VERSION_CODE, APK_NAME
    return base


def donor_link():
    return {'run_id': DONOR_RUN_ID, 'repository_commit': DONOR_COMMIT, 'apk': DONOR_APK, 'build_report': DONOR_BUILD}


def validate_donor_receipt(path):
    builder().checked_file(path, DONOR_BUILD)
    donor = read_json(path)
    qualification = donor.get('qualification', {})
    require(donor.get('format') == 1 and donor.get('repository_commit') == DONOR_COMMIT
        and donor.get('apk') == DONOR_APK_NAME and {key: donor.get(key) for key in DONOR_APK} == DONOR_APK
        and donor.get('application_id') == builder().APP_ID and donor.get('version_name') == '0.13.1'
        and donor.get('version_code') == 16 and donor.get('abi') == 'arm64-v8a'
        and donor.get('signer_certificate_sha256') == SIGNER and donor.get('signing_key_created') is False
        and all(donor.get(key) is True for key in ('signature_verified', 'package_badging_verified', 'payload_bytes_verified'))
        and len(donor.get('payloads', {})) == 65 and len(donor.get('java_sources', {})) == 18
        and donor.get('server_payload_extraction_preflight', {}).get('status') == 'passed'
        and qualification.get('scope') == 'android_storage_inventory_owned_cleanup_and_retained_0130_runtime'
        and qualification.get('status') == 'passed' and qualification.get('tests_run') == 384
        and qualification.get('repository_commit') == DONOR_COMMIT
        and donor.get('runtime_repository_commit') == RUNTIME_COMMIT
        and donor.get('runtime_manifest', {}).get('repository_commit') == RUNTIME_COMMIT
        and donor['runtime_manifest'].get('task_gate_required') is True
        and donor.get('server_animation_manifest', {}).get('repository_commit') == RUNTIME_COMMIT,
        'Exact public 0.13.1 retained-signer donor receipt differs')
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
        retained = {'classes.dex': donor['recompiled_dex'], **donor['retained_android_resources']}
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
    previous = donor['java_sources']
    require(len(pins) == 18 and set(pins) == set(previous) and not JAVA_ADDITIONS,
            'Recovery update must keep all 18 authored Java sources')
    changed = {name for name in previous if pins[name] != previous[name]}
    require(changed == JAVA_CHANGES, 'Java changes exceed the six recovery sources')
    for name, expected in donor['preserved_sources'].items():
        if name not in JAVA_CHANGES: base.checked_file(ROOT/name, expected)
    base.checked_file(ROOT/'android/interactive/src/main/AndroidManifest.xml', donor['source_manifest'])
    for name, expected in donor['payloads'].items():
        if name.startswith('assets/runtime/') and (name.endswith('.py') or name == 'assets/runtime/task-gate.json'):
            base.checked_file(ROOT/'android/guest'/Path(name).name, expected)
    return sources, pins, sorted(changed)


def validate_qualification(receipt, commit):
    require(receipt.get('format') == 1 and receipt.get('status') == 'passed'
        and receipt.get('scope') == QUALIFICATION_SCOPE and receipt.get('repository_commit') == commit
        and receipt.get('runtime_repository_commit') == RUNTIME_COMMIT
        and receipt.get('donor_apk_sha256') == DONOR_APK['sha256']
        and receipt.get('physical_gameplay_validated') is False and receipt.get('native_runtime_booted') is False
        and receipt.get('physical_storage_cleanup_validated') is False
        and receipt.get('physical_fresh_profile_recovery_validated') is False
        and receipt.get('native_client_or_server_recompiled') is False
        and receipt.get('physical_startup_timing_validated') is False
        and receipt.get('long_prior_gameplay_milestones_repeated') is False
        and type(receipt.get('tests_run')) is int and receipt['tests_run'] >= 489
        and set(receipt.get('checks', {})) == set(CHECKS) and all(value is True for value in receipt['checks'].values()),
        'Exact focused storage-recovery qualification is required')
    require(SOURCE_FILES <= set(receipt.get('source_files', {})), 'Qualification source closure incomplete')
    for name, expected in receipt['source_files'].items():
        require(isinstance(name, str) and not Path(name).is_absolute() and '..' not in Path(name).parts
                and '\\' not in name, 'Unsafe qualification source path')
        builder().checked_file(ROOT/name, expected)
    return receipt


def extract_retained(apk, donor, destination):
    base = builder(); destination.mkdir(parents=True)
    retained = {}
    with zipfile.ZipFile(apk) as archive:
        require(archive_inventory(archive) == set(donor['payloads'])|set(donor['retained_android_resources'])|
                {'AndroidManifest.xml', 'classes.dex'}, 'Unexpected donor APK inventory')
        for entry in archive.infolist():
            name = entry.filename
            if name == 'AndroidManifest.xml' or name.startswith('META-INF/'): continue
            target = destination/name; target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open('xb') as output:
                shutil.copyfileobj(source, output, 64*1024)
            retained[name] = base.file_pin(target)
    payloads = {name: retained[name] for name in donor['payloads']}
    require(payloads == donor['payloads'], 'Extracted runtime payload bytes differ')
    assets = destination/'assets/runtime'
    runtime = read_json(assets/'runtime-manifest.json')
    require(runtime == donor['runtime_manifest'] and runtime['repository_commit'] == RUNTIME_COMMIT,
            'Runtime provenance must remain the exact 0.13.0 source')
    preflight = verify_server_archives(assets)
    require(preflight == donor['server_payload_extraction_preflight'], 'Retained server extraction differs')
    return runtime, payloads, retained, preflight


def repair_android_manifest(source, destination):
    base = builder(); base.verify_source_manifest(source)
    tree = ET.parse(source); manifest = tree.getroot()
    manifest.set(base.ANDROID+'versionName', VERSION_NAME); manifest.set(base.ANDROID+'versionCode', str(VERSION_CODE))
    ET.register_namespace('android', base.ANDROID[1:-1]); tree.write(destination, encoding='utf-8', xml_declaration=True)
    builder(repaired=True).verify_source_manifest(destination)


def verify_derivative(apk, donor, payloads, dex_pin):
    require(payloads == donor['payloads'], 'Storage wrapper changed retained runtime payloads')
    require(dex_pin != donor['recompiled_dex'], 'Storage wrapper did not recompile Java')
    builder().verify_packaged_payloads(apk, payloads)
    with zipfile.ZipFile(apk) as archive:
        require(archive_inventory(archive) == set(payloads)|set(donor['retained_android_resources'])|
                {'AndroidManifest.xml', 'classes.dex'}, 'Unexpected candidate APK member')
        for name, expected in {'classes.dex': dex_pin, **donor['retained_android_resources']}.items():
            raw = archive.read(name)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == expected,
                    'Retained Android resources or recompiled DEX differ')
        require(json.loads(archive.read('assets/runtime/runtime-manifest.json')) == donor['runtime_manifest']
            and json.loads(archive.read('assets/runtime/native-responsiveness.json')) == donor['native_responsiveness']
            and json.loads(archive.read('assets/runtime/server-animation-manifest.json')) == donor['server_animation_manifest'],
            'Storage derivative relabelled retained native or runtime history')


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
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), 'Fresh storage-recovery APK required')
    base.checked_file(args.testing_notes); require(0 < args.testing_notes.stat().st_size <= 65536, 'Bounded testing notes required')
    for tool in (args.android_jar, args.build_tools/'aapt2', args.build_tools/'zipalign', args.build_tools/'lib/d8.jar', args.build_tools/'lib/apksigner.jar'):
        require(tool.is_file() and not tool.is_symlink(), 'Required Android tool missing')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-storage-', dir=args.output.parent) as temporary:
        work = Path(temporary)
        runtime, payloads, retained, preflight = extract_retained(args.donor_apk, donor, work/'donor')
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
        verify_derivative(signed, donor, payloads, dex_pin)
        verify_binary_manifest(signed, args.donor_apk, args.build_tools)
        require(verify_apk_server_archives(signed) == preflight, 'Signed storage wrapper server extraction differs')
        shutil.copyfile(signed, args.output)
        report = {'format': 1, 'apk': APK_NAME, **base.file_pin(args.output), 'repository_commit': commit,
            'runtime_repository_commit': RUNTIME_COMMIT, 'application_id': base.APP_ID,
            'version_name': VERSION_NAME, 'version_code': VERSION_CODE, 'abi': 'arm64-v8a',
            'signer_certificate_sha256': certificate, 'signing_key_created': False, 'signature_verified': True,
            'package_badging_verified': True, 'binary_manifest_version_only_verified': True,
            'payload_bytes_verified': True, 'payloads': payloads,
            'changed_apk_payloads': [], 'replaced_apk_payloads': [], 'added_apk_payloads': [],
            'recompiled_dex': dex_pin, 'donor_dex': donor['recompiled_dex'], 'donor': donor_link(),
            'java_sources': source_pins, 'changed_java_sources': changed_java,
            'added_java_sources': sorted(JAVA_ADDITIONS),
            'preserved_sources': {name: pin for name, pin in donor['preserved_sources'].items() if name not in JAVA_CHANGES},
            'generated_manifest': base.file_pin(manifest), 'qualification': qualification,
            'qualification_receipt': base.file_pin(args.qualification), 'testing_notes': base.file_pin(args.testing_notes),
            'native_libraries_changed': False, 'client_or_server_recompiled': False, 'java_or_dex_recompiled': True,
            'world_assets_changed': False, 'prepared_cache_archive_changed': False, 'dbserver_changed': False,
            'graphics_driver_changed': False, 'physical_gameplay_validated': False,
            'physical_storage_cleanup_validated': False, 'physical_fresh_profile_recovery_validated': False, 'dialog_semantics_validated': False,
            'runtime_refresh_required': False, 'asset_reimport_required': False,
            'scope': 'Android bounded streaming storage audit, same-runtime setup reuse and explicit fresh-profile recovery; exact public 0.13.0 runtime and all 65 payloads retained; physical storage and fresh-profile recovery pending',
            **{name: donor[name] for name in RETAINED_RECEIPT_FIELDS}}
        (args.output.parent/REPORT_NAME).write_text(json.dumps(report, indent=2)+'\n')
        args.output.with_suffix('.apk.sha256').write_text(report['sha256']+'  '+APK_NAME+'\n')
        shutil.copyfile(args.testing_notes, args.output.parent/NOTES_NAME)
        print('Built retained-runtime storage candidate', report['sha256'])


def publish_release(api, report, assets, notes):
    require(tuple(path.name for path in assets) == (APK_NAME, APK_NAME+'.sha256', NOTES_NAME), 'Unexpected storage release assets')
    builder().checked_file(assets[0], report)
    for path in ('/releases/tags/'+RELEASE_TAG, '/git/ref/tags/'+RELEASE_TAG):
        try: existing = api.request(path)
        except urllib.error.HTTPError as error:
            if error.code != 404: raise
        else:
            require(not path.startswith('/releases/'), 'Existing storage release is never replaced')
            require(existing.get('object', {}).get('type') == 'commit' and existing['object'].get('sha') == report['repository_commit'], 'Existing tag points elsewhere')
    body = notes+'\n\nAPK SHA-256: `'+report['sha256']+'`.\n'
    body += '[Storage and retained-runtime host qualification](https://github.com/'+REPOSITORY+'/actions/runs/'+os.environ.get('GITHUB_RUN_ID', '')+').\n'
    release = api.request('/releases', {'tag_name': RELEASE_TAG, 'target_commitish': report['repository_commit'],
        'name': 'COH Atlas Gameplay 0.13.2 — storage and fresh-profile recovery', 'body': body,
        'draft': True, 'prerelease': True, 'generate_release_notes': False, 'make_latest': 'false'}, method='POST')
    require(type(release.get('id')) is int and release.get('draft') is True and release.get('prerelease') is True and release.get('tag_name') == RELEASE_TAG, 'Unexpected created storage release')
    for path in assets:
        uploaded = api.request('/releases/'+str(release['id'])+'/assets?'+urllib.parse.urlencode({'name': path.name}), path, method='POST', upload=True)
        expected = builder().file_pin(path)
        require(uploaded.get('state') == 'uploaded' and uploaded.get('name') == path.name and uploaded.get('size') == expected['bytes'] and uploaded.get('digest') == 'sha256:'+expected['sha256'], 'Storage release upload differs')
    published = api.request('/releases/'+str(release['id']), {'draft': False, 'prerelease': True, 'make_latest': 'false'}, method='PATCH')
    require(published.get('id') == release['id'] and published.get('draft') is False and published.get('prerelease') is True and published.get('tag_name') == RELEASE_TAG, 'Storage publication did not complete')
    return published.get('html_url')


def verify_report(args, commit):
    base, current = builder(), builder(repaired=True)
    donor = validate_donor(args.donor_apk, args.donor_build_report)
    qualification = validate_qualification(read_json(args.qualification), commit)
    report = read_json(args.build_report)
    with tempfile.TemporaryDirectory(prefix='coh-storage-source-') as temporary:
        _, sources, changes = current_java_sources(donor, Path(temporary))
    require(report.get('format') == 1 and report.get('apk') == APK_NAME and report.get('repository_commit') == commit
        and report.get('runtime_repository_commit') == RUNTIME_COMMIT
        and report.get('application_id') == base.APP_ID and report.get('version_name') == VERSION_NAME
        and report.get('version_code') == VERSION_CODE and report.get('signer_certificate_sha256') == SIGNER
        and report.get('signing_key_created') is False and report.get('donor') == donor_link()
        and report.get('qualification') == qualification and report.get('qualification_receipt') == base.file_pin(args.qualification)
        and report.get('java_sources') == sources and report.get('changed_java_sources') == changes
        and report.get('added_java_sources') == sorted(JAVA_ADDITIONS)
        and report.get('donor_dex') == donor['recompiled_dex'] and report.get('preserved_sources') == {name: pin for name, pin in donor['preserved_sources'].items() if name not in JAVA_CHANGES}
        and report.get('changed_apk_payloads') == [] and report.get('added_apk_payloads') == [] and report.get('replaced_apk_payloads') == []
        and all(report.get(key) is True for key in ('signature_verified', 'package_badging_verified', 'binary_manifest_version_only_verified', 'payload_bytes_verified', 'java_or_dex_recompiled'))
        and all(report.get(key) is False for key in ('native_libraries_changed', 'client_or_server_recompiled', 'world_assets_changed', 'prepared_cache_archive_changed', 'dbserver_changed', 'graphics_driver_changed', 'physical_gameplay_validated', 'physical_storage_cleanup_validated', 'physical_fresh_profile_recovery_validated', 'dialog_semantics_validated', 'runtime_refresh_required', 'asset_reimport_required'))
        and all(report.get(name) == donor[name] for name in RETAINED_RECEIPT_FIELDS), 'Storage build receipt differs')
    base.checked_file(args.apk, report); verify_derivative(args.apk, donor, report['payloads'], report['recompiled_dex'])
    verify_binary_manifest(args.apk, args.donor_apk, args.build_tools)
    require(verify_apk_server_archives(args.apk) == report['server_payload_extraction_preflight'], 'Published storage wrapper fails actual guest extraction')
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
    api = module('storage_recovery_github', Path(__file__).with_name('build_atlas_gameplay_apk.py'))
    print('Published storage prerelease:', publish_release(api.GitHub(os.environ.get('GH_TOKEN')), report,
        (args.apk, checksum, public_notes), public_notes.read_text()))


def audit(args):
    commit = builder().source_commit(args.repository_commit)
    report, _, _ = verify_report(args, commit)
    print('Public APK independently verified:', report['sha256'], '65 retained payloads; exact 0.13.0 runtime')


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
