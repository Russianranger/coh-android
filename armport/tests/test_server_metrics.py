"""Real telemetry code against synthetic procfs/progress, without Wine or compilers."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'armport/app'), str(ROOT / 'android/guest')]
import diagnostic as base
import game_map_progress as progress
import server_metrics as metrics
import armport_interactive


def stat_text(pid, start=200, user=0, system=0, threads=1):
    fields = ['0'] * 20
    fields[0] = 'S'
    for index, value in ((11, user), (12, system), (17, threads), (19, start)):
        fields[index] = str(value)
    return str(pid) + ' (name with ) parentheses) ' + ' '.join(fields)


def status_text(pid, tgid=None):
    return 'Uid:\t%d\nPid:\t%d\nTgid:\t%d\nNSpid:\t%d\n' % (
        os.getuid(), pid, tgid or pid, pid)


class MetricsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.proc = self.root / 'proc'
        self.proc.mkdir()
        own = self.proc / 'self'
        own.mkdir()
        (own / 'stat').write_text(stat_text(os.getpid(), start=100))
        (own / 'status').write_text(status_text(os.getpid()))
        self.context = SimpleNamespace(secrets=[], report={})
        self.owner = base.WineProcessOwner(self.context, self.proc)
        self.now = 10.0
        self.diagnostic = SimpleNamespace(ctx=self.context, wine_owner=self.owner,
            capture_dir=self.root, local_server=SimpleNamespace(maps={}))
        self.sampler = metrics.ServerMetrics(self.diagnostic, clock=lambda: self.now, wall=lambda: 1000)
        self.addCleanup(self.sampler.close)

    def process(self, pid=9001, start=200, user=20, system=10, role=b'DbServer.exe', count=1, token=True):
        path = self.proc / str(pid)
        path.mkdir(exist_ok=True)
        (path / 'stat').write_text(stat_text(pid, start, user, system, count))
        (path / 'status').write_text(status_text(pid))
        (path / 'environ').write_bytes(self.owner.needle if token else b'UNRELATED=1')
        (path / 'cmdline').write_bytes(role + b'\0secret-argument\0-map_id\0' + b'5\0')
        task = path / 'task'
        task.mkdir(exist_ok=True)
        for i in range(count):
            tid = pid + i
            thread = task / str(tid)
            thread.mkdir(exist_ok=True)
            (thread / 'stat').write_text(stat_text(tid, start + i, user + i, system))
            (thread / 'status').write_text(status_text(tid, pid))
        return path

    def test_stat_parser_handles_parentheses_and_rejects_invalid(self):
        value = metrics.parse_stat(stat_text(123, 456, 78, 90, 4))
        self.assertEqual(value, dict(proc_pid=123, starttime=456, user_ticks=78, system_ticks=90, threads=4))
        for invalid in ('bad', stat_text(123, user=-1), 'x' * (metrics.READ_BYTES + 1)):
            with self.assertRaises((ValueError, IndexError)):
                metrics.parse_stat(invalid)

    def test_cpu_delta_clock_resets_and_pid_reuse(self):
        old = dict(proc_pid=12, starttime=20, user_ticks=100, system_ticks=50, observed_monotonic=10)
        new = dict(old, user_ticks=200, system_ticks=75, observed_monotonic=15)
        result = metrics.cpu_delta(new, old, 100)
        self.assertEqual((result['cpu_user_ms'], result['cpu_system_ms'], result['cpu_percent_one_core']),
                         (1000, 250, 25))
        for modified, status in ((None, 'initial'), (dict(old, starttime=1), 'identity_changed'),
                (dict(old, user_ticks=500), 'counter_regressed'),
                (dict(old, observed_monotonic=16), 'nonadvancing_clock')):
            result = metrics.cpu_delta(new, modified, 100)
            self.assertEqual(result['delta_status'], status)
            self.assertIsNone(result['cpu_user_ms'])

    def test_roles_never_export_command_line(self):
        role, map_id = metrics.process_role(b'/opt/FEXInterpreter\0Z:\\srv\\MapServer.exe\0-map_id\0' + b'5\0private\0')
        self.assertEqual((role, map_id), ('mapserver', 5))
        self.assertEqual(metrics.process_role(b'not-wineserver-helper\0secret'), ('other', None))

    def test_owned_totals_threads_and_nonowner_exclusion(self):
        self.process(count=3)
        self.process(pid=9500, role=b'CityOfHeroes.exe', token=False)
        receipt = copy.deepcopy(self.owner.receipt)
        first, info = self.sampler.processes(11)
        self.assertTrue(info['complete'])
        self.assertEqual([row['proc_pid'] for row in first], [9001])
        self.assertEqual(first[0]['threads'], 3)
        self.assertEqual(len(first[0]['thread_cpu']), 3)
        self.assertTrue(first[0]['ownership_rechecked_before_and_after'])
        self.assertEqual(self.owner.receipt, receipt)
        self.assertFalse(self.owner.initialized)
        self.now = 15
        self.process(user=120, system=60, count=3)
        second, _ = self.sampler.processes(16)
        self.assertEqual(second[0]['delta_status'], 'measured')
        self.assertAlmostEqual(second[0]['cpu_user_ms'], 100000 / self.sampler.hz)
        self.assertEqual(second[0]['thread_cpu'][0]['delta_status'], 'measured')

    def test_owner_before_after_rejects_pid_reuse(self):
        self.process(role=b'unknown')
        identities = [dict(proc_pid=9001, pid=9001, starttime=200),
                      dict(proc_pid=9001, pid=9001, starttime=201)]
        with patch.object(base.WineProcessOwner, 'inspect', side_effect=identities):
            rows, info = self.sampler.processes(11)
        self.assertFalse(rows)
        self.assertFalse(info['complete'])
        self.assertEqual(info['errors'], 1)

    def test_thread_limits_are_explicit_and_totals_remain(self):
        self.process(count=4)
        with patch.object(metrics, 'THREAD_LIMIT', 2), patch.object(metrics, 'THREAD_EXPORT_LIMIT', 1):
            rows, _ = self.sampler.processes(11)
        self.assertEqual(rows[0]['threads'], 4)
        self.assertEqual(len(rows[0]['thread_cpu']), 1)
        self.assertEqual(rows[0]['thread_sampling']['tasks_scanned'], 2)
        self.assertFalse(rows[0]['thread_sampling']['complete'])
        self.assertEqual(rows[0]['thread_sampling']['rows_omitted'], 1)

    def test_thread_detail_discarded_if_ownership_changes_after_tasks(self):
        self.process(count=2)
        identity = dict(proc_pid=9001, pid=9001, starttime=200)
        with patch.object(base.WineProcessOwner, 'inspect', side_effect=[identity, identity,
                identity, dict(identity, starttime=201)]):
            rows, _ = self.sampler.processes(11)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['thread_cpu'], [])
        self.assertEqual(rows[0]['thread_sampling']['unavailable_reason'], 'ValueError')

    def test_unreadable_thread_keeps_group_total_with_partial_marker(self):
        path = self.process(count=2)
        (path / 'task/9002/status').unlink()
        rows, _ = self.sampler.processes(11)
        self.assertEqual(rows[0]['threads'], 2)
        self.assertEqual(rows[0]['thread_sampling']['errors'], 1)
        self.assertFalse(rows[0]['thread_sampling']['complete'])

    def test_process_limits_and_deadline_are_explicit(self):
        self.process()
        self.process(pid=9500)
        with patch.object(metrics, 'PROCESS_LIMIT', 1):
            rows, info = self.sampler.processes(11)
        self.assertEqual(len(rows), 1)
        self.assertFalse(info['complete'])

    def test_discovery_resumes_after_budget_to_find_new_zone(self):
        for pid in range(9001, 9007):
            self.process(pid=pid, token=False)
        self.process(pid=9008, role=b'MapServer.exe')
        original = base.WineProcessOwner.inspect
        def slower_inspect(observer, pid, deadline):
            self.now += .02
            return original(observer, pid, deadline)
        found = []
        with patch.object(base.WineProcessOwner, 'inspect', slower_inspect):
            for _ in range(5):
                rows, info = self.sampler.processes(self.now + metrics.BUDGET)
                found.extend(rows)
                self.now += 5
        self.assertIn(9008, [row['proc_pid'] for row in found])
        rows, info = self.sampler.processes(9)
        self.assertFalse(rows)
        self.assertFalse(info['complete'])

    def test_cleanup_closes_partial_discovery_and_stops_observation(self):
        self.process()
        self.process(pid=9500)
        with patch.object(metrics, 'PROCESS_LIMIT', 1):
            self.sampler.processes(11)
        self.assertIsNotNone(self.sampler._proc_entries)
        self.sampler.close()
        self.assertIsNone(self.sampler._proc_entries)
        self.sampler.observe()
        self.assertFalse(self.sampler.path.exists())

    def write_progress(self, path, completed, sequence=2, pid=33):
        record = progress.HEADER.pack(b'COHMAP1\0', 1, 128, pid, 44, sequence, 34,
            completed, completed, 0, len(progress.STAGES))
        path.write_bytes(record + bytes(progress.MAPPING_BYTES - len(record)))

    def test_all_resident_maps_use_real_progress_decoder_and_independent_history(self):
        maps = self.diagnostic.local_server.maps
        for map_id in (1, 5):
            path = self.root / (str(map_id) + '.bin')
            self.write_progress(path, map_id * 100)
            maps[map_id] = dict(progress_path=path, process=SimpleNamespace(
                process=SimpleNamespace(pid=9000 + map_id, poll=lambda: None)), previous={'sentinel': True})
        with patch.object(progress.time, 'monotonic', return_value=10):
            rows, _ = self.sampler.maps(11)
        self.assertEqual([row['map_id'] for row in rows], [1, 5])
        self.assertTrue(all(row['delta_status'] == 'initial' for row in rows))
        self.now = 15
        for map_id in maps:
            self.write_progress(maps[map_id]['progress_path'], map_id * 100 + 150, sequence=4)
        with patch.object(progress.time, 'monotonic', return_value=15):
            rows, _ = self.sampler.maps(16)
        self.assertTrue(all(row['ticks_per_second'] == 30 for row in rows))
        self.assertTrue(all(entry['previous'] == {'sentinel': True} for entry in maps.values()))

    def test_map_identity_reset_and_counter_regression_have_no_rate(self):
        before = dict(windows_pid=1, main_thread_id=2, file_identity={'inode': 3},
                      tick_completed=100, sequence=4, observed_monotonic=10)
        after = dict(before, tick_completed=90, observed_monotonic=15)
        self.assertEqual(metrics.map_delta(after, before)['delta_status'], 'counter_regressed')
        self.assertIsNone(metrics.map_delta(dict(after, windows_pid=9), before)['ticks_per_second'])

    def test_stopped_missing_or_invalid_map_is_unavailable(self):
        self.diagnostic.local_server.maps = {5: dict(progress_path=self.root / 'missing',
            process=SimpleNamespace(process=SimpleNamespace(pid=55, poll=lambda: 1)))}
        rows, _ = self.sampler.maps(11)
        self.assertFalse(rows[0]['available'])
        self.assertEqual(rows[0]['unavailable_reason'], 'ProcessLookupError')

    def test_observe_schema_throttle_and_no_private_arguments(self):
        self.process()
        self.sampler.observe()
        self.sampler.observe()
        self.assertEqual(self.sampler.summary['samples_written'], 1)
        raw = self.sampler.path.read_text()
        row = json.loads(raw)
        self.assertEqual(row['schema'], metrics.SCHEMA)
        self.assertFalse(row['is_success_proof'])
        for name in ('longest_tick_ms', 'file_load_ms', 'wineserver_requests'):
            self.assertIsNone(row[name])
            self.assertFalse(self.sampler.summary[name]['available'])
        self.assertIn('collection_overhead_ms', row)
        self.assertIn('last_callback_overhead_ms', self.sampler.summary)
        self.assertNotIn('secret-argument', raw)
        self.assertNotIn(self.owner.needle.decode(), raw)

    def test_failsoft_errors_and_export_bounds(self):
        with patch.object(self.sampler, 'processes', side_effect=PermissionError('private details')):
            self.sampler.observe()
        row = json.loads(self.sampler.path.read_text())
        self.assertEqual(row['sample_error_type'], 'PermissionError')
        self.assertNotIn('private details', self.sampler.path.read_text())
        self.now = 15
        with patch.object(metrics, 'SAMPLE_LIMIT', 1):
            self.sampler.observe()
        self.assertEqual(self.sampler.summary['samples_omitted'], 1)
        old_bytes = self.sampler.summary['export_bytes']
        with patch.object(metrics, 'EXPORT_BYTES', old_bytes):
            self.sampler.append({'new': 'value'})
        self.assertEqual(self.sampler.path.stat().st_size, old_bytes)

    def test_output_symlink_cannot_overwrite_other_file(self):
        other = self.root / 'other'
        other.write_text('unchanged')
        self.sampler.path.symlink_to(other)
        self.sampler.observe()
        self.assertEqual(other.read_text(), 'unchanged')
        self.assertEqual(self.sampler.summary['samples_written'], 0)
        self.assertGreater(self.sampler.summary['errors'], 0)

    def test_health_hook_preserves_original_failures_and_isolates_telemetry(self):
        class Existing:
            def initialize(self):
                pass
        class Selected(armport_interactive.ArmPortClient, Existing):
            pass
        value = Selected()
        calls = []
        context = SimpleNamespace(report={'asset_sha256': {name: {} for name in
            ('armport-client.zip', 'armport_client_package.py', 'armport_interactive.py', 'client_stdio.py')},
            'client_worktree': {}}, server_health=lambda: calls.append('health'))
        value.ctx, value.root, value.args = context, self.root, SimpleNamespace(session_id='abc')
        fake = SimpleNamespace(observe=lambda: calls.append('metrics'),
                               failure=lambda error: calls.append(type(error).__name__))
        with patch.object(metrics, 'ServerMetrics', return_value=fake):
            value.initialize()
        context.server_health()
        self.assertEqual(calls, ['health', 'metrics'])
        def telemetry_error():
            raise PermissionError('optional sample')
        fake.observe = telemetry_error
        context.server_health()
        self.assertEqual(calls[-2:], ['health', 'PermissionError'])
        def required_error():
            raise base.DiagnosticError('original health failure')
        context.server_health = required_error
        with patch.object(metrics, 'ServerMetrics', return_value=fake):
            value.initialize()
        with self.assertRaisesRegex(base.DiagnosticError, 'original health failure'):
            context.server_health()


if __name__ == '__main__':
    unittest.main()
