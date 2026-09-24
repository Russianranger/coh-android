"""Regression cases for corrupt/untrusted archives and selective staging."""
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from inspect_piggs import geometry_header, inspect
from index_piggs import index_archive


def archive(entries, cached_header=None):
    def pool(flag, items):
        data = b''.join(struct.pack('<I', len(x)) + x for x in items)
        return struct.pack('<III', flag, len(items), len(data)) + data
    names = pool(0x6789, [name.encode() + b'\0' for name, body in entries])
    headers = pool(0x9ABC, [] if cached_header is None else [cached_header])
    offset = 16 + 48 * len(entries) + len(names) + len(headers)
    table, payloads = [], []
    for i, (name, body) in enumerate(entries):
        payload = zlib.compress(body)
        digest = hashlib.md5(body).digest() if body else bytes(16)
        table.append(struct.pack('<IiIIIIi16sI', 0x3456, i, len(body), 0, offset, 0,
                                 -1 if cached_header is None else 0, digest, len(payload)))
        payloads.append(payload)
        offset += len(payload)
    return (struct.pack('<IHHHHI', 0x123, 2, 2, 16, 48, len(entries)) +
            b''.join(table) + names + headers + b''.join(payloads))


class ArchiveTests(unittest.TestCase):
    def run_archive(self, data, *, stage=False, limit=1024):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'sample.pigg'
            source.write_bytes(data)
            target = root / 'assets' if stage else None
            report = inspect(source, None, limit, [8192], target, set())
            files = sorted(str(x.relative_to(target)) for x in target.rglob('*') if x.is_file()) if stage else []
            return report, files

    def test_selective_staging_excludes_generated_and_text_files(self):
        report, files = self.run_archive(archive([
            ('Texture_Library/sample.texture', b'texture'),
            ('fonts/fallback.ttc', b'font collection'),
            ('bin/powers.bin', b'compiled'), ('defs/example.def', b'definition')]), stage=True)
        self.assertEqual(files, ['fonts/fallback.ttc', 'texture_library/sample.texture'])
        self.assertEqual(report['entry_count'], 4)

    def test_checksum_corruption_rejected(self):
        data = bytearray(archive([('sample.txt', b'content')]))
        data[16 + 28] ^= 1
        with self.assertRaisesRegex(ValueError, 'MD5 mismatch'):
            self.run_archive(data)

    def test_truncated_archive_rejected(self):
        with self.assertRaisesRegex(ValueError, 'out-of-bounds'):
            self.run_archive(archive([('sample.txt', b'content')])[:-2])

    def test_path_traversal_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unsafe archive path'):
            self.run_archive(archive([('../escape.texture', b'content')]), stage=True)

    def test_case_collisions_rejected(self):
        with self.assertRaisesRegex(ValueError, 'case-colliding'):
            self.run_archive(archive([('A.txt', b'a'), ('a.txt', b'b')]))

    def test_inflation_limit_rejected(self):
        with self.assertRaisesRegex(ValueError, 'limit exceeded'):
            self.run_archive(archive([('sample.txt', b'x' * 128)]), limit=64)

    def test_mismatching_cached_header_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Cached header differs'):
            self.run_archive(archive([('sample.texture', b'content')], cached_header=b'wrong'))

    def test_future_reader_version_rejected(self):
        data = bytearray(archive([('sample.txt', b'content')]))
        struct.pack_into('<H', data, 6, 3)
        with self.assertRaisesRegex(ValueError, 'Unsupported PIGG'):
            self.run_archive(data)

    def test_geometry_version_and_header_envelope(self):
        header = struct.pack('<IIII', 3, 0, 0, 0)
        packed = zlib.compress(header)
        data = struct.pack('<IIII', len(packed) + 12, 0, 8, len(header)) + packed + b'abc'
        result = geometry_header(data)
        self.assertEqual(result['version'], 8)
        self.assertTrue(result['header_decompression_verified'])
        self.assertEqual(result['runtime_compatibility'], 'unverified')
        with self.assertRaisesRegex(ValueError, 'out-of-bounds'):
            geometry_header(data[:-1])

    def test_geometry_legacy_offset(self):
        header = struct.pack('<IIII', 3, 0, 0, 0)
        packed = zlib.compress(header)
        data = struct.pack('<II', len(packed) + 4, len(header)) + packed + b'\0' * 4 + b'abc'
        self.assertTrue(geometry_header(data)['data_block_bounds_verified'])
        with self.assertRaisesRegex(ValueError, 'out-of-bounds'):
            geometry_header(data[:-1])

    def test_unsupported_geometry_reported_without_claiming_compatibility(self):
        for version in (1, 6, 9):
            result = geometry_header(struct.pack('<IIII', 20, 0, version, 64))
            self.assertFalse(result['baseline_loader_accepts_version'])
            self.assertNotIn('header_decompression_verified', result)

    def test_index_reads_tables_without_claiming_payload_integrity(self):
        data = archive([('player_library/animations/male/thumbsup.anim', b'animation'),
                        ('texture_library/system/white.texture', b'texture')])
        # A missing payload is intentionally not detected by the index-only tool.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'index-only.pigg'
            path.write_bytes(data[:-4])
            result = index_archive(path)
        self.assertEqual(result['animation_count'], 1)
        self.assertTrue(result['has_male_thumbsup_animation'])
        self.assertEqual(result['startup_texture_paths'], ['texture_library/system/white.texture'])
        self.assertFalse(result['integrity_checked'])
        self.assertFalse(result['payloads_read'])

    def test_index_rejects_bad_filename_table(self):
        data = bytearray(archive([('sample.txt', b'content')]))
        struct.pack_into('<I', data, 16 + 48, 0)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad-table.pigg'
            path.write_bytes(data)
            with self.assertRaisesRegex(ValueError, 'Invalid filename table'):
                index_archive(path)


if __name__ == '__main__':
    unittest.main()
