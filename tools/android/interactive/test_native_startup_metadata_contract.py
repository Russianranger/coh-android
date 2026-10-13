"""Controlled receipt/consumer fixtures; no native process or shipping claim."""
import copy
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'android/guest'), str(ROOT/'tools')]
import native_startup_metadata_contract as native
import native_startup_component_migration as migration


@lru_cache(maxsize=2)
def fixture(kind):
    """Mutate only an unused final byte of real retained PE for archive tests.

    This controlled byte fixture is never executed or described as a native
    candidate build/qualification. Production authorities remain absent.
    """
    donor = Path(os.environ.get('COH_ZONE_STARTUP_TEST_DONOR_APK', ROOT/'out/donor.apk'))
    if not donor.is_file():
        donor = Path('/workspace/scratch/5d16603ca7ff/publication-037-evidence/COH-Atlas-Gameplay-0.13.36.apk')
    if not donor.is_file():
        raise AssertionError('Authenticated actual public .36 APK required; no skipped or synthetic donor archive')
    originals = migration.authenticated_donor(donor)
    reader = migration.zip_members if kind == 'game' else migration.game_members
    members, _ = reader(originals[kind])
    names = native.COMPONENTS[kind]
    old_manifest = native.unique_json(members[names['manifest']])
    raw = members[names['executable']]
    controlled_native = raw[:-1] + bytes([raw[-1] ^ 1])
    record = copy.deepcopy(old_manifest['files'][names['executable']])
    record['sha256'] = hashlib.sha256(controlled_native).hexdigest()
    expected = {'format': 1, 'kind': kind, 'shipping_allowed': False,
        'runtime_activation_allowed': False, 'native_record': record,
        'materials': dict.fromkeys(native.MATERIAL_ROLES, {'scope': 'controlled_unit_receipt_only'}),
        'compatibility': {}}
    return originals[kind], members, controlled_native, expected


def package_fixture(kind, compatibility=None, source_compatibility=None):
    _, members, _, expected = fixture(kind)
    expected = copy.deepcopy(expected)
    expected['compatibility'] = copy.deepcopy(compatibility or {})
    if source_compatibility is not None: expected['source_compatibility'] = copy.deepcopy(source_compatibility)
    with patch.dict(native.COMPONENT_AUTHORITIES, {kind: expected}):
        raw = migration.wrap_manifest(members[native.COMPONENTS[kind]['manifest']], kind, expected)
    return native.unique_json(raw), expected


class NativeStartupMetadataContractTests(unittest.TestCase):
    def test_real_authorities_absent_and_activation_dormant(self):
        self.assertEqual(native.COMPONENT_AUTHORITIES, {'game': None, 'mapserver': None})
        self.assertFalse(native.ACTIVATION_IMPLEMENTED)
        for kind in ('game', 'mapserver'):
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'not frozen'):
                native.authority(kind)

    def test_both_raw_original_receipts_restore_byte_exact_order(self):
        for kind in ('game', 'mapserver'):
            package, expected = package_fixture(kind)
            original = fixture(kind)[1][native.COMPONENTS[kind]['manifest']]
            restored, _ = native.previous_package(package, kind)
            self.assertEqual(native.encoded(restored), original)
            with patch.dict(native.COMPONENT_AUTHORITIES, {kind: expected}):
                result = native.validate_package(package, kind)
                self.assertFalse(result['shipping_allowed'])
                self.assertFalse(result['runtime_activation_allowed'])

    def test_old_ancestry_tamper_rejected_after_rehashing_outer_wrapper(self):
        package, _ = package_fixture('mapserver')
        package['native_map_startup']['receipt']['physical_timing_validated'] = True
        with self.assertRaisesRegex(ValueError, 'ancestry changed'):
            native.previous_package(package, 'mapserver')

    def test_new_record_authority_and_scope_tamper_rejected(self):
        package, expected = package_fixture('game')
        for field, value in (('authority_sha256', 'f'*64), ('materials', {}),
            ('scope', {'shipping_allowed': True})):
            candidate = copy.deepcopy(package)
            wrapper = candidate[native.WRAPPER]
            wrapper['receipt'][field] = value
            wrapper['receipt_sha256'] = native.canonical_sha(wrapper['receipt'])
            with self.subTest(field=field), patch.dict(native.COMPONENT_AUTHORITIES, {'game': expected}), self.assertRaises(ValueError):
                native.validate_package(candidate, 'game')

    def test_scope_booleans_cannot_be_replaced_with_numeric_aliases(self):
        package, expected = package_fixture('game')
        wrapper = package[native.WRAPPER]
        wrapper['receipt']['scope']['runtime_activation_allowed'] = 0
        wrapper['receipt_sha256'] = native.canonical_sha(wrapper['receipt'])
        with patch.dict(native.COMPONENT_AUTHORITIES, {'game': expected}), self.assertRaises(ValueError):
            native.validate_package(package, 'game')

    def test_duplicate_and_nonfinite_json_refused(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError): native.unique_json(raw)

    def test_old_consumer_hash_alone_never_authorizes_cache_reuse(self):
        package, expected = package_fixture('mapserver')
        with patch.dict(native.COMPONENT_AUTHORITIES, {'mapserver': expected}), self.assertRaisesRegex(ValueError, 'No authenticated'):
            native.cache_compatibility(package, 'mapserver', previous_consumer_sha256='a'*64,
                provider_identity_sha256='b'*64, bin_recipe_identity_sha256='c'*64, original_proof_sha256='d'*64)

    def test_exact_per_bin_provider_recipe_and_proof_bridge_only(self):
        _, _, _, initial = fixture('mapserver')
        before = fixture('mapserver')[1]
        previous = native.unique_json(before['game-package.json'])['files']['MapServer.exe']['sha256']
        bridge = {'policy': 'exact_provider_recipe_and_native_consumer_parity',
            'previous_consumer_sha256': previous,
            'current_consumer_sha256': initial['native_record']['sha256'],
            'provider_identity_sha256': 'b'*64, 'bin_recipe_identity_sha256': 'c'*64,
            'original_proof_sha256': 'd'*64, 'qualified_per_bin': {'bin/sequencers.bin': {
                'schema_identity_sha256': 'e'*64, 'output_sha256': 'f'*64,
                'native_ids_sha256': '1'*64, 'loader_decisions_sha256': '2'*64}}}
        package, expected = package_fixture('mapserver', {'cache': bridge})
        kwargs = {'previous_consumer_sha256': previous, 'provider_identity_sha256': 'b'*64,
            'bin_recipe_identity_sha256': 'c'*64, 'original_proof_sha256': 'd'*64}
        with patch.dict(native.COMPONENT_AUTHORITIES, {'mapserver': expected}):
            result = native.cache_compatibility(package, 'mapserver', **kwargs)
            self.assertFalse(result['runtime_activation_allowed'])
            for field in kwargs:
                changed = dict(kwargs, **{field: '9'*64})
                with self.subTest(field=field), self.assertRaises(ValueError):
                    native.cache_compatibility(package, 'mapserver', **changed)

    def test_self_consistent_fake_previous_consumer_rejected(self):
        _, _, _, initial = fixture('mapserver')
        bridge = {'policy': 'exact_provider_recipe_and_native_consumer_parity',
            'previous_consumer_sha256': '9'*64,
            'current_consumer_sha256': initial['native_record']['sha256'],
            'provider_identity_sha256': 'b'*64, 'bin_recipe_identity_sha256': 'c'*64,
            'original_proof_sha256': 'd'*64, 'qualified_per_bin': {'bin/sequencers.bin': {
                'schema_identity_sha256': 'e'*64, 'output_sha256': 'f'*64,
                'native_ids_sha256': '1'*64, 'loader_decisions_sha256': '2'*64}}}
        package, expected = package_fixture('mapserver', {'cache': bridge})
        with patch.dict(native.COMPONENT_AUTHORITIES, {'mapserver': expected}), self.assertRaises(ValueError):
            native.cache_compatibility(package, 'mapserver', previous_consumer_sha256='9'*64,
                provider_identity_sha256='b'*64, bin_recipe_identity_sha256='c'*64, original_proof_sha256='d'*64)

    def test_new_map_texture_projection_requires_explicit_consumer_and_source(self):
        _, _, _, initial = fixture('mapserver')
        proof = {'policy': 'exact_native_excluded_texture_directory_v1',
            'native_consumer_sha256': initial['native_record']['sha256'],
            'native_source_path': 'MapServer/src/svr/svr_init.c',
            'native_source_sha256': '2048c22f8380931514cefb429790552295e52dd72e03617973820936e116639d',
            'excluded_top_level_directories': ['texture_library'], 'client_inputs_modified': False}
        package, expected = package_fixture('mapserver', {'server_texture_projection': proof})
        with patch.dict(native.COMPONENT_AUTHORITIES, {'mapserver': expected}):
            self.assertEqual(native.map_texture_projection(package), proof)
        package, expected = package_fixture('mapserver')
        with patch.dict(native.COMPONENT_AUTHORITIES, {'mapserver': expected}), self.assertRaises(ValueError):
            native.map_texture_projection(package)

    def test_game_texture_migration_binds_both_native_and_input_identities(self):
        _, members, _, initial = fixture('game')
        old_sha = native.unique_json(members['client-package.json'])['files']['CityOfHeroes.exe']['sha256']
        old_identity = {'content_identity_sha256': '3'*64, 'data_contract': {'assets': '1.0.0'}}
        bridge = {'policy': 'exact_unchanged_texture_schema_and_inputs', 'texture_header_struct_bytes': 32,
            'previous_executable_sha256': old_sha, 'client_executable_sha256': initial['native_record']['sha256'],
            'previous_content_identity_sha256': '3'*64, 'content_identity_sha256': '4'*64,
            'data_contract': old_identity['data_contract'], 'unchanged_texture_source_pins': {
                name: {'bytes': 1, 'sha256': '5'*64} for name in native.TEXTURE_SOURCE_PATHS}}
        closure = {'previous_texture_source_pins': bridge['unchanged_texture_source_pins'],
            'current_texture_source_pins': bridge['unchanged_texture_source_pins']}
        package, expected = package_fixture('game', {'texture_header_index': bridge}, closure)
        with patch.dict(native.COMPONENT_AUTHORITIES, {'game': expected}):
            result = native.game_texture_index_migration(package, old_identity, '4'*64)
            self.assertFalse(result['runtime_activation_allowed'])
            with self.assertRaises(ValueError): native.game_texture_index_migration(package, old_identity, '6'*64)
            with self.assertRaises(ValueError): native.game_texture_index_migration(package, None, '4'*64)
        for field, invalid in (('texture_header_struct_bytes', 32.0),
            ('unchanged_texture_source_pins', {'arbitrary': True})):
            changed = copy.deepcopy(bridge); changed[field] = invalid
            bad_package, bad_expected = package_fixture('game', {'texture_header_index': changed}, closure)
            with self.subTest(field=field), patch.dict(native.COMPONENT_AUTHORITIES, {'game': bad_expected}), self.assertRaises(ValueError):
                native.game_texture_index_migration(bad_package, old_identity, '4'*64)
        for side in ('current_texture_source_pins', 'previous_texture_source_pins'):
            bool_closure = copy.deepcopy(closure)
            bool_closure[side]['Game/src/render/tex.c']['bytes'] = True
            bad_package, bad_expected = package_fixture('game', {'texture_header_index': bridge}, bool_closure)
            with self.subTest(side=side), patch.dict(native.COMPONENT_AUTHORITIES, {'game': bad_expected}), self.assertRaises(ValueError):
                native.game_texture_index_migration(bad_package, old_identity, '4'*64)
        bool_bridge = copy.deepcopy(bridge)
        bool_bridge['unchanged_texture_source_pins']['Game/src/render/tex.c']['bytes'] = True
        bad_package, bad_expected = package_fixture('game', {'texture_header_index': bool_bridge}, closure)
        with patch.dict(native.COMPONENT_AUTHORITIES, {'game': bad_expected}), self.assertRaises(ValueError):
            native.game_texture_index_migration(bad_package, old_identity, '4'*64)
        partial = {name: source_pin for name, source_pin in bridge['unchanged_texture_source_pins'].items()
            if name.startswith('Game/')}
        partial_closure = {'previous_texture_source_pins': partial, 'current_texture_source_pins': partial}
        changed = copy.deepcopy(bridge); changed['unchanged_texture_source_pins'] = partial
        bad_package, bad_expected = package_fixture('game', {'texture_header_index': changed}, partial_closure)
        with patch.dict(native.COMPONENT_AUTHORITIES, {'game': bad_expected}), self.assertRaises(ValueError):
            native.game_texture_index_migration(bad_package, old_identity, '4'*64)
        bad_closure = {'previous_texture_source_pins': {'arbitrary': True},
            'current_texture_source_pins': {'arbitrary': True}}
        changed = copy.deepcopy(bridge); changed['unchanged_texture_source_pins'] = {'arbitrary': True}
        bad_package, bad_expected = package_fixture('game', {'texture_header_index': changed}, bad_closure)
        with patch.dict(native.COMPONENT_AUTHORITIES, {'game': bad_expected}), self.assertRaises(ValueError):
            native.game_texture_index_migration(bad_package, old_identity, '4'*64)



if __name__ == '__main__': unittest.main()
