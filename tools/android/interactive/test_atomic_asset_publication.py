"""Asset publication retains one regular leaf and never replaces an input."""
import ctypes
import errno
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import client_startup_diagnostic as client


class AtomicAssetPublicationTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.temporary = self.root / '.world-pending-test'
        self.target = self.root / 'ground.geo'
        self.temporary.write_bytes(b'checked immutable Atlas geometry')
        self.temporary.chmod(0o444)
        os.utime(self.temporary, (client.CACHE_EPOCH, client.CACHE_EPOCH))

    def identity(self, path):
        info = path.lstat()
        return (path.read_bytes(), info.st_dev, info.st_ino, stat.S_IMODE(info.st_mode),
                info.st_mtime_ns, info.st_nlink)

    def test_publication_moves_exact_bytes_metadata_and_inode_to_one_regular_leaf(self):
        before = self.identity(self.temporary)
        client.publish_new_regular_file(self.temporary, self.target)
        self.assertEqual(self.identity(self.target), before)
        self.assertFalse(self.temporary.exists())
        self.assertEqual({path.name for path in self.root.iterdir()}, {self.target.name})
        self.assertTrue(stat.S_ISREG(self.target.lstat().st_mode))
        self.assertFalse(self.target.is_symlink())
        self.assertEqual(self.target.stat().st_nlink, 1)
        self.assertEqual(sum(path.stat().st_size for path in self.root.iterdir()), len(before[0]))

    def test_existing_regular_target_keeps_its_bytes_inode_and_temporary_source(self):
        self.target.write_bytes(b'preserved imported input')
        self.target.chmod(0o400)
        os.utime(self.target, (client.CACHE_EPOCH - 1, client.CACHE_EPOCH - 1))
        source_before, target_before = self.identity(self.temporary), self.identity(self.target)
        with self.assertRaises((client.base.DiagnosticError, OSError)):
            client.publish_new_regular_file(self.temporary, self.target)
        self.assertEqual(self.identity(self.temporary), source_before)
        self.assertEqual(self.identity(self.target), target_before)
        self.assertEqual({path.name for path in self.root.iterdir()}, {self.temporary.name, self.target.name})

    def test_existing_symlink_and_dangling_symlink_are_refused_before_native_rename(self):
        for dangling in (False, True):
            with self.subTest(dangling=dangling):
                backing = self.root / 'preserved-backing'
                if not dangling:
                    backing.write_bytes(b'preserved external input')
                self.target.symlink_to(backing)
                link_before = (self.target.lstat().st_ino, os.readlink(self.target))
                source_before = self.identity(self.temporary)
                with patch.object(client.C, 'CDLL') as load_library:
                    with self.assertRaises((client.base.DiagnosticError, OSError)):
                        client.publish_new_regular_file(self.temporary, self.target)
                    load_library.assert_not_called()
                self.assertEqual(self.identity(self.temporary), source_before)
                self.assertEqual((self.target.lstat().st_ino, os.readlink(self.target)), link_before)
                if not dangling:
                    self.assertEqual(backing.read_bytes(), b'preserved external input')
                else:
                    self.assertFalse(backing.exists())
                self.target.unlink()
                backing.unlink(missing_ok=True)

    def test_target_created_after_preflight_is_preserved_by_native_noreplace(self):
        native = ctypes.CDLL(None, use_errno=True).renameat2
        native.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
        native.restype = ctypes.c_int
        source_before = self.identity(self.temporary)
        target_before = None

        def raced_rename(old_fd, old_path, new_fd, new_path, flags):
            nonlocal target_before
            self.assertEqual((old_fd, new_fd, flags), (-100, -100, 1))
            self.assertEqual(old_path, os.fsencode(self.temporary))
            self.assertEqual(new_path, os.fsencode(self.target))
            self.target.write_bytes(b'input published by another writer')
            target_before = self.identity(self.target)
            return native(old_fd, old_path, new_fd, new_path, flags)

        rename = Mock(side_effect=raced_rename)
        library = SimpleNamespace(renameat2=rename)
        with patch.object(client.C, 'CDLL', return_value=library):
            with self.assertRaises((client.base.DiagnosticError, OSError)):
                client.publish_new_regular_file(self.temporary, self.target)
        rename.assert_called_once()
        self.assertIsNotNone(target_before)
        self.assertEqual(self.identity(self.target), target_before)
        self.assertEqual(self.identity(self.temporary), source_before)
        self.assertEqual({path.name for path in self.root.iterdir()}, {self.temporary.name, self.target.name})

    def test_missing_native_symbol_fails_closed_without_a_link_or_replacing_rename(self):
        source_before = self.identity(self.temporary)
        with patch.object(client.C, 'CDLL', return_value=SimpleNamespace()), \
                patch.object(client.os, 'link') as link, \
                patch.object(client.os, 'replace') as replace, \
                patch.object(client.os, 'rename') as rename:
            with self.assertRaises((client.base.DiagnosticError, OSError)):
                client.publish_new_regular_file(self.temporary, self.target)
            link.assert_not_called(); replace.assert_not_called(); rename.assert_not_called()
        self.assertEqual(self.identity(self.temporary), source_before)
        self.assertFalse(os.path.lexists(self.target))

    def test_native_errors_fail_closed_without_a_link_or_replacing_rename(self):
        for error in (errno.ENOSYS, errno.EOPNOTSUPP, errno.EXDEV, errno.EACCES):
            with self.subTest(error=error):
                source_before = self.identity(self.temporary)
                native = Mock(return_value=-1)
                with patch.object(client.C, 'CDLL', return_value=SimpleNamespace(renameat2=native)), \
                        patch.object(client.C, 'get_errno', return_value=error), \
                        patch.object(client.os, 'link') as link, \
                        patch.object(client.os, 'replace') as replace, \
                        patch.object(client.os, 'rename') as rename:
                    with self.assertRaises((client.base.DiagnosticError, OSError)):
                        client.publish_new_regular_file(self.temporary, self.target)
                    native.assert_called_once()
                    link.assert_not_called(); replace.assert_not_called(); rename.assert_not_called()
                self.assertEqual(self.identity(self.temporary), source_before)
                self.assertFalse(os.path.lexists(self.target))
                self.assertEqual({path.name for path in self.root.iterdir()}, {self.temporary.name})


if __name__ == '__main__':
    unittest.main()
