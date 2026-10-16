"""Reject changed source, unexecuted ABI tampering and false compact authority."""
from pathlib import Path
from types import SimpleNamespace
import copy
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import compact_android as driver
from common import ABIS, CLAIMS, digest, read, write


class CompactAdmission(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.capture = self.root / "catalog.cohcat"
        self.capture.write_bytes(b"exact capture")
        self.provenance = {"catalog": {"bytes": 13, "sha256": digest(self.capture)}}
        self.sources = {}
        for name in driver.REQUIRED.union(driver.DRIVERS):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("source\n")
            self.sources[name] = digest(path)
        fixture = self.root / "android/catalog_fixtures.h"
        fixture.parent.mkdir()
        fixture.write_text("original fixture\n")
        self.expected = dict(passed=True, checks=19, actual_capture_expected_missing_ref=True,
                             world_ready=False, live_allocations=0,
                             actual_candidate_reserved_bytes=4096, actual_peak_live_payload_bytes=8192,
                             actual_audit_named_peak_bytes=16384, actual_references_checked=130314,
                             actual_missing_count=7, actual_missing_stored=7, actual_diagnostics_truncated=0,
                             actual_missing_names=copy.deepcopy(driver.MISSING_NAMES))
        self.host = dict(passed=True, authentic_capture_refusal_tested=True,
                         capture_provenance=self.provenance, source_sha256=copy.deepcopy(self.sources),
                         fixtures_sha256=digest(fixture), checks={mode: copy.deepcopy(self.expected)
                         for mode in ("release", "asan", "ubsan")},
                         **{key: False for key in ("graph_published_from_authentic_capture",
                            "roots_bound", "assets_bound", "renderer_authorized", "android_executed",
                            "physical_thor_accepted")})
        self.proof = dict(schema=driver.SCHEMA, passed=True, android_executed=False,
                          source_revision="a" * 40, source_worktree_dirty=False,
                          source_sha256=copy.deepcopy(self.sources), capture_provenance=self.provenance,
                          expected=copy.deepcopy(self.expected), abis={}, **{key: False for key in CLAIMS})
        for abi, machine in ABIS.items():
            folder = self.root / "android" / abi
            folder.mkdir()
            binary = folder / "test"
            header = bytearray(64)
            header[:7] = b"\x7fELF\x02\x01\x01"
            struct.pack_into("<HHI", header, 16, 3, machine, 1)
            binary.write_bytes(header)
            receipt = folder / "receipt.json"
            write(receipt, dict(passed=True, abi=abi, binary=binary.name, binary_sha256=digest(binary),
                  fixtures_sha256=digest(fixture), source_sha256=self.sources, execution_qualified=False))
            self.proof["abis"][abi] = dict(path=binary.relative_to(self.root).as_posix(), bytes=64,
                sha256=digest(binary), receipt=receipt.relative_to(self.root).as_posix(),
                receipt_sha256=digest(receipt))
        self.save_host()
        for name, value in (("git_state", {"source_revision": "a" * 40}),
                ("catalog_module", SimpleNamespace(admit_capture=lambda _: (self.capture, self.provenance)))):
            mock = patch.object(driver, name, return_value=value)
            mock.start()
            self.addCleanup(mock.stop)

    def save_host(self):
        write(self.root / "host.json", self.host)
        self.proof["host_receipt_sha256"] = digest(self.root / "host.json")

    def validate(self):
        return driver.validate(self.root, self.root, self.proof)

    def test_complete(self):
        self.assertEqual(self.validate(), self.capture)

    def test_live_authority_and_dirty_source_refused(self):
        for key in (*CLAIMS, "android_executed", "source_worktree_dirty"):
            with self.subTest(key=key):
                self.proof[key] = True
                with self.assertRaises(ValueError): self.validate()
                self.proof[key] = False

    def test_changed_source_file(self):
        (self.root / next(iter(driver.REQUIRED))).write_text("changed\n")
        with self.assertRaises(ValueError): self.validate()

    def test_source_omission(self):
        del self.proof["source_sha256"][next(iter(driver.REQUIRED))]
        with self.assertRaises(ValueError): self.validate()

    def test_dependency_omitted_from_every_rehashed_map(self):
        key = "native-android/engine/scenecatalog/coh_scenecatalog.h"
        del self.proof["source_sha256"][key]
        del self.host["source_sha256"][key]
        self.save_host()
        for item in self.proof["abis"].values():
            path = self.root / item["receipt"]
            receipt = read(path); del receipt["source_sha256"][key]; write(path, receipt)
            item["receipt_sha256"] = digest(path)
        with self.assertRaises(ValueError): self.validate()

    def test_host_source_mismatch(self):
        self.host["source_sha256"][next(iter(driver.REQUIRED))] = "b" * 64
        self.save_host()
        with self.assertRaises(ValueError): self.validate()

    def test_wrong_revision(self):
        self.proof["source_revision"] = "b" * 40
        with self.assertRaises(ValueError): self.validate()

    def test_missing_abi(self):
        del self.proof["abis"]["arm64-v8a"]
        with self.assertRaises(ValueError): self.validate()

    def test_unexecuted_abi_binary_changed_same_length(self):
        item = self.proof["abis"]["arm64-v8a"]
        path = self.root / item["path"]
        data = bytearray(path.read_bytes()); data[-1] ^= 1; path.write_bytes(data)
        with self.assertRaises(ValueError): self.validate()

    def test_unexecuted_abi_fixture_receipt_changed(self):
        item = self.proof["abis"]["arm64-v8a"]
        path = self.root / item["receipt"]
        receipt = read(path); receipt["fixtures_sha256"] = "f" * 64; write(path, receipt)
        item["receipt_sha256"] = digest(path)
        with self.assertRaises(ValueError): self.validate()

    def test_abi_relabelled(self):
        self.proof["abis"]["arm64-v8a"] = self.proof["abis"]["x86_64"]
        with self.assertRaises(ValueError): self.validate()

    def test_fixture_changed(self):
        (self.root / "android/catalog_fixtures.h").write_text("different fixture\n")
        with self.assertRaises(ValueError): self.validate()

    def test_host_authority_claims(self):
        for key in ("graph_published_from_authentic_capture", "roots_bound", "assets_bound", "renderer_authorized"):
            with self.subTest(key=key):
                self.host[key] = True; self.save_host()
                with self.assertRaises(ValueError): self.validate()
                self.host[key] = False
        self.save_host()

    def test_refusal_memory_and_cleanup_required(self):
        for key, value in (("actual_capture_expected_missing_ref", False), ("world_ready", True),
                           ("live_allocations", 1), ("actual_peak_live_payload_bytes", 97 * 1024**2),
                           ("actual_candidate_reserved_bytes", True)):
            with self.subTest(key=key):
                old = self.proof["expected"][key]; self.proof["expected"][key] = value
                with self.assertRaises(ValueError): self.validate()
                self.proof["expected"][key] = old

    def test_sanitizer_result_mismatch(self):
        self.host["checks"]["asan"]["checks"] = 18; self.save_host()
        with self.assertRaises(ValueError): self.validate()

    def test_exact_missing_identity_required(self):
        for key, value in (("actual_references_checked", 130313), ("actual_missing_count", 6),
                           ("actual_missing_stored", 6), ("actual_diagnostics_truncated", 1),
                           ("actual_missing_names", ["invented"]), ("live_allocations", False)):
            with self.subTest(key=key):
                old = self.proof["expected"][key]; self.proof["expected"][key] = value
                with self.assertRaises(ValueError): self.validate()
                self.proof["expected"][key] = old


if __name__ == "__main__":
    unittest.main()
