"""Check input identity, immutable data precedence and fail-closed publication."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

import prepare_game_data as game


def digest(data):
    return hashlib.sha256(data).hexdigest()


class ReviewedGameDataTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='coh-game-data-tests-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root, self.assets, self.output = (self.base / name for name in ('repo', 'assets', 'output'))
        self.root.mkdir()
        (self.root / 'tools').mkdir()
        shutil.copyfile(game.ROOT / 'tools/verify_source.py', self.root / 'tools/verify_source.py')
        self.source_config = b'UseFakeAuth 1\nUseQueueServer 0\n'
        self.map_text = b'pinned map\r\n'
        self.asset_bytes = b'animation payload'
        source = {'data/server/db/servers.cfg': self.source_config}
        companion = {'data/server/db/servers.cfg': b'companion overridden\n',
                     'data/maps/atlas.txt': self.map_text,
                     'data/bin/untrusted.bin': b'excluded generated cache'}
        companion.update({'tools/' + name: b'Game.exe\n' for name in game.runtime.LAUNCHERS})
        self.write_import('upstream-lock.json', 'upstream/ouroboros', game.SOURCE, source)
        self.write_import('content-lock.json', 'upstream/i24', game.DATA, companion)
        self.assets.mkdir()
        (self.assets / 'animations').mkdir()
        (self.assets / 'animations/atlas.anim').write_bytes(self.asset_bytes)
        self.provenance = {'source_commit': game.SOURCE, 'text_data_commit': game.DATA,
            'donors': [{'archive': 'player.pigg', 'bytes': 100, 'sha256': '1' * 64}],
            'asset_count': 1, 'asset_bytes': len(self.asset_bytes), 'extensions': {'.anim': 1}}
        document = {**self.provenance, 'schema_version': 1,
                    'status': 'reviewed_base_assets_byte_checked_runtime_unvalidated',
                    'files': [{'path': 'animations/atlas.anim', 'size': len(self.asset_bytes),
                               'sha256': digest(self.asset_bytes), 'donor': 'player.pigg'}]}
        (self.root / 'assets').mkdir()
        self.manifest = self.root / 'assets/reference-inputs-manifest.json'
        self.manifest.write_bytes(game.assets.canonical(document))
        self.receipt = self.root / 'assets/reference-inputs-receipt.json'
        self.receipt.write_text(json.dumps({
            'source_commit': game.SOURCE, 'text_data_commit': game.DATA,
            'archive_sha256': game.ASSET_ARCHIVE_SHA256, 'archive_bytes': game.ASSET_ARCHIVE_BYTES,
            'manifest_sha256': digest(self.manifest.read_bytes()),
            'asset_count': 1, 'asset_bytes': len(self.asset_bytes)}))
        patches = mock.patch.multiple(game, ASSET_MANIFEST_SHA256=digest(self.manifest.read_bytes()),
            ASSET_COUNT=1, ASSET_BYTES=len(self.asset_bytes), DATA_COUNT=3,
            DATA_BYTES=len(self.source_config) + len(self.map_text) + len(self.asset_bytes))
        patches.start()
        self.addCleanup(patches.stop)
        provenance = mock.patch.object(game.assets, 'provenance', return_value=self.provenance)
        provenance.start()
        self.addCleanup(provenance.stop)

    def write_import(self, filename, destination, commit, files):
        directory = self.root / destination
        entries = []
        for name, data in files.items():
            target = directory / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            entries.append({'path': name, 'size': len(data), 'sha256': digest(data),
                'git_blob': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest(),
                'mode': '100644'})
        manifest = filename.replace('-lock', '-manifest')
        (self.root / manifest).write_text(json.dumps({'commit': commit, 'entries': entries}))
        (self.root / filename).write_text(json.dumps({'commit': commit, 'destination': destination,
            'manifest': manifest, 'files': len(entries), 'bytes': sum(e['size'] for e in entries),
            'source_pair': game.SOURCE}))

    def prepare(self):
        return game.prepare(self.assets, self.output, root=self.root)

    def test_exact_payload_source_config_priority_and_input_preservation(self):
        original = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        manifest = self.prepare()
        expected = {'data/server/db/servers.cfg': self.source_config,
                    'data/maps/atlas.txt': self.map_text,
                    'data/animations/atlas.anim': self.asset_bytes}
        self.assertEqual(set(manifest['files']), set(expected))
        self.assertEqual({p.name for p in self.output.iterdir()}, {'data', game.MANIFEST})
        self.assertEqual(manifest['file_count'], 3)
        self.assertEqual(manifest['scope'], 'reviewed_game_data')
        self.assertFalse(manifest['android_execution_validated'])
        self.assertFalse(manifest['gameplay_validated'])
        for name, data in expected.items():
            self.assertEqual((self.output / name).read_bytes(), data)
            self.assertEqual(manifest['files'][name], {'bytes': len(data), 'sha256': digest(data)})
        self.assertEqual(json.loads((self.output / game.MANIFEST).read_bytes()), manifest)
        self.assertTrue(all(path.read_bytes() == data for path, data in original.items()))
        self.assertEqual((self.assets / 'animations/atlas.anim').read_bytes(), self.asset_bytes)

    def test_changed_asset_refused_before_output_creation(self):
        (self.assets / 'animations/atlas.anim').write_bytes(b'x' * len(self.asset_bytes))
        with self.assertRaisesRegex(ValueError, 'Extracted asset size/hash differs'):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_external_receipt_and_manifest_pins_are_required(self):
        receipt = json.loads(self.receipt.read_text())
        receipt['archive_sha256'] = '0' * 64
        self.receipt.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, 'receipt differs: archive_sha256'):
            self.prepare()
        self.manifest.write_bytes(self.manifest.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'manifest hash differs'):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_unlisted_missing_and_linked_assets_refused(self):
        extra = self.assets / 'unknown.texture'
        extra.write_bytes(b'not reviewed')
        with self.assertRaisesRegex(ValueError, 'Unlisted extracted asset'):
            self.prepare()
        extra.unlink()
        asset = self.assets / 'animations/atlas.anim'
        asset.unlink()
        with self.assertRaisesRegex(ValueError, 'Missing extracted assets'):
            self.prepare()
        source = self.base / 'linked.anim'
        source.write_bytes(self.asset_bytes)
        asset.symlink_to(source)
        with self.assertRaisesRegex(ValueError, 'Symlinks are not allowed'):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_existing_output_is_never_replaced(self):
        self.output.mkdir()
        keep = self.output / 'existing.txt'
        keep.write_bytes(b'preserve')
        with self.assertRaisesRegex(ValueError, 'Output already exists'):
            self.prepare()
        self.assertEqual(keep.read_bytes(), b'preserve')

    def test_text_mutation_after_source_validation_refused(self):
        assemble = game.runtime.stage
        def changed(*args, **kwargs):
            result = assemble(*args, **kwargs)
            (args[0] / 'data/maps/atlas.txt').write_bytes(b'x' * len(self.map_text))
            return result
        with mock.patch.object(game.runtime, 'stage', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'Staged data differs from reviewed input'):
                self.prepare()
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.base.glob('coh-game-data-*')))

    def test_payload_bounds_fail_before_publication(self):
        for bounds in ({'MAX_FILES': 2}, {'MAX_BYTES': 1}):
            with self.subTest(bounds=bounds), mock.patch.multiple(game, **bounds):
                with self.assertRaisesRegex(ValueError, 'inventory bounds'):
                    self.prepare()
                self.assertFalse(self.output.exists())

    def test_binary_cannot_enter_even_with_matching_record(self):
        staged = self.base / 'assembled'
        (staged / 'data').mkdir(parents=True)
        (staged / 'data/client.exe').write_bytes(b'MZ')
        with self.assertRaisesRegex(ValueError, 'Executable or generated cache'):
            game.checked_inventory(staged, {'data/client.exe': {'bytes': 2, 'sha256': digest(b'MZ')}})


class RealGameDataContractTests(unittest.TestCase):
    def test_accepted_immutable_receipts_define_exact_full_payload(self):
        path = game.ROOT / 'assets/reference-inputs-manifest.json'
        manifest = json.loads(path.read_bytes())
        self.assertEqual(digest(path.read_bytes()), game.ASSET_MANIFEST_SHA256)
        expected = game.expected_data(game.ROOT, manifest['files'])
        self.assertEqual(len(expected), 173011)
        self.assertEqual(sum(r['bytes'] for r in expected.values()), 2977730517)
        self.assertIn('data/maps/city_zones/city_01_01/city_01_01.txt', expected)
        self.assertFalse(any(name.endswith(('.exe', '.dll', '.bin', '.pigg')) for name in expected))


if __name__ == '__main__':
    unittest.main()
