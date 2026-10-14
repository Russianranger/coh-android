package org.coh.systemsprobe;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Rect;
import android.hardware.input.InputManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.util.AtomicFile;
import android.view.InputDevice;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.HashSet;
import java.util.Locale;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Three bounded native diagnostics; no game, network, or background playback. */
public final class MainActivity extends Activity {
    static { System.loadLibrary("coh_systems_probe"); }
    private static native void nativeFocus(boolean focused);
    private static native void nativeKey(int key, boolean down);
    private static native void nativeAxes(float x, float y, float z, float rz);
    private static native void nativeTouch(int action, int id, float x, float y);
    private static native String nativeFrame(float seconds);
    private static native String nativeChecks(byte[] blob);
    private static native String nativePlay(byte[] blob);
    private static native void nativeCancelAudio();
    private static native void nativeAudioForeground(boolean foreground);
    private static native boolean nativeAudioActive();
    private final Handler main = new Handler(Looper.getMainLooper());
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final JSONArray events = new JSONArray(), nativeRuns = new JSONArray(), audioRuns = new JSONArray();
    private JSONObject report, lastFrame = object(), fixture = object(), background = object();
    private AtomicFile reportFile;
    private InputAdapter adapter;
    private InputManager inputManager;
    private FrameLayout inputContainer;
    private InputCanvas inputView;
    private HorizontalScrollView controlScroll;
    private final Map<String,Button> measuredButtons=new LinkedHashMap<>();
    private TextView status, inputStatus, reportText;
    private byte[] audio, exportSnapshot;
    private volatile boolean active, destroyed, audioBusy;
    private boolean assetsReady, small, autoSmoke, syntheticPassed, audibleConfirmed, smokeCompleted;
    private long generation, eventSequence, nativeSequence, audioSequence, lastTick, lastReportTick, currentAudioRun;
    private int smokeStage, failures, exportRequest = 49;
    private String pendingAction;
    private String loadFailure;

    private static JSONObject object(Object... pairs) {
        JSONObject o = new JSONObject();
        try { for (int i=0; i<pairs.length; i+=2) o.put((String)pairs[i],pairs[i+1]); }
        catch (Exception e) { throw new IllegalArgumentException(e); }
        return o;
    }
    private static String now() {
        return new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSXXX",Locale.US).format(new Date());
    }
    private int dp(int x) { return Math.round(x*getResources().getDisplayMetrics().density); }
    private JSONObject event(String type, JSONObject detail) {
        JSONObject e=object("sequence",++eventSequence,"type",type,"time",now(),"elapsed_ms",SystemClock.elapsedRealtime(),"generation",generation,"detail",detail);
        events.put(e);while(events.length()>400)events.remove(0);return e;
    }
    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        reportFile=new AtomicFile(new File(getFilesDir(),"systems-probe-report.json"));
        boolean emulator=(Build.MODEL+" "+Build.HARDWARE).toLowerCase(Locale.US).matches(".*(emulator|sdk|ranchu|goldfish).*");
        report=object("schema","coh-native-systems-probe-v1","started_at",now(),"session_id",Long.toHexString(System.currentTimeMillis())+"-"+android.os.Process.myPid(),
            "scope","native source input, authentic PCM AAudio sink, offline legacy packet framing; no gameplay or network",
            "device",object("manufacturer",Build.MANUFACTURER,"model",Build.MODEL,"hardware",Build.HARDWARE,
                "sdk",Build.VERSION.SDK_INT,"abis",new JSONArray(java.util.Arrays.asList(Build.SUPPORTED_ABIS)),"emulator_detected",emulator),
            "events",events,"native_runs",nativeRuns,"audio_runs",audioRuns);
        autoSmoke=getIntent().getBooleanExtra("autoSmoke",false);
        pendingAction=getIntent().getStringExtra("probe_action");
        adapter=new InputAdapter(new InputAdapter.Sink() {
            public void focus(boolean yes) { nativeFocus(yes); }
            public void key(int key, boolean down) { nativeKey(key,down); }
            public void axes(float x,float y,float z,float rz) { nativeAxes(x,y,z,rz); }
            public void touch(int action,int id,float x,float y) { nativeTouch(action,id,x,y); }
        });
        inputManager=(InputManager)getSystemService(INPUT_SERVICE);
        if(inputManager!=null) inputManager.registerInputDeviceListener(adapter,main);
        buildUi();event("activity_created",object("auto_smoke",autoSmoke));
        worker.execute(() -> {
            try {
                JSONObject meta=new JSONObject(new String(readAsset("audio-fixture.json",256*1024),StandardCharsets.UTF_8));
                JSONObject pin=meta.getJSONObject("audio");
                if(!"coh-native-audio-fixture-v1".equals(meta.getString("schema")) || !"audio.bin".equals(pin.getString("file")))
                    throw new IllegalArgumentException("Unexpected audio fixture contract");
                byte[] bytes=readAsset("audio.bin",1024*1024);
                if(bytes.length!=pin.getInt("bytes") || !sha256(bytes).equals(pin.getString("sha256")))
                    throw new IllegalArgumentException("Audio asset hash or length mismatch");
                main.post(() -> { if(destroyed)return;audio=bytes;fixture=meta;assetsReady=true;
                    event("asset_verified",object("file","audio.bin","bytes",bytes.length,"sha256",sha256(bytes)));
                    runChecks("initial");runPending(); });
            } catch(Exception e) { main.post(() -> { if(destroyed)return;loadFailure=e.toString();failures++;
                event("asset_error",object("error",loadFailure));refresh(); }); }
        });
    }
    private byte[] readAsset(String name,int limit) throws Exception {
        try(InputStream in=getAssets().open(name);ByteArrayOutputStream out=new ByteArrayOutputStream()) {
            byte[] buffer=new byte[8192];int n;while((n=in.read(buffer))!=-1){if(out.size()+n>limit)throw new IllegalArgumentException("Asset exceeds bound");out.write(buffer,0,n);}
            return out.toByteArray();
        }
    }
    private static String sha256(byte[] bytes) {
        try { byte[] digest=MessageDigest.getInstance("SHA-256").digest(bytes);StringBuilder s=new StringBuilder();
            for(byte b:digest)s.append(String.format(Locale.US,"%02x",b&255));return s.toString();
        } catch(Exception e) {throw new IllegalStateException(e);}
    }
    private void button(LinearLayout row,String label,Runnable action) {
        Button b=new Button(this);b.setText(label);b.setTextSize(12);b.setOnClickListener(v->action.run());row.addView(b,new LinearLayout.LayoutParams(-2,-2));
        String key="Run checks".equals(label)?"run":"Play sound".equals(label)?"play":"Stop sound".equals(label)?"stop":
            "Export report".equals(label)?"export":"Heard 3 sounds".equals(label)?"audible_confirmation":label.toLowerCase(Locale.US);
        measuredButtons.put(key,b);
    }
    private void buildUi() {
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setPadding(dp(8),dp(5),dp(8),dp(5));
        root.setBackgroundColor(Color.rgb(239,243,246));status=new TextView(this);status.setTextSize(15);status.setLines(3);root.addView(status);
        HorizontalScrollView horizontal=new HorizontalScrollView(this);controlScroll=horizontal;LinearLayout row=new LinearLayout(this);
        button(row,"Run checks",()->runChecks("manual"));button(row,"Play sound",()->play("manual"));
        button(row,"Stop sound",()->stopAudio("manual"));button(row,"Heard 3 sounds",()->{
            long successful=-1;for(int i=0;i<audioRuns.length();i++)if(audioRuns.optJSONObject(i).optBoolean("passed"))successful=audioRuns.optJSONObject(i).optLong("run_id");
            if(successful>=0&&!report.optJSONObject("device").optBoolean("emulator_detected")){audibleConfirmed=true;event("audible_confirmation",object("basis","user_button","audio_run_id",successful));}refresh();});
        button(row,"Resize",this::resizeInput);button(row,"Recreate",this::recreateInput);button(row,"Export report",this::exportReport);
        horizontal.addView(row);root.addView(horizontal,new LinearLayout.LayoutParams(-1,-2));
        TextView guide=new TextView(this);guide.setTextSize(12);
        guide.setText("Drag the arrow and press/release a controller button. Try both sticks in all four directions. Play sound: listen for three sounds, quieter in the middle. Resize, recreate, then start sound and press Home while it plays. Return, play once more, and export after SYSTEM GATES PASSED. Sound confirmation and controller stick coverage are recorded separately.");root.addView(guide);
        inputStatus=new TextView(this);inputStatus.setTextSize(12);root.addView(inputStatus);
        inputContainer=new FrameLayout(this);inputContainer.setBackgroundColor(Color.rgb(20,27,34));root.addView(inputContainer,new LinearLayout.LayoutParams(-1,0,1));
        createInputView();ScrollView scroll=new ScrollView(this);reportText=new TextView(this);reportText.setTextSize(10);reportText.setTextIsSelectable(true);scroll.addView(reportText);
        root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));setContentView(root);refresh();
    }
    private void createInputView() {
        ++generation;inputView=new InputCanvas();FrameLayout.LayoutParams p=new FrameLayout.LayoutParams(-1,-1,android.view.Gravity.CENTER);
        if(small && inputContainer.getWidth()>0){p.width=inputContainer.getWidth()*3/4;p.height=inputContainer.getHeight()*3/4;}
        inputContainer.addView(inputView,p);event("input_view_created",object("generation",generation));
    }
    private void resizeInput() {
        if(!active)return;small=!small;FrameLayout.LayoutParams p=(FrameLayout.LayoutParams)inputView.getLayoutParams();
        p.width=small?Math.max(32,inputContainer.getWidth()*3/4):-1;p.height=small?Math.max(32,inputContainer.getHeight()*3/4):-1;
        inputView.setLayoutParams(p);event("resize_requested",object("smaller",small));
    }
    private void recreateInput() {
        if(!active)return;event("view_recreation_requested",object("previous_generation",generation));
        adapter.clear();nativeFocus(true);inputContainer.removeView(inputView);event("input_view_destroyed",object());createInputView();
    }
    private final Runnable tick=new Runnable() { public void run() {
        if(!active||destroyed)return;long time=SystemClock.elapsedRealtime();float elapsed=lastTick==0?0f:Math.min(.05f,Math.max(0f,(time-lastTick)/1000f));lastTick=time;
        try {lastFrame=new JSONObject(nativeFrame(elapsed));}catch(Exception e){failures++;}
        JSONObject external=adapterReport().optJSONObject("external_android");
        inputStatus.setText("Held: "+lastFrame.optLong("held")+"   yaw: "+String.format(Locale.US,"%.3f",lastFrame.optJSONArray("pyr")==null?0:lastFrame.optJSONArray("pyr").optDouble(1))+
            "   Android key / touch moves: "+(external==null?0:external.optInt("key_down"))+" / "+(external==null?0:external.optInt("touch_move")));
        inputView.invalidate();main.postDelayed(this,16);
        if(time-lastReportTick>=500){lastReportTick=time;refresh();}
    }};
    private void runChecks(String reason) {
        if(!active||destroyed||!assetsReady||inputView.getWidth()<1)return;
        if(!syntheticPassed) testInputDispatch();
        final long gen=generation, id=++nativeSequence;final int width=inputView.getWidth(),height=inputView.getHeight();
        final long began=eventSequence;worker.execute(()->{
            JSONObject r;try{r=new JSONObject(nativeChecks(audio));}catch(Exception e){r=object("passed",false,"error",e.toString());}
            final JSONObject value=r;main.post(()->{if(destroyed)return;try{
                value.put("run_id",id).put("reason",reason).put("generation",gen).put("width",width).put("height",height)
                    .put("started_after_event",began).put("completed_at",now()).put("foreground_at_completion",active);
            }catch(Exception e){throw new IllegalStateException(e);}nativeRuns.put(value);while(nativeRuns.length()>32)nativeRuns.remove(0);
                if(!value.optBoolean("passed"))failures++;event("checks_complete",object("run_id",id,"passed",value.optBoolean("passed")));
                refresh();if(autoSmoke&&active&&gen==generation)advanceSmoke();
            });
        });refresh();
    }
    private void play(String reason) {
        if(!active||destroyed||!assetsReady||audioBusy)return;
        audioBusy=true;final long id=++audioSequence, gen=generation, began=eventSequence;currentAudioRun=id;
        event("audio_play_requested",object("run_id",id,"reason",reason));refresh();
        worker.execute(()->{
            if(!active||destroyed){main.post(()->{audioBusy=false;refresh();});return;}
            JSONObject r;try{r=new JSONObject(nativePlay(audio));}catch(Exception e){r=object("passed",false,"result",-99,"error",e.toString());}
            final JSONObject value=r;main.post(()->{if(destroyed)return;audioBusy=false;
                try{value.put("run_id",id).put("reason",reason).put("generation",gen).put("started_after_event",began)
                    .put("completed_at",now()).put("foreground_at_completion",active);}catch(Exception e){throw new IllegalStateException(e);}
                audioRuns.put(value);while(audioRuns.length()>32)audioRuns.remove(0);if(audioRunFailed(value))failures++;
                event("audio_complete",object("run_id",id,"passed",value.optBoolean("passed"),"cancelled",value.optBoolean("cancelled"),"closed",value.optBoolean("closed")));
                refresh();if(autoSmoke&&active)advanceSmoke();
            });
        });
    }
    private void stopAudio(String reason) {nativeCancelAudio();event("audio_cancel_requested",object("reason",reason,"active_backend",nativeAudioActive()));refresh();}
    private static boolean audioRunFailed(JSONObject run) {
        if(run==null||!(run.opt("passed") instanceof Boolean)||!(run.opt("cancelled") instanceof Boolean)
            ||!(run.opt("result") instanceof Number)||!(run.opt("backend_errors") instanceof Number))return true;
        if(((Number)run.opt("backend_errors")).doubleValue()!=0)return true;
        double result=((Number)run.opt("result")).doubleValue();
        // A cancel may arrive after the last frame is consumed, during clean
        // stop/close. That late OK result is harmless but cannot prove Home
        // interruption: backgroundPassed still requires native CANCELLED (1).
        boolean lateCancellation=!run.optBoolean("passed")&&run.optBoolean("cancelled")&&result==0
            &&run.opt("completed_clips") instanceof Number&&((Number)run.opt("completed_clips")).doubleValue()==3
            &&run.opt("requested_clips") instanceof Number&&((Number)run.opt("requested_clips")).doubleValue()==3
            &&Boolean.TRUE.equals(run.opt("opened"))&&Boolean.TRUE.equals(run.opt("started"))
            &&Boolean.TRUE.equals(run.opt("stopped"))&&Boolean.TRUE.equals(run.opt("closed"));
        // A later successful run cannot erase actual backend errors.
        return !(run.optBoolean("passed")&&!run.optBoolean("cancelled")&&result==0
            ||!run.optBoolean("passed")&&run.optBoolean("cancelled")&&result==1||lateCancellation);
    }
    private void advanceSmoke() {
        if(!autoSmoke||!active||audioBusy)return;
        if(smokeStage==0){smokeStage=1;play("autoSmoke_initial");}
        else if(smokeStage==1){smokeStage=2;resizeInput();}
        else if(smokeStage==2){smokeStage=3;recreateInput();}
        else if(smokeStage==3&&!smokeCompleted&&preBackground()){
            smokeCompleted=true;event("auto_smoke_completed",object("stage",3,"scope","source checks, bounded AAudio playback and input view resizing/recreation; Home return pending"));}
        refresh();
    }
    private static boolean zeroInput(JSONObject o) {
        JSONArray axes=o.optJSONArray("axes");if(axes==null||axes.length()!=4)return false;
        for(int i=0;i<4;i++)if(axes.optDouble(i,Double.NaN)!=0)return false;
        return o.optInt("result")==1 && o.optLong("held")==0 && o.optLong("pressed")==0 && o.optLong("released")==0 && o.optInt("delta_x") ==0 && o.optInt("delta_y")==0;
    }
    private void testInputDispatch() {
        if(!active)return;adapter.setSynthetic(true);boolean pass=false;
        try {
            adapter.clear();adapter.onWindowFocusChanged(true);nativeFocus(true);long t=SystemClock.uptimeMillis();
            KeyEvent down=new KeyEvent(t,t,KeyEvent.ACTION_DOWN,KeyEvent.KEYCODE_BUTTON_A,0,0,-1,0,0,InputDevice.SOURCE_GAMEPAD);
            boolean accepted=adapter.dispatchKeyEvent(down);
            MotionEvent.PointerProperties pp=new MotionEvent.PointerProperties();pp.id=0;pp.toolType=MotionEvent.TOOL_TYPE_UNKNOWN;
            MotionEvent.PointerCoords pc=new MotionEvent.PointerCoords();pc.setAxisValue(MotionEvent.AXIS_X,.5f);pc.setAxisValue(MotionEvent.AXIS_Y,-.5f);
            pc.setAxisValue(MotionEvent.AXIS_Z,.6f);pc.setAxisValue(MotionEvent.AXIS_RZ,-.4f);
            MotionEvent axes=MotionEvent.obtain(t,t,MotionEvent.ACTION_MOVE,1,new MotionEvent.PointerProperties[]{pp},new MotionEvent.PointerCoords[]{pc},0,0,1,1,-1,0,InputDevice.SOURCE_JOYSTICK,0);
            accepted&=adapter.dispatchGenericMotionEvent(axes);axes.recycle();
            MotionEvent begin=MotionEvent.obtain(t,t,MotionEvent.ACTION_DOWN,10,10,0);
            MotionEvent move=MotionEvent.obtain(t,t+1,MotionEvent.ACTION_MOVE,40,30,0);
            begin.setSource(InputDevice.SOURCE_TOUCHSCREEN);move.setSource(InputDevice.SOURCE_TOUCHSCREEN);
            accepted&=adapter.dispatchTouchEvent(begin,100,100);accepted&=adapter.dispatchTouchEvent(move,100,100);begin.recycle();move.recycle();
            JSONObject held=new JSONObject(nativeFrame(.016f));adapter.clear();nativeFocus(true);
            JSONObject clear=new JSONObject(nativeFrame(0f));pass=accepted&&held.optLong("held")!=0&&zeroInput(clear);
            event("synthetic_dispatch_checked",object("passed",pass,"held_sample",held,"cleared_sample",clear));
        } catch(Exception e) {event("synthetic_dispatch_checked",object("passed",false,"error",e.toString()));}
        finally{adapter.clear();adapter.onWindowFocusChanged(active&&hasWindowFocus());adapter.setSynthetic(false);}
        syntheticPassed=pass;if(!pass)failures++;refresh();
    }
    @Override public boolean dispatchKeyEvent(KeyEvent event) {
        boolean used=adapter!=null&&adapter.dispatchKeyEvent(event);if(used)refresh();return used||super.dispatchKeyEvent(event);
    }
    @Override public boolean dispatchGenericMotionEvent(MotionEvent event) {
        boolean used=adapter!=null&&adapter.dispatchGenericMotionEvent(event);if(used)refresh();return used||super.dispatchGenericMotionEvent(event);
    }
    @Override public void onWindowFocusChanged(boolean yes) {
        super.onWindowFocusChanged(yes);if(adapter==null)return;adapter.onWindowFocusChanged(yes&&active);
        event("window_focus_changed",object("focused",yes));refresh();
    }
    @Override public void onResume() {
        super.onResume();active=true;nativeAudioForeground(true);nativeFocus(true);lastTick=0;main.removeCallbacks(tick);main.post(tick);
        JSONObject e=event("activity_resumed",object());
        if(background.has("pause_sequence")){try{background.put("resume_sequence",e.getLong("sequence"));}catch(Exception x){throw new IllegalStateException(x);}
            runChecks("foreground_return");if(autoSmoke)play("autoSmoke_foreground_reopen");}
        runPending();refresh();
    }
    @Override public void onPause() {
        boolean startedAudio=nativeAudioActive();long interruptedAudio=currentAudioRun;
        active=false;main.removeCallbacks(tick);nativeAudioForeground(false);adapter.clear();nativeFocus(false);
        JSONObject clear;try{clear=new JSONObject(nativeFrame(0f));}catch(Exception e){clear=object("error",e.toString());}
        boolean playing=audioBusy||startedAudio;JSONObject e=event("activity_paused",object("input_cleared",zeroInput(clear),"input_snapshot",clear,
            "audio_active_or_pending",playing,"audio_started_before_pause",startedAudio,"interrupted_audio_run_id",interruptedAudio));
        background=object("pause_sequence",e.optLong("sequence"),"input_cleared",zeroInput(clear),"audio_was_active_or_pending",playing,
            "audio_started_before_pause",startedAudio,"interrupted_audio_run_id",interruptedAudio);
        refresh();super.onPause();
    }
    @Override public void onStop() {
        JSONObject e=event("activity_stopped",object());if(background.has("pause_sequence"))try{background.put("stop_sequence",e.getLong("sequence"));}catch(Exception x){throw new IllegalStateException(x);}
        refresh();super.onStop();
    }
    @Override public void onDestroy() {
        destroyed=true;active=false;nativeAudioForeground(false);nativeFocus(false);main.removeCallbacksAndMessages(null);
        if(inputManager!=null)inputManager.unregisterInputDeviceListener(adapter);worker.shutdown();super.onDestroy();
    }
    @Override public void onNewIntent(Intent intent) {
        super.onNewIntent(intent);setIntent(intent);pendingAction=intent.getStringExtra("probe_action");runPending();
    }
    private void runPending() {
        if(!active||!assetsReady||pendingAction==null)return;String action=pendingAction;pendingAction=null;
        event("external_action",object("action",action));
        if("run".equals(action))runChecks("external");else if("resize".equals(action))resizeInput();else if("recreate".equals(action))recreateInput();
        else if("play".equals(action))play("external");else if("stop".equals(action))stopAudio("external");else if("input-test".equals(action))testInputDispatch();
        else if("cancel-input".equals(action)){adapter.setSynthetic(true);MotionEvent cancel=MotionEvent.obtain(SystemClock.uptimeMillis(),SystemClock.uptimeMillis(),MotionEvent.ACTION_CANCEL,0,0,0);
            cancel.setSource(InputDevice.SOURCE_TOUCHSCREEN);
            adapter.dispatchTouchEvent(cancel,Math.max(1,inputView.getWidth()),Math.max(1,inputView.getHeight()));cancel.recycle();adapter.setSynthetic(false);
            event("synthetic_input_cancel",object());refresh();}
    }
    private boolean preBackground() {
        Set<Long> generations=new HashSet<>();Set<String> sizes=new HashSet<>();int nativeCount=0,audioCount=0;boolean current=false;
        for(int i=0;i<nativeRuns.length();i++){JSONObject r=nativeRuns.optJSONObject(i);if(r!=null&&r.optBoolean("passed")){nativeCount++;generations.add(r.optLong("generation"));sizes.add(r.optInt("width")+"x"+r.optInt("height"));
            if(r.optLong("run_id")==nativeSequence&&r.optLong("generation")==generation&&r.optInt("width")==inputView.getWidth()&&r.optInt("height")==inputView.getHeight()&&r.optBoolean("foreground_at_completion"))current=true;}}
        for(int i=0;i<audioRuns.length();i++)if(audioRuns.optJSONObject(i).optBoolean("passed"))audioCount++;
        return active&&current&&assetsReady&&syntheticPassed&&failures==0&&nativeCount>=3&&generations.size()>=2&&sizes.size()>=2&&audioCount>=1;
    }
    private boolean backgroundPassed() {
        long pause=background.optLong("pause_sequence",-1),stop=background.optLong("stop_sequence",-1),resume=background.optLong("resume_sequence",-1);
        if(!(pause>0&&stop>pause&&resume>stop&&background.optBoolean("input_cleared")&&background.optBoolean("audio_started_before_pause")))return false;
        boolean check=false,reopen=false,cancel=false;
        for(int i=0;i<nativeRuns.length();i++){JSONObject r=nativeRuns.optJSONObject(i);if(r.optBoolean("passed")&&r.optBoolean("foreground_at_completion")&&r.optLong("started_after_event")>=resume)check=true;}
        for(int i=0;i<audioRuns.length();i++){JSONObject r=audioRuns.optJSONObject(i);if(r.optBoolean("passed")&&r.optBoolean("foreground_at_completion")&&r.optLong("started_after_event")>=resume)reopen=true;
            if(r.optLong("run_id")==background.optLong("interrupted_audio_run_id",-1)&&r.optInt("result")==1&&r.optBoolean("cancelled")&&r.optBoolean("opened")&&r.optBoolean("started")&&r.optBoolean("stopped")&&r.optBoolean("closed")&&
                r.optInt("backend_errors")==0&&r.optLong("submitted_frames")>0&&r.optLong("started_after_event")<pause)cancel=true;}
        return check&&reopen&&cancel;
    }
    private JSONObject adapterReport() {
        try{return adapter==null?object():adapter.report();}catch(Exception e){throw new IllegalStateException(e);}
    }
    private JSONObject visibleScreenBounds(View view) {
        Rect rect=new Rect();boolean visible=view!=null&&view.getGlobalVisibleRect(rect)&&rect.width()>0&&rect.height()>0;
        if(!visible)return object("left",0,"top",0,"width",0,"height",0,"visible",false,"fully_visible",false,
            "view_width",view==null?0:view.getWidth(),"view_height",view==null?0:view.getHeight());
        int[] origin=new int[2];view.getRootView().getLocationOnScreen(origin);rect.offset(origin[0],origin[1]);
        return object("left",rect.left,"top",rect.top,"width",rect.width(),"height",rect.height(),"visible",true,
            "fully_visible",rect.width()==view.getWidth()&&rect.height()==view.getHeight(),"view_width",view.getWidth(),"view_height",view.getHeight());
    }
    private JSONObject measuredControls() {
        JSONObject result=object();try{for(Map.Entry<String,Button> entry:measuredButtons.entrySet())result.put(entry.getKey(),visibleScreenBounds(entry.getValue()));}
        catch(Exception e){throw new IllegalStateException(e);}return result;
    }
    private JSONObject measuredControlRow() {
        JSONObject result=visibleScreenBounds(controlScroll);try{if(controlScroll!=null)result.put("scroll_x",controlScroll.getScrollX())
            .put("content_width",controlScroll.getChildCount()>0?controlScroll.getChildAt(0).getWidth():0)
            .put("can_scroll_left",controlScroll.canScrollHorizontally(-1)).put("can_scroll_right",controlScroll.canScrollHorizontally(1));}
        catch(Exception e){throw new IllegalStateException(e);}return result;
    }
    private boolean externalInputTransportPassed() {
        JSONObject e=adapterReport().optJSONObject("external_android");
        return e!=null&&e.optLong("touch_begin")>0&&e.optLong("touch_move")>0&&e.optLong("touch_end")>0&&e.optLong("key_down")>0&&e.optLong("key_up")>0;
    }
    private void refresh() {
        if(report==null||status==null||destroyed)return;
        try {
            boolean pre=preBackground(),home=backgroundPassed(),transport=externalInputTransportPassed(),qualified=pre&&home&&transport;
            boolean sourceInput=false,sourceAudio=false,protocol=false,audioEngine=false;
            JSONObject external=adapterReport().optJSONObject("external_android");
            boolean controllerAxes=external!=null&&external.optLong("controller_events")>0&&external.optInt("left_axis_directions")==15&&external.optInt("right_axis_directions")==15;
            for(int i=0;i<nativeRuns.length();i++){JSONObject r=nativeRuns.optJSONObject(i);
                sourceInput|=r.optJSONObject("input")!=null&&r.optJSONObject("input").optBoolean("passed");
                sourceAudio|=r.optJSONObject("audio_source")!=null&&r.optJSONObject("audio_source").optBoolean("passed");
                protocol|=r.optJSONObject("protocol")!=null&&r.optJSONObject("protocol").optBoolean("passed");}
            for(int i=0;i<audioRuns.length();i++)audioEngine|=audioRuns.optJSONObject(i).optBoolean("passed");
            report.put("updated_at",now()).put("assets_verified",assetsReady).put("asset_metadata",fixture).put("load_failure",loadFailure==null?JSONObject.NULL:loadFailure)
                .put("input_adapter",adapterReport()).put("input_snapshot",lastFrame).put("synthetic_dispatch_passed",syntheticPassed)
                .put("audio_busy",audioBusy).put("backend_audio_active",nativeAudioActive()).put("session_failures",failures)
                .put("auto_smoke",autoSmoke).put("auto_smoke_stage",smokeStage).put("auto_smoke_completed",smokeCompleted).put("generation",generation)
                .put("background_return",background).put("pre_background_checks_passed",pre).put("background_return_gate_passed",home)
                .put("android_input_transport_passed",transport).put("input_gate_passed",sourceInput&&syntheticPassed&&transport&&home&&failures==0)
                .put("controller_axis_coverage_passed",controllerAxes&&!report.getJSONObject("device").optBoolean("emulator_detected"))
                .put("controller_axis_coverage_scope","All four Android directions on both controller sticks; tracked separately from emulator callback qualification")
                .put("audio_engine_gate_passed",sourceAudio&&audioEngine&&home&&failures==0).put("protocol_gate_passed",protocol&&failures==0)
                .put("qualification_passed",qualified).put("device_audible_confirmation_passed",audibleConfirmed)
                .put("audible_confirmation_scope",audibleConfirmed?"user reported hearing three sounds":"not confirmed; engine writes do not prove audibility")
                .put("input_area",inputView==null?object():inputView.area()).put("controls",measuredControls()).put("control_row",measuredControlRow());
            status.setText((qualified?"SYSTEM GATES PASSED":"QUALIFICATION PENDING")+" — Gates 10–12\n"+
                (!pre?"Run checks, resize and recreate.":home?(transport?"Home/return and callbacks passed.":"Drag arrow and press/release a button."):"Play, then Home during audio; return and play.")+"\n"+
                "Audio: "+(nativeAudioActive()?"playing":audioBusy?"preparing":"idle")+"  |  Sticks: "+(controllerAxes?"complete":"pending")+"  |  Heard: "+(audibleConfirmed?"confirmed":"pending"));
            status.setTextColor(qualified?Color.rgb(0,104,42):failures>0?Color.rgb(150,20,20):Color.DKGRAY);
            String text=report.toString(2);reportText.setText(text);writeReport(text.getBytes(StandardCharsets.UTF_8));
        }catch(Exception e){status.setText("REPORT ERROR — "+e);status.setTextColor(Color.RED);}
    }
    private void writeReport(byte[] bytes) throws Exception {
        FileOutputStream out=null;try{out=reportFile.startWrite();out.write(bytes);reportFile.finishWrite(out);}catch(Exception e){if(out!=null)reportFile.failWrite(out);throw e;}
    }
    private void exportReport() {
        try {refresh();exportSnapshot=report.toString(2).getBytes(StandardCharsets.UTF_8);Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT);
            intent.addCategory(Intent.CATEGORY_OPENABLE);intent.setType("application/json");intent.putExtra(Intent.EXTRA_TITLE,"COH-NativeSystems-"+new SimpleDateFormat("yyyyMMdd-HHmmss",Locale.US).format(new Date())+".json");startActivityForResult(intent,exportRequest);
        }catch(Exception e){event("export_error",object("error",e.toString()));refresh();}
    }
    @Override protected void onActivityResult(int request,int result,Intent data) {
        super.onActivityResult(request,result,data);if(request!=exportRequest)return;
        if(result==RESULT_OK&&data!=null&&data.getData()!=null&&exportSnapshot!=null)try(java.io.OutputStream out=getContentResolver().openOutputStream(data.getData())){
            if(out==null)throw new IllegalStateException("No export stream");out.write(exportSnapshot);event("export_complete",object("bytes",exportSnapshot.length));
        }catch(Exception e){event("export_error",object("error",e.toString()));}exportSnapshot=null;refresh();
    }
    private final class InputCanvas extends View {
        private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
        InputCanvas(){super(MainActivity.this);setFocusable(true);setFocusableInTouchMode(true);}
        @Override protected void onSizeChanged(int w,int h,int oldW,int oldH){super.onSizeChanged(w,h,oldW,oldH);
            event("input_view_size_changed",object("width",w,"height",h,"old_width",oldW,"old_height",oldH));main.post(()->{runChecks("input_view_size_changed");runPending();});}
        @Override public boolean onTouchEvent(MotionEvent e){boolean used=adapter.dispatchTouchEvent(e,getWidth(),getHeight());if(used){requestFocus();refresh();}return used;}
        @Override protected void onDraw(Canvas canvas){super.onDraw(canvas);float cx=getWidth()/2f,cy=getHeight()/2f;
            paint.setColor(Color.rgb(53,64,75));paint.setStrokeWidth(dp(1));canvas.drawLine(0,cy,getWidth(),cy,paint);canvas.drawLine(cx,0,cx,getHeight(),paint);
            JSONArray pyr=lastFrame.optJSONArray("pyr");float yaw=pyr==null?0:(float)pyr.optDouble(1);float pitch=pyr==null?0:(float)pyr.optDouble(0);
            float r=Math.min(getWidth(),getHeight())*.34f;float x=cx+(float)Math.sin(yaw)*r,y=cy-(float)Math.cos(yaw)*r;
            paint.setColor(Color.rgb(100,204,241));paint.setStrokeWidth(dp(5));canvas.drawLine(cx,cy,x,y,paint);canvas.drawCircle(x,y,dp(9),paint);
            paint.setTextSize(dp(14));canvas.drawText("Native source editor-look preview",dp(12),dp(22),paint);canvas.drawText("Pitch "+String.format(Locale.US,"%.3f",pitch)+" rad",dp(12),getHeight()-dp(12),paint);
        }
        JSONObject area(){int[] location=new int[2];getLocationOnScreen(location);return object("left",location[0],"top",location[1],"width",getWidth(),"height",getHeight());}
    }
}
