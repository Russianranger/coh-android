"""Actual public .29 native ancestry and animation installer failure boundaries.

Native bytes and the serialized game receipt come from the authenticated public
APK. Tiny tracks exercise archive rejection only; full Assets 1.0.0 installation
is separately required by the release startup preflight.
"""
import ast
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'android/guest'), str(ROOT / 'tools')]
import server_animation_package as animation
import native_monorail_contract as monorail
import prepare_monorail_source as native_source

spec = importlib.util.spec_from_file_location('animation_compatibility_fixture',
    ROOT / 'tools/android/atlasgame/test_server_animations.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)

DONOR = {'bytes': 41199716,
         'sha256': 'b417827778f451335ec5299b92e4ba2f6d2a30d6c7706d4a2a4405139236171b'}
GAME_ARCHIVE = {'bytes': 10943638,
                'sha256': '36d815fd6e9b8eeebbf04de756ea05fa9ee4f29a5330a6cde15926522a4215aa'}
ANIMATION_SOURCES = (
    'Common/seq/animtrack.c', 'Common/seq/animtrack.h', 'Common/seq/seqload.c',
    'libs/UtilitiesLib/src/utils/piglib.c', 'libs/UtilitiesLib/src/utils/file.c',
    'libs/UtilitiesLib/src/utils/FolderCache.c', 'libs/UtilitiesLib/src/utils/FolderCacheNode.c',
    'libs/UtilitiesLib/src/utils/PigFileWrapper.c',
    'libs/UtilitiesLib/include/utilitieslib/utils/piglib_internal.h',
)


class AnimationRuntimeCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        donor = Path(os.environ.get('COH_ANIMATION_TEST_DONOR_APK', ROOT / 'out/donor.apk'))
        if not donor.is_file() or animation.file_pin(donor) != DONOR:
            raise AssertionError('Stage the authenticated public .29 APK via COH_ANIMATION_TEST_DONOR_APK; '
                                 'actual native validation must never skip')
        with zipfile.ZipFile(donor) as apk:
            raw = apk.read('assets/runtime/game-package.tar.gz')
        if animation.caches.pin_bytes(raw) != GAME_ARCHIVE:
            raise AssertionError('Published repaired game archive differs')
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
            cls.game = json.load(archive.extractfile('game-package.json'))
            cls.binary = archive.extractfile('MapServer.exe').read()
        if animation.caches.pin_bytes(cls.binary)['sha256'] != animation.MONORAIL_MAPSERVER_SHA256:
            raise AssertionError('Published monorail native binary differs')

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.runtime = self.root / 'runtime'
        self.runtime.mkdir()
        (self.runtime / 'MapServer.exe').write_bytes(self.binary)
        self.document = {'identity': animation.identity()}

    def proof(self, game=None):
        return animation.verify_runtime(self.runtime, self.document,
                                        mapserver_package=self.game if game is None else game)

    def archive_fixture(self):
        bodies, files = fixture.inputs()
        self.pigg = self.root / animation.PIGG
        self.manifest = self.root / animation.MANIFEST
        packed, _ = fixture.producer.write_pigg(self.pigg, files, bodies.__getitem__)
        document = {'format': 1, 'role': animation.ROLE, 'repository_commit': 'a' * 40,
                    'identity': animation.identity(), 'files': files, 'pigg': packed,
                    'loose_inputs_preserved': True, 'native_client_or_server_recompiled': False,
                    'android_execution_validated': False, 'physical_startup_timing_validated': False}
        self.manifest.write_bytes(animation.canonical(document))
        # Only the finite test inventory is substituted. Manifest identity,
        # native receipt, Pig structure, every body/header/hash and install guards
        # all run normally. Complete real assets have a separate preflight gate.
        original = animation.validate_inventory
        patch = mock.patch.object(animation, 'validate_inventory',
            side_effect=lambda values, **kw: original(values, exact=False))
        patch.start()
        self.addCleanup(patch.stop)
        return bodies, document

    def install(self):
        return animation.install(self.pigg, self.manifest, self.runtime, mapserver_package=self.game)

    def test_actual_public_native_reproduces_old_mismatch_and_passes_exact_bridge(self):
        self.assertNotEqual(animation.file_pin(self.runtime / 'MapServer.exe')['sha256'],
                            self.document['identity']['mapserver_sha256'])
        proof = self.proof()
        self.assertEqual(proof['actual_mapserver_sha256'], animation.MONORAIL_MAPSERVER_SHA256)
        self.assertEqual(proof['original_animation_producer_mapserver_sha256'],
                         animation.caches.MAPSERVER_SHA256)
        self.assertEqual(proof['monorail_receipt_sha256'], animation.MONORAIL_RECEIPT_SHA256)
        self.assertTrue(proof['animation_identity_preserved'])
        self.assertFalse(proof['native_animation_reader_changed'])

    def test_missing_or_malformed_additional_consumer_receipt_is_rejected(self):
        for package in (None, {}, {'native_monorail': None}, {'native_monorail': []}):
            with self.subTest(package=package), self.assertRaisesRegex(ValueError, 'Animation runtime/native'):
                animation.verify_runtime(self.runtime, self.document, mapserver_package=package)

    def test_mutated_and_rehashed_receipts_cannot_extend_native_acceptance(self):
        for rehash in (False, True):
            game = copy.deepcopy(self.game)
            game['native_monorail']['receipt']['schema_sources_sha256']['Common/seq/seqload.c'] = 'f' * 64
            if rehash:
                game['native_monorail']['receipt_sha256'] = monorail.canonical_sha(game['native_monorail']['receipt'])
            with self.subTest(rehash=rehash), self.assertRaises(ValueError):
                self.proof(game)

    def test_unknown_binary_is_rejected_even_with_forged_current_hash(self):
        binary = self.runtime / 'MapServer.exe'
        binary.write_bytes(self.binary[:-1] + bytes([self.binary[-1] ^ 1]))
        game = copy.deepcopy(self.game)
        changed = animation.file_pin(binary)['sha256']
        game['files']['MapServer.exe']['sha256'] = changed
        game['native_monorail']['receipt']['mapserver']['sha256'] = changed
        game['native_monorail']['receipt_sha256'] = monorail.canonical_sha(game['native_monorail']['receipt'])
        with self.assertRaisesRegex(ValueError, 'Animation runtime/native'):
            self.proof(game)

    def test_linked_runtime_or_native_binary_is_rejected(self):
        linked = self.root / 'linked-runtime'
        linked.symlink_to(self.runtime, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Animation runtime/native'):
            animation.verify_runtime(linked, self.document, mapserver_package=self.game)
        native = self.runtime / 'MapServer.exe'
        moved = self.root / 'native.exe'
        native.rename(moved)
        native.symlink_to(moved)
        with self.assertRaisesRegex(ValueError, 'Expected regular file'):
            self.proof()

    def test_original_consumer_path_and_identity_are_preserved(self):
        baseline = {'bytes': 1, 'sha256': animation.caches.MAPSERVER_SHA256}
        with mock.patch.object(animation, 'file_pin', return_value=baseline):
            proof = animation.verify_runtime(self.runtime, self.document)
        self.assertEqual(proof['policy'], 'exact_original_animation_producer')
        self.assertEqual(self.document['identity'], animation.identity())
        self.assertEqual(animation.identity()['mapserver_sha256'], animation.caches.MAPSERVER_SHA256)

    def test_present_pigg_installs_reuses_and_preserves_historical_identity_and_loose_inputs(self):
        bodies, document = self.archive_fixture()
        original_manifest = self.manifest.read_bytes()
        loose = self.runtime / 'data' / next(iter(bodies))
        loose.parent.mkdir(parents=True)
        loose.write_bytes(bodies[next(iter(bodies))])
        first = self.install()
        second = self.install()
        self.assertFalse(first['reused'])
        self.assertTrue(second['reused'])
        self.assertEqual(first['native_compatibility'], second['native_compatibility'])
        self.assertEqual(self.manifest.read_bytes(), original_manifest)
        self.assertEqual(animation.file_pin(self.runtime / 'piggs' / animation.PIGG),
                         {key: document['pigg'][key] for key in ('bytes', 'sha256')})
        self.assertEqual(loose.read_bytes(), bodies[next(iter(bodies))])

    def test_mutated_historical_manifest_identity_is_rejected_before_install(self):
        _, document = self.archive_fixture()
        document['identity']['mapserver_sha256'] = animation.MONORAIL_MAPSERVER_SHA256
        self.manifest.write_bytes(animation.canonical(document))
        with self.assertRaisesRegex(ValueError, 'Animation compatibility differs'):
            self.install()
        self.assertFalse((self.runtime / 'piggs').exists())

    def test_corrupt_archive_and_linked_archive_fail_before_install(self):
        self.archive_fixture()
        raw = self.pigg.read_bytes()
        self.pigg.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
        with self.assertRaisesRegex(ValueError, 'Animation Pig payload differs'):
            self.install()
        self.assertFalse((self.runtime / 'piggs').exists())
        target = self.root / 'foreign.pigg'
        self.pigg.rename(target)
        target.write_bytes(raw)
        self.pigg.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'Missing, linked or oversized animation Pig'):
            self.install()

    def test_corrupt_existing_destination_is_preserved_and_rejected(self):
        self.archive_fixture()
        self.install()
        target = self.runtime / 'piggs' / animation.PIGG
        target.chmod(0o600)
        target.write_bytes(b'foreign bytes')
        with self.assertRaisesRegex(ValueError, 'Existing animation Pig differs'):
            self.install()
        self.assertEqual(target.read_bytes(), b'foreign bytes')

    def test_exact_native_source_overlay_leaves_animation_loader_closure_unchanged(self):
        build = monorail.embedded_receipt(self.game)['build_input']
        self.assertEqual(build, native_source.expected_receipt(events_build_input=build['events_build_input']))
        changed = set(build['patched_sha256']) | set(build['overlay_sha256'])
        self.assertFalse(changed.intersection(ANIMATION_SOURCES))
        baseline = json.loads((ROOT / 'docs/source-manifest.json').read_bytes())
        pins = {entry['path']: entry for entry in baseline['entries']}
        for name in ANIMATION_SOURCES:
            with self.subTest(name=name):
                self.assertEqual(animation.file_pin(ROOT / 'upstream/ouroboros' / name),
                                 {'bytes': pins[name]['size'], 'sha256': pins[name]['sha256']})

    def test_atlas_and_kings_install_calls_pass_the_verified_game_package(self):
        tree = ast.parse((ROOT / 'android/guest/local_character_server.py').read_text())
        server = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                      and node.name == 'LocalCharacterServer')
        for method in ('prepare_runtime', 'prepare_kings_row_runtime'):
            body = next(node for node in server.body if isinstance(node, ast.FunctionDef) and node.name == method)
            calls = [node for node in ast.walk(body) if isinstance(node, ast.Call)
                     and ast.unparse(node.func) == 'server_animation_package.install']
            self.assertEqual(len(calls), 1)
            kwargs = {value.arg: ast.unparse(value.value) for value in calls[0].keywords}
            self.assertEqual(kwargs.get('mapserver_package'), 'self.map_package')


if __name__ == '__main__':
    unittest.main()
