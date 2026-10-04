"""Real extractor fixtures test the runtime archive qualification verifier."""
import io
import os
from pathlib import Path
import stat
import subprocess
import tarfile
import tempfile
import unittest

import qualify_runtime_timestamps as qualify


class RuntimeTimestampTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = tempfile.TemporaryDirectory(prefix='coh-real-runtime-qualifier-')
        cls.classes = Path(cls.build.name)
        subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                        '-d', str(cls.classes), str(qualify.ROOT/qualify.EXTRACTOR),
                        *(str(qualify.ROOT/name) for name in qualify.HOST_SOURCES)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.build.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='coh-runtime-qualified-fixture-')
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.archive = self.work/'fixture.tar.gz'
        self.root = self.work/'root'
        with tarfile.open(self.archive, 'w:gz', format=tarfile.PAX_FORMAT) as archive:
            for name, kind, stamp, data, target in (
                ('.', tarfile.DIRTYPE, 100, b'', ''),
                ('bin', tarfile.DIRTYPE, 200, b'', ''),
                ('bin/probe', tarfile.REGTYPE, 300, b'\x00ELF exact bytes', ''),
                ('bin/copy', tarfile.LNKTYPE, 400, b'', 'bin/probe'),
                ('guest-link', tarfile.SYMTYPE, 500, b'', '/guest/absolute'),
                ('bin', tarfile.DIRTYPE, 600, b'', ''),
            ):
                entry = tarfile.TarInfo(name)
                entry.type, entry.mtime, entry.size = kind, stamp, len(data)
                entry.mode, entry.linkname = 0o755, target
                archive.addfile(entry, io.BytesIO(data) if data else None)
        qualify.extract(self.classes, self.archive, self.root)

    def test_real_java_fixture_verifies_bytes_modes_deferred_directory_and_hardlink_dates(self):
        receipt, files = qualify.verify_extracted(self.archive, self.root)
        self.assertEqual('passed', receipt['status'])
        self.assertEqual(1, receipt['copied_hardlinks'])
        self.assertEqual(1, receipt['symlinks'])
        self.assertEqual(600000000000, (self.root/'bin').stat().st_mtime_ns)
        self.assertEqual(400000000000, files['bin/copy']['mtime_ns'])
        self.assertFalse(os.path.samefile(self.root/'bin/probe', self.root/'bin/copy'))
        self.assertEqual('/guest/absolute', os.readlink(self.root/'guest-link'))

    def test_changed_payload_is_rejected(self):
        (self.root/'bin/probe').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'payload bytes differ'):
            qualify.verify_extracted(self.archive, self.root)

    def test_changed_normalized_mode_is_rejected(self):
        (self.root/'bin/probe').chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'normalized mode differs'):
            qualify.verify_extracted(self.archive, self.root)

    def test_changed_leaf_or_directory_date_is_rejected(self):
        os.utime(self.root/'bin/copy', ns=(0, 401000000000))
        with self.assertRaisesRegex(ValueError, 'archive date differs'):
            qualify.verify_extracted(self.archive, self.root)
        os.utime(self.root/'bin/copy', ns=(0, 400000000000))
        os.utime(self.root/'bin', ns=(0, 601000000000))
        with self.assertRaisesRegex(ValueError, 'directory date differs'):
            qualify.verify_extracted(self.archive, self.root)

    def test_unknown_output_cannot_pass_inventory_verification(self):
        # Add a leaf without modifying an explicit parent date.
        (self.root/'unexpected').write_bytes(b'unknown')
        os.utime(self.root, ns=(0, 100000000000))
        with self.assertRaisesRegex(ValueError, 'Unexpected or absent'):
            qualify.verify_extracted(self.archive, self.root)

    def test_linked_payload_is_rejected_without_reading_external_target(self):
        target = self.work/'external'
        target.write_bytes(b'\x00ELF exact bytes')
        target.chmod(0o755)
        before = target.stat()
        (self.root/'bin/probe').unlink()
        (self.root/'bin/probe').symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'independent regular file'):
            qualify.verify_extracted(self.archive, self.root)
        self.assertEqual(before.st_mtime_ns, target.stat().st_mtime_ns)
        self.assertEqual(stat.S_IMODE(before.st_mode), stat.S_IMODE(target.stat().st_mode))

    def test_archive_decimal_precision_is_floored_without_rounding_to_a_later_nanosecond(self):
        entry = tarfile.TarInfo('tiny-fraction')
        entry.pax_headers = {'mtime': '2.123456789999999999999999999999999999999999'}
        self.assertEqual(2123456789, qualify.archive_time(entry))
        for value in ('-0.1', '1e3', '9223372036.854775808'):
            entry.pax_headers = {'mtime': value}
            with self.subTest(value=value), self.assertRaises(ValueError):
                qualify.archive_time(entry)


if __name__ == '__main__':
    unittest.main()
