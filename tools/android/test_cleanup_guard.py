#!/usr/bin/env python3
"""Execute the APK's actual process-wide cleanup guard using the host JDK."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'android/app/src/main/java/io/github/russianranger/cohdiagnostic/CleanupGuard.java'
CLASS = 'io.github.russianranger.cohdiagnostic.CleanupGuardHost'
FIXTURE = r'''
package io.github.russianranger.cohdiagnostic;
import java.io.IOException;
import java.io.InterruptedIOException;

public final class CleanupGuardHost {
    static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
    static final class RecreatedService {
        void begin() throws IOException { CleanupGuard.requireClear(); }
    }
    public static void main(String[] args) throws Exception {
        CleanupGuard.requireClear();
        check(!CleanupGuard.isBlocked(), "New app process must start clear");
        check(CleanupGuard.reason().isEmpty(), "Fresh process has no failure reason");
        if (args[0].equals("fresh")) return;
        boolean cancelled = args[0].equals("cancelled");
        boolean failedReport = !args[0].equals("report_ok");
        if (cancelled) Thread.currentThread().interrupt();
        CleanupGuard.Failure failure = CleanupGuard.block(() -> {
            check(CleanupGuard.isBlocked(), "Block must publish before report I/O");
            if (failedReport) {
                if (cancelled) throw new InterruptedIOException("Report interrupted");
                throw new IOException("Storage full");
            }
        });
        check(CleanupGuard.isBlocked(), "Cleanup failure must retain block");
        check(failure.getMessage().contains("Force-stop COH Diagnostic in Android settings"), "Precise recovery instruction");
        check(failure.getSuppressed().length == (failedReport ? 1 : 0), "Preserve report failure without replacing cleanup failure");
        check(Thread.currentThread().isInterrupted() == cancelled, "Cancellation remains recorded");
        for (int i = 0; i < 2; i++) {
            try {
                new RecreatedService().begin();
                throw new AssertionError("Service recreation allowed work");
            } catch (CleanupGuard.Failure blocked) {
                check(blocked == failure, "Service recreation lost original cleanup failure");
            }
        }
        check(!CleanupGuard.reason().contains("has stopped"), "Failure must not claim owned work stopped");
    }
}
'''


class CleanupGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='coh-cleanup-guard-')
        cls.directory = Path(cls.temporary.name)
        fixture = cls.directory / 'CleanupGuardHost.java'
        fixture.write_text(FIXTURE)
        subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                        '-d', str(cls.directory), str(SOURCE), str(fixture)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def execute(self, mode):
        result = subprocess.run(['java', '-cp', str(self.directory), CLASS, mode],
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_cleanup_failure_blocks_recreated_services(self):
        self.execute('report_ok')

    def test_report_failure_cannot_mask_cleanup_failure(self):
        self.execute('report_failed')

    def test_stop_and_interrupted_report_preserve_cleanup_block(self):
        self.execute('cancelled')

    def test_only_a_new_app_process_starts_clear_again(self):
        self.execute('report_failed')
        self.execute('fresh')


if __name__ == '__main__':
    unittest.main()
