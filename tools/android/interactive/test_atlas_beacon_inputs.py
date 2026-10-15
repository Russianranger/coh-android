"""Beacon preflight trust boundaries; test bytes are deliberately not real graphs."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest

import audit_atlas_beacon_inputs as audit


class BeaconInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        # A syntactically plausible prefix followed by arbitrary bytes is NOT a
        # generated graph. Acceptance must remain unqualified even with SHA pins.
        self.prefix_only = struct.pack('<ii', 8, 1) + b'\0regular\0' + b'not a graph body'
        self.bcn = self.root / 'City_01_01.txt.v8.bcn'
        self.bcn.write_bytes(self.prefix_only)
        self.date = self.root / 'City_01_01.txt.v8.bcn.date'
        self.date.write_bytes(struct.pack('<iII', 9, 1767225600, 0x12345678))

    def test_default_audit_is_deterministic_missing_input_without_graph_claim(self):
        before = {path: path.stat().st_mtime_ns for path, _ in
                  [(audit.ROOT / name, scope) for name, scope in audit.INVENTORIES]}
        result = audit.audit_repo()
        self.assertEqual(result, audit.audit_repo())
        self.assertEqual('no_input', result['status'])
        self.assertTrue(result['preflight_completed'])
        self.assertFalse(result['native_graph_load_verified'])
        self.assertFalse(result['authentic_generated_graph_verified'])
        self.assertFalse(result['generation_routes']['bounded_one_map_generator_ready'])
        self.assertFalse(result['generation_routes']['chat_commands_active']['beacongenerate'])
        self.assertFalse(result['generation_routes']['chat_commands_active']['beaconprocess'])
        self.assertEqual([6, 7, 8], result['native_contract']['read_versions'])
        self.assertTrue(all(not item['generated_beacon_files'] for item in result['inventories']))
        self.assertEqual(before, {path: path.stat().st_mtime_ns for path in before})

    def test_pinned_fake_prefix_and_matching_supplied_crc_never_qualify_graph(self):
        result = audit.probe_candidate(self.bcn, self.date,
            hashlib.sha256(self.prefix_only).hexdigest(),
            hashlib.sha256(self.date.read_bytes()).hexdigest(), 0x12345678)
        self.assertEqual('candidate_unqualified', result['status'])
        self.assertTrue(result['prefix']['structural_prefix_verified'])
        self.assertTrue(result['crc_evidence']['matches_supplied_crc'])
        self.assertFalse(result['prefix']['full_graph_structure_verified'])
        self.assertFalse(result['native_graph_load_verified'])
        self.assertFalse(result['authentic_generated_graph_verified'])
        self.assertFalse(result['loaded_world_crc_verified'])
        self.assertFalse(result['crc_evidence']['supplied_crc_provenance_verified'])

    def test_native_packed_integer_widths_and_u32_bound(self):
        vectors = [(b'\xfc', 63), (b'\x01\xff', 16320),
                   (b'\x02\xff\xff', 4194240), (b'\xff\xff\xff\xff\x03', 0xffffffff)]
        for raw, expected in vectors:
            with self.subTest(raw=raw):
                self.assertEqual((expected, len(raw)), audit.packed_u32(raw, 0))
        for raw in (b'', b'\x01', b'\x02\0', b'\x03\0\0\0', b'\xff\xff\xff\xff\xff'):
            with self.subTest(raw=raw):
                with self.assertRaises(audit.AuditError):
                    audit.packed_u32(raw, 0)

    def test_truncated_wrong_version_flag_marker_and_count_are_rejected(self):
        malformed = [b'\0' * 8,
                     struct.pack('<ii', 9, 1) + self.prefix_only[8:],
                     struct.pack('<ii', 8, 2) + self.prefix_only[8:],
                     self.prefix_only.replace(b'regular', b'garbage'),
                     struct.pack('<ii', 8, 1) + b'\0regular\x10' + b'x' * 4]
        for raw in malformed:
            with self.subTest(raw=raw):
                with self.assertRaises(audit.AuditError):
                    audit.probe_v8_prefix(raw)

    def test_wrong_payload_pin_and_sidecar_crc_fail(self):
        with self.assertRaisesRegex(audit.AuditError, 'SHA-256 pin'):
            audit.probe_candidate(self.bcn, bcn_sha='0' * 64)
        with self.assertRaisesRegex(audit.AuditError, 'CRC differs'):
            audit.probe_candidate(self.bcn, self.date, native_crc=0x12345679)
        with self.assertRaisesRegex(audit.AuditError, 'outside U32'):
            audit.probe_candidate(self.bcn, self.date, native_crc=2**32)

    def test_sidecar_is_exact_v9_three_field_metadata(self):
        for raw in (b'\0' * 8, struct.pack('<iII', 8, 1767225600, 0x12345678), self.date.read_bytes() + b'x'):
            self.date.write_bytes(raw)
            with self.subTest(raw=raw):
                with self.assertRaises(audit.AuditError):
                    audit.probe_candidate(self.bcn, self.date)
        with self.assertRaisesRegex(audit.AuditError, 'sidecar is required'):
            audit.probe_candidate(self.bcn, native_crc=0x12345678)

    def test_regular_reader_refuses_symlink_fifo_and_oversize(self):
        symlink = self.root / 'link.bcn'
        symlink.symlink_to(self.bcn)
        with self.assertRaises(OSError):
            audit.read_regular(symlink, 1024)
        fifo = self.root / 'pipe.bcn'
        os.mkfifo(fifo)
        with self.assertRaisesRegex(audit.AuditError, 'regular file'):
            audit.read_regular(fifo, 1024)
        with self.assertRaisesRegex(audit.AuditError, 'byte bound'):
            audit.read_regular(self.bcn, 3)

    def test_inventory_paths_refuse_traversal_and_false_file_collections(self):
        for value in ({'files': {'../escape.bcn': {}}}, {'files': {'/absolute.bcn': {}}},
                      {'files': {'a\\b.bcn': {}}}, {'files': 'not-an-inventory'}):
            with self.subTest(value=value):
                with self.assertRaises(audit.AuditError):
                    audit.inventory_paths(value)

    def test_cli_candidate_arguments_cannot_be_silently_ignored(self):
        with contextlib.redirect_stdout(io.StringIO()) as stream:
            exit_code = audit.main(['--native-map-crc', '0x12345678'])
        result = json.loads(stream.getvalue())
        self.assertEqual(2, exit_code)
        self.assertEqual('invalid_input', result['status'])
        self.assertFalse(result['native_graph_load_verified'])


if __name__ == '__main__':
    unittest.main()
