"""Real telemetry code against synthetic procfs/progress, without Wine or compilers."""
import copy
import ast
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


def native_line(map_id=5, pid=33, **changes):
    values = dict(seconds='5.250000', ticks='150', max_tick_ms='30.000', max_loop_ms='35.000',
        filealloc_ms='1.250', filealloc_calls='4', filealloc_failures='1', counter_saturated='0',
        scope=metrics.NATIVE_SCOPE)
    values.update(changes)
    fields = ' '.join(key + '=' + str(value) for key, value in values.items())
    return ('ARMPORT_SERVER_METRICS_V1 status=ok map_id=%d pid=%d ' % (map_id, pid) + fields + '\n').encode()


class NativeConsoleTests(unittest.TestCase):
    setUp = MetricsTests.setUp
    write_progress = MetricsTests.write_progress
    process = MetricsTests.process

    def owned_map(self, map_id=5, pid=33, output=None):
        path = self.root / ('map-%d.bin' % map_id)
        self.write_progress(path, 100, pid=pid)
        handle = SimpleNamespace(process=SimpleNamespace(pid=9000 + map_id, poll=lambda: None),
            output=bytearray(native_line(map_id, pid) if output is None else output), overflow=False)
        entry = dict(process=handle, progress_path=path, launch_utc_ms=9000, server_metrics_enabled=True)
        self.diagnostic.local_server.maps[map_id] = entry
        self.diagnostic.local_server.map_contract = {'producer': {'armport_server_metrics': {'variant': 'test'}}}
        return entry

    def sample_maps(self):
        with patch.object(progress.time, 'monotonic', return_value=self.now):
            rows, _ = self.sampler.maps(self.now + .05)
        info = self.sampler.native_durations(rows, self.now + .05)
        return rows, info

    def tail(self, output):
        return metrics.NativeConsoleTail(('generation',), bytearray(output))

    def sample_tail(self, tail, now=10, maximum=8192):
        return tail.sample(5, 33, now, lambda: now, now + .005, maximum)

    def test_parser_matches_actual_native_snprintf_format(self):
        source = (ROOT / 'armport/patches/0119-armport-server-tick-file-metrics.patch').read_text()
        literal = next(line[1:].strip().removesuffix(',') for line in source.splitlines()
            if '"ARMPORT_SERVER_METRICS_V1 status=ok map_id=' in line)
        template = ast.literal_eval(literal).replace('%llu', '%d').replace('%lu', '%d')
        real_format_line = (template % (5, 33, 5.25, 150, 30, 35, 1.25, 4, 1, 0)).encode()
        self.assertEqual(real_format_line, native_line())
        row = metrics.parse_native_window(real_format_line.rstrip(b'\n'), 5, 33)
        self.assertEqual((row['max_tick_ms'], row['max_loop_ms'], row['filealloc_ms']), (30, 35, 1.25))
        self.assertEqual(row['windows_pid'], 33)
        self.assertNotIn('wineserver_requests', row)

    def test_parser_rejects_malformed_numeric_scope_and_identity(self):
        for changes in ({'seconds': 'nan'}, {'seconds': '4.999999'}, {'ticks': '0'},
                {'ticks': str(2**64)}, {'filealloc_calls': '-1'}, {'filealloc_failures': '5'},
                {'max_tick_ms': '36.000'}, {'max_loop_ms': '6000.000'}, {'filealloc_ms': '6000.000'},
                {'scope': 'all_IO'}, {'counter_saturated': '2'}, {'seconds': '5.25'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                metrics.parse_native_window(native_line(**changes).rstrip(b'\n'), 5, 33)
        for line in (native_line().rstrip(b'\n') + b' secret=hidden',
                     b'prefix ' + native_line().rstrip(b'\n'), metrics.NATIVE_PREFIX + b'x' * 500):
            with self.assertRaises(ValueError):
                metrics.parse_native_window(line, 5, 33)
        for map_id, pid in ((1, 33), (5, 9005)):
            with self.assertRaises(LookupError):
                metrics.parse_native_window(native_line().rstrip(b'\n'), map_id, pid)
        self.assertIsNone(metrics.parse_native_window(b'ordinary private logging', 5, 33))

    def test_fragmented_record_crlf_and_no_duplicate_window(self):
        line = native_line().replace(b'\n', b'\r\n')
        tail = self.tail(line[:100])
        first = self.sample_tail(tail)
        self.assertEqual(first['status'], 'partial')
        self.assertFalse(first['available'])
        tail.output.extend(line[100:])
        second = self.sample_tail(tail, 15)
        self.assertEqual(second['status'], 'measured')
        self.assertEqual(len(second['windows']), 1)
        self.assertIsNone(second['windows'][0]['since_previous_caught_up_sample_seconds'])
        third = self.sample_tail(tail, 20)
        self.assertEqual(third['status'], 'no_new_record')
        self.assertEqual(third['windows'], [])
        tail.output.extend(native_line())  # identical native values in another legitimate window
        fourth = self.sample_tail(tail, 25)
        self.assertEqual(len(fourth['windows']), 1)
        self.assertEqual(fourth['windows'][0]['since_previous_caught_up_sample_seconds'], 5)

    def test_missing_stale_and_clock_error_are_not_zero_measurements(self):
        tail = self.tail(b'')
        self.assertEqual(self.sample_tail(tail)['status'], 'missing')
        tail.output.extend(native_line())
        self.assertEqual(self.sample_tail(tail, 15)['status'], 'measured')
        stale = self.sample_tail(tail, 30)
        self.assertEqual(stale['status'], 'stale')
        self.assertTrue(stale['last_record_stale'])
        self.assertFalse(stale['available'])
        self.assertEqual(stale['windows'], [])
        tail.output.extend(b'ARMPORT_SERVER_METRICS_V1 status=clock_error map_id=5 pid=33\n')
        self.assertEqual(self.sample_tail(tail, 35)['status'], 'clock_error')
        tail.output.extend(native_line())
        after = self.sample_tail(tail, 40)
        self.assertEqual(after['status'], 'clock_error')
        self.assertEqual(after['malformed_records'], 1)
        self.assertFalse(after['available'])

    def test_byte_line_window_and_pending_bounds_are_explicit(self):
        tail = self.tail(b'private' * 2000 + b'\n' + native_line())
        row = self.sample_tail(tail)
        self.assertEqual(row['status'], 'partial')
        self.assertGreater(row['bytes_skipped'], 0)
        self.assertLessEqual(row['bytes_copied'], metrics.NATIVE_BYTES_PER_MAP)
        self.assertEqual(len(row['windows']), 1)
        self.assertNotIn('private', json.dumps(row))
        tail = self.tail(b'x\n' * 5 + native_line())
        with patch.object(metrics, 'NATIVE_LINES', 2):
            row = self.sample_tail(tail)
        self.assertEqual(row['lines_scanned'], 2)
        self.assertEqual(row['status'], 'partial')
        self.assertEqual(len(self.sample_tail(tail, 15)['windows']), 1)
        tail = self.tail(native_line() * (metrics.NATIVE_WINDOWS + 2))
        row = self.sample_tail(tail)
        self.assertEqual(row['windows_omitted'], 2)
        self.assertEqual(len(row['windows']), metrics.NATIVE_WINDOWS)
        self.assertEqual(row['status'], 'partial')
        tail = self.tail(metrics.NATIVE_PREFIX + b'x' * 5000)
        row = self.sample_tail(tail)
        self.assertEqual(row['malformed_records'], 1)
        self.assertLess(len(tail.pending), metrics.NATIVE_LINE_BYTES)
        tail.output.extend(b'\n' + native_line())
        self.assertEqual(len(self.sample_tail(tail, 15)['windows']), 1)

    def test_budget_and_saturation_never_claim_complete_window(self):
        tail = self.tail(native_line(counter_saturated='1', ticks=str(2**64 - 1)))
        row = tail.sample(5, 33, 10, lambda: 11, 11, 8192)
        self.assertEqual(row['status'], 'partial')
        self.assertEqual(row['bytes_copied'], 0)
        self.assertEqual(tail.offset, 0)
        row = self.sample_tail(tail)
        self.assertEqual(row['status'], 'partial')
        self.assertTrue(row['windows'][0]['counter_saturated'])
        self.assertFalse(row['complete'])

    def test_admission_and_launch_activation_are_both_required(self):
        entry = self.owned_map()
        self.diagnostic.local_server.map_contract = {}
        rows, _ = self.sample_maps()
        self.assertEqual(rows[0]['native_durations']['status'], 'disabled')
        self.assertEqual(self.sampler.native_tails, {})
        self.diagnostic.local_server.map_contract = {'producer': {'armport_server_metrics': {'variant': 'test'}}}
        entry['server_metrics_enabled'] = False
        rows, _ = self.sample_maps()
        self.assertEqual(rows[0]['native_durations']['status'], 'disabled')
        del entry['server_metrics_enabled']
        rows, _ = self.sample_maps()
        self.assertEqual(rows[0]['native_durations']['status'], 'activation_unknown')

    def test_durations_are_separate_from_real_progress_and_cpu(self):
        self.process()
        entry = self.owned_map(output=native_line() + b'secret-argument\n')
        entry['previous'] = {'do_not_mutate': True}
        self.sampler.observe()
        result = json.loads(self.sampler.path.read_text())
        row = result['maps'][0]
        self.assertEqual(row['tick_completed'], 100)
        self.assertEqual(row['delta_status'], 'initial')
        self.assertEqual(row['native_durations']['windows'][0]['ticks'], 150)
        self.assertEqual(result['processes'][0]['role'], 'dbserver')
        self.assertFalse(row['native_durations']['is_success_proof'])
        self.assertIsNone(result['wineserver_requests'])
        self.assertFalse(self.sampler.summary['wineserver_requests']['available'])
        self.assertEqual(self.sampler.summary['native_duration_windows_observed'], 1)
        self.assertEqual(entry['previous'], {'do_not_mutate': True})
        self.assertNotIn('secret-argument', self.sampler.path.read_text())

    def test_foreign_native_pid_does_not_bind_to_linux_launcher(self):
        self.owned_map(output=native_line(pid=9005))
        rows, _ = self.sample_maps()
        row = rows[0]['native_durations']
        self.assertEqual(row['identity_mismatches'], 1)
        self.assertEqual(row['status'], 'malformed')
        self.assertFalse(row['available'])

    def test_new_owned_process_generation_resets_tail_but_file_change_does_not(self):
        entry = self.owned_map()
        first, _ = self.sample_maps()
        self.assertTrue(first[0]['native_durations']['available'])
        self.write_progress(entry['progress_path'], 200, pid=77)
        entry['process'].output.extend(native_line(pid=77))
        second, _ = self.sample_maps()
        self.assertEqual(second[0]['native_durations']['status'], 'identity_unavailable')
        self.owned_map(pid=77, output=native_line(pid=77))
        third, _ = self.sample_maps()
        self.assertEqual(third[0]['native_durations']['windows'][0]['windows_pid'], 77)

    def test_process_exit_and_console_replacement_during_read_discard_windows(self):
        entry = self.owned_map()
        with patch.object(progress.time, 'monotonic', return_value=10):
            rows, _ = self.sampler.maps(11)
        entry['process'].process.poll = unittest.mock.Mock(side_effect=[None, 1])
        self.sampler.native_durations(rows, 11)
        self.assertEqual(rows[0]['native_durations']['status'], 'identity_unavailable')
        self.assertFalse(rows[0]['native_durations']['available'])
        self.assertEqual(self.sampler.summary['native_duration_windows_observed'], 0)
        entry = self.owned_map()
        original = metrics.NativeConsoleTail.sample
        def replace(tail, *args):
            result = original(tail, *args)
            entry['process'].output = bytearray()
            return result
        with patch.object(metrics.NativeConsoleTail, 'sample', replace):
            rows, _ = self.sample_maps()
        self.assertEqual(rows[0]['native_durations']['status'], 'identity_unavailable')
        self.assertFalse(rows[0]['native_durations']['available'])

    def test_native_budget_rotates_maps_and_bounds_total_copies(self):
        for map_id in (1, 5):
            self.owned_map(map_id=map_id, output=native_line(map_id=map_id))
        with patch.object(metrics, 'NATIVE_TOTAL_BYTES', len(native_line(map_id=1))):
            rows, info = self.sample_maps()
        self.assertTrue(rows[0]['native_durations']['available'])
        self.assertFalse(rows[1]['native_durations']['available'])
        self.assertLessEqual(info['bytes_copied'], len(native_line(map_id=1)))
        self.assertEqual(self.sampler.native_cursor, 1)
        self.now = 15
        self.diagnostic.local_server.maps[1]['process'].output.extend(native_line(map_id=1))
        with patch.object(metrics, 'NATIVE_TOTAL_BYTES', len(native_line(map_id=5))):
            rows, _ = self.sample_maps()
        self.assertTrue(rows[1]['native_durations']['available'])
        self.assertFalse(rows[0]['native_durations']['available'])

    def test_cpu_sampling_error_does_not_hide_available_native_window(self):
        self.owned_map()
        with patch.object(self.sampler, 'processes', side_effect=PermissionError('private path')):
            self.sampler.observe()
        row = json.loads(self.sampler.path.read_text())
        self.assertEqual(row['sample_error_type'], 'PermissionError')
        self.assertTrue(row['maps'][0]['native_durations']['available'])
        self.assertNotIn('private path', self.sampler.path.read_text())

    def test_console_truncation_and_overflow_are_unavailable(self):
        entry = self.owned_map()
        self.sample_maps()
        entry['process'].output.clear()
        rows, _ = self.sample_maps()
        self.assertEqual(rows[0]['native_durations']['status'], 'identity_unavailable')
        self.assertFalse(rows[0]['native_durations']['available'])
        entry = self.owned_map()
        entry['process'].overflow = True
        rows, _ = self.sample_maps()
        self.assertEqual(rows[0]['native_durations']['status'], 'identity_unavailable')

    def test_native_sub_budget_does_not_consume_unused_whole_callback(self):
        self.owned_map(output=b'log\n' * 100 + native_line())
        original = self.sampler.clock
        time_calls = []
        def advancing_clock():
            value = 10 + len(time_calls) * .001
            time_calls.append(value)
            return value
        with patch.object(progress.time, 'monotonic', return_value=10):
            rows, _ = self.sampler.maps(11)
        self.sampler.clock = advancing_clock
        self.sampler.native_durations(rows, 11)
        self.sampler.clock = original
        row = rows[0]['native_durations']
        self.assertEqual(row['status'], 'partial')
        self.assertFalse(row['available'])
        self.assertLessEqual(row['lines_scanned'], 5)


if __name__ == '__main__':
    unittest.main()
