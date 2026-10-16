"""Reject mixed, tampered and overclaiming Android qualification artifacts."""
from pathlib import Path
import copy
import json
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ABIS, CLAIMS, FIXTURES, MODULES, digest, json_equal, native_result, write
from run_android import validate


class ArtifactAdmission(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.manifest = {"schema": "coh-primary-continuation-android-v1", "passed": True,
                         "source_revision": "a" * 40, "suites": {}, **{key: False for key in CLAIMS}}
        for module in MODULES:
            result = {"passed": True, "checks": 37, "real_account_login_verified": False}
            host = self.root / module / "host.json"
            fixture = None
            host_result = {"passed": True, "checks": {"release": result}}
            if module in FIXTURES:
                fixture_path = self.root / module / FIXTURES[module]
                fixture_path.parent.mkdir(parents=True, exist_ok=True)
                fixture_path.write_text("/* original-source fixture bytes */\n")
                fixture = {"path": fixture_path.relative_to(self.root).as_posix(), "sha256": digest(fixture_path)}
                host_result["fixtures_sha256"] = fixture["sha256"]
            write(host, host_result)
            suite = {"expected": result, "abis": {},
                     "fixture": fixture,
                     "host_receipt": host.relative_to(self.root).as_posix(),
                     "host_receipt_sha256": digest(host)}
            for abi, machine in ABIS.items():
                folder = self.root / module / abi
                folder.mkdir(parents=True)
                binary = folder / "test_contract"
                header = bytearray(64)
                header[:7] = b"\x7fELF\x02\x01\x01"
                struct.pack_into("<HH", header, 16, 3, machine)
                binary.write_bytes(header)
                receipt = folder / "receipt.json"
                receipt_value = {"passed": True, "abi": abi, "binary": binary.name, "binary_sha256": digest(binary)}
                if fixture:
                    receipt_value["fixtures_sha256"] = fixture["sha256"]
                write(receipt, receipt_value)
                suite["abis"][abi] = {"abi": abi, "binary": binary.relative_to(self.root).as_posix(),
                    "sha256": digest(binary), "bytes": 64,
                    "receipt": receipt.relative_to(self.root).as_posix(), "receipt_sha256": digest(receipt)}
            self.manifest["suites"][module] = suite

    def test_complete_manifest(self):
        for abi in ABIS:
            self.assertEqual(set(validate(self.root, self.manifest, abi)), set(MODULES))

    def test_missing_suite_or_abi(self):
        for missing_abi in (False, True):
            value = copy.deepcopy(self.manifest)
            if missing_abi:
                del value["suites"][MODULES[0]]["abis"]["arm64-v8a"]
            else:
                del value["suites"][MODULES[0]]
            with self.assertRaises(ValueError):
                validate(self.root, value, "x86_64")

    def test_tampered_bytes_receipt_and_host(self):
        suite = self.manifest["suites"][MODULES[0]]
        for relative in (suite["abis"]["x86_64"]["binary"], suite["abis"]["x86_64"]["receipt"], suite["host_receipt"]):
            target = self.root / relative
            old = target.read_bytes()
            target.write_bytes(old + b" ")
            with self.assertRaises(ValueError):
                validate(self.root, self.manifest, "x86_64")
            target.write_bytes(old)

    def test_wrong_machine_even_with_rehashed_receipt(self):
        suite = self.manifest["suites"][MODULES[0]]
        descriptor = suite["abis"]["x86_64"]
        binary = self.root / descriptor["binary"]
        data = bytearray(binary.read_bytes())
        struct.pack_into("<H", data, 18, ABIS["arm64-v8a"])
        binary.write_bytes(data)
        descriptor["sha256"] = digest(binary)
        receipt = self.root / descriptor["receipt"]
        value = json.loads(receipt.read_text())
        value["binary_sha256"] = descriptor["sha256"]
        write(receipt, value)
        descriptor["receipt_sha256"] = digest(receipt)
        with self.assertRaises(ValueError):
            validate(self.root, self.manifest, "x86_64")

    def test_tampered_source_fixture(self):
        fixture = self.manifest["suites"]["scenegraph"]["fixture"]
        (self.root / fixture["path"]).write_text("/* changed fixture */\n")
        with self.assertRaises(ValueError):
            validate(self.root, self.manifest, "x86_64")

    def test_unexecuted_abi_fixture_must_also_match_host(self):
        descriptor = self.manifest["suites"]["entities"]["abis"]["arm64-v8a"]
        path = self.root / descriptor["receipt"]
        value = json.loads(path.read_text())
        value["fixtures_sha256"] = "0" * 64
        write(path, value)
        descriptor["receipt_sha256"] = digest(path)
        with self.assertRaises(ValueError):
            validate(self.root, self.manifest, "x86_64")

    def test_path_escape_and_symlink(self):
        descriptor = self.manifest["suites"][MODULES[0]]["abis"]["x86_64"]
        descriptor["binary"] = "../outside"
        with self.assertRaises(ValueError):
            validate(self.root, self.manifest, "x86_64")
        (self.root / "escape").symlink_to(Path(__file__).resolve())
        descriptor["binary"] = "escape"
        with self.assertRaises(ValueError):
            validate(self.root, self.manifest, "x86_64")

    def test_unsupported_qualification_claims(self):
        for claim in CLAIMS:
            value = copy.deepcopy(self.manifest)
            value[claim] = True
            with self.assertRaises(ValueError):
                validate(self.root, value, "x86_64")

    def test_result_is_bound_to_host_oracle(self):
        self.manifest["suites"][MODULES[0]]["expected"]["checks"] += 1
        with self.assertRaises(ValueError):
            validate(self.root, self.manifest, "x86_64")

    def test_native_evidence_types_and_scope(self):
        for result in ({"passed": True, "checks": True}, {"passed": 1, "checks": 3},
                       {"passed": True, "checks": 0},
                       {"passed": True, "checks": 3, "live_world": True}):
            with self.assertRaises(ValueError):
                native_result(result)
        self.assertFalse(json_equal({"count": 1}, {"count": True}))
        self.assertTrue(json_equal({"count": 1}, {"count": 1}))


if __name__ == "__main__":
    unittest.main()
