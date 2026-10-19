#!/usr/bin/env python3
"""Host regression for the observed Android document-drawer occlusion.

The captured Android 13 accessibility state exposed both the open drawer and a
filename behind it. These controls verify driver event selection only, never
reporting a host simulation as Android execution or a real import.
"""
from pathlib import Path
from types import SimpleNamespace
import json
import copy
import tempfile
import hashlib
import subprocess
import re
import xml.etree.ElementTree as ET
from unittest.mock import patch
from emulator_check import (Check, PACKAGE, scene_pixels, settled_preview, viewport_contract,
                            map_report_contract, installed_apk_contract, guest_resources_contract,
                            activity_inventory, retained_launcher, large_scene_contract,
                            complete_scene_contract, SCENE_INSPECTION_FIELDS,
                            idle_preview_contract, initial_map_contract,
                            fresh_active_root_capture, CAPTURE_HELPER_PACKAGE)

FILE = 'native-test-donor.apk'
BACKGROUND = f'<node package="com.google.android.documentsui" text="{FILE}" bounds="[189,899][583,956]"/>'
DRAWER = '<node package="com.google.android.documentsui" text="Open from"/><node package="com.google.android.documentsui" text="Downloads" resource-id="android:id/title" bounds="[168,552][714,603]"/>'
APP = f'<node package="{PACKAGE}" text="Import launcher APK"/>'


class Driver(Check):
    def __init__(self, path, frames):
        super().__init__(SimpleNamespace(output=path))
        self.frames = iter(ET.fromstring('<hierarchy>'+x+'</hierarchy>') for x in frames)
        self.commands = []
    def tap(self, label):
        self.control = label
    def dump(self):
        return next(self.frames)
    def adb(self, *args, check=True):
        self.commands.append(args)


class AnrDriver(Check):
    def record(self, name, **details):
        self.proofs.append({'host_fixture':True,'check':name,**details})
    def __init__(self, path, frames, lastanr='', events=''):
        super().__init__(SimpleNamespace(output=path))
        self.lastanr, self.events = lastanr, events
        self.frames = iter(x.encode() for x in frames)
        self.commands = []
    def text(self, *args, check=True):
        return self.lastanr if 'lastanr' in args else self.events
    def adb(self, *args, check=True):
        if args[:2] == ('exec-out', 'cat'):
            return SimpleNamespace(stdout=next(self.frames), stderr=b'', returncode=0)
        if args[:3] == ('shell', 'input', 'tap'):
            self.commands.append(args)
        return SimpleNamespace(stdout=b'', stderr=b'', returncode=0)


class CaptureDriver(Check):
    def __init__(self, path, captures, lastanr='', events='', crashes='', clear_code=0, helper=None):
        super().__init__(SimpleNamespace(output=path))
        self.captures=iter(captures)
        self.lastanr,self.events,self.crashes=lastanr,events,crashes
        self.clear_code=clear_code
        self.remote=b'<hierarchy><node text="stale"/></hierarchy>'
        self.dump_count=self.read_count=self.clear_count=0
        self.helper=helper;self.helper_count=self.helper_read_count=0
        if helper is not None:self._capture_helper_ready=True
    def capture_active_root(self,prefix):
        if self.helper is None:raise RuntimeError('Host fixture has no fresh helper capture')
        return super().capture_active_root(prefix)
    def text(self, *args, check=True):
        if 'lastanr' in args:return self.lastanr
        if 'events' in args:return self.events
        return self.crashes() if callable(self.crashes) else self.crashes
    def record(self, name, **details):
        self.proofs.append({'host_fixture':True,'check':name,**details})
    def adb(self, *args, check=True):
        if args[:3]==('shell','rm','-f'):
            self.clear_count+=1
            if not self.clear_code:self.remote=None
            return SimpleNamespace(returncode=self.clear_code,stdout=b'',stderr=b'')
        if args[:3]==('shell','uiautomator','dump'):
            self.dump_count+=1
            code,stdout,stderr,payload=next(self.captures)
            if payload is not None:self.remote=payload
            return SimpleNamespace(returncode=code,stdout=stdout,stderr=stderr)
        if args[:2]==('exec-out','cat'):
            self.read_count+=1
            return SimpleNamespace(returncode=int(self.remote is None),stdout=self.remote or b'',stderr=b'')
        if args[:4]==('shell','am','instrument','-w'):
            self.helper_count+=1
            return SimpleNamespace(returncode=self.helper.get('returncode',0),stdout=self.helper['diagnostic'].encode(),stderr=b'')
        if args[:3]==('exec-out','run-as',CAPTURE_HELPER_PACKAGE):
            self.helper_read_count+=1
            return SimpleNamespace(returncode=self.helper.get('readcode',0),stdout=self.helper['raw'],stderr=b'')
        if args[:4]==('shell','run-as',CAPTURE_HELPER_PACKAGE,'rm'):
            return SimpleNamespace(returncode=self.helper.get('removecode',0),stdout=b'',stderr=b'')
        raise AssertionError('Unexpected fixture command: '+repr(args))


def capture_controls(path):
    fresh=b'<hierarchy><node text="fresh"/></hierarchy>'
    idle=(1,b'ERROR: could not get idle state.',b'',b'<hierarchy><node text="stale"/></hierarchy>')
    null=(0,b'',b'ERROR: null root node returned by UiTestAutomationBridge.',None)
    good=(0,b'UI hierchary dumped to: /data/local/tmp/combined-ui.xml',b'',fresh)
    count=0
    def driver(name, frames, **kwargs):
        return CaptureDriver(path/name,frames,**kwargs)
    def rejected(value, exception=RuntimeError):
        nonlocal count
        try:value.capture_ui()
        except exception:count+=1;return
        raise AssertionError('Failed capture was admitted')
    with patch('emulator_check.time.sleep'):
        for index,failure in enumerate((idle,null)):
            value=driver('retry-'+str(index),[failure,good]);raw,root=value.capture_ui()
            assert raw==fresh and root.find('node').get('text')=='fresh'
            assert (value.dump_count,value.clear_count,value.read_count)==(2,2,1)
            assert value.proofs[0]['stale_xml_used'] is False
            count+=1
        exhausted=driver('exhausted',[idle]*3);rejected(exhausted)
        assert exhausted.dump_count==3 and exhausted.clear_count==3 and exhausted.read_count==0
        assert len(list(exhausted.args.output.glob('*-dump.stdout')))==3
        for name,stdout,stderr in [('unknown',b'unknown failure',b''),('empty',b'',b''),('permission',b'',b'Permission denied')]:
            value=driver(name,[(1,stdout,stderr,fresh),good]);rejected(value)
            assert value.dump_count==1 and value.read_count==0
            assert (value.args.output/'ui-capture-1-attempt-1-dump.stdout').read_bytes()==stdout
            assert (value.args.output/'ui-capture-1-attempt-1-dump.stderr').read_bytes()==stderr
        for name,kwargs in [('native-anr',{'lastanr':'ANR in '+PACKAGE}),
                            ('native-event',{'events':'am_crash: [0,123,'+PACKAGE+',1]'}),
                            ('native-crash',{'crashes':'Process: '+PACKAGE})]:
            value=driver(name,[idle,good],**kwargs);rejected(value)
            assert value.dump_count==1 and value.read_count==0
        value=driver('late-crash',[idle,good]);value.crashes=lambda:'Process: '+PACKAGE if value.dump_count>1 else ''
        rejected(value);assert value.dump_count==2 and not value.proofs
        value=driver('clear-failure',[good],clear_code=1);rejected(value)
        assert value.dump_count==0 and value.read_count==0
        value=driver('missing-fresh-file',[(0,b'',b'',None)]);rejected(value)
        assert value.read_count==1
        value=driver('malformed-fresh-file',[(0,b'',b'',b'<broken')]);rejected(value,ET.ParseError)
        assert value.dump_count==1
        nonce='a'*32
        raw=('<hierarchy rotation="0" capture-nonce="'+nonce+'" capture-method="fresh-ui-automation-active-root-without-global-idle" capture-root-attempts="2" capture-root-wait-ms="50" capture-snapshot-attempts="2" capture-discarded-partial-trees="1"><node text="fresh"/></hierarchy>').encode()
        fields={'status':'passed','nonce':nonce,'file':'snapshot-'+nonce+'.xml','sha256':hashlib.sha256(raw).hexdigest(),
                'bytes':str(len(raw)),'nodes':'1','started_elapsed_ms':'10','completed_elapsed_ms':'100','root_attempts':'2','root_wait_ms':'50',
                'snapshot_attempts':'2','discarded_partial_trees':'1','total_nodes_visited':'4','partial_xml_reused':'false'}
        def diagnostic(values):return '\n'.join('INSTRUMENTATION_RESULT: '+k+'='+v for k,v in values.items())+'\nINSTRUMENTATION_CODE: -1\n'
        helper={'raw':raw,'diagnostic':diagnostic(fields)}
        with patch('emulator_check.uuid.uuid4',return_value=SimpleNamespace(hex=nonce)):
            value=driver('fresh-without-idle',[idle]*3,helper=helper)
            captured,root=value.capture_ui()
            assert captured==raw and root.find('node').get('text')=='fresh'
            assert (value.dump_count,value.clear_count,value.read_count,value.helper_count,value.helper_read_count)==(3,3,0,1,1)
            assert value.proofs[-1]['stale_xml_used'] is False and value.proofs[-1]['global_idle_required'] is False
            count+=1
            for key,bad in [('nonce','b'*32),('sha256','0'*64),('file','snapshot-old.xml'),('bytes','1'),('nodes','8193'),('started_elapsed_ms','101'),('status','failed'),('root_attempts','0'),('root_attempts','33'),('root_wait_ms','3001'),('root_wait_ms','91'),('root_attempts','1'),('snapshot_attempts','4'),('discarded_partial_trees','0'),('total_nodes_visited','0'),('total_nodes_visited','16385'),('partial_xml_reused','true')]:
                changed=dict(fields);changed[key]=bad
                value=driver('helper-'+key,[idle]*3,helper={'raw':raw,'diagnostic':diagnostic(changed)})
                rejected(value,AssertionError)
                assert value.read_count==0 and value.helper_count==1
            value=driver('helper-command-failure',[idle]*3,helper={**helper,'returncode':1});rejected(value,AssertionError)
            assert value.helper_read_count==0
            failed='INSTRUMENTATION_RESULT: status=failed\nINSTRUMENTATION_RESULT: error=IOException: Fresh active root unavailable\nINSTRUMENTATION_CODE: 0\n'
            value=driver('helper-root-unavailable',[idle]*3,helper={**helper,'diagnostic':failed})
            rejected(value,AssertionError);assert value.helper_read_count==0 and not value.proofs
            value=driver('helper-read-failure',[idle]*3,helper={**helper,'readcode':1});rejected(value,AssertionError)
            value=driver('helper-xml-stale-nonce',[idle]*3,helper={**helper,'raw':raw.replace(nonce.encode(),b'b'*32)})
            rejected(value,AssertionError)
            value=driver('helper-late-app-crash',[idle]*3,helper=helper)
            value.crashes=lambda:'Process: '+PACKAGE if value.helper_count else ''
            rejected(value);assert not value.proofs
        next_nonce='b'*32;next_raw=raw.replace(nonce.encode(),next_nonce.encode())
        next_fields={**fields,'nonce':next_nonce,'file':'snapshot-'+next_nonce+'.xml','sha256':hashlib.sha256(next_raw).hexdigest(),'bytes':str(len(next_raw))}
        with patch('emulator_check.uuid.uuid4',side_effect=[SimpleNamespace(hex=nonce),SimpleNamespace(hex=next_nonce)]):
            value=driver('direct-only-after-verified-idle',[idle]*3,helper=helper)
            value.capture_ui();value.helper={'raw':next_raw,'diagnostic':diagnostic(next_fields)}
            actual,root=value.capture_ui()
            assert actual==next_raw and root.get('capture-nonce')==next_nonce
            assert value.dump_count==3 and value.helper_count==2 and value.helper_read_count==2
            assert value.proofs[0]['capture_mode']=='fallback_after_three_recorded_idle_failures'
            assert value.proofs[1]['capture_mode']=='direct_after_verified_idle_starvation'
            assert all(row['shell_idle_starvation_previously_verified'] and not row['stale_xml_used'] for row in value.proofs)
            count+=1
        fresh_active_root_capture(raw,diagnostic(fields),nonce);count+=1
        for value in [raw.replace(b'rotation="0"',b'rotation="9"'),b'',b'x'*(8<<20)]:
            mutated=dict(fields);mutated['sha256']=hashlib.sha256(value).hexdigest();mutated['bytes']=str(len(value))
            try:fresh_active_root_capture(value,diagnostic(mutated),nonce)
            except AssertionError:count+=1
            else:raise AssertionError('Invalid active-root hierarchy admitted')
    return count


def root_acquisition_controls(path):
    """Execute the exact helper acquisition block with bounded clock/root stubs."""
    source=Path(__file__).with_name('UiSnapshotInstrumentation.java').read_text()
    constants=re.search(r'private static final int ROOT_ATTEMPTS=\d+, ROOT_WAIT_MS=\d+;',source).group()
    begin=source.index('            // ROOT_ACQUISITION_BEGIN')
    end=source.index('            // ROOT_ACQUISITION_END',begin)
    block=source[begin:end]
    harness=r'''
import java.io.IOException;
public final class RootAcquisitionTest {
 CONSTANTS
 static final class SystemClock {
  static long now;static boolean frozen;
  static long elapsedRealtime(){return now;}
  static void sleep(long value){if(!frozen)now+=value;}
 }
 static final class Automation {
  int calls,available;long perCall;boolean failure;
  Object getRootInActiveWindow(){calls++;SystemClock.now+=perCall;if(failure)throw new IllegalStateException("unavailable fixture");return calls>=available&&available>0?new Object():null;}
 }
 static long[] run(Automation automation)throws Exception {
  long started=0;Object root=null;int rootAttempts=0;long rootWait=0;
  BLOCK
  return new long[]{rootAttempts,rootWait};
 }
 static Automation fixture(int available,long delay,boolean frozen){SystemClock.now=0;SystemClock.frozen=frozen;Automation a=new Automation();a.available=available;a.perCall=delay;return a;}
 public static void main(String[]args)throws Exception {
  int checks=0;long[] got=run(fixture(1,0,false));if(got[0]!=1||got[1]!=0)throw new AssertionError();checks++;
  got=run(fixture(4,0,false));if(got[0]!=4||got[1]!=300)throw new AssertionError();checks++;
  Automation missing=fixture(0,0,false);try{run(missing);throw new AssertionError();}catch(IOException e){if(missing.calls>32||SystemClock.now>3000)throw new AssertionError();}checks++;
  Automation frozen=fixture(0,0,true);try{run(frozen);throw new AssertionError();}catch(IOException e){if(frozen.calls!=32)throw new AssertionError();}checks++;
  try{run(fixture(1,3001,false));throw new AssertionError();}catch(IOException expected){}checks++;
  Automation broken=fixture(1,0,false);broken.failure=true;try{run(broken);throw new AssertionError();}catch(IllegalStateException expected){if(broken.calls!=1)throw new AssertionError();}checks++;
  System.out.print(checks);
 }
}
'''.replace('CONSTANTS',constants).replace('BLOCK',block)
    path.mkdir(parents=True);java=path/'RootAcquisitionTest.java';java.write_text(harness)
    compiled=subprocess.run(['java','com.sun.tools.javac.Main','-d',str(path),str(java)],capture_output=True,text=True,timeout=30)
    assert compiled.returncode==0,compiled.stderr
    result=subprocess.run(['java','-cp',str(path),'RootAcquisitionTest'],capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr
    return int(result.stdout)


def snapshot_retry_controls(path):
    """Execute the exact whole-tree retry loop; Android traversal is stubbed."""
    source=Path(__file__).with_name('UiSnapshotInstrumentation.java').read_text()
    constants='\n'.join(re.findall(r'private static final int (?:MAX_NODES|ROOT_ATTEMPTS|SNAPSHOT_ATTEMPTS)=[^;]+;',source))
    begin=source.index('            for(snapshotAttempts=1;')
    end=source.index('            if(raw==null)',begin)
    block=source[begin:end]
    assert 'if(child==null)throw new SnapshotChangedException();' in source
    harness=r'''
import java.io.*;
public final class SnapshotRetryTest {
 CONSTANTS
 int nodes,totalNodes,failures;boolean unexpected;long work;
 static int buffers,recycled;static BoundedOutput lastBuffer;
 static final class SnapshotChangedException extends IOException {}
 static final class AccessibilityNodeInfo {void recycle(){recycled++;}}
 static final class UiAutomation {AccessibilityNodeInfo getRootInActiveWindow(){return new AccessibilityNodeInfo();}}
 static final class SystemClock {static long now;static long elapsedRealtime(){return now;}static void sleep(long t){now+=t;}}
 static final class BoundedOutput extends OutputStream {final ByteArrayOutputStream bytes=new ByteArrayOutputStream();BoundedOutput(){buffers++;lastBuffer=this;}public void write(int n){bytes.write(n);}}
 static final class Point {int x=1080,y=1920;}
 static final class Rect {void set(int a,int b,int c,int d){}}
 static final class Display {void getRealSize(Point p){}int getRotation(){return 0;}}
 static final class WindowManager {Display getDefaultDisplay(){return new Display();}}
 static final class Context {static final String WINDOW_SERVICE="window";Object getSystemService(String n){return new WindowManager();}}
 static final class XmlSerializer {BoundedOutput output;void setOutput(BoundedOutput o,String e){output=o;}void startDocument(String e,boolean b){}void startTag(String n,String t){}void endTag(String n,String t){}void endDocument(){}void flush(){}}
 static final class Xml {static XmlSerializer newSerializer(){return new XmlSerializer();}}
 final Rect displayBounds=new Rect();Context getTargetContext(){return new Context();}String nonce="fixture";
 void attr(XmlSerializer x,String k,Object v){}
 void node(XmlSerializer xml,AccessibilityNodeInfo root,int index,int depth)throws Exception {
  nodes++;totalNodes++;SystemClock.now+=work;
  xml.output.write((failures>0?"partial":"complete").getBytes("UTF-8"));
  if(unexpected)throw new IOException("not a traversal-change fixture");
  if(failures>0){failures--;throw new SnapshotChangedException();}
 }
 byte[] run()throws Exception {
  SystemClock.now=0;buffers=recycled=0;long started=0;AccessibilityNodeInfo root=null;UiAutomation automation=new UiAutomation();
  int rootAttempts=0,snapshotAttempts=0;long rootWait=0;BoundedOutput output=new BoundedOutput();byte[] raw=null;
  BLOCK
  if(raw==null)throw new AssertionError();
  if(buffers!=1||recycled!=snapshotAttempts||totalNodes!=snapshotAttempts)throw new AssertionError("ownership/attempts");
  return raw;
 }
 static SnapshotRetryTest fixture(int failures,boolean unexpected,long work){SnapshotRetryTest t=new SnapshotRetryTest();t.failures=failures;t.unexpected=unexpected;t.work=work;return t;}
 public static void main(String[]args)throws Exception {
  int checks=0;
  for(int failures=0;failures<3;failures++){SnapshotRetryTest t=fixture(failures,false,0);String value=new String(t.run(),"UTF-8");if(!value.equals("complete")||recycled!=failures+1)throw new AssertionError("partial tree retained");checks++;}
  try{fixture(3,false,0).run();throw new AssertionError();}catch(SnapshotChangedException expected){if(recycled!=3||buffers!=1||lastBuffer.bytes.size()!=0)throw new AssertionError();}checks++;
  try{fixture(1,false,3001).run();throw new AssertionError();}catch(SnapshotChangedException expected){if(recycled!=1||buffers!=1)throw new AssertionError();}checks++;
  try{fixture(0,true,0).run();throw new AssertionError();}catch(IOException expected){if(recycled!=1||buffers!=1)throw new AssertionError();}checks++;
  System.out.print(checks);
 }
}
'''.replace('CONSTANTS',constants).replace('BLOCK',block)
    path.mkdir(parents=True);java=path/'SnapshotRetryTest.java';java.write_text(harness)
    built=subprocess.run(['java','com.sun.tools.javac.Main','-d',str(path),str(java)],capture_output=True,text=True,timeout=30)
    assert built.returncode==0,built.stderr
    result=subprocess.run(['java','-cp',str(path),'SnapshotRetryTest'],capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr
    return int(result.stdout)


def return_locator_controls(path):
    """Replay the captured landscape clip and Return-above-viewport case."""
    class Locator(Check):
        def __init__(self,name,frames):
            super().__init__(SimpleNamespace(output=path/name));self.frames=iter(frames);self.commands=[]
        def dump(self):return ET.fromstring(next(self.frames))
        def adb(self,*args,check=True):self.commands.append(args)
    clip='<node package="'+PACKAGE+'" class="android.widget.ScrollView" content-desc="Native client controls" bounds="[0,63][1920,635]">BODY</node>'
    def frame(body):return '<hierarchy>'+clip.replace('BODY',body)+'</hierarchy>'
    missing=frame('<node package="'+PACKAGE+'" text="Connect local server" enabled="true" bounds="[0,68][495,194]"/>')
    partial=frame('<node package="'+PACKAGE+'" text="Return to launcher" enabled="true" bounds="[0,0][1920,123]"/>')
    visible=frame('<node package="'+PACKAGE+'" text="Return to launcher" enabled="true" bounds="[0,63][1920,189]"/>')
    with patch('emulator_check.time.sleep'):
        value=Locator('found-start',[missing,visible]);node=value.tap('Return to launcher',activate=False,toward_start=True)
        assert node.get('bounds')=='[0,63][1920,189]'
        assert value.commands==[('shell','input','swipe',960,177,960,521,'250')]
        value=Locator('direct-interop-default',[missing,visible]);value.tap('Return to launcher',activate=False)
        assert value.commands==[('shell','input','swipe',960,177,960,521,'250')]
        value=Locator('partial-center-outside',[partial,visible]);value.tap('Return to launcher',toward_start=True)
        assert value.commands==[('shell','input','swipe',960,177,960,521,'250'),('shell','input','tap',960,126)]
        value=Locator('bounded-missing',[missing]*11)
        try:value.tap('Return to launcher',activate=False,toward_start=True)
        except RuntimeError:pass
        else:raise AssertionError('Missing Return accepted')
        assert len(value.commands)==10 and all(c==('shell','input','swipe',960,177,960,521,'250') for c in value.commands)
    return 4


def viewport_protocol_controls(path):
    """Replay Thor dimensions and reject stale/secret-bearing public reports."""
    count = 0
    preview = {'viewport_policy': {'schema':'coh-native-viewport-v1', 'maximum_controls_percent':60,
        'minimum_aspect':.25, 'maximum_aspect':8, 'maximum_dimension':16384,
        'host_width':1920, 'host_height':469},
        'input_area':{'left':0,'top':611,'width':1920,'height':469,'shown':True,'surface_ready':True},
        'native':{'width':1920,'height':469}, 'preview_is_server_world':False}
    viewport_contract(preview);count+=1
    # The actual failed EGL height must fail even if its outer host is larger.
    def reject(function, value):
        nonlocal count
        try:function(value)
        except AssertionError:count+=1;return
        raise AssertionError('Invalid public report was admitted')
    for mutate in (
        lambda v:v['input_area'].update(height=137),
        lambda v:v['native'].update(height=137),
        lambda v:v['input_area'].update(width=16385),
        lambda v:v['input_area'].update(width=True),
        lambda v:v['input_area'].update(surface_ready=False),
        lambda v:v['viewport_policy'].update(host_height=100),
        lambda v:v.update(preview_is_server_world=True),
    ):
        value=copy.deepcopy(preview);mutate(value);reject(viewport_contract,value)
    fitted=copy.deepcopy(preview);fitted['input_area'].update(width=1096,height=137)
    fitted['native'].update(width=1096,height=137);viewport_contract(fitted);count+=1
    mapping_fields = ('phase stage last_status last_command_valid last_command last_payload_bits last_byte_aligned '
        'accepted_messages rejected_messages malformed unsupported scene_prefixes entity_prefixes disconnects suspends timeouts '
        'last_decoded_bytes scene_decoded_bytes scene_structures').split()
    udp_fields = ('state link_state sockets_opened sockets_closed datagrams_sent datagrams_received peer_rejects '
        'truncated empty malformed unsupported send_would_block interrupted io_errors receive_budget_exhausted '
        'suspends resumes cancellations timeouts last_system_error').split()
    link_fields = ('sent received retransmits acknowledged duplicates malformed queue_limits fragment_expirations '
        'timeouts unsupported tx_pending rx_pending fragment_groups storage_bytes codec_bytes high_water_retained_bytes '
        'owned_retained_bytes owned_high_water_bytes').split()
    top_fields = ('local_development_auth server_identity_bound generation selection_generation db_phase map_phase '
        'last_status attempts character_lists character_choices map_handoffs policy_rejections failures suspends '
        'cancellations opened_sockets closed_sockets terminal_failure terminal_db_phase terminal_map_phase').split()
    protocol = dict.fromkeys(top_fields,0)
    protocol.update(schema='coh-native-local-numeric-v1',phase='SCENE_INCOMPLETE',authserver_authenticated=False,
        live_world_rendered=False,map_protocol=dict.fromkeys(mapping_fields,0))
    protocol['map_protocol']['udp']=dict.fromkeys(udp_fields,0)
    protocol['map_protocol']['scene_inspection']=dict.fromkeys(SCENE_INSPECTION_FIELDS,0)
    protocol['map_protocol']['scene_failure']=dict(stage=0,bit_offset=0,status=0)
    protocol['map_protocol']['udp']['link']=dict.fromkeys(link_fields,0)
    protocol['map_protocol']['udp']['link']['decode']=dict.fromkeys(
        ('failure_kind','compressed_bytes','declared_raw_bytes','output_budget','normalized_command','command_valid'),0)
    map_report_contract(protocol);count+=1
    idle_preview_contract({'phase':'IDLE'});count+=1
    for value in ({'phase':'CLOSED'}, {'phase':'IDLE','attempts':0},
                  {'phase':'IDLE','password':'private'}, {'phase':'IDLE','map_protocol':{}},
                  {'phase':'IDLE','authserver_authenticated':True}, None):
        reject(idle_preview_contract,value)
    initial=copy.deepcopy(protocol);initial['phase']='CHARACTERS_READY'
    initial_map_contract(initial);count+=1
    for mutate in (
        lambda v:v.update(phase='IDLE'),
        lambda v:v['map_protocol'].update(scene_structures=1),
        lambda v:v['map_protocol'].update(last_decoded_bytes=32),
        lambda v:v['map_protocol'].update(scene_decoded_bytes=32),
        lambda v:v['map_protocol']['scene_inspection'].update(defs=1),
        lambda v:v['map_protocol']['scene_failure'].update(stage=4,status=2),
        lambda v:v['map_protocol']['udp']['link']['decode'].update(payload='private'),
    ):
        value=copy.deepcopy(initial);mutate(value);reject(initial_map_contract,value)
    for mutate in (
        lambda v:v.update(password='must never appear'),
        lambda v:v['map_protocol'].update(packet_body='must never appear'),
        lambda v:v['map_protocol']['udp']['link'].update(cookie=42),
        lambda v:v.update(terminal_map_phase=-1),
        lambda v:v['map_protocol'].update(last_status=True),
        lambda v:v['map_protocol']['udp'].update(datagrams_received=-1),
        lambda v:v.update(authserver_authenticated=True),
        lambda v:v.update(live_world_rendered=True),
        lambda v:v['map_protocol'].update(last_decoded_bytes=4194305),
        lambda v:v['map_protocol'].update(scene_decoded_bytes=True),
        lambda v:v['map_protocol']['udp']['link'].update(owned_retained_bytes=1),
        lambda v:v['map_protocol']['udp']['link'].update(owned_high_water_bytes=4194305),
        lambda v:v['map_protocol']['udp']['link']['decode'].update(payload='private'),
        lambda v:v['map_protocol']['udp']['link']['decode'].update(failure_kind=5),
        lambda v:v['map_protocol']['udp']['link']['decode'].update(compressed_bytes=16385),
        lambda v:v['map_protocol']['udp']['link']['decode'].update(declared_raw_bytes=4294967300),
        lambda v:v['map_protocol']['udp']['link']['decode'].update(output_budget=4194305),
        lambda v:v['map_protocol']['udp']['link']['decode'].update(output_budget=1),
        lambda v:v['map_protocol']['udp']['link']['decode'].update(command_valid=2),
        lambda v:v['map_protocol']['udp']['link']['decode'].update(normalized_command=6),
        lambda v:v['map_protocol']['udp']['link']['decode'].update(output_budget=4194304,command_valid=1,normalized_command=7),
        lambda v:v['map_protocol']['udp']['link']['decode'].update(failure_kind=True),
        lambda v:v['map_protocol'].update(scene_structures=True),
        lambda v:v['map_protocol']['scene_inspection'].update(asset_path='private'),
        lambda v:v['map_protocol']['scene_inspection'].update(defs=-1),
        lambda v:v['map_protocol']['scene_inspection'].update(new_world=2),
        lambda v:v['map_protocol']['scene_inspection'].update(files=1025),
        lambda v:v['map_protocol']['scene_inspection'].update(present_files=1),
        lambda v:v['map_protocol']['scene_inspection'].update(defs=65537),
        lambda v:v['map_protocol']['scene_inspection'].update(children=262145),
        lambda v:v['map_protocol']['scene_inspection'].update(roots=65537),
        lambda v:v['map_protocol']['scene_inspection'].update(properties=65537),
        lambda v:v['map_protocol']['scene_inspection'].update(swaps=65537),
        lambda v:v['map_protocol']['scene_inspection'].update(raw_matrices=327681),
        lambda v:v['map_protocol']['scene_inspection'].update(strings=1048577),
        lambda v:v['map_protocol']['scene_inspection'].update(string_bytes=3145729),
        lambda v:v['map_protocol']['scene_inspection'].update(work_units=1048577),
        lambda v:v['map_protocol']['scene_inspection'].update(max_def_id=65536),
        lambda v:v['map_protocol']['scene_inspection'].update(max_root_id=1048576),
        lambda v:v['map_protocol']['scene_inspection'].update(footer_file_count=1025),
        lambda v:v['map_protocol']['scene_inspection'].update(footer_active_roots=65537),
        lambda v:v['map_protocol']['scene_inspection'].update(footer_defs_crc=4294967296),
        lambda v:v['map_protocol']['scene_inspection'].update(prefix_bits=1),
        lambda v:v['map_protocol']['scene_inspection'].update(consumed_bits=33554433),
        lambda v:v['map_protocol']['scene_inspection'].update(consumed_bits=True),
        lambda v:v['map_protocol']['scene_failure'].update(packet_body='private'),
        lambda v:v['map_protocol']['scene_failure'].update(stage=13),
        lambda v:v['map_protocol']['scene_failure'].update(bit_offset=33554433),
        lambda v:v['map_protocol']['scene_failure'].update(status=8),
    ):
        value=copy.deepcopy(protocol);mutate(value);reject(map_report_contract,value)
    protocol['map_protocol']['udp']['last_system_error']=-11
    map_report_contract(protocol);count+=1
    peer=dict(scripted_source_layout=True,real_server_interoperability=False,large_body_fixture=True,
        scene_tail_parsed=False,scene_compressed=True,scene_ordered=False,scene_decoded_bytes=131072,
        scene_payload_bits=1048576,scene_compressed_bytes=200,decoded_budget_bytes=4194304)
    expanded=copy.deepcopy(protocol);mapping=expanded['map_protocol'];link=mapping['udp']['link']
    mapping.update(last_payload_bits=1048576,last_decoded_bytes=131072,scene_decoded_bytes=131072)
    link.update(owned_retained_bytes=0,owned_high_water_bytes=131072)
    link['decode'].update(failure_kind=0,compressed_bytes=200,declared_raw_bytes=131072,
        output_budget=4194304,normalized_command=6,command_valid=1)
    large_scene_contract(expanded,peer);count+=1
    for mutate in (
        lambda v:v.update(phase='FAILED'),
        lambda v:v.update(terminal_failure=1),
        lambda v:v['map_protocol'].update(last_payload_bits=131072),
        lambda v:v['map_protocol'].update(scene_decoded_bytes=16384),
        lambda v:v['map_protocol']['udp']['link'].update(owned_retained_bytes=131072),
        lambda v:v['map_protocol']['udp']['link']['decode'].update(declared_raw_bytes=131068),
        lambda v:v['map_protocol']['udp']['link']['decode'].update(compressed_bytes=201),
        lambda v:v['map_protocol']['udp']['link']['decode'].update(failure_kind=2),
    ):
        value=copy.deepcopy(expanded);mutate(value)
        reject(lambda report:large_scene_contract(report,peer),value)
    for change in ({'real_server_interoperability':True},{'scene_tail_parsed':True},
                   {'large_body_fixture':False},{'scene_compressed':False},{'scene_ordered':True},
                   {'scene_decoded_bytes':16384},{'scene_payload_bits':True},
                   {'scene_compressed_bytes':16384},{'decoded_budget_bytes':8388608}):
        value=copy.deepcopy(peer);value.update(change)
        reject(lambda fixture:large_scene_contract(expanded,fixture),value)
    complete=copy.deepcopy(expanded);complete['server_identity_bound']=1
    complete_map=complete['map_protocol']
    complete_map.update(scene_structures=1,stage=10)
    complete_map['scene_inspection'].update(new_world=1,files=1,present_files=1,defs=1,children=1,roots=1,
        raw_matrices=2,strings=1,string_bytes=4,work_units=20,footer_file_count=1,footer_active_roots=1,
        prefix_bits=80,consumed_bits=1048576)
    complete_peer=copy.deepcopy(peer)
    complete_peer.update(scene_tail_parsed=True,scene_assets_resolved=False,scene_crc_verified=False,
        scene_expected_counts={k:complete_map['scene_inspection'][k] for k in ('files present_files defs children '
            'roots properties swaps raw_matrices packed_matrices footer_file_count footer_active_roots '
            'footer_defs_crc footer_refs_crc').split()})
    complete_scene_contract(complete,complete_peer);count+=1
    for mutate in (
        lambda v:v.update(server_identity_bound=0),
        lambda v:v['map_protocol'].update(entity_prefixes=1),
        lambda v:v['map_protocol'].update(scene_structures=0),
        lambda v:v['map_protocol'].update(stage=6),
        lambda v:v['map_protocol']['scene_inspection'].update(defs=2),
        lambda v:v['map_protocol']['scene_inspection'].update(consumed_bits=1048575),
        lambda v:v['map_protocol']['scene_inspection'].update(prefix_bits=1048576),
        lambda v:v['map_protocol']['scene_failure'].update(stage=4,status=2),
    ):
        value=copy.deepcopy(complete);mutate(value)
        reject(lambda report:complete_scene_contract(report,complete_peer),value)
    for change in ({'scene_tail_parsed':False},{'scene_assets_resolved':True},{'scene_crc_verified':True},
                   {'scene_expected_counts':{}},{'scene_expected_counts':{'account':'private'}}):
        value=copy.deepcopy(complete_peer);value.update(change)
        reject(lambda fixture:complete_scene_contract(complete,fixture),value)
    for key,wrong in (('files',True),('footer_file_count',2),('password',0)):
        value=copy.deepcopy(complete_peer);value['scene_expected_counts'][key]=wrong
        reject(lambda fixture:complete_scene_contract(complete,fixture),value)
    class ScrollDriver(Check):
        def __init__(self):
            super().__init__(SimpleNamespace(output=path/'scroll'))
            self.commands=[]
            self.frames=iter([
                '<node text="Native Fixture • level 1" enabled="true" bounds="[0,430][800,510]"/>',
                '<node text="Native Fixture • level 1" enabled="true" bounds="[0,180][800,260]"/>'])
        def dump(self):
            return ET.fromstring('<hierarchy><node package="'+PACKAGE+'" content-desc="Native client controls" bounds="[0,30][1920,400]">'+next(self.frames)+'</node></hierarchy>')
        def adb(self,*args,**kwargs):self.commands.append(args)
    scroll=ScrollDriver()
    with patch('emulator_check.time.sleep'):scroll.tap('Native Fixture',prefix=True)
    assert scroll.commands==[('shell','input','swipe',960,326,960,104,'250'),('shell','input','tap',400,220)]
    count+=1
    return count


def identity_resource_controls():
    count = 0
    identity = {'installed_apk_status':'ready','installed_apk':{'bytes':1000,'sha256':'a'*64}}
    def accepted(v):return installed_apk_contract(v,'a'*64,1000)
    def reject(function, value):
        nonlocal count
        try:function(value)
        except AssertionError:count+=1;return
        raise AssertionError('Invalid APK/resource report was admitted')
    accepted(identity);count+=1
    for state in ('pending','unavailable'):
        value={'installed_apk_status':state,'installed_apk':None}
        installed_apk_contract(value,'a'*64,1000,require_ready=False);count+=1
        reject(accepted,value)
    for change in (
        {'bytes':True,'sha256':'a'*64}, {'bytes':0,'sha256':'a'*64},
        {'bytes':(25<<20)+1,'sha256':'a'*64}, {'bytes':1000,'sha256':'A'*64},
        {'bytes':1000,'sha256':'b'*64}, {'bytes':1000,'sha256':'a'*63},
        {'bytes':1000,'sha256':'a'*64,'path':'must stay private'},
    ):
        reject(accepted,{'installed_apk_status':'ready','installed_apk':change})
    reject(accepted,{'installed_apk_status':'ready','installed_apk':None})
    reject(accepted,{'installed_apk_status':'unknown','installed_apk':None})
    metrics=('rss_kib','peak_rss_kib','children_peak_rss_kib','cgroup_current_bytes','cgroup_max_bytes','cgroup_oom_kill_count')
    row=dict.fromkeys(metrics,None);row.update(stage='server_only_input_admission',boundary='entered',elapsed_ms=0)
    guest_resources_contract({'guest_resources':[]});count+=1
    guest_resources_contract({'guest_resources':[row]*32});count+=1
    populated=copy.deepcopy(row);populated.update(dict.fromkeys(metrics,1<<50))
    guest_resources_contract({'guest_resources':[populated]});count+=1
    reject(guest_resources_contract,{'guest_resources':[row]*33})
    for change in ({'pid':123},{'stage':'/private/path'},{'stage':'x'*121},{'boundary':'unknown'},
                   {'elapsed_ms':-1},{'elapsed_ms':True},{'rss_kib':-1},{'peak_rss_kib':True},
                   {'children_peak_rss_kib':.5},{'cgroup_current_bytes':(1<<50)+1}):
        value=copy.deepcopy(row);value.update(change);reject(guest_resources_contract,{'guest_resources':[value]})
    return count


def activity_controls():
    header='ACTIVITY MANAGER ACTIVITIES (dumpsys activity activities)\n'
    main=PACKAGE+'/.MainActivity';native=PACKAGE+'/.NativeClientActivity'
    live='  * Hist  #0: ActivityRecord{abc123 u0 '+main+' t41}\n'
    resumed='  ResumedActivity: ActivityRecord{abc123 u0 '+main+'} t41}\n'
    historical='  mLastPausedActivity: ActivityRecord{def456 u0 '+native+' t41 f}}\n'
    def parsed(text):return {**activity_inventory(header+text),'pid':1000}
    baseline=parsed(live+resumed)
    assert retained_launcher(baseline,parsed(live+resumed+resumed+historical))
    count=1
    brief=parsed(live.replace('* Hist  ','Hist  ').replace(main,PACKAGE+'/'+PACKAGE+'.MainActivity')+resumed)
    assert retained_launcher(baseline,brief);count+=1
    for changed in (
        live+resumed+' * Hist #1: ActivityRecord{def456 u0 '+native+' t41}\n',
        live+resumed+live.replace('abc123','eeee'),
        (live+resumed).replace('abc123','eeee'),
        live+resumed+live.replace('abc123','eeee').replace('t41','t99'),
        live+resumed.replace('abc123','def456').replace(main,native),
        live,
        live+resumed+' * Fin #0: ActivityRecord{def456 u0 '+native+' t41 f}}\n',
        live+resumed+' Stop #0: ActivityRecord{def456 u0 '+native+' t41}\n',
    ):
        assert not retained_launcher(baseline,parsed(changed));count+=1
    changed=parsed(live+resumed);changed['pid']=1001
    assert not retained_launcher(baseline,changed);count+=1
    for raw in ('', 'Permission denied', live+resumed, header+' * Hist #0: broken '+main,
                header+' * Hist #0: ActivityRecord{abc123 u0 '+main+'}\n'):
        try:activity_inventory(raw)
        except AssertionError:count+=1;continue
        raise AssertionError('Malformed Activity inventory was admitted')
    return count


def main():
    with tempfile.TemporaryDirectory(prefix='coh-driver-controls-') as temp:
        driver = Driver(Path(temp), [BACKGROUND+DRAWER, BACKGROUND, APP])
        driver.select_document('Import launcher APK', FILE)
        assert driver.commands == [('shell','input','tap',441,577), ('shell','input','tap',386,927)], 'Obscured filename was clicked before the foreground drawer root'
        trace = json.loads((Path(temp)/'picker-selection-history.json').read_text())
        assert trace[0]['drawer_open'] is True and trace[0]['selected_file'] is False
        assert trace[1]['selected_file'] is True
        direct = Driver(Path(temp), [BACKGROUND, APP])
        direct.select_document('Import launcher APK', FILE)
        assert direct.commands == [('shell','input','tap',386,927)]
        anr = '<hierarchy><node resource-id="android:id/alertTitle" text="Pixel Launcher isn&amp;apos;t responding"/><node resource-id="android:id/aerr_wait" text="Wait" bounds="[70,1024][1010,1150]"/></hierarchy>'.replace('isn&amp;apos;t', "isn't")
        external = AnrDriver(Path(temp), [anr, '<hierarchy>'+APP+'</hierarchy>'])
        external.dump()
        assert external.commands == [('shell','input','tap',540,1087)] and external.launcher_anrs == 1
        own = AnrDriver(Path(temp), [anr.replace('Pixel Launcher', 'CoH Native Combined')])
        try:
            own.dump()
            raise AssertionError('Native app ANR was admitted')
        except RuntimeError as failure:
            assert 'without dismissal' in str(failure) and not own.commands
        files = AnrDriver(Path(temp), [anr.replace('Pixel Launcher','Files'), '<hierarchy>'+APP+'</hierarchy>'], 'ANR in com.google.android.documentsui (com.google.android.documentsui/.files.FilesActivity)')
        files.dump()
        assert files.commands == [('shell','input','tap',540,1087)] and files.proofs[0]['external_component'] == 'com.google.android.documentsui'
        cpu_only = AnrDriver(Path(temp), [anr.replace('Pixel Launcher','Files'), '<hierarchy>'+APP+'</hierarchy>'], 'ANR in com.android.documentsui\nCPU usage: 1% '+PACKAGE)
        cpu_only.dump()
        assert cpu_only.commands == [('shell','input','tap',540,1087)]
        unknown = AnrDriver(Path(temp), [anr.replace('Pixel Launcher','Files')])
        try:
            unknown.dump()
            raise AssertionError('Unidentified Files ANR was admitted')
        except RuntimeError as failure:
            assert 'not positively identified' in str(failure) and not unknown.commands
        native_trace = AnrDriver(Path(temp), [anr], 'ANR in '+PACKAGE)
        try:
            native_trace.dump()
            raise AssertionError('Native app ANR trace was admitted')
        except RuntimeError as failure:
            assert 'Native app ANR' in str(failure) and not native_trace.commands
        from PIL import Image
        from io import BytesIO
        def png(image):
            out=BytesIO();image.save(out,format='PNG');return out.getvalue()
        area={'left':0,'top':872,'width':1080,'height':985,'shown':True,'surface_ready':True}
        shot=Image.new('RGB',(1080,1920),(0,0,0));shot.paste((255,255,255),(0,0,1080,872))
        proof,_=scene_pixels(png(shot),area)
        assert proof['passed'] is False and proof['bright_pixels']==0, 'White app header admitted a black actual Surface'
        shot.paste((17,19,23),(0,872,1080,1857));proof,_=scene_pixels(png(shot),area)
        assert proof['passed'] is False, 'Uniform GLES clear admitted without scene'
        texture=Image.new('RGB',(128,128));texture.putdata([(40+x,40+y,80) for y in range(128) for x in range(128)]);shot.paste(texture,(100,1000))
        proof,_=scene_pixels(png(shot),area)
        assert proof['passed'] is True and proof['surface_bounds_ltrb']==[0,872,1080,1857]
        native=dict(valid=True,failed=False,running=True,foreground=True,objects_released=False,frames=300,contexts_started=6,contexts_completed=5,gl_errors=0,tf_mismatches=0,world_visible_pixels=1,actor_visible_pixels=1,world_occludes_actor_pixels=1,actor_occludes_world_pixels=1,actor_changed_pixels=1,static_renderer=dict(gpu_bytes=1,tf_mismatches=0,visible_pixels=1))
        ready=dict(assets_verified=True,resumed=True,failure=None,report_write_failed=False,native=native)
        assert settled_preview(ready,290) is True
        native['objects_released']=True;assert settled_preview(ready,290) is False
        native['objects_released']=False;native['static_renderer']['gpu_bytes']=0;assert settled_preview(ready,290) is False
        native['static_renderer']['gpu_bytes']=1;assert settled_preview(ready,310) is False
        capture_checks=capture_controls(Path(temp)/'captures')
        acquisition_checks=root_acquisition_controls(Path(temp)/'root-acquisition')
        retry_checks=snapshot_retry_controls(Path(temp)/'snapshot-retry')
        return_checks=return_locator_controls(Path(temp)/'return-locator')
        viewport_protocol_checks=viewport_protocol_controls(Path(temp)/'viewport-protocol')
        identity_resource_checks=identity_resource_controls()
        activity_checks=activity_controls()
    print(json.dumps({'passed':True,'checks':17+capture_checks+acquisition_checks+retry_checks+return_checks+viewport_protocol_checks+identity_resource_checks+activity_checks,'capture_controls':capture_checks,
        'exact_helper_root_acquisition_stub_controls':acquisition_checks,
        'exact_helper_whole_snapshot_retry_stub_controls':retry_checks,'return_toward_start_controls':return_checks,
        'activity_inventory_controls':activity_checks,
        'identity_resource_controls':identity_resource_checks,
        'viewport_protocol_controls':viewport_protocol_checks,'scope':'Host regressions for document selection, strict fresh capture, native fault rejection, scene/viewport admission, bounded scrolling, exact APK identity and numeric protocol/resource privacy; no Android execution claim.'}))


if __name__ == '__main__':
    main()
