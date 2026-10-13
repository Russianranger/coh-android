import copy
import unittest
import native_startup_metadata_admission as native


class NativeMetadataAdmissionTests(unittest.TestCase):
    def test_closed_promotions_require_exact_typed_false_values(self):
        value = {'game': {'enabled': False}, 'mapserver': {'enabled': False}}
        self.assertEqual(native.validate_disabled_promotions(value), value)
        for changed in ({'game': {'enabled': 0}, 'mapserver': {'enabled': False}},
            {'game': {'enabled': True}, 'mapserver': {'enabled': False}},
            {'game': {'enabled': False}, 'mapserver': {'enabled': True}},
            {'game': {'enabled': False}, 'mapserver': {'enabled': False, 'proof': 'passed'}},
            {'game': {'enabled': False}}, None):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                native.validate_disabled_promotions(changed)

    def fixture(self):
        component = {'files': {'MapServer.exe': native.RETAINED_MAP}, 'old_producer': 32}
        dummy = {'bytes': 1, 'sha256': 'a'*64}
        receipt = {'format': 1, 'role': 'nonshipping_map_metadata_research',
            'previous_component': component,
            'previous_component_sha256': native.canonical_sha(component),
            'native_producer_relabelled': False, 'shipping_allowed': False,
            'behavioral_collision_validated': False, 'physical_timing_validated': False,
            'mapserver': native.MAP_CANDIDATE, 'build_repository_commit': native.MAP_SOURCE,
            'build_run_id': native.MAP_BUILD_RUN, 'build_artifact': native.MAP_BUILD_ARTIFACT,
            **dict.fromkeys(('build_manifest', 'native_fixture', 'paired_preload', 'native_world'), dummy)}
        return component, {'receipt': receipt, 'receipt_sha256': native.canonical_sha(receipt)}

    def test_research_structure_never_grants_runtime_or_shipping_authority(self):
        component, wrapper = self.fixture()
        result = native.inspect_map_research_wrapper(wrapper, component)
        self.assertFalse(result['runtime_admission_granted'])
        self.assertFalse(result['shipping_allowed'])
        self.assertFalse(result['behavioral_collision_validated'])

    def test_old_component_tamper_rejected_even_with_rehashed_wrapper(self):
        component, wrapper = self.fixture()
        wrapper['receipt']['previous_component']['old_producer'] = 37
        wrapper['receipt_sha256'] = native.canonical_sha(wrapper['receipt'])
        with self.assertRaises(ValueError):
            native.inspect_map_research_wrapper(wrapper, component)

    def test_native_producer_and_candidate_changes_rejected(self):
        for key, value in (('mapserver', native.RETAINED_MAP), ('build_repository_commit', 'b'*40),
            ('build_run_id', 1), ('shipping_allowed', True),
            ('behavioral_collision_validated', True), ('physical_timing_validated', True)):
            component, wrapper = self.fixture()
            wrapper['receipt'][key] = value
            wrapper['receipt_sha256'] = native.canonical_sha(wrapper['receipt'])
            with self.subTest(key=key), self.assertRaises(ValueError):
                native.inspect_map_research_wrapper(wrapper, component)

    def test_receipt_digest_and_pin_types_rejected(self):
        component, wrapper = self.fixture()
        wrapper['receipt_sha256'] = 'f'*64
        with self.assertRaises(ValueError):
            native.inspect_map_research_wrapper(wrapper, component)
        for value in ({'bytes': True, 'sha256': 'a'*64}, {'bytes': 1, 'sha256': 'A'*64},
            {'bytes': 0, 'sha256': 'a'*64}, {'bytes': 1, 'sha256': 'a'*64, 'extra': 1}):
            with self.subTest(value=value), self.assertRaises(ValueError): native.pin(value)

    def test_closed_retention_preserves_exact_native_archive_producer(self):
        component, _ = self.fixture()
        archives = {'archives': {'game-package.tar.gz': {'sha256': 'a'*64}}}
        donor = {'map_startup_component': component, 'package_preflight': {'server_archives': archives}}
        result = native.retain_native_component(donor, archives, component)
        self.assertEqual(result['original_component'], component)
        self.assertFalse(result['new_native_consumer_admitted'])
        changed = copy.deepcopy(component)
        changed['files']['MapServer.exe'] = native.MAP_CANDIDATE
        with self.assertRaises(ValueError): native.retain_native_component(donor, archives, changed)


if __name__ == '__main__': unittest.main()
