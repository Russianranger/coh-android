#!/usr/bin/env python3
"""Package 0.13.13's DbServer startup repair from the exact public 0.13.12 APK.

Every UI texture, Game, MapServer, DLL, cache and Android Java/DEX/resource stays
byte-identical. The existing typed DbServer producer and its guest witness are
qualified in this run; historical 0.13.12 publication evidence remains immutable.
"""
from __future__ import annotations
import argparse
import ast
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

import build_levelup_ui_repair_apk as prior

ROOT = prior.ROOT
require, module, shared = prior.require, prior.module, prior.shared
REPOSITORY, BRANCH, SIGNER = prior.REPOSITORY, prior.BRANCH, prior.SIGNER
DONOR_COMMIT = 'e552fadeb1f392ab2574be16df6b474933c8ed00'
DONOR_RUN_ID = 37315299321
DONOR_APK_NAME = 'COH-Atlas-Gameplay-0.13.12.apk'
DONOR_APK = {'bytes': 1535588715, 'sha256': 'ca692d986d7f8bf50d11be03348f07c436e7f3f1b6c5fab83e8ebe2bc932e749'}
DONOR_BUILD = {'bytes': 124125896, 'sha256': '6846719dcb007f74516c32ace836e5b54a43d90c6c93a48685f79eb22c004cea'}
DONOR_URL = 'https://github.com/'+REPOSITORY+'/releases/download/coh-atlas-gameplay-v0.13.12/'+DONOR_APK_NAME
VERSION_NAME, VERSION_CODE = '0.13.13', 28
APK_NAME = 'COH-Atlas-Gameplay-0.13.13.apk'
REPORT_NAME = 'reopen-startup-repair-apk-build-report.json'
NOTES_NAME = 'COH-Atlas-Gameplay-0.13.13-testing.txt'
NOTES = ROOT/'docs'/NOTES_NAME
RELEASE_TAG = 'coh-atlas-gameplay-v0.13.13'
WORKFLOW = '.github/workflows/android-reopen-startup-repair.yml'
QUALIFICATION_SCRIPT = 'tools/android/interactive/qualify_reopen_startup_repair.py'
QUALIFICATION_SCOPE = 'dbserver_reopen_startup_formatting_repair_with_exact_public_0_13_12_ui_client_and_android'
GUEST = 'local_character_server.py'
UPDATES = frozenset({GUEST, 'startup-dbserver.exe', 'startup-dbserver-manifest.json'})
REPLACED_PAYLOADS = frozenset('assets/runtime/'+name for name in UPDATES|{'client-manifest.json', 'runtime-manifest.json'})
SOURCE_FILES = frozenset({WORKFLOW, QUALIFICATION_SCRIPT,
    'tools/android/interactive/build_reopen_startup_repair_apk.py',
    'tools/android/interactive/test_reopen_startup_repair_package.py',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'patches/levelup-ui-repair/0001-pg-empty-row-witness.patch',
    'tools/android/interactive/package_levelup_ui_repair_dbserver.py',
    'tools/android/interactive/test_levelup_ui_repair_dbserver.py',
    'tools/android/interactive/test_levelup_ui_repair_contract.py',
    'tools/android/interactive/test_reopen_dbserver_thread_name.py',
    'tools/android/game/test_game_diagnostic.py',
    'android/guest/'+GUEST, 'docs/'+NOTES_NAME})
# Only these reviewed pre-existing sources may differ from the pinned donor.
REVIEWED_DONOR_SOURCE_CHANGES = SOURCE_FILES
CHECKS = ('native_startup_formatting_and_postgresql_contracts_verified',
    'all_public_ui_client_server_cache_and_android_payloads_retained',
    'current_typed_native_producer_and_guest_witness_verified',
    'retained_gameplay_save_training_and_preload_regressions_verified')
RETAINED_REPORT_FIELDS = tuple(name for name in prior.RETAINED_RECEIPT_FIELDS) + (
    'visual_package', 'visual_superset', 'visual_original_streams')


def builder(*, repaired=False):
    base = prior.builder()
    if repaired: base.VERSION_NAME, base.VERSION_CODE, base.APK_NAME = VERSION_NAME, VERSION_CODE, APK_NAME
    return base


def read_json(path):
    path = Path(path)
    limit = 256*1024**2 if path.name in (REPORT_NAME, 'levelup-ui-repair-apk-build-report.json', 'reopen-startup-repair-qualification.json') else 8*1024**2
    require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= limit,
        'Missing, linked or unbounded reopen receipt: '+path.name)
    return json.loads(path.read_text())


def donor_link():
    return {'run_id': DONOR_RUN_ID, 'repository_commit': DONOR_COMMIT, 'apk': DONOR_APK, 'build_report': DONOR_BUILD}


def validate_donor_receipt(path):
    builder().checked_file(path, DONOR_BUILD)
    donor = read_json(path); qualification = donor.get('qualification', {})
    require(donor.get('repository_commit') == DONOR_COMMIT and donor.get('runtime_repository_commit') == DONOR_COMMIT
        and donor.get('apk') == DONOR_APK_NAME and {key: donor.get(key) for key in DONOR_APK} == DONOR_APK
        and donor.get('application_id') == builder().APP_ID and donor.get('version_name') == '0.13.12'
        and donor.get('version_code') == 27 and donor.get('abi') == 'arm64-v8a'
        and donor.get('signer_certificate_sha256') == SIGNER and donor.get('signing_key_created') is False
        and all(donor.get(key) is True for key in ('signature_verified', 'package_badging_verified',
            'binary_manifest_version_only_verified', 'payload_bytes_verified', 'setup_memory_guards_preserved'))
        and len(donor.get('payloads', {})) == 72 and len(donor.get('java_sources', {})) == 19
        and qualification.get('scope') == prior.QUALIFICATION_SCOPE and qualification.get('status') == 'passed'
        and qualification.get('tests_run') == 962 and len(qualification.get('source_files', {})) == 6804
        and qualification.get('repository_commit') == DONOR_COMMIT and donor.get('donor') == prior.donor_link()
        and donor.get('native_dbserver') == donor.get('native_levelup_ui_repair')
        and donor.get('server_payload_extraction_preflight', {}).get('status') == 'passed',
        'Exact public 0.13.12 donor receipt differs')
    return donor


def validate_retained_sources(donor):
    pins = donor['qualification']['source_files']
    require(len(pins) == 6804, 'Published donor source closure differs')
    for name, pin in pins.items():
        require(isinstance(name, str) and not Path(name).is_absolute() and '..' not in Path(name).parts,
            'Unsafe donor source path')
        if name not in REVIEWED_DONOR_SOURCE_CHANGES: builder().checked_file(ROOT/name, pin)
    return sorted(set(pins)-REVIEWED_DONOR_SOURCE_CHANGES)


def validate_donor(apk, receipt):
    base = builder(); base.checked_file(apk, DONOR_APK)
    donor = validate_donor_receipt(receipt); base.verify_packaged_payloads(apk, donor['payloads'])
    with zipfile.ZipFile(apk) as archive:
        shell = {'classes.dex': donor['retained_dex'], **donor['retained_android_resources']}
        require(prior.archive_inventory(archive) == set(donor['payloads'])|set(shell)|{'AndroidManifest.xml'},
            'Unexpected donor APK inventory')
        for name, pin in shell.items():
            raw = archive.read(name)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == pin,
                'Donor Android shell differs: '+name)
        for name, field in (('runtime-manifest.json', 'runtime_manifest'),
                ('native-responsiveness.json', 'native_responsiveness'),
                ('server-animation-manifest.json', 'server_animation_manifest'),
                ('startup-dbserver-manifest.json', 'native_dbserver')):
            require(json.loads(archive.read('assets/runtime/'+name)) == donor[field], 'Donor provenance differs: '+name)
        donor['_client_verification'] = json.loads(archive.read('assets/runtime/client-manifest.json'))
        donor['_server_guest_source'] = archive.read('assets/runtime/'+GUEST)
    require(prior.verify_apk_server_archives(apk) == donor['server_payload_extraction_preflight'],
        'Public donor actual server extraction differs')
    validate_retained_sources(donor)
    return donor


def validate_guest_delta(previous, current):
    before, after = (ast.parse(raw.decode()) for raw in (previous, current))
    name = 'levelup_ui_repair_build_input'
    old = next((node for node in before.body if isinstance(node, ast.FunctionDef) and node.name == name), None)
    new = next((node for node in after.body if isinstance(node, ast.FunctionDef) and node.name == name), None)
    require(old is not None and new is not None and ast.dump(old) != ast.dump(new), 'Producer witness must change')
    after.body[after.body.index(new)] = copy.deepcopy(old)
    installer = next((node for node in after.body if isinstance(node, ast.FunctionDef)
        and node.name == 'install_manual_atlas_dbserver'), None)
    changed = [name]
    if installer is not None:
        expected = ast.parse("installed['startup_thread_name'] = value['levelup_ui_repair_build_input']['startup_thread_name_contract']").body[0]
        found = 0
        for node in ast.walk(installer):
            for field, children in ast.iter_fields(node):
                if isinstance(children, list):
                    matching = [child for child in children if isinstance(child, ast.Assign)
                        and ast.dump(child, include_attributes=False) == ast.dump(expected, include_attributes=False)]
                    for child in matching: children.remove(child); found += 1
        require(found == 1, 'Installer must add exactly the typed startup diagnostic field')
        changed.append('install_manual_atlas_dbserver')
    require(ast.dump(before, include_attributes=False) == ast.dump(after, include_attributes=False),
        'Guest changes outside reviewed native producer witness')
    return {'changed_functions': sorted(changed), 'all_other_ast_nodes_retained': True}


def current_sources(donor):
    base = builder(); sources = prior.retained.java_sources(base, ROOT/'out/no-generated-java')
    pins = {path.relative_to(ROOT).as_posix(): base.file_pin(path) for path in sources if path.is_relative_to(ROOT)}
    require(len(pins) == 19 and pins == donor['java_sources'], 'Retain all19 memory-protected Java sources')
    for name, pin in donor['preserved_sources'].items(): base.checked_file(ROOT/name, pin)
    base.checked_file(ROOT/'android/interactive/src/main/AndroidManifest.xml', donor['source_manifest'])
    for name, pin in donor['payloads'].items():
        if name.startswith('assets/runtime/') and (name.endswith('.py') or name.endswith('/task-gate.json')):
            if Path(name).name != GUEST: base.checked_file(ROOT/'android/guest'/Path(name).name, pin)
    validate_guest_delta(donor['_server_guest_source'], (ROOT/'android/guest'/GUEST).read_bytes())
    validate_retained_sources(donor)
    return pins


def validate_native(directory, commit, donor):
    native = prior.native_builder().validate_package(directory, commit)
    require(native['files']['DbServer.exe'] != donor['native_dbserver']['files']['DbServer.exe'],
        'Startup repair must freshly replace the failing DbServer')
    for name in ('role', 'build_input', 'startup_bundle_build_input', 'retained_normal_files',
            'base_package_manifest_sha256', 'base_normal_executable', 'base_startup_executable',
            'base_startup_bundle_executable', 'base_normal_cmake_cache_sha256'):
        require(native[name] == donor['native_dbserver'][name], 'Native startup repair changed ancestry: '+name)
    return native


def verification_manifests(donor, updates, commit, native):
    require(set(updates) == UPDATES, 'Unexpected startup replacement inputs')
    client = copy.deepcopy(donor['_client_verification']); client['files'].update(updates)
    runtime = copy.deepcopy(donor['runtime_manifest']); runtime['files'].update(updates)
    encoded = shared.encoded(client)
    runtime['files']['client-manifest.json'] = {'bytes': len(encoded), 'sha256': hashlib.sha256(encoded).hexdigest()}
    runtime['repository_commit'] = commit
    runtime['reopen_startup_repair'] = {'format': 1, 'repository_commit': commit,
        'donor_repository_commit': DONOR_COMMIT, 'native_dbserver_recompiled': True,
        'native_client_recompiled': False, 'native_mapserver_recompiled': False,
        'native_manifest_sha256': shared.native_contract.canonical_sha(native),
        'all_published_ui_resources_retained': True, 'physical_reopen_validated': False}
    runtime['scope'] = QUALIFICATION_SCOPE
    require(set(client['files']) == set(donor['_client_verification']['files']) and
        set(runtime['files']) == set(donor['runtime_manifest']['files']), 'Runtime file inventories must stay exact')
    return client, runtime


def extract_and_repair(apk, donor, destination, commit, dbserver_directory):
    base = builder(); current_sources(donor); native = validate_native(dbserver_directory, commit, donor)
    destination.mkdir(parents=True)
    with zipfile.ZipFile(apk) as archive:
        for entry in archive.infolist():
            if entry.filename == 'AndroidManifest.xml' or entry.filename.startswith('META-INF/'): continue
            require(entry.filename in set(donor['payloads'])|set(donor['retained_android_resources'])|{'classes.dex'},
                'Unexpected donor extraction member')
            target = destination/entry.filename; target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open('xb') as output: shutil.copyfileobj(source, output, 64*1024)
    require(all(base.file_pin(destination/name) == pin for name, pin in donor['payloads'].items()), 'Extracted donor bytes differ')
    assets = destination/'assets/runtime'
    shutil.copyfile(ROOT/'android/guest'/GUEST, assets/GUEST)
    for source, target in (('DbServer.exe', 'startup-dbserver.exe'), ('startup-dbserver-manifest.json', 'startup-dbserver-manifest.json')):
        shutil.copyfile(dbserver_directory/source, assets/target)
    updates = {name: base.file_pin(assets/name) for name in UPDATES}
    client, runtime = verification_manifests(donor, updates, commit, native)
    for name, value in (('client-manifest.json', client), ('runtime-manifest.json', runtime)):
        (assets/name).write_bytes(shared.encoded(value))
    payloads = {name: base.file_pin(destination/name) for name in donor['payloads']}
    require({name for name in payloads if payloads[name] != donor['payloads'][name]} == REPLACED_PAYLOADS,
        'Unexpected startup payload replacement')
    preflight = prior.verify_server_archives(assets)
    require(preflight == donor['server_payload_extraction_preflight'], 'Retained server extraction differs')
    return runtime, payloads, preflight


def verify_derivative(apk, donor, payloads, commit, dbserver_directory):
    base = builder(); native = validate_native(dbserver_directory, commit, donor)
    require(set(payloads) == set(donor['payloads']) and len(payloads) == 72 and
        {name for name in payloads if payloads[name] != donor['payloads'][name]} == REPLACED_PAYLOADS,
        'Candidate startup payload boundaries differ')
    base.verify_packaged_payloads(apk, payloads)
    with zipfile.ZipFile(apk) as archive:
        shell = {'classes.dex': donor['retained_dex'], **donor['retained_android_resources']}
        require(prior.archive_inventory(archive) == set(payloads)|set(shell)|{'AndroidManifest.xml'}, 'Unexpected candidate inventory')
        for name, pin in shell.items():
            raw = archive.read(name)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == pin, 'Retained Android shell differs')
        require(payloads['assets/runtime/'+GUEST] == base.file_pin(ROOT/'android/guest'/GUEST), 'Authored guest witness differs')
        for source, target in (('DbServer.exe', 'startup-dbserver.exe'), ('startup-dbserver-manifest.json', 'startup-dbserver-manifest.json')):
            require(payloads['assets/runtime/'+target] == base.file_pin(dbserver_directory/source), 'Source-bound native bytes differ')
        client, runtime = verification_manifests(donor, {name: payloads['assets/runtime/'+name] for name in UPDATES}, commit, native)
        require(json.loads(archive.read('assets/runtime/client-manifest.json')) == client and
            json.loads(archive.read('assets/runtime/runtime-manifest.json')) == runtime, 'Startup verification manifests differ')
        require(json.loads(archive.read('assets/runtime/startup-dbserver-manifest.json')) == native, 'Native manifest differs')
    require(prior.verify_apk_server_archives(apk) == donor['server_payload_extraction_preflight'], 'Actual retained server extraction differs')
    return runtime


def validate_qualification(receipt, commit):
    require(receipt.get('format') == 1 and receipt.get('status') == 'passed' and receipt.get('scope') == QUALIFICATION_SCOPE
        and receipt.get('repository_commit') == commit and receipt.get('donor') == donor_link()
        and set(receipt.get('checks', {})) == set(CHECKS) and all(value is True for value in receipt['checks'].values())
        and receipt.get('native_dbserver_compiled_in_current_run') is True and receipt.get('native_dbserver_package_reused') is False
        and all(receipt.get(key) is False for key in ('physical_reopen_validated', 'physical_gameplay_validated',
            'physical_client_timing_validated', 'physical_visual_assets_validated', 'native_client_recompiled',
            'native_mapserver_recompiled', 'java_or_dex_recompiled', 'asset_reimport_required')),
        'Exact source-bound startup qualification required')
    contract = module('reopen_startup_qualification_contract', ROOT/QUALIFICATION_SCRIPT)
    suites = receipt.get('test_suites', {})
    require(set(suites) == set(contract.TEST_MODULES) and receipt.get('check_suites') == contract.CHECK_SUITES
        and all(item.get('status') == 'passed' and item.get('skipped') == 0 and type(item.get('tests_run')) is int
            and item['tests_run'] > 0 for item in suites.values())
        and receipt.get('tests_run') == sum(item['tests_run'] for item in suites.values()), 'Complete unskipped test inventory required')
    require(SOURCE_FILES <= set(receipt.get('source_files', {})), 'Current source closure incomplete')
    for name, pin in receipt['source_files'].items():
        require(isinstance(name, str) and not Path(name).is_absolute() and '..' not in Path(name).parts and chr(92) not in name,
            'Unsafe current source path')
        builder().checked_file(ROOT/name, pin)
    native_fixture = module('startup_formatter_fixture_contract', ROOT/'tools/android/interactive/test_reopen_dbserver_thread_name.py')
    require(receipt.get('startup_thread_name_fixtures') == sorted(native_fixture.REQUIRED_THREAD_NAME_FIXTURES),
        'Compiled production thread-name formatting fixtures required')
    require(receipt.get('postgresql_emission_fixtures') == ['cancelled_child_deletion_commits', 'delete_insert_replacement_commits', 'duplicate_insert_23505_rollback']
        and receipt.get('postgresql_levelup_fixtures') == sorted(prior.levelup_postgresql_fixtures()), 'All real PostgreSQL fixtures required')
    return receipt


def repair_android_manifest(source, destination):
    base = builder(); base.verify_source_manifest(source)
    tree = ET.parse(source); tree.getroot().set(base.ANDROID+'versionName', VERSION_NAME)
    tree.getroot().set(base.ANDROID+'versionCode', str(VERSION_CODE))
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
    native = validate_native(args.dbserver_directory, commit, donor)
    require(qualification.get('native_levelup_ui_repair') == native, 'Native package changed after qualification')
    java = current_sources(donor)
    password = base.signing_password_spec(args.password_env)
    base.verify_signing_identity(args.keystore, 'coh-client-interactive', SIGNER, password)
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), 'Fresh startup APK required')
    base.checked_file(args.testing_notes); require(0 < args.testing_notes.stat().st_size <= 65536, 'Bounded testing notes required')
    for tool in (args.android_jar, args.build_tools/'aapt2', args.build_tools/'zipalign', args.build_tools/'lib/apksigner.jar'):
        require(tool.is_file() and not tool.is_symlink(), 'Required Android tool missing')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-reopen-startup-', dir=args.output.parent) as temporary:
        work = Path(temporary)
        runtime, payloads, preflight = extract_and_repair(args.donor_apk, donor, work/'donor', commit, args.dbserver_directory)
        manifest = work/'AndroidManifest.xml'; repair_android_manifest(ROOT/'android/interactive/src/main/AndroidManifest.xml', manifest)
        resources, unsigned, aligned, signed = (work/name for name in ('resources.zip', 'unsigned.apk', 'aligned.apk', 'signed.apk'))
        base.run(args.build_tools/'aapt2', 'compile', '--dir', ROOT/'android/interactive/src/main/res', '-o', resources)
        base.run(args.build_tools/'aapt2', 'link', '-I', args.android_jar, '--manifest', manifest, '--min-sdk-version', '26', '--target-sdk-version', '35', resources, '-o', unsigned)
        with zipfile.ZipFile(unsigned) as archive:
            require(prior.archive_inventory(archive) == {'AndroidManifest.xml', 'resources.arsc', 'res/drawable/ic_coh_client.xml'}, 'Generated Android resource inventory differs')
            for name, pin in donor['retained_android_resources'].items():
                raw = archive.read(name)
                require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == pin, 'Android resources changed beyond version metadata')
        with zipfile.ZipFile(unsigned, 'a', zipfile.ZIP_DEFLATED) as archive:
            base.append_payloads(archive, [(work/'donor'/name, name) for name in sorted(payloads)])
            archive.write(work/'donor/classes.dex', 'classes.dex')
        base.run(args.build_tools/'zipalign', '-f', '4', unsigned, aligned)
        base.run('java', '-jar', args.build_tools/'lib/apksigner.jar', 'sign', '--ks', args.keystore, '--ks-key-alias', 'coh-client-interactive', '--ks-pass', password, '--key-pass', password, '--out', signed, aligned)
        certificate = prior.verify_signature(signed, args.build_tools); base.run(args.build_tools/'zipalign', '-c', '4', signed)
        current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', signed))
        verify_derivative(signed, donor, payloads, commit, args.dbserver_directory)
        prior.verify_binary_manifest(signed, args.donor_apk, args.build_tools)
        shutil.copyfile(signed, args.output)
        report = {'format': 1, 'apk': APK_NAME, **base.file_pin(args.output), 'repository_commit': commit,
            'runtime_repository_commit': commit, 'application_id': base.APP_ID, 'version_name': VERSION_NAME,
            'version_code': VERSION_CODE, 'abi': 'arm64-v8a', 'scope': QUALIFICATION_SCOPE, 'donor': donor_link(),
            'signer_certificate_sha256': certificate, 'signing_key_created': False, 'signature_verified': True,
            'package_badging_verified': True, 'binary_manifest_version_only_verified': True, 'payload_bytes_verified': True,
            'payloads': payloads, 'changed_apk_payloads': sorted(REPLACED_PAYLOADS), 'added_apk_payloads': [],
            'retained_baseline_payloads_verified': 72, 'java_sources': java, 'changed_java_sources': [],
            'retained_dex': donor['retained_dex'], 'preserved_sources': donor['preserved_sources'],
            'source_manifest': donor['source_manifest'], 'qualification': qualification,
            'qualification_receipt': base.file_pin(args.qualification), 'testing_notes': base.file_pin(args.testing_notes),
            'native_dbserver': native, 'native_levelup_ui_repair': native,
            'native_dbserver_compiled_in_current_run': True, 'native_dbserver_package_reused': False,
            'native_client_recompiled': False, 'native_mapserver_recompiled': False, 'java_or_dex_recompiled': False,
            'physical_reopen_validated': False, 'physical_gameplay_validated': False,
            'physical_client_timing_validated': False, 'physical_visual_assets_validated': False,
            'runtime_refresh_required': True, 'previous_runtime_generation_retained': True, 'asset_reimport_required': False,
            'setup_memory_guards_preserved': True, 'world_assets_changed': False, 'prepared_cache_archive_changed': False,
            'all_published_ui_resources_retained': True, 'server_payload_extraction_preflight': preflight,
            'runtime_manifest': runtime, 'runtime_manifest_sha256': payloads['assets/runtime/runtime-manifest.json']['sha256'],
            **{name: donor[name] for name in RETAINED_REPORT_FIELDS}}
        (args.output.parent/REPORT_NAME).write_text(json.dumps(report, indent=2)+'\n')
    shutil.copyfile(args.testing_notes, args.output.parent/NOTES_NAME)
    args.output.with_suffix('.apk.sha256').write_text(report['sha256']+'  '+APK_NAME+'\n')
    verify_report(argparse.Namespace(**vars(args), apk=args.output, build_report=args.output.parent/REPORT_NAME), commit)
    print('Qualified startup APK:', args.output, report['sha256'])
    return report


def verify_report(args, commit):
    donor = validate_donor(args.donor_apk, args.donor_build_report); base, current = builder(), builder(repaired=True)
    qualification = validate_qualification(read_json(args.qualification), commit)
    report = read_json(args.build_report); native = validate_native(args.dbserver_directory, commit, donor)
    require(report.get('format') == 1 and report.get('apk') == APK_NAME and report.get('repository_commit') == commit
        and report.get('runtime_repository_commit') == commit and report.get('donor') == donor_link()
        and report.get('application_id') == base.APP_ID and report.get('version_name') == VERSION_NAME
        and report.get('version_code') == VERSION_CODE and report.get('abi') == 'arm64-v8a'
        and report.get('scope') == QUALIFICATION_SCOPE and report.get('signer_certificate_sha256') == SIGNER
        and report.get('signing_key_created') is False and report.get('qualification') == qualification
        and report.get('qualification_receipt') == base.file_pin(args.qualification)
        and report.get('java_sources') == current_sources(donor) and report.get('changed_java_sources') == []
        and report.get('retained_dex') == donor['retained_dex'] and report.get('preserved_sources') == donor['preserved_sources']
        and report.get('source_manifest') == donor['source_manifest']
        and report.get('native_dbserver') == native and report.get('native_levelup_ui_repair') == native
        and report.get('changed_apk_payloads') == sorted(REPLACED_PAYLOADS) and report.get('added_apk_payloads') == []
        and all(report.get(key) is True for key in ('signature_verified', 'package_badging_verified',
            'binary_manifest_version_only_verified', 'payload_bytes_verified', 'native_dbserver_compiled_in_current_run',
            'runtime_refresh_required', 'previous_runtime_generation_retained', 'setup_memory_guards_preserved',
            'all_published_ui_resources_retained'))
        and all(report.get(key) is False for key in ('native_dbserver_package_reused', 'native_client_recompiled',
            'native_mapserver_recompiled', 'java_or_dex_recompiled', 'physical_reopen_validated', 'physical_gameplay_validated',
            'physical_client_timing_validated', 'physical_visual_assets_validated', 'asset_reimport_required',
            'world_assets_changed', 'prepared_cache_archive_changed'))
        and report.get('retained_baseline_payloads_verified') == 72
        and all(report.get(name) == donor[name] for name in RETAINED_REPORT_FIELDS), 'Startup build receipt differs')
    base.checked_file(args.apk, report)
    runtime = verify_derivative(args.apk, donor, report['payloads'], commit, args.dbserver_directory)
    require(report.get('runtime_manifest') == runtime and report.get('runtime_manifest_sha256') == report['payloads']['assets/runtime/runtime-manifest.json']['sha256'],
        'Runtime provenance differs')
    prior.verify_binary_manifest(args.apk, args.donor_apk, args.build_tools)
    prior.verify_signature(args.apk, args.build_tools); base.run(args.build_tools/'zipalign', '-c', '4', args.apk)
    current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', args.apk))
    checksum = args.apk.with_suffix('.apk.sha256')
    require(checksum.read_text() == report['sha256']+'  '+APK_NAME+'\n', 'Published checksum differs')
    notes = args.apk.parent/NOTES_NAME
    base.checked_file(notes, report['testing_notes']); base.checked_file(args.testing_notes, report['testing_notes'])
    return report, checksum, notes


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
    body = notes+'\n\nAPK SHA-256: `'+report['sha256']+'`.\n'
    body += '[Source-bound DbServer qualification](https://github.com/'+REPOSITORY+'/actions/runs/'+os.environ.get('GITHUB_RUN_ID', '')+').\n'
    release = api.request('/releases', {'tag_name': RELEASE_TAG, 'target_commitish': report['repository_commit'],
        'name': 'COH Atlas Gameplay 0.13.13 — saved-character startup repair', 'body': body,
        'draft': True, 'prerelease': True, 'generate_release_notes': False, 'make_latest': 'false'}, method='POST')
    require(type(release.get('id')) is int and release.get('draft') is True and release.get('prerelease') is True and release.get('tag_name') == RELEASE_TAG, 'Unexpected created release')
    for path in assets:
        uploaded = api.request('/releases/'+str(release['id'])+'/assets?'+urllib.parse.urlencode({'name': path.name}), path, method='POST', upload=True)
        pin = builder().file_pin(path)
        require(uploaded.get('state') == 'uploaded' and uploaded.get('name') == path.name and uploaded.get('size') == pin['bytes']
            and uploaded.get('digest') == 'sha256:'+pin['sha256'], 'Release upload differs')
    published = api.request('/releases/'+str(release['id']), {'draft': False, 'prerelease': True, 'make_latest': 'false'}, method='PATCH')
    require(published.get('id') == release['id'] and published.get('draft') is False and published.get('prerelease') is True
        and published.get('tag_name') == RELEASE_TAG, 'Publication did not complete')
    return published.get('html_url')


def publish(args):
    require(os.environ.get('GITHUB_REPOSITORY') == REPOSITORY and os.environ.get('GITHUB_REF') == 'refs/heads/'+BRANCH
        and os.environ.get('GITHUB_EVENT_NAME') in ('push', 'workflow_dispatch'), 'Publication requires authorized continuation branch')
    commit = builder().source_commit(os.environ.get('GITHUB_SHA')); report, checksum, notes = verify_report(args, commit)
    api = module('reopen_startup_github', Path(__file__).with_name('build_atlas_gameplay_apk.py'))
    print('Published startup prerelease:', publish_release(api.GitHub(os.environ.get('GH_TOKEN')), report,
        (args.apk, checksum, notes), notes.read_text()))


def main():
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest='command', required=True)
    download_parser = commands.add_parser('download-donor'); download_parser.add_argument('--output', type=Path, required=True)
    for command in ('build', 'publish', 'audit'):
        item = commands.add_parser(command)
        for name in ('donor-apk', 'donor-build-report', 'dbserver-directory', 'qualification', 'build-tools'):
            item.add_argument('--'+name, type=Path, required=True)
        item.add_argument('--testing-notes', type=Path, default=NOTES)
        if command == 'build':
            for name in ('android-jar', 'keystore', 'output'): item.add_argument('--'+name, type=Path, required=True)
            item.add_argument('--password-env', default='COH_INTERACTIVE_KEYSTORE_PASSWORD')
        else:
            for name in ('apk', 'build-report'): item.add_argument('--'+name, type=Path, required=True)
        if command != 'publish': item.add_argument('--repository-commit', required=True)
    args = parser.parse_args()
    if args.command == 'download-donor': download(args)
    elif args.command == 'build': build(args)
    elif args.command == 'publish': publish(args)
    else:
        report, _, _ = verify_report(args, builder().source_commit(args.repository_commit))
        print('Public startup APK independently verified:', report['sha256'])


if __name__ == '__main__': main()
