#!/usr/bin/env python3
"""Bounded Atlas Park startup against normal DbServer and disposable PostgreSQL.

Requires a fresh complete runtime AND successful asset-backed template comparison
bound to its original runtime-inputs.json. Reuses only the 56 checked generated
outputs, never caches from template comparison. Stock dbquery status packets prove
DB-confirmed readiness; a console Ready string, live process, or port alone cannot.
A successful run proves this map stayed registered/ready and sent recent stats for
the observation window. It does not prove client login, gameplay or asset coverage.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import socket
import sys
import time
import subprocess

import run_generated_schema as schema
import run_network_ack as network
from run_generated_schema import (ROOT, LOG_LIMIT, is_failure_line, benign_catalog_notices, require, sha256, redact,
    initialize, make_private_directory, private_write, collect_logs, catalog_snapshot,
    validate_catalog, payload)
sys.path.insert(0, str(ROOT / 'tools'))
import compare_reference_templates as comparison
import generate_runtime_data as generation
from prepare_runtime import input_files

SUCCESS = 'atlas_park_protocol_ready_observation_passed_gameplay_unvalidated'
MAP_ID = 1
MAP_PATH = 'maps/City_Zones/City_01_01/City_01_01.txt'
BASE_NAME = 'City_01_01.txt'
MAP_UDP_PORT = 7001
CRITICAL_ASSET = re.compile(r'(?:cannot|can\x27t|could not|couldn\x27t|failed to|unable to)\s+(?:find|open|load|read)\b.*\.(?:geo|anim|texture|pigg|txt)|\bmissing\s+(?:geometry|animation|map|texture)\b', re.I)


def source_map_contract(root=ROOT):
    text = (root / 'upstream/i24/data/server/db/maps.db').read_text()
    matches = re.findall(r'^Container\s+1\s*\n(.*?)^ContainerEnd\s*$', text, re.M | re.S)
    require(len(matches) == 1 and re.search(r'^\s*MapKey\s+atlaspark\s*$', matches[0], re.M) and
            re.search(r'^\s*MapName\s+"' + re.escape(MAP_PATH) + r'"\s*$', matches[0], re.M),
            'Pinned map1 is not the reviewed Atlas Park map')
    require((root / 'upstream/i24/data' / MAP_PATH.lower()).is_file(), 'Pinned Atlas Park map text is missing')
    init = (root / 'upstream/ouroboros/DBServer/src/dbinit.c').read_text()
    mission = (root / 'upstream/ouroboros/DBServer/src/dbmission.c').read_text()
    status = (root / 'upstream/ouroboros/DBServer/src/status.c').read_text()
    require('container->starting        = 1;' in init and 'void dbClientReadyForPlayers' in mission and
            'container->starting    = 0;' in mission and 'if (container->starting)' in status and
            'NotReady 1' in status, 'Reviewed registration/readiness status contract changed')
    return {'map_id': MAP_ID, 'map_key': 'atlaspark', 'map_path': MAP_PATH,
            'status_source': 'DBServer mapStatusCb via DBCLIENT_REQ_CONTAINER_STATUS',
            'ready_transition': 'registerDbClient starting=1; dbClientReadyForPlayers starting=0'}


def parse_status(text, allow_missing=False):
    """Accept only an explicit, unambiguous map1 response from stock dbquery."""
    require(not any(is_failure_line(line) for line in text.splitlines()), 'Status query emitted failure diagnostics')
    missing = [line.strip() for line in text.splitlines() if line.strip() == 'invalid container request']
    require(not missing or allow_missing, 'Requested Atlas Park container is missing')
    matches = re.findall(r'^\s*1\s+(\S+)\s+([^\r\n]+)\r?$', text, re.M)
    if missing:
        require(len(missing) == 1 and not matches, 'Ambiguous missing-container status')
        return {'ready': False, 'not_started': False, 'missing': True, 'raw': missing[0]}
    require(len(matches) == 1, 'Missing or ambiguous Atlas Park status response')
    name, fields = matches[0]
    require(name.replace('\\', '/').split('/')[-1].casefold() == BASE_NAME.casefold(), 'Status response names a different map')
    if 'NotReady' in fields:
        require('NotReady 1' in fields, 'Unrecognized not-ready status')
        return {'ready': False, 'not_started': '(Not started)' in fields, 'raw': matches[0][0] + ' ' + fields}
    ready = re.match(r'S:\s*(\d+)\s*/\s*(\d+)\s+Ip:\s*([0-9.]+):(\d+)\s+Mem:', fields)
    require(ready is not None, 'Unrecognized connected-map status format')
    network_age, stats_age, address, port = ready.groups()
    require(0 < int(port) <= 65535 and len(address.split('.')) == 4 and
            all(part.isdigit() and 0 <= int(part) <= 255 for part in address.split('.')), 'Invalid map endpoint in status')
    return {'ready': True, 'network_age_seconds': int(network_age), 'stats_age_seconds': int(stats_age),
            'address': address, 'port': int(port), 'raw': name + ' ' + fields}


def accept_comparison(report, original_inputs, original_inputs_sha, fresh_inputs, package, hashes, schema_report_sha):
    require(report.get('status') == comparison.SUCCESS and report.get('exit_code') == 0 and
            report.get('failures') == [] and report.get('output_differences') == [] and
            report.get('identical_fresh_output_count') == len(comparison.EXPECTED) and
            report.get('expected_output_count') == len(comparison.EXPECTED) and
            report.get('serializer_equivalence') == '56_generated_files_byte_equal_for_checked_inputs' and
            not any(report.get(k) for k in ('timed_out', 'log_limit_exceeded', 'capture_error')),
            'Asset-backed reference template comparison has not passed acceptance')
    require(report.get('runtime_inputs_sha256') == original_inputs_sha and
            report.get('schema_report_sha256') == schema_report_sha, 'Comparison input/evidence hash mismatch')
    require(report.get('source_commit') == generation.SOURCE_COMMIT and
            report.get('data_commit') == generation.DATA_COMMIT and
            report.get('reference_repository_commit') == package['repository_commit'] and
            report.get('postgresql_build_input') == package['postgresql_build_input'] and
            report.get('mapserver_sha256') == hashes['MapServer.exe'], 'Comparison and reference source/build receipts differ')
    for key in ('status', 'source_commit', 'data_commit', 'binary_assets_supplied',
                'executables_supplied', 'binary_asset_files', 'build_file_sha256',
                'reference_repository_commit', 'postgresql_build_input'):
        require(original_inputs.get(key) == fresh_inputs.get(key), 'Fresh runtime differs from compared inputs: ' + key)
    require(report.get('verified_asset_files') == len(fresh_inputs['binary_asset_files']),
            'Compared asset inventory count differs')


def preflight(runtime, reference, schema_report, comparison_report, comparison_inputs,
              schema_archive=None, comparison_archive=None, root=ROOT):
    contract = source_map_contract(root)
    context = comparison.check_runtime(runtime, reference, root)
    accepted, expected_outputs, schema_payloads = comparison.accepted_schema(schema_report, root, schema_archive)
    observed = comparison.regular_json(comparison_report)
    original = comparison.regular_json(comparison_inputs)
    accept_comparison(observed, original, sha256(comparison_inputs), context['inputs'], context['package'],
                      context['hashes'], sha256(schema_report))
    require(observed.get('accepted_schema_archive_sha256') == accepted['schema_outputs_archive']['sha256'],
            'Comparison used a different accepted schema archive')
    compared = schema.archive_payloads(comparison_archive or comparison_report.parent / 'schema-outputs.zip',
                                       observed.get('compared_outputs_archive', {}))
    require(set(compared) == comparison.EXPECTED, 'Compared archive does not contain exactly56 reviewed outputs')
    require(all(payload(compared[name][1]) == schema_payloads[name] for name in comparison.EXPECTED),
            'Compared template/archive bytes differ from accepted schema output')
    templates, attrs = schema.schema_contract((root / 'upstream/ouroboros/DBServer/src/dbinit.c').read_text())
    tables = {}
    for table, path in templates.items():
        for name, columns in schema.template_columns(schema_payloads[path].decode('utf-8'), table).items():
            require(name not in tables, 'Overlapping generated template table')
            tables[name] = columns
    for table in attrs:
        tables[table] = ['id', 'name']
    return context, schema_payloads, tables, contract


def map_command(runtime):
    return [str(runtime / 'MapServer.exe'), '-nogui', '-db', '127.0.0.1',
            '-nosharedmemory', '-nostats', '-udp', str(MAP_UDP_PORT), '-tcp', '0', '-map_id', str(MAP_ID)]


def preflight_ports(pg_port):
    ports = [('postgresql', socket.SOCK_STREAM, pg_port), ('dbserver', socket.SOCK_STREAM, network.DB_PORT),
             ('map_client', socket.SOCK_DGRAM, MAP_UDP_PORT)]
    require(1024 <= pg_port <= 65535 and pg_port not in (network.DB_PORT, MAP_UDP_PORT), 'Conflicting/invalid PostgreSQL port')
    results = []
    for label, protocol, port in ports:
        with socket.socket(socket.AF_INET, protocol) as probe:
            if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                # Match the stock engine's INADDR_ANY bind rather than overlooking
                # an existing listener on another interface. Release before launch.
                probe.bind(('0.0.0.0', port))
            except OSError as error:
                raise ValueError(f'Required {label} port {port} is unavailable') from error
        results.append({'service': label, 'protocol': 'UDP' if protocol == socket.SOCK_DGRAM else 'TCP',
                        'port': port, 'available_before_start': True})
    return results


def diagnostic_failures(text):
    return [line[:2000] for line in text.splitlines() if is_failure_line(line) or CRITICAL_ASSET.search(line)]


def database_query_possible(cluster, tables):
    # This only permits the first status query. Its received response, followed
    # by READY_FOR_PLAYERS-derived status, provides the actual protocol proof.
    with socket.socket() as probe:
        probe.settimeout(0.2)
        if probe.connect_ex(('127.0.0.1', network.DB_PORT)) != 0:
            return False
    actual = {}
    for row in catalog_snapshot(cluster)['columns']:
        actual.setdefault(row['table_name'], []).append(row['column_name'])
    return actual == tables


def run(runtime, reference, schema_report, comparison_report, comparison_inputs,
        work, output, pg_bin, driver, port=15436, timeout=900, hold=60,
        schema_archive=None, comparison_archive=None, root=ROOT):
    runtime, reference, work, output = [Path(p).resolve() for p in (runtime, reference, work, output)]
    network.new_paths(runtime, reference, work, output, root)
    require(60 <= timeout <= 1800 and 30 <= hold <= 120, 'Startup timeout60..1800 and hold30..120 seconds required')
    context, outputs, tables, contract = preflight(runtime, reference, Path(schema_report),
        Path(comparison_report), Path(comparison_inputs), Path(schema_archive) if schema_archive else None,
        Path(comparison_archive) if comparison_archive else None, root)
    port_checks = preflight_ports(port)
    make_private_directory(work)
    output.mkdir(parents=True)
    isolated, logs = work / 'runtime', work / 'raw-logs'
    isolated.mkdir()
    logs.mkdir()
    cluster, processes, secrets = None, [], []
    report = {'status': 'atlas_park_smoke_validation_failed', 'source_commit': generation.SOURCE_COMMIT,
        'data_commit': generation.DATA_COMMIT, 'reference_repository_commit': context['package']['repository_commit'],
        'dbserver_sha256': context['hashes']['DbServer.exe'], 'mapserver_sha256': context['hashes']['MapServer.exe'],
        'comparison_report_sha256': sha256(Path(comparison_report)),
        'comparison_inputs_sha256': sha256(Path(comparison_inputs)), 'map_contract': contract,
        'hold_seconds_requested': hold, 'startup_timeout_seconds': timeout, 'port_preflight': port_checks,
        'map_client_udp_port': MAP_UDP_PORT, 'map_client_tcp_listener': 'disabled (-tcp 0)',
        'network_scope': 'Queries and database connections use loopback; unmodified game listeners bind INADDR_ANY on the disposable host',
        'scope': 'One Atlas Park MapServer with DB-confirmed ready status and recent stats during a bounded observation',
        'gameplay_validated': False, 'character_persistence_validated': False, 'client_login_validated': False,
        'asset_coverage_complete': False, 'queued_error_count': None,
        'queued_error_limit': 'Normal executable does not report queued startup error count; diagnostics captured, missing-asset list is not exhaustive',
        'started_utc': datetime.now(timezone.utc).isoformat(), 'status_samples': [], 'failures': []}

    def start(command, label):
        process = network.Process(command, isolated, logs, label)
        processes.append(process)
        return process

    def status_query(label, allow_missing=False):
        query = start([str(isolated / 'MapServer.exe'), '-nogui', '-db', '127.0.0.1',
                       '-dbquery', '-timeout', '10000', '-getstatus', '1', '1'], label)
        query.wait(25)
        require(query.child.returncode == 0, 'Map status query failed')
        value = parse_status(query.text(), allow_missing=allow_missing)
        value['sampled_utc'] = datetime.now(timezone.utc).isoformat()
        report['status_samples'].append(value)
        return value

    def logs_clean():
        text, records = collect_logs(isolated, logs, output, secrets)
        report['redacted_logs'] = records
        report['benign_catalog_notices'] = benign_catalog_notices(text)
        errors = diagnostic_failures(text)
        require(not errors, 'Observed startup/runtime failure diagnostics:\n' + '\n'.join(errors[:30]))
        return text

    try:
        # Copy, never hardlink: MapServer may create caches and rewrite ID maps.
        for name, path in input_files(runtime):
            destination = isolated / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
        # Preserve the existing case spelling of any pinned dbidmap.
        existing = {name.casefold(): path for name, path in input_files(isolated)}
        for name, data in outputs.items():
            target = existing.get(name, isolated / name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        config = isolated / 'data/server/db/servers.cfg'
        original = config.read_text()
        config.unlink()  # private_write reserves a newly-created credentials file.
        cluster = initialize(work / 'pg', pg_bin, port, 'coh_one_map', driver)
        secrets = list(cluster.secrets.values())
        private_write(config, network.service_config(original, (cluster.root / 'dbserver-postgresql.cfg').read_text()))
        require(not catalog_snapshot(cluster)['columns'], 'Disposable dbo schema was not initially empty')
        database = start([str(isolated / 'DbServer.exe'), '-start', '0'], 'dbserver')

        network.wait_for(lambda: database_query_possible(cluster, tables), [database], isolated,
                         min(timeout, 300), 'listening DbServer and complete generated SQL schema')
        report['database_startup_gate'] = {
            'captured_ready_diagnostic': 'DbServer Ready.' in database.text(),
            'listening_loopback_port': network.DB_PORT, 'generated_schema_matches': True,
            'protocol_readiness_proof': 'Requires subsequent stock status response; socket/schema alone do not prove readiness'}
        # maps.db is loaded after the normal launchers wait, so allow up to60s
        # for its first real protocol reply without starting any map.
        deadline = time.monotonic() + 60
        while True:
            baseline = status_query('baseline-' + str(len(report['status_samples'])), allow_missing=True)
            require(not baseline['ready'], 'Atlas Park was already running before the owned MapServer started')
            if baseline.get('not_started'):
                break
            require(time.monotonic() < deadline and database.poll() is None, 'Atlas Park was not in an unstarted baseline state')
            time.sleep(1)
        report['baseline_not_started_verified'] = True
        logs_clean()
        mapserver = start(map_command(isolated), 'atlas-park')
        deadline, sample_index = time.monotonic() + timeout, 0
        while True:
            require(database.poll() is None and mapserver.poll() is None, 'DbServer/MapServer exited before protocol readiness')
            network.engine_bounds(isolated)
            sample = status_query(f'startup-{sample_index}')
            sample_index += 1
            if sample['ready']:
                require(sample['port'] == MAP_UDP_PORT, 'Registered MapServer endpoint differs from owned map port')
                break
            require(time.monotonic() < deadline, 'Atlas Park did not reach DB-confirmed ready status')
            time.sleep(2)
        logs_clean()
        ready_at = time.monotonic()
        while time.monotonic() - ready_at < hold:
            require(database.poll() is None and mapserver.poll() is None, 'DbServer/MapServer exited during observation')
            network.engine_bounds(isolated)
            sample = status_query(f'observe-{sample_index}')
            sample_index += 1
            require(sample['ready'], 'Atlas Park lost DB-confirmed readiness')
            elapsed = time.monotonic() - ready_at
            if elapsed >= 20:
                require(sample['network_age_seconds'] <= 20 and sample['stats_age_seconds'] <= 20,
                        'Atlas Park network/statistics updates stopped during observation')
            time.sleep(min(5, max(0, hold - (time.monotonic() - ready_at))))
        final = status_query('final-status')
        require(final['ready'] and final['stats_age_seconds'] <= 20 and final['network_age_seconds'] <= 20,
                'Final Atlas Park status is not ready/current')
        require(database.poll() is None and mapserver.poll() is None, 'Service exited at end of observation')
        validate_catalog(catalog_snapshot(cluster), tables)
        text = logs_clean()
        report['warning_lines'] = [line[:2000] for line in text.splitlines() if comparison.WARNING.search(line)][:1000]
        report['observed_ready_seconds'] = round(time.monotonic() - ready_at, 3)
        report['generated_output_count'] = len(generation.output_snapshot(isolated))
        report['comparison_caches_reused'] = False
        report['status'] = SUCCESS
    except (OSError, ValueError, RuntimeError, AssertionError, subprocess.SubprocessError) as error:
        report['failures'].append(redact(str(error), secrets))
    finally:
        # The test stops owned disposable services after observation; this is not
        # evidence for graceful shutdown, which remains a separate milestone.
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
            report['status'] = 'atlas_park_smoke_validation_failed'
        report['shutdown_scope'] = 'Owned disposable processes stopped; graceful game-service shutdown unvalidated'
        report['processes'] = [process.record() for process in processes]
        report['finished_utc'] = datetime.now(timezone.utc).isoformat()
        (output / 'one-map-report.json').write_text(redact(json.dumps(report, indent=2) + '\n', secrets), encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('runtime', 'reference-binaries', 'schema-report', 'comparison-report', 'comparison-inputs', 'work', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--schema-archive', type=Path)
    parser.add_argument('--comparison-archive', type=Path)
    parser.add_argument('--bin', required=True)
    parser.add_argument('--driver', default='PostgreSQL Unicode')
    parser.add_argument('--port', type=int, default=15436)
    parser.add_argument('--timeout-seconds', type=float, default=900)
    parser.add_argument('--hold-seconds', type=float, default=60)
    args = parser.parse_args()
    report = run(args.runtime, args.reference_binaries, args.schema_report, args.comparison_report,
                 args.comparison_inputs, args.work, args.output, args.bin, args.driver, args.port,
                 args.timeout_seconds, args.hold_seconds, args.schema_archive, args.comparison_archive)
    print(report['status'])
    return 0 if report['status'] == SUCCESS else 1


if __name__ == '__main__':
    sys.exit(main())
