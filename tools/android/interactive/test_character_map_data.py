"""Wine-visible real directories and isolated writable Atlas data."""
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import local_character_server as server


class CharacterMapDataTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.work = self.root/'work'; self.source = self.work/'data'; self.source.mkdir(parents=True)
        self.imported = self.root/'import'; self.imported.mkdir()
        self.target = self.root/'runtime'/'data'
        self.value = server.LocalCharacterServer.__new__(server.LocalCharacterServer)
        self.value.owner = SimpleNamespace(work=self.work, args=SimpleNamespace(game_data=self.imported))
        self.value.ctx = SimpleNamespace(check=Mock(), event=Mock())
        self.value.creation_report = {}

    def immutable(self, name, contents='accepted'):
        original = self.imported/name; original.parent.mkdir(parents=True, exist_ok=True)
        original.write_text(contents); original.chmod(0o444)
        source = self.source/name; source.parent.mkdir(parents=True, exist_ok=True); source.symlink_to(original)
        return original

    def test_nested_definitions_are_visible_without_following_directory_links(self):
        originals = [self.immutable(name) for name in ('defs/powers/set.def', 'defs/classes/class.def', 'maps/Atlas/a.txt')]
        result = self.value.stage_map_data(self.source, self.target)
        found = []
        pending = [self.target]
        while pending:
            with os.scandir(pending.pop()) as entries:
                for entry in entries:
                    if entry.is_dir(follow_symlinks=False):
                        self.assertFalse(entry.is_symlink()); pending.append(Path(entry.path))
                    else:
                        found.append(Path(entry.path).relative_to(self.target).as_posix())
        self.assertEqual(sorted(found), ['defs/classes/class.def', 'defs/powers/set.def', 'maps/Atlas/a.txt'])
        self.assertEqual(result['files'], 3)
        self.assertEqual(result['linked_immutable_files'], 3)
        self.assertEqual(result['copied_private_files'], 0)
        resolution = self.value.creation_report['cold_mirror_input_resolution']
        self.assertEqual(resolution['resolved_leaves'], 3)
        self.assertEqual(resolution['parent_directory_checks'], resolution['parent_metadata_rechecks'])
        for original in originals:
            target = self.target/original.relative_to(self.imported)
            self.assertTrue(target.is_symlink()); self.assertEqual(target.resolve(), original)
            self.assertEqual(original.stat().st_mode & 0o777, 0o444)

    def test_cold_mirror_uses_one_fresh_leaf_observation_and_bounded_parent_checks(self):
        import character_server_data_cache as cache
        originals = [self.immutable('defs/shared/leaf-' + str(i) + '.def') for i in range(256)]
        recorder = cache.ServerDataCache.__new__(cache.ServerDataCache)
        recorder.directory_names, recorder.private_names, recorder.anchor_names = [], [], {}
        actual_stat, actual_lstat = os.stat, os.lstat
        counts = {'stat': 0, 'lstat': 0}
        def measured(name, method):
            def call(*args, **kwargs):
                counts[name] += 1
                return method(*args, **kwargs)
            return call
        with patch.object(os, 'stat', side_effect=measured('stat', actual_stat)), \
                patch.object(os, 'lstat', side_effect=measured('lstat', actual_lstat)):
            result = self.value.stage_map_data(self.source, self.target, cache_recorder=recorder)
        self.assertEqual(result['files'], 256)
        self.assertEqual(result['linked_immutable_files'], 256)
        self.assertLess(sum(counts.values()), 4 * 256 + 128)
        self.assertEqual(len(recorder.anchor_names), 1)
        for original in originals:
            target = self.target / original.relative_to(self.imported)
            self.assertEqual(target.resolve(strict=True), original)
        self.assertEqual(self.value.creation_report['cold_mirror_input_resolution']['resolved_leaves'], 256)

    def test_existing_linked_leaf_and_dangling_destination_are_rejected(self):
        self.immutable('defs/leaf.def')
        (self.target / 'defs').mkdir(parents=True)
        leaf = self.target / 'defs/leaf.def'
        for original in (self.imported / 'defs/leaf.def', self.root / 'missing'):
            leaf.symlink_to(original)
            with self.assertRaisesRegex(server.base.DiagnosticError, 'Linked private destination'):
                self.value.stage_map_data(self.source, self.target)
            self.assertTrue(leaf.is_symlink())
            leaf.unlink()
        self.assertEqual((self.imported / 'defs/leaf.def').read_text(), 'accepted')

    def test_cache_config_and_dbidmap_files_remain_private_and_schema_wins(self):
        names = ('bin/powers.bin', 'geobin/city.bin', 'server/db/servers.cfg', 'defs/powers/ids.dbidmap')
        originals = [self.immutable(name) for name in names]
        self.target.joinpath('server/db').mkdir(parents=True)
        self.target.joinpath('server/db/servers.cfg').write_text('qualified schema')
        result = self.value.stage_map_data(self.source, self.target)
        self.assertEqual(result['linked_immutable_files'], 0)
        self.assertEqual(result['copied_private_files'], 3)
        self.assertEqual(result['preserved_schema_files'], 1)
        self.assertEqual(self.target.joinpath('server/db/servers.cfg').read_text(), 'qualified schema')
        for original in originals:
            target = self.target/original.relative_to(self.imported)
            self.assertFalse(target.is_symlink())
            target.write_text('owned mutation')
            self.assertEqual(original.read_text(), 'accepted')
            self.assertEqual(original.stat().st_mode & 0o777, 0o444)

    def test_writable_file_outside_cache_roots_is_copied(self):
        source = self.source/'generated.txt'; source.write_text('client state')
        result = self.value.stage_map_data(self.source, self.target)
        target = self.target/'generated.txt'
        self.assertFalse(target.is_symlink()); self.assertEqual(result['copied_private_files'], 1)
        target.write_text('map state'); self.assertEqual(source.read_text(), 'client state')

    def test_source_directory_symlink_is_rejected(self):
        directory = self.imported/'defs'; directory.mkdir()
        (self.source/'defs').symlink_to(directory, target_is_directory=True)
        with self.assertRaises(server.base.DiagnosticError):
            self.value.stage_map_data(self.source, self.target)
        self.assertFalse((self.target/'defs').exists())

    def test_file_link_cannot_escape_verified_roots(self):
        outside = self.root/'outside'; outside.write_text('outside'); outside.chmod(0o444)
        (self.source/'escape.def').symlink_to(outside)
        with self.assertRaisesRegex(server.base.DiagnosticError, 'escaped verified data roots'):
            self.value.stage_map_data(self.source, self.target)
        self.assertFalse((self.target/'escape.def').exists())

    def test_linked_destination_never_writes_through_to_import(self):
        self.immutable('defs/powers/set.def')
        self.target.mkdir(parents=True)
        (self.target/'defs').symlink_to(self.imported/'defs', target_is_directory=True)
        with self.assertRaisesRegex(server.base.DiagnosticError, 'Linked private destination'):
            self.value.stage_map_data(self.source, self.target)
        self.assertEqual((self.imported/'defs/powers/set.def').read_text(), 'accepted')

    def test_nonregular_file_and_file_count_bounds_are_enforced(self):
        os.mkfifo(self.source/'fifo')
        with self.assertRaisesRegex(server.base.DiagnosticError, 'Nonregular'):
            self.value.stage_map_data(self.source, self.target)
        (self.source/'fifo').unlink(); self.immutable('one.def')
        import client_visual_assets as visual
        with patch.object(server.device, 'DATA_COUNT', -4096 - server.world.FILE_COUNT - len(server.avatar.ALLOWED) - visual.FILE_COUNT):
            with self.assertRaisesRegex(server.base.DiagnosticError, 'count exceeded bound'):
                self.value.stage_map_data(self.source, self.target)
        with patch.object(server.device, 'DATA_BYTES', -1024**3 - server.world.PAYLOAD_BYTES - server.avatar.PAYLOAD_BYTES - visual.PAYLOAD_BYTES):
            with self.assertRaisesRegex(server.base.DiagnosticError, 'data exceeded bound'):
                self.value.stage_map_data(self.source, self.target)


class ServerdataProbeTests(unittest.TestCase):
    """CI-only shared read-only serverdata probe (COH_SERVERDATA_PROBE)."""
    immutable = CharacterMapDataTests.immutable

    def setUp(self):
        CharacterMapDataTests.setUp(self)
        self.value.owner.root = self.root / 'owner'; self.value.owner.root.mkdir()
        self.runtime = self.root / 'runtime'
        for name in ('data', 'tools'):
            (self.runtime / name).mkdir(parents=True, exist_ok=True)
        self.identity = {'format': 2, 'shared_server_data': {'format': 1, 'shared_top_level': ['scripts.loc']}}
        self.addCleanup(self.writable_again)

    def writable_again(self):
        for current, _directories, _files in os.walk(self.value.owner.root):
            os.chmod(current, 0o700)

    def test_switch_accepts_only_empty_zero_or_one(self):
        for value, expected in (('', 0), ('0', 0), ('1', 1), ('2', 2)):
            with self.subTest(value=value), patch.dict(os.environ, {server.SERVERDATA_PROBE_ENV: value}):
                self.assertEqual(server.serverdata_probe_requested(), expected)
        with patch.dict(os.environ, {server.SERVERDATA_PROBE_ENV: 'yes'}):
            with self.assertRaises(server.base.DiagnosticError):
                server.serverdata_probe_requested()

    def test_wide_level_keeps_private_and_proof_read_folders_in_the_private_tree(self):
        for name in ('bin/a.bin', 'Geobin/g.bin', 'server/db/x.cfg', 'defs/a.def', 'maps/m.txt',
                     'object_library/o.geo', 'tricks/t.txt', 'texture_library/t.texture',
                     'fx/f.fx', 'scripts.loc/s.storyarc', 'sequencers/q.txt', 'top.txt'):
            self.immutable(name)
        self.assertEqual(server.serverdata_probe_roots(1, self.source), ['scripts.loc'])
        self.assertEqual(server.serverdata_probe_roots(2, self.source), ['fx', 'scripts.loc', 'sequencers'])
        empty = self.root / 'empty'; empty.mkdir()
        with self.assertRaises(server.base.DiagnosticError):
            server.serverdata_probe_roots(2, empty)

    def test_split_mirror_skips_and_selects_top_level_folders_only(self):
        for name in ('scripts.loc/arcs/a.storyarc', 'Scripts.loc/b.taskset', 'defs/a.def', 'maps/scripts.loc/x.txt'):
            self.immutable(name)
        private = self.value.stage_map_data(self.source, self.target, skip_top_level=('scripts.loc',))
        self.assertFalse((self.target / 'scripts.loc').exists())
        self.assertFalse((self.target / 'Scripts.loc').exists())
        self.assertTrue((self.target / 'maps/scripts.loc/x.txt').is_symlink())
        self.assertEqual(private['files'], 2)
        shared = self.root / 'shared'
        selected = self.value.stage_map_data(self.source, shared, only_top_level=('scripts.loc',))
        self.assertEqual(selected['files'], 2)
        self.assertFalse((shared / 'defs').exists()); self.assertFalse((shared / 'maps').exists())
        self.assertTrue((shared / 'scripts.loc/arcs/a.storyarc').is_symlink())

    def test_shared_tree_is_built_once_sealed_read_only_and_linked(self):
        original = self.immutable('scripts.loc/arcs/a.storyarc')
        self.immutable('defs/a.def')
        self.value.creation_report['cold_mirror_input_resolution'] = {'resolved_leaves': 7}
        first = self.value.link_shared_server_data(self.runtime, self.identity)
        self.assertEqual(self.value.creation_report['cold_mirror_input_resolution'], {'resolved_leaves': 7})
        link = self.runtime / 'serverdata'
        self.assertTrue(link.is_symlink())
        self.assertEqual((link / 'scripts.loc/arcs/a.storyarc').resolve(), original)
        shared = link.resolve()
        self.assertEqual(shared.parent, self.value.owner.root)
        self.assertFalse((shared / 'defs').exists())
        for current, _directories, _files in os.walk(shared):
            self.assertEqual(os.stat(current).st_mode & 0o777, 0o500)
        self.assertFalse(first['reused_shared_tree']); self.assertEqual(first['shared_files'], 1)
        self.assertFalse(first['native_resolution_verified']); self.assertFalse(first['physical_gain_validated'])
        second_runtime = self.root / 'runtime-2'
        for name in ('data', 'tools'):
            (second_runtime / name).mkdir(parents=True)
        second = self.value.link_shared_server_data(second_runtime, self.identity)
        self.assertTrue(second['reused_shared_tree']); self.assertEqual(second['shared_tree'], first['shared_tree'])
        self.assertEqual((second_runtime / 'serverdata').resolve(), shared)

    def test_private_copy_existing_link_or_missing_tools_is_refused(self):
        self.immutable('scripts.loc/a.storyarc')
        (self.runtime / 'data/scripts.loc').mkdir()
        with self.assertRaisesRegex(server.base.DiagnosticError, 'still holds a shared folder'):
            self.value.link_shared_server_data(self.runtime, self.identity)
        (self.runtime / 'data/scripts.loc').rmdir()
        (self.runtime / 'serverdata').mkdir()
        with self.assertRaisesRegex(server.base.DiagnosticError, 'already has serverdata'):
            self.value.link_shared_server_data(self.runtime, self.identity)
        (self.runtime / 'serverdata').rmdir(); (self.runtime / 'tools').rmdir()
        with self.assertRaisesRegex(server.base.DiagnosticError, 'data/ and tools/ layout'):
            self.value.link_shared_server_data(self.runtime, self.identity)

    def test_changed_marker_is_refused_and_an_unsealed_tree_is_rebuilt(self):
        original = self.immutable('scripts.loc/a.storyarc')
        self.value.link_shared_server_data(self.runtime, self.identity)
        marker = next(self.value.owner.root.glob('shared-server-data-*.json'))
        marker.write_text('{"format": 1, "key": "other", "roots": ["scripts.loc"], "stats": {}}')
        (self.runtime / 'serverdata').unlink()
        with self.assertRaisesRegex(server.base.DiagnosticError, 'marker differs'):
            self.value.link_shared_server_data(self.runtime, self.identity)
        marker.unlink()                                   # a build stopped before its marker
        rebuilt = self.value.link_shared_server_data(self.runtime, self.identity)
        self.assertEqual(rebuilt['removed'], {'unsealed_trees': 1, 'other_identity_trees': 0})
        self.assertFalse(rebuilt['reused_shared_tree'])
        self.assertEqual((self.runtime / 'serverdata/scripts.loc/a.storyarc').resolve(), original)

    def test_a_new_identity_removes_older_trees_and_never_their_targets(self):
        original = self.immutable('scripts.loc/a.storyarc')
        self.value.link_shared_server_data(self.runtime, self.identity)
        old = next(path for path in self.value.owner.root.iterdir() if not path.name.endswith('.json'))
        other = self.root / 'runtime-3'
        for name in ('data', 'tools'):
            (other / name).mkdir(parents=True)
        newer = dict(self.identity, format=3)
        result = self.value.link_shared_server_data(other, newer)
        self.assertEqual(result['removed']['other_identity_trees'], 1)
        self.assertFalse(old.exists()); self.assertFalse((self.value.owner.root / (old.name + '.json')).exists())
        self.assertEqual(original.read_text(), 'accepted')
        self.assertEqual(sorted(path.name.endswith('.json') for path in self.value.owner.root.iterdir()), [False, True])

    def test_tree_removal_refuses_regular_files_and_foreign_paths(self):
        self.immutable('scripts.loc/a.storyarc')
        self.value.link_shared_server_data(self.runtime, self.identity)
        shared = (self.runtime / 'serverdata').resolve()
        os.chmod(shared / 'scripts.loc', 0o700)
        (shared / 'scripts.loc/real.txt').write_text('data')
        with self.assertRaisesRegex(server.base.DiagnosticError, 'regular file'):
            self.value.remove_shared_tree(shared)
        self.assertTrue((shared / 'scripts.loc/real.txt').exists())
        elsewhere = self.root / 'shared-server-data-elsewhere'; elsewhere.mkdir()
        with self.assertRaisesRegex(server.base.DiagnosticError, 'unexpected shared server data path'):
            self.value.remove_shared_tree(elsewhere)

    def test_app_selection_is_off_by_default_and_ci_probe_overrides_it(self):
        for name in ('scripts.loc/s.storyarc', 'fx/f.fx', 'sequencers/q.txt', 'player_library/p.txt',
                     'defs/a.def', 'Texts/t.ms'):
            self.immutable(name)
        with patch.dict(os.environ, {server.SHARED_SERVER_ENV: '', server.SERVERDATA_PROBE_ENV: ''}):
            self.assertIsNone(server.shared_server_selection(self.source))
        with patch.dict(os.environ, {server.SHARED_SERVER_ENV: '1', server.SERVERDATA_PROBE_ENV: ''}):
            value = server.shared_server_selection(self.source)
        self.assertEqual(value['shared_top_level'], ['Texts', 'fx', 'scripts.loc'])
        self.assertEqual(value['selection'], 'app_default_folders_v1')
        with patch.dict(os.environ, {server.SHARED_SERVER_ENV: '1', server.SERVERDATA_PROBE_ENV: '1'}):
            self.assertEqual(server.shared_server_selection(self.source)['shared_top_level'], ['scripts.loc'])
        with patch.dict(os.environ, {server.SHARED_SERVER_ENV: 'yes'}), self.assertRaises(server.base.DiagnosticError):
            server.shared_server_requested()
        self.assertTrue({'sequencers', 'player_library'}.isdisjoint(server.SHARED_SERVER_FOLDERS))
        self.assertTrue(server.SERVERDATA_PROBE_KEEP.isdisjoint(server.SHARED_SERVER_FOLDERS))


if __name__ == '__main__': unittest.main()
