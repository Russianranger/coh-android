package io.github.russianranger.cohclientinteractive;

import android.content.Context;
import android.net.LocalSocket;
import android.net.Uri;
import io.github.russianranger.cohatlas.AtlasAssetImporter;

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
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.RejectedExecutionException;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/** Starts the pinned real CoH client in an isolated app runtime; never starts a game server or SQL. */
public final class ClientRuntime {
    public interface Listener {
        void onStage(String stage, String detail);
        void onLog(String line);
        void onFrame(int[] argb, int width, int height, long sequence);
        void onInputState(boolean ready, boolean finishing, long sent, long failed, long deadline);
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
    private static final long MAX_GUEST_ZIP = 160L * 1024 * 1024;
    private static final String PROCESS_INSTANCE = UUID.randomUUID().toString();
    private static final String BLOCK_MESSAGE = "Runtime cleanup needs attention. Force-stop COH Client Interactive in Android settings, then reopen it.";
    private static boolean guardInitialized, blocked;
    private static boolean operationActive;
    private final Context context;
    private final Listener listener;
    private final File home, work, state;
    private final StringBuilder log = new StringBuilder();
    private final List<Map<String, Object>> surfaceSamples = new ArrayList<>();
    private final List<byte[]> surfacePngs = new ArrayList<>();
    private final List<Map<String, Object>> interactionSamples = new ArrayList<>();
    private final List<byte[]> interactionPngs = new ArrayList<>();
    private final ThreadPoolExecutor inputWorker = new ThreadPoolExecutor(1, 1, 0L, TimeUnit.MILLISECONDS,
            new ArrayBlockingQueue<Runnable>(128), runnable -> new Thread(runnable, "coh-interactive-input"));
    private volatile boolean inputReady, finishRequested;
    private volatile long inputSent, inputFailed, readyDeadlineUptimeMillis;
    private long lastInputUptime = -1, lastInputFrameWatermark = -1, interactionCaptureId, lastInputRefresh;
    private long lastCapturedInputCount = -1;
    private boolean finishCaptureRetained;
    private volatile AtlasAssetImporter.Control importControl;
    private AtlasAssetImporter.Summary imported;
    private volatile long clientWindowObservedUptime = -1, clientWindowEndedUptime = -1;
    private final List<Map<String, Object>> lifecycle = new ArrayList<>();
    private volatile Process child;
    private volatile LocalSocket socket;
    private volatile InteractiveRfbClient decoder;
    private volatile DiagnosticRuntime installer;
    private volatile boolean cancelled, finished, closingReceiver, runLaunched, producerCompleted;
    private volatile String receiverFailure;
    private volatile long decodedFrames;
    private volatile int frameWidth, frameHeight;
    private volatile File latestReport;
    private JSONObject manifest, clientManifest;
    private volatile long observedClientPid = -1, clientWindowFrameWatermark = -1;
    private String manifestHash, session, operation, runId, error;
    private File generation, operationDir;
    private long startedUptime, endedUptime;
    private int processExit = -1;

    public ClientRuntime(Context context, Listener listener) {
        this.context = context.getApplicationContext(); this.listener = listener;
        try {
            File files = this.context.getFilesDir().getCanonicalFile();
            home = new File(files, "m2"); work = new File(files, "client");
            state = new File(work, "state");
            work.mkdirs();
            initializeGuard(this.context);
            File pointer = new File(work, "latest-report.txt");
            if (pointer.isFile()) {
                File candidate = new File(new String(read(pointer, 4096), StandardCharsets.UTF_8).trim());
                if (candidate.isFile() && candidate.getCanonicalPath().startsWith(new File(work, "reports").getCanonicalPath() + File.separator))
                    latestReport = candidate;
            }
        } catch (IOException e) { throw new IllegalStateException("Cannot open private client storage", e); }
    }

    public static synchronized boolean cleanupBlocked(Context context) {
        initializeGuard(context.getApplicationContext());
        return blocked;
    }
    public boolean isCleanupBlocked() { return cleanupBlocked(context); }
    private static File guard(Context context) { return new File(context.getFilesDir(), "client/cleanup-guard.json"); }
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
                block(context, "The previous client operation was interrupted");
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
        synchronized (ClientRuntime.class) {
            if (cleanupBlocked(context)) throw new IOException(BLOCK_MESSAGE);
            if (operationActive) throw new IOException("A client operation is already running");
            operationActive = true;
        }
        operation = kind; session = selectedSession;
        runId = System.currentTimeMillis() + "-" + UUID.randomUUID().toString().replace("-", "").substring(0, 12);
        operationDir = new File(work, "reports/" + runId); operationDir.mkdirs();
        startedUptime = SystemClock.uptimeMillis();
        latestReport = null;
        File pointer = new File(work, "latest-report.txt");
        if (pointer.exists() && !pointer.delete()) {
            synchronized (ClientRuntime.class) { operationActive = false; }
            throw new IOException("Cannot invalidate the previous support report");
        }
        recordLifecycle("operation_" + kind + "_started");
    }
    private void endOperation() {
        finished = true; inputReady = false; inputWorker.shutdownNow();
        synchronized (ClientRuntime.class) { operationActive = false; }
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
        return new Result(ready, latestReport, ready ? "Runtime ready. Import the pinned Atlas assets, then start an interactive client session."
                : cancelled ? "Runtime setup stopped. Export the latest report." : "Runtime setup failed: " + error);
    }

    private AtlasAssetImporter importer() throws IOException {
        return new AtlasAssetImporter(new File(home.getParentFile(), "client-import"),
                name -> context.getAssets().open("atlas/" + name));
    }

    public Result importAssets(Uri selected) throws Exception {
        if (selected == null) throw new IOException("Select the pinned Atlas asset ZIP first");
        begin("import", null);
        JSONObject report = new JSONObject();
        boolean ready = false;
        try {
            loadManifest(); check();
            importControl = new AtlasAssetImporter.Control();
            check();
            AtlasAssetImporter assetImporter = importer();
            InputStream input = context.getContentResolver().openInputStream(selected);
            if (input == null) throw new IOException("The selected asset archive could not be opened");
            // The unchanged importer owns and closes this stream, verifies the full
            // selected archive once, and atomically publishes its verified receipt.
            imported = assetImporter.importArchive(input, (phase, files, totalFiles, bytes, totalBytes) -> {
                String detail = totalFiles > 0 ? files + " / " + totalFiles + " files"
                        : totalBytes > 0 ? (bytes / (1024 * 1024)) + " / " + (totalBytes / (1024 * 1024)) + " MiB" : phase;
                listener.onStage(phase, detail);
            }, importControl);
            ready = true;
            report.put("status", "import_complete").put("passed", false)
                    .put("scope", "Verified asset import only; no client or game execution claimed");
        } catch (Exception e) {
            error = message(e);
            report.put("status", cancelled || e instanceof AtlasAssetImporter.CancelledException ? "cancelled" : "failed")
                    .put("passed", false).put("error", error);
        } finally {
            synchronized (this) { finished = true; importControl = null; }
            endedUptime = SystemClock.uptimeMillis();
            try { publish(report, false, false); } finally { endOperation(); }
        }
        return new Result(ready, latestReport, ready ? "Verified game assets are ready. Start an interactive client session next."
                : cancelled ? "Asset import stopped; the previous verified content is preserved."
                : "Asset import failed: " + error);
    }

    public Result run(String selectedSession) throws Exception {
        if (selectedSession == null || !selectedSession.matches("[0-9a-f]{32}")) throw new IOException("Invalid client session identity");
        begin("client_interaction", selectedSession);
        JSONObject report = new JSONObject();
        Thread output = null, receiver = null;
        boolean launched = false, passed = false, cleanup = false, guestPassed = false;
        try {
            loadManifest(); check(); validateInstalled();
            imported = importer().inspect();
            if (imported == null) throw new IOException("Import the pinned Atlas assets before starting the client");
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
            new File(root, "game-import").mkdirs();
            String nativeDir = context.getApplicationInfo().nativeLibraryDir;
            File proot = new File(nativeDir, "libproot.so"), loader = new File(nativeDir, "libproot-loader.so");
            if (!proot.canExecute() || !loader.canExecute()) throw new IOException("The APK process runtime is missing");
            List<String> command = new ArrayList<>(Arrays.asList(proot.getPath(), "--link2symlink", "--kill-on-exit", "--sysvipc",
                    "-i", "1000:1000", "-r", root.getPath(), "-b", "/dev", "-b", "/proc", "-b", "/sys",
                    "-b", state.getPath() + ":/state", "-b", tmp.getPath() + ":/tmp",
                    "-b", socketDir.getPath() + ":/presentation-socket",
                    "-b", imported.dataDirectory.getParentFile().getCanonicalPath() + ":/game-import",
                    "-b", new File(generation, "assets").getPath() + ":/opt/coh",
                    "-b", new File(generation, "pg/opt/coh/pgsql").getPath() + ":/opt/coh/pgsql",
                    "-b", new File(generation, "wine").getPath() + ":/opt/wine",
                    "-b", new File(generation, "passwd").getPath() + ":/etc/passwd",
                    "-b", new File(generation, "group").getPath() + ":/etc/group",
                    "-w", "/state", "/usr/bin/env", "-i", "HOME=/state", "USER=coh", "LOGNAME=coh",
                    "PATH=/opt/coh/pgsql/bin:/usr/local/bin:/usr/bin:/bin", "LANG=C.UTF-8", "TZ=UTC", "TMPDIR=/tmp",
                    "PYTHONUNBUFFERED=1", "PYTHONDONTWRITEBYTECODE=1",
                    "/usr/bin/python3", "/opt/coh/client_interactive_diagnostic.py", "--state", "/state", "--assets", "/opt/coh",
                    "--pg-bin", "/opt/coh/pgsql/bin", "--wine", "/opt/wine/bin/wine", "--wineserver", "/opt/wine/bin/wineserver",
                    "--execution-platform", "android", "--session-id", session,
                    "--game-data", "/game-import/data", "--socket-dir", "/presentation-socket",
                    "--startup-timeout-seconds", "900", "--observation-seconds", "30", "--interaction-seconds", "180", "--timeout-seconds", "1620"));
            ProcessBuilder builder = new ProcessBuilder(command).redirectErrorStream(true);
            builder.environment().put("PROOT_LOADER", loader.getPath());
            builder.environment().put("PROOT_TMP_DIR", prootTmp.getPath());
            builder.environment().put("PROOT_NO_SECCOMP", "1");
            write(guard(context), new JSONObject().put("status", "running").put("process_instance", PROCESS_INSTANCE)
                    .put("session_id", session).put("operation_id", runId).toString().getBytes(StandardCharsets.UTF_8));
            stage("Starting City of Heroes", "Preparing Wine and the verified client files, then checking the actual client window.");
            check(); child = builder.start(); launched = true; runLaunched = true;
            Process process = child;
            output = new Thread(() -> captureOutput(process), "coh-client-output"); output.start();
            receiver = new Thread(() -> receiveFrames(process, socketFile), "coh-client-frames"); receiver.start();
            long deadline = System.nanoTime() + TimeUnit.MINUTES.toNanos(28);
            while (!process.waitFor(200, TimeUnit.MILLISECONDS)) {
                check();
                if (receiverFailure != null) throw new IOException("Local display connection failed: " + receiverFailure);
                if (System.nanoTime() > deadline) throw new IOException("Client startup exceeded its 28 minute limit");
            }
            processExit = process.exitValue();
            output.join(2000); check();
        } catch (Exception e) {
            if (e instanceof InterruptedException || Thread.currentThread().isInterrupted()) cancelled = true;
            error = message(e); line("Client operation: " + error);
        } finally {
            boolean interrupted = Thread.interrupted();
            stopInputWorker();
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
            try { inputWorker.awaitTermination(3, TimeUnit.SECONDS); } catch (InterruptedException ignored) {}
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
                        && (receiver == null || !receiver.isAlive()) && inputWorker.isTerminated()
                        && ClientAcceptance.cleanupSafe(jsonValue(report)));
                if (!cleanup) { block(context, "Owned display processes could not be proved stopped"); error = BLOCK_MESSAGE; }
                else if (guard(context).exists() && !guard(context).delete()) {
                    block(context, "Cannot clear completed operation state"); cleanup = false; error = BLOCK_MESSAGE;
                }
                try { guestPassed = launched && processExit == 0 && guestAccepted(report); }
                catch (Exception invalid) { error = "Guest acceptance evidence is invalid: " + invalid.getClass().getSimpleName(); }
                if (launched && processExit == 0 && report.optBoolean("passed") && !guestPassed && error == null)
                    error = "The guest completed, but its current-session client evidence did not match this APK.";
                if (receiverFailure != null && error == null) error = "Local display connection failed: " + receiverFailure;
                passed = guestPassed && cleanup && !cancelled && error == null && receiverFailure == null
                        && inputFailed == 0 && surfaceAccepted(report);
                if (inputFailed > 0 && error == null) error = "Input transport failed; review the exported report.";
                if (guestPassed && !passed && error == null) error = "Client startup incomplete: three current-session PixelCopy captures were not retained while the client window was alive.";
                publish(report, passed, cleanup);
            } finally {
                child = null; endOperation();
                if (interrupted) Thread.currentThread().interrupt();
            }
        }
        String summary = passed ? "Interactive session complete with Android captures and verified cleanup. Input effects require manual review of the exported screenshots; no login or gameplay is claimed."
                : isCleanupBlocked() ? BLOCK_MESSAGE : cancelled ? "Interactive session stopped. Export the latest report."
                : guestPassed ? "Interactive session incomplete. Export the latest report."
                : "Interactive session failed. Export the latest report.";
        stage(passed ? "Interactive session complete" : isCleanupBlocked() ? "Cleanup needs attention" : cancelled ? "Interactive session stopped"
                : guestPassed ? "Interactive session incomplete" : "Interactive session failed", summary);
        return new Result(passed, latestReport, summary);
    }

    public synchronized boolean requestStop() {
        if (finished || producerCompleted) return false;
        AtlasAssetImporter.Control control = importControl;
        if (control != null && !control.requestCancel()) return false;
        inputReady = false; cancelPendingInput(); releaseAllInputs(session);
        cancelled = true; signalStop(); notifyInputState();
        DiagnosticRuntime activeInstaller = installer; if (activeInstaller != null) activeInstaller.requestStop();
        return true;
    }
    private interface InputWrite { void write(InteractiveRfbClient active, long epoch) throws IOException; }
    public boolean sendPointer(String selectedSession, int x, int y, int mask) {
        if (x < 0 || y < 0 || mask < 0 || mask > 7) return false;
        return queueInput(selectedSession, (active, epoch) -> active.sendPointer(x, y, mask, epoch));
    }
    public boolean sendKey(String selectedSession, int keysym, boolean down) {
        if (keysym <= 0) return false;
        return queueInput(selectedSession, (active, epoch) -> active.sendKey(keysym, down, epoch));
    }
    private synchronized boolean queueInput(String selectedSession, InputWrite action) {
        if (!inputReady || finishRequested || finished || cancelled || producerCompleted
                || session == null || !session.equals(selectedSession)) return false;
        InteractiveRfbClient queuedDecoder = decoder;
        if (queuedDecoder == null) return false;
        // Bind at queue acceptance: a task which starts after a lifecycle release
        // must not adopt the new epoch and deliver a stale delayed press.
        long queuedEpoch = queuedDecoder.inputEpoch();
        try {
            inputWorker.execute(() -> {
                InteractiveRfbClient active = decoder;
                if (!inputReady || finishRequested || finished || cancelled || producerCompleted || active != queuedDecoder) return;
                try {
                    // The executor and decoder both serialize writes. Never retain
                    // key values or typed text in the evidence archive.
                    action.write(active, queuedEpoch);
                    synchronized (ClientRuntime.this) {
                        inputSent++; lastInputUptime = SystemClock.uptimeMillis();
                        lastInputFrameWatermark = decodedFrames;
                    }
                    long now = SystemClock.uptimeMillis();
                    if (now - lastInputRefresh >= 500) { active.requestFullUpdate(); lastInputRefresh = now; }
                    notifyInputState();
                } catch (InteractiveRfbClient.InputCancelledException discarded) {
                    // An intentionally discarded pending gesture is neither a
                    // sent input event nor a transport failure.
                } catch (IOException failure) { inputFailure("Input transport write failed"); }
            });
            return true;
        } catch (RejectedExecutionException full) {
            inputFailure("Input queue exceeded its bound");
            inputWorker.getQueue().clear();
            releaseAllInputs(selectedSession);
            return false;
        }
    }
    private void notifyInputState() {
        listener.onInputState(inputReady && !finishRequested && !producerCompleted && !cancelled && !finished,
                finishRequested && !finished, inputSent, inputFailed, readyDeadlineUptimeMillis);
    }
    private synchronized void inputFailure(String detail) {
        inputFailed++; inputReady = false; cancelPendingInput();
        receiverFailure = detail; recordLifecycle(detail); notifyInputState();
    }
    private void releaseOnInputWorker() {
        InteractiveRfbClient active = decoder;
        if (active == null) return;
        try { active.releaseAllInputs(); recordLifecycle("held_input_released"); }
        catch (IOException failure) {
            if (!producerCompleted && !closingReceiver && !cancelled) inputFailure("Input release failed");
        }
    }
    public synchronized void releaseAllInputs(String selectedSession) {
        queueRelease(selectedSession, false);
    }
    public synchronized void discardPendingInputs(String selectedSession) {
        queueRelease(selectedSession, true);
    }
    private void queueRelease(String selectedSession, boolean discard) {
        if (session == null || !session.equals(selectedSession) || finished || inputWorker.isShutdown()) return;
        if (finishRequested) return; // The queued Finish already releases input before writing its request.
        if (discard) { cancelPendingInput(); inputWorker.getQueue().clear(); }
        if (decoder == null || clientWindowObservedUptime < 0) return;
        try { inputWorker.execute(this::releaseOnInputWorker); }
        catch (RejectedExecutionException full) {
            inputFailure("Input release queue exceeded its bound");
            // Saturation must not leave an already-sent key/button held while
            // the queued presses become ineligible after inputFailure.
            inputWorker.getQueue().clear();
            try { inputWorker.execute(this::releaseOnInputWorker); }
            catch (RejectedExecutionException closed) { /* Socket closure in cleanup terminates the session. */ }
        }
    }
    public synchronized boolean requestFinish() {
        if (!inputReady || finished || finishRequested || cancelled || producerCompleted || observedClientPid < 1) return false;
        finishRequested = true; inputReady = false; cancelPendingInput();
        inputWorker.getQueue().clear(); notifyInputState();
        try {
            inputWorker.execute(() -> {
                releaseOnInputWorker();
                if (cancelled || finished || producerCompleted || inputFailed > 0) return;
                try {
                    byte[] request = new JSONObject().put("format", 1).put("session_id", session)
                            .put("client_pid", observedClientPid).put("action", "finish_interaction")
                            .toString().getBytes(StandardCharsets.UTF_8);
                    write(new File(state, "interaction-finish.json"), request);
                    recordLifecycle("interaction_finish_requested");
                } catch (Exception failure) { inputFailure("Could not write interaction Finish request"); }
            });
            return true;
        } catch (RejectedExecutionException closed) { inputFailure("Finish could not be queued"); return false; }
    }
    private void stopInputWorker() {
        inputReady = false; cancelPendingInput();
        inputWorker.getQueue().clear();
        if (!inputWorker.isShutdown()) {
            try { inputWorker.execute(this::releaseOnInputWorker); } catch (RejectedExecutionException ignored) {}
            inputWorker.shutdown();
            try { inputWorker.awaitTermination(2, TimeUnit.SECONDS); } catch (InterruptedException ignored) {}
            inputWorker.shutdownNow();
        }
        notifyInputState();
    }
    private void cancelPendingInput() {
        InteractiveRfbClient active = decoder;
        if (active != null) active.cancelPendingInput();
    }
    private synchronized void signalStop() {
        try { write(new File(state, "stop-request"), "stop\n".getBytes(StandardCharsets.UTF_8)); }
        catch (IOException e) { line("Could not write stop request: " + e.getClass().getSimpleName()); }
    }
    public synchronized void recordSurfaceCapture(Map<String, Object> record, byte[] png) {
        if (finished || session == null || !session.equals(record.get("session_id"))
                || clientWindowObservedUptime < 0 || clientWindowEndedUptime >= 0 || png == null
                || png.length < 33 || png.length > 4 * 1024 * 1024
                || !Boolean.TRUE.equals(record.get("pixel_copy_success"))
                || !Boolean.TRUE.equals(record.get("non_uniform"))) return;
        Object stamp = record.get("captured_elapsed_ms"), sequence = record.get("sequence");
        if (!(stamp instanceof Number) || !(sequence instanceof Number) || clientWindowFrameWatermark < 0
                || ((Number) sequence).doubleValue() != ((Number) sequence).longValue()
                || ((Number) sequence).longValue() <= clientWindowFrameWatermark) return;
        long captured = ((Number) stamp).longValue();
        if (((Number) stamp).doubleValue() != captured || captured < clientWindowObservedUptime
                || captured > SystemClock.uptimeMillis()) return;
        boolean startupSample = surfaceSamples.size() < 3 && (surfaceSamples.isEmpty()
                || captured - ((Number) surfaceSamples.get(surfaceSamples.size()-1).get("captured_elapsed_ms")).longValue() >= 1000);
        boolean afterInput = inputSent > 0 && captured >= lastInputUptime
                && ((Number) sequence).longValue() > lastInputFrameWatermark;
        boolean interactionSample = readyDeadlineUptimeMillis > 0 && (interactionSamples.isEmpty()
                || (afterInput && inputSent > lastCapturedInputCount) || (finishRequested && !finishCaptureRetained));
        if (!startupSample && !interactionSample) return;
        try {
            // Bind the retained bytes to the PixelCopy record. The source Surface
            // provides the nonuniform check; the PNG must be a bounded 800x600 image.
            byte[] signature = {(byte)137,80,78,71,13,10,26,10};
            for (int i=0;i<signature.length;i++) if (png[i] != signature[i]) return;
            if (png[12] != 'I' || png[13] != 'H' || png[14] != 'D' || png[15] != 'R'
                    || int32(png,16) != 800 || int32(png,20) != 600) return;
            String digest = hex(MessageDigest.getInstance("SHA-256").digest(png));
            if (!digest.equals(record.get("sha256"))) return;
            Map<String,Object> sample = new LinkedHashMap<>(record);
            sample.put("png_sha256", digest);
            sample.put("png_verified", true);
            sample.put("png_bytes", png.length);
            if (startupSample) {
                sample.put("archive_path", "android-surface/capture-" + (surfaceSamples.size()+1) + ".png");
                surfaceSamples.add(sample); surfacePngs.add(png.clone());
            }
            if (interactionSample) {
                Map<String,Object> interactive = new LinkedHashMap<>(sample);
                interactive.put("archive_path", "android-interaction/capture-" + (++interactionCaptureId) + ".png");
                interactive.put("input_events_sent", inputSent);
                interactive.put("last_input_uptime_ms", lastInputUptime);
                interactive.put("input_frame_watermark", lastInputFrameWatermark);
                interactive.put("post_input_frame_observed", afterInput);
                interactive.put("input_effect_verified", false);
                interactive.put("finish_requested", finishRequested);
                if (interactionSamples.size() == 8) {
                    // Keep the first available view plus the seven latest interaction views.
                    interactionSamples.remove(1); interactionPngs.remove(1);
                }
                interactionSamples.add(interactive); interactionPngs.add(png.clone());
                lastCapturedInputCount = inputSent;
                if (finishRequested) finishCaptureRetained = true;
            }
        } catch (Exception e) { line("Android capture was not retained: " + e.getClass().getSimpleName()); }
    }
    private static int int32(byte[] bytes, int start) {
        return ((bytes[start] & 255) << 24) | ((bytes[start+1] & 255) << 16)
                | ((bytes[start+2] & 255) << 8) | (bytes[start+3] & 255);
    }
    public synchronized void recordLifecycle(String event) {
        if (lifecycle.size() >= 512) return;
        Map<String, Object> entry = new LinkedHashMap<>();
        entry.put("event", clean(event)); entry.put("uptime_ms", SystemClock.uptimeMillis());
        if (session != null) entry.put("session_id", session);
        lifecycle.add(entry);
    }
    private void check() throws InterruptedIOException {
        if (cancelled || Thread.currentThread().isInterrupted()) throw new InterruptedIOException("Client operation stopped");
    }
    private void receiveFrames(Process process, File file) {
        long deadline = System.nanoTime() + TimeUnit.MINUTES.toNanos(26);
        try {
            while (!cancelled && !closingReceiver && process.isAlive()) {
                if (System.nanoTime() > deadline) throw new IOException("Timed out waiting for the private display socket");
                LocalSocket candidate = new LocalSocket();
                try {
                    candidate.connect(new LocalSocketAddress(file.getPath(), LocalSocketAddress.Namespace.FILESYSTEM));
                    socket = candidate;
                    // This socket is app-private and there is no TCP listener or network fallback.
                    decoder = new InteractiveRfbClient(candidate.getInputStream(), candidate.getOutputStream(), (pixels, width, height, sequence) -> {
                        if (closingReceiver || cancelled) return;
                        decodedFrames++; frameWidth = width; frameHeight = height;
                        listener.onFrame(pixels, width, height, sequence);
                    });
                    decoder.run(); return;
                } catch (IOException e) {
                    try { candidate.close(); } catch (IOException ignored) {}
                    if (socket == candidate) {
                        // Do not silently accept an early disconnect and certify a
                        // frozen framebuffer. The outer handler allows stdout to
                        // deliver the already-emitted completion before deciding.
                        throw e;
                    }
                    Thread.sleep(250);
                }
            }
        } catch (Exception e) {
            if (e instanceof EOFException && !closingReceiver && !cancelled && !producerCompleted) {
                long grace = System.nanoTime() + TimeUnit.SECONDS.toNanos(2);
                while (!closingReceiver && !cancelled && !producerCompleted && System.nanoTime() < grace) {
                    try { Thread.sleep(20); } catch (InterruptedException ignored) { break; }
                }
            }
            if (!closingReceiver && !cancelled && !producerCompleted)
                receiverFailure = e instanceof EOFException ? "Display socket closed before client observation completed" : message(e);
            else if (producerCompleted) recordLifecycle("display_socket_closed_after_producer: " + message(e));
        } finally { closeReceiver(); }
    }
    private void closeReceiver() {
        LocalSocket active = socket; socket = null;
        if (active != null) try { active.close(); } catch (IOException ignored) {}
        InteractiveRfbClient activeDecoder = decoder; decoder = null;
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
                        if ("client_startup_observed".equals(event.optString("type"))
                                && session.equals(event.optString("session_id")) && event.optLong("client_pid", -1) > 0) {
                            synchronized (this) {
                                clientWindowObservedUptime = SystemClock.uptimeMillis();
                                clientWindowEndedUptime = -1;
                                observedClientPid = event.getLong("client_pid");
                                clientWindowFrameWatermark = decodedFrames;
                                surfaceSamples.clear(); surfacePngs.clear();
                            }
                            InteractiveRfbClient activeDecoder = decoder;
                            if (activeDecoder != null) {
                                try { activeDecoder.requestFullUpdate(); }
                                catch (IOException e) { receiverFailure = "Cannot refresh the observed client window: " + message(e); }
                            }
                            stage("Client window observed", "The client window is ready for the interactive session.");
                        }
                        if ("stage".equals(event.optString("type")) && "actual_client_interaction".equals(event.optString("stage"))
                                && "passed".equals(event.optString("status"))) {
                            producerCompleted = true; inputReady = false; clientWindowEndedUptime = SystemClock.uptimeMillis();
                            releaseAllInputs(session); notifyInputState();
                        }
                        if ("client_interaction_finishing".equals(event.optString("type"))
                                && session.equals(event.optString("session_id")) && observedClientPid > 0
                                && observedClientPid == event.optLong("client_pid", -1)) {
                            inputReady = false; discardPendingInputs(session); notifyInputState();
                            stage("Finishing session", "Releasing input and saving the final view before cleanup.");
                        }
                        if ("client_interaction_ready".equals(event.optString("type"))
                                && session.equals(event.optString("session_id")) && observedClientPid > 0
                                && observedClientPid == event.optLong("client_pid", -1)
                                && event.optInt("minimum_observation_seconds", -1) == 30
                                && event.optInt("interaction_timeout_seconds", -1) == 180
                                && readyDeadlineUptimeMillis == 0 && !cancelled && !finished) {
                            readyDeadlineUptimeMillis = SystemClock.uptimeMillis() + 180000;
                            inputReady = true; recordLifecycle("interaction_ready"); notifyInputState();
                            stage("Client ready for input", "Interact with the menu, then press Finish. The session closes after three minutes.");
                        }
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
        if (manifest.getInt("format") != 1) throw new IOException("Unsupported client package");
        try (InputStream in = context.getAssets().open("runtime/client-manifest.json")) {
            clientManifest = new JSONObject(new String(read(in, MAX_JSON), StandardCharsets.UTF_8));
        }
        // The shared pinned input inventory retains its accepted startup scope;
        // the enclosing bundle and current guest result identify interaction.
        if (clientManifest.getInt("format") != 1 || !"actual_client_startup_guest".equals(clientManifest.getString("scope"))
                || !"actual_client_interaction_guest".equals(manifest.getJSONObject("client_bundle").optString("scope"))
                || !"client_interactive_diagnostic.py".equals(manifest.getJSONObject("client_bundle").optString("guest_script")))
            throw new IOException("The client package has the wrong scope");
    }
    private void validateInstalled() throws Exception {
        File ready = new File(generation, "ready.json");
        if (!ready.isFile() || !manifestHash.equals(json(ready, 16384).optString("manifest_sha256")))
            throw new IOException("Set up the client runtime first");
        JSONObject files = manifest.getJSONObject("files");
        for (Iterator<String> it = files.keys(); it.hasNext();) {
            String name = it.next();
            if (!name.matches("[A-Za-z0-9_.-]+")) throw new IOException("Unsafe runtime member");
            File file = new File(generation, "assets/" + name); JSONObject pin = files.getJSONObject(name);
            if (!file.isFile() || file.length() != pin.getLong("bytes") || !sha(file).equals(pin.getString("sha256")))
                throw new IOException("Runtime integrity check failed: " + name);
        }
        for (String name : new String[]{"client_interactive_diagnostic.py", "client-manifest.json", "client-runtime.zip", "client-caches.zip", "client-prerequisites.zip", "client-launcher.exe"})
            if (!files.has(name)) throw new IOException("Client runtime payload is missing: " + name);
    }
    private void removePreviousGuestOutput() throws IOException {
        for (String name : new String[]{"stop-request", "interaction-finish.json", "latest-report.json", "report.zip"}) {
            File file = new File(state, name);
            if (file.exists() && !file.delete()) throw new IOException("Cannot clear previous guest output: " + name);
        }
    }

    private boolean guestAccepted(JSONObject report) throws Exception {
        if (!(report.optBoolean("passed") && "passed".equals(report.optString("status"))
                && session.equals(report.optString("session_id"))
                && "actual_client_interaction_guest".equals(report.optString("scope"))
                && "actual_client_interaction".equals(report.optString("diagnostic_mode"))
                && "android".equals(report.optString("execution_platform_requested"))
                && report.optJSONArray("failures") != null && report.getJSONArray("failures").length() == 0
                && Boolean.FALSE.equals(report.opt("postgres_started")) && Boolean.FALSE.equals(report.opt("server_started"))
                && Boolean.FALSE.equals(report.opt("android_surface_validated"))
                && Boolean.FALSE.equals(report.opt("game_validated")) && Boolean.FALSE.equals(report.opt("gameplay_validated"))
                && Boolean.FALSE.equals(report.opt("menu_visual_validated"))
                && Boolean.FALSE.equals(report.opt("hardware_acceleration_validated"))
                && ClientAcceptance.interactionCompleted(jsonValue(report))
                && report.optBoolean("presentation_socket_removed")
                && ClientAcceptance.cleanupSafe(jsonValue(report)))) return false;
        for (String key : new String[]{"client_process_started", "renderer_initialized", "all_data_loaded",
                "client_main_loop_reached", "client_window_observed", "startup_observed"})
            if (!Boolean.TRUE.equals(report.opt(key))) return false;
        double observed = report.optDouble("observation_seconds", -1);
        double elapsed = report.optDouble("startup_elapsed_seconds", -1);
        if (!Double.isFinite(observed) || observed < 30 || observed > 190
                || !Double.isFinite(elapsed) || elapsed < 0 || elapsed > 900) return false;
        JSONObject launch = report.optJSONObject("client_launch");
        if (launch == null || !session.equals(launch.optString("session_id")) || observedClientPid < 1
                || observedClientPid != launch.optLong("pid", -1)) return false;
        JSONArray windows = report.optJSONArray("client_windows");
        if (windows == null || windows.length() < 1 || windows.length() > 512) return false;
        boolean actualWindow = false;
        for (int i=0;i<windows.length();i++) {
            JSONObject window = windows.getJSONObject(i);
            if (("City of Heroes : PID: " + observedClientPid).equals(window.optString("title"))
                    && Boolean.TRUE.equals(window.opt("mapped")) && window.optInt("width") >= 320
                    && window.optInt("height") >= 240) actualWindow = true;
        }
        if (!actualWindow) return false;
        JSONObject hashes = report.optJSONObject("asset_sha256"), pins = manifest.getJSONObject("files");
        JSONObject clientPins = clientManifest.getJSONObject("files");
        if (hashes == null || hashes.length() != clientPins.length()) return false;
        for (Iterator<String> it = clientPins.keys(); it.hasNext();) {
            String name = it.next();
            String digest = clientPins.getJSONObject(name).getString("sha256");
            if (!pins.has(name) || !digest.equals(hashes.optString(name))
                    || !pins.getJSONObject(name).getString("sha256").equals(digest)) return false;
        }
        JSONObject identity = report.optJSONObject("import_identity");
        if (identity == null || imported == null || !imported.generation.equals(identity.optString("generation"))
                || identity.optLong("file_count", -1) != imported.count || identity.optLong("total_bytes", -1) != imported.bytes)
            return false;
        File receipt = new File(imported.dataDirectory.getParentFile(), "complete.properties");
        byte[] receiptBytes = read(receipt, 4096); Properties properties = new Properties();
        properties.load(new ByteArrayInputStream(receiptBytes));
        if (!hex(MessageDigest.getInstance("SHA-256").digest(receiptBytes)).equals(identity.optString("receipt_sha256"))
                || !properties.getProperty("contract.sha256", "missing").equals(identity.optString("contract_sha256"))) return false;
        JSONObject worktree = report.optJSONObject("client_worktree");
        if (worktree == null || !"/game-import/data".equals(worktree.optString("source_data"))
                || !Boolean.TRUE.equals(worktree.opt("imported_inputs_readonly"))
                || !Boolean.TRUE.equals(worktree.opt("imported_input_bytes_unchanged"))
                || !Boolean.TRUE.equals(worktree.opt("imported_metadata_normalized"))
                || worktree.optLong("normalized_mtime_epoch", -1) != 1767225600L
                || !pins.getJSONObject("client-caches.zip").getString("sha256").equals(worktree.optString("cache_archive_sha256"))
                || !pins.getJSONObject("client-prerequisites.zip").getString("sha256").equals(worktree.optString("prerequisites_archive_sha256"))
                || worktree.optInt("prepared_prerequisite_files", -1) != 3
                || worktree.optLong("prepared_prerequisite_bytes", -1) != 54948L
                || worktree.optLong("input_files", -1) != imported.count
                || worktree.optLong("input_bytes", -1) != imported.bytes) return false;
        String[] requiredStages = {"client_inputs", "client_private_data", "presentation_display", "wine_initialization",
                "win32_runtime_dll", "actual_client_startup", "actual_client_interaction"};
        JSONArray stages = report.optJSONArray("stages");
        if (stages == null || stages.length() != requiredStages.length) return false;
        for (int i=0;i<requiredStages.length;i++) {
            JSONObject stage = stages.getJSONObject(i);
            if (!requiredStages[i].equals(stage.optString("stage")) || !"passed".equals(stage.optString("status"))) return false;
        }
        JSONObject inputs = stages.getJSONObject(0), startup = stages.getJSONObject(6);
        if (!imported.sourceCommit.equals(inputs.optString("source_commit"))
                || !imported.dataCommit.equals(inputs.optString("data_commit"))
                || !Boolean.TRUE.equals(startup.opt("bounded_live_observation"))) return false;
        JSONArray screenshots = report.optJSONArray("screenshots");
        if (screenshots == null || screenshots.length() != 3) return false;
        Set<String> actualCaptures = new HashSet<>();
        for (int i=0;i<screenshots.length();i++) {
            JSONObject capture = screenshots.getJSONObject(i);
            if (!session.equals(capture.optString("session_id")) || capture.optInt("width") != 800
                    || capture.optInt("height") != 600 || !capture.optString("sha256").matches("[0-9a-f]{64}")) return false;
            if (capture.optInt("distinct_colors_capped") >= 8) actualCaptures.add(capture.optString("path"));
        }
        return actualCaptures.contains("client-startup.ppm") && actualCaptures.contains("client-observed.ppm");
    }
    private boolean surfaceAccepted(JSONObject report) {
        synchronized (this) {
            return decodedFrames >= 1 && ClientAcceptance.surfaceAccepted(surfaceSamples, session,
                    startedUptime, endedUptime, clientWindowObservedUptime, clientWindowEndedUptime, clientWindowFrameWatermark);
        }
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
                    .put("passed", passed).put("android_surface_validated", passed).put("interaction_session_completed", passed)
                    .put("menu_visual_validated", false).put("cleanup_verified", cleanup)
                    .put("cleanup_blocked", isCleanupBlocked()).put("cancelled", cancelled)
                    .put("gameplay_validated", false).put("game_rendering_validated", false)
                    .put("hardware_acceleration_validated", false).put("controller_input_validated", false)
                    .put("input_effect_verified", false).put("input_events_sent", inputSent).put("input_events_failed", inputFailed)
                    .put("input_transport_observed", inputSent > 0 && inputFailed == 0)
                    .put("input_worker_stopped", inputWorker.isTerminated())
                    .put("finish_requested", finishRequested).put("interaction_deadline_uptime_ms", readyDeadlineUptimeMillis)
                    .put("scope", "Bounded interactive City of Heroes menu session through private RFB input and Android PixelCopy; input effects require manual review")
                    .put("decoded_frame_count", decodedFrames)
                    .put("client_window_observed_uptime_ms", clientWindowObservedUptime)
                    .put("client_window_frame_watermark", clientWindowFrameWatermark)
                    .put("client_window_ended_uptime_ms", clientWindowEndedUptime)
                    .put("source_width", frameWidth).put("source_height", frameHeight)
                    .put("guest", guest);
            if (error != null) wrapper.put("app_error", error);
            if (receiverFailure != null) wrapper.put("receiver_error", receiverFailure);
            synchronized (this) {
                wrapper.put("surface_captures", new JSONArray(surfaceSamples));
                wrapper.put("interaction_captures", new JSONArray(interactionSamples));
                wrapper.put("lifecycle", new JSONArray(lifecycle));
            }
            String status = isCleanupBlocked() ? "cleanup_failed" : cancelled ? "cancelled" : passed ? "passed"
                    : ("setup".equals(operation) || "import".equals(operation)) ? guest.optString("status", "failed")
                    : guest.optBoolean("passed") ? "client_incomplete" : "failed";
            wrapper.put("status", status);
            File target = new File(operationDir, "coh-client-test-" + runId + ".zip");
            File part = new File(operationDir, "support.zip.part");
            try (ZipOutputStream out = new ZipOutputStream(new FileOutputStream(part))) {
                if (imported != null) wrapper.put("import", new JSONObject().put("generation", imported.generation)
                        .put("source_commit", imported.sourceCommit).put("data_commit", imported.dataCommit)
                        .put("repository_commit", imported.repositoryCommit).put("files", imported.count).put("bytes", imported.bytes));
                zipText(out, "android-client-report.json", wrapper.toString(2));
                synchronized (this) { for (int i=0;i<surfacePngs.size();i++)
                    zipBytes(out, "android-surface/capture-" + (i+1) + ".png", surfacePngs.get(i)); }
                synchronized (this) { for (int i=0;i<interactionPngs.size();i++)
                    zipBytes(out, (String) interactionSamples.get(i).get("archive_path"), interactionPngs.get(i)); }
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
                try (InputStream in = context.getAssets().open("atlas/atlas-import.properties")) {
                    zipBytes(out, "atlas-import.properties", read(in, 16384));
                }
                if ("client_interaction".equals(operation) && runLaunched) {
                    File file = new File(state, "report.zip");
                    if (file.isFile()) zipFile(out, "guest-report.zip", file, MAX_GUEST_ZIP);
                }
            }
            Files.move(part.toPath(), target.toPath(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
            write(new File(work, "latest-report.txt"), target.getCanonicalPath().getBytes(StandardCharsets.UTF_8));
            latestReport = target;
        } catch (Exception e) { throw new IOException("Could not save a fresh client support report", e); }
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
    private static void zipFile(ZipOutputStream out, String name, File file, long limit) throws IOException {
        long expected = file.length(), copied = 0;
        if (expected > limit) throw new IOException("Guest support archive exceeds size limit");
        out.putNextEntry(new ZipEntry(name));
        try (InputStream in = new FileInputStream(file)) {
            byte[] buffer = new byte[65536]; int count;
            while ((count = in.read(buffer)) != -1) {
                if (copied + count > limit) throw new IOException("Guest support archive exceeds size limit");
                out.write(buffer, 0, count); copied += count;
            }
        }
        if (copied != expected) throw new IOException("Guest support archive changed during export");
        out.closeEntry();
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
