import struct
import unittest
from polycell import decode


class GridDecode(unittest.TestCase):
    def rejects(self, raw, count=3):
        with self.assertRaises(ValueError):
            decode(bytes(raw), count)

    def test_leaf_and_duplicate_references(self):
        raw = struct.pack('<IIi3H', 0, 12, 3, 2, 0, 2)
        self.assertEqual(decode(raw, 3)['cells'][0]['triangles'], [2, 0, 2])

    def test_children_and_shared_cell(self):
        raw = struct.pack('<IIi8I', 12, 0, 0, 44, 44, 0, 0, 0, 0, 0, 0)
        raw += struct.pack('<IIiH', 0, 56, 1, 1)
        result = decode(raw, 3)
        self.assertEqual((result['cell_count'], result['triangle_references']), (2, 1))
        for end in range(len(raw)):
            self.rejects(raw[:end])

    def test_malformed_records(self):
        for record in [(0, 0, 1), (0, 12, -1), (0, 12, 4), (0, 13, 1),
                       (1, 0, 0), (100, 0, 0), (0, 100, 1)]:
            self.rejects(struct.pack('<IIi', *record) + bytes(16))
        self.rejects(struct.pack('<IIiH', 0, 12, 1, 3))
        self.rejects(bytes(12), 0)
        self.rejects(bytes(12), 65537)

    def test_cycle_and_depth_bound(self):
        raw = struct.pack('<IIi8I', 12, 0, 0, 44, 0, 0, 0, 0, 0, 0, 0)
        raw += struct.pack('<IIi8I', 56, 0, 0, 44, 0, 0, 0, 0, 0, 0, 0)
        self.rejects(raw)
        raw = bytearray()
        for i in range(66):
            raw += struct.pack('<IIi8I', i * 44 + 12, 0, 0,
                               (i + 1) * 44 if i < 65 else 0, 0, 0, 0, 0, 0, 0, 0)
        self.rejects(raw)

class AuthenticBench(unittest.TestCase):
    def test_pinned_grid_and_truncations(self):
        import hashlib
        import json
        from pathlib import Path
        fixture = json.loads(Path(__file__).with_name('bench-grid.json').read_text())
        raw = bytes.fromhex(fixture['grid_hex'])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), fixture['source_grid_sha256'])
        result = decode(raw, 188)
        self.assertEqual((result['cell_count'], result['triangle_references']), (3, 216))
        self.assertEqual({i for c in result['cells'] for i in c['triangles']}, set(range(188)))
        # Every authentic byte prefix must fail or yield the same complete tree.
        # Source padding is not falsely treated as semantic payload.
        for end in range(len(raw)):
            try:
                partial = decode(raw[:end], 188)
            except ValueError:
                continue
            self.assertEqual(partial['cells'], result['cells'])


if __name__ == '__main__':
    unittest.main()
