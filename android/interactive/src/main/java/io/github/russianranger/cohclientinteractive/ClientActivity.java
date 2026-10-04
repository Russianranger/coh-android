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

/** Bounded touch, keyboard and Thor controller session for initial Atlas gameplay. */
public final class ClientActivity extends Activity {
    private static final int EXPORT=11,NOTIFY=12,IMPORT=13,STORAGE_EXPORT=14;
    private final ExecutorService exporter=Executors.newSingleThreadExecutor();
    private ClientService service;
    private ClientService.State state;
    private ClientSurface display;
    private TextView status,detail,counter,logs,profileStatus;
    private Button setup,importAssets,run,createFresh,stop,export,storage,finish,typeText,returnGround,saveLogout,captureContact,openTaskContact,captureAcceptedTask,completeTask,captureCompletedTask;
    private CheckBox performanceGraphics;
    private CursorOverlay cursor;
    private final Handler inputHandler=new Handler(Looper.getMainLooper());
    private final ClientInput.KeyOwners heldKeys=new ClientInput.KeyOwners();
    private final ClientInput.WalkingKeys walkingKeys=new ClientInput.WalkingKeys();
    private final List<Button> movementButtons=new ArrayList<>();
    private final Set<Integer> heldButtons=new HashSet<>();
    private float rightX,rightY;
    private boolean inputActive,textDialogVisible,movementSuppressed,deadlineMovementSuppressed;
    private AlertDialog activeTextDialog;
    private long lastTick;
    private final Runnable inputTick=new Runnable(){@Override public void run(){
        long now=SystemClock.uptimeMillis();float elapsed=Math.min(64,Math.max(0,now-lastTick));lastTick=now;
        if(gameInputOpen()&&hasWindowFocus()&&!textDialogVisible&&(rightX!=0||rightY!=0))display.movePointer(rightX*elapsed*0.55f,rightY*elapsed*0.55f);
        refreshDeadlineControls();updateCounter();inputHandler.postDelayed(this,32);
    }};
    private boolean bound,exporting,captureEnabled,importWaiting;
    private String pendingExport,pendingAction,shownSession="";
    private String pendingStorageExport;
    private android.net.Uri pendingExportDestination;
    private String pendingExportSource;
    private boolean storageDialogRequested;
    private AlertDialog storageDialog;
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
        @Override public void onServiceConnected(ComponentName name,IBinder binder){service=((ClientService.LocalBinder)binder).service();service.setUiVisible(true);service.addListener(listener);dispatchPendingImport();dispatchPendingExport();}
        @Override public void onServiceDisconnected(ComponentName name){releaseControls(true);inputActive=false;refreshMovementControls();display.setInputEnabled(false);finish.setEnabled(false);typeText.setEnabled(false);saveLogout.setEnabled(false);returnGround.setEnabled(false);captureContact.setEnabled(false);disableTaskControls();service=null;setup.setEnabled(false);importAssets.setEnabled(false);run.setEnabled(false);createFresh.setEnabled(false);stop.setEnabled(false);status.setText("Service disconnected");detail.setText("Reopen this screen to reconnect.");}
    };
    @Override public void onCreate(Bundle saved){
        super.onCreate(saved);getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        if(saved!=null){pendingExport=saved.getString("export");pendingStorageExport=saved.getString("storage_export");pendingExportSource=saved.getString("export_source");String destination=saved.getString("export_destination");if(destination!=null)pendingExportDestination=android.net.Uri.parse(destination);pendingAction=saved.getString("action");importWaiting=saved.getBoolean("import_waiting",false);String selected=saved.getString("import_uri");if(selected!=null)pendingImport=android.net.Uri.parse(selected);}
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.HORIZONTAL);root.setBackgroundColor(Color.rgb(9,19,30));root.setPadding(dp(12),dp(8),dp(12),dp(8));
        root.setOnApplyWindowInsetsListener((v,insets)->{v.setPadding(dp(12)+insets.getSystemWindowInsetLeft(),dp(8)+insets.getSystemWindowInsetTop(),dp(12)+insets.getSystemWindowInsetRight(),dp(8)+insets.getSystemWindowInsetBottom());return insets;});
        LinearLayout controls=new LinearLayout(this);controls.setOrientation(LinearLayout.VERTICAL);controls.setPadding(0,0,dp(12),0);
        ScrollView scroll=new ScrollView(this);scroll.addView(controls);root.addView(scroll,new LinearLayout.LayoutParams(dp(224),-1));
        TextView title=text("COH Atlas Gameplay",22,true);controls.addView(title);
        controls.addView(text("Persistent local server · v0.13.2",12,false));
        controls.addView(text("Reopen THORHERO, accept one task, complete it with the stock command and save. Keep your app data, imported assets, costume and powers.",13,false));
        setup=button("Set up runtime (new install only)",()->request(ClientService.SETUP));controls.addView(setup);
        importAssets=button("Import assets (new install only)",this::chooseImport);controls.addView(importAssets);
        performanceGraphics=new CheckBox(this);performanceGraphics.setText("Use performance graphics");
        performanceGraphics.setTextColor(Color.rgb(221,234,245));performanceGraphics.setTextSize(13);
        performanceGraphics.setChecked(ClientRuntime.performanceGraphicsEnabled(this));
        performanceGraphics.setOnCheckedChangeListener((button,checked)->ClientRuntime.setPerformanceGraphicsEnabled(this,checked));
        controls.addView(performanceGraphics);
        controls.addView(text("Lower detail and effects; 600×450 world with the same 800×600 interface. Turn off before launch to use your saved graphics settings.",12,false));
        run=button("2 · Reopen saved THORHERO",()->request(ClientService.RUN));controls.addView(run);
        createFresh=button("Create fresh THORHERO",this::confirmFreshProfile);createFresh.setVisibility(View.GONE);controls.addView(createFresh);
        profileStatus=text("Checking saved character profile…",12,false);controls.addView(profileStatus);
        returnGround=button("Return to safe ground (optional)",()->{releaseControls();if(service!=null)service.requestReturnToSafeGround();});controls.addView(returnGround);
        captureContact=button("Capture contact dialog",()->{releaseControls();if(service!=null)service.requestContactCapture();});controls.addView(captureContact);
        openTaskContact=button("Open task contact",()->{releaseControls();if(service!=null)service.requestOpenTaskContact();});controls.addView(openTaskContact);
        captureAcceptedTask=button("Capture accepted task",()->{releaseControls();if(service!=null)service.requestTaskCapture(false);});controls.addView(captureAcceptedTask);
        completeTask=button("Complete accepted task",()->{releaseControls();if(service!=null)service.requestCompleteAcceptedTask();});controls.addView(completeTask);
        captureCompletedTask=button("Capture completed task",()->{releaseControls();if(service!=null)service.requestTaskCapture(true);});controls.addView(captureCompletedTask);
        saveLogout=button("Save character / log out",this::saveCharacter);controls.addView(saveLogout);
        finish=button("Finish and save report",()->{releaseControls();if(service!=null)service.requestFinish();});controls.addView(finish);
        typeText=button("Send text / L3",this::showTextInput);controls.addView(typeText);
        controls.addView(text("Atlas movement · hold a button",12,true));
        addMovementRow(controls,"Forward",'w',"Back",'s',120001);
        addMovementRow(controls,"Left",'a',"Right",'d',120003);
        controls.addView(movementButton("Jump",' ',120005));
        stop=button("Abort operation",()->{movementSuppressed=true;releaseControls();refreshMovementControls();if(service!=null)startService(new Intent(this,ClientService.class).setAction(ClientService.STOP));});controls.addView(stop);
        export=button("Export latest report",this::chooseExport);controls.addView(export);
        storage=button("Storage and cleanup",this::showStorage);controls.addView(storage);
        status=text("Connecting",17,true);controls.addView(status);
        detail=text("Connecting to the private runtime service…",13,false);controls.addView(detail);
        counter=text("Waiting for the client",12,false);controls.addView(counter);
        controls.addView(text("Keep your current runtime and imported data after this update; setup and import do not restore a character database deleted by uninstalling. If no saved profile exists, use Create fresh THORHERO, create the character in the game, then Save character / log out and Finish. Reopen saved THORHERO resumes the task gate after that save. Log in with COHLOCAL / offline and enter THORHERO. After Atlas connection and fresh views, close help and game dialogs and tap Open task contact. Accept Matthew Habashy's What Was Lost / Part One: Demons and Gangsters task yourself; it mentions five Hellions, but the command below completes it without combat. Accept exactly one task. Open its journal entry and wait for Accepted task verified, then tap Capture accepted task and keep the journal visible until Accepted task view captured. Close the journal and contact dialog with B and tap Complete accepted task once; it sends /completetask 0 through the stock game command route. After Task completion verified, open its completed journal entry and tap Capture completed task. Follow the movement and Save countdowns, release controls for 60 seconds before Save, and stay still during logout. After Saved character verified, tap Finish and export. Prior contact tests remain accepted; Return to safe ground is optional if stuck.",12,false));
        logs=text("",10,false);logs.setTypeface(Typeface.MONOSPACE);logs.setTextIsSelectable(true);controls.addView(logs);
        LinearLayout right=new LinearLayout(this);right.setOrientation(LinearLayout.VERTICAL);root.addView(right,new LinearLayout.LayoutParams(0,-1,1));
        TextView caption=text("CITY OF HEROES · ATLAS PARK",12,true);right.addView(caption);
        FrameLayout viewport=new FrameLayout(this);right.addView(viewport,new LinearLayout.LayoutParams(-1,0,1));
        display=new ClientSurface(this);viewport.addView(display,new FrameLayout.LayoutParams(-1,-1));
        cursor=new CursorOverlay();viewport.addView(cursor,new FrameLayout.LayoutParams(-1,-1));
        display.setInputListener(new ClientSurface.InputListener(){
            @Override public void onPointer(String session,int x,int y,int buttons){if(service!=null)service.sendPointer(session,x,y,buttons);}
            @Override public void onReleaseAll(String session){resetLocalInputs();releaseRemoteInputs(session,!textDialogVisible&&!movementSuppressed);}
            @Override public void onCursor(float x,float y,boolean visible){cursor.move(x,y,visible);}
        });
        right.addView(text("After Atlas connection: Left stick: WASD · X: jump · Right stick: cursor · A: click/talk · B: Esc · Shoulders: right click / turn view · D-pad: arrows · L3: text",12,false));

        setContentView(root);root.requestApplyInsets();setup.setEnabled(false);importAssets.setEnabled(false);run.setEnabled(false);createFresh.setEnabled(false);stop.setEnabled(false);export.setEnabled(false);storage.setEnabled(false);finish.setEnabled(false);typeText.setEnabled(false);saveLogout.setEnabled(false);returnGround.setEnabled(false);captureContact.setEnabled(false);disableTaskControls();refreshMovementControls();
    }
    private TextView text(String value,int size,boolean bold){TextView t=new TextView(this);t.setText(value);t.setTextSize(size);t.setTextColor(Color.rgb(221,234,245));t.setPadding(0,dp(3),0,dp(7));if(bold)t.setTypeface(Typeface.DEFAULT,Typeface.BOLD);return t;}
    private Button button(String label,Runnable click){Button b=new Button(this);b.setText(label);b.setAllCaps(false);b.setTextSize(13);b.setOnClickListener(v->click.run());return b;}
    private void addMovementRow(LinearLayout parent,String first,int firstKey,String second,int secondKey,int physical){
        LinearLayout row=new LinearLayout(this);
        row.addView(movementButton(first,firstKey,physical),new LinearLayout.LayoutParams(0,-2,1));
        row.addView(movementButton(second,secondKey,physical+1),new LinearLayout.LayoutParams(0,-2,1));
        parent.addView(row);
    }
    private Button movementButton(String label,int key,int physical){
        Button b=button(label,()->{});b.setFocusable(false);movementButtons.add(b);
        b.setOnTouchListener((v,event)->{
            int action=event.getActionMasked();
            if(action==MotionEvent.ACTION_DOWN){
                if(!canWalk())return true;
                v.getParent().requestDisallowInterceptTouchEvent(true);v.setPressed(true);pressKey(physical,key);
            }else if(action==MotionEvent.ACTION_UP||action==MotionEvent.ACTION_CANCEL
                    ||action==MotionEvent.ACTION_MOVE&&(event.getX()<0||event.getY()<0||event.getX()>=v.getWidth()||event.getY()>=v.getHeight())){
                releaseKey(physical);v.setPressed(false);v.getParent().requestDisallowInterceptTouchEvent(false);
                if(action==MotionEvent.ACTION_UP)v.performClick();
            }
            return true;
        });return b;
    }
    private boolean canWalk(){return inputActive&&service!=null&&state!=null&&state.canSaveLogout&&!state.characterSaved&&!movementSuppressed&&!textDialogVisible&&hasWindowFocus()&&movementWindowOpen();}
    private boolean movementWindowOpen(){return state!=null&&(state.movementDeadlineUptimeMillis==0||SystemClock.uptimeMillis()<state.movementDeadlineUptimeMillis);}
    private boolean gameInputOpen(){return inputActive&&movementWindowOpen()&&!movementSuppressed;}
    private void disableTaskControls(){openTaskContact.setEnabled(false);captureAcceptedTask.setEnabled(false);completeTask.setEnabled(false);captureCompletedTask.setEnabled(false);}
    private void refreshDeadlineControls(){
        if(captureContact!=null)captureContact.setEnabled(inputActive&&service!=null&&state!=null
                &&state.canSaveLogout&&!state.characterSaved&&!textDialogVisible&&hasWindowFocus()
                &&movementWindowOpen()&&service.canCaptureContact());
        boolean taskAvailable=inputActive&&service!=null&&state!=null&&state.canSaveLogout&&!state.characterSaved
                &&!textDialogVisible&&hasWindowFocus()&&movementWindowOpen();
        if(openTaskContact!=null)openTaskContact.setEnabled(taskAvailable&&service.canOpenTaskContact());
        if(captureAcceptedTask!=null)captureAcceptedTask.setEnabled(taskAvailable&&service.canCaptureTask(false));
        if(completeTask!=null)completeTask.setEnabled(taskAvailable&&service.canCompleteAcceptedTask());
        if(captureCompletedTask!=null)captureCompletedTask.setEnabled(taskAvailable&&service.canCaptureTask(true));
        if(state==null)return;
        if(!movementWindowOpen()&&!deadlineMovementSuppressed){deadlineMovementSuppressed=true;releaseControls(!movementSuppressed);refreshMovementControls();}
        display.setInputEnabled(gameInputOpen());typeText.setEnabled(gameInputOpen());
        saveLogout.setEnabled(inputActive&&state.canSaveLogout&&service!=null&&service.canRequestSaveLogout()
                &&(state.saveDeadlineUptimeMillis==0||SystemClock.uptimeMillis()<state.saveDeadlineUptimeMillis));
    }
    private void refreshMovementControls(){
        boolean enabled=canWalk();
        if(!enabled){walkingKeys.update(0,0,false,heldKeys,this::sendOwnedKey);for(int owner=120001;owner<=120005;owner++)releaseKey(owner);releaseKey(KeyEvent.KEYCODE_BUTTON_X);}
        for(Button b:movementButtons){b.setEnabled(enabled);if(!enabled)b.setPressed(false);}
    }
    private void saveCharacter(){
        boolean before=movementSuppressed;movementSuppressed=true;releaseControls();refreshMovementControls();
        if(service==null||!service.requestSaveLogout()){movementSuppressed=before;refreshMovementControls();}
    }
    private int dp(int value){return Math.round(value*getResources().getDisplayMetrics().density);}
    @Override protected void onStart(){super.onStart();lastTick=SystemClock.uptimeMillis();inputHandler.post(inputTick);bound=bindService(new Intent(this,ClientService.class),connection,BIND_AUTO_CREATE);}
    @Override protected void onStop(){inputHandler.removeCallbacks(inputTick);releaseControls(true);display.setInputEnabled(false);inputActive=false;display.setCaptureListener(null);captureEnabled=false;if(service!=null){service.setUiVisible(false);service.removeListener(listener);}service=null;if(bound){unbindService(connection);bound=false;}super.onStop();}
    private boolean profileIdle(ClientService.State next){
        return next!=null&&service!=null&&!next.busy&&!next.storageBusy&&!next.reportExporting
                &&!next.blocked&&!exporting&&!ClientRuntime.operationInProgress();
    }
    private boolean canCreateFreshProfile(ClientService.State next){
        return profileIdle(next)&&next.profileState==ClientRuntime.ProfileState.ABSENT;
    }
    private void refreshProfileControls(ClientService.State next){
        run.setEnabled(profileIdle(next)&&next.profileState==ClientRuntime.ProfileState.READY);
        createFresh.setVisibility(next.profileState==ClientRuntime.ProfileState.ABSENT?View.VISIBLE:View.GONE);
        createFresh.setEnabled(canCreateFreshProfile(next));
        setTextIfChanged(profileStatus,next.profileNote);
    }
    private void confirmFreshProfile(){
        if(!canCreateFreshProfile(state))return;
        new AlertDialog.Builder(this).setTitle("Create fresh THORHERO?")
                .setMessage("This installation has no saved profile. Runtime setup and asset import do not restore a character database deleted by uninstalling. Start native character creation using your current runtime and imported assets, log in with COHLOCAL / offline and create THORHERO. Save character / log out, then Finish and export. Reopen saved THORHERO resumes task testing after that save.")
                .setNegativeButton("Cancel",null).setPositiveButton("Start character creation",(dialog,which)->{
                    // The profile or operation may change while this confirmation is open.
                    if(canCreateFreshProfile(state))request(ClientService.CREATE);
                }).show();
    }
    private void refreshAbortControl(ClientService.State next){
        stop.setEnabled(next.busy||next.storageBusy);
        stop.setText(next.storageBusy?"Cancel storage scan / cleanup":"Abort operation");
    }
    private void render(ClientService.State next){
        if(next.busy&&next.session.isEmpty())display.clearFrames();
        state=next;boolean capture=next.busy&&!next.session.isEmpty();if(capture!=captureEnabled){captureEnabled=capture;display.setCaptureListener(capture?captureListener:null);}setTextIfChanged(status,next.stage);setTextIfChanged(detail,next.detail);setTextIfChanged(logs,next.log);updateCounter();
        boolean idle=!next.busy&&!next.storageBusy&&!next.reportExporting&&!next.blocked&&!exporting&&!ClientRuntime.operationInProgress();setup.setEnabled(idle);importAssets.setEnabled(idle);refreshProfileControls(next);performanceGraphics.setEnabled(idle);storage.setEnabled(idle);refreshAbortControl(next);export.setEnabled(!next.busy&&!next.storageBusy&&!next.reportExporting&&next.report!=null&&!exporting&&!ClientRuntime.operationInProgress());
        if(next.storageBusy){setTextIfChanged(status,"Storage");setTextIfChanged(detail,next.storageStatus);}
        if(storageDialogRequested&&!next.storageBusy&&idle){storageDialogRequested=false;showStorage();}
        if(!next.session.isEmpty()&&!next.session.equals(shownSession)){releaseControls();shownSession=next.session;movementSuppressed=false;deadlineMovementSuppressed=false;display.setSession(shownSession);}
        boolean enabled=next.busy&&next.inputReady&&!next.finishing&&!next.blocked;
        if(inputActive&&!enabled)releaseControls();inputActive=enabled;display.setInputEnabled(enabled);
        finish.setEnabled(enabled&&next.characterSaved);typeText.setEnabled(enabled);returnGround.setEnabled(enabled&&next.canReturnGround);saveLogout.setEnabled(enabled&&next.canSaveLogout&&service!=null&&service.canRequestSaveLogout());
        refreshMovementControls();refreshDeadlineControls();
    }
    private void setTextIfChanged(TextView view,String value){if(!android.text.TextUtils.equals(view.getText(),value))view.setText(value);}
    private void updateCounter(){
        if(state==null||counter==null)return;
        long remaining=state.readyDeadlineUptimeMillis>0?Math.max(0,(state.readyDeadlineUptimeMillis-SystemClock.uptimeMillis()+999)/1000):0;
        String timing="";
        if(state.inputReady){
            long now=SystemClock.uptimeMillis();
            if(state.characterSaved)timing="\nSaved character verified · tap Finish now";
            else if(state.saveDeadlineUptimeMillis>0){
                long movement=Math.max(0,(state.movementDeadlineUptimeMillis-now+999)/1000);
                long save=Math.max(0,(state.saveDeadlineUptimeMillis-now+999)/1000);
                timing=save==0?"\nSave window expired · export after cleanup":movement==0?
                        "\nStand still · Save cutoff in "+save+"s":
                        "\nMove for up to "+movement+"s · Save cutoff in "+save+"s";
                timing+="\nSave proof and Finish: "+remaining+"s remaining";
            }else timing="\n"+("connected".equals(state.sessionPhase)?"Character connected":"Login window")+" · "+remaining+"s remaining";
        }
        setTextIfChanged(counter,"Android captures: "+state.certified+" · Inputs sent: "+state.inputSent
                +(state.inputFailed>0?" · Input failures: "+state.inputFailed:"")+timing);
    }
    private void showTextInput(){
        if(!gameInputOpen()||service==null||textDialogVisible)return;
        // This app-owned dialog must not discard the preceding account-field tap
        // while its neutral preposition is settling on the input worker.
        textDialogVisible=true;releaseControls();refreshMovementControls();
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
        dialog.setOnDismissListener(d->{textDialogVisible=false;activeTextDialog=null;field.setText("");refreshMovementControls();});dialog.show();
        field.requestFocus();if(dialog.getWindow()!=null)dialog.getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_VISIBLE);
        } catch(RuntimeException failure){
            textDialogVisible=false;
            if(activeTextDialog!=null){activeTextDialog.dismiss();activeTextDialog=null;}
            releaseControls(true);
            refreshMovementControls();
            Toast.makeText(this,"Could not open test text entry. Return to the client and retry.",Toast.LENGTH_SHORT).show();
        }
    }
    private void pressKey(int physical,int keysym){
        if(service!=null)heldKeys.press(physical,keysym,this::sendOwnedKey);
    }
    private void releaseKey(int physical){
        heldKeys.release(physical,this::sendOwnedKey);
    }
    private boolean sendOwnedKey(int key,boolean down){return service!=null&&service.sendKey(shownSession,key,down);}
    private void releaseRemoteInputs(String session,boolean discardPending){
        if(service==null||session.isEmpty())return;
        if(discardPending)service.releaseAllInputs(session);else service.releaseInput(session);
    }
    private void releaseControls(){releaseControls(!textDialogVisible);}
    private void resetLocalInputs(){
        rightX=rightY=0;walkingKeys.reset();heldKeys.clear();heldButtons.clear();for(Button b:movementButtons)b.setPressed(false);
    }
    private void releaseControls(boolean discardPending){
        resetLocalInputs();
        if(display!=null)display.releaseInput();
        releaseRemoteInputs(shownSession,discardPending);
    }
    @Override public void onWindowFocusChanged(boolean focus){super.onWindowFocusChanged(focus);if(!focus)releaseControls();refreshMovementControls();}
    @Override public boolean dispatchKeyEvent(KeyEvent event){
        if(!gameInputOpen()||textDialogVisible||service==null)return super.dispatchKeyEvent(event);
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
        if(gamepad&&code==KeyEvent.KEYCODE_BUTTON_X){if(down&&canWalk())pressKey(code,' ');else releaseKey(code);return true;}
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
        if(!down&&heldKeys.contains(code)){releaseKey(code);return true;}
        if(keysym==0)return super.dispatchKeyEvent(event);
        if(down)pressKey(code,keysym);else releaseKey(code);return true;
    }
    @Override public boolean onGenericMotionEvent(MotionEvent event){
        if(!gameInputOpen()||textDialogVisible||(event.getSource()&InputDevice.SOURCE_JOYSTICK)!=InputDevice.SOURCE_JOYSTICK)
            return super.onGenericMotionEvent(event);
        InputDevice device=event.getDevice();
        int xAxis=device!=null&&device.getMotionRange(MotionEvent.AXIS_Z,event.getSource())!=null?MotionEvent.AXIS_Z:MotionEvent.AXIS_RX;
        int yAxis=device!=null&&device.getMotionRange(MotionEvent.AXIS_RZ,event.getSource())!=null?MotionEvent.AXIS_RZ:MotionEvent.AXIS_RY;
        rightX=ClientInput.axis(event.getAxisValue(xAxis));rightY=ClientInput.axis(event.getAxisValue(yAxis));
        walkingKeys.update(event.getAxisValue(MotionEvent.AXIS_X),event.getAxisValue(MotionEvent.AXIS_Y),canWalk(),heldKeys,this::sendOwnedKey);
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
        if(state==null||state.busy||state.storageBusy||state.reportExporting||state.blocked||exporting||ClientRuntime.operationInProgress())return;
        if(Build.VERSION.SDK_INT>=33&&checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED){pendingAction=action;requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},NOTIFY);return;}
        launch(action);
    }
    private void launch(String action){try{Intent intent=new Intent(this,ClientService.class).setAction(action);if(ClientService.IMPORT.equals(action)){intent.setData(pendingImport);intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);}startForegroundService(intent);}catch(RuntimeException e){Toast.makeText(this,"Could not start. Return to this screen and retry.",Toast.LENGTH_LONG).show();}}
    @Override public void onRequestPermissionsResult(int request,String[] permissions,int[] results){super.onRequestPermissionsResult(request,permissions,results);if(request==NOTIFY&&pendingAction!=null){String action=pendingAction;pendingAction=null;launch(action);}}
    private void chooseImport(){
        if(state==null||state.busy||state.storageBusy||state.reportExporting||state.blocked||exporting||ClientRuntime.operationInProgress())return;
        Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("*/*").addCategory(Intent.CATEGORY_OPENABLE).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        try{startActivityForResult(intent,IMPORT);}catch(RuntimeException e){Toast.makeText(this,"No file picker is available.",Toast.LENGTH_LONG).show();}
    }
    private void dispatchPendingImport(){
        // A document result can arrive before the recreated Activity has rebound.
        if(!importWaiting||service==null||state==null)return;
        importWaiting=false;
        if(state.busy||state.storageBusy||state.reportExporting||state.blocked||ClientRuntime.operationInProgress()){Toast.makeText(this,"Wait until the current operation has finished, then select the asset ZIP again.",Toast.LENGTH_LONG).show();return;}
        request(ClientService.IMPORT);
    }
    private static String storageBytes(long bytes){
        if(bytes<1024)return bytes+" B";double value=bytes;String[] units={"B","KiB","MiB","GiB","TiB"};int unit=0;
        while(value>=1024&&unit<units.length-1){value/=1024;unit++;}return String.format(Locale.ROOT,"%.2f %s",value,units[unit]);
    }
    private void showStorage(){
        if(state==null||state.busy||state.storageBusy||state.reportExporting||state.blocked||exporting||ClientRuntime.operationInProgress())return;
        if(storageDialog!=null)storageDialog.dismiss();
        final StorageAudit.Plan plan=state.storagePlan;
        LinearLayout body=new LinearLayout(this);body.setOrientation(LinearLayout.VERTICAL);body.setPadding(dp(16),dp(8),dp(16),dp(8));
        TextView message=new TextView(this);message.setText(state.storageStatus+"\nThese totals cover private app files; Android also counts the installed APK and its cache. Allocated size counts storage blocks once; apparent size can include shared files. Character data, current runtime, imported assets and startup caches are protected.");body.addView(message);
        final Map<String,CheckBox> choices=new LinkedHashMap<>();
        if(plan!=null){
            TextView totals=new TextView(this);totals.setText("\nTotal allocated: "+storageBytes(plan.allocatedBytes)+"\nTotal apparent: "+storageBytes(plan.apparentBytes)+"\nEstimated removable: "+storageBytes(plan.reclaimableBytes)+"\nEntries inspected: "+plan.entryCount);body.addView(totals);
            if(!plan.errors.isEmpty()){TextView errors=new TextView(this);StringBuilder text=new StringBuilder("\nScan notes:");for(int i=0;i<Math.min(3,plan.errors.size());i++)text.append("\n").append(plan.errors.get(i));errors.setText(text.toString());body.addView(errors);}
            for(StorageAudit.Category category:plan.categories){
                String description=category.label+"\nAllocated: "+storageBytes(category.allocatedBytes)+" · Apparent: "+storageBytes(category.apparentBytes)+"\nRemovable: "+storageBytes(category.reclaimableBytes);
                if(plan.cleanupAllowed&&category.candidateCount>0&&Arrays.asList("old_runtime","downloads","old_reports").contains(category.id)){
                    CheckBox choice=new CheckBox(this);choice.setText(description);choice.setChecked(false);choices.put(category.id,choice);body.addView(choice);
                }else{TextView line=new TextView(this);line.setText(description+" · protected");line.setPadding(0,dp(8),0,dp(8));body.addView(line);}
            }
        }
        Button scan=new Button(this);scan.setText("Scan storage");scan.setOnClickListener(v->{storageDialog.dismiss();storageDialogRequested=true;request(ClientService.STORAGE_SCAN);});body.addView(scan);
        Button clean=new Button(this);clean.setText("Review selected cleanup");clean.setEnabled(plan!=null&&plan.cleanupAllowed&&!choices.isEmpty());clean.setOnClickListener(v->{
            Set<String> selected=new LinkedHashSet<>();for(Map.Entry<String,CheckBox> choice:choices.entrySet())if(choice.getValue().isChecked())selected.add(choice.getKey());
            if(selected.isEmpty()){Toast.makeText(this,"Select a disposable category first.",Toast.LENGTH_LONG).show();return;}
            StringBuilder review=new StringBuilder("Remove these disposable files from the reviewed scan?\n");long reclaimable=0;
            for(StorageAudit.Category category:plan.categories)if(selected.contains(category.id)){review.append("\n").append(category.label).append(": ").append(category.candidateCount).append(" candidates · ").append(storageBytes(category.reclaimableBytes));reclaimable+=category.reclaimableBytes;}
            int shown=0,total=0;for(StorageAudit.Candidate candidate:plan.candidates)if(selected.contains(candidate.categoryId)){total++;if(shown++<12)review.append("\n").append(candidate.path);}
            if(total>12)review.append("\n").append(total-12).append(" more candidates are listed in the storage report.");
            review.append("\n\nEstimated space recoverable: ").append(storageBytes(reclaimable)).append(". Current runtime, character database, imported assets and startup caches remain protected. Old support reports selected here will be removed.");
            new AlertDialog.Builder(this).setTitle("Confirm selected cleanup").setMessage(review.toString()).setNegativeButton("Cancel",null).setPositiveButton("Clean selected",(dialog,which)->{
                if(state==null||state.busy||state.storageBusy||state.reportExporting||state.blocked||exporting||ClientRuntime.operationInProgress())return;
                storageDialog.dismiss();storageDialogRequested=true;
                Intent intent=new Intent(this,ClientService.class).setAction(ClientService.STORAGE_CLEAN).putExtra("storage_snapshot",plan.snapshotId).putExtra("storage_categories",selected.toArray(new String[0]));
                try{startForegroundService(intent);}catch(RuntimeException e){storageDialogRequested=false;Toast.makeText(this,"Could not start cleanup. Scan again and retry.",Toast.LENGTH_LONG).show();}
            }).show();
        });body.addView(clean);
        Button exportStorage=new Button(this);exportStorage.setText("Export storage report");exportStorage.setEnabled(state.storageReport!=null);exportStorage.setOnClickListener(v->{storageDialog.dismiss();chooseStorageExport();});body.addView(exportStorage);
        ScrollView scroll=new ScrollView(this);scroll.addView(body);storageDialog=new AlertDialog.Builder(this).setTitle("Storage and cleanup").setView(scroll).setNegativeButton("Close",null).create();storageDialog.show();
    }
    private void chooseExport(){
        if(state==null||state.busy||state.storageBusy||state.reportExporting||state.report==null||exporting||ClientRuntime.operationInProgress())return;pendingExport=state.report.getPath();
        Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT).setType("application/zip").addCategory(Intent.CATEGORY_OPENABLE);
        SimpleDateFormat format=new SimpleDateFormat("yyyyMMdd-HHmmss",Locale.ROOT);format.setTimeZone(TimeZone.getTimeZone("UTC"));intent.putExtra(Intent.EXTRA_TITLE,"coh-atlas-gameplay-"+format.format(new Date())+".zip");
        try{startActivityForResult(intent,EXPORT);}catch(RuntimeException e){pendingExport=null;Toast.makeText(this,"No export destination is available.",Toast.LENGTH_LONG).show();}
    }
    private void chooseStorageExport(){
        if(state==null||state.busy||state.storageBusy||state.reportExporting||state.storageReport==null||exporting||ClientRuntime.operationInProgress())return;pendingStorageExport=state.storageReport.getPath();
        Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT).setType("application/json").addCategory(Intent.CATEGORY_OPENABLE);
        SimpleDateFormat format=new SimpleDateFormat("yyyyMMdd-HHmmss",Locale.ROOT);format.setTimeZone(TimeZone.getTimeZone("UTC"));intent.putExtra(Intent.EXTRA_TITLE,"coh-storage-"+format.format(new Date())+".json");
        try{startActivityForResult(intent,STORAGE_EXPORT);}catch(RuntimeException e){pendingStorageExport=null;Toast.makeText(this,"No export destination is available.",Toast.LENGTH_LONG).show();}
    }
    @Override protected void onActivityResult(int request,int result,Intent data){
        super.onActivityResult(request,result,data);
        if(request==IMPORT){if(result==RESULT_OK&&data!=null&&data.getData()!=null){pendingImport=data.getData();try{getContentResolver().takePersistableUriPermission(pendingImport,Intent.FLAG_GRANT_READ_URI_PERMISSION);}catch(SecurityException ignored){}importWaiting=true;dispatchPendingImport();}return;}
        if(request!=EXPORT&&request!=STORAGE_EXPORT)return;String selected=request==EXPORT?pendingExport:pendingStorageExport;if(request==EXPORT)pendingExport=null;else pendingStorageExport=null;
        if(result!=RESULT_OK||data==null||data.getData()==null||selected==null)return;pendingExportSource=selected;pendingExportDestination=data.getData();dispatchPendingExport();
    }
    private void dispatchPendingExport(){
        if(service==null||pendingExportSource==null||pendingExportDestination==null||exporting)return;
        final ClientService ownerService=service;final String selected=pendingExportSource;final android.net.Uri uri=pendingExportDestination;pendingExportSource=null;pendingExportDestination=null;
        final Object owner;try{owner=ownerService.beginReportExport(new File(selected));}catch(IOException e){Toast.makeText(this,"Wait for the current operation, then export again.",Toast.LENGTH_LONG).show();return;}
        exporting=true;if(state!=null)render(state);
        try{exporter.execute(()->{String message;try(InputStream in=new FileInputStream(selected);OutputStream out=getContentResolver().openOutputStream(uri,"w")){if(out==null)throw new IOException("No export stream");byte[] buffer=new byte[65536];int n;while((n=in.read(buffer))!=-1)out.write(buffer,0,n);message="Report exported";}catch(Exception e){message="Export failed. Try another destination.";}finally{ownerService.endReportExport(owner);}final String finish=message;runOnUiThread(()->{exporting=false;if(state!=null)render(state);Toast.makeText(this,finish,Toast.LENGTH_LONG).show();});});}
        catch(RuntimeException e){ownerService.endReportExport(owner);exporting=false;if(state!=null)render(state);Toast.makeText(this,"Export could not start. Try again.",Toast.LENGTH_LONG).show();}
    }
    @Override protected void onSaveInstanceState(Bundle out){out.putString("export",pendingExport);out.putString("storage_export",pendingStorageExport);out.putString("export_source",pendingExportSource);out.putString("export_destination",pendingExportDestination==null?null:pendingExportDestination.toString());out.putString("action",pendingAction);out.putString("import_uri",pendingImport==null?null:pendingImport.toString());out.putBoolean("import_waiting",importWaiting);super.onSaveInstanceState(out);}
    @Override protected void onDestroy(){if(activeTextDialog!=null)activeTextDialog.dismiss();if(storageDialog!=null)storageDialog.dismiss();exporter.shutdown();super.onDestroy();}
}
