#!/usr/bin/env python3
"""Build/test the separate nonshipping GROUPS and raw ALLENTS observer.

Scripted peers exercise real OS sockets, never actual-server interoperability.
The default Map/Local sources and accepted applications are unchanged.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import tempfile
import types

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NATIVE = ROOT / 'native-android'
RELATIVE = [
    'engine/initial-capture/coh_initial_local.c', 'engine/dbclient/coh_dbclient.c',
    'engine/dbclient/coh_db_session.c', 'engine/dbclient/coh_db_account_controls.c', 'engine/initial-capture/coh_initial_map.c',
    'engine/mapclient/coh_mapclient_owned.c', 'engine/replication/coh_replication.c',
    'engine/replication/coh_groups.c', 'engine/network/coh_net.c',
    'engine/network/coh_net_frame.c', 'engine/network/coh_net_zip.c',
    'engine/network/coh_net_udp.c', 'engine/auth/coh_auth.c',
    'engine/auth/coh_auth_openssl.c', 'engine/session/coh_session_crypto.c',
    'protocol/coh_protocol.c', 'src/coh_blowfish.c',
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, **kwargs):
    return subprocess.run(list(map(str, command)), capture_output=True, text=True,
                          timeout=120, **kwargs)


def require(command, **kwargs):
    result = run(command, **kwargs)
    if result.returncode:
        raise RuntimeError(f'{command[0]} failed\n{result.stdout}\n{result.stderr}')
    return result


def source_module(path):
    module = types.ModuleType(path.stem)
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    return module


def tool_tests(binary, peer, work, environment, evidence):
    account = work / 'account'
    account.write_text('Fixture\n')
    account.chmod(0o600)
    checks = 0
    evidence.mkdir(mode=0o700)
    stdout_files = {}
    for mode in ('captured', 'unknown', 'badheader', 'none'):
        report = work / (mode + '-peer.json')
        child = subprocess.Popen([str(peer), '--serve', '--report', str(report), '--mode', mode],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=environment)
        try:
            with selectors.DefaultSelector() as ready:
                ready.register(child.stdout, selectors.EVENT_READ)
                if not ready.select(10):
                    raise TimeoutError('scripted initial peer did not become ready')
                port = json.loads(child.stdout.readline())['db_port']
            target = work / mode
            completed = subprocess.run(list(map(str, [binary, port, 0, account, target, 1000, 5, 0, 0])),
                capture_output=True, timeout=120, env=environment)
            if completed.returncode:
                raise RuntimeError('scripted initial receiver refused')
            public = json.loads(completed.stdout)
            groups = json.loads((target / 'capture.json').read_bytes())
            initial = json.loads((target / 'initial-observation.json').read_bytes())
            assert set(public) == {'schema', 'passed', 'initial_packet_observed', 'status',
                'opened_sockets', 'closed_sockets', 'source_generation_admitted', 'complete_initial_character',
                'actor_publication', 'ack_permitted', 'world_authority', 'diagnostic_failure_code',
                'groups_observed', 'reqallents_sent', 'local_phase', 'terminal_failure',
                'terminal_db_phase', 'terminal_map_phase', 'refused_command_valid', 'refused_command_kind'}
            assert public['schema'] == 'coh-local-initial-capture-status-v2'
            assert public['groups_observed'] is True and public['reqallents_sent'] == 1
            assert type(public['terminal_failure']) is bool
            for name, maximum in (('status', 7), ('local_phase', 10), ('terminal_db_phase', 12), ('terminal_map_phase', 10)):
                assert type(public[name]) is int and 0 <= public[name] <= maximum
            assert public['diagnostic_failure_code'] == {'captured': 'NONE', 'unknown': 'COMMAND',
                'badheader': 'HEADER', 'none': 'TIMEOUT'}[mode]
            assert public['terminal_failure'] is (mode != 'captured')
            assert public['terminal_db_phase'] == (0 if mode == 'captured' else 9)
            assert public['terminal_map_phase'] == (0 if mode == 'captured' else 5)
            assert type(public['refused_command_valid']) is bool and type(public['refused_command_kind']) is str
            assert public['refused_command_valid'] is (mode in ('unknown', 'badheader'))
            assert public['refused_command_kind'] == {'captured': 'NONE', 'unknown': 'SERVER_GAME_CMDS',
                'badheader': 'SERVER_ALLENTS', 'none': 'NONE'}[mode]
            stdout_path = evidence / (mode + '.json')
            stdout_path.write_bytes(completed.stdout)
            stdout_path.chmod(0o600)
            stdout_files[mode] = {'file': str(Path(evidence.name) / stdout_path.name),
                'bytes': stdout_path.stat().st_size, 'sha256': digest(stdout_path)}
            checks += 15
            assert public['passed'] and groups['passed'] and groups['cleanup_verified']
            assert groups['packet_sha256'] == digest(target / 'groups.bin')
            assert initial['groups_packet_sha256'] == groups['packet_sha256']
            assert initial['selected_dbid'] == groups['selected_dbid'] == 17
            assert initial['opened_sockets'] == initial['closed_sockets'] == 2
            assert initial['reqallents_sent'] == 1
            assert not any(initial[k] for k in ('source_generation_admitted', 'complete_initial_character',
                'actor_publication', 'ack_permitted', 'world_authority', 'sends_ready',
                'sends_received_character', 'sends_full_update_ack'))
            if mode == 'captured':
                assert initial['passed'] and public['initial_packet_observed']
                assert initial['raw_allents_loan_verified'] and initial['failure_code'] == 'NONE'
                assert initial['packet_sha256'] == digest(target / 'initial-update.bin')
                assert initial['message_generation'] > initial['groups_message_generation']
                assert initial['payload_bits'] <= initial['bytes'] * 8
                assert initial['update_prefix']['command'] == 3
            else:
                assert not initial['passed'] and not public['initial_packet_observed']
                assert not (target / 'initial-update.bin').exists()
                assert initial['bytes'] == initial['payload_bits'] == 0 and initial['packet_sha256'] == ''
                assert initial['failure_code'] == {'unknown': 'COMMAND', 'badheader': 'HEADER', 'none': 'TIMEOUT'}[mode]
            assert (target.stat().st_mode & 0o777) == 0o700
            assert all((p.stat().st_mode & 0o777) == 0o600 for p in target.iterdir())
            checks += 19
        finally:
            if child.poll() is None:
                child.send_signal(signal.SIGTERM)
            stdout, stderr = child.communicate(timeout=10)
            if child.returncode:
                raise RuntimeError('scripted initial peer failed\n' + stdout + stderr)
        peer_report = json.loads(report.read_bytes())
        assert not peer_report['failed'] and peer_report['reqallents_unique'] == 1
        assert not any(peer_report[k] for k in ('forbidden_application_commands', 'ready_commands',
            'received_character_commands', 'full_update_ack_commands'))
        checks += 3
    for args in ([], ['0'] * 8, ['7000', '64', account, work / 'invalid', '100', '5', '0', '0']):
        assert run([binary, *args], env=environment).returncode == 2
        checks += 1
    return {'passed': True, 'checks': checks, 'fixed_status_stdout': stdout_files, 'actual_os_sockets': True,
            'scripted_peers_only': True, 'groups_survives_initial_refusal': True,
            'real_server_capture': False, 'complete_initial_character': False,
            'actor_publication': False, 'ack_permitted': False, 'world_authority': False}


def editmsg_tool_tests(binary, peer, work, environment, evidence):
    """Only the newly supported control-message path, with real local sockets."""
    account = work / 'account'
    account.write_text('Fixture\n')
    account.chmod(0o600)
    evidence.mkdir(mode=0o700)
    checks, stdout_files = 0, {}
    def need(ok):
        nonlocal checks
        assert ok
        checks += 1
    cases = {
        'editmsg-captured': ('NONE', 2, False, 'NONE'),
        'editmsg-unknown': ('COMMAND', 2, True, 'SERVER_GAME_CMDS'),
        'editmsg-malformed': ('PROTOCOL', 1, True, 'SERVER_EDITMSG'),
        'editmsg-limit': ('PROTOCOL', 4, True, 'SERVER_EDITMSG'),
        'editmsg-none': ('TIMEOUT', 7, False, 'NONE'),
    }
    keys = {'schema', 'passed', 'initial_packet_observed', 'status',
        'opened_sockets', 'closed_sockets', 'source_generation_admitted', 'complete_initial_character',
        'actor_publication', 'ack_permitted', 'world_authority', 'diagnostic_failure_code',
        'groups_observed', 'reqallents_sent', 'local_phase', 'terminal_failure',
        'terminal_db_phase', 'terminal_map_phase', 'refused_command_valid', 'refused_command_kind'}
    for mode, (failure, status, refused, kind) in cases.items():
        report = work / (mode + '-peer.json')
        child = subprocess.Popen([str(peer), '--serve', '--report', str(report), '--mode', mode],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=environment)
        try:
            with selectors.DefaultSelector() as ready:
                ready.register(child.stdout, selectors.EVENT_READ)
                if not ready.select(10):
                    raise TimeoutError('new EDITMSG peer did not become ready')
                port = json.loads(child.stdout.readline())['db_port']
            target = work / mode
            completed = subprocess.run(list(map(str, [binary, port, 0, account, target, 1000, 5, 0, 0])),
                capture_output=True, timeout=120, env=environment)
            need(completed.returncode == 0 and completed.stderr == b'')
            public = json.loads(completed.stdout)
            groups = json.loads((target / 'capture.json').read_bytes())
            initial = json.loads((target / 'initial-observation.json').read_bytes())
            captured = mode == 'editmsg-captured'
            need(set(public) == keys and public['schema'] == 'coh-local-initial-capture-status-v2')
            need(public['passed'] is True and public['groups_observed'] is True)
            need(public['reqallents_sent'] == 1 and type(public['reqallents_sent']) is int)
            need(public['initial_packet_observed'] is captured and public['terminal_failure'] is (not captured))
            need(public['diagnostic_failure_code'] == failure and type(public['status']) is int and public['status'] == status)
            need(public['refused_command_valid'] is refused and public['refused_command_kind'] == kind)
            need(public['terminal_db_phase'] == (0 if captured else 9))
            need(public['terminal_map_phase'] == (0 if captured else 5))
            need(public['opened_sockets'] == public['closed_sockets'] == 2)
            need(all(public[k] is False for k in ('source_generation_admitted', 'complete_initial_character',
                'actor_publication', 'ack_permitted', 'world_authority')))
            need(groups['passed'] is True and groups['cleanup_verified'] is True)
            need(groups['packet_sha256'] == digest(target / 'groups.bin'))
            need(initial['groups_packet_sha256'] == groups['packet_sha256'])
            need(initial['selected_dbid'] == groups['selected_dbid'] == 17)
            need(initial['opened_sockets'] == initial['closed_sockets'] == 2 and initial['reqallents_sent'] == 1)
            need(initial['passed'] is captured and initial['failure_code'] == failure)
            need(all(initial[k] is False for k in ('source_generation_admitted', 'complete_initial_character',
                'actor_publication', 'ack_permitted', 'world_authority', 'sends_ready',
                'sends_received_character', 'sends_full_update_ack')))
            if captured:
                need(initial['raw_allents_loan_verified'] is True)
                need(initial['packet_sha256'] == digest(target / 'initial-update.bin'))
                need(initial['message_generation'] > initial['groups_message_generation'])
                need(initial['payload_bits'] <= initial['bytes'] * 8 and initial['update_prefix']['command'] == 3)
            else:
                need(not (target / 'initial-update.bin').exists())
                need(initial['bytes'] == initial['payload_bits'] == 0 and initial['packet_sha256'] == '')
            need((target.stat().st_mode & 0o777) == 0o700)
            need(all((p.stat().st_mode & 0o777) == 0o600 for p in target.iterdir()))
            stdout_path = evidence / (mode + '.json')
            stdout_path.write_bytes(completed.stdout)
            stdout_path.chmod(0o600)
            stdout_files[mode] = {'file': str(Path(evidence.name) / stdout_path.name),
                'bytes': stdout_path.stat().st_size, 'sha256': digest(stdout_path)}
        finally:
            if child.poll() is None:
                child.send_signal(signal.SIGTERM)
            stdout, stderr = child.communicate(timeout=10)
            if child.returncode:
                raise RuntimeError('new EDITMSG peer refused cleanup\n' + stdout + stderr)
        peer_report = json.loads(report.read_bytes())
        need(peer_report['failed'] is False and peer_report['reqallents_unique'] == 1)
        need(all(peer_report[k] == 0 for k in ('forbidden_application_commands', 'ready_commands',
            'received_character_commands', 'full_update_ack_commands')))
    noargs = run([binary], env=environment)
    need(noargs.returncode == 2 and noargs.stdout == '' and noargs.stderr == '')
    return {'passed': True, 'checks': checks, 'cases': list(cases), 'fixed_status_stdout': stdout_files,
        'actual_os_sockets': True, 'scripted_peers_only': True, 'groups_survives_initial_refusal': True,
        'handled_status_is_not_initial_capture': True, 'new_editmsg_controls_only': True,
        'old151_controls_reexecuted': False, 'real_server_capture': False,
        'complete_initial_character': False, 'actor_publication': False, 'ack_permitted': False,
        'world_authority': False}


def account_controls_tool_tests(binary, peer, work, environment, evidence):
    """Only complete DB controls followed by initial capture, with real local sockets."""
    account = work / 'account'
    account.write_text('Fixture\n')
    account.chmod(0o600)
    evidence.mkdir(mode=0o700)
    checks, stdout_files = 0, {}
    def need(ok):
        nonlocal checks
        assert ok
        checks += 1
    cases = {'account-controls-captured': ('NONE', 2, False, 'NONE')}
    keys = {'schema', 'passed', 'initial_packet_observed', 'status',
        'opened_sockets', 'closed_sockets', 'source_generation_admitted', 'complete_initial_character',
        'actor_publication', 'ack_permitted', 'world_authority', 'diagnostic_failure_code',
        'groups_observed', 'reqallents_sent', 'local_phase', 'terminal_failure',
        'terminal_db_phase', 'terminal_map_phase', 'refused_command_valid', 'refused_command_kind'}
    for mode, (failure, status, refused, kind) in cases.items():
        report = work / (mode + '-peer.json')
        child = subprocess.Popen([str(peer), '--serve', '--report', str(report), '--mode', 'captured'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=environment)
        try:
            with selectors.DefaultSelector() as ready:
                ready.register(child.stdout, selectors.EVENT_READ)
                if not ready.select(10):
                    raise TimeoutError('new DB account-control peer did not become ready')
                port = json.loads(child.stdout.readline())['db_port']
            target = work / mode
            completed = subprocess.run(list(map(str, [binary, port, 0, account, target, 1000, 5, 0, 0])),
                capture_output=True, timeout=120, env=environment)
            need(completed.returncode == 0 and completed.stderr == b'')
            public = json.loads(completed.stdout)
            groups = json.loads((target / 'capture.json').read_bytes())
            initial = json.loads((target / 'initial-observation.json').read_bytes())
            captured = mode == 'account-controls-captured'
            need(set(public) == keys and public['schema'] == 'coh-local-initial-capture-status-v2')
            need(public['passed'] is True and public['groups_observed'] is True)
            need(public['reqallents_sent'] == 1 and type(public['reqallents_sent']) is int)
            need(public['initial_packet_observed'] is captured and public['terminal_failure'] is (not captured))
            need(public['diagnostic_failure_code'] == failure and type(public['status']) is int and public['status'] == status)
            need(public['refused_command_valid'] is refused and public['refused_command_kind'] == kind)
            need(public['terminal_db_phase'] == (0 if captured else 9))
            need(public['terminal_map_phase'] == (0 if captured else 5))
            need(public['opened_sockets'] == public['closed_sockets'] == 2)
            need(all(public[k] is False for k in ('source_generation_admitted', 'complete_initial_character',
                'actor_publication', 'ack_permitted', 'world_authority')))
            need(groups['passed'] is True and groups['cleanup_verified'] is True)
            need(groups['packet_sha256'] == digest(target / 'groups.bin'))
            need(initial['groups_packet_sha256'] == groups['packet_sha256'])
            need(initial['selected_dbid'] == groups['selected_dbid'] == 17)
            need(initial['opened_sockets'] == initial['closed_sockets'] == 2 and initial['reqallents_sent'] == 1)
            need(initial['passed'] is captured and initial['failure_code'] == failure)
            need(all(initial[k] is False for k in ('source_generation_admitted', 'complete_initial_character',
                'actor_publication', 'ack_permitted', 'world_authority', 'sends_ready',
                'sends_received_character', 'sends_full_update_ack')))
            if captured:
                need(initial['raw_allents_loan_verified'] is True)
                need(initial['packet_sha256'] == digest(target / 'initial-update.bin'))
                need(initial['message_generation'] > initial['groups_message_generation'])
                need(initial['payload_bits'] <= initial['bytes'] * 8 and initial['update_prefix']['command'] == 3)
            else:
                need(not (target / 'initial-update.bin').exists())
                need(initial['bytes'] == initial['payload_bits'] == 0 and initial['packet_sha256'] == '')
            need((target.stat().st_mode & 0o777) == 0o700)
            need(all((p.stat().st_mode & 0o777) == 0o600 for p in target.iterdir()))
            stdout_path = evidence / (mode + '.json')
            stdout_path.write_bytes(completed.stdout)
            stdout_path.chmod(0o600)
            stdout_files[mode] = {'file': str(Path(evidence.name) / stdout_path.name),
                'bytes': stdout_path.stat().st_size, 'sha256': digest(stdout_path)}
        finally:
            if child.poll() is None:
                child.send_signal(signal.SIGTERM)
            stdout, stderr = child.communicate(timeout=10)
            if child.returncode:
                raise RuntimeError('new DB account-control peer refused cleanup\n' + stdout + stderr)
        peer_report = json.loads(report.read_bytes())
        need(peer_report['failed'] is False and peer_report['reqallents_unique'] == 1)
        need(peer_report['account_controls_sent'] == 3 and peer_report['character_lists'] == 1)
        need(all(peer_report[k] == 0 for k in ('forbidden_application_commands', 'ready_commands',
            'received_character_commands', 'full_update_ack_commands')))
    noargs = run([binary], env=environment)
    need(noargs.returncode == 2 and noargs.stdout == '' and noargs.stderr == '')
    return {'passed': True, 'checks': checks, 'cases': list(cases), 'fixed_status_stdout': stdout_files,
        'actual_os_sockets': True, 'scripted_peers_only': True, 'initial_refusal_case_exercised': False,
        'account_controls_are_not_character_lists': True, 'new_account_controls_only': True,
        'old151_controls_reexecuted': False, 'old123_controls_reexecuted': False, 'real_server_capture': False,
        'complete_initial_character': False, 'actor_publication': False, 'ack_permitted': False,
        'world_authority': False}


def account_inventory_tool_tests(binary, peer, work, environment, evidence):
    """Only complete DB controls and inventory followed by initial capture, with real local sockets."""
    account = work / 'account'
    account.write_text('Fixture\n')
    account.chmod(0o600)
    evidence.mkdir(mode=0o700)
    checks, stdout_files = 0, {}
    def need(ok):
        nonlocal checks
        assert ok
        checks += 1
    cases = {'account-inventory-captured': ('NONE', 2, False, 'NONE')}
    keys = {'schema', 'passed', 'initial_packet_observed', 'status',
        'opened_sockets', 'closed_sockets', 'source_generation_admitted', 'complete_initial_character',
        'actor_publication', 'ack_permitted', 'world_authority', 'diagnostic_failure_code',
        'groups_observed', 'reqallents_sent', 'local_phase', 'terminal_failure',
        'terminal_db_phase', 'terminal_map_phase', 'refused_command_valid', 'refused_command_kind'}
    for mode, (failure, status, refused, kind) in cases.items():
        report = work / (mode + '-peer.json')
        child = subprocess.Popen([str(peer), '--serve', '--report', str(report), '--mode', 'captured'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=environment)
        try:
            with selectors.DefaultSelector() as ready:
                ready.register(child.stdout, selectors.EVENT_READ)
                if not ready.select(10):
                    raise TimeoutError('new DB inventory peer did not become ready')
                port = json.loads(child.stdout.readline())['db_port']
            target = work / mode
            completed = subprocess.run(list(map(str, [binary, port, 0, account, target, 1000, 5, 0, 0])),
                capture_output=True, timeout=120, env=environment)
            need(completed.returncode == 0 and completed.stderr == b'')
            public = json.loads(completed.stdout)
            groups = json.loads((target / 'capture.json').read_bytes())
            initial = json.loads((target / 'initial-observation.json').read_bytes())
            captured = mode == 'account-inventory-captured'
            need(set(public) == keys and public['schema'] == 'coh-local-initial-capture-status-v2')
            need(public['passed'] is True and public['groups_observed'] is True)
            need(public['reqallents_sent'] == 1 and type(public['reqallents_sent']) is int)
            need(public['initial_packet_observed'] is captured and public['terminal_failure'] is (not captured))
            need(public['diagnostic_failure_code'] == failure and type(public['status']) is int and public['status'] == status)
            need(public['refused_command_valid'] is refused and public['refused_command_kind'] == kind)
            need(public['terminal_db_phase'] == (0 if captured else 9))
            need(public['terminal_map_phase'] == (0 if captured else 5))
            need(public['opened_sockets'] == public['closed_sockets'] == 2)
            need(all(public[k] is False for k in ('source_generation_admitted', 'complete_initial_character',
                'actor_publication', 'ack_permitted', 'world_authority')))
            need(groups['passed'] is True and groups['cleanup_verified'] is True)
            need(groups['packet_sha256'] == digest(target / 'groups.bin'))
            need(initial['groups_packet_sha256'] == groups['packet_sha256'])
            need(initial['selected_dbid'] == groups['selected_dbid'] == 17)
            need(initial['opened_sockets'] == initial['closed_sockets'] == 2 and initial['reqallents_sent'] == 1)
            need(initial['passed'] is captured and initial['failure_code'] == failure)
            need(all(initial[k] is False for k in ('source_generation_admitted', 'complete_initial_character',
                'actor_publication', 'ack_permitted', 'world_authority', 'sends_ready',
                'sends_received_character', 'sends_full_update_ack')))
            if captured:
                need(initial['raw_allents_loan_verified'] is True)
                need(initial['packet_sha256'] == digest(target / 'initial-update.bin'))
                need(initial['message_generation'] > initial['groups_message_generation'])
                need(initial['payload_bits'] <= initial['bytes'] * 8 and initial['update_prefix']['command'] == 3)
            else:
                need(not (target / 'initial-update.bin').exists())
                need(initial['bytes'] == initial['payload_bits'] == 0 and initial['packet_sha256'] == '')
            need((target.stat().st_mode & 0o777) == 0o700)
            need(all((p.stat().st_mode & 0o777) == 0o600 for p in target.iterdir()))
            stdout_path = evidence / (mode + '.json')
            stdout_path.write_bytes(completed.stdout)
            stdout_path.chmod(0o600)
            stdout_files[mode] = {'file': str(Path(evidence.name) / stdout_path.name),
                'bytes': stdout_path.stat().st_size, 'sha256': digest(stdout_path)}
        finally:
            if child.poll() is None:
                child.send_signal(signal.SIGTERM)
            stdout, stderr = child.communicate(timeout=10)
            if child.returncode:
                raise RuntimeError('new DB inventory peer refused cleanup\n' + stdout + stderr)
        peer_report = json.loads(report.read_bytes())
        need(peer_report['failed'] is False and peer_report['reqallents_unique'] == 1)
        need(peer_report['account_controls_sent'] == 3 and peer_report['character_lists'] == 1)
        need(peer_report['account_inventory_sent'] == 1 and type(peer_report['account_inventory_sent']) is int)
        need(all(peer_report[k] == 0 for k in ('forbidden_application_commands', 'ready_commands',
            'received_character_commands', 'full_update_ack_commands')))
    noargs = run([binary], env=environment)
    need(noargs.returncode == 2 and noargs.stdout == '' and noargs.stderr == '')
    return {'passed': True, 'checks': checks, 'cases': list(cases), 'fixed_status_stdout': stdout_files,
        'actual_os_sockets': True, 'scripted_peers_only': True, 'initial_refusal_case_exercised': False,
        'account_controls_are_not_character_lists': True, 'inventory_is_not_character_list_or_character_state': True,
        'new_account_inventory_only': True, 'new_account_controls_only': False,
        'old28_controls_reexecuted': False,
        'old151_controls_reexecuted': False, 'old123_controls_reexecuted': False, 'real_server_capture': False,
        'complete_initial_character': False, 'actor_publication': False, 'ack_permitted': False,
        'world_authority': False}



def main():
    if not __debug__ or os.environ.get('PYTHONOPTIMIZE'):
        raise SystemExit('qualification requires Python assertions enabled')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    controls = parser.add_mutually_exclusive_group(required=True)
    controls.add_argument('--test', action='store_true')
    controls.add_argument('--editmsg-only', action='store_true')
    controls.add_argument('--account-controls-only', action='store_true')
    controls.add_argument('--account-inventory-only', action='store_true')
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('fresh output required')
    args.output.mkdir(parents=True)
    sys.dont_write_bytecode = True
    sources = [NATIVE / p for p in RELATIVE]
    observer = HERE / 'capture_local_initial.c'
    selected_peer = NATIVE / 'engine/initial-capture' / ('test_initial_inventory_peer.c' if args.account_inventory_only else 'test_initial_account_peer.c' if args.account_controls_only else 'test_initial_editmsg_peer.c' if args.editmsg_only else 'test_initial_peer.c')
    inputs = {observer, Path(__file__), selected_peer, *sources}
    # Bind the compiler's consumed project closure, including headers and
    # implementation includes that are newly introduced in a local checkout.
    for source in [*sources, observer]:
        dependencies = require(['cc', '-MM', '-I' + str(NATIVE / 'include'), source]).stdout
        for name in dependencies.replace('\\\n', ' ').partition(':')[2].split():
            dependency = Path(name).resolve()
            dependency.relative_to(ROOT)
            inputs.add(dependency)
    tracked = require(['git', '-C', ROOT, 'ls-files', '-z', 'native-android']).stdout.split('\0')
    inputs.update(ROOT / path for path in tracked if path and Path(path).suffix in ('.py', '.h', '.c', '.inc', '.json')
                  and not any(part in ('evidence', 'qualification', 'diagnostics') for part in Path(path).parts))
    for relative in ('local/source-pins.json', 'dbclient/source-pins.json', 'mapclient/source-pins.json',
                     'replication/source-pins.json', 'replication/groups-source-pins.json',
                     'initial-capture/command-source-pins.json', 'initial-capture/editmsg-source-pins.json'):
        manifest = NATIVE / 'engine' / relative
        inputs.add(manifest)
        inputs.update(ROOT / path if path.startswith(('upstream/', 'android/')) else ROOT / 'upstream/ouroboros' / path
                      for path in json.loads(manifest.read_bytes())['sha256_lf'])
    if args.account_controls_only or args.account_inventory_only:
        account_manifest = NATIVE / 'engine/dbclient/tests/account-controls-source-pins.json'
        inputs.add(account_manifest)
        account_source_pins = json.loads(account_manifest.read_bytes())['sha256_lf']
        if args.account_inventory_only and len(account_source_pins) != 10:
            raise RuntimeError('inventory composition requires the complete ten-source account fixture manifest')
        inputs.update(ROOT / 'upstream/ouroboros' / path for path in account_source_pins)
    if args.account_inventory_only:
        inventory_manifest = NATIVE / 'engine/dbclient/tests/inventory-source-pins.json'
        inputs.add(inventory_manifest)
        inventory_source_pins = json.loads(inventory_manifest.read_bytes())['sha256_lf']
        if len(inventory_source_pins) != 17:
            raise RuntimeError('inventory composition requires the complete seventeen-source inventory manifest')
        inputs.update(ROOT / 'upstream/ouroboros' / path for path in inventory_source_pins)
    inputs = sorted(inputs)
    pins = {str(p.relative_to(ROOT)): digest(p) for p in inputs}
    revision = require(['git', '-C', ROOT, 'rev-parse', 'HEAD']).stdout.strip()
    committed = {}
    for entry in require(['git', '-C', ROOT, 'ls-tree', '-r', '-z', 'HEAD']).stdout.split('\0'):
        if entry:
            metadata, path = entry.split('\t', 1)
            committed[path] = metadata.split()[2]
    for path in inputs:
        data = path.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if path.is_symlink() or committed.get(str(path.relative_to(ROOT))) != blob:
            raise RuntimeError('qualification input differs from committed HEAD: ' + str(path.relative_to(ROOT)))
    dirty = require(['git', '-C', ROOT, 'status', '--porcelain', '--untracked-files=normal']).stdout
    modes = [('release', ['-O2'])]
    if args.sanitize:
        modes += [('address', ['-O1', '-g', '-fsanitize=address', '-no-pie']),
                  ('undefined', ['-O1', '-g', '-fsanitize=undefined', '-fno-sanitize-recover=all'])]
    results = {}
    with tempfile.TemporaryDirectory(prefix='coh-initial-tool-') as temporary:
        work = Path(temporary)
        db = source_module(NATIVE / 'engine/dbclient/check.py')
        oracle, _ = db.oracle(ROOT, work)
        db.fixtures(oracle, work)
        maps = source_module(NATIVE / 'engine/mapclient/check.py')
        maps.command_fixtures(ROOT, work)
        maps.groups_fixtures(ROOT, work)
        account_controls_proof = None
        if args.account_controls_only or args.account_inventory_only:
            account_controls = source_module(NATIVE / 'engine/dbclient/tests/account_controls_oracle.py')
            account_controls_proof = account_controls.produce(ROOT, work)
        account_inventory_proof = None
        if args.account_inventory_only:
            account_inventory = source_module(NATIVE / 'engine/dbclient/tests/inventory_oracle.py')
            account_inventory_proof = account_inventory.produce(ROOT, work)
            if (len(account_controls_proof['whole_source_sha256_lf']) != 10 or
                    len(account_inventory_proof['whole_source_sha256_lf']) != 17):
                raise RuntimeError('incomplete original source fixture closure')
        editmsg_proof = None
        if args.editmsg_only:
            editmsg = source_module(NATIVE / 'engine/initial-capture/editmsg_fixtures.py')
            editmsg_proof = editmsg.produce_fixtures(ROOT, work)
        # The unchanged UI peer undefines its DB-test main rename before this
        # generated header. Rename only its qualification entry point here.
        with (work / 'server-command-fixtures.h').open('a') as fixture:
            fixture.write('\n#ifdef COH_INITIAL_PEER_RENAME_MAIN\n#define main accepted_ui_peer_main\n#endif\n')
        environment = dict(os.environ, ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',
                           UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        for label, options in modes:
            flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-fstack-usage', *options,
                     '-I' + str(NATIVE / 'include'), '-I' + str(work)]
            objects = []
            for index, source in enumerate(sources):
                target = work / f'{label}-{index}.o'
                original = ['-O0'] if source.name in ('coh_protocol.c', 'coh_blowfish.c') else []
                require(['cc', *flags, *original, '-c', source, '-o', target])
                objects.append(target)
            binary = args.output.resolve() / ('coh-capture-local-initial' + ('' if label == 'release' else '-' + label))
            require(['cc', *flags, observer, *objects, '-lz', '-lm', '-lcrypto', '-o', binary])
            peer = work / ('peer-' + label)
            peer_source = ('test_initial_inventory_peer.c' if args.account_inventory_only else
                           'test_initial_account_peer.c' if args.account_controls_only else
                           'test_initial_editmsg_peer.c' if args.editmsg_only else 'test_initial_peer.c')
            require(['cc', *flags, NATIVE / 'engine/initial-capture' / peer_source, *objects,
                     '-lz', '-lm', '-lcrypto', '-o', peer])
            mode_work = work / label
            mode_work.mkdir()
            if args.account_inventory_only:
                before_tests = {'receiver': digest(binary), 'peer': digest(peer)}
                tests = account_inventory_tool_tests(binary, peer, mode_work, environment,
                    args.output.resolve() / ('status-' + label))
                if tests['checks'] != 29:
                    raise RuntimeError('inventory-only qualification must run exactly twenty-nine new checks')
                after_tests = {'receiver': digest(binary), 'peer': digest(peer)}
                if before_tests != after_tests:
                    raise RuntimeError('inventory-only executable bytes changed during tests')
                results[label] = {'binary': binary.name, 'sha256': before_tests['receiver'], 'built': True,
                    'tests': tests, 'peer_sha256': before_tests['peer'],
                    'receiver_and_peer_bytes_unchanged_during_tests': True}
            else:
                results[label] = {'binary': binary.name, 'sha256': digest(binary), 'built': True,
                                  'tests': (account_controls_tool_tests if args.account_controls_only else
                                            editmsg_tool_tests if args.editmsg_only else tool_tests)(binary, peer, mode_work, environment,
                                      args.output.resolve() / ('status-' + label))}
    assert pins == {str(p.relative_to(ROOT)): digest(p) for p in inputs}
    assert require(['git', '-C', ROOT, 'rev-parse', 'HEAD']).stdout.strip() == revision
    proof = {'schema': 'coh-local-initial-capture-build-v1', 'passed': True,
        'source_revision': revision, 'source_dirty_at_start': bool(dirty),
        'consumed_source_equals_committed_head': True,
        'source_checkout_state_at_start': dirty, 'source_hashes_authoritative_for_build_bytes': True,
        'source_sha256': pins, 'modes': results, 'nonshipping_initial_observation': True,
        'new_editmsg_controls_only': args.editmsg_only,
        'new_account_controls_only': args.account_controls_only,
        'new_account_inventory_only': args.account_inventory_only,
        'old28_controls_reexecuted': False if args.account_inventory_only else args.account_controls_only,
        'old151_controls_reexecuted': not (args.editmsg_only or args.account_controls_only or args.account_inventory_only),
        'old123_controls_reexecuted': args.editmsg_only,
        'original_editmsg_fixtures': editmsg_proof, 'original_account_control_fixtures': account_controls_proof,
        'original_account_inventory_fixtures': account_inventory_proof,
        'groups_capture_scope': True, 'application_character_acceptance': False,
        'sends_reqallents': True, 'sends_ready': False, 'sends_received_character': False,
        'sends_full_update_ack': False, 'android_built': False, 'android_executed': False,
        'real_server_capture': False, 'source_generation_admitted': False,
        'actor_identity_verified': False, 'world_authority': False}
    if args.account_inventory_only:
        for result in results.values():
            if digest(args.output.resolve() / result['binary']) != result['sha256']:
                raise RuntimeError('inventory-only receiver bytes changed before final publication')
    (args.output / 'build.json').write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps({'passed': True, 'modes': results, 'world_authority': False}))


if __name__ == '__main__':
    main()
