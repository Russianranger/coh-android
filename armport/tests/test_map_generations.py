"""Observational launch history; no retirement, native launch or device proof."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'android/guest'))
import character_zoning as zoning

SESSION = 'a' * 32


def owned(root, map_id, pid, launch=1000, output=b'one complete line\n'):
    process = SimpleNamespace(process=SimpleNamespace(pid=pid), output=bytearray(output), overflow=False,
                              text=Mock(return_value=output.decode()))
    return {'process': process, 'progress_path': root / ('map-' + str(map_id) + '-progress.bin'),
            'launch_utc_ms': launch, 'previous': None, 'ready': True}


class GenerationHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.target = self.root / 'evidence'; self.target.mkdir()
        self.history = zoning.MapLaunchHistory(SESSION)

    def test_launch_descriptor_is_immutable_and_resident_return_keeps_identity(self):
        atlas, kings = owned(self.root, 1, 101), owned(self.root, 5, 102)
        first = self.history.observe(1, atlas, 0)
        second = self.history.observe(5, kings, 1)
        with self.assertRaises(TypeError): first['map_id'] = 5
        self.assertIs(self.history.observe(1, atlas, 2), first)
        self.assertIs(self.history.observe(5, kings, 3), second)
        report = self.history.collect(self.target, {1: atlas, 5: kings}, kings['process'], [])
        self.assertEqual([row['launch']['generation'] for row in report['generations']], [1, 2])
        self.assertEqual([row['active_process_reference'] for row in report['generations']], [False, True])
        self.assertTrue(all(row['current_resident'] for row in report['generations']))
        self.assertFalse(report['retirement_enabled'])
        self.assertFalse(report['is_success_proof'])
        self.assertFalse(report['native_process_identity_verified'])

    def test_replacement_launch_keeps_old_history_and_separate_evidence(self):
        old, replacement = owned(self.root, 1, 101), owned(self.root, 1, 101, launch=2000)
        self.history.observe(1, old, 0)
        self.history.observe(1, replacement, 2)
        report = self.history.collect(self.target, {1: replacement}, replacement['process'], [])
        before, after = report['generations']
        self.assertFalse(before['current_resident']); self.assertFalse(before['active_process_reference'])
        self.assertTrue(after['current_resident']); self.assertTrue(after['active_process_reference'])
        self.assertNotEqual(before['launch']['console_member'], after['launch']['console_member'])
        self.assertEqual(len(list(self.target.glob('*console-tail.txt'))), 2)
        # Reused Linux PID does not become an ownership or process-exit proof.
        self.assertEqual(before['launch']['launcher_pid'], after['launch']['launcher_pid'])
        self.assertFalse(report['native_process_identity_verified'])

    def test_rebinding_one_owned_launcher_does_not_rewrite_original_descriptor(self):
        row = owned(self.root, 1, 101)
        original = self.history.observe(1, row, 0)
        changed = dict(row, progress_path=self.root / 'foreign' / row['progress_path'].name)
        self.assertIsNone(self.history.observe(1, changed, 1))
        self.assertIsNone(self.history.observe(5, row, 1))
        row['process'].process = SimpleNamespace(pid=102)
        self.assertIsNone(self.history.observe(1, row, 1))
        self.assertEqual(original['map_id'], 1)
        self.assertEqual(original['launcher_pid'], 101)
        report = self.history.collect(self.target, {}, None, [])
        self.assertEqual(len(report['generations']), 1)
        self.assertFalse(report['complete'])
        self.assertEqual(report['observation_errors']['invalid_or_changed_launch_observation'], 3)
        self.assertFalse(report['generations'][0]['console']['available'])
        self.assertFalse((self.target / original['console_member']).exists())

    def test_replaced_capture_cannot_be_exported_under_old_launch(self):
        row = owned(self.root, 1, 101)
        record = self.history.observe(1, row, 0)
        row['process'].output = bytearray(b'another process\n')
        report = self.history.collect(self.target, {1: row}, row['process'], [])
        self.assertFalse(report['generations'][0]['console']['available'])
        self.assertFalse((self.target / record['console_member']).exists())

    def test_exhaustion_and_malformed_observations_are_diagnostic_only(self):
        for index in range(self.history.LIMIT):
            self.assertIsNotNone(self.history.observe(1, owned(self.root, 1, 100 + index), 0))
        self.assertIsNone(self.history.observe(5, owned(self.root, 5, 200), 1))
        self.assertIsNone(self.history.observe(5, {}, 1))
        report = self.history.collect(self.target, {}, None, [])
        self.assertEqual(len(report['generations']), self.history.LIMIT)
        self.assertEqual(report['omitted_launch_observations'], 1)
        self.assertTrue(report['observation_errors'])
        self.assertFalse(report['complete'])

    def test_console_export_is_a_small_redacted_complete_line_tail(self):
        limit = self.history.CONSOLE_BYTES
        raw = b'x' * (limit * 2) + b'\npassword=hidden\nkeep me\ntrailing password=hidden'
        row = owned(self.root, 5, 101, output=raw)
        self.history.observe(5, row, 0)
        report = self.history.collect(self.target, {5: row}, row['process'], ['hidden'])
        row['process'].text.assert_not_called()
        exported = report['generations'][0]
        text = (self.target / exported['launch']['console_member']).read_text()
        self.assertEqual(text, 'password=[redacted]\nkeep me\n')
        self.assertNotIn('hidden', text)
        self.assertLessEqual(exported['console']['exported_bytes'], limit)
        self.assertGreater(exported['console']['omitted_source_bytes'], limit)
        self.assertFalse(exported['console']['complete'])

    def test_existing_or_linked_generation_export_is_not_overwritten(self):
        row = owned(self.root, 1, 101)
        record = self.history.observe(1, row, 0)
        path = self.target / record['console_member']
        path.write_text('old evidence\n')
        report = self.history.collect(self.target, {1: row}, row['process'], [])
        self.assertEqual(path.read_text(), 'old evidence\n')
        self.assertFalse(report['generations'][0]['console']['available'])
        path.unlink(); outside = self.root / 'outside'; outside.write_text('preserve\n')
        path.symlink_to(outside)
        report = self.history.collect(self.target, {1: row}, row['process'], [])
        self.assertEqual(outside.read_text(), 'preserve\n')
        self.assertFalse(report['complete'])

    def test_multiline_secret_boundary_omits_optional_tail(self):
        row = owned(self.root, 1, 101, output=b'x\nsecret-first\nsecret-last\n')
        record = self.history.observe(1, row, 0)
        with patch.object(self.history, 'CONSOLE_BYTES', 24):
            report = self.history.collect(self.target, {1: row}, row['process'], ['secret-first\nsecret-last'])
        self.assertFalse(report['generations'][0]['console']['available'])
        self.assertFalse((self.target / record['console_member']).exists())

    def test_collector_failure_and_capture_overflow_remain_explicit(self):
        row = owned(self.root, 1, 101)
        self.history.observe(1, row, 0)
        with patch.object(zoning.base, 'private_write', side_effect=OSError('fixture')):
            report = self.history.collect(self.target, {1: row}, row['process'], [])
        self.assertEqual(report['generations'][0]['console'], {'available': False, 'reason': 'OSError'})
        row['process'].overflow = True
        report = self.history.collect(self.target, {1: row}, row['process'], [])
        self.assertTrue(report['generations'][0]['console']['overflow'])
        self.assertFalse(report['complete'])


class ProductionBookkeepingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.ctx = SimpleNamespace(report={}, start=Mock(), secrets=[])
        owner = SimpleNamespace(root=self.root, ctx=self.ctx, wine_env={},
            args=SimpleNamespace(session_id=SESSION, wine='/usr/bin/wine'))
        self.server = zoning.LocalCharacterZoningServer(owner)
        self.server.runtime = self.root
        self.server.map_package = {}
        self.server.prepare_atlas_runtime = Mock(return_value=self.root)
        self.server.prepare_kings_row_runtime = Mock(return_value={
            'runtime': self.root / 'kings', 'graph': {'verified': True, 'map_id': 5}})
        self.server.immediate_event_contract = Mock(return_value=None)

    def atlas(self):
        row = owned(self.root, 1, 101)
        self.server.map_process, self.server.map_progress_path = row['process'], row['progress_path']
        self.server.map_launch_utc_ms = row['launch_utc_ms']
        self.server._remember_active()
        return row

    def spawn(self, map_id, pid):
        row = owned(self.root, map_id, pid)
        self.ctx.start.return_value = row['process']
        with patch.object(zoning.character.game, 'check_game_port'):
            self.server._spawn_map(map_id)
        return self.server.maps[map_id]

    def test_initial_atlas_and_resident_round_trips_do_not_spawn_again(self):
        self.atlas()
        self.server.epoch = 1
        self.spawn(5, 102)
        for epoch, map_id in ((1, 5), (2, 1), (3, 5)):
            self.server.epoch = epoch
            self.server._activate(map_id)
        self.ctx.start.assert_called_once()
        target = self.root / 'evidence'; target.mkdir()
        report = self.server.map_launch_history.collect(target, self.server.maps,
            self.server.map_process, [])
        self.assertEqual([row['launch']['map_id'] for row in report['generations']], [1, 5])
        self.assertFalse(self.server.creation_report['verified'])
        self.assertFalse(self.server.creation_report['committed_sql_verified'])
        self.assertEqual(self.server.maps[5]['progress_path'].name, 'character-zoning-5-progress.bin')
        self.assertEqual(len(list(self.root.glob('*.bin'))), 0)
        argv = self.ctx.start.call_args.args[1]
        self.assertIn('-idleExitTimeout', argv)
        self.assertEqual(argv[argv.index('-idleExitTimeout') + 1], '0')

    def test_saved_kings_initial_launch_is_registered_without_atlas(self):
        self.server.active_map_id = 5
        self.spawn(5, 102)
        self.server._activate(5)
        target = self.root / 'evidence'; target.mkdir()
        report = self.server.map_launch_history.collect(target, self.server.maps,
            self.server.map_process, [])
        self.assertEqual([row['launch']['map_id'] for row in report['generations']], [5])
        self.assertEqual(self.server.active_map_id, 5)

    def test_initial_atlas_readiness_failure_preserves_original_error_and_launch(self):
        row = owned(self.root, 1, 101)
        original_environment = self.server.owner.wine_env
        def failed_start():
            self.server.map_process = row['process']
            self.server.map_progress_path = row['progress_path']
            self.server.map_launch_utc_ms = row['launch_utc_ms']
            raise RuntimeError('original readiness failure')
        with patch.object(zoning.character.LocalCharacterReopenServer, 'start_map', side_effect=failed_start), \
             self.assertRaisesRegex(RuntimeError, 'original readiness failure'):
            self.server.start_map()
        self.assertIs(self.server.owner.wine_env, original_environment)
        self.assertEqual(self.server.maps, {})
        self.assertFalse(self.server.creation_report.get('map_ready', False))
        target = self.root / 'evidence'; target.mkdir()
        report = self.server.map_launch_history.collect(target, self.server.maps,
            self.server.map_process, [])
        self.assertEqual(len(report['generations']), 1)
        self.assertFalse(report['generations'][0]['current_resident'])

    def test_real_collector_keeps_legacy_export_and_reports_optional_failure(self):
        atlas = self.atlas(); self.spawn(5, 102); self.server._activate(5)
        target = self.root / 'evidence'; target.mkdir()
        original = zoning.base.private_write
        def write(path, text):
            if path.name.startswith('character-zoning-generation-'):
                raise OSError('optional history export fixture')
            return original(path, text)
        with patch.object(zoning.character.LocalCharacterReopenServer, 'collect'), \
             patch.object(zoning.base, 'private_write', side_effect=write):
            self.server.collect(target)
        self.assertEqual((target / 'character-zoning-map-1-console.txt').read_text(), 'one complete line\n')
        atlas['process'].text.assert_called_once()
        result = json.loads((target / 'character-zoning.json').read_text())
        self.assertEqual(result['active_console']['archive_member'], 'character-atlas-console.txt')
        self.assertFalse(result['launch_history']['complete'])
        self.assertTrue(all(row['console']['reason'] == 'OSError'
                            for row in result['launch_history']['generations']))
        self.assertFalse(self.server.creation_report['verified'])

    def test_unexpected_optional_collector_error_does_not_fail_legacy_collection(self):
        self.atlas()
        target = self.root / 'evidence'; target.mkdir()
        with patch.object(zoning.character.LocalCharacterReopenServer, 'collect'), \
             patch.object(self.server.map_launch_history, 'collect', side_effect=RuntimeError('fixture')):
            self.server.collect(target)
        result = json.loads((target / 'character-zoning.json').read_text())
        self.assertEqual(result['launch_history']['reason'], 'RuntimeError')
        self.assertFalse(result['launch_history']['available'])
        self.assertFalse(result['launch_history']['is_success_proof'])


if __name__ == '__main__':
    unittest.main()
