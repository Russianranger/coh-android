"""Execute shipped failure details and distinguish recovered evidence from interruption proof."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_storage_ui import production_method

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
HOST = r'''
import java.util.*;import java.util.concurrent.*;import java.io.*;
class SystemClock {static long uptimeMillis(){return 100;}}
class AtlasAssetImporter {interface Control {boolean requestCancel();}}
class DiagnosticRuntime {boolean requested;void requestStop(){requested=true;}}
class InteractiveRfbClient {boolean fails;int released;void releaseAllInputs()throws IOException{released++;if(fails)throw new IOException("closed display");}}
class JSONArray {
    final List<Object> values = new ArrayList<>();
    int length(){return values.size();}Object opt(int index){return values.get(index);}
}
class JSONObject {
    JSONArray failures;
    final Map<String,Object> fields=new HashMap<>();
    JSONArray optJSONArray(String key){return failures;}
    String optString(String key){Object value=fields.get(key);return value instanceof String?(String)value:"";}
    Object opt(String key){return fields.get(key);}
}
public class ProfileFailurePresentationHost {
    METHODS
    static class Runtime {
        volatile boolean producerCompleted,producerFailed,closingReceiver,cancelled;boolean inputReady=true,finished;
        boolean stop,pendingCancelled;AtlasAssetImporter.Control importControl;DiagnosticRuntime installer;
        void cancelPendingInput(){pendingCancelled=true;}void signalStop(){stop=true;}
        long clientWindowEndedUptime;String session="current",receiverFailure;int releases,notifications,inputFailed;InteractiveRfbClient decoder;
        List<String> lifecycle=new ArrayList<>();
        void recordLifecycle(String value){lifecycle.add(value);}void releaseAllInputs(String selected){need(session.equals(selected));releases++;}void notifyInputState(){notifications++;}
        static String message(Exception e){return e.getClass().getSimpleName();}
        RUNTIME_METHODS
    }
    static void need(boolean value){if(!value)throw new AssertionError();}
    static JSONObject report(Object... failures){JSONObject report=new JSONObject();report.failures=new JSONArray();report.failures.values.addAll(Arrays.asList(failures));return report;}
    public static void main(String[] args){
        switch(args[0]){
        case "actual":
            JSONObject failed=report("No saved THORHERO exists. Use Resume first character creation; all characters are preserved.");
            String before=(String)failed.failures.opt(0);
            need(guestFailureMessage(failed).equals(before));need(failed.failures.opt(0).equals(before));break;
        case "bounded":
            String longMessage=String.join("",Collections.nCopies(2000,"x"));
            need(guestFailureMessage(report(longMessage)).equals(longMessage.substring(0,512)+"…"));break;
        case "sanitize":
            String detail=guestFailureMessage(report("password=private\ntoken: hidden\tsecret=internal\nroot cause\u0000"));
            need(!detail.contains("private")&&!detail.contains("hidden")&&!detail.contains("internal"));
            need(!detail.contains("\n")&&!detail.contains("\t")&&!detail.contains("\u0000"));need(detail.contains("root cause"));break;
        case "missing":need(guestFailureMessage(new JSONObject()).contains("exited"));need(guestFailureMessage(report()).contains("exited"));need(guestFailureMessage(report(" \n\t")).contains("exited"));break;
        case "invalid":need(guestFailureMessage(report(42)).equals("The guest failure report is invalid."));break;
        case "first":need(guestFailureMessage(report("first failure","second failure")).equals("first failure"));break;
        case "terminal":
            JSONObject terminal=report("SQL guard refused an empty reopen");terminal.fields.put("type","result");terminal.fields.put("session_id","current");terminal.fields.put("status","failed");terminal.fields.put("passed",false);
            need(failedGuestResult(terminal,"current"));need(!failedGuestResult(terminal,"previous"));
            terminal.fields.put("passed",true);need(!failedGuestResult(terminal,"current"));terminal.fields.put("passed",false);
            terminal.fields.remove("session_id");need(!failedGuestResult(terminal,"current"));break;
        case "terminal_eof":
            JSONObject completion=report("SQL guard refused an empty reopen");completion.fields.put("type","result");completion.fields.put("session_id","current");completion.fields.put("status","failed");completion.fields.put("passed",false);
            Runtime runtime=new Runtime();runtime.observeFailedGuestResult(completion);runtime.handleReceiverClosure(new EOFException());
            need(runtime.producerCompleted&&!runtime.inputReady&&runtime.releases==1&&runtime.notifications==1&&runtime.receiverFailure==null);need(runtime.lifecycle.contains("guest_failed_result_observed type=result"));
            need(Boolean.FALSE.equals(completion.opt("passed")));break;
        case "failure_signal":
            JSONObject signal=report("SQL eligibility failed");signal.fields.put("type","character_session_failed");signal.fields.put("session_id","current");signal.fields.put("status","failed");signal.fields.put("passed",false);
            Runtime failedSession=new Runtime();failedSession.observeFailedGuestResult(signal);failedSession.handleReceiverClosure(new EOFException());
            need(failedSession.producerFailed&&!failedSession.producerCompleted&&!failedSession.inputReady&&failedSession.receiverFailure==null);
            Runtime stoppable=new Runtime();stoppable.observeFailedGuestResult(signal);need(stoppable.requestStop());need(stoppable.cancelled&&stoppable.stop&&stoppable.pendingCancelled);
            signal.fields.put("type","result");failedSession.observeFailedGuestResult(signal);need(failedSession.producerCompleted);need(!failedSession.requestStop());need(Boolean.FALSE.equals(signal.opt("passed")));break;
        case "failure_release":
            JSONObject knownFailure=report("native guest failed");knownFailure.fields.put("type","character_session_failed");knownFailure.fields.put("session_id","current");knownFailure.fields.put("status","failed");knownFailure.fields.put("passed",false);
            Runtime cleanup=new Runtime();cleanup.decoder=new InteractiveRfbClient();cleanup.decoder.fails=true;cleanup.observeFailedGuestResult(knownFailure);cleanup.releaseOnInputWorker();
            need(cleanup.producerFailed&&!cleanup.producerCompleted&&cleanup.decoder.released==1&&cleanup.inputFailed==0&&cleanup.receiverFailure==null);need(cleanup.requestStop());break;
        case "live_release":
            Runtime live=new Runtime();live.decoder=new InteractiveRfbClient();live.decoder.fails=true;live.releaseOnInputWorker();
            need(!live.producerFailed&&!live.producerCompleted&&live.decoder.released==1&&live.inputFailed==1&&live.receiverFailure.equals("Input release failed")&&!live.inputReady);break;
        case "foreign_signal":
            JSONObject foreign=report("foreign failure");foreign.fields.put("type","character_session_failed");foreign.fields.put("session_id","previous");foreign.fields.put("status","failed");foreign.fields.put("passed",false);
            Runtime unaffected=new Runtime();unaffected.observeFailedGuestResult(foreign);need(!unaffected.producerFailed&&!unaffected.producerCompleted&&unaffected.inputReady);break;
        case "early_eof":
            Runtime premature=new Runtime();premature.handleReceiverClosure(new EOFException());need(!premature.producerCompleted&&premature.receiverFailure.equals("Display socket closed before client observation completed"));break;
        case "attribution":
            JSONObject current=report("SQL guard refused an empty reopen");current.fields.put("session_id","current");current.fields.put("status","failed");current.fields.put("passed",false);current.fields.put("scope","actual_character_reopen_guest");
            need(currentGuestFailureMessage(current,"current").equals("SQL guard refused an empty reopen"));need(currentGuestFailureMessage(current,"previous")==null);
            current.fields.put("scope","previous_guest_outputs");need(currentGuestFailureMessage(current,"current")==null);
            current.fields.put("scope","actual_character_reopen_guest");current.fields.put("passed",true);need(currentGuestFailureMessage(current,"current")==null);break;
        case "recovery":need(reportArchiveLabel("coh-interrupted-guest-1791749675136-abcdef123456.zip").equals("Recovered guest evidence · session unverified"));break;
        case "checkpoint":need(reportArchiveLabel("coh-interrupted-1791749675136-abcdef123456.zip").equals("Recovered / incomplete report"));break;
        case "archive":need(reportArchiveLabel("coh-character-reopen-1791749675136-abcdef123456.zip").equals("Session report · inspect save and gameplay results"));break;
        default:throw new AssertionError();
        }
    }
}
'''


class ProfileFailurePresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(prefix='coh-failure-presentation-')
        cls.addClassCleanup(cls.folder.cleanup)
        cls.path = Path(cls.folder.name)
        runtime = (JAVA / 'ClientRuntime.java').read_text()
        activity = (JAVA / 'ClientActivity.java').read_text()
        methods = '\n'.join((production_method(runtime, 'static boolean failedGuestResult('),
                             production_method(runtime, 'static String currentGuestFailureMessage('),
                             production_method(runtime, 'static String guestFailureMessage('),
                             production_method(runtime, 'private static String clean('),
                             production_method(activity, 'static String reportArchiveLabel(')))
        source = cls.path / 'ProfileFailurePresentationHost.java'
        runtime_methods = '\n'.join((production_method(runtime, 'private void observeFailedGuestResult('),
                                     production_method(runtime, 'private void handleReceiverClosure('),
                                     production_method(runtime, 'public synchronized boolean requestStop('),
                                     production_method(runtime, 'private synchronized void inputFailure('),
                                     production_method(runtime, 'private void releaseOnInputWorker(')))
        source.write_text(HOST.replace('RUNTIME_METHODS', runtime_methods).replace('METHODS', methods))
        subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                        '-d', str(cls.path), str(source)], check=True, capture_output=True, text=True)

    def scenario(self, name):
        subprocess.run(['java', '-cp', str(self.path), 'ProfileFailurePresentationHost', name],
                       check=True, capture_output=True, text=True)

    def test_actual_sql_failure_is_actionable_without_mutating_report(self): self.scenario('actual')
    def test_guest_failure_display_is_bounded(self): self.scenario('bounded')
    def test_failure_detail_redacts_credentials_and_control_characters(self): self.scenario('sanitize')
    def test_absent_or_empty_failure_gets_honest_incomplete_message(self): self.scenario('missing')
    def test_malformed_failure_gets_no_synthetic_pass(self): self.scenario('invalid')
    def test_first_failure_stays_primary(self): self.scenario('first')
    def test_failure_terminal_stops_input_only_for_current_strictly_failed_session(self): self.scenario('terminal')
    def test_failed_terminal_then_eof_preserves_primary_failure_and_disables_input(self): self.scenario('terminal_eof')
    def test_early_failure_signal_then_eof_then_terminal_retains_failed_status(self): self.scenario('failure_signal')
    def test_release_during_known_failure_cleanup_does_not_abort_original_failure_report(self): self.scenario('failure_release')
    def test_release_failure_in_live_session_remains_transport_failure(self): self.scenario('live_release')
    def test_foreign_failure_signal_cannot_close_current_input(self): self.scenario('foreign_signal')
    def test_early_eof_without_terminal_remains_a_display_failure(self): self.scenario('early_eof')
    def test_primary_failure_attribution_requires_current_guest_session_and_failed_status(self): self.scenario('attribution')
    def test_previous_guest_archive_does_not_claim_android_interruption(self): self.scenario('recovery')
    def test_checkpoint_archive_remains_incomplete(self): self.scenario('checkpoint')
    def test_archive_completion_is_not_labeled_passed(self): self.scenario('archive')

    def test_detail_is_used_only_for_current_failed_guest_with_verified_cleanup(self):
        runtime = (JAVA / 'ClientRuntime.java').read_text()
        method = production_method(runtime, 'private Result runCharacter(')
        self.assertIn('if (launched && processExit != 0 && !cancelled)', method)
        self.assertLess(method.index('if (!cleanup)'), method.index('String guestFailure = currentGuestFailureMessage(report, session);'))
        self.assertIn('(error == null ? "" : error + " ")', method)
        self.assertIn('passed = guestPassed && cleanup && !cancelled', method)
        self.assertIn('error == null || error.startsWith("Local display connection failed:")', method)
        capture = production_method(runtime, 'private void captureOutput(')
        self.assertIn('observeFailedGuestResult(event);', capture)
        terminal = production_method(runtime, 'private void observeFailedGuestResult(')
        self.assertIn('if (failedGuestResult(event, session))', terminal)
        self.assertIn('producerFailed = true;', terminal)
        self.assertIn('if ("result".equals(event.optString("type"))) producerCompleted = true;', terminal)
        stop = production_method(runtime, 'public synchronized boolean requestStop(')
        self.assertIn('if (finished || producerCompleted) return false;', stop)
        self.assertNotIn('producerFailed', stop)


if __name__ == '__main__':
    unittest.main()
