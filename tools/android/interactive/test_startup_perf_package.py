"""Host checks for the retained 0.11.3 performance derivative trust boundary."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest import mock
import zipfile


SPEC = importlib.util.spec_from_file_location(
    "startup_perf_package", Path(__file__).with_name("build_startup_perf_apk.py"))
repair = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repair)

CHECKS = (
    "cache_isolation_and_reuse_regressions_passed",
    "readiness_and_log_boundaries_preserved",
    "buffered_rfb_equivalence_verified",
    "ground_save_and_budget_guards_preserved",
    "retained_donor_boundaries_preserved",
)


def qualified():
    return {
        "format": 1, "status": "passed", "scope": repair.QUALIFICATION_SCOPE,
        "repository_commit": "a" * 40,
        "donor_apk_sha256": repair.DONOR_APK["sha256"],
        "source_files": {
            name: repair.builder().file_pin(repair.ROOT / name)
            for name in repair.SOURCE_FILES
        },
        "physical_gameplay_validated": False, "native_runtime_booted": False,
        "tests_run": 45, "policy": copy.deepcopy(repair.POLICY),
        "checks": {name: True for name in CHECKS},
    }


class QualificationTrustTests(unittest.TestCase):
    def test_exact_current_commit_and_focused_qualification_are_required(self):
        receipt = qualified()
        repair.validate_qualification(receipt, "a" * 40)
        for key, value in (
            ("format", 2), ("status", "failed"), ("scope", "native_gameplay"),
            ("repository_commit", "b" * 40), ("donor_apk_sha256", "f" * 64),
            ("physical_gameplay_validated", True), ("native_runtime_booted", True),
            ("tests_run", 19), ("tests_run", True), ("source_files", {}),
        ):
            changed = copy.deepcopy(receipt)
            changed[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                repair.validate_qualification(changed, "a" * 40)

    def test_every_unchanged_budget_value_and_guard_is_required(self):
        receipt = qualified()
        for section in ("policy", "checks"):
            for key in receipt[section]:
                changed = copy.deepcopy(receipt)
                changed[section][key] = (
                    False if section == "checks" else receipt[section][key] + 1)
                with self.subTest(section=section, key=key), self.assertRaises(ValueError):
                    repair.validate_qualification(changed, "a" * 40)

    def test_source_closure_omissions_stale_bytes_and_unsafe_paths_are_rejected(self):
        receipt = qualified()
        for name in repair.SOURCE_FILES:
            changed = copy.deepcopy(receipt)
            del changed["source_files"][name]
            with self.subTest(name=name), self.assertRaises(ValueError):
                repair.validate_qualification(changed, "a" * 40)
        changed = copy.deepcopy(receipt)
        changed["source_files"][repair.WORKFLOW] = {"bytes": 1, "sha256": "f" * 64}
        with self.assertRaises(ValueError):
            repair.validate_qualification(changed, "a" * 40)
        for name in ("../outside.py", "/tmp/outside.py", "tools\\outside.py"):
            changed = copy.deepcopy(receipt)
            changed["source_files"][name] = {"bytes": 1, "sha256": "a" * 64}
            with self.subTest(name=name), self.assertRaises(ValueError):
                repair.validate_qualification(changed, "a" * 40)

    def test_corrupt_lineage_fails_before_json_is_trusted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = [root / (str(index) + ".json") for index in range(4)]
            for path in files:
                path.write_text("{}")
            with self.assertRaises(ValueError):
                repair.validate_lineage(*files)

    def test_donor_identity_does_not_accept_an_empty_or_another_package_receipt(self):
        for receipt in ({}, {"format": 1, "version_name": "0.11.2"},
                        {"format": 1, "version_name": "0.11.3", "signing_key_created": True}):
            with self.subTest(receipt=receipt), self.assertRaises(ValueError):
                repair.validate_donor_receipt(receipt)


class JavaTrustTests(unittest.TestCase):
    def test_rfb_source_reverses_only_the_exact_bounded_input_wrapper(self):
        original = (
            b"package sample;\nimport java.io.DataInputStream;\n"
            b"class Decoder {\n    Decoder(Object input) {\n"
            b"        this.input = new DataInputStream(input);\n    }\n}\n")
        current = original.replace(
            b"import java.io.DataInputStream;\n",
            b"import java.io.BufferedInputStream;\nimport java.io.DataInputStream;\n", 1)
        current = current.replace(
            b"        this.input = new DataInputStream(input);\n",
            b"        // Raw rectangles arrive row by row. Bound read-ahead so those small\n"
            b"        // decoder reads do not each require a local-socket read.\n"
            b"        this.input = new DataInputStream(new BufferedInputStream(input, 64 * 1024));\n", 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source"
            path.write_bytes(original)
            donor_pin = repair.builder().file_pin(path)
        repair.validate_rfb_scope(current, donor_pin)
        for changed in (
            current.replace(b"64 * 1024", b"64 * 1024 * 1024", 1),
            current + b"// unauthorized decoder change\n",
            current.replace(b"class Decoder", b"class ChangedDecoder", 1),
        ):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                repair.validate_rfb_scope(changed, donor_pin)

    def test_only_rfb_source_changes_and_all_donor_sources_are_retained(self):
        base = repair.builder()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rfb = repair.JAVA_ROOT + "InteractiveRfbClient.java"
            input_name = repair.JAVA_ROOT + "ClientInput.java"
            budget = repair.JAVA_ROOT + "ClientSessionBudget.java"
            native = "android/native/client-launcher.c"
            manifest = "android/interactive/src/main/AndroidManifest.xml"
            names = {rfb, input_name, budget}
            for name in names | {native, manifest}:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("original " + name)
            donor = {
                "java_sources": {name: base.file_pin(root / name) for name in names},
                "preserved_sources": {native: base.file_pin(root / native)},
                "source_manifest": base.file_pin(root / manifest),
            }
            (root / rfb).write_text("reviewed buffered RFB transport")
            sources = [root / name for name in sorted(names)]
            with mock.patch.object(repair, "ROOT", root), \
                    mock.patch.object(base, "java_sources", return_value=sources), \
                    mock.patch.object(repair, "builder", return_value=base):
                _, pins, changed = repair.current_java_sources(donor, root / "generated")
                self.assertEqual(set(pins), names)
                self.assertEqual(set(changed), {rfb})
                for name in (input_name, budget, native, manifest):
                    path = root / name
                    original = path.read_bytes()
                    path.write_bytes(original + b" unauthorized")
                    with self.subTest(name=name), self.assertRaises(ValueError):
                        repair.current_java_sources(donor, root / "generated")
                    path.write_bytes(original)
                missing = sources.pop()
                with self.assertRaises(ValueError):
                    repair.current_java_sources(donor, root / "generated")
                sources.append(missing)
                extra = root / (repair.JAVA_ROOT + "Unapproved.java")
                extra.write_text("unapproved")
                sources.append(extra)
                with self.assertRaises(ValueError):
                    repair.current_java_sources(donor, root / "generated")

    def test_source_manifest_changes_only_package_version_metadata(self):
        source = repair.ROOT / "android/interactive/src/main/AndroidManifest.xml"
        original = source.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "AndroidManifest.xml"
            repair.repair_android_manifest(source, target)
            repair.builder(repaired=True).verify_source_manifest(target)
            self.assertIn(b'android:versionName="0.11.4"', target.read_bytes())
            self.assertIn(b'android:versionCode="10"', target.read_bytes())
            self.assertEqual(source.read_bytes(), original)


class PayloadTrustTests(unittest.TestCase):
    def test_verification_manifests_change_only_approved_helper_and_client_pins(self):
        old, new = ({"bytes": 10, "sha256": "a" * 64},
                    {"bytes": 20, "sha256": "b" * 64})
        client = {"format": 1, "scope": "retained",
                  "files": {**{name: old for name in repair.HELPERS},
                            "character_session_budget.py": old}}
        runtime = {"format": 1, "repository_commit": "c" * 40, "scope": "old",
                   "accepted_base_runtime": {"retained": True},
                   "files": {**client["files"], "client-manifest.json": old}}
        original = copy.deepcopy((runtime, client))
        helpers = {name: new for name in repair.HELPERS | {repair.GUEST_ADDITION}}
        revised, revised_client = repair.repair_manifests(runtime, client, helpers, new, "d" * 40)
        expected_client = copy.deepcopy(client)
        expected_client["files"].update(helpers)
        self.assertEqual(revised_client, expected_client)
        expected_runtime = copy.deepcopy(runtime)
        expected_runtime["files"].update(helpers)
        expected_runtime["files"]["client-manifest.json"] = new
        expected_runtime["repository_commit"] = "d" * 40
        expected_runtime["scope"] = revised["scope"]
        self.assertEqual(revised, expected_runtime)
        self.assertEqual((runtime, client), original)

    def test_missing_added_helper_or_unapproved_pin_is_rejected(self):
        helpers = {name: {"bytes": 1, "sha256": "a" * 64} for name in repair.HELPERS}
        for pins in (helpers, {**helpers, repair.GUEST_ADDITION: {}, "unrelated.py": {}}):
            with self.subTest(pins=pins), self.assertRaises(ValueError):
                repair.repair_manifests({"files": {}}, {"files": {}}, pins, {}, "b" * 40)

    def test_actual_payload_diff_and_retained_resources_are_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            names = {
                *repair.ALLOWED_PAYLOADS, *repair.ADDED_PAYLOADS,
                "assets/runtime/character_session_budget.py",
                "assets/runtime/character_avatar_assets.py",
                *repair.builder().NATIVE_MEMBERS,
                "classes.dex", "resources.arsc", "res/drawable/ic_coh_client.xml",
                "AndroidManifest.xml",
            }
            entries = {name: name.encode() for name in names}

            def pin(data):
                temporary = root / "pin"
                temporary.write_bytes(data)
                return repair.builder().file_pin(temporary)

            def apk():
                path = root / "repair.apk"
                with zipfile.ZipFile(path, "w") as archive:
                    for name, data in entries.items():
                        archive.writestr(name, data)
                return path

            pins = {name: pin(data) for name, data in entries.items()}
            payloads = {name: value for name, value in pins.items()
                        if name.startswith(("assets/", "lib/"))}
            donor = {
                "payloads": {name: value for name, value in payloads.items()
                             if name not in repair.ADDED_PAYLOADS},
                "recompiled_dex": pin(b"donor DEX"),
                "retained_android_resources": {
                    name: pins[name] for name in (
                        "resources.arsc", "res/drawable/ic_coh_client.xml")},
            }
            for name in repair.REQUIRED_PAYLOADS:
                donor["payloads"][name] = pin(b"donor " + name.encode())
            repair.verify_derivative(apk(), donor, payloads, pins["classes.dex"])
            for name in ("classes.dex", "resources.arsc", "res/drawable/extra.xml"):
                previous = entries.get(name)
                entries[name] = b"changed"
                with self.subTest(name=name), self.assertRaises(ValueError):
                    repair.verify_derivative(apk(), donor, payloads, pins["classes.dex"])
                if previous is None:
                    del entries[name]
                else:
                    entries[name] = previous
            for name in ("assets/runtime/character_session_budget.py",
                         "assets/runtime/character_avatar_assets.py"):
                changed = copy.deepcopy(payloads)
                changed[name] = pin(b"unapproved replacement")
                with self.subTest(name=name), self.assertRaises(ValueError):
                    repair.verify_derivative(apk(), donor, changed, pins["classes.dex"])
            for name in repair.REQUIRED_PAYLOADS:
                changed = copy.deepcopy(payloads)
                changed[name] = donor["payloads"][name]
                with self.subTest(required=name), self.assertRaises(ValueError):
                    repair.verify_derivative(apk(), donor, changed, pins["classes.dex"])
            changed = copy.deepcopy(payloads)
            for name in repair.ADDED_PAYLOADS:
                del changed[name]
            with self.assertRaises(ValueError):
                repair.verify_derivative(apk(), donor, changed, pins["classes.dex"])


class GuestSourceScopeTests(unittest.TestCase):
    def source_pair(self):
        old = b'''#!/usr/bin/env python3
"""Owned server evidence."""
import hashlib
LOGOUT_MAX_AGE_MS = 120000
RELOCATION_MAX_AGE_MS = 600000

def stable_ground_evidence(logs, delivery, now_utc_ms):
    # Keep the ordinary recovery proof intact.
    return delivery is not None and bool(logs)

class LocalCharacterServer:
    REPORT_KEY = 'character_creation'

    def collect_server_logs(self, target):
        return 0

    def character_evidence(self):
        # Keep the committed SQL and normal logout guard intact.
        return False
'''
        return old, old.replace(b"        return 0\n", b"        return 1\n", 1)

    def test_reviewed_function_body_change_preserves_unapproved_source(self):
        old, new = self.source_pair()
        repair.validate_guest_scope("local_character_server.py", old, new)

    def test_module_constants_and_top_level_guard_functions_cannot_change(self):
        old, new = self.source_pair()
        for before, after in (
            (b"LOGOUT_MAX_AGE_MS = 120000", b"LOGOUT_MAX_AGE_MS = 240000"),
            (b"RELOCATION_MAX_AGE_MS = 600000", b"RELOCATION_MAX_AGE_MS = 1200000"),
            (b"return delivery is not None and bool(logs)", b"return True"),
        ):
            with self.subTest(before=before), self.assertRaises(ValueError):
                repair.validate_guest_scope("local_character_server.py", old, new.replace(before, after, 1))

    def test_unapproved_methods_class_attributes_and_bases_cannot_change(self):
        old, new = self.source_pair()
        for before, after in (
            (b"return False", b"return True"),
            (b"REPORT_KEY = 'character_creation'", b"REPORT_KEY = 'character_reopen'"),
            (b"class LocalCharacterServer:", b"class LocalCharacterServer(UnsafeServer):"),
        ):
            with self.subTest(before=before), self.assertRaises(ValueError):
                repair.validate_guest_scope("local_character_server.py", old, new.replace(before, after, 1))

    def test_reviewed_function_signature_and_decorators_cannot_change(self):
        old, new = self.source_pair()
        for before, after in (
            (b"def collect_server_logs(self, target):",
             b"def collect_server_logs(self, target, allow_mutation=True):"),
            (b"    def collect_server_logs(self, target):",
             b"    @classmethod\n    def collect_server_logs(self, target):"),
        ):
            with self.subTest(after=after), self.assertRaises(ValueError):
                repair.validate_guest_scope("local_character_server.py", old, new.replace(before, after, 1))

    def test_unknown_import_method_and_top_level_execution_are_rejected(self):
        old, new = self.source_pair()
        for changed in (
            new.replace(b"import hashlib\n", b"import hashlib\nimport unauthorized\n", 1),
            new + b"\n    def fabricate_saved_proof(self):\n        return True\n",
            new + b"\nunauthorized_mutation()\n",
            new.replace(b"import hashlib\n", b"import hashlib; unauthorized_mutation()\n", 1),
        ):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                repair.validate_guest_scope("local_character_server.py", old, changed)

    def test_duplicate_or_deleted_functions_are_rejected(self):
        old, new = self.source_pair()
        duplicate = new + b"\n    def character_evidence(self):\n        return True\n"
        removed = new[:new.index(b"    def character_evidence")]
        for changed in (duplicate, removed):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                repair.validate_guest_scope("local_character_server.py", old, changed)

    def test_exact_cache_import_and_log_override_addition_have_fixed_scope(self):
        old, new = self.source_pair()
        new = new.replace(b"import hashlib\n",
                          b"import hashlib\nimport character_server_data_cache as server_data_cache\n", 1)
        new += b"\n    def current_logs(self):\n        return []\n"
        repair.validate_guest_scope("local_character_server.py", old, new)
        for changed in (
            new.replace(b"as server_data_cache", b"as unsafe_cache", 1),
            new.replace(b"as server_data_cache\n", b"as server_data_cache; unauthorized_mutation()\n", 1),
            new.replace(b"def current_logs(self):", b"def current_logs(self, allow_external=False):", 1),
        ):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                repair.validate_guest_scope("local_character_server.py", old, changed)

    def test_guard_comments_remain_exact_and_unknown_guest_names_fail(self):
        old, new = self.source_pair()
        changed = new.replace(b"# Keep the committed SQL and normal logout guard intact.",
                              b"# Change an unapproved guard comment.", 1)
        with self.assertRaises(ValueError):
            repair.validate_guest_scope("local_character_server.py", old, changed)
        with self.assertRaises(ValueError):
            repair.validate_guest_scope("unapproved_helper.py", old, new)

    def test_stage_cache_recorder_is_the_only_allowed_signature_extension(self):
        old, new = self.source_pair()
        stage = (b"\n    def stage_map_data(self, source, target, *, force_private=False):\n"
                 b"        return None\n")
        old += stage
        new += stage.replace(b"force_private=False):", b"force_private=False, cache_recorder=None):", 1)
        repair.validate_guest_scope("local_character_server.py", old, new)
        for changed in (
            new.replace(b"cache_recorder=None", b"cache_recorder=True", 1),
            new.replace(b"cache_recorder=None", b"cache_recorder=None, mutate_sql=False", 1),
            new.replace(b"force_private=False", b"force_private=True", 1),
        ):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                repair.validate_guest_scope("local_character_server.py", old, changed)

    def test_creation_required_adds_only_the_cache_module_and_preserves_save_guards(self):
        old = b'''#!/usr/bin/env python3
import client_login_diagnostic as login
SCOPE = 'actual_character_creation_guest'
REQUIRED = login.REQUIRED | {'character_creation_diagnostic.py', 'local_character_server.py'}

def save_verified(proof, session):
    return proof.get('committed_sql_verified') is True
'''
        new = old.replace(b"'local_character_server.py'}",
                          b"'local_character_server.py', 'character_server_data_cache.py'}", 1)
        repair.validate_guest_scope("character_creation_diagnostic.py", old, new)
        for changed in (
            new.replace(b"login.REQUIRED", b"set()", 1),
            new.replace(b"'local_character_server.py', ", b"", 1),
            new.replace(b"'character_server_data_cache.py'", b"'unapproved_cache.py'", 1),
            new.replace(b"return proof.get('committed_sql_verified') is True", b"return True", 1),
        ):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                repair.validate_guest_scope("character_creation_diagnostic.py", old, changed)


class PublicationTests(unittest.TestCase):
    def prepare(self, root):
        paths = tuple(root / name for name in (
            repair.APK_NAME, repair.APK_NAME + ".sha256", repair.NOTES_NAME))
        for path, data in zip(paths, (b"signed APK", b"checksum", b"testing notes")):
            path.write_bytes(data)
        return {"repository_commit": "a" * 40,
                **repair.builder().file_pin(paths[0])}, paths

    def api(self, *, bad_upload=False, existing_release=False):
        api = mock.Mock()

        def request(path, data=None, *, method=None, upload=False):
            if path.startswith(("/releases/tags/", "/git/ref/tags/")):
                if existing_release:
                    return {"id": 10}
                raise urllib.error.HTTPError("https://api.github.com", 404, "Not Found", {}, None)
            if path == "/releases":
                self.assertTrue(data["draft"])
                return {"id": 10, "draft": True, "prerelease": True,
                        "tag_name": repair.RELEASE_TAG}
            if upload:
                value = repair.builder().file_pin(data)
                return {"name": data.name, "state": "uploaded", "size": value["bytes"],
                        "digest": "sha256:" + ("f" * 64 if bad_upload else value["sha256"])}
            return {"id": 10, "draft": False, "prerelease": True,
                    "tag_name": repair.RELEASE_TAG, "html_url": "https://github.com/release"}

        api.request.side_effect = request
        return api

    def test_every_exact_upload_is_verified_before_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            report, assets = self.prepare(Path(directory))
            api = self.api()
            repair.publish_release(api, report, assets, "notes")
            uploads = [call for call in api.request.call_args_list if call.kwargs.get("upload")]
            self.assertEqual([call.args[1].name for call in uploads],
                             [path.name for path in assets])
            self.assertEqual(api.request.call_args_list[-1].kwargs.get("method"), "PATCH")

    def test_bad_upload_and_existing_release_are_never_published_or_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            report, assets = self.prepare(Path(directory))
            for mutation in ("upload", "existing"):
                api = self.api(bad_upload=mutation == "upload", existing_release=mutation == "existing")
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    repair.publish_release(api, report, assets, "notes")
                self.assertFalse(any(call.kwargs.get("method") in ("PATCH", "DELETE")
                                     for call in api.request.call_args_list))

    def test_unexpected_release_asset_is_rejected_before_any_write(self):
        with tempfile.TemporaryDirectory() as directory:
            report, assets = self.prepare(Path(directory))
            api = self.api()
            with self.assertRaises(ValueError):
                repair.publish_release(api, report, assets + (Path(directory) / "key.jks",), "notes")
            api.request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
