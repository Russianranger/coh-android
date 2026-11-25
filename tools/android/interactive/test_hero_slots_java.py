"""0.13.85: the second hero slot swaps folders by renaming (the shipped ClientZoning.switchHeroFolders, run for real)."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
ZONING_JAVA = ROOT / 'android/zoning/src/main/java/io/github/russianranger/cohclientinteractive/ClientZoning.java'
JAVA = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
HARNESS = r'''
package io.github.russianranger.cohclientinteractive;
import java.io.*;
import java.nio.file.*;
public final class HeroSlotsHost {
 static void need(boolean value){if(!value)throw new AssertionError();}
 static File hero(File folder,String name)throws IOException{need(folder.mkdirs());Files.write(new File(folder,"profile.json").toPath(),name.getBytes());return folder;}
 static String who(File folder)throws IOException{return new String(Files.readAllBytes(new File(folder,"profile.json").toPath()));}
 static String refused(File c,File o,File p,boolean saved,boolean readable){
  try{ClientZoning.switchHeroFolders(c,o,p,saved,readable);}catch(IOException e){return e.getMessage();}
  throw new AssertionError();
 }
 public static void main(String[] args)throws Exception{
  File root=new File(args[0]);File c=new File(root,"android-local-login"),o=new File(root,"android-local-login.other-hero"),p=new File(root,"android-local-login.switching");
  // Nothing anywhere.
  need(refused(c,o,p,false,true).startsWith("There is no saved hero"));
  // Set the saved hero aside: the saved slot becomes empty (Create fresh character).
  hero(c,"first");
  need(ClientZoning.switchHeroFolders(c,o,p,true,true).startsWith("The saved hero is in the other slot"));
  need(!c.exists()&&who(o).equals("first"));
  // A new hero is created, then swapped with the first, and back.
  hero(c,"second");
  need(ClientZoning.switchHeroFolders(c,o,p,true,true).startsWith("Switched"));
  need(who(c).equals("first")&&who(o).equals("second")&&!p.exists());
  need(ClientZoning.switchHeroFolders(c,o,p,true,true).startsWith("Switched"));
  need(who(c).equals("second")&&who(o).equals("first"));
  // An empty saved slot takes the other hero back.
  need(c.renameTo(new File(root,"elsewhere")));
  need(ClientZoning.switchHeroFolders(c,o,p,false,true).startsWith("The hero from the other slot"));
  need(who(c).equals("first")&&!o.exists());
  // Refusals change nothing: an incomplete saved hero, a leftover of a stopped switch, a file in the slot.
  hero(o,"other");
  need(refused(c,o,p,false,false).contains("incomplete"));
  need(refused(c,o,p,false,true).contains("not empty"));
  need(p.mkdir());need(refused(c,o,p,true,true).contains("did not finish"));need(p.delete());
  need(who(c).equals("first")&&who(o).equals("other"));
  File f=new File(root,"file-slot");Files.write(f.toPath(),new byte[]{1});
  need(refused(c,f,p,true,true).contains("not a folder"));
  need(who(c).equals("first")&&f.isFile());
  System.out.println("hero slots ok");
 }
}
'''


class HeroSlots(unittest.TestCase):
    @unittest.skipUnless(shutil.which('javac') and shutil.which('java'), 'no JDK here')
    def test_the_shipped_swap_renames_and_never_loses_a_hero(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            source = work / 'HeroSlotsHost.java'; source.write_text(HARNESS)
            classes = work / 'classes'; classes.mkdir(); slots = work / 'slots'; slots.mkdir()
            subprocess.run(['javac', '-d', str(classes), str(ZONING_JAVA), str(source)], check=True, capture_output=True)
            done = subprocess.run(['java', '-cp', str(classes), 'io.github.russianranger.cohclientinteractive.HeroSlotsHost',
                                   str(slots)], capture_output=True, text=True)
            self.assertEqual((done.returncode, done.stdout.strip()), (0, 'hero slots ok'), done.stderr[-2000:])

    def test_the_app_only_swaps_when_idle_and_refreshes_what_it_shows(self):
        runtime = (JAVA / 'ClientRuntime.java').read_text()
        self.assertIn('if (operationInProgress()) throw new IOException("Wait for the current operation to finish.");', runtime)
        self.assertIn('state == ProfileState.READY, state != ProfileState.PRESERVE);', runtime)
        self.assertIn('static final String OTHER_HERO_PATH = PROFILE_PATH + ".other-hero";', runtime)
        service = (JAVA / 'ClientService.java').read_text()
        self.assertIn('if(busy||storageBusy||reportExporting||blocked)return "Finish the current operation first.";', service)
        self.assertIn('refreshProfileState();publish();return message;', service)
        activity = (JAVA / 'ClientActivity.java').read_text()
        self.assertIn('switchHero=button("Switch hero slot",this::confirmSwitchHero);', activity)
        self.assertIn('if(!profileIdle(state))return;', activity[activity.index('private void confirmSwitchHero()'):][:200])


if __name__ == '__main__':
    unittest.main()
