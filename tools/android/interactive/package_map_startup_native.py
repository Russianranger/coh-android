#!/usr/bin/env python3
"""Admit only exact accepted native/FX components; preserve every donor layer."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tarfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'android/guest'), str(ROOT/'tools/android/atlasgame')]
import prepare_map_startup_source as source
import native_map_startup_contract as contract
from package_reference_runtime import file_record, dependency_report
from package_responsiveness_native import schema_pins, read_json
from package_monorail_native import write_game_archive

require = contract.require
BUILD = 'native-map-startup-build.json'
ANIMATION_FIXTURE = 'map-startup-animation-native.json'
ANIMATION_BINARY = 'map-startup-animation-native.exe'
MONORAIL_FIXTURE = 'map-startup-monorail-native.json'
MONORAIL_BINARY = 'map-startup-monorail-native.exe'
COMPONENT = 'map-startup-component.json'
MANIFEST = 'map-startup-manifest.json'
MARKER = ROOT/'tools/android/interactive/release-client-map-startup-0.13.32.json'
NATIVE_FILES = {'MapServer.exe', BUILD, ANIMATION_FIXTURE, ANIMATION_BINARY, MONORAIL_FIXTURE, MONORAIL_BINARY}
SOURCE_FILES = ('tools/prepare_map_startup_source.py', 'tools/map_startup_animation_certificate.py',
    'tools/test_map_startup_animation_certificate.py', source.OVERLAY,
    'database/map-startup/tests/animation_certificate.c',
    'tools/android/interactive/package_map_startup_native.py', 'android/guest/native_map_startup_contract.py',
    'android/guest/native_monorail_contract.py', 'android/guest/server_animation_package.py',
    'android/guest/server_cache_package.py', 'android/guest/atlas_beacon_package.py')
SOURCE_FILES += ('tools/map_startup_monorail_budget.py', 'tools/test_map_startup_monorail_budget.py',
    'tools/android/game/test_map_startup_monorail_budget.py', 'database/map-startup/tests/monorail_budget_contract.c',
    'database/monorail/overlay/MapServer/src/svr/wine_monorail.c',
    'database/monorail/overlay/MapServer/src/svr/wine_monorail.h')
MAX_ARCHIVE = 2*1024**3


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def pin(path):
    return contract.file_pin(path)


def sources():
    return {name: pin(ROOT/name) for name in SOURCE_FILES}


def run_id(url):
    match = re.fullmatch(r'https://github\.com/Russianranger/coh-android/actions/runs/([1-9][0-9]+)', str(url))
    require(match is not None, 'Exact native component Actions owner required')
    return int(match[1])


def validate_animation_fixture(path, build, *, binary=None):
    value = read_json(path)
    require(value.get('format') == 1 and value.get('status') == 'passed'
        and value.get('scope') == 'genuine Windows x86 raw-byte certificate and exact stock key validator; no MapServer or Thor boot'
        and contract.same(value.get('certificate'), build['animation_certificate'])
        and value.get('native_fixture_source') == pin(ROOT/'database/map-startup/tests/animation_certificate.c')
        and value.get('physical_startup_timing_validated') is False
        and value.get('native_binary_file') == ANIMATION_BINARY,
        'Actual Windows animation fixture identity/scope differs')
    original = (ROOT/'upstream/ouroboros'/source.SOURCE).read_bytes().replace(b'\r\n', b'\n')
    start = original.index(b'static void animDebugCheckBoneTrackOnLoad(')
    end = original.index(b'\nstatic SkeletonAnimTrack * animReadTrackFile', start)
    require(value.get('exact_stock_validator_sha256') == hashlib.sha256(original[start:end]).hexdigest(),
        'Native animation fixture did not use the exact stock validator')
    outputs = value.get('native_results', [])
    require(isinstance(outputs, list) and len(outputs) >= 14
        and sum('ALL tracks=5878 actual_stock_validator_errors=0' in line for line in outputs) == 1
        and any('opened=5878 certified=5878 fallback=0 crypto_failed=0 raw_bytes=88380730' in line for line in outputs)
        and any('bounded=1 certified=0 stock_errors=0' in line for line in outputs)
        and any(re.search(r'bounded=1 certified=0 stock_errors=[1-9]', line) for line in outputs)
        and any('bounded=0 certified=0' in line for line in outputs)
        and any('crypto_failed=1' in line for line in outputs),
        'Native animation full-byte and negative fallback evidence missing')
    if binary is not None:
        require(pin(binary) == value.get('native_binary'), 'Native animation fixture binary differs')
        record = file_record(binary)
        require(record.get('pe_machine') == 0x14c, 'Native animation fixture must be actual Win32 PE')
    return value


def validate_monorail_fixture(path, build, *, binary=None):
    value = read_json(path); budget = build['monorail_budget']
    require(type(value.get('format')) is int and value['format'] == 1
        and value.get('role') == 'native_map_startup_monorail_budget_fixtures' and value.get('status') == 'passed'
        and value.get('platform') == 'win32' and value.get('architecture') == 'x86'
        and type(value.get('tests_run')) is int and value['tests_run'] == 9
        and all(type(value.get(key)) is int and value[key] == 0 for key in ('skipped', 'errors', 'failures'))
        and value.get('original_source_sha256') == budget['source_sha256']['MapServer/src/svr/wine_monorail.c']
        and value.get('candidate_source_sha256') == budget['patched_sha256']['MapServer/src/svr/wine_monorail.c']
        and value.get('compiled_clock_instrumentation') == {'bytes': 114,
            'sha256': '671d2c5ac61ab9976a99f943c6e10286c402c41d5fb6d185c6c7f5a6d8b13752',
            'scope': 'GetTickCount_calls_in_actual_bridge_only_transport_APIs_retained'}
        and all(value.get(key) is True for key in ('historical_650_seconds_timeout_reproduced',
            'candidate_650_seconds_authorization_verified', '720_second_boundary_and_expiry_verified',
            'wrong_identity_cancel_retry_late_reply_and_wrap_verified', 'native_source_executed'))
        and value.get('physical_thor_execution_validated') is False
        and value.get('physical_startup_timing_validated') is False
        and value.get('native_binary_file') == MONORAIL_BINARY,
        'Actual Windows station-boundary fixture identity/scope differs')
    expected_sources = ('tools/map_startup_monorail_budget.py', 'tools/android/game/test_map_startup_monorail_budget.py',
        'database/map-startup/tests/monorail_budget_contract.c',
        'database/monorail/overlay/MapServer/src/svr/wine_monorail.c',
        'database/monorail/overlay/MapServer/src/svr/wine_monorail.h')
    require(value.get('sources') == {name: pin(ROOT/name) for name in expected_sources},
        'Actual Windows station fixture sources changed')
    if binary is not None:
        require(pin(binary) == value.get('native_binary') and file_record(binary).get('pe_machine') == 0x14c,
            'Actual Windows station fixture binary differs')
    return value


def package(args):
    require(re.fullmatch(r'[0-9a-f]{40}', args.repository_commit), 'Exact native source commit required')
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh native startup output required')
    build = read_json(args.source/source.RECEIPT)
    require(contract.same(build, source.expected_receipt(build['animation_certificate'],
            monorail_build_input=build['monorail_build_input'])), 'Native startup source receipt differs')
    require(re.findall(r'^COH_PG_PERSISTENCE_TESTS:BOOL=(.*)$', args.cache.read_text(encoding='utf-8-sig'), re.M) == ['OFF'],
        'Shipping native startup must disable persistence fixtures')
    for name, digest in {**build['patched_sha256'], **build['overlay_sha256'], **build['retained_sources_sha256'],
                         **build['monorail_build_input']['retained_collision_sources']}.items():
        require(source.sha256(args.source/name) == digest, 'Compiled native startup source differs: ' + name)
    fixture_binary = args.native_evidence.with_suffix('.exe')
    validate_animation_fixture(args.native_evidence, build, binary=fixture_binary)
    monorail_binary = args.monorail_evidence.with_suffix('.exe')
    validate_monorail_fixture(args.monorail_evidence, build, binary=monorail_binary)
    record = file_record(args.directory/'MapServer.exe'); contract.monorail.retained.pe_record(record)
    executable = (args.directory/'MapServer.exe').read_bytes()
    require(b'COH_ANIM_CERT_V1' in executable and contract.PACK_SHA256.encode() in executable
        and b'COH_HOST_ONLY_FX_IDS_COMPLETE_V1' not in executable,
        'Shipping MapServer certificate marker missing or host-only observer selected')
    value = {'format': 1, 'role': contract.ROLE, 'repository_commit': args.repository_commit,
        'source_commit': contract.SOURCE, 'data_commit': contract.DATA, 'configuration': 'OptDebug',
        'architecture': 'Win32', 'postgresql_persistence_fixture': False, 'runtime_execution_validated': False,
        'native_gameplay_validated': False, 'physical_timing_validated': False, 'build_targets': ['MapServer'],
        'build_input': build, 'schema_sources_sha256': schema_pins(args.source), 'cmake_cache': pin(args.cache),
        'files': {'MapServer.exe': record}, 'native_fixture': pin(args.native_evidence),
        'native_fixture_binary': pin(fixture_binary), 'symbols': {'MapServer.pdb': file_record(args.directory/'MapServer.pdb')},
        'native_monorail_fixture': pin(args.monorail_evidence), 'native_monorail_fixture_binary': pin(monorail_binary),
        'run_url': args.run_url, 'run_id': run_id(args.run_url), 'source_files': sources()}
    args.output.mkdir(parents=True)
    for original, name in ((args.directory/'MapServer.exe', 'MapServer.exe'),
                           (args.native_evidence, ANIMATION_FIXTURE), (fixture_binary, ANIMATION_BINARY),
                           (args.monorail_evidence, MONORAIL_FIXTURE), (monorail_binary, MONORAIL_BINARY)):
        shutil.copyfile(original, args.output/name)
    (args.output/BUILD).write_bytes(canonical(value))
    validate_package(args.output, args.repository_commit)
    return value


def validate_package(directory, commit=None):
    directory = Path(directory); value = read_json(directory/BUILD)
    require({p.name for p in directory.iterdir()} == NATIVE_FILES and not any(p.is_symlink() for p in directory.iterdir()),
        'Native startup package member closure differs')
    require(value.get('format') == 1 and value.get('role') == contract.ROLE
        and re.fullmatch(r'[0-9a-f]{40}', str(value.get('repository_commit')))
        and (commit is None or value['repository_commit'] == commit)
        and value.get('source_commit') == contract.SOURCE and value.get('data_commit') == contract.DATA
        and value.get('configuration') == 'OptDebug' and value.get('architecture') == 'Win32'
        and all(value.get(key) is False for key in ('postgresql_persistence_fixture', 'runtime_execution_validated',
            'native_gameplay_validated', 'physical_timing_validated'))
        and value.get('build_targets') == ['MapServer'] and value.get('source_files') == sources()
        and value.get('schema_sources_sha256') == schema_pins()
        and value.get('run_id') == run_id(value.get('run_url')), 'Native startup build source/provenance differs')
    build = value.get('build_input', {})
    require(contract.same(build, source.expected_receipt(build.get('animation_certificate'),
            monorail_build_input=build.get('monorail_build_input'))), 'Native startup staged inputs differ')
    require(file_record(directory/'MapServer.exe') == value.get('files', {}).get('MapServer.exe')
        and pin(directory/ANIMATION_FIXTURE) == value.get('native_fixture')
        and pin(directory/ANIMATION_BINARY) == value.get('native_fixture_binary')
        and pin(directory/MONORAIL_FIXTURE) == value.get('native_monorail_fixture')
        and pin(directory/MONORAIL_BINARY) == value.get('native_monorail_fixture_binary'), 'Native startup package raw bytes differ')
    contract.monorail.retained.pe_record(value['files']['MapServer.exe'])
    validate_animation_fixture(directory/ANIMATION_FIXTURE, build, binary=directory/ANIMATION_BINARY)
    validate_monorail_fixture(directory/MONORAIL_FIXTURE, build, binary=directory/MONORAIL_BINARY)
    return value


def validate_component_inputs(directory, commit=None):
    directory = Path(directory); component = read_json(directory/COMPONENT)
    require(component.get('format') == 1 and component.get('role') == 'qualified_mapserver_startup_component'
        and component.get('status') == 'accepted_native_components_verified'
        and re.fullmatch(r'[0-9a-f]{40}', str(component.get('repository_commit')))
        and (commit is None or component['repository_commit'] == commit)
        and component.get('physical_timing_validated') is False
        and component.get('native_gameplay_validated') is False, 'Accepted component source/status differs')
    native = validate_package(directory/'native', component.get('native_repository_commit'))
    import prepare_server_fx_catalog as fx_producer
    fx = fx_producer.verify_qualification(directory/'fx')
    consumer = fx.get('startup_native_consumer', {})
    require(consumer.get('status') == 'actual_candidate_full_and_compact_private_provider_preloads_verified'
        and consumer.get('repository_commit') == native['repository_commit']
        and consumer.get('previous_control_mapserver') == fx_producer.fx.MAPSERVER
        and contract.pin_record(consumer.get('actual_mapserver')) == contract.pin_record(native['files']['MapServer.exe'])
        and consumer.get('build_manifest') == pin(directory/'native'/BUILD)
        and contract.same(consumer.get('build'), native)
        and consumer.get('pair_stages') == ['startup-full', 'startup-compact']
        and type(consumer.get('native_preload_processes')) is int and consumer['native_preload_processes'] == 2
        and consumer.get('native_id_table_on_candidate_executed') is False
        and consumer.get('physical_timing_validated') is False and consumer.get('native_gameplay_validated') is False,
        'FX qualification did not execute the exact admitted new MapServer consumer')
    producers = component.get('producer_artifacts', {})
    require(contract.same(producers, read_json(MARKER).get('native_component_inputs'))
        and producers.get('status') == 'accepted_native_and_fx_components'
        and producers.get('native', {}).get('repository_commit') == native['repository_commit']
        and producers['native'].get('run_id') == native['run_id']
        and producers.get('fx', {}).get('repository_commit') == fx['repository_commit'],
        'Component accepted artifact producer/source changed')
    for key in ('native', 'fx'):
        row = producers[key]['artifact']
        archive = directory/'component-artifacts'/(key+'.zip')
        require(pin(archive) == {'bytes': row['bytes'], 'sha256': row['sha256']}, 'Accepted component ZIP bytes differ')
        verify_extracted_archive(archive, directory/key)
    require(fx['repository_commit'] == component.get('fx_repository_commit')
        and contract.same(component.get('native_build'), native)
        and contract.same(component.get('fx_qualification'), fx), 'Component native/FX raw proof differs')
    expected_files = {'MapServer.exe': pin(directory/'native/MapServer.exe'), BUILD: pin(directory/'native'/BUILD),
        ANIMATION_FIXTURE: pin(directory/'native'/ANIMATION_FIXTURE), ANIMATION_BINARY: pin(directory/'native'/ANIMATION_BINARY),
        MONORAIL_FIXTURE: pin(directory/'native'/MONORAIL_FIXTURE), MONORAIL_BINARY: pin(directory/'native'/MONORAIL_BINARY),
        fx_producer.fx.PAYLOAD: pin(directory/'fx'/fx_producer.fx.PAYLOAD),
        fx_producer.fx.MANIFEST: pin(directory/'fx'/fx_producer.fx.MANIFEST), fx_producer.REPORT: pin(directory/'fx'/fx_producer.REPORT)}
    require(component.get('files') == expected_files and (directory/MANIFEST).read_bytes() == canonical(component),
        'APK startup manifest does not bind exact native/FX components')
    for name in (fx_producer.fx.PAYLOAD, fx_producer.fx.MANIFEST):
        require(pin(directory/name) == expected_files[name], 'Staged APK FX payload differs: ' + name)
    return component


def patch_game(assets, directory, commit):
    assets, directory = Path(assets), Path(directory)
    component = validate_component_inputs(directory, commit)
    with tarfile.open(assets/'game-package.tar.gz', 'r:gz') as archive:
        entries = archive.getmembers()
        require(all(e.isfile() and '/' not in e.name and '\\' not in e.name for e in entries)
            and len({e.name.casefold() for e in entries}) == len(entries), 'Retained game archive closure differs')
        files = {e.name: archive.extractfile(e).read() for e in entries}
    game = json.loads(files['game-package.json'])
    old = contract.monorail.embedded_receipt(game)
    require(game['native_monorail']['receipt_sha256'] == contract.PREVIOUS_RECEIPT_SHA256
        and old['mapserver']['sha256'] == contract.PREVIOUS_SHA256
        and set(files) == set(game['files']) | {'game-package.json'} and len(game['files']) == 25,
        'Exact .31 station-aware game donor required')
    for name, row in game['files'].items():
        require({'bytes': len(files[name]), 'sha256': hashlib.sha256(files[name]).hexdigest()} == contract.pin_record(row),
            'Retained game member bytes differ: ' + name)
    native = component['native_build']; row = copy.deepcopy(native['files']['MapServer.exe'])
    row['bytes'] = row.pop('size')
    receipt = {'format': 1, 'role': contract.ROLE, 'repository_commit': commit,
        'source_commit': game['source_commit'], 'data_commit': game['data_commit'], 'build_input': native['build_input'],
        'schema_sources_sha256': native['schema_sources_sha256'], 'mapserver': row,
        'previous_mapserver': copy.deepcopy(game['files']['MapServer.exe']),
        'retained_native_files': {n:r for n,r in game['files'].items() if n != 'MapServer.exe'},
        'native_build_repository_commit': native['repository_commit'], 'native_build_manifest': component['files'][BUILD],
        'native_fixture': component['files'][ANIMATION_FIXTURE],
        'native_monorail_fixture': component['files'][MONORAIL_FIXTURE],
        'fx_qualification': component['files']['server-fx-catalog-native-qualification.json'],
        'physical_timing_validated': False, 'native_gameplay_validated': False}
    game['native_map_startup'] = {'receipt': receipt, 'receipt_sha256': contract.canonical_sha(receipt)}
    game['files']['MapServer.exe'] = row
    game['dependency_report'] = dependency_report(game['files'])
    require(not game['dependency_report']['unresolved'], 'New MapServer imports exceed retained native closure')
    contract.embedded_receipt(game)
    files['MapServer.exe'] = (directory/'native/MapServer.exe').read_bytes()
    files['game-package.json'] = canonical(game)
    write_game_archive(assets/'game-package.tar.gz', files)
    return component, game


def runtime_binding(component, game, commit):
    receipt = contract.embedded_receipt(game)
    require(receipt['repository_commit'] == component['repository_commit'] == commit,
        'Runtime startup binding source differs')
    return {'package_manifest_sha256': hashlib.sha256(canonical(game)).hexdigest(),
        'mapserver_progress_producer': contract.progress_contract(game)['producer'],
        'native_map_startup_candidate': True, 'map_startup_packaging_repository_commit': commit,
        'map_startup_native_repository_commit': component['native_repository_commit'],
        'map_startup_native_run_id': component['native_build']['run_id'],
        'map_startup_receipt_sha256': game['native_map_startup']['receipt_sha256'],
        'monorail_contract': receipt['build_input']['monorail_budget']['contract'],
        'map_startup_component_manifest': {'bytes': len(canonical(component)), 'sha256': hashlib.sha256(canonical(component)).hexdigest()}}


def github_json(path):
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    require(token, 'Authenticated accepted component artifact metadata required')
    request = urllib.request.Request('https://api.github.com/repos/Russianranger/coh-android/' + path,
        headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read(4*1024**2 + 1)
    require(len(raw) <= 4*1024**2, 'Component metadata exceeds bound')
    return json.loads(raw)


def accepted_artifact(record, target):
    require(isinstance(record, dict) and set(record) == {'run_id', 'repository_commit', 'artifact'},
        'Strong component producer/run/artifact pin required')
    row = record['artifact']
    require(set(row) == {'id', 'name', 'bytes', 'sha256'} and type(row['id']) is int and row['id'] > 0
        and type(row['bytes']) is int and 0 < row['bytes'] <= MAX_ARCHIVE
        and re.fullmatch(r'[0-9a-f]{64}', str(row['sha256']))
        and type(record['run_id']) is int and record['run_id'] > 0
        and re.fullmatch(r'[0-9a-f]{40}', str(record['repository_commit'])), 'Component artifact identity missing')
    artifact = github_json('actions/artifacts/' + str(row['id']))
    run = github_json('actions/runs/' + str(record['run_id']))
    require(artifact.get('name') == row['name'] and artifact.get('size_in_bytes') == row['bytes']
        and artifact.get('digest') == 'sha256:' + row['sha256'] and artifact.get('expired') is False
        and artifact.get('workflow_run', {}).get('id') == record['run_id']
        and artifact.get('workflow_run', {}).get('head_sha') == record['repository_commit']
        and run.get('head_sha') == record['repository_commit'] and run.get('status') == 'completed'
        and run.get('conclusion') == 'success', 'Component artifact producer did not complete successfully')
    if target.exists():
        require(pin(target) == {'bytes': row['bytes'], 'sha256': row['sha256']}, 'Existing component ZIP differs')
        return
    from build_client_render_queue_apk import authenticated_artifact_download
    previous = os.environ.get('GH_TOKEN')
    if previous is None: os.environ['GH_TOKEN'] = os.environ['GITHUB_TOKEN']
    try:
        authenticated_artifact_download(row['id'], target, {'bytes': row['bytes'], 'sha256': row['sha256']})
    finally:
        if previous is None: os.environ.pop('GH_TOKEN', None)


def extract_artifact(archive_path, directory):
    require(not directory.exists(), 'Fresh component extraction required')
    with zipfile.ZipFile(archive_path) as archive:
        names = set(); total = 0
        for entry in archive.infolist():
            name = entry.filename
            require(not name.startswith('/') and '\\' not in name and ':' not in name
                and all(part not in ('', '.', '..') for part in name.rstrip('/').split('/'))
                and name.casefold() not in names and not entry.flag_bits & 1,
                'Unsafe, duplicate or encrypted component member')
            names.add(name.casefold())
            mode = entry.external_attr >> 16
            require(stat.S_IFMT(mode) in (0, stat.S_IFREG, stat.S_IFDIR), 'Linked or special component member')
            total += entry.file_size
            require(total <= 2*MAX_ARCHIVE and len(names) <= 30000 and entry.file_size <= MAX_ARCHIVE,
                'Component extraction exceeds bound')
        directory.mkdir(parents=True)
        for entry in archive.infolist():
            target = directory/entry.filename
            if entry.is_dir(): target.mkdir(parents=True, exist_ok=True); continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source_stream, target.open('xb') as output:
                shutil.copyfileobj(source_stream, output, 1024*1024)


def verify_extracted_archive(archive_path, directory):
    """Rebind accepted compressed bytes to every actual extracted evidence leaf."""
    with zipfile.ZipFile(archive_path) as archive:
        entries = [entry for entry in archive.infolist() if not entry.is_dir()]
        require({path.relative_to(directory).as_posix() for path in directory.rglob('*') if path.is_file()}
            == {entry.filename for entry in entries}, 'Accepted component extracted member set differs')
        for entry in entries:
            digest = hashlib.sha256()
            with archive.open(entry) as stream:
                for block in iter(lambda: stream.read(1024*1024), b''): digest.update(block)
            require(pin(directory/entry.filename) == {'bytes': entry.file_size, 'sha256': digest.hexdigest()},
                'Accepted component extracted evidence differs: ' + entry.filename)


def stage_inputs(args):
    marker = read_json(args.marker); inputs = marker.get('native_component_inputs')
    require(isinstance(inputs, dict) and inputs.get('format') == 1
        and inputs.get('status') == 'accepted_native_and_fx_components'
        and set(inputs) == {'format', 'status', 'native', 'fx'},
        'Native/FX accepted artifact pins are not ready; refuse unqualified publication')
    require(re.fullmatch(r'[0-9a-f]{40}', args.repository_commit), 'Exact APK source commit required')
    if (args.output/COMPONENT).exists():
        return validate_component_inputs(args.output, args.repository_commit)
    require(not args.output.is_symlink(), 'Component staging directory is linked')
    args.output.mkdir(parents=True, exist_ok=True)
    downloads = args.output/'component-artifacts'; downloads.mkdir(exist_ok=True)
    for key in ('native', 'fx'):
        archive = downloads/(key + '.zip')
        accepted_artifact(inputs[key], archive)
        if (args.output/key).exists(): verify_extracted_archive(archive, args.output/key)
        else: extract_artifact(archive, args.output/key)
    native = validate_package(args.output/'native', inputs['native']['repository_commit'])
    import prepare_server_fx_catalog as fx_producer
    fx = fx_producer.verify_qualification(args.output/'fx')
    require(fx['repository_commit'] == inputs['fx']['repository_commit'], 'FX source differs from accepted artifact owner')
    files = {'MapServer.exe': pin(args.output/'native/MapServer.exe'), BUILD: pin(args.output/'native'/BUILD),
        ANIMATION_FIXTURE: pin(args.output/'native'/ANIMATION_FIXTURE), ANIMATION_BINARY: pin(args.output/'native'/ANIMATION_BINARY),
        MONORAIL_FIXTURE: pin(args.output/'native'/MONORAIL_FIXTURE), MONORAIL_BINARY: pin(args.output/'native'/MONORAIL_BINARY),
        fx_producer.fx.PAYLOAD: pin(args.output/'fx'/fx_producer.fx.PAYLOAD),
        fx_producer.fx.MANIFEST: pin(args.output/'fx'/fx_producer.fx.MANIFEST), fx_producer.REPORT: pin(args.output/'fx'/fx_producer.REPORT)}
    value = {'format': 1, 'role': 'qualified_mapserver_startup_component', 'status': 'accepted_native_components_verified',
        'repository_commit': args.repository_commit, 'native_repository_commit': native['repository_commit'],
        'fx_repository_commit': fx['repository_commit'], 'producer_artifacts': inputs,
        'native_build': native, 'fx_qualification': fx, 'files': files,
        'physical_timing_validated': False, 'native_gameplay_validated': False}
    for name in (fx_producer.fx.PAYLOAD, fx_producer.fx.MANIFEST):
        shutil.copyfile(args.output/'fx'/name, args.output/name)
    for name in (COMPONENT, MANIFEST): (args.output/name).write_bytes(canonical(value))
    return validate_component_inputs(args.output, args.repository_commit)


def main():
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest='command', required=True)
    native = commands.add_parser('package')
    for name in ('directory', 'source', 'cache', 'native-evidence', 'monorail-evidence', 'output'):
        native.add_argument('--' + name, required=True, type=Path)
    native.add_argument('--repository-commit', required=True); native.add_argument('--run-url', required=True)
    staged = commands.add_parser('stage-inputs')
    for name in ('marker', 'output'): staged.add_argument('--' + name, required=True, type=Path)
    staged.add_argument('--repository-commit', required=True)
    args = parser.parse_args()
    value = package(args) if args.command == 'package' else stage_inputs(args)
    print(json.dumps({'status': 'native_startup_packaged' if args.command == 'package' else value['status'],
        'repository_commit': value['repository_commit'], 'physical_timing_validated': False}))


if __name__ == '__main__': main()
