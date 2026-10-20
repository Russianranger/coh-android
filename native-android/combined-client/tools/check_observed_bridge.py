#!/usr/bin/env python3
"""Execute exact Activity pose-bridge methods with deterministic host doubles."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path

def extract(text,name):
 m=re.search(r'    private void '+re.escape(name)+r'\(',text);assert m,name
 at=text.index('{',m.end());depth=0;quote=None;escaped=False
 for i in range(at,len(text)):
  c=text[i]
  if quote:
   if escaped:escaped=False
   elif c=='\\':escaped=True
   elif c==quote:quote=None
  elif c in '\"\'':quote=c
  elif c=='{':depth+=1
  elif c=='}':
   depth-=1
   if not depth:return text[m.start():i+1]
 raise ValueError('unclosed '+name)
HEADER=r'''
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayDeque;
final class ObservedBridgeTest {
 enum NetworkMode {LOCAL,WORLD_HANDOFF}
 NetworkMode networkMode=NetworkMode.WORLD_HANDOFF;
 volatile long networkHandle=101,networkOwnerAttempt=10,networkAttempt=10,handle=900,observedEntityAttempt=-1;
 volatile int observedEntityIndex=-1;
 boolean destroying,networkForeground=true,networkRequested=true,charactersPublished;
 String networkReport="{}";long policyCheckedAt=1000;
 Handler main=new Handler();Handoff handoffState=new Handoff();Ui networkStatus=new Ui();
 int publications,events,uiUpdates,saves,suspends,fullscreenRequests,fullscreenStep;boolean fullscreenEnabled;
 void setSceneFullscreen(boolean enabled){fullscreenRequests++;fullscreenEnabled=enabled;fullscreenStep=++SessionNative.sequence;}
 JSONObject localPolicy(){return new JSONObject("{}");}
 boolean sameNetworkPolicy(JSONObject p){return true;}
 void publishNetwork(){publications++;}
 void suspendNetwork(){suspends++;}
 void showCharacters(JSONArray v,long attempt){}
 void event(String name){events++;}
 void updateNetworkUi(){uiUpdates++;}
 void saveReport(){saves++;}
'''
TESTS=r'''
 static int checks;
 static void need(boolean b,String why){checks++;if(!b)throw new AssertionError(why+" ["+checks+"]");}
 static ObservedBridgeTest fresh(){InteropNative.reset();SessionNative.reset();return new ObservedBridgeTest();}
 static byte[] pose(int index,float x,float y,float z){return ByteBuffer.allocate(16).order(ByteOrder.LITTLE_ENDIAN).putInt(index).putFloat(x).putFloat(y).putFloat(z).array();}
 public static void main(String[] args){
  ObservedBridgeTest t=fresh();InteropNative.raw=pose(27,123.25f,-74.5f,0.125f);
  t.networkTick();need(InteropNative.queries==1&&InteropNative.lastHandle==101,"getter uses exact owner handle");need(SessionNative.requests==0&&t.fullscreenRequests==0&&t.main.q.size()==1,"UI publication and fullscreen transition are deferred");t.main.drain();
  need(SessionNative.requests==1&&SessionNative.handle==900&&SessionNative.index==27,"exact renderer bridge signature");
  need(t.fullscreenRequests==(BuildConfig.FULLSCREEN_DIAGNOSTIC?1:0),"profile controls fullscreen invocation");
  need(!BuildConfig.FULLSCREEN_DIAGNOSTIC||(t.fullscreenEnabled&&t.fullscreenStep<SessionNative.poseStep),"fullscreen requested before real pose bridge");need(SessionNative.x==123.25f&&SessionNative.y==-74.5f&&SessionNative.z==0.125f,"little-endian pose decoded");need(t.observedEntityAttempt==10&&t.observedEntityIndex==27,"same owner attempt recorded");need(t.events==1&&t.uiUpdates==1&&t.saves==1,"single UI report notification");
  t.networkTick();t.main.drain();need(InteropNative.queries==1&&SessionNative.requests==1&&t.fullscreenRequests==(BuildConfig.FULLSCREEN_DIAGNOSTIC?1:0),"published attempt and fullscreen request deduplicated");
  // Old owner tick already queued ahead of a newly requested connection.
  t=fresh();t.networkAttempt=11;t.networkTick();t.main.drain();need(InteropNative.controls==0&&InteropNative.queries==0&&SessionNative.requests==0,"queued old owner cannot be retagged with new attempt");
  // Reconnect occurs while servicing an old owner, before getter/publication.
  t=fresh();final ObservedBridgeTest serviceRace=t;t.handoffState.service=true;InteropNative.onService=()->{serviceRace.networkAttempt=11;serviceRace.clearObservedBox();};t.networkTick();t.main.drain();need(InteropNative.services==1&&InteropNative.queries==0&&SessionNative.requests==0,"service race refuses old pose before getter");
  // Replacement occurs during JNI getter, before the posted callback executes.
  t=fresh();final ObservedBridgeTest queryRace=t;InteropNative.onQuery=()->{queryRace.networkAttempt=11;queryRace.networkOwnerAttempt=11;queryRace.networkHandle=202;queryRace.clearObservedBox();};t.publishObservedSelf(101,10);t.main.drain();need(SessionNative.requests==0&&t.observedEntityAttempt==-1,"getter race cannot publish into replacement");
  for(int change=0;change<9;change++){
   t=fresh();t.publishObservedSelf(101,10);need(t.main.q.size()==1,"valid pose queued before mutation");
   if(change==0)t.networkAttempt++;if(change==1)t.networkOwnerAttempt++;if(change==2)t.networkHandle++;if(change==3)t.networkRequested=false;if(change==4)t.networkForeground=false;if(change==5)t.destroying=true;if(change==6)t.handle=0;if(change==7)t.networkMode=NetworkMode.LOCAL;if(change==8){t.networkAttempt++;t.clearObservedBox();}
   t.main.drain();need(SessionNative.requests==0&&t.observedEntityAttempt==-1,"posted callback cannot cross lifecycle/owner/clear change "+change);need(t.fullscreenRequests==0,"stale callback cannot request fullscreen "+change);
  }
  for(int bad=0;bad<3;bad++){t=fresh();if(bad==0)t.networkHandle=202;if(bad==1)t.networkAttempt=11;if(bad==2)t.networkOwnerAttempt=11;t.publishObservedSelf(101,10);need(InteropNative.queries==0&&t.main.q.isEmpty(),"wrong owner tuple rejected before getter");}
  for(byte[] raw:new byte[][]{null,new byte[0],new byte[15],new byte[17]}){t=fresh();InteropNative.raw=raw;t.publishObservedSelf(101,10);t.main.drain();need(SessionNative.requests==0&&t.fullscreenRequests==0&&t.main.q.isEmpty(),"null/size refusal");}
  for(float bad:new float[]{Float.NaN,Float.POSITIVE_INFINITY,Float.NEGATIVE_INFINITY})for(int axis=0;axis<3;axis++){t=fresh();float[] p={1,2,3};p[axis]=bad;InteropNative.raw=pose(1,p[0],p[1],p[2]);t.publishObservedSelf(101,10);t.main.drain();need(SessionNative.requests==0&&t.fullscreenRequests==0&&t.main.q.isEmpty(),"nonfinite pose refused");}
  t=fresh();InteropNative.raw=pose(-1,1,2,3);t.publishObservedSelf(101,10);t.main.drain();need(SessionNative.requests==0,"negative index refused");
  t=fresh();t.publishObservedSelf(101,10);t.publishObservedSelf(101,10);t.main.drain();need(SessionNative.requests==1,"queued duplicate publications collapse");
  t.clearObservedBox();need(t.observedEntityAttempt==-1&&t.observedEntityIndex==-1&&SessionNative.clears==1&&SessionNative.clearHandle==900,"clear resets marker and native renderer");t.handle=0;t.clearObservedBox();need(SessionNative.clears==1,"no clear against absent renderer");
  // A later coherent owner can publish normally after old queued work refused.
  t=fresh();t.publishObservedSelf(101,10);t.networkHandle=202;t.networkAttempt=t.networkOwnerAttempt=11;t.clearObservedBox();InteropNative.raw=pose(7,-1,-2,-3);t.publishObservedSelf(202,11);t.main.drain();need(SessionNative.requests==1&&SessionNative.index==7&&t.observedEntityAttempt==11,"new owner is not poisoned by stale queued pose");
  System.out.println("{\"passed\":true,\"checks\":"+checks+",\"exact_activity_methods\":3,\"fullscreen_branch\":"+BuildConfig.FULLSCREEN_DIAGNOSTIC+",\"Android_or_native_execution\":false,\"collaborators_are_doubles\":true}");
 }
}
final class BuildConfig {static final boolean FULLSCREEN_DIAGNOSTIC=Boolean.getBoolean("coh.fullscreen");}
final class Handler {final ArrayDeque<Runnable>q=new ArrayDeque<>();void post(Runnable r){q.add(r);}void drain(){while(!q.isEmpty())q.remove().run();}}
final class Handoff {boolean service;void control(int bits){}boolean shouldService(){return service;}boolean charactersReady(){return false;}}
final class SystemClock {static long elapsedRealtime(){return 1000;}}
final class JSONObject {JSONObject(String raw){}String optString(String key,String value){return "WAIT_ALLENTS";}String optString(String key){return "WAIT_ALLENTS";}}
final class JSONArray {JSONArray(String raw){}}
final class Ui {void setText(String text){}}
final class InteropNative {
 static byte[]raw;static int queries,controls,services;static long lastHandle;static Runnable onService,onQuery;
 static void reset(){raw=ByteBuffer.allocate(16).order(ByteOrder.LITTLE_ENDIAN).putInt(1).putFloat(1).putFloat(2).putFloat(3).array();queries=controls=services=0;lastHandle=0;onService=onQuery=null;}
 static int controlState(long h){controls++;return 1;}
 static int service(long h,long now){services++;if(onService!=null)onService.run();return 0;}
 static byte[] observedSelfPose(long h){queries++;lastHandle=h;byte[]value=raw;if(onQuery!=null)onQuery.run();return value;}
 static byte[]characters(long h){return null;}
}
final class LocalNative {static int service(long h,long now){return 0;}static byte[]characters(long h){return null;}}
final class SessionNative {
 static int requests,clears,index,sequence,poseStep;static long handle,clearHandle;static float x,y,z;
 static void reset(){requests=clears=index=sequence=poseStep=0;handle=clearHandle=0;x=y=z=0;}
 static void observedEntity(long h,int i,float a,float b,float c){poseStep=++sequence;requests++;handle=h;index=i;x=a;y=b;z=c;}
 static void clearObservedEntity(long h){clears++;clearHandle=h;}
}
'''

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();source=a.source_root.resolve()/'native-android/combined-client/app/src/main/java/org/coh/nativecombined/NativeClientActivity.java';raw=source.read_bytes();text=raw.decode();assert 'networkOwnerAttempt=attempt;'in text and 'networkOwnerAttempt=-1;'in text
 names=['networkTick','publishObservedSelf','clearObservedBox'];methods={n:extract(text,n)for n in names};work=a.work.resolve();work.mkdir(parents=True,exist_ok=False);java=work/'ObservedBridgeTest.java';java.write_text(HEADER+'\n'.join(methods.values())+TESTS)
 result=subprocess.run(['java','-Xmx128m','com.sun.tools.javac.Main','--release','8','-d',str(work),str(java)],capture_output=True,text=True,timeout=60)
 if result.returncode:raise RuntimeError(result.stderr)
 profiles={}
 for profile in ('legacy','fullscreen'):
  result=subprocess.run(['java','-Xmx64m','-Dcoh.fullscreen='+str(profile=='fullscreen').lower(),'-cp',str(work),'ObservedBridgeTest'],capture_output=True,text=True,timeout=30)
  if result.returncode:raise RuntimeError(result.stdout+result.stderr)
  profiles[profile]=json.loads(result.stdout);assert profiles[profile]['fullscreen_branch']==(profile=='fullscreen')
 assert source.read_bytes()==raw,'source changed during focused qualification';v=profiles['legacy'].copy();v.update(profiles=profiles,checks=sum(x['checks']for x in profiles.values()),activity_sha256=hashlib.sha256(raw).hexdigest(),exact_method_sha256={n:hashlib.sha256(x.encode()).hexdigest()for n,x in methods.items()},source_unchanged_during_test=True,scope='Exact Java Activity owner-tuple/posted-callback bridge only; Android/JNI/render/network collaborators are explicit doubles.');a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
if __name__=='__main__':main()
