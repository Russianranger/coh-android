"""Launch receipts: an unchanged step is skipped; any changed directory runs it in full again."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import unittest.mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import launch_receipts as receipts  # noqa: E402

IDENTITY = {'format': 1, 'step': 'zone_resources', 'inputs': {'zones.zip': 'a' * 64}}
RESULT = {'format': 1, 'file_count': 4, 'installed_files': 4, 'decoded_payload_bytes': 40,
          'fingerprint_reused': False, 'source_generation_rebound': False, 'elapsed_seconds': 43.0}


@unittest.skipIf(os.name == 'nt', 'The guest runs on Android (POSIX)')
class LaunchReceiptTests(unittest.TestCase):
    class Context:
        checks = 0

        def check(self):
            self.checks += 1

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        self.work, self.store = base / 'client-work', base / 'launch-receipts'
        self.leaves = [self.write(name) for name in ('data/texture_library/zone/a.texture',
            'data/texture_library/zone/b.texture', 'data/object_library/zone/part.geo', 'data/sound/ogg/z.ogg')]
        (self.work / 'data/bin').mkdir()                      # a folder no leaf of this step lives in

    def write(self, name, raw=b'leaf'):
        path = self.work / name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw); path.chmod(0o444)
        return path

    def record(self, **kwargs):
        return receipts.record(self.store, 'zone_resources', IDENTITY, self.work, self.leaves, RESULT, self.Context(), **kwargs)

    def reusable(self, identity=IDENTITY, **kwargs):
        return receipts.reusable(self.store, 'zone_resources', identity, self.work, self.Context(), **kwargs)

    def test_an_unchanged_tree_reuses_the_last_full_result(self):
        self.assertEqual(self.reusable(), (None, 'no_receipt'))
        # data, texture_library, object_library and sound hold no leaf: identity only.
        self.assertEqual(self.record(), 8)
        rows = json.loads((self.store / 'zone_resources.json').read_bytes())['directories']
        self.assertEqual({name: len(row) for name, row in rows.items()},
                         {'': 4, 'data': 4, 'data/texture_library': 4, 'data/texture_library/zone': 8,
                          'data/object_library': 4, 'data/object_library/zone': 8, 'data/sound': 4, 'data/sound/ogg': 8})
        self.assertEqual(self.reusable(), (RESULT, None))
        self.assertEqual(os.stat(self.store / 'zone_resources.json').st_mode & 0o777, 0o600)

    def test_a_change_above_the_leaves_does_not_matter(self):
        self.record()
        (self.work / 'client-work.json').write_bytes(b'{}')   # the worktree root
        (self.work / 'data/bin/powers.bin').write_bytes(b'x')  # a folder of another step
        (self.work / 'data/texture_library/other').mkdir()     # a sibling folder
        self.assertEqual(self.reusable(), (RESULT, None))

    def test_any_change_of_a_leaf_folder_runs_the_step_in_full(self):
        folder = 'data/texture_library/zone'
        def added(): self.write(folder + '/new.texture')
        def removed(): (self.work / folder / 'a.texture').unlink()
        def renamed(): (self.work / folder / 'a.texture').rename(self.work / folder / 'c.texture')
        def replaced():
            fresh = self.write(folder + '/.pending', b'leaf'); os.replace(fresh, self.work / folder / 'a.texture')
        def linked():
            (self.work / folder / 'a.texture').unlink(); (self.work / folder / 'a.texture').symlink_to('b.texture')
        for change in (added, removed, renamed, replaced, linked):
            with self.subTest(change=change.__name__):
                self.setUp(); self.record(); change()
                self.assertEqual(self.reusable(), (None, 'directory_changed: ' + folder))

    def test_a_replaced_or_missing_folder_runs_the_step_in_full(self):
        self.record()
        folder = self.work / 'data/sound/ogg'
        folder.rename(self.work / 'data/sound/old'); folder.mkdir(); self.write('data/sound/ogg/z.ogg')
        self.assertEqual(self.reusable(), (None, 'directory_changed: data/sound/ogg'))
        self.setUp(); self.record()
        middle = self.work / 'data/sound'
        middle.rename(self.work / 'data/sound-old'); middle.symlink_to('sound-old')
        self.assertEqual(self.reusable(), (None, 'directory_missing: data/sound'))

    def test_other_inputs_an_old_receipt_or_a_damaged_one_run_the_step_in_full(self):
        self.record(now=1000.0)
        self.assertEqual(self.reusable(now=1000.0 + receipts.MAX_AGE_SECONDS), (RESULT, None))
        self.assertEqual(self.reusable(now=1001.0 + receipts.MAX_AGE_SECONDS), (None, 'receipt_expired'))
        self.assertEqual(self.reusable(now=999.0), (None, 'receipt_expired'))    # the clock went back
        changed = dict(IDENTITY, inputs={'zones.zip': 'b' * 64})
        self.assertEqual(self.reusable(changed, now=1000.0), (None, 'inputs_changed'))
        path = self.store / 'zone_resources.json'
        value = json.loads(path.read_bytes())
        for damage in (b'not json', b'[]', json.dumps(dict(value, policy='other')).encode(),
                       json.dumps(dict(value, directories={'../outside': [1, 2, 3, 4]})).encode()):
            path.write_bytes(damage)
            self.assertTrue(self.reusable(now=1000.0)[1].startswith('receipt_refused'), damage[:20])
        path.unlink(); path.symlink_to(self.work / 'client-work.json')
        self.assertTrue(self.reusable(now=1000.0)[1].startswith('receipt_unreadable'))

    def test_a_leaf_outside_the_worktree_is_not_recorded(self):
        with self.assertRaises(ValueError):
            receipts.record(self.store, 'zone_resources', IDENTITY, self.work, [Path(self.temporary.name) / 'x'], RESULT)
        with self.assertRaises(receipts.ReceiptError):
            receipts.record(self.store, 'Zone Resources', IDENTITY, self.work, self.leaves, RESULT)

    def test_a_rewrite_in_place_is_the_stated_limit(self):
        # Documented in launch_receipts.py: same inode, so no directory row changes.
        self.record()
        leaf = self.leaves[0]; leaf.chmod(0o644); leaf.write_bytes(b'LEAF'); leaf.chmod(0o444)
        self.assertEqual(self.reusable(), (RESULT, None))

    def test_a_reused_result_reports_no_work_and_this_launch_s_time(self):
        self.assertEqual(receipts.as_reused(RESULT, 1.25), {'format': 1, 'file_count': 4, 'installed_files': 0,
            'decoded_payload_bytes': 0, 'fingerprint_reused': True, 'source_generation_rebound': False,
            'elapsed_seconds': 1.25})
        world = {'reuse_validation': 'pinned_content_verification', 'archive_read_bytes': 9, 'decoded_files': 4,
                 'decoded_payload_bytes': 40, 'installed_files': 4, 'reused_files': 0, 'file_count': 4,
                 'preparation_elapsed_seconds': 21.7}
        # The keys and values CI's host validator accepts for a reused Atlas world (interactive_host.py).
        self.assertEqual(receipts.as_reused(world, 0.5), {'reuse_validation': 'unchanged_filesystem_receipt',
            'archive_read_bytes': 0, 'decoded_files': 0, 'decoded_payload_bytes': 0, 'installed_files': 0,
            'reused_files': 4, 'file_count': 4, 'preparation_elapsed_seconds': 0.5})


@unittest.skipIf(os.name == 'nt', 'The guest runs on Android (POSIX)')
class ReceiptedStepTests(unittest.TestCase):
    """character_creation_diagnostic: a step runs in full once, is recorded after every step, then reused."""

    def setUp(self):
        import character_creation_diagnostic as creation
        self.creation = creation
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        self.owner = unittest.mock.Mock()
        self.owner.work, self.owner.root = base / 'client-work', base
        (self.owner.work / 'data/texture_library').mkdir(parents=True)
        self.owner.ctx.report = {'asset_sha256': {'zone_asset_package.py': 'c' * 64, 'zones.zip': 'a' * 64}}
        self.owner.pending_launch_receipts = []
        self.runs = 0

    def run_step(self, pins=('zone_asset_package.py', 'zones.zip')):
        def run():
            self.runs += 1
            leaf = self.owner.work / 'data/texture_library/a.texture'
            if not leaf.exists():
                leaf.write_bytes(b'leaf')
            return dict(RESULT)
        return self.creation.CharacterCreationDiagnostic.receipted_step(
            self.owner, 'zone_resources', lambda: pins, lambda: {'data/texture_library/a.texture': {}}, run)

    def record(self):
        targets = {'data/texture_library/a.texture': self.owner.work / 'data/texture_library/a.texture'}
        with unittest.mock.patch('atlas_world_assets.resolve_targets', return_value=targets):
            self.creation.CharacterCreationDiagnostic.record_launch_receipts(self.owner)

    def test_full_then_recorded_then_reused(self):
        self.assertEqual(self.run_step(), RESULT)
        status = self.owner.ctx.report['launch_receipts']['zone_resources']
        self.assertEqual((status['status'], status['reason'], self.runs), ('ran_in_full', 'no_receipt', 1))
        self.record()
        self.assertEqual((status['recorded'], status['directories'], self.owner.pending_launch_receipts), (True, 3, []))
        reused = self.run_step()
        status = self.owner.ctx.report['launch_receipts']['zone_resources']
        self.assertEqual((status['status'], self.runs, reused['installed_files'], reused['fingerprint_reused']),
                         ('reused', 1, 0, True))
        self.assertEqual(self.owner.pending_launch_receipts, [])
        # Another pinned input (an APK with other assets or step code) runs the step in full again.
        self.owner.ctx.report['asset_sha256']['zones.zip'] = 'b' * 64
        self.run_step()
        self.assertEqual((self.owner.ctx.report['launch_receipts']['zone_resources']['reason'], self.runs),
                         ('inputs_changed', 2))

    def test_an_input_without_a_pin_always_runs_in_full(self):
        for _ in range(2):
            self.run_step(pins=('zone_asset_package.py', 'unknown.zip'))
            self.record()
        status = self.owner.ctx.report['launch_receipts']['zone_resources']
        self.assertEqual((status['status'], status['reason'], self.runs), ('ran_in_full', 'inputs_not_pinned', 2))
        self.assertFalse((self.owner.root / 'launch-receipts').exists())

    def test_a_step_module_without_pin_names_runs_in_full(self):
        # Older step modules (and the schedule tests' stand-ins) name no manifest or archive.
        import types
        module = types.SimpleNamespace()
        result = self.creation.CharacterCreationDiagnostic.receipted_step(
            self.owner, 'zone_resources', lambda: ('zone_asset_package.py', module.MANIFEST), dict, lambda: dict(RESULT))
        status = self.owner.ctx.report['launch_receipts']['zone_resources']
        self.assertEqual((result, status['status'], status['reason']), (RESULT, 'ran_in_full', 'inputs_not_pinned'))
        self.assertEqual(self.owner.pending_launch_receipts, [])


if __name__ == '__main__':
    unittest.main()
