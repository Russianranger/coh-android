"""Frozen donor streams produce one reproducible, strictly pinned world ZIP."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zlib

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('world_package_test', HERE / 'prepare_atlas_world_assets.py')
world = importlib.util.module_from_spec(spec); spec.loader.exec_module(world)


class WorldPackageTests(unittest.TestCase):
    def entry(self, name, raw, *, compressed=True):
        stored = zlib.compress(raw, 9) if compressed else raw
        donor = {'bytes': len(raw), 'stored_bytes': len(stored), 'compressed': compressed,
            'sha256': hashlib.sha256(raw).hexdigest(), 'stored_sha256': hashlib.sha256(stored).hexdigest(),
            'md5_table': hashlib.md5(raw).hexdigest()}
        return (name, donor, stored)

    def test_reviewed_payload_preserves_import_avatar_and_honest_provenance(self):
        document = world.read_manifest(world.ROOT / 'assets' / world.MANIFEST)
        self.assertEqual((len(document['files']), document['payload_bytes']), (2877, 309655940))
        self.assertEqual(document['dependency_review']['atlas_makeover_geometry_files'], 37)
        self.assertFalse(document['provenance']['source_archives_fully_downloaded'])
        self.assertFalse(document['provenance']['source_archive_sha256_verified'])
        self.assertFalse(document['dependency_review']['complete_global_world_asset_closure'])
        self.assertLess(world.ARCHIVE_PIN['bytes'], world.MAX_ARCHIVE_BYTES)

    def test_original_deflate_and_stored_members_read_with_zipfile_and_have_reproducible_order(self):
        entries = [self.entry('data/object_library/atlas.geo', b'ground triangles' * 30),
            self.entry('data/texture_library/atlas.texture', b'original pixels', compressed=False)]
        with tempfile.TemporaryDirectory() as temp:
            first, second = Path(temp) / 'first.zip', Path(temp) / 'second.zip'
            world.write_donor_zip(first, entries); world.write_donor_zip(second, list(reversed(entries)))
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(archive.read(entries[0][0]), b'ground triangles' * 30)
                self.assertEqual(archive.read(entries[1][0]), b'original pixels')
                self.assertEqual(archive.getinfo(entries[0][0]).compress_type, zipfile.ZIP_DEFLATED)
                self.assertEqual(archive.getinfo(entries[1][0]).compress_type, zipfile.ZIP_STORED)

    def test_changed_stored_bytes_decoded_sha_or_table_md5_are_rejected(self):
        name, donor, stored = self.entry('data/object_library/atlas.geo', b'ground')
        for field in ('sha256', 'stored_sha256', 'md5_table'):
            bad = dict(donor); bad[field] = '0' * len(bad[field])
            with self.assertRaises(ValueError): world.decode_entry(stored, bad)
        with self.assertRaises(ValueError): world.decode_entry(stored + b'changed', donor)

    def test_changed_http_identity_full_transfer_and_oversized_range_are_refused(self):
        group = (('https://dists.thunderspy.org/piggs/stage1.pigg', '"old"', 'modified', 100, 'bytes 20-29/100'), [])
        class Response:
            status = 206
            headers = {'ETag': '"old"', 'Last-Modified': 'modified', 'Content-Range': 'bytes 20-29/100', 'Content-Length': '10'}
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def geturl(self): return group[0][0]
            def read(self, count): return b'0123456789'
        for field, value in [('status', 200), ('ETag', '"new"'), ('Content-Range', 'bytes 21-30/100'), ('Content-Length', '100')]:
            response = Response(); response.headers = dict(Response.headers)
            if field == 'status': response.status = value
            else: response.headers[field] = value
            with patch.object(world.urllib.request, 'urlopen', return_value=response):
                with self.assertRaises(ValueError): world.download_range(group)
        large = (('url', 'etag', 'modified', world.MAX_RANGE_BYTES + 10,
            f'bytes 0-{world.MAX_RANGE_BYTES}/{world.MAX_RANGE_BYTES+10}'), [])
        with patch.object(world.urllib.request, 'urlopen') as request:
            with self.assertRaises(ValueError): world.download_range(large)
            request.assert_not_called()

    def test_existing_archive_is_verified_without_network_or_rewrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); archive = root / world.ARCHIVE; manifest = root / world.MANIFEST
            archive.write_bytes(b'fixture pinned archive'); manifest.write_text('{}')
            before = archive.stat().st_ino
            with patch.object(world, 'read_manifest', return_value={}), \
                    patch.object(world, 'verify') as verify:
                result = world.materialize(archive, manifest, root=root,
                    downloader=lambda group: self.fail('network forbidden'))
            verify.assert_called_once_with(archive, manifest, root=root)
            self.assertEqual(result['status'], 'verified_existing_archive')
            self.assertEqual(before, archive.stat().st_ino)



if __name__ == '__main__':
    unittest.main()
