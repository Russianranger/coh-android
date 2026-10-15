"""Exercise byte identity, Android contract bounds and failure-safe publication."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest import mock
import zipfile

import package_game_import as package

sys.path.insert(0, str(package.ROOT / "tools/android/game"))
import test_prepare_game_data as fixtures


class GameImportPackageTests(unittest.TestCase):
    # Reuse the small, immutable source/data/asset fixture, not its test cases.
    write_import = fixtures.ReviewedGameDataTests.write_import

    def setUp(self):
        fixtures.ReviewedGameDataTests.setUp(self)
        self.commit = "a" * 40

    def build(self):
        return package.package(self.output, self.commit, root=self.root)

    def verify(self, **kwargs):
        return package.verify_package(self.output, self.commit, root=self.root, **kwargs)

    def test_complete_contract_and_source_config_priority(self):
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        receipt = self.build()
        self.assertEqual({p.name for p in self.output.iterdir()}, package.PACKAGE_FILES | {package.BUILD_RECEIPT})
        properties = self.verify()
        self.assertEqual(properties["format"], 1)
        self.assertEqual(properties["text.count"], 2)
        self.assertEqual(properties["asset.count"], 1)
        self.assertEqual(properties["total.count"], 3)
        self.assertEqual(properties["text.bytes"], len(self.source_config) + len(self.map_text))
        self.assertEqual(properties["total.bytes"], package.game.DATA_BYTES)
        self.assertEqual(properties["storage.reserve.bytes"], 256 * 1024**2)
        self.assertEqual(properties["storage.per.file.bytes"], 4096)
        with zipfile.ZipFile(self.output / package.TEXT_ARCHIVE) as archive:
            self.assertEqual(archive.namelist(), ["data/maps/atlas.txt", "data/server/db/servers.cfg"])
            self.assertEqual(archive.read("data/server/db/servers.cfg"), self.source_config)
            self.assertEqual(archive.read("data/maps/atlas.txt"), self.map_text)
        text = package.read_index(self.output / package.TEXT_INDEX, "data/")
        assets = package.read_index(self.output / package.ASSET_INDEX, "assets/")
        self.assertEqual(list(assets), ["assets/animations/atlas.anim"])
        self.assertEqual(text["data/maps/atlas.txt"]["bytes"], len(self.map_text))
        self.assertFalse(receipt["reviewed_binary_assets_included"])
        self.assertFalse(receipt["schema_and_generated_caches_included"])
        self.assertFalse(receipt["android_execution_validated"])
        self.assertTrue(all(path.read_bytes() == data for path, data in before.items()))
        self.assertEqual(receipt, json.loads((self.output / package.BUILD_RECEIPT).read_bytes()))

    def test_deterministic_package_and_receipt_with_zip64(self):
        with mock.patch.object(zipfile, "ZIP_FILECOUNT_LIMIT", 1):
            self.build()
            second = self.base / "second"
            package.package(second, self.commit, root=self.root)
        self.assertIn(b"PK\x06\x06", (self.output / package.TEXT_ARCHIVE).read_bytes())
        for path in self.output.iterdir():
            self.assertEqual(path.read_bytes(), (second / path.name).read_bytes())
        self.verify()

    def test_verifier_needs_receipts_but_not_source_payloads_or_build_receipt(self):
        self.build()
        shutil.rmtree(self.root / "upstream")
        (self.output / package.BUILD_RECEIPT).unlink()
        self.verify()

    def test_changed_source_bytes_refused_without_partial_publication(self):
        path = self.root / "upstream/i24/data/maps/atlas.txt"
        path.write_bytes(b"x" * len(self.map_text))
        with self.assertRaisesRegex(ValueError, "input hash differs"):
            self.build()
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.base.glob(".atlas-import-*")))

    def test_missing_unlisted_and_linked_source_inputs_refused(self):
        path = self.root / "upstream/i24/data/maps/atlas.txt"
        original = path.read_bytes()
        path.unlink()
        with self.assertRaisesRegex(ValueError, "Missing immutable text input"):
            self.build()
        path.write_bytes(original)
        extra = path.with_name("unlisted.txt")
        extra.write_text("not reviewed")
        with self.assertRaisesRegex(ValueError, "Unlisted immutable text input"):
            self.build()
        extra.unlink()
        path.unlink()
        path.symlink_to(self.base / "elsewhere")
        with self.assertRaisesRegex(ValueError, "Symlinks are not allowed"):
            self.build()
        self.assertFalse(self.output.exists())

    def test_preserves_existing_destination_and_rejects_input_overlap(self):
        self.output.mkdir()
        keep = self.output / "accepted"
        keep.write_bytes(b"preserve")
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.build()
        self.assertEqual(keep.read_bytes(), b"preserve")
        with self.assertRaisesRegex(ValueError, "outside immutable"):
            package.package(self.root / "upstream/new", self.commit, root=self.root)

    def test_invalid_commit_and_changed_anchor_refused(self):
        with self.assertRaisesRegex(ValueError, "Git commit"):
            package.package(self.output, "main", root=self.root)
        self.manifest.write_bytes(self.manifest.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "manifest hash differs"):
            self.build()
        self.assertFalse(self.output.exists())

    def test_property_mutation_or_wrong_repository_commit_refused(self):
        self.build()
        with self.assertRaisesRegex(ValueError, "repository commit differs"):
            package.verify_package(self.output, "b" * 40, root=self.root)
        path = self.output / package.PROPERTIES
        original = path.read_bytes()
        for mutation in (original + b"unexpected=true\n", original.replace(b"format=1", b"format=2"),
                         original.replace(b"\n", b"\r\n"), original + b"format=1\n"):
            with self.subTest(mutation=mutation[-30:]):
                path.write_bytes(mutation)
                with self.assertRaises(ValueError):
                    self.verify()
        path.write_bytes(original)

    def test_changed_inventory_cannot_self_attest_with_updated_hash_property(self):
        self.build()
        index = self.output / package.TEXT_INDEX
        index.write_bytes(index.read_bytes().replace(hashlib.sha256(self.map_text).hexdigest().encode(), b"0" * 64))
        properties = self.output / package.PROPERTIES
        lines = properties.read_text().splitlines()
        properties.write_text("\n".join("text.index.sha256=" + package.digest(index)
            if line.startswith("text.index.sha256=") else line for line in lines) + "\n")
        with self.assertRaisesRegex(ValueError, "Combined import inventory differs"):
            self.verify()

    def test_changed_text_archive_cannot_self_attest_with_updated_properties(self):
        self.build()
        archive = self.output / package.TEXT_ARCHIVE
        archive.unlink()
        records = {"data/maps/atlas.txt": {"bytes": len(self.map_text), "sha256": "0" * 64,
                                           "path": self.base / "wrong"},
                   "data/server/db/servers.cfg": {"bytes": len(self.source_config),
                       "sha256": hashlib.sha256(self.source_config).hexdigest(),
                       "path": self.root / "upstream/ouroboros/data/server/db/servers.cfg"}}
        records["data/maps/atlas.txt"]["path"].write_bytes(b"x" * len(self.map_text))
        records["data/maps/atlas.txt"]["sha256"] = package.digest(records["data/maps/atlas.txt"]["path"])
        package.write_text_archive(records, archive)
        properties = self.output / package.PROPERTIES
        values = dict(line.split("=", 1) for line in properties.read_text().splitlines())
        values["text.archive.bytes"] = str(archive.stat().st_size)
        values["text.archive.sha256"] = package.digest(archive)
        properties.write_text("".join(key + "=" + value + "\n" for key, value in sorted(values.items())))
        with self.assertRaisesRegex(ValueError, "Packaged text hash differs"):
            self.verify()

    def test_publication_failure_cleans_temporary_package(self):
        with mock.patch.object(package, "verify_text_archive", side_effect=ValueError("roundtrip refused")):
            with self.assertRaisesRegex(ValueError, "roundtrip refused"):
                self.build()
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.base.glob(".atlas-import-*")))

    def test_index_rejects_ambiguous_or_unsafe_paths(self):
        index = self.base / "index.tsv"
        hashed = "a" * 64
        cases = ["data/../escape", "data/a\\b", "data/a\tb", "data/CON.txt", "data/a.", "data//a"]
        for name in cases:
            with self.subTest(name=name):
                index.write_text("1\t" + hashed + "\t" + name + "\n")
                with self.assertRaises(ValueError):
                    package.read_index(index, "data/")
        index.write_text("1\t" + hashed + "\tdata/Maps/a\n1\t" + hashed + "\tdata/maps/b\n")
        with self.assertRaisesRegex(ValueError, "directory casing"):
            package.read_index(index, "data/")
        index.write_text("0\t" + hashed + "\tdata/empty\n")
        self.assertEqual(package.read_index(index, "data/")["data/empty"]["bytes"], 0)

    def test_asset_output_uses_authoritative_directory_casing(self):
        text = {"data/Objects/Mixed/a.txt": {"bytes": 1, "sha256": "a" * 64}}
        assets = [{"path": "objects/mixed/b.geo", "size": 2, "sha256": "b" * 64}]
        actual = package.canonical_inventory(text, assets)
        self.assertEqual(set(actual), {"data/Objects/Mixed/a.txt", "data/Objects/Mixed/b.geo"})
        self.assertEqual(actual["data/Objects/Mixed/b.geo"]["sha256"], "b" * 64)


if __name__ == "__main__":
    unittest.main()
