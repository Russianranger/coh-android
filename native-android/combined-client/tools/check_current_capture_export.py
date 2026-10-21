#!/usr/bin/env python3
"""Exact Main selector + genuine store: stale service/report data cannot set APK identity."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[3]
JAVA=ROOT/'native-android/combined-client/app/src/main/java/org/coh/nativecombined'
MAIN=JAVA/'MainActivity.java'
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

HARNESS=r'''
package org.coh.nativecombined;
import java.io.*;
import java.nio.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;
import org.json.JSONObject;
public final class CurrentCaptureExportControls {
 static int checks;static void need(boolean c,String m){checks++;if(!c)throw new AssertionError(m);}
 final Worker reportWorker=new Worker();final Layout controlsLayout=new Layout();
 long sessionStarted=0xcafe20;String captureMetadata,captureFailure;int sceneExports;
 long captureAppVersion(){return BuildConfig.VERSION_CODE;}void exportSceneCapture(){sceneExports++;}
 void initializeCapture(){/*ON_CREATE_CAPTURE*/}
 final File directory;Object service=null;JSONObject storedCombined=new JSONObject().put("version_code",18);
 CurrentCaptureExportControls(File dir){directory=dir;}
 File getFilesDir(){return directory;}String getPackageName(){return "org.coh.nativecombined";}
 /*MAIN_SELECTOR*/
 /*RAW*/
 static JSONObject report(long version,String session){return new JSONObject().put("session_id",session)
   .put("app",new JSONObject().put("package","org.coh.nativecombined").put("version_code",version))
   .put("scene_frame_capture",new JSONObject().put("source_app_version",version).put("activity_session",session));}
 static void absent(SceneFrameCapture.Selection c,String reason)throws Exception{
  need(reason.equals(c.omissionReason()),"omission reason: "+c.omissionReason());need(c.metadata()==null,"omitted metadata");
  ByteArrayOutputStream output=new ByteArrayOutputStream();need(!c.writeZip(output)&&output.size()==0,"no standalone capture bytes");
  try(ZipOutputStream zip=new ZipOutputStream(output)){zip.putNextEntry(new ZipEntry("combined-report.json"));zip.write(1);zip.closeEntry();
   int before=output.size();need(!c.append(zip)&&output.size()==before,"no capture entries appended");}
  try(ZipInputStream zip=new ZipInputStream(new ByteArrayInputStream(output.toByteArray()))){need(zip.getNextEntry().getName().equals("combined-report.json"),"essential report retained");need(zip.getNextEntry()==null,"all raw/json/png capture entries omitted");}
 }
 public static void main(String[]args)throws Exception{
  File dir=new File(args[0]);CurrentCaptureExportControls app=new CurrentCaptureExportControls(dir);
  need(app.service==null&&app.storedCombined.optLong("version_code",-1)==18&&BuildConfig.VERSION_CODE==20,"stale service-absent regression setup");
  byte[] pixels=raw(640,360,120);SceneFrameCapture.saveLarge(dir,pixels,18,"cafe18");
  absent(app.currentSceneCapture(report(18,"cafe18")),"CAPTURE_APP_VERSION_MISMATCH");
  app.captureMetadata="before";app.initializeCapture();need(app.controlsLayout.children.size()==1&&app.reportWorker.pending.size()==1&&"before".equals(app.captureMetadata),"exact onCreate block queues background inspection and retains Button capture lexical scope");
  app.reportWorker.drain();need(app.captureMetadata==null&&"CAPTURE_APP_VERSION_MISMATCH".equals(app.captureFailure),"onCreate inspection refuses stale app capture");
  app.controlsLayout.children.get(0).click();need(app.sceneExports==1,"exact scene export button callback");
  SceneFrameCapture.saveLarge(dir,pixels,20,"cafe99");
  absent(app.currentSceneCapture(report(20,"cafe20")),"CAPTURE_ACTIVITY_SESSION_MISMATCH");
  app.initializeCapture();app.reportWorker.drain();need(app.captureMetadata==null&&"CAPTURE_ACTIVITY_SESSION_MISMATCH".equals(app.captureFailure),"onCreate inspection refuses stale activity capture");
  SceneFrameCapture.saveLarge(dir,pixels,20,"cafe20");
  app.initializeCapture();app.reportWorker.drain();need(app.captureMetadata!=null&&app.captureFailure==null&&app.captureMetadata.contains("\"source_app_version\":20")&&app.captureMetadata.contains("\"activity_session\":\"cafe20\""),"onCreate inspection accepts fresh installed app/session capture");
  BuildConfig.FRAME_CAPTURE_DIAGNOSTIC=false;int children=app.controlsLayout.children.size();app.initializeCapture();need(children==app.controlsLayout.children.size()&&app.reportWorker.pending.isEmpty(),"legacy profile does not create capture UI or I/O");BuildConfig.FRAME_CAPTURE_DIAGNOSTIC=true;
  SceneFrameCapture.Selection valid=app.currentSceneCapture(report(20,"cafe20"));need(valid.omissionReason()==null&&valid.metadata()!=null,"installed version and current activity accepted");
  ByteArrayOutputStream output=new ByteArrayOutputStream();need(valid.writeZip(output),"current capture exported");
  Set<String> names=new HashSet<>();try(ZipInputStream zip=new ZipInputStream(new ByteArrayInputStream(output.toByteArray()))){ZipEntry e;while((e=zip.getNextEntry())!=null)names.add(e.getName());}
  need(names.equals(new HashSet<>(Arrays.asList("scene-capture.rgba","scene-capture.json","scene-capture.png"))),"current raw/json/PNG entries");
  JSONObject noMetadata=report(20,"cafe20");noMetadata.put("scene_frame_capture",null);absent(app.currentSceneCapture(noMetadata),"CAPTURE_CURRENT_RUN_UNAVAILABLE");
  absent(app.currentSceneCapture(null),"CAPTURE_CURRENT_RUN_UNAVAILABLE");
  absent(app.currentSceneCapture(report(18,"cafe20")),"CAPTURE_CURRENT_RUN_UNAVAILABLE");
  JSONObject wrongPackage=report(20,"cafe20");wrongPackage.optJSONObject("app").put("package","other.app");absent(app.currentSceneCapture(wrongPackage),"CAPTURE_CURRENT_RUN_UNAVAILABLE");
  byte[] corrupt=Files.readAllBytes(new File(dir,"scene-capture.bin").toPath());corrupt[corrupt.length-1]^=1;Files.write(new File(dir,"scene-capture.bin").toPath(),corrupt);
  absent(app.currentSceneCapture(report(20,"cafe20")),"CAPTURE_MISSING_OR_INVALID");
  System.out.println("{\"passed\":true,\"checks\":"+checks+",\"installed_version\":20,\"stale_combined_native_capture_version\":18,\"service_bound\":false,\"Android_execution\":false}");
 }
 }
final class Button {interface Click {void onClick(Button button);}Click listener;String text;Button(Object context){}void setText(String value){text=value;}void setOnClickListener(Click value){listener=value;}void click(){listener.onClick(this);}}
final class Layout {final List<Button> children=new ArrayList<>();void addView(Button button){children.add(button);}}
final class Worker {final ArrayDeque<Runnable> pending=new ArrayDeque<>();void execute(Runnable job){pending.add(job);}void drain(){while(!pending.isEmpty())pending.remove().run();}}
'''

def main():
    global ROOT,JAVA,MAIN
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-root',type=Path,default=ROOT);args=parser.parse_args()
    ROOT=args.source_root.resolve();JAVA=ROOT/'native-android/combined-client/app/src/main/java/org/coh/nativecombined';MAIN=JAVA/'MainActivity.java'
    activity=JAVA/'NativeClientActivity.java'
    extract=load('capture_export_extract',ROOT/'native-android/session-client/tools/lifecycle_host_check.py').method
    store=load('capture_export_controls',Path(__file__).with_name('check_frame_capture_store.py'))
    selector=extract(MAIN.read_text(),'private SceneFrameCapture.Selection currentSceneCapture(JSONObject report)')
    assert 'BuildConfig.VERSION_CODE' in selector and 'combined.optLong' not in selector
    assert 'SceneFrameCapture.Selection capture=currentSceneCapture(captureReport);' in MAIN.read_text()
    on_create=extract(activity.read_text(),'@Override public void onCreate(Bundle bundle)')
    capture_block=extract(on_create,'if(BuildConfig.FRAME_CAPTURE_DIAGNOSTIC)')
    assert 'Button capture=new Button(this);' in capture_block and 'reportWorker.execute' in capture_block
    raw='\n'.join(extract(store.HARNESS,s)for s in ('private static ByteBuffer bytes(byte[] raw)','private static byte[] raw(int width, int height, long frame)'))
    paths=[MAIN,JAVA/'SceneFrameCapture.java',JAVA/'SceneCapturePng.java',JAVA/'ApkReportIdentity.java',Path(__file__),activity]
    pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}
    with tempfile.TemporaryDirectory(prefix='coh-current-capture-')as temp:
        w=Path(temp);sources={
          'org/json/JSONObject.java':'''package org.json;import java.util.*;public class JSONObject {Map<String,Object> values=new HashMap<>();public JSONObject put(String k,Object v){values.put(k,v);return this;}public Object opt(String k){return values.get(k);}public JSONObject optJSONObject(String k){Object v=values.get(k);return v instanceof JSONObject?(JSONObject)v:null;}public String optString(String k){Object v=values.get(k);return v instanceof String?(String)v:"";}public long optLong(String k,long fallback){Object v=values.get(k);return v instanceof Number?((Number)v).longValue():fallback;}}''',
          'org/coh/nativecombined/BuildConfig.java':'package org.coh.nativecombined;final class BuildConfig {static final int VERSION_CODE=20;static final boolean FULLSCREEN_DIAGNOSTIC=true;static boolean FRAME_CAPTURE_DIAGNOSTIC=true;}',
          'org/coh/nativecombined/CurrentCaptureExportControls.java':HARNESS.replace('/*MAIN_SELECTOR*/',selector).replace('/*RAW*/',raw).replace('/*ON_CREATE_CAPTURE*/',capture_block)}
        java=[]
        for name,text in sources.items():
            p=w/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);java.append(p)
        subprocess.run(['java','-Xmx128m','com.sun.tools.javac.Main','--release','8','-d',str(w),*map(str,paths[1:4]),*map(str,java)],check=True,timeout=60)
        original=w/'org/coh/nativecombined/CurrentCaptureExportControls.java'
        mutant=w/'negative/org/coh/nativecombined/CurrentCaptureExportControls.java';mutant.parent.mkdir(parents=True)
        old_name=capture_block.replace('selectedCapture','capture');assert old_name!=capture_block
        mutant.write_text(original.read_text().replace(capture_block,old_name))
        bad_sources=[mutant if path==original else path for path in java]
        bad=subprocess.run(['java','-Xmx128m','com.sun.tools.javac.Main','--release','8','-d',str(w/'negative-classes'),*map(str,paths[1:4]),*map(str,bad_sources)],capture_output=True,text=True,timeout=60)
        assert bad.returncode!=0 and 'variable capture is already defined' in bad.stderr,'Old lexical-scope defect was not reproduced by javac'
        r=subprocess.run(['java','-Xmx64m','-cp',str(w),'org.coh.nativecombined.CurrentCaptureExportControls',str(w/'capture')],check=True,capture_output=True,text=True,timeout=60)
        result=json.loads(r.stdout)
    assert pins=={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}
    result['old_lexical_scope_name_rejected_by_javac']=True;result['exact_onCreate_capture_block']=True
    result['source_unchanged']=True;result['source_sha256']=pins;result['scope']='Exact MainActivity selector and complete onCreate capture block with enclosing Button scope; genuine store/PNG/APK identity. Android/JSON/UI/worker/service collaborators explicit host doubles; old-name mutant must fail javac.'
    print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
