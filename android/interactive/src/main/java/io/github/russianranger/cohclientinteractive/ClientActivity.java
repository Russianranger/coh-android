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
    private Button setup,importAssets,run,createFresh,resumeCreation,switchHero,stop,export,storage,finish,typeText,returnGround,saveLogout,captureContact,openTaskContact,captureAcceptedTask,completeTask,captureCompletedTask;
    private Button enterKey,showFps,fps10,fps30,fps60;
    private TextView recommendedStatus,optionsNotice;
    private CheckBox performanceGraphics,prootFastMode,prestartNextZone,trustedBins,gameplay60,idleResidentMaps,sharedServerData,clientSkipServerFolders,clientFolderIndex,clientAudio,sharedHeap,stockTravel,earlyZone,spareZone,glDirect,prootIoctlFilter,prootSocketFilter,prootCasefold,serverQuickStart,wineserverPathCache,physxCache,serverX87,deferZoneLoads,clientGroupBins,keepPreviousZone,missionMaps,unlockAll,primalist;
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
    private Button[] menuTabs;
    private LinearLayout[] menuPages;
    private ScrollView menuScroll;
    private int menuTab=-1;
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
    private CheckBox testDetails;
    private LinearLayout testTools;
    private TextView assetPackStatus,navigationMapStatus;
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
        // 0.13.83 (owner, 2026-11-24): what is happening stays above three tabs. Play holds the commands used in
        // every session, Options the launch options in four categories, Setup everything done once or rarely.
        status=text("Connecting",17,true);controls.addView(status);
        detail=text("Connecting to the private runtime service…",13,false);controls.addView(detail);
        counter=text("Waiting for the client",12,false);controls.addView(counter);
        optionsNotice=text("",12,true);optionsNotice.setVisibility(View.GONE);controls.addView(optionsNotice);
        LinearLayout tabRow=new LinearLayout(this);controls.addView(tabRow);
        String[] tabNames={"Play","Options","Setup"};menuTabs=new Button[tabNames.length];menuPages=new LinearLayout[tabNames.length];
        for(int i=0;i<tabNames.length;i++){final int index=i;
            menuTabs[i]=button(tabNames[i],()->selectTab(index));tabRow.addView(menuTabs[i],new LinearLayout.LayoutParams(0,-2,1));
            menuPages[i]=new LinearLayout(this);menuPages[i].setOrientation(LinearLayout.VERTICAL);controls.addView(menuPages[i]);
        }
        menuScroll=scroll;
        buildPlayPage(menuPages[0]);buildOptionsPage(menuPages[1]);buildSetupPage(menuPages[2]);
        selectTab(controlsPreferences.getInt(CONTROLS_PREFIX+"tab",0));
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
    /** Play: the commands of an ordinary session, in the order they are used. */
    private void buildPlayPage(LinearLayout controls){
        resumeGame=button("Resume game",()->setMenuOpen(false));resumeGame.setEnabled(false);controls.addView(resumeGame);
        run=button("Play",()->request(ClientService.RUN));controls.addView(run);
        createFresh=button("Create fresh character",this::confirmFreshProfile);createFresh.setVisibility(View.GONE);controls.addView(createFresh);
        profileStatus=text("Checking saved character profile…",12,false);controls.addView(profileStatus);
        controls.addView(text("Play opens the game's own character list: choose a hero, or make a new one in an empty slot. The zone of the hero you played last is prepared first. Sign in as COHLOCAL (offline).",12,false));
        typeText=button("Send text / L3",this::showTextInput);controls.addView(typeText);
        enterKey=button("Enter / Start",this::sendEnter);controls.addView(enterKey);
        saveLogout=button("Save character / log out",this::saveCharacter);controls.addView(saveLogout);
        finish=button("Finish",()->{releaseControls();if(service!=null)service.requestFinish();});controls.addView(finish);
        export=button("Reports / export",this::chooseExport);controls.addView(export);
        controls.addView(text("Travel",15,true));
        zoningStatus=text("Start Play to travel.",12,false);controls.addView(zoningStatus);
        travelZone=button("Return from old Atlas instance",this::travelToZone);travelZone.setVisibility(View.GONE);controls.addView(travelZone);
        returnGround=button("Return to safe ground (optional)",()->{releaseControls();if(service!=null)service.requestReturnToSafeGround();});controls.addView(returnGround);
        stop=button("Abort operation",()->{movementSuppressed=true;releaseControls();refreshMovementControls();if(service!=null)startService(new Intent(this,ClientService.class).setAction(ClientService.STOP));});controls.addView(stop);
        controls.addView(text("When ready to save, release controls, tap Save character / log out, wait until the status says Saved, then tap Finish. Show FPS and the FPS caps are on the Options tab. Reports / export makes the ZIP of a session.",12,false));
    }
    /** 0.13.86 (owner, 2026-11-25): Show FPS and the frame caps sit at the top of the Options tab. */
    private void addFpsControls(LinearLayout controls){
        controls.addView(text("Frame rate",15,true));
        controls.addView(text("These work while your hero is in the game.",12,false));
        showFps=button("Show FPS",()->sendPerformanceCommand(ClientInput.PerformanceCommand.SHOW_FPS));controls.addView(showFps);
        LinearLayout fpsRow=new LinearLayout(this);
        fps10=button("10 FPS",()->sendPerformanceCommand(ClientInput.PerformanceCommand.FPS_10));
        fps30=button("30 FPS",()->sendPerformanceCommand(ClientInput.PerformanceCommand.FPS_30));
        fps60=button("60 FPS",()->sendPerformanceCommand(ClientInput.PerformanceCommand.FPS_60));
        fpsRow.addView(fps10,new LinearLayout.LayoutParams(0,-2,1));
        fpsRow.addView(fps30,new LinearLayout.LayoutParams(0,-2,1));
        fpsRow.addView(fps60,new LinearLayout.LayoutParams(0,-2,1));controls.addView(fpsRow);
    }
    /** Options: one line that says whether anything is off the recommended settings, then four categories
     *  (owner, 2026-11-24): Recommended, Optional, Test, Experimental. */
    private void buildOptionsPage(LinearLayout controls){
        addFpsControls(controls);
        controls.addView(text("Launch options",15,true));
        // 0.13.76: Thor 0.13.75 ran four launches with one option left unticked by an earlier test.
        recommendedStatus=text("Checking options…",12,true);controls.addView(recommendedStatus);
        controls.addView(button("Restore recommended options",this::restoreRecommendedOptions));
        category(controls,"Recommended","Ticked in a new install. Leave them ticked unless a test sheet asks otherwise.");
        performanceGraphics=new CheckBox(this);performanceGraphics.setText("Use performance graphics");
        performanceGraphics.setTextColor(Color.rgb(221,234,245));performanceGraphics.setTextSize(13);
        performanceGraphics.setChecked(ClientRuntime.performanceGraphicsEnabled(this));
        performanceGraphics.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setPerformanceGraphicsEnabled(this,checked);recommendedChanged();});
        controls.addView(performanceGraphics);
        prootFastMode=new CheckBox(this);prootFastMode.setText("Fast mode (PRoot seccomp, experimental)");
        prootFastMode.setTextColor(Color.rgb(221,234,245));prootFastMode.setTextSize(13);
        prootFastMode.setChecked(ClientRuntime.prootFastModeEnabled(this));
        prootFastMode.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setProotFastModeEnabled(this,checked);recommendedChanged();});
        controls.addView(prootFastMode);
        sharedServerData=new CheckBox(this);sharedServerData.setText("Share server data between zones (faster zone preparation)");
        sharedServerData.setTextColor(Color.rgb(221,234,245));sharedServerData.setTextSize(13);
        sharedServerData.setChecked(ClientRuntime.sharedServerDataEnabled(this));
        sharedServerData.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setSharedServerDataEnabled(this,checked);recommendedChanged();});
        controls.addView(sharedServerData);
        clientSkipServerFolders=new CheckBox(this);clientSkipServerFolders.setText("Skip server-only folders in the client's file scan (faster client start)");
        clientSkipServerFolders.setTextColor(Color.rgb(221,234,245));clientSkipServerFolders.setTextSize(13);
        clientSkipServerFolders.setChecked(ClientRuntime.clientSkipServerFoldersEnabled(this));
        clientSkipServerFolders.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setClientSkipServerFoldersEnabled(this,checked);recommendedChanged();});
        controls.addView(clientSkipServerFolders);
        clientFolderIndex=new CheckBox(this);clientFolderIndex.setText("Reuse the client's saved file list while the data is unchanged (faster client start)");
        clientFolderIndex.setTextColor(Color.rgb(221,234,245));clientFolderIndex.setTextSize(13);
        clientFolderIndex.setChecked(ClientRuntime.clientFolderIndexEnabled(this));
        clientFolderIndex.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setClientFolderIndexEnabled(this,checked);recommendedChanged();});
        controls.addView(clientFolderIndex);
        clientAudio=new CheckBox(this);clientAudio.setText("Game audio (sound and music through Android)");
        clientAudio.setTextColor(Color.rgb(221,234,245));clientAudio.setTextSize(13);
        clientAudio.setChecked(ClientRuntime.clientAudioEnabled(this));
        clientAudio.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setClientAudioEnabled(this,checked);recommendedChanged();});
        controls.addView(clientAudio);
        stockTravel=new CheckBox(this);stockTravel.setText("Game's own zone travel (doors, tunnels, monorail; any zone)");
        stockTravel.setTextColor(Color.rgb(221,234,245));stockTravel.setTextSize(13);
        stockTravel.setChecked(ClientRuntime.stockTravelEnabled(this));
        stockTravel.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setStockTravelEnabled(this,checked);recommendedChanged();});
        controls.addView(stockTravel);
        earlyZone=new CheckBox(this);earlyZone.setText("Start my saved zone while the game starts (Reopen)");
        earlyZone.setTextColor(Color.rgb(221,234,245));earlyZone.setTextSize(13);
        earlyZone.setChecked(ClientRuntime.earlyZoneEnabled(this));
        earlyZone.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setEarlyZoneEnabled(this,checked);recommendedChanged();});
        controls.addView(earlyZone);
        spareZone=new CheckBox(this);spareZone.setText("Keep a spare zone server loaded for travel (needs Fast server)");
        spareZone.setTextColor(Color.rgb(221,234,245));spareZone.setTextSize(13);
        spareZone.setChecked(ClientRuntime.spareZoneEnabled(this));
        spareZone.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setSpareZoneEnabled(this,checked);recommendedChanged();});
        controls.addView(spareZone);
        trustedBins=new CheckBox(this);trustedBins.setText("Fast server (untick for the 0.13.36 server)");
        trustedBins.setTextColor(Color.rgb(221,234,245));trustedBins.setTextSize(13);
        trustedBins.setChecked(ClientRuntime.trustedBinsEnabled(this));
        trustedBins.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setTrustedBinsEnabled(this,checked);recommendedChanged();});
        controls.addView(trustedBins);
        gameplay60=new CheckBox(this);gameplay60.setText("Raise the frame cap to 60 FPS in the world");
        gameplay60.setTextColor(Color.rgb(221,234,245));gameplay60.setTextSize(13);
        gameplay60.setChecked(ClientRuntime.gameplay60FpsEnabled(this));
        gameplay60.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setGameplay60FpsEnabled(this,checked);recommendedChanged();});
        controls.addView(gameplay60);
        prootIoctlFilter=new CheckBox(this);prootIoctlFilter.setText("Lighter system-call monitor (untick for the 0.13.36 one)");
        prootIoctlFilter.setTextColor(Color.rgb(221,234,245));prootIoctlFilter.setTextSize(13);
        prootIoctlFilter.setChecked(ClientRuntime.prootIoctlFilterEnabled(this));
        prootIoctlFilter.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setProotIoctlFilterEnabled(this,checked);recommendedChanged();});
        controls.addView(prootIoctlFilter);
        prootSocketFilter=new CheckBox(this);prootSocketFilter.setText("Do not monitor ordinary socket traffic (needs Lighter system-call monitor)");
        prootSocketFilter.setTextColor(Color.rgb(221,234,245));prootSocketFilter.setTextSize(13);
        prootSocketFilter.setChecked(ClientRuntime.prootSocketFilterEnabled(this));
        prootSocketFilter.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setProotSocketFilterEnabled(this,checked);recommendedChanged();});
        controls.addView(prootSocketFilter);
        prootCasefold=new CheckBox(this);prootCasefold.setText("Find files in any letter case in one step (needs Lighter system-call monitor)");
        prootCasefold.setTextColor(Color.rgb(221,234,245));prootCasefold.setTextSize(13);
        prootCasefold.setChecked(ClientRuntime.prootCasefoldEnabled(this));
        prootCasefold.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setProotCasefoldEnabled(this,checked);recommendedChanged();});
        controls.addView(prootCasefold);
        serverQuickStart=new CheckBox(this);serverQuickStart.setText("Load zone server animations when first used (faster zone start)");
        serverQuickStart.setTextColor(Color.rgb(221,234,245));serverQuickStart.setTextSize(13);
        serverQuickStart.setChecked(ClientRuntime.serverQuickStartEnabled(this));
        serverQuickStart.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setServerQuickStartEnabled(this,checked);recommendedChanged();});
        controls.addView(serverQuickStart);
        wineserverPathCache=new CheckBox(this);wineserverPathCache.setText("Remember folder locations in the Wine server (faster file opening)");
        wineserverPathCache.setTextColor(Color.rgb(221,234,245));wineserverPathCache.setTextSize(13);
        wineserverPathCache.setChecked(ClientRuntime.wineserverPathCacheEnabled(this));
        wineserverPathCache.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setWineserverPathCacheEnabled(this,checked);recommendedChanged();});
        controls.addView(wineserverPathCache);
        physxCache=new CheckBox(this);physxCache.setText("Reuse prepared collision meshes (faster zone start, needs Fast server)");
        physxCache.setTextColor(Color.rgb(221,234,245));physxCache.setTextSize(13);
        physxCache.setChecked(ClientRuntime.physxCacheEnabled(this));
        physxCache.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setPhysxCacheEnabled(this,checked);recommendedChanged();});
        controls.addView(physxCache);
        serverX87=new CheckBox(this);serverX87.setText("Faster number emulation in zone servers (64-bit x87; faster zone start and travel)");
        serverX87.setTextColor(Color.rgb(221,234,245));serverX87.setTextSize(13);
        serverX87.setChecked(ClientRuntime.serverX87Enabled(this));
        serverX87.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setServerX87Enabled(this,checked);recommendedChanged();});
        controls.addView(serverX87);
        deferZoneLoads=new CheckBox(this);deferZoneLoads.setText("Finish zone loading while the game loads the zone (needs Fast server)");
        deferZoneLoads.setTextColor(Color.rgb(221,234,245));deferZoneLoads.setTextSize(13);
        deferZoneLoads.setChecked(ClientRuntime.deferZoneLoadsEnabled(this));
        deferZoneLoads.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setDeferZoneLoadsEnabled(this,checked);recommendedChanged();});
        controls.addView(deferZoneLoads);
        controls.addView(text("Performance graphics, ARM64 client: water effects, shadows, bloom and depth of field off; detail and resolution unchanged. x86 client: lower detail and a 600×450 world. Untick before launch to use the game's own graphics settings.",12,false));
        category(controls,"Optional","Works, at a cost. Your choice.");
        keepPreviousZone=new CheckBox(this);keepPreviousZone.setText("Keep the zone you just left loaded (about 1.2 GB more memory; needs the spare zone server)");
        keepPreviousZone.setTextColor(Color.rgb(221,234,245));keepPreviousZone.setTextSize(13);
        keepPreviousZone.setChecked(ClientRuntime.keepPreviousZoneEnabled(this));
        keepPreviousZone.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setKeepPreviousZoneEnabled(this,checked);recommendedChanged();});
        controls.addView(keepPreviousZone);
        category(controls,"Test","Being tested in this version. Tick only when a test sheet asks.");
        missionMaps=new CheckBox(this);missionMaps.setText("Start mission maps (test; needs the game's own zone travel and the imported zone assets)");
        missionMaps.setTextColor(Color.rgb(221,234,245));missionMaps.setTextSize(13);
        missionMaps.setChecked(ClientRuntime.missionMapsEnabled(this));
        missionMaps.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setMissionMapsEnabled(this,checked);recommendedChanged();});
        controls.addView(missionMaps);
        unlockAll=new CheckBox(this);unlockAll.setText("Unlock all content (test; store, veteran and pack rewards, locked power sets and archetypes; needs Fast server)");
        unlockAll.setTextColor(Color.rgb(221,234,245));unlockAll.setTextSize(13);
        unlockAll.setChecked(ClientRuntime.unlockAllEnabled(this));
        unlockAll.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setUnlockAllEnabled(this,checked);recommendedChanged();});
        controls.addView(unlockAll);
        primalist=new CheckBox(this);primalist.setText("Primalist archetype (test; adds its name to the saved game once and stays on; older app versions will not open that saved game; needs Fast server)");
        primalist.setTextColor(Color.rgb(221,234,245));primalist.setTextSize(13);
        primalist.setChecked(ClientRuntime.primalistEnabled(this));
        primalist.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setPrimalistEnabled(this,checked);recommendedChanged();});
        controls.addView(primalist);
        category(controls,"Experimental","Tried and showed no clear benefit on the Thor. Kept for comparison; leave unticked.");
        prestartNextZone=new CheckBox(this);prestartNextZone.setText("Start King's Row in the background (zoning)");
        prestartNextZone.setTextColor(Color.rgb(221,234,245));prestartNextZone.setTextSize(13);
        prestartNextZone.setChecked(ClientRuntime.prestartNextZoneEnabled(this));
        prestartNextZone.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setPrestartNextZoneEnabled(this,checked);recommendedChanged();});
        controls.addView(prestartNextZone);
        idleResidentMaps=new CheckBox(this);idleResidentMaps.setText("Lower the waiting zone server's priority (zoning, experimental)");
        idleResidentMaps.setTextColor(Color.rgb(221,234,245));idleResidentMaps.setTextSize(13);
        idleResidentMaps.setChecked(ClientRuntime.idleResidentMapsEnabled(this));
        idleResidentMaps.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setIdleResidentMapsEnabled(this,checked);recommendedChanged();});
        controls.addView(idleResidentMaps);
        sharedHeap=new CheckBox(this);sharedHeap.setText("Shared server memory (experiment: zone servers share game data)");
        sharedHeap.setTextColor(Color.rgb(221,234,245));sharedHeap.setTextSize(13);
        sharedHeap.setChecked(ClientRuntime.sharedHeapEnabled(this));
        sharedHeap.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setSharedHeapEnabled(this,checked);recommendedChanged();});
        controls.addView(sharedHeap);
        glDirect=new CheckBox(this);glDirect.setText("Draw on the game's own thread (frame rate experiment)");
        glDirect.setTextColor(Color.rgb(221,234,245));glDirect.setTextSize(13);
        glDirect.setChecked(ClientRuntime.glDirectEnabled(this));
        glDirect.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setGlDirectEnabled(this,checked);recommendedChanged();});
        controls.addView(glDirect);
        clientGroupBins=new CheckBox(this);clientGroupBins.setText("Keep prepared zone object files (experimental, ARM64 client; faster zone loading)");
        clientGroupBins.setTextColor(Color.rgb(221,234,245));clientGroupBins.setTextSize(13);
        clientGroupBins.setChecked(ClientRuntime.clientGroupBinsEnabled(this));
        clientGroupBins.setOnCheckedChangeListener((button,checked)->{ClientRuntime.setClientGroupBinsEnabled(this,checked);recommendedChanged();});
        controls.addView(clientGroupBins);
        recommendedChanged();
        category(controls,"Client and renderer","Change these only after finishing a run.");
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
    }
    /** Setup: what is done once per install or update, then the rarely used tools. */
    private void buildSetupPage(LinearLayout controls){
        controls.addView(text("Runtime and game files",15,true));
        setup=button("Set up / update runtime",()->request(ClientService.SETUP));controls.addView(setup);
        importAssets=button("Import asset or map pack part",this::chooseImport);controls.addView(importAssets);
        assetPackStatus=text("Checking required asset pack…",12,false);controls.addView(assetPackStatus);
        // Owner, 2026-11-09: every zone's navigation map, imported with the same button (optional).
        navigationMapStatus=text("Checking navigation maps…",12,false);controls.addView(navigationMapStatus);
        controls.addView(text("Fresh install: import every ZIP part from the compatible versioned Assets release, then Set up / update runtime. Each completed part is retained; the app shows any missing parts. Keep these ZIPs for reinstalling. Future APK updates reuse compatible imported assets.",12,false));
        controls.addView(text("Saved games",15,true));
        // 0.13.87 (owner, 2026-11-25): every hero is in the one saved game and is chosen in the game's own
        // character list. The second saved game of 0.13.85 stays reachable here; nothing is merged or deleted.
        controls.addView(text("All your heroes are in one saved game; you choose or make them in the game's own character list. If you made a second saved game with version 0.13.85, this button swaps it in and back. Nothing is deleted.",12,false));
        switchHero=button("Swap to the other saved game",this::confirmSwitchHero);controls.addView(switchHero);
        resumeCreation=button("Resume first character creation",this::confirmResumeCreation);resumeCreation.setVisibility(View.GONE);controls.addView(resumeCreation);
        controls.addView(text("Resume first character creation is only for a first hero whose creation was interrupted before it was saved.",12,false));
        controls.addView(text("Controller and options button",15,true));
        controls.addView(button("Controller mappings",this::controllerDialog));
        controls.addView(text("Default controller: Left stick: WASD · X: jump · Right stick: cursor · A: click/talk · B: Esc · Shoulders: right click / turn view · D-pad: arrows · L3: text · Start: Enter. Triggers are unbound. The COH power trays preset adds hold LT for 1–0 and Select for this menu; Back or the gear also opens it.",12,false));
        controls.addView(button("Move options button",this::controlsPositionDialog));
        controls.addView(button("Reset options button position",()->{controlsX=1f;controlsY=0f;positionControls();saveControlsPosition();}));
        controls.addView(text("Reports and storage",15,true));
        recoverReports=button("Recover interrupted reports",()->{if(service!=null)startForegroundService(new Intent(this,ClientService.class).setAction(ClientService.RECOVER_REPORTS));});controls.addView(recoverReports);
        storage=button("Storage and cleanup",this::showStorage);controls.addView(storage);
        // 0.13.86 (owner, 2026-11-25): what a session checks is recorded in its report, not shown in the menu.
        // This box brings the check wording, the counters, the log and the test buttons back for a test sheet.
        testDetails=new CheckBox(this);testDetails.setText("Show test details and tools");
        testDetails.setTextColor(Color.rgb(221,234,245));testDetails.setTextSize(13);
        testDetails.setChecked(controlsPreferences.getBoolean(CONTROLS_PREFIX+"test_details",false));
        testDetails.setOnCheckedChangeListener((button,checked)->{controlsPreferences.edit().putBoolean(CONTROLS_PREFIX+"test_details",checked).apply();applyTestDetails();});
        controls.addView(testDetails);
        final LinearLayout page=controls;
        controls=new LinearLayout(this);controls.setOrientation(LinearLayout.VERTICAL);testTools=controls;page.addView(controls);
        controls.addView(text("Test tools",15,true));
        controls.addView(text("Tap Start test when ready and Stop test when finished; neither starts a countdown.",12,false));
        startTest=button("Start test",()->{if(service!=null)service.startManualTest();});controls.addView(startTest);
        stopTest=button("Stop test",()->{if(service!=null)service.stopManualTest();});controls.addView(stopTest);
        captureContact=button("Capture contact dialog",()->{releaseControls();if(service!=null)service.requestContactCapture();});controls.addView(captureContact);
        openTaskContact=button("Open task contact",()->{releaseControls();if(service!=null)service.requestOpenTaskContact();});controls.addView(openTaskContact);
        captureAcceptedTask=button("Capture accepted task",()->{releaseControls();if(service!=null)service.requestTaskCapture(false);});controls.addView(captureAcceptedTask);
        completeTask=button("Complete accepted task",()->{releaseControls();if(service!=null)service.requestCompleteAcceptedTask();});controls.addView(completeTask);
        captureCompletedTask=button("Capture completed task",()->{releaseControls();if(service!=null)service.requestTaskCapture(true);});controls.addView(captureCompletedTask);
        controls.addView(text("Atlas movement · hold a button",12,true));
        addMovementRow(controls,"Forward",'w',"Back",'s',120001);
        addMovementRow(controls,"Left",'a',"Right",'d',120003);
        controls.addView(movementButton("Jump",' ',120005));
        logs=text("",10,false);logs.setTypeface(Typeface.MONOSPACE);logs.setTextIsSelectable(true);controls.addView(logs);
        page.addView(text("First time: import every asset-pack part, tap Set up / update runtime, then on the Play tab create your character (sign in as COHLOCAL, offline) and save it once. After an interruption use Recover interrupted reports; Play resumes from the last save.",12,false));
        applyTestDetails();
    }
    private boolean testDetailsShown(){return testDetails!=null&&testDetails.isChecked();}
    private void applyTestDetails(){
        boolean shown=testDetailsShown();
        if(testTools!=null)testTools.setVisibility(shown?View.VISIBLE:View.GONE);
        if(state!=null){showStatus(state);updateCounter();}
    }
    /** The two lines above the tabs: plain words, or the session's own check wording with test details shown. */
    private void showStatus(ClientService.State next){
        String stage=next.storageBusy?"Storage":next.stage,line=next.storageBusy?next.storageStatus:next.detail;
        if(!testDetailsShown()&&!next.storageBusy){String[] plain=ClientZoning.plainStatus(stage,line);stage=plain[0];line=plain[1];}
        setTextIfChanged(status,stage);setTextIfChanged(detail,line);
    }
    private void category(LinearLayout parent,String name,String note){parent.addView(text(name,15,true));parent.addView(text(note,12,false));}
    private void selectTab(int index){
        if(menuPages==null)return;if(index<0||index>=menuPages.length)index=0;
        for(int i=0;i<menuPages.length;i++){menuPages[i].setVisibility(i==index?View.VISIBLE:View.GONE);menuTabs[i].setAlpha(i==index?1f:0.55f);menuTabs[i].setTypeface(Typeface.DEFAULT,i==index?Typeface.BOLD:Typeface.NORMAL);}
        if(menuTab!=index&&menuScroll!=null)menuScroll.scrollTo(0,0);menuTab=index;
        controlsPreferences.edit().putInt(CONTROLS_PREFIX+"tab",index).apply();
    }
    /** The options as a new install has them: ticked, then unticked (ClientRuntime's defaults). */
    private CheckBox[] recommendedTicked(){return new CheckBox[]{performanceGraphics,prootFastMode,sharedServerData,clientSkipServerFolders,clientFolderIndex,clientAudio,stockTravel,earlyZone,trustedBins,gameplay60,prootIoctlFilter,prootSocketFilter,prootCasefold,serverQuickStart,wineserverPathCache,physxCache,spareZone,serverX87,deferZoneLoads};}
    private CheckBox[] recommendedUnticked(){return new CheckBox[]{prestartNextZone,idleResidentMaps,sharedHeap,glDirect,clientGroupBins,keepPreviousZone,missionMaps,unlockAll,primalist};}
    private static String optionName(CheckBox box){String name=String.valueOf(box.getText());int cut=name.indexOf(" (");return cut>0?name.substring(0,cut):name;}
    /** The Optional category (owner, 2026-11-24): the owner's choice either way, so never "off recommended" on the screen. */
    private CheckBox[] optionalOptions(){return new CheckBox[]{keepPreviousZone};}
    private boolean optionalOption(CheckBox box){for(CheckBox optional:optionalOptions())if(optional==box)return true;return false;}
    private void recommendedChanged(){
        if(recommendedStatus==null)return;
        StringBuilder names=new StringBuilder(),chosen=new StringBuilder();int count=0;
        for(CheckBox box:recommendedTicked())if(box!=null&&!box.isChecked()){names.append(count++==0?"":"; ").append("unticked: ").append(optionName(box));}
        for(CheckBox box:recommendedUnticked())if(box!=null&&box.isChecked()){
            if(optionalOption(box)){chosen.append(chosen.length()==0?" Optional, on: ":"; ").append(optionName(box));continue;}
            names.append(count++==0?"":"; ").append("ticked: ").append(optionName(box));
        }
        if(chosen.length()>0)chosen.append(".");
        String line=count==0?"Options: all at the recommended settings."+chosen:"Options: "+count+" differ from the recommended settings ("+names+")."+chosen;
        int color=count==0?Color.rgb(150,214,160):Color.rgb(255,196,92);
        recommendedStatus.setText(line);recommendedStatus.setTextColor(color);
        // The same line above the tabs, only when something differs: the options are no longer on the first page.
        if(optionsNotice!=null){optionsNotice.setText(line);optionsNotice.setTextColor(color);optionsNotice.setVisibility(count==0?View.GONE:View.VISIBLE);}
    }
    private void restoreRecommendedOptions(){
        if(ClientRuntime.operationInProgress()){Toast.makeText(this,"Finish the current operation before changing options.",Toast.LENGTH_SHORT).show();return;}
        for(CheckBox box:recommendedTicked())if(box!=null&&!box.isChecked())box.setChecked(true);
        for(CheckBox box:recommendedUnticked())if(box!=null&&box.isChecked()&&!optionalOption(box))box.setChecked(false);
        recommendedChanged();
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
    // 0.13.62 (owner, 2026-11-08: "make it so controls aren't locked"): walking (the
    // on-screen pad, the controller's movement keys and jump) follows the ordinary game
    // input gate instead of waiting for the guest's proof that the character connected
    // (canSaveLogout). It still stops while Save / log out runs (moving cancels the game's
    // logout timer), after the save, during a zone transfer (ClientRuntime refuses gameplay
    // input) and while a typed command or the text dialog is pending.
    private boolean canWalk(){return inputActive&&service!=null&&state!=null&&!state.characterSaved&&!movementSuppressed&&!textDialogVisible&&!commandInputBusy()&&hasWindowFocus()&&movementWindowOpen();}
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
        if(zoningStatus!=null)setTextIfChanged(zoningStatus,service==null?"Start Play to travel.":service.zoningStatus());
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
    /** 0.13.85: the second hero slot can be used whenever nothing runs and the saved hero's data is complete or absent. */
    private void refreshHeroSlotControl(ClientService.State next){
        if(switchHero!=null)switchHero.setEnabled(profileIdle(next)&&next.profileState!=ClientRuntime.ProfileState.PRESERVE);
    }
    private void confirmSwitchHero(){
        if(!profileIdle(state))return;
        boolean other=ClientRuntime.otherHeroPresent(this);
        boolean saved=state.profileState==ClientRuntime.ProfileState.READY;
        String message=saved&&other?"Swap this saved game with the other one? Both are kept, each with all of its heroes."
                :saved?"Set this saved game aside? It is kept exactly as it is, and you can swap back here at any time. You do not need this to make another hero: use an empty slot in the game's character list."
                :other?"Bring the other saved game back?"
                :"There is no saved game in either place.";
        AlertDialog.Builder dialog=new AlertDialog.Builder(this).setTitle("Swap saved games").setMessage(message).setNegativeButton("Cancel",null);
        if(saved||other)dialog.setPositiveButton("Switch",(d,which)->{
            if(profileIdle(state)&&service!=null)Toast.makeText(this,service.switchHero(),Toast.LENGTH_LONG).show();
        });
        dialog.show();
    }
    private void confirmFreshProfile(){
        if(!canCreateFreshProfile(state))return;
        new AlertDialog.Builder(this).setTitle("Create fresh character?")
                .setMessage("This installation has no saved profile. Runtime setup and asset import do not restore a character database deleted by uninstalling. Start native character creation using your current runtime and imported assets, log in with COHLOCAL / offline and create your character, with any name the game accepts, as a hero, villain or Praetorian. With the game's own zone travel the game starts its starting zone after Enter Game (Atlas Park, Mercy Island, Nova Praetoria or a tutorial). Save character / log out, then Finish and export. Play resumes in the zone it was saved in.")
                .setNegativeButton("Cancel",null).setPositiveButton("Start character creation",(dialog,which)->{
                    // The profile or operation may change while this confirmation is open.
                    if(canCreateFreshProfile(state))request(ClientService.CREATE);
                }).show();
    }
    private void confirmResumeCreation(){
        if(!canResumeFirstCreation(state))return;
        new AlertDialog.Builder(this).setTitle("Resume first character creation?")
                .setMessage("Continue the first creation attempt using the existing initialized profile and imported assets. The database is preserved. Startup checks its real character rows. A character that was created but never entered the game (its first zone did not start) is removed first, and the report keeps a copy of its rows; any other existing character makes this request stop before the game opens. If your character was already saved, use Play. Log in with COHLOCAL / offline, create your character (any name the game accepts), then Save character / log out and Finish and export.")
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
        state=next;refreshTestControls();showStatus(next);setTextIfChanged(logs,next.log);updateCounter();
        recoverReports.setEnabled(!next.busy&&!next.storageBusy&&!next.reportExporting&&!ClientRuntime.operationInProgress());
        boolean diagnostics=diagnosticControlsReady(next,service!=null,exporting,ClientRuntime.operationInProgress());
        boolean idle=diagnostics&&!next.blocked;setup.setEnabled(idle);importAssets.setEnabled(idle);refreshProfileControls(next);refreshHeroSlotControl(next);performanceGraphics.setEnabled(idle);prootFastMode.setEnabled(idle);prestartNextZone.setEnabled(idle);trustedBins.setEnabled(idle);gameplay60.setEnabled(idle);idleResidentMaps.setEnabled(idle);sharedServerData.setEnabled(idle);clientSkipServerFolders.setEnabled(idle);clientFolderIndex.setEnabled(idle);clientAudio.setEnabled(idle);sharedHeap.setEnabled(idle);stockTravel.setEnabled(idle);earlyZone.setEnabled(idle);spareZone.setEnabled(idle);glDirect.setEnabled(idle);gpuProfile.setEnabled(idle);clientArchitecture.setEnabled(idle);storage.setEnabled(diagnostics);refreshAbortControl(next);export.setEnabled(diagnostics);
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
        if(!testDetailsShown()){
            long now=SystemClock.uptimeMillis();
            String line=ClientZoning.plainTiming(state.inputReady,state.characterSaved,remaining,state.readyDeadlineUptimeMillis>0,
                    Math.max(0,(state.saveDeadlineUptimeMillis-now+999)/1000),Math.max(0,(state.movementDeadlineUptimeMillis-now+999)/1000),
                    state.saveDeadlineUptimeMillis>0);
            setTextIfChanged(counter,line);counter.setVisibility(line.isEmpty()?View.GONE:View.VISIBLE);return;
        }
        counter.setVisibility(View.VISIBLE);
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
                .setMessage("First tap the game field. Account: COHLOCAL. Password: offline. Character name: any name the game accepts (one character per install).")
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
        // During a game the menu opens on Play: Resume game takes the focus (it is on that page).
        if(open&&changed&&gameSessionRunning())selectTab(0);
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
            final String maps=AssetPackStore.status(application,AssetPackStore.NAVIGATION_MAPS);
            runOnUiThread(()->{
                assetStatusChecking=false;assetStatusLoaded=true;
                if(!isDestroyed()){assetPackStatus.setText(text);navigationMapStatus.setText(maps);}
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
