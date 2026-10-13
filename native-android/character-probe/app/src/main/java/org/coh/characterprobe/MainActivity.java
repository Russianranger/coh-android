package org.coh.characterprobe;

import android.app.Activity;
import android.content.Intent;
import android.content.res.Configuration;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.util.AtomicFile;
import android.view.Gravity;
import android.view.Surface;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
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
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Arrays;
import java.util.HashSet;
import java.util.IdentityHashMap;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

/** Standalone rig and animation qualification. This activity does not start a game or server. */
public final class MainActivity extends Activity implements SurfaceHolder.Callback {
    private static final int EXPORT_REPORT = 41;
    private static final int MAX_RUNS = 20;
    private static final int MAX_EVENTS = 160;
    private static final int MAX_ASSET_BYTES = 16 * 1024 * 1024;
    private static final int MAX_TOTAL_ASSET_BYTES = 32 * 1024 * 1024;
    private static final int MAX_METADATA_BYTES = 128 * 1024;
    private static final Set<String> REQUIRED_ASSETS = new HashSet<>(Arrays.asList(
            "character.bin", "rig.bin", "morph.bin", "character-reference.bin", "material-reference.bin"));
    private final Handler main = new Handler(Looper.getMainLooper());
    private final ThreadPoolExecutor worker = new ThreadPoolExecutor(1, 1, 0,
            TimeUnit.MILLISECONDS, new LinkedBlockingQueue<Runnable>());
    private volatile boolean active, destroyed, surfaceReady;
    private volatile long generation, requestSequence;
    private SurfaceView surfaceView;
    private FrameLayout surfaceFrame;
    private TextView status, reportText;
    private int surfaceWidth, surfaceHeight;
    private boolean smallerSurface, autoSmoke;
    private int smokeStage;
    private int sessionFailures;
    private String pendingAction;
    private JSONObject report;
    private JSONArray events = new JSONArray(), runs = new JSONArray(), history;
    private AtomicFile reportFile;
    private byte[] exportSnapshot;
    private final IdentityHashMap<SurfaceHolder, Long> holderGenerations = new IdentityHashMap<>();

    private static JSONObject object(Object... pairs) {
        JSONObject result = new JSONObject();
        try {
            for (int i = 0; i < pairs.length; i += 2) result.put((String) pairs[i], pairs[i + 1]);
        } catch (Exception e) { throw new IllegalArgumentException(e); }
        return result;
    }
    private static JSONArray trim(JSONArray values, int maximum) {
        JSONArray result = new JSONArray();
        for (int i = Math.max(0, values.length() - maximum); i < values.length(); ++i)
            result.put(values.opt(i));
        return result;
    }
    private static String time() {
        return new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSXXX", Locale.US).format(new Date());
    }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        reportFile = new AtomicFile(new File(getFilesDir(), "character-probe-report.json"));
        history = readHistory();
        boolean emulator = (Build.FINGERPRINT + " " + Build.MODEL + " " + Build.HARDWARE)
                .toLowerCase(Locale.US).matches(".*(generic|emulator|sdk_gphone|sdk_google|ranchu|goldfish).*")
                || Build.HARDWARE.equals("ranchu") || Build.HARDWARE.equals("goldfish")
                || Build.FINGERPRINT.startsWith("generic") || Build.MODEL.contains("sdk");
        report = object("schema", "coh-native-character-probe-v1", "started_at", time(),
                "session_id", Long.toHexString(System.currentTimeMillis()) + "-" + android.os.Process.myPid(),
                "scope", "complete source-selected character parts, actor morphs, sockets and native animation; bounded preview, no game or networking",
                "device", object("manufacturer", Build.MANUFACTURER, "model", Build.MODEL,
                    "device", Build.DEVICE, "hardware", Build.HARDWARE, "fingerprint", Build.FINGERPRINT,
                    "sdk", Build.VERSION.SDK_INT, "release", Build.VERSION.RELEASE,
                    "abis", new JSONArray(Arrays.asList(Build.SUPPORTED_ABIS)), "emulator_detected", emulator),
                "evidence_scope", emulator ? "host_emulator_only; Thor acceptance pending" : "this device only",
                "events", events, "native_runs", runs, "run_history", history);
        autoSmoke = getIntent().getBooleanExtra("autoSmoke", false);
        pendingAction = getIntent().getStringExtra("probe_action");
        buildUi();
        event("activity_created", object("auto_smoke", autoSmoke));
        refresh("Waiting for the Android surface.");
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(8), dp(6), dp(8), dp(6));
        root.setBackgroundColor(Color.rgb(239, 243, 246));
        status = new TextView(this);
        status.setTextSize(16);
        // A changing status message must not accidentally resize the tested surface.
        status.setLines(2);
        status.setPadding(0, 0, 0, dp(4));
        root.addView(status, new LinearLayout.LayoutParams(-1, -2));
        HorizontalScrollView controlsScroll = new HorizontalScrollView(this);
        LinearLayout controls = new LinearLayout(this);
        controls.setOrientation(LinearLayout.HORIZONTAL);
        button(controls, "Run check", () -> schedule("manual"));
        button(controls, "Resize surface", this::resizeSurface);
        button(controls, "Recreate surface", this::recreateSurface);
        button(controls, "Export report", this::exportReport);
        controlsScroll.addView(controls);
        root.addView(controlsScroll, new LinearLayout.LayoutParams(-1, -2));
        TextView instructions = new TextView(this);
        instructions.setText("Each check shows the complete Wretch in two short animation previews. Resize, then recreate the surface; background and return to verify lifecycle handling. Export the JSON report. This is a character assembly probe, not the game.");
        instructions.setTextSize(12);
        root.addView(instructions, new LinearLayout.LayoutParams(-1, -2));
        surfaceFrame = new FrameLayout(this);
        surfaceFrame.setBackgroundColor(Color.rgb(21, 28, 35));
        root.addView(surfaceFrame, new LinearLayout.LayoutParams(-1, 0, 1.2f));
        addSurface();
        ScrollView scroll = new ScrollView(this);
        reportText = new TextView(this);
        reportText.setTextSize(11);
        reportText.setTextIsSelectable(true);
        scroll.addView(reportText, new ScrollView.LayoutParams(-1, -2));
        root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1f));
        setContentView(root);
    }
    private void button(LinearLayout row, String label, Runnable action) {
        Button b = new Button(this);
        b.setText(label);
        b.setTextSize(12);
        b.setOnClickListener(v -> action.run());
        row.addView(b, new LinearLayout.LayoutParams(-2, -2));
    }
    private void addSurface() {
        surfaceView = new SurfaceView(this);
        surfaceView.getHolder().setFormat(PixelFormat.RGBA_8888);
        surfaceView.getHolder().addCallback(this);
        FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(-1, -1, Gravity.CENTER);
        if (smallerSurface && surfaceFrame.getWidth() > 0 && surfaceFrame.getHeight() > 0) {
            params.width = Math.max(16, surfaceFrame.getWidth() * 3 / 4);
            params.height = Math.max(16, surfaceFrame.getHeight() * 3 / 4);
        }
        surfaceFrame.addView(surfaceView, params);
    }
    private void resizeSurface() {
        if (destroyed) return;
        if (!active || destroyed || surfaceFrame.getWidth() < 32 || surfaceFrame.getHeight() < 32) {
            refresh("Resize pending: bring the activity to the foreground."); return;
        }
        invalidateRequests();
        smallerSurface = !smallerSurface;
        FrameLayout.LayoutParams params = (FrameLayout.LayoutParams) surfaceView.getLayoutParams();
        params.width = smallerSurface ? Math.max(16, surfaceFrame.getWidth() * 3 / 4) : -1;
        params.height = smallerSurface ? Math.max(16, surfaceFrame.getHeight() * 3 / 4) : -1;
        surfaceView.setLayoutParams(params);
        event("resize_requested", object("smaller", smallerSurface,
                "requested_width", params.width, "requested_height", params.height));
        refresh("Waiting for an actual surfaceChanged callback.");
    }
    private void recreateSurface() {
        if (destroyed) return;
        if (!active || destroyed) { refresh("Recreate pending: bring the activity to the foreground."); return; }
        invalidateRequests();
        surfaceReady = false;
        event("surface_recreation_requested", object("previous_generation", generation));
        surfaceFrame.removeView(surfaceView);
        addSurface();
        refresh("Waiting for actual surface destruction and creation callbacks.");
    }
    private void invalidateRequests() {
        ++requestSequence;
        worker.getQueue().clear();
    }

    @Override public void surfaceCreated(SurfaceHolder holder) {
        if (destroyed) return;
        if (holder != surfaceView.getHolder()) return;
        ++generation;
        holderGenerations.put(holder, generation);
        surfaceReady = true;
        surfaceWidth = surfaceHeight = 0;
        event("surface_created", object("generation", generation));
    }
    @Override public void surfaceChanged(SurfaceHolder holder, int format, int width, int height) {
        if (destroyed) return;
        if (holder != surfaceView.getHolder()) return;
        boolean changed = width != surfaceWidth || height != surfaceHeight;
        surfaceWidth = width; surfaceHeight = height;
        event("surface_changed", object("generation", generation, "width", width, "height", height, "format", format));
        if (width > 0 && height > 0 && (changed || runs.length() == 0)) schedule("surfaceChanged");
        runPendingAction();
    }
    @Override public void surfaceDestroyed(SurfaceHolder holder) {
        if (destroyed) return;
        // Removing a view can deliver its final callback after a replacement was attached.
        boolean current = holder == surfaceView.getHolder();
        Long destroyedGeneration = holderGenerations.remove(holder);
        event("surface_destroyed", object("destroyed_generation", destroyedGeneration == null ? -1 : destroyedGeneration,
                "current_holder", current));
        if (current) { surfaceReady = false; invalidateRequests(); }
        if (!destroyed) refresh("Surface unavailable; obsolete in-flight results cannot qualify.");
    }

    private void schedule(String reason) {
        if (destroyed) return;
        if (!active || destroyed || !surfaceReady || surfaceWidth <= 0 || surfaceHeight <= 0
                || !surfaceView.getHolder().getSurface().isValid()) {
            refresh("Waiting for a valid foreground surface."); return;
        }
        worker.getQueue().clear();
        final long sequence = ++requestSequence, requestedGeneration = generation;
        final int width = surfaceWidth, height = surfaceHeight;
        final Surface requestedSurface = surfaceView.getHolder().getSurface();
        final long started = SystemClock.elapsedRealtime();
        event("probe_requested", object("request", sequence, "generation", requestedGeneration,
                "width", width, "height", height, "reason", reason));
        refresh("Running character checks and a short animation preview for surface " + requestedGeneration + " (" + width + " × " + height + ").");
        worker.execute(() -> {
            if (destroyed || !active || sequence != requestSequence || requestedGeneration != generation) return;
            JSONObject nativeResult, fixture = new JSONObject();
            try {
                byte[] metadata = readAsset("character-fixture.json", MAX_METADATA_BYTES);
                fixture = new JSONObject(new String(metadata, StandardCharsets.UTF_8));
                Map<String, byte[]> assets = verifyAssets(fixture);
                if (destroyed || !active || sequence != requestSequence || requestedGeneration != generation) return;
                nativeResult = new JSONObject(runNative(requestedSurface, assets));
            } catch (Throwable e) {
                nativeResult = object("passed", false, "error", e.getClass().getSimpleName() + ": " + e.getMessage());
            }
            final JSONObject result = nativeResult, verifiedFixture = fixture;
            main.post(() -> complete(sequence, requestedGeneration, width, height,
                    SystemClock.elapsedRealtime() - started, reason, requestedSurface, result, verifiedFixture));
        });
    }

    private void complete(long sequence, long requestedGeneration, int width, int height,
            long duration, String reason, Surface requestedSurface, JSONObject nativeResult, JSONObject fixture) {
        if (destroyed) return;
        boolean obsolete = !active || !surfaceReady || requestedGeneration != generation
                || sequence != requestSequence || width != surfaceWidth || height != surfaceHeight
                || requestedSurface != surfaceView.getHolder().getSurface() || !requestedSurface.isValid();
        boolean checked = nativeResult.optBoolean("passed")
                && nativeResult.optBoolean("mesh_valid")
                && nativeResult.optBoolean("rig_valid")
                && nativeResult.optBoolean("morph_valid")
                && nativeResult.optBoolean("actor_sample_match")
                && nativeResult.optBoolean("morph_scale_match")
                && nativeResult.optBoolean("character_assembly_match")
                && nativeResult.optBoolean("character_valid")
                && nativeResult.optBoolean("hierarchy_match")
                && nativeResult.optBoolean("socket_palette_match")
                && nativeResult.optBoolean("animation_clock_match")
                && nativeResult.optBoolean("animated_preview_passed")
                && nativeResult.optBoolean("skin_transform_match")
                && nativeResult.optBoolean("skin_render_match")
                && nativeResult.optBoolean("material_pixel_match")
                && nativeResult.optBoolean("alpha_fog_passed")
                && nativeResult.optBoolean("offscreen_passed")
                && nativeResult.optBoolean("context_recreation_passed")
                && nativeResult.optBoolean("window_pixel_match")
                && nativeResult.optInt("pointer_bytes", -1) == 8
                && nativeResult.optInt("long_bytes", -1) == 8
                && nativeResult.optInt("required_cycles", -1) == 2
                && nativeResult.optInt("attempted_cycles", -1) == 2
                && nativeCyclesValid(nativeResult)
                && nativeResult.optInt("surface_width", -1) == width
                && nativeResult.optInt("surface_height", -1) == height;
        if (!obsolete && !checked) ++sessionFailures;
        JSONObject run = object("completed_at", time(), "request", sequence, "generation", requestedGeneration,
                "session_id", report.optString("session_id"),
                "callback_width", width, "callback_height", height, "duration_ms", duration,
                "reason", reason, "obsolete", obsolete, "passed", checked && !obsolete,
                "native", nativeResult,
                "java_validation", object("required_native_checks", checked,
                        "native_context_cycles_match", nativeCyclesValid(nativeResult),
                        "native_pointer_and_long_bytes_are_eight", nativeResult.optInt("pointer_bytes", -1) == 8
                                && nativeResult.optInt("long_bytes", -1) == 8,
                        "native_dimensions_match_callback", nativeResult.optInt("surface_width", -1) == width
                                && nativeResult.optInt("surface_height", -1) == height));
        runs.put(run); runs = trim(runs, MAX_RUNS);
        history.put(run); history = trim(history, MAX_RUNS);
        try { report.put("fixture", fixture); } catch (Exception ignored) {}
        event("probe_completed", object("request", sequence, "generation", requestedGeneration,
                "obsolete", obsolete, "passed", checked && !obsolete));
        refresh(obsolete ? "Obsolete result recorded; waiting for the current surface."
                : checked ? "Native character assembly check passed." : "Check failed; see the exported report.");
        if (autoSmoke && checked && !obsolete && active) {
            // Advance only after validated rendering, using actual SurfaceView callbacks.
            if (smokeStage == 0) { smokeStage = 1; main.post(this::resizeSurface); }
            else if (smokeStage == 1) { smokeStage = 2; main.post(this::recreateSurface); }
            else if (smokeStage == 2) { smokeStage = 3; event("auto_smoke_completed", new JSONObject()); refresh("Automated surface checks completed."); }
        }
    }

    private static boolean nativeCyclesValid(JSONObject nativeResult) {
        JSONArray cycles = nativeResult.optJSONArray("cycles");
        if (cycles == null || cycles.length() != 2) return false;
        for (int i = 0; i < cycles.length(); ++i) {
            JSONObject cycle = cycles.optJSONObject(i);
            if (cycle == null || !cycle.optBoolean("passed") || !cycle.optBoolean("context_created")
                    || !cycle.optBoolean("completed") || !cycle.optBoolean("objects_released")
                    || !cycle.optBoolean("swap_passed") || cycle.optInt("gl_errors", -1) != 0
                    || cycle.optInt("egl_error", -1) != 0
                    || cycle.optInt("preview_frames", -1) < 45
                    || cycle.optInt("distinct_animated_poses", -1) < 2
                    || cycle.optInt("preview_clock_wraps", -1) < 1) return false;
        }
        return true;
    }

    private JSONObject qualification() {
        Set<Long> generations = new HashSet<>();
        Set<String> dimensions = new HashSet<>();
        Set<Integer> widths = new HashSet<>(), heights = new HashSet<>();
        int failures = sessionFailures, successful = 0;
        boolean currentPassed = false;
        for (int i = 0; i < runs.length(); ++i) {
            JSONObject run = runs.optJSONObject(i);
            if (run == null || run.optBoolean("obsolete")) continue;
            if (!run.optBoolean("passed")) continue;
            ++successful;
            generations.add(run.optLong("generation"));
            dimensions.add(run.optInt("callback_width") + "x" + run.optInt("callback_height"));
            widths.add(run.optInt("callback_width")); heights.add(run.optInt("callback_height"));
            if (run.optLong("generation") == generation && run.optInt("callback_width") == surfaceWidth
                    && run.optInt("callback_height") == surfaceHeight
                    && run.optLong("request") == requestSequence) currentPassed = true;
        }
        JSONArray pending = new JSONArray();
        if (!currentPassed || !surfaceReady || !active) pending.put("Current foreground surface must pass");
        if (failures > 0) pending.put("A current-session check failed; inspect evidence and rerun in a new session");
        if (dimensions.size() < 2) pending.put("Two actual surface sizes must render successfully (use Resize surface)");
        if (widths.size() < 2 || heights.size() < 2) pending.put("Both actual width and height must change and render successfully");
        if (generations.size() < 2) pending.put("Two actual Surface generations must render successfully (use Recreate surface)");
        return object("passed", pending.length() == 0, "pending_requirements", pending,
                "successful_runs", successful, "failed_runs", failures,
                "successful_surface_generations", generations.size(), "successful_actual_dimensions", dimensions.size(),
                "successful_widths", widths.size(), "successful_heights", heights.size(),
                "current_surface_passed", currentPassed && surfaceReady && active,
                "native_context_recreation", "required in each passing native run",
                "limits", "Device-specific complete character assembly and single-clip diagnostic gate only; not full client/gameplay qualification");
    }
    private void event(String name, JSONObject details) {
        if (destroyed) return;
        events.put(object("at", time(), "elapsed_ms", SystemClock.elapsedRealtime(), "event", name,
                "generation", generation, "details", details));
        events = trim(events, MAX_EVENTS);
        persist();
    }
    private void refresh(String message) {
        if (destroyed) return;
        JSONObject qualification = qualification();
        boolean passed = qualification.optBoolean("passed");
        status.setText((passed ? "CHARACTER GATE PASSED — " : "QUALIFICATION PENDING — ") + message);
        status.setTextColor(passed ? Color.rgb(12, 96, 39) : Color.rgb(55, 62, 69));
        persist();
        try { reportText.setText(report.toString(2)); } catch (Exception ignored) {}
    }
    private void persist() {
        if (destroyed || report == null || reportFile == null) return;
        FileOutputStream stream = null;
        try {
            JSONObject q = qualification();
            report.put("updated_at", time()); report.put("qualification", q);
            report.put("qualification_passed", q.optBoolean("passed"));
            report.put("overall_passed", q.optBoolean("passed")); report.put("passed", q.optBoolean("passed"));
            report.put("events", events); report.put("native_runs", runs); report.put("run_history", history);
            report.put("auto_smoke_stage", smokeStage);
            report.put("session_failures", sessionFailures);
            stream = reportFile.startWrite();
            stream.write(report.toString(2).getBytes(StandardCharsets.UTF_8));
            reportFile.finishWrite(stream);
        } catch (Exception e) {
            if (stream != null) reportFile.failWrite(stream);
            if (status != null) status.setText("Report could not be saved: " + e.getMessage());
        }
    }
    private JSONArray readHistory() {
        try (InputStream input = reportFile.openRead()) {
            JSONObject previous = new JSONObject(new String(read(input, 4 * 1024 * 1024), StandardCharsets.UTF_8));
            JSONArray values = previous.optJSONArray("run_history");
            return values == null ? new JSONArray() : trim(values, MAX_RUNS);
        } catch (Exception e) { return new JSONArray(); }
    }
    private byte[] readAsset(String name, int limit) throws Exception {
        try (InputStream input = getAssets().open(name)) { return read(input, limit); }
    }
    private Map<String, byte[]> verifyAssets(JSONObject fixture) throws Exception {
        JSONObject manifest = fixture.getJSONObject("assets");
        if (manifest.length() != REQUIRED_ASSETS.size())
            throw new IllegalStateException("Animation asset manifest must contain exactly six files");
        Map<String, byte[]> assets = new LinkedHashMap<>();
        JSONObject verified = new JSONObject();
        int total = 0;
        Iterator<String> names = manifest.keys();
        while (names.hasNext()) {
            String name = names.next();
            if (!name.matches("[A-Za-z0-9][A-Za-z0-9_.-]{0,79}") || name.equals("character-fixture.json"))
                throw new IllegalStateException("Asset filename must be a simple bounded name: " + name);
            if (!REQUIRED_ASSETS.contains(name))
                throw new IllegalStateException("Unexpected animation asset: " + name);
            JSONObject entry = manifest.getJSONObject(name);
            Object byteValue = entry.opt("bytes"), hashValue = entry.opt("sha256");
            if (!(byteValue instanceof Number) || !(hashValue instanceof String))
                throw new IllegalStateException("Asset size and SHA256 must have exact manifest types: " + name);
            long size = ((Number) byteValue).longValue();
            if (((Number) byteValue).doubleValue() != (double) size || size <= 0 || size > MAX_ASSET_BYTES
                    || total > MAX_TOTAL_ASSET_BYTES - size)
                throw new IllegalStateException("Asset size exceeds bounded file/total limits: " + name);
            String expected = (String) hashValue;
            if (!expected.matches("[0-9a-fA-F]{64}"))
                throw new IllegalStateException("Asset SHA256 is invalid: " + name);
            byte[] bytes = readAsset(name, (int) size);
            String actual = sha256(bytes);
            if (bytes.length != size || !actual.equalsIgnoreCase(expected))
                throw new IllegalStateException("Asset length or SHA256 does not match its manifest: " + name);
            total += bytes.length;
            assets.put(name, bytes);
            verified.put(name, object("sha256", actual, "bytes", bytes.length));
        }
        fixture.put("verified_assets", verified);
        fixture.put("verified_total_bytes", total);
        return assets;
    }
    private static String runNative(Surface surface, Map<String, byte[]> assets) {
        return ProbeNative.probe(surface, requireAsset(assets, "character.bin"),
                requireAsset(assets, "rig.bin"), requireAsset(assets, "morph.bin"),
                requireAsset(assets, "character-reference.bin"), requireAsset(assets, "material-reference.bin"));
    }
    private static byte[] requireAsset(Map<String, byte[]> assets, String name) {
        byte[] value = assets.get(name);
        if (value == null) throw new IllegalStateException("Required verified animation asset is absent: " + name);
        return value;
    }
    private static byte[] read(InputStream input, int limit) throws Exception {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192]; int count;
        while ((count = input.read(buffer)) >= 0) {
            if (output.size() > limit - count) throw new IllegalStateException("File exceeds bounded input limit");
            output.write(buffer, 0, count);
        }
        return output.toByteArray();
    }
    private static String sha256(byte[] bytes) throws Exception {
        StringBuilder value = new StringBuilder();
        for (byte b : MessageDigest.getInstance("SHA-256").digest(bytes)) value.append(String.format(Locale.US, "%02x", b & 255));
        return value.toString();
    }
    private void exportReport() {
        persist();
        try { exportSnapshot = report.toString(2).getBytes(StandardCharsets.UTF_8); }
        catch (Exception e) { refresh("Could not capture the report: " + e.getMessage()); return; }
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("application/json");
        intent.putExtra(Intent.EXTRA_TITLE, "COH-NativeCharacter-" + new SimpleDateFormat("yyyyMMdd-HHmmss", Locale.US).format(new Date()) + ".json");
        try { startActivityForResult(intent, EXPORT_REPORT); }
        catch (Exception e) { refresh("No document provider is available: " + e.getMessage()); }
    }
    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (destroyed) return;
        if (request != EXPORT_REPORT || result != RESULT_OK || data == null || data.getData() == null) return;
        try (OutputStream output = getContentResolver().openOutputStream(data.getData(), "wt")) {
            if (output == null) throw new IllegalStateException("Document provider returned no stream");
            // Pausing for the document picker cannot turn a successful exported snapshot into pending.
            if (exportSnapshot == null) throw new IllegalStateException("No report snapshot; export again");
            output.write(exportSnapshot);
            exportSnapshot = null;
            refresh("Report exported.");
        } catch (Exception e) { refresh("Export failed: " + e.getMessage()); }
    }
    @Override protected void onResume() {
        super.onResume(); active = true;
        if (report == null) return;
        event("activity_resumed", new JSONObject());
        if (surfaceReady && surfaceWidth > 0 && surfaceHeight > 0) schedule("resume");
        runPendingAction();
    }
    @Override protected void onPause() {
        active = false; invalidateRequests(); event("activity_paused", new JSONObject());
        super.onPause();
    }
    @Override protected void onStop() { event("activity_stopped", new JSONObject()); super.onStop(); }
    @Override protected void onDestroy() {
        active = false; invalidateRequests(); event("activity_destroyed", new JSONObject()); destroyed = true;
        worker.shutdownNow(); super.onDestroy();
    }
    @Override protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent); setIntent(intent);
        pendingAction = intent.getStringExtra("probe_action");
        runPendingAction();
    }
    private void runPendingAction() {
        if (!active || destroyed || !surfaceReady || surfaceWidth <= 0 || pendingAction == null) return;
        String action = pendingAction; pendingAction = null;
        main.post(() -> {
            if (!active || destroyed) { pendingAction = action; return; }
            if (action.equals("resize")) resizeSurface();
            else if (action.equals("recreate")) recreateSurface();
            else if (action.equals("run")) schedule("intent");
            else event("unknown_intent_action", object("action", action));
        });
    }
    @Override public void onConfigurationChanged(Configuration configuration) {
        super.onConfigurationChanged(configuration);
        event("configuration_changed", object("orientation", configuration.orientation,
                "screen_width_dp", configuration.screenWidthDp, "screen_height_dp", configuration.screenHeightDp));
        // Layout causes actual surfaceChanged events; only those dimensions qualify.
    }
}
