package io.github.russianranger.cohclientinteractive;

import android.content.Context;
import android.os.Build;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;
import org.json.JSONArray;
import org.json.JSONObject;

/** 0.13.90: what ended the app.
 *
 * Thor 0.13.89 (2026-11-27): the app closed to the Android home screen about twenty seconds after a
 * saved hero from another zone was chosen. The guest reported no failure, 8 GB was free, and the
 * recovered export held the last checkpoint only: neither Android's exit record of the process nor
 * a trace of a crash in the app's own code. Both are kept from now on.
 *
 * An uncaught exception is written to one small private file and then handed to Android's own
 * handler, so the process ends exactly as before. At the next start, when the interrupted
 * operation's checkpoint is retained, that file and Android's exit records go into the recovered
 * export as android-interruption.json. Evidence only: nothing here changes a session. */
final class ClientCrash {
    static final String FILE = "android-crash.json";
    static final int MAX_BYTES = 48 * 1024;
    static final int MAX_FRAMES = 48;
    static final int MAX_TRACE_TEXT = 256 * 1024, MAX_TRACE_BINARY = 96 * 1024;
    private static boolean installed;
    private ClientCrash() {}

    static synchronized void install(Context context) {
        if (installed || context == null) return;
        final Context application = context.getApplicationContext() == null ? context : context.getApplicationContext();
        final File target = new File(application.getFilesDir(), FILE);
        final Thread.UncaughtExceptionHandler previous = Thread.getDefaultUncaughtExceptionHandler();
        Thread.setDefaultUncaughtExceptionHandler(new Thread.UncaughtExceptionHandler() {
            @Override public void uncaughtException(Thread thread, Throwable failure) {
                try { write(target, record(thread == null ? null : thread.getName(), failure, System.currentTimeMillis())); }
                catch (Throwable ignored) { /* The crash itself is Android's to report. */ }
                if (previous != null) previous.uncaughtException(thread, failure);
            }
        });
        ClientReports.setInterruptionEvidence(new ClientReports.InterruptionEvidence() {
            @Override public byte[] collect() throws Exception { return evidence(application); }
        });
        installed = true;
    }

    /** One JSON object, built by hand so that it needs nothing but strings while the app is failing. */
    static String record(String thread, Throwable failure, long utcMillis) {
        StringBuilder out = new StringBuilder(4096);
        out.append("{\"format\":1,\"utc_ms\":").append(utcMillis).append(",\"thread\":");
        quote(out, thread, 80);
        out.append(",\"chain\":[");
        Throwable current = failure;
        for (int depth = 0; current != null && depth < 4 && out.length() < MAX_BYTES - 8192; depth++) {
            if (depth > 0) out.append(',');
            out.append("{\"exception\":");
            quote(out, current.getClass().getName(), 160);
            out.append(",\"message\":");
            String message = null;
            try { message = current.getMessage(); } catch (Throwable unreadable) { message = "unreadable"; }
            quote(out, message, 400);
            out.append(",\"frames\":[");
            StackTraceElement[] frames = current.getStackTrace();
            int count = frames == null ? 0 : Math.min(frames.length, MAX_FRAMES);
            for (int i = 0; i < count; i++) {
                if (i > 0) out.append(',');
                quote(out, String.valueOf(frames[i]), 240);
            }
            out.append("],\"frames_total\":").append(frames == null ? 0 : frames.length).append('}');
            Throwable cause = current.getCause();
            current = cause == current ? null : cause;
        }
        return out.append("]}").toString();
    }

    private static void quote(StringBuilder out, String value, int limit) {
        if (value == null) { out.append("null"); return; }
        out.append('"');
        int length = Math.min(value.length(), limit);
        for (int i = 0; i < length; i++) {
            char c = value.charAt(i);
            if (c == '"' || c == '\\') out.append('\\').append(c);
            else if (c < 0x20 || c > 0x7e) out.append(String.format(java.util.Locale.ROOT, "\\u%04x", (int) c));
            else out.append(c);
        }
        out.append('"');
    }

    static void write(File target, String json) throws java.io.IOException {
        byte[] bytes = json.getBytes(StandardCharsets.UTF_8);
        if (bytes.length > MAX_BYTES) throw new java.io.IOException("Crash record exceeds limit");
        File part = new File(target.getParentFile(), "." + target.getName() + ".part");
        try (FileOutputStream out = new FileOutputStream(part, false)) { out.write(bytes); out.getFD().sync(); }
        if (!part.renameTo(target)) { part.delete(); throw new java.io.IOException("Crash record was not kept"); }
    }

    /** The last crash record, or null. A file that is not a small regular file is left alone. */
    static String lastRecord(File filesDir) {
        File file = new File(filesDir, FILE);
        try {
            if (!file.isFile() || file.length() <= 0 || file.length() > MAX_BYTES) return null;
            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
            try (InputStream in = new FileInputStream(file)) {
                byte[] block = new byte[8192];
                for (int n; (n = in.read(block)) != -1; ) {
                    bytes.write(block, 0, n);
                    if (bytes.size() > MAX_BYTES) return null;
                }
            }
            return new String(bytes.toByteArray(), StandardCharsets.UTF_8);
        } catch (Exception unreadable) { return null; }
    }

    static String reasonName(int reason) {
        switch (reason) {
            case 1: return "EXIT_SELF";
            case 2: return "SIGNALED";
            case 3: return "LOW_MEMORY";
            case 4: return "CRASH";
            case 5: return "CRASH_NATIVE";
            case 6: return "ANR";
            case 7: return "INITIALIZATION_FAILURE";
            case 8: return "PERMISSION_CHANGE";
            case 9: return "EXCESSIVE_RESOURCE_USAGE";
            case 10: return "USER_REQUESTED";
            case 11: return "USER_STOPPED";
            case 12: return "DEPENDENCY_DIED";
            case 13: return "OTHER";
            case 14: return "FREEZER";
            case 15: return "PACKAGE_STATE_CHANGE";
            case 16: return "PACKAGE_UPDATED";
            default: return "UNKNOWN";
        }
    }

    /** Collected when an interrupted operation is first retained: the newest exit record is its end. */
    static byte[] evidence(Context context) throws Exception {
        JSONObject result = new JSONObject().put("format", 1).put("collected_utc_ms", System.currentTimeMillis())
                .put("policy", "android_exit_records_and_own_crash_trace_v1").put("is_success_proof", false);
        String crash = lastRecord(context.getFilesDir());
        Object parsed = JSONObject.NULL;
        if (crash != null) try { parsed = new JSONObject(crash); } catch (Exception invalid) { parsed = "unreadable"; }
        result.put("last_crash", parsed);
        JSONObject exits = new JSONObject().put("maximum_records", ClientRuntime.EXIT_HISTORY_RECORDS).put("own_processes_only", true)
                .put("trace_streams_requested", true);
        if (Build.VERSION.SDK_INT < 30) exits.put("status", "unsupported_api");
        else try { ExitRecords.collect(context, exits); } catch (Exception unavailable) {
            exits.put("status", "unavailable").put("error", unavailable.getClass().getSimpleName());
        }
        result.put("exit_history", exits);
        byte[] bytes = result.toString().getBytes(StandardCharsets.UTF_8);
        if (bytes.length > ClientReports.MAX_INTERRUPTION_BYTES) {
            // The reason codes matter more than a trace that does not fit.
            JSONArray records = exits.optJSONArray("records");
            if (records != null) for (int i = 0; i < records.length(); i++) {
                JSONObject record = records.optJSONObject(i);
                if (record != null && (record.remove("trace_text") != null | record.remove("trace_base64") != null))
                    record.put("trace", "dropped_over_limit");
            }
            bytes = result.toString().getBytes(StandardCharsets.UTF_8);
        }
        if (bytes.length > ClientReports.MAX_INTERRUPTION_BYTES) throw new java.io.IOException("Interruption evidence exceeds limit");
        return bytes;
    }

    /** Isolates Android 11 classes from the supported Android 8-10 path. */
    private static final class ExitRecords {
        static void collect(Context context, JSONObject result) throws Exception {
            android.app.ActivityManager manager = (android.app.ActivityManager) context.getSystemService(Context.ACTIVITY_SERVICE);
            if (manager == null) { result.put("status", "unavailable"); return; }
            String ownPackage = context.getPackageName();
            List<android.app.ApplicationExitInfo> history = manager.getHistoricalProcessExitReasons(ownPackage, 0, ClientRuntime.EXIT_HISTORY_RECORDS);
            JSONArray records = new JSONArray();
            boolean traceTaken = false;
            if (history != null) for (int i = 0; i < Math.min(history.size(), ClientRuntime.EXIT_HISTORY_RECORDS); i++) {
                android.app.ApplicationExitInfo info = history.get(i);
                if (info == null) continue;
                String description = info.getDescription();
                if (description != null && description.length() > 240) description = description.substring(0, 240);
                String process = info.getProcessName();
                JSONObject record = new JSONObject().put("timestamp_utc_ms", info.getTimestamp())
                        .put("reason", info.getReason()).put("reason_name", reasonName(info.getReason()))
                        .put("status", info.getStatus()).put("importance", info.getImportance())
                        .put("pss_kib", info.getPss()).put("rss_kib", info.getRss()).put("pid", info.getPid())
                        .put("process_name", process == null ? JSONObject.NULL : process.substring(0, Math.min(process.length(), 160)))
                        .put("description", description == null ? JSONObject.NULL : description);
                // Android keeps a trace for two endings only: the thread dump of an app that stopped
                // answering (text, this process first) and the tombstone of a native crash (binary).
                // One trace, the newest, bounded; a Java crash has none here (android-crash.json).
                if (!traceTaken && (info.getReason() == 6 || info.getReason() == 5)) {
                    traceTaken = true;
                    try (InputStream in = info.getTraceInputStream()) {
                        if (in == null) record.put("trace", "none");
                        else {
                            int limit = info.getReason() == 6 ? MAX_TRACE_TEXT : MAX_TRACE_BINARY;
                            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
                            byte[] block = new byte[8192];
                            for (int n; bytes.size() < limit && (n = in.read(block, 0, Math.min(block.length, limit - bytes.size()))) != -1; )
                                bytes.write(block, 0, n);
                            record.put("trace_bytes_kept", bytes.size()).put("trace_truncated", in.read() != -1);
                            if (info.getReason() == 6) record.put("trace_text", new String(bytes.toByteArray(), StandardCharsets.UTF_8));
                            else record.put("trace_base64", android.util.Base64.encodeToString(bytes.toByteArray(), android.util.Base64.NO_WRAP));
                        }
                    } catch (Exception | OutOfMemoryError unreadable) { record.put("trace", "unreadable:" + unreadable.getClass().getSimpleName()); }
                }
                records.put(record);
            }
            result.put("status", "available").put("records", records);
        }
    }
}
