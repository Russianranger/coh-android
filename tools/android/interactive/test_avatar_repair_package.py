"""Focused repair trust boundaries and preserved package metadata."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest import mock

SPEC = importlib.util.spec_from_file_location("avatar_repair_package", Path(__file__).with_name("build_avatar_repair_apk.py"))
repair = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repair)


def qualified():
    base = repair.builder()
    files = {name: base.file_pin(repair.ROOT / name) for name in (
        "android/guest/" + repair.HELPER, repair.QUALIFICATION_SCRIPT, repair.WORKFLOW,
        "tools/android/interactive/build_avatar_repair_apk.py")}
    return {"format": 1, "status": "passed", "scope": repair.QUALIFICATION_SCOPE,
            "machine": "aarch64", "guest_uid": 1000, "execution_platform": "native_proot",
            "repository_commit": "a" * 40, "donor_apk_sha256": repair.DONOR_APK["sha256"],
            "helper_sha256": files["android/guest/" + repair.HELPER]["sha256"],
            "qualifier_sha256": files[repair.QUALIFICATION_SCRIPT]["sha256"], "source_files": files,
            "fixture": {"old_read_nofollow_errno": 40, "repaired_files": 21, "repeated_reused_files": 21,
                        "exact_bytes_metadata_preserved": True, "hidden_backing_entries_removed": True,
                        "sentinels_preserved": True, "negative_cases_passed": True,
                        "interruption_cases": {name: {"retry_passed": True, "all_payloads_preserved": True,
                            "hidden_backing_entries_removed": True} for name in ("after_leaf_replacement", "after_intermediate_removal")},
                        "healthy_links_refused_unchanged": {"refused": True, "all_entries_preserved": True}},
            "native_proot_build": {"target": "linux-arm64", "source_commit": "7266fb3e8516535682f5a9c8f3a7e70f6506eddb",
                "source_tree": "8fcee3911b8e0848a1fc75c2e9827316ba658a5a", "sysvipc_memfd_patch": True,
                "optional_acceleration_patch": False}}


class RepairTrustTests(unittest.TestCase):
    def test_passed_exact_native_qualification_is_required(self):
        receipt = qualified()
        repair.validate_qualification(receipt, "a" * 40)
        for key, value in (("status", "failed"), ("machine", "x86_64"), ("guest_uid", 0),
                           ("execution_platform", "native"), ("repository_commit", "b" * 40),
                           ("donor_apk_sha256", "f" * 64), ("helper_sha256", "f" * 64),
                           ("qualifier_sha256", "f" * 64), ("source_files", {})):
            changed = copy.deepcopy(receipt)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                repair.validate_qualification(changed, "a" * 40)

    def test_negative_preservation_and_legacy_reproduction_are_required(self):
        receipt = qualified()
        for key, value in (("old_read_nofollow_errno", 0), ("repaired_files", 20), ("repeated_reused_files", 0),
                           ("exact_bytes_metadata_preserved", False), ("hidden_backing_entries_removed", False),
                           ("sentinels_preserved", False), ("negative_cases_passed", False)):
            changed = copy.deepcopy(receipt)
            changed["fixture"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                repair.validate_qualification(changed, "a" * 40)

    def test_accepted_proot_source_and_patch_family_are_required(self):
        receipt = qualified()
        for key, value in (("target", "android-arm64"), ("source_commit", "f" * 40),
                           ("source_tree", "f" * 40), ("sysvipc_memfd_patch", False),
                           ("optional_acceleration_patch", True)):
            changed = copy.deepcopy(receipt)
            changed["native_proot_build"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                repair.validate_qualification(changed, "a" * 40)

    def test_interrupted_retry_and_healthy_link_refusal_evidence_are_required(self):
        receipt = qualified()
        for mutation in ("missing_retry", "retry_changed_payload", "retry_left_backing", "healthy_changed"):
            changed = copy.deepcopy(receipt)
            if mutation == "missing_retry":
                del changed["fixture"]["interruption_cases"]["after_leaf_replacement"]
            elif mutation == "retry_changed_payload":
                changed["fixture"]["interruption_cases"]["after_intermediate_removal"]["all_payloads_preserved"] = False
            elif mutation == "retry_left_backing":
                changed["fixture"]["interruption_cases"]["after_leaf_replacement"]["hidden_backing_entries_removed"] = False
            else:
                changed["fixture"]["healthy_links_refused_unchanged"]["all_entries_preserved"] = False
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                repair.validate_qualification(changed, "a" * 40)

    def test_qualification_cannot_relabel_changed_source_bytes(self):
        receipt = qualified()
        receipt["source_files"][repair.WORKFLOW] = {"bytes": 1, "sha256": "f" * 64}
        with self.assertRaisesRegex(ValueError, "changed after verification"):
            repair.validate_qualification(receipt, "a" * 40)

    def test_donor_is_bound_before_any_qualification_extraction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            apk, report = root / "donor.apk", root / "report.json"
            apk.write_bytes(b"corrupted APK")
            report.write_text("{}")
            output = root / "output"
            args = type("Args", (), {"donor_apk": apk, "donor_build_report": report, "output": output})
            with self.assertRaisesRegex(ValueError, "changed after verification"):
                repair.prepare(args)
            self.assertFalse(output.exists())


class NarrowDerivativeTests(unittest.TestCase):
    def test_only_helper_and_two_verification_manifests_change(self):
        old = {"bytes": 10, "sha256": "a" * 64}
        new = {"bytes": 20, "sha256": "b" * 64}
        client = {"scope": "actual_client_startup_guest", "repository_commit": "c" * 40,
                  "files": {repair.HELPER: old, "client-runtime.zip": old}, "other": {"retained": True}}
        runtime = {"repository_commit": "c" * 40, "scope": "old",
                   "files": {**client["files"], "client-manifest.json": old},
                   "accepted_base_runtime": {"untouched": True}, "client_bundle": {"retained": True}}
        runtime_before, client_before = copy.deepcopy(runtime), copy.deepcopy(client)
        revised, revised_client = repair.repair_manifests(runtime, client, new, new, "d" * 40)
        self.assertEqual(runtime, runtime_before)
        self.assertEqual(client, client_before)
        expected_client = copy.deepcopy(client)
        expected_client["files"][repair.HELPER] = new
        self.assertEqual(revised_client, expected_client)
        expected_runtime = copy.deepcopy(runtime)
        expected_runtime["files"][repair.HELPER] = new
        expected_runtime["files"]["client-manifest.json"] = new
        expected_runtime["repository_commit"] = "d" * 40
        expected_runtime["scope"] = revised["scope"]
        self.assertEqual(revised, expected_runtime)
        self.assertEqual(repair.CHANGED_PAYLOADS, {"assets/runtime/character_avatar_assets.py",
            "assets/runtime/client-manifest.json", "assets/runtime/runtime-manifest.json"})

    def test_missing_verification_pins_are_rejected(self):
        for runtime, client in (({"files": {}}, {"files": {}}),
                                ({"files": {repair.HELPER: {}}}, {"files": {repair.HELPER: {}}})):
            with self.assertRaises(ValueError):
                repair.repair_manifests(runtime, client, {"bytes": 1, "sha256": "a" * 64}, {}, "b" * 40)

    def test_manifest_advances_version_without_mutating_source_or_app_identity(self):
        base = repair.builder()
        source = repair.ROOT / "android/interactive/src/main/AndroidManifest.xml"
        original = source.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "AndroidManifest.xml"
            repair.repair_android_manifest(source, target)
            repair.builder(repaired=True).verify_source_manifest(target)
            self.assertIn(b'android:versionName="0.11.1"', target.read_bytes())
            self.assertIn(b'android:versionCode="7"', target.read_bytes())
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(base.VERSION_NAME, "0.10.0")


class PublicationTests(unittest.TestCase):
    def prepare(self, root):
        paths = tuple(root / name for name in (repair.APK_NAME, repair.APK_NAME + ".sha256", repair.NOTES_NAME))
        for path, data in zip(paths, (b"signed APK", b"checksum", b"testing notes")):
            path.write_bytes(data)
        return {"repository_commit": "a" * 40, **repair.builder().file_pin(paths[0])}, paths

    def api(self, *, bad_upload=False, existing_release=False):
        api = mock.Mock()
        def request(path, data=None, *, method=None, upload=False):
            if path.startswith(("/releases/tags/", "/git/ref/tags/")):
                if existing_release:
                    return {"id": 10}
                raise urllib.error.HTTPError("https://api.github.com", 404, "Not Found", {}, None)
            if path == "/releases":
                self.assertTrue(data["draft"])
                return {"id": 10, "draft": True, "prerelease": True, "tag_name": repair.RELEASE_TAG}
            if upload:
                pin = repair.builder().file_pin(data)
                return {"name": data.name, "state": "uploaded", "size": pin["bytes"],
                        "digest": "sha256:" + ("f" * 64 if bad_upload else pin["sha256"])}
            return {"id": 10, "draft": False, "prerelease": True, "tag_name": repair.RELEASE_TAG,
                    "html_url": "https://github.com/release"}
        api.request.side_effect = request
        return api

    def test_all_exact_uploads_are_verified_before_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            report, assets = self.prepare(Path(directory))
            api = self.api()
            repair.publish_release(api, report, assets, "notes")
            uploads = [call for call in api.request.call_args_list if call.kwargs.get("upload")]
            self.assertEqual([call.args[1].name for call in uploads], [path.name for path in assets])
            self.assertEqual(api.request.call_args_list[-1].kwargs.get("method"), "PATCH")

    def test_bad_upload_or_existing_release_is_never_published_or_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            report, assets = self.prepare(Path(directory))
            for mutation in ("upload", "existing"):
                api = self.api(bad_upload=mutation == "upload", existing_release=mutation == "existing")
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    repair.publish_release(api, report, assets, "notes")
                self.assertFalse(any(call.kwargs.get("method") in ("PATCH", "DELETE") for call in api.request.call_args_list))

    def test_unexpected_release_asset_fails_before_any_write(self):
        with tempfile.TemporaryDirectory() as directory:
            report, assets = self.prepare(Path(directory))
            api = self.api()
            with self.assertRaises(ValueError):
                repair.publish_release(api, report, assets + (Path(directory) / "key.jks",), "notes")
            api.request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
