"""0.13.74: the ownership scan reads a /proc file with one open, one or two reads and a close.

Thor 0.13.73, launch B: 82,700 opens of /proc status and stat files in 593 s, 139 a second in
the world. Path.read_text() also asks for the opened descriptor's status, which under PRoot
is two more stops per file.
"""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'android/guest'))
import diagnostic


class ProcText(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_content_small_large_and_empty(self):
        for name, data in (('small', b'Name:\tx\nUid:\t1000\t1000\n'), ('large', b'ab' * 100000), ('empty', b'')):
            (self.root / name).write_bytes(data)
            self.assertEqual(diagnostic.read_proc_text(self.root / name), data.decode())

    def test_one_open_no_descriptor_status_and_always_closed(self):
        (self.root / 'stat').write_text('7 (x) S 1 ' + '0 ' * 20)
        opened, closed = [], []
        real_open, real_close = os.open, os.close
        with mock.patch.object(os, 'open', side_effect=lambda *a, **k: opened.append(a) or real_open(*a, **k)), \
                mock.patch.object(os, 'close', side_effect=lambda fd: closed.append(fd) or real_close(fd)), \
                mock.patch.object(os, 'fstat', side_effect=AssertionError('descriptor status asked')), \
                mock.patch.object(os, 'stat', side_effect=AssertionError('path status asked')):
            diagnostic.read_proc_text(self.root / 'stat')
            self.assertEqual((len(opened), len(closed)), (1, 1))
            self.assertTrue(opened[0][1] & os.O_CLOEXEC)
            with mock.patch.object(os, 'read', side_effect=ProcessLookupError(3, 'gone')):
                with self.assertRaises(ProcessLookupError):       # a task that exited after the open
                    diagnostic.read_proc_text(self.root / 'stat')
            self.assertEqual((len(opened), len(closed)), (2, 2))

    def test_errors_are_the_ones_the_callers_already_handle(self):
        with self.assertRaises(FileNotFoundError):
            diagnostic.read_proc_text(self.root / 'absent')
        (self.root / 'odd').write_bytes(b'Name:\t\xff\xfe\n')
        with self.assertRaises(ValueError):
            diagnostic.read_proc_text(self.root / 'odd')
        with self.assertRaises(OSError):
            diagnostic.read_proc_text(self.root)

    def test_status_and_stat_use_it_and_parse_as_before(self):
        process = self.root / '42'
        process.mkdir()
        (process / 'status').write_text('Name:\twine\nTgid:\t42\nPid:\t42\nUid:\t10123\t10123\t10123\t10123\nNSpid:\t42\t7\n')
        (process / 'stat').write_text('42 (wine (x) y) S 1 ' + ' '.join(str(n) for n in range(4, 30)) + '\n')
        self.assertEqual(diagnostic.WineProcessOwner.status(process),
                         {'uid': 10123, 'pid': 42, 'tgid': 42, 'namespace_pids': [42, 7]})
        self.assertEqual(diagnostic.WineProcessOwner.process_stat(process),
                         {'pid': 42, 'state': 'S', 'parent': 1, 'starttime': 21})
        source = (ROOT / 'android/guest/diagnostic.py').read_text()
        self.assertIn('lines = read_proc_text(path / "status").splitlines()', source)
        self.assertIn('value = read_proc_text(path / "stat")', source)


if __name__ == '__main__':
    unittest.main()
