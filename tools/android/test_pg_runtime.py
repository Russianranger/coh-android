#!/usr/bin/env python3
"""Portable contract tests; the ARM64 container also runs the real PG tools."""
import copy
import hashlib
import io
import json
from pathlib import Path
import struct
import tarfile
import tempfile
import unittest

import build_pg_runtime as build
import prepare_pg_runtime as prepare


def arm64_elf():
    data = bytearray(64)
    data[:6] = b'\x7fELF\x02\x01'
    struct.pack_into('<H', data, 18, 183)
    return bytes(data)


class RuntimePackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.prefix = self.root / 'pgsql'
        (self.prefix / 'bin').mkdir(parents=True)
        for name in build.REQUIRED_BINS:
            path = self.prefix / 'bin' / name
            path.write_bytes(arm64_elf())
            path.chmod(0o755)
        (self.prefix / 'share').mkdir()
        (self.prefix / 'share' / 'config.sample').write_text('shared_memory_type = mmap\n')

    def package(self):
        files = build.collect_files(self.prefix)
        archive = self.root / 'pg.tar.gz'
        build.write_overlay(archive, files)
        receipt = {'archive': {'sha256': build.digest(archive), 'bytes': archive.stat().st_size},
                   'files': {name: item[0] for name, item in files.items()}}
        return archive, receipt

    def test_roundtrip_and_deterministic_regular_file_archive(self):
        archive, receipt = self.package()
        build.verify_overlay(archive, receipt)
        second = self.root / 'second.tar.gz'
        build.write_overlay(second, build.collect_files(self.prefix))
        self.assertEqual(archive.read_bytes(), second.read_bytes())
        with tarfile.open(archive) as opened:
            self.assertTrue(all(m.isfile() and m.mtime == 0 and m.uid == 1000 for m in opened))

    def test_internal_symlink_is_materialized(self):
        (self.prefix / 'bin' / 'postgres-alias').symlink_to('postgres')
        archive, receipt = self.package()
        build.verify_overlay(archive, receipt)
        self.assertEqual(receipt['files']['opt/coh/pgsql/bin/postgres-alias'], receipt['files']['opt/coh/pgsql/bin/postgres'])

    def test_external_symlink_fails(self):
        outside = self.root / 'outside'
        outside.write_text('outside')
        (self.prefix / 'bin' / 'bad').symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'escapes'):
            build.collect_files(self.prefix)

    def test_wrong_elf_architecture_fails(self):
        data = bytearray(arm64_elf())
        struct.pack_into('<H', data, 18, 62)
        (self.prefix / 'bin' / 'postgres').write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'AArch64'):
            build.collect_files(self.prefix)

    def test_missing_required_executable_fails(self):
        (self.prefix / 'bin' / 'initdb').unlink()
        with self.assertRaises(KeyError):
            self.package()

    def test_hash_corruption_fails(self):
        archive, receipt = self.package()
        archive.write_bytes(archive.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'hash/size'):
            build.verify_overlay(archive, receipt)

    def test_inventory_hash_cannot_lie(self):
        archive, receipt = self.package()
        receipt['files']['opt/coh/pgsql/bin/psql']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'member hash'):
            build.verify_overlay(archive, receipt)

    def test_inventory_cannot_omit_member(self):
        archive, receipt = self.package()
        del receipt['files']['opt/coh/pgsql/bin/psql']
        with self.assertRaisesRegex(ValueError, 'member metadata'):
            build.verify_overlay(archive, receipt)

    def test_traversal_and_special_members_rejected(self):
        for name, kind in [('opt/coh/pgsql/../../escape', tarfile.REGTYPE), ('opt/coh/pgsql/link', tarfile.SYMTYPE), ('/opt/coh/pgsql/absolute', tarfile.REGTYPE)]:
            with self.subTest(name=name):
                archive = self.root / 'bad.tar.gz'
                with tarfile.open(archive, 'w:gz') as opened:
                    member = tarfile.TarInfo(name)
                    member.type = kind
                    member.linkname = '/outside' if kind == tarfile.SYMTYPE else ''
                    opened.addfile(member)
                receipt = {'archive': {'sha256': build.digest(archive), 'bytes': archive.stat().st_size}, 'files': {}}
                with self.assertRaisesRegex(ValueError, 'unsafe'):
                    build.verify_overlay(archive, receipt)


class InputTests(unittest.TestCase):
    def test_lock_has_official_source_and_immutable_image(self):
        lock = prepare.load_lock(prepare.HERE / 'postgresql-lock.json')
        self.assertEqual(lock['version'], '18.6')
        self.assertEqual(lock['configure_environment']['USE_UNNAMED_POSIX_SEMAPHORES'], '1')
        self.assertEqual(lock['prefix'], '/opt/coh/pgsql')

    def test_mutable_image_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = json.loads((prepare.HERE / 'postgresql-lock.json').read_text())
            lock['builder_image'] = 'debian:bookworm-slim'
            path = Path(directory) / 'lock.json'
            path.write_text(json.dumps(lock))
            with self.assertRaisesRegex(ValueError, 'build lock'):
                prepare.load_lock(path)

    def test_source_hash_and_safe_extraction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.tar.bz2'
            with tarfile.open(source, 'w:bz2') as opened:
                member = tarfile.TarInfo('postgresql-18.6/COPYRIGHT')
                member.size = 7
                opened.addfile(member, io.BytesIO(b'license'))
            lock = {'source': {'sha256': build.digest(source), 'bytes': source.stat().st_size}}
            build.check_source(source, lock)
            extracted = build.extract_source(source, root / 'safe', '18.6')
            self.assertEqual((extracted / 'COPYRIGHT').read_text(), 'license')
            lock['source']['sha256'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'size/hash'):
                build.check_source(source, lock)

    def test_source_escape_rejected_before_extracting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.tar.bz2'
            with tarfile.open(source, 'w:bz2') as opened:
                member = tarfile.TarInfo('postgresql-18.6/../../escape')
                member.size = 1
                opened.addfile(member, io.BytesIO(b'x'))
            with self.assertRaisesRegex(ValueError, 'escapes'):
                build.extract_source(source, root / 'out', '18.6')
            self.assertFalse((root / 'out').exists())


if __name__ == '__main__':
    unittest.main()
