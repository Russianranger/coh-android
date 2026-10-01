"""The small avatar supplement must never replace imported or cached data."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import character_avatar_assets as avatar
import character_creation_diagnostic as guest


# This list and aggregate metadata pin describe the original shipped supplement.
# Keep them fixed so upgrading the package cannot silently replace its 13 files.
LEGACY_FILES = (
    'data/player_library/male_boot.geo',
    'data/player_library/male_pants.geo',
    'data/player_library/male_shirt.geo',
    'data/player_library/v_male_head.geo',
    'data/texture_library/players/avatar/male/chest/leather/chest_leather_03.texture',
    'data/texture_library/players/avatar/male/chest/leather/chest_leather_03_mask.texture',
    'data/texture_library/players/avatar/male/hips/leather/hips_leather_03.texture',
    'data/texture_library/players/avatar/male/hips/leather/hips_leather_03_mask.texture',
    'data/texture_library/players/avatar/super_shared/boots/boot_leather_03.texture',
    'data/texture_library/players/avatar/super_shared/boots/boot_leather_03_mask.texture',
    'data/texture_library/players/avatar/super_shared/gloves/glove_leather_03.texture',
    'data/texture_library/players/avatar/super_shared/gloves/glove_leather_03_mask.texture',
    'data/texture_library/v_players/avatar/super_shared/patterns/face/face_v_asym_eyes_01.texture',
)
LEGACY_FILES_SHA256 = '7128786c6d28bf4f43e63e03db7dc18fd001e0e915fb8851f328989ad9281240'
CLEAR_TWENTY_FILES_SHA256 = 'f80befcb13dce3be586f3091cb7617c7e8c1ab1cf2348bfe5546a76bda242539'
SMOOTH_GLOVE_FILE = 'data/player_library/male_glove.geo'


class AvatarAssetsTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.work = self.root/'client-work-example'; (self.work/'data').mkdir(parents=True)
        self.assets = ROOT/'assets'; self.context = SimpleNamespace(check=Mock())
        self.manifest = json.loads((self.assets/avatar.MANIFEST).read_text())
        self.first = sorted(avatar.ALLOWED)[0]

    def moved_legacy_links(self, label):
        old = self.root / label / ('client-work-' + 'a' * 24)
        new = old.with_name('client-work-' + 'b' * 24)
        (old / 'data').mkdir(parents=True)
        _, payloads = avatar.package(self.assets)
        for index, name in enumerate(sorted(avatar.ALLOWED)):
            target = old / name; target.parent.mkdir(parents=True, exist_ok=True)
            intermediate = target.parent / ('.l2s..avatar-pending-%08x0001' % index)
            backing = intermediate.with_name(intermediate.name + '.0001')
            backing.write_bytes(payloads[name]); backing.chmod(0o444)
            os.utime(backing, (avatar.client.CACHE_EPOCH,) * 2)
            intermediate.symlink_to(backing)
            target.symlink_to(intermediate)
        marker = old / 'client-work.json'; marker.write_bytes(b'preserved identity')
        cache = old / 'data/bin/generated.bin'; cache.parent.mkdir(); cache.write_bytes(b'preserved cache')
        old.rename(new)
        return new

    def test_moved_legacy_emulated_links_are_materialized_once_without_backing_entries(self):
        work = self.moved_legacy_links('moved')
        with self.assertRaises(OSError) as error:
            avatar.verify_target(work / self.first, self.manifest['files'][self.first])
        self.assertEqual(error.exception.errno, 40)
        preserved = {path: (path.read_bytes(), path.stat().st_ino, path.stat().st_mtime_ns)
                     for path in (work / 'client-work.json', work / 'data/bin/generated.bin')}
        proof = avatar.install(work, self.assets, self.context)
        self.assertEqual((proof['installed_files'], proof['reused_files'], proof['legacy_repaired_files']), (0, 21, 21))
        self.assertFalse(list(work.rglob('.l2s.*')))
        self.assertEqual(preserved, {path: (path.read_bytes(), path.stat().st_ino, path.stat().st_mtime_ns)
                                     for path in preserved})
        self.assertTrue(all(avatar.verify_target(work / name, pin) for name, pin in self.manifest['files'].items()))
        second = avatar.install(work, self.assets, self.context)
        self.assertEqual((second['installed_files'], second['reused_files'], second['legacy_repaired_files']), (0, 21, 0))

    def test_cancelled_legacy_cleanup_is_completed_on_retry(self):
        work = self.moved_legacy_links('cancelled')
        checks = 0
        def check():
            nonlocal checks
            checks += 1
            if checks == 43:
                raise avatar.client.base.Cancelled('after atomic replacement, before cleanup')
        with self.assertRaises(avatar.client.base.Cancelled):
            avatar.install(work, self.assets, SimpleNamespace(check=check))
        self.assertEqual(len(list(work.rglob('.l2s.*'))), 42)
        proof = avatar.install(work, self.assets, self.context)
        self.assertEqual((proof['installed_files'], proof['reused_files'], proof['legacy_repaired_files']), (0, 21, 0))
        self.assertFalse(list(work.rglob('.l2s.*')))

    def test_invalid_legacy_chains_fail_preflight_without_replacing_any_leaf(self):
        for change in ('bytes', 'mode', 'timestamp', 'chain', 'external_backing', 'old_worktree'):
            with self.subTest(change=change):
                work = self.moved_legacy_links(change)
                target = work / self.first
                old_value = os.readlink(target)
                intermediate = target.parent / Path(old_value).name
                backing = intermediate.with_name(intermediate.name + '.0001')
                if change == 'bytes':
                    backing.chmod(0o600); backing.write_bytes(b'incorrect'); backing.chmod(0o444)
                    os.utime(backing, (avatar.client.CACHE_EPOCH,) * 2)
                elif change == 'mode': backing.chmod(0o600)
                elif change == 'timestamp': os.utime(backing, (avatar.client.CACHE_EPOCH + 1,) * 2)
                elif change == 'chain':
                    intermediate.unlink(); intermediate.symlink_to('/untrusted/external')
                elif change == 'external_backing':
                    external = self.root / 'external.geo'; external.write_bytes(backing.read_bytes())
                    backing.unlink(); backing.symlink_to(external)
                else:
                    target.unlink(); target.symlink_to(old_value.replace('a' * 24, 'bad-worktree'))
                links = {name: os.readlink(work / name) for name in avatar.ALLOWED}
                with self.assertRaises((avatar.client.base.DiagnosticError, OSError)):
                    avatar.install(work, self.assets, self.context)
                self.assertEqual(links, {name: os.readlink(work / name) for name in avatar.ALLOWED})

    def test_all_twenty_one_assets_install_and_reuse_without_import_cache_or_identity_changes(self):
        imported = self.root/'import'; imported.mkdir()
        original = imported/'original.geo'; original.write_bytes(b'import unchanged')
        (self.work/'data/original.geo').symlink_to(original)
        marker = self.work/'client-work.json'; marker.write_text('{"original_identity":true}\n')
        cache = self.work/'data/bin/generated.bin'; cache.parent.mkdir(); cache.write_bytes(b'preserved cache')
        prior = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in (original, marker, cache)}
        first = avatar.install(self.work, self.assets, self.context)
        self.assertEqual((first['installed_files'], first['reused_files'], first['payload_bytes']),
                         (21, 0, avatar.PAYLOAD_BYTES))
        for name, pin in self.manifest['files'].items():
            path = self.work/name; info = path.lstat()
            self.assertTrue(stat.S_ISREG(info.st_mode)); self.assertEqual(info.st_nlink, 1)
            self.assertEqual(stat.S_IMODE(info.st_mode), 0o444)
            self.assertEqual(info.st_mtime, avatar.client.CACHE_EPOCH)
            self.assertEqual(len(path.read_bytes()), pin['bytes'])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), pin['sha256'])
        inodes = {name: (self.work/name).stat().st_ino for name in avatar.ALLOWED}
        second = avatar.install(self.work, self.assets, self.context)
        self.assertEqual((second['installed_files'], second['reused_files']), (0, 21))
        self.assertEqual(inodes, {name: (self.work/name).stat().st_ino for name in avatar.ALLOWED})
        self.assertEqual(prior, {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in prior})
        self.assertFalse((self.work/'character-avatar-applied.json').exists())

    def test_upgrade_reuses_original_thirteen_bytes_and_installs_only_eight_new_files(self):
        legacy_pins = {name: self.manifest['files'][name] for name in LEGACY_FILES}
        encoded = json.dumps(legacy_pins, sort_keys=True, separators=(',', ':')).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(), LEGACY_FILES_SHA256)
        _, payloads = avatar.package(self.assets)
        # Reproduce the old install's immutable files without calling the new installer.
        for name in LEGACY_FILES:
            target = self.work/name; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payloads[name]); target.chmod(0o444)
            os.utime(target, (avatar.client.CACHE_EPOCH,)*2)
        imported = self.root/'imported.geo'; imported.write_bytes(b'original imported bytes')
        (self.work/'data/original.geo').symlink_to(imported)
        identity = self.work/'client-work.json'; identity.write_text('{"original_identity":true}\n')
        cache = self.work/'data/bin/generated.bin'; cache.parent.mkdir(); cache.write_bytes(b'private cache')
        def snapshot(paths):
            return {path: (path.read_bytes(), path.stat().st_ino, path.stat().st_mode,
                           path.stat().st_mtime_ns) for path in paths}
        before = snapshot([*(self.work/name for name in LEGACY_FILES), imported, identity, cache])
        proof = avatar.install(self.work, self.assets, self.context)
        self.assertEqual((proof['installed_files'], proof['reused_files'], proof['file_count']), (8, 13, 21))
        self.assertEqual(before, snapshot(before))
        self.assertEqual(set(payloads), set(avatar.ALLOWED))
        for name, content in payloads.items():
            self.assertEqual((self.work/name).read_bytes(), content)
        self.assertFalse(proof['imported_files_modified'])
        self.assertFalse(proof['cache_files_modified'])
        self.assertFalse(proof['worktree_identity_modified'])
        self.assertFalse((self.work/'character-avatar-applied.json').exists())

    def test_upgrade_from_clear_twenty_preserves_installed_files_and_adds_only_glove_geometry(self):
        previous = sorted(avatar.ALLOWED - {SMOOTH_GLOVE_FILE})
        pins = {name: self.manifest['files'][name] for name in previous}
        encoded = json.dumps(pins, sort_keys=True, separators=(',', ':')).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(), CLEAR_TWENTY_FILES_SHA256)
        _, payloads = avatar.package(self.assets)
        for name in previous:
            path = self.work/name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payloads[name]); path.chmod(0o444)
            os.utime(path, (avatar.client.CACHE_EPOCH,)*2)
        def snapshot():
            return {name: ((self.work/name).read_bytes(), (self.work/name).stat().st_ino,
                           (self.work/name).stat().st_mode, (self.work/name).stat().st_mtime_ns)
                    for name in previous}
        before = snapshot()
        proof = avatar.install(self.work, self.assets, self.context)
        self.assertEqual((proof['installed_files'], proof['reused_files']), (1, 20))
        self.assertEqual(snapshot(), before)
        self.assertEqual((self.work/SMOOTH_GLOVE_FILE).read_bytes(), payloads[SMOOTH_GLOVE_FILE])

    def test_conflicting_existing_asset_is_preserved_and_no_other_file_is_installed(self):
        path = self.work/self.first; path.parent.mkdir(parents=True); path.write_bytes(b'existing')
        with self.assertRaises(avatar.client.base.DiagnosticError): avatar.install(self.work, self.assets, self.context)
        self.assertEqual(path.read_bytes(), b'existing')
        self.assertEqual(sum((self.work/name).exists() for name in avatar.ALLOWED), 1)

    def test_reuse_detects_changed_bytes_mode_timestamp_and_hardlinks(self):
        for change in ('content', 'mode', 'timestamp', 'hardlink'):
            with self.subTest(change=change):
                work = self.root/change; (work/'data').mkdir(parents=True)
                avatar.install(work, self.assets, self.context); path = work/self.first
                if change == 'content':
                    path.chmod(0o600); raw = bytearray(path.read_bytes()); raw[-1] ^= 1
                    path.write_bytes(raw); path.chmod(0o444)
                    os.utime(path, (avatar.client.CACHE_EPOCH, avatar.client.CACHE_EPOCH))
                elif change == 'mode': path.chmod(0o600)
                elif change == 'timestamp': os.utime(path, (avatar.client.CACHE_EPOCH+1,)*2)
                else: os.link(path, work/'linked-copy')
                with self.assertRaises(avatar.client.base.DiagnosticError): avatar.install(work, self.assets, self.context)

    def test_target_and_parent_symlinks_cannot_modify_external_files(self):
        external = self.root/'external'; external.mkdir()
        original = external/'male_boot.geo'; original.write_bytes(b'untouched')
        for kind in ('target', 'parent', 'dangling_parent'):
            with self.subTest(kind=kind):
                work = self.root/kind; (work/'data').mkdir(parents=True)
                if kind == 'target':
                    (work/'data/player_library').mkdir(); (work/self.first).symlink_to(original)
                else: (work/'data/player_library').symlink_to(external if kind == 'parent' else external/'missing')
                with self.assertRaises((avatar.client.base.DiagnosticError, OSError)):
                    avatar.install(work, self.assets, self.context)
                self.assertEqual(original.read_bytes(), b'untouched')
                self.assertFalse((work/'data/texture_library').exists())

    def test_case_only_aliases_and_duplicate_case_names_are_refused(self):
        for kind in ('parent', 'target', 'duplicate'):
            with self.subTest(kind=kind):
                work = self.root/kind; (work/'data').mkdir(parents=True)
                if kind == 'parent': (work/'data/PLAYER_LIBRARY').mkdir()
                else:
                    (work/'data/player_library').mkdir()
                    (work/'data/player_library/MALE_BOOT.geo').write_bytes(b'alias')
                    if kind == 'duplicate': (work/self.first).write_bytes(b'other')
                with self.assertRaisesRegex(avatar.client.base.DiagnosticError, 'Case-conflicting'):
                    avatar.install(work, self.assets, self.context)

    def test_pinned_archive_and_manifest_tampering_fail_before_install(self):
        for changed in (avatar.ARCHIVE, avatar.MANIFEST):
            assets = self.root/changed; assets.mkdir()
            for name in (avatar.ARCHIVE, avatar.MANIFEST): shutil.copyfile(self.assets/name, assets/name)
            path = assets/changed; raw = bytearray(path.read_bytes()); raw[-1] ^= 1; path.write_bytes(raw)
            with self.assertRaises(avatar.client.base.DiagnosticError): avatar.install(self.work, assets, self.context)
            self.assertFalse(any((self.work/name).exists() for name in avatar.ALLOWED))

    def test_interrupted_install_reuses_completed_files_on_retry(self):
        checks = 0
        def check():
            nonlocal checks
            checks += 1
            if checks == len(avatar.ALLOWED) + 3: raise avatar.client.base.Cancelled('test cancellation')
        with self.assertRaises(avatar.client.base.Cancelled):
            avatar.install(self.work, self.assets, SimpleNamespace(check=check))
        proof = avatar.install(self.work, self.assets, self.context)
        self.assertEqual((proof['installed_files'], proof['reused_files']), (19, 2))
        self.assertFalse(list(self.work.rglob('.avatar-pending-*')))

    def test_character_initialize_installs_only_after_parent_prepares_worktree(self):
        d = guest.CharacterCreationDiagnostic.__new__(guest.CharacterCreationDiagnostic)
        state = self.root/'state'; state.mkdir()
        d.args = SimpleNamespace(state=state, assets=self.assets)
        d.ctx = SimpleNamespace(report={'asset_sha256': {name: 'pinned' for name in guest.REQUIRED}})
        order = []
        def parent_initialize():
            d.work = self.work
            order.append('parent')
        def install_avatar(*_args):
            order.append('avatar')
            return {'installed_files': 21}
        def install_world(*_args):
            order.append('world')
            return {'installed_files': 0}
        world = SimpleNamespace(install=Mock(side_effect=install_world))
        with patch.object(guest.login.ClientLoginDiagnostic, 'initialize', side_effect=parent_initialize), \
                patch.object(guest.avatar, 'install', side_effect=install_avatar) as install, \
                patch.dict(sys.modules, atlas_world_assets=world):
            d.initialize()
        install.assert_called_once_with(self.work, self.assets, d.ctx)
        self.assertEqual(d.ctx.report['character_avatar_supplement']['installed_files'], 21)
        world.install.assert_called_once_with(self.work, self.assets, d.ctx)
        self.assertEqual(d.ctx.report['atlas_world_supplement'], {'installed_files': 0})
        self.assertEqual(order, ['parent', 'avatar', 'world'])


if __name__ == '__main__': unittest.main()
