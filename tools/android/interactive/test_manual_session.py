"""Execute manual session/capture policies; these fixtures do not claim device gameplay."""
import copy
import math
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT/'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
sys.path[:0] = [str(ROOT/'android/guest'), str(Path(__file__).parent)]
import character_reopen_diagnostic as reopen
import character_session_budget as budget
import character_zoning as zoning
import local_character_server as character
import test_guest as interactive_fixture
import test_client_gameplay_performance_contract as gameplay_fixture
from test_session_budget_guest import proof, SESSION, PID, UTC_START
from test_client_sidebar_runtime import method


class ManualSessionGuestTests(unittest.TestCase):
    def test_manual_budget_keeps_identity_and_zero_deadline_after_days_of_idle(self):
        policy = budget.SessionBudget(SESSION, PID, 0, math.inf, manual=True, supported_maps=(1, 5, 101))
        row = dict(proof(), map_id=5, zoning_enabled=True, monorail_enabled=True, connected_on_supported_map=True)
        event = policy.connected(row, 86400, UTC_START+86400000)
        self.assertTrue(event['manual_session'])
        self.assertEqual(event['map_id'], 5)
        self.assertTrue(math.isinf(policy.deadline))
        for name in ('deadline_utc_ms', 'movement_deadline_utc_ms', 'save_request_deadline_utc_ms'):
            self.assertEqual(event[name], 0)
        self.assertIsNone(policy.connected(row, 86401, UTC_START+86401000))
        self.assertEqual(len(policy.events), 1)

    def test_manual_policy_cannot_bypass_identity_map_or_native_connection(self):
        row = dict(proof(), map_id=5, zoning_enabled=True, monorail_enabled=True, connected_on_supported_map=True)
        for key, value in [('session_id', 'f'*32), ('client_pid', PID+1), ('map_id', 6),
                           ('name', 'OTHER'), ('native_client_ready_observed', False), ('monorail_enabled', False)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                policy = budget.SessionBudget(SESSION, PID, 0, math.inf, manual=True, supported_maps=(1, 5, 101))
                policy.connected(dict(row, **{key:value}), 86400, UTC_START+86400000)

    def test_shipping_reopen_uses_manual_launcher_and_scoped_budget(self):
        diagnostic = reopen.ZoningCharacterReopenDiagnostic.__new__(reopen.ZoningCharacterReopenDiagnostic)
        diagnostic.args = SimpleNamespace(session_id=SESSION, wine='/wine', assets=Path('/assets'))
        diagnostic.work = Path('/work')
        self.assertEqual(diagnostic.launcher_command()[-1], '--character-manual')
        diagnostic.ctx = SimpleNamespace(deadline=math.inf, report={'character_reopen': dict(proof(),
            map_id=5, zoning_enabled=True, monorail_enabled=True, connected_on_supported_map=True)}, event=Mock())
        diagnostic.connected_announced = True
        diagnostic.presentation_ready_monotonic = 0
        diagnostic.launcher_started_monotonic = 0
        with patch.object(reopen.time,'monotonic',return_value=86400), patch.object(reopen.time,'time',return_value=UTC_START/1000+86400):
            self.assertTrue(math.isinf(diagnostic.interaction_deadline(math.inf, {'pid':PID})))
        event = diagnostic.ctx.report['character_session_budgets'][0]
        self.assertEqual(event['deadline_utc_ms'], 0)
        self.assertEqual(event['map_id'], 5)

    def test_zoning_has_no_remaining_playtime_admission_gate(self):
        for now in (0, 86400, 604800):
            window = zoning.travel_window(math.inf, now, UTC_START+int(now*1000), 720, manual=True)
            self.assertEqual(window['departure_deadline_utc_ms'], 0)
            self.assertEqual(window['session_deadline_utc_ms'], 0)
            self.assertEqual(window['transfer_budget_seconds'], zoning.TRANSFER_SECONDS)
            self.assertTrue(window['manual_session'])
            self.assertFalse(window['session_budget_extended'])
        with self.assertRaises(Exception): zoning.travel_window(math.inf, 1, UTC_START, 720)

    def connection_wait(self):
        server = character.LocalCharacterReopenServer.__new__(character.LocalCharacterReopenServer)
        server.owner = SimpleNamespace(MANUAL_SESSION=True)
        server.ctx = SimpleNamespace(report={})
        server.creation_report = {'verified':False, 'connected_on_atlas':False,
            'existing_character_verified':True, 'baseline':{'character_id':1,'auth_id':44}}
        server.auth_id=44;server.character_next=0;server.query_count=160
        server.health=Mock();server.sample_progress=Mock(return_value={});server.live_progress=Mock(return_value=True)
        server.native_ready_record=Mock(return_value=None);server.inventory=Mock(side_effect=RuntimeError('full SQL proof'))
        return server

    def test_idle_character_selection_does_not_exhaust_protocol_query_budget(self):
        server = self.connection_wait()
        for tick in range(200):
            with patch.object(character.time,'monotonic',return_value=tick*60):
                self.assertIsNone(server.character_evidence())
        server.inventory.assert_not_called();self.assertEqual(server.query_count,160)
        self.assertFalse(server.creation_report['connected_on_atlas'])
        self.assertEqual(server.creation_report['character_id'],1)
        self.assertEqual(server.ctx.report['character_observer_metrics']['manual_login_wait']['translated_status_probes_skipped'],200)

    def test_native_ready_still_requires_full_sql_protocol_connection_proof(self):
        server=self.connection_wait();server.native_ready_record.return_value={'native':'ready'}
        with self.assertRaisesRegex(RuntimeError,'full SQL proof'):server.character_evidence()
        self.assertFalse(server.creation_report['connected_on_atlas'])
        server.inventory.assert_called_once()

    def test_idle_connection_wait_rejects_foreign_saved_account(self):
        server=self.connection_wait();server.auth_id=45
        with self.assertRaisesRegex(Exception,'saved character identity'):server.character_evidence()
        server.native_ready_record.assert_not_called();server.inventory.assert_not_called()

    def fixture(self):
        fixture = interactive_fixture.InteractionTests()
        fixture.setUp(); self.addCleanup(fixture.doCleanups)
        fixture.d.MANUAL_SESSION = True
        return fixture

    def test_manual_launcher_preserves_qualified_performance_and_standard_settings(self):
        fixture=gameplay_fixture.ClientGameplayLaunchTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        diagnostic=fixture.diagnostic
        command=diagnostic.launcher_command()
        diagnostic.launcher_command=lambda:command[:-1]+['--character-manual']
        for profile,cap in [('performance','30'),('standard','10')]:
            diagnostic.wine_env['COH_CLIENT_GRAPHICS_PROFILE']=profile
            baseline=dict(diagnostic.wine_env)
            for label in ('actual-coh-client','actual-coh-client-retry'):
                diagnostic.launch_client_attempt(label=label)
                environment=diagnostic.ctx.start.call_args.kwargs['env']
                self.assertEqual(environment['COH_CLIENT_GAMEPLAY_FPS'],cap)
                self.assertEqual(environment['COH_CLIENT_BOUNDED_TEXTURE_ERRORS'],'1')
                self.assertEqual(environment['COH_CLIENT_SCENE_PROFILE'],'1')
                self.assertEqual(diagnostic.wine_env,baseline)

    def test_manual_finish_has_no_minimum_observation_wait(self):
        fixture = self.fixture(); fixture.finish_when_ready(); fixture.d.execute()
        self.assertEqual(fixture.elapsed, 0)
        self.assertEqual(fixture.d.ctx.report['interaction_completion_reason'], 'finish_requested')
        self.assertTrue(fixture.d.ctx.report['manual_session'])
        self.assertEqual(fixture.d.ctx.report['interaction_timeout_seconds'], 0)
        self.assertEqual(fixture.d.ctx.report['minimum_observation_seconds'], 0)
        self.assertFalse(fixture.d.ctx.passed.call_args.kwargs['bounded_live_observation'])
        self.assertTrue(fixture.d.ctx.passed.call_args.kwargs['user_controlled_observation'])

    def test_login_can_idle_past_all_previous_caps_until_user_finishes(self):
        fixture = self.fixture()
        def check():
            if fixture.d.ctx.report.get('manual_session'):
                fixture.elapsed = max(fixture.elapsed, 86400)
                fixture.d.finish_path.write_text(__import__('json').dumps(interactive_fixture.request()))
        fixture.d.ctx.check.side_effect = check
        fixture.d.execute()
        self.assertEqual(fixture.elapsed, 86400)
        self.assertEqual(fixture.d.ctx.report['interaction_completion_reason'], 'finish_requested')
        self.assertTrue(math.isinf(fixture.d.ctx.deadline))

    def test_input_and_manual_lifetime_wait_for_world_dependency(self):
        fixture = self.fixture(); fixture.finish_when_ready()
        fixture.d.interaction_dependencies_ready = lambda: fixture.elapsed >= 15
        fixture.d.execute()
        ready = [event for event in fixture.events if event[1] == 'client_interaction_ready']
        self.assertEqual(ready[0][0], 15)
        self.assertEqual(fixture.elapsed, 15)
        self.assertTrue(fixture.d.ctx.report['manual_session'])

    def test_map_join_does_not_shorten_its_independent_readiness_deadline(self):
        fixture=self.fixture();fixture.finish_when_ready()
        fixture.d.interaction_dependencies_ready=lambda: fixture.elapsed >= 1200
        fixture.d.execute()
        self.assertEqual(fixture.elapsed,1200)
        self.assertEqual(fixture.d.ctx.report['startup_elapsed_seconds'],0)
        self.assertEqual(fixture.d.ctx.report['startup_dependencies_join_elapsed_seconds'],1200)
        self.assertEqual([event[0] for event in fixture.events if event[1]=='client_interaction_ready'],[1200])
        registry_calls=[call for call in fixture.d.ctx.run.call_args_list if call.args[0]=='client-progress-registry']
        self.assertEqual(len(registry_calls),2)  # Initial independent proof and fresh final proof.

    def test_manual_mode_still_bounds_stalled_native_startup(self):
        fixture = self.fixture(); fixture.output = fixture.output.replace('Loaded all data!', 'Loading data')
        with self.assertRaisesRegex(Exception, 'startup exceeded'):
            fixture.d.execute()
        self.assertEqual(fixture.elapsed, 900)
        self.assertNotIn('manual_session', fixture.d.ctx.report)

    def test_manual_mode_still_rejects_lost_current_window(self):
        fixture = self.fixture(); original = fixture.observer.windows.return_value
        fixture.observer.windows.side_effect = lambda: original if fixture.elapsed < 5 else []
        with self.assertRaisesRegex(Exception, 'disappeared'): fixture.d.execute()
        self.assertFalse(fixture.d.startup_complete)

    def test_manual_finish_still_bounds_unusable_final_capture(self):
        fixture = self.fixture(); fixture.finish_when_ready(); fixture.blank_until = 1000
        with self.assertRaisesRegex(Exception, 'remained blank.*deadline'): fixture.d.execute()
        self.assertEqual(fixture.elapsed, 30)
        self.assertEqual(fixture.d.ctx.report['final_frame_settling']['status'], 'failed')


JAVA_HOST = r'''
package io.github.russianranger.cohclientinteractive;
import java.util.*;
class SystemClock {static long now=100;static long uptimeMillis(){return now;}}
public final class ManualSessionHost {
 static final String SESSION="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
 static final long WALL=1790000000000L;
 static void need(boolean b){if(!b)throw new AssertionError();}
 static Map<String,Object> event(){
  Map<String,Object> e=new LinkedHashMap<>();
  e.put("type","character_session_budget");e.put("format",1);e.put("session_id",SESSION);e.put("client_pid",44);
  e.put("character_id",1);e.put("name","THORHERO");e.put("account","COHLOCAL");e.put("map_id",5);
  e.put("zoning_enabled",true);e.put("monorail_enabled",true);e.put("native_client_ready_observed",true);
  e.put("reopen_verified",true);e.put("manual_session",true);e.put("revision",1);e.put("phase","connected");
  e.put("generated_utc_ms",WALL);e.put("deadline_utc_ms",0);e.put("movement_deadline_utc_ms",0);e.put("save_request_deadline_utc_ms",0);
  return e;
 }
 static boolean apply(ClientSessionBudget b,Map<String,Object> e){return b.apply(e,SESSION,44,true,false,0,WALL,86400000,10,true,5);}
 static void budget(String mode){
  ClientSessionBudget b=new ClientSessionBudget(true);Map<String,Object> e=event();
  if(mode.equals("identity")){e.put("client_pid",45);need(!apply(b,e));need(b.revision()==0);return;}
  if(mode.equals("deadline")){e.put("deadline_utc_ms",WALL+1000);need(!apply(b,e));return;}
  if(mode.equals("legacy")){need(!apply(new ClientSessionBudget(),e));return;}
  need(apply(b,e));need(b.deadline()==0&&b.saveDeadline()==0&&b.movementDeadline()==0);
  need(b.canMove(604800000)&&b.canSave(604800000));need(!apply(b,e));
  List<Object> accepted=Arrays.<Object>asList(e);Map<String,Object> report=new LinkedHashMap<>();
  report.put("manual_session",true);report.put("observation_seconds",86400L);report.put("interaction_timeout_seconds",0);
  report.put("interaction_completion_reason","finish_requested");report.put("character_session_budgets",Arrays.<Object>asList(new LinkedHashMap<>(e)));
  if(mode.equals("forged"))report.put("character_session_budgets",Collections.emptyList());
  if(mode.equals("auto"))report.put("interaction_completion_reason","interaction_timeout");
  if(mode.equals("short"))report.put("observation_seconds",0L);
  boolean ok=ClientAcceptance.clientObservationAccepted(report,accepted,SESSION,44,100,86400100,0,50,0,true);
  need(ok==(!mode.equals("forged")&&!mode.equals("auto")));
 }
 static class Event extends HashMap<String,Object>{int optInt(String n,int d){Object v=get(n);return v instanceof Integer?(Integer)v:d;}}
 static class Zoning {String phase="idle";int currentMap(){return 5;}String phase(){return phase;}}
 static class Capture {boolean active;boolean pending(long n){return active;}}
 boolean reopen=true,inputReady=true,saveLogoutRequested,finished,finishRequested,cancelled,producerCompleted,manualTestActive,manualTestOpeningCaptured;
 long manualTestStartedUptime,manualTestFrameWatermark,manualTestCapturesAccepted;
 String session=SESSION;long observedClientPid=44,inputSent,decodedFrames;
 Event characterConnectedEvent=new Event();Zoning zoning=new Zoning();
 List<Map<String,Object>> manualTestEvents=new ArrayList<>();
 List<Object> surfaceSamples=new ArrayList<>(),loginSamples=new ArrayList<>(),connectedSamples=new ArrayList<>(),relocationSamples=new ArrayList<>(),characterSamples=new ArrayList<>();
 long clientWindowObservedUptime=0,clientWindowEndedUptime=-1,loginObservedUptime=-1,connectedObservedUptime=-1,relocatedObservedUptime=-1,characterObservedUptime=-1;
 Capture contactCapture=new Capture(),taskAcceptedCapture=new Capture(),taskCompletedCapture=new Capture();
 int checkpoints;boolean zoningEnabled(){return true;}
 void stage(String a,String b){} void notifyInputState(){} void recordLifecycle(String s){} void checkpoint(){checkpoints++;}
 METHODS
 static void fill(List<Object> x){while(x.size()<3)x.add(1);}
 void capture(String mode){
  need(needsSurfaceCapture());fill(surfaceSamples);need(!needsSurfaceCapture());
  need(startManualTest());need(!startManualTest());need(needsSurfaceCapture());
  need(!manualCaptureEligible(99,1));need(!manualCaptureEligible(100,0));need(manualCaptureEligible(101,1));
  SystemClock.now=86400000;need(manualTestActive());
  if(mode.equals("save"))need(stopManualTest("save_logout"));else need(stopManualTest());
  need(!manualTestActive()&&!needsSurfaceCapture());need(!stopManualTest());
  need(manualTestEvents.size()==2&&checkpoints==2);
  need(manualTestEvents.get(0).get("action").equals("start"));need(manualTestEvents.get(1).get("action").equals("stop"));
  need(manualTestEvents.get(1).get("uptime_ms").equals(86400000L));need(manualTestEvents.get(0).get("map_id").equals(5));
  if(mode.equals("required")){
   characterObservedUptime=86400000;need(needsSurfaceCapture());fill(characterSamples);need(!needsSurfaceCapture());
   zoning.phase="capturing";need(needsSurfaceCapture());zoning.phase="idle";
   contactCapture.active=true;need(needsSurfaceCapture());contactCapture.active=false;need(!needsSurfaceCapture());
  }
  if(mode.equals("repeat")){
   manualTestOpeningCaptured=true;decodedFrames=300;need(startManualTest());need(!manualTestOpeningCaptured);
   need(!manualCaptureEligible(101,500));need(!manualCaptureEligible(86400001,299));need(manualCaptureEligible(86400001,301));
   need(stopManualTest());need(manualTestEvents.size()==4);need(manualTestEvents.get(2).get("test_id").equals(2));
   need(manualTestEvents.get(3).get("captures_accepted").equals(0L));
  }
  if(mode.equals("capacity")){for(int i=0;i<31;i++){need(startManualTest());need(stopManualTest());}need(!canStartManualTest());need(manualTestEvents.size()==64);}
  if(mode.equals("unowned")){characterConnectedEvent=null;need(!canStartManualTest());cancelled=true;need(!needsSurfaceCapture());}
 }
 public static void main(String[] args){if(args[0].startsWith("capture_"))new ManualSessionHost().capture(args[0].substring(8));else budget(args[0]);}
}
'''


class ManualSessionJavaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (JAVA/'ClientRuntime.java').read_text()
        signatures = ('public synchronized boolean manualTestActive(', 'public synchronized boolean canStartManualTest(',
            'public synchronized boolean startManualTest(', 'public synchronized boolean stopManualTest(',
            'private synchronized boolean stopManualTest(', 'private boolean manualCaptureEligible(', 'private void recordManualTest(', 'public synchronized boolean needsSurfaceCapture(')
        methods = '\n'.join(method(source, signature) for signature in signatures)
        cls.temp = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.temp.cleanup)
        path = Path(cls.temp.name)/'ManualSessionHost.java';path.write_text(JAVA_HOST.replace(' METHODS',methods))
        result = subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','--release','8','-d',cls.temp.name,
            str(JAVA/'ClientSessionBudget.java'),str(JAVA/'ClientAcceptance.java'),str(path)],capture_output=True,text=True,timeout=60)
        if result.returncode: raise AssertionError(result.stderr)

    def check(self, mode):
        result=subprocess.run(['java','-cp',self.temp.name,'io.github.russianranger.cohclientinteractive.ManualSessionHost',mode],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_owned_manual_budget_has_no_day_or_week_expiry(self): self.check('long')
    def test_manual_budget_rejects_foreign_pid(self): self.check('identity')
    def test_manual_budget_rejects_nonzero_deadlines(self): self.check('deadline')
    def test_legacy_validator_cannot_accept_untimed_policy(self): self.check('legacy')
    def test_manual_finish_accepts_short_truthful_observation(self): self.check('short')
    def test_manual_report_cannot_forge_accepted_budget(self): self.check('forged')
    def test_manual_report_cannot_claim_automatic_timeout_success(self): self.check('auto')
    def test_capture_start_stop_records_owned_times_without_expiry(self): self.check('capture_normal')
    def test_save_stops_optional_capture_and_keeps_reason(self): self.check('capture_save')
    def test_required_save_zoning_contact_views_remain_available(self): self.check('capture_required')
    def test_repeat_stationary_test_requires_its_own_fresh_frame(self): self.check('capture_repeat')
    def test_capture_history_is_bounded_without_time_limits(self): self.check('capture_capacity')
    def test_unowned_or_cancelled_session_cannot_start_capture(self): self.check('capture_unowned')


if __name__ == '__main__': unittest.main()
