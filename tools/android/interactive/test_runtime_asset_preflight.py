"""Host preflight mechanics; real payload installers run in the release gate."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('runtime_asset_preflight', Path(__file__).with_name('qualify_runtime_asset_preflight.py'))
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


def pin(raw): return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


class RuntimeAssetPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.runtime = self.root/'runtime'; self.runtime.mkdir()

    def test_materializes_only_hash_matching_original_sources(self):
        path = self.root/'source.zip'
        raw = b'exact original input'; name = 'data/object_library/example.geo'
        with zipfile.ZipFile(path, 'w') as z: z.writestr('assets/'+name[5:], raw); z.writestr('assets/unrelated.bin', b'not selected')
        with zipfile.ZipFile(path) as z:
            result = module.materialize(self.runtime, {name: pin(raw)}, [z], {})
        self.assertEqual(result['files'], 1)
        self.assertEqual((self.runtime/name).read_bytes(), raw)
        self.assertFalse((self.runtime/'data/unrelated.bin').exists())
        self.assertEqual((self.runtime/name).stat().st_mode & 0o222, 0)

    def test_wrong_bytes_and_missing_source_are_refused(self):
        name = 'data/defs/example.attribute'
        for source in ({}, {name: b'different data'}):
            with self.subTest(source=bool(source)), self.assertRaisesRegex(ValueError, 'source missing'):
                module.materialize(self.runtime, {name: pin(b'expected')}, [], source)
        self.assertFalse((self.runtime/name).exists())

    def test_unsafe_paths_and_existing_destination_are_refused(self):
        for name in ('../escape', '/absolute', 'data/../escape', 'data\\escape', 'data//escape'):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'Unsafe'):
                module.materialize(self.runtime, {name: pin(b'payload')}, [], {name: b'payload'})
        name = 'data/defs/x.attribute'; path = self.runtime/name; path.parent.mkdir(parents=True); path.write_bytes(b'old')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            module.materialize(self.runtime, {name: pin(b'new')}, [], {name: b'new'})
        self.assertEqual(path.read_bytes(), b'old')

    def test_case_conflicting_zip_sources_are_refused(self):
        path = self.root/'source.zip'
        with zipfile.ZipFile(path, 'w') as z: z.writestr('data/x', b'1'); z.writestr('data/X', b'2')
        with zipfile.ZipFile(path) as z, self.assertRaisesRegex(ValueError, 'Case-conflicting'):
            module.materialize(self.runtime, {'data/x': pin(b'1')}, [z], {})

    def test_input_pin_rejects_mutation_and_symlinks(self):
        path = self.root/'source'; path.write_bytes(b'exact')
        module.checked(path, pin(b'exact'))
        path.write_bytes(b'other')
        with self.assertRaisesRegex(ValueError, 'pin differs'): module.checked(path, pin(b'exact'))
        link = self.root/'link'; link.symlink_to(path)
        with self.assertRaisesRegex(ValueError, 'Regular'): module.checked(link, pin(b'other'))

    def test_receipt_normalization_retains_negative_scope_flags(self):
        value = {'elapsed_seconds': 1.2, 'native_runtime_booted': False,
                 'proof': [{'preparation_elapsed_seconds': 99, 'status': 'passed'}]}
        self.assertEqual(module.stable(value), {'native_runtime_booted': False, 'proof': [{'status': 'passed'}]})
        self.assertIn('elapsed_seconds', value)

    def test_full_historical_wrapper_is_mandatory_and_untyped_hash_switch_refused(self):
        fixture = Path(__file__).with_name('fixtures')/'monorail-game-package-0.13.31.json'
        module.checked(fixture, {'bytes': 162281,
            'sha256': '520713891e4d5be9d7a64fb736ef15e37e062a104513ec37bdaf09670898dab7'})
        package = json.loads(fixture.read_bytes())
        value = module.package_native_binding(package)
        self.assertEqual(module.validate_native_binding(value), module.HISTORICAL_MAPSERVER)
        for changed in ({'format': True}, {'authenticated_mapserver': pin(b'arbitrary map')},
                        {'native_consumer_binding': {}}, {'game_package_canonical_sha256': 'a'*64}):
            invalid = dict(value, **changed)
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                module.validate_native_binding(invalid)
        with self.assertRaises(ValueError):
            module.validate_native_binding({'expected_mapserver': module.HISTORICAL_MAPSERVER})

    def test_new_startup_payloads_and_full_client_fx_source_are_explicit(self):
        self.assertEqual(set(module.STARTUP_PAYLOADS), {'native_map_startup_contract.py',
            'server_fx_catalog.py', 'server-fx-catalog.bin', 'server-fx-catalog-manifest.json', 'map-startup-manifest.json'})
        self.assertEqual(module.ASSET_PINS['runtime/client-caches.zip'], {'bytes': 27071659,
            'sha256': '5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051'})
        self.assertNotEqual(module.CLIENT_FULL_FX, module.SERVER_PROJECTED_FX)

    def test_serialized_leaf_proof_cannot_change_native_admission_or_claim_device_execution(self):
        fixture = Path(__file__).with_name('fixtures')/'monorail-game-package-0.13.31.json'
        admission = module.package_native_binding(json.loads(fixture.read_bytes()))
        value = {'status': 'passed', 'scope': module.SCOPE, 'native_runtime_booted': False,
            'physical_execution_validated': False, 'full_private_worktree_mirror_executed': False,
            'installers': {name: {'native_admission': copy.deepcopy(admission),
                'mapserver': module.HISTORICAL_MAPSERVER, 'server_fx_catalog_cold': None,
                'server_fx_catalog_reuse': None} for name in ('atlas', 'kings')}}
        module.validate_proof(value)
        for flag in ('native_runtime_booted', 'physical_execution_validated', 'full_private_worktree_mirror_executed'):
            bad = copy.deepcopy(value); bad[flag] = True
            with self.subTest(flag=flag), self.assertRaises(ValueError): module.validate_proof(bad)
        bad = copy.deepcopy(value); bad['installers']['kings']['native_admission']['native_consumer_binding'] = {}
        with self.assertRaises(ValueError): module.validate_proof(bad)
        bad = copy.deepcopy(value); bad['installers']['atlas']['mapserver'] = pin(b'unknown native')
        with self.assertRaises(ValueError): module.validate_proof(bad)


if __name__ == '__main__': unittest.main()
