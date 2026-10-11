"""Execute Android's stock-station state machine without accepting input as proof."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'android/zoning/src/main/java/io/github/russianranger/cohclientinteractive/ClientZoning.java'
HARNESS = r'''
package io.github.russianranger.cohclientinteractive;
import java.util.*;
public final class MonorailHost {
 static final String SESSION="0123456789abcdef0123456789abcdef";
 static void need(boolean x){if(!x)throw new AssertionError();}
 static Map<String,Object> event(String status,int epoch,int from,int target,long utc){
  Map<String,Object> e=new LinkedHashMap<>();
  e.put("type","character_zoning");e.put("format",1);e.put("session_id",SESSION);
  e.put("client_pid",73);e.put("character_id",1);e.put("epoch",epoch);
  e.put("current_map_id",from);e.put("target_map_id",target);e.put("generated_utc_ms",utc);
  e.put("status",status);e.put("current_map_verified",true);e.put("zoning_enabled",true);
  e.put("travel_method","stock_monorail");e.put("native_station_pid",from==1?91:92);
  e.put("native_request_sequence",1);e.put("requested_utc_ms",200L);
  e.put("native_station_request_verified",true);return e;
 }
 static boolean accept(ClientZoning z,Map<String,Object> e){return z.accept(e,SESSION,73,1,1000,1000,5,true);}
 static ClientZoning enabled(){ClientZoning z=new ClientZoning();need(accept(z,event("enabled",0,1,5,100)));return z;}
 static void forward(ClientZoning z){
  need(accept(z,event("preparing",1,1,5,210)));need(z.blocksInput());need(!z.canPrepare()&&!z.canTravel());
  Map<String,Object> e=event("ready",1,1,5,300);e.put("destination_ready",true);need(accept(z,e));need(!z.beginTravel());
  e=event("transferring",1,1,5,400);e.put("native_station_departure_verified",true);e.put("sent_utc_ms",350L);need(accept(z,e));
  e=event("arrived",1,5,5,500);e.put("native_station_pid",91);e.put("arrival_native_verified",true);
  e.put("character_identity_preserved",true);e.put("exact_destination_endpoint_verified",true);
  e.put("mapserver_pid",92);e.put("elapsed_ms",150);need(accept(z,e));need(z.blocksInput());
  need(!z.capture(1000,6));need(z.capture(1001,6));need(!z.capture(1500,7));
  need(z.capture(2001,7));need(z.capture(3001,8));need(z.currentMap()==5&&!z.blocksInput());
 }
 public static void main(String[] args){
  String mode=args[0];ClientZoning z=new ClientZoning();
  if(mode.equals("optin")){
   need(!z.accept(event("enabled",0,1,5,100),SESSION,73,1,1000,1000,5));need(!z.enabled());
   need(accept(z,event("enabled",0,1,5,100)));need(z.stockMonorail());need(!z.prepare(200));
  }else if(mode.equals("roundtrip")){
   z=enabled();forward(z);Map<String,Object> e=event("preparing",2,5,1,600);e.put("requested_utc_ms",550L);
   need(accept(z,e));need(z.targetMap()==1&&z.epoch()==2);
  }else if(mode.equals("departure")){
   z=enabled();need(accept(z,event("preparing",1,1,5,210)));
   Map<String,Object> e=event("transferring",1,1,5,400);e.put("native_station_departure_verified",true);e.put("sent_utc_ms",350L);
   need(!accept(z,e));need(z.phase().equals("preparing"));
   Map<String,Object> ready=event("ready",1,1,5,300);ready.put("destination_ready",true);need(accept(z,ready));
   e.put("current_map_id",5);need(!accept(z,e));need(z.phase().equals("ready"));
   e.put("current_map_id",1);e.remove("native_station_departure_verified");need(!accept(z,e));
  }else if(mode.equals("failure")){
   z=enabled();need(accept(z,event("preparing",1,1,5,210)));
   Map<String,Object> e=event("failed",1,1,5,300);e.put("transfer_requested",false);need(accept(z,e));
   need(z.phase().equals("prepare_failed")&&!z.blocksInput());
  }else{
   z=enabled();Map<String,Object> e=event("preparing",1,1,5,210);
   e.remove(mode);need(!accept(z,e));need(z.phase().equals("idle")&&z.epoch()==0);
  }
  System.out.println("PASS");
 }
}
'''


class ClientMonorailJavaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='coh-monorail-java-')
        cls.addClassCleanup(cls.tmp.cleanup)
        host = Path(cls.tmp.name) / 'MonorailHost.java'
        host.write_text(HARNESS)
        subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8', '-d', cls.tmp.name, str(SOURCE), str(host)],
                       check=True, capture_output=True, text=True, timeout=60)

    def run_case(self, name):
        result = subprocess.run(['java', '-cp', self.tmp.name,
            'io.github.russianranger.cohclientinteractive.MonorailHost', name],
            check=True, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.stdout.strip(), 'PASS')

    def test_stock_station_requires_explicit_runtime_opt_in(self): self.run_case('optin')
    def test_arrival_requires_three_fresh_views_before_return(self): self.run_case('roundtrip')
    def test_departure_requires_ready_target_and_native_departure(self): self.run_case('departure')
    def test_preparation_failure_preserves_ordinary_save(self): self.run_case('failure')
    def test_foreign_or_incomplete_station_request_cannot_advance_epoch(self):
        for field in ('session_id', 'client_pid', 'character_id', 'epoch', 'current_map_id',
                      'target_map_id', 'native_station_pid', 'native_request_sequence',
                      'native_station_request_verified', 'requested_utc_ms', 'travel_method'):
            with self.subTest(field=field): self.run_case(field)


class KingsRowPersistenceJavaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import test_client_zoning_java as retained
        cls.tmp = tempfile.TemporaryDirectory(prefix='coh-kings-save-java-')
        cls.addClassCleanup(cls.tmp.cleanup)
        source = retained.HARNESS.replace(
            'for(int origin:new int[]{1,101})for(int destination:new int[]{1,101})',
            'for(int origin:new int[]{1,5,101})for(int destination:new int[]{1,5,101})')
        source = source.replace('item.put("zoning_enabled",true);',
            'item.put("monorail_enabled",true);item.put("zoning_enabled",true);')
        source = source.replace('need(ClientAcceptance.characterReopenVerified(report,saved,connected,SESSION,73,true));',
            'if(destination==5){proof.remove("monorail_enabled");need(!ClientAcceptance.characterReopenVerified(report,saved,connected,SESSION,73,true));proof.put("monorail_enabled",true);}'
            'need(ClientAcceptance.characterReopenVerified(report,saved,connected,SESSION,73,true));')
        source = source.replace('e.put("map_id",101);e.put("zoning_enabled",true);',
            'e.put("map_id",5);e.put("monorail_enabled",true);e.put("zoning_enabled",true);')
        source = source.replace('700000,true,101)', '700000,true,5)')
        host = Path(cls.tmp.name) / 'ZoningHost.java'
        host.write_text(source)
        sources = [retained.ZONING_JAVA] + [retained.JAVA / name for name in
            ('ClientAcceptance.java', 'ClientSessionBudget.java', 'InteractiveRfbClient.java')]
        subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                        '-d', cls.tmp.name, *map(str, sources), str(host)],
                       check=True, capture_output=True, text=True, timeout=60)

    def run_case(self, mode):
        result = subprocess.run(['java', '-cp', self.tmp.name,
            'io.github.russianranger.cohclientinteractive.ZoningHost', mode],
            check=True, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.stdout.strip(), 'PASS')

    def test_kings_row_save_and_reopen_require_all_existing_persistence_proofs(self):
        self.run_case('saves')

    def test_kings_row_budget_preserves_deadline_and_exact_connected_map(self):
        self.run_case('budget')


if __name__ == '__main__': unittest.main()
