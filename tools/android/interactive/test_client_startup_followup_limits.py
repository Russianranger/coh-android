"""Exercise the real guest callers for the larger visual pack and restart tree.

Payload size fixtures mock file stat/hash, and byte-boundary staging uses sparse
readonly inputs. These checks exercise the actual guards without large buffers
or any accepted physical game-test repetition.
"""
from contextlib import ExitStack
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'android/guest'))
import client_startup_diagnostic as client
import client_visual_assets as visual
import local_character_server as server
import prepare_client_appearance_assets as producer


class ClientStartupFollowupCallerLimitsTests(unittest.TestCase):
    def verify(self, overrides, *, expected_overrides=None, digest_overrides=None):
        sizes = {name: 1 for name in client.REQUIRED}
        sizes.update(overrides)
        expected = dict(sizes, **(expected_overrides or {}))
        hashes = {name: 'a'*64 for name in sizes}
        manifest = {'format': 1, 'scope': client.SCOPE,
            'files': {name: {'bytes': expected[name], 'sha256': hashes[name]} for name in sizes}}
        paths = {}
        for name, size in sizes.items():
            path = Mock(name=name)
            path.is_file.return_value = True
            path.is_symlink.return_value = False
            path.stat.return_value = SimpleNamespace(st_size=size)
            paths[name] = path
        reverse = {id(path): name for name, path in paths.items()}
        paths.setdefault('client-manifest.json', Mock())
        def digest(path):
            name = reverse[id(path)]
            return (digest_overrides or {}).get(name, hashes[name])
        assets = MagicMock()
        assets.__truediv__.side_effect = lambda name: paths[name]
        with patch.object(client, 'read_json', return_value=manifest), \
                patch.object(client.base, 'file_hash', side_effect=digest), \
                patch.object(client.base, 'verify_pe32') as verify_pe:
            result = client.verify_assets(assets)
        self.assertEqual(verify_pe.call_count, 3)
        self.assertEqual(result, hashes)
        return result

    def test_complete_current_inventory_accepts_actual_larger_pack_and_manifest(self):
        self.assertGreater(visual.ARCHIVE_BYTES, 128*1024**2)
        self.assertLessEqual(visual.ARCHIVE_BYTES, 1024**3)
        self.verify({'client-visual-assets.zip': visual.ARCHIVE_BYTES,
            'client-visual-manifest.json': len(producer.manifest_bytes(ROOT/'assets/client-appearance-manifest.json'))})

    def test_exact_visual_names_have_finite_archive_and_manifest_caps(self):
        for name, limit in (('client-visual-assets.zip', 1024**3),
                ('client-visual-manifest.json', 64*1024**2)):
            with self.subTest(name=name, size=limit):
                self.verify({name: limit})
            with self.subTest(name=name, size=limit+1), \
                    self.assertRaisesRegex(server.base.DiagnosticError, 'oversized client input'):
                self.verify({name: limit+1})

    def test_unrelated_names_keep_their_previous_caps(self):
        for name in ('unrelated.zip', 'client-visual-assets.zip.tmp', 'Client-visual-assets.zip'):
            with self.subTest(name=name), \
                    self.assertRaisesRegex(server.base.DiagnosticError, 'oversized client input'):
                self.verify({name: 128*1024**2+1})
        for name in ('client-caches.zip', 'server-caches.zip'):
            with self.subTest(name=name):
                self.verify({name: 512*1024**2})
            with self.subTest(name=name, oversized=True), \
                    self.assertRaisesRegex(server.base.DiagnosticError, 'oversized client input'):
                self.verify({name: 512*1024**2+1})
        self.verify({'atlas-world-supplement.zip': 256*1024**2})
        with self.assertRaisesRegex(server.base.DiagnosticError, 'oversized client input'):
            self.verify({'atlas-world-supplement.zip': 256*1024**2+1})

    def test_larger_visual_inputs_still_require_exact_expected_size_and_hash(self):
        for name, size in (('client-visual-assets.zip', visual.ARCHIVE_BYTES),
                ('client-visual-manifest.json', 3*1024**2)):
            with self.subTest(name=name, wrong='hash'), \
                    self.assertRaisesRegex(server.base.DiagnosticError, 'Client input pin differs'):
                self.verify({name: size}, digest_overrides={name: 'b'*64})
            with self.subTest(name=name, wrong='size'), \
                    self.assertRaisesRegex(server.base.DiagnosticError, 'Client input pin differs'):
                self.verify({name: size}, expected_overrides={name: size-1})


class ClientStartupFollowupRestartBudgetTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.work = self.root/'work'
        self.source = self.work/'data'
        self.source.mkdir(parents=True)
        self.imported = self.root/'import'
        self.imported.mkdir()
        self.value = server.LocalCharacterServer.__new__(server.LocalCharacterServer)
        self.value.owner = SimpleNamespace(work=self.work,
            args=SimpleNamespace(game_data=self.imported))
        self.value.ctx = SimpleNamespace(check=Mock(), event=Mock())

    def readonly(self, relative, *, size=1):
        path = self.source/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('wb') as stream:
            stream.truncate(size)
        path.chmod(0o444)
        return path

    def test_restart_stages_all_installed_visual_leaves_above_generated_allowance(self):
        self.readonly('defs/imported.def')
        for index in range(4096):
            self.readonly(f'defs/generated-{index}.def')
        for index in range(visual.FILE_COUNT):
            self.readonly(f'texture_library/visual-{index}.texture')
        original = self.source/'texture_library/visual-0.texture'
        before = original.stat()
        with ExitStack() as patches:
            patches.enter_context(patch.object(server.device, 'DATA_COUNT', 1))
            patches.enter_context(patch.object(server.world, 'FILE_COUNT', 0))
            patches.enter_context(patch.object(server.avatar, 'ALLOWED', frozenset()))
            target = self.root/'restart'
            staged = self.value.stage_map_data(self.source, target)
            self.assertEqual(staged['files'], 1+4096+visual.FILE_COUNT)
            self.assertEqual(staged['linked_immutable_files'], staged['files'])
            self.assertEqual(staged['copied_private_files'], 0)
            self.assertEqual((target/'texture_library/visual-0.texture').resolve(), original)
            self.assertEqual(original.stat(), before)
            self.readonly('texture_library/unaccounted.texture')
            with self.assertRaisesRegex(server.base.DiagnosticError, 'Private map data exceeded bound'):
                self.value.stage_map_data(self.source, self.root/'over-count')

    def test_restart_byte_bound_includes_exact_visual_payload_and_rejects_one_extra(self):
        before_visual = (server.device.DATA_BYTES + 1024**3
            + server.world.PAYLOAD_BYTES + server.avatar.PAYLOAD_BYTES)
        limit = before_visual + visual.PAYLOAD_BYTES
        original = self.readonly('texture_library/sparse.texture', size=limit)
        target = self.root/'byte-bound'
        staged = self.value.stage_map_data(self.source, target)
        self.assertEqual(staged['bytes'], limit)
        self.assertGreater(staged['bytes'], before_visual)
        self.assertTrue((target/'texture_library/sparse.texture').is_symlink())
        original.chmod(0o644)
        with original.open('r+b') as stream:
            stream.truncate(limit+1)
        original.chmod(0o444)
        with self.assertRaisesRegex(server.base.DiagnosticError, 'Private map data exceeded bound'):
            self.value.stage_map_data(self.source, self.root/'over-bytes')


if __name__ == '__main__':
    unittest.main()
