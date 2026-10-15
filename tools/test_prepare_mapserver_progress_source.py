"""Bind the MapServer-only diagnostic overlay to the unchanged loopback base."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import prepare_mapserver_progress_source as progress


class MapServerProgressSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.expected = progress.expected_progress_receipt()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='coh-map-progress-source-')
        self.addCleanup(temporary.cleanup)
        self.source = Path(temporary.name) / 'source'
        self.source.mkdir()
        self.base = copy.deepcopy(self.expected['game_build_input'])
        self.pg = self.base['postgresql_build_input']
        for name in set(progress.PROGRESS_FILES).union(progress.game.GAME_FILES, self.pg['patched_sha256']):
            target = self.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(progress.ROOT / 'upstream/ouroboros' / name, target)
        progress.apply_patch(self.source, (progress.ROOT / 'patches/postgresql/0001-dbserver-postgresql.patch')
                             .read_bytes().replace(b'\r\n', b'\n'))
        for name in self.pg['overlay_sha256']:
            target = self.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(progress.ROOT / 'database/postgresql/overlay' / name, target)
        (self.source / 'postgresql-build-input.json').write_text(json.dumps(self.pg))
        progress.game.apply_game_overlay(self.source)

    def test_composes_only_mapserver_after_creation_and_preserves_base_receipts(self):
        originals = {name: progress.sha256(progress.ROOT / 'upstream/ouroboros' / name)
                     for name in progress.PROGRESS_FILES}
        base_bytes = (self.source / progress.game.RECEIPT).read_bytes()
        actual = progress.apply_progress_overlay(self.source)
        self.assertEqual(actual, self.expected)
        self.assertEqual(actual['game_build_input'], self.base)
        self.assertEqual((self.source / progress.game.RECEIPT).read_bytes(), base_bytes)
        self.assertEqual(json.loads((self.source / progress.RECEIPT).read_text()), actual)
        self.assertEqual({name: progress.sha256(self.source / name) for name in progress.PROGRESS_FILES},
                         actual['patched_sha256'])
        self.assertEqual({name: progress.sha256(self.source / name) for name in progress.OVERLAY_FILES},
                         actual['progress_overlay_sha256'])
        for name, digest in self.base['patched_sha256'].items():
            if name not in progress.PROGRESS_FILES:
                self.assertEqual(progress.sha256(self.source / name), digest)
        self.assertEqual({name: progress.sha256(progress.ROOT / 'upstream/ouroboros' / name)
                          for name in progress.PROGRESS_FILES}, originals)
        self.assertEqual(actual['build_targets'], ['MapServer'])
        self.assertEqual(actual['runtime_validation'], 'unverified')

    def test_dirty_mapserver_loopback_or_pg_source_rejected_before_mutation(self):
        for name in (progress.PROGRESS_FILES[-1], progress.game.GAME_FILES[0],
                     progress.game.GAME_FILES[-1], next(iter(self.pg['overlay_sha256']))):
            with self.subTest(name=name):
                path = self.source / name
                original = path.read_bytes()
                path.write_bytes(original + b'\n// dirty\n')
                before = {name: progress.sha256(self.source / name) for name in progress.PROGRESS_FILES}
                with self.assertRaisesRegex(ValueError, 'Staged source SHA-256 mismatch'):
                    progress.apply_progress_overlay(self.source)
                self.assertEqual(before, {name: progress.sha256(self.source / name) for name in progress.PROGRESS_FILES})
                self.assertFalse((self.source / progress.RECEIPT).exists())
                path.write_bytes(original)

    def test_stale_or_resume_base_receipt_rejected(self):
        for receipt in (dict(self.base, variant='resume'), dict(self.base, source_commit='f' * 40)):
            (self.source / progress.game.RECEIPT).write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, 'Creation loopback source receipt mismatch'):
                progress.apply_progress_overlay(self.source)
        (self.source / progress.game.RECEIPT).write_text(json.dumps(self.base))
        (self.source / progress.game.resume.RECEIPT).write_text('{}')
        with self.assertRaisesRegex(ValueError, 'without a resume overlay'):
            progress.apply_progress_overlay(self.source)

    def test_overwrite_symlink_repeat_and_upstream_rejected(self):
        overlay = self.source / progress.OVERLAY_FILES[0]
        overlay.write_text('foreign overlay')
        with self.assertRaisesRegex(ValueError, 'would overwrite source'):
            progress.apply_progress_overlay(self.source)
        overlay.unlink()
        overlay.symlink_to(self.source / progress.PROGRESS_FILES[-1])
        with self.assertRaisesRegex(ValueError, 'would overwrite source'):
            progress.apply_progress_overlay(self.source)
        overlay.unlink()
        progress.apply_progress_overlay(self.source)
        with self.assertRaisesRegex(ValueError, 'already exists'):
            progress.apply_progress_overlay(self.source)
        with self.assertRaisesRegex(ValueError, 'immutable snapshots'):
            progress.apply_progress_overlay(progress.ROOT / 'upstream/ouroboros')
        with self.assertRaisesRegex(ValueError, 'new directory'):
            progress.prepare(self.source)

    def test_contract_parses_hash_bound_stages_and_rejects_ambiguous_schema(self):
        contents = progress.overlay_bytes()
        contract = progress.progress_metadata(contents)
        self.assertEqual(contract['stages']['24'], 'TICK_BEGIN')
        self.assertEqual(contract['stages']['34'], 'TICK_DONE')
        self.assertEqual(contract['stages']['37'], 'SLEEP_DONE')
        self.assertEqual(contract['offsets']['reserved'] + contract['reserved_bytes'], 128)
        self.assertFalse(contract['proves_readiness_or_game_success'])
        for before, after in ((b'FORMAT 1', b'FORMAT 2'), (b'TICK_BEGIN = 24', b'TICK_BEGIN = 25')):
            bad = dict(contents)
            bad[progress.OVERLAY_FILES[1]] = bad[progress.OVERLAY_FILES[1]].replace(before, after)
            with self.assertRaises(ValueError):
                progress.progress_metadata(bad)

    def test_windows_pg_profile_keeps_actual_base_receipt(self):
        for name in self.pg['overlay_sha256']:
            path = self.source / name
            path.write_bytes(path.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
            self.pg['overlay_sha256'][name] = progress.sha256(path)
        self.base = progress.game.expected_game_receipt(postgresql_build_input=self.pg)
        (self.source / 'postgresql-build-input.json').write_text(json.dumps(self.pg))
        (self.source / progress.game.RECEIPT).write_text(json.dumps(self.base))
        self.assertEqual(progress.apply_progress_overlay(self.source),
                         progress.expected_progress_receipt(game_build_input=self.base))


if __name__ == '__main__':
    unittest.main(verbosity=2)
