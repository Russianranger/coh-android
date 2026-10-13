"""Strict native observation admission tests; fixture rows are not native evidence."""
import copy
from pathlib import Path
import tempfile
import unittest
import qualify_native_startup_profile as profile


def fixture_rows():
    lines=[]
    for phase in ['bin_decode']*12+['sequencer_postprocess','sequencer_finalize','sequencer_total']:
        lines.append('COH_NATIVE_STARTUP_PROFILE_V1 phase='+phase+' input_token=00000001 success=1 clock_valid=1 elapsed_us=10')
    for ordinal in range(1,13):
        lines.append('COH_MAP_BIN_FRESHNESS_V1 ordinal='+str(ordinal)+' input_token=00000001 outcome=freshness_accepted clock_valid=1 '
            'open_us=1 dependencies_us=2 scan_us=3 dates_us=4 membership_us=5 cleanup_us=6')
    return ('\n'.join(lines)+'\n').encode()


class NativeProfileQualificationTests(unittest.TestCase):
    def test_complete_observation_retains_scope_and_phases(self):
        result=profile.parse_observations(fixture_rows())
        self.assertEqual(len(result['profile_rows']),15)
        self.assertEqual(len(result['freshness_rows']),12)
        self.assertFalse(result['freshness_bypass_enabled'])
        self.assertFalse(result['cache_authority_created'])

    def test_missing_decoder_observations_refused(self):
        with self.assertRaisesRegex(ValueError,'decoder'):
            profile.parse_observations(b'\n'.join(l for l in fixture_rows().splitlines() if b'phase=bin_decode' not in l))

    def test_missing_sequencer_phase_refused(self):
        lines=[l for l in fixture_rows().splitlines() if b'phase=sequencer_finalize' not in l]
        with self.assertRaisesRegex(ValueError,'sequencer_finalize'):
            profile.parse_observations(b'\n'.join(lines))

    def test_duplicate_sequencer_phase_refused(self):
        with self.assertRaisesRegex(ValueError,'sequencer_total'):
            profile.parse_observations(fixture_rows()+b'COH_NATIVE_STARTUP_PROFILE_V1 phase=sequencer_total input_token=00000001 success=1 clock_valid=1 elapsed_us=10\n')

    def test_invalid_clock_refused(self):
        with self.assertRaisesRegex(ValueError,'clock'):
            profile.parse_observations(fixture_rows().replace(b'clock_valid=1',b'clock_valid=0',1))

    def test_production_assumed_freshness_is_not_admitted(self):
        with self.assertRaisesRegex(ValueError,'production-mode'):
            profile.parse_observations(fixture_rows().replace(b'outcome=freshness_accepted',b'outcome=production_assumed',1))

    def test_negative_elapsed_refused(self):
        with self.assertRaisesRegex(ValueError,'Malformed'):
            profile.parse_observations(fixture_rows().replace(b'elapsed_us=10',b'elapsed_us=-1',1))

    def test_missing_freshness_refused(self):
        rows=b'\n'.join(l for l in fixture_rows().splitlines() if not l.startswith(b'COH_MAP_BIN'))
        with self.assertRaisesRegex(ValueError,'missing'):
            profile.parse_observations(rows)

    def test_duplicate_field_refused(self):
        with self.assertRaisesRegex(ValueError,'fields'):
            profile.parse_observations(fixture_rows().replace(b'ordinal=1 ',b'ordinal=1 ordinal=1 ',1))

    def test_noncontiguous_ordinals_refused(self):
        with self.assertRaisesRegex(ValueError,'ordinals'):
            profile.parse_observations(fixture_rows().replace(b'ordinal=2 ',b'ordinal=99 ',1))

    def test_uint64_overflow_refused(self):
        with self.assertRaisesRegex(ValueError,'bounds'):
            profile.parse_observations(fixture_rows().replace(b'scan_us=3',b'scan_us=18446744073709551616',1))

    def test_cache_inventory_preserves_bytes_and_refuses_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'data/bin').mkdir(parents=True);(root/'data/server/bin').mkdir(parents=True)
            path=root/'data/bin/sequencers.bin';path.write_bytes(b'exact')
            before=profile.cache_snapshot(root);self.assertEqual(before['data/bin/sequencers.bin']['bytes'],5)
            path.unlink();path.symlink_to(root/'outside')
            with self.assertRaisesRegex(ValueError,'Regular'):
                profile.cache_snapshot(root)

    def test_real_fixture_and_provider_modules_agree_on_original_native(self):
        import prepare_server_fx_control_fixture as fixture
        self.assertEqual(profile.control_native_identity({'mapserver':fixture.MAPSERVER}),fixture.MAPSERVER)
        changed=dict(fixture.MAPSERVER,sha256='0'*64)
        with self.assertRaisesRegex(ValueError,'producer'):
            profile.control_native_identity({'mapserver':changed})


if __name__=='__main__':unittest.main()
