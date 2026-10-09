"""Reject stale, foreign, ambiguous and crash-only command/task evidence."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import task_gate_evidence as gate

SESSION = '0123456789abcdef0123456789abcdef'
PID = 44
ENTITY = 'logs/mapserver/entity.log'
ADMIN = 'logs/mapserver/admin.log'
REWARDS = 'logs/mapserver/rewards.log'
TASK_NAME = 'Mission1'
SUFFIX = ' ExpLevel:1, AlignmentNum:0, Archetype:Class_Blaster, Incarnate:0'


def stamp(seconds):
    return int(time.mktime(time.strptime('261003 12:00:00', '%y%m%d %H:%M:%S')) * 1000) + seconds * 1000


def proof():
    return {'session_id': SESSION, 'client_pid': PID, 'character_id': 1, 'auth_id': 77,
        'map_id': 1, 'name': 'THORHERO', 'account': 'COHLOCAL', 'connected_on_atlas': True,
        'existing_character_verified': True, 'preserved_existing_identity': True,
        'reopen_verified': True, 'native_client_ready_observed': True,
        'client_ready_observed_utc_ms': stamp(10),
        'client_ready_evidence': {'source': 'current_owned_mapserver_immediate_ready',
            'kind': 'ready', 'session_id': SESSION, 'map_id': 1, 'db_id': 1, 'auth_id': 77,
            'name': 'THORHERO', 'account': 'COHLOCAL', 'windows_pid': 90,
            'main_thread_id': 91, 'utc_ms': stamp(9), 'loaded_world_assets': True}}


def line(seconds, body, *, route=None, identity='THORHERO:COHLOCAL', suffix=SUFFIX):
    route = ('2' if body.startswith('Storyarc:Add') else '0') if route is None else route
    calendar = time.strftime('%y%m%d %H:%M:%S', time.localtime(stamp(seconds) / 1000))
    return f'{calendar} {route} "{identity}" 0 {body}{suffix}\n'


def rows(state=1):
    return {
        'tasks': [{'containerid': 1, 'subid': 0, 'id': 811, 'subhandle': 1,
            'compoundpos': None, 'state': state, 'assigneddbid': 1,
            'assignedtime': 844603234, 'seed': 22718899, 'subtasksuccess': None if state == 1 else 1,
            'playercreated': None}],
        'contacts': [{'containerid': 1, 'subid': 0, 'id': 812, 'contactpoints': None,
            'taskissued': None, 'storyarcissued': '01000000', 'contactrelationship': 1, 'notifyplayer': None}],
        'ents': [{'containerid': 1, 'experiencepoints': None, 'influencepoints': None}],
        'storyarcs': [{'containerid': 1, 'subid': 0, 'id': 811, 'contact': 812, 'episode': None}],
    }


def baseline():
    value = rows()
    value['tasks'] = []
    value['storyarcs'] = []
    return value


def attributes():
    return [{'id': 811, 'name': gate.CONTEXT_PATH.upper()}, {'id': 812, 'name': gate.CONTACT_PATH.upper()}]


def setup():
    return {'format': 1, 'session_id': SESSION, 'client_pid': PID, 'character_id': 1,
        'action': 'contactdialog', 'contact_path': gate.CONTACT_PATH, 'sent_utc_ms': stamp(11),
        'commands': ['/contactdialog ' + gate.CONTACT_PATH], 'native_effect_verified': False}


def accepted_logs():
    return [(ENTITY, line(12, 'ContactInteract:Debug Initiating interaction with contact 173')
        + line(14, 'Storyarc:Add Handle -52') + line(15, 'Task:Add ' + TASK_NAME))]


def acceptance(logs=None, sql=None, **changes):
    kwargs = {'session': SESSION, 'client_pid': PID, 'now_utc_ms': stamp(20),
              'baseline_rows': baseline(), 'attributes': attributes(), 'setup_receipt': setup()}
    kwargs.update(changes)
    return gate.observe_acceptance(accepted_logs() if logs is None else logs, proof(),
        rows() if sql is None else sql, **kwargs)


def receipt(accepted=None):
    accepted = acceptance() if accepted is None else accepted
    return {'format': 1, 'session_id': SESSION, 'client_pid': PID, 'character_id': 1,
        'action': 'completetask', 'task_index': 0, 'task': accepted['task'], 'sent_utc_ms': stamp(21)}


def completed_logs():
    return [(ENTITY, accepted_logs()[0][1] + line(22,
        'Task:Success Name: Mission1, Type: taskKillX')),
        (ADMIN, line(22, 'Task:ForceComplete Auth: COHLOCAL Task: ' + gate.TASK_FILE.upper())
        + line(22, 'Task:ForceComplete Character Level: 1')
        + line(22, 'Task:ForceComplete Context: -52 Subhandle: 1')
        + line(22, 'Task:ForceComplete Contact Name: Matthew Habashy')
        + line(22, 'Task:ForceComplete Task Name: Mission1, File: ' + gate.TASK_FILE.upper())
        + line(22, 'Task:ForceComplete Task Level: 1')),
        (REWARDS, line(22, '[Tbl]:Rcv:Points XP: 25, Debt: 0, Inf: 0, Pres: 0 (SGMode off (0))'))]


def completed_rows():
    value = rows(4)
    value['ents'][0]['experiencepoints'] = 25
    value['contacts'][0]['contactpoints'] = 10
    return value


def completion(logs=None, sql=None, accepted=None, delivery=None, **changes):
    accepted = acceptance() if accepted is None else accepted
    kwargs = {'session': SESSION, 'client_pid': PID, 'now_utc_ms': stamp(30)}
    kwargs.update(changes)
    return gate.observe_completion(completed_logs() if logs is None else logs, proof(), accepted,
        receipt(accepted) if delivery is None else delivery,
        completed_rows() if sql is None else sql, **kwargs)


def saved(sql=None, ordinary=True, done=None, **changes):
    kwargs = {'session': SESSION, 'client_pid': PID, 'now_utc_ms': stamp(60),
              'ordinary_save_verified': ordinary}
    kwargs.update(changes)
    return gate.verify_saved(completed_logs(), proof(), acceptance(), completion() if done is None else done,
        completed_rows() if sql is None else sql, **kwargs)


class TaskGateEvidenceTests(unittest.TestCase):
    def test_authored_native_acceptance_and_sql_bind_one_task_without_mutation(self):
        sql, logs, before = rows(), accepted_logs(), copy.deepcopy(rows())
        result = acceptance(logs=logs, sql=sql)
        self.assertTrue(result['task_accepted_verified'])
        self.assertEqual(result['task'], {'name': 'Mission1', 'context': -52, 'subhandle': 1, 'task_index': 0})
        self.assertEqual(result['sql_context_attribute_id'], 811)
        self.assertEqual(result['native_contact_runtime_handle'], 173)
        self.assertEqual(result['context_kind'], 'native_runtime_storyarc_handle_not_sql_attribute_id')
        self.assertEqual(result['sql_at_acceptance']['tasks'][0]['compoundpos'], 0)
        self.assertEqual(sql, before)
        self.assertFalse(result['verified'])
        self.assertFalse(result['combat_verified'])
        self.assertFalse(result['mission_map_verified'])
        self.assertFalse(result['sql_game_mutations_performed'])
        signed = rows(); signed['tasks'][0]['seed'] = -2147483648
        self.assertTrue(acceptance(sql=signed)['task_accepted_verified'])

    def test_stock_force_success_sql_and_ordinary_save_pass_without_reward_turn_in(self):
        complete = completion()
        self.assertTrue(complete['task_completed_verified'])
        self.assertTrue(complete['completed_task_pending_contact_return'])
        result = saved(done=complete)
        self.assertTrue(result['verified'])
        self.assertTrue(result['task_save_verified'])
        self.assertTrue(result['ordinary_character_save_verified'])
        self.assertFalse(result['reward_turn_in_verified'])
        self.assertFalse(result['dialog_semantics_verified'])
        self.assertEqual(result['task'], complete['task'])

    def test_baseline_existing_task_multiple_current_tasks_and_missing_sql_never_arm(self):
        for sql, before in [(rows(), rows()), (dict(rows(), tasks=rows()['tasks'] * 2), baseline()),
                            (dict(rows(), tasks=[]), baseline())]:
            with self.subTest(sql=sql, before=before):
                self.assertFalse(acceptance(sql=sql, baseline_rows=before)['task_accepted_verified'])
        for field in ('experiencepoints', 'influencepoints'):
            sql = rows(); sql['ents'][0][field] = 1
            self.assertFalse(acceptance(sql=sql)['task_accepted_verified'])

    def test_non_contract_compound_failed_foreign_and_duplicate_rows_never_arm(self):
        for table, key, value in [('tasks', 'containerid', 2), ('tasks', 'assigneddbid', 2),
                ('tasks', 'compoundpos', 1), ('tasks', 'subid', 1), ('tasks', 'subhandle', 2),
                ('tasks', 'playercreated', 1), ('tasks', 'state', 4), ('tasks', 'subtasksuccess', 1),
                ('tasks', 'id', 812), ('tasks', 'seed', True), ('storyarcs', 'contact', 811),
                ('storyarcs', 'episode', 1), ('contacts', 'id', 999), ('ents', 'experiencepoints', -1)]:
            value_rows = rows(); value_rows[table][0][key] = value
            with self.subTest(table=table, key=key, value=value):
                self.assertFalse(acceptance(sql=value_rows)['task_accepted_verified'])
        value_rows = rows(); value_rows['storyarcs'] *= 2
        self.assertFalse(acceptance(sql=value_rows)['task_accepted_verified'])

    def test_wrong_or_duplicate_attribute_and_setup_transport_are_rejected(self):
        for attrs in [[], [{'id': 811, 'name': gate.CONTACT_PATH}], attributes() * 2,
                      [{'id': 811, 'name': '../' + gate.CONTEXT_PATH}, attributes()[1]]]:
            self.assertFalse(acceptance(attributes=attrs)['task_accepted_verified'])
        for field, changed in [('session_id', 'f' * 32), ('client_pid', 99), ('character_id', True),
                ('sent_utc_ms', stamp(16)), ('action', 'addcontact'), ('contact_path', 'Other.contact'),
                ('commands', ['/getcontacttask ' + gate.CONTACT_PATH]), ('native_effect_verified', True),
                ('format', True), ('extra', 1)]:
            with self.subTest(field=field):
                self.assertFalse(acceptance(setup_receipt=dict(setup(), **{field: changed}))['task_accepted_verified'])

    def test_foreign_route_character_account_map_and_incomplete_native_lines_rejected(self):
        for logs in [accepted_logs()[0][1].replace('THORHERO:COHLOCAL', 'OTHER:COHLOCAL'),
                     accepted_logs()[0][1].replace('THORHERO:COHLOCAL', 'THORHERO:OTHER'),
                     accepted_logs()[0][1].replace(' 0 "', ' 1 "'),
                     accepted_logs()[0][1].rstrip('\n')]:
            self.assertFalse(acceptance(logs=[(ENTITY, logs)])['task_accepted_verified'])
        self.assertFalse(acceptance(logs=[('other/entity.log', accepted_logs()[0][1])])['task_accepted_verified'])
        routed = accepted_logs()[0][1].replace(' 0 "', ' City_01_01_2:127.0.0.1:127.0.0.1 "')
        self.assertFalse(acceptance(logs=[('logs/dbserver/entity_2026-10-03-12-00-00.log', routed)])['task_accepted_verified'])

    def test_acceptance_requires_one_native_add_one_contact_and_one_negative_arc_context(self):
        original = accepted_logs()[0][1]
        for text in [original.replace('Task:Add Mission1', 'Task:Add Different'),
                original + line(16, 'Task:Add Mission1'),
                original.replace('Storyarc:Add Handle -52', 'Storyarc:Add Handle 52'),
                original.replace('Storyarc:Add Handle -52', 'Storyarc:Add Handle -2147483649'),
                original.replace('Storyarc:Add Handle -52', 'Storyarc:Add Handle -52') + line(14, 'Storyarc:Add Handle -53'),
                original.replace(line(12, 'ContactInteract:Debug Initiating interaction with contact 173'), ''),
                line(8, 'ContactInteract:Debug Initiating interaction with contact 173') + original.split('\n', 1)[1]]:
            self.assertFalse(acceptance(logs=[(ENTITY, text)])['task_accepted_verified'])

    def test_matching_local_embedded_duplicates_are_one_observation(self):
        entity = accepted_logs()[0][1]
        embedded = entity.replace(' 0 "', ' City_01_01_1:127.0.0.1:127.0.0.1 "').replace(' 2 "', ' City_01_01_1:127.0.0.1:127.0.0.1 "')
        result = acceptance(logs=[('logs/dbserver/entity_2026-10-03-12-00-00.log', embedded), (ENTITY, entity)])
        self.assertTrue(result['task_accepted_verified'])
        logs = completed_logs()
        routed = [(name.replace('logs/mapserver/entity.log', 'logs/dbserver/entity_2026-10-03-12-00-00.log')
            .replace('logs/mapserver/admin.log', 'logs/dbserver/admin_2026-10-03-12-00-00.log')
            .replace('logs/mapserver/rewards.log', 'logs/dbserver/rewards_2026-10-03-12-00-00.log'),
            raw.replace(' 0 "', ' City_01_01_1:127.0.0.1:127.0.0.1 "').replace(' 2 "', ' City_01_01_1:127.0.0.1:127.0.0.1 "')) for name, raw in logs]
        self.assertTrue(completion(logs=routed + logs)['task_completed_verified'])

    def test_malformed_stale_future_foreign_and_changed_completion_receipts_rejected(self):
        for field, changed in [('format', True), ('session_id', 'f' * 32), ('client_pid', True),
                ('character_id', 2), ('task_index', 1), ('action', 'taskcomplete'),
                ('sent_utc_ms', stamp(19)), ('sent_utc_ms', stamp(31)), ('extra', 1),
                ('task', dict(receipt()['task'], context=811))]:
            with self.subTest(field=field):
                self.assertFalse(completion(delivery=dict(receipt(), **{field: changed}))['task_completed_verified'])
        self.assertFalse(completion(now_utc_ms=stamp(202))['task_completed_verified'])
        self.assertFalse(completion(accepted=dict(acceptance(), client_pid=99))['task_completed_verified'])

    def test_completion_requires_exact_authored_native_block_and_matching_success(self):
        raw = completed_logs()
        for old, new, index in [('Auth: COHLOCAL', 'Auth: OTHER', 1),
                ('Context: -52', 'Context: -51', 1), ('Subhandle: 1', 'Subhandle: 2', 1),
                ('Task Name: Mission1', 'Task Name: Other', 1), ('SL1_MATTHEWHABASHY', 'OTHER', 1),
                ('Type: taskKillX', 'Type: taskMission', 0), ('Task:Success', 'Task:Failure', 0)]:
            logs = copy.deepcopy(raw); logs[index] = (logs[index][0], logs[index][1].replace(old, new))
            with self.subTest(old=old):
                self.assertFalse(completion(logs=logs)['task_completed_verified'])
        logs = copy.deepcopy(raw); logs[0] = (ENTITY, logs[0][1] + line(23, 'Task:Success Name: Mission1, Type: taskKillX'))
        self.assertFalse(completion(logs=logs)['task_completed_verified'])
        logs = copy.deepcopy(raw); logs[1] = (ADMIN, logs[1][1] + line(23, 'Task:ForceComplete Auth: COHLOCAL Task: ' + gate.TASK_FILE))
        self.assertFalse(completion(logs=logs)['task_completed_verified'])

    def test_complete_sql_must_retain_exact_accepted_task_state_and_subtask_bit(self):
        for field, changed in [('state', 5), ('state', 2), ('subtasksuccess', 0), ('subtasksuccess', 3),
                ('id', 812), ('assigneddbid', 2), ('seed', 9), ('assignedtime', 7), ('subhandle', 2),
                ('subid', 1), ('compoundpos', 1), ('playercreated', 1)]:
            sql = completed_rows(); sql['tasks'][0][field] = changed
            with self.subTest(field=field):
                self.assertFalse(completion(sql=sql)['task_completed_verified'])
        self.assertFalse(completion(sql=dict(completed_rows(), tasks=[]))['task_completed_verified'])
        for key, value in [('episode', 1), ('contact', 999), ('id', 812)]:
            sql = completed_rows(); sql['storyarcs'][0][key] = value
            self.assertFalse(completion(sql=sql)['task_completed_verified'])
        for key, value in [('subid', 1), ('storyarcissued', '02000000'), ('taskissued', '01000000'),
                           ('contactrelationship', 2), ('notifyplayer', 2)]:
            sql = completed_rows(); sql['contacts'][0][key] = value
            self.assertFalse(completion(sql=sql)['task_completed_verified'])
            self.assertFalse(saved(sql=sql)['verified'])
        sql = completed_rows(); sql['contacts'][0]['notifyplayer'] = 1
        self.assertTrue(completion(sql=sql)['task_completed_verified'])
        self.assertTrue(saved(sql=sql)['verified'])

    def test_saved_task_never_substitutes_for_existing_ordinary_character_save(self):
        for ordinary in [False, None, 1, 'true']:
            self.assertFalse(saved(ordinary=ordinary)['verified'])
        for field, changed in [('state', 1), ('state', 5), ('seed', 99), ('assignedtime', 1)]:
            sql = completed_rows(); sql['tasks'][0][field] = changed
            self.assertFalse(saved(sql=sql)['verified'])
        self.assertFalse(saved(sql=dict(completed_rows(), tasks=[]))['verified'])
        self.assertFalse(saved(done=dict(completion(), session_id='f' * 32))['verified'])
        self.assertFalse(saved(done=dict(completion(), observed_utc_ms=stamp(61)))['verified'])
        self.assertFalse(saved(done=dict(completion(), completion_delivery=dict(receipt(), task_index=1)))['verified'])

    def test_record_limits_freshness_partial_lines_and_input_snapshot_shapes_fail_closed(self):
        with patch.object(gate, 'RECORD_LIMIT', 1):
            self.assertFalse(acceptance()['task_accepted_verified'])
        with patch.object(gate.server, 'SERVER_LOG_FILE_LIMIT', 10):
            self.assertFalse(acceptance()['task_accepted_verified'])
        self.assertFalse(acceptance(logs=[(ENTITY, None)])['task_accepted_verified'])
        self.assertFalse(acceptance(now_utc_ms=stamp(14))['task_accepted_verified'])
        self.assertFalse(acceptance(sql=dict(rows(), extra=[]))['task_accepted_verified'])
        logs = accepted_logs()[0][1] + line(21, 'Task:Add Mission1').replace('261003', '261099')
        self.assertTrue(acceptance(logs=[(ENTITY, logs)])['task_accepted_verified'])

    def test_private_receipts_are_owned_bounded_regular_single_link_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'task.json'
            self.assertIsNone(gate.read_delivery(path, proof(), session=SESSION, client_pid=PID, now_utc_ms=stamp(30)))
            path.write_text(json.dumps(setup()))
            self.assertEqual(gate.read_delivery(path, proof(), session=SESSION, client_pid=PID,
                now_utc_ms=stamp(30)), setup())
            path.write_text(json.dumps(receipt()))
            self.assertEqual(gate.read_delivery(path, proof(), session=SESSION, client_pid=PID,
                now_utc_ms=stamp(30), accepted=acceptance()), receipt())
            path.write_text(json.dumps(dict(receipt(), task_index=1)))
            with self.assertRaises(gate.server.base.DiagnosticError):
                gate.read_delivery(path, proof(), session=SESSION, client_pid=PID,
                    now_utc_ms=stamp(30), accepted=acceptance())
            path.write_text('x' * (gate.RECEIPT_LIMIT + 1))
            with self.assertRaises(gate.server.base.DiagnosticError):
                gate.read_delivery(path, proof(), session=SESSION, client_pid=PID,
                    now_utc_ms=stamp(30), accepted=acceptance())
            path.unlink(); path.symlink_to(Path(directory) / 'missing')
            with self.assertRaises(OSError):
                gate.read_delivery(path, proof(), session=SESSION, client_pid=PID, now_utc_ms=stamp(30))

    def test_reward_credit_matches_actual_native_xp_not_authored_nominal_and_remains_bounded(self):
        sql = completed_rows(); sql['ents'][0]['experiencepoints'] = 50
        logs = completed_logs(); logs[2] = (REWARDS, logs[2][1].replace('XP: 25', 'XP: 50'))
        result = completion(logs=logs, sql=sql)
        self.assertTrue(result['task_completed_verified'])
        self.assertEqual(result['credited_experience'], 50)
        self.assertEqual(result['expected_saved_reward_values']['experiencepoints'], 50)
        self.assertFalse(result['native_reward_log_contains_task_name'])
        for old, new in [('XP: 25', 'XP: 1001'), ('Inf: 0', 'Inf: 1'), ('Pres: 0', 'Pres: 1'),
                         ('Debt: 0', 'Debt: 1001'), ('off (0)', 'off (1)'), ('XP: 25', 'XP: -25')]:
            logs = completed_logs(); logs[2] = (REWARDS, logs[2][1].replace(old, new))
            self.assertFalse(completion(logs=logs)['task_completed_verified'])
        logs = completed_logs(); logs[2] = (REWARDS, logs[2][1] + line(23,
            '[Tbl]:Rcv:Points XP: 25, Debt: 0, Inf: 0, Pres: 0 (SGMode off (0))'))
        self.assertFalse(completion(logs=logs)['task_completed_verified'])
        logs = completed_logs(); logs[2] = (REWARDS, line(28,
            '[Tbl]:Rcv:Points XP: 25, Debt: 0, Inf: 0, Pres: 0 (SGMode off (0))'))
        self.assertFalse(completion(logs=logs)['task_completed_verified'])
        for table, field, value in [('ents', 'experiencepoints', 24), ('ents', 'influencepoints', 1),
                                  ('contacts', 'contactpoints', 9)]:
            sql = completed_rows(); sql[table][0][field] = value
            self.assertFalse(completion(sql=sql)['task_completed_verified'])
            self.assertFalse(saved(sql=sql)['verified'])

    def test_level_two_logging_is_scoped_to_deprecated_arc_records(self):
        original = accepted_logs()[0][1]
        self.assertFalse(acceptance(logs=[(ENTITY, original.replace(' 0 "', ' 2 "'))])['task_accepted_verified'])
        self.assertFalse(acceptance(logs=[(ENTITY, original.replace(' 2 "', ' 0 "'))])['task_accepted_verified'])


if __name__ == '__main__':
    unittest.main()
