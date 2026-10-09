#!/usr/bin/env python3
"""Append an opt-in, probed GPU profile over the audited immutable 0.13.19 APK."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

import build_client_renderer_attribution_apk as previous
import package_client_renderer_attribution_native as retained_native
import package_client_gpu_runtime as gpu_producer

ROOT, require, module, shared = previous.ROOT, previous.require, previous.module, previous.shared
REPOSITORY, BRANCH, SIGNER = previous.REPOSITORY, previous.BRANCH, previous.SIGNER
retained, engine = previous.retained, previous.engine
DONOR_COMMIT = 'a4a658be25d2b5ca1393b7d3daedd83a7d9ca1f4'
DONOR_RUN_ID = 37723301707
DONOR_APK_NAME = 'COH-Atlas-Gameplay-0.13.19.apk'
DONOR_APK = {'bytes': 1557408356, 'sha256': 'e4c04aff16056ba2fb2560b818355ada6c3fe95d7f5c219a37d3b2945b330241'}
DONOR_BUILD = {'bytes': 5103904, 'sha256': 'c16f161383e842ebc151bc3863069b874013e2d38a243dd77e3b86a5c6071ee5'}
DONOR_GAME = {'bytes': 9487872, 'sha256': 'adcabb11135fe44b2c1f997a088ec58e4ea0d90e9defaa9f88efea34538caa44'}
DONOR_URL = 'https://github.com/'+REPOSITORY+'/releases/download/coh-atlas-gameplay-v0.13.19/'+DONOR_APK_NAME
VERSION_NAME, VERSION_CODE = '0.13.20', 35
APK_NAME, REPORT_NAME = 'COH-Atlas-Gameplay-0.13.20.apk', 'client-gpu-profile-apk-build-report.json'
NOTES_NAME = 'COH-Atlas-Gameplay-0.13.20-testing.txt'
NOTES = ROOT/'docs'/NOTES_NAME
RELEASE_TAG = 'coh-atlas-gameplay-v0.13.20'
WORKFLOW = '.github/workflows/android-client-gpu-profile.yml'
QUALIFICATION_SCRIPT = 'tools/android/interactive/qualify_client_gpu_profile.py'
QUALIFICATION_SCOPE = 'optional_probed_kgsl_turnip_zink_profile_retaining_public_0_13_19_Game_and_software_default'
JAVA_ROOT = previous.JAVA_ROOT
JAVA_CHANGES = frozenset(JAVA_ROOT+name+'.java' for name in ('ClientActivity', 'ClientRuntime'))
JAVA_ADDITIONS = frozenset()
HELPERS = frozenset({'client_startup_diagnostic.py', 'client_interactive_diagnostic.py'})
ADDED_HELPERS = frozenset({'client_gpu_profile.py'})
GPU_ARCHIVE = 'hardware-renderer.zip'
REPLACED_PAYLOADS = frozenset('assets/runtime/'+name for name in HELPERS|{'client-manifest.json', 'runtime-manifest.json'})
ADDED_PAYLOADS = frozenset('assets/runtime/'+name for name in ADDED_HELPERS|{GPU_ARCHIVE})
CHECKS = ('probed_optional_gpu_profile_and_software_fallback_verified',
    'retained_gameplay_postgresql_and_recovery_guards_verified',
    'exact_retained_Game_and_reviewed_android_helper_gpu_payload_boundaries_verified')
SOURCE_FILES = frozenset({WORKFLOW, QUALIFICATION_SCRIPT,
    'tools/android/interactive/build_client_gpu_profile_apk.py',
    'tools/android/interactive/test_client_gpu_profile_package.py',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'docs/COH-PERFORMANCE-0.13.20.md', 'docs/'+NOTES_NAME,
    'docs/android-evidence/gpu-profile-0.13.19-thor-20261008.json',
    *JAVA_CHANGES, *('android/guest/'+name for name in HELPERS|ADDED_HELPERS),
    *gpu_producer.SOURCE_FILES})
REVIEWED_DONOR_SOURCE_CHANGES = frozenset(name for name in SOURCE_FILES
    if not name.startswith('upstream/') and name != 'android/runtime-lock.json') | frozenset({'docs/HANDOFF.md',
    'docs/android-evidence/renderer-attribution-0.13.19-publication.json'})
FALSE_FLAGS = ('native_dbserver_recompiled', 'native_client_recompiled', 'native_mapserver_recompiled',
    'native_client_compiled_in_current_run', 'native_runtime_booted', 'physical_gameplay_validated',
    'physical_client_timing_validated', 'physical_visual_assets_validated', 'physical_hardware_renderer_validated',
    'physical_fps_gain_validated', 'physical_black_glitch_fix_validated', 'asset_reimport_required',
    'world_assets_changed', 'prepared_cache_archive_changed', 'wine_or_fex_changed',
    'rootfs_changed', 'display_transport_changed', 'save_acceptance_relaxed', 'zoning_implemented')
RETAINED_RECEIPT_FIELDS = previous.RETAINED_RECEIPT_FIELDS + ('native_client_renderer_attribution',)
read_json = previous.read_json


def builder(*, repaired=False):
    base = previous.builder()
    if repaired: base.VERSION_NAME, base.VERSION_CODE, base.APK_NAME = VERSION_NAME, VERSION_CODE, APK_NAME
    return base


def donor_link():
    return {'run_id': DONOR_RUN_ID, 'repository_commit': DONOR_COMMIT, 'apk': DONOR_APK, 'build_report': DONOR_BUILD}


def validate_retained_sources(donor):
    for name, pin in donor['qualification']['source_files'].items():
        require(isinstance(name, str) and not Path(name).is_absolute() and '..' not in Path(name).parts
            and chr(92) not in name, 'Unsafe retained source path')
        if name not in REVIEWED_DONOR_SOURCE_CHANGES: builder().checked_file(ROOT/name, pin)


def current_java_sources(donor, generated):
    base = builder(); sources = retained.retained.java_sources(base, generated)
    pins = {path.relative_to(ROOT).as_posix(): base.file_pin(path) for path in sources
        if path.is_relative_to(ROOT) and not path.is_relative_to(generated)}
    require(set(pins) == set(donor['java_sources']) and len(pins) == 19, 'Authored Java inventory must remain exact')
    changed = {name for name in pins if pins[name] != donor['java_sources'][name]}
    require(changed == JAVA_CHANGES, 'Java changes exceed the reviewed optional GPU selector/runtime sources')
    for name, pin in donor['preserved_sources'].items(): base.checked_file(ROOT/name, pin)
    base.checked_file(ROOT/'android/interactive/src/main/AndroidManifest.xml', donor['source_manifest'])
    for name, pin in donor['payloads'].items():
        if name.startswith('assets/runtime/') and name.endswith('.py') and Path(name).name not in HELPERS:
            base.checked_file(ROOT/'android/guest'/Path(name).name, pin)
    require({name for name in HELPERS if base.file_pin(ROOT/'android/guest'/name) != donor['payloads']['assets/runtime/'+name]} == HELPERS,
        'Exactly the reviewed GPU launch helpers must change')
    validate_retained_sources(donor)
    return sources, pins, sorted(changed)


def repair_android_manifest(source, destination):
    base = builder(); base.verify_source_manifest(source); tree = ET.parse(source)
    tree.getroot().set(base.ANDROID+'versionName', VERSION_NAME); tree.getroot().set(base.ANDROID+'versionCode', str(VERSION_CODE))
    ET.register_namespace('android', base.ANDROID[1:-1]); tree.write(destination, encoding='utf-8', xml_declaration=True)
    builder(repaired=True).verify_source_manifest(destination)


def download(args):
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh donor required'); args.output.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(DONOR_URL, timeout=120) as source, args.output.open('xb') as target:
        total = 0
        while chunk := source.read(1024*1024):
            total += len(chunk); require(total <= DONOR_APK['bytes'], 'Oversized donor'); target.write(chunk)
    builder().checked_file(args.output, DONOR_APK)


def validate_donor_receipt(path):
    builder().checked_file(path, DONOR_BUILD); donor = read_json(path); q = donor.get('qualification', {})
    require(donor.get('format') == 1 and donor.get('repository_commit') == DONOR_COMMIT
        and donor.get('runtime_repository_commit') == DONOR_COMMIT and donor.get('apk') == DONOR_APK_NAME
        and {key: donor.get(key) for key in DONOR_APK} == DONOR_APK
        and donor.get('application_id') == builder().APP_ID and donor.get('version_name') == '0.13.19'
        and donor.get('version_code') == 34 and donor.get('abi') == 'arm64-v8a'
        and donor.get('signer_certificate_sha256') == SIGNER and donor.get('signing_key_created') is False
        and all(donor.get(key) is True for key in ('signature_verified', 'package_badging_verified',
            'binary_manifest_version_only_verified', 'payload_bytes_verified', 'setup_memory_guards_preserved',
            'java_or_dex_recompiled', 'native_client_recompiled', 'runtime_refresh_required'))
        and len(donor.get('payloads', {})) == 75 and len(donor.get('java_sources', {})) == 19
        and q.get('status') == 'passed' and q.get('scope') == previous.QUALIFICATION_SCOPE
        and q.get('repository_commit') == DONOR_COMMIT and q.get('tests_run') == 1345
        and len(q.get('source_files', {})) == 9656 and len(q.get('test_suites', {})) == 91
        and all(item.get('status') == 'passed' and item.get('skipped') == 0 for item in q['test_suites'].values())
        and q.get('native_client_renderer_attribution') == donor.get('native_client_renderer_attribution')
        and donor.get('server_payload_extraction_preflight', {}).get('status') == 'passed'
        and donor.get('runtime_manifest_sha256') == '89f591caeb5e0d8731bcd28defeae35dc59c1435ed3b8d0a141702cfe805edf3'
        and donor.get('runtime_manifest_sha256') == donor.get('payloads', {}).get('assets/runtime/runtime-manifest.json', {}).get('sha256'),
        'Exact audited public 0.13.19 donor receipt differs')
    game = donor['native_client_renderer_attribution']['files']['CityOfHeroes.exe']
    require({'bytes': game['size'], 'sha256': game['sha256']} == DONOR_GAME, 'Frozen published 0.13.19 Game differs')
    return donor


def validate_retained_native(directory, donor):
    native = retained_native.validate_package(directory, DONOR_COMMIT)
    require(native == donor['native_client_renderer_attribution']
        and native.get('run_url') == 'https://github.com/'+REPOSITORY+'/actions/runs/'+str(DONOR_RUN_ID),
        'Exact previously compiled and Win32-qualified 0.13.19 native package required')
    return native


def validate_gpu(directory, commit):
    gpu = gpu_producer.validate_package(directory, commit)
    if os.environ.get('GITHUB_RUN_ID'):
        require(gpu.get('run_url') == 'https://github.com/'+REPOSITORY+'/actions/runs/'+os.environ['GITHUB_RUN_ID'],
            'GPU payload must be produced and qualified in this exact current run')
    require(gpu.get('repository_commit') == commit and set(gpu.get('files', {})) == {GPU_ARCHIVE},
        'Exact source-bound single GPU archive required')
    builder().checked_file(Path(directory)/GPU_ARCHIVE, gpu['files'][GPU_ARCHIVE])
    return gpu


def validate_donor(apk, receipt, client_directory):
    base = builder(); base.checked_file(apk, DONOR_APK); donor = validate_donor_receipt(receipt)
    native = validate_retained_native(client_directory, donor)
    base.verify_packaged_payloads(apk, donor['payloads'])
    with zipfile.ZipFile(apk) as archive:
        shell = {'classes.dex': donor['recompiled_dex'], **donor['retained_android_resources']}
        require(retained.archive_inventory(archive) == set(donor['payloads'])|set(shell)|{'AndroidManifest.xml'},
            'Unexpected immutable public donor inventory')
        for name, pin in shell.items():
            raw = archive.read(name); require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == pin,
                'Donor Android shell differs: '+name)
        require(json.loads(archive.read('assets/runtime/runtime-manifest.json')) == donor['runtime_manifest'], 'Donor runtime provenance differs')
        donor['_client_verification'] = json.loads(archive.read('assets/runtime/client-manifest.json'))
        with archive.open('assets/runtime/client-runtime.zip') as source, tempfile.TemporaryFile() as target:
            shutil.copyfileobj(source, target, 1024*1024); target.seek(0)
            with zipfile.ZipFile(target) as client:
                package = json.loads(client.read('client-package.json')); pins = engine.startup.startup.client_member_pins(client)
                shared.native_contract.client_contract(package, donor['immutable_donor_provenance']['native_responsiveness'])
                require(package.get('client_renderer_attribution', {}).get('manifest') == native
                    and package.get('files', {}).get('CityOfHeroes.exe') == native['files']['CityOfHeroes.exe']
                    and pins.get('CityOfHeroes.exe') == DONOR_GAME, 'Actual donor Game and typed native history differ')
                dlls = donor['immutable_donor_provenance']['native_responsiveness']['retained_native_files']['client']
                require(len(dlls) == 20 and set(pins) == set(dlls)|{'CityOfHeroes.exe', 'client-package.json'}
                    and all(pins[name] == {'bytes': pin['size'], 'sha256': pin['sha256']} for name, pin in dlls.items()),
                    'Actual immutable donor DLL closure differs')
                donor['_native_client_manifest'], donor['_client_members'] = package, pins
    require(retained.verify_apk_server_archives(apk) == donor['server_payload_extraction_preflight'], 'Donor server extraction differs')
    validate_retained_sources(donor)
    return donor


def verification_manifests(donor, updates, commit, gpu):
    require(set(updates) == HELPERS|ADDED_HELPERS|{GPU_ARCHIVE}, 'Unexpected GPU replacement/addition inputs')
    client = copy.deepcopy(donor['_client_verification']); client['files'].update(updates)
    require(set(client['files']) == set(donor['_client_verification']['files'])|HELPERS|ADDED_HELPERS|{GPU_ARCHIVE}
        and len(client['files']) <= 64, 'Exact bounded client payload inventory required')
    runtime = copy.deepcopy(donor['runtime_manifest']); runtime['files'].update(updates)
    encoded = shared.encoded(client)
    runtime['files']['client-manifest.json'] = {'bytes': len(encoded), 'sha256': hashlib.sha256(encoded).hexdigest()}
    runtime['repository_commit'] = commit; runtime['scope'] = QUALIFICATION_SCOPE
    runtime['client_gpu_profile'] = {'format': 1, 'repository_commit': commit,
        'donor_repository_commit': DONOR_COMMIT, 'default_profile': 'software', 'hardware_opt_in': True,
        'hardware_archive': GPU_ARCHIVE, 'hardware_archive_pin': updates[GPU_ARCHIVE],
        'producer_manifest_sha256': shared.native_contract.canonical_sha(gpu),
        'retained_Game_and_Wine_FEX_rootfs_display_verified': True,
        'physical_hardware_renderer_validated': False, 'physical_performance_validated': False}
    require(set(runtime['files']) == set(donor['runtime_manifest']['files'])|ADDED_HELPERS|{GPU_ARCHIVE}, 'Runtime inventory additions differ')
    return client, runtime


def extract_and_repair(apk, donor, destination, commit, client_directory, gpu_directory):
    validate_retained_native(client_directory, donor); gpu = validate_gpu(gpu_directory, commit)
    base = builder(); current_java_sources(donor, ROOT/'out/no-generated-java'); destination.mkdir(parents=True)
    with zipfile.ZipFile(apk) as archive:
        require(retained.archive_inventory(archive) == set(donor['payloads'])|set(donor['retained_android_resources'])|{'AndroidManifest.xml', 'classes.dex'}, 'Unexpected donor inventory')
        for entry in archive.infolist():
            if entry.filename == 'AndroidManifest.xml' or entry.filename.startswith('META-INF/'): continue
            target = destination/entry.filename; target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open('xb') as output: shutil.copyfileobj(source, output, 1024*1024)
    require(all(base.file_pin(destination/name) == pin for name, pin in donor['payloads'].items()), 'Extracted donor bytes differ')
    assets = destination/'assets/runtime'
    for name in sorted(HELPERS|ADDED_HELPERS): shutil.copyfile(ROOT/'android/guest'/name, assets/name)
    shutil.copyfile(Path(gpu_directory)/GPU_ARCHIVE, assets/GPU_ARCHIVE)
    updates = {name: base.file_pin(assets/name) for name in sorted(HELPERS|ADDED_HELPERS|{GPU_ARCHIVE})}
    client, runtime = verification_manifests(donor, updates, commit, gpu)
    for name, value in (('client-manifest.json', client), ('runtime-manifest.json', runtime)): (assets/name).write_bytes(shared.encoded(value))
    payloads = {name: base.file_pin(destination/name) for name in sorted(set(donor['payloads'])|ADDED_PAYLOADS)}
    require({name for name in donor['payloads'] if payloads[name] != donor['payloads'][name]} == REPLACED_PAYLOADS
        and set(payloads)-set(donor['payloads']) == ADDED_PAYLOADS and len(payloads) == 77, 'Unexpected GPU payload replacement/addition')
    preflight = retained.verify_server_archives(assets)
    require(preflight == donor['server_payload_extraction_preflight'], 'Retained server extraction differs')
    return runtime, payloads, preflight


def verify_derivative(apk, donor, payloads, dex_pin, commit, client_directory, gpu_directory):
    validate_retained_native(client_directory, donor); gpu = validate_gpu(gpu_directory, commit); base = builder()
    require(set(payloads) == set(donor['payloads'])|ADDED_PAYLOADS and len(payloads) == 77
        and {name for name in donor['payloads'] if payloads[name] != donor['payloads'][name]} == REPLACED_PAYLOADS,
        'GPU profile payload boundaries differ')
    require(dex_pin != donor['recompiled_dex'], 'GPU selector/runtime shell did not recompile Java/DEX')
    base.verify_packaged_payloads(apk, payloads)
    with zipfile.ZipFile(apk) as archive:
        shell = {'classes.dex': dex_pin, **donor['retained_android_resources']}
        require(retained.archive_inventory(archive) == set(payloads)|set(shell)|{'AndroidManifest.xml'}, 'Unexpected candidate inventory')
        for name, pin in shell.items():
            raw = archive.read(name); require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == pin, 'DEX or retained resources differ')
        for name in HELPERS|ADDED_HELPERS:
            require(payloads['assets/runtime/'+name] == base.file_pin(ROOT/'android/guest'/name), 'Authored GPU helper differs')
        require(payloads['assets/runtime/'+GPU_ARCHIVE] == gpu['files'][GPU_ARCHIVE], 'GPU archive differs from qualified source producer')
        client, runtime = verification_manifests(donor,
            {name: payloads['assets/runtime/'+name] for name in sorted(HELPERS|ADDED_HELPERS|{GPU_ARCHIVE})}, commit, gpu)
        client_raw = archive.read('assets/runtime/client-manifest.json'); require(json.loads(client_raw) == client, 'Candidate client provenance differs')
        client_pin = {'bytes': len(client_raw), 'sha256': hashlib.sha256(client_raw).hexdigest()}
        require(client_pin == payloads['assets/runtime/client-manifest.json'], 'Embedded client byte pin differs')
        runtime['files']['client-manifest.json'] = client_pin
        require(json.loads(archive.read('assets/runtime/runtime-manifest.json')) == runtime, 'Runtime provenance differs')
        require(payloads['assets/runtime/client-runtime.zip'] == donor['payloads']['assets/runtime/client-runtime.zip'], 'Game/DLL/package bytes changed')
    require(retained.verify_apk_server_archives(apk) == donor['server_payload_extraction_preflight'], 'Candidate server extraction differs')
    return runtime


def validate_qualification(receipt, commit):
    require(receipt.get('format') == 1 and receipt.get('status') == 'passed' and receipt.get('scope') == QUALIFICATION_SCOPE
        and receipt.get('repository_commit') == commit and receipt.get('runtime_repository_commit') == commit
        and receipt.get('donor') == donor_link() and set(receipt.get('checks', {})) == set(CHECKS)
        and all(value is True for value in receipt['checks'].values())
        and all(receipt.get(key) is False for key in FALSE_FLAGS)
        and all(receipt.get(key) is True for key in ('native_client_package_reused', 'retained_native_source_and_Win32_proof_verified',
            'gpu_runtime_produced_in_current_run', 'java_or_dex_recompiled', 'guest_helpers_changed',
            'runtime_manifest_changed', 'runtime_refresh_required', 'graphics_driver_changed'))
        and receipt.get('installed_runtime_identity_preserved') is False,
        'Exact source-bound optional GPU profile qualification required')
    contract = module('client_gpu_profile_qualification_contract', ROOT/QUALIFICATION_SCRIPT)
    contract.validate_suite_inventory(); suites = receipt.get('test_suites', {})
    require(set(suites) == set(contract.TEST_MODULES) and receipt.get('check_suites') == contract.CHECK_SUITES
        and all(item.get('status') == 'passed' and item.get('skipped') == 0 and type(item.get('tests_run')) is int and item['tests_run'] > 0
            for item in suites.values()) and receipt.get('tests_run') == sum(item['tests_run'] for item in suites.values()), 'Complete retained and new unskipped suite inventory required')
    require(SOURCE_FILES <= set(receipt.get('source_files', {})), 'Current GPU-profile source closure incomplete')
    for name, pin in receipt['source_files'].items():
        require(isinstance(name, str) and not Path(name).is_absolute() and '..' not in Path(name).parts and chr(92) not in name, 'Unsafe source path')
        builder().checked_file(ROOT/name, pin)
    require(receipt.get('postgresql_emission_fixtures') == ['cancelled_child_deletion_commits', 'delete_insert_replacement_commits', 'duplicate_insert_23505_rollback']
        and receipt.get('postgresql_levelup_fixtures') == sorted(retained.levelup_postgresql_fixtures()), 'All seven real PostgreSQL fixtures required')
    return receipt


def build(args):
    base, current = builder(), builder(repaired=True); commit = base.source_commit(args.repository_commit)
    donor = validate_donor(args.donor_apk, args.donor_build_report, args.client_directory)
    q = validate_qualification(read_json(args.qualification), commit)
    native = validate_retained_native(args.client_directory, donor)
    gpu = validate_gpu(args.gpu_directory, commit)
    require(q.get('native_client_renderer_attribution') == native and q.get('client_gpu_runtime') == gpu, 'Qualified retained Game/GPU package differs')
    password = base.signing_password_spec(args.password_env)
    base.verify_signing_identity(args.keystore, 'coh-client-interactive', SIGNER, password)
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), 'Fresh optional GPU APK required')
    base.checked_file(args.testing_notes); require(0 < args.testing_notes.stat().st_size <= 65536, 'Bounded notes required')
    for tool in (args.android_jar, args.build_tools/'aapt2', args.build_tools/'zipalign', args.build_tools/'lib/d8.jar', args.build_tools/'lib/apksigner.jar'):
        require(tool.is_file() and not tool.is_symlink(), 'Required Android tool missing')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-client-gpu-profile-', dir=args.output.parent) as temporary:
        work = Path(temporary); runtime, payloads, preflight = extract_and_repair(args.donor_apk, donor, work/'donor', commit, args.client_directory, args.gpu_directory)
        classes, generated, dex = (work/name for name in ('classes', 'generated', 'dex'))
        for folder in (classes, generated, dex): folder.mkdir()
        current_java_sources(donor, generated)
        manifest = work/'AndroidManifest.xml'; repair_android_manifest(ROOT/'android/interactive/src/main/AndroidManifest.xml', manifest)
        resources, unsigned, aligned, signed = (work/name for name in ('resources.zip', 'unsigned.apk', 'aligned.apk', 'signed.apk'))
        base.run(args.build_tools/'aapt2', 'compile', '--dir', ROOT/'android/interactive/src/main/res', '-o', resources)
        base.run(args.build_tools/'aapt2', 'link', '-I', args.android_jar, '--manifest', manifest, '--min-sdk-version', '26', '--target-sdk-version', '35', '--java', generated, resources, '-o', unsigned)
        with zipfile.ZipFile(unsigned) as archive:
            require(retained.archive_inventory(archive) == {'AndroidManifest.xml', 'resources.arsc', 'res/drawable/ic_coh_client.xml'}, 'Generated Android inventory differs')
            for name, pin in donor['retained_android_resources'].items():
                raw = archive.read(name); require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == pin, 'Android resources changed beyond version')
        require({path.relative_to(generated).as_posix() for path in generated.rglob('*.java')} == {base.APP_ID.replace('.', '/')+'/R.java'}, 'Unexpected generated Java source')
        sources, java, changed = current_java_sources(donor, generated)
        require(q.get('java_sources') == java and q.get('changed_java_sources') == changed, 'Java changed after qualification')
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
        certificate = retained.verify_signature(signed, args.build_tools); base.run(args.build_tools/'zipalign', '-c', '4', signed)
        current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', signed))
        verify_derivative(signed, donor, payloads, dex_pin, commit, args.client_directory, args.gpu_directory); retained.verify_binary_manifest(signed, args.donor_apk, args.build_tools)
        shutil.copyfile(signed, args.output)
        report = {'format': 1, 'apk': APK_NAME, **base.file_pin(args.output), 'repository_commit': commit,
            'runtime_repository_commit': commit, 'retained_runtime_repository_commit': donor['runtime_repository_commit'],
            'retained_native_repository_commit': donor['runtime_repository_commit'], 'application_id': base.APP_ID,
            'version_name': VERSION_NAME, 'version_code': VERSION_CODE, 'abi': 'arm64-v8a', 'scope': QUALIFICATION_SCOPE,
            'donor': donor_link(), 'signer_certificate_sha256': certificate, 'signing_key_created': False,
            'signature_verified': True, 'package_badging_verified': True, 'binary_manifest_version_only_verified': True,
            'payload_bytes_verified': True, 'payloads': payloads, 'changed_apk_payloads': sorted(REPLACED_PAYLOADS), 'replaced_apk_payloads': sorted(REPLACED_PAYLOADS),
            'added_apk_payloads': sorted(ADDED_PAYLOADS), 'baseline_payloads_verified': 75, 'retained_baseline_payloads_verified': 75-len(REPLACED_PAYLOADS),
            'recompiled_dex': dex_pin, 'donor_dex': donor['recompiled_dex'], 'java_sources': java,
            'changed_java_sources': changed, 'added_java_sources': [], 'retained_java_sources_verified': 19-len(JAVA_CHANGES),
            'generated_manifest': base.file_pin(manifest), 'qualification': q,
            'qualification_receipt': base.file_pin(args.qualification), 'testing_notes': base.file_pin(args.testing_notes),
            'java_or_dex_recompiled': True, 'installed_runtime_identity_preserved': False,
            'previous_runtime_generation_retained': True, 'native_client_package_reused': True,
            'native_client_renderer_attribution': native,
            'native_client_recompiled': False, 'native_client_compiled_in_current_run': False,
            'retained_native_source_and_Win32_proof_verified': True, 'client_gpu_runtime': gpu,
            'gpu_runtime_produced_in_current_run': True, 'graphics_driver_changed': True,
            'guest_helpers_changed': True, 'runtime_manifest_changed': True, 'runtime_refresh_required': True,
            'runtime_manifest': runtime, 'runtime_manifest_sha256': payloads['assets/runtime/runtime-manifest.json']['sha256'],
            'setup_memory_guards_preserved': True,
            'all_published_visual_resources_retained': True, **{key: False for key in FALSE_FLAGS},
            **{name: donor[name] for name in RETAINED_RECEIPT_FIELDS}}
        (args.output.parent/REPORT_NAME).write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
    shutil.copyfile(args.testing_notes, args.output.parent/NOTES_NAME)
    args.output.with_suffix('.apk.sha256').write_text(report['sha256']+'  '+APK_NAME+'\n')
    verify_report(argparse.Namespace(**vars(args), apk=args.output, build_report=args.output.parent/REPORT_NAME), commit)
    print('Qualified optional GPU profile APK:', args.output, report['sha256']); return report



def verify_report(args, commit):
    donor = validate_donor(args.donor_apk, args.donor_build_report, args.client_directory)
    base, current = builder(), builder(repaired=True); q = validate_qualification(read_json(args.qualification), commit)
    native = validate_retained_native(args.client_directory, donor); gpu = validate_gpu(args.gpu_directory, commit)
    report = read_json(args.build_report); _, java, changed = current_java_sources(donor, ROOT/'out/no-generated-java')
    require(report.get('format') == 1 and report.get('apk') == APK_NAME and report.get('repository_commit') == commit
        and report.get('runtime_repository_commit') == commit and report.get('retained_runtime_repository_commit') == DONOR_COMMIT
        and report.get('retained_native_repository_commit') == DONOR_COMMIT and report.get('donor') == donor_link()
        and report.get('scope') == QUALIFICATION_SCOPE and report.get('application_id') == base.APP_ID
        and report.get('version_name') == VERSION_NAME and report.get('version_code') == VERSION_CODE and report.get('abi') == 'arm64-v8a'
        and report.get('signer_certificate_sha256') == SIGNER and report.get('signing_key_created') is False
        and report.get('qualification') == q and report.get('qualification_receipt') == base.file_pin(args.qualification)
        and report.get('native_client_renderer_attribution') == native == q.get('native_client_renderer_attribution')
        and report.get('client_gpu_runtime') == gpu == q.get('client_gpu_runtime')
        and report.get('java_sources') == q.get('java_sources') == java and report.get('changed_java_sources') == q.get('changed_java_sources') == changed
        and report.get('added_java_sources') == [] and report.get('retained_java_sources_verified') == 19-len(JAVA_CHANGES)
        and report.get('donor_dex') == donor['recompiled_dex']
        and report.get('changed_apk_payloads') == sorted(REPLACED_PAYLOADS) and report.get('replaced_apk_payloads') == sorted(REPLACED_PAYLOADS)
        and report.get('added_apk_payloads') == sorted(ADDED_PAYLOADS) and len(report.get('payloads', {})) == 77
        and report.get('baseline_payloads_verified') == 75 and report.get('retained_baseline_payloads_verified') == 75-len(REPLACED_PAYLOADS)
        and all(report.get(key) is True for key in ('signature_verified', 'package_badging_verified', 'binary_manifest_version_only_verified',
            'payload_bytes_verified', 'java_or_dex_recompiled', 'previous_runtime_generation_retained',
            'native_client_package_reused', 'retained_native_source_and_Win32_proof_verified', 'gpu_runtime_produced_in_current_run',
            'guest_helpers_changed', 'runtime_manifest_changed', 'runtime_refresh_required', 'graphics_driver_changed',
            'setup_memory_guards_preserved', 'all_published_visual_resources_retained'))
        and report.get('installed_runtime_identity_preserved') is False and all(report.get(key) is False for key in FALSE_FLAGS)
        and all(report.get(name) == donor[name] for name in RETAINED_RECEIPT_FIELDS), 'Optional GPU profile build receipt differs')
    base.checked_file(args.apk, report)
    runtime = verify_derivative(args.apk, donor, report['payloads'], report['recompiled_dex'], commit, args.client_directory, args.gpu_directory)
    require(report.get('runtime_manifest') == runtime and report.get('runtime_manifest_sha256') == report['payloads']['assets/runtime/runtime-manifest.json']['sha256'], 'Runtime provenance differs')
    retained.verify_binary_manifest(args.apk, args.donor_apk, args.build_tools); retained.verify_signature(args.apk, args.build_tools)
    base.run(args.build_tools/'zipalign', '-c', '4', args.apk)
    current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', args.apk))
    checksum = args.apk.with_suffix('.apk.sha256'); require(checksum.read_text() == report['sha256']+'  '+APK_NAME+'\n', 'Checksum differs')
    notes = args.apk.parent/NOTES_NAME; base.checked_file(notes, report['testing_notes']); base.checked_file(args.testing_notes, report['testing_notes'])
    return report, checksum, notes


def require_current_release_head(api, commit):
    return previous.require_current_release_head(api, commit)


def publish_release(api, report, assets, notes):
    require(tuple(path.name for path in assets) == (APK_NAME, APK_NAME+'.sha256', NOTES_NAME), 'Unexpected release assets')
    builder().checked_file(assets[0], report)
    for path in ('/releases/tags/'+RELEASE_TAG, '/git/ref/tags/'+RELEASE_TAG):
        try: existing = api.request(path)
        except urllib.error.HTTPError as error:
            if error.code != 404: raise
        else:
            require(not path.startswith('/releases/'), 'Existing release is never replaced')
            require(existing.get('object', {}).get('type') == 'commit' and existing['object'].get('sha') == report['repository_commit'], 'Existing tag points elsewhere')
    require_current_release_head(api, report['repository_commit'])
    release = api.request('/releases', {'tag_name': RELEASE_TAG, 'target_commitish': report['repository_commit'],
        'name': 'COH Atlas Gameplay 0.13.20 — optional probed GPU profile',
        'body': notes+'\n\nAPK SHA-256: `'+report['sha256']+'`.\n[Hosted qualification](https://github.com/'+REPOSITORY+'/actions/runs/'+os.environ.get('GITHUB_RUN_ID', '')+').\n',
        'draft': True, 'prerelease': True, 'generate_release_notes': False, 'make_latest': 'false'}, method='POST')
    require(type(release.get('id')) is int and release.get('draft') is True and release.get('tag_name') == RELEASE_TAG, 'Unexpected release')
    for path in assets:
        uploaded = api.request('/releases/'+str(release['id'])+'/assets?'+urllib.parse.urlencode({'name': path.name}), path, method='POST', upload=True)
        pin = builder().file_pin(path)
        require(uploaded.get('state') == 'uploaded' and uploaded.get('name') == path.name and uploaded.get('size') == pin['bytes']
            and uploaded.get('digest') == 'sha256:'+pin['sha256'], 'Release upload differs')
    require_current_release_head(api, report['repository_commit'])
    published = api.request('/releases/'+str(release['id']), {'draft': False, 'prerelease': True, 'make_latest': 'false'}, method='PATCH')
    require(published.get('id') == release['id'] and published.get('draft') is False and published.get('prerelease') is True
        and published.get('tag_name') == RELEASE_TAG, 'Publication incomplete')
    return published.get('html_url')


def publish(args):
    require(os.environ.get('GITHUB_REPOSITORY') == REPOSITORY and os.environ.get('GITHUB_REF') == 'refs/heads/'+BRANCH
        and os.environ.get('GITHUB_EVENT_NAME') in ('push', 'workflow_dispatch'), 'Publication requires continuation branch')
    commit = builder().source_commit(os.environ.get('GITHUB_SHA')); report, checksum, notes = verify_report(args, commit)
    api = module('client_gpu_profile_github', Path(__file__).with_name('build_atlas_gameplay_apk.py'))
    print('Published optional GPU prerelease:', publish_release(api.GitHub(os.environ.get('GH_TOKEN')), report, (args.apk, checksum, notes), notes.read_text()))


def main():
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest='command', required=True)
    fetch = commands.add_parser('download-donor'); fetch.add_argument('--output', type=Path, required=True)
    for name in ('build', 'audit', 'publish'):
        command = commands.add_parser(name)
        for argument in ('donor-apk', 'donor-build-report', 'qualification', 'build-tools', 'client-directory', 'gpu-directory'):
            command.add_argument('--'+argument, type=Path, required=True)
        command.add_argument('--testing-notes', type=Path, default=NOTES)
        command.add_argument('--repository-commit', default=os.environ.get('GITHUB_SHA'))
        if name == 'build':
            command.add_argument('--android-jar', type=Path, required=True); command.add_argument('--keystore', type=Path, required=True)
            command.add_argument('--password-env', default='COH_INTERACTIVE_KEYSTORE_PASSWORD'); command.add_argument('--output', type=Path, required=True)
        else:
            command.add_argument('--apk', type=Path, required=True); command.add_argument('--build-report', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'download-donor': download(args)
    elif args.command == 'build': build(args)
    elif args.command == 'publish': publish(args)
    else: print('Public candidate verified:', verify_report(args, builder().source_commit(args.repository_commit))[0]['sha256'])


if __name__ == '__main__': main()
