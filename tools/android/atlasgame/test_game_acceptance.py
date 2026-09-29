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
        boolean actual=args.length>2&&args[2].equals("cleanup")?AtlasGameAcceptance.cleanupSafe(value.get("report")):
            AtlasGameAcceptance.accepts(value.get("report"),(String)value.get("runtime"),value.get("import"));
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
                        '-d', str(cls.directory), str(SOURCE), str(harness)], check=True)
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

    def execute(self, accepted=False, mode='acceptance'):
        fixture = self.directory / 'input.json'
        fixture.write_text(json.dumps({'report': self.report, 'runtime': self.baseline['inputs']['runtime_manifest_sha256'],
                                       'import': self.imported}))
        result = subprocess.run(['java', '-cp', str(self.directory), CLASS, str(fixture), str(accepted).lower(), mode],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_complete_accepted_sequence_is_required(self):
        self.execute(True)

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
