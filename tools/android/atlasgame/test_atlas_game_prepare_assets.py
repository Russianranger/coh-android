"""Pinned Atlas packaging, unchanged runtime identity and bounded extraction."""
import contextlib
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

_spec = importlib.util.spec_from_file_location("atlas_device_assets_under_test", Path(__file__).with_name("prepare_device_assets.py"))
prepare = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prepare)


def inventory(directory):
    return {path.relative_to(directory).as_posix(): {"bytes": path.stat().st_size, "sha256": prepare.digest(path)}
            for path in sorted(directory.rglob("*")) if path.is_file()}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")
    return prepare.digest(path)


class AcceptedEvidenceTests(unittest.TestCase):
    def test_production_pins_match_preserved_hosted_acceptance(self):
        inputs = prepare.accepted_evidence()
        self.assertEqual(inputs["game_package_sha256"], prepare.PACKAGE_MANIFEST_SHA256)
        self.assertEqual(prepare.bundle_contract()["package_repository_commit"], prepare.PACKAGE_COMMIT)
        self.assertFalse(prepare.bundle_contract()["android_execution_validated"])


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.assets, self.package, self.schema, self.probe = [self.root / name for name in ("base", "package", "schema", "probe")]
        for path in (self.assets, self.package, self.schema, self.probe):
            path.mkdir()
        for number in range(12):
            (self.assets / f"base-{number:02d}").write_bytes(f"accepted base {number}".encode())
        base = {"format": 1, "repository_commit": prepare.host.ACCEPTED_RUNTIME_COMMIT,
                "scope": "accepted", "files": inventory(self.assets)}
        self.patch(prepare.host, "ACCEPTED_RUNTIME_MANIFEST", write_json(self.assets / "runtime-manifest.json", base))
        for directory, name in ((self.package, "game-package.json"), (self.schema, "schema-manifest.json")):
            (directory / "fixture.txt").write_text("payload")
            value = {"format": 1, "repository_commit": prepare.PACKAGE_COMMIT, "files": inventory(directory)}
            pin = write_json(directory / name, value)
            self.patch(prepare, "PACKAGE_MANIFEST_SHA256" if directory == self.package else "SCHEMA_MANIFEST_SHA256", pin)
        (self.probe / "GameStackProbe.exe").write_bytes(b"observer fixture")
        self.patch(prepare, "OBSERVER_MANIFEST_SHA256", write_json(self.probe / "stack-probe-build.json", {"format": 1}))
        self.data_manifest = self.root / "game-data-manifest.json"
        data = {"format": 1, "scope": "reviewed_game_data", "source_commit": prepare.host.SOURCE_COMMIT,
                "data_commit": prepare.host.DATA_COMMIT, "files": {"data/test.txt": {"bytes": 1, "sha256": "a" * 64}},
                "file_count": 1, "total_bytes": 1, "asset_manifest_sha256": prepare.game.ASSET_MANIFEST_SHA256,
                "asset_archive_sha256": prepare.game.ASSET_ARCHIVE_SHA256,
                "android_execution_validated": False, "gameplay_validated": False}
        self.patch(prepare, "DATA_MANIFEST_SHA256", write_json(self.data_manifest, data))
        self.patch(prepare, "DATA_MANIFEST_BYTES", self.data_manifest.stat().st_size)
        self.patch(prepare.game, "DATA_FILE_COUNT", 1)
        self.patch(prepare.game, "DATA_TOTAL_BYTES", 1)
        self.patch(prepare, "accepted_evidence", lambda: {})
        # Real ZIP/tar/hash/metadata validators run on tiny inventory fixtures.
        # PE dependency interpretation is covered by the donor suite and CI's
        # actual accepted binaries; replace only that external parser boundary.
        def verify_fixture(directory, filename):
            value = json.loads((directory / filename).read_text())
            prepare.host.verify_inventory(directory, value["files"], excluded=(filename,))
            return value
        self.patch(prepare.game, "verify_package", lambda path, **kwargs: verify_fixture(path, "game-package.json"))
        self.patch(prepare.host, "verify_schema", lambda path: verify_fixture(path, "schema-manifest.json"))
        self.patch(prepare.stack_probe_receipt, "verify", lambda *args: {})
        guest_root = self.root / "source/android/guest"
        guest_root.mkdir(parents=True)
        for name in prepare.GUEST_SCRIPTS:
            (guest_root / name).write_text("# current source: " + name)
        self.patch(prepare, "ROOT", self.root / "source")

    def patch(self, obj, name, value):
        self.stack.enter_context(mock.patch.object(obj, name, value))

    def assemble(self, name="candidate", **kwargs):
        values = {"assets": self.assets, "package": self.package, "schema": self.schema,
                  "game_data_manifest": self.data_manifest, "stack_probe": self.probe,
                  "output": self.root / name, "repository_commit": "a" * 40}
        values.update(kwargs)
        return prepare.prepare_device_assets(**values)

    def rewrite_inventory(self, name):
        root = self.root / "candidate"
        path = root / "runtime-manifest.json"
        value = json.loads(path.read_text())
        value["files"][name] = {"bytes": (root / name).stat().st_size, "sha256": prepare.digest(root / name)}
        write_json(path, value)

    def test_reproducible_roundtrip_retains_old_donor_and_new_wrapper_commits(self):
        first = self.assemble("first", receipt=self.root / "receipt.json")
        self.assertEqual(first, self.assemble("second"))
        self.assertEqual(inventory(self.root / "first"), inventory(self.root / "second"))
        paths = prepare.extract_device_inputs(self.root / "first", self.root / "unpacked")
        self.assertEqual(inventory(paths["package"]), inventory(self.package))
        self.assertEqual(inventory(paths["schema"]), inventory(self.schema))
        self.assertEqual(paths["data_manifest"].read_bytes(), self.data_manifest.read_bytes())
        self.assertEqual(first["repository_commit"], "a" * 40)
        self.assertEqual(first["atlas_device_bundle"]["package_repository_commit"], prepare.PACKAGE_COMMIT)
        self.assertEqual((self.root / "first/accepted-runtime-manifest.json").read_bytes(),
                         (self.assets / "runtime-manifest.json").read_bytes())

    def test_modified_accepted_manifest_is_rejected_before_publication(self):
        with (self.package / "game-package.json").open("a") as stream:
            stream.write(" ")
        with self.assertRaisesRegex(RuntimeError, "exact qualified Atlas"):
            self.assemble()
        self.assertFalse((self.root / "candidate").exists())

    def test_modified_base_payload_is_rejected(self):
        (self.assets / "base-00").write_text("changed")
        with self.assertRaisesRegex(RuntimeError, "hash/size"):
            self.assemble()
        self.assertFalse((self.root / "candidate").exists())

    def test_rehashed_candidate_cannot_replace_base_inventory(self):
        self.assemble()
        (self.root / "candidate/base-00").write_text("changed")
        self.rewrite_inventory("base-00")
        with self.assertRaisesRegex(RuntimeError, "runtime inventory was modified"):
            prepare.verify_device_metadata(self.root / "candidate")

    def test_rehashed_guest_must_still_match_checkout(self):
        self.assemble()
        name = prepare.GUEST_SCRIPTS[0]
        (self.root / "candidate" / name).write_text("changed guest")
        self.rewrite_inventory(name)
        with self.assertRaisesRegex(RuntimeError, "guest script differs"):
            prepare.verify_device_metadata(self.root / "candidate")

    def test_rehashed_tar_cannot_replace_accepted_binary_payload(self):
        self.assemble()
        (self.package / "fixture.txt").write_text("changed executable")
        archive = self.root / "candidate/game-package.tar.gz"
        archive.unlink()
        prepare.write_archive(self.package, archive)
        self.rewrite_inventory(archive.name)
        with self.assertRaisesRegex(RuntimeError, "hash/size"):
            prepare.extract_device_inputs(self.root / "candidate", self.root / "unpacked")
        self.assertFalse((self.root / "unpacked").exists())

    def test_output_cannot_overlap_an_input_or_replace_existing_output(self):
        with self.assertRaisesRegex(RuntimeError, "overlap"):
            self.assemble(output=self.assets / "nested")
        self.assemble()
        previous = inventory(self.root / "candidate")
        with self.assertRaisesRegex(RuntimeError, "fresh output"):
            self.assemble()
        self.assertEqual(previous, inventory(self.root / "candidate"))

    def test_failed_receipt_does_not_publish_candidate(self):
        blocker = self.root / "blocker"
        blocker.write_text("existing")
        with self.assertRaises(FileExistsError):
            self.assemble(receipt=blocker / "receipt.json")
        self.assertFalse((self.root / "candidate").exists())

    def test_gzip_output_deterministic_and_roundtrip_exact(self):
        for name in ("one", "two"):
            prepare.write_data_manifest(self.data_manifest, self.root / name)
        self.assertEqual((self.root / "one").read_bytes(), (self.root / "two").read_bytes())
        prepare.extract_data_manifest(self.root / "one", self.root / "decoded")
        self.assertEqual((self.root / "decoded").read_bytes(), self.data_manifest.read_bytes())

    def test_gzip_bomb_is_bounded_and_partial_output_removed(self):
        archive = self.root / "bomb.gz"
        with gzip.open(archive, "wb") as stream:
            stream.write(b"X" * (prepare.DATA_MANIFEST_BYTES + 1))
        with self.assertRaisesRegex(RuntimeError, "exceeds bound"):
            prepare.extract_data_manifest(archive, self.root / "decoded")
        self.assertFalse((self.root / "decoded").exists())

    def test_existing_decompression_destination_is_preserved(self):
        archive = self.root / "manifest.gz"
        prepare.write_data_manifest(self.data_manifest, archive)
        destination = self.root / "existing"
        destination.write_bytes(b"previous accepted input")
        with self.assertRaises(FileExistsError):
            prepare.extract_data_manifest(archive, destination)
        self.assertEqual(destination.read_bytes(), b"previous accepted input")

    def test_gzip_truncation_and_wrong_content_are_rejected(self):
        archive = self.root / "manifest.gz"
        prepare.write_data_manifest(self.data_manifest, archive)
        archive.write_bytes(archive.read_bytes()[:-4])
        with self.assertRaises(EOFError):
            prepare.extract_data_manifest(archive, self.root / "decoded")
        self.assertFalse((self.root / "decoded").exists())
        with gzip.open(archive, "wb") as stream:
            stream.write(b"X" * prepare.DATA_MANIFEST_BYTES)
        with self.assertRaisesRegex(RuntimeError, "manifest differs"):
            prepare.extract_data_manifest(archive, self.root / "decoded")
        self.assertFalse((self.root / "decoded").exists())


if __name__ == "__main__":
    unittest.main()
