"""Exercise serialization of setup, import and Atlas tests across service recreation."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT / "android/atlasgame/src/main/java/io/github/russianranger/cohatlastest"

FIXTURE = r"""
package io.github.russianranger.cohatlastest;

public final class OperationDispatchHost {
    static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
    public static void main(String[] args) {
        // ACTION_OPEN_DOCUMENT removes the only activity binding. Its result
        // reaches a new service before asynchronous receipt inspection ends.
        AtlasOperationDispatch<Object> recreated = new AtlasOperationDispatch<>();
        Object selected = "import";
        check(recreated.offer(selected), "New document selection was refused");
        check(recreated.takeReady() == null, "Import bypassed receipt inspection");
        check(!recreated.offer(new Object()), "A second start replaced the selected document");
        check(recreated.initialized() == selected, "Document selection was lost during service initialization");
        check(recreated.takeReady() == null, "Import dispatched twice");
        check(recreated.initialized() == null, "Repeated initialization replayed the import");
        check(!recreated.offer(new Object()), "A running import allowed another operation");
        recreated.finish(selected);

        // Returning while the original service survives must use the same path.
        Object second = "atlas_server_test";
        check(recreated.offer(second), "Completed import blocked a later selection");
        check(recreated.takeReady() == second, "Initialized service did not dispatch immediately");
        recreated.finish(selected);
        check(!recreated.offer(new Object()), "A delayed previous completion released the current import");
        recreated.finish(second);

        // Process death discards document grants and queued requests; nothing
        // persisted by this helper can restart the old selection automatically.
        AtlasOperationDispatch<Object> restarted = new AtlasOperationDispatch<>();
        check(restarted.initialized() == null, "Process restart replayed a selected document");
        Object fresh = "runtime_setup";
        check(restarted.offer(fresh) && restarted.takeReady() == fresh, "Fresh explicit selection could not run");
    }
}
"""


class OperationDispatchTests(unittest.TestCase):
    def test_picker_service_recreation_and_exactly_once_dispatch(self):
        with tempfile.TemporaryDirectory(prefix="coh-operation-dispatch-") as temporary:
            root = Path(temporary)
            fixture = root / "OperationDispatchHost.java"
            fixture.write_text(FIXTURE)
            subprocess.run([
                "java", "-m", "jdk.compiler/com.sun.tools.javac.Main", "--release", "8",
                "-d", str(root), str(JAVA / "AtlasOperationDispatch.java"), str(fixture),
            ], check=True, capture_output=True, text=True, timeout=30)
            result = subprocess.run([
                "java", "-cp", str(root), "io.github.russianranger.cohatlastest.OperationDispatchHost",
            ], capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
