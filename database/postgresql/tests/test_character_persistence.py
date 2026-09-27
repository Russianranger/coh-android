"""Acceptance tests for stock character protocol evidence, not game execution."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run_character_persistence as driver


ACCOUNT = 'CohP12345'
NAME = 'TEST12345'
STATUS = '    9 Name TEST12345        Auth CohP12345        Ip 127.0.0.1        MapId 1 SmapId 1  \n'


def pipe_state():
    events = []
    for kind, value in (('PID', '55'), ('AuthName', ACCOUNT), ('VersionRequest', 'NULL'),
                        ('Player', NAME), ('MapName', driver.one_map.MAP_PATH), ('Status', 'Running')):
        events.append({'kind': kind, 'value': value, 'raw': kind + ': ' + value,
                       'sequence': len(events), 'time_utc': '2026-09-26T00:00:00+00:00'})
    return {'events': events, 'client_pid': 55, 'pid_verified': True, 'version_requests': 1,
            'player': NAME, 'map_name': driver.one_map.MAP_PATH, 'status': 'Running', 'error': None}


def resume_text():
    return f'Found character {NAME} in slot 2\nResuming character in slot 2...done\ncommReqScene()...done\n'


class CharacterProtocolTests(unittest.TestCase):
    def test_current_immutable_sources_match_protocol_assumptions(self):
        self.assertEqual(driver.source_contract()['list_id'], 3)

    def test_no_create_resume_is_order_sensitive_and_create_does_not_disconnect(self):
        root = Path('runtime')
        first = driver.client_command(root, ACCOUNT)
        self.assertNotIn('-disconnect', first)
        self.assertNotIn('-cov', first)
        self.assertNotIn('-character', first)
        for flag in ('-fakeauth', '-nolevel', '-TEAMACCEPT', '-FOLLOW', '-SUPERGROUPACCEPT', '-LEAGUEACCEPT'):
            self.assertIn(flag, first)
        second = driver.client_command(root, ACCOUNT, NAME)
        self.assertEqual(second[-3:], ['-justlogin', '-character', NAME])
        self.assertNotIn('-CREATE', second)

    def test_private_configuration_retains_required_provider_and_disables_auxiliaries(self):
        text = driver.character_config('SqlInit "old MSSQL init"\nSqlDbProvider MSSQL\n'
            'SqlLogin old\nSqlDbName old\nSqlAllowDDL 1\nUseFakeAuth 1\nUseQueueServer 0\n'
            'DefaultAccessLevel 0\nAdvertisedIp 192.0.2.3\n',
            'SqlDbProvider PostgreSQL\nSqlDbName coh_test\nSqlLogin "private"\n')
        for line in ('DefaultAccessLevel 9', 'AdvertisedIp 127.0.0.1', 'UseFakeAuth 1', 'UseQueueServer 0',
                     'BlockFreePlayersIfNoAccountServer 0', 'NoStats 1', 'SqlDbProvider PostgreSQL'):
            self.assertEqual(text.splitlines().count(line), 1)
        self.assertNotIn('SqlInit', text)
        self.assertNotIn('MSSQL', text)

    def test_positive_character_id_requires_one_clean_find_reply(self):
        self.assertEqual(driver.parse_find('noise\ncontainer_id = 9\n'), 9)
        for text in ('', 'container_id = -1\n', 'container_id = 0\n',
                     'container_id = 9\ncontainer_id = 9\n', 'container_id = 9\nSQLERROR: broken'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                driver.parse_find(text)

    def test_connected_character_requires_same_identity_and_atlas_no_transfer(self):
        result = driver.parse_character_status(STATUS, 9, NAME, ACCOUNT)
        self.assertTrue(driver.connected_on_atlas(result))
        for changed in (STATUS.replace('MapId 1', 'MapId 2'), STATUS.rstrip() + ' NoConnect\n',
                        STATUS.rstrip() + ' InMapXfer\n'):
            self.assertFalse(driver.connected_on_atlas(driver.parse_character_status(changed, 9, NAME, ACCOUNT)))
        for changed in (STATUS.replace(NAME, 'another'), STATUS.replace(ACCOUNT, 'another'),
                        STATUS.replace('    9 ', '   10 '), STATUS * 2, 'Status: Running\n',
                        STATUS.rstrip() + ' UnknownFlag\n', STATUS + 'SQLERROR: failed\n'):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                driver.parse_character_status(changed, 9, NAME, ACCOUNT)
        self.assertFalse(driver.parse_character_status('invalid container request\n', 9, NAME, ACCOUNT,
                                                       allow_missing=True)['loaded'])
        with self.assertRaises(ValueError):
            driver.parse_character_status('invalid container request\n', 9, NAME, ACCOUNT)

    def test_status_flags_cannot_consume_following_process_diagnostics(self):
        # Run36269025801 returned a valid connected status with no flags, then
        # the original multiline whitespace pattern read past the response.
        windows_line = ('    1 Name TEST14081        Auth CohPfba5e64b23   '
                        'Ip 127.0.0.1        MapId 1 SmapId 1  \r\n')
        for suffix in ('\r\nDisconnecting...\r\n', 'Total time: 0.3\r\n', '\n'):
            text = 'Query startup diagnostic\r\n' + windows_line + suffix
            state = driver.parse_character_status(text, 1, 'TEST14081', 'CohPfba5e64b23')
            self.assertTrue(driver.connected_on_atlas(state))
        disconnected = windows_line.rstrip() + ' NoConnect\r\nDisconnecting...\r\n'
        self.assertFalse(driver.parse_character_status(disconnected, 1, 'TEST14081', 'CohPfba5e64b23')['connected'])
        with self.assertRaisesRegex(ValueError, 'Unknown character status flags'):
            driver.parse_character_status(windows_line.rstrip() + ' Unexpected\r\n', 1,
                                          'TEST14081', 'CohPfba5e64b23')

    def test_pipe_identity_requires_child_pid_version_player_map_and_running(self):
        state = pipe_state()
        self.assertEqual(driver.pipe_identity(state, 55, ACCOUNT), NAME)
        for mutation in ({'pid_verified': False}, {'client_pid': 56}, {'version_requests': 0},
                         {'player': None}, {'map_name': None}):
            self.assertFalse(driver.pipe_identity(dict(state, **mutation), 55, ACCOUNT))
        changed = copy.deepcopy(state)
        changed['events'] = [e for e in changed['events'] if e['kind'] != 'Status']
        self.assertFalse(driver.pipe_identity(changed, 55, ACCOUNT))
        for mutation in ({'map_name': 'Atlas Park'}, {'map_name': 'maps/City_Zones/City_00_01/City_00_01.txt'},
                         {'error': 'broken framing'}):
            with self.assertRaises(ValueError):
                driver.pipe_identity(dict(state, **mutation), 55, ACCOUNT)

    def test_exact_no_create_resume_requires_all_positive_evidence(self):
        result = driver.accept_resume(resume_text(), pipe_state(), 55, ACCOUNT, NAME, 0)
        self.assertTrue(result['creation_disabled'])
        self.assertFalse(result['active_gameplay_confirmed'])
        variants = ['', 'Status: Running\n', resume_text().replace('Found character', 'Unable to locate character'),
                    resume_text().replace(NAME, 'Different'), resume_text().replace('commReqScene()', 'nothing'),
                    resume_text().replace('slot 2...done', 'slot 3...done'),
                    resume_text() + 'simulateCharacterCreate()\n', resume_text() + 'Server timeout\n']
        for text in variants:
            with self.subTest(text=text), self.assertRaises(ValueError):
                driver.accept_resume(text, pipe_state(), 55, ACCOUNT, NAME, 0)
        with self.assertRaises(ValueError):
            driver.accept_resume(resume_text(), pipe_state(), 55, ACCOUNT, NAME, 1)

    def test_live_currency_requires_server_printf_and_recent_matching_identity(self):
        event = {'sequence': 9, 'time_utc': 'now', 'raw':
                 f'ChatText:conPrintf:0:\nPlayer:    {NAME} \nLogin:     {ACCOUNT} \nCurrent cash: 12345 (Influence)\n'}
        self.assertEqual(driver.live_currency_evidence([event], NAME, ACCOUNT, 8)['influence'], 12345)
        self.assertFalse(driver.live_currency_evidence([event], NAME, ACCOUNT, 9))
        for raw in (event['raw'].replace('conPrintf:0:', 'Local:0:'),
                    event['raw'].replace('Current cash: 12345', 'Current cash: 12344')):
            self.assertFalse(driver.live_currency_evidence([dict(event, raw=raw)], NAME, ACCOUNT, 8))
        for raw in (event['raw'].replace(NAME, 'OTHER'), event['raw'].replace(ACCOUNT, 'OTHER'),
                    event['raw'] + 'Current cash: 12345 (Influence)\n',
                    event['raw'].replace('Current cash:', 'Wrong currency:')):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                driver.live_currency_evidence([dict(event, raw=raw)], NAME, ACCOUNT, 8)

    def test_only_exact_known_fatal_after_quit_may_be_classified_as_logout(self):
        expected = 'Fatal Error: Booted back to login screen'
        self.assertEqual(driver.diagnostic_failures(expected), [expected])
        self.assertEqual(driver.diagnostic_failures(expected, allow_requested_logout=True), [])
        for message in ('Fatal Error: other', 'CRASH', 'SQLERROR: something broke', 'Errorf: invalid data'):
            self.assertEqual(driver.diagnostic_failures(message, allow_requested_logout=True), [message])
        state = pipe_state()
        error = {'kind': 'Status', 'value': 'ERROR', 'sequence': 8}
        state['events'].append(error)
        with self.assertRaises(ValueError):
            driver.pipe_identity(state, 55, ACCOUNT, allow_logout_error=True)
        state['events'].insert(-1, {'kind': 'QuitNow', 'value': '', 'sequence': 7})
        self.assertEqual(driver.pipe_identity(state, 55, ACCOUNT, allow_logout_error=True), NAME)
        with self.assertRaises(ValueError):
            driver.pipe_identity(state, 55, ACCOUNT)
        error['value'] = 'CRASH'
        with self.assertRaises(ValueError):
            driver.pipe_identity(state, 55, ACCOUNT, allow_logout_error=True)

    def test_public_pipe_record_excludes_arbitrary_chat_host_and_raw_data(self):
        state = pipe_state()
        state['events'].append({'kind': 'ChatText', 'raw': 'PRIVATE FULL PAYLOAD', 'value': 'private'})
        result = str(driver.selected_pipe_record(state))
        self.assertNotIn('PRIVATE', result)
        self.assertNotIn('ChatText', result)
        self.assertNotIn("'raw'", result)


class CharacterReceiptTests(unittest.TestCase):
    def setUp(self):
        self.context = {'package': {'repository_commit': 'c' * 40},
                        'hashes': {'DbServer.exe': 'd' * 64, 'MapServer.exe': 'e' * 64}}
        self.receipt = {'status': driver.one_map.SUCCESS, 'failures': [],
            'baseline_not_started_verified': True, 'comparison_caches_reused': False,
            'generated_output_count': 1328, 'source_commit': driver.one_map.generation.SOURCE_COMMIT,
            'data_commit': driver.one_map.generation.DATA_COMMIT, 'reference_repository_commit': 'c' * 40,
            'dbserver_sha256': 'd' * 64, 'mapserver_sha256': 'e' * 64,
            'comparison_report_sha256': 'f' * 64, 'comparison_inputs_sha256': 'a' * 64,
            'observed_ready_seconds': 60.5, 'map_contract': {'map_id': 1, 'map_path': driver.one_map.MAP_PATH},
            'status_samples': [{'ready': True, 'port': 7001, 'network_age_seconds': 1, 'stats_age_seconds': 1}]}

    def test_prior_map_receipt_binds_success_to_exact_source_binaries_and_comparison(self):
        driver.accept_one_map(self.receipt, self.context, 'f' * 64, 'a' * 64)
        for mutation in ({'status': 'passed'}, {'failures': ['a failure']}, {'source_commit': '0' * 40},
                         {'comparison_report_sha256': '0' * 64}, {'comparison_inputs_sha256': '0' * 64},
                         {'dbserver_sha256': '0' * 64}, {'mapserver_sha256': '0' * 64},
                         {'generated_output_count': 55}, {'observed_ready_seconds': 0}, {'status_samples': []}):
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                driver.accept_one_map(dict(self.receipt, **mutation), self.context, 'f' * 64, 'a' * 64)

    def test_actual_accepted_one_map_receipt_passes_gate(self):
        report = json.loads((driver.ROOT / 'docs/postgresql-evidence/one-map-36176806895.json').read_text())
        comparison_path = driver.ROOT / 'docs/reference-runtime-evidence/reference-template-comparison-36176806895.json'
        context = {'package': {'repository_commit': report['reference_repository_commit']},
                   'hashes': {'DbServer.exe': report['dbserver_sha256'], 'MapServer.exe': report['mapserver_sha256']}}
        driver.accept_one_map(report, context, driver.sha256(comparison_path), report['comparison_inputs_sha256'])

    def test_preflight_rejection_prevents_credentials_or_processes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(driver.one_map, 'preflight', side_effect=ValueError('Unaccepted inputs')), \
                 patch.object(driver, 'initialize') as initialize, patch.object(driver.network, 'Process') as process:
                with self.assertRaisesRegex(ValueError, 'Unaccepted inputs'):
                    driver.run(root / 'runtime', root / 'reference', root / 'schema', root / 'comparison',
                               root / 'inputs', root / 'one-map', root / 'work', root / 'output', 'unused', 'unused')
                initialize.assert_not_called()
                process.assert_not_called()
            self.assertFalse((root / 'work').exists())
            self.assertFalse((root / 'output').exists())


if __name__ == '__main__':
    unittest.main()
