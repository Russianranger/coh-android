"""0.13.85: the Primalist's definition files (armport/content/single-player) and their installer.

Reads only armport/ and android/guest (the build's unit-test job checks out no game data);
the comparison with the game text runs where upstream/i24 is present.
"""
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'armport/app'), str(ROOT / 'android/guest')]
import single_player_content as content
import stage_app_assets

FOLDER = ROOT / 'armport/content/single-player'
UPSTREAM = ROOT / 'upstream/i24/data'


def parse6(names, body=b'\0\0\0\0'):
    """A Parse6 bin whose Files1 table lists `names`."""
    def string(value):
        raw = struct.pack('<H', len(value)) + value
        return raw + b'\0' * (-len(raw) % 4)
    table = struct.pack('<I', len(names)) + b''.join(string(name.encode()) + struct.pack('<I', 1767225600)
                                                     for name in names)
    return (b'CrypticS' + struct.pack('<I', 0x1234) + string(b'Parse6') + string(b'Files1')
            + struct.pack('<I', len(table)) + table + struct.pack('<I', len(body)) + body)


class Folder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((FOLDER / 'manifest.json').read_text())
        cls.files = cls.manifest['files']

    def test_the_manifest_lists_exactly_the_folder(self):
        on_disk = {path.relative_to(FOLDER / 'data').as_posix() for path in (FOLDER / 'data').rglob('*')
                   if path.is_file()}
        self.assertEqual(on_disk, set(self.files))
        for name, record in self.files.items():
            data = (FOLDER / 'data' / name).read_bytes()
            self.assertEqual((len(data), hashlib.sha256(data).hexdigest()), (record['bytes'], record['sha256']), name)
        self.assertEqual(hashlib.sha256(json.dumps(self.files, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                         self.manifest['files_sha256'])

    def test_it_is_the_primalist_and_nothing_else(self):
        replaced = sorted(name for name, record in self.files.items() if 'replaces' in record)
        added = sorted(name for name, record in self.files.items() if 'replaces' not in record)
        self.assertEqual(len(self.files), 39)
        self.assertEqual([name for name in replaced if not name.startswith('defs/powers/')],
                         ['defs/classes.def', 'texts/english/classes/classes.def.ms', 'texts/english/menumessages.ms'])
        powers = [name[len('defs/powers/'):] for name in replaced if name.startswith('defs/powers/')]
        self.assertEqual(len(powers), 18)
        self.assertTrue(all(name.startswith(('feral_might_', 'primal_gifts_', 'primalist_misc_')) for name in powers))
        self.assertEqual(added[0], 'defs/classes/pc_primalist.def')
        self.assertEqual(len(added), 18)
        self.assertTrue(all(name.startswith('menu/powers/animfx/playerpowers/primalist_') and name.endswith('.pfx')
                            for name in added[1:]))
        # Every animation file a power names is one of the added files or was already in the game text.
        import re
        wanted = set()
        for name in powers:
            text = (FOLDER / 'data/defs/powers' / name).read_text(encoding='latin1')
            self.assertNotIn('accesslevel', text, name)          # no developer-only lock
            for match in re.finditer(r'(?im)^\s*(?:VisualFX|include)\s+"?([^"\r\n]+\.pfx)"?', text):
                wanted.add(match.group(1).strip().replace('\\', '/').casefold())
        mine = {name for name in wanted if '/primalist_' in name}
        self.assertEqual(mine, set(added[1:]))

    def test_the_class_keeps_its_own_lock_and_the_class_list_includes_it(self):
        text = (FOLDER / 'data/defs/classes/pc_primalist.def').read_text()
        self.assertIn('Name\t\t\t\t\t"Class_Primalist"', text)
        self.assertIn('PrimaryCategory\t\t\t"Feral_Might"', text)
        self.assertIn('SecondaryCategory\t\t"Primal_Gifts"', text)
        # The client's bins always hold the class; it is selectable only when the session turns the
        # Primalist on (patch 0136 owns "ctatprim" with ARMPORT_PRIMALIST=1 and never through unlock-all).
        self.assertIn('StoreRequires\t\t\t"ctatprim ProductOwned?"', text)
        self.assertIn('ProductCode\t\t\t"ctatprim"', text)
        self.assertIn('LockedTooltip\t\t\t"P1372576813"', text)
        strings = (FOLDER / 'data/texts/english/classes/classes.def.ms').read_text(encoding='utf-8-sig')
        locked = [line for line in strings.splitlines() if line.startswith('"P1372576813" ')]
        self.assertEqual(len(locked), 1)
        self.assertEqual(locked[0].count('"'), 4)                 # no quote inside the text
        self.assertIn("'Primalist archetype'", locked[0])
        patch = (ROOT / 'armport/patches/0136-armport-single-player-unlock.patch').read_text()
        self.assertIn('skuIdFromString("ctatprim")', patch)
        self.assertIn('\ninclude defs/classes/PC_Primalist.def\n',
                      (FOLDER / 'data/defs/classes.def').read_text())
        self.assertIn('"P297054078" "Primalist"\n',
                      (FOLDER / 'data/texts/english/classes/classes.def.ms').read_text(encoding='utf-8-sig'))
        self.assertIn('"PrimalEnergyTip",\t\t"Primal Energy: {current}/{total}"\n',
                      (FOLDER / 'data/texts/english/menumessages.ms').read_text(encoding='utf-8-sig'))

    @unittest.skipUnless((UPSTREAM / 'defs/classes.def').is_file(), 'game text is not checked out here')
    def test_each_replaced_file_was_made_from_the_game_text_as_it_is_now(self):
        for name, record in self.files.items():
            base = record.get('replaces')
            if base is None:
                self.assertFalse((UPSTREAM / name).exists(), name)
                continue
            self.assertEqual(base['path'].casefold(), name)
            self.assertEqual(hashlib.sha256((UPSTREAM / base['path']).read_bytes()).hexdigest(), base['sha256'], name)
        # The two text files and the class list differ from the game text by added lines only.
        import difflib
        for name in ('defs/classes.def', 'texts/english/classes/classes.def.ms', 'texts/english/menumessages.ms'):
            old = (UPSTREAM / name).read_bytes().split(b'\n')
            new = (FOLDER / 'data' / name).read_bytes().split(b'\n')
            removed = [line for line in difflib.ndiff([l.decode('latin1') for l in old],
                                                      [l.decode('latin1') for l in new]) if line.startswith('- ')]
            self.assertEqual(removed, ['- //include defs/classes/PC_Primalist.def'] if name == 'defs/classes.def' else [],
                             name)


class Archive(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.assets = self.root / 'assets'; self.assets.mkdir()
        (payload,) = stage_app_assets.single_player_content().values()
        (self.assets / content.ARCHIVE).write_bytes(payload)
        self.payload = payload

    def test_the_staged_archive_is_deterministic_and_loads(self):
        self.assertEqual(stage_app_assets.single_player_content()[content.ARCHIVE], self.payload)
        self.assertLess(len(self.payload), 2 * 1024 * 1024)
        loaded = content.load(self.assets)
        manifest = json.loads((FOLDER / 'manifest.json').read_text())
        self.assertEqual(loaded.identity, manifest['files_sha256'])
        self.assertEqual(loaded.summary()['files'], 39)
        self.assertEqual((loaded.summary()['replaced'], loaded.summary()['added']), (21, 18))
        self.assertEqual(set(loaded.selected(skip=('menu', 'texts'))), {n for n in manifest['files'] if n.startswith('defs/')})
        self.assertEqual({content.Content.top_level(loaded, n) for n in loaded.selected(only=('MENU', 'texts'))},
                         {'menu', 'texts'})
        self.assertIsNone(content.load(self.root))             # a package without the archive
        self.assertIn(content.ARCHIVE, __import__('build_thor_apk').ADDED_RUNTIME)
        self.assertIn('single_player_content.py', stage_app_assets.GUEST_DEPENDENCIES)

    def test_a_changed_member_is_refused(self):
        import zipfile
        changed = self.root / 'changed'; changed.mkdir()
        with zipfile.ZipFile(self.assets / content.ARCHIVE) as source, \
                zipfile.ZipFile(changed / content.ARCHIVE, 'w') as target:
            for info in source.infolist():
                data = source.read(info)
                if info.filename == 'data/defs/classes.def':
                    data = data.replace(b'PC_Primalist', b'PC_Primalisu')
                target.writestr(info.filename, data)
        with self.assertRaisesRegex(ValueError, 'digest differs'):
            content.load(changed)

    def mirror(self):
        """LocalCharacterServer over a small imported tree that has the files the content replaces."""
        import local_character_server as server
        work = self.root / 'work'; source = work / 'data'; source.mkdir(parents=True)
        imported = self.root / 'import'; imported.mkdir()
        value = server.LocalCharacterServer.__new__(server.LocalCharacterServer)
        value.owner = SimpleNamespace(work=work, args=SimpleNamespace(game_data=imported))
        value.ctx = SimpleNamespace(check=Mock(), event=Mock())
        value.creation_report = {}
        value.single_player_content = content.load(self.assets)
        names = [name for name, entry in value.single_player_content.files.items() if not entry['new']]
        names += ['defs/classes/pc_scrapper.def', 'menu/powers/animfx/playerpowers/other.pfx', 'maps/atlas/a.txt',
                  'texts/english/powers/epic_powers.ms']
        for name in names:
            original = imported / name; original.parent.mkdir(parents=True, exist_ok=True)
            original.write_text('imported'); original.chmod(0o444)
            link = source / name; link.parent.mkdir(parents=True, exist_ok=True); link.symlink_to(original)
        return value, source, imported

    def shared_setup(self, *, content_on):
        """A server over the small import, with the shared folders of the phone (menu, texts, fx)."""
        import local_character_server as server
        if not hasattr(self, 'shared_value'):
            value, source, imported = self.mirror()
            original = imported / 'fx/a.fx'; original.parent.mkdir(parents=True)
            original.write_text('imported'); original.chmod(0o444)
            (source / 'fx').mkdir(); (source / 'fx/a.fx').symlink_to(original)
            value.owner.root = self.root / 'owner-root'; value.owner.root.mkdir()
            value.owner.args.assets = self.assets
            self.shared_value, self.shared_content, self.shared_count = value, value.single_player_content, 0
        value = self.shared_value
        value.single_player_content = self.shared_content if content_on else None
        identity = {'format': 2, 'source': 'the import', 'shared_server_data': {
            'shared_top_level': ['fx', 'menu', 'texts'], 'selection': 'app_default_folders_v1', 'level': None}}
        if content_on:
            identity['single_player_content'] = self.shared_content.identity
        self.shared_count += 1
        runtime = self.root / ('shared-runtime-%d' % self.shared_count)
        for name in ('data', 'tools'):
            (runtime / name).mkdir(parents=True)
        return value, runtime, identity

    def shared_link(self, *, content_on):
        value, runtime, identity = self.shared_setup(content_on=content_on)
        result = value.link_shared_server_data(runtime, identity)
        served = {name: (runtime / 'serverdata' / name).resolve().parent.name for name in ('fx', 'menu', 'texts')}
        class_text = (runtime / 'serverdata/texts/english/classes/classes.def.ms').read_bytes()
        has_content = class_text == self.shared_content.files['texts/english/classes/classes.def.ms']['data']
        return result, served, has_content

    def test_only_the_folders_the_content_touches_get_a_second_shared_tree(self):
        """Thor 20261126-035051: the Primalist's first launch linked all 128,765 shared files again
        (335 s) and removed the other tree; only menu and texts differ (10,700 files)."""
        plain, plain_served, plain_content = self.shared_link(content_on=False)
        self.assertEqual((len(set(plain_served.values())), plain_content, plain['reused_shared_tree']), (1, False, False))
        self.assertEqual([row['kind'] for row in plain['shared_trees']], ['all_folders'])
        first, served, has_content = self.shared_link(content_on=True)
        self.assertTrue(has_content)
        self.assertEqual(served['fx'], plain_served['fx'])                    # untouched: the kept tree
        self.assertEqual(served['menu'], served['texts']); self.assertNotEqual(served['menu'], plain_served['menu'])
        self.assertEqual([(row['kind'], row['reused'], row['roots']) for row in first['shared_trees']],
                         [('content_folders', False, 2), ('all_folders_without_content', True, 3)])
        self.assertEqual(first['removed'], {'unsealed_trees': 0, 'other_identity_trees': 0})
        self.assertFalse(first['reused_shared_tree'])
        again, served_again, _ = self.shared_link(content_on=True)
        self.assertEqual((again['reused_shared_tree'], served_again), (True, served))
        back, back_served, back_content = self.shared_link(content_on=False)   # and the way back costs nothing
        self.assertEqual((back['reused_shared_tree'], back_served, back_content), (True, plain_served, False))

    def test_a_whole_tree_made_with_the_content_by_0_13_85_serves_both_states(self):
        value, runtime, identity = self.shared_setup(content_on=True)
        import hashlib, character_server_data_cache as cache
        key = hashlib.sha256(cache.canonical(identity)).hexdigest()[:24]
        old = value.shared_tree({'key': key, 'roots': ['fx', 'menu', 'texts'], 'kind': 'all_folders'}, {key},
                                {'unsealed_trees': 0, 'other_identity_trees': 0})[0]
        with_content, served, has_content = self.shared_link(content_on=True)
        self.assertEqual((with_content['reused_shared_tree'], set(served.values()), has_content), (True, {old.name}, True))
        plain, plain_served, plain_content = self.shared_link(content_on=False)
        self.assertFalse(plain_content)
        self.assertEqual(plain_served['fx'], old.name)                         # untouched folders: the 0.13.85 tree
        self.assertNotEqual(plain_served['menu'], old.name)
        self.assertEqual([(row['kind'], row['reused']) for row in plain['shared_trees']],
                         [('content_folders_without_content', False), ('all_folders_other_content_state', True)])
        self.assertTrue(old.is_dir())
        self.assertEqual(plain['removed']['other_identity_trees'], 0)

    def test_a_tree_of_another_source_is_still_removed(self):
        value, runtime, identity = self.shared_setup(content_on=False)
        stranger = value.owner.root / 'shared-server-data-0123456789abcdef01234567'
        (stranger / 'fx').mkdir(parents=True)
        (value.owner.root / (stranger.name + '.json')).write_text('{}')
        result = value.link_shared_server_data(runtime, identity)
        self.assertEqual(result['removed']['other_identity_trees'], 1)
        self.assertFalse(stranger.exists())

    def test_the_mirror_takes_private_copies_and_leaves_the_import_alone(self):
        import character_server_data_cache as cache
        value, source, imported = self.mirror()
        recorder = cache.ServerDataCache.__new__(cache.ServerDataCache)
        recorder.directory_names, recorder.private_names, recorder.anchor_names = [], [], {}
        target = self.root / 'runtime/data'
        result = value.stage_map_data(source, target, cache_recorder=recorder)
        files = value.single_player_content.files
        self.assertEqual(result['single_player_files'], 39)
        self.assertEqual(result['copied_private_files'], 0)
        for name, entry in files.items():
            path = target / name
            self.assertTrue(path.is_file() and not path.is_symlink(), name)
            self.assertEqual(path.read_bytes(), entry['data'], name)
            self.assertEqual((path.stat().st_mode & 0o777, int(path.stat().st_mtime)), (0o600, content.FILE_TIME))
            self.assertIn(name, recorder.private_names)
            if not entry['new']:
                self.assertEqual((imported / name).read_text(), 'imported')     # the import is untouched
        self.assertTrue((target / 'defs/classes/pc_scrapper.def').is_symlink())
        # A replaced file is never one of the cache's read-only anchors.
        self.assertFalse(set(recorder.anchor_names.values()) & set(files))
        self.assertEqual(list(target.rglob('*.single-player-pending')), [])

    def test_a_kept_tree_with_the_content_is_taken_again_by_the_next_session(self):
        """Run 45627352623: the receipt's own file count made the next session refuse the kept
        tree, so the zone server compiled all its files again on every launch."""
        import character_server_data_cache as cache
        value, source, imported = self.mirror()
        stale = parse6(['defs/classes.def'])
        for name in ('server/db/readme.txt', 'bin/keep.txt', 'geobin/keep.txt', 'server/bin/keep.txt',
                     'bin/classes.bin', 'server/bin/powers.bin'):      # the import brings old compiled files
            original = imported / name; original.parent.mkdir(parents=True, exist_ok=True)
            original.write_bytes(stale if name.endswith('.bin') else b'imported'); original.chmod(0o444)
            link = source / name; link.parent.mkdir(parents=True, exist_ok=True); link.symlink_to(original)
        owner = self.root / 'owner'; owner.mkdir()
        identity = {'format': 2, 'source_data': str(source.resolve(strict=True)),
                    'source_device': source.stat().st_dev, 'source_inode': source.stat().st_ino,
                    'source_roots': [{'path': str(root.resolve(strict=True)),
                                      'identity': cache.fingerprint(root.resolve(strict=True), directory=True)}
                                     for root in (source.parent, imported)],
                    'single_player_content': value.single_player_content.identity}
        for shared in ((), ('menu', 'texts')):
            if shared:
                identity = dict(identity, shared_server_data={'shared_top_level': list(shared)})
            first = cache.ServerDataCache(owner, identity, '1' * 32, value.ctx)
            target = self.root / ('first%d/data' % len(shared)); target.mkdir(parents=True)
            self.assertFalse(first.checkout(target))
            stats = value.stage_map_data(source, target, cache_recorder=first, skip_top_level=shared)
            self.assertIn('single_player_files', stats)
            first.seal(target, stats)
            # The zone server compiles its class list; the first pass removes one made from the old text.
            compiled = target / 'server/bin/classes.bin'
            compiled.write_bytes(parse6(['defs/classes.def']))
            # A staged file in the server's folder is removed too (the server writes it again);
            # the client's staged copy under data/bin stays, as the tree's receipt lists it.
            self.assertIn('bin/classes.bin', first.private_names)
            self.assertEqual(content.drop_stale_bins(value.single_player_content, target)['dropped'],
                             ['server/bin/classes.bin', 'server/bin/powers.bin'])
            self.assertTrue((target / 'bin/classes.bin').exists())
            compiled.write_bytes(parse6(['defs/classes.def']) + b'new')
            (target / 'server/bin/powers.bin').write_bytes(parse6(['defs/classes.def']) + b'new')
            self.assertTrue(first.release(target, {'wine_prefix_stopped': True, 'owned_processes_reaped': True}))
            second = cache.ServerDataCache(owner, identity, '2' * 32, value.ctx)
            again = self.root / ('second%d/data' % len(shared)); again.mkdir(parents=True)
            self.assertTrue(second.checkout(again), second.summary.get('reuse_refused'))
            self.assertNotIn('reuse_refused', second.summary)
            self.assertTrue((again / 'server/bin/classes.bin').read_bytes().endswith(b'new'))
            later = content.drop_stale_bins(value.single_player_content, again)
            self.assertEqual((later['pass'], later['dropped']), ('seeded_bins_only', []))
            self.assertEqual((again / 'defs/classes.def').read_bytes(),
                             value.single_player_content.files['defs/classes.def']['data'])

    def test_a_receipt_with_an_unknown_count_is_still_refused(self):
        import character_server_data_cache as cache
        self.assertEqual(cache.OPTIONAL_STATS, {'single_player_files'})
        self.assertFalse(cache.OPTIONAL_STATS & cache.STATS)

    def test_the_shared_tree_and_a_tree_without_its_folders_split_the_files(self):
        value, source, imported = self.mirror()
        shared = self.root / 'shared'
        stats = value.stage_map_data(source, shared, only_top_level=['menu', 'texts'])
        self.assertEqual(stats['copied_private_files'], 0)        # link_shared_server_data requires this
        self.assertEqual(stats['single_player_files'], 19)
        copy = shared / 'menu/powers/animfx/playerpowers/primalist_hunterform.pfx'
        self.assertEqual(copy.stat().st_mode & 0o777, 0o400)
        self.assertFalse((shared / 'defs').exists())
        private = self.root / 'private/data'
        stats = value.stage_map_data(source, private, skip_top_level=['menu', 'texts'])
        self.assertEqual(stats['single_player_files'], 20)
        self.assertFalse((private / 'menu').exists())

    def test_another_source_or_no_content_changes_nothing(self):
        value, source, imported = self.mirror()
        value.single_player_content = None
        result = value.stage_map_data(source, self.root / 'plain/data')
        self.assertNotIn('single_player_files', result)
        self.assertTrue((self.root / 'plain/data/defs/classes.def').is_symlink())

    def test_a_missing_folder_stops_the_mirror(self):
        value, source, imported = self.mirror()
        import shutil
        shutil.rmtree(source / 'menu')
        with self.assertRaisesRegex(ValueError, 'folder is missing'):
            value.stage_map_data(source, self.root / 'broken/data')


class StaleBins(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.data = Path(temporary.name) / 'data'
        (self.data / 'server/bin').mkdir(parents=True); (self.data / 'bin').mkdir()
        self.content = content.Content('a' * 64, {
            'defs/classes.def': {'data': b'x', 'new': False, 'sha256': ''},
            'defs/powers/feral_might_feral_might.powers': {'data': b'x', 'new': False, 'sha256': ''},
            'defs/classes/pc_primalist.def': {'data': b'x', 'new': True, 'sha256': ''}}, {})
        self.bins = {
            'server/bin/classes.bin': ['Defs/classes.def', 'defs\\classes\\PC_Scrapper.def'],
            'server/bin/powers.bin': ['defs/powers/Feral_Might_Feral_Might.powers', 'defs/powers/other.powers'],
            'server/bin/origins.bin': ['defs/origins.def'],
            'bin/powers.bin': ['defs/powers/feral_might_feral_might.powers']}
        for name, names in self.bins.items():
            (self.data / name).write_bytes(parse6(names))
        (self.data / 'server/bin/messages-en.bin').write_bytes(b'\x01\x02\x03\x04' * 8)     # not Parse6

    def test_the_header_reader_lists_source_files_in_any_spelling(self):
        self.assertEqual(content.parse6_dependencies(self.data / 'server/bin/classes.bin'),
                         ['defs/classes.def', 'defs/classes/pc_scrapper.def'])
        self.assertIsNone(content.parse6_dependencies(self.data / 'server/bin/messages-en.bin'))
        truncated = self.data / 'server/bin/short.bin'
        truncated.write_bytes(parse6(['defs/classes.def'])[:30])
        self.assertIsNone(content.parse6_dependencies(truncated))

    def test_the_first_pass_drops_every_bin_made_from_replaced_text(self):
        record = content.drop_stale_bins(self.content, self.data)
        self.assertEqual(record['pass'], 'every_bin')
        self.assertEqual(record['dropped'], ['server/bin/classes.bin', 'server/bin/powers.bin'])
        self.assertEqual(record['checked'], 4)        # the four files under server/bin
        # The client's copy under data/bin is a staged file of the kept tree: never removed.
        self.assertTrue((self.data / 'bin/powers.bin').exists())
        self.assertEqual(content.drop_stale_bins(self.content, self.data, ['data/bin/powers.bin']),
                         {'format': 1, 'pass': 'seeded_bins_only', 'checked': 0, 'dropped': []})
        self.assertTrue((self.data / 'bin/powers.bin').exists())
        self.assertTrue((self.data / 'server/bin/origins.bin').exists())
        self.assertTrue((self.data / 'server/bin/messages-en.bin').exists())
        marker = json.loads((self.data / content.MARKER).read_text())
        self.assertEqual(marker['identity'], 'a' * 64)

    def test_later_passes_keep_rebuilt_bins_and_drop_only_newly_seeded_ones(self):
        content.drop_stale_bins(self.content, self.data)
        # The server rebuilt both; a prepared-cache package then seeds classes.bin again (it was
        # missing at that moment in another start) and reports it.
        for name in ('server/bin/classes.bin', 'server/bin/powers.bin'):
            (self.data / name).write_bytes(parse6(self.bins[name]))
        record = content.drop_stale_bins(self.content, self.data, ['data/server/bin/classes.bin'])
        self.assertEqual((record['pass'], record['dropped']), ('seeded_bins_only', ['server/bin/classes.bin']))
        self.assertTrue((self.data / 'server/bin/powers.bin').exists())
        self.assertEqual(content.drop_stale_bins(self.content, self.data)['dropped'], [])
        # Another content identity starts over.
        other = content.Content('b' * 64, self.content.files, {})
        self.assertEqual(content.drop_stale_bins(other, self.data)['dropped'], ['server/bin/powers.bin'])


class DatabaseName(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.runtime = Path(temporary.name)
        self.path = self.runtime / content.ATTRIBUTE_FILE
        self.path.parent.mkdir(parents=True)
        self.path.write_bytes(b'1 "race"\r\n2 "Class_Scrapper"\r\n3 "Bright Energy Manipulation"\r\n')
        self.schema = {'expected_attributes': {'attributes': [
            {'id': 1, 'name': 'race'}, {'id': 2, 'name': 'class_scrapper'},
            {'id': 3, 'name': 'bright energy manipulation'}]}}

    def test_the_name_goes_after_the_last_one_once(self):
        self.assertEqual(content.append_class_attribute(self.runtime, self.schema), 4)
        self.assertTrue(self.path.read_bytes().endswith(b'3 "Bright Energy Manipulation"\r\n4 "Class_Primalist"\r\n'))
        self.assertEqual(self.schema['expected_attributes']['attributes'][-1], {'id': 4, 'name': 'class_primalist'})
        before = self.path.read_bytes()
        self.assertEqual(content.append_class_attribute(self.runtime, self.schema), 4)     # same session, again
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(len(self.schema['expected_attributes']['attributes']), 4)
        # A fresh copy of the accepted file with rows that already know the name (the next call
        # of a session whose runtime was copied again).
        self.path.write_bytes(before[:-len(content.attribute_line(4))])
        self.assertEqual(content.append_class_attribute(self.runtime, self.schema), 4)
        self.assertEqual(self.path.read_bytes(), before)

    def test_a_list_that_ends_elsewhere_is_refused(self):
        self.path.write_bytes(b'1 "race"\r\n2 "Class_Scrapper"\r\n')
        with self.assertRaisesRegex(ValueError, 'does not end where the accepted schema ends'):
            content.append_class_attribute(self.runtime, self.schema)
        self.schema['expected_attributes']['attributes'].insert(1, {'id': 2, 'name': 'class_primalist'})
        with self.assertRaisesRegex(ValueError, 'not the last database name'):
            content.append_class_attribute(self.runtime, self.schema)

    def test_a_saved_game_that_knows_the_class_is_accepted_before_the_server_tree_exists(self):
        # Thor 0.13.87: the saved heroes are checked before prepare_runtime adds the name.
        before = self.path.read_bytes()
        self.assertEqual(content.accept_stored_class_attribute(self.schema, 4), 4)
        self.assertEqual(self.schema['expected_attributes']['attributes'][-1], {'id': 4, 'name': 'class_primalist'})
        self.assertEqual(self.path.read_bytes(), before)                                     # nothing written
        self.assertEqual(content.append_class_attribute(self.runtime, self.schema), 4)        # prepare_runtime, later
        self.assertTrue(self.path.read_bytes().endswith(b'4 "Class_Primalist"\r\n'))
        self.assertEqual(len(self.schema['expected_attributes']['attributes']), 4)
        self.assertEqual(content.accept_stored_class_attribute(self.schema, 4), 4)            # idempotent
        for stored in (3, 5, 0, -1, True, '4', None):
            with self.assertRaisesRegex(ValueError, 'another number|Invalid stored'):
                content.accept_stored_class_attribute(self.schema, stored)
        fresh = {'expected_attributes': {'attributes': [{'id': 1, 'name': 'race'}]}}
        with self.assertRaisesRegex(ValueError, 'another number'):
            content.accept_stored_class_attribute(fresh, 4)
        self.assertEqual(len(fresh['expected_attributes']['attributes']), 1)                 # refused: unchanged

    def test_the_database_rows_say_whether_the_class_is_known(self):
        self.assertFalse(content.attribute_present([{'id': 1, 'name': 'class_scrapper'}]))
        self.assertTrue(content.attribute_present([{'id': 9, 'name': 'Class_Primalist'}]))


class Wiring(unittest.TestCase):
    """The hooks are where the design needs them (text checks; the flows run in CI)."""

    def staged(self, limit=None):
        """Stage a one-file donor the way the APK build does (no server archive)."""
        import json, tempfile
        from unittest import mock
        import stage_app_assets as stage
        work = Path(tempfile.mkdtemp(prefix='stage-content-'))
        self.addCleanup(__import__('shutil').rmtree, work, True)
        source = work / 'donor'; source.mkdir()
        (source / 'game-package.tar.gz').write_bytes(b'donor archive')
        client = {'format': 1, 'scope': 'actual_client_startup_guest',
                  'files': {'game-package.tar.gz': stage.pin(source / 'game-package.tar.gz')}}
        (source / 'client-manifest.json').write_text(json.dumps(client))
        (source / 'runtime-manifest.json').write_text(json.dumps({'format': 1, 'repository_commit': '1' * 40, 'files': {
            **client['files'], 'client-manifest.json': stage.pin(source / 'client-manifest.json')}}))
        armport = work / 'client.zip'; armport.write_bytes(b'client overlay')
        document = {'files': {'CityOfHeroes.exe': {'sha256': 'c' * 64}}, 'client_run_id': 1, 'data_run_id': 1}
        with mock.patch.object(stage.package, 'unpack', return_value=document), \
                mock.patch.object(stage, 'CLIENT_INVENTORY_LIMIT', limit or stage.CLIENT_INVENTORY_LIMIT):
            stage.stage(source, armport, work / 'staged', '2' * 40)
        return (json.loads((work / 'staged/runtime-manifest.json').read_text()),
                json.loads((work / 'staged/client-manifest.json').read_text()), work / 'staged')

    def test_the_archive_is_staged_outside_the_bounded_client_inventory(self):
        """Run 45700074655: the first 0.13.85 APK build had 97 client inventory entries for a bound of 96."""
        import stage_app_assets as stage
        runtime, client, folder = self.staged()
        archive = stage.SINGLE_PLAYER_ARCHIVE
        self.assertEqual(runtime['files'][archive], stage.pin(folder / archive))
        self.assertNotIn(archive, client['files'])
        self.assertIn('single_player_content.py', client['files'])      # the module is a guest dependency
        self.assertEqual((folder / archive).read_bytes(), stage.single_player_content()[archive])
        with self.assertRaisesRegex(ValueError, 'Client inventory bound exceeded: %d' % len(client['files'])):
            self.staged(limit=len(client['files']) - 1)

    def test_the_packer_and_the_device_use_one_client_inventory_bound(self):
        import re
        import stage_app_assets as stage, build_thor_apk as apk
        device = (ROOT / 'android/guest/client_startup_diagnostic.py').read_text()
        self.assertEqual([int(v) for v in re.findall(r'len\(files\) <= (\d+)', device)], [stage.CLIENT_INVENTORY_LIMIT])
        # 95 entries in 0.13.84, one more module in 0.13.85, room for later ones.
        self.assertGreaterEqual(stage.CLIENT_INVENTORY_LIMIT, 96 + 16)
        self.assertIn('client_startup_diagnostic.py', apk.CHANGED_RUNTIME)
        self.assertLessEqual({'single_player_content.py', stage.SINGLE_PLAYER_ARCHIVE}, apk.ADDED_RUNTIME)

    def test_login_server_appends_before_the_dbserver_and_stays_on_once_stored(self):
        text = (ROOT / 'android/guest/local_login_server.py').read_text()
        prepare = text[text.index('    def prepare_runtime(self):'):text.index('    def start(self):')]
        self.assertLess(prepare.index('shutil.copyfile(self.schema_dir / name, target)'),
                        prepare.index('self.apply_single_player_schema()'))
        self.assertIn('self.primalist = content.requested() or stored', prepare)
        self.assertIn("lower(name)='class_primalist'", prepare)
        start = text[text.index('    def start(self):'):]
        self.assertLess(start.index('self.prepare_runtime()'), start.index("self.ctx.start('local-dbserver'"))

    def test_trees_are_keyed_by_the_content_and_stale_bins_go_after_each_cache_install(self):
        text = (ROOT / 'android/guest/local_character_server.py').read_text()
        self.assertIn("identity['single_player_content'] = self.single_player_content.identity", text)
        self.assertEqual(text.count('server_cache_package.install('), 3)
        self.assertEqual(text.count('self.drop_single_player_stale_bins('), 3)
        for chunk in text.split('server_cache_package.install(')[1:]:
            self.assertLess(chunk.index('drop_single_player_stale_bins'), 900)
        self.assertIn("environment['ARMPORT_PRIMALIST'] = '1'", text)
        self.assertIn("environment['ARMPORT_UNLOCK_ALL'] = '1'", text)

    def test_changes_the_unlock_causes_are_recorded_and_not_judged(self):
        import local_character_server as server
        from unittest.mock import patch
        value = server.LocalCharacterReopenServer.__new__(server.LocalCharacterReopenServer)
        value.creation_report = {}
        with patch.object(server.LocalCharacterReopenServer, 'enhancement_change_in_ordinary_play',
                          return_value=True):
            with patch.dict(os.environ, {'COH_UNLOCK_ALL': '0'}):
                self.assertFalse(value.unlock_all_change_recorded('powers'))
            self.assertEqual(value.creation_report, {})
            with patch.dict(os.environ, {'COH_UNLOCK_ALL': '1'}):
                self.assertTrue(value.unlock_all_change_recorded('powers'))
                self.assertTrue(value.unlock_all_change_recorded('ents2'))
                self.assertTrue(value.unlock_all_change_recorded('powers'))
        self.assertEqual(value.creation_report['unlock_all_changes']['tables'], ['powers', 'ents2'])
        with patch.object(server.LocalCharacterReopenServer, 'enhancement_change_in_ordinary_play',
                          return_value=False), patch.dict(os.environ, {'COH_UNLOCK_ALL': '1'}):
            self.assertFalse(value.unlock_all_change_recorded('costumeparts'))    # a forced stop, a task profile
        text = (ROOT / 'android/guest/local_character_server.py').read_text()
        self.assertLess(text.index('and self.unlock_all_change_recorded(table)):'),
                        text.index("require(False, 'Committed existing character rows changed after reopen: ' + table)"))

    def test_unlock_all_grants_only_names_the_dbserver_accepts(self):
        import game_diagnostic as game
        self.assertEqual(len(set(game.UNLOCK_AUTH_BITS)), len(game.UNLOCK_AUTH_BITS))
        for refused in ('TrialAccount', 'Beta', 'CovBeta', 'TransferToEU', 'KoreanLevelMinimum',
                        'LimitedRogueAccess', 'PreorderCode', 'LoyaltyReward', 'CreatePrimals'):
            self.assertNotIn(refused, game.UNLOCK_AUTH_BITS)
        source = ROOT / 'upstream/ouroboros/Common/auth/authUserData.c'
        text = source.read_text(encoding='latin1')
        setter = text[text.index('authUserSetFieldByName'):]
        setter = setter[:setter.index('\n}\n')]
        import re
        accepted = set(re.findall(r'ELSE_SETBIT\((\w+)\)', setter))
        self.assertEqual(sorted(set(game.UNLOCK_AUTH_BITS) - accepted), [])
        original = ('UseFakeAuth 1\nUseQueueServer 0\nUseLogServer 0\nSqlAllowDDL 1\n'
                    'OverrideAuthBit TrialAccount\n')
        connection = 'Driver={x};Servername=127.0.0.1;Port=1;Database=db;Username=u;Password=p;'
        plain = game.game_config(original, 'db', connection)
        self.assertNotIn('OverrideAuthBit', plain)
        unlocked = game.game_config(original, 'db', connection, unlock=True)
        self.assertEqual(unlocked.count('OverrideAuthBit '), len(game.UNLOCK_AUTH_BITS))
        self.assertNotIn('TrialAccount', unlocked)
        self.assertIn('OverrideAuthBit Kheldian\n', unlocked)


if __name__ == '__main__':
    unittest.main()
