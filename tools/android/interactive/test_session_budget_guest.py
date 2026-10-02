"""Reopen clocks follow native phases without extending recovery/save evidence."""
from datetime import datetime, timezone
from pathlib import Path
import math
import sys
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
    value.update(ordinary_stuck_observed=True, on_atlas_safe_position=True,
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
        self.assertEqual(event['save_request_deadline_utc_ms'], 0)
        self.assertEqual(event['movement_deadline_utc_ms'], 0)

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
            with self.subTest(poll_returned=now), \
                 patch.object(reopen.time, 'monotonic', return_value=now), \
                 patch.object(reopen.time, 'time', return_value=(UTC_START + int(now * 1000)) / 1000), \
                 self.assertRaisesRegex(Exception, 'current menu deadline'):
                diagnostic.interaction_deadline(1802, {'pid': PID})
            self.assertFalse(hasattr(diagnostic, 'session_budget'))
            diagnostic.ctx.event.assert_not_called()

    def test_slow_ground_poll_cannot_revive_expired_connected_phase(self):
        for now, accepted in ((1599.999, True), (1600, False), (1600.001, False)):
            diagnostic = reopen.CharacterReopenDiagnostic.__new__(reopen.CharacterReopenDiagnostic)
            diagnostic.args = SimpleNamespace(session_id=SESSION)
            value = proof(); value['client_ready_observed_utc_ms'] = UTC_START + 400000
            diagnostic.ctx = SimpleNamespace(deadline=5400,
                report={'character_reopen': value}, event=Mock())
            diagnostic.connected_announced = True
            diagnostic.launcher_started_monotonic = 0
            with patch.object(reopen.time, 'monotonic', return_value=400), \
                 patch.object(reopen.time, 'time', return_value=(UTC_START + 400000) / 1000):
                self.assertEqual(diagnostic.interaction_deadline(1802, {'pid': PID}), 1600)
            value = recovered(1550); value['client_ready_observed_utc_ms'] = UTC_START + 400000
            diagnostic.ctx.report['character_reopen'] = value
            diagnostic.relocated_announced = True
            with self.subTest(poll_returned=now), \
                 patch.object(reopen.time, 'monotonic', return_value=now), \
                 patch.object(reopen.time, 'time', return_value=(UTC_START + int(now * 1000)) / 1000):
                if accepted:
                    self.assertEqual(diagnostic.interaction_deadline(1600, {'pid': PID}), 2040)
                else:
                    with self.assertRaisesRegex(Exception, 'current connected deadline'):
                        diagnostic.interaction_deadline(1600, {'pid': PID})
            self.assertEqual(diagnostic.session_budget.revision, 2 if accepted else 1)
            self.assertEqual(diagnostic.ctx.event.call_count, 2 if accepted else 1)


if __name__ == '__main__':
    unittest.main()
