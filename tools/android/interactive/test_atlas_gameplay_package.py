"""Trust gates and backend preservation for gameplay controls and Atlas materials."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest import mock

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("atlas_gameplay_package_test", HERE / "build_atlas_gameplay_apk.py")
gameplay = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gameplay)


def qualification():
    repository = {"id": gameplay.REPOSITORY_ID, "full_name": gameplay.REPOSITORY}
    apk = {"name": gameplay.DONOR_APK_NAME, "bytes": 100, "sha256": "a" * 64}
    build = {"name": gameplay.DONOR_BUILD_NAME, "bytes": 200, "sha256": "b" * 64}
    artifact = {"id": 71, "name": gameplay.DONOR_ARTIFACT_NAME, "bytes": 300, "sha256": "e" * 64}
    review = {"format": 1, "status": "passed", "qualification_run_id": gameplay.DONOR_RUN_ID,
              "qualification_head_sha": gameplay.DONOR_COMMIT, "apk_sha256": apk["sha256"],
              "donor_apk": apk, "donor_build_report": build, "apk_artifact": artifact,
              "atlas_world_visible": True, "avatar_visible": True,
              "qualification_artifact": {"id": 72, "bytes": 400, "sha256": "b" * 64},
              "host_report": {"name": gameplay.HOST_REPORT_NAME, "bytes": 100, "sha256": "c" * 64},
              "qualification_driver": {"name": gameplay.DRIVER_NAME, "bytes": 100, "sha256": "f" * 64},
              "visual_evidence_frames": [{"name": "client-evidence/reopen/world.png", "bytes": 100, "sha256": "d" * 64}]}
    review["qualification_run_id"], review["qualification_head_sha"] = 123456789, "2" * 40
    run = {"id": gameplay.DONOR_RUN_ID, "run_attempt": 1, "status": "completed", "conclusion": "failure",
           "head_sha": gameplay.DONOR_COMMIT, "head_branch": gameplay.BRANCH, "event": "push",
           "path": gameplay.DONOR_WORKFLOW, "repository": repository, "head_repository": repository.copy()}
    jobs = {"total_count": 4, "jobs": [{"name": name, "run_id": gameplay.DONOR_RUN_ID, "status": "completed",
             "conclusion": "success", "labels": ["ubuntu-24.04-arm"] if name == "runtime" else []}
             for name in ("tooling", "client-caches", "apk", "runtime")]}
    artifacts = {}
    for name, pin in ((gameplay.DONOR_ARTIFACT_NAME, artifact), (gameplay.EVIDENCE_NAME, review["qualification_artifact"])):
        artifacts[name] = {"id": pin["id"], "name": name, "expired": False, "size_in_bytes": pin["bytes"],
                           "digest": "sha256:" + pin["sha256"], "workflow_run": {"id": gameplay.DONOR_RUN_ID,
                               "head_sha": gameplay.DONOR_COMMIT, "repository_id": gameplay.REPOSITORY_ID,
                               "head_repository_id": gameplay.REPOSITORY_ID}}
    qualified_run = {**run, "id": review["qualification_run_id"], "head_sha": review["qualification_head_sha"],
                     "conclusion": "success", "path": gameplay.QUALIFICATION_WORKFLOW}
    qualified_jobs = {"total_count": 2, "jobs": [{**job, "run_id": review["qualification_run_id"]}
                                                for job in jobs["jobs"] if job["name"] in ("tooling", "runtime")]}
    evidence = artifacts[gameplay.EVIDENCE_NAME]
    evidence["workflow_run"]["id"], evidence["workflow_run"]["head_sha"] = review["qualification_run_id"], review["qualification_head_sha"]
    jobs["jobs"][-1]["conclusion"] = "failure"
    return {"format": 1, "donor": {"run": run, "jobs": jobs, "artifacts": {gameplay.DONOR_ARTIFACT_NAME: artifacts[gameplay.DONOR_ARTIFACT_NAME]}},
            "qualification": {"run": qualified_run, "jobs": qualified_jobs, "artifacts": {gameplay.EVIDENCE_NAME: evidence}}}, review


def receipts():
    _, review = qualification()
    donor = {"format": 1, "apk": gameplay.DONOR_APK_NAME, "repository_commit": gameplay.DONOR_COMMIT,
             **gameplay.builder().checked_pin(review["donor_apk"]), "application_id": gameplay.builder().APP_ID, "version_name": "0.10.0",
             "version_code": 5, "abi": "arm64-v8a", "signature_verified": True, "payload_bytes_verified": True,
             "package_badging_verified": True, "signing_key_created": False, "signer_certificate_sha256": gameplay.SIGNER,
             "expected_signer_certificate_sha256": gameplay.SIGNER, "runtime_manifest_sha256": "e" * 64}
    host = {"format": 1, "status": "passed", "failure": None,
            "scope": "exact_apk_graphical_character_reopen_native_arm64", "repository_commit": gameplay.DONOR_COMMIT,
            "apk_sha256": review["donor_apk"]["sha256"], "runtime_manifest_sha256": "e" * 64,
            "sessions": [{"status": "passed", "failure": None}] * 2,
            "persistent_reopen_continuity": {"same_persistent_profile": True, "fully_stopped_between_sessions": True,
                "existing_powers_and_costume_preserved": True, "synthetic_character_rows": False,
                "new_creation_requested_during_reopen": False}}
    return donor, host, review


class QualifiedRuntimeTrustTests(unittest.TestCase):
    def test_failed_running_forked_or_different_source_cannot_build(self):
        metadata, review = qualification()
        gameplay.validate_qualification(metadata, review)
        for key, value in (("conclusion", "failure"), ("status", "in_progress"), ("head_sha", "f" * 40),
                           ("head_branch", "main"), ("event", "pull_request"), ("run_attempt", 2),
                           ("head_repository", {"id": 99, "full_name": "someone/coh-android"})):
            changed = copy.deepcopy(metadata)
            changed["qualification"]["run"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                gameplay.validate_qualification(changed, review)

    def test_world_and_avatar_review_must_bind_report_artifact_and_screenshots(self):
        metadata, review = qualification()
        for key, value in (("atlas_world_visible", False), ("avatar_visible", False), ("status", "unreviewed"),
                           ("donor_apk", None), ("donor_build_report", {}), ("apk_artifact", {}),
                           ("host_report", {}), ("qualification_artifact", {}), ("visual_evidence_frames", []),
                           ("visual_evidence_frames", [{"name": "../world.png", "bytes": 100, "sha256": "d" * 64}])):
            changed = copy.deepcopy(review)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                gameplay.validate_qualification(metadata, changed)

    def test_exact_artifact_and_arm64_runtime_are_required(self):
        metadata, review = qualification()
        for mutation in ("digest", "expired", "source", "runtime", "duplicate", "pagination"):
            changed = copy.deepcopy(metadata)
            if mutation in ("digest", "expired", "source"):
                artifact = changed["qualification"]["artifacts"][gameplay.EVIDENCE_NAME]
                if mutation == "digest":
                    artifact["digest"] = "sha256:" + "f" * 64
                elif mutation == "expired":
                    artifact["expired"] = True
                else:
                    artifact["workflow_run"]["head_repository_id"] = 99
            elif mutation == "runtime":
                changed["qualification"]["jobs"]["jobs"][-1]["labels"] = ["ubuntu-24.04"]
            elif mutation == "duplicate":
                changed["qualification"]["jobs"]["jobs"].append(changed["qualification"]["jobs"]["jobs"][-1].copy())
                changed["qualification"]["jobs"]["total_count"] += 1
            else:
                changed["qualification"]["jobs"]["total_count"] += 1
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                gameplay.validate_qualification(changed, review)

    def test_donor_build_success_and_separate_corrected_runtime_success_are_distinct(self):
        metadata, review = qualification()
        self.assertEqual("failure", metadata["donor"]["run"]["conclusion"])
        gameplay.validate_qualification(metadata, review)
        metadata["donor"]["jobs"]["jobs"][2]["conclusion"] = "failure"
        with self.assertRaisesRegex(ValueError, "Required source job"):
            gameplay.validate_qualification(metadata, review)
        metadata, review = qualification()
        review["qualification_run_id"] = gameplay.DONOR_RUN_ID
        with self.assertRaisesRegex(ValueError, "separate"):
            gameplay.validate_qualification(metadata, review)

    def test_current_host_driver_is_bound_separately_from_unchanged_apk_source(self):
        _, review = qualification()
        base = gameplay.builder()
        paths = {gameplay.QUALIFICATION_WORKFLOW, "tools/android/interactive/character_reopen_host_smoke.py",
                 "tools/android/interactive/character_host_smoke.py", "tools/android/interactive/host_smoke.py",
                 "tools/android/interactive/login_host_smoke.py"}
        files = {name: base.file_pin(gameplay.ROOT / name) for name in sorted(paths)}
        driver = {"format": 1, "scope": "exact_donor_apk_current_host_harness_native_arm64",
                  "host_harness_repository_commit": review["qualification_head_sha"], "host_harness_repository_tree": "3" * 40,
                  "workflow_path": gameplay.QUALIFICATION_WORKFLOW, "workflow_run_id": review["qualification_run_id"],
                  "workflow_run_attempt": 1, "repository": gameplay.REPOSITORY, "ref": "refs/heads/" + gameplay.BRANCH,
                  "apk_rebuilt": False, "client_or_server_recompiled": False, "fresh_postgresql_profile": True,
                  "synthetic_character_rows": False,
                  "qualification_scope": "two_real_graphical_sessions_with_owned_stack_restart_and_normal_logout",
                  "apk_donor": {"run_id": gameplay.DONOR_RUN_ID, "repository_commit": gameplay.DONOR_COMMIT,
                      "apk": review["donor_apk"], "build_report": review["donor_build_report"], "artifact": review["apk_artifact"]},
                  "source_manifest": {"format": 1, "files": files,
                      "files_sha256": hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}}
        self.assertEqual(files, gameplay.validate_driver(driver, review))
        for key, value in (("host_harness_repository_commit", gameplay.DONOR_COMMIT), ("apk_rebuilt", True),
                           ("synthetic_character_rows", True), ("workflow_run_id", gameplay.DONOR_RUN_ID)):
            changed = copy.deepcopy(driver)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                gameplay.validate_driver(changed, review)
        changed = copy.deepcopy(driver)
        name = "tools/android/interactive/character_reopen_host_smoke.py"
        changed["source_manifest"]["files"][name] = {"bytes": 1, "sha256": "f" * 64}
        changed["source_manifest"]["files_sha256"] = hashlib.sha256(
            json.dumps(changed["source_manifest"]["files"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        with self.assertRaisesRegex(ValueError, "changed after verification"):
            gameplay.validate_driver(changed, review)

    def test_receipts_require_exact_apk_signer_and_real_persistent_sessions(self):
        donor, host, review = receipts()
        gameplay.validate_donor_receipts(donor, host, review)
        for key, value in (("sha256", "f" * 64), ("version_code", 6), ("signing_key_created", True),
                           ("signer_certificate_sha256", "f" * 64), ("payload_bytes_verified", False)):
            changed = donor.copy()
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                gameplay.validate_donor_receipts(changed, host, review)
        changed = copy.deepcopy(host)
        changed["persistent_reopen_continuity"]["synthetic_character_rows"] = True
        with self.assertRaises(ValueError):
            gameplay.validate_donor_receipts(donor, changed, review)


class ShellIsolationTests(unittest.TestCase):
    def test_generated_manifest_advances_version_and_preserves_source_and_profile(self):
        base = gameplay.builder()
        source = base.ROOT / "android/interactive/src/main/AndroidManifest.xml"
        original = source.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "AndroidManifest.xml"
            gameplay.gameplay_manifest(source, target)
            gameplay.builder(gameplay=True).verify_source_manifest(target)
            self.assertIn(b'android:versionName="0.11.0"', target.read_bytes())
            self.assertIn(b'android:versionCode="6"', target.read_bytes())
            self.assertEqual(original, source.read_bytes())
            self.assertEqual("0.10.0", gameplay.builder().VERSION_NAME)
            self.assertEqual("0.11.0", gameplay.builder(gameplay=True).VERSION_NAME)
            with self.assertRaises(ValueError):
                base.verify_source_manifest(target)

    def test_only_two_ui_input_sources_can_differ(self):
        base = gameplay.builder()
        sources = base.java_sources(base.ROOT / "android/interactive/src/main", base.ROOT / "out/no-generated-java")
        pins = {path.relative_to(base.ROOT).as_posix(): base.file_pin(path) for path in sources}
        native = "android/native/client-launcher.c"
        donor = {"java_sources": pins, "native_launcher_source": {native: base.file_pin(base.ROOT / native)}}
        for name in gameplay.INPUT_SOURCES:
            donor["java_sources"][name] = {"bytes": 1, "sha256": "f" * 64}
        preserved = gameplay.verify_backend_sources(donor)
        self.assertFalse(gameplay.INPUT_SOURCES & set(preserved))
        backend = next(name for name in pins if name.endswith("ClientRuntime.java"))
        donor["java_sources"][backend] = {"bytes": 1, "sha256": "f" * 64}
        with self.assertRaisesRegex(ValueError, "changed after verification"):
            gameplay.verify_backend_sources(donor)

    def test_corrupted_donor_apk_fails_before_creating_extraction_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / gameplay.DONOR_APK_NAME
            source.write_bytes(b"corrupted APK")
            destination = root / "extracted"
            with self.assertRaisesRegex(ValueError, "changed after verification"):
                gameplay.extract_donor(source, {"bytes": 100, "sha256": "a" * 64, "payloads": {}}, destination)
            self.assertFalse(destination.exists())

    def test_world_helper_changes_are_limited_to_immutable_pins(self):
        path = gameplay.ROOT / "android/guest/atlas_world_assets.py"
        original = path.read_bytes()
        text = original.decode()
        old, _ = gameplay.world_helper_pins(original)
        changed = text.replace(old["MANIFEST_SHA256"], "f" * 64).replace(
            str(old["FILE_COUNT"]), str(old["FILE_COUNT"] + 27), 1).encode()
        delta = gameplay.validate_world_helper(original, changed)
        self.assertEqual(old["FILE_COUNT"] + 27, delta["current"]["FILE_COUNT"])
        for mutation in (changed.replace(b"MAX_ARCHIVE_BYTES = 256", b"MAX_ARCHIVE_BYTES = 512"),
                         changed.replace(b"def package(assets):", b"def changed_package(assets):")):
            with self.assertRaisesRegex(ValueError, "beyond immutable"):
                gameplay.validate_world_helper(original, mutation)

    def test_world_extension_preserves_existing_payloads_and_bounds_new_textures(self):
        original = {"data/object_library/existing.geo": {"bytes": 3, "sha256": "a" * 64}}
        added = {"data/texture_library/new%d.texture" % index: {"bytes": 1, "sha256": "b" * 64} for index in range(27)}
        added["data/texture_library/new0.texture"]["bytes"] = 8955931 - 26
        old = {"source_commit": "a" * 40, "data_commit": "b" * 40, "files": original}
        new = {**old, "files": {**original, **added}, "runtime_visual_validated": False, "gameplay_validated": False}
        self.assertEqual(added, gameplay.validate_world_extension(old, new))
        changed = copy.deepcopy(new)
        changed["files"]["data/object_library/existing.geo"]["sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "existing qualified"):
            gameplay.validate_world_extension(old, changed)
        changed = copy.deepcopy(new)
        del changed["files"]["data/texture_library/new0.texture"]
        with self.assertRaisesRegex(ValueError, "27 missing"):
            gameplay.validate_world_extension(old, changed)


class ReleaseBoundaryTests(unittest.TestCase):
    def prepare(self, root):
        base = gameplay.builder()
        assets = tuple(root / name for name in (gameplay.APK_NAME, gameplay.APK_NAME + ".sha256", gameplay.NOTES_NAME))
        for path, data in zip(assets, (b"signed APK", b"checksum", b"testing notes")):
            path.write_bytes(data)
        return {"repository_commit": "a" * 40, "qualification_donor": {"qualification_run_id": 123456789},
                **base.file_pin(assets[0])}, assets

    def api(self, *, wrong_upload=False, existing_release=False):
        api = mock.Mock()

        def request(path, data=None, *, method=None, upload=False):
            if path.startswith(("/releases/tags/", "/git/ref/tags/")):
                if existing_release and path.startswith("/releases/"):
                    return {"id": 10}
                raise urllib.error.HTTPError("https://api.github.com", 404, "Not Found", {}, None)
            if path == "/releases":
                self.assertTrue(data["draft"])
                return {"id": 10, "draft": True, "prerelease": True, "tag_name": gameplay.RELEASE_TAG}
            if upload:
                pin = gameplay.builder().file_pin(data)
                return {"name": data.name, "state": "uploaded", "size": pin["bytes"],
                        "digest": "sha256:" + ("f" * 64 if wrong_upload else pin["sha256"])}
            return {"id": 10, "draft": False, "prerelease": True, "tag_name": gameplay.RELEASE_TAG, "html_url": "https://github.com/release"}

        api.request.side_effect = request
        return api

    def test_release_remains_draft_until_three_exact_uploads_verify(self):
        with tempfile.TemporaryDirectory() as directory:
            report, assets = self.prepare(Path(directory))
            api = self.api()
            gameplay.publish_release(api, report, assets, "testing notes")
            uploads = [call for call in api.request.call_args_list if call.kwargs.get("upload")]
            self.assertEqual([call.args[1].name for call in uploads], [path.name for path in assets])
            self.assertEqual("PATCH", api.request.call_args_list[-1].kwargs.get("method"))
            create = next(call for call in api.request.call_args_list if call.args[0] == "/releases")
            self.assertEqual(report["repository_commit"], create.args[1]["target_commitish"])

    def test_corrupted_upload_and_existing_release_never_publish_or_replace(self):
        with tempfile.TemporaryDirectory() as directory:
            report, assets = self.prepare(Path(directory))
            for mutation in ("upload", "existing"):
                api = self.api(wrong_upload=mutation == "upload", existing_release=mutation == "existing")
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    gameplay.publish_release(api, report, assets, "notes")
                self.assertFalse(any(call.kwargs.get("method") in ("PATCH", "DELETE") for call in api.request.call_args_list))

    def test_extra_assets_and_modified_apk_fail_before_github_write(self):
        with tempfile.TemporaryDirectory() as directory:
            report, assets = self.prepare(Path(directory))
            api = self.api()
            with self.assertRaises(ValueError):
                gameplay.publish_release(api, report, assets + (Path(directory) / "secret.jks",), "notes")
            assets[0].write_bytes(b"different APK")
            with self.assertRaises(ValueError):
                gameplay.publish_release(api, report, assets, "notes")
            api.request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
