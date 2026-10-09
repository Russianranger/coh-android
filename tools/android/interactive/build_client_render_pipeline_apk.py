#!/usr/bin/env python3
"""Publish a Game-only rendering continuation over the immutable public .21 APK.

Preserve the successful .21 GPU driver, WGL/Vulkan probes, Android DEX, resources,
servers, save rules, visual assets and Software fallback. Authenticate the donor
build report through its independently pinned original Actions artifact ZIP.
"""
from __future__ import annotations
import argparse
import copy
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

import build_client_gpu_repair_apk as previous

ROOT, require, module, shared = previous.ROOT, previous.require, previous.module, previous.shared
REPOSITORY, BRANCH, SIGNER = previous.REPOSITORY, previous.BRANCH, previous.SIGNER
retained, engine = previous.retained, previous.engine
DONOR_COMMIT, DONOR_RUN_ID = '20b559420b1bb0978b7eac6e6eecdfe2a468f693', 37837207655
DONOR_APK_NAME, DONOR_REPORT_NAME = 'COH-Atlas-Gameplay-0.13.21.apk', 'client-gpu-repair-apk-build-report.json'
DONOR_APK = {'bytes': 1560283912, 'sha256': '67a8fe01d8f6e7cbb5139d7d1cecc7706d33b25671d0072a93808b1fc04bbe76'}
DONOR_EVIDENCE_ID = 11576253333
DONOR_EVIDENCE = {'bytes': 1255583, 'sha256': '2aad94d4dacd07d1c02fafafc9e41f8b65f92322b6d6fdd369caaf2935223b2e'}
DONOR_EVIDENCE_ARCHIVE = 'published-0.13.21-packaging-evidence.zip'
DONOR_EVIDENCE_NAMES = frozenset({DONOR_REPORT_NAME, 'COH-Atlas-Gameplay-0.13.21-testing.txt', DONOR_APK_NAME+'.sha256'})
DONOR_GAME = {'bytes': 9487872, 'sha256': 'adcabb11135fe44b2c1f997a088ec58e4ea0d90e9defaa9f88efea34538caa44'}
DONOR_URL = 'https://github.com/'+REPOSITORY+'/releases/download/coh-atlas-gameplay-v0.13.21/'+DONOR_APK_NAME
VERSION_NAME, VERSION_CODE = '0.13.22', 37
APK_NAME, REPORT_NAME = 'COH-Atlas-Gameplay-0.13.22.apk', 'client-render-pipeline-apk-build-report.json'
NOTES_NAME = 'COH-Atlas-Gameplay-0.13.22-testing.txt'
RELEASE_TAG = 'coh-atlas-gameplay-v0.13.22'
NOTES = ROOT/'docs'/NOTES_NAME
WORKFLOW = '.github/workflows/android-client-render-pipeline.yml'
QUALIFICATION_SCRIPT = 'tools/android/interactive/qualify_client_render_pipeline.py'
QUALIFICATION_SCOPE = 'native_render_pipeline_wake_repair_and_focused_frame_attribution_retaining_public_0_13_21'
HELPERS = frozenset({'native_responsiveness_contract.py', 'client_startup_diagnostic.py', 'client_gpu_profile.py', 'texture_header_index.py'})
REPLACED_PAYLOADS = frozenset('assets/runtime/'+name for name in HELPERS|{'client-runtime.zip', 'client-manifest.json', 'runtime-manifest.json'})
ACTUAL_NATIVE_ANCESTRY_CHECKS = dict(previous.old.previous.ACTUAL_NATIVE_ANCESTRY_CHECKS)
ACTUAL_NATIVE_ANCESTRY_CHECKS.pop('actual_gameplay_Game_predecessor_verified')
ACTUAL_NATIVE_ANCESTRY_CHECKS['actual_renderer_Game_predecessor_verified'] = True
CHECKS = ('native_render_pipeline_and_owned_current_game_controls_verified',
    'retained_gameplay_postgresql_gpu_cleanup_and_recovery_guards_verified',
    'exact_game_only_payload_android_shell_and_successful_gpu_bytes_verified')
SOURCE_FILES = frozenset({WORKFLOW, QUALIFICATION_SCRIPT,
    'tools/android/interactive/build_client_render_pipeline_apk.py',
    'tools/android/interactive/test_client_render_pipeline_package.py',
    'tools/android/interactive/analyze_client_render_pipeline.py',
    'tools/android/interactive/test_client_render_pipeline_report.py',
    'docs/android-evidence/renderer-sync-0.13.21-thor-20261009.json',
    'docs/COH-PERFORMANCE-0.13.22.md', 'docs/'+NOTES_NAME,
    *('android/guest/'+name for name in HELPERS)})
REVIEWED_DONOR_SOURCE_CHANGES = frozenset({'docs/HANDOFF.md', *('android/guest/'+name for name in HELPERS)})
FALSE_FLAGS = ('native_dbserver_recompiled', 'native_mapserver_recompiled', 'java_or_dex_recompiled',
    'graphics_driver_changed', 'mesa_driver_compiled_in_current_run', 'native_vulkan_probe_compiled_in_current_run',
    'wgl_probe_compiled_in_current_run', 'physical_performance_validated', 'physical_fps_gain_validated',
    'asset_reimport_required', 'world_assets_changed', 'prepared_cache_archive_changed',
    'wine_or_fex_changed', 'save_acceptance_relaxed', 'zoning_implemented')
TRUE_FLAGS = ('native_client_recompiled', 'retained_android_dex_and_resources_verified',
    'successful_gpu_driver_and_both_probes_retained', 'software_fallback_preserved',
    'graphical_fidelity_preserved_by_payload_and_recipe', 'runtime_refresh_required', 'previous_runtime_generation_retained')
RETAINED_FIELDS = previous.old.RETAINED_RECEIPT_FIELDS + ('client_gpu_runtime',)
read_json, read_json_value = previous.read_json, previous.read_json_value


def native_producer():
    return module('client_render_pipeline_native_producer', ROOT/'tools/android/interactive/package_client_render_pipeline_native.py')


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
            'Exact published .21 packaging evidence inventory required')
        result = {}
        for entry in archive.infolist():
            require(entry.filename in DONOR_EVIDENCE_NAMES and not entry.is_dir() and 0 < entry.file_size <= 256*1024**2,
                'Unsafe or unbounded donor evidence member')
            result[entry.filename] = pin(archive.read(entry))
    return result


def validate_donor_receipt(path):
    expected = donor_evidence_members(path.parent/DONOR_EVIDENCE_ARCHIVE)[DONOR_REPORT_NAME]
    builder().checked_file(path, expected); donor = read_json(path); q = donor.get('qualification', {})
    require(donor.get('format') == 1 and donor.get('repository_commit') == DONOR_COMMIT
        and donor.get('runtime_repository_commit') == DONOR_COMMIT and donor.get('apk') == DONOR_APK_NAME
        and {k: donor.get(k) for k in DONOR_APK} == DONOR_APK
        and donor.get('application_id') == builder().APP_ID and donor.get('version_name') == '0.13.21'
        and donor.get('version_code') == 36 and donor.get('abi') == 'arm64-v8a'
        and donor.get('signer_certificate_sha256') == SIGNER and donor.get('signing_key_created') is False
        and all(donor.get(k) is True for k in ('signature_verified', 'package_badging_verified',
            'binary_manifest_version_only_verified', 'payload_bytes_verified', 'setup_memory_guards_preserved'))
        and len(donor.get('payloads', {})) == 77 and len(donor.get('java_sources', {})) == 19
        and q.get('status') == 'passed' and q.get('scope') == previous.QUALIFICATION_SCOPE
        and q.get('repository_commit') == DONOR_COMMIT and q.get('tests_run') == 1470
        and len(q.get('test_suites', {})) == 99 and all(v.get('status') == 'passed' and v.get('skipped') == 0 for v in q['test_suites'].values())
        and donor.get('native_client_renderer_attribution') == q.get('native_client_renderer_attribution')
        and donor.get('client_gpu_runtime') == q.get('client_gpu_runtime'), 'Exact independently authenticated .21 donor receipt differs')
    return donor


def current_sources(donor):
    base = builder(); sources = retained.retained.java_sources(base, ROOT/'out/no-generated-java')
    pins = {p.relative_to(ROOT).as_posix(): base.file_pin(p) for p in sources if p.is_relative_to(ROOT)}
    require(pins == donor['java_sources'] and len(pins) == 19, 'All nineteen authored .21 Java sources must remain exact')
    for name, expected in donor['preserved_sources'].items():
        # Historical preserved_sources remain a frozen older producer history.
        # The actual current .21 Java bytes are independently pinned above.
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
        require(retained.archive_inventory(archive) == set(donor['payloads'])|set(shell)|{'AndroidManifest.xml'}, 'Exact .21 donor inventory required')
        for name, expected in shell.items(): require(pin(archive.read(name)) == expected, 'Donor Android shell differs: '+name)
        require(read_json_value(archive.read('assets/runtime/runtime-manifest.json')) == donor['runtime_manifest'], 'Donor runtime provenance differs')
        donor['_client_verification'] = read_json_value(archive.read('assets/runtime/client-manifest.json'))
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
    require(retained.verify_apk_server_archives(apk) == donor['server_payload_extraction_preflight'], 'Donor server extraction differs')
    current_sources(donor); return donor


def validate_native(directory, commit, donor):
    producer = native_producer(); native = producer.validate_package(directory, commit)
    require(native['base_client_executable'] == donor['native_client_renderer_attribution']['files']['CityOfHeroes.exe']
        and native['build_input']['base_client_renderer_attribution_build_input'] == donor['native_client_renderer_attribution']['build_input'],
        'New native Game must extend the exact physically accepted .21/.19 Game ancestry')
    engine.validate_native_source_ancestry(native['retained_source_inputs'], donor['immutable_donor_provenance']['native_responsiveness']['build_inputs'])
    require(native['schema_sources_sha256'] == donor['immutable_donor_provenance']['native_responsiveness']['retained_cache']['schema_sources_sha256'],
        'Prepared native cache schema changed')
    if os.environ.get('GITHUB_RUN_ID'):
        require(native['run_url'] == 'https://github.com/'+REPOSITORY+'/actions/runs/'+os.environ['GITHUB_RUN_ID'],
            'Game must be built and qualified in this exact owner run')
    return native


def client_manifest(donor, native):
    result = copy.deepcopy(donor['_native_client_manifest'])
    result['files']['CityOfHeroes.exe'] = native['files']['CityOfHeroes.exe']
    result['dependency_report'] = shared.dependency_report(result['files'])
    require(not result['dependency_report']['unresolved'], 'New Game imports exceed retained DLL closure')
    result['client_render_pipeline'] = {'manifest': native, 'manifest_sha256': shared.native_contract.canonical_sha(native),
        'base_client_renderer_attribution_manifest_sha256': result['client_renderer_attribution']['manifest_sha256'],
        'base_client_executable': copy.deepcopy(donor['_native_client_manifest']['files']['CityOfHeroes.exe'])}
    shared.native_contract.client_contract(result, donor['immutable_donor_provenance']['native_responsiveness'])
    return result


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
        require(read_json_value(archive.read('client-package.json')) == expected, 'Actual native client wrapper differs')
    output.replace(path)


def verification_manifests(donor, updates, commit, native):
    require(set(updates) == HELPERS|{'client-runtime.zip'}, 'Only exact native integration inputs required')
    client = copy.deepcopy(donor['_client_verification']); client['files'].update(updates)
    runtime = copy.deepcopy(donor['runtime_manifest']); runtime['files'].update(updates)
    runtime['files']['client-manifest.json'] = pin(shared.encoded(client))
    runtime.update(repository_commit=commit, scope=QUALIFICATION_SCOPE)
    runtime['client_render_pipeline'] = {'format': 1, 'repository_commit': commit, 'donor_repository_commit': DONOR_COMMIT,
        'native_recompiled': True, 'native_manifest_sha256': shared.native_contract.canonical_sha(native),
        'replacement_scope': 'CityOfHeroes.exe_only', 'changed_guest_helpers': sorted(HELPERS),
        'successful_gpu_driver_and_both_probes_retained': True, 'android_dex_and_resources_retained': True,
        'graphical_fidelity_preserved': True, 'physical_performance_validated': False}
    require(set(client['files']) == set(donor['_client_verification']['files'])
        and set(runtime['files']) == set(donor['runtime_manifest']['files']), 'Runtime inventory must remain exact')
    return client, runtime


def payload_boundaries(payloads, donor):
    require(len(payloads) == 77 and set(payloads) == set(donor['payloads'])
        and {n for n in payloads if payloads[n] != donor['payloads'][n]} == REPLACED_PAYLOADS,
        'Exactly seven reviewed integration payloads and seventy retained .21 payloads required')


def extract_and_repair(apk, donor, destination, commit, directory, native):
    destination.mkdir(parents=True); base = builder()
    with zipfile.ZipFile(apk) as archive:
        for entry in archive.infolist():
            if entry.filename == 'AndroidManifest.xml' or entry.filename.startswith('META-INF/'): continue
            target = destination/entry.filename; target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open('xb') as output: shutil.copyfileobj(source, output, 1024*1024)
    require(all(base.file_pin(destination/n) == v for n, v in donor['payloads'].items()), 'Extracted .21 donor payload bytes differ')
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
        for n, expected in shell.items(): require(pin(archive.read(n)) == expected, 'Exact .21 DEX/resources changed: '+n)
        for name in HELPERS: require(payloads['assets/runtime/'+name] == base.file_pin(ROOT/'android/guest'/name), 'Current helper bytes differ')
        client, runtime = verification_manifests(donor, {n: payloads['assets/runtime/'+n] for n in HELPERS|{'client-runtime.zip'}}, commit, native)
        require(archive.read('assets/runtime/client-manifest.json') == shared.encoded(client)
            and archive.read('assets/runtime/runtime-manifest.json') == shared.encoded(runtime), 'Actual manifest/provenance bytes differ')
        with archive.open('assets/runtime/client-runtime.zip') as source, tempfile.TemporaryFile() as target:
            shutil.copyfileobj(source, target, 1024*1024); target.seek(0)
            with zipfile.ZipFile(target) as client_zip:
                package = read_json_value(client_zip.read('client-package.json')); members = engine.startup.startup.client_member_pins(client_zip)
                require(package == client_manifest(donor, native) and members['CityOfHeroes.exe'] ==
                    {'bytes': native['files']['CityOfHeroes.exe']['size'], 'sha256': native['files']['CityOfHeroes.exe']['sha256']}
                    and set(members) == set(donor['_client_members']) and all(members[n] == donor['_client_members'][n]
                        for n in members if n not in {'CityOfHeroes.exe', 'client-package.json'}), 'Actual Game/typed wrapper/retained DLL bytes differ')
    require(retained.verify_apk_server_archives(apk) == donor['server_payload_extraction_preflight'], 'Actual candidate server extraction differs')
    return runtime


def validate_qualification(q, commit):
    contract = module('client_render_pipeline_qualification', ROOT/QUALIFICATION_SCRIPT); contract.validate_suite_inventory()
    require(q.get('format') == 1 and q.get('status') == 'passed' and q.get('scope') == QUALIFICATION_SCOPE
        and q.get('repository_commit') == commit and q.get('runtime_repository_commit') == commit
        and q.get('donor') == donor_link() and q.get('checks') == dict.fromkeys(CHECKS, True)
        and q.get('actual_native_ancestry_validation') == ACTUAL_NATIVE_ANCESTRY_CHECKS
        and q.get('changed_java_sources') == [] and q.get('retained_java_sources_verified') == 19
        and q.get('baseline_payloads_verified') == 77
        and q.get('actual_external_donor_and_full_guest_wrapper_verified') is True
        and all(q.get(k) is False for k in FALSE_FLAGS) and all(q.get(k) is True for k in TRUE_FLAGS), 'Truthful exact .22 qualification required')
    suites = q.get('test_suites', {})
    require(set(suites) == set(contract.TEST_MODULES) and q.get('check_suites') == contract.CHECK_SUITES
        and all(v.get('status') == 'passed' and v.get('skipped') == 0 and type(v.get('tests_run')) is int and v['tests_run'] > 0 for v in suites.values())
        and q.get('tests_run') == sum(v['tests_run'] for v in suites.values()), 'Every retained/new suite must pass without skips')
    require(SOURCE_FILES|frozenset(native_producer().SOURCE_FILES) <= set(q.get('source_files', {})), 'New source closure incomplete')
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
    donor = validate_donor(args.donor_apk, args.donor_build_report); q = validate_qualification(read_json(args.qualification), commit)
    native = validate_native(args.client_directory, commit, donor)
    require(q.get('native_client_render_pipeline') == native and q.get('java_sources') == current_sources(donor)
        and q.get('client_gpu_runtime') == donor['client_gpu_runtime']
        and q.get('retained_native_client_renderer_attribution') == donor['native_client_renderer_attribution'],
        'Qualified native/Java/retained successful GPU inputs differ')
    password = base.signing_password_spec(args.password_env); base.verify_signing_identity(args.keystore, 'coh-client-interactive', SIGNER, password)
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), 'Fresh .22 APK required')
    base.checked_file(args.testing_notes); require(0 < args.testing_notes.stat().st_size <= 65536, 'Bounded testing notes required')
    for tool in (args.android_jar, args.build_tools/'aapt2', args.build_tools/'zipalign', args.build_tools/'lib/apksigner.jar'):
        require(tool.is_file() and not tool.is_symlink(), 'Required Android SDK tool missing')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-render-pipeline-', dir=args.output.parent) as temporary:
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
            'retained_runtime_repository_commit': DONOR_COMMIT, 'application_id': base.APP_ID, 'version_name': VERSION_NAME, 'version_code': VERSION_CODE,
            'abi': 'arm64-v8a', 'scope': QUALIFICATION_SCOPE, 'donor': donor_link(), 'signer_certificate_sha256': certificate,
            'signing_key_created': False, 'signature_verified': True, 'package_badging_verified': True, 'binary_manifest_version_only_verified': True,
            'payload_bytes_verified': True, 'payloads': payloads, 'changed_apk_payloads': sorted(REPLACED_PAYLOADS), 'added_apk_payloads': [],
            'baseline_payloads_verified': 77, 'retained_baseline_payloads_verified': 70, 'retained_dex': donor['recompiled_dex'],
            'java_sources': donor['java_sources'], 'changed_java_sources': [], 'retained_java_sources_verified': 19,
            'qualification': q, 'qualification_receipt': base.file_pin(args.qualification), 'testing_notes': base.file_pin(args.testing_notes),
            'native_client_render_pipeline': native, 'runtime_manifest': runtime,
            'runtime_manifest_sha256': payloads['assets/runtime/runtime-manifest.json']['sha256'],
            **dict.fromkeys(FALSE_FLAGS, False), **dict.fromkeys(TRUE_FLAGS, True), **{name: donor[name] for name in RETAINED_FIELDS}}
        (args.output.parent/REPORT_NAME).write_bytes(shared.encoded(report))
    shutil.copyfile(args.testing_notes, args.output.parent/NOTES_NAME)
    args.output.with_suffix('.apk.sha256').write_text(report['sha256']+'  '+APK_NAME+'\n')
    verify_report(argparse.Namespace(**vars(args), apk=args.output, build_report=args.output.parent/REPORT_NAME), commit)
    print('Qualified native render pipeline APK:', args.output, report['sha256']); return report


def verify_report(args, commit):
    donor = validate_donor(args.donor_apk, args.donor_build_report); q = validate_qualification(read_json(args.qualification), commit)
    native = validate_native(args.client_directory, commit, donor); report = read_json(args.build_report)
    require(report.get('format') == 1 and report.get('apk') == APK_NAME and report.get('repository_commit') == commit
        and report.get('runtime_repository_commit') == commit and report.get('retained_runtime_repository_commit') == DONOR_COMMIT
        and report.get('scope') == QUALIFICATION_SCOPE and report.get('donor') == donor_link()
        and report.get('application_id') == builder().APP_ID and report.get('version_name') == VERSION_NAME and report.get('version_code') == VERSION_CODE
        and report.get('abi') == 'arm64-v8a' and report.get('signer_certificate_sha256') == SIGNER and report.get('signing_key_created') is False
        and report.get('qualification') == q and report.get('qualification_receipt') == builder().file_pin(args.qualification)
        and report.get('native_client_render_pipeline') == q.get('native_client_render_pipeline') == native
        and q.get('client_gpu_runtime') == donor['client_gpu_runtime']
        and q.get('retained_native_client_renderer_attribution') == donor['native_client_renderer_attribution']
        and report.get('java_sources') == q.get('java_sources') == donor['java_sources'] and report.get('changed_java_sources') == []
        and report.get('retained_java_sources_verified') == 19 and report.get('retained_dex') == donor['recompiled_dex']
        and report.get('changed_apk_payloads') == sorted(REPLACED_PAYLOADS) and report.get('added_apk_payloads') == []
        and report.get('baseline_payloads_verified') == 77 and report.get('retained_baseline_payloads_verified') == 70
        and all(report.get(name) == donor[name] for name in RETAINED_FIELDS)
        and all(report.get(name) is False for name in FALSE_FLAGS)
        and all(report.get(name) is True for name in TRUE_FLAGS+('signature_verified', 'package_badging_verified', 'binary_manifest_version_only_verified', 'payload_bytes_verified')),
        'Exact retained .21 native continuation build receipt differs')
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


bounded_download = previous.bounded_download


def download_donor_evidence(args):
    """Fetch only the immutable evidence artifact; never rebuild an old probe."""
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh evidence directory required'); args.output.mkdir(parents=True)
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl): return None
    request = urllib.request.Request('https://api.github.com/repos/'+REPOSITORY+'/actions/artifacts/'+str(DONOR_EVIDENCE_ID)+'/zip',
        headers={'Authorization': 'Bearer '+os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json'})
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response: raise ValueError('Artifact API must redirect to immutable ZIP')
    except urllib.error.HTTPError as error:
        require(error.code == 302 and urllib.parse.urlparse(error.headers['Location']).scheme == 'https', 'Unexpected artifact redirect')
        location = error.headers['Location']
    target = args.output/DONOR_EVIDENCE_ARCHIVE; bounded_download(location, target, DONOR_EVIDENCE)
    members = donor_evidence_members(target)
    with zipfile.ZipFile(target) as archive:
        for name in sorted(members):
            destination = args.output/name; destination.write_bytes(archive.read(name)); builder().checked_file(destination, members[name])
    print('Authenticated original published .21 packaging evidence; driver and probes retained')
    print('Authenticated donor build-report pin:', json.dumps(members[DONOR_REPORT_NAME], sort_keys=True))


def publish_release(api, report, assets, notes):
    require(tuple(p.name for p in assets) == (APK_NAME, APK_NAME+'.sha256', NOTES_NAME), 'Unexpected release assets'); builder().checked_file(assets[0], report)
    for path in ('/releases/tags/'+RELEASE_TAG, '/git/ref/tags/'+RELEASE_TAG):
        try: existing = api.request(path)
        except urllib.error.HTTPError as error:
            if error.code != 404: raise
        else:
            require(not path.startswith('/releases/'), 'Existing release is never replaced')
            require(existing.get('object', {}).get('type') == 'commit' and existing['object'].get('sha') == report['repository_commit'], 'Existing tag points elsewhere')
    previous.old.require_current_release_head(api, report['repository_commit'])
    release = api.request('/releases', {'tag_name': RELEASE_TAG, 'target_commitish': report['repository_commit'],
        'name': 'COH Atlas Gameplay 0.13.22 — render worker wake repair and frame attribution',
        'body': notes+'\n\nAPK SHA-256: `'+report['sha256']+'`.\n[Hosted qualification](https://github.com/'+REPOSITORY+'/actions/runs/'+os.environ.get('GITHUB_RUN_ID', '')+').\n',
        'draft': True, 'prerelease': True, 'generate_release_notes': False, 'make_latest': 'false'}, method='POST')
    require(type(release.get('id')) is int and release.get('draft') is True and release.get('tag_name') == RELEASE_TAG, 'Unexpected draft release')
    for path in assets:
        uploaded = api.request('/releases/'+str(release['id'])+'/assets?'+urllib.parse.urlencode({'name': path.name}), path, method='POST', upload=True)
        expected = builder().file_pin(path)
        require(uploaded.get('state') == 'uploaded' and uploaded.get('name') == path.name and uploaded.get('size') == expected['bytes']
            and uploaded.get('digest') == 'sha256:'+expected['sha256'], 'Release upload differs')
    previous.old.require_current_release_head(api, report['repository_commit'])
    result = api.request('/releases/'+str(release['id']), {'draft': False, 'prerelease': True, 'make_latest': 'false'}, method='PATCH')
    require(result.get('id') == release['id'] and result.get('draft') is False and result.get('prerelease') is True and result.get('tag_name') == RELEASE_TAG, 'Publication incomplete')
    return result.get('html_url')


def publish(args):
    require(os.environ.get('GITHUB_REPOSITORY') == REPOSITORY and os.environ.get('GITHUB_REF') == 'refs/heads/'+BRANCH
        and os.environ.get('GITHUB_EVENT_NAME') in ('push', 'workflow_dispatch'), 'Publication requires continuation branch')
    commit = builder().source_commit(os.environ.get('GITHUB_SHA')); report, checksum, notes = verify_report(args, commit)
    api = module('client_render_pipeline_github', Path(__file__).with_name('build_atlas_gameplay_apk.py'))
    print('Published rendering continuation:', publish_release(api.GitHub(os.environ.get('GH_TOKEN')), report, (args.apk, checksum, notes), notes.read_text()))


def download_public(args):
    report = read_json(args.build_report); require(report.get('apk') == APK_NAME, 'Expected .22 public APK')
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
    command = commands.add_parser('download-public'); command.add_argument('--output', type=Path, required=True); command.add_argument('--build-report', type=Path, required=True)
    for name in ('build', 'audit', 'publish'):
        command = commands.add_parser(name)
        for value in ('donor-apk', 'donor-build-report', 'qualification', 'build-tools', 'client-directory'): command.add_argument('--'+value, type=Path, required=True)
        command.add_argument('--testing-notes', type=Path, default=NOTES); command.add_argument('--repository-commit', default=os.environ.get('GITHUB_SHA'))
        if name == 'build':
            command.add_argument('--android-jar', type=Path, required=True); command.add_argument('--keystore', type=Path, required=True)
            command.add_argument('--password-env', default='COH_INTERACTIVE_KEYSTORE_PASSWORD'); command.add_argument('--output', type=Path, required=True)
        else:
            command.add_argument('--apk', type=Path, required=True); command.add_argument('--build-report', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'download-donor': bounded_download(DONOR_URL, args.output, DONOR_APK)
    elif args.command == 'download-donor-evidence': download_donor_evidence(args)
    elif args.command == 'download-public': download_public(args)
    elif args.command == 'build': build(args)
    elif args.command == 'publish': publish(args)
    else: print('Fresh-process candidate verified:', verify_report(args, builder().source_commit(args.repository_commit))[0]['sha256'])


if __name__ == '__main__': main()
