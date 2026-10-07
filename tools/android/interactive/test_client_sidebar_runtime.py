"""Execute the shipped Runtime command gates/queue with controlled transport races."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT/'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'


def method(text, signature):
    start = text.index(signature)
    cursor = text.index('{', start)
    depth = 1
    end = cursor + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def harness():
    source = (JAVA/'ClientRuntime.java').read_text()
    signatures = (
        'public synchronized boolean requestEnter(',
        'public boolean isPerformanceCommandPending(',
        'private boolean performanceCommandInputAllowed(',
        'public synchronized boolean canSendPerformanceCommand(',
        'public synchronized boolean requestPerformanceCommand(',
        'private synchronized void completePerformanceCommand(',
        'private boolean gameplayInputAllowed(',
        'private boolean queueInput(String selectedSession, InputWrite action)',
        'private synchronized boolean queueInput(String selectedSession, InputWrite action, boolean gameplay)',
        'private synchronized boolean queueInput(String selectedSession, InputWrite action, boolean gameplay, long performanceToken)',
        'private void queueRelease(',
        'private void cancelPendingInput(',
        'public synchronized boolean canRequestSaveLogout(',
        'private boolean taskControlsAvailable(',
        'private boolean taskInputAvailable(',
    )
    actual = '\n'.join(method(source, name) for name in signatures)
    events = '\n'.join(method(source, name) for name in (
        'if(taskAcceptedEvent==null && taskControlsAvailable()',
        'if(taskCompletedEvent==null && taskCompletionRequested && taskAcceptedEvent!=null',
    ))
    return r'''
package io.github.russianranger.cohclientinteractive;
import java.io.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
final class SystemClock {static long uptimeMillis(){return System.nanoTime()/1000000;}}
final class Budget {boolean move=true;int revision(){return 1;}boolean canMove(long n){return move;}boolean canSave(long n){return true;}}
final class JSONObject extends LinkedHashMap<String,Object> {
 JSONObject getJSONObject(String name){return (JSONObject)get(name);}
}
final class InteractiveRfbClient {
 static final class InputCancelledException extends IOException {}
 final AtomicLong generation=new AtomicLong();
 final CountDownLatch entered=new CountDownLatch(1),proceed=new CountDownLatch(1);
 final List<String> writes=Collections.synchronizedList(new ArrayList<>());
 volatile boolean hold;
 long inputEpoch(){return generation.get();}
 void cancelPendingInput(){generation.incrementAndGet();}
 void sendEnter(long epoch)throws IOException {if(epoch!=inputEpoch())throw new InputCancelledException();writes.add("enter");}
 void sendPerformanceCommand(String name,long epoch)throws IOException {
  entered.countDown();
  while(hold&&proceed.getCount()>0) {
   if(epoch!=inputEpoch())throw new InputCancelledException();
   try{proceed.await(10,TimeUnit.MILLISECONDS);}catch(InterruptedException e){throw new InputCancelledException();}
  }
  if(epoch!=inputEpoch())throw new InputCancelledException();writes.add(name);
 }
 void requestFullUpdate()throws IOException {}
 void releaseAllInputs()throws IOException {writes.add("release");}
}
public final class SidebarRuntimeHost {
 static void require(boolean ok){if(!ok)throw new AssertionError();}
 static final class ClientRuntime {
  boolean reopen=true,inputReady=true,finishRequested,finished,cancelled,producerCompleted;
  boolean connectedCapturedReady,saveLogoutRequested,stuckRequested,relocationCapturedReady;
  boolean taskContactRequested,taskCompletionRequested,performanceCommandPending;
  long performanceCommandGeneration,observedClientPid=17,inputSent,inputFailed,lastInputUptime,lastInputFrameWatermark,decodedFrames,lastInputRefresh,clientWindowObservedUptime=1;
  Object characterConnectedEvent,characterSavedEvent,taskContactReceipt,taskCompletionReceipt;
  JSONObject taskAcceptedEvent,taskCompletedEvent;
  String session="owned";
  Budget sessionBudget=new Budget();
  InteractiveRfbClient decoder=new InteractiveRfbClient();
  ThreadPoolExecutor inputWorker=new ThreadPoolExecutor(1,1,0,TimeUnit.MILLISECONDS,new ArrayBlockingQueue<Runnable>(128));
  List<String> log=Collections.synchronizedList(new ArrayList<>());
  private interface InputWrite {void write(InteractiveRfbClient active,long epoch)throws IOException;}
  void recordLifecycle(String event){log.add(event);}
  void stage(String title,String detail){}
  void notifyInputState(){}
  Object jsonValue(Object value){return value;}
  boolean taskSaveReady(){return true;}
  boolean taskGateRequired(){return true;}
  void inputFailure(String detail){inputFailed++;inputReady=false;cancelPendingInput();}
  void releaseAllInputs(String session){queueRelease(session,false);}
  void releaseOnInputWorker(){try{decoder.releaseAllInputs();}catch(IOException failure){inputFailure("release");}}
  void world(){connectedCapturedReady=true;characterConnectedEvent=new Object();}
  void idle()throws Exception {inputWorker.submit(()->{}).get(2,TimeUnit.SECONDS);}
  void close()throws Exception {inputWorker.shutdownNow();inputWorker.awaitTermination(2,TimeUnit.SECONDS);}
ACTUAL_METHODS
  void observeTask(JSONObject event)throws Exception {ACTUAL_EVENTS}
 }
 static void gates()throws Exception {
  ClientRuntime r=new ClientRuntime();
  try {
   require(!r.canSendPerformanceCommand());require(!r.requestPerformanceCommand(ClientInput.PerformanceCommand.FPS_30));
   require(r.requestEnter("owned"));r.idle();require(r.decoder.writes.equals(Arrays.asList("enter")));
   require(!r.requestEnter("foreign"));
   r.world();require(r.canSendPerformanceCommand());require(!r.requestPerformanceCommand(null));
   r.saveLogoutRequested=true;require(!r.canSendPerformanceCommand());r.saveLogoutRequested=false;
   r.characterSavedEvent=new Object();require(!r.canSendPerformanceCommand());r.characterSavedEvent=null;
   r.stuckRequested=true;require(!r.canSendPerformanceCommand());r.relocationCapturedReady=true;
   require(r.canSendPerformanceCommand());r.stuckRequested=false;
   r.taskContactRequested=true;require(!r.canSendPerformanceCommand());r.taskContactReceipt=new Object();
   require(r.canSendPerformanceCommand());r.taskCompletionRequested=true;require(!r.canSendPerformanceCommand());
   r.taskCompletionReceipt=new Object();require(r.canSendPerformanceCommand());
   r.sessionBudget.move=false;require(!r.canSendPerformanceCommand());r.sessionBudget.move=true;
   r.cancelled=true;require(!r.canSendPerformanceCommand());r.cancelled=false;
   r.producerCompleted=true;require(!r.canSendPerformanceCommand());r.producerCompleted=false;
   r.finished=true;require(!r.canSendPerformanceCommand());r.finished=false;
   r.inputReady=false;require(!r.canSendPerformanceCommand());r.inputReady=true;
   r.finishRequested=true;require(!r.canSendPerformanceCommand());r.finishRequested=false;
   r.observedClientPid=-1;require(!r.canSendPerformanceCommand());r.observedClientPid=17;
   r.connectedCapturedReady=false;require(!r.canSendPerformanceCommand());r.connectedCapturedReady=true;
   r.reopen=false;require(!r.canSendPerformanceCommand());
  }finally{r.close();}
 }
 static void dispatch(boolean cancel,boolean replace)throws Exception {
  ClientRuntime r=new ClientRuntime();r.world();r.decoder.hold=true;InteractiveRfbClient original=r.decoder;
  try {
   require(r.requestPerformanceCommand(ClientInput.PerformanceCommand.FPS_30));
   require(original.entered.await(1,TimeUnit.SECONDS));
   require(r.isPerformanceCommandPending()&&!r.canSendPerformanceCommand());
   require(!r.canRequestSaveLogout()&&!r.taskInputAvailable());require(r.taskControlsAvailable());
   require(!r.requestEnter("owned"));require(!r.queueInput("owned",(a,e)->a.writes.add("foreign input"),true));
   if(cancel)r.queueRelease("owned",true);else r.queueRelease("owned",false);
   if(replace)r.decoder=new InteractiveRfbClient();
   original.proceed.countDown();r.idle();
   require(!r.isPerformanceCommandPending()&&r.inputFailed==0);
   if(cancel){require(!original.writes.contains("cap_30"));require(r.inputSent==0);}
   else {require(original.writes.equals(Arrays.asList("cap_30","release")));require(r.inputSent==1);}
   for(String line:r.log)require(!line.contains("/maxfps")&&!line.contains("offline"));
   require(r.log.stream().anyMatch(x->x.contains("performance_command_dispatch name=cap_30 dispatch_utc_ms=")));
   require(cancel||r.log.stream().anyMatch(x->x.contains("native_effect_verified=false")));
  }finally{r.close();}
 }
 static JSONObject taskEvent(ClientRuntime r,String type) {
  JSONObject task=new JSONObject();task.put("name","Demons and Gangsters");task.put("context",7);
  task.put("subhandle",0);task.put("task_index",0);
  JSONObject event=new JSONObject();event.put("type",type);event.put("session_id",r.session);
  event.put("client_pid",r.observedClientPid);event.put("character_id",1);event.put("active_task_count",1);
  event.put("native_task_verified",true);event.put("sql_task_verified",true);event.put("observed_utc_ms",System.currentTimeMillis());
  event.put("task",task);return event;
 }
 static void taskEvidenceWhileCommandPending()throws Exception {
  ClientRuntime r=new ClientRuntime();r.world();r.session="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";r.decoder.hold=true;
  try {
   require(r.requestPerformanceCommand(ClientInput.PerformanceCommand.SHOW_FPS));
   require(r.decoder.entered.await(1,TimeUnit.SECONDS));
   require(r.isPerformanceCommandPending()&&!r.taskInputAvailable()&&r.taskControlsAvailable());
   JSONObject wrong=taskEvent(r,"character_task_accepted");wrong.put("session_id","foreign");
   r.observeTask(wrong);require(r.taskAcceptedEvent==null);
   JSONObject accepted=taskEvent(r,"character_task_accepted");
   require(ClientAcceptance.taskEvent(accepted,"character_task_accepted",r.session,r.observedClientPid));
   r.observeTask(accepted);require(r.taskAcceptedEvent==accepted);
   r.taskCompletionRequested=true;r.taskCompletionReceipt=new Object();
   JSONObject completed=taskEvent(r,"character_task_completed");
   require(ClientAcceptance.taskEvent(completed,"character_task_completed",r.session,r.observedClientPid));
   r.observeTask(completed);require(r.taskCompletedEvent==completed);
   require(r.isPerformanceCommandPending());r.decoder.proceed.countDown();r.idle();
   require(r.taskAcceptedEvent==accepted&&r.taskCompletedEvent==completed&&r.taskInputAvailable());
   require(ClientAcceptance.taskSaveReady(accepted,completed,3,3,r.session,r.observedClientPid));
  }finally{r.decoder.proceed.countDown();r.close();}
 }
 static void queuedIdentity()throws Exception {
  for(int mode=0;mode<4;mode++) {
   ClientRuntime r=new ClientRuntime();r.world();CountDownLatch blocker=new CountDownLatch(1);
   try {
    r.inputWorker.execute(()->{try{blocker.await();}catch(InterruptedException ignored){}});
    require(r.requestPerformanceCommand(ClientInput.PerformanceCommand.FPS_10));
    if(mode==0)r.decoder=new InteractiveRfbClient();
    if(mode==1)r.observedClientPid=999;
    if(mode==2)r.sessionBudget.move=false;
    if(mode==3)r.session="foreign";
    blocker.countDown();r.idle();require(!r.isPerformanceCommandPending()&&r.inputSent==0&&r.inputFailed==0);
    require(r.decoder.writes.isEmpty());
   }finally{blocker.countDown();r.close();}
  }
 }
 public static void main(String[] args)throws Exception {gates();dispatch(false,false);dispatch(true,false);queuedIdentity();taskEvidenceWhileCommandPending();System.out.println("PASS shipped runtime gates, queue identity, ordered release, pause cancellation, safe submission logs and native task evidence during pending commands");}
}
'''.replace('ACTUAL_METHODS', actual).replace('ACTUAL_EVENTS', events)


class SidebarRuntimeTests(unittest.TestCase):
    def test_actual_runtime_queue_requires_world_identity_and_preserves_cancellation(self):
        with tempfile.TemporaryDirectory(prefix='coh-sidebar-runtime-') as temporary:
            output=Path(temporary)
            source=output/'SidebarRuntimeHost.java'
            source.write_text(harness())
            subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','--release','8','-d',str(output),str(JAVA/'ClientInput.java'),str(JAVA/'ClientAcceptance.java'),str(source)],check=True,capture_output=True,text=True)
            result=subprocess.run(['java','-cp',str(output),'io.github.russianranger.cohclientinteractive.SidebarRuntimeHost'],check=True,capture_output=True,text=True,timeout=15)
            self.assertIn('PASS shipped runtime gates',result.stdout)


if __name__=='__main__':
    unittest.main()
