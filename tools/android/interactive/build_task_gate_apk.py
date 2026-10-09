#!/usr/bin/env python3
"""Package the bounded task gate and animation pack from immutable public 0.12.1.

Retain every native, renderer, import, world, avatar and prepared client-cache
byte. Only the task observer/UI and server animation wrapper inputs change.
Actual animation-pack consumption by the retained stock MapServer is required.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
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
REPOSITORY, BRANCH = shared.REPOSITORY, shared.BRANCH
SIGNER = shared.SIGNER
DONOR_COMMIT = '1fcabfa28f1f32a8c78de2cac496d6647fd376a9'
DONOR_RUN_ID = 37116009802
DONOR_APK_NAME = 'COH-Atlas-Gameplay-0.12.1.apk'
DONOR_APK = {'bytes': 625055087, 'sha256': 'fee8880a53916e4ff746d67c8a6ab22f3f0cf2ab7779198cef59035ef4d6bf29'}
DONOR_BUILD = {'bytes': 182804, 'sha256': '39c6cf242b3ebcb69ca1e0ed6ab538dc8c5b7c43ac5871c555d158c4a1486340'}
DONOR_URL = 'https://github.com/'+REPOSITORY+'/releases/download/coh-atlas-gameplay-v0.12.1/'+DONOR_APK_NAME
VERSION_NAME, VERSION_CODE = '0.13.0', 15
APK_NAME = 'COH-Atlas-Gameplay-0.13.0.apk'
REPORT_NAME = 'task-gate-apk-build-report.json'
NOTES_NAME = 'COH-Atlas-Gameplay-0.13.0-testing.txt'
NOTES = ROOT/'docs'/NOTES_NAME
RELEASE_TAG = 'coh-atlas-gameplay-v0.13.0'
HELPERS = frozenset(('client_startup_diagnostic.py', 'character_reopen_diagnostic.py',
    'local_character_server.py', 'stationary_contact_evidence.py'))
GUEST_ADDITIONS = frozenset(('server_animation_package.py', 'task_gate_evidence.py'))
ANIMATION_ARCHIVE = 'server-animations.pigg'
ANIMATION_MANIFEST = 'server-animation-manifest.json'
ANIMATION_PAYLOADS = frozenset((ANIMATION_ARCHIVE, ANIMATION_MANIFEST))
GUEST_DATA_ADDITIONS = frozenset(('task-gate.json',))
ADDED_PAYLOADS = frozenset('assets/runtime/'+name for name in GUEST_ADDITIONS|GUEST_DATA_ADDITIONS|ANIMATION_PAYLOADS)
ALLOWED_PAYLOADS = frozenset('assets/runtime/'+name for name in HELPERS|{'client-manifest.json', 'runtime-manifest.json'})
REQUIRED_PAYLOADS = ALLOWED_PAYLOADS-{'assets/runtime/client_startup_diagnostic.py'}
JAVA_ROOT = shared.JAVA_ROOT
JAVA_CHANGES = frozenset(JAVA_ROOT+name+'.java' for name in
    ('ClientRuntime', 'ClientActivity', 'ClientService', 'ClientAcceptance', 'InteractiveRfbClient'))
QUALIFICATION_SCOPE = 'bounded_task_acceptance_completion_save_and_server_animation_pack'
CHECKS = ('task_identity_completion_and_save_guards_verified',
    'owned_command_delivery_and_capture_bounds_verified',
    'retained_contact_input_recovery_and_persistence_guards_verified',
    'animation_layout_fallback_and_native_proof_rejection_verified',
    'retained_native_payload_and_actual_extraction_verified')
WORKFLOW = '.github/workflows/android-task-gate.yml'
QUALIFICATION_SCRIPT = 'tools/android/interactive/qualify_task_gate.py'
SOURCE_FILES = frozenset((WORKFLOW, QUALIFICATION_SCRIPT,
    'tools/android/interactive/build_task_gate_apk.py',
    'tools/android/interactive/test_task_gate_package.py',
    'tools/android/atlasgame/prepare_server_animations.py',
    'tools/android/atlasgame/test_server_animations.py',
    'tools/android/interactive/test_task_gate_evidence.py',
    'tools/android/interactive/test_task_gate_native_contract.py',
    'tools/android/interactive/test_task_gate_integration.py',
    'tools/android/interactive/test_task_gate_java.py',
    'tools/android/interactive/test_character_logout_position.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'tools/android/interactive/fixtures/thor-contact-save-0.12.1-20261003.log',
    'tools/android/interactive/build_responsiveness_apk.py', 'tools/android/interactive/build_apk.py',
    'tools/android/interactive/build_atlas_gameplay_apk.py', 'android/interactive/src/main/AndroidManifest.xml',
    'docs/'+NOTES_NAME, *(('android/guest/'+name) for name in HELPERS|GUEST_ADDITIONS|GUEST_DATA_ADDITIONS), *JAVA_CHANGES))
require, module, read_json = shared.require, shared.module, shared.read_json
verify_server_archives, verify_apk_server_archives = shared.verify_server_archives, shared.verify_apk_server_archives


def builder(*, repaired=False):
    base = module('task_gate_android_builder', Path(__file__).with_name('build_apk.py'))
    if repaired: base.VERSION_NAME, base.VERSION_CODE, base.APK_NAME = VERSION_NAME, VERSION_CODE, APK_NAME
    return base


def donor_link():
    return {'run_id': DONOR_RUN_ID, 'repository_commit': DONOR_COMMIT, 'apk': DONOR_APK, 'build_report': DONOR_BUILD}


def validate_donor_receipt(path):
    builder().checked_file(path, DONOR_BUILD)
    donor = read_json(path)
    require(donor.get('format') == 1 and donor.get('repository_commit') == DONOR_COMMIT
        and donor.get('apk') == DONOR_APK_NAME and {key: donor.get(key) for key in DONOR_APK} == DONOR_APK
        and donor.get('application_id') == builder().APP_ID and donor.get('version_name') == '0.12.1'
        and donor.get('version_code') == 14 and donor.get('abi') == 'arm64-v8a'
        and donor.get('signer_certificate_sha256') == SIGNER and donor.get('signing_key_created') is False
        and all(donor.get(key) is True for key in ('signature_verified', 'package_badging_verified', 'payload_bytes_verified'))
        and len(donor.get('payloads', {})) == 60 and len(donor.get('java_sources', {})) == 16
        and donor.get('server_payload_extraction_preflight', {}).get('status') == 'passed'
        and donor.get('qualification', {}).get('scope') == 'exact_server_caches_stable_data_identity_and_runtime_mtime'
        and donor['qualification'].get('status') == 'passed'
        and donor['qualification'].get('repository_commit') == DONOR_COMMIT,
        'Exact public 0.12.1 retained-signer donor receipt differs')
    return donor


def validate_donor(apk, receipt):
    base = builder(); base.checked_file(apk, DONOR_APK)
    donor = validate_donor_receipt(receipt)
    base.verify_packaged_payloads(apk, donor['payloads'])
    with zipfile.ZipFile(apk) as archive:
        retained = {'classes.dex': donor['recompiled_dex'], **donor['retained_android_resources']}
        require({name for name in archive.namelist() if not name.startswith('META-INF/')} ==
            set(donor['payloads'])|set(retained)|{'AndroidManifest.xml'}, 'Unexpected donor APK inventory')
        for name, pin in retained.items():
            raw = archive.read(name)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == pin,
                    'Donor Android shell differs: '+name)
        require(json.loads(archive.read('assets/runtime/native-responsiveness.json')) == donor['native_responsiveness'],
                'Donor native provenance differs')
    require(verify_apk_server_archives(apk) == donor['server_payload_extraction_preflight'],
            'Exact public donor does not pass actual guest extraction')
    return donor


def current_java_sources(donor, generated):
    base = builder(); sources = base.java_sources(ROOT/'android/interactive/src/main', generated)
    pins = {path.relative_to(ROOT).as_posix(): base.file_pin(path) for path in sources
            if path.is_relative_to(ROOT) and not path.is_relative_to(generated)}
    require(set(pins) == set(donor['java_sources']), 'Authored Java inventory changed unexpectedly')
    changed = {name for name in pins if pins[name] != donor['java_sources'][name]}
    require(changed == JAVA_CHANGES, 'Java changes exceed the bounded task UI and command sender')
    for name, pin in donor['preserved_sources'].items():
        if name not in JAVA_CHANGES: base.checked_file(ROOT/name, pin)
    base.checked_file(ROOT/'android/interactive/src/main/AndroidManifest.xml', donor['source_manifest'])
    return sources, pins, sorted(changed)


def validate_qualification(receipt, commit):
    require(receipt.get('format') == 1 and receipt.get('status') == 'passed'
        and receipt.get('scope') == QUALIFICATION_SCOPE and receipt.get('repository_commit') == commit
        and receipt.get('donor_apk_sha256') == DONOR_APK['sha256']
        and receipt.get('physical_gameplay_validated') is False and receipt.get('native_runtime_booted') is False
        and receipt.get('dialog_semantics_validated') is False and receipt.get('native_client_or_server_recompiled') is False
        and receipt.get('physical_startup_timing_validated') is False and receipt.get('long_prior_gameplay_milestones_repeated') is False
        and type(receipt.get('tests_run')) is int and receipt['tests_run'] >= 50
        and set(receipt.get('checks', {})) == set(CHECKS) and all(receipt['checks'].values()),
        'Exact focused task-gate qualification is required')
    require(SOURCE_FILES <= set(receipt.get('source_files', {})), 'Qualification source closure incomplete')
    for name, pin in receipt['source_files'].items():
        require(isinstance(name, str) and not Path(name).is_absolute() and '..' not in Path(name).parts
                and '\\' not in name, 'Unsafe qualification source path')
        builder().checked_file(ROOT/name, pin)
    return receipt


def validate_animation_pack(directory, commit=None):
    directory = Path(directory)
    require(directory.is_dir() and not directory.is_symlink(), 'Verified animation-pack directory required')
    native = module('task_native_server_animation_qualification',
        ROOT/'tools/android/atlasgame/prepare_server_animations.py')
    # The producer validates actual retained-MapServer consumption, normal exits,
    # source/data identity and immutable cold/warm evidence, not just a PIG envelope.
    manifest = native.verify_generated_package(directory)
    require(manifest == read_json(directory/ANIMATION_MANIFEST),
            'Animation native proof and packaged manifest differ')
    if commit is not None:
        require(manifest.get('repository_commit') == commit, 'Animation pack source commit differs')
    return manifest


def extract_and_repair(apk, donor, destination, commit, server_animations):
    base = builder(); destination.mkdir(parents=True)
    retained = {}
    with zipfile.ZipFile(apk) as archive:
        for entry in archive.infolist():
            name = entry.filename
            if name == 'AndroidManifest.xml' or name.startswith('META-INF/'): continue
            require((name in donor['payloads'] or name in ('classes.dex', 'resources.arsc', 'res/drawable/ic_coh_client.xml'))
                and not stat.S_ISLNK(entry.external_attr >> 16), 'Unexpected donor APK entry')
            target = destination/name; target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open('xb') as output: shutil.copyfileobj(source, output, 64*1024)
            retained[name] = base.file_pin(target)
    require(all(retained.get(name) == pin for name, pin in donor['payloads'].items()), 'Extracted donor bytes differ')
    assets = destination/'assets/runtime'
    runtime, client = read_json(assets/'runtime-manifest.json'), read_json(assets/'client-manifest.json')
    require(runtime == donor['runtime_manifest'], 'Donor runtime verification manifest differs')
    for name, pin in donor['payloads'].items():
        if name.startswith('assets/runtime/') and name.endswith('.py') and Path(name).name not in HELPERS:
            base.checked_file(ROOT/'android/guest'/Path(name).name, pin)
    for name in HELPERS|GUEST_ADDITIONS|GUEST_DATA_ADDITIONS:
        source = ROOT/'android/guest'/name; base.checked_file(source)
        require(source.stat().st_size <= (32768 if name in GUEST_DATA_ADDITIONS else 1024*1024), 'Unbounded guest helper/config')
        if name in GUEST_ADDITIONS|GUEST_DATA_ADDITIONS: require(not (assets/name).exists(), 'New guest helper collides with donor')
        shutil.copyfile(source, assets/name)
    animation_manifest = validate_animation_pack(server_animations, commit)
    for name in ANIMATION_PAYLOADS:
        require(not (assets/name).exists(), 'New animation payload collides with donor')
        shutil.copyfile(server_animations/name, assets/name)
    updates = {name: base.file_pin(assets/name) for name in HELPERS|GUEST_ADDITIONS|GUEST_DATA_ADDITIONS|ANIMATION_PAYLOADS}
    client['files'].update(updates); (assets/'client-manifest.json').write_bytes(shared.encoded(client))
    runtime['files'].update(updates); runtime['files']['client-manifest.json'] = base.file_pin(assets/'client-manifest.json')
    runtime['repository_commit'] = commit
    runtime['task_gate_required'] = True
    runtime['scope'] = 'Bounded native task accept/forced-success command/save evidence and exact stock server animation pack; prior milestones retained; physical task and timing pending'
    (assets/'runtime-manifest.json').write_bytes(shared.encoded(runtime))
    preflight = verify_server_archives(assets)
    payloads = {name: base.file_pin(destination/name) for name in set(donor['payloads'])|ADDED_PAYLOADS}
    changed = {name for name in donor['payloads'] if payloads[name] != donor['payloads'][name]}
    require(REQUIRED_PAYLOADS <= changed <= ALLOWED_PAYLOADS, 'Source-only derivative changed unexpected payloads or missed required helper updates')
    return runtime, payloads, retained, preflight


def repair_android_manifest(source, destination):
    base = builder(); base.verify_source_manifest(source)
    tree = ET.parse(source); manifest = tree.getroot()
    manifest.set(base.ANDROID+'versionName', VERSION_NAME); manifest.set(base.ANDROID+'versionCode', str(VERSION_CODE))
    ET.register_namespace('android', base.ANDROID[1:-1]); tree.write(destination, encoding='utf-8', xml_declaration=True)
    builder(repaired=True).verify_source_manifest(destination)


def verify_derivative(apk, donor, payloads, dex_pin):
    require(set(payloads) == set(donor['payloads'])|ADDED_PAYLOADS
        and REQUIRED_PAYLOADS <= {name for name in donor['payloads'] if payloads[name] != donor['payloads'][name]} <= ALLOWED_PAYLOADS,
        'Candidate source-only payload boundaries differ')
    builder().verify_packaged_payloads(apk, payloads)
    with zipfile.ZipFile(apk) as archive:
        require({name for name in archive.namelist() if not name.startswith('META-INF/')} ==
            set(payloads)|set(donor['retained_android_resources'])|{'AndroidManifest.xml', 'classes.dex'},
            'Unexpected candidate APK member')
        for name, pin in {'classes.dex': dex_pin, **donor['retained_android_resources']}.items():
            raw = archive.read(name)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == pin, 'Retained Android shell differs')
        require(json.loads(archive.read('assets/runtime/native-responsiveness.json')) == donor['native_responsiveness'],
                'Source-only derivative relabelled retained native history')


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
    validate_animation_pack(args.server_animations, commit)
    password = base.signing_password_spec(args.password_env)
    base.verify_signing_identity(args.keystore, 'coh-client-interactive', SIGNER, password)
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), 'Fresh task-gate APK required')
    base.checked_file(args.testing_notes); require(0 < args.testing_notes.stat().st_size <= 65536, 'Bounded testing notes required')
    for tool in (args.android_jar, args.build_tools/'aapt2', args.build_tools/'zipalign', args.build_tools/'lib/d8.jar', args.build_tools/'lib/apksigner.jar'):
        require(tool.is_file() and not tool.is_symlink(), 'Required Android tool missing')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-task-', dir=args.output.parent) as temporary:
        work = Path(temporary)
        runtime, payloads, retained, preflight = extract_and_repair(args.donor_apk, donor, work/'donor', commit, args.server_animations)
        classes, generated, dex = (work/name for name in ('classes', 'generated', 'dex'))
        for folder in (classes, generated, dex): folder.mkdir()
        current_java_sources(donor, generated)
        manifest = work/'AndroidManifest.xml'; repair_android_manifest(ROOT/'android/interactive/src/main/AndroidManifest.xml', manifest)
        resources, unsigned, aligned, signed = (work/name for name in ('resources.zip', 'unsigned.apk', 'aligned.apk', 'signed.apk'))
        base.run(args.build_tools/'aapt2', 'compile', '--dir', ROOT/'android/interactive/src/main/res', '-o', resources)
        base.run(args.build_tools/'aapt2', 'link', '-I', args.android_jar, '--manifest', manifest, '--min-sdk-version', '26', '--target-sdk-version', '35', '--java', generated, resources, '-o', unsigned)
        with zipfile.ZipFile(unsigned) as archive:
            require(set(archive.namelist()) == {'AndroidManifest.xml', 'resources.arsc', 'res/drawable/ic_coh_client.xml'}, 'Generated Android resource inventory differs')
            for name in donor['retained_android_resources']:
                data = archive.read(name)
                require({'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} == retained[name], 'Android resources changed beyond version metadata')
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
            base.append_payloads(archive, [(work/'donor'/name, name) for name in sorted(payloads)]); archive.write(dex/'classes.dex', 'classes.dex')
        base.run(args.build_tools/'zipalign', '-f', '4', unsigned, aligned)
        base.run('java', '-jar', args.build_tools/'lib/apksigner.jar', 'sign', '--ks', args.keystore, '--ks-key-alias', 'coh-client-interactive', '--ks-pass', password, '--key-pass', password, '--out', signed, aligned)
        certificate = base.verify_signer_output(base.run('java', '-jar', args.build_tools/'lib/apksigner.jar', 'verify', '--verbose', '--print-certs', signed), SIGNER)
        base.run(args.build_tools/'zipalign', '-c', '4', signed); current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', signed))
        verify_derivative(signed, donor, payloads, dex_pin)
        require(verify_apk_server_archives(signed) == preflight, 'Signed task-gate APK server extraction differs')
        shutil.copyfile(signed, args.output)
        report = {'format': 1, 'apk': APK_NAME, **base.file_pin(args.output), 'repository_commit': commit,
            'application_id': base.APP_ID, 'version_name': VERSION_NAME, 'version_code': VERSION_CODE, 'abi': 'arm64-v8a',
            'signer_certificate_sha256': certificate, 'signing_key_created': False, 'signature_verified': True,
            'package_badging_verified': True, 'payload_bytes_verified': True, 'runtime_manifest': runtime,
            'runtime_manifest_sha256': payloads['assets/runtime/runtime-manifest.json']['sha256'], 'payloads': payloads,
            'changed_apk_payloads': sorted({name for name in donor['payloads'] if payloads[name] != donor['payloads'][name]}|ADDED_PAYLOADS),
            'replaced_apk_payloads': sorted(name for name in donor['payloads'] if payloads[name] != donor['payloads'][name]),
            'added_apk_payloads': sorted(ADDED_PAYLOADS), 'recompiled_dex': dex_pin, 'donor_dex': donor['recompiled_dex'],
            'retained_android_resources': donor['retained_android_resources'], 'donor': donor_link(),
            'java_sources': source_pins, 'changed_java_sources': changed_java, 'added_java_sources': [],
            'preserved_sources': {name: pin for name, pin in donor['preserved_sources'].items() if name not in JAVA_CHANGES},
            'source_manifest': donor['source_manifest'], 'generated_manifest': base.file_pin(manifest),
            'qualification': qualification, 'qualification_receipt': base.file_pin(args.qualification),
            'native_responsiveness': donor['native_responsiveness'], 'native_package_receipt': donor['native_package_receipt'],
            'native_launcher': donor['native_launcher'], 'server_animation_manifest': validate_animation_pack(args.server_animations, commit),
            'prepared_server_animations_added': True, 'server_cache_manifest': donor['server_cache_manifest'],
            'retained_server_cache_archive': donor['payloads']['assets/runtime/server-caches.zip'],
            'runtime_timestamps': donor['runtime_timestamps'],
            'runtime_timestamps_receipt': donor['runtime_timestamps_receipt'], 'testing_notes': base.file_pin(args.testing_notes),
            'native_libraries_changed': False, 'client_or_server_recompiled': False, 'java_or_dex_recompiled': True,
            'world_assets_changed': False, 'prepared_cache_archive_changed': False, 'dbserver_changed': False,
            'graphics_driver_changed': False, 'physical_gameplay_validated': False, 'dialog_semantics_validated': False,
            'server_payload_extraction_preflight': preflight,
            'scope': 'Native task acceptance, command-assisted completion and normal save observer; qualified stock animation pack; unchanged server/client/driver/native and exact 93 caches; physical task and startup timing pending'}
        (args.output.parent/REPORT_NAME).write_text(json.dumps(report, indent=2)+'\n')
        args.output.with_suffix('.apk.sha256').write_text(report['sha256']+'  '+APK_NAME+'\n')
        shutil.copyfile(args.testing_notes, args.output.parent/NOTES_NAME)
        print('Built retained-native task-gate candidate', report['sha256'])


def publish_release(api, report, assets, notes):
    require(tuple(path.name for path in assets) == (APK_NAME, APK_NAME+'.sha256', NOTES_NAME),
            'Unexpected task-gate release assets')
    builder().checked_file(assets[0], report)
    for path in ('/releases/tags/'+RELEASE_TAG, '/git/ref/tags/'+RELEASE_TAG):
        try: existing = api.request(path)
        except urllib.error.HTTPError as error:
            if error.code != 404: raise
        else:
            require(not path.startswith('/releases/'), 'Existing task-gate release is never replaced')
            require(existing.get('object', {}).get('type') == 'commit'
                and existing['object'].get('sha') == report['repository_commit'], 'Existing tag points elsewhere')
    body = notes+'\n\nAPK SHA-256: `'+report['sha256']+'`.\n'
    body += '[Focused task, animation-pack consumption and retained persistence qualification](https://github.com/'+REPOSITORY+'/actions/runs/'+os.environ.get('GITHUB_RUN_ID', '')+').\n'
    release = api.request('/releases', {'tag_name': RELEASE_TAG, 'target_commitish': report['repository_commit'],
        'name': 'COH Atlas Gameplay 0.13.0 — bounded task gate and server animation pack',
        'body': body, 'draft': True, 'prerelease': True, 'generate_release_notes': False, 'make_latest': 'false'}, method='POST')
    require(type(release.get('id')) is int and release.get('draft') is True and release.get('prerelease') is True
        and release.get('tag_name') == RELEASE_TAG, 'Unexpected created task-gate release')
    for path in assets:
        uploaded = api.request('/releases/'+str(release['id'])+'/assets?'+urllib.parse.urlencode({'name': path.name}),
                               path, method='POST', upload=True)
        pin = builder().file_pin(path)
        require(uploaded.get('state') == 'uploaded' and uploaded.get('name') == path.name
            and uploaded.get('size') == pin['bytes'] and uploaded.get('digest') == 'sha256:'+pin['sha256'],
            'Task-gate release upload differs')
    published = api.request('/releases/'+str(release['id']), {'draft': False, 'prerelease': True, 'make_latest': 'false'}, method='PATCH')
    require(published.get('id') == release['id'] and published.get('draft') is False
        and published.get('prerelease') is True and published.get('tag_name') == RELEASE_TAG,
        'Task-gate publication did not complete')
    return published.get('html_url')


def publish(args):
    base, current = builder(), builder(repaired=True)
    require(os.environ.get('GITHUB_REPOSITORY') == REPOSITORY and os.environ.get('GITHUB_REF') == 'refs/heads/'+BRANCH
        and os.environ.get('GITHUB_EVENT_NAME') in ('push', 'workflow_dispatch'), 'Publication requires authorized continuation branch')
    commit = base.source_commit(os.environ.get('GITHUB_SHA'))
    report = read_json(args.build_report); donor = validate_donor(args.donor_apk, args.donor_build_report)
    animation_manifest = validate_animation_pack(args.server_animations, commit)
    qualification = validate_qualification(read_json(args.qualification), commit)
    with tempfile.TemporaryDirectory(prefix='coh-task-source-') as temporary:
        _, sources, changes = current_java_sources(donor, Path(temporary))
    require(report.get('format') == 1 and report.get('apk') == APK_NAME and report.get('repository_commit') == commit
        and report.get('application_id') == base.APP_ID and report.get('version_name') == VERSION_NAME
        and report.get('version_code') == VERSION_CODE and report.get('signer_certificate_sha256') == SIGNER
        and report.get('signing_key_created') is False and report.get('donor') == donor_link()
        and report.get('runtime_timestamps') == donor['runtime_timestamps']
        and report.get('runtime_timestamps_receipt') == donor['runtime_timestamps_receipt']
        and report.get('qualification') == qualification and report.get('qualification_receipt') == base.file_pin(args.qualification)
        and report.get('java_sources') == sources and report.get('changed_java_sources') == changes and report.get('added_java_sources') == []
        and all(report.get(key) is True for key in ('signature_verified', 'package_badging_verified', 'payload_bytes_verified', 'java_or_dex_recompiled'))
        and all(report.get(key) is False for key in ('native_libraries_changed', 'client_or_server_recompiled', 'world_assets_changed',
            'prepared_cache_archive_changed', 'dbserver_changed', 'graphics_driver_changed', 'physical_gameplay_validated', 'dialog_semantics_validated'))
        and report.get('server_animation_manifest') == animation_manifest and report.get('prepared_server_animations_added') is True
        and report.get('server_cache_manifest') == donor['server_cache_manifest']
        and report.get('retained_server_cache_archive') == donor['payloads']['assets/runtime/server-caches.zip']
        and report.get('native_responsiveness') == donor['native_responsiveness']
        and report.get('native_package_receipt') == donor['native_package_receipt'] and report.get('native_launcher') == donor['native_launcher'],
        'Task-gate build receipt differs')
    base.checked_file(args.apk, report); verify_derivative(args.apk, donor, report['payloads'], report['recompiled_dex'])
    for name in HELPERS|GUEST_ADDITIONS|GUEST_DATA_ADDITIONS:
        require(report['payloads']['assets/runtime/'+name] == base.file_pin(ROOT/'android/guest'/name), 'Packaged qualified guest helper differs')
    for name in ANIMATION_PAYLOADS:
        require(report['payloads']['assets/runtime/'+name] == base.file_pin(args.server_animations/name), 'Published animation payload differs')
    require(verify_apk_server_archives(args.apk) == report['server_payload_extraction_preflight'], 'Published task-gate APK fails real guest extraction')
    with zipfile.ZipFile(args.apk) as archive:
        runtime = json.loads(archive.read('assets/runtime/runtime-manifest.json'))
        client = json.loads(archive.read('assets/runtime/client-manifest.json'))
        require(runtime == report['runtime_manifest'] and runtime.get('task_gate_required') is True and runtime['accepted_base_runtime'] == donor['runtime_manifest']['accepted_base_runtime']
            and all(runtime['files'].get(name) == pin for name, pin in client['files'].items()), 'Runtime verification manifests differ')
    base.verify_signer_output(base.run('java', '-jar', args.build_tools/'lib/apksigner.jar', 'verify', '--verbose', '--print-certs', args.apk), SIGNER)
    current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', args.apk))
    checksum = args.apk.with_suffix('.apk.sha256'); require(checksum.read_text() == report['sha256']+'  '+APK_NAME+'\n', 'Published checksum differs')
    public_notes = args.apk.parent/NOTES_NAME; base.checked_file(public_notes, report['testing_notes']); base.checked_file(args.testing_notes, report['testing_notes'])
    api = module('contact_interaction_github', Path(__file__).with_name('build_atlas_gameplay_apk.py'))
    print('Published task-gate prerelease:', publish_release(api.GitHub(os.environ.get('GH_TOKEN')), report,
        (args.apk, checksum, public_notes), public_notes.read_text()))


def main():
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest='command', required=True)
    get = commands.add_parser('download-donor'); get.add_argument('--output', type=Path, required=True)
    create = commands.add_parser('build')
    for name in ('donor-apk', 'donor-build-report', 'qualification', 'android-jar', 'build-tools', 'keystore', 'output', 'server-animations'):
        create.add_argument('--'+name, type=Path, required=True)
    create.add_argument('--repository-commit'); create.add_argument('--password-env', default='COH_INTERACTIVE_KEYSTORE_PASSWORD')
    create.add_argument('--testing-notes', type=Path, default=NOTES)
    release = commands.add_parser('publish')
    for name in ('apk', 'build-report', 'build-tools', 'qualification', 'donor-build-report', 'donor-apk', 'server-animations'):
        release.add_argument('--'+name, type=Path, required=True)
    release.add_argument('--testing-notes', type=Path, default=NOTES)
    args = parser.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path): setattr(args, key, value.absolute())
    {'download-donor': download, 'build': build, 'publish': publish}[args.command](args)


if __name__ == '__main__': main()
