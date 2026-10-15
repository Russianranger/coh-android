#!/usr/bin/env python3
"""Conserve the accepted 0.13.17 APK with a bounded 30 FPS native Game profile."""
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

import build_client_scene_performance_apk as previous
import build_client_startup_followup_apk as startup
import package_client_gameplay_performance_native as native_producer

ROOT, require, module, shared = previous.ROOT, previous.require, previous.module, previous.shared
REPOSITORY, BRANCH, SIGNER = previous.REPOSITORY, previous.BRANCH, previous.SIGNER
retained = previous.previous.previous.previous.prior
DONOR_COMMIT = 'd41aab3dd1a2f169a0ec71ff47d56767a8eb65e5'
DONOR_RUN_ID = 37559820885
DONOR_APK_NAME = 'COH-Atlas-Gameplay-0.13.16.apk'
DONOR_APK = {'bytes': 1557359204, 'sha256': 'ddb1f26913291295248cd4195d0184c02b24849921a6b47fda391dd7af26c7d7'}
DONOR_BUILD = {'bytes': 4994538, 'sha256': '1135803a6a5bb68364d2baa3d94e7e4bbd148d0e7840fdc8b8a67e46c456bad6'}
DONOR_URL = 'https://github.com/'+REPOSITORY+'/releases/download/coh-atlas-gameplay-v0.13.16/'+DONOR_APK_NAME
VERSION_NAME, VERSION_CODE = '0.13.17', 32
APK_NAME, REPORT_NAME = 'COH-Atlas-Gameplay-0.13.17.apk', 'client-gameplay-performance-apk-build-report.json'
NOTES_NAME = 'COH-Atlas-Gameplay-0.13.17-testing.txt'
NOTES = ROOT/'docs'/NOTES_NAME
RELEASE_TAG = 'coh-atlas-gameplay-v0.13.17'
WORKFLOW = '.github/workflows/android-client-gameplay-performance.yml'
QUALIFICATION_SCRIPT = 'tools/android/interactive/qualify_client_gameplay_performance.py'
QUALIFICATION_SCOPE = 'native_gameplay_30fps_and_bounded_texture_diagnostics_retaining_public_0_13_16'
HELPERS = frozenset({'client_interactive_diagnostic.py', 'native_responsiveness_contract.py',
    'client_startup_diagnostic.py', 'texture_header_index.py'})
REPLACED_PAYLOADS = frozenset('assets/runtime/'+name for name in HELPERS|{'client-runtime.zip', 'client-manifest.json', 'runtime-manifest.json'})
ADDED_PAYLOADS = frozenset()
CHECKS = ('native_gameplay_profile_texture_diagnostics_and_guest_controls_verified',
    'retained_ui_beacon_gameplay_postgresql_and_recovery_guards_verified',
    'exact_game_only_payload_shell_source_and_server_extraction_verified')
ACTUAL_NATIVE_ANCESTRY_CHECKS = {'status': 'passed', 'actual_external_donor_and_win32_receipts_verified': True,
    'full_guest_typed_client_wrapper_verified': True, 'older_native_history_unchanged': True,
    'actual_scene_Game_predecessor_verified': True,
    'raw_source_histories_preserved': True, 'rejected_foreign_variants': ['pg_header', 'pg_fixture',
        'pg_extra', 'pg_patch', 'event_source', 'texture', 'event_bool', 'event_float', 'pg_digest', 'game_digest', 'progress_digest']}
SOURCE_FILES = frozenset({WORKFLOW, QUALIFICATION_SCRIPT,
    'tools/android/interactive/build_client_gameplay_performance_apk.py',
    'tools/android/interactive/test_client_gameplay_performance_package.py',
    *native_producer.SOURCE_FILES,
    'tools/android/interactive/test_client_gameplay_performance_contract.py',
    'tools/android/interactive/test_client_preload_launch.py',
    'tools/android/interactive/analyze_thor_performance.py',
    'tools/android/interactive/test_thor_performance_report.py',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'docs/COH-PERFORMANCE-0.13.17.md', 'docs/'+NOTES_NAME,
    'docs/android-evidence/performance-0.13.16-thor-20261007.json',
    *('android/guest/'+name for name in HELPERS)})
# Frozen predecessor source pins stay exact except the enumerated new helper,
# qualification, dispatch ownership, and reviewed documentation changes.
REVIEWED_DONOR_SOURCE_CHANGES = frozenset(name for name in SOURCE_FILES
    if not name.startswith('upstream/')) | frozenset({
    'docs/COH-PERFORMANCE-0.13.16.md', 'docs/HANDOFF.md',
    'docs/android-evidence/performance-0.13.16-publication.json'})
FALSE_FLAGS = ('native_dbserver_recompiled', 'native_mapserver_recompiled',
    'java_or_dex_recompiled', 'physical_gameplay_validated', 'physical_client_timing_validated',
    'physical_visual_assets_validated', 'asset_reimport_required', 'world_assets_changed',
    'prepared_cache_archive_changed', 'graphics_driver_changed', 'wine_or_fex_changed')


def builder(*, repaired=False):
    base = previous.builder()
    if repaired: base.VERSION_NAME, base.VERSION_CODE, base.APK_NAME = VERSION_NAME, VERSION_CODE, APK_NAME
    return base


def read_json(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= 256*1024**2,
        'Missing linked or unbounded performance receipt: '+path.name)
    return json.loads(path.read_bytes())


def donor_link():
    return {'run_id': DONOR_RUN_ID, 'repository_commit': DONOR_COMMIT, 'apk': DONOR_APK, 'build_report': DONOR_BUILD}


def validate_donor_receipt(path):
    builder().checked_file(path, DONOR_BUILD); donor = read_json(path); q = donor.get('qualification', {})
    require(donor.get('format') == 1 and donor.get('repository_commit') == DONOR_COMMIT
        and donor.get('runtime_repository_commit') == DONOR_COMMIT and donor.get('apk') == DONOR_APK_NAME
        and {key: donor.get(key) for key in DONOR_APK} == DONOR_APK
        and donor.get('application_id') == builder().APP_ID and donor.get('version_name') == '0.13.16'
        and donor.get('version_code') == 31 and donor.get('abi') == 'arm64-v8a'
        and donor.get('signer_certificate_sha256') == SIGNER and donor.get('signing_key_created') is False
        and all(donor.get(key) is True for key in ('signature_verified', 'package_badging_verified',
            'binary_manifest_version_only_verified', 'payload_bytes_verified', 'setup_memory_guards_preserved'))
        and len(donor.get('payloads', {})) == 75 and len(donor.get('java_sources', {})) == 19
        and q.get('status') == 'passed' and q.get('scope') == previous.QUALIFICATION_SCOPE
        and q.get('repository_commit') == DONOR_COMMIT and q.get('tests_run') == 1163
        and len(q.get('source_files', {})) == 9615 and len(q.get('test_suites', {})) == 76
        and all(item.get('status') == 'passed' and item.get('skipped') == 0 for item in q['test_suites'].values())
        and donor.get('server_payload_extraction_preflight', {}).get('status') == 'passed'
        and donor.get('native_client_scene_performance', {}).get('files')
            == {'CityOfHeroes.exe': native_producer.BASE_GAME}
        and q.get('native_client_scene_performance') == donor.get('native_client_scene_performance'),
        'Exact physically accepted public 0.13.16 donor receipt differs')
    return donor


def validate_retained_sources(donor):
    for name, pin in donor['qualification']['source_files'].items():
        require(isinstance(name, str) and not Path(name).is_absolute() and '..' not in Path(name).parts
            and chr(92) not in name, 'Unsafe retained source path')
        if name not in REVIEWED_DONOR_SOURCE_CHANGES: builder().checked_file(ROOT/name, pin)


def validate_donor(apk, receipt):
    base = builder(); base.checked_file(apk, DONOR_APK); donor = validate_donor_receipt(receipt)
    base.verify_packaged_payloads(apk, donor['payloads'])
    with zipfile.ZipFile(apk) as archive:
        shell = {'classes.dex': donor['retained_dex'], **donor['retained_android_resources']}
        require(retained.archive_inventory(archive) == set(donor['payloads'])|set(shell)|{'AndroidManifest.xml'},
            'Unexpected public donor inventory')
        for name, pin in shell.items():
            raw = archive.read(name)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == pin, 'Donor Android shell differs')
        require(json.loads(archive.read('assets/runtime/runtime-manifest.json')) == donor['runtime_manifest'],
            'Donor runtime provenance differs')
        donor['_client_verification'] = json.loads(archive.read('assets/runtime/client-manifest.json'))
        for name in HELPERS: donor.setdefault('_helper_sources', {})[name] = archive.read('assets/runtime/'+name)
        with archive.open('assets/runtime/client-runtime.zip') as source, tempfile.TemporaryFile() as target:
            shutil.copyfileobj(source, target, 1024*1024); target.seek(0)
            with zipfile.ZipFile(target) as client:
                donor['_native_client_manifest'] = json.loads(client.read('client-package.json'))
                donor['_client_members'] = startup.startup.client_member_pins(client)
                shared.native_contract.client_contract(donor['_native_client_manifest'],
                    donor['immutable_donor_provenance']['native_responsiveness'])
                require(donor['_native_client_manifest'].get('client_scene_performance', {}).get('manifest')
                    == donor['native_client_scene_performance']
                    and len(donor['_client_members']) == 22
                    and donor['_client_members']['CityOfHeroes.exe'] == {'bytes': native_producer.BASE_GAME['size'],
                        'sha256': native_producer.BASE_GAME['sha256']}, 'Accepted donor Game provenance or bytes differ')
    require(retained.verify_apk_server_archives(apk) == donor['server_payload_extraction_preflight'],
        'Donor actual server extraction differs')
    validate_retained_sources(donor)
    return donor


def current_sources(donor):
    base = builder(); sources = retained.retained.java_sources(base, ROOT/'out/no-generated-java')
    pins = {path.relative_to(ROOT).as_posix(): base.file_pin(path) for path in sources if path.is_relative_to(ROOT)}
    require(len(pins) == 19 and pins == donor['java_sources'], 'All 19 authored Java sources must remain exact')
    for name, pin in donor['preserved_sources'].items(): base.checked_file(ROOT/name, pin)
    base.checked_file(ROOT/'android/interactive/src/main/AndroidManifest.xml', donor['source_manifest'])
    for name, pin in donor['payloads'].items():
        if name.startswith('assets/runtime/') and (name.endswith('.py') or name.endswith('/task-gate.json')):
            if Path(name).name not in HELPERS: base.checked_file(ROOT/'android/guest'/Path(name).name, pin)
    require({name for name in HELPERS if base.file_pin(ROOT/'android/guest'/name) != donor['payloads']['assets/runtime/'+name]} == HELPERS,
        'Exactly the reviewed performance guest helpers must change')
    validate_retained_sources(donor)
    return pins


def validate_native(directory, commit, donor):
    native = native_producer.validate_package(directory, commit)
    if os.environ.get('GITHUB_RUN_ID'):
        require(native.get('run_url') == 'https://github.com/'+REPOSITORY+'/actions/runs/'+os.environ['GITHUB_RUN_ID'],
            'Native Game must be compiled and qualified in this exact current run')
    provenance = donor['immutable_donor_provenance']
    validate_native_source_ancestry(native['retained_source_inputs'], provenance['native_responsiveness']['build_inputs'])
    require(native['base_client_executable'] == donor['native_client_scene_performance']['files']['CityOfHeroes.exe']
        and native['schema_sources_sha256'] == provenance['native_responsiveness']['retained_cache']['schema_sources_sha256']
        and native['build_input']['base_client_scene_performance_build_input']
            == donor['native_client_scene_performance']['build_input'], 'Native Game ancestry or cache schema differs')
    return native


def validate_native_source_ancestry(received, accepted):
    # Recompute every frozen source recipe independently for each raw history.
    # The guest comparison then permits only the enumerated PG checkout EOLs
    # and their three verified enclosing digests, without relabeling either.
    baseline = native_producer.base.base.base.base.baseline
    for inputs in (received, accepted):
        require(isinstance(inputs, dict) and set(inputs) == set(baseline.INPUTS),
            'Native Game retained source input inventory differs')
        for name, receipt in inputs.items():
            require(receipt == baseline.expected_source_receipt(name, receipt),
                'Native Game independently recomputed ancestry differs: '+name)
    return shared.native_contract.scene_source_inputs_equivalent(received, accepted)


def client_manifest(donor, native):
    expected = copy.deepcopy(donor['_native_client_manifest'])
    expected['files']['CityOfHeroes.exe'] = native['files']['CityOfHeroes.exe']
    expected['dependency_report'] = shared.dependency_report(expected['files'])
    require(not expected['dependency_report']['unresolved'], 'New Game imports exceed retained DLL closure')
    expected['client_gameplay_performance'] = {'manifest': native,
        'manifest_sha256': shared.native_contract.canonical_sha(native),
        'base_client_scene_performance_manifest_sha256': expected['client_scene_performance']['manifest_sha256'],
        'base_client_executable': copy.deepcopy(donor['_native_client_manifest']['files']['CityOfHeroes.exe'])}
    shared.native_contract.client_contract(expected, donor['immutable_donor_provenance']['native_responsiveness'])
    return expected


def replace_client_archive(path, donor, native, directory):
    require(builder().file_pin(path) == donor['payloads']['assets/runtime/client-runtime.zip'], 'Exact donor client archive required')
    output = path.with_suffix('.candidate.zip'); require(not output.exists(), 'Fresh native client archive staging required')
    expected = client_manifest(donor, native)
    with zipfile.ZipFile(path) as original, zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        require(startup.startup.client_member_pins(original) == donor['_client_members'], 'Donor native members differ')
        for entry in original.infolist():
            if entry.filename == 'client-package.json': archive.writestr(entry.filename, shared.encoded(expected))
            elif entry.filename == 'CityOfHeroes.exe': archive.write(directory/'CityOfHeroes.exe', entry.filename)
            else:
                with original.open(entry) as source, archive.open(entry.filename, 'w') as target:
                    shutil.copyfileobj(source, target, 1024*1024)
    output.replace(path); verify_client_archive(path, donor, native)


def verify_client_archive(path, donor, native):
    expected = client_manifest(donor, native)
    with zipfile.ZipFile(path) as archive:
        pins = startup.startup.client_member_pins(archive)
        require(set(pins) == set(donor['_client_members']) and len(pins) == 22, 'Native client archive inventory differs')
        require(json.loads(archive.read('client-package.json')) == expected, 'Native package wrapper differs')
        record = native['files']['CityOfHeroes.exe']
        require(pins['CityOfHeroes.exe'] == {'bytes': record['size'], 'sha256': record['sha256']}, 'Packaged native Game bytes differ')
        require(all(pins[name] == pin for name, pin in donor['_client_members'].items()
            if name not in ('CityOfHeroes.exe', 'client-package.json')), 'A retained client DLL or native dependency changed')
    return expected


def verification_manifests(donor, updates, commit, native):
    require(set(updates) == HELPERS|{'client-runtime.zip'}, 'Unexpected performance replacement inputs')
    client = copy.deepcopy(donor['_client_verification']); client['files'].update(updates)
    runtime = copy.deepcopy(donor['runtime_manifest']); runtime['files'].update(updates)
    encoded = shared.encoded(client)
    runtime['files']['client-manifest.json'] = {'bytes': len(encoded), 'sha256': hashlib.sha256(encoded).hexdigest()}
    runtime['repository_commit'] = commit; runtime['scope'] = QUALIFICATION_SCOPE
    runtime['client_gameplay_performance'] = {'format': 1, 'repository_commit': commit, 'donor_repository_commit': DONOR_COMMIT,
        'all_visual_beacon_server_and_android_payloads_retained': True,
        'physical_gameplay_validated': False, 'physical_timing_validated': False,
        'native_recompiled': True, 'native_manifest_sha256': shared.native_contract.canonical_sha(native),
        'changed_guest_helpers': sorted(HELPERS), 'replacement_scope': 'CityOfHeroes.exe_only'}
    require(set(client['files']) == set(donor['_client_verification']['files'])
        and set(runtime['files']) == set(donor['runtime_manifest']['files']), 'Runtime inventory must remain exact')
    return client, runtime


def extract_and_repair(apk, donor, destination, commit, client_directory):
    native = validate_native(client_directory, commit, donor)
    base = builder(); current_sources(donor); destination.mkdir(parents=True)
    with zipfile.ZipFile(apk) as archive:
        for entry in archive.infolist():
            if entry.filename == 'AndroidManifest.xml' or entry.filename.startswith('META-INF/'): continue
            require(entry.filename in set(donor['payloads'])|set(donor['retained_android_resources'])|{'classes.dex'}, 'Unexpected donor member')
            target = destination/entry.filename; target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open('xb') as output: shutil.copyfileobj(source, output, 1024*1024)
    require(all(base.file_pin(destination/name) == pin for name, pin in donor['payloads'].items()), 'Extracted donor bytes differ')
    assets = destination/'assets/runtime'
    for name in sorted(HELPERS): shutil.copyfile(ROOT/'android/guest'/name, assets/name)
    replace_client_archive(assets/'client-runtime.zip', donor, native, client_directory)
    updates = {name: base.file_pin(assets/name) for name in sorted(HELPERS|{'client-runtime.zip'})}
    client, runtime = verification_manifests(donor, updates, commit, native)
    for name, value in (('client-manifest.json', client), ('runtime-manifest.json', runtime)):
        (assets/name).write_bytes(shared.encoded(value))
    payloads = {name: base.file_pin(destination/name) for name in sorted(donor['payloads'])}
    require({name for name in payloads if payloads[name] != donor['payloads'][name]} == REPLACED_PAYLOADS,
        'Unexpected performance payload replacement')
    preflight = retained.verify_server_archives(assets)
    require(preflight == donor['server_payload_extraction_preflight'], 'Retained server extraction differs')
    return runtime, payloads, preflight


def verify_derivative(apk, donor, payloads, commit, client_directory):
    native = validate_native(client_directory, commit, donor)
    base = builder()
    require(set(payloads) == set(donor['payloads']) and
        {name for name in payloads if payloads[name] != donor['payloads'][name]} == REPLACED_PAYLOADS,
        'Candidate Game-only payload boundaries differ')
    base.verify_packaged_payloads(apk, payloads)
    with zipfile.ZipFile(apk) as archive:
        shell = {'classes.dex': donor['retained_dex'], **donor['retained_android_resources']}
        require(retained.archive_inventory(archive) == set(payloads)|set(shell)|{'AndroidManifest.xml'}, 'Unexpected candidate inventory')
        for name, pin in shell.items():
            raw = archive.read(name)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == pin, 'Retained Android shell differs')
        for name in HELPERS:
            require(payloads['assets/runtime/'+name] == base.file_pin(ROOT/'android/guest'/name), 'Authored performance helper differs')
        client, runtime = verification_manifests(donor,
            {name: payloads['assets/runtime/'+name] for name in sorted(HELPERS|{'client-runtime.zip'})}, commit, native)
        client_raw = archive.read('assets/runtime/client-manifest.json')
        require(json.loads(client_raw) == client, 'Candidate client provenance differs')
        client_pin = {'bytes': len(client_raw), 'sha256': hashlib.sha256(client_raw).hexdigest()}
        require(client_pin == payloads['assets/runtime/client-manifest.json'], 'Candidate embedded client byte pin differs')
        runtime['files']['client-manifest.json'] = client_pin
        require(json.loads(archive.read('assets/runtime/runtime-manifest.json')) == runtime, 'Candidate runtime provenance differs')
        with archive.open('assets/runtime/client-runtime.zip') as source, tempfile.TemporaryFile() as target:
            shutil.copyfileobj(source, target, 1024*1024); target.seek(0); verify_client_archive(target, donor, native)
    require(retained.verify_apk_server_archives(apk) == donor['server_payload_extraction_preflight'], 'Candidate server extraction differs')
    return runtime


def validate_qualification(receipt, commit):
    require(receipt.get('format') == 1 and receipt.get('status') == 'passed' and receipt.get('scope') == QUALIFICATION_SCOPE
        and receipt.get('repository_commit') == commit and receipt.get('donor') == donor_link()
        and set(receipt.get('checks', {})) == set(CHECKS) and all(value is True for value in receipt['checks'].values())
        and all(receipt.get(key) is False for key in FALSE_FLAGS)
        and receipt.get('native_client_recompiled') is True and receipt.get('native_client_compiled_in_current_run') is True
        and receipt.get('native_client_package_reused') is False
        and receipt.get('requested_gameplay_cap') == 30
        and receipt.get('diagnostic_only_texture_repeat_bounding') is True
        and receipt.get('actual_native_ancestry_validation') == ACTUAL_NATIVE_ANCESTRY_CHECKS,
        'Exact source-bound performance qualification required')
    contract = module('client_gameplay_performance_qualification_contract', ROOT/QUALIFICATION_SCRIPT)
    suites = receipt.get('test_suites', {})
    require(set(suites) == set(contract.TEST_MODULES) and receipt.get('check_suites') == contract.CHECK_SUITES
        and all(item.get('status') == 'passed' and item.get('skipped') == 0 and type(item.get('tests_run')) is int and item['tests_run'] > 0
            for item in suites.values()) and receipt.get('tests_run') == sum(item['tests_run'] for item in suites.values()), 'Complete unskipped suite inventory required')
    require(SOURCE_FILES <= set(receipt.get('source_files', {})), 'Current performance source closure incomplete')
    for name, pin in receipt['source_files'].items():
        require(isinstance(name, str) and not Path(name).is_absolute() and '..' not in Path(name).parts and chr(92) not in name, 'Unsafe source path')
        builder().checked_file(ROOT/name, pin)
    require(receipt.get('postgresql_emission_fixtures') == ['cancelled_child_deletion_commits', 'delete_insert_replacement_commits', 'duplicate_insert_23505_rollback']
        and receipt.get('postgresql_levelup_fixtures') == sorted(retained.levelup_postgresql_fixtures()), 'All seven real PostgreSQL fixtures required')
    return receipt


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


def build(args):
    base, current = builder(), builder(repaired=True); commit = base.source_commit(args.repository_commit)
    donor = validate_donor(args.donor_apk, args.donor_build_report); q = validate_qualification(read_json(args.qualification), commit)
    native = validate_native(args.client_directory, commit, donor)
    require(q.get('native_client_gameplay_performance') == native, 'Native package changed after qualification')
    java = current_sources(donor); password = base.signing_password_spec(args.password_env)
    base.verify_signing_identity(args.keystore, 'coh-client-interactive', SIGNER, password)
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), 'Fresh candidate APK required')
    base.checked_file(args.testing_notes); require(0 < args.testing_notes.stat().st_size <= 65536, 'Bounded notes required')
    for tool in (args.android_jar, args.build_tools/'aapt2', args.build_tools/'zipalign', args.build_tools/'lib/apksigner.jar'):
        require(tool.is_file() and not tool.is_symlink(), 'Required Android tool missing')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-client-gameplay-performance-', dir=args.output.parent) as temporary:
        work = Path(temporary); runtime, payloads, preflight = extract_and_repair(args.donor_apk, donor, work/'donor', commit, args.client_directory)
        manifest = work/'AndroidManifest.xml'; repair_android_manifest(ROOT/'android/interactive/src/main/AndroidManifest.xml', manifest)
        resources, unsigned, aligned, signed = (work/name for name in ('resources.zip', 'unsigned.apk', 'aligned.apk', 'signed.apk'))
        base.run(args.build_tools/'aapt2', 'compile', '--dir', ROOT/'android/interactive/src/main/res', '-o', resources)
        base.run(args.build_tools/'aapt2', 'link', '-I', args.android_jar, '--manifest', manifest, '--min-sdk-version', '26', '--target-sdk-version', '35', resources, '-o', unsigned)
        with zipfile.ZipFile(unsigned) as archive:
            require(retained.archive_inventory(archive) == {'AndroidManifest.xml', 'resources.arsc', 'res/drawable/ic_coh_client.xml'}, 'Generated Android inventory differs')
            for name, pin in donor['retained_android_resources'].items():
                raw = archive.read(name); require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == pin, 'Android resources changed beyond version')
        with zipfile.ZipFile(unsigned, 'a', zipfile.ZIP_DEFLATED) as archive:
            base.append_payloads(archive, [(work/'donor'/name, name) for name in sorted(payloads)]); archive.write(work/'donor/classes.dex', 'classes.dex')
        base.run(args.build_tools/'zipalign', '-f', '4', unsigned, aligned)
        base.run('java', '-jar', args.build_tools/'lib/apksigner.jar', 'sign', '--ks', args.keystore, '--ks-key-alias', 'coh-client-interactive', '--ks-pass', password, '--key-pass', password, '--out', signed, aligned)
        certificate = retained.verify_signature(signed, args.build_tools); base.run(args.build_tools/'zipalign', '-c', '4', signed)
        current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', signed))
        verify_derivative(signed, donor, payloads, commit, args.client_directory); retained.verify_binary_manifest(signed, args.donor_apk, args.build_tools)
        shutil.copyfile(signed, args.output)
        report = {'format': 1, 'apk': APK_NAME, **base.file_pin(args.output), 'repository_commit': commit,
            'runtime_repository_commit': commit, 'application_id': base.APP_ID, 'version_name': VERSION_NAME, 'version_code': VERSION_CODE,
            'abi': 'arm64-v8a', 'scope': QUALIFICATION_SCOPE, 'donor': donor_link(), 'signer_certificate_sha256': certificate,
            'signing_key_created': False, 'signature_verified': True, 'package_badging_verified': True,
            'binary_manifest_version_only_verified': True, 'payload_bytes_verified': True, 'payloads': payloads,
            'changed_apk_payloads': sorted(REPLACED_PAYLOADS), 'replaced_apk_payloads': sorted(REPLACED_PAYLOADS),
            'added_apk_payloads': [], 'baseline_payloads_verified': 75, 'retained_baseline_payloads_verified': 75-len(REPLACED_PAYLOADS),
            'java_sources': java, 'changed_java_sources': [], 'retained_dex': donor['retained_dex'],
            'retained_android_resources': donor['retained_android_resources'], 'preserved_sources': donor['preserved_sources'],
            'source_manifest': donor['source_manifest'], 'qualification': q, 'qualification_receipt': base.file_pin(args.qualification),
            'testing_notes': base.file_pin(args.testing_notes), **{key: False for key in FALSE_FLAGS},
            'native_client_recompiled': True, 'native_client_compiled_in_current_run': True,
            'native_client_package_reused': False, 'native_client_gameplay_performance': native,
            'requested_gameplay_cap': 30, 'diagnostic_only_texture_repeat_bounding': True,
            'runtime_refresh_required': True, 'previous_runtime_generation_retained': True, 'setup_memory_guards_preserved': True,
            'all_published_visual_resources_retained': True, 'server_payload_extraction_preflight': preflight,
            'runtime_manifest': runtime, 'runtime_manifest_sha256': payloads['assets/runtime/runtime-manifest.json']['sha256'],
            'immutable_donor_provenance': donor['immutable_donor_provenance']}
        (args.output.parent/REPORT_NAME).write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
    shutil.copyfile(args.testing_notes, args.output.parent/NOTES_NAME)
    args.output.with_suffix('.apk.sha256').write_text(report['sha256']+'  '+APK_NAME+'\n')
    verify_report(argparse.Namespace(**vars(args), apk=args.output, build_report=args.output.parent/REPORT_NAME), commit)
    print('Qualified native Game performance APK:', args.output, report['sha256']); return report


def verify_report(args, commit):
    donor = validate_donor(args.donor_apk, args.donor_build_report); base, current = builder(), builder(repaired=True)
    q = validate_qualification(read_json(args.qualification), commit); report = read_json(args.build_report)
    native = validate_native(args.client_directory, commit, donor)
    require(q.get('native_client_gameplay_performance') == native, 'Qualified native package differs')
    require(report.get('format') == 1 and report.get('apk') == APK_NAME and report.get('repository_commit') == commit
        and report.get('runtime_repository_commit') == commit and report.get('donor') == donor_link() and report.get('scope') == QUALIFICATION_SCOPE
        and report.get('application_id') == base.APP_ID and report.get('version_name') == VERSION_NAME and report.get('version_code') == VERSION_CODE
        and report.get('signer_certificate_sha256') == SIGNER and report.get('signing_key_created') is False
        and report.get('qualification') == q and report.get('qualification_receipt') == base.file_pin(args.qualification)
        and report.get('native_client_gameplay_performance') == native and report.get('native_client_recompiled') is True
        and report.get('native_client_compiled_in_current_run') is True and report.get('native_client_package_reused') is False
        and report.get('java_sources') == current_sources(donor) and report.get('changed_java_sources') == []
        and report.get('retained_dex') == donor['retained_dex'] and report.get('retained_android_resources') == donor['retained_android_resources']
        and report.get('preserved_sources') == donor['preserved_sources'] and report.get('source_manifest') == donor['source_manifest']
        and report.get('immutable_donor_provenance') == donor['immutable_donor_provenance']
        and report.get('requested_gameplay_cap') == 30 and report.get('diagnostic_only_texture_repeat_bounding') is True
        and report.get('changed_apk_payloads') == sorted(REPLACED_PAYLOADS) and report.get('replaced_apk_payloads') == sorted(REPLACED_PAYLOADS)
        and report.get('added_apk_payloads') == [] and report.get('baseline_payloads_verified') == 75
        and report.get('retained_baseline_payloads_verified') == 75-len(REPLACED_PAYLOADS)
        and all(report.get(key) is True for key in ('signature_verified', 'package_badging_verified', 'binary_manifest_version_only_verified',
            'payload_bytes_verified', 'runtime_refresh_required', 'previous_runtime_generation_retained', 'setup_memory_guards_preserved', 'all_published_visual_resources_retained'))
        and all(report.get(key) is False for key in FALSE_FLAGS), 'Performance build receipt differs')
    base.checked_file(args.apk, report); runtime = verify_derivative(args.apk, donor, report['payloads'], commit, args.client_directory)
    require(report.get('runtime_manifest') == runtime and report.get('runtime_manifest_sha256') == report['payloads']['assets/runtime/runtime-manifest.json']['sha256'], 'Runtime provenance differs')
    retained.verify_binary_manifest(args.apk, args.donor_apk, args.build_tools)
    retained.verify_signature(args.apk, args.build_tools)
    base.run(args.build_tools/'zipalign', '-c', '4', args.apk)
    current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', args.apk))
    checksum = args.apk.with_suffix('.apk.sha256'); require(checksum.read_text() == report['sha256']+'  '+APK_NAME+'\n', 'Checksum differs')
    notes = args.apk.parent/NOTES_NAME; base.checked_file(notes, report['testing_notes']); base.checked_file(args.testing_notes, report['testing_notes'])
    return report, checksum, notes


def require_current_release_head(api, commit):
    head = api.request('/git/ref/heads/'+BRANCH)
    require(isinstance(commit, str) and re.fullmatch(r'[0-9a-f]{40}', commit)
        and isinstance(head, dict) and head.get('ref') == 'refs/heads/'+BRANCH
        and head.get('object', {}).get('type') == 'commit' and head['object'].get('sha') == commit,
        'Publication candidate has been superseded by the current continuation branch head')


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
        'name': 'COH Atlas Gameplay 0.13.17 — 30 FPS profile and bounded texture diagnostics',
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
    api = module('client_gameplay_performance_github', Path(__file__).with_name('build_atlas_gameplay_apk.py'))
    print('Published performance prerelease:', publish_release(api.GitHub(os.environ.get('GH_TOKEN')), report, (args.apk, checksum, notes), notes.read_text()))


def main():
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest='command', required=True)
    fetch = commands.add_parser('download-donor'); fetch.add_argument('--output', type=Path, required=True)
    for name in ('build', 'audit', 'publish'):
        command = commands.add_parser(name)
        for argument in ('donor-apk', 'donor-build-report', 'qualification', 'build-tools', 'client-directory'):
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
