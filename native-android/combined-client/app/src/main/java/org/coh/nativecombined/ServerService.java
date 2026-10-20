package org.coh.nativecombined;

import android.app.*;
import android.content.*;
import android.net.Uri;
import android.os.*;
import android.util.AtomicFile;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import android.system.Os;
import android.system.ErrnoException;
import android.system.OsConstants;

/** Owns imports, the disposable server runtime and its fresh native endpoint lease. */
public final class ServerService extends Service {
    public final class LocalBinder extends Binder { public ServerService service(){return ServerService.this;} }
    private final LocalBinder binder=new LocalBinder();
    private final ExecutorService owner=Executors.newSingleThreadExecutor();
    private final Handler main=new Handler(Looper.getMainLooper());
    private final JSONArray events=new JSONArray();
    private volatile String phase="stopped",message="Import the existing launcher APK and four game asset parts.";
    private volatile boolean busy,ready,runtimeReady,stopRequested;
    private volatile ImportContract.Control control;
    private volatile java.lang.Process guest;
    private volatile String importStatus="Checking imports…",session="",generation="";
    private volatile long progressDone,progressTotal;
    private volatile int guestExit=-1;
    private final GuestDiagnostics diagnostics=new GuestDiagnostics();
    private String appVersion="unknown";
    private long appVersionCode;
    private volatile long startFreeBytes;
    private volatile ServerMemoryPolicy serverMemory=new ServerMemoryPolicy();
    private volatile JSONArray processExits=new JSONArray();
    private volatile String exitHistoryStatus="not_collected";
    private volatile ApkReportIdentity.Snapshot installedApk;
    private volatile String installedApkStatus="pending";
    private final Object resourcesLock=new Object();
    private volatile JSONArray guestResources=new JSONArray();
    private ImportStore imports;
    private RuntimeSetup setup;
    private PowerManager.WakeLock wake;
    private File stateDir;
    private long lastProgress;
    private final Runnable ticker=new Runnable(){public void run(){save();main.postDelayed(this,2000);}};
    @Override public void onCreate(){
        super.onCreate();stateDir=new File(getFilesDir(),"combined-server");stateDir.mkdirs();
        MemoryTelemetry.request(this,PhaseMemoryDiagnostics.Phase.COLD_STARTUP);
        try{android.content.pm.PackageInfo p=getPackageManager().getPackageInfo(getPackageName(),0);appVersion=p.versionName;appVersionCode=p.versionCode;}catch(Exception ignored){}
        NotificationManager nm=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);
        nm.createNotificationChannel(new NotificationChannel("server","Native COH local runtime",NotificationManager.IMPORTANCE_LOW));
        foreground();
        // Capture before returning a binder: submit/stop can save synchronously.
        final JSONObject persisted=readJson(new File(getFilesDir(),"combined-report.json"),128*1024);
        owner.execute(()->{try{archiveAttempt(persisted);collectProcessExits();captureApkIdentity();initialize();refresh();}catch(Exception e){fail(e);}save();main.post(ticker);});
    }
    private void captureApkIdentity(){
        try{installedApk=ApkReportIdentity.capture(new File(getApplicationInfo().sourceDir));installedApkStatus="ready";}
        catch(IOException|RuntimeException unavailable){installedApkStatus="unavailable";}
    }
    private void foreground(){
        PendingIntent open=PendingIntent.getActivity(this,0,new Intent(this,MainActivity.class),PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        Notification notification=new Notification.Builder(this,"server").setSmallIcon(android.R.drawable.ic_menu_compass)
            .setContentTitle("CoH Native Combined").setContentText("Local test runtime · "+phase).setContentIntent(open).setOngoing(true).build();
        startForeground(1,notification);
    }
    @Override public int onStartCommand(Intent intent,int flags,int id){foreground();return START_NOT_STICKY;}
    @Override public IBinder onBind(Intent intent){return binder;}
    private void initialize()throws Exception {if(imports==null){imports=new ImportStore(this,this::progress);setup=new RuntimeSetup(this,imports);}}
    private void refresh()throws Exception {importStatus=imports.status();runtimeReady=setup.ready();}
    public JSONObject snapshot(){
        JSONObject out=new JSONObject();try{
            GuestDiagnostics.Snapshot d=diagnostics.snapshot(SystemClock.elapsedRealtime());JSONArray stages=new JSONArray();
            ApkReportIdentity.Snapshot apk=installedApk;
            String apkStatus=apk!=null?"ready":"unavailable".equals(installedApkStatus)?"unavailable":"pending";
            for(int i=0;i<d.stages.length;i++)stages.put(new JSONObject().put("stage",d.stages[i]).put("elapsed_ms",d.stageTimes[i]));
            out.put("schema","coh-native-combined-app-v1").put("package",getPackageName()).put("busy",busy).put("runtime_ready",runtimeReady)
                .put("version_name",appVersion).put("version_code",appVersionCode).put("android_sdk",Build.VERSION.SDK_INT).put("abis",new JSONArray(Arrays.asList(Build.SUPPORTED_ABIS)))
                .put("installed_apk_status",apkStatus).put("installed_apk",apk==null?JSONObject.NULL:new JSONObject().put("bytes",apk.bytes).put("sha256",apk.sha256))
                .put("guest_resources",guestResources)
                .put("storage_available_bytes",getFilesDir().getUsableSpace()).put("server_start_available_bytes",startFreeBytes)
                .put("server_memory",new JSONObject(serverMemory.snapshot())).put("android_process_exits",processExits).put("android_exit_history_status",exitHistoryStatus)
                .put("android_exit_history_scope","ApplicationExitInfo for this package; explicit LOW_MEMORY reason is OS evidence; SIGKILL alone has no established cause")
                .put("memory_diagnostics",MemoryTelemetry.snapshot())
                .put("diagnostic_states",new JSONObject(PhaseMemoryDiagnostics.states((Boolean)null,(String)serverMemory.snapshot().get("reason"))))
                .put("imports",importStatus).put("message",message).put("progress_done",progressDone).put("progress_total",progressTotal)
                .put("server",new JSONObject().put("phase",phase).put("ready",ready).put("session_id",session).put("guest_exit_code",guestExit).put("owned_process_alive",guest!=null&&guest.isAlive())
                    .put("failure_code",d.failure).put("last_stage",d.stage).put("elapsed_ms",d.elapsedMs).put("stage_elapsed_ms",d.stageElapsedMs).put("stages",stages))
                .put("local_development_auth",true).put("real_authserver_login_verified",false).put("native_live_world_verified",false)
                .put("old_application_modified",false).put("updated_elapsed_ms",SystemClock.elapsedRealtime());
            synchronized(events){out.put("events",new JSONArray(events.toString()));}
        }catch(JSONException ignored){/* Fixed primitive fields only. */}return out;
    }
    private void event(String name){synchronized(events){try{if(events.length()<128)events.put(new JSONObject().put("name",name).put("elapsed_ms",SystemClock.elapsedRealtime()));}catch(JSONException ignored){}}}
    private void progress(String text,long done,long total){
        message=text;progressDone=done;progressTotal=total;
        long now=SystemClock.elapsedRealtime();if(now-lastProgress>1000){lastProgress=now;save();}
    }
    private interface Operation {void run(ImportContract.Control cancellation)throws Exception;}
    private synchronized void submit(String name,Operation operation){
        if(busy||(guest!=null&&guest.isAlive())){message="Stop the current operation before starting another.";save();return;}
        final JSONObject prior=name.equals("starting")?snapshot():null;
        busy=true;ready=false;phase=name;stopRequested=false;progressDone=progressTotal=0;control=new ImportContract.Control();final ImportContract.Control operationControl=control;revoke();event(name);foreground();save();
        owner.execute(()->{
            try{initialize();if(prior!=null)archiveAttempt(prior);operation.run(operationControl);if(!name.equals("starting")){phase="stopped";message="Operation complete. Start the server when ready.";}}
            catch(Exception e){if(name.equals("starting"))diagnostics.failure(session,"SERVER_ADMISSION_FAILED");fail(e);}finally{if(name.equals("starting")){diagnostics.finish(SystemClock.elapsedRealtime());if(guest==null||!guest.isAlive())MemoryTelemetry.request(this,PhaseMemoryDiagnostics.Phase.SERVER_STOPPED);}ready=false;revoke();try{refresh();}catch(Exception ignored){}releaseWake();synchronized(this){if(control==operationControl)control=null;busy=false;}save();}
        });
    }
    public void importDocuments(String kind,List<Uri> documents){
        submit("importing",c->{
            for(Uri uri:documents){c.check();InputStream in=getContentResolver().openInputStream(uri);
                if(in==null)throw new IOException("Selected document cannot be opened");
                if(kind.equals("launcher"))imports.importDonorApk(in,c);
                else if(kind.equals("part"))imports.importAssetPart(in,c);
                else if(kind.equals("profile"))imports.importProfileDump(in,c);
                else imports.importRuntimeArchive(kind,in,c);
            }refresh();event("import_complete");
        });
    }
    public void setupRuntime(){submit("setting_up",c->{setup.setup(c,this::progress);runtimeReady=true;event("runtime_ready");});}
    public void startServer(){submit("starting",this::runServer);}
    public void stopOperation(){
        stopRequested=true;ready=false;revoke();ImportContract.Control c=control;if(c!=null)c.cancel();
        try{write(new File(stateDir,"stop-request"),"stop\n".getBytes(StandardCharsets.US_ASCII));}catch(IOException ignored){}
        message="Stopping owned work and preserving the test profile…";event("stop_requested");save();
    }
    private void runServer(ImportContract.Control cancellation)throws Exception {
        session=UUID.randomUUID().toString().replace("-","");generation="";guestExit=-1;
        synchronized(resourcesLock){guestResources=new JSONArray();}
        serverMemory=new ServerMemoryPolicy();
        diagnostics.start(session,SystemClock.elapsedRealtime());
        startFreeBytes=getFilesDir().getUsableSpace();
        message="Checking local server inputs…";
        if(!Arrays.asList(Build.SUPPORTED_ABIS).contains("arm64-v8a"))throw new IOException("The server runtime requires an ARM64 Android device");
        if(!setup.ready())throw new IOException("Import the files and complete Set up runtime before starting the server");
        File data=imports.gameDataDirectory();if(data==null)throw new IOException("Import all four verified game asset parts");
        generation=data.getParentFile().getName();if(!generation.matches("generation-[0-9a-f]{32}"))throw new IOException("Invalid imported game generation");
        File stop=new File(stateDir,"stop-request"),lease=new File(stateDir,"server-ready.json");
        Files.deleteIfExists(stop.toPath());Files.deleteIfExists(lease.toPath());
        File previous=new File(stateDir,"owner-active.json");
        if(previous.exists())throw new IOException("Previous server ownership is incomplete. Preserve the report and force-stop this test app before recovery");
        diagnostics.stage(session,"server_memory_admission",SystemClock.elapsedRealtime());
        admitServerMemory();
        diagnostics.stage(session,"prepare_immutable_server_inputs",SystemClock.elapsedRealtime());
        File runtime=setup.prepareForServer(cancellation,this::progress);
        File tmp=new File(getFilesDir(),"combined-tmp"),shortTmp=new File(getFilesDir(),"p"),helper=new File(getFilesDir(),"combined-guest");
        tmp.mkdirs();shortTmp.mkdirs();helper.mkdirs();
        if(shortTmp.getCanonicalPath().getBytes(StandardCharsets.UTF_8).length+27>107)throw new IOException("Storage path exceeds the process runtime socket limit");
        // PRoot rewrites guest Unix paths to their real Android backing path.
        // Session display components are 25 ASCII bytes, plus the separator.
        if(new File(stateDir,"diagnostic/runtime").getCanonicalPath().getBytes(StandardCharsets.UTF_8).length+26>107)
            throw new IOException("Storage path exceeds the private display socket limit");
        try(InputStream in=getAssets().open("combined/server_runtime.py")){write(new File(helper,"server_runtime.py"),bounded(in,512*1024));}
        File hosts=new File(helper,"hosts");String hostname=Os.uname().nodename;if(!hostname.matches("[A-Za-z0-9_.-]{1,253}"))throw new IOException("Invalid device hostname");write(hosts,("127.0.0.1 localhost "+hostname+"\n::1 localhost\n").getBytes(StandardCharsets.US_ASCII));
        String lib=getApplicationInfo().nativeLibraryDir;
        File proot=new File(lib,"libproot.so"),loader=new File(lib,"libproot-loader.so");
        if(!proot.canExecute()||!loader.canExecute())throw new IOException("ARM64 process runtime is missing");
        List<String> command=new ArrayList<>(Arrays.asList(proot.getPath(),"--link2symlink","--kill-on-exit","--sysvipc","-i","1000:1000","-r",new File(runtime,"rootfs").getPath(),
            "-b","/dev","-b","/proc","-b","/sys","-b",stateDir.getPath()+":/state","-b",tmp.getPath()+":/tmp",
            "-b",new File(runtime,"assets").getPath()+":/opt/coh","-b",new File(runtime,"pg/opt/coh/pgsql").getPath()+":/opt/coh/pgsql",
            "-b",new File(runtime,"wine").getPath()+":/opt/wine","-b",new File(runtime,"passwd").getPath()+":/etc/passwd",
            "-b",new File(runtime,"group").getPath()+":/etc/group","-b",hosts.getPath()+":/etc/hosts",
            "-b",helper.getPath()+":/opt/combined","-b",data.getParentFile().getPath()+":/game",
            "-b",imports.runtimePayloadDirectory().getPath()+":/imports",
            "-w","/state","/usr/bin/env","-i","HOME=/state","USER=coh","LOGNAME=coh","PATH=/opt/coh/pgsql/bin:/usr/local/bin:/usr/bin:/bin","LANG=C.UTF-8","TZ=UTC","TMPDIR=/tmp","PYTHONUNBUFFERED=1",
            "/usr/bin/python3","/opt/combined/server_runtime.py","--state","/state","--assets","/opt/coh","--game-data","/game/data","--session-id",session,"--import-generation",generation,"--timeout-seconds","21600"));
        File backup=imports.profileDump();
        if(backup!=null){command.addAll(Arrays.asList("--logical-backup","/imports-profile/"+backup.getName()));
            int start=command.indexOf("-w");command.add(start,"-b");command.add(start+1,backup.getParent()+":/imports-profile");}
        else command.add("--provision-test-character");
        ProcessBuilder builder=new ProcessBuilder(command).redirectErrorStream(true);
        builder.environment().put("PROOT_LOADER",loader.getPath());builder.environment().put("PROOT_TMP_DIR",shortTmp.getPath());builder.environment().put("PROOT_NO_SECCOMP","1");
        cancellation.check();admitServerMemory();write(previous,new JSONObject().put("session_id",session).put("clean",false).toString().getBytes(StandardCharsets.UTF_8));
        PowerManager manager=(PowerManager)getSystemService(POWER_SERVICE);wake=manager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"coh:native-server");wake.acquire(6*60*60*1000L);
        long cleanupDeadline=0;
        try {
            guest=builder.start();MemoryTelemetry.requestProcessSet(this,true);event("server_process_started");
            final java.lang.Process process=guest;
            Thread output=new Thread(()->readOutput(process),"coh-server-output");output.start();
            while(!process.waitFor(1,TimeUnit.SECONDS)){
                MemoryTelemetry.requestProcessSet(this,true);
                if(!stopRequested&&!cancellation.isCancelled()&&serverMemory.observe(memorySample(),SystemClock.elapsedRealtime())){
                    diagnostics.failure(session,"SERVER_MEMORY_SAFETY_STOP");ready=false;revoke();stopRequested=true;
                    message="Server memory check requested cleanup; stopping the server and preserving the test profile.";event("server_memory_safety_stop");
                }
                if(stopRequested||cancellation.isCancelled()){
                    ready=false;revoke();if(cleanupDeadline==0){cleanupDeadline=SystemClock.elapsedRealtime()+120000;write(stop,"stop\n".getBytes(StandardCharsets.US_ASCII));}
                    if(SystemClock.elapsedRealtime()>=cleanupDeadline){message="Owned cleanup exceeded its deadline; export the report.";phase="cleanup_failed";awaitCleanup(process,cleanupDeadline);break;}
                }else try{updateLease(lease,process);}catch(Exception e){diagnostics.failure(session,"ENDPOINT_LEASE_FAILED");ready=false;revoke();stopRequested=true;message="Endpoint lease failed; stopping the owned server.";}
                save();
            }
            if(process.isAlive())throw new IOException("Owned runtime did not exit; force-stop this test app and export the report");
            guestExit=process.exitValue();MemoryTelemetry.requestProcessSet(this,false);output.join(3000);ready=false;revoke();
            JSONObject result=readJson(new File(stateDir,"latest-report.json"),256*1024);
            boolean current=result!=null&&GuestDiagnostics.currentReport(session,result.optString("session_id"),result.opt("format"),result.optString("app_id"));
            if(current){
                diagnostics.stage(session,result.optString("last_stage"),SystemClock.elapsedRealtime());
                diagnostics.failure(session,result.optString("primary_failure_code",result.optString("failure_code")));
            }
            diagnostics.finish(SystemClock.elapsedRealtime());
            boolean cleaned=GuestDiagnostics.cleanupProved(!process.isAlive(),current,result==null?null:result.opt("cleanup_complete"));
            String failure=diagnostics.snapshot(SystemClock.elapsedRealtime()).failure;
            if(cleaned){Files.deleteIfExists(previous.toPath());phase=guestExit==0&&failure.isEmpty()?"stopped":"failed";message=phase.equals("stopped")?"Server stopped; test profile preserved.":"Server failed"+(failure.isEmpty()?"":": "+failure)+". Test profile preserved. Export report.";}
            else {phase="cleanup_failed";message="Server cleanup could not be proved"+(failure.isEmpty()?"": " after "+failure)+". Preserve and export the report.";}
            event("server_process_exited");
        }catch(Exception failure){ready=false;revoke();if(guest!=null&&guest.isAlive()){try{write(stop,"stop\n".getBytes(StandardCharsets.US_ASCII));if(cleanupDeadline==0)cleanupDeadline=SystemClock.elapsedRealtime()+120000;awaitCleanup(guest,cleanupDeadline);}catch(Exception ignored){/* Marker blocks reuse until explicit recovery. */}}throw failure;}finally{diagnostics.finish(SystemClock.elapsedRealtime());ready=false;revoke();if(guest!=null&&!guest.isAlive())guest=null;}
    }
    private ServerMemoryPolicy.Sample memorySample(){
        return MemoryTelemetry.systemSample(this);
    }
    private void admitServerMemory()throws IOException{
        if(!serverMemory.admit(memorySample(),SystemClock.elapsedRealtime())){
            diagnostics.failure(session,"SERVER_MEMORY_ADMISSION_FAILED");
            throw new IOException("Server startup stopped because available memory is low or unavailable. Close other apps and retry; imports and profile are preserved.");
        }
    }
    private void collectProcessExits(){
        if(Build.VERSION.SDK_INT<30){exitHistoryStatus="unsupported_before_android_11";return;}
        JSONArray records=new JSONArray();
        try{
            ActivityManager manager=(ActivityManager)getSystemService(ACTIVITY_SERVICE);
            for(ApplicationExitInfo item:manager.getHistoricalProcessExitReasons(getPackageName(),0,8)){
                // Numeric OS evidence only: no process command, description or trace.
                records.put(new JSONObject().put("pid",item.getPid()).put("reason",item.getReason()).put("status",item.getStatus()).put("timestamp_utc_ms",item.getTimestamp())
                    .put("importance",item.getImportance()).put("pss_kib",item.getPss()).put("rss_kib",item.getRss()).put("low_memory",item.getReason()==ApplicationExitInfo.REASON_LOW_MEMORY));
                if(records.length()==8)break;
            }
            processExits=records;exitHistoryStatus="collected";
        }catch(RuntimeException|JSONException unavailable){processExits=records;exitHistoryStatus="unavailable";}
    }
    private void archiveAttempt(JSONObject app)throws IOException{
        if(app==null||!"coh-native-combined-app-v1".equals(app.optString("schema"))||!getPackageName().equals(app.optString("package")))return;
        JSONObject server=app==null?null:app.optJSONObject("server");
        if(server==null||!server.optString("session_id").matches("[0-9a-f]{32}"))return;
        String id=server.optString("session_id");
        File file=new File(stateDir,"previous-attempts.json");JSONObject saved=readJson(file,2*1024*1024);
        JSONArray old=saved==null?null:saved.optJSONArray("attempts"),next=new JSONArray();
        try{
            if(old!=null)for(int i=0;i<old.length();i++){JSONObject item=old.optJSONObject(i);if(item!=null&&id.equals(item.optString("session_id")))return;}
            if(old!=null)for(int i=Math.max(0,old.length()-3);i<old.length();i++)if(old.optJSONObject(i)!=null)next.put(old.getJSONObject(i));
            JSONObject entry=new JSONObject().put("session_id",id).put("app",app);
            JSONObject guestReport=readJson(new File(stateDir,"latest-report.json"),256*1024);
            if(guestReport!=null&&GuestDiagnostics.sameSession(id,guestReport.optString("session_id"))){
                JSONObject readiness=guestReport.optJSONObject("server_readiness");if(readiness!=null)readiness.remove("account");
                entry.put("guest",guestReport);
            }
            next.put(entry);
            byte[] bytes=new JSONObject().put("format",1).put("maximum_attempts",4).put("attempts",next).toString(2).getBytes(StandardCharsets.UTF_8);
            if(bytes.length>2*1024*1024)throw new IOException("Previous attempt evidence exceeds its bound");
            write(file,bytes);
        }catch(JSONException invalid){throw new IOException("Previous attempt evidence could not be preserved",invalid);}
    }
    private static void awaitCleanup(java.lang.Process process,long deadline)throws InterruptedException {
        if(waitUntil(process,deadline))return;
        process.destroy();if(waitUntil(process,deadline+15000))return;
        process.destroyForcibly();waitUntil(process,deadline+20000);
    }
    private static boolean waitUntil(java.lang.Process process,long deadline)throws InterruptedException {
        long remaining=Math.max(0,deadline-SystemClock.elapsedRealtime());
        return !process.isAlive()||(remaining>0&&process.waitFor(remaining,TimeUnit.MILLISECONDS));
    }
    private void updateLease(File lease,java.lang.Process process)throws Exception {
        JSONObject r=readJson(lease,16384);long now=System.currentTimeMillis();
        if(r==null||r.optInt("format")!=1||!getPackageName().equals(r.optString("app_id"))||!"server_ready".equals(r.optString("type"))||!r.optBoolean("local_fake_auth")
            ||!LeaseRules.accept(process.isAlive(),session,r.optString("session_id"),generation,r.optString("import_generation"),r.optString("db_address"),r.optInt("db_port"),now,r.optLong("observed_utc_ms"),lease.lastModified(),SystemClock.elapsedRealtime())){ready=false;revoke();return;}
        JSONObject policy=new JSONObject().put("schema","coh-native-local-policy-v1").put("state","ready").put("db_address","127.0.0.1").put("db_port",7000)
            .put("account",r.getString("account")).put("net_version",5).put("encryption_required",false).put("outbound_compressed",false)
            .put("server_session_id",session).put("import_generation",generation.substring(11)).put("ready_elapsed_ms",SystemClock.elapsedRealtime());
        write(policyFile(),policy.toString().getBytes(StandardCharsets.UTF_8));
        if(!ready){event("server_ready");MemoryTelemetry.request(this,PhaseMemoryDiagnostics.Phase.SERVER_READY);}ready=true;phase="ready";message="Server ready. Launch the native client manually.";
    }
    private void readOutput(java.lang.Process process){
        try(Reader reader=new InputStreamReader(process.getInputStream(),StandardCharsets.UTF_8)){
            char[] block=new char[1024];StringBuilder line=new StringBuilder();boolean overlong=false;int n;
            while((n=reader.read(block))!=-1)for(int i=0;i<n;i++){
                char ch=block[i];if(ch=='\n'){if(!overlong)stageLine(line.toString());line.setLength(0);overlong=false;}
                else if(!overlong){if(line.length()==8192){line.setLength(0);overlong=true;}else line.append(ch);}
            }
        }catch(IOException ignored){/* Guest report remains authoritative. */}
    }
    private void stageLine(String line){
        if(!line.startsWith("{"))return;
        try{JSONObject e=new JSONObject(line);String id=e.optString("session_id");
            if(!GuestDiagnostics.sameSession(session,id))return;
            if(e.optString("type").equals("guest_resources")){
                captureGuestResources(id,e);
            }else if(e.optString("type").equals("stage")){
                String stage=e.optString("stage");if(diagnostics.stage(id,stage,SystemClock.elapsedRealtime()))message="Preparing server: "+stage.replace('_',' ');
            }else if(e.optString("type").equals("server_stopped")){
                diagnostics.failure(id,e.optString("primary_failure_code",e.optString("failure_code")));
                // Output is diagnostic only. The session-bound private report
                // remains the cleanup authority after the process has exited.
            }
        }catch(JSONException ignored){}
    }
    private void captureGuestResources(String id,JSONObject source)throws JSONException{
        synchronized(resourcesLock){
            if(!GuestDiagnostics.sameSession(session,id))return;
            String stage=GuestDiagnostics.stageName(source.optString("stage"));
            String boundary=source.optString("boundary");
            if(stage.isEmpty()||!(boundary.equals("entered")||boundary.equals("leaving")))return;
            JSONObject row=new JSONObject().put("stage",stage).put("boundary",boundary)
                .put("elapsed_ms",diagnostics.snapshot(SystemClock.elapsedRealtime()).elapsedMs);
            for(String key:new String[]{"rss_kib","peak_rss_kib","children_peak_rss_kib","cgroup_current_bytes","cgroup_max_bytes","cgroup_oom_kill_count"}){
                Long value=GuestDiagnostics.numericMetric(source.opt(key));
                row.put(key,value==null?JSONObject.NULL:value);
            }
            JSONArray next=new JSONArray();JSONArray previous=guestResources;
            for(int i=Math.max(0,previous.length()-31);i<previous.length();i++)next.put(previous.getJSONObject(i));
            next.put(row);guestResources=next;
        }
        // Persist the last stage boundary before a later abrupt process exit.
        save();
    }
    public void recoverInterrupted(){submit("recovering",c->{
        if(guest!=null&&guest.isAlive())throw new IOException("The owned server is still running. Stop it first.");
        File[] entries=new File("/proc").listFiles();if(entries==null||entries.length>8192)throw new IOException("Cannot inspect process ownership");
        boolean sawSelf=false;int own=0;
        for(File entry:entries){c.check();if(!entry.getName().matches("[0-9]+"))continue;
            try{if(Os.stat(entry.getPath()).st_uid==android.os.Process.myUid()){
                if(entry.getName().equals(Integer.toString(android.os.Process.myPid())))sawSelf=true;
                else own++;
            }}catch(ErrnoException e){if(e.errno!=OsConstants.ENOENT&&e.errno!=OsConstants.EACCES)throw new IOException("Process inspection failed");}
        }
        if(!sawSelf||own!=0)throw new IOException("Owned child processes remain. Force-stop this test app, reopen it, then recover.");
        Files.deleteIfExists(new File(stateDir,"owner-active.json").toPath());Files.deleteIfExists(new File(stateDir,"server-ready.json").toPath());
        guest=null;phase="stopped";message="Interrupted ownership cleared after inspection; test database preserved.";event("interrupted_owner_recovered");
    });}
    private void fail(Exception e){ready=false;revoke();phase="failed";message=e instanceof InterruptedIOException?"Operation stopped; verified content preserved.":safe(e.getMessage());event("operation_failed");}
    private static String safe(String value){if(value==null)return "Operation failed. Export the report.";String v=value.replaceAll("[\\r\\n]"," ");return v.length()>240?v.substring(0,240):v;}
    private void releaseWake(){if(wake!=null){if(wake.isHeld())wake.release();wake=null;}}
    public File policyFile(){return new File(getFilesDir(),"native-session-policy.json");}
    private void revoke(){try{Files.deleteIfExists(policyFile().toPath());}catch(IOException ignored){/* Client also checks freshness and session identity. */}}
    private synchronized void save(){try{write(new File(getFilesDir(),"combined-report.json"),snapshot().toString(2).getBytes(StandardCharsets.UTF_8));}catch(Exception ignored){}}
    static JSONObject readJson(File file,int max){try(InputStream in=new FileInputStream(file)){return new JSONObject(new String(bounded(in,max),StandardCharsets.UTF_8));}catch(Exception e){return null;}}
    static byte[] bounded(InputStream in,int limit)throws IOException {ByteArrayOutputStream out=new ByteArrayOutputStream();byte[] buf=new byte[8192];int n;while((n=in.read(buf))!=-1){if(n==0||out.size()+n>limit)throw new IOException("Input exceeds its bound");out.write(buf,0,n);}return out.toByteArray();}
    static synchronized void write(File file,byte[] bytes)throws IOException {file.getParentFile().mkdirs();AtomicFile atomic=new AtomicFile(file);FileOutputStream out=atomic.startWrite();try{out.write(bytes);out.getFD().sync();atomic.finishWrite(out);}catch(IOException e){atomic.failWrite(out);throw e;}}
    @Override public void onTaskRemoved(Intent rootIntent){stopOperation();if(!busy)stopSelf();}
    @Override public void onTrimMemory(int level) {super.onTrimMemory(level);MemoryTelemetry.memoryPressure(this,level,false);}
    @Override public void onLowMemory() {super.onLowMemory();MemoryTelemetry.memoryPressure(this,-1,true);}
    @Override public void onDestroy(){stopOperation();main.removeCallbacks(ticker);owner.shutdown();super.onDestroy();}
}
