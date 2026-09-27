package io.github.russianranger.cohdiagnostic;

import java.io.IOException;

/** A failed owned-process cleanup blocks this entire app process, not an Activity. */
final class CleanupGuard {
    private static final String MESSAGE = "Owned runtime did not finish stopping. Force-stop COH Diagnostic in Android settings, then reopen it before starting more work.";
    private static volatile Failure failure;

    static final class Failure extends IOException {
        private Failure() { super(MESSAGE); }
    }

    interface ReportWriter { void write() throws Exception; }

    static boolean isBlocked() { return failure != null; }
    static String reason() { return isBlocked() ? MESSAGE : ""; }

    static void requireClear() throws Failure {
        Failure current = failure;
        if (current != null) throw current;
    }

    static Failure block(ReportWriter reportWriter) {
        Failure blocked = new Failure();
        // Publish before any fallible I/O. No Activity/service recreation or
        // unsuccessful report export can clear the process-wide block.
        failure = blocked;
        try { reportWriter.write(); }
        catch (Exception reportFailure) { blocked.addSuppressed(reportFailure); }
        return blocked;
    }

    private CleanupGuard() {}
}
