"""Ordinary reopen saves accept exact owned point awards without relaxing rows.

The two complete reward lines and logout location below are retained from the
0.13.9 Thor support ZIP, whose provenance is recorded in the device receipt.
The SQL fixture and private sender receipt are synthetic. This host regression
does not turn the original failed device report into a passed physical test.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import character_reopen_diagnostic as guest
import local_character_server as server
import task_gate_evidence as task
from test_character_server import fixture, SESSION
from test_task_gate_evidence import proof as task_proof, completion

ENTITY = 'logs/dbserver/entity_2026-10-04-22-00-00.log'
REWARDS = 'logs/dbserver/rewards_2026-10-04-22-00-00.log'
AWARD_1 = ('261004 22:34:20 City_01_01_1:127.0.0.1:127.0.0.1 "THORHERO:COHLOCAL" 0 '
    '[Tbl]:Rcv:Points XP: 15, Debt: 0, Inf: 7, Pres: 0 (SGMode off (0)) '
    'ExpLevel:1, AlignmentNum:0, Archetype:Class_Blaster, Incarnate:0 '
    'BuildNumber: dev: 26980-26478-29281 19551:30837:11825\n')
AWARD_2 = ('261004 22:34:53 City_01_01_1:127.0.0.1:127.0.0.1 "THORHERO:COHLOCAL" 0 '
    '[Tbl]:Rcv:Points XP: 10, Debt: 0, Inf: 7, Pres: 0 (SGMode off (0)) '
    'ExpLevel:1, AlignmentNum:0, Archetype:Class_Blaster, Incarnate:0 '
    'BuildNumber: dev: 18261-8285-24933 26980:26478:17184\n')
LOGOUT = ('261004 22:36:40 City_01_01_1:127.0.0.1:127.0.0.1 "THORHERO:COHLOCAL" 0 '
    '[Disconnect:Logout timer expired] Science Class_Blaster, Level:1 XPLevel:1 XP:25 '
    'HP:102.50 End:100.00 Debt: 0 Inf:14 AccessLvl: 9 WisLvl: 0 Wis: 0 Merits: 0 Tickets: 0 '
    'ExpLevel:1, AlignmentNum:0, Archetype:Class_Blaster, Incarnate:0 '
    'BuildNumber: dev: 0125-00-32768 9888:17596:22266\n')
PERIODIC = ('261004 22:36:20 City_01_01_1:127.0.0.1:127.0.0.1 "THORHERO:COHLOCAL" 0 '
    'PeriodicInfo pos=<125.4375,18.1875,-203.5> ExpLevel:1\n')
LOCATION = ('261004 22:36:40 City_01_01_1:127.0.0.1:127.0.0.1 "THORHERO:COHLOCAL" 0 '
    'Logout location : map 1 (125.437500 18.187500 -203.500000) '
    'ExpLevel:1, AlignmentNum:0, Archetype:Class_Blaster, Incarnate:0 '
    'BuildNumber: dev: 62964-18-123 22928:197:100\n')


def stamp(calendar):
    return int(time.mktime(time.strptime(calendar, '%y%m%d %H:%M:%S')) * 1000)


READY_MS = stamp('261004 22:31:28') + 823
NOW_MS = stamp('261004 22:36:50')


def connection():
    value = task_proof()
    value['client_ready_observed_utc_ms'] = READY_MS
    value['client_ready_evidence']['utc_ms'] = stamp('261004 22:31:21') + 457
    return value


def delivery():
    return dict(format=1, session_id=SESSION, client_pid=44, character_id=1,
                action='quittologin', sent_utc_ms=stamp('261004 22:36:30'))


def logs(rewards=AWARD_1 + AWARD_2):
    return [(ENTITY, PERIODIC + LOGOUT + LOCATION), (REWARDS, rewards)]


def credit(log_inventory=None, proof=None, receipt=None, now=NOW_MS):
    inventory = logs() if log_inventory is None else log_inventory
    return server.native_reward_credit_evidence(inventory,
        connection() if proof is None else proof, delivery() if receipt is None else receipt,
        server.logout_record(inventory), session=SESSION, client_pid=44, now_utc_ms=now)


class NativeRewardCreditTests(unittest.TestCase):
    def test_retained_two_awards_sum_exactly_and_keep_connection_provenance(self):
        value = credit()
        self.assertEqual((value['experiencepoints_delta'], value['influencepoints_delta']), (25, 14))
        self.assertEqual(value['positive_credit_count'], 2)
        self.assertEqual(value['logout_utc_ms'], stamp('261004 22:36:40'))
        self.assertEqual(value['connection']['character_id'], 1)
        self.assertEqual(value['connection']['auth_id'], 77)
        self.assertFalse(value['connection']['native_log_contains_character_db_id'])
        self.assertFalse(value['connection']['native_log_contains_session_or_client_pid'])
        self.assertFalse(value['combat_defeat_verified'])
        self.assertFalse(value['sql_game_mutations_performed'])
        for record in value['records']:
            self.assertEqual(record['path'], REWARDS)
            self.assertEqual(record['log_route'], 'embedded_dbserver_logserver')
            self.assertEqual(len(record['line_sha256']), 64)

    def test_earlier_later_and_future_awards_are_excluded_at_native_logout(self):
        for calendar in ('261004 22:30:00', '261004 22:36:41', '261004 22:40:00'):
            extra = AWARD_1.replace('261004 22:34:20', calendar).replace('XP: 15', 'XP: 99')
            value = credit(logs(AWARD_1 + AWARD_2 + extra))
            self.assertEqual(value['experiencepoints_delta'], 25)
            self.assertIsNone(credit(logs(extra)))
        self.assertIsNone(credit(now=stamp('261004 22:36:39')))

    def test_zero_records_cannot_authorize_drift_and_zero_duplicates_do_not_count_twice(self):
        zero = AWARD_1.replace('XP: 15', 'XP: 0').replace('Inf: 7', 'Inf: 0')
        self.assertIsNone(credit(logs(zero * 3)))
        value = credit(logs(AWARD_1 + AWARD_2 + zero * 3))
        self.assertEqual(value['candidate_count'], 5)
        self.assertEqual(value['parsed_reward_count'], 3)
        self.assertEqual(value['experiencepoints_delta'], 25)

    def test_positive_duplicates_fail_closed_in_one_file_and_across_logger_routes(self):
        self.assertIsNone(credit(logs(AWARD_1 + AWARD_2 + AWARD_1)))
        mirrored = AWARD_1.replace('City_01_01_1:127.0.0.1:127.0.0.1', '0')
        self.assertIsNone(credit(logs() + [('logs/mapserver/rewards.log', mirrored)]))

    def test_wrong_identity_route_category_map_and_partial_records_never_supply_credits(self):
        bad = [
            [(REWARDS, AWARD_1.replace('THORHERO:COHLOCAL', 'OTHERHERO:COHLOCAL'))],
            [(REWARDS, AWARD_1.replace('City_01_01_1:', 'City_01_02_1:'))],
            [('logs/dbserver/entity_2026-10-04-22-00-00.log', AWARD_1)],
            [('logs/foreign/rewards.log', AWARD_1)],
            [('logs/mapserver/rewards.log', AWARD_1.replace('City_01_01_1:127.0.0.1:127.0.0.1', '2'))],
            [(REWARDS, AWARD_1[:-1])],
        ]
        for inventory in bad:
            with self.subTest(inventory=inventory):
                self.assertIsNone(credit([(ENTITY, LOGOUT)] + inventory))
        self.assertIsNone(credit(logs(AWARD_1 + AWARD_2 + AWARD_1[:-1])))

    def test_unhandled_debt_prestige_sg_malformed_signed_or_overflow_credit_is_refused(self):
        for source, target in (('Debt: 0', 'Debt: 1'), ('Pres: 0', 'Pres: 1'),
                ('SGMode off (0)', 'SGMode off (1)'), ('SGMode off', 'SGMode on'),
                ('XP: 15', 'XP: -15'), ('XP: 15', 'XP: 2147483648'),
                ('XP: 15', 'XP: 99999999999'), ('Inf: 7', 'Inf: +7'),
                ('Class_Blaster', 'unknown')):
            with self.subTest(target=target):
                self.assertIsNone(credit(logs(AWARD_1.replace(source, target) + AWARD_2)))
        too_large = AWARD_1.replace('XP: 15', 'XP: 2147483640')
        self.assertIsNone(credit(logs(too_large + AWARD_2)))

    def test_cap_and_owned_inventory_size_fail_closed_even_when_duplicates_are_zero(self):
        zero = AWARD_1.replace('XP: 15', 'XP: 0').replace('Inf: 7', 'Inf: 0')
        self.assertIsNone(credit(logs(AWARD_1 + AWARD_2 + zero * task.RECORD_LIMIT)))
        self.assertIsNone(credit(logs() * (server.SERVER_LOG_COUNT_LIMIT + 1)))
        with patch.object(task.server, 'SERVER_LOG_FILE_LIMIT', 20):
            self.assertIsNone(credit())
        additions = []
        for second in range(task.RECORD_LIMIT + 1):
            calendar = time.strftime('%y%m%d %H:%M:%S', time.localtime((READY_MS + 1000 + second * 1000) / 1000))
            additions.append(f'{calendar} 0 "THORHERO:COHLOCAL" 0 Task:Add Mission1 '
                'ExpLevel:1, AlignmentNum:0, Archetype:Class_Blaster, Incarnate:0\n')
        self.assertIsNone(credit(logs() + [('logs/mapserver/entity.log', ''.join(additions))]))

    def test_foreign_stale_or_unvalidated_connection_and_sender_are_refused(self):
        for field, value in (('session_id', 'f' * 32), ('client_pid', 45), ('character_id', 2),
                ('auth_id', False), ('map_id', 2), ('name', 'OTHERHERO'),
                ('connected_on_atlas', False), ('existing_character_verified', False),
                ('native_client_ready_observed', False), ('client_ready_evidence', {})):
            changed = connection(); changed[field] = value
            with self.subTest(field=field):
                self.assertIsNone(credit(proof=changed))
        for field, value in (('session_id', 'f' * 32), ('client_pid', 45), ('character_id', True),
                ('action', 'stuck'), ('sent_utc_ms', READY_MS - 1)):
            changed = delivery(); changed[field] = value
            with self.subTest(field=field):
                self.assertIsNone(credit(receipt=changed))
        self.assertIsNone(credit([(REWARDS, AWARD_1 + AWARD_2)]))


class CombatRewardSaveTests(unittest.TestCase):
    def instance(self):
        state = Path(self.enterContext(tempfile.TemporaryDirectory()))
        owner = SimpleNamespace(ctx=SimpleNamespace(report={}, event=Mock()), root=state,
            args=SimpleNamespace(session_id=SESSION, state=state))
        value = server.LocalCharacterReopenServer(owner)
        before, _, attributes = fixture()
        for selected in before.values():
            for row in selected:
                row['containerid'] = 1
        before['ents'][0].update(experiencepoints=None, influencepoints=None, level=None)
        inventory = [{key: before['ents'][0][key] for key in server.evidence.IDENTITY_FIELDS}]
        value.schema = {'expected_attributes': attributes}
        value.auth_id = 77; value.baseline = inventory
        value.baseline_snapshot = server.validate_character_rows(before, inventory, inventory,
            attributes, 77, existing_identity=inventory[0])
        value.creation_report.update(connection(), before_character_id=1, baseline_character_id=1,
            baseline_character_count=1, baseline={'character_id': 1, 'auth_id': 77,
                'login_count': 1, 'table_sha256': {}, 'row_counts': {}})
        self.rows = copy.deepcopy(before)
        self.rows['ents'][0].update(logincount=2, experiencepoints=25, influencepoints=14)
        value.current_logs = Mock(return_value=logs())
        value.current_native_events = Mock(return_value=None)
        value.character_position = Mock(return_value={'containerid': 1, 'mapid': 1, 'staticmapid': 1,
            'posx': 125.4375, 'posy': 18.1875, 'posz': -203.5})
        (state / 'character-logout.json').write_text(json.dumps(delivery()))
        self.enterContext(patch.object(server.time, 'time', return_value=NOW_MS / 1000))
        return value, inventory

    def test_exact_native_credits_preserve_all_other_rows_and_complete_ordinary_save(self):
        value, inventory = self.instance()
        before = copy.deepcopy(value.baseline_snapshot)
        result = value.validate_saved_rows(self.rows, inventory)
        metadata = value.saved_metadata(result)
        self.assertTrue(metadata['selected_rows_preserved'])
        self.assertTrue(metadata['selected_non_reward_rows_preserved'])
        self.assertTrue(metadata['native_reward_values_committed_verified'])
        self.assertEqual(metadata['native_reward_credit_evidence']['expected_saved_reward_values'],
            {'experiencepoints': 25, 'influencepoints': 14})
        self.assertEqual(value.baseline_snapshot, before)
        self.assertTrue(value.creation_report['committed_native_position_verified'])
        self.assertFalse(value.creation_report['recovery_requested'])
        self.assertEqual(result['rows']['powers'], before['rows']['powers'])
        self.assertEqual(result['rows']['costumeparts'], before['rows']['costumeparts'])

    def test_full_owned_logout_pipeline_retains_report_contract_and_reward_proof(self):
        value, inventory = self.instance()
        value.health = Mock()
        value.sample_progress = Mock(return_value={'available': True, 'tick_completed': 7, 'unchanged_seconds': 0})
        value.inventory = Mock(return_value=inventory)
        value.character_rows = Mock(return_value=self.rows)
        value.query = Mock(return_value='invalid container request\n')
        with patch.object(server.progress, 'compare_records'):
            proof = value.character_evidence()
        self.assertTrue(guest.save_verified(proof, SESSION))
        self.assertTrue(proof['committed_sql_verified'])
        self.assertTrue(proof['disconnected_before_sql'])
        self.assertTrue(proof['requested_logout_observed'])
        self.assertTrue(proof['logout_timer_observed'])
        self.assertTrue(proof['native_reward_values_committed_verified'])
        self.assertTrue(proof['selected_rows_preserved'])
        self.assertFalse(proof['forced_stop_before_save'])
        self.assertEqual(proof['saved_native_position_evidence']['source'],
            'current_owned_server_entity_log_ordinary_logout_position')
        self.assertEqual(value.character_evidence(), proof)

    def test_existing_nonzero_reward_balance_uses_delta_and_strict_numeric_types(self):
        value, inventory = self.instance()
        value.baseline_snapshot['rows']['ents'][0].update(experiencepoints=100, influencepoints=200)
        self.rows['ents'][0].update(experiencepoints=125, influencepoints=214)
        self.assertIsNotNone(value.validate_saved_rows(self.rows, inventory))
        for field, changed in (('experiencepoints', 25), ('experiencepoints', True),
                ('experiencepoints', 125.0), ('experiencepoints', '125'),
                ('experiencepoints', -1), ('experiencepoints', 0x80000000),
                ('influencepoints', 215), ('influencepoints', None)):
            altered = copy.deepcopy(self.rows); altered['ents'][0][field] = changed
            with self.subTest(field=field, changed=changed), self.assertRaises(server.base.DiagnosticError):
                value.validate_saved_rows(altered, inventory)

    def test_no_missing_or_zero_credit_proof_can_authorize_null_zero_or_monotonic_drift(self):
        value, inventory = self.instance()
        for rewards in ('', AWARD_1.replace('THORHERO', 'OTHERHERO'),
                AWARD_1.replace('XP: 15', 'XP: 0').replace('Inf: 7', 'Inf: 0')):
            value.current_logs.return_value = logs(rewards)
            for xp, inf in ((25, 14), (0, 0), (1, None)):
                self.rows['ents'][0].update(experiencepoints=xp, influencepoints=inf)
                with self.subTest(rewards=rewards, xp=xp), self.assertRaises(server.base.DiagnosticError):
                    value.validate_saved_rows(self.rows, inventory)
        self.rows['ents'][0].update(experiencepoints=None, influencepoints=None)
        self.assertIsNotNone(value.validate_saved_rows(self.rows, inventory))
        self.assertNotIn('native_reward_values_committed_verified', value.saved_metadata(value.baseline_snapshot))

    def test_every_other_selected_field_remains_strict_including_ent_extension_powers_and_costume(self):
        value, inventory = self.instance()
        for table, fields in server.evidence.SELECTED.items():
            for field in fields:
                if table == 'ents' and field in ('experiencepoints', 'influencepoints'):
                    continue
                altered = copy.deepcopy(self.rows)
                original = altered[table][0][field]
                altered[table][0][field] = 99999 if type(original) is int else 'changed'
                with self.subTest(table=table, field=field), self.assertRaises(server.base.DiagnosticError):
                    value.validate_saved_rows(altered, inventory)
        altered = copy.deepcopy(self.rows); altered['ents'][0]['logincount'] = 3
        with self.assertRaises(server.base.DiagnosticError):
            value.validate_saved_rows(altered, inventory)

    def test_exact_credits_never_bypass_ordinary_sender_or_native_position_gates(self):
        for failure in ('sender_missing', 'sender_foreign', 'sender_expired', 'logout_missing',
                'position_missing', 'position_stale', 'position_fallen', 'sql_position', 'recovery_unverified'):
            value, inventory = self.instance()
            path = value.owner.args.state / 'character-logout.json'
            if failure == 'sender_missing': path.unlink()
            if failure == 'sender_foreign': path.write_text(json.dumps(dict(delivery(), session_id='f' * 32)))
            if failure == 'sender_expired': path.write_text(json.dumps(dict(delivery(), sent_utc_ms=READY_MS)))
            if failure == 'logout_missing': value.current_logs.return_value = [(ENTITY, PERIODIC), (REWARDS, AWARD_1 + AWARD_2)]
            if failure == 'position_missing': value.current_logs.return_value = [(ENTITY, LOGOUT), (REWARDS, AWARD_1 + AWARD_2)]
            if failure == 'position_stale': value.current_logs.return_value[0] = (ENTITY, LOGOUT + LOCATION)
            if failure == 'position_fallen':
                value.current_logs.return_value[0] = (ENTITY, PERIODIC.replace('18.1875', '-2000') + LOGOUT + LOCATION)
            if failure == 'sql_position': value.character_position.return_value['posx'] += 10
            if failure == 'recovery_unverified': value.creation_report['recovery_requested'] = True
            with self.subTest(failure=failure), self.assertRaises(server.base.DiagnosticError):
                value.validate_saved_rows(self.rows, inventory)
            self.assertFalse(value.creation_report['committed_native_position_verified'])

    def test_task_profile_keeps_authored_credit_contract_and_strict_fallback(self):
        value = server.LocalCharacterTaskReopenServer.__new__(server.LocalCharacterTaskReopenServer)
        previous = [{'containerid': 1, 'authid': 77, 'experiencepoints': None, 'influencepoints': None, 'level': None}]
        authored = [dict(previous[0], experiencepoints=25)]
        combat = [dict(previous[0], experiencepoints=25, influencepoints=14)]
        for completed in (None, {}, {'reward_credit_verified': False, 'task_completed_verified': True}):
            value.task_completed = completed
            with patch.object(server.LocalCharacterReopenServer, 'saved_selected_rows_match', return_value=True) as parent:
                self.assertFalse(value.saved_selected_rows_match('ents', previous, authored))
                self.assertFalse(value.saved_selected_rows_match('ents', previous, combat))
                self.assertTrue(value.saved_selected_rows_match('ents', previous, previous))
                parent.assert_not_called()
        value.task_completed = completion()
        self.assertTrue(value.saved_selected_rows_match('ents', previous, authored))
        self.assertFalse(value.saved_selected_rows_match('ents', previous, combat))


if __name__ == '__main__':
    unittest.main()
