package io.github.russianranger.cohatlas;

import android.content.Context;
import android.os.Build;
import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.UUID;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/** Immutable evidence of one attempt; excludes selected document names and URIs. */
final class AtlasImportReports {
    static File write(Context context, File home, String runId, String status, String message,
                      long started, String phase, long filesDone, long totalFiles,
                      long bytesDone, long totalBytes, AtlasAssetImporter.Summary content,
                      String errorType, String interruptedRun, String log) throws IOException {
        try {
            UUID.fromString(runId);
            byte[] contract = null;
            try (InputStream input = context.getAssets().open("atlas/atlas-import.properties")) {
                ByteArrayOutputStream bytes = new ByteArrayOutputStream();
                byte[] buffer = new byte[4096]; int count;
                while ((count = input.read(buffer)) != -1) {
                    if (bytes.size() + count > 65536) throw new IOException("Import contract is oversized");
                    bytes.write(buffer, 0, count);
                }
                contract = bytes.toByteArray();
            } catch (IOException ignored) { /* Missing metadata must not hide an import failure. */ }
            JSONObject report = new JSONObject().put("format", 1).put("run_id", runId)
                    .put("operation", "verified_content_import").put("status", status)
                    .put("message", message).put("started_epoch_ms", started)
                    .put("finished_epoch_ms", System.currentTimeMillis())
                    .put("app_id", context.getPackageName()).put("app_version", "0.3.0")
                    .put("android_sdk", Build.VERSION.SDK_INT)
                    .put("device", Build.MANUFACTURER + " " + Build.MODEL)
                    .put("content_import_validated", "passed".equals(status))
                    .put("apk_content_contract_available", contract != null)
                    .put("server_execution_validated", false).put("gameplay_validated", false)
                    .put("scope", "Reviewed content preparation only; no game server or graphical client was started")
                    .put("progress", new JSONObject().put("phase", phase).put("files_done", filesDone)
                            .put("total_files", totalFiles).put("bytes_done", bytesDone).put("total_bytes", totalBytes));
            if (errorType != null) report.put("error_type", errorType);
            if (interruptedRun != null) report.put("interrupted_run_id", interruptedRun);
            if (content != null) report.put("available_content", new JSONObject()
                    .put("generation", content.generation).put("file_count", content.count)
                    .put("total_bytes", content.bytes).put("source_commit", content.sourceCommit)
                    .put("data_commit", content.dataCommit).put("repository_commit", content.repositoryCommit)
                    .put("verified_during_this_attempt", "passed".equals(status))
                    .put("inspection_scope", "passed".equals(status)
                            ? "All archived file sizes and hashes were checked during this import"
                            : "Previously committed import receipt; reopening the app does not rescan all content"));
            File directory = new File(home, "reports");
            Files.createDirectories(directory.toPath());
            File target = new File(directory, "coh-atlas-import-" + runId + ".zip");
            File partial = new File(directory, target.getName() + ".part");
            if (target.exists() || partial.exists()) throw new IOException("Report identity already exists");
            try {
                try (FileOutputStream file = new FileOutputStream(partial);
                     ZipOutputStream archive = new ZipOutputStream(file)) {
                    archive.putNextEntry(new ZipEntry("atlas-import-report.json"));
                    archive.write((report.toString(2) + "\n").getBytes(StandardCharsets.UTF_8));
                    archive.closeEntry();
                    archive.putNextEntry(new ZipEntry("import.log"));
                    archive.write(log.getBytes(StandardCharsets.UTF_8));
                    archive.closeEntry();
                    if (contract != null) {
                        archive.putNextEntry(new ZipEntry("atlas-import.properties"));
                        archive.write(contract);
                        archive.closeEntry();
                    }
                    archive.finish(); archive.flush(); file.getFD().sync();
                }
                Files.move(partial.toPath(), target.toPath(), StandardCopyOption.ATOMIC_MOVE);
                return target;
            } finally { Files.deleteIfExists(partial.toPath()); }
        } catch (IOException failure) { throw failure; }
        catch (Exception failure) { throw new IOException("Could not create import report", failure); }
    }
}
