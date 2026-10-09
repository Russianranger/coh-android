package io.github.russianranger.cohatlastest;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.content.pm.ServiceInfo;
import android.net.Uri;
import android.os.Binder;
import android.os.Build;
import android.os.CancellationSignal;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.ParcelFileDescriptor;
import android.os.PowerManager;
import android.os.SystemClock;
import io.github.russianranger.cohatlas.AtlasAssetImporter;
import io.github.russianranger.cohdiagnostic.AtlasGameRuntime;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** One foreground owner serializes runtime setup, content import, and server tests. */
public final class AtlasGameService extends Service {
    public static final String ACTION_SETUP = "io.github.russianranger.cohatlastest.SETUP";
    public static final String ACTION_IMPORT = "io.github.russianranger.cohatlastest.IMPORT";
    public static final String ACTION_TEST = "io.github.russianranger.cohatlastest.TEST";
    public static final String ACTION_STOP = "io.github.russianranger.cohatlastest.STOP";
    private static final String CHANNEL = "atlas_test";
    private static final int NOTIFICATION_ID = 40;
    private static final int MAX_LOG = 16000, MAX_LIFECYCLE = 16000;
    private static final String CLEANUP_MESSAGE = "The owned runtime could not be proved stopped. Export the latest report, force-stop COH Atlas Test in Android settings, then reopen it before starting more work.";

    enum Kind {
        SETUP("runtime_setup", 45), IMPORT("verified_content_import", 90), TEST("atlas_server_test", 94);
        final String reportName; final long limitMs;
        Kind(String reportName, int minutes) { this.reportName = reportName; limitMs = minutes * 60000L; }
    }

    public interface Listener { void onState(State state); }
    public static final class State {
        public final boolean busy, stopping, initializing, contentReady, blocked;
        public final String stage, detail, prepared, log;
        public final long bytesDone, totalBytes;
        public final File report;
        State(boolean busy, boolean stopping, boolean initializing, boolean contentReady, boolean blocked,
              String stage, String detail, String prepared, String log, long bytesDone,
              long totalBytes, File report) {
            this.busy = busy; this.stopping = stopping; this.initializing = initializing;
            this.contentReady = contentReady; this.blocked = blocked; this.stage = stage; this.detail = detail;
            this.prepared = prepared; this.log = log; this.bytesDone = bytesDone;
            this.totalBytes = totalBytes; this.report = report;
        }
    }
    public final class LocalBinder extends Binder { public AtlasGameService getService() { return AtlasGameService.this; } }
    private static final class Operation {
        final String runId = UUID.randomUUID().toString();
        final long started = System.currentTimeMillis(), elapsedStart = SystemClock.elapsedRealtime();
        final AtlasAssetImporter.Control importControl = new AtlasAssetImporter.Control();
        final AtlasGameRuntime.Control runtimeControl = new AtlasGameRuntime.Control();
        final CancellationSignal openSignal = new CancellationSignal();
        final Kind kind; final Uri source;
        final StringBuilder log = new StringBuilder(), lifecycle = new StringBuilder();
        InputStream input; Thread thread; AtlasGameRuntime runtime;
        boolean finished;
        volatile String phase = "Preparing operation", explanation = "Please wait…";
        volatile long filesDone, totalFiles, bytesDone, totalBytes;
        long lastPosted;
        Operation(Kind kind, Uri source) { this.kind = kind; this.source = source; }
        boolean cancelled() { return kind == Kind.IMPORT ? importControl.isCancelled() : runtimeControl.cancelled(); }
    }
    private final IBinder binder = new LocalBinder();
    private final Handler main = new Handler(Looper.getMainLooper());
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final ExecutorService stopper = Executors.newSingleThreadExecutor();
    private final ExecutorService providerStopper = Executors.newSingleThreadExecutor();
    private final List<Listener> listeners = new ArrayList<>();
    private final AtlasOperationDispatch<Operation> dispatch = new AtlasOperationDispatch<>();
    private SharedPreferences preferences;
    private File home;
    private PowerManager.WakeLock wakeLock;
    private Operation operation;
    private Runnable deadline;
    private boolean busy, stopping, initializing = true, destroyed, uiVisible;
    private String stage = "Checking saved state", detail = "Please wait…", prepared = "", log = "";
    private long bytesDone, totalBytes;
    private File latestReport;
    private AtlasAssetImporter.Summary availableContent;
    private final BroadcastReceiver screenEvents = new BroadcastReceiver() {
        @Override public void onReceive(Context context, Intent intent) {
            if (busy && operation != null) lifecycle(operation, "screen_event=" + intent.getAction());
        }
    };

    @Override public void onCreate() {
        super.onCreate();
        try { home = new File(getFilesDir().getCanonicalFile(), "atlas-game"); }
        catch (IOException failure) { throw new IllegalStateException("Cannot resolve private app storage", failure); }
        preferences = getSharedPreferences("atlas_game", MODE_PRIVATE);
        latestReport = existingReport(preferences.getString("report", ""));
        NotificationChannel channel = new NotificationChannel(CHANNEL, "Atlas Park test", NotificationManager.IMPORTANCE_LOW);
        channel.setDescription("Progress and Stop for runtime setup, content import and local server testing");
        getSystemService(NotificationManager.class).createNotificationChannel(channel);
        IntentFilter filter = new IntentFilter(Intent.ACTION_SCREEN_ON);
        filter.addAction(Intent.ACTION_SCREEN_OFF); filter.addAction(Intent.ACTION_USER_PRESENT);
        if (Build.VERSION.SDK_INT >= 33) registerReceiver(screenEvents, filter, Context.RECEIVER_NOT_EXPORTED);
        else registerReceiver(screenEvents, filter);
        worker.execute(this::inspectSavedState);
    }

    private AtlasAssetImporter importer() throws IOException {
        return new AtlasAssetImporter(new File(home, "content"), name -> getAssets().open("atlas/" + name));
    }

    private void inspectSavedState() {
        boolean interrupted = preferences.getBoolean("busy", false);
        AtlasAssetImporter.Summary content = null;
        File report = latestReport;
        String nextStage = preferences.getString("stage", "Ready for setup");
        String nextDetail = preferences.getString("detail", "Set up the runtime, import game assets, then run the Atlas test.");
        try { content = importer().inspect(); }
        catch (Exception failure) {
            nextStage = "Content needs attention";
            nextDetail = "Saved content could not be verified. Import the reviewed archive again.";
        }
        if (interrupted) {
            String kind = preferences.getString("operation", "unknown");
            boolean interruptedServer = Kind.TEST.reportName.equals(kind);
            nextStage = "Previous operation interrupted";
            nextDetail = "The previous attempt was interrupted and is not a pass. Nothing restarted automatically. Export this report, then retry the operation.";
            if (interruptedServer) {
                // A Java-only crash does not prove that its PRoot children
                // stopped. Prevent imports from reclaiming content that an
                // orphan might still use, as well as preventing another test.
                AtlasGameRuntime.markCleanupUncertain();
                nextStage = "Interrupted server needs cleanup";
                nextDetail = CLEANUP_MESSAGE + " The interrupted test is not a pass.";
            }
            try {
                String previous = preferences.getString("run_id", "");
                if (!previous.matches("[0-9a-f-]{36}")) previous = "unknown";
                report = AtlasGameReports.write(this, home, UUID.randomUUID().toString(), kind,
                        "interrupted", nextDetail, preferences.getLong("started", 0), "Interrupted before completion",
                        0, 0, 0, 0, content, interruptedServer ? "UncertainRuntimeOwnership" : null, previous,
                        "The app reopened after unfinished work. No operation restarted automatically.\n", "", null);
            } catch (Exception failure) { report = null; nextDetail += " A fresh report could not be saved."; }
            preferences.edit().putBoolean("busy", false).putString("stage", nextStage)
                    .putString("detail", nextDetail).putString("report", report == null ? "" : report.getAbsolutePath()).commit();
        }
        final AtlasAssetImporter.Summary inspected = content;
        final File recoveredReport = report;
        final String recoveredStage = nextStage, recoveredDetail = nextDetail;
        main.post(() -> {
            if (destroyed) return;
            availableContent = inspected; latestReport = recoveredReport;
            prepared = prepared(inspected); initializing = false;
            Operation queued = dispatch.initialized();
            if (queued != null) begin(queued);
            else { stage = recoveredStage; detail = recoveredDetail; notifyState(); }
        });
    }

    @Override public IBinder onBind(Intent intent) { return binder; }
    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent == null ? "" : intent.getAction();
        if (ACTION_STOP.equals(action)) {
            requestStop("Stopping the current operation and cleaning up its unfinished work.");
            if (!busy) stopSelf();
            return START_NOT_STICKY;
        }
        Kind kind = ACTION_SETUP.equals(action) ? Kind.SETUP : ACTION_IMPORT.equals(action) ? Kind.IMPORT
                : ACTION_TEST.equals(action) ? Kind.TEST : null;
        if (kind == null) { if (!busy) stopSelf(); return START_NOT_STICKY; }
        if (busy) return START_NOT_STICKY;
        if (AtlasGameRuntime.cleanupBlocked()) {
            foreground(); stopForeground(STOP_FOREGROUND_REMOVE); stopSelf();
            stage = "Cleanup needs attention"; detail = CLEANUP_MESSAGE; notifyState();
            return START_NOT_STICKY;
        }
        Uri source = intent.getData();
        if (kind == Kind.IMPORT && (source == null || !"content".equals(source.getScheme()))) {
            foreground(); stopForeground(STOP_FOREGROUND_REMOVE); stopSelf();
            if (!initializing) { stage = "Choose an archive"; detail = "Use Import game assets to choose a file through Android's document picker."; notifyState(); }
            return START_NOT_STICKY;
        }
        Operation next = new Operation(kind, source);
        if (dispatch.offer(next)) {
            operation = next; busy = true; stopping = false; log = ""; bytesDone = totalBytes = 0;
            latestReport = null;
            stage = "Preparing operation";
            detail = initializing ? "Checking saved state before starting…" : "Preparing the selected operation…";
            PowerManager power = (PowerManager) getSystemService(POWER_SERVICE);
            lifecycle(next, "operation_requested kind=" + kind.reportName + " ui_visible=" + uiVisible + " screen_interactive=" + power.isInteractive());
            // The picker may destroy a bound-only service. Start foreground
            // immediately and keep the request until asynchronous inspection ends.
            foreground(); notifyState();
            Operation ready = dispatch.takeReady();
            if (ready != null) begin(ready);
        }
        return START_NOT_STICKY;
    }

    public State snapshot() { return new State(busy, stopping, initializing, availableContent != null, AtlasGameRuntime.cleanupBlocked(), stage, detail, prepared, log, bytesDone, totalBytes, latestReport); }
    public void addListener(Listener listener) { if (!listeners.contains(listener)) listeners.add(listener); listener.onState(snapshot()); }
    public void removeListener(Listener listener) { listeners.remove(listener); }
    public void setUiVisible(boolean visible) {
        if (uiVisible == visible) return;
        uiVisible = visible;
        if (busy && operation != null) lifecycle(operation, "activity_visible=" + visible);
    }

    private void begin(Operation current) {
        // Initialization may discover an interrupted server after this request
        // was queued. Recheck before clearing its fresh interrupted report or
        // starting any new setup, import, or runtime work.
        if (AtlasGameRuntime.cleanupBlocked()) {
            busy = false; stopping = false; dispatch.finish(current);
            stage = "Cleanup needs attention"; detail = CLEANUP_MESSAGE;
            stopForeground(STOP_FOREGROUND_REMOVE); stopSelf(); notifyState(); return;
        }
        latestReport = null;
        if (!stopping) { stage = "Preparing operation"; detail = "You can leave this screen. Use Stop to cancel."; }
        // Persist the attempt before opening a provider or starting native work.
        if (!preferences.edit().putBoolean("busy", true).putString("run_id", current.runId)
                .putString("operation", current.kind.reportName).putLong("started", current.started)
                .putString("report", "").commit()) {
            busy = false; stage = "Could not start"; detail = "The app could not save its operation state. Check free storage and retry.";
            dispatch.finish(current); stopForeground(STOP_FOREGROUND_REMOVE); stopSelf(); notifyState(); return;
        }
        PowerManager manager = (PowerManager) getSystemService(POWER_SERVICE);
        wakeLock = manager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "COHAtlas:serverTest");
        wakeLock.acquire(current.kind.limitMs + 60000);
        deadline = () -> { if (operation == current && busy) requestStop("The operation reached its " + current.kind.limitMs / 60000 + "-minute limit. Stopping unfinished work."); };
        main.postDelayed(deadline, current.kind.limitMs);
        notifyState(); worker.execute(() -> execute(current));
    }

    private void execute(Operation current) {
        synchronized (current) { current.thread = Thread.currentThread(); }
        AtlasAssetImporter engine = null;
        AtlasAssetImporter.Summary content = availableContent;
        String status = "failed", message = "The operation did not complete.", errorType = null;
        File report = null, runtimeReport = null;
        try {
            if (current.kind == Kind.IMPORT) {
                engine = importer();
                if (current.cancelled()) throw new AtlasAssetImporter.CancelledException();
                ParcelFileDescriptor descriptor = getContentResolver().openFileDescriptor(current.source, "r", current.openSignal);
                if (descriptor == null) throw new IOException("Selected document is unavailable");
                InputStream input = new ParcelFileDescriptor.AutoCloseInputStream(descriptor);
                synchronized (current) { current.input = input; }
                if (current.cancelled()) throw new AtlasAssetImporter.CancelledException();
                content = engine.importArchive(input,
                        (phase, done, count, bytes, total) -> updateProgress(current, phase, done, count, bytes, total), current.importControl);
                status = "passed"; message = "All " + number(content.count) + " files verified. Set up the runtime if needed, then run the Atlas test.";
            } else {
                AtlasGameRuntime runtime = new AtlasGameRuntime(this, new AtlasGameRuntime.Listener() {
                    @Override public void onStage(String phase, String explanation) { runtimeProgress(current, phase, explanation); }
                    @Override public void onLog(String line) { runtimeLog(current, line); }
                }, current.runtimeControl);
                synchronized (current) { current.runtime = runtime; }
                if (current.kind == Kind.SETUP) {
                    runtime.setupRuntime(); status = "setup_complete";
                    message = "Runtime is ready. Import game assets if needed, then run the Atlas test.";
                } else {
                    engine = importer(); content = engine.inspect();
                    if (content == null) throw new IOException("A completed content import is required");
                    AtlasGameRuntime.Result result = runtime.runGameProbe(content.dataDirectory.getParentFile());
                    status = result.passed ? "passed" : "failed"; message = result.summary;
                }
                runtimeReport = runtime.getLatestReport();
            }
        } catch (Exception failure) {
            status = current.cancelled() ? "cancelled" : "failed";
            message = "cancelled".equals(status) ? stoppedMessage(current) : friendlyFailure(current, failure);
            errorType = failure.getClass().getSimpleName();
        } finally {
            Thread.interrupted();
            InputStream opened;
            synchronized (current) { opened = current.input; current.input = null; }
            if (opened != null) try { opened.close(); } catch (IOException ignored) { }
            if (current.kind == Kind.IMPORT && !"passed".equals(status) && engine != null) {
                try { content = engine.inspect(); } catch (Exception ignored) { content = null; }
            }
            synchronized (current) {
                if (current.runtime != null) runtimeReport = current.runtime.getLatestReport();
                if (AtlasGameRuntime.cleanupBlocked()) { status = "cleanup_failed"; message = CLEANUP_MESSAGE; }
                else if (current.cancelled()) { status = "cancelled"; message = stoppedMessage(current); }
                lifecycle(current, "operation_finished status=" + status);
                current.finished = true; current.thread = null;
            }
            append(current, message);
            try {
                report = AtlasGameReports.write(this, home, current.runId, current.kind.reportName,
                        status, message, current.started, current.phase, current.filesDone, current.totalFiles,
                        current.bytesDone, current.totalBytes, content, errorType, null,
                        logSnapshot(current), lifecycleSnapshot(current), runtimeReport);
            } catch (Exception failure) { message += " A fresh support report could not be saved. Check free storage."; }
            Thread.interrupted();
            final String terminalStatus = status, terminalMessage = message;
            final File terminalReport = report;
            final AtlasAssetImporter.Summary terminalContent = content;
            main.post(() -> finish(current, terminalStatus, terminalMessage, terminalContent, terminalReport));
        }
    }

    private void updateProgress(Operation current, String phase, long done, long count, long bytes, long total) {
        boolean changed = !phase.equals(current.phase);
        current.phase = phase; current.filesDone = done; current.totalFiles = count; current.bytesDone = bytes; current.totalBytes = total;
        if (changed) append(current, phase);
        long now = SystemClock.elapsedRealtime();
        if (!changed && now - current.lastPosted < 250) return;
        current.lastPosted = now;
        String explanation = (count > 0 ? number(done) + " / " + number(count) + " files" : "")
                + (total > 0 ? (count > 0 ? " · " : "") + mib(bytes) + " / " + mib(total) + " MiB" : "");
        postProgress(current, phase, explanation.isEmpty() ? "Preparing game content…" : explanation, bytes, total);
    }

    private void runtimeProgress(Operation current, String phase, String explanation) {
        current.phase = phase; current.explanation = explanation;
        current.lastPosted = SystemClock.elapsedRealtime();
        append(current, phase + ": " + explanation);
        postProgress(current, phase, explanation, 0, 0);
    }

    private void runtimeLog(Operation current, String line) {
        append(current, line);
        long now = SystemClock.elapsedRealtime();
        if (now - current.lastPosted < 500) return;
        current.lastPosted = now;
        postProgress(current, current.phase, current.explanation, 0, 0);
    }

    private void postProgress(Operation current, String phase, String explanation, long bytes, long total) {
        final String progressLog = logSnapshot(current);
        main.post(() -> {
            if (operation != current || destroyed || !busy) return;
            bytesDone = bytes; totalBytes = total; log = progressLog;
            if (!stopping) { stage = phase; detail = explanation; }
            notifyState();
        });
    }

    private void finish(Operation current, String status, String message, AtlasAssetImporter.Summary content, File report) {
        if (operation != current) return;
        if (deadline != null) main.removeCallbacks(deadline);
        releaseWakeLock(); busy = false; stopping = false; dispatch.finish(current);
        availableContent = content; prepared = prepared(content); log = logSnapshot(current);
        stage = "cleanup_failed".equals(status) ? "Cleanup needs attention" : "setup_complete".equals(status) ? "Runtime ready" : "passed".equals(status)
                ? current.kind == Kind.IMPORT ? "Content ready" : "Atlas test passed"
                : "cancelled".equals(status) ? "Operation stopped" : "Operation failed";
        detail = message; latestReport = report;
        preferences.edit().putBoolean("busy", false).putString("stage", stage).putString("detail", detail)
                .putString("report", report == null ? "" : report.getAbsolutePath()).commit();
        if (!destroyed) notifyState();
        stopForeground(STOP_FOREGROUND_REMOVE); stopSelf();
    }

    private void requestStop(String reason) {
        if (!busy || stopping || operation == null) return;
        Operation current = operation;
        synchronized (current) {
            if (current.finished) return;
            boolean accepted = current.kind == Kind.IMPORT ? current.importControl.requestCancel() : current.runtimeControl.requestStop();
            if (!accepted) return;
            lifecycle(current, "stop_requested");
        }
        stopping = true; stage = "Stopping operation"; detail = reason; notifyState();
        stopper.execute(() -> {
            InputStream opened; AtlasGameRuntime runtime;
            synchronized (current) {
                if (current.finished) return;
                if (current.thread != null) current.thread.interrupt();
                opened = current.input; runtime = current.runtime;
            }
            if (runtime != null) runtime.requestStop();
            if (opened != null) try { opened.close(); } catch (IOException ignored) { }
        });
        if (current.kind == Kind.IMPORT) providerStopper.execute(current.openSignal::cancel);
    }

    private static String stoppedMessage(Operation current) {
        return current.kind == Kind.IMPORT ? "Import stopped. Previously completed content remains available; select the archive to retry."
                : "Operation stopped. Export the latest report, then rerun the operation when ready.";
    }
    private static String friendlyFailure(Operation current, Exception failure) {
        String raw = failure.getMessage() == null ? "" : failure.getMessage().toLowerCase(Locale.ROOT);
        if (raw.contains("space") || raw.contains("enospc") || raw.contains("storage filled") || raw.contains("gib free"))
            return "There is not enough free internal storage. Free space and retry. Setup needs 8 GiB free, import needs 5 GiB, and the Atlas test needs 6 GiB after setup and import.";
        if (current.kind != Kind.IMPORT) {
            if (raw.contains("completed content import")) return "Import game assets in this app before running the Atlas test.";
            if (raw.contains("set up the runtime first")) return "Set up the runtime in this app before running the Atlas test.";
            return "The operation did not pass. Review the progress below and export the latest report before retrying.";
        }
        if (raw.contains("hash") || raw.contains("digest") || raw.contains("checksum") || raw.contains("archive") || raw.contains("size"))
            return "The selected archive did not match the reviewed assets or could not be read completely. Choose the original coh-reference-assets.zip and retry.";
        if (failure instanceof SecurityException) return "Android could not read the selected file. Choose the archive again through the document picker.";
        return "Content preparation failed. Choose the original asset ZIP and retry, then export the report if it fails again.";
    }
    private static String number(long value) { return String.format(Locale.US, "%,d", value); }
    private static String mib(long value) { return number(value / 1048576); }
    private static String prepared(AtlasAssetImporter.Summary content) {
        return content == null ? "No completed content import is available in this app." : "Accepted content: " + number(content.count)
                + " files · " + mib(content.bytes) + " MiB. The graphical game client is not included.";
    }
    private static void append(Operation current, String line) {
        synchronized (current) {
            current.log.append(line).append('\n');
            if (current.log.length() > MAX_LOG) current.log.delete(0, current.log.length() - MAX_LOG);
        }
    }
    private static String logSnapshot(Operation current) { synchronized (current) { return current.log.toString(); } }
    private static String lifecycleSnapshot(Operation current) { synchronized (current) { return current.lifecycle.toString(); } }
    private static void lifecycle(Operation current, String event) {
        synchronized (current) {
            if (current.finished) return;
            String line = System.currentTimeMillis() + " elapsed_ms=" + (SystemClock.elapsedRealtime() - current.elapsedStart) + " " + event + "\n";
            if (current.lifecycle.length() + line.length() < MAX_LIFECYCLE) current.lifecycle.append(line);
        }
    }
    private File existingReport(String path) {
        if (path.isEmpty()) return null;
        try { File value = new File(path); return value.isFile() && value.getCanonicalPath().startsWith(new File(home, "reports").getCanonicalPath() + File.separator) ? value : null; }
        catch (IOException failure) { return null; }
    }
    private void notifyState() {
        State current = snapshot();
        for (Listener listener : new ArrayList<>(listeners)) listener.onState(current);
        if (busy && !destroyed) getSystemService(NotificationManager.class).notify(NOTIFICATION_ID, notification());
    }
    private void foreground() {
        if (Build.VERSION.SDK_INT >= 34) startForeground(NOTIFICATION_ID, notification(), ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE);
        else startForeground(NOTIFICATION_ID, notification());
    }
    private Notification notification() {
        PendingIntent open = PendingIntent.getActivity(this, 0, new Intent(this, AtlasActivity.class), PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        PendingIntent stop = PendingIntent.getService(this, 1, new Intent(this, AtlasGameService.class).setAction(ACTION_STOP), PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        return new Notification.Builder(this, CHANNEL).setSmallIcon(android.R.drawable.stat_notify_sync)
                .setContentTitle("COH Atlas Test — " + stage).setContentText(detail).setContentIntent(open)
                .setOnlyAlertOnce(true).setOngoing(true).addAction(new Notification.Action.Builder(null, "Stop", stop).build()).build();
    }
    private void releaseWakeLock() { if (wakeLock != null && wakeLock.isHeld()) wakeLock.release(); wakeLock = null; }
    @Override public void onDestroy() {
        if (busy) requestStop("The service is stopping; cancelling unfinished work.");
        destroyed = true; listeners.clear(); unregisterReceiver(screenEvents);
        if (deadline != null) main.removeCallbacks(deadline);
        releaseWakeLock(); worker.shutdown(); stopper.shutdown(); providerStopper.shutdown(); super.onDestroy();
    }
}
