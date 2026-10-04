"""Pinned Atlas packaging, unchanged runtime identity and bounded extraction."""
import contextlib
import copy
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

    def test_progress_production_pins_match_separate_preserved_qualification(self):
        profile = prepare.MAPSERVER_PROGRESS_PROFILE
        inputs = prepare.accepted_evidence(profile)
        contract = prepare.bundle_contract(profile)
        self.assertEqual(inputs["game_package_sha256"], contract["package_manifest_sha256"])
        self.assertEqual(inputs["repository_commit"], contract["package_repository_commit"])
        self.assertEqual(inputs["mapserver_progress_producer"], contract["mapserver_progress_producer"])
        self.assertEqual(inputs["accepted_supporting_donors"]["manifest_sha256"], prepare.PACKAGE_MANIFEST_SHA256)

    def test_progress_profile_has_separate_pins_and_keeps_six_checkout_guests(self):
        original = prepare.bundle_contract()
        progress = prepare.bundle_contract(prepare.MAPSERVER_PROGRESS_PROFILE)
        changed = {"package_run_id", "package_repository_commit", "package_manifest_sha256",
                   "mapserver_progress_profile", "mapserver_progress_producer"}
        self.assertEqual({key: value for key, value in original.items() if key not in changed},
                         {key: value for key, value in progress.items() if key not in changed})
        self.assertEqual(original["package_run_id"], 36510836956)
        self.assertEqual(progress["package_run_id"], 36630872719)
        self.assertEqual(progress["package_repository_commit"], prepare.MAPSERVER_PROGRESS_COMMIT)
        self.assertEqual(progress["mapserver_progress_producer"], {
            "repository_commit": prepare.MAPSERVER_PROGRESS_COMMIT,
            "manifest_sha256": prepare.MAPSERVER_PROGRESS_MANIFEST_SHA256,
            "mapserver_sha256": prepare.MAPSERVER_PROGRESS_BINARY_SHA256})
        self.assertEqual(len(original["guest_scripts"]), 6)
        self.assertIn("game_map_progress.py", original["guest_scripts"])
        self.assertNotIn("mapserver_progress_profile", original)
        for profile in ("accepted", "unknown", "dispatch_progress_v2", ""):
            with self.subTest(profile=profile), self.assertRaisesRegex(RuntimeError, "Unknown MapServer progress"):
                prepare.accepted_evidence(profile)


class ProgressEvidenceTests(unittest.TestCase):
    """Exercise qualification record checks without inventing production acceptance."""
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.evidence = self.root / "docs/android-evidence"
        self.evidence.mkdir(parents=True)
        for name in (f"accepted-game-listeners-hosted-{prepare.PACKAGE_RUN_ID}.json",
                     f"game-listeners-host-inputs-{prepare.PACKAGE_RUN_ID}.json",
                     f"game-listeners-package-{prepare.PACKAGE_RUN_ID}.json"):
            shutil.copyfile(prepare.ROOT / "docs/android-evidence" / name, self.evidence / name)
        self.contract = prepare.bundle_contract(prepare.MAPSERVER_PROGRESS_PROFILE)
        self.package = self.evidence / f"mapserver-progress-package-{prepare.MAPSERVER_PROGRESS_RUN_ID}.json"
        self.inputs = self.evidence / f"mapserver-progress-host-inputs-{prepare.MAPSERVER_PROGRESS_RUN_ID}.json"
        self.accepted = self.evidence / f"accepted-mapserver-progress-hosted-{prepare.MAPSERVER_PROGRESS_RUN_ID}.json"
        manifest = {"format": 1, "repository_commit": prepare.MAPSERVER_PROGRESS_COMMIT,
                    "mapserver_progress_profile": prepare.MAPSERVER_PROGRESS_PROFILE,
                    "files": {"MapServer.exe": {"sha256": prepare.MAPSERVER_PROGRESS_BINARY_SHA256}},
                    "inputs": {"mapserver_progress": {
                        "repository_commit": prepare.MAPSERVER_PROGRESS_COMMIT,
                        "manifest_sha256": prepare.MAPSERVER_PROGRESS_MANIFEST_SHA256}}}
        package_sha = write_json(self.package, manifest)
        self.input_value = {
            "format": 1,
            "runtime_manifest_sha256": prepare.host.ACCEPTED_RUNTIME_MANIFEST,
            "game_package_sha256": package_sha, "schema_manifest_sha256": prepare.SCHEMA_MANIFEST_SHA256,
            "game_data_manifest_sha256": prepare.DATA_MANIFEST_SHA256,
            "repository_commit": prepare.MAPSERVER_PROGRESS_COMMIT,
            "runtime_commit": prepare.host.ACCEPTED_RUNTIME_COMMIT,
            "mapserver_progress_profile": prepare.MAPSERVER_PROGRESS_PROFILE,
            "mapserver_progress_producer": self.contract["mapserver_progress_producer"],
            "binary_sha256": {"MapServer.exe": prepare.MAPSERVER_PROGRESS_BINARY_SHA256},
            "accepted_supporting_donors": {"run_id": prepare.PACKAGE_RUN_ID,
                "repository_commit": prepare.PACKAGE_COMMIT, "manifest_sha256": prepare.PACKAGE_MANIFEST_SHA256}}
        self.record = {"format": 1, "status": "accepted_hosted_mapserver_progress", "workflow_conclusion": "success",
                       "run_id": prepare.MAPSERVER_PROGRESS_RUN_ID, "repository_commit": prepare.MAPSERVER_PROGRESS_COMMIT,
                       "android_execution_validated": False, "gameplay_validated": False,
                       "native_contracts": {"passed": 6, "skipped": 0},
                       "arm64": {"stages_passed": 18, "cleanup_complete": True},
                       "independent_validation": {"status": "passed"},
                       "mapserver_progress_profile": prepare.MAPSERVER_PROGRESS_PROFILE,
                       "mapserver_progress_producer": copy.deepcopy(self.contract["mapserver_progress_producer"])}
        self.write_evidence()
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(mock.patch.object(prepare, "ROOT", self.root))
        stack.enter_context(mock.patch.object(prepare, "MAPSERVER_PROGRESS_PACKAGE_SHA256", package_sha))

    def write_evidence(self):
        write_json(self.inputs, self.input_value)
        self.record["inputs"] = copy.deepcopy(self.input_value)
        self.record["preserved_files"] = {path.name: {"bytes": path.stat().st_size, "sha256": prepare.digest(path)}
                                           for path in (self.inputs, self.package)}
        write_json(self.accepted, self.record)

    def verify(self):
        return prepare.accepted_evidence(prepare.MAPSERVER_PROGRESS_PROFILE)

    def test_new_qualification_requires_complete_pinned_inputs_and_original_support_acceptance(self):
        self.assertEqual(self.verify(), self.input_value)
        path = self.evidence / f"accepted-game-listeners-hosted-{prepare.PACKAGE_RUN_ID}.json"
        old = json.loads(path.read_text())
        old["status"] = "failed"
        write_json(path, old)
        with self.assertRaisesRegex(RuntimeError, "qualification differs"):
            self.verify()

    def test_failed_unreviewed_or_mismatched_run_does_not_qualify(self):
        original = copy.deepcopy(self.record)
        for key, value in (("status", "diagnostic_build_packaged_runtime_unverified"),
                           ("workflow_conclusion", "failure"), ("run_id", prepare.PACKAGE_RUN_ID),
                           ("repository_commit", "a" * 40), ("android_execution_validated", True)):
            with self.subTest(key=key):
                write_json(self.accepted, dict(original, **{key: value}))
                with self.assertRaisesRegex(RuntimeError, "qualification differs"):
                    self.verify()

    def test_rehashed_input_cannot_substitute_producer_or_supporting_donors(self):
        original = copy.deepcopy(self.input_value)
        for mutate in (lambda value: value["mapserver_progress_producer"].update(repository_commit="a" * 40),
                       lambda value: value["mapserver_progress_producer"].update(manifest_sha256="0" * 64),
                       lambda value: value["binary_sha256"].update({"MapServer.exe": "0" * 64}),
                       lambda value: value["accepted_supporting_donors"].update(run_id=prepare.MAPSERVER_PROGRESS_RUN_ID)):
            self.input_value = copy.deepcopy(original)
            mutate(self.input_value)
            self.write_evidence()
            with self.assertRaisesRegex(RuntimeError, "producer or supporting donor pins"):
                self.verify()

    def test_all_native_arm64_and_independent_review_gates_are_mandatory(self):
        original = copy.deepcopy(self.record)
        for mutate in (lambda value: value["native_contracts"].update(passed=5),
                       lambda value: value["native_contracts"].update(skipped=1),
                       lambda value: value["arm64"].update(stages_passed=9),
                       lambda value: value["arm64"].update(cleanup_complete=1),
                       lambda value: value["independent_validation"].update(status="pending"),
                       lambda value: value["mapserver_progress_producer"].update(mapserver_sha256="0" * 64),
                       lambda value: value.update(mapserver_progress_profile=None)):
            changed = copy.deepcopy(original)
            mutate(changed)
            write_json(self.accepted, changed)
            with self.assertRaisesRegex(RuntimeError, "review gates differ"):
                self.verify()

    def test_preserved_bytes_and_exact_input_record_cannot_drift(self):
        self.inputs.write_text(self.inputs.read_text() + " ")
        with self.assertRaisesRegex(RuntimeError, "Preserved Atlas evidence differs"):
            self.verify()
        self.write_evidence()
        changed = copy.deepcopy(self.record)
        changed["inputs"].pop("binary_sha256")
        write_json(self.accepted, changed)
        with self.assertRaisesRegex(RuntimeError, "Qualified MapServer inputs differ"):
            self.verify()


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
        self.patch(prepare, "accepted_evidence", lambda profile=None: {})
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

    def use_progress_package(self):
        executable = self.package / "MapServer.exe"
        executable.write_bytes(b"local unit-test progress executable")
        producer = {"repository_commit": prepare.MAPSERVER_PROGRESS_COMMIT,
                    "manifest_sha256": prepare.MAPSERVER_PROGRESS_MANIFEST_SHA256}
        value = {"format": 1, "repository_commit": prepare.MAPSERVER_PROGRESS_COMMIT,
                 "mapserver_progress_profile": prepare.MAPSERVER_PROGRESS_PROFILE,
                 "inputs": {"mapserver_progress": producer},
                 "files": {name: info for name, info in inventory(self.package).items() if name != "game-package.json"}}
        self.patch(prepare, "MAPSERVER_PROGRESS_BINARY_SHA256", prepare.digest(executable))
        self.patch(prepare, "MAPSERVER_PROGRESS_PACKAGE_SHA256", write_json(self.package / "game-package.json", value))

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

    def test_explicit_progress_roundtrip_keeps_distinct_wrapper_donor_and_old_observer(self):
        self.use_progress_package()
        profile = prepare.MAPSERVER_PROGRESS_PROFILE
        with mock.patch.object(prepare.stack_probe_receipt, "verify", return_value={}) as observer:
            result = self.assemble(mapserver_progress_profile=profile)
            self.assertTrue(observer.call_args_list)
            self.assertTrue(all(call.args[1] == prepare.PACKAGE_COMMIT for call in observer.call_args_list))
        self.assertEqual(result["repository_commit"], "a" * 40)
        self.assertEqual(result["atlas_device_bundle"], prepare.bundle_contract(profile))
        self.assertNotEqual(result["repository_commit"], result["atlas_device_bundle"]["package_repository_commit"])
        paths = prepare.extract_device_inputs(self.root / "candidate", self.root / "unpacked",
                                               mapserver_progress_profile=profile)
        self.assertEqual(inventory(paths["package"]), inventory(self.package))
        manifest = prepare.verify_device_assets(self.root / "candidate", mapserver_progress_profile=profile)
        self.assertIn("game_map_progress.py", manifest["files"])
        self.assertEqual(len(manifest["atlas_device_bundle"]["guest_scripts"]), 6)
        with self.assertRaisesRegex(RuntimeError, "bundle contract differs"):
            prepare.verify_device_metadata(self.root / "candidate")

    def test_progress_package_requires_explicit_selection_and_cannot_use_old_package(self):
        with self.assertRaisesRegex(RuntimeError, "exact qualified Atlas"):
            self.assemble(mapserver_progress_profile=prepare.MAPSERVER_PROGRESS_PROFILE)
        self.use_progress_package()
        with self.assertRaisesRegex(RuntimeError, "exact qualified Atlas"):
            self.assemble()
        self.assertFalse((self.root / "candidate").exists())
        with self.assertRaisesRegex(RuntimeError, "Unknown MapServer progress profile"):
            self.assemble(mapserver_progress_profile="unknown")

    def test_progress_parser_is_required_and_rehashed_checkout_substitution_fails(self):
        self.use_progress_package()
        profile = prepare.MAPSERVER_PROGRESS_PROFILE
        self.assemble(mapserver_progress_profile=profile)
        parser = self.root / "candidate/game_map_progress.py"
        parser.write_text("substituted parser")
        self.rewrite_inventory(parser.name)
        with self.assertRaisesRegex(RuntimeError, "guest script differs"):
            prepare.verify_device_metadata(self.root / "candidate", mapserver_progress_profile=profile)
        parser.unlink()
        with self.assertRaisesRegex(RuntimeError, "inventory|Missing"):
            prepare.verify_device_metadata(self.root / "candidate", mapserver_progress_profile=profile)

    def test_rehashed_progress_bundle_cannot_relabel_the_donor_as_wrapper(self):
        self.use_progress_package()
        profile = prepare.MAPSERVER_PROGRESS_PROFILE
        self.assemble(mapserver_progress_profile=profile)
        path = self.root / "candidate/runtime-manifest.json"
        value = json.loads(path.read_text())
        value["atlas_device_bundle"]["package_repository_commit"] = value["repository_commit"]
        write_json(path, value)
        with self.assertRaisesRegex(RuntimeError, "bundle contract differs"):
            prepare.verify_device_assets(self.root / "candidate", mapserver_progress_profile=profile)

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
