import gzip
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import extract_talloc_source as extract


class TallocSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.assets = self.root / 'assets'
        self.assets.mkdir()
        self.bundle = self.root / 'bundle.tar.gz'
        self.output = self.root / 'cache/talloc.tar.gz'
        self.source = b'pinned source archive'

    def inputs(self, members=None, source=None):
        if members is None:
            members = [(extract.MEMBER_NAME, tarfile.REGTYPE, self.source)]
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode='w') as archive:
            for name, kind, content in members:
                member = tarfile.TarInfo(name)
                member.type = kind
                member.size = len(content) if kind == tarfile.REGTYPE else 0
                if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                    member.linkname = 'other'
                archive.addfile(member, io.BytesIO(content))
        self.bundle.write_bytes(gzip.compress(data.getvalue()))
        build = {'schema_version': 1, 'target': 'android-arm64',
                 'source_commit': extract.build_proot.PROOT_COMMIT,
                 'source_tree': extract.build_proot.PROOT_TREE, 'talloc_version': '2.4.3',
                 'corresponding_sources': dict(extract.record(self.bundle.read_bytes()),
                                              file='proot-corresponding-sources.tar.gz'),
                 'sources': {'talloc-2.4.3.tar.gz': extract.record(self.source if source is None else source)}}
        build_data = json.dumps(build).encode()
        (self.assets / 'proot-build.json').write_bytes(build_data)
        manifest = {'format': 1, 'repository_commit': extract.ACCEPTED_RUNTIME_COMMIT,
                    'files': {'proot-build.json': extract.record(build_data)}}
        manifest_data = json.dumps(manifest).encode()
        (self.assets / 'runtime-manifest.json').write_bytes(manifest_data)
        self.enterContext(patch.object(extract, 'ACCEPTED_RUNTIME_MANIFEST', extract.record(manifest_data)['sha256']))
        self.enterContext(patch.object(extract.build_proot, 'TALLOC_SHA256', extract.record(self.source)['sha256']))

    def run_extract(self):
        return extract.extract_source(self.assets, self.bundle, self.output)

    def rejected(self, pattern):
        with self.assertRaisesRegex((ValueError, OSError, tarfile.TarError), pattern):
            self.run_extract()
        self.assertFalse(self.output.exists())

    def test_recovers_only_exact_member_and_receipts_authenticated_bytes(self):
        self.inputs([('../ignored', tarfile.REGTYPE, b'never extracted'),
                     (extract.MEMBER_NAME, tarfile.REGTYPE, self.source)])
        receipt = self.run_extract()
        self.assertEqual(self.output.read_bytes(), self.source)
        self.assertEqual(receipt['member'], dict(extract.record(self.source), name=extract.MEMBER_NAME))
        self.assertEqual(receipt['accepted_runtime_run_id'], 36364550345)
        self.assertFalse(receipt['runtime_execution_validated'])
        self.assertFalse((self.root / 'ignored').exists())
        self.assertEqual(list(self.output.parent.iterdir()), [self.output])

    def test_authentication_chain_rejects_changed_manifest_receipt_or_bundle(self):
        for filename, message in (('runtime-manifest.json', 'accepted.*manifest'),
                                  ('proot-build.json', 'PRoot build receipt'),
                                  ('bundle', 'Corresponding-source bundle')):
            with self.subTest(input=filename):
                self.inputs()
                path = self.bundle if filename == 'bundle' else self.assets / filename
                path.write_bytes(path.read_bytes() + b' ')
                self.rejected(message)

    def test_requires_exact_unique_regular_member(self):
        for members, message in (
            ([('./' + extract.MEMBER_NAME, tarfile.REGTYPE, self.source)], 'missing'),
            ([(extract.MEMBER_NAME, tarfile.SYMTYPE, b'')], 'regular member'),
            ([(extract.MEMBER_NAME, tarfile.LNKTYPE, b'')], 'regular member'),
            ([(extract.MEMBER_NAME, tarfile.DIRTYPE, b'')], 'regular member'),
            ([(extract.MEMBER_NAME, tarfile.REGTYPE, self.source)] * 2, 'Duplicate'),
        ):
            with self.subTest(message=message, members=members):
                self.inputs(members)
                self.rejected(message)

    def test_member_must_match_both_receipt_and_build_recipe_pin(self):
        self.inputs([(extract.MEMBER_NAME, tarfile.REGTYPE, b'changed')])
        self.rejected('Talloc source size/SHA-256')
        self.inputs([(extract.MEMBER_NAME, tarfile.REGTYPE, b'changed')], source=b'changed')
        self.rejected('build recipe SHA-256')

    def test_existing_outputs_and_symlinks_are_preserved(self):
        self.inputs()
        self.output.parent.mkdir()
        self.output.write_bytes(b'existing')
        with self.assertRaisesRegex(ValueError, 'fresh'):
            self.run_extract()
        self.assertEqual(self.output.read_bytes(), b'existing')
        self.output.unlink()
        self.output.symlink_to(self.root / 'absent')
        with self.assertRaisesRegex(ValueError, 'fresh'):
            self.run_extract()
        self.assertTrue(self.output.is_symlink())
        self.assertFalse((self.root / 'absent').exists())

    def test_input_symlink_refused(self):
        self.inputs()
        original = self.bundle.with_name('original')
        self.bundle.rename(original)
        self.bundle.symlink_to(original)
        self.rejected('symlink')

    def test_size_and_member_count_bounds(self):
        for constant, value, message in (
            ('MAX_METADATA_BYTES', 1, 'size bound'),
            ('MAX_SOURCE_BYTES', 1, 'size bound'),
            ('MAX_TAR_BYTES', 1, 'Expanded source bundle'),
            ('MAX_MEMBERS', 0, 'too many members'),
        ):
            with self.subTest(bound=constant):
                self.inputs()
                with patch.object(extract, constant, value):
                    self.rejected(message)

    def test_atomic_publication_refuses_racing_destination_and_removes_temporary(self):
        self.inputs()
        def collision(source, output):
            output.write_bytes(b'other writer')
            raise FileExistsError('already exists')
        with patch.object(extract.os, 'link', side_effect=collision):
            with self.assertRaises(FileExistsError):
                self.run_extract()
        self.assertEqual(self.output.read_bytes(), b'other writer')
        self.assertEqual(list(self.output.parent.iterdir()), [self.output])


if __name__ == '__main__':
    unittest.main()
