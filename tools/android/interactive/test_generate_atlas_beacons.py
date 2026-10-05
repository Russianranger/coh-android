"""Reject incomplete graph, CRC and native route evidence before packaging."""
import struct
import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import generate_atlas_beacons as generator


class AtlasNativeEvidenceTests(unittest.TestCase):
    MARKER = b'COH_ATLAS_BEACON_NATIVE_V1 crc=0x10203040 combat=2000 connected=1900 ground=5000 raised=100 blocks=100 paths=32\n'

    def test_valid_bounded_native_receipt_shape(self):
        value = generator.native_evidence(self.MARKER, struct.pack('<iII',9,1767225600,0x10203040))
        self.assertEqual(value['native_pathfinder_successes'],32)
        self.assertEqual(value['full_world_crc'],'0x10203040')

    def test_missing_duplicate_or_low_connection_witness_is_rejected(self):
        for raw in (b'', self.MARKER*2, self.MARKER.replace(b'ground=5000',b'ground=0'),
                    self.MARKER.replace(b'paths=32',b'paths=0'),
                    self.MARKER.replace(b'connected=1900',b'connected=2001')):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    generator.native_evidence(raw,struct.pack('<iII',9,1767225600,0x10203040))

    def test_date_crc_version_and_size_must_match_native_loaded_world(self):
        for date in (b'bad',struct.pack('<iII',8,1767225600,0x10203040),
                     struct.pack('<iII',9,1767225600,0x10203041)):
            with self.subTest(date=date):
                with self.assertRaises(ValueError): generator.native_evidence(self.MARKER,date)

    def test_owned_roles_remove_progress_request_instead_of_setting_it_empty(self):
        for request in ('', 'C:/android-observer.map'):
            value = generator.role_environment({'PATH': 'owned-path', 'COH_WINE_MAP_PROGRESS': request,
                'COH_CLIENT_DEPENDENCY_PRELOAD': '1', 'COH_MANUAL_ATLAS_DB': '1',
                'COH_WINE_GAME_LISTENERS': '1'})
            self.assertEqual(value, {'PATH': 'owned-path'})

    def test_failure_receipt_retains_exit_status_and_only_bounded_role_tail(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary)
            (evidence/'master.log').write_bytes(b'EXCLUDED_PREFIX' + b'x'*9000 + b'FINAL_NATIVE_FAILURE')
            process = SimpleNamespace(returncode=3221225477, poll=lambda: 3221225477)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                generator.record_role_failure(evidence, {'master': process},
                    {'master': ['C:/owned/AtlasBeaconGenerator.exe', '-beaconmasterserver']},
                    ValueError('Native role startup failed: master'))
            report = json.loads((evidence/'native-role-failure.json').read_bytes())
            self.assertTrue(report['cleanup_complete'])
            self.assertEqual(report['roles']['master']['windows_exit_hex'], '0xc0000005')
            self.assertNotIn('EXCLUDED_PREFIX', output.getvalue())
            self.assertIn('FINAL_NATIVE_FAILURE', output.getvalue())
            self.assertLess(len(output.getvalue()), generator.MAX_FAILURE_TAIL + 200)


if __name__ == '__main__': unittest.main()
