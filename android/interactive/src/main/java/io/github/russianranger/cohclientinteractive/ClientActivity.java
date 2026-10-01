package io.github.russianranger.cohclientinteractive;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.text.InputFilter;
import android.text.InputType;
import android.content.*;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.*;
import android.view.*;
import android.widget.*;
import java.io.*;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.*;

/** Bounded touch, keyboard and Thor controller session for reopening an existing character. */
public final class ClientActivity extends Activity {
    private static final int EXPORT=11,NOTIFY=12,IMPORT=13;
    private final ExecutorService exporter=Executors.newSingleThreadExecutor();
    private ClientService service;
    private ClientService.State state;
    private ClientSurface display;
    private TextView status,detail,counter,logs;
    private Button setup,importAssets,run,stop,export,finish,typeText,returnGround,saveLogout;
    private CursorOverlay cursor;
    private final Handler inputHandler=new Handler(Looper.getMainLooper());
    private final Map<Integer,Integer> heldKeys=new LinkedHashMap<>();
    private final Set<Integer> heldButtons=new HashSet<>();
    private float rightX,rightY;
    private boolean inputActive,textDialogVisible;
    private AlertDialog activeTextDialog;
    private long lastTick;
    private final Runnable inputTick=new Runnable(){@Override public void run(){
        long now=SystemClock.uptimeMillis();float elapsed=Math.min(64,Math.max(0,now-lastTick));lastTick=now;
        if(inputActive&&hasWindowFocus()&&!textDialogVisible&&(rightX!=0||rightY!=0))display.movePointer(rightX*elapsed*0.55f,rightY*elapsed*0.55f);
        updateCounter();inputHandler.postDelayed(this,32);
    }};
    private boolean bound,exporting,captureEnabled,importWaiting;
    private String pendingExport,pendingAction,shownSession="";
    private android.net.Uri pendingImport;
    private final ClientService.Listener listener=new ClientService.Listener(){
        @Override public void onState(ClientService.State value){render(value);}
        @Override public void onFrame(int[] pixels,int width,int height,long sequence){display.setFrame(pixels,width,height,sequence);}
    };
    private final ClientSurface.Listener captureListener=new ClientSurface.Listener(){
        @Override public void onCapture(ClientSurface.Capture sample){if(service!=null)service.recordCapture(sample);}
        @Override public void onCaptureError(String error){if(service!=null)service.recordCertificationError(error);}
    };
    private final ServiceConnection connection=new ServiceConnection(){
        @Override public void onServiceConnected(ComponentName name,IBinder binder){service=((ClientService.LocalBinder)binder).service();service.setUiVisible(true);service.addListener(listener);dispatchPendingImport();}
        @Override public void onServiceDisconnected(ComponentName name){releaseControls(true);inputActive=false;display.setInputEnabled(false);finish.setEnabled(false);typeText.setEnabled(false);saveLogout.setEnabled(false);returnGround.setEnabled(false);service=null;setup.setEnabled(false);importAssets.setEnabled(false);run.setEnabled(false);stop.setEnabled(false);status.setText("Service disconnected");detail.setText("Reopen this screen to reconnect.");}
    };
    @Override public void onCreate(Bundle saved){
        super.onCreate(saved);getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        if(saved!=null){pendingExport=saved.getString("export");pendingAction=saved.getString("action");importWaiting=saved.getBoolean("import_waiting",false);String selected=saved.getString("import_uri");if(selected!=null)pendingImport=android.net.Uri.parse(selected);}
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.HORIZONTAL);root.setBackgroundColor(Color.rgb(9,19,30));root.setPadding(dp(12),dp(8),dp(12),dp(8));
        root.setOnApplyWindowInsetsListener((v,insets)->{v.setPadding(dp(12)+insets.getSystemWindowInsetLeft(),dp(8)+insets.getSystemWindowInsetTop(),dp(12)+insets.getSystemWindowInsetRight(),dp(8)+insets.getSystemWindowInsetBottom());return insets;});
        LinearLayout controls=new LinearLayout(this);controls.setOrientation(LinearLayout.VERTICAL);controls.setPadding(0,0,dp(12),0);
        ScrollView scroll=new ScrollView(this);scroll.addView(controls);root.addView(scroll,new LinearLayout.LayoutParams(dp(224),-1));
        TextView title=text("COH Character Reopen",22,true);controls.addView(title);
        controls.addView(text("Persistent local server · v0.10.0",12,false));
        controls.addView(text("Reopen your saved THORHERO and verify its identity, powers and costume survive another ordinary save. Keep your app data and imported assets.",13,false));
        setup=button("1 · Refresh runtime",()->request(ClientService.SETUP));controls.addView(setup);
        importAssets=button("Import assets (new install only)",this::chooseImport);controls.addView(importAssets);
        run=button("2 · Reopen saved THORHERO",()->request(ClientService.RUN));controls.addView(run);
        returnGround=button("Return to safe ground",()->{releaseControls();if(service!=null)service.requestReturnToSafeGround();});controls.addView(returnGround);
        saveLogout=button("Save character / log out",()->{releaseControls();if(service!=null)service.requestSaveLogout();});controls.addView(saveLogout);
        finish=button("Finish and save report",()->{releaseControls();if(service!=null)service.requestFinish();});controls.addView(finish);
        typeText=button("Send text / L3",this::showTextInput);controls.addView(typeText);
        stop=button("Abort operation",()->{if(service!=null)startService(new Intent(this,ClientService.class).setAction(ClientService.STOP));});controls.addView(stop);
        export=button("Export latest report",this::chooseExport);controls.addView(export);
        status=text("Connecting",17,true);controls.addView(status);
        detail=text("Connecting to the private runtime service…",13,false);controls.addView(detail);
        counter=text("Waiting for the client",12,false);controls.addView(counter);
        controls.addView(text("Refresh runtime once after this update. When input is ready: verify COHLOCAL / offline, select your existing THORHERO and click Enter Game. Do not create or delete a character or change its costume. Wait for Saved character reopened, dismiss the Welcome popup with OK, then tap Return to safe ground once and stay still. After Atlas position verified, inspect Atlas, your character and the UI, then tap Save character / log out once. Wait for Saved character verified, then tap Finish and export the report. You have 20 minutes after input becomes ready.",12,false));
        logs=text("",10,false);logs.setTypeface(Typeface.MONOSPACE);logs.setTextIsSelectable(true);controls.addView(logs);
        LinearLayout right=new LinearLayout(this);right.setOrientation(LinearLayout.VERTICAL);root.addView(right,new LinearLayout.LayoutParams(0,-1,1));
        TextView caption=text("CITY OF HEROES · SAVED CHARACTER",12,true);right.addView(caption);
        FrameLayout viewport=new FrameLayout(this);right.addView(viewport,new LinearLayout.LayoutParams(-1,0,1));
        display=new ClientSurface(this);viewport.addView(display,new FrameLayout.LayoutParams(-1,-1));
        cursor=new CursorOverlay();viewport.addView(cursor,new FrameLayout.LayoutParams(-1,-1));
        display.setInputListener(new ClientSurface.InputListener(){
            @Override public void onPointer(String session,int x,int y,int buttons){if(service!=null)service.sendPointer(session,x,y,buttons);}
            @Override public void onReleaseAll(String session){releaseRemoteInputs(session,!textDialogVisible);}
            @Override public void onCursor(float x,float y,boolean visible){cursor.move(x,y,visible);}
        });
        right.addView(text("Tap / drag · Right stick: cursor · A: click · B: Esc · Shoulders: right click · D-pad: arrows · L3: text",12,false));

        setContentView(root);root.requestApplyInsets();setup.setEnabled(false);importAssets.setEnabled(false);run.setEnabled(false);stop.setEnabled(false);export.setEnabled(false);finish.setEnabled(false);typeText.setEnabled(false);saveLogout.setEnabled(false);returnGround.setEnabled(false);
    }
    private TextView text(String value,int size,boolean bold){TextView t=new TextView(this);t.setText(value);t.setTextSize(size);t.setTextColor(Color.rgb(221,234,245));t.setPadding(0,dp(3),0,dp(7));if(bold)t.setTypeface(Typeface.DEFAULT,Typeface.BOLD);return t;}
    private Button button(String label,Runnable click){Button b=new Button(this);b.setText(label);b.setAllCaps(false);b.setTextSize(13);b.setOnClickListener(v->click.run());return b;}
    private int dp(int value){return Math.round(value*getResources().getDisplayMetrics().density);}
    @Override protected void onStart(){super.onStart();lastTick=SystemClock.uptimeMillis();inputHandler.post(inputTick);bound=bindService(new Intent(this,ClientService.class),connection,BIND_AUTO_CREATE);}
    @Override protected void onStop(){inputHandler.removeCallbacks(inputTick);releaseControls(true);display.setInputEnabled(false);inputActive=false;display.setCaptureListener(null);captureEnabled=false;if(service!=null){service.setUiVisible(false);service.removeListener(listener);}service=null;if(bound){unbindService(connection);bound=false;}super.onStop();}
    private void render(ClientService.State next){
        state=next;boolean capture=next.busy&&!next.session.isEmpty();if(capture!=captureEnabled){captureEnabled=capture;display.setCaptureListener(capture?captureListener:null);}setTextIfChanged(status,next.stage);setTextIfChanged(detail,next.detail);setTextIfChanged(logs,next.log);updateCounter();
        boolean idle=!next.busy&&!next.blocked;setup.setEnabled(idle);importAssets.setEnabled(idle);run.setEnabled(idle);stop.setEnabled(next.busy);export.setEnabled(!next.busy&&next.report!=null&&!exporting);
        if(!next.session.isEmpty()&&!next.session.equals(shownSession)){releaseControls();shownSession=next.session;display.setSession(shownSession);}
        boolean enabled=next.busy&&next.inputReady&&!next.finishing&&!next.blocked;
        if(inputActive&&!enabled)releaseControls();inputActive=enabled;display.setInputEnabled(enabled);
        finish.setEnabled(enabled&&next.characterSaved);typeText.setEnabled(enabled);returnGround.setEnabled(enabled&&next.canReturnGround);saveLogout.setEnabled(enabled&&next.canSaveLogout);
    }
    private void setTextIfChanged(TextView view,String value){if(!android.text.TextUtils.equals(view.getText(),value))view.setText(value);}
    private void updateCounter(){
        if(state==null||counter==null)return;
        long remaining=state.readyDeadlineUptimeMillis>0?Math.max(0,(state.readyDeadlineUptimeMillis-SystemClock.uptimeMillis()+999)/1000):0;
        setTextIfChanged(counter,"Android captures: "+state.certified+" · Inputs sent: "+state.inputSent
                +(state.inputFailed>0?" · Input failures: "+state.inputFailed:"")
                +(state.inputReady?"\nInput ready · "+remaining+"s remaining":""));
    }
    private void showTextInput(){
        if(!inputActive||service==null||textDialogVisible)return;
        // This app-owned dialog must not discard the preceding account-field tap
        // while its neutral preposition is settling on the input worker.
        textDialogVisible=true;releaseControls();
        try {
        EditText field=new EditText(this);field.setSingleLine(true);field.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
        field.setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS);field.setSaveEnabled(false);
        field.setFilters(new InputFilter[]{new InputFilter.LengthFilter(ClientInput.MAX_TEXT)});field.setText("COHLOCAL");field.selectAll();
        CheckBox replace=new CheckBox(this);replace.setText("Replace focused game field (Ctrl+A)");replace.setChecked(true);
        LinearLayout entry=new LinearLayout(this);entry.setOrientation(LinearLayout.VERTICAL);entry.addView(field);entry.addView(replace);
        AlertDialog dialog=new AlertDialog.Builder(this).setTitle("Send text to game")
                .setMessage("First tap the game field. Account: COHLOCAL. Password: offline. Character name: THORHERO.")
                .setView(entry).setNegativeButton("Cancel",null).setPositiveButton("Send",(d,w)->{
                    String value=field.getText().toString();
                    if(!ClientInput.validText(value)){Toast.makeText(this,"Use 1–32 printable English characters.",Toast.LENGTH_SHORT).show();return;}
                    if(!inputActive||service==null)return;
                    boolean queued=true;
                    if(replace.isChecked()) {
                        queued=service.sendKey(shownSession,0xffe3,true)
                                && service.sendKey(shownSession,'a',true)
                                && service.sendKey(shownSession,'a',false)
                                && service.sendKey(shownSession,0xffe3,false);
                    }
                    for(int i=0;queued&&i<value.length();i++){
                        int key=value.charAt(i);
                        if(!service.sendKey(shownSession,key,true)){queued=false;break;}
                        if(!service.sendKey(shownSession,key,false)){queued=false;break;}
                    }
                    if(!queued){service.releaseAllInputs(shownSession);Toast.makeText(this,"Text was not fully sent. Wait for input ready and retry.",Toast.LENGTH_SHORT).show();}
                    field.setText("");
                }).create();
        activeTextDialog=dialog;
        dialog.setOnDismissListener(d->{textDialogVisible=false;activeTextDialog=null;field.setText("");});dialog.show();
        field.requestFocus();if(dialog.getWindow()!=null)dialog.getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_VISIBLE);
        } catch(RuntimeException failure){
            textDialogVisible=false;
            if(activeTextDialog!=null){activeTextDialog.dismiss();activeTextDialog=null;}
            releaseControls(true);
            Toast.makeText(this,"Could not open test text entry. Return to the client and retry.",Toast.LENGTH_SHORT).show();
        }
    }
    private void pressKey(int physical,int keysym){
        if(keysym==0||heldKeys.containsKey(physical)||service==null)return;
        boolean alreadyHeld=heldKeys.containsValue(keysym);heldKeys.put(physical,keysym);
        if(!alreadyHeld&&!service.sendKey(shownSession,keysym,true))heldKeys.remove(physical);
    }
    private void releaseKey(int physical){
        Integer key=heldKeys.remove(physical);
        if(key!=null&&!heldKeys.containsValue(key)&&service!=null)service.sendKey(shownSession,key,false);
    }
    private void releaseRemoteInputs(String session,boolean discardPending){
        if(service==null||session.isEmpty())return;
        if(discardPending)service.releaseAllInputs(session);else service.releaseInput(session);
    }
    private void releaseControls(){releaseControls(!textDialogVisible);}
    private void releaseControls(boolean discardPending){
        rightX=rightY=0;heldKeys.clear();heldButtons.clear();
        if(display!=null)display.releaseInput();
        releaseRemoteInputs(shownSession,discardPending);
    }
    @Override public void onWindowFocusChanged(boolean focus){super.onWindowFocusChanged(focus);if(!focus)releaseControls();}
    @Override public boolean dispatchKeyEvent(KeyEvent event){
        if(!inputActive||textDialogVisible||service==null)return super.dispatchKeyEvent(event);
        int code=event.getKeyCode();boolean down=event.getAction()==KeyEvent.ACTION_DOWN;
        if(event.getAction()!=KeyEvent.ACTION_DOWN&&event.getAction()!=KeyEvent.ACTION_UP)return super.dispatchKeyEvent(event);
        boolean gamepad=(event.getSource()&InputDevice.SOURCE_GAMEPAD)==InputDevice.SOURCE_GAMEPAD;
        if(gamepad&&(code==KeyEvent.KEYCODE_BUTTON_A||code==KeyEvent.KEYCODE_BUTTON_L1||code==KeyEvent.KEYCODE_BUTTON_R1)){
            if(down)heldButtons.add(code);else heldButtons.remove(code);
            int buttons=(heldButtons.contains(KeyEvent.KEYCODE_BUTTON_A)?1:0)
                    |((heldButtons.contains(KeyEvent.KEYCODE_BUTTON_L1)||heldButtons.contains(KeyEvent.KEYCODE_BUTTON_R1))?4:0);
            display.setControllerButtons(buttons);return true;
        }
        if(gamepad&&code==KeyEvent.KEYCODE_BUTTON_THUMBL){if(down&&event.getRepeatCount()==0)showTextInput();return true;}
        int keysym=0;
        switch(code){
            case KeyEvent.KEYCODE_DPAD_LEFT:keysym=0xff51;break;case KeyEvent.KEYCODE_DPAD_UP:keysym=0xff52;break;
            case KeyEvent.KEYCODE_DPAD_RIGHT:keysym=0xff53;break;case KeyEvent.KEYCODE_DPAD_DOWN:keysym=0xff54;break;
            case KeyEvent.KEYCODE_ESCAPE:case KeyEvent.KEYCODE_BUTTON_B:keysym=0xff1b;break;
            case KeyEvent.KEYCODE_ENTER:case KeyEvent.KEYCODE_NUMPAD_ENTER:keysym=0xff0d;break;
            case KeyEvent.KEYCODE_TAB:keysym=0xff09;break;case KeyEvent.KEYCODE_DEL:keysym=0xff08;break;
            case KeyEvent.KEYCODE_FORWARD_DEL:keysym=0xffff;break;
            case KeyEvent.KEYCODE_SHIFT_LEFT:keysym=0xffe1;break;case KeyEvent.KEYCODE_SHIFT_RIGHT:keysym=0xffe2;break;
            case KeyEvent.KEYCODE_CTRL_LEFT:keysym=0xffe3;break;case KeyEvent.KEYCODE_CTRL_RIGHT:keysym=0xffe4;break;
            case KeyEvent.KEYCODE_ALT_LEFT:keysym=0xffe9;break;case KeyEvent.KEYCODE_ALT_RIGHT:keysym=0xffea;break;
            default:if(!gamepad)keysym=ClientInput.unicodeKeysym(event.getUnicodeChar());break;
        }
        if(!down&&heldKeys.containsKey(code)){releaseKey(code);return true;}
        if(keysym==0)return super.dispatchKeyEvent(event);
        if(down)pressKey(code,keysym);else releaseKey(code);return true;
    }
    @Override public boolean onGenericMotionEvent(MotionEvent event){
        if(!inputActive||textDialogVisible||(event.getSource()&InputDevice.SOURCE_JOYSTICK)!=InputDevice.SOURCE_JOYSTICK)
            return super.onGenericMotionEvent(event);
        InputDevice device=event.getDevice();
        int xAxis=device!=null&&device.getMotionRange(MotionEvent.AXIS_Z,event.getSource())!=null?MotionEvent.AXIS_Z:MotionEvent.AXIS_RX;
        int yAxis=device!=null&&device.getMotionRange(MotionEvent.AXIS_RZ,event.getSource())!=null?MotionEvent.AXIS_RZ:MotionEvent.AXIS_RY;
        rightX=ClientInput.axis(event.getAxisValue(xAxis));rightY=ClientInput.axis(event.getAxisValue(yAxis));
        updateHat(100001,0xff51,event.getAxisValue(MotionEvent.AXIS_HAT_X)<-0.5f);
        updateHat(100002,0xff53,event.getAxisValue(MotionEvent.AXIS_HAT_X)>0.5f);
        updateHat(100003,0xff52,event.getAxisValue(MotionEvent.AXIS_HAT_Y)<-0.5f);
        updateHat(100004,0xff54,event.getAxisValue(MotionEvent.AXIS_HAT_Y)>0.5f);
        return true;
    }
    private void updateHat(int physical,int key,boolean down){if(down)pressKey(physical,key);else releaseKey(physical);}
    /** Overlay is outside SurfaceView; it is not included in client PixelCopy evidence. */
    private final class CursorOverlay extends View{
        private final Paint paint=new Paint();private float x,y;private boolean visible;
        CursorOverlay(){super(ClientActivity.this);setClickable(false);setFocusable(false);paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(dp(2));}
        void move(float x,float y,boolean visible){if(this.x==x&&this.y==y&&this.visible==visible)return;this.x=x;this.y=y;this.visible=visible;invalidate();}
        @Override protected void onDraw(Canvas canvas){if(!visible)return;paint.setColor(Color.BLACK);canvas.drawCircle(x,y,dp(7),paint);paint.setColor(Color.CYAN);canvas.drawLine(x-dp(6),y,x+dp(6),y,paint);canvas.drawLine(x,y-dp(6),x,y+dp(6),paint);}
    }

    private void request(String action){
        if(state==null||state.busy||state.blocked)return;
        if(Build.VERSION.SDK_INT>=33&&checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED){pendingAction=action;requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},NOTIFY);return;}
        launch(action);
    }
    private void launch(String action){try{Intent intent=new Intent(this,ClientService.class).setAction(action);if(ClientService.IMPORT.equals(action)){intent.setData(pendingImport);intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);}startForegroundService(intent);}catch(RuntimeException e){Toast.makeText(this,"Could not start. Return to this screen and retry.",Toast.LENGTH_LONG).show();}}
    @Override public void onRequestPermissionsResult(int request,String[] permissions,int[] results){super.onRequestPermissionsResult(request,permissions,results);if(request==NOTIFY&&pendingAction!=null){String action=pendingAction;pendingAction=null;launch(action);}}
    private void chooseImport(){
        if(state==null||state.busy||state.blocked)return;
        Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("*/*").addCategory(Intent.CATEGORY_OPENABLE).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        try{startActivityForResult(intent,IMPORT);}catch(RuntimeException e){Toast.makeText(this,"No file picker is available.",Toast.LENGTH_LONG).show();}
    }
    private void dispatchPendingImport(){
        // A document result can arrive before the recreated Activity has rebound.
        if(!importWaiting||service==null||state==null)return;
        importWaiting=false;
        if(state.busy||state.blocked){Toast.makeText(this,"Wait until the current operation has finished, then select the asset ZIP again.",Toast.LENGTH_LONG).show();return;}
        request(ClientService.IMPORT);
    }
    private void chooseExport(){
        if(state==null||state.busy||state.report==null||exporting)return;pendingExport=state.report.getPath();
        Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT).setType("application/zip").addCategory(Intent.CATEGORY_OPENABLE);
        SimpleDateFormat format=new SimpleDateFormat("yyyyMMdd-HHmmss",Locale.ROOT);format.setTimeZone(TimeZone.getTimeZone("UTC"));intent.putExtra(Intent.EXTRA_TITLE,"coh-character-reopen-"+format.format(new Date())+".zip");
        try{startActivityForResult(intent,EXPORT);}catch(RuntimeException e){pendingExport=null;Toast.makeText(this,"No export destination is available.",Toast.LENGTH_LONG).show();}
    }
    @Override protected void onActivityResult(int request,int result,Intent data){
        super.onActivityResult(request,result,data);
        if(request==IMPORT){if(result==RESULT_OK&&data!=null&&data.getData()!=null){pendingImport=data.getData();try{getContentResolver().takePersistableUriPermission(pendingImport,Intent.FLAG_GRANT_READ_URI_PERMISSION);}catch(SecurityException ignored){}importWaiting=true;dispatchPendingImport();}return;}
        if(request!=EXPORT)return;String selected=pendingExport;pendingExport=null;
        if(result!=RESULT_OK||data==null||data.getData()==null||selected==null)return;final android.net.Uri uri=data.getData();exporting=true;if(state!=null)render(state);
        exporter.execute(()->{String message;try(InputStream in=new FileInputStream(selected);OutputStream out=getContentResolver().openOutputStream(uri,"w")){if(out==null)throw new IOException("No export stream");byte[] buffer=new byte[65536];int n;while((n=in.read(buffer))!=-1)out.write(buffer,0,n);message="Report exported";}catch(Exception e){message="Export failed. Try another destination.";}final String finish=message;runOnUiThread(()->{exporting=false;if(state!=null)render(state);Toast.makeText(this,finish,Toast.LENGTH_LONG).show();});});
    }
    @Override protected void onSaveInstanceState(Bundle out){out.putString("export",pendingExport);out.putString("action",pendingAction);out.putString("import_uri",pendingImport==null?null:pendingImport.toString());out.putBoolean("import_waiting",importWaiting);super.onSaveInstanceState(out);}
    @Override protected void onDestroy(){if(activeTextDialog!=null)activeTextDialog.dismiss();exporter.shutdown();super.onDestroy();}
}
