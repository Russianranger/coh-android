#!/usr/bin/env python3
"""Opt-in genuine Win32 catalog capture on a disposable GitHub-hosted Linux shard.

Uses exact published .31 Atlas assets, exact .34 manual DbServer, fresh isolated
PostgreSQL, a fresh Wine prefix and the already admitted nonshipping MapServer.
It never opens a player profile or changes the source fixture. A matching footer
is reported separately from unproved physical Thor generation provenance.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import struct
import subprocess
import sys
import time
import zipfile
import delivery as d

ROOT = d.ROOT
MAX_FILES, MAX_BYTES = 350000, 12 * 1024**3
MAX_LOG = 8 * 1024**2
EXPECTED = {'files': 508, 'active_roots': 33, 'definitions_crc': 3173822562,
            'references_crc': 3649375123}
ODBC_SHA256 = '1b1c85f694ecad95fd3a0125a8b071669772bef098366738de48812124896773'
SOURCE_PATHS = ('native-android/engine/scenecatalog-server/capture_disposable.py',
                'native-android/engine/scenecatalog-server/delivery.py',
                'native-android/engine/scenecatalog/validate_file.c',
                'native-android/engine/scenecatalog/coh_scenecatalog.c',
                'native-android/engine/scenecatalog/coh_scenecatalog.h',
                'native-android/engine/scenegraph/coh_scenegraph.c',
                'native-android/engine/scenegraph/coh_scenegraph.h',
                'native-android/engine/replication/coh_groups.c',
                'native-android/engine/replication/coh_replication.c',
                'native-android/engine/replication/coh_replication.h',
                'native-android/engine/replication/coh_groups.h', 'native-android/engine/coh_contracts.h',
                'tools/android/atlasgame/prepare_server_fx_catalog.py',
                'tools/android/atlasgame/prepare_server_fx_control_fixture.py',
                'tools/android/interactive/qualify_minimal_db_runtime.py',
                'database/postgresql/pg_local.py', 'database/postgresql/001-coh-compat.sql',
                'android/guest/dbserver_diagnostic.py', 'android/guest/game_diagnostic.py',
                'android/guest/game_evidence.py', 'android/guest/diagnostic.py',
                'android/native/runtime-probe.c',
                'tools/package_reference_runtime.py')


def windows_path(value):
    value = str(Path(value).resolve())
    d.require(value.startswith('/') and ':' not in value and '\\' not in value, 'WINDOWS_PATH')
    return 'Z:' + value.replace('/', '\\')


def pins():
    return {name: d.hash_file(ROOT / name, 8 * 1024**2)[1] for name in SOURCE_PATHS}


def inventory(root, destination=None):
    """Bounded content inventory; optional dereferenced copy to NEW private tree."""
    root = Path(root)
    if destination is not None:
        destination.mkdir(mode=0o700)
    count, total, identity = 0, 0, hashlib.sha256()
    for base, dirs, files in os.walk(root, followlinks=False):
        dirs.sort(); files.sort()
        for name in dirs:
            d.require(not (Path(base) / name).is_symlink(), 'LINKED_DIRECTORY')
        for name in files:
            source = Path(base) / name
            relative = source.relative_to(root).as_posix()
            actual = source.resolve(strict=True)
            d.require(actual.is_file(), 'NONREGULAR_INPUT')
            size = actual.stat().st_size
            count += 1; total += size
            d.require(count <= MAX_FILES and total <= MAX_BYTES and size <= 512 * 1024**2, 'RUNTIME_LIMIT')
            digest = hashlib.sha256()
            target = None
            if destination is not None:
                target = destination / relative
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with actual.open('rb') as stream:
                out = target.open('xb') if target else None
                try:
                    consumed = 0
                    for chunk in iter(lambda: stream.read(d.CHUNK), b''):
                        consumed += len(chunk); d.require(consumed <= size, 'CHANGED_INPUT')
                        digest.update(chunk)
                        if out: out.write(chunk)
                    d.require(consumed == size, 'CHANGED_INPUT')
                finally:
                    if out: out.close()
            if target:
                shutil.copystat(actual, target)
            identity.update(json.dumps([relative, size, digest.hexdigest()], separators=(',', ':')).encode()+b'\n')
    return {'files': count, 'bytes': total, 'ordered_inventory_sha256': identity.hexdigest()}


def fixture_modules():
    sys.path[:0] = [str(ROOT / 'tools/android/interactive'), str(ROOT / 'tools/android/atlasgame'),
                   str(ROOT / 'database/postgresql'), str(ROOT / 'tools')]
    return (importlib.import_module('prepare_server_fx_catalog'),
            importlib.import_module('qualify_minimal_db_runtime'),
            importlib.import_module('pg_local'), importlib.import_module('package_reference_runtime'))


def wine_version(raw):
    value = raw.decode('ascii').strip()
    match = re.fullmatch(r'wine-(\d+)\.(\d+)(?:\.\d+)?(?: \([^\r\n]{1,160}\))?', value)
    d.require(match is not None, 'WINE_VERSION')
    # Wine 9.0 forwards all ODBC through Unix libodbc. Windows driver support
    # entered upstream in 9.13. This is a necessary floor, not qualification.
    d.require(tuple(map(int, match.groups())) >= (9, 13), 'WINE_WINDOWS_ODBC_UNSUPPORTED')
    return value


def dispatch_snapshot(progress, stages):
    if not progress.exists():
        return {'present': False, 'stable': False}
    d.require(progress.is_file() and not progress.is_symlink() and progress.stat().st_size == 4096, 'DISPATCH_FILE')
    with progress.open('rb') as stream:
        first = stream.read(128); stream.seek(0); second = stream.read(128)
    if first != second or len(first) != 128:
        return {'present': True, 'stable': False}
    magic, version, size, pid, tid, seq, stage, loops, flags, count = struct.unpack_from('<8s9I', first)
    if seq == 0 or seq & 1:
        return {'present': True, 'stable': False}
    d.require(magic == b'COHDBP1\0' and version == 1 and size == 128 and pid > 0 and tid > 0
              and str(stage) in stages and count == len(stages) and flags == 0 and not any(first[44:]), 'DISPATCH')
    return {'present': True, 'stable': True, 'process_id': pid, 'thread_id': tid,
            'sequence': seq, 'stage': stage, 'stage_name': stages[str(stage)], 'loop_count': loops}


def dispatch_ready(progress, stages):
    return dispatch_snapshot(progress, stages).get('loop_count', 0) > 0


def postgres_activity(cluster):
    """Read only private aggregate counts; never retain statements or values."""
    database = cluster.meta['database']
    d.require(re.fullmatch('[a-z][a-z0-9_]{0,47}', database) is not None, 'PG_DATABASE')
    query = """SELECT json_build_object('sessions',count(*),'active',
count(*) FILTER(WHERE state='active'),'waiting_locks',count(*) FILTER(WHERE wait_event_type='Lock'),
'schema_ddl',count(*) FILTER(WHERE query ~* '^(create|alter|drop)'))
FROM pg_stat_activity WHERE usename='coh_game' AND datname='%s';""" % database
    env = {k:v for k,v in os.environ.items() if not k.startswith('PG')}
    env.update(PGHOST='127.0.0.1', PGPORT=str(cluster.meta['port']), PGUSER='coh_admin',
               PGDATABASE='postgres', PGPASSFILE=str(cluster.root/'pgpass'), PGCONNECT_TIMEOUT='2',
               PGOPTIONS='-c statement_timeout=2000')
    result = subprocess.run([str(Path(cluster.meta['bin'])/'psql'), '-X', '-q', '-A', '-t',
                             '-v', 'ON_ERROR_STOP=1'], input=query, text=True, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=3)
    d.require(result.returncode == 0 and len(result.stdout) < 1024, 'PG_ACTIVITY')
    value = d.json_object(result.stdout.encode())
    d.require(set(value) == {'sessions','active','waiting_locks','schema_ddl'} and
              all(type(n) is int and 0 <= n <= 1000 for n in value.values()), 'PG_ACTIVITY')
    return dict(value, raw_sql_included=False)


def bounded_logs(paths):
    return sum(len(d.read(path, MAX_LOG)) for path in paths)


def stop_owned(process):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL); process.wait(timeout=10)
    return process.poll() is not None


def process_group_absent(process):
    # Read-only existence check after prefix/PG teardown. Never kill a recycled
    # group ID whose original leader has already exited.
    try:
        os.killpg(process.pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


def cleanup_postgresql(cluster, root, pg_module):
    """Recover only this invocation's new private cluster after partial init."""
    if cluster is None and root.exists():
        # pg.initialize writes both descriptors BEFORE it starts any PG process.
        # An incomplete descriptor set is not silently accepted as cleanup proof.
        d.require((root/'cluster.json').is_file() and (root/'credentials.json').is_file(), 'PG_PARTIAL_INIT')
        cluster = pg_module.Cluster(root)
    if cluster is None:
        return True
    status = cluster.run('pg_ctl', '-D', cluster.root/'data', 'status', check=False)
    d.require(status.returncode in (0, 3), 'PG_STATUS_UNKNOWN')
    if status.returncode == 0:
        cluster.stop()
    after = cluster.run('pg_ctl', '-D', cluster.root/'data', 'status', check=False)
    d.require(after.returncode == 3, 'PG_STILL_RUNNING')
    return True


def sink_observation(raw):
    fields = ('status', 'producer_status', 'failure_file', 'failure_slot', 'files',
              'definitions', 'slots', 'children', 'wire_bytes', 'total_bytes',
              'emitted_bytes', 'written_bytes', 'partial_remaining', 'partial_removed')
    expression = rb'COH_NATIVE_SCENE_CATALOG_V1 ' + b' '.join(name.encode()+rb'=([0-9]+)' for name in fields)
    matches = re.findall(expression, raw)
    d.require(len(matches) <= 1, 'DUPLICATE_SINK')
    if not matches:
        return None
    values = dict(zip(fields, map(int, matches[0])))
    d.require(values['status'] == 1 and values['producer_status'] == 0 and values['partial_remaining'] == 0
              and values['total_bytes'] == values['emitted_bytes'] == values['written_bytes']
              and 48 <= values['written_bytes'] <= d.CATALOG_MAX, 'SINK_FAILED')
    return values


def capture(args):
    d.require(sys.platform == 'linux' and os.geteuid() != 0 and
              os.environ.get('RUNNER_ENVIRONMENT') == 'github-hosted' and
              os.environ.get('GITHUB_REPOSITORY') == 'Russianranger/coh-android', 'ISOLATED_HOST_REQUIRED')
    d.uint(args.generation, nonzero=True)
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
    d.require(d.hash_file(candidate / 'MapServer.exe', 8 * 1024**2)[1] == d.EXPORTER_SHA256 and
              d.digest(d.read(candidate / 'compile-only-receipt.json', d.JSON_MAX)) == d.COMPILE_RECEIPT_SHA256,
              'CANDIDATE')
    validator = d.regular(args.native_validator)
    validator_identity = d.hash_file(validator, 16 * 1024**2)[1]
    work, output = d.absent_directory(args.work), d.absent_directory(args.output)
    d.require(work != output and work not in output.parents and output not in work.parents and
              work not in source.parents and source not in work.parents and
              output not in source.parents and source not in output.parents, 'ISOLATION')
    d.require(shutil.disk_usage(work.parent).free >= 16 * 1024**3, 'DISK_HEADROOM')
    for port, protocol in ((15437, socket.SOCK_STREAM), (6997, socket.SOCK_STREAM),
                           (7000, socket.SOCK_DGRAM), (7001, socket.SOCK_DGRAM)):
        with socket.socket(socket.AF_INET, protocol) as probe: probe.bind(('127.0.0.1', port))
    work.mkdir(mode=0o700); output.mkdir(mode=0o700)
    report = {'schema': 'coh-disposable-native-capture-v1', 'passed': False,
              'source_sha256': source_pins, 'exporter_sha256': d.EXPORTER_SHA256,
              'exporter_source_revision': d.SOURCE_REVISION,
              'orchestration_source_revision': source_revision, 'orchestration_source_tree': source_tree,
              'native_validator_sha256': validator_identity,
              'generation': args.generation, 'control_fixture_sha256': d.hash_file(args.control_fixture, 8 * 1024**2)[1],
              'db_donor': inputs['donor_apk'], 'disposable_db_only': True,
              'player_profile_opened': False, 'accepted_runtime_modified': False,
              'physical_thor_generation_verified': False, 'matching_groups_transaction_captured': False,
              'renderer_authorized': False, 'runtime_executed': False, 'catalog_captured': False,
              'native_decode_completed': False,
              'hard_process_memory_cap_established': False, 'log_limits_polled_not_kernel_enforced': True,
              'historical_thor_footer_matches': False, 'cleanup_verified': False}
    children, handles, logs, secrets = [], [], [], []
    cluster, environment, progress = None, None, None
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
    def run(label, command, cwd, env, timeout):
        child, stdout, stderr = start(label, command, cwd, env)
        end = min(deadline, time.monotonic()+timeout)
        while child.poll() is None:
            health(); d.require(time.monotonic() < end, 'CHILD_TIMEOUT'); time.sleep(.2)
        d.require(child.returncode == 0, 'CHILD_FAILED')
        return stdout, stderr
    try:
        out, err = run('wine-version', [args.wine, '--version'], work, os.environ.copy(), 15)
        report['wine_version'] = wine_version(d.read(out, 1024))
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
        executable = runtime / 'MapServer.exe'; executable.chmod(0o600)
        shutil.copyfile(candidate / 'MapServer.exe', executable)
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
        environment = {k: v for k, v in os.environ.items() if not k.startswith(('PG', 'COH_'))}
        environment.update(WINEARCH='win32', WINEPREFIX=str(work / 'wine-prefix'), WINEDEBUG='-all',
                           WINEDLLOVERRIDES='winemenubuilder.exe=d;mscoree=d;mshtml=d', TZ='UTC', LANG='C.UTF-8')
        run('wineboot', [args.wine, 'wineboot', '--init'], work, environment, 180)
        run('odbc', [args.wine, 'msiexec', '/i', windows_path(installer_path), '/qn', '/norestart'], work, environment, 180)
        out, err = run('odbc-driver', [args.wine, windows_path(probe), '--odbc-driver'], work, environment, 60)
        validation = {'require': d.require, 're': re}
        db.load_functions('android/guest/diagnostic.py', ('validate_odbc_driver',), validation)
        report['odbc_driver'] = validation['validate_odbc_driver'](
            (d.read(out, MAX_LOG)+d.read(err, MAX_LOG)).decode(errors='replace'))
        driver = report['odbc_driver']['driver_name']
        cluster = pg.initialize(work / 'pg', args.pg_bin, 15437, 'coh_catalog_disposable', driver)
        secrets = list(cluster.secrets.values())
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
        captures = work / 'captures'; captures.mkdir(mode=0o700)
        catalog = captures / 'catalog.cohcat'
        map_env = dict(environment, COH_GAME_LOOPBACK_ONLY='1',
                       COH_NATIVE_SCENE_CATALOG_OUTPUT=windows_path(catalog),
                       COH_NATIVE_SCENE_CATALOG_GENERATION=str(args.generation))
        map_process, map_out, map_err = start('map', [args.wine, windows_path(executable),
            '-nogui', '-db', '127.0.0.1', '-nosharedmemory', '-nostats', '-udp', '7001', '-tcp', '0',
            '-map_id', '1', '-donotautogroup'], runtime, map_env)
        sink = None
        while not catalog.exists() or sink is None:
            health(); d.require(process.poll() is None and map_process.poll() is None, 'SERVER_EXITED')
            sink = sink_observation(d.read(map_out, MAX_LOG) + d.read(map_err, MAX_LOG))
            time.sleep(.2)
        d.require(not catalog.with_name(catalog.name+'.partial').exists(), 'PARTIAL_CATALOG')
        listener_policy = importlib.import_module('game_evidence')
        map_text = (d.read(map_out, MAX_LOG)+d.read(map_err, MAX_LOG)).decode(errors='replace')
        report['map_loopback_bindings'] = listener_policy.game_listener_bindings(map_text, 'atlas')
        # Retain successful source output even if downstream native admission fails.
        size, digest = d.hash_file(catalog, d.CATALOG_MAX)
        d.require(size == sink['written_bytes'], 'CAPTURE_SIZE')
        d.copy_verified(catalog, output/'catalog.cohcat', digest, d.CATALOG_MAX)
        report.update(catalog_captured=True, sink=sink, catalog={'bytes': size, 'sha256': digest})
        out, err = run('native-validator', [str(validator), str(catalog), str(args.generation)], work, environment, 120)
        decoded = d.json_object(d.read(out, d.JSON_MAX))
        d.require(decoded.get('native_decode_completed') is True and decoded['generation'] == args.generation
                  and decoded['files'] == sink['files'] and decoded['definitions'] == sink['definitions']
                  and decoded['slots'] == sink['slots'] and decoded['children'] == sink['children']
                  and decoded['input_bytes'] == sink['written_bytes'], 'NATIVE_VALIDATION')
        size, digest = d.hash_file(catalog, d.CATALOG_MAX)
        d.require(d.hash_file(executable, 8*1024**2)[1] == d.EXPORTER_SHA256 and
                  d.hash_file(validator, 16*1024**2)[1] == validator_identity, 'EXECUTABLE_CHANGED')
        report.update(native_decode_completed=True, sink=sink, native_decode=decoded,
                      catalog={'bytes': size, 'sha256': digest},
                      historical_thor_footer_matches=all(decoded[k] == v for k, v in EXPECTED.items()))
        # No full GROUPS receiver ran here. This native export is retained separately.
        d.emit_json(output/'native-validation.json', decoded)
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
            report['source_runtime_unchanged'] = inventory(source) == report.get('source_runtime_inventory')
            cleanup.append(report['source_runtime_unchanged'] and pins() == source_pins)
        except Exception: cleanup.append(False)
        report['cleanup_verified'] = all(cleanup) and bool(cleanup)
        report['passed'] = report['passed'] and report['cleanup_verified']
        report['diagnostics'] = []
        for index, log in enumerate(logs):
            try:
                raw = d.read(log, MAX_LOG)
                text = raw[-256*1024:].decode(errors='replace')
                for secret in secrets: text = text.replace(secret, '[redacted]')
                target = output / ('diagnostic-%02d.txt' % index)
                target.write_text(text)
                report['diagnostics'].append({'file': target.name, 'bytes': target.stat().st_size,
                                              'sha256': d.hash_file(target, MAX_LOG)[1],
                                              'owned_source': log.relative_to(work).as_posix()})
            except Exception: report['passed'] = False
        d.emit_json(output/'capture-receipt.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('runtime', 'control-fixture', 'db-donor-apk', 'candidate-directory',
                 'native-validator', 'pg-bin', 'work', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--generation', type=int, required=True)
    parser.add_argument('--timeout-seconds', type=int, default=2400)
    parser.add_argument('--wine', default='wine'); parser.add_argument('--wineserver', default='wineserver')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        result = capture(args)
        print(json.dumps({k: result[k] for k in ('passed', 'runtime_executed', 'catalog_captured',
             'historical_thor_footer_matches', 'physical_thor_generation_verified', 'matching_groups_transaction_captured')}))
        return 0 if result['passed'] else 2
    except Exception as error:
        print(json.dumps({'passed': False, 'runtime_executed': None,
                          'failure_type': type(error).__name__, 'failure_code': str(error) if isinstance(error,d.Refused) else 'PREFLIGHT_FAILED'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
