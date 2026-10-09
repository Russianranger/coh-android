"""Real report contracts: avoid misleading cap/GPU/save claims and reject corruption."""
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile

import analyze_client_renderer_performance as report
from test_client_scene_performance_report import frame, metric


def state(ordinal=1, cap=30):
    return {'format': 1, 'event': 'state', 'ordinal': ordinal, 'maxfps': cap, 'showfps': 1.0}


def window(index=1, role='main', samples=(100, 200)):
    result = {'format': 1, 'event': 'window', 'role': role, 'report': index,
        'window_ms': 10000, 'thread_cpu_ms': 1000, 'wait_iterations': 0,
        'incomplete_batches': 0, 'callback_counts': [0, 0, 0, 0],
        'bucket_upper_ms': list(report.scene.BOUNDS), 'metrics': {}}
    names = report.MAIN_METRICS if role == 'main' else report.RENDERER_METRICS
    for name in names:
        result['metrics'][name] = {key: value for key, value in metric(samples).items()
            if key in ('count', 'mean_ms', 'max_ms', 'p95_upper_ms', 'histogram')}
    if role == 'main':
        result['configuration'] = {'allow_frames_buffered': 0, 'threaded': 1,
                                   'sli_limit': 0, 'frame_delay': 0}
    return result


def line(value, prefix=report.PREFIX):
    return '[timestamp] ' + prefix + json.dumps(value)


def support(path, console, *, android=None, guest=None):
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, 'w') as archive:
        archive.writestr('latest-report.json', json.dumps(guest or {}))
        if console is not None:
            archive.writestr('client-evidence/client-console.log', console)
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('android-client-report.json', json.dumps(android or {}))
        archive.writestr('guest-report.zip', inner.getvalue())


class RendererReportTests(unittest.TestCase):
    def test_state_changes_exclude_straddling_windows_and_never_align_other_roles(self):
        first, second = frame(1, (50,)), frame(2, (100,))
        third, fourth = frame(3, (1000,)), frame(4, (100, 200, 200))
        fifth = frame(5, (100,))
        fifth['states']['menu'] = fifth['states']['gameplay']
        console = '\n'.join((line(first, report.scene.FRAME_PREFIX), line(state()),
            line(second, report.scene.FRAME_PREFIX), line(window()),
            line(frame(role='presentation'), report.scene.FRAME_PREFIX),
            line(window(role='renderer')), line(state(2, 10)),
            line(third, report.scene.FRAME_PREFIX), line(window(2)),
            line(fourth, report.scene.FRAME_PREFIX), line(window(3)),
            line(frame(6, (100,)), report.scene.FRAME_PREFIX), line(window(4)),
            line(fifth, report.scene.FRAME_PREFIX)))
        result = report.partition_main_windows(console)
        gameplay = result['pure_gameplay_main_frames_by_cap']
        self.assertEqual(set(gameplay), {'10'})
        self.assertEqual(gameplay['10']['reports'], [4, 6])
        measured = gameplay['10']['states']['gameplay']['frame_interval']
        self.assertEqual(measured['count'], 4)
        self.assertEqual(measured['mean_ms'], 150)
        self.assertEqual(measured['mean_cadence_hz'], 6.667)
        self.assertEqual(measured['p50_upper_ms'], 100)
        self.assertEqual(measured['p95_upper_ms'], 200)
        coverage = result['main_window_coverage']
        self.assertEqual([row['classification'] for row in coverage['frame']],
                         ['unclassified', 'transition', 'transition', 'stable_cap', 'stable_cap', 'stable_cap'])
        self.assertEqual(len(coverage['frame']), 6)
        self.assertEqual(len(coverage['attribution']), 4)
        self.assertEqual(result['main_attribution_by_stable_cap_game_state_unavailable']['10']['reports'], [3, 4])
        self.assertFalse(coverage['frame'][-1]['pure_gameplay'])

    def test_state_bound_stops_cap_assignments_and_missing_cpu_is_not_zero(self):
        console = '\n'.join(line(state(i, i)) for i in range(1, 65))
        console += '\n' + line(frame(), report.scene.FRAME_PREFIX)
        result = report.partition_main_windows(console)
        self.assertEqual(result['main_window_coverage']['frame'][0]['classification'], 'state_bound_reached')
        self.assertFalse(result['pure_gameplay_main_frames_by_cap'])
        row = window(); row['thread_cpu_ms'] = None
        stream = report.summarize_attribution([row])['main']
        self.assertIsNone(stream['measured_thread_cpu_ms'])
        self.assertEqual(stream['cpu_windows'], 0)

    def test_attribution_uses_sample_weights_and_bucket_upper_percentiles(self):
        rows = [window(samples=(50,)), window(2, samples=(100, 200, 200))]
        report.validate_attribution(rows)
        value = report.summarize_attribution(rows)['main']['metrics']['gfx_wall']
        self.assertEqual(value['count'], 4)
        self.assertEqual(value['sample_sum_ms'], 550)
        self.assertEqual(value['mean_ms'], 137.5)
        self.assertEqual(value['p50_upper_ms'], 100)
        self.assertEqual(value['p95_upper_ms'], 200)
        overflow = report.summarize_attribution([window(samples=(130000,))])['main']
        self.assertIsNone(overflow['metrics']['gfx_wall']['p95_upper_ms'])
        self.assertNotIn('fps', overflow)

    def test_invalid_role_counts_buckets_sequences_and_nonfinite_metrics_are_rejected(self):
        mutations = [lambda r: r.update(report=2), lambda r: r.update(role='presentation'),
            lambda r: r.update(thread_cpu_ms=True), lambda r: r.update(window_ms=float('nan')),
            lambda r: r.update(callback_counts=[0, 0, 0, -1]),
            lambda r: r['metrics']['gfx_wall'].update(count=3),
            lambda r: r['metrics']['gfx_wall'].update(max_ms=50),
            lambda r: r['metrics']['gfx_wall'].update(mean_ms=1),
            lambda r: r['metrics']['gfx_wall'].update(p95_upper_ms=100),
            lambda r: r['metrics']['gfx_wall'].update(histogram=[True]+[0]*21),
            lambda r: r['metrics'].update(swap_wall=r['metrics']['gfx_wall']),
            lambda r: r['metrics'].pop('backpressure_wall'),
            lambda r: r.update(bucket_upper_ms=[15]+list(report.scene.BOUNDS[1:]))]
        for mutate in mutations:
            row = window(); mutate(row)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                report.validate_attribution([row])
        for rows in ([window(), window()], [state(2)], [state(cap=True)]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                report.validate_attribution(rows)
        with self.assertRaises(ValueError):
            report.scene.records(report.PREFIX+'{"format":1,"format":1}', report.PREFIX, report.MAX_RECORDS)
        with self.assertRaises(ValueError):
            report.scene.records('\n'.join(line(state()) for _ in range(report.MAX_RECORDS + 1)), report.PREFIX, report.MAX_RECORDS)

    def test_selected_gpu_and_prerequisite_receipts_cannot_validate_actual_software_game(self):
        profile = {'requested': 'turnip', 'selected': 'turnip', 'state': 'selected_after_probes',
            'vulkan_probe': {'native_gpu_executed': True}, 'wine_gl_probe': {'zink_nonsoftware': True},
            'game_rendering_validated': True, 'physical_fps_improvement_validated': True}
        guest = {'client_gpu_profile': profile,
            'graphics_observation': {'renderer': 'llvmpipe (LLVM 15)', 'renderer_classification': 'software'}}
        result = report.gpu_summary(guest)
        self.assertEqual(result['selected_environment'], 'turnip')
        self.assertTrue(result['software_renderer_observed'])
        self.assertTrue(result['gpu_selected_but_actual_game_software_observed'])
        self.assertFalse(result['hardware_acceleration_validated_by_this_analysis'])
        self.assertFalse(result['physical_fps_improvement_validated_by_this_analysis'])
        guest['client_gpu_profile'] = dict(profile, selected='software', state='software_fallback', fallback_reason='probe rejected')
        self.assertEqual(report.gpu_summary(guest)['fallback_reason'], 'probe rejected')
        self.assertTrue(report.gpu_summary(guest)['requested_selected_differ'])
        guest['client_gpu_profile_attempts'] = [profile, guest['client_gpu_profile']]
        self.assertEqual(len(report.gpu_summary(guest)['bounded_attempt_receipts']), 2)
        guest['graphics_observation'] = {'renderer': 'zink Adreno 740', 'renderer_classification': 'unknown'}
        self.assertFalse(report.gpu_summary(guest)['hardware_acceleration_validated_by_this_analysis'])
        self.assertFalse(report.gpu_summary({})['profile_receipt_present'])
        self.assertIsNone(report.gpu_summary({})['software_renderer_observed'])
        for renderer in ('zink Vulkan (SwiftShader Device)', 'GDI Generic', 'software rasterizer'):
            with self.subTest(renderer=renderer):
                self.assertTrue(report.gpu_summary({'graphics_observation': {'renderer': renderer}})['software_renderer_observed'])
        for bad in ([profile] * 5, [True], {}):
            with self.subTest(attempts=bad), self.assertRaises(ValueError):
                report.gpu_summary({'client_gpu_profile_attempts': bad})

    def test_complete_outer_zip_retains_failed_strict_save_capture_and_separate_streams(self):
        android = {'app_version': '0.13.20', 'passed': False, 'character_reopen_verified': False,
            'decoded_frame_count': 1000, 'android_capture_diagnostics': {'native_fps_measurement': False,
                'encoding_wall_ms': {'sum': 200, 'maximum': 100, 'mean': 100}}}
        failure = {'status': 'failed', 'save_verified': False, 'save_acceptance_changed': False,
            'power_delta': {'deleted_uniqueids': [680838905], 'before_power_count': 16, 'after_power_count': 15}}
        guest = {'passed': False, 'failures': ['Committed existing character rows changed after reopen: powers'],
            'character_reopen': {'verified': False, 'save_comparison_failure': failure}}
        console = '\n'.join((line(state()), line(frame(), report.scene.FRAME_PREFIX),
            line(frame(2, (100,)), report.scene.FRAME_PREFIX), line(window()),
            line(window(role='renderer')), line(frame(role='presentation'), report.scene.FRAME_PREFIX)))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'support.zip'; support(path, console, android=android, guest=guest)
            value = report.analyze(path)
        self.assertEqual(value['strict_save_result']['save_comparison_failure'], failure)
        self.assertFalse(value['strict_save_result']['analysis_changes_save_acceptance'])
        self.assertEqual(value['android_capture_diagnostics'], android['android_capture_diagnostics'])
        self.assertEqual(set(value['renderer_attribution_all_game_states_unaligned']), {'main', 'renderer'})
        self.assertEqual(value['native_frames_all_caps_and_game_states']['presentation']['reports'], 1)
        self.assertIsNone(value['startup']['measured_game_fps'])
        self.assertEqual(value['pure_gameplay_main_frames_by_cap']['30']['reports'], [2])

    def test_complete_zip_rejects_duplicate_members_metadata_keys_and_corrupt_frame_metrics(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'support.zip'; support(path, line(window()))
            with zipfile.ZipFile(path, 'a') as archive, warnings.catch_warnings():
                warnings.simplefilter('ignore'); archive.writestr('android-client-report.json', '{}')
            with self.assertRaises(ValueError): report.analyze(path)
            for raw in ('{"passed":false,"passed":true}', '{"timing":NaN}'):
                with self.subTest(raw=raw), self.assertRaises(ValueError): report.strict_json(raw)
            bad = frame(); bad['states']['gameplay']['frame_interval']['mean_ms'] = 1
            support(path, line(bad, report.scene.FRAME_PREFIX))
            with self.assertRaises(ValueError): report.analyze(path)
            support(path, line(window()) + 'interleaved output')
            with self.assertRaises(ValueError): report.analyze(path)
            with zipfile.ZipFile(path) as archive:
                with self.assertRaises(ValueError): report.thor.read_member(archive, 'guest-report.zip', 1)

    def test_gpu_failure_before_game_has_no_console_or_measured_fps_but_retains_reason(self):
        guest = {'passed': False, 'failures': ['Private GPU probe prefix shutdown could not be proved'],
            'client_gpu_profile': {'requested': 'turnip', 'selected': None,
                'state': 'unsafe_probe_cleanup', 'probe_cleanup_safe': False}}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'support.zip'; support(path, None, guest=guest)
            value = report.analyze(path)
        self.assertFalse(value['client_console_present'])
        self.assertFalse(value['native_frame_instrumentation_present'])
        self.assertFalse(value['native_renderer_attribution_present'])
        self.assertFalse(value['pure_gameplay_main_frames_by_cap'])
        self.assertIsNone(value['startup']['measured_game_fps'])
        self.assertEqual(value['strict_save_result']['failures'], guest['failures'])
        gpu = value['gpu_profile_and_actual_backend']
        self.assertEqual(gpu['prerequisite_state'], 'unsafe_probe_cleanup')
        self.assertIsNone(gpu['software_renderer_observed'])
        self.assertFalse(gpu['hardware_acceleration_validated_by_this_analysis'])

    def test_cli_output_matches_stdout_and_cannot_write_success_for_bad_input(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'support.zip'; support(path, line(state()))
            script = Path(report.__file__)
            stdout = subprocess.run([sys.executable, str(script), str(path)], check=True, capture_output=True, text=True)
            output = Path(temp) / 'nested' / 'report.json'
            subprocess.run([sys.executable, str(script), str(path), '--output', str(output)], check=True, capture_output=True)
            self.assertEqual(output.read_text(), stdout.stdout)
            previous = output.read_bytes()
            support(path, line(window(index=2)))
            result = subprocess.run([sys.executable, str(script), str(path), '--output', str(output)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_bytes(), previous)


if __name__ == '__main__':
    unittest.main()
