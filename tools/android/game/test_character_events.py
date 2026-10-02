"""Read-only immediate native events retain current launch and physics gates."""
import copy
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
sys.path.insert(0, str(ROOT / 'tools'))
import native_character_events as events
import local_character_server as server
import prepare_character_events_source as source

SESSION = '0123456789abcdef0123456789abcdef'
START = 1790960400000
PROGRESS = {'available': True, 'windows_pid': 44, 'main_thread_id': 55,
            'tick_completed': 1, 'unchanged_seconds': 0}


def line(sequence=1, kind='ready', utc_ms=START + 1000, **changes):
    values = dict(session=SESSION, pid=44, tid=55, sequence=sequence, kind=kind,
                  utc_ms=utc_ms, map_id=1, db_id=1, auth_id=17, name='THORHERO',
                  account='COHLOCAL', peer='127.0.0.1', port=12345 if kind == 'ready' else 0,
                  x='0.00' if kind == 'ready' else '104.47',
                  y='0.00' if kind == 'ready' else '31.96',
                  z='0.00' if kind == 'ready' else '-531.56')
    values.update(changes)
    return ('COH_CHARACTER_EVENT_V1 session={session} pid={pid} tid={tid} sequence={sequence} '
            'kind={kind} utc_ms={utc_ms} map_id={map_id} db_id={db_id} auth_id={auth_id} '
            'name={name} account={account} peer={peer}:{port} position=<{x},{y},{z}>\n').format(**values)


def parse(console, **changes):
    kwargs = dict(session=SESSION, progress=PROGRESS, launch_utc_ms=START,
                  now_utc_ms=START + 120000, db_id=1, auth_id=17)
    kwargs.update(changes)
    return events.records(console, **kwargs)


class NativeCharacterEventObserverTests(unittest.TestCase):
    def test_immediate_ready_needs_no_delayed_sorted_log(self):
        ready = events.latest_ready(parse('ordinary native output\n' + line()))
        self.assertTrue(ready['loaded_world_assets'])
        self.assertEqual(ready['utc_ms'], START + 1000)
        self.assertEqual(ready['session_id'], SESSION)
        self.assertEqual(ready['log_route'], 'immediate_owned_mapserver_console')
        self.assertIsNone(server.ready_record([]))

    def test_ground_keeps_two_real_samples_and_25_to_90_second_window(self):
        ready = line()
        first = line(2, 'position', START + 30000)
        delivery = {'sent_utc_ms': START + 2000}
        for elapsed, expected in ((24999, False), (25000, True), (30000, True), (90000, True), (90001, False)):
            with self.subTest(elapsed=elapsed):
                values = parse(ready + first + line(3, 'position', START + 30000 + elapsed),
                               now_utc_ms=START + 180000)
                proof = server.stable_ground_evidence([], delivery, START + 180000,
                    positions=events.positions_after_ready(values))
                self.assertEqual(proof is not None, expected)
                if proof is not None:
                    self.assertEqual(proof['elapsed_ms'], elapsed)
                    self.assertFalse(proof['full_collision_geometry_verified'])

    def test_partial_duplicate_regressed_and_skipped_events_are_not_fresh(self):
        self.assertEqual(parse(line().rstrip('\n')), [])
        self.assertEqual(len(parse(line() + line(2, 'position').rstrip('\n'))), 1)
        for bad in (line() + line(), line() + line(3, 'position'),
                    line() + line(2, 'position', START), line(sequence=0),
                    line(sequence=4294967296), 'prefix ' + line()):
            with self.subTest(bad=bad), self.assertRaises(server.base.DiagnosticError):
                parse(bad)

    def test_foreign_native_identity_session_peer_and_clock_fail_closed(self):
        for changes in ({'session': 'f'*32}, {'pid': 45}, {'tid': 56}, {'db_id': 2},
                        {'auth_id': 18}, {'name': 'OTHER'}, {'account': 'OTHER'},
                        {'map_id': 2}, {'peer': '10.0.0.1'}, {'port': 0}, {'port': 65536},
                        {'utc_ms': START - 1001}, {'utc_ms': START + 121001}, {'x': 'nan'}):
            with self.subTest(changes=changes), self.assertRaises(server.base.DiagnosticError):
                parse(line(**changes))

    def test_reconnect_resets_position_window_and_position_without_ready_cannot_verify(self):
        before_ready = parse(line(1, 'position', START + 30000) + line(2, 'position', START + 60000))
        self.assertEqual(events.positions_after_ready(before_ready), [])
        values = parse(line() + line(2, 'position', START + 30000)
                       + line(3, 'position', START + 60000) + line(4, 'ready', START + 70000)
                       + line(5, 'position', START + 90000))
        positions = events.positions_after_ready(values)
        self.assertEqual(len(positions), 1)
        self.assertIsNone(server.stable_ground_evidence([], {'sent_utc_ms': START + 2000},
            START + 120000, positions=positions))

    def test_falling_moving_stale_and_pre_command_samples_still_fail(self):
        first = line(2, 'position', START + 30000)
        for extra, now, delivery in (({'y': '-2000.00'}, START + 120000, START + 2000),
                                    ({'y': '33.00'}, START + 120000, START + 2000),
                                    ({'x': '107.00'}, START + 120000, START + 2000),
                                    ({}, START + 240001, START + 2000),
                                    ({}, START + 120000, START + 30001)):
            with self.subTest(extra=extra, now=now, delivery=delivery):
                values = parse(line() + first + line(3, 'position', START + 60000, **extra),
                               now_utc_ms=now)
                self.assertIsNone(server.stable_ground_evidence([], {'sent_utc_ms': delivery}, now,
                    positions=events.positions_after_ready(values)))

    def test_native_observer_requires_owned_live_progress_and_does_not_fallback_to_sorted_logs(self):
        context = SimpleNamespace(report={})
        owner = SimpleNamespace(root=ROOT, ctx=context, args=SimpleNamespace(session_id=SESSION))
        value = server.LocalCharacterReopenServer(owner)
        value.map_package = {'inputs': {'mapserver_progress': {'events_contract': events.CONTRACT}}}
        value.auth_id = 17
        value.map_launch_utc_ms = START
        value.creation_report.update(character_id=1, immediate_native_events={'enabled': True})
        value.map_process = SimpleNamespace(process=SimpleNamespace(poll=lambda: None), text=lambda: line())
        value.sample_progress = Mock(return_value=PROGRESS)
        value.current_logs = Mock(side_effect=AssertionError('sorted logger cannot be readiness input'))
        with patch.object(server.time, 'time', return_value=(START + 120000)/1000):
            self.assertTrue(value.native_ready_record()['loaded_world_assets'])
            self.assertIsNone(value.native_ground_evidence({'sent_utc_ms': START + 2000}))
            value.sample_progress.return_value = dict(PROGRESS, tick_completed=0)
            self.assertIsNone(value.native_ready_record())
            value.sample_progress.return_value = PROGRESS
            value.map_process.process.poll = lambda: 0
            with self.assertRaises(server.base.DiagnosticError): value.native_ready_record()
        value.current_logs.assert_not_called()

    def test_contract_is_exact_and_bound_to_source_receipt(self):
        receipt = source.expected_events_receipt()
        self.assertEqual(receipt['events_contract'], events.CONTRACT)
        self.assertEqual(receipt['progress_contract'], receipt['progress_build_input']['progress_contract'])
        for changes in ({'format': 2}, {'writer': 'helper'}, {'changes_native_game_state': True}):
            with self.subTest(changes=changes), self.assertRaises(server.base.DiagnosticError):
                events.validate_contract(dict(events.CONTRACT, **changes))


@unittest.skipUnless(os.name == 'nt', 'real native flushed event fixture requires Windows')
class NativeCharacterEventsWindowsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('cl'):
            raise RuntimeError('native event contracts require initialized x86 MSVC')
        cls.build = tempfile.TemporaryDirectory(prefix='coh-character-events-native-')
        directory = Path(cls.build.name)
        cls.binary = directory / 'character-events-contract.exe'
        overlay = ROOT / 'database/character-events/overlay/MapServer/src/svr'
        subprocess.run(['cl', '/nologo', '/W4', '/WX', '/O2', '/MT', f'/I{overlay}',
            str(overlay / 'wine_character_events.c'),
            str(ROOT / 'database/character-events/tests/events_contract.c'),
            f'/Fe:{cls.binary}'], cwd=directory, check=True)

    @classmethod
    def tearDownClass(cls): cls.build.cleanup()

    def start(self, session):
        environment = os.environ.copy()
        environment.pop(events.ENVIRONMENT, None)
        if session is not None: environment[events.ENVIRONMENT] = session
        process = subprocess.Popen([str(self.binary)], env=environment, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        self.addCleanup(self.close, process)
        lines = queue.Queue()
        def read():
            for value in process.stdout:
                if value.strip(): lines.put(value.rstrip('\n'))
        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        process.lines = lines
        process.reader = reader
        return process, self.receive(process)

    def close(self, process):
        if process.poll() is None: process.terminate()
        process.wait(timeout=10)
        process.reader.join(timeout=10)
        for stream in (process.stdin, process.stdout, process.stderr): stream.close()

    def receive(self, process):
        try: return process.lines.get(timeout=5)
        except queue.Empty as exc: raise AssertionError('native event was not flushed while producer remains live') from exc

    def send(self, process, command):
        process.stdin.write(command + '\n')
        process.stdin.flush()
        return self.receive(process)

    def test_real_ready_and_position_are_immediately_flushed_without_fixture_output(self):
        process, status = self.start(SESSION)
        fields = status.split()
        self.assertEqual(fields[:3], ['STATUS', '1', '0'])
        console = self.send(process, 'ready') + '\n' + self.send(process, 'position') + '\n'
        now = int(__import__('time').time()*1000)
        values = parse(console, progress=dict(PROGRESS, windows_pid=int(fields[3]), main_thread_id=int(fields[4])),
                       launch_utc_ms=now - 10000, now_utc_ms=now)
        self.assertEqual([value['kind'] for value in values], ['ready', 'position'])
        self.assertIsNone(process.poll())
        self.assertEqual(self.send(process, 'foreign'), 'FILTERED')
        self.assertEqual(self.send(process, 'init-again'), 'REINIT -1')

    def test_disabled_and_invalid_tokens_emit_no_native_proof(self):
        for token, expected in ((None, 0), ('', -1), ('f'*31, -1), ('F'*32, -1), ('f'*33, -1)):
            with self.subTest(token=token):
                process, status = self.start(token)
                self.assertEqual(status.split()[:2], ['STATUS', str(expected)])
                self.assertEqual(self.send(process, 'disabled'), 'DISABLED')


if __name__ == '__main__':
    if '--require-windows' in sys.argv:
        sys.argv.remove('--require-windows')
        if os.name != 'nt' or not shutil.which('cl'):
            raise SystemExit('native event contracts require initialized x86 MSVC Windows')
    unittest.main(verbosity=2)
