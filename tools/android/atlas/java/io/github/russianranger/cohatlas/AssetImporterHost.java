package io.github.russianranger.cohatlas;

import java.io.*;
import java.nio.channels.*;
import java.nio.file.*;
import java.util.Properties;

/** Small fixture driver; exercises the same class shipped in the Android APK. */
public final class AssetImporterHost {
    public static void main(String[] args) throws Exception {
        File assets = new File(args[0]), base = new File(args[1]);
        String mode = args[2];
        Properties output = new Properties();
        AtlasAssetImporter.Control control = new AtlasAssetImporter.Control();
        try {
            final int[] spaceChecks = {0};
            AtlasAssetImporter importer = new AtlasAssetImporter(base, name -> new FileInputStream(new File(assets, name)),
                    directory -> mode.equals("no-space") || (mode.equals("fill-space") && spaceChecks[0]++ > 0) ? 0 : Long.MAX_VALUE);
            AtlasAssetImporter.Summary summary;
            if (mode.equals("inspect")) summary = importer.inspect();
            else if (mode.equals("recover")) { importer.recover(); summary = importer.inspect(); }
            else if (mode.equals("locked")) {
                try (FileChannel channel = FileChannel.open(base.toPath().resolve("import.lock"), StandardOpenOption.WRITE);
                     FileLock ignored = channel.lock()) {
                    summary = importer.importArchive(new FileInputStream(args[3]), null, control);
                }
            } else {
                if (mode.equals("cancel-before")) control.requestCancel();
                AtlasAssetImporter.Progress progress = (phase, files, totalFiles, bytes, totalBytes) -> {
                    if ((mode.equals("kill-copy") && phase.equals("Checking selected asset archive") && bytes > 0)
                            || (mode.equals("kill-publish") && phase.equals("Publishing verified content")))
                        Runtime.getRuntime().halt(17); // Simulate process death: no finally/close callbacks.
                    boolean stop = mode.equals("cancel-copy") && phase.equals("Checking selected asset archive") && bytes > 0;
                    stop |= mode.equals("cancel-extract") && phase.equals("Installing verified content") && files > 0;
                    stop |= mode.equals("cancel-publish") && phase.equals("Publishing verified content");
                    if (stop) control.requestCancel();
                };
                InputStream input = new FileInputStream(args[3]);
                if (mode.equals("bad-close")) input = new FilterInputStream(input) {
                    @Override public void close() throws IOException { super.close(); throw new IOException("Synthetic close failure"); }
                };
                summary = importer.importArchive(input, progress, control);
                output.setProperty("stopAcceptedAfterCommit", Boolean.toString(control.requestCancel()));
            }
            output.setProperty("status", summary == null ? "absent" : "ok");
            if (summary != null) {
                output.setProperty("generation", summary.generation);
                output.setProperty("dataDirectory", summary.dataDirectory.toString());
                output.setProperty("count", Long.toString(summary.count));
                output.setProperty("bytes", Long.toString(summary.bytes));
            }
        } catch (IOException error) {
            output.setProperty("status", error instanceof AtlasAssetImporter.CancelledException ? "cancelled" : "error");
            output.setProperty("message", String.valueOf(error.getMessage()));
        }
        output.setProperty("committed", Boolean.toString(control.isCommitted()));
        output.store(System.out, "fixture result");
    }
}
