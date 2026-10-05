"""Reject incomplete graph, CRC and native route evidence before packaging."""
import struct
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


if __name__ == '__main__': unittest.main()
