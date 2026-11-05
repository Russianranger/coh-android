package io.github.russianranger.cohclientinteractive;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.res.ColorStateList;
import android.graphics.Canvas;
import android.graphics.ColorFilter;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.PixelFormat;
import android.graphics.Rect;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.RippleDrawable;
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
import io.github.russianranger.cohdiagnostic.AssetPackStore;

/** Bounded touch, keyboard and Thor controller session for initial Atlas gameplay.
 * The game fills the window; launcher options live in a movable gear's overlay menu. */
public final class ClientActivity extends Activity {
    private static final int EXPORT=11,NOTIFY=12,IMPORT=13,STORAGE_EXPORT=14;
    private ClientService service;
    private ClientService.State state;
    private ClientSurface display;
    private TextView status,detail,counter,logs,profileStatus;
    private Button travelZone, recoverReports;
    private TextView zoningStatus;
    private Button setup,importAssets,run,createFresh,resumeCreation,stop,export,storage,finish,typeText,returnGround,saveLogout,captureContact,openTaskContact,captureAcceptedTask,completeTask,captureCompletedTask;
    private Button enterKey,showFps,fps10,fps30,fps60;
    private CheckBox performanceGraphics,prootFastMode,prestartNextZone,trustedBins,gameplay60,idleResidentMaps,sharedServerData,clientSkipServerFolders,clientFolderIndex,clientAudio,sharedHeap;
    private Spinner gpuProfile,clientArchitecture;
    private CursorOverlay cursor;
    private final Handler inputHandler=new Handler(Looper.getMainLooper());
    private final ClientInput.KeyOwners heldKeys=new ClientInput.KeyOwners();
    private final List<Button> movementButtons=new ArrayList<>();
    /** RFB button bits (1 left, 2 middle, 4 right) currently held by the controller. */
    private final Set<Integer> heldButtons=new HashSet<>();
    private boolean inputActive,textDialogVisible,movementSuppressed,deadlineMovementSuppressed;
    private boolean orderedInputRelease;
    private AlertDialog activeTextDialog;
    private final Runnable inputTick=new Runnable(){@Override public void run(){
        refreshDeadlineControls();refreshTestControls();updateCounter();controllerOutput.refresh();inputHandler.postDelayed(this,32);
    }};
    // Saved controller profile (controller.json) and its COH output; capture follows the game view.
    private ControllerManager controller;
    private final ControllerBridge controllerOutput=new ControllerBridge(controllerTarget());
    private boolean controllerCapturing,mappingsOpen;
    // Floating gear and overlay menu (ported from TRASC's ClientActivity).
    private static final String CONTROLS_PREFIX="coh.";
    private FrameLayout controlsHost,menuLayer;
    private LinearLayout menuPanel;
    private ImageButton gear;
    private Button resumeGame;
    private TextView layerBanner;
    private FrameLayout.LayoutParams gearPosition;
    private SharedPreferences controlsPreferences;
    private float controlsX=1f,controlsY;
    private int controlsInsetLeft,controlsInsetTop,controlsInsetRight,controlsInsetBottom;
    private boolean menuOpen,controlsDragging;
    private String menuClosedSession="";
    private ClientOverlayPosition.Drag controlsDrag;
    private final Runnable hideLayer=()->{if(layerBanner!=null)layerBanner.animate().alpha(0f).setDuration(250).start();};
    private boolean bound,exporting,captureEnabled,importWaiting;
    private Button startTest,stopTest;
    private TextView assetPackStatus;
    private boolean assetStatusChecking,assetStatusLoaded,assetStatusDirty;
    private String pendingExport,pendingAction,shownSession="";
    private long pendingStartupUiActionElapsedRealtime = -1;
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
        @Override public void onServiceDisconnected(ComponentName name){releaseControls(true);inputActive=false;refreshMovementControls();display.setInputEnabled(false);finish.setEnabled(false);typeText.setEnabled(false);saveLogout.setEnabled(false);returnGround.setEnabled(false);captureContact.setEnabled(false);disableTaskControls();service=null;refreshPerformanceControls();setup.setEnabled(false);importAssets.setEnabled(false);run.setEnabled(false);createFresh.setEnabled(false);resumeCreation.setEnabled(false);stop.setEnabled(false);status.setText("Service disconnected");detail.setText("Reopen this screen to reconnect.");refreshOverlayMenu();}
    };
    @Override public void onCreate(Bundle saved){
        super.onCreate(saved);getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        if(saved!=null){pendingExport=saved.getString("export");pendingStorageExport=saved.getString("storage_export");pendingExportSource=saved.getString("export_source");String destination=saved.getString("export_destination");if(destination!=null)pendingExportDestination=android.net.Uri.parse(destination);pendingAction=saved.getString("action");importWaiting=saved.getBoolean("import_waiting",false);String selected=saved.getString("import_uri");if(selected!=null)pendingImport=android.net.Uri.parse(selected);}
        // The 800x600 client is aspect-fitted into the whole window. The former sidebar's
        // controls are unchanged inside the gear's scrolling menu panel.
        FrameLayout root=new FrameLayout(this);root.setBackgroundColor(Color.BLACK);controlsHost=root;
        controlsPreferences=getSharedPreferences("client-controls",MODE_PRIVATE);
        controlsX=ClientOverlayPosition.normalized(controlsPreferences.getFloat(CONTROLS_PREFIX+"x",1f),1f);
        controlsY=ClientOverlayPosition.normalized(controlsPreferences.getFloat(CONTROLS_PREFIX+"y",0f),0f);
        controlsDrag=new ClientOverlayPosition.Drag(ViewConfiguration.get(this).getScaledTouchSlop());
        display=new ClientSurface(this);root.addView(display,new FrameLayout.LayoutParams(-1,-1));
        cursor=new CursorOverlay();root.addView(cursor,new FrameLayout.LayoutParams(-1,-1));
        // A separate overlay never changes the client's size or touch map.
        menuLayer=new FrameLayout(this);menuLayer.setVisibility(View.GONE);menuLayer.setOnClickListener(v->setMenuOpen(false));
        root.addView(menuLayer,new FrameLayout.LayoutParams(-1,-1));
        LinearLayout controls=new LinearLayout(this);controls.setOrientation(LinearLayout.VERTICAL);controls.setPadding(dp(12),dp(8),dp(12),dp(12));
        controls.setBackground(panelBackground(0xf0091320));controls.setOnClickListener(v->{});menuPanel=controls;
        ScrollView scroll=new ScrollView(this);scroll.addView(controls);
        final FrameLayout.LayoutParams panel=new FrameLayout.LayoutParams(dp(300),-2,Gravity.TOP|Gravity.RIGHT);
        panel.setMargins(dp(12),dp(68),dp(12),dp(12));menuLayer.addView(scroll,panel);
        TextView title=text("COH Atlas Gameplay",22,true);controls.addView(title);
        String version="unknown";
        try{version=getPackageManager().getPackageInfo(getPackageName(),0).versionName;}catch(PackageManager.NameNotFoundException ignored){}
        controls.addView(text("Persistent local server · v"+version,12,false));
        resumeGame=button("Resume game",()->setMenuOpen(false));resumeGame.setEnabled(false);controls.addView(resumeGame);
        controls.addView(button("Controller mappings",this::controllerDialog));
        controls.addView(text("Default controller: Left stick: WASD · X: jump · Right stick: cursor · A: click/talk · B: Esc · Shoulders: right click / turn view · D-pad: arrows · L3: text · Start: Enter. Triggers are unbound. The COH power trays preset adds hold LT for 1–0 and Select for this menu; Back or the gear also opens it.",12,false));
        controls.addView(button("Move options button",this::controlsPositionDialog));
        controls.addView(button("Reset options button position",()->{controlsX=1f;controlsY=0f;positionControls();saveControlsPosition();}));
        controls.addView(text("Reopen THORHERO and test the Atlas Park–Kings Row monorail. Keep the accepted graphics settings, costume and powers.",13,false));
        setup=button("Set up / update runtime",()->request(ClientService.SETUP));controls.addView(setup);
        importAssets=button("Import asset pack part",this::chooseImport);controls.addView(importAssets);
        assetPackStatus=text("Checking required asset pack…",12,false);controls.addView(assetPackStatus);
        controls.addView(text("Fresh install: import every ZIP part from the compatible versioned Assets release, then Set up / update runtime. Each completed part is retained; the app shows any missing parts. Keep these ZIPs for reinstalling. Future APK updates reuse compatible imported assets.",12,false));
        performanceGraphics=new CheckBox(this);performanceGraphics.setText("Use performance graphics");
        performanceGraphics.setTextColor(Color.rgb(221,234,245));performanceGraphics.setTextSize(13);
        performanceGraphics.setChecked(ClientRuntime.performanceGraphicsEnabled(this));
        performanceGraphics.setOnCheckedChangeListener((button,checked)->ClientRuntime.setPerformanceGraphicsEnabled(this,checked));
        controls.addView(performanceGraphics);
        prootFastMode=new CheckBox(this);prootFastMode.setText("Fast mode (PRoot seccomp, experimental)");
        prootFastMode.setTextColor(Color.rgb(221,234,245));prootFastMode.setTextSize(13);
        prootFastMode.setChecked(ClientRuntime.prootFastModeEnabled(this));
        prootFastMode.setOnCheckedChangeListener((button,checked)->ClientRuntime.setProotFastModeEnabled(this,checked));
        controls.addView(prootFastMode);
        prestartNextZone=new CheckBox(this);prestartNextZone.setText("Start King's Row in the background (zoning)");
        prestartNextZone.setTextColor(Color.rgb(221,234,245));prestartNextZone.setTextSize(13);
        prestartNextZone.setChecked(ClientRuntime.prestartNextZoneEnabled(this));
        prestartNextZone.setOnCheckedChangeListener((button,checked)->ClientRuntime.setPrestartNextZoneEnabled(this,checked));
        controls.addView(prestartNextZone);
        idleResidentMaps=new CheckBox(this);idleResidentMaps.setText("Lower the waiting zone server's priority (zoning, experimental)");
        idleResidentMaps.setTextColor(Color.rgb(221,234,245));idleResidentMaps.setTextSize(13);
        idleResidentMaps.setChecked(ClientRuntime.idleResidentMapsEnabled(this));
        idleResidentMaps.setOnCheckedChangeListener((button,checked)->ClientRuntime.setIdleResidentMapsEnabled(this,checked));
        controls.addView(idleResidentMaps);
        sharedServerData=new CheckBox(this);sharedServerData.setText("Share server data between zones (faster zone preparation)");
        sharedServerData.setTextColor(Color.rgb(221,234,245));sharedServerData.setTextSize(13);
        sharedServerData.setChecked(ClientRuntime.sharedServerDataEnabled(this));
        sharedServerData.setOnCheckedChangeListener((button,checked)->ClientRuntime.setSharedServerDataEnabled(this,checked));
        controls.addView(sharedServerData);
        clientSkipServerFolders=new CheckBox(this);clientSkipServerFolders.setText("Skip server-only folders in the client's file scan (faster client start)");
        clientSkipServerFolders.setTextColor(Color.rgb(221,234,245));clientSkipServerFolders.setTextSize(13);
        clientSkipServerFolders.setChecked(ClientRuntime.clientSkipServerFoldersEnabled(this));
        clientSkipServerFolders.setOnCheckedChangeListener((button,checked)->ClientRuntime.setClientSkipServerFoldersEnabled(this,checked));
        controls.addView(clientSkipServerFolders);
        clientFolderIndex=new CheckBox(this);clientFolderIndex.setText("Reuse the client's saved file list while the data is unchanged (faster client start)");
        clientFolderIndex.setTextColor(Color.rgb(221,234,245));clientFolderIndex.setTextSize(13);
        clientFolderIndex.setChecked(ClientRuntime.clientFolderIndexEnabled(this));
        clientFolderIndex.setOnCheckedChangeListener((button,checked)->ClientRuntime.setClientFolderIndexEnabled(this,checked));
        controls.addView(clientFolderIndex);
        clientAudio=new CheckBox(this);clientAudio.setText("Game audio (sound and music through Android)");
        clientAudio.setTextColor(Color.rgb(221,234,245));clientAudio.setTextSize(13);
        clientAudio.setChecked(ClientRuntime.clientAudioEnabled(this));
        clientAudio.setOnCheckedChangeListener((button,checked)->ClientRuntime.setClientAudioEnabled(this,checked));
        controls.addView(clientAudio);
        sharedHeap=new CheckBox(this);sharedHeap.setText("Shared server memory (experiment: zone servers share game data)");
        sharedHeap.setTextColor(Color.rgb(221,234,245));sharedHeap.setTextSize(13);
        sharedHeap.setChecked(ClientRuntime.sharedHeapEnabled(this));
        sharedHeap.setOnCheckedChangeListener((button,checked)->ClientRuntime.setSharedHeapEnabled(this,checked));
        controls.addView(sharedHeap);
        trustedBins=new CheckBox(this);trustedBins.setText("Fast server start (test server with trusted bins)");
        trustedBins.setTextColor(Color.rgb(221,234,245));trustedBins.setTextSize(13);
        trustedBins.setChecked(ClientRuntime.trustedBinsEnabled(this));
        trustedBins.setOnCheckedChangeListener((button,checked)->ClientRuntime.setTrustedBinsEnabled(this,checked));
        controls.addView(trustedBins);
        gameplay60=new CheckBox(this);gameplay60.setText("Raise the frame cap to 60 FPS in the world");
        gameplay60.setTextColor(Color.rgb(221,234,245));gameplay60.setTextSize(13);
        gameplay60.setChecked(ClientRuntime.gameplay60FpsEnabled(this));
        gameplay60.setOnCheckedChangeListener((button,checked)->ClientRuntime.setGameplay60FpsEnabled(this,checked));
        controls.addView(gameplay60);
        controls.addView(text("Lower detail and effects; 600×450 world with the same 800×600 interface. Turn off before launch to use your saved graphics settings.",12,false));
        controls.addView(text("Client for next launch",12,true));
        clientArchitecture=new Spinner(this);
        clientArchitecture.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,
                new String[]{"x86 client (fallback)", "ARM64 client"}));
        clientArchitecture.setSelection("arm64".equals(ClientRuntime.clientArchitecture(this))?1:0);
        clientArchitecture.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){
            @Override public void onItemSelected(AdapterView<?> parent,View view,int position,long id){
                if(clientArchitecture.isEnabled())ClientRuntime.setClientArchitecture(ClientActivity.this,position==1?"arm64":"x86");
            }
            @Override public void onNothingSelected(AdapterView<?> parent){}
        });
        controls.addView(clientArchitecture);
        controls.addView(text("ARM64 uses standard graphics and the renderer selected below (GPU test falls back to Software if its checks fail). Saved-character reopen and supported monorail travel are available; ARM64 remains experimental.",12,false));
        controls.addView(text("Renderer for next launch",12,true));
        gpuProfile=new Spinner(this);
        ArrayAdapter<String> gpuChoices=new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,
                new String[]{"Software (current)","GPU test"});
        gpuProfile.setAdapter(gpuChoices);
        gpuProfile.setSelection("turnip".equals(ClientRuntime.gpuProfileEnabled(this))?1:0);
        gpuProfile.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){
            @Override public void onItemSelected(AdapterView<?> parent,View view,int position,long id){
                if(gpuProfile.isEnabled())ClientRuntime.setGpuProfileEnabled(ClientActivity.this,position==1?"turnip":"software");
            }
            @Override public void onNothingSelected(AdapterView<?> parent){}
        });
        controls.addView(gpuProfile);
        controls.addView(text("GPU test checks the private driver before launch. If unavailable, it starts with Software and records the reason. Change this after finishing a run.",12,false));
        run=button("2 · Reopen saved THORHERO",()->request(ClientService.RUN));controls.addView(run);
        createFresh=button("Create fresh THORHERO",this::confirmFreshProfile);createFresh.setVisibility(View.GONE);controls.addView(createFresh);
        resumeCreation=button("Resume first character creation",this::confirmResumeCreation);resumeCreation.setVisibility(View.GONE);controls.addView(resumeCreation);
        profileStatus=text("Checking saved character profile…",12,false);controls.addView(profileStatus);
        returnGround=button("Return to safe ground (optional)",()->{releaseControls();if(service!=null)service.requestReturnToSafeGround();});controls.addView(returnGround);
        startTest=button("Start test",()->{if(service!=null)service.startManualTest();});controls.addView(startTest);
        stopTest=button("Stop test",()->{if(service!=null)service.stopManualTest();});controls.addView(stopTest);
        captureContact=button("Capture contact dialog",()->{releaseControls();if(service!=null)service.requestContactCapture();});controls.addView(captureContact);
        openTaskContact=button("Open task contact",()->{releaseControls();if(service!=null)service.requestOpenTaskContact();});controls.addView(openTaskContact);
        captureAcceptedTask=button("Capture accepted task",()->{releaseControls();if(service!=null)service.requestTaskCapture(false);});controls.addView(captureAcceptedTask);
        completeTask=button("Complete accepted task",()->{releaseControls();if(service!=null)service.requestCompleteAcceptedTask();});controls.addView(completeTask);
        captureCompletedTask=button("Capture completed task",()->{releaseControls();if(service!=null)service.requestTaskCapture(true);});controls.addView(captureCompletedTask);
        controls.addView(text("Monorail travel",16,true));
        controls.addView(text("Walk to the monorail station in Atlas Park, click its entrance and choose Kings Row. The destination prepares automatically before boarding. Use the Kings Row station to return to Atlas Park. Stay in this app until arrival; loading time includes preparation and fresh destination views.",12,false));
        zoningStatus=text("Reopen THORHERO to use the monorail.",12,false);controls.addView(zoningStatus);
        travelZone=button("Return from old Atlas instance",this::travelToZone);travelZone.setVisibility(View.GONE);controls.addView(travelZone);
        saveLogout=button("Save character / log out",this::saveCharacter);controls.addView(saveLogout);
        finish=button("Finish and save report",()->{releaseControls();if(service!=null)service.requestFinish();});controls.addView(finish);
        typeText=button("Send text / L3",this::showTextInput);controls.addView(typeText);
        enterKey=button("Enter / Start",this::sendEnter);controls.addView(enterKey);
        showFps=button("Show FPS",()->sendPerformanceCommand(ClientInput.PerformanceCommand.SHOW_FPS));controls.addView(showFps);
        LinearLayout fpsRow=new LinearLayout(this);
        fps10=button("10 FPS",()->sendPerformanceCommand(ClientInput.PerformanceCommand.FPS_10));
        fps30=button("30 FPS",()->sendPerformanceCommand(ClientInput.PerformanceCommand.FPS_30));
        fps60=button("60 FPS",()->sendPerformanceCommand(ClientInput.PerformanceCommand.FPS_60));
        fpsRow.addView(fps10,new LinearLayout.LayoutParams(0,-2,1));
        fpsRow.addView(fps30,new LinearLayout.LayoutParams(0,-2,1));
        fpsRow.addView(fps60,new LinearLayout.LayoutParams(0,-2,1));controls.addView(fpsRow);
        controls.addView(text("Atlas movement · hold a button",12,true));
        addMovementRow(controls,"Forward",'w',"Back",'s',120001);
        addMovementRow(controls,"Left",'a',"Right",'d',120003);
        controls.addView(movementButton("Jump",' ',120005));
        stop=button("Abort operation",()->{movementSuppressed=true;releaseControls();refreshMovementControls();if(service!=null)startService(new Intent(this,ClientService.class).setAction(ClientService.STOP));});controls.addView(stop);
        export=button("Reports / export",this::chooseExport);controls.addView(export);
        recoverReports=button("Recover interrupted reports",()->{if(service!=null)startForegroundService(new Intent(this,ClientService.class).setAction(ClientService.RECOVER_REPORTS));});controls.addView(recoverReports);
        storage=button("Storage and cleanup",this::showStorage);controls.addView(storage);
        status=text("Connecting",17,true);controls.addView(status);
        detail=text("Connecting to the private runtime service…",13,false);controls.addView(detail);
        counter=text("Waiting for the client",12,false);controls.addView(counter);
        controls.addView(text("Import every required asset-pack part, then apply Set up / update runtime. On a fresh install, create THORHERO and complete its ordinary save before Reopen. Use COHLOCAL / offline. Keep the accepted GPU, Performance and 800×600 settings. Reopen starts in THORHERO's saved destination. Use the actual monorail when ready to travel; preparation happens on demand. Tap Start test when ready and Stop test when finished; neither starts a countdown. When ready to save, release controls, Save character / log out, wait for Saved character verified, then Finish and Reports / export. Recover interrupted reports after an interruption. Export early if loading stalls; Reopen resumes the last verified save.",12,false));
        logs=text("",10,false);logs.setTypeface(Typeface.MONOSPACE);logs.setTextIsSelectable(true);controls.addView(logs);
        display.setInputListener(new ClientSurface.InputListener(){
            @Override public void onPointer(String session,int x,int y,int buttons){if(service!=null)service.sendPointer(session,x,y,buttons);}
            @Override public void onReleaseAll(String session){resetLocalInputs();releaseRemoteInputs(session,!orderedInputRelease&&!textDialogVisible&&!movementSuppressed&&!commandInputBusy());}
            @Override public void onCursor(float x,float y,boolean visible){cursor.move(x,y,visible);}
            @Override public void onWheel(String session,int x,int y,boolean up){if(service!=null)service.sendWheel(session,x,y,up);}
        });
        buildOverlay(root,scroll,panel);
        controller=new ControllerManager(this,new File(getFilesDir(),ControllerProfile.FILE_NAME),controllerOutput);
        if(!controller.loadError().isEmpty())Toast.makeText(this,controller.loadError()+" · using the default bindings",Toast.LENGTH_LONG).show();

        startTest.setEnabled(false);stopTest.setEnabled(false);setContentView(root);root.requestApplyInsets();immersive();setMenuOpen(true);setup.setEnabled(false);importAssets.setEnabled(false);run.setEnabled(false);createFresh.setEnabled(false);resumeCreation.setEnabled(false);stop.setEnabled(false);export.setEnabled(false);storage.setEnabled(false);finish.setEnabled(false);typeText.setEnabled(false);saveLogout.setEnabled(false);returnGround.setEnabled(false);captureContact.setEnabled(false);disableTaskControls();refreshMovementControls();refreshPerformanceControls();
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
    private boolean canWalk(){return inputActive&&service!=null&&state!=null&&state.canSaveLogout&&!state.characterSaved&&!movementSuppressed&&!textDialogVisible&&!commandInputBusy()&&hasWindowFocus()&&movementWindowOpen();}
    private boolean movementWindowOpen(){return state!=null&&(state.movementDeadlineUptimeMillis==0||SystemClock.uptimeMillis()<state.movementDeadlineUptimeMillis);}
    private boolean commandInputBusy(){return service!=null&&service.isPerformanceCommandPending();}
    private boolean gameInputOpen(){return inputActive&&movementWindowOpen()&&!movementSuppressed&&!commandInputBusy();}
    private boolean ownedInputOpen(){return gameInputOpen()&&service!=null&&state!=null
            &&state.busy&&state.inputReady&&!state.finishing&&!state.blocked&&!state.characterSaved
            &&!shownSession.isEmpty()&&shownSession.equals(state.session)&&!textDialogVisible&&hasWindowFocus();}
    private boolean canSendPerformanceCommand(){return ownedInputOpen()
            &&("connected".equals(state.sessionPhase)||"grounded".equals(state.sessionPhase))
            &&service.canSendPerformanceCommand();}
    private void refreshPerformanceControls(){
        refreshZoningControls();
        boolean available=canSendPerformanceCommand();
        if(showFps!=null)showFps.setEnabled(available);
        if(fps10!=null)fps10.setEnabled(available);
        if(fps30!=null)fps30.setEnabled(available);
        if(fps60!=null)fps60.setEnabled(available);
        if(enterKey!=null)enterKey.setEnabled(ownedInputOpen());
    }
    private void refreshZoningControls(){
        boolean available=inputActive&&service!=null&&state!=null&&!textDialogVisible&&hasWindowFocus();
        if(zoningStatus!=null)setTextIfChanged(zoningStatus,service==null?"Reopen THORHERO to use the monorail.":service.zoningStatus());
        if(travelZone!=null){
            boolean legacy=service!=null&&service.zoningCurrentMap()==101;
            travelZone.setVisibility(legacy?View.VISIBLE:View.GONE);
            travelZone.setEnabled(available&&legacy&&service.canRequestZoning());travelZone.setText("Return from old Atlas instance");
        }
    }
    private void travelToZone(){
        if(service==null||!service.canRequestZoning()||textDialogVisible||!hasWindowFocus())return;
        releaseControls(true);
        if(!service.requestZoning())Toast.makeText(this,"Travel is unavailable while the current operation finishes.",Toast.LENGTH_SHORT).show();
        refreshMovementControls();refreshDeadlineControls();
    }
    private void sendPerformanceCommand(ClientInput.PerformanceCommand command){
        if(command==null||!canSendPerformanceCommand())return;
        releaseControls(true);
        if(!service.requestPerformanceCommand(command))
            Toast.makeText(this,"Wait for world input to be ready, then retry.",Toast.LENGTH_SHORT).show();
        refreshMovementControls();refreshDeadlineControls();
    }
    private void sendEnter(){
        if(!ownedInputOpen())return;
        // Keep a preceding field tap or Send Text transaction ahead of Enter.
        releaseControls(false);
        if(!service.requestEnter())
            Toast.makeText(this,"Enter was not queued. Wait for input ready and retry.",Toast.LENGTH_SHORT).show();
    }
    private void disableTaskControls(){openTaskContact.setEnabled(false);captureAcceptedTask.setEnabled(false);completeTask.setEnabled(false);captureCompletedTask.setEnabled(false);}
    private void refreshDeadlineControls(){
        if(captureContact!=null)captureContact.setEnabled(inputActive&&service!=null&&state!=null
                &&state.canSaveLogout&&!state.characterSaved&&!textDialogVisible&&!commandInputBusy()&&hasWindowFocus()
                &&movementWindowOpen()&&service.canCaptureContact());
        boolean taskAvailable=inputActive&&service!=null&&state!=null&&state.canSaveLogout&&!state.characterSaved
                &&!textDialogVisible&&!commandInputBusy()&&hasWindowFocus()&&movementWindowOpen();
        if(openTaskContact!=null)openTaskContact.setEnabled(taskAvailable&&service.canOpenTaskContact());
        if(captureAcceptedTask!=null)captureAcceptedTask.setEnabled(taskAvailable&&service.canCaptureTask(false));
        if(completeTask!=null)completeTask.setEnabled(taskAvailable&&service.canCompleteAcceptedTask());
        if(captureCompletedTask!=null)captureCompletedTask.setEnabled(taskAvailable&&service.canCaptureTask(true));
        refreshPerformanceControls();
        if(state==null)return;
        if(!movementWindowOpen()&&!deadlineMovementSuppressed){deadlineMovementSuppressed=true;releaseControls(!movementSuppressed);refreshMovementControls();}
        display.setInputEnabled(gameInputOpen());typeText.setEnabled(gameInputOpen());
        saveLogout.setEnabled(inputActive&&!commandInputBusy()&&state.canSaveLogout&&service!=null&&service.canRequestSaveLogout()
                &&(state.saveDeadlineUptimeMillis==0||SystemClock.uptimeMillis()<state.saveDeadlineUptimeMillis));
    }
    private void refreshMovementControls(){
        boolean enabled=canWalk();
        if(!enabled)for(int owner=120001;owner<=120005;owner++)releaseKey(owner);
        // Controller walking keys and jump follow the same gate (see ControllerBridge.refresh).
        controllerOutput.refresh();
        for(Button b:movementButtons){b.setEnabled(enabled);if(!enabled)b.setPressed(false);}
        refreshControllerCapture();
    }
    private void saveCharacter(){
        if(commandInputBusy())return;
        boolean before=movementSuppressed;movementSuppressed=true;releaseControls();refreshMovementControls();
        if(service==null||!service.requestSaveLogout()){movementSuppressed=before;refreshMovementControls();}
    }
    private int dp(int value){return Math.round(value*getResources().getDisplayMetrics().density);}
    @Override protected void onStart(){super.onStart();inputHandler.post(inputTick);bound=bindService(new Intent(this,ClientService.class),connection,BIND_AUTO_CREATE);}
    @Override protected void onStop(){inputHandler.removeCallbacks(inputTick);cancelControlsGesture();releaseControls(true);stopControllerCapture();display.setInputEnabled(false);inputActive=false;display.setCaptureListener(null);captureEnabled=false;if(service!=null){service.setUiVisible(false);service.removeListener(listener);}service=null;if(bound){unbindService(connection);bound=false;}super.onStop();}
    private boolean profileIdle(ClientService.State next){
        return next!=null&&service!=null&&!next.busy&&!next.storageBusy&&!next.reportExporting
                &&!next.blocked&&!exporting&&!ClientRuntime.operationInProgress();
    }
    private boolean canCreateFreshProfile(ClientService.State next){
        return profileIdle(next)&&next.profileState==ClientRuntime.ProfileState.ABSENT;
    }
    private boolean canResumeFirstCreation(ClientService.State next){
        return profileIdle(next)&&next.profileState==ClientRuntime.ProfileState.READY;
    }
    private void refreshProfileControls(ClientService.State next){
        run.setEnabled(profileIdle(next)&&next.profileState==ClientRuntime.ProfileState.READY);
        createFresh.setVisibility(next.profileState==ClientRuntime.ProfileState.ABSENT?View.VISIBLE:View.GONE);
        createFresh.setEnabled(canCreateFreshProfile(next));
        resumeCreation.setVisibility(next.profileState==ClientRuntime.ProfileState.READY?View.VISIBLE:View.GONE);
        resumeCreation.setEnabled(canResumeFirstCreation(next));
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
    private void confirmResumeCreation(){
        if(!canResumeFirstCreation(state))return;
        new AlertDialog.Builder(this).setTitle("Resume first character creation?")
                .setMessage("Continue the first creation attempt using the existing initialized profile and imported assets. The database is preserved. Startup checks its real character rows; any existing character makes this request stop before the game opens. If THORHERO was already saved, use Reopen saved THORHERO. Log in with COHLOCAL / offline, create THORHERO, then Save character / log out and Finish and export.")
                .setNegativeButton("Cancel",null).setPositiveButton("Resume first creation",(dialog,which)->{
                    if(canResumeFirstCreation(state))request(ClientService.RESUME_FIRST_CREATION);
                }).show();
    }
    private void refreshAbortControl(ClientService.State next){
        stop.setEnabled(next.busy||next.storageBusy);
        stop.setText(next.storageBusy?"Cancel storage scan / cleanup":"Abort operation");
    }
    private void render(ClientService.State next){
        if(next.busy)assetStatusDirty=true;
        if(!next.busy&&!next.storageBusy&&!assetStatusChecking&&(!assetStatusLoaded||assetStatusDirty))refreshAssetPackStatus();
        if(next.busy&&next.session.isEmpty())display.clearFrames();
        state=next;refreshTestControls();setTextIfChanged(status,next.stage);setTextIfChanged(detail,next.detail);setTextIfChanged(logs,next.log);updateCounter();
        recoverReports.setEnabled(!next.busy&&!next.storageBusy&&!next.reportExporting&&!ClientRuntime.operationInProgress());
        boolean diagnostics=diagnosticControlsReady(next,service!=null,exporting,ClientRuntime.operationInProgress());
        boolean idle=diagnostics&&!next.blocked;setup.setEnabled(idle);importAssets.setEnabled(idle);refreshProfileControls(next);performanceGraphics.setEnabled(idle);prootFastMode.setEnabled(idle);prestartNextZone.setEnabled(idle);trustedBins.setEnabled(idle);gameplay60.setEnabled(idle);idleResidentMaps.setEnabled(idle);sharedServerData.setEnabled(idle);clientSkipServerFolders.setEnabled(idle);clientFolderIndex.setEnabled(idle);clientAudio.setEnabled(idle);sharedHeap.setEnabled(idle);gpuProfile.setEnabled(idle);clientArchitecture.setEnabled(idle);storage.setEnabled(diagnostics);refreshAbortControl(next);export.setEnabled(diagnostics);
        if(next.storageBusy){setTextIfChanged(status,"Storage");setTextIfChanged(detail,next.storageStatus);}
        if(storageDialogRequested&&diagnostics){storageDialogRequested=false;showStorage();}
        if(!next.session.isEmpty()&&!next.session.equals(shownSession)){releaseControls();shownSession=next.session;movementSuppressed=false;deadlineMovementSuppressed=false;display.setSession(shownSession);}
        boolean enabled=next.busy&&next.inputReady&&!next.finishing&&!next.blocked;
        if(inputActive&&!enabled)releaseControls();inputActive=enabled;display.setInputEnabled(enabled);
        finish.setEnabled(enabled&&next.characterSaved);typeText.setEnabled(enabled);returnGround.setEnabled(enabled&&next.canReturnGround);saveLogout.setEnabled(enabled&&next.canSaveLogout&&service!=null&&service.canRequestSaveLogout());
        refreshMovementControls();refreshDeadlineControls();refreshOverlayMenu();
    }
    private void setTextIfChanged(TextView view,String value){if(!android.text.TextUtils.equals(view.getText(),value))view.setText(value);}
    /** Failed-session diagnostics stay accessible; live ownership still excludes file work. */
    static boolean diagnosticControlsReady(ClientService.State state,boolean serviceAvailable,boolean exporting,boolean operationOwned){
        return state!=null&&serviceAvailable&&!state.busy&&!state.storageBusy&&!state.reportExporting&&!exporting&&!operationOwned;
    }
    private void refreshTestControls(){
        boolean available=service!=null&&state!=null&&state.busy;
        if(startTest!=null)startTest.setEnabled(available&&service.canStartManualTest());
        if(stopTest!=null)stopTest.setEnabled(available&&service.manualTestActive());
        boolean capture=available&&service.needsSurfaceCapture();
        if(capture!=captureEnabled){captureEnabled=capture;display.setCaptureListener(capture?captureListener:null);}
    }
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
            }else timing="\n"+("connected".equals(state.sessionPhase)?"Character connected":"Login window")+" · "+(state.readyDeadlineUptimeMillis==0?"No countdown":remaining+"s remaining");
        }
        setTextIfChanged(counter,"Android captures: "+state.certified+" · Inputs sent: "+state.inputSent
                +(state.inputFailed>0?" · Input failures: "+state.inputFailed:"")+timing
                +(service!=null&&service.manualTestActive()?"\nTest capture active · tap Stop test when finished":""));
    }
    private void showTextInput(){
        if(!gameInputOpen()||service==null||textDialogVisible)return;
        final String targetSession=shownSession;
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
                    if(!inputActive||service==null||!targetSession.equals(shownSession))return;
                    boolean queued=service.sendText(targetSession,value,replace.isChecked());
                    if(!queued){service.releaseAllInputs(targetSession);Toast.makeText(this,"Text was not queued. Wait for input ready and retry.",Toast.LENGTH_SHORT).show();}
                    else Toast.makeText(this,"Sending text. Check the game field before pressing Enter.",Toast.LENGTH_SHORT).show();
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
        heldKeys.clear();heldButtons.clear();for(Button b:movementButtons)b.setPressed(false);
    }
    private void releaseControls(boolean discardPending){
        resetLocalInputs();
        // Surface callbacks must preserve the same ordering decision as their
        // caller, especially Enter after a still-running text transaction.
        boolean previous=orderedInputRelease;orderedInputRelease=previous||!discardPending;
        try{if(display!=null)display.releaseInput();}finally{orderedInputRelease=previous;}
        releaseRemoteInputs(shownSession,discardPending);
    }
    @Override public void onWindowFocusChanged(boolean focus){super.onWindowFocusChanged(focus);if(!focus){cancelControlsGesture();releaseControls();}else if(!textDialogVisible)immersive();refreshMovementControls();refreshPerformanceControls();}
    @Override public boolean dispatchKeyEvent(KeyEvent event){
        // The first controller follows the saved profile (default: the earlier fixed mapping).
        if(controllerKey(event))return true;
        // The open overlay menu suspends game keys; Back toggles the menu.
        if(menuOpen||!gameInputOpen()||textDialogVisible||service==null)return super.dispatchKeyEvent(event);
        int code=event.getKeyCode();boolean down=event.getAction()==KeyEvent.ACTION_DOWN;
        if(event.getAction()!=KeyEvent.ACTION_DOWN&&event.getAction()!=KeyEvent.ACTION_UP)return super.dispatchKeyEvent(event);
        boolean gamepad=(event.getSource()&InputDevice.SOURCE_GAMEPAD)==InputDevice.SOURCE_GAMEPAD;
        int keysym=0;
        switch(code){
            case KeyEvent.KEYCODE_DPAD_LEFT:keysym=0xff51;break;case KeyEvent.KEYCODE_DPAD_UP:keysym=0xff52;break;
            case KeyEvent.KEYCODE_DPAD_RIGHT:keysym=0xff53;break;case KeyEvent.KEYCODE_DPAD_DOWN:keysym=0xff54;break;
            case KeyEvent.KEYCODE_ESCAPE:case KeyEvent.KEYCODE_BUTTON_B:keysym=0xff1b;break;
            case KeyEvent.KEYCODE_ENTER:case KeyEvent.KEYCODE_NUMPAD_ENTER:keysym=ClientInput.RETURN_KEY;break;
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
    @Override public boolean dispatchGenericMotionEvent(MotionEvent event){
        if(controllerCapturing&&controller!=null&&controller.motion(event))return true;
        return super.dispatchGenericMotionEvent(event);
    }
    @Override public void onBackPressed(){
        if(!menuOpen){setMenuOpen(true);return;}
        if(gameSessionRunning()){setMenuOpen(false);return;}
        super.onBackPressed();
    }
    /** ControllerInput outputs for COH: today's key owners, Surface buttons/cursor and the wheel. */
    private ControllerBridge.Target controllerTarget(){return new ControllerBridge.Target(){
        @Override public boolean keysOpen(){return gameInputOpen()&&!textDialogVisible&&service!=null;}
        @Override public boolean walkOpen(){return canWalk();}
        @Override public boolean holds(int owner){return heldKeys.contains(owner);}
        @Override public void press(int owner,int keysym){pressKey(owner,keysym);}
        @Override public void release(int owner){releaseKey(owner);}
        @Override public void mouse(int button,boolean down){
            if(down)heldButtons.add(button);else heldButtons.remove(button);
            int mask=0;for(int held:heldButtons)mask|=held&7;
            display.setControllerButtons(mask);
        }
        @Override public void pointer(float dx,float dy){if(gameInputOpen()&&hasWindowFocus()&&!textDialogVisible)display.movePointer(dx,dy);}
        @Override public void wheel(int amount){if(gameInputOpen()&&hasWindowFocus()&&!textDialogVisible)display.wheel(amount);}
        @Override public void command(String action){controllerCommand(action);}
        @Override public void layer(int index,String name){showLayer(index,name);}
    };}
    private void controllerCommand(String action){
        if("ClientMenu".equals(action))setMenuOpen(true);
        else if("TextEntry".equals(action))showTextInput();
        else if("SendEnter".equals(action)&&ownedInputOpen())sendEnter();
    }
    /** Capture only while the game view is in front: no menu, dialog or gear drag. */
    private boolean controllerCaptures(){return hasWindowFocus()&&!menuOpen&&!textDialogVisible&&!mappingsOpen&&!controlsDragging;}
    private void refreshControllerCapture(){
        boolean capture=controllerCaptures();
        if(capture==controllerCapturing)return;
        controllerCapturing=capture;if(controller!=null)controller.capture(capture);
    }
    private void stopControllerCapture(){if(controllerCapturing){controllerCapturing=false;if(controller!=null)controller.capture(false);}}
    private boolean controllerKey(KeyEvent event){return controllerCapturing&&controller!=null&&controller.key(event);}
    private void controllerDialog(){
        if(controller==null||mappingsOpen)return;
        mappingsOpen=true;refreshControllerCapture();
        try{new ControllerDialog(this,controller,()->{mappingsOpen=false;refreshControllerCapture();if(hasWindowFocus())immersive();}).show();}
        catch(RuntimeException failure){mappingsOpen=false;refreshControllerCapture();Toast.makeText(this,"Could not open controller mappings.",Toast.LENGTH_SHORT).show();}
    }
    private void showLayer(int index,String name){
        if(layerBanner==null||controller==null||controller.layerCount()<2)return;
        inputHandler.removeCallbacks(hideLayer);layerBanner.animate().cancel();layerBanner.setText("Layer "+(index+1)+" · "+name);layerBanner.setAlpha(1f);
        inputHandler.postDelayed(hideLayer,1500);
    }

    /** True while a client session can show frames; otherwise the menu stays open as the launcher. */
    private boolean gameSessionRunning(){return service!=null&&state!=null&&state.busy&&!state.session.isEmpty();}
    /** Close the menu once when a session's input first opens; reopen it when the session ends. */
    private void refreshOverlayMenu(){
        boolean running=gameSessionRunning();
        if(running&&inputActive&&!shownSession.isEmpty()&&!shownSession.equals(menuClosedSession)){menuClosedSession=shownSession;setMenuOpen(false);}
        else if(!running&&!menuOpen)setMenuOpen(true);
        if(resumeGame!=null)resumeGame.setEnabled(running);
    }
    private void setMenuOpen(boolean open){
        if(!open&&!gameSessionRunning())open=true;
        boolean changed=open!=menuOpen;menuOpen=open;
        if(menuLayer!=null)menuLayer.setVisibility(open?View.VISIBLE:View.GONE);
        if(gear!=null){gear.setContentDescription((open?"Close options":"Open options")+". Drag to move.");gear.setAlpha(open?1f:.78f);}
        if(resumeGame!=null)resumeGame.setEnabled(gameSessionRunning());
        // Opening releases held game input in order (a queued field tap still lands first).
        if(open&&changed)releaseControls(false);
        refreshControllerCapture();
        if(open&&changed&&menuPanel!=null){if(resumeGame!=null&&resumeGame.isEnabled())resumeGame.requestFocus();else menuPanel.requestFocus();}
        else if(!open&&changed&&display!=null)display.requestFocus();
    }
    private void buildOverlay(FrameLayout root,ScrollView scroll,FrameLayout.LayoutParams panel){
        gear=new ImageButton(this);gear.setImageDrawable(new GearDrawable(dp(24)));gear.setPadding(dp(12),dp(12),dp(12),dp(12));
        gear.setContentDescription("Open options. Drag to move.");gear.setTooltipText("Options · drag to move");
        gear.setBackground(new RippleDrawable(ColorStateList.valueOf(0x55ffffff),panelBackground(0x6010191c),null));
        gear.setOnClickListener(v->setMenuOpen(!menuOpen));
        gear.setOnTouchListener((view,event)->dragControls(event));
        gearPosition=new FrameLayout.LayoutParams(dp(48),dp(48),Gravity.TOP|Gravity.LEFT);
        root.addView(gear,gearPosition);
        root.addOnLayoutChangeListener((view,l,t,r,b,oldL,oldT,oldR,oldB)->{if(r-l!=oldR-oldL||b-t!=oldB-oldT){cancelControlsGesture();positionControls();}});
        layerBanner=new TextView(this);layerBanner.setTextColor(0xb3ffffff);layerBanner.setTextSize(16);layerBanner.setGravity(Gravity.CENTER);layerBanner.setPadding(dp(12),dp(6),dp(12),dp(6));
        layerBanner.setBackground(panelBackground(0x28081010));layerBanner.setShadowLayer(dp(2),0,dp(1),0x66000000);layerBanner.setAlpha(0f);layerBanner.setMaxLines(1);layerBanner.setEllipsize(android.text.TextUtils.TruncateAt.END);
        layerBanner.setClickable(false);layerBanner.setFocusable(false);
        final FrameLayout.LayoutParams layerPosition=new FrameLayout.LayoutParams(-2,-2,Gravity.TOP|Gravity.CENTER_HORIZONTAL);layerPosition.topMargin=dp(12);root.addView(layerBanner,layerPosition);
        // Keep the gear and menu clear of display cutouts and temporarily revealed bars.
        root.setOnApplyWindowInsetsListener((view,insets)->{
            int left=insets.getSystemWindowInsetLeft(),top=insets.getSystemWindowInsetTop(),right=insets.getSystemWindowInsetRight(),bottom=insets.getSystemWindowInsetBottom();
            if(Build.VERSION.SDK_INT>=28&&insets.getDisplayCutout()!=null){DisplayCutout cutout=insets.getDisplayCutout();left=Math.max(left,cutout.getSafeInsetLeft());top=Math.max(top,cutout.getSafeInsetTop());right=Math.max(right,cutout.getSafeInsetRight());bottom=Math.max(bottom,cutout.getSafeInsetBottom());}
            if(controlsInsetLeft!=left||controlsInsetTop!=top||controlsInsetRight!=right||controlsInsetBottom!=bottom)cancelControlsGesture();
            controlsInsetLeft=left;controlsInsetTop=top;controlsInsetRight=right;controlsInsetBottom=bottom;positionControls();
            panel.setMargins(dp(12)+left,dp(68)+top,dp(12)+right,dp(12)+bottom);scroll.setLayoutParams(panel);
            layerPosition.topMargin=dp(12)+top;layerBanner.setMaxWidth(Math.max(dp(1),getResources().getDisplayMetrics().widthPixels-dp(140)-left-right));layerBanner.setLayoutParams(layerPosition);
            return insets;
        });
    }
    private ClientOverlayPosition.Area controlsArea(){return new ClientOverlayPosition.Area(controlsHost.getWidth(),controlsHost.getHeight(),controlsInsetLeft,controlsInsetTop,controlsInsetRight,controlsInsetBottom,dp(12),dp(48),dp(48));}
    private void positionControls(){
        if(gear==null||controlsHost==null||controlsHost.getWidth()==0||controlsHost.getHeight()==0)return;
        ClientOverlayPosition.Placement position=controlsArea().place(controlsX,controlsY,0,dp(12),false);
        if(gearPosition.leftMargin!=position.gearLeft||gearPosition.topMargin!=position.gearTop){gearPosition.setMargins(position.gearLeft,position.gearTop,0,0);gear.setLayoutParams(gearPosition);}
    }
    private void saveControlsPosition(){controlsPreferences.edit().putFloat(CONTROLS_PREFIX+"x",controlsX).putFloat(CONTROLS_PREFIX+"y",controlsY).apply();}
    private boolean dragControls(MotionEvent event){
        switch(event.getActionMasked()){
            case MotionEvent.ACTION_DOWN:
                controlsDrag.start(event.getRawX(),event.getRawY(),gearPosition.leftMargin,gearPosition.topMargin);gear.setPressed(true);return true;
            case MotionEvent.ACTION_MOVE:
                if(controlsDrag.move(event.getRawX(),event.getRawY())){
                    if(!controlsDragging){controlsDragging=true;gear.setPressed(false);setMenuOpen(false);refreshControllerCapture();}
                    ClientOverlayPosition.Point point=controlsDrag.position(event.getRawX(),event.getRawY());ClientOverlayPosition.Point normalized=controlsArea().normalize(point.x,point.y);controlsX=normalized.x;controlsY=normalized.y;positionControls();
                }
                return true;
            case MotionEvent.ACTION_UP:
                boolean click=controlsDrag.finish();gear.setPressed(false);finishControlsDrag();if(click)gear.performClick();return true;
            case MotionEvent.ACTION_CANCEL:case MotionEvent.ACTION_POINTER_DOWN:case MotionEvent.ACTION_POINTER_UP:
                cancelControlsGesture();return true;
            default:return true;
        }
    }
    private void finishControlsDrag(){if(controlsDragging){controlsDragging=false;saveControlsPosition();refreshControllerCapture();}}
    private void cancelControlsGesture(){if(controlsDrag!=null)controlsDrag.cancel();if(gear!=null)gear.setPressed(false);finishControlsDrag();}
    private void controlsPositionDialog(){
        new AlertDialog.Builder(this).setTitle("Move options button").setItems(new String[]{"Upper left","Upper right","Lower left","Lower right","Center"},(dialog,which)->{
            controlsX=which==4?.5f:which%2==0?0f:1f;controlsY=which==4?.5f:which<2?0f:1f;positionControls();saveControlsPosition();
        }).setNegativeButton("Cancel",null).show();
    }
    private GradientDrawable panelBackground(int color){GradientDrawable background=new GradientDrawable();background.setColor(color);background.setCornerRadius(dp(16));return background;}
    private void immersive(){
        if(Build.VERSION.SDK_INT>=30){
            getWindow().setDecorFitsSystemWindows(false);
            WindowInsetsController insets=getWindow().getInsetsController();
            if(insets!=null){insets.setSystemBarsBehavior(WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);insets.hide(WindowInsets.Type.systemBars());}
        }else getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY|View.SYSTEM_UI_FLAG_FULLSCREEN|View.SYSTEM_UI_FLAG_HIDE_NAVIGATION|View.SYSTEM_UI_FLAG_LAYOUT_STABLE|View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN|View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION);
    }
    /** TRASC's ic_client_gear vector (24-unit path, even-odd hole), drawn in code so the APK's
     * resource table stays identical to the donor's. */
    private static final class GearDrawable extends Drawable {
        private static final float[] OUTLINE={10,2,14,2,14.6f,5,16,5.8f,18.9f,4.8f,21,8.3f,18.7f,10.3f,18.7f,13.7f,21,15.7f,18.9f,19.2f,16,18.2f,14.6f,19,14,22,
            10,22,9.4f,19,8,18.2f,5.1f,19.2f,3,15.7f,5.3f,13.7f,5.3f,10.3f,3,8.3f,5.1f,4.8f,8,5.8f,9.4f,5};
        private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);private final Path path=new Path();private final int size;
        GearDrawable(int size){this.size=size;paint.setColor(0xE6FFFFFF);paint.setStyle(Paint.Style.FILL);}
        @Override protected void onBoundsChange(Rect bounds){
            path.reset();path.setFillType(Path.FillType.EVEN_ODD);
            float scale=Math.min(bounds.width(),bounds.height())/24f,left=bounds.exactCenterX()-12*scale,top=bounds.exactCenterY()-12*scale;
            for(int i=0;i<OUTLINE.length;i+=2){float x=left+OUTLINE[i]*scale,y=top+OUTLINE[i+1]*scale;if(i==0)path.moveTo(x,y);else path.lineTo(x,y);}
            path.close();path.addCircle(left+12*scale,top+12*scale,4*scale,Path.Direction.CW);
        }
        @Override public void draw(Canvas canvas){canvas.drawPath(path,paint);}
        @Override public void setAlpha(int alpha){paint.setAlpha(alpha*0xE6/255);invalidateSelf();}
        @Override public void setColorFilter(ColorFilter filter){paint.setColorFilter(filter);invalidateSelf();}
        @Override public int getOpacity(){return PixelFormat.TRANSLUCENT;}
        @Override public int getIntrinsicWidth(){return size;}
        @Override public int getIntrinsicHeight(){return size;}
    }
    /** Overlay is outside SurfaceView; it is not included in client PixelCopy evidence. */
    private final class CursorOverlay extends View{
        private final Paint paint=new Paint();private float x,y;private boolean visible;
        CursorOverlay(){super(ClientActivity.this);setClickable(false);setFocusable(false);paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(dp(2));}
        void move(float x,float y,boolean visible){if(this.x==x&&this.y==y&&this.visible==visible)return;this.x=x;this.y=y;this.visible=visible;invalidate();}
        @Override protected void onDraw(Canvas canvas){if(!visible)return;paint.setColor(Color.BLACK);canvas.drawCircle(x,y,dp(7),paint);paint.setColor(Color.CYAN);canvas.drawLine(x-dp(6),y,x+dp(6),y,paint);canvas.drawLine(x,y-dp(6),x,y+dp(6),paint);}
    }

    private void request(String action){
        final long uiActionElapsedRealtime = SystemClock.elapsedRealtime();
        if(!diagnosticControlsReady(state,service!=null,exporting,ClientRuntime.operationInProgress())||(state.blocked&&!ClientService.STORAGE_SCAN.equals(action)))return;
        pendingStartupUiActionElapsedRealtime = uiActionElapsedRealtime;
        if(Build.VERSION.SDK_INT>=33&&checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED){pendingAction=action;requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},NOTIFY);return;}
        launch(action);
    }
    private void launch(String action){final long uiActionElapsedRealtime=pendingStartupUiActionElapsedRealtime;pendingStartupUiActionElapsedRealtime=-1;try{Intent intent=new Intent(this,ClientService.class).setAction(action);if((ClientService.RUN.equals(action)||ClientService.CREATE.equals(action)||ClientService.RESUME_FIRST_CREATION.equals(action))&&uiActionElapsedRealtime>=0)intent.putExtra(ClientService.EXTRA_STARTUP_UI_ACTION_ELAPSED_REALTIME,uiActionElapsedRealtime);if(ClientService.IMPORT.equals(action)){intent.setData(pendingImport);intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);}startForegroundService(intent);}catch(RuntimeException e){Toast.makeText(this,"Could not start. Return to this screen and retry.",Toast.LENGTH_LONG).show();}}
    @Override public void onRequestPermissionsResult(int request,String[] permissions,int[] results){super.onRequestPermissionsResult(request,permissions,results);if(request==NOTIFY&&pendingAction!=null){String action=pendingAction;pendingAction=null;launch(action);}}
    private void chooseImport(){
        if(state==null||state.busy||state.storageBusy||state.reportExporting||state.blocked||exporting||ClientRuntime.operationInProgress())return;
        Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("*/*").addCategory(Intent.CATEGORY_OPENABLE).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        try{startActivityForResult(intent,IMPORT);}catch(RuntimeException e){Toast.makeText(this,"No file picker is available.",Toast.LENGTH_LONG).show();}
    }
    private void refreshAssetPackStatus(){
        assetStatusChecking=true;assetStatusDirty=false;
        final Context application=getApplicationContext();
        Thread worker=new Thread(()->{
            final String text=AssetPackStore.status(application);
            runOnUiThread(()->{
                assetStatusChecking=false;assetStatusLoaded=true;
                if(!isDestroyed())assetPackStatus.setText(text);
            });
        },"coh-asset-status");
        worker.setDaemon(true);worker.start();
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
        if(!diagnosticControlsReady(state,service!=null,exporting,ClientRuntime.operationInProgress()))return;
        if(storageDialog!=null)storageDialog.dismiss();
        final StorageAudit.Plan plan=state.storagePlan;
        LinearLayout body=new LinearLayout(this);body.setOrientation(LinearLayout.VERTICAL);body.setPadding(dp(16),dp(8),dp(16),dp(8));
        TextView message=new TextView(this);message.setText(state.storageStatus+"\nThese totals cover private app files; Android also counts the installed APK and its cache. Allocated size counts storage blocks once; apparent size can include shared files. Character data, current runtime, imported assets and startup caches are protected.");body.addView(message);
        if(state.blocked){TextView blockedNote=new TextView(this);blockedNote.setText("Read-only scan and report export remain available. File deletion stays disabled until owned-process cleanup is verified.");body.addView(blockedNote);}
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
        Button clean=new Button(this);clean.setText("Review selected cleanup");clean.setEnabled(!state.blocked&&plan!=null&&plan.cleanupAllowed&&!choices.isEmpty());clean.setOnClickListener(v->{
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
        if(!diagnosticControlsReady(state,service!=null,exporting,ClientRuntime.operationInProgress()))return;
        final List<File> reports;
        try{reports=service.retainedReports();}catch(IOException failure){Toast.makeText(this,"Report inventory needs recovery. Use Recover interrupted reports.",Toast.LENGTH_LONG).show();return;}
        if(reports.isEmpty()){Toast.makeText(this,"No retained report found. Recover interrupted reports, then retry Reports / export.",Toast.LENGTH_LONG).show();return;}
        String[] labels=new String[reports.size()];
        SimpleDateFormat format=new SimpleDateFormat("yyyy-MM-dd HH:mm:ss 'UTC'",Locale.ROOT);format.setTimeZone(TimeZone.getTimeZone("UTC"));
        for(int i=0;i<labels.length;i++){
            File report=reports.get(i);String run=report.getParentFile().getName();long utc=report.lastModified();
            try{utc=ClientReports.reportStartedUtc(report);}catch(Exception ignored){}
            labels[i]=format.format(new Date(utc))+" · "+reportFileLabel(report)+" · "+storageBytes(report.length());
        }
        new AlertDialog.Builder(this).setTitle("Retained reports · newest first").setItems(labels,(dialog,index)->chooseReportDestination(reports.get(index))).setNegativeButton("Cancel",null).show();
    }
    static String reportFileLabel(File report){
        try {
            switch(ClientReports.reportStatus(report)) {
                case "successful":return "Successful session · inspect gameplay results";
                case "incomplete":return "Incomplete session · inspect committed save";
                case "failed":return "Failed session · diagnostic evidence";
                case "interrupted":return "Interrupted / incomplete session";
                case "finalization_failed":return "Report finalization failed · diagnostic evidence";
                case "recovered":return reportArchiveLabel(report.getName());
                default:break;
            }
        }catch(IOException unavailable){/* The archive remains retained; no completion is inferred. */}
        return reportArchiveLabel(report.getName());
    }
    static String reportArchiveLabel(String name){
        if(name.startsWith("coh-interrupted-guest-"))return "Recovered guest evidence · session unverified";
        if(name.contains("interrupted"))return "Recovered / incomplete report";
        if(name.contains("report-failure"))return "Report finalization failed · diagnostic evidence";
        return "Session report · inspect save and gameplay results";
    }
    private void chooseReportDestination(File report){
        pendingExport=report.getPath();
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
        if(service==null||pendingExportSource==null||pendingExportDestination==null)return;
        final String selected=pendingExportSource;final android.net.Uri uri=pendingExportDestination;
        try{
            Intent intent=new Intent(this,ClientService.class).setAction(ClientService.EXPORT_REPORT).setData(uri)
                    .putExtra("report_source",selected).addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
            startForegroundService(intent);pendingExportSource=null;pendingExportDestination=null;
        }catch(RuntimeException failure){Toast.makeText(this,"Export could not start. The private report is retained.",Toast.LENGTH_LONG).show();}
    }
    @Override protected void onSaveInstanceState(Bundle out){out.putString("export",pendingExport);out.putString("storage_export",pendingStorageExport);out.putString("export_source",pendingExportSource);out.putString("export_destination",pendingExportDestination==null?null:pendingExportDestination.toString());out.putString("action",pendingAction);out.putString("import_uri",pendingImport==null?null:pendingImport.toString());out.putBoolean("import_waiting",importWaiting);super.onSaveInstanceState(out);}
    @Override protected void onDestroy(){if(activeTextDialog!=null)activeTextDialog.dismiss();if(storageDialog!=null)storageDialog.dismiss();inputHandler.removeCallbacks(hideLayer);if(layerBanner!=null)layerBanner.animate().cancel();if(controller!=null)controller.close();super.onDestroy();}
}
