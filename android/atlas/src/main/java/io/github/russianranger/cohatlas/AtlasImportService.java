package io.github.russianranger.cohatlas;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
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

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Owns an explicitly started import independently of the screen lifecycle. */
public final class AtlasImportService extends Service {
    public static final String ACTION_IMPORT = "io.github.russianranger.cohatlas.IMPORT";
    public static final String ACTION_STOP = "io.github.russianranger.cohatlas.STOP";
    private static final String CHANNEL = "atlas_import";
    private static final int NOTIFICATION_ID = 30;
    private static final long IMPORT_LIMIT_MS = 90L * 60 * 1000;
    private static final int MAX_LOG = 12000;

    public interface Listener { void onState(State state); }
    public static final class State {
        public final boolean busy, stopping, initializing;
        public final String stage, detail, prepared, log;
        public final long bytesDone, totalBytes;
        public final File report;
        State(boolean busy, boolean stopping, boolean initializing, String stage, String detail,
              String prepared, String log, long bytesDone, long totalBytes, File report) {
            this.busy = busy; this.stopping = stopping; this.initializing = initializing;
            this.stage = stage; this.detail = detail; this.prepared = prepared; this.log = log;
            this.bytesDone = bytesDone; this.totalBytes = totalBytes; this.report = report;
        }
    }
    public final class LocalBinder extends Binder { public AtlasImportService getService() { return AtlasImportService.this; } }
    private static final class Operation {
        final String runId = UUID.randomUUID().toString();
        final long started = System.currentTimeMillis();
        final AtlasAssetImporter.Control control = new AtlasAssetImporter.Control();
        final CancellationSignal openSignal = new CancellationSignal();
        final Uri source;
        final StringBuilder log = new StringBuilder();
        InputStream input;
        Thread thread;
        boolean finished;
        volatile String phase = "Opening selected archive";
        volatile long filesDone, totalFiles, bytesDone, totalBytes;
        long lastPosted;
        Operation(Uri source) { this.source = source; }
    }
    private final IBinder binder = new LocalBinder();
    private final Handler main = new Handler(Looper.getMainLooper());
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final ExecutorService stopper = Executors.newSingleThreadExecutor();
    private final ExecutorService providerStopper = Executors.newSingleThreadExecutor();
    private final List<Listener> listeners = new ArrayList<>();
    private final AtlasImportDispatch<Operation> dispatch = new AtlasImportDispatch<>();
    private SharedPreferences preferences;
    private File home;
    private PowerManager.WakeLock wakeLock;
    private Operation operation;
    private Runnable deadline;
    private boolean busy, stopping, initializing = true, destroyed;
    private String stage = "Checking saved state", detail = "Please wait…", prepared = "", log = "";
    private long bytesDone, totalBytes;
    private File latestReport;
    private AtlasAssetImporter.Summary availableContent;

    @Override public void onCreate() {
        super.onCreate();
        // Android can expose private app storage through /data/user/0 aliases.
        // Resolve that framework-owned root before the importer rejects links
        // in content paths below it.
        try { home = new File(getFilesDir().getCanonicalFile(), "atlas"); }
        catch (IOException failure) { throw new IllegalStateException("Cannot resolve private app storage", failure); }
        preferences = getSharedPreferences("atlas_import", MODE_PRIVATE);
        latestReport = existingReport(preferences.getString("report", ""));
        NotificationChannel channel = new NotificationChannel(CHANNEL, "Game content import", NotificationManager.IMPORTANCE_LOW);
        channel.setDescription("Progress and Stop for user-started game content import");
        getSystemService(NotificationManager.class).createNotificationChannel(channel);
        worker.execute(this::inspectSavedState);
    }

    private AtlasAssetImporter importer() throws IOException {
        return new AtlasAssetImporter(new File(home, "content"), name -> getAssets().open("atlas/" + name));
    }

    private void inspectSavedState() {
        boolean interrupted = preferences.getBoolean("busy", false);
        AtlasAssetImporter.Summary content = null;
        File report = latestReport;
        String nextStage = preferences.getString("stage", "Ready to import");
        String nextDetail = preferences.getString("detail", "Choose the reviewed game asset ZIP to prepare the content.");
        try { content = importer().inspect(); }
        catch (Exception failure) {
            nextStage = "Content needs attention";
            nextDetail = "Saved content could not be verified. Import the reviewed archive again; export a report if the problem continues.";
        }
        if (interrupted) {
            nextStage = "Previous import interrupted";
            nextDetail = "The interrupted attempt was not accepted as a pass. Choose Import to retry; partial work is cleared before the next import.";
            try {
                String previous = preferences.getString("run_id", "");
                if (!previous.matches("[0-9a-f-]{36}")) previous = "unknown";
                report = AtlasImportReports.write(this, home, UUID.randomUUID().toString(), "interrupted", nextDetail,
                        preferences.getLong("started", 0), "Interrupted before completion", 0, 0, 0, 0,
                        content, null, previous, "The app reopened after an unfinished import. No import was restarted automatically.\n");
                preferences.edit().putBoolean("busy", false).putString("stage", nextStage)
                        .putString("detail", nextDetail).putString("report", report.getAbsolutePath()).commit();
            } catch (Exception failure) { report = null; nextDetail += " A fresh report could not be saved."; }
        }
        if (content == null && "Content ready".equals(nextStage)) {
            nextStage = "Ready to import"; nextDetail = "No completed content import is available. Choose the reviewed asset ZIP.";
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
        if (ACTION_STOP.equals(action)) { requestStop("Stopping the import and removing unfinished files."); if (!busy) stopSelf(); }
        else if (ACTION_IMPORT.equals(action)) {
            if (busy) return START_NOT_STICKY;
            Uri source = intent.getData();
            if (source == null || !"content".equals(source.getScheme())) {
                foreground(); stopForeground(STOP_FOREGROUND_REMOVE); stopSelf();
                if (!initializing) { stage = "Choose an archive"; detail = "Use Import game assets to choose a file through Android's document picker."; notifyState(); }
            } else {
                Operation next = new Operation(source);
                if (dispatch.offer(next)) {
                    operation = next; busy = true; stopping = false; log = ""; bytesDone = totalBytes = 0;
                    stage = "Preparing content"; detail = initializing ? "Checking saved state before opening the selected archive…" : "Opening the selected archive…";
                    // A picker can destroy the previous bound-only service.
                    // Start foreground now and retain this request until the
                    // replacement instance completes its initial inspection.
                    foreground(); notifyState();
                    Operation ready = dispatch.takeReady();
                    if (ready != null) begin(ready);
                }
            }
        }
        return START_NOT_STICKY;
    }

    public State snapshot() { return new State(busy, stopping, initializing, stage, detail, prepared, log, bytesDone, totalBytes, latestReport); }
    public void addListener(Listener listener) { if (!listeners.contains(listener)) listeners.add(listener); listener.onState(snapshot()); }
    public void removeListener(Listener listener) { listeners.remove(listener); }

    private void begin(Operation current) {
        if (!stopping) { stage = "Preparing content"; detail = "You can leave this screen. Use Stop to cancel."; }
        // Commit before opening the provider so process death cannot hide a started attempt.
        if (!preferences.edit().putBoolean("busy", true).putString("run_id", current.runId)
                .putLong("started", current.started).commit()) {
            busy = false; stage = "Import could not start"; detail = "The app could not save its import state. Check free storage and retry.";
            dispatch.finish(current);
            stopForeground(STOP_FOREGROUND_REMOVE); stopSelf(); notifyState(); return;
        }
        PowerManager manager = (PowerManager) getSystemService(POWER_SERVICE);
        wakeLock = manager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "COHAtlas:contentImport");
        wakeLock.acquire(IMPORT_LIMIT_MS + 60000);
        deadline = () -> { if (operation == current && busy) requestStop("Import reached its 90-minute limit. Stopping unfinished work."); };
        main.postDelayed(deadline, IMPORT_LIMIT_MS);
        notifyState(); worker.execute(() -> execute(current));
    }

    private void execute(Operation current) {
        synchronized (current) { current.thread = Thread.currentThread(); }
        AtlasAssetImporter engine = null;
        AtlasAssetImporter.Summary content = availableContent;
        String status = "failed", message = "Import did not complete.", errorType = null;
        File report = null;
        try {
            engine = importer();
            if (current.control.isCancelled()) throw new AtlasAssetImporter.CancelledException();
            ParcelFileDescriptor descriptor = getContentResolver().openFileDescriptor(current.source, "r", current.openSignal);
            if (descriptor == null) throw new IOException("Selected document is unavailable");
            InputStream input = new ParcelFileDescriptor.AutoCloseInputStream(descriptor);
            synchronized (current) {
                current.input = input;
            }
            if (current.control.isCancelled()) throw new AtlasAssetImporter.CancelledException();
            content = engine.importArchive(input, (phase, done, count, bytes, total) -> updateProgress(current, phase, done, count, bytes, total), current.control);
            status = "passed";
            message = "All " + number(content.count) + " files were verified. Content is ready for the next server-integration milestone.";
        } catch (Exception failure) {
            status = current.control.isCancelled() ? "cancelled" : "failed";
            message = "cancelled".equals(status) ? "Import stopped. Previously accepted content remains available; select the archive to retry." : friendlyFailure(failure);
            errorType = failure.getClass().getSimpleName();
        } finally {
            // An interrupt is used only to unblock this operation, never the next executor task.
            Thread.interrupted();
            InputStream opened;
            synchronized (current) {
                opened = current.input;
                current.input = null;
            }
            if (opened != null) try { opened.close(); } catch (IOException ignored) { }
            if (!"passed".equals(status) && engine != null) {
                try { content = engine.inspect(); } catch (Exception ignored) { content = null; }
            }
            synchronized (current) {
                // Stop is sealed before writing an immutable terminal report.
                // A Stop accepted before this point must be reflected in it.
                current.finished = true; current.thread = null;
                if (current.control.isCancelled()) {
                    status = "cancelled";
                    message = "Import stopped. Previously accepted content remains available; select the archive to retry.";
                }
            }
            append(current, message);
            try {
                report = AtlasImportReports.write(this, home, current.runId, status, message, current.started,
                        current.phase, current.filesDone, current.totalFiles, current.bytesDone, current.totalBytes,
                        content, errorType, null, current.log.toString());
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
        long now = android.os.SystemClock.elapsedRealtime();
        if (!changed && now - current.lastPosted < 250) return;
        current.lastPosted = now;
        final String progressDetail = (count > 0 ? number(done) + " / " + number(count) + " files" : "")
                + (total > 0 ? (count > 0 ? " · " : "") + mib(bytes) + " / " + mib(total) + " MiB" : "");
        final String progressLog = current.log.toString();
        main.post(() -> {
            if (operation != current || destroyed || !busy) return;
            bytesDone = bytes; totalBytes = total; log = progressLog;
            if (!stopping) { stage = phase; detail = progressDetail.isEmpty() ? "Preparing game content…" : progressDetail; }
            notifyState();
        });
    }

    private void finish(Operation current, String status, String message, AtlasAssetImporter.Summary content, File report) {
        if (operation != current) return;
        if (deadline != null) main.removeCallbacks(deadline);
        releaseWakeLock(); busy = false; stopping = false;
        dispatch.finish(current);
        availableContent = content; prepared = prepared(content); log = current.log.toString();
        stage = "passed".equals(status) ? "Content ready" : "cancelled".equals(status) ? "Import stopped" : "Import failed";
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
            if (current.finished || !current.control.requestCancel()) return;
        }
        stopping = true; stage = "Stopping import"; detail = reason; notifyState();
        // A provider may block its synchronous cancellation callback. Keep it
        // independent of the local interrupt and descriptor close.
        stopper.execute(() -> {
            InputStream opened;
            synchronized (current) {
                if (current.finished) return;
                if (current.thread != null) current.thread.interrupt();
                opened = current.input;
            }
            if (opened != null) try { opened.close(); } catch (IOException ignored) { }
        });
        providerStopper.execute(current.openSignal::cancel);
    }

    private static String friendlyFailure(Exception failure) {
        String raw = failure.getMessage() == null ? "" : failure.getMessage().toLowerCase(Locale.ROOT);
        if (raw.contains("space") || raw.contains("enospc") || raw.contains("not enough internal storage") || raw.contains("storage filled"))
            return "There is not enough free internal storage. Free some space and retry the import.";
        if (raw.contains("hash") || raw.contains("digest") || raw.contains("checksum") || raw.contains("archive") || raw.contains("size"))
            return "The selected archive did not match the reviewed game assets, or could not be read completely. Select the original coh-reference-assets.zip and try again.";
        if (failure instanceof SecurityException) return "Android could not read the selected file. Choose the archive again through the document picker.";
        return "Content preparation failed. Choose the original asset ZIP and retry, then export the report if it fails again.";
    }
    private static String number(long value) { return String.format(Locale.US, "%,d", value); }
    private static String mib(long value) { return number(value / 1048576); }
    private static String prepared(AtlasAssetImporter.Summary content) {
        return content == null ? "No completed content import is available." : "Last accepted content: " + number(content.count)
                + " files · " + mib(content.bytes) + " MiB. Server execution and gameplay are not tested by this app.";
    }
    private static void append(Operation current, String line) {
        current.log.append(line).append('\n');
        if (current.log.length() > MAX_LOG) current.log.delete(0, current.log.length() - MAX_LOG);
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
        PendingIntent stop = PendingIntent.getService(this, 1, new Intent(this, AtlasImportService.class).setAction(ACTION_STOP), PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        return new Notification.Builder(this, CHANNEL).setSmallIcon(android.R.drawable.stat_notify_sync)
                .setContentTitle("COH Atlas Setup — " + stage).setContentText(detail).setContentIntent(open)
                .setOnlyAlertOnce(true).setOngoing(true).addAction(new Notification.Action.Builder(null, "Stop", stop).build()).build();
    }
    private void releaseWakeLock() { if (wakeLock != null && wakeLock.isHeld()) wakeLock.release(); wakeLock = null; }
    @Override public void onDestroy() {
        if (busy) requestStop("Import service is stopping; cancelling unfinished work.");
        destroyed = true; listeners.clear();
        if (deadline != null) main.removeCallbacks(deadline);
        releaseWakeLock(); worker.shutdown(); stopper.shutdown(); providerStopper.shutdown(); super.onDestroy();
    }
}
