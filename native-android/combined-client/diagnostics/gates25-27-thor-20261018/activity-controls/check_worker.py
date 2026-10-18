from pathlib import Path
import hashlib,json,re,subprocess
root=Path('/workspace/scratch/36381ad6133b/coh-android')
out=Path('/workspace/scratch/36381ad6133b/worker-e-handoff-activity')
source=root/'native-android/combined-client/app/src/main/java/org/coh/nativecombined/NativeClientActivity.java'
text=source.read_text()
methods=['connectLocalServer','sameNetworkPolicy','disconnectNetwork','suspendNetwork','retireNetworkOwner','networkTick','storeNetworkReport','publishNetwork']
# Extract the exact complete production methods; only Android/JNI collaborators are doubles.
def extract(name):
 m=re.search(r'    private (?:void|boolean) '+name+r'\(',text)
 if not m: raise RuntimeError(name)
 start=text.index('{',m.end());depth=0;quoted=None;escape=False
 for i in range(start,len(text)):
  c=text[i]
  if quoted:
   if escape:escape=False
   elif c=='\\':escape=True
   elif c==quoted:quoted=None
  elif c in '\"\'':quoted=c
  elif c=='{':depth+=1
  elif c=='}':
   depth-=1
   if depth==0:return text[m.start():i+1]
 raise RuntimeError('unclosed method '+name)
parts=[extract(m) for m in methods]
head=r'''
import java.util.*;
import java.nio.charset.StandardCharsets;
public final class WorkerControls {
 private enum NetworkMode { LOCAL, WORLD_HANDOFF }
 private NetworkMode networkMode=NetworkMode.LOCAL;
 private String networkReport="{\"phase\":\"IDLE\"}";
 private String localNetworkReport=networkReport,interopReport=networkReport;
 private boolean destroying,returningToLauncher,networkConnecting,networkForeground=true,networkRequested,charactersPublished;
 private long networkAttempt,networkHandle,policyCheckedAt;
 private JSONObject networkPolicy;
 private final QueueWorker networkWorker=new QueueWorker();
 private final QueueWorker main=new QueueWorker();
 private final Ui connectButton=new Ui(),handoffButton=new Ui(),characterButtons=new Ui(),charactersScroll=new Ui(),networkStatus=new Ui();
 private JSONObject provided=policy(); private boolean policyFailure;
 private JSONObject localPolicy() {if(policyFailure)throw new RuntimeException("private failure must not export");return provided;}
 private void event(String e){} private void updateNetworkUi(){} private void showCharacters(JSONArray a,long attempt){}
'''
tail=r'''
 static int checks;
 static void check(boolean b,String why){checks++;if(!b)throw new AssertionError(why);}
 static JSONObject policy(){return new JSONObject().put("server_session_id","a").put("import_generation","b").put("account","PRIVATE_ACCOUNT").put("db_address","127.0.0.1").put("db_port",7000).put("net_version",5).put("encryption_required",false).put("outbound_compressed",false);}
 static void clean(){NativeDouble.trace.clear();NativeDouble.throwAt="";}
 static WorkerControls connected(NetworkMode mode){WorkerControls w=new WorkerControls();w.connectLocalServer(mode);w.networkWorker.drain();check(w.networkHandle!=0,"begin admitted");return w;}
 public static void main(String[] args)throws Exception {
  clean();WorkerControls w=connected(NetworkMode.LOCAL);long local=w.networkHandle;
  check(NativeDouble.trace.equals(Arrays.asList("L.begin","L.report")),"default LocalNative begin/report");
  clean();w.connectLocalServer(NetworkMode.WORLD_HANDOFF);w.networkWorker.drain();
  check(NativeDouble.trace.equals(Arrays.asList("L.disconnect","L.report","L.close","I.begin","I.report")),"switch retires previous local owner before interop begin");
  check(w.networkMode==NetworkMode.WORLD_HANDOFF&&w.networkHandle!=local,"exclusive new owner/mode");
  check(w.localNetworkReport.contains("CLOSED")&&w.interopReport.contains("DB_CONNECTING"),"reports retain independent producer state");
  clean();w.networkTick();check(NativeDouble.trace.equals(Arrays.asList("I.service","I.report")),"interop service/report routing");
  NativeDouble.phases.put(w.networkHandle,"CHARACTERS_READY");clean();w.networkTick();check(NativeDouble.trace.equals(Arrays.asList("I.service","I.report","I.characters")),"interop character-list routing");
  clean();w.suspendNetwork();w.disconnectNetwork();check(NativeDouble.trace.equals(Arrays.asList("I.suspend","I.disconnect")),"interop suspend/disconnect routing");
  clean();NativeDouble.throwAt="I.report";boolean failed=false;try{w.retireNetworkOwner();}catch(RuntimeException expected){failed=true;}
  check(failed&&NativeDouble.trace.equals(Arrays.asList("I.disconnect","I.report","I.close")),"report failure still closes exact retiring owner");
  check(w.networkHandle==0&&w.networkPolicy==null,"report failure clears private owner/policy");
  clean();w=connected(NetworkMode.WORLD_HANDOFF);NativeDouble.trace.clear();NativeDouble.throwAt="I.disconnect";failed=false;try{w.retireNetworkOwner();}catch(RuntimeException expected){failed=true;}
  check(failed&&NativeDouble.trace.equals(Arrays.asList("I.disconnect","I.close")),"disconnect failure still closes");
  check(w.networkHandle==0&&w.networkPolicy==null,"disconnect failure retires fields");
  clean();w=connected(NetworkMode.WORLD_HANDOFF);NativeDouble.trace.clear();NativeDouble.throwAt="I.close";failed=false;try{w.retireNetworkOwner();}catch(RuntimeException expected){failed=true;}
  check(failed&&w.networkHandle==0&&w.networkPolicy==null,"close exception retires fields");
  clean();w=connected(NetworkMode.WORLD_HANDOFF);w.networkConnecting=false;w.policyFailure=true;NativeDouble.trace.clear();w.connectLocalServer(NetworkMode.LOCAL);w.networkWorker.drain();
  check(NativeDouble.trace.equals(Arrays.asList("I.disconnect","I.report","I.close")),"invalid replacement policy cannot leave previous owner live");
  check(w.networkHandle==0&&w.networkReport.contains("POLICY_UNAVAILABLE")&&!w.networkReport.contains("private"),"fixed policy refusal has no exception/identity data");
  clean();w=new WorkerControls();w.connectLocalServer(NetworkMode.WORLD_HANDOFF);w.networkRequested=false;w.networkAttempt++;w.networkWorker.drain();
  check(w.networkHandle==0&&NativeDouble.trace.isEmpty(),"stale queued begin is suppressed");
  clean();w=connected(NetworkMode.WORLD_HANDOFF);NativeDouble.trace.clear();w.networkForeground=false;w.networkTick();check(NativeDouble.trace.isEmpty(),"background has no service/reconnect");
  w.networkForeground=true;w.networkRequested=false;w.networkTick();check(NativeDouble.trace.isEmpty(),"stopped request has no service/reconnect");
  w.networkPolicy=policy();check(w.sameNetworkPolicy(policy()),"equal private policy accepted");
  for(String k:new String[]{"server_session_id","import_generation","account","db_address","db_port","net_version","encryption_required","outbound_compressed"}){
   JSONObject changed=policy();Object v=changed.values.get(k);changed.put(k,v instanceof Boolean?!((Boolean)v):v instanceof Integer?((Integer)v)+1:v+"changed");
   check(!w.sameNetworkPolicy(changed),"policy replacement rejected: "+k);
  }
  clean();w=connected(NetworkMode.WORLD_HANDOFF);w.networkReport="{\"phase\":\"INITIAL_OBSERVED\"}";NativeDouble.trace.clear();w.networkTick();check(NativeDouble.trace.isEmpty(),"raw initial terminal never re-services native owner");
  clean();w=connected(NetworkMode.WORLD_HANDOFF);w.provided=policy().put("account","OTHER");SystemClock.now+=1001;NativeDouble.trace.clear();w.networkTick();check(NativeDouble.trace.equals(Arrays.asList("I.suspend","I.report")),"changed account suspends rather than services or reconnects");
  check(w.networkReport.contains("SUSPENDED"),"policy replacement reports suspended");
  System.out.println("{\"checks\":"+checks+",\"methods_extracted\":8,\"native_calls_are_doubles\":true,\"android_execution\":false,\"world_authority\":false}");
 }
}
final class QueueWorker {final ArrayDeque<Runnable> q=new ArrayDeque<>();void execute(Runnable r){q.add(r);}void post(Runnable r){q.add(r);}void drain(){while(!q.isEmpty())q.remove().run();}}
final class Ui {void setEnabled(boolean b){}void removeAllViews(){}void setVisibility(int i){}void setText(String s){}}
final class SystemClock {static long now=1000;static long elapsedRealtime(){return now;}}
final class JSONArray {JSONArray(String s){}}
final class JSONObject {
 final Map<String,Object> values=new HashMap<>();JSONObject(){}JSONObject(String s){java.util.regex.Matcher m=java.util.regex.Pattern.compile("\\\"phase\\\":\\\"([^\\\"]+)\\\"").matcher(s);if(m.find())values.put("phase",m.group(1));}
 JSONObject put(String k,Object v){values.put(k,v);return this;}String getString(String k){return (String)values.get(k);}int getInt(String k){return (Integer)values.get(k);}boolean getBoolean(String k){return (Boolean)values.get(k);}String optString(String k){return optString(k,"");}String optString(String k,String d){return (String)values.getOrDefault(k,d);}
}
final class NativeDouble {
 static final List<String> trace=new ArrayList<>();static final Map<Long,String> phases=new HashMap<>();static String throwAt="";static long next;
 static void hit(String name){trace.add(name);if(name.equals(throwAt))throw new RuntimeException("native collaborator failure");}
 static long begin(String mode){hit(mode+".begin");long h=++next;phases.put(h,"DB_CONNECTING");return h;}
 static int service(String m,long h){hit(m+".service");return 0;}static byte[] chars(String m){hit(m+".characters");return "[]".getBytes(StandardCharsets.UTF_8);}
 static String report(String m,long h){hit(m+".report");return "{\"phase\":\""+phases.get(h)+"\",\"producer\":\""+m+"\"}";}
 static void stop(String m,long h,String action){hit(m+"."+action);if(!action.equals("close"))phases.put(h,action.equals("suspend")?"SUSPENDED":"CLOSED");}
}
'''
wrappers=''
for cls,mode in [('LocalNative','L'),('InteropNative','I')]:
 wrappers+='final class '+cls+' {\n'
 wrappers+=' static long begin(int port,String account,int version,boolean encrypted,boolean compressed,long now){return NativeDouble.begin("'+mode+'");}\n'
 wrappers+=' static int service(long h,long now){return NativeDouble.service("'+mode+'",h);}\n'
 wrappers+=' static byte[] characters(long h){return NativeDouble.chars("'+mode+'");}\n'
 wrappers+=' static String report(long h){return NativeDouble.report("'+mode+'",h);}\n'
 for op in ['disconnect','suspend','close']: wrappers+=' static void '+op+'(long h){NativeDouble.stop("'+mode+'",h,"'+op+'");}\n'
 wrappers+='}\n'
java=head+'\n\n'.join(parts)+tail+wrappers
(out/'WorkerControls.java').write_text(java)
(out/'android/view').mkdir(parents=True,exist_ok=True)
(out/'android/view/View.java').write_text('package android.view; public final class View {public static final int GONE=8;}\n')
java_bin='/usr/lib/jvm/java-17-openjdk-amd64/bin/java'
commands=[[java_bin,'-m','jdk.compiler/com.sun.tools.javac.Main','--release','8','-d',str(out/'classes'),str(out/'WorkerControls.java'),str(out/'android/view/View.java')],[java_bin,'-cp',str(out/'classes'),'WorkerControls']]
results=[]
for i,cmd in enumerate(commands):
 p=subprocess.run(cmd,capture_output=True,text=True)
 (out/f'{i}.stdout').write_text(p.stdout);(out/f'{i}.stderr').write_text(p.stderr)
 results.append({'command':cmd,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
 if p.returncode:print(json.dumps(results,indent=2));raise SystemExit(p.returncode)
classes={str(p.relative_to(out)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in (out/'classes').rglob('*.class')}
checks={
 'explicit_mode_button':'handoffButton.setText("Test world handoff")' in text,
 'legacy_button_selects_local':'connectLocalServer(NetworkMode.LOCAL)' in text,
 'character_choice_dispatches_interop':'InteropNative.choose(networkHandle,slot,SystemClock.elapsedRealtime())' in text,
 'attempt_guard_on_choice':'networkHandle!=0&&networkForeground&&networkRequested&&attempt==networkAttempt' in text,
 'pause_dispatches_same_owner':'if(networkHandle!=0) { suspendNetwork(); publishNetwork(); }' in text,
 'destroy_uses_finally_retirement':'networkWorker.execute(this::retireNetworkOwner)' in text,
 'separate_export_labels':'.put("server_protocol",new JSONObject(localNetworkReport)).put("world_handoff",new JSONObject(interopReport))' in text,
 'export_frozen_before_document_picker':'frozenExport=report().toString(2).getBytes(StandardCharsets.UTF_8)' in text,
 'preview_not_world':'.put("preview_is_server_world",false)' in text,
 'interop_status_explicit_false':'World authority: false. The scene remains a local preview.' in text,
 'policy_not_in_export':'networkPolicy' not in text[text.index('    private JSONObject report()'):text.index('    private final Runnable poll=')],
}
if not all(checks.values()):raise RuntimeError(checks)
report={'schema':'coh-handoff-activity-focused-worker-e-v1','scope':'exact eight production worker methods compiled as Java8 and executed with explicit Android/JNI doubles; source controls cover remaining Activity routing/export/lifecycle','activity_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'activity_bytes':source.stat().st_size,'commands':results,'source_controls':checks,'class_files':classes,'compiler':{'java_launcher_sha256':hashlib.sha256(Path(java_bin).read_bytes()).hexdigest(),'jdk_modules_sha256':hashlib.sha256(Path('/usr/lib/jvm/java-17-openjdk-amd64/lib/modules').read_bytes()).hexdigest()},'android_compile':False,'android_execution':False,'server_or_world_authority':False}
(out/'focused.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps({'host_java':results[-1]['stdout'].strip(),'source_controls':len(checks),'report':str(out/'focused.json')}))
