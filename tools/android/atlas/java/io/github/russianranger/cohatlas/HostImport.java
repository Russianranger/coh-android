package io.github.russianranger.cohatlas;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

/** Runs the unmodified Android importer core with real APK assets on a host JVM. */
public final class HostImport {
    private static void require(boolean value, String message) throws IOException {
        if (!value) throw new IOException(message);
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 4) throw new IllegalArgumentException("assets archive private-base summary");
        final File assets = new File(args[0]);
        File archive = new File(args[1]), base = new File(args[2]), summaryFile = new File(args[3]);
        AtlasAssetImporter importer = new AtlasAssetImporter(base,
                name -> new FileInputStream(new File(assets, name)));
        require(importer.inspect() == null, "Host import must begin with fresh state");
        AtlasAssetImporter.Control successful = new AtlasAssetImporter.Control();
        final long[] last = {0};
        final String[] phase = {""};
        AtlasAssetImporter.Summary result;
        try (InputStream selected = new FileInputStream(archive)) {
            result = importer.importArchive(selected, (label, files, totalFiles, bytes, totalBytes) -> {
                long now = System.nanoTime();
                if (!label.equals(phase[0]) || now - last[0] > 5000000000L) {
                    System.out.println(label + ": " + files + "/" + totalFiles + " files, "
                            + bytes + "/" + totalBytes + " bytes");
                    phase[0] = label;
                    last[0] = now;
                }
            }, successful);
        }
        require(successful.isCommitted() && !successful.requestCancel(),
                "A completed import must not accept a late Stop");
        require(result.generation.equals(importer.inspect().generation), "Active generation differs");

        // An interrupted second import must leave the complete first import active.
        final AtlasAssetImporter.Control stopped = new AtlasAssetImporter.Control();
        boolean cancelled = false;
        try (InputStream selected = new FileInputStream(archive)) {
            importer.importArchive(selected, (label, files, totalFiles, bytes, totalBytes) -> {
                if (label.equals("Checking selected asset archive") && bytes > 0)
                    requireStop(stopped.requestCancel());
            }, stopped);
        } catch (AtlasAssetImporter.CancelledException expected) {
            cancelled = true;
        }
        require(cancelled && !stopped.isCommitted(), "Reimport cancellation did not take effect");
        require(result.generation.equals(importer.inspect().generation), "Stop changed active content");

        // Model process death after staging starts and before the active pointer moves.
        File abandoned = new File(base, ".import-ffffffffffffffffffffffffffffffff");
        require(abandoned.mkdir(), "Could not create interruption fixture");
        Files.write(new File(abandoned, "partial.bin").toPath(), new byte[]{1, 2, 3});
        importer.recover();
        require(!abandoned.exists() && result.generation.equals(importer.inspect().generation),
                "Recovery did not preserve the completed content");
        String summary = "status=passed\nsource.commit=" + result.sourceCommit
                + "\ndata.commit=" + result.dataCommit + "\nrepository.commit=" + result.repositoryCommit
                + "\ncount=" + result.count + "\nbytes=" + result.bytes
                + "\ndata.directory=" + result.dataDirectory.getCanonicalPath()
                + "\nrecovery=passed\ncancel=passed\n";
        Files.write(summaryFile.toPath(), summary.getBytes(StandardCharsets.US_ASCII));
        System.out.println("Complete import, cancelled reimport and interrupted-stage recovery passed.");
    }

    private static void requireStop(boolean accepted) {
        if (!accepted) throw new IllegalStateException("Stop was not accepted during input copy");
    }
}
