#!/usr/bin/env python3
"""Exercise the APK tar extractor; --extract ARCHIVE EMPTY_DEST installs CI inputs.

Example: python3 tools/android/test_archive.py --extract rootfs.tar.gz out/rootfs
Repeat --extract to unpack multiple exact pinned runtime archives into fresh roots.
"""
import argparse
import gzip
import io
import os
from pathlib import Path
import stat
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HOST = Path(__file__).resolve().parent / 'java'
CLASS = 'io.github.russianranger.cohdiagnostic.ExtractRuntimeHost'
SOURCE = ROOT / 'android/app/src/main/java/io/github/russianranger/cohdiagnostic/TarExtractor.java'


def compile_extractor(classes):
    classes = Path(classes)
    classes.mkdir(parents=True, exist_ok=True)
    subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                    '-d', str(classes), str(SOURCE), *map(str, sorted(HOST.rglob('*.java')))], check=True)


def extract_archive(classes, archive, destination, cancel_after=None):
    command = ['java', '-cp', str(classes), CLASS, str(archive), str(destination)]
    if cancel_after is not None:
        command.append(str(cancel_after))
    return subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)


def member(name, data=b'payload', kind=tarfile.REGTYPE, target='', mode=0o644):
    entry = tarfile.TarInfo(name)
    entry.type, entry.linkname, entry.mode = kind, target, mode
    entry.size = len(data) if kind == tarfile.REGTYPE else 0
    return entry, data


def archive_bytes(entries, format=tarfile.PAX_FORMAT):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode='w', format=format) as archive:
        for entry, data in entries:
            archive.addfile(entry, io.BytesIO(data) if entry.isreg() else None)
    return output.getvalue()


class ArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = tempfile.TemporaryDirectory(prefix='coh-extractor-classes-')
        cls.classes = Path(cls.build.name)
        compile_extractor(cls.classes)

    @classmethod
    def tearDownClass(cls):
        cls.build.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='coh-extractor-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.archive = self.base/'runtime.tar.gz'
        self.destination = self.base/'stage'

    def run_archive(self, data, *, compressed=False, success=True, cancel_after=None):
        self.archive.write_bytes(data if compressed else gzip.compress(data))
        result = extract_archive(self.classes, self.archive, self.destination, cancel_after)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('COH_RUNTIME_EXTRACT_V1 PASS', result.stdout)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertNotIn('COH_RUNTIME_EXTRACT_V1 PASS', result.stdout)
        return result

    def test_ustar_directories_payload_and_modes(self):
        data = archive_bytes([member('.', kind=tarfile.DIRTYPE),
                              member('bin', kind=tarfile.DIRTYPE),
                              member('bin/probe', b'\x00ELF fixture', mode=0o755),
                              member('data', b'hello')], format=tarfile.USTAR_FORMAT)
        self.run_archive(data)
        self.assertEqual((self.destination/'bin/probe').read_bytes(), b'\x00ELF fixture')
        self.assertEqual(stat.S_IMODE((self.destination/'bin/probe').stat().st_mode), 0o755)
        self.assertEqual(stat.S_IMODE((self.destination/'data').stat().st_mode), 0o644)

    def test_gnu_long_name_and_long_guest_symlink(self):
        name = 'prefix/' + 'a'*120
        target = '/usr/lib/' + 'b'*120
        self.run_archive(archive_bytes([member(name, b'long'), member('link', kind=tarfile.SYMTYPE,
                                                                      target=target)], format=tarfile.GNU_FORMAT))
        self.assertEqual((self.destination/name).read_bytes(), b'long')
        self.assertEqual(os.readlink(self.destination/'link'), target)

    def test_pax_unicode_and_size_override(self):
        entry, payload = member('placeholder', b'pax payload')
        entry.pax_headers = {'path': 'usr/share/'+'日本語'*20, 'size': str(len(payload)), 'mtime': '1.5'}
        self.run_archive(archive_bytes([(entry, payload)]))
        self.assertEqual((self.destination/entry.pax_headers['path']).read_bytes(), payload)

    def test_forward_hardlink_is_independent_copy(self):
        self.run_archive(archive_bytes([member('copy', kind=tarfile.LNKTYPE, target='original'),
                                       member('original', b'shared bytes', mode=0o755)]))
        original, copy = self.destination/'original', self.destination/'copy'
        self.assertEqual(copy.read_bytes(), original.read_bytes())
        self.assertFalse(os.path.samefile(original, copy))
        self.assertEqual(stat.S_IMODE(copy.stat().st_mode), 0o755)
        copy.write_bytes(b'changed')
        self.assertEqual(original.read_bytes(), b'shared bytes')

    def test_rejects_regular_and_pax_traversal(self):
        for index, name in enumerate(['../outside', '/absolute', 'one/../../outside', 'one\\outside']):
            for pax in [False, True]:
                with self.subTest(name=name, pax=pax):
                    self.destination = self.base/f'stage-{index}-{pax}'
                    entry, payload = member('safe' if pax else name)
                    if pax:
                        entry.pax_headers = {'path': name}
                    self.run_archive(archive_bytes([(entry, payload)]), success=False)
        self.assertFalse((self.base/'outside').exists())

    def test_rejects_nonempty_staging_without_modifying_contents(self):
        self.destination.mkdir()
        sentinel = self.destination/'sentinel'
        sentinel.write_bytes(b'keep')
        result = self.run_archive(archive_bytes([member('sentinel', b'overwrite')]), success=False)
        self.assertIn('empty staging', result.stderr)
        self.assertEqual(sentinel.read_bytes(), b'keep')

    def test_rejects_symlink_staging_ancestor(self):
        outside = self.base/'outside'
        outside.mkdir()
        (self.base/'alias').symlink_to(outside, target_is_directory=True)
        self.destination = self.base/'alias/stage'
        self.run_archive(archive_bytes([member('escaped')]), success=False)
        self.assertEqual(list(outside.iterdir()), [])

    def test_rejects_archive_symlink_ancestor_without_escape(self):
        outside = self.base/'outside'
        outside.mkdir()
        data = archive_bytes([member('escape', kind=tarfile.SYMTYPE, target=str(outside)),
                              member('escape/child', kind=tarfile.SYMTYPE, target='/unused')])
        self.run_archive(data, success=False)
        self.assertEqual(list(outside.iterdir()), [])

    def test_regular_data_cannot_follow_deferred_symlink(self):
        outside = self.base/'outside'
        outside.mkdir()
        data = archive_bytes([member('escape', kind=tarfile.SYMTYPE, target=str(outside)),
                              member('escape/child', b'private')])
        self.run_archive(data, success=False)
        self.assertEqual(list(outside.iterdir()), [])

    def test_rejects_hardlink_escape_and_symlink_source(self):
        outside = self.base/'outside'
        outside.write_bytes(b'keep')
        for index, entries in enumerate([
                [member('copy', kind=tarfile.LNKTYPE, target='../outside')],
                [member('alias', kind=tarfile.SYMTYPE, target=str(outside)),
                 member('copy', kind=tarfile.LNKTYPE, target='alias')]]):
            with self.subTest(index=index):
                self.destination = self.base/f'stage-{index}'
                self.run_archive(archive_bytes(entries), success=False)
        self.assertEqual(outside.read_bytes(), b'keep')

    def test_rejects_duplicate_file(self):
        self.run_archive(archive_bytes([member('same', b'first'), member('same', b'second')]), success=False)
        self.assertEqual((self.destination/'same').read_bytes(), b'first')

    def test_rejects_truncated_payload(self):
        self.run_archive(archive_bytes([member('file', b'x'*700)])[:600], success=False)

    def test_rejects_truncated_pax_record(self):
        header = tarfile.TarInfo('PaxHeader')
        header.type, header.size = tarfile.XHDTYPE, 12
        data = header.tobuf() + b'99 path=x\nxx' + b'\0'*(512-12) + b'\0'*1024
        result = self.run_archive(data, success=False)
        self.assertIn('PAX', result.stderr)

    def test_rejects_pax_header_without_following_member(self):
        entry, payload = member('file')
        entry.pax_headers = {'path': 'destination'}
        data = archive_bytes([(entry, payload)])[:1024] + b'\0'*1024
        self.run_archive(data, success=False)

    def test_rejects_sparse_pax_and_bad_checksum(self):
        entry, payload = member('sparse')
        entry.pax_headers = {'GNU.sparse.size': '50000'}
        self.run_archive(archive_bytes([(entry, payload)]), success=False)
        self.destination = self.base/'checksum-stage'
        bad = bytearray(archive_bytes([member('file')]))
        bad[0] ^= 1
        self.run_archive(bytes(bad), success=False)

    def test_validates_tar_and_gzip_trailers(self):
        raw = archive_bytes([member('file')])
        cases = [raw[:1024]+b'\0'*512, raw+b'not padding']
        for index, data in enumerate(cases):
            self.destination = self.base/f'trailer-{index}'
            self.run_archive(data, success=False)
        damaged = bytearray(gzip.compress(raw))
        damaged[-8] ^= 1
        self.destination = self.base/'gzip-crc'
        self.run_archive(bytes(damaged), compressed=True, success=False)

    def test_cancellation_before_start_and_between_members(self):
        result = self.run_archive(archive_bytes([member('file')]), success=False, cancel_after=0)
        self.assertIn('cancelled', result.stderr)
        self.assertFalse(self.destination.exists())
        self.destination = self.base/'during'
        result = self.run_archive(archive_bytes([member(f'f{i}', b'x') for i in range(501)]),
                                  success=False, cancel_after=500)
        self.assertIn('cancelled', result.stderr)
        self.assertFalse((self.destination/'f500').exists())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extract', nargs=2, action='append', metavar=('ARCHIVE', 'EMPTY_DEST'))
    parser.add_argument('--classes', type=Path, help='Keep compiled host classes at this location')
    args, rest = parser.parse_known_args()
    if not args.extract:
        unittest.main(argv=[__file__, *rest])
        return
    if rest:
        parser.error('unrecognized arguments: ' + ' '.join(rest))
    with tempfile.TemporaryDirectory(prefix='coh-extractor-cli-') as temporary:
        classes = args.classes or Path(temporary)
        compile_extractor(classes)
        for archive, destination in args.extract:
            result = extract_archive(classes, archive, destination)
            if result.returncode:
                raise SystemExit(result.stderr)
            print(result.stdout.strip(), str(Path(archive)), str(Path(destination)))


if __name__ == '__main__':
    main()
