"""Essential source-framing projection controls; no runtime owner is admitted."""
import copy
import unittest
from report_diagnostic_contract import separate_catalog_boundary


class CatalogBoundaryTests(unittest.TestCase):
    def sample(self):
        return {'schema': 'coh-native-initial-interop-numeric-v1',
                'phase': 'INITIAL_OBSERVED', 'raw_allents_observed': True,
                'catalog_boundary': [2, 41, 3, 1, 2424, 3416, 262144]}

    def test_exact_default_and_explicit(self):
        for stage, metadata in [(41, 262144), (43, (5 << 26) | (28 << 21) | (1 << 18)),
                                (43, (1 << 26) | (2 << 21))]:
            value = self.sample()
            value['catalog_boundary'][1] = stage
            value['catalog_boundary'][6] = metadata
            self.assertNotIn('catalog_boundary', separate_catalog_boundary(value))
            self.assertEqual(value['catalog_boundary'][1], stage)

    def test_absent_null_and_retained_partial(self):
        for value in ({}, {'catalog_boundary': None}):
            self.assertNotIn('catalog_boundary', separate_catalog_boundary(value))
        for phase in ('REPORT_LIMIT', 'REPORT_UNAVAILABLE'):
            value = self.sample()
            value['phase'] = phase
            del value['raw_allents_observed']
            separate_catalog_boundary(value)

    def test_numeric_and_shape_refusals(self):
        original = self.sample()
        for bad in (True, 41.0, '41', None, -1, 2**63):
            for index in range(7):
                with self.subTest(bad=bad, index=index):
                    value = copy.deepcopy(original)
                    value['catalog_boundary'][index] = bad
                    with self.assertRaises(ValueError):
                        separate_catalog_boundary(value)
        for bad in ([], [2, 41], 'DEFAULT_CATALOG_REQUIRED', {}, original['catalog_boundary'] + [0]):
            value = copy.deepcopy(original)
            value['catalog_boundary'] = bad
            with self.assertRaises(ValueError):
                separate_catalog_boundary(value)

    def test_prefix_framing_overflow_and_observation_refusals(self):
        for index, bad in [(0, 1), (1, 40), (1, 42), (2, 257), (3, 257),
                           (4, 33554433), (4, 33554432), (5, 3271),
                           (6, 1 << 29), (6, (1 << 18) | (1 << 21)),
                           (6, (1 << 18) | (1 << 26))]:
            value = self.sample()
            value['catalog_boundary'][index] = bad
            with self.assertRaises(ValueError):
                separate_catalog_boundary(value)
        for key, bad in [('schema', 'wrong'), ('raw_allents_observed', False),
                         ('raw_allents_observed', None), ('raw_allents_observed', 1)]:
            value = self.sample()
            value[key] = bad
            with self.assertRaises(ValueError):
                separate_catalog_boundary(value)

    def test_optional_progress_agrees_when_present(self):
        value = self.sample()
        value['first_reward_string'] = {'progress': value['catalog_boundary'].copy()}
        separate_catalog_boundary(value)
        value['first_reward_string']['progress'][1] = 43
        with self.assertRaises(ValueError):
            separate_catalog_boundary(value)

    def test_explicit_requires_separate_count_framing(self):
        for metadata in (0, 1 << 18, (5 << 26), (1 << 26) | (1 << 18),
                         (2 << 26) | (31 << 21), (6 << 26), (3 << 26), (4 << 26),
                         (2 << 26) | (14 << 21), (1 << 26) | (15 << 21)):
            value = self.sample()
            value['catalog_boundary'][1] = 43
            value['catalog_boundary'][6] = metadata
            with self.assertRaises(ValueError):
                separate_catalog_boundary(value)


if __name__ == '__main__':
    unittest.main()
