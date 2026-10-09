#!/usr/bin/env python3
"""Package qualified startup reuse from the exact published 0.12.0 APK.

Retain every native, renderer, import, world, avatar and prepared client-cache
byte. Only bounded guest reuse/cache helpers and trusted tar mtime extraction
change. Native server-cache generation and consumption are separately required.
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
DONOR_COMMIT = '1791a3203ecf662191f2d6e3401cfa9ea4692004'
DONOR_RUN_ID = 37071344940
DONOR_APK_NAME = 'COH-Atlas-Gameplay-0.12.0.apk'
DONOR_APK = {'bytes': 595203099, 'sha256': '4a507d7d59b3af07be74de4bf47e39b8fd09ac86266a34c4fefd756fb442ee7c'}
DONOR_BUILD = {'bytes': 103482, 'sha256': 'bb5cb7237fd1f489a53df5fe081398dcedde49f8d21ed7e9d27bb6417f21de07'}
DONOR_URL = 'https://github.com/'+REPOSITORY+'/releases/download/coh-atlas-gameplay-v0.12.0/'+DONOR_APK_NAME
VERSION_NAME, VERSION_CODE = '0.12.1', 14
APK_NAME = 'COH-Atlas-Gameplay-0.12.1.apk'
REPORT_NAME = 'startup-caches-apk-build-report.json'
NOTES_NAME = 'COH-Atlas-Gameplay-0.12.1-testing.txt'
NOTES = ROOT/'docs'/NOTES_NAME
RELEASE_TAG = 'coh-atlas-gameplay-v0.12.1'
HELPERS = frozenset(('client_startup_diagnostic.py', 'character_server_data_cache.py', 'local_character_server.py', 'texture_header_index.py'))
GUEST_ADDITIONS = frozenset(('server_cache_package.py', 'server_message_cache_format.py'))
CACHE_ARCHIVE = 'server-caches.zip'
CACHE_MANIFEST = 'server-cache-manifest.json'
CACHE_PAYLOADS = frozenset((CACHE_ARCHIVE, CACHE_MANIFEST))
ADDED_PAYLOADS = frozenset('assets/runtime/'+name for name in GUEST_ADDITIONS|CACHE_PAYLOADS)
ALLOWED_PAYLOADS = frozenset('assets/runtime/'+name for name in HELPERS|{'client-manifest.json', 'runtime-manifest.json'})
REQUIRED_PAYLOADS = ALLOWED_PAYLOADS
JAVA_ROOT = shared.JAVA_ROOT
JAVA_CHANGES = frozenset(('android/app/src/main/java/io/github/russianranger/cohdiagnostic/TarExtractor.java',))
QUALIFICATION_SCOPE = 'exact_server_caches_stable_data_identity_and_runtime_mtime'
CHECKS = ('stable_data_and_private_cache_reuse_verified', 'server_cache_validation_and_fallback_verified',
          'trusted_archive_mtime_and_genuine_wine_refresh_verified', 'contact_save_persistence_and_input_guards_verified',
          'retained_native_payload_and_actual_extraction_verified')
WORKFLOW = '.github/workflows/android-startup-caches.yml'
QUALIFICATION_SCRIPT = 'tools/android/interactive/qualify_startup_caches.py'
SOURCE_FILES = frozenset((WORKFLOW, QUALIFICATION_SCRIPT,
    'tools/android/interactive/build_startup_caches_apk.py',
    'tools/android/interactive/test_startup_caches_package.py',
    'tools/android/atlasgame/prepare_server_caches.py',
    'tools/android/atlasgame/server_message_source_contract.py',
    'tools/android/atlasgame/test_server_message_source_contract.py',
    'android/native/server-cache-launcher.c',
    'tools/android/interactive/qualify_runtime_timestamps.py',
    'tools/android/interactive/test_server_cache_package.py',
    'tools/android/interactive/test_server_message_cache_format.py',
    'tools/android/interactive/test_startup_cache_integration.py',
    'tools/android/interactive/test_contact_capture.py',
    'tools/android/interactive/test_stationary_contact_evidence.py',
    'tools/android/interactive/build_responsiveness_apk.py', 'tools/android/interactive/build_apk.py',
    'tools/android/interactive/build_atlas_gameplay_apk.py',
    '.github/workflows/android-client-startup.yml', '.github/workflows/android-client-interactive.yml', 'android/interactive/src/main/AndroidManifest.xml',
    'docs/'+NOTES_NAME, *(('android/guest/'+name) for name in HELPERS|GUEST_ADDITIONS), *JAVA_CHANGES))
require, module, read_json = shared.require, shared.module, shared.read_json
verify_server_archives, verify_apk_server_archives = shared.verify_server_archives, shared.verify_apk_server_archives


def builder(*, repaired=False):
    base = module('contact_interaction_android_builder', Path(__file__).with_name('build_apk.py'))
    if repaired: base.VERSION_NAME, base.VERSION_CODE, base.APK_NAME = VERSION_NAME, VERSION_CODE, APK_NAME
    return base


def donor_link():
    return {'run_id': DONOR_RUN_ID, 'repository_commit': DONOR_COMMIT, 'apk': DONOR_APK, 'build_report': DONOR_BUILD}


def validate_donor_receipt(path):
    builder().checked_file(path, DONOR_BUILD)
    donor = read_json(path)
    require(donor.get('format') == 1 and donor.get('repository_commit') == DONOR_COMMIT
        and donor.get('apk') == DONOR_APK_NAME and {key: donor.get(key) for key in DONOR_APK} == DONOR_APK
        and donor.get('application_id') == builder().APP_ID and donor.get('version_name') == '0.12.0'
        and donor.get('version_code') == 13 and donor.get('abi') == 'arm64-v8a'
        and donor.get('signer_certificate_sha256') == SIGNER and donor.get('signing_key_created') is False
        and all(donor.get(key) is True for key in ('signature_verified', 'package_badging_verified', 'payload_bytes_verified'))
        and len(donor.get('payloads', {})) == 56 and len(donor.get('java_sources', {})) == 16
        and donor.get('server_payload_extraction_preflight', {}).get('status') == 'passed'
        and donor.get('qualification', {}).get('scope') == 'optional_ground_recovery_and_stationary_contact_evidence'
        and donor['qualification'].get('status') == 'passed'
        and donor['qualification'].get('repository_commit') == DONOR_COMMIT,
        'Exact public 0.12.0 retained-signer donor receipt differs')
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
    require(changed == JAVA_CHANGES, 'Java changes exceed the trusted runtime timestamp extraction')
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
        'Exact focused startup-cache qualification is required')
    require(SOURCE_FILES <= set(receipt.get('source_files', {})), 'Qualification source closure incomplete')
    for name, pin in receipt['source_files'].items():
        require(isinstance(name, str) and not Path(name).is_absolute() and '..' not in Path(name).parts
                and '\\' not in name, 'Unsafe qualification source path')
        builder().checked_file(ROOT/name, pin)
    return receipt


def validate_runtime_timestamps(receipt, commit):
    verifier = module('startup_runtime_timestamps', Path(__file__).with_name('qualify_runtime_timestamps.py'))
    return verifier.validate_receipt(receipt, commit)


def validate_server_caches(directory):
    directory = Path(directory)
    require(directory.is_dir() and not directory.is_symlink(), 'Verified server cache directory required')
    native = module('startup_native_server_cache_generation', ROOT/'tools/android/atlasgame/prepare_server_caches.py')
    native_manifest = native.verify_generated_package(directory)
    verifier = module('startup_server_cache_package', ROOT/'android/guest/server_cache_package.py')
    manifest = verifier.verify_archive(directory/CACHE_ARCHIVE)
    require(manifest == native_manifest and manifest == read_json(directory/CACHE_MANIFEST), 'Server cache embedded/external manifests differ')
    # Generation and consumption are genuine unchanged-MapServer proofs, never
    # inferred from serializer envelope checks or process launch alone.
    require(manifest.get('native_consumption', {}).get('cache_files_unchanged') is True
        and manifest.get('native_generation', {}).get('native_errors', {}).get('status') == 'no_native_data_errors',
        'Server cache native generation/consumption qualification is incomplete')
    return manifest


def extract_and_repair(apk, donor, destination, commit, server_caches):
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
    for name in HELPERS|GUEST_ADDITIONS:
        source = ROOT/'android/guest'/name; base.checked_file(source)
        require(source.stat().st_size <= 1024*1024, 'Unbounded guest helper')
        if name in GUEST_ADDITIONS: require(not (assets/name).exists(), 'New guest helper collides with donor')
        shutil.copyfile(source, assets/name)
    cache_manifest = validate_server_caches(server_caches)
    for name in CACHE_PAYLOADS:
        require(not (assets/name).exists(), 'New server cache payload collides with donor')
        shutil.copyfile(server_caches/name, assets/name)
    updates = {name: base.file_pin(assets/name) for name in HELPERS|GUEST_ADDITIONS|CACHE_PAYLOADS}
    client['files'].update(updates); (assets/'client-manifest.json').write_bytes(shared.encoded(client))
    runtime['files'].update(updates); runtime['files']['client-manifest.json'] = base.file_pin(assets/'client-manifest.json')
    runtime['repository_commit'] = commit
    runtime['scope'] = 'Exact native server/message caches, stable data reuse and trusted runtime timestamps; retained optional recovery/contact capture; physical startup and dialogue pending'
    (assets/'runtime-manifest.json').write_bytes(shared.encoded(runtime))
    preflight = verify_server_archives(assets)
    payloads = {name: base.file_pin(destination/name) for name in set(donor['payloads'])|ADDED_PAYLOADS}
    changed = {name for name in donor['payloads'] if payloads[name] != donor['payloads'][name]}
    require(changed == REQUIRED_PAYLOADS, 'Source-only derivative changed unexpected payloads or missed required helper updates')
    return runtime, payloads, retained, preflight


def repair_android_manifest(source, destination):
    base = builder(); base.verify_source_manifest(source)
    tree = ET.parse(source); manifest = tree.getroot()
    manifest.set(base.ANDROID+'versionName', VERSION_NAME); manifest.set(base.ANDROID+'versionCode', str(VERSION_CODE))
    ET.register_namespace('android', base.ANDROID[1:-1]); tree.write(destination, encoding='utf-8', xml_declaration=True)
    builder(repaired=True).verify_source_manifest(destination)


def verify_derivative(apk, donor, payloads, dex_pin):
    require(set(payloads) == set(donor['payloads'])|ADDED_PAYLOADS
        and {name for name in donor['payloads'] if payloads[name] != donor['payloads'][name]} == REQUIRED_PAYLOADS,
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
    runtime_timestamps = validate_runtime_timestamps(read_json(args.runtime_timestamps), commit)
    password = base.signing_password_spec(args.password_env)
    base.verify_signing_identity(args.keystore, 'coh-client-interactive', SIGNER, password)
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), 'Fresh startup-cache APK required')
    base.checked_file(args.testing_notes); require(0 < args.testing_notes.stat().st_size <= 65536, 'Bounded testing notes required')
    for tool in (args.android_jar, args.build_tools/'aapt2', args.build_tools/'zipalign', args.build_tools/'lib/d8.jar', args.build_tools/'lib/apksigner.jar'):
        require(tool.is_file() and not tool.is_symlink(), 'Required Android tool missing')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-contact-', dir=args.output.parent) as temporary:
        work = Path(temporary)
        runtime, payloads, retained, preflight = extract_and_repair(args.donor_apk, donor, work/'donor', commit, args.server_caches)
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
        require(verify_apk_server_archives(signed) == preflight, 'Signed startup-cache APK server extraction differs')
        shutil.copyfile(signed, args.output)
        report = {'format': 1, 'apk': APK_NAME, **base.file_pin(args.output), 'repository_commit': commit,
            'application_id': base.APP_ID, 'version_name': VERSION_NAME, 'version_code': VERSION_CODE, 'abi': 'arm64-v8a',
            'signer_certificate_sha256': certificate, 'signing_key_created': False, 'signature_verified': True,
            'package_badging_verified': True, 'payload_bytes_verified': True, 'runtime_manifest': runtime,
            'runtime_manifest_sha256': payloads['assets/runtime/runtime-manifest.json']['sha256'], 'payloads': payloads,
            'changed_apk_payloads': sorted(REQUIRED_PAYLOADS|ADDED_PAYLOADS), 'replaced_apk_payloads': sorted(REQUIRED_PAYLOADS),
            'added_apk_payloads': sorted(ADDED_PAYLOADS), 'recompiled_dex': dex_pin, 'donor_dex': donor['recompiled_dex'],
            'retained_android_resources': donor['retained_android_resources'], 'donor': donor_link(),
            'java_sources': source_pins, 'changed_java_sources': changed_java, 'added_java_sources': [],
            'preserved_sources': {name: pin for name, pin in donor['preserved_sources'].items() if name not in JAVA_CHANGES},
            'source_manifest': donor['source_manifest'], 'generated_manifest': base.file_pin(manifest),
            'qualification': qualification, 'qualification_receipt': base.file_pin(args.qualification),
            'native_responsiveness': donor['native_responsiveness'], 'native_package_receipt': donor['native_package_receipt'],
            'native_launcher': donor['native_launcher'], 'server_cache_manifest': validate_server_caches(args.server_caches),
            'prepared_server_caches_added': True, 'runtime_timestamps': runtime_timestamps,
            'runtime_timestamps_receipt': base.file_pin(args.runtime_timestamps), 'testing_notes': base.file_pin(args.testing_notes),
            'native_libraries_changed': False, 'client_or_server_recompiled': False, 'java_or_dex_recompiled': True,
            'world_assets_changed': False, 'prepared_cache_archive_changed': False, 'dbserver_changed': False,
            'graphics_driver_changed': False, 'physical_gameplay_validated': False, 'dialog_semantics_validated': False,
            'server_payload_extraction_preflight': preflight,
            'scope': 'Exact prepared server/message caches, stable data roots and preserved component timestamps; retained native/world/avatar/client caches/driver and persistence/contact behavior; physical startup and contact dialogue remain pending'}
        (args.output.parent/REPORT_NAME).write_text(json.dumps(report, indent=2)+'\n')
        args.output.with_suffix('.apk.sha256').write_text(report['sha256']+'  '+APK_NAME+'\n')
        shutil.copyfile(args.testing_notes, args.output.parent/NOTES_NAME)
        print('Built retained-native startup-cache candidate', report['sha256'])


def publish_release(api, report, assets, notes):
    require(tuple(path.name for path in assets) == (APK_NAME, APK_NAME+'.sha256', NOTES_NAME),
            'Unexpected contact release assets')
    builder().checked_file(assets[0], report)
    for path in ('/releases/tags/'+RELEASE_TAG, '/git/ref/tags/'+RELEASE_TAG):
        try: existing = api.request(path)
        except urllib.error.HTTPError as error:
            if error.code != 404: raise
        else:
            require(not path.startswith('/releases/'), 'Existing contact release is never replaced')
            require(existing.get('object', {}).get('type') == 'commit'
                and existing['object'].get('sha') == report['repository_commit'], 'Existing tag points elsewhere')
    body = notes+'\n\nAPK SHA-256: `'+report['sha256']+'`.\n'
    body += '[Focused startup-cache, runtime extraction and persistence qualification](https://github.com/'+REPOSITORY+'/actions/runs/'+os.environ.get('GITHUB_RUN_ID', '')+').\n'
    release = api.request('/releases', {'tag_name': RELEASE_TAG, 'target_commitish': report['repository_commit'],
        'name': 'COH Atlas Gameplay 0.12.1 — prepared server caches and faster update reuse',
        'body': body, 'draft': True, 'prerelease': True, 'generate_release_notes': False, 'make_latest': 'false'}, method='POST')
    require(type(release.get('id')) is int and release.get('draft') is True and release.get('prerelease') is True
        and release.get('tag_name') == RELEASE_TAG, 'Unexpected created contact release')
    for path in assets:
        uploaded = api.request('/releases/'+str(release['id'])+'/assets?'+urllib.parse.urlencode({'name': path.name}),
                               path, method='POST', upload=True)
        pin = builder().file_pin(path)
        require(uploaded.get('state') == 'uploaded' and uploaded.get('name') == path.name
            and uploaded.get('size') == pin['bytes'] and uploaded.get('digest') == 'sha256:'+pin['sha256'],
            'Contact release upload differs')
    published = api.request('/releases/'+str(release['id']), {'draft': False, 'prerelease': True, 'make_latest': 'false'}, method='PATCH')
    require(published.get('id') == release['id'] and published.get('draft') is False
        and published.get('prerelease') is True and published.get('tag_name') == RELEASE_TAG,
        'Contact publication did not complete')
    return published.get('html_url')


def publish(args):
    base, current = builder(), builder(repaired=True)
    require(os.environ.get('GITHUB_REPOSITORY') == REPOSITORY and os.environ.get('GITHUB_REF') == 'refs/heads/'+BRANCH
        and os.environ.get('GITHUB_EVENT_NAME') in ('push', 'workflow_dispatch'), 'Publication requires authorized continuation branch')
    report = read_json(args.build_report); donor = validate_donor(args.donor_apk, args.donor_build_report)
    cache_manifest = validate_server_caches(args.server_caches)
    commit = base.source_commit(os.environ.get('GITHUB_SHA'))
    qualification = validate_qualification(read_json(args.qualification), commit)
    runtime_timestamps = validate_runtime_timestamps(read_json(args.runtime_timestamps), commit)
    with tempfile.TemporaryDirectory(prefix='coh-contact-source-') as temporary:
        _, sources, changes = current_java_sources(donor, Path(temporary))
    require(report.get('format') == 1 and report.get('apk') == APK_NAME and report.get('repository_commit') == commit
        and report.get('application_id') == base.APP_ID and report.get('version_name') == VERSION_NAME
        and report.get('version_code') == VERSION_CODE and report.get('signer_certificate_sha256') == SIGNER
        and report.get('signing_key_created') is False and report.get('donor') == donor_link()
        and report.get('runtime_timestamps') == runtime_timestamps
        and report.get('runtime_timestamps_receipt') == base.file_pin(args.runtime_timestamps)
        and report.get('qualification') == qualification and report.get('qualification_receipt') == base.file_pin(args.qualification)
        and report.get('java_sources') == sources and report.get('changed_java_sources') == changes and report.get('added_java_sources') == []
        and all(report.get(key) is True for key in ('signature_verified', 'package_badging_verified', 'payload_bytes_verified', 'java_or_dex_recompiled'))
        and all(report.get(key) is False for key in ('native_libraries_changed', 'client_or_server_recompiled', 'world_assets_changed',
            'prepared_cache_archive_changed', 'dbserver_changed', 'graphics_driver_changed', 'physical_gameplay_validated', 'dialog_semantics_validated'))
        and report.get('server_cache_manifest') == cache_manifest and report.get('prepared_server_caches_added') is True
        and report.get('native_responsiveness') == donor['native_responsiveness']
        and report.get('native_package_receipt') == donor['native_package_receipt'] and report.get('native_launcher') == donor['native_launcher'],
        'Startup-cache build receipt differs')
    base.checked_file(args.apk, report); verify_derivative(args.apk, donor, report['payloads'], report['recompiled_dex'])
    for name in HELPERS|GUEST_ADDITIONS:
        require(report['payloads']['assets/runtime/'+name] == base.file_pin(ROOT/'android/guest'/name), 'Packaged qualified guest helper differs')
    for name in CACHE_PAYLOADS:
        require(report['payloads']['assets/runtime/'+name] == base.file_pin(args.server_caches/name), 'Published server cache payload differs')
    require(verify_apk_server_archives(args.apk) == report['server_payload_extraction_preflight'], 'Published startup-cache APK fails real guest extraction')
    with zipfile.ZipFile(args.apk) as archive:
        runtime = json.loads(archive.read('assets/runtime/runtime-manifest.json'))
        client = json.loads(archive.read('assets/runtime/client-manifest.json'))
        require(runtime == report['runtime_manifest'] and runtime['accepted_base_runtime'] == donor['runtime_manifest']['accepted_base_runtime']
            and all(runtime['files'].get(name) == pin for name, pin in client['files'].items()), 'Runtime verification manifests differ')
    base.verify_signer_output(base.run('java', '-jar', args.build_tools/'lib/apksigner.jar', 'verify', '--verbose', '--print-certs', args.apk), SIGNER)
    current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', args.apk))
    checksum = args.apk.with_suffix('.apk.sha256'); require(checksum.read_text() == report['sha256']+'  '+APK_NAME+'\n', 'Published checksum differs')
    public_notes = args.apk.parent/NOTES_NAME; base.checked_file(public_notes, report['testing_notes']); base.checked_file(args.testing_notes, report['testing_notes'])
    api = module('contact_interaction_github', Path(__file__).with_name('build_atlas_gameplay_apk.py'))
    print('Published startup-cache prerelease:', publish_release(api.GitHub(os.environ.get('GH_TOKEN')), report,
        (args.apk, checksum, public_notes), public_notes.read_text()))


def main():
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest='command', required=True)
    get = commands.add_parser('download-donor'); get.add_argument('--output', type=Path, required=True)
    create = commands.add_parser('build')
    for name in ('donor-apk', 'donor-build-report', 'qualification', 'android-jar', 'build-tools', 'keystore', 'output', 'server-caches', 'runtime-timestamps'):
        create.add_argument('--'+name, type=Path, required=True)
    create.add_argument('--repository-commit'); create.add_argument('--password-env', default='COH_INTERACTIVE_KEYSTORE_PASSWORD')
    create.add_argument('--testing-notes', type=Path, default=NOTES)
    release = commands.add_parser('publish')
    for name in ('apk', 'build-report', 'build-tools', 'qualification', 'donor-build-report', 'donor-apk', 'server-caches', 'runtime-timestamps'):
        release.add_argument('--'+name, type=Path, required=True)
    release.add_argument('--testing-notes', type=Path, default=NOTES)
    args = parser.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path): setattr(args, key, value.absolute())
    {'download-donor': download, 'build': build, 'publish': publish}[args.command](args)


if __name__ == '__main__': main()
