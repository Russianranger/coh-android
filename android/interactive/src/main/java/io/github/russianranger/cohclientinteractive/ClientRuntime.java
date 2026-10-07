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

/** Runs the pinned CoH client with a persistent local PostgreSQL and DbServer profile. */
public final class ClientRuntime {
    public interface Listener {
        void onStage(String stage, String detail);
        void onLog(String line);
        void onFrame(int[] argb, int width, int height, long sequence);
        void onInputState(boolean ready, boolean finishing, boolean characterSaved, boolean canReturnGround, boolean canSaveLogout, long sent, long failed, long deadline, String phase, long saveDeadline, long movementDeadline);
    }
    public static final class Result {
        public final boolean passed;
        public final File report;
        public final String summary;
        Result(boolean passed, File report, String summary) {
            this.passed = passed; this.report = report; this.summary = summary;
        }
    }

    /** A missing app-private profile is different from an interrupted or saved profile. */
    public enum ProfileState { ABSENT, READY, PRESERVE }

    private static final long MAX_JSON = 2L * 1024 * 1024, MAX_LOG = 1024 * 1024;
    private static final long MAX_GUEST_ZIP = 260L * 1024 * 1024;
    private static final long MAX_WORLD_IDENTITY = 8L * 1024 * 1024;
    private static final String PROCESS_INSTANCE = UUID.randomUUID().toString();
    private static final String BLOCK_MESSAGE = "Runtime cleanup needs attention. Force-stop COH Character Reopen in Android settings, then reopen it.";
    private static boolean guardInitialized, blocked;
    private static boolean operationActive;
    private static Object storageOwner;
    private final Context context;
    private final Listener listener;
    private final File home, work, state;
    private final StringBuilder log = new StringBuilder();
    private final List<Map<String, Object>> surfaceSamples = new ArrayList<>();
    private final List<byte[]> surfacePngs = new ArrayList<>();
    private final List<Map<String, Object>> loginSamples = new ArrayList<>();
    private final List<byte[]> loginPngs = new ArrayList<>();
    private volatile long loginObservedUptime = -1, loginFrameWatermark = -1;
    private final List<Map<String, Object>> connectedSamples = new ArrayList<>();
    private final List<byte[]> connectedPngs = new ArrayList<>();
    private volatile long connectedObservedUptime = -1, connectedFrameWatermark = -1;
    private volatile boolean connectedCapturedReady, relocationCapturedReady, stuckRequested, reopen;
    private final List<Map<String, Object>> relocationSamples = new ArrayList<>();
    private final List<byte[]> relocationPngs = new ArrayList<>();
    private volatile long relocatedObservedUptime = -1, relocatedFrameWatermark = -1;
    private volatile JSONObject characterRelocatedEvent;
    private final List<Map<String, Object>> characterSamples = new ArrayList<>();
    private final List<byte[]> characterPngs = new ArrayList<>();
    private volatile long characterObservedUptime = -1, characterFrameWatermark = -1;
    private volatile JSONObject characterSavedEvent, characterConnectedEvent;
    private volatile boolean saveLogoutRequested;
    private volatile boolean characterSavedReady;
    private final List<Map<String, Object>> interactionSamples = new ArrayList<>();
    private final List<byte[]> interactionPngs = new ArrayList<>();
    private final ContactCaptureWindow contactCapture = new ContactCaptureWindow();
    private final List<Map<String,Object>> contactRequests = new ArrayList<>();
    private final List<Map<String,Object>> contactSamples = new ArrayList<>();
    private final List<byte[]> contactPngs = new ArrayList<>();
    private volatile JSONObject taskAcceptedEvent, taskCompletedEvent, taskCompletionReceipt;
    private volatile boolean taskCompletionRequested;
    private volatile boolean taskContactRequested;
    private volatile JSONObject taskContactReceipt;
    private final ContactCaptureWindow taskAcceptedCapture = new ContactCaptureWindow();
    private final ContactCaptureWindow taskCompletedCapture = new ContactCaptureWindow();
    private final List<Map<String,Object>> taskCaptureRequests = new ArrayList<>();
    private final List<Map<String,Object>> taskSamples = new ArrayList<>();
    private final List<byte[]> taskPngs = new ArrayList<>();
    private final ThreadPoolExecutor inputWorker = new ThreadPoolExecutor(1, 1, 0L, TimeUnit.MILLISECONDS,
            new ArrayBlockingQueue<Runnable>(128), runnable -> new Thread(runnable, "coh-interactive-input"));
    private volatile boolean inputReady, finishRequested;
    private volatile boolean performanceCommandPending;
    private long performanceCommandGeneration;
    private volatile long inputSent, inputFailed, readyDeadlineUptimeMillis;
    private final ClientSessionBudget sessionBudget = new ClientSessionBudget();
    private final List<Map<String,Object>> sessionBudgetEvents = new ArrayList<>();
    private volatile long launcherBudgetStartedUptime = -1, relocationSentUtcMillis;
    private volatile boolean deadlineInputSuppressed, interactionReadyObserved;
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
    private String graphicsProfileRequested="standard";
    private File generation, operationDir;
    private boolean operationOwned;
    private static Object setupFinalizationOwner;
    private Object setupReservation;
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
    public static boolean performanceGraphicsEnabled(Context context) {
        return context.getSharedPreferences("client-launch-options", Context.MODE_PRIVATE)
                .getBoolean("performance-graphics", true);
    }
    public static void setPerformanceGraphicsEnabled(Context context, boolean enabled) {
        context.getSharedPreferences("client-launch-options", Context.MODE_PRIVATE)
                .edit().putBoolean("performance-graphics", enabled).apply();
    }
    public boolean isCleanupBlocked() { return cleanupBlocked(context); }
    /** Shared ownership keeps storage work and report export away from a live guest. */
    public static synchronized Object acquireStorage(Context context) throws IOException {
        if (cleanupBlocked(context)) throw new IOException(BLOCK_MESSAGE);
        return acquireIdleStorage();
    }
    public static synchronized Object acquireReportExport(Context context) throws IOException {
        // A failed test's report remains exportable while destructive cleanup is blocked.
        return acquireIdleStorage();
    }
    private static Object acquireIdleStorage() throws IOException {
        if (operationActive || setupFinalizationOwner != null) throw new IOException("Wait for the current operation to finish");
        Object owner = new Object(); storageOwner = owner; operationActive = true;
        return owner;
    }
    public static synchronized void releaseStorage(Object owner) {
        if (owner != null && owner == storageOwner) { storageOwner = null; operationActive = false; }
    }
    public static synchronized boolean operationInProgress() { return operationActive || setupFinalizationOwner != null; }
    static synchronized Object acquireSetupReservation(Context context) throws IOException {
        if (cleanupBlocked(context)) throw new IOException(BLOCK_MESSAGE);
        if (operationActive || setupFinalizationOwner != null) throw new IOException("Wait for the current operation to finish");
        setupFinalizationOwner = new Object();
        return setupFinalizationOwner;
    }
    static synchronized boolean setupFinalizationInProgress() { return setupFinalizationOwner != null; }
    static synchronized boolean ownsSetupReservation(Object owner) { return owner != null && owner == setupFinalizationOwner; }
    static synchronized void releaseSetupReservation(Object owner) {
        if (owner != null && owner == setupFinalizationOwner) setupFinalizationOwner = null;
    }
    void attachSetupReservation(Object owner) {
        synchronized (ClientRuntime.class) {
            if (owner == null || owner != setupFinalizationOwner || operationOwned)
                throw new IllegalStateException("Runtime setup reservation changed");
            setupReservation = owner;
        }
    }
    /** Read at most two small identity files; never walk imported assets or a database. */
    public static ProfileState characterProfileState(Context context) {
        try { return inspectCharacterProfile(new StorageFiles(context.getApplicationContext().getFilesDir())); }
        catch (Exception unreadable) { return ProfileState.PRESERVE; }
    }
    static ProfileState inspectCharacterProfile(StorageAudit.Fs files) throws IOException {
        String path = "";
        for (String component : new String[]{"client", "state", "diagnostic", "android-local-login"}) {
            path = path.isEmpty() ? component : path + "/" + component;
            StorageAudit.Stat entry = files.stat(path);
            if (entry == null) return ProfileState.ABSENT;
            if (entry.kind != StorageAudit.Kind.DIRECTORY) return ProfileState.PRESERVE;
        }
        String profile = "client/state/diagnostic/android-local-login";
        if (!profileEntry(files, profile + "/profile.json", StorageAudit.Kind.FILE, 4096)
                || !profileEntry(files, profile + "/pgdata", StorageAudit.Kind.DIRECTORY, 0)
                || !profileEntry(files, profile + "/pgdata/PG_VERSION", StorageAudit.Kind.FILE, 32)
                || !profileEntry(files, profile + "/credentials.json", StorageAudit.Kind.FILE, 4096))
            return ProfileState.PRESERVE;
        Map<String,Object> marker = files.json(files.read(profile + "/profile.json", 4096));
        Map<String,Object> identity = new LinkedHashMap<>();
        identity.put("format", 1); identity.put("purpose", "persistent_local_login");
        identity.put("profile", "android-local-login"); identity.put("database", "coh_local_android");
        identity.put("source_commit", "0b75ade0c801735e10c5798f641948a45cc50488");
        identity.put("data_commit", "d51533ec8e6a9cf726b9214968077a05fdcf19f3");
        identity.put("package_manifest_sha256", "95f62cc81b0743c13652e55aee01aed6871fc96d70a84b8dfd62fb8a0d9fe0d6");
        identity.put("schema_manifest_sha256", "b89136892e69ceb39db640613d3f8a34abf2ef8e75e947f4034728b935938b92");
        identity.put("initialized", Boolean.TRUE);
        if (!identity.equals(marker)) return ProfileState.PRESERVE;
        Map<String,Object> credentials = files.json(files.read(profile + "/credentials.json", 4096));
        if (!credentials.keySet().equals(new HashSet<>(Arrays.asList("cohdiag_admin", "cohtest"))))
            return ProfileState.PRESERVE;
        for (Object credential : credentials.values())
            if (!(credential instanceof String) || !((String)credential).matches("[0-9a-f]{64}"))
                return ProfileState.PRESERVE;
        return ProfileState.READY;
    }
    private static boolean profileEntry(StorageAudit.Fs files, String path, StorageAudit.Kind kind, int bound) throws IOException {
        StorageAudit.Stat entry = files.stat(path);
        return entry != null && entry.kind == kind && (kind == StorageAudit.Kind.DIRECTORY
                || entry.links == 1 && entry.size > 0 && entry.size <= bound);
    }
    public static String profileRecoveryMessage(ProfileState profile) {
        if (profile == ProfileState.ABSENT)
            return "No saved character profile is present. After a fresh install, use Create fresh THORHERO once, then save normally. An earlier character requires an external database backup.";
        if (profile == ProfileState.READY)
            return "The existing character database is present. Reopen THORHERO to continue the task check.";
        return "Existing character data is incomplete or unreadable. It has been preserved; export the report. Fresh creation is unavailable while any profile data remains.";
    }
    private void requireCharacterProfile(boolean reopening) throws IOException {
        ProfileState profile = characterProfileState(context);
        if (reopening && profile != ProfileState.READY)
            throw new IOException(profileRecoveryMessage(profile));
        if (!reopening && profile != ProfileState.ABSENT)
            throw new IOException("Fresh creation was refused because character profile data already exists. " + profileRecoveryMessage(profile));
    }
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
            if (operationActive || (setupFinalizationOwner != null
                    && (setupReservation != setupFinalizationOwner || !"setup".equals(kind))))
                throw new IOException("A client operation is already running");
            operationActive = true;
            operationOwned = true;
        }
        operation = kind; session = selectedSession;
        runId = System.currentTimeMillis() + "-" + UUID.randomUUID().toString().replace("-", "").substring(0, 12);
        operationDir = new File(work, "reports/" + runId); operationDir.mkdirs();
        startedUptime = SystemClock.uptimeMillis();
        latestReport = null;
        File pointer = new File(work, "latest-report.txt");
        if (pointer.exists() && !pointer.delete()) {
            synchronized (ClientRuntime.class) { operationActive = false; operationOwned = false; }
            throw new IOException("Cannot invalidate the previous support report");
        }
        recordLifecycle("operation_" + kind + "_started");
    }
    private void endOperation() {
        try { finished = true; inputReady = false; inputWorker.shutdownNow(); }
        finally { synchronized (ClientRuntime.class) {
            if (operationOwned) { operationActive = false; operationOwned = false; }
        } }
    }
    public File getLatestReport() { return latestReport; }

    public Result setup() throws Exception {
        boolean ready = false;
        try {
            // The ownership boundary includes begin/report allocation and every
            // evidence path: even a setup heap failure must release this owner.
            begin("setup", null);
            JSONObject report = new JSONObject();
            boolean heapFailed = false;
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
            } catch (OutOfMemoryError failure) {
                heapFailed = true;
                throw failure;
            } finally {
                // The service releases its reserve and writes compact recovery
                // evidence. Avoid masking the original heap failure with export.
                if (!heapFailed) {
                DiagnosticRuntime completedInstaller = installer;
                if (completedInstaller != null) {
                    try {
                        JSONObject receipt = completedInstaller.getSetupReceipt();
                        if (receipt != null) report.put("runtime_setup", receipt);
                    } catch (Exception telemetryFailure) {
                        report.put("runtime_setup_recording_error", telemetryFailure.getClass().getSimpleName());
                    }
                }
                installer = null;
                synchronized (this) {
                    finished = true;
                    if (cancelled) { ready = false; report.put("status", "cancelled").put("passed", false); }
                }
                endedUptime = SystemClock.uptimeMillis();
                publish(report, false, false);
                }
            }
            return new Result(ready, latestReport, ready ? "Runtime ready. Import the pinned Atlas assets if needed. " + profileRecoveryMessage(characterProfileState(context))
                    : cancelled ? "Runtime setup stopped. Export the latest report." : "Runtime setup failed: " + error);
        } finally {
            installer = null;
            endOperation();
        }
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
        return new Result(ready, latestReport, ready ? "Verified game assets are ready. " + profileRecoveryMessage(characterProfileState(context))
                : cancelled ? "Asset import stopped; the previous verified content is preserved."
                : "Asset import failed: " + error);
    }

    public Result run(String selectedSession) throws Exception {
        return runCharacter(selectedSession, true);
    }

    /** Explicit first-install creation; never a fallback for an existing or partial database. */
    public Result runCreation(String selectedSession) throws Exception {
        return runFreshCreation(selectedSession);
    }
    public Result runFreshCreation(String selectedSession) throws Exception {
        return runCharacter(selectedSession, false);
    }

    private Result runCharacter(String selectedSession, boolean reopening) throws Exception {
        reopen = reopening;
        if (selectedSession == null || !selectedSession.matches("[0-9a-f]{32}")) throw new IOException("Invalid client session identity");
        begin(reopen ? "character_reopen" : "character_creation", selectedSession);
        graphicsProfileRequested=performanceGraphicsEnabled(context)?"performance":"standard";
        JSONObject report = new JSONObject();
        Thread output = null, receiver = null;
        boolean launched = false, passed = false, cleanup = false, guestPassed = false;
        try {
            // The operation lock is held. Detect a missing/partial profile before
            // runtime hashing, thin worktree staging, or any Wine/SQL process.
            requireCharacterProfile(reopen);
            loadManifest(); check(); validateInstalled();
            imported = importer().inspect();
            if (imported == null) throw new IOException("Import the pinned Atlas assets before starting the client");
            state.mkdirs();
            removePreviousGuestOutput();
            File tmp = new File(operationDir, "tmp"); tmp.mkdirs();
            File guestHosts = new File(operationDir, "hosts");
            write(guestHosts, localHosts(android.system.Os.uname().nodename).getBytes(StandardCharsets.US_ASCII));
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
                    "-b", guestHosts.getPath() + ":/etc/hosts",
                    "-w", "/state", "/usr/bin/env", "-i", "HOME=/state", "USER=coh", "LOGNAME=coh",
                    "PATH=/opt/coh/pgsql/bin:/usr/local/bin:/usr/bin:/bin", "LANG=C.UTF-8", "TZ=UTC", "TMPDIR=/tmp",
                    "PYTHONUNBUFFERED=1", "PYTHONDONTWRITEBYTECODE=1",
                    "COH_CLIENT_GRAPHICS_PROFILE="+graphicsProfileRequested,
                    "/usr/bin/python3", "/opt/coh/" + (reopen ? "character_reopen_diagnostic.py" : "character_creation_diagnostic.py"), "--state", "/state", "--assets", "/opt/coh",
                    "--pg-bin", "/opt/coh/pgsql/bin", "--wine", "/opt/wine/bin/wine", "--wineserver", "/opt/wine/bin/wineserver",
                    "--execution-platform", "android", "--session-id", session, "--profile", "android-local-login",
                    "--game-data", "/game-import/data", "--socket-dir", "/presentation-socket",
                    "--startup-timeout-seconds", "900", "--observation-seconds", "30", "--interaction-seconds", "1200", "--timeout-seconds", "5400"));
            if (reopen && Boolean.TRUE.equals(manifest.opt("startup_only_reopen"))) command.add("--startup-only");
            ProcessBuilder builder = new ProcessBuilder(command).redirectErrorStream(true);
            builder.environment().put("PROOT_LOADER", loader.getPath());
            builder.environment().put("PROOT_TMP_DIR", prootTmp.getPath());
            builder.environment().put("PROOT_NO_SECCOMP", "1");
            write(guard(context), new JSONObject().put("status", "running").put("process_instance", PROCESS_INSTANCE)
                    .put("session_id", session).put("operation_id", runId).toString().getBytes(StandardCharsets.UTF_8));
            stage("Starting City of Heroes", "Starting the persistent local database, DbServer and Atlas, then opening the graphical client.");
            check(); child = builder.start(); launched = true; runLaunched = true;
            Process process = child;
            output = new Thread(() -> captureOutput(process), "coh-client-output"); output.start();
            receiver = new Thread(() -> receiveFrames(process, socketFile), "coh-client-frames"); receiver.start();
            long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(5500);
            while (!process.waitFor(200, TimeUnit.MILLISECONDS)) {
                check();
                if (receiverFailure != null) throw new IOException("Local display connection failed: " + receiverFailure);
                if (System.nanoTime() > deadline) throw new IOException("Character session exceeded its 5500 second runtime limit");
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
                        && inputFailed == 0 && surfaceAccepted(report) && loginSurfaceAccepted() && characterSurfaceAccepted(report);
                if (inputFailed > 0 && error == null) error = "Input transport failed; review the exported report.";
                if (guestPassed && !passed && error == null) error = taskGateRequired()
                        ? "Task gate incomplete: matching native and SQL task completion, accepted/completed task views, ordinary save evidence and fresh Android save captures are required."
                        : "Character save incomplete: matching committed SQL evidence and three fresh Android captures after the save event are required.";
                publish(report, passed, cleanup);
            } finally {
                child = null; endOperation();
                if (interrupted) Thread.currentThread().interrupt();
            }
        }
        String label = taskGateRequired() ? "Task save" : reopen ? "Character reopen" : "Character creation";
        String summary = passed ? (taskGateRequired()
                ? "One manually accepted task completed through the stock command and remained committed after ordinary logout, with matching native/SQL evidence, accepted/completed Android views and verified cleanup. Review both task views; combat, mission maps and reward turn-in remain separate."
                : reopen
                ? "The existing THORHERO was reopened and saved with its identity, powers and costume preserved, fresh Android captures after connection and save, and verified cleanup. Review the Atlas view; rendering and gameplay require separate visual validation."
                : "THORHERO was saved to the local database, with matching current-session SQL evidence, fresh Android captures and verified cleanup. World rendering, movement and gameplay still need validation.")
                : isCleanupBlocked() ? BLOCK_MESSAGE : cancelled ? label + " check stopped. Export the latest report."
                : guestPassed ? label + " check incomplete. Export the latest report."
                : label + " check failed. Export the latest report.";
        stage(passed ? label + " check complete" : isCleanupBlocked() ? "Cleanup needs attention" : cancelled ? label + " check stopped"
                : guestPassed ? label + " check incomplete" : label + " check failed", summary);
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
        return queueInput(selectedSession, (active, epoch) -> active.sendPointer(x, y, mask, epoch), true);
    }
    public boolean sendKey(String selectedSession, int keysym, boolean down) {
        if (keysym <= 0) return false;
        return queueInput(selectedSession, (active, epoch) -> active.sendKey(keysym, down, epoch), down);
    }
    /** Ordinary paired Enter remains available in the owned login input phase. */
    public synchronized boolean requestEnter(String selectedSession) {
        return queueInput(selectedSession, (active, epoch) -> {
            active.sendEnter(epoch);
            recordLifecycle("sidebar_enter_submitted sent_utc_ms=" + System.currentTimeMillis());
        }, true);
    }
    public boolean isPerformanceCommandPending() { return performanceCommandPending; }
    private boolean performanceCommandInputAllowed() {
        return session != null && !session.isEmpty() && reopen && inputReady && !finishRequested && !finished && !cancelled && !producerCompleted
                && connectedCapturedReady && characterConnectedEvent != null && observedClientPid > 0
                && !saveLogoutRequested && characterSavedEvent == null
                && (!stuckRequested || relocationCapturedReady)
                && !(taskContactRequested && taskContactReceipt == null)
                && !(taskCompletionRequested && taskCompletionReceipt == null)
                && sessionBudget.canMove(SystemClock.uptimeMillis());
    }
    public synchronized boolean canSendPerformanceCommand() {
        return !performanceCommandPending && decoder != null && !inputWorker.isShutdown()
                && performanceCommandInputAllowed();
    }
    public synchronized boolean requestPerformanceCommand(ClientInput.PerformanceCommand command) {
        if (command == null || !canSendPerformanceCommand()) return false;
        final String selectedSession = session;
        final long selectedPid = observedClientPid;
        final long token = ++performanceCommandGeneration;
        performanceCommandPending = true;
        boolean queued = queueInput(selectedSession, (active, epoch) -> {
            synchronized (ClientRuntime.this) {
                if (token != performanceCommandGeneration || !performanceCommandPending || !selectedSession.equals(session)
                        || observedClientPid != selectedPid || !performanceCommandInputAllowed())
                    throw new InteractiveRfbClient.InputCancelledException();
            }
            recordLifecycle("performance_command_dispatch name=" + command.safeName
                    + " dispatch_utc_ms=" + System.currentTimeMillis());
            active.sendPerformanceCommand(command.safeName, epoch);
            recordLifecycle("performance_command_submitted name=" + command.safeName
                    + " submitted_utc_ms=" + System.currentTimeMillis() + " native_effect_verified=false");
            stage("FPS command sent", "Check the in-game FPS display. The selected value is a cap.");
        }, true, token);
        if (!queued) { performanceCommandPending = false; return false; }
        recordLifecycle("performance_command_queued name=" + command.safeName);
        notifyInputState();
        return true;
    }
    private synchronized void completePerformanceCommand(long token) {
        if (token != 0 && token == performanceCommandGeneration && performanceCommandPending) {
            performanceCommandPending = false;
            notifyInputState();
        }
    }
    /** Bounds manual contact-view evidence; it never proves a native dialog opened. */
    private static final class ContactCaptureWindow {
        static final int MAX_REQUESTS=3, FRAMES_PER_REQUEST=3;
        static final long MAX_AGE_MS=120000;
        private String session;
        private long pid, requested, deadline, watermark, lastCapture=-1, lastSequence=-1;
        private int batch, count;
        boolean canRequest(long now) {
            return now>=0 && now>=requested && (lastCapture<0 || now>=lastCapture) && batch<MAX_REQUESTS
                    && (batch==0 || count==FRAMES_PER_REQUEST || now>deadline);
        }
        boolean request(String selectedSession,long selectedPid,long characterId,long now,long sequence) {
            if(selectedSession==null || !selectedSession.matches("[0-9a-f]{32}") || selectedPid<=0
                    || selectedPid>4294967295L || characterId!=1 || now>Long.MAX_VALUE-MAX_AGE_MS
                    || sequence<0 || !canRequest(now))return false;
            session=selectedSession;pid=selectedPid;requested=now;deadline=now+MAX_AGE_MS;
            watermark=sequence;lastCapture=lastSequence=-1;count=0;batch++;
            return true;
        }
        boolean accepts(String selectedSession,long selectedPid,long characterId,long captured,long sequence) {
            return batch>0 && count<FRAMES_PER_REQUEST && session.equals(selectedSession) && pid==selectedPid
                    && characterId==1 && captured>requested && captured<=deadline && sequence>watermark
                    && sequence>lastSequence && (lastCapture<0 || captured-lastCapture>=1000);
        }
        boolean accept(String selectedSession,long selectedPid,long characterId,long captured,long sequence) {
            if(!accepts(selectedSession,selectedPid,characterId,captured,sequence))return false;
            lastCapture=captured;lastSequence=sequence;count++;return true;
        }
        int batch(){return batch;}
        int count(){return count;}
    }
    public synchronized boolean canCaptureContact() {
        return !performanceCommandPending && reopen && inputReady && !finished && !finishRequested && !cancelled && !producerCompleted
                && connectedCapturedReady && characterConnectedEvent!=null && !saveLogoutRequested
                && characterSavedEvent==null && (!stuckRequested || relocationCapturedReady)
                && sessionBudget.canMove(SystemClock.uptimeMillis())
                && contactCapture.canRequest(SystemClock.uptimeMillis());
    }
    public synchronized boolean requestContactCapture() {
        if(!canCaptureContact())return false;
        long now=SystemClock.uptimeMillis();
        if(!contactCapture.request(session,observedClientPid,characterConnectedEvent.optLong("character_id",-1),now,decodedFrames))return false;
        Map<String,Object> request=new LinkedHashMap<>();
        request.put("session_id",session);request.put("client_pid",observedClientPid);request.put("character_id",1);
        request.put("batch",contactCapture.batch());request.put("requested_uptime_ms",now);
        request.put("frame_watermark",decodedFrames);request.put("dialog_semantics_verified",false);
        contactRequests.add(request);
        recordLifecycle("stationary_contact_view_capture_requested batch="+contactCapture.batch());
        requestContactFullUpdate();
        stage("Capturing contact view", "Keep the contact dialog visible while three fresh Android views are captured. Read a response, then close it normally and Save before the countdown expires.");
        notifyInputState();return true;
    }
    private void requestContactFullUpdate() {
        final InteractiveRfbClient expected=decoder;
        final String expectedSession=session;
        if(expected==null || inputWorker.isShutdown())return;
        try { inputWorker.execute(()->{
            if(decoder!=expected || !expectedSession.equals(session) || finished || cancelled || producerCompleted)return;
            try { expected.requestFullUpdate(); }
            catch(IOException failure) { inputFailure("Contact view refresh failed"); }
        }); }
        catch(RejectedExecutionException unavailable) { recordLifecycle("contact_view_refresh_queue_unavailable"); }
    }
    private boolean taskControlsAvailable() {
        return taskGateRequired() && reopen && inputReady && !finished && !finishRequested && !cancelled && !producerCompleted
                && connectedCapturedReady && characterConnectedEvent!=null && !saveLogoutRequested
                && characterSavedEvent==null && (!stuckRequested || relocationCapturedReady)
                && sessionBudget.canMove(SystemClock.uptimeMillis());
    }
    /** New input is reserved while a sidebar command types; native task evidence
     * and captures already requested retain their ordinary availability gate. */
    private boolean taskInputAvailable() {
        return !performanceCommandPending && taskControlsAvailable();
    }
    public synchronized boolean canCaptureTask(boolean completed) {
        if(!taskInputAvailable())return false;
        return completed ? taskCompletedEvent!=null && taskCompletionReceipt!=null
                && taskCompletedCapture.canRequest(SystemClock.uptimeMillis())
                : taskAcceptedEvent!=null && !taskCompletionRequested
                && taskAcceptedCapture.canRequest(SystemClock.uptimeMillis());
    }
    public synchronized boolean canOpenTaskContact() {
        return taskInputAvailable() && !taskContactRequested && taskAcceptedEvent==null && !taskCompletionRequested;
    }
    public synchronized boolean requestOpenTaskContact() {
        if(!canOpenTaskContact())return false;
        final String selectedSession=session;
        final long selectedPid=observedClientPid;
        if(!queueInput(selectedSession,(active,epoch)->{
            if(!taskInputAvailable() || taskAcceptedEvent!=null)
                throw new InteractiveRfbClient.InputCancelledException();
            active.sendOpenTaskContact(epoch);
            try {
                JSONObject receipt=new JSONObject().put("format",1).put("session_id",selectedSession)
                        .put("client_pid",selectedPid).put("character_id",1).put("action","contactdialog")
                        .put("contact_path","Contacts/Atlas_Park/Matthew_Habashy.contact")
                        .put("commands",new JSONArray().put("/contactdialog Contacts/Atlas_Park/Matthew_Habashy.contact"))
                        .put("sent_utc_ms",System.currentTimeMillis()).put("native_effect_verified",false);
                write(new File(state,"character-task-contact.json"),receipt.toString().getBytes(StandardCharsets.UTF_8));
                taskContactReceipt=receipt;
                recordLifecycle("task_contact_dialog_delivered");
            } catch(Exception failure) { throw new IOException("Could not record task contact command delivery",failure); }
            stage("Task contact dialog sent","Choose Matthew Habashy's first offered task, What Was Lost / Part One: Demons and Gangsters, and accept it yourself. Close the dialog, open the Tasks journal, and wait for Accepted task verified. The task mentions five Hellions; the completion command avoids that combat.");
        },true))return false;
        taskContactRequested=true;
        recordLifecycle("task_contact_dialog_requested");
        stage("Opening task contact","The fixed stock contactdialog command is queued. Keep game dialogs closed and controls released while it types. This opens Matthew Habashy without relying on his model; it does not accept a task.");
        notifyInputState();return true;
    }
    public synchronized boolean requestTaskCapture(boolean completed) {
        if(!canCaptureTask(completed))return false;
        ContactCaptureWindow window=completed?taskCompletedCapture:taskAcceptedCapture;
        JSONObject event=completed?taskCompletedEvent:taskAcceptedEvent;
        long now=SystemClock.uptimeMillis();
        if(!window.request(session,observedClientPid,1,now,decodedFrames))return false;
        try {
            Map<String,Object> request=new LinkedHashMap<>();
            request.put("session_id",session);request.put("client_pid",observedClientPid);request.put("character_id",1);
            request.put("phase",completed?"completed":"accepted");request.put("batch",window.batch());
            request.put("requested_uptime_ms",now);request.put("frame_watermark",decodedFrames);
            request.put("task",jsonValue(event.getJSONObject("task")));request.put("dialog_semantics_verified",false);
            taskCaptureRequests.add(request);
        } catch(Exception failure) { inputFailure("Could not bind task capture identity");return false; }
        recordLifecycle(completed?"completed_task_view_capture_requested":"accepted_task_view_capture_requested");
        requestContactFullUpdate();
        stage(completed?"Capturing completed task":"Capturing accepted task",
                "Keep the matching task journal entry visible while three fresh Android views are captured.");
        notifyInputState();return true;
    }
    public synchronized boolean canCompleteAcceptedTask() {
        return taskInputAvailable() && taskAcceptedEvent!=null && taskCompletedEvent==null
                && !taskCompletionRequested && taskAcceptedCapture.count()==ContactCaptureWindow.FRAMES_PER_REQUEST;
    }
    public synchronized boolean requestCompleteAcceptedTask() {
        if(!canCompleteAcceptedTask())return false;
        final JSONObject accepted=taskAcceptedEvent;
        final String selectedSession=session;
        final long selectedPid=observedClientPid;
        if(!queueInput(selectedSession,(active,epoch)->{
            if(!taskInputAvailable() || accepted!=taskAcceptedEvent || taskCompletedEvent!=null)
                throw new InteractiveRfbClient.InputCancelledException();
            active.sendCompleteAcceptedTask(epoch);
            try {
                JSONObject receipt=new JSONObject().put("format",1).put("session_id",selectedSession)
                        .put("client_pid",selectedPid).put("character_id",1).put("action","completetask")
                        .put("task_index",0).put("task",accepted.getJSONObject("task"))
                        .put("sent_utc_ms",System.currentTimeMillis());
                write(new File(state,"character-task-completion.json"),receipt.toString().getBytes(StandardCharsets.UTF_8));
                taskCompletionReceipt=receipt;
                recordLifecycle("accepted_task_completion_delivered");
            } catch(Exception failure) { throw new IOException("Could not record completed task command delivery",failure); }
        },true))return false;
        taskCompletionRequested=true;
        recordLifecycle("accepted_task_completion_requested");
        stage("Completing accepted task","The stock /completetask 0 command is queued for the single verified task. Wait for native and SQL completion verification, then capture its completed journal entry.");
        notifyInputState();return true;
    }
    private boolean gameplayInputAllowed() {
        return !reopen || sessionBudget.revision() < 1
                || (!saveLogoutRequested && sessionBudget.canMove(SystemClock.uptimeMillis()));
    }
    /** Release held inputs even if the activity is paused when its movement cutoff arrives. */
    public synchronized void enforceSessionDeadlines() {
        if (!reopen || sessionBudget.revision() < 1 || deadlineInputSuppressed
                || sessionBudget.canMove(SystemClock.uptimeMillis()) || finished || producerCompleted) return;
        deadlineInputSuppressed = true;
        // A queued normal save releases held input before typing its command.
        // Do not cancel that command as the preceding movement window closes.
        if (!saveLogoutRequested) discardPendingInputs(session);
        recordLifecycle("session_movement_deadline_reached");
        if (!saveLogoutRequested && characterSavedEvent == null)
            stage("Stand still before saving", "The movement window has ended. Keep controls released for 60 seconds, then request Save before its countdown expires.");
        notifyInputState();
    }
    private boolean queueInput(String selectedSession, InputWrite action) {
        return queueInput(selectedSession, action, false);
    }
    private synchronized boolean queueInput(String selectedSession, InputWrite action, boolean gameplay) {
        return queueInput(selectedSession, action, gameplay, 0);
    }
    private synchronized boolean queueInput(String selectedSession, InputWrite action, boolean gameplay, long performanceToken) {
        if (!inputReady || finishRequested || finished || cancelled || producerCompleted
                || session == null || !session.equals(selectedSession)
                || (performanceCommandPending && performanceToken != performanceCommandGeneration)
                || (gameplay && !gameplayInputAllowed())
                || (reopen && stuckRequested && !relocationCapturedReady)) return false;
        InteractiveRfbClient queuedDecoder = decoder;
        if (queuedDecoder == null) return false;
        // Bind at queue acceptance: a task which starts after a lifecycle release
        // must not adopt the new epoch and deliver a stale delayed press.
        long queuedEpoch = queuedDecoder.inputEpoch();
        try {
            inputWorker.execute(() -> {
                InteractiveRfbClient active = decoder;
                try {
                    if (!inputReady || finishRequested || finished || cancelled || producerCompleted || active != queuedDecoder
                            || (performanceCommandPending && performanceToken != performanceCommandGeneration)
                            || (gameplay && !gameplayInputAllowed())) return;
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
                finally { completePerformanceCommand(performanceToken); }
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
                finishRequested && !finished, characterSavedReady,
                !performanceCommandPending && reopen && sessionBudget.canMove(SystemClock.uptimeMillis()) && connectedCapturedReady && !stuckRequested && !saveLogoutRequested,
                !performanceCommandPending && characterConnectedEvent != null && (!reopen || (connectedCapturedReady && (!stuckRequested || relocationCapturedReady) && sessionBudget.canSave(SystemClock.uptimeMillis()))) && !saveLogoutRequested && characterSavedEvent == null,
                inputSent, inputFailed, readyDeadlineUptimeMillis, sessionBudget.phase(), sessionBudget.saveDeadline(), sessionBudget.movementDeadline());
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
        // Once accepted, normal Save owns its input epoch until delivery.
        // Surface disable/focus release must not interrupt the typed command;
        // explicit Stop and transport failure still cancel it separately.
        if (discard && !saveLogoutRequested) {
            cancelPendingInput(); inputWorker.getQueue().clear();
            if (performanceCommandPending) {
                performanceCommandPending = false;
                ++performanceCommandGeneration;
                recordLifecycle("performance_command_cancelled_by_input_release");
                notifyInputState();
            }
        }
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
    public synchronized boolean requestReturnToSafeGround() {
        if (performanceCommandPending || !reopen || !inputReady || finished || finishRequested || cancelled || producerCompleted
                || !sessionBudget.canMove(SystemClock.uptimeMillis()) || !connectedCapturedReady || characterConnectedEvent == null || stuckRequested
                || saveLogoutRequested || characterSavedEvent != null) return false;
        final String relocationSession = session;
        final long relocationClientPid = observedClientPid;
        final long relocationCharacterId = characterConnectedEvent.optLong("character_id", -1);
        if (!queueInput(relocationSession, (active, epoch) -> {
            active.sendReturnToSafeGround(epoch);
            try {
                long sentUtc = System.currentTimeMillis();
                byte[] receipt = new JSONObject().put("format", 1).put("session_id", relocationSession)
                        .put("client_pid", relocationClientPid).put("character_id", relocationCharacterId)
                        .put("action", "stuck").put("sent_utc_ms", sentUtc)
                        .toString().getBytes(StandardCharsets.UTF_8);
                write(new File(state, "character-relocation.json"), receipt);
                relocationSentUtcMillis = sentUtc;
                recordLifecycle("ordinary_character_relocation_delivered");
            } catch (Exception failure) {
                throw new IOException("Could not record completed character recovery delivery", failure);
            }
        })) return false;
        stuckRequested = true;
        recordLifecycle("ordinary_character_relocation_requested");
        stage("Returning to safe ground", "The ordinary /stuck command is queued. Stay still while the server checks two stable Atlas positions; this takes at least 25 seconds. Save remains disabled until ground verification and three fresh Android views.");
        notifyInputState();
        return true;
    }

    /** Save readiness is separate from the connected-session capability used for movement and task input. */
    public synchronized boolean canRequestSaveLogout() {
        return !performanceCommandPending && inputReady && !finished && !finishRequested && !cancelled && !producerCompleted
                && characterConnectedEvent != null && (!reopen || (connectedCapturedReady
                && (!stuckRequested || relocationCapturedReady) && sessionBudget.canSave(SystemClock.uptimeMillis())))
                && characterSavedEvent == null && !saveLogoutRequested && taskSaveReady();
    }
    private boolean taskSaveReady() {
        if(!taskGateRequired())return true;
        if(taskContactReceipt==null || taskCompletionReceipt==null)return false;
        try {
            return ClientAcceptance.taskSaveReady(jsonValue(taskAcceptedEvent),jsonValue(taskCompletedEvent),
                    taskAcceptedCapture.count(),taskCompletedCapture.count(),session,observedClientPid);
        } catch(Exception malformed) {return false;}
    }
    public synchronized boolean requestSaveLogout() {
        if(!canRequestSaveLogout())return false;
        final String logoutSession = session;
        final long logoutClientPid = observedClientPid;
        final long logoutCharacterId = characterConnectedEvent.optLong("character_id", -1);
        if (!queueInput(logoutSession, (active, epoch) -> {
            if ((reopen && !sessionBudget.canSave(SystemClock.uptimeMillis())) || !taskSaveReady()) {
                saveLogoutRequested = false;
                if(!taskSaveReady()) {
                    recordLifecycle("ordinary_character_logout_task_gate_incomplete_before_delivery");
                    stage("Task views required before Save", "Wait for matching accepted and completed task verification and capture both task journal views before saving.");
                } else {
                    recordLifecycle("ordinary_character_logout_deadline_expired_before_delivery");
                    stage("Save window expired", "The save command was not delivered before its cutoff. Export this session after cleanup.");
                }
                notifyInputState();
                throw new InteractiveRfbClient.InputCancelledException();
            }
            active.sendSaveLogout(epoch);
            // This receipt records completed command transport, never merely a
            // button press or queued work. The guest independently checks the
            // current character's logout timer and committed SQL afterwards.
            try {
                byte[] receipt = new JSONObject().put("format", 1).put("session_id", logoutSession)
                        .put("client_pid", logoutClientPid).put("character_id", logoutCharacterId)
                        .put("action", "quittologin").put("sent_utc_ms", System.currentTimeMillis())
                        .toString().getBytes(StandardCharsets.UTF_8);
                write(new File(state, "character-logout.json"), receipt);
                recordLifecycle("ordinary_character_logout_delivered");
            } catch (Exception failure) {
                recordLifecycle("ordinary_character_logout_receipt_failed");
                throw new IOException("Could not record completed character logout delivery", failure);
            }
        })) return false;
        saveLogoutRequested = true;
        recordLifecycle("ordinary_character_logout_requested");
        stage("Saving character", "The ordinary /quittologin command is queued. Wait for logout and committed database verification, then three fresh Android captures.");
        notifyInputState();
        return true;
    }

    public synchronized boolean requestFinish() {
        if (!inputReady || finished || finishRequested || cancelled || producerCompleted || observedClientPid < 1) return false;
        if (!characterSavedReady) {
            stage("Waiting for saved character", "Finish becomes available after THORHERO is committed to the database and three fresh Android views are captured.");
            return false;
        }
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
        boolean loginSample = loginObservedUptime >= 0 && captured >= loginObservedUptime
                && ((Number) sequence).longValue() > loginFrameWatermark && loginSamples.size() < 3
                && (loginSamples.isEmpty()
                || captured - ((Number) loginSamples.get(loginSamples.size()-1).get("captured_elapsed_ms")).longValue() >= 1000);
        boolean connectedSample = reopen && connectedObservedUptime >= 0 && captured >= connectedObservedUptime
                && ((Number) sequence).longValue() > connectedFrameWatermark && connectedSamples.size() < 3
                && (connectedSamples.isEmpty()
                || captured - ((Number) connectedSamples.get(connectedSamples.size()-1).get("captured_elapsed_ms")).longValue() >= 1000);
        boolean relocationSample = reopen && relocatedObservedUptime >= 0 && captured >= relocatedObservedUptime
                && ((Number) sequence).longValue() > relocatedFrameWatermark && relocationSamples.size() < 3
                && (relocationSamples.isEmpty()
                || captured - ((Number) relocationSamples.get(relocationSamples.size()-1).get("captured_elapsed_ms")).longValue() >= 1000);
        boolean characterSample = characterObservedUptime >= 0 && captured >= characterObservedUptime
                && ((Number) sequence).longValue() > characterFrameWatermark && characterSamples.size() < 3
                && (characterSamples.isEmpty()
                || captured - ((Number) characterSamples.get(characterSamples.size()-1).get("captured_elapsed_ms")).longValue() >= 1000);
        boolean afterInput = inputSent > 0 && captured >= lastInputUptime
                && ((Number) sequence).longValue() > lastInputFrameWatermark;
        boolean interactionSample = readyDeadlineUptimeMillis > 0 && (interactionSamples.isEmpty()
                || (afterInput && inputSent > lastCapturedInputCount) || (finishRequested && !finishCaptureRetained));
        boolean contactSample = characterConnectedEvent!=null && !saveLogoutRequested && characterSavedEvent==null
                && (!stuckRequested || relocationCapturedReady) && sessionBudget.canMove(SystemClock.uptimeMillis())
                && contactCapture.accepts(session,observedClientPid,characterConnectedEvent.optLong("character_id",-1),captured,((Number)sequence).longValue());
        boolean acceptedTaskSample=taskControlsAvailable() && taskAcceptedEvent!=null && !taskCompletionRequested
                && taskAcceptedCapture.accepts(session,observedClientPid,1,captured,((Number)sequence).longValue());
        boolean completedTaskSample=taskControlsAvailable() && taskCompletedEvent!=null && taskCompletionReceipt!=null
                && taskCompletedCapture.accepts(session,observedClientPid,1,captured,((Number)sequence).longValue());
        if (!startupSample && !loginSample && !connectedSample && !relocationSample && !characterSample && !interactionSample && !contactSample && !acceptedTaskSample && !completedTaskSample) return;
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
            if(acceptedTaskSample || completedTaskSample) {
                boolean completed=completedTaskSample;
                ContactCaptureWindow window=completed?taskCompletedCapture:taskAcceptedCapture;
                JSONObject event=completed?taskCompletedEvent:taskAcceptedEvent;
                if(window.accept(session,observedClientPid,1,captured,((Number)sequence).longValue())) {
                    Map<String,Object> task=new LinkedHashMap<>(sample);
                    task.put("client_pid",observedClientPid);task.put("character_id",1);
                    task.put("phase",completed?"completed":"accepted");task.put("batch",window.batch());
                    task.put("task",jsonValue(event.getJSONObject("task")));task.put("dialog_semantics_verified",false);
                    task.put("archive_path","android-task/"+(completed?"completed":"accepted")+"-capture-"+(taskSamples.size()+1)+".png");
                    taskSamples.add(task);taskPngs.add(png.clone());
                    if(window.count()<ContactCaptureWindow.FRAMES_PER_REQUEST)requestContactFullUpdate();
                    else {
                        stage(completed?"Completed task view captured":"Accepted task view captured",
                                completed?"Three completed-task views were saved for review. Release controls for 60 seconds, then Save character / log out and Finish after verification."
                                        :"Three accepted-task views were saved for review. Close the journal and contact dialog with B, then tap Complete accepted task once.");
                        notifyInputState();
                    }
                }
            }
            if (contactSample && contactCapture.accept(session,observedClientPid,characterConnectedEvent.optLong("character_id",-1),captured,((Number)sequence).longValue())) {
                Map<String,Object> contact = new LinkedHashMap<>(sample);
                contact.put("client_pid",observedClientPid);contact.put("character_id",1);
                contact.put("batch",contactCapture.batch());contact.put("dialog_semantics_verified",false);
                contact.put("archive_path","android-contact/capture-"+(contactSamples.size()+1)+".png");
                contactSamples.add(contact);contactPngs.add(png.clone());
                if(contactCapture.count()<ContactCaptureWindow.FRAMES_PER_REQUEST)requestContactFullUpdate();
                if(contactCapture.count()==ContactCaptureWindow.FRAMES_PER_REQUEST) {
                    stage("Contact view captured", "Three fresh Android views were saved for review. Confirm the NPC and readable dialog, choose a normal response or Goodbye, then release controls for 60 seconds before Save.");
                    notifyInputState();
                }
            }
            if (startupSample) {
                sample.put("archive_path", "android-surface/capture-" + (surfaceSamples.size()+1) + ".png");
                surfaceSamples.add(sample); surfacePngs.add(png.clone());
            }
            if (loginSample) {
                Map<String,Object> login = new LinkedHashMap<>(sample);
                login.put("archive_path", "android-login/capture-" + (loginSamples.size()+1) + ".png");
                login.put("post_login_frame_observed", true);
                loginSamples.add(login); loginPngs.add(png.clone());
                if (loginSamples.size() == 3)
                    stage("Local login verified", reopen ? "Select the existing THORHERO and click Enter Game. Keep its existing costume and powers. Do not create or delete a character." : "Create THORHERO as a Primal Earth Hero, skip the tutorial, and wait for Saved character verified.");
            }
            if (connectedSample) {
                Map<String,Object> connected = new LinkedHashMap<>(sample);
                connected.put("archive_path", "android-connected/capture-" + (connectedSamples.size()+1) + ".png");
                connected.put("post_character_connection_frame_observed", true);
                connected.put("character_id", characterConnectedEvent.getLong("character_id"));
                connectedSamples.add(connected); connectedPngs.add(png.clone());
                if (connectedSamples.size() == 3) {
                    connectedCapturedReady = true;
                    if (Boolean.TRUE.equals(manifest.opt("startup_only_reopen")))
                        stage("Atlas connected for startup timing", "THORHERO connected and fresh Android views were captured. Note your loading time, then Stop and export this startup-only session. Existing tasks are preserved; no task or movement retest is requested.");
                    else stage("Atlas ready for task check", "THORHERO connected and fresh Android views were captured. Close help and game dialogs, then tap Open task contact to speak to Matthew Habashy. Accept his first offered task, open its journal entry, and wait for Accepted task verified. Capture it before using Complete accepted task. Return to safe ground is optional if stuck.");
                    notifyInputState();
                }
            }
            if (relocationSample) {
                Map<String,Object> relocated = new LinkedHashMap<>(sample);
                relocated.put("archive_path", "android-relocated/capture-" + (relocationSamples.size()+1) + ".png");
                relocated.put("post_character_relocation_frame_observed", true);
                relocated.put("character_id", characterRelocatedEvent.getLong("character_id"));
                relocationSamples.add(relocated); relocationPngs.add(png.clone());
                if (relocationSamples.size() == 3) {
                    relocationCapturedReady = true;
                    stage("Atlas position verified", "The server observed two stable positions after /stuck and three fresh Android views were captured. Follow the movement and Save countdowns below. Release controls for 60 seconds before Save; keep still through logout, then tap Finish after Saved character verified.");
                    notifyInputState();
                }
            }
            if (characterSample) {
                Map<String,Object> saved = new LinkedHashMap<>(sample);
                saved.put("archive_path", "android-character/capture-" + (characterSamples.size()+1) + ".png");
                saved.put("post_character_save_frame_observed", true);
                saved.put("character_id", characterSavedEvent.getLong("character_id"));
                characterSamples.add(saved); characterPngs.add(png.clone());
                if (characterSamples.size() == 3) {
                    characterSavedReady = true;
                    stage("Saved character verified", "THORHERO was committed to the local database and three fresh Android views were captured. Tap Finish and save report.");
                    notifyInputState();
                }
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
                        if ("client_display_ready".equals(event.optString("type"))
                                && session.equals(event.optString("session_id"))
                                && event.optInt("width", -1) == 800 && event.optInt("height", -1) == 600
                                && event.optInt("startup_timeout_seconds", -1) == 900
                                && launcherBudgetStartedUptime < 0 && !cancelled && !finished)
                            launcherBudgetStartedUptime = SystemClock.uptimeMillis();
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
                        if ("client_login_ready".equals(event.optString("type"))
                                && session.equals(event.optString("session_id")) && observedClientPid > 0
                                && observedClientPid == event.optLong("client_pid", -1)
                                && loginObservedUptime < 0 && !cancelled && !finished && !producerCompleted) {
                            synchronized (this) {
                                loginObservedUptime = SystemClock.uptimeMillis();
                                loginFrameWatermark = decodedFrames;
                                loginSamples.clear(); loginPngs.clear();
                            }
                            InteractiveRfbClient activeDecoder = decoder;
                            if (activeDecoder != null) {
                                try { activeDecoder.requestFullUpdate(); }
                                catch (IOException e) { receiverFailure = "Cannot refresh the logged-in client: " + message(e); }
                            }
                            recordLifecycle("local_login_observed");
                            stage("Local server login observed", reopen ? "The server sent the saved character list. Select THORHERO and click Enter Game. Do not create or delete a character." : "The server sent the character list. Create THORHERO as a Primal Earth Hero and skip the tutorial.");
                        }
                        if ((reopen ? ClientAcceptance.characterReopenConnectedEvent(jsonValue(event), session, observedClientPid) : ClientAcceptance.characterConnectedEvent(jsonValue(event), session, observedClientPid))
                                && characterConnectedEvent == null && loginObservedUptime >= 0
                                && !cancelled && !finished && !producerCompleted) {
                            synchronized (this) {
                                characterConnectedEvent = event;
                                connectedObservedUptime = SystemClock.uptimeMillis();
                                connectedFrameWatermark = decodedFrames;
                                connectedSamples.clear(); connectedPngs.clear(); connectedCapturedReady = false;
                            }
                            InteractiveRfbClient activeDecoder = decoder;
                            if (activeDecoder != null) {
                                try { activeDecoder.requestFullUpdate(); }
                                catch (IOException e) { receiverFailure = "Cannot refresh the reopened character: " + message(e); }
                            }
                            recordLifecycle("character_connected_observed");
                            stage("Character connected", reopen ? "The existing THORHERO connected to Atlas. Waiting for fresh Android views and the bounded session window before movement, contact interaction and Save become available." : "THORHERO connected to Atlas. Inspect the character and UI, then tap Save character / log out once to verify ordinary character persistence.");
                            notifyInputState();
                        }
                        if (reopen && stuckRequested && connectedCapturedReady && characterRelocatedEvent == null
                                && ClientAcceptance.characterRelocatedEvent(jsonValue(event), session, observedClientPid)
                                && !cancelled && !finished && !producerCompleted) {
                            synchronized (this) {
                                characterRelocatedEvent = event;
                                relocatedObservedUptime = SystemClock.uptimeMillis();
                                relocatedFrameWatermark = decodedFrames;
                                relocationSamples.clear(); relocationPngs.clear(); relocationCapturedReady = false;
                            }
                            InteractiveRfbClient activeDecoder = decoder;
                            if (activeDecoder != null) {
                                try { activeDecoder.requestFullUpdate(); }
                                catch (IOException e) { receiverFailure = "Cannot refresh the recovered character: " + message(e); }
                            }
                            recordLifecycle("character_relocation_verified");
                            stage("Stable Atlas position observed", "The server verified stable ground after /stuck. Waiting for three fresh Android views before Save becomes available.");
                        }
                        if(taskAcceptedEvent==null && taskControlsAvailable()
                                && ClientAcceptance.taskEvent(jsonValue(event),"character_task_accepted",session,observedClientPid)) {
                            taskAcceptedEvent=event;
                            recordLifecycle("accepted_task_verified");
                            stage("Accepted task verified","The guest bound one current task to its native Task:Add and SQL state. Open that task in the journal and tap Capture accepted task.");
                            notifyInputState();
                        }
                        if(taskCompletedEvent==null && taskCompletionRequested && taskAcceptedEvent!=null
                                && taskControlsAvailable()
                                && ClientAcceptance.taskEvent(jsonValue(event),"character_task_completed",session,observedClientPid)
                                && ClientAcceptance.sameTaskIdentity(jsonValue(taskAcceptedEvent.getJSONObject("task")),jsonValue(event.getJSONObject("task")))) {
                            taskCompletedEvent=event;
                            recordLifecycle("accepted_task_completion_verified");
                            stage("Task completion verified","The same accepted task completed through the stock command and current SQL state. Open its completed journal entry and tap Capture completed task; no combat is required.");
                            notifyInputState();
                        }
                        if (ClientAcceptance.characterSavedEvent(jsonValue(event), session, observedClientPid)
                                && characterObservedUptime < 0 && loginObservedUptime >= 0
                                && characterConnectedEvent != null
                                && event.getLong("character_id") == characterConnectedEvent.getLong("character_id")
                                && !cancelled && !finished && !producerCompleted) {
                            synchronized (this) {
                                characterSavedEvent = event;
                                characterObservedUptime = SystemClock.uptimeMillis();
                                characterFrameWatermark = decodedFrames;
                                characterSamples.clear(); characterPngs.clear();
                            }
                            InteractiveRfbClient activeDecoder = decoder;
                            if (activeDecoder != null) {
                                try { activeDecoder.requestFullUpdate(); }
                                catch (IOException e) { receiverFailure = "Cannot refresh the saved character: " + message(e); }
                            }
                            recordLifecycle("character_saved_observed");
                            stage("Character saved", "THORHERO is committed to the local database. Waiting for three fresh Android views before Finish.");
                        }
                        if (reopen && "character_session_budget".equals(event.optString("type"))
                                && !cancelled && !finished && !producerCompleted) {
                            long now = SystemClock.uptimeMillis();
                            // The display event precedes Wine launcher startup. Allow
                            // up to one minute of transport/setup here; the guest's
                            // actual emitted deadline is capped at launcher +34min.
                            long hardCap = Math.min(startedUptime + 5400000,
                                    launcherBudgetStartedUptime < 0 ? now : launcherBudgetStartedUptime + 2100000);
                            @SuppressWarnings("unchecked") Map<String,Object> value = (Map<String,Object>)jsonValue(event);
                            if (sessionBudget.apply(value, session, observedClientPid,
                                    characterConnectedEvent != null, characterRelocatedEvent != null,
                                    relocationSentUtcMillis, System.currentTimeMillis(), now, hardCap)) {
                                synchronized (this) { sessionBudgetEvents.add(value); }
                                readyDeadlineUptimeMillis = sessionBudget.deadline();
                                recordLifecycle("character_session_budget_" + sessionBudget.phase());
                                notifyInputState();
                            } else {
                                recordLifecycle("character_session_budget_rejected");
                                stage("Session deadline not verified", "The current character's phase deadline could not be verified. Save remains guarded by the current session evidence; export this session after cleanup if it stays unavailable.");
                            }
                        }
                        if ("client_interaction_ready".equals(event.optString("type"))
                                && session.equals(event.optString("session_id")) && observedClientPid > 0
                                && observedClientPid == event.optLong("client_pid", -1)
                                && event.optInt("minimum_observation_seconds", -1) == 30
                                && event.optInt("interaction_timeout_seconds", -1) == 1200
                                && !interactionReadyObserved && !cancelled && !finished) {
                            interactionReadyObserved = true;
                            if (sessionBudget.revision() == 0) readyDeadlineUptimeMillis = SystemClock.uptimeMillis() + 1200000;
                            inputReady = true; recordLifecycle("interaction_ready"); notifyInputState();
                            stage("Client ready for input", reopen ? "Log in with COHLOCAL / offline, select the existing THORHERO and click Enter Game. Do not create or delete a character. Twenty minutes remain." : "Log in with COHLOCAL / offline. Create THORHERO as a Primal Earth Hero, skip the tutorial, and wait for Saved character verified. Twenty minutes remain.");
                        }
                        // Keep the actionable save/Finish instruction visible while
                        // the guest continues its generic five-second live heartbeat.
                        boolean interactionHeartbeat = "stage".equals(event.optString("type"))
                                && "running".equals(event.optString("status"))
                                && "actual_client_interaction".equals(event.optString("stage"));
                        if ("stage".equals(event.optString("type"))
                                && !(interactionHeartbeat && (characterSavedReady || characterConnectedEvent != null)))
                            listener.onStage(event.optString("stage", "Checking display"),
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
                || !"actual_character_reopen_guest".equals(manifest.getJSONObject("client_bundle").optString("scope"))
                || !"character_reopen_diagnostic.py".equals(manifest.getJSONObject("client_bundle").optString("guest_script")))
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
        for (String name : new String[]{"character_reopen_diagnostic.py", "character_creation_diagnostic.py", "character_avatar_assets.py",
                "character-avatar-defaults.zip", "character-avatar-defaults-manifest.json",
                "local_login_server.py", "dbserver-package.tar.gz", "dbserver-schema.tar.gz", "client-manifest.json",
                "client-runtime.zip", "client-caches.zip", "client-prerequisites.zip", "client-launcher.exe"})
            if (!files.has(name)) throw new IOException("Client runtime payload is missing: " + name);
    }
    private void removePreviousGuestOutput() throws IOException {
        retirePreviousGuestOutput(new StorageFiles(home.getParentFile()));
    }
    /** Retire only fixed session outputs, never any profile/cache/import directory. */
    static void retirePreviousGuestOutput(StorageAudit.Fs files) throws IOException {
        StorageAudit.Stat parent = files.stat("client/state");
        if (parent == null || parent.kind != StorageAudit.Kind.DIRECTORY)
            throw new IOException("Private guest output directory is unavailable");
        Map<String,StorageAudit.Stat> previous = new LinkedHashMap<>();
        for (String name : new String[]{"stop-request", "interaction-finish.json", "character-logout.json", "character-relocation.json", "latest-report.json", "report.zip", "character-task-contact.json", "character-task-completion.json"}) {
            String path = "client/state/" + name;
            StorageAudit.Stat entry = files.stat(path);
            if (entry == null) continue;
            if (entry.kind != StorageAudit.Kind.FILE && entry.kind != StorageAudit.Kind.SYMLINK)
                throw new IOException("Cannot clear unsafe previous guest output: " + name);
            previous.put(path, entry);
        }
        // Validate every fixed member first. remove() anchors the verified parent
        // and unlinks a symlink itself, including a dangling link, without following it.
        for (Map.Entry<String,StorageAudit.Stat> entry : previous.entrySet())
            files.remove(entry.getKey(), entry.getValue(), parent);
    }

    private boolean guestAccepted(JSONObject report) throws Exception {
        if (!(report.optBoolean("passed") && "passed".equals(report.optString("status"))
                && session.equals(report.optString("session_id"))
                && (reopen ? Boolean.TRUE.equals(manifest.opt("startup_only_reopen")) ? "actual_character_startup_timing_guest" : "actual_character_reopen_guest" : "actual_character_creation_guest").equals(report.optString("scope"))
                && (reopen ? Boolean.TRUE.equals(manifest.opt("startup_only_reopen")) ? "actual_character_startup_timing" : "actual_character_reopen" : "actual_character_creation").equals(report.optString("diagnostic_mode"))
                && (!reopen || !Boolean.TRUE.equals(manifest.opt("startup_only_reopen"))
                    || Boolean.TRUE.equals(report.opt("startup_only_reopen")) && Boolean.FALSE.equals(report.opt("task_gate_required")))
                && "android".equals(report.optString("execution_platform_requested"))
                && report.optJSONArray("failures") != null && report.getJSONArray("failures").length() == 0
                && Boolean.TRUE.equals(report.opt("postgres_started")) && Boolean.TRUE.equals(report.opt("server_started"))
                && Boolean.TRUE.equals(report.opt("mapserver_started"))
                && (reopen ? ClientAcceptance.characterReopenVerified(jsonValue(report), jsonValue(characterSavedEvent), jsonValue(characterConnectedEvent), session, observedClientPid) : ClientAcceptance.characterCreationVerified(jsonValue(report), jsonValue(characterSavedEvent), jsonValue(characterConnectedEvent), session, observedClientPid))
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
        if (!Double.isFinite(observed) || observed < 30 || observed > 1210
                || !Double.isFinite(elapsed) || elapsed < 0 || elapsed > 900) return false;
        JSONObject launch = report.optJSONObject("client_launch");
        if (launch == null || !session.equals(launch.optString("session_id")) || observedClientPid < 1
                || observedClientPid != launch.optLong("pid", -1)) return false;
        JSONArray windows = report.optJSONArray("client_windows");
        if (windows == null || windows.length() < 1 || windows.length() > 512) return false;
        boolean actualWindow = false;
        for (int i=0;i<windows.length();i++) {
            JSONObject window = windows.getJSONObject(i);
            if (ClientAcceptance.clientWindowAccepted(jsonValue(window), observedClientPid)) actualWindow = true;
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
        JSONArray stages = report.optJSONArray("stages");
        // The visual/animation stages are required only by an APK whose exact
        // asset pins include the complete bundle. A guest flag cannot select
        // a shorter path or excuse a missing/failed preparation stage.
        int interactionStage = ClientAcceptance.clientInteractionStageIndex(
                jsonValue(stages), jsonValue(clientPins));
        if (interactionStage < 0) return false;
        JSONObject inputs = stages.getJSONObject(0), startup = stages.getJSONObject(interactionStage);
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
    private boolean loginSurfaceAccepted() {
        synchronized (this) {
            return ClientAcceptance.surfaceAccepted(loginSamples, session, startedUptime, endedUptime,
                    loginObservedUptime, clientWindowEndedUptime, loginFrameWatermark);
        }
    }

    private boolean characterSurfaceAccepted(JSONObject report) throws Exception {
        synchronized (this) {
            if (reopen) return characterSavedReady && connectedCapturedReady && (!stuckRequested || relocationCapturedReady)
                    && (!taskGateRequired() || taskGateAccepted(report))
                    && ClientAcceptance.characterReopenAccepted(jsonValue(report), jsonValue(characterSavedEvent),
                    jsonValue(characterConnectedEvent), jsonValue(characterRelocatedEvent), connectedSamples, relocationSamples, characterSamples, session, observedClientPid,
                    startedUptime, endedUptime, connectedObservedUptime, connectedFrameWatermark, relocatedObservedUptime, relocatedFrameWatermark,
                    characterObservedUptime, clientWindowEndedUptime, characterFrameWatermark);
            return characterSavedReady && ClientAcceptance.characterCreationAccepted(jsonValue(report), jsonValue(characterSavedEvent),
                    jsonValue(characterConnectedEvent), characterSamples, session, observedClientPid, startedUptime, endedUptime,
                    characterObservedUptime, clientWindowEndedUptime, characterFrameWatermark);
        }
    }
    private boolean taskGateRequired() {
        return reopen && manifest!=null && !Boolean.TRUE.equals(manifest.opt("startup_only_reopen"))
                && Boolean.TRUE.equals(manifest.opt("task_gate_required"));
    }
    private boolean taskGateAccepted(JSONObject report) throws Exception {
        JSONObject proof=report.optJSONObject("task_gate");
        if(proof==null || !Boolean.TRUE.equals(proof.opt("verified")) || taskContactReceipt==null
                || !session.equals(proof.optString("session_id")) || proof.optLong("client_pid",-1)!=observedClientPid
                || proof.optLong("character_id",-1)!=1
                || taskAcceptedEvent==null || taskCompletedEvent==null || taskCompletionReceipt==null
                || !ClientAcceptance.taskEvent(jsonValue(taskAcceptedEvent),"character_task_accepted",session,observedClientPid)
                || !ClientAcceptance.taskEvent(jsonValue(taskCompletedEvent),"character_task_completed",session,observedClientPid)
                || !ClientAcceptance.sameTaskIdentity(jsonValue(taskAcceptedEvent.getJSONObject("task")),jsonValue(taskCompletedEvent.getJSONObject("task")))
                || !ClientAcceptance.sameTaskIdentity(jsonValue(taskAcceptedEvent.getJSONObject("task")),jsonValue(proof.optJSONObject("task"))))return false;
        return taskAcceptedCapture.count()==ContactCaptureWindow.FRAMES_PER_REQUEST
                && taskCompletedCapture.count()==ContactCaptureWindow.FRAMES_PER_REQUEST;
    }

    private static String localHosts(String hostname) throws IOException {
        if (hostname == null || hostname.isEmpty() || hostname.length() > 253)
            throw new IOException("Kernel hostname is not a safe hosts-file name");
        String[] labels = hostname.split("\\.", -1);
        for (String label : labels)
            if (!label.matches("[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"))
                throw new IOException("Kernel hostname is not a safe hosts-file name");
        return "127.0.0.1 " + String.join(" ", new LinkedHashSet<>(Arrays.asList("localhost", hostname, labels[0]))) + "\n";
    }

    private static JSONObject historicalProcessExits(Context context) throws Exception {
        JSONObject result=new JSONObject().put("maximum_records",4).put("records",new JSONArray())
                .put("own_processes_only",true).put("trace_streams_requested",false);
        if(Build.VERSION.SDK_INT<30)return result.put("status","unsupported_api");
        try { return ProcessExitHistory.collect(context,result); }
        catch(RuntimeException e) {
            // Exit history is optional evidence. A vendor/service failure must
            // never prevent the current operation's report from being saved.
            return result.put("status","unavailable").put("records",new JSONArray())
                    .put("error_class",e.getClass().getSimpleName());
        }
    }
    static JSONObject setupProcessExitHistory(Context context) throws Exception {
        return historicalProcessExits(context);
    }
    /** Isolates Android 11 classes from the supported Android 8-10 path. */
    private static final class ProcessExitHistory {
        static JSONObject collect(Context context,JSONObject result) throws Exception {
            android.app.ActivityManager manager=(android.app.ActivityManager)context.getSystemService(Context.ACTIVITY_SERVICE);
            if(manager==null)return result.put("status","unavailable");
            String ownPackage=context.getPackageName();
            List<android.app.ApplicationExitInfo> history=manager.getHistoricalProcessExitReasons(ownPackage,0,4);
            JSONArray records=new JSONArray();
            if(history!=null)for(int i=0;i<Math.min(history.size(),4);i++) {
                android.app.ApplicationExitInfo info=history.get(i);
                if(info==null)continue;
                String processName=info.getProcessName();
                if(processName==null||!(processName.equals(ownPackage)||processName.startsWith(ownPackage+":")))continue;
                records.put(new JSONObject().put("timestamp_utc_ms",info.getTimestamp())
                        .put("reason",info.getReason()).put("status",info.getStatus())
                        .put("importance",info.getImportance()).put("pss_kib",info.getPss())
                        .put("rss_kib",info.getRss()).put("pid",info.getPid())
                        .put("process_name",processName.substring(0,Math.min(processName.length(),160))));
            }
            return result.put("status","available").put("records",records);
        }
    }

    private void publish(JSONObject guest, boolean passed, boolean cleanup) throws IOException {
        try {
            JSONObject wrapper = new JSONObject().put("format", 1).put("operation", operation).put("run_id", runId)
                    .put("session_id", session == null ? JSONObject.NULL : session).put("app_id", context.getPackageName())
                    .put("app_version", appVersion()).put("android_sdk", Build.VERSION.SDK_INT)
                    .put("android_uid", android.os.Process.myUid()).put("device", Build.MANUFACTURER + " " + Build.MODEL)
                    .put("android_process_exit_history",historicalProcessExits(context))
                    .put("runtime_setup_service",ClientService.setupMemoryEvidence(context))
                    .put("abis", new JSONArray(Arrays.asList(Build.SUPPORTED_ABIS)))
                    .put("runtime_manifest_sha256", manifestHash).put("started_uptime_ms", startedUptime)
                    .put("finished_uptime_ms", endedUptime).put("process_exit_code", processExit)
                    .put("passed", passed).put("android_surface_validated", passed).put("interaction_session_completed", passed)
                    .put("menu_visual_validated", false).put("cleanup_verified", cleanup)
                    .put("cleanup_blocked", isCleanupBlocked()).put("cancelled", cancelled)
                    .put("gameplay_validated", false).put("game_rendering_validated", false)
                    .put("hardware_acceleration_validated", false).put("controller_input_validated", false)
                    .put("graphics_profile_requested", graphicsProfileRequested)
                    .put("fresh_profile_creation_requested", !reopen && "character_creation".equals(operation))
                    .put("startup_only_reopen", reopen && manifest!=null && Boolean.TRUE.equals(manifest.opt("startup_only_reopen")))
                    .put("character_profile_state", characterProfileState(context).name())
                    .put("input_effect_verified", false).put("input_events_sent", inputSent).put("input_events_failed", inputFailed)
                    .put("input_transport_observed", inputSent > 0 && inputFailed == 0)
                    .put("input_worker_stopped", inputWorker.isTerminated())
                    .put("finish_requested", finishRequested).put("interaction_deadline_uptime_ms", readyDeadlineUptimeMillis)
                    .put("session_budget_revision", sessionBudget.revision()).put("session_budget_phase", sessionBudget.phase())
                    .put("session_budget_events", new JSONArray(sessionBudgetEvents))
                    .put("save_request_deadline_uptime_ms", sessionBudget.saveDeadline())
                    .put("movement_deadline_uptime_ms", sessionBudget.movementDeadline())
                    .put("relocation_sent_utc_ms", relocationSentUtcMillis)
                    .put("deadline_input_suppressed", deadlineInputSuppressed)
                    .put("scope", reopen && manifest!=null && Boolean.TRUE.equals(manifest.opt("startup_only_reopen")) ? "Saved THORHERO startup and connection timing only; existing tasks are preserved and task qualification is not requested. Stop produces timing evidence, not an ordinary save or gameplay pass." : taskGateRequired() ? "Manually accept one authored task, complete it through the stock command, and persist its completed state by ordinary THORHERO logout with fresh accepted/completed Android views; combat, mission maps and reward turn-in remain unvalidated" : reopen ? "Reopen the existing COHLOCAL THORHERO with preserved identity, powers and costume and fresh Android PixelCopy after native connection and ordinary save; rendering, movement and gameplay remain separately assessed" : "Graphical creation and committed SQL persistence of THORHERO with fresh Android PixelCopy after the save event; world rendering, movement and gameplay remain unvalidated")
                    .put("local_login_verified", ClientAcceptance.localLoginVerified(jsonValue(guest), session, observedClientPid))
                    .put("character_creation_verified", !reopen && "character_creation".equals(operation) && passed)
                    .put("character_reopen_verified", reopen && passed)
                    .put("character_connected_observed_uptime_ms", connectedObservedUptime)
                    .put("character_connected_frame_watermark", connectedFrameWatermark)
                    .put("character_saved_event", characterSavedEvent == null ? JSONObject.NULL : characterSavedEvent)
                    .put("character_connected_event", characterConnectedEvent == null ? JSONObject.NULL : characterConnectedEvent)
                    .put("character_relocated_event", characterRelocatedEvent == null ? JSONObject.NULL : characterRelocatedEvent)
                    .put("stuck_requested", stuckRequested)
                    .put("character_relocated_observed_uptime_ms", relocatedObservedUptime)
                    .put("character_relocated_frame_watermark", relocatedFrameWatermark)
                    .put("save_logout_requested", saveLogoutRequested)
                    .put("character_saved_observed_uptime_ms", characterObservedUptime)
                    .put("character_saved_frame_watermark", characterFrameWatermark)
                    .put("character_selection_visible", false)
                    .put("login_observed_uptime_ms", loginObservedUptime)
                    .put("login_frame_watermark", loginFrameWatermark)
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
                wrapper.put("login_captures", new JSONArray(loginSamples));
                wrapper.put("character_captures", new JSONArray(characterSamples));
                wrapper.put("connected_captures", new JSONArray(connectedSamples));
                wrapper.put("relocation_captures", new JSONArray(relocationSamples));
                wrapper.put("interaction_captures", new JSONArray(interactionSamples));
                List<Map<String,Object>> requests = new ArrayList<>();
                for(Map<String,Object> original:contactRequests) {
                    Map<String,Object> request=new LinkedHashMap<>(original);
                    int count=0;
                    for(Map<String,Object> capture:contactSamples)if(original.get("batch").equals(capture.get("batch")))count++;
                    request.put("fresh_views_captured",count);request.put("capture_complete",count==ContactCaptureWindow.FRAMES_PER_REQUEST);
                    requests.add(request);
                }
                wrapper.put("stationary_contact",new JSONObject().put("capture_requests",new JSONArray(requests))
                        .put("captures",new JSONArray(contactSamples)).put("maximum_requests",ContactCaptureWindow.MAX_REQUESTS)
                        .put("frames_per_request",ContactCaptureWindow.FRAMES_PER_REQUEST).put("dialog_semantics_verified",false)
                        .put("native_interaction_effect_verified",false).put("user_visual_assessment_required",true));
                List<Map<String,Object>> taskRequests=new ArrayList<>();
                for(Map<String,Object> original:taskCaptureRequests) {
                    Map<String,Object> request=new LinkedHashMap<>(original);
                    int count=0;
                    for(Map<String,Object> capture:taskSamples)
                        if(original.get("phase").equals(capture.get("phase")) && original.get("batch").equals(capture.get("batch")))count++;
                    request.put("fresh_views_captured",count);request.put("capture_complete",count==ContactCaptureWindow.FRAMES_PER_REQUEST);
                    taskRequests.add(request);
                }
                wrapper.put("task_gate",new JSONObject()
                        .put("required",taskGateRequired())
                        .put("verified",taskGateRequired() && taskGateAccepted(guest))
                        .put("contact_requested",taskContactRequested)
                        .put("contact_delivered_receipt",taskContactReceipt==null?JSONObject.NULL:taskContactReceipt)
                        .put("accepted_event",taskAcceptedEvent==null?JSONObject.NULL:taskAcceptedEvent)
                        .put("completed_event",taskCompletedEvent==null?JSONObject.NULL:taskCompletedEvent)
                        .put("completion_requested",taskCompletionRequested)
                        .put("completion_delivered_receipt",taskCompletionReceipt==null?JSONObject.NULL:taskCompletionReceipt)
                        .put("capture_requests",new JSONArray(taskRequests)).put("captures",new JSONArray(taskSamples))
                        .put("maximum_requests_per_phase",ContactCaptureWindow.MAX_REQUESTS)
                        .put("frames_per_request",ContactCaptureWindow.FRAMES_PER_REQUEST)
                        .put("dialog_semantics_verified",false).put("user_visual_assessment_required",true)
                        .put("combat_verified",false).put("mission_map_verified",false));
                wrapper.put("recovery_requested",stuckRequested).put("recovery_verified",stuckRequested&&relocationCapturedReady);
                wrapper.put("lifecycle", new JSONArray(lifecycle));
            }
            String status = isCleanupBlocked() ? "cleanup_failed" : cancelled ? "cancelled" : passed ? "passed"
                    : ("setup".equals(operation) || "import".equals(operation)) ? guest.optString("status", "failed")
                    : guest.optBoolean("passed") ? "client_incomplete" : "failed";
            wrapper.put("status", status);
            File target = new File(operationDir, (reopen ? "coh-character-reopen-" : "coh-character-creation-") + runId + ".zip");
            File part = new File(operationDir, "support.zip.part");
            try (ZipOutputStream out = new ZipOutputStream(new FileOutputStream(part))) {
                if (imported != null) wrapper.put("import", new JSONObject().put("generation", imported.generation)
                        .put("source_commit", imported.sourceCommit).put("data_commit", imported.dataCommit)
                        .put("repository_commit", imported.repositoryCommit).put("files", imported.count).put("bytes", imported.bytes));
                zipText(out, "android-client-report.json", wrapper.toString(2));
                synchronized (this) { for (int i=0;i<surfacePngs.size();i++)
                    zipBytes(out, "android-surface/capture-" + (i+1) + ".png", surfacePngs.get(i)); }
                synchronized (this) { for (int i=0;i<loginPngs.size();i++)
                    zipBytes(out, "android-login/capture-" + (i+1) + ".png", loginPngs.get(i)); }
                synchronized (this) { for (int i=0;i<connectedPngs.size();i++)
                    zipBytes(out, "android-connected/capture-" + (i+1) + ".png", connectedPngs.get(i)); }
                synchronized (this) { for (int i=0;i<relocationPngs.size();i++)
                    zipBytes(out, "android-relocated/capture-" + (i+1) + ".png", relocationPngs.get(i)); }
                synchronized (this) { for (int i=0;i<characterPngs.size();i++)
                    zipBytes(out, "android-character/capture-" + (i+1) + ".png", characterPngs.get(i)); }
                synchronized (this) { for (int i=0;i<interactionPngs.size();i++)
                    zipBytes(out, (String) interactionSamples.get(i).get("archive_path"), interactionPngs.get(i)); }
                synchronized (this) { for (int i=0;i<contactPngs.size();i++)
                    zipBytes(out, (String) contactSamples.get(i).get("archive_path"), contactPngs.get(i)); }
                synchronized (this) { for (int i=0;i<taskPngs.size();i++)
                    zipBytes(out, (String) taskSamples.get(i).get("archive_path"), taskPngs.get(i)); }
                synchronized (this) { zipText(out, "operation.log", log.toString()); }
                zipText(out, "runtime-setup-service.json", ClientService.setupMemoryEvidence(context).toString());
                if (manifest != null) zipText(out, "runtime-manifest.json", manifest.toString(2));
                if (generation != null) {
                    File assets = new File(generation, "assets");
                    File[] identities = assets.listFiles((dir, name) -> name.endsWith("manifest.json") && !name.equals("runtime-manifest.json"));
                    if (identities != null) for (File file : identities) {
                        if ("atlas-world-supplement-manifest.json".equals(file.getName())) {
                            // Keep the larger donor inventory raw. The runtime file pin
                            // and compact guest world receipt bind its SHA-256; never
                            // parse or embed the multi-megabyte document in the wrapper.
                            zipFile(out, "identities/" + file.getName(), file, MAX_WORLD_IDENTITY);
                        } else if (file.length() <= MAX_JSON)
                            zipBytes(out, "identities/" + file.getName(), read(file, MAX_JSON));
                    }
                }
                try (InputStream in = context.getAssets().open("runtime/runtime-lock.json")) {
                    zipBytes(out, "runtime-lock.json", read(in, MAX_JSON));
                }
                try (InputStream in = context.getAssets().open("atlas/atlas-import.properties")) {
                    zipBytes(out, "atlas-import.properties", read(in, 16384));
                }
                if (("character_creation".equals(operation) || "character_reopen".equals(operation)) && runLaunched) {
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
