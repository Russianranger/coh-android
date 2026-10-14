#!/usr/bin/env python3
"""Execute shipped late-callback guards without an Android SDK or native driver.

Bodies are extracted from MainActivity, not reimplemented. A still-nonzero
retired handle makes accidental JNI calls observable. This checks the Java
destruction boundary; framework ordering and native cleanup remain device gates.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


SIGNATURES = {
    'surface_changed': 'public void surfaceChanged(SurfaceHolder holder,int format,int width,int height)',
    'surface_destroyed': 'public void surfaceDestroyed(SurfaceHolder holder)',
    'window_focus': 'public void onWindowFocusChanged(boolean focused)',
    'key_callback': 'public boolean dispatchKeyEvent(KeyEvent event)',
    'motion_callback': 'public boolean dispatchGenericMotionEvent(MotionEvent event)',
    'event': 'private void event(String type)',
    'sink_focus': 'public void focus(boolean focused)',
    'sink_key': 'public void key(int key, boolean down)',
    'sink_axes': 'public void axes(float x, float y, float z, float rz)',
    'sink_touch': 'public void touch(int action, int pointer, float x, float y)',
    'save_report': 'private void saveReport()',
}


def method(source, signature):
    """Keep an exact body while ignoring braces inside strings/comments."""
    assert source.count(signature) == 1, 'Ambiguous shipped method: ' + signature
    start = source.index(signature)
    index = source.index('{', start)
    depth, state = 0, 'code'
    while index < len(source):
        char = source[index]
        following = source[index:index + 2]
        if state in ('string', 'char'):
            if char == '\\':
                index += 2
                continue
            if char == ('"' if state == 'string' else "'"):
                state = 'code'
        elif state == 'line':
            if char == '\n':
                state = 'code'
        elif state == 'comment':
            if following == '*/':
                state = 'code'
                index += 2
                continue
        elif following in ('//', '/*'):
            state = 'line' if following == '//' else 'comment'
            index += 2
            continue
        elif char in ('"', "'"):
            state = 'string' if char == '"' else 'char'
        elif char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
        index += 1
    raise AssertionError('Unclosed shipped method: ' + signature)


def strip_guard(name, body):
    if name in ('surface_changed', 'surface_destroyed'):
        old, new = 'destroying || holder!=currentHolder', 'holder!=currentHolder'
        assert body.count(old) == 1
        return body.replace(old, new)
    if name in ('window_focus', 'key_callback', 'motion_callback'):
        old = '!destroying && adapter!=null'
        assert body.count(old) == 1
        return body.replace(old, 'adapter!=null')
    stripped, count = re.subn(r'if\s*\(destroying\)\s*return\s*;', '', body)
    assert count == 1, 'Missing or ambiguous destruction guard: ' + name
    return stripped


HARNESS = r'''package org.coh.sessionclient;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;

class Effects {
 static final List<String> calls = new ArrayList<>();
 static void call(String name) { calls.add(name); }
 static void reset() { calls.clear(); }
}
class KeyEvent { }
class MotionEvent { }
class Surface { }
class SurfaceHolder {
 Surface getSurface() { Effects.call("holder.getSurface"); return new Surface(); }
}
class BaseActivity {
 public void surfaceChanged(SurfaceHolder h,int f,int w,int t) { }
 public void surfaceDestroyed(SurfaceHolder h) { }
 public void onWindowFocusChanged(boolean focused) { }
 public boolean dispatchKeyEvent(KeyEvent event) { return false; }
 public boolean dispatchGenericMotionEvent(MotionEvent event) { return false; }
}
class InputAdapter {
 void onWindowFocusChanged(boolean focus) { Effects.call("adapter.focus"); }
 boolean dispatchKeyEvent(KeyEvent event) { Effects.call("adapter.key"); return true; }
 boolean dispatchGenericMotionEvent(MotionEvent event) { Effects.call("adapter.motion"); return true; }
}
class SessionNative {
 static void state(long h,long e,boolean f) { Effects.call("jni.state"); }
 static void focus(long h) { Effects.call("jni.focus"); }
 static void look(long h,float x,float y) { Effects.call("jni.look"); }
 static String snapshot(long h) { Effects.call("jni.snapshot"); return "{}"; }
}
class JSONObject {
 final Map<String,Object> values = new HashMap<>();
 JSONObject() { }
 JSONObject(String raw) { }
 JSONObject put(String key,Object value) { values.put(key,value); return this; }
 JSONObject optJSONObject(String key) { Object value=values.get(key); return value instanceof JSONObject?(JSONObject)value:null; }
 int optInt(String key) { return 0; }
 String optString(String key,String fallback) { return fallback; }
 long optLong(String key) { return 0; }
 String toString(int indent) { return "{}"; }
}
class JSONArray {
 final List<Object> values = new ArrayList<>();
 void put(Object value) { values.add(value); }
 int length() { return values.size(); }
 void remove(int index) { values.remove(index); }
}
class Status { void setText(String text) { Effects.call("status.setText"); } }

public final class LifecycleGuardCheck extends BaseActivity {
 static final String[] CASES = {"surface_changed","surface_destroyed","window_focus",
  "key_callback","motion_callback","event","sink_focus","sink_key","sink_axes",
  "sink_touch","save_report"};
 long handle=7,epoch=3,sequence;
 boolean destroying,resumed=true,touching=true,assetsVerified=true,writeFailed;
 int keys=1<<20;
 float axisX=1,axisY=1,axisZ=1,axisRz=1,touchX,touchY;
 String failure;
 Surface currentSurface=new Surface();
 SurfaceHolder currentHolder=new SurfaceHolder();
 InputAdapter adapter=new InputAdapter();
 JSONArray events=new JSONArray();
 Status status=new Status();
 AtomicReference<byte[]> pendingReport=new AtomicReference<>();
 void requestRender() { Effects.call("requestRender"); }
 void sendInput() { Effects.call("sendInput"); }
 void queueWriter() { Effects.call("queueWriter"); }
 JSONObject report() { Effects.call("report"); return new JSONObject(); }

/* SHIPPED_METHODS */

 void invoke(String name) {
  switch(name) {
   case "surface_changed":surfaceChanged(currentHolder,4,100,100);break;
   case "surface_destroyed":surfaceDestroyed(currentHolder);break;
   case "window_focus":onWindowFocusChanged(false);break;
   case "key_callback":dispatchKeyEvent(new KeyEvent());break;
   case "motion_callback":dispatchGenericMotionEvent(new MotionEvent());break;
   case "event":event("late_callback");break;
   case "sink_focus":focus(false);break;
   case "sink_key":key(20,true);break;
   case "sink_axes":axes(1,1,1,1);break;
   case "sink_touch":touch(1,0,.5f,.5f);break;
   case "save_report":saveReport();break;
   default:throw new AssertionError("Unknown case "+name);
  }
 }
 static void destroyed(String name) {
  LifecycleGuardCheck subject=new LifecycleGuardCheck();
  subject.destroying=true;Effects.reset();subject.invoke(name);
  if(!Effects.calls.isEmpty())throw new AssertionError("Destroyed callback "+name+" emitted effects: "+Effects.calls);
  if(subject.failure!=null)throw new AssertionError("Destroyed callback changed failure: "+name);
 }
 public static void main(String[] args) {
  if(args.length==1) { destroyed(args[0]);return; }
  int checks=0;
  for(String name:CASES) {
   LifecycleGuardCheck subject=new LifecycleGuardCheck();
   Effects.reset();subject.invoke(name);
   if(Effects.calls.isEmpty())throw new AssertionError("Live positive control inert: "+name);
   if(subject.failure!=null)throw new AssertionError("Live positive control failed: "+name);
   checks++;destroyed(name);checks++;
  }
  System.out.println("{\"checks\":"+checks+"}");
 }
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--java-home', type=Path)
    args = parser.parse_args()
    source_path = Path(__file__).resolve().parents[1] / 'app/src/main/java/org/coh/sessionclient/MainActivity.java'
    raw = source_path.read_bytes()
    bodies = {name: method(raw.decode(), signature) for name, signature in SIGNATURES.items()}
    java_home = args.java_home or (Path(os.environ['JAVA_HOME']) if os.environ.get('JAVA_HOME') else None)
    javac = str(java_home / 'bin/javac') if java_home else shutil.which('javac')
    java = str(java_home / 'bin/java') if java_home else shutil.which('java')
    assert javac and java, 'Provide --java-home for an installed JDK'
    args.output.mkdir(parents=True, exist_ok=True)
    roots = {}
    for variant in ('shipped', 'removed-guards'):
        root = args.output / variant
        package = root / 'org/coh/sessionclient'
        package.mkdir(parents=True, exist_ok=True)
        selected = bodies if variant == 'shipped' else {name: strip_guard(name, body) for name, body in bodies.items()}
        path = package / 'LifecycleGuardCheck.java'
        path.write_text(HARNESS.replace('/* SHIPPED_METHODS */', '\n'.join(selected.values())))
        subprocess.run([javac, '-d', str(root), str(path)], check=True, capture_output=True, text=True, timeout=60)
        roots[variant] = root
    baseline = subprocess.run([java, '-cp', str(roots['shipped']), 'org.coh.sessionclient.LifecycleGuardCheck'],
                              check=True, capture_output=True, text=True, timeout=30)
    checks = json.loads(baseline.stdout)['checks']
    assert checks == len(SIGNATURES) * 2
    negative = []
    for name in SIGNATURES:
        result = subprocess.run([java, '-cp', str(roots['removed-guards']), 'org.coh.sessionclient.LifecycleGuardCheck', name],
                                capture_output=True, text=True, timeout=30)
        assert result.returncode != 0 and ('Destroyed callback ' + name + ' emitted effects:') in result.stderr, \
            'Negative control did not catch removed guard: ' + name
        negative.append(name)
    proof = {
        'schema': 'coh-native-session-lifecycle-host-v1', 'passed': True,
        'checks': checks, 'negative_control_checks': len(negative),
        'source': 'native-android/session-client/app/src/main/java/org/coh/sessionclient/MainActivity.java',
        'source_sha256': hashlib.sha256(raw).hexdigest(),
        'scope': 'Actual extracted Java callback/sink/event/save methods under minimal host transport stubs; destruction guards only, not Android framework ordering or native resource cleanup',
        'entry_points': list(SIGNATURES),
        'retired_nonzero_handle': 7,
        'destroyed_callbacks_emit_no_jni_snapshot_adapter_input_render_or_report_effects': True,
        'live_positive_controls_passed': True,
        'negative_control': {'mutation': 'Remove only each extracted destruction guard; keep shipped remaining body intact',
                             'detected_for_every_entry_point': negative},
    }
    (args.output / 'lifecycle-host-checks.json').write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps(proof))


if __name__ == '__main__':
    main()
