package org.coh.nativecombined;

import org.coh.sessionclient.SessionNative;
import android.os.SystemClock;
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
import java.security.MessageDigest;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

/** Reuses the accepted 0.3.0 renderer/controller Activity behavior.
 * Local preview and real server protocol progress remain separate.
 * Source: session-client MainActivity at 132a813 (qualified renderer unchanged). */
public final class NativeClientActivity extends Activity implements SurfaceHolder.Callback {
    private static final int EXPORT = 18;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final ExecutorService renderWorker = Executors.newSingleThreadExecutor();
    private final ExecutorService reportWorker = Executors.newSingleThreadExecutor();
    private final AtomicReference<byte[]> pendingReport = new AtomicReference<>();
    private final AtomicBoolean writerQueued = new AtomicBoolean();
    private final JSONArray events = new JSONArray();
    private volatile long handle;
    private volatile boolean destroying, writeFailed;
    private volatile boolean resumed;
    private boolean renderQueued, assetsVerified, exporting;
    private long sequence, sessionStarted;
    private volatile long epoch;
    private String failure;
    private JSONObject assetManifest, apkIdentity;
    private Surface currentSurface;
    private SurfaceHolder currentHolder;
    private SurfaceView view;
    private FrameLayout scene;
    private TextView status;
    private InputAdapter adapter;
    private InputManager inputManager;
    private int keys;
    private float axisX, axisY, axisZ, axisRz, touchX, touchY;
    private boolean touching;
    private byte[] frozenExport;
    private final ScheduledExecutorService networkWorker = Executors.newSingleThreadScheduledExecutor();
    private volatile String networkReport = "{\"phase\":\"IDLE\"}";
    private volatile boolean networkForeground, networkConnecting, networkRequested;
    private volatile long networkAttempt;
    // Transport handle and policy identity are owned exclusively by networkWorker.
    private long networkHandle, policyCheckedAt;
    private String serverSessionId, importGeneration;
    private boolean charactersPublished;
    private TextView networkStatus;
    private LinearLayout characterButtons;
    private android.widget.ScrollView charactersScroll;
    private Button connectButton;


    @Override public void onCreate(Bundle bundle) {
        super.onCreate(bundle);
        sessionStarted = System.currentTimeMillis();
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        TextView title = new TextView(this);
        title.setText("Native City of Heroes • Local development client");
        title.setTextSize(18); layout.addView(title);
        TextView controls = new TextView(this);
        controls.setText("Local scene preview • Left stick / WASD / D-pad: move • Right stick / drag: look\n"
                + "The scene below is the accepted offline preview. Server character/world rendering is pending.");
        layout.addView(controls);
        LinearLayout networkButtons = new LinearLayout(this);
        connectButton = new Button(this); connectButton.setText("Connect local server");
        connectButton.setOnClickListener(v -> connectLocalServer()); networkButtons.addView(connectButton);
        Button disconnect = new Button(this); disconnect.setText("Disconnect client");
        disconnect.setOnClickListener(v -> {
            networkRequested=false;networkAttempt++;
            characterButtons.removeAllViews(); charactersScroll.setVisibility(android.view.View.GONE);
            networkWorker.execute(() -> {
                if(networkHandle!=0){LocalNative.disconnect(networkHandle);publishNetwork();}
            });
        }); networkButtons.addView(disconnect); layout.addView(networkButtons);
        networkStatus = new TextView(this); networkStatus.setText("Server protocol: idle • Start the server in the launcher first.");
        layout.addView(networkStatus);
        characterButtons = new LinearLayout(this); characterButtons.setOrientation(LinearLayout.VERTICAL);
        charactersScroll = new android.widget.ScrollView(this);
        charactersScroll.addView(characterButtons);
        layout.addView(charactersScroll, new LinearLayout.LayoutParams(-1, (int)(144*getResources().getDisplayMetrics().density)));
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
        Button distance = new Button(this); distance.setText("View distance");
        distance.setOnClickListener(v -> {
            if (handle != 0) SessionNative.viewDistance(handle);
            event("view_distance_requested"); saveReport();
        });
        layout.addView(buttons);
        layout.addView(distance);
        status = new TextView(this); status.setText("Preparing native scene…"); layout.addView(status);
        scene = new FrameLayout(this); layout.addView(scene, new LinearLayout.LayoutParams(-1, 0, 1));
        setContentView(layout);
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
                String[] names = {"world.bin", "character.bin", "rig.bin", "morph.bin", "locomotion.bin", "walkable.bin", "map.bin"};
                byte[][] bytes = new byte[names.length][];
                for (int i=0; i<names.length; i++) {
                    bytes[i] = readAsset(names[i]); JSONObject pin = records.getJSONObject(names[i]);
                    if (pin.getLong("bytes") != bytes[i].length || !pin.getString("sha256").equals(sha(bytes[i])))
                        throw new IllegalStateException("Asset integrity: " + names[i]);
                }
                JSONObject apk = apkIdentity();
                long result = SessionNative.createSession(bytes[0], bytes[1], bytes[2], bytes[3], bytes[4], bytes[5], bytes[6]);
                if (result == 0) throw new IllegalStateException("Native scene rejected its fixtures");
                handle = result;
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
    private void connectLocalServer() {
        if(destroying||networkConnecting||!networkForeground)return;
        final long attempt=++networkAttempt;networkRequested=true;
        networkConnecting=true;connectButton.setEnabled(false);
        characterButtons.removeAllViews();charactersScroll.setVisibility(android.view.View.GONE);
        networkStatus.setText("Server protocol: connecting to the local development server…");
        event("local_connect_requested");
        networkWorker.execute(() -> {
            try {
                if(!networkForeground||!networkRequested||attempt!=networkAttempt)return;
                JSONObject policy=localPolicy();
                if(!networkForeground||!networkRequested||attempt!=networkAttempt)return;
                if(networkHandle!=0){LocalNative.close(networkHandle);networkHandle=0;}
                serverSessionId=policy.getString("server_session_id");charactersPublished=false;
                importGeneration=policy.getString("import_generation");
                policyCheckedAt=SystemClock.elapsedRealtime();
                networkHandle=LocalNative.begin(policy.getInt("db_port"),policy.getString("account"),policy.getInt("net_version"),
                        policy.getBoolean("encryption_required"),policy.getBoolean("outbound_compressed"),policyCheckedAt);
                if(networkHandle==0)throw new IllegalStateException("Local owner rejected policy");
                publishNetwork();
            } catch(Exception problem) {
                networkReport="{\"phase\":\"POLICY_UNAVAILABLE\",\"live_world_rendered\":false,\"authserver_authenticated\":false}";
                main.post(() -> {if(!destroying)updateNetworkUi();});
            } finally {networkConnecting=false;main.post(() -> {if(!destroying)updateNetworkUi();});}
        });
    }
    private void networkTick() {
        if(destroying||!networkForeground||!networkRequested||networkHandle==0)return;
        try {
            long now=SystemClock.elapsedRealtime();
            if(now-policyCheckedAt>=1000) {
                JSONObject policy=localPolicy();
                if(!policy.getString("server_session_id").equals(serverSessionId)
                        ||!policy.getString("import_generation").equals(importGeneration))throw new IllegalStateException("Server replaced");
                policyCheckedAt=now;
            }
            String phase=new JSONObject(networkReport).optString("phase","IDLE");
            if("SUSPENDED".equals(phase)||"CLOSED".equals(phase)||"CANCELLED".equals(phase)
                    ||"FAILED".equals(phase)||"TIMED_OUT".equals(phase)||"UNSUPPORTED".equals(phase)
                    ||"POLICY_UNAVAILABLE".equals(phase))return;
            LocalNative.service(networkHandle,now);publishNetwork();
            if(!charactersPublished&&"CHARACTERS_READY".equals(new JSONObject(networkReport).optString("phase"))) {
                byte[] list=LocalNative.characters(networkHandle);
                if(list!=null) {
                    JSONArray characters=new JSONArray(new String(list,StandardCharsets.UTF_8));
                    charactersPublished=true;
                    final long attempt=networkAttempt;
                    main.post(() -> {if(!destroying&&networkForeground&&networkRequested&&attempt==networkAttempt)showCharacters(characters,attempt);});
                }
            }
        } catch(Exception problem) {
            LocalNative.suspend(networkHandle);publishNetwork();
            main.post(() -> {if(!destroying)networkStatus.setText("Server protocol suspended • Start/verify the local server, then connect again.");});
        }
    }
    private void publishNetwork() {
        if(networkHandle==0)return;
        String next=LocalNative.report(networkHandle);
        if(!next.equals(networkReport)) {
            networkReport=next;
            main.post(() -> {if(!destroying)updateNetworkUi();});
        }
    }
    private void updateNetworkUi() {
        try {
            JSONObject report=new JSONObject(networkReport);String phase=report.optString("phase","IDLE");
            boolean active="DB_CONNECTING".equals(phase)||"CHARACTERS_READY".equals(phase)
                    ||"MAP_CONNECTING".equals(phase)||"SCENE_INCOMPLETE".equals(phase);
            connectButton.setEnabled(!active&&!networkConnecting);
            String detail="SCENE_INCOMPLETE".equals(phase)
                    ? " • MapServer replied; complete server scene/entity rendering is pending."
                    : "CHARACTERS_READY".equals(phase) ? " • Select an existing disposable-profile character."
                    : "POLICY_UNAVAILABLE".equals(phase) ? " • Start/verify the server in the launcher, then reconnect."
                    : "SUSPENDED".equals(phase) ? " • Connect again after returning; no background reconnection." : "";
            networkStatus.setText("Server protocol: "+phase+detail);
            if(!"CHARACTERS_READY".equals(phase)){characterButtons.removeAllViews();charactersScroll.setVisibility(android.view.View.GONE);}
        } catch(Exception impossible) {networkStatus.setText("Server protocol report unavailable");}
    }
    private void showCharacters(JSONArray characters,long attempt) {
        try {if(!"CHARACTERS_READY".equals(new JSONObject(networkReport).optString("phase")))return;}
        catch(Exception invalid){return;}
        characterButtons.removeAllViews();
        for(int i=0;i<characters.length();i++) {
            JSONObject player=characters.optJSONObject(i);if(player==null||!player.optBoolean("selectable"))continue;
            int slot=player.optInt("wire_slot",-1);if(slot<0||slot>=64)continue;
            Button choose=new Button(this);
            choose.setText(player.optString("name","Character")+" • level "+player.optInt("level")+" • "+player.optString("map",""));
            choose.setOnClickListener(v -> {
                characterButtons.removeAllViews();charactersScroll.setVisibility(android.view.View.GONE);
                event("local_character_choice_requested");
                networkWorker.execute(() -> {
                    if(networkHandle!=0&&networkForeground&&networkRequested&&attempt==networkAttempt){LocalNative.choose(networkHandle,slot,SystemClock.elapsedRealtime());publishNetwork();}
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
    private void newSurface() {
        epoch++;
        if (handle != 0) SessionNative.state(handle,epoch,resumed);
        currentSurface=null; currentHolder=null;
        scene.removeAllViews(); view = new SurfaceView(this);
        view.setContentDescription("Local native Atlas scene preview");
        view.setImportantForAccessibility(android.view.View.IMPORTANT_FOR_ACCESSIBILITY_YES);
        currentHolder=view.getHolder(); currentHolder.addCallback(this);
        view.setOnTouchListener((v,event) -> !destroying && adapter != null && adapter.dispatchTouchEvent(event,v.getWidth(),v.getHeight()));
        scene.addView(view,new FrameLayout.LayoutParams(-1,-1));
    }
    private void requestRender() {
        if (destroying || !resumed || handle==0 || renderQueued || currentSurface==null || !currentSurface.isValid()) return;
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
        currentSurface=holder.getSurface(); event("surface_changed"); requestRender();
    }
    @Override public void surfaceDestroyed(SurfaceHolder holder) {
        if (destroying || holder!=currentHolder) return;
        epoch++; currentSurface=null; if(handle!=0)SessionNative.state(handle,epoch,false); event("surface_destroyed");
    }
    @Override protected void onResume() { super.onResume(); networkForeground=true; resumed=true; epoch++; if(handle!=0)SessionNative.state(handle,epoch,true); event("resume"); requestRender(); }
    @Override protected void onPause() {
        event("pause_requested");
        networkForeground=false;networkRequested=false;networkAttempt++;
        networkWorker.execute(() -> {
            if(networkHandle!=0) { LocalNative.suspend(networkHandle); publishNetwork(); }
        });
        resumed=false; epoch++; if(adapter!=null)adapter.clear();
        if(handle!=0)SessionNative.state(handle,epoch,false); event("pause"); saveReport(); super.onPause();
    }
    @Override public void onWindowFocusChanged(boolean focused) {
        super.onWindowFocusChanged(focused); if(!destroying && adapter!=null)adapter.onWindowFocusChanged(focused);
    }
    @Override public boolean dispatchKeyEvent(KeyEvent event) {
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
                .put("scope","Local development DB/Map protocol progress plus separate accepted offline scene preview. No AuthServer authentication, server-authoritative rendering, full map or complete entity replication")
                .put("app",app).put("device",d).put("assets_verified",assetsVerified).put("asset_manifest",assetManifest)
                .put("server_protocol",new JSONObject(networkReport)).put("preview_is_server_world",false)
                .put("events",new JSONArray(events.toString())).put("resumed",resumed).put("render_busy",renderQueued)
                .put("report_write_failed",writeFailed).put("failure",failure==null?JSONObject.NULL:failure)
                .put("input_adapter",adapter==null?JSONObject.NULL:adapter.report());
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
            JSONObject j=report(); pendingReport.set(j.toString(2).getBytes(StandardCharsets.UTF_8)); queueWriter();
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
    @Override protected void onDestroy() {
        networkForeground=false;networkRequested=false;networkAttempt++;
        networkWorker.execute(() -> { if(networkHandle!=0){LocalNative.close(networkHandle);networkHandle=0;} });
        networkWorker.shutdown();
        destroying=true;resumed=false;epoch++;main.removeCallbacks(poll);
        if(currentHolder!=null)currentHolder.removeCallback(this);
        currentHolder=null;currentSurface=null;
        if(adapter!=null)adapter.clear();if(inputManager!=null)inputManager.unregisterInputDeviceListener(adapter);
        if(handle!=0)SessionNative.state(handle,epoch,false);
        renderWorker.execute(() -> {long previous=handle;handle=0;if(previous!=0)SessionNative.destroy(previous);});
        renderWorker.shutdown();reportWorker.shutdown();super.onDestroy();
    }
}
