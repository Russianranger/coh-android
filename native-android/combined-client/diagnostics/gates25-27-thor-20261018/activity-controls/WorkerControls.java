
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
    private void connectLocalServer(NetworkMode mode) {
        if(destroying||returningToLauncher||networkConnecting||!networkForeground)return;
        final long attempt=++networkAttempt;networkRequested=true;
        networkConnecting=true;connectButton.setEnabled(false);handoffButton.setEnabled(false);
        characterButtons.removeAllViews();charactersScroll.setVisibility(android.view.View.GONE);
        networkStatus.setText(mode==NetworkMode.WORLD_HANDOFF
                ? "World handoff test: connecting to the local development server… The scene remains a local preview."
                : "Server protocol: connecting to the local development server…");
        event(mode==NetworkMode.WORLD_HANDOFF?"world_handoff_requested":"local_connect_requested");
        networkWorker.execute(() -> {
            try {
                if(!networkForeground||!networkRequested||attempt!=networkAttempt)return;
                retireNetworkOwner();networkMode=mode;charactersPublished=false;
                JSONObject policy=localPolicy();
                if(!networkForeground||!networkRequested||attempt!=networkAttempt)return;
                networkPolicy=policy;
                policyCheckedAt=SystemClock.elapsedRealtime();
                networkHandle=mode==NetworkMode.WORLD_HANDOFF
                        ? InteropNative.begin(policy.getInt("db_port"),policy.getString("account"),policy.getInt("net_version"),
                            policy.getBoolean("encryption_required"),policy.getBoolean("outbound_compressed"),policyCheckedAt)
                        : LocalNative.begin(policy.getInt("db_port"),policy.getString("account"),policy.getInt("net_version"),
                            policy.getBoolean("encryption_required"),policy.getBoolean("outbound_compressed"),policyCheckedAt);
                if(networkHandle==0)throw new IllegalStateException("Local owner rejected policy");
                publishNetwork();
            } catch(Exception problem) {
                storeNetworkReport("{\"phase\":\"POLICY_UNAVAILABLE\",\"live_world_rendered\":false,\"authserver_authenticated\":false,\"world_authority\":false}");
                main.post(() -> {if(!destroying)updateNetworkUi();});
            } finally {networkConnecting=false;main.post(() -> {if(!destroying)updateNetworkUi();});}
        });
    }

    private boolean sameNetworkPolicy(JSONObject policy) throws Exception {
        if(networkPolicy==null)return false;
        for(String key:new String[]{"server_session_id","import_generation","account","db_address"})
            if(!networkPolicy.getString(key).equals(policy.getString(key)))return false;
        for(String key:new String[]{"db_port","net_version"})
            if(networkPolicy.getInt(key)!=policy.getInt(key))return false;
        for(String key:new String[]{"encryption_required","outbound_compressed"})
            if(networkPolicy.getBoolean(key)!=policy.getBoolean(key))return false;
        return true;
    }

    private void disconnectNetwork() {
        if(networkMode==NetworkMode.WORLD_HANDOFF)InteropNative.disconnect(networkHandle);
        else LocalNative.disconnect(networkHandle);
    }

    private void suspendNetwork() {
        if(networkMode==NetworkMode.WORLD_HANDOFF)InteropNative.suspend(networkHandle);
        else LocalNative.suspend(networkHandle);
    }

    private void retireNetworkOwner() {
        final long retiring=networkHandle;final NetworkMode mode=networkMode;
        try {
            if(retiring==0)return;
            try { disconnectNetwork();publishNetwork(); }
            finally {
                if(mode==NetworkMode.WORLD_HANDOFF)InteropNative.close(retiring);
                else LocalNative.close(retiring);
            }
        } finally {networkHandle=0;networkPolicy=null;}
    }

    private void networkTick() {
        if(destroying||!networkForeground||!networkRequested||networkHandle==0)return;
        try {
            long now=SystemClock.elapsedRealtime();
            if(now-policyCheckedAt>=1000) {
                JSONObject policy=localPolicy();
                if(!sameNetworkPolicy(policy))throw new IllegalStateException("Server policy replaced");
                policyCheckedAt=now;
            }
            String phase=new JSONObject(networkReport).optString("phase","IDLE");
            if("SUSPENDED".equals(phase)||"CLOSED".equals(phase)||"CANCELLED".equals(phase)
                    ||"FAILED".equals(phase)||"TIMED_OUT".equals(phase)||"UNSUPPORTED".equals(phase)
                    ||"INITIAL_OBSERVED".equals(phase)||"POLICY_UNAVAILABLE".equals(phase))return;
            if(networkMode==NetworkMode.WORLD_HANDOFF)InteropNative.service(networkHandle,now);
            else LocalNative.service(networkHandle,now);
            publishNetwork();
            if(!charactersPublished&&"CHARACTERS_READY".equals(new JSONObject(networkReport).optString("phase"))) {
                byte[] list=networkMode==NetworkMode.WORLD_HANDOFF?InteropNative.characters(networkHandle):LocalNative.characters(networkHandle);
                if(list!=null) {
                    JSONArray characters=new JSONArray(new String(list,StandardCharsets.UTF_8));
                    charactersPublished=true;
                    final long attempt=networkAttempt;
                    main.post(() -> {if(!destroying&&networkForeground&&networkRequested&&attempt==networkAttempt)showCharacters(characters,attempt);});
                }
            }
        } catch(Exception problem) {
            suspendNetwork();publishNetwork();
            main.post(() -> {if(!destroying)networkStatus.setText("Client suspended • Start/verify the local server, then connect again.");});
        }
    }

    private void storeNetworkReport(String next) {
        if(networkMode==NetworkMode.WORLD_HANDOFF)interopReport=next;else localNetworkReport=next;
        networkReport=next;
    }

    private void publishNetwork() {
        if(networkHandle==0)return;
        String next=networkMode==NetworkMode.WORLD_HANDOFF?InteropNative.report(networkHandle):LocalNative.report(networkHandle);
        if(!next.equals(networkReport)) {
            storeNetworkReport(next);
            main.post(() -> {if(!destroying)updateNetworkUi();});
        }
    }
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
final class LocalNative {
 static long begin(int port,String account,int version,boolean encrypted,boolean compressed,long now){return NativeDouble.begin("L");}
 static int service(long h,long now){return NativeDouble.service("L",h);}
 static byte[] characters(long h){return NativeDouble.chars("L");}
 static String report(long h){return NativeDouble.report("L",h);}
 static void disconnect(long h){NativeDouble.stop("L",h,"disconnect");}
 static void suspend(long h){NativeDouble.stop("L",h,"suspend");}
 static void close(long h){NativeDouble.stop("L",h,"close");}
}
final class InteropNative {
 static long begin(int port,String account,int version,boolean encrypted,boolean compressed,long now){return NativeDouble.begin("I");}
 static int service(long h,long now){return NativeDouble.service("I",h);}
 static byte[] characters(long h){return NativeDouble.chars("I");}
 static String report(long h){return NativeDouble.report("I",h);}
 static void disconnect(long h){NativeDouble.stop("I",h,"disconnect");}
 static void suspend(long h){NativeDouble.stop("I",h,"suspend");}
 static void close(long h){NativeDouble.stop("I",h,"close");}
}
