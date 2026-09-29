"""Reject incomplete, stale, foreign and mutated game proof without a runtime."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import game_evidence as evidence

ACCOUNT, NAME, IDENTIFIER = 'CohGuest01', 'TEST12345', 42
MAP = ' 1 City_01_01.txt S: 2/3 Ip:127.0.0.1:7001 Mem: 100M Cpu:0:00.00 = 0.0 0.0 Up: 0:01 Info '
CHARACTER = f'   {IDENTIFIER} Name {NAME} Auth {ACCOUNT} Ip 127.0.0.1 MapId 1 SmapId 1  \r\n'


def ready():
    return {'format': 1, 'child_pid': 55, 'transport_pid': 55, 'console_attached': True,
            'pipe_pid_verified': True, 'protocol_pid_verified': True, 'initial_snapshot': True,
            'version_requests': 1, 'buffer_rows_limit': 16384,
            'capture_byte_limit': 16777216, 'event_byte_limit': 8388608}


def event_records():
    pairs = [('BridgeStarted', ''), ('PID', '55'), ('AuthName', ACCOUNT), ('VersionRequest', 'NULL'),
             ('VersionReply', ''), ('Player', NAME), ('MapName', evidence.MAP_PATH), ('Status', 'Running')]
    return [{'sequence': i, 'kind': kind, 'value': value, 'raw': kind + ': ' + value, 'elapsed_ms': i * 10}
            for i, (kind, value) in enumerate(pairs, 1)]


def append(events, kind, value):
    events.append({'sequence': len(events) + 1, 'kind': kind, 'value': value.strip(),
                   'raw': kind + ':' + value, 'elapsed_ms': (len(events) + 1) * 10})


def resume_text():
    return (f'Found character {NAME} in slot 2\nResuming character in slot 2...done\ncommReqScene()...done\n'
            f'COH_RESUME_ONLY_SELECTED slot=2 name={NAME}\n'
            f'COH_RESUME_ONLY_SERVER_UPDATE id={IDENTIFIER} name={NAME}\n')


class GameListenerTests(unittest.TestCase):
    def output(self, ports):
        return evidence.GAME_LOOPBACK_ACK + '\n' + ''.join(
            f'{evidence.GAME_LOOPBACK_ENV} bind verified: protocol=udp address=127.0.0.1 port={port}\n'
            for port in ports)

    def test_actual_map_and_both_client_socket_binds_are_required(self):
        self.assertEqual(evidence.game_listener_bindings(self.output([7001]), 'atlas')['endpoints'],
                         [{'protocol': 'udp', 'address': '127.0.0.1', 'port': 7001}])
        # Reopening a closed UDP socket can legitimately reuse the ephemeral port.
        for ports in ([41001, 41002], [41001, 41001], [41001, 41002, 41003]):
            self.assertEqual([item['port'] for item in evidence.game_listener_bindings(
                self.output(ports), 'client')['endpoints']], ports)
        for role, ports in (('atlas', []), ('atlas', [7002]), ('atlas', [7001, 7001]), ('client', [41001])):
            with self.subTest(role=role, ports=ports), self.assertRaises(evidence.base.DiagnosticError):
                evidence.game_listener_bindings(self.output(ports), role)

    def test_partial_records_wait_but_complete_invalid_records_fail(self):
        good = self.output([41001, 41002])
        for text in ('', evidence.GAME_LOOPBACK_ACK, self.output([41001]), good[:-1]):
            self.assertFalse(evidence.game_listener_bindings(text, 'client', pending=True))
        for text in (good.replace('127.0.0.1', '0.0.0.0'), good.replace('udp', 'tcp'),
                     good.replace('port=41002', 'port=0'), good.replace('port=41002', 'port=65536'),
                     good + evidence.GAME_LOOPBACK_ACK + '\n', 'prefix ' + good,
                     good.replace('bind verified', 'bind failed'), self.output([1] * 129)):
            with self.subTest(text=text), self.assertRaises(evidence.base.DiagnosticError):
                evidence.game_listener_bindings(text, 'client', pending=True)

    def test_accepted_profile_cannot_silently_activate_policy(self):
        self.assertIsNone(evidence.game_listener_bindings('normal output\n', 'client', enabled=False))
        with self.assertRaises(evidence.base.DiagnosticError):
            evidence.game_listener_bindings(self.output([41001, 41002]), 'client', enabled=False)


def sql_evidence(login_count=1):
    rows = {table: [{column: 1 for column in fields}] for table, fields in evidence.SELECTED.items()}
    for table, records in rows.items():
        records[0]['containerid'] = IDENTIFIER
        if table != 'ents':
            records[0]['subid'] = 0
    rows['ents'][0].update(authid=77, authname=ACCOUNT, name=NAME, influencepoints=12345,
        logincount=login_count, description='', motto='', datecreated='2026-09-28T00:00:00')
    rows['ents2'][0].update(originalprimary='Energy_Blast', originalsecondary='Energy_Manipulation')
    inventory = [{field: rows['ents'][0][field] for field in evidence.IDENTITY_FIELDS + ('logincount',)}]
    attributes = {name: [{'id': 1, 'name': 'reviewed_attribute'}]
                  for name in ('attributes', 'badgestatsattributes', 'pophelpattributes')}
    return rows, inventory, attributes


class ProtocolEvidenceTests(unittest.TestCase):
    def rejects(self, function, *args, **kwargs):
        with self.assertRaises(evidence.base.DiagnosticError):
            function(*args, **kwargs)

    def test_map_status_requires_exact_map_identity_and_valid_endpoint(self):
        self.assertTrue(evidence.map_ready_current(evidence.parse_map_status(MAP)))
        self.assertFalse(evidence.parse_map_status(MAP + ' NotReady 1')['ready'])
        absent = evidence.parse_map_status('1 ' + evidence.MAP_PATH + ' NotReady 1 (Not started) Info ')
        self.assertTrue(absent['not_started'])
        for text in (MAP.replace(' 1 ', ' 2 ', 1), MAP.replace('City_01_01.txt', 'other/City_01_01.txt'),
                     MAP + '\n' + MAP, MAP.replace('127.0.0.1', '127.0.0.256'),
                     MAP.replace(':7001', ':70000'), MAP + ' NotReady 10', MAP + '\nSQLERROR: failed'):
            with self.subTest(text=text):
                self.rejects(evidence.parse_map_status, text)
        for text in (MAP.replace('2/3', '21/3'), MAP.replace('2/3', '2/21'),
                     MAP.replace('127.0.0.1', '192.0.2.1'), MAP.replace(':7001', ':7002')):
            self.assertFalse(evidence.map_ready_current(evidence.parse_map_status(text)))
        self.assertTrue(evidence.parse_map_status('invalid container request', True)['missing'])
        self.rejects(evidence.parse_map_status, 'invalid container request\n' + MAP, True)

    def test_character_status_uses_one_physical_line_and_exact_identity(self):
        self.assertTrue(evidence.connected_on_atlas(evidence.parse_character_status(
            CHARACTER + 'Disconnecting...\r\n', IDENTIFIER, NAME, ACCOUNT)))
        for text in (CHARACTER.rstrip() + ' NoConnect', CHARACTER.rstrip() + ' InMapXfer',
                     CHARACTER.replace('SmapId 1', 'SmapId 2'), CHARACTER.replace('MapId 1', 'MapId 2')):
            self.assertFalse(evidence.connected_on_atlas(evidence.parse_character_status(text, IDENTIFIER, NAME, ACCOUNT)))
        for text in (CHARACTER.replace(NAME, 'OTHER'), CHARACTER.replace(ACCOUNT, 'OTHER'),
                     CHARACTER.replace('42 Name', '43 Name'), CHARACTER * 2,
                     CHARACTER.rstrip() + ' UnknownFlag', CHARACTER.rstrip() + ' NoConnect NoConnect',
                     CHARACTER.replace('127.0.0.1', '999.0.0.1')):
            self.rejects(evidence.parse_character_status, text, IDENTIFIER, NAME, ACCOUNT)
        self.assertFalse(evidence.parse_character_status('invalid container request', IDENTIFIER, NAME, ACCOUNT, True)['loaded'])
        self.rejects(evidence.parse_character_status, 'invalid container request\n' + CHARACTER, IDENTIFIER, NAME, ACCOUNT, True)

    def test_find_needs_one_positive_clean_reply(self):
        self.assertEqual(evidence.parse_find('container_id = 42\n'), 42)
        for text in ('', 'container_id = 0', 'container_id = -1', 'container_id = 42\ncontainer_id = 42',
                     'container_id = 42\nCRASH'):
            self.rejects(evidence.parse_find, text)

    def test_pipe_binds_windows_transport_protocol_console_and_same_identity(self):
        self.assertEqual(evidence.pipe_identity(event_records(), ready(), ACCOUNT), NAME)
        self.assertFalse(evidence.pipe_identity([], None, ACCOUNT))
        for field, value in (('child_pid', 56), ('transport_pid', 56), ('pipe_pid_verified', False),
                             ('protocol_pid_verified', False), ('console_attached', False),
                             ('initial_snapshot', False), ('capture_byte_limit', 1), ('version_requests', 2)):
            self.rejects(evidence.pipe_identity, event_records(), dict(ready(), **{field: value}), ACCOUNT)
        for kind, value in (('PID', '56'), ('AuthName', 'OTHER'), ('Player', 'OTHER'),
                            ('MapName', 'other/City_01_01.txt'), ('Status', 'CRASH'), ('Status', 'ERROR')):
            records = event_records()
            append(records, kind, value)
            self.rejects(evidence.pipe_identity, records, ready(), ACCOUNT)
        self.rejects(evidence.pipe_identity, event_records(), ready(), ACCOUNT, 'OTHER')

    def test_bridge_event_reordering_and_raw_field_spoofing_cannot_pass(self):
        for field, value in (('sequence', 2), ('sequence', True), ('elapsed_ms', -1),
                             ('elapsed_ms', float('nan')), ('raw', 'AuthName: OTHER'), ('value', 'OTHER')):
            records = event_records()
            records[2][field] = value
            self.rejects(evidence.pipe_identity, records, ready(), ACCOUNT)
        records = event_records()
        records[1], records[2] = records[2], records[1]
        for sequence, record in enumerate(records, 1):
            record.update(sequence=sequence, elapsed_ms=sequence)
        self.rejects(evidence.pipe_identity, records, ready(), ACCOUNT)

    def test_logout_error_only_after_quit_for_requested_logout(self):
        records = event_records()
        append(records, 'QuitNow', '')
        append(records, 'Status', 'ERROR')
        self.assertEqual(evidence.pipe_identity(records, ready(), ACCOUNT, allow_logout_error=True), NAME)
        self.rejects(evidence.pipe_identity, records, ready(), ACCOUNT)
        early = event_records()
        append(early, 'Status', 'ERROR')
        append(early, 'QuitNow', '')
        self.rejects(evidence.pipe_identity, early, ready(), ACCOUNT, allow_logout_error=True)

    def test_live_currency_needs_recent_server_printf_for_same_player_and_account(self):
        body = f'conPrintf:0:\nPlayer: {NAME}\nLogin: {ACCOUNT}\nCurrent cash: 12345 (Influence)\n'
        records = event_records()
        append(records, 'ChatText', body)
        self.assertEqual(evidence.live_currency_evidence(records, NAME, ACCOUNT, 8)['influence'], 12345)
        self.assertFalse(evidence.live_currency_evidence(records, NAME, ACCOUNT, 9))
        for value in (body.replace('conPrintf:0:', 'Local:0:'), body.replace('Current cash: 12345', 'Current cash: 12344')):
            changed = event_records()
            append(changed, 'ChatText', value)
            self.assertFalse(evidence.live_currency_evidence(changed, NAME, ACCOUNT, 8))
        for value in (body.replace(NAME, 'OTHER'), body.replace(ACCOUNT, 'OTHER'),
                      body + 'Current cash: 12345 (Influence)\n', body.replace('Login:', 'User:')):
            changed = event_records()
            append(changed, 'ChatText', value)
            self.rejects(evidence.live_currency_evidence, changed, NAME, ACCOUNT, 8)

    def test_resume_requires_exact_once_processed_player_update_and_no_creation(self):
        proof = evidence.accept_sustained_resume(resume_text(), event_records(), ready(), ACCOUNT, NAME, IDENTIFIER)
        self.assertTrue(proof['processed_server_update_for_original_player'])
        self.assertFalse(proof['active_gameplay_confirmed'])
        for text in (resume_text().replace('id=42', 'id=43'), resume_text().replace('SERVER_UPDATE', 'PLAYER_UPDATE'),
                     resume_text().replace('Found character', 'Found something'),
                     resume_text().replace('SELECTED slot=2', 'SELECTED slot=3'),
                     resume_text() + 'COH_RESUME_ONLY_SERVER_UPDATE id=42 name=' + NAME + '\n',
                     resume_text() + 'simulateCharacterCreate()\n', resume_text() + 'COH_RESUME_ONLY_MISSING\n'):
            self.rejects(evidence.accept_sustained_resume, text, event_records(), ready(), ACCOUNT, NAME, IDENTIFIER)
        self.rejects(evidence.accept_sustained_resume, resume_text(), event_records(), ready(), ACCOUNT, NAME, IDENTIFIER, 0)
        for identifier in (None, True, 0, '42'):
            self.rejects(evidence.accept_sustained_resume, resume_text(), event_records(), ready(), ACCOUNT, NAME, identifier)


class SnapshotEvidenceTests(unittest.TestCase):
    def capture(self, inputs=None, login_count=1):
        return evidence.validate_snapshot(*(inputs or sql_evidence(login_count)), ACCOUNT, IDENTIFIER, NAME, login_count)

    def test_snapshot_is_independent_unchanged_and_exact_inventory(self):
        inputs = sql_evidence()
        before = copy.deepcopy(inputs)
        snapshot = self.capture(inputs)
        self.assertEqual(inputs, before)
        self.assertEqual(snapshot['identity']['containerid'], IDENTIFIER)
        self.assertNotIn('logincount', snapshot['rows']['ents'][0])
        self.assertEqual(snapshot['login_count'], 1)

    def test_missing_foreign_duplicate_or_reordered_child_rows_fail(self):
        mutations = [lambda r, i, a: r['powers'].clear(),
                     lambda r, i, a: r['powers'][0].update(containerid=43),
                     lambda r, i, a: r['powers'].append(dict(r['powers'][0])),
                     lambda r, i, a: r['powers'][0].update(subid=True),
                     lambda r, i, a: r['powers'][0].pop('uniqueid'),
                     lambda r, i, a: r['ents2'][0].update(subid=1),
                     lambda r, i, a: r['powers'].extend([dict(r['powers'][0], subid=2), dict(r['powers'][0], subid=1)])]
        for mutate in mutations:
            inputs = sql_evidence()
            mutate(*inputs)
            with self.assertRaises(evidence.base.DiagnosticError):
                self.capture(inputs)

    def test_changed_identity_extra_inventory_and_wrong_login_or_cash_fail(self):
        mutations = [lambda r, i, a: r['ents'][0].update(name='OTHER'),
                     lambda r, i, a: r['ents'][0].update(authname='OTHER'),
                     lambda r, i, a: r['ents'][0].update(authid=True),
                     lambda r, i, a: r['ents'][0].update(influencepoints=23456),
                     lambda r, i, a: r['ents'][0].update(logincount=2),
                     lambda r, i, a: i.append(dict(i[0], containerid=43)),
                     lambda r, i, a: i[0].update(logincount=True),
                     lambda r, i, a: i.clear()]
        for mutate in mutations:
            inputs = sql_evidence()
            mutate(*inputs)
            with self.assertRaises(evidence.base.DiagnosticError):
                self.capture(inputs)

    def test_attribute_reference_must_resolve_and_mapping_must_remain_identical(self):
        inputs = sql_evidence()
        inputs[0]['costumeparts'][0]['fxname'] = None
        self.capture(inputs)
        for table, column, value in (('ents', 'class', 0), ('powers', 'powername', 2),
                                     ('costumeparts', 'fxname', True)):
            inputs = sql_evidence()
            inputs[0][table][0][column] = value
            with self.assertRaises(evidence.base.DiagnosticError):
                self.capture(inputs)
        attributes = sql_evidence()[2]
        changed = copy.deepcopy(attributes)
        changed['attributes'][0]['name'] = 'different'
        with self.assertRaises(evidence.base.DiagnosticError):
            evidence.compare_attributes(attributes, changed)
        changed = copy.deepcopy(attributes)
        changed['attributes'].append(dict(changed['attributes'][0]))
        with self.assertRaises(evidence.base.DiagnosticError):
            evidence.validate_attributes(changed)

    def test_restart_then_second_logout_preserve_every_selected_field_and_cash(self):
        before, restarted, resumed = self.capture(), self.capture(), self.capture(login_count=2)
        self.assertTrue(evidence.compare_snapshots(before, restarted, 'restart')['selected_rows_unchanged'])
        self.assertEqual(evidence.compare_snapshots(before, resumed, 'second_logout')['login_count_after'], 2)
        for phase, changed in (('restart', resumed), ('second_logout', restarted)):
            with self.assertRaises(evidence.base.DiagnosticError):
                evidence.compare_snapshots(before, changed, phase)
        for table, field, value in (('ents', 'influencepoints', 23456), ('ents', 'level', True),
                                     ('ents2', 'curbuild', 2), ('powers', 'powername', 2),
                                     ('costumeparts', 'color1', 2)):
            changed = copy.deepcopy(resumed)
            changed['rows'][table][0][field] = value
            with self.assertRaises(evidence.base.DiagnosticError):
                evidence.compare_snapshots(before, changed, 'second_logout')


if __name__ == '__main__':
    unittest.main()
