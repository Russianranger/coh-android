"""Host evidence admission and ownership regressions for actual Game execution."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import qualify_native_client_startup as q

class AdmissionTests(unittest.TestCase):
    def test_native_RGB_crop_preserves_raw_and_nearest_scaled_pixel_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); source = root / 'source.ppm'; target = root / 'crop.ppm'
            pixels = bytes(range(256)) * (320 * 240 * 3 // 256)
            source.write_bytes(b'P6\n320 240\n255\n' + pixels); before = q.pin(source)
            value = q.login_crop(source, target); self.assertEqual(q.pin(source), before)
            self.assertFalse(value['native_pixels_or_UI_changed'])
            self.assertEqual(value['crop_xyxy'], [220, 68, 316, 178])
            raw = target.read_bytes(); offset = raw.index(b'\n255\n') + 5
            first = pixels[(68 * 320 + 220) * 3:(68 * 320 + 220) * 3 + 3]
            self.assertEqual(raw[offset:offset + 12], first * 4)

    def test_RGB_capture_malformed_truncated_or_oversized_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); source = root / 'source.ppm'
            for raw in (b'not a PPM', b'P6\n320 240\n255\nshort', b'P6\n9999 9999\n255\n'):
                source.write_bytes(raw)
                with self.assertRaises(ValueError): q.login_crop(source, root / 'crop.ppm')

    def test_login_OCR_requires_actual_positive_crop_and_retains_negative_full_frame(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); source = root / 'source.ppm'
            source.write_bytes(b'P6\n320 240\n255\n' + b'\0' * (320 * 240 * 3))
            executable = root / 'tesseract'; executable.write_bytes(b'owned OCR tool')
            tool = {'resolved': str(executable), 'resolved_pin': q.pin(executable), 'invocation': str(executable)}
            results = [subprocess.CompletedProcess([], 0, b'unrelated artwork', b''),
                       subprocess.CompletedProcess([], 0, b'Remember Account Name\nPASSWORD', b'')]
            with patch.object(q.subprocess, 'run', side_effect=results) as run:
                value = q.observe_login_text(source, tool, root, 'startup')
            self.assertEqual(run.call_count, 2); self.assertTrue(value['login_text_observed'])
            self.assertFalse(value['attempts'][0]['login_text_observed'])
            self.assertFalse(value['UI_input_sent']); self.assertFalse(value['graphics_quality_changed'])
            self.assertEqual((root / 'startup-ocr-full-11.txt').read_bytes(), b'unrelated artwork')

    def test_missing_login_OCR_or_failed_OCR_cannot_be_promoted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); source = root / 'source.ppm'
            source.write_bytes(b'P6\n320 240\n255\n' + b'\0' * (320 * 240 * 3))
            executable = root / 'tesseract'; executable.write_bytes(b'owned OCR tool')
            tool = {'resolved': str(executable), 'resolved_pin': q.pin(executable), 'invocation': str(executable)}
            with patch.object(q.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, b'Account Password', b'failed')):
                self.assertFalse(q.observe_login_text(source, tool, root, 'failed')['login_text_observed'])
            with patch.object(q.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, b'artwork and settings', b'')):
                self.assertFalse(q.observe_login_text(source, tool, root, 'missing')['login_text_observed'])

    def probe(self, row, returncode=0):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            raw = ('COH_CLIENT_PROBE_V1 ' + json.dumps(row) + '\n').encode()
            with patch.object(q, 'pin', return_value=q.CLIENT_PROBE), patch.object(q.subprocess, 'run',
                    return_value=subprocess.CompletedProcess([], returncode, raw, b'')):
                return q.native_probe(directory, {}, '/usr/bin/wine', directory)

    def test_actual_PE32_WGL_probe_requires_renderer_context_readback(self):
        row = {'status': 'passed', 'pointer_bits': 32, 'failure_stage': '', 'gl': {'renderer_class': 'software'},
               'render': {'textured_quad_verified': True, 'samples_verified': 4, 'swap_buffers': True}}
        result = self.probe(row)
        self.assertTrue(result['outside_Game_timing']); self.assertTrue(result['may_warm_driver_and_prefix'])

    def test_native_probe_rejects_context_readback_or_software_mismatch(self):
        base = {'status': 'passed', 'pointer_bits': 32, 'failure_stage': '', 'gl': {'renderer_class': 'software'},
                'render': {'textured_quad_verified': True, 'samples_verified': 4, 'swap_buffers': True}}
        for label in ('context', 'readback', 'renderer', 'pointer_bits'):
            with self.subTest(label=label):
                row = json.loads(json.dumps(base))
                if label == 'context': row.update(status='failed', failure_stage='wgl_context')
                elif label == 'readback': row['render']['samples_verified'] = 0
                elif label == 'renderer': row['gl']['renderer_class'] = 'hardware'
                else: row['pointer_bits'] = 64
                with self.assertRaises(ValueError): self.probe(row)

    def test_exact_cg_object_row_is_not_a_compile_claim(self):
        result = q.parse_cg('COH_NATIVE_CG_PROFILE_V1 kind=2 input_token=abcdef01 success=1 clock_valid=1 create_us=54 driver_load_called=1 driver_load_us=91\n')
        self.assertEqual((result['source_count'], result['object_count'], result['create_us'], result['driver_load_us']), (0, 1, 54, 91))
        self.assertTrue(result['object_does_not_prove_gpu_driver_cache_hit'])

    def test_cg_source_and_object_rows_keep_driver_scope(self):
        row = 'COH_NATIVE_CG_PROFILE_V1 kind={} input_token=12345678 success=1 clock_valid=1 create_us=3 driver_load_called=0 driver_load_us=0\n'
        result = q.parse_cg(row.format(1) + row.format(2))
        self.assertEqual(result['source_count'], 1)
        self.assertEqual(result['object_count'], 1)

    def test_cg_bad_clock_unknown_kind_duplicate_field_rejected(self):
        row = 'COH_NATIVE_CG_PROFILE_V1 kind=2 input_token=abcdef01 success=1 clock_valid=1 create_us=54 driver_load_called=1 driver_load_us=91\n'
        for changed in (row.replace('clock_valid=1', 'clock_valid=0'), row.replace('kind=2', 'kind=7'),
                        row.replace('create_us=54', 'create_us=-1'), row.replace('driver_load_us=91', 'unknown=1')):
            with self.subTest(changed=changed), self.assertRaises(ValueError): q.parse_cg(changed)

    def test_cg_bounded_rows(self):
        row = 'COH_NATIVE_CG_PROFILE_V1 kind=2 input_token=12345678 success=1 clock_valid=1 create_us=1 driver_load_called=1 driver_load_us=2\n'
        self.assertEqual(len(q.parse_cg(row * 1024)['rows']), 1024)
        with self.assertRaises(ValueError): q.parse_cg(row * 1025)

    def test_preserves_alternative_wrapper_invocation_and_pins_real_binary(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); actual = root / 'real-wine'; actual.write_bytes(b'actual executable')
            alternative = root / 'wine'; alternative.symlink_to(actual)
            with patch.object(q.shutil, 'which', return_value=str(alternative)):
                tool = q.binary_tool('wine')
            self.assertEqual(tool['invocation'], str(alternative))
            self.assertEqual(tool['resolved'], str(actual))
            self.assertEqual(tool['resolved_pin'], q.pin(actual))

    def test_missing_tool_refused(self):
        with patch.object(q.shutil, 'which', return_value=None), self.assertRaises(ValueError): q.binary_tool('wine')

    def test_private_input_pin_refuses_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); actual = root / 'actual'; actual.write_bytes(b'x')
            link = root / 'link'; link.symlink_to(actual)
            with self.assertRaises(ValueError): q.pin(link)

    def registry(self, delete, query):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(q.subprocess, 'run', side_effect=(delete, query)):
                return q.registry_empty('/usr/bin/wine', {'WINEPREFIX': '/private/prefix'}, Path(temporary))

    def test_existing_progress_deleted_and_query_must_be_absent(self):
        deleted = subprocess.CompletedProcess([], 0, b'The operation completed successfully\n', b'')
        absent = subprocess.CompletedProcess([], 1, b'reg: Unable to find the specified registry key\n', b'')
        result = self.registry(deleted, absent)
        self.assertEqual([r['returncode'] for r in result], [0, 1])

    def test_already_absent_progress_accepted_with_explicit_wine_diagnostic(self):
        absent = subprocess.CompletedProcess([], 1, b'reg: Unable to find the specified registry key\n', b'')
        self.assertEqual(len(self.registry(absent, absent)), 2)

    def test_reset_access_failure_refused(self):
        bad = subprocess.CompletedProcess([], 1, b'', b'Access denied\n')
        absent = subprocess.CompletedProcess([], 1, b'not found\n', b'')
        with self.assertRaises(ValueError): self.registry(bad, absent)

    def test_stale_mainloop_progress_refused(self):
        deleted = subprocess.CompletedProcess([], 0, b'', b'')
        present = subprocess.CompletedProcess([], 0, b'GameProgress REG_SZ game_mainLoop\n', b'')
        with self.assertRaises(ValueError): self.registry(deleted, present)

    def test_absent_query_cannot_report_success_or_unclassified_error(self):
        deleted = subprocess.CompletedProcess([], 0, b'', b'')
        for query in (subprocess.CompletedProcess([], 0, b'', b''), subprocess.CompletedProcess([], 1, b'Other error', b'')):
            with self.subTest(query=query), self.assertRaises(ValueError): self.registry(deleted, query)

    def test_mutated_added_removed_native_bins_are_reported(self):
        a = {'a.bin': {'bytes': 1, 'sha256': 'a'}, 'b.bin': {'bytes': 2, 'sha256': 'b'}}
        b = {'a.bin': {'bytes': 1, 'sha256': 'c'}, 'c.bin': {'bytes': 2, 'sha256': 'd'}}
        self.assertEqual([r['path'] for r in q.cache_delta(a, b)], ['a.bin', 'b.bin', 'c.bin'])
        self.assertIsNone(q.cache_delta(a, b)[1]['after'])
        self.assertIsNone(q.cache_delta(a, b)[2]['before'])

    def test_public_prefix_stop_refused_before_any_native_signal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); prefix = root / 'prefix'; prefix.mkdir(mode=0o755)
            with patch.object(q.subprocess, 'run') as run, self.assertRaises(ValueError):
                q.stop_prefix(prefix, {}, {}, root)
            run.assert_not_called()

    def test_changed_host_wineserver_refused_before_stop(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); prefix = root / 'prefix'; prefix.mkdir(mode=0o700)
            executable = root / 'wineserver'; executable.write_bytes(b'original'); saved = q.pin(executable)
            executable.write_bytes(b'changed')
            with patch.object(q.subprocess, 'run') as run, self.assertRaises(ValueError):
                q.stop_prefix(prefix, {}, {'resolved': str(executable), 'resolved_pin': saved}, root)
            run.assert_not_called()

    def test_owned_prefix_cleanup_has_exact_prefix_and_no_game_normal_exit_claim(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); prefix = root / 'prefix'; prefix.mkdir(mode=0o700)
            executable = root / 'wineserver'; executable.write_bytes(b'owned wine server')
            tool = {'resolved': str(executable), 'resolved_pin': q.pin(executable), 'invocation': '/usr/bin/wineserver'}
            env = {'WINEPREFIX': str(prefix)}
            results = [subprocess.CompletedProcess([], 0, b'', b''), subprocess.CompletedProcess([], 0, b'', b'')]
            with patch.object(q.subprocess, 'run', side_effect=results) as run, patch.object(q, 'process_census', return_value=[]):
                receipt = q.stop_prefix(prefix, env, tool, root)
            self.assertEqual([call.args[0] for call in run.call_args_list], [['/usr/bin/wineserver', '-k'], ['/usr/bin/wineserver', '-w']])
            self.assertTrue(all(call.kwargs['env'] == env for call in run.call_args_list))
            self.assertTrue(receipt['passed']); self.assertFalse(receipt['normal_game_exit_claimed'])

    def stop_fixture(self, root):
        prefix = root / 'prefix'; prefix.mkdir(mode=0o700)
        executable = root / 'wineserver'; executable.write_bytes(b'owned wine server')
        tool = {'resolved': str(executable), 'resolved_pin': q.pin(executable), 'invocation': '/usr/bin/wineserver'}
        return prefix, tool, {'WINEPREFIX': str(prefix)}

    def test_held_native_launcher_reaped_before_absence_census(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); prefix, tool, env = self.stop_fixture(root)
            process = subprocess.Popen([sys.executable, '-c', 'pass'])
            def census(_):
                self.assertIsNotNone(process.returncode)
                return []
            try:
                with patch.object(q.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, b'', b'')), \
                     patch.object(q, 'process_census', side_effect=census):
                    value = q.stop_prefix(prefix, env, tool, root, owned_process=process)
                self.assertEqual(value['held_launch_Popen_reaped_before_census']['pid'], process.pid)
                self.assertEqual(value['held_launch_Popen_reaped_before_census']['returncode'], 0)
                self.assertFalse(value['held_launch_Popen_reaped_before_census']['additional_signal_sent'])
            finally: process.wait(timeout=10)

    def test_unreadable_dying_Wine_waits_without_signal_until_actual_absence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); prefix, tool, env = self.stop_fixture(root)
            with patch.object(q.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, b'', b'')) as run, \
                 patch.object(q, 'process_census', side_effect=[q.UnreadableWineProcess(9999, 'wineserver'), []]), \
                 patch.object(q.time, 'sleep'):
                value = q.stop_prefix(prefix, env, tool, root)
            self.assertEqual(run.call_count, 2); self.assertTrue(value['passed'])
            self.assertFalse(value['census_observations'][0]['absence_claimed'])
            self.assertEqual(value['census_observations'][-1]['exact_prefix_processes'], [])

    def test_live_or_persistently_unreadable_Wine_refused_after_bounded_wait(self):
        for census in (q.UnreadableWineProcess(9999, 'wineserver'), [{'pid': 1234, 'name': 'wine'}]):
            with self.subTest(census=census), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); prefix, tool, env = self.stop_fixture(root)
                with patch.object(q.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, b'', b'')) as run, \
                     patch.object(q, 'process_census', side_effect=census if isinstance(census, Exception) else None,
                                  return_value=census if not isinstance(census, Exception) else None), \
                     patch.object(q.time, 'monotonic', side_effect=[0, 11]):
                    with self.assertRaisesRegex(ValueError, 'unreadable or live'): q.stop_prefix(prefix, env, tool, root)
                self.assertEqual(run.call_count, 2); self.assertTrue((root / 'owned-prefix-census.json').is_file())

    def test_prefix_replacement_cannot_wait_or_claim_other_prefix_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); prefix, tool, env = self.stop_fixture(root)
            def stopped(*args, **kwargs):
                prefix.rename(root / 'original-prefix'); prefix.mkdir(mode=0o700)
                return subprocess.CompletedProcess([], 0, b'', b'')
            with patch.object(q.subprocess, 'run', side_effect=stopped) as run:
                with self.assertRaisesRegex(ValueError, 'Held owned prefix identity changed'): q.stop_prefix(prefix, env, tool, root)
            self.assertEqual(run.call_count, 1)

    def test_wineboot_timeout_stops_partial_prefix_and_retains_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); work = root / 'work'; work.mkdir(); assets = root / 'assets'; assets.mkdir()
            fixture = root / 'fixture.json'
            game = {'bytes': 1, 'sha256': q.GAME_SHA}
            fixture.write_text(json.dumps({'role': 'complete_public_036_native_client_host_fixture', 'status': 'prepared',
                'donor_apk': q.APK, 'donor_source_commit': q.SOURCE, 'work': str(work), 'assets': str(assets),
                'game': game, 'actual_client_worktree': {}, 'texture_header_environment': {}, 'source_script': {}}))
            args = SimpleNamespace(fixture=fixture, prefix=root / 'prefix', output=root / 'evidence', native_role='retained',
                                   native=None, timeout_seconds=60)
            client = SimpleNamespace(__file__=str(assets / 'client_startup_diagnostic.py'))
            def file_pin(path):
                if Path(path).name == 'CityOfHeroes.exe': return game
                if Path(path).name == 'client-launcher.exe': return {'bytes': 1, 'sha256': q.LAUNCHER_SHA}
                return {'bytes': 1, 'sha256': 'a' * 64}
            with patch.object(q, 'pin', side_effect=file_pin), patch.object(q, 'binary_tool', return_value={'invocation': '/usr/bin/wine'}), \
                 patch.object(q.importlib, 'import_module', return_value=client), patch.dict(q.os.environ, {'DISPLAY': ':91'}), \
                 patch.object(q.subprocess, 'run', side_effect=subprocess.TimeoutExpired(['wineboot'], 180)), \
                 patch.object(q, 'stop_prefix', return_value={'passed': True}) as stop:
                with self.assertRaisesRegex(ValueError, 'failure/cleanup evidence retained'): q.qualify(args)
            self.assertEqual(stop.call_count, 1)
            self.assertEqual(stop.call_args.args[0], args.prefix)
            self.assertEqual(stop.call_args.args[1]['WINEPREFIX'], str(args.prefix))
            receipt = json.loads((args.output / 'native-client-startup-qualification.json').read_text())
            self.assertEqual(receipt['status'], 'failed')
            self.assertEqual(receipt['failure']['type'], 'TimeoutExpired')
            self.assertTrue(receipt['final_cleanup']['passed'])

    def test_registry_and_X_observer_prelaunch_failures_stop_prefix_and_report(self):
        for phase in ('registry', 'observer'):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); work = root / 'work'; work.mkdir(); prefix = root / 'prefix'; prefix.mkdir(mode=0o700)
                output = root / 'output'; output.mkdir()
                args = SimpleNamespace(native_role='retained', timeout_seconds=60)
                fixture = {'assets': str(root / 'assets')}
                env = {'DISPLAY': ':92', 'WINEPREFIX': str(prefix), 'COH_CLIENT_GRAPHICS_PROFILE': 'performance'}
                tools = {'wine': {'invocation': '/usr/bin/wine'}, 'wineserver': {}}
                client = SimpleNamespace(XObserver=lambda _: (_ for _ in ()).throw(ValueError('observer failed')))
                registry_effect = ValueError('registry failed') if phase == 'registry' else None
                with patch.object(q, 'pin', return_value={'bytes': 1, 'sha256': 'a' * 64}), \
                     patch.object(q, 'registry_empty', side_effect=registry_effect), patch.object(q, 'cache_snapshot', return_value={}), \
                     patch.object(q, 'stop_prefix', return_value={'passed': True}) as stop:
                    with self.assertRaisesRegex(ValueError, 'current evidence retained'):
                        q.launch_case(args, fixture, client, work, env, tools, output, 'failed-prelaunch')
                self.assertEqual(stop.call_count, 1)
                receipt = json.loads((output / 'failed-prelaunch' / 'native-client-phase.json').read_text())
                self.assertEqual(receipt['status'], 'failed')
                self.assertEqual(receipt['failure']['message'], phase + ' failed')
                self.assertFalse(receipt['native_game_executed'])
                self.assertTrue(receipt['cleanup']['passed'])

if __name__ == '__main__': unittest.main()
