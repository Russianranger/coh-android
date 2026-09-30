package io.github.russianranger.cohpresentation;

import android.app.*;
import android.content.*;
import android.os.*;
import java.io.File;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

/** One foreground-owned display operation; no server boot or game-data import. */
public final class PresentationService extends Service {
    public static final String SETUP="coh.presentation.SETUP", RUN="coh.presentation.RUN", STOP="coh.presentation.STOP";
    private static final String CHANNEL="presentation", PREFS="presentation_ui";
    private static final int NOTICE=51;
    public interface Listener { void onState(State state); void onFrame(int[] pixels,int width,int height,long sequence); }
    public static final class State {
        public final boolean busy, blocked;
        public final String stage, detail, session, log;
        public final File report;
        public final int certified;
        State(boolean busy,boolean blocked,String stage,String detail,String session,String log,File report,int certified) {
            this.busy=busy;this.blocked=blocked;this.stage=stage;this.detail=detail;this.session=session;this.log=log;this.report=report;this.certified=certified;
        }
    }
    public final class LocalBinder extends Binder { public PresentationService service(){return PresentationService.this;} }
    private final LocalBinder binder=new LocalBinder();
    private final Handler main=new Handler(Looper.getMainLooper());
    private final ExecutorService worker=Executors.newSingleThreadExecutor();
    private final List<Listener> listeners=new ArrayList<>();
    private final AtomicBoolean framePending=new AtomicBoolean();
    private final StringBuilder logs=new StringBuilder();
    private volatile PresentationRuntime runtime;
    private volatile boolean busy, stopping, destroyed;
    private boolean blocked, uiVisible;
    private String stage="Ready", detail="Set up the runtime, then run the 60-second display test.", session="";
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
        @Override public void onReceive(Context context,Intent intent){ lifecycle("screen_event="+intent.getAction()); }
    };
    @Override public void onCreate(){
        super.onCreate();
        NotificationManager manager=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);
        manager.createNotificationChannel(new NotificationChannel(CHANNEL,"Client display test",NotificationManager.IMPORTANCE_LOW));
        blocked=PresentationRuntime.cleanupBlocked(this);
        SharedPreferences p=getSharedPreferences(PREFS,MODE_PRIVATE);
        if(p.getBoolean("was_busy",false)){stage="Previous test interrupted";detail="The previous operation did not complete. Review its report before starting another test.";}
        else {stage=p.getString("stage",stage);detail=p.getString("detail",detail);}
        String saved=p.getString("report",null);
        if(saved!=null){try{File f=new File(saved).getCanonicalFile();if(f.isFile()&&f.getPath().startsWith(getFilesDir().getCanonicalPath()+File.separator))report=f;}catch(Exception ignored){}}
        if(blocked){stage="Cleanup needs attention";detail="Force-stop COH Client Test in Android settings, then reopen it before starting more work.";}
        IntentFilter f=new IntentFilter();f.addAction(Intent.ACTION_SCREEN_OFF);f.addAction(Intent.ACTION_SCREEN_ON);
        if(Build.VERSION.SDK_INT>=33)registerReceiver(screenReceiver,f,Context.RECEIVER_NOT_EXPORTED);else registerReceiver(screenReceiver,f);
    }
    @Override public IBinder onBind(Intent intent){return binder;}
    public void addListener(Listener listener){listeners.add(listener);listener.onState(snapshot());deliverFrame(listener);}
    public void removeListener(Listener listener){listeners.remove(listener);}
    public void setUiVisible(boolean visible){uiVisible=visible;lifecycle("activity_visible="+visible);}
    private void lifecycle(String event){PresentationRuntime r=runtime;if(r!=null&&busy)r.recordLifecycle(event);}
    private State snapshot(){return new State(busy,blocked,stage,detail,session,logs.toString(),report,certified);}
    private void publish(){if(destroyed)return;State s=snapshot();for(Listener l:new ArrayList<>(listeners))l.onState(s);}
    private void deliverFrame(Listener l){Frame value=frame;if(value!=null)l.onFrame(value.pixels,value.width,value.height,value.sequence);}
    private void queueFrame(int[] pixels,int width,int height,long sequence){
        frame=new Frame(pixels,width,height,sequence);
        if(framePending.compareAndSet(false,true))main.post(()->{framePending.set(false);if(!destroyed)for(Listener l:new ArrayList<>(listeners))deliverFrame(l);});
    }
    public void recordCertification(PresentationSurface.Certification c){
        PresentationRuntime r=runtime;if(!busy||r==null||!session.equals(c.session))return;
        Map<String,Object> record=new LinkedHashMap<>();
        record.put("session_id",c.session);record.put("frame_id",c.frameId);record.put("pixel_copy_success",true);record.put("matching_session",true);
        record.put("captured_elapsed_ms",c.capturedAtUptimeMillis);record.put("sequence",c.sequence);record.put("surface_generation",c.surfaceGeneration);
        record.put("source_width",c.width);record.put("source_height",c.height);record.put("surface_width",c.surfaceWidth);record.put("surface_height",c.surfaceHeight);
        record.put("bars_hex",Arrays.asList(c.barsHex));r.recordSurfaceCertification(record);certified++;publish();
    }
    public void recordCertificationError(String error){
        PresentationRuntime r=runtime;if(!busy||r==null)return;
        String key=error==null?"unknown":error.substring(0,Math.min(160,error.length()));
        if(!certificationErrors.containsKey(key)&&certificationErrors.size()>=16)return;
        int count=certificationErrors.getOrDefault(key,0)+1;certificationErrors.put(key,count);
        if(count==1||(count&(count-1))==0)r.recordLifecycle("surface_certification_error count="+count+" message="+key);
    }
    @Override public int onStartCommand(Intent intent,int flags,int startId){
        String action=intent==null?null:intent.getAction();
        if(STOP.equals(action)){PresentationRuntime r=runtime;if(busy&&!stopping&&r!=null&&r.requestStop()){stopping=true;stage="Stopping";detail="Waiting for owned display and Wine cleanup.";publish();notifyStatus();}return START_NOT_STICKY;}
        if(!SETUP.equals(action)&&!RUN.equals(action))return START_NOT_STICKY;
        if(busy||PresentationRuntime.cleanupBlocked(this)){blocked=PresentationRuntime.cleanupBlocked(this);if(blocked){stage="Cleanup needs attention";detail="Export the report, force-stop this app in Android settings, then reopen.";publish();}return START_NOT_STICKY;}
        busy=true;stopping=false;blocked=false;report=null;certified=0;logs.setLength(0);frame=null;certificationErrors.clear();
        session=RUN.equals(action)?UUID.randomUUID().toString().replace("-",""):"";
        stage=SETUP.equals(action)?"Setting up runtime":"Starting display test";
        detail=SETUP.equals(action)?"Download and unpack the private runtime once.":"Preparing Wine; the visible animation lasts 60 seconds. No server is started.";
        getSharedPreferences(PREFS,MODE_PRIVATE).edit().putBoolean("was_busy",true).remove("report").apply();
        startForeground(NOTICE,notification());
        wake=((PowerManager)getSystemService(POWER_SERVICE)).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"cohpresentation:operation");wake.acquire(20*60*1000L);
        publish();
        final boolean setup=SETUP.equals(action);final String selectedSession=session;
        PresentationRuntime instance=new PresentationRuntime(this,new PresentationRuntime.Listener(){
            @Override public void onStage(String name,String text){main.post(()->{if(!busy||destroyed)return;if(!stopping){stage=name;detail=text;}publish();notifyStatus();});}
            @Override public void onLog(String text){main.post(()->{if(destroyed)return;logs.append(text).append('\n');if(logs.length()>6000)logs.delete(0,logs.length()-6000);publish();});}
            @Override public void onFrame(int[] pixels,int width,int height,long sequence){queueFrame(pixels,width,height,sequence);}
        });
        runtime=instance;instance.recordLifecycle("operation_requested setup="+setup+" activity_visible="+uiVisible);
        worker.execute(()->{
            PresentationRuntime.Result result=null;Exception failure=null;
            try{result=setup?instance.setup():instance.run(selectedSession);}catch(Exception e){failure=e;}
            final PresentationRuntime.Result outcome=result;final Exception error=failure;
            main.post(()->{
                if(destroyed)return;
                blocked=instance.isCleanupBlocked();busy=false;
                report=outcome!=null?outcome.report:instance.getLatestReport();
                if(blocked){stage="Cleanup needs attention";detail="Export the report, then force-stop COH Client Test in Android settings before reopening.";}
                else if(stopping){stage="Stopped";detail="The operation stopped. Export the latest report to review cleanup.";}
                else if(error!=null){stage="Test failed";detail="Export the latest report. "+(error.getMessage()==null?error.getClass().getSimpleName():error.getMessage());}
                else if(outcome!=null&&outcome.passed){stage=setup?"Runtime ready":"Visible display test passed";detail=outcome.summary;}
                else {stage="Display check incomplete";detail=outcome==null?"Export the latest report.":outcome.summary;}
                runtime=null;
                getSharedPreferences(PREFS,MODE_PRIVATE).edit().putBoolean("was_busy",false).putString("stage",stage).putString("detail",detail).putString("report",report==null?null:report.getPath()).apply();
                if(wake!=null&&wake.isHeld())wake.release();stopForeground(STOP_FOREGROUND_REMOVE);publish();stopSelf();
            });
        });
        return START_NOT_STICKY;
    }
    private Notification notification(){
        PendingIntent open=PendingIntent.getActivity(this,0,new Intent(this,PresentationActivity.class),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder b=new Notification.Builder(this,CHANNEL).setSmallIcon(android.R.drawable.ic_menu_view).setContentTitle("COH Client Test · "+stage).setContentText(detail).setContentIntent(open).setOngoing(busy).setOnlyAlertOnce(true);
        if(busy)b.addAction(new Notification.Action.Builder(null,"Stop",PendingIntent.getService(this,1,new Intent(this,PresentationService.class).setAction(STOP),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE)).build());
        return b.build();
    }
    private void notifyStatus(){if(busy)((NotificationManager)getSystemService(NOTIFICATION_SERVICE)).notify(NOTICE,notification());}
    @Override public void onDestroy(){destroyed=true;PresentationRuntime r=runtime;if(r!=null)r.requestStop();worker.shutdown();listeners.clear();try{unregisterReceiver(screenReceiver);}catch(Exception ignored){}if(wake!=null&&wake.isHeld())wake.release();super.onDestroy();}
}
