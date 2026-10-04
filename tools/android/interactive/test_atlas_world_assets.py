"""World assets refresh owned Atlas caches without replacing preserved inputs."""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import atlas_world_assets as world


class WorldInstallTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.work = self.root / 'client-work-test'; (self.work / 'data').mkdir(parents=True)
        self.context = SimpleNamespace(check=Mock())
        self.payloads = {'data/object_library/city_zones/atlas_park_makeover/ground.geo': b'ground mesh',
            'data/texture_library/world/atlas/ground.texture': b'ground image'}
        self.files = {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
            for name, raw in self.payloads.items()}
        archive = self.root / world.ARCHIVE
        with zipfile.ZipFile(archive, 'w') as output:
            for name, raw in self.payloads.items():
                entry = zipfile.ZipInfo(name); entry.external_attr = (stat.S_IFREG | 0o444) << 16
                entry.compress_type = zipfile.ZIP_DEFLATED; output.writestr(entry, raw)
        archive_raw = archive.read_bytes()
        self.manifest = {'format': 1, 'scope': world.SCOPE, 'source_commit': world.client.SOURCE,
            'data_commit': world.client.DATA, 'files': self.files, 'file_count': len(self.files),
            'payload_bytes': sum(len(raw) for raw in self.payloads.values()),
            'archive': {'filename': world.ARCHIVE, 'bytes': len(archive_raw),
                'sha256': hashlib.sha256(archive_raw).hexdigest()},
            'runtime_visual_validated': False, 'gameplay_validated': False,
            'visual_scope': 'unqualified world fixture'}
        manifest_raw = world.canonical(self.manifest)
        (self.root / world.MANIFEST).write_bytes(manifest_raw)
        self.enterContext(patch.object(world, 'MANIFEST_SHA256', hashlib.sha256(manifest_raw).hexdigest()))
        self.enterContext(patch.object(world, 'ARCHIVE_SHA256', hashlib.sha256(archive_raw).hexdigest()))
        self.enterContext(patch.object(world, 'ARCHIVE_BYTES', len(archive_raw)))
        self.enterContext(patch.object(world, 'FILE_COUNT', len(self.files)))
        self.enterContext(patch.object(world, 'PAYLOAD_BYTES', sum(len(raw) for raw in self.payloads.values())))
        self.enterContext(patch.object(world, 'FILES_SHA256', hashlib.sha256(world.canonical(self.files)).hexdigest()))

    def leaf(self, name, raw=b'preserved data'):
        path = self.work / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        return path

    def test_first_install_invalidates_only_affected_private_geobin_then_reuses_regenerated_cache(self):
        affected = [self.leaf('data/geobin/maps/city_zones/city_01_01/city_01_01.bin'),
            self.leaf('data/geobin/maps/city_zones/city_01_01/city_01_01.bounds'),
            self.leaf('data/geobin/object_library/city_zones/atlas_park_makeover/ground.bin')]
        unrelated = [self.leaf('data/geobin/maps/city_zones/city_02_01/city_02_01.bin'),
            self.leaf('data/geobin/object_library/unrelated.bin'),
            self.leaf('data/bin/tricks.bin'), self.leaf('client-work.json'),
            self.leaf('data/player_library/male_glove.geo')]
        originals = self.root / 'original'; originals.write_bytes(b'imported bytes')
        (self.work / 'data/imported.geo').symlink_to(originals)
        before = {p: (p.read_bytes(), p.stat().st_ino, p.stat().st_mtime_ns) for p in unrelated + [originals]}
        first = world.install(self.work, self.root, self.context)
        self.assertEqual((first['installed_files'], first['reused_files']), (2, 0))
        self.assertTrue(first['cache_refresh']['performed']); self.assertEqual(first['cache_refresh']['removed_files'], 3)
        self.assertTrue(all(not p.exists() for p in affected))
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_ino, p.stat().st_mtime_ns) for p in before})
        for name, raw in self.payloads.items():
            path = self.work / name
            self.assertEqual(path.read_bytes(), raw); self.assertEqual(path.stat().st_nlink, 1)
            self.assertEqual(path.stat().st_mode & 0o777, 0o444); self.assertEqual(path.stat().st_mtime, world.client.CACHE_EPOCH)
        self.leaf('data/geobin/maps/city_zones/city_01_01/city_01_01.bin', b'regenerated from full world')
        inodes = {name: (self.work / name).stat().st_ino for name in self.payloads}
        second = world.install(self.work, self.root, self.context)
        self.assertEqual((second['installed_files'], second['reused_files']), (0, 2))
        self.assertFalse(second['cache_refresh']['performed'])
        self.assertEqual(affected[0].read_bytes(), b'regenerated from full world')
        self.assertEqual(inodes, {name: (self.work / name).stat().st_ino for name in self.payloads})

    def test_conflicting_payload_fails_before_install_or_cache_deletion(self):
        name = sorted(self.payloads)[0]
        existing = self.leaf(name, b'other input')
        cache = self.leaf('data/geobin/maps/city_zones/city_01_01/atlas.bin')
        with self.assertRaises(world.client.base.DiagnosticError):
            world.install(self.work, self.root, self.context)
        self.assertEqual(existing.read_bytes(), b'other input'); self.assertTrue(cache.exists())
        self.assertFalse((self.work / world.MARKER).exists())
        self.assertFalse((self.work / sorted(self.payloads)[1]).exists())

    def test_alias_and_linked_cache_are_rejected_before_input_changes(self):
        (self.work / 'data/Object_Library').mkdir()
        (self.work / 'data/object_library').mkdir()
        with self.assertRaisesRegex(world.client.base.DiagnosticError, 'case-conflicting'):
            world.install(self.work, self.root, self.context)
        (self.work / 'data/Object_Library').rmdir()
        (self.work / 'data/object_library').rmdir()
        outside = self.root / 'outside'; outside.write_bytes(b'original cache')
        path = self.work / 'data/geobin/maps/city_zones/city_01_01/atlas.bin'; path.parent.mkdir(parents=True)
        path.symlink_to(outside)
        with self.assertRaisesRegex(world.client.base.DiagnosticError, 'Linked private world cache'):
            world.install(self.work, self.root, self.context)
        self.assertEqual(outside.read_bytes(), b'original cache'); self.assertTrue(path.is_symlink())
        self.assertFalse(any((self.work / name).exists() for name in self.payloads))

    def test_existing_import_directory_case_is_preserved_for_world_install_and_reuse(self):
        geo = self.work / 'data/object_library/city_zones/Atlas_Park_makeover/ground.geo'
        geo.parent.mkdir(parents=True)
        rootnames = geo.with_suffix('.rootnames'); rootnames.write_bytes(b'Def ground\nEnd\n')
        before = (rootnames.read_bytes(), rootnames.stat().st_ino, geo.parent.stat().st_ino)
        first = world.install(self.work, self.root, self.context)
        self.assertEqual(first['installed_files'], 2)
        self.assertEqual(geo.read_bytes(), b'ground mesh')
        self.assertFalse((self.work / 'data/object_library/city_zones/atlas_park_makeover').exists())
        second = world.install(self.work, self.root, self.context)
        self.assertEqual(second['reused_files'], 2)
        self.assertEqual(before, (rootnames.read_bytes(), rootnames.stat().st_ino, geo.parent.stat().st_ino))

    def test_hardlinked_cache_and_payload_are_rejected(self):
        path = self.leaf('data/geobin/maps/city_zones/city_01_01/atlas.bin'); os.link(path, self.root / 'external-hardlink')
        with self.assertRaises(world.client.base.DiagnosticError):
            world.install(self.work, self.root, self.context)
        self.assertTrue(path.exists()); path.unlink(); (self.root / 'external-hardlink').unlink()
        name = sorted(self.payloads)[0]; p = self.leaf(name, self.payloads[name]); p.chmod(0o444)
        os.utime(p, (world.client.CACHE_EPOCH,) * 2); os.link(p, self.root / 'payload-hardlink')
        with self.assertRaises(world.client.base.DiagnosticError):
            world.install(self.work, self.root, self.context)
        self.assertFalse((self.work / world.MARKER).exists())

    def test_changed_or_missing_installed_payload_cannot_reuse_marker(self):
        world.install(self.work, self.root, self.context)
        name = sorted(self.payloads)[0]; p = self.work / name
        p.unlink()
        with self.assertRaisesRegex(world.client.base.DiagnosticError, 'payload is missing'):
            world.install(self.work, self.root, self.context)
        self.assertFalse(p.exists())

    def test_modified_cache_refresh_marker_is_rejected_before_reuse(self):
        world.install(self.work, self.root, self.context)
        marker = self.work / world.MARKER
        value = json.loads(marker.read_text()); value['cache_refresh']['removed_files'] += 1
        marker.chmod(0o600); marker.write_bytes(world.canonical(value)); marker.chmod(0o444)
        os.utime(marker, (world.client.CACHE_EPOCH,) * 2)
        with self.assertRaisesRegex(world.client.base.DiagnosticError, 'cache refresh receipt differs'):
            world.install(self.work, self.root, self.context)

    def test_interruption_before_cache_refresh_can_resume_without_deleting_other_caches(self):
        cache = self.leaf('data/geobin/maps/city_zones/city_01_01/atlas.bin')
        calls = 0
        def check():
            nonlocal calls
            calls += 1
            if calls == 8:
                raise world.client.base.Cancelled('interrupted test')
        with self.assertRaises(world.client.base.Cancelled):
            world.install(self.work, self.root, SimpleNamespace(check=check))
        result = world.install(self.work, self.root, self.context)
        self.assertEqual(result['verified_file_count'], 2)
        self.assertFalse(cache.exists()); self.assertTrue((self.work / world.MARKER).exists())
        self.assertFalse(list(self.work.rglob('.world-pending-*')))


if __name__ == '__main__':
    unittest.main()
