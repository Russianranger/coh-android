"""Exercise APK identity, immutable payload provenance and streamed verification."""
import copy
import importlib.util
import json
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest import mock

_spec = importlib.util.spec_from_file_location("atlas_game_apk_builder", Path(__file__).with_name("build_apk.py"))
builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(builder)


class IdentityTests(unittest.TestCase):
    def badging(self, *, app_id=builder.APP_ID, permissions=builder.PERMISSIONS,
                minimum="minSdkVersion:'26'", native="native-code: 'arm64-v8a'\n"):
        permission_text = "".join("uses-permission: name='" + value + "'\n" for value in sorted(permissions))
        return (f"package: name='{app_id}' versionCode='4' versionName='0.4.3'\n"
                f"{minimum}\ntargetSdkVersion:'35'\n{permission_text}{native}"
                f"launchable-activity: name='{builder.LAUNCHER}' label='COH Atlas Test' icon=''\n")

    def manifest(self, directory, *, app_id=builder.APP_ID, permissions=builder.PERMISSIONS,
                 shared="", version="0.4.3", sdk="26", launcher=builder.LAUNCHER,
                 extraction="true", backup="false", exported="false"):
        permissions_text = "".join(f'<uses-permission android:name="{name}" />' for name in sorted(permissions))
        xml = (f'<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="{app_id}" '
               f'android:versionCode="4" android:versionName="{version}" {shared}>'
               f'<uses-sdk android:minSdkVersion="{sdk}" android:targetSdkVersion="35" />'
               f'{permissions_text}<application android:extractNativeLibs="{extraction}" android:allowBackup="{backup}">'
               f'<activity android:name="{launcher}" android:exported="true">'
               '<intent-filter><action android:name="android.intent.action.MAIN" />'
               '<category android:name="android.intent.category.LAUNCHER" /></intent-filter></activity>'
               f'<service android:name=".AtlasGameService" android:exported="{exported}" '
               'android:foregroundServiceType="specialUse" /></application></manifest>')
        path = directory / "AndroidManifest.xml"
        path.write_text(xml)
        return path

    def test_sdk35_and_older_aapt_dialects(self):
        builder.verify_badging(self.badging())
        builder.verify_badging(self.badging(minimum="sdkVersion:'26'"))

    def test_accepted_apps_cannot_be_overwritten(self):
        for app_id in ("io.github.russianranger.cohdiagnostic", "io.github.russianranger.cohdiagnostic.m3",
                       "io.github.russianranger.cohatlas"):
            with self.subTest(app_id=app_id), self.assertRaisesRegex(ValueError, "package/version"):
                builder.verify_badging(self.badging(app_id=app_id))
            with tempfile.TemporaryDirectory() as temp, self.assertRaisesRegex(ValueError, "identity"):
                builder.verify_source_manifest(self.manifest(Path(temp), app_id=app_id))

    def test_unneeded_storage_permission_and_missing_runtime_permission_rejected(self):
        for permissions in (builder.PERMISSIONS | {"android.permission.MANAGE_EXTERNAL_STORAGE"},
                            builder.PERMISSIONS - {"android.permission.INTERNET"},
                            builder.PERMISSIONS - {"android.permission.FOREGROUND_SERVICE_SPECIAL_USE"}):
            with self.subTest(permissions=permissions), self.assertRaisesRegex(ValueError, "permissions"):
                builder.verify_badging(self.badging(permissions=permissions))
            with tempfile.TemporaryDirectory() as temp, self.assertRaisesRegex(ValueError, "permissions"):
                builder.verify_source_manifest(self.manifest(Path(temp), permissions=permissions))

    def test_only_arm64_and_supported_sdk_accepted(self):
        for native in ("", "native-code: 'x86_64'\n", "native-code: 'arm64-v8a' 'x86_64'\n"):
            with self.subTest(native=native), self.assertRaisesRegex(ValueError, "ARM64"):
                builder.verify_badging(self.badging(native=native))
        with self.assertRaisesRegex(ValueError, "SDK"):
            builder.verify_badging(self.badging(minimum="minSdkVersion:'25'"))

    def test_shared_identity_wrong_version_launcher_and_runtime_configuration_rejected(self):
        cases = (({"shared": 'android:sharedUserId="io.github.russianranger.cohatlas"'}, "identity"),
                 ({"version": "0.3.0"}, "identity"), ({"sdk": "25"}, "SDK"),
                 ({"launcher": builder.APP_ID + ".OtherActivity"}, "launcher"),
                 ({"extraction": "false"}, "native extraction"), ({"backup": "true"}, "backup"),
                 ({"exported": "true"}, "private special-use"))
        for changes, reason in cases:
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as temp:
                with self.assertRaisesRegex(ValueError, reason):
                    builder.verify_source_manifest(self.manifest(Path(temp), **changes))

    def test_current_runtime_manifest_accepted(self):
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
        self.runtime = self.directory / "runtime"
        self.native = self.directory / "native"
        for directory in (self.assets, self.runtime, self.native / "arm64-v8a"):
            directory.mkdir(parents=True)
        for name in builder.IMPORT_NAMES:
            (self.assets / name).write_bytes((name + "\n").encode())
        self.contract = {"repository.commit": "a" * 40}
        for name, prefix in (("atlas-text.zip", "text.archive"), ("atlas-text-index.tsv", "text.index"),
                             ("atlas-assets-index.tsv", "asset.index")):
            pin = builder.file_pin(self.assets / name)
            self.contract[prefix + ".bytes"] = str(pin["bytes"])
            self.contract[prefix + ".sha256"] = pin["sha256"]
        elf = b"\x7fELF\x02\x01" + b"\0" * 12 + (183).to_bytes(2, "little")
        for name in builder.NATIVE_NAMES:
            (self.native / "arm64-v8a" / name).write_bytes(elf + name.encode())
        self.receipt = {"target": "android-arm64", "files": {
            name: builder.file_pin(self.native / "arm64-v8a" / name) for name in builder.NATIVE_NAMES}}
        (self.runtime / "proot-build.json").write_text(json.dumps(self.receipt))
        (self.runtime / "game-package.tar.gz").write_bytes(b"fixture compressed payload")
        self.manifest = {"format": 1, "repository_commit": "a" * 40, "files": {
            name: builder.file_pin(self.runtime / name) for name in ("proot-build.json", "game-package.tar.gz")}}
        (self.runtime / "runtime-manifest.json").write_text(json.dumps(self.manifest))
        self.apk = self.directory / "fixture.apk"
        self.members = [(self.assets / name, "assets/atlas/" + name) for name in sorted(builder.IMPORT_NAMES)]
        self.members.extend((path, "assets/runtime/" + path.name) for path in sorted(self.runtime.iterdir()))
        self.members.extend((self.native / "arm64-v8a" / name, "lib/arm64-v8a/" + name)
                            for name in sorted(builder.NATIVE_NAMES))
        self.pins = {member: builder.file_pin(path) for path, member in self.members}

    def payloads(self, *, contract=None, manifest=None):
        with mock.patch.object(builder, "verify_import_package", return_value=contract or self.contract), \
                mock.patch.object(builder, "verify_runtime_assets", return_value=manifest or self.manifest):
            return builder.payloads(self.assets, self.runtime, self.native, "a" * 40)

    def write_apk(self, *, compression=None, extra=None, dex=True, omit=None):
        with zipfile.ZipFile(self.apk, "w") as archive:
            if dex:
                archive.writestr("classes.dex", b"dex\nfixture")
            selected = [(path, member) for path, member in self.members if member != omit]
            if compression is None:
                builder.append_payloads(archive, selected)
            else:
                for path, member in selected:
                    archive.write(path, member, compress_type=compression)
            if extra:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    archive.writestr(extra, b"unexpected")

    def test_all_verified_inputs_forwarded_and_exact_payloads_preserved(self):
        (self.assets / "atlas-import-build.json").write_text("{}")
        with mock.patch.object(builder, "verify_import_package", return_value=self.contract) as imports, \
                mock.patch.object(builder, "verify_runtime_assets", return_value=self.manifest) as runtime:
            contract, manifest, members, pins = builder.payloads(self.assets, self.runtime, self.native, "a" * 40)
        imports.assert_called_once_with(self.assets, "a" * 40)
        runtime.assert_called_once_with(self.runtime)
        self.assertEqual(contract, self.contract)
        self.assertEqual(manifest, self.manifest)
        self.assertEqual(dict((member, path) for path, member in members), dict((member, path) for path, member in self.members))
        self.assertEqual(pins, self.pins)
        self.write_apk()
        self.assertEqual(builder.verify_packaged_payloads(self.apk, pins), pins)

    def test_changed_data_runtime_and_native_payloads_rejected(self):
        for path in (self.assets / "atlas-text.zip", self.runtime / "game-package.tar.gz",
                     self.native / "arm64-v8a/libproot.so"):
            with self.subTest(path=path):
                original = path.read_bytes()
                path.write_bytes(b"changed")
                with self.assertRaisesRegex(ValueError, "changed after verification"):
                    self.payloads()
                path.write_bytes(original)

    def test_metadata_changed_during_verification_rejected(self):
        for path in (self.assets / "atlas-import.properties", self.runtime / "runtime-manifest.json"):
            with self.subTest(path=path):
                original = path.read_bytes()

                def mutate(_assets):
                    path.write_bytes(b"changed")
                    return self.manifest

                with mock.patch.object(builder, "verify_import_package", return_value=self.contract), \
                        mock.patch.object(builder, "verify_runtime_assets", side_effect=mutate):
                    with self.assertRaisesRegex(ValueError, "changed after verification"):
                        builder.payloads(self.assets, self.runtime, self.native, "a" * 40)
                path.write_bytes(original)

    def test_mismatched_candidate_commits_and_unsafe_runtime_members_rejected(self):
        contract = {**self.contract, "repository.commit": "b" * 40}
        with self.assertRaisesRegex(ValueError, "exact candidate commit"):
            self.payloads(contract=contract)
        manifest = {**self.manifest, "repository_commit": "b" * 40}
        with self.assertRaisesRegex(ValueError, "exact candidate commit"):
            self.payloads(manifest=manifest)
        for name in ("../outside", ".", "..", "runtime-manifest.json", "/absolute", "a/b", "a\\b"):
            manifest = copy.deepcopy(self.manifest)
            manifest["files"][name] = {"bytes": 0, "sha256": "a" * 64}
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "Unsafe runtime member"):
                self.payloads(manifest=manifest)

    def test_native_provenance_and_arm64_elf_are_required(self):
        for mode in ("target", "elf"):
            with self.subTest(mode=mode):
                receipt = copy.deepcopy(self.receipt)
                if mode == "target":
                    receipt["target"] = "linux-arm64"
                    reason = "accepted Android PRoot provenance"
                else:
                    path = self.native / "arm64-v8a/libproot.so"
                    path.write_bytes(b"not an ELF" * 3)
                    receipt["files"][path.name] = builder.file_pin(path)
                    reason = "ARM64 ELF"
                (self.runtime / "proot-build.json").write_text(json.dumps(receipt))
                manifest = copy.deepcopy(self.manifest)
                manifest["files"]["proot-build.json"] = builder.file_pin(self.runtime / "proot-build.json")
                with self.assertRaisesRegex(ValueError, reason):
                    self.payloads(manifest=manifest)

    def test_symlinked_payloads_and_native_directory_rejected(self):
        for path in (self.assets / "atlas-text.zip", self.runtime / "game-package.tar.gz",
                     self.native / "arm64-v8a/libproot.so", self.native / "arm64-v8a"):
            with self.subTest(path=path):
                target = self.directory / "outside"
                path.rename(target)
                path.symlink_to(target)
                with self.assertRaisesRegex(ValueError, "linked APK payload"):
                    self.payloads()
                path.unlink()
                target.rename(path)

    def test_changed_packaged_bytes_rejected_even_when_crc_valid(self):
        for path in (self.assets / "atlas-assets-index.tsv", self.runtime / "game-package.tar.gz",
                     self.native / "arm64-v8a/libproot-loader.so"):
            with self.subTest(path=path):
                original = path.read_bytes()
                path.write_bytes(b"changed")
                self.write_apk()
                with self.assertRaisesRegex(ValueError, "Packaged payload changed"):
                    builder.verify_packaged_payloads(self.apk, self.pins)
                path.write_bytes(original)

    def test_duplicate_missing_and_injected_payloads_rejected(self):
        for extra, reason in (("assets/atlas/atlas-text.zip", "duplicate"), ("assets/injected.zip", "payload set"),
                              ("lib/arm64-v8a/libinjected.so", "payload set"), ("lib/x86_64/libproot.so", "payload set")):
            with self.subTest(extra=extra):
                self.write_apk(extra=extra)
                with self.assertRaisesRegex(ValueError, reason):
                    builder.verify_packaged_payloads(self.apk, self.pins)
        self.write_apk(omit="lib/arm64-v8a/libproot-loader.so")
        with self.assertRaisesRegex(ValueError, "payload set"):
            builder.verify_packaged_payloads(self.apk, self.pins)

    def test_missing_dex_and_recompressed_archives_rejected(self):
        self.write_apk(dex=False)
        with self.assertRaisesRegex(ValueError, "DEX missing"):
            builder.verify_packaged_payloads(self.apk, self.pins)
        self.write_apk(compression=zipfile.ZIP_DEFLATED)
        with self.assertRaisesRegex(ValueError, "without APK recompression"):
            builder.verify_packaged_payloads(self.apk, self.pins)

    def test_large_data_runtime_and_native_verification_never_uses_unbounded_reads(self):
        for path in (self.assets / "atlas-text.zip", self.runtime / "game-package.tar.gz",
                     self.native / "arm64-v8a/libproot-loader.so"):
            with path.open("wb") as stream:
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


if __name__ == "__main__":
    unittest.main()
