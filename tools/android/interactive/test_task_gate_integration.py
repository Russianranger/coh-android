"""Task-only runtime, ordinary-save protection and delayed SQL observations."""
import copy
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'android/guest'))
import character_reopen_diagnostic as guest
import local_character_server as server
import task_gate_evidence as evidence
from test_character_reopen_guest import reopened
from test_character_server import SESSION
from test_task_gate_evidence import acceptance, completion, proof, setup, attributes, baseline, rows


def task_server(state):
    value = server.LocalCharacterTaskReopenServer.__new__(server.LocalCharacterTaskReopenServer)
    value.owner = SimpleNamespace(args=SimpleNamespace(state=state, session_id=SESSION))
    value.creation_report = dict(proof(), task_gate_required=True)
    value.ctx = SimpleNamespace(report={'task_gate': {}}, check=Mock())
    value.task_evidence = evidence
    value.task_baseline = baseline()
    value.task_accepted = value.task_completed = value.task_saved = None
    value.task_sql_next = 0
    value.task_sql_reads = 0
    value.schema = {'expected_attributes': {'attributes': attributes()}}
    value.current_logs = Mock(return_value=[])
    value.sample_progress = Mock(return_value={'live': True})
    value.live_progress = Mock(side_effect=lambda item: item is not None)
    value.health = Mock()
    value.sql_rows = Mock(return_value=[])
    return value


class TaskGateIntegrationTests(unittest.TestCase):
    def test_retained_save_proof_remains_valid_without_task_profile(self):
        self.assertTrue(guest.save_verified(reopened(), SESSION))
        self.assertFalse(guest.save_verified(reopened(task_gate_required=True), SESSION))
        for value in (False, None, 1, 'true'):
            self.assertFalse(guest.save_verified(reopened(task_gate_required=True,
                task_gate_verified=value), SESSION))
        self.assertTrue(guest.save_verified(reopened(task_gate_required=True,
            task_gate_verified=True), SESSION))

    def test_task_profile_is_selected_only_by_its_explicit_packaged_config(self):
        with tempfile.TemporaryDirectory() as temporary:
            d = guest.CharacterReopenDiagnostic.__new__(guest.CharacterReopenDiagnostic)
            d.args = SimpleNamespace(assets=Path(temporary))
            with patch.object(guest.character, 'LocalCharacterReopenServer', return_value='old'), \
                    patch.object(guest.character, 'LocalCharacterTaskReopenServer', return_value='task'):
                self.assertEqual(d.make_server(), 'old')
                (d.args.assets/'task-gate.json').write_text('{}')
                self.assertEqual(d.make_server(), 'task')

    def test_stock_task_logging_is_rewritten_only_in_private_task_runtime(self):
        with tempfile.TemporaryDirectory() as temporary:
            s = task_server(Path(temporary)); s.runtime = Path(temporary)
            config = s.runtime/'data/server/db/servers.cfg'
            config.parent.mkdir(parents=True)
            config.write_text('DefaultAccessLevel 9\nSetLogLevel entity 0\nSetLogLevel database 1\n')
            with patch.object(server.LocalCharacterReopenServer, 'prepare_runtime'):
                s.prepare_runtime()
            text = config.read_text()
            self.assertIn('DefaultAccessLevel 9\n', text)
            self.assertIn('SetLogLevel database 1\n', text)
            self.assertEqual(text.count('SetLogLevel entity'), 1)
            self.assertIn('SetLogLevel entity 2\nSetLogLevel rewards 0\nSetLogLevel admin 0\n', text)
            self.assertTrue(s.ctx.report['task_gate']['native_logging']['task_profile_only'])

    def test_no_task_sql_is_polled_without_current_delivery_and_native_effect(self):
        with tempfile.TemporaryDirectory() as temporary:
            s = task_server(Path(temporary))
            with patch.object(server.LocalCharacterReopenServer, 'observe_connected_character'), \
                    patch.object(evidence, 'read_delivery', return_value=None):
                s.observe_connected_character()
            s.sql_rows.assert_not_called()
            with patch.object(server.LocalCharacterReopenServer, 'observe_connected_character'), \
                    patch.object(evidence, 'read_delivery', return_value=setup()):
                s.observe_connected_character()
            s.sql_rows.assert_not_called()

    def observation(self, server_value, deliveries, live=True):
        return (patch.object(server.LocalCharacterReopenServer, 'observe_connected_character'),
            patch.object(evidence, 'read_delivery', side_effect=deliveries),
            patch.object(evidence, 'records', return_value=[{'kind': 'add'}]),
            patch.object(server.progress, 'compare_records'),
            patch.object(evidence, 'observe_acceptance', return_value=acceptance()))

    def test_changed_delivery_during_sql_query_cannot_emit_acceptance(self):
        with tempfile.TemporaryDirectory() as temporary:
            s = task_server(Path(temporary)); changed = dict(setup(), sent_utc_ms=setup()['sent_utc_ms']+1)
            patches = self.observation(s, [setup(), changed])
            with patches[0], patches[1], patches[2], patches[3], patches[4] as observe:
                with self.assertRaises(server.base.DiagnosticError):
                    s.observe_connected_character()
                observe.assert_not_called()
            self.assertIsNone(s.task_accepted)

    def test_lost_map_progress_after_sql_query_cannot_emit_acceptance(self):
        with tempfile.TemporaryDirectory() as temporary:
            s = task_server(Path(temporary)); s.sample_progress.side_effect = [{'live': True}, None]
            patches = self.observation(s, [setup()])
            with patches[0], patches[1], patches[2], patches[3], patches[4] as observe:
                s.observe_connected_character(); observe.assert_not_called()
            self.assertIsNone(s.task_accepted)

    def test_observation_uses_post_query_clock_and_rechecks_runtime_health(self):
        with tempfile.TemporaryDirectory() as temporary:
            s = task_server(Path(temporary))
            patches = self.observation(s, [setup(), setup()])
            with patches[0], patches[1], patches[2], patches[3] as compare, patches[4] as observe, \
                    patch.object(server.time, 'time', side_effect=[100.0, 110.0]):
                s.observe_connected_character()
            self.assertEqual(observe.call_args.kwargs['now_utc_ms'], 110000)
            s.ctx.check.assert_called_once(); s.health.assert_called_once(); compare.assert_called_once()
            self.assertTrue(s.task_accepted['task_accepted_verified'])
            self.assertEqual(s.task_sql_reads, 1)

    def test_sql_is_read_only_scoped_and_bounded(self):
        s = task_server(Path('/unused'))
        for _ in range(40):
            s.task_rows()
        self.assertEqual(s.sql_rows.call_count, 40*len(evidence.SELECTED))
        for args in s.sql_rows.call_args_list:
            self.assertEqual(args.args[-1], 'containerid=1')
            self.assertIn(args.args[0], evidence.SELECTED)
        with self.assertRaises(server.base.DiagnosticError):
            s.task_rows()
        self.assertEqual(s.sql_rows.call_count, 40*len(evidence.SELECTED))

    def test_verified_native_reward_allows_only_exact_xp_delta(self):
        s = task_server(Path('/unused')); s.task_completed = completion()
        previous = [{'containerid': 1, 'experiencepoints': None, 'influencepoints': None, 'level': None}]
        current = [dict(previous[0], experiencepoints=25)]
        self.assertTrue(s.saved_selected_rows_match('ents', previous, current))
        for changed in (dict(current[0], experiencepoints=26), dict(current[0], level=1),
                        dict(current[0], influencepoints=1), dict(current[0], influencepoints=False)):
            self.assertFalse(s.saved_selected_rows_match('ents', previous, [changed]))
        s.task_completed['reward_credit_verified'] = False
        self.assertFalse(s.saved_selected_rows_match('ents', previous, current))
        self.assertFalse(s.saved_selected_rows_match('powers', [{'id': 1}], [{'id': 2}]))

    def test_save_before_both_native_task_phases_never_reaches_parent_save(self):
        s = task_server(Path('/unused'))
        with patch.object(server.LocalCharacterReopenServer, 'validate_saved_rows') as parent:
            for accepted, completed in ((None, None), (acceptance(), None)):
                s.task_accepted, s.task_completed = accepted, completed
                with self.assertRaises(server.base.DiagnosticError):
                    s.validate_saved_rows({}, [])
            parent.assert_not_called()

    def test_phase_events_emit_once_and_refuse_foreign_client(self):
        d = guest.CharacterReopenDiagnostic.__new__(guest.CharacterReopenDiagnostic)
        d.args = SimpleNamespace(session_id=SESSION)
        d.ctx = SimpleNamespace(report={'character_reopen': reopened(client_pid=44,
            task_gate_required=True, recovery_requested=False),
            'task_gate': {'accepted': acceptance(), 'completed': completion()}}, event=Mock())
        d.connected_announced = True
        with patch.object(guest.creation.CharacterCreationDiagnostic, 'observe_console',
                return_value=('', {'pid': 44}, {})):
            d.observe_console(); d.observe_console()
            self.assertEqual(d.ctx.event.call_count, 2)
            self.assertEqual([call.args[0] for call in d.ctx.event.call_args_list],
                ['character_task_accepted', 'character_task_completed'])
            d.task_completed_announced = False
            d.ctx.report['task_gate']['completed']['client_pid'] = 45
            with self.assertRaises(server.base.DiagnosticError):
                d.observe_console()


if __name__ == '__main__':
    unittest.main()
