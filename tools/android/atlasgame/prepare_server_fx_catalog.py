#!/usr/bin/env python3
"""Produce and qualify an isolated stock-schema server FX projection.

Six fresh native processes establish stock shipping-loader provider reuse,
the full/compact observer's actual native IDs, and the new startup consumer's
full/compact provider plus certified-animation use. The observer is host-only. The
runtime input must be a complete disposable .31 Atlas preparation, never a
player's database or running session. No physical timing is certified.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'android/guest'), str(ROOT/'tools')]
import server_fx_catalog as fx
import prepare_server_fx_catalog_observer_source as source
from package_reference_runtime import file_record

PROJECTION = 'server-fx-projection.json'
BUILD = 'server-fx-observer-native.json'
REPORT = 'server-fx-catalog-native-qualification.json'
CLIENT_CACHES = {'bytes': 27071659, 'sha256': '5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051'}
SOURCES = ('android/guest/server_fx_catalog.py', 'tools/prepare_server_fx_catalog_observer_source.py',
    'tools/android/atlasgame/prepare_server_fx_catalog.py',
    'tools/android/atlasgame/prepare_server_fx_control_fixture.py',
    'tools/android/interactive/qualify_full_startup_preflight.py',
    'tools/android/interactive/qualify_runtime_asset_preflight.py',
    'upstream/ouroboros/Common/fxinfo.c', 'upstream/ouroboros/libs/UtilitiesLib/src/components/StringCache.c',
    'upstream/ouroboros/libs/UtilitiesLib/src/utils/textparser.c', 'android/native/server-cache-launcher.c')
STAGES = ('shipping-full','shipping-compact','observer-full','observer-compact','startup-full','startup-compact')
STARTUP_STAGES = ('startup-full','startup-compact')
ANIMATION_PIG = {'bytes':97084456,'sha256':'465d69a266f2b07afd800b8a7bd3f5e63fa16a24955391f826264d7f8d3a968b'}
require, pin, canonical = fx.require, fx.caches.file_pin, fx.canonical


def write(path, value): Path(path).write_bytes(canonical(value))
def read(path): return json.loads(Path(path).read_bytes(), object_pairs_hook=fx.caches.unique_object)
def source_pins(): return {n: pin(ROOT/n) for n in SOURCES}


def startup_package_module():
    sys.path.insert(0,str(ROOT/'tools/android/interactive'))
    import package_map_startup_native as package
    return package


def validate_startup_native(directory, commit=None):
    package = startup_package_module()
    build = package.validate_package(Path(directory),commit)
    retained = build.get('build_input',{}).get('retained_sources_sha256',{})
    require(all(retained.get(name) == digest for name,digest in fx.RETAINED_FX_SOURCES.items()),
            'Startup native consumer changed the qualified FX source/parser')
    record = build['files']['MapServer.exe']
    require({'bytes':record.get('bytes',record.get('size')),'sha256':record['sha256']} != fx.MAPSERVER,
            'Startup candidate must be its actual separately compiled MapServer')
    return build


def validate_startup_consumer(report, directory):
    """Require the actual new compiled consumer, not inferred stock-PE behavior."""
    package = startup_package_module(); directory = Path(directory)
    build = validate_startup_native(directory,report.get('repository_commit'))
    value = report.get('startup_native_consumer',{})
    record = build['files']['MapServer.exe']
    require(isinstance(value,dict) and value.get('format') == 1
        and value.get('status') == 'actual_candidate_full_and_compact_private_provider_preloads_verified'
        and value.get('repository_commit') == report.get('repository_commit')
        and value.get('previous_control_mapserver') == fx.MAPSERVER
        and value.get('actual_mapserver') == {'bytes':record.get('bytes',record.get('size')),'sha256':record['sha256']}
        and value.get('build_manifest') == pin(directory/package.BUILD) and value.get('build') == build
        and value.get('retained_fx_sources') == fx.RETAINED_FX_SOURCES
        and value.get('pair_stages') == list(STARTUP_STAGES) and value.get('native_preload_processes') == 2
        and value.get('native_id_table_on_candidate_executed') is False
        and value.get('physical_timing_validated') is False and value.get('native_gameplay_validated') is False
        and isinstance(report.get('providers'),dict) and set(report['providers']) == set(STAGES)
        and isinstance(value.get('animation_fastpath'),dict) and set(value['animation_fastpath']) == set(STARTUP_STAGES),
        'Both actual startup native full/compact consumer proofs and exact PE/source binding are required')
    return value


def validate_control_fixture(value):
    require(value.get('format') == 1 and value.get('role') == 'complete_prepared_public_031_native_fx_control'
        and value.get('status') == 'prepared' and value.get('donor_apk') == {
            'bytes':41203812,'sha256':'e56df1bcf2210aff131ba80189b1b2dee760f27066e3ee26e09c5fea1654ad80'}
        and value.get('source_commit') == '74fe247be85173e618f1af2c8af71b1316de4cd8'
        and value.get('mapserver') == fx.MAPSERVER and value.get('fx') == fx.BASE
        and value.get('native_processes_started') is False and value.get('live_sql_started') is False
        and value.get('player_database_used') is False
        and value.get('cache_cleanup_prerequisites_stubbed_no_native_processes_started') is True
        and value.get('source_script') == pin(ROOT/'tools/android/atlasgame/prepare_server_fx_control_fixture.py'),
        'Complete .31 host control fixture source/identity/scope differs')
    imported = value.get('original_import',{}); preparation = value.get('atlas_preparation',{})
    require(imported.get('files') == 173011 and imported.get('bytes') == 2977730517
        and imported.get('all_leaf_sha256_checked') is True and imported.get('android_import_service_executed') is False
        and preparation.get('private_data_files',0) >= 173011 and preparation.get('private_data_bytes',0) >= 2977730517
        and preparation.get('cache_reused') is False and preparation.get('native_mapserver') == fx.MAPSERVER
        and preparation.get('animation_installed') is True and preparation.get('animation_count') == 5878
        and preparation.get('graph_status') == 'installed_verified_graph'
        and preparation.get('prepared_cache_status') in ('installed','preserved_existing_native_caches'),
        'Complete cold Atlas/original import control preparation did not pass')
    return value


def build_projection(args):
    require(fx.caches.HEX40.fullmatch(args.repository_commit), 'Exact projection source commit required')
    require(pin(args.client_caches) == CLIENT_CACHES, 'Exact external client cache payload required')
    require(not args.output.exists(), 'Fresh projection output required')
    with zipfile.ZipFile(args.client_caches) as archive:
        require(len(archive.namelist()) == len(set(archive.namelist())), 'Duplicate client cache entry')
        full = archive.read(fx.TARGET)
    compact, identity = fx.project(full)
    args.output.mkdir(parents=True)
    (args.output/fx.PAYLOAD).write_bytes(compact)
    value = {'format': 1, 'role': 'unaccepted_server_fx_projection_candidate',
        'repository_commit': args.repository_commit, 'base': fx.BASE, 'projected': fx.PROJECTED,
        'client_caches': CLIENT_CACHES, 'identity': identity, 'native_qualification': False,
        'source_files': source_pins(), 'client_fx_changed': False, 'shipping_native_changed': False}
    write(args.output/PROJECTION, value)
    return value


def validate_projection(directory):
    directory = Path(directory); value = read(directory/PROJECTION)
    require(value.get('format') == 1 and value.get('role') == 'unaccepted_server_fx_projection_candidate'
        and value.get('base') == fx.BASE and value.get('projected') == fx.PROJECTED
        and value.get('client_caches') == CLIENT_CACHES and value.get('source_files') == source_pins()
        and value.get('native_qualification') is False and value.get('shipping_native_changed') is False
        and value.get('client_fx_changed') is False and fx.caches.HEX40.fullmatch(str(value.get('repository_commit'))),
        'Projection candidate source/identity differs')
    require(pin(directory/fx.PAYLOAD) == fx.PROJECTED
            and fx.inspect((directory/fx.PAYLOAD).read_bytes())['identity'] == value['identity'], 'Projection candidate differs')
    return value


def package_observer(args):
    require(fx.caches.HEX40.fullmatch(args.repository_commit) and not args.output.exists(), 'Fresh exact observer build required')
    build = read(args.source/source.RECEIPT)
    require(build == source.expected(), 'Host-only observer source receipt differs')
    require({n: hashlib.sha256((args.source/n).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
             for n in build['patched_sha256']} == build['patched_sha256'], 'Compiled observer sources differ')
    require(re.findall(r'^COH_PG_PERSISTENCE_TESTS:BOOL=(.*)$', args.cache.read_text(encoding='utf-8-sig'), re.M) == ['OFF'],
            'Observer must exclude PostgreSQL shipping-fixture instrumentation')
    record = file_record(args.directory/'MapServer.exe')
    require(record.get('pe_machine') == 0x14c, 'Observer must be Win32 PE')
    executable = (args.directory/'MapServer.exe').read_bytes()
    require(all(marker in executable for marker in (source.ENVIRONMENT.encode(), b'COH_FX_NATIVE_IDS_V1',
            b'COH_HOST_ONLY_FX_IDS_COMPLETE_V1')), 'Observer binary lacks host-only observation markers')
    args.output.mkdir(parents=True)
    shutil.copyfile(args.directory/'MapServer.exe', args.output/'MapServer.exe')
    value = {'format': 1, 'role': 'host_only_server_fx_catalog_observer', 'shipping_executable': False,
        'repository_commit': args.repository_commit, 'build_input': build,
        'files': {'MapServer.exe': record}, 'source_files': source_pins(),
        'cmake_cache': pin(args.cache), 'configuration': 'OptDebug', 'build_targets': ['MapServer']}
    write(args.output/BUILD, value)
    return value


def validate_observer(directory):
    directory = Path(directory); value = read(directory/BUILD)
    require(set(p.name for p in directory.iterdir()) == {BUILD, 'MapServer.exe'}
        and value.get('format') == 1 and value.get('role') == 'host_only_server_fx_catalog_observer'
        and value.get('shipping_executable') is False and value.get('configuration') == 'OptDebug'
        and value.get('build_targets') == ['MapServer'] and value.get('build_input') == source.expected()
        and value.get('source_files') == source_pins()
        and file_record(directory/'MapServer.exe') == value.get('files',{}).get('MapServer.exe'),
        'Nonshipping native observer identity differs')
    return value


def parse_native_ids(path, names):
    require(pin(path)['bytes'] <= 4*1024**2, 'Native FX ID report exceeds bound')
    lines = Path(path).read_text(encoding='ascii').splitlines()
    require(lines[0] == 'COH_FX_NATIVE_IDS_V1\t19607\t19606\t4cb7d9cb\t1'
            and lines[-1] == 'COH_FX_NATIVE_DONE_V1' and len(lines) == 19608, 'Native FX header/completion differs')
    entries = []; unique = {}
    for name in names: unique.setdefault(name.casefold(), name)
    expected = [unique[n] for n in sorted(unique)]
    for index, line in enumerate(lines[1:-1], 1):
        fields = line.split('\t')
        require(fields == [str(index), expected[index-1], str(index)], 'Native FX ID/name/roundtrip differs')
        entries.append({'id': index, 'name': fields[1]})
    return {'indexed_names': len(entries), 'native_schema_crc': '4cb7d9cb',
            'ordered_native_ids_sha256': hashlib.sha256(canonical(entries)).hexdigest(), 'report': pin(path)}


def native_observer():
    spec = importlib.util.spec_from_file_location('fx_stock_cache_observer', ROOT/'tools/android/atlasgame/prepare_server_caches.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def fx_source_providers(runtime, base):
    import atlas_beacon_package as atlas
    context = type('Context', (), {'check': lambda self: None})()
    logical = ['data/'+row['path'] for row in base['envelope']['dependencies']]
    targets = atlas.actual_targets(runtime, logical, context)
    providers = {}
    for name, path in targets.items():
        require(path.is_file(), 'Original FX dependency missing: '+name)
        resolved = str(path.resolve(strict=True))
        require(resolved not in providers, 'Ambiguous FX source provider')
        providers[resolved] = name
    return providers


def provider_receipt(trace_paths, runtime, providers, expected, observer):
    """Inspect actual FD targets, including canonical imported symlink targets."""
    # Runtime was proved real and absolute at execution. This exact canonical
    # pathname also permits evidence verification after disposable trees retire.
    target = str(Path(runtime)/fx.TARGET)
    source_reads = {}; reads = writes = 0; trace_pins = {}; total = 0
    for path in sorted(trace_paths):
        total += path.stat().st_size; require(total <= observer.MAX_TRACE, 'FX provider trace exceeds bound')
        trace_pins[path.name] = pin(path)
        for line in observer.completed_trace_lines(path):
            match = re.search(r'\b(read|pread64|write|pwrite64)\(\d+<([^>]*)>.*\)\s*=\s*(\d+)(?:\s|$)', line)
            if match:
                operation, opened, amount = match.groups(); amount = int(amount)
                if not amount: continue
                if opened == target:
                    if operation in ('read','pread64'): reads += amount
                    else: writes += amount
                elif opened in providers and operation in ('read','pread64'):
                    source_reads[providers[opened]] = source_reads.get(providers[opened],0)+amount
            if re.search(r'\bmmap(?:2)?\(', line) and 'PROT_READ' in line and re.search(r'\)\s*=\s*0x',line):
                for opened in re.findall(r'\d+<([^>]*)>',line):
                    require(opened not in providers, 'Mapped FX source fallback was used')
            if re.search(r'\b(?:rename|renameat|renameat2|unlink|unlinkat)\(', line) and re.search(r'\)\s*=\s*0(?:\s|$)',line):
                require(target not in line, 'Native process replaced the private FX BIN')
    require(trace_pins and reads >= expected['bytes'] and writes == 0 and not source_reads,
            'Native FX provider proof missed the BIN, rewrote it or read original FX text')
    return {'format': 1, 'actual_private_fx_provider': target, 'provider': expected,
        'successful_fd_content_bytes': reads, 'cache_writes': writes, 'fx_source_content_reads': source_reads,
        'trace_files': trace_pins, 'private_provider_verified': True}


def animation_fastpath_receipt(stdout, trace_paths, runtime, observer):
    """Prove actual compiled certificate use and its opened immutable PIG bytes.

    Counters describe the observed loaded subset, not all 5,878 tracks, MapServer
    gameplay, physical device performance or the full startup target.
    """
    fields = ('opened','certified','fallback','crypto_failed','raw_bytes','hash_us','stock_us',
              'skipped_rot_keys','skipped_pos_keys','scanned_rot_keys','scanned_pos_keys')
    rows = []
    for line in re.findall(rb'COH_ANIM_CERT_V1 [^\r\n]*',stdout):
        parts = line.decode('ascii').split()[1:]
        require(all('=' in part for part in parts), 'Animation native counter field differs')
        pairs = [part.split('=',1) for part in parts]
        value = dict(pairs)
        require(len(value) == len(pairs) and set(value) == {'schema','pack',*fields}
            and value['schema'] == '1' and value['pack'] == ANIMATION_PIG['sha256']
            and all(re.fullmatch(r'0|[1-9][0-9]*',value[key]) for key in fields), 'Animation native counter identity differs')
        row = {key:int(value[key]) for key in fields}
        require(all(0 <= row[key] < 2**64 for key in fields) and 0 < row['opened'] <= 1000000
            and row['certified'] + row['fallback'] == row['opened'] and row['crypto_failed'] == 0,
            'Animation native counter bounds/certificate accounting differs')
        if rows: require(all(row[key] >= rows[-1][key] for key in fields), 'Animation native counters regressed')
        rows.append(row)
    require(rows and rows[-1]['certified'] > 0 and rows[-1]['raw_bytes'] >= rows[-1]['certified']*596
        and rows[-1]['skipped_rot_keys'] + rows[-1]['skipped_pos_keys'] > 0,
        'Actual startup MapServer did not prove certified-animation key validation skips')
    target = str(Path(runtime)/'piggs/server-animations.pigg'); reads = writes = 0; pins = {}; total = 0
    for path in sorted(trace_paths):
        total += path.stat().st_size; require(total <= observer.MAX_TRACE, 'Animation provider trace exceeds bound')
        pins[path.name] = pin(path)
        for line in observer.completed_trace_lines(path):
            match = re.search(r'\b(read|pread64|write|pwrite64)\(\d+<([^>]*)>.*\)\s*=\s*(\d+)(?:\s|$)',line)
            if match and match[2] == target:
                if match[1] in ('read','pread64'): reads += int(match[3])
                else: writes += int(match[3])
            if re.search(r'\b(?:rename|renameat|renameat2|unlink|unlinkat)\(',line) and re.search(r'\)\s*=\s*0(?:\s|$)',line):
                require(target not in line, 'Native startup process replaced its animation PIG')
    require(pins and reads >= rows[-1]['raw_bytes'] and writes == 0,
            'Certified animation counters lacked the actual immutable PIG provider read proof')
    return {'format':1,'scope':'actual_host_MapServer_loaded_subset_raw_animation_certificate_and_PIG_provider',
        'counter_samples':rows,'latest_counters':rows[-1],'actual_animation_pig_provider':target,
        'pig':ANIMATION_PIG,'successful_fd_content_bytes':reads,'pig_writes':writes,'trace_files':pins,
        'certified_animation_path_observed':True,'whole_inventory_loaded_claimed':False,'physical_timing_validated':False}


def run_ids(args, runtime, environment, output, stage, observer):
    directory = output/'evidence'/stage; directory.mkdir(parents=True)
    ids = directory/'native-ids.tsv'
    env = dict(environment); env[source.ENVIRONMENT] = observer.wine_path(ids)
    command = ['strace','-ff','-yy','-s','128','-o',str(directory/'trace'),'-e',
        'trace=read,pread64,mmap,mmap2,write,pwrite64,openat,close,rename,renameat,renameat2,unlink,unlinkat',
        args.wine,str(runtime/'MapServer.exe'),'-nosharedmemory','-tsr2','-assertmode','8256']
    write(directory/'invocation.json', {'stage': stage, 'command': command, 'runtime_host_path': str(runtime),
        'wine_prefix': environment['WINEPREFIX'], 'observer': pin(runtime/'MapServer.exe'),
        'stop': 'host_only_after_stock_fx_registry', 'shipping_execution': False})
    started = time.monotonic()
    with (directory/'stdout.log').open('wb') as out, (directory/'stderr.log').open('wb') as err:
        process = subprocess.Popen(command,cwd=runtime,env=env,stdin=subprocess.DEVNULL,
            stdout=out,stderr=err,start_new_session=True)
        try:
            while process.poll() is None:
                require(time.monotonic()-started < args.timeout_seconds, 'Native FX observer timed out')
                require((directory/'stdout.log').stat().st_size <= observer.MAX_LOG
                    and (directory/'stderr.log').stat().st_size <= observer.MAX_LOG, 'Native FX observer log exceeds bound')
                time.sleep(0.1)
            require(process.wait(timeout=10) == 0, 'Native FX observer failed')
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: os.killpg(process.pid, signal.SIGKILL); process.wait(timeout=5)
    require((directory/'stdout.log').read_bytes().count(b'COH_HOST_ONLY_FX_IDS_COMPLETE_V1') == 1,
            'Native FX observer completion missing/repeated')
    observer.stop_owned_prefix(environment,directory)
    result = {'format': 1, 'exit_code': 0, 'completed_native_ids': True,
        'elapsed_seconds': round(time.monotonic()-started,6), 'native_boot_scope': 'FX_preload_only'}
    write(directory/'phase-receipt.json',result)
    return result


def verify_qualification(directory):
    directory = Path(directory); report = read(directory/REPORT)
    require(report.get('format') == 1 and report.get('status') == fx.QUALIFICATION_STATUS
        and report.get('source_files') == source_pins() and report.get('base') == fx.BASE
        and report.get('projected') == fx.PROJECTED and report.get('shipping_mapserver') == fx.MAPSERVER
        and report.get('shipping_native_changed') is False and report.get('physical_timing_validated') is False
        and report.get('indexed_names') == 19606 and report.get('native_schema_crc') == '4cb7d9cb'
        and report.get('all_native_ids_equal') is True and report.get('private_provider_verified') is True,
        'Native FX qualification identity/scope differs')
    observed = native_observer()
    require(report.get('evidence_files') == observed.evidence_pins(directory), 'Native FX raw evidence changed')
    control = validate_control_fixture(read(directory/'evidence/native-control-fixture.json'))
    require(control == report.get('native_control_fixture'), 'Native control fixture receipt differs')
    projection = validate_projection(directory/'candidate')
    names = fx.inspect((directory/fx.PAYLOAD).read_bytes())['names']
    require(pin(directory/fx.PAYLOAD) == fx.PROJECTED and projection['identity'] == report.get('identity'), 'Qualified FX payload differs')
    build = validate_observer(directory/'observer')
    require(build == report.get('observer_build') and fx.caches.HEX40.fullmatch(str(report.get('repository_commit')))
            and build['repository_commit'] == projection['repository_commit'] == report['repository_commit'],
            'Native observer/qualification source differs')
    startup = validate_startup_consumer(report,directory/'startup-native')
    ids = [parse_native_ids(directory/'evidence'/stage/'native-ids.tsv',names)
           for stage in ('observer-full','observer-compact')]
    require(ids == report.get('native_ids') and ids[0]['ordered_native_ids_sha256'] == ids[1]['ordered_native_ids_sha256'],
            'Native FX IDs changed')
    providers = read(directory/'evidence/source-providers.json')
    for stage in STAGES:
        expected = fx.PROJECTED if stage.endswith('compact') else fx.BASE
        evidence = directory/'evidence'/stage; phase = read(evidence/'phase-receipt.json')
        invocation = read(evidence/'invocation.json'); runtime = Path(invocation['runtime_host_path'])
        result = provider_receipt(evidence.glob('trace.*'), runtime, providers, expected, observed)
        require(result == read(evidence/'fx-provider-receipt.json') and result == report['providers'][stage],
                'Native FX actual provider receipt differs')
        cleanup = read(evidence/'wine-helpers-stop.json')
        require(cleanup.get('status') == 'prefix_server_lock_unheld'
                and cleanup.get('normal_launcher_exit_observed_first') is True, 'Owned native FX cleanup was not verified')
        identifiers = read(evidence/'identifier-snapshots.json')
        require(identifiers.get('before') == identifiers.get('after') and identifiers.get('before'),
                'Native FX preload altered or omitted identifier evidence')
        require(read(evidence/'fx-payload-snapshots.json') == {'before': expected, 'after': expected},
                'Native FX payload changed during execution')
        native_snapshot = read(evidence/'native-executable-snapshots.json')
        native_pin = (startup['actual_mapserver'] if stage.startswith('startup') else
                      pin(directory/'observer/MapServer.exe') if stage.startswith('observer') else fx.MAPSERVER)
        require(native_snapshot == {'before':native_pin,'after':native_pin}, 'Native FX executable bytes changed')
        if not stage.startswith('observer'):
            actual = observed.phase_receipt((evidence/'stdout.log').read_bytes(),(evidence/'stderr.log').read_bytes(),
                stage,invocation['session_id'],phase['launcher_exit_code'],True)
            require(all(phase.get(k) == v for k,v in actual.items()), 'Shipping/candidate FX preload failed')
        else:
            require(phase.get('exit_code') == 0 and phase.get('completed_native_ids') is True
                and (evidence/'stdout.log').read_bytes().count(b'COH_HOST_ONLY_FX_IDS_COMPLETE_V1') == 1,
                'Host-only FX observation failed')
        if stage.startswith('startup'):
            animation = animation_fastpath_receipt((evidence/'stdout.log').read_bytes(),
                evidence.glob('trace.*'),runtime,observed)
            require(animation == read(evidence/'animation-fastpath-receipt.json')
                    and animation == startup['animation_fastpath'][stage]
                    and read(evidence/'animation-pig-snapshots.json') == {'before':ANIMATION_PIG,'after':ANIMATION_PIG},
                    'Actual startup certificate/PIG consumer proof changed')
    manifest, _ = fx.verify_package(directory)
    require(manifest['repository_commit'] == report['repository_commit'] and manifest['identity'] == report['identity']
            and manifest['native_qualification']['report'] == pin(directory/REPORT),
            'APK-owned FX manifest is not bound to accepted native qualification')
    require(manifest['native_qualification']['startup_native_consumer'] == {
        'mapserver':startup['actual_mapserver'],'build_manifest':startup['build_manifest'],'preload_processes':2,
        'normal_full_and_compact_preloads':True,'private_provider_verified':True,
        'certified_animation_path_observed':True,'physical_timing_validated':False},
        'APK-owned FX manifest does not bind the actually executed startup native consumer')
    return report


def qualify(args):
    require(fx.caches.HEX40.fullmatch(args.repository_commit) and 30 <= args.timeout_seconds <= 3600,
            'Invalid exact FX qualification source/timeout')
    projection = validate_projection(args.projection); build = validate_observer(args.observer_directory)
    startup_build = validate_startup_native(args.startup_native_directory,args.repository_commit)
    control = validate_control_fixture(read(args.control_fixture))
    require(projection['repository_commit'] == build['repository_commit'] == args.repository_commit,
            'Projection/native observer sources must match the qualification commit')
    require(pin(args.runtime/'MapServer.exe') == fx.MAPSERVER and pin(args.runtime/fx.TARGET) == fx.BASE,
            'Complete prepared .31 Atlas runtime with original FX/shipping MapServer required')
    require(args.runtime.is_dir() and not args.runtime.is_symlink() and not args.work.exists() and not args.output.exists(),
            'Fresh disposable host FX qualification required')
    args.work = args.work.resolve(); args.output = args.output.resolve(); args.runtime = args.runtime.resolve()
    args.work.mkdir(parents=True); args.output.mkdir(parents=True); (args.output/'evidence').mkdir()
    require(str(args.runtime) == control['runtime_host_path'], 'Native control runtime path differs')
    write(args.output/'evidence/native-control-fixture.json',control)
    shutil.copytree(args.projection,args.output/'candidate'); shutil.copytree(args.observer_directory,args.output/'observer')
    shutil.copytree(args.startup_native_directory,args.output/'startup-native')
    shutil.copyfile(args.projection/fx.PAYLOAD,args.output/fx.PAYLOAD)
    full = (args.runtime/fx.TARGET).read_bytes(); base = fx.inspect(full)
    providers = fx_source_providers(args.runtime,base); write(args.output/'evidence/source-providers.json',providers)
    observed = native_observer(); launcher = args.output/'evidence/server-cache-launcher.exe'
    with (args.output/'evidence/launcher-build.log').open('wb') as log:
        subprocess.run(['i686-w64-mingw32-gcc','-O2','-Wall','-Wextra','-Werror','-static-libgcc',
            str(ROOT/'android/native/server-cache-launcher.c'),'-o',str(launcher)],check=True,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    environment = dict(os.environ,WINEARCH='win32',WINEPREFIX=str(args.work/'wine-prefix'),WINEDEBUG='-all',
        WINEDLLOVERRIDES='winemenubuilder.exe=d;mscoree=d;mshtml=d',TZ='UTC',LANG='C.UTF-8')
    environment.pop(source.ENVIRONMENT,None)
    with (args.output/'evidence/wine-initialization.log').open('wb') as log:
        subprocess.run([args.wine,'wineboot','--init'],env=environment,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    initialized = args.output/'evidence/prefix-initialization'; initialized.mkdir()
    observed.stop_owned_prefix(environment,initialized,normal_launcher_exit_observed_first=False)
    # New source changes are bounded to the typed animation/station supplement;
    # its DLL/PE closure must remain that of this exact original control runtime.
    old_record = file_record(args.runtime/'MapServer.exe'); candidate_record = startup_build['files']['MapServer.exe']
    require(candidate_record['imports'] == old_record['imports']
        and candidate_record['delay_imports'] == old_record['delay_imports'], 'Startup native imports exceed retained control closure')
    candidate_pin = pin(args.startup_native_directory/'MapServer.exe')
    proofs = {}; ids = []; animations = {}
    for stage in STAGES:
        runtime = args.work/stage
        shutil.copytree(args.runtime,runtime,symlinks=True)
        require(not (runtime/'piggs/texts.pigg').exists(), 'FX proof requires original development-mode freshness checks')
        expected = fx.PROJECTED if stage.endswith('compact') else fx.BASE
        if stage.endswith('compact'):
            target = runtime/fx.TARGET; require(not target.is_symlink(), 'Private host FX BIN required')
            target.chmod(0o600); target.write_bytes((args.projection/fx.PAYLOAD).read_bytes())
            os.utime(target,ns=(fx.caches.EPOCH*10**9,)*2)
        if stage.startswith('observer'):
            (runtime/'MapServer.exe').chmod(0o600)
            shutil.copyfile(args.observer_directory/'MapServer.exe',runtime/'MapServer.exe')
        if stage.startswith('startup'):
            (runtime/'MapServer.exe').chmod(0o600)
            shutil.copyfile(args.startup_native_directory/'MapServer.exe',runtime/'MapServer.exe')
            require(pin(runtime/'piggs/server-animations.pigg') == ANIMATION_PIG, 'Original prepared server animation PIG required')
        before = fx.caches.identifier_snapshot(runtime/'data')
        native_before = pin(runtime/'MapServer.exe')
        if not stage.startswith('observer'):
            observed.run_phase(args,runtime,launcher,environment,args.output,stage,projection['identity'],trace=True)
        else:
            run_ids(args,runtime,environment,args.output,stage,observed)
            ids.append(parse_native_ids(args.output/'evidence'/stage/'native-ids.tsv',base['names']))
        after = fx.caches.identifier_snapshot(runtime/'data')
        require(before == after and pin(runtime/fx.TARGET) == expected and pin(runtime/'MapServer.exe') == native_before,
                'Native FX qualification altered identifiers or private FX bytes')
        write(args.output/'evidence'/stage/'identifier-snapshots.json', {'before':before,'after':after})
        write(args.output/'evidence'/stage/'fx-payload-snapshots.json', {'before':expected,'after':pin(runtime/fx.TARGET)})
        write(args.output/'evidence'/stage/'native-executable-snapshots.json', {'before':native_before,'after':pin(runtime/'MapServer.exe')})
        proof = provider_receipt((args.output/'evidence'/stage).glob('trace.*'),runtime,providers,expected,observed)
        write(args.output/'evidence'/stage/'fx-provider-receipt.json',proof); proofs[stage] = proof
        if stage.startswith('startup'):
            require(pin(runtime/'piggs/server-animations.pigg') == ANIMATION_PIG, 'Native startup process altered its animation PIG')
            animation = animation_fastpath_receipt((args.output/'evidence'/stage/'stdout.log').read_bytes(),
                (args.output/'evidence'/stage).glob('trace.*'),runtime,observed)
            write(args.output/'evidence'/stage/'animation-fastpath-receipt.json',animation); animations[stage] = animation
            write(args.output/'evidence'/stage/'animation-pig-snapshots.json', {'before':ANIMATION_PIG,'after':ANIMATION_PIG})
    require(ids[0]['ordered_native_ids_sha256'] == ids[1]['ordered_native_ids_sha256'], 'Compact FX changed native IDs')
    report = {'format':1,'status':fx.QUALIFICATION_STATUS,'repository_commit':args.repository_commit,
        'base':fx.BASE,'projected':fx.PROJECTED,'identity':projection['identity'],'shipping_mapserver':fx.MAPSERVER,
        'observer_build':build,'native_control_fixture':control,'native_ids':ids,'providers':proofs,
        'indexed_names':19606,'native_schema_crc':'4cb7d9cb',
        'all_native_ids_equal':True,'private_provider_verified':True,'shipping_native_changed':False,
        'physical_timing_validated':False,'source_files':source_pins(),'evidence_files':observed.evidence_pins(args.output)}
    package = startup_package_module()
    report['startup_native_consumer'] = {'format':1,
        'status':'actual_candidate_full_and_compact_private_provider_preloads_verified',
        'repository_commit':args.repository_commit,'previous_control_mapserver':fx.MAPSERVER,
        'actual_mapserver':candidate_pin,'build_manifest':pin(args.startup_native_directory/package.BUILD),
        'build':startup_build,'retained_fx_sources':fx.RETAINED_FX_SOURCES,'pair_stages':list(STARTUP_STAGES),
        'native_preload_processes':2,'native_id_table_on_candidate_executed':False,
        'animation_fastpath':animations,'physical_timing_validated':False,'native_gameplay_validated':False}
    write(args.output/REPORT,report)
    manifest = {'format':1,'role':fx.ROLE,'repository_commit':args.repository_commit,'base':fx.BASE,'projected':fx.PROJECTED,
        'native_mapserver':fx.MAPSERVER,'identity':projection['identity'],'client_fx_changed':False,'physical_timing_validated':False,
        'native_qualification':{'status':fx.QUALIFICATION_STATUS,'report':pin(args.output/REPORT),'indexed_names':19606,
            'native_schema_crc':'4cb7d9cb','all_native_ids_equal':True,'private_provider_verified':True,'shipping_native_changed':False,
            'startup_native_consumer':{'mapserver':candidate_pin,'build_manifest':report['startup_native_consumer']['build_manifest'],
                'preload_processes':2,'normal_full_and_compact_preloads':True,'private_provider_verified':True,
                'certified_animation_path_observed':True,'physical_timing_validated':False}}}
    write(args.output/fx.MANIFEST,manifest); verify_qualification(args.output)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='command',required=True)
    projection = sub.add_parser('projection')
    for n in ('client-caches','output'): projection.add_argument('--'+n,type=Path,required=True)
    projection.add_argument('--repository-commit',required=True)
    package = sub.add_parser('package-observer')
    for n in ('directory','source','cache','output'): package.add_argument('--'+n,type=Path,required=True)
    package.add_argument('--repository-commit',required=True)
    qualification = sub.add_parser('qualify')
    for n in ('runtime','control-fixture','observer-directory','startup-native-directory','projection','work','output'):
        qualification.add_argument('--'+n,type=Path,required=True)
    qualification.add_argument('--repository-commit',required=True); qualification.add_argument('--wine',default='wine')
    qualification.add_argument('--timeout-seconds',type=int,default=1800)
    verify = sub.add_parser('verify'); verify.add_argument('--directory',required=True,type=Path)
    args = p.parse_args()
    result = {'projection':build_projection,'package-observer':package_observer,'qualify':qualify,
              'verify':lambda a:verify_qualification(a.directory)}[args.command](args)
    print(json.dumps({'status':result.get('status',result.get('role')),'projected':fx.PROJECTED}))


if __name__ == '__main__': main()
