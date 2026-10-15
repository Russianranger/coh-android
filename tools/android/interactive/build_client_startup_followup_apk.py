#!/usr/bin/env python3
"""Build the typed 0.13.11 Game-only startup and append-only appearance follow-up.

The Android memory DEX, all 19 authored Java files, DbServer, MapServer,
server caches, graphics closure, twenty client DLLs and world/avatar packs stay
exact. A new source-bound Game contains the opt-in dependency preload. Existing
reward/save proofs and all prior native producer histories remain unchanged.
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

import build_startup_bundle_apk as startup

ROOT = Path(__file__).resolve().parents[3]
retained, shared = startup.retained, startup.shared
REPOSITORY, BRANCH, SIGNER = startup.REPOSITORY, startup.BRANCH, startup.SIGNER
DONOR_COMMIT = '9c36a5f411290400cb4aa4b2711a4bdcd39ca8cb'
DONOR_RUNTIME_COMMIT = '7b48762de0748e443a2df60c6e4b59e22b365e35'
RETAINED_SETUP_MEMORY_COMMIT = '31c8a1722f992e7a8334ef2256b4feaa9ca173be'
RETAINED_NATIVE_COMMIT = startup.RETAINED_NATIVE_COMMIT
DONOR_RUN_ID = 37249488856
DONOR_APK_NAME = 'COH-Atlas-Gameplay-0.13.10.apk'
DONOR_APK = {'bytes': 1194150167, 'sha256': '4c02b4f5f1ff9b82ab8b96fe5b4d2f402b687c3ee66ef1d8535a1a68f0c07d4a'}
DONOR_BUILD = {'bytes': 46029749, 'sha256': '11f3420fe7b278851b25e91726114af0cbcdcb5fc3a33f6fe6eb3b826681deb1'}
DONOR_URL = 'https://github.com/'+REPOSITORY+'/releases/download/coh-atlas-gameplay-v0.13.10/'+DONOR_APK_NAME
VERSION_NAME, VERSION_CODE = '0.13.11', 26
APK_NAME = 'COH-Atlas-Gameplay-0.13.11.apk'
REPORT_NAME = 'client-startup-followup-apk-build-report.json'
NOTES_NAME = 'COH-Atlas-Gameplay-0.13.11-testing.txt'
NOTES = ROOT/'docs'/NOTES_NAME
RELEASE_TAG = 'coh-atlas-gameplay-v0.13.11'
HELPERS = frozenset({'client_visual_assets.py', 'native_responsiveness_contract.py', 'client_startup_diagnostic.py',
    'texture_header_index.py'})
NATIVE_ASSETS = frozenset({'client-runtime.zip'})
SERVER_GUEST = 'android/guest/local_character_server.py'
REVIEWED_REWARD_FUNCTION = 'native_reward_credit_evidence'
REVIEWED_REWARD_METHODS = frozenset({
    ('LocalCharacterReopenServer', 'validate_saved_rows'),
    ('LocalCharacterReopenServer', 'saved_selected_rows_match'),
    ('LocalCharacterReopenServer', 'saved_metadata'),
    ('LocalCharacterTaskReopenServer', 'saved_selected_rows_match'),
})
REVIEWED_STAGING_METHOD = ('LocalCharacterServer', 'stage_map_data')
# The exact retained MapServer producer defines the point/log formats consumed
# by the reviewed save proof. These unchanged files were not in the immediate
# donor's older qualification closure, so pin their original source separately.
RETAINED_REWARD_SOURCE_FILES = {
    'upstream/ouroboros/MapServer/src/Reward.c': {'bytes': 211292,
        'sha256': 'd3143fbb0d4e2a7134448cf51e5d47333cae6a3f8b8efe300a3d23a84766501b'},
    'upstream/ouroboros/MapServer/src/dbcomm/logcomm.c': {'bytes': 12704,
        'sha256': 'fb18f0a290ff6cc99d2f546ddd8e13f1bc20062865dff30414fcb738f22d95a0'},
}
ADDED_HELPERS = frozenset()
VISUAL_ASSETS = frozenset({'client-visual-assets.zip', 'client-visual-manifest.json'})
REPLACED_PAYLOADS = frozenset('assets/runtime/'+name for name in HELPERS|VISUAL_ASSETS|NATIVE_ASSETS|{'client-manifest.json', 'runtime-manifest.json'})
ADDED_PAYLOADS = frozenset()
QUALIFICATION_SCOPE = 'game_only_dependency_preload_and_append_only_appearance_with_retained_0_13_10_server_identity'
CHECKS = ('client_animation_mount_and_failure_guards_verified',
    'missing_only_visual_assets_and_texture_index_binding_verified',
    'owned_native_reward_delta_and_strict_save_rows_verified',
    'retained_save_task_storage_profile_and_memory_guards_verified',
    'exact_payload_boundaries_and_actual_archive_extraction_verified',
    'source_bound_game_dependency_preload_verified')
WORKFLOW = '.github/workflows/android-client-startup-followup.yml'
QUALIFICATION_SCRIPT = 'tools/android/interactive/qualify_client_startup_followup.py'
SOURCE_FILES = frozenset((WORKFLOW, QUALIFICATION_SCRIPT,
    'tools/android/interactive/build_client_startup_followup_apk.py',
    'tools/android/interactive/test_client_startup_followup_package.py',
    'tools/android/interactive/test_client_startup_followup_limits.py',
    'tools/android/interactive/package_client_startup_followup_native.py',
    'tools/android/interactive/test_client_startup_followup_native.py',
    'tools/android/interactive/test_client_startup_followup_contract.py',
    'tools/android/interactive/discover_client_appearance_assets.py',
    'tools/android/interactive/client_appearance_costumes.py',
    'tools/android/interactive/test_client_appearance_costumes.py',
    'tools/android/interactive/test_client_visual_assets.py',
    'tools/android/interactive/prepare_client_appearance_assets.py',
    'tools/android/interactive/test_client_appearance_assets.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'assets/client-appearance-requests.json', 'assets/client-appearance-manifest.json',
    'assets/client-visual-manifest.json', 'android/interactive/src/main/AndroidManifest.xml',
    'docs/'+NOTES_NAME, 'docs/android-evidence/client-asset-closure-0.13.10-device-result.json', 'docs/android-evidence/client-asset-closure-0.13.10-publication.json',
    *(('android/guest/'+name) for name in HELPERS)))
require, module = startup.require, startup.module
JSON_LIMITS = {'client-visual-manifest.json': 64*1024**2,
    'client-asset-closure-apk-build-report.json': 64*1024**2,
    'client-startup-followup-qualification.json': 96*1024**2,
    REPORT_NAME: 192*1024**2}
archive_inventory = startup.archive_inventory
verify_server_archives, verify_apk_server_archives = startup.verify_server_archives, startup.verify_apk_server_archives
RETAINED_RECEIPT_FIELDS = tuple(name for name in retained.RETAINED_RECEIPT_FIELDS
    if name not in ('runtime_manifest', 'runtime_manifest_sha256')) + ('native_client_startup', 'native_client_loading', 'native_source_commit', 'native_source_provenance')


def read_json(path):
    # The reviewed visual recipe is larger than the historical native receipt
    # bound. Only this derivative's typed records receive the necessary limits;
    # retained donor/native readers and runtime payloads keep their old bounds.
    path = Path(path)
    if path == ROOT/'assets/client-appearance-manifest.json':
        return json.loads(visual_builder().manifest_bytes(path))
    if path == ROOT/'assets/client-visual-manifest.json':
        producer = module('old_visual_recipe_reader', Path(__file__).with_name('prepare_client_visual_assets.py'))
        return json.loads(producer.manifest_bytes(path))
    limit = JSON_LIMITS.get(path.name, 8*1024**2)
    require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= limit,
        'Missing, linked or unbounded client asset receipt: '+path.name)
    return json.loads(path.read_text())


def builder(*, repaired=False):
    base = module('client_startup_followup_android_builder', Path(__file__).with_name('build_apk.py'))
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
        and donor.get('application_id') == builder().APP_ID and donor.get('version_name') == '0.13.10'
        and donor.get('version_code') == 25 and donor.get('abi') == 'arm64-v8a'
        and donor.get('signer_certificate_sha256') == SIGNER and donor.get('signing_key_created') is False
        and all(donor.get(key) is True for key in ('signature_verified', 'package_badging_verified',
            'binary_manifest_version_only_verified', 'payload_bytes_verified', 'setup_memory_guards_preserved'))
        and len(donor.get('payloads', {})) == 71 and len(donor.get('java_sources', {})) == 19
        and donor.get('server_payload_extraction_preflight', {}).get('status') == 'passed'
        and qualification.get('scope') == 'client_visual_asset_closure_and_owned_reward_acceptance_with_retained_0_13_9_identity'
        and qualification.get('status') == 'passed' and qualification.get('tests_run') == 838
        and qualification.get('repository_commit') == DONOR_COMMIT
        and qualification.get('postgresql_emission_fixture_verified') is True
        and donor.get('retained_setup_memory_repository_commit') == RETAINED_SETUP_MEMORY_COMMIT
        and donor.get('retained_native_repository_commit') == RETAINED_NATIVE_COMMIT
        and donor.get('runtime_manifest', {}).get('repository_commit') == DONOR_COMMIT
        and donor['runtime_manifest'].get('startup_only_reopen') is True
        and donor['runtime_manifest'].get('task_gate_required') is True
        and donor.get('native_dbserver', {}).get('repository_commit') == DONOR_RUNTIME_COMMIT
        and donor.get('native_client_startup', {}).get('repository_commit') == DONOR_RUNTIME_COMMIT,
        'Exact public 0.13.10 startup/save/appearance donor receipt differs')
    return donor


def validate_retained_native_sources(donor):
    # The whole published receipt is fixed by DONOR_BUILD. Additionally prevent
    # an unreviewed native/schema/source edit from hiding behind retained bytes.
    native_names = {name for name in donor['qualification']['source_files'] if
        (name.startswith(('patches/', 'database/', 'upstream/')) or
        name in ('tools/android/interactive/package_startup_bundle_client.py',
            'tools/android/interactive/package_startup_bundle_dbserver.py',
            'tools/android/interactive/package_client_loading_native.py',
            'tools/android/interactive/test_client_loading_native.py',
            'android/guest/native_responsiveness_contract.py', 'android/guest/character_server_data_cache.py',
            'android/guest/local_character_server.py')) and Path(name).name not in HELPERS}
    require(native_names, 'Retained native source closure missing')
    for name in native_names: builder().checked_file(ROOT/name, donor['qualification']['source_files'][name])
    for name, expected in RETAINED_REWARD_SOURCE_FILES.items(): builder().checked_file(ROOT/name, expected)
    return sorted(native_names|set(RETAINED_REWARD_SOURCE_FILES))


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
        donor['_helper_sources'] = {name: archive.read('assets/runtime/'+name) for name in HELPERS}
        donor['_server_guest_source'] = archive.read('assets/runtime/local_character_server.py')
        donor['_visual_manifest'] = json.loads(archive.read('assets/runtime/client-visual-manifest.json'))
        require(donor['_visual_manifest'] == donor['visual_package']['manifest']
            and donor['_visual_manifest']['file_count'] == 5476,
            'Immediate donor visual inventory differs')
        with archive.open('assets/runtime/client-visual-assets.zip') as source, tempfile.TemporaryFile() as target:
            shutil.copyfileobj(source, target, 64*1024); target.seek(0)
            with zipfile.ZipFile(target) as visuals:
                require(archive_inventory(visuals) == set(donor['_visual_manifest']['files']), 'Donor visual ZIP inventory differs')
                donor['_visual_stream_pins'] = {entry.filename: visual_stream_pin(visuals, entry) for entry in visuals.infolist()}
        with archive.open('assets/runtime/client-runtime.zip') as source, tempfile.TemporaryFile() as target:
            shutil.copyfileobj(source, target, 64*1024); target.seek(0)
            with zipfile.ZipFile(target) as client:
                manifest = json.loads(client.read('client-package.json')); donor['_native_client_manifest'] = manifest
                shared.native_contract.client_contract(manifest, donor['native_responsiveness'])
                require(manifest.get('startup_bundle_client', {}).get('manifest') == donor['native_client_startup'],
                    'Retained native Game receipt differs')
                require(manifest.get('client_loading', {}).get('manifest') == donor['native_client_loading'],
                    'Immediate donor Game loading receipt differs')
                donor['_client_members'] = startup.client_member_pins(client)
                record = donor['native_client_loading']['files']['CityOfHeroes.exe']
                require(len(donor['_client_members']) == 22 and donor['_client_members']['CityOfHeroes.exe'] ==
                    {'bytes': record['size'], 'sha256': record['sha256']},
                    'Immediate donor Game PE bytes differ')
    require(verify_apk_server_archives(apk) == donor['server_payload_extraction_preflight'],
        'Exact public donor does not pass actual guest extraction')
    validate_retained_native_sources(donor)
    return donor


def current_sources(donor):
    base = builder(); sources = retained.java_sources(base, ROOT/'out/no-generated-java')
    pins = {path.relative_to(ROOT).as_posix(): base.file_pin(path) for path in sources if path.is_relative_to(ROOT)}
    require(len(pins) == 19 and pins == donor['java_sources'], 'Retain all 19 memory-protected Java sources')
    for name, expected in donor['preserved_sources'].items(): base.checked_file(ROOT/name, expected)
    base.checked_file(ROOT/'android/interactive/src/main/AndroidManifest.xml', donor['source_manifest'])
    for name, expected in donor['payloads'].items():
        if name.startswith('assets/runtime/') and (name.endswith('.py') or name.endswith('/task-gate.json')):
            if Path(name).name not in HELPERS: base.checked_file(ROOT/'android/guest'/Path(name).name, expected)
    require({name for name in HELPERS if base.file_pin(ROOT/'android/guest'/name) !=
        donor['payloads']['assets/runtime/'+name]} == HELPERS, 'Exactly the reviewed startup/appearance helpers must change')
    for name in HELPERS-{'client_visual_assets.py'}:
        validate_guest_delta(name, donor['_helper_sources'][name], (ROOT/'android/guest'/name).read_bytes())
    validate_retained_native_sources(donor)
    return pins






def visual_builder():
    return module('client_appearance_asset_producer', Path(__file__).with_name('prepare_client_appearance_assets.py'))


def visual_guest():
    return module('client_asset_closure_guest_contract', ROOT/'android/guest/client_visual_assets.py')


def validate_visual_package(directory):
    require(directory is not None and directory.is_dir() and not directory.is_symlink(), 'Verified appearance package required')
    for name in VISUAL_ASSETS: builder().checked_file(directory/name)
    producer = visual_builder()
    producer.verify(directory/'client-visual-assets.zip', directory/'client-visual-manifest.json', root=ROOT)
    manifest = read_json(directory/'client-visual-manifest.json')
    require(manifest == json.loads(producer.manifest_bytes(ROOT/'assets/client-appearance-manifest.json')),
        'Appearance supplement differs from the frozen source recipe')
    require(visual_guest().package(directory) == manifest, 'Guest appearance identity/policy differs')
    return {'format': 1, 'manifest': manifest, 'files': {name: builder().file_pin(directory/name) for name in sorted(VISUAL_ASSETS)}}


def validate_visual_superset(donor, visual):
    previous = donor['_visual_manifest']['files']; current = visual['manifest']['files']
    require(len(previous) == 5476 and set(previous) < set(current) and all(current[name] == pin for name, pin in previous.items()),
        'Every immediate 0.13.10 visual leaf must remain byte exact')
    additions = set(current)-set(previous)
    return {'retained_files': len(previous), 'added_files': len(additions),
        'added_bytes': sum(current[name]['bytes'] for name in additions),
        'previous_files_sha256': donor['_visual_manifest']['files_sha256']}


def verify_retained_world_geometry(apk, visual):
    producer = module('retained_world_geometry_verifier', Path(__file__).with_name('prepare_client_visual_assets.py'))
    with zipfile.ZipFile(apk) as archive, tempfile.TemporaryDirectory(prefix='coh-startup-world-') as temporary:
        path = Path(temporary)/'world.zip'
        with archive.open('assets/runtime/atlas-world-supplement.zip') as source, path.open('xb') as target:
            shutil.copyfileobj(source, target, 64*1024)
        producer.verify_preserved_world_geometry(path, visual['manifest'])


def verification_manifests(donor, client, updates, commit, native=None):
    updates = {name: updates[name] for name in sorted(updates)}
    expected_client = copy.deepcopy(client); expected_client['files'].update(updates)
    expected_runtime = copy.deepcopy(donor['runtime_manifest']); expected_runtime['files'].update(updates)
    require(set(expected_client['files']) == set(client['files']) and len(expected_client['files']) <= 64,
        'Client follow-up cannot add verification payload names')
    require(set(expected_runtime['files']) == set(donor['runtime_manifest']['files'])
        and len(expected_runtime['files']) == 64, 'Runtime manifest must retain frozen inventory')
    encoded = shared.encoded(expected_client)
    expected_runtime['files']['client-manifest.json'] = {'bytes': len(encoded), 'sha256': hashlib.sha256(encoded).hexdigest()}
    expected_runtime['repository_commit'] = commit
    expected_runtime['client_startup_followup'] = {'format': 1, 'repository_commit': commit,
        'donor_repository_commit': DONOR_COMMIT, 'retained_setup_memory_repository_commit': RETAINED_SETUP_MEMORY_COMMIT,
        'retained_native_repository_commit': RETAINED_NATIVE_COMMIT,
        'native_dbserver_recompiled': False, 'native_client_recompiled': True, 'native_mapserver_recompiled': False,
        'physical_client_timing_validated': False, 'physical_visual_assets_validated': False,
        'existing_server_cache_and_save_fix_preserved': True,
        'native_manifest_sha256': shared.native_contract.canonical_sha(native) if native else None}
    expected_runtime['scope'] = 'Source-bound Game dependency preload and append-only NPC appearance assets retaining immediate 0.13.10 server/cache/DEX/DLL history; physical candidate validation pending'
    return expected_client, expected_runtime


def extract_and_repair(apk, donor, destination, commit, visual_directory=None, client_directory=None):
    base = builder(); current_sources(donor); visual = validate_visual_package(visual_directory)
    native = validate_native(client_directory, commit, donor)
    validate_visual_superset(donor, visual); verify_visual_streams(apk, visual_directory, donor)
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
    for name in HELPERS:
        source = ROOT/'android/guest'/name; base.checked_file(source)
        require(0 < source.stat().st_size <= 1024*1024, 'Unbounded client guest helper')
        shutil.copyfile(source, assets/name)
    for name in VISUAL_ASSETS: shutil.copyfile(visual_directory/name, assets/name)
    producer = module('followup_world_geometry_verifier', Path(__file__).with_name('prepare_client_visual_assets.py'))
    producer.verify_preserved_world_geometry(assets/'atlas-world-supplement.zip', visual['manifest'])
    replace_client_archive(assets/'client-runtime.zip', donor, native, client_directory)
    updates = {name: base.file_pin(assets/name) for name in HELPERS|VISUAL_ASSETS|NATIVE_ASSETS}
    client, runtime = verification_manifests(donor, donor['_client_verification'], updates, commit, native)
    (assets/'client-manifest.json').write_bytes(shared.encoded(client))
    (assets/'runtime-manifest.json').write_bytes(shared.encoded(runtime))
    payloads = {name: base.file_pin(destination/name) for name in donor['payloads']}
    require({name for name in donor['payloads'] if payloads[name] != donor['payloads'][name]} == REPLACED_PAYLOADS,
        'Unexpected client payload replacement')
    preflight = verify_server_archives(assets)
    require(preflight == donor['server_payload_extraction_preflight'], 'Startup derivative changed retained server extraction')
    return runtime, payloads, visual, preflight


def verify_derivative(apk, donor, payloads, commit, visual_directory=None, client_directory=None):
    require(set(payloads) == set(donor['payloads']) and len(payloads) == 71
        and {name for name in donor['payloads'] if payloads[name] != donor['payloads'][name]} == REPLACED_PAYLOADS,
        'Candidate startup payload boundaries differ')
    visual = validate_visual_package(visual_directory); native = validate_native(client_directory, commit, donor)
    validate_visual_superset(donor, visual); verify_visual_streams(apk, visual_directory, donor)
    base = builder(); base.verify_packaged_payloads(apk, payloads)
    with zipfile.ZipFile(apk) as archive:
        require(archive_inventory(archive) == set(payloads)|set(donor['retained_android_resources'])|
            {'AndroidManifest.xml', 'classes.dex'}, 'Unexpected candidate APK inventory')
        for name, expected in {'classes.dex': donor['retained_dex'], **donor['retained_android_resources']}.items():
            raw = archive.read(name)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == expected, 'Retained Android shell differs')
        for name in HELPERS:
            require(payloads['assets/runtime/'+name] == base.file_pin(ROOT/'android/guest'/name), 'Authored client helper differs: '+name)
        for name in VISUAL_ASSETS:
            require(payloads['assets/runtime/'+name] == base.file_pin(visual_directory/name), 'Verified appearance asset differs: '+name)
        updates = {name: payloads['assets/runtime/'+name] for name in HELPERS|VISUAL_ASSETS|NATIVE_ASSETS}
        expected_client, expected_runtime = verification_manifests(donor, donor['_client_verification'], updates, commit, native)
        require(json.loads(archive.read('assets/runtime/client-manifest.json')) == expected_client
            and json.loads(archive.read('assets/runtime/runtime-manifest.json')) == expected_runtime,
            'Runtime manifest changed beyond startup/appearance pins')
        for name, field in (('native-responsiveness.json', 'native_responsiveness'),
                ('server-animation-manifest.json', 'server_animation_manifest'),
                ('startup-dbserver-manifest.json', 'native_dbserver')):
            require(json.loads(archive.read('assets/runtime/'+name)) == donor[field], 'Retained native/history receipt changed: '+name)
        with archive.open('assets/runtime/client-runtime.zip') as source, tempfile.TemporaryFile() as target:
            shutil.copyfileobj(source, target, 64*1024); target.seek(0)
            verify_client_archive(target, donor, native)
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
            'asset_reimport_required', 'java_or_dex_recompiled', 'native_dbserver_recompiled',
            'native_mapserver_recompiled'))
        and receipt.get('native_client_recompiled') is True
        and receipt.get('native_client_compiled_in_current_run') is True
        and receipt.get('native_client_package_reused') is False
        and receipt.get('runtime_refresh_required') is True and receipt.get('previous_runtime_generation_retained') is True
        and receipt.get('setup_memory_guards_preserved') is True and receipt.get('retained_server_cache_and_save_fix_verified') is True
        and receipt.get('postgresql_emission_fixture_verified') is True
        and receipt.get('changed_java_sources') == [] and receipt.get('retained_java_sources') == 19
        and receipt.get('authored_java_sources_verified') == 19 and receipt.get('retained_baseline_payloads_verified') == 71
        and receipt.get('postgresql_emission_fixtures') == ['cancelled_child_deletion_commits', 'delete_insert_replacement_commits', 'duplicate_insert_23505_rollback']
        and type(receipt.get('tests_run')) is int and receipt['tests_run'] > 0
        and set(receipt.get('checks', {})) == set(CHECKS) and all(value is True for value in receipt['checks'].values()),
        'Exact client asset qualification required')
    require(SOURCE_FILES <= set(receipt.get('source_files', {})), 'Qualification source closure incomplete')
    contract = module('client_asset_closure_qualification_contract', ROOT/QUALIFICATION_SCRIPT)
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


def extract_baseline(args):
    base = builder(); base.checked_file(args.donor_apk, DONOR_APK)
    donor = validate_donor_receipt(args.donor_build_report)
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh appearance baseline directory required')
    args.output.mkdir(parents=True)
    with zipfile.ZipFile(args.donor_apk) as archive:
        for name in VISUAL_ASSETS:
            member = 'assets/runtime/'+name
            target = args.output/name
            with archive.open(member) as source, target.open('xb') as output: shutil.copyfileobj(source, output, 64*1024)
            base.checked_file(target, donor['payloads'][member])


def verify_discovery_plan(args):
    evidence = visual_builder().verify_discovery_plan(args.directory, args.manifest, root=ROOT)
    print('Reproduced frozen source discovery:', evidence)


def build(args):
    base, current = builder(), builder(repaired=True); commit = base.source_commit(args.repository_commit)
    donor = validate_donor(args.donor_apk, args.donor_build_report)
    qualification = validate_qualification(read_json(args.qualification), commit)
    visual = validate_visual_package(args.visual_directory); conservation = validate_visual_superset(donor, visual)
    native = validate_native(args.client_directory, commit, donor)
    streams = verify_visual_streams(args.donor_apk, args.visual_directory, donor)
    require(qualification.get('visual_original_streams') == streams, 'Original visual streams differ from qualification')
    require(qualification.get('visual_package') == visual, 'Visual asset package changed after host qualification')
    require(qualification.get('visual_superset') == conservation, 'Immediate donor visual conservation differs from qualification')
    require(qualification.get('native_client_startup_followup') == native, 'Native startup package changed after host qualification')
    password = base.signing_password_spec(args.password_env)
    base.verify_signing_identity(args.keystore, 'coh-client-interactive', SIGNER, password)
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), 'Fresh client asset APK required')
    base.checked_file(args.testing_notes); require(0 < args.testing_notes.stat().st_size <= 65536, 'Bounded testing notes required')
    for tool in (args.android_jar, args.build_tools/'aapt2', args.build_tools/'zipalign', args.build_tools/'lib/apksigner.jar'):
        require(tool.is_file() and not tool.is_symlink(), 'Required Android tool missing')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-client-visual-', dir=args.output.parent) as temporary:
        work = Path(temporary)
        runtime, payloads, visual, preflight = extract_and_repair(args.donor_apk, donor, work/'donor', commit, args.visual_directory, args.client_directory)
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
        verify_derivative(signed, donor, payloads, commit, args.visual_directory, args.client_directory)
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
            'retained_dex': donor['retained_dex'], 'donor': donor_link(), 'java_sources': current_sources(donor),
            'changed_java_sources': [], 'added_java_sources': [], 'preserved_sources': donor['preserved_sources'],
            'generated_manifest': base.file_pin(manifest), 'qualification': qualification,
            'qualification_receipt': base.file_pin(args.qualification), 'testing_notes': base.file_pin(args.testing_notes),
            'native_libraries_changed': False, 'client_or_server_recompiled': True, 'java_or_dex_recompiled': False,
            'world_assets_changed': False, 'prepared_cache_archive_changed': False, 'dbserver_changed': False,
            'graphics_driver_changed': False, 'physical_gameplay_validated': False, 'physical_client_timing_validated': False,
            'physical_visual_assets_validated': False, 'runtime_refresh_required': True, 'installed_runtime_identity_preserved': False,
            'previous_runtime_generation_retained': True, 'asset_reimport_required': False, 'setup_memory_guards_preserved': True,
            'native_dbserver_recompiled': False, 'native_client_recompiled': True, 'native_mapserver_recompiled': False,
            'retained_server_cache_and_save_fix_verified': True, 'visual_package': visual, 'visual_superset': conservation,
            'visual_original_streams': streams,
            'retained_java_sources': 19, 'native_client_compiled_in_current_run': True,
            'native_client_package_reused': False, 'native_client_startup_followup': native,
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
    streams = verify_visual_streams(args.donor_apk, args.visual_directory, donor)
    require(qualification.get('visual_original_streams') == streams, 'Original visual streams differ from qualification')
    require(qualification.get('visual_package') == visual, 'Visual asset package changed after host qualification')
    require(qualification.get('visual_superset') == conservation, 'Immediate donor visual conservation differs from qualification')
    require(qualification.get('native_client_startup_followup') == native, 'Native startup package changed after host qualification')
    require(report.get('format') == 1 and report.get('apk') == APK_NAME and report.get('repository_commit') == commit
        and report.get('runtime_repository_commit') == commit and report.get('retained_runtime_repository_commit') == DONOR_COMMIT
        and report.get('retained_setup_memory_repository_commit') == RETAINED_SETUP_MEMORY_COMMIT
        and report.get('retained_native_repository_commit') == RETAINED_NATIVE_COMMIT
        and report.get('abi') == 'arm64-v8a' and report.get('scope') == QUALIFICATION_SCOPE
        and report.get('application_id') == base.APP_ID and report.get('version_name') == VERSION_NAME
        and report.get('version_code') == VERSION_CODE and report.get('signer_certificate_sha256') == SIGNER
        and report.get('signing_key_created') is False and report.get('donor') == donor_link()
        and report.get('qualification') == qualification and report.get('qualification_receipt') == base.file_pin(args.qualification)
        and report.get('java_sources') == current_sources(donor) and report.get('changed_java_sources') == []
        and report.get('added_java_sources') == [] and report.get('retained_dex') == donor['retained_dex']
        and report.get('preserved_sources') == donor['preserved_sources']
        and report.get('visual_superset') == conservation and report.get('visual_original_streams') == streams
        and report.get('retained_java_sources') == 19
        and report.get('native_client_compiled_in_current_run') is True and report.get('native_client_package_reused') is False
        and report.get('native_client_startup_followup') == native
        and report.get('changed_apk_payloads') == sorted(REPLACED_PAYLOADS|ADDED_PAYLOADS)
        and report.get('replaced_apk_payloads') == sorted(REPLACED_PAYLOADS) and report.get('added_apk_payloads') == sorted(ADDED_PAYLOADS)
        and all(report.get(key) is True for key in ('signature_verified', 'package_badging_verified', 'binary_manifest_version_only_verified',
            'payload_bytes_verified', 'previous_runtime_generation_retained', 'runtime_refresh_required', 'setup_memory_guards_preserved',
            'retained_server_cache_and_save_fix_verified', 'client_or_server_recompiled', 'native_client_recompiled'))
        and all(report.get(key) is False for key in ('native_libraries_changed', 'java_or_dex_recompiled',
            'world_assets_changed', 'prepared_cache_archive_changed', 'dbserver_changed', 'graphics_driver_changed',
            'physical_gameplay_validated', 'physical_client_timing_validated', 'physical_visual_assets_validated',
            'native_dbserver_recompiled', 'native_mapserver_recompiled',
            'installed_runtime_identity_preserved', 'asset_reimport_required'))
        and report.get('visual_package') == visual and all(report.get(name) == donor[name] for name in RETAINED_RECEIPT_FIELDS),
        'Client asset build receipt differs')
    base.checked_file(args.apk, report); verify_derivative(args.apk, donor, report['payloads'], commit, args.visual_directory, args.client_directory)
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
        'name': 'COH Atlas Gameplay 0.13.11 — NPC appearance and guarded client startup', 'body': body,
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
    api = module('client_asset_closure_github', Path(__file__).with_name('build_atlas_gameplay_apk.py'))
    print('Published client asset prerelease:', publish_release(api.GitHub(os.environ.get('GH_TOKEN')), report,
        (args.apk, checksum, public_notes), public_notes.read_text()))


def audit(args):
    commit = builder().source_commit(args.repository_commit); report, _, _ = verify_report(args, commit)
    print('Public APK independently verified:', report['sha256'], 'source-bound Game with retained 0.13.10 servers, DLLs and DEX')



def validate_guest_delta(name, previous, current):
    """Permit only reviewed binding functions; retain imports/constants and other AST nodes."""
    allowed = {
        'native_responsiveness_contract.py': {'client_contract', 'client_startup_followup_contract'},
        'client_startup_diagnostic.py': {'prepare_worktree', 'ClientStartupDiagnostic.initialize',
            'ClientStartupDiagnostic.execute', 'verify_assets'},
        'texture_header_index.py': {'prepare'},
    }
    require(name in allowed, 'No reviewed guest delta contract: '+name)
    def selected(tree):
        return {node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))} | {
            cls.name+'.'+node.name: node for cls in tree.body if isinstance(cls, ast.ClassDef)
            for node in cls.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    before, after = (ast.parse(raw.decode()) for raw in (previous, current))
    old, new = selected(before), selected(after)
    require(set(old)-set(new) == set(), 'Guest binding removes an existing function')
    changed = {key for key in new if key not in old or ast.dump(old[key], include_attributes=False) != ast.dump(new[key], include_attributes=False)}
    require(changed and changed <= allowed[name], 'Guest changes outside reviewed startup binding: '+repr(sorted(changed)))
    if name == 'client_startup_diagnostic.py':
        expected = copy.deepcopy(old['verify_assets'])
        for node in ast.walk(expected):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'limit':
                expression = ast.parse("1024*1024*1024 if name == 'client-visual-assets.zip' else 64*1024*1024 if name == 'client-visual-manifest.json' else CACHE_BYTES_LIMIT if name in ('client-caches.zip', 'server-caches.zip') else 256*1024*1024 if name == 'atlas-world-supplement.zip' else 128*1024*1024", mode='eval').body
                node.value = expression
        require(ast.dump(expected, include_attributes=False) == ast.dump(new['verify_assets'], include_attributes=False),
            'Startup verifier differs beyond the exact appearance payload caps')
    if name == 'native_responsiveness_contract.py':
        require(set(new)-set(old) == {'client_startup_followup_contract'}, 'Require one typed native follow-up contract')
    else:
        require(set(new) == set(old), 'Startup function inventory must remain unchanged')
    for cls in list(after.body):
        if isinstance(cls, (ast.FunctionDef, ast.AsyncFunctionDef)) and cls.name in changed:
            if cls.name in old: after.body[after.body.index(cls)] = copy.deepcopy(old[cls.name])
            else: after.body.remove(cls)
        elif isinstance(cls, ast.ClassDef):
            cls.body = [copy.deepcopy(old[cls.name+'.'+node.name])
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and cls.name+'.'+node.name in changed
                else node for node in cls.body]
    require(ast.dump(before, include_attributes=False) == ast.dump(after, include_attributes=False),
        'Guest module imports/constants/class state changed outside reviewed binding')
    return {'changed_functions': sorted(changed), 'all_other_ast_nodes_retained': True}


def visual_stream_pin(archive, entry):
    archive.fp.seek(entry.header_offset)
    header = archive.fp.read(30)
    require(len(header) == 30 and header[:4] == b'PK\x03\x04', 'Invalid retained ZIP local header')
    filename_bytes = int.from_bytes(header[26:28], 'little'); extra_bytes = int.from_bytes(header[28:30], 'little')
    archive.fp.seek(filename_bytes+extra_bytes, 1)
    digest = hashlib.sha256(); remaining = entry.compress_size
    while remaining:
        raw = archive.fp.read(min(remaining, 64*1024)); require(raw, 'Truncated original compressed stream')
        digest.update(raw); remaining -= len(raw)
    return {'sha256': digest.hexdigest(), 'metadata': [entry.file_size, entry.compress_size, entry.CRC,
        entry.compress_type, entry.external_attr, list(entry.date_time), entry.flag_bits]}


def verify_visual_streams(apk, directory, donor):
    """Keep the exact old compressed stream and metadata, pinned from the verified donor."""
    pins = donor.get('_visual_stream_pins', {})
    require(set(pins) == set(donor['_visual_manifest']['files']) and len(pins) == 5476,
        'Exact immediate donor compressed-stream inventory required')
    with zipfile.ZipFile(directory/'client-visual-assets.zip') as current:
        for name, expected in pins.items():
            require(visual_stream_pin(current, current.getinfo(name)) == expected,
                'Previous compressed visual stream changed: '+name)
    return {'retained_compressed_streams': 5476, 'all_streams_byte_identical': True}


def native_builder():
    return module('client_startup_followup_native_producer', Path(__file__).with_name('package_client_startup_followup_native.py'))


def validate_native(directory, commit, donor):
    producer = native_builder(); native = producer.validate_package(directory, commit)
    require(native.get('repository_commit') == commit
        and native.get('base_client_executable') == donor['native_client_loading']['files']['CityOfHeroes.exe']
        and native.get('retained_source_inputs') == donor['native_responsiveness']['build_inputs']
        and native.get('schema_sources_sha256') == donor['native_responsiveness']['retained_cache']['schema_sources_sha256']
        and native.get('files', {}).get('CityOfHeroes.exe') != donor['native_client_loading']['files']['CityOfHeroes.exe']
        and native.get('build_targets') == ['Game'] and native.get('replacement_scope') == 'CityOfHeroes.exe_only'
        and native.get('retained_native_dependencies_changed') is False,
        'Native startup layer changes retained schema/native dependency ancestry')
    return native


def client_manifest(donor, native):
    expected = copy.deepcopy(donor['_native_client_manifest'])
    expected['files']['CityOfHeroes.exe'] = native['files']['CityOfHeroes.exe']
    expected['dependency_report'] = shared.dependency_report(expected['files'])
    require(not expected['dependency_report']['unresolved'], 'New Game imports exceed retained DLL closure')
    expected['client_startup_followup'] = {'manifest': native, 'manifest_sha256': shared.native_contract.canonical_sha(native),
        'base_client_loading_manifest_sha256': shared.native_contract.canonical_sha(donor['native_client_loading']),
        'base_client_executable': donor['native_client_loading']['files']['CityOfHeroes.exe']}
    shared.native_contract.client_contract(expected, donor['native_responsiveness'])
    return expected


def replace_client_archive(path, donor, native, directory):
    require(builder().file_pin(path) == donor['payloads']['assets/runtime/client-runtime.zip'], 'Client archive donor differs')
    output = path.with_suffix('.candidate.zip'); require(not output.exists(), 'Fresh native client staging required')
    expected = client_manifest(donor, native)
    with zipfile.ZipFile(path) as previous, zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        require(startup.client_member_pins(previous) == donor['_client_members'], 'Extracted native client members differ')
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
        require(json.loads(archive.read('client-package.json')) == expected, 'Client package drifted beyond startup layer')
        raw = shared.encoded(expected)
        require(pins['client-package.json'] == {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}, 'Native client manifest encoding differs')
        record = native['files']['CityOfHeroes.exe']
        require(pins['CityOfHeroes.exe'] == {'bytes': record['size'], 'sha256': record['sha256']}, 'Packaged new Game differs')
        require(all(pins[name] == pin for name, pin in donor['_client_members'].items()
            if name not in ('CityOfHeroes.exe', 'client-package.json')), 'A retained client DLL changed')
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest='command', required=True)
    get = commands.add_parser('download-donor'); get.add_argument('--output', type=Path, required=True)
    get_baseline = commands.add_parser('extract-baseline')
    for name in ('donor-apk', 'donor-build-report', 'output'):
        get_baseline.add_argument('--'+name, type=Path, required=True)
    replay = commands.add_parser('verify-discovery-plan')
    replay.add_argument('--directory', type=Path, required=True)
    replay.add_argument('--manifest', type=Path, required=True)
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
    {'download-donor': download, 'extract-baseline': extract_baseline, 'verify-discovery-plan': verify_discovery_plan, 'build': build, 'publish': publish, 'audit-public': audit}[args.command](args)


if __name__ == '__main__': main()
