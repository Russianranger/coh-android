"""Malformed or mixed evidence must fail before the Android runner is used."""
from pathlib import Path
import copy
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (ABIS, CLAIMS, FIXTURES, MODULES, REQUIRED_SOURCES, SCHEMA, child, digest,
                    json_equal, loads, native_result, read, verify_sources, write)
from run_android import validate
from qualify import inventory


class ArtifactAdmission(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.manifest = {"schema": SCHEMA, "passed": True, "android_executed": False,
            "sanitizers_passed": True, "source_worktree_dirty": False,
            "source_revision": "a" * 40, "suites": {}, "source_sha256": {},
            **{key: False for key in CLAIMS}}
        for module in MODULES:
            result = {"passed": True, "checks": 37, "real_account_login_verified": False}
            sources = {path: "b" * 64 for path in REQUIRED_SOURCES[module]}
            self.manifest["source_sha256"].update(sources)
            fixture_path = self.root / module / FIXTURES[module]
            fixture_path.parent.mkdir(parents=True, exist_ok=True)
            fixture_path.write_text("/* exact original-source fixture bytes */\n")
            fixture = {"path": fixture_path.relative_to(self.root).as_posix(), "sha256": digest(fixture_path)}
            costume = None
            extra = {}
            if module == "entities":
                path = self.root / module / "costume_fixtures.h"
                path.write_text("/* original costume fixture */\n")
                costume = {"path": path.relative_to(self.root).as_posix(), "sha256": digest(path)}
                extra["costume_fixtures_sha256"] = costume["sha256"]
            host = self.root / module / "host.json"
            write(host, {**extra, "passed": True, "fixtures": 4, "fixtures_sha256": fixture["sha256"],
                "source_sha256": sources, "checks": {mode: result for mode in ("release", "asan", "ubsan")}})
            suite = {"expected": result, "abis": {}, "fixture": fixture, "costume_fixture": costume, "source_sha256": sources,
                "host_receipt": host.relative_to(self.root).as_posix(), "host_receipt_sha256": digest(host)}
            for abi, machine in ABIS.items():
                folder = self.root / module / abi
                folder.mkdir(parents=True)
                binary = folder / "test_contract"
                header = bytearray(64)
                header[:7] = b"\x7fELF\x02\x01\x01"
                struct.pack_into("<HHI", header, 16, 3, machine, 1)
                binary.write_bytes(header)
                receipt = folder / "receipt.json"
                write(receipt, {**extra, "passed": True, "abi": abi, "binary": binary.name,
                    "binary_sha256": digest(binary), "fixtures_sha256": fixture["sha256"],
                    "source_sha256": sources, "executed": False})
                suite["abis"][abi] = {"abi": abi, "binary": binary.relative_to(self.root).as_posix(),
                    "sha256": digest(binary), "bytes": 64,
                    "receipt": receipt.relative_to(self.root).as_posix(), "receipt_sha256": digest(receipt)}
            self.manifest["suites"][module] = suite

    def validate(self, value=None):
        return validate(self.root, self.manifest if value is None else value, "x86_64")

    def change_receipt(self, module, abi, field, value):
        item = self.manifest["suites"][module]["abis"][abi]
        path = self.root / item["receipt"]
        receipt = read(path)
        receipt[field] = value
        write(path, receipt)
        item["receipt_sha256"] = digest(path)

    def test_costume_fixture_required_and_bound_to_both_abis(self):
        suite = self.manifest["suites"]["entities"]
        costume = suite["costume_fixture"]
        for mode in ("missing", "tampered", "unexecuted_abi"):
            with self.subTest(mode=mode):
                value = copy.deepcopy(self.manifest)
                target = self.root / costume["path"]
                old = target.read_bytes()
                descriptor = value["suites"]["entities"]["abis"]["arm64-v8a"]
                receipt_path = self.root / descriptor["receipt"]
                old_receipt = receipt_path.read_bytes()
                if mode == "missing":
                    del value["suites"]["entities"]["costume_fixture"]
                elif mode == "tampered":
                    target.write_bytes(b"tampered")
                else:
                    data = json.loads(old_receipt)
                    data["costume_fixtures_sha256"] = "0" * 64
                    write(receipt_path, data)
                    descriptor["receipt_sha256"] = digest(receipt_path)
                with self.assertRaises(ValueError):
                    validate(self.root, value, "x86_64")
                target.write_bytes(old)
                receipt_path.write_bytes(old_receipt)

    def test_complete_manifest_both_abis(self):
        for abi in ABIS:
            self.assertEqual(set(validate(self.root, self.manifest, abi)), set(MODULES))

    def test_missing_or_extra_suite_and_abi(self):
        for path, operation in (((), "suite"), ((MODULES[0],), "abi")):
            for extra in (False, True):
                value = copy.deepcopy(self.manifest)
                target = value["suites"] if operation == "suite" else value["suites"][path[0]]["abis"]
                if extra:
                    target["unexpected"] = {}
                else:
                    del target[next(iter(target))]
                with self.assertRaises(ValueError):
                    self.validate(value)

    def test_manifest_types_and_scope(self):
        for key, value in (("passed", 1), ("source_revision", True), ("source_revision", "b" * 39),
                           ("source_worktree_dirty", 0), ("sanitizers_passed", False), ("android_executed", True),
                           ("suites", []), ("source_sha256", {}), ("schema", "unknown")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.validate({**self.manifest, key: value})

    def test_missing_or_true_acceptance_claims(self):
        for claim in CLAIMS:
            for missing in (False, True):
                value = copy.deepcopy(self.manifest)
                if missing:
                    del value[claim]
                else:
                    value[claim] = True
                with self.assertRaises(ValueError):
                    self.validate(value)

    def test_tampered_binary_receipt_host_and_fixture(self):
        suite = self.manifest["suites"][MODULES[0]]
        for relative in (suite["abis"]["x86_64"]["binary"], suite["abis"]["arm64-v8a"]["binary"],
                         suite["abis"]["x86_64"]["receipt"], suite["host_receipt"], suite["fixture"]["path"]):
            target = self.root / relative
            old = target.read_bytes()
            target.write_bytes(old + b" ")
            with self.assertRaises(ValueError):
                self.validate()
            target.write_bytes(old)

    def test_unexecuted_abi_elf_machine_is_validated_even_when_rehashed(self):
        item = self.manifest["suites"][MODULES[0]]["abis"]["arm64-v8a"]
        binary = self.root / item["binary"]
        header = bytearray(binary.read_bytes())
        struct.pack_into("<H", header, 18, ABIS["x86_64"])
        binary.write_bytes(header)
        item["sha256"] = digest(binary)
        self.change_receipt(MODULES[0], "arm64-v8a", "binary_sha256", item["sha256"])
        with self.assertRaises(ValueError):
            self.validate()

    def test_unexecuted_abi_receipts_bound_to_source_fixture_and_execution(self):
        cases = (("fixtures_sha256", "c" * 64), ("source_sha256", {"wrong.c": "b" * 64}),
                 ("passed", 1), ("abi", "x86_64"), ("executed", True), ("binary", "../escape"),
                 ("android_executed", True), ("emulator_qualified", True), ("physical_android_executed", True),
                 ("actual_server_interoperability_verified", True))
        for field, value in cases:
            original = copy.deepcopy(self.manifest)
            item = self.manifest["suites"][MODULES[0]]["abis"]["arm64-v8a"]
            path = self.root / item["receipt"]
            old = path.read_bytes()
            self.change_receipt(MODULES[0], "arm64-v8a", field, value)
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.validate()
            path.write_bytes(old)
            self.manifest = original

    def test_invalid_sizes_digests_and_source_paths(self):
        for field, value in (("bytes", True), ("bytes", 0), ("bytes", 65), ("bytes", 2**40),
                             ("sha256", "A" * 64), ("receipt_sha256", "not-a-digest")):
            manifest = copy.deepcopy(self.manifest)
            manifest["suites"][MODULES[0]]["abis"]["x86_64"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.validate(manifest)
        for bad in ("../escape", "/absolute", "./alias", "a//b", "a\\b", "", "a/../b"):
            with self.subTest(path=bad), self.assertRaises(ValueError):
                child(self.root, bad)

    def test_escaping_symlink(self):
        (self.root / "escape").symlink_to(Path(__file__).resolve())
        self.manifest["suites"][MODULES[0]]["abis"]["x86_64"]["binary"] = "escape"
        with self.assertRaises(ValueError):
            self.validate()

    def test_expected_result_and_sanitizers_bound_to_host(self):
        self.manifest["suites"][MODULES[0]]["expected"]["checks"] += 1
        with self.assertRaises(ValueError):
            self.validate()
        self.manifest["suites"][MODULES[0]]["expected"]["checks"] -= 1
        suite = self.manifest["suites"][MODULES[0]]
        path = self.root / suite["host_receipt"]
        host = read(path)
        del host["checks"]["ubsan"]
        write(path, host)
        suite["host_receipt_sha256"] = digest(path)
        with self.assertRaises(ValueError):
            self.validate()

    def test_source_inventory_is_not_replaced_by_module_map(self):
        suite = self.manifest["suites"][MODULES[0]]
        del self.manifest["source_sha256"][next(iter(suite["source_sha256"]))]
        with self.assertRaises(ValueError):
            self.validate()

    def test_source_inventory_requires_native_and_exporter_inputs(self):
        for module in MODULES:
            value = copy.deepcopy(self.manifest)
            del value["suites"][module]["source_sha256"]["native-android/engine/" + module + "/coh_" + module + ".c"]
            with self.assertRaises(ValueError):
                self.validate(value)

    def test_source_checkout_bytes_are_verified(self):
        source = self.root / "source.c"
        source.write_text("int example;\n")
        sources = {source.name: digest(source)}
        verify_sources(self.root, sources)
        source.write_text("int changed;\n")
        with self.assertRaises(ValueError):
            verify_sources(self.root, sources)

    def test_strict_json_duplicate_keys_and_nonfinite_numbers(self):
        for text in ('{"passed":false,"passed":true}', '{"checks":NaN}', '{"checks":Infinity}', '{"checks":-Infinity}', '{"float":1e999}'):
            with self.assertRaises(ValueError):
                loads(text)

    def test_inventory_expands_only_pin_sets_used_by_qualified_oracles(self):
        files = {
            "native-android/engine/entities/source-pins.json": {"sha256_lf": {"Common/entity/entity.h": "e" * 64}},
            "native-android/engine/replication/groups-source-pins.json": {"sha256_lf": {"Common/group/group.h": "e" * 64}},
            "native-android/engine/replication/source-pins.json": {"sha256_lf": {"Optional/missing.c": "e" * 64}},
            "native-android/tools/protocol_fixture/source-pins.json": {"sources": {"external": {"path": "external:missing.cpp"}}},
        }
        for relative, value in files.items():
            write(self.root / relative, value)
        for relative in ("upstream/ouroboros/Common/entity/entity.h", "upstream/ouroboros/Common/group/group.h",
                         "upstream/ouroboros/MapServer/src/svr/svr_init.c",
                         "native-android/engine/scenecatalog/source_export.inc",
                         "native-android/engine/coh_contracts.h", ".github/workflows/native-scene-catalog.yml"):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("/* input */\n")
        with patch("qualify.subprocess.check_output", return_value="\0".join([*files, "native-android/engine/scenecatalog/source_export.inc"]) + "\0"):
            result = inventory(self.root)
        self.assertEqual(len(result), 10)
        self.assertIn("upstream/ouroboros/Common/entity/entity.h", result)
        self.assertIn("native-android/engine/scenecatalog/source_export.inc", result)
        self.assertNotIn("external:missing.cpp", result)
        self.assertNotIn("upstream/ouroboros/Optional/missing.c", result)

    def test_native_evidence_types_and_scope(self):
        for result in ({"passed": True, "checks": True}, {"passed": 1, "checks": 3},
                       {"passed": True, "checks": 0}, {"passed": True, "checks": 3, "live_world": True}):
            with self.assertRaises(ValueError):
                native_result(result)
        self.assertFalse(json_equal({"count": 1}, {"count": True}))
        self.assertTrue(json_equal({"count": 1}, {"count": 1}))

    def test_execution_refuses_to_overwrite_prior_command_evidence(self):
        output = self.root / "prior-execution"
        (output / "logs").mkdir(parents=True)
        log = output / "logs/001.log"
        log.write_text("retained previous evidence\n")
        result = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "run_android.py"),
            "--adb", "/missing/adb", "--serial", "test", "--artifacts", str(self.root),
            "--output", str(output / "another-receipt.json")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("output directory must be empty", result.stderr)
        self.assertEqual(log.read_text(), "retained previous evidence\n")


if __name__ == "__main__":
    unittest.main()
