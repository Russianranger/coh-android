"""Isolation contract plus live PE32 observation on a Windows/MSVC worker."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "database/wine-game/GameStackProbe.c"


class StackProbePathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which("cc")
        if not compiler:
            raise unittest.SkipTest("portable C compiler is unavailable")
        cls.temporary = tempfile.TemporaryDirectory()
        cls.binary = Path(cls.temporary.name) / "probe-path"
        subprocess.run([compiler, "-std=c99", "-Wall", "-Wextra", "-Werror",
                        "-DCOH_STACK_PROBE_PATH_TEST", str(SOURCE), "-o", str(cls.binary)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def accepted(self, path, runtime=r"Z:\private\runtime"):
        result = subprocess.run([str(self.binary), path, runtime], check=False)
        self.assertIn(result.returncode, (0, 1))
        return result.returncode == 0

    def test_exact_game_image_allowlist_accepts_wine_case_and_separator_forms(self):
        for name in ("DbServer.exe", "MapServer.exe", "TestClient.exe",
                     "TestClientCreate.exe", "TestClientResume.exe"):
            with self.subTest(name=name):
                self.assertTrue(self.accepted("Z:\\private\\runtime\\" + name))
                self.assertTrue(self.accepted("z:/PRIVATE/RUNTIME/" + name.lower(), "Z:/private/runtime/"))

    def test_rejects_sibling_prefixes_nested_paths_and_similarly_named_helpers(self):
        for path in (r"Z:\private\runtime-other\DbServer.exe",
                     r"Z:\private\runtime\nested\DbServer.exe",
                     r"Z:\private\runtime\..\DbServer.exe",
                     r"Z:\private\runtime\TestClientBridge.exe",
                     r"Z:\private\runtime\TestClientUnknown.exe",
                     r"Z:\private\runtime\DbServer.exe.bak",
                     r"Z:\private\runtime\GameStackProbe.exe",
                     r"Y:\private\runtime\DbServer.exe"):
            with self.subTest(path=path):
                self.assertFalse(self.accepted(path))

    def test_root_runtime_and_empty_runtime(self):
        self.assertTrue(self.accepted(r"Z:\DbServer.exe", "Z:\\"))
        self.assertFalse(self.accepted(r"Z:\DbServer.exe", ""))


@unittest.skipUnless(os.name == "nt" and shutil.which("cl"), "requires x86 MSVC Windows worker")
class StackProbeLiveTests(unittest.TestCase):
    def test_observes_only_selected_directory_and_resumes_every_live_thread(self):
        with tempfile.TemporaryDirectory(prefix="coh-stack-probe-") as temporary:
            root = Path(temporary)
            runtime = root / "runtime"
            decoy = root / "runtime-other"
            runtime.mkdir()
            decoy.mkdir()
            probe = root / "GameStackProbe.exe"
            subprocess.run(["cl", "/nologo", "/W4", "/WX", "/O2", "/MT", "/D_WIN32_WINNT=0x0601",
                            str(SOURCE), f"/Fe:{probe}"], cwd=root, check=True)
            target_source = root / "target.c"
            target_source.write_text('''
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
int main(void) {
    unsigned n = 0;
    for (;;) { printf("heartbeat %u\\n", ++n); fflush(stdout); Sleep(10); }
}
''')
            target = runtime / "DbServer.exe"
            subprocess.run(["cl", "/nologo", "/W4", "/WX", "/O2", "/MT", str(target_source),
                            f"/Fe:{target}"], cwd=root, check=True)
            shutil.copy2(target, decoy / "DbServer.exe")
            shutil.copy2(target, runtime / "TestClientBridge.exe")
            children = []
            logs = []
            try:
                for index, executable in enumerate((target, decoy / "DbServer.exe", runtime / "TestClientBridge.exe")):
                    log = (root / f"heartbeat-{index}.log").open("wb")
                    logs.append(log)
                    children.append(subprocess.Popen([str(executable)], stdout=log, stderr=subprocess.STDOUT))
                time.sleep(0.2)
                observed = subprocess.run([str(probe), "--runtime-dir", str(runtime)],
                                          capture_output=True, timeout=15, check=True)
                self.assertLessEqual(len(observed.stdout), 320 * 1024)
                records = [json.loads(line) for line in observed.stdout.splitlines()]
                self.assertEqual(records[0]["kind"], "probe")
                self.assertEqual(records[-1]["kind"], "complete")
                self.assertEqual(records[-1]["errors"], 0)
                self.assertFalse(records[-1]["truncated"])
                self.assertEqual([r["pid"] for r in records if r["kind"] == "process"], [children[0].pid])
                threads = [r for r in records if r["kind"] == "thread"]
                self.assertTrue(threads)
                for thread in threads:
                    self.assertTrue(thread["context_valid"])
                    self.assertTrue(thread["resume_ok"])
                    self.assertLessEqual(len(thread["stack_words"]), 64)
                modules = [r for r in records if r["kind"] == "module"]
                self.assertTrue(any(r["name"].lower() == "dbserver.exe" for r in modules))
                heartbeat = root / "heartbeat-0.log"
                before = heartbeat.stat().st_size
                time.sleep(0.15)
                self.assertGreater(heartbeat.stat().st_size, before, "target must still run after snapshot")
                self.assertTrue(all(child.poll() is None for child in children))
            finally:
                for child in children:
                    child.terminate()
                for child in children:
                    child.wait(timeout=10)
                for log in logs:
                    log.close()


if __name__ == "__main__":
    unittest.main()
