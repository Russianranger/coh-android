"""Reject changed import payloads, privileged APKs, and diagnostic-ID reuse."""
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest import mock

import build_apk as builder


class IdentityTests(unittest.TestCase):
    def badging(self, *, app_id=builder.APP_ID, permissions=builder.PERMISSIONS,
                minimum="minSdkVersion:'26'", native=""):
        permission_text = "".join("uses-permission: name='" + value + "'\n" for value in sorted(permissions))
        return (f"package: name='{app_id}' versionCode='1' versionName='0.3.0'\n"
                f"{minimum}\ntargetSdkVersion:'35'\n{permission_text}{native}"
                f"launchable-activity: name='{builder.LAUNCHER}' label='COH Atlas Setup' icon=''\n")

    def manifest(self, directory, *, app_id=builder.APP_ID, permissions=builder.PERMISSIONS,
                 shared="", version="0.3.0", sdk="26", launcher=builder.LAUNCHER):
        permissions_text = "".join(f'<uses-permission android:name="{name}" />' for name in sorted(permissions))
        xml = (f'<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="{app_id}" '
               f'android:versionCode="1" android:versionName="{version}" {shared}>'
               f'<uses-sdk android:minSdkVersion="{sdk}" android:targetSdkVersion="35" />'
               f'{permissions_text}<application><activity android:name="{launcher}" android:exported="true">'
               '<intent-filter><action android:name="android.intent.action.MAIN" />'
               '<category android:name="android.intent.category.LAUNCHER" /></intent-filter>'
               '</activity></application></manifest>')
        path = directory / "AndroidManifest.xml"
        path.write_text(xml)
        return path

    def test_sdk35_and_older_aapt_dialects(self):
        builder.verify_badging(self.badging())
        builder.verify_badging(self.badging(minimum="sdkVersion:'26'"))

    def test_accepted_diagnostic_ids_cannot_be_overwritten(self):
        for app_id in ("io.github.russianranger.cohdiagnostic", "io.github.russianranger.cohdiagnostic.m3"):
            with self.subTest(app_id=app_id), self.assertRaisesRegex(ValueError, "package/version"):
                builder.verify_badging(self.badging(app_id=app_id))
            with tempfile.TemporaryDirectory() as temp, self.assertRaisesRegex(ValueError, "identity"):
                builder.verify_source_manifest(self.manifest(Path(temp), app_id=app_id))

    def test_internet_and_storage_permissions_are_rejected(self):
        for name in ("INTERNET", "MANAGE_EXTERNAL_STORAGE", "READ_EXTERNAL_STORAGE"):
            permissions = builder.PERMISSIONS | {"android.permission." + name}
            with self.subTest(permission=name), self.assertRaisesRegex(ValueError, "permissions"):
                builder.verify_badging(self.badging(permissions=permissions))
            with tempfile.TemporaryDirectory() as temp, self.assertRaisesRegex(ValueError, "permissions"):
                builder.verify_source_manifest(self.manifest(Path(temp), permissions=permissions))

    def test_missing_foreground_import_permission_rejected(self):
        permissions = builder.PERMISSIONS - {"android.permission.FOREGROUND_SERVICE_SPECIAL_USE"}
        with self.assertRaisesRegex(ValueError, "permissions"):
            builder.verify_badging(self.badging(permissions=permissions))

    def test_native_code_and_wrong_sdk_rejected(self):
        with self.assertRaisesRegex(ValueError, "native code"):
            builder.verify_badging(self.badging(native="native-code: 'arm64-v8a'\n"))
        with self.assertRaisesRegex(ValueError, "SDK"):
            builder.verify_badging(self.badging(minimum="minSdkVersion:'25'"))

    def test_shared_identity_old_version_and_wrong_launcher_rejected(self):
        for changes, reason in (({"shared": 'android:sharedUserId="io.github.russianranger.cohdiagnostic"'}, "identity"),
                                ({"version": "0.2.0"}, "identity"), ({"sdk": "25"}, "SDK"),
                                ({"launcher": builder.APP_ID + ".OtherActivity"}, "launcher")):
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as temp:
                with self.assertRaisesRegex(ValueError, reason):
                    builder.verify_source_manifest(self.manifest(Path(temp), **changes))

    def test_offline_import_manifest_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            builder.verify_source_manifest(self.manifest(Path(temp)))

    def test_only_exact_repository_commits_accepted(self):
        self.assertEqual(builder.source_commit("a" * 40), "a" * 40)
        for value in ("main", "a" * 7, "A" * 40, "a" * 40 + "\n", ""):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "exact"):
                builder.source_commit(value)


class PayloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.assets = self.directory / "assets"
        self.assets.mkdir()
        for name in builder.PAYLOAD_NAMES:
            (self.assets / name).write_bytes((name + "\n").encode())
        self.members = [(self.assets / name, "assets/atlas/" + name) for name in sorted(builder.PAYLOAD_NAMES)]
        self.pins = {member: builder.file_pin(path) for path, member in self.members}
        self.apk = self.directory / "fixture.apk"

    def write_apk(self, *, compression=zipfile.ZIP_STORED, extra=None):
        with zipfile.ZipFile(self.apk, "w") as archive:
            archive.writestr("classes.dex", b"dex\nfixture")
            if compression == zipfile.ZIP_STORED:
                builder.append_payloads(archive, self.members)
            else:
                for path, member in self.members:
                    archive.write(path, member, compress_type=compression)
            if extra:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    archive.writestr(extra, b"unexpected")

    def test_all_payloads_preserved(self):
        self.write_apk()
        self.assertEqual(builder.verify_packaged_payloads(self.apk, self.pins), self.pins)

    def test_changed_packaged_bytes_rejected_even_when_crc_valid(self):
        (self.assets / "atlas-assets-index.tsv").write_bytes(b"changed\n")
        self.write_apk()
        with self.assertRaisesRegex(ValueError, "Packaged payload changed"):
            builder.verify_packaged_payloads(self.apk, self.pins)

    def test_duplicate_extra_payload_and_native_members_rejected(self):
        for extra, reason in (("assets/atlas/atlas-text.zip", "duplicate"),
                              ("assets/injected.zip", "payload set"),
                              ("lib/arm64-v8a/libinjected.so", "native libraries")):
            with self.subTest(extra=extra):
                self.write_apk(extra=extra)
                with self.assertRaisesRegex(ValueError, reason):
                    builder.verify_packaged_payloads(self.apk, self.pins)

    def test_missing_dex_and_recompressed_archive_rejected(self):
        with zipfile.ZipFile(self.apk, "w") as archive:
            builder.append_payloads(archive, self.members)
        with self.assertRaisesRegex(ValueError, "DEX missing"):
            builder.verify_packaged_payloads(self.apk, self.pins)
        self.write_apk(compression=zipfile.ZIP_DEFLATED)
        with self.assertRaisesRegex(ValueError, "without APK recompression"):
            builder.verify_packaged_payloads(self.apk, self.pins)

    def test_large_payload_verification_never_uses_unbounded_reads(self):
        with (self.assets / "atlas-text.zip").open("wb") as stream:
            for _ in range(9):
                stream.write(b"0123456789abcdef" * 16384)
        self.pins = {member: builder.file_pin(path) for path, member in self.members}
        self.write_apk()
        original_read = zipfile.ZipExtFile.read

        def bounded_read(stream, size=-1):
            self.assertGreater(size, 0, "APK members must not be loaded in full")
            self.assertLessEqual(size, builder.STREAM_BLOCK)
            return original_read(stream, size)

        with mock.patch.object(zipfile.ZipFile, "read", side_effect=AssertionError("Use streamed members")), \
                mock.patch.object(zipfile.ZipExtFile, "read", bounded_read):
            builder.verify_packaged_payloads(self.apk, self.pins)

    def contract(self):
        result = {"repository.commit": "a" * 40}
        for name, prefix in (("atlas-text.zip", "text.archive"), ("atlas-text-index.tsv", "text.index"),
                             ("atlas-assets-index.tsv", "asset.index")):
            pin = self.pins["assets/atlas/" + name]
            result[prefix + ".bytes"] = pin["bytes"]
            result[prefix + ".sha256"] = pin["sha256"]
        return result

    def test_commits_forwarded_to_trusted_bundle_verifier_and_receipt_not_packaged(self):
        (self.assets / "atlas-import-build.json").write_text("{}")
        with mock.patch("package_game_import.verify_package", return_value=self.contract()) as verifier:
            contract, members, pins = builder.payloads(self.assets, "a" * 40)
        verifier.assert_called_once_with(self.assets, repository_commit="a" * 40)
        self.assertEqual({path.name for path, _ in members}, builder.PAYLOAD_NAMES)
        self.assertEqual(pins, self.pins)
        self.assertEqual(contract["repository.commit"], "a" * 40)

    def test_mutation_after_trusted_verification_rejected(self):
        contract = self.contract()
        (self.assets / "atlas-text.zip").write_bytes(b"different")
        with mock.patch("package_game_import.verify_package", return_value=contract):
            with self.assertRaisesRegex(ValueError, "changed after verification"):
                builder.payloads(self.assets, "a" * 40)

    def test_linked_payload_rejected(self):
        path = self.assets / "atlas-text.zip"
        target = self.directory / "outside.zip"
        path.rename(target)
        path.symlink_to(target)
        with mock.patch("package_game_import.verify_package", return_value=self.contract()):
            with self.assertRaisesRegex(ValueError, "linked APK payload"):
                builder.payloads(self.assets, "a" * 40)


if __name__ == "__main__":
    unittest.main()
