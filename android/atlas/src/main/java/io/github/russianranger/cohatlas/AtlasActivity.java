package io.github.russianranger.cohatlas;

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

/** A small content-preparation screen; the service owns every import. */
public final class AtlasActivity extends Activity {
    private static final int IMPORT_REQUEST = 20, EXPORT_REQUEST = 21, NOTIFICATION_REQUEST = 22;
    private static final int INK = Color.rgb(226, 237, 245), MUTED = Color.rgb(159, 182, 199);
    private final ExecutorService exporter = Executors.newSingleThreadExecutor();
    private AtlasImportService service;
    private AtlasImportService.State state;
    private boolean bound, exporting;
    private Button importButton, stopButton, exportButton;
    private TextView stage, detail, prepared, log;
    private ProgressBar progress;
    private String pendingExport;
    private final AtlasImportService.Listener listener = this::render;
    private final ServiceConnection connection = new ServiceConnection() {
        @Override public void onServiceConnected(ComponentName name, IBinder binder) {
            service = ((AtlasImportService.LocalBinder) binder).getService();
            service.addListener(listener);
        }
        @Override public void onServiceDisconnected(ComponentName name) {
            service = null;
            importButton.setEnabled(false); stopButton.setEnabled(false);
            stage.setText("Service disconnected");
            detail.setText("Reopen this screen to reconnect. Interrupted imports never restart automatically.");
        }
    };

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        if (saved != null) pendingExport = saved.getString("pending_export");
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
        TextView title = text("COH Atlas Setup", 27, INK);
        title.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        root.addView(title, full());
        root.addView(text("Prepare the verified game content for the next Atlas Park server test. This version imports and checks files only; it does not start the server or graphical game client.", 14, MUTED), full());
        TextView instructions = text("Choose coh-reference-assets.zip (587 MiB) from your device. The app checks the archive, combines it with the included game data, and verifies all 173,011 files. Keep at least 5 GiB free in internal storage. You can leave this screen during import.", 14, INK);
        instructions.setPadding(0, dp(16), 0, dp(10));
        root.addView(instructions, full());
        importButton = button("Import game assets", this::chooseImport);
        root.addView(importButton, full());
        stopButton = button("Stop", () -> startService(new Intent(this, AtlasImportService.class).setAction(AtlasImportService.ACTION_STOP)));
        root.addView(stopButton, full());
        exportButton = button("Export latest report", this::chooseExport);
        root.addView(exportButton, full());
        importButton.setEnabled(false); stopButton.setEnabled(false); exportButton.setEnabled(false);
        stage = text("Connecting", 19, INK);
        stage.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        stage.setPadding(0, dp(16), 0, dp(5));
        root.addView(stage, full());
        progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progress.setMax(10000); progress.setVisibility(View.GONE);
        root.addView(progress, full());
        detail = text("Connecting to the import service…", 14, MUTED);
        root.addView(detail, full());
        prepared = text("", 13, INK);
        prepared.setPadding(0, dp(12), 0, dp(8));
        root.addView(prepared, full());
        log = text("Progress will appear here.", 12, MUTED);
        log.setTypeface(Typeface.MONOSPACE); log.setTextIsSelectable(true);
        root.addView(log, full());
        TextView version = text("Content preparation · v0.3.0 · Android " + Build.VERSION.RELEASE, 11, MUTED);
        version.setPadding(0, dp(16), 0, dp(8));
        root.addView(version, full());
        root.requestApplyInsets();
    }

    @Override protected void onStart() {
        super.onStart();
        bound = bindService(new Intent(this, AtlasImportService.class), connection, BIND_AUTO_CREATE);
        if (!bound) { stage.setText("Service unavailable"); detail.setText("Close and reopen the app to retry."); }
    }

    @Override protected void onStop() {
        if (service != null) service.removeListener(listener);
        service = null;
        if (bound) { unbindService(connection); bound = false; }
        super.onStop();
    }

    private void chooseImport() {
        if (state == null || state.busy) return;
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[] { Manifest.permission.POST_NOTIFICATIONS }, NOTIFICATION_REQUEST);
            return;
        }
        openAssetPicker();
    }

    @Override public void onRequestPermissionsResult(int request, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(request, permissions, results);
        // Notification permission is optional; the app's progress and Stop
        // remain available when the user declines it.
        if (request == NOTIFICATION_REQUEST) openAssetPicker();
    }

    private void openAssetPicker() {
        Intent pick = new Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE)
                .setType("application/zip").putExtra(Intent.EXTRA_MIME_TYPES,
                        new String[] { "application/zip", "application/x-zip-compressed", "application/octet-stream" });
        try { startActivityForResult(pick, IMPORT_REQUEST); }
        catch (RuntimeException failure) { toast("No document provider is available. Open Android Files and try again."); }
    }

    private void render(AtlasImportService.State current) {
        state = current;
        importButton.setEnabled(!current.busy && !current.initializing);
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
                .setType("application/zip").putExtra(Intent.EXTRA_TITLE, "coh-atlas-import-" + format.format(new Date()) + ".zip");
        try { startActivityForResult(pick, EXPORT_REQUEST); }
        catch (RuntimeException failure) { pendingExport = null; toast("No document provider is available for export."); }
    }

    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request == IMPORT_REQUEST) {
            if (result != RESULT_OK || data == null || data.getData() == null) return;
            Uri source = data.getData();
            if (!"content".equals(source.getScheme())) { toast("Choose a file using Android's document picker."); return; }
            Intent start = new Intent(this, AtlasImportService.class).setAction(AtlasImportService.ACTION_IMPORT)
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
                File reports = new File(getFilesDir(), "atlas/reports");
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

    @Override protected void onSaveInstanceState(Bundle out) { out.putString("pending_export", pendingExport); super.onSaveInstanceState(out); }
    @Override protected void onDestroy() { exporter.shutdown(); super.onDestroy(); }
    private void toast(String message) { Toast.makeText(this, message, Toast.LENGTH_LONG).show(); }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }
    private LinearLayout.LayoutParams full() { return new LinearLayout.LayoutParams(-1, -2); }
    private TextView text(String value, int size, int color) { TextView view = new TextView(this); view.setText(value); view.setTextSize(size); view.setTextColor(color); return view; }
    private Button button(String title, Runnable action) { Button view = new Button(this); view.setText(title); view.setAllCaps(false); view.setMinHeight(dp(52)); view.setOnClickListener(v -> action.run()); return view; }
}
