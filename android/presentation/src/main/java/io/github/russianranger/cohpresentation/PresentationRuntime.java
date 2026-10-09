package io.github.russianranger.cohpresentation;

import android.content.Context;
import android.net.LocalSocket;
import android.net.LocalSocketAddress;
import android.os.Build;
import android.os.SystemClock;
import io.github.russianranger.cohdiagnostic.DiagnosticRuntime;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/** A short, isolated Wine-to-Android display check. No game server or SQL is started. */
public final class PresentationRuntime {
    public interface Listener {
        void onStage(String stage, String detail);
        void onLog(String line);
        void onFrame(int[] argb, int width, int height, long sequence);
    }
    public static final class Result {
        public final boolean passed;
        public final File report;
        public final String summary;
        Result(boolean passed, File report, String summary) {
            this.passed = passed; this.report = report; this.summary = summary;
        }
    }

    private static final long MAX_JSON = 2L * 1024 * 1024, MAX_LOG = 1024 * 1024;
    private static final String PROCESS_INSTANCE = UUID.randomUUID().toString();
    private static final String BLOCK_MESSAGE = "Runtime cleanup needs attention. Force-stop COH Client Test in Android settings, then reopen it.";
    private static boolean guardInitialized, blocked;
    private static boolean operationActive;
    private final Context context;
    private final Listener listener;
    private final File home, work, state;
    private final StringBuilder log = new StringBuilder();
    private final List<Map<String, Object>> surfaceSamples = new ArrayList<>();
    private final List<Map<String, Object>> lifecycle = new ArrayList<>();
    private volatile Process child;
    private volatile LocalSocket socket;
    private volatile RfbClient decoder;
    private volatile DiagnosticRuntime installer;
    private volatile boolean cancelled, finished, closingReceiver, runLaunched, producerCompleted;
    private volatile String receiverFailure;
    private volatile long decodedFrames;
    private volatile int frameWidth, frameHeight;
    private volatile File latestReport;
    private JSONObject manifest;
    private String manifestHash, session, operation, runId, error;
    private File generation, operationDir;
    private long startedUptime, endedUptime;
    private int processExit = -1;

    public PresentationRuntime(Context context, Listener listener) {
        this.context = context.getApplicationContext(); this.listener = listener;
        try {
            File files = this.context.getFilesDir().getCanonicalFile();
            home = new File(files, "m2"); work = new File(files, "presentation");
            state = new File(work, "state");
            work.mkdirs();
            initializeGuard(this.context);
            File pointer = new File(work, "latest-report.txt");
            if (pointer.isFile()) {
                File candidate = new File(new String(read(pointer, 4096), StandardCharsets.UTF_8).trim());
                if (candidate.isFile() && candidate.getCanonicalPath().startsWith(new File(work, "reports").getCanonicalPath() + File.separator))
                    latestReport = candidate;
            }
        } catch (IOException e) { throw new IllegalStateException("Cannot open private display storage", e); }
    }

    public static synchronized boolean cleanupBlocked(Context context) {
        initializeGuard(context.getApplicationContext());
        return blocked;
    }
    public boolean isCleanupBlocked() { return cleanupBlocked(context); }
    private static File guard(Context context) { return new File(context.getFilesDir(), "presentation/cleanup-guard.json"); }
    private static synchronized void initializeGuard(Context context) {
        if (guardInitialized) return;
        guardInitialized = true;
        File file = guard(context);
        if (!file.isFile()) return;
        try {
            JSONObject previous = json(file, 16384);
            if (PROCESS_INSTANCE.equals(previous.optString("process_instance"))) {
                blocked = "blocked".equals(previous.optString("status"));
            } else if ("running".equals(previous.optString("status"))) {
                // A crashed app may leave its guest descendants alive. Require an
                // explicit force-stop/reopen before allowing another owned run.
                block(context, "The previous display operation was interrupted");
            } else if ("blocked".equals(previous.optString("status"))) {
                if (!file.delete()) blocked = true;
            } else {
                block(context, "Unrecognized cleanup state");
            }
        } catch (Exception e) { block(context, "Could not read cleanup state"); }
    }
    private static synchronized void block(Context context, String reason) {
        blocked = true;
        try { write(guard(context), new JSONObject().put("status", "blocked")
                .put("process_instance", PROCESS_INSTANCE).put("reason", reason).toString().getBytes(StandardCharsets.UTF_8)); }
        catch (Exception ignored) { /* The in-process block remains authoritative. */ }
    }
    private synchronized void begin(String kind, String selectedSession) throws Exception {
        synchronized (PresentationRuntime.class) {
            if (cleanupBlocked(context)) throw new IOException(BLOCK_MESSAGE);
            if (operationActive) throw new IOException("A display operation is already running");
            operationActive = true;
        }
        operation = kind; session = selectedSession;
        runId = System.currentTimeMillis() + "-" + UUID.randomUUID().toString().replace("-", "").substring(0, 12);
        operationDir = new File(work, "reports/" + runId); operationDir.mkdirs();
        startedUptime = SystemClock.uptimeMillis();
        latestReport = null;
        File pointer = new File(work, "latest-report.txt");
        if (pointer.exists() && !pointer.delete()) {
            synchronized (PresentationRuntime.class) { operationActive = false; }
            throw new IOException("Cannot invalidate the previous support report");
        }
        recordLifecycle("operation_" + kind + "_started");
    }
    private void endOperation() {
        finished = true;
        synchronized (PresentationRuntime.class) { operationActive = false; }
    }
    public File getLatestReport() { return latestReport; }

    public Result setup() throws Exception {
        begin("setup", null);
        JSONObject report = new JSONObject();
        boolean ready = false;
        try {
            loadManifest(); check();
            installer = new DiagnosticRuntime(context, new DiagnosticRuntime.Listener() {
                public void onStage(String name, String detail) { stage(name, detail); }
                public void onLog(String text) { line(text); }
            });
            check(); installer.setupRuntime(); check();
            report.put("status", "setup_complete").put("passed", false)
                    .put("scope", "Runtime installation only; no display or game execution claimed");
            ready = true;
        } catch (Exception e) {
            error = message(e); report.put("status", cancelled ? "cancelled" : "failed").put("passed", false).put("error", error);
        } finally {
            installer = null;
            synchronized (this) {
                finished = true;
                if (cancelled) { ready = false; report.put("status", "cancelled").put("passed", false); }
            }
            endedUptime = SystemClock.uptimeMillis();
            try { publish(report, false, false); } finally { endOperation(); }
        }
        return new Result(ready, latestReport, ready ? "Runtime ready. Run the display check next."
                : cancelled ? "Runtime setup stopped. Export the latest report." : "Runtime setup failed: " + error);
    }

    public Result run(String selectedSession) throws Exception {
        if (selectedSession == null || !selectedSession.matches("[0-9a-f]{32}")) throw new IOException("Invalid display session identity");
        begin("display", selectedSession);
        JSONObject report = new JSONObject();
        Thread output = null, receiver = null;
        boolean launched = false, passed = false, cleanup = false, guestPassed = false;
        try {
            loadManifest(); check(); validateInstalled();
            state.mkdirs();
            removePreviousGuestOutput();
            File tmp = new File(operationDir, "tmp"); tmp.mkdirs();
            File prootTmp = new File(home.getParentFile(), "p").getCanonicalFile(); prootTmp.mkdirs();
            File socketDir = new File(home.getParentFile(), "s").getCanonicalFile(); socketDir.mkdirs();
            android.system.Os.chmod(socketDir.getPath(), 0700);
            File socketFile = new File(socketDir, "view.sock");
            if (prootTmp.getPath().getBytes(StandardCharsets.UTF_8).length + 27 > 107
                    || socketFile.getPath().getBytes(StandardCharsets.UTF_8).length > 106)
                throw new IOException("Private app path is too long for local display sockets");
            if (Files.exists(socketFile.toPath(), java.nio.file.LinkOption.NOFOLLOW_LINKS))
                throw new IOException("A previous private display socket remains. Export the report before running another check.");
            File root = new File(generation, "rootfs"); new File(root, "presentation-socket").mkdirs();
            String nativeDir = context.getApplicationInfo().nativeLibraryDir;
            File proot = new File(nativeDir, "libproot.so"), loader = new File(nativeDir, "libproot-loader.so");
            if (!proot.canExecute() || !loader.canExecute()) throw new IOException("The APK process runtime is missing");
            List<String> command = new ArrayList<>(Arrays.asList(proot.getPath(), "--link2symlink", "--kill-on-exit", "--sysvipc",
                    "-i", "1000:1000", "-r", root.getPath(), "-b", "/dev", "-b", "/proc", "-b", "/sys",
                    "-b", state.getPath() + ":/state", "-b", tmp.getPath() + ":/tmp",
                    "-b", socketDir.getPath() + ":/presentation-socket",
                    "-b", new File(generation, "assets").getPath() + ":/opt/coh",
                    "-b", new File(generation, "pg/opt/coh/pgsql").getPath() + ":/opt/coh/pgsql",
                    "-b", new File(generation, "wine").getPath() + ":/opt/wine",
                    "-b", new File(generation, "passwd").getPath() + ":/etc/passwd",
                    "-b", new File(generation, "group").getPath() + ":/etc/group",
                    "-w", "/state", "/usr/bin/env", "-i", "HOME=/state", "USER=coh", "LOGNAME=coh",
                    "PATH=/opt/coh/pgsql/bin:/usr/local/bin:/usr/bin:/bin", "LANG=C.UTF-8", "TZ=UTC", "TMPDIR=/tmp",
                    "PYTHONUNBUFFERED=1", "PYTHONDONTWRITEBYTECODE=1",
                    "/usr/bin/python3", "/opt/coh/presentation_diagnostic.py", "--state", "/state", "--assets", "/opt/coh",
                    "--pg-bin", "/opt/coh/pgsql/bin", "--wine", "/opt/wine/bin/wine", "--wineserver", "/opt/wine/bin/wineserver",
                    "--execution-platform", "android", "--session-id", session, "--duration-seconds", "60",
                    "--socket-dir", "/presentation-socket", "--timeout-seconds", "780"));
            ProcessBuilder builder = new ProcessBuilder(command).redirectErrorStream(true);
            builder.environment().put("PROOT_LOADER", loader.getPath());
            builder.environment().put("PROOT_TMP_DIR", prootTmp.getPath());
            builder.environment().put("PROOT_NO_SECCOMP", "1");
            write(guard(context), new JSONObject().put("status", "running").put("process_instance", PROCESS_INSTANCE)
                    .put("session_id", session).put("operation_id", runId).toString().getBytes(StandardCharsets.UTF_8));
            stage("Starting display check", "Preparing Wine, then showing a moving test pattern for 60 seconds.");
            check(); child = builder.start(); launched = true; runLaunched = true;
            Process process = child;
            output = new Thread(() -> captureOutput(process), "coh-display-output"); output.start();
            receiver = new Thread(() -> receiveFrames(process, socketFile), "coh-display-frames"); receiver.start();
            long deadline = System.nanoTime() + TimeUnit.MINUTES.toNanos(14);
            while (!process.waitFor(200, TimeUnit.MILLISECONDS)) {
                check();
                if (receiverFailure != null) throw new IOException("Local display connection failed: " + receiverFailure);
                if (System.nanoTime() > deadline) throw new IOException("Display check exceeded its 14 minute limit");
            }
            processExit = process.exitValue();
            output.join(2000); check();
        } catch (Exception e) {
            if (e instanceof InterruptedException || Thread.currentThread().isInterrupted()) cancelled = true;
            error = message(e); line("Display operation: " + error);
        } finally {
            boolean interrupted = Thread.interrupted();
            Process process = child;
            if (process != null && process.isAlive()) {
                signalStop();
                try {
                    if (!process.waitFor(30, TimeUnit.SECONDS)) {
                        process.destroy(); if (!process.waitFor(5, TimeUnit.SECONDS)) process.destroyForcibly();
                    }
                    process.waitFor(5, TimeUnit.SECONDS);
                } catch (InterruptedException e) { process.destroyForcibly(); }
            }
            closingReceiver = true; closeReceiver();
            join(receiver, 3000); join(output, 2000);
            boolean forcedCaptureClose = output != null && output.isAlive();
            if (forcedCaptureClose && process != null) {
                try { process.getInputStream().close(); } catch (IOException ignored) {}
                join(output, 2000);
            }
            if (process != null && !process.isAlive()) processExit = process.exitValue();
            synchronized (this) { finished = true; }
            endedUptime = SystemClock.uptimeMillis();
            try {
                File guest = new File(state, "latest-report.json");
                if (launched && guest.isFile()) {
                    try { report = json(guest, MAX_JSON); }
                    catch (Exception invalid) {
                        report = new JSONObject().put("status", "failed").put("passed", false)
                                .put("failures", new JSONArray().put("Guest report is unreadable"));
                        error = "Guest report is unreadable: " + invalid.getClass().getSimpleName();
                    }
                }
                else report.put("status", cancelled ? "cancelled" : "failed").put("passed", false)
                        .put("failures", new JSONArray().put(error == null ? "No complete guest report" : error));
                cleanup = !launched || (process != null && !process.isAlive() && !forcedCaptureClose
                        && (receiver == null || !receiver.isAlive()) && PresentationAcceptance.cleanupSafe(jsonValue(report)));
                if (!cleanup) { block(context, "Owned display processes could not be proved stopped"); error = BLOCK_MESSAGE; }
                else if (guard(context).exists() && !guard(context).delete()) {
                    block(context, "Cannot clear completed operation state"); cleanup = false; error = BLOCK_MESSAGE;
                }
                try { guestPassed = launched && processExit == 0 && guestAccepted(report); }
                catch (Exception invalid) { error = "Guest acceptance evidence is invalid: " + invalid.getClass().getSimpleName(); }
                passed = guestPassed && cleanup && !cancelled && error == null && surfaceAccepted(report);
                if (guestPassed && !passed && error == null) error = "Display check incomplete: not enough matching PixelCopy frames reached the Android surface.";
                publish(report, passed, cleanup);
            } finally {
                child = null; endOperation();
                if (interrupted) Thread.currentThread().interrupt();
            }
        }
        String summary = passed ? "Display check passed: a changing Wine test pattern reached the Android surface. Game rendering remains untested."
                : isCleanupBlocked() ? BLOCK_MESSAGE : cancelled ? "Display check stopped. Export the latest report."
                : guestPassed ? "Display check incomplete. Keep the test visible and export the latest report."
                : "Display check failed. Export the latest report.";
        stage(passed ? "Display check passed" : isCleanupBlocked() ? "Cleanup needs attention" : cancelled ? "Display check stopped"
                : guestPassed ? "Display check incomplete" : "Display check failed", summary);
        return new Result(passed, latestReport, summary);
    }

    public synchronized boolean requestStop() {
        if (finished) return false;
        cancelled = true; signalStop();
        DiagnosticRuntime activeInstaller = installer; if (activeInstaller != null) activeInstaller.requestStop();
        return true;
    }
    private synchronized void signalStop() {
        try { write(new File(state, "stop-request"), "stop\n".getBytes(StandardCharsets.UTF_8)); }
        catch (IOException e) { line("Could not write stop request: " + e.getClass().getSimpleName()); }
    }
    public synchronized void recordSurfaceCertification(Map<String, Object> record) {
        if (finished || session == null || !session.equals(record.get("session_id")) || surfaceSamples.size() >= 512) return;
        surfaceSamples.add(new LinkedHashMap<>(record));
    }
    public synchronized void recordLifecycle(String event) {
        if (lifecycle.size() >= 512) return;
        Map<String, Object> entry = new LinkedHashMap<>();
        entry.put("event", clean(event)); entry.put("uptime_ms", SystemClock.uptimeMillis());
        if (session != null) entry.put("session_id", session);
        lifecycle.add(entry);
    }
    private void check() throws InterruptedIOException {
        if (cancelled || Thread.currentThread().isInterrupted()) throw new InterruptedIOException("Display operation stopped");
    }
    private void receiveFrames(Process process, File file) {
        long deadline = System.nanoTime() + TimeUnit.MINUTES.toNanos(12);
        try {
            while (!cancelled && !closingReceiver && process.isAlive()) {
                if (System.nanoTime() > deadline) throw new IOException("Timed out waiting for the private display socket");
                LocalSocket candidate = new LocalSocket();
                try {
                    candidate.connect(new LocalSocketAddress(file.getPath(), LocalSocketAddress.Namespace.FILESYSTEM));
                    socket = candidate;
                    // This socket is app-private and there is no TCP listener or network fallback.
                    decoder = new RfbClient(candidate.getInputStream(), candidate.getOutputStream(), (pixels, width, height, sequence) -> {
                        if (closingReceiver || cancelled) return;
                        decodedFrames++; frameWidth = width; frameHeight = height;
                        listener.onFrame(pixels, width, height, sequence);
                    });
                    decoder.run(); return;
                } catch (IOException e) {
                    try { candidate.close(); } catch (IOException ignored) {}
                    if (socket == candidate) {
                        // EOF is normal when the producer/display exits. The guest
                        // exit and strict report gates decide whether that was success.
                        if (e instanceof EOFException) return;
                        throw e;
                    }
                    Thread.sleep(250);
                }
            }
        } catch (Exception e) {
            if (!closingReceiver && !cancelled && process.isAlive() && !producerCompleted) receiverFailure = message(e);
            else if (producerCompleted) recordLifecycle("display_socket_closed_after_producer: " + message(e));
        } finally { closeReceiver(); }
    }
    private void closeReceiver() {
        LocalSocket active = socket; socket = null;
        if (active != null) try { active.close(); } catch (IOException ignored) {}
        RfbClient activeDecoder = decoder; decoder = null;
        if (activeDecoder != null) try { activeDecoder.close(); } catch (IOException ignored) {}
    }
    private static void join(Thread thread, long millis) {
        if (thread != null) try { thread.join(millis); } catch (InterruptedException ignored) {}
    }
    private void captureOutput(Process process) {
        try (Reader in = new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8)) {
            char[] block = new char[4096]; StringBuilder pending = new StringBuilder(); boolean omitted = false; int count;
            while ((count = in.read(block)) != -1) for (int i = 0; i < count; i++) {
                char c = block[i];
                if (c == '\n') {
                    String text = pending.toString(); pending.setLength(0);
                    if (!omitted) try {
                        JSONObject event = new JSONObject(text);
                        if ("stage".equals(event.optString("type")) && "visible_presentation_frames".equals(event.optString("stage"))
                                && "passed".equals(event.optString("status"))) producerCompleted = true;
                        if ("stage".equals(event.optString("type"))) listener.onStage(event.optString("stage", "Checking display"),
                                clean(event.optString("message", event.optString("detail", ""))));
                    } catch (Exception ignored) {}
                    line(text + (omitted ? " [line truncated]" : "")); omitted = false;
                } else if (pending.length() < 8192) pending.append(c); else omitted = true;
            }
            if (pending.length() > 0) line(pending.toString());
        } catch (IOException e) { line("Output capture closed: " + e.getClass().getSimpleName()); }
    }
    private void loadManifest() throws Exception {
        byte[] bytes;
        try (InputStream in = context.getAssets().open("runtime/runtime-manifest.json")) { bytes = read(in, MAX_JSON); }
        manifest = new JSONObject(new String(bytes, StandardCharsets.UTF_8));
        manifestHash = hex(MessageDigest.getInstance("SHA-256").digest(bytes));
        generation = new File(home, "runtime-" + manifestHash.substring(0, 16));
        if (manifest.getInt("format") != 1) throw new IOException("Unsupported display package");
    }
    private void validateInstalled() throws Exception {
        File ready = new File(generation, "ready.json");
        if (!ready.isFile() || !manifestHash.equals(json(ready, 16384).optString("manifest_sha256")))
            throw new IOException("Set up the display runtime first");
        JSONObject files = manifest.getJSONObject("files");
        for (Iterator<String> it = files.keys(); it.hasNext();) {
            String name = it.next();
            if (!name.matches("[A-Za-z0-9_.-]+")) throw new IOException("Unsafe runtime member");
            File file = new File(generation, "assets/" + name); JSONObject pin = files.getJSONObject(name);
            if (!file.isFile() || file.length() != pin.getLong("bytes") || !sha(file).equals(pin.getString("sha256")))
                throw new IOException("Runtime integrity check failed: " + name);
        }
        if (!files.has("presentation_diagnostic.py")) throw new IOException("Presentation diagnostic is missing");
    }
    private void removePreviousGuestOutput() throws IOException {
        for (String name : new String[]{"stop-request", "latest-report.json", "report.zip"}) {
            File file = new File(state, name);
            if (file.exists() && !file.delete()) throw new IOException("Cannot clear previous guest output: " + name);
        }
    }

    private boolean guestAccepted(JSONObject report) throws Exception {
        if (!(report.optBoolean("passed") && "passed".equals(report.optString("status"))
                && session.equals(report.optString("session_id"))
                && "visible_presentation_guest".equals(report.optString("scope"))
                && "visible_presentation".equals(report.optString("diagnostic_mode"))
                && "android".equals(report.optString("execution_platform_requested"))
                && report.optJSONArray("failures") != null && report.getJSONArray("failures").length() == 0
                && Boolean.FALSE.equals(report.opt("postgres_started"))
                && Boolean.FALSE.equals(report.opt("android_surface_validated"))
                && Boolean.FALSE.equals(report.opt("game_validated"))
                && Boolean.FALSE.equals(report.opt("hardware_acceleration_validated"))
                && report.optBoolean("presentation_socket_removed")
                && PresentationAcceptance.cleanupSafe(jsonValue(report)))) return false;
        JSONObject producer = report.optJSONObject("producer");
        if (producer == null || producer.optInt("format") != 1 || !"passed".equals(producer.optString("status"))
                || !"".equals(producer.optString("failure_stage", "missing"))
                || !session.equals(producer.optString("session_id")) || producer.optInt("width") != 800
                || producer.optInt("height") != 600 || producer.optInt("frames") != 120
                || producer.optInt("duration_seconds") != 60 || producer.optInt("pointer_bits") != 32
                || producer.optInt("frame_contract") != 1 || !producer.optBoolean("readback_verified")
                || report.optInt("frames_emitted") != 120
                || Boolean.TRUE.equals(producer.opt("android_surface_validated"))
                || Boolean.TRUE.equals(producer.opt("game_validated"))) return false;
        JSONObject hashes = report.optJSONObject("asset_sha256"), pins = manifest.getJSONObject("files");
        if (hashes == null || hashes.length() < 10) return false;
        for (Iterator<String> it = hashes.keys(); it.hasNext();) {
            String name = it.next();
            if (!pins.has(name) || !pins.getJSONObject(name).getString("sha256").equals(hashes.optString(name))) return false;
        }
        String[] requiredStages = {"presentation_inputs", "presentation_display", "wine_initialization", "win32_runtime_dll", "visible_presentation_frames"};
        JSONArray stages = report.optJSONArray("stages");
        if (stages == null || stages.length() != requiredStages.length) return false;
        for (int i = 0; i < requiredStages.length; i++) {
            JSONObject stage = stages.getJSONObject(i);
            if (!requiredStages[i].equals(stage.optString("stage")) || !"passed".equals(stage.optString("status"))) return false;
        }
        return true;
    }
    private boolean surfaceAccepted(JSONObject report) {
        long frames = producerFrames(report);
        synchronized (this) { return decodedFrames >= 6 && PresentationAcceptance.surfaceAccepted(surfaceSamples, session,
                startedUptime, endedUptime, frames); }
    }
    private long producerFrames(JSONObject report) {
        JSONObject producer = report.optJSONObject("producer");
        return producer == null ? -1 : producer.optLong("frames", -1);
    }

    private void publish(JSONObject guest, boolean passed, boolean cleanup) throws IOException {
        try {
            JSONObject wrapper = new JSONObject().put("format", 1).put("operation", operation).put("run_id", runId)
                    .put("session_id", session == null ? JSONObject.NULL : session).put("app_id", context.getPackageName())
                    .put("app_version", appVersion()).put("android_sdk", Build.VERSION.SDK_INT)
                    .put("android_uid", android.os.Process.myUid()).put("device", Build.MANUFACTURER + " " + Build.MODEL)
                    .put("abis", new JSONArray(Arrays.asList(Build.SUPPORTED_ABIS)))
                    .put("runtime_manifest_sha256", manifestHash).put("started_uptime_ms", startedUptime)
                    .put("finished_uptime_ms", endedUptime).put("process_exit_code", processExit)
                    .put("passed", passed).put("android_surface_validated", passed).put("cleanup_verified", cleanup)
                    .put("cleanup_blocked", isCleanupBlocked()).put("cancelled", cancelled)
                    .put("gameplay_validated", false).put("game_rendering_validated", false)
                    .put("hardware_acceleration_validated", false).put("controller_input_validated", false)
                    .put("scope", "Synthetic Wine pattern presented through a private local socket and verified with Android PixelCopy")
                    .put("decoded_frame_count", decodedFrames).put("producer_frame_count", producerFrames(guest))
                    .put("source_width", frameWidth).put("source_height", frameHeight)
                    .put("guest", guest);
            if (error != null) wrapper.put("app_error", error);
            if (receiverFailure != null) wrapper.put("receiver_error", receiverFailure);
            synchronized (this) {
                wrapper.put("surface_certifications", new JSONArray(surfaceSamples));
                wrapper.put("lifecycle", new JSONArray(lifecycle));
            }
            String status = isCleanupBlocked() ? "cleanup_failed" : cancelled ? "cancelled" : passed ? "passed"
                    : "setup".equals(operation) ? guest.optString("status", "failed")
                    : guest.optBoolean("passed") ? "display_incomplete" : "failed";
            wrapper.put("status", status);
            File target = new File(operationDir, "coh-display-test-" + runId + ".zip");
            File part = new File(operationDir, "support.zip.part");
            try (ZipOutputStream out = new ZipOutputStream(new FileOutputStream(part))) {
                zipText(out, "android-presentation-report.json", wrapper.toString(2));
                synchronized (this) { zipText(out, "operation.log", log.toString()); }
                if (manifest != null) zipText(out, "runtime-manifest.json", manifest.toString(2));
                if (generation != null) {
                    File assets = new File(generation, "assets");
                    File[] identities = assets.listFiles((dir, name) -> name.endsWith("manifest.json") && !name.equals("runtime-manifest.json"));
                    if (identities != null) for (File file : identities) if (file.length() <= MAX_JSON)
                        zipBytes(out, "identities/" + file.getName(), read(file, MAX_JSON));
                }
                try (InputStream in = context.getAssets().open("runtime/runtime-lock.json")) {
                    zipBytes(out, "runtime-lock.json", read(in, MAX_JSON));
                }
                if ("display".equals(operation) && runLaunched) {
                    File file = new File(state, "report.zip");
                    if (file.isFile()) zipBytes(out, "guest-report.zip", read(file, 32L * 1024 * 1024));
                }
            }
            Files.move(part.toPath(), target.toPath(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
            write(new File(work, "latest-report.txt"), target.getCanonicalPath().getBytes(StandardCharsets.UTF_8));
            latestReport = target;
        } catch (Exception e) { throw new IOException("Could not save a fresh display support report", e); }
    }
    private String appVersion() {
        try { return context.getPackageManager().getPackageInfo(context.getPackageName(), 0).versionName; }
        catch (Exception e) { return "unknown"; }
    }
    private synchronized void line(String text) {
        text = clean(text); if (text.length() > 8192) text = text.substring(0, 8192);
        log.append(text).append('\n');
        if (log.length() > MAX_LOG) log.delete(0, log.length() - (int) MAX_LOG);
        listener.onLog(text);
    }
    private void stage(String name, String detail) { listener.onStage(name, detail); line(name + ": " + detail); }
    private static String clean(String value) {
        return (value == null ? "" : value).replaceAll("(?i)(password|pwd|token|secret)(\\s*[=:]\\s*)([^;\\s]+)", "$1$2[redacted]");
    }
    private static String message(Exception e) { return clean(e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage()); }
    private String sha(File file) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream in = new FileInputStream(file)) {
            byte[] data = new byte[1024 * 1024]; int count;
            while ((count = in.read(data)) != -1) { check(); digest.update(data, 0, count); }
        }
        return hex(digest.digest());
    }
    private static String hex(byte[] bytes) {
        StringBuilder out = new StringBuilder(); for (byte b : bytes) out.append(String.format(Locale.ROOT, "%02x", b & 255)); return out.toString();
    }
    private static JSONObject json(File file, long limit) throws Exception {
        return new JSONObject(new String(read(file, limit), StandardCharsets.UTF_8));
    }
    private static byte[] read(File file, long limit) throws IOException {
        try (InputStream in = new FileInputStream(file)) { return read(in, limit); }
    }
    private static byte[] read(InputStream in, long limit) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream(); byte[] bytes = new byte[8192]; int count;
        while ((count = in.read(bytes)) != -1) {
            if (out.size() + count > limit) throw new IOException("Support input exceeds size limit");
            out.write(bytes, 0, count);
        }
        return out.toByteArray();
    }
    private static void write(File file, byte[] bytes) throws IOException {
        file.getParentFile().mkdirs(); File part = new File(file.getParentFile(), file.getName() + ".part");
        try (FileOutputStream out = new FileOutputStream(part)) { out.write(bytes); out.getFD().sync(); }
        Files.move(part.toPath(), file.toPath(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
    }
    private static Object jsonValue(Object value) throws Exception {
        if (value instanceof JSONObject) {
            JSONObject source = (JSONObject) value; Map<String, Object> target = new LinkedHashMap<>();
            for (Iterator<String> it = source.keys(); it.hasNext();) { String key = it.next(); target.put(key, jsonValue(source.get(key))); }
            return target;
        }
        if (value instanceof JSONArray) {
            JSONArray source = (JSONArray) value; List<Object> target = new ArrayList<>();
            for (int i = 0; i < source.length(); i++) target.add(jsonValue(source.get(i))); return target;
        }
        return value;
    }
    private static void zipText(ZipOutputStream out, String name, String text) throws IOException {
        zipBytes(out, name, text.getBytes(StandardCharsets.UTF_8));
    }
    private static void zipBytes(ZipOutputStream out, String name, byte[] bytes) throws IOException {
        out.putNextEntry(new ZipEntry(name)); out.write(bytes); out.closeEntry();
    }
}
