"""Focused observer repair package pins, narrow source changes and publication."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest import mock
import zipfile

SPEC = importlib.util.spec_from_file_location("ground_repair_package", Path(__file__).with_name("build_ground_repair_apk.py"))
repair = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repair)


def qualified():
    files = {name: repair.builder().file_pin(repair.ROOT / name) for name in repair.SOURCE_FILES}
    return {"format": 1, "status": "passed", "scope": repair.QUALIFICATION_SCOPE,
            "repository_commit": "a" * 40, "donor_apk_sha256": repair.DONOR_APK["sha256"],
            "helper_sha256": files["android/guest/" + repair.HELPER]["sha256"],
            "qualifier_sha256": files[repair.QUALIFICATION_SCRIPT]["sha256"], "source_files": files,
            "physical_gameplay_validated": False, "tests_run": 22,
            "checks": {name: True for name in ("observer_regression_tests_passed", "thor_fixture_replay_passed",
                "entity_log_fallback_refused", "identity_freshness_stability_guards_preserved")},
            "replay": {"position": [123.5, -768.0, -579.0], "accepted_as_native_log": True, "synthetic_delivery": True}}


class RepairTrustTests(unittest.TestCase):
    def test_exact_focused_observer_qualification_is_required(self):
        receipt = qualified()
        repair.validate_qualification(receipt, "a" * 40)
        for key, value in (("status", "failed"), ("scope", "native_gameplay"), ("repository_commit", "b" * 40),
                           ("donor_apk_sha256", "f" * 64), ("physical_gameplay_validated", True),
                           ("helper_sha256", "f" * 64), ("qualifier_sha256", "f" * 64), ("tests_run", 19),
                           ("source_files", {})):
            changed = copy.deepcopy(receipt)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                repair.validate_qualification(changed, "a" * 40)

    def test_archived_replay_cannot_claim_observed_delivery_or_weaken_guards(self):
        receipt = qualified()
        for section, key, value in (
            ("replay", "synthetic_delivery", False), ("replay", "accepted_as_native_log", False),
            ("replay", "position", [123.5, -2000, -579]),
            *(('checks', name, False) for name in receipt['checks'])):
            changed = copy.deepcopy(receipt)
            changed[section][key] = value
            with self.subTest(section=section, key=key), self.assertRaises(ValueError):
                repair.validate_qualification(changed, "a" * 40)

    def test_all_source_dependencies_and_actual_bytes_are_bound(self):
        receipt = qualified()
        for name in repair.SOURCE_FILES:
            changed = copy.deepcopy(receipt)
            del changed["source_files"][name]
            with self.subTest(name=name), self.assertRaises(ValueError):
                repair.validate_qualification(changed, "a" * 40)
        receipt["source_files"][repair.WORKFLOW] = {"bytes": 1, "sha256": "f" * 64}
        with self.assertRaisesRegex(ValueError, "changed after verification"):
            repair.validate_qualification(receipt, "a" * 40)

    def test_donor_bytes_are_pinned_before_any_source_receipt_or_extraction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            apk = root / "donor.apk"
            apk.write_bytes(b"corrupted APK")
            with self.assertRaisesRegex(ValueError, "changed after verification"):
                repair.validate_donor(apk, root / "report.json", root / "source-report.json")

    def test_transitive_retained_source_receipt_checks_every_native_and_java_pin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = repair.builder()
            names = ("android/native/client-launcher.c", "java/Client.java",
                     "android/interactive/src/main/AndroidManifest.xml")
            for name in names:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("retained " + name)
            pins = {name: base.file_pin(root / name) for name in names}
            old = {name: {"bytes": 1, "sha256": "a" * 64} for name in (
                "assets/runtime/character_avatar_assets.py", "assets/runtime/client-manifest.json",
                "assets/runtime/runtime-manifest.json", "assets/runtime/local_character_server.py")}
            new = copy.deepcopy(old)
            changed = set(old) - {"assets/runtime/local_character_server.py"}
            for name in changed:
                new[name] = {"bytes": 2, "sha256": "b" * 64}
            donor = {"payloads": new, "changed_apk_payloads": sorted(changed)}
            previous = {"repository_commit": repair.RETAINED_SOURCE_COMMIT, **repair.RETAINED_SOURCE_APK,
                "version_name": "0.11.0", "version_code": 6, "signer_certificate_sha256": repair.SIGNER,
                "java_sources": {names[1]: pins[names[1]]},
                "preserved_sources": {names[0]: pins[names[0]]},
                "source_manifest": pins[names[2]], "payloads": old}
            report = root / "report.json"
            report.write_text(json.dumps(previous))
            with mock.patch.object(repair, "ROOT", root), mock.patch.object(repair, "RETAINED_SOURCE_BUILD", base.file_pin(report)):
                repair.validate_retained_sources(report, donor)
                for name in names:
                    target = root / name
                    original = target.read_bytes()
                    target.write_bytes(original + b"changed")
                    with self.subTest(name=name), self.assertRaisesRegex(ValueError, "changed after verification"):
                        repair.validate_retained_sources(report, donor)
                    target.write_bytes(original)
                altered = copy.deepcopy(donor)
                altered["payloads"]["assets/runtime/local_character_server.py"] = {"bytes": 2, "sha256": "c" * 64}
                with self.assertRaisesRegex(ValueError, "transitive payload retention"):
                    repair.validate_retained_sources(report, altered)


class NarrowDerivativeTests(unittest.TestCase):
    def test_only_helper_and_two_verification_manifests_change(self):
        old = {"bytes": 10, "sha256": "a" * 64}
        new = {"bytes": 20, "sha256": "b" * 64}
        client = {"scope": "actual_client_startup_guest", "repository_commit": "c" * 40,
                  "files": {repair.HELPER: old, "character_avatar_assets.py": old}, "other": {"retained": True}}
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
        self.assertEqual(repair.CHANGED_PAYLOADS, {"assets/runtime/local_character_server.py",
            "assets/runtime/client-manifest.json", "assets/runtime/runtime-manifest.json"})

    def test_exact_reviewed_helper_transform_preserves_all_other_source_bytes(self):
        donor = (b"preserved prefix\nSERVER_LOG_COUNT_LIMIT = 128\n\n\n"
                 b"old expression and -100 < value[1] < 10000\n"
                 b"require(-100 < position['posy'] < 10000\npreserved suffix\n")
        corrected = repair.repaired_helper(donor)
        self.assertTrue(corrected.startswith(b"preserved prefix\n"))
        self.assertTrue(corrected.endswith(b"\npreserved suffix\n"))
        self.assertEqual(corrected.count(b"above_native_fall_floor"), 3)
        self.assertIn(b"NATIVE_FALL_FLOOR_Y = -2000.0\nFALL_FLOOR_CLEARANCE = 1.0\n", corrected)
        for corrupted in (donor.replace(b"128", b"129"), donor + donor,
                          donor.replace(b"-100 < position", b"-101 < position"), corrected):
            with self.assertRaises(ValueError):
                repair.repaired_helper(corrupted)

    def test_actual_payload_diff_and_retained_shell_are_verified_independently(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entries = {name: name.encode() for name in (
                *repair.CHANGED_PAYLOADS, "assets/runtime/character_avatar_assets.py",
                *repair.builder().NATIVE_MEMBERS, "classes.dex", "resources.arsc",
                "res/drawable/ic_coh_client.xml", "AndroidManifest.xml")}
            def write_apk():
                apk = root / "repair.apk"
                with zipfile.ZipFile(apk, "w") as archive:
                    for name, data in entries.items():
                        archive.writestr(name, data)
                return apk
            pins = {}
            for name, data in entries.items():
                target = root / "temporary"
                target.write_bytes(data)
                pins[name] = repair.builder().file_pin(target)
            payloads = {name: pin for name, pin in pins.items() if name.startswith(("assets/", "lib/"))}
            donor = {"payloads": copy.deepcopy(payloads), "retained_dex": pins["classes.dex"],
                     "retained_android_resources": {name: pins[name] for name in ("resources.arsc", "res/drawable/ic_coh_client.xml")}}
            for name in repair.CHANGED_PAYLOADS:
                donor["payloads"][name] = {"bytes": 1, "sha256": "a" * 64}
            repair.verify_derivative(write_apk(), donor, payloads)
            for name in ("classes.dex", "resources.arsc", "res/drawable/extra.xml"):
                original = entries.get(name)
                entries[name] = b"changed"
                with self.subTest(name=name), self.assertRaises(ValueError):
                    repair.verify_derivative(write_apk(), donor, payloads)
                if original is None:
                    del entries[name]
                else:
                    entries[name] = original
            altered = copy.deepcopy(payloads)
            altered["assets/runtime/character_avatar_assets.py"] = {"bytes": 1, "sha256": "b" * 64}
            with self.assertRaisesRegex(ValueError, "payload boundary"):
                repair.verify_derivative(write_apk(), donor, altered)

    def test_missing_verification_pins_are_rejected(self):
        for runtime, client in (({"files": {}}, {"files": {}}),
                                ({"files": {repair.HELPER: {}}}, {"files": {repair.HELPER: {}}})):
            with self.assertRaises(ValueError):
                repair.repair_manifests(runtime, client, {"bytes": 1, "sha256": "a" * 64}, {}, "b" * 40)

    def test_manifest_advances_version_without_mutating_source_or_app_identity(self):
        source = repair.ROOT / "android/interactive/src/main/AndroidManifest.xml"
        original = source.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "AndroidManifest.xml"
            repair.repair_android_manifest(source, target)
            repair.builder(repaired=True).verify_source_manifest(target)
            self.assertIn(b'android:versionName="0.11.2"', target.read_bytes())
            self.assertIn(b'android:versionCode="8"', target.read_bytes())
            self.assertEqual(source.read_bytes(), original)


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
