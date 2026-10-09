"""Reuse world assets only while their proved filesystem generation is unchanged."""
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_atlas_world_assets as fixtures

world = fixtures.world


class WorldAssetReuseTests(unittest.TestCase):
    setUp = fixtures.WorldInstallTests.setUp
    leaf = fixtures.WorldInstallTests.leaf

    def install(self):
        return world.install(self.work, self.root, self.context)

    def readonly(self, path):
        path.chmod(0o444)
        os.utime(path, (world.client.CACHE_EPOCH,) * 2)
        return path

    def assert_preserved(self, paths, before):
        self.assertEqual(before, [(path.read_bytes(), world.fingerprint(path.lstat())) for path in paths])

    def test_unchanged_receipt_opens_neither_archive_nor_installed_payloads(self):
        first = self.install()
        self.assertEqual(first['decoded_files'], len(self.payloads))
        self.assertEqual(first['decoded_payload_bytes'], world.PAYLOAD_BYTES)
        forbidden = {self.root / world.ARCHIVE, *(self.work / name for name in self.payloads)}
        original_open = os.open
        def guarded_open(path, *args, **kwargs):
            self.assertNotIn(Path(path), forbidden)
            return original_open(path, *args, **kwargs)
        with patch.object(world.os, 'open', side_effect=guarded_open), \
                patch.object(world, 'verify_target', side_effect=AssertionError('output hash on reuse')), \
                patch.object(world.zipfile, 'ZipFile', side_effect=AssertionError('archive decode on reuse')):
            second = self.install()
        self.assertEqual(second['reuse_validation'], 'unchanged_filesystem_receipt')
        self.assertEqual((second['archive_read_bytes'], second['decoded_files'], second['decoded_payload_bytes']), (0, 0, 0))
        self.assertFalse(second['cache_refresh']['performed'])

    def test_initial_install_streams_and_decodes_only_missing_payloads(self):
        name = sorted(self.payloads)[0]
        existing = self.readonly(self.leaf(name, self.payloads[name]))
        before = (existing.read_bytes(), world.fingerprint(existing.lstat()))
        with patch.object(world, 'BLOCK_BYTES', 3), \
                patch.object(world.zipfile.ZipFile, 'read', side_effect=AssertionError('unbounded ZIP read')):
            result = self.install()
        self.assertEqual(result['decoded_files'], 1)
        self.assertEqual(result['decoded_payload_bytes'], world.PAYLOAD_BYTES - len(self.payloads[name]))
        self.assertEqual(before, (existing.read_bytes(), world.fingerprint(existing.lstat())))
        self.assertGreater(self.context.check.call_count, world.ARCHIVE_BYTES // 3)

    def test_legacy_marker_is_verified_without_decoding_or_refreshing_regenerated_caches(self):
        self.install()
        (self.work / world.REUSE_MARKER).unlink()
        cache = self.leaf('data/geobin/maps/city_zones/city_01_01/atlas.bin', b'regenerated cache')
        marker = self.work / world.MARKER
        before = [(p.read_bytes(), world.fingerprint(p.lstat())) for p in (marker, cache)]
        with patch.object(world, 'extract_payload', side_effect=AssertionError('existing payload decoded')):
            result = self.install()
        self.assertEqual(result['reuse_validation'], 'pinned_content_verification')
        self.assertEqual((result['installed_files'], result['decoded_files']), (0, 0))
        self.assertEqual(result['archive_read_bytes'], world.ARCHIVE_BYTES)
        self.assert_preserved((marker, cache), before)
        self.assertEqual(self.install()['reuse_validation'], 'unchanged_filesystem_receipt')

    def test_same_size_output_corruption_with_restored_mtime_is_rejected(self):
        self.install()
        marker, receipt = self.work / world.MARKER, self.work / world.REUSE_MARKER
        before = [(p.read_bytes(), world.fingerprint(p.lstat())) for p in (marker, receipt)]
        target = self.work / sorted(self.payloads)[0]
        target.chmod(0o600); target.write_bytes(b'x' * target.stat().st_size); self.readonly(target)
        with self.assertRaisesRegex(world.client.base.DiagnosticError, 'conflicts with the reviewed payload'):
            self.install()
        self.assert_preserved((marker, receipt), before)

    def test_same_size_archive_corruption_with_restored_mtime_is_rejected(self):
        self.install()
        receipt = self.work / world.REUSE_MARKER
        before = [(receipt.read_bytes(), world.fingerprint(receipt.lstat()))]
        archive = self.root / world.ARCHIVE
        info = archive.stat(); raw = bytearray(archive.read_bytes()); raw[0] ^= 1
        archive.write_bytes(raw); os.utime(archive, ns=(info.st_atime_ns, info.st_mtime_ns))
        with self.assertRaisesRegex(world.client.base.DiagnosticError, 'archive differs from reviewed'):
            self.install()
        self.assert_preserved((receipt,), before)

    def test_inode_replacement_with_pinned_bytes_reverifies_once_without_decoding(self):
        self.install()
        name = sorted(self.payloads)[0]; target = self.work / name
        replacement = self.readonly(self.leaf('replacement.geo', self.payloads[name]))
        os.replace(replacement, target)
        with patch.object(world, 'extract_payload', side_effect=AssertionError('existing payload decoded')):
            result = self.install()
        self.assertEqual(result['reuse_validation'], 'pinned_content_verification')
        self.assertEqual(result['archive_read_bytes'], world.ARCHIVE_BYTES)
        self.assertEqual(result['decoded_files'], 0)
        self.assertEqual(self.install()['reuse_validation'], 'unchanged_filesystem_receipt')

    def test_archive_metadata_change_reverifies_once_without_decoding(self):
        self.install()
        archive = self.root / world.ARCHIVE
        info = archive.stat(); archive.write_bytes(archive.read_bytes())
        os.utime(archive, ns=(info.st_atime_ns, info.st_mtime_ns))
        result = self.install()
        self.assertEqual(result['reuse_validation'], 'pinned_content_verification')
        self.assertEqual(result['decoded_files'], 0)
        self.assertEqual(self.install()['archive_read_bytes'], 0)

    def test_worktree_import_or_config_identity_change_reverifies_once(self):
        config = self.leaf('client-work.json', b'{"import":{"generation":"one"},"cache":"one"}')
        self.install()
        config.write_bytes(b'{"import":{"generation":"two"},"cache":"two"}')
        result = self.install()
        self.assertEqual(result['reuse_validation'], 'pinned_content_verification')
        self.assertEqual(result['archive_read_bytes'], world.ARCHIVE_BYTES)
        self.assertEqual(result['decoded_files'], 0)
        self.assertEqual(self.install()['archive_read_bytes'], 0)
        with patch.object(world.client, 'SOURCE', '0' * 40):
            with self.assertRaisesRegex(world.client.base.DiagnosticError, 'provenance or allowlist differs'):
                self.install()

    def test_links_and_new_case_alias_cannot_use_receipt(self):
        self.install()
        target = self.work / sorted(self.payloads)[0]
        outside = self.root / 'outside.geo'; outside.write_bytes(target.read_bytes())
        target.unlink(); target.symlink_to(outside)
        with self.assertRaisesRegex(world.client.base.DiagnosticError, 'Invalid world supplement file'):
            self.install()
        target.unlink(); target.write_bytes(outside.read_bytes()); self.readonly(target)
        os.link(target, self.root / 'hardlink.geo')
        with self.assertRaisesRegex(world.client.base.DiagnosticError, 'Invalid world supplement file'):
            self.install()
        (self.root / 'hardlink.geo').unlink()
        (self.work / 'data/Object_Library').mkdir()
        with self.assertRaisesRegex(world.client.base.DiagnosticError, 'case-conflicting'):
            self.install()

    def test_linked_ancestor_cannot_use_receipt(self):
        self.install()
        directory = self.work / 'data/object_library'
        moved = self.root / 'moved-object-library'; directory.rename(moved); directory.symlink_to(moved)
        with self.assertRaisesRegex(world.client.base.DiagnosticError, 'Linked or non-directory'):
            self.install()

    def test_corrupt_derived_receipt_falls_back_but_linked_receipt_is_rejected(self):
        self.install()
        receipt = self.work / world.REUSE_MARKER
        receipt.chmod(0o600); receipt.write_bytes(b'{broken'); self.readonly(receipt)
        self.assertEqual(self.install()['reuse_validation'], 'pinned_content_verification')
        self.assertEqual(self.install()['archive_read_bytes'], 0)
        outside = self.root / 'receipt-copy'; outside.write_bytes(receipt.read_bytes())
        receipt.unlink(); receipt.symlink_to(outside)
        with self.assertRaises(OSError):
            self.install()

    def test_cancellation_during_archive_hash_preserves_legacy_marker_and_caches(self):
        self.install(); (self.work / world.REUSE_MARKER).unlink()
        cache = self.leaf('data/geobin/maps/city_zones/city_01_01/atlas.bin', b'regenerated cache')
        marker = self.work / world.MARKER
        before = [(p.read_bytes(), world.fingerprint(p.lstat())) for p in (marker, cache)]
        original_hash = world.hash_stream
        archive = self.root / world.ARCHIVE
        def interrupt(source, context, limit):
            info = os.fstat(source.fileno())
            if (info.st_dev, info.st_ino) == (archive.stat().st_dev, archive.stat().st_ino):
                calls = 0
                def check():
                    nonlocal calls
                    calls += 1
                    if calls == 2:
                        raise world.client.base.Cancelled('archive hash interrupted')
                return original_hash(source, SimpleNamespace(check=check), limit)
            return original_hash(source, context, limit)
        with patch.object(world, 'BLOCK_BYTES', 3), patch.object(world, 'hash_stream', side_effect=interrupt):
            with self.assertRaises(world.client.base.Cancelled):
                self.install()
        self.assert_preserved((marker, cache), before)
        self.assertFalse((self.work / world.REUSE_MARKER).exists())
        self.assertFalse(list(self.work.rglob('.world-pending-*')))
        self.assertEqual(self.install()['reuse_validation'], 'pinned_content_verification')

    def test_cancellation_during_fresh_decode_removes_pending_leaf_and_preserves_cache(self):
        cache = self.leaf('data/geobin/maps/city_zones/city_01_01/atlas.bin')
        original_extract = world.extract_payload
        def interrupted(archive, name, pin, output, context):
            calls = 0
            def check():
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise world.client.base.Cancelled('decode interrupted')
            return original_extract(archive, name, pin, output, SimpleNamespace(check=check))
        with patch.object(world, 'BLOCK_BYTES', 3), patch.object(world, 'extract_payload', side_effect=interrupted):
            with self.assertRaises(world.client.base.Cancelled):
                self.install()
        self.assertTrue(cache.exists())
        self.assertFalse((self.work / world.MARKER).exists())
        self.assertFalse((self.work / world.REUSE_MARKER).exists())
        self.assertFalse(list(self.work.rglob('.world-pending-*')))
        self.assertEqual(self.install()['installed_files'], 2)

    def test_output_change_during_partial_install_cannot_seal_unverified_generation(self):
        name = sorted(self.payloads)[0]
        existing = self.readonly(self.leaf(name, self.payloads[name]))
        cache = self.leaf('data/geobin/maps/city_zones/city_01_01/atlas.bin')
        before = [(cache.read_bytes(), world.fingerprint(cache.lstat()))]
        original_extract = world.extract_payload
        def changed_output(*args):
            original_extract(*args)
            existing.chmod(0o600); existing.write_bytes(b'x' * len(self.payloads[name])); self.readonly(existing)
        with patch.object(world, 'extract_payload', side_effect=changed_output):
            with self.assertRaisesRegex(world.client.base.DiagnosticError, 'payload changed during preparation'):
                self.install()
        self.assert_preserved((cache,), before)
        self.assertFalse((self.work / world.MARKER).exists())
        self.assertFalse((self.work / world.REUSE_MARKER).exists())

    def test_cancelled_receipt_replacement_preserves_prior_receipt_and_installation_history(self):
        config = self.leaf('client-work.json', b'{"import":"one"}')
        self.install(); config.write_bytes(b'{"import":"two"}')
        paths = (self.work / world.MARKER, self.work / world.REUSE_MARKER)
        before = [(p.read_bytes(), world.fingerprint(p.lstat())) for p in paths]
        original_publish = world.publish_reuse
        def cancelled(worktree, value, context):
            def check():
                raise world.client.base.Cancelled('receipt publication interrupted')
            return original_publish(worktree, value, SimpleNamespace(check=check))
        with patch.object(world, 'publish_reuse', side_effect=cancelled):
            with self.assertRaises(world.client.base.Cancelled):
                self.install()
        self.assert_preserved(paths, before)
        self.assertFalse(list(self.work.glob('.world-reuse-*')))
        self.assertEqual(self.install()['reuse_validation'], 'pinned_content_verification')

    def test_output_change_during_cache_removal_cannot_publish_installation_marker(self):
        self.leaf('data/geobin/maps/city_zones/city_01_01/atlas.bin')
        original_remove = world.remove_cache
        def changed_output(*args):
            original_remove(*args)
            name = sorted(self.payloads)[0]; target = self.work / name
            target.chmod(0o600); target.write_bytes(b'x' * len(self.payloads[name])); self.readonly(target)
        with patch.object(world, 'remove_cache', side_effect=changed_output):
            with self.assertRaisesRegex(world.client.base.DiagnosticError, 'payload changed during preparation'):
                self.install()
        self.assertFalse((self.work / world.MARKER).exists())
        self.assertFalse((self.work / world.REUSE_MARKER).exists())

    def test_cache_ancestor_changed_during_decode_cannot_delete_external_cache(self):
        relative = 'maps/city_zones/city_01_01/atlas.bin'
        cache = self.leaf('data/geobin/' + relative)
        outside = self.root / 'outside-caches'; external = outside / relative
        external.parent.mkdir(parents=True); external.write_bytes(cache.read_bytes())
        before = [(external.read_bytes(), world.fingerprint(external.lstat()))]
        original_extract = world.extract_payload
        def changed_cache(archive, name, *args):
            original_extract(archive, name, *args)
            if name == sorted(self.payloads)[-1]:
                root = self.work / 'data/geobin'
                root.rename(self.root / 'preserved-caches'); root.symlink_to(outside)
        with patch.object(world, 'extract_payload', side_effect=changed_cache):
            with self.assertRaisesRegex(world.client.base.DiagnosticError, 'Linked or non-directory'):
                self.install()
        self.assert_preserved((external,), before)
        self.assertTrue((self.root / 'preserved-caches' / relative).exists())
        self.assertFalse((self.work / world.MARKER).exists())

    def test_file_growing_after_initial_stat_is_rejected_within_stream_bound(self):
        target = self.root / 'growing.bin'; target.write_bytes(b'initial')
        original_hash = world.hash_stream
        def grew(source, context, limit):
            with target.open('ab') as output:
                output.write(b'unreviewed growth')
            return original_hash(source, context, limit)
        with patch.object(world, 'BLOCK_BYTES', 3), patch.object(world, 'hash_stream', side_effect=grew):
            with self.assertRaisesRegex(world.client.base.DiagnosticError, 'grew while reading'):
                world.hash_regular(target, 1024, self.context)


if __name__ == '__main__':
    unittest.main()
