"""Execute shipped Java saved-map/window checks; no Android pixels are claimed."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientAcceptance.java'
HARNESS = r'''
package io.github.russianranger.cohclientinteractive;
import java.util.*;
public final class SavedMapWindowHost {
 static final String SESSION="0123456789abcdef0123456789abcdef";
 static Map<String,Object> window(String title){Map<String,Object> w=new LinkedHashMap<>();
  w.put("title",title);w.put("width",800);w.put("height",600);w.put("mapped",true);return w;}
 static void need(boolean value){if(!value)throw new AssertionError();}
 static boolean accept(String title,int first,int last,boolean qualified){
  return ClientAcceptance.clientWindowAccepted(window(title),42L,first,last,qualified);}
 public static void main(String[] args){
  String atlas="City of Heroes : City_Zones/City_01_01/City_01_01.txt  PID: 42";
  String kings="City of Heroes : City_Zones/City_01_02/City_01_02.txt  PID: 42";
  if("windows".equals(args[0])){
   need(!ClientAcceptance.clientWindowAccepted(window(kings),42L));
   need(accept(kings,5,5,true));need(accept(atlas,1,1,false));need(accept(atlas,101,101,false));
   need(!accept(kings,5,5,false));need(!accept(kings,1,1,true));need(!accept(atlas,5,5,true));
   need(accept(kings,5,1,true));need(accept(atlas,5,1,true));
   need(accept(kings,1,5,true));need(accept(atlas,1,5,true));
   need(accept("City of Heroes : PID: 42",5,5,true));
   need(accept(kings.replace('/','\\'),5,5,true));
   for(String bad:new String[]{kings.replace("42","43"),kings+" extra",kings.replace("City_01_02.txt","City_01_01.txt"),
       kings.replace("City_Zones/","../City_Zones/"),kings.replace("City_01_02","City_02_01")})need(!accept(bad,5,5,true));
   need(!accept(kings,2,5,true));need(!accept(kings,5,2,true));
   Map<String,Object> w=window(kings);w.put("mapped",1);need(!ClientAcceptance.clientWindowAccepted(w,42L,5,5,true));
   need(!ClientAcceptance.clientWindowAccepted(window(kings),true,5,5,true));
  }else{
   Map<String,Object> e=new LinkedHashMap<>();e.put("type","saved_character_destination");e.put("session_id",SESSION);
   e.put("character_id",1);e.put("auth_id",77);e.put("name","THORHERO");e.put("account","COHLOCAL");
   e.put("map_id",5);e.put("port",7003);e.put("world","City_01_02");e.put("existing_character_verified",true);
   e.put("saved_location_verified",true);e.put("sql_game_mutations_performed",false);
   need(ClientAcceptance.savedDestinationEvent(e,SESSION,true));need(!ClientAcceptance.savedDestinationEvent(e,SESSION,false));
   need(!ClientAcceptance.savedDestinationEvent(e,"ffffffffffffffffffffffffffffffff",true));
   for(String key:new String[]{"type","session_id","character_id","auth_id","name","account","map_id","port","world",
       "existing_character_verified","saved_location_verified","sql_game_mutations_performed"}){
    Object old=e.remove(key);need(!ClientAcceptance.savedDestinationEvent(e,SESSION,true));e.put(key,old);}
   e.put("port",7001);need(!ClientAcceptance.savedDestinationEvent(e,SESSION,true));e.put("port",7003);
   e.put("world","City_01_01");need(!ClientAcceptance.savedDestinationEvent(e,SESSION,true));e.put("world","City_01_02");
   e.put("map_id",true);need(!ClientAcceptance.savedDestinationEvent(e,SESSION,true));
   e.put("map_id",5);e.put("auth_id",4294967296L);need(!ClientAcceptance.savedDestinationEvent(e,SESSION,true));
   e.put("auth_id",true);need(!ClientAcceptance.savedDestinationEvent(e,SESSION,true));e.put("auth_id",77);
   e.put("map_id",1);e.put("port",7001);e.put("world","City_01_01");need(ClientAcceptance.savedDestinationEvent(e,SESSION,false));
   e.put("map_id",101);e.put("port",7002);need(ClientAcceptance.savedDestinationEvent(e,SESSION,false));
  }
  System.out.println("PASS");
 }
}
'''


class SavedMapWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        host = Path(cls.tmp.name) / 'SavedMapWindowHost.java'
        host.write_text(HARNESS)
        subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                        '-d', cls.tmp.name, str(SOURCE), str(host)], check=True,
                       capture_output=True, text=True, timeout=60)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def execute(self, mode):
        result = subprocess.run(['java', '-cp', self.tmp.name,
            'io.github.russianranger.cohclientinteractive.SavedMapWindowHost', mode],
            check=True, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.stdout.strip(), 'PASS')

    def test_exact_current_pid_and_proved_initial_final_maps(self):
        self.execute('windows')

    def test_saved_destination_progress_requires_exact_readonly_identity_world_port(self):
        self.execute('destination')

    def test_runtime_uses_map_scoped_acceptance_and_saved_destination_progress(self):
        source = SOURCE.with_name('ClientRuntime.java').read_text()
        self.assertIn('initialMap, currentMap, monorailQualified', source)
        self.assertIn('ClientAcceptance.savedDestinationEvent', source)
        self.assertIn('Saved destination verified', source)
        service = SOURCE.with_name('ClientService.java').read_text()
        self.assertNotIn('Starting the persistent database, DbServer and Atlas before the client', service)


if __name__ == '__main__':
    unittest.main()
