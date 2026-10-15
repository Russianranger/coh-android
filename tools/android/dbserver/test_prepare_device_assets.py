"""Device bundle provenance, byte preservation, safe archives and atomic failure."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest
from unittest import mock

import prepare_device_assets as prepare


def write_manifest(directory, name, manifest):
    path = directory / name
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    return prepare.digest(path)


def inventory(directory):
    return {path.relative_to(directory).as_posix(): {"bytes": path.stat().st_size,
                                                    "sha256": prepare.digest(path)}
            for path in sorted(directory.rglob("*")) if path.is_file()}


class DeviceAssetsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Tiny payload files exercise the full real manifest/inventory validators.
        # Only their qualification hashes differ from production; no validators are mocked.
        cls.temporary = tempfile.TemporaryDirectory()
        cls.fixture = Path(cls.temporary.name)
        cls.assets, cls.package, cls.schema = (cls.fixture / name for name in ("runtime", "package", "schema"))
        for directory in (cls.assets, cls.package, cls.schema):
            directory.mkdir()
        original = json.loads((prepare.ROOT / "docs/android-evidence/runtime-manifest-36364550345.json").read_text())
        for name in original["files"]:
            (cls.assets / name).write_bytes(("base payload " + name).encode())
        original["files"] = inventory(cls.assets)
        cls.runtime_hash = write_manifest(cls.assets, "runtime-manifest.json", original)
        loopback, listeners = prepare.host.source_loopback_contracts()
        package = {"format": 1, "repository_commit": prepare.PACKAGE_COMMIT,
                   "source_commit": prepare.host.SOURCE_COMMIT,
                   "android_execution_validated": False, "gameplay_validated": False,
                   "wine_build_input": {"fixed_inputs": prepare.host.FIXED_INPUTS_METADATA,
                                        "loopback_only": loopback, "normal_schema_listeners": listeners},
                   "variants": {}}
        for name, enabled in (("fixture", True), ("normal", False)):
            directory = cls.package / name
            directory.mkdir()
            (directory / "DbServer.exe").write_bytes(("test binary " + name).encode())
            package["variants"][name] = {"postgresql_persistence_fixture": enabled, "files": inventory(directory)}
        cls.package_hash = write_manifest(cls.package, "package-manifest.json", package)
        for number in range(62):
            (cls.schema / f"schema-{number:02d}.txt").write_text("schema input\n")
        schema = {"format": 1, "scope": "accepted_generated_schema_inputs",
                  "acceptance_run_id": 36088012666, "source_commit": prepare.host.SOURCE_COMMIT,
                  "data_commit": prepare.host.DATA_COMMIT,
                  "android_execution_validated": False, "gameplay_validated": False,
                  "generated_file_count": 56, "supplemental_file_count": 6, "files": inventory(cls.schema),
                  "expected_tables": {f"table_{number}": [f"column_{index}" for index in range(60 if number < 98 else 55)]
                                      for number in range(99)},
                  "expected_attributes": {"attributes": [{"id": index, "name": str(index)} for index in range(58272)]}}
        cls.schema_hash = write_manifest(cls.schema, "schema-manifest.json", schema)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name)
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(mock.patch.object(prepare.host, "ACCEPTED_RUNTIME_MANIFEST", self.runtime_hash))
        self.stack.enter_context(mock.patch.object(prepare, "PACKAGE_MANIFEST_SHA256", self.package_hash))
        self.stack.enter_context(mock.patch.object(prepare, "SCHEMA_MANIFEST_SHA256", self.schema_hash))
        self.stack.enter_context(mock.patch.object(prepare, "accepted_evidence"))

    def assemble(self, name="candidate", **kwargs):
        inputs = {"assets": self.assets, "package": self.package, "schema": self.schema,
                  "output": self.root / name, "repository_commit": "a" * 40}
        inputs.update(kwargs)
        return prepare.prepare_device_assets(**inputs)

    def test_reproducible_preserved_base_and_archives_roundtrip(self):
        first = self.assemble("first", receipt=self.root / "first-receipt.json")
        second = self.assemble("second")
        self.assertEqual(first, second)
        self.assertEqual(inventory(self.root / "first"), inventory(self.root / "second"))
        result = prepare.extract_device_inputs(self.root / "first", self.root / "extracted")
        self.assertEqual(inventory(result["package"]), inventory(self.package))
        self.assertEqual(inventory(result["schema"]), inventory(self.schema))
        self.assertEqual((self.root / "first" / prepare.BASE_MANIFEST).read_bytes(),
                         (self.assets / "runtime-manifest.json").read_bytes())
        manifest = prepare.verify_device_assets(self.root / "first")
        self.assertEqual(manifest["accepted_base_runtime"]["manifest"]["repository_commit"],
                         prepare.host.ACCEPTED_RUNTIME_COMMIT)
        self.assertEqual(manifest["repository_commit"], "a" * 40)
        self.assertEqual(json.loads((self.root / "first-receipt.json").read_text()), first)
        self.assertFalse(first["android_execution_validated"])

    def test_wrong_donor_hash_does_not_publish_output(self):
        package = self.root / "wrong-package"
        shutil.copytree(self.package, package)
        with (package / "package-manifest.json").open("a") as stream:
            stream.write(" ")
        with self.assertRaisesRegex(RuntimeError, "qualified loopback package"):
            self.assemble(package=package)
        self.assertFalse((self.root / "candidate").exists())

    def test_corrupted_base_file_does_not_publish_output(self):
        assets = self.root / "bad-runtime"
        shutil.copytree(self.assets, assets)
        (assets / "diagnostic.py").write_text("corruption")
        with self.assertRaisesRegex(RuntimeError, "Input hash/size mismatch"):
            self.assemble(assets=assets)
        self.assertFalse((self.root / "candidate").exists())

    def test_extra_uninventoried_file_is_rejected(self):
        package = self.root / "bad-package"
        shutil.copytree(self.package, package)
        (package / "normal/untracked.dll").write_bytes(b"extra")
        with self.assertRaisesRegex(RuntimeError, "differs from its inventory"):
            self.assemble(package=package)
        self.assertFalse((self.root / "candidate").exists())

    def test_symlink_in_inventoried_tree_is_rejected(self):
        schema = self.root / "bad-schema"
        shutil.copytree(self.schema, schema)
        path = schema / "schema-00.txt"
        path.unlink()
        path.symlink_to(self.schema / path.name)
        with self.assertRaisesRegex(RuntimeError, "symlink"):
            self.assemble(schema=schema)

    def test_nested_output_and_existing_output_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "overlap"):
            self.assemble(output=self.assets / "nested")
        self.assemble()
        existing = inventory(self.root / "candidate")
        with self.assertRaisesRegex(RuntimeError, "fresh output"):
            self.assemble()
        self.assertEqual(inventory(self.root / "candidate"), existing)

    def test_failed_receipt_publication_rolls_back_candidate(self):
        blocked_parent = self.root / "regular-file"
        blocked_parent.write_text("not a directory")
        with self.assertRaises(FileExistsError):
            self.assemble(receipt=blocked_parent / "receipt.json")
        self.assertFalse((self.root / "candidate").exists())
        self.assertEqual(blocked_parent.read_text(), "not a directory")

    def test_preserved_base_metadata_cannot_be_rewritten(self):
        self.assemble()
        path = self.root / "candidate/runtime-manifest.json"
        manifest = json.loads(path.read_text())
        manifest["accepted_base_runtime"]["manifest"]["repository_commit"] = "b" * 40
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(RuntimeError, "base runtime metadata differs"):
            prepare.verify_device_assets(path.parent)

    def test_runtime_inventory_record_cannot_be_rewritten_even_with_matching_bytes(self):
        self.assemble()
        path = self.root / "candidate/runtime-manifest.json"
        manifest = json.loads(path.read_text())
        data = b"replacement base"
        (path.parent / "diagnostic.py").write_bytes(data)
        manifest["files"]["diagnostic.py"] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(RuntimeError, "runtime inventory was modified"):
            prepare.verify_device_assets(path.parent)

    def test_rehashed_archive_still_requires_the_qualified_package_inventory(self):
        self.assemble()
        package = self.root / "tampered-package"
        shutil.copytree(self.package, package)
        (package / "normal/DbServer.exe").write_bytes(b"replacement executable")
        root = self.root / "candidate"
        archive = root / "dbserver-package.tar.gz"
        archive.unlink()
        prepare.write_archive(package, archive)
        manifest = json.loads((root / "runtime-manifest.json").read_text())
        manifest["files"][archive.name] = {"bytes": archive.stat().st_size, "sha256": prepare.digest(archive)}
        write_manifest(root, "runtime-manifest.json", manifest)
        with self.assertRaisesRegex(RuntimeError, "Input hash/size mismatch"):
            prepare.verify_device_assets(root)

    def test_tampered_archive_cannot_be_extracted(self):
        self.assemble()
        path = self.root / "candidate/dbserver-package.tar.gz"
        path.write_bytes(b"not the accepted archive")
        with self.assertRaisesRegex(RuntimeError, "Input hash/size mismatch"):
            prepare.extract_device_inputs(path.parent, self.root / "extracted")
        self.assertFalse((self.root / "extracted").exists())


class ArchiveTests(unittest.TestCase):
    def test_tar_output_ignores_input_mtime_and_permission_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            path = source / "payload.txt"
            path.write_bytes(b"immutable bytes")
            prepare.write_archive(source, root / "one.tar.gz")
            path.chmod(0o755)
            import os
            os.utime(path, (42, 42))
            prepare.write_archive(source, root / "two.tar.gz")
            self.assertEqual((root / "one.tar.gz").read_bytes(), (root / "two.tar.gz").read_bytes())

    def test_unsafe_and_ambiguous_members_are_refused(self):
        cases = [("../escape", tarfile.REGTYPE, 0o644, False),
                 ("/absolute", tarfile.REGTYPE, 0o644, False),
                 ("back\\slash", tarfile.REGTYPE, 0o644, False),
                 ("link", tarfile.SYMTYPE, 0o644, False),
                 ("hardlink", tarfile.LNKTYPE, 0o644, False),
                 ("device", tarfile.CHRTYPE, 0o644, False),
                 ("executable", tarfile.REGTYPE, 0o777, False),
                 ("duplicate", tarfile.REGTYPE, 0o644, True)]
        for name, kind, mode, duplicate in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                archive = root / "bad.tar.gz"
                with tarfile.open(archive, "w:gz") as output:
                    item = tarfile.TarInfo(name)
                    item.type, item.mode, item.size = kind, mode, 0
                    output.addfile(item, io.BytesIO())
                    if duplicate:
                        output.addfile(item, io.BytesIO())
                with self.assertRaises(RuntimeError):
                    prepare.extract_archive(archive, root / "output")
                self.assertFalse((root / "escape").exists())


if __name__ == "__main__":
    unittest.main()
