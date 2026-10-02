"""Reject unreviewed native, cache-history, data and publication changes."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import urllib.error
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT/'android/guest'))
sys.path.insert(0, str(ROOT/'tools'))
import build_responsiveness_apk as package
import native_responsiveness_contract as contract
import prepare_character_events_source as events
import prepare_client_texture_source as texture
import prepare_client_graphics_source as graphics
import prepare_runtime
import prepare_game_loopback_source as loopback
import prepare_mapserver_progress_source as progress


def pe(seed, size=100):
    return {'size': size, 'sha256': seed*64, 'pe_machine': 0x14c,
            'imports': ['KERNEL32.dll'], 'delay_imports': []}


def receipt():
    return {'format': 1, 'role': contract.ROLE, 'repository_commit': 'a'*40,
        'source_commit': contract.SOURCE, 'data_commit': contract.DATA,
        'configuration': 'OptDebug', 'architecture': 'Win32',
        'runtime_execution_validated': False, 'postgresql_persistence_fixture': False,
        'files': {'CityOfHeroes.exe': pe('1'), 'MapServer.exe': pe('2'), 'client-launcher.exe': pe('3')},
        'build_inputs': {'character_events': events.expected_events_receipt(),
            'client_texture': texture.expected_texture_receipt(), 'graphics_profile': graphics.expected_graphics_receipt()},
        'retained_cache': {'archive': {'bytes': 100, 'sha256': '4'*64}, 'executable_sha256': '5'*64,
            'schema_changed': False, 'schema_sources_sha256': {'reader.c': '6'*64}},
        'retained_native_files': {'client': {f'dependency{i}.dll': pe('7') for i in range(20)},
                                  'game': {'DbServer.exe': dict(pe('8'), bytes=100)}}}


class NativeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = receipt()

    def setUp(self):
        self.value = copy.deepcopy(self.original)

    def test_exact_source_receipts_and_candidate_status_are_required(self):
        self.assertEqual(self.value, contract.validate_receipt(self.value))
        mutations = [(['runtime_execution_validated'], True), (['postgresql_persistence_fixture'], True),
            (['source_commit'], 'f'*40), (['files', 'CityOfHeroes.exe', 'pe_machine'], 0x8664),
            (['build_inputs', 'client_texture', 'parse6_schema_changes'], True),
            (['build_inputs', 'graphics_profile', 'runtime_validation'], 'passed')]
        for keys, new in mutations:
            candidate = copy.deepcopy(self.value); node = candidate
            for key in keys[:-1]: node = node[key]
            node[keys[-1]] = new
            with self.subTest(keys=keys), self.assertRaises(ValueError): contract.validate_receipt(candidate)

    def test_cache_history_cannot_be_relabelled_for_the_new_executable(self):
        for key, value in (('schema_changed', True), ('executable_sha256', self.value['files']['CityOfHeroes.exe']['sha256']),
                           ('schema_sources_sha256', {})):
            candidate = copy.deepcopy(self.value); candidate['retained_cache'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): contract.validate_receipt(candidate)

    def client(self):
        candidate = {'repository_commit': self.value['repository_commit'],
            'source_commit': contract.SOURCE, 'data_commit': contract.DATA,
            'android_execution_validated': False, 'gameplay_validated': False,
            'native_responsiveness': {'receipt': self.value, 'receipt_sha256': contract.canonical_sha(self.value)},
            'files': {**self.value['retained_native_files']['client'], 'CityOfHeroes.exe': self.value['files']['CityOfHeroes.exe']}}
        return candidate

    def test_new_client_is_bound_to_the_complete_retained_dll_closure(self):
        value = self.client()
        self.assertEqual(self.value['files']['CityOfHeroes.exe'], contract.client_contract(value, self.value))
        for name in ('CityOfHeroes.exe', 'dependency0.dll'):
            candidate = copy.deepcopy(value); candidate['files'][name] = pe('f')
            with self.subTest(name=name), self.assertRaises(ValueError): contract.client_contract(candidate)

    def test_embedded_receipt_hash_and_commit_cannot_change(self):
        for key, value in (('repository_commit', 'b'*40), ('receipt_sha256', 'f'*64)):
            candidate = self.client()
            if key == 'receipt_sha256': candidate['native_responsiveness'][key] = value
            else: candidate[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): contract.client_contract(candidate)

    def game(self):
        build = self.value['build_inputs']['character_events']
        producer = {'build_role': 'character_events', 'repository_commit': self.value['repository_commit'],
            'build_input': build, 'files': {'MapServer.exe': self.value['files']['MapServer.exe']},
            'progress_contract': build['progress_contract'], 'events_contract': build['events_contract']}
        raw = (json.dumps(producer, indent=2)+'\n').encode()
        map_record = dict(self.value['files']['MapServer.exe'], bytes=100); del map_record['size']
        return {'repository_commit': self.value['repository_commit'],
            'postgresql_persistence_fixture': False, 'runtime_execution_validated': False,
            'native_responsiveness': {'receipt': self.value, 'receipt_sha256': contract.canonical_sha(self.value)},
            'files': {**self.value['retained_native_files']['game'], 'MapServer.exe': map_record},
            'character_events_contract': build['events_contract'], 'inputs': {'mapserver_progress': {
                'repository_commit': self.value['repository_commit'], 'manifest': producer,
                'manifest_sha256': hashlib.sha256(raw).hexdigest()}}}

    def test_map_candidate_keeps_the_original_progress_contract(self):
        value = self.game(); proof = contract.events_progress_contract(value)
        self.assertEqual(self.value['build_inputs']['character_events']['progress_contract'], proof['contract'])
        candidate = copy.deepcopy(value); candidate['character_events_contract'] = {}
        with self.assertRaises(ValueError): contract.events_progress_contract(candidate)

    def test_map_candidate_cannot_change_dbserver_or_new_map_bytes(self):
        for name in ('DbServer.exe', 'MapServer.exe'):
            value = self.game(); value['files'][name]['sha256'] = 'f'*64
            with self.subTest(name=name), self.assertRaises(ValueError): contract.events_progress_contract(value)


class PackagingTests(unittest.TestCase):
    def test_windows_pg_encoding_provenance_is_preserved_and_unknown_hash_refused(self):
        pg = prepare_runtime.expected_pg_receipt(ROOT, json.loads((ROOT/'upstream-lock.json').read_text()))
        for name in pg['overlay_sha256']:
            if Path(name).suffix in ('.c', '.h'):
                raw = (ROOT/'database/postgresql/overlay'/name).read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
                pg['overlay_sha256'][name] = hashlib.sha256(raw).hexdigest()
        game = loopback.expected_game_receipt(ROOT, pg, 'creation')
        received = events.expected_events_receipt(ROOT, progress.expected_progress_receipt(ROOT, game))
        self.assertEqual(received, package.native_package.expected_source_receipt('character_events', received))
        bad = copy.deepcopy(received)
        nested = bad['progress_build_input']['game_build_input']['postgresql_build_input']
        first = next(iter(nested['overlay_sha256']))
        nested['overlay_sha256'][first] = 'f'*64
        with self.assertRaises(ValueError): package.native_package.expected_source_receipt('character_events', bad)

    def test_manifest_changes_only_version_metadata_and_preserves_app_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            source = package.ROOT/'android/interactive/src/main/AndroidManifest.xml'
            old = source.read_bytes(); target = Path(directory)/'AndroidManifest.xml'
            package.repair_android_manifest(source, target)
            package.builder(repaired=True).verify_source_manifest(target)
            self.assertIn(b'android:versionName="0.11.5"', target.read_bytes())
            self.assertIn(b'android:versionCode="11"', target.read_bytes())
            self.assertEqual(old, source.read_bytes())

    def test_prepared_cache_data_avatar_and_proot_are_outside_mutation_scope(self):
        for name in ('client-caches.zip', 'character_session_budget.py', 'character_server_data_cache.py',
                     'character-avatar-defaults.zip', 'atlas-world-supplement.zip', 'dbserver-package.tar.gz',
                     'postgresql-runtime.tar.gz', 'accepted-runtime-manifest.json'):
            self.assertNotIn('assets/runtime/'+name, package.ALLOWED_PAYLOADS)
        self.assertEqual(set(package.NATIVE_PAYLOADS), {'client-runtime.zip', 'game-package.tar.gz', 'client-launcher.exe'})

    def test_schema_sources_are_actual_immutable_readers(self):
        pins = package.native_package.schema_pins()
        self.assertTrue(pins)
        for name, digest in pins.items():
            self.assertEqual(hashlib.sha256((ROOT/'upstream/ouroboros'/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest(), digest)

    def test_release_upload_mismatch_is_never_published(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); paths = tuple(root/name for name in (package.APK_NAME, package.APK_NAME+'.sha256', package.NOTES_NAME))
            for path in paths: path.write_bytes(b'test')
            report = dict(package.builder().file_pin(paths[0]), repository_commit='a'*40)
            api = mock.Mock()
            def request(path, data=None, **kwargs):
                if path.startswith(('/releases/tags/', '/git/ref/tags/')):
                    raise urllib.error.HTTPError('https://api.github.com', 404, 'Not Found', {}, None)
                if path == '/releases':
                    return {'id': 1, 'draft': True, 'prerelease': True, 'tag_name': package.RELEASE_TAG}
                return {'state': 'uploaded', 'name': data.name, 'size': data.stat().st_size, 'digest': 'sha256:'+'f'*64}
            api.request.side_effect = request
            with self.assertRaises(ValueError): package.publish_release(api, report, paths, 'notes')
            self.assertFalse(any(call.kwargs.get('method') == 'PATCH' for call in api.request.call_args_list))


if __name__ == '__main__': unittest.main()
