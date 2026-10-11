"""Shipping package reconstruction is deterministic and source-bound."""
import gzip
import hashlib
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
import package_monorail_native as package


class MonorailPackageTests(unittest.TestCase):
    def test_deterministic_game_archive_preserves_member_bytes(self):
        files={'MapServer.exe':b'new candidate','retained.dll':b'unchanged','game-package.json':b'{}'}
        with tempfile.TemporaryDirectory() as td:
            first,second=Path(td)/'one.gz',Path(td)/'two.gz'
            package.write_game_archive(first,files);package.write_game_archive(second,dict(reversed(list(files.items()))))
            self.assertEqual(first.read_bytes(),second.read_bytes())
            with tarfile.open(first,'r:gz') as archive:
                self.assertEqual({r.name:archive.extractfile(r).read() for r in archive.getmembers()},files)
                self.assertTrue(all(r.mtime==1767225600 and r.uid==0 for r in archive.getmembers()))

    def test_source_contract_keeps_frozen_collision_algorithms(self):
        receipt=package.source.expected_receipt()
        import atlas_beacon_package as atlas
        self.assertEqual(receipt['retained_collision_sources'],atlas.RETAINED_COLLISION_SOURCES)
        self.assertEqual(receipt['contract'],package.contract.CONTRACT)
        self.assertEqual(receipt['build_targets'],['MapServer'])
        self.assertNotIn('Game/src',str(receipt['patched_sha256']))


if __name__=='__main__':unittest.main()
