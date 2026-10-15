"""Exercise the same request gate used after a document picker recreates the service."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT / "android/atlas/src/main/java/io/github/russianranger/cohatlas"

FIXTURE = r"""
package io.github.russianranger.cohatlas;

public final class ImportDispatchHost {
    static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
    public static void main(String[] args) {
        // ACTION_OPEN_DOCUMENT removes the only activity binding. Its result
        // reaches a new service before asynchronous receipt inspection ends.
        AtlasImportDispatch<Object> recreated = new AtlasImportDispatch<>();
        Object selected = new Object();
        check(recreated.offer(selected), "New document selection was refused");
        check(recreated.takeReady() == null, "Import bypassed receipt inspection");
        check(!recreated.offer(new Object()), "A second start replaced the selected document");
        check(recreated.initialized() == selected, "Document selection was lost during service initialization");
        check(recreated.takeReady() == null, "Import dispatched twice");
        check(recreated.initialized() == null, "Repeated initialization replayed the import");
        check(!recreated.offer(new Object()), "A running import allowed another operation");
        recreated.finish(selected);

        // Returning while the original service survives must use the same path.
        Object second = new Object();
        check(recreated.offer(second), "Completed import blocked a later selection");
        check(recreated.takeReady() == second, "Initialized service did not dispatch immediately");
        recreated.finish(selected);
        check(!recreated.offer(new Object()), "A delayed previous completion released the current import");
        recreated.finish(second);

        // Process death discards document grants and queued requests; nothing
        // persisted by this helper can restart the old selection automatically.
        AtlasImportDispatch<Object> restarted = new AtlasImportDispatch<>();
        check(restarted.initialized() == null, "Process restart replayed a selected document");
        Object fresh = new Object();
        check(restarted.offer(fresh) && restarted.takeReady() == fresh, "Fresh explicit selection could not run");
    }
}
"""


class ImportDispatchTests(unittest.TestCase):
    def test_picker_service_recreation_and_exactly_once_dispatch(self):
        with tempfile.TemporaryDirectory(prefix="coh-import-dispatch-") as temporary:
            root = Path(temporary)
            fixture = root / "ImportDispatchHost.java"
            fixture.write_text(FIXTURE)
            subprocess.run([
                "java", "-m", "jdk.compiler/com.sun.tools.javac.Main", "--release", "8",
                "-d", str(root), str(JAVA / "AtlasImportDispatch.java"), str(fixture),
            ], check=True, capture_output=True, text=True, timeout=30)
            result = subprocess.run([
                "java", "-cp", str(root), "io.github.russianranger.cohatlas.ImportDispatchHost",
            ], capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
