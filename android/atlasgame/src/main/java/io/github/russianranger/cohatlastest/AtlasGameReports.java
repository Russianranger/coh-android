package io.github.russianranger.cohatlastest;

import android.content.Context;
import android.os.Build;
import io.github.russianranger.cohatlas.AtlasAssetImporter;
import io.github.russianranger.cohdiagnostic.AtlasGameRuntime;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.UUID;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/** An immutable, fresh report for every app operation, including interruptions. */
final class AtlasGameReports {
    static File write(Context context, File home, String runId, String operation,
                      String status, String message, long started, String phase,
                      long filesDone, long totalFiles, long bytesDone, long totalBytes,
                      AtlasAssetImporter.Summary content, String errorType,
                      String interruptedRun, String log, String lifecycle, File runtimeReport) throws IOException {
        try {
            UUID.fromString(runId);
            boolean imported = "verified_content_import".equals(operation) && "passed".equals(status);
            boolean serverPassed = "atlas_server_test".equals(operation) && "passed".equals(status);
            byte[] contract = readAsset(context, "atlas/atlas-import.properties");
            JSONObject report = new JSONObject().put("format", 1).put("run_id", runId)
                    .put("operation", operation).put("status", status).put("message", message)
                    .put("started_epoch_ms", started).put("finished_epoch_ms", System.currentTimeMillis())
                    .put("app_id", context.getPackageName()).put("app_version", "0.4.3")
                    .put("android_sdk", Build.VERSION.SDK_INT)
                    .put("device", Build.MANUFACTURER + " " + Build.MODEL)
                    .put("content_import_validated", imported)
                    .put("server_execution_validated", serverPassed)
                    .put("gameplay_validated", false)
                    .put("cleanup_blocked", AtlasGameRuntime.cleanupBlocked())
                    .put("scope", "Runtime setup, verified content import, or automated local Atlas Park server test; no graphical game client")
                    .put("lifecycle_evidence", "Timestamped observations only; background and screen-lock acceptance requires reviewing events during a completed test")
                    .put("runtime_report_included", runtimeReport != null && runtimeReport.isFile())
                    .put("progress", new JSONObject().put("phase", phase).put("files_done", filesDone)
                            .put("total_files", totalFiles).put("bytes_done", bytesDone).put("total_bytes", totalBytes));
            if (errorType != null) report.put("error_type", errorType);
            if (interruptedRun != null) report.put("interrupted_run_id", interruptedRun);
            if (content != null) report.put("available_content", new JSONObject()
                    .put("generation", content.generation).put("file_count", content.count)
                    .put("total_bytes", content.bytes).put("source_commit", content.sourceCommit)
                    .put("data_commit", content.dataCommit).put("repository_commit", content.repositoryCommit)
                    .put("verified_during_this_attempt", imported)
                    .put("inspection_scope", imported ? "Every imported file size and hash"
                            : "Previously committed import receipt; reopen does not rescan all content"));
            File directory = new File(home, "reports");
            Files.createDirectories(directory.toPath());
            File target = new File(directory, "coh-atlas-test-" + runId + ".zip");
            File partial = new File(directory, target.getName() + ".part");
            if (target.exists() || partial.exists()) throw new IOException("Report identity already exists");
            try {
                try (FileOutputStream file = new FileOutputStream(partial);
                     ZipOutputStream archive = new ZipOutputStream(file)) {
                    put(archive, "atlas-test-report.json", report.toString(2) + "\n");
                    put(archive, "operation.log", log);
                    put(archive, "lifecycle.log", lifecycle);
                    if (contract != null) {
                        archive.putNextEntry(new ZipEntry("atlas-import.properties"));
                        archive.write(contract); archive.closeEntry();
                    }
                    if (runtimeReport != null && runtimeReport.isFile()) {
                        if (runtimeReport.length() > 224L * 1024 * 1024) throw new IOException("Runtime report exceeded limit");
                        archive.putNextEntry(new ZipEntry("runtime-report.zip"));
                        try (FileInputStream input = new FileInputStream(runtimeReport)) {
                            byte[] buffer = new byte[65536]; int count; long copied = 0;
                            while ((count = input.read(buffer)) != -1) {
                                copied += count;
                                if (copied > 224L * 1024 * 1024) throw new IOException("Runtime report exceeded limit");
                                archive.write(buffer, 0, count);
                            }
                        }
                        archive.closeEntry();
                    }
                    archive.finish(); archive.flush(); file.getFD().sync();
                }
                Files.move(partial.toPath(), target.toPath(), StandardCopyOption.ATOMIC_MOVE);
                return target;
            } finally { Files.deleteIfExists(partial.toPath()); }
        } catch (IOException failure) { throw failure; }
        catch (Exception failure) { throw new IOException("Could not create operation report", failure); }
    }

    private static void put(ZipOutputStream archive, String name, String value) throws IOException {
        archive.putNextEntry(new ZipEntry(name));
        archive.write(value.getBytes(StandardCharsets.UTF_8)); archive.closeEntry();
    }

    private static byte[] readAsset(Context context, String name) {
        try (InputStream input = context.getAssets().open(name)) {
            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
            byte[] buffer = new byte[4096]; int count;
            while ((count = input.read(buffer)) != -1) {
                if (bytes.size() + count > 65536) return null;
                bytes.write(buffer, 0, count);
            }
            return bytes.toByteArray();
        } catch (IOException ignored) { return null; }
    }
}
