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


if __name__ == '__main__': unittest.main()
