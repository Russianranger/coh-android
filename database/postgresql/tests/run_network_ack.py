#!/usr/bin/env python3
"""Exercise real fixture-OFF DbServer/MapServer container ACKs on disposable PG.

MapServer runs its stock -dbquery path before game definitions/maps load. The
query-mode ACK diagnostic proves a packet reached its normal receive handler;
exit code zero alone never establishes success. Private work holds credentials.
Only --output is publishable. Single and bounded two-ID MiningAccumulator
requests are tested; this does not validate character persistence or gameplay.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import time

import run_generated_schema as schema
from run_generated_schema import (ROOT, accepted_inputs, catalog_snapshot, collect_logs,
                                  initialize, make_private_directory, payload, payload_hash,
                                  private_config, private_write, query_json, redact, require,
                                  sha256, validate_catalog, LOG_LIMIT, is_failure_line,
                                  benign_catalog_notices)

SUCCESS = 'normal_network_ack_commit_order_passed_gameplay_unvalidated'
MARKER = 'COH_DBQUERY_CONTAINER_ACK'
ACK = re.compile(r'^COH_DBQUERY_CONTAINER_ACK list=(\d+) callback=(\d+) count=(\d+) id=(\d+)\r?$', re.M)
TABLE = 'miningaccumulator'
LIST_ID = 23
DB_PORT = 6997


def ack_records(text):
    return [dict(zip(('list', 'callback', 'count', 'id'), map(int, match))) for match in ACK.findall(text)]


def require_ack(text, exit_code, expected_id=None):
    values = ack_records(text)
    require(exit_code == 0 and len(values) == 1, 'Query must exit cleanly with exactly one received ACK')
    value = values[0]
    require(value['list'] == LIST_ID and value['callback'] == 0 and value['count'] == 1 and value['id'] > 0,
            'Received ACK has wrong list, callback, count or ID')
    require(expected_id is None or value['id'] == expected_id, 'Received ACK ID differs from request')
    require(not any(is_failure_line(line) for line in text.splitlines()), 'Successful query emitted failure diagnostics')
    return value


def require_batch_ack(text, exit_code, identifiers):
    values = ack_records(text)
    require(exit_code == 0 and len(values) == 2 and len(set(identifiers)) == 2,
            'Batch query must exit cleanly with exactly two received ACK records')
    require(all(v['list'] == LIST_ID and v['callback'] == 0 and v['count'] == 2 for v in values) and
            sorted(v['id'] for v in values) == sorted(identifiers), 'Batch ACK count/IDs differ from request')
    require(not any(is_failure_line(line) for line in text.splitlines()), 'Batch query emitted failure diagnostics')
    return values


def require_no_ack(text):
    require(MARKER not in text, 'Received an ACK before commit or after a failed write')


def fixture_source_contract(root=ROOT):
    header = schema.without_comments((root / 'upstream/ouroboros/Common/comm_backend.h').read_text())
    match = re.search(r'typedef enum\s*\{(.*?)\}\s*ContainerType', header, re.S)
    require(match is not None, 'Missing container enumeration')
    members = [entry.strip() for entry in match[1].split(',') if entry.strip()]
    require(members[0] == 'CONTAINER_TESTDATABASETYPES = 0' and
            members[LIST_ID] == 'CONTAINER_MININGACCUMULATOR' and
            all('=' not in entry for entry in members[1:]), 'Reviewed container list ID changed')
    source = (root / 'upstream/ouroboros/DBServer/src/dbinit.c').read_text()
    require('containerListRegister(CONTAINER_MININGACCUMULATOR,"MiningAccumulator",sizeof(DbContainer),0,0,0)' in source,
            'Fixture container registration changed')
    require('tpltUpdateSqlcolumns(mineacc_list->tplt)' in source, 'Fixture template is not SQL backed')
    return {'list_id': LIST_ID, 'table': TABLE, 'field': 'name', 'containers_per_single_request': 1, 'containers_per_batch_request': 2}


def fixture_text(value):
    require(re.fullmatch(r'[a-z0-9_]{1,48}', value), 'Unsafe test fixture value')
    return f'Name "{value}"\n'


def service_config(original, fragment):
    text = private_config(original, fragment)
    # All changes apply only to the newly created disposable runtime.
    settings = {'assertmode': 'AssertMode Exit', 'nostats': 'NoStats 1',
                'donotlaunchbeaconmasterserver': 'DoNotLaunchBeaconMasterServer 1',
                'donotlaunchbeaconclients': 'DoNotLaunchBeaconClients 1',
                'donotlaunchmapservertsr': 'DoNotLaunchMapServerTSR 1',
                'disablecontainerbackups': 'DisableContainerBackups 1'}
    lines = [line for line in text.splitlines()
             if not line.split() or line.split()[0].lower() not in settings]
    return '\n'.join(lines + list(settings.values())) + '\n'


def new_paths(runtime, reference, work, output, root):
    for path in (work, output):
        require(not path.exists() and not path.is_symlink(), 'Work and output directories must be new')
        require(path not in (runtime, reference, root.resolve()) and runtime not in path.parents and
                reference not in path.parents and (root / 'upstream').resolve() not in path.parents,
                'Output overlaps protected input')
    require(work != output and work not in output.parents and output not in work.parents,
            'Private work and public evidence must be separate')


class Process:
    """File-backed output avoids inherited-pipe hangs and bounds each subprocess."""
    def __init__(self, command, cwd, logs, label, *, env=None, interactive=False):
        self.label, self.started = label, time.monotonic()
        self.stdout, self.stderr = logs / (label + '-stdout.log'), logs / (label + '-stderr.log')
        self.handles = [self.stdout.open('xb'), self.stderr.open('xb')]
        options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
        try:
            self.child = subprocess.Popen(command, cwd=cwd, env=env,
                stdin=subprocess.PIPE if interactive else subprocess.DEVNULL,
                stdout=self.handles[0], stderr=self.handles[1], **options)
        except Exception:
            self.close()
            raise
        self.forced_stop = False

    def text(self):
        self.check_bounds()
        return '\n'.join(p.read_text(encoding='utf-8', errors='replace') for p in (self.stdout, self.stderr))

    def check_bounds(self):
        require(all(p.stat().st_size <= LOG_LIMIT for p in (self.stdout, self.stderr)),
                'Process output exceeded capture bound: ' + self.label)

    def poll(self):
        self.check_bounds()
        return self.child.poll()

    def wait(self, timeout):
        deadline = time.monotonic() + timeout
        while self.poll() is None:
            require(time.monotonic() < deadline, 'Process timed out: ' + self.label)
            time.sleep(0.1)
        return self.child.returncode

    def send(self, text):
        require(self.child.poll() is None and self.child.stdin is not None, 'Interactive process exited')
        self.child.stdin.write(text.encode('utf-8'))
        self.child.stdin.flush()

    def stop(self):
        if self.child.poll() is None:
            self.forced_stop = True
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(self.child.pid), '/T', '/F'],
                               capture_output=True, timeout=30, check=False)
            else:
                os.killpg(self.child.pid, signal.SIGTERM)
            try:
                self.child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.child.kill()
                self.child.wait(timeout=10)
        self.close()

    def close(self):
        for handle in self.handles:
            handle.close()
        child = getattr(self, 'child', None)
        if child is not None and child.stdin is not None:
            child.stdin.close()

    def record(self):
        return {'label': self.label, 'exit_code': self.child.poll(), 'forced_stop': self.forced_stop,
                'elapsed_seconds': round(time.monotonic() - self.started, 3)}


def observe_ack(process, timeout, expected_id=None, batch_ids=None):
    """Return as soon as flushed receive diagnostics arrive, before disconnect."""
    deadline = time.monotonic() + timeout
    wanted = 2 if batch_ids is not None else 1
    while True:
        text = process.text()
        if len(ack_records(text)) >= wanted:
            values = (require_batch_ack(text, 0, batch_ids) if batch_ids is not None
                      else require_ack(text, 0, expected_id))
            return values, time.monotonic()
        require(process.poll() is None, 'Query exited without the required received ACK')
        require(time.monotonic() < deadline, 'Timed out waiting for received ACK')
        time.sleep(0.05)


def engine_bounds(runtime):
    for path in runtime.rglob('*.log'):
        require(not path.is_symlink() and path.stat().st_size <= LOG_LIMIT, 'Internal engine log exceeded capture bound')


def wait_for(predicate, processes, runtime, timeout, description):
    deadline = time.monotonic() + timeout
    while True:
        for process in processes:
            require(process.poll() is None, 'Process exited while waiting for ' + description + ': ' + process.label)
        engine_bounds(runtime)
        result = predicate()
        if result:
            return result
        require(time.monotonic() < deadline, 'Timed out waiting for ' + description)
        time.sleep(0.1)


def pg_environment(cluster):
    env = {key: value for key, value in os.environ.items() if not key.startswith('PG')}
    env.update(PGHOST='127.0.0.1', PGPORT=str(cluster.meta['port']), PGUSER='coh_game',
               PGDATABASE=cluster.meta['database'], PGPASSFILE=str(cluster.root / 'pgpass'),
               PGCONNECT_TIMEOUT='10', PGAPPNAME='coh_ack_lock_holder')
    return env


def read_row(cluster, identifier):
    require(type(identifier) is int and identifier > 0, 'Invalid row ID')
    return query_json(cluster, f"SELECT coalesce(json_agg(x),'[]'::json) FROM (SELECT containerid,name FROM dbo.{TABLE} WHERE containerid={identifier}) x;")


def require_row(cluster, identifier, value):
    actual = read_row(cluster, identifier)
    require(actual == [{'containerid': identifier, 'name': value}], 'Independent SQL row differs after protocol ACK')
    return actual


def waiting_writers(cluster):
    return query_json(cluster, f"""SELECT coalesce(json_agg(x),'[]'::json) FROM (
        SELECT a.pid,a.wait_event_type,a.wait_event,a.state,left(a.query,1024) AS query
        FROM pg_stat_activity a
        WHERE a.datname=current_database() AND a.usename='coh_game'
          AND EXISTS (SELECT 1 FROM pg_locks l WHERE l.pid=a.pid AND NOT l.granted)
          AND lower(a.query) LIKE '%{TABLE}%' AND a.query ~* '(UPDATE|INSERT)'
          AND a.wait_event_type='Lock' AND a.state='active') x;""")


def failure_trigger_sql():
    # Deferred trigger fails COMMIT itself after the row UPDATE was executed.
    return f"""CREATE FUNCTION dbo.coh_network_ack_reject() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.name = 'network_commit_failure' THEN
    RAISE EXCEPTION 'COH_NETWORK_ACK_EXPECTED_COMMIT_FAILURE' USING ERRCODE='42501';
  END IF;
  RETURN NEW;
END; $$;
CREATE CONSTRAINT TRIGGER coh_network_ack_failure AFTER UPDATE ON dbo.{TABLE}
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION dbo.coh_network_ack_reject();"""


def run(runtime, schema_report, reference, work, output, pg_bin, driver,
        port=15435, timeout=300, root=ROOT, schema_archive=None):
    runtime, reference, work, output = [Path(p).resolve() for p in (runtime, reference, work, output)]
    new_paths(runtime, reference, work, output, root)
    require(30 <= timeout <= 1800, 'Timeout must be between 30 and 1800 seconds')
    contract = fixture_source_contract(root)
    files, expected, attrs, optional, package, binaries, hashes = accepted_inputs(
        runtime, Path(schema_report), reference, root, Path(schema_archive) if schema_archive else None)
    require(TABLE in expected and 'name' in expected[TABLE], 'Missing generated fixture table/column')
    require(MARKER.encode() in binaries['MapServer.exe'].read_bytes(),
            'Reference MapServer lacks the reviewed real ACK receive diagnostic; rebuild reference runtime')
    original_config = files['data/server/db/servers.cfg'][1].read_text()
    service_config(original_config, '')
    # No accidental connection to an existing local game service.
    with socket.socket() as probe:
        probe.settimeout(1)
        require(probe.connect_ex(('127.0.0.1', DB_PORT)) != 0, 'DbServer port is already occupied')
    make_private_directory(work)
    output.mkdir(parents=True)
    isolated, logs = work / 'runtime', work / 'raw-logs'
    isolated.mkdir()
    logs.mkdir()
    report = {'status': 'normal_network_ack_validation_failed', 'source_commit': schema.generation.SOURCE_COMMIT,
              'data_commit': schema.generation.DATA_COMMIT, 'schema_report_sha256': sha256(Path(schema_report)),
              'reference_repository_commit': package['repository_commit'],
              'dbserver_sha256': hashes['DbServer.exe'], 'mapserver_sha256': hashes['MapServer.exe'],
              'scope': 'Normal fixture-OFF DbServer and MapServer dbquery over loopback, disposable PostgreSQL',
              'contract': contract, 'phases': [], 'failures': [], 'input_sha256': {}, 'optional_inputs': optional,
              'multi_container_batch_validated': False, 'batch_atomicity': 'not promised; individual container writes use separate transactions',
              'character_persistence_validated': False,
              'gameplay_validated': False, 'asset_complete_mapserver_startup_validated': False,
              'console_capture_limit': 'DbServer may reopen CONOUT$; require client receive diagnostics plus independent SQL, lock and fatal-worker evidence',
              'started_utc': datetime.now(timezone.utc).isoformat()}
    cluster, service, processes, secrets = None, None, [], []

    def start(command, label, **kwargs):
        process = Process(command, isolated, logs, label, **kwargs)
        processes.append(process)
        return process

    def client(label, identifier, value):
        fixture = work / (label + '.txt')
        private_write(fixture, fixture_text(value))
        return start([str(isolated / 'MapServer.exe'), '-nogui', '-db', '127.0.0.1',
                      '-dbquery', '-set', str(LIST_ID), str(identifier), str(fixture),
                      '-timeout', str(int(timeout * 1000))], label)

    def batch_client(identifiers):
        fixtures = []
        for index, value in enumerate(('network_batch_first', 'network_batch_second')):
            fixture = work / f'batch-{index}.txt'
            private_write(fixture, fixture_text(value))
            fixtures.append(fixture)
        return start([str(isolated / 'MapServer.exe'), '-nogui', '-db', '127.0.0.1',
                      '-dbquery', '-timeout', str(int(timeout * 1000)), '-setbatch', str(LIST_ID),
                      str(identifiers[0]), str(fixtures[0]), str(identifiers[1]), str(fixtures[1])], 'blocked-batch')

    def start_service(label):
        running = start([str(isolated / 'DbServer.exe'), '-start', '0'], label)
        def startup_ready():
            # Legacy console redirection may hide Ready. A listening socket and
            # complete SQL schema permit the first request; only its actual
            # received ACK proves that the normal network loop serviced it.
            with socket.socket() as probe:
                probe.settimeout(0.2)
                if probe.connect_ex(('127.0.0.1', DB_PORT)) != 0:
                    return False
            catalog = catalog_snapshot(cluster)
            actual = {}
            for row in catalog['columns']:
                actual.setdefault(row['table_name'], []).append(row['column_name'])
            return actual == expected
        wait_for(startup_ready, [running], isolated, timeout, 'listening DbServer and complete generated SQL schema')
        report['phases'].append({'name': label + '_startup_gate',
            'captured_ready_diagnostic': 'DbServer Ready.' in running.text(),
            'listening_loopback_port': DB_PORT, 'generated_schema_matches': True,
            'protocol_readiness_proof': 'Requires subsequent received CONTAINER_ACK; socket/schema alone do not prove readiness'})
        return running

    def positive_phase(label, identifier, value):
        process = client(label, identifier, value)
        ack, observed = observe_ack(process, timeout, identifier if identifier > 0 else None)
        rows = require_row(cluster, ack['id'], value)
        sql_delay = round(time.monotonic() - observed, 4)
        process.wait(timeout)
        require_ack(process.text(), process.child.returncode, ack['id'])
        require(service.poll() is None, 'DbServer exited after positive request')
        report['phases'].append({'name': label, 'ack': ack, 'committed_row': rows[0],
                                 'sql_check_after_ack_observation_seconds': sql_delay, 'process': process.record()})
        return ack['id']

    try:
        for name, source in files.values():
            report['input_sha256'][name] = payload_hash(source)
            if name != 'data/server/db/servers.cfg':
                target = isolated / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload(source))
        for name, path in binaries.items():
            if name in ('DbServer.exe', 'MapServer.exe') or name.lower().endswith('.dll'):
                shutil.copy2(path, isolated / name)
        cluster = initialize(work / 'pg', pg_bin, port, 'coh_network_ack', driver)
        secrets = list(cluster.secrets.values())
        private_write(isolated / 'data/server/db/servers.cfg', service_config(
            original_config, (cluster.root / 'dbserver-postgresql.cfg').read_text()))
        require(not catalog_snapshot(cluster)['columns'], 'Disposable dbo schema was not initially empty')
        service = start_service('dbserver-initial')
        identifier = positive_phase('create', -1, 'network_initial')
        second_id = positive_phase('create-second', -1, 'network_second')
        require(second_id != identifier, 'Distinct creates returned the same ID')
        # Stock -set TEMPLOAD requires the generic container not already cached
        # unlocked. Restart after the ACK/independent committed-row check.
        service.stop()
        report['phases'].append({'name': 'intentional_service_restart_after_commit', 'process': service.record(),
                                 'reason': 'Clear stock generic container cache before TEMPLOAD modify'})
        service = start_service('dbserver-restarted')
        require_row(cluster, identifier, 'network_initial')
        positive_phase('modify', identifier, 'network_modified')

        holder = start([str(Path(cluster.meta['bin']) / 'psql'), '-X', '-q', '-A', '-t', '-v', 'ON_ERROR_STOP=1'],
                       'lock-holder', env=pg_environment(cluster), interactive=True)
        holder.send(f"BEGIN; SELECT containerid FROM dbo.{TABLE} WHERE containerid={second_id} FOR UPDATE; SELECT 'COH_ACK_LOCK_HELD';\n")
        wait_for(lambda: 'COH_ACK_LOCK_HELD' in holder.text(), [holder, service], isolated, timeout, 'test SQL lock')
        blocked = batch_client((identifier, second_id))

        def prove_wait():
            require_no_ack(blocked.text())
            return waiting_writers(cluster)

        waiters = wait_for(prove_wait, [blocked, holder, service], isolated, timeout, 'DbServer writer blocked by PostgreSQL lock')
        require(all(re.search(r'\b(?:UPDATE|INSERT)\b', row['query'], re.I) for row in waiters),
                'Observed lock wait is not a container write')
        blocked_start = time.monotonic()
        while time.monotonic() - blocked_start < 2:
            require(blocked.poll() is None and service.poll() is None and holder.poll() is None,
                    'A process exited while commit was blocked')
            require_no_ack(blocked.text())
            engine_bounds(isolated)
            time.sleep(0.1)
        require_row(cluster, second_id, 'network_second')
        hold_seconds = round(time.monotonic() - blocked_start, 3)
        holder.send('COMMIT;\n\\q\n')
        require(holder.wait(30) == 0, 'SQL lock release failed')
        acks, observed = observe_ack(blocked, timeout, batch_ids=(identifier, second_id))
        rows = require_row(cluster, identifier, 'network_batch_first') + require_row(cluster, second_id, 'network_batch_second')
        sql_delay = round(time.monotonic() - observed, 4)
        blocked.wait(timeout)
        require_batch_ack(blocked.text(), blocked.child.returncode, (identifier, second_id))
        report['phases'].append({'name': 'batch_ack_waits_for_all_commits', 'acks': acks, 'committed_rows': rows,
            'observed_waiting_writers': waiters, 'no_ack_while_write_blocked_seconds': hold_seconds,
            'sql_check_after_ack_observation_seconds': sql_delay,
            'process': blocked.record(), 'lock_holder': holder.record()})
        report['multi_container_batch_validated'] = True

        positive_text, _ = collect_logs(isolated, logs, output, secrets)
        report['pre_injection_benign_catalog_notices'] = benign_catalog_notices(positive_text)
        positive_errors = [line[:1500] for line in positive_text.splitlines() if is_failure_line(line)]
        require(not positive_errors, 'Unexpected pre-injection failure diagnostics: ' + '\n'.join(positive_errors[:20]))
        cluster.sql(failure_trigger_sql(), user='coh_game', database=cluster.meta['database'])
        rejected = client('deferred-commit-failure', identifier, 'network_commit_failure')
        deadline = time.monotonic() + min(timeout, 90)
        while service.poll() is None:
            require_no_ack(rejected.text())
            engine_bounds(isolated)
            require(time.monotonic() < deadline, 'DbServer failed to stop after permanent commit failure')
            time.sleep(0.1)
        require(service.child.returncode == 3, 'Expected fail-closed DbServer exit 3')
        fatal_text, records = collect_logs(isolated, logs, output, secrets)
        require(re.search(r'PG_FIFO_FAILED[^\r\n]*SQLSTATE=42501', fatal_text),
                'Missing expected permanent SQL commit failure evidence')
        require('COH_NETWORK_ACK_EXPECTED_COMMIT_FAILURE' in fatal_text,
                'Failure did not originate from the injected deferred constraint trigger')
        try:
            rejected.wait(min(timeout, 30))
        except ValueError as error:
            require('Process timed out:' in str(error), str(error))
            rejected.stop()  # Service is already gone, so no later ACK is possible.
        require_no_ack(rejected.text())
        unchanged = require_row(cluster, identifier, 'network_batch_first')
        report['phases'].append({'name': 'failed_commit_no_ack_and_rollback', 'sqlstate': '42501',
            'trigger': 'DEFERRABLE INITIALLY DEFERRED AFTER UPDATE', 'committed_row': unchanged[0],
            'received_ack_count': 0, 'client': rejected.record(), 'service': service.record()})
        report['status'] = SUCCESS
    except (OSError, ValueError, RuntimeError, AssertionError, subprocess.SubprocessError) as error:
        report['failures'].append(redact(str(error), secrets))
    finally:
        for process in reversed(processes):
            try:
                process.stop()
            except Exception as error:
                report['failures'].append('Process cleanup: ' + redact(str(error), secrets))
        if cluster is not None:
            try:
                cluster.stop()
            except Exception as error:
                report['failures'].append('Cluster shutdown: ' + redact(str(error), secrets))
        try:
            text, records = collect_logs(isolated, logs, output, secrets)
            report['redacted_logs'] = records
            report['benign_catalog_notices'] = benign_catalog_notices(text)
        except Exception as error:
            report['failures'].append('Log capture: ' + redact(str(error), secrets))
        if report['failures']:
            report['status'] = 'normal_network_ack_validation_failed'
        report['processes'] = [process.record() for process in processes]
        report['finished_utc'] = datetime.now(timezone.utc).isoformat()
        (output / 'network-ack-report.json').write_text(redact(json.dumps(report, indent=2) + '\n', secrets), encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--schema-report', type=Path, required=True)
    parser.add_argument('--schema-archive', type=Path)
    parser.add_argument('--reference-binaries', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--bin', required=True)
    parser.add_argument('--driver', default='PostgreSQL Unicode')
    parser.add_argument('--port', type=int, default=15435)
    parser.add_argument('--timeout-seconds', type=float, default=300)
    args = parser.parse_args()
    report = run(args.runtime, args.schema_report, args.reference_binaries, args.work,
                 args.output, args.bin, args.driver, args.port, args.timeout_seconds,
                 schema_archive=args.schema_archive)
    print(report['status'])
    return 0 if report['status'] == SUCCESS else 1


if __name__ == '__main__':
    sys.exit(main())
