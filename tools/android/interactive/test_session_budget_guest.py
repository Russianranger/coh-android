"""Reopen clocks follow native phases without extending recovery/save evidence."""
from datetime import datetime, timezone
from pathlib import Path
import math
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import character_session_budget as policy
import character_reopen_diagnostic as reopen
import character_creation_diagnostic as creation
import client_interactive_diagnostic as interactive

SESSION = 'b415255f972440f3ab7b4a6e42263682'
PID = 672
UTC_START = int(datetime(2026, 10, 2, 12, 24, 40, tzinfo=timezone.utc).timestamp() * 1000)


def proof():
    return {'session_id': SESSION, 'client_pid': PID, 'character_id': 1,
        'before_character_id': 1, 'baseline_character_id': 1, 'auth_id': 1353310574,
        'map_id': 1, 'name': 'THORHERO', 'account': 'COHLOCAL',
        'connected_on_atlas': True, 'reopen_verified': True,
        'existing_character_verified': True, 'preserved_existing_identity': True,
        'native_client_ready_observed': True,
        'client_ready_observed_utc_ms': UTC_START + 1214 * 1000}


def recovered(sent_seconds=1285):
    value = proof()
    value.update(recovery_requested=True, recovery_verified=True,
        ordinary_stuck_observed=True, on_atlas_safe_position=True,
        stable_ground_verified=True, relocation_delivery={
            'format': 1, 'session_id': SESSION, 'client_pid': PID, 'character_id': 1,
            'action': 'stuck', 'sent_utc_ms': UTC_START + sent_seconds * 1000})
    return value


class SessionBudgetGuestTests(unittest.TestCase):
    def budget(self, operation_deadline=5400):
        return policy.SessionBudget(SESSION, PID, 0, operation_deadline)

    def connect(self, budget=None, now=1214):
        budget = budget or self.budget()
        event = budget.connected(proof(), now, UTC_START + int(now * 1000))
        return budget, event

    def test_latest_physical_timeline_retains_save_time_after_login_retry_and_ground_wait(self):
        # Input-ready12:34:42, connected12:44:54, /stuck12:46:05, ground12:49:10.
        old_deadline = 602 + 1200
        budget, event = self.connect()
        self.assertEqual(event['revision'], 1)
        self.assertEqual(event['phase'], 'connected')
        self.assertEqual(budget.deadline, 2040)  # launcher start +34min hard cap
        self.assertGreater(budget.deadline, old_deadline)
        event = budget.grounded(recovered(), 1470, UTC_START + 1470000)
        self.assertEqual(event['revision'], 2)
        self.assertEqual(event['phase'], 'grounded')
        self.assertEqual(event['movement_deadline_utc_ms'], UTC_START + 1645000)
        self.assertEqual(event['save_request_deadline_utc_ms'], UTC_START + 1705000)
        self.assertEqual(event['deadline_utc_ms'], UTC_START + 1885000)
        self.assertEqual(budget.deadline, 1885)
        self.assertEqual(event['deadline_utc_ms'] - event['save_request_deadline_utc_ms'], 180000)
        self.assertEqual(event['save_request_deadline_utc_ms'] - event['movement_deadline_utc_ms'], 60000)
        self.assertEqual(event['deadline_utc_ms'] - recovered()['relocation_delivery']['sent_utc_ms'], 600000)

    def test_no_validated_connection_leaves_the_initial_twenty_minute_menu_bound_unchanged(self):
        diagnostic = reopen.CharacterReopenDiagnostic.__new__(reopen.CharacterReopenDiagnostic)
        diagnostic.connected_announced = False
        self.assertEqual(diagnostic.interaction_deadline(1802, None), 1802)
        self.assertFalse(hasattr(diagnostic, 'session_budget'))

    def test_generic_menu_and_character_creation_keep_their_existing_fixed_deadlines(self):
        for cls in (interactive.ClientInteractiveDiagnostic, creation.CharacterCreationDiagnostic):
            diagnostic = cls.__new__(cls)
            self.assertEqual(diagnostic.interaction_deadline(1234.5, None), 1234.5)
        self.assertNotIn('character_session_budget.py', creation.REQUIRED)
        self.assertIn('character_session_budget.py', reopen.REQUIRED)

    def test_connection_is_one_shot_and_duplicates_cannot_renew_deadline(self):
        budget, event = self.connect(now=900)
        first = budget.deadline
        self.assertIsNone(budget.connected(proof(), 1100, UTC_START + 1100000))
        self.assertEqual(budget.deadline, first)
        self.assertEqual(len(budget.events), 1)
        self.assertEqual(event['save_request_deadline_utc_ms'], event['deadline_utc_ms'] - 180000)
        self.assertEqual(event['movement_deadline_utc_ms'], event['deadline_utc_ms'] - 240000)

    def test_ground_receipt_is_one_shot_and_cannot_be_replaced_or_renewed(self):
        budget, _ = self.connect()
        event = budget.grounded(recovered(), 1470, UTC_START + 1470000)
        first = budget.deadline
        self.assertIsNone(budget.grounded(recovered(), 1500, UTC_START + 1500000))
        self.assertEqual(budget.deadline, first)
        self.assertEqual(len(budget.events), 2)
        replacement = recovered(1300)
        with self.assertRaises(ValueError):
            budget.grounded(replacement, 1500, UTC_START + 1500000)
        self.assertTrue(event['ordinary_stuck_observed'])
        self.assertTrue(event['stable_ground_verified'])

    def test_operation_cap_preserves_neutral_and_save_proof_reserves(self):
        budget, _ = self.connect(self.budget(operation_deadline=2000))
        event = budget.grounded(recovered(1480), 1500, UTC_START + 1500000)
        self.assertEqual(budget.hardcap, 1880)
        self.assertEqual(event['deadline_utc_ms'], UTC_START + 1880000)
        self.assertEqual(event['save_request_deadline_utc_ms'], UTC_START + 1700000)
        self.assertEqual(event['movement_deadline_utc_ms'], UTC_START + 1640000)

    def test_exhausted_ground_allowance_fails_instead_of_presenting_unusable_save_window(self):
        for now, sent in ((1920, 1870), (1705, 1285), (1285 + 601, 1285)):
            budget, _ = self.connect()
            with self.subTest(now=now, sent=sent), self.assertRaises(ValueError):
                budget.grounded(recovered(sent), now, UTC_START + now * 1000)
            self.assertEqual(budget.revision, 1)

    def test_invalid_identity_session_map_or_unvalidated_ready_cannot_grant_budget(self):
        for field, value in (('session_id', 'f' * 32), ('client_pid', PID + 1),
                ('character_id', True), ('map_id', 2), ('name', 'OTHER'), ('account', 'OTHER'),
                ('native_client_ready_observed', False), ('existing_character_verified', False),
                ('reopen_verified', False), ('preserved_existing_identity', False)):
            budget = self.budget(); value_proof = proof(); value_proof[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                budget.connected(value_proof, 1214, UTC_START + 1214000)
            self.assertEqual(budget.revision, 0)

    def test_ground_requires_exact_current_delivered_stuck_receipt_after_ready(self):
        changes = [('format', True), ('session_id', 'f' * 32), ('client_pid', PID + 1),
            ('character_id', True), ('action', 'quittologin'), ('sent_utc_ms', UTC_START),
            ('sent_utc_ms', UTC_START + 1501000), ('sent_utc_ms', True)]
        for field, value in changes:
            budget, _ = self.connect(); value_proof = recovered()
            value_proof['relocation_delivery'][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                budget.grounded(value_proof, 1470, UTC_START + 1470000)
        budget, _ = self.connect()
        value_proof = recovered(); value_proof['stable_ground_verified'] = False
        with self.assertRaises(ValueError):
            budget.grounded(value_proof, 1470, UTC_START + 1470000)

    def test_nonfinite_bool_or_exhausted_caps_and_backwards_monotonic_clock_are_refused(self):
        for start, cap in ((math.nan, 5400), (0, math.inf), (False, 5400), (0, 120)):
            with self.subTest(start=start, cap=cap), self.assertRaises(ValueError):
                policy.SessionBudget(SESSION, PID, start, cap)
        budget, _ = self.connect()
        for now, utc in ((math.inf, UTC_START), (False, UTC_START), (1213, UTC_START),
                         (1214, True)):
            with self.subTest(now=now, utc=utc), self.assertRaises(ValueError):
                budget.connected(proof(), now, utc)

    def test_reopen_hook_emits_current_native_phases_once_and_returns_effective_deadline(self):
        diagnostic = reopen.CharacterReopenDiagnostic.__new__(reopen.CharacterReopenDiagnostic)
        diagnostic.args = SimpleNamespace(session_id=SESSION)
        diagnostic.ctx = SimpleNamespace(deadline=5400,
            report={'character_reopen': proof()}, event=Mock())
        diagnostic.connected_announced = True
        diagnostic.launcher_started_monotonic = 0
        diagnostic.presentation_ready_monotonic = 0
        with patch.object(reopen.time, 'monotonic', return_value=1214), \
             patch.object(reopen.time, 'time', return_value=(UTC_START + 1214000) / 1000):
            self.assertEqual(diagnostic.interaction_deadline(1802, {'pid': PID}), 2040)
        diagnostic.ctx.report['character_reopen'] = recovered()
        diagnostic.relocated_announced = True
        with patch.object(reopen.time, 'monotonic', return_value=1470), \
             patch.object(reopen.time, 'time', return_value=(UTC_START + 1470000) / 1000):
            self.assertEqual(diagnostic.interaction_deadline(2040, {'pid': PID}), 1885)
            self.assertEqual(diagnostic.interaction_deadline(1885, {'pid': PID}), 1885)
        self.assertEqual(diagnostic.ctx.event.call_count, 2)
        events = diagnostic.ctx.report['character_session_budgets']
        self.assertEqual([event['revision'] for event in events], [1, 2])
        self.assertTrue(all(event['client_pid'] == PID and event['session_id'] == SESSION for event in events))
        self.assertEqual(diagnostic.ctx.event.call_args.args, ('character_session_budget',))

    def test_slow_poll_cannot_admit_first_connection_at_or_after_menu_expiry(self):
        for now in (1802, 1802.001):
            diagnostic = reopen.CharacterReopenDiagnostic.__new__(reopen.CharacterReopenDiagnostic)
            diagnostic.args = SimpleNamespace(session_id=SESSION)
            diagnostic.ctx = SimpleNamespace(deadline=5400,
                report={'character_reopen': proof()}, event=Mock())
            diagnostic.connected_announced = True
            diagnostic.launcher_started_monotonic = 0
            diagnostic.presentation_ready_monotonic = 0
            with self.subTest(poll_returned=now), \
                 patch.object(reopen.time, 'monotonic', return_value=now), \
                 patch.object(reopen.time, 'time', return_value=(UTC_START + int(now * 1000)) / 1000), \
                 self.assertRaisesRegex(Exception, 'current menu deadline'):
                diagnostic.interaction_deadline(1802, {'pid': PID})
            self.assertFalse(hasattr(diagnostic, 'session_budget'))
            diagnostic.ctx.event.assert_not_called()

    def test_slow_ground_poll_cannot_revive_expired_connected_phase(self):
        for now, accepted in ((1200, True), (1600, False), (1600.001, False)):
            diagnostic = reopen.CharacterReopenDiagnostic.__new__(reopen.CharacterReopenDiagnostic)
            diagnostic.args = SimpleNamespace(session_id=SESSION)
            value = proof(); value['client_ready_observed_utc_ms'] = UTC_START + 400000
            diagnostic.ctx = SimpleNamespace(deadline=5400,
                report={'character_reopen': value}, event=Mock())
            diagnostic.connected_announced = True
            diagnostic.launcher_started_monotonic = 0
            diagnostic.presentation_ready_monotonic = 0
            with patch.object(reopen.time, 'monotonic', return_value=400), \
                 patch.object(reopen.time, 'time', return_value=(UTC_START + 400000) / 1000):
                self.assertEqual(diagnostic.interaction_deadline(1802, {'pid': PID}), 1600)
            value = recovered(1150); value['client_ready_observed_utc_ms'] = UTC_START + 400000
            diagnostic.ctx.report['character_reopen'] = value
            diagnostic.relocated_announced = True
            with self.subTest(poll_returned=now), \
                 patch.object(reopen.time, 'monotonic', return_value=now), \
                 patch.object(reopen.time, 'time', return_value=(UTC_START + int(now * 1000)) / 1000):
                if accepted:
                    self.assertEqual(diagnostic.interaction_deadline(1600, {'pid': PID}), 1600)
                else:
                    with self.assertRaisesRegex(Exception, 'current connected deadline'):
                        diagnostic.interaction_deadline(1600, {'pid': PID})
            self.assertEqual(diagnostic.session_budget.revision, 2 if accepted else 1)
            self.assertEqual(diagnostic.ctx.event.call_count, 2 if accepted else 1)

    def test_connection_grants_finite_play_and_save_without_recovery(self):
        budget, event = self.connect(now=900)
        self.assertEqual(event['phase'], 'connected')
        self.assertEqual(event['movement_deadline_utc_ms'], event['save_request_deadline_utc_ms'] - 60000)
        self.assertEqual(event['save_request_deadline_utc_ms'], event['deadline_utc_ms'] - 180000)
        self.assertNotIn('stable_ground_verified', event)
        self.assertNotIn('ordinary_stuck_observed', event)
        self.assertIsNone(budget.receipt)

    def test_optional_recovery_can_shorten_but_never_extend_connected_window(self):
        budget, _ = self.connect(now=400)
        recovered_proof = recovered(1150)
        recovered_proof['client_ready_observed_utc_ms'] = UTC_START + 400000
        first_end = budget.deadline
        event = budget.grounded(recovered_proof, 1200, UTC_START + 1200000)
        self.assertEqual(budget.deadline, first_end)
        self.assertTrue(event['recovery_verified'])
        self.assertEqual(event['deadline_utc_ms'], UTC_START + 1600000)

    def test_connection_arriving_without_reserves_fails_without_granting_budget(self):
        budget = self.budget(operation_deadline=1574)
        with self.assertRaisesRegex(ValueError, 'neutral wait'):
            budget.connected(proof(), 1214, UTC_START + 1214000)
        self.assertEqual(budget.revision, 0)

    def test_thor_22_slow_launcher_preparation_fits_retained_android_display_bound(self):
        # Actual .22 display16:05:51.426, launcher16:06:53.901, connect16:21:11.342.
        # Android kept a35min display bound; old launcher+34min exceeded it2.475s.
        display_utc_ms = 1791561951426
        launch_seconds = 62.475
        connected_seconds = (1791562871342 - display_utc_ms) / 1000
        legacy = policy.SessionBudget(SESSION, PID, launch_seconds, 5400)
        old = legacy.connected(proof(), connected_seconds, 1791562871342)
        self.assertEqual(old['deadline_utc_ms'], 1791564053901)

        diagnostic = reopen.StartupOnlyCharacterReopenDiagnostic.__new__(
            reopen.StartupOnlyCharacterReopenDiagnostic)
        diagnostic.args = SimpleNamespace(session_id=SESSION)
        diagnostic.ctx = SimpleNamespace(deadline=5400,
            report={'character_reopen': proof()}, event=Mock())
        diagnostic.connected_announced = True
        diagnostic.presentation_ready_monotonic = 0
        diagnostic.launcher_started_monotonic = launch_seconds
        with patch.object(reopen.time, 'monotonic', return_value=connected_seconds), \
             patch.object(reopen.time, 'time', return_value=1791562871342 / 1000):
            self.assertEqual(diagnostic.interaction_deadline(1802, {'pid': PID}), 2100)
        event = diagnostic.ctx.report['character_session_budgets'][0]
        self.assertEqual(event['deadline_utc_ms'], 1791564051426)
        self.assertEqual(old['deadline_utc_ms'] - event['deadline_utc_ms'], 2475)
        self.assertEqual(event['save_request_deadline_utc_ms'], 1791563871426)
        self.assertEqual(event['movement_deadline_utc_ms'], 1791563811426)
        self.assertGreater(event['movement_deadline_utc_ms'], event['generated_utc_ms'])
        diagnostic.ctx.event.assert_called_once()

    def test_faster_launcher_preparation_preserves_prior_deadlines_and_reserves(self):
        for preparation_seconds in (0, 20, 59.999, 60):
            old = policy.SessionBudget(SESSION, PID, preparation_seconds, 5400)
            bounded = policy.SessionBudget(SESSION, PID, preparation_seconds, 5400,
                presentation_ready=0)
            now = 1200
            with self.subTest(preparation_seconds=preparation_seconds):
                self.assertEqual(bounded.hardcap, old.hardcap)
                self.assertEqual(bounded.connected(proof(), now, UTC_START + 1200000),
                                 old.connected(proof(), now, UTC_START + 1200000))

    def test_long_preparation_shortens_guest_bound_and_retains_operation_reserve(self):
        for operation_end, expected_end in ((5400, 2100), (2100, 1980)):
            budget = policy.SessionBudget(SESSION, PID, 120.001, operation_end,
                presentation_ready=0)
            with self.subTest(operation_end=operation_end):
                self.assertEqual(budget.hardcap, expected_end)
                event = budget.connected(proof(), 1500, UTC_START + 1500000)
                self.assertEqual(event['deadline_utc_ms'], UTC_START + expected_end * 1000)
                self.assertEqual(event['deadline_utc_ms'] - event['save_request_deadline_utc_ms'], 180000)
                self.assertEqual(event['save_request_deadline_utc_ms'] - event['movement_deadline_utc_ms'], 60000)
                self.assertLessEqual(budget.deadline, 120.001 + policy.LAUNCHER_BUDGET_SECONDS)
                self.assertLessEqual(budget.deadline, operation_end - policy.OPERATION_RESERVE_SECONDS)

    def test_invalid_or_future_presentation_clock_cannot_grant_reopen_budget(self):
        for presentation in (-1, False, math.nan, math.inf, 120.002):
            with self.subTest(presentation=presentation), \
                 self.assertRaisesRegex(ValueError, 'presentation clock'):
                policy.SessionBudget(SESSION, PID, 120.001, 5400,
                    presentation_ready=presentation)
        with self.assertRaisesRegex(ValueError, 'reserved launcher'):
            policy.SessionBudget(SESSION, PID, 2100, 5400, presentation_ready=0)

    def test_presentation_cap_never_grants_connection_without_neutral_and_save_reserves(self):
        for now, accepted in ((1859.999, True), (1860, False), (1860.001, False), (2100, False)):
            budget = policy.SessionBudget(SESSION, PID, 120, 5400, presentation_ready=0)
            with self.subTest(now=now):
                if accepted:
                    event = budget.connected(proof(), now, UTC_START + 1859999)
                    self.assertEqual(event['movement_deadline_utc_ms'] - event['generated_utc_ms'], 1)
                    self.assertEqual(event['deadline_utc_ms'], UTC_START + 2100000)
                else:
                    with self.assertRaises(ValueError):
                        budget.connected(proof(), now, UTC_START + int(now * 1000))
                    self.assertEqual(budget.revision, 0)
                    self.assertEqual(budget.events, [])

    def test_owned_presentation_clock_is_recorded_before_display_event_and_launcher_preparation(self):
        class StopBeforeLaunch(Exception):
            pass
        diagnostic = interactive.ClientInteractiveDiagnostic.__new__(interactive.ClientInteractiveDiagnostic)
        diagnostic.args = SimpleNamespace(session_id=SESSION, startup_timeout_seconds=900,
            wine='/usr/bin/wine', assets=Path('/assets'))
        diagnostic.wine_env = {'DISPLAY': ':1'}
        diagnostic.presentation_socket = Path('/presentation-socket/view.sock')
        diagnostic.initialize = Mock()
        diagnostic.start_wine = Mock()
        diagnostic.mark_wine_ready = Mock()
        diagnostic.reset_client_startup_inputs = Mock()
        diagnostic.capture = Mock()
        diagnostic.launch_client_attempt = Mock(side_effect=StopBeforeLaunch)
        diagnostic.ctx = SimpleNamespace(stage=Mock(), run=Mock(return_value={'output': ''}),
            passed=Mock(), event=Mock())
        with tempfile.TemporaryDirectory() as directory:
            diagnostic.finish_path = Path(directory) / 'finish.json'
            with patch.object(interactive, 'XObserver'), \
                 patch.object(interactive.base, 'validate_runtime_probe', return_value={}), \
                 patch.object(interactive.time, 'monotonic', return_value=10.25), \
                 self.assertRaises(StopBeforeLaunch):
                diagnostic.ctx.event.side_effect = lambda name, **fields: self.assertEqual(
                    diagnostic.presentation_ready_monotonic, 10.25)
                diagnostic.execute()
        diagnostic.ctx.event.assert_called_once_with('client_display_ready', session_id=SESSION,
            width=800, height=600, socket_path='/presentation-socket/view.sock', startup_timeout_seconds=900)
        diagnostic.launch_client_attempt.assert_called_once_with()

    def test_reopen_hook_refuses_missing_owned_presentation_clock(self):
        diagnostic = reopen.CharacterReopenDiagnostic.__new__(reopen.CharacterReopenDiagnostic)
        diagnostic.args = SimpleNamespace(session_id=SESSION)
        diagnostic.ctx = SimpleNamespace(deadline=5400,
            report={'character_reopen': proof()}, event=Mock())
        diagnostic.connected_announced = True
        diagnostic.launcher_started_monotonic = 0
        with patch.object(reopen.time, 'monotonic', return_value=1214), \
             patch.object(reopen.time, 'time', return_value=(UTC_START + 1214000) / 1000), \
             self.assertRaisesRegex(Exception, 'owned presentation clock'):
            diagnostic.interaction_deadline(1802, {'pid': PID})
        self.assertFalse(hasattr(diagnostic, 'session_budget'))
        diagnostic.ctx.event.assert_not_called()


if __name__ == '__main__':
    unittest.main()
