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
    ByteArrayOutputStream output=new ByteArrayOutputStream(){
      @Override public void write(int value){super.write(value);Thread.yield();}
    };
    final InteractiveRfbClient[] ref=new InteractiveRfbClient[1];
    final String mode=args[0];
    InteractiveRfbClient client=new InteractiveRfbClient(new ByteArrayInputStream(Files.readAllBytes(Paths.get(args[1]))),output,(pixels,w,h,seq)->{
      try {
        if(mode.equals("basic")){
          ref[0].sendPointer(-5,900,1);ref[0].sendPointer(1,0,4);
          ref[0].sendKey('A',true);ref[0].sendKey(0xff52,true);ref[0].releaseAllInputs();
          ref[0].releaseAllInputs(); // A second release must not invent held keys/buttons.
        } else if(mode.equals("concurrent")) {
          Thread[] writers=new Thread[4];
          for(int i=0;i<4;i++){final int id=i;writers[i]=new Thread(()->{
            for(int n=0;n<50;n++)try{
              if(id==0)ref[0].requestFullUpdate();
              else if(id==1){ref[0].sendKey('X',true);ref[0].sendKey('X',false);}
              else ref[0].sendPointer(id,0,n%2==0?1:0);
            }catch(IOException e){throw new IllegalStateException(e);}
          });writers[i].start();}
          for(Thread thread:writers)thread.join();ref[0].releaseAllInputs();
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
        self.assertEqual([struct.pack('>BBHHHH', 3, 0, 0, 0, 2, 2), pointer(1, 0, 1),
                          pointer(4, 1, 0), key(65, 1), key(0xff52, 1), key(65, 0),
                          key(0xff52, 0), pointer(0, 1, 0), struct.pack('>BBHHHH', 3, 1, 0, 0, 2, 2)], messages)

    def test_input_and_refresh_writes_do_not_interleave(self):
        messages = self.messages(self.run_harness('concurrent'))
        self.assertEqual(52, sum(m[0] == 3 for m in messages))
        self.assertEqual(100, sum(m[0] == 4 for m in messages))
        self.assertEqual(100, sum(m[0] == 5 for m in messages))
        for message in messages:
            if message[0] == 4:
                self.assertIn(message, [struct.pack('>BBHI', 4, x, 0, 88) for x in (0, 1)])
            if message[0] == 5:
                self.assertIn(message, [struct.pack('>BBHH', 5, x, 1, 0) for x in (0, 1)])

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
