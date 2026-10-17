"""Admission/cleanup boundaries for transferable standalone ABI evidence."""
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, mock
import copy
import hashlib
import json
import struct
import tempfile
import unittest

import very_rare_tail_android as driver


class Evidence(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo, self.artifacts = self.root / "repo", self.root / "artifacts"
        for name in driver.REQUIRED | driver.DRIVERS:
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("source control\n")
        pins = {}
        for i in range(13):
            name = f"original-{i}.c"
            path = self.repo / "upstream/ouroboros" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"original {i}\n")
            pins[name] = driver.common.digest(path)
        driver.common.write(self.repo / driver.ENGINE / "entities/very-rare-tail-source-pins.json", {"sha256_lf": pins})
        source = {name: driver.common.digest(self.repo / name) for name in driver.REQUIRED}
        fixture = self.artifacts / "android/tail_fixtures.h"
        fixture.parent.mkdir(parents=True)
        fixture.write_text("exact source fixture\n")
        self.expected = dict(passed=True, checks=100, truncations=10, mutations=10, randomized=10,
                             fixtures=10, output_bytes=79184, workspace_bytes=79184, aggregate_limit=4194304,
                             full_update_complete=False, actor_publication=False)
        self.host = dict(schema="coh-very-rare-tail-qualification-v1", passed=True, prepare_only=False,
                         source_worktree_clean=True, source_unchanged_before_after=True, cpp_link_passed=True,
                         source_revision="a" * 40, source_sha256=source,
                         original={"source_sha256_lf": pins, "whole_functions_executed": sorted(driver.FUNCTIONS), "oracle_sanitized": False},
                         fixtures={"sha256": driver.common.digest(fixture)},
                         checks={key: copy.deepcopy(self.expected) for key in ("release", "asan", "ubsan")}, android={},
                         **{key: False for key in driver.FALSE_CLAIMS})
        self.proof = dict(schema=driver.SCHEMA, passed=True, android_executed=False, source_worktree_dirty=False,
                          source_revision="a" * 40, source_sha256={**source, **{name: driver.common.digest(self.repo / name) for name in driver.DRIVERS}},
                          expected=copy.deepcopy(self.expected), abis={}, **{key: False for key in driver.CLAIMS})
        for abi, machine in driver.ABIS.items():
            header = bytearray(64)
            header[:7] = b"\x7fELF\x02\x01\x01"
            struct.pack_into("<HHI", header, 16, 3, machine, 1)
            binary = self.artifacts / "android" / abi / "coh_very_rare_tail_test"
            binary.parent.mkdir(parents=True)
            binary.write_bytes(header)
            receipt_path = binary.parent / "receipt.json"
            receipt = dict(built=True, executed=False, binary=binary.name, binary_sha256=driver.common.digest(binary),
                           fixtures_sha256=self.host["fixtures"]["sha256"], source_sha256=source)
            driver.common.write(receipt_path, receipt)
            self.host["android"][abi] = receipt
            self.proof["abis"][abi] = dict(path=binary.relative_to(self.artifacts).as_posix(), bytes=64,
                sha256=receipt["binary_sha256"], receipt=receipt_path.relative_to(self.artifacts).as_posix(),
                receipt_sha256=driver.common.digest(receipt_path))
        self.save_host()
        patch = mock.patch.object(driver.common, "git_state", return_value={"source_revision": "a" * 40, "source_git_status_porcelain": []})
        patch.start()
        self.addCleanup(patch.stop)

    def save_host(self):
        driver.common.write(self.artifacts / "host.json", self.host)
        self.proof["host_receipt_sha256"] = driver.common.digest(self.artifacts / "host.json")

    def admit(self):
        return driver.validate(self.repo, self.artifacts, self.proof)

    def test_complete_artifact(self):
        self.assertEqual(self.admit(), self.expected)

    def test_wrong_checkout(self):
        self.proof["source_revision"] = "b" * 40
        with self.assertRaises(ValueError): self.admit()

    def test_missing_arm64(self):
        del self.proof["abis"]["arm64-v8a"]
        with self.assertRaises(ValueError): self.admit()

    def test_swapped_abi(self):
        self.proof["abis"]["arm64-v8a"] = copy.deepcopy(self.proof["abis"]["x86_64"])
        with self.assertRaises(ValueError): self.admit()

    def test_binary_mutation(self):
        path = self.artifacts / self.proof["abis"]["arm64-v8a"]["path"]
        path.write_bytes(path.read_bytes() + b"x")
        with self.assertRaises(ValueError): self.admit()

    def test_wrong_fixture(self):
        (self.artifacts / "android/tail_fixtures.h").write_text("other fixture")
        with self.assertRaises(ValueError): self.admit()

    def test_missing_driver_source(self):
        del self.proof["source_sha256"][next(iter(driver.DRIVERS))]
        with self.assertRaises(ValueError): self.admit()

    def test_source_mutation(self):
        (self.repo / next(iter(driver.REQUIRED))).write_text("changed")
        with self.assertRaises(ValueError): self.admit()

    def test_original_source_mutation(self):
        (self.repo / "upstream/ouroboros/original-0.c").write_text("changed")
        with self.assertRaises(ValueError): self.admit()

    def test_original_lf_normalization(self):
        (self.repo / "upstream/ouroboros/original-0.c").write_bytes(b"original 0\r\n")
        self.assertEqual(self.admit(), self.expected)

    def test_missing_original_function(self):
        self.host["original"]["whole_functions_executed"].pop()
        self.save_host()
        with self.assertRaises(ValueError): self.admit()

    def test_missing_sanitizer(self):
        del self.host["checks"]["asan"]
        self.save_host()
        with self.assertRaises(ValueError): self.admit()

    def test_different_sanitizer_result(self):
        self.host["checks"]["ubsan"]["checks"] += 1
        self.save_host()
        with self.assertRaises(ValueError): self.admit()

    def test_boolean_check_count(self):
        self.proof["expected"]["checks"] = True
        with self.assertRaises(ValueError): self.admit()

    def test_outer_transaction_claim(self):
        self.host["full_update_complete"] = True
        self.save_host()
        with self.assertRaises(ValueError): self.admit()

    def test_physical_claim(self):
        self.proof["physical_thor_accepted"] = True
        with self.assertRaises(ValueError): self.admit()

    def test_missing_false_claim(self):
        del self.proof["accepted_apks_rebuilt"]
        with self.assertRaises(ValueError): self.admit()

    def test_path_escape(self):
        self.proof["abis"]["x86_64"]["path"] = "../outside"
        with self.assertRaises(ValueError): self.admit()

    def test_abi_receipt_claim(self):
        receipt = self.host["android"]["x86_64"]
        receipt["executed"] = True
        path = self.artifacts / self.proof["abis"]["x86_64"]["receipt"]
        driver.common.write(path, receipt)
        self.proof["abis"]["x86_64"]["receipt_sha256"] = driver.common.digest(path)
        self.save_host()
        with self.assertRaises(ValueError): self.admit()

    def test_duplicate_json_key(self):
        path = self.artifacts / "host.json"
        path.write_text('{"passed":true,"passed":false}')
        self.proof["host_receipt_sha256"] = driver.common.digest(path)
        with self.assertRaises(ValueError): self.admit()

    def test_nonfinite_json(self):
        with self.assertRaises(ValueError): driver.common.loads('{"value":NaN}')

    def test_android_mismatch_still_cleans_owned_directory(self):
        driver.common.write(self.artifacts / "build.json", self.proof)
        calls = []
        def execute(command, log, **unused):
            command = list(map(str, command)); calls.append(command)
            tail = command[3:]
            if tail[:2] == ["shell", "getprop"]:
                return {"ro.kernel.qemu": "1", "ro.build.version.sdk": "33", "ro.product.cpu.abilist": "x86_64", "ro.build.fingerprint": "test fingerprint"}[tail[2]]
            if tail[:2] == ["shell", "mktemp"]: return "/data/local/tmp/coh-entity-tail.owned123"
            if tail[:2] == ["shell", "sha256sum"]: return self.proof["abis"]["x86_64"]["sha256"] + "  tail-test"
            if tail[:2] == ["shell", "timeout"]: return json.dumps({**self.expected, "checks": 99})
            return ""
        args = SimpleNamespace(source_root=self.repo, artifacts=self.artifacts, output=self.root / "execution", adb=Path("/tmp/adb"), serial="emulator-5554")
        with mock.patch.object(driver.common, "execute", side_effect=execute):
            self.assertEqual(driver.run_android(args), 1)
        result = driver.common.read(args.output / "receipt.json")
        self.assertFalse(result["passed"])
        self.assertTrue(result["android_executed"])
        self.assertFalse(result["emulator_qualified"])
        self.assertTrue(result["temporary_files_removed"])
        self.assertTrue(any(command[3:6] == ["shell", "rm", "-rf"] for command in calls))


if __name__ == "__main__":
    unittest.main()
