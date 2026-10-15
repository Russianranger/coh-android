"""New successor host policy tests; never Android/Wine/FEX/PRoot admission.

Runs real Java 8-target bytecode. Java source compiler is available in the JRE's
jdk.compiler module here even when a javac executable is not on PATH. The Android
API-only collector is deliberately excluded: no Android SDK exists on this host.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "io.github.russianranger.cohclientinteractive.recovery037"
SOURCE = ROOT / "source" / Path(PACKAGE.replace(".", "/")) / "InstalledPackagePreflight.java"
HARNESS = ROOT / "tests/InstalledPackagePreflightHarness.java"
CASES = [
    "system-owned-library-valid", "closed-after-valid", "defensive-pins", "defensive-observation",
    "missing-pin", "wrong-package", "wrong-context", "wrong-process-uid", "wrong-package-uid",
    "wrong-version", "wrong-update", "wrong-source", "wrong-native-dir", "wrong-signer",
    "rotation-history-is-not-current", "missing-roots", "root-system-owned", "root-object-alias",
    "root-mixed-device-current",
    *[f"library-{field}" for field in ("path", "canonical", "device", "inode", "zero-device", "zero-inode",
        "negative-uid", "symlink", "directory", "writable", "bytes", "mtime", "ctime", "digest")],
    *[f"apk-{field}" for field in ("path", "canonical", "inode", "writable", "bytes", "digest", "ctime")],
    *[f"root-{field}" for field in ("path", "canonical", "device", "inode", "uid", "symlink", "regular",
        "writable", "mtime", "ctime")],
    "pin-too-few-roots", "pin-wrong-order", "pin-root-escape", "pin-dot-root", "pin-double-slash",
    "pin-duplicate-root", "pin-empty-signer", "pin-malformed-signer", "pin-duplicate-signer",
]


class InstalledPackagePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix="coh037-package-policy-")
        cls.classes = Path(cls.scratch.name)
        cls.java = os.environ.get("COH_POLICY_JAVA") or shutil.which("java")
        if not cls.java:
            raise RuntimeError("Java required; do not count an unavailable compiler as passing")
        subprocess.run([cls.java, "com.sun.tools.javac.Main", "--release", "8", "-d", str(cls.classes),
                        str(SOURCE), str(HARNESS)], check=True, capture_output=True, text=True, timeout=60)

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    def execute_case(self, case):
        completed = subprocess.run([self.java, "-cp", str(self.classes), PACKAGE + ".InstalledPackagePreflightHarness", case],
                                   check=True, capture_output=True, text=True, timeout=10)
        self.assertEqual(completed.stdout.strip(), f"host_policy_pass:{case};android_admission=false")


for case in CASES:
    setattr(InstalledPackagePolicyTests, "test_" + case.replace("-", "_"),
            lambda self, case=case: self.execute_case(case))

if __name__ == "__main__":
    unittest.main()
