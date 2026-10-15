package io.github.russianranger.cohatlastest;

import android.Manifest;
import android.app.Activity;
import android.content.ClipData;
import android.content.ComponentName;
import android.content.Intent;
import android.content.ServiceConnection;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Insets;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.IBinder;
import android.view.View;
import android.view.WindowInsets;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** The service owns setup, content import, and local Atlas server testing. */
public final class AtlasActivity extends Activity {
    private static final int IMPORT_REQUEST = 20, EXPORT_REQUEST = 21, NOTIFICATION_REQUEST = 22;
    private static final int INK = Color.rgb(226, 237, 245), MUTED = Color.rgb(159, 182, 199);
    private final ExecutorService exporter = Executors.newSingleThreadExecutor();
    private AtlasGameService service;
    private AtlasGameService.State state;
    private boolean bound, exporting;
    private Button setupButton, importButton, runButton, stopButton, exportButton;
    private String notificationAction;
    private TextView stage, detail, prepared, log;
    private ProgressBar progress;
    private String pendingExport;
    private final AtlasGameService.Listener listener = this::render;
    private final ServiceConnection connection = new ServiceConnection() {
        @Override public void onServiceConnected(ComponentName name, IBinder binder) {
            service = ((AtlasGameService.LocalBinder) binder).getService();
            service.setUiVisible(true);
            service.addListener(listener);
        }
        @Override public void onServiceDisconnected(ComponentName name) {
            service = null;
            setupButton.setEnabled(false); importButton.setEnabled(false); runButton.setEnabled(false); stopButton.setEnabled(false);
            stage.setText("Service disconnected");
            detail.setText("Reopen this screen to reconnect. Interrupted operations never restart automatically.");
        }
    };

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        if (saved != null) { pendingExport = saved.getString("pending_export"); notificationAction = saved.getString("notification_action"); }
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.rgb(12, 23, 34));
        int pad = dp(18);
        root.setPadding(pad, pad, pad, pad);
        root.setOnApplyWindowInsetsListener((view, insets) -> {
            int left, top, right, bottom;
            if (Build.VERSION.SDK_INT >= 30) {
                Insets bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
                left = bars.left; top = bars.top; right = bars.right; bottom = bars.bottom;
            } else {
                left = insets.getSystemWindowInsetLeft(); top = insets.getSystemWindowInsetTop();
                right = insets.getSystemWindowInsetRight(); bottom = insets.getSystemWindowInsetBottom();
            }
            view.setPadding(pad + left, pad + top, pad + right, pad + bottom);
            return insets;
        });
        ScrollView screen = new ScrollView(this);
        screen.setFillViewport(true);
        screen.addView(root, new ScrollView.LayoutParams(-1, -2));
        setContentView(screen);
        TextView title = text("COH Atlas Test", 27, INK);
        title.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        root.addView(title, full());
        root.addView(text("Run the local Atlas Park server and automated character persistence checks on this device. This test has no graphical game client.", 14, MUTED), full());
        TextView instructions = text("1. Set up the runtime while connected to the internet.\n2. Import the complete coh-reference-assets.zip again for this separate app.\n3. Run the Atlas test. You can switch apps or lock the screen, and use Stop to cancel.\n\nFree internal storage required: 8 GiB before runtime setup, 5 GiB before import, and 6 GiB after both are installed for the server test. Each step checks available space.", 14, INK);
        instructions.setPadding(0, dp(16), 0, dp(10));
        root.addView(instructions, full());
        setupButton = button("1 · Set up runtime", () -> requestAction(AtlasGameService.ACTION_SETUP));
        root.addView(setupButton, full());
        importButton = button("2 · Import game assets", this::chooseImport);
        root.addView(importButton, full());
        runButton = button("3 · Run Atlas test", () -> requestAction(AtlasGameService.ACTION_TEST));
        root.addView(runButton, full());
        stopButton = button("Stop", () -> startService(new Intent(this, AtlasGameService.class).setAction(AtlasGameService.ACTION_STOP)));
        root.addView(stopButton, full());
        exportButton = button("Export latest report", this::chooseExport);
        root.addView(exportButton, full());
        setupButton.setEnabled(false); importButton.setEnabled(false); runButton.setEnabled(false); stopButton.setEnabled(false); exportButton.setEnabled(false);
        stage = text("Connecting", 19, INK);
        stage.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        stage.setPadding(0, dp(16), 0, dp(5));
        root.addView(stage, full());
        progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progress.setMax(10000); progress.setVisibility(View.GONE);
        root.addView(progress, full());
        detail = text("Connecting to the Atlas test service…", 14, MUTED);
        root.addView(detail, full());
        prepared = text("", 13, INK);
        prepared.setPadding(0, dp(12), 0, dp(8));
        root.addView(prepared, full());
        log = text("Progress will appear here.", 12, MUTED);
        log.setTypeface(Typeface.MONOSPACE); log.setTextIsSelectable(true);
        root.addView(log, full());
        TextView version = text("Local server test · v0.4.4 · Android " + Build.VERSION.RELEASE, 11, MUTED);
        version.setPadding(0, dp(16), 0, dp(8));
        root.addView(version, full());
        root.requestApplyInsets();
    }

    @Override protected void onStart() {
        super.onStart();
        bound = bindService(new Intent(this, AtlasGameService.class), connection, BIND_AUTO_CREATE);
        if (!bound) { stage.setText("Service unavailable"); detail.setText("Close and reopen the app to retry."); }
    }

    @Override protected void onStop() {
        if (service != null) { service.setUiVisible(false); service.removeListener(listener); }
        service = null;
        if (bound) { unbindService(connection); bound = false; }
        super.onStop();
    }

    private void chooseImport() { requestAction(AtlasGameService.ACTION_IMPORT); }

    private void requestAction(String action) {
        if (state == null || state.busy || state.initializing || state.blocked) return;
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            notificationAction = action;
            requestPermissions(new String[] { Manifest.permission.POST_NOTIFICATIONS }, NOTIFICATION_REQUEST);
            return;
        }
        launchAction(action);
    }

    private void launchAction(String action) {
        if (AtlasGameService.ACTION_IMPORT.equals(action)) { openAssetPicker(); return; }
        try { startForegroundService(new Intent(this, AtlasGameService.class).setAction(action)); }
        catch (RuntimeException failure) { toast("Could not start. Return to this screen and try again."); }
    }

    @Override public void onRequestPermissionsResult(int request, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(request, permissions, results);
        if (request == NOTIFICATION_REQUEST) {
            String action = notificationAction; notificationAction = null;
            if (action != null) launchAction(action);
        }
    }

    private void openAssetPicker() {
        Intent pick = new Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE)
                .setType("application/zip").putExtra(Intent.EXTRA_MIME_TYPES,
                        new String[] { "application/zip", "application/x-zip-compressed", "application/octet-stream" });
        try { startActivityForResult(pick, IMPORT_REQUEST); }
        catch (RuntimeException failure) { toast("No document provider is available. Open Android Files and try again."); }
    }

    private void render(AtlasGameService.State current) {
        state = current;
        setupButton.setEnabled(!current.busy && !current.initializing && !current.blocked);
        importButton.setEnabled(!current.busy && !current.initializing && !current.blocked);
        runButton.setEnabled(!current.busy && !current.initializing && !current.blocked && current.contentReady);
        stopButton.setEnabled(current.busy && !current.stopping);
        stopButton.setText(current.stopping ? "Stopping…" : "Stop");
        exportButton.setEnabled(!exporting && !current.busy && current.report != null && current.report.isFile());
        stage.setText(current.stage); detail.setText(current.detail);
        prepared.setText(current.prepared);
        progress.setVisibility(current.busy ? View.VISIBLE : View.GONE);
        progress.setIndeterminate(current.totalBytes <= 0);
        if (current.totalBytes > 0)
            progress.setProgress((int) Math.min(10000, current.bytesDone * 10000L / current.totalBytes));
        log.setText(current.log.isEmpty() ? "Progress will appear here." : current.log);
    }

    private void chooseExport() {
        if (state == null || state.busy || state.report == null || !state.report.isFile()) return;
        pendingExport = state.report.getAbsolutePath();
        SimpleDateFormat format = new SimpleDateFormat("yyyyMMdd-HHmmss", Locale.US);
        format.setTimeZone(TimeZone.getTimeZone("UTC"));
        Intent pick = new Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE)
                .setType("application/zip").putExtra(Intent.EXTRA_TITLE, "coh-atlas-test-" + format.format(new Date()) + ".zip");
        try { startActivityForResult(pick, EXPORT_REQUEST); }
        catch (RuntimeException failure) { pendingExport = null; toast("No document provider is available for export."); }
    }

    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request == IMPORT_REQUEST) {
            if (result != RESULT_OK || data == null || data.getData() == null) return;
            Uri source = data.getData();
            if (!"content".equals(source.getScheme())) { toast("Choose a file using Android's document picker."); return; }
            Intent start = new Intent(this, AtlasGameService.class).setAction(AtlasGameService.ACTION_IMPORT)
                    .setData(source).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            start.setClipData(ClipData.newRawUri("Game assets", source));
            try { startForegroundService(start); }
            catch (RuntimeException failure) { toast("Could not start the import. Return to this screen and try again."); }
            return;
        }
        if (request != EXPORT_REQUEST) return;
        String sourcePath = pendingExport; pendingExport = null;
        if (result != RESULT_OK || data == null || data.getData() == null || sourcePath == null) return;
        Uri destination = data.getData();
        exporting = true; exportButton.setEnabled(false);
        exporter.execute(() -> {
            String message;
            try {
                File source = new File(sourcePath);
                File reports = new File(getFilesDir(), "atlas-game/reports");
                if (!source.getCanonicalPath().startsWith(reports.getCanonicalPath() + File.separator) || !source.isFile())
                    throw new IOException("Report unavailable");
                try (FileInputStream input = new FileInputStream(source);
                     OutputStream output = getContentResolver().openOutputStream(destination, "w")) {
                    if (output == null) throw new IOException("Export unavailable");
                    byte[] buffer = new byte[65536]; int count;
                    while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
                    output.flush();
                }
                message = "Report exported.";
            } catch (Exception failure) { message = "Export failed. Choose another destination and try again."; }
            final String outcome = message;
            runOnUiThread(() -> { exporting = false; if (!isDestroyed()) { if (state != null) render(state); toast(outcome); } });
        });
    }

    @Override protected void onSaveInstanceState(Bundle out) { out.putString("pending_export", pendingExport); out.putString("notification_action", notificationAction); super.onSaveInstanceState(out); }
    @Override protected void onDestroy() { exporter.shutdown(); super.onDestroy(); }
    private void toast(String message) { Toast.makeText(this, message, Toast.LENGTH_LONG).show(); }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }
    private LinearLayout.LayoutParams full() { return new LinearLayout.LayoutParams(-1, -2); }
    private TextView text(String value, int size, int color) { TextView view = new TextView(this); view.setText(value); view.setTextSize(size); view.setTextColor(color); return view; }
    private Button button(String title, Runnable action) { Button view = new Button(this); view.setText(title); view.setAllCaps(false); view.setMinHeight(dp(52)); view.setOnClickListener(v -> action.run()); return view; }
}
