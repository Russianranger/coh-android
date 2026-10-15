"""Replay the Thor .22 deadline regression through the unchanged Java consumer.

The real guest producer supplies every event.  The host harness compiles the
Android-free ClientSessionBudget class, so acceptance is independent of the
Python producer's implementation and its unit tests.
"""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
JAVA_SOURCE = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientSessionBudget.java'
PRODUCER_SOURCE = ROOT / 'android/guest/character_session_budget.py'
SPEC = importlib.util.spec_from_file_location('coh_session_repair_budget', PRODUCER_SOURCE)
PRODUCER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PRODUCER)

# Complete outer ZIP coh-atlas-gameplay-20261009-162841.zip, SHA-256
# 1be60a5dec87b1d09fa5f8f74d2eff2ca2e95a73638ee199b97a944e2852d1b6.
# Millisecond UTC values match the captured JSON events; Java receives this
# event only after delivery, using its independent Android uptime clock.
SESSION = 'cf758df7c9ae4751879ec0d17433eaa2'
DISPLAY_UTC_MS = 1791561951426
LAUNCHER_UTC_MS = 1791562013901
CONNECTED_UTC_MS = 1791562871342
CONNECTED_UPTIME_MS = 35047709
DISPLAY_MONOTONIC = 34127.792810913
PROOF = {
    'session_id': SESSION, 'client_pid': 632, 'character_id': 1,
    'before_character_id': 1, 'baseline_character_id': 1, 'map_id': 1,
    'name': 'THORHERO', 'account': 'COHLOCAL', 'connected_on_atlas': True,
    'reopen_verified': True, 'existing_character_verified': True,
    'preserved_existing_identity': True, 'native_client_ready_observed': True,
}

HARNESS = r'''
package io.github.russianranger.cohclientinteractive;
import java.util.*;

public final class SessionRepairHost {
    public static void main(String[] args) {
        String session = "cf758df7c9ae4751879ec0d17433eaa2";
        Map<String,Object> event = new LinkedHashMap<>();
        event.put("type", "character_session_budget"); event.put("format", 1);
        event.put("session_id", session); event.put("client_pid", 632);
        event.put("character_id", 1); event.put("name", "THORHERO");
        event.put("account", "COHLOCAL"); event.put("map_id", 1);
        event.put("native_client_ready_observed", true);
        event.put("reopen_verified", true); event.put("revision", 1);
        event.put("phase", "connected");
        event.put("generated_utc_ms", Long.parseLong(args[0]));
        event.put("deadline_utc_ms", Long.parseLong(args[1]));
        event.put("save_request_deadline_utc_ms", Long.parseLong(args[2]));
        event.put("movement_deadline_utc_ms", Long.parseLong(args[3]));
        long wallNow = Long.parseLong(args[4]), upNow = Long.parseLong(args[5]);
        long capUp = Long.parseLong(args[6]), probeUp = Long.parseLong(args[7]);
        ClientSessionBudget budget = new ClientSessionBudget();
        boolean accepted = budget.apply(event, session, 632, true, false, 0,
                wallNow, upNow, capUp);
        System.out.println(accepted + "," + budget.revision() + ","
                + budget.deadline() + "," + budget.saveDeadline() + ","
                + budget.movementDeadline() + "," + budget.canMove(upNow) + ","
                + budget.canSave(upNow) + "," + budget.canMove(probeUp) + ","
                + budget.canSave(probeUp));
    }
}
'''


class ClientSessionRepairJavaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='coh-session-repair-java-')
        cls.addClassCleanup(cls.temp.cleanup)
        harness = Path(cls.temp.name) / 'SessionRepairHost.java'
        harness.write_text(HARNESS, encoding='utf-8')
        subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main',
            '--release', '8', '-d', cls.temp.name, str(JAVA_SOURCE), str(harness)],
            check=True, capture_output=True, text=True, timeout=60)

    def produce(self, preparation_ms=62475, *, bounded=True):
        launcher = DISPLAY_MONOTONIC + preparation_ms / 1000
        now = DISPLAY_MONOTONIC + (CONNECTED_UTC_MS - DISPLAY_UTC_MS) / 1000
        options = {'presentation_ready': DISPLAY_MONOTONIC} if bounded else {}
        budget = PRODUCER.SessionBudget(SESSION, 632, launcher,
            DISPLAY_MONOTONIC + 5400, **options)
        return budget.connected(dict(PROOF), now, CONNECTED_UTC_MS)

    def consume(self, event, *, delay_ms=0, probe_up=None, uptime_offset=0):
        wall_now = CONNECTED_UTC_MS + delay_ms
        up_now = CONNECTED_UPTIME_MS + delay_ms + uptime_offset
        cap_utc = DISPLAY_UTC_MS + 2100000
        cap_up = up_now + cap_utc - wall_now
        args = [event[key] for key in ('generated_utc_ms', 'deadline_utc_ms',
            'save_request_deadline_utc_ms', 'movement_deadline_utc_ms')]
        args += [wall_now, up_now, cap_up, up_now if probe_up is None else probe_up]
        completed = subprocess.run(['java', '-cp', self.temp.name,
            'io.github.russianranger.cohclientinteractive.SessionRepairHost',
            *map(str, args)], check=True, capture_output=True, text=True, timeout=10)
        values = completed.stdout.strip().split(',')
        self.assertEqual(9, len(values), completed.stdout + completed.stderr)
        return {'accepted': values[0] == 'true', 'revision': int(values[1]),
            'deadline': int(values[2]), 'save_deadline': int(values[3]),
            'movement_deadline': int(values[4]), 'can_move_now': values[5] == 'true',
            'can_save_now': values[6] == 'true', 'can_move_probe': values[7] == 'true',
            'can_save_probe': values[8] == 'true'}

    def assert_current_inputs(self, result):
        self.assertTrue(result['accepted'])
        self.assertEqual(1, result['revision'])
        self.assertTrue(result['can_move_now'])
        self.assertTrue(result['can_save_now'])

    def test_captured_01322_budget_is_rejected_without_presentation_bound(self):
        legacy = self.produce(bounded=False)
        self.assertEqual(62475, LAUNCHER_UTC_MS - DISPLAY_UTC_MS)
        self.assertEqual(LAUNCHER_UTC_MS + 2040000, legacy['deadline_utc_ms'])
        self.assertEqual(1791564053901, legacy['deadline_utc_ms'])
        self.assertEqual(2475, legacy['deadline_utc_ms'] - (DISPLAY_UTC_MS + 2100000))
        result = self.consume(legacy)
        self.assertFalse(result['accepted'])
        self.assertEqual(0, result['revision'])
        self.assertFalse(result['can_move_now'])
        self.assertFalse(result['can_save_now'])
        self.assertEqual(0, result['deadline'])

    def test_corrected_capture_opens_movement_and_save_inside_original_cap(self):
        event = self.produce()
        self.assertEqual(DISPLAY_UTC_MS + 2100000, event['deadline_utc_ms'])
        self.assertEqual(1791564051426, event['deadline_utc_ms'])
        result = self.consume(event)
        self.assert_current_inputs(result)
        self.assertEqual(CONNECTED_UPTIME_MS + event['deadline_utc_ms'] -
            CONNECTED_UTC_MS, result['deadline'])

    def test_short_gpu_preparation_retains_launcher_cap(self):
        for preparation_ms in (0, 1000, 45000, 59999, 60000):
            with self.subTest(preparation_ms=preparation_ms):
                event = self.produce(preparation_ms)
                self.assertEqual(DISPLAY_UTC_MS + preparation_ms + 2040000,
                    event['deadline_utc_ms'])
                self.assert_current_inputs(self.consume(event))

    def test_long_gpu_preparation_uses_earlier_presentation_cap(self):
        for preparation_ms in (60001, 62475, 90000, 120000, 600000):
            with self.subTest(preparation_ms=preparation_ms):
                event = self.produce(preparation_ms)
                self.assertEqual(DISPLAY_UTC_MS + 2100000, event['deadline_utc_ms'])
                self.assertLessEqual(event['deadline_utc_ms'],
                    DISPLAY_UTC_MS + preparation_ms + 2040000)
                self.assert_current_inputs(self.consume(event))

    def test_event_transport_delay_keeps_independent_uptime_mapping(self):
        event = self.produce()
        for delay_ms, uptime_offset in ((0, 0), (250, 0), (2475, 0),
                (60000, 700000), (119999, 3210000)):
            with self.subTest(delay_ms=delay_ms, uptime_offset=uptime_offset):
                result = self.consume(event, delay_ms=delay_ms,
                    uptime_offset=uptime_offset)
                self.assert_current_inputs(result)
                self.assertEqual(CONNECTED_UPTIME_MS + uptime_offset +
                    event['deadline_utc_ms'] - CONNECTED_UTC_MS, result['deadline'])

    def test_neutral_and_save_reserves_and_exact_input_expiry(self):
        event = self.produce()
        self.assertEqual(60000, event['save_request_deadline_utc_ms'] -
            event['movement_deadline_utc_ms'])
        self.assertEqual(180000, event['deadline_utc_ms'] -
            event['save_request_deadline_utc_ms'])
        mapped = self.consume(event)
        self.assertEqual(60000, mapped['save_deadline'] - mapped['movement_deadline'])
        self.assertEqual(180000, mapped['deadline'] - mapped['save_deadline'])
        for probe_up, movement, save in (
                (mapped['movement_deadline'] - 1, True, True),
                (mapped['movement_deadline'], False, True),
                (mapped['save_deadline'] - 1, False, True),
                (mapped['save_deadline'], False, False),
                (mapped['deadline'], False, False)):
            with self.subTest(probe_up=probe_up):
                result = self.consume(event, probe_up=probe_up)
                self.assertTrue(result['accepted'])
                self.assertEqual(movement, result['can_move_probe'])
                self.assertEqual(save, result['can_save_probe'])

    def test_expired_or_stale_events_do_not_authorize_input(self):
        event = self.produce()
        for delay_ms in (120001, event['deadline_utc_ms'] - CONNECTED_UTC_MS):
            with self.subTest(delay_ms=delay_ms):
                result = self.consume(event, delay_ms=delay_ms)
                self.assertFalse(result['accepted'])
                self.assertEqual(0, result['revision'])
                self.assertFalse(result['can_move_now'])
                self.assertFalse(result['can_save_now'])


if __name__ == '__main__':
    unittest.main()
