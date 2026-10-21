package org.coh.nativecombined;

import org.coh.sessionclient.SessionNative;
import android.os.SystemClock;
import android.os.ParcelFileDescriptor;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

import android.app.Activity;
import android.content.Intent;
import android.hardware.input.InputManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.AtomicFile;
import android.view.KeyEvent;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.Surface;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import org.coh.systemsprobe.InputAdapter;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.security.MessageDigest;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

/** Reuses the accepted renderer/controller behavior and adds a crude visual
 * marker for a selected-self pose decoded from the real initial packet.
 * A position box does not complete costume or world replication. */
public final class NativeClientActivity extends Activity implements SurfaceHolder.Callback {
    private static final int EXPORT = 18;
    private static final int EXPORT_CAPTURE = 19;
    private final Object captureLife = new Object();
    private final AtomicBoolean captureQueued = new AtomicBoolean();
    private volatile long captureSavedFrame,captureRunSequence;
    private volatile String captureMetadata,captureFailure;
    private volatile String initialReplayMetadata,initialReplayFailure;
    private volatile String postReadyReplayMetadata,postReadyReplayFailure;
    private boolean postReadyReplayStorageReady,postReadyReplayAttempted;
    // Only networkWorker reads/writes these transport-attempt flags.
    private boolean initialReplayAttempted,initialReplayStorageReady;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final ExecutorService renderWorker = Executors.newSingleThreadExecutor();
    private final ExecutorService reportWorker = Executors.newSingleThreadExecutor();
    private final AtomicReference<byte[]> pendingReport = new AtomicReference<>();
    private final AtomicBoolean writerQueued = new AtomicBoolean();
    private final AtomicBoolean networkRetired=new AtomicBoolean(),rendererRetired=new AtomicBoolean();
    private final JSONArray events = new JSONArray();
    private volatile long handle;
    private volatile boolean destroying, writeFailed;
    private volatile boolean resumed;
    private boolean renderQueued, assetsVerified, exporting;
    private boolean returningToLauncher,sceneFullscreen;
    private android.widget.ScrollView controlsPanel;
    private Button fullscreenReturn;
    private int previousOrientation,previousSystemUi;

    private final Runnable returnDeadline = () -> finishReturnToLauncher(true);
    private long sequence, sessionStarted;
    private volatile long epoch;
    private String failure;
    private JSONObject assetManifest, apkIdentity;
    private Surface currentSurface;
    private SurfaceHolder currentHolder;
    private SurfaceView view;
    private FrameLayout scene;
    private TextView status, memoryStatus;
    private InputAdapter adapter;
    private InputManager inputManager;
    private int keys;
    private float axisX, axisY, axisZ, axisRz, touchX, touchY;
    private boolean touching;
    private byte[] frozenExport;
    private final ScheduledExecutorService networkWorker = Executors.newSingleThreadScheduledExecutor();
    private enum NetworkMode { LOCAL, WORLD_HANDOFF }
    private volatile NetworkMode networkMode = NetworkMode.LOCAL;
    private volatile String networkReport = "{\"phase\":\"IDLE\"}";
    private volatile String localNetworkReport = networkReport;
    private volatile String interopReport = "{\"schema\":\"coh-native-initial-interop-numeric-v1\",\"phase\":\"IDLE\",\"world_authority\":false}";
    private final HandoffState handoffState=new HandoffState(BuildConfig.FULLSCREEN_DIAGNOSTIC);
    private boolean captureTelemetryPublished;
    private volatile boolean networkForeground, networkConnecting, networkRequested;
    private volatile long networkAttempt;
    private volatile long networkOwnerAttempt=-1;
    private volatile long observedEntityAttempt=-1;
    private volatile int observedEntityIndex=-1;
    private volatile long costumeReadAttempt=-1;
    private long actorPreparationSequence;
    private boolean actorPreparing;
    private ImportContract.Control actorControl;
    private String runtimeActorFailure="";
    // Transport handle and policy identity are owned exclusively by networkWorker.
    private volatile long networkHandle;
    private long policyCheckedAt;
    private JSONObject networkPolicy;
    private boolean charactersPublished;
    private TextView networkStatus;
    private LinearLayout characterButtons;
    private android.widget.ScrollView charactersScroll;
    private Button connectButton, handoffButton;


    @Override public void onCreate(Bundle bundle) {
        super.onCreate(bundle);
        sessionStarted = System.currentTimeMillis();
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        LinearLayout controlsLayout = new LinearLayout(this);
        controlsLayout.setOrientation(LinearLayout.VERTICAL);
        android.widget.ScrollView controlsScroll = new android.widget.ScrollView(this) {
            @Override protected void onMeasure(int widthSpec, int heightSpec) {
                if (android.view.View.MeasureSpec.getMode(heightSpec) != android.view.View.MeasureSpec.UNSPECIFIED) {
                    int maximum = ViewportPolicy.controlsHeight(android.view.View.MeasureSpec.getSize(heightSpec), Integer.MAX_VALUE);
                    heightSpec = android.view.View.MeasureSpec.makeMeasureSpec(maximum, android.view.View.MeasureSpec.AT_MOST);
                }
                super.onMeasure(widthSpec, heightSpec);
            }
        };
        controlsPanel=controlsScroll;
        controlsScroll.setContentDescription("Native client controls");
        controlsScroll.addView(controlsLayout);
        layout.addView(controlsScroll, new LinearLayout.LayoutParams(-1, -2));
        if(BuildConfig.FULLSCREEN_DIAGNOSTIC){
            Button full=new Button(this);full.setText("Full screen");
            full.setOnClickListener(v->setSceneFullscreen(true));controlsLayout.addView(full);
        }
        Button launcher = new Button(this); launcher.setText("Return to launcher");
        launcher.setOnClickListener(v -> returnToLauncher());
        controlsLayout.addView(launcher, new LinearLayout.LayoutParams(-1, -2));
        TextView title = new TextView(this);
        title.setText("Native City of Heroes • Local development client");
        title.setTextSize(18); controlsLayout.addView(title);
        TextView controls = new TextView(this);
        controls.setText("Local scene preview • Left stick / WASD / D-pad: move • Right stick / drag: look\n"
                + "The Atlas preview can show one observed server entity as an orange position box. Full costume/world rendering is pending.");
        controlsLayout.addView(controls);
        LinearLayout networkButtons = new LinearLayout(this);
        connectButton = new Button(this); connectButton.setText("Connect local server");
        connectButton.setOnClickListener(v -> connectLocalServer(NetworkMode.LOCAL)); networkButtons.addView(connectButton);
        Button disconnect = new Button(this); disconnect.setText("Disconnect client");
        disconnect.setOnClickListener(v -> {
            networkRequested=false;networkAttempt++;
            clearObservedBox();
            characterButtons.removeAllViews(); charactersScroll.setVisibility(android.view.View.GONE);
            networkWorker.execute(() -> {
                if(networkHandle!=0){disconnectNetwork();publishNetwork();}
            });
        }); networkButtons.addView(disconnect); controlsLayout.addView(networkButtons);
        handoffButton = new Button(this); handoffButton.setText("Test world handoff");
        handoffButton.setOnClickListener(v -> connectLocalServer(NetworkMode.WORLD_HANDOFF));
        controlsLayout.addView(handoffButton);
        networkStatus = new TextView(this); networkStatus.setText("Server protocol: idle • Start the server in the launcher first.");
        controlsLayout.addView(networkStatus);
        characterButtons = new LinearLayout(this); characterButtons.setOrientation(LinearLayout.VERTICAL);
        charactersScroll = new android.widget.ScrollView(this);
        charactersScroll.addView(characterButtons);
        controlsLayout.addView(charactersScroll, new LinearLayout.LayoutParams(-1, (int)(144*getResources().getDisplayMetrics().density)));
        charactersScroll.setVisibility(android.view.View.GONE);
        LinearLayout buttons = new LinearLayout(this);
        Button reset = new Button(this); reset.setText("Reset actor");
        reset.setOnClickListener(v -> {
            if (handle != 0) { adapter.clear(); SessionNative.reset(handle); event("reset_requested"); saveReport(); }
        }); buttons.addView(reset);
        Button recreate = new Button(this); recreate.setText("Recreate");
        recreate.setOnClickListener(v -> { event("recreate_requested"); newSurface(); });
        buttons.addView(recreate);
        Button export = new Button(this); export.setText("Export report");
        export.setOnClickListener(v -> exportReport()); buttons.addView(export);
        if(BuildConfig.FRAME_CAPTURE_DIAGNOSTIC){
            Button capture=new Button(this);capture.setText("Export scene ZIP");
            capture.setOnClickListener(v->exportSceneCapture());controlsLayout.addView(capture);
            reportWorker.execute(()->{
                SceneFrameCapture.Selection selectedCapture=SceneFrameCapture.inspectCurrent(getFilesDir(),captureAppVersion(),
                        Long.toHexString(sessionStarted),BuildConfig.FULLSCREEN_DIAGNOSTIC);
                captureMetadata=selectedCapture.metadata();captureFailure=selectedCapture.omissionReason();
            });
        }
        Button distance = new Button(this); distance.setText("View distance");
        distance.setOnClickListener(v -> {
            if (handle != 0) SessionNative.viewDistance(handle);
            event("view_distance_requested"); saveReport();
        });
        controlsLayout.addView(buttons);
        controlsLayout.addView(distance);
        status = new TextView(this); status.setText("Preparing native scene…"); controlsLayout.addView(status);
        memoryStatus=new TextView(this);memoryStatus.setText("Memory observation pending");controlsLayout.addView(memoryStatus);
        Button sampleMemory=new Button(this);sampleMemory.setText("Sample memory");
        sampleMemory.setOnClickListener(v->MemoryTelemetry.request(this,PhaseMemoryDiagnostics.Phase.DIAGNOSTIC));controlsLayout.addView(sampleMemory);
        scene = new FrameLayout(this); layout.addView(scene, new LinearLayout.LayoutParams(-1, 0, 1));
        FrameLayout screen=new FrameLayout(this);
        screen.addView(layout,new FrameLayout.LayoutParams(-1,-1));
        fullscreenReturn=new Button(this);fullscreenReturn.setText("Return to controls");
        fullscreenReturn.setContentDescription("Return to native client controls");
        fullscreenReturn.setOnClickListener(v->setSceneFullscreen(false));
        FrameLayout.LayoutParams corner=new FrameLayout.LayoutParams(-2,-2,Gravity.TOP|Gravity.END);
        int inset=(int)(8*getResources().getDisplayMetrics().density);corner.setMargins(inset,inset,inset,inset);
        screen.addView(fullscreenReturn,corner);fullscreenReturn.setVisibility(android.view.View.GONE);
        scene.addOnLayoutChangeListener((v,l,t,r,b,ol,ot,oright,ob)->publishCaptureViewport());
        setContentView(screen);
        adapter = new InputAdapter(new InputAdapter.Sink() {
            public void focus(boolean focused) {
                if(destroying)return;
                if (!focused) {
                    event("input_clear_requested");
                    keys = 0; axisX = axisY = axisZ = axisRz = 0; touching = false;
                    if (handle != 0) SessionNative.focus(handle);
                }
            }
            public void key(int key, boolean down) {
                if(destroying)return;
                if (down) keys |= 1 << key; else keys &= ~(1 << key);
                sendInput();
                event(down ? "key_down" : "key_up"); saveReport();
            }
            public void axes(float x, float y, float z, float rz) {
                if(destroying)return;
                axisX=x; axisY=y; axisZ=z; axisRz=rz; sendInput();
            }
            public void touch(int action, int pointer, float x, float y) {
                if(destroying)return;
                if (action == 0) { touching = true; touchX=x; touchY=y; }
                else if (action == 1 && touching) {
                    if (handle != 0) SessionNative.look(handle, (x-touchX)*1.2f, (y-touchY)*1.2f);
                    touchX=x; touchY=y;
                } else if (action == 2 || action == 3) touching=false;
            }
        });
        inputManager = (InputManager)getSystemService(INPUT_SERVICE);
        if (inputManager != null) inputManager.registerInputDeviceListener(adapter, main);
        newSurface(); event("session_created");
        renderWorker.execute(() -> {
            try {
                JSONObject manifest = new JSONObject(new String(readAsset("asset-manifest.json"), StandardCharsets.UTF_8));
                JSONObject records = manifest.getJSONObject("assets");
                JSONObject buildInputs = BuildConfig.NEIGHBORHOOD_DIAGNOSTIC
                        ? new JSONObject(new String(readAsset("combined/build-inputs.json"), StandardCharsets.UTF_8)) : null;
                JSONObject neighborhoodRecords = buildInputs == null ? null : buildInputs.getJSONObject("neighborhood").getJSONObject("assets");
                String[] names = {"world.bin", "character.bin", "rig.bin", "morph.bin", "locomotion.bin", "walkable.bin",
                        BuildConfig.NEIGHBORHOOD_DIAGNOSTIC?"neighborhood-map.bin":"map.bin"};
                byte[][] bytes = new byte[names.length][];
                for (int i=0; i<names.length; i++) {
                    bytes[i] = readAsset(names[i]); JSONObject pin = sceneAssetPin(records, neighborhoodRecords, names[i]);
                    if (pin.getLong("bytes") != bytes[i].length || !pin.getString("sha256").equals(sha(bytes[i])))
                        throw new IllegalStateException("Asset integrity: " + names[i]);
                }
                JSONObject apk = apkIdentity();
                long result = SessionNative.createSession(bytes[0], bytes[1], bytes[2], bytes[3], bytes[4], bytes[5], bytes[6]);
                if (result == 0) throw new IllegalStateException("Native scene rejected its fixtures");
                try {
                if(BuildConfig.FULLSCREEN_DIAGNOSTIC){
                    try(RuntimeWorldInputs inputs=RuntimeWorldInputs.open(this,new ImportStore(this,(phase,done,total)->{}),
                            buildInputs.getJSONObject("live_world").getJSONObject("assets").getJSONObject("live-world.bin"),new ImportContract.Control())){
                        long javaPayload=inputs.stagingPayloadBytes();for(byte[] source:bytes)javaPayload=Math.addExact(javaPayload,source.length);
                        int admitted=SessionNative.runtimeWorld(result,inputs.fds,inputs.offsets,inputs.lengths,javaPayload);
                        main.post(()->event(admitted==1?"runtime_world_attached":"runtime_world_fallback"));
                    }catch(Exception optional){String reason=optional.getClass().getSimpleName()+": "+optional.getMessage();
                        main.post(()->{if(destroying)return;runtimeWorldFailure=reason.length()>160?reason.substring(0,160):reason;event("runtime_world_import_unavailable");saveReport();});}
                }
                handle = result;result=0;
                }finally{if(result!=0)SessionNative.destroy(result);}
                main.post(() -> {
                    if (destroying) return;
                    assetManifest=manifest; apkIdentity=apk; assetsVerified=true;
                    SessionNative.state(handle,epoch,resumed);
                    event("assets_loaded"); requestRender(); saveReport();
                });
            } catch (Exception ex) {
                main.post(() -> { if(destroying)return; failure=ex.toString(); event("load_failed"); saveReport(); });
            }
        });
        networkWorker.scheduleWithFixedDelay(this::networkTick, 0, 20, TimeUnit.MILLISECONDS);
        main.post(poll);
    }
    private void returnToLauncher() {
        if(destroying || returningToLauncher || isFinishing())return;
        returningToLauncher=true;
        networkForeground=false;networkRequested=false;networkAttempt++;
        event("return_to_launcher_requested");saveReport();
        // Capture client suspension without waiting on its owner from the UI
        // thread. Normal pause/destroy still own input/render/handle teardown.
        main.postDelayed(returnDeadline,2000);
        networkWorker.execute(() -> {
            if(networkHandle!=0){suspendNetwork();publishNetwork();}
            MemoryTelemetry.request(this,PhaseMemoryDiagnostics.Phase.RETURN);
            main.post(() -> finishReturnToLauncher(false));
        });
    }
    private void finishReturnToLauncher(boolean deadlineExpired) {
        if(destroying || !returningToLauncher || isFinishing())return;
        main.removeCallbacks(returnDeadline);
        event(deadlineExpired ? "return_to_launcher_cleanup_pending" : "return_to_launcher_ready");
        saveReport();
        // A normal launcher→client stack retains MainActivity underneath.
        // A direct client task needs its launcher created before it finishes.
        if(isTaskRoot())startActivity(new Intent(this,MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP|Intent.FLAG_ACTIVITY_SINGLE_TOP));
        finish();
    }
    private JSONObject localPolicy() throws Exception {
        String supplied=getIntent().getStringExtra("session_policy_path");
        File files=getFilesDir().getCanonicalFile();
        File file=new File(supplied==null ? new File(files,"native-session-policy.json").getPath() : supplied).getCanonicalFile();
        if(!file.getPath().startsWith(files.getPath()+File.separator)||!file.isFile()||file.length()<2||file.length()>16384)
            throw new IllegalStateException("Policy unavailable");
        ByteArrayOutputStream bytes=new ByteArrayOutputStream();
        try(InputStream input=new FileInputStream(file)) {
            byte[] chunk=new byte[1024];int count;
            while((count=input.read(chunk))!=-1){if(bytes.size()+count>16384)throw new IllegalStateException("Policy too large");bytes.write(chunk,0,count);}
        }
        JSONObject p=new JSONObject(new String(bytes.toByteArray(),StandardCharsets.UTF_8));
        long age=SystemClock.elapsedRealtime()-p.getLong("ready_elapsed_ms");
        if(!"coh-native-local-policy-v1".equals(p.getString("schema"))||!"ready".equals(p.getString("state"))
                ||!"127.0.0.1".equals(p.getString("db_address"))||age<0||age>15000
                ||!p.getString("server_session_id").matches("[a-fA-F0-9]{32}")
                ||!p.getString("import_generation").matches("[a-fA-F0-9]{32}")
                ||!p.getString("account").matches("[A-Za-z0-9_-]{1,14}")
                ||p.getInt("db_port")<1||p.getInt("db_port")>65535||p.getInt("net_version")<0||p.getInt("net_version")>5)
            throw new IllegalStateException("Policy rejected");
        // Require explicit booleans: absence never weakens encryption policy.
        p.getBoolean("encryption_required");p.getBoolean("outbound_compressed");return p;
    }
    private void connectLocalServer(NetworkMode mode) {
        if(destroying||returningToLauncher||networkConnecting||!networkForeground)return;
        if(mode==NetworkMode.WORLD_HANDOFF&&networkMode==mode&&handoffState.blocksNewAttempt())return;
        final long attempt=++networkAttempt;networkRequested=true;
        clearObservedBox();
        if(BuildConfig.FRAME_CAPTURE_DIAGNOSTIC){
            final long run=++captureRunSequence;captureMetadata=null;captureFailure="CAPTURE_CURRENT_RUN_PENDING";
            reportWorker.execute(()->{
                if(run!=captureRunSequence)return;
                try{SceneFrameCapture.clear(getFilesDir());}
                catch(Exception unavailable){captureFailure="CAPTURE_STORAGE_CLEAR_FAILED";}
            });
        }
        MemoryTelemetry.request(this,PhaseMemoryDiagnostics.Phase.NATIVE_CONNECTION);
        networkConnecting=true;connectButton.setEnabled(false);handoffButton.setEnabled(false);
        characterButtons.removeAllViews();charactersScroll.setVisibility(android.view.View.GONE);
        networkStatus.setText(mode==NetworkMode.WORLD_HANDOFF
                ? "World handoff test: connecting… An observed server entity will appear as a crude box."
                : "Server protocol: connecting to the local development server…");
        event(mode==NetworkMode.WORLD_HANDOFF?"world_handoff_requested":"local_connect_requested");
        networkWorker.execute(() -> {
            try {
                if(!networkForeground||!networkRequested||attempt!=networkAttempt)return;
                retireNetworkOwner();networkMode=mode;charactersPublished=false;
                postReadyReplayMetadata=null;postReadyReplayFailure=null;
                postReadyReplayStorageReady=false;postReadyReplayAttempted=false;
                if(BuildConfig.FRAME_CAPTURE_DIAGNOSTIC){
                    initialReplayMetadata=null;initialReplayFailure=null;initialReplayAttempted=false;initialReplayStorageReady=false;
                    try{InitialReplayStore.clear(getFilesDir());initialReplayStorageReady=true;}
                    catch(Exception unavailable){initialReplayFailure="INITIAL replay storage unavailable";}
                }
                JSONObject policy=localPolicy();
                if(!networkForeground||!networkRequested||attempt!=networkAttempt)return;
                networkPolicy=policy;
                policyCheckedAt=SystemClock.elapsedRealtime();
                if(mode==NetworkMode.WORLD_HANDOFF) {
                    String cachePath=null;
                    try {
                        File data=new ImportStore(this,(phase,done,total)->{}).gameDataDirectory();
                        if(data!=null)cachePath=new File(data,"bin/BodyParts.bin").getCanonicalPath();
                    } catch(Exception unavailable) { /* A missing cache does not prevent pose observation. */ }
                    InteropNative.configureBodyPartsCache(cachePath);
                    if(BuildConfig.CLIENT_SLOT_DICTIONARY)InteropNative.configureClientSlots(getAssets());
                }
                networkHandle=mode==NetworkMode.WORLD_HANDOFF
                        ? InteropNative.begin(policy.getInt("db_port"),policy.getString("account"),policy.getInt("net_version"),
                            policy.getBoolean("encryption_required"),policy.getBoolean("outbound_compressed"),policyCheckedAt)
                        : LocalNative.begin(policy.getInt("db_port"),policy.getString("account"),policy.getInt("net_version"),
                            policy.getBoolean("encryption_required"),policy.getBoolean("outbound_compressed"),policyCheckedAt);
                networkOwnerAttempt=attempt;
                if(networkHandle==0)throw new IllegalStateException("Local owner rejected policy");
                preparePostReadyReplay();
                if(mode==NetworkMode.WORLD_HANDOFF){handoffState.begin();captureTelemetryPublished=false;}
                publishNetwork();
            } catch(Exception problem) {
                storeNetworkReport("{\"phase\":\"POLICY_UNAVAILABLE\",\"live_world_rendered\":false,\"authserver_authenticated\":false,\"world_authority\":false}");
                main.post(() -> {if(!destroying)updateNetworkUi();});
            } finally {
                if(mode==NetworkMode.WORLD_HANDOFF&&BuildConfig.CLIENT_SLOT_DICTIONARY&&networkHandle==0)
                    InteropNative.configureClientSlots(null);
                networkConnecting=false;main.post(() -> {if(!destroying)updateNetworkUi();});
            }
        });
    }
    private boolean sameNetworkPolicy(JSONObject policy) throws Exception {
        if(networkPolicy==null)return false;
        for(String key:new String[]{"server_session_id","import_generation","account","db_address"})
            if(!networkPolicy.getString(key).equals(policy.getString(key)))return false;
        for(String key:new String[]{"db_port","net_version"})
            if(networkPolicy.getInt(key)!=policy.getInt(key))return false;
        for(String key:new String[]{"encryption_required","outbound_compressed"})
            if(networkPolicy.getBoolean(key)!=policy.getBoolean(key))return false;
        return true;
    }
    // Every handle operation runs on networkWorker, including mode switches.
    private void disconnectNetwork() {
        if(networkMode==NetworkMode.WORLD_HANDOFF){saveInitialReplay();InteropNative.disconnect(networkHandle);savePostReadyReplay();handoffState.stopped();}
        else LocalNative.disconnect(networkHandle);
    }
    private void suspendNetwork() {
        if(networkMode==NetworkMode.WORLD_HANDOFF){saveInitialReplay();InteropNative.suspend(networkHandle);savePostReadyReplay();handoffState.stopped();}
        else LocalNative.suspend(networkHandle);
    }
    private void retireNetworkOwner() {
        final long retiring=networkHandle;final NetworkMode mode=networkMode;
        try {
            if(retiring==0)return;
            try { disconnectNetwork();publishNetwork(); }
            finally {
                if(mode==NetworkMode.WORLD_HANDOFF)InteropNative.close(retiring);
                else LocalNative.close(retiring);
            }
        } finally {networkHandle=0;networkOwnerAttempt=-1;networkPolicy=null;if(mode==NetworkMode.WORLD_HANDOFF)handoffState.retired();}
    }
    private void networkTick() {
        if(destroying||!networkForeground||!networkRequested||networkHandle==0)return;
        final long tickHandle=networkHandle,tickAttempt=networkOwnerAttempt;
        if(tickAttempt!=networkAttempt)return;
        try {
            // JSON is diagnostic output. Completion and ownership come from the
            // same serialized native executor even if a report is unavailable.
            if(networkMode==NetworkMode.WORLD_HANDOFF) {
                handoffState.control(InteropNative.controlState(networkHandle));
                if(!handoffState.shouldService()){publishObservedSelf(tickHandle,tickAttempt);return;}
            }
            long now=SystemClock.elapsedRealtime();
            if(now-policyCheckedAt>=1000) {
                JSONObject policy=localPolicy();
                if(!sameNetworkPolicy(policy))throw new IllegalStateException("Server policy replaced");
                policyCheckedAt=now;
            }
            String phase=new JSONObject(networkReport).optString("phase","UNKNOWN");
            if(networkMode!=NetworkMode.WORLD_HANDOFF&&("SUSPENDED".equals(phase)||"CLOSED".equals(phase)||"CANCELLED".equals(phase)
                    ||"FAILED".equals(phase)||"TIMED_OUT".equals(phase)||"UNSUPPORTED".equals(phase)
                    ||"INITIAL_OBSERVED".equals(phase)||"POLICY_UNAVAILABLE".equals(phase)))return;
            if(networkMode==NetworkMode.WORLD_HANDOFF)InteropNative.service(networkHandle,now);
            else LocalNative.service(networkHandle,now);
            if(networkMode==NetworkMode.WORLD_HANDOFF)publishObservedSelf(tickHandle,tickAttempt);
            publishNetwork();
            if(!charactersPublished&&(networkMode==NetworkMode.WORLD_HANDOFF?handoffState.charactersReady():
                    "CHARACTERS_READY".equals(new JSONObject(networkReport).optString("phase")))) {
                byte[] list=networkMode==NetworkMode.WORLD_HANDOFF?InteropNative.characters(networkHandle):LocalNative.characters(networkHandle);
                if(list!=null) {
                    JSONArray characters=new JSONArray(new String(list,StandardCharsets.UTF_8));
                    charactersPublished=true;
                    final long attempt=networkAttempt;
                    main.post(() -> {if(!destroying&&networkForeground&&networkRequested&&attempt==networkAttempt)showCharacters(characters,attempt);});
                }
            }
        } catch(Exception problem) {
            suspendNetwork();publishNetwork();
            main.post(() -> {if(!destroying)networkStatus.setText("Client suspended • Start/verify the local server, then connect again.");});
        }
    }
    private void publishObservedSelf(final long sourceHandle,final long attempt) {
        if(BuildConfig.CONTINUATION_DIAGNOSTIC)publishObservedCostume(sourceHandle,attempt);
        if(sourceHandle!=networkHandle||attempt!=networkAttempt||attempt!=networkOwnerAttempt
                ||observedEntityAttempt==attempt)return;
        byte[] raw=InteropNative.observedSelfPose(sourceHandle);
        if(raw==null||raw.length!=16)return;
        ByteBuffer pose=ByteBuffer.wrap(raw).order(ByteOrder.LITTLE_ENDIAN);
        final int index=pose.getInt();
        final float x=pose.getFloat(),y=pose.getFloat(),z=pose.getFloat();
        if(index<=0||index>10239||!Float.isFinite(x)||!Float.isFinite(y)||!Float.isFinite(z))return;
        main.post(() -> {
            if(destroying||!networkRequested||!networkForeground||attempt!=networkAttempt||handle==0
                    ||sourceHandle!=networkHandle||attempt!=networkOwnerAttempt
                    ||networkMode!=NetworkMode.WORLD_HANDOFF||observedEntityAttempt==attempt)return;
            if(BuildConfig.FULLSCREEN_DIAGNOSTIC)setSceneFullscreen(true);
            SessionNative.observedEntity(handle,index,x,y,z);
            observedEntityIndex=index;observedEntityAttempt=attempt;
            event("observed_server_entity_box_requested");updateNetworkUi();saveReport();
        });
    }
    private void clearObservedBox() {
        actorPreparationSequence++;actorPreparing=false;costumeReadAttempt=-1;
        if(actorControl!=null){actorControl.cancel();actorControl=null;}
        runtimeActorFailure="";
        observedEntityAttempt=-1;observedEntityIndex=-1;
        if(handle!=0)SessionNative.clearObservedEntity(handle);
    }
    // Called only by networkWorker. Getter and source accounting refer to the
    // same serialized transport owner; no live transport pointer crosses JNI.
    private void publishObservedCostume(final long sourceHandle,final long attempt) {
        if(sourceHandle!=networkHandle||attempt!=networkAttempt||attempt!=networkOwnerAttempt
                ||networkMode!=NetworkMode.WORLD_HANDOFF||observedEntityAttempt!=attempt||costumeReadAttempt==attempt)return;
        final byte[] frame=InteropNative.observedSelfCostume(sourceHandle);
        if(frame==null)return;
        final long sourceBytes=InteropNative.observedSelfCostumeSourceBytes(sourceHandle);
        if(sourceBytes<0)return;
        costumeReadAttempt=attempt;
        main.post(()->{
            if(destroying||!networkRequested||!networkForeground||attempt!=networkAttempt
                    ||sourceHandle!=networkHandle||attempt!=networkOwnerAttempt
                    ||networkMode!=NetworkMode.WORLD_HANDOFF||observedEntityAttempt!=attempt||handle==0)return;
            final long renderer=handle,preparation=++actorPreparationSequence;
            final ImportContract.Control control=new ImportContract.Control();actorControl=control;
            actorPreparing=true;runtimeActorFailure="";
            // End the current EGL loop before CPU preparation; this same worker
            // serializes rendering, archive reads, candidate publication and destroy.
            epoch++;SessionNative.state(renderer,epoch,false);
            renderWorker.execute(()->{
                int admitted=-1;String problem=null;
                try(RuntimeActorInputs inputs=RuntimeActorInputs.open(this,new ImportStore(this,(phase,done,total)->{}),control)) {
                    control.check();
                    if(!destroying&&networkRequested&&networkForeground&&renderer==handle&&attempt==networkAttempt
                            &&sourceHandle==networkHandle&&attempt==networkOwnerAttempt
                            &&networkMode==NetworkMode.WORLD_HANDOFF&&observedEntityAttempt==attempt)
                        admitted=SessionNative.observedCostume(renderer,frame,inputs.fds,inputs.offsets,inputs.lengths,
                                Math.addExact(frame.length,inputs.stagingPayloadBytes()),sourceBytes);
                }catch(Exception optional){problem=optional.getClass().getSimpleName()+": "+optional.getMessage();}
                final int result=admitted;final String error=problem;
                main.post(()->{
                    if(preparation!=actorPreparationSequence||destroying||renderer!=handle)return;
                    actorPreparing=false;actorControl=null;
                    if(attempt!=networkAttempt||sourceHandle!=networkHandle||attempt!=networkOwnerAttempt
                            ||networkMode!=NetworkMode.WORLD_HANDOFF||!networkRequested||!networkForeground
                            ||observedEntityAttempt!=attempt)return;
                    runtimeActorFailure=error==null?(result==0?"":"Native costume preparation status "+result):error;
                    if(runtimeActorFailure.length()>160)runtimeActorFailure=runtimeActorFailure.substring(0,160);
                    if(result==5||result==7)costumeReadAttempt=-1; // lifecycle interruption may be retried
                    SessionNative.state(renderer,epoch,resumed);
                    publishCaptureViewport();
                    event(result==0?"observed_costume_published":"observed_costume_box_fallback");
                    requestRender();saveReport();
                });
            });
        });
    }
    private String checkedHandoffReport(String next) {
        JSONObject report;
        try {report=new JSONObject(next);}
        catch(Exception invalid) {report=new JSONObject();}
        try {
            boolean sourceSchema="coh-native-initial-interop-numeric-v1".equals(report.opt("schema"));
            if(!(report.opt("schema") instanceof String))report.put("schema","coh-native-initial-interop-numeric-v1");
            report.put("diagnostic_only",true);
            for(String flag:new String[]{"authserver_authenticated","source_generation_admitted","complete_initial_character",
                    "actor_publication","ack_permitted","world_authority","live_world_rendered"})
                if(!(report.opt(flag) instanceof Boolean))report.put(flag,false);
            String phase=report.optString("phase","REPORT_UNAVAILABLE");
            handoffState.phase(phase);
            if(report.opt("raw_allents_observed") instanceof Boolean
                    &&!Boolean.FALSE.equals(report.opt("initial_observation_known"))
                    &&(Boolean.TRUE.equals(report.opt("raw_allents_observed"))
                        ||Boolean.TRUE.equals(report.opt("initial_observation_known"))||handoffState.controlKnown()))
                handoffState.initial(report.getBoolean("raw_allents_observed"));
            JSONArray boundary=report.optJSONArray("catalog_boundary");
            if(boundary!=null&&boundary.length()==7) {
                long[] values=new long[7];boolean exact=true;
                for(int i=0;i<values.length;i++) {
                    Object value=boundary.opt(i);
                    if(!(value instanceof Integer)&&!(value instanceof Long)){exact=false;break;}
                    values[i]=((Number)value).longValue();
                }
                if(exact)handoffState.catalogBoundary(values,sourceSchema&&Boolean.TRUE.equals(report.opt("raw_allents_observed")));
            }
            long[] boundarySaved=handoffState.catalogBoundary();
            if(boundarySaved!=null) {
                JSONArray retained=new JSONArray();for(long value:boundarySaved)retained.put(value);
                report.put("catalog_boundary",retained);
            }
            JSONObject first=report.optJSONObject("first_failure");
            if(first!=null&&Boolean.TRUE.equals(first.opt("valid"))) {
                String[] fields={"local_phase","db_phase","map_phase","status","failure"};
                long[] values=new long[fields.length];boolean numeric=true;
                for(int i=0;i<fields.length;i++) {
                    Object value=first.opt(fields[i]);
                    if(!(value instanceof Number)||((Number)value).longValue()<0){numeric=false;break;}
                    values[i]=((Number)value).longValue();
                }
                if(numeric)handoffState.firstFailure(values[0],values[1],values[2],values[3],values[4]);
            }
            long[] saved=handoffState.firstFailure();
            if(saved!=null)report.put("first_failure",new JSONObject().put("valid",true)
                    .put("local_phase",saved[0]).put("db_phase",saved[1]).put("map_phase",saved[2])
                    .put("status",saved[3]).put("failure",saved[4]));
            report.put("phase",phase).put("last_observed_phase",handoffState.lastPhase())
                    .put("control_observation",new JSONObject().put("source","native_scalar_control_state")
                        .put("owner_present",handoffState.ownerPresent()).put("known",handoffState.controlKnown())
                        .put("owner_terminal",handoffState.terminal())
                        .put("initial_observed",handoffState.initialObserved()==null?JSONObject.NULL:handoffState.initialObserved()))
                    .put("report_serialization_unknown","REPORT_LIMIT".equals(phase)||"REPORT_UNAVAILABLE".equals(phase));
            return report.toString();
        } catch(Exception unavailable) {
            // Fixed fallback retains no identity/packet or exception text. The
            // independent control state and first failure remain in memory.
            return "{\"schema\":\"coh-native-initial-interop-numeric-v1\",\"diagnostic_only\":true,\"phase\":\"REPORT_UNAVAILABLE\",\"source_generation_admitted\":false,\"complete_initial_character\":false,\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false,\"live_world_rendered\":false}";
        }
    }
    private void storeNetworkReport(String next) {
        if(networkMode==NetworkMode.WORLD_HANDOFF){next=checkedHandoffReport(next);interopReport=next;}else localNetworkReport=next;
        networkReport=next;
    }
    // Runs only on the serialized network owner before suspend/disconnect/close.
    // Optional replay failures never change transport or character admission.
    private void saveInitialReplay(){
        if(!BuildConfig.FRAME_CAPTURE_DIAGNOSTIC||!initialReplayStorageReady||initialReplayAttempted
                ||networkMode!=NetworkMode.WORLD_HANDOFF||networkHandle==0)return;
        byte[] raw=null;
        try{
            handoffState.control(InteropNative.controlState(networkHandle));
            if(!Boolean.TRUE.equals(handoffState.initialObserved()))return;
            initialReplayAttempted=true;
            raw=InteropNative.exportInitialReplay(networkHandle);
            if(raw==null){initialReplayFailure="INITIAL replay omitted";return;}
            initialReplayMetadata=InitialReplayStore.save(getFilesDir(),raw,
                    getPackageManager().getPackageInfo(getPackageName(),0).versionCode,Long.toHexString(sessionStarted));
            initialReplayFailure=null;
        }catch(Exception unavailable){initialReplayFailure=unavailable.getClass().getSimpleName();}
        catch(OutOfMemoryError optionalReplay){initialReplayFailure="INITIAL replay memory unavailable";}
        finally{if(raw!=null)java.util.Arrays.fill(raw,(byte)0);}
    }
    /** Optional fixture I/O stays on the serialized network owner. Native owns
     * its duplicate; Java closes the attaching descriptor before any service. */
    private void preparePostReadyReplay() {
        if(!BuildConfig.POST_READY_REPLAY_DIAGNOSTIC||networkMode!=NetworkMode.WORLD_HANDOFF||networkHandle==0)return;
        try {
            File stage=PostReadyReplayStore.prepare(getFilesDir());
            try(ParcelFileDescriptor fd=ParcelFileDescriptor.open(stage,ParcelFileDescriptor.MODE_WRITE_ONLY)) {
                int status=InteropNative.configurePostReadyReplay(networkHandle,fd.getFd());
                if(status!=0)throw new java.io.IOException("Native fixture storage status "+status);
            }
            postReadyReplayStorageReady=true;postReadyReplayFailure="POST_READY_REPLAY_RECORDING";
        }catch(Exception unavailable){postReadyReplayFailure="POST_READY_REPLAY_STORAGE_"+unavailable.getClass().getSimpleName();}
        catch(OutOfMemoryError optional){postReadyReplayFailure="POST_READY_REPLAY_MEMORY_UNAVAILABLE";}
    }
    private void savePostReadyReplay() {
        if(!BuildConfig.POST_READY_REPLAY_DIAGNOSTIC||!postReadyReplayStorageReady||postReadyReplayAttempted
                ||networkMode!=NetworkMode.WORLD_HANDOFF||networkHandle==0)return;
        if((InteropNative.controlState(networkHandle)&2)==0)return;
        postReadyReplayAttempted=true;
        try {
            postReadyReplayMetadata=PostReadyReplayStore.seal(getFilesDir(),BuildConfig.VERSION_CODE,Long.toHexString(sessionStarted));
            postReadyReplayFailure=null;
        }catch(Exception unavailable){postReadyReplayFailure="POST_READY_REPLAY_SEAL_"+unavailable.getClass().getSimpleName();}
        catch(OutOfMemoryError optional){postReadyReplayFailure="POST_READY_REPLAY_MEMORY_UNAVAILABLE";}
    }
    private void publishNetwork() {
        if(networkHandle==0)return;
        if(networkMode==NetworkMode.WORLD_HANDOFF)handoffState.control(InteropNative.controlState(networkHandle));
        savePostReadyReplay();
        String next=networkMode==NetworkMode.WORLD_HANDOFF?InteropNative.report(networkHandle):LocalNative.report(networkHandle);
        String previous=networkReport;storeNetworkReport(next);
        saveInitialReplay();
        if(!networkReport.equals(previous)) {
            if(networkMode==NetworkMode.WORLD_HANDOFF&&Boolean.TRUE.equals(handoffState.initialObserved())&&!captureTelemetryPublished) {
                captureTelemetryPublished=true;MemoryTelemetry.request(this,PhaseMemoryDiagnostics.Phase.DIAGNOSTIC);
            }
            main.post(() -> {if(!destroying)updateNetworkUi();});
        }
    }
    private void updateNetworkUi() {
        try {
            JSONObject report=new JSONObject(networkReport);String phase=report.optString("phase","UNKNOWN");
            boolean active=networkMode==NetworkMode.WORLD_HANDOFF?handoffState.blocksNewAttempt():"DB_CONNECTING".equals(phase)||"CHARACTERS_READY".equals(phase)
                    ||"MAP_CONNECTING".equals(phase)||"SCENE_INCOMPLETE".equals(phase)
                    ||"WAIT_GROUPS".equals(phase)||"WAIT_ALLENTS".equals(phase);
            boolean available=networkForeground&&!networkConnecting&&!returningToLauncher;
            connectButton.setEnabled(available&&(!active||networkMode!=NetworkMode.LOCAL));
            handoffButton.setEnabled(available&&(!active||networkMode!=NetworkMode.WORLD_HANDOFF));
            if(networkMode==NetworkMode.WORLD_HANDOFF) {
                String detail=handoffState.charactersReady()?"Select an existing disposable-profile character."
                        : handoffState.catalogDetail()!=null?handoffState.catalogDetail()
                        : Boolean.TRUE.equals(handoffState.initialObserved())?"Raw initial update observed. Complete character decoding remains pending."
                        : "WAIT_GROUPS".equals(phase)||"MAP_CONNECTING".equals(phase)?"Waiting for Map scene data (GROUPS)."
                        : "WAIT_ALLENTS".equals(phase)?"GROUPS received; REQALLENTS queued. Waiting for a raw initial update."
                        : "INITIAL_OBSERVED".equals(phase)?"Raw initial update observed. Complete character decoding remains pending."
                        : "TIMED_OUT".equals(phase)?"The handoff attempt timed out. Export the report."
                        : "FAILED".equals(phase)||"UNSUPPORTED".equals(phase)?"The handoff attempt stopped. Export the report."
                        : "POLICY_UNAVAILABLE".equals(phase)?"Start/verify the server in the launcher, then try again."
                        : "SUSPENDED".equals(phase)?"Suspended; tap Test world handoff for a fresh attempt."
                        : "CLOSED".equals(phase)||"CANCELLED".equals(phase)?"Handoff test stopped."
                        : "Real DB/Map diagnostic progress only.";
                JSONArray continuation=report.optJSONArray("costume_continuation");
                JSONArray defaults=report.optJSONArray("bodyparts_default");
                if(defaults!=null&&defaults.length()==2&&defaults.optInt(0,-1)!=0
                        &&Boolean.TRUE.equals(handoffState.initialObserved()))
                    detail="The common BodyParts.bin file could not be matched. Export the report; its earlier entity pose can still be drawn.";
                if(continuation!=null&&continuation.length()==12&&continuation.optInt(8,0)==1) {
                    int field=continuation.optInt(1,-1),dictionary=continuation.optInt(7,0);
                    String fieldName=field==3?"geometry":field==4?"first texture":field==5?"second texture"
                            :field==6?"FX":field==7?"color":field==8?"region":field==9?"body set":"header";
                    String dependency=dictionary==3?"the costume palette":dictionary==2?"the extra costume strings":"the costume strings";
                    detail=continuation.optInt(9,0)==1?"Original costume body decoded ("+continuation.optInt(4,0)
                              +" parts, "+continuation.optInt(5,0)+" strings, "+continuation.optInt(6,0)+" colors)."
                            : "BodyPart count verified; costume "+fieldName
                              +(dictionary!=0?" requires "+dependency:" remains incomplete")+".";
                    JSONArray slots=report.optJSONArray("client_slots");
                    if(slots!=null&&slots.length()==4&&slots.optInt(0,0)!=0&&dictionary!=0)
                        detail="Bundled CLIENT slots unavailable (native status "+slots.optInt(0,0)
                                +"); original costume receiver stopped at "+fieldName+".";
                    JSONArray bodies=report.optJSONArray("costume_bodies");
                    if(bodies!=null&&bodies.length()==2&&bodies.optInt(0,0)>0) {
                        int expected=bodies.optInt(0),decoded=bodies.optInt(1);
                        detail=decoded==expected?"Decoded "+decoded+"/"+expected
                                +" original costume bodies. Next entity field: SupergroupCostume presence."
                                :"Decoded "+decoded+"/"+expected+" original costume bodies. "+detail;
                    }
                }
                if(BuildConfig.FULLSCREEN_DIAGNOSTIC)detail=initialContinuationDetail(report,detail);
                if(observedEntityAttempt==networkAttempt)detail+=" Box requested for observed server entity #"+observedEntityIndex+".";
                networkStatus.setText("World handoff test: "+phase+" • "+detail+"\nFull character/world decoding remains pending.");
                if(!handoffState.charactersReady()){characterButtons.removeAllViews();charactersScroll.setVisibility(android.view.View.GONE);}
                return;
            }
            String detail="SCENE_INCOMPLETE".equals(phase)
                    ? " • Scene data received; full server world decoding is pending."
                    : "CHARACTERS_READY".equals(phase) ? " • Select an existing disposable-profile character."
                    : "POLICY_UNAVAILABLE".equals(phase) ? " • Start/verify the server in the launcher, then reconnect."
                    : "SUSPENDED".equals(phase) ? " • Connect again after returning; no background reconnection." : "";
            JSONObject map=report.optJSONObject("map_protocol");
            JSONObject sceneFailure=map==null?null:map.optJSONObject("scene_failure");
            if("SCENE_INCOMPLETE".equals(phase)&&map!=null&&map.optLong("scene_structures")>0
                    &&sceneFailure!=null&&sceneFailure.optInt("status")==0) {
                detail=" • Scene structure decoded; server world rendering is pending.";
            }
            if("SCENE_INCOMPLETE".equals(phase)&&map!=null&&map.optInt("stage")==10
                    &&sceneFailure!=null&&sceneFailure.optInt("status")==2) {
                detail=" • Server scene format needs further decoding. Export the report.";
            }
            if("FAILED".equals(phase)&&map!=null&&map.optInt("stage")==10) {
                detail=sceneFailure!=null&&sceneFailure.optInt("status")==4
                        ? " • Server scene exceeds the current decoding limit. Export the report."
                        : " • Server scene could not be decoded. Export the report.";
            }
            JSONObject udp=map==null?null:map.optJSONObject("udp");
            JSONObject link=udp==null?null:udp.optJSONObject("link");
            JSONObject decode=link==null?null:link.optJSONObject("decode");
            if("FAILED".equals(phase)&&map!=null&&map.optInt("stage")==2&&decode!=null) {
                switch(decode.optInt("failure_kind")) {
                    case 2: detail=" • Server data exceeds the current receive limit. Export the report.";break;
                    case 3: detail=" • Server receive memory is unavailable. Export the report.";break;
                    case 1: case 4: detail=" • Server data could not be decoded. Export the report.";break;
                    default: break;
                }
            }
            networkStatus.setText("Server protocol: "+phase+detail);
            if(!"CHARACTERS_READY".equals(phase)){characterButtons.removeAllViews();charactersScroll.setVisibility(android.view.View.GONE);}
        } catch(Exception impossible) {networkStatus.setText("Server protocol report unavailable");}
    }
    private void showCharacters(JSONArray characters,long attempt) {
        try {if(networkMode==NetworkMode.WORLD_HANDOFF?!handoffState.charactersReady():
                !"CHARACTERS_READY".equals(new JSONObject(networkReport).optString("phase")))return;}
        catch(Exception invalid){return;}
        characterButtons.removeAllViews();
        for(int i=0;i<characters.length();i++) {
            JSONObject player=characters.optJSONObject(i);if(player==null||!player.optBoolean("selectable"))continue;
            int slot=player.optInt("wire_slot",-1);if(slot<0||slot>=64)continue;
            Button choose=new Button(this);
            choose.setText(player.optString("name","Character")+" • level "+player.optInt("level")+" • "+player.optString("map",""));
            choose.setOnClickListener(v -> {
                characterButtons.removeAllViews();charactersScroll.setVisibility(android.view.View.GONE);
                event(networkMode==NetworkMode.WORLD_HANDOFF?"world_handoff_character_choice_requested":"local_character_choice_requested");
                networkWorker.execute(() -> {
                    if(networkHandle!=0&&networkForeground&&networkRequested&&attempt==networkAttempt){
                        if(networkMode==NetworkMode.WORLD_HANDOFF)InteropNative.choose(networkHandle,slot,SystemClock.elapsedRealtime());
                        else LocalNative.choose(networkHandle,slot,SystemClock.elapsedRealtime());
                        publishNetwork();
                    }
                });
            });characterButtons.addView(choose);
        }
        if(characterButtons.getChildCount()==0) {
            TextView empty=new TextView(this);empty.setText("No selectable existing character in the disposable profile. Create/copy one with the conventional client first.");characterButtons.addView(empty);
        }
        charactersScroll.setVisibility(android.view.View.VISIBLE);
    }
    private float dead(float value) {
        float magnitude=Math.abs(value);
        return magnitude<=.15f ? 0 : Math.copySign((magnitude-.15f)/.85f,value);
    }
    private void sendInput() {
        if (handle == 0 || !resumed || destroying) return;
        int directions = ((keys & (1<<20))!=0 || axisY<-.5f ? 1 : 0)
                | ((keys & (1<<21))!=0 || axisY>.5f ? 2 : 0)
                | ((keys & (1<<22))!=0 || axisX<-.5f ? 4 : 0)
                | ((keys & (1<<23))!=0 || axisX>.5f ? 8 : 0);
        SessionNative.controls(handle, directions, dead(axisZ)*2f, dead(axisRz)*2f);
    }
    /** Numeric source progress only; queued work is distinct from actual sends. */
    private static String initialContinuationDetail(JSONObject report,String fallback){
        if(!report.has("initial_packet_complete"))return fallback;
        boolean complete=Boolean.TRUE.equals(report.opt("initial_packet_complete"));
        JSONArray tail=report.optJSONArray("initial_command_tail");
        String detail=complete?"Initial packet reached exact EOF"
                +(tail!=null&&tail.length()==7&&tail.optLong(2,-1)>=0?" at bit "+tail.optLong(2):"")+".":"Initial packet remains incomplete.";
        JSONArray partial=report.optJSONArray("initial_partial_tail");
        if(!complete&&partial!=null&&partial.length()==10&&partial.optInt(3,0)==1)
            detail="Entity section complete; diagnostic partial-tail skipped command "+partial.optLong(4)
                    +" with "+partial.optLong(8)+" bits discarded. Whole packet remains incomplete.";
        if(!complete){String next=report.optString("initial_next","");
            if(next.matches("[A-Za-z0-9_ .:-]{1,120}"))detail+=" Next: "+next+".";}
        JSONArray power=report.optJSONArray("power_unresolved");
        if(power!=null&&power.length()==5&&power.optLong(1,0)>0)
            detail+=" Original receiver tolerated "+power.optLong(1)+" unmapped power entries.";
        JSONArray progress=report.optJSONArray("initial_continuation");
        if(progress!=null&&progress.length()==10){
            String ack=progress.optInt(1,0)==1?(progress.optInt(3,0)==1?"sent":"queued"):"not queued";
            String ready=progress.optInt(2,0)==1?(progress.optInt(4,0)==1?"sent":"queued"):"not queued";
            detail+=" Full-update ACK "+ack+"; client READY "+ready+".";
            if(progress.optInt(3,0)==1&&progress.optInt(4,0)==1){
                detail+=" Later messages "+progress.optLong(7,0)+".";
                JSONArray position=report.optJSONArray("post_position");
                if(position!=null&&position.length()==7)detail+=" Position changes "+position.optLong(2,0)
                        +", stationary "+position.optLong(3,0)+", unsupported "+position.optLong(5,0)+".";
                detail+=progress.optInt(8,0)==1?" Bounded observation ended.":" Observing bounded updates.";
            }
        }
        return detail;
    }
    private void applyFullscreenBars(){
        if(!sceneFullscreen)return;
        getWindow().getDecorView().setSystemUiVisibility(android.view.View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                |android.view.View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN|android.view.View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                |android.view.View.SYSTEM_UI_FLAG_FULLSCREEN|android.view.View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                |android.view.View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
    }
    private void setSceneFullscreen(boolean enabled){
        if(!BuildConfig.FULLSCREEN_DIAGNOSTIC||destroying||sceneFullscreen==enabled)return;
        if(adapter!=null)adapter.clear();
        if(enabled){previousOrientation=getRequestedOrientation();previousSystemUi=getWindow().getDecorView().getSystemUiVisibility();}
        sceneFullscreen=enabled;
        epoch++;if(handle!=0){SessionNative.state(handle,epoch,resumed);SessionNative.captureViewport(handle,epoch,0,0);}
        controlsPanel.setVisibility(enabled?android.view.View.GONE:android.view.View.VISIBLE);
        fullscreenReturn.setVisibility(enabled?android.view.View.VISIBLE:android.view.View.GONE);
        if(enabled){
            setRequestedOrientation(android.content.pm.ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE);applyFullscreenBars();
        }else{
            getWindow().getDecorView().setSystemUiVisibility(previousSystemUi);setRequestedOrientation(previousOrientation);
        }
        scene.requestLayout();publishCaptureViewport();
        event(enabled?"fullscreen_entered":"fullscreen_controls_restored");saveReport();requestRender();
    }
    private void publishCaptureViewport(){
        if(!BuildConfig.FULLSCREEN_DIAGNOSTIC||destroying||view==null)return;
        final long ticket=epoch;
        view.post(()->{
            if(destroying||handle==0||epoch!=ticket)return;
            int width=0,height=0;
            if(sceneFullscreen&&currentHolder!=null&&currentSurface!=null&&currentSurface.isValid()){
                android.graphics.Rect frame=currentHolder.getSurfaceFrame();
                if(frame.width()==scene.getWidth()&&frame.height()==scene.getHeight()
                        &&view.getWidth()==frame.width()&&view.getHeight()==frame.height()){
                    width=frame.width();height=frame.height();
                }
            }
            SessionNative.captureViewport(handle,ticket,width,height);
        });
    }
    @Override public void onBackPressed(){if(sceneFullscreen)setSceneFullscreen(false);else super.onBackPressed();}
    private void newSurface() {
        epoch++;
        if (handle != 0) SessionNative.state(handle,epoch,resumed);
        currentSurface=null; currentHolder=null;
        scene.removeAllViews(); view = new SurfaceView(this) {
            @Override protected void onMeasure(int widthSpec, int heightSpec) {
                int[] bounds = ViewportPolicy.fit(android.view.View.MeasureSpec.getSize(widthSpec),
                        android.view.View.MeasureSpec.getSize(heightSpec));
                setMeasuredDimension(bounds[0], bounds[1]);
            }
        };
        view.setContentDescription("Local native Atlas scene preview");
        view.setImportantForAccessibility(android.view.View.IMPORTANT_FOR_ACCESSIBILITY_YES);
        currentHolder=view.getHolder(); currentHolder.addCallback(this);
        view.setOnTouchListener((v,event) -> !destroying && adapter != null && adapter.dispatchTouchEvent(event,v.getWidth(),v.getHeight()));
        scene.addView(view,new FrameLayout.LayoutParams(-1,-1,Gravity.CENTER));
    }
    private void requestRender() {
        if (destroying || !resumed || handle==0 || renderQueued || actorPreparing || currentSurface==null || !currentSurface.isValid()) return;
        final long ticket=epoch, h=handle; final Surface surface=currentSurface;
        renderQueued=true;
        renderWorker.execute(() -> {
            int result=0;
            try {
                if (!destroying && resumed && ticket==epoch && surface.isValid()) result=SessionNative.render(h,surface,ticket);
            } catch(RuntimeException ex) { result=-1; }
            final int completed=result;
            main.post(() -> {
                renderQueued=false;
                if (destroying) return;
                if (completed < 0) failure="Native renderer failed; preserve the exported report";
                event("render_returned"); saveReport();
                if (failure==null) requestRender();
            });
        });
    }
    @Override public void surfaceCreated(SurfaceHolder holder) { }
    @Override public void surfaceChanged(SurfaceHolder holder,int format,int width,int height) {
        if (destroying || holder!=currentHolder) return;
        epoch++; if (handle!=0) SessionNative.state(handle,epoch,resumed);
        currentSurface=holder.getSurface(); publishCaptureViewport(); event("surface_changed"); requestRender();
    }
    @Override public void surfaceDestroyed(SurfaceHolder holder) {
        if (destroying || holder!=currentHolder) return;
        epoch++; currentSurface=null; if(handle!=0)SessionNative.state(handle,epoch,false); event("surface_destroyed");
    }
    @Override protected void onResume() { super.onResume(); networkForeground=true; resumed=true; epoch++; if(handle!=0)SessionNative.state(handle,epoch,true);applyFullscreenBars();publishCaptureViewport(); event("resume");MemoryTelemetry.request(this,PhaseMemoryDiagnostics.Phase.RESUME); updateNetworkUi(); requestRender(); }
    @Override protected void onPause() {
        if(!returningToLauncher)MemoryTelemetry.request(this,PhaseMemoryDiagnostics.Phase.PAUSE);
        event("pause_requested");
        networkForeground=false;networkRequested=false;networkAttempt++;
        clearObservedBox();
        networkWorker.execute(() -> {
            if(networkHandle!=0) { suspendNetwork(); publishNetwork(); }
        });
        resumed=false; epoch++; if(adapter!=null)adapter.clear();
        if(handle!=0)SessionNative.state(handle,epoch,false); event("pause"); saveReport(); super.onPause();
    }
    @Override public void onWindowFocusChanged(boolean focused) {
        super.onWindowFocusChanged(focused);if(focused)applyFullscreenBars(); if(!destroying && adapter!=null)adapter.onWindowFocusChanged(focused);
    }
    @Override public boolean dispatchKeyEvent(KeyEvent event) {
        if(sceneFullscreen&&event.getKeyCode()==KeyEvent.KEYCODE_BACK){if(event.getAction()==KeyEvent.ACTION_UP)setSceneFullscreen(false);return true;}
        return !destroying && adapter!=null && adapter.dispatchKeyEvent(event) || super.dispatchKeyEvent(event);
    }
    @Override public boolean dispatchGenericMotionEvent(MotionEvent event) {
        return !destroying && adapter!=null && adapter.dispatchGenericMotionEvent(event) || super.dispatchGenericMotionEvent(event);
    }
    private void event(String type) {
        if(destroying)return;
        try {
            JSONObject event=new JSONObject().put("sequence",++sequence).put("type",type).put("time_ms",System.currentTimeMillis());
            if(handle!=0)event.put("native",new JSONObject(SessionNative.snapshot(handle)));
            events.put(event); if(events.length()>128)events.remove(0);
        } catch(Exception ex) { failure=ex.toString(); }
    }
    private JSONObject report() throws Exception {
        JSONObject d=new JSONObject().put("manufacturer",Build.MANUFACTURER).put("model",Build.MODEL)
                .put("sdk",Build.VERSION.SDK_INT).put("abis",new JSONArray(Build.SUPPORTED_ABIS))
                .put("emulator_detected",Build.FINGERPRINT.contains("generic") || Build.MODEL.contains("sdk_gphone"));
        JSONObject app=new JSONObject().put("package",getPackageName()).put("version_name",getPackageManager().getPackageInfo(getPackageName(),0).versionName)
                .put("version_code",getPackageManager().getPackageInfo(getPackageName(),0).versionCode).put("installed_apk",apkIdentity);
        JSONObject j=new JSONObject().put("schema","coh-native-combined-client-v1")
                .put("session_id",Long.toHexString(sessionStarted)).put("updated_at",new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSXXX",Locale.US).format(new Date()))
                .put("scope","Local DB/Map handoff and bounded source scene at the decoded selected-self pose; optional received costume with box fallback. Numeric packet, ACK/READY and observation fields state actual progress.")
                .put("app",app).put("device",d).put("runtime_world_optional_failure",runtimeWorldFailure).put("runtime_actor_optional_failure",runtimeActorFailure).put("assets_verified",assetsVerified).put("asset_manifest",assetManifest)
                .put("server_protocol",new JSONObject(localNetworkReport)).put("world_handoff",new JSONObject(interopReport))
                .put("memory_diagnostics",MemoryTelemetry.snapshot())
                .put("diagnostic_states",new JSONObject(PhaseMemoryDiagnostics.states(handoffState.initialObserved(),false)))
                .put("connection_mode",networkMode.name()).put("preview_is_server_world",false)
                .put("observed_entity_box_requested",observedEntityAttempt==networkAttempt)
                .put("observed_entity_index",observedEntityAttempt==networkAttempt?observedEntityIndex:JSONObject.NULL)
                .put("events",new JSONArray(events.toString())).put("resumed",resumed).put("render_busy",renderQueued)
                .put("report_write_failed",writeFailed).put("failure",failure==null?JSONObject.NULL:failure)
                .put("input_adapter",adapter==null?JSONObject.NULL:adapter.report())
                .put("viewport_policy",new JSONObject().put("schema","coh-native-viewport-v1")
                    .put("maximum_controls_percent",60).put("minimum_aspect",0.25).put("maximum_aspect",8)
                    .put("maximum_dimension",16384).put("host_width",scene==null?0:scene.getWidth())
                    .put("host_height",scene==null?0:scene.getHeight()).put("fullscreen",sceneFullscreen));
        if(BuildConfig.FRAME_CAPTURE_DIAGNOSTIC)j.put("scene_frame_capture",captureMetadata==null?JSONObject.NULL:new JSONObject(captureMetadata))
                .put("scene_frame_capture_error",captureFailure==null?JSONObject.NULL:captureFailure)
                .put("initial_replay",initialReplayMetadata==null?JSONObject.NULL:new JSONObject(initialReplayMetadata))
                .put("initial_replay_error",initialReplayFailure==null?JSONObject.NULL:initialReplayFailure);
        if(BuildConfig.POST_READY_REPLAY_DIAGNOSTIC)j.put("post_ready_replay",postReadyReplayMetadata==null?JSONObject.NULL:new JSONObject(postReadyReplayMetadata))
                .put("post_ready_replay_error",postReadyReplayFailure==null?JSONObject.NULL:postReadyReplayFailure);
        if(handle!=0)j.put("native",new JSONObject(SessionNative.snapshot(handle)));
        if(view!=null) {
            int[] location=new int[2];view.getLocationOnScreen(location);
            j.put("input_area",new JSONObject().put("left",location[0]).put("top",location[1])
                    .put("width",view.getWidth()).put("height",view.getHeight()).put("shown",view.isShown())
                    .put("surface_ready",currentSurface!=null&&currentSurface.isValid()));
        }
        return j;
    }
    private final Runnable poll=new Runnable() {
        public void run() { if(destroying)return; saveReport(); main.postDelayed(this,1000); }
    };
    private void saveReport() {
        if(destroying)return;
        try {
            JSONObject j=report(); pendingReport.set(j.toString(2).getBytes(StandardCharsets.UTF_8)); queueWriter(); queueSceneCapture(j);
            JSONObject memory=j.getJSONObject("memory_diagnostics");JSONArray phases=memory.getJSONArray("phases");JSONObject latest=null;
            for(int i=0;i<phases.length();i++){JSONObject row=phases.getJSONObject(i);if(latest==null||row.getLong("sequence")>latest.getLong("sequence"))latest=row;}
            memoryStatus.setText(latest==null?"Memory observation pending":"Memory • system headroom "+memoryMiB(latest,"system_headroom_bytes")
                    +" • Java free "+memoryMiB(latest,"java_heap_headroom_bytes")+" • app RSS "+memoryMiB(latest,"process_rss_bytes")
                    +" • PSS "+memoryMiB(latest,"process_pss_bytes")+" • "+latest.optString("phase")
                    +" • sampled "+Math.max(0,(SystemClock.elapsedRealtime()-latest.optLong("sampled_elapsed_ms"))/1000)+"s ago");
            JSONObject n=j.optJSONObject("native");
            JSONObject stream=n==null ? null : n.optJSONObject("stream");
            String move=n==null ? "starting" : n.optString("animation_move","starting");
            status.setText(failure!=null ? failure : !assetsVerified ? "Preparing native scene…" :
                    "Local scene preview • " + move + " • " + (n==null ? "starting" : n.optLong("frames")+" frames")
                    + (stream==null ? "" : " • " + (stream.optDouble("view_radius")<60 ? "Near" : "Far")
                        + " • " + stream.optLong("selected_instances") + "/" + stream.optLong("catalog_instances") + " objects")
                    + (writeFailed ? " • report save failed" : " • report ready"));
        } catch(Exception ex) { failure=ex.toString(); status.setText(failure); }
    }
    private long captureAppVersion(){
        try{return getPackageManager().getPackageInfo(getPackageName(),0).versionCode;}
        catch(Exception unavailable){return -1;}
    }
    private void queueSceneCapture(JSONObject report) {
        if(!BuildConfig.FRAME_CAPTURE_DIAGNOSTIC||destroying||!assetsVerified||reportWorker.isShutdown())return;
        JSONObject nativeState=report.optJSONObject("native");
        JSONObject frame=nativeState==null?null:nativeState.optJSONObject("frame_capture");
        if(frame==null||frame.optLong("frame")<=captureSavedFrame||!captureQueued.compareAndSet(false,true))return;
        final long run=captureRunSequence;
        try{reportWorker.execute(()->{
            try{
                if(run!=captureRunSequence)return;
                byte[] raw;
                synchronized(captureLife){if(destroying||handle==0)return;raw=SessionNative.frameCapture(handle,captureSavedFrame);}
                if(raw==null||run!=captureRunSequence)return;
                long version=getPackageManager().getPackageInfo(getPackageName(),0).versionCode;
                String saved=BuildConfig.FULLSCREEN_DIAGNOSTIC
                        ?SceneFrameCapture.saveLarge(getFilesDir(),raw,version,Long.toHexString(sessionStarted))
                        :SceneFrameCapture.save(getFilesDir(),raw,version,Long.toHexString(sessionStarted));
                JSONObject metadata=new JSONObject(saved);captureSavedFrame=metadata.getLong("frame");
                if(run==captureRunSequence){captureMetadata=saved;captureFailure=null;}
            }catch(Exception ex){captureFailure=ex.getClass().getSimpleName();}
            catch(OutOfMemoryError optionalCapture){captureFailure="Capture memory unavailable";}
            finally{captureQueued.set(false);}
        });}catch(RejectedExecutionException retired){captureQueued.set(false);}
    }
    private void exportSceneCapture(){
        if(destroying||exporting)return;
        exporting=true;
        Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("application/zip");
        intent.putExtra(Intent.EXTRA_TITLE,"COH-ObservedScene-"+System.currentTimeMillis()+".zip");
        startActivityForResult(intent,EXPORT_CAPTURE);
    }
    private void queueWriter() {
        if(reportWorker.isShutdown() || !writerQueued.compareAndSet(false,true))return;
        try { reportWorker.execute(() -> {
            try {
                byte[] next;
                while((next=pendingReport.getAndSet(null))!=null) {
                    AtomicFile file=new AtomicFile(new File(getFilesDir(),"native-client-report.json")); FileOutputStream output=null;
                    try { output=file.startWrite(); output.write(next); file.finishWrite(output); }
                    catch(Exception ex) { if(output!=null)file.failWrite(output); writeFailed=true; }
                }
            } finally { writerQueued.set(false); if(!reportWorker.isShutdown() && pendingReport.get()!=null)queueWriter(); }
        }); } catch(RejectedExecutionException retired) { writerQueued.set(false); }
    }
    private static String memoryMiB(JSONObject row,String field){return row.isNull(field)?"unavailable":row.optLong(field)/(1024*1024)+" MiB";}
    private void exportReport() {
        if(destroying || exporting)return;
        try {
            event("export_requested"); frozenExport=report().toString(2).getBytes(StandardCharsets.UTF_8); exporting=true;
            Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("application/json");
            intent.putExtra(Intent.EXTRA_TITLE,"COH-NativeCombined-"+new SimpleDateFormat("yyyyMMdd-HHmmss",Locale.US).format(new Date())+".json");
            startActivityForResult(intent,EXPORT);
        } catch(Exception ex) { exporting=false; frozenExport=null; failure=ex.toString(); saveReport(); }
    }
    @Override protected void onActivityResult(int request,int result,Intent data) {
        super.onActivityResult(request,result,data);
        if(request==EXPORT_CAPTURE){
            exporting=false;if(destroying)return;
            if(result!=RESULT_OK||data==null||data.getData()==null){event("capture_export_cancelled");return;}
            reportWorker.execute(()->{
                String error=null;
                try(OutputStream output=getContentResolver().openOutputStream(data.getData(),"wt")){
                    SceneFrameCapture.Selection capture=SceneFrameCapture.current(getFilesDir(),
                            captureMetadata==null?-1:captureAppVersion(),Long.toHexString(sessionStarted),BuildConfig.FULLSCREEN_DIAGNOSTIC);
                    if(output==null)error="CAPTURE_OUTPUT_UNAVAILABLE";
                    else if(!capture.writeZip(output))error=capture.omissionReason();
                }catch(Exception ex){error=ex.getClass().getSimpleName();}
                final String problem=error;main.post(()->{if(destroying)return;captureFailure=problem;event(problem==null?"capture_export_complete":"capture_export_failed");saveReport();});
            });return;
        }
        if(request!=EXPORT)return;
        if(destroying)return;
        final byte[] bytes=frozenExport; frozenExport=null; exporting=false;
        if(result!=RESULT_OK || data==null || data.getData()==null || bytes==null){event("export_cancelled");return;}
        reportWorker.execute(() -> {
            String error=null;
            try(OutputStream output=getContentResolver().openOutputStream(data.getData(),"wt")) {
                if(output==null)throw new IllegalStateException("Document destination unavailable"); output.write(bytes);
            } catch(Exception ex){error=ex.toString();}
            final String problem=error;
            main.post(() -> {if(destroying)return;if(problem!=null)failure=problem;event(problem==null?"export_complete":"export_failed");saveReport();});
        });
    }
    private String runtimeWorldFailure="";
    private static JSONObject sceneAssetPin(JSONObject original, JSONObject neighborhood, String name) throws Exception {
        return ("neighborhood-map.bin".equals(name) ? neighborhood : original).getJSONObject(name);
    }
    private byte[] readAsset(String name) throws Exception {
        try(InputStream input=getAssets().open(name);ByteArrayOutputStream output=new ByteArrayOutputStream()) {
            byte[] chunk=new byte[16384];int n;
            while((n=input.read(chunk))!=-1){if(output.size()+n>32*1024*1024)throw new IllegalStateException("Asset too large");output.write(chunk,0,n);}
            return output.toByteArray();
        }
    }
    private static String hex(byte[] bytes) {
        StringBuilder text=new StringBuilder();for(byte value:bytes)text.append(String.format(Locale.US,"%02x",value&255));return text.toString();
    }
    private static String sha(byte[] bytes) throws Exception { return hex(MessageDigest.getInstance("SHA-256").digest(bytes)); }
    private JSONObject apkIdentity() throws Exception {
        File path=new File(getApplicationInfo().sourceDir);MessageDigest digest=MessageDigest.getInstance("SHA-256");
        try(InputStream input=new FileInputStream(path)){byte[] chunk=new byte[65536];int n;while((n=input.read(chunk))!=-1)digest.update(chunk,0,n);}
        return new JSONObject().put("bytes",path.length()).put("sha256",hex(digest.digest()));
    }
    @Override public void onTrimMemory(int level) {super.onTrimMemory(level);MemoryTelemetry.memoryPressure(this,level,false);}
    @Override public void onLowMemory() {super.onLowMemory();MemoryTelemetry.memoryPressure(this,-1,true);}
    @Override protected void onDestroy() {
        if(actorControl!=null)actorControl.cancel();actorPreparationSequence++;
        networkForeground=false;networkRequested=false;networkAttempt++;
        networkWorker.execute(()->{retireNetworkOwner();networkRetired.set(true);sampleFinalCleanup();});
        networkWorker.shutdown();
        destroying=true;resumed=false;epoch++;main.removeCallbacks(poll);main.removeCallbacks(returnDeadline);
        if(currentHolder!=null)currentHolder.removeCallback(this);
        currentHolder=null;currentSurface=null;
        if(adapter!=null)adapter.clear();if(inputManager!=null)inputManager.unregisterInputDeviceListener(adapter);
        if(handle!=0)SessionNative.state(handle,epoch,false);
        renderWorker.execute(() -> {synchronized(captureLife){long previous=handle;handle=0;if(previous!=0)SessionNative.destroy(previous);}rendererRetired.set(true);sampleFinalCleanup();});
        renderWorker.shutdown();reportWorker.shutdown();super.onDestroy();
    }
    private void sampleFinalCleanup(){if(networkRetired.get()&&rendererRetired.get())MemoryTelemetry.request(this,PhaseMemoryDiagnostics.Phase.FINAL_CLEANUP);}
}
