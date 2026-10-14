#!/usr/bin/env python3
"""Execute the shipped Java receipt predicates on hostile lifecycle receipts."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def method(source, signature):
    start = source.index(signature)
    brace = source.index('{', start)
    depth, end = 1, brace + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--java-home', type=Path)
    args = parser.parse_args()
    java_dir = Path(__file__).resolve().parents[1] / 'app/src/main/java/org/coh/integrationprobe'
    source = (java_dir / 'MainActivity.java').read_text()
    rules = (java_dir / 'ReceiptRules.java').read_text()
    root = args.output / 'java'
    package = root / 'org/coh/integrationprobe'
    package.mkdir(parents=True, exist_ok=True)
    (root / 'org/json').mkdir(parents=True, exist_ok=True)
    (package / 'ReceiptRules.java').write_text(rules)
    (root / 'org/json/JSONObject.java').write_text(r'''package org.json;
import java.util.*;
public class JSONObject {
 public final Map<String,Object> m=new HashMap<>();
 public JSONObject put(String k,Object v){m.put(k,v);return this;}
 public Object opt(String k){return m.get(k);}public boolean has(String k){return m.containsKey(k);}
 public boolean optBoolean(String k){return Boolean.TRUE.equals(m.get(k));}
 public long optLong(String k){return optLong(k,0);}public long optLong(String k,long d){Object v=m.get(k);return v instanceof Number?((Number)v).longValue():d;}
 public int optInt(String k){return (int)optLong(k);}
 public double optDouble(String k,double d){Object v=m.get(k);return v instanceof Number?((Number)v).doubleValue():d;}
 public JSONObject optJSONObject(String k){Object v=m.get(k);return v instanceof JSONObject?(JSONObject)v:null;}
 public JSONArray optJSONArray(String k){Object v=m.get(k);return v instanceof JSONArray?(JSONArray)v:null;}
}''')
    (root / 'org/json/JSONArray.java').write_text(r'''package org.json;
import java.util.*;public class JSONArray {
 public final List<Object> l=new ArrayList<>();public JSONArray put(Object v){l.add(v);return this;}
 public int length(){return l.size();}public JSONObject optJSONObject(int i){return i>=0&&i<l.size()&&l.get(i) instanceof JSONObject?(JSONObject)l.get(i):null;}
 public double optDouble(int i,double d){Object v=i>=0&&i<l.size()?l.get(i):null;return v instanceof Number?((Number)v).doubleValue():d;}
}''')
    harness = r'''package org.coh.integrationprobe;
import org.json.*;
public final class IntegrationUiCheck {
 static int checked;long generation=2;JSONObject background=new JSONObject();
 JSONArray audioRuns=new JSONArray(),transportRuns=new JSONArray(),nativeRuns=new JSONArray(),worldRuns=new JSONArray();
 static JSONObject o(Object... x){JSONObject o=new JSONObject();for(int i=0;i<x.length;i+=2)o.put((String)x[i],x[i+1]);return o;}
 static void check(boolean value,String label){checked++;if(!value)throw new AssertionError(label);}
 static JSONObject decode(){return o("passed",true,"result",0,"reference_compared",true,"reference_passed",true,"opened",true,"cleared",true,"eos",true,"streams",1,"sample_rate",44100,"channels",2,"frames",18168,"pcm_bytes",72672,"ov_read_calls",24,"compared_samples",36336,"failed",0,"maximum_sample_error",1);}
 static JSONObject audio(){return o("passed",true,"cancelled",false,"result",0,"backend_errors",0,"decode",decode(),"decoded_audio_played",true,"opened",true,"started",true,"stopped",true,"closed",true,"submitted_frames",512);}
 static JSONObject audioCancel(){return audio().put("passed",false).put("cancelled",true).put("result",1).put("run_id",7).put("started_after_event",90);}
 static JSONObject udp(){return o("passed",true,"cancelled",false,"expected_cancel",false,"session_failure",false,"result",0,"backend_errors",0,"opened",true,"closed",true,"sockets_opened",2,"sockets_closed",2,"blocked_polls",1,"interrupted_blocked_poll",0,"timeouts",0,"datagrams_sent",8,"datagrams_received",8,"clear_frames",4,"encrypted_frames",4,"expected_rejects",2,"byte_parity_checks",8,"decoded_payloads",8);}
 static JSONObject nativeProof(){return o("passed",true,"decode",decode(),"input_source",o("passed",true,"result",1,"failed",0,"checks",200),"transport",udp());}
 static JSONObject udpCancel(){return udp().put("cancelled",true).put("interrupted_blocked_poll",1).put("run_id",8).put("started_after_event",91);}
 static JSONObject world(){return o("java_obsolete",false,"session_failure",false,"expected_cancel",false,"engine_passed",true,"fixtures_valid",true,"baseline_cpu_passed",true,"baseline_gpu_passed",true,"context_created",true,"objects_released",true,"cancelled",false,"gl_errors",0,"source_frames_consumed",450,"frames",450,"stationary_mismatches",0,"camera_determinism_mismatches",0,"same_camera_image_mismatches",0,"interactive_transform_mismatches",0);}
 static IntegrationUiCheck valid(){IntegrationUiCheck t=new IntegrationUiCheck();t.background=o("pause_sequence",100,"stop_sequence",101,"resume_sequence",102,"input_cleared",true,"audio_started_before_pause",true,"transport_started_before_pause",true,"interrupted_audio_run_id",7,"interrupted_transport_run_id",8);
  t.audioRuns.put(audioCancel()).put(audio().put("started_after_event",103).put("foreground_at_completion",true));t.transportRuns.put(udpCancel());t.nativeRuns.put(nativeProof().put("foreground_at_completion",true).put("started_after_event",104));t.worldRuns.put(world().put("generation",2).put("foreground_at_completion",true).put("started_after_event",105));return t;}
 public static void main(String[] args){
  check(ReceiptRules.decodePassed(decode()),"Native decoded reference metadata");
  for(String key:new String[]{"passed","reference_compared","reference_passed","opened","cleared","eos"}){JSONObject d=decode();d.m.remove(key);check(!ReceiptRules.decodePassed(d),"Missing decoder receipt "+key);check(!ReceiptRules.decodePassed(decode().put(key,"true")),"Typed decoder receipt "+key);}
  for(String key:new String[]{"sample_rate","channels","frames","pcm_bytes","streams","failed"}){JSONObject d=decode();d.m.remove(key);check(!ReceiptRules.decodePassed(d),"Missing decode dimension "+key);check(!ReceiptRules.decodePassed(decode().put(key,"1")),"Typed decode dimension "+key);}
  check(!ReceiptRules.decodePassed(decode().put("maximum_sample_error",2)),"Sample mismatch rejected");check(!ReceiptRules.decodePassed(decode().put("maximum_sample_error",Double.NaN)),"NaN decoder error rejected");
  check(!ReceiptRules.audioRunFailed(audio()),"Complete on-device decoded playback");check(!ReceiptRules.audioRunFailed(audioCancel()),"Clean interruption allowed");
  JSONObject early=audioCancel().put("decoded_audio_played",false).put("opened",false).put("started",false).put("stopped",false).put("closed",false).put("submitted_frames",0);
  check(!ReceiptRules.audioRunFailed(early),"Early clean cancellation permits retry");check(!ReceiptRules.audioInterrupted(early,7,100),"Queued playback never proves Home interruption");
  check(ReceiptRules.audioRunFailed(audio().put("decoded_audio_played",false)),"Reference fallback cannot pass");check(ReceiptRules.audioRunFailed(audio().put("backend_errors",1)),"Successful flag cannot erase backend errors");
  check(ReceiptRules.audioRunFailed(audioCancel().put("result",0)),"Late cancellation requires complete playback");JSONObject late=audioCancel().put("result",0).put("completed_clips",3).put("requested_clips",3);check(!ReceiptRules.audioRunFailed(late),"Clean late cancel remains retryable");check(!ReceiptRules.audioInterrupted(late,7,100),"Late cancellation never proves Home");
  for(String key:new String[]{"opened","started","stopped","closed"}){check(!ReceiptRules.audioInterrupted(audioCancel().put(key,false),7,100),"Home requires audio "+key);check(ReceiptRules.audioRunFailed(audioCancel().put("result",0).put("completed_clips",3).put("requested_clips",3).put(key,"true")),"Late cleanup flag typed "+key);}
  check(!ReceiptRules.audioInterrupted(audioCancel(),99,100),"Unrelated cancelled audio rejected");check(!ReceiptRules.audioInterrupted(audioCancel(),7,89),"Cancelled audio must start before pause");
  check(!ReceiptRules.transportRunFailed(udp()),"Clean real sockets closed");check(!ReceiptRules.transportRunFailed(udpCancel()),"Native blocked poll cancellation");
  JSONObject timeout=udp().put("passed",false).put("result",1).put("timeouts",1);check(!ReceiptRules.transportRunFailed(timeout),"Bounded timeout retryable");check(!ReceiptRules.transportInterrupted(timeout,8,100),"Timeout cannot prove Home");
  JSONObject queued=udp().put("passed",false).put("result",1).put("blocked_polls",0);check(!ReceiptRules.transportRunFailed(queued),"Clean cancellation before first blocked poll is retryable");check(!ReceiptRules.transportInterrupted(queued,8,100),"Queued socket wait cannot prove Home");
  check(ReceiptRules.transportRunFailed(udp().put("sockets_closed",1)),"Descriptor leak sticky");check(ReceiptRules.transportRunFailed(udpCancel().put("backend_errors",1)),"Cancelled socket backend error sticky");
  check(!ReceiptRules.transportInterrupted(udpCancel().put("blocked_polls",0),8,100),"Queued wait cannot qualify Home");check(!ReceiptRules.transportInterrupted(udpCancel(),99,100),"Unrelated UDP cancellation rejected");
  check(ReceiptRules.nativeCheckPassed(nativeProof()),"Decoder/input and actual ordinary loopback checks");
  JSONObject ordinaryCancel=nativeProof().put("passed",false).put("transport",udp().put("passed",false).put("result",1).put("cancelled",true).put("expected_cancel",true));
  check(!ReceiptRules.nativeCheckFailed(ordinaryCancel,true),"Stale foreground explicit native socket cancellation is retryable");check(ReceiptRules.nativeCheckFailed(ordinaryCancel,false),"Current normal checks cannot be excused");
  check(ReceiptRules.nativeCheckFailed(nativeProof().put("passed",false),true),"Foreground transition cannot hide ordinary failure");
  ordinaryCancel.optJSONObject("transport").put("session_failure",true);check(ReceiptRules.nativeCheckFailed(ordinaryCancel,true),"Explicit cancel cannot erase source/backend failure");
  ordinaryCancel.optJSONObject("transport").put("session_failure",false).put("sockets_closed",1);check(ReceiptRules.nativeCheckFailed(ordinaryCancel,true),"Ordinary cancelled check must release all owned sockets");
  ordinaryCancel.optJSONObject("transport").put("sockets_opened",0).put("sockets_closed",0).put("opened",false).put("closed",false);check(!ReceiptRules.nativeCheckFailed(ordinaryCancel,true),"Explicit stale prestart normal check owns no sockets");
  ordinaryCancel.optJSONObject("transport").put("cancelled",false);check(ReceiptRules.nativeCheckFailed(ordinaryCancel,true),"Typed explicit cancellation evidence required");
  check(ReceiptRules.worldEnginePassed(world()),"Baseline source renderer");for(String key:new String[]{"fixtures_valid","baseline_cpu_passed","baseline_gpu_passed","context_created","objects_released"}){check(!ReceiptRules.worldEnginePassed(world().put(key,false)),"World requires "+key);check(!ReceiptRules.worldEnginePassed(world().put(key,"true")),"Typed world field "+key);}
  for(String key:new String[]{"gl_errors","stationary_mismatches","camera_determinism_mismatches","same_camera_image_mismatches"})check(!ReceiptRules.worldEnginePassed(world().put(key,1)),"Renderer mismatch sticky "+key);
  check(!ReceiptRules.worldEnginePassed(world().put("source_frames_consumed",0)),"Unconsumed source input cannot qualify");check(!ReceiptRules.worldEnginePassed(world().put("cancelled",true)),"Cancelled surface cannot qualify engine");
  check(!ReceiptRules.worldEnginePassed(world().put("java_obsolete",true)),"Queued obsolete success cannot qualify");JSONObject current=world().put("generation",2).put("width",600).put("height",400).put("render_token",6).put("foreground_at_completion",true);
  check(ReceiptRules.worldCurrentPassed(current,2,600,400,6),"Exact current renderer epoch");check(!ReceiptRules.worldCurrentPassed(current,2,600,400,7),"Stale same-size reset token cannot qualify");check(!ReceiptRules.worldCurrentPassed(current,3,600,400,6),"Recreated generation cannot qualify stale renderer");check(!ReceiptRules.worldCurrentPassed(current,2,601,400,6),"Actual dimensions must match");
  JSONObject expectedCancel=world().put("engine_passed",false).put("cancelled",true).put("expected_cancel",true).put("java_obsolete",true);
  check(ReceiptRules.worldObsoleteHarmless(expectedCancel,true),"Expected obsolete surface cancellation is harmless");check(!ReceiptRules.worldObsoleteHarmless(expectedCancel,false),"Current render cancellation cannot be excused");check(!ReceiptRules.worldObsoleteHarmless(expectedCancel.put("session_failure",true),true),"Home cannot hide actual native failure");
  expectedCancel.put("session_failure",false).put("gl_errors",1);check(!ReceiptRules.worldObsoleteHarmless(expectedCancel,true),"Home cannot hide GL error");check(ReceiptRules.worldObsoleteHarmless(world().put("java_obsolete",true),true),"Obsolete otherwise-good completion is ignored");
  for(String key:new String[]{"stationary_mismatches","camera_determinism_mismatches","same_camera_image_mismatches","interactive_transform_mismatches"}){JSONObject fake=world().put("engine_passed",false).put("cancelled",true).put("expected_cancel",true).put(key,1);check(!ReceiptRules.worldObsoleteHarmless(fake,true),"Deferred source/GPU mismatch cannot be hidden by cancellation "+key);}
  IntegrationUiCheck t=valid();check(t.backgroundPassed(),"Exact Home cancel and foreground reopen");
  for(String key:new String[]{"input_cleared","audio_started_before_pause","transport_started_before_pause"}){t=valid();t.background.put(key,false);check(!t.backgroundPassed(),"Home requires "+key);}
  t=valid();t.background.put("stop_sequence",104);check(!t.backgroundPassed(),"Stop precedes resume");t=valid();t.background.put("interrupted_transport_run_id",999);check(!t.backgroundPassed(),"Exact UDP run required");
  t=valid();t.worldRuns.optJSONObject(0).put("generation",1);check(!t.backgroundPassed(),"Stale renderer generation rejected");t=valid();t.worldRuns.optJSONObject(0).put("started_after_event",90);check(!t.backgroundPassed(),"Foreground renderer must start after resume");
  t=valid();t.audioRuns.optJSONObject(1).put("started_after_event",90);check(!t.backgroundPassed(),"Fresh complete foreground playback required");t=valid();t.nativeRuns.optJSONObject(0).put("started_after_event",90);check(!t.backgroundPassed(),"Fresh decoder+network checks required");
  JSONObject zero=o("result",1,"held",0,"pressed",0,"released",0,"delta_x",0,"delta_y",0,"axes",new JSONArray().put(0).put(0).put(0).put(0));check(ReceiptRules.zeroInput(zero),"Focus-cleared source frame");check(!ReceiptRules.zeroInput(zero.put("held",1)),"Held input blocks Home receipt");
  System.out.println(checked);
 }
 __BACKGROUND__
}'''.replace('__BACKGROUND__', method(source, 'private boolean backgroundPassed('))
    (package / 'IntegrationUiCheck.java').write_text(harness)
    args.output.mkdir(parents=True, exist_ok=True)
    javac = str(args.java_home / 'bin/javac') if args.java_home else 'javac'
    java = str(args.java_home / 'bin/java') if args.java_home else 'java'
    subprocess.run([javac,'--release','8','-Xlint:-options',*[str(p) for p in root.rglob('*.java')]],check=True,timeout=30)
    result = subprocess.run([java,'-cp',str(root),'org.coh.integrationprobe.IntegrationUiCheck'],check=True,capture_output=True,text=True,timeout=30)
    receipt = {'schema':'coh-native-integration-ui-host-v2','passed':True,'checks':int(result.stdout.strip()),'scope':'Actual shipped Java validation predicates on controlled decoder/audio/socket/renderer/Home receipts; not hardware execution','main_activity_sha256':hashlib.sha256((java_dir/'MainActivity.java').read_bytes()).hexdigest(),'receipt_rules_sha256':hashlib.sha256((java_dir/'ReceiptRules.java').read_bytes()).hexdigest()}
    (args.output/'ui-host-checks.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
