package io.github.russianranger.cohdiagnostic;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.UUID;

/** A completed report is immutable, including while a document picker is open. */
final class DiagnosticReports {
    final String runId = UUID.randomUUID().toString();
    final File target;
    private final File partial;

    DiagnosticReports(File home) {
        File directory = new File(home, "reports");
        target = new File(directory, "coh-diagnostic-" + runId + ".zip");
        partial = new File(directory, target.getName() + ".part");
    }

    File prepare() throws IOException {
        if (target.exists()) throw new IOException("A completed report cannot be overwritten");
        Files.createDirectories(target.getParentFile().toPath());
        Files.createFile(partial.toPath());
        return partial;
    }

    void publish() throws IOException {
        if (target.exists()) throw new IOException("A completed report cannot be overwritten");
        Files.move(partial.toPath(), target.toPath(), StandardCopyOption.ATOMIC_MOVE);
    }

    void discardPartial() { partial.delete(); }
}
