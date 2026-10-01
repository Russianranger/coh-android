#!/usr/bin/env python3
"""Exercise shipped input mapping and serialized RFB events without an Android device."""
from pathlib import Path
import importlib.util
import os
import shutil
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
HARNESS = r'''
import io.github.russianranger.cohclientinteractive.*;
import java.io.*;
import java.nio.file.*;
public class InputHarness {
  static void check(boolean ok) { if (!ok) throw new AssertionError(); }
  public static void main(String[] args) throws Exception {
    if (args[0].equals("mapping")) {
      check(ClientInput.map(99,300,1000,600,800,600,false)==null);
      ClientInput.Point left=ClientInput.map(100,0,1000,600,800,600,false);
      check(left.x==0 && left.y==0);
      ClientInput.Point center=ClientInput.map(500,300,1000,600,800,600,false);
      check(center.x==400 && center.y==300);
      check(ClientInput.map(900,300,1000,600,800,600,false)==null);
      ClientInput.Point drag=ClientInput.map(2000,-100,1000,600,800,600,true);
      check(drag.x==799 && drag.y==0);
      check(ClientInput.map(100,99,800,800,800,600,false)==null);
      check(ClientInput.map(100,100,800,800,800,600,false).y==0);
      check(ClientInput.map(Float.NaN,100,800,600,800,600,true)==null);
      check(ClientInput.map(100,100,800,600,5000,600,true)==null);
      check(ClientInput.map(1023.9f,767.9f,1024,768,1024,768,false).x==1023);
      check(ClientInput.axis(0.1f)==0 && ClientInput.axis(-0.18f)==0);
      check(ClientInput.axis(1)==1 && ClientInput.axis(-1)==-1 && ClientInput.axis(Float.NaN)==0);
      check(ClientInput.validText("COHINPUT") && !ClientInput.validText("login\n"));
      check(!ClientInput.validText(new String(new char[33]).replace('\0','a')));
      check(!ClientInput.validText("") && !ClientInput.validText("\u00e9"));
      check(ClientInput.unicodeKeysym('A')==65 && ClientInput.unicodeKeysym(0x20ac)==0x010020ac);
      check(ClientInput.unicodeKeysym(0xd800)==0 && ClientInput.unicodeKeysym('\n')==0);
      System.out.println("mapping passed"); return;
    }
    final java.util.concurrent.CountDownLatch neutralSent=new java.util.concurrent.CountDownLatch(1);
    final java.util.concurrent.CountDownLatch commandKeySent=new java.util.concurrent.CountDownLatch(1);
    ByteArrayOutputStream output=new ByteArrayOutputStream(){
      private int flushed;
      @Override public void write(int value){super.write(value);Thread.yield();}
      @Override public synchronized void flush(){
        byte[] bytes=toByteArray();
        if(bytes.length-flushed==6 && bytes[flushed]==5 && bytes[flushed+1]==0)neutralSent.countDown();
        if(bytes.length-flushed==8 && bytes[flushed]==4 && bytes[flushed+1]==1)commandKeySent.countDown();
        flushed=bytes.length;
      }
    };
    final InteractiveRfbClient[] ref=new InteractiveRfbClient[1];
    final String mode=args[0];
    InteractiveRfbClient client=new InteractiveRfbClient(new ByteArrayInputStream(Files.readAllBytes(Paths.get(args[1]))),output,(pixels,w,h,seq)->{
      try {
        if(mode.equals("basic")){
          ref[0].sendPointer(-5,900,1);ref[0].sendPointer(1,0,4);
          ref[0].sendKey('A',true);ref[0].sendKey(0xff52,true);ref[0].releaseAllInputs();
          ref[0].releaseAllInputs(); // A second release must not invent held keys/buttons.
        } else if(mode.startsWith("walking_")) {
          ClientInput.KeyOwners owners=new ClientInput.KeyOwners();
          ClientInput.WalkingKeys walking=new ClientInput.WalkingKeys();
          ClientInput.KeySender sender=(key,down)->{try{ref[0].sendKey(key,down);return true;}
            catch(IOException failure){throw new IllegalStateException(failure);}};
          if(mode.equals("walking_hysteresis")) {
            walking.update(1,-1,false,owners,sender); // Menu/recovery does not move the character.
            walking.update(0,-0.34f,true,owners,sender);
            walking.update(0,-0.35f,true,owners,sender);
            walking.update(0,-1,true,owners,sender);
            walking.update(0,-0.25f,true,owners,sender);
            walking.update(0,-0.19f,true,owners,sender);
            walking.update(0.5f,-0.5f,true,owners,sender);
            walking.update(-0.5f,0.5f,true,owners,sender); // Opposites release before replacement.
            walking.update(Float.NaN,Float.POSITIVE_INFINITY,true,owners,sender);
          } else if(mode.equals("walking_shared_owners")) {
            owners.press(42,'w',sender); // Hardware keyboard and stick share one remote W.
            walking.update(0,-1,true,owners,sender);
            owners.press(120001,'w',sender); // Touch pad becomes its third owner.
            owners.press(120001,'w',sender); // Holding a control does not repeat key-down.
            owners.release(42,sender);walking.update(0,0,true,owners,sender);
            owners.release(120001,sender);
            owners.press(99,' ',sender);owners.press(120005,' ',sender);
            owners.release(99,sender);owners.release(120005,sender);
          } else if(mode.equals("walking_disable_and_reset")) {
            walking.update(1,-1,true,owners,sender);
            walking.update(1,-1,false,owners,sender); // Save/recovery/focus gate releases both keys.
            walking.update(1,-1,false,owners,sender);
            walking.update(1,-1,true,owners,sender);
            walking.reset();owners.clear();ref[0].releaseAllInputs(); // Activity lifecycle release.
            walking.update(1,-1,true,owners,sender); // Fresh ownership after focus/session restart.
            walking.update(0,0,true,owners,sender);
          } else if(mode.equals("walking_rejected_press")) {
            ClientInput.KeySender rejected=(key,down)->false;
            owners.press(42,'w',rejected);check(!owners.contains(42));
            owners.press(42,'w',sender);check(owners.contains(42));owners.release(42,sender);
          } else if(mode.equals("walking_rejected_stick_retry")) {
            final int[] attempts={0};
            ClientInput.KeySender rejectFirst=(key,down)->{
              attempts[0]++;return attempts[0]>1 && sender.send(key,down);
            };
            walking.update(0,-1,true,owners,rejectFirst);check(!owners.contains(110001));
            walking.update(0,-1,true,owners,rejectFirst);check(owners.contains(110001));
            walking.update(0,-1,true,owners,rejectFirst);check(attempts[0]==2);
            walking.update(0,0,true,owners,rejectFirst);check(!owners.contains(110001));
            check(attempts[0]==3);
          }
        } else if(mode.equals("save_logout")) {
          long before=System.nanoTime();ref[0].sendSaveLogout(ref[0].inputEpoch());
          check(System.nanoTime()-before>=3_000_000_000L);
        } else if(mode.equals("return_ground") || mode.equals("return_ground_held")) {
          if(mode.equals("return_ground_held")) ref[0].sendKey(0xffe3,true);
          long before=System.nanoTime();ref[0].sendReturnToSafeGround(ref[0].inputEpoch());
          check(System.nanoTime()-before>=2_000_000_000L);
        } else if(mode.equals("cancel_logout") || mode.equals("cancel_return_ground")) {
          final long epoch=ref[0].inputEpoch();final boolean[] cancelled={false};
          Thread pending=new Thread(()->{try{if(mode.equals("cancel_return_ground"))ref[0].sendReturnToSafeGround(epoch);else ref[0].sendSaveLogout(epoch);}
            catch(InteractiveRfbClient.InputCancelledException expected){cancelled[0]=true;}
            catch(IOException error){throw new IllegalStateException(error);}});
          pending.start();check(commandKeySent.await(1,java.util.concurrent.TimeUnit.SECONDS));
          ref[0].cancelPendingInput();pending.join(1000);check(!pending.isAlive()&&cancelled[0]);
          ref[0].releaseAllInputs();
        } else if(mode.equals("concurrent")) {
          Thread[] writers=new Thread[4];
          for(int i=0;i<4;i++){final int id=i;writers[i]=new Thread(()->{
            for(int n=0;n<8;n++)try{
              if(id==0)ref[0].requestFullUpdate();
              else if(id==1){ref[0].sendKey('X',true);ref[0].sendKey('X',false);}
              else ref[0].sendPointer(id,0,n%2==0?1:0);
            }catch(IOException e){throw new IllegalStateException(e);}
          });writers[i].start();}
          for(Thread thread:writers)thread.join();ref[0].releaseAllInputs();
        } else if(mode.equals("settle")){
          long before=System.nanoTime();ref[0].sendPointer(1,1,1);
          check(System.nanoTime()-before>=280_000_000L);
          long pressed=System.nanoTime();ref[0].sendPointer(1,1,0);
          check(System.nanoTime()-pressed<200_000_000L); // queued touch-up never inherits the prepress wait
          before=System.nanoTime();ref[0].sendKey('A',true);
          check(System.nanoTime()-before>=280_000_000L);
          ref[0].sendKey('A',false);
          ref[0].sendPointer(1,1,1);before=System.nanoTime();
          ref[0].sendPointer(0,1,1);ref[0].sendPointer(0,1,0);
          check(System.nanoTime()-before<200_000_000L); // drag and release stay immediate
        } else if(mode.equals("ordered_dialog")){
          java.util.concurrent.ExecutorService worker=java.util.concurrent.Executors.newSingleThreadExecutor();
          try{
            worker.submit(()->{try{ref[0].sendPointer(1,1,1);}catch(IOException e){throw new IllegalStateException(e);}});
            worker.submit(()->{try{ref[0].sendPointer(1,1,0);}catch(IOException e){throw new IllegalStateException(e);}});
            // App-owned dialog focus loss orders its release after the valid target tap.
            worker.submit(()->{try{ref[0].releaseAllInputs();}catch(IOException e){throw new IllegalStateException(e);}});
            worker.submit(()->{try{ref[0].sendKey('A',true);ref[0].sendKey('A',false);}
              catch(IOException e){throw new IllegalStateException(e);}}).get(3,java.util.concurrent.TimeUnit.SECONDS);
          }finally{worker.shutdownNow();}
        } else if(mode.equals("cancel")){
          final long epoch=ref[0].inputEpoch();final boolean[] cancelled={false};
          Thread pending=new Thread(()->{try{ref[0].sendPointer(1,1,1,epoch);}
            catch(InteractiveRfbClient.InputCancelledException expected){cancelled[0]=true;}
            catch(IOException error){throw new IllegalStateException(error);}});
          pending.start();check(neutralSent.await(1,java.util.concurrent.TimeUnit.SECONDS));
          ref[0].cancelPendingInput();pending.join(1000);check(!pending.isAlive()&&cancelled[0]);
          ref[0].releaseAllInputs();
        } else if(mode.equals("stale")){
          long epoch=ref[0].inputEpoch();ref[0].cancelPendingInput();int cancelled=0;
          try{ref[0].sendPointer(1,1,1,epoch);}catch(InteractiveRfbClient.InputCancelledException expected){cancelled++;}
          try{ref[0].sendKey('A',true,epoch);}catch(InteractiveRfbClient.InputCancelledException expected){cancelled++;}
          check(cancelled==2);ref[0].sendKey('B',true);ref[0].cancelPendingInput();ref[0].releaseAllInputs();
        } else if(mode.equals("cancel_key")){
          ref[0].sendPointer(1,1,1);ref[0].sendPointer(1,1,0);
          final long epoch=ref[0].inputEpoch();final boolean[] cancelled={false};
          Thread pending=new Thread(()->{try{ref[0].sendKey('A',true,epoch);}
            catch(InteractiveRfbClient.InputCancelledException expected){cancelled[0]=true;}
            catch(IOException error){throw new IllegalStateException(error);}});
          pending.start();Thread.sleep(40);ref[0].cancelPendingInput();pending.join(1000);
          check(!pending.isAlive()&&cancelled[0]);ref[0].releaseAllInputs();
        } else if(mode.equals("bounds")){
          int rejected=0;
          try{ref[0].sendPointer(0,0,8);}catch(IOException expected){rejected++;}
          try{ref[0].sendKey(0,true);}catch(IOException expected){rejected++;}
          for(int i=0;i<64;i++)ref[0].sendKey(32+i,true);
          try{ref[0].sendKey(200,true);}catch(IOException expected){rejected++;}
          check(rejected==3);ref[0].releaseAllInputs();
        }
      }catch(Exception e){throw new IllegalStateException(e);}
    });ref[0]=client;
    int early=0;try{client.sendKey('A',true);}catch(IOException expected){early++;}
    try{client.sendPointer(0,0,0);}catch(IOException expected){early++;}check(early==2&&output.size()==0);
    try{client.run();}catch(EOFException expected){}
    client.close();
    try{client.sendKey('B',true);throw new AssertionError();}catch(IOException expected){}
    Files.write(Paths.get(args[2]),output.toByteArray());System.out.println("wire passed");
  }
}
'''


class InputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.java = shutil.which('java') or os.environ.get('ATLAS_JAVA')
        if not cls.java:
            raise unittest.SkipTest('JDK required')
        javac = shutil.which('javac') or os.environ.get('ATLAS_JAVAC')
        compiler = [javac] if javac else [cls.java, '-m', 'jdk.compiler/com.sun.tools.javac.Main']
        cls.tmp = tempfile.TemporaryDirectory(prefix='coh-interaction-input-')
        cls.path = Path(cls.tmp.name)
        harness = cls.path / 'InputHarness.java'
        harness.write_text(HARNESS)
        subprocess.run(compiler + ['--release', '8', '-d', str(cls.path), str(SOURCE / 'ClientInput.java'),
                                  str(SOURCE / 'InteractiveRfbClient.java'), str(harness)],
                       check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'tmp'):
            cls.tmp.cleanup()

    def run_harness(self, mode):
        fixture, response = self.path / 'fixture', self.path / 'response'
        fixture.write_bytes(b'RFB 003.008\n\1\1' + bytes(4) + struct.pack('>HH', 2, 2)
                            + bytes(16) + bytes(4) + b'\0\0\0\1' + struct.pack('>HHHHi', 0, 0, 2, 2, 0)
                            + bytes(16))
        result = subprocess.run([self.java, '-cp', str(self.path), 'InputHarness', mode,
                                 str(fixture), str(response)], check=True, capture_output=True, text=True, timeout=10)
        return response.read_bytes()[46:] if mode != 'mapping' else result.stdout

    @staticmethod
    def messages(wire):
        sizes = {3: 10, 4: 8, 5: 6}
        result = []
        while wire:
            size = sizes[wire[0]]
            if len(wire) < size:
                raise AssertionError('Truncated/interleaved RFB input')
            result.append(wire[:size])
            wire = wire[size:]
        return result

    def test_letterbox_edges_resize_drag_and_text_bounds(self):
        self.assertIn('mapping passed', self.run_harness('mapping'))

    def test_exact_network_order_pointer_keyboard_and_release(self):
        messages = self.messages(self.run_harness('basic'))
        key = lambda code, down: struct.pack('>BBHI', 4, down, 0, code)
        pointer = lambda mask, x, y: struct.pack('>BBHH', 5, mask, x, y)
        self.assertEqual([struct.pack('>BBHHHH', 3, 0, 0, 0, 2, 2), pointer(0, 0, 1), pointer(1, 0, 1),
                          pointer(4, 1, 0), key(65, 1), key(0xff52, 1), key(65, 0),
                          key(0xff52, 0), pointer(0, 1, 0), struct.pack('>BBHHHH', 3, 1, 0, 0, 2, 2)], messages)

    def walking_keys(self, mode):
        messages = self.messages(self.run_harness(mode))
        return [(struct.unpack('>I', message[4:])[0], message[1]) for message in messages if message[0] == 4]

    def test_walking_deadzone_hysteresis_diagonal_reversal_and_nonfinite_release(self):
        self.assertEqual([(ord(key), down) for key, down in
            [('w',1),('w',0),('w',1),('d',1),('w',0),('d',0),('s',1),('a',1),('s',0),('a',0)]],
            self.walking_keys('walking_hysteresis'))

    def test_stick_touch_keyboard_and_jump_share_keys_without_duplicates_or_early_release(self):
        self.assertEqual([(ord('w'),1),(ord('w'),0),(ord(' '),1),(ord(' '),0)],
                         self.walking_keys('walking_shared_owners'))

    def test_walking_disable_and_lifecycle_reset_release_keys_and_allow_fresh_ownership(self):
        self.assertEqual([(ord(key), down) for _ in range(3) for key, down in
                         [('w',1),('d',1),('w',0),('d',0)]],
                         self.walking_keys('walking_disable_and_reset'))

    def test_rejected_key_press_does_not_leave_an_unsent_local_owner(self):
        self.assertEqual([(ord('w'),1),(ord('w'),0)], self.walking_keys('walking_rejected_press'))

    def test_rejected_stick_press_retries_on_same_sample_without_repeating_accepted_press(self):
        self.assertEqual([(ord('w'),1),(ord('w'),0)], self.walking_keys('walking_rejected_stick_retry'))

    def test_save_logout_sends_exact_ordinary_chat_command_without_ctrl_a(self):
        messages = self.messages(self.run_harness('save_logout'))
        keys = [0xff0d] + list(map(ord, '/quittologin')) + [0xff0d]
        self.assertEqual([struct.pack('>BBHI', 4, down, 0, key) for key in keys for down in (1, 0)],
                         messages[1:-1])

    def test_save_logout_cancellation_releases_partial_command_key(self):
        messages = self.messages(self.run_harness('cancel_logout'))
        self.assertEqual([struct.pack('>BBHI', 4, down, 0, 0xff0d) for down in (1, 0)], messages[1:-1])

    def test_return_to_safe_ground_sends_exact_access_zero_stuck_command(self):
        keys = [0xff0d] + list(map(ord, '/stuck')) + [0xff0d]
        expected = [struct.pack('>BBHI', 4, down, 0, key) for key in keys for down in (1, 0)]
        self.assertEqual(expected, self.messages(self.run_harness('return_ground'))[1:-1])
        held = self.messages(self.run_harness('return_ground_held'))[1:-1]
        self.assertEqual([struct.pack('>BBHI', 4, down, 0, 0xffe3) for down in (1, 0)] + expected, held)

    def test_return_to_safe_ground_cancellation_releases_partial_command_key(self):
        messages = self.messages(self.run_harness('cancel_return_ground'))
        self.assertEqual([struct.pack('>BBHI', 4, down, 0, 0xff0d) for down in (1, 0)], messages[1:-1])

    def test_input_and_refresh_writes_do_not_interleave(self):
        messages = self.messages(self.run_harness('concurrent'))
        self.assertEqual(10, sum(m[0] == 3 for m in messages))
        self.assertEqual(16, sum(m[0] == 4 for m in messages))
        self.assertEqual(17, sum(m[0] == 5 for m in messages))
        for message in messages:
            if message[0] == 4:
                self.assertIn(message, [struct.pack('>BBHI', 4, x, 0, 88) for x in (0, 1)])
            if message[0] == 5:
                self.assertIn(message, [struct.pack('>BBHH', 5, x, 1, 0) for x in (0, 1)])

    def test_preposition_then_short_click_focus_settle_and_drag(self):
        messages = self.messages(self.run_harness('settle'))
        pointer = lambda mask, x, y: struct.pack('>BBHH', 5, mask, x, y)
        self.assertEqual([pointer(0, 1, 1), pointer(1, 1, 1), pointer(0, 1, 1)], messages[1:4])
        self.assertEqual([pointer(1, 1, 1), pointer(1, 0, 1), pointer(0, 0, 1)], messages[-4:-1])

    def test_own_text_dialog_ordered_release_preserves_queued_focus_tap(self):
        messages = self.messages(self.run_harness('ordered_dialog'))
        self.assertEqual([struct.pack('>BBHH', 5, mask, 1, 1) for mask in (0, 1, 0)]
                         + [struct.pack('>BBHI', 4, down, 0, 65) for down in (1, 0)], messages[1:-1])

    def test_finish_cancels_delayed_press_after_neutral_move(self):
        messages = self.messages(self.run_harness('cancel'))
        self.assertEqual([struct.pack('>BBHH', 5, 0, 1, 1)], messages[1:-1])

    def test_queued_stale_epoch_writes_nothing_and_emergency_release_bypasses_epoch(self):
        messages = self.messages(self.run_harness('stale'))
        self.assertEqual([struct.pack('>BBHI', 4, 1, 0, 66), struct.pack('>BBHI', 4, 0, 0, 66)], messages[1:-1])

    def test_focus_settle_can_cancel_before_first_character(self):
        messages = self.messages(self.run_harness('cancel_key'))
        self.assertFalse(any(message[0] == 4 for message in messages))
        self.assertEqual([0, 1, 0], [message[1] for message in messages if message[0] == 5])

    def test_invalid_inputs_and_held_key_limit_fail_without_writes(self):
        messages = self.messages(self.run_harness('bounds'))
        self.assertEqual(130, len(messages))
        self.assertEqual(64, sum(m[0] == 4 and m[1] == 1 for m in messages))
        self.assertEqual(64, sum(m[0] == 4 and m[1] == 0 for m in messages))


# The new input sender must also preserve the accepted decoder's hostile-wire bounds.
_spec = importlib.util.spec_from_file_location('interactive_decoder_regression',
                                             ROOT / 'tools/android/presentation/test_rfb.py')
_decoder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_decoder)
_decoder.CORE = SOURCE / 'InteractiveRfbClient.java'
_decoder.HARNESS = _decoder.HARNESS.replace('io.github.russianranger.cohpresentation',
                                           'io.github.russianranger.cohclientinteractive').replace(
                                               'RfbClient', 'InteractiveRfbClient')


class InteractiveDecoderTests(_decoder.RfbDecoderTests):
    pass


if __name__ == '__main__':
    unittest.main()
