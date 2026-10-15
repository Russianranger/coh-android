#!/usr/bin/env python3
"""Build .21 by repairing the GPU helper/probe over the immutable public .20 APK.

Game, twenty DLLs, seventeen Java sources, resources, servers, prepared assets,
rootfs, Wine and FEX retain exact published bytes. Two Java evidence validators,
DEX, four runtime payloads and the two binary Android version values change.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

import build_client_gpu_profile_apk as old
import package_client_gpu_repair as gpu_repair

ROOT, require, module, shared = old.ROOT, old.require, old.module, old.shared
REPOSITORY, BRANCH, SIGNER = old.REPOSITORY, old.BRANCH, old.SIGNER
retained, engine = old.retained, old.engine
DONOR_COMMIT, DONOR_RUN_ID = gpu_repair.DONOR_COMMIT, 37788954170
DONOR_APK_NAME = 'COH-Atlas-Gameplay-0.13.20.apk'
DONOR_APK = {'bytes': 1560271624, 'sha256': 'ac99a528e088bccce6e3164de62b55408624e3027ebaef24bce0f8c9f9e8b94e'}
DONOR_BUILD = {'bytes': 5244666, 'sha256': '2a86d163f90a4f1bd30a7d799c5030647a717d890d7395f8931aac67397fa848'}
DONOR_URL = 'https://github.com/'+REPOSITORY+'/releases/download/coh-atlas-gameplay-v0.13.20/'+DONOR_APK_NAME
VERSION_NAME, VERSION_CODE = '0.13.21', 36
APK_NAME, REPORT_NAME = 'COH-Atlas-Gameplay-0.13.21.apk', 'client-gpu-repair-apk-build-report.json'
NOTES_NAME = 'COH-Atlas-Gameplay-0.13.21-testing.txt'
RELEASE_TAG = 'coh-atlas-gameplay-v0.13.21'
NOTES = ROOT/'docs'/NOTES_NAME
WORKFLOW = '.github/workflows/android-client-gpu-repair.yml'
QUALIFICATION_SCRIPT = 'tools/android/interactive/qualify_client_gpu_repair.py'
QUALIFICATION_SCOPE = 'gpu_owned_cleanup_and_presented_screen_probe_repair_retaining_public_0_13_20_payloads'
JAVA_ROOT = old.JAVA_ROOT
JAVA_CHANGES = frozenset(JAVA_ROOT+name+'.java' for name in ('ClientAcceptance', 'ClientRuntime'))
HELPERS = frozenset({'client_gpu_profile.py'})
GPU_ARCHIVE = gpu_repair.ARCHIVE
REPLACED_PAYLOADS = frozenset('assets/runtime/'+name for name in HELPERS|{GPU_ARCHIVE, 'client-manifest.json', 'runtime-manifest.json'})
CHECKS = ('owned_cleanup_and_actual_screen_presentation_probe_guards_verified',
    'retained_gameplay_postgresql_and_recovery_guards_verified',
    'exact_retained_donor_payload_source_signer_and_probe_only_gpu_repair_verified')
SOURCE_FILES = frozenset({WORKFLOW, QUALIFICATION_SCRIPT,
    'tools/android/interactive/build_client_gpu_repair_apk.py',
    'tools/android/interactive/test_client_gpu_repair_package.py',
    'tools/android/interactive/test_client_gpu_profile.py', 'android/guest/client_gpu_profile.py',
    'docs/COH-PERFORMANCE-0.13.21.md', 'docs/'+NOTES_NAME, *gpu_repair.SOURCE_FILES,
    *JAVA_CHANGES, 'tools/android/interactive/test_client_gpu_repair_evidence.py'})
# Explicit reviewed modifications to source files already present in .20.
# Additions are in SOURCE_FILES; no broad directory exemption is permitted.
REVIEWED_DONOR_SOURCE_CHANGES = frozenset({
    'android/guest/client_gpu_profile.py', 'android/native/coh-gpu-probe.c',
    'tools/android/interactive/test_client_gpu_profile.py',
    'tools/android/interactive/test_coh_gpu_probe_native.py', 'docs/HANDOFF.md', *JAVA_CHANGES})
FALSE_FLAGS = old.FALSE_FLAGS + ('graphics_driver_changed',
    'mesa_driver_compiled_in_current_run', 'native_vulkan_probe_compiled_in_current_run')
TRUE_FLAGS = ('java_or_dex_recompiled', 'native_client_package_reused', 'retained_native_source_and_Win32_proof_verified',
    'wgl_probe_compiled_in_current_run', 'guest_helpers_changed', 'runtime_manifest_changed',
    'runtime_refresh_required', 'previous_runtime_generation_retained', 'gpu_driver_and_native_vulkan_probe_retained')
read_json = old.read_json


def builder(*, repaired=False):
    base = old.builder()
    if repaired: base.VERSION_NAME, base.VERSION_CODE, base.APK_NAME = VERSION_NAME, VERSION_CODE, APK_NAME
    return base


def donor_link():
    return {'run_id': DONOR_RUN_ID, 'repository_commit': DONOR_COMMIT, 'apk': DONOR_APK, 'build_report': DONOR_BUILD}


def validate_existing_release(release):
    """Skip publication only for a complete public asset inventory.

    This is metadata validation, not a substitute for the owner's public byte
    audit. Rerun failed jobs in that original run after an interrupted audit.
    An incomplete draft fails visibly and is never silently treated as done.
    """
    require(type(release.get('id')) is int and release['id'] > 0
        and release.get('tag_name') == RELEASE_TAG and release.get('draft') is False
        and release.get('prerelease') is True and type(release.get('published_at')) is str
        and release['published_at'], 'Existing release is incomplete; review the original owner run and rerun its failed jobs')
    assets = release.get('assets')
    require(type(assets) is list and len(assets) == 3
        and {item.get('name') for item in assets if type(item) is dict} == {APK_NAME, APK_NAME+'.sha256', NOTES_NAME},
        'Existing release has incomplete or duplicate assets; review the original owner run')
    base = 'https://github.com/'+REPOSITORY+'/releases/download/'+RELEASE_TAG+'/'
    for item in assets:
        name = item['name']; size = item.get('size')
        require(item.get('state') == 'uploaded' and type(size) is int and 0 < size <= 2*1024**3
            and type(item.get('digest')) is str and re.fullmatch(r'sha256:[0-9a-f]{64}', item['digest'])
            and item.get('browser_download_url') == base+name, 'Existing release asset metadata is incomplete')
        if name == APK_NAME+'.sha256': require(size == 97, 'Existing checksum metadata differs')
        if name == NOTES_NAME: require(size <= 65536, 'Existing testing notes are oversized')
    return True


def validate_retained_sources(donor):
    for name, expected in donor['qualification']['source_files'].items():
        require(type(name) is str and not Path(name).is_absolute() and '..' not in Path(name).parts
            and chr(92) not in name, 'Unsafe retained source path')
        if name not in REVIEWED_DONOR_SOURCE_CHANGES: builder().checked_file(ROOT/name, expected)


def current_java_sources(donor, generated):
    base = builder(); sources = retained.retained.java_sources(base, generated)
    pins = {p.relative_to(ROOT).as_posix(): base.file_pin(p) for p in sources
        if p.is_relative_to(ROOT) and not p.is_relative_to(generated)}
    require(len(pins) == 19 and set(pins) == set(donor['java_sources']), 'Exact nineteen authored Java inventory required')
    changed = {name for name in pins if pins[name] != donor['java_sources'][name]}
    require(changed == JAVA_CHANGES, 'Exactly two reviewed Java evidence validators must change')
    for name, expected in donor['preserved_sources'].items():
        if name not in JAVA_CHANGES: base.checked_file(ROOT/name, expected)
    base.checked_file(ROOT/'android/interactive/src/main/AndroidManifest.xml', donor['source_manifest'])
    for name, expected in donor['payloads'].items():
        if name.startswith('assets/runtime/') and name.endswith('.py') and Path(name).name not in HELPERS:
            base.checked_file(ROOT/'android/guest'/Path(name).name, expected)
    require(all(base.file_pin(ROOT/'android/guest'/name) != donor['payloads']['assets/runtime/'+name]
        for name in HELPERS), 'Reviewed GPU helper did not change')
    validate_retained_sources(donor)
    return sources, pins, sorted(changed)


def validate_donor_receipt(path):
    base = builder(); base.checked_file(path, DONOR_BUILD); donor = read_json(path); q = donor.get('qualification', {})
    require(donor.get('format') == 1 and donor.get('repository_commit') == DONOR_COMMIT
        and donor.get('runtime_repository_commit') == DONOR_COMMIT and donor.get('apk') == DONOR_APK_NAME
        and {k: donor.get(k) for k in DONOR_APK} == DONOR_APK
        and donor.get('application_id') == base.APP_ID and donor.get('version_name') == '0.13.20'
        and donor.get('version_code') == 35 and donor.get('abi') == 'arm64-v8a'
        and donor.get('signer_certificate_sha256') == SIGNER and donor.get('signing_key_created') is False
        and all(donor.get(k) is True for k in ('signature_verified', 'package_badging_verified',
            'binary_manifest_version_only_verified', 'payload_bytes_verified', 'setup_memory_guards_preserved'))
        and len(donor.get('payloads', {})) == 77 and len(donor.get('java_sources', {})) == 19
        and q.get('status') == 'passed' and q.get('scope') == old.QUALIFICATION_SCOPE
        and q.get('repository_commit') == DONOR_COMMIT and q.get('tests_run') == 1427
        and len(q.get('source_files', {})) == 9676 and len(q.get('test_suites', {})) == 96
        and all(v.get('status') == 'passed' and v.get('skipped') == 0 for v in q['test_suites'].values())
        and q.get('native_client_renderer_attribution') == donor.get('native_client_renderer_attribution')
        and donor.get('runtime_manifest_sha256') == 'acb477170c107810ad501d80e4774dbd69537bf899c60374754b7ef28a26605e'
        and donor.get('runtime_manifest_sha256') == donor['payloads']['assets/runtime/runtime-manifest.json']['sha256'],
        'Exact audited public .20 donor receipt differs')
    return donor


def validate_retained_native(directory, donor):
    native = old.retained_native.validate_package(directory, old.DONOR_COMMIT)
    require(native == donor['native_client_renderer_attribution']
        and native.get('run_url') == 'https://github.com/'+REPOSITORY+'/actions/runs/'+str(old.DONOR_RUN_ID),
        'Exact retained .19 Game/native proof required')
    return native


def validate_donor(apk, receipt, client_directory, donor_gpu_directory):
    base = builder(); base.checked_file(apk, DONOR_APK); donor = validate_donor_receipt(receipt)
    native = validate_retained_native(client_directory, donor)
    gpu, _ = gpu_repair.validate_donor(donor_gpu_directory)
    require(gpu == donor.get('client_gpu_runtime'), 'Retained GPU package differs from published .20 receipt')
    base.verify_packaged_payloads(apk, donor['payloads'])
    with zipfile.ZipFile(apk) as archive:
        shell = {'classes.dex': donor['recompiled_dex'], **donor['retained_android_resources']}
        require(retained.archive_inventory(archive) == set(donor['payloads'])|set(shell)|{'AndroidManifest.xml'}, 'Exact donor inventory required')
        for name, expected in shell.items():
            require(gpu_repair.pin(archive.read(name)) == expected, 'Donor Android shell differs: '+name)
        require(gpu_repair.pin(archive.read('assets/runtime/'+GPU_ARCHIVE)) == gpu_repair.DONOR_ARCHIVE,
            'Donor embedded GPU archive differs')
        require(read_json_value(archive.read('assets/runtime/runtime-manifest.json')) == donor['runtime_manifest'], 'Donor runtime provenance differs')
        donor['_client_verification'] = read_json_value(archive.read('assets/runtime/client-manifest.json'))
        with archive.open('assets/runtime/client-runtime.zip') as source, tempfile.TemporaryFile() as target:
            shutil.copyfileobj(source, target, 1024*1024); target.seek(0)
            with zipfile.ZipFile(target) as client:
                package = read_json_value(client.read('client-package.json')); pins = engine.startup.startup.client_member_pins(client)
                shared.native_contract.client_contract(package, donor['immutable_donor_provenance']['native_responsiveness'])
                dlls = donor['immutable_donor_provenance']['native_responsiveness']['retained_native_files']['client']
                require(package.get('client_renderer_attribution', {}).get('manifest') == native
                    and pins.get('CityOfHeroes.exe') == old.DONOR_GAME and len(dlls) == 20
                    and set(pins) == set(dlls)|{'CityOfHeroes.exe', 'client-package.json'}
                    and all(pins[n] == {'bytes': v['size'], 'sha256': v['sha256']} for n, v in dlls.items()), 'Actual donor Game/DLLs/native history differs')
    require(retained.verify_apk_server_archives(apk) == donor['server_payload_extraction_preflight'], 'Donor server extraction differs')
    current_java_sources(donor, ROOT/'out/no-generated-java')
    return donor


read_json_value = gpu_repair.old.json_value


def validate_gpu(directory, commit, donor_gpu_directory, probe_directory):
    return gpu_repair.validate_package(directory, commit, donor_gpu_directory, probe_directory)


def verification_manifests(donor, updates, commit, gpu):
    require(set(updates) == HELPERS|{GPU_ARCHIVE}, 'Only repaired helper/GPU archive inputs required')
    client = copy.deepcopy(donor['_client_verification']); client['files'].update(updates)
    runtime = copy.deepcopy(donor['runtime_manifest']); runtime['files'].update(updates)
    require(set(client['files']) == set(donor['_client_verification']['files']) and len(client['files']) <= 64,
        'Client inventory cannot change')
    raw = shared.encoded(client); runtime['files']['client-manifest.json'] = gpu_repair.pin(raw)
    runtime.update(repository_commit=commit, scope=QUALIFICATION_SCOPE)
    profile = copy.deepcopy(runtime['client_gpu_profile'])
    profile.update(repository_commit=commit, donor_repository_commit=DONOR_COMMIT,
        hardware_archive_pin=updates[GPU_ARCHIVE], producer_manifest_sha256=shared.native_contract.canonical_sha(gpu))
    runtime['client_gpu_profile'] = profile
    runtime['client_gpu_probe_repair'] = {'format': 1, 'repository_commit': commit,
        'donor_repository_commit': DONOR_COMMIT, 'retained_GPU_source_commit': DONOR_COMMIT,
        'retained_Game_source_commit': old.DONOR_COMMIT, 'driver_and_native_Vulkan_probe_retained': True,
        'only_WGL_probe_compiled_in_current_run': True, 'two_reviewed_Java_validators_and_DEX_recompiled': True,
        'physical_hardware_renderer_validated': False, 'physical_performance_validated': False}
    require(set(runtime['files']) == set(donor['runtime_manifest']['files']), 'Runtime inventory cannot change')
    return client, runtime


def payload_boundaries(payloads, donor):
    require(len(payloads) == 77 and set(payloads) == set(donor['payloads'])
        and {n for n in payloads if payloads[n] != donor['payloads'][n]} == REPLACED_PAYLOADS,
        'Exactly four repaired payloads and seventy-three retained payloads required')


def extract_and_repair(apk, donor, destination, commit, gpu_directory, gpu):
    destination.mkdir(parents=True); base = builder()
    with zipfile.ZipFile(apk) as archive:
        for entry in archive.infolist():
            if entry.filename == 'AndroidManifest.xml' or entry.filename.startswith('META-INF/'): continue
            target = destination/entry.filename; target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open('xb') as output: shutil.copyfileobj(source, output, 1024*1024)
    require(all(base.file_pin(destination/n) == v for n, v in donor['payloads'].items()), 'Extracted donor bytes differ')
    assets = destination/'assets/runtime'
    for name in HELPERS: shutil.copyfile(ROOT/'android/guest'/name, assets/name)
    shutil.copyfile(Path(gpu_directory)/GPU_ARCHIVE, assets/GPU_ARCHIVE)
    updates = {n: base.file_pin(assets/n) for n in sorted(HELPERS|{GPU_ARCHIVE})}
    require(updates[GPU_ARCHIVE] == gpu['files'][GPU_ARCHIVE], 'Qualified GPU archive bytes differ')
    client, runtime = verification_manifests(donor, updates, commit, gpu)
    for n, value in (('client-manifest.json', client), ('runtime-manifest.json', runtime)): (assets/n).write_bytes(shared.encoded(value))
    payloads = {n: base.file_pin(destination/n) for n in sorted(donor['payloads'])}; payload_boundaries(payloads, donor)
    require(retained.verify_server_archives(assets) == donor['server_payload_extraction_preflight'], 'Retained server extraction differs')
    return runtime, payloads


def verify_derivative(apk, donor, payloads, dex_pin, commit, gpu):
    base = builder(); payload_boundaries(payloads, donor); base.verify_packaged_payloads(apk, payloads)
    with zipfile.ZipFile(apk) as archive:
        require(dex_pin != donor['recompiled_dex'], 'Current evidence Java/DEX was not recompiled')
        shell = {'classes.dex': dex_pin, **donor['retained_android_resources']}
        require(retained.archive_inventory(archive) == set(payloads)|set(shell)|{'AndroidManifest.xml'}, 'Exact candidate inventory required')
        for n, expected in shell.items(): require(gpu_repair.pin(archive.read(n)) == expected, 'Retained DEX/resources differ: '+n)
        for n in HELPERS: require(payloads['assets/runtime/'+n] == base.file_pin(ROOT/'android/guest'/n), 'Current authored GPU helper differs')
        require(payloads['assets/runtime/'+GPU_ARCHIVE] == gpu['files'][GPU_ARCHIVE], 'Qualified repaired GPU archive differs')
        client, runtime = verification_manifests(donor, {n: payloads['assets/runtime/'+n] for n in HELPERS|{GPU_ARCHIVE}}, commit, gpu)
        require(archive.read('assets/runtime/client-manifest.json') == shared.encoded(client)
            and archive.read('assets/runtime/runtime-manifest.json') == shared.encoded(runtime), 'Actual candidate manifest/provenance bytes differ')
    require(retained.verify_apk_server_archives(apk) == donor['server_payload_extraction_preflight'], 'Candidate server extraction differs')
    return runtime


def validate_qualification(q, commit):
    require(q.get('format') == 1 and q.get('status') == 'passed' and q.get('scope') == QUALIFICATION_SCOPE
        and q.get('repository_commit') == commit and q.get('runtime_repository_commit') == commit
        and q.get('donor') == donor_link() and q.get('checks') == dict.fromkeys(CHECKS, True)
        and all(q.get(k) is False for k in FALSE_FLAGS) and all(q.get(k) is True for k in TRUE_FLAGS)
        and q.get('installed_runtime_identity_preserved') is False, 'Exact truthful repair qualification required')
    contract = module('client_gpu_repair_qualification_contract', ROOT/QUALIFICATION_SCRIPT); contract.validate_suite_inventory()
    suites = q.get('test_suites', {})
    require(set(suites) == set(contract.TEST_MODULES) and q.get('check_suites') == contract.CHECK_SUITES
        and all(v.get('status') == 'passed' and v.get('skipped') == 0 and type(v.get('tests_run')) is int and v['tests_run'] > 0 for v in suites.values())
        and q.get('tests_run') == sum(v['tests_run'] for v in suites.values()), 'All retained/new suites must pass without skips')
    require(SOURCE_FILES <= set(q.get('source_files', {})), 'Repair source closure incomplete')
    for n, expected in q['source_files'].items():
        require(type(n) is str and not Path(n).is_absolute() and '..' not in Path(n).parts and chr(92) not in n, 'Unsafe qualified source')
        builder().checked_file(ROOT/n, expected)
    require(q.get('postgresql_emission_fixtures') == ['cancelled_child_deletion_commits', 'delete_insert_replacement_commits', 'duplicate_insert_23505_rollback']
        and q.get('postgresql_levelup_fixtures') == sorted(retained.levelup_postgresql_fixtures()), 'All seven real PostgreSQL fixtures required')
    return q


def repair_android_manifest(source, destination):
    base = builder(); base.verify_source_manifest(source); tree = ET.parse(source)
    tree.getroot().set(base.ANDROID+'versionName', VERSION_NAME); tree.getroot().set(base.ANDROID+'versionCode', str(VERSION_CODE))
    ET.register_namespace('android', base.ANDROID[1:-1]); tree.write(destination, encoding='utf-8', xml_declaration=True)
    builder(repaired=True).verify_source_manifest(destination)


def build(args):
    base, current = builder(), builder(repaired=True); commit = base.source_commit(args.repository_commit)
    donor = validate_donor(args.donor_apk, args.donor_build_report, args.client_directory, args.donor_gpu_directory)
    q = validate_qualification(read_json(args.qualification), commit)
    gpu = validate_gpu(args.gpu_directory, commit, args.donor_gpu_directory, args.probe_directory)
    native = validate_retained_native(args.client_directory, donor); _, java, changed = current_java_sources(donor, ROOT/'out/no-generated-java')
    require(q.get('native_client_renderer_attribution') == native and q.get('client_gpu_runtime') == gpu
        and q.get('java_sources') == java and q.get('changed_java_sources') == changed, 'Qualified native/GPU/Java inputs differ')
    password = base.signing_password_spec(args.password_env); base.verify_signing_identity(args.keystore, 'coh-client-interactive', SIGNER, password)
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), 'Fresh .21 APK required')
    base.checked_file(args.testing_notes); require(0 < args.testing_notes.stat().st_size <= 65536, 'Bounded notes required')
    for tool in (args.android_jar, args.build_tools/'aapt2', args.build_tools/'zipalign', args.build_tools/'lib/d8.jar', args.build_tools/'lib/apksigner.jar'):
        require(tool.is_file() and not tool.is_symlink(), 'Required SDK tool missing')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-gpu-repair-', dir=args.output.parent) as temporary:
        work = Path(temporary); runtime, payloads = extract_and_repair(args.donor_apk, donor, work/'donor', commit, args.gpu_directory, gpu)
        manifest = work/'AndroidManifest.xml'; repair_android_manifest(ROOT/'android/interactive/src/main/AndroidManifest.xml', manifest)
        resources, unsigned, aligned, signed = (work/n for n in ('resources.zip', 'unsigned.apk', 'aligned.apk', 'signed.apk'))
        classes, generated, dex = (work/n for n in ('classes', 'generated', 'dex'))
        for folder in (classes, generated, dex): folder.mkdir()
        base.run(args.build_tools/'aapt2', 'compile', '--dir', ROOT/'android/interactive/src/main/res', '-o', resources)
        base.run(args.build_tools/'aapt2', 'link', '-I', args.android_jar, '--manifest', manifest, '--min-sdk-version', '26', '--target-sdk-version', '35', '--java', generated, resources, '-o', unsigned)
        with zipfile.ZipFile(unsigned) as archive:
            require(retained.archive_inventory(archive) == {'AndroidManifest.xml', 'resources.arsc', 'res/drawable/ic_coh_client.xml'}, 'Generated Android resource inventory differs')
            for n, expected in donor['retained_android_resources'].items(): require(gpu_repair.pin(archive.read(n)) == expected, 'Retained resources changed')
        # aapt2 only generates the exact retained R class; authored Java is finite.
        require({p.relative_to(generated).as_posix() for p in generated.rglob('*.java')} == {base.APP_ID.replace('.', '/')+'/R.java'}, 'Unexpected generated Java source')
        sources, java, changed = current_java_sources(donor, generated)
        require(q.get('java_sources') == java and q.get('changed_java_sources') == changed, 'Java changed after qualification')
        base.run('java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8', '-cp', args.android_jar, '-d', classes, *sources)
        class_jar = work/'classes.jar'
        with zipfile.ZipFile(class_jar, 'w', zipfile.ZIP_DEFLATED) as archive:
            for p in sorted(classes.rglob('*.class')): archive.write(p, p.relative_to(classes).as_posix())
        base.run('java', '-cp', args.build_tools/'lib/d8.jar', 'com.android.tools.r8.D8', '--min-api', '26', '--lib', args.android_jar, '--output', dex, class_jar)
        require({p.name for p in dex.iterdir()} == {'classes.dex'}, 'Unexpected DEX output')
        dex_pin = base.file_pin(dex/'classes.dex')
        with zipfile.ZipFile(unsigned, 'a', zipfile.ZIP_DEFLATED) as archive:
            base.append_payloads(archive, [(work/'donor'/n, n) for n in sorted(payloads)])
            archive.write(dex/'classes.dex', 'classes.dex')
        base.run(args.build_tools/'zipalign', '-f', '4', unsigned, aligned)
        base.run('java', '-jar', args.build_tools/'lib/apksigner.jar', 'sign', '--ks', args.keystore,
            '--ks-key-alias', 'coh-client-interactive', '--ks-pass', password, '--key-pass', password, '--out', signed, aligned)
        certificate = retained.verify_signature(signed, args.build_tools); base.run(args.build_tools/'zipalign', '-c', '4', signed)
        current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', signed))
        verify_derivative(signed, donor, payloads, dex_pin, commit, gpu); retained.verify_binary_manifest(signed, args.donor_apk, args.build_tools)
        shutil.copyfile(signed, args.output)
        report = {'format': 1, 'apk': APK_NAME, **base.file_pin(args.output), 'repository_commit': commit,
            'runtime_repository_commit': commit, 'retained_runtime_repository_commit': DONOR_COMMIT,
            'retained_native_repository_commit': old.DONOR_COMMIT, 'application_id': base.APP_ID,
            'version_name': VERSION_NAME, 'version_code': VERSION_CODE, 'abi': 'arm64-v8a', 'scope': QUALIFICATION_SCOPE,
            'donor': donor_link(), 'signer_certificate_sha256': certificate, 'signing_key_created': False,
            'signature_verified': True, 'package_badging_verified': True, 'binary_manifest_version_only_verified': True,
            'payload_bytes_verified': True, 'payloads': payloads, 'changed_apk_payloads': sorted(REPLACED_PAYLOADS),
            'replaced_apk_payloads': sorted(REPLACED_PAYLOADS), 'added_apk_payloads': [],
            'baseline_payloads_verified': 77, 'retained_baseline_payloads_verified': 73,
            'recompiled_dex': dex_pin, 'donor_dex': donor['recompiled_dex'], 'java_sources': java, 'changed_java_sources': changed,
            'added_java_sources': [], 'retained_java_sources_verified': 17, 'generated_manifest': base.file_pin(manifest),
            'qualification': q, 'qualification_receipt': base.file_pin(args.qualification), 'testing_notes': base.file_pin(args.testing_notes),
            'installed_runtime_identity_preserved': False, 'native_client_renderer_attribution': native, 'client_gpu_runtime': gpu,
            'runtime_manifest': runtime, 'runtime_manifest_sha256': payloads['assets/runtime/runtime-manifest.json']['sha256'],
            'setup_memory_guards_preserved': True, 'all_published_visual_resources_retained': True,
            **dict.fromkeys(FALSE_FLAGS, False), **dict.fromkeys(TRUE_FLAGS, True),
            **{n: donor[n] for n in old.RETAINED_RECEIPT_FIELDS}}
        (args.output.parent/REPORT_NAME).write_bytes(shared.encoded(report))
    shutil.copyfile(args.testing_notes, args.output.parent/NOTES_NAME)
    args.output.with_suffix('.apk.sha256').write_text(report['sha256']+'  '+APK_NAME+'\n')
    verify_report(argparse.Namespace(**vars(args), apk=args.output, build_report=args.output.parent/REPORT_NAME), commit)
    print('Qualified GPU probe repair APK:', args.output, report['sha256']); return report


def verify_report(args, commit):
    donor = validate_donor(args.donor_apk, args.donor_build_report, args.client_directory, args.donor_gpu_directory)
    base = builder(); q = validate_qualification(read_json(args.qualification), commit)
    gpu = validate_gpu(args.gpu_directory, commit, args.donor_gpu_directory, args.probe_directory)
    report = read_json(args.build_report); _, java, changed = current_java_sources(donor, ROOT/'out/no-generated-java')
    require(report.get('format') == 1 and report.get('apk') == APK_NAME and report.get('repository_commit') == commit
        and report.get('runtime_repository_commit') == commit and report.get('retained_runtime_repository_commit') == DONOR_COMMIT
        and report.get('retained_native_repository_commit') == old.DONOR_COMMIT and report.get('donor') == donor_link()
        and report.get('scope') == QUALIFICATION_SCOPE and report.get('application_id') == base.APP_ID
        and report.get('version_name') == VERSION_NAME and report.get('version_code') == VERSION_CODE and report.get('abi') == 'arm64-v8a'
        and report.get('signer_certificate_sha256') == SIGNER and report.get('signing_key_created') is False
        and report.get('qualification') == q and report.get('qualification_receipt') == base.file_pin(args.qualification)
        and report.get('native_client_renderer_attribution') == q.get('native_client_renderer_attribution') == donor['native_client_renderer_attribution']
        and report.get('client_gpu_runtime') == q.get('client_gpu_runtime') == gpu
        and report.get('java_sources') == q.get('java_sources') == java and report.get('changed_java_sources') == q.get('changed_java_sources') == changed
        and report.get('added_java_sources') == [] and report.get('retained_java_sources_verified') == 17
        and report.get('donor_dex') == donor['recompiled_dex']
        and report.get('changed_apk_payloads') == report.get('replaced_apk_payloads') == sorted(REPLACED_PAYLOADS)
        and report.get('added_apk_payloads') == [] and report.get('baseline_payloads_verified') == 77
        and report.get('retained_baseline_payloads_verified') == 73
        and all(report.get(k) is True for k in TRUE_FLAGS+('signature_verified', 'package_badging_verified',
            'binary_manifest_version_only_verified', 'payload_bytes_verified', 'setup_memory_guards_preserved', 'all_published_visual_resources_retained'))
        and all(report.get(k) is False for k in FALSE_FLAGS) and report.get('installed_runtime_identity_preserved') is False
        and all(report.get(n) == donor[n] for n in old.RETAINED_RECEIPT_FIELDS), 'Exact probe repair build receipt differs')
    base.checked_file(args.apk, report); runtime = verify_derivative(args.apk, donor, report['payloads'], report['recompiled_dex'], commit, gpu)
    require(report.get('runtime_manifest') == runtime and report.get('runtime_manifest_sha256') == report['payloads']['assets/runtime/runtime-manifest.json']['sha256'], 'Runtime repair provenance differs')
    retained.verify_binary_manifest(args.apk, args.donor_apk, args.build_tools); retained.verify_signature(args.apk, args.build_tools)
    base.run(args.build_tools/'zipalign', '-c', '4', args.apk); builder(repaired=True).verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', args.apk))
    checksum = args.apk.with_suffix('.apk.sha256'); require(checksum.read_text() == report['sha256']+'  '+APK_NAME+'\n', 'Checksum differs')
    notes = args.apk.parent/NOTES_NAME; base.checked_file(notes, report['testing_notes']); base.checked_file(args.testing_notes, report['testing_notes'])
    return report, checksum, notes


def bounded_download(url, destination, expected):
    destination = Path(destination); require(not destination.exists() and not destination.is_symlink(), 'Fresh download required')
    destination.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic()+600
    try:
        with urllib.request.urlopen(url, timeout=30) as response, destination.open('xb') as output:
            require(response.status == 200, 'Public download must return HTTP 200'); count = 0
            while chunk := response.read(1024*1024):
                count += len(chunk); require(count <= expected['bytes'] and time.monotonic() < deadline, 'Oversized/timed out public download')
                output.write(chunk)
        builder().checked_file(destination, expected)
    except BaseException:
        destination.unlink(missing_ok=True); raise


def publish_release(api, report, assets, notes):
    require(tuple(p.name for p in assets) == (APK_NAME, APK_NAME+'.sha256', NOTES_NAME), 'Unexpected release assets')
    builder().checked_file(assets[0], report)
    for path in ('/releases/tags/'+RELEASE_TAG, '/git/ref/tags/'+RELEASE_TAG):
        try: existing = api.request(path)
        except urllib.error.HTTPError as error:
            if error.code != 404: raise
        else:
            require(not path.startswith('/releases/'), 'Existing release is never replaced')
            require(existing.get('object', {}).get('type') == 'commit' and existing['object'].get('sha') == report['repository_commit'], 'Existing tag points elsewhere')
    old.require_current_release_head(api, report['repository_commit'])
    release = api.request('/releases', {'tag_name': RELEASE_TAG, 'target_commitish': report['repository_commit'],
        'name': 'COH Atlas Gameplay 0.13.21 — GPU preflight and cleanup repair',
        'body': notes+'\n\nAPK SHA-256: `'+report['sha256']+'`.\n[Hosted qualification](https://github.com/'+REPOSITORY+'/actions/runs/'+os.environ.get('GITHUB_RUN_ID', '')+').\n',
        'draft': True, 'prerelease': True, 'generate_release_notes': False, 'make_latest': 'false'}, method='POST')
    require(type(release.get('id')) is int and release.get('draft') is True and release.get('tag_name') == RELEASE_TAG, 'Unexpected release')
    for p in assets:
        uploaded = api.request('/releases/'+str(release['id'])+'/assets?'+urllib.parse.urlencode({'name': p.name}), p, method='POST', upload=True)
        expected = builder().file_pin(p)
        require(uploaded.get('state') == 'uploaded' and uploaded.get('name') == p.name and uploaded.get('size') == expected['bytes']
            and uploaded.get('digest') == 'sha256:'+expected['sha256'], 'Release upload differs')
    old.require_current_release_head(api, report['repository_commit'])
    result = api.request('/releases/'+str(release['id']), {'draft': False, 'prerelease': True, 'make_latest': 'false'}, method='PATCH')
    require(result.get('id') == release['id'] and result.get('draft') is False and result.get('prerelease') is True
        and result.get('tag_name') == RELEASE_TAG, 'Publication incomplete')
    return result.get('html_url')


def publish(args):
    require(os.environ.get('GITHUB_REPOSITORY') == REPOSITORY and os.environ.get('GITHUB_REF') == 'refs/heads/'+BRANCH
        and os.environ.get('GITHUB_EVENT_NAME') in ('push', 'workflow_dispatch'), 'Publication requires continuation branch')
    commit = builder().source_commit(os.environ.get('GITHUB_SHA')); report, checksum, notes = verify_report(args, commit)
    api = module('client_gpu_repair_github', Path(__file__).with_name('build_atlas_gameplay_apk.py'))
    print('Published GPU repair prerelease:', publish_release(api.GitHub(os.environ.get('GH_TOKEN')), report, (args.apk, checksum, notes), notes.read_text()))


def download_public(args):
    report = read_json(args.build_report); require(report.get('apk') == APK_NAME, 'Expected repair public APK')
    specs = {APK_NAME: {k: report[k] for k in ('bytes', 'sha256')},
        APK_NAME+'.sha256': gpu_repair.pin((report['sha256']+'  '+APK_NAME+'\n').encode()), NOTES_NAME: report['testing_notes']}
    base = 'https://github.com/'+REPOSITORY+'/releases/download/'+RELEASE_TAG+'/'
    for name, expected in specs.items():
        destination = args.output/name
        if destination.exists() or destination.is_symlink():
            # Evidence artifacts contain local notes/checksum, not proof of
            # public bytes. Authenticate them, then fetch the actual asset.
            builder().checked_file(destination, expected); destination.unlink()
        bounded_download(base+name, destination, expected)
    print('Actual public APK/checksum/testing notes authenticated')


def main():
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest='command', required=True)
    donor = commands.add_parser('download-donor'); donor.add_argument('--output', type=Path, required=True)
    public = commands.add_parser('download-public'); public.add_argument('--output', type=Path, required=True); public.add_argument('--build-report', type=Path, required=True)
    for name in ('build', 'audit', 'publish'):
        command = commands.add_parser(name)
        for arg in ('donor-apk', 'donor-build-report', 'qualification', 'build-tools', 'client-directory', 'gpu-directory', 'donor-gpu-directory', 'probe-directory'):
            command.add_argument('--'+arg, type=Path, required=True)
        command.add_argument('--testing-notes', type=Path, default=NOTES); command.add_argument('--repository-commit', default=os.environ.get('GITHUB_SHA'))
        if name == 'build':
            command.add_argument('--android-jar', type=Path, required=True); command.add_argument('--keystore', type=Path, required=True)
            command.add_argument('--password-env', default='COH_INTERACTIVE_KEYSTORE_PASSWORD'); command.add_argument('--output', type=Path, required=True)
        else:
            command.add_argument('--apk', type=Path, required=True); command.add_argument('--build-report', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'download-donor': bounded_download(DONOR_URL, args.output, DONOR_APK)
    elif args.command == 'download-public': download_public(args)
    elif args.command == 'build': build(args)
    elif args.command == 'publish': publish(args)
    else: print('Repair candidate verified:', verify_report(args, builder().source_commit(args.repository_commit))[0]['sha256'])


if __name__ == '__main__': main()
