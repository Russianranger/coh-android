"""On-demand zone DbServer layer: source receipt, package contract and guest acceptance (no build)."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'armport/server'), str(ROOT / 'tools/android/interactive'), str(ROOT / 'android/guest')]
import package_external_maps_dbserver as external  # noqa: E402
import local_character_server as character  # noqa: E402
from test_package_reference_runtime import pe_file  # noqa: E402


def layered_inputs():
    base = external.accepted_base()
    bundle = external.bundle_layer.expected_receipt(ROOT, base)
    levelup = external.levelup.expected_receipt(ROOT, base, bundle)
    return base, bundle, levelup


def guest_fixture(root, receipt):
    assets, runtime = root / 'assets', root / 'runtime'
    assets.mkdir(); runtime.mkdir()
    package = json.loads((ROOT / external.manual.ACCEPTED_BASE_MANIFEST).read_text())
    original, library = b'accepted donor executable', b'accepted donor library'
    normal = package['variants']['normal']
    normal['files'] = {'DbServer.exe': {'bytes': len(original), 'sha256': hashlib.sha256(original).hexdigest()},
                       'retained.dll': {'bytes': len(library), 'sha256': hashlib.sha256(library).hexdigest()}}
    (runtime / 'DbServer.exe').write_bytes(original); (runtime / 'retained.dll').write_bytes(library)
    image = pe_file(('KERNEL32.dll',)); (assets / 'startup-dbserver.exe').write_bytes(image)
    base, bundle, levelup = layered_inputs()
    manifest = {'format': 1, 'role': external.ROLE, 'repository_commit': 'a' * 40,
        'source_commit': package['source_commit'], 'base_package_manifest_sha256': external.manual.BASE_PACKAGE_SHA256,
        'replacement_scope': 'fresh_owned_manual_atlas_runtime_DbServer.exe_only',
        'base_package_archive_changed': False, 'architecture': 'Win32', 'configuration': 'OptDebug',
        'postgresql_persistence_fixture': False, 'android_execution_validated': False, 'gameplay_validated': False,
        'retained_normal_files': {'retained.dll': normal['files']['retained.dll']},
        'base_normal_executable': normal['files']['DbServer.exe'],
        'base_normal_cmake_cache_sha256': normal['cmake_cache_sha256'],
        'base_startup_executable': external.bundle_layer.BASE_STARTUP_EXECUTABLE,
        'base_startup_bundle_executable': external.levelup.BASE_STARTUP_BUNDLE_EXECUTABLE,
        'base_levelup_ui_repair_executable': external.BASE_LEVELUP_EXECUTABLE,
        'build_input': base, 'startup_bundle_build_input': bundle, 'levelup_ui_repair_build_input': levelup,
        'external_maps_build_input': receipt,
        'files': {'DbServer.exe': {'bytes': len(image), 'sha256': hashlib.sha256(image).hexdigest()}},
        'dependency_report': {'unresolved': []}, 'odbc_imports': list(external.wine.REQUIRED_IMPORTS)}
    (assets / 'startup-dbserver-manifest.json').write_text(json.dumps(manifest))
    return assets, runtime, package, manifest, original, image


class ExternalMapsDbServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = external.expected_receipt(ROOT)

    def test_receipt_sits_on_the_shipped_level_up_layer_and_matches_the_guest_pins(self):
        base, bundle, levelup = layered_inputs()
        self.assertEqual(character.digest_json(levelup), character.EXTERNAL_MAPS_BASE_LEVELUP_SHA256)
        self.assertEqual(levelup, character.levelup_ui_repair_build_input(base, bundle))
        self.assertEqual(character.digest_json(self.receipt), character.EXTERNAL_MAPS_BUILD_INPUT_SHA256)
        self.assertEqual(character.EXTERNAL_MAPS_BASE_EXECUTABLE, external.BASE_LEVELUP_EXECUTABLE)
        self.assertEqual(character.EXTERNAL_MAPS_ROLE, external.ROLE)
        self.assertEqual(set(self.receipt['patched_sha256']), set(external.PATCHED_FILES))
        self.assertEqual(set(self.receipt['overlay_sha256']), set(external.OVERLAY_FILES))
        self.assertTrue(self.receipt['request_contract']['disabled_by_default'])
        # The acknowledgement is the overlay's own string.
        header = (ROOT / external.OVERLAY / 'DBServer/src/wine_external_maps.h').read_text()
        self.assertIn('"' + self.receipt['request_contract']['acknowledgement'] + '"', header)

    def test_guest_installs_the_layer_inert_with_the_level_up_contracts(self):
        with tempfile.TemporaryDirectory() as temporary:
            assets, runtime, package, _, _, image = guest_fixture(Path(temporary), self.receipt)
            installed = character.install_manual_atlas_dbserver(assets, runtime, package)
            self.assertEqual((runtime / 'DbServer.exe').read_bytes(), image)
            self.assertFalse(installed['external_maps']['enabled'])
            self.assertEqual(installed['external_maps']['request_contract'], self.receipt['request_contract'])
            # The level-up read and save contracts stay active (training save, logging).
            self.assertIsNotNone(installed['levelup_ui_repair_save'])
            self.assertIsNotNone(installed['startup_bundle_save'])

    def test_changed_layer_or_relabeled_role_is_refused_before_replacement(self):
        changes = [lambda m: m['external_maps_build_input']['request_contract'].update(disabled_by_default=False),
                   lambda m: m['external_maps_build_input']['patched_sha256'].update({'DBServer/src/mapxfer.c': 'f' * 64}),
                   lambda m: m.update(base_levelup_ui_repair_executable={'bytes': 1, 'sha256': 'f' * 64}),
                   lambda m: m['levelup_ui_repair_build_input'].update(patch_sha256='f' * 64),
                   lambda m: m.pop('external_maps_build_input'),
                   # A level-up manifest may not carry an unqualified external layer.
                   lambda m: m.update(role=character.LEVELUP_UI_REPAIR_ROLE)]
        for index, change in enumerate(changes):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as temporary:
                assets, runtime, package, manifest, original, _ = guest_fixture(Path(temporary), copy.deepcopy(self.receipt))
                change(manifest)
                (assets / 'startup-dbserver-manifest.json').write_text(json.dumps(manifest))
                with self.assertRaises(character.base.DiagnosticError):
                    character.install_manual_atlas_dbserver(assets, runtime, package)
                self.assertEqual((runtime / 'DbServer.exe').read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
