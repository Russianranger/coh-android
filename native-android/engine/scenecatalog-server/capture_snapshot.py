#!/usr/bin/env python3
"""One isolated missing-data startup snapshot; never a native/client world session.

Qualified helper boundaries are imported unchanged from capture_disposable.
The orchestration differs only for the new admitted PE, paired startup output,
immutable provenance, and teardown before any offline graph decoding.
"""
from __future__ import annotations
import argparse
import importlib
import json
import os
from pathlib import Path
import re
import secrets as entropy
import shutil
import socket
import struct
import subprocess
import sys
import time
import zipfile
import delivery as d
import build_path_probe as path_probe_builder
import capture_disposable as base
import stage_snapshot as stage
from capture_disposable import (ROOT,MAX_LOG,ODBC_SHA256,fixture_modules,inventory,
    windows_path,capture_destination,validate_path_observation,wine_version,
    bounded_logs,dispatch_ready,dispatch_snapshot,postgres_activity,stop_owned,
    process_group_absent,cleanup_postgresql)
CATALOG_SHA256='61c9408b02e366fa487acc857ffb89cde5d431e7dfcc2b2e01ecd0446bea3763'
SOURCE_PATHS=(*base.SOURCE_PATHS,*('native-android/engine/scenecatalog-server/'+name for name in (
    'source_snapshot.inc','source_snapshot_sink.inc','stage_snapshot.py','record_snapshot_compile.py',
    'admit_snapshot.py','capture_snapshot.py')),'native-android/engine/scenecatalog/source_export.inc')

def pins():
    return {name:d.hash_file(ROOT/name,8*1024**2)[1] for name in SOURCE_PATHS}

def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()

def emit_identity(path,value):
    raw=canonical(value)
    with path.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    return d.digest(raw)

def copy_candidate(source,target,identity):
    """Replace only the private inventory copy, then admit those copied bytes."""
    d.regular(target).chmod(0o600)
    shutil.copyfile(d.regular(source),target)
    d.require(d.hash_file(target,16*1024**2)==(identity['bytes'],identity['sha256']),'COPIED_EXECUTABLE_IDENTITY')

def log_redaction_secrets(cluster,root):
    """Recover this private invocation's secrets even if initialize raised.

    pg_local writes credentials before starting PostgreSQL. An absent private
    directory means initialization never began; any other unverified credential
    state suppresses diagnostic export instead of guessing that logs are safe.
    """
    if cluster is None and not root.exists():return ()
    try:
        values=d.json_object(d.read(root/'credentials.json',4096))
        d.require(set(values)=={'admin','game'} and all(type(v) is str and re.fullmatch('[0-9a-f]{48}',v) for v in values.values()),'LOG_CREDENTIALS')
        if cluster is not None:d.require(cluster.secrets==values,'LOG_CREDENTIALS_CHANGED')
        return tuple(values.values())
    except Exception:
        return None

def redacted_log_tail(log,secrets):
    d.require(secrets is not None,'LOG_REDACTION_UNAVAILABLE')
    raw=d.read(log,MAX_LOG)
    # Redact before truncation: a tail boundary can otherwise retain an
    # unrecognizable password suffix from a failing CREATE ROLE statement.
    for secret in secrets:raw=raw.replace(secret.encode('ascii'),b'[redacted]')
    return raw[-256*1024:].decode(errors='replace')

def verify_candidate(candidate,revision):
    plan=d.json_object(d.read(candidate/'deployment-plan.json',8*1024**2))
    compile_receipt=d.json_object(d.read(candidate/'compile-only-receipt.json',8*1024**2))
    staged=d.json_object(d.read(candidate/stage.RECEIPT,8*1024**2))
    d.require(plan.get('schema')=='coh-runtime-snapshot-candidate-v1' and plan.get('source_revision')==revision and
        plan.get('source_snapshot_only') is True and plan.get('runtime_executed') is False,'CANDIDATE_SCOPE')
    d.require(compile_receipt.get('schema')=='coh-runtime-snapshot-compile-v1' and compile_receipt.get('passed') is True and
        compile_receipt.get('source_revision')==revision and compile_receipt.get('build_role')==stage.ROLE and
        compile_receipt.get('runtime_executed') is False,'COMPILE_SCOPE')
    d.require(d.hash_file(candidate/'MapServer.exe',16*1024**2)==(plan['binary']['bytes'],plan['binary']['sha256']) and
        plan['binary']==compile_receipt['artifacts']['MapServer.exe'],'CANDIDATE_PE')
    d.require(d.hash_file(candidate/'compile-only-receipt.json',8*1024**2)[1]==plan['compile_receipt_sha256'] and
        d.hash_file(candidate/stage.RECEIPT,8*1024**2)[1]==plan['stage_receipt_sha256'],'CANDIDATE_RECEIPTS')
    d.require(staged.get('build_role')==stage.ROLE and staged.get('contract')==stage.CONTRACT and
        staged.get('overlay_sha256')=={name:d.digest(raw) for name,raw in stage.overlays(ROOT).items()} and
        staged.get('stager_sha256')==d.hash_file(Path(stage.__file__),1024**2)[1], 'CANDIDATE_SOURCE')
    return plan

def sink_observation(raw):
    fields=('status','catalog_status','snapshot_status','catalog_bytes','snapshot_bytes','files','slots',
        'definitions','children','root_slots','active_roots','external_count','external_children','defs_crc','refs_crc','partial_remaining')
    expression=rb'COH_RUNTIME_SNAPSHOT_V1 '+b' '.join(name.encode()+rb'=([0-9]+)' for name in fields)
    rows=re.findall(expression,raw);d.require(len(rows)<=1,'DUPLICATE_SINK')
    if not rows:return None
    values=dict(zip(fields,map(int,rows[0])))
    d.require(values['status']==1 and values['catalog_status']==values['snapshot_status']==values['partial_remaining']==0 and
        80<=values['snapshot_bytes']<=16*1024**2 and 48<=values['catalog_bytes']<=d.CATALOG_MAX and
        values['external_count']<=64 and values['root_slots']<=65536,'SINK_FAILED')
    return values

def validate_pair(catalog,snapshot,sink,generation):
    size,sha=d.hash_file(catalog,d.CATALOG_MAX)
    d.require((size,sha)==(12179670,CATALOG_SHA256),'CATALOG_EXACT_EQUALITY')
    side_size,_=d.hash_file(snapshot,16*1024**2)
    with snapshot.open('rb') as stream:head=stream.read(80)
    d.require(len(head)==80 and head[:8]==b'COHRTS01','SNAPSHOT_HEADER')
    fields=struct.unpack('<18I',head[8:])
    d.require(fields[:5]==(1,80,side_size,generation,size) and fields[5:9]==(508,40225,40225,130314) and
        fields[10]==33 and fields[11]<=64 and fields[12:14]==(3173822562,3649375123) and not any(fields[14:]),'SNAPSHOT_CONTEXT')
    d.require(sink['catalog_bytes']==size and sink['snapshot_bytes']==side_size and
        (sink['files'],sink['slots'],sink['definitions'],sink['children'],sink['root_slots'],sink['active_roots'],sink['external_count'],sink['defs_crc'],sink['refs_crc'])==
        (*fields[5:12],*fields[12:14]),'SNAPSHOT_SINK_BINDING')
    return True

def capture(args):
    d.require(sys.platform == 'linux' and os.geteuid() != 0 and
              os.environ.get('RUNNER_ENVIRONMENT') == 'github-hosted' and
              os.environ.get('GITHUB_REPOSITORY') == 'Russianranger/coh-android', 'ISOLATED_HOST_REQUIRED')
    d.require(args.generation == 20261016, 'IMMUTABLE_CATALOG_GENERATION')
    d.require(d.hash_file(args.retained_catalog, d.CATALOG_MAX) == (12179670, CATALOG_SHA256), 'RETAINED_CATALOG')
    d.require(600 <= args.timeout_seconds <= 3600, 'TIMEOUT')
    source_pins = pins()
    source_revision = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()
    source_tree = subprocess.check_output(['git','rev-parse','HEAD^{tree}'], cwd=ROOT, text=True).strip()
    d.require(source_revision == os.environ.get('GITHUB_SHA'), 'ORCHESTRATION_REVISION')
    d.require(subprocess.run(['git','diff','--quiet','HEAD','--',*SOURCE_PATHS],cwd=ROOT).returncode == 0, 'ORCHESTRATION_DIRTY')
    fx, db, pg, pe = fixture_modules()
    fixture = fx.validate_control_fixture(d.json_object(d.read(args.control_fixture, 8 * 1024**2)))
    source = d.path(args.runtime)
    d.require(str(source) == fixture['runtime_host_path'] and source.is_dir(), 'CONTROL_PATH')
    files, schema, dbdoc, inputs = db.donor_inputs(args.db_donor_apk)
    d.require(inputs == db.expected_inputs(), 'DB_DONOR')
    candidate = d.path(args.candidate_directory)
    candidate_plan = verify_candidate(candidate, source_revision)
    exporter_sha256 = candidate_plan['binary']['sha256']
    path_probe = d.regular(args.path_probe)
    path_probe_size, path_probe_identity = d.hash_file(path_probe, 1024**2)
    path_build = d.json_object(d.read(args.path_probe_receipt, d.JSON_MAX))
    path_sources = {name:d.hash_file(Path(__file__).parent/name, 1024**2)[1]
                    for name in ('build_path_probe.py','path_probe.c','source_sink.inc')}
    d.require(path_build.get('schema') == 'coh-win32-catalog-path-build-v1' and
              path_build.get('compiled') is True and path_build.get('read_only') is True and
              path_build.get('source_sha256') == path_sources and
              path_build.get('original_path_functions_sha256') == d.digest(path_probe_builder.original_path_functions(
                  d.read(Path(__file__).parent/'source_sink.inc', 1024**2)).encode()) and
              path_build.get('binary') == {'bytes':path_probe_size,'sha256':path_probe_identity,'machine':'I386','format':'PE32'},
              'PATH_PROBE_IDENTITY')
    work, output = d.absent_directory(args.work), d.absent_directory(args.output)
    d.require(work != output and work not in output.parents and output not in work.parents and
              work not in source.parents and source not in work.parents and
              output not in source.parents and source not in output.parents, 'ISOLATION')
    d.require(shutil.disk_usage(work.parent).free >= 16 * 1024**3, 'DISK_HEADROOM')
    for port, protocol in ((15437, socket.SOCK_STREAM), (6997, socket.SOCK_STREAM),
                           (7000, socket.SOCK_DGRAM), (7001, socket.SOCK_DGRAM)):
        with socket.socket(socket.AF_INET, protocol) as probe: probe.bind(('127.0.0.1', port))
    work.mkdir(mode=0o700); output.mkdir(mode=0o700)
    report = {'schema': 'coh-disposable-runtime-snapshot-v1', 'passed': False,
              'source_sha256': source_pins, 'exporter_sha256': exporter_sha256,
              'exporter_source_revision': source_revision,
              'orchestration_source_revision': source_revision, 'orchestration_source_tree': source_tree,
              'path_probe_sha256': path_probe_identity,
              'path_probe_build_receipt_sha256': d.hash_file(args.path_probe_receipt, d.JSON_MAX)[1],
              'generation': args.generation, 'control_fixture_sha256': d.hash_file(args.control_fixture, 8 * 1024**2)[1],
              'db_donor': inputs['donor_apk'], 'disposable_db_only': True,
              'player_profile_opened': False, 'accepted_runtime_modified': False,
              'physical_thor_generation_verified': False, 'matching_groups_transaction_captured': False,
              'renderer_authorized': False, 'runtime_executed': False, 'catalog_captured': False,
              'native_decode_completed': False, 'runtime_snapshot_captured': False,
              'source_snapshot_only': True, 'live_groups_transaction': False, 'catalog_exact_equality': False,
              'hard_process_memory_cap_established': False, 'log_limits_polled_not_kernel_enforced': True,
              'historical_thor_footer_matches': False, 'cleanup_verified': False}
    children, handles, logs = [], [], []
    cluster, environment, progress = None, None, None
    catalog, snapshot = None, None
    deadline = time.monotonic() + args.timeout_seconds
    def health():
        d.require(time.monotonic() < deadline, 'CAPTURE_TIMEOUT')
        bounded_logs(logs)
    def start(label, command, cwd, env):
        stdout, stderr = work / (label + '-stdout.log'), work / (label + '-stderr.log')
        out, err = stdout.open('xb'), stderr.open('xb'); handles.extend((out, err)); logs.extend((stdout, stderr))
        child = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                 stdout=out, stderr=err, start_new_session=True)
        children.append(child)
        return child, stdout, stderr
    def run(label, command, cwd, env, timeout, expected=0):
        child, stdout, stderr = start(label, command, cwd, env)
        end = min(deadline, time.monotonic()+timeout)
        while child.poll() is None:
            health(); d.require(time.monotonic() < end, 'CHILD_TIMEOUT'); time.sleep(.2)
        d.require(child.returncode == expected, 'CHILD_FAILED')
        return stdout, stderr
    try:
        out, err = run('wine-version', [args.wine, '--version'], work, os.environ.copy(), 15)
        report['wine_version'] = wine_version(d.read(out, 1024))
        environment = {k: v for k, v in os.environ.items() if not k.startswith(('PG', 'COH_'))}
        environment.update(WINEARCH='win32', WINEPREFIX=str(work / 'wine-prefix'), WINEDEBUG='-all',
                           WINEDLLOVERRIDES='winemenubuilder.exe=d;mscoree=d;mshtml=d', TZ='UTC', LANG='C.UTF-8')
        run('wineboot', [args.wine, 'wineboot', '--init'], work, environment, 180)
        catalog, native_catalog_path = capture_destination(work)
        snapshot = catalog.parent/'runtime.cohrts'
        native_snapshot_path = r'C:\coh-native-catalog\runtime.cohrts'
        report['capture_location'] = 'private_wine_c_drive'
        for label, path, admitted in (('private-c', native_catalog_path, True), ('private-sidecar', native_snapshot_path, True), ('unix-root-z', windows_path(catalog), False)):
            out, err = run('path-'+label, [args.wine, windows_path(path_probe), path], work, environment, 30,
                           expected=0 if admitted else 2)
            report['path_probe_'+label] = validate_path_observation(d.read(out, d.JSON_MAX), admitted)
        d.require(d.hash_file(path_probe, 1024**2)[1] == path_probe_identity, 'PATH_PROBE_CHANGED')
        # Dereference into private files: native loader cannot write through to any input.
        runtime = work / 'map-runtime'
        report['source_runtime_inventory'] = inventory(source, runtime)
        db_runtime = work / 'db-runtime'; db_runtime.mkdir(mode=0o700)
        for name, data in files.items():
            target = db_runtime / name; target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
            with target.open('xb') as stream: stream.write(data)
        original = pe.file_record(db_runtime / 'MapServer.exe')
        replacement = pe.file_record(candidate / 'MapServer.exe')
        d.require(original['imports'] == replacement['imports'] and
                  original['delay_imports'] == replacement['delay_imports'], 'PE_DEPENDENCIES')
        executable = runtime / 'MapServer.exe'
        copy_candidate(candidate/'MapServer.exe',executable,candidate_plan['binary'])
        records = {p.name: pe.file_record(p) for p in runtime.iterdir() if p.suffix.lower() in ('.dll', '.exe')}
        closure = pe.dependency_report(records)
        d.require(not closure['unresolved'], 'UNRESOLVED_DEPENDENCIES')
        report['native_dependency_closure_sha256'] = d.digest(json.dumps(closure, sort_keys=True).encode())
        with zipfile.ZipFile(args.db_donor_apk) as archive:
            installer = archive.read('assets/runtime/psqlodbc_x86.msi')
            manifest = d.json_object(archive.read('assets/runtime/runtime-manifest.json'))
            name = 'runtime-probe.exe'
            d.require(0 < archive.getinfo('assets/runtime/'+name).file_size <= 8*1024**2, 'DRIVER_PROBE_SIZE')
            probe_bytes = archive.read('assets/runtime/'+name)
            probe_identity = {'bytes':len(probe_bytes), 'sha256':d.digest(probe_bytes)}
            d.require(probe_identity == manifest['files'][name], 'DRIVER_PROBE_IDENTITY')
            probe = work / name; probe.write_bytes(probe_bytes)
            report['driver_probe'] = dict(probe_identity, exact_admitted_donor=True, rebuilt=False)
        d.require(d.digest(installer) == ODBC_SHA256, 'ODBC_IDENTITY')
        installer_path = work / 'psqlodbc_x86.msi'; installer_path.write_bytes(installer)
        run('odbc', [args.wine, 'msiexec', '/i', windows_path(installer_path), '/qn', '/norestart'], work, environment, 180)
        out, err = run('odbc-driver', [args.wine, windows_path(probe), '--odbc-driver'], work, environment, 60)
        validation = {'require': d.require, 're': re}
        db.load_functions('android/guest/diagnostic.py', ('validate_odbc_driver',), validation)
        report['odbc_driver'] = validation['validate_odbc_driver'](
            (d.read(out, MAX_LOG)+d.read(err, MAX_LOG)).decode(errors='replace'))
        driver = report['odbc_driver']['driver_name']
        cluster = pg.initialize(work / 'pg', args.pg_bin, 15437, 'coh_catalog_disposable', driver)
        config = db_runtime / 'data/server/db/servers.cfg'
        config.write_text(db.guest_config(config.read_text(), cluster.meta['database'],
                                         cluster.connection_string(driver)))
        progress = db_runtime / 'dispatch.bin'
        db_env = dict(environment, COH_WINE_DB_FIXED_INPUTS='1', COH_WINE_DB_LOOPBACK_ONLY='1',
                      COH_WINE_DB_MANUAL_ATLAS='1', COH_WINE_DB_PROGRESS=windows_path(progress))
        process, stdout, stderr = start('db', [args.wine, windows_path(db_runtime/'DbServer.exe'), '-start', '0'], db_runtime, db_env)
        report['runtime_executed'] = True
        db_deadline = min(deadline, time.monotonic()+600)
        while True:
            health(); d.require(process.poll() is None and time.monotonic() < db_deadline, 'DB_NOT_READY')
            text = d.read(stdout, MAX_LOG).decode(errors='replace') + d.read(stderr, MAX_LOG).decode(errors='replace')
            if all(ack in text for ack in (db.FIXED_ACK, db.LOOPBACK_ACK, db.MANUAL_ACK)) and dispatch_ready(progress, dbdoc['wine_build_input']['dispatch_progress']['stages']):
                break
            time.sleep(.2)
        report['db_schema'] = db.schema_snapshot(cluster, schema)
        source_identity = {'schema':'coh-runtime-snapshot-source-v1',
            'exporter_source_revision':source_revision, 'exporter':candidate_plan['binary'],
            'stage_receipt_sha256':candidate_plan['stage_receipt_sha256'],
            'compile_receipt_sha256':candidate_plan['compile_receipt_sha256'],
            'runtime_inventory':report['source_runtime_inventory'], 'native_dependency_closure_sha256':report['native_dependency_closure_sha256'],
            'control_fixture_sha256':report['control_fixture_sha256'], 'db_donor':report['db_donor'],
            'map_id':1, 'map_name':'maps/City_Zones/City_01_01/City_01_01.txt',
            'asset_generation':args.generation, 'retained_catalog_sha256':CATALOG_SHA256,
            'orchestration_source_sha256':source_pins, 'source_snapshot_only':True}
        source_pin = emit_identity(output/'source-identity.json',source_identity)
        run_pin = emit_identity(output/'run-identity.json',{'schema':'coh-runtime-snapshot-run-v1',
            'nonce':entropy.token_hex(32),'source_identity_sha256':source_pin,
            'orchestration_source_revision':source_revision,'orchestration_source_tree':source_tree,
            'db_schema_sha256':d.digest(canonical(report['db_schema'])),
            'private_fresh_wine_prefix':True,'private_fresh_postgresql':True,'player_profile_opened':False})
        report['source_identity_sha256']=source_pin;report['run_identity_sha256']=run_pin
        d.require(d.hash_file(executable,16*1024**2)==(candidate_plan['binary']['bytes'],exporter_sha256),'EXECUTABLE_CHANGED_BEFORE_START')
        map_env = dict(environment, COH_GAME_LOOPBACK_ONLY='1',
                       COH_NATIVE_SCENE_CATALOG_OUTPUT=native_catalog_path,
                       COH_NATIVE_RUNTIME_SNAPSHOT_OUTPUT=native_snapshot_path,
                       COH_NATIVE_SCENE_CATALOG_GENERATION=str(args.generation))
        map_process, map_out, map_err = start('map', [args.wine, windows_path(executable),
            '-nogui', '-db', '127.0.0.1', '-nosharedmemory', '-nostats', '-udp', '7001', '-tcp', '0',
            '-map_id', '1', '-donotautogroup'], runtime, map_env)
        sink = None
        while not catalog.exists() or not snapshot.exists() or sink is None:
            health(); d.require(process.poll() is None and map_process.poll() is None, 'SERVER_EXITED')
            sink = sink_observation(d.read(map_out, MAX_LOG) + d.read(map_err, MAX_LOG))
            time.sleep(.2)
        d.require(not catalog.with_name(catalog.name+'.partial').exists(), 'PARTIAL_CATALOG')
        d.require(not snapshot.with_name(snapshot.name+'.partial').exists(), 'PARTIAL_SNAPSHOT')
        listener_policy = importlib.import_module('game_evidence')
        map_text = (d.read(map_out, MAX_LOG)+d.read(map_err, MAX_LOG)).decode(errors='replace')
        report['map_loopback_bindings'] = listener_policy.game_listener_bindings(map_text, 'atlas')
        # Preserve both real outputs before any downstream matching refusal.
        catalog_size,catalog_digest=d.hash_file(catalog,d.CATALOG_MAX)
        sidecar_size,sidecar_digest=d.hash_file(snapshot,16*1024**2)
        d.copy_verified(catalog,output/'catalog.cohcat',catalog_digest,d.CATALOG_MAX)
        d.copy_verified(snapshot,output/'runtime.cohrts',sidecar_digest,16*1024**2)
        report.update(catalog_captured=True,runtime_snapshot_captured=True,sink=sink,
            catalog={'bytes':catalog_size,'sha256':catalog_digest},snapshot={'bytes':sidecar_size,'sha256':sidecar_digest})
        validate_pair(catalog, snapshot, sink, args.generation)
        d.require(d.hash_file(executable,16*1024**2)==(candidate_plan['binary']['bytes'],exporter_sha256), 'EXECUTABLE_CHANGED')
        report['catalog_exact_equality']=True
        report['historical_thor_footer_matches']=True
        report['passed'] = True
    except Exception as error:
        report['failure_type'] = type(error).__name__
        report['failure_code'] = str(error) if isinstance(error, d.Refused) else 'DEPENDENCY_OR_RUNTIME_FAILURE'
        if progress is not None:
            try: report['db_dispatch_at_failure'] = dispatch_snapshot(progress, dbdoc['wine_build_input']['dispatch_progress']['stages'])
            except Exception as observation: report['db_dispatch_observation_error'] = type(observation).__name__
        if cluster is not None:
            try: report['db_activity_at_failure'] = postgres_activity(cluster)
            except Exception as observation: report['db_activity_observation_error'] = type(observation).__name__
    finally:
        cleanup = []
        for child in reversed(children):
            try: cleanup.append(stop_owned(child))
            except Exception: cleanup.append(False)
        for handle in handles: handle.close()
        if environment:
            # Prefix-specific Wine helper cleanup; never a global wineserver kill.
            wine_cleanup = {'private_fresh_prefix': True, 'kill_exit_code': None, 'wait_exit_code': None}
            try:
                for option, field in (('-k', 'kill_exit_code'), ('-w', 'wait_exit_code')):
                    result = subprocess.run([args.wineserver, option], env=environment,
                                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
                    wine_cleanup[field] = result.returncode
                    cleanup.append(result.returncode == 0)
            except Exception: cleanup.append(False)
            report['wine_prefix_cleanup'] = wine_cleanup
        try: cleanup.append(cleanup_postgresql(cluster, work/'pg', pg))
        except Exception: cleanup.append(False)
        pg_log = work/'pg'/'postgres.log'
        if pg_log.is_file(): logs.append(pg_log)
        groups_deadline = time.monotonic() + 5
        while any(not process_group_absent(child) for child in children) and time.monotonic() < groups_deadline:
            time.sleep(.1)
        report['owned_process_groups_absent'] = all(process_group_absent(child) for child in children)
        cleanup.append(report['owned_process_groups_absent'])
        try:
            report['source_runtime_unchanged'] = (inventory(source) == report['source_runtime_inventory']
                                                if 'source_runtime_inventory' in report else None)
            cleanup.append(report['source_runtime_unchanged'] is not False and pins() == source_pins and
                d.hash_file(args.retained_catalog,d.CATALOG_MAX)==(12179670,CATALOG_SHA256))
        except Exception: cleanup.append(False)
        report['cleanup_verified'] = all(cleanup) and bool(cleanup)
        report['passed'] = report['passed'] and report['cleanup_verified']
        # Failed paired publication can leave one completed file. Preserve it
        # after teardown as unaccepted diagnostic evidence; never mint binding.
        report['retained_failed_outputs'] = []
        if not report['passed']:
            for path,name,limit in ((catalog,'catalog.cohcat',d.CATALOG_MAX),(snapshot,'runtime.cohrts',16*1024**2)):
                if path is None: continue
                for observed,artifact in ((path,name),(path.with_name(path.name+'.partial'),name+'.partial')):
                    try:
                        if observed.is_file() and not (output/artifact).exists():
                            size,digest=d.hash_file(observed,limit)
                            d.copy_verified(observed,output/artifact,digest,limit)
                            report['retained_failed_outputs'].append({'file':artifact,'bytes':size,'sha256':digest,'accepted':False})
                    except Exception:
                        report['failed_output_preservation_error']=True
        report['diagnostics'] = []
        redactions=log_redaction_secrets(cluster,work/'pg')
        report['diagnostics_suppressed_unverified_credentials']=redactions is None
        if redactions is None:report['passed']=False
        for index, log in enumerate(logs if redactions is not None else ()):
            try:
                text = redacted_log_tail(log,redactions)
                target = output / ('diagnostic-%02d.txt' % index)
                target.write_text(text)
                report['diagnostics'].append({'file': target.name, 'bytes': target.stat().st_size,
                                              'sha256': d.hash_file(target, MAX_LOG)[1],
                                              'owned_source': log.relative_to(work).as_posix()})
            except Exception: report['passed'] = False
        d.emit_json(output/'capture-receipt.json', report)
        if report['passed']:
            d.emit_json(output/'snapshot-binding.json',{'schema':'coh-runtime-snapshot-binding-v1',
                'asset_generation':args.generation,'catalog':report['catalog'],'snapshot':report['snapshot'],
                'source_identity':{'file':'source-identity.json','sha256':report['source_identity_sha256']},
                'run_identity':{'file':'run-identity.json','sha256':report['run_identity_sha256']},
                'source_snapshot_only':True,'live_groups_transaction':False,'cleanup_verified':True})
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('runtime','control-fixture','db-donor-apk','candidate-directory','retained-catalog','pg-bin','work','output','path-probe','path-probe-receipt'):
        p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--generation',type=int,required=True);p.add_argument('--timeout-seconds',type=int,default=600)
    p.add_argument('--wine',default='wine');p.add_argument('--wineserver',default='wineserver');a=p.parse_args();os.umask(0o077)
    try:
        result=capture(a);print(json.dumps({k:result[k] for k in ('passed','runtime_executed','runtime_snapshot_captured','catalog_exact_equality','cleanup_verified','source_snapshot_only','live_groups_transaction')}));return 0 if result['passed'] else 2
    except Exception as error:
        print(json.dumps({'passed':False,'failure_type':type(error).__name__,'failure_code':str(error) if isinstance(error,d.Refused) else 'PREFLIGHT_FAILED'}));return 2
if __name__=='__main__':raise SystemExit(main())
