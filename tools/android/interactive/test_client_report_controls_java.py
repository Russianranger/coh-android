"""Execute diagnostic UI admission after a failed session without relaxing cleanup."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_storage_ui import production_method

ROOT = Path(__file__).resolve().parents[3]
ACTIVITY = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientActivity.java'


class ReportControlsJava(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='coh-report-controls-')
        source = ACTIVITY.read_text()
        methods = '\n'.join(production_method(source, signature) for signature in
            ('static boolean diagnosticControlsReady(', 'static String reportArchiveLabel('))
        host = '''
class ClientService { static class State { boolean busy,storageBusy,reportExporting,blocked; } }
public class ReportControlsHost {
METHODS
static void need(boolean value){if(!value)throw new AssertionError();}
public static void main(String[] args){
 ClientService.State state=new ClientService.State();
 switch(args[0]){
 case "failed": state.blocked=true;need(diagnosticControlsReady(state,true,false,false));break;
 case "ownership":
  need(!diagnosticControlsReady(state,true,false,true));
  state.blocked=true;need(!diagnosticControlsReady(state,true,false,true));break;
 case "busy":
  state.busy=true;need(!diagnosticControlsReady(state,true,false,false));state.busy=false;
  state.storageBusy=true;need(!diagnosticControlsReady(state,true,false,false));state.storageBusy=false;
  state.reportExporting=true;need(!diagnosticControlsReady(state,true,false,false));break;
 case "unavailable":
  need(!diagnosticControlsReady(null,true,false,false));
  need(!diagnosticControlsReady(state,false,false,false));
  need(!diagnosticControlsReady(state,true,true,false));break;
 case "labels":
  need(reportArchiveLabel("coh-character-reopen-1-abc.zip").contains("inspect save"));
  need(reportArchiveLabel("coh-report-failure-1-abc.zip").contains("finalization failed"));
  need(reportArchiveLabel("coh-interrupted-guest-1-abc.zip").contains("unverified"));
  need(reportArchiveLabel("coh-interrupted-1-abc.zip").contains("incomplete"));break;
 default:throw new AssertionError();
 }
}
}
'''.replace('METHODS', methods)
        path = Path(cls.directory.name) / 'ReportControlsHost.java'
        path.write_text(host)
        subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                        '-encoding', 'UTF-8', '-d', cls.directory.name, str(path)],
                       check=True, capture_output=True, text=True, timeout=30)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def scenario(self, name):
        subprocess.run(['java', '-cp', self.directory.name, 'ReportControlsHost', name],
                       check=True, capture_output=True, text=True, timeout=15)

    def test_failed_session_still_offers_diagnostics(self): self.scenario('failed')
    def test_live_operation_still_excludes_diagnostic_file_work(self): self.scenario('ownership')
    def test_busy_import_storage_and_export_still_exclude_file_work(self): self.scenario('busy')
    def test_missing_service_state_and_open_picker_are_not_admitted(self): self.scenario('unavailable')
    def test_report_labels_do_not_claim_gameplay_completion(self): self.scenario('labels')


if __name__ == '__main__':
    unittest.main()
