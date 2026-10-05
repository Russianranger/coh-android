"""Reject incomplete graph, CRC and native route evidence before packaging."""
import struct
import contextlib
import io
import json
import os
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

    def test_unicode_tail_is_cp1252_safe_and_json_precedes_console_rendering(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary); (evidence/'sentry.log').write_bytes(b'heap \xff\xfe FINAL')
            process = SimpleNamespace(returncode=1, poll=lambda: 1)
            class WindowsConsole(io.StringIO):
                def write(self, value):
                    self_exists = (evidence/'native-role-failure.json').exists()
                    if not self_exists: raise AssertionError('Receipt must precede rendering')
                    value.encode('cp1252', errors='strict')
                    return super().write(value)
            output = WindowsConsole()
            with contextlib.redirect_stdout(output):
                generator.record_role_failure(evidence, {'sentry': process}, {'sentry':['owned.exe']},
                    ValueError('Native role exited'), {'sentry':3221226356})
            report = json.loads((evidence/'native-role-failure.json').read_bytes())
            self.assertEqual(report['roles']['sentry']['windows_exit_before_cleanup'], '0xc0000374')
            self.assertEqual(report['roles']['sentry']['windows_exit_hex'], '0x00000001')
            self.assertIn('FINAL',output.getvalue())

    def test_cold_mirror_shares_readonly_inputs_and_isolates_mutable_native_caches(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); runtime=root/'r'; runtime.mkdir()
            fixtures = {'data/object_library/a.geo':b'exact geometry', 'data/maps/a.txt':b'exact groups',
                        'data/bin/defs.bin':b'private definitions', 'data/geobin/world.bin':b'private geometry cache',
                        'data/server/cache':b'private server cache', 'MapServer.exe':b'owned native'}
            for name, raw in fixtures.items():
                target=runtime/name; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(raw)
            cold=root/'c'; value=generator.mirror_cold_runtime(runtime,cold)
            self.assertTrue(value['created_before_visual_overlay_and_generation'])
            self.assertTrue(os.path.samefile(runtime/'data/object_library/a.geo',cold/'data/object_library/a.geo'))
            self.assertEqual((cold/'data/object_library/a.geo').stat().st_mode & 0o222,0)
            for name in ('data/bin/defs.bin','data/geobin/world.bin','data/server/cache','MapServer.exe'):
                self.assertFalse(os.path.samefile(runtime/name,cold/name))
                (runtime/name).write_bytes(b'generated after cold snapshot')
                self.assertEqual((cold/name).read_bytes(),fixtures[name])
            optional=runtime/'data/object_library/optional.geo';optional.write_bytes(b'visual object')
            self.assertFalse((cold/'data/object_library/optional.geo').exists())

    def test_rich_source_records_are_projected_without_weakening_byte_pins(self):
        original = {'data/object_library/a.geo': {'bytes': 17, 'sha256': 'a'*64,
            'original_client_source': {'container': 'original.pigg', 'index': 45},
            'models': ['exact-model']}}
        projected = generator.physical_pins(original)
        self.assertEqual(projected, {'data/object_library/a.geo': {'bytes': 17, 'sha256': 'a'*64}})
        self.assertIn('models', original['data/object_library/a.geo'])
        self.assertNotEqual(generator.canonical(projected), generator.canonical(original))
        for row in ({'bytes':True,'sha256':'a'*64}, {'bytes':17,'sha256':'not-a-digest'}, {'bytes':0,'sha256':'a'*64}):
            with self.subTest(row=row), self.assertRaises(ValueError):
                generator.physical_pins({'data/object_library/a.geo':row})

    def test_inventory_failure_preserves_bounded_actual_missing_extra_and_changed_differences(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence=Path(temporary)
            common={'data/maps/map.txt': {'bytes':2,'sha256':'a'*64}}
            optional={'data/object_library/optional.geo': {'bytes':3,'sha256':'b'*64}}
            warm={'data/maps/map.txt': {'bytes':4,'sha256':'c'*64}}
            warm.update({'data/object_library/extra%d.geo'%i: {'bytes':1,'sha256':'d'*64} for i in range(50)})
            output=io.StringIO()
            with contextlib.redirect_stdout(output):
                record=generator.record_profile_inventory(evidence,common,optional,warm,{})
            self.assertEqual(record['status'],'mismatch')
            self.assertEqual(record['warm_difference']['missing_count'],1)
            self.assertEqual(record['warm_difference']['extra_count'],50)
            self.assertEqual(len(record['warm_difference']['extra_first_16']),16)
            self.assertEqual(record['warm_difference']['changed_count'],1)
            self.assertEqual(record['cold_difference']['missing_count'],1)
            self.assertEqual(json.loads((evidence/'native-input-profiles.json').read_bytes()),record)
            self.assertIn('COH_ATLAS_BEACON_INPUT_PROFILES',output.getvalue())


if __name__ == '__main__': unittest.main()
