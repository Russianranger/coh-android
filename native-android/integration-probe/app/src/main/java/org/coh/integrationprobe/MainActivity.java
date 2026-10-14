package org.coh.integrationprobe;

import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.graphics.Color;
import android.graphics.Rect;
import android.hardware.input.InputManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.util.AtomicFile;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.Surface;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.view.View;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import org.coh.systemsprobe.InputAdapter;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.text.SimpleDateFormat;
import java.util.Arrays;
import java.util.Date;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** One isolated native probe: compressed decode, loopback transport and source scene look. */
public final class MainActivity extends Activity {
    static { System.loadLibrary("coh_integration_probe"); }
    private static native void nativeFocus(boolean focused);
    private static native void nativeKey(int key, boolean down);
    private static native void nativeAxes(float x,float y,float z,float rz);
    private static native void nativeTouch(int action,int id,float x,float y);
    private static native String nativeFrame(float seconds);
    private static native void nativeResetCamera();
    private static native String nativeChecks(byte[] ogg,byte[] reference);
    private static native String nativePlay(byte[] ogg,byte[] reference);
    private static native void nativeCancelAudio();
    private static native void nativeAudioForeground(boolean foreground);
    private static native boolean nativeAudioActive();
    private static native String nativeTransportWait(int timeoutMs);
    private static native void nativeTransportCancel();
    private static native void nativeTransportForeground(boolean foreground);
    private static native boolean nativeTransportActive();
    private static native long nativeWorldTicket();
    private static native String nativeWorld(Surface surface,byte[] world,byte[] reference,byte[] materials,long expectedTicket);
    private static native void nativeWorldCancel();
    private static native void nativeWorldForeground(boolean foreground);
    private static native boolean nativeWorldActive();
    private final Handler main=new Handler(Looper.getMainLooper());
    private final ExecutorService worker=Executors.newSingleThreadExecutor();
    private final ExecutorService graphics=Executors.newSingleThreadExecutor();
    private final ExecutorService network=Executors.newSingleThreadExecutor();
    private final JSONArray events=new JSONArray(),nativeRuns=new JSONArray(),audioRuns=new JSONArray(),transportRuns=new JSONArray(),worldRuns=new JSONArray();
    private JSONObject report,lastFrame=object(),fixture=object(),background=object();
    private AtomicFile reportFile;
    private InputAdapter adapter;
    private InputManager inputManager;
    private FrameLayout inputContainer;
    private SceneSurface inputView;
    private HorizontalScrollView controlScroll;
    private final Map<String,Button> measuredButtons=new LinkedHashMap<>();
    private TextView status,inputStatus,reportText;
    private byte[] ogg,audioReference,world,worldReference,materialReference,exportSnapshot;
    private volatile boolean active,destroyed,audioBusy,transportBusy,checksBusy,renderBusy;
    private boolean assetsReady,small,audibleConfirmed,homeRequested,homeReady,pendingForegroundChecks;
    private int failures,exportRequest=49,interactionMask;
    private volatile long generation,renderToken,foregroundEpoch;
    private long eventSequence,nativeSequence,audioSequence,transportSequence,worldSequence;
    private long currentAudioRun,currentTransportRun,lastTick,lastReportTick;
    private long settledFrames,changedPixels;
    private String loadFailure,pendingAction;

    private static JSONObject object(Object... pairs){JSONObject o=new JSONObject();try{for(int i=0;i<pairs.length;i+=2)o.put((String)pairs[i],pairs[i+1]);}catch(Exception e){throw new IllegalArgumentException(e);}return o;}
    private static String now(){return new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSXXX",Locale.US).format(new Date());}
    private int dp(int value){return Math.round(value*getResources().getDisplayMetrics().density);}
    private JSONObject event(String type,JSONObject detail){JSONObject e=object("sequence",++eventSequence,"type",type,"time",now(),"elapsed_ms",SystemClock.elapsedRealtime(),"generation",generation,"detail",detail);events.put(e);while(events.length()>400)events.remove(0);return e;}
    private static void append(JSONArray array,JSONObject value){array.put(value);while(array.length()>32)array.remove(0);}
    @Override public void onCreate(Bundle saved){
        super.onCreate(saved);reportFile=new AtomicFile(new File(getFilesDir(),"integration-probe-report.json"));
        boolean emulator=(Build.MODEL+" "+Build.HARDWARE).toLowerCase(Locale.US).matches(".*(emulator|sdk|ranchu|goldfish).*");
        JSONObject identity=object("package",getPackageName());
        try{PackageInfo info=getPackageManager().getPackageInfo(getPackageName(),0);identity.put("version_name",info.versionName).put("version_code",Build.VERSION.SDK_INT>=28?info.getLongVersionCode():info.versionCode);}catch(Exception e){identity=object("package",getPackageName(),"error",e.toString());}
        report=object("schema","coh-native-integration-probe-v2","phases",new JSONArray(Arrays.asList(13,14,15)),"started_at",now(),"session_id",Long.toHexString(System.currentTimeMillis())+"-"+android.os.Process.myPid(),
            "scope","Compressed authentic Ogg decoded on this device; local UDP only; authored Atlas bench rendered using accepted source camera/math and Android input. No game login, character movement or server interoperability.",
            "app",identity,"device",object("manufacturer",Build.MANUFACTURER,"model",Build.MODEL,"hardware",Build.HARDWARE,"sdk",Build.VERSION.SDK_INT,"abis",new JSONArray(Arrays.asList(Build.SUPPORTED_ABIS)),"emulator_detected",emulator),
            "events",events,"native_runs",nativeRuns,"audio_runs",audioRuns,"transport_runs",transportRuns,"world_runs",worldRuns);
        pendingAction=getIntent().getStringExtra("probe_action");
        adapter=new InputAdapter(new InputAdapter.Sink(){public void focus(boolean v){nativeFocus(v);}public void key(int k,boolean v){nativeKey(k,v);}public void axes(float x,float y,float z,float rz){nativeAxes(x,y,z,rz);}public void touch(int a,int id,float x,float y){nativeTouch(a,id,x,y);}});
        inputManager=(InputManager)getSystemService(INPUT_SERVICE);if(inputManager!=null)inputManager.registerInputDeviceListener(adapter,main);
        buildUi();event("activity_created",object());
        worker.execute(()->{try{
            JSONObject installedApk=installedApkIdentity();
            JSONObject audioMeta=new JSONObject(new String(readAsset("audio-fixture.json",256*1024),StandardCharsets.UTF_8));
            JSONObject worldMeta=new JSONObject(new String(readAsset("world-fixture.json",512*1024),StandardCharsets.UTF_8));
            if(!"coh-native-audio-fixture-v1".equals(audioMeta.getString("schema")))throw new IllegalArgumentException("Audio fixture contract mismatch");
            byte[] compressed=readAsset("headset.ogg",1024*1024),pcm=verifiedAsset("audio.bin",audioMeta.getJSONObject("audio"),1024*1024);
            JSONObject source=audioMeta.getJSONObject("source");
            if(compressed.length!=12930||!sha256(compressed).equals("82bec697f9e824d192cac90f32a01421e4a3875aada64fc709862bc4d3ae9198")||source.getInt("size")!=compressed.length||!source.getString("sha256").equals(sha256(compressed)))throw new IllegalArgumentException("Compressed authentic Ogg pin mismatch");
            JSONObject pins=worldMeta.getJSONObject("assets");byte[] w=verifiedAsset("world.bin",pins.getJSONObject("world.bin"),1024*1024),wr=verifiedAsset("world-reference.bin",pins.getJSONObject("world-reference.bin"),1024*1024),mr=verifiedAsset("material-reference.bin",pins.getJSONObject("material-reference.bin"),1024*1024);
            main.post(()->{if(destroyed)return;try{report.getJSONObject("app").put("installed_apk",installedApk);}catch(Exception e){throw new IllegalStateException(e);}ogg=compressed;audioReference=pcm;world=w;worldReference=wr;materialReference=mr;fixture=object("audio",audioMeta,"world",worldMeta);assetsReady=true;
                event("assets_verified",object("compressed_ogg_bytes",compressed.length,"compressed_ogg_sha256",sha256(compressed),"pcm_role","reference only, never played instead of decoder output"));runChecks("initial");startWorld("initial");runPending();});
        }catch(Exception e){main.post(()->{if(destroyed)return;loadFailure=e.toString();failures++;event("asset_error",object("error",loadFailure));refresh();});}});
    }
    private byte[] readAsset(String name,int limit)throws Exception{try(InputStream in=getAssets().open(name);ByteArrayOutputStream out=new ByteArrayOutputStream()){byte[] buffer=new byte[8192];int n;while((n=in.read(buffer))!=-1){if(out.size()+n>limit)throw new IllegalArgumentException("Asset exceeds bound");out.write(buffer,0,n);}return out.toByteArray();}}
    private JSONObject installedApkIdentity()throws Exception{MessageDigest digest=MessageDigest.getInstance("SHA-256");long count=0;try(InputStream in=new FileInputStream(getApplicationInfo().sourceDir)){byte[] buffer=new byte[8192];int n;while((n=in.read(buffer))!=-1){count+=n;if(count>32L*1024*1024)throw new IllegalArgumentException("Installed APK exceeds identity bound");digest.update(buffer,0,n);}}if(count<=0)throw new IllegalArgumentException("Empty installed APK");StringBuilder hex=new StringBuilder();for(byte b:digest.digest())hex.append(String.format(Locale.US,"%02x",b&255));return object("bytes",count,"sha256",hex.toString(),"scope","Observed installed base APK bytes, hashed on asset worker");}
    private byte[] verifiedAsset(String name,JSONObject pin,int limit)throws Exception{byte[] bytes=readAsset(name,limit);if(bytes.length!=pin.getInt("bytes")||!sha256(bytes).equals(pin.getString("sha256")))throw new IllegalArgumentException("Asset hash/length mismatch: "+name);return bytes;}
    private static String sha256(byte[] bytes){try{byte[] digest=MessageDigest.getInstance("SHA-256").digest(bytes);StringBuilder result=new StringBuilder();for(byte b:digest)result.append(String.format(Locale.US,"%02x",b&255));return result.toString();}catch(Exception e){throw new IllegalStateException(e);}}
    private void button(LinearLayout row,String label,String key,Runnable action){Button b=new Button(this);b.setText(label);b.setTextSize(11);b.setOnClickListener(v->action.run());row.addView(b,new LinearLayout.LayoutParams(-2,-2));measuredButtons.put(key,b);}
    private void buildUi(){
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setPadding(dp(7),dp(4),dp(7),dp(4));root.setBackgroundColor(Color.rgb(239,243,246));
        status=new TextView(this);status.setTextSize(14);status.setLines(3);root.addView(status);
        controlScroll=new HorizontalScrollView(this);LinearLayout row=new LinearLayout(this);
        button(row,"Run checks","run",()->{runChecks("manual");startWorld("manual");});button(row,"Play decoded sound","play",()->play("manual"));
        button(row,"Heard 3 sounds","audible_confirmation",()->{long id=-1;for(int i=0;i<audioRuns.length();i++){JSONObject r=audioRuns.optJSONObject(i);if(r.optBoolean("passed")&&!ReceiptRules.audioRunFailed(r))id=r.optLong("run_id");}if(id>=0&&!report.optJSONObject("device").optBoolean("emulator_detected")){audibleConfirmed=true;event("audible_confirmation",object("basis","user_button","audio_run_id",id));}refresh();});
        button(row,"Reset view","reset",this::resetView);button(row,"Resize","resize",this::resizeInput);button(row,"Recreate","recreate",this::recreateInput);button(row,"Home check","home",this::homeCheck);button(row,"Export report","export",this::exportReport);
        controlScroll.addView(row);root.addView(controlScroll,new LinearLayout.LayoutParams(-1,-2));
        TextView guide=new TextView(this);guide.setTextSize(11);guide.setText("Drag the bench view right, left, down and up; release and watch it stop. Try both sticks and A. Play decoded sound (three clips, quieter middle), resize and recreate. Home check: press Android Home as soon as READY appears; return and play once more. Export after INTEGRATION GATES PASSED. Reset view returns to the authored camera.");root.addView(guide);
        inputStatus=new TextView(this);inputStatus.setTextSize(11);root.addView(inputStatus);
        inputContainer=new FrameLayout(this);inputContainer.setBackgroundColor(Color.rgb(18,25,34));root.addView(inputContainer,new LinearLayout.LayoutParams(-1,0,3));createInputView();
        ScrollView scroll=new ScrollView(this);reportText=new TextView(this);reportText.setTextSize(9);reportText.setTextIsSelectable(true);scroll.addView(reportText);root.addView(scroll,new LinearLayout.LayoutParams(-1,0,2));setContentView(root);refresh();
    }
    private void createInputView(){++generation;inputView=new SceneSurface();FrameLayout.LayoutParams p=new FrameLayout.LayoutParams(-1,-1,android.view.Gravity.CENTER);if(small&&inputContainer.getWidth()>0){p.width=Math.max(32,inputContainer.getWidth()*3/4);p.height=Math.max(32,inputContainer.getHeight()*3/4);}inputContainer.addView(inputView,p);event("input_view_created",object("generation",generation));}
    private void resizeInput(){if(!active)return;small=!small;FrameLayout.LayoutParams p=(FrameLayout.LayoutParams)inputView.getLayoutParams();p.width=small?Math.max(32,inputContainer.getWidth()*3/4):-1;p.height=small?Math.max(32,inputContainer.getHeight()*3/4):-1;nativeWorldCancel();++renderToken;inputView.setLayoutParams(p);event("resize_requested",object("smaller",small));refresh();}
    private void recreateInput(){if(!active)return;event("view_recreation_requested",object("previous_generation",generation));nativeWorldCancel();++renderToken;adapter.clear();nativeFocus(true);inputContainer.removeView(inputView);createInputView();refresh();}
    private void resetView(){if(!active)return;nativeWorldCancel();++renderToken;adapter.clear();nativeFocus(true);nativeResetCamera();event("view_reset_requested",object());if(!renderBusy)startWorld("reset");refresh();}
    private final Runnable tick=new Runnable(){public void run(){if(!active||destroyed)return;long time=SystemClock.elapsedRealtime();float seconds=lastTick==0?0:Math.min(.05f,Math.max(0,(time-lastTick)/1000f));lastTick=time;try{lastFrame=new JSONObject(nativeFrame(seconds));}catch(Exception e){failures++;event("input_snapshot_error",object("error",e.toString()));}
        JSONArray pyr=lastFrame.optJSONArray("pyr");inputStatus.setText("Held "+lastFrame.optLong("held")+"   source yaw "+String.format(Locale.US,"%.3f",pyr==null?0:pyr.optDouble(1))+"   Look "+interactionMask+"/15   render "+(nativeWorldActive()?"active":"idle"));
        if(homeRequested){boolean ready=nativeAudioActive()&&nativeTransportActive();if(ready&&!homeReady){homeReady=true;event("home_check_ready",object("audio_run_id",currentAudioRun,"transport_run_id",currentTransportRun));refresh();}}
        if(pendingForegroundChecks&&!audioBusy&&!transportBusy&&!checksBusy){pendingForegroundChecks=false;runChecks("foreground_return");}
        if(time-lastReportTick>=200){lastReportTick=time;refresh();}main.postDelayed(this,16);}};
    private void runChecks(String reason){if(!active||destroyed||!assetsReady||checksBusy||audioBusy||transportBusy)return;checksBusy=true;final long id=++nativeSequence,began=eventSequence,gen=generation,epoch=foregroundEpoch;event("checks_requested",object("run_id",id,"reason",reason));worker.execute(()->{JSONObject r;try{r=new JSONObject(nativeChecks(ogg,audioReference));}catch(Exception e){r=object("passed",false,"error",e.toString());}final JSONObject value=r;main.post(()->{if(destroyed)return;checksBusy=false;decorate(value,id,reason,began,gen);boolean stale=epoch!=foregroundEpoch||!active,failed=ReceiptRules.nativeCheckFailed(value,stale);try{value.put("java_expected_cancel",!value.optBoolean("passed")&&!failed).put("foreground_epoch",epoch);}catch(Exception e){throw new IllegalStateException(e);}append(nativeRuns,value);if(failed)failures++;event("checks_complete",object("run_id",id,"passed",value.optBoolean("passed"),"expected_cancel",!value.optBoolean("passed")&&!failed));refresh();});});refresh();}
    private void decorate(JSONObject value,long id,String reason,long began,long gen){try{value.put("run_id",id).put("reason",reason).put("generation",gen).put("started_after_event",began).put("completed_at",now()).put("foreground_at_completion",active);}catch(Exception e){throw new IllegalStateException(e);}}
    private void play(String reason){if(!active||destroyed||!assetsReady||audioBusy||checksBusy)return;audioBusy=true;final long id=++audioSequence,gen=generation,began=eventSequence;currentAudioRun=id;event("audio_play_requested",object("run_id",id,"reason",reason));worker.execute(()->{JSONObject r;try{r=new JSONObject(nativePlay(ogg,audioReference));}catch(Exception e){r=object("passed",false,"error",e.toString());}final JSONObject value=r;main.post(()->{if(destroyed)return;audioBusy=false;decorate(value,id,reason,began,gen);append(audioRuns,value);if(ReceiptRules.audioRunFailed(value))failures++;event("audio_complete",object("run_id",id,"passed",value.optBoolean("passed"),"cancelled",value.optBoolean("cancelled"),"closed",value.optBoolean("closed")));refresh();});});refresh();}
    private void homeCheck(){if(!active||destroyed||!assetsReady||checksBusy||audioBusy||transportBusy)return;homeRequested=true;homeReady=false;transportBusy=true;final long id=++transportSequence,gen=generation,began=eventSequence;currentTransportRun=id;event("home_check_requested",object("transport_run_id",id));network.execute(()->{JSONObject r;try{r=new JSONObject(nativeTransportWait(5000));}catch(Exception e){r=object("passed",false,"error",e.toString());}final JSONObject value=r;main.post(()->{if(destroyed)return;transportBusy=false;decorate(value,id,"home_wait",began,gen);append(transportRuns,value);if(ReceiptRules.transportRunFailed(value))failures++;event("transport_wait_complete",object("run_id",id,"cancelled",value.optBoolean("cancelled"),"closed",value.optBoolean("closed")));if(active){homeRequested=false;homeReady=false;}refresh();});});play("home_check");refresh();}
    private void startWorld(String reason){if(!active||destroyed||!assetsReady||renderBusy||inputView==null||!inputView.ready||!inputView.getHolder().getSurface().isValid())return;
        renderBusy=true;final long id=++worldSequence,gen=generation,began=eventSequence,token=renderToken,ticket=nativeWorldTicket();final int width=inputView.getWidth(),height=inputView.getHeight();final Surface surface=inputView.getHolder().getSurface();event("world_render_requested",object("run_id",id,"reason",reason,"width",width,"height",height,"render_token",token,"native_ticket",ticket));
        graphics.execute(()->{JSONObject r;try{if(!active||destroyed||gen!=generation||token!=renderToken)r=object("engine_passed",false,"cancelled",true,"expected_cancel",true,"session_failure",false,"objects_released",true,"gl_errors",0,"started_native",false,"stage","Queued Java renderer cancelled before JNI");else r=new JSONObject(nativeWorld(surface,world,worldReference,materialReference,ticket));}catch(Exception e){r=object("engine_passed",false,"session_failure",true,"error",e.toString());}final JSONObject value=r;main.post(()->{if(destroyed)return;renderBusy=false;decorate(value,id,reason,began,gen);boolean obsolete=token!=renderToken||gen!=generation||!active||inputView.getWidth()!=width||inputView.getHeight()!=height;try{value.put("requested_width",width).put("requested_height",height).put("render_token",token).put("native_ticket",ticket).put("java_obsolete",obsolete);}catch(Exception e){throw new IllegalStateException(e);}append(worldRuns,value);
            boolean engine=ReceiptRules.worldEnginePassed(value);boolean cleanCancel=ReceiptRules.worldObsoleteHarmless(value,obsolete);
            if(!engine&&!cleanCancel){failures++;event("world_error",object("run_id",id,"report",value));}
            if(engine&&value.optLong("external_revision_changes")>0&&value.optLong("input_linked_changed_pixels")>0){interactionMask|=value.optInt("direction_mask");changedPixels+=value.optLong("input_linked_changed_pixels");}
            if(engine)settledFrames+=value.optLong("settled_frames");event("world_render_complete",object("run_id",id,"engine_passed",engine,"clean_obsolete_cancellation",cleanCancel,"direction_mask",value.optInt("direction_mask")));refresh();if(active&&(engine||cleanCancel))main.postDelayed(()->startWorld("bounded_preview_continuation"),200);});});refresh();}
    @Override public boolean dispatchKeyEvent(KeyEvent e){boolean used=adapter!=null&&adapter.dispatchKeyEvent(e);if(used)refresh();return used||super.dispatchKeyEvent(e);}
    @Override public boolean dispatchGenericMotionEvent(MotionEvent e){boolean used=adapter!=null&&adapter.dispatchGenericMotionEvent(e);if(used)refresh();return used||super.dispatchGenericMotionEvent(e);}
    @Override public void onWindowFocusChanged(boolean yes){super.onWindowFocusChanged(yes);if(adapter!=null){adapter.onWindowFocusChanged(yes&&active);event("window_focus_changed",object("focused",yes));refresh();}}
    @Override public void onResume(){super.onResume();active=true;nativeAudioForeground(true);nativeTransportForeground(true);nativeWorldForeground(true);nativeFocus(true);pendingForegroundChecks=assetsReady;lastTick=0;main.removeCallbacks(tick);main.post(tick);JSONObject e=event("activity_resumed",object());if(background.has("pause_sequence")&&!background.has("resume_sequence")){try{background.put("resume_sequence",e.optLong("sequence"));}catch(Exception x){throw new IllegalStateException(x);}pendingForegroundChecks=true;}
        homeRequested=false;homeReady=false;startWorld("foreground_return");runPending();refresh();}
    @Override public void onPause(){boolean audioStarted=nativeAudioActive(),transportStarted=nativeTransportActive();long audioId=currentAudioRun,transportId=currentTransportRun;active=false;++foregroundEpoch;main.removeCallbacks(tick);nativeAudioForeground(false);nativeTransportForeground(false);nativeWorldForeground(false);++renderToken;adapter.clear();nativeFocus(false);JSONObject clear;try{clear=new JSONObject(nativeFrame(0));}catch(Exception e){clear=object("error",e.toString());}
        JSONObject e=event("activity_paused",object("input_cleared",ReceiptRules.zeroInput(clear),"input_snapshot",clear,"audio_started_before_pause",audioStarted,"transport_started_before_pause",transportStarted,"interrupted_audio_run_id",audioId,"interrupted_transport_run_id",transportId));
        // A document picker or ordinary foreground UI must not replace a genuine Home witness.
        if(audioStarted&&transportStarted){background=object("pause_sequence",e.optLong("sequence"),"input_cleared",ReceiptRules.zeroInput(clear),"audio_started_before_pause",true,"transport_started_before_pause",true,"interrupted_audio_run_id",audioId,"interrupted_transport_run_id",transportId);}
        homeRequested=false;homeReady=false;refresh();super.onPause();}
    @Override public void onStop(){JSONObject e=event("activity_stopped",object());if(background.has("pause_sequence")&&!background.has("stop_sequence")&&!background.has("resume_sequence"))try{background.put("stop_sequence",e.optLong("sequence"));}catch(Exception x){throw new IllegalStateException(x);}refresh();super.onStop();}
    @Override public void onDestroy(){destroyed=true;active=false;nativeAudioForeground(false);nativeTransportForeground(false);nativeWorldForeground(false);nativeFocus(false);main.removeCallbacksAndMessages(null);if(inputManager!=null)inputManager.unregisterInputDeviceListener(adapter);worker.shutdown();graphics.shutdown();network.shutdown();super.onDestroy();}
    @Override public void onNewIntent(Intent intent){super.onNewIntent(intent);setIntent(intent);pendingAction=intent.getStringExtra("probe_action");runPending();}
    private void runPending(){if(!active||!assetsReady||pendingAction==null)return;String action=pendingAction;pendingAction=null;event("external_action",object("action",action));if("run".equals(action))runChecks("external");else if("resize".equals(action))resizeInput();else if("recreate".equals(action))recreateInput();else if("play".equals(action))play("external");else if("home".equals(action))homeCheck();else if("reset".equals(action))resetView();}
    private JSONObject adapterReport(){try{return adapter==null?object():adapter.report();}catch(Exception e){throw new IllegalStateException(e);}}
    private boolean externalInputPassed(){JSONObject e=adapterReport().optJSONObject("external_android");return e!=null&&e.optLong("touch_begin")>0&&e.optLong("touch_move")>0&&e.optLong("touch_end")>0&&e.optInt("touch_motion_directions")==15&&e.optLong("key_down")>0&&e.optLong("key_up")>0;}
    private boolean currentWorldPassed(){if(inputView==null)return false;for(int i=worldRuns.length()-1;i>=0;i--){JSONObject r=worldRuns.optJSONObject(i);if(ReceiptRules.worldCurrentPassed(r,generation,inputView.getWidth(),inputView.getHeight(),renderToken))return true;}return false;}
    private boolean preBackground(){Set<Long> generations=new HashSet<>();Set<String> sizes=new HashSet<>();boolean nativePass=false,audioPass=false;for(int i=0;i<worldRuns.length();i++){JSONObject r=worldRuns.optJSONObject(i);if(ReceiptRules.worldEnginePassed(r)){generations.add(r.optLong("generation"));sizes.add(r.optInt("width")+"x"+r.optInt("height"));}}
        for(int i=0;i<nativeRuns.length();i++){JSONObject r=nativeRuns.optJSONObject(i);nativePass|=ReceiptRules.nativeCheckPassed(r)&&r.optBoolean("foreground_at_completion");}
        for(int i=0;i<audioRuns.length();i++){JSONObject r=audioRuns.optJSONObject(i);audioPass|=r.optBoolean("passed")&&!ReceiptRules.audioRunFailed(r);}
        return active&&assetsReady&&failures==0&&currentWorldPassed()&&generations.size()>=2&&sizes.size()>=2&&nativePass&&audioPass&&interactionMask==15&&settledFrames>0&&changedPixels>0&&externalInputPassed();}
    private boolean backgroundPassed(){long pause=background.optLong("pause_sequence",-1),stop=background.optLong("stop_sequence",-1),resume=background.optLong("resume_sequence",-1);if(!(pause>0&&stop>pause&&resume>stop&&background.optBoolean("input_cleared")&&background.optBoolean("audio_started_before_pause")&&background.optBoolean("transport_started_before_pause")))return false;
        boolean audioCancel=false,transportCancel=false,reopen=false,check=false,render=false;for(int i=0;i<audioRuns.length();i++){JSONObject r=audioRuns.optJSONObject(i);audioCancel|=ReceiptRules.audioInterrupted(r,background.optLong("interrupted_audio_run_id",-1),pause);reopen|=r.optBoolean("passed")&&!ReceiptRules.audioRunFailed(r)&&r.optBoolean("foreground_at_completion")&&r.optLong("started_after_event")>=resume;}
        for(int i=0;i<transportRuns.length();i++)transportCancel|=ReceiptRules.transportInterrupted(transportRuns.optJSONObject(i),background.optLong("interrupted_transport_run_id",-1),pause);
        for(int i=0;i<nativeRuns.length();i++){JSONObject r=nativeRuns.optJSONObject(i);check|=ReceiptRules.nativeCheckPassed(r)&&r.optBoolean("foreground_at_completion")&&r.optLong("started_after_event")>=resume;}
        for(int i=0;i<worldRuns.length();i++){JSONObject r=worldRuns.optJSONObject(i);render|=ReceiptRules.worldEnginePassed(r)&&r.optBoolean("foreground_at_completion")&&r.optLong("started_after_event")>=resume&&r.optLong("generation")==generation;}
        return audioCancel&&transportCancel&&reopen&&check&&render;
    }
    private JSONObject visibleScreenBounds(View view){Rect rect=new Rect();boolean visible=view!=null&&view.getGlobalVisibleRect(rect)&&rect.width()>0&&rect.height()>0;if(!visible)return object("left",0,"top",0,"width",0,"height",0,"visible",false,"fully_visible",false,"view_width",view==null?0:view.getWidth(),"view_height",view==null?0:view.getHeight());int[] origin=new int[2];view.getRootView().getLocationOnScreen(origin);rect.offset(origin[0],origin[1]);return object("left",rect.left,"top",rect.top,"width",rect.width(),"height",rect.height(),"visible",true,"fully_visible",rect.width()==view.getWidth()&&rect.height()==view.getHeight(),"view_width",view.getWidth(),"view_height",view.getHeight());}
    private JSONObject measuredControls(){JSONObject result=object();try{for(Map.Entry<String,Button> entry:measuredButtons.entrySet())result.put(entry.getKey(),visibleScreenBounds(entry.getValue()));}catch(Exception e){throw new IllegalStateException(e);}return result;}
    private JSONObject measuredControlRow(){JSONObject result=visibleScreenBounds(controlScroll);try{if(controlScroll!=null)result.put("scroll_x",controlScroll.getScrollX()).put("content_width",controlScroll.getChildCount()>0?controlScroll.getChildAt(0).getWidth():0);}catch(Exception e){throw new IllegalStateException(e);}return result;}
    private void refresh(){if(report==null||status==null||destroyed)return;try{boolean pre=preBackground(),home=backgroundPassed(),qualified=pre&&home;JSONObject external=adapterReport().optJSONObject("external_android");boolean controller=external!=null&&external.optLong("controller_events")>0&&external.optInt("left_axis_directions")==15&&external.optInt("right_axis_directions")==15;
        boolean decode=false,transport=false;for(int i=0;i<nativeRuns.length();i++){JSONObject r=nativeRuns.optJSONObject(i);decode|=ReceiptRules.decodePassed(r.optJSONObject("decode"));transport|=!ReceiptRules.transportRunFailed(r.optJSONObject("transport"))&&r.optJSONObject("transport").optBoolean("passed");}
        report.put("updated_at",now()).put("assets_verified",assetsReady).put("asset_metadata",fixture).put("load_failure",loadFailure==null?JSONObject.NULL:loadFailure).put("input_adapter",adapterReport()).put("input_snapshot",lastFrame).put("session_failures",failures).put("generation",generation).put("render_token",renderToken)
            .put("audio_busy",audioBusy).put("backend_audio_active",nativeAudioActive()).put("transport_busy",transportBusy).put("backend_transport_active",nativeTransportActive()).put("checks_busy",checksBusy).put("render_busy",renderBusy).put("backend_world_active",nativeWorldActive()).put("home_check_ready",homeRequested&&nativeAudioActive()&&nativeTransportActive())
            .put("background_return",background).put("pre_background_checks_passed",pre).put("background_return_gate_passed",home).put("android_input_transport_passed",externalInputPassed()).put("interactive_direction_mask",interactionMask).put("interactive_settled_frames",settledFrames).put("input_linked_changed_pixels",changedPixels).put("current_world_gate_passed",currentWorldPassed())
            .put("compressed_decode_gate_passed",decode&&failures==0).put("loopback_transport_gate_passed",transport&&home&&failures==0).put("interactive_world_gate_passed",pre&&home).put("qualification_passed",qualified)
            .put("controller_axis_coverage_passed",controller&&!report.getJSONObject("device").optBoolean("emulator_detected")).put("device_audible_confirmation_passed",audibleConfirmed).put("physical_confirmation_scope","Engine and ADB callbacks do not prove physical speakers or sticks; those observations are recorded separately")
            .put("input_area",inputView==null?object():inputView.area()).put("controls",measuredControls()).put("control_row",measuredControlRow());
        String next=homeRequested?(nativeAudioActive()&&nativeTransportActive()?"READY — press Android Home now":"Preparing Home check; wait for READY"):
            qualified?"Engine checks complete; confirm sticks and three audible clips":!pre?"Drag all four ways; play, resize and recreate":!home?"Home check, return, then Play decoded sound":"Checks complete";
        status.setText((qualified?"INTEGRATION GATES PASSED":"QUALIFICATION PENDING")+" — Gates 13–15\n"+next+"\nLook: "+interactionMask+"/15 | Sticks: "+(controller?"complete":"pending")+" | Heard: "+(audibleConfirmed?"confirmed":"pending")+" | Failures: "+failures);status.setTextColor(qualified?Color.rgb(0,104,42):failures>0?Color.rgb(150,20,20):Color.DKGRAY);
        String text=report.toString(2);reportText.setText(text);writeReport(text.getBytes(StandardCharsets.UTF_8));
    }catch(Exception e){status.setText("REPORT ERROR — "+e);status.setTextColor(Color.RED);}}
    private void writeReport(byte[] bytes)throws Exception{FileOutputStream out=null;try{out=reportFile.startWrite();out.write(bytes);reportFile.finishWrite(out);}catch(Exception e){if(out!=null)reportFile.failWrite(out);throw e;}}
    private void exportReport(){try{refresh();exportSnapshot=report.toString(2).getBytes(StandardCharsets.UTF_8);event("export_snapshot_created",object("bytes",exportSnapshot.length,"sha256",sha256(exportSnapshot),"qualification_passed",report.optBoolean("qualification_passed")));Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT);intent.addCategory(Intent.CATEGORY_OPENABLE);intent.setType("application/json");intent.putExtra(Intent.EXTRA_TITLE,"COH-NativeIntegration-"+new SimpleDateFormat("yyyyMMdd-HHmmss",Locale.US).format(new Date())+".json");startActivityForResult(intent,exportRequest);}catch(Exception e){event("export_error",object("error",e.toString()));refresh();}}
    @Override protected void onActivityResult(int request,int result,Intent data){super.onActivityResult(request,result,data);if(request!=exportRequest)return;if(result==RESULT_OK&&data!=null&&data.getData()!=null&&exportSnapshot!=null)try(java.io.OutputStream out=getContentResolver().openOutputStream(data.getData())){if(out==null)throw new IllegalStateException("No export stream");out.write(exportSnapshot);event("export_complete",object("bytes",exportSnapshot.length));}catch(Exception e){event("export_error",object("error",e.toString()));}exportSnapshot=null;refresh();}
    private final class SceneSurface extends SurfaceView implements SurfaceHolder.Callback {
        boolean ready;
        SceneSurface(){super(MainActivity.this);setFocusable(true);setFocusableInTouchMode(true);getHolder().addCallback(this);}
        @Override public boolean onTouchEvent(MotionEvent e){boolean used=adapter.dispatchTouchEvent(e,getWidth(),getHeight());if(used){requestFocus();refresh();}return used;}
        public void surfaceCreated(SurfaceHolder holder){ready=true;event("surface_created",object());main.post(()->startWorld("surface_created"));}
        public void surfaceChanged(SurfaceHolder holder,int format,int w,int h){ready=true;nativeWorldCancel();++renderToken;event("surface_changed",object("width",w,"height",h,"format",format));main.post(()->startWorld("surface_changed"));}
        public void surfaceDestroyed(SurfaceHolder holder){ready=false;nativeWorldCancel();++renderToken;event("surface_destroyed",object());}
        JSONObject area(){int[] location=new int[2];getLocationOnScreen(location);return object("left",location[0],"top",location[1],"width",getWidth(),"height",getHeight(),"surface_ready",ready);}
    }
}
