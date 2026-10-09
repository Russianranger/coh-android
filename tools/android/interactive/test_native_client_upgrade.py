"""Exercise candidate installation without recreating imported client links."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import zipfile

import package_startup_bundle_client as startup_package
import prepare_client_texture_source as texture_source
import prepare_client_graphics_source as graphics_source

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    'client_upgrade_fixtures', ROOT / 'tools/android/client/test_guest.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
guest = fixtures.guest


class NativeClientUpgradeTests(unittest.TestCase):
    def setUp(self):
        fixtures.WorktreeTests.setUp(self)

    def candidate(self):
        path = self.assets / 'client-runtime.zip'
        with zipfile.ZipFile(path) as archive:
            content = {name: archive.read(name) for name in archive.namelist()}
        manifest = json.loads(content.pop('client-package.json'))
        payload = fixtures.pe_bytes() + b'candidate-native-client'
        content['CityOfHeroes.exe'] = payload
        for pin in manifest['files'].values():
            pin.update(imports=[], delay_imports=[])
        manifest['files']['CityOfHeroes.exe'].update(
            size=len(payload), sha256=hashlib.sha256(payload).hexdigest())
        shared = {'source_commit': guest.SOURCE, 'runtime_validation': 'unverified'}
        receipt = {
            'format': 1, 'role': guest.native_candidate.ROLE,
            'repository_commit': 'a' * 40, 'source_commit': guest.SOURCE,
            'data_commit': guest.DATA, 'configuration': 'OptDebug', 'architecture': 'Win32',
            'runtime_execution_validated': False, 'postgresql_persistence_fixture': False,
            'files': {name: copy.deepcopy(manifest['files']['CityOfHeroes.exe'])
                      for name in guest.native_candidate.EXECUTABLES},
            'build_inputs': {
                'character_events': dict(shared, build_role='character_events',
                                         progress_build_input={'build_role': 'mapserver_progress'}),
                'client_texture': dict(shared, role='opt_in_client_texture_header_index',
                                       runtime_performance_validated=False, parse6_schema_changes=False),
                'graphics_profile': dict(shared)},
            'retained_cache': {
                'schema_changed': False, 'executable_sha256': self.exesha,
                'archive': {'bytes': (self.assets / 'client-caches.zip').stat().st_size,
                            'sha256': guest.base.file_hash(self.assets / 'client-caches.zip')},
                'schema_sources_sha256': {'fixture': 'b' * 64}},
            'retained_native_files': {
                'client': {name: pin for name, pin in manifest['files'].items()
                           if name != 'CityOfHeroes.exe'},
                'game': {'DbServer.exe': copy.deepcopy(manifest['files']['CityOfHeroes.exe'])}}}
        manifest.update(repository_commit='a' * 40, android_execution_validated=False,
                        gameplay_validated=False, native_responsiveness={
                            'receipt': receipt,
                            'receipt_sha256': guest.native_candidate.canonical_sha(receipt)})
        with zipfile.ZipFile(path, 'w') as archive:
            for name, value in content.items(): archive.writestr(name, value)
            archive.writestr('client-package.json', json.dumps(manifest))
        (self.assets / 'native-responsiveness.json').write_text(json.dumps(receipt))
        return receipt

    def prepare(self):
        return guest.prepare_worktree(self.work, self.data, self.assets, self.identity, self.context)

    def startup_derivative(self):
        path = self.assets / 'client-runtime.zip'
        with zipfile.ZipFile(path) as archive:
            content = {name: archive.read(name) for name in archive.namelist()}
        manifest = json.loads(content.pop('client-package.json'))
        frozen = manifest['native_responsiveness']['receipt']
        frozen['build_inputs']['client_texture'] = texture_source.expected_texture_receipt()
        frozen['build_inputs']['graphics_profile'] = graphics_source.expected_graphics_receipt()
        manifest['native_responsiveness']['receipt_sha256'] = guest.native_candidate.canonical_sha(frozen)
        (self.assets / 'native-responsiveness.json').write_text(json.dumps(frozen))
        content['CityOfHeroes.exe'] = fixtures.pe_bytes() + b'verified-root-startup-native-client'
        record = copy.deepcopy(manifest['files']['CityOfHeroes.exe'])
        record.update(size=len(content['CityOfHeroes.exe']),
            sha256=hashlib.sha256(content['CityOfHeroes.exe']).hexdigest())
        derivative = {'format': 1, 'role': startup_package.ROLE, 'repository_commit': 'c' * 40,
            'source_commit': guest.SOURCE, 'data_commit': guest.DATA, 'configuration': 'OptDebug',
            'architecture': 'Win32', 'build_targets': ['Game'], 'postgresql_persistence_fixture': False,
            'runtime_execution_validated': False, 'replacement_scope': 'CityOfHeroes.exe_only',
            'retained_native_dependencies_changed': False,
            'retained_source_inputs': copy.deepcopy(frozen['build_inputs']),
            'schema_sources_sha256': copy.deepcopy(frozen['retained_cache']['schema_sources_sha256']),
            'build_input': startup_package.expected_receipt(), 'files': {'CityOfHeroes.exe': record}}
        manifest['startup_bundle_client'] = {'manifest': derivative,
            'manifest_sha256': guest.native_candidate.canonical_sha(derivative),
            'base_responsiveness_receipt_sha256': guest.native_candidate.canonical_sha(frozen),
            'base_client_executable': copy.deepcopy(frozen['files']['CityOfHeroes.exe'])}
        manifest['files']['CityOfHeroes.exe'] = record
        with zipfile.ZipFile(path, 'w') as archive:
            for name, value in content.items(): archive.writestr(name, value)
            archive.writestr('client-package.json', json.dumps(manifest))
        return manifest

    def test_startup_derivative_upgrades_current_candidate_in_place(self):
        self.candidate()
        work, previous = self.prepare()
        generated = work / 'data/bin/generated.bin'
        generated.write_bytes(b'valuable current runtime cache')
        link = work / 'data/textures/a.texture'
        before = link.lstat().st_ino
        self.startup_derivative()
        with patch.object(guest.os, 'scandir', side_effect=AssertionError('recreated input tree')):
            again, report = self.prepare()
        self.assertEqual(work, again)
        self.assertTrue(report['native_executable_upgraded'])
        self.assertTrue(report['source_root_preserved'])
        self.assertEqual(before, link.lstat().st_ino)
        self.assertEqual(b'valuable current runtime cache', generated.read_bytes())
        proof = report['native_texture_index_migration']
        self.assertEqual(previous['content_identity_sha256'], proof['previous_client_identity']['content_identity_sha256'])
        self.assertNotIn('native_texture_index_migration', json.loads((work / 'client-work.json').read_text()))
        retry = self.prepare()[1]
        self.assertTrue(retry['reused'])
        self.assertEqual(proof, retry['native_texture_index_migration'])

    def test_startup_derivative_interrupted_copy_marker_recovers_exact_old_index_proof(self):
        self.candidate()
        work, previous = self.prepare()
        (work / 'data/bin/generated.bin').write_bytes(b'keep current cache')
        self.startup_derivative()
        with patch.object(guest.base, 'private_write', side_effect=OSError('Interrupted receipt rename')):
            with self.assertRaises(OSError): self.prepare()
        with patch.object(guest.os, 'scandir', side_effect=AssertionError('recreated input tree')):
            again, report = self.prepare()
        self.assertEqual(work, again)
        self.assertEqual(b'keep current cache', (work / 'data/bin/generated.bin').read_bytes())
        proof = report['native_texture_index_migration']
        self.assertEqual(previous['content_identity_sha256'], proof['previous_client_identity']['content_identity_sha256'])
        self.assertTrue(proof['native_source_closure_verified'])

    def test_startup_derivative_foreign_previous_candidate_rejected_before_replacement(self):
        self.candidate()
        work, _ = self.prepare()
        target = work / 'CityOfHeroes.exe'
        target.chmod(0o600)
        target.write_bytes(target.read_bytes() + b'foreign bytes')
        before = guest.base.file_hash(target)
        self.startup_derivative()
        with self.assertRaises(guest.base.DiagnosticError): self.prepare()
        self.assertEqual(before, guest.base.file_hash(target))

    def test_startup_derivative_unrelated_native_producer_and_cache_mutations_rejected(self):
        self.candidate()
        self.prepare()
        original = self.startup_derivative()
        for changed in ('base', 'schema', 'source', 'map', 'validation', 'dll'):
            candidate = copy.deepcopy(original)
            wrapper = candidate['startup_bundle_client']
            native = wrapper['manifest']
            if changed == 'base': wrapper['base_client_executable']['sha256'] = 'f' * 64
            if changed == 'schema': native['schema_sources_sha256'] = {'foreign': 'f' * 64}
            if changed == 'source': native['retained_source_inputs']['client_texture']['patch_sha256'] = 'f' * 64
            if changed == 'map': native['files']['MapServer.exe'] = native['files']['CityOfHeroes.exe']
            if changed == 'validation': native['build_input']['gameplay_validation_changes'] = True
            if changed == 'dll': candidate['files']['fixture0.dll']['sha256'] = 'f' * 64
            wrapper['manifest_sha256'] = guest.native_candidate.canonical_sha(native)
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                guest.native_candidate.client_contract(candidate)

    def test_exact_old_executable_upgrade_retains_links_and_generated_caches(self):
        work, _ = self.prepare()
        generated = work / 'data/bin/generated.bin'
        generated.write_bytes(b'valuable generated cache')
        inode = (work / 'data/textures/a.texture').lstat().st_ino
        receipt = self.candidate()
        with patch.object(guest.os, 'scandir', side_effect=AssertionError('recreated input tree')):
            again, report = self.prepare()
        self.assertTrue(report['native_executable_upgraded'])
        self.assertFalse(report['wrapper_only_migration'])
        self.assertEqual((again / 'data/textures/a.texture').lstat().st_ino, inode)
        self.assertEqual((again / 'data/bin/generated.bin').read_bytes(), b'valuable generated cache')
        self.assertEqual(guest.base.file_hash(again / 'CityOfHeroes.exe'),
                         receipt['files']['CityOfHeroes.exe']['sha256'])
        self.assertTrue(self.prepare()[1]['reused'])

    def test_unknown_executable_is_rejected_before_upgrade(self):
        work, _ = self.prepare()
        target = work / 'CityOfHeroes.exe'
        target.chmod(0o600)
        target.write_bytes(target.read_bytes() + b'foreign')
        old_hash = guest.base.file_hash(target)
        self.candidate()
        with self.assertRaises(guest.base.DiagnosticError): self.prepare()
        self.assertEqual(guest.base.file_hash(target), old_hash)

    def test_changed_retained_dll_is_rejected_before_client_replacement(self):
        work, _ = self.prepare()
        target = work / 'fixture0.dll'
        target.chmod(0o600)
        target.write_bytes(target.read_bytes() + b'foreign')
        self.candidate()
        with self.assertRaises(guest.base.DiagnosticError): self.prepare()
        self.assertEqual(guest.base.file_hash(work / 'CityOfHeroes.exe'), self.exesha)

    def test_interrupted_marker_publication_recovers_verified_candidate(self):
        work, _ = self.prepare()
        (work / 'data/bin/generated.bin').write_bytes(b'keep')
        self.candidate()
        with patch.object(guest.base, 'private_write', side_effect=OSError('interrupted marker')):
            with self.assertRaises(OSError): self.prepare()
        with patch.object(guest.os, 'scandir', side_effect=AssertionError('recreated input tree')):
            again, report = self.prepare()
        self.assertTrue(report['reused'])
        self.assertEqual((again / 'data/bin/generated.bin').read_bytes(), b'keep')

    def test_candidate_requires_matching_installed_receipt_and_original_cache_donor(self):
        self.prepare()
        receipt = self.candidate()
        for mutation in ('receipt', 'cache'):
            path = self.assets / ('native-responsiveness.json' if mutation == 'receipt' else 'client-caches.zip')
            original = path.read_bytes()
            if mutation == 'receipt':
                changed = copy.deepcopy(receipt)
                changed['repository_commit'] = 'f' * 40
                path.write_text(json.dumps(changed))
            else:
                path.write_bytes(original + b'foreign suffix')
            with self.subTest(mutation=mutation), self.assertRaises((ValueError, guest.base.DiagnosticError)):
                self.prepare()
            path.write_bytes(original)


if __name__ == '__main__': unittest.main()
