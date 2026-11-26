"""0.13.86: the menu's status lines in plain words (the shipped ClientZoning.plainStatus, run for real)."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
ZONING_JAVA = ROOT / 'android/zoning/src/main/java/io/github/russianranger/cohclientinteractive/ClientZoning.java'
JAVA = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
HARNESS = r'''
package io.github.russianranger.cohclientinteractive;
public final class PlainStatusHost {
 static void need(boolean value,String what){if(!value)throw new AssertionError(what);}
 static String[] plain(String stage,String detail){return ClientZoning.plainStatus(stage,detail);}
 public static void main(String[] args){
  // Every status the session can show is given on the command line; none may keep the check wording.
  for(String stage:args){
   String[] shown=plain(stage,"Ralakar connected to Atlas Park. More follows.");
   String both=(shown[0]+" "+shown[1]).toLowerCase();
   for(String word:new String[]{"verified","check complete","check incomplete","check failed","android views","captures","ownership","sql","mapserver","dbserver"})
    need(!both.contains(word)||stage.startsWith("Task ")||stage.startsWith("Accepted task")||stage.contains("ontact")||stage.startsWith("Test capture"),stage+" -> "+both);
  }
  String[] done=plain("Character reopen check complete","The existing character was reopened and saved with its identity, powers and costume preserved.");
  need(done[0].equals("Session finished")&&done[1].startsWith("Your hero is saved."),"complete");
  need(plain("Character creation check incomplete","x")[0].equals("Session finished"),"incomplete");
  need(plain("Character reopen check stopped","x")[0].equals("Session stopped"),"stopped");
  String[] failed=plain("Character reopen check failed","Character reopen check failed. Kings Row did not start. Export the latest report.");
  need(failed[0].equals("Session ended with a problem")&&failed[1].startsWith("Kings Row did not start. Your hero's last save is kept."),failed[1]);
  String[] in=plain("Character connected","Ralakar connected to Kings Row. Walking works now; more.");
  need(in[0].equals("In the game")&&in[1].startsWith("Ralakar is in Kings Row. Play as long as you like."),in[1]);
  String[] found=plain("Saved destination verified","Ralakar is saved in Atlas Park. Atlas Park starts when you press Enter Game.");
  need(found[0].equals("Hero found")&&found[1].equals("Ralakar is saved in Atlas Park."),found[1]);
  need(plain("Client ready for input","Log in with COHLOCAL / offline, select your existing character and click Enter Game.")[1]
    .equals("Log in as COHLOCAL (offline), then choose your hero and click Enter Game."),"ready");
  need(plain("Local login verified","Create your character (any name) as a Primal Earth Hero.")[1]
    .startsWith("Create your hero. After Enter Game"),"create");
  // A status the table does not know, and the setup ones, pass unchanged.
  String[] other=plain("Runtime ready","Everything is installed.");
  need(other[0].equals("Runtime ready")&&other[1].equals("Everything is installed."),"unchanged");
  need(plain(null,null)[0].isEmpty(),"null");
  // The line under the status: nothing for a saved hero's session, a time limit only for a first hero.
  need(ClientZoning.plainTiming(true,false,0,false,0,0,false).isEmpty(),"no limit");
  need(ClientZoning.plainTiming(false,false,90,true,0,0,false).isEmpty(),"not ready");
  need(ClientZoning.plainTiming(true,true,90,true,0,0,false).isEmpty(),"saved");
  need(ClientZoning.plainTiming(true,false,90,true,0,0,false).equals("Time left for this first session: 90 s."),"first");
  need(ClientZoning.plainTiming(true,false,90,true,40,10,true).equals("Save within 40 s."),"save");
  need(ClientZoning.plainTiming(true,false,90,true,40,0,true).equals("Stand still and save within 40 s."),"still");
  need(ClientZoning.plainTiming(true,false,90,true,0,0,true).equals("The time to save has run out."),"out");
  System.out.println("plain status ok");
 }
}
'''


class PlainStatus(unittest.TestCase):
    @unittest.skipUnless(shutil.which('javac') and shutil.which('java'), 'no JDK here')
    def test_no_status_of_a_session_keeps_the_check_wording(self):
        stages = set()
        for name in ('ClientRuntime.java', 'ClientService.java'):
            stages.update(re.findall(r'stage\("([^"]+)"', (JAVA / name).read_text()))
        stages.update(label + ending for label in ('Character reopen', 'Character creation', 'Task save')
                      for ending in (' check complete', ' check incomplete', ' check failed', ' check stopped'))
        self.assertGreater(len(stages), 40)
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            source = work / 'io/github/russianranger/cohclientinteractive'
            source.mkdir(parents=True)
            shutil.copy(ZONING_JAVA, source / 'ClientZoning.java')
            (source / 'PlainStatusHost.java').write_text(HARNESS)
            subprocess.run(['javac', '-d', str(work / 'out'), str(source / 'ClientZoning.java'),
                            str(source / 'PlainStatusHost.java')], check=True, capture_output=True, text=True)
            done = subprocess.run(['java', '-cp', str(work / 'out'),
                                   'io.github.russianranger.cohclientinteractive.PlainStatusHost', *sorted(stages)],
                                  capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertIn('plain status ok', done.stdout)

    def test_the_menu_shows_plain_words_unless_test_details_are_ticked(self):
        activity = (JAVA / 'ClientActivity.java').read_text()
        self.assertIn('testDetails.setText("Show test details and tools");', activity)
        self.assertIn('state=next;refreshTestControls();showStatus(next);', activity)
        self.assertNotIn('setTextIfChanged(status,next.stage)', activity)
        self.assertIn('finish=button("Finish",', activity)
        self.assertIn('run=button("Play",', activity)


if __name__ == '__main__':
    unittest.main()
