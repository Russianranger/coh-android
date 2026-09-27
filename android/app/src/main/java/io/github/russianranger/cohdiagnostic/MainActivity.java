package io.github.russianranger.cohdiagnostic;

import android.Manifest;
import android.app.Activity;
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
import android.view.Gravity;
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

/** A native shell; long-running work belongs to DiagnosticService. */
public final class MainActivity extends Activity {
    private static final int EXPORT_REQUEST = 10, NOTIFICATION_REQUEST = 11;
    private static final int INK = Color.rgb(226, 237, 245);
    private static final int MUTED = Color.rgb(159, 182, 199);
    private final ExecutorService exporter = Executors.newSingleThreadExecutor();
    private DiagnosticService service;
    private boolean bound, exporting;
    private Button setup, run, clientProbe, stop, export;
    private TextView stage, detail, logs;
    private ProgressBar progress;
    private ScrollView logScroll;
    private DiagnosticService.State state;
    private String pendingExportPath;
    private final DiagnosticService.Listener listener = this::render;
    private final ServiceConnection connection = new ServiceConnection() {
        @Override public void onServiceConnected(ComponentName name, IBinder binder) {
            service = ((DiagnosticService.LocalBinder) binder).getService();
            service.addListener(listener);
        }
        @Override public void onServiceDisconnected(ComponentName name) {
            service = null;
            stage.setText("Service disconnected");
            detail.setText("Reopen this screen to reconnect. Interrupted tests do not restart automatically.");
            setup.setEnabled(false); run.setEnabled(false); clientProbe.setEnabled(false); stop.setEnabled(false);
        }
    };

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (savedInstanceState != null) pendingExportPath = savedInstanceState.getString("pending_export");
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
        // Keep controls reachable on the Thor's short landscape viewport and
        // with larger Android font sizes. The log retains its own bounded area.
        ScrollView screen = new ScrollView(this);
        screen.setFillViewport(true);
        screen.addView(root, new ScrollView.LayoutParams(ScrollView.LayoutParams.MATCH_PARENT, ScrollView.LayoutParams.WRAP_CONTENT));
        setContentView(screen);

        TextView title = text("COH Diagnostic", 27, INK);
        title.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        root.addView(title, full());
        TextView scope = text("Runtime and database checks for AYN Thor. The optional client probe adds synthetic graphics and input checks. City of Heroes gameplay is not included.", 14, MUTED);
        scope.setPadding(0, dp(5), 0, dp(12));
        root.addView(scope, full());

        setup = button("Setup runtime", () -> startOperation(DiagnosticService.ACTION_SETUP));
        root.addView(setup, full());
        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.HORIZONTAL);
        run = button("Run diagnostics", () -> startOperation(DiagnosticService.ACTION_RUN));
        stop = button("Stop", () -> startService(new Intent(this, DiagnosticService.class).setAction(DiagnosticService.ACTION_STOP)));
        actions.addView(run, new LinearLayout.LayoutParams(0, dp(52), 1));
        LinearLayout.LayoutParams stopSize = new LinearLayout.LayoutParams(dp(100), dp(52));
        stopSize.setMarginStart(dp(8));
        actions.addView(stop, stopSize);
        root.addView(actions, full());
        clientProbe = button("Run client probe", () -> startOperation(DiagnosticService.ACTION_CLIENT_PROBE));
        root.addView(clientProbe, full());
        TextView probeScope = text("Includes diagnostics plus a test Windows window, OpenGL and input messages in a virtual display. Does not validate game rendering or controller input.", 12, MUTED);
        probeScope.setPadding(0, dp(2), 0, dp(6));
        root.addView(probeScope, full());
        export = button("Export latest report", this::chooseExport);
        root.addView(export, full());
        setup.setEnabled(false); run.setEnabled(false); clientProbe.setEnabled(false); stop.setEnabled(false); export.setEnabled(false);

        LinearLayout status = new LinearLayout(this);
        status.setGravity(Gravity.CENTER_VERTICAL);
        status.setPadding(0, dp(12), 0, dp(4));
        progress = new ProgressBar(this);
        progress.setVisibility(View.GONE);
        status.addView(progress, new LinearLayout.LayoutParams(dp(24), dp(24)));
        stage = text("Connecting", 18, INK);
        stage.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        stage.setPadding(dp(8), 0, 0, 0);
        status.addView(stage, new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1));
        root.addView(status, full());
        detail = text("Connecting to the diagnostic service…", 14, MUTED);
        detail.setPadding(0, 0, 0, dp(10));
        root.addView(detail, full());

        logScroll = new ScrollView(this);
        logScroll.setFillViewport(true);
        logScroll.setBackgroundColor(Color.rgb(7, 16, 25));
        logs = text("Progress will appear here.", 12, INK);
        logs.setTypeface(Typeface.MONOSPACE);
        logs.setTextIsSelectable(true);
        logs.setPadding(dp(12), dp(12), dp(12), dp(12));
        logScroll.addView(logs, new ScrollView.LayoutParams(ScrollView.LayoutParams.MATCH_PARENT, ScrollView.LayoutParams.WRAP_CONTENT));
        root.addView(logScroll, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(180), 1));
        TextView version = text("M2 + client probe · v0.1.1 · Android " + Build.VERSION.RELEASE + " · "
                + (Build.SUPPORTED_ABIS.length == 0 ? "unknown ABI" : Build.SUPPORTED_ABIS[0]), 11, MUTED);
        version.setPadding(0, dp(8), 0, 0);
        root.addView(version, full());
        root.requestApplyInsets();
    }

    @Override protected void onStart() {
        super.onStart();
        bound = bindService(new Intent(this, DiagnosticService.class), connection, BIND_AUTO_CREATE);
        if (!bound) { stage.setText("Service unavailable"); detail.setText("Close and reopen the app to retry."); }
    }

    @Override protected void onStop() {
        if (service != null) service.removeListener(listener);
        service = null;
        if (bound) { unbindService(connection); bound = false; }
        super.onStop();
    }

    private void startOperation(String action) {
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[] { Manifest.permission.POST_NOTIFICATIONS }, NOTIFICATION_REQUEST);
        }
        try {
            startForegroundService(new Intent(this, DiagnosticService.class).setAction(action));
        } catch (RuntimeException failure) {
            Toast.makeText(this, "Could not start diagnostics: " + failure.getClass().getSimpleName(), Toast.LENGTH_LONG).show();
        }
    }

    private void render(DiagnosticService.State current) {
        state = current;
        setup.setEnabled(!current.busy && !current.blocked);
        run.setEnabled(!current.busy && !current.blocked && current.setupComplete);
        clientProbe.setEnabled(!current.busy && !current.blocked && current.setupComplete);
        stop.setEnabled(current.busy && !current.stopping);
        stop.setText(current.stopping ? "Stopping…" : "Stop");
        export.setEnabled(!exporting && current.report != null && current.report.isFile());
        progress.setVisibility(current.busy ? View.VISIBLE : View.GONE);
        stage.setText(current.stage);
        detail.setText(current.detail);
        String nextLog = current.log.isEmpty() ? "Progress will appear here." : current.log;
        if (!nextLog.contentEquals(logs.getText())) {
            boolean atEnd = logScroll.getScrollY() + logScroll.getHeight() >= logs.getHeight() - dp(48);
            logs.setText(nextLog);
            if (atEnd) logScroll.post(() -> logScroll.fullScroll(View.FOCUS_DOWN));
        }
    }

    private void chooseExport() {
        if (state == null || state.report == null || !state.report.isFile()) return;
        pendingExportPath = state.report.getAbsolutePath();
        SimpleDateFormat format = new SimpleDateFormat("yyyyMMdd-HHmmss", Locale.US);
        format.setTimeZone(TimeZone.getTimeZone("UTC"));
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE)
                .setType("application/zip").putExtra(Intent.EXTRA_TITLE, "coh-diagnostic-" + format.format(new Date()) + ".zip");
        try { startActivityForResult(intent, EXPORT_REQUEST); }
        catch (RuntimeException failure) { Toast.makeText(this, "No document provider is available for export.", Toast.LENGTH_LONG).show(); }
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != EXPORT_REQUEST) return;
        String sourcePath = pendingExportPath;
        pendingExportPath = null;
        if (resultCode != RESULT_OK || data == null || data.getData() == null || sourcePath == null) return;
        File source = new File(sourcePath);
        Uri destination = data.getData();
        exporting = true;
        export.setEnabled(false);
        exporter.execute(() -> {
            String outcome;
            try {
                if (!source.getCanonicalPath().startsWith(getFilesDir().getCanonicalPath() + File.separator))
                    throw new IOException("Report is outside app storage");
                try (FileInputStream input = new FileInputStream(source);
                     OutputStream output = getContentResolver().openOutputStream(destination, "w")) {
                    if (output == null) throw new IOException("Document provider did not open the destination");
                    byte[] buffer = new byte[65536];
                    int count;
                    while ((count = input.read(buffer)) >= 0) output.write(buffer, 0, count);
                    output.flush();
                }
                outcome = "Report exported.";
            } catch (Exception failure) { outcome = "Export failed. Choose another destination and try again."; }
            final String message = outcome;
            runOnUiThread(() -> {
                exporting = false;
                if (!isDestroyed()) {
                    if (state != null) render(state);
                    Toast.makeText(this, message, Toast.LENGTH_LONG).show();
                }
            });
        });
    }

    @Override protected void onSaveInstanceState(Bundle out) {
        out.putString("pending_export", pendingExportPath);
        super.onSaveInstanceState(out);
    }

    @Override protected void onDestroy() {
        exporter.shutdown();
        super.onDestroy();
    }

    private Button button(String label, Runnable action) {
        Button button = new Button(this);
        button.setText(label);
        button.setAllCaps(false);
        button.setMinHeight(dp(48));
        button.setOnClickListener(view -> action.run());
        return button;
    }

    private TextView text(String value, int size, int color) {
        TextView view = new TextView(this);
        view.setText(value); view.setTextSize(size); view.setTextColor(color);
        return view;
    }

    private LinearLayout.LayoutParams full() {
        return new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
    }

    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }
}
