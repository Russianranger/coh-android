#!/usr/bin/env python3
"""Exact Main selector + genuine store: stale service/report data cannot set APK identity."""
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
  SceneFrameCapture.saveLarge(dir,pixels,20,"cafe99");
  absent(app.currentSceneCapture(report(20,"cafe20")),"CAPTURE_ACTIVITY_SESSION_MISMATCH");
  SceneFrameCapture.saveLarge(dir,pixels,20,"cafe20");
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
'''

def main():
    extract=load('capture_export_extract',ROOT/'native-android/session-client/tools/lifecycle_host_check.py').method
    store=load('capture_export_controls',Path(__file__).with_name('check_frame_capture_store.py'))
    selector=extract(MAIN.read_text(),'private SceneFrameCapture.Selection currentSceneCapture(JSONObject report)')
    assert 'BuildConfig.VERSION_CODE' in selector and 'combined.optLong' not in selector
    assert 'SceneFrameCapture.Selection capture=currentSceneCapture(captureReport);' in MAIN.read_text()
    raw='\n'.join(extract(store.HARNESS,s)for s in ('private static ByteBuffer bytes(byte[] raw)','private static byte[] raw(int width, int height, long frame)'))
    paths=[MAIN,JAVA/'SceneFrameCapture.java',JAVA/'SceneCapturePng.java',JAVA/'ApkReportIdentity.java',Path(__file__)]
    pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}
    with tempfile.TemporaryDirectory(prefix='coh-current-capture-')as temp:
        w=Path(temp);sources={
          'org/json/JSONObject.java':'''package org.json;import java.util.*;public class JSONObject {Map<String,Object> values=new HashMap<>();public JSONObject put(String k,Object v){values.put(k,v);return this;}public Object opt(String k){return values.get(k);}public JSONObject optJSONObject(String k){Object v=values.get(k);return v instanceof JSONObject?(JSONObject)v:null;}public String optString(String k){Object v=values.get(k);return v instanceof String?(String)v:"";}public long optLong(String k,long fallback){Object v=values.get(k);return v instanceof Number?((Number)v).longValue():fallback;}}''',
          'org/coh/nativecombined/BuildConfig.java':'package org.coh.nativecombined;final class BuildConfig {static final int VERSION_CODE=20;static final boolean FULLSCREEN_DIAGNOSTIC=true;}',
          'org/coh/nativecombined/CurrentCaptureExportControls.java':HARNESS.replace('/*MAIN_SELECTOR*/',selector).replace('/*RAW*/',raw)}
        java=[]
        for name,text in sources.items():
            p=w/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);java.append(p)
        subprocess.run(['java','-Xmx128m','com.sun.tools.javac.Main','--release','8','-d',str(w),*map(str,paths[1:4]),*map(str,java)],check=True,timeout=60)
        r=subprocess.run(['java','-Xmx64m','-cp',str(w),'org.coh.nativecombined.CurrentCaptureExportControls',str(w/'capture')],check=True,capture_output=True,text=True,timeout=60)
        result=json.loads(r.stdout)
    assert pins=={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}
    result['source_unchanged']=True;result['source_sha256']=pins;result['scope']='Exact MainActivity selector, genuine capture store/PNG and APK-report identity; Android/JSON/service collaborators explicit host doubles.'
    print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
