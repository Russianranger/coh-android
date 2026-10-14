#!/usr/bin/env python3
"""Execute actual Java qualification methods on controlled lifecycle receipts.

This validates receipt rejection logic on a host JVM. It does not run Android
callbacks, create an AAudio stream, or establish hardware controller behavior.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def method(source, signature):
    start = source.index(signature)
    brace = source.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        if source[end] == '{':
            depth += 1
        elif source[end] == '}':
            depth -= 1
        end += 1
    return source[start:end]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--java-home', type=Path, default=None)
    args = p.parse_args()
    source_path = Path(__file__).resolve().parents[1] / 'app/src/main/java/org/coh/systemsprobe/MainActivity.java'
    source = source_path.read_text()
    methods = '\n'.join(method(source, s) for s in (
        'private static boolean zeroInput(', 'private boolean preBackground(', 'private boolean backgroundPassed('))
    harness = r'''
import java.util.*;
public final class SystemsUiCheck {
 JSONArray nativeRuns=new JSONArray(),audioRuns=new JSONArray();JSONObject background=object();
 boolean active=true,assetsReady=true,syntheticPassed=true;int failures=0;long generation=2,nativeSequence=3;
 View inputView=new View();static int checked;
 static JSONObject object(Object... x){JSONObject o=new JSONObject();for(int i=0;i<x.length;i+=2)o.put((String)x[i],x[i+1]);return o;}
 static void check(boolean x,String why){checked++;if(!x)throw new AssertionError(why);}
 static JSONObject nativeRun(long id,long gen,int w,int h,long began){return object("run_id",id,"generation",gen,"width",w,"height",h,"passed",true,"foreground_at_completion",true,"started_after_event",began);}
 static JSONObject cancel(){return object("run_id",2,"result",1,"cancelled",true,"opened",true,"started",true,"stopped",true,"closed",true,"backend_errors",0,"submitted_frames",512,"started_after_event",99);}
 static SystemsUiCheck valid(){SystemsUiCheck t=new SystemsUiCheck();
  t.nativeRuns.put(nativeRun(1,1,100,100,1)).put(nativeRun(2,1,75,75,2)).put(nativeRun(3,2,75,75,3));
  t.audioRuns.put(object("passed",true,"run_id",1,"started_after_event",4));
  t.background=object("pause_sequence",100,"stop_sequence",101,"resume_sequence",102,"input_cleared",true,"audio_started_before_pause",true,"interrupted_audio_run_id",2);
  t.audioRuns.put(cancel()).put(object("run_id",3,"passed",true,"foreground_at_completion",true,"started_after_event",102));
  t.nativeRuns.put(nativeRun(4,2,75,75,102));t.nativeSequence=4;return t;}
 public static void main(String[] a){SystemsUiCheck t=valid();
  check(t.preBackground(),"Three current source passes with two sizes/generations");check(t.backgroundPassed(),"Exact interrupted stream and fresh foreground passes");
  t.active=false;check(!t.preBackground(),"Background activity cannot qualify current checks");t.active=true;
  t.failures=1;check(!t.preBackground(),"Sticky native failure blocks checks");t.failures=0;
  t.nativeSequence=99;check(!t.preBackground(),"Pending or stale source run cannot qualify");t.nativeSequence=4;
  t.inputView.w=74;check(!t.preBackground(),"Run must match current actual view size");t.inputView.w=75;
  t.nativeRuns.optJSONObject(3).put("foreground_at_completion",false);check(!t.preBackground(),"Background-completed source run cannot qualify");
  String[] bools={"opened","started","stopped","closed"};for(String key:bools){t=valid();t.audioRuns.optJSONObject(1).put(key,false);check(!t.backgroundPassed(),"Interrupted stream cleanup requires "+key);}
  t=valid();t.background.put("interrupted_audio_run_id",99);check(!t.backgroundPassed(),"Earlier unrelated cancellation cannot satisfy Home");
  t=valid();t.audioRuns.optJSONObject(1).put("result",0);check(!t.backgroundPassed(),"Successful noncancelled stream cannot satisfy interruption");
  t=valid();t.audioRuns.optJSONObject(1).put("submitted_frames",0);check(!t.backgroundPassed(),"Stream must actually have submitted samples");
  t=valid();t.audioRuns.optJSONObject(1).put("backend_errors",1);check(!t.backgroundPassed(),"Interrupted stream backend error blocks cleanup");
  t=valid();t.background.put("stop_sequence",103);check(!t.backgroundPassed(),"Stop must precede resume");
  t=valid();t.background.put("input_cleared",false);check(!t.backgroundPassed(),"Input release proof is required");
  t=valid();t.background.put("audio_started_before_pause",false);check(!t.backgroundPassed(),"Queued playback is not an interrupted started sink");
  t=valid();t.nativeRuns.optJSONObject(3).put("started_after_event",101);check(!t.backgroundPassed(),"Source checks must start after this resume");
  t=valid();t.audioRuns.optJSONObject(2).put("started_after_event",101);check(!t.backgroundPassed(),"Full playback must start after this resume");
  t=valid();t.audioRuns.optJSONObject(2).put("foreground_at_completion",false);check(!t.backgroundPassed(),"Replay must finish in foreground");
  JSONObject clear=object("result",1,"held",0,"pressed",0,"released",0,"delta_x",0,"delta_y",0,"axes",new JSONArray().put(0).put(0).put(0).put(0));
  check(zeroInput(clear),"Cleared native key/axis/motion state");clear.put("held",1);check(!zeroInput(clear),"Held key fails input clearing");clear.put("held",0).put("delta_x",1);check(!zeroInput(clear),"Pending relative motion fails clearing");
  System.out.println(checked);}
__METHODS__
}
class View {int w=75,h=75;int getWidth(){return w;}int getHeight(){return h;}}
class JSONObject {Map<String,Object> m=new HashMap<>();JSONObject put(String k,Object v){m.put(k,v);return this;}boolean optBoolean(String k){return Boolean.TRUE.equals(m.get(k));}
 int optInt(String k){Object v=m.get(k);return v instanceof Number?((Number)v).intValue():0;}long optLong(String k){return optLong(k,0);}long optLong(String k,long f){Object v=m.get(k);return v instanceof Number?((Number)v).longValue():f;}
 JSONArray optJSONArray(String k){Object v=m.get(k);return v instanceof JSONArray?(JSONArray)v:null;}}
class JSONArray {List<Object> l=new ArrayList<>();JSONArray put(Object v){l.add(v);return this;}int length(){return l.size();}JSONObject optJSONObject(int i){return i>=0&&i<l.size()?(JSONObject)l.get(i):null;}
 double optDouble(int i,double f){Object v=i>=0&&i<l.size()?l.get(i):null;return v instanceof Number?((Number)v).doubleValue():f;}}
'''.replace('__METHODS__', methods)
    args.output.mkdir(parents=True, exist_ok=True)
    java_source = args.output / 'SystemsUiCheck.java'
    java_source.write_text(harness)
    java_home = args.java_home or (Path(os.environ['JAVA_HOME']) if 'JAVA_HOME' in os.environ else None)
    javac = str(java_home / 'bin/javac') if java_home else 'javac'
    java = str(java_home / 'bin/java') if java_home else 'java'
    subprocess.run([javac, '--release', '8', '-Xlint:-options', str(java_source)], check=True, timeout=30)
    run = subprocess.run([java, '-cp', str(args.output), 'SystemsUiCheck'], check=True, capture_output=True, text=True, timeout=30)
    receipt = {'schema':'coh-native-systems-ui-host-v1','passed':True,'checks':int(run.stdout.strip()),
        'scope':'Actual receipt validation methods on controlled host Java data; not Android lifecycle or AAudio execution',
        'main_activity_sha256':hashlib.sha256(source_path.read_bytes()).hexdigest()}
    (args.output / 'ui-host-checks.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
