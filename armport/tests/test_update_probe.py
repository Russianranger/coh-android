"""CI's update probe (0.13.89): the first session runs with the previous version's content."""
import contextlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'armport/app'), str(ROOT / 'android/guest')]
import interactive_host as host
import single_player_content as content
import stage_app_assets


@contextlib.contextmanager
def environment(**values):
    names = ('COH_SINGLE_PLAYER_PROBE', 'COH_SINGLE_PLAYER_PROBE_PART', host.HEROES_PROBE_ENV, host.UPDATE_PROBE_ENV)
    saved = {name: os.environ.pop(name, None) for name in names}
    os.environ.update(values)
    try:
        yield
    finally:
        for name in names:
            os.environ.pop(name, None)
            if saved[name] is not None:
                os.environ[name] = saved[name]


def record(trees, removed=0, sealed=None):
    value = {'shared_trees': [{'kind': kind, 'reused': reused, 'files': files, 'tree': 'shared-server-data-x'}
                              for kind, reused, files in trees],
             'removed': {'unsealed_trees': 0, 'other_identity_trees': removed}, 'link_seconds': 1.5}
    return value


def report(identity, *records):
    return {'single_player_content': {'identity': identity},
            'character_reopen': {'zone_tree_preparation': {'shared_server_data': records[0]},
                                 'others': [{'shared_server_data': item} for item in records[1:]]}}


class UpdateProbe(unittest.TestCase):
    def test_the_probe_is_asked_for_by_its_own_switch(self):
        with environment():
            self.assertFalse(host.update_probe_requested())
        with environment(COH_UPDATE_PROBE='1', COH_SINGLE_PLAYER_PROBE='1'):
            self.assertTrue(host.update_probe_requested() and host.primalist_creation_requested())
        with environment(COH_UPDATE_PROBE='yes'), self.assertRaises(ValueError):
            host.update_probe_requested()
        workflow = (ROOT / '.github/workflows/armport-app-runtime.yml').read_text()
        self.assertIn("options: ['false', 'true', unlock, primalist, heroes, update]", workflow)
        self.assertIn("COH_UPDATE_PROBE: ${{ inputs.single_player_probe == 'update' && '1' || '' }}", workflow)
        line = next(line for line in workflow.splitlines() if line.startswith('  COH_SINGLE_PLAYER_PROBE:'))
        self.assertIn("inputs.single_player_probe == 'update'", line)       # a Primalist is made, with both options

    def test_only_the_differing_files_change_places_and_come_back(self):
        with tempfile.TemporaryDirectory() as folder:
            first, second = Path(folder) / 'assets', Path(folder) / 'earlier'
            for root, content_bytes in ((first, b'new'), (second, b'old')):
                (root / 'sub').mkdir(parents=True)
                (root / 'world.zip').write_bytes(b'w' * 4096)
                (root / 'sub/helper.py').write_bytes(b'same')
                (root / stage_app_assets.SINGLE_PLAYER_ARCHIVE).write_bytes(content_bytes)
                (root / 'runtime-manifest.json').write_bytes(b'{"pin":"' + content_bytes + b'"}')
            (first / 'added-later.json').write_bytes(b'{}')
            kept = {name: (first / name).stat().st_ino for name in ('world.zip', 'sub/helper.py', 'added-later.json')}
            moved = host.exchange_staged_files(first, second)
            self.assertEqual(moved, ['runtime-manifest.json', stage_app_assets.SINGLE_PLAYER_ARCHIVE])
            self.assertEqual((first / stage_app_assets.SINGLE_PLAYER_ARCHIVE).read_bytes(), b'old')
            self.assertEqual((first / 'runtime-manifest.json').read_bytes(), b'{"pin":"old"}')
            self.assertEqual((second / stage_app_assets.SINGLE_PLAYER_ARCHIVE).read_bytes(), b'new')
            # every other file is the very file the next session sees
            self.assertEqual({name: (first / name).stat().st_ino for name in kept}, kept)
            self.assertEqual(host.exchange_staged_files(first, second), moved)
            self.assertEqual((first / stage_app_assets.SINGLE_PLAYER_ARCHIVE).read_bytes(), b'new')
            self.assertEqual((first / 'runtime-manifest.json').read_bytes(), b'{"pin":"new"}')
            self.assertEqual(sorted(path.name for path in second.rglob('*.exchange')), [])
        source = (ROOT / 'armport/app/interactive_host.py').read_text()
        self.assertNotIn("earlier_assets.resolve()) + ':/opt/coh'", source)      # one folder is bound, always

    def test_the_earlier_folder_is_exactly_what_the_previous_version_shipped(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'earlier'
            identities = host.earlier_content_folder(target)
            self.assertEqual(identities, {'earlier': content.IDENTITY_HISTORY[-2], 'current': content.IDENTITY_HISTORY[-1]})
            self.assertEqual(identities['earlier'], '3fa56ed5affbf14728d2ccb53c21a3ca17bc030352084ddf62338ee1deba1485')
            # The packer accepts it (every file against its manifest) and the guest loads it under that identity.
            assets = Path(folder) / 'assets'; assets.mkdir()
            (payload,) = stage_app_assets.single_player_content(target).values()
            (assets / content.ARCHIVE).write_bytes(payload)
            loaded = content.load(assets)
            self.assertEqual(loaded.identity, identities['earlier'])
            text = loaded.files['defs/classes/pc_primalist.def']['data']
            self.assertIn(b'"archetypeicon_primalist.texture"', text); self.assertNotIn(b'primalist.tga', text)
            self.assertEqual(len(loaded.files), 39)
            # This version's folder was not changed, and a second folder is not written over the first.
            self.assertEqual(stage_app_assets.single_player_content()[content.ARCHIVE] == payload, False)
            current = json.loads((stage_app_assets.SINGLE_PLAYER_CONTENT / 'manifest.json').read_text())
            self.assertEqual(current['files_sha256'], identities['current'])
            with self.assertRaisesRegex(ValueError, 'already exists'):
                host.earlier_content_folder(target)

    def test_the_reopen_must_have_replaced_the_old_content_tree_and_kept_the_rest(self):
        ids = {'earlier': 'a' * 64, 'current': 'b' * 64}
        made = report(ids['earlier'], record([('content_folders', False, 10715), ('untouched_folders', False, 118050)]))
        good = report(ids['current'],
                      record([('content_folders', False, 10715), ('untouched_folders', True, 118050)], removed=1),
                      record([('content_folders', True, 10715), ('untouched_folders', True, 118050)]))
        summary = host.update_probe_validate(made, good, ids)
        self.assertEqual(summary['content'], ids)
        self.assertEqual(len(summary['reopen']), 2)
        for bad, message in (
                (report(ids['earlier'], *[item['shared_server_data'] for item in []] or
                        [record([('content_folders', True, 1), ('untouched_folders', True, 2)])]), 'this version'),
                (report(ids['current'], record([('content_folders', True, 1), ('untouched_folders', True, 2)])),
                 'did not replace'),
                (report(ids['current'], record([('content_folders', False, 1), ('untouched_folders', True, 2)])),
                 'did not replace'),
                (report(ids['current'], record([('content_folders', False, 1), ('untouched_folders', False, 2)], removed=2)),
                 'linked again')):
            with self.assertRaisesRegex(ValueError, message):
                host.update_probe_validate(made, bad, ids)
        with self.assertRaisesRegex(ValueError, 'earlier content'):
            host.update_probe_validate(good, good, ids)
        with self.assertRaisesRegex(ValueError, 'no content tree'):
            host.update_probe_validate(report(ids['earlier'], record([('all_folders', False, 5)])), good, ids)

    def test_stage_takes_the_content_folder_it_is_given(self):
        import inspect
        self.assertIn('content_root', inspect.signature(stage_app_assets.stage).parameters)
        text = (ROOT / 'armport/app/interactive_host.py').read_text()
        self.assertIn("content_root=args.work / 'earlier-content'", text)
        self.assertIn("first, first_manifests[0], first_manifests[1], deadline)", text)


if __name__ == '__main__':
    unittest.main()
