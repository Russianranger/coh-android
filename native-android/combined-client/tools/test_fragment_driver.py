"""Focused public-projection/privacy and optional-peer-role admission controls."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import fragment_interop_emulator_check as driver
from fragment_fixture import produce

ROOT = Path(__file__).resolve().parents[3]


def sample():
    value = json.loads((ROOT / 'native-android/combined-client/diagnostics/gates25-27-thor-20261018/thor-20261018-user-report-review.json').read_bytes())['world_handoff']
    receive = dict.fromkeys(driver.COUNTERS + driver.GAUGES, 0)
    receive.update(dict.fromkeys(driver.REFUSED_AUTHORITY, False))
    receive.update(schema='coh-initial-receive-counters-v1', diagnostic_only=True, valid=True, refusal='NONE', observation_retired=True, cleanup_transport_counters_equal=True, sample_count=2,
                   udp_datagrams_received=value['map_protocol']['udp']['datagrams_received'], link_received=value['map_protocol']['udp']['link']['received'])
    value['receive_diagnostics'] = receive
    return value


class FragmentDriver(unittest.TestCase):
    def test_retained_physical_projection_with_explicit_new_numeric_extension(self):
        value = sample()
        self.assertIs(driver.current_snapshot(value), value)

    def test_privacy_authority_bounds_and_producer_mismatch_refuse(self):
        cases = [({}, 'account', 'private'), ({}, 'world_authority', True),
                 ({'receive': True}, 'packet_bytes', 'private'), ({'receive': True}, 'world_authority', True),
                 ({'receive': True}, 'source_generation_admitted', True), ({'receive': True}, 'link_received', True),
                 ({'receive': True}, 'udp_datagrams_received', 999), ({'receive': True}, 'rx_pending', 17),
                 ({'receive': True}, 'fragment_groups', 5), ({'receive': True}, 'decode_compressed_bytes', 16385),
                 ({'receive': True}, 'decode_output_budget', 4194305), ({'receive': True}, 'sample_count', 1000001),
                 ({'receive': True}, 'refusal', 'PRIVATE_ERROR_TEXT')]
        for where, key, changed in cases:
            with self.subTest(key=key, changed=changed):
                value = sample()
                target = value['receive_diagnostics'] if where else value
                target[key] = changed
                with self.assertRaises(ValueError):
                    driver.current_snapshot(value)
        value = sample()
        del value['receive_diagnostics']
        with self.assertRaises(ValueError):
            driver.current_snapshot(value)

    def test_new_streaming_fixtures_are_repeatable_and_hit_both_original_forms(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            a, b = produce(first), produce(second)
            self.assertEqual(a, b)
            self.assertEqual((Path(first) / 'fragment-fixtures.h').read_bytes(), (Path(second) / 'fragment-fixtures.h').read_bytes())
        single, multi = a['cases']['fragment-single'], a['cases']['fragment-multi']
        self.assertEqual((single['compressed_bytes'], single['sibling_count']), (1200, 1))
        self.assertEqual(multi['sibling_count'], 6)
        self.assertTrue(multi['part_zero_sent_last'])
        self.assertFalse(a['whole_original_allents_producer'])
        self.assertFalse(a['world_authority'])

    def test_new_peer_role_reverses_to_unchanged_historical_peer(self):
        source = (ROOT / 'native-android/engine/initial-capture/test_initial_peer.c').read_text()
        while '#ifdef COH_INITIAL_FRAGMENT_PEER\n' in source:
            at = source.index('#ifdef COH_INITIAL_FRAGMENT_PEER\n')
            # All optional insertions are deliberately unnested. Preserve the
            # indentation that belonged to the historical following directive.
            start = at - 1 if at and source[at - 1] == ' ' else at
            end = source.index('#endif\n', at) + len('#endif\n')
            source = source[:start] + source[end:]
        self.assertEqual(hashlib.sha256(source.encode()).hexdigest(), 'e5d91921f6ba9547680e0551be91fe63b6de69474fcebb1d9257bdaa84d8a512')

    def test_exact_upgrade_identity_source(self):
        source = (ROOT / 'native-android/combined-client/app/build.gradle').read_text()
        self.assertIn("applicationId 'org.coh.nativecombined'", source)
        self.assertIn('versionCode 10', source)
        self.assertIn("versionName '0.1.9-gates25-27-test'", source)
        self.assertIn("storeFile file('../../session-client/app/test-signing/session-test.p12')", source)
        activity = (ROOT / 'native-android/combined-client/app/src/main/java/org/coh/nativecombined/NativeClientActivity.java').read_text()
        self.assertIn('private volatile String interopReport = "{\\"schema\\":\\"coh-native-initial-interop-numeric-v1\\",\\"phase\\":\\"IDLE\\",\\"world_authority\\":false}";', activity)


if __name__ == '__main__':
    unittest.main()
