"""Host-only checks for the bounded M3 diagnostics (no Wine/server required)."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import stall_snapshot
import zone_report


class M3DiagnosticsTests(unittest.TestCase):
    def test_snapshot_selects_exact_client_mapping_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = root / 'client'
            proc = root / 'proc'
            proc.mkdir()
            for pid, exe in ((101, client / 'CityOfHeroes.exe'),
                             (102, root / 'other/CityOfHeroes.exe'),
                             (103, client / 'MapServer.exe')):
                task = proc / str(pid)
                task.mkdir()
                (task / 'maps').write_text(f'140000000-140100000 r-xp 00000000 00:01 123 {exe}\n')
            (proc / '104').mkdir()  # process exited before maps could be read
            self.assertEqual(stall_snapshot.client_pids(client, proc), [101])

    def test_full_loading_result_survives_socket_history_and_asset_noise(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'login-driver.json').write_text(json.dumps({
                'sockets': ['x' * 1000] * 40, 'world_rendered': False,
                'zone_load_seconds': 1505, 'loading_brightness': [0.911] * 50,
                'load_samples': [{'seconds': 30 * i, 'stdio_bytes': 1990994 + i} for i in range(50)]}))
            (root / 'armport-game-report.json').write_text(json.dumps({
                'game': {'armport_client': {'connected_on_atlas': True, 'still_connected': False,
                                          'final_status': {'connected': False}}}}))
            (root / 'armport_stdio.txt').write_text(
                'missing texture\n' * 20000 + 'ArmPort zone: 100 groups.begin \n' +
                ''.join(f'ArmPort zone: {i} library.begin file-{i}\n' for i in range(200)) +
                'ArmPort zone: 300 groupfile.loaded atlas\n')
            entries = dict(zone_report.sections(root, root))
            status_text = entries['ArmPort M3 load status']
            self.assertLess(len(status_text), 3700)
            status = json.loads(status_text)
            self.assertFalse(status['world_rendered'])
            self.assertFalse(status['guest']['still_connected'])
            self.assertEqual(len(status['load_samples']), 50)
            self.assertNotIn('sockets', status)
            self.assertIn('groups.begin', entries['ArmPort M3 zone stages'])
            self.assertIn('groupfile.loaded', entries['ArmPort M3 zone stages'])
            self.assertIn('file-199', entries['ArmPort M3 library progress'])
            self.assertLessEqual(len(entries), 8)

    def test_missing_diagnostics_report_unknown_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            entries = dict(zone_report.sections(Path(tmp), Path(tmp)))
            status = json.loads(entries['ArmPort M3 load status'])
            self.assertIsNone(status['guest']['still_connected'])
            self.assertNotIn('world_rendered', status)


if __name__ == '__main__':
    unittest.main()
