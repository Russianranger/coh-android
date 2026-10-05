#!/usr/bin/env python3
"""Package an append-only UI sweep and verified Atlas beacons over public 0.13.13.

The saved character, SQL repair, native Game, Android shell and every retained
runtime payload are conserved against the exact published APK and build receipt.
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

import build_reopen_startup_repair_apk as previous

ROOT, require, module, shared = previous.ROOT, previous.require, previous.module, previous.shared
REPOSITORY, BRANCH, SIGNER = previous.REPOSITORY, previous.BRANCH, previous.SIGNER
DONOR_COMMIT = 'be955678b4b82f889b31c4071b3b979b0aef6771'
DONOR_RUN_ID = 37324515114
DONOR_APK_NAME = 'COH-Atlas-Gameplay-0.13.13.apk'
DONOR_APK = {'bytes': 1535592811, 'sha256': '81f199d6380faa09261a85efea6fd3abca6ed58749b8cc68c75d1cd579d454a4'}
DONOR_BUILD = {'bytes': 62348362, 'sha256': 'bf8ae4305601c2c8f1d78412c8cd8a5ee868a7149418a95ef08abd62593513a0'}
DONOR_URL = 'https://github.com/'+REPOSITORY+'/releases/download/coh-atlas-gameplay-v0.13.13/'+DONOR_APK_NAME
VERSION_NAME, VERSION_CODE = '0.13.14', 29
APK_NAME = 'COH-Atlas-Gameplay-0.13.14.apk'
REPORT_NAME = 'ui-beacon-apk-build-report.json'
NOTES_NAME = 'COH-Atlas-Gameplay-0.13.14-testing.txt'
NOTES = ROOT/'docs'/NOTES_NAME
RELEASE_TAG = 'coh-atlas-gameplay-v0.13.14'
WORKFLOW = '.github/workflows/android-ui-beacon.yml'
QUALIFICATION_SCRIPT = 'tools/android/interactive/qualify_ui_beacon.py'
QUALIFICATION_SCOPE = 'append_only_original_ui_sweep_and_authentic_atlas_beacons_retaining_public_0_13_13'
VISUAL_ASSETS = frozenset({'client-visual-assets.zip', 'client-visual-manifest.json'})
HELPERS = frozenset({'client_visual_assets.py', 'native_training_save.py', 'local_character_server.py'})
# Filled by the reviewed server-only beacon producer, never inferred from a folder.
BEACON_ASSETS = frozenset({'atlas-beacons.zip', 'atlas-beacon-manifest.json'})
ADDED_HELPERS = frozenset({'atlas_beacon_package.py'})
UPDATES = VISUAL_ASSETS | HELPERS | BEACON_ASSETS | ADDED_HELPERS
REPLACED_PAYLOADS = frozenset('assets/runtime/'+name for name in VISUAL_ASSETS|HELPERS|{'client-manifest.json', 'runtime-manifest.json'})
ADDED_PAYLOADS = frozenset('assets/runtime/'+name for name in BEACON_ASSETS|ADDED_HELPERS)
SOURCE_FILES = frozenset({WORKFLOW, QUALIFICATION_SCRIPT,
    '.github/workflows/android-atlas-beacon-generation.yml',
    'tools/android/interactive/build_ui_beacon_apk.py', 'tools/android/interactive/test_ui_beacon_package.py',
    'tools/android/interactive/discover_client_ui_sweep_assets.py',
    'tools/android/interactive/prepare_client_ui_sweep_assets.py',
    'tools/android/interactive/test_client_ui_sweep_assets.py',
    'tools/android/interactive/test_client_ui_repair_assets.py',
    'tools/prepare_atlas_beacon_generator_source.py',
    'patches/atlas-beacons/0001-host-only-atlas-generator.patch',
    'tools/android/interactive/generate_atlas_beacons.py',
    'tools/android/interactive/test_atlas_beacon_package.py',
    'tools/android/interactive/test_generate_atlas_beacons.py',
    'tools/test_prepare_atlas_beacon_generator_source.py',
    'tools/android/interactive/test_training_save.py',
    'tools/android/interactive/fixtures/thor-training-normalization-0.13.13-20261005.json',
    'assets/client-ui-sweep-manifest.json', 'assets/client-ui-sweep-requests.json', 'assets/client-ui-sweep-plan.json',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    *('android/guest/'+name for name in HELPERS|ADDED_HELPERS), 'docs/'+NOTES_NAME})
REVIEWED_DONOR_SOURCE_CHANGES = SOURCE_FILES
CHECKS = ('missing_only_original_ui_and_all_previous_encoded_streams_verified',
    'authentic_atlas_beacon_provenance_and_installation_verified',
    'retained_gameplay_training_postgresql_preload_and_cache_guards_verified',
    'exact_payload_boundaries_android_shell_and_actual_server_extraction_verified')
RETAINED_REPORT_FIELDS = tuple(name for name in previous.RETAINED_REPORT_FIELDS
    if name not in ('visual_package', 'visual_superset', 'visual_original_streams')) + ('native_dbserver', 'native_levelup_ui_repair')


def builder(*, repaired=False):
    base = previous.builder()
    if repaired: base.VERSION_NAME, base.VERSION_CODE, base.APK_NAME = VERSION_NAME, VERSION_CODE, APK_NAME
    return base


def read_json(path):
    path = Path(path)
    limit = 256*1024**2 if path.name in (REPORT_NAME, previous.REPORT_NAME, 'ui-beacon-qualification.json') else 64*1024**2 if path.name == 'client-visual-manifest.json' else 8*1024**2
    require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= limit,
        'Missing, linked or unbounded UI/beacon receipt: '+path.name)
    return json.loads(path.read_text())


def donor_link():
    return {'run_id': DONOR_RUN_ID, 'repository_commit': DONOR_COMMIT, 'apk': DONOR_APK, 'build_report': DONOR_BUILD}


def validate_donor_receipt(path):
    builder().checked_file(path, DONOR_BUILD)
    donor = read_json(path); q = donor.get('qualification', {})
    require(donor.get('format') == 1 and donor.get('repository_commit') == DONOR_COMMIT
        and donor.get('runtime_repository_commit') == DONOR_COMMIT and donor.get('apk') == DONOR_APK_NAME
        and {key: donor.get(key) for key in DONOR_APK} == DONOR_APK
        and donor.get('application_id') == builder().APP_ID and donor.get('version_name') == '0.13.13'
        and donor.get('version_code') == 28 and donor.get('abi') == 'arm64-v8a'
        and donor.get('signer_certificate_sha256') == SIGNER and donor.get('signing_key_created') is False
        and all(donor.get(key) is True for key in ('signature_verified', 'package_badging_verified',
            'binary_manifest_version_only_verified', 'payload_bytes_verified', 'setup_memory_guards_preserved'))
        and len(donor.get('payloads', {})) == 72 and len(donor.get('java_sources', {})) == 19
        and q.get('scope') == previous.QUALIFICATION_SCOPE and q.get('status') == 'passed'
        and q.get('tests_run') == 985 and len(q.get('source_files', {})) == 6815
        and q.get('repository_commit') == DONOR_COMMIT and donor.get('donor') == previous.donor_link()
        and donor.get('native_dbserver') == donor.get('native_levelup_ui_repair')
        and donor['payloads']['assets/runtime/startup-dbserver.exe']['sha256'] ==
            'ea1d43d7a1ed61559376563bd8bad68987fbf47a4ec41f0d6fe8fe16cfe933ba'
        and donor.get('server_payload_extraction_preflight', {}).get('status') == 'passed',
        'Exact public 0.13.13 donor receipt differs')
    return donor


def validate_retained_sources(donor):
    pins = donor['qualification']['source_files']
    require(len(pins) == 6815, 'Published donor source closure differs')
    for name, pin in pins.items():
        require(isinstance(name, str) and not Path(name).is_absolute() and '..' not in Path(name).parts, 'Unsafe donor source path')
        if name not in REVIEWED_DONOR_SOURCE_CHANGES: builder().checked_file(ROOT/name, pin)
    return sorted(set(pins)-REVIEWED_DONOR_SOURCE_CHANGES)


def validate_donor(apk, receipt):
    base = builder(); base.checked_file(apk, DONOR_APK)
    donor = validate_donor_receipt(receipt); base.verify_packaged_payloads(apk, donor['payloads'])
    with zipfile.ZipFile(apk) as archive:
        shell = {'classes.dex': donor['retained_dex'], **donor['retained_android_resources']}
        require(previous.prior.archive_inventory(archive) == set(donor['payloads'])|set(shell)|{'AndroidManifest.xml'}, 'Unexpected donor APK inventory')
        for name, pin in shell.items():
            raw = archive.read(name)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == pin, 'Donor Android shell differs')
        for name, field in (('runtime-manifest.json', 'runtime_manifest'), ('native-responsiveness.json', 'native_responsiveness'),
                ('server-animation-manifest.json', 'server_animation_manifest'), ('startup-dbserver-manifest.json', 'native_dbserver')):
            require(json.loads(archive.read('assets/runtime/'+name)) == donor[field], 'Donor provenance differs: '+name)
        donor['_client_verification'] = json.loads(archive.read('assets/runtime/client-manifest.json'))
        donor['_helper_sources'] = {name: archive.read('assets/runtime/'+name) for name in HELPERS}
        donor['_visual_manifest'] = json.loads(archive.read('assets/runtime/client-visual-manifest.json'))
        require(donor['_visual_manifest'] == donor['visual_package']['manifest'] and donor['_visual_manifest']['file_count'] == 9613,
            'Exact public visual manifest differs')
        with archive.open('assets/runtime/client-visual-assets.zip') as source, tempfile.TemporaryFile() as target:
            shutil.copyfileobj(source, target, 64*1024); target.seek(0)
            with zipfile.ZipFile(target) as visual:
                donor['_visual_stream_pins'] = {name: previous.prior.visual_stream_pin(visual, visual.getinfo(name))
                    for name in sorted(donor['_visual_manifest']['files'])}
    require(previous.prior.verify_apk_server_archives(apk) == donor['server_payload_extraction_preflight'], 'Donor actual server extraction differs')
    validate_retained_sources(donor)
    return donor


def current_sources(donor):
    base = builder(); sources = previous.prior.retained.java_sources(base, ROOT/'out/no-generated-java')
    pins = {path.relative_to(ROOT).as_posix(): base.file_pin(path) for path in sources if path.is_relative_to(ROOT)}
    require(len(pins) == 19 and pins == donor['java_sources'], 'Retain all 19 memory-protected Java sources')
    for name, pin in donor['preserved_sources'].items(): base.checked_file(ROOT/name, pin)
    base.checked_file(ROOT/'android/interactive/src/main/AndroidManifest.xml', donor['source_manifest'])
    for name, pin in donor['payloads'].items():
        if name.startswith('assets/runtime/') and (name.endswith('.py') or name.endswith('/task-gate.json')):
            if Path(name).name not in HELPERS: base.checked_file(ROOT/'android/guest'/Path(name).name, pin)
    require({name for name in HELPERS if base.file_pin(ROOT/'android/guest'/name) != donor['payloads']['assets/runtime/'+name]} == HELPERS,
        'Exactly reviewed installed helpers must change')
    validate_guest_delta('native_training_save.py', donor['_helper_sources']['native_training_save.py'], (ROOT/'android/guest/native_training_save.py').read_bytes())
    validate_guest_delta('local_character_server.py', donor['_helper_sources']['local_character_server.py'], (ROOT/'android/guest/local_character_server.py').read_bytes())
    validate_retained_sources(donor)
    return pins


def validate_guest_delta(name, before_raw, after_raw):
    before, after = (ast.parse(raw.decode()) for raw in (before_raw, after_raw))
    changes = []
    if name == 'native_training_save.py':
        amended, added = {'verify'}, {'verify_reopen_normalization'}
        for node in list(after.body):
            if isinstance(node, ast.FunctionDef) and node.name in amended:
                old = next(item for item in before.body if isinstance(item, ast.FunctionDef) and item.name == node.name)
                require(ast.dump(old) != ast.dump(node), 'Reviewed training function must change')
                after.body[after.body.index(node)] = copy.deepcopy(old); changes.append(node.name)
            elif isinstance(node, ast.FunctionDef) and node.name in added:
                after.body.remove(node); changes.append(node.name)
            elif isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'CANONICAL_POWERS' for target in node.targets):
                expected = ast.parse('CANONICAL_POWERS = {name.casefold(): name for name in (*AUTO_POWERS, *PURCHASABLE)}').body[0]
                require(ast.dump(node) == ast.dump(expected), 'Canonical native names must derive solely from finite existing powers')
                after.body.remove(node); changes.append('CANONICAL_POWERS')
        require(set(changes) == amended|added|{'CANONICAL_POWERS'}, 'Complete reviewed normalization delta required')
    elif name == 'local_character_server.py':
        amended = {'validate_saved_rows', 'saved_selected_rows_match', 'saved_metadata'}
        old_class = next(node for node in before.body if isinstance(node, ast.ClassDef) and node.name == 'LocalCharacterReopenServer')
        new_class = next(node for node in after.body if isinstance(node, ast.ClassDef) and node.name == old_class.name)
        for node in list(new_class.body):
            if isinstance(node, ast.FunctionDef) and node.name in amended:
                old = next(item for item in old_class.body if isinstance(item, ast.FunctionDef) and item.name == node.name)
                require(ast.dump(old) != ast.dump(node), 'Reviewed save method must change')
                new_class.body[new_class.body.index(node)] = copy.deepcopy(old); changes.append(node.name)
        require(set(changes) == amended, 'Complete reviewed save method delta required')
        old_atlas = next(node for node in before.body if isinstance(node, ast.ClassDef) and node.name == 'LocalCharacterServer')
        new_atlas = next(node for node in after.body if isinstance(node, ast.ClassDef) and node.name == old_atlas.name)
        method = next(node for node in new_atlas.body if isinstance(node, ast.FunctionDef) and node.name == 'prepare_runtime')
        exact = ast.parse('''beacon_archive = self.owner.args.assets / 'atlas-beacons.zip'
beacon_manifest = self.owner.args.assets / 'atlas-beacon-manifest.json'
if beacon_archive.exists() or beacon_manifest.exists():
    import atlas_beacon_package
    installed = atlas_beacon_package.install(beacon_archive, beacon_manifest,
        self.runtime, context=self.ctx,
        imported_inputs_readonly=receipt.get('imported_inputs_readonly'))
    self.creation_report['atlas_beacon_graph'] = installed
    self.ctx.report['atlas_beacon_graph'] = installed
''').body
        locations = [index for index in range(len(method.body)-len(exact)+1)
            if [ast.dump(node) for node in method.body[index:index+len(exact)]] == [ast.dump(node) for node in exact]]
        require(len(locations) == 1, 'Exactly the reviewed lazy native beacon installer block is required')
        index = locations[0]
        require(index+len(exact) < len(method.body) and isinstance(method.body[index+len(exact)], ast.Assign)
            and ast.unparse(method.body[index+len(exact)].targets[0]) == "self.creation_report['private_map_data']",
            'Beacon installation must precede the qualified private map data receipt')
        del method.body[index:index+len(exact)]
        changes.append('LocalCharacterServer.prepare_runtime.beacon_install')
    else:
        raise ValueError('Unreviewed guest helper delta')
    require(ast.dump(before, include_attributes=False) == ast.dump(after, include_attributes=False), 'Guest changes outside reviewed UI/beacon/save scope')
    return {'changed_functions': sorted(changes), 'all_other_ast_nodes_retained': True}


def visual_builder():
    return module('client_ui_sweep_asset_producer', Path(__file__).with_name('prepare_client_ui_sweep_assets.py'))


def validate_visual_package(directory):
    require(directory is not None and directory.is_dir() and not directory.is_symlink(), 'Verified UI package required')
    for name in VISUAL_ASSETS: builder().checked_file(directory/name)
    producer = visual_builder()
    producer.verify(directory/'client-visual-assets.zip', directory/'client-visual-manifest.json', root=ROOT)
    manifest = read_json(directory/'client-visual-manifest.json')
    require(manifest == json.loads(producer.manifest_bytes(ROOT/'assets/client-ui-sweep-manifest.json')), 'UI sweep differs from frozen source recipe')
    guest = module('ui_sweep_guest_contract', ROOT/'android/guest/client_visual_assets.py')
    require(guest.package(directory) == manifest, 'Guest UI identity/policy differs')
    return {'format': 1, 'manifest': manifest, 'files': {name: builder().file_pin(directory/name) for name in sorted(VISUAL_ASSETS)}}


def validate_visual_superset(donor, visual):
    before, after = donor['_visual_manifest']['files'], visual['manifest']['files']
    require(len(before) == 9613 and set(before) < set(after) and all(after[name] == pin for name, pin in before.items()),
        'Every public 0.13.13 visual leaf must remain byte exact')
    additions = set(after)-set(before)
    require(all(name.endswith('.texture') for name in additions), 'Only exact original UI textures may be appended')
    return {'retained_files': len(before), 'added_files': len(additions), 'added_bytes': sum(after[name]['bytes'] for name in additions),
        'previous_files_sha256': donor['_visual_manifest']['files_sha256']}


def verify_visual_streams(apk, directory, donor):
    pins = donor.get('_visual_stream_pins', {})
    require(set(pins) == set(donor['_visual_manifest']['files']) and len(pins) == 9613, 'Exact donor encoded stream inventory required')
    with zipfile.ZipFile(directory/'client-visual-assets.zip') as current:
        for name, pin in pins.items():
            require(previous.prior.visual_stream_pin(current, current.getinfo(name)) == pin, 'Retained encoded visual stream changed: '+name)
    return {'retained_compressed_streams': 9613, 'all_streams_byte_identical': True}


def validate_beacons(directory, commit, donor):
    require(directory is not None and directory.is_dir() and not directory.is_symlink(), 'Verified native Atlas beacon package required')
    producer = module('native_atlas_beacon_producer', Path(__file__).with_name('generate_atlas_beacons.py'))
    validated_manifest = producer.validate_package(directory, commit)
    report = read_json(directory/'atlas-beacon-generation-report.json')
    require(report.get('cleanup_complete') is True and report.get('owned_roles') == 4
        and report.get('native_worker_spawning_allowed') is False, 'Native producer ownership/cleanup evidence differs')
    manifest = read_json(directory/'atlas-beacon-manifest.json')
    require(validated_manifest == manifest, 'Validated native graph manifest differs')
    require(manifest.get('role') == 'authentic_native_atlas_beacon_graph' and manifest.get('runtime_graph_readback') is True
        and manifest.get('physical_npc_pathing_validated') is False, 'Native graph proof scope differs')
    geo = {name: value for name, value in donor['_visual_manifest']['files'].items() if name.endswith('.geo')}
    require(manifest.get('input_identity', {}).get('world_manifest') == donor['payloads']['assets/runtime/atlas-world-supplement-manifest.json']
        and manifest['input_identity'].get('visual_geometry_sha256') == hashlib.sha256(producer.canonical(geo)).hexdigest(),
        'Native beacons do not match the exact shipped world geometry')
    guest = module('atlas_beacon_guest_contract', ROOT/'android/guest/atlas_beacon_package.py')
    require(guest.read_manifest(directory/'atlas-beacon-manifest.json') == manifest, 'Guest beacon identity/policy differs')
    require(guest.ARCHIVE_BYTES == builder().file_pin(directory/'atlas-beacons.zip')['bytes']
        and guest.ARCHIVE_SHA256 == builder().file_pin(directory/'atlas-beacons.zip')['sha256'], 'Guest beacon archive pin differs')
    return {'format': 1, 'manifest': manifest, 'generation': report,
        'files': {name: builder().file_pin(directory/name) for name in sorted(BEACON_ASSETS)}}


def verification_manifests(donor, updates, commit, visual, beacons):
    require(set(updates) == UPDATES, 'Unexpected UI/beacon replacement inputs')
    client = copy.deepcopy(donor['_client_verification']); client['files'].update(updates)
    runtime = copy.deepcopy(donor['runtime_manifest']); runtime['files'].update(updates)
    encoded = shared.encoded(client)
    runtime['files']['client-manifest.json'] = {'bytes': len(encoded), 'sha256': hashlib.sha256(encoded).hexdigest()}
    runtime['repository_commit'] = commit
    runtime['ui_beacon'] = {'format': 1, 'repository_commit': commit, 'donor_repository_commit': DONOR_COMMIT,
        'native_dbserver_recompiled': False, 'native_client_recompiled': False, 'native_mapserver_recompiled': False,
        'all_published_visual_resources_retained': True, 'ui_sweep_files_sha256': visual['manifest']['files_sha256'],
        'authentic_atlas_beacons': beacons, 'physical_gameplay_validated': False}
    runtime['scope'] = QUALIFICATION_SCOPE
    require(set(client['files']) == set(donor['_client_verification']['files'])|BEACON_ASSETS|ADDED_HELPERS and
        set(runtime['files']) == set(donor['runtime_manifest']['files'])|BEACON_ASSETS|ADDED_HELPERS, 'Reviewed runtime inventory differs')
    return client, runtime


def extract_and_repair(apk, donor, destination, commit, visual_directory, beacon_directory=None):
    base = builder(); current_sources(donor)
    visual = validate_visual_package(visual_directory); validate_visual_superset(donor, visual)
    verify_visual_streams(apk, visual_directory, donor); beacons = validate_beacons(beacon_directory, commit, donor)
    destination.mkdir(parents=True)
    with zipfile.ZipFile(apk) as archive:
        for entry in archive.infolist():
            if entry.filename == 'AndroidManifest.xml' or entry.filename.startswith('META-INF/'): continue
            require(entry.filename in set(donor['payloads'])|set(donor['retained_android_resources'])|{'classes.dex'}, 'Unexpected donor member')
            target = destination/entry.filename; target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open('xb') as output: shutil.copyfileobj(source, output, 64*1024)
    require(all(base.file_pin(destination/name) == pin for name, pin in donor['payloads'].items()), 'Extracted donor bytes differ')
    assets = destination/'assets/runtime'
    for name in HELPERS|ADDED_HELPERS: shutil.copyfile(ROOT/'android/guest'/name, assets/name)
    for name in VISUAL_ASSETS: shutil.copyfile(visual_directory/name, assets/name)
    for name in BEACON_ASSETS: shutil.copyfile(beacon_directory/name, assets/name)
    updates = {name: base.file_pin(assets/name) for name in UPDATES}
    client, runtime = verification_manifests(donor, updates, commit, visual, beacons)
    for name, value in (('client-manifest.json', client), ('runtime-manifest.json', runtime)): (assets/name).write_bytes(shared.encoded(value))
    payloads = {name: base.file_pin(destination/name) for name in set(donor['payloads'])|ADDED_PAYLOADS}
    require({name for name in donor['payloads'] if payloads[name] != donor['payloads'][name]} == REPLACED_PAYLOADS and
        set(payloads)-set(donor['payloads']) == ADDED_PAYLOADS, 'Unexpected UI/beacon payload replacement')
    preflight = previous.prior.verify_server_archives(assets)
    require(preflight == donor['server_payload_extraction_preflight'], 'Retained server extraction differs')
    return runtime, payloads, preflight, visual, beacons


def verify_derivative(apk, donor, payloads, commit, visual_directory, beacon_directory=None):
    base = builder(); visual = validate_visual_package(visual_directory); validate_visual_superset(donor, visual)
    verify_visual_streams(apk, visual_directory, donor); beacons = validate_beacons(beacon_directory, commit, donor)
    require(set(payloads) == set(donor['payloads'])|ADDED_PAYLOADS and
        {name for name in donor['payloads'] if payloads[name] != donor['payloads'][name]} == REPLACED_PAYLOADS, 'Candidate payload boundaries differ')
    base.verify_packaged_payloads(apk, payloads)
    with zipfile.ZipFile(apk) as archive:
        shell = {'classes.dex': donor['retained_dex'], **donor['retained_android_resources']}
        require(previous.prior.archive_inventory(archive) == set(payloads)|set(shell)|{'AndroidManifest.xml'}, 'Unexpected candidate inventory')
        for name, pin in shell.items():
            raw = archive.read(name); require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == pin, 'Retained Android shell differs')
        for name in HELPERS|ADDED_HELPERS: require(payloads['assets/runtime/'+name] == base.file_pin(ROOT/'android/guest'/name), 'Authored helper differs')
        for name in VISUAL_ASSETS: require(payloads['assets/runtime/'+name] == base.file_pin(visual_directory/name), 'Qualified UI bytes differ')
        for name in BEACON_ASSETS: require(payloads['assets/runtime/'+name] == base.file_pin(beacon_directory/name), 'Qualified beacon bytes differ')
        client, runtime = verification_manifests(donor, {name: payloads['assets/runtime/'+name] for name in UPDATES}, commit, visual, beacons)
        require(json.loads(archive.read('assets/runtime/client-manifest.json')) == client and
            json.loads(archive.read('assets/runtime/runtime-manifest.json')) == runtime, 'Candidate provenance differs')
    require(previous.prior.verify_apk_server_archives(apk) == donor['server_payload_extraction_preflight'], 'Candidate actual server extraction differs')
    return runtime


def validate_qualification(receipt, commit):
    require(receipt.get('format') == 1 and receipt.get('status') == 'passed' and receipt.get('scope') == QUALIFICATION_SCOPE
        and receipt.get('repository_commit') == commit and receipt.get('donor') == donor_link()
        and set(receipt.get('checks', {})) == set(CHECKS) and all(value is True for value in receipt['checks'].values())
        and all(receipt.get(key) is False for key in ('physical_gameplay_validated', 'physical_client_timing_validated',
            'physical_visual_assets_validated', 'native_dbserver_recompiled', 'native_client_recompiled',
            'native_mapserver_recompiled', 'java_or_dex_recompiled', 'asset_reimport_required')),
        'Exact source-bound UI/beacon qualification required')
    contract = module('ui_beacon_qualification_contract', ROOT/QUALIFICATION_SCRIPT); suites = receipt.get('test_suites', {})
    require(set(suites) == set(contract.TEST_MODULES) and receipt.get('check_suites') == contract.CHECK_SUITES and
        all(item.get('status') == 'passed' and item.get('skipped') == 0 and type(item.get('tests_run')) is int and item['tests_run'] > 0
            for item in suites.values()) and receipt.get('tests_run') == sum(item['tests_run'] for item in suites.values()), 'Complete unskipped suite inventory required')
    require(SOURCE_FILES <= set(receipt.get('source_files', {})), 'Current source closure incomplete')
    for name, pin in receipt['source_files'].items():
        require(isinstance(name, str) and not Path(name).is_absolute() and '..' not in Path(name).parts and chr(92) not in name, 'Unsafe source path')
        builder().checked_file(ROOT/name, pin)
    require(receipt.get('postgresql_emission_fixtures') == ['cancelled_child_deletion_commits', 'delete_insert_replacement_commits', 'duplicate_insert_23505_rollback']
        and receipt.get('postgresql_levelup_fixtures') == sorted(previous.prior.levelup_postgresql_fixtures()), 'Retained real PostgreSQL fixtures required')
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


def extract_baseline(args):
    base = builder(); base.checked_file(args.donor_apk, DONOR_APK); donor = validate_donor_receipt(args.donor_build_report)
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh baseline required'); args.output.mkdir(parents=True)
    with zipfile.ZipFile(args.donor_apk) as archive:
        for name in VISUAL_ASSETS:
            with archive.open('assets/runtime/'+name) as source, (args.output/name).open('xb') as target: shutil.copyfileobj(source, target, 64*1024)
            base.checked_file(args.output/name, donor['payloads']['assets/runtime/'+name])


def build(args):
    base, current = builder(), builder(repaired=True); commit = base.source_commit(args.repository_commit)
    donor = validate_donor(args.donor_apk, args.donor_build_report); qualification = validate_qualification(read_json(args.qualification), commit)
    visual = validate_visual_package(args.visual_directory); conservation = validate_visual_superset(donor, visual)
    streams = verify_visual_streams(args.donor_apk, args.visual_directory, donor); beacons = validate_beacons(args.beacon_directory, commit, donor)
    require(qualification.get('visual_package') == visual and qualification.get('visual_superset') == conservation and
        qualification.get('visual_original_streams') == streams and qualification.get('atlas_beacons') == beacons, 'Inputs changed after qualification')
    java = current_sources(donor); password = base.signing_password_spec(args.password_env)
    base.verify_signing_identity(args.keystore, 'coh-client-interactive', SIGNER, password)
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), 'Fresh candidate APK required')
    base.checked_file(args.testing_notes); require(0 < args.testing_notes.stat().st_size <= 65536, 'Bounded notes required')
    for tool in (args.android_jar, args.build_tools/'aapt2', args.build_tools/'zipalign', args.build_tools/'lib/apksigner.jar'):
        require(tool.is_file() and not tool.is_symlink(), 'Required Android tool missing')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-ui-beacon-', dir=args.output.parent) as temporary:
        work = Path(temporary)
        runtime, payloads, preflight, _, _ = extract_and_repair(args.donor_apk, donor, work/'donor', commit, args.visual_directory, args.beacon_directory)
        manifest = work/'AndroidManifest.xml'; repair_android_manifest(ROOT/'android/interactive/src/main/AndroidManifest.xml', manifest)
        resources, unsigned, aligned, signed = (work/name for name in ('resources.zip', 'unsigned.apk', 'aligned.apk', 'signed.apk'))
        base.run(args.build_tools/'aapt2', 'compile', '--dir', ROOT/'android/interactive/src/main/res', '-o', resources)
        base.run(args.build_tools/'aapt2', 'link', '-I', args.android_jar, '--manifest', manifest, '--min-sdk-version', '26', '--target-sdk-version', '35', resources, '-o', unsigned)
        with zipfile.ZipFile(unsigned) as archive:
            require(previous.prior.archive_inventory(archive) == {'AndroidManifest.xml', 'resources.arsc', 'res/drawable/ic_coh_client.xml'}, 'Generated Android inventory differs')
            for name, pin in donor['retained_android_resources'].items():
                raw = archive.read(name); require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == pin, 'Android resources changed beyond version')
        with zipfile.ZipFile(unsigned, 'a', zipfile.ZIP_DEFLATED) as archive:
            base.append_payloads(archive, [(work/'donor'/name, name) for name in sorted(payloads)]); archive.write(work/'donor/classes.dex', 'classes.dex')
        base.run(args.build_tools/'zipalign', '-f', '4', unsigned, aligned)
        base.run('java', '-jar', args.build_tools/'lib/apksigner.jar', 'sign', '--ks', args.keystore, '--ks-key-alias', 'coh-client-interactive', '--ks-pass', password, '--key-pass', password, '--out', signed, aligned)
        certificate = previous.prior.verify_signature(signed, args.build_tools); base.run(args.build_tools/'zipalign', '-c', '4', signed)
        current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', signed))
        verify_derivative(signed, donor, payloads, commit, args.visual_directory, args.beacon_directory)
        previous.prior.verify_binary_manifest(signed, args.donor_apk, args.build_tools); shutil.copyfile(signed, args.output)
        report = {'format': 1, 'apk': APK_NAME, **base.file_pin(args.output), 'repository_commit': commit,
            'runtime_repository_commit': commit, 'application_id': base.APP_ID, 'version_name': VERSION_NAME, 'version_code': VERSION_CODE,
            'abi': 'arm64-v8a', 'scope': QUALIFICATION_SCOPE, 'donor': donor_link(), 'signer_certificate_sha256': certificate,
            'signing_key_created': False, 'signature_verified': True, 'package_badging_verified': True,
            'binary_manifest_version_only_verified': True, 'payload_bytes_verified': True, 'payloads': payloads,
            'changed_apk_payloads': sorted(REPLACED_PAYLOADS|ADDED_PAYLOADS), 'replaced_apk_payloads': sorted(REPLACED_PAYLOADS),
            'added_apk_payloads': sorted(ADDED_PAYLOADS), 'retained_baseline_payloads_verified': 72, 'java_sources': java,
            'changed_java_sources': [], 'retained_dex': donor['retained_dex'], 'preserved_sources': donor['preserved_sources'],
            'source_manifest': donor['source_manifest'], 'qualification': qualification, 'qualification_receipt': base.file_pin(args.qualification),
            'testing_notes': base.file_pin(args.testing_notes), 'visual_package': visual, 'visual_superset': conservation,
            'visual_original_streams': streams, 'atlas_beacons': beacons,
            **{key: False for key in ('native_dbserver_recompiled', 'native_client_recompiled', 'native_mapserver_recompiled',
                'java_or_dex_recompiled', 'physical_gameplay_validated', 'physical_client_timing_validated',
                'physical_visual_assets_validated', 'asset_reimport_required', 'world_assets_changed', 'prepared_cache_archive_changed')},
            'runtime_refresh_required': True, 'previous_runtime_generation_retained': True, 'setup_memory_guards_preserved': True,
            'all_published_visual_resources_retained': True, 'server_payload_extraction_preflight': preflight,
            'runtime_manifest': runtime, 'runtime_manifest_sha256': payloads['assets/runtime/runtime-manifest.json']['sha256'],
            **{name: donor[name] for name in RETAINED_REPORT_FIELDS}}
        (args.output.parent/REPORT_NAME).write_text(json.dumps(report, indent=2)+'\n')
    shutil.copyfile(args.testing_notes, args.output.parent/NOTES_NAME); args.output.with_suffix('.apk.sha256').write_text(report['sha256']+'  '+APK_NAME+'\n')
    verify_report(argparse.Namespace(**vars(args), apk=args.output, build_report=args.output.parent/REPORT_NAME), commit)
    print('Qualified UI/beacon APK:', args.output, report['sha256']); return report


def verify_report(args, commit):
    donor = validate_donor(args.donor_apk, args.donor_build_report); base, current = builder(), builder(repaired=True)
    q = validate_qualification(read_json(args.qualification), commit); report = read_json(args.build_report)
    visual = validate_visual_package(args.visual_directory); conservation = validate_visual_superset(donor, visual)
    streams = verify_visual_streams(args.donor_apk, args.visual_directory, donor); beacons = validate_beacons(args.beacon_directory, commit, donor)
    require(report.get('format') == 1 and report.get('apk') == APK_NAME and report.get('repository_commit') == commit
        and report.get('runtime_repository_commit') == commit and report.get('donor') == donor_link() and report.get('scope') == QUALIFICATION_SCOPE
        and report.get('application_id') == base.APP_ID and report.get('version_name') == VERSION_NAME and report.get('version_code') == VERSION_CODE
        and report.get('signer_certificate_sha256') == SIGNER and report.get('signing_key_created') is False
        and report.get('qualification') == q and report.get('qualification_receipt') == base.file_pin(args.qualification)
        and report.get('java_sources') == current_sources(donor) and report.get('changed_java_sources') == []
        and report.get('retained_dex') == donor['retained_dex'] and report.get('preserved_sources') == donor['preserved_sources']
        and report.get('source_manifest') == donor['source_manifest'] and report.get('visual_package') == visual
        and report.get('visual_superset') == conservation and report.get('visual_original_streams') == streams
        and report.get('atlas_beacons') == beacons and report.get('changed_apk_payloads') == sorted(REPLACED_PAYLOADS|ADDED_PAYLOADS)
        and report.get('replaced_apk_payloads') == sorted(REPLACED_PAYLOADS) and report.get('added_apk_payloads') == sorted(ADDED_PAYLOADS)
        and report.get('retained_baseline_payloads_verified') == 72 and all(report.get(name) == donor[name] for name in RETAINED_REPORT_FIELDS)
        and all(report.get(key) is True for key in ('signature_verified', 'package_badging_verified', 'binary_manifest_version_only_verified',
            'payload_bytes_verified', 'runtime_refresh_required', 'previous_runtime_generation_retained', 'setup_memory_guards_preserved', 'all_published_visual_resources_retained'))
        and all(report.get(key) is False for key in ('native_dbserver_recompiled', 'native_client_recompiled', 'native_mapserver_recompiled',
            'java_or_dex_recompiled', 'physical_gameplay_validated', 'physical_client_timing_validated', 'physical_visual_assets_validated',
            'asset_reimport_required', 'world_assets_changed', 'prepared_cache_archive_changed')), 'Candidate build receipt differs')
    base.checked_file(args.apk, report); runtime = verify_derivative(args.apk, donor, report['payloads'], commit, args.visual_directory, args.beacon_directory)
    require(report.get('runtime_manifest') == runtime and report.get('runtime_manifest_sha256') == report['payloads']['assets/runtime/runtime-manifest.json']['sha256'], 'Runtime provenance differs')
    previous.prior.verify_binary_manifest(args.apk, args.donor_apk, args.build_tools); previous.prior.verify_signature(args.apk, args.build_tools)
    base.run(args.build_tools/'zipalign', '-c', '4', args.apk); current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', args.apk))
    checksum = args.apk.with_suffix('.apk.sha256'); require(checksum.read_text() == report['sha256']+'  '+APK_NAME+'\n', 'Checksum differs')
    notes = args.apk.parent/NOTES_NAME; base.checked_file(notes, report['testing_notes']); base.checked_file(args.testing_notes, report['testing_notes'])
    return report, checksum, notes


def publish_release(api, report, assets, notes):
    require(tuple(path.name for path in assets) == (APK_NAME, APK_NAME+'.sha256', NOTES_NAME), 'Unexpected release assets'); builder().checked_file(assets[0], report)
    for path in ('/releases/tags/'+RELEASE_TAG, '/git/ref/tags/'+RELEASE_TAG):
        try: existing = api.request(path)
        except urllib.error.HTTPError as error:
            if error.code != 404: raise
        else:
            require(not path.startswith('/releases/'), 'Existing release is never replaced')
            require(existing.get('object', {}).get('type') == 'commit' and existing['object'].get('sha') == report['repository_commit'], 'Existing tag points elsewhere')
    body = notes+'\n\nAPK SHA-256: `'+report['sha256']+'`.\n[Source-bound UI/beacon qualification](https://github.com/'+REPOSITORY+'/actions/runs/'+os.environ.get('GITHUB_RUN_ID', '')+').\n'
    release = api.request('/releases', {'tag_name': RELEASE_TAG, 'target_commitish': report['repository_commit'],
        'name': 'COH Atlas Gameplay 0.13.14 — UI sweep and Atlas beacons', 'body': body, 'draft': True, 'prerelease': True,
        'generate_release_notes': False, 'make_latest': 'false'}, method='POST')
    require(type(release.get('id')) is int and release.get('draft') is True and release.get('tag_name') == RELEASE_TAG, 'Unexpected release')
    for path in assets:
        uploaded = api.request('/releases/'+str(release['id'])+'/assets?'+urllib.parse.urlencode({'name': path.name}), path, method='POST', upload=True); pin = builder().file_pin(path)
        require(uploaded.get('state') == 'uploaded' and uploaded.get('name') == path.name and uploaded.get('size') == pin['bytes'] and uploaded.get('digest') == 'sha256:'+pin['sha256'], 'Release upload differs')
    published = api.request('/releases/'+str(release['id']), {'draft': False, 'prerelease': True, 'make_latest': 'false'}, method='PATCH')
    require(published.get('id') == release['id'] and published.get('draft') is False and published.get('prerelease') is True and published.get('tag_name') == RELEASE_TAG, 'Publication incomplete')
    return published.get('html_url')


def publish(args):
    require(os.environ.get('GITHUB_REPOSITORY') == REPOSITORY and os.environ.get('GITHUB_REF') == 'refs/heads/'+BRANCH and
        os.environ.get('GITHUB_EVENT_NAME') in ('push', 'workflow_dispatch'), 'Publication requires continuation branch')
    commit = builder().source_commit(os.environ.get('GITHUB_SHA')); report, checksum, notes = verify_report(args, commit)
    api = module('ui_beacon_github', Path(__file__).with_name('build_atlas_gameplay_apk.py'))
    print('Published UI/beacon prerelease:', publish_release(api.GitHub(os.environ.get('GH_TOKEN')), report, (args.apk, checksum, notes), notes.read_text()))


def main():
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('download-donor'); p.add_argument('--output', type=Path, required=True)
    p = commands.add_parser('extract-baseline')
    for name in ('donor-apk', 'donor-build-report', 'output'): p.add_argument('--'+name, type=Path, required=True)
    for command in ('build', 'publish', 'audit'):
        p = commands.add_parser(command)
        for name in ('donor-apk', 'donor-build-report', 'visual-directory', 'qualification', 'build-tools'): p.add_argument('--'+name, type=Path, required=True)
        p.add_argument('--beacon-directory', type=Path); p.add_argument('--testing-notes', type=Path, default=NOTES)
        if command == 'build':
            for name in ('android-jar', 'keystore', 'output'): p.add_argument('--'+name, type=Path, required=True)
            p.add_argument('--password-env', default='COH_INTERACTIVE_KEYSTORE_PASSWORD')
        else:
            for name in ('apk', 'build-report'): p.add_argument('--'+name, type=Path, required=True)
        if command != 'publish': p.add_argument('--repository-commit', required=True)
    args = parser.parse_args()
    if args.command == 'download-donor': download(args)
    elif args.command == 'extract-baseline': extract_baseline(args)
    elif args.command == 'build': build(args)
    elif args.command == 'publish': publish(args)
    else:
        report, _, _ = verify_report(args, builder().source_commit(args.repository_commit)); print('Candidate verified:', report['sha256'])


if __name__ == '__main__': main()
