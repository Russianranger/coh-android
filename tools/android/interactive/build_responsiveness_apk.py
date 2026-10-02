#!/usr/bin/env python3
"""Build the explicit 0.11.5 native responsiveness candidate from public 0.11.4.

Retain the signer, DbServer, imported world, avatar, prepared cache history and
runtime. New Game and MapServer bytes remain unaccepted until device testing.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'android/guest'))
import native_responsiveness_contract as native_contract
import package_responsiveness_native as native_package
from package_reference_runtime import file_record, dependency_report
REPOSITORY = 'Russianranger/coh-android'
BRANCH = 'codex/character-persistence-continuation'
DONOR_COMMIT = '97c5ece986c9ba91825844e648d728ee310ed732'
DONOR_RUN_ID = 37030944557
DONOR_APK_NAME = 'COH-Atlas-Gameplay-0.11.4.apk'
DONOR_APK = {'bytes': 595116556, 'sha256': '8f5a398f15adc4d94ed1137817a7db696bafa3c03aa0e7a54638e5570bfb0fa3'}
DONOR_BUILD = {'bytes': 65042, 'sha256': '7608f24579a23a6b538cf77c7153d3cf69f4e7178588fd5eb7cfb87d8be8978f'}
DONOR_URL = 'https://github.com/'+REPOSITORY+'/releases/download/coh-atlas-gameplay-v0.11.4/'+DONOR_APK_NAME
SIGNER = '92955353965f118a748f1f2cadc00dfb39b3e8ade0a6cdd7d44058a3a776c282'
VERSION_NAME, VERSION_CODE = '0.11.5', 11
APK_NAME = 'COH-Atlas-Gameplay-0.11.5.apk'
REPORT_NAME = 'responsiveness-apk-build-report.json'
NOTES_NAME = 'COH-Atlas-Gameplay-0.11.5-testing.txt'
NOTES = ROOT/'docs'/NOTES_NAME
RELEASE_TAG = 'coh-atlas-gameplay-v0.11.5'
RELEASE_NAME = 'COH Atlas Gameplay 0.11.5 — startup readiness and software rendering improvements'
BUILD_SCOPE = 'Explicit native responsiveness candidate: immediate native character events, compact texture headers, transient graphics profile and one owned client retry; data, avatar, DbServer, CRT, prepared cache donor and software renderer retained; physical timings and FPS pending'
CLIENT_OR_SERVER_RECOMPILED = True
HELPERS = frozenset(('local_character_server.py', 'client_interactive_diagnostic.py',
    'client_startup_diagnostic.py', 'game_diagnostic.py', 'character_creation_diagnostic.py',
    'character_reopen_diagnostic.py'))
GUEST_ADDITIONS = frozenset(('native_responsiveness_contract.py', 'native_character_events.py',
                           'texture_header_index.py', 'client_attempt_retry.py'))
NATIVE_PAYLOADS = frozenset(('client-runtime.zip', 'game-package.tar.gz', 'client-launcher.exe'))
ADDED_PAYLOADS = frozenset('assets/runtime/'+name for name in GUEST_ADDITIONS|{'native-responsiveness.json'})
ALLOWED_PAYLOADS = frozenset('assets/runtime/'+name for name in HELPERS|NATIVE_PAYLOADS|{'client-manifest.json', 'runtime-manifest.json'})
REQUIRED_PAYLOADS = frozenset('assets/runtime/'+name for name in NATIVE_PAYLOADS|{'client-manifest.json', 'runtime-manifest.json'})
JAVA_ROOT = 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/'
JAVA_CHANGES = frozenset(JAVA_ROOT+name for name in ('ClientActivity.java', 'ClientRuntime.java'))
PRESERVED_SOURCE_CHANGES = frozenset(('android/native/client-launcher.c',))
QUALIFICATION_SCOPE = 'immediate_native_readiness_texture_header_index_transient_graphics_client_retry'
CHECKS = ('native_candidate_source_receipts_verified', 'retained_data_runtime_and_cache_history_preserved',
          'readiness_stability_save_and_budget_guards_preserved', 'texture_index_fallbacks_verified',
          'transient_graphics_and_owned_client_retry_verified')
WORKFLOW = '.github/workflows/android-responsiveness.yml'
QUALIFICATION_SCRIPT = 'tools/android/interactive/qualify_responsiveness.py'
SOURCE_FILES = frozenset((WORKFLOW, QUALIFICATION_SCRIPT,
    'tools/android/interactive/build_responsiveness_apk.py',
    'tools/android/interactive/package_responsiveness_native.py',
    'tools/android/interactive/test_responsiveness_package.py',
    'android/native/client-launcher.c', 'android/interactive/src/main/AndroidManifest.xml',
    *(('android/guest/'+name) for name in HELPERS|GUEST_ADDITIONS), *JAVA_CHANGES))


def require(value, message):
    if not value:
        raise ValueError(message)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def builder(*, repaired=False):
    base = module('responsiveness_base', Path(__file__).with_name('build_apk.py'))
    if repaired:
        base.VERSION_NAME, base.VERSION_CODE, base.APK_NAME = VERSION_NAME, VERSION_CODE, APK_NAME
    return base


def prior_builder():
    return module('responsiveness_prior', Path(__file__).with_name('build_startup_perf_apk.py'))


def read_json(path):
    return native_package.read_json(path)


def donor_link():
    return {'run_id': DONOR_RUN_ID, 'repository_commit': DONOR_COMMIT,
            'apk': DONOR_APK, 'build_report': DONOR_BUILD}


def validate_donor_receipt(path):
    base, prior = builder(), prior_builder()
    base.checked_file(path, DONOR_BUILD)
    donor = read_json(path)
    require(donor.get('repository_commit') == DONOR_COMMIT and donor.get('apk') == DONOR_APK_NAME
            and {key: donor.get(key) for key in DONOR_APK} == DONOR_APK
            and donor.get('version_name') == '0.11.4' and donor.get('version_code') == 10
            and donor.get('signer_certificate_sha256') == SIGNER and donor.get('signing_key_created') is False
            and donor.get('donor') == prior.donor_link()
            and len(donor.get('payloads', {})) == 50 and len(donor.get('java_sources', {})) == 16
            and all(donor.get(key) is True for key in ('signature_verified', 'package_badging_verified', 'payload_bytes_verified'))
            and donor.get('client_or_server_recompiled') is False,
            'Exact public 0.11.4 donor receipt differs')
    return donor


def validate_donor(apk, receipt):
    base = builder()
    base.checked_file(apk, DONOR_APK)
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
    return donor


def current_java_sources(donor, generated):
    base = builder()
    sources = base.java_sources(ROOT/'android/interactive/src/main', generated)
    pins = {path.relative_to(ROOT).as_posix(): base.file_pin(path) for path in sources
            if path.is_relative_to(ROOT) and not path.is_relative_to(generated)}
    require(set(pins) == set(donor['java_sources']), 'Authored Java inventory changed unexpectedly')
    changed = {name for name in pins if pins[name] != donor['java_sources'][name]}
    require(changed == JAVA_CHANGES, 'Java changes exceed the graphics profile UI/runtime')
    for name, pin in donor['preserved_sources'].items():
        if name not in JAVA_CHANGES|PRESERVED_SOURCE_CHANGES:
            base.checked_file(ROOT/name, pin)
    base.checked_file(ROOT/'android/interactive/src/main/AndroidManifest.xml', donor['source_manifest'])
    return sources, pins, sorted(changed)


def validate_qualification(receipt, commit):
    base = builder()
    require(receipt.get('format') == 1 and receipt.get('status') == 'passed'
            and receipt.get('scope') == QUALIFICATION_SCOPE and receipt.get('repository_commit') == commit
            and receipt.get('donor_apk_sha256') == DONOR_APK['sha256']
            and receipt.get('physical_gameplay_validated') is False and receipt.get('native_runtime_booted') is False
            and type(receipt.get('tests_run')) is int and receipt['tests_run'] >= 30
            and set(receipt.get('checks', {})) == set(CHECKS) and all(receipt['checks'].values()),
            'Exact focused responsiveness qualification is required')
    require(SOURCE_FILES <= set(receipt.get('source_files', {})), 'Qualification source closure incomplete')
    for name, pin in receipt['source_files'].items():
        require(isinstance(name, str) and not Path(name).is_absolute() and '..' not in Path(name).parts
                and '\\' not in name, 'Unsafe qualification source path')
        base.checked_file(ROOT/name, pin)
    return receipt


def zip_contents(path):
    with zipfile.ZipFile(path) as archive:
        require(len(archive.namelist()) == len(set(archive.namelist())), 'Duplicate client archive members')
        return {name: archive.read(name) for name in archive.namelist()}


def tar_contents(path):
    with tarfile.open(path, 'r:gz') as archive:
        entries = archive.getmembers()
        require(len(entries) == len({entry.name for entry in entries})
                and all(entry.isfile() and '/' not in entry.name and '\\' not in entry.name
                        and entry.name not in ('.', '..') for entry in entries), 'Unsafe game archive inventory')
        return {entry.name: archive.extractfile(entry).read() for entry in entries}


def encoded(value):
    return (json.dumps(value, indent=2)+'\n').encode()


def write_game_archive(path, members):
    """Use the canonical metadata required by the actual guest unpacker."""
    with tarfile.open(path, 'w:gz', compresslevel=6) as archive:
        for name, raw in sorted(members.items()):
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            info.mode = 0o644
            info.uid = info.gid = info.mtime = 0
            info.uname = info.gname = ''
            archive.addfile(info, io.BytesIO(raw))


def verify_server_archives(assets):
    """Exercise the guest's real extraction gate before packaging or publishing.

    Inner payload hashes alone do not prove that the guest accepts tar metadata.
    This preflight never opens a database or starts a native process.
    """
    from local_login_server import extract_regular
    records = {}
    with tempfile.TemporaryDirectory(prefix='coh-server-archive-preflight-') as temporary:
        for name in ('dbserver-package.tar.gz', 'dbserver-schema.tar.gz', 'game-package.tar.gz'):
            source = Path(assets)/name
            pin = builder().file_pin(source)
            destination = Path(temporary)/name
            extract_regular(source, destination)
            files = [path for path in destination.rglob('*') if path.is_file()]
            records[name] = dict(pin, file_count=len(files),
                                 extracted_bytes=sum(path.stat().st_size for path in files))
    return {'format': 1, 'status': 'passed', 'archives': records}


def verify_apk_server_archives(apk):
    with tempfile.TemporaryDirectory(prefix='coh-apk-server-preflight-') as temporary:
        assets = Path(temporary)
        with zipfile.ZipFile(apk) as archive:
            for name in ('dbserver-package.tar.gz', 'dbserver-schema.tar.gz', 'game-package.tar.gz'):
                with archive.open('assets/runtime/'+name) as source, (assets/name).open('xb') as target:
                    shutil.copyfileobj(source, target, 64*1024)
        return verify_server_archives(assets)


def apply_native(assets, native_directory, launcher, donor, commit, native_commit=None):
    base = builder()
    build = native_package.validate_package(native_directory, native_commit or commit)
    launch = file_record(launcher)
    native_contract.pe_record(launch)
    clients, games = zip_contents(assets/'client-runtime.zip'), tar_contents(assets/'game-package.tar.gz')
    client, game = json.loads(clients['client-package.json']), json.loads(games['game-package.json'])
    retained_client = {name: value for name, value in client['files'].items() if name != 'CityOfHeroes.exe'}
    retained_game = {name: value for name, value in game['files'].items() if name != 'MapServer.exe'}
    receipt = {'format': 1, 'role': native_contract.ROLE, 'repository_commit': commit,
        'source_commit': native_contract.SOURCE, 'data_commit': native_contract.DATA,
        'configuration': 'OptDebug', 'architecture': 'Win32', 'runtime_execution_validated': False,
        'postgresql_persistence_fixture': False, 'files': {**build['files'], 'client-launcher.exe': launch},
        'build_inputs': build['build_inputs'], 'retained_native_files': {'client': retained_client, 'game': retained_game},
        'retained_cache': {'archive': donor['payloads']['assets/runtime/client-caches.zip'],
            'executable_sha256': client['files']['CityOfHeroes.exe']['sha256'], 'schema_changed': False,
            'schema_sources_sha256': build['schema_sources_sha256']},
        'build_provenance': {'native_build_manifest': base.file_pin(native_directory/'native-responsiveness-build.json'),
            'native_build_repository_commit': build['repository_commit'],
            'cmake_cache_sha256': build['cmake_cache_sha256'], 'run_url': build['run_url'],
            'launcher_source': base.file_pin(ROOT/'android/native/client-launcher.c')}}
    native_contract.validate_receipt(receipt)
    wrapper = {'receipt': receipt, 'receipt_sha256': native_contract.canonical_sha(receipt)}
    client['repository_commit'] = commit
    client['native_responsiveness'] = wrapper
    client['files']['CityOfHeroes.exe'] = build['files']['CityOfHeroes.exe']
    client['dependency_report'] = dependency_report(client['files'])
    require(not client['dependency_report']['unresolved'], 'New client imports exceed retained DLL closure')
    clients['CityOfHeroes.exe'] = (native_directory/'CityOfHeroes.exe').read_bytes()
    clients['client-package.json'] = encoded(client)
    with zipfile.ZipFile(assets/'client-runtime.zip', 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, raw in sorted(clients.items()):
            archive.writestr(name, raw)
    event_build = build['build_inputs']['character_events']
    source_raw = encoded(event_build)
    producer = {'schema_version': 1, 'build_role': 'character_events',
        'status': 'diagnostic_build_packaged_runtime_unverified', 'source_commit': native_contract.SOURCE,
        'data_commit': native_contract.DATA, 'repository_commit': commit, 'configuration': 'OptDebug',
        'architecture': 'Win32', 'postgresql_persistence_fixture': False, 'runtime_execution_validated': False,
        'build_targets': ['MapServer'], 'build_input': event_build, 'progress_contract': event_build['progress_contract'],
        'events_contract': event_build['events_contract'], 'cmake_cache_sha256': build['cmake_cache_sha256'],
        'files': {'MapServer.exe': build['files']['MapServer.exe'],
                  'character-events-build-input.json': {'size': len(source_raw), 'sha256': hashlib.sha256(source_raw).hexdigest()}},
        'symbols': {'MapServer.pdb': build['symbols']['MapServer.pdb']},
        'run_url': build['run_url'], 'dependency_validation': 'exact_public_0.11.4_dll_closure'}
    game['repository_commit'] = commit
    game['native_responsiveness'] = wrapper
    game['character_events_contract'] = event_build['events_contract']
    game['inputs']['mapserver_progress'] = {'repository_commit': commit,
        'events_contract': event_build['events_contract'],
        'manifest_sha256': hashlib.sha256(encoded(producer)).hexdigest(), 'manifest': producer}
    game['files']['MapServer.exe'] = dict(build['files']['MapServer.exe'], bytes=build['files']['MapServer.exe']['size'])
    del game['files']['MapServer.exe']['size']
    game['file_donors']['MapServer.exe'] = 'character_events'
    game['dependency_report'] = dependency_report(game['files'])
    require(not game['dependency_report']['unresolved'], 'New MapServer imports exceed retained DLL closure')
    games['MapServer.exe'] = (native_directory/'MapServer.exe').read_bytes()
    games['game-package.json'] = encoded(game)
    write_game_archive(assets/'game-package.tar.gz', games)
    shutil.copyfile(launcher, assets/'client-launcher.exe')
    (assets/'native-responsiveness.json').write_bytes(encoded(receipt))
    native_contract.client_contract(client, receipt)
    native_contract.events_progress_contract(game)
    return receipt, game


def extract_and_repair(apk, donor, destination, commit, native_directory, launcher, native_commit=None):
    base = builder()
    destination.mkdir(parents=True)
    retained = {}
    with zipfile.ZipFile(apk) as archive:
        for entry in archive.infolist():
            name = entry.filename
            if name == 'AndroidManifest.xml' or name.startswith('META-INF/'):
                continue
            require((name in donor['payloads'] or name in ('classes.dex', 'resources.arsc', 'res/drawable/ic_coh_client.xml'))
                    and not stat.S_ISLNK(entry.external_attr >> 16), 'Unexpected donor APK entry')
            target = destination/name; target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open('xb') as output:
                shutil.copyfileobj(source, output, 1024*1024)
            retained[name] = base.file_pin(target)
    require(all(retained.get(name) == pin for name, pin in donor['payloads'].items()), 'Extracted donor bytes differ')
    assets = destination/'assets/runtime'
    runtime, client = read_json(assets/'runtime-manifest.json'), read_json(assets/'client-manifest.json')
    require(runtime == donor['runtime_manifest'], 'Donor runtime manifest differs')
    for name, pin in donor['payloads'].items():
        if name.startswith('assets/runtime/') and name.endswith('.py') and Path(name).name not in HELPERS:
            base.checked_file(ROOT/'android/guest'/Path(name).name, pin)
    for name in HELPERS|GUEST_ADDITIONS:
        source = ROOT/'android/guest'/name
        base.checked_file(source)
        require(source.stat().st_size <= 1024*1024, 'Unbounded guest helper')
        if name in GUEST_ADDITIONS:
            require(not (assets/name).exists(), 'New guest helper collides with donor')
        shutil.copyfile(source, assets/name)
    native, game = apply_native(assets, native_directory, launcher, donor, commit, native_commit)
    verify_server_archives(assets)
    updates = {name: base.file_pin(assets/name) for name in HELPERS|GUEST_ADDITIONS|NATIVE_PAYLOADS|{'native-responsiveness.json'}}
    client['files'].update(updates)
    (assets/'client-manifest.json').write_bytes(encoded(client))
    runtime['files'].update(updates)
    runtime['files']['client-manifest.json'] = base.file_pin(assets/'client-manifest.json')
    runtime['repository_commit'] = commit
    runtime['scope'] = 'Explicit native responsiveness candidate; retained DbServer, data, caches and graphics driver; device performance pending'
    map_meta = runtime['client_bundle']['local_server']['mapserver']
    producer = native_contract.events_progress_contract(game)['producer']
    map_meta.update(package_run_id=int(native['build_provenance']['run_url'].rsplit('/', 1)[1]),
        package_repository_commit=commit, package_manifest_sha256=hashlib.sha256(encoded(game)).hexdigest(),
        mapserver_progress_producer=producer, archive_pin=updates['game-package.tar.gz'],
        native_responsiveness_candidate=True, character_events_contract=game['character_events_contract'])
    runtime['client_bundle']['native_responsiveness'] = {
        'receipt_file': 'native-responsiveness.json', 'receipt_pin': updates['native-responsiveness.json'],
        'runtime_execution_validated': False, 'retained_cache_schema': True}
    (assets/'runtime-manifest.json').write_bytes(encoded(runtime))
    payloads = {name: base.file_pin(destination/name) for name in set(donor['payloads'])|ADDED_PAYLOADS}
    changed = {name for name in donor['payloads'] if payloads[name] != donor['payloads'][name]}
    require(REQUIRED_PAYLOADS <= changed <= ALLOWED_PAYLOADS, 'Derivative modified an unapproved APK payload')
    return runtime, payloads, retained, native


def repair_android_manifest(source, destination):
    base = builder(); base.verify_source_manifest(source)
    tree = ET.parse(source); manifest = tree.getroot()
    manifest.set(base.ANDROID+'versionName', VERSION_NAME)
    manifest.set(base.ANDROID+'versionCode', str(VERSION_CODE))
    ET.register_namespace('android', base.ANDROID[1:-1])
    tree.write(destination, encoding='utf-8', xml_declaration=True)
    builder(repaired=True).verify_source_manifest(destination)


def verify_derivative(apk, donor, payloads, dex_pin):
    base = builder()
    require(set(payloads) == set(donor['payloads'])|ADDED_PAYLOADS
            and REQUIRED_PAYLOADS <= {name for name in donor['payloads'] if payloads[name] != donor['payloads'][name]} <= ALLOWED_PAYLOADS,
            'Candidate APK payload boundaries differ')
    base.verify_packaged_payloads(apk, payloads)
    with zipfile.ZipFile(apk) as archive:
        require({name for name in archive.namelist() if not name.startswith('META-INF/')} ==
                set(payloads)|set(donor['retained_android_resources'])|{'AndroidManifest.xml', 'classes.dex'},
                'Unexpected candidate APK member')
        for name, pin in {'classes.dex': dex_pin, **donor['retained_android_resources']}.items():
            raw = archive.read(name)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == pin, 'Retained Android shell differs')


def verify_native_derivative(apk, donor_apk, receipt):
    """Compare native containers to the exact donor, independently of new receipts."""
    native_contract.validate_receipt(receipt)
    with zipfile.ZipFile(apk) as current, zipfile.ZipFile(donor_apk) as original:
        client_payloads = []
        game_payloads = []
        for archive in (original, current):
            with zipfile.ZipFile(io.BytesIO(archive.read('assets/runtime/client-runtime.zip'))) as client:
                names = client.namelist()
                require(len(names) == len(set(names)), 'Duplicate native client member')
                client_payloads.append({name: client.read(name) for name in names})
            with tarfile.open(fileobj=io.BytesIO(archive.read('assets/runtime/game-package.tar.gz')), mode='r:gz') as game:
                entries = game.getmembers()
                require(len(entries) == len({entry.name for entry in entries})
                        and all(entry.isfile() and '/' not in entry.name and '\\' not in entry.name for entry in entries),
                        'Unsafe native game member')
                game_payloads.append({entry.name: game.extractfile(entry).read() for entry in entries})
        for before, after, executable, manifest in (
                (*client_payloads, 'CityOfHeroes.exe', 'client-package.json'),
                (*game_payloads, 'MapServer.exe', 'game-package.json')):
            require(set(before) == set(after)
                    and all(before[name] == after[name] for name in before if name not in (executable, manifest)),
                    'Native derivative changed a retained executable or DLL')
            require(after[executable] != before[executable]
                    and hashlib.sha256(after[executable]).hexdigest() == receipt['files'][executable]['sha256'],
                    'Native executable was not replaced with the source-bound candidate')
        old_client = json.loads(client_payloads[0]['client-package.json'])
        old_game = json.loads(game_payloads[0]['game-package.json'])
        require(receipt['retained_native_files']['client'] == {
                    name: value for name, value in old_client['files'].items() if name != 'CityOfHeroes.exe'}
                and receipt['retained_native_files']['game'] == {
                    name: value for name, value in old_game['files'].items() if name != 'MapServer.exe'}
                and receipt['retained_cache']['executable_sha256'] == old_client['files']['CityOfHeroes.exe']['sha256'],
                'Retained native receipt relabelled the exact donor')
        cache = original.read('assets/runtime/client-caches.zip')
        require(receipt['retained_cache']['archive'] == {'bytes': len(cache), 'sha256': hashlib.sha256(cache).hexdigest()}
                and current.read('assets/runtime/client-caches.zip') == cache,
                'Prepared-cache donor archive or generation history changed')
        launcher = current.read('assets/runtime/client-launcher.exe')
        require(hashlib.sha256(launcher).hexdigest() == receipt['files']['client-launcher.exe']['sha256'],
                'Candidate launcher differs from its native receipt')


def download(args):
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh donor download required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(DONOR_URL, timeout=120) as source, args.output.open('xb') as target:
        total = 0
        while chunk := source.read(1024*1024):
            total += len(chunk); require(total <= DONOR_APK['bytes'], 'Oversized donor download')
            target.write(chunk)
    builder().checked_file(args.output, DONOR_APK)


def build(args):
    base, current = builder(), builder(repaired=True)
    commit = base.source_commit(args.repository_commit)
    donor = validate_donor(args.donor_apk, args.donor_build_report)
    qualification = validate_qualification(read_json(args.qualification), commit)
    password = base.signing_password_spec(args.password_env)
    base.verify_signing_identity(args.keystore, "coh-client-interactive", SIGNER, password)
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), "Fresh responsiveness APK required")
    base.checked_file(args.testing_notes)
    require(0 < args.testing_notes.stat().st_size <= 65536, "Bounded testing notes required")
    for tool in (args.android_jar, args.build_tools / "aapt2", args.build_tools / "zipalign",
                 args.build_tools / "lib/d8.jar", args.build_tools / "lib/apksigner.jar"):
        require(tool.is_file() and not tool.is_symlink(), "Required Android tool missing")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="coh-responsiveness-", dir=args.output.parent) as temporary:
        work = Path(temporary)
        runtime, payloads, retained, native = extract_and_repair(args.donor_apk, donor, work / "donor", commit, args.native_package, args.launcher, args.native_commit)
        classes, generated, dex = (work / name for name in ("classes", "generated", "dex"))
        for folder in (classes, generated, dex):
            folder.mkdir()
        # Check the complete authored compilation closure before invoking aapt/javac.
        current_java_sources(donor, generated)
        manifest = work / "AndroidManifest.xml"
        repair_android_manifest(ROOT / "android/interactive/src/main/AndroidManifest.xml", manifest)
        resources, unsigned, aligned, signed = (work / name for name in ("resources.zip", "unsigned.apk", "aligned.apk", "signed.apk"))
        base.run(args.build_tools / "aapt2", "compile", "--dir", ROOT / "android/interactive/src/main/res", "-o", resources)
        base.run(args.build_tools / "aapt2", "link", "-I", args.android_jar, "--manifest", manifest,
                 "--min-sdk-version", "26", "--target-sdk-version", "35", "--java", generated, resources, "-o", unsigned)
        with zipfile.ZipFile(unsigned) as archive:
            require(set(archive.namelist()) == {"AndroidManifest.xml", "resources.arsc", "res/drawable/ic_coh_client.xml"},
                    "Generated Android resource inventory differs")
            for name in donor["retained_android_resources"]:
                data = archive.read(name)
                require({"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()} == retained[name],
                        "Android resources changed beyond package version metadata")
        require({path.relative_to(generated).as_posix() for path in generated.rglob("*.java")} ==
                {base.APP_ID.replace(".", "/") + "/R.java"}, "Unexpected generated Java source inventory")
        sources, source_pins, changed_java = current_java_sources(donor, generated)
        base.run("java", "-m", "jdk.compiler/com.sun.tools.javac.Main", "--release", "8", "-cp", args.android_jar,
                 "-d", classes, *sources)
        class_jar = work / "classes.jar"
        with zipfile.ZipFile(class_jar, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(classes.rglob("*.class")):
                archive.write(path, path.relative_to(classes).as_posix())
        base.run("java", "-cp", args.build_tools / "lib/d8.jar", "com.android.tools.r8.D8", "--min-api", "26",
                 "--lib", args.android_jar, "--output", dex, class_jar)
        require({path.name for path in dex.iterdir()} == {"classes.dex"}, "Unexpected DEX output inventory")
        dex_pin = base.file_pin(dex / "classes.dex")
        with zipfile.ZipFile(unsigned, "a", zipfile.ZIP_DEFLATED) as archive:
            base.append_payloads(archive, [(work / "donor" / name, name) for name in sorted(payloads)])
            archive.write(dex / "classes.dex", "classes.dex")
        base.run(args.build_tools / "zipalign", "-f", "4", unsigned, aligned)
        base.run("java", "-jar", args.build_tools / "lib/apksigner.jar", "sign", "--ks", args.keystore,
                 "--ks-key-alias", "coh-client-interactive", "--ks-pass", password, "--key-pass", password, "--out", signed, aligned)
        certificate = base.verify_signer_output(base.run("java", "-jar", args.build_tools / "lib/apksigner.jar",
                                                       "verify", "--verbose", "--print-certs", signed), SIGNER)
        base.run(args.build_tools / "zipalign", "-c", "4", signed)
        current.verify_badging(base.run(args.build_tools / "aapt2", "dump", "badging", signed))
        verify_derivative(signed, donor, payloads, dex_pin)
        verify_native_derivative(signed, args.donor_apk, native)
        shutil.copyfile(signed, args.output)
        replaced_payloads = {name for name in donor["payloads"] if donor["payloads"][name] != payloads[name]}
        report = {"format": 1, "apk": APK_NAME, **base.file_pin(args.output), "repository_commit": commit,
            "application_id": base.APP_ID, "version_name": VERSION_NAME, "version_code": VERSION_CODE,
            "abi": "arm64-v8a", "signer_certificate_sha256": certificate, "signing_key_created": False,
            "signature_verified": True, "package_badging_verified": True, "payload_bytes_verified": True,
            "runtime_manifest": runtime, "runtime_manifest_sha256": payloads["assets/runtime/runtime-manifest.json"]["sha256"],
            "payloads": payloads, "changed_apk_payloads": sorted(replaced_payloads | ADDED_PAYLOADS),
            "replaced_apk_payloads": sorted(replaced_payloads), "added_apk_payloads": sorted(ADDED_PAYLOADS),
            "recompiled_dex": dex_pin, "donor_dex": donor["recompiled_dex"],
            "retained_android_resources": donor["retained_android_resources"], "donor": donor_link(),
            "java_sources": source_pins, "changed_java_sources": changed_java, "added_java_sources": [],
            "preserved_sources": {name: pin for name, pin in donor["preserved_sources"].items()
                                  if name not in JAVA_CHANGES | PRESERVED_SOURCE_CHANGES},
            "source_manifest": donor["source_manifest"], "generated_manifest": base.file_pin(manifest),
            "qualification": qualification, "qualification_receipt": base.file_pin(args.qualification),
            "native_responsiveness": native, "native_package_receipt": base.file_pin(args.native_package / "native-responsiveness-build.json"),
            "native_launcher": base.file_pin(args.launcher), "testing_notes": base.file_pin(args.testing_notes),
            "native_libraries_changed": False, "client_or_server_recompiled": CLIENT_OR_SERVER_RECOMPILED, "java_or_dex_recompiled": True,
            "world_assets_changed": False, "prepared_cache_archive_changed": False, "dbserver_changed": False,
            "graphics_driver_changed": False, "physical_gameplay_validated": False,
            "scope": BUILD_SCOPE,
            "server_payload_extraction_preflight": verify_apk_server_archives(args.output)}
        (args.output.parent / REPORT_NAME).write_text(json.dumps(report, indent=2) + "\n")
        args.output.with_suffix(".apk.sha256").write_text(report["sha256"] + "  " + APK_NAME + "\n")
        shutil.copyfile(args.testing_notes, args.output.parent / NOTES_NAME)
        print("Built focused retained-signer responsiveness candidate", report["sha256"])


def publish_release(api, report, assets, notes):
    base = builder()
    require(tuple(path.name for path in assets) == (APK_NAME, APK_NAME+'.sha256', NOTES_NAME),
            'Unexpected responsiveness release assets')
    base.checked_file(assets[0], report)
    for path in ('/releases/tags/'+RELEASE_TAG, '/git/ref/tags/'+RELEASE_TAG):
        try:
            existing = api.request(path)
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
        else:
            require(not path.startswith('/releases/'), 'Existing responsiveness release is never replaced')
            require(existing.get('object', {}).get('type') == 'commit'
                    and existing['object'].get('sha') == report['repository_commit'], 'Existing tag points elsewhere')
    body = notes+'\n\nAPK SHA-256: `'+report['sha256']+'`.\n'
    body += '[Focused native build and responsiveness qualification](https://github.com/'+REPOSITORY+'/actions/runs/'+os.environ.get('GITHUB_RUN_ID', '')+').\n'
    release = api.request('/releases', {'tag_name': RELEASE_TAG, 'target_commitish': report['repository_commit'],
        'name': RELEASE_NAME,
        'body': body, 'draft': True, 'prerelease': True, 'generate_release_notes': False, 'make_latest': 'false'}, method='POST')
    require(type(release.get('id')) is int and release.get('draft') is True and release.get('prerelease') is True
            and release.get('tag_name') == RELEASE_TAG, 'Unexpected created responsiveness release')
    for path in assets:
        uploaded = api.request('/releases/'+str(release['id'])+'/assets?'+urllib.parse.urlencode({'name': path.name}),
                               path, method='POST', upload=True)
        pin = base.file_pin(path)
        require(uploaded.get('state') == 'uploaded' and uploaded.get('name') == path.name
                and uploaded.get('size') == pin['bytes'] and uploaded.get('digest') == 'sha256:'+pin['sha256'],
                'Responsiveness release upload differs')
    published = api.request('/releases/'+str(release['id']), {'draft': False, 'prerelease': True, 'make_latest': 'false'}, method='PATCH')
    require(published.get('id') == release['id'] and published.get('draft') is False
            and published.get('prerelease') is True and published.get('tag_name') == RELEASE_TAG,
            'Responsiveness publication did not complete')
    return published.get('html_url')


def publish(args):
    base, current = builder(), builder(repaired=True)
    require(os.environ.get('GITHUB_REPOSITORY') == REPOSITORY and os.environ.get('GITHUB_REF') == 'refs/heads/'+BRANCH
            and os.environ.get('GITHUB_EVENT_NAME') in ('push', 'workflow_dispatch'),
            'Publication requires the authorized continuation branch')
    report = read_json(args.build_report)
    donor = validate_donor(args.donor_apk, args.donor_build_report)
    commit = base.source_commit(os.environ.get('GITHUB_SHA'))
    qualification = validate_qualification(read_json(args.qualification), commit)
    with tempfile.TemporaryDirectory(prefix='coh-responsiveness-source-') as temporary:
        _, sources, changes = current_java_sources(donor, Path(temporary))
    require(report.get('format') == 1 and report.get('apk') == APK_NAME and report.get('repository_commit') == commit
            and report.get('application_id') == base.APP_ID and report.get('version_name') == VERSION_NAME
            and report.get('version_code') == VERSION_CODE and report.get('signer_certificate_sha256') == SIGNER
            and report.get('signing_key_created') is False and report.get('donor') == donor_link()
            and report.get('qualification') == qualification
            and report.get('qualification_receipt') == base.file_pin(args.qualification)
            and report.get('java_sources') == sources and report.get('changed_java_sources') == changes
            and report.get('added_java_sources') == []
            and all(report.get(key) is True for key in ('signature_verified', 'package_badging_verified',
                'payload_bytes_verified', 'java_or_dex_recompiled'))
            and report.get('client_or_server_recompiled') is CLIENT_OR_SERVER_RECOMPILED
            and all(report.get(key) is False for key in ('native_libraries_changed', 'world_assets_changed',
                'prepared_cache_archive_changed', 'dbserver_changed', 'graphics_driver_changed', 'physical_gameplay_validated')),
            'Responsiveness build receipt differs')
    base.checked_file(args.apk, report)
    require(verify_apk_server_archives(args.apk) == report.get('server_payload_extraction_preflight'),
            'Published APK does not pass the actual guest server extraction gate')
    verify_derivative(args.apk, donor, report['payloads'], report['recompiled_dex'])
    for name in HELPERS|GUEST_ADDITIONS:
        require(report['payloads']['assets/runtime/'+name] == base.file_pin(ROOT/'android/guest'/name),
                'Qualified guest source differs from packaged helper')
    with zipfile.ZipFile(args.apk) as archive:
        receipt = json.loads(archive.read('assets/runtime/native-responsiveness.json'))
        require(receipt == report.get('native_responsiveness'), 'Published native receipt differs')
        native_contract.validate_receipt(receipt)
        verify_native_derivative(args.apk, args.donor_apk, receipt)
        with zipfile.ZipFile(io.BytesIO(archive.read('assets/runtime/client-runtime.zip'))) as client_zip:
            client = json.loads(client_zip.read('client-package.json'))
            native_contract.client_contract(client, receipt)
            require(hashlib.sha256(client_zip.read('CityOfHeroes.exe')).hexdigest() == receipt['files']['CityOfHeroes.exe']['sha256'],
                    'Published new client bytes differ')
        with tarfile.open(fileobj=io.BytesIO(archive.read('assets/runtime/game-package.tar.gz')), mode='r:gz') as game_tar:
            game = json.load(game_tar.extractfile('game-package.json'))
            native_contract.events_progress_contract(game)
            require(hashlib.sha256(game_tar.extractfile('MapServer.exe').read()).hexdigest() == receipt['files']['MapServer.exe']['sha256'],
                    'Published new MapServer bytes differ')
        runtime = json.loads(archive.read('assets/runtime/runtime-manifest.json'))
        client_manifest = json.loads(archive.read('assets/runtime/client-manifest.json'))
        require(runtime == report.get('runtime_manifest')
                and runtime['accepted_base_runtime'] == donor['runtime_manifest']['accepted_base_runtime']
                and all(runtime['files'].get(name) == pin for name, pin in client_manifest['files'].items()),
                'Published runtime verification metadata differs')
    base.verify_signer_output(base.run('java', '-jar', args.build_tools/'lib/apksigner.jar', 'verify',
                                      '--verbose', '--print-certs', args.apk), SIGNER)
    current.verify_badging(base.run(args.build_tools/'aapt2', 'dump', 'badging', args.apk))
    checksum = args.apk.with_suffix('.apk.sha256')
    require(checksum.read_text() == report['sha256']+'  '+APK_NAME+'\n', 'Published checksum differs')
    public_notes = args.apk.parent/NOTES_NAME
    base.checked_file(public_notes, report['testing_notes'])
    base.checked_file(args.testing_notes, report['testing_notes'])
    api_module = module('responsiveness_github', Path(__file__).with_name('build_atlas_gameplay_apk.py'))
    print('Published responsiveness prerelease:', publish_release(api_module.GitHub(os.environ.get('GH_TOKEN')), report,
          (args.apk, checksum, public_notes), public_notes.read_text()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    get = commands.add_parser('download-donor'); get.add_argument('--output', type=Path, required=True)
    create = commands.add_parser('build')
    for name in ('donor-apk', 'donor-build-report', 'qualification', 'native-package', 'launcher',
                 'android-jar', 'build-tools', 'keystore', 'output'):
        create.add_argument('--'+name, type=Path, required=True)
    create.add_argument('--repository-commit')
    create.add_argument('--native-commit', required=True)
    create.add_argument('--password-env', default='COH_INTERACTIVE_KEYSTORE_PASSWORD')
    create.add_argument('--testing-notes', type=Path, default=NOTES)
    release = commands.add_parser('publish')
    for name in ('apk', 'build-report', 'build-tools', 'qualification', 'donor-build-report', 'donor-apk'):
        release.add_argument('--'+name, type=Path, required=True)
    release.add_argument('--testing-notes', type=Path, default=NOTES)
    args = parser.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, key, value.absolute())
    {'download-donor': download, 'build': build, 'publish': publish}[args.command](args)


if __name__ == '__main__':
    main()
