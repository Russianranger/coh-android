import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('verify_server_donors',
    Path(__file__).resolve().parents[1] / 'scripts/verify_server_donors.py')
donors = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(donors)


class ServerDonors(unittest.TestCase):
    def test_restored_bytes_and_corrupt_inventories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'reference/client.zip'
            path.parent.mkdir()
            path.write_bytes(b'original')
            manifest = dict(source_run=39782080360, source_artifact=12428500525,
                files=[dict(path='reference/client.zip', bytes=8,
                            sha256=hashlib.sha256(b'original').hexdigest())])
            self.assertTrue(donors.verify(root, manifest)['verified'])
            path.write_bytes(b'changed!')
            with self.assertRaisesRegex(ValueError, 'digest mismatch'):
                donors.verify(root, manifest)
            path.write_bytes(b'original')
            extra = root / 'extra'
            extra.write_bytes(b'')
            with self.assertRaisesRegex(ValueError, 'unexpected donor'):
                donors.verify(root, manifest)
            extra.unlink()
            path.unlink()
            with self.assertRaisesRegex(ValueError, 'missing donors'):
                donors.verify(root, manifest)
            path.symlink_to('/dev/null')
            with self.assertRaisesRegex(ValueError, 'non-regular donor'):
                donors.verify(root, manifest)
            path.unlink()
            path.parent.rmdir()
            path.parent.symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'non-regular donor'):
                donors.verify(root, manifest)
