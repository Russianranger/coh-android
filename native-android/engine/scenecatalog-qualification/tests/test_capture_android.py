"""Captured-input and mixed-build refusal controls, without Android or a server."""
from pathlib import Path
from types import SimpleNamespace
import copy
import struct
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import capture_android as driver
from common import ABIS, CLAIMS, digest, write


class CaptureAdmission(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.capture = self.root / "capture.cohcat"
        self.capture.write_bytes(b"capture")
        self.sources = {path: "b" * 64 for path in driver.SOURCES}
        self.provenance = {"catalog": {"bytes": 7, "generation": 19},
                           "observations": {"definitions": 2, "files": 1, "slots": 2,
                                            "children": 0, "active_roots": 1,
                                            "definitions_crc": 42, "references_crc": 43}}
        self.expected = {**self.provenance["observations"], "native_decode_completed": True,
                         "status": 0, "validation_mode": "stream", "catalog_materialized": False,
                         "graph_published": False, "renderer_authorized": False,
                         "failed_record_peak_unknown": False, "records_validated": 2,
                         "input_bytes": 7, "generation": 19, "peak_working_bytes": 8192,
                         "peak_aggregate_bytes": 8192, "owned_bytes": 0, "stage": 6, "offset": 7,
                         "working_upper_bound": 32 * 1024**2, "aggregate_upper_bound": 32 * 1024**2}
        result = dict(authentic_capture_stream=self.expected, malformed_rejections=24,
                      unchanged_materializer_refusal={"status": 4})
        self.host = dict(passed=True, authentic_capture_validated=True,
                         authentic_capture_provenance=self.provenance, source_sha256=self.sources,
                         checks={mode: copy.deepcopy(result) for mode in ("release", "asan", "ubsan")})
        self.proof = dict(schema=driver.SCHEMA, passed=True, android_executed=False,
                          source_revision="a" * 40, source_worktree_dirty=False,
                          source_sha256=self.sources, capture_provenance=self.provenance,
                          expected=self.expected, abis={}, **{key: False for key in CLAIMS})
        for abi, machine in ABIS.items():
            path = self.root / abi
            data = bytearray(64)
            data[:7] = b"\x7fELF\x02\x01\x01"
            struct.pack_into("<HHI", data, 16, 3, machine, 1)
            path.write_bytes(data)
            self.proof["abis"][abi] = dict(path=abi, bytes=64, sha256=digest(path))
        self.save_host()
        for name, value in (("inventory", self.sources),
                            ("git_state", {"source_revision": "a" * 40}),
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

    def test_claims_and_unclean_build(self):
        for field in (*CLAIMS, "android_executed", "source_worktree_dirty"):
            with self.subTest(field=field):
                old = self.proof[field]
                self.proof[field] = True
                with self.assertRaises(ValueError): self.validate()
                self.proof[field] = old

    def test_wrong_source_revision(self):
        self.proof["source_revision"] = "c" * 40
        with self.assertRaises(ValueError): self.validate()

    def test_missing_source_closure(self):
        self.proof["source_sha256"] = {}
        with self.assertRaises(ValueError): self.validate()

    def test_host_byte_identity(self):
        (self.root / "host.json").write_text("{}")
        with self.assertRaises(ValueError): self.validate()

    def test_host_source_omission(self):
        self.host["source_sha256"] = {}
        self.save_host()
        with self.assertRaises(ValueError): self.validate()

    def test_host_sanitizer_parity(self):
        self.host["checks"]["asan"]["authentic_capture_stream"]["records_validated"] = 1
        self.save_host()
        with self.assertRaises(ValueError): self.validate()

    def test_refusal_control(self):
        self.host["checks"]["ubsan"]["unchanged_materializer_refusal"]["status"] = 0
        self.save_host()
        with self.assertRaises(ValueError): self.validate()

    def test_missing_other_abi(self):
        del self.proof["abis"]["arm64-v8a"]
        with self.assertRaises(ValueError): self.validate()

    def test_changed_other_abi(self):
        (self.root / "arm64-v8a").write_bytes(b"changed")
        with self.assertRaises(ValueError): self.validate()

    def test_relabelled_other_abi(self):
        self.proof["abis"]["arm64-v8a"] = self.proof["abis"]["x86_64"]
        with self.assertRaises(ValueError): self.validate()

    def test_complete_counts_and_limits(self):
        changes = {"definitions": 1, "references_crc": 44, "records_validated": 1,
                   "generation": 20, "input_bytes": 8, "peak_working_bytes": 33 * 1024**2,
                   "peak_aggregate_bytes": 97 * 1024**2, "failed_record_peak_unknown": True,
                   "graph_published": True, "renderer_authorized": True, "catalog_materialized": True,
                   "offset": 6, "stage": 5, "owned_bytes": 1, "working_upper_bound": 0,
                   "aggregate_upper_bound": 97 * 1024**2, "status": False}
        for field, value in changes.items():
            with self.subTest(field=field):
                old = self.expected[field]
                self.expected[field] = value
                with self.assertRaises(ValueError): self.validate()
                self.expected[field] = old


class ArchiveAdmission(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.archive = self.root / "capture.zip"
        with zipfile.ZipFile(self.archive, "w") as bundle:
            bundle.writestr("capture/catalog.cohcat", b"catalog")
            bundle.writestr("capture/capture-receipt.json", b"{}")
            bundle.writestr("../ignored", b"not extracted")
        self.manifest = dict(artifact=dict(bytes=self.archive.stat().st_size, sha256=digest(self.archive)),
                             catalog=dict(path="capture/catalog.cohcat", bytes=7))

    def test_exact_selected_members_only(self):
        driver.extract_capture(self.archive, self.root / "out", self.manifest)
        self.assertEqual((self.root / "out/capture/catalog.cohcat").read_bytes(), b"catalog")
        self.assertFalse((self.root / "ignored").exists())

    def test_zip_hash_mismatch(self):
        self.manifest["artifact"]["sha256"] = "a" * 64
        with self.assertRaises(ValueError): driver.extract_capture(self.archive, self.root / "out", self.manifest)

    def test_member_limit(self):
        self.manifest["catalog"]["bytes"] = 6
        with self.assertRaises(ValueError): driver.extract_capture(self.archive, self.root / "out", self.manifest)


if __name__ == "__main__":
    unittest.main()
