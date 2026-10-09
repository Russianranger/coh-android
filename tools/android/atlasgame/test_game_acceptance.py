"""Execute the Android acceptance gate against the accepted full Atlas report and mutations."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'android/atlasgame/src/main/java/io/github/russianranger/cohdiagnostic/AtlasGameAcceptance.java'
CLASS = 'io.github.russianranger.cohdiagnostic.AtlasGameAcceptanceHost'
HARNESS = r'''
package io.github.russianranger.cohdiagnostic;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
public final class AtlasGameAcceptanceHost {
    static final class Json {
        final String source; int at;
        Json(String source){this.source=source;}
        void space(){while(at<source.length()&&Character.isWhitespace(source.charAt(at)))at++;}
        Object value(){space();char c=source.charAt(at);
            if(c=='{'){at++;Map<String,Object> result=new LinkedHashMap<>();space();
                if(source.charAt(at)=='}'){at++;return result;}
                do{space();String key=string();space();if(source.charAt(at++)!=':')throw new Error();
                    result.put(key,value());space();c=source.charAt(at++);
                }while(c==',');if(c!='}')throw new Error();return result;}
            if(c=='['){at++;List<Object> result=new ArrayList<>();space();
                if(source.charAt(at)==']'){at++;return result;}
                do{result.add(value());space();c=source.charAt(at++);}while(c==',');
                if(c!=']')throw new Error();return result;}
            if(c=='"')return string();
            for(String word:new String[]{"true","false","null"})if(source.startsWith(word,at)){
                at+=word.length();return word.equals("null")?null:Boolean.valueOf(word);}
            int start=at;while(at<source.length()&&"-+0123456789.eE".indexOf(source.charAt(at))>=0)at++;
            if(start==at)throw new Error();return Double.valueOf(source.substring(start,at));
        }
        String string(){if(source.charAt(at++)!='"')throw new Error();StringBuilder out=new StringBuilder();
            while(true){char c=source.charAt(at++);if(c=='"')return out.toString();if(c=='\\'){
                c=source.charAt(at++);switch(c){case 'u':c=(char)Integer.parseInt(source.substring(at,at+4),16);at+=4;break;
                case 'n':c='\n';break;case 'r':c='\r';break;case 't':c='\t';break;case 'b':c='\b';break;case 'f':c='\f';break;}
            }out.append(c);}
        }
    }
    public static void main(String[] args)throws Exception{
        Map<?,?> value=(Map<?,?>)new Json(new String(Files.readAllBytes(Paths.get(args[0])),StandardCharsets.UTF_8)).value();
        if(args.length>2&&args[2].equals("capture")) {
            Map<?,?> capture=(Map<?,?>)value.get("report");boolean valid;
            try {valid=AtlasGameCapturePolicy.captureLimit((String)capture.get("group"),(String)capture.get("name"))==((Number)capture.get("limit")).longValue();}
            catch(java.io.IOException invalid){valid=false;}
            if(valid!=Boolean.parseBoolean(args[1]))throw new AssertionError("Capture acceptance was "+valid);
            return;
        }
        boolean actual=args.length>2&&args[2].equals("cleanup")?AtlasGameAcceptance.cleanupSafe(value.get("report")):
            AtlasGameAcceptance.accepts(value.get("report"),(String)value.get("runtime"),value.get("import"),value.get("bundle"));
        if(actual!=Boolean.parseBoolean(args[1]))throw new AssertionError("Acceptance was "+actual);
    }
}
'''


class GameAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='coh-atlas-acceptance-')
        cls.directory = Path(cls.temporary.name)
        harness = cls.directory / 'AtlasGameAcceptanceHost.java'
        harness.write_text(HARNESS)
        subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                        '-d', str(cls.directory), str(SOURCE), str(SOURCE.with_name('AtlasMapProgressAcceptance.java')),
                        str(SOURCE.with_name('AtlasGameCapturePolicy.java')), str(harness)], check=True)
        cls.baseline = json.loads((ROOT / 'docs/android-evidence/game-listeners-arm64-36510836956.json').read_text())
        cls.baseline['execution_platform_requested'] = 'android'
        cls.baseline['listener_policy'] = 'device'
        cls.imported = {'generation': 'generation-' + 'a' * 32, 'contract_sha256': 'b' * 64,
                        'receipt_sha256': 'c' * 64, 'file_count': 173011, 'total_bytes': 2977730517}
        cls.baseline['imported_content'] = {**cls.imported, 'private_copy_verified': True,
                                           'source_generation_unchanged': True}
        cls.baseline['cleanup_execution'] = {'diagnostic_initialized': True, 'wine_started': True, 'postgres_started': True,
                                             'owned_child_count': len(cls.baseline['processes'])}

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.report = copy.deepcopy(self.baseline)
        self.runtime = self.baseline['inputs']['runtime_manifest_sha256']
        self.bundle = {'format': 1, 'package_run_id': 36510836956,
                       'package_repository_commit': 'ac4c1f7978be444a893f65f5177641191861d42f',
                       'package_manifest_sha256': 'ebfdbbab3984627f7c39220f42a9c3e67b78ffe555aa742621a7a1450731fb2a'}

    def progress_fixture(self):
        # Only the game evidence below is the qualified donor report. Android import
        # context and the new device startup guard are explicit local test fixtures.
        self.report = json.loads((ROOT / 'docs/android-evidence/mapserver-progress-arm64-36630872719.json').read_text())
        self.report.update(execution_platform_requested='android', listener_policy='device',
                           imported_content=copy.deepcopy(self.baseline['imported_content']))
        self.runtime = self.report['inputs']['runtime_manifest_sha256']
        progress = self.report['game']['mapserver_progress']
        self.bundle = {'format': 1, 'package_run_id': 36630872719,
                       'package_repository_commit': '003b07bcd98cb100c1505c15670c07d11a240c8f',
                       'package_manifest_sha256': 'ef1e5b1aa7cad69f2e25d286cc579531c86417d3f7f1a5de86843a350f4024cd',
                       'mapserver_progress_profile': 'dispatch_progress_v1',
                       'mapserver_progress_producer': copy.deepcopy(progress['producer'])}
        guards = {}
        for index, label in enumerate(('first', 'restart')):
            samples = [sample for sample in progress['phases'][label]['samples']
                       if sample['available'] and sample['tick_completed'] > 0]
            samples[0]['reason'] = 'startup-tick-before:' + label + '-ready'
            samples[1]['reason'] = 'startup-tick-after:' + label + '-ready'
            before, after = copy.deepcopy(samples[0]), copy.deepcopy(samples[1])
            protocol = self.report['game']['phases'][index]['map']
            protocol['monotonic'] = (before['observed_monotonic'] + after['observed_monotonic']) / 2
            guards[label] = {'attempts': 1, 'status': 'passed', 'before': before, 'after': after,
                             'protocol': copy.deepcopy(protocol)}
        self.report['game']['mapserver_startup'] = {'profile': 'dispatch_progress_v1',
            'requires_completed_tick_before_protocol': True, 'phases': guards}

    def execute(self, accepted=False, mode='acceptance'):
        fixture = self.directory / 'input.json'
        fixture.write_text(json.dumps({'report': self.report, 'runtime': self.runtime, 'bundle': self.bundle,
                                       'import': self.imported}))
        result = subprocess.run(['java', '-cp', str(self.directory), CLASS, str(fixture), str(accepted).lower(), mode],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_complete_accepted_sequence_is_required(self):
        self.execute(True)

    def test_qualified_progress_sequence_requires_its_explicit_selection(self):
        self.progress_fixture()
        self.execute(True)
        del self.bundle['mapserver_progress_profile']
        self.execute()

    def test_selected_package_and_producer_pins_cannot_be_relabelled(self):
        for group, key, value in (
                ('bundle', 'package_repository_commit', 'a' * 40),
                ('bundle', 'package_manifest_sha256', 'a' * 64),
                ('bundle', 'package_run_id', 36510836956),
                ('bundle', 'mapserver_progress_profile', 'unknown'),
                ('producer', 'repository_commit', 'a' * 40),
                ('producer', 'manifest_sha256', 'a' * 64),
                ('producer', 'mapserver_sha256', 'a' * 64),
                ('inputs', 'repository_commit', 'a' * 40),
                ('inputs', 'game_package_sha256', 'a' * 64)):
            with self.subTest(group=group, key=key):
                self.progress_fixture()
                target = {'bundle': self.bundle, 'producer': self.bundle['mapserver_progress_producer'],
                          'inputs': self.report['inputs']}[group]
                target[key] = value
                self.execute()
        self.progress_fixture()
        self.report['game']['mapserver_progress']['producer']['mapserver_sha256'] = 'a' * 64
        self.execute()

    def test_progress_cannot_replace_original_readiness_observation_or_stages(self):
        for mutation in ('network', 'stats', 'duration', 'stage'):
            with self.subTest(mutation=mutation):
                self.progress_fixture()
                if mutation in ('network', 'stats'):
                    self.report['game']['phases'][0]['map'][mutation + '_age_seconds'] = 21
                    self.report['game']['mapserver_startup']['phases']['first']['protocol'][mutation + '_age_seconds'] = 21
                elif mutation == 'duration':
                    self.report['game']['atlas_observation']['seconds'] = 29
                else:
                    self.report['stages'].pop()
                self.execute()

    def test_progress_requires_raw_bytes_digest_and_matching_decoded_fields(self):
        for field, value in (('raw_record_hex', '00' * 128), ('raw_record_sha256', 'a' * 64),
                             ('tick_completed', 999999), ('stage', 'UNREVIEWED'), ('is_success_proof', True)):
            with self.subTest(field=field):
                self.progress_fixture()
                sample = next(item for item in self.report['game']['mapserver_progress']['phases']['first']['samples']
                              if item['available'])
                sample[field] = value
                self.execute()

    def test_both_progress_histories_and_bounded_capture_are_required(self):
        for mutation in ('phase', 'capture', 'oversize', 'stalled'):
            with self.subTest(mutation=mutation):
                self.progress_fixture()
                if mutation == 'phase':
                    del self.report['game']['mapserver_progress']['phases']['restart']
                elif mutation == 'capture':
                    del self.report['game']['capture_files']['mapserver-progress.json']
                elif mutation == 'oversize':
                    self.report['game']['capture_files']['mapserver-progress.json']['bytes'] = 512 * 1024 + 1
                else:
                    phase = self.report['game']['mapserver_progress']['phases']['restart']
                    phase['samples'] = phase['samples'][:1]
                    phase.update(sample_count=1, dropped_samples=0)
                self.execute()

    def test_startup_guard_requires_raw_completed_ticks_identity_and_enclosed_protocol(self):
        for mutation in ('missing', 'waiting', 'raw', 'identity', 'clock', 'protocol'):
            with self.subTest(mutation=mutation):
                self.progress_fixture()
                guard = self.report['game']['mapserver_startup']['phases']['restart']
                if mutation == 'missing':
                    del self.report['game']['mapserver_startup']
                elif mutation == 'waiting':
                    guard['status'] = 'waiting'
                elif mutation == 'raw':
                    guard['before']['raw_record_sha256'] = 'a' * 64
                elif mutation == 'identity':
                    guard['after']['file_identity']['inode'] += 1
                elif mutation == 'clock':
                    guard['after']['observed_monotonic'] = guard['before']['observed_monotonic'] - 1
                else:
                    guard['protocol']['monotonic'] += 1
                self.execute()

    def test_startup_witness_must_match_its_retained_ordinal(self):
        for mutation in ('timestamp', 'zero', 'fractional', 'future', 'same', 'reason', 'history_gap'):
            with self.subTest(mutation=mutation):
                self.progress_fixture()
                phase = self.report['game']['mapserver_progress']['phases']['restart']
                guard = self.report['game']['mapserver_startup']['phases']['restart']
                before = guard['before']
                if mutation == 'timestamp':
                    before['observed_monotonic'] += .01
                    if before['freshness'] != 'unchanged':
                        before['last_advance_monotonic'] = before['observed_monotonic']
                    before['unchanged_seconds'] = round(before['observed_monotonic'] - before['last_advance_monotonic'], 3)
                elif mutation == 'zero':
                    before['sample_number'] = 0
                elif mutation == 'fractional':
                    before['sample_number'] += .5
                elif mutation == 'future':
                    before['sample_number'] = phase['sample_count'] + 1
                elif mutation == 'same':
                    guard['after']['sample_number'] = before['sample_number']
                elif mutation == 'reason':
                    before['reason'] = 'startup-tick-before:first-ready'
                else:
                    phase['samples'][0]['sample_number'] += 1
                self.execute()

    def evicted_startup_fixture(self):
        self.progress_fixture()
        label = 'restart'
        phase = self.report['game']['mapserver_progress']['phases'][label]
        guard = self.report['game']['mapserver_startup']['phases'][label]
        first = next(sample for sample in phase['samples'] if sample['available'])

        def sample(template, ordinal, last_advance, freshness, reason):
            value = copy.deepcopy(template)
            observed = phase['launch_monotonic'] + ordinal
            value.update(sample_number=ordinal, observed_monotonic=observed, reason=reason,
                         last_advance_monotonic=phase['launch_monotonic'] + last_advance,
                         unchanged_seconds=round(ordinal - last_advance, 3), freshness=freshness)
            return value

        # Local fixture: 240 samples retain the first 16 and last 112. The
        # independently decoded startup samples 18/19 fall in the evicted middle.
        before = sample(guard['before'], 18, 18, 'advanced', 'startup-tick-before:restart-ready')
        after = sample(guard['after'], 19, 19, 'advanced', 'startup-tick-after:restart-ready')
        retained = [sample(first, n, 1, 'initial' if n == 1 else 'unchanged', 'local-fixture') for n in range(1, 17)]
        retained += [sample(after, n, 19, 'unchanged', 'local-fixture') for n in range(129, 241)]
        phase.update(samples=retained, sample_count=240, dropped_samples=112)
        protocol = self.report['game']['phases'][1]['map']
        protocol['monotonic'] = phase['launch_monotonic'] + 18.5
        guard.update(before=before, after=after, protocol=copy.deepcopy(protocol))

    def test_startup_witness_can_only_be_detached_by_the_actual_retention_policy(self):
        self.evicted_startup_fixture()
        self.execute(True)
        for ordinal in (16, 129):
            with self.subTest(protected_ordinal=ordinal):
                self.evicted_startup_fixture()
                guard = self.report['game']['mapserver_startup']['phases']['restart']
                guard['before' if ordinal == 16 else 'after']['sample_number'] = ordinal
                self.execute()
        self.evicted_startup_fixture()
        phase = self.report['game']['mapserver_progress']['phases']['restart']
        phase['samples'][15]['sample_number'] = 17
        self.execute()

    def test_exact_progress_capture_allowlist_preserves_existing_limits(self):
        for group, name, limit, accepted in (
                ('game-captures', 'mapserver-progress.json', 512 * 1024, True),
                ('game-captures', 'first-ready.json', 16384, True),
                ('game-captures', 'restart-snapshot.json', 1024 * 1024, True),
                ('game-service-captures', 'first-atlas-stdout.txt', 6 * 1024 * 1024, True),
                ('game-captures', '../mapserver-progress.json', 512 * 1024, False),
                ('game-captures', 'other-mapserver-progress.json', 512 * 1024, False),
                ('game-service-captures', 'mapserver-progress.json', 512 * 1024, False),
                ('game-hang-captures', 'mapserver-progress.json', 512 * 1024, False)):
            with self.subTest(group=group, name=name):
                self.report = {'group': group, 'name': name, 'limit': limit}
                self.execute(accepted, 'capture')

    def test_optional_crash_listener_may_be_absent(self):
        for phase in self.report['game']['phases']:
            phase['loopback_only']['endpoints'] = [item for item in phase['loopback_only']['endpoints'] if item['port'] != 6992]
        self.execute(True)

    def test_required_launcher_listener_missing(self):
        self.report['game']['phases'][1]['loopback_only']['endpoints'] = [item for item in self.report['game']['phases'][1]['loopback_only']['endpoints'] if item['port'] != 6998]
        self.execute()

    def test_stale_success_from_other_import_cannot_pass(self):
        self.report['imported_content']['receipt_sha256'] = 'd' * 64
        self.execute()

    def test_different_runtime_cannot_pass(self):
        self.report['inputs']['runtime_manifest_sha256'] = 'd' * 64
        self.execute()

    def test_guest_host_execution_cannot_pass_as_android(self):
        self.report['execution_platform_requested'] = 'host'
        self.execute()

    def test_wrong_restart_identity_is_rejected(self):
        self.report['game']['resume']['database_id'] += 1
        self.execute()

    def test_save_without_committed_sql_is_rejected(self):
        self.report['game']['second_save']['independent_committed_sql'] = False
        self.execute()

    def test_gameplay_claim_is_rejected(self):
        self.report['gameplay_validated'] = True
        self.execute()

    def test_missing_capture_and_nonlocal_listener_are_rejected(self):
        del self.report['game']['capture_files']['restart-snapshot.json']
        self.execute()
        self.report = copy.deepcopy(self.baseline)
        self.report['game']['sessions']['second']['game_listeners']['endpoints'][0]['address'] = '0.0.0.0'
        self.execute()

    def test_incomplete_cleanup_cannot_pass(self):
        self.report['wine_process_cleanup']['remaining'] = 1
        self.execute()

    def test_cancelled_pass_flag_is_rejected(self):
        self.report['status'] = 'cancelled'
        self.execute()

    def test_cleanup_requires_owned_wine_and_closed_process_records(self):
        self.execute(True, 'cleanup')
        self.report['wine_process_cleanup']['remaining'] = 1
        self.execute(False, 'cleanup')

    def test_stop_during_private_copy_does_not_require_a_never_started_wine_owner(self):
        self.report['processes'] = []
        self.report['cleanup_execution'] = {'diagnostic_initialized': True, 'wine_started': False, 'postgres_started': False, 'owned_child_count': 0}
        self.report['cleanup'].update(postgres_graceful=False, wine_prefix_stopped=False)
        del self.report['wine_process_cleanup']
        self.execute(True, 'cleanup')

    def test_preflight_stop_with_no_children_is_safe_but_missing_or_contradictory_evidence_is_not(self):
        self.report['processes'] = []
        self.report['cleanup_execution'] = {'diagnostic_initialized': False, 'wine_started': False, 'postgres_started': False, 'owned_child_count': 0}
        self.report['cleanup'] = dict.fromkeys(self.report['cleanup'], False)
        self.execute(True, 'cleanup')
        self.report['cleanup_execution']['owned_child_count'] = 1
        self.execute(False, 'cleanup')
        del self.report['cleanup_execution']
        self.execute(False, 'cleanup')


if __name__ == '__main__':
    unittest.main()
