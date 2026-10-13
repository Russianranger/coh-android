"""Negative/parity gates for the isolated NONSHIPPING metadata prototype."""
import copy
import json
from pathlib import Path
import random
import tempfile
import unittest
import native_client_metadata_parity as fixture


class MetadataParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='coh-provider-parity-')
        cls.native = fixture.NativeFixture(cls.temporary.name)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.identity = fixture.fixture_identity()
        self.rows = [fixture.row('fx/Test.fx'),
                     fixture.row('FX/test.FX', provider=-1, index=4),
                     fixture.row('fx/test.fx', provider=-2, index=7),
                     fixture.row('fx/test.fx', provider=1),
                     fixture.row('fx/optional.fx', timestamp=0),
                     fixture.row('fx/empty', size=0, is_dir=1)]
        self.manifest = fixture.make_manifest(self.rows, self.identity, self.native)

    def qualify(self, manifest=None, rows=None, identity=None):
        return fixture.qualify(manifest or self.manifest, rows or self.rows,
                               identity or self.identity, self.native)

    def test_actual_native_pig_winner_preserves_case_and_loose_presence(self):
        self.assertEqual(self.qualify()['status'], 'passed')
        winner = next(x for x in self.manifest['effective'] if x['path'] == 'fx/Test.fx')
        self.assertEqual((winner['provider'], winner['file_index'], winner['seen_in_fs']), (-2, 7, 1))
        self.assertFalse(self.manifest['production_acceptance_allowed'])

    def test_directional_pig_DST_rule_is_not_symmetric_freshness_tolerance(self):
        for offset, expected in [(3600, -1), (-3600, 0), (3601, 0), (0, -1)]:
            with self.subTest(offset=offset):
                rows = [fixture.row('fx/a.fx'), fixture.row('fx/a.fx',
                    timestamp=1767225600+offset, provider=-1, index=1)]
                manifest = fixture.make_manifest(rows, self.identity, self.native)
                leaf = manifest['effective'][-1]
                self.assertEqual(leaf['provider'], expected)
                self.qualify(manifest, rows)

    def test_pig_winner_retains_existing_loose_attributes_as_stock_loader_does(self):
        rows = [fixture.row('fx/a.fx', attributes=7),
                fixture.row('fx/a.fx', provider=-1, index=1, attributes=0)]
        manifest = fixture.make_manifest(rows, self.identity, self.native)
        self.assertEqual(manifest['effective'][-1]['attributes'], 7)
        self.qualify(manifest, rows)

    def test_randomized_ordered_provider_replay_equals_hydrated_metadata(self):
        rng = random.Random(36013)
        for sequence in range(80):
            rows = []
            for event in range(64):
                provider = rng.choice([-2, -1, 0, 1])
                rows.append(fixture.row('fx/' + rng.choice(['d0', 'D0', 'd1']) + '/' +
                    rng.choice(['A', 'a', 'b', 'c']) + '.fx', provider=provider,
                    index=rng.randrange(10) if provider < 0 else -1,
                    timestamp=1767225600+rng.choice([0, 1, 3600, -3600]),
                    size=rng.randrange(1000), attributes=rng.randrange(8)))
            manifest = fixture.make_manifest(rows, self.identity, self.native)
            self.assertEqual(self.qualify(manifest, rows)['status'], 'passed', sequence)

    def test_provider_order_generation_mode_consumer_and_ownership_changes_refused(self):
        for name in ('roots', 'pigs', 'generation', 'consumer', 'ownership', 'ignore_policy', 'mode'):
            with self.subTest(name=name):
                changed = copy.deepcopy(self.identity)
                changed[name] = changed[name][::-1] if isinstance(changed[name], list) else changed[name] + '-changed'
                with self.assertRaises(ValueError): self.qualify(identity=changed)

    def test_unknown_or_incomplete_provider_authority_refused(self):
        for field in ('complete_namespace', 'immutable'):
            changed = copy.deepcopy(self.identity)
            changed[field] = False
            with self.assertRaises(ValueError): self.qualify(identity=changed)
        changed = copy.deepcopy(self.rows)
        changed[0]['provider'] = 10
        with self.assertRaises(ValueError): self.qualify(rows=changed)

    def test_optional_absence_addition_deletion_and_same_size_date_change_refused(self):
        modifications = [self.rows + [fixture.row('fx/v_Test.fx')], self.rows[:-1],
                         list(reversed(self.rows))]
        changed = copy.deepcopy(self.rows)
        changed[0]['timestamp'] += 1
        modifications.append(changed)
        for changed in modifications:
            with self.subTest(changed=changed):
                with self.assertRaisesRegex(ValueError, 'membership/metadata/order'):
                    self.qualify(rows=changed)

    def test_effective_tampering_and_recomputed_payload_hash_refused(self):
        changed = copy.deepcopy(self.manifest)
        changed['effective'][-1]['timestamp'] += 1
        with self.assertRaisesRegex(ValueError, 'payload changed'): self.qualify(changed)
        changed['effective_sha256'] = fixture.digest(fixture.canonical(changed['effective']))
        with self.assertRaisesRegex(ValueError, 'provider closure'): self.qualify(changed)

    def test_native_source_and_schema_change_refused(self):
        changed = copy.deepcopy(self.manifest)
        changed['native_source_contract']['FolderNodeAdd'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'native source'): self.qualify(changed)
        changed = copy.deepcopy(self.manifest)
        changed['format'] += '-changed'
        with self.assertRaisesRegex(ValueError, 'nonshipping'): self.qualify(changed)

    def test_unsafe_paths_and_native_bounds_refused(self):
        for field, value in [('path', '../fx/x.fx'), ('path', 'C:/x.fx'), ('path', 'fx//x.fx'),
                             ('path', 'fx/\tx.fx'), ('path', 'fx/é.fx'), ('path', 'x'*260),
                             ('timestamp', 2147483648), ('bytes', -1), ('seen_in_fs', 2),
                             ('attributes', 8), ('file_index', 3)]:
            with self.subTest(field=field, value=value):
                changed = copy.deepcopy(self.rows)
                changed[0][field] = value
                with self.assertRaises(ValueError): self.qualify(rows=changed)
        changed = copy.deepcopy(self.rows)
        changed[1]['file_index'] = 2147483648
        with self.assertRaisesRegex(ValueError, 'provider file index'): self.qualify(rows=changed)

    def test_algorithm_parity_does_not_authenticate_in_place_source_content(self):
        # Demonstrate the precise residual authority gap, not a falsely passing
        # source-integrity test: FolderCache metadata cannot detect these bytes.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.fx'
            path.write_bytes(b'AAAA')
            old = fixture.digest(path.read_bytes())
            path.write_bytes(b'BBBB')
            self.assertNotEqual(old, fixture.digest(path.read_bytes()))
            self.assertEqual(self.qualify()['status'], 'passed')
            self.assertFalse(self.qualify()['production_acceptance_allowed'])

    def test_manifest_roundtrip_retains_empty_dirs_zero_dates_and_flags(self):
        recovered = json.loads(json.dumps(self.manifest))
        self.assertEqual(self.qualify(recovered)['status'], 'passed')
        self.assertTrue(any(x['is_dir'] and x['path'] == 'fx/empty' for x in recovered['effective']))
        self.assertEqual(next(x for x in recovered['effective'] if x['path'] == 'fx/optional.fx')['timestamp'], 0)


if __name__ == '__main__': unittest.main(verbosity=2)
