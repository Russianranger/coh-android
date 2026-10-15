"""Execute the shipped finite zoning state and input transport under replay/race failures."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT/'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
ZONING_JAVA = ROOT/'android/zoning/src/main/java/io/github/russianranger/cohclientinteractive/ClientZoning.java'
HARNESS = r'''
package io.github.russianranger.cohclientinteractive;
import java.util.*;
import java.io.*;
import java.lang.reflect.*;
public final class ZoningHost {
 static final String SESSION="0123456789abcdef0123456789abcdef";
 static void need(boolean value){if(!value)throw new AssertionError();}
 static Map<String,Object> event(String status,int epoch,int map,int target,long now){
  Map<String,Object> e=new LinkedHashMap<>();e.put("type","character_zoning");e.put("format",1);
  e.put("session_id",SESSION);e.put("client_pid",73);e.put("character_id",1);e.put("epoch",epoch);
  e.put("current_map_id",map);e.put("target_map_id",target);e.put("status",status);e.put("generated_utc_ms",now);
  e.put("current_map_verified",true);e.put("zoning_enabled",true);e.put("destination_ready",true);
  e.put("arrival_native_verified",true);e.put("mapserver_pid",99);e.put("elapsed_ms",20);
  e.put("character_identity_preserved",true);e.put("exact_destination_endpoint_verified",true);
  return e;
 }
 static boolean accept(ClientZoning z,Map<String,Object> e,long now,long up,long seq){return z.accept(e,SESSION,73,1,now,up,seq);}
 static ClientZoning enabled(){ClientZoning z=new ClientZoning();need(accept(z,event("enabled",0,1,101,1000),1000,10,1));return z;}
 static ClientZoning ready(){ClientZoning z=enabled();need(z.prepare(1100));need(accept(z,event("ready",1,1,101,1200),1200,20,2));return z;}
 static ClientZoning transferring(){ClientZoning z=ready();need(z.beginTravel());need(z.delivered(1300));return z;}
 static void roundtrip(){
  ClientZoning z=enabled();need(z.canPrepare()&&!z.blocksInput());
  need(!accept(z,event("enabled",0,1,101,1000),1000,10,1));
  for(int epoch=1;epoch<=4;epoch++){
   int origin=z.currentMap(),target=origin==1?101:1;long now=1000+epoch*10000;
   need(z.prepare(now));need(z.epoch()==epoch&&!z.blocksInput());need(!z.prepare(now+1)&&!z.beginTravel());
   need(accept(z,event("preparing",epoch,origin,target,now+1),now+1,20,2));
   need(accept(z,event("ready",epoch,origin,target,now+2),now+2,20,2));need(z.canTravel()&&!z.blocksInput());
   need(z.beginTravel()&&z.blocksInput());need(!z.canTravel());need(z.delivered(now+3));
   need(accept(z,event("transferring",epoch,origin,target,now+4),now+4,30,3));
   need(accept(z,event("arrived",epoch,target,target,now+5),now+5,40,4));
   need(z.currentMap()==target&&z.blocksInput()&&!z.canPrepare());
   need(!z.capture(40,5)&&!z.capture(41,4));need(z.capture(41,5));
   need(!z.capture(500,6)&&!z.capture(1041,5));need(z.capture(1041,6));need(z.capture(2041,7));
   need(z.captures()==3&&!z.blocksInput());need(!z.capture(3041,8));
  }
  need(!z.canPrepare()&&!z.prepare(999999)&&z.currentMap()==1);
 }
 static void forged(String field){
  ClientZoning z=transferring();Map<String,Object> e=event("arrived",1,101,101,1400);
  if(field.equals("session_id"))e.put(field,"fedcba9876543210fedcba9876543210");
  else if(field.equals("status"))e.put(field,"ready");
  else if(field.equals("generated_utc_ms"))e.put(field,999L);
  else if(field.equals("current_map_id")||field.equals("target_map_id"))e.put(field,2);
  else if(field.equals("epoch"))e.put(field,2);
  else if(field.equals("format"))e.put(field,1.0);
  else if(field.equals("elapsed_ms"))e.put(field,-1);
  else if(field.equals("client_pid")||field.equals("character_id")||field.equals("mapserver_pid"))e.put(field,0);
  else e.put(field,false);
  need(!accept(z,e,1400,50,5));need(z.blocksInput()&&z.currentMap()==1&&!z.capture(10000,100));
 }
 static void stale(){
  ClientZoning z=enabled();need(!accept(z,event("ready",1,1,101,1400),1400,40,4));
  need(z.prepare(1100));need(!accept(z,event("ready",1,1,101,1200),130001,40,4));
  need(!accept(z,event("ready",1,1,101,5000),1200,40,4));
  need(accept(z,event("ready",1,1,101,1200),1200,40,4));
  need(!accept(z,event("arrived",1,101,101,1400),1400,40,4));
  need(z.beginTravel());need(!accept(z,event("arrived",1,101,101,1400),1400,40,4));
 }
 static void fail(){
  ClientZoning z=enabled();need(z.prepare(1100));Map<String,Object> e=event("failed",1,1,101,1200);e.put("transfer_requested",false);
  need(accept(z,e,1200,20,2));need(!z.blocksInput()&&!z.canPrepare()&&!z.canTravel());
  z=transferring();e=event("failed",1,1,101,1400);e.put("transfer_requested",true);e.put("current_map_verified",false);
  need(accept(z,e,1400,50,5));need(z.blocksInput()&&!z.canPrepare());
 }
 static void connection(){
  Map<String,Object> e=new LinkedHashMap<>();e.put("type","character_connected");e.put("session_id",SESSION);e.put("client_pid",73);
  e.put("character_id",1);e.put("baseline_character_id",1);e.put("name","THORHERO");e.put("account","COHLOCAL");
  e.put("map_id",101);e.put("zoning_enabled",true);e.put("connected_on_supported_map",true);e.put("reopen_verified",true);e.put("existing_character_verified",true);
  need(!ClientAcceptance.characterReopenConnectedEvent(e,SESSION,73));need(ClientAcceptance.characterReopenConnectedEvent(e,SESSION,73,true));
  e.remove("connected_on_supported_map");need(!ClientAcceptance.characterReopenConnectedEvent(e,SESSION,73,true));e.put("connected_on_supported_map",true);
  e.put("map_id",2);need(!ClientAcceptance.characterReopenConnectedEvent(e,SESSION,73,true));
  e.put("map_id",1);need(ClientAcceptance.characterReopenConnectedEvent(e,SESSION,73));
 }
 static void saves(){
  for(int origin:new int[]{1,101})for(int destination:new int[]{1,101}){
   Map<String,Object> connected=new LinkedHashMap<>(),saved=new LinkedHashMap<>(),proof=new LinkedHashMap<>(),login=new LinkedHashMap<>(),report=new LinkedHashMap<>();
   for(Map<String,Object> item:Arrays.asList(connected,saved,proof,login)){
    item.put("session_id",SESSION);item.put("client_pid",73);item.put("character_id",1);item.put("name","THORHERO");item.put("account","COHLOCAL");
    item.put("zoning_enabled",true);item.put("connected_on_supported_map",true);item.put("map_id",destination);
   }
   connected.put("type","character_connected");connected.put("map_id",origin);connected.put("baseline_character_id",1);connected.put("reopen_verified",true);connected.put("existing_character_verified",true);
   saved.put("type","character_saved");saved.put("committed_sql_verified",true);
   for(String flag:new String[]{"verified","connected_on_atlas","committed_sql_verified","requested_logout_observed","logout_timer_observed","disconnected_before_sql","reopen_verified","existing_character_verified","preserved_existing_identity","native_client_ready_observed","powers_preserved","costume_preserved","selected_rows_preserved","committed_native_position_verified"})proof.put(flag,true);
   for(String flag:new String[]{"forced_stop_before_save","recovery_requested","recovery_verified","ordinary_stuck_observed","on_atlas_safe_position","stable_ground_verified","committed_safe_position_verified"})proof.put(flag,false);
   proof.put("auth_id",2);proof.put("before_character_id",1);proof.put("baseline_character_id",1);
   login.put("auth_id",2);login.put("profile","android-local-login");for(String flag:new String[]{"local_login_verified","character_list_sent","local_account_verified","character_list_response_sent","database_preserved"})login.put(flag,true);
   report.put("local_login",login);report.put("character_reopen",proof);
   need(ClientAcceptance.characterReopenVerified(report,saved,connected,SESSION,73,true));
   for(String flag:new String[]{"committed_sql_verified","requested_logout_observed","logout_timer_observed","disconnected_before_sql","powers_preserved","costume_preserved","selected_rows_preserved","committed_native_position_verified"}){
    proof.put(flag,false);need(!ClientAcceptance.characterReopenVerified(report,saved,connected,SESSION,73,true));proof.put(flag,true);
   }
   saved.put("map_id",destination==1?101:1);need(!ClientAcceptance.characterReopenVerified(report,saved,connected,SESSION,73,true));
  }
 }
 static void budget(){
  Map<String,Object> e=new LinkedHashMap<>();e.put("type","character_session_budget");e.put("format",1);e.put("session_id",SESSION);e.put("client_pid",73);
  e.put("character_id",1);e.put("name","THORHERO");e.put("account","COHLOCAL");e.put("map_id",101);e.put("zoning_enabled",true);
  e.put("native_client_ready_observed",true);e.put("reopen_verified",true);e.put("revision",1);e.put("phase","connected");
  e.put("generated_utc_ms",1000);e.put("deadline_utc_ms",601000);e.put("save_request_deadline_utc_ms",421000);e.put("movement_deadline_utc_ms",361000);
  ClientSessionBudget b=new ClientSessionBudget();need(!b.apply(e,SESSION,73,true,false,0,1000,10,700000));
  need(!b.apply(e,SESSION,73,true,false,0,1000,10,700000,true,1));
  need(b.apply(e,SESSION,73,true,false,0,1000,10,700000,true,101));need(b.canMove(10));
  need(!b.apply(e,SESSION,73,true,false,0,1000,10,700000,true,101));
 }
 static void commands()throws Exception {
  ByteArrayOutputStream output=new ByteArrayOutputStream();InteractiveRfbClient r=new InteractiveRfbClient(new ByteArrayInputStream(new byte[0]),output,(p,w,h,s)->{});
  for(String name:new String[]{"width","height"}){Field f=InteractiveRfbClient.class.getDeclaredField(name);f.setAccessible(true);f.setInt(r,name.equals("width")?800:600);}
  Field ready=InteractiveRfbClient.class.getDeclaredField("updatesReady");ready.setAccessible(true);ready.setBoolean(r,true);
  for(int map:new int[]{1,101}){
   output.reset();r.sendMapMove(map,r.inputEpoch());DataInputStream input=new DataInputStream(new ByteArrayInputStream(output.toByteArray()));StringBuilder typed=new StringBuilder();
   while(input.available()>0){int type=input.readUnsignedByte();if(type==5){input.skipBytes(5);continue;}need(type==4);boolean down=input.readUnsignedByte()==1;input.skipBytes(2);int key=input.readInt();if(down)typed.append(key==0xff0d?'|':(char)key);}
   need(typed.toString().equals("|/mapmove "+map+"|"));
  }
  for(int map:new int[]{-1,0,2,100,102,Integer.MAX_VALUE}){output.reset();try{r.sendMapMove(map,r.inputEpoch());throw new AssertionError();}catch(IOException expected){}need(output.size()==0);}
  long old=r.inputEpoch();r.cancelPendingInput();output.reset();try{r.sendMapMove(101,old);throw new AssertionError();}catch(InteractiveRfbClient.InputCancelledException expected){}need(output.size()==0);
 }
 public static void main(String[] args)throws Exception {
  switch(args[0]){case "roundtrip":roundtrip();break;case "stale":stale();break;case "fail":fail();break;case "connection":connection();break;case "budget":budget();break;case "saves":saves();break;case "commands":commands();break;default:forged(args[0]);}
  System.out.println("PASS");
 }
}
'''

class ClientZoningJavaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='coh-zoning-java-')
        cls.addClassCleanup(cls.tmp.cleanup)
        host=Path(cls.tmp.name)/'ZoningHost.java';host.write_text(HARNESS)
        sources=[ZONING_JAVA]+[JAVA/name for name in ('ClientAcceptance.java','ClientSessionBudget.java','InteractiveRfbClient.java')]
        subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','--release','8','-d',cls.tmp.name,*map(str,sources),str(host)],check=True,capture_output=True,text=True,timeout=60)
    def run_host(self,mode):
        result=subprocess.run(['java','-cp',self.tmp.name,'io.github.russianranger.cohclientinteractive.ZoningHost',mode],check=True,capture_output=True,text=True,timeout=15)
        self.assertEqual(result.stdout.strip(),'PASS')
    def test_four_transfers_require_fresh_native_event_and_three_views(self):self.run_host('roundtrip')
    def test_stale_future_and_pre_delivery_arrivals_rejected(self):self.run_host('stale')
    def test_preparation_failure_preserves_save_but_transfer_failure_blocks(self):self.run_host('fail')
    def test_map101_connection_requires_opt_in_and_supported_map_proof(self):self.run_host('connection')
    def test_map101_budget_requires_initial_map_identity_without_extension(self):self.run_host('budget')
    def test_same_character_save_on_both_maps_retains_every_strict_proof(self):self.run_host('saves')
    def test_stock_mapmove_transport_fixed_allowlist_and_epoch_cancellation(self):self.run_host('commands')
    def test_each_foreign_or_missing_arrival_claim_fails_closed(self):
        for field in ('session_id','client_pid','character_id','epoch','status','current_map_id','target_map_id','format','generated_utc_ms','elapsed_ms','arrival_native_verified','mapserver_pid','current_map_verified','character_identity_preserved','exact_destination_endpoint_verified'):
            with self.subTest(field=field):self.run_host(field)


# The real Runtime methods are also exercised with controlled delivery pauses,
# so state-only fixtures cannot conceal a UI/queue reservation regression.
class ClientZoningRuntimeTests(unittest.TestCase):
    def test_shipped_runtime_reservation_receipt_and_recovery_exclusion(self):
        import test_client_sidebar_runtime as sidebar
        source=(JAVA/'ClientRuntime.java').read_text()
        self.assertIn('zoning_preparation_observations',sidebar.method(source,'private synchronized void checkpoint('))
        self.assertIn('preparation_observations',sidebar.method(source,'private void publish('))
        self.assertIn('recordZoningPreparation',sidebar.method(source,'private void captureOutput('))
        runtime=sidebar.harness()
        actual='\n'.join(sidebar.method(source,name) for name in (
            'private boolean zoningEnabled(', 'public synchronized String zoningStatus(',
            'private boolean zoningRecoveryAllowed(', 'public int zoningCurrentMap(',
            'public synchronized void setUiVisible(', 'public synchronized boolean canRequestZoning(',
            'public synchronized boolean requestZoning(', 'private void markZoningTime(',
            'private synchronized void dispatchPreparedZoning(',
            'private static long preparationInteger(', 'private static boolean nativePreparationStage(',
            'private synchronized boolean recordZoningPreparation(',
            'public synchronized boolean canPrepareZoning(', 'public synchronized boolean canTravelZoning(',
            'private JSONObject zoningRequest(', 'public synchronized boolean requestPrepareZoning(',
            'public synchronized boolean requestTravelZoning('))
        runtime=runtime.replace('import java.io.*;', 'import java.io.*;\nimport java.nio.charset.StandardCharsets;')
        runtime=runtime.replace('boolean canSave(long n){return true;}', 'boolean canSave(long n){return true;}boolean manualPolicy;boolean manual(){return manualPolicy;}long movementDeadline(){return manualPolicy?0:Long.MAX_VALUE/2;}')
        runtime=runtime.replace(' JSONObject getJSONObject(String name)', ' Object opt(String name){return get(name);}\n public JSONObject put(String key,Object value){super.put(key,value);return this;}\n JSONObject getJSONObject(String name)')
        runtime=runtime.replace(' void requestFullUpdate()throws IOException {}', ' void sendMapMove(int map,long epoch)throws IOException {sendPerformanceCommand("mapmove "+map,epoch);}\n void requestFullUpdate()throws IOException {}')
        runtime=runtime.replace('  String zoningStatus(){return zoning.phase();}', '''
  JSONObject manifest=new JSONObject().put("character_zoning_enabled",true);
  boolean uiVisible=true,automaticTravel;long zoningDepartureDeadlineUtc;
  List<Map<String,Object>> zoningTimings=new ArrayList<>();
  List<Map<String,Object>> zoningPreparationObservations=new ArrayList<>();
  boolean zoningPreparationObservationLimitReached;int checkpoints;
  void checkpoint(){checkpoints++;}
  File state=new File("/not-written-host-fixture");
  List<String> receipts=Collections.synchronizedList(new ArrayList<>());
  void write(File path,byte[] bytes){receipts.add(path.getName()+":"+new String(bytes,StandardCharsets.UTF_8));}
''' + actual)
        test=r'''
 static void zoningQueue(boolean resume,boolean manual) throws Exception {
  String owner="0123456789abcdef0123456789abcdef";
  ClientRuntime r=new ClientRuntime();r.world();r.session=owner;r.sessionBudget.manualPolicy=manual;long now=System.currentTimeMillis();
  try {
   Map<String,Object> enabled=new LinkedHashMap<>();enabled.put("type","character_zoning");enabled.put("format",1);enabled.put("session_id",owner);
   enabled.put("client_pid",17);enabled.put("character_id",1);enabled.put("epoch",0);enabled.put("current_map_id",1);enabled.put("target_map_id",101);
   enabled.put("status","enabled");enabled.put("generated_utc_ms",now-10);enabled.put("current_map_verified",true);enabled.put("zoning_enabled",true);
   require(r.zoning.accept(enabled,owner,17,1,now,10,1));require(r.zoningRecoveryAllowed());
   r.stuckRequested=true;r.relocationCapturedReady=true;require(!r.canPrepareZoning());require(r.zoningStatus().contains("Save and reopen"));r.stuckRequested=false;
   require(r.requestZoning());require(r.automaticTravel);require(r.receipts.size()==1&&r.receipts.get(0).startsWith("character-zoning-request.json:"));
   require(!r.zoningRecoveryAllowed()&&!r.canPrepareZoning()&&!r.canTravelZoning());
   Map<String,Object> observation=new LinkedHashMap<>();
   observation.put("type","character_zoning_preparation");observation.put("session_id",owner);observation.put("client_pid",17);observation.put("character_id",1);
   observation.put("epoch",1);observation.put("map_id",101);observation.put("observed_utc_ms",System.currentTimeMillis());observation.put("observed_monotonic_ms",100L);
   observation.put("stage","MAP_LOAD");observation.put("windows_pid",91);observation.put("tick_completed",0);observation.put("native_stage_duration_measured",false);
   observation.put("unreviewed_secret","must-not-retain");require(r.recordZoningPreparation(observation));require(r.checkpoints==1);
   require(!r.recordZoningPreparation(observation)&&!r.zoningPreparationObservations.get(0).containsKey("unreviewed_secret"));
   for(String field:new String[]{"session_id","client_pid","character_id","epoch","map_id","observed_utc_ms","observed_monotonic_ms","stage","windows_pid","tick_completed","native_stage_duration_measured"}){
    Map<String,Object> invalid=new LinkedHashMap<>(observation);invalid.put(field,field.equals("session_id")?"other":field.equals("stage")?"FAKE_STAGE":field.equals("native_stage_duration_measured")?true:-1);
    require(!r.recordZoningPreparation(invalid));
   }
   Map<String,Object> scheduler=new LinkedHashMap<>(observation);scheduler.put("observation_kind","scheduler");scheduler.put("scheduler_phase","capability");scheduler.put("capability",Collections.singletonMap("supported",false));
   scheduler.put("changed_threads",0);scheduler.put("restored_threads",0);scheduler.put("exited_threads",0);scheduler.put("restore_complete",false);scheduler.put("exact_destination_only",true);scheduler.put("physical_performance_gain_verified",false);
   require(r.recordZoningPreparation(scheduler));require(!r.zoningPreparationObservations.get(1).containsKey("stage"));
   scheduler.put("physical_performance_gain_verified",true);require(!r.recordZoningPreparation(scheduler));
   for(int i=0;i<126;i++){observation.put("observed_monotonic_ms",101L+i);observation.put("tick_completed",i);require(r.recordZoningPreparation(observation));}
   observation.put("observed_monotonic_ms",1000L);require(!r.recordZoningPreparation(observation));require(r.zoningPreparationObservations.size()==128&&r.zoningPreparationObservationLimitReached);
   require(r.zoning.phase().equals("preparing")&&!r.zoning.blocksInput());require(r.canRequestSaveLogout());require(r.canSendPerformanceCommand());
   Map<String,Object> ready=new LinkedHashMap<>(enabled);ready.put("epoch",1);ready.put("status","ready");ready.put("generated_utc_ms",System.currentTimeMillis()+1);ready.put("destination_ready",true);
   require(r.zoning.accept(ready,owner,17,1,System.currentTimeMillis()+1,20,2));require(r.canTravelZoning()==manual);r.zoningDepartureDeadlineUtc=System.currentTimeMillis()+600000;require(r.canTravelZoning());
   r.markZoningTime("ready");r.decoder.hold=true;
   if(resume){
    r.setUiVisible(false);require(!r.automaticTravel&&!r.requestZoning()&&!r.requestTravelZoning());
    r.dispatchPreparedZoning();require(r.decoder.writes.isEmpty());
    r.setUiVisible(true);require(!r.automaticTravel);require(r.requestZoning());
   }else {r.dispatchPreparedZoning();require(!r.automaticTravel);}
   require(r.decoder.entered.await(1,TimeUnit.SECONDS));
   require(r.isPerformanceCommandPending()&&!r.canRequestSaveLogout()&&!r.canSendPerformanceCommand());
   require(!r.queueInput(owner,(a,e)->a.writes.add("overlap"),true));require(r.receipts.size()==1);
   r.queueRelease(owner,true);require(r.zoning.commandInFlight());r.decoder.proceed.countDown();r.idle();
   require(r.receipts.size()==2&&r.receipts.get(1).startsWith("character-zoning-delivery.json:"));
   require(r.receipts.get(1).contains("client_pid=17")&&r.receipts.get(1).contains("epoch=1")&&r.receipts.get(1).contains("to_map_id=101"));
   require(r.zoning.phase().equals("transferring")&&!r.canRequestSaveLogout());require(!r.decoder.writes.contains("overlap"));
   r.markZoningTime("native_arrival");r.markZoningTime("fresh_views");
   Map<String,Object> timing=r.zoningTimings.get(0);require(timing.containsKey("request_to_ready_ms")&&timing.containsKey("request_to_delivery_ms")&&timing.containsKey("request_to_native_arrival_ms")&&timing.containsKey("total_elapsed_ms"));
   require(((Number)timing.get("total_elapsed_ms")).longValue()>=((Number)timing.get("request_to_delivery_ms")).longValue());
  }finally{r.decoder.proceed.countDown();r.close();}
 }
'''
        start=runtime.index(' public static void main(String[] args)throws Exception {')
        runtime=runtime[:start]+test+' public static void main(String[] args)throws Exception {zoningQueue(false,false);zoningQueue(true,false);zoningQueue(false,true);zoningQueue(true,true);System.out.println("PASS runtime zoning");}\n}\n'
        with tempfile.TemporaryDirectory(prefix='coh-zoning-runtime-') as temp:
            host=Path(temp)/'SidebarRuntimeHost.java';host.write_text(runtime)
            subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','--release','8','-d',temp,
                str(JAVA/'ClientInput.java'),str(JAVA/'ClientAcceptance.java'),str(ZONING_JAVA),str(host)],check=True,capture_output=True,text=True,timeout=60)
            result=subprocess.run(['java','-cp',temp,'io.github.russianranger.cohclientinteractive.SidebarRuntimeHost'],check=True,capture_output=True,text=True,timeout=15)
            self.assertEqual(result.stdout.strip(),'PASS runtime zoning')

if __name__=='__main__':unittest.main()
