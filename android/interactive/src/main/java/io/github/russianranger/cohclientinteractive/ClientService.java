package io.github.russianranger.cohclientinteractive;

import android.app.*;
import android.content.*;
import android.os.*;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

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
        State(boolean busy,boolean blocked,String stage,String detail,String session,String log,File report,int certified,boolean inputReady,boolean finishing,boolean characterSaved,boolean canReturnGround,boolean canSaveLogout,long inputSent,long inputFailed,long deadline,String phase,long saveDeadline,long movementDeadline,boolean storageBusy,boolean reportExporting,StorageAudit.Plan storagePlan,String storageStatus,File storageReport) {
            this.busy=busy;this.blocked=blocked;this.stage=stage;this.detail=detail;this.session=session;this.log=log;this.report=report;this.certified=certified;this.inputReady=inputReady;this.finishing=finishing;
            this.characterSaved=characterSaved;this.canReturnGround=canReturnGround;this.canSaveLogout=canSaveLogout;this.inputSent=inputSent;this.inputFailed=inputFailed;this.readyDeadlineUptimeMillis=deadline;this.sessionPhase=phase;this.saveDeadlineUptimeMillis=saveDeadline;this.movementDeadlineUptimeMillis=movementDeadline;
            this.storageBusy=storageBusy;this.reportExporting=reportExporting;this.storagePlan=storagePlan;this.storageStatus=storageStatus;this.storageReport=storageReport;
        }
    }
    public final class LocalBinder extends Binder { public ClientService service(){return ClientService.this;} }
    private final LocalBinder binder=new LocalBinder();
    private final Handler main=new Handler(Looper.getMainLooper());
    private final Runnable sessionDeadlineTick=new Runnable(){@Override public void run(){
        if(destroyed)return;
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
        SharedPreferences storage=getSharedPreferences("storage_ui",MODE_PRIVATE);
        String storagePath=storage.getString("report",null);
        if(storagePath!=null)try{File f=new File(storagePath);File parent=new File(getCacheDir().getCanonicalFile(),"storage-tools");if(Files.isRegularFile(f.toPath(),LinkOption.NOFOLLOW_LINKS)&&f.getCanonicalFile().getParentFile().equals(parent))storageReport=f;}catch(Exception ignored){}
        storageStatus=storage.getString("status",storageStatus);
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
    private State snapshot(){return new State(busy,blocked,stage,detail,session,logs.toString(),report,certified,inputReady,finishing,characterSaved,canReturnGround,canSaveLogout,inputSent,inputFailed,readyDeadlineUptimeMillis,sessionPhase,saveDeadlineUptimeMillis,movementDeadlineUptimeMillis,storageBusy,reportExporting,storagePlan,storageStatus,storageReport);}
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
        storageBusy=true;storageStatus=cleaning?"Cleaning the selected disposable files…":"Scanning private storage. No files are being changed…";
        final PowerManager.WakeLock storageWake;
        try{storageWake=((PowerManager)getSystemService(POWER_SERVICE)).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"cohclient:storage");}
        catch(RuntimeException e){ClientRuntime.releaseStorage(owner);storageBusy=false;storageStatus="Could not start storage work. Reopen this screen and retry.";publish();return;}
        try{startForeground(NOTICE,notification());storageWake.acquire(40*60*1000L);publish();worker.execute(()->{
            StorageAudit.Plan plan=null;File saved=null;String result;
            try{
                StorageFiles fs=new StorageFiles(getFilesDir());StorageAudit.Limits limits=StorageAudit.Limits.defaults();
                if(cleaning){StorageAudit.CleanupResult cleanup=StorageAudit.cleanup(fs,reviewed,selected,limits);saved=writeStorageReport(cleanup.toJson());plan=cleanup.afterPlan;result=cleanup.stalePlan?"Storage changed after review. No cleanup was started; review the fresh scan.":cleanup.completed?"Cleanup finished: "+cleanup.deletedCount+" entries removed. Review the fresh totals and export its report.":"Cleanup stopped before all selected files were removed. Review the fresh totals and export its report.";}
                else{plan=StorageAudit.scan(fs,currentManifestSha(),limits);saved=writeStorageReport(plan.toJson());result=plan.cleanupAllowed?"Storage scan complete. Select disposable categories to review cleanup.":plan.complete?"Storage scan complete. Cleanup is unavailable; export the report for details.":"Storage scan incomplete. Cleanup is unavailable; export the storage report.";}
            }catch(Exception e){result="Storage operation stopped: "+(e.getMessage()==null?e.getClass().getSimpleName():e.getMessage());}
            finally{ClientRuntime.releaseStorage(owner);if(storageWake.isHeld())storageWake.release();}
            final StorageAudit.Plan completed=plan;final File reportFile=saved;final String message=result;
            main.post(()->{storageBusy=false;if(destroyed)return;storagePlan=completed;if(reportFile!=null)storageReport=reportFile;storageStatus=message;getSharedPreferences("storage_ui",MODE_PRIVATE).edit().putString("report",storageReport==null?null:storageReport.getPath()).putString("status",storageStatus).apply();stopForeground(STOP_FOREGROUND_REMOVE);publish();stopSelf();});
        });}catch(RuntimeException e){ClientRuntime.releaseStorage(owner);if(storageWake.isHeld())storageWake.release();storageBusy=false;storageStatus="Could not start storage work. Reopen this screen and retry.";stopForeground(STOP_FOREGROUND_REMOVE);publish();}
    }
    @Override public int onStartCommand(Intent intent,int flags,int startId){
        String action=intent==null?null:intent.getAction();
        if(STORAGE_SCAN.equals(action)||STORAGE_CLEAN.equals(action)){startStorage(intent,STORAGE_CLEAN.equals(action));return START_NOT_STICKY;}
        if(FINISH.equals(action)){requestFinish();return START_NOT_STICKY;}
        if(STOP.equals(action)){ClientRuntime r=runtime;if(busy&&!stopping&&r!=null&&r.requestStop()){stopping=true;stage="Stopping";detail="Waiting for the client and Wine to close.";publish();notifyStatus();}return START_NOT_STICKY;}
        if(!SETUP.equals(action)&&!IMPORT.equals(action)&&!RUN.equals(action)&&!CREATE.equals(action))return START_NOT_STICKY;
        if(busy||storageBusy||reportExporting||ClientRuntime.operationInProgress()||ClientRuntime.cleanupBlocked(this)){blocked=ClientRuntime.cleanupBlocked(this);if(blocked){stage="Cleanup needs attention";detail="Export the report, force-stop this app in Android settings, then reopen.";publish();}return START_NOT_STICKY;}
        final android.net.Uri importUri=intent.getData();
        if(IMPORT.equals(action)&&importUri==null)return START_NOT_STICKY;
        storagePlan=null;
        busy=true;stopping=false;blocked=false;inputReady=false;finishing=false;characterSaved=false;canReturnGround=false;canSaveLogout=false;inputSent=0;inputFailed=0;readyDeadlineUptimeMillis=0;saveDeadlineUptimeMillis=0;movementDeadlineUptimeMillis=0;sessionPhase="menu";report=null;certified=0;logs.setLength(0);frame=null;certificationErrors.clear();
        session=(RUN.equals(action)||CREATE.equals(action))?UUID.randomUUID().toString().replace("-",""):"";
        stage=SETUP.equals(action)?"Setting up runtime":IMPORT.equals(action)?"Importing client data":"Starting CoH client";
        detail=SETUP.equals(action)?"Download and unpack the private runtime once.":IMPORT.equals(action)?"Verify and import the same reviewed asset ZIP used for Atlas.":"Starting the persistent database, DbServer and Atlas before the client. Atlas startup may take up to 40 minutes on the Thor.";
        getSharedPreferences(PREFS,MODE_PRIVATE).edit().putBoolean("was_busy",true).remove("report").apply();
        startForeground(NOTICE,notification());
        wake=((PowerManager)getSystemService(POWER_SERVICE)).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"cohclient:operation");wake.acquire(95*60*1000L);
        publish();
        final boolean setup=SETUP.equals(action), importing=IMPORT.equals(action), creating=CREATE.equals(action);final String selectedSession=session;
        ClientRuntime instance=new ClientRuntime(this,new ClientRuntime.Listener(){
            @Override public void onStage(String name,String text){main.post(()->{if(!busy||destroyed)return;if(!stopping&&!finishing){stage=name;detail=text;}publish();notifyStatus();});}
            @Override public void onLog(String text){main.post(()->{if(destroyed)return;logs.append(text).append('\n');if(logs.length()>6000)logs.delete(0,logs.length()-6000);publish();});}
            @Override public void onFrame(int[] pixels,int width,int height,long sequence){queueFrame(pixels,width,height,sequence);}
            @Override public void onInputState(boolean ready,boolean ending,boolean saved,boolean returnAvailable,boolean saveAvailable,long sent,long failed,long deadline,String phase,long saveDeadline,long movementDeadline){main.post(()->{if(!busy||destroyed)return;boolean noticeChanged=inputReady!=ready||finishing!=ending||characterSaved!=saved;inputReady=ready;finishing=ending;characterSaved=saved;canReturnGround=returnAvailable;canSaveLogout=saveAvailable;inputSent=sent;inputFailed=failed;readyDeadlineUptimeMillis=deadline;sessionPhase=phase;saveDeadlineUptimeMillis=saveDeadline;movementDeadlineUptimeMillis=movementDeadline;publish();if(noticeChanged)notifyStatus();});}
        });
        runtime=instance;instance.recordLifecycle("operation_requested setup="+setup+" activity_visible="+uiVisible);
        worker.execute(()->{
            ClientRuntime.Result result=null;Exception failure=null;
            try{result=setup?instance.setup():importing?instance.importAssets(importUri):(creating?instance.runCreation(selectedSession):instance.run(selectedSession));}catch(Exception e){failure=e;}
            final ClientRuntime.Result outcome=result;final Exception error=failure;
            main.post(()->{
                if(destroyed)return;
                blocked=instance.isCleanupBlocked();busy=false;inputReady=false;finishing=false;
                report=outcome!=null?outcome.report:instance.getLatestReport();
                if(blocked){stage="Cleanup needs attention";detail="Export the report, then force-stop COH Character Reopen in Android settings before reopening.";}
                else if(stopping){stage="Stopped";detail="The operation stopped. Export the latest report to review cleanup.";}
                else if(error!=null){stage="Test failed";detail="Export the latest report. "+(error.getMessage()==null?error.getClass().getSimpleName():error.getMessage());}
                else if(outcome!=null&&outcome.passed){stage=setup?"Runtime ready":importing?"Client data ready":creating?"Character creation check complete":"Character reopen check complete";detail=outcome.summary;}
                else {stage=creating?"Character creation check incomplete":"Character reopen check incomplete";detail=outcome==null?"Export the latest report.":outcome.summary;}
                runtime=null;
                getSharedPreferences(PREFS,MODE_PRIVATE).edit().putBoolean("was_busy",false).putString("stage",stage).putString("detail",detail).putString("report",report==null?null:report.getPath()).putInt("certified",certified).putLong("input_sent",inputSent).putLong("input_failed",inputFailed).apply();
                if(wake!=null&&wake.isHeld())wake.release();stopForeground(STOP_FOREGROUND_REMOVE);publish();stopSelf();
            });
        });
        return START_NOT_STICKY;
    }
    private Notification notification(){
        PendingIntent open=PendingIntent.getActivity(this,0,new Intent(this,ClientActivity.class),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder b=new Notification.Builder(this,CHANNEL).setSmallIcon(android.R.drawable.ic_menu_view).setContentTitle(storageBusy?"COH storage":"COH Character Reopen · "+stage).setContentText(storageBusy?storageStatus:detail).setContentIntent(open).setOngoing(busy||storageBusy).setOnlyAlertOnce(true);
        if(busy&&inputReady&&characterSaved)b.addAction(new Notification.Action.Builder(null,"Finish",PendingIntent.getService(this,2,new Intent(this,ClientService.class).setAction(FINISH),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE)).build());
        if(busy)b.addAction(new Notification.Action.Builder(null,"Stop",PendingIntent.getService(this,1,new Intent(this,ClientService.class).setAction(STOP),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE)).build());
        return b.build();
    }
    private void notifyStatus(){if(busy)((NotificationManager)getSystemService(NOTIFICATION_SERVICE)).notify(NOTICE,notification());}
    @Override public void onDestroy(){destroyed=true;main.removeCallbacks(sessionDeadlineTick);ClientRuntime r=runtime;if(r!=null)r.requestStop();worker.shutdown();listeners.clear();try{unregisterReceiver(screenReceiver);}catch(Exception ignored){}if(wake!=null&&wake.isHeld())wake.release();super.onDestroy();}
}
