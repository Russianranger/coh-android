#!/usr/bin/env python3
"""Qualify bounded renderer/capture diagnostics over the immutable public 0.13.18 APK."""
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

import build_client_sidebar_apk as previous
import package_client_renderer_attribution_native as native_producer

ROOT, require, module, shared = previous.ROOT, previous.require, previous.module, previous.shared
REPOSITORY, BRANCH, SIGNER = previous.REPOSITORY, previous.BRANCH, previous.SIGNER
retained = previous.retained
engine = previous.previous
DONOR_COMMIT = 'd1e455f8d0047ac02398d17c5df1001375522f98'
DONOR_RUN_ID = 37637034415
DONOR_APK_NAME = 'COH-Atlas-Gameplay-0.13.18.apk'
DONOR_APK = {'bytes': 1557379684, 'sha256': 'd7fb00ae5406208a2497c7b9ea9659403a422dd0698404cd968112a4ba7b8ca1'}
DONOR_BUILD = {'bytes': 5077901, 'sha256': '4eb3708e2384303bcebfc51c5f572d7f29f82b28163ab2a5aaa26e89938bee71'}
DONOR_URL = 'https://github.com/'+REPOSITORY+'/releases/download/coh-atlas-gameplay-v0.13.18/'+DONOR_APK_NAME
DONOR_GAME = {'bytes': 9477120, 'sha256': '5b6cfb6d20eb5f6642d6d1124e6b5ba188e89f9ad58c26268f0be35d996134aa'}
VERSION_NAME, VERSION_CODE = '0.13.19', 34
APK_NAME, REPORT_NAME = 'COH-Atlas-Gameplay-0.13.19.apk', 'client-renderer-attribution-apk-build-report.json'
NOTES_NAME = 'COH-Atlas-Gameplay-0.13.19-testing.txt'
NOTES = ROOT/'docs'/NOTES_NAME
RELEASE_TAG = 'coh-atlas-gameplay-v0.13.19'
WORKFLOW = '.github/workflows/android-client-renderer-attribution.yml'
QUALIFICATION_SCRIPT = 'tools/android/interactive/qualify_client_renderer_attribution.py'
QUALIFICATION_SCOPE = 'native_renderer_attribution_bounded_background_capture_and_strict_save_diagnostics_retaining_public_0_13_18'
JAVA_ROOT = 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/'
JAVA_CHANGES = frozenset(JAVA_ROOT+name+'.java' for name in
    ('ClientSurface', 'ClientActivity', 'ClientRuntime', 'ClientService'))
JAVA_ADDITIONS, ADDED_PAYLOADS = frozenset(), frozenset()
HELPERS = frozenset({'native_responsiveness_contract.py', 'client_startup_diagnostic.py',
    'texture_header_index.py', 'local_character_server.py'})
REPLACED_PAYLOADS = frozenset('assets/runtime/'+name for name in
    HELPERS|{'client-runtime.zip', 'client-manifest.json', 'runtime-manifest.json'})
CHECKS = ('native_renderer_attribution_and_current_producer_controls_verified',
    'bounded_background_capture_and_strict_failed_save_diagnostics_verified',
    'retained_gameplay_postgresql_and_recovery_guards_verified',
    'exact_game_and_reviewed_android_helper_payload_boundaries_verified')
SOURCE_FILES = frozenset({WORKFLOW, QUALIFICATION_SCRIPT,
    'tools/android/interactive/build_client_renderer_attribution_apk.py',
    'tools/android/interactive/test_client_renderer_attribution_package.py',
    'tools/android/interactive/test_client_renderer_attribution_contract.py',
    'tools/android/interactive/test_client_surface_capture.py',
    'tools/android/interactive/test_client_capture_metrics.py',
    'tools/android/interactive/test_stock_power_delta.py',
    'tools/android/interactive/test_setup_service.py', *native_producer.SOURCE_FILES,
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'docs/COH-PERFORMANCE-0.13.19.md', 'docs/'+NOTES_NAME,
    'docs/android-evidence/renderer-attribution-0.13.18-thor-20261008.json',
    *JAVA_CHANGES, *('android/guest/'+name for name in HELPERS)})
REVIEWED_DONOR_SOURCE_CHANGES = frozenset(name for name in SOURCE_FILES
    if not name.startswith('upstream/')) | frozenset({'docs/HANDOFF.md',
    'docs/android-evidence/client-sidebar-0.13.18-publication.json'})
FALSE_FLAGS = ('native_dbserver_recompiled', 'native_mapserver_recompiled',
    'native_runtime_booted', 'physical_gameplay_validated', 'physical_client_timing_validated',
    'physical_visual_assets_validated', 'physical_sidebar_input_validated',
    'physical_capture_savings_validated', 'physical_renderer_savings_validated',
    'asset_reimport_required', 'world_assets_changed', 'prepared_cache_archive_changed',
    'graphics_driver_changed', 'wine_or_fex_changed', 'save_acceptance_relaxed', 'zoning_implemented')
RETAINED_RECEIPT_FIELDS = ('retained_android_resources', 'preserved_sources', 'source_manifest',
    'immutable_donor_provenance', 'native_client_gameplay_performance', 'server_payload_extraction_preflight')
ACTUAL_NATIVE_ANCESTRY_CHECKS = {'status': 'passed', 'actual_external_donor_and_win32_receipts_verified': True,
    'full_guest_typed_client_wrapper_verified': True, 'older_native_history_unchanged': True,
    'actual_gameplay_Game_predecessor_verified': True, 'raw_source_histories_preserved': True,
    'rejected_foreign_variants': ['pg_header', 'pg_fixture', 'pg_extra', 'pg_patch', 'event_source',
        'texture', 'event_bool', 'event_float', 'pg_digest', 'game_digest', 'progress_digest']}



def builder(*, repaired=False):
    base = previous.builder()
    if repaired: base.VERSION_NAME, base.VERSION_CODE, base.APK_NAME = VERSION_NAME, VERSION_CODE, APK_NAME
    return base



read_json = previous.read_json


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
    require(changed == JAVA_CHANGES, 'Java changes exceed the reviewed capture/report shell')
    for name, pin in donor['preserved_sources'].items(): base.checked_file(ROOT/name, pin)
    base.checked_file(ROOT/'android/interactive/src/main/AndroidManifest.xml', donor['source_manifest'])
    for name, pin in donor['payloads'].items():
        if name.startswith('assets/runtime/') and name.endswith('.py') and Path(name).name not in HELPERS:
            base.checked_file(ROOT/'android/guest'/Path(name).name, pin)
    require({name for name in HELPERS if base.file_pin(ROOT/'android/guest'/name) != donor['payloads']['assets/runtime/'+name]} == HELPERS, 'Exactly the reviewed renderer/save diagnostic helpers must change')
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
        'name': 'COH Atlas Gameplay 0.13.19 — renderer attribution and bounded background captures',
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
    api = module('client_renderer_attribution_github', Path(__file__).with_name('build_atlas_gameplay_apk.py'))
    print('Published performance prerelease:', publish_release(api.GitHub(os.environ.get('GH_TOKEN')), report, (args.apk, checksum, notes), notes.read_text()))


def validate_donor_receipt(path):
    builder().checked_file(path, DONOR_BUILD); donor = read_json(path); q = donor.get('qualification', {})
    require(donor.get('format') == 1 and donor.get('repository_commit') == DONOR_COMMIT
        and donor.get('runtime_repository_commit') == '4a57ffe3b75612fb9c356de9c4150729736e849e'
        and donor.get('apk') == DONOR_APK_NAME and {key: donor.get(key) for key in DONOR_APK} == DONOR_APK
        and donor.get('application_id') == builder().APP_ID and donor.get('version_name') == '0.13.18'
        and donor.get('version_code') == 33 and donor.get('abi') == 'arm64-v8a'
        and donor.get('signer_certificate_sha256') == SIGNER and donor.get('signing_key_created') is False
        and all(donor.get(key) is True for key in ('signature_verified', 'package_badging_verified',
            'binary_manifest_version_only_verified', 'payload_bytes_verified', 'setup_memory_guards_preserved',
            'java_or_dex_recompiled', 'installed_runtime_identity_preserved', 'native_client_package_reused'))
        and donor.get('runtime_refresh_required') is False
        and len(donor.get('payloads', {})) == 75 and len(donor.get('java_sources', {})) == 19
        and q.get('status') == 'passed' and q.get('scope') == previous.QUALIFICATION_SCOPE
        and q.get('repository_commit') == DONOR_COMMIT and q.get('tests_run') == 1264
        and len(q.get('source_files', {})) == 9638 and len(q.get('test_suites', {})) == 84
        and all(item.get('status') == 'passed' and item.get('skipped') == 0 for item in q['test_suites'].values())
        and donor.get('server_payload_extraction_preflight', {}).get('status') == 'passed'
        and q.get('retained_native_gameplay_performance') == donor.get('native_client_gameplay_performance')
        and donor.get('native_client_gameplay_performance') == donor.get('retained_native_gameplay_performance')
        and donor.get('runtime_manifest_sha256') == donor.get('payloads', {}).get('assets/runtime/runtime-manifest.json', {}).get('sha256'),
        'Exact audited public 0.13.18 donor receipt differs')
    game = donor['native_client_gameplay_performance']['files']['CityOfHeroes.exe']
    require({'bytes': game['size'], 'sha256': game['sha256']} == DONOR_GAME,
        'Frozen published 0.13.18 Game differs')
    return donor


def validate_donor(apk, receipt):
    base = builder(); base.checked_file(apk, DONOR_APK); donor = validate_donor_receipt(receipt)
    base.verify_packaged_payloads(apk, donor['payloads'])
    with zipfile.ZipFile(apk) as archive:
        shell = {'classes.dex': donor['recompiled_dex'], **donor['retained_android_resources']}
        require(retained.archive_inventory(archive) == set(donor['payloads'])|set(shell)|{'AndroidManifest.xml'},
            'Unexpected immutable public donor inventory')
        for name, pin in shell.items():
            raw = archive.read(name)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == pin,
                'Donor Android shell differs: '+name)
        require(json.loads(archive.read('assets/runtime/runtime-manifest.json')) == donor['runtime_manifest'],
            'Donor runtime provenance differs')
        donor['_client_verification'] = json.loads(archive.read('assets/runtime/client-manifest.json'))
        for name in HELPERS: donor.setdefault('_helper_sources', {})[name] = archive.read('assets/runtime/'+name)
        with archive.open('assets/runtime/client-runtime.zip') as source, tempfile.TemporaryFile() as target:
            shutil.copyfileobj(source, target, 1024*1024); target.seek(0)
            with zipfile.ZipFile(target) as client:
                package = json.loads(client.read('client-package.json'))
                pins = engine.startup.startup.client_member_pins(client)
                shared.native_contract.client_contract(package, donor['immutable_donor_provenance']['native_responsiveness'])
                require(package.get('client_gameplay_performance', {}).get('manifest') == donor['native_client_gameplay_performance']
                    and package.get('files', {}).get('CityOfHeroes.exe') == donor['native_client_gameplay_performance']['files']['CityOfHeroes.exe']
                    and pins.get('CityOfHeroes.exe') == DONOR_GAME, 'Actual donor Game and typed native history differ')
                dlls = donor['immutable_donor_provenance']['native_responsiveness']['retained_native_files']['client']
                require(len(dlls) == 20 and set(pins) == set(dlls)|{'CityOfHeroes.exe', 'client-package.json'}
                    and all(pins[name] == {'bytes': pin['size'], 'sha256': pin['sha256']} for name, pin in dlls.items()),
                    'Actual immutable donor DLL closure differs')
                donor['_native_client_manifest'], donor['_client_members'] = package, pins
    require(retained.verify_apk_server_archives(apk) == donor['server_payload_extraction_preflight'],
        'Donor actual server archive extraction differs')
    validate_retained_sources(donor)
    return donor


def validate_native(directory, commit, donor):
    native = native_producer.validate_package(directory, commit)
    if os.environ.get('GITHUB_RUN_ID'):
        require(native.get('run_url') == 'https://github.com/'+REPOSITORY+'/actions/runs/'+os.environ['GITHUB_RUN_ID'],
            'Renderer Game must be compiled and Win32-qualified in this exact current run')
    provenance = donor['immutable_donor_provenance']['native_responsiveness']
    engine.validate_native_source_ancestry(native['retained_source_inputs'], provenance['build_inputs'])
    require(native['base_client_executable'] == donor['_native_client_manifest']['files']['CityOfHeroes.exe']
        and native['schema_sources_sha256'] == provenance['retained_cache']['schema_sources_sha256']
        and native['build_input']['base_client_gameplay_performance_build_input']
            == donor['native_client_gameplay_performance']['build_input'], 'Native renderer ancestry or cache schema differs')
    return native


def client_manifest(donor, native):
    expected = copy.deepcopy(donor['_native_client_manifest'])
    expected['files']['CityOfHeroes.exe'] = native['files']['CityOfHeroes.exe']
    expected['dependency_report'] = shared.dependency_report(expected['files'])
    require(not expected['dependency_report']['unresolved'], 'New Game imports exceed retained DLL closure')
    expected['client_renderer_attribution'] = {'manifest': native,
        'manifest_sha256': shared.native_contract.canonical_sha(native),
        'base_client_gameplay_performance_manifest_sha256': expected['client_gameplay_performance']['manifest_sha256'],
        'base_client_executable': copy.deepcopy(donor['_native_client_manifest']['files']['CityOfHeroes.exe'])}
    shared.native_contract.client_contract(expected, donor['immutable_donor_provenance']['native_responsiveness'])
    return expected


def replace_client_archive(path, donor, native, directory):
    require(builder().file_pin(path) == donor['payloads']['assets/runtime/client-runtime.zip'], 'Exact donor client archive required')
    output = path.with_suffix('.candidate.zip'); require(not output.exists(), 'Fresh native client archive staging required')
    expected = client_manifest(donor, native)
    with zipfile.ZipFile(path) as original, zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        require(engine.startup.startup.client_member_pins(original) == donor['_client_members'], 'Donor native members differ')
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
        pins = engine.startup.startup.client_member_pins(archive)
        require(set(pins) == set(donor['_client_members']) and len(pins) == 22, 'Native client archive inventory differs')
        require(json.loads(archive.read('client-package.json')) == expected, 'Native package wrapper differs')
        record = native['files']['CityOfHeroes.exe']
        require(pins['CityOfHeroes.exe'] == {'bytes': record['size'], 'sha256': record['sha256']}, 'Packaged native Game bytes differ')
        require(all(pins[name] == pin for name, pin in donor['_client_members'].items()
            if name not in ('CityOfHeroes.exe', 'client-package.json')), 'A retained client DLL or native dependency changed')
    return expected


def verification_manifests(donor, updates, commit, native):
    require(set(updates) == HELPERS|{'client-runtime.zip'}, 'Unexpected renderer diagnostic replacement inputs')
    client = copy.deepcopy(donor['_client_verification']); client['files'].update(updates)
    runtime = copy.deepcopy(donor['runtime_manifest']); runtime['files'].update(updates)
    encoded = shared.encoded(client)
    runtime['files']['client-manifest.json'] = {'bytes': len(encoded), 'sha256': hashlib.sha256(encoded).hexdigest()}
    runtime['repository_commit'] = commit; runtime['scope'] = QUALIFICATION_SCOPE
    runtime['client_renderer_attribution'] = {'format': 1, 'repository_commit': commit,
        'donor_repository_commit': DONOR_COMMIT, 'all_visual_beacon_server_and_cache_payloads_retained': True,
        'physical_gameplay_validated': False, 'physical_timing_validated': False,
        'native_recompiled': True, 'android_capture_shell_recompiled': True,
        'strict_save_acceptance_preserved': True,
        'native_manifest_sha256': shared.native_contract.canonical_sha(native),
        'changed_guest_helpers': sorted(HELPERS), 'replacement_scope': 'CityOfHeroes.exe_only'}
    require(set(client['files']) == set(donor['_client_verification']['files'])
        and set(runtime['files']) == set(donor['runtime_manifest']['files']), 'Runtime inventory must remain exact')
    return client, runtime


def extract_and_repair(apk, donor, destination, commit, client_directory):
    native = validate_native(client_directory, commit, donor)
    base = builder(); current_java_sources(donor, ROOT/'out/no-generated-java'); destination.mkdir(parents=True)
    with zipfile.ZipFile(apk) as archive:
        require(retained.archive_inventory(archive) == set(donor['payloads'])|set(donor['retained_android_resources'])|{'AndroidManifest.xml', 'classes.dex'}, 'Unexpected donor inventory')
        for entry in archive.infolist():
            if entry.filename == 'AndroidManifest.xml' or entry.filename.startswith('META-INF/'): continue
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
        'Unexpected renderer/capture/save diagnostic payload replacement')
    preflight = retained.verify_server_archives(assets)
    require(preflight == donor['server_payload_extraction_preflight'], 'Retained server extraction differs')
    return runtime, payloads, preflight


def verify_derivative(apk, donor, payloads, dex_pin, commit, client_directory):
    native = validate_native(client_directory, commit, donor); base = builder()
    require(set(payloads) == set(donor['payloads']) and
        {name for name in payloads if payloads[name] != donor['payloads'][name]} == REPLACED_PAYLOADS,
        'Candidate renderer payload boundaries differ')
    require(dex_pin != donor['recompiled_dex'], 'Capture/report shell did not recompile Java/DEX')
    base.verify_packaged_payloads(apk, payloads)
    with zipfile.ZipFile(apk) as archive:
        shell = {'classes.dex': dex_pin, **donor['retained_android_resources']}
        require(retained.archive_inventory(archive) == set(payloads)|set(shell)|{'AndroidManifest.xml'}, 'Unexpected candidate inventory')
        for name, pin in shell.items():
            raw = archive.read(name)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == pin, 'Recompiled DEX or retained resources differ')
        for name in HELPERS:
            require(payloads['assets/runtime/'+name] == base.file_pin(ROOT/'android/guest'/name), 'Authored renderer/save diagnostic helper differs')
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
        and receipt.get('repository_commit') == commit and receipt.get('runtime_repository_commit') == commit
        and receipt.get('donor') == donor_link()
        and set(receipt.get('checks', {})) == set(CHECKS) and all(value is True for value in receipt['checks'].values())
        and all(receipt.get(key) is False for key in FALSE_FLAGS)
        and all(receipt.get(key) is True for key in ('native_client_recompiled', 'native_client_compiled_in_current_run',
            'java_or_dex_recompiled', 'guest_helpers_changed', 'runtime_manifest_changed', 'runtime_refresh_required'))
        and receipt.get('native_client_package_reused') is False and receipt.get('installed_runtime_identity_preserved') is False
        and receipt.get('actual_native_ancestry_validation') == ACTUAL_NATIVE_ANCESTRY_CHECKS,
        'Exact source-bound renderer/capture/save diagnostic qualification required')
    contract = module('client_renderer_attribution_qualification_contract', ROOT/QUALIFICATION_SCRIPT)
    contract.validate_suite_inventory(); suites = receipt.get('test_suites', {})
    require(set(suites) == set(contract.TEST_MODULES) and receipt.get('check_suites') == contract.CHECK_SUITES
        and all(item.get('status') == 'passed' and item.get('skipped') == 0 and type(item.get('tests_run')) is int and item['tests_run'] > 0
            for item in suites.values()) and receipt.get('tests_run') == sum(item['tests_run'] for item in suites.values()),
        'Complete retained and new unskipped suite inventory required')
    require(SOURCE_FILES <= set(receipt.get('source_files', {})), 'Current renderer/capture source closure incomplete')
    for name, pin in receipt['source_files'].items():
        require(isinstance(name, str) and not Path(name).is_absolute() and '..' not in Path(name).parts and chr(92) not in name, 'Unsafe source path')
        builder().checked_file(ROOT/name, pin)
    require(receipt.get('postgresql_emission_fixtures') == ['cancelled_child_deletion_commits', 'delete_insert_replacement_commits', 'duplicate_insert_23505_rollback']
        and receipt.get('postgresql_levelup_fixtures') == sorted(retained.levelup_postgresql_fixtures()), 'All seven real PostgreSQL fixtures required')
    return receipt


def build(args):
    base, current = builder(), builder(repaired=True); commit = base.source_commit(args.repository_commit)
    donor = validate_donor(args.donor_apk, args.donor_build_report)
    q = validate_qualification(read_json(args.qualification), commit)
    native = validate_native(args.client_directory, commit, donor)
    require(q.get('native_client_renderer_attribution') == native, 'Qualified retained native package differs')
    password = base.signing_password_spec(args.password_env)
    base.verify_signing_identity(args.keystore, 'coh-client-interactive', SIGNER, password)
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), 'Fresh sidebar APK required')
    base.checked_file(args.testing_notes); require(0 < args.testing_notes.stat().st_size <= 65536, 'Bounded notes required')
    for tool in (args.android_jar, args.build_tools/'aapt2', args.build_tools/'zipalign', args.build_tools/'lib/d8.jar', args.build_tools/'lib/apksigner.jar'):
        require(tool.is_file() and not tool.is_symlink(), 'Required Android tool missing')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-client-renderer-attribution-', dir=args.output.parent) as temporary:
        work = Path(temporary); runtime, payloads, preflight = extract_and_repair(args.donor_apk, donor, work/'donor', commit, args.client_directory)
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
        verify_derivative(signed, donor, payloads, dex_pin, commit, args.client_directory); retained.verify_binary_manifest(signed, args.donor_apk, args.build_tools)
        shutil.copyfile(signed, args.output)
        report = {'format': 1, 'apk': APK_NAME, **base.file_pin(args.output), 'repository_commit': commit,
            'runtime_repository_commit': commit, 'retained_runtime_repository_commit': donor['runtime_repository_commit'],
            'retained_native_repository_commit': donor['runtime_repository_commit'], 'application_id': base.APP_ID,
            'version_name': VERSION_NAME, 'version_code': VERSION_CODE, 'abi': 'arm64-v8a', 'scope': QUALIFICATION_SCOPE,
            'donor': donor_link(), 'signer_certificate_sha256': certificate, 'signing_key_created': False,
            'signature_verified': True, 'package_badging_verified': True, 'binary_manifest_version_only_verified': True,
            'payload_bytes_verified': True, 'payloads': payloads, 'changed_apk_payloads': sorted(REPLACED_PAYLOADS), 'replaced_apk_payloads': sorted(REPLACED_PAYLOADS),
            'added_apk_payloads': [], 'baseline_payloads_verified': 75, 'retained_baseline_payloads_verified': 75-len(REPLACED_PAYLOADS),
            'recompiled_dex': dex_pin, 'donor_dex': donor['recompiled_dex'], 'java_sources': java,
            'changed_java_sources': changed, 'added_java_sources': [], 'retained_java_sources_verified': 15,
            'generated_manifest': base.file_pin(manifest), 'qualification': q,
            'qualification_receipt': base.file_pin(args.qualification), 'testing_notes': base.file_pin(args.testing_notes),
            'java_or_dex_recompiled': True, 'installed_runtime_identity_preserved': False,
            'previous_runtime_generation_retained': True, 'native_client_package_reused': False,
            'native_client_renderer_attribution': native,
            'native_client_recompiled': True, 'native_client_compiled_in_current_run': True,
            'guest_helpers_changed': True, 'runtime_manifest_changed': True, 'runtime_refresh_required': True,
            'runtime_manifest': runtime, 'runtime_manifest_sha256': payloads['assets/runtime/runtime-manifest.json']['sha256'],
            'actual_native_ancestry_validation': q['actual_native_ancestry_validation'], 'setup_memory_guards_preserved': True,
            'all_published_visual_resources_retained': True, **{key: False for key in FALSE_FLAGS},
            **{name: donor[name] for name in RETAINED_RECEIPT_FIELDS}}
        (args.output.parent/REPORT_NAME).write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
    shutil.copyfile(args.testing_notes, args.output.parent/NOTES_NAME)
    args.output.with_suffix('.apk.sha256').write_text(report['sha256']+'  '+APK_NAME+'\n')
    verify_report(argparse.Namespace(**vars(args), apk=args.output, build_report=args.output.parent/REPORT_NAME), commit)
    print('Qualified renderer/capture diagnostic APK:', args.output, report['sha256']); return report


def verify_report(args, commit):
    donor = validate_donor(args.donor_apk, args.donor_build_report)
    base, current = builder(), builder(repaired=True); q = validate_qualification(read_json(args.qualification), commit)
    native = validate_native(args.client_directory, commit, donor); report = read_json(args.build_report)
    _, java, changed = current_java_sources(donor, ROOT/'out/no-generated-java')
    require(report.get('format') == 1 and report.get('apk') == APK_NAME and report.get('repository_commit') == commit
        and report.get('runtime_repository_commit') == commit and report.get('retained_runtime_repository_commit') == donor['runtime_repository_commit']
        and report.get('retained_native_repository_commit') == donor['runtime_repository_commit'] and report.get('donor') == donor_link()
        and report.get('scope') == QUALIFICATION_SCOPE and report.get('application_id') == base.APP_ID
        and report.get('version_name') == VERSION_NAME and report.get('version_code') == VERSION_CODE and report.get('abi') == 'arm64-v8a'
        and report.get('signer_certificate_sha256') == SIGNER and report.get('signing_key_created') is False
        and report.get('qualification') == q and report.get('qualification_receipt') == base.file_pin(args.qualification)
        and report.get('native_client_renderer_attribution') == native and q.get('native_client_renderer_attribution') == native
        and report.get('java_sources') == q.get('java_sources') == java and report.get('changed_java_sources') == q.get('changed_java_sources') == changed
        and report.get('added_java_sources') == [] and report.get('retained_java_sources_verified') == 15
        and report.get('donor_dex') == donor['recompiled_dex']
        and report.get('changed_apk_payloads') == sorted(REPLACED_PAYLOADS) and report.get('replaced_apk_payloads') == sorted(REPLACED_PAYLOADS) and report.get('added_apk_payloads') == []
        and report.get('baseline_payloads_verified') == 75 and report.get('retained_baseline_payloads_verified') == 75-len(REPLACED_PAYLOADS)
        and all(report.get(key) is True for key in ('signature_verified', 'package_badging_verified', 'binary_manifest_version_only_verified',
            'payload_bytes_verified', 'java_or_dex_recompiled', 'previous_runtime_generation_retained',
            'native_client_recompiled', 'native_client_compiled_in_current_run', 'guest_helpers_changed', 'runtime_manifest_changed', 'runtime_refresh_required', 'setup_memory_guards_preserved', 'all_published_visual_resources_retained'))
        and report.get('native_client_package_reused') is False and report.get('installed_runtime_identity_preserved') is False
        and report.get('actual_native_ancestry_validation') == ACTUAL_NATIVE_ANCESTRY_CHECKS
        and all(report.get(key) is False for key in FALSE_FLAGS)
        and all(report.get(name) == donor[name] for name in RETAINED_RECEIPT_FIELDS), 'Renderer/capture diagnostic build receipt differs')
    base.checked_file(args.apk, report); runtime = verify_derivative(args.apk, donor, report['payloads'], report['recompiled_dex'], commit, args.client_directory)
    require(report.get('runtime_manifest') == runtime and report.get('runtime_manifest_sha256') == report['payloads']['assets/runtime/runtime-manifest.json']['sha256'], 'Runtime provenance differs')
    retained.verify_binary_manifest(args.apk, args.donor_apk, args.build_tools); retained.verify_signature(args.apk, args.build_tools)
    base.run(args.build_tools/'zipalign', '-c', '4', args.apk)
    current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', args.apk))
    checksum = args.apk.with_suffix('.apk.sha256'); require(checksum.read_text() == report['sha256']+'  '+APK_NAME+'\n', 'Checksum differs')
    notes = args.apk.parent/NOTES_NAME; base.checked_file(notes, report['testing_notes']); base.checked_file(args.testing_notes, report['testing_notes'])
    return report, checksum, notes


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
