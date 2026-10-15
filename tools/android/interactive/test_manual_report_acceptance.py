"""Replay exact .36 manual report through the production Java acceptance gate.

The private import receipt read is a controlled host adapter. All consumed report,
Android event and APK-pin fields come from the named physical outer ZIP projection.
This test does not retroactively confer a device or overall session pass.
"""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import test_client_gpu_repair_evidence as previous

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
FIXTURE = json.loads((Path(__file__).parent/'fixtures/thor-manual-report-0.13.36-20261013.json').read_text())
MAIN = r''' @SuppressWarnings("unchecked") public static void main(String[] args)throws Exception {
  JSONObject fixture=FIXTURE_VALUE,report=fixture.getJSONObject("guest"),a=fixture.getJSONObject("android");
  Runtime owner=new Runtime();owner.session=a.getString("session_id");owner.gpuProfileRequested="turnip";
  owner.sessionBudget=new ClientSessionBudget(true);
  owner.observedClientPid=report.getJSONObject("client_launch").optLong("pid",-1);
  JSONObject pinned=fixture.getJSONObject("current_apk_files"),runtimePins=new JSONObject(),clientPins=new JSONObject();
  for(String name:pinned.keySet()) {
   runtimePins.put(name,pinned.get(name));clientPins.put(name,pinned.get(name));
  }
  JSONArray processes=new JSONArray();for(Object code:report.getJSONArray("process_exit_codes"))processes.add(obj("exit_code",code,"input_closed",true,"output_capture_closed",true));
  report.put("processes",processes);report.remove("process_exit_codes");
  owner.manifest=obj("startup_only_reopen",false,"character_zoning_enabled",true,"character_monorail_enabled",true,
   "client_gpu_profile",obj("format",1),"files",runtimePins);
  owner.clientManifest=obj("files",clientPins);
  owner.characterConnectedEvent=a.getJSONObject("character_connected_event");owner.characterSavedEvent=a.getJSONObject("character_saved_event");
  owner.startedUptime=a.optLong("started_uptime_ms",-1);
  owner.clientWindowObservedUptime=a.optLong("client_window_observed_uptime_ms",-1);
  owner.clientWindowEndedUptime=a.optLong("client_window_ended_uptime_ms",-1);
  owner.launcherBudgetStartedUptime=fixture.optLong("launcher_started_uptime_ms",-1);
  for(Object event:a.getJSONArray("session_budget_events")) {
   Map<String,Object> row=(Map<String,Object>)event;long generated=((Number)row.get("generated_utc_ms")).longValue();
   require(owner.sessionBudget.apply(row,owner.session,owner.observedClientPid,true,false,0,generated,
    owner.clientWindowObservedUptime,owner.startedUptime+5400000,true,1),"physical accepted manual budget");
   owner.sessionBudgetEvents.add(row);
  }
  JSONObject identity=report.getJSONObject("import_identity");owner.imported.generation=identity.getString("generation");
  owner.imported.count=identity.optLong("file_count",-1);owner.imported.bytes=identity.optLong("total_bytes",-1);
  JSONObject inputs=report.getJSONArray("stages").getJSONObject(0);
  owner.imported.sourceCommit=inputs.getString("source_commit");owner.imported.dataCommit=inputs.getString("data_commit");
  owner.receipt=("contract.sha256="+identity.getString("contract_sha256")+"\n").getBytes(StandardCharsets.UTF_8);
  identity.put("receipt_sha256",owner.hex(MessageDigest.getInstance("SHA-256").digest(owner.receipt)));
  JSONObject stage=report.getJSONArray("stages").getJSONObject(report.getJSONArray("stages").length()-1);
  String mode=args[0];
  if(mode.equals("physical")){
   require(Boolean.FALSE.equals(stage.opt("bounded_live_observation")),"manual source flag remains honest");
   require(Boolean.TRUE.equals(stage.opt("user_controlled_observation")),"manual source policy");
  }
  if(mode.equals("legacy_gate")){System.out.print(Boolean.TRUE.equals(stage.opt("bounded_live_observation")));return;}
  if(mode.equals("bounded_flag"))stage.put("bounded_live_observation",true);
  if(mode.equals("missing_policy"))stage.remove("user_controlled_observation");
  if(mode.equals("policy_false"))stage.put("user_controlled_observation",false);
  if(mode.equals("not_manual"))report.put("manual_session",false);
  if(mode.equals("unapproved"))owner.sessionBudgetEvents.clear();
  if(mode.equals("timed_policy"))owner.sessionBudget=new ClientSessionBudget(false);
  if(mode.equals("guest_timeout"))report.put("interaction_completion_reason","interaction_timeout");
  if(mode.equals("foreign_session"))report.put("session_id","00000000000000000000000000000000");
  if(mode.equals("foreign_budget_pid"))report.getJSONArray("character_session_budgets").getJSONObject(0).put("client_pid",625);
  if(mode.equals("nonzero_budget"))report.getJSONArray("character_session_budgets").getJSONObject(0).put("deadline_utc_ms",1);
  if(mode.equals("overrun"))report.put("observation_seconds",6000);
  if(mode.equals("missing_stage"))report.getJSONArray("stages").remove(10);
  if(mode.equals("lost_powers"))report.getJSONObject("character_reopen").put("powers_preserved",false);
  if(mode.equals("unsafe_cleanup"))report.getJSONObject("wine_process_cleanup").put("inspection_failures",1);
  if(mode.equals("foreign_hash"))report.getJSONObject("asset_sha256").put("local_character_server.py",String.join("",Collections.nCopies(64,"e")));
  System.out.print(owner.guestAccepted(report));
 }
}
'''

class ManualReportAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source=(JAVA/'ClientRuntime.java').read_text()
        methods='\n'.join(previous.method(source, signature) for signature in (
            'private boolean gpuProfileReportMatches(', 'private boolean zoningEnabled(', 'private boolean guestAccepted('))
        cls.temp=tempfile.TemporaryDirectory(prefix='coh-manual-report-')
        harness=Path(cls.temp.name)/'GPURepairEvidenceHost.java'
        prefix=previous.HARNESS.split(' @SuppressWarnings("unchecked") public static void main')[0]
        harness.write_text((prefix+MAIN).replace('METHODS',methods).replace('FIXTURE_VALUE',previous.java_value(FIXTURE)))
        result=subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','--release','8','-d',cls.temp.name,
            str(JAVA/'ClientAcceptance.java'),str(JAVA/'ClientSessionBudget.java'),str(harness)],capture_output=True,text=True,timeout=60)
        if result.returncode:raise AssertionError(result.stderr)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def execute(self,mode,accepted=False):
        run=subprocess.run(['java','-cp',self.temp.name,'io.github.russianranger.cohclientinteractive.GPURepairEvidenceHost',mode],
            check=True,capture_output=True,text=True,timeout=20)
        self.assertEqual(run.stdout,str(accepted).lower(),mode)

    def test_exact_current_manual_report_passes_production_guest_gate(self):
        self.assertEqual(FIXTURE['app_version'],'0.13.36')
        self.execute('physical',True)

    def test_old_gate_reproduces_false_incomplete_label(self):self.execute('legacy_gate')

    def test_manual_policy_requires_explicit_honest_flags_and_local_approval(self):
        for mode in ['bounded_flag','missing_policy','policy_false','not_manual','unapproved','timed_policy','guest_timeout']:
            with self.subTest(mode=mode):self.execute(mode)

    def test_current_session_budget_and_window_still_required(self):
        for mode in ['foreign_session','foreign_budget_pid','nonzero_budget','overrun']:
            with self.subTest(mode=mode):self.execute(mode)

    def test_preservation_cleanup_source_pins_and_complete_assets_still_required(self):
        for mode in ['missing_stage','lost_powers','unsafe_cleanup','foreign_hash']:
            with self.subTest(mode=mode):self.execute(mode)

if __name__=='__main__':unittest.main()
