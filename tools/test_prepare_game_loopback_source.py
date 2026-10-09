"""Verify exact staged game provenance and creation/resume overlay composition."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import prepare_game_loopback_source as game
import prepare_resume_client_source as resume


class GameSourceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='coh-game-source-')
        self.addCleanup(self.temporary.cleanup)
        self.source = Path(self.temporary.name) / 'source'
        self.source.mkdir()
        self.pg = game.expected_game_receipt()['postgresql_build_input']
        for name in set(game.GAME_FILES).union(self.pg['patched_sha256']):
            target = self.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(game.ROOT / 'upstream/ouroboros' / name, target)
        game.apply_patch(self.source, (game.ROOT / 'patches/postgresql/0001-dbserver-postgresql.patch')
                         .read_bytes().replace(b'\r\n', b'\n'))
        for name in self.pg['overlay_sha256']:
            target = self.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(game.ROOT / 'database/postgresql/overlay' / name, target)
        self.pg_path = self.source / 'postgresql-build-input.json'
        self.pg_path.write_text(json.dumps(self.pg))

    def test_creation_changes_only_receipted_files_preserving_upstream(self):
        originals = {name: game.sha256(game.ROOT / 'upstream/ouroboros' / name) for name in game.GAME_FILES}
        actual = game.apply_game_overlay(self.source)
        self.assertEqual(actual, game.expected_game_receipt())
        self.assertEqual(actual['source_sha256'], originals)
        self.assertEqual(json.loads((self.source / game.RECEIPT).read_text()), actual)
        self.assertEqual({name: game.sha256(self.source / name) for name in game.GAME_FILES}, actual['patched_sha256'])
        self.assertEqual({name: game.sha256(game.ROOT / 'upstream/ouroboros' / name) for name in game.GAME_FILES}, originals)
        self.assertEqual(json.loads(self.pg_path.read_text()), self.pg)
        self.assertIsNone(actual['resume_build_input'])
        self.assertEqual(actual['runtime_validation'], 'unverified')

    def test_resume_composes_exact_existing_resume_overlay_and_retains_its_receipt(self):
        previous = resume.apply_resume_overlay(self.source)
        actual = game.apply_game_overlay(self.source, variant='resume')
        self.assertEqual(actual, game.expected_game_receipt(variant='resume'))
        self.assertEqual(actual['resume_build_input'], previous)
        self.assertEqual(json.loads((self.source / resume.RECEIPT).read_text()), previous)
        name = resume.RESUME_FILES[0]
        self.assertEqual(actual['source_sha256'][name], previous['patched_sha256'][name])
        self.assertNotEqual(actual['patched_sha256'][name], previous['patched_sha256'][name])
        self.assertIn('COH_RESUME_ONLY_SELECTED', (self.source / name).read_text())

    def test_dirty_inputs_and_pg_base_rejected_before_any_mutation(self):
        for name in (game.GAME_FILES[0], game.GAME_FILES[-1], next(iter(self.pg['patched_sha256'])),
                     next(iter(self.pg['overlay_sha256']))):
            with self.subTest(name=name):
                path = self.source / name
                original = path.read_bytes()
                path.write_bytes(original + b'\n// dirty input\n')
                before = {name: game.sha256(self.source / name) for name in game.GAME_FILES}
                with self.assertRaisesRegex(ValueError, 'Staged source SHA-256 mismatch'):
                    game.apply_game_overlay(self.source)
                self.assertEqual(before, {name: game.sha256(self.source / name) for name in game.GAME_FILES})
                path.write_bytes(original)
        self.assertFalse((self.source / game.RECEIPT).exists())

    def test_wrong_or_missing_resume_profile_rejected_before_patch(self):
        with self.assertRaisesRegex(ValueError, 'Missing resume build receipt'):
            game.apply_game_overlay(self.source, variant='resume')
        resume.apply_resume_overlay(self.source)
        with self.assertRaisesRegex(ValueError, 'Creation source must not contain'):
            game.apply_game_overlay(self.source)
        receipt_path = self.source / resume.RECEIPT
        value = json.loads(receipt_path.read_text())
        value['creation_allowed'] = True
        receipt_path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, 'Resume build receipt mismatch'):
            game.apply_game_overlay(self.source, variant='resume')

    def test_stale_pg_receipt_and_unknown_variant_rejected(self):
        stale = dict(self.pg, source_commit='f' * 40)
        self.pg_path.write_text(json.dumps(stale))
        with self.assertRaisesRegex(ValueError, 'PostgreSQL build receipt mismatch'):
            game.apply_game_overlay(self.source)
        with self.assertRaisesRegex(ValueError, 'Invalid game source variant'):
            game.expected_game_receipt(variant='stock')

    def test_known_windows_crlf_pg_profile_retains_actual_hashes(self):
        for name in self.pg['overlay_sha256']:
            path = self.source / name
            path.write_bytes(path.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
            self.pg['overlay_sha256'][name] = game.sha256(path)
        self.pg_path.write_text(json.dumps(self.pg))
        actual = game.apply_game_overlay(self.source)
        self.assertEqual(actual, game.expected_game_receipt(postgresql_build_input=self.pg))

    def test_repeat_upstream_and_existing_output_rejected(self):
        with self.assertRaisesRegex(ValueError, 'new directory'):
            game.prepare(self.source)
        with self.assertRaisesRegex(ValueError, 'immutable snapshots'):
            game.apply_game_overlay(game.ROOT / 'upstream/ouroboros')
        game.apply_game_overlay(self.source)
        with self.assertRaisesRegex(ValueError, 'already exists'):
            game.apply_game_overlay(self.source)

    def test_actual_startup_precedes_socket_usage_for_both_variants(self):
        for variant in game.VARIANTS:
            receipt = game.expected_game_receipt(variant=variant)
            self.assertEqual(receipt['socket_contract']['mapserver']['required_endpoints'][0]['port'], 7001)
            self.assertEqual(receipt['loopback_only']['outbound_TCP'], 'unchanged')
        game.apply_game_overlay(self.source)
        for name in ('MapServer/src/svr/svr_init.c', 'Utilities/TestClient/src/main.c'):
            source = (self.source / name).read_text()
            entry = source.index('int __cdecl main(' if name.startswith('MapServer') else 'int main(')
            main = source[entry:]
            self.assertLess(main.index('sockGameLoopbackInit()'), main.index('memCheckInit()'))
            self.assertIn('return 2;', main[:main.index('memCheckInit()')])
        packet = (self.source / 'Utilities/TestClient/src/packetFlood.c').read_text()
        self.assertEqual(packet.count('sockGameBindClientUdp(s);'), 2)
        self.assertEqual(packet.count('socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)'), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
