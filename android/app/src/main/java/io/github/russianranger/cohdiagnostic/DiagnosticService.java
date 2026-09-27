package io.github.russianranger.cohdiagnostic;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.ServiceInfo;
import android.os.Binder;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.PowerManager;

import java.io.File;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

/** Owns one user-started operation independently of the Activity lifecycle. */
public final class DiagnosticService extends Service {
    public static final String ACTION_SETUP = "io.github.russianranger.cohdiagnostic.SETUP";
    public static final String ACTION_RUN = "io.github.russianranger.cohdiagnostic.RUN";
    public static final String ACTION_STOP = "io.github.russianranger.cohdiagnostic.STOP";
    private static final String CHANNEL = "diagnostic_progress";
    private static final int NOTIFICATION_ID = 1;
    private static final int MAX_LOG_CHARS = 64000;
    private static final long SETUP_LIMIT_MS = 45L * 60L * 1000L;
    // The runtime has its own 20 minute limit and needs time to stop its children.
    private static final long RUN_LIMIT_MS = 22L * 60L * 1000L;

    public interface Listener { void onState(State state); }

    public static final class State {
        public final boolean busy, stopping, setupComplete;
        public final String stage, detail, log;
        public final File report;
        private State(boolean busy, boolean stopping, boolean setupComplete,
                      String stage, String detail, String log, File report) {
            this.busy = busy;
            this.stopping = stopping;
            this.setupComplete = setupComplete;
            this.stage = stage;
            this.detail = detail;
            this.log = log;
            this.report = report;
        }
    }

    public final class LocalBinder extends Binder {
        public DiagnosticService getService() { return DiagnosticService.this; }
    }

    private final IBinder binder = new LocalBinder();
    private final Handler main = new Handler(Looper.getMainLooper());
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final ExecutorService stopper = Executors.newSingleThreadExecutor();
    private final List<Listener> listeners = new ArrayList<>();
    private final StringBuilder log = new StringBuilder();
    private static final class Operation {
        final AtomicBoolean stop = new AtomicBoolean(false);
        final File previousReport;
        // Accessed under this operation's monitor: a delayed Stop cannot
        // interrupt the reused executor thread during a later operation.
        DiagnosticRuntime runtime;
        Thread thread;
        boolean finished;
        Operation(File previousReport) { this.previousReport = previousReport; }
    }
    private Operation currentOperation;
    private SharedPreferences preferences;
    private PowerManager.WakeLock wakeLock;
    private boolean busy, stopping, setupComplete, destroyed, notificationPending;
    private String stage = "Ready", detail = "Set up the runtime to begin.";
    private File latestReport;
    private Runnable deadline;

    @Override public void onCreate() {
        super.onCreate();
        preferences = getSharedPreferences("diagnostic_state", MODE_PRIVATE);
        setupComplete = preferences.getBoolean("setup_complete", false);
        stage = preferences.getString("stage", "Ready");
        detail = preferences.getString("detail", setupComplete ? "Ready to run diagnostics." : detail);
        String savedPath = preferences.getString("report", "");
        if (!savedPath.isEmpty()) {
            File candidate = new File(savedPath);
            try {
                if (candidate.getCanonicalPath().startsWith(getFilesDir().getCanonicalPath() + File.separator)
                        && candidate.isFile()) latestReport = candidate;
            } catch (Exception ignored) { /* An unavailable old report is not exportable. */ }
        }
        if (preferences.getBoolean("busy", false)) {
            stage = "Previous operation interrupted";
            detail = "Run diagnostics again, or export the last available report.";
            preferences.edit().putBoolean("busy", false).apply();
        }
        NotificationChannel channel = new NotificationChannel(CHANNEL, "Runtime diagnostics", NotificationManager.IMPORTANCE_LOW);
        channel.setDescription("Progress and Stop control for user-started runtime diagnostics");
        getSystemService(NotificationManager.class).createNotificationChannel(channel);
    }

    @Override public IBinder onBind(Intent intent) { return binder; }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent == null ? "" : intent.getAction();
        if (ACTION_STOP.equals(action)) {
            requestStop("Stop requested. Waiting for owned processes to finish.");
            if (!busy) stopSelf();
        } else if (ACTION_SETUP.equals(action) || ACTION_RUN.equals(action)) {
            if (!busy) begin(ACTION_SETUP.equals(action));
        }
        // A killed process must never silently restart an interrupted test.
        return START_NOT_STICKY;
    }

    public State snapshot() {
        return new State(busy, stopping, setupComplete, stage, detail, log.toString(), latestReport);
    }

    public void addListener(Listener listener) {
        if (!listeners.contains(listener)) listeners.add(listener);
        listener.onState(snapshot());
    }

    public void removeListener(Listener listener) { listeners.remove(listener); }

    private void begin(boolean setup) {
        if (!setup && !setupComplete) {
            stage = "Setup needed";
            detail = "Choose Setup runtime before running diagnostics.";
            notifyState();
            // Satisfy startForegroundService even when a stale caller starts Run.
            foreground();
            stopForeground(STOP_FOREGROUND_REMOVE);
            stopSelf();
            return;
        }
        busy = true;
        stopping = false;
        stage = setup ? "Setting up runtime" : "Running diagnostics";
        detail = "You can leave this screen. Use Stop to cancel.";
        log.setLength(0);
        final Operation operation = new Operation(latestReport);
        currentOperation = operation;
        preferences.edit().putBoolean("busy", true).apply();
        foreground();
        long limit = setup ? SETUP_LIMIT_MS : RUN_LIMIT_MS;
        PowerManager manager = (PowerManager) getSystemService(POWER_SERVICE);
        wakeLock = manager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "COHDiagnostic:operation");
        wakeLock.acquire(limit + 30000L);
        deadline = () -> {
            if (busy && currentOperation == operation) requestStop("Operation reached its time limit. Stopping owned work.");
        };
        main.postDelayed(deadline, limit);
        notifyState();
        worker.execute(() -> execute(setup, operation));
    }

    private void execute(boolean setup, Operation operation) {
        synchronized (operation) { operation.thread = Thread.currentThread(); }
        DiagnosticRuntime runtime = null;
        File report = operation.previousReport;
        boolean passed = false;
        String summary = "Operation did not complete.";
        try {
            runtime = new DiagnosticRuntime(getApplicationContext(), new DiagnosticRuntime.Listener() {
                @Override public void onStage(String nextStage, String nextDetail) {
                    main.post(() -> {
                        if (currentOperation != operation || destroyed) return;
                        if (!stopping) { stage = bounded(nextStage, 120); detail = bounded(nextDetail, 600); }
                        notifyState();
                    });
                }
                @Override public void onLog(String line) {
                    main.post(() -> {
                        if (currentOperation != operation || destroyed) return;
                        appendLog(line);
                        scheduleNotify();
                    });
                }
            });
            synchronized (operation) { operation.runtime = runtime; }
            if (operation.stop.get()) throw new InterruptedException("Stopped before startup");
            if (setup) {
                runtime.setupRuntime();
                passed = true;
                summary = "Runtime setup finished. You can now run diagnostics.";
            } else {
                DiagnosticRuntime.Result result = runtime.runDiagnostics();
                if (result == null) throw new IllegalStateException("Runtime returned no diagnostic result");
                passed = result.passed;
                summary = bounded(result.summary, 600);
                if (result.report != null) report = result.report;
            }
        } catch (Exception failure) {
            summary = operation.stop.get() || failure instanceof InterruptedException
                    ? "Operation stopped. Export the latest report if one is available."
                    : bounded(failure.getMessage() == null ? failure.getClass().getSimpleName() : failure.getMessage(), 600);
            final String message = summary;
            main.post(() -> { if (currentOperation == operation && !destroyed) appendLog(message); });
        } finally {
            if (runtime != null) {
                try {
                    File current = runtime.getLatestReport();
                    if (current != null && current.isFile()) report = current;
                } catch (Exception ignored) { /* Retain any earlier complete report. */ }
            }
            synchronized (operation) {
                operation.finished = true;
                operation.runtime = null;
                operation.thread = null;
            }
            Thread.interrupted();
            final boolean completed = passed && !operation.stop.get();
            final String outcome = summary;
            final File completedReport = report;
            main.post(() -> finish(setup, operation, operation.stop.get(), completed, outcome, completedReport));
        }
    }

    private void finish(boolean setup, Operation operation, boolean cancelled, boolean passed, String summary, File report) {
        if (currentOperation != operation) return;
        if (deadline != null) main.removeCallbacks(deadline);
        releaseWakeLock();
        busy = false;
        stopping = false;
        if (setup) setupComplete = passed;
        stage = cancelled ? "Stopped" : setup ? (passed ? "Runtime ready" : "Setup failed")
                                             : (passed ? "Diagnostics passed" : "Diagnostics failed");
        detail = cancelled ? "Owned work has stopped. Export the latest report for details." : bounded(summary, 600);
        if (report != null && report.isFile()) latestReport = report;
        preferences.edit().putBoolean("busy", false).putBoolean("setup_complete", setupComplete)
                .putString("stage", stage).putString("detail", detail)
                .putString("report", latestReport == null ? "" : latestReport.getAbsolutePath()).apply();
        if (!destroyed) notifyState();
        stopForeground(STOP_FOREGROUND_REMOVE);
        stopSelf();
    }

    private void requestStop(String reason) {
        if (!busy || stopping) return;
        stopping = true;
        final Operation operation = currentOperation;
        operation.stop.set(true);
        stage = "Stopping";
        detail = reason;
        appendLog(reason);
        notifyState();
        // Neither process shutdown nor waiting for a worker happens on the UI thread.
        stopper.execute(() -> {
            synchronized (operation) {
                if (operation.finished) return;
                if (operation.thread != null) operation.thread.interrupt();
                // Finish this instance's cancellation before its worker can
                // publish completion and allow another operation to start.
                if (operation.runtime != null) operation.runtime.requestStop();
            }
        });
    }

    private void foreground() {
        if (Build.VERSION.SDK_INT >= 34) {
            startForeground(NOTIFICATION_ID, notification(), ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE);
        } else {
            startForeground(NOTIFICATION_ID, notification());
        }
    }

    private Notification notification() {
        PendingIntent open = PendingIntent.getActivity(this, 0, new Intent(this, MainActivity.class),
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        PendingIntent stop = PendingIntent.getService(this, 1,
                new Intent(this, DiagnosticService.class).setAction(ACTION_STOP),
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        return new Notification.Builder(this, CHANNEL)
                .setSmallIcon(android.R.drawable.stat_notify_sync)
                .setContentTitle("COH Diagnostic — " + bounded(stage, 80))
                .setContentText(bounded(detail, 160)).setContentIntent(open)
                .setOnlyAlertOnce(true).setOngoing(true)
                .addAction(new Notification.Action.Builder(null, "Stop", stop).build()).build();
    }

    private void appendLog(String line) {
        log.append(bounded(line, 4000)).append('\n');
        if (log.length() > MAX_LOG_CHARS) {
            int through = log.indexOf("\n", log.length() - MAX_LOG_CHARS);
            log.delete(0, through >= 0 ? through + 1 : log.length() - MAX_LOG_CHARS);
        }
    }

    private void scheduleNotify() {
        if (notificationPending) return;
        notificationPending = true;
        main.postDelayed(() -> { notificationPending = false; if (!destroyed) notifyState(); }, 150L);
    }

    private void notifyState() {
        State state = snapshot();
        for (Listener listener : new ArrayList<>(listeners)) listener.onState(state);
        if (busy && !destroyed) getSystemService(NotificationManager.class).notify(NOTIFICATION_ID, notification());
    }

    private static String bounded(String text, int limit) {
        if (text == null) return "";
        String safe = text.replace('\0', ' ');
        return safe.length() <= limit ? safe : safe.substring(0, limit) + "…";
    }

    private void releaseWakeLock() {
        if (wakeLock != null && wakeLock.isHeld()) wakeLock.release();
        wakeLock = null;
    }

    @Override public void onDestroy() {
        if (busy) requestStop("Service is stopping; cancelling owned work.");
        destroyed = true;
        listeners.clear();
        if (deadline != null) main.removeCallbacks(deadline);
        releaseWakeLock();
        // Already queued cancellation and cleanup must be allowed to finish.
        worker.shutdown();
        stopper.shutdown();
        super.onDestroy();
    }
}
