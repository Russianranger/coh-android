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
        self.assertFalse(contract['mapserver_included'])

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
