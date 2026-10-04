"""Session-window source/payload boundaries and retained-signer publication."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest import mock
import zipfile

SPEC = importlib.util.spec_from_file_location("session_window_package", Path(__file__).with_name("build_session_window_apk.py"))
repair = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repair)

# Published 0.11.3 APK payloads, verified against its immutable build receipt:
# session-window-apk-build-report.json SHA256
# 4967e83deff3da231c4bfd3e0f6aa4d83b29669e6b014051c1dd0b196b08a248.
# Later observer changes must not replace this historical derivative's input.
SESSION_WINDOW_FIXTURE_PINS = {
    "client_interactive_diagnostic.py": {
        "bytes": 21380,
        "sha256": "b029df4ba2233450f913deb96f0abe7771634a1836c846a5437b005a796917ea",
    },
    "character_reopen_diagnostic.py": {
        "bytes": 5662,
        "sha256": "243f3a8f261d301b19d55a21a909d5076f2505e7f98dd38b4d0d89aee85159b3",
    },
}


def qualified():
    files = {name: repair.builder().file_pin(repair.ROOT / name) for name in repair.SOURCE_FILES}
    return {"format": 1, "status": "passed", "scope": repair.QUALIFICATION_SCOPE,
            "repository_commit": "a" * 40, "donor_apk_sha256": repair.DONOR_APK["sha256"],
            "source_files": files, "physical_gameplay_validated": False, "tests_run": 45,
            "policy": copy.deepcopy(repair.POLICY),
            "checks": {name: True for name in ("guest_budget_regressions_passed", "java_budget_regressions_passed",
                "ground_and_save_guards_preserved", "phase_identity_and_deadline_caps_preserved")}}


class RepairTrustTests(unittest.TestCase):
    def test_exact_focused_observer_qualification_is_required(self):
        receipt = qualified()
        repair.validate_qualification(receipt, "a" * 40)
        for key, value in (("status", "failed"), ("scope", "native_gameplay"), ("repository_commit", "b" * 40),
                           ("donor_apk_sha256", "f" * 64), ("physical_gameplay_validated", True),
                           ("policy", {}), ("tests_run", 19),
                           ("source_files", {})):
            changed = copy.deepcopy(receipt)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                repair.validate_qualification(changed, "a" * 40)

    def test_policy_caps_reserves_and_ground_save_guards_are_required(self):
        receipt = qualified()
        for section in ("policy", "checks"):
            for key in receipt[section]:
                changed = copy.deepcopy(receipt)
                changed[section][key] = False if section == "checks" else receipt[section][key] + 1
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
                repair.validate_donor(apk, root / "report.json", root / "avatar-report.json", root / "source-report.json")

    def test_java_compilation_closure_allows_only_reviewed_sources_and_budget_addition(self):
        base = repair.builder()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            retained_name = repair.JAVA_ROOT + "ClientInput.java"
            native = "android/native/client-launcher.c"
            manifest = "android/interactive/src/main/AndroidManifest.xml"
            old_names = {*repair.JAVA_CHANGES, retained_name}
            all_names = {*old_names, repair.JAVA_ADDITION, native, manifest}
            for name in all_names:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("original " + name)
            donor = {"java_sources": {name: base.file_pin(root / name) for name in old_names},
                     "preserved_sources": {name: base.file_pin(root / name) for name in (native, retained_name)},
                     "source_manifest": base.file_pin(root / manifest)}
            for name in repair.JAVA_REQUIRED_CHANGES:
                (root / name).write_text("reviewed change " + name)
            sources = [root / name for name in old_names | {repair.JAVA_ADDITION}]
            with mock.patch.object(repair, "ROOT", root), mock.patch.object(base, "java_sources", return_value=sources), \
                    mock.patch.object(repair, "builder", return_value=base):
                _, pins, changed = repair.current_java_sources(donor, root / "generated")
                self.assertEqual(set(pins), old_names | {repair.JAVA_ADDITION})
                self.assertEqual(set(changed), repair.JAVA_REQUIRED_CHANGES)
                target = root / retained_name
                old = target.read_bytes()
                target.write_bytes(old + b"unauthorized")
                with self.assertRaisesRegex(ValueError, "Java changes exceed"):
                    repair.current_java_sources(donor, root / "generated")
                target.write_bytes(old)
                sources.pop()
                with self.assertRaisesRegex(ValueError, "source addition or omission"):
                    repair.current_java_sources(donor, root / "generated")
                sources.append(root / (repair.JAVA_ROOT + "Unapproved.java"))
                sources[-1].write_text("unapproved")
                with self.assertRaisesRegex(ValueError, "source addition or omission"):
                    repair.current_java_sources(donor, root / "generated")



class NarrowDerivativeTests(unittest.TestCase):
    def test_only_two_hooks_new_budget_and_verification_pins_change(self):
        old = {"bytes": 10, "sha256": "a" * 64}
        new = {"bytes": 20, "sha256": "b" * 64}
        client = {"scope": "retained", "repository_commit": "c" * 40,
                  "files": {**{name: old for name in repair.HELPERS}, "local_character_server.py": old}}
        runtime = {"repository_commit": "c" * 40, "scope": "old", "accepted_base_runtime": {"retained": True},
                   "files": {**client["files"], "client-manifest.json": old}}
        before_runtime, before_client = copy.deepcopy(runtime), copy.deepcopy(client)
        helper_pins = {name: new for name in repair.HELPERS | {repair.GUEST_ADDITION}}
        revised, revised_client = repair.repair_manifests(runtime, client, helper_pins, new, "d" * 40)
        expected_client = copy.deepcopy(client)
        expected_client["files"].update(helper_pins)
        self.assertEqual(revised_client, expected_client)
        expected_runtime = copy.deepcopy(runtime)
        expected_runtime["files"].update(helper_pins)
        expected_runtime["files"]["client-manifest.json"] = new
        expected_runtime["repository_commit"] = "d" * 40
        expected_runtime["scope"] = revised["scope"]
        self.assertEqual(revised, expected_runtime)
        self.assertEqual(runtime, before_runtime)
        self.assertEqual(client, before_client)

    def test_exact_deadline_hook_transform_preserves_all_other_diagnostic_bytes(self):
        # Reversing the reviewed additions must leave the complete original
        # diagnostic. Any save-proof or initialization edit then fails closed.
        for name in repair.HELPERS:
            fixture = Path(__file__).with_name("fixtures") / ("session-window-0.11.3-" + name)
            current = fixture.read_bytes()
            self.assertEqual({"bytes": len(current), "sha256": hashlib.sha256(current).hexdigest()},
                             SESSION_WINDOW_FIXTURE_PINS[name])
            if name == "client_interactive_diagnostic.py":
                donor = current.replace(repair.CLIENT_DEADLINE_HOOK, b"", 1)
                donor = donor.replace(b"        self.launcher_started_monotonic = started\n", b"", 1)
                donor = donor.replace(b"                if ready_at is not None:\n                    deadline = self.interaction_deadline(deadline, launch)\n", b"", 1)
                donor = donor.replace(b"                        deadline = self.interaction_deadline(deadline, launch)\n", b"", 1)
            else:
                donor = current.replace(b"import time\n", b"", 1)
                donor = donor.replace(b"import character_session_budget as session_budget\n", b"", 1)
                donor = donor.replace(b"'character_reopen_diagnostic.py', 'character_session_budget.py',", b"'character_reopen_diagnostic.py',", 1)
                donor = donor.replace(repair.REOPEN_DEADLINE_HOOK, b"", 1)
            repair.validate_guest_scope(name, donor, current)
            for mutation in (current + b"\nunauthorized = True\n", current.replace(b"def initialize", b"def initialize_changed", 1)):
                if mutation == current:
                    continue
                with self.subTest(name=name), self.assertRaises(ValueError):
                    repair.validate_guest_scope(name, donor, mutation)
            with self.assertRaises(ValueError):
                repair.validate_guest_scope(name, donor + donor, current)

    def test_actual_payload_diff_and_retained_shell_are_verified_independently(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entries = {name: name.encode() for name in (
                *repair.CHANGED_PAYLOADS, *repair.ADDED_PAYLOADS, "assets/runtime/character_avatar_assets.py",
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
            donor = {"payloads": {name: pin for name, pin in payloads.items() if name not in repair.ADDED_PAYLOADS}, "retained_dex": {"bytes": 1, "sha256": "a" * 64},
                     "retained_android_resources": {name: pins[name] for name in ("resources.arsc", "res/drawable/ic_coh_client.xml")}}
            for name in repair.CHANGED_PAYLOADS:
                donor["payloads"][name] = {"bytes": 1, "sha256": "a" * 64}
            repair.verify_derivative(write_apk(), donor, payloads, pins["classes.dex"])
            for name in ("classes.dex", "resources.arsc", "res/drawable/extra.xml"):
                original = entries.get(name)
                entries[name] = b"changed"
                with self.subTest(name=name), self.assertRaises(ValueError):
                    repair.verify_derivative(write_apk(), donor, payloads, pins["classes.dex"])
                if original is None:
                    del entries[name]
                else:
                    entries[name] = original
            altered = copy.deepcopy(payloads)
            altered["assets/runtime/character_avatar_assets.py"] = {"bytes": 1, "sha256": "b" * 64}
            with self.assertRaisesRegex(ValueError, "payload boundary"):
                repair.verify_derivative(write_apk(), donor, altered, pins["classes.dex"])

    def test_missing_or_extra_helper_verification_pins_are_rejected(self):
        helpers = {name: {"bytes": 1, "sha256": "a" * 64} for name in repair.HELPERS}
        for helper_pins in (helpers, {**helpers, repair.GUEST_ADDITION: {}, "unrelated.py": {}}):
            with self.assertRaises(ValueError):
                repair.repair_manifests({"files": {}}, {"files": {}}, helper_pins, {}, "b" * 40)

    def test_manifest_advances_version_without_mutating_source_or_app_identity(self):
        source = repair.ROOT / "android/interactive/src/main/AndroidManifest.xml"
        original = source.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "AndroidManifest.xml"
            repair.repair_android_manifest(source, target)
            repair.builder(repaired=True).verify_source_manifest(target)
            self.assertIn(b'android:versionName="0.11.3"', target.read_bytes())
            self.assertIn(b'android:versionCode="9"', target.read_bytes())
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
