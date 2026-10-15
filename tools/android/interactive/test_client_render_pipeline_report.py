"""Exercise real report aggregation and rejection of misleading/corrupt timings."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import analyze_client_render_pipeline as report
from test_client_renderer_performance_report import support
from test_client_scene_performance_report import metric


def window(index=1, role='main', samples=(50, 100), sampled=(10, 20)):
    result = {'format': 1, 'event': 'window', 'role': role, 'report': index,
        'window_ms': 10000, 'thread_cpu_ms': 1000, 'incomplete_batches': 0,
        'scope': 'gameplay' if role == 'main' else 'all_states_independent',
        'bucket_upper_ms': list(report.renderer.scene.BOUNDS), 'metrics': {}}
    names = report.MAIN_METRICS if role == 'main' else report.RENDERER_METRICS
    for name in names:
        values = sampled if name in ('renderer_command_wall', 'renderer_queue_gap_wall') else samples
        result['metrics'][name] = {key: value for key, value in metric(values).items()
            if key in report.METRIC_FIELDS}
    if role == 'renderer':
        result.update(sample_interval=16, sampled_batches=len(sampled), sampled_command_count=len(sampled) * 4)
    return result


def line(value):
    return report.PREFIX + json.dumps(value)


class RenderPipelineReportTests(unittest.TestCase):
    def test_each_metric_uses_its_own_sample_weights_and_roles_remain_independent(self):
        rows = [window(samples=(50,)), window(role='renderer', samples=(100,) * 20, sampled=(10,)),
            window(2, samples=(100, 200, 200)),
            window(2, role='renderer', samples=(200,) * 10, sampled=(20, 30))]
        report.validate_pipeline(rows)
        value = report.summarize_pipeline(rows)
        main, worker = value['main'], value['renderer']
        self.assertEqual(main['metrics']['gfx_wall']['count'], 4)
        self.assertEqual(main['metrics']['gfx_wall']['mean_ms'], 137.5)
        self.assertEqual(worker['metrics']['renderer_batch_wall']['count'], 30)
        self.assertEqual(worker['metrics']['renderer_batch_wall']['mean_ms'], 133.333)
        self.assertEqual(worker['metrics']['renderer_command_wall']['count'], 3)
        self.assertEqual(worker['metrics']['renderer_command_wall']['mean_ms'], 20)
        self.assertEqual(worker['sampled_batches'], 3)
        self.assertEqual(worker['sampled_span_ms'], 120)
        self.assertEqual(worker['sampled_dispatch_fraction_of_sampled_span'], .5)
        self.assertNotIn('fps', worker)
        self.assertNotIn('gpu_time_ms', worker)
        self.assertNotIn('gameplay', main)
        self.assertEqual(main['native_record_scope'], 'gameplay')
        self.assertEqual(worker['native_record_scope'], 'all_states_independent')

    def test_missing_cpu_remains_missing_and_zero_dispatch_span_is_not_ratio_zero(self):
        row = window(role='renderer', sampled=(0, 0)); row['thread_cpu_ms'] = None
        report.validate_pipeline([row])
        worker = report.summarize_pipeline([row])['renderer']
        self.assertIsNone(worker['measured_thread_cpu_ms'])
        self.assertEqual(worker['cpu_windows'], 0)
        self.assertIsNone(worker['sampled_dispatch_fraction_of_sampled_span'])
        self.assertEqual(worker['sampled_span_ms'], 0)

    def test_invalid_schema_role_sequences_nonfinite_and_histograms_are_rejected(self):
        mutations = [lambda r: r.update(report=2), lambda r: r.update(role='presentation'),
            lambda r: r.update(thread_cpu_ms=True), lambda r: r.update(window_ms=float('nan')),
            lambda r: r.update(incomplete_batches=-1), lambda r: r.update(event='state'),
            lambda r: r.update(scope='all_states_independent'),
            lambda r: r.update(sample_interval=16), lambda r: r['metrics'].pop('ui_wall'),
            lambda r: r['metrics']['gfx_wall'].update(count=3),
            lambda r: r['metrics']['gfx_wall'].update(mean_ms=1),
            lambda r: r['metrics']['gfx_wall'].update(max_ms=1),
            lambda r: r['metrics']['gfx_wall'].update(p95_upper_ms=33),
            lambda r: r['metrics']['gfx_wall'].update(histogram=[True] + [0] * 21),
            lambda r: r.update(bucket_upper_ms=[15] + list(report.renderer.scene.BOUNDS[1:]))]
        for mutate in mutations:
            row = window(); mutate(row)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                report.validate_pipeline([row])
        for rows in ([window(), window()], [window(121)]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                report.validate_pipeline(rows)

    def test_sampled_counts_must_match_sampled_metrics_but_need_not_match_all_batches(self):
        valid = window(role='renderer', samples=(50,) * 32, sampled=(10, 20))
        report.validate_pipeline([valid])
        mutations = [lambda r: r.update(sample_interval=1), lambda r: r.update(sampled_batches=0),
            lambda r: r.update(sampled_command_count=-1), lambda r: r.update(sampled_batches=3),
            lambda r: r['metrics']['renderer_queue_gap_wall'].update(count=1, histogram=[1]+[0]*21, mean_ms=10, max_ms=10, p95_upper_ms=16)]
        for mutate in mutations:
            row = copy.deepcopy(valid); mutate(row)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                report.validate_pipeline([row])

    def test_unsampled_window_omits_sample_metrics_and_is_not_zero_measured_work(self):
        row = window(role='renderer', samples=(50,), sampled=(10,))
        row.update(sampled_batches=0, sampled_command_count=0)
        row['metrics'].pop('renderer_command_wall')
        row['metrics'].pop('renderer_queue_gap_wall')
        report.validate_pipeline([row])
        worker = report.summarize_pipeline([row])['renderer']
        self.assertEqual(worker['sampled_batches'], 0)
        self.assertIsNone(worker['sampled_span_ms'])
        self.assertIsNone(worker['sampled_dispatch_fraction_of_sampled_span'])
        self.assertNotIn('renderer_command_wall', worker['metrics'])
        row['sampled_command_count'] = 1
        with self.assertRaises(ValueError):
            report.validate_pipeline([row])

    def test_corrupt_prefixed_json_duplicate_keys_and_record_bound_are_rejected(self):
        for raw in ('{"format":1,"format":1}', '{"format":NaN}', '{}trailing'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                report.pipeline_records(report.PREFIX + raw)
        console = '\n'.join(line(window()) for _ in range(report.MAX_RECORDS + 1))
        with self.assertRaises(ValueError):
            report.pipeline_records(console)

    def test_complete_zip_keeps_failed_save_and_separate_streams_without_gpu_claim(self):
        android = {'app_version': '0.13.22', 'passed': False, 'cleanup_verified': False,
            'character_reopen_verified': False, 'android_capture_diagnostics': {'native_fps_measurement': False}}
        failure = {'status': 'failed', 'save_verified': False}
        guest = {'passed': False, 'failures': ['Committed character rows changed'],
            'character_reopen': {'verified': False, 'save_comparison_failure': failure}}
        console = '\n'.join((line(window()), line(window(role='renderer'))))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'support.zip'; support(path, console, android=android, guest=guest)
            value = report.analyze(path)
        self.assertTrue(value['native_render_pipeline_present'])
        self.assertEqual(set(value['render_pipeline_streams_all_states_unaligned']), {'main', 'renderer'})
        self.assertFalse(value['strict_save_result']['android_passed'])
        self.assertEqual(value['strict_save_result']['save_comparison_failure'], failure)
        self.assertFalse(value['strict_save_result']['analysis_changes_save_acceptance'])
        self.assertFalse(value['gpu_profile_and_actual_backend']['hardware_acceleration_validated_by_this_analysis'])
        self.assertFalse(value['pure_gameplay_main_frames_by_cap'])
        self.assertEqual(value['android_capture_diagnostics'], android['android_capture_diagnostics'])

    def test_previous_zip_without_new_prefix_reports_missing_instrumentation(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'support.zip'; support(path, None)
            value = report.analyze(path)
        self.assertFalse(value['native_render_pipeline_present'])
        self.assertEqual(value['render_pipeline_streams_all_states_unaligned'], {})
        self.assertFalse(value['client_console_present'])

    def test_current_Game_producer_is_separate_from_ancestor_and_identity_mismatch_rejected(self):
        current = {'verified': True, 'repository_commit': '2' * 40,
            'client_executable_sha256': '2' * 64, 'manifest_sha256': '3' * 64,
            'base_client_executable_sha256': '1' * 64,
            'base_client_renderer_attribution_manifest_sha256': '4' * 64}
        ancestor = {'repository_commit': '1' * 40,
            'client_executable_sha256': '1' * 64, 'manifest_sha256': '4' * 64}
        guest = {'client_render_pipeline': current, 'client_renderer_attribution': ancestor,
            'client_executable_sha256': '2' * 64,
            'client_render_pipeline_environment': {'enabled': True,
                'client_executable_sha256': '2' * 64, 'producer_manifest_sha256': '3' * 64}}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'support.zip'; support(path, line(window()), guest=guest)
            value = report.analyze(path)
        source = value['render_pipeline_Game_source_attribution']
        self.assertEqual(source['supplied_identity_checks'], 5)
        self.assertTrue(source['supplied_identity_fields_consistent'])
        backend = value['gpu_profile_and_actual_backend']
        self.assertEqual(backend['game_producer']['client_executable_sha256'], '2' * 64)
        self.assertEqual(backend['inherited_renderer_attribution_producer']['client_executable_sha256'], '1' * 64)
        self.assertFalse(source['source_closure_reverified_by_host_analysis'])
        for mutate in (lambda g: g.update(client_executable_sha256='0' * 64),
                lambda g: g['client_render_pipeline_environment'].update(client_executable_sha256='0' * 64),
                lambda g: g['client_renderer_attribution'].update(manifest_sha256='0' * 64),
                lambda g: g.update(client_render_pipeline=True)):
            bad = copy.deepcopy(guest); mutate(bad)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                report.producer_summary(bad)
        missing = report.producer_summary({})
        self.assertIsNone(missing['supplied_identity_fields_consistent'])
        self.assertIsNone(missing['current_producer_verified_by_guest_report'])

    def test_cli_emits_same_result_and_does_not_create_report_after_corrupt_input(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'support.zip'; support(path, line(window()))
            script = Path(report.__file__)
            stdout = subprocess.run([sys.executable, str(script), str(path)], check=True, capture_output=True, text=True)
            output = Path(temp) / 'nested' / 'report.json'
            subprocess.run([sys.executable, str(script), str(path), '--output', str(output)], check=True, capture_output=True)
            self.assertEqual(json.loads(stdout.stdout), json.loads(output.read_text()))
            output.unlink(); bad = window(); bad['metrics']['ui_wall']['mean_ms'] = 1
            support(path, line(bad))
            rejected = subprocess.run([sys.executable, str(script), str(path), '--output', str(output)], capture_output=True)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
