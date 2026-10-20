#!/usr/bin/env python3
"""Exact Activity fullscreen methods with explicit host View/window doubles.

Also exercises real Java large-frame storage/export. No Android ABI, framework
resize, actual renderer or device memory execution is claimed by these controls.
Serialize externally with flock /tmp/coh-next-build.lock.
"""
from pathlib import Path
import hashlib, importlib.util, json, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[3]
ACTIVITY=ROOT/'native-android/combined-client/app/src/main/java/org/coh/nativecombined/NativeClientActivity.java'
STORE=ACTIVITY.with_name('SceneFrameCapture.java')

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

JAVA=r'''package org.coh.nativecombined;
import java.io.*;import java.nio.*;import java.util.*;import java.util.zip.*;
class Base {public void onBackPressed(){}}
public class FullscreenControlsTest extends Base {
 static int checks;static void check(boolean v){checks++;if(!v)throw new AssertionError("check "+checks);}
 static class BuildConfig {static boolean FULLSCREEN_DIAGNOSTIC=true;}
 static class SessionNative {static List<String> calls=new ArrayList<>();
  static void state(long h,long e,boolean f){calls.add("state:"+e);}
  static void captureViewport(long h,long e,int w,int t){calls.add(e+":"+w+":"+t);}}
 static class Adapter {int clears;void clear(){clears++;}}
 static class Window {android.view.View decor=new android.view.View();android.view.View getDecorView(){return decor;}}
 static class Surface {boolean valid=true;boolean isValid(){return valid;}}
 static class Holder {android.graphics.Rect frame=new android.graphics.Rect(1920,410);android.graphics.Rect getSurfaceFrame(){return frame;}}
 Adapter adapter=new Adapter();Window window=new Window();Surface currentSurface=new Surface();Holder currentHolder=new Holder();
 android.view.View view=new android.view.View(),scene=new android.view.View(),controlsPanel=new android.view.View(),fullscreenReturn=new android.view.View();
 boolean sceneFullscreen,destroying,resumed=true;long handle=1,epoch=4;int previousOrientation,previousSystemUi,orientation=-1,events,reports,renders;
 Window getWindow(){return window;}int getRequestedOrientation(){return orientation;}void setRequestedOrientation(int o){orientation=o;}
 void event(String e){events++;}void saveReport(){reports++;}void requestRender(){renders++;}
 /*ACTIVITY*/
 /*RAW*/
 public static void main(String[]args)throws Exception{
  FullscreenControlsTest a=new FullscreenControlsTest();a.scene.width=a.view.width=1920;a.scene.height=1080;a.view.height=410;
  a.fullscreenReturn.visible=8;a.window.decor.flags=123;
  BuildConfig.FULLSCREEN_DIAGNOSTIC=false;a.setSceneFullscreen(true);check(!a.sceneFullscreen&&a.epoch==4);
  BuildConfig.FULLSCREEN_DIAGNOSTIC=true;a.setSceneFullscreen(true);
  check(a.sceneFullscreen&&a.controlsPanel.visible==8&&a.fullscreenReturn.visible==0);
  check(a.orientation==6&&a.previousOrientation==-1&&a.previousSystemUi==123);
  check(a.epoch==5&&a.adapter.clears==1&&a.events==1&&a.reports==1&&a.renders==1);
  check(SessionNative.calls.contains("5:0:0"));android.view.View.drain();check(SessionNative.calls.get(SessionNative.calls.size()-1).equals("5:0:0"));
  a.view.height=1080;a.currentHolder.frame=new android.graphics.Rect(1920,1080);a.publishCaptureViewport();android.view.View.drain();
  check(SessionNative.calls.get(SessionNative.calls.size()-1).equals("5:1920:1080"));
  int calls=SessionNative.calls.size();a.publishCaptureViewport();a.epoch++;android.view.View.drain();check(SessionNative.calls.size()==calls);
  a.setSceneFullscreen(true);check(a.epoch==6&&SessionNative.calls.size()==calls);
  a.onBackPressed();android.view.View.drain();check(!a.sceneFullscreen&&a.controlsPanel.visible==0&&a.fullscreenReturn.visible==8);
  check(a.orientation==-1&&a.window.decor.flags==123&&a.adapter.clears==2);
  check(SessionNative.calls.get(SessionNative.calls.size()-1).equals("7:0:0"));
  a.setSceneFullscreen(true);a.destroying=true;calls=SessionNative.calls.size();android.view.View.drain();check(SessionNative.calls.size()==calls);
  a.setSceneFullscreen(false);check(a.sceneFullscreen&&SessionNative.calls.size()==calls);
  File dir=new File(args[0],"large");byte[]raw=raw(640,360,120);
  String metadata=SceneFrameCapture.saveLarge(dir,raw,18,"cafe18");check(metadata.contains("\"width\":640")&&metadata.contains("\"height\":360"));
  check(raw.length==921728&&new File(dir,"scene-capture.bin").length()==921856);
  check(SceneFrameCapture.metadata(dir)==null&&SceneFrameCapture.metadataLarge(dir)!=null);
  boolean refused=false;try{SceneFrameCapture.save(dir,raw,18,"cafe18");}catch(IOException expected){refused=true;}check(refused);
  ByteArrayOutputStream zip=new ByteArrayOutputStream();check(SceneFrameCapture.writeZipLarge(dir,zip)&&zip.size()<2*1024*1024);
  try(ZipInputStream input=new ZipInputStream(new ByteArrayInputStream(zip.toByteArray()))){check(input.getNextEntry().getName().equals("scene-capture.rgba"));ByteArrayOutputStream actual=new ByteArrayOutputStream();byte[]chunk=new byte[16384];int n;while((n=input.read(chunk))!=-1)actual.write(chunk,0,n);check(Arrays.equals(actual.toByteArray(),raw));check(input.getNextEntry().getName().equals("scene-capture.json"));}
  ByteArrayOutputStream old=new ByteArrayOutputStream();check(!SceneFrameCapture.writeZip(dir,old)&&old.size()==0);
  byte[]oversize=raw(641,360,121);refused=false;try{SceneFrameCapture.saveLarge(dir,oversize,18,"cafe18");}catch(IOException expected){refused=true;}check(refused);
  check(new File(dir,"scene-capture.bin").length()==921856);
  System.out.println("{\"passed\":true,\"checks\":"+checks+",\"large_raw_bytes\":"+raw.length+",\"zip_bytes\":"+zip.size()+",\"actual_Android_execution\":false}");
 }
}'''


def main():
    extract=load('fullscreen_extract',ROOT/'native-android/session-client/tools/lifecycle_host_check.py').method
    old=load('capture_store_controls',Path(__file__).with_name('check_frame_capture_store.py'))
    methods='\n'.join(extract(ACTIVITY.read_text(),x)for x in ('private void applyFullscreenBars()','private void setSceneFullscreen(boolean enabled)','private void publishCaptureViewport()','@Override public void onBackPressed()'))
    raw='\n'.join(extract(old.HARNESS,x)for x in ('private static ByteBuffer bytes(byte[] raw)','private static byte[] raw(int width, int height, long frame)'))
    pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in (ACTIVITY,STORE,Path(__file__))}
    with tempfile.TemporaryDirectory(prefix='coh-fullscreen-java-')as temp:
        w=Path(temp)
        sources={
        'android/view/View.java':'''package android.view;import java.util.*;public class View {public static final int GONE=8,VISIBLE=0,SYSTEM_UI_FLAG_LAYOUT_STABLE=1,SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN=2,SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION=4,SYSTEM_UI_FLAG_FULLSCREEN=8,SYSTEM_UI_FLAG_HIDE_NAVIGATION=16,SYSTEM_UI_FLAG_IMMERSIVE_STICKY=32;public int width,height,visible,flags;static List<Runnable> tasks=new ArrayList<>();public void setSystemUiVisibility(int f){flags=f;}public int getSystemUiVisibility(){return flags;}public void setVisibility(int f){visible=f;}public void requestLayout(){}public int getWidth(){return width;}public int getHeight(){return height;}public void post(Runnable r){tasks.add(r);}public static void drain(){List<Runnable> q=new ArrayList<>(tasks);tasks.clear();for(Runnable r:q)r.run();}}''',
        'android/content/pm/ActivityInfo.java':'package android.content.pm;public class ActivityInfo {public static final int SCREEN_ORIENTATION_SENSOR_LANDSCAPE=6;}',
        'android/graphics/Rect.java':'package android.graphics;public class Rect {int w,h;public Rect(int a,int b){w=a;h=b;}public int width(){return w;}public int height(){return h;}}',
        'FullscreenControlsTest.java':JAVA.replace('/*ACTIVITY*/',methods).replace('/*RAW*/',raw)}
        java=[]
        for name,text in sources.items():
            p=w/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);java.append(p)
        subprocess.run(['java','-Xmx128m','com.sun.tools.javac.Main','--release','8','-d',str(w),str(STORE),*map(str,java)],check=True,timeout=60)
        r=subprocess.run(['java','-Xmx64m','-cp',str(w),'org.coh.nativecombined.FullscreenControlsTest',str(w)],capture_output=True,text=True,check=True,timeout=60)
        data=json.loads(r.stdout)
    assert pins=={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in (ACTIVITY,STORE,Path(__file__))}
    print(json.dumps({**data,'source_sha256':pins,'scope':'Exact Activity fullscreen methods with explicit host window/View/native-call doubles, plus real bounded Java store/ZIP; no Android framework or GL execution'}))

if __name__=='__main__':main()
