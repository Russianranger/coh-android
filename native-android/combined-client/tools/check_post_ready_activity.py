#!/usr/bin/env python3
"""Exact optional replay Activity/export hooks with explicit host I/O/JNI doubles."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

HARNESS=r'''
package org.coh.nativecombined;
import java.io.*;
import java.util.*;
import java.util.zip.*;
import android.os.ParcelFileDescriptor;
import org.json.JSONObject;
public final class PostReadyActivityControls {
 enum NetworkMode {LOCAL,WORLD_HANDOFF}
 NetworkMode networkMode=NetworkMode.WORLD_HANDOFF;long networkHandle=900,sessionStarted=0xcafe20;
 String postReadyReplayMetadata,postReadyReplayFailure;boolean postReadyReplayStorageReady,postReadyReplayAttempted;
 final File directory;Object service=null;JSONObject storedCombined=new JSONObject().put("version_code",18);
 final Handoff handoffState=new Handoff();boolean networkRequested=true;
 PostReadyActivityControls(File dir){directory=dir;}
 File getFilesDir(){return directory;}String getPackageName(){return "org.coh.nativecombined";}
 void saveInitialReplay(){Trace.add("initial");}
 /*ACTIVITY*/
 /*MAIN_CONTEXT*/
 JSONObject exportReplay(JSONObject captureReport)throws Exception{
  JSONObject combined=new JSONObject();ByteArrayOutputStream output=new ByteArrayOutputStream();
  try(ZipOutputStream zip=new ZipOutputStream(output)){
   /*MAIN_EXPORT*/
  }
  return combined;
 }
 static int checks;
 static void need(boolean value,String why){checks++;if(!value)throw new AssertionError(why+" ["+checks+"]");}
 static PostReadyActivityControls fresh(File dir){BuildConfig.POST_READY_REPLAY_DIAGNOSTIC=true;Trace.values.clear();InteropNative.reset();PostReadyReplayStore.reset();ParcelFileDescriptor.reset();return new PostReadyActivityControls(dir);}
 static JSONObject report(long version,String session,String sha){return new JSONObject().put("session_id",session)
  .put("app",new JSONObject().put("package","org.coh.nativecombined").put("version_code",version))
  .put("post_ready_replay",new JSONObject().put("app_version",version).put("activity_session",session).put("sha256",sha));}
 static void excluded(PostReadyActivityControls app,JSONObject report,String reason)throws Exception{
  int before=PostReadyReplayStore.appends;need(reason.equals(app.postReadyReplayContextFailure(report)),"context refusal "+reason);
  JSONObject result=app.exportReplay(report).optJSONObject("post_ready_replay_export");
  need(result!=null&&Boolean.FALSE.equals(result.opt("included"))&&reason.equals(result.optString("omission_reason")),"export omission reported "+reason);
  need(PostReadyReplayStore.appends==before,"bad context never opens replay output");
 }
 public static void main(String[]args)throws Exception{
  File dir=new File(args[0]);PostReadyActivityControls app;
  for(int guard=0;guard<3;guard++){
   app=fresh(dir);if(guard==0)BuildConfig.POST_READY_REPLAY_DIAGNOSTIC=false;if(guard==1)app.networkMode=NetworkMode.LOCAL;if(guard==2)app.networkHandle=0;
   app.preparePostReadyReplay();app.savePostReadyReplay();need(PostReadyReplayStore.prepares==0&&InteropNative.configures==0&&InteropNative.controls==0,"inactive profile/mode/handle owns no replay I/O "+guard);
  }
  for(int failure=1;failure<=6;failure++){
   app=fresh(dir);if(failure==1)PostReadyReplayStore.prepareFailure=1;if(failure==2)InteropNative.configureStatus=3;if(failure==3)InteropNative.configureThrows=true;
   if(failure==4)ParcelFileDescriptor.openFailure=true;if(failure==5)PostReadyReplayStore.prepareFailure=2;if(failure==6)ParcelFileDescriptor.closeFailure=true;
   app.preparePostReadyReplay();
   need(app.networkHandle==900&&app.networkRequested&&!app.postReadyReplayStorageReady,"optional configure failure leaves transport usable "+failure);
   need(app.postReadyReplayFailure!=null&&app.postReadyReplayMetadata==null,"optional failure explicitly reported "+failure);
   need(ParcelFileDescriptor.live==0&&ParcelFileDescriptor.opened==ParcelFileDescriptor.closed,"every attached Java FD closed "+failure);
   need(InteropNative.stops==0&&PostReadyReplayStore.seals==0,"configure failure neither stops network nor seals "+failure);
  }
  app=fresh(dir);app.preparePostReadyReplay();
  need(app.postReadyReplayStorageReady&&"POST_READY_REPLAY_RECORDING".equals(app.postReadyReplayFailure),"successful attachment records pending state");
  need(InteropNative.configures==1&&InteropNative.lastHandle==900&&InteropNative.lastFd==77&&InteropNative.nativeDuplicates==1,"native duplicates exact descriptor on exact owner");
  need(ParcelFileDescriptor.opened==1&&ParcelFileDescriptor.closed==1&&ParcelFileDescriptor.live==0,"Java attachment closes before next service");
  for(int state:new int[]{0,1}){InteropNative.control=state;app.savePostReadyReplay();need(!app.postReadyReplayAttempted&&PostReadyReplayStore.seals==0,"live/pending observation cannot seal "+state);}
  InteropNative.control=3;app.savePostReadyReplay();
  need(app.postReadyReplayAttempted&&PostReadyReplayStore.seals==1&&"sealed".equals(app.postReadyReplayMetadata)&&app.postReadyReplayFailure==null,"terminal seals exactly once");
  need(PostReadyReplayStore.version==20&&"cafe20".equals(PostReadyReplayStore.session),"seal uses installed version and current Activity session");
  app.savePostReadyReplay();need(PostReadyReplayStore.seals==1,"repeat terminal publications cannot reseal");
  for(int failure=1;failure<=2;failure++){
   app=fresh(dir);app.preparePostReadyReplay();InteropNative.control=3;PostReadyReplayStore.sealFailure=failure;app.savePostReadyReplay();app.savePostReadyReplay();
   need(PostReadyReplayStore.seals==1&&app.postReadyReplayAttempted&&app.postReadyReplayMetadata==null&&app.postReadyReplayFailure!=null,"failed seal is explicit and bounded "+failure);
   need(app.networkHandle==900&&InteropNative.stops==0,"seal failure cannot abort transport "+failure);
  }
  for(boolean suspend:new boolean[]{true,false}){
   app=fresh(dir);app.preparePostReadyReplay();Trace.values.clear();if(suspend)app.suspendNetwork();else app.disconnectNetwork();
   need(Trace.values.equals(Arrays.asList("initial",suspend?"suspend":"disconnect","control","seal","stopped")),"terminal native flush precedes Java seal and handoff retirement");
   need(PostReadyReplayStore.seals==1&&app.handoffState.stops==1&&ParcelFileDescriptor.live==0,"terminal hook retains sealed evidence and releases Java FD");
  }
  app=fresh(dir);app.networkMode=NetworkMode.LOCAL;app.suspendNetwork();app.disconnectNetwork();need(LocalNative.stops==2&&PostReadyReplayStore.seals==0&&InteropNative.stops==0,"other connection mode unchanged");
  app=fresh(dir);String valid=PostReadyReplayStore.actualHash;
  need(app.service==null&&app.storedCombined.optLong("version_code",-1)==18&&BuildConfig.VERSION_CODE==20,"service-absent old report setup");
  excluded(app,report(18,"cafe18",valid),"POST_READY_REPLAY_APP_VERSION_MISMATCH");
  JSONObject oldMetadata=report(20,"cafe20",valid);oldMetadata.optJSONObject("post_ready_replay").put("app_version",19);excluded(app,oldMetadata,"POST_READY_REPLAY_APP_VERSION_MISMATCH");
  JSONObject staleSession=report(20,"cafe20",valid);staleSession.optJSONObject("post_ready_replay").put("activity_session","cafe19");excluded(app,staleSession,"POST_READY_REPLAY_ACTIVITY_SESSION_MISMATCH");
  excluded(app,report(20,"NOT-A-SESSION",valid),"POST_READY_REPLAY_ACTIVITY_SESSION_MISMATCH");
  excluded(app,report(20,"cafe20","short"),"POST_READY_REPLAY_HASH_UNAVAILABLE");excluded(app,report(20,"cafe20",valid.toUpperCase(Locale.ROOT)),"POST_READY_REPLAY_HASH_UNAVAILABLE");
  excluded(app,null,"POST_READY_REPLAY_REPORT_UNAVAILABLE");
  JSONObject absent=report(20,"cafe20",valid);absent.put("post_ready_replay",null).put("post_ready_replay_error","POST_READY_REPLAY_STORAGE_IOException");excluded(app,absent,"POST_READY_REPLAY_STORAGE_IOException");
  JSONObject wrongPackage=report(20,"cafe20",valid);wrongPackage.optJSONObject("app").put("package","other.app");excluded(app,wrongPackage,"POST_READY_REPLAY_APP_VERSION_MISMATCH");
  JSONObject current=report(20,"cafe20",valid);need(app.postReadyReplayContextFailure(current)==null,"current installed app/session/hash context accepted");
  JSONObject result=app.exportReplay(current).optJSONObject("post_ready_replay_export");need(Boolean.TRUE.equals(result.opt("included"))&&result.opt("omission_reason")==JSONObject.NULL,"current replay appended and reported");
  need(PostReadyReplayStore.exportVersion==20&&"cafe20".equals(PostReadyReplayStore.exportSession)&&PostReadyReplayStore.exportHash.equals(valid),"exact installed context and expected hash reach store");
  JSONObject wrongHash=report(20,"cafe20",valid.replace('a','b'));need(app.postReadyReplayContextFailure(wrongHash)==null,"syntactically valid hash alone is not file admission");
  result=app.exportReplay(wrongHash).optJSONObject("post_ready_replay_export");need(Boolean.FALSE.equals(result.opt("included"))&&"POST_READY_REPLAY_FILE_UNAVAILABLE_OR_MISMATCH".equals(result.optString("omission_reason")),"file hash mismatch remains explicit");
  BuildConfig.POST_READY_REPLAY_DIAGNOSTIC=false;int appends=PostReadyReplayStore.appends;need(app.exportReplay(current).optJSONObject("post_ready_replay_export")==null&&PostReadyReplayStore.appends==appends,"legacy profile never exports replay");
  System.out.println("{\"passed\":true,\"checks\":"+checks+",\"installed_version\":20,\"exact_activity_methods\":4,\"exact_Main_context_and_export\":true,\"Android_or_native_execution\":false,\"collaborators_are_doubles\":true}");
 }
}
final class BuildConfig {static final int VERSION_CODE=20;static boolean POST_READY_REPLAY_DIAGNOSTIC=true;}
final class Trace {static final List<String> values=new ArrayList<>();static void add(String value){values.add(value);}}
final class Handoff {int stops;void stopped(){stops++;Trace.add("stopped");}}
final class InteropNative {
 static int configureStatus,configures,controls,control,stops,lastFd,nativeDuplicates;static long lastHandle;static boolean configureThrows;
 static void reset(){configureStatus=configures=controls=control=stops=lastFd=nativeDuplicates=0;lastHandle=0;configureThrows=false;LocalNative.stops=0;}
 static int configurePostReadyReplay(long h,int fd){configures++;lastHandle=h;lastFd=fd;if(configureThrows)throw new IllegalStateException("explicit native configure failure");if(configureStatus==0)nativeDuplicates++;return configureStatus;}
 static int controlState(long h){controls++;lastHandle=h;Trace.add("control");return control;}
 static void suspend(long h){stops++;control=3;Trace.add("suspend");}static void disconnect(long h){stops++;control=3;Trace.add("disconnect");}
}
final class LocalNative {static int stops;static void suspend(long h){stops++;}static void disconnect(long h){stops++;}}
final class PostReadyReplayStore {
 static int prepares,seals,appends,prepareFailure,sealFailure;static long version,exportVersion;static String session,exportSession,exportHash;
 static final String actualHash=new String(new char[64]).replace('\0','a');
 static void reset(){prepares=seals=appends=prepareFailure=sealFailure=0;version=exportVersion=0;session=exportSession=exportHash=null;}
 static File prepare(File dir)throws IOException{prepares++;if(prepareFailure==1)throw new IOException("explicit prepare failure");if(prepareFailure==2)throw new OutOfMemoryError("explicit optional memory failure");return new File(dir,"post-ready-replay.tmp");}
 static String seal(File dir,long v,String s)throws IOException{seals++;Trace.add("seal");version=v;session=s;if(sealFailure==1)throw new IOException("explicit seal failure");if(sealFailure==2)throw new OutOfMemoryError("explicit optional memory failure");return "sealed";}
 static boolean append(File dir,ZipOutputStream zip,String hash,long v,String s)throws IOException{appends++;exportHash=hash;exportVersion=v;exportSession=s;if(!actualHash.equals(hash))return false;zip.putNextEntry(new ZipEntry("post-ready-replay.bin"));zip.write(1);zip.closeEntry();return true;}
}
'''

JSON_STUB=r'''package org.json;import java.util.*;public class JSONObject {
 public static final Object NULL=new Object();Map<String,Object> values=new HashMap<>();
 public JSONObject put(String k,Object v){values.put(k,v);return this;}public Object opt(String k){return values.get(k);}
 public JSONObject optJSONObject(String k){Object v=values.get(k);return v instanceof JSONObject?(JSONObject)v:null;}
 public JSONObject getJSONObject(String k){JSONObject v=optJSONObject(k);if(v==null)throw new IllegalArgumentException(k);return v;}
 public String optString(String k){return optString(k,"");}public String optString(String k,String fallback){Object v=values.get(k);return v instanceof String?(String)v:fallback;}
 public long optLong(String k,long fallback){Object v=values.get(k);return v instanceof Number?((Number)v).longValue():fallback;}
}'''
PFD_STUB=r'''package android.os;import java.io.*;public final class ParcelFileDescriptor implements AutoCloseable {
 public static final int MODE_WRITE_ONLY=2;public static int opened,closed,live;public static boolean openFailure,closeFailure;boolean done;
 public static void reset(){opened=closed=live=0;openFailure=closeFailure=false;}
 public static ParcelFileDescriptor open(File f,int mode)throws IOException{if(mode!=MODE_WRITE_ONLY)throw new AssertionError("wrong FD mode");if(openFailure)throw new IOException("explicit open failure");opened++;live++;return new ParcelFileDescriptor();}
 public int getFd(){if(done)throw new AssertionError("closed FD");return 77;}
 public void close()throws IOException{if(done)throw new AssertionError("double close");done=true;closed++;live--;if(closeFailure)throw new IOException("explicit close failure");}
}'''

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[3]);args=parser.parse_args();root=args.source_root.resolve()
    java=root/'native-android/combined-client/app/src/main/java/org/coh/nativecombined';activity=java/'NativeClientActivity.java';main=java/'MainActivity.java';extractor=root/'native-android/session-client/tools/lifecycle_host_check.py'
    method=load('post_ready_activity_extract',extractor).method;act=activity.read_text();launcher=main.read_text()
    signatures=['private void preparePostReadyReplay()','private void savePostReadyReplay()','private void disconnectNetwork()','private void suspendNetwork()']
    bodies='\n'.join(method(act,s)for s in signatures)
    context=method(launcher,'private String postReadyReplayContextFailure(JSONObject report)')
    export=method(launcher,'if(BuildConfig.POST_READY_REPLAY_DIAGNOSTIC)')
    connect=method(act,'private void connectLocalServer(NetworkMode mode)');publish=method(act,'private void publishNetwork()');retire=method(act,'private void retireNetworkOwner()')
    assert connect.index('postReadyReplayStorageReady=false;postReadyReplayAttempted=false;')<connect.index('networkHandle=mode==NetworkMode.WORLD_HANDOFF')<connect.index('preparePostReadyReplay();')<connect.index('publishNetwork();')
    assert publish.index('savePostReadyReplay();')<publish.index('InteropNative.report(networkHandle)')
    assert retire.index('disconnectNetwork();')<retire.index('InteropNative.close(retiring)')
    assert 'BuildConfig.VERSION_CODE' in context and 'combined.optLong' not in context
    paths=[activity,main,java/'InteropNative.java',java/'PostReadyReplayStore.java',java/'ApkReportIdentity.java',extractor,Path(__file__).resolve()]
    pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}
    with tempfile.TemporaryDirectory(prefix='coh-post-ready-activity-')as temp:
        w=Path(temp);sources={
          'org/json/JSONObject.java':JSON_STUB,'android/os/ParcelFileDescriptor.java':PFD_STUB,
          'org/coh/nativecombined/PostReadyActivityControls.java':HARNESS.replace('/*ACTIVITY*/',bodies).replace('/*MAIN_CONTEXT*/',context).replace('/*MAIN_EXPORT*/',export)}
        files=[]
        for name,text in sources.items():
            p=w/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);files.append(p)
        subprocess.run(['java','-Xmx128m','com.sun.tools.javac.Main','--release','8','-d',str(w),str(java/'ApkReportIdentity.java'),*map(str,files)],check=True,timeout=60)
        r=subprocess.run(['java','-Xmx64m','-cp',str(w),'org.coh.nativecombined.PostReadyActivityControls',str(w/'app')],capture_output=True,text=True,check=True,timeout=60)
        data=json.loads(r.stdout)
    assert pins=={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},'Source changed during qualification'
    data.update(source_unchanged=True,source_sha256=pins,source_assertions=4,scope='Exact Activity optional attachment/seal/suspend/disconnect and Main context/export block; Android/PFD/JNI/store/service/JSON collaborators are explicit host doubles. No raw body decoding, real FD/native execution, Android or APK build.')
    print(json.dumps(data,sort_keys=True))
if __name__=='__main__':main()
