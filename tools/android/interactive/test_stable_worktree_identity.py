"""Wrapper refresh keeps verified data roots and their external links alive."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    'stable_worktree_fixtures', ROOT / 'tools/android/client/test_guest.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
guest = fixtures.guest


class StableWorktreeIdentityTests(unittest.TestCase):
    def setUp(self):
        fixtures.WorktreeTests.setUp(self)

    def prepare(self):
        return guest.prepare_worktree(self.work, self.data, self.assets, self.identity, self.context)

    def wrapper(self):
        fixtures.WorktreeTests.change_wrapper_commit(self)

    def test_wrapper_refresh_preserves_absolute_server_supplement_links_and_data_identity(self):
        work, first = self.prepare()
        supplement = work / 'data/texture_library/stationary.texture'
        supplement.parent.mkdir(); supplement.write_bytes(b'reviewed supplement'); supplement.chmod(0o444)
        server_link = self.root / 'cached-server-texture'; server_link.symlink_to(supplement)
        before = (work.stat().st_ino, (work / 'data').stat().st_ino, supplement.stat().st_ino)
        (work / 'data/bin/generated.bin').write_bytes(b'generated cache stays private')
        self.wrapper()
        with patch.object(guest.os, 'scandir', side_effect=AssertionError('input tree rebuilt')):
            again, second = self.prepare()
        self.assertEqual(again, work)
        self.assertEqual(second['content_identity_sha256'], first['content_identity_sha256'])
        self.assertEqual((again.stat().st_ino, (again / 'data').stat().st_ino, supplement.stat().st_ino), before)
        self.assertEqual(server_link.read_bytes(), b'reviewed supplement')
        self.assertEqual((again / 'data/bin/generated.bin').read_bytes(), b'generated cache stays private')
        self.assertTrue(second['source_root_preserved'])

    def test_legacy_wrapper_named_tree_is_adopted_in_place_with_checked_receipt_lineage(self):
        work, receipt = self.prepare()
        for key in ('content_identity_sha256', 'worktree_key', 'verified_legacy_receipts'):
            receipt.pop(key)
        receipt.pop('reused')
        legacy_key = hashlib.sha256((self.identity['receipt_sha256'] + receipt['package_sha256']
            + receipt['cache_archive_sha256'] + receipt['prerequisites_archive_sha256']
            + str(guest.CACHE_EPOCH)).encode()).hexdigest()[:24]
        legacy = self.work / ('client-work-' + legacy_key)
        work.rename(legacy)
        marker = legacy / 'client-work.json'; marker.write_text(json.dumps(receipt) + '\n')
        old_marker_sha = guest.base.file_hash(marker)
        supplement = legacy / 'data/supplement.dat'; supplement.write_bytes(b'keep source'); supplement.chmod(0o444)
        external = self.root / 'external'; external.symlink_to(supplement)
        self.wrapper()
        with patch.object(guest.os, 'scandir', side_effect=AssertionError('legacy import rescanned')):
            again, result = self.prepare()
        self.assertEqual(again, legacy)
        self.assertEqual(external.read_bytes(), b'keep source')
        self.assertIn(old_marker_sha, result['verified_legacy_receipts'])
        self.assertEqual(result['worktree_key'], legacy.name)
        self.assertEqual(self.prepare()[0], legacy)

    def test_new_import_receipt_gets_new_data_root_and_preserves_old_generated_data(self):
        work, first = self.prepare()
        generated = work / 'data/bin/native.bin'; generated.write_bytes(b'old generation cache')
        self.identity = dict(self.identity, receipt_sha256='e' * 64, generation='generation-' + '2' * 32)
        again, second = self.prepare()
        self.assertNotEqual(again, work)
        self.assertNotEqual(second['content_identity_sha256'], first['content_identity_sha256'])
        self.assertEqual(generated.read_bytes(), b'old generation cache')
        self.assertFalse(second['reused'])

    def test_interrupted_marker_refresh_leaves_external_link_valid_and_recovers_without_mirror(self):
        work, first = self.prepare()
        supplement = work / 'data/held.dat'; supplement.write_bytes(b'held'); supplement.chmod(0o444)
        link = self.root / 'held-link'; link.symlink_to(supplement)
        old_marker = (work / 'client-work.json').read_bytes()
        self.wrapper()
        with patch.object(guest.base, 'private_write', side_effect=OSError('marker interrupted')):
            with self.assertRaises(OSError): self.prepare()
        self.assertEqual((work / 'client-work.json').read_bytes(), old_marker)
        self.assertEqual(link.read_bytes(), b'held')
        with patch.object(guest.os, 'scandir', side_effect=AssertionError('recovery rebuilt inputs')):
            again, result = self.prepare()
        self.assertEqual(again, work)
        self.assertEqual(result['content_identity_sha256'], first['content_identity_sha256'])


if __name__ == '__main__': unittest.main()
