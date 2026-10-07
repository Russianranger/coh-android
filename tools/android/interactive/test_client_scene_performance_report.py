"""Reject misleading/corrupt native measurements; retain nested-phase semantics."""
import copy
import json
import unittest

import analyze_client_scene_performance as report


def metric(samples):
    histogram = [0]*len(report.BOUNDS)
    for sample in samples:
        bucket = next((i for i, bound in enumerate(report.BOUNDS) if bound is None or sample <= bound))
        histogram[bucket] += 1
    return {'count': len(samples), 'mean_ms': sum(samples)/len(samples), 'max_ms': max(samples),
            'p50_upper_ms': report.quantile(histogram, 50), 'p95_upper_ms': report.quantile(histogram, 95),
            'over_125ms_count': sum(x > 125 for x in samples),
            'over_200ms_count': sum(x > 200 for x in samples), 'histogram': histogram}


def frame(index=1, samples=(100, 100, 150, 250), role='main'):
    return {'role': role, 'report': index, 'window_ms': 10000, 'thread_cpu_ms': 1700,
            'histogram_upper_ms': list(report.BOUNDS),
            'states': {'gameplay' if role == 'main' else 'unclassified':
                       {'frame_interval' if role == 'main' else 'presentation_interval': metric(samples)}}}


class NativePerformanceReportTests(unittest.TestCase):
    def test_weighted_windows_keep_cadence_histogram_and_stutters_distinct(self):
        result = report.summarize_frames([frame(), frame(2, (100, 100)), frame(role='presentation')])
        main = result['main']['states']['gameplay']['frame_interval']
        self.assertEqual(main['count'], 6)
        self.assertAlmostEqual(main['mean_ms'], 133.333, places=3)
        self.assertEqual(main['mean_cadence_hz'], 7.5)
        self.assertEqual(main['p95_upper_ms'], 250)
        self.assertEqual(main['over_125ms_count'], 2)
        self.assertEqual(main['over_200ms_count'], 1)
        self.assertEqual(result['presentation']['reports'], 1)
        self.assertNotIn('gpu_ms', main)

    def test_corrupt_histograms_roles_sequences_and_nonfinite_numbers_refused(self):
        changes = [lambda r: r.update(report=2), lambda r: r.update(window_ms=float('nan')),
                   lambda r: r.update(thread_cpu_ms=-1), lambda r: r.update(role='gpu'),
                   lambda r: r['states']['gameplay']['frame_interval'].update(count=5),
                   lambda r: r['states']['gameplay']['frame_interval'].update(p95_upper_ms=200),
                   lambda r: r['states']['gameplay']['frame_interval'].update(over_125ms_count=0),
                   lambda r: r['histogram_upper_ms'].__setitem__(0, 15)]
        for mutate in changes:
            with self.subTest(mutate=mutate):
                value = frame(); mutate(value)
                with self.assertRaises(ValueError): report.summarize_frames([value])
        with self.assertRaises(ValueError): report.summarize_frames([frame(), frame()])

    def test_overflow_is_not_a_precise_percentile_or_gpu_completion(self):
        result = report.summarize_frames([frame(samples=(130000,))])
        value = result['main']['states']['gameplay']['frame_interval']
        self.assertIsNone(value['p95_upper_ms'])
        self.assertEqual(value['over_200ms_count'], 1)

    def test_scene_parent_child_are_retained_without_double_count_total(self):
        rows = [{'phase': phase, 'milliseconds': ms, 'success': 1, 'ordinal': index,
                 'clock': 'GetTickCount', 'bound_per_translation_unit': 128}
                for index, (phase, ms) in enumerate((('groups_network_and_processing', 70000),
                                                   ('groups_collision_and_physics', 17000)), 1)]
        result = report.summarize_scene(rows)
        self.assertEqual(result['groups_network_and_processing']['total_ms'], 70000)
        self.assertNotIn('total_scene_ms', result)
        bad = copy.deepcopy(rows); bad[0]['milliseconds'] = -1
        with self.assertRaises(ValueError): report.summarize_scene(bad)

    def test_duplicate_json_keys_interleaving_and_budget_refused(self):
        with self.assertRaises(ValueError):
            report.records(report.FRAME_PREFIX+'{"role":"main","role":"presentation"}', report.FRAME_PREFIX, 240)
        with self.assertRaises(ValueError):
            report.records(report.FRAME_PREFIX+'{"role":"main"}garbage', report.FRAME_PREFIX, 240)
        with self.assertRaises(ValueError):
            report.records('\n'.join(report.FRAME_PREFIX+'{}' for _ in range(241)), report.FRAME_PREFIX, 240)
        value = report.records('[timestamp] '+report.FRAME_PREFIX+json.dumps(frame()), report.FRAME_PREFIX, 240)
        self.assertEqual(len(value), 1)

    def test_scene_ready_uses_timestamped_connection_not_user_selection(self):
        console = '[2026-10-06 18:54:34.894] [INFO] Connecting to MapServer 127.0.0.1'
        guest = {'character_reopen': {'client_ready_evidence':
                 {'utc_ms': 1791312952687, 'loaded_world_assets': True}}}
        value = report.scene_entry(console, guest)
        self.assertEqual(value['client_connect_to_native_ready_seconds'], 77.793)
        guest['character_reopen']['client_ready_evidence']['loaded_world_assets'] = False
        self.assertIsNone(report.scene_entry(console, guest))


if __name__ == '__main__':
    unittest.main()
