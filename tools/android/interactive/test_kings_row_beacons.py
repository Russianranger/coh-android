"""Reject partial native evidence and tampered external graph packages."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import generate_kings_row_beacons as host
sys.path.insert(0,str(host.ROOT/'android/guest'))
import kings_row_beacon_package as guest


class NativeKingsProofTests(unittest.TestCase):
    def test_native_witness_requires_collision_crc_readback_and_32_routes(self):
        log=(b'COH_KINGS_ROW_COLLISION_LOAD_V1 missing_groups=0 missing_root_models=0\n'
             b'COH_KINGS_ROW_BEACON_FRESH_WORLD_V1 crc=0x12345678\n'
             b'COH_KINGS_ROW_BEACON_NATIVE_V1 crc=0x12345678 combat=8000 connected=7900 ground=9000 raised=1 blocks=22 paths=32\n')
        date=struct.pack('<iII',9,0,0x12345678)
        self.assertTrue(host.native_evidence(log,date)['native_collision_load_verified'])
        for invalid in (log.replace(b'paths=32',b'paths=31'),log.replace(b'missing_groups=0',b'missing_groups=1'),
                        log.replace(b'FRESH_WORLD_V1',b'NO_FRESH_WORLD'),log+log):
            with self.assertRaises(ValueError):host.native_evidence(invalid,date)
        with self.assertRaises(ValueError):host.native_evidence(log,struct.pack('<iII',9,0,0x12345679))

    def test_inherited_verify_flag_cannot_change_generation_role(self):
        with unittest.mock.patch.dict(host.os.environ,{'COH_ATLAS_BEACON_VERIFY_ONLY':'1','COH_KINGS_ROW_BEACON_VERIFY_ONLY':'1'}):
            self.assertNotIn('COH_KINGS_ROW_BEACON_VERIFY_ONLY',host.role_environment())
            self.assertNotIn('COH_ATLAS_BEACON_VERIFY_ONLY',host.role_environment(True))
            self.assertEqual(host.role_environment(True)['COH_KINGS_ROW_BEACON_VERIFY_ONLY'],'1')

    def test_runtime_lock_refuses_modified_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);manifest=root/guest.MANIFEST;lock=root/guest.LOCK
            manifest.write_text('{}')
            lock.write_text(json.dumps({'format':1,'map_id':5,'manifest':host.pin(manifest),'archive':{}}))
            manifest.write_text('{"changed":true}')
            with self.assertRaisesRegex(ValueError,'APK-owned lock'):guest.read_manifest(manifest,lock)

    def test_input_paths_do_not_admit_other_maps_or_traversal(self):
        self.assertTrue(guest.input_name('data/'+host.MAP))
        for value in ('data/maps/city_zones/city_01_01/city_01_01.txt','data/object_library/../../bad.geo',
                      '/data/object_library/a.geo','data/object_library/a.dll'):
            self.assertFalse(guest.input_name(value))


import unittest.mock
if __name__=='__main__':unittest.main()
