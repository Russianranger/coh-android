import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('coh_f_recovery_audit', HERE / 'audit_recovery.py')
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class RecoveryAuditTests(unittest.TestCase):
    def test_git_blob_identity_and_path_specific_history(self):
        digest = AUDIT.blob(b'example\n')
        self.assertEqual(AUDIT.blob(b''), 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391')
        self.assertEqual(AUDIT.classify('file', digest, {'file': digest}, {}), 'identical_at_pin')
        self.assertEqual(AUDIT.classify('file', digest, {'file': 'new'},
                                      {('file', digest): 'old'}), 'remote_history_superseded')
        self.assertEqual(AUDIT.classify('file', digest, {'file': 'new'},
                                      {('another', digest): 'old'}), 'different_unclassified')
        self.assertEqual(AUDIT.classify('missing', digest, {}, {}), 'not_at_pin')

    def test_symlink_read_refuses_and_preserves_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            actual = root / 'actual'
            actual.write_bytes(b'immutable')
            (root / 'link').symlink_to(actual)
            with self.assertRaises(OSError):
                AUDIT.read_regular(root / 'link')
            self.assertEqual(AUDIT.read_regular(actual), b'immutable')

    def test_nonregular_input_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises((OSError, ValueError)):
                AUDIT.read_regular(Path(tmp))


if __name__ == '__main__':
    unittest.main()
