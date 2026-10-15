"""Reject corrupt observations and preserve timing/producer uncertainty."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import analyze_client_render_queue as report
from test_client_renderer_performance_report import support
from test_client_scene_performance_report import metric


def window(index=1, samples=(50, 100)):
    counters = dict.fromkeys(report.COUNTERS, 0)
    counters.update(commands=1000*index, armed_observations=10*index,
        wake_signals=8*index, wake_signal_failures=index,
        pending_commands=900*index, ring_waits=2*index,
        ring_wait_iterations=4*index, ring_wait_wall_ms=100.0*index,
        ring_wait_max_ms=50.0*index)
    return {'format': 1, 'event': 'window', 'scope': 'gameplay',
        'queue_scope': 'process_cumulative', 'report': index, 'window_ms': 10000,
        'sample_interval': 32, 'gameplay_frames': 64, 'sampled_frames': len(samples),
        'incomplete_frames': 0, 'queue_counters_saturated': False,
        'queue_counters': counters, 'bucket_upper_ms': list(report.renderer.scene.BOUNDS),
        'metrics': {name: {key: value for key, value in metric(samples).items()
            if key in report.pipeline.METRIC_FIELDS} for name in report.METRICS} if samples else {}}


def line(row):
    return report.PREFIX + json.dumps(row)


def producers():
    return {'client_executable_sha256': '3'*64,
        'client_render_queue': {'verified': True, 'repository_commit': '3'*40,
            'client_executable_sha256': '3'*64, 'manifest_sha256': '4'*64,
            'native_source_sha256': '9'*64, 'base_client_executable_sha256': '2'*64,
            'base_client_render_pipeline_manifest_sha256': '5'*64},
        'client_render_pipeline': {'client_executable_sha256': '2'*64,
            'manifest_sha256': '5'*64, 'base_client_executable_sha256': '1'*64,
            'base_client_renderer_attribution_manifest_sha256': '6'*64},
        'client_renderer_attribution': {'client_executable_sha256': '1'*64, 'manifest_sha256': '6'*64},
        'client_render_queue_environment': {'enabled': True, 'client_executable_sha256': '3'*64,
            'producer_manifest_sha256': '4'*64, 'native_source_sha256': '9'*64},
        'client_render_pipeline_environment': {'enabled': True, 'client_executable_sha256': '3'*64,
            'producer_manifest_sha256': '5'*64, 'current_Game_manifest_sha256': '4'*64,
            'pipeline_producer_executable_sha256': '2'*64}}


class RenderQueueReportTests(unittest.TestCase):
    def test_weighted_samples_and_cumulative_snapshots_not_summed(self):
        rows = [window(samples=(50,)), window(2, samples=(100, 200, 200))]
        report.validate_queue(rows)
        value = report.summarize_queue(rows)
        self.assertEqual(value['sampled_scene_metrics']['setup_wall']['mean_ms'], 137.5)
        self.assertEqual(value['sampled_scene_metrics']['setup_wall']['count'], 4)
        self.assertEqual(value['latest_process_cumulative_queue_counters']['commands'], 2000)
        self.assertEqual(value['queue_counter_increase_between_first_and_last_report']['commands'], 1000)
        self.assertNotIn('ring_wait_max_ms', value['queue_counter_increase_between_first_and_last_report'])
        for key in ('fps', 'cpu_ms', 'gpu_time_ms', 'avoided_event_calls'):
            self.assertNotIn(key, value)

    def test_missing_unsampled_and_single_snapshot_are_not_zero_measurements(self):
        self.assertIsNone(report.summarize_queue([]))
        row = window(samples=())
        report.validate_queue([row])
        value = report.summarize_queue([row])
        self.assertEqual(value['sampled_scene_metrics'], {})
        self.assertIsNone(value['queue_counter_increase_between_first_and_last_report'])

    def test_uint64_counters_are_exact_and_saturated_deltas_are_unavailable(self):
        rows = [window(), window(2)]
        rows[-1]['queue_counters']['commands'] = report.UINT64_MAX
        rows[-1]['queue_counters_saturated'] = True
        report.validate_queue(rows)
        self.assertIsNone(report.summarize_queue(rows)['queue_counter_increase_between_first_and_last_report'])
        parsed = report.queue_records(line(rows[-1]))[0]
        self.assertEqual(parsed['queue_counters']['commands'], report.UINT64_MAX)
        for wrong in (False, 1, 1.0, None):
            bad = copy.deepcopy(rows); bad[-1]['queue_counters_saturated'] = wrong
            with self.subTest(wrong=wrong), self.assertRaises(ValueError): report.validate_queue(bad)

    def test_counter_conservation_monotonicity_and_clock_bounds_reject_corruption(self):
        changes = [('commands', 1), ('armed_observations', 1001), ('pending_commands', 1001),
            ('wake_signal_failures', 3), ('ring_waits', 5), ('ring_wait_clock_failures', 3),
            ('ring_wait_max_ms', 101), ('ring_wait_wall_ms', -1),
            ('ring_wait_wall_ms', float('inf')), ('commands', report.UINT64_MAX+1),
            ('commands', True), ('commands', 1000.0)]
        for key, value in changes:
            row = window(); row['queue_counters'][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError): report.validate_queue([row])
        for key in report.COUNTERS | report.WALL_COUNTERS:
            a = window()
            a['queue_counters'].update(commands=1000, armed_observations=100,
                wake_signals=20, wake_signal_failures=10, pending_commands=100,
                ring_waits=50, ring_wait_iterations=500, ring_wait_clock_failures=10)
            b = copy.deepcopy(a); b['queue_counters'][key] -= 1
            report.validate_queue([a]); report.validate_queue([b])
            b['report'] = 2
            with self.subTest(decreased=key), self.assertRaises(ValueError): report.validate_queue([a, b])

    def test_native_large_count_and_clock_values_are_accepted_without_lower_parser_cap(self):
        row = window(samples=(5e9,))
        report.validate_queue([row])
        report.validate_queue([window(samples=(1e12,))])
        with self.assertRaises(ValueError): report.validate_queue([window(samples=(1e12, 1e12))])
        self.assertEqual(report.summarize_queue([row])['sampled_scene_metrics']['draw_wall']['mean_ms'], 5e9)
        row = window(samples=(0,))
        row['gameplay_frames'] = row['sampled_frames'] = 2**32-1
        for value in row['metrics'].values():
            value['count'] = 2**32-1
            value['histogram'][0] = 2**32-1
        report.validate_queue([row])

    def test_saturation_does_not_bypass_independent_conservation(self):
        row = window()
        row['queue_counters']['commands'] = report.UINT64_MAX
        row['queue_counters_saturated'] = True
        row['queue_counters'].update(ring_waits=100, ring_wait_iterations=1)
        with self.assertRaises(ValueError): report.validate_queue([row])
        row = window()
        row['queue_counters'].update(commands=report.UINT64_MAX,
            armed_observations=report.UINT64_MAX, wake_signals=report.UINT64_MAX,
            wake_signal_failures=report.UINT64_MAX)
        row['queue_counters_saturated'] = True
        report.validate_queue([row])

    def test_schema_sampling_histogram_and_sequence_are_strict(self):
        changes = [lambda r: r.update(format=True), lambda r: r.update(report=2),
            lambda r: r.update(queue_scope='gameplay'), lambda r: r.update(sample_interval=1),
            lambda r: r.update(sampled_frames=65), lambda r: r.update(window_ms=9999),
            lambda r: r.update(queue_counters_saturated=True), lambda r: r.update(extra=True),
            lambda r: r['bucket_upper_ms'].__setitem__(0, 16.0),
            lambda r: r['metrics'].pop('setup_wall'),
            lambda r: r['metrics']['setup_wall'].update(count=3),
            lambda r: r['metrics']['setup_wall'].update(mean_ms=1),
            lambda r: r['metrics']['setup_wall'].update(p95_upper_ms=33)]
        for change in changes:
            row = window(); change(row)
            with self.subTest(change=change), self.assertRaises(ValueError): report.validate_queue([row])
        with self.assertRaises(ValueError): report.validate_queue([window(), window()])

    def test_prefixed_json_budgets_and_duplicate_keys_fail_closed(self):
        for raw in ('{"format":1,"format":1}', '{"format":NaN}', '{}trailing', ' '*8192):
            with self.subTest(raw=raw[:40]), self.assertRaises(ValueError): report.queue_records(report.PREFIX+raw)
        with self.assertRaises(ValueError): report.queue_records('\n'.join(line(window()) for _ in range(121)))

    def test_current_Game_parent_and_operational_environment_are_distinct(self):
        guest = producers()
        value = report.producer_summary(guest)
        self.assertTrue(value['supplied_identity_fields_consistent'])
        self.assertEqual(value['supplied_identity_checks'], 10)
        self.assertFalse(value['source_closure_reverified_by_host_analysis'])
        for group, key in [('client_render_queue', 'base_client_executable_sha256'),
                ('client_render_queue', 'base_client_render_pipeline_manifest_sha256'),
                ('client_render_queue_environment', 'client_executable_sha256'),
                ('client_render_queue_environment', 'native_source_sha256'),
                ('client_render_pipeline_environment', 'client_executable_sha256'),
                ('client_render_pipeline_environment', 'producer_manifest_sha256'),
                ('client_renderer_attribution', 'manifest_sha256')]:
            bad = copy.deepcopy(guest); bad[group][key] = '0'*64
            with self.subTest(group=group, key=key), self.assertRaises(ValueError): report.producer_summary(bad)
        guest['client_render_pipeline_environment']['enabled'] = False
        guest['client_render_pipeline_environment']['client_executable_sha256'] = None
        self.assertTrue(report.producer_summary(guest)['supplied_identity_fields_consistent'])
        guest['client_render_pipeline_environment']['client_executable_sha256'] = '0'*64
        with self.assertRaises(ValueError): report.producer_summary(guest)

    def test_identity_types_and_actual_attempt_conflicts_are_not_promoted_to_consistent(self):
        for group, field, wrong in [('client_render_queue', 'verified', 1),
                ('client_render_queue_environment', 'enabled', 1),
                ('client_render_queue', 'client_executable_sha256', True),
                ('client_render_queue', 'repository_commit', 'invalid')]:
            guest = producers(); guest[group][field] = wrong
            with self.subTest(group=group, field=field), self.assertRaises(ValueError): report.producer_summary(guest)
        for name in ('client_gpu_profile', 'client_gpu_profile_attempts'):
            guest = producers(); value = {'game_producer': {'client_executable_sha256': '0'*64}}
            guest[name] = value if name == 'client_gpu_profile' else [value]
            with self.subTest(name=name), self.assertRaises(ValueError): report.producer_summary(guest)
        for field, expected in [('current_Game_repository_commit', '3'*40),
                ('pipeline_producer_repository_commit', '2'*40), ('native_source_sha256', '8'*64)]:
            guest = producers()
            guest['client_render_pipeline'].update(repository_commit='2'*40, native_source_sha256='8'*64)
            guest['client_render_pipeline_environment'][field] = expected
            report.producer_summary(guest)
            guest['client_render_pipeline_environment'][field] = '0'*len(expected)
            with self.subTest(field=field), self.assertRaises(ValueError): report.producer_summary(guest)

    def test_complete_zip_retains_failed_save_and_missing_older_diagnostics(self):
        guest = producers()
        guest.update(passed=False, character_reopen={'verified': False,
            'save_comparison_failure': {'status': 'failed'}})
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'support.zip'
            support(path, line(window()), android={'passed': False}, guest=guest)
            value = report.analyze(path)
        self.assertTrue(value['native_render_queue_present'])
        self.assertFalse(value['native_render_pipeline_present'])
        self.assertEqual(value['gpu_profile_and_actual_backend']['game_producer']['client_executable_sha256'], '3'*64)
        self.assertFalse(value['strict_save_result']['android_passed'])
        self.assertFalse(value['strict_save_result']['analysis_changes_save_acceptance'])
        self.assertFalse(value['pure_gameplay_main_frames_by_cap'])

    def test_old_export_and_missing_producer_remain_supported(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'support.zip'; support(path, None)
            value = report.analyze(path)
        self.assertFalse(value['native_render_queue_present'])
        self.assertIsNone(value['render_queue_observations'])
        self.assertIsNone(value['render_queue_Game_source_attribution']['supplied_identity_fields_consistent'])

    def test_cli_writes_only_a_valid_analysis(self):
        with tempfile.TemporaryDirectory() as temp:
            path, output = Path(temp)/'support.zip', Path(temp)/'out.json'
            support(path, line(window()))
            command = [sys.executable, report.__file__, str(path), '--output', str(output)]
            run = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(output.read_text()), report.analyze(path))
            output.unlink(); support(path, report.PREFIX+'{"format":NaN}')
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertFalse(output.exists())


if __name__ == '__main__': unittest.main()
