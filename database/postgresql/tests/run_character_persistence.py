#!/usr/bin/env python3
"""Exercise a fresh stock fake-auth character, protocol logout and short resume.

Windows reference harness; not Android/gameplay validation. Only --output is
publishable. Credentials, full containers and raw logs remain in private --work.
Services and the message-mode pipe are owned by this run. No player saves are
imported and neither the immutable source nor the supplied runtime is modified.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets as random_secrets
import shutil
import subprocess
import sys
import time

import run_generated_schema as schema
import run_network_ack as network
import run_one_map as one_map
import character_snapshot as snapshots
from character_pipe import TestClientPipe
from run_generated_schema import (ROOT, require, sha256, redact, initialize,
    make_private_directory, private_write, collect_logs, catalog_snapshot,
    validate_catalog)
from prepare_runtime import input_files

SUCCESS = 'fresh_fakeauth_character_persistence_short_resume_passed_gameplay_unvalidated'
FAILED = 'character_persistence_validation_failed'
INFLUENCE = 12345
CLIENT_FAILURE = re.compile(
    r'\b(?:CRASH|Exception caught|CRT Error|Errorf|Unable to locate character|'
    r'Character creation did not reach|Error logging on|Error connecting to MapServer|'
    r'Error calling choosePlayerWrapper|Did not get players|Server timeout|'
    r'No free slots|does not have a character in slot|dbQuery failed|Failed to connect to DbServer)\b', re.I)
EXPECTED_LOGOUT = re.compile(r'^\s*Fatal Error: Booted back to login screen\s*$')
PUBLIC_LINE = re.compile(r'DbServer Ready\.|container_id = |\bName .+ Auth .+ MapId |'
    r'Found character |Resuming character in slot |simulateCharacterCreate\(\)|'
    r'commReqScene\(\)|^Map: |MESSAGE FROM LAUNCHER: CMD (?:quit|influence 12345)$')


def utc():
    return datetime.now(timezone.utc).isoformat()


def source_contract(root=ROOT):
    base = root / 'upstream/ouroboros'
    paths = {
        'main': 'Utilities/TestClient/src/main.c',
        'commands': 'Utilities/TestClient/src/testClientCmdParse.c',
        'status': 'DBServer/src/status.c',
        'scene': 'Game/src/clientcomm/clientcomm.c',
        'server_commands': 'MapServer/src/cmdparse/cmdserver.c',
        'logout': 'Utilities/TestClient/src/externs.c',
        'debug': 'MapServer/src/cmdparse/cmdservercsr.c',
        'chat': 'Utilities/TestClient/src/chatter.c',
    }
    sources = {key: (base / path).read_text() for key, path in paths.items()}
    expected = {
        'main': ('g_testMode = TEST_LOGIN;', 'g_testMode |= TEST_RESUME_CHAR;',
                 'game_state.no_version_check = 1;', 'Found character %s in slot %d',
                 'Resuming character in slot %d', 'commReqScene(1);',
                 'sendMessageToLauncher("Player: %s"', 'sendMessageToLauncher("MapName: %s"',
                 'if (err || !(g_testMode & TEST_STAY_CONNECTED))', 'Fatal Error: %s'),
        'commands': ('commSendQuitGame(0);', 'sendMessageToLauncher("QuitNow:");'),
        'status': ('MapId %d SmapId %d', '"NoConnect "', '"InMapXfer "'),
        'scene': ('CLIENT_REQSCENE', 'commCheck(SERVER_GROUPS)', 'commCheck(SERVER_ALLENTS)', 'CLIENT_READY'),
        'server_commands': ('xcase SCMD_INFLUENCE:', 'ent_SetInfluence(e, tmp_int);'),
        'logout': ('FatalErrorf("Booted back to login screen");',),
        'debug': ('char * csrPlayerInfo(', 'localizedPrintf(e,"CSRInfo1")',
                  'localizedPrintf(e,"CSRInfo2")', 'localizedPrintf(e,"CSRInfo8a")', 'e->pchar->iInfluencePoints'),
        'chat': ('PipeClientSendMessage(pc,"ChatText:%s",str);',),
    }
    for key, fragments in expected.items():
        require(all(fragment in sources[key] for fragment in fragments), 'Reviewed character source contract changed: ' + key)
    messages = (root / 'upstream/i24/data/texts/english/menumessages.ms').read_text(encoding='utf-8-sig')
    for key, value in (('CSRInfo1', 'Player:'), ('CSRInfo2', 'Login:'), ('CSRInfo8a', 'Current cash:')):
        require(re.search(r'"' + key + r'",\s+"' + re.escape(value), messages), 'Reviewed live currency message changed: ' + key)
    return {'list_id': 3, 'map_id': one_map.MAP_ID, 'map_path': one_map.MAP_PATH,
            'influence': INFLUENCE, 'source_sha256': {paths[key]: sha256(base / paths[key]) for key in paths},
            'resume_scope': 'Stock order-sensitive -justlogin -character clears CREATE and STAY_CONNECTED',
            'quit_ack_scope': 'QuitNow confirms the request only; server status plus committed SQL are required'}


def accept_one_map(report, context, comparison_sha, inputs_sha):
    require(report.get('status') == one_map.SUCCESS and report.get('failures') == [] and
            report.get('baseline_not_started_verified') is True and
            report.get('comparison_caches_reused') is False and
            type(report.get('generated_output_count')) is int and
            report['generated_output_count'] >= len(one_map.comparison.EXPECTED),
            'Prior one-map readiness acceptance has not passed')
    expected = {'source_commit': one_map.generation.SOURCE_COMMIT,
                'data_commit': one_map.generation.DATA_COMMIT,
                'reference_repository_commit': context['package']['repository_commit'],
                'dbserver_sha256': context['hashes']['DbServer.exe'],
                'mapserver_sha256': context['hashes']['MapServer.exe'],
                'comparison_report_sha256': comparison_sha, 'comparison_inputs_sha256': inputs_sha}
    require(all(report.get(key) == value for key, value in expected.items()),
            'Prior one-map source/reference/comparison provenance differs')
    samples = report.get('status_samples', [])
    require(isinstance(samples, list) and samples and samples[-1].get('ready') is True and
            samples[-1].get('port') == one_map.MAP_UDP_PORT and
            type(report.get('observed_ready_seconds')) in (int, float) and
            report['observed_ready_seconds'] >= 30 and
            all(type(samples[-1].get(key)) is int and 0 <= samples[-1][key] <= 20
                for key in ('network_age_seconds', 'stats_age_seconds')),
            'Prior one-map observation/heartbeat proof is incomplete')
    contract = report.get('map_contract', {})
    require(contract.get('map_id') == one_map.MAP_ID and contract.get('map_path') == one_map.MAP_PATH,
            'Prior readiness evidence is not for reviewed Atlas Park')


def diagnostic_failures(text, allow_requested_logout=False):
    failures = []
    for line in text.splitlines():
        if allow_requested_logout and EXPECTED_LOGOUT.fullmatch(line):
            continue
        # The stock TCLOG_FATAL record has an engine-specific timestamp prefix.
        # Only this exact payload may accompany the independently proven logout.
        if allow_requested_logout and re.fullmatch(r'[^\r\n]*\bFATAL\b[^\r\n]*Was booted back to login screen\s*', line):
            continue
        if one_map.diagnostic_failures(line) or CLIENT_FAILURE.search(line):
            failures.append(line[:2000])
    return failures


def parse_find(text):
    require(not diagnostic_failures(text), 'Character find query emitted failure diagnostics')
    matches = re.findall(r'^\s*container_id = (-?\d+)\s*$', text, re.M)
    require(len(matches) == 1 and int(matches[0]) > 0, 'Missing/ambiguous positive character ID')
    return int(matches[0])


def parse_character_status(text, identifier, name, account, allow_missing=False):
    require(type(identifier) is int and identifier > 0, 'Invalid character ID')
    require(not diagnostic_failures(text), 'Character status query emitted failure diagnostics')
    missing = [line for line in text.splitlines() if line.strip() == 'invalid container request']
    matches = re.findall(r'^\s*(\d+)\s+Name\s+(.+?)\s+Auth\s+(\S+)\s+Ip\s+(\S+)\s+'
                         r'MapId\s+(\d+)\s+SmapId\s+(\d+)\s*(.*?)\s*$', text, re.M)
    if missing:
        require(allow_missing and len(missing) == 1 and not matches, 'Unexpected/ambiguous missing character status')
        return {'loaded': False, 'connected': False, 'in_map_transfer': False, 'sampled_utc': utc()}
    require(len(matches) == 1, 'Missing/ambiguous character status response')
    ident, observed_name, observed_account, ip, mapid, static_mapid, flags = matches[0]
    require(int(ident) == identifier and observed_name.rstrip() == name and observed_account == account,
            'Character status identity differs')
    require(set(flags.split()).issubset({'NoConnect', 'InMapXfer'}), 'Unknown character status flags')
    require(re.fullmatch(r'(?:\d{1,3}\.){3}\d{1,3}', ip) and
            all(int(part) <= 255 for part in ip.split('.')), 'Invalid character status endpoint')
    return {'loaded': True, 'connected': 'NoConnect' not in flags.split(),
            'in_map_transfer': 'InMapXfer' in flags.split(), 'map_id': int(mapid),
            'static_map_id': int(static_mapid), 'sampled_utc': utc()}


def connected_on_atlas(status):
    return status['loaded'] and status['connected'] and not status['in_map_transfer'] and status['map_id'] == one_map.MAP_ID


def live_currency_evidence(events, name, account, after_sequence):
    """Only the stock server's conPrintf response identifies the live entity.

    Ordinary player chat containing these words cannot satisfy the diagnostic.
    The CMD debug reply reads the MapServer entity; no SQL write/forced save is
    used to make the currency visible before protocol logout.
    """
    accepted = []
    for event in events:
        if event['sequence'] <= after_sequence or not event['raw'].startswith('ChatText:conPrintf:0:'):
            continue
        body = event['raw'][len('ChatText:conPrintf:0:'):]
        players = re.findall(r'^\s*Player:\s*([^\r\n]+?)\s*$', body, re.M)
        accounts = re.findall(r'^\s*Login:\s*([^\r\n]+?)\s*$', body, re.M)
        values = re.findall(r'^\s*Current cash:\s*(\d+)\s+\(Influence\)\s*$', body, re.M)
        if not players and not accounts and not values:
            continue
        require(len(players) == len(accounts) == len(values) == 1, 'Malformed/ambiguous live currency diagnostic')
        require(players[0] == name and accounts[0] == account, 'Live currency diagnostic identifies another character/account')
        if int(values[0]) == INFLUENCE:
            accepted.append({'player': name, 'account': account, 'influence': INFLUENCE,
                             'time_utc': event['time_utc'], 'sequence': event['sequence']})
    return accepted[-1] if accepted else False


def client_command(runtime, account, name=None):
    require(re.fullmatch(r'[A-Za-z][A-Za-z0-9]{1,19}', account), 'Unsafe diagnostic account name')
    command = [str(runtime / 'TestClient.exe'), '-db', '127.0.0.1', '-fakeauth', '-authname', account,
               '-dontpause', '-nosharedmemory']
    if name is None:
        return command + ['-nolevel', '-TEAMACCEPT', '-FOLLOW', '-SUPERGROUPACCEPT', '-LEAGUEACCEPT']
    require(name and len(name) <= 128 and not any(ord(c) < 32 for c in name), 'Invalid recorded character name')
    return command + ['-justlogin', '-character', name]


def character_config(original, fragment):
    settings = {'advertisedip': 'AdvertisedIp 127.0.0.1', 'usefakeauth': 'UseFakeAuth 1',
                'usequeueserver': 'UseQueueServer 0', 'blockfreeplayersifnoaccountserver': 'BlockFreePlayersIfNoAccountServer 0',
                'defaultaccesslevel': 'DefaultAccessLevel 9'}
    text = '\n'.join(line for line in original.splitlines()
                     if not line.split() or line.split()[0].lower() not in settings)
    # Supply the explicitly reviewed auth flags before the reusable validator.
    return network.service_config(text + '\n' + '\n'.join(settings.values()) + '\n', fragment)


def pipe_identity(state, pid, account, expected_name=None, allow_logout_error=False):
    require(not state.get('error'), 'Named-pipe transport failed: ' + str(state.get('error')))
    events = state.get('events', [])
    require(not any(e['kind'] == 'Status' and e['value'] == 'CRASH' for e in events), 'TestClient reported CRASH')
    errors = [e for e in events if e['kind'] == 'Status' and e['value'] == 'ERROR']
    if errors:
        quit_events = [e for e in events if e['kind'] == 'QuitNow']
        require(allow_logout_error and quit_events and all(e['sequence'] > quit_events[0]['sequence'] for e in errors),
                'TestClient reported ERROR before a requested logout')
    for event in events:
        if event['kind'] == 'AuthName':
            require(event['value'] == account, 'Launcher account identity differs')
    if not (state.get('pid_verified') and state.get('client_pid') == pid and state.get('version_requests') == 1 and
            state.get('player') and state.get('map_name') and any(e['kind'] == 'Status' and e['value'] == 'Running' for e in events)):
        return False
    name = state['player']
    require(not expected_name or name == expected_name, 'Launcher returned a different character name')
    require(state['map_name'].replace('\\', '/').casefold() == one_map.MAP_PATH.casefold(), 'Launcher returned a different map')
    require(all(e['value'] == name for e in events if e['kind'] == 'Player'), 'Launcher player identity changed')
    return name


def accept_resume(text, state, pid, account, name, exit_code):
    require(exit_code == 0, 'Short resume probe did not exit cleanly')
    require(not diagnostic_failures(text), 'Short resume probe emitted failure diagnostics')
    require('simulateCharacterCreate' not in text and not re.search(r'Character creation|Create a new character', text, re.I),
            'Short resume attempted character creation')
    matches = re.findall(r'^Found character (.+) in slot (\d+)\s*$', text, re.M)
    require(len(matches) == 1 and matches[0][0] == name, 'Exact-name existing-character match was not observed')
    slot = int(matches[0][1])
    require(re.search(r'Resuming character in slot ' + str(slot) + r'\.\.\.', text) and 'commReqScene()' in text,
            'Resume branch/scene exchange diagnostic is missing')
    require(pipe_identity(state, pid, account, name) == name, 'Resume lacks returned player/map identity')
    return {'slot': slot, 'scene_exchange_observed': True, 'creation_disabled': True,
            'active_gameplay_confirmed': False, 'scope': 'Short resume/scene probe; queued CLIENT_READY processing is unproven'}


def selected_pipe_record(state):
    # Arbitrary chat, host information and full SCREEN/container messages stay private.
    kinds = {'PID', 'AuthName', 'Player', 'MapName', 'Status', 'QuitNow', 'VersionRequest'}
    return {key: state.get(key) for key in ('client_pid', 'pid_verified', 'version_requests', 'disconnected')} | {
        'events': [{key: event[key] for key in ('kind', 'value', 'time_utc', 'sequence')}
                   for event in state.get('events', []) if event['kind'] in kinds]}


def run(runtime, reference, schema_report, comparison_report, comparison_inputs, one_map_report,
        work, output, pg_bin, driver, port=15437, timeout=900, phase_timeout=300,
        schema_archive=None, comparison_archive=None, diagnostic_version=None, root=ROOT):
    runtime, reference, work, output = [Path(p).resolve() for p in (runtime, reference, work, output)]
    network.new_paths(runtime, reference, work, output, root)
    require(60 <= timeout <= 1800 and 30 <= phase_timeout <= 900, 'Timeouts must be startup60..1800 and phase30..900 seconds')
    context, outputs, tables, map_contract = one_map.preflight(runtime, reference, Path(schema_report),
        Path(comparison_report), Path(comparison_inputs), Path(schema_archive) if schema_archive else None,
        Path(comparison_archive) if comparison_archive else None, root)
    accept_one_map(one_map.comparison.regular_json(Path(one_map_report)), context,
                   sha256(Path(comparison_report)), sha256(Path(comparison_inputs)))
    contract = source_contract(root)
    selection = snapshots.selected_contract(tables)
    require(os.name == 'nt', 'This stock named-pipe harness requires the Windows reference host')
    version_source = 'explicit diagnostic override' if diagnostic_version else 'reference package'
    version = diagnostic_version or context['package'].get('client_version') or context['package'].get('patch_version')
    if not version:
        version, version_source = 'coh-persistence-diagnostic', 'diagnostic fallback; reference package contains no patch version'
    require(isinstance(version, str) and re.fullmatch(r'[\x20-\x7e]{1,128}', version), 'Invalid diagnostic version')
    port_checks = one_map.preflight_ports(port)
    make_private_directory(work)
    output.mkdir(parents=True)
    isolated, logs, query_logs, scanned = (work / name for name in ('runtime', 'raw-logs', 'private-query-logs', 'scanned-logs'))
    for path in (isolated, logs, query_logs, scanned):
        path.mkdir()
    report = {'status': FAILED, 'started_utc': utc(), 'failures': [], 'phases': [],
        'source_commit': one_map.generation.SOURCE_COMMIT, 'data_commit': one_map.generation.DATA_COMMIT,
        'reference_repository_commit': context['package']['repository_commit'],
        'binary_sha256': {name: context['hashes'][name] for name in ('DbServer.exe', 'MapServer.exe', 'TestClient.exe')},
        'schema_report_sha256': sha256(Path(schema_report)), 'comparison_report_sha256': sha256(Path(comparison_report)),
        'comparison_inputs_sha256': sha256(Path(comparison_inputs)), 'one_map_report_sha256': sha256(Path(one_map_report)),
        'source_contract': contract, 'selected_sql_contract': selection, 'port_preflight': port_checks,
        'diagnostic_version': version, 'diagnostic_version_source': version_source,
        'version_compatibility_validated': False, 'no_version_check': True,
        'character_persistence_validated': False, 'gameplay_validated': False, 'android_execution_validated': False,
        'scope': 'Fresh fake-auth create, influence command, protocol logout, committed SQL, service restart and short exact-name resume',
        'network_scope': 'Loopback queries; stock game listeners still bind INADDR_ANY on the private disposable host',
        'raw_evidence_private': True, 'status_samples': [], 'character_status_samples': [], 'snapshots': {}}
    cluster, processes, pipes, services, secrets = None, [], [], [], []
    requested_logout = False
    account = 'CohP' + random_secrets.token_hex(5)
    report['account'] = account

    def start(command, label, private=False):
        process = network.Process(command, isolated, query_logs if private else logs, label)
        processes.append(process)
        return process

    def health():
        for service in services:
            require(service.poll() is None, 'Owned service exited: ' + service.label)
        for process in processes:
            process.check_bounds()
        network.engine_bounds(isolated)

    def query(args, label, private=False):
        health()
        process = start([str(isolated / 'MapServer.exe'), '-nogui', '-db', '127.0.0.1',
                         '-dbquery', '-timeout', '10000'] + args, label, private)
        process.wait(25)
        require(process.child.returncode == 0, 'Stock query failed: ' + label)
        text = process.text()
        require(not diagnostic_failures(text), 'Stock query emitted failure diagnostics: ' + label)
        process.stop()
        health()
        return text

    def logs_clean():
        text, records = collect_logs(isolated, logs, scanned, secrets)
        errors = diagnostic_failures(text, allow_requested_logout=requested_logout)
        # Publish selected diagnostics only. In particular -get payloads are never
        # copied out of private work, nor are arbitrary engine/player log lines.
        selected = [line[:2000] for line in text.splitlines() if PUBLIC_LINE.search(line) or
                    diagnostic_failures(line) or EXPECTED_LOGOUT.fullmatch(line)]
        require(len(selected) <= 4000, 'Selected diagnostic evidence exceeded bound')
        target = output / 'selected-diagnostics.txt'
        target.write_text(redact('\n'.join(selected) + '\n', secrets), encoding='utf-8')
        report['redacted_logs'] = [{'file': target.name, 'sha256': sha256(target), 'bytes': target.stat().st_size,
                                    'scope': 'Selected diagnostics; complete raw logs and container payloads remain private'}]
        report['benign_catalog_notices'] = schema.benign_catalog_notices(text)
        require(not errors, 'Observed failure diagnostics:\n' + '\n'.join(errors[:30]))
        return text

    def wait(predicate, seconds, label, client=None):
        deadline = time.monotonic() + seconds
        while True:
            health()
            result = predicate()
            if result:
                return result
            if client is not None:
                require(client.poll() is None, 'TestClient exited before ' + label)
            require(time.monotonic() < deadline, 'Timed out waiting for ' + label)
            time.sleep(0.2)

    def map_status(label, allow_missing=False):
        sample = one_map.parse_status(query(['-getstatus', '1', '1'], label), allow_missing=allow_missing)
        sample['sampled_utc'] = utc()
        report['status_samples'].append(sample)
        return sample

    def start_services(phase):
        database = start([str(isolated / 'DbServer.exe'), '-start', '0'], phase + '-dbserver')
        services.append(database)
        wait(lambda: one_map.database_query_possible(cluster, tables), min(timeout, 300), 'DbServer schema/listener')
        index = 0
        deadline = time.monotonic() + 60
        while True:
            sample = map_status(phase + '-baseline-' + str(index), allow_missing=True)
            index += 1
            require(not sample['ready'], 'Unowned Atlas Park MapServer was already running')
            if sample.get('not_started'):
                break
            require(time.monotonic() < deadline, 'Atlas Park baseline never reached unstarted state')
            time.sleep(1)
        services.append(start(one_map.map_command(isolated), phase + '-atlas-park'))
        deadline = time.monotonic() + timeout
        while True:
            sample = map_status(phase + '-ready-' + str(index))
            index += 1
            if sample['ready']:
                require(sample['port'] == one_map.MAP_UDP_PORT and sample['network_age_seconds'] <= 20 and
                        sample['stats_age_seconds'] <= 20, 'Atlas Park ready response is stale or from a different endpoint')
                break
            require(time.monotonic() < deadline, 'Atlas Park did not reach protocol readiness')
            time.sleep(2)
        logs_clean()
        report['phases'].append({'phase': phase + '_services_ready', 'time_utc': utc(), 'status': 'passed'})

    def char_status(identifier, name, phase, allow_missing=False):
        index = len(report['character_status_samples'])
        state = parse_character_status(query(['-getstatus', '3', str(identifier)], phase + '-status-' + str(index)),
                                       identifier, name, account, allow_missing)
        report['character_status_samples'].append(dict(state, phase=phase, character_id=identifier))
        return state

    def attributes():
        _, attrs = schema.schema_contract((root / 'upstream/ouroboros/DBServer/src/dbinit.c').read_text())
        expected = {table: schema.attribute_rows(outputs[path].decode('utf-8')) for table, path in attrs.items()}
        return snapshots.attribute_snapshot(cluster, tables, expected=expected)

    try:
        for name, path in input_files(runtime):
            target = isolated / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        existing = {name.casefold(): path for name, path in input_files(isolated)}
        for name, data in outputs.items():
            target = existing.get(name, isolated / name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        config = isolated / 'data/server/db/servers.cfg'
        original = config.read_text()
        config.unlink()
        cluster = initialize(work / 'pg', pg_bin, port, 'coh_character_persistence', driver)
        secrets = list(cluster.secrets.values())
        private_write(config, character_config(original, (cluster.root / 'dbserver-postgresql.cfg').read_text()))
        require(not catalog_snapshot(cluster)['columns'], 'Disposable SQL schema was not initially empty')
        start_services('first')
        attr_before = attributes()
        report['attribute_mapping_sha256'] = {key: hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
                                               for key, value in attr_before.items()}
        require(snapshots.account_rows(cluster, account, tables) == [], 'Fresh diagnostic account already has characters')
        report['phases'].append({'phase': 'account_empty', 'time_utc': utc(), 'status': 'passed'})
        pipe = TestClientPipe(version)
        pipe.__enter__()
        pipes.append(pipe)
        client = start(client_command(isolated, account), 'create-client')
        pipe.bind_process(client.child.pid)
        name = wait(lambda: pipe_identity(pipe.snapshot(), client.child.pid, account), phase_timeout,
                    'fresh character launcher identity', client)
        identifier = parse_find(query(['-find', '3', 'Name', name], 'find-created-character'))
        rows = wait(lambda: snapshots.account_rows(cluster, account, tables), phase_timeout,
                    'committed fresh account character', client)
        require(len(rows) == 1 and rows[0]['containerid'] == identifier and rows[0]['name'] == name,
                'Stock find and independent SQL character identities differ')
        report['character'] = {'container_id': identifier, 'name': name, 'account': account}
        wait(lambda: connected_on_atlas(char_status(identifier, name, 'created')), phase_timeout,
             'connected character on Atlas Park', client)
        require('simulateCharacterCreate()' in client.text(), 'Fresh client did not report creation branch')
        logs_clean()
        report['phases'].append({'phase': 'created_connected', 'time_utc': utc(), 'status': 'passed'})
        before_currency = pipe.snapshot()['events']
        currency_sequence = before_currency[-1]['sequence'] if before_currency else -1
        pipe.send('CMD influence ' + str(INFLUENCE))
        report['influence_requested_utc'] = utc()
        require(re.fullmatch(r'[A-Za-z0-9 _.-]{1,128}', name), 'Character name cannot be safely quoted in diagnostic command')
        next_debug = 0

        def currency_received():
            nonlocal next_debug
            state = pipe.snapshot()
            pipe_identity(state, client.child.pid, account, name)
            evidence = live_currency_evidence(state['events'], name, account, currency_sequence)
            if not evidence:
                if time.monotonic() >= next_debug:
                    pipe.send('CMD debug "' + name + '"')
                    next_debug = time.monotonic() + 3
                return False
            require(connected_on_atlas(char_status(identifier, name, 'currency')), 'Character disconnected before currency observation')
            return evidence

        report['live_currency_evidence'] = wait(currency_received, phase_timeout, 'live MapServer currency response', client)
        report['phases'].append({'phase': 'influence_observed_while_connected', 'time_utc': utc(), 'status': 'passed',
            'value': INFLUENCE, 'scope': 'CMD debug live entity conPrintf response plus connected MapId1 status; no forced save'})
        logs_clean()  # Fatal diagnostics before the protocol quit are never tolerated.
        requested_logout = True
        report['quit_requested_utc'] = utc()
        pipe.send('CMD quit')
        wait(lambda: pipe.snapshot().get('quit_now'), 15, 'QuitNow request confirmation')

        def saved_after_logout():
            state = pipe.snapshot()
            pipe_identity(state, client.child.pid, account, name, allow_logout_error=True)
            status = char_status(identifier, name, 'logout', allow_missing=True)
            if status['connected'] or status['in_map_transfer']:
                time.sleep(1)
                return False
            # SQL read uses a new independently committed connection after the
            # server disconnected/unloaded the previously connected character.
            try:
                return snapshots.capture(cluster, tables, account, identifier, name, expected_influence=INFLUENCE)
            except ValueError as error:
                report['last_pending_save'] = redact(str(error), secrets)
                return False

        before = wait(saved_after_logout, phase_timeout, 'protocol logout and committed selected SQL rows')
        snapshots.validate_attribute_references(before, attr_before)
        state = pipe.snapshot()
        if any(e['kind'] == 'Status' and e['value'] == 'ERROR' for e in state['events']):
            require(any(EXPECTED_LOGOUT.fullmatch(line) for line in client.text().splitlines()),
                    'Post-quit ERROR lacks the exact stock logout diagnostic')
        report['snapshots']['after_protocol_logout'] = before
        report['first_session_pipe'] = selected_pipe_record(state)
        report['phases'].append({'phase': 'protocol_logout_committed', 'time_utc': utc(), 'status': 'passed',
                                'quitnow_is_save_ack': False, 'client_forced_stop_before_commit': client.forced_stop})
        require(not client.forced_stop, 'Forced disconnect cannot establish protocol logout')
        logs_clean()
        client.stop()  # Cleanup occurs only after independently proven logout/save.
        pipe.close()
        for service in reversed(services):
            service.stop()
        services.clear()
        cluster.stop()
        cluster.start()  # Same cluster/database; no reseeding, restore or map replacement.
        start_services('restart')
        after_restart = snapshots.capture(cluster, tables, account, identifier, name, expected_influence=INFLUENCE)
        snapshots.validate_attribute_references(after_restart, attr_before)
        report['restart_comparison'] = snapshots.compare(before, after_restart, phase='restart')
        report['snapshots']['after_service_restart'] = after_restart
        snapshots.compare_attributes(attr_before, attributes())
        report['phases'].append({'phase': 'restart_saved_state', 'time_utc': utc(), 'status': 'passed'})

        resume_pipe = TestClientPipe(version)
        resume_pipe.__enter__()
        pipes.append(resume_pipe)
        resume = start(client_command(isolated, account, name), 'resume-client')
        resume_pipe.bind_process(resume.child.pid)
        wait(lambda: resume.poll() is not None, phase_timeout, 'short resume probe process completion')
        wait(lambda: pipe_identity(resume_pipe.snapshot(), resume.child.pid, account, name), 5,
             'short resume pipe drain')
        report['resume_probe'] = accept_resume(resume.text(), resume_pipe.snapshot(), resume.child.pid,
                                                account, name, resume.child.returncode)
        report['resume_session_pipe'] = selected_pipe_record(resume_pipe.snapshot())

        def saved_after_resume():
            state = char_status(identifier, name, 'resume_disconnect', allow_missing=True)
            if state['connected'] or state['in_map_transfer']:
                time.sleep(1)
                return False
            try:
                current = snapshots.capture(cluster, tables, account, identifier, name, expected_influence=INFLUENCE)
                comparison = snapshots.compare(before, current, phase='resume')
                return current, comparison
            except ValueError as error:
                report['last_pending_resume_save'] = redact(str(error), secrets)
                return False

        final, resume_comparison = wait(saved_after_resume, phase_timeout, 'resume disconnect save and LoginCount progression')
        report['snapshots']['after_short_resume'] = final
        snapshots.validate_attribute_references(final, attr_before)
        report['resume_comparison'] = resume_comparison
        snapshots.compare_attributes(attr_before, attributes())
        validate_catalog(catalog_snapshot(cluster), tables)
        final_map = map_status('final-map-status')
        require(final_map['ready'] and final_map['network_age_seconds'] <= 20 and final_map['stats_age_seconds'] <= 20,
                'Map lost readiness/current heartbeat after short resume')
        logs_clean()
        report['phases'].append({'phase': 'short_resume_and_committed_state', 'time_utc': utc(), 'status': 'passed'})
        report['character_persistence_validated'] = True
        report['status'] = SUCCESS
    except (OSError, ValueError, RuntimeError, AssertionError, subprocess.SubprocessError) as error:
        report['failures'].append(redact(str(error), secrets))
    finally:
        for process in reversed(processes):
            try:
                process.stop()
            except Exception as error:
                report['failures'].append('Process cleanup: ' + redact(str(error), secrets))
        for pipe in reversed(pipes):
            try:
                pipe.close()
            except Exception as error:
                report['failures'].append('Pipe cleanup: ' + redact(str(error), secrets))
        for index, pipe in enumerate(pipes):
            try:
                private_write(work / f'launcher-session-{index}.json', json.dumps(pipe.snapshot(), indent=2) + '\n')
            except Exception as error:
                report['failures'].append('Private pipe evidence: ' + redact(str(error), secrets))
        if cluster is not None:
            try:
                cluster.stop()
            except Exception as error:
                report['failures'].append('Cluster shutdown: ' + redact(str(error), secrets))
        try:
            logs_clean()
        except Exception as error:
            report['failures'].append('Final diagnostics: ' + redact(str(error), secrets))
        if report['failures']:
            report['status'] = FAILED
            report['character_persistence_validated'] = False
        report['processes'] = [process.record() for process in processes]
        report['shutdown_scope'] = 'Owned disposable processes stopped; graceful whole-server shutdown remains unvalidated'
        report['finished_utc'] = utc()
        (output / 'character-persistence-report.json').write_text(redact(json.dumps(report, indent=2) + '\n', secrets), encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('runtime', 'reference-binaries', 'schema-report', 'comparison-report', 'comparison-inputs',
                 'one-map-report', 'work', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--schema-archive', type=Path)
    parser.add_argument('--comparison-archive', type=Path)
    parser.add_argument('--bin', required=True)
    parser.add_argument('--driver', default='PostgreSQL Unicode')
    parser.add_argument('--port', type=int, default=15437)
    parser.add_argument('--timeout-seconds', type=float, default=900)
    parser.add_argument('--phase-timeout-seconds', type=float, default=300)
    parser.add_argument('--diagnostic-version')
    args = parser.parse_args()
    result = run(args.runtime, args.reference_binaries, args.schema_report, args.comparison_report,
                 args.comparison_inputs, args.one_map_report, args.work, args.output, args.bin, args.driver,
                 args.port, args.timeout_seconds, args.phase_timeout_seconds, args.schema_archive,
                 args.comparison_archive, args.diagnostic_version)
    print(result['status'])
    return 0 if result['status'] == SUCCESS else 1


if __name__ == '__main__':
    sys.exit(main())
