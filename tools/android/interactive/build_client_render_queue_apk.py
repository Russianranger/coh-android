#!/usr/bin/env python3
"""Publish a Game-only continuation over the authenticated public .24 APK.

Retain the actual .24 Android DEX/resources, all nineteen Java sources, successful
GPU driver and both probes, servers, assets, saving and Software fallback. Bind
the new queue Game to its own Windows producer and the immutable .22 parent.
"""
from __future__ import annotations
import argparse
import copy
import functools
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

import build_setup_copy_repair_apk as previous
import build_client_render_pipeline_apk as parent_history

ROOT, require, module, shared = previous.ROOT, previous.require, previous.module, previous.shared
REPOSITORY, BRANCH, SIGNER = previous.REPOSITORY, previous.BRANCH, previous.SIGNER
retained, engine = previous.retained, previous.engine
DONOR_COMMIT, DONOR_RUN_ID = '3d73e9b4c71fe3f87de6bf0bb41fc0ce50f3f6ce', 37973264500
DONOR_APK_NAME, DONOR_REPORT_NAME = 'COH-Atlas-Gameplay-0.13.24.apk', 'setup-copy-repair-apk-build-report.json'
DONOR_APK = {'bytes': 1560316680, 'sha256': '7ae9e8b21e48c30e1d6b9373e676ec7b6eb4727db7fa7b313281fb30a8ab38b0'}
DONOR_BUILD = {'bytes': 5439187, 'sha256': '8cee18527c30767fc6d49f0e423028a16ed342a4cd5a9d9d9ac4137c457991b5'}
DONOR_EVIDENCE_ID = 11638093807
DONOR_EVIDENCE = {'bytes': 1273548, 'sha256': '97fbb865b6e252ca69e5b2bbf5d12fcc9488741482cd3b6ff16d35e2d744ad41'}
DONOR_EVIDENCE_ARCHIVE = 'published-0.13.24-packaging-evidence.zip'
DONOR_EVIDENCE_NAMES = frozenset({DONOR_REPORT_NAME, 'COH-Atlas-Gameplay-0.13.24-testing.txt', DONOR_APK_NAME+'.sha256'})
DONOR_GAME = {'bytes': 9494016, 'sha256': '1953fa3ed1bee3dcdecaed14ccd369730a13bc4addf06ddfc283f7f6f9211b72'}
# Original .22 parent remains separately identified and immutable.
PARENT_NATIVE_COMMIT = parent_history.NATIVE_BUILD_COMMIT
PARENT_NATIVE_RUN_ID = parent_history.NATIVE_BUILD_RUN_ID
PARENT_NATIVE_SOURCE_FILES = parent_history.RETAINED_NATIVE_SOURCE_FILES
DONOR_RUNTIME_COMMIT = previous.DONOR_COMMIT
DONOR_URL = 'https://github.com/'+REPOSITORY+'/releases/download/coh-atlas-gameplay-v0.13.24/'+DONOR_APK_NAME
VERSION_NAME, VERSION_CODE = '0.13.25', 40
APK_NAME, REPORT_NAME = 'COH-Atlas-Gameplay-0.13.25.apk', 'client-render-queue-apk-build-report.json'
NOTES_NAME = 'COH-Atlas-Gameplay-0.13.25-testing.txt'
RELEASE_TAG = 'coh-atlas-gameplay-v0.13.25'
NOTES = ROOT/'docs'/NOTES_NAME
WORKFLOW = '.github/workflows/android-client-render-queue.yml'
QUALIFICATION_SCRIPT = 'tools/android/interactive/qualify_client_render_queue.py'
QUALIFICATION_SCOPE = 'native_render_queue_wake_coalescing_and_sparse_scene_full_ring_attribution_retaining_public_0_13_24'
HELPERS = frozenset({'native_responsiveness_contract.py', 'client_startup_diagnostic.py', 'client_gpu_profile.py', 'texture_header_index.py'})
REPLACED_PAYLOADS = frozenset('assets/runtime/'+name for name in HELPERS|{'client-runtime.zip','client-manifest.json','runtime-manifest.json'})
ACTUAL_NATIVE_ANCESTRY_CHECKS = dict(parent_history.ACTUAL_NATIVE_ANCESTRY_CHECKS)
ACTUAL_NATIVE_ANCESTRY_CHECKS.pop('actual_renderer_Game_predecessor_verified')
ACTUAL_NATIVE_ANCESTRY_CHECKS['actual_pipeline_Game_predecessor_verified'] = True
CHECKS = ('native_queue_wake_coalescing_sparse_attribution_and_owned_controls_verified',
    'retained_gameplay_postgresql_gpu_cleanup_and_recovery_guards_verified',
    'exact_Game_only_payload_024_Android_shell_and_successful_GPU_bytes_verified')
SOURCE_FILES = frozenset({WORKFLOW, QUALIFICATION_SCRIPT,
    'tools/android/interactive/build_client_render_queue_apk.py',
    'tools/android/interactive/test_client_render_queue_package.py',
    'tools/android/interactive/test_client_render_pipeline_package.py',
    'tools/android/interactive/test_client_session_repair_package.py',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'tools/android/interactive/analyze_client_render_queue.py',
    'tools/android/interactive/test_analyze_client_render_queue.py',
    'tools/android/interactive/test_client_render_queue_contract.py',
    'tools/android/interactive/test_client_render_queue_guest.py',
    'docs/android-evidence/render-queue-0.13.24-thor-20261009.json',
    'docs/COH-PERFORMANCE-0.13.25.md', 'docs/'+NOTES_NAME,
    *('android/guest/'+name for name in HELPERS)})
REVIEWED_DONOR_SOURCE_CHANGES = SOURCE_FILES | frozenset({'docs/HANDOFF.md', 'docs/COH-SETUP-COPY-0.13.24.md'})
FALSE_FLAGS = ('native_dbserver_recompiled', 'native_mapserver_recompiled', 'java_or_dex_recompiled',
    'graphics_driver_changed', 'mesa_driver_compiled_in_current_run', 'native_vulkan_probe_compiled_in_current_run',
    'wgl_probe_compiled_in_current_run', 'physical_performance_validated', 'physical_fps_gain_validated',
    'asset_reimport_required', 'world_assets_changed', 'prepared_cache_archive_changed',
    'wine_or_fex_changed', 'save_acceptance_relaxed', 'zoning_implemented', 'native_runtime_booted')
TRUE_FLAGS = ('native_client_recompiled', 'native_client_package_reused', 'raw_native_producer_preserved',
    'retained_android_dex_and_resources_verified', 'successful_gpu_driver_and_both_probes_retained',
    'software_fallback_preserved', 'graphical_fidelity_preserved_by_payload_and_recipe',
    'runtime_refresh_required', 'previous_runtime_generation_retained')
RETAINED_FIELDS = previous.history.RETAINED_FIELDS + ('client_session_repair','native_client_render_pipeline')
read_json, read_json_value = previous.read_json, previous.read_json_value


@functools.lru_cache(maxsize=1)
def native_producer():
    return module('client_render_queue_native_producer', ROOT/'tools/android/interactive/package_client_render_queue_native.py')


def builder(*, repaired=False):
    base = previous.builder()
    if repaired: base.VERSION_NAME, base.VERSION_CODE, base.APK_NAME = VERSION_NAME, VERSION_CODE, APK_NAME
    return base


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def donor_link():
    return {'run_id': DONOR_RUN_ID, 'repository_commit': DONOR_COMMIT, 'apk': DONOR_APK,
        'build_report_artifact_id': DONOR_EVIDENCE_ID, 'build_report_artifact_zip': DONOR_EVIDENCE}


def donor_evidence_members(path):
    """Authenticate the producer ZIP before trusting any contained file pin."""
    builder().checked_file(path, DONOR_EVIDENCE)
    with zipfile.ZipFile(path) as archive:
        require(retained.archive_inventory(archive) == DONOR_EVIDENCE_NAMES,
            'Exact published .24 packaging evidence inventory required')
        result = {}
        for entry in archive.infolist():
            require(entry.filename in DONOR_EVIDENCE_NAMES and not entry.is_dir() and 0 < entry.file_size <= 256*1024**2,
                'Unsafe or unbounded donor evidence member')
            result[entry.filename] = pin(archive.read(entry))
    return result


def validate_donor_receipt(path):
    expected = donor_evidence_members(path.parent/DONOR_EVIDENCE_ARCHIVE)[DONOR_REPORT_NAME]
    require(expected == DONOR_BUILD, 'Authenticated raw .24 producer pin differs')
    builder().checked_file(path, expected); donor = read_json(path); q = donor.get('qualification', {})
    require(donor.get('format') == 1 and donor.get('repository_commit') == DONOR_COMMIT
        and donor.get('runtime_repository_commit') == DONOR_RUNTIME_COMMIT and donor.get('apk') == DONOR_APK_NAME
        and {key:donor.get(key) for key in DONOR_APK} == DONOR_APK
        and donor.get('application_id') == builder().APP_ID and donor.get('version_name') == '0.13.24'
        and donor.get('version_code') == 39 and donor.get('abi') == 'arm64-v8a'
        and donor.get('signer_certificate_sha256') == SIGNER and donor.get('signing_key_created') is False
        and all(donor.get(key) is True for key in ('signature_verified', 'package_badging_verified',
            'binary_manifest_version_only_verified', 'payload_bytes_verified', 'setup_memory_guards_preserved'))
        and len(donor.get('payloads', {})) == 77 and len(donor.get('java_sources', {})) == 19
        and q.get('status') == 'passed' and q.get('scope') == previous.QUALIFICATION_SCOPE
        and q.get('repository_commit') == DONOR_COMMIT and q.get('tests_run') == 1605
        and len(q.get('test_suites', {})) == 110
        and all(value.get('status') == 'passed' and value.get('skipped') == 0 for value in q['test_suites'].values())
        and donor.get('java_or_dex_recompiled') is True and donor.get('native_client_recompiled') is False
        and donor.get('native_build_provenance') == parent_history.native_build_provenance()
        and donor.get('native_client_render_pipeline') == q.get('retained_native_render_pipeline'),
        'Exact independently authenticated public .24 donor receipt required')
    return donor

def current_sources(donor):
    base = builder(); sources = retained.retained.java_sources(base, ROOT/'out/no-generated-java')
    pins = {p.relative_to(ROOT).as_posix(): base.file_pin(p) for p in sources if p.is_relative_to(ROOT)}
    require(pins == donor['java_sources'] and len(pins) == 19, 'All nineteen authored .24 Java sources must remain exact')
    for name, expected in donor['preserved_sources'].items():
        # Historical preserved_sources remain a frozen older producer history.
        # The actual current .24 Java bytes are independently pinned above.
        if name not in donor['java_sources']: base.checked_file(ROOT/name, expected)
    base.checked_file(ROOT/'android/interactive/src/main/AndroidManifest.xml', donor['source_manifest'])
    for name, expected in donor['payloads'].items():
        if name.startswith('assets/runtime/') and name.endswith('.py') and Path(name).name not in HELPERS:
            base.checked_file(ROOT/'android/guest'/Path(name).name, expected)
    require(all(base.file_pin(ROOT/'android/guest'/name) != donor['payloads']['assets/runtime/'+name] for name in HELPERS),
        'Exactly the reviewed native producer integration helpers must change')
    for name, expected in donor['qualification']['source_files'].items():
        require(type(name) is str and not Path(name).is_absolute() and '..' not in Path(name).parts and chr(92) not in name,
            'Unsafe donor source path')
        if name not in REVIEWED_DONOR_SOURCE_CHANGES: base.checked_file(ROOT/name, expected)
    return pins


def validate_donor(apk, receipt):
    base = builder(); base.checked_file(apk, DONOR_APK); donor = validate_donor_receipt(receipt)
    base.verify_packaged_payloads(apk, donor['payloads'])
    with zipfile.ZipFile(apk) as archive:
        shell = {'classes.dex': donor['recompiled_dex'], **donor['retained_android_resources']}
        require(retained.archive_inventory(archive) == set(donor['payloads'])|set(shell)|{'AndroidManifest.xml'}, 'Exact .24 donor inventory required')
        for name, expected in shell.items(): require(pin(archive.read(name)) == expected, 'Donor Android shell differs: '+name)
        require(read_json_value(archive.read('assets/runtime/runtime-manifest.json')) == donor['runtime_manifest'], 'Donor runtime provenance differs')
        donor['_client_verification'] = read_json_value(archive.read('assets/runtime/client-manifest.json'))
        for name in HELPERS:
            require(pin(archive.read('assets/runtime/'+name)) == PARENT_NATIVE_SOURCE_FILES['android/guest/'+name],
                'Actual retained .22/.24 native integration helper ancestry differs')
        with archive.open('assets/runtime/client-runtime.zip') as source, tempfile.TemporaryFile() as target:
            shutil.copyfileobj(source, target, 1024*1024); target.seek(0)
            with zipfile.ZipFile(target) as client:
                package = read_json_value(client.read('client-package.json'))
                shared.native_contract.client_contract(package, donor['immutable_donor_provenance']['native_responsiveness'])
                members = engine.startup.startup.client_member_pins(client)
                require(members.get('CityOfHeroes.exe') == DONOR_GAME and len(members) == 22
                    and package.get('client_renderer_attribution', {}).get('manifest') == donor['native_client_renderer_attribution'],
                    'Donor Game, DLL closure or actual .19 renderer ancestry differs')
                donor['_native_client_manifest'], donor['_client_members'] = package, members
                require(package['client_render_pipeline']['manifest'] == donor['native_client_render_pipeline'],
                    'Actual unchanged original pipeline producer differs')
    for name, expected in PARENT_NATIVE_SOURCE_FILES.items():
        if name not in {'android/guest/'+helper for helper in HELPERS}: base.checked_file(ROOT/name, expected)
    parent = parent_history.native_producer()
    require(parent.typed_equal(donor['native_client_render_pipeline']['build_input'], parent.expected_receipt()),
        'Original .22 source recipe does not independently reproduce')
    parent.validate_checks(donor['native_client_render_pipeline']['windows_qualification'])
    require(retained.verify_apk_server_archives(apk) == donor['server_payload_extraction_preflight'], 'Donor server extraction differs')
    current_sources(donor); return donor


def native_build_provenance(native, directory, commit):
    match = re.fullmatch(r'https://github\.com/Russianranger/coh-android/actions/runs/([1-9][0-9]+)', native['run_url'])
    require(match and re.fullmatch('[0-9a-f]{40}', native['repository_commit']), 'Actual native producer identity required')
    game = native['files']['CityOfHeroes.exe']
    return {'format': 1, 'repository_commit': native['repository_commit'], 'run_id': int(match[1]),
        'run_url': native['run_url'], 'native_manifest': builder().file_pin(Path(directory)/native_producer().MANIFEST),
        'game': {'bytes': game['size'], 'sha256': game['sha256']},
        'source_files': {name:builder().file_pin(ROOT/name) for name in native_producer().SOURCE_FILES},
        'source_recipe_independently_recomputed': True, 'raw_producer_preserved': True,
        'compiled_in_current_publication_run': native['repository_commit'] == commit and
            native['run_url'] == publication_provenance(commit)['run_url'],
        'game_changed_from_public_0_13_24': True,
        'parent_native_build_provenance': parent_history.native_build_provenance()}

def publication_provenance(commit):
    owner = os.environ.get('GITHUB_RUN_ID')
    require(owner is None or re.fullmatch('[1-9][0-9]*', owner), 'Exact current publication owner required')
    return {'format': 1, 'repository_commit': commit,
        'run_url': 'https://github.com/'+REPOSITORY+'/actions/runs/'+owner if owner else None,
        'donor_apk_repository_commit': DONOR_COMMIT, 'donor_runtime_repository_commit': DONOR_RUNTIME_COMMIT,
        'parent_native_build_repository_commit': PARENT_NATIVE_COMMIT,
        'parent_native_build_run_id': PARENT_NATIVE_RUN_ID, 'parent_native_producer_relabelled': False}

def validate_native(directory, commit, donor, native_source_commit=None):
    builder().source_commit(commit)
    native_source_commit = native_source_commit or commit
    require(re.fullmatch('[0-9a-f]{40}', native_source_commit), 'Exact current native source required')
    native = native_producer().validate_package(directory, native_source_commit)
    parent = donor['native_client_render_pipeline']
    require(native['base_client_executable'] == donor['_native_client_manifest']['files']['CityOfHeroes.exe']
        and native['build_input']['base_client_render_pipeline_build_input'] == parent['build_input'],
        'New queue Game must extend the exact published .24/.22 pipeline Game')
    require(native['schema_sources_sha256'] == parent['schema_sources_sha256']
        and native['retained_source_inputs'] == parent['retained_source_inputs'], 'Prepared schema or source ancestry changed')
    require(native['files']['CityOfHeroes.exe']['sha256'] != DONOR_GAME['sha256'], 'New native Game was not compiled')
    return native

def client_manifest(donor, native):
    result = copy.deepcopy(donor['_native_client_manifest'])
    result['files']['CityOfHeroes.exe'] = native['files']['CityOfHeroes.exe']
    result['dependency_report'] = shared.dependency_report(result['files'])
    require(not result['dependency_report']['unresolved'], 'New Game imports exceed retained DLL closure')
    result['client_render_queue'] = {'manifest': native,
        'manifest_sha256': shared.native_contract.canonical_sha(native),
        'base_client_render_pipeline_manifest_sha256': result['client_render_pipeline']['manifest_sha256'],
        'base_client_executable': copy.deepcopy(donor['_native_client_manifest']['files']['CityOfHeroes.exe'])}
    shared.native_contract.client_contract(result, donor['immutable_donor_provenance']['native_responsiveness'])
    return result

def validate_client_package_bytes(raw, donor, native):
    """Qualify the actual nested JSON with typed ancestry and exact encoding.

    Python object equality collapses bool/int/float distinctions. Validate the
    received wrapper itself before requiring the canonical bytes the builder
    writes, rather than qualifying only an independently generated expectation.
    """
    package = read_json_value(raw)
    record = shared.native_contract.client_contract(
        package, donor['immutable_donor_provenance']['native_responsiveness'])
    expected = client_manifest(donor, native)
    require(raw == shared.encoded(expected)
        and record == native['files']['CityOfHeroes.exe'],
        'Actual native client wrapper bytes or typed producer differ')
    return package


def replace_client_archive(path, donor, native, directory):
    require(builder().file_pin(path) == donor['payloads']['assets/runtime/client-runtime.zip'], 'Exact donor client archive required')
    output = path.with_suffix('.candidate.zip'); require(not output.exists(), 'Fresh client ZIP staging required')
    expected = client_manifest(donor, native)
    with zipfile.ZipFile(path) as original, zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        require(engine.startup.startup.client_member_pins(original) == donor['_client_members'], 'Donor client members differ')
        for entry in original.infolist():
            if entry.filename == 'CityOfHeroes.exe': raw = (Path(directory)/entry.filename).read_bytes()
            elif entry.filename == 'client-package.json': raw = shared.encoded(expected)
            else: raw = original.read(entry)
            archive.writestr(entry, raw)
    with zipfile.ZipFile(output) as archive:
        received = engine.startup.startup.client_member_pins(archive)
        require(set(received) == set(donor['_client_members']) and all(received[n] == donor['_client_members'][n]
            for n in received if n not in {'CityOfHeroes.exe', 'client-package.json'}), 'Retained twenty client DLL bytes changed')
        validate_client_package_bytes(archive.read('client-package.json'), donor, native)
    output.replace(path)


def verification_manifests(donor, updates, commit, native, provenance=None):
    require(set(updates) == HELPERS|{'client-runtime.zip'}, 'Only exact native integration inputs required')
    client = copy.deepcopy(donor['_client_verification']); client['files'].update(updates)
    runtime = copy.deepcopy(donor['runtime_manifest']); runtime['files'].update(updates)
    runtime['files']['client-manifest.json'] = pin(shared.encoded(client))
    runtime.update(repository_commit=commit, scope=QUALIFICATION_SCOPE)
    runtime['client_render_queue'] = {'format': 1, 'repository_commit': commit,
        'donor_apk_repository_commit': DONOR_COMMIT, 'donor_runtime_repository_commit': DONOR_RUNTIME_COMMIT,
        'native_recompiled': True, 'native_build_repository_commit': native['repository_commit'],
        'native_build_run_url': native['run_url'], 'parent_native_build_provenance': donor['native_build_provenance'],
        'native_compiled_in_current_publication_run': native['repository_commit'] == commit and
            native['run_url'] == publication_provenance(commit)['run_url'],
        'publication_provenance': publication_provenance(commit),
        'native_manifest_sha256': shared.native_contract.canonical_sha(native),
        'replacement_scope': 'CityOfHeroes.exe_only', 'changed_guest_helpers': sorted(HELPERS),
        'successful_gpu_driver_and_both_probes_retained': True, 'android_dex_and_resources_retained': True,
        'graphical_fidelity_preserved': True, 'physical_performance_validated': False}
    require(set(client['files']) == set(donor['_client_verification']['files'])
        and set(runtime['files']) == set(donor['runtime_manifest']['files']), 'Runtime inventory must remain exact')
    return client, runtime

def payload_boundaries(payloads, donor):
    require(len(payloads) == 77 and set(payloads) == set(donor['payloads'])
        and {n for n in payloads if payloads[n] != donor['payloads'][n]} == REPLACED_PAYLOADS,
        'Exactly seven reviewed integration payloads and seventy retained .24 payloads required')


def extract_and_repair(apk, donor, destination, commit, directory, native):
    destination.mkdir(parents=True); base = builder()
    with zipfile.ZipFile(apk) as archive:
        for entry in archive.infolist():
            if entry.filename == 'AndroidManifest.xml' or entry.filename.startswith('META-INF/'): continue
            target = destination/entry.filename; target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open('xb') as output: shutil.copyfileobj(source, output, 1024*1024)
    require(all(base.file_pin(destination/n) == v for n, v in donor['payloads'].items()), 'Extracted .24 donor payload bytes differ')
    assets = destination/'assets/runtime'
    for name in HELPERS: shutil.copyfile(ROOT/'android/guest'/name, assets/name)
    replace_client_archive(assets/'client-runtime.zip', donor, native, directory)
    updates = {n: base.file_pin(assets/n) for n in sorted(HELPERS|{'client-runtime.zip'})}
    client, runtime = verification_manifests(donor, updates, commit, native)
    for name, value in (('client-manifest.json', client), ('runtime-manifest.json', runtime)): (assets/name).write_bytes(shared.encoded(value))
    payloads = {n: base.file_pin(destination/n) for n in sorted(donor['payloads'])}; payload_boundaries(payloads, donor)
    require(retained.verify_server_archives(assets) == donor['server_payload_extraction_preflight'], 'Retained server extraction differs')
    return runtime, payloads


def verify_derivative(apk, donor, payloads, commit, native):
    base = builder(); payload_boundaries(payloads, donor); base.verify_packaged_payloads(apk, payloads)
    with zipfile.ZipFile(apk) as archive:
        shell = {'classes.dex': donor['recompiled_dex'], **donor['retained_android_resources']}
        require(retained.archive_inventory(archive) == set(payloads)|set(shell)|{'AndroidManifest.xml'}, 'Candidate inventory differs')
        for n, expected in shell.items(): require(pin(archive.read(n)) == expected, 'Exact .24 DEX/resources changed: '+n)
        for name in HELPERS: require(payloads['assets/runtime/'+name] == base.file_pin(ROOT/'android/guest'/name), 'Current helper bytes differ')
        client, runtime = verification_manifests(donor, {n: payloads['assets/runtime/'+n] for n in HELPERS|{'client-runtime.zip'}}, commit, native)
        require(archive.read('assets/runtime/client-manifest.json') == shared.encoded(client)
            and archive.read('assets/runtime/runtime-manifest.json') == shared.encoded(runtime), 'Actual manifest/provenance bytes differ')
        with archive.open('assets/runtime/client-runtime.zip') as source, tempfile.TemporaryFile() as target:
            shutil.copyfileobj(source, target, 1024*1024); target.seek(0)
            with zipfile.ZipFile(target) as client_zip:
                validate_client_package_bytes(client_zip.read('client-package.json'), donor, native)
                members = engine.startup.startup.client_member_pins(client_zip)
                require(members['CityOfHeroes.exe'] ==
                    {'bytes': native['files']['CityOfHeroes.exe']['size'], 'sha256': native['files']['CityOfHeroes.exe']['sha256']}
                    and set(members) == set(donor['_client_members']) and all(members[n] == donor['_client_members'][n]
                        for n in members if n not in {'CityOfHeroes.exe', 'client-package.json'}), 'Actual Game/typed wrapper/retained DLL bytes differ')
    require(retained.verify_apk_server_archives(apk) == donor['server_payload_extraction_preflight'], 'Actual candidate server extraction differs')
    return runtime


def validate_qualification(q, commit, donor):
    contract = module('client_render_queue_qualification', ROOT/QUALIFICATION_SCRIPT); contract.validate_suite_inventory()
    require(type(q.get('format')) is int and q['format'] == 1 and q.get('status') == 'passed' and q.get('scope') == QUALIFICATION_SCOPE
        and q.get('repository_commit') == commit and q.get('runtime_repository_commit') == commit
        and q.get('donor') == donor_link() and native_producer().typed_equal(q.get('checks'), dict.fromkeys(CHECKS, True))
        and native_producer().typed_equal(q.get('actual_native_ancestry_validation'), ACTUAL_NATIVE_ANCESTRY_CHECKS)
        and q.get('native_build_provenance', {}).get('repository_commit') == q.get('native_client_render_queue', {}).get('repository_commit')
        and q.get('publication_provenance') == publication_provenance(commit)
        and q.get('retained_native_repository_commit') == PARENT_NATIVE_COMMIT
        and q.get('native_build_repository_commit') == q.get('native_client_render_queue', {}).get('repository_commit')
        and q.get('changed_java_sources') == [] and q.get('retained_java_sources_verified') == 19
        and q.get('baseline_payloads_verified') == 77
        and q.get('actual_external_donor_and_full_guest_wrapper_verified') is True
        and all(q.get(k) is False for k in FALSE_FLAGS) and all(q.get(k) is True for k in TRUE_FLAGS), 'Truthful exact .25 qualification required')
    native = q['native_client_render_queue']; provenance = q['native_build_provenance']
    # Qualify the received producer itself, including exact JSON types and all
    # eight immutable parent layers, before dictionary comparisons can collapse
    # bool/int/float distinctions. The actual donor was authenticated by caller.
    client_manifest(donor,native)
    expected_compile = native['repository_commit'] == commit and native['run_url'] == publication_provenance(commit)['run_url']
    require(native.get('role') == native_producer().ROLE and native_producer().typed_equal(native.get('build_input'), native_producer().expected_receipt())
        and provenance.get('run_url') == native['run_url'] and provenance.get('compiled_in_current_publication_run') is expected_compile
        and q.get('native_client_compiled_in_current_publication_run') is expected_compile
        and q.get('native_client_compiled_in_current_run') is expected_compile
        and provenance.get('parent_native_build_provenance') == parent_history.native_build_provenance(),
        'Current queue producer and immutable parent identities differ')
    native_producer().validate_checks(native['windows_qualification'])
    require(provenance.get('source_files') == {name:builder().file_pin(ROOT/name) for name in native_producer().SOURCE_FILES},
        'Current native recipe source closure differs')
    suites = q.get('test_suites', {})
    require(set(suites) == set(contract.TEST_MODULES) and q.get('check_suites') == contract.CHECK_SUITES
        and all(v.get('status') == 'passed' and v.get('skipped') == 0 and type(v.get('tests_run')) is int and v['tests_run'] > 0 for v in suites.values())
        and type(q.get('tests_run')) is int and q['tests_run'] == sum(v['tests_run'] for v in suites.values()), 'Every retained/new suite must pass without skips')
    require(set(q.get('source_files', {})) == set(contract.source_paths(donor)),
        'Exact retained and current source dependency closure required')
    for name, expected in q['source_files'].items():
        require(type(name) is str and not Path(name).is_absolute() and '..' not in Path(name).parts and chr(92) not in name, 'Unsafe qualified source')
        builder().checked_file(ROOT/name, expected)
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
    donor = validate_donor(args.donor_apk, args.donor_build_report); q = validate_qualification(read_json(args.qualification), commit, donor)
    native = validate_native(args.client_directory, commit, donor, args.native_source_commit)
    require(q.get('native_client_render_queue') == native and q.get('java_sources') == current_sources(donor)
        and q.get('client_gpu_runtime') == donor['client_gpu_runtime']
        and q.get('retained_native_client_renderer_attribution') == donor['native_client_renderer_attribution']
        and q.get('native_build_provenance') == native_build_provenance(native,args.client_directory,commit),
        'Qualified native/Java/retained successful GPU inputs differ')
    password = base.signing_password_spec(args.password_env); base.verify_signing_identity(args.keystore, 'coh-client-interactive', SIGNER, password)
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), 'Fresh .25 APK required')
    base.checked_file(args.testing_notes); require(0 < args.testing_notes.stat().st_size <= 65536, 'Bounded testing notes required')
    for tool in (args.android_jar, args.build_tools/'aapt2', args.build_tools/'zipalign', args.build_tools/'lib/apksigner.jar'):
        require(tool.is_file() and not tool.is_symlink(), 'Required Android SDK tool missing')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-render-queue-', dir=args.output.parent) as temporary:
        work = Path(temporary); runtime, payloads = extract_and_repair(args.donor_apk, donor, work/'donor', commit, args.client_directory, native)
        manifest = work/'AndroidManifest.xml'; repair_android_manifest(ROOT/'android/interactive/src/main/AndroidManifest.xml', manifest)
        resources, unsigned, aligned, signed = (work/n for n in ('resources.zip', 'unsigned.apk', 'aligned.apk', 'signed.apk'))
        base.run(args.build_tools/'aapt2', 'compile', '--dir', ROOT/'android/interactive/src/main/res', '-o', resources)
        base.run(args.build_tools/'aapt2', 'link', '-I', args.android_jar, '--manifest', manifest, '--min-sdk-version', '26', '--target-sdk-version', '35', resources, '-o', unsigned)
        with zipfile.ZipFile(unsigned) as archive:
            require(retained.archive_inventory(archive) == {'AndroidManifest.xml', *donor['retained_android_resources']}, 'Generated Android inventory differs')
            for name, expected in donor['retained_android_resources'].items(): require(pin(archive.read(name)) == expected, 'Retained Android resources changed')
        with zipfile.ZipFile(unsigned, 'a', zipfile.ZIP_DEFLATED) as archive:
            base.append_payloads(archive, [(work/'donor'/n, n) for n in sorted(payloads)])
            archive.write(work/'donor/classes.dex', 'classes.dex')
        base.run(args.build_tools/'zipalign', '-f', '4', unsigned, aligned)
        base.run('java', '-jar', args.build_tools/'lib/apksigner.jar', 'sign', '--ks', args.keystore,
            '--ks-key-alias', 'coh-client-interactive', '--ks-pass', password, '--key-pass', password, '--out', signed, aligned)
        certificate = retained.verify_signature(signed, args.build_tools); base.run(args.build_tools/'zipalign', '-c', '4', signed)
        current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', signed))
        verify_derivative(signed, donor, payloads, commit, native); retained.verify_binary_manifest(signed, args.donor_apk, args.build_tools)
        shutil.copyfile(signed, args.output)
        report = {'format': 1, 'apk': APK_NAME, **base.file_pin(args.output), 'repository_commit': commit, 'runtime_repository_commit': commit,
            'retained_runtime_repository_commit': DONOR_RUNTIME_COMMIT, 'application_id': base.APP_ID, 'version_name': VERSION_NAME, 'version_code': VERSION_CODE,
            'abi': 'arm64-v8a', 'scope': QUALIFICATION_SCOPE, 'donor': donor_link(), 'signer_certificate_sha256': certificate,
            'signing_key_created': False, 'signature_verified': True, 'package_badging_verified': True, 'binary_manifest_version_only_verified': True,
            'payload_bytes_verified': True, 'payloads': payloads, 'changed_apk_payloads': sorted(REPLACED_PAYLOADS), 'added_apk_payloads': [],
            'baseline_payloads_verified': 77, 'retained_baseline_payloads_verified': 70, 'retained_dex': donor['recompiled_dex'],
            'java_sources': donor['java_sources'], 'changed_java_sources': [], 'retained_java_sources_verified': 19,
            'qualification': q, 'qualification_receipt': base.file_pin(args.qualification), 'testing_notes': base.file_pin(args.testing_notes),
            'native_client_render_queue': native, 'native_build_provenance': native_build_provenance(native, args.client_directory, commit),
            'previous_native_build_provenance': donor['native_build_provenance'],
            'native_client_compiled_in_current_run': q['native_client_compiled_in_current_run'],
            'native_client_compiled_in_current_publication_run': q['native_client_compiled_in_current_publication_run'],
            'publication_provenance': publication_provenance(commit), 'retained_native_repository_commit': PARENT_NATIVE_COMMIT, 'native_build_repository_commit': native['repository_commit'],
            'runtime_manifest': runtime,
            'runtime_manifest_sha256': payloads['assets/runtime/runtime-manifest.json']['sha256'],
            **dict.fromkeys(FALSE_FLAGS, False), **dict.fromkeys(TRUE_FLAGS, True), **{name: donor[name] for name in RETAINED_FIELDS}}
        (args.output.parent/REPORT_NAME).write_bytes(shared.encoded(report))
    shutil.copyfile(args.testing_notes, args.output.parent/NOTES_NAME)
    args.output.with_suffix('.apk.sha256').write_text(report['sha256']+'  '+APK_NAME+'\n')
    verify_report(argparse.Namespace(**vars(args), apk=args.output, build_report=args.output.parent/REPORT_NAME), commit)
    print('Qualified native render queue APK:', args.output, report['sha256']); return report


def verify_report(args, commit):
    donor = validate_donor(args.donor_apk, args.donor_build_report); q = validate_qualification(read_json(args.qualification), commit, donor)
    native = validate_native(args.client_directory, commit, donor, args.native_source_commit); report = read_json(args.build_report)
    require(report.get('format') == 1 and report.get('apk') == APK_NAME and report.get('repository_commit') == commit
        and report.get('runtime_repository_commit') == commit and report.get('retained_runtime_repository_commit') == DONOR_RUNTIME_COMMIT
        and report.get('scope') == QUALIFICATION_SCOPE and report.get('donor') == donor_link()
        and report.get('application_id') == builder().APP_ID and report.get('version_name') == VERSION_NAME and report.get('version_code') == VERSION_CODE
        and report.get('abi') == 'arm64-v8a' and report.get('signer_certificate_sha256') == SIGNER and report.get('signing_key_created') is False
        and report.get('qualification') == q and report.get('qualification_receipt') == builder().file_pin(args.qualification)
        and report.get('native_client_render_queue') == q.get('native_client_render_queue') == native
        and report.get('native_build_provenance') == q.get('native_build_provenance') == native_build_provenance(native, args.client_directory, commit)
        and report.get('publication_provenance') == q.get('publication_provenance') == publication_provenance(commit)
        and report.get('retained_native_repository_commit') == PARENT_NATIVE_COMMIT and report.get('native_build_repository_commit') == native['repository_commit']
        and q.get('client_gpu_runtime') == donor['client_gpu_runtime']
        and q.get('retained_native_client_renderer_attribution') == donor['native_client_renderer_attribution']
        and report.get('previous_native_build_provenance') == donor['native_build_provenance']
        and report.get('native_client_compiled_in_current_run') is q['native_client_compiled_in_current_run']
        and report.get('native_client_compiled_in_current_publication_run') is q['native_client_compiled_in_current_publication_run']
        and report.get('java_sources') == q.get('java_sources') == donor['java_sources'] and report.get('changed_java_sources') == []
        and report.get('retained_java_sources_verified') == 19 and report.get('retained_dex') == donor['recompiled_dex']
        and report.get('changed_apk_payloads') == sorted(REPLACED_PAYLOADS) and report.get('added_apk_payloads') == []
        and report.get('baseline_payloads_verified') == 77 and report.get('retained_baseline_payloads_verified') == 70
        and all(report.get(name) == donor[name] for name in RETAINED_FIELDS)
        and all(report.get(name) is False for name in FALSE_FLAGS)
        and all(report.get(name) is True for name in TRUE_FLAGS+('signature_verified', 'package_badging_verified', 'binary_manifest_version_only_verified', 'payload_bytes_verified')),
        'Exact retained .24 native continuation build receipt differs')
    builder().checked_file(args.apk, report); runtime = verify_derivative(args.apk, donor, report['payloads'], commit, native)
    require(report.get('runtime_manifest') == runtime and report.get('runtime_manifest_sha256') == report['payloads']['assets/runtime/runtime-manifest.json']['sha256'], 'Runtime continuation provenance differs')
    retained.verify_binary_manifest(args.apk, args.donor_apk, args.build_tools); retained.verify_signature(args.apk, args.build_tools)
    builder().run(args.build_tools/'zipalign', '-c', '4', args.apk); builder(repaired=True).verify_badging(builder().run(args.build_tools/'aapt2', 'dump', 'badging', args.apk))
    checksum = args.apk.with_suffix('.apk.sha256'); require(checksum.read_text() == report['sha256']+'  '+APK_NAME+'\n', 'Checksum differs')
    notes = args.apk.parent/NOTES_NAME; builder().checked_file(notes, report['testing_notes']); builder().checked_file(args.testing_notes, report['testing_notes'])
    return report, checksum, notes


def validate_existing_release(release):
    require(type(release.get('id')) is int and release['id'] > 0 and release.get('tag_name') == RELEASE_TAG
        and release.get('draft') is False and release.get('prerelease') is True
        and type(release.get('published_at')) is str and bool(release['published_at']), 'Incomplete existing release: resume original owner jobs')
    assets = release.get('assets'); base = 'https://github.com/'+REPOSITORY+'/releases/download/'+RELEASE_TAG+'/'
    require(type(assets) is list and len(assets) == 3 and {v.get('name') for v in assets} == {APK_NAME, APK_NAME+'.sha256', NOTES_NAME}, 'Incomplete release asset inventory')
    for value in assets:
        require(value.get('state') == 'uploaded' and type(value.get('size')) is int and 0 < value['size'] <= 2*1024**3
            and re.fullmatch(r'sha256:[0-9a-f]{64}', str(value.get('digest', ''))) and value.get('browser_download_url') == base+value['name'], 'Incomplete release asset metadata')
        if value['name'] == APK_NAME+'.sha256': require(value['size'] == 97, 'Incomplete checksum metadata')
        if value['name'] == NOTES_NAME: require(value['size'] <= 65536, 'Oversized testing instructions metadata')
    return True


bounded_download = parent_history.bounded_download


def authenticated_artifact_download(artifact_id, destination, expected):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl): return None
    request = urllib.request.Request('https://api.github.com/repos/'+REPOSITORY+'/actions/artifacts/'+str(artifact_id)+'/zip',
        headers={'Authorization': 'Bearer '+os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json'})
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
            raise ValueError('Artifact API must redirect to immutable ZIP')
    except urllib.error.HTTPError as error:
        require(error.code == 302 and urllib.parse.urlparse(error.headers['Location']).scheme == 'https', 'Unexpected artifact redirect')
        location = error.headers['Location']
    bounded_download(location, destination, expected)


def download_donor_evidence(args):
    """Fetch only the immutable evidence artifact; never rebuild an old probe."""
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh evidence directory required'); args.output.mkdir(parents=True)
    target = args.output/DONOR_EVIDENCE_ARCHIVE
    authenticated_artifact_download(DONOR_EVIDENCE_ID, target, DONOR_EVIDENCE)
    members = donor_evidence_members(target)
    with zipfile.ZipFile(target) as archive:
        for name in sorted(members):
            destination = args.output/name; destination.write_bytes(archive.read(name)); builder().checked_file(destination, members[name])
    print('Authenticated original published .24 packaging evidence; driver and probes retained')
    print('Authenticated donor build-report pin:', json.dumps(members[DONOR_REPORT_NAME], sort_keys=True))




HOST_NATIVE_REUSE_FILES = (SOURCE_FILES - frozenset('android/guest/'+name for name in HELPERS)
    - frozenset({'tools/android/interactive/analyze_client_render_queue.py',
        'tools/android/interactive/test_analyze_client_render_queue.py',
        'tools/android/interactive/test_client_render_queue_contract.py',
        'tools/android/interactive/test_client_render_queue_guest.py'})) | frozenset({
            'docs/HANDOFF.md','docs/android-evidence/render-queue-0.13.25-publication.json'})


def validate_native_reuse_records(run, jobs, artifacts, comparison, source_commit, publication_commit):
    """Accept one completed Game job only for an exact bounded host-only followup."""
    require(re.fullmatch('[0-9a-f]{40}', source_commit or '')
        and re.fullmatch('[0-9a-f]{40}', publication_commit or ''), 'Full native and publication source identities required')
    require(type(run.get('id')) is int and run['id'] > 0 and run.get('status') == 'completed'
        and run.get('head_sha') == source_commit and run.get('head_branch') == BRANCH
        and run.get('path') == WORKFLOW and run.get('event') in ('push','workflow_dispatch')
        and run.get('repository', {}).get('full_name') == REPOSITORY,
        'Reuse requires a completed exact .25 owner; active or unrelated owners are rejected')
    entries = jobs.get('jobs', [])
    require(type(entries) is list and jobs.get('total_count') == len(entries)
        and len([item for item in entries if item.get('name') == 'client']) == 1,
        'Complete original native owner job inventory required')
    client = next(item for item in entries if item.get('name') == 'client')
    require(client.get('run_id') == run['id'] and client.get('head_sha') == source_commit
        and client.get('status') == 'completed' and client.get('conclusion') == 'success',
        'Original native Game job must have completed successfully')
    entries = artifacts.get('artifacts', [])
    require(type(entries) is list and artifacts.get('total_count') == len(entries),
        'Complete original native artifact inventory required')
    matches = [item for item in entries if item.get('name') == 'coh-client-render-queue-native']
    require(len(matches) == 1, 'Exactly one completed current queue Game artifact required')
    artifact = matches[0]
    require(type(artifact.get('id')) is int and artifact['id'] > 0 and artifact.get('expired') is False
        and type(artifact.get('size_in_bytes')) is int and 0 < artifact['size_in_bytes'] <= 64*1024**2
        and re.fullmatch('sha256:[0-9a-f]{64}', str(artifact.get('digest','')))
        and artifact.get('workflow_run', {}).get('id') == run['id']
        and artifact['workflow_run'].get('head_sha') == source_commit,
        'Authenticated original current queue Game artifact required')
    compare_path = REPOSITORY+'/compare/'+source_commit+'...'+publication_commit
    commits = comparison.get('commits')
    count = comparison.get('total_commits')
    require(comparison.get('url') == 'https://api.github.com/repos/'+compare_path
        and comparison.get('html_url') == 'https://github.com/'+compare_path
        and comparison.get('base_commit', {}).get('sha') == source_commit
        and comparison.get('merge_base_commit', {}).get('sha') == source_commit
        and comparison.get('status') == ('identical' if source_commit == publication_commit else 'ahead')
        and type(count) is int and 0 <= count <= 64
        and type(comparison.get('ahead_by')) is int and comparison['ahead_by'] == count
        and type(comparison.get('behind_by')) is int and comparison['behind_by'] == 0
        and type(commits) is list and len(commits) == count
        and type(comparison.get('files')) is list and len(comparison['files']) < 300,
        'Bounded forward native-to-publication source history required')
    # GitHub's compare response has no head_commit field. Its complete,
    # chronological commits list must end at the requested publication SHA.
    parents_by_commit = {}
    known = {source_commit}
    for item in commits:
        require(type(item) is dict and type(item.get('sha')) is str
            and re.fullmatch('[0-9a-f]{40}', item['sha'])
            and item['sha'] not in known and type(item.get('parents')) is list
            and 0 < len(item['parents']) <= 65,
            'Complete distinct forward comparison commits required')
        parents = []
        for parent in item['parents']:
            require(type(parent) is dict and type(parent.get('sha')) is str
                and parent['sha'] in known, 'Comparison commit ancestry must remain inside the complete forward history')
            parents.append(parent['sha'])
        require(len(parents) == len(set(parents)), 'Duplicate comparison commit parents rejected')
        parents_by_commit[item['sha']] = parents
        known.add(item['sha'])
    require((source_commit == publication_commit and count == 0) or
        (source_commit != publication_commit and count > 0 and commits[-1]['sha'] == publication_commit),
        'Complete comparison history must end at the exact publication source')
    ancestors = {publication_commit}
    pending = [publication_commit]
    while pending:
        for parent in parents_by_commit.get(pending.pop(), []):
            if parent not in ancestors:
                ancestors.add(parent); pending.append(parent)
    require(ancestors == known, 'Comparison history contains commits outside the exact publication ancestry')
    names = []
    for item in comparison['files']:
        name = item.get('filename')
        require(type(name) is str and name in HOST_NATIVE_REUSE_FILES
            and item.get('status') in ('added','modified','removed') and 'previous_filename' not in item,
            'Native reuse permits only reviewed host publication corrections')
        names.append(name)
    require(len(names) == len(set(names)) and ((source_commit == publication_commit and not names
        and count == 0) or (source_commit != publication_commit and bool(names)
        and count > 0)), 'Native reuse source comparison identity differs')
    return {'format':1,'status':'passed','native_source_commit':source_commit,
        'publication_source_commit':publication_commit,'original_native_run_id':run['id'],
        'original_native_artifact_id':artifact['id'],'original_native_artifact_zip':{
            'bytes':artifact['size_in_bytes'],'sha256':artifact['digest'][7:]},
        'reviewed_host_only_changes':sorted(names),'native_build_repeated':False}


def validate_native_reuse(args):
    require(re.fullmatch('[1-9][0-9]*', str(args.run_id)), 'Positive exact native owner required')
    commit = builder().source_commit(args.repository_commit)
    api = module('client_render_queue_reuse_github', Path(__file__).with_name('build_atlas_gameplay_apk.py')).GitHub(os.environ.get('GH_TOKEN'))
    run = api.request('/actions/runs/'+str(args.run_id))
    require(run.get('id') == int(args.run_id), 'Native owner API identity differs')
    receipt = validate_native_reuse_records(run,
        api.request('/actions/runs/'+str(args.run_id)+'/jobs?filter=latest&per_page=100'),
        api.request('/actions/runs/'+str(args.run_id)+'/artifacts?per_page=100'),
        api.request('/compare/'+args.native_source_commit+'...'+commit+'?per_page=100'),
        args.native_source_commit,commit)
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh native reuse audit required')
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_bytes(shared.encoded(receipt))
    print('Original completed current queue Game accepted for exact host-only publication correction')
    return receipt


def download_native_reuse(args):
    receipt = read_json(args.receipt)
    require(receipt.get('format') == 1 and receipt.get('status') == 'passed'
        and type(receipt.get('original_native_run_id')) is int and receipt['original_native_run_id'] > 0
        and type(receipt.get('original_native_artifact_id')) is int and receipt['original_native_artifact_id'] > 0
        and receipt.get('native_build_repeated') is False
        and re.fullmatch('[0-9a-f]{40}', receipt.get('native_source_commit',''))
        and receipt.get('publication_source_commit') == builder().source_commit(args.repository_commit),
        'Exact authenticated native reuse receipt required')
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh reused native destination required')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-authenticated-queue-native-',dir=args.output.parent) as temporary:
        target=Path(temporary)/'original-native.zip'
        authenticated_artifact_download(receipt['original_native_artifact_id'], target,
            receipt['original_native_artifact_zip'])
        with zipfile.ZipFile(target) as archive:
            expected={'CityOfHeroes.exe','CMakeCache.txt',native_producer().MANIFEST,native_producer().CHECKS}
            require(retained.archive_inventory(archive) == expected, 'Exact completed Game artifact inventory required')
            args.output.mkdir()
            for entry in archive.infolist():
                require(not entry.is_dir() and 0 < entry.file_size <= 32*1024**2,
                    'Unbounded reused Game artifact member')
                (args.output/entry.filename).write_bytes(archive.read(entry))
    native=native_producer().validate_package(args.output,receipt['native_source_commit'])
    require(native['run_url'] == 'https://github.com/'+REPOSITORY+'/actions/runs/'+str(receipt['original_native_run_id']),
        'Reused raw native producer owner differs from authenticated original')
    print('Authenticated completed current queue Game artifact; original raw producer preserved')
    return native


def publish_release(api, report, assets, notes):
    require(tuple(p.name for p in assets) == (APK_NAME, APK_NAME+'.sha256', NOTES_NAME), 'Unexpected release assets'); builder().checked_file(assets[0], report)
    for path in ('/releases/tags/'+RELEASE_TAG, '/git/ref/tags/'+RELEASE_TAG):
        try: existing = api.request(path)
        except urllib.error.HTTPError as error:
            if error.code != 404: raise
        else:
            require(not path.startswith('/releases/'), 'Existing release is never replaced')
            require(existing.get('object', {}).get('type') == 'commit' and existing['object'].get('sha') == report['repository_commit'], 'Existing tag points elsewhere')
    previous.require_current_release_head(api, report['repository_commit'])
    release = api.request('/releases', {'tag_name': RELEASE_TAG, 'target_commitish': report['repository_commit'],
        'name': 'COH Atlas Gameplay 0.13.25 — coalesced render wakes and sparse scene timing',
        'body': notes+'\n\nAPK SHA-256: `'+report['sha256']+'`.\n[Hosted qualification](https://github.com/'+REPOSITORY+'/actions/runs/'+os.environ.get('GITHUB_RUN_ID', '')+').\n',
        'draft': True, 'prerelease': True, 'generate_release_notes': False, 'make_latest': 'false'}, method='POST')
    require(type(release.get('id')) is int and release.get('draft') is True and release.get('tag_name') == RELEASE_TAG, 'Unexpected draft release')
    for path in assets:
        uploaded = api.request('/releases/'+str(release['id'])+'/assets?'+urllib.parse.urlencode({'name': path.name}), path, method='POST', upload=True)
        expected = builder().file_pin(path)
        require(uploaded.get('state') == 'uploaded' and uploaded.get('name') == path.name and uploaded.get('size') == expected['bytes']
            and uploaded.get('digest') == 'sha256:'+expected['sha256'], 'Release upload differs')
    previous.require_current_release_head(api, report['repository_commit'])
    result = api.request('/releases/'+str(release['id']), {'draft': False, 'prerelease': True, 'make_latest': 'false'}, method='PATCH')
    require(result.get('id') == release['id'] and result.get('draft') is False and result.get('prerelease') is True and result.get('tag_name') == RELEASE_TAG, 'Publication incomplete')
    return result.get('html_url')


def publish(args):
    require(os.environ.get('GITHUB_REPOSITORY') == REPOSITORY and os.environ.get('GITHUB_REF') == 'refs/heads/'+BRANCH
        and os.environ.get('GITHUB_EVENT_NAME') in ('push', 'workflow_dispatch'), 'Publication requires continuation branch')
    commit = builder().source_commit(os.environ.get('GITHUB_SHA')); report, checksum, notes = verify_report(args, commit)
    api = module('client_render_queue_github', Path(__file__).with_name('build_atlas_gameplay_apk.py'))
    print('Published rendering continuation:', publish_release(api.GitHub(os.environ.get('GH_TOKEN')), report, (args.apk, checksum, notes), notes.read_text()))


def download_public(args):
    report = read_json(args.build_report); require(report.get('apk') == APK_NAME, 'Expected .25 public APK')
    specs = {APK_NAME: {k: report[k] for k in ('bytes', 'sha256')}, APK_NAME+'.sha256': pin((report['sha256']+'  '+APK_NAME+'\n').encode()), NOTES_NAME: report['testing_notes']}
    for name, expected in specs.items():
        destination = args.output/name
        if destination.exists() or destination.is_symlink(): builder().checked_file(destination, expected); destination.unlink()
        bounded_download('https://github.com/'+REPOSITORY+'/releases/download/'+RELEASE_TAG+'/'+name, destination, expected)
    print('Actual public APK, checksum and notes independently authenticated')


def main():
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest='command', required=True)
    for name in ('download-donor', 'download-donor-evidence'):
        command = commands.add_parser(name); command.add_argument('--output', type=Path, required=True)
    command = commands.add_parser('validate-native-reuse'); command.add_argument('--run-id', required=True); command.add_argument('--native-source-commit', required=True); command.add_argument('--repository-commit', required=True); command.add_argument('--output', type=Path, required=True)
    command = commands.add_parser('download-native-reuse'); command.add_argument('--receipt', type=Path, required=True); command.add_argument('--repository-commit', required=True); command.add_argument('--output', type=Path, required=True)
    command = commands.add_parser('download-public'); command.add_argument('--output', type=Path, required=True); command.add_argument('--build-report', type=Path, required=True)
    for name in ('build', 'audit', 'publish'):
        command = commands.add_parser(name)
        for value in ('donor-apk', 'donor-build-report', 'qualification', 'build-tools', 'client-directory'): command.add_argument('--'+value, type=Path, required=True)
        command.add_argument('--native-source-commit', required=True); command.add_argument('--testing-notes', type=Path, default=NOTES); command.add_argument('--repository-commit', default=os.environ.get('GITHUB_SHA'))
        if name == 'build':
            command.add_argument('--android-jar', type=Path, required=True); command.add_argument('--keystore', type=Path, required=True)
            command.add_argument('--password-env', default='COH_INTERACTIVE_KEYSTORE_PASSWORD'); command.add_argument('--output', type=Path, required=True)
        else:
            command.add_argument('--apk', type=Path, required=True); command.add_argument('--build-report', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'download-donor': bounded_download(DONOR_URL, args.output, DONOR_APK)
    elif args.command == 'download-donor-evidence': download_donor_evidence(args)
    elif args.command == 'download-public': download_public(args)
    elif args.command == 'validate-native-reuse': validate_native_reuse(args)
    elif args.command == 'download-native-reuse': download_native_reuse(args)
    elif args.command == 'build': build(args)
    elif args.command == 'publish': publish(args)
    else: print('Fresh-process candidate verified:', verify_report(args, builder().source_commit(args.repository_commit))[0]['sha256'])


if __name__ == '__main__': main()
