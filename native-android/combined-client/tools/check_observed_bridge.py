#!/usr/bin/env python3
"""Execute exact Activity pose/costume bridges and FD helper with host doubles."""
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
package org.coh.nativecombined;
import android.os.ParcelFileDescriptor;
import io.github.russianranger.cohdiagnostic.AssetPackStore;
import java.io.*;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayDeque;
import java.util.SortedMap;
import java.util.TreeMap;
final class ObservedBridgeTest extends android.content.Context {
 enum NetworkMode {LOCAL,WORLD_HANDOFF}
 NetworkMode networkMode=NetworkMode.WORLD_HANDOFF;
 volatile long networkHandle=101,networkOwnerAttempt=10,networkAttempt=10,handle=900,observedEntityAttempt=-1;
 volatile int observedEntityIndex=-1;
 boolean destroying,networkForeground=true,networkRequested=true,charactersPublished;
 String networkReport="{}";long policyCheckedAt=1000;
 Handler main=new Handler();Handoff handoffState=new Handoff();Ui networkStatus=new Ui();
 int captureViewportPublications;long captureViewportEpoch;
 void publishCaptureViewport(){captureViewportPublications++;captureViewportEpoch=epoch;}
 int publications,events,uiUpdates,saves,suspends,fullscreenRequests,fullscreenStep;boolean fullscreenEnabled;
 long costumeReadAttempt=-1,actorPreparationSequence,epoch=1;boolean actorPreparing,resumed=true,renderQueued;
 ImportContract.Control actorControl;String runtimeActorFailure="",failure,lastEvent;Surface currentSurface=new Surface();
 Worker renderWorker=new Worker();
 void setSceneFullscreen(boolean enabled){fullscreenRequests++;fullscreenEnabled=enabled;fullscreenStep=++SessionNative.sequence;}
 JSONObject localPolicy(){return new JSONObject("{}");}
 boolean sameNetworkPolicy(JSONObject p){return true;}
 void publishNetwork(){publications++;}
 void suspendNetwork(){suspends++;}
 void showCharacters(JSONArray v,long attempt){}
 void event(String name){events++;lastEvent=name;}
 void updateNetworkUi(){uiUpdates++;}
 void saveReport(){saves++;}
'''
TESTS=r'''
 static int checks;
 static void need(boolean b,String why){checks++;if(!b)throw new AssertionError(why+" ["+checks+"]");}
 static ObservedBridgeTest fresh(){ImportContract.externalMetadata=false;ImportStore.extraArchives=0;InteropNative.reset();SessionNative.reset();RuntimeWorldInputs.reset();ParcelFileDescriptor.reset();return new ObservedBridgeTest();}
 static byte[] pose(int index,float x,float y,float z){return ByteBuffer.allocate(16).order(ByteOrder.LITTLE_ENDIAN).putInt(index).putFloat(x).putFloat(y).putFloat(z).array();}
 CONTINUATION_TEST_METHODS
 public static void main(String[] args)throws Exception{
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
  if(BuildConfig.CONTINUATION_DIAGNOSTIC){continuationTests();inputTests();}
  System.out.println("{\"passed\":true,\"checks\":"+checks+",\"exact_activity_methods\":5,\"continuation_branch\":"+BuildConfig.CONTINUATION_DIAGNOSTIC+",\"fullscreen_branch\":"+BuildConfig.FULLSCREEN_DIAGNOSTIC+",\"Android_or_native_execution\":false,\"collaborators_are_doubles\":true}");
 }
}
final class BuildConfig {static final boolean FULLSCREEN_DIAGNOSTIC=Boolean.getBoolean("coh.fullscreen");static final boolean CONTINUATION_DIAGNOSTIC=Boolean.getBoolean("coh.continuation");}
final class Handler {final ArrayDeque<Runnable>q=new ArrayDeque<>();void post(Runnable r){q.add(r);}void one(){ObservedBridgeTest.need(!q.isEmpty(),"queued main callback available");q.remove().run();}void drain(){while(!q.isEmpty())q.remove().run();}}
final class Handoff {boolean service;void control(int bits){}boolean shouldService(){return service;}boolean charactersReady(){return false;}}
final class SystemClock {static long elapsedRealtime(){return 1000;}}
final class JSONObject {String key;JSONObject(String raw){key=raw;}JSONObject getJSONObject(String name){return new JSONObject(name);}String optString(String key,String value){return "WAIT_ALLENTS";}String optString(String key){return "WAIT_ALLENTS";}}
final class JSONArray {JSONArray(String raw){}}
final class Ui {void setText(String text){}}
final class InteropNative {
 static byte[]raw,costume;static int queries,controls,services,costumeQueries,sourceQueries;static long lastHandle,sourceBytes;static Runnable onService,onQuery,onCostumeQuery;
 static void reset(){raw=ByteBuffer.allocate(16).order(ByteOrder.LITTLE_ENDIAN).putInt(1).putFloat(1).putFloat(2).putFloat(3).array();queries=controls=services=costumeQueries=sourceQueries=0;lastHandle=0;sourceBytes=1432908;costume=null;onService=onQuery=onCostumeQuery=null;}
 static int controlState(long h){controls++;return 1;}
 static int service(long h,long now){services++;if(onService!=null)onService.run();return 0;}
 static byte[] observedSelfPose(long h){queries++;lastHandle=h;byte[]value=raw;if(onQuery!=null)onQuery.run();return value;}
 static byte[]observedSelfCostume(long h){costumeQueries++;lastHandle=h;byte[]value=costume;if(onCostumeQuery!=null)onCostumeQuery.run();return value;}
 static long observedSelfCostumeSourceBytes(long h){sourceQueries++;ObservedBridgeTest.need(h==101||h==202,"source charge belongs to supplied transport handle");return sourceBytes;}
 static byte[]characters(long h){return null;}
}
final class LocalNative {static int service(long h,long now){return 0;}static byte[]characters(long h){return null;}}
final class SessionNative {
 static int requests,clears,index,sequence,poseStep,costumes,states,renders,admitResult;static long handle,clearHandle,actorHandle,staging,source;static float x,y,z;static boolean active;static Runnable onCostume;static ObservedBridgeTest actor;
 static void reset(){requests=clears=index=sequence=poseStep=costumes=states=renders=admitResult=0;handle=clearHandle=actorHandle=staging=source=0;x=y=z=0;active=true;onCostume=null;actor=null;}
 static void observedEntity(long h,int i,float a,float b,float c){poseStep=++sequence;requests++;handle=h;index=i;x=a;y=b;z=c;}
 static void state(long h,long epoch,boolean value){ObservedBridgeTest.need(h!=0&&epoch>0,"explicit renderer/epoch state");states++;active=value;}
 static int observedCostume(long h,byte[]frame,int[]fds,long[]offsets,long[]lengths,long bytes,long charged){ObservedBridgeTest.need(actor!=null&&actor.actorPreparing&&!active,"no active EGL while preparing");ObservedBridgeTest.need(frame==InteropNative.costume&&frame.length==48384&&fds.length==2&&offsets.length==2&&lengths.length==2,"exact copied frame and bounded FD arrays");ObservedBridgeTest.need(ParcelFileDescriptor.live==2&&fds[0]>=0&&fds[1]>=0&&offsets[0]==0&&offsets[1]==0&&lengths[0]==4096&&lengths[1]==8192,"two pinned archive spans remain open for synchronous native call");costumes++;actorHandle=h;staging=bytes;source=charged;if(onCostume!=null)onCostume.run();return admitResult;}
 static int render(long h,Surface surface,long epoch){ObservedBridgeTest.need(actor==null||!actor.actorPreparing,"render never enters preparation");renders++;return 0;}
 static void clearObservedEntity(long h){clears++;clearHandle=h;}
}
'''

CONTINUATION_TESTS=r"""
 static ObservedBridgeTest actorFresh(){ObservedBridgeTest t=fresh();t.observedEntityAttempt=t.networkAttempt;t.observedEntityIndex=125;InteropNative.costume=new byte[48384];SessionNative.actor=t;return t;}
 static void queueActor(ObservedBridgeTest t){t.publishObservedCostume(101,10);need(t.main.q.size()==1,"actor UI start queued");t.main.one();need(t.actorPreparing&&!SessionNative.active&&t.renderWorker.q.size()==1,"EGL stopped before queued preparation");}
 static void continuationTests(){
  ObservedBridgeTest t=actorFresh();queueActor(t);t.requestRender();need(t.renderWorker.q.size()==1&&!t.renderQueued,"preparation blocks EGL queue");t.publishObservedCostume(101,10);need(InteropNative.costumeQueries==1,"actor attempt read once");t.renderWorker.one();need(SessionNative.costumes==1&&SessionNative.actorHandle==900&&SessionNative.staging==48424&&SessionNative.source==1432908,"frame and concrete source charge forwarded without changing native result");need(ParcelFileDescriptor.opened==2&&ParcelFileDescriptor.closed==2&&ParcelFileDescriptor.live==0,"FDs closed before UI completion");need(t.actorPreparing&&!SessionNative.active,"preparation stays exclusive through completion handoff");t.main.one();need(!t.actorPreparing&&t.actorControl==null&&SessionNative.active&&"observed_costume_published".equals(t.lastEvent)&&t.saves==1,"success resumes EGL and reports one publication");need(t.renderQueued&&t.renderWorker.q.size()==1,"success schedules rendering");t.renderWorker.one();need(SessionNative.renders==1,"EGL can run after preparation");
  need(t.captureViewportPublications==1&&t.captureViewportEpoch==t.epoch,"actor completion renews current fullscreen capture ticket");
  for(int bad=0;bad<5;bad++){t=actorFresh();if(bad==0)t.networkHandle++;if(bad==1)t.networkAttempt++;if(bad==2)t.networkOwnerAttempt++;if(bad==3)t.observedEntityAttempt=-1;if(bad==4)t.networkMode=NetworkMode.LOCAL;t.publishObservedCostume(101,10);need(InteropNative.costumeQueries==0&&t.main.q.isEmpty(),"actor tuple/mode rejected before getter "+bad);}
  t=actorFresh();InteropNative.costume=null;t.publishObservedCostume(101,10);need(t.costumeReadAttempt==-1&&InteropNative.sourceQueries==0,"missing snapshot may retry");InteropNative.costume=new byte[48384];InteropNative.sourceBytes=-1;t.publishObservedCostume(101,10);need(t.costumeReadAttempt==-1&&t.main.q.isEmpty(),"unknown source charge may retry");InteropNative.sourceBytes=1432908;t.publishObservedCostume(101,10);need(t.main.q.size()==1&&t.costumeReadAttempt==10,"later admitted snapshot is not poisoned");
  t=actorFresh();final ObservedBridgeTest getterRace=t;InteropNative.onCostumeQuery=()->{getterRace.networkHandle=202;getterRace.networkAttempt=getterRace.networkOwnerAttempt=11;getterRace.clearObservedBox();};t.publishObservedCostume(101,10);t.main.drain();need(SessionNative.costumes==0&&t.renderWorker.q.isEmpty(),"getter replacement cannot enqueue actor");
  for(int change=0;change<10;change++){t=actorFresh();t.publishObservedCostume(101,10);if(change==0)t.networkAttempt++;if(change==1)t.networkOwnerAttempt++;if(change==2)t.networkHandle++;if(change==3)t.networkRequested=false;if(change==4)t.networkForeground=false;if(change==5)t.destroying=true;if(change==6)t.handle=0;if(change==7)t.networkMode=NetworkMode.LOCAL;if(change==8)t.clearObservedBox();if(change==9)t.observedEntityAttempt=-1;t.main.drain();need(t.renderWorker.q.isEmpty()&&SessionNative.costumes==0&&RuntimeWorldInputs.opens==0,"posted actor callback refuses stale/lifecycle change "+change);}
  for(int change=0;change<10;change++){t=actorFresh();queueActor(t);if(change==0)t.networkAttempt++;if(change==1)t.networkOwnerAttempt++;if(change==2)t.networkHandle++;if(change==3)t.networkRequested=false;if(change==4)t.networkForeground=false;if(change==5)t.destroying=true;if(change==6)t.handle=901;if(change==7)t.networkMode=NetworkMode.LOCAL;if(change==8)t.clearObservedBox();if(change==9)t.observedEntityAttempt=-1;t.renderWorker.one();t.main.drain();need(SessionNative.costumes==0&&ParcelFileDescriptor.live==0&&ParcelFileDescriptor.opened==ParcelFileDescriptor.closed,"queued CPU work closes all FDs and refuses stale actor "+change);need(!SessionNative.active&&SessionNative.renders==0,"stale CPU result does not resume old renderer "+change);}
  for(int change=0;change<10;change++){t=actorFresh();queueActor(t);t.renderWorker.one();need(SessionNative.costumes==1&&ParcelFileDescriptor.live==0,"successful synchronous native return precedes completion race");if(change==0)t.networkAttempt++;if(change==1)t.networkOwnerAttempt++;if(change==2)t.networkHandle++;if(change==3)t.networkRequested=false;if(change==4)t.networkForeground=false;if(change==5)t.destroying=true;if(change==6)t.handle=901;if(change==7)t.networkMode=NetworkMode.LOCAL;if(change==8)t.clearObservedBox();if(change==9)t.observedEntityAttempt=-1;t.main.drain();need(!SessionNative.active&&SessionNative.renders==0&&t.saves==0&&t.events==0,"stale completed candidate cannot resume or notify replacement "+change);}
  for(int status:new int[]{5,7}){t=actorFresh();SessionNative.admitResult=status;queueActor(t);t.renderWorker.one();t.main.one();need(t.costumeReadAttempt==-1&&!t.actorPreparing&&SessionNative.active&&"observed_costume_box_fallback".equals(t.lastEvent),"native lifecycle result is retryable "+status);int before=InteropNative.costumeQueries;t.publishObservedCostume(101,10);need(InteropNative.costumeQueries==before+1&&t.main.q.size()==1,"same owner can retry after lifecycle result "+status);t.main.one();t.renderWorker.one();need(SessionNative.renders==0,"old queued render ticket cannot run during retry prep");t.renderWorker.one();need(SessionNative.costumes==2&&ParcelFileDescriptor.live==0,"retry remains bounded and closes both sources "+status);}
  t=actorFresh();SessionNative.admitResult=2;queueActor(t);t.renderWorker.one();t.main.one();need(t.costumeReadAttempt==10&&!t.runtimeActorFailure.isEmpty(),"source/material failure retains box without retry loop");need(t.captureViewportPublications==1&&t.captureViewportEpoch==t.epoch,"box fallback renews capture ticket");
  t=actorFresh();RuntimeWorldInputs.failOpenAt=2;queueActor(t);t.renderWorker.one();t.main.one();need(ParcelFileDescriptor.opened==1&&ParcelFileDescriptor.closed==1&&ParcelFileDescriptor.live==0&&SessionNative.costumes==0&&!t.actorPreparing&&SessionNative.active&&"observed_costume_box_fallback".equals(t.lastEvent),"archive failure closes input and restores box rendering");
  t=actorFresh();queueActor(t);final StringBuilder longProblem=new StringBuilder();for(int i=0;i<300;i++)longProblem.append('x');SessionNative.onCostume=()->{throw new IllegalStateException(longProblem.toString());};t.renderWorker.one();t.main.one();need(ParcelFileDescriptor.opened==2&&ParcelFileDescriptor.closed==2&&ParcelFileDescriptor.live==0&&t.runtimeActorFailure.length()==160&&!t.actorPreparing&&SessionNative.active,"native Java exception closes sources and bounds optional failure text");
  t=actorFresh();queueActor(t);ImportContract.Control cancelled=t.actorControl;t.resumed=false;t.networkForeground=false;t.networkRequested=false;t.networkAttempt++;t.clearObservedBox();need(cancelled.isCancelled()&&t.costumeReadAttempt==-1&&!t.actorPreparing,"pause clear cancels active import and resets attempt");t.renderWorker.one();t.main.drain();need(SessionNative.costumes==0&&ParcelFileDescriptor.opened==0&&!SessionNative.active,"cancelled pending preparation opens nothing and never resumes EGL");t.networkForeground=t.networkRequested=t.resumed=true;t.networkAttempt=t.networkOwnerAttempt=11;t.networkHandle=202;t.observedEntityAttempt=11;t.publishObservedCostume(202,11);t.main.one();t.renderWorker.one();t.main.one();need(SessionNative.costumes==1&&t.costumeReadAttempt==11&&SessionNative.active,"fresh resumed owner can publish after cancelled work");
  t=actorFresh();queueActor(t);final ObservedBridgeTest midRead=t;RuntimeWorldInputs.onOpen=()->{if(RuntimeWorldInputs.opens==2){midRead.networkAttempt++;midRead.clearObservedBox();}};t.renderWorker.one();t.main.drain();need(SessionNative.costumes==0&&ParcelFileDescriptor.opened==2&&ParcelFileDescriptor.closed==2&&ParcelFileDescriptor.live==0,"cancel during archive acquisition closes every acquired FD");
  t=actorFresh();queueActor(t);final ObservedBridgeTest midNative=t;SessionNative.admitResult=5;SessionNative.onCostume=()->{midNative.networkAttempt++;midNative.clearObservedBox();};t.renderWorker.one();t.main.drain();need(SessionNative.costumes==1&&ParcelFileDescriptor.live==0&&!SessionNative.active&&t.costumeReadAttempt==-1,"cancel during synchronous native preparation cannot resume stale EGL");
 }
 static void inputTests()throws Exception{
  if(System.getProperty("coh.archive.manifest")!=null){fresh();ImportContract.externalMetadata=true;RuntimeActorInputs actual=RuntimeActorInputs.open(null,new ImportStore(null,(a,b,c)->{}),new ImportContract.Control());need(actual.fds.length==Integer.getInteger("coh.archive.count")&&actual.lengths[0]==859075775L&&actual.lengths[1]==1663681523L&&actual.stagingPayloadBytes()==20L*actual.fds.length,"actual018 descriptor yields all11 loaded archives with existingCLIENT/zones priority");boolean reference=false;for(long bytes:actual.lengths)if(bytes==615541018L)reference=true;need(reference,"actual reference archive is included from descriptor metadata");actual.close();need(ParcelFileDescriptor.live==0&&ParcelFileDescriptor.closed==11,"all actual descriptor sources are released");}

  fresh();ImportStore.extraArchives=1;RuntimeActorInputs all=RuntimeActorInputs.open(null,new ImportStore(null,(a,b,c)->{}),new ImportContract.Control());need(all.fds.length==3&&all.lengths[0]==4096&&all.lengths[1]==8192&&all.lengths[2]==16384&&all.stagingPayloadBytes()==60,"reference archive follows existing CLIENT/zones precedence");all.close();need(ParcelFileDescriptor.live==0&&ParcelFileDescriptor.closed==3,"all imported sources released");
  fresh();ImportStore.extraArchives=14;all=RuntimeActorInputs.open(null,new ImportStore(null,(a,b,c)->{}),new ImportContract.Control());need(all.fds.length==16&&all.stagingPayloadBytes()==320,"maximum descriptor array payload charged");all.close();need(ParcelFileDescriptor.live==0&&ParcelFileDescriptor.closed==16,"maximum imported source set closes fully");
  fresh();ImportStore.extraArchives=15;try{RuntimeActorInputs.open(null,new ImportStore(null,(a,b,c)->{}),new ImportContract.Control());throw new AssertionError("descriptor capacity ignored");}catch(IOException expected){need(ParcelFileDescriptor.opened==0,"descriptor capacity checked before opening");}

  fresh();RuntimeActorInputs inputs=RuntimeActorInputs.open(null,new ImportStore(null,(a,b,c)->{}),new ImportContract.Control());need(ParcelFileDescriptor.live==2&&inputs.fds.length==2&&inputs.fds[0]>=0&&inputs.fds[1]>=0&&inputs.offsets[0]==0&&inputs.offsets[1]==0&&inputs.lengths[0]==4096&&inputs.lengths[1]==8192&&inputs.stagingPayloadBytes()==40,"actual helper keeps bounded pinned archive spans");inputs.close();need(ParcelFileDescriptor.live==0&&inputs.fds[0]==-1&&inputs.fds[1]==-1&&inputs.lengths[0]==0&&inputs.lengths[1]==0,"actual close clears exported arrays");inputs.close();need(ParcelFileDescriptor.closed==2,"actual close is idempotent");
  fresh();RuntimeWorldInputs.failOpenAt=2;try{RuntimeActorInputs.open(null,new ImportStore(null,(a,b,c)->{}),new ImportContract.Control());throw new AssertionError("second archive failure admitted");}catch(IOException expected){need(ParcelFileDescriptor.opened==1&&ParcelFileDescriptor.closed==1&&ParcelFileDescriptor.live==0,"second open failure closes first archive");}
  fresh();ParcelFileDescriptor.failGetFd=1;try{RuntimeActorInputs.open(null,new ImportStore(null,(a,b,c)->{}),new ImportContract.Control());throw new AssertionError("FD failure admitted");}catch(IllegalStateException expected){need(ParcelFileDescriptor.opened==1&&ParcelFileDescriptor.closed==1&&ParcelFileDescriptor.live==0,"getFd failure closes already acquired descriptor");}
  fresh();ImportContract.Control control=new ImportContract.Control();control.cancel();try{RuntimeActorInputs.open(null,new ImportStore(null,(a,b,c)->{}),control);throw new AssertionError("cancel admitted");}catch(InterruptedIOException expected){need(ParcelFileDescriptor.opened==0,"initial cancellation opens nothing");}
  fresh();control=new ImportContract.Control();final ImportContract.Control cancelling=control;RuntimeWorldInputs.onOpen=()->cancelling.cancel();try{RuntimeActorInputs.open(null,new ImportStore(null,(a,b,c)->{}),control);throw new AssertionError("mid-open cancel admitted");}catch(InterruptedIOException expected){need(ParcelFileDescriptor.opened==1&&ParcelFileDescriptor.closed==1&&ParcelFileDescriptor.live==0,"mid-open cancellation closes acquired descriptor");}
  fresh();inputs=RuntimeActorInputs.open(null,new ImportStore(null,(a,b,c)->{}),new ImportContract.Control());ParcelFileDescriptor.failClose=true;try{inputs.close();throw new AssertionError("close failures ignored");}catch(IOException expected){need(expected.getSuppressed().length==1&&ParcelFileDescriptor.closed==2&&ParcelFileDescriptor.live==0&&inputs.fds[0]==-1&&inputs.fds[1]==-1,"both close errors retained and arrays cleared");}inputs.close();need(ParcelFileDescriptor.closed==2,"failed-close owner remains idempotently retired");
  fresh();RuntimeWorldInputs.failOpenAt=2;ParcelFileDescriptor.failClose=true;try{RuntimeActorInputs.open(null,new ImportStore(null,(a,b,c)->{}),new ImportContract.Control());throw new AssertionError("combined open/close failure ignored");}catch(IOException expected){need(expected.getSuppressed().length==1&&ParcelFileDescriptor.closed==1&&ParcelFileDescriptor.live==0,"primary open failure retains cleanup exception");}
 }
"""
HELPERS=r"""
final class Worker {final ArrayDeque<Runnable>q=new ArrayDeque<>();void execute(Runnable r){q.add(r);}void one(){ObservedBridgeTest.need(!q.isEmpty(),"queued render-worker task available");q.remove().run();}}
final class Surface {boolean valid=true;boolean isValid(){return valid;}}
final class ImportContract {
 interface Progress {void update(String phase,long done,long total);}
 static final class Control {boolean cancelled;void cancel(){cancelled=true;}boolean isCancelled(){return cancelled;}void check()throws InterruptedIOException{if(cancelled)throw new InterruptedIOException("test cancellation");}}
 static final class Pin {final long bytes;final String sha256;Pin(long bytes){this(bytes,"0000000000000000000000000000000000000000000000000000000000000000");}Pin(long bytes,String sha256){this.bytes=bytes;this.sha256=sha256;}}
 final JSONObject runtimeManifest=new JSONObject("manifest");
 static Pin pin(JSONObject value){return new Pin(value.key.equals("client-visual-assets.zip")?4096:8192);}
 static Pin pin(org.json.JSONObject value){return new Pin(value.getLong("bytes"),value.getString("sha256"));}
 static boolean externalMetadata;
 static byte[] asset(android.content.Context context,String name,int limit)throws IOException{
  ObservedBridgeTest.need(name.equals("runtime/asset-pack-manifest.json")&&limit==1048576,"actual helper requests shipped bounded descriptor");
  if(externalMetadata)return java.nio.file.Files.readAllBytes(java.nio.file.Paths.get(System.getProperty("coh.archive.manifest")));
  String zero="0000000000000000000000000000000000000000000000000000000000000000";
  StringBuilder raw=new StringBuilder("{\"format\":1,\"files\":{\"runtime/client-visual-assets.zip\":{\"bytes\":4096,\"sha256\":\"").append(zero).append("\"},\"runtime/zones-world-supplement.zip\":{\"bytes\":8192,\"sha256\":\"").append(zero).append("\"}");
  for(int i=0;i<ImportStore.extraArchives;i++)raw.append(",\"").append(i==0?"atlas/atlas-assets.zip":"atlas/optional"+i+".zip").append("\":{\"bytes\":16384,\"sha256\":\"").append(zero).append("\"}");
  return raw.append("}}").toString().getBytes(StandardCharsets.UTF_8);
 }
}
final class ImportStore {static int extraArchives;ImportStore(Object activity,ImportContract.Progress progress){}AssetPackStore assetStore(ImportContract.Control control)throws IOException{control.check();return new AssetPackStore();}ImportContract contract(){return new ImportContract();}}
final class RuntimeWorldInputs {
 static int opens,failOpenAt;static Runnable onOpen;
 static void reset(){opens=failOpenAt=0;onOpen=null;}
 static ParcelFileDescriptor openArchive(File file,ImportContract.Pin pin)throws IOException{opens++;ObservedBridgeTest.need(SessionNative.actor==null||!SessionNative.active,"archive acquisition starts only after EGL stop");if(onOpen!=null)onOpen.run();if(opens==failOpenAt)throw new IOException("test archive open failure");ObservedBridgeTest.need(ImportContract.externalMetadata?(pin.bytes>=22&&pin.sha256.matches("[0-9a-f]{64}")):((file.getPath().endsWith("client-visual-assets.zip")&&pin.bytes==4096)||(file.getPath().endsWith("zones-world-supplement.zip")&&pin.bytes==8192)||(file.getPath().startsWith("atlas/")&&pin.bytes==16384)),"exact declared archive and supplied pin");return ParcelFileDescriptor.openFixture();}
}
"""
FD_DOUBLE=r"""
package android.os;
import java.io.IOException;
public final class ParcelFileDescriptor implements AutoCloseable {
 public static int opened,closed,live,failGetFd;public static boolean failClose;private final int ordinal;private boolean done;
 private ParcelFileDescriptor(int value){ordinal=value;}
 public static void reset(){opened=closed=live=failGetFd=0;failClose=false;}
 public static ParcelFileDescriptor openFixture(){opened++;live++;return new ParcelFileDescriptor(opened);}
 public int getFd(){if(ordinal==failGetFd)throw new IllegalStateException("test getFd failure");return 100+ordinal;}
 public void close()throws IOException{if(done)return;done=true;closed++;live--;if(failClose)throw new IOException("test close failure "+ordinal);}
}
"""
PACK_DOUBLE=r"""
package io.github.russianranger.cohdiagnostic;
import java.io.File;
public final class AssetPackStore {public File resolve(String path){return new File(path);}}
"""

CONTEXT_DOUBLE=r"""
package android.content;
public class Context { }
"""
METADATA_JSON_DOUBLE=r"""
package org.json;
import java.util.*;
import java.util.regex.*;
/** Explicit host double for this flat metadata shape; not Android JSON qualification. */
public final class JSONObject {
 private final Map<String,JSONObject> values=new LinkedHashMap<>();private long bytes;private String sha;
 public JSONObject(String raw){
  if(!raw.contains("\"files\""))throw new IllegalArgumentException("files missing");
  Matcher rows=Pattern.compile("\\\"([^\\\"]+)\\\"\\s*:\\s*\\{([^{}]*)\\}").matcher(raw);
  while(rows.find()){
   Matcher b=Pattern.compile("\\\"bytes\\\"\\s*:\\s*(\\d+)").matcher(rows.group(2));
   Matcher h=Pattern.compile("\\\"sha256\\\"\\s*:\\s*\\\"([0-9a-f]{64})\\\"").matcher(rows.group(2));
   if(b.find()&&h.find()){JSONObject value=new JSONObject();value.bytes=Long.parseLong(b.group(1));value.sha=h.group(1);values.put(rows.group(1),value);}
  }
 }
 private JSONObject(){}
 public JSONObject getJSONObject(String key){if(key.equals("files"))return this;JSONObject value=values.get(key);if(value==null)throw new IllegalArgumentException(key);return value;}
 public Iterator<String> keys(){return values.keySet().iterator();}
 public long getLong(String key){if(!key.equals("bytes"))throw new IllegalArgumentException(key);return bytes;}
 public String getString(String key){if(!key.equals("sha256"))throw new IllegalArgumentException(key);return sha;}
}
"""

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--archive-manifest',type=Path);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 a=p.parse_args();root=a.source_root.resolve();base=root/'native-android/combined-client/app/src/main/java/org/coh/nativecombined'
 source=base/'NativeClientActivity.java';raw=source.read_bytes();text=raw.decode()
 inputs=base/'RuntimeActorInputs.java';input_raw=inputs.read_bytes()
 assert 'networkOwnerAttempt=attempt;'in text and 'networkOwnerAttempt=-1;'in text
 names=['networkTick','publishObservedSelf','clearObservedBox','publishObservedCostume','requestRender'];methods={n:extract(text,n)for n in names}
 work=a.work.resolve();work.mkdir(parents=True,exist_ok=False)
 java=work/'ObservedBridgeTest.java';java.write_text(HEADER+'\n'.join(methods.values())+TESTS.replace(' CONTINUATION_TEST_METHODS',CONTINUATION_TESTS)+HELPERS)
 helper=work/'RuntimeActorInputs.java';helper.write_bytes(input_raw)
 fd=work/'android/os/ParcelFileDescriptor.java';fd.parent.mkdir(parents=True);fd.write_text(FD_DOUBLE)
 pack=work/'io/github/russianranger/cohdiagnostic/AssetPackStore.java';pack.parent.mkdir(parents=True);pack.write_text(PACK_DOUBLE)
 context=work/'android/content/Context.java';context.parent.mkdir(parents=True);context.write_text(CONTEXT_DOUBLE)
 metadata=work/'org/json/JSONObject.java';metadata.parent.mkdir(parents=True);metadata.write_text(METADATA_JSON_DOUBLE)
 metadata_args=[]
 if a.archive_manifest:
  raw_metadata=a.archive_manifest.read_bytes();actual_metadata=json.loads(raw_metadata);count=sum(n.lower().endswith('.zip')for n in actual_metadata['files']);assert count==11
  fixture=work/'asset-pack-manifest.json';fixture.write_bytes(raw_metadata);metadata_args=['-Dcoh.archive.manifest='+str(fixture),'-Dcoh.archive.count='+str(count)]
 result=subprocess.run(['java','-Xmx128m','com.sun.tools.javac.Main','--release','8','-d',str(work),str(java),str(helper),str(fd),str(pack),str(context),str(metadata)],capture_output=True,text=True,timeout=60)
 if result.returncode:raise RuntimeError(result.stderr)
 profiles={}
 for profile in ('legacy','fullscreen','continuation'):
  result=subprocess.run(['java','-Xmx64m',*metadata_args,'-Dcoh.fullscreen='+str(profile!='legacy').lower(),'-Dcoh.continuation='+str(profile=='continuation').lower(),'-cp',str(work),'org.coh.nativecombined.ObservedBridgeTest'],capture_output=True,text=True,timeout=30)
  if result.returncode:raise RuntimeError(result.stdout+result.stderr)
  profiles[profile]=json.loads(result.stdout)
  assert profiles[profile]['fullscreen_branch']==(profile!='legacy') and profiles[profile]['continuation_branch']==(profile=='continuation')
 assert source.read_bytes()==raw and inputs.read_bytes()==input_raw,'source changed during focused qualification'
 v=profiles['legacy'].copy();v.update(profiles=profiles,checks=sum(x['checks']for x in profiles.values()),activity_sha256=hashlib.sha256(raw).hexdigest(),runtime_inputs_sha256=hashlib.sha256(input_raw).hexdigest(),exact_method_sha256={n:hashlib.sha256(x.encode()).hexdigest()for n,x in methods.items()},source_unchanged_during_test=True,scope='Exact Java Activity pose/costume/queued-render methods and unchanged RuntimeActorInputs source; Android/JNI/native/render/network/archive/pin collaborators are explicit host doubles. No Android, EGL, asset hash or native actor acceptance claim.')
 if a.archive_manifest:v.update(actual_archive_manifest_sha256=hashlib.sha256(raw_metadata).hexdigest(),actual_archive_descriptors=count,metadata_JSON_and_Context_are_explicit_host_doubles=True)
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
if __name__=='__main__':main()
