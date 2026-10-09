"""Client animation-link boundaries; synthetic tracks never qualify performance."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
sys.path.insert(0, str(ROOT / 'tools'))
import client_animation_package as package
import server_animation_package as animation

spec = importlib.util.spec_from_file_location('client_animation_fixture',
    ROOT / 'tools/android/atlasgame/test_server_animations.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class ClientAnimationPackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.assets = self.root / 'assets'; self.assets.mkdir()
        self.work = self.root / ('client-work-' + 'a' * 24); self.work.mkdir()
        (self.work / 'tools').mkdir(); (self.work / 'data').mkdir()
        self.source = self.root / 'import/data'; self.source.mkdir(parents=True)
        (self.source.parent / 'complete.properties').write_text(
            'generation=generation-' + 'b' * 32 + '\ncontract.sha256=' + 'c' * 64
            + '\ncount=173011\nbytes=2977730517\n')
        self.bodies, self.files = fixture.inputs()
        for name, body in self.bodies.items():
            original = self.source / name; original.parent.mkdir(parents=True, exist_ok=True)
            original.write_bytes(body); original.chmod(0o444)
            os.utime(original, (animation.caches.EPOCH, animation.caches.EPOCH))
            loose = self.work / 'data' / name; loose.parent.mkdir(parents=True, exist_ok=True)
            loose.symlink_to(original)
        self.pigg = self.assets / animation.PIGG
        pigg_pin, _ = fixture.producer.write_pigg(self.pigg, self.files, self.bodies.__getitem__)
        self.manifest = self.assets / animation.MANIFEST
        self.document = {'format': 1, 'role': animation.ROLE,
            'repository_commit': 'd' * 40, 'identity': animation.identity(),
            'files': self.files, 'pigg': pigg_pin, 'loose_inputs_preserved': True,
            'native_client_or_server_recompiled': False,
            'android_execution_validated': False, 'physical_startup_timing_validated': False}
        self.manifest.write_bytes(animation.canonical(self.document))
        executable = b'Game native fixture'
        (self.work / 'CityOfHeroes.exe').write_bytes(executable)
        self.native_package = {'source_commit': package.client.SOURCE,
            'data_commit': package.client.DATA,
            'files': {'CityOfHeroes.exe': {'size': len(executable),
                'sha256': hashlib.sha256(executable).hexdigest(), 'pe_machine': 0x14c}}}
        self.archive = self.assets / 'client-runtime.zip'
        with zipfile.ZipFile(self.archive, 'w') as output:
            output.writestr('CityOfHeroes.exe', executable)
        self.receipt = {'format': 1, 'source_data': str(self.source),
            'import': package.client.import_identity(self.source),
            'package_sha256': package.client.base.file_hash(self.archive),
            'cache_archive_sha256': 'e' * 64, 'prerequisites_archive_sha256': 'f' * 64,
            'prerequisites_manifest_sha256': package.client.PREREQUISITES_MANIFEST_SHA,
            'normalized_mtime_epoch': package.client.CACHE_EPOCH,
            'worktree_key': self.work.name}
        self.receipt['content_identity_sha256'] = package.client.identity_sha256({
            'data': package.client.worktree_data_identity(self.receipt),
            'native': package.client.native_closure_identity(self.native_package)})
        self.write_receipt()
        # Small native/animation fixtures exercise installer decisions. Actual
        # runtime qualification validates archive_manifest without these mocks
        # and the existing full 5,878-track pack using verify_package directly.
        original = animation.validate_inventory
        patch = mock.patch.object(animation, 'validate_inventory',
            side_effect=lambda files, **_kw: original(files, exact=False))
        patch.start(); self.addCleanup(patch.stop)
        patch = mock.patch.object(package.client, 'archive_manifest', return_value=self.native_package)
        patch.start(); self.addCleanup(patch.stop)

    def write_receipt(self):
        (self.work / 'client-work.json').write_bytes(animation.canonical(self.receipt))

    def install(self, **kwargs):
        return package.install(self.pigg, self.manifest, self.work, assets=self.assets, **kwargs)

    def test_install_and_reuse_without_payload_copy_or_loose_changes(self):
        before = {name: (self.source / name).read_bytes() for name in self.files}
        first, second = self.install(), self.install()
        self.assertFalse(first['reused']); self.assertTrue(second['reused'])
        self.assertEqual(first['additional_animation_payload_bytes'], 0)
        self.assertTrue(first['verified_payload_read_only'])
        self.assertFalse(first['native_animation_reader_changed'])
        self.assertFalse(first['physical_startup_timing_validated'])
        self.assertTrue(first['loose_inputs_preserved'])
        self.assertEqual(first['client_contract']['loose_animation_count'], 2)
        target = self.work / 'piggs' / animation.PIGG
        self.assertTrue(target.is_symlink()); self.assertEqual(target.resolve(), self.pigg)
        self.assertEqual({name: (self.source / name).read_bytes() for name in self.files}, before)
        self.assertEqual(set(p.name for p in (self.work / 'piggs').iterdir()), {animation.PIGG, package.MARKER})

    def test_missing_optional_inputs_leave_worktree_untouched(self):
        self.pigg.unlink(); self.manifest.unlink()
        before = set(self.work.iterdir())
        self.assertFalse(self.install()['installed'])
        self.assertEqual(set(self.work.iterdir()), before)

    def test_partial_inputs_refuse_before_any_output(self):
        self.manifest.unlink()
        with self.assertRaises(ValueError): self.install()
        self.assertFalse((self.work / 'piggs').exists())

    def test_corrupt_pack_payload_refused_without_override(self):
        data = bytearray(self.pigg.read_bytes()); data[-1] ^= 1; self.pigg.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'payload differs'): self.install()
        self.assertFalse((self.work / 'piggs').exists())

    def test_linked_pack_or_manifest_refused(self):
        for path in (self.pigg, self.manifest):
            with self.subTest(name=path.name):
                target = self.root / ('original-' + path.name)
                path.rename(target); path.symlink_to(target)
                with self.assertRaises(ValueError): self.install()
                path.unlink(); target.rename(path)

    def test_wrong_source_or_data_package_rejected(self):
        for key in ('source_commit', 'data_commit'):
            value = self.native_package[key]; self.native_package[key] = '0' * 40
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'source or original asset closure'):
                self.install()
            self.native_package[key] = value

    def test_actual_game_mutation_rejected(self):
        (self.work / 'CityOfHeroes.exe').write_bytes(b'Game native fixture CORRUPT')
        with self.assertRaisesRegex(ValueError, 'actual Game identity'): self.install()

    def test_native_zip_wrapper_or_content_identity_mutation_rejected(self):
        for key in ('package_sha256', 'content_identity_sha256'):
            old = self.receipt[key]; self.receipt[key] = '0' * 64; self.write_receipt()
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'native/data content identity'):
                self.install()
            self.receipt[key] = old; self.write_receipt()

    def test_changed_import_generation_rejected(self):
        (self.source.parent / 'complete.properties').write_text(
            'generation=generation-' + '0' * 32 + '\ncontract.sha256=' + 'c' * 64
            + '\ncount=173011\nbytes=2977730517\n')
        with self.assertRaisesRegex(ValueError, 'import generation'): self.install()

    def test_worktree_receipt_and_executable_symlinks_rejected(self):
        for name in ('client-work.json', 'CityOfHeroes.exe'):
            path = self.work / name; original = self.root / ('original-' + name)
            path.rename(original); path.symlink_to(original)
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'Linked or foreign'):
                self.install()
            path.unlink(); original.rename(path)

    def test_loose_source_size_mtime_writability_and_missing_binding_rejected(self):
        name = next(iter(self.files)); source = self.source / name
        for change in ('size', 'mtime', 'writable', 'missing'):
            with self.subTest(change=change):
                if change == 'size': source.chmod(0o600); source.write_bytes(b'corrupt'); source.chmod(0o444)
                elif change == 'mtime': os.utime(source, (0, 0))
                elif change == 'writable': source.chmod(0o644)
                else: (self.work / 'data' / name).unlink()
                with self.assertRaisesRegex(ValueError, 'loose animation binding'): self.install()
                source.chmod(0o600); source.write_bytes(self.bodies[name]); source.chmod(0o444)
                os.utime(source, (animation.caches.EPOCH, animation.caches.EPOCH))
                loose = self.work / 'data' / name
                if not os.path.lexists(loose): loose.symlink_to(source)

    def test_foreign_loose_animation_link_is_rejected(self):
        name = next(iter(self.files)); other = self.root / 'other.anim'; other.write_bytes(self.bodies[name])
        loose = self.work / 'data' / name; loose.unlink(); loose.symlink_to(other)
        with self.assertRaisesRegex(ValueError, 'loose animation binding'): self.install()

    def test_linked_ancestor_in_import_or_worktree_is_rejected(self):
        for base in (self.source, self.work / 'data'):
            path = base / 'player_library'; old = base / 'saved-player-library'
            path.rename(old); path.symlink_to(old)
            with self.subTest(base=str(base)), self.assertRaisesRegex(ValueError, 'animation directory'):
                self.install()
            path.unlink(); old.rename(path)

    def test_foreign_pigg_directory_and_unreceipted_link_are_rejected(self):
        directory = self.work / 'piggs'; directory.mkdir()
        foreign = directory / 'foreign.pigg'; foreign.write_bytes(b'foreign')
        with self.assertRaisesRegex(ValueError, 'Foreign client animation Pig directory'): self.install()
        foreign.unlink(); (directory / animation.PIGG).symlink_to(self.pigg)
        with self.assertRaisesRegex(ValueError, 'unreceipted'): self.install()

    def test_linked_pigg_directory_is_rejected(self):
        outside = self.root / 'outside'; outside.mkdir()
        (self.work / 'piggs').symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'animation directory'): self.install()
        self.assertEqual(list(outside.iterdir()), [])

    def test_foreign_destination_regular_file_not_overwritten(self):
        self.install(); target = self.work / 'piggs' / animation.PIGG
        target.unlink(); target.write_bytes(b'do not overwrite')
        with self.assertRaisesRegex(ValueError, 'unreceipted'): self.install()
        self.assertEqual(target.read_bytes(), b'do not overwrite')

    def test_marker_corruption_is_rejected(self):
        self.install(); marker = self.work / 'piggs' / package.MARKER
        document = json.loads(marker.read_bytes()); document['pigg']['sha256'] = '0' * 64
        marker.write_bytes(animation.canonical(document))
        with self.assertRaisesRegex(ValueError, 'ownership receipt'): self.install()

    def test_other_destination_link_is_rejected(self):
        self.install(); target = self.work / 'piggs' / animation.PIGG
        target.unlink(); target.symlink_to(self.root / 'unknown.pigg')
        with self.assertRaisesRegex(ValueError, 'unreceipted'): self.install()

    def test_marker_only_interruption_resumes(self):
        self.install(); (self.work / 'piggs' / animation.PIGG).unlink()
        self.assertFalse(self.install()['reused']); self.assertTrue(self.install()['reused'])

    def refresh_assets(self):
        old_assets = self.root / 'old-assets'
        self.assets.rename(old_assets)
        shutil.copytree(old_assets, self.assets)
        return old_assets

    def test_runtime_asset_rebind_preserves_payload_and_old_resource(self):
        self.install()
        old = self.refresh_assets()
        marker = self.work / 'piggs' / package.MARKER
        prior = json.loads(marker.read_bytes()); prior['target'] = str(old / animation.PIGG)
        marker.write_bytes(animation.canonical(prior))
        target = self.work / 'piggs' / animation.PIGG
        target.unlink(); target.symlink_to(old / animation.PIGG)
        result = self.install()
        self.assertFalse(result['reused']); self.assertTrue(self.install()['reused'])
        self.assertEqual(target.resolve(), self.pigg)
        self.assertTrue((old / animation.PIGG).is_file())
        self.assertEqual(result['additional_animation_payload_bytes'], 0)

    def test_interrupted_rebind_to_verified_current_asset_repairs_marker(self):
        self.install()
        marker = self.work / 'piggs' / package.MARKER
        prior = json.loads(marker.read_bytes())
        prior['target'] = str(self.root / 'retired-runtime-assets' / animation.PIGG)
        marker.write_bytes(animation.canonical(prior))
        # Current verified link + old compatible marker is the only interrupted
        # rebind state accepted; arbitrary destinations still fail above.
        self.assertFalse(self.install()['reused'])
        self.assertTrue(self.install()['reused'])

    def test_changed_previous_resource_is_refused_during_rebind(self):
        self.install(); old = self.root / 'old-assets'; old.mkdir()
        old_pigg = old / animation.PIGG; old_pigg.write_bytes(b'corrupt')
        marker = self.work / 'piggs' / package.MARKER
        prior = json.loads(marker.read_bytes()); prior['target'] = str(old_pigg)
        marker.write_bytes(animation.canonical(prior))
        target = self.work / 'piggs' / animation.PIGG
        target.unlink(); target.symlink_to(old_pigg)
        with self.assertRaisesRegex(ValueError, 'Previous client animation resource differs'):
            self.install()
        self.assertEqual(os.readlink(target), str(old_pigg))

    def test_linked_old_resource_is_refused_during_rebind(self):
        self.install(); old = self.root / 'old-assets'; old.mkdir()
        old_pigg = old / animation.PIGG; old_pigg.symlink_to(self.pigg)
        marker = self.work / 'piggs' / package.MARKER
        prior = json.loads(marker.read_bytes()); prior['target'] = str(old_pigg)
        marker.write_bytes(animation.canonical(prior))
        target = self.work / 'piggs' / animation.PIGG
        target.unlink(); target.symlink_to(old_pigg)
        with self.assertRaisesRegex(ValueError, 'Linked or foreign client animation file'):
            self.install()

    def test_linked_lexical_asset_parent_is_rejected(self):
        parent = self.root / 'linked-parent'; parent.symlink_to(self.root, target_is_directory=True)
        linked_assets = parent / 'assets'
        with self.assertRaisesRegex(ValueError, 'animation directory'):
            package.install(linked_assets / animation.PIGG, linked_assets / animation.MANIFEST,
                            self.work, assets=linked_assets)

    def test_linked_lexical_runtime_parent_is_rejected(self):
        parent = self.root / 'linked-parent'; parent.symlink_to(self.root, target_is_directory=True)
        linked_work = parent / self.work.name
        with self.assertRaisesRegex(ValueError, 'animation directory'):
            package.install(self.pigg, self.manifest, linked_work, assets=self.assets)

    def test_linked_lexical_import_parent_is_rejected(self):
        parent = self.root / 'linked-parent'; parent.symlink_to(self.root, target_is_directory=True)
        self.receipt['source_data'] = str(parent / 'import/data'); self.write_receipt()
        with self.assertRaisesRegex(ValueError, 'animation directory'): self.install()

    def test_hardlinked_runtime_pack_and_manifest_are_refused(self):
        for path in (self.pigg, self.manifest):
            extra = self.root / ('hardlink-' + path.name); os.link(path, extra)
            with self.subTest(name=path.name), self.assertRaisesRegex(ValueError, 'animation file'):
                self.install()
            extra.unlink()

    def test_foreign_owned_runtime_resource_is_refused(self):
        actual = Path.lstat
        def foreign(path):
            observed = actual(path)
            if path == self.pigg:
                fields = list(observed); fields[4] += 1
                return os.stat_result(fields)
            return observed
        with mock.patch.object(Path, 'lstat', foreign):
            with self.assertRaisesRegex(ValueError, 'foreign client animation file'): self.install()
        self.assertFalse((self.work / 'piggs').exists())

    def test_cancelled_publication_leaves_no_link_or_temporaries(self):
        class Cancelled:
            def __init__(self): self.calls = 0
            def check(self):
                self.calls += 1
                if self.calls == 7: raise RuntimeError('cancelled publication')
        context = Cancelled()
        with self.assertRaisesRegex(RuntimeError, 'cancelled publication'):
            self.install(context=context)
        self.assertFalse(os.path.lexists(self.work / 'piggs' / animation.PIGG))
        self.assertFalse(any(path.name.startswith('client-animation-') for path in self.work.iterdir()))
        self.assertFalse(self.install()['reused'])

    def test_missing_optional_input_cannot_leave_old_packed_override(self):
        self.install(); self.pigg.unlink(); self.manifest.unlink()
        with self.assertRaisesRegex(ValueError, 'disappeared'): self.install()

    def test_cancelled_verification_has_no_packed_output(self):
        class Cancelled:
            def check(self): raise RuntimeError('cancelled')
        with self.assertRaisesRegex(RuntimeError, 'cancelled'): self.install(context=Cancelled())
        self.assertFalse((self.work / 'piggs').exists())

    def test_exact_accepted_inventory_and_shared_loader_source_are_retained(self):
        files = fixture.producer.accepted_inventory()
        self.assertEqual(len(files), 5878)
        self.assertEqual(sum(row['bytes'] for row in files.values()), 88380730)
        baseline = json.loads((ROOT / 'docs/source-manifest.json').read_bytes())
        pins = {entry['path']: entry for entry in baseline['entries']}
        for name in ('Common/seq/animtrack.c', 'Common/seq/seqload.c',
                     'libs/UtilitiesLib/src/utils/PigFileWrapper.c',
                     'libs/UtilitiesLib/src/utils/FolderCache.c',
                     'libs/UtilitiesLib/src/utils/piglib.c'):
            with self.subTest(source=name):
                self.assertEqual(animation.file_pin(ROOT / 'upstream/ouroboros' / name),
                    {'bytes': pins[name]['size'], 'sha256': pins[name]['sha256']})


if __name__ == '__main__':
    unittest.main()
