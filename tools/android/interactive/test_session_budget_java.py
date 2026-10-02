"""Compile the Android-free budget helper and exercise independent protocol cases."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientSessionBudget.java'
HARNESS = r'''
package io.github.russianranger.cohclientinteractive;
import java.time.Instant;
import java.util.*;

public final class SessionBudgetHost {
    static final String SESSION = "b415255f972440f3ab7b4a6e42263682";
    static final long PID = 672;
    static final long LAUNCHER = Instant.parse("2026-10-02T12:24:40Z").toEpochMilli();
    static final long MENU = Instant.parse("2026-10-02T12:34:42.897Z").toEpochMilli();
    static final long CONNECTED = Instant.parse("2026-10-02T12:44:54.139Z").toEpochMilli();
    static final long STUCK = Instant.parse("2026-10-02T12:46:05.077Z").toEpochMilli();
    static final long GROUND = Instant.parse("2026-10-02T12:49:01.595Z").toEpochMilli();
    static final long CUP = 280660144L, GUP = 280907600L;
    static void check(boolean condition, String detail) {
        if (!condition) throw new AssertionError(detail);
    }
    static Map<String,Object> event(int revision, long generated, long end) {
        Map<String,Object> value = new LinkedHashMap<>();
        value.put("type", "character_session_budget"); value.put("format", 1);
        value.put("session_id", SESSION); value.put("client_pid", PID);
        value.put("character_id", 1); value.put("name", "THORHERO");
        value.put("account", "COHLOCAL"); value.put("map_id", 1);
        value.put("native_client_ready_observed", true); value.put("reopen_verified", true);
        value.put("revision", revision); value.put("phase", revision == 1 ? "connected" : "grounded");
        value.put("generated_utc_ms", generated); value.put("deadline_utc_ms", end);
        value.put("save_request_deadline_utc_ms", revision == 1 ? 0L : end - 180000);
        value.put("movement_deadline_utc_ms", revision == 1 ? 0L : end - 240000);
        if (revision == 2) {
            value.put("ordinary_stuck_observed", true); value.put("stable_ground_verified", true);
        }
        return value;
    }
    static boolean apply(ClientSessionBudget budget, Map<String,Object> value, long wall, long up, long cap) {
        return budget.apply(value, SESSION, PID, true, true, STUCK, wall, up, cap);
    }
    static ClientSessionBudget seeded() {
        ClientSessionBudget budget = new ClientSessionBudget();
        check(apply(budget, event(1, CONNECTED, CONNECTED + 1200000), CONNECTED, CUP, CUP + 3600000), "seed connection");
        return budget;
    }
    static void physicalTimeline() {
        ClientSessionBudget budget = new ClientSessionBudget();
        check(budget.revision() == 0 && "menu".equals(budget.phase()), "initial menu revision");
        check(!budget.canMove(CUP) && !budget.canSave(CUP), "menu cannot authorize gameplay/save");
        long actualEnd = Math.min(CONNECTED + 1200000, LAUNCHER + 2040000);
        long shellCap = CUP + LAUNCHER + 2100000 - CONNECTED;
        check(apply(budget, event(1, CONNECTED, actualEnd), CONNECTED, CUP, shellCap), "current connection accepted within actual launcher cap");
        check(budget.revision() == 1 && "connected".equals(budget.phase()), "one-way connected phase");
        check(budget.deadline() == CUP + actualEnd - CONNECTED, "connection allowance is capped at actual launcher plus34min");
        check(actualEnd > MENU + 1200000, "regression timeline previously exhausted menu budget");
        check(!budget.canMove(CUP) && !budget.canSave(CUP), "connection alone cannot bypass ground proof");
        check(apply(budget, event(2, GROUND, STUCK + 600000), GROUND, GUP, GUP + 3600000), "ground phase accepted");
        check(budget.revision() == 2 && "grounded".equals(budget.phase()), "one-way grounded phase");
        check(budget.movementDeadline() == GUP + STUCK + 360000 - GROUND, "movement ends at recovery plus six minutes");
        check(budget.saveDeadline() == GUP + STUCK + 420000 - GROUND, "save request ends at recovery plus seven minutes");
        check(budget.deadline() == GUP + STUCK + 600000 - GROUND, "producer ends at recovery plus ten minutes");
        check(budget.canMove(budget.movementDeadline() - 1), "last movement millisecond");
        check(!budget.canMove(budget.movementDeadline()), "movement deadline equality excludes movement");
        check(budget.canSave(budget.saveDeadline() - 1), "last save-request millisecond");
        check(!budget.canSave(budget.saveDeadline()), "save deadline equality excludes save request");
        check(!budget.canSave(budget.deadline()) && !budget.canMove(budget.deadline()), "end excludes both inputs");
    }
    static void cappedTimeline() {
        ClientSessionBudget budget = seeded();
        long end = GROUND + 300000, cap = GUP + 300000;
        check(apply(budget, event(2, GROUND, end), GROUND, GUP, cap), "grounded event exactly capped accepted");
        check(budget.deadline() == cap, "UTC end mapped to independent uptime cap");
        check(budget.saveDeadline() == cap - 180000, "capped end reserves three minutes after save request");
        check(budget.movementDeadline() == cap - 240000, "capped movement reserves neutral minute before save");
        check(budget.canMove(GUP) && budget.canSave(GUP), "remaining capped opportunity exists");
    }
    static void duplicates() {
        ClientSessionBudget budget = seeded();
        long initial = budget.deadline();
        check(!apply(budget, event(1, CONNECTED + 60000, CONNECTED + 1260000), CONNECTED + 60000, CUP + 60000, CUP + 3600000), "duplicate connected event cannot renew");
        check(initial == budget.deadline() && budget.revision() == 1, "rejected duplicate leaves state unchanged");
        check(apply(budget, event(2, GROUND, STUCK + 600000), GROUND, GUP, GUP + 3600000), "first grounded event");
        long end = budget.deadline(), move = budget.movementDeadline(), save = budget.saveDeadline();
        check(!apply(budget, event(2, GROUND + 1000, STUCK + 600000), GROUND + 1000, GUP + 1000, GUP + 3600000), "duplicate grounded event cannot renew");
        check(!apply(budget, event(1, GROUND, GROUND + 1200000), GROUND, GUP, GUP + 3600000), "reordered connection after ground rejected");
        check(budget.revision() == 2 && end == budget.deadline() && move == budget.movementDeadline() && save == budget.saveDeadline(), "reordered duplicates do not change deadlines");
    }
    public static void main(String[] args) {
        String name = args[0];
        if ("physical_timeline".equals(name)) { physicalTimeline(); return; }
        if ("capped_timeline".equals(name)) { cappedTimeline(); return; }
        if ("one_way_duplicates".equals(name)) { duplicates(); return; }
        boolean groundCase = name.startsWith("ground_");
        ClientSessionBudget budget = groundCase ? seeded() : new ClientSessionBudget();
        long wall = groundCase ? GROUND : CONNECTED, up = groundCase ? GUP : CUP;
        long cap = up + 3600000, relocation = STUCK, pid = PID;
        String session = SESSION; boolean connected = true, grounded = true, expected = false;
        Map<String,Object> value = event(groundCase ? 2 : 1, wall, groundCase ? STUCK + 600000 : wall + 1200000);
        switch(name) {
            case "connected_valid": expected = true; break;
            case "ground_valid": expected = true; break;
            case "null_event": value = null; break;
            case "null_session": session = null; break;
            case "malformed_session": session = "bad-session"; break;
            case "wrong_type": value.put("type", "character_relocated"); break;
            case "wrong_session": value.put("session_id", "0123456789abcdef0123456789abcdef"); break;
            case "wrong_pid": value.put("client_pid", PID + 1); break;
            case "zero_pid": pid = 0; break;
            case "negative_pid": pid = -1; break;
            case "wrong_character": value.put("character_id", 2); break;
            case "wrong_name": value.put("name", "OTHERHERO"); break;
            case "wrong_account": value.put("account", "OTHER"); break;
            case "wrong_map": value.put("map_id", 2); break;
            case "not_connected": connected = false; break;
            case "missing_native_ready": value.remove("native_client_ready_observed"); break;
            case "false_native_ready": value.put("native_client_ready_observed", false); break;
            case "string_native_ready": value.put("native_client_ready_observed", "true"); break;
            case "missing_reopen_proof": value.remove("reopen_verified"); break;
            case "false_reopen_proof": value.put("reopen_verified", false); break;
            case "string_reopen_proof": value.put("reopen_verified", "true"); break;
            case "format_string": value.put("format", "1"); break;
            case "format_double": value.put("format", 1.0); break;
            case "pid_boolean": value.put("client_pid", true); break;
            case "character_string": value.put("character_id", "1"); break;
            case "map_double": value.put("map_id", 1.0); break;
            case "revision_double": value.put("revision", 1.0); break;
            case "generated_string": value.put("generated_utc_ms", Long.toString(wall)); break;
            case "deadline_double": value.put("deadline_utc_ms", (double)(wall + 1200000)); break;
            case "revision_zero": value.put("revision", 0); break;
            case "revision_two_before_one": value.put("revision", 2); break;
            case "revision_three": value.put("revision", 3); break;
            case "wrong_phase": value.put("phase", "grounded"); break;
            case "connected_save_nonzero": value.put("save_request_deadline_utc_ms", wall + 60000); break;
            case "connected_movement_nonzero": value.put("movement_deadline_utc_ms", wall + 60000); break;
            case "utc_to_small_uptime": up = 17; cap = 1200017; expected = true; break;
            case "utc_to_large_uptime": up = 900000000000L; cap = up + 1200000; expected = true; break;
            case "future_tolerance_boundary": value.put("generated_utc_ms", wall + 1000); expected = true; break;
            case "future_tolerance_exceeded": value.put("generated_utc_ms", wall + 1001); break;
            case "freshness_boundary": value.put("generated_utc_ms", wall - 120000); value.put("deadline_utc_ms", wall + 1080000); expected = true; break;
            case "stale_event": value.put("generated_utc_ms", wall - 120001); value.put("deadline_utc_ms", wall + 1079999); break;
            case "zero_generated": value.put("generated_utc_ms", 0L); break;
            case "zero_wall": wall = 0; break;
            case "negative_wall": wall = -1; break;
            case "negative_uptime": up = -1; break;
            case "end_equal_now": value.put("deadline_utc_ms", wall); break;
            case "end_before_now": value.put("deadline_utc_ms", wall - 1); break;
            case "over_twenty_minutes": value.put("deadline_utc_ms", wall + 1200001); break;
            case "exact_uptime_cap": cap = up + 1200000; expected = true; break;
            case "exceeds_uptime_cap": cap = up + 1199999; break;
            case "cap_equal_uptime": cap = up; break;
            case "cap_before_uptime": cap = up - 1; break;
            case "near_max_wall": wall = Long.MAX_VALUE - 500; value.put("generated_utc_ms", wall); value.put("deadline_utc_ms", wall + 100); break;
            case "near_max_uptime": up = Long.MAX_VALUE - 500; cap = Long.MAX_VALUE; value.put("deadline_utc_ms", wall + 100); break;
            case "max_generated": value.put("generated_utc_ms", Long.MAX_VALUE); break;
            case "max_deadline": value.put("deadline_utc_ms", Long.MAX_VALUE); break;
            case "ground_expired_connected_phase": up = budget.deadline(); cap = up + 3600000; break;
            case "ground_after_connected_phase": up = budget.deadline() + 1; cap = up + 3600000; break;
            case "ground_missing_ground_proof": value.remove("stable_ground_verified"); break;
            case "ground_false_ground_proof": value.put("stable_ground_verified", false); break;
            case "ground_string_ground_proof": value.put("stable_ground_verified", "true"); break;
            case "ground_missing_stuck_proof": value.remove("ordinary_stuck_observed"); break;
            case "ground_false_stuck_proof": value.put("ordinary_stuck_observed", false); break;
            case "ground_string_stuck_proof": value.put("ordinary_stuck_observed", "true"); break;
            case "ground_not_observed": grounded = false; break;
            case "ground_wrong_phase": value.put("phase", "connected"); break;
            case "ground_zero_relocation": relocation = 0; break;
            case "ground_future_relocation": relocation = wall + 120000; break;
            case "ground_max_relocation": relocation = Long.MAX_VALUE; break;
            case "ground_stale_event": value.put("generated_utc_ms", wall - 120001); break;
            case "ground_save_equal_now": value.put("save_request_deadline_utc_ms", wall); break;
            case "ground_save_before_now": value.put("save_request_deadline_utc_ms", wall - 1); break;
            case "ground_move_equal_generated": value.put("movement_deadline_utc_ms", wall); break;
            case "ground_move_before_generated": value.put("movement_deadline_utc_ms", wall - 1); break;
            case "ground_neutral_wait_too_short": value.put("movement_deadline_utc_ms", STUCK + 360001); break;
            case "ground_reserve_too_short": value.put("deadline_utc_ms", STUCK + 599999); break;
            case "ground_save_window_exceeded": value.put("save_request_deadline_utc_ms", STUCK + 420001); value.put("movement_deadline_utc_ms", STUCK + 360001); value.put("deadline_utc_ms", STUCK + 600001); break;
            case "ground_recovery_window_exceeded": value.put("deadline_utc_ms", STUCK + 600001); break;
            case "ground_capped_exact": value = event(2, wall, wall + 300000); cap = up + 300000; expected = true; break;
            case "ground_cap_exceeded": value = event(2, wall, wall + 300000); cap = up + 299999; break;
            case "ground_capped_no_movement_room": value = event(2, wall, wall + 240000); cap = up + 240000; break;
            case "ground_capped_minimum_room": value = event(2, wall, wall + 240001); cap = up + 240001; expected = true; break;
            case "ground_save_string": value.put("save_request_deadline_utc_ms", Long.toString(STUCK + 420000)); break;
            case "ground_move_double": value.put("movement_deadline_utc_ms", (double)(STUCK + 360000)); break;
            case "ground_max_save": value.put("save_request_deadline_utc_ms", Long.MAX_VALUE); break;
            case "ground_max_movement": value.put("movement_deadline_utc_ms", Long.MAX_VALUE); break;
            default: throw new AssertionError("Unknown scenario: " + name);
        }
        int beforeRevision = budget.revision(); long beforeEnd = budget.deadline();
        long beforeSave = budget.saveDeadline(), beforeMove = budget.movementDeadline();
        boolean accepted = budget.apply(value, session, pid, connected, grounded, relocation, wall, up, cap);
        check(accepted == expected, name + " expected=" + expected + " actual=" + accepted);
        if (!accepted) {
            check(beforeRevision == budget.revision() && beforeEnd == budget.deadline()
                && beforeSave == budget.saveDeadline() && beforeMove == budget.movementDeadline(), name + " rejected event mutated budget");
        } else {
            long utcEnd = ((Number)value.get("deadline_utc_ms")).longValue();
            check(budget.deadline() == up + utcEnd - wall, name + " UTC/uptime conversion");
            check(budget.deadline() <= cap, name + " independent uptime cap");
            if (groundCase) {
                check(budget.saveDeadline() == budget.deadline() - 180000, name + " capped producer reserve");
                check(budget.movementDeadline() == budget.saveDeadline() - 60000, name + " neutral wait reserve");
            }
        }
    }
}
'''

CASES = {
    'physical_and_revision_sequences': ('physical_timeline', 'capped_timeline', 'one_way_duplicates',
                                      'connected_valid', 'ground_valid', 'revision_zero',
                                      'revision_two_before_one', 'revision_three', 'wrong_phase'),
    'current_identity_and_proofs': ('null_event', 'null_session', 'malformed_session', 'wrong_type',
        'wrong_session', 'wrong_pid', 'zero_pid', 'negative_pid', 'wrong_character', 'wrong_name',
        'wrong_account', 'wrong_map', 'not_connected', 'missing_native_ready', 'false_native_ready',
        'string_native_ready', 'missing_reopen_proof', 'false_reopen_proof', 'string_reopen_proof'),
    'integer_protocol_types': ('format_string', 'format_double', 'pid_boolean', 'character_string',
        'map_double', 'revision_double', 'generated_string', 'deadline_double',
        'connected_save_nonzero', 'connected_movement_nonzero', 'ground_save_string', 'ground_move_double'),
    'freshness_and_independent_clocks': ('utc_to_small_uptime', 'utc_to_large_uptime',
        'future_tolerance_boundary', 'future_tolerance_exceeded', 'freshness_boundary', 'stale_event',
        'zero_generated', 'zero_wall', 'negative_wall', 'negative_uptime', 'end_equal_now',
        'end_before_now', 'over_twenty_minutes', 'exact_uptime_cap', 'exceeds_uptime_cap',
        'cap_equal_uptime', 'cap_before_uptime', 'near_max_wall', 'near_max_uptime',
        'max_generated', 'max_deadline'),
    'ground_reserves_and_recovery_binding': ('ground_expired_connected_phase', 'ground_after_connected_phase', 'ground_missing_ground_proof', 'ground_false_ground_proof',
        'ground_string_ground_proof', 'ground_missing_stuck_proof', 'ground_false_stuck_proof',
        'ground_string_stuck_proof', 'ground_not_observed', 'ground_wrong_phase', 'ground_zero_relocation',
        'ground_future_relocation', 'ground_max_relocation', 'ground_stale_event', 'ground_save_equal_now',
        'ground_save_before_now', 'ground_move_equal_generated', 'ground_move_before_generated',
        'ground_neutral_wait_too_short', 'ground_reserve_too_short', 'ground_save_window_exceeded',
        'ground_recovery_window_exceeded', 'ground_capped_exact', 'ground_cap_exceeded',
        'ground_capped_no_movement_room', 'ground_capped_minimum_room', 'ground_max_save',
        'ground_max_movement'),
}


class SessionBudgetJavaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='coh-session-budget-java-')
        cls.addClassCleanup(cls.temp.cleanup)
        harness = Path(cls.temp.name) / 'SessionBudgetHost.java'
        harness.write_text(HARNESS, encoding='utf-8')
        subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                        '-d', cls.temp.name, str(SOURCE), str(harness)],
                       check=True, capture_output=True, text=True, timeout=60)

    def execute_group(self, name):
        for scenario in CASES[name]:
            with self.subTest(scenario=scenario):
                completed = subprocess.run(['java', '-cp', self.temp.name,
                    'io.github.russianranger.cohclientinteractive.SessionBudgetHost', scenario],
                    capture_output=True, text=True, timeout=10)
                self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)

    def test_physical_and_revision_sequences(self):
        self.execute_group('physical_and_revision_sequences')

    def test_current_identity_and_proofs(self):
        self.execute_group('current_identity_and_proofs')

    def test_integer_protocol_types(self):
        self.execute_group('integer_protocol_types')

    def test_freshness_and_independent_clocks(self):
        self.execute_group('freshness_and_independent_clocks')

    def test_ground_reserves_and_recovery_binding(self):
        self.execute_group('ground_reserves_and_recovery_binding')


if __name__ == '__main__':
    unittest.main()
