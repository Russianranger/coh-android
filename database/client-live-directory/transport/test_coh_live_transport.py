#!/usr/bin/env python3
"""Portable source-only transport controls; no SDK/native/device qualification."""
from __future__ import annotations
import hashlib
import json
import pathlib
import subprocess
import tempfile
import unittest
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent
IMMUTABLE_BYTES = 4316
IMMUTABLE_SHA256 = "767077bfefa2f023fbb558a0757d95e0d2021b2b12da7c4c18d25c6591292fc6"
GROUPS = ("basic", "malformed", "acknowledgements", "io", "declines", "bounds", "allocation", "paths", "empty-full")

class TransportControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / "portable-control-report.json").unlink(missing_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(prefix="coh-live-transport-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.executable = pathlib.Path(cls.temporary.name) / "transport-controls"
        cls.tcp_executable = pathlib.Path(cls.temporary.name) / "tcp-controls"
        cls.results = []
        subprocess.run([
            "cc", "-std=c99", "-O2", "-Wall", "-Wextra", "-Werror",
            # The frozen decoder predates this fixture; do not edit its bytes.
            "-Wno-misleading-indentation", "-I", str(ROOT),
            str(ROOT / "coh_live_transport.c"), str(ROOT / "transport_fixture.c"),
            "-o", str(cls.executable),
        ], check=True, capture_output=True, text=True)
        subprocess.run([
            "cc", "-std=c99", "-O2", "-Wall", "-Wextra", "-Werror",
            "-Wno-misleading-indentation", "-I", str(ROOT),
            str(ROOT / "coh_live_transport.c"), str(ROOT / "transport_tcp_fixture.c"),
            "-o", str(cls.tcp_executable),
        ], check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        if len(cls.results) == len(GROUPS) + 1:
            pins = []
            for name in ("coh_live_directory_batch.h", "coh_live_transport.h", "coh_live_transport.c", "transport_fixture.c", "transport_tcp_fixture.c", "test_coh_live_transport.py"):
                data = (ROOT / name).read_bytes()
                pins.append({"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
            report = {
                "schema": "coh-live-transport-portable-controls-v1",
                "source_only": True,
                "groups": cls.results,
                "c_checks": sum(r["checks"] for r in cls.results),
                "groups_passed": len(cls.results),
                "skipped": 0,
                "source_pins": pins,
                "authority": {"native_game": False, "wine": False, "fex": False,
                              "proot": False, "android": False, "thor": False,
                              "provider_ownership": False, "production": False},
            }
            (ROOT / "portable-control-report.json").write_text(json.dumps(report, indent=2) + "\n")
        cls.temporary.cleanup()

    def test_immutable_decoder(self):
        data = (ROOT / "coh_live_directory_batch.h").read_bytes()
        self.assertEqual(len(data), IMMUTABLE_BYTES)
        self.assertEqual(hashlib.sha256(data).hexdigest(), IMMUTABLE_SHA256)

    def test_installed_repository_layout_has_no_scratch_authority_dependency(self):
        with tempfile.TemporaryDirectory(prefix="coh-live-installed-") as temporary:
            directory=pathlib.Path(temporary)/"database/client-live-directory/transport"
            directory.mkdir(parents=True)
            for name in ("test_coh_live_transport.py","coh_live_directory_batch.h","coh_live_transport.h",
                         "coh_live_transport.c","transport_fixture.c","transport_tcp_fixture.c"):
                shutil.copyfile(ROOT/name,directory/name)
            self.assertFalse((pathlib.Path(temporary)/"database/native037-recovery").exists())
            result=subprocess.run([sys.executable,"-W","error::ResourceWarning","-m","unittest",
                                   "test_coh_live_transport.TransportControls.test_immutable_decoder"],
                                  cwd=directory,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_host_tcpv4_byte_stream(self):
        result = subprocess.run([str(self.tcp_executable)], check=True, capture_output=True, text=True, timeout=10)
        value = json.loads(result.stdout)
        self.assertTrue(value["passed"])
        self.assertFalse(value["native_authority"])
        self.results.append(value)

def control(group):
    def test(self):
        result = subprocess.run([str(self.executable), group], check=True, capture_output=True, text=True)
        value = json.loads(result.stdout)
        self.assertTrue(value["passed"])
        self.assertGreater(value["checks"], 0)
        self.results.append(value)
    return test

for group in GROUPS:
    setattr(TransportControls, "test_" + group.replace("-", "_"), control(group))

if __name__ == "__main__":
    unittest.main(verbosity=2)
