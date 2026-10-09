package io.github.russianranger.cohclientinteractive;

import android.app.*;
import android.content.*;
import android.os.*;
import java.io.File;
import java.io.IOException;
import java.io.InterruptedIOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;
import org.json.JSONArray;
import org.json.JSONObject;

/** Foreground ownership for runtime setup, verified asset import and bounded client startup. */
public final class ClientService extends Service {
    public static final String SETUP="coh.client.SETUP", RUN="coh.client.RUN", CREATE="coh.client.CREATE", IMPORT="coh.client.IMPORT", STOP="coh.client.STOP", FINISH="coh.client.FINISH", STORAGE_SCAN="coh.client.STORAGE_SCAN", STORAGE_CLEAN="coh.client.STORAGE_CLEAN";
    private static final String CHANNEL="client", PREFS="client_ui";
    private static final int NOTICE=61;
    public interface Listener { void onState(State state); void onFrame(int[] pixels,int width,int height,long sequence); }
    public static final class State {
        public final boolean busy, blocked, inputReady, finishing, characterSaved, canReturnGround, canSaveLogout;
        public final long inputSent, inputFailed, readyDeadlineUptimeMillis, saveDeadlineUptimeMillis, movementDeadlineUptimeMillis;
        public final String stage, detail, session, log, sessionPhase;
        public final File report;
        public final int certified;
        public final boolean storageBusy, reportExporting;
        public final StorageAudit.Plan storagePlan;
        public final String storageStatus;
        public final File storageReport;
        public final ClientRuntime.ProfileState profileState;
        public final String profileNote;
        State(boolean busy,boolean blocked,String stage,String detail,String session,String log,File report,int certified,boolean inputReady,boolean finishing,boolean characterSaved,boolean canReturnGround,boolean canSaveLogout,long inputSent,long inputFailed,long deadline,String phase,long saveDeadline,long movementDeadline,boolean storageBusy,boolean reportExporting,StorageAudit.Plan storagePlan,String storageStatus,File storageReport,ClientRuntime.ProfileState profileState,String profileNote) {
            this.busy=busy;this.blocked=blocked;this.stage=stage;this.detail=detail;this.session=session;this.log=log;this.report=report;this.certified=certified;this.inputReady=inputReady;this.finishing=finishing;
            this.characterSaved=characterSaved;this.canReturnGround=canReturnGround;this.canSaveLogout=canSaveLogout;this.inputSent=inputSent;this.inputFailed=inputFailed;this.readyDeadlineUptimeMillis=deadline;this.sessionPhase=phase;this.saveDeadlineUptimeMillis=saveDeadline;this.movementDeadlineUptimeMillis=movementDeadline;
            this.storageBusy=storageBusy;this.reportExporting=reportExporting;this.storagePlan=storagePlan;this.storageStatus=storageStatus;this.storageReport=storageReport;
            this.profileState=profileState;this.profileNote=profileNote;
        }
    }
    public final class LocalBinder extends Binder { public ClientService service(){return ClientService.this;} }
    private final LocalBinder binder=new LocalBinder();
    private final Handler main=new Handler(Looper.getMainLooper());
    private final Runnable sessionDeadlineTick=new Runnable(){@Override public void run(){
        if(destroyed)return;
        refreshFinishedSetup();
        ClientRuntime active=runtime;if(busy&&active!=null)active.enforceSessionDeadlines();
        main.postDelayed(this,1000);
    }};
    private final ExecutorService worker=Executors.newSingleThreadExecutor();
    private final List<Listener> listeners=new ArrayList<>();
    private final AtomicBoolean framePending=new AtomicBoolean();
    private final StringBuilder logs=new StringBuilder();
    private volatile ClientRuntime runtime;
    private volatile boolean busy, stopping, destroyed;
    private boolean storageBusy, reportExporting;
    private Object exportOwner;
    private StorageAudit.Plan storagePlan;
    private String storageStatus="Scan storage after the current test has finished.";
    private File storageReport;
    private final AtomicBoolean storageStopRequested=new AtomicBoolean();
    private volatile byte[] storageRecoveryReserve;
    private volatile byte[] setupRecoveryReserve;
    private volatile boolean setupWorkerOwnsWake;
    private boolean waitingForSetupFinalization;
    private volatile File setupFailureReport;
    private long setupStartedUtc, lastSetupCheckpointUptime;
    private String lastSetupPhase="";
    private String setupAppVersion="unknown",setupAppId="";
    private static final String SETUP_PREFS="runtime_setup_ui";
    private static final int MAX_SETUP_EVIDENCE=16384;
    private ClientRuntime.ProfileState profileState=ClientRuntime.ProfileState.PRESERVE;
    private String profileNote="Checking the saved profile…";
    private boolean blocked, uiVisible, inputReady, finishing, characterSaved, canReturnGround, canSaveLogout;
    private long inputSent, inputFailed, readyDeadlineUptimeMillis, saveDeadlineUptimeMillis, movementDeadlineUptimeMillis;
    private String sessionPhase="menu";
    private String stage="Ready", detail="Set up the runtime, import the reviewed assets, then launch CoH.", session="";
    private File report;
    private int certified;
    private static final class Frame {
        final int[] pixels; final int width, height; final long sequence;
        Frame(int[] pixels,int width,int height,long sequence){this.pixels=pixels;this.width=width;this.height=height;this.sequence=sequence;}
    }
    private volatile Frame frame;
    private final Map<String,Integer> certificationErrors=new LinkedHashMap<>();
    private PowerManager.WakeLock wake;
    private final BroadcastReceiver screenReceiver=new BroadcastReceiver(){
        @Override public void onReceive(Context context,Intent intent){ lifecycle("screen_event="+intent.getAction()); if(Intent.ACTION_SCREEN_OFF.equals(intent.getAction()))discardPendingInputs(); }
    };
    @Override public void onCreate(){
        super.onCreate();main.post(sessionDeadlineTick);
        NotificationManager manager=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);
        manager.createNotificationChannel(new NotificationChannel(CHANNEL,"CoH saved character",NotificationManager.IMPORTANCE_LOW));
        blocked=ClientRuntime.cleanupBlocked(this);
        SharedPreferences p=getSharedPreferences(PREFS,MODE_PRIVATE);
        if(p.getBoolean("was_busy",false)){stage="Previous test interrupted";detail="The previous operation did not complete. Review its report before starting another test.";}
        else {stage=p.getString("stage",stage);detail=p.getString("detail",detail);
            certified=p.getInt("certified",0);inputSent=p.getLong("input_sent",0);inputFailed=p.getLong("input_failed",0);}
        String saved=p.getString("report",null);
        if(saved!=null){try{File f=new File(saved).getCanonicalFile();if(f.isFile()&&f.getPath().startsWith(getFilesDir().getCanonicalPath()+File.separator))report=f;}catch(Exception ignored){}}
        recoverSetupOperation();
        SharedPreferences storage=getSharedPreferences("storage_ui",MODE_PRIVATE);
        String storagePath=storage.getString("report",null);
        if(storagePath!=null)try{File f=new File(storagePath);File parent=new File(getCacheDir().getCanonicalFile(),"storage-tools");if(Files.isRegularFile(f.toPath(),LinkOption.NOFOLLOW_LINKS)&&f.getCanonicalFile().getParentFile().equals(parent))storageReport=f;}catch(Exception ignored){}
        storageStatus=storage.getString("status",storageStatus);
        recoverStorageOperation(storage);
        refreshProfileState();
        if(blocked){stage="Cleanup needs attention";detail="Force-stop COH Character Reopen in Android settings, then reopen it before starting more work.";}
        IntentFilter f=new IntentFilter();f.addAction(Intent.ACTION_SCREEN_OFF);f.addAction(Intent.ACTION_SCREEN_ON);
        if(Build.VERSION.SDK_INT>=33)registerReceiver(screenReceiver,f,Context.RECEIVER_NOT_EXPORTED);else registerReceiver(screenReceiver,f);
    }
    @Override public IBinder onBind(Intent intent){return binder;}
    public void addListener(Listener listener){listeners.add(listener);listener.onState(snapshot());deliverFrame(listener);}
    public void removeListener(Listener listener){listeners.remove(listener);}
    public void setUiVisible(boolean visible){uiVisible=visible;if(!visible)discardPendingInputs();lifecycle("activity_visible="+visible);}
    private void discardPendingInputs(){ClientRuntime active=runtime;if(active!=null)active.discardPendingInputs(session);}
    public boolean sendKey(String selectedSession,int keysym,boolean down){
        ClientRuntime active=runtime;return busy&&uiVisible&&inputReady&&active!=null&&session.equals(selectedSession)
                &&active.sendKey(selectedSession,keysym,down);
    }
    public boolean sendPointer(String selectedSession,int x,int y,int mask){
        ClientRuntime active=runtime;return busy&&uiVisible&&inputReady&&active!=null&&session.equals(selectedSession)
                &&active.sendPointer(selectedSession,x,y,mask);
    }
    public boolean requestEnter(){
        ClientRuntime active=runtime;
        return busy&&uiVisible&&inputReady&&!stopping&&!finishing&&!blocked&&active!=null
                &&active.requestEnter(session);
    }
    public boolean isPerformanceCommandPending(){
        ClientRuntime active=runtime;return active!=null&&active.isPerformanceCommandPending();
    }
    public boolean canSendPerformanceCommand(){
        ClientRuntime active=runtime;
        return busy&&uiVisible&&inputReady&&!stopping&&!finishing&&!blocked&&active!=null
                &&active.canSendPerformanceCommand();
    }
    public boolean requestPerformanceCommand(ClientInput.PerformanceCommand command){
        ClientRuntime active=runtime;
        return command!=null&&canSendPerformanceCommand()&&active!=null&&active.requestPerformanceCommand(command);
    }
    public void releaseAllInputs(String selectedSession){ClientRuntime active=runtime;if(active!=null)active.discardPendingInputs(selectedSession);}
    /** Our own text dialog keeps the queued target-field tap before releasing held input. */
    public void releaseInput(String selectedSession){ClientRuntime active=runtime;if(active!=null)active.releaseAllInputs(selectedSession);}
    public boolean requestReturnToSafeGround(){
        ClientRuntime active=runtime;
        return busy&&uiVisible&&inputReady&&canReturnGround&&active!=null&&active.requestReturnToSafeGround();
    }
    public boolean requestSaveLogout(){
        ClientRuntime active=runtime;
        return busy&&uiVisible&&inputReady&&canSaveLogout&&active!=null&&active.requestSaveLogout();
    }
    public boolean canRequestSaveLogout(){
        ClientRuntime active=runtime;
        return busy&&uiVisible&&inputReady&&canSaveLogout&&active!=null&&active.canRequestSaveLogout();
    }
    public boolean canCaptureContact(){
        ClientRuntime active=runtime;
        return busy&&uiVisible&&inputReady&&active!=null&&active.canCaptureContact();
    }
    public boolean requestContactCapture(){
        ClientRuntime active=runtime;
        return busy&&uiVisible&&inputReady&&active!=null&&active.requestContactCapture();
    }
    public boolean canCaptureTask(boolean completed){
        ClientRuntime active=runtime;
        return busy&&uiVisible&&inputReady&&active!=null&&active.canCaptureTask(completed);
    }
    public boolean canOpenTaskContact(){
        ClientRuntime active=runtime;
        return busy&&uiVisible&&inputReady&&active!=null&&active.canOpenTaskContact();
    }
    public boolean requestOpenTaskContact(){
        ClientRuntime active=runtime;
        return busy&&uiVisible&&inputReady&&active!=null&&active.requestOpenTaskContact();
    }
    public boolean requestTaskCapture(boolean completed){
        ClientRuntime active=runtime;
        return busy&&uiVisible&&inputReady&&active!=null&&active.requestTaskCapture(completed);
    }
    public boolean canCompleteAcceptedTask(){
        ClientRuntime active=runtime;
        return busy&&uiVisible&&inputReady&&active!=null&&active.canCompleteAcceptedTask();
    }
    public boolean requestCompleteAcceptedTask(){
        ClientRuntime active=runtime;
        return busy&&uiVisible&&inputReady&&active!=null&&active.requestCompleteAcceptedTask();
    }
    public boolean finish(String selectedSession){return session.equals(selectedSession)&&requestFinish();}
    public boolean requestFinish(){
        ClientRuntime active=runtime;
        if(!busy||stopping||finishing||active==null||!active.requestFinish())return false;
        inputReady=false;finishing=true;stage="Finishing session";
        detail="Releasing input and closing the client after the minimum observation. Cleanup and evidence export follow.";
        publish();notifyStatus();return true;
    }
    private void lifecycle(String event){ClientRuntime r=runtime;if(r!=null&&busy)r.recordLifecycle(event);}
    private void refreshProfileState(){profileState=ClientRuntime.characterProfileState(this);profileNote=ClientRuntime.profileRecoveryMessage(profileState);}
    private State snapshot(){return new State(busy,blocked,stage,detail,session,logs.toString(),report,certified,inputReady,finishing,characterSaved,canReturnGround,canSaveLogout,inputSent,inputFailed,readyDeadlineUptimeMillis,sessionPhase,saveDeadlineUptimeMillis,movementDeadlineUptimeMillis,storageBusy,reportExporting,storagePlan,storageStatus,storageReport,profileState,profileNote);}
    private void publish(){if(destroyed)return;State s=snapshot();for(Listener l:new ArrayList<>(listeners))l.onState(s);}
    private void deliverFrame(Listener l){Frame value=frame;if(value!=null)l.onFrame(value.pixels,value.width,value.height,value.sequence);}
    private void queueFrame(int[] pixels,int width,int height,long sequence){
        frame=new Frame(pixels,width,height,sequence);
        if(framePending.compareAndSet(false,true))main.post(()->{framePending.set(false);if(!destroyed)for(Listener l:new ArrayList<>(listeners))deliverFrame(l);});
    }
    public void recordCapture(ClientSurface.Capture c){
        ClientRuntime r=runtime;if(!busy||r==null||!session.equals(c.session))return;
        Map<String,Object> record=new LinkedHashMap<>();
        record.put("session_id",c.session);record.put("pixel_copy_success",true);
        record.put("captured_elapsed_ms",c.capturedAtUptimeMillis);record.put("sequence",c.sequence);record.put("surface_generation",c.surfaceGeneration);
        record.put("source_width",c.width);record.put("source_height",c.height);record.put("surface_width",c.surfaceWidth);record.put("surface_height",c.surfaceHeight);
        record.put("sha256",c.sha256);record.put("non_uniform",c.nonUniform);
        record.put("pixel_copy_wall_ms",c.pixelCopyWallMs);record.put("encoding_wall_ms",c.encodingWallMs);
        record.put("encoding_cpu_ms",c.encodingCpuMs);record.put("presentation_freeze_ms",c.presentationFreezeMs);
        record.put("encode_queue_wall_ms",c.encodeQueueWallMs);record.put("encoding_on_ui_thread",c.encodingOnUiThread);
        record.put("pending_frames_peak",c.pendingFramesPeak);record.put("frames_coalesced_during_copy",c.framesCoalescedDuringCopy);
        r.recordCaptureTiming(record);
        r.recordSurfaceCapture(record,c.png);if(c.nonUniform)certified++;publish();
    }
    public void recordCertificationError(String error){
        ClientRuntime r=runtime;if(!busy||r==null)return;
        String key=error==null?"unknown":error.substring(0,Math.min(160,error.length()));
        if(!certificationErrors.containsKey(key)&&certificationErrors.size()>=16)return;
        int count=certificationErrors.getOrDefault(key,0)+1;certificationErrors.put(key,count);
        if(count==1||(count&(count-1))==0)r.recordLifecycle("surface_certification_error count="+count+" message="+key);
    }
    /** Reserve the same process-wide ownership while a SAF export stream is open. */
    public Object beginReportExport(File selected) throws IOException {
        if(destroyed||busy||storageBusy||reportExporting||selected==null)throw new IOException("Wait for the current operation to finish");
        File expected=report!=null&&report.getPath().equals(selected.getPath())?report:
                storageReport!=null&&storageReport.getPath().equals(selected.getPath())?storageReport:null;
        if(expected==null||!Files.isRegularFile(selected.toPath(),LinkOption.NOFOLLOW_LINKS))throw new IOException("Select the current report again");
        exportOwner=ClientRuntime.acquireReportExport(this);reportExporting=true;publish();return exportOwner;
    }
    public void endReportExport(Object owner){
        ClientRuntime.releaseStorage(owner);
        main.post(()->{if(owner==exportOwner){exportOwner=null;reportExporting=false;publish();}});
    }
    private String currentManifestSha() throws Exception {
        MessageDigest digest=MessageDigest.getInstance("SHA-256");
        try(InputStream in=getAssets().open("runtime/runtime-manifest.json")){
            byte[] bytes=new byte[8192];int n;long count=0;
            while((n=in.read(bytes))!=-1){count+=n;if(count>2L*1024*1024)throw new IOException("Runtime manifest exceeds limit");digest.update(bytes,0,n);}
        }
        StringBuilder result=new StringBuilder();for(byte b:digest.digest())result.append(String.format(Locale.ROOT,"%02x",b&255));return result.toString();
    }
    private File writeStorageReport(String json) throws IOException {
        byte[] bytes=json.getBytes(StandardCharsets.UTF_8);if(bytes.length>8*1024*1024)throw new IOException("Storage report exceeds limit");
        // Keep our own report outside the scanned files root so it cannot stale the reviewed plan.
        File base=getCacheDir().getCanonicalFile();
        File directory=new File(base,"storage-tools");
        for(File path:new File[]{directory}){
            if(Files.exists(path.toPath(),LinkOption.NOFOLLOW_LINKS)&&!Files.isDirectory(path.toPath(),LinkOption.NOFOLLOW_LINKS))throw new IOException("Storage report path is linked or invalid");
            if(!Files.exists(path.toPath(),LinkOption.NOFOLLOW_LINKS))Files.createDirectory(path.toPath());
        }
        File target=new File(directory,"storage-"+System.currentTimeMillis()+"-"+UUID.randomUUID().toString()+".json");
        Files.write(target.toPath(),bytes,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE,LinkOption.NOFOLLOW_LINKS);
        File[] previous=directory.listFiles((dir,name)->name.matches("storage-[0-9]+-[0-9a-f-]{36}\\.json"));
        if(previous!=null){Arrays.sort(previous,(a,b)->Long.compare(b.lastModified(),a.lastModified()));int kept=0;for(File path:previous){if(!Files.isRegularFile(path.toPath(),LinkOption.NOFOLLOW_LINKS))continue;if(path.equals(target)||kept++<2)continue;Files.deleteIfExists(path.toPath());}}
        return target;
    }
    private JSONObject storageProcessExits(){
        JSONObject result=new JSONObject();JSONArray records=new JSONArray();
        try{
            result.put("maximum_records",4).put("own_processes_only",true).put("trace_streams_requested",false).put("records",records);
            if(Build.VERSION.SDK_INT<30)return result.put("status","unsupported_api");
            ActivityManager manager=(ActivityManager)getSystemService(ACTIVITY_SERVICE);
            if(manager==null)return result.put("status","unavailable");
            for(ApplicationExitInfo info:manager.getHistoricalProcessExitReasons(getPackageName(),0,4)){
                String description=info.getDescription();
                if(description!=null&&description.length()>240)description=description.substring(0,240);
                records.put(new JSONObject().put("timestamp_utc_ms",info.getTimestamp()).put("pid",info.getPid())
                        .put("reason",info.getReason()).put("status",info.getStatus()).put("importance",info.getImportance())
                        .put("pss_kib",info.getPss()).put("rss_kib",info.getRss()).put("description",description));
            }
            return result.put("status","available");
        }catch(Exception ignored){try{result.put("status","unavailable");}catch(Exception ignoredAgain){}return result;}
    }
    /** One bounded durable setup checkpoint, also included in ordinary support ZIPs. */
    public static JSONObject setupMemoryEvidence(Context context) {
        try {
            String raw=context.getSharedPreferences(SETUP_PREFS,MODE_PRIVATE).getString("progress",null);
            if(raw==null)return new JSONObject().put("status","not_recorded");
            if(raw.length()>MAX_SETUP_EVIDENCE)return new JSONObject().put("status","checkpoint_exceeded_bound");
            return new JSONObject(raw);
        } catch(Exception ignored) {
            try{return new JSONObject().put("status","unavailable");}catch(Exception impossible){return new JSONObject();}
        }
    }
    private String setupAppVersion() {
        try {
            String version=getPackageManager().getPackageInfo(getPackageName(),0).versionName;
            return version==null?"unknown":version.substring(0,Math.min(80,version.length()));
        } catch(Exception ignored){return "unknown";}
    }
    private JSONObject setupSystemMemory() {
        JSONObject value=new JSONObject();
        try {
            ActivityManager manager=(ActivityManager)getSystemService(ACTIVITY_SERVICE);
            if(manager==null)return value.put("available",false);
            ActivityManager.MemoryInfo memory=new ActivityManager.MemoryInfo();manager.getMemoryInfo(memory);
            return value.put("available",true).put("available_bytes",memory.availMem)
                    .put("total_bytes",memory.totalMem).put("threshold_bytes",memory.threshold).put("low_memory",memory.lowMemory);
        } catch(Exception failure) {
            try {value.put("available",false).put("error",failure.getClass().getSimpleName());}catch(Exception ignored){}
            return value;
        }
    }
    private JSONObject setupProcessMemory() {
        JSONObject value=new JSONObject();
        try(InputStream in=Files.newInputStream(new File("/proc/self/status").toPath())) {
            byte[] bytes=new byte[32768];int used=0,n;
            while(used<bytes.length&&(n=in.read(bytes,used,bytes.length-used))!=-1) {
                if(n==0)throw new IOException("Process memory sample made no progress");
                used+=n;
            }
            if(used==bytes.length&&in.read()!=-1)throw new IOException("Process memory sample exceeds its bound");
            int fields=0;
            for(String line:new String(bytes,0,used,StandardCharsets.US_ASCII).split("\n")) {
                String[] parts=line.trim().split("\\s+");
                if(parts.length!=3||!parts[2].equals("kB"))continue;
                String key=parts[0].equals("VmRSS:")?"rss_bytes":parts[0].equals("RssAnon:")?"anonymous_rss_bytes"
                        :parts[0].equals("RssFile:")?"file_rss_bytes":parts[0].equals("RssShmem:")?"shared_rss_bytes":null;
                if(key!=null) {
                    long kib=Long.parseLong(parts[1]);
                    if(kib<0||kib>Long.MAX_VALUE/1024)throw new IOException("Invalid process memory sample");
                    value.put(key,kib*1024);fields++;
                }
            }
            return value.put("available",fields>0).put("source","bounded_proc_self_status").put("maximum_source_bytes",bytes.length);
        } catch(Exception failure) {
            try {value=new JSONObject().put("available",false).put("error",failure.getClass().getSimpleName());}catch(Exception ignored){}
            return value;
        }
    }
    private synchronized void checkpointSetup(String phase,String text,String status,boolean force) throws IOException {
        long now=SystemClock.uptimeMillis();
        String boundedPhase=phase==null?"":phase.substring(0,Math.min(80,phase.length()));
        if(!force&&boundedPhase.equals(lastSetupPhase)&&now-lastSetupCheckpointUptime<5000)return;
        try {
            Runtime vm=Runtime.getRuntime();
            JSONObject value=new JSONObject().put("format",1).put("scope","runtime_setup_service_diagnostic")
                    .put("application_id",setupAppId).put("app_version",setupAppVersion).put("android_sdk",Build.VERSION.SDK_INT)
                    .put("device",(Build.MANUFACTURER+" "+Build.MODEL).substring(0,Math.min(160,(Build.MANUFACTURER+" "+Build.MODEL).length())))
                    .put("status",status).put("phase",boundedPhase)
                    .put("detail",text==null?"":text.substring(0,Math.min(240,text.length())))
                    .put("started_utc_ms",setupStartedUtc).put("updated_utc_ms",System.currentTimeMillis())
                    .put("elapsed_ms",Math.max(0,System.currentTimeMillis()-setupStartedUtc))
                    .put("pid",android.os.Process.myPid()).put("java_heap_used_bytes",vm.totalMemory()-vm.freeMemory())
                    .put("java_heap_limit_bytes",vm.maxMemory()).put("native_heap_allocated_bytes",Debug.getNativeHeapAllocatedSize())
                    .put("system_memory",setupSystemMemory())
                    .put("process_memory",setupProcessMemory())
                    .put("game_execution_requested",false).put("runtime_cleanup_requested",false);
            ClientRuntime activeRuntime=runtime;
            JSONObject progress=activeRuntime==null?null:activeRuntime.getSetupProgressReceipt();
            if(progress!=null)value.put("runtime_setup_progress",progress);
            String raw=value.toString();
            if(raw.length()>MAX_SETUP_EVIDENCE)throw new IOException("Setup checkpoint exceeded its bound");
            if(!getSharedPreferences(SETUP_PREFS,MODE_PRIVATE).edit().putBoolean("was_busy","running".equals(status))
                    .putString("progress",raw).commit())throw new IOException("Setup checkpoint could not be saved");
            lastSetupCheckpointUptime=now;lastSetupPhase=boundedPhase;
        } catch(IOException failure){throw failure;}
        catch(Exception failure){throw new IOException("Setup checkpoint could not be saved",failure);}
    }
    private File writeSetupRecoveryReport(JSONObject evidence) throws IOException {
        try {
            String raw=evidence.toString();
            if(raw.length()>MAX_SETUP_EVIDENCE)throw new IOException("Setup evidence exceeded its bound");
            File base=getFilesDir().getCanonicalFile(),client=new File(base,"client"),reports=new File(client,"reports");
            File directory=new File(reports,"setup-recovery-"+System.currentTimeMillis()+"-"+UUID.randomUUID().toString());
            for(File path:new File[]{client,reports,directory}) {
                if(Files.exists(path.toPath(),LinkOption.NOFOLLOW_LINKS)&&!Files.isDirectory(path.toPath(),LinkOption.NOFOLLOW_LINKS))
                    throw new IOException("Setup evidence directory is linked or invalid");
                if(!Files.exists(path.toPath(),LinkOption.NOFOLLOW_LINKS))Files.createDirectory(path.toPath());
            }
            File target=new File(directory,"support.zip");
            try(ZipOutputStream out=new ZipOutputStream(Files.newOutputStream(target.toPath(),StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE,LinkOption.NOFOLLOW_LINKS))) {
                out.putNextEntry(new ZipEntry("runtime-setup-service.json"));out.write(raw.getBytes(StandardCharsets.UTF_8));out.closeEntry();
                JSONObject wrapper=new JSONObject().put("format",1).put("operation","setup_recovery").put("passed",false)
                        .put("app_id",evidence.optString("application_id")).put("app_version",evidence.optString("app_version"))
                        .put("gameplay_validated",false).put("runtime_setup_service",evidence);
                out.putNextEntry(new ZipEntry("wrapper.json"));out.write(wrapper.toString().getBytes(StandardCharsets.UTF_8));out.closeEntry();
            }
            return target;
        } catch(IOException failure){throw failure;}
        catch(Exception failure){throw new IOException("Setup recovery report could not be saved",failure);}
    }
    private void recoverSetupOperation() {
        SharedPreferences preferences=getSharedPreferences(SETUP_PREFS,MODE_PRIVATE);
        if(!preferences.getBoolean("was_busy",false))return;
        if(ClientRuntime.setupFinalizationInProgress()) {
            waitingForSetupFinalization=true;
            stage="Previous runtime setup finishing";
            detail="Waiting for the previous setup worker to stop safely.";
            return;
        }
        stage="Previous runtime setup interrupted";
        detail="Setup did not complete. Export the report for its last phase and this app's Android exit reason.";
        try {
            JSONObject recovered=setupMemoryEvidence(this).put("status","interrupted")
                    .put("recovered_utc_ms",System.currentTimeMillis())
                    .put("android_process_exit_history",ClientRuntime.setupProcessExitHistory(this));
            String raw=recovered.toString();
            if(raw.length()>MAX_SETUP_EVIDENCE)throw new IOException("Recovered setup evidence exceeded its bound");
            report=writeSetupRecoveryReport(recovered);
            preferences.edit().putBoolean("was_busy",false).putString("progress",raw).commit();
            getSharedPreferences(PREFS,MODE_PRIVATE).edit().putBoolean("was_busy",false)
                    .putString("stage",stage).putString("detail",detail).putString("report",report.getPath()).commit();
        } catch(Exception ignored) {
            detail="Setup did not complete. Its last checkpoint will be included in the next support report.";
        }
    }
    private ClientRuntime.Result executeSetup(ClientRuntime instance) throws Exception {
        try {
            setupRecoveryReserve=new byte[128*1024];
            checkpointSetup("Starting","Preparing the pinned runtime","running",true);
            ClientRuntime.Result result=instance.setup();
            checkpointSetup("Finished",result.summary,result.passed?"complete":"stopped",true);
            return result;
        } catch(OutOfMemoryError failure) {
            setupRecoveryReserve=null;
            String message="Runtime setup stopped at its Java memory limit. Close other apps and export the report before retrying.";
            try {
                checkpointSetup(lastSetupPhase,message,"java_heap_exhausted",true);
                setupFailureReport=writeSetupRecoveryReport(setupMemoryEvidence(this));
            } catch(Exception|OutOfMemoryError ignored) { /* The last durable phase remains available after restart. */ }
            throw new IOException(message);
        } finally { setupRecoveryReserve=null; }
    }
    private File validSetupReport(String path) throws IOException {
        if(path==null||path.length()>4096)return null;
        File selected=new File(path);
        if(!Files.isRegularFile(selected.toPath(),LinkOption.NOFOLLOW_LINKS))return null;
        File client=new File(getFilesDir().getCanonicalFile(),"client"),reports=new File(client,"reports");
        if(!Files.isDirectory(client.toPath(),LinkOption.NOFOLLOW_LINKS)||!Files.isDirectory(reports.toPath(),LinkOption.NOFOLLOW_LINKS))return null;
        File canonical=selected.getCanonicalFile();
        String prefix=reports.getCanonicalPath()+File.separator;
        return canonical.getPath().startsWith(prefix)?canonical:null;
    }
    private void refreshFinishedSetup() {
        if(!waitingForSetupFinalization||ClientRuntime.setupFinalizationInProgress())return;
        waitingForSetupFinalization=false;
        SharedPreferences preferences=getSharedPreferences(PREFS,MODE_PRIVATE);
        stage=preferences.getString("stage","Runtime setup stopped");
        detail=preferences.getString("detail","Export the latest report before retrying.");
        try{report=validSetupReport(preferences.getString("report",null));}catch(IOException ignored){report=null;}
        publish();
    }
    private void finishSetupWorker(PowerManager.WakeLock operationWake,Exception failure,Object owner,ClientRuntime.Result result,File sourceReport) {
        setupRecoveryReserve=null;
        try {
            if(ClientRuntime.ownsSetupReservation(owner)) {
                if(failure!=null&&"running".equals(setupMemoryEvidence(this).optString("status")))
                    checkpointSetup(lastSetupPhase,failure.getMessage(),"stopped",true);
                String terminalStage=stopping?"Stopped":failure!=null?"Runtime setup stopped":result!=null&&result.passed?"Runtime ready":"Runtime setup incomplete";
                String terminalDetail=stopping?"The operation stopped. Export the latest report to review cleanup.":failure!=null?"Export the latest report. "+(failure.getMessage()==null?failure.getClass().getSimpleName():failure.getMessage()):result==null?"Export the latest report.":result.summary;
                terminalDetail=terminalDetail.substring(0,Math.min(600,terminalDetail.length()));
                File terminalReport=setupFailureReport!=null?setupFailureReport:result!=null?result.report:sourceReport;
                getSharedPreferences(PREFS,MODE_PRIVATE).edit().putBoolean("was_busy",false)
                        .putString("stage",terminalStage).putString("detail",terminalDetail)
                        .putString("report",terminalReport==null?null:terminalReport.getPath()).commit();
            }
        } catch(Exception|OutOfMemoryError ignored) { /* Keep the last durable checkpoint. */ }
        finally {
            try { if(operationWake!=null&&operationWake.isHeld())operationWake.release(); }
            finally {
                setupWorkerOwnsWake=false;
                ClientRuntime.releaseSetupReservation(owner);
                // This volatile admission flag is last: a following setup cannot
                // acquire its wake before all of the old owner's writes finish.
                busy=false;
            }
        }
    }
    private void failedOperationDispatch(boolean setup,PowerManager.WakeLock operationWake,Object owner) {
        try {
            busy=false;runtime=null;inputReady=false;finishing=false;
            stage="Operation could not start";detail="Close other apps and export the latest report before retrying.";
            getSharedPreferences(PREFS,MODE_PRIVATE).edit().putBoolean("was_busy",false).putString("stage",stage).putString("detail",detail).apply();
            stopForeground(STOP_FOREGROUND_REMOVE);publish();stopSelf();
        } finally {
            if(setup)finishSetupWorker(operationWake,new IOException("Runtime setup could not be dispatched"),owner,null,null);
            else if(operationWake!=null&&operationWake.isHeld())operationWake.release();
        }
    }
    private void recoverStorageOperation(SharedPreferences preferences){
        if(!preferences.getBoolean("was_busy",false))return;
        storagePlan=null;storageBusy=false;
        storageStatus="Previous storage operation was interrupted. Export the storage report for its last progress and Android exit reason.";
        try{
            String checkpoint=preferences.getString("progress","{}");
            if(checkpoint.length()>16384)checkpoint="{}";
            JSONObject recovered=new JSONObject(checkpoint).put("format",2).put("status","interrupted")
                    .put("scope","app_private_storage_operation_diagnostic").put("cleanup_allowed",false)
                    .put("android_process_exit_history",storageProcessExits());
            storageReport=writeStorageReport(recovered.toString());
        }catch(Exception ignored){storageStatus="Previous storage operation was interrupted. Its checkpoint could not be exported; scan again when idle.";}
        preferences.edit().putBoolean("was_busy",false).putString("status",storageStatus)
                .putString("report",storageReport==null?null:storageReport.getPath()).apply();
    }
    private void checkpointStorage(String mode,String phase,int entries,String path,long elapsed) throws IOException {
        if(storageStopRequested.get())throw new InterruptedIOException("Storage operation cancelled");
        try{
            Runtime vm=Runtime.getRuntime();
            String boundedPath=path==null?"":path.substring(0,Math.min(2048,path.length()));
            JSONObject checkpoint=new JSONObject().put("format",2).put("scope","app_private_storage_operation_diagnostic")
                    .put("status","running").put("mode",mode).put("phase",phase).put("entries",entries)
                    .put("last_relative_path",boundedPath).put("elapsed_ms",elapsed).put("updated_utc_ms",System.currentTimeMillis())
                    .put("java_heap_used_bytes",vm.totalMemory()-vm.freeMemory()).put("java_heap_limit_bytes",vm.maxMemory())
                    .put("native_heap_allocated_bytes",Debug.getNativeHeapAllocatedSize()).put("cleanup_allowed",false);
            if(!getSharedPreferences("storage_ui",MODE_PRIVATE).edit().putBoolean("was_busy",true)
                    .putString("progress",checkpoint.toString()).commit())throw new IOException("Storage checkpoint could not be saved");
            String message=phase+" · "+entries+" entries · "+elapsed/1000+"s";
            main.post(()->{if(destroyed)return;storageStatus=message;publish();notifyStatus();});
        }catch(IOException e){throw e;}
        catch(Exception e){throw new IOException("Storage checkpoint could not be saved",e);}
    }
    private File storageFailureReport(String message) throws IOException {
        try{
            String checkpoint=getSharedPreferences("storage_ui",MODE_PRIVATE).getString("progress","{}");
            if(checkpoint.length()>16384)checkpoint="{}";
            return writeStorageReport(new JSONObject(checkpoint).put("format",2).put("status","stopped")
                    .put("error",message.substring(0,Math.min(240,message.length()))).put("cleanup_allowed",false)
                    .put("android_process_exit_history",storageProcessExits()).toString());
        }catch(IOException e){throw e;}
        catch(Exception e){throw new IOException("Storage failure report could not be saved",e);}
    }
    private void startStorage(Intent intent,boolean cleaning){
        if(destroyed||busy||storageBusy||reportExporting||ClientRuntime.operationInProgress()||ClientRuntime.cleanupBlocked(this))return;
        final StorageAudit.Plan reviewed=storagePlan;
        final Set<String> selected=new LinkedHashSet<>();
        if(cleaning){
            String[] ids=intent.getStringArrayExtra("storage_categories");
            if(reviewed==null||!reviewed.cleanupAllowed||!reviewed.snapshotId.equals(intent.getStringExtra("storage_snapshot"))||ids==null||ids.length==0||ids.length>3)return;
            selected.addAll(Arrays.asList(ids));
            if(!new HashSet<>(Arrays.asList("old_runtime","downloads","old_reports")).containsAll(selected))return;
        }
        final Object owner;
        try{owner=ClientRuntime.acquireStorage(this);}catch(IOException e){storageStatus=e.getMessage();publish();return;}
        storageStopRequested.set(false);storageBusy=true;storageStatus=cleaning?"Cleaning the selected disposable files…":"Scanning private storage. No files are being changed…";
        final PowerManager.WakeLock storageWake;
        try{storageWake=((PowerManager)getSystemService(POWER_SERVICE)).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"cohclient:storage");}
        catch(RuntimeException e){ClientRuntime.releaseStorage(owner);storageBusy=false;storageStatus="Could not start storage work. Reopen this screen and retry.";publish();return;}
        try{startForeground(NOTICE,notification());storageWake.acquire(40*60*1000L);publish();worker.execute(()->{
            StorageAudit.Plan plan=null;File saved=null;String result=null;
            try{
                storageRecoveryReserve=new byte[128*1024];
                String mode=cleaning?"cleanup":"scan";checkpointStorage(mode,"Starting",0,"",0);
                StorageAudit.ProgressListener progress=(phase,entries,path,elapsed)->checkpointStorage(mode,phase,entries,path,elapsed);
                StorageFiles fs=new StorageFiles(getFilesDir(),getCacheDir());StorageAudit.Limits limits=StorageAudit.Limits.defaults();
                if(cleaning){StorageAudit.CleanupResult cleanup=StorageAudit.cleanup(fs,reviewed,selected,limits,progress);saved=writeStorageReport(cleanup.toJson());plan=cleanup.afterPlan;result=cleanup.stalePlan?"Storage changed after review. No cleanup was started; review the fresh scan.":cleanup.completed?"Cleanup finished: "+cleanup.deletedCount+" entries removed. Review the fresh totals and export its report.":"Cleanup stopped before all selected files were removed. Review the fresh totals and export its report.";}
                else{plan=StorageAudit.scan(fs,currentManifestSha(),limits,progress);saved=writeStorageReport(plan.toJson());result=plan.cleanupAllowed?"Storage scan complete. Select disposable categories to review cleanup.":plan.complete?"Storage scan complete. Cleanup is unavailable; export the report for details.":"Storage scan incomplete. Cleanup is unavailable; export the storage report.";}
            }catch(OutOfMemoryError e){plan=null;storageRecoveryReserve=null;result="Storage operation stopped at its memory limit. Export the storage report.";try{saved=storageFailureReport(result);}catch(Exception ignored){} }
            catch(Exception e){plan=null;result="Storage operation stopped: "+(e.getMessage()==null?e.getClass().getSimpleName():e.getMessage());try{saved=storageFailureReport(result);}catch(Exception ignored){} }
            finally{
                storageRecoveryReserve=null;
                try{if(result!=null)getSharedPreferences("storage_ui",MODE_PRIVATE).edit().putBoolean("was_busy",saved==null).putString("status",result)
                        .putString("report",saved==null?null:saved.getPath()).commit();}
                finally{ClientRuntime.releaseStorage(owner);if(storageWake.isHeld())storageWake.release();}
            }
            final StorageAudit.Plan completed=plan;final File reportFile=saved;final String message=result;
            main.post(()->{storageBusy=false;if(destroyed)return;storagePlan=completed;storageReport=reportFile;storageStatus=message;stopForeground(STOP_FOREGROUND_REMOVE);publish();stopSelf();});
        });}catch(RuntimeException e){ClientRuntime.releaseStorage(owner);if(storageWake.isHeld())storageWake.release();storageBusy=false;storageStatus="Could not start storage work. Reopen this screen and retry.";stopForeground(STOP_FOREGROUND_REMOVE);publish();}
    }
    @Override public int onStartCommand(Intent intent,int flags,int startId){
        String action=intent==null?null:intent.getAction();
        if(STORAGE_SCAN.equals(action)||STORAGE_CLEAN.equals(action)){startStorage(intent,STORAGE_CLEAN.equals(action));return START_NOT_STICKY;}
        if(FINISH.equals(action)){requestFinish();return START_NOT_STICKY;}
        if(STOP.equals(action)&&storageBusy){storageStopRequested.set(true);storageStatus="Cancelling storage work; waiting for owned file operations to finish…";publish();notifyStatus();return START_NOT_STICKY;}
        if(STOP.equals(action)){ClientRuntime r=runtime;if(busy&&!stopping&&r!=null&&r.requestStop()){stopping=true;stage="Stopping";detail=setupWorkerOwnsWake?"Waiting for runtime setup to stop safely.":"Waiting for the client and Wine to close.";publish();notifyStatus();}return START_NOT_STICKY;}
        if(!SETUP.equals(action)&&!IMPORT.equals(action)&&!RUN.equals(action)&&!CREATE.equals(action))return START_NOT_STICKY;
        if(busy||storageBusy||reportExporting||ClientRuntime.operationInProgress()||ClientRuntime.cleanupBlocked(this)){blocked=ClientRuntime.cleanupBlocked(this);if(blocked){stage="Cleanup needs attention";detail="Export the report, force-stop this app in Android settings, then reopen.";publish();}return START_NOT_STICKY;}
        if(RUN.equals(action)||CREATE.equals(action)){
            refreshProfileState();
            if((CREATE.equals(action)&&profileState!=ClientRuntime.ProfileState.ABSENT)
                    ||(RUN.equals(action)&&profileState!=ClientRuntime.ProfileState.READY)){
                stage=profileState==ClientRuntime.ProfileState.ABSENT?"Saved profile missing":"Saved profile needs attention";
                detail=profileNote;publish();return START_NOT_STICKY;
            }
        }
        final android.net.Uri importUri=intent.getData();
        if(IMPORT.equals(action)&&importUri==null)return START_NOT_STICKY;
        final boolean setup=SETUP.equals(action), importing=IMPORT.equals(action), creating=CREATE.equals(action);final String selectedSession;
        final Object setupOwner;
        try{setupOwner=setup?ClientRuntime.acquireSetupReservation(this):null;}
        catch(IOException failure){stage="Previous operation finishing";detail=failure.getMessage();publish();return START_NOT_STICKY;}
        PowerManager.WakeLock dispatchWake=null;
        try {
        storagePlan=null;
        busy=true;stopping=false;blocked=false;inputReady=false;finishing=false;characterSaved=false;canReturnGround=false;canSaveLogout=false;inputSent=0;inputFailed=0;readyDeadlineUptimeMillis=0;saveDeadlineUptimeMillis=0;movementDeadlineUptimeMillis=0;sessionPhase="menu";report=null;certified=0;logs.setLength(0);frame=null;certificationErrors.clear();
        session=(RUN.equals(action)||CREATE.equals(action))?UUID.randomUUID().toString().replace("-",""):"";
        stage=SETUP.equals(action)?"Setting up runtime":IMPORT.equals(action)?"Importing client data":"Starting CoH client";
        detail=SETUP.equals(action)?"Preparing the private runtime. Close other apps; setup pauses if available memory is low.":IMPORT.equals(action)?"Verify and import the same reviewed asset ZIP used for Atlas.":"Starting the persistent database, DbServer and Atlas before the client. Atlas startup may take up to 40 minutes on the Thor.";
        getSharedPreferences(PREFS,MODE_PRIVATE).edit().putBoolean("was_busy",true).remove("report").apply();
        selectedSession=session;
        if(setup){setupStartedUtc=System.currentTimeMillis();lastSetupCheckpointUptime=0;lastSetupPhase="";setupFailureReport=null;setupWorkerOwnsWake=true;setupAppVersion=setupAppVersion();String appId=getPackageName();setupAppId=appId.substring(0,Math.min(160,appId.length()));}
        startForeground(NOTICE,notification());
        wake=((PowerManager)getSystemService(POWER_SERVICE)).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"cohclient:operation");dispatchWake=wake;wake.acquire(95*60*1000L);
        final PowerManager.WakeLock operationWake=dispatchWake;
        publish();
        ClientRuntime instance=new ClientRuntime(this,new ClientRuntime.Listener(){
            @Override public void onStage(String name,String text){if(setup)try{checkpointSetup(name,text,"running",false);}catch(IOException failure){throw new IllegalStateException("Setup checkpoint could not be saved",failure);}main.post(()->{if(!busy||destroyed)return;if(!stopping&&!finishing){stage=name;detail=text;}publish();notifyStatus();});}
            @Override public void onLog(String text){main.post(()->{if(destroyed)return;logs.append(text).append('\n');if(logs.length()>6000)logs.delete(0,logs.length()-6000);publish();});}
            @Override public void onFrame(int[] pixels,int width,int height,long sequence){queueFrame(pixels,width,height,sequence);}
            @Override public void onInputState(boolean ready,boolean ending,boolean saved,boolean returnAvailable,boolean saveAvailable,long sent,long failed,long deadline,String phase,long saveDeadline,long movementDeadline){main.post(()->{if(!busy||destroyed)return;boolean noticeChanged=inputReady!=ready||finishing!=ending||characterSaved!=saved;inputReady=ready;finishing=ending;characterSaved=saved;canReturnGround=returnAvailable;canSaveLogout=saveAvailable;inputSent=sent;inputFailed=failed;readyDeadlineUptimeMillis=deadline;sessionPhase=phase;saveDeadlineUptimeMillis=saveDeadline;movementDeadlineUptimeMillis=movementDeadline;publish();if(noticeChanged)notifyStatus();});}
        });
        if(setup)instance.attachSetupReservation(setupOwner);
        runtime=instance;instance.recordLifecycle("operation_requested setup="+setup+" activity_visible="+uiVisible);
        worker.execute(()->{
            ClientRuntime.Result result=null;Exception failure=null;
            try{result=setup?executeSetup(instance):importing?instance.importAssets(importUri):(creating?instance.runFreshCreation(selectedSession):instance.run(selectedSession));}catch(Exception e){failure=e;}
            finally{if(setup)finishSetupWorker(operationWake,failure,setupOwner,result,instance.getLatestReport());}
            final ClientRuntime.Result outcome=result;final Exception error=failure;
            main.post(()->{
                if(destroyed||runtime!=instance)return;
                blocked=instance.isCleanupBlocked();busy=false;inputReady=false;finishing=false;
                refreshProfileState();
                report=setup&&setupFailureReport!=null?setupFailureReport:outcome!=null?outcome.report:instance.getLatestReport();
                if(blocked){stage="Cleanup needs attention";detail="Export the report, then force-stop COH Character Reopen in Android settings before reopening.";}
                else if(stopping){stage="Stopped";detail="The operation stopped. Export the latest report to review cleanup.";}
                else if(error!=null){stage=setup?"Runtime setup stopped":"Test failed";detail="Export the latest report. "+(error.getMessage()==null?error.getClass().getSimpleName():error.getMessage());}
                else if(outcome!=null&&outcome.passed){stage=setup?"Runtime ready":importing?"Client data ready":creating?"Character creation check complete":"Character reopen check complete";detail=outcome.summary;}
                else {stage=setup?"Runtime setup incomplete":creating?"Character creation check incomplete":"Character reopen check incomplete";detail=outcome==null?"Export the latest report.":outcome.summary;}
                runtime=null;
                getSharedPreferences(PREFS,MODE_PRIVATE).edit().putBoolean("was_busy",false).putString("stage",stage).putString("detail",detail).putString("report",report==null?null:report.getPath()).putInt("certified",certified).putLong("input_sent",inputSent).putLong("input_failed",inputFailed).apply();
                if(operationWake!=null&&operationWake.isHeld())operationWake.release();stopForeground(STOP_FOREGROUND_REMOVE);publish();stopSelf();
            });
        });
        } catch(RuntimeException failure){failedOperationDispatch(setup,dispatchWake,setupOwner);}
        catch(OutOfMemoryError failure){if(!setup)throw failure;setupRecoveryReserve=null;failedOperationDispatch(true,dispatchWake,setupOwner);}
        return START_NOT_STICKY;
    }
    private Notification notification(){
        PendingIntent open=PendingIntent.getActivity(this,0,new Intent(this,ClientActivity.class),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder b=new Notification.Builder(this,CHANNEL).setSmallIcon(android.R.drawable.ic_menu_view).setContentTitle(storageBusy?"COH storage":"COH Character Reopen · "+stage).setContentText(storageBusy?storageStatus:detail).setContentIntent(open).setOngoing(busy||storageBusy).setOnlyAlertOnce(true);
        if(busy&&inputReady&&characterSaved)b.addAction(new Notification.Action.Builder(null,"Finish",PendingIntent.getService(this,2,new Intent(this,ClientService.class).setAction(FINISH),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE)).build());
        if(busy||storageBusy)b.addAction(new Notification.Action.Builder(null,storageBusy?"Cancel storage work":"Stop",PendingIntent.getService(this,1,new Intent(this,ClientService.class).setAction(STOP),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE)).build());
        return b.build();
    }
    private void notifyStatus(){if(busy||storageBusy)((NotificationManager)getSystemService(NOTIFICATION_SERVICE)).notify(NOTICE,notification());}
    @Override public void onDestroy(){destroyed=true;if(storageBusy)storageStopRequested.set(true);main.removeCallbacks(sessionDeadlineTick);ClientRuntime r=runtime;if(r!=null)r.requestStop();worker.shutdown();listeners.clear();try{unregisterReceiver(screenReceiver);}catch(Exception ignored){}if(!setupWorkerOwnsWake&&wake!=null&&wake.isHeld())wake.release();super.onDestroy();}
}
