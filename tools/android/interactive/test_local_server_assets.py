"""Pin local-login donors and reject malformed server archive inputs."""
import importlib.util
import io
from pathlib import Path
import sys
import tarfile
import tempfile
import types
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('local_login_assets_test', HERE/'prepare_assets.py')
assets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assets)


class LocalServerAssetsTests(unittest.TestCase):
    def test_donors_match_independently_accepted_evidence(self):
        tools = assets.server_tools()
        evidence = tools.accepted_evidence()
        contract = assets.local_server_contract()
        self.assertEqual(36460867428, contract['package_run_id'])
        self.assertEqual(evidence['package_manifest_sha256'], contract['package_manifest_sha256'])
        self.assertEqual(evidence['schema_manifest_sha256'], contract['schema_manifest_sha256'])
        self.assertEqual('normal', contract['variant'])
        self.assertEqual('device', contract['listener_policy'])
        self.assertTrue(contract['mapserver_included'])
        self.assertEqual('android-local-login', contract['persistent_profile'])
        map_contract = contract['mapserver']
        assets.mapserver_tools().accepted_evidence(assets.MAPSERVER_PROFILE)
        self.assertEqual(36630872719, map_contract['package_run_id'])
        self.assertEqual('dispatch_progress_v1', map_contract['mapserver_progress_profile'])
        self.assertEqual('ef1e5b1aa7cad69f2e25d286cc579531c86417d3f7f1a5de86843a350f4024cd', map_contract['package_manifest_sha256'])
        self.assertEqual('52f85c9e2cccfe88eb92f0a2c379a45b14eb997339ce902ed7ba5d470f3690fb', map_contract['mapserver_progress_producer']['mapserver_sha256'])
        self.assertEqual('5d677b9e26def071929d73ffe23ef62418d3dc6c9385abb470b9607af0c47864', map_contract['archive_pin']['sha256'])

    def test_import_loader_preserves_an_existing_prepare_assets_module(self):
        marker = types.ModuleType('unrelated_prepare_assets')
        cache_name = 'coh_login_accepted_dbserver_assets'
        previous_cache = sys.modules.pop(cache_name, None)
        try:
            with mock.patch.dict(sys.modules, {'prepare_assets': marker}):
                before = sys.path[:]
                tools = assets.server_tools()
                self.assertIs(sys.modules['prepare_assets'], marker)
                self.assertEqual(before, sys.path)
                self.assertEqual('eed2ce1f5388195f65a07853919761a93657aca6', tools.PACKAGE_COMMIT)
        finally:
            sys.modules.pop(cache_name, None)
            if previous_cache is not None:
                sys.modules[cache_name] = previous_cache

    def test_mapserver_loader_preserves_existing_helper_modules_and_search_path(self):
        markers = {name: types.ModuleType('unrelated_' + name)
                   for name in ('prepare_assets', 'host_dbserver_smoke', 'host_game_smoke')}
        cache_name = 'coh_character_accepted_atlas_assets'
        previous_cache = sys.modules.pop(cache_name, None)
        try:
            with mock.patch.dict(sys.modules, markers):
                before = sys.path[:]
                tools = assets.mapserver_tools()
                self.assertEqual(before, sys.path)
                for name, module in markers.items():
                    self.assertIs(module, sys.modules[name])
                self.assertEqual(36630872719, tools.MAPSERVER_PROGRESS_RUN_ID)
        finally:
            sys.modules.pop(cache_name, None)
            if previous_cache is not None:
                sys.modules[cache_name] = previous_cache

    def test_modified_mapserver_manifest_fails_before_binary_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary)
            receipt = assets.ROOT/'docs/android-evidence/mapserver-progress-package-36630872719.json'
            (package/'game-package.json').write_bytes(receipt.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError, 'exact accepted MapServer composite manifest'):
                assets.verify_mapserver_package(package)

    def test_modified_mapserver_archive_fails_before_extraction(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root/'game-package.tar.gz'; archive.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'MapServer archive bytes differ'):
                assets.extract_mapserver_archive(archive, root/'output')
            self.assertFalse((root/'output').exists())

    def test_wrong_atlas_apk_cannot_donate_an_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            apk = root/'wrong.apk'; apk.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'Atlas APK bytes differ'):
                assets.recover_mapserver_archive(apk, root/'game-package.tar.gz')
            self.assertFalse((root/'game-package.tar.gz').exists())

    def test_modified_package_receipt_fails_before_binary_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root/'package'; package.mkdir()
            schema = root/'schema'; schema.mkdir()
            receipt = assets.ROOT/'docs/android-evidence/dbserver-package-36460867428.json'
            (package/'package-manifest.json').write_bytes(receipt.read_bytes()+b' ')
            with self.assertRaisesRegex(RuntimeError, 'qualified loopback package'):
                assets.verify_local_server_inputs(package, schema)

    def test_unsafe_archive_never_creates_output_or_traversal_file(self):
        for name in ('../outside', '/outside', 'normal/../../outside'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); donor = root/'assets'; donor.mkdir()
                with tarfile.open(donor/'dbserver-package.tar.gz', 'w:gz') as archive:
                    entry = tarfile.TarInfo(name); entry.size = 1; entry.mode = 0o644
                    archive.addfile(entry, io.BytesIO(b'x'))
                with self.assertRaisesRegex(RuntimeError, 'Unsafe archive path'):
                    assets.extract_local_server_inputs(donor, root/'output')
                self.assertFalse((root/'output').exists())
                self.assertFalse((root/'outside').exists())

    def test_archive_symlink_never_reaches_manifest_validation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); donor = root/'assets'; donor.mkdir()
            with tarfile.open(donor/'dbserver-package.tar.gz', 'w:gz') as archive:
                entry = tarfile.TarInfo('DbServer.exe'); entry.type = tarfile.SYMTYPE
                entry.linkname = '/outside'; entry.mode = 0o644; archive.addfile(entry)
            with self.assertRaisesRegex(RuntimeError, 'metadata is not canonical'):
                assets.extract_local_server_inputs(donor, root/'output')
            self.assertFalse((root/'output').exists())


if __name__ == '__main__':
    unittest.main()
