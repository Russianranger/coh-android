"""Compile the actual bounded contact-view state machine on the host JVM."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT/'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientRuntime.java'


class ContactCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = SOURCE.read_text()
        start = source.index('    private static final class ContactCaptureWindow {')
        opening = source.index('{', start)
        depth = 1
        end = opening + 1
        while depth:
            depth += (source[end] == '{') - (source[end] == '}')
            end += 1
        production = source[start:end]
        cls.folder = tempfile.TemporaryDirectory(prefix='coh-contact-capture-')
        cls.path = Path(cls.folder.name)
        host = '''public final class ContactCaptureHost {
PRODUCTION
static final String SESSION="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
static void need(boolean value){if(!value)throw new AssertionError();}
static ContactCaptureWindow opened(){
 ContactCaptureWindow w=new ContactCaptureWindow();need(w.request(SESSION,664,1,1000,40));return w;
}
static void three(ContactCaptureWindow w,long time,long sequence){
 for(int i=0;i<3;i++)need(w.accept(SESSION,664,1,time+i*1000,sequence+i));
}
public static void main(String[] args){
 switch(args[0]){
 case "fresh":{
  ContactCaptureWindow w=opened();need(!w.canRequest(1001));
  three(w,1001,41);need(w.count()==3&&w.batch()==1&&w.canRequest(3001));
  need(!w.accept(SESSION,664,1,4001,44));break;
 }
 case "identity":{
  ContactCaptureWindow w=opened();
  need(!w.accept("bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",664,1,1001,41));
  need(!w.accept(SESSION,665,1,1001,41));need(!w.accept(SESSION,664,2,1001,41));
  need(w.count()==0);three(w,1001,41);break;
 }
 case "freshness":{
  ContactCaptureWindow w=opened();
  need(!w.accept(SESSION,664,1,1000,41));need(!w.accept(SESSION,664,1,1001,40));
  need(w.accept(SESSION,664,1,1001,41));
  need(!w.accept(SESSION,664,1,2001,41));need(!w.accept(SESSION,664,1,2000,42));
  need(w.accept(SESSION,664,1,2001,42));need(w.count()==2);break;
 }
 case "expiry":{
  ContactCaptureWindow w=opened();need(w.accept(SESSION,664,1,1001,41));
  need(!w.accept(SESSION,664,1,121001,42));need(w.canRequest(121001));
  need(w.request(SESSION,664,1,121001,100));
  need(!w.accept(SESSION,664,1,121002,42));three(w,121002,101);need(w.batch()==2);break;
 }
 case "capacity":{
  ContactCaptureWindow w=opened();three(w,1001,41);
  need(w.request(SESSION,664,1,4000,60));three(w,4001,61);
  need(w.request(SESSION,664,1,7000,80));three(w,7001,81);
  need(w.batch()==3&&!w.canRequest(10000));need(!w.request(SESSION,664,1,10000,100));break;
 }
 case "invalid":{
  ContactCaptureWindow w=new ContactCaptureWindow();
  need(!w.request(null,664,1,1000,40));need(!w.request("invalid",664,1,1000,40));
  need(!w.request(SESSION,0,1,1000,40));need(!w.request(SESSION,4294967296L,1,1000,40));
  need(!w.request(SESSION,664,2,1000,40));need(!w.request(SESSION,664,1,-1,40));
  need(!w.request(SESSION,664,1,Long.MAX_VALUE,40));need(!w.request(SESSION,664,1,1000,-1));
  need(w.batch()==0&&w.canRequest(1000));break;
 }
 case "rollback":{
  ContactCaptureWindow w=opened();three(w,1001,41);
  need(!w.canRequest(3000));need(!w.request(SESSION,664,1,3000,60));
  need(w.request(SESSION,664,1,3001,60));need(!w.accept(SESSION,664,1,2001,61));break;
 }
 default:throw new AssertionError("unknown scenario");
 }
}
}'''.replace('PRODUCTION', production)
        (cls.path/'ContactCaptureHost.java').write_text(host)
        subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                        '-d', str(cls.path), str(cls.path/'ContactCaptureHost.java')],
                       check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def scenario(self, name):
        subprocess.run(['java', '-cp', str(self.path), 'ContactCaptureHost', name],
                       check=True, capture_output=True, text=True)

    def test_three_fresh_views_complete_one_request(self): self.scenario('fresh')
    def test_foreign_session_pid_or_character_never_counts(self): self.scenario('identity')
    def test_pre_request_duplicate_and_tightly_spaced_views_rejected(self): self.scenario('freshness')
    def test_expired_request_can_retry_without_accepting_old_frames(self): self.scenario('expiry')
    def test_request_and_frame_counts_are_bounded(self): self.scenario('capacity')
    def test_invalid_identity_clocks_and_watermarks_rejected(self): self.scenario('invalid')
    def test_clock_rollback_cannot_start_or_fill_another_request(self): self.scenario('rollback')


if __name__ == '__main__': unittest.main()
