#!/usr/bin/env python3
"""Exercise fresh fake-auth character persistence and opt-in sustained resume.

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
import character_transfer as transfers
from character_console import ConsoleCapture
from character_pipe import TestClientPipe
from run_generated_schema import (ROOT, require, sha256, redact, initialize,
    make_private_directory, private_write, collect_logs, catalog_snapshot,
    validate_catalog)
from prepare_runtime import input_files

SUCCESS = 'fresh_fakeauth_character_persistence_short_resume_passed_gameplay_unvalidated'
SESSION_SUCCESS = 'fresh_fakeauth_character_sustained_resume_second_save_passed_gameplay_unvalidated'
TRANSFER_SUCCESS = 'fresh_fakeauth_character_map_roundtrip_second_save_passed_gameplay_unvalidated'
FAILED = 'character_persistence_validation_failed'
INFLUENCE = 12345
SECOND_INFLUENCE = 23456
CLIENT_FAILURE = re.compile(
    r'\b(?:CRASH|Exception caught|CRT Error|Errorf|Unable to locate character|'
    r'Character creation did not reach|Error logging on|Error connecting to MapServer|'
    r'Error calling choosePlayerWrapper|Did not get players|Server timeout|'
    r'No free slots|does not have a character in slot|dbQuery failed|Failed to connect to DbServer)\b', re.I)
EXPECTED_LOGOUT = re.compile(r'^\s*Fatal Error: Booted back to login screen\s*$')
PUBLIC_LINE = re.compile(r'DbServer Ready\.|container_id = |\bName .+ Auth .+ MapId |'
    r'Found character |Resuming character in slot |simulateCharacterCreate\(\)|'
    r'commReqScene\(\)|^COH_RESUME_ONLY_|^Map: |MESSAGE FROM LAUNCHER: CMD (?:quit|influence (?:12345|23456)|mapmove (?:1|101))$')


def utc():
    return datetime.now(timezone.utc).isoformat()


def announce(phase, status='started', **details):
    """Small flushed records make long verification/copy phases observable."""
    print('COH_CHARACTER_PROGRESS ' + json.dumps({'time_utc': utc(), 'phase': phase,
                                                  'status': status, **details}), flush=True)


def source_contract(root=ROOT):
    base = root / 'upstream/ouroboros'
    paths = {
        'main': 'Utilities/TestClient/src/main.c',
        'commands': 'Utilities/TestClient/src/testClientCmdParse.c',
        'status': 'DBServer/src/status.c',
        'scene': 'Game/src/clientcomm/clientcomm.c',
        'character_list': 'Game/src/clientcomm/dbclient.c',
        'entity_receive': 'Game/src/entity/entrecv.c',
        'server_ready': 'MapServer/src/svr/svr_tick.c',
        'server_commands': 'MapServer/src/cmdparse/cmdserver.c',
        'logout': 'Utilities/TestClient/src/externs.c',
        'debug': 'MapServer/src/cmdparse/cmdservercsr.c',
        'chat': 'Utilities/TestClient/src/chatter.c',
        'windows_entry': 'Utilities/TestClient/src/win_init.c',
        'console': 'libs/UtilitiesLib/src/utils/utils.c',
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
        'scene': ('CLIENT_REQSCENE', 'commCheck(SERVER_GROUPS)', 'commCheck(SERVER_ALLENTS)', 'CLIENT_READY',
                  'case SERVER_UPDATE:', 'entReceiveUpdate(pak,cmd==SERVER_ALLENTS);'),
        'server_ready': ('xcase CLIENT_READY:', 'client->ready = CLIENTSTATE_ENTERING_GAME;',
                         'client->ready=CLIENTSTATE_IN_GAME;', 'entSendUpdate('),
        'character_list': ('db_info.players = calloc(db_info.max_slots,sizeof(db_info.players[0]));',
                           'Strncpyt(db_info.players[i].name,pktGetString(pak));'),
        'entity_receive': ('db_id = pktGetBitsPack(pak,PKT_BITS_TO_REP_DB_ID);',),
        'server_commands': ('xcase SCMD_INFLUENCE:', 'ent_SetInfluence(e, tmp_int);'),
        'logout': ('FatalErrorf("Booted back to login screen");',),
        'debug': ('char * csrPlayerInfo(', 'localizedPrintf(e,"CSRInfo1")',
                  'localizedPrintf(e,"CSRInfo2")', 'localizedPrintf(e,"CSRInfo8a")', 'e->pchar->iInfluencePoints'),
        'chat': ('PipeClientSendMessage(pc,"ChatText:%s",str);',),
        'windows_entry': ('int APIENTRY _tWinMain(', 'newConsoleWindow();', 'return main(argc,argv);'),
        'console': ('if (AllocConsole())', 'freopen("CONOUT$", "w", stdout);', 'setvbuf( stdout, NULL, _IONBF, 0 );'),
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
    # Stock query stdout can contain normal shutdown diagnostics after the
    # response. Parse one physical line at a time: multiline \s* may cross its
    # CRLF and misclassify the next diagnostic as character status flags.
    pattern = re.compile(r'\s*(\d+)\s+Name\s+(.+?)\s+Auth\s+(\S+)\s+Ip\s+(\S+)\s+'
                         r'MapId\s+(\d+)\s+SmapId\s+(\d+)\s*(.*?)\s*')
    matches = [match.groups() for line in text.splitlines() if (match := pattern.fullmatch(line))]
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


def live_currency_evidence(events, name, account, after_sequence, expected=INFLUENCE):
    """Only the stock server's conPrintf response identifies the live entity.

    Ordinary player chat containing these words cannot satisfy the diagnostic.
    The CMD debug reply reads the MapServer entity; no SQL write/forced save is
    used to make the currency visible before protocol logout.
    """
    require(type(expected) is int and expected in (INFLUENCE, SECOND_INFLUENCE), 'Unreviewed live currency target')
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
        if int(values[0]) == expected:
            accepted.append({'player': name, 'account': account, 'influence': expected,
                             'time_utc': event['time_utc'], 'sequence': event['sequence']})
    return accepted[-1] if accepted else False


def client_command(runtime, account, name=None, resume_only=False):
    require(re.fullmatch(r'[A-Za-z][A-Za-z0-9]{1,19}', account), 'Unsafe diagnostic account name')
    require(not resume_only or name is not None, 'Resume-only requires an explicit recorded name')
    command = [str(runtime / ('TestClientResume.exe' if resume_only else 'TestClient.exe')),
               '-db', '127.0.0.1', '-fakeauth', '-authname', account,
               '-dontpause', '-nosharedmemory']
    if name is None:
        return command + ['-nolevel', '-TEAMACCEPT', '-FOLLOW', '-SUPERGROUPACCEPT', '-LEAGUEACCEPT']
    require(name and len(name) <= 128 and not any(ord(c) < 32 for c in name), 'Invalid recorded character name')
    if resume_only:
        return command + ['-resumeonly', '-character', name]
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


def resume_branch(text, name):
    require(not diagnostic_failures(text), 'Resume probe emitted failure diagnostics')
    require('simulateCharacterCreate' not in text and not re.search(r'Character creation|Create a new character', text, re.I),
            'Short resume attempted character creation')
    matches = re.findall(r'^Found character (.+) in slot (\d+)\s*$', text, re.M)
    require(len(matches) == 1 and matches[0][0] == name, 'Exact-name existing-character match was not observed')
    slot = int(matches[0][1])
    require(re.search(r'Resuming character in slot ' + str(slot) + r'\.\.\.', text) and 'commReqScene()' in text,
            'Resume branch/scene exchange diagnostic is missing')
    return slot


def accept_resume(text, state, pid, account, name, exit_code):
    require(exit_code == 0, 'Short resume probe did not exit cleanly')
    slot = resume_branch(text, name)
    require(pipe_identity(state, pid, account, name) == name, 'Resume lacks returned player/map identity')
    return {'slot': slot, 'scene_exchange_observed': True, 'creation_disabled': True,
            'active_gameplay_confirmed': False, 'scope': 'Short resume/scene probe; queued CLIENT_READY processing is unproven'}


def active_pipe_identity(state, pid, account, name):
    require(not state.get('disconnected') and not state.get('quit_now'), 'Sustained client pipe disconnected or requested quit')
    require(not any(event['kind'] == 'QuitNow' for event in state.get('events', [])), 'Premature sustained session logout')
    return pipe_identity(state, pid, account, name)


def accept_sustained_resume(text, state, pid, account, name, identifier, exit_code):
    require(exit_code is None, 'Sustained resume client exited before session observation')
    slot = resume_branch(text, name)
    # Character-list packets contain name/slot, not db_id. The latter remains
    # zero in DbPlayer; the actual ID is received in the map entity update.
    matches = [match.groups() for line in text.splitlines() if
               (match := re.fullmatch(r'COH_RESUME_ONLY_SELECTED slot=(\d+) name=(.+)', line))]
    require(len(matches) == 1 and int(matches[0][0]) == slot and matches[0][1] == name,
            'Resume-only selection lacks the exact name and slot')
    require('COH_RESUME_ONLY_MISSING' not in text, 'Positive resume reported a missing character')
    updates = [line for line in text.splitlines() if line.startswith('COH_RESUME_ONLY_SERVER_UPDATE')]
    require(type(identifier) is int and identifier > 0 and
            updates == [f'COH_RESUME_ONLY_SERVER_UPDATE id={identifier} name={name}'],
            'Resume lacks one processed server update for the original player database ID/name')
    require(active_pipe_identity(state, pid, account, name) == name, 'Sustained resume lacks live player/map pipe identity')
    return {'slot': slot, 'database_id': identifier, 'database_id_source': 'processed MapServer player entity update',
            'exact_name': name, 'creation_disabled': True,
            'scene_exchange_observed': True, 'processed_server_update_for_original_player': True,
            'active_gameplay_confirmed': False,
            'scope': 'Connected existing-character session; combat, movement and rendered gameplay unvalidated'}


def accept_missing_name(text, state, pid, account, name, exit_code):
    require(exit_code == 3, 'Missing-name probe did not take the explicit resume-only refusal exit')
    require(not diagnostic_failures(text), 'Missing-name probe emitted unexpected failure diagnostics')
    require([line for line in text.splitlines() if line.startswith('COH_RESUME_ONLY_MISSING')] ==
            ['COH_RESUME_ONLY_MISSING name=' + name], 'Missing-name refusal does not identify exactly the requested name')
    require(not any(fragment in text for fragment in
                    ('COH_RESUME_ONLY_SELECTED', 'Found character', 'Resuming character',
                     'COH_RESUME_ONLY_SERVER_UPDATE', 'simulateCharacterCreate', 'commReqScene()')) and
            not re.search(r'Character creation|Create a new character', text, re.I),
            'Missing-name probe attempted creation, selection or scene exchange')
    require(not state.get('error') and state.get('pid_verified') and state.get('client_pid') == pid and
            state.get('version_requests') == 1, 'Missing-name probe lacks verified launcher transport')
    require(not state.get('player') and not state.get('map_name') and not state.get('quit_now'),
            'Missing-name probe entered a character session')
    for event in state.get('events', []):
        require(event['kind'] not in ('Player', 'MapName', 'QuitNow') and
                not (event['kind'] == 'Status' and event['value'] in ('Running', 'CRASH')),
                'Missing-name probe emitted session or failure events')
        if event['kind'] == 'AuthName':
            require(event['value'] == account, 'Missing-name account identity differs')
    require(sum(event['kind'] == 'Status' and event['value'] == 'ERROR' for event in state.get('events', [])) == 1,
            'Missing-name refusal must carry exactly its explicit ERROR status')
    return {'requested_name': name, 'exit_code': exit_code, 'explicit_refusal': True,
            'creation_or_scene_observed': False, 'counts_as_login_or_save': False}


def accept_session_samples(samples, seconds):
    require(30 <= seconds <= 300 and len(samples) >= 3, 'Sustained session observation is incomplete')
    previous = None
    for sample in samples:
        elapsed = sample['elapsed_seconds']
        require(type(elapsed) in (int, float) and elapsed >= 0, 'Invalid sustained session timing')
        if previous is not None:
            require(0 < elapsed - previous <= 20, 'Sustained session sampling has an excessive gap')
        previous = elapsed
        map_sample = sample['map']
        require(map_sample.get('ready') is True and map_sample.get('port') == one_map.MAP_UDP_PORT and
                all(type(map_sample.get(key)) is int and 0 <= map_sample[key] <= 20
                    for key in ('network_age_seconds', 'stats_age_seconds')),
                'Sustained session map heartbeat/readiness is stale')
        require(connected_on_atlas(sample['character']), 'Sustained character disconnected or left Atlas Park')
    observed = samples[-1]['elapsed_seconds'] - samples[0]['elapsed_seconds']
    require(observed >= seconds, 'Sustained session duration was shorter than requested')
    return {'required_seconds': seconds, 'observed_seconds': observed, 'sample_count': len(samples),
            'maximum_sample_gap_seconds': max(b['elapsed_seconds'] - a['elapsed_seconds']
                                            for a, b in zip(samples, samples[1:])),
            'connected_map_id': one_map.MAP_ID, 'current_server_heartbeats': True}


def selected_pipe_record(state):
    # Arbitrary chat, host information and full SCREEN/container messages stay private.
    kinds = {'PID', 'AuthName', 'Player', 'MapName', 'Status', 'QuitNow', 'VersionRequest'}
    return {key: state.get(key) for key in ('client_pid', 'pid_verified', 'version_requests', 'disconnected')} | {
        'events': [{key: event[key] for key in ('kind', 'value', 'time_utc', 'sequence')}
                   for event in state.get('events', []) if event['kind'] in kinds]}


def run(runtime, reference, schema_report, comparison_report, comparison_inputs, one_map_report,
        work, output, pg_bin, driver, port=15437, timeout=900, phase_timeout=300,
        schema_archive=None, comparison_archive=None, diagnostic_version=None, root=ROOT,
        resume_client_package=None, expected_resume_repository_commit=None, session_seconds=60,
        map_transfer=False):
    runtime, reference, work, output = [Path(p).resolve() for p in (runtime, reference, work, output)]
    network.new_paths(runtime, reference, work, output, root)
    require(60 <= timeout <= 1800 and 30 <= phase_timeout <= 900, 'Timeouts must be startup60..1800 and phase30..900 seconds')
    require(30 <= session_seconds <= 300, 'Sustained observation must be30..300seconds')
    require(bool(resume_client_package) == bool(expected_resume_repository_commit),
            'Resume client package and expected repository commit must be supplied together')
    require(type(map_transfer) is bool and (not map_transfer or resume_client_package),
            'Map transfer requires the separately verified resume-only client package')
    announce('input_verification')
    context, outputs, tables, map_contract = one_map.preflight(runtime, reference, Path(schema_report),
        Path(comparison_report), Path(comparison_inputs), Path(schema_archive) if schema_archive else None,
        Path(comparison_archive) if comparison_archive else None, root)
    accept_one_map(one_map.comparison.regular_json(Path(one_map_report)), context,
                   sha256(Path(comparison_report)), sha256(Path(comparison_inputs)))
    contract = source_contract(root)
    selection = snapshots.selected_contract(tables)
    resume_executable, resume_manifest = None, None
    if resume_client_package:
        from package_resume_client import verify_resume_client_package
        resume_executable, resume_manifest = verify_resume_client_package(
            Path(resume_client_package), expected_resume_repository_commit, context['package'], root=root)
    transfer_contract = transfers.source_contract(root) if map_transfer else None
    if map_transfer:
        require(resume_manifest['resume_client_build_input'].get('transfer_proof') == transfers.PROOF,
                'Diagnostic client lacks the reviewed processed transfer-update proof')
    announce('input_verification', 'passed')
    require(os.name == 'nt', 'This stock named-pipe harness requires the Windows reference host')
    version_source = 'explicit diagnostic override' if diagnostic_version else 'reference package'
    version = diagnostic_version or context['package'].get('client_version') or context['package'].get('patch_version')
    if not version:
        version, version_source = 'coh-persistence-diagnostic', 'diagnostic fallback; reference package contains no patch version'
    require(isinstance(version, str) and re.fullmatch(r'[\x20-\x7e]{1,128}', version), 'Invalid diagnostic version')
    port_checks = one_map.preflight_ports(port)
    if map_transfer:
        port_checks.append(transfers.preflight_clone_port())
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
        'testclient_console_capture': 'Owned helper attaches to stock GUI console before launcher version reply and retains bounded screen buffer through client exit',
        'character_persistence_validated': False, 'gameplay_validated': False, 'android_execution_validated': False,
        'scope': 'Fresh fake-auth create, influence command, protocol logout, committed SQL, service restart and short exact-name resume',
        'network_scope': 'Loopback queries; stock game listeners still bind INADDR_ANY on the private disposable host',
        'raw_evidence_private': True, 'status_samples': [], 'character_status_samples': [], 'snapshots': {}}
    if resume_manifest:
        report.update(resume_client_package=resume_manifest, sustained_session_validated=False,
            scope='Fresh stock-client create/save, service restart, diagnostic-client missing-name refusal, sustained exact-name resume and second protocol save',
            sustained_observation_required_seconds=session_seconds)
    if map_transfer:
        report.update(map_transfer_contract=transfer_contract, map_transfer_validated=False,
            scope='Fresh character/save/restart, missing-name refusal, sustained resume, Atlas1 to clone101 to Atlas1, then second protocol save',
            transfer_legs=[], transfer_map_startup={})
    cluster, processes, pipes, consoles, services, secrets = None, [], [], [], [], []
    requested_logout = False
    active_client_logs = {'console': None, 'logout_requested': False}
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
        for console in consoles:
            console.check_bounds()
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
        # Aggregate logs retain the first client's accepted post-quit records.
        # Its exception must never apply to a later, still-connected client.
        if active_client_logs['console'] is not None:
            require(not diagnostic_failures(active_client_logs['console'].text(),
                    allow_requested_logout=active_client_logs['logout_requested']),
                    'Active client emitted failure diagnostics outside its own requested logout')
        require(not errors, 'Observed failure diagnostics:\n' + '\n'.join(errors[:30]))
        return text

    def wait(predicate, seconds, label, client=None):
        started = time.monotonic()
        deadline, progress_at = started + seconds, started + 30
        announce(label)
        while True:
            health()
            result = predicate()
            if result:
                announce(label, 'observed', elapsed_seconds=round(time.monotonic() - started, 1))
                return result
            if client is not None:
                require(client.poll() is None, 'TestClient exited before ' + label)
            require(time.monotonic() < deadline, 'Timed out waiting for ' + label)
            if time.monotonic() >= progress_at:
                announce(label, 'waiting', elapsed_seconds=round(time.monotonic() - started, 1))
                progress_at = time.monotonic() + 30
            time.sleep(0.2)

    def map_status(label, allow_missing=False, map_id=one_map.MAP_ID):
        text = query(['-getstatus', '1', str(map_id)], label)
        sample = (transfers.parse_map_status(text, map_id, allow_missing) if map_transfer else
                  one_map.parse_status(text, allow_missing=allow_missing))
        sample['sampled_utc'] = utc()
        report['status_samples'].append(sample)
        return sample

    def start_services(phase):
        announce(phase + '_services')
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
        announce(phase + '_services_ready', 'passed')

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

    def sustained_session(identifier, name, before, attr_before):
        nonlocal requested_logout
        require(before['login_count'] == 1, 'Fresh stock session must have exactly one committed login')
        inventory = snapshots.character_inventory(cluster, tables)
        require(inventory == [dict(before['identity'], logincount=1)],
                'Disposable database must contain exactly the one recorded character')
        # Diagnostic executable is additional; accepted stock bytes are never
        # overwritten, and only this opt-in branch can execute it.
        diagnostic_client = isolated / 'TestClientResume.exe'
        require(not diagnostic_client.exists(), 'Unexpected diagnostic client already exists in accepted runtime')
        shutil.copy2(resume_executable, diagnostic_client)
        require(sha256(diagnostic_client) == sha256(resume_executable) ==
                resume_manifest['files']['TestClient.exe']['sha256'],
                'Staged diagnostic executable differs from the verified build receipt')
        report['diagnostic_testclient_sha256'] = sha256(diagnostic_client)
        missing_name = 'CohAbsent' + random_secrets.token_hex(6)
        require(missing_name != name, 'Negative probe name unexpectedly equals the saved character')
        negative_pipe = TestClientPipe(version)
        negative_pipe.__enter__()
        pipes.append(negative_pipe)
        negative = start(client_command(isolated, account, missing_name, resume_only=True), 'missing-name-client')
        negative_console = ConsoleCapture(negative.child.pid, logs, 'missing-name-client')
        consoles.append(negative_console)
        negative_console.start(timeout=10)
        negative_pipe.bind_process(negative.child.pid)
        wait(lambda: negative.poll() is not None, phase_timeout, 'missing-name refusal process completion')
        negative_console.stop()
        wait(lambda: negative_pipe.snapshot().get('disconnected'), 5, 'missing-name pipe drain')
        negative_state = negative_pipe.snapshot()
        report['missing_name_probe'] = accept_missing_name(negative_console.text(), negative_state,
            negative.child.pid, account, missing_name, negative.child.returncode)
        require(not negative.forced_stop, 'Forced termination cannot establish missing-name refusal')
        after_negative = snapshots.capture(cluster, tables, account, identifier, name, expected_influence=INFLUENCE)
        report['missing_name_comparison'] = snapshots.compare(before, after_negative, phase='missing_name')
        snapshots.validate_attribute_references(after_negative, attr_before)
        snapshots.compare_attributes(attr_before, attributes())
        after_inventory = snapshots.character_inventory(cluster, tables)
        require(after_inventory == inventory, 'Missing-name probe changed the database character inventory')
        require(not char_status(identifier, name, 'missing_name', allow_missing=True)['connected'],
                'Missing-name probe connected the existing character')
        report['missing_name_probe'].update(character_count_before=len(inventory),
                                           character_count_after=len(after_inventory),
                                           independent_sql_unchanged=True)
        report['snapshots']['after_missing_name_refusal'] = after_negative
        report['missing_name_session_pipe'] = selected_pipe_record(negative_state)
        negative.stop()
        negative_pipe.close()
        logs_clean()
        report['phases'].append({'phase': 'missing_name_refused_without_mutation', 'time_utc': utc(), 'status': 'passed'})
        announce('missing_name_refused_without_mutation', 'passed')

        sustained_pipe = TestClientPipe(version)
        sustained_pipe.__enter__()
        pipes.append(sustained_pipe)
        resumed = start(client_command(isolated, account, name, resume_only=True), 'sustained-resume-client')
        resumed_console = ConsoleCapture(resumed.child.pid, logs, 'sustained-resume-client')
        consoles.append(resumed_console)
        resumed_console.start(timeout=10)
        active_client_logs.update(console=resumed_console, logout_requested=False)
        sustained_pipe.bind_process(resumed.child.pid)
        wait(lambda: active_pipe_identity(sustained_pipe.snapshot(), resumed.child.pid, account, name),
             phase_timeout, 'sustained resume launcher identity', resumed)
        wait(lambda: 'COH_RESUME_ONLY_SELECTED' in resumed_console.text() and
             'COH_RESUME_ONLY_SERVER_UPDATE' in resumed_console.text(), phase_timeout,
             'captured sustained resume and processed server update', resumed)
        report['resume_probe'] = accept_sustained_resume(resumed_console.text(), sustained_pipe.snapshot(),
            resumed.child.pid, account, name, identifier, resumed.poll())
        wait(lambda: connected_on_atlas(char_status(identifier, name, 'resumed')), phase_timeout,
             'resumed original character connected on Atlas Park', resumed)

        def observe_currency(expected, label, map_id=one_map.MAP_ID):
            current_events = sustained_pipe.snapshot()['events']
            sequence = current_events[-1]['sequence'] if current_events else -1
            next_debug = 0

            def response():
                nonlocal next_debug
                state = sustained_pipe.snapshot()
                require(active_pipe_identity(state, resumed.child.pid, account, name) == name,
                        'Resumed character pipe identity was lost')
                require(not diagnostic_failures(resumed_console.text()), 'Resumed client emitted failure diagnostics')
                evidence = live_currency_evidence(state['events'], name, account, sequence, expected)
                if evidence:
                    ownership = char_status(identifier, name, label)
                    connected = (transfers.connected(ownership, map_id) if map_transfer else
                                 connected_on_atlas(ownership))
                    require(connected,
                            'Resumed character disconnected before live currency response')
                    require(resumed.poll() is None, 'Resumed client exited before live currency response')
                    return evidence
                if time.monotonic() >= next_debug:
                    sustained_pipe.send('CMD debug "' + name + '"')
                    next_debug = time.monotonic() + 3
                return False

            return wait(response, phase_timeout, label, resumed)

        def roundtrip():
            """Use two owned servers; do not infer arrival from their shared name."""
            require(not transfers.updates(resumed_console.text(), identifier, name),
                    'Unrequested map transfer occurred before the round-trip gate')
            baseline = map_status('clone101-baseline', allow_missing=True, map_id=transfers.CLONE_ID)
            require(not baseline['ready'] and baseline.get('not_started') is True,
                    'Clone101 was already running or has no explicit unstarted baseline')
            report['transfer_map_startup']['baseline'] = baseline
            services.append(start(transfers.map_command(isolated), 'atlas-clone101'))

            def clone_ready():
                require(active_pipe_identity(sustained_pipe.snapshot(), resumed.child.pid, account, name) == name,
                        'Character lost its live pipe while the destination started')
                require(not diagnostic_failures(resumed_console.text()), 'Client failed while the destination started')
                sample = map_status('clone101-ready-' + str(len(report['status_samples'])), map_id=transfers.CLONE_ID)
                return sample if transfers.ready(sample, transfers.CLONE_ID) else False

            ready_clone = wait(clone_ready, timeout, 'owned Atlas clone101 protocol readiness', resumed)
            report['transfer_map_startup']['ready'] = ready_clone
            report['phases'].append({'phase': 'clone101_prestarted_ready', 'time_utc': utc(), 'status': 'passed',
                                    'map_id': transfers.CLONE_ID, 'udp_port': transfers.PORTS[transfers.CLONE_ID]})
            previous_arrival = None
            for epoch, origin, destination in ((1, transfers.HOME_ID, transfers.CLONE_ID),
                                               (2, transfers.CLONE_ID, transfers.HOME_ID)):
                require(len(transfers.updates(resumed_console.text(), identifier, name)) == epoch - 1,
                        'Transfer history changed before the next requested leg')
                source_state = char_status(identifier, name, 'transfer' + str(epoch) + '_departure')
                require(transfers.connected(source_state, origin), 'Character is not owned by the expected departure map')
                before_maps = {str(map_id): map_status('transfer' + str(epoch) + '-before-map' + str(map_id), map_id=map_id)
                               for map_id in transfers.PORTS}
                require(all(transfers.ready(before_maps[str(map_id)], map_id) for map_id in transfers.PORTS),
                        'Both owned maps must be ready with fresh heartbeats before transfer')
                leg = {'epoch': epoch, 'from_map_id': origin, 'to_map_id': destination,
                       'requested_utc': utc(), 'command': 'mapmove ' + str(destination),
                       'departure_character_status': source_state, 'maps_before': before_maps}
                report['transfer_legs'].append(leg)
                sustained_pipe.send('CMD mapmove ' + str(destination))

                def arrived():
                    require(active_pipe_identity(sustained_pipe.snapshot(), resumed.child.pid, account, name) == name,
                            'Character pipe identity was lost during transfer')
                    text = resumed_console.text()
                    require(not diagnostic_failures(text), 'Client emitted failure diagnostics during transfer')
                    markers = transfers.updates(text, identifier, name)
                    require(len(markers) <= epoch, 'Client completed an unrequested extra transfer')
                    if len(markers) < epoch:
                        return False
                    map_sample = map_status('transfer' + str(epoch) + '-arrival-map-' + str(len(report['status_samples'])),
                                            map_id=destination)
                    character_sample = char_status(identifier, name, 'transfer' + str(epoch) + '_arrival')
                    if not transfers.ready(map_sample, destination) or not transfers.connected(character_sample, destination):
                        return False
                    evidence = transfers.accept_arrival(text, identifier, name, epoch, map_sample, character_sample)
                    return {'processed_update': evidence, 'map_status': map_sample, 'character_status': character_sample,
                            'observed_utc': utc()}

                leg['arrival'] = wait(arrived, phase_timeout, 'transfer' + str(epoch) + ' processed update and exact destination', resumed)
                leg['live_currency'] = observe_currency(INFLUENCE, 'transfer' + str(epoch) + ' live currency', destination)

                def transfer_saved():
                    require(active_pipe_identity(sustained_pipe.snapshot(), resumed.child.pid, account, name) == name,
                            'Character pipe identity was lost before transfer SQL evidence')
                    try:
                        current = snapshots.capture(cluster, tables, account, identifier, name, expected_influence=INFLUENCE)
                        comparison = snapshots.compare_transfer(before, current, previous_arrival)
                        return current, comparison
                    except ValueError as error:
                        leg['last_pending_committed_update'] = redact(str(error), secrets)
                        return False

                current, comparison = wait(transfer_saved, phase_timeout, 'transfer' + str(epoch) + ' committed selected SQL', resumed)
                snapshots.validate_attribute_references(current, attr_before)
                snapshots.compare_attributes(attr_before, attributes())
                require(snapshots.character_inventory(cluster, tables) == [dict(current['identity'], logincount=2)],
                        'Transfer changed the one-character database inventory')
                leg['sql_comparison'] = comparison
                leg['committed_sql_observed_utc'] = utc()
                report['snapshots']['after_transfer' + str(epoch)] = current
                previous_arrival = current
                after_map = map_status('transfer' + str(epoch) + '-settled-map', map_id=destination)
                after_character = char_status(identifier, name, 'transfer' + str(epoch) + '_settled')
                transfers.accept_arrival(resumed_console.text(), identifier, name, epoch, after_map, after_character)
                require(resumed.poll() is None and active_pipe_identity(sustained_pipe.snapshot(), resumed.child.pid,
                        account, name) == name, 'Client disconnected after transfer evidence')
                leg.update(status='passed', settled_utc=utc(), settled_map_status=after_map,
                           settled_character_status=after_character, account_character_count=1)
                logs_clean()
                report['phases'].append({'phase': 'transfer' + str(epoch) + '_arrived_and_committed', 'time_utc': utc(),
                                        'status': 'passed', 'map_id': destination, 'udp_port': transfers.PORTS[destination]})
                announce('transfer' + str(epoch) + '_arrived_and_committed', 'passed', map_id=destination)

        report['restored_live_currency_evidence'] = observe_currency(INFLUENCE, 'restored live currency')
        report['phases'].append({'phase': 'restored_currency_while_connected', 'time_utc': utc(),
                                'status': 'passed', 'value': INFLUENCE})
        samples = report['sustained_session_samples'] = []
        observation_start = time.monotonic()
        announce('sustained_connected_observation', required_seconds=session_seconds)
        while True:
            health()
            require(resumed.poll() is None, 'Resumed client exited during sustained observation')
            require(active_pipe_identity(sustained_pipe.snapshot(), resumed.child.pid, account, name) == name,
                    'Resumed character lost launcher identity during observation')
            require(not diagnostic_failures(resumed_console.text()), 'Resumed client failed during sustained observation')
            map_sample = map_status('sustained-map-' + str(len(samples)))
            character_sample = char_status(identifier, name, 'sustained')
            elapsed = time.monotonic() - observation_start
            samples.append({'sampled_utc': utc(), 'elapsed_seconds': elapsed,
                            'map': map_sample, 'character': character_sample})
            require(resumed.poll() is None, 'Resumed client exited during status sampling')
            require(map_sample.get('ready') and map_sample.get('port') == one_map.MAP_UDP_PORT and
                    map_sample['network_age_seconds'] <= 20 and map_sample['stats_age_seconds'] <= 20 and
                    connected_on_atlas(character_sample), 'Resumed character or current map heartbeat was lost')
            require(elapsed <= session_seconds + 30, 'Sustained session observation exceeded its bound')
            if elapsed - samples[0]['elapsed_seconds'] >= session_seconds:
                break
            if len(samples) % 5 == 0:
                announce('sustained_connected_observation', 'observing', elapsed_seconds=round(elapsed, 1))
            time.sleep(3)
        report['sustained_observation'] = accept_session_samples(samples, session_seconds)
        report['restored_live_currency_after_observation'] = observe_currency(INFLUENCE, 'restored currency after observation')
        report['phases'].append({'phase': 'sustained_connected_observation', 'time_utc': utc(), 'status': 'passed',
                                **report['sustained_observation']})
        announce('sustained_connected_observation', 'passed', **report['sustained_observation'])
        if map_transfer:
            roundtrip()
        sustained_pipe.send('CMD influence ' + str(SECOND_INFLUENCE))
        report['second_influence_requested_utc'] = utc()
        report['second_live_currency_evidence'] = observe_currency(SECOND_INFLUENCE, 'second live currency')
        report['phases'].append({'phase': 'second_influence_observed_while_connected', 'time_utc': utc(),
                                'status': 'passed', 'value': SECOND_INFLUENCE})
        logs_clean()
        require(not diagnostic_failures(resumed_console.text()), 'Resumed client failed before second protocol quit')
        requested_logout = True
        active_client_logs['logout_requested'] = True
        report['second_quit_requested_utc'] = utc()
        sustained_pipe.send('CMD quit')
        wait(lambda: sustained_pipe.snapshot().get('quit_now'), 15, 'second QuitNow request confirmation')

        def second_saved():
            state = sustained_pipe.snapshot()
            pipe_identity(state, resumed.child.pid, account, name, allow_logout_error=True)
            status = char_status(identifier, name, 'second_logout', allow_missing=True)
            if status['connected'] or status['in_map_transfer']:
                time.sleep(1)
                return False
            try:
                current = snapshots.capture(cluster, tables, account, identifier, name, expected_influence=SECOND_INFLUENCE)
                comparison = snapshots.compare(before, current, phase='second_logout')
                return current, comparison
            except ValueError as error:
                report['last_pending_second_save'] = redact(str(error), secrets)
                return False

        final, comparison = wait(second_saved, phase_timeout, 'second protocol logout and committed SQL')
        require(not resumed.forced_stop, 'Forced disconnect cannot establish second protocol logout')
        state = sustained_pipe.snapshot()
        if any(e['kind'] == 'Status' and e['value'] == 'ERROR' for e in state['events']):
            require(any(EXPECTED_LOGOUT.fullmatch(line) for line in resumed_console.text().splitlines()),
                    'Second post-quit ERROR lacks exact stock logout diagnostic')
        require(not diagnostic_failures(resumed_console.text(), allow_requested_logout=True),
                'Resumed client emitted unexpected post-quit failure diagnostics')
        snapshots.validate_attribute_references(final, attr_before)
        snapshots.compare_attributes(attr_before, attributes())
        require(snapshots.character_inventory(cluster, tables) == [dict(final['identity'], logincount=2)],
                'Second session created or changed an unexpected character')
        report['snapshots']['after_second_protocol_logout'] = final
        report['second_logout_comparison'] = comparison
        report['resume_session_pipe'] = selected_pipe_record(state)
        report['phases'].append({'phase': 'second_protocol_logout_committed', 'time_utc': utc(), 'status': 'passed',
                                'quitnow_is_save_ack': False, 'client_forced_stop_before_commit': resumed.forced_stop})
        logs_clean()
        resumed_console.stop()
        resumed_console.check_bounds()
        resumed.stop()
        active_client_logs['console'] = None
        sustained_pipe.close()
        validate_catalog(catalog_snapshot(cluster), tables)
        final_map = map_status('final-sustained-map-status')
        require(final_map['ready'] and final_map['network_age_seconds'] <= 20 and final_map['stats_age_seconds'] <= 20,
                'Map lost readiness/current heartbeat after second protocol save')
        report['sustained_session_validated'] = True
        report['character_persistence_validated'] = True
        report['status'] = SESSION_SUCCESS
        if map_transfer:
            require(len(report['transfer_legs']) == 2 and all(leg.get('status') == 'passed' for leg in report['transfer_legs']),
                    'Both requested map-transfer legs must pass before final acceptance')
            final_clone = map_status('final-transfer-clone101-status', map_id=transfers.CLONE_ID)
            require(transfers.ready(final_map, transfers.HOME_ID) and transfers.ready(final_clone, transfers.CLONE_ID),
                    'Owned maps lost readiness after completed round trip and protocol save')
            report['map_transfer_validated'] = True
            report['status'] = TRANSFER_SUCCESS
        announce('second_protocol_logout_committed', 'passed')

    try:
        announce('private_runtime_copy')
        for copied, (name, path) in enumerate(input_files(runtime), 1):
            target = isolated / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            if copied % 20000 == 0:
                announce('private_runtime_copy', 'copying', file_count=copied)
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
        announce('private_runtime_and_database', 'prepared')
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
        console = ConsoleCapture(client.child.pid, logs, 'create-client')
        consoles.append(console)
        console.start(timeout=10)
        active_client_logs.update(console=console, logout_requested=False)
        # The stock client blocks waiting for the launcher version. The pipe
        # drains only after this PID bind, so its console is owned/captured
        # before creation diagnostics or a short resume can complete.
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
        wait(lambda: 'simulateCharacterCreate()' in console.text(), 5, 'captured fresh creation branch', client)
        logs_clean()
        report['phases'].append({'phase': 'created_connected', 'time_utc': utc(), 'status': 'passed'})
        announce('created_connected', 'passed')
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
        active_client_logs['logout_requested'] = True
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
            require(any(EXPECTED_LOGOUT.fullmatch(line) for line in console.text().splitlines()),
                    'Post-quit ERROR lacks the exact stock logout diagnostic')
        report['snapshots']['after_protocol_logout'] = before
        report['first_session_pipe'] = selected_pipe_record(state)
        report['phases'].append({'phase': 'protocol_logout_committed', 'time_utc': utc(), 'status': 'passed',
                                'quitnow_is_save_ack': False, 'client_forced_stop_before_commit': client.forced_stop})
        announce('protocol_logout_committed', 'passed')
        require(not client.forced_stop, 'Forced disconnect cannot establish protocol logout')
        logs_clean()
        # taskkill /T can also end the GUI child's conhost. Take the final
        # owned-console snapshot before that cleanup, after logout/save proof.
        console.stop()
        console.check_bounds()
        client.stop()  # Cleanup occurs only after independently proven logout/save.
        active_client_logs['console'] = None
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
        announce('restart_saved_state', 'passed')

        if resume_manifest:
            sustained_session(identifier, name, before, attr_before)
        else:
            resume_pipe = TestClientPipe(version)
            resume_pipe.__enter__()
            pipes.append(resume_pipe)
            resume = start(client_command(isolated, account, name), 'resume-client')
            resume_console = ConsoleCapture(resume.child.pid, logs, 'resume-client')
            consoles.append(resume_console)
            resume_console.start(timeout=10)
            resume_pipe.bind_process(resume.child.pid)
            wait(lambda: resume.poll() is not None, phase_timeout, 'short resume probe process completion')
            resume_console.stop()  # Captures the retained console once more after child exit.
            wait(lambda: pipe_identity(resume_pipe.snapshot(), resume.child.pid, account, name), 5,
                 'short resume pipe drain')
            report['resume_probe'] = accept_resume(resume_console.text(), resume_pipe.snapshot(), resume.child.pid,
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
            announce('short_resume_and_committed_state', 'passed')
            report['character_persistence_validated'] = True
            report['status'] = SUCCESS
    except (OSError, ValueError, RuntimeError, AssertionError, subprocess.SubprocessError) as error:
        report['failures'].append(redact(str(error), secrets))
        announce('character_persistence', 'failed', diagnostic=redact(str(error), secrets))
    finally:
        # Final snapshots must precede forced client-tree cleanup. The normal
        # short resume explicitly captures after its unforced exit above.
        for console in reversed(consoles):
            try:
                console.stop()
                console.check_bounds()
            except Exception as error:
                report['failures'].append('Console cleanup: ' + redact(str(error), secrets))
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
                state = pipe.snapshot()
                private_write(work / f'launcher-session-{index}.json', json.dumps(state, indent=2) + '\n')
                report.setdefault('launcher_sessions', []).append(selected_pipe_record(state))
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
            if resume_manifest:
                report['sustained_session_validated'] = False
            if map_transfer:
                report['map_transfer_validated'] = False
        report['processes'] = [process.record() for process in processes]
        report['console_observers'] = [console.report() for console in consoles]
        report['shutdown_scope'] = 'Owned disposable processes stopped; graceful whole-server shutdown remains unvalidated'
        report['finished_utc'] = utc()
        (output / 'character-persistence-report.json').write_text(redact(json.dumps(report, indent=2) + '\n', secrets), encoding='utf-8')
        announce('cleanup_and_evidence', 'complete', result=report['status'], failure_count=len(report['failures']))
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
    parser.add_argument('--resume-client-package', type=Path)
    parser.add_argument('--expected-resume-repository-commit')
    parser.add_argument('--session-seconds', type=float, default=60)
    parser.add_argument('--map-transfer', action='store_true')
    args = parser.parse_args()
    result = run(args.runtime, args.reference_binaries, args.schema_report, args.comparison_report,
                 args.comparison_inputs, args.one_map_report, args.work, args.output, args.bin, args.driver,
                 args.port, args.timeout_seconds, args.phase_timeout_seconds, args.schema_archive,
                 args.comparison_archive, args.diagnostic_version,
                 resume_client_package=args.resume_client_package,
                 expected_resume_repository_commit=args.expected_resume_repository_commit,
                 session_seconds=args.session_seconds, map_transfer=args.map_transfer)
    print(result['status'])
    return 0 if result['status'] in (SUCCESS, SESSION_SUCCESS, TRANSFER_SUCCESS) else 1


if __name__ == '__main__':
    sys.exit(main())
