import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import package_game_runtime as game
from test_package_reference_runtime import pe_file


class CompositePackageTests(unittest.TestCase):
    def test_game_candidate_requires_explicit_profile_and_donor(self):
        with tempfile.TemporaryDirectory() as temp:
            for profile, donor in (('accepted', Path(temp)), ('loopback', None), ('unknown', None)):
                args = SimpleNamespace(repository_commit='a' * 40, output=Path(temp) / 'out',
                                       game_listener_profile=profile, loopback_game=donor)
                with self.subTest(profile=profile), self.assertRaisesRegex(ValueError, 'profile'):
                    game.assemble(args)
                self.assertFalse(args.output.exists())

    def test_candidate_selection_is_separate_and_accepted_default_is_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for folder, names in (('reference', ('MapServer.exe', 'TestClient.exe')),
                                  ('dbserver', ('DbServer.exe',)), ('resume', ('TestClient.exe',)),
                                  ('bridge', ('TestClientBridge.exe',)),
                                  ('loopback', ('MapServer.exe', 'TestClientCreate.exe', 'TestClientResume.exe'))):
                (root / folder).mkdir()
                for name in names:
                    (root / folder / name).write_bytes(pe_file(('KERNEL32.dll',)) + folder.encode())
            commit = 'a' * 40
            game.bridge_receipt(root / 'bridge', commit)
            candidate = {'build_role': 'loopback_game_diagnostic', 'repository_commit': commit}
            (root / 'loopback' / 'build-info.json').write_text(json.dumps(candidate))
            args = SimpleNamespace(repository_commit=commit, reference=root / 'reference',
                                   dbserver=root / 'dbserver', resume=root / 'resume', bridge=root / 'bridge',
                                   output=root / 'accepted-out')
            def donor(directory, kind, **kwargs):
                return {'repository_commit': commit}, directory, {'manifest': {'role': kind}}
            selected = {name: root / 'loopback' / name
                        for name in ('MapServer.exe', 'TestClientCreate.exe', 'TestClientResume.exe')}
            with patch.object(game, 'verified_donor', side_effect=donor), \
                    patch.object(game, 'verify_resume_client_package', return_value=(root / 'resume/TestClient.exe', {})), \
                    patch('package_loopback_game.verify_loopback_game_package', return_value=(selected, candidate)) as loopback:
                accepted = game.assemble(args)
                loopback.assert_not_called()
                self.assertNotIn('game_listener_profile', accepted)
                self.assertNotIn('loopback_game', accepted['inputs'])
                self.assertEqual(accepted['file_donors']['MapServer.exe'], 'reference')
                self.assertEqual(accepted['file_donors']['TestClientResume.exe'], 'resume')
                original = (args.output / 'MapServer.exe').read_bytes()
                args.output = root / 'candidate-out'
                args.game_listener_profile = 'loopback'
                args.loopback_game = root / 'loopback'
                with self.assertRaisesRegex(ValueError, 'require the loopback DbServer'):
                    game.assemble(args)
                self.assertFalse(args.output.exists())
                args.dbserver_profile = 'loopback'
                actual = game.assemble(args)
                loopback.assert_called_once_with(args.loopback_game, commit, {'repository_commit': commit})
                self.assertEqual(actual['game_listener_profile'], 'loopback')
                self.assertEqual(actual['inputs']['loopback_game']['manifest'], candidate)
                for name, path in selected.items():
                    self.assertEqual(actual['file_donors'][name], 'loopback_game')
                    self.assertEqual((args.output / name).read_bytes(), path.read_bytes())
                self.assertEqual((root / 'accepted-out/MapServer.exe').read_bytes(), original)

    def test_loopback_donor_is_opt_in_and_cannot_substitute_the_accepted_donor(self):
        for profile, pin in (('accepted', game.PINS['dbserver']), ('loopback', game.LOOPBACK_DBSERVER_PIN)):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                manifest = json.loads((game.ROOT / pin[0]).read_text())
                (root / pin[1]).write_text(json.dumps(manifest))
                normal = root / 'normal'
                normal.mkdir()
                records = manifest['variants']['normal']['files']
                for name in records:
                    (normal / name).write_bytes(b'payload validated by record helper')
                with patch.object(game, 'record', side_effect=lambda path: records[path.name]):
                    actual, _, proof = game.verified_donor(root, 'dbserver', dbserver_profile=profile)
                    self.assertEqual(actual, manifest)
                    self.assertEqual(proof['run_id'], pin[2])
                    opposite = 'loopback' if profile == 'accepted' else 'accepted'
                    with self.assertRaisesRegex(ValueError, 'accepted receipt'):
                        game.verified_donor(root, 'dbserver', dbserver_profile=opposite)
                    if profile == 'accepted':
                        self.assertEqual(game.verified_donor(root, 'dbserver')[2]['run_id'], 36451873322)
                with self.assertRaisesRegex(ValueError, 'Unknown DbServer profile'):
                    game.verified_donor(root, 'dbserver', dbserver_profile='unqualified')

    def test_donor_manifest_tampering_is_rejected_before_payloads(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / 'build-info.json'
            manifest = json.loads((game.ROOT / game.PINS['reference'][0]).read_text())
            manifest['repository_commit'] = 'f' * 40
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'accepted receipt'):
                game.verified_donor(root, 'reference')

    def test_collision_selection_is_explicit_and_uses_wine_closure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ref, db = root / 'ref', root / 'db'
            ref.mkdir(); db.mkdir()
            for folder, name, value in ((ref,'CrashRpt.dll',b'old'),(db,'CrashRpt.dll',b'new'),
                                        (ref,'PhysXCore.dll',b'physics'),(db,'DbServer.exe',b'wine')):
                (folder / name).write_bytes(value)
            chosen, collisions = game.choose_files(ref, db)
            self.assertEqual(chosen['CrashRpt.dll'], (db / 'CrashRpt.dll', 'dbserver'))
            self.assertNotEqual(collisions['CrashRpt.dll']['reference_sha256'], collisions['CrashRpt.dll']['dbserver_sha256'])
            self.assertEqual(chosen['TestClientCreate.exe'], (ref / 'TestClient.exe', 'reference'))
            self.assertNotIn('TestClient.exe', chosen)
            self.assertEqual(chosen['PhysXCore.dll'][1], 'reference')

    def test_bridge_receipt_rejects_non_x86_and_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.object(game, 'record', return_value={'pe_machine': 0x8664}):
                with self.assertRaisesRegex(ValueError, 'PE32'):
                    game.bridge_receipt(root, 'a' * 40)
            self.assertFalse((root / 'bridge-build.json').exists())
            with self.assertRaisesRegex(ValueError, 'new directory'):
                game.new_output(root)

    def test_bridge_source_hashes_are_line_ending_independent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in game.BRIDGE_SOURCES:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'one\r\ntwo\r\n')
            one = game.source_hashes(root)
            for name in game.BRIDGE_SOURCES:
                (root / name).write_bytes(b'one\ntwo\n')
            self.assertEqual(one, game.source_hashes(root))


if __name__ == '__main__':
    unittest.main()
