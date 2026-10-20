"""Focused public-projection/privacy and optional-peer-role admission controls."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import copy
import subprocess
import fragment_interop_emulator_check as driver
from interop_probe_contract import PROBE_KEYS, SPECS, COSTUME_STAGES, REWARD_STAGES, probe_snapshot
from package_check import BUILD_PROFILES, check_build_identity
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
    def test_exact_runtime_revision_requires_bound_unchanged_source_proof(self):
        head, old = 'f' * 40, 'e' * 40
        self.assertEqual(driver.admit_runtime_revision(head, None, None), (head, None))
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'proof.json'
            value=dict(schema='coh-combined-exact-apk-requalification-v1',passed=True,candidate_source_revision=old,qualification_source_revision=head,runtime_and_build_inputs_unchanged=True)
            path.write_text(json.dumps(value))
            self.assertEqual(driver.admit_runtime_revision(head,old,path),(old,driver.sha(path.read_bytes())))
            for key,bad in [('schema','other'),('passed',False),('candidate_source_revision',head),('qualification_source_revision',old),('runtime_and_build_inputs_unchanged',False)]:
                changed=dict(value);changed[key]=bad;path.write_text(json.dumps(changed))
                with self.subTest(key=key),self.assertRaises(ValueError):driver.admit_runtime_revision(head,old,path)
            with self.assertRaises(ValueError):driver.admit_runtime_revision(head,old,None)
            with self.assertRaises(ValueError):driver.admit_runtime_revision(head,None,path)
            with self.assertRaises(ValueError):driver.admit_runtime_revision(head,'not-a-revision',path)

    def test_actual_current_Android_failure_replay_and_exact_probe_extension(self):
        review = json.loads((ROOT / 'native-android/combined-client/diagnostics/memory-candidate-20261019/fragment-driver-schema-failure.json').read_bytes())
        value = review['captured_world_handoff_numeric']
        self.assertIs(driver.current_snapshot(value, True), value)
        self.assertEqual(set(PROBE_KEYS).intersection(value), set(PROBE_KEYS))
        legacy = {k:v for k,v in value.items() if k not in PROBE_KEYS}
        self.assertIs(driver.current_snapshot(legacy), legacy)
        with self.assertRaises(ValueError): driver.current_snapshot(legacy, True)
        for name in PROBE_KEYS:
            changed = copy.deepcopy(value); del changed[name]
            with self.subTest(missing=name), self.assertRaises(ValueError): driver.current_snapshot(changed, True)
        changed = copy.deepcopy(value); changed['first_private_name'] = 'private'
        with self.assertRaises(ValueError): driver.current_snapshot(changed, True)

    def test_all_existing_original_probe_formatters_and_privacy_mutations(self):
        """Execute unchanged C JSON formatters; never execute their packet parsers."""
        definitions = [('first_create', 'create', 'CohInitialCreateProbe'),
            ('first_record_pose', 'pose', 'CohInitialPoseProbe'),
            ('first_record_sequence', 'sequence', 'CohInitialSequenceProbe'),
            ('first_record_triggered_moves', 'triggered', 'CohInitialTriggeredProbe'),
            ('first_record_ai_animation', 'aianim', 'CohInitialAiAnimProbe'),
            ('first_record_netfx', 'netfx', 'CohInitialNetFxProbe'),
            ('first_record_costume_prefix', 'costume', 'CohInitialCostumeProbe'),
            ('first_reward_string', 'reward', 'CohInitialRewardProbe')]
        native = ROOT / 'native-android/engine/initial-capture'
        includes = ''.join('#include "coh_initial_%s_probe.h"\n' % short for _,short,_ in definitions)
        statements = []
        for name, short, ctype in definitions:
            stages = SPECS[name][3] if name in SPECS else COSTUME_STAGES if short == 'costume' else REWARD_STAGES
            statements.append('{%s value={0};for(unsigned i=0;i<%d;i++){value.stage=i;int n=coh_initial_%s_probe_json(&value,json,sizeof(json));if(n<=0||n>=(int)sizeof(json))return 1;printf("%s\\t%%s\\n",json);}}' % (ctype,len(stages),short,name))
        source = '#include <stdio.h>\n' + includes + 'int main(void){char json[2048];' + ''.join(statements) + 'return 0;}\n'
        with tempfile.TemporaryDirectory(prefix='coh-interop-probe-contract-') as tmp:
            root = Path(tmp); harness=root/'formatters.c'; harness.write_text(source); binary=root/'formatters'
            result = subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-ffunction-sections','-fdata-sections','-I',str(native),str(harness),*[str(native/('coh_initial_'+short+'_probe.c')) for _,short,_ in definitions],'-Wl,--gc-sections','-o',str(binary)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            result = subprocess.run([binary],capture_output=True,text=True,check=True)
        present = {}
        for line in result.stdout.splitlines():
            name, raw = line.split('\t'); value=json.loads(raw)
            probe_snapshot(name,value,0)
            if value is not None:
                present[name]=value
                for key in value:
                    if type(value[key]) is int:
                        changed=copy.deepcopy(value);changed[key]=-1
                        with self.subTest(name=name,key=key), self.assertRaises(ValueError): probe_snapshot(name,changed,0)
        self.assertEqual(set(present),set(PROBE_KEYS))
        for name,value in present.items():
            for key,bad in [('account','private'),('world_authority',True),('stage','PRIVATE_STAGE'),('packet_bytes',[1,2,3])]:
                changed=copy.deepcopy(value);changed[key]=bad
                with self.subTest(name=name,key=key), self.assertRaises(ValueError): probe_snapshot(name,changed,0)
        for progress in ([0,6,2,256,256,256,0,1,6],[0,43,256,256,0,0,0xffffffff]):
            value=copy.deepcopy(present['first_reward_string']);value['progress']=progress;probe_snapshot('first_reward_string',value,0)
            value['progress']=progress+[0]
            with self.assertRaises(ValueError): probe_snapshot('first_reward_string',value,0)

    def memory_report(self):
        phases = []
        for i, phase in enumerate(sorted(driver.MEMORY_PHASES)):
            phases.append(dict(phase=phase, requested_elapsed_ms=i, sampled_elapsed_ms=10, sequence=i+1,
                system_sample_valid=False, process_rss_bytes=None, process_pss_bytes=None,
                process_rss_source='unavailable', process_pss_source='unavailable'))
        value = dict(schema='coh-combined-phase-memory-v1', phase_limit=9, sample_interval_ms=1000,
            admission_authority=False, server_policy_thresholds_changed=False, snapshot_elapsed_ms=20,
            latest_sample_elapsed_ms=10, latest_sample_age_ms=10, samples=9, phases=phases, sampler_failures=0,
            owned_guest_process_memory='unavailable', native_owner_memory='unavailable', graphics_memory='unavailable')
        return dict(memory_diagnostics=value, diagnostic_states=dict(catalog='MISSING_CATALOG_GENERATION',
            world_resource='UNRESOLVED_RESOURCE_IDENTITY', character='INCOMPLETE_CHARACTER_DATA',
            world_authority=False, application_ack_permitted=False))

    def test_memory_unknowns_bounds_age_and_authority_controls(self):
        value = self.memory_report()
        self.assertEqual(len(driver.memory_snapshot(value)), 9)
        for key, bad in [('latest_sample_age_ms', 0), ('admission_authority', True),
                         ('phase_limit', 10), ('sampler_failures', -1), ('owned_guest_process_memory', 'zero'), ('extra', 'x' * 24576)]:
            with self.subTest(key=key):
                changed = self.memory_report(); changed['memory_diagnostics'][key] = bad
                with self.assertRaises(ValueError): driver.memory_snapshot(changed)
        for key, bad in [('process_rss_bytes', 0), ('process_pss_source', 'proc_self_status_VmRSS'),
                         ('available_bytes', 0), ('requested_elapsed_ms', 11), ('sequence', 10)]:
            with self.subTest(row=key):
                changed = self.memory_report(); changed['memory_diagnostics']['phases'][0][key] = bad
                with self.assertRaises(ValueError): driver.memory_snapshot(changed)
        value = self.memory_report(); value['memory_diagnostics']['phases'].append(value['memory_diagnostics']['phases'][0])
        with self.assertRaises(ValueError): driver.memory_snapshot(value)
        value = self.memory_report(); value['diagnostic_states']['world_authority'] = True
        with self.assertRaises(ValueError): driver.memory_snapshot(value)

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
        code, name = BUILD_PROFILES['report-diagnostic']
        self.assertIn('versionCode ' + code, source)
        self.assertIn("versionName '" + name + "'", source)
        self.assertIn("storeFile file('../../session-client/app/test-signing/session-test.p12')", source)
        activity = (ROOT / 'native-android/combined-client/app/src/main/java/org/coh/nativecombined/NativeClientActivity.java').read_text()
        self.assertIn('private volatile String interopReport = "{\\"schema\\":\\"coh-native-initial-interop-numeric-v1\\",\\"phase\\":\\"IDLE\\",\\"world_authority\\":false}";', activity)

    def test_explicit_memory_profile_preserves_exact_historical_default(self):
        self.assertEqual(BUILD_PROFILES['original-fragment'], ('10', '0.1.9-gates25-27-test'))
        self.assertEqual(BUILD_PROFILES['memory-diagnostic'], ('11', '0.1.10-memory-diagnostic-test'))
        self.assertEqual(BUILD_PROFILES['report-diagnostic'], ('12', '0.1.11-report-diagnostic-test'))
        self.assertEqual(BUILD_PROFILES['catalog-diagnostic'], ('13', '0.1.12-catalog-diagnostic-test'))
        self.assertEqual(BUILD_PROFILES['entity-diagnostic'], ('15', '0.1.14-entity-diagnostic-test'))
        with self.assertRaises(AssertionError):
            check_build_identity('14', '0.1.13-entity-diagnostic-test', 'entity-diagnostic')
        for profile, identity in BUILD_PROFILES.items():
            check_build_identity(*identity, profile)
            for rejected in (('10', '0.1.10-memory-diagnostic-test'), ('11', '0.1.9-gates25-27-test'), (str(int(identity[0]) + 1), identity[1])):
                with self.subTest(profile=profile, rejected=rejected), self.assertRaises(AssertionError):
                    check_build_identity(*rejected, profile)
        old_code, old_name = BUILD_PROFILES['original-fragment']
        with self.assertRaises(AssertionError):
            check_build_identity(old_code, old_name, 'memory-diagnostic')


if __name__ == '__main__':
    unittest.main()
