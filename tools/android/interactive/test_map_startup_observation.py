"""Bounded actual activation observation never grants gameplay acceptance."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import local_character_server as server
import native_map_startup_contract as startup


class MapStartupObservationTests(unittest.TestCase):
    def line(self, **changes):
        row = dict(opened=5878, certified=5878, fallback=0, crypto_failed=0, raw_bytes=88380730,
            hash_us=123, stock_us=0, skipped_rot_keys=42, skipped_pos_keys=51,
            scanned_rot_keys=0, scanned_pos_keys=0)
        row.update(changes)
        return ('COH_ANIM_CERT_V1 schema=1 pack=' + startup.PACK_SHA256 + ' ' +
            ' '.join(name + '=' + str(row[name]) for name in server.ANIMATION_COUNTER_KEYS) + '\n').encode()

    def test_missing_and_split_line_remain_unknown_until_complete_exact_console_row(self):
        state = {}; raw = bytearray(b'ordinary stock loading\n')
        self.assertFalse(server.observe_animation_counter_bytes(state, raw))
        self.assertNotIn('observation', state)
        row = self.line(); raw.extend(row[:80])
        self.assertFalse(server.observe_animation_counter_bytes(state, raw))
        raw.extend(row[80:]); self.assertTrue(server.observe_animation_counter_bytes(state, raw))
        self.assertTrue(state['observation']['observed'])
        self.assertEqual(state['observation']['certified'], 5878)
        self.assertEqual(state['observation']['counter_rows_observed'], 1)
        self.assertFalse(server.observe_animation_counter_bytes(state, raw))
        self.assertEqual(state['observation']['counter_rows_observed'], 1)

    def test_wrong_pack_numeric_overflow_and_impossible_counters_grant_no_activation(self):
        for raw in (self.line().replace(startup.PACK_SHA256.encode(), b'f' * 64),
                    self.line(opened=2**64), self.line(certified=9999),
                    self.line().replace(b'opened=5878', b'opened=' + b'9' * 10000)):
            with self.subTest(raw_length=len(raw)):
                state = {}; self.assertFalse(server.observe_animation_counter_bytes(state, raw))
                self.assertNotIn('observation', state)
                self.assertLessEqual(len(state['tail']), 4096)

    def test_truncated_console_explicitly_removes_activation_authority(self):
        state = {}; server.observe_animation_counter_bytes(state, self.line())
        self.assertTrue(server.observe_animation_counter_bytes(state, b''))
        self.assertEqual(state['observation']['status'], 'unknown_console_truncated')
        self.assertFalse(state['observation']['observed'])

    def test_counter_receipt_bounds_rows_and_retains_only_last_partial_line(self):
        state = {}; self.assertTrue(server.observe_animation_counter_bytes(state, self.line() * 100))
        self.assertEqual(state['rows'], 64)
        self.assertEqual(state['observation']['counter_rows_observed'], 64)
        self.assertEqual(state['tail'], b'')

    def fixture(self):
        temporary = tempfile.TemporaryDirectory(prefix='coh-startup-observation-test-')
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name); runtime = root / 'owned-map'; runtime.mkdir()
        exe = runtime / 'MapServer.exe'; exe.write_bytes(b'exact native Map fixture')
        exe.chmod(0o400)
        fx = runtime / server.server_fx_catalog.TARGET; fx.parent.mkdir(parents=True)
        fx.write_bytes(b'exact projected server FX fixture')
        ctx = SimpleNamespace(state=root, secrets=['do-not-export-secret'], report={
            'status': 'running', 'passed': False, 'scope': 'do-not-export-secret',
            'character_reopen': {'verified': False}})
        value = server.LocalCharacterServer.__new__(server.LocalCharacterServer)
        value.owner = SimpleNamespace(args=SimpleNamespace(session_id='a' * 32))
        value.ctx, value.creation_report = ctx, {}
        value.map_process = None
        value.runtime, value.kings_row_runtime = runtime, runtime
        value.map_package = {'files': {'MapServer.exe': server.server_cache_package.file_pin(exe)}}
        return root, runtime, fx, value

    def test_durable_prepared_receipt_contains_actual_pins_and_keeps_incomplete_acceptance(self):
        root, runtime, fx, value = self.fixture()
        pin = server.server_cache_package.file_pin(fx)
        with mock.patch.object(server.server_fx_catalog, 'PROJECTED', pin):
            value.record_startup_preparation(1, runtime, {'status': 'installed'}, {'installed': True,
                'pigg': {'sha256': 'b' * 64}}, {'status': 'installed', 'input_payload_bytes_hashed': 100}, 8.5, {'geometry': 5.0})
        row = value.creation_report['map_startup_observation']['1']
        self.assertEqual(row['actual_installed_mapserver'], value.map_package['files']['MapServer.exe'])
        self.assertEqual(row['server_fx_provider']['actual_payload'], pin)
        self.assertTrue(row['server_fx_provider']['projected_payload_present'])
        self.assertFalse(row['server_fx_provider']['native_provider_open_observed'])
        self.assertFalse(row['launched']); self.assertFalse(row['native_ready_verified'])
        latest = json.loads((root / 'latest-report.json').read_text())
        self.assertEqual(latest['status'], 'running'); self.assertFalse(latest['passed'])
        self.assertFalse(latest['character_reopen']['verified'])
        self.assertNotIn('do-not-export-secret', (root / 'latest-report.json').read_text())
        self.assertEqual(json.loads((root / 'map-startup-observation.json').read_text())['session_id'], 'a' * 32)

    def test_linked_fx_is_explicitly_unobserved_and_wrong_map_bytes_refuse(self):
        root, runtime, fx, value = self.fixture()
        donor = fx.with_name('other.bin'); fx.rename(donor); fx.symlink_to(donor)
        value.record_startup_preparation(5, runtime, {}, {}, {}, 2, {})
        row = value.creation_report['map_startup_observation']['5']['server_fx_provider']
        self.assertFalse(row['private_owned_regular_provider']); self.assertIsNone(row['actual_payload'])
        exe = runtime / 'MapServer.exe'; exe.chmod(0o600); exe.write_bytes(b'substituted map')
        with self.assertRaisesRegex(server.base.DiagnosticError, 'different installed MapServer'):
            value.record_startup_preparation(1, runtime, {}, {}, {}, 2, {})

    def test_actual_owned_console_counters_and_existing_ready_gate_are_required_independently(self):
        root, runtime, fx, value = self.fixture()
        value.record_startup_preparation(5, runtime, {}, {}, {}, 2, {})
        child = SimpleNamespace(process=SimpleNamespace(pid=456, args=[
            '--chdir=' + str(runtime), server.base.windows_path(runtime / 'MapServer.exe')]), started=100,
                                output=bytearray(self.line()))
        # Real OwnedProcess is identity-hashable; the fake must be too.
        class OwnedChild: pass
        owned_child = OwnedChild(); owned_child.process = child.process
        owned_child.started, owned_child.output = child.started, child.output
        value.maps = {5: {'process': owned_child, 'ready': False, 'launch_utc_ms': 1234}}
        with mock.patch.object(server.time, 'monotonic', return_value=120): value.sample_startup_observation(force=True)
        row = value.creation_report['map_startup_observation']['5']
        self.assertTrue(row['launched']); self.assertEqual(row['launcher_pid'], 456)
        self.assertEqual(row['actual_launched_mapserver'], value.map_package['files']['MapServer.exe'])
        self.assertTrue(row['launch_path_binding_observed'])
        self.assertTrue(row['animation_storage']['native_certificate']['observed'])
        self.assertFalse(row['native_ready_verified'])
        value.maps[5]['ready'] = True
        with mock.patch.object(server.time, 'monotonic', return_value=125): value.sample_startup_observation(force=True)
        self.assertTrue(row['native_ready_verified'])
        self.assertEqual(row['native_ready_elapsed_seconds'], 25)
        self.assertIn('upper_bound', row['native_ready_time_scope'])
        self.assertFalse(json.loads((root / 'latest-report.json').read_text())['passed'])

    def test_post_ready_fx_observation_distinguishes_regenerated_full_bytes_once(self):
        root, runtime, fx, value = self.fixture()
        compact = server.server_cache_package.file_pin(fx)
        with mock.patch.object(server.server_fx_catalog, 'PROJECTED', compact):
            value.record_startup_preparation(1, runtime, {}, {}, {}, 2, {})
            fx.write_bytes(b'new full native FX bytes after startup')
            full = server.server_cache_package.file_pin(fx)
            with mock.patch.object(server.server_fx_catalog, 'BASE', full), \
                    mock.patch.object(server, 'observe_ready_fx_provider', wraps=server.observe_ready_fx_provider) as observe:
                class OwnedChild: pass
                child = OwnedChild(); child.process = SimpleNamespace(pid=456, args=[
                    '--chdir=' + str(runtime), server.base.windows_path(runtime / 'MapServer.exe')])
                child.started, child.output = 100, bytearray()
                value.maps = {1: {'process': child, 'ready': True}}
                value.sample_startup_observation(force=True)
                value.sample_startup_observation(force=True)
                self.assertEqual(observe.call_count, 1)
        row = value.creation_report['map_startup_observation']['1']['server_fx_provider']
        self.assertTrue(row['projected_payload_present'])
        post = row['post_native_ready']
        self.assertTrue(post['observed']); self.assertFalse(post['projected_payload_present'])
        self.assertTrue(post['full_original_payload_present']); self.assertFalse(post['matches_preparation_payload'])
        self.assertEqual(post['payload_bytes_hashed'], full['bytes'])
        self.assertGreaterEqual(post['hash_elapsed_seconds'], 0)
        self.assertFalse(post['native_provider_open_observed'])

    def test_post_ready_optional_missing_linked_owner_or_runtime_change_stays_unknown(self):
        root, runtime, fx, value = self.fixture()
        value.record_startup_preparation(1, runtime, {}, {}, {}, 2, {})
        row = value.creation_report['map_startup_observation']['1']
        original = fx.read_bytes(); fx.unlink()
        missing = server.observe_ready_fx_provider(runtime, row['private_runtime_identity'], None)
        self.assertFalse(missing['observed']); self.assertIsNone(missing['actual_payload'])
        donor = runtime / 'linked-fx.bin'; donor.write_bytes(original); fx.symlink_to(donor)
        linked = server.observe_ready_fx_provider(runtime, row['private_runtime_identity'], None)
        self.assertFalse(linked['observed']); self.assertEqual(linked['payload_bytes_hashed'], 0)
        fx.unlink(); fx.write_bytes(original)
        wrong = dict(row['private_runtime_identity'], uid=row['private_runtime_identity']['uid'] + 1)
        self.assertFalse(server.observe_ready_fx_provider(runtime, wrong, None)['observed'])
        with mock.patch.object(server.server_fx_catalog, '_unchanged_leaf', side_effect=ValueError('changed')):
            self.assertFalse(server.observe_ready_fx_provider(runtime, row['private_runtime_identity'], None)['observed'])
        self.assertFalse(value.ctx.report['passed'])

    def test_observation_write_failure_is_reported_without_upgrading_acceptance(self):
        root, runtime, fx, value = self.fixture()
        (root / 'map-startup-observation.json').symlink_to(root / 'other.json')
        value.record_startup_preparation(1, runtime, {}, {}, {}, 2, {})
        self.assertIn('map_startup_observation_write_failure', value.creation_report)
        self.assertFalse(value.ctx.report['passed'])
        self.assertFalse((root / 'other.json').exists())


if __name__ == '__main__': unittest.main()
