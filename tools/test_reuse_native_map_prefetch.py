#!/usr/bin/env python3
"""Exact candidate provenance/admission tests; these never execute native code.

Pure tests always run. Supplying --package and --baseline adds mandatory tests
against the completed artifact bytes, without downloading or rebuilding them.
"""
from __future__ import annotations

import argparse
import copy
import os
from pathlib import Path
import shutil
import stat
import struct
import sys
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reuse_native_map_prefetch as reuse

EXPECTED_SOURCE = '47e40d4d586d29e273e31ed4d0d51d160832b89d'
EXPECTED_RUN = 38350813669
EXPECTED_JOB = 115142552789
EXPECTED_ARTIFACT = 11790609618
EXPECTED_ZIP = {'bytes': 3307410,
                'sha256': '69bfc9f44e5304eae786d0668ba30f183f5b99a58586f8db7861f697d8e23aab'}
EXPECTED_FILES = {
    'native-map-prefetch-checks.json': {
        'bytes': 5053, 'sha256': '56555e6e89b1adbae2ec24d02d3b1511b93e71ede45af361afc446b147547c02'},
    'native-map-prefetch-package.json': {
        'bytes': 12283, 'sha256': '877207e8889a4e5c97e39aa8fb87f113592f062eb74b89d7a41a82faf1e6cafe'},
    'native-map-prefetch-fixture.exe': {
        'bytes': 152576, 'sha256': 'ac723e27bafd46e1c21ecaf62556079d32a84d5745058c9d4e380c57d9393a5d'},
    'MapServer-prefetch.exe': {
        'bytes': 7480832, 'sha256': '5927f87fdac50c5a839ac067ccbb34b5dfad6223e579287a66a2f866a7d4b2e6'},
}


def metadata():
    """Independent API-shaped controls; not a fetched producer receipt."""
    return ({'id': EXPECTED_RUN, 'head_sha': EXPECTED_SOURCE,
             'status': 'completed', 'conclusion': 'success',
             'head_branch': 'codex/native-map-prefetch-036',
             'path': '.github/workflows/android-native-map-prefetch.yml'},
            {'jobs': [{'id': EXPECTED_JOB, 'run_id': EXPECTED_RUN,
                       'name': 'native-candidate', 'status': 'completed', 'conclusion': 'success'}]},
            {'id': EXPECTED_ARTIFACT, 'name': 'coh-nonshipping-map-metadata-prefetch',
             'size_in_bytes': EXPECTED_ZIP['bytes'], 'digest': 'sha256:'+EXPECTED_ZIP['sha256'],
             'expired': False, 'workflow_run': {'id': EXPECTED_RUN, 'head_sha': EXPECTED_SOURCE}})


class MetadataTests(unittest.TestCase):
    def test_one_completed_producer_and_exact_four_members_are_pinned(self):
        self.assertEqual((reuse.SOURCE, reuse.RUN, reuse.JOB, reuse.ARTIFACT),
                         (EXPECTED_SOURCE, EXPECTED_RUN, EXPECTED_JOB, EXPECTED_ARTIFACT))
        self.assertEqual(reuse.ZIP, EXPECTED_ZIP)
        self.assertEqual(reuse.FILES, EXPECTED_FILES)

    def test_exact_metadata_retains_build_scope_without_claiming_runtime(self):
        values = metadata()
        original = copy.deepcopy(values)
        result = reuse.validate_metadata(*values)
        self.assertEqual(result, reuse.provenance())
        self.assertEqual(values, original)
        self.assertIs(result['actual_native_build_and_Win32_fixture_passed'], True)
        for key in ('native_binaries_rebuilt', 'native_world_or_Wine_preload_claimed', 'publication_allowed'):
            self.assertIs(result[key], False)

    def test_wrong_or_missing_run_metadata_is_rejected(self):
        mutations = {'id': [EXPECTED_RUN+1, str(EXPECTED_RUN)],
                     'head_sha': ['0'*40, EXPECTED_SOURCE.upper()],
                     'head_branch': ['main', 'codex/native-startup-profile-036'],
                     'path': ['.github/workflows/android-native-startup-profile.yml'],
                     'status': ['in_progress', 'queued'],
                     'conclusion': ['failure', 'cancelled', 'skipped', None]}
        for key, replacements in mutations.items():
            for replacement in replacements+[None]:
                values = metadata()
                if replacement is None:
                    values[0].pop(key)
                else:
                    values[0][key] = replacement
                with self.subTest(key=key, replacement=replacement), self.assertRaises(ValueError):
                    reuse.validate_metadata(*values)

    def test_wrong_or_missing_job_metadata_is_rejected(self):
        mutations = {'id': [EXPECTED_JOB+1], 'run_id': [EXPECTED_RUN+1],
                     'name': ['native', 'native-candidate-extra'],
                     'status': ['in_progress'], 'conclusion': ['failure', 'cancelled', 'skipped']}
        for key, replacements in mutations.items():
            for replacement in replacements+[None]:
                values = metadata()
                job = values[1]['jobs'][0]
                if replacement is None:
                    job.pop(key)
                else:
                    job[key] = replacement
                with self.subTest(key=key, replacement=replacement), self.assertRaises(ValueError):
                    reuse.validate_metadata(*values)

    def test_missing_or_duplicate_exact_job_is_rejected(self):
        for count in (0, 2):
            values = metadata()
            values[1]['jobs'] *= count
            with self.subTest(count=count), self.assertRaises(ValueError):
                reuse.validate_metadata(*values)

    def test_unrelated_job_does_not_replace_exact_successful_candidate(self):
        values = metadata()
        values[1]['jobs'].append({'id': 1, 'name': 'unrelated', 'conclusion': 'failure'})
        self.assertEqual(reuse.validate_metadata(*values)['job_id'], EXPECTED_JOB)

    def test_wrong_or_missing_artifact_metadata_is_rejected(self):
        mutations = {'id': [EXPECTED_ARTIFACT+1, str(EXPECTED_ARTIFACT)],
                     'name': ['coh-nonshipping-native-startup-profile'],
                     'size_in_bytes': [EXPECTED_ZIP['bytes']-1, str(EXPECTED_ZIP['bytes'])],
                     'digest': ['sha256:'+'0'*64, EXPECTED_ZIP['sha256'],
                                'sha256:'+EXPECTED_ZIP['sha256'].upper()],
                     'expired': [True, 0, 'false']}
        for key, replacements in mutations.items():
            for replacement in replacements+[None]:
                values = metadata()
                if replacement is None:
                    values[2].pop(key)
                else:
                    values[2][key] = replacement
                with self.subTest(key=key, replacement=replacement), self.assertRaises(ValueError):
                    reuse.validate_metadata(*values)
        for key, replacement in (('id', EXPECTED_RUN+1), ('head_sha', '0'*40)):
            for missing in (False, True):
                values = metadata()
                if missing:
                    values[2]['workflow_run'].pop(key)
                else:
                    values[2]['workflow_run'][key] = replacement
                with self.subTest(workflow_key=key, missing=missing), self.assertRaises(ValueError):
                    reuse.validate_metadata(*values)

    def test_numeric_identity_fields_require_json_integers(self):
        for field in ('run', 'job', 'job_run', 'artifact', 'artifact_run', 'zip_size'):
            values = metadata()
            mapping, key = {
                'run': (values[0], 'id'), 'job': (values[1]['jobs'][0], 'id'),
                'job_run': (values[1]['jobs'][0], 'run_id'), 'artifact': (values[2], 'id'),
                'artifact_run': (values[2]['workflow_run'], 'id'),
                'zip_size': (values[2], 'size_in_bytes'),
            }[field]
            mapping[key] = float(mapping[key])
            with self.subTest(field=field), self.assertRaises(ValueError):
                reuse.validate_metadata(*values)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.archive = self.root/'input.zip'
        self.output = self.root/'output'
        self.baseline = self.root/'unused-baseline'

    def write_archive(self, mutation=None):
        names = list(EXPECTED_FILES)
        entries = [(name, EXPECTED_FILES[name]['bytes'], stat.S_IFREG | 0o600) for name in names]
        if mutation == 'missing':
            entries.pop()
        elif mutation == 'extra':
            entries.append(('unexpected', 1, stat.S_IFREG | 0o600))
        elif mutation == 'duplicate':
            entries[-1] = entries[0]
        elif mutation in ('relative', 'absolute', 'windows', 'backslash', 'nested'):
            name = {'relative': '../MapServer-prefetch.exe', 'absolute': '/MapServer-prefetch.exe',
                    'windows': 'C:/MapServer-prefetch.exe', 'backslash': '..\\MapServer-prefetch.exe',
                    'nested': 'nested/MapServer-prefetch.exe'}[mutation]
            entries[-1] = (name, entries[-1][1], entries[-1][2])
        elif mutation == 'case':
            entries[-1] = (names[-1].upper(), entries[-1][1], entries[-1][2])
        elif mutation in ('symlink', 'directory_mode', 'fifo'):
            mode = {'symlink': stat.S_IFLNK, 'directory_mode': stat.S_IFDIR, 'fifo': stat.S_IFIFO}[mutation]
            entries[-1] = (names[-1], entries[-1][1], mode | 0o600)
        elif mutation == 'size':
            entries[-1] = (names[-1], entries[-1][1]+1, entries[-1][2])
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(self.archive, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                for name, size, mode in entries:
                    info = zipfile.ZipInfo(name)
                    info.create_system = 3
                    info.external_attr = mode << 16
                    info.compress_type = zipfile.ZIP_DEFLATED
                    archive.writestr(info, b'x'*size)
        if mutation == 'encrypted':
            raw = bytearray(self.archive.read_bytes())
            central = raw.index(b'PK\x01\x02')
            struct.pack_into('<H', raw, central+8, struct.unpack_from('<H', raw, central+8)[0] | 1)
            self.archive.write_bytes(raw)

    def test_unknown_zip_is_rejected_before_output_creation(self):
        self.archive.write_bytes(b'unrelated archive')
        with self.assertRaises(ValueError):
            reuse.extract(self.archive, self.output, self.baseline)
        self.assertFalse(self.output.exists())

    def test_malformed_zip_is_rejected_after_exact_pin_gate(self):
        self.archive.write_bytes(b'not a ZIP even if its content hash is known')
        with mock.patch.object(reuse, 'ZIP', reuse.base.pin(self.archive)):
            with self.assertRaises((ValueError, zipfile.BadZipFile)):
                reuse.extract(self.archive, self.output, self.baseline)
        self.assertFalse(self.output.exists())

    def test_bad_closure_paths_types_sizes_and_encryption_fail_before_extraction(self):
        for mutation in ('missing', 'extra', 'duplicate', 'relative', 'absolute', 'windows',
                         'backslash', 'nested', 'case', 'symlink', 'directory_mode', 'fifo',
                         'size', 'encrypted'):
            self.write_archive(mutation)
            # Only the outer ZIP identity is changed: member names, types and
            # sizes must still satisfy the real retained-artifact contract.
            with self.subTest(mutation=mutation), mock.patch.object(reuse, 'ZIP', reuse.base.pin(self.archive)):
                with self.assertRaises(ValueError):
                    reuse.extract(self.archive, self.output, self.baseline)
                self.assertFalse(self.output.exists())
            self.assertFalse((self.root/'MapServer-prefetch.exe').exists())

    def test_preexisting_or_symlinked_destination_is_rejected(self):
        self.write_archive()
        with mock.patch.object(reuse, 'ZIP', reuse.base.pin(self.archive)):
            self.output.mkdir()
            marker = self.output/'retained-marker'
            marker.write_bytes(b'unchanged')
            with self.assertRaises(ValueError):
                reuse.extract(self.archive, self.output, self.baseline)
            self.assertEqual(marker.read_bytes(), b'unchanged')
            marker.unlink()
            self.output.rmdir()
            self.output.symlink_to(self.root/'missing-target')
            with self.assertRaises(ValueError):
                reuse.extract(self.archive, self.output, self.baseline)
            self.assertTrue(self.output.is_symlink())

    def test_linked_destination_ancestor_is_rejected_before_writing(self):
        self.write_archive()
        actual = self.root/'actual'
        actual.mkdir()
        alias = self.root/'alias'
        alias.symlink_to(actual, target_is_directory=True)
        with mock.patch.object(reuse, 'ZIP', reuse.base.pin(self.archive)):
            with self.assertRaises(ValueError):
                reuse.extract(self.archive, alias/'output', self.baseline)
        self.assertFalse((actual/'output').exists())

    def test_outer_zip_symlink_is_rejected(self):
        self.write_archive()
        alias = self.root/'archive-link.zip'
        alias.symlink_to(self.archive)
        with mock.patch.object(reuse, 'ZIP', reuse.base.pin(self.archive)):
            with self.assertRaises(ValueError):
                reuse.extract(alias, self.output, self.baseline)
        self.assertFalse(self.output.exists())


def actual_artifact_suite(package, baseline):
    """No skipped cases: explicitly supplied artifact paths must all validate."""
    class ActualArtifactTests(unittest.TestCase):
        def test_original_exact_four_members_and_native_build_receipt_are_accepted(self):
            before = {name: reuse.base.pin(package/name) for name in EXPECTED_FILES}
            self.assertEqual(before, EXPECTED_FILES)
            result = reuse.validate_package(package, baseline)
            self.assertEqual(result['repository_commit'], EXPECTED_SOURCE)
            self.assertEqual(result['binary']['sha256'], EXPECTED_FILES['MapServer-prefetch.exe']['sha256'])
            self.assertIs(result['native_checks']['native_windows_executed'], True)
            self.assertIs(result['native_world_executed'], False)
            self.assertEqual(before, {name: reuse.base.pin(package/name) for name in EXPECTED_FILES})

        def test_one_byte_change_in_each_member_is_rejected(self):
            for name in EXPECTED_FILES:
                with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                    target = Path(temporary)/'package'
                    shutil.copytree(package, target)
                    path = target/name
                    with path.open('r+b') as stream:
                        stream.seek(-1, os.SEEK_END)
                        original = stream.read(1)
                        stream.seek(-1, os.SEEK_END)
                        stream.write(bytes([original[0] ^ 1]))
                    with self.assertRaises(ValueError):
                        reuse.validate_package(target, baseline)

        def test_member_closure_is_exact(self):
            for mutation in ('missing', 'extra', 'renamed'):
                with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                    target = Path(temporary)/'package'
                    shutil.copytree(package, target)
                    member = target/'native-map-prefetch-checks.json'
                    if mutation == 'missing':
                        member.unlink()
                    elif mutation == 'extra':
                        (target/'unexpected.txt').write_bytes(b'extra')
                    else:
                        member.rename(member.with_name(member.name.upper()))
                    with self.assertRaises(ValueError):
                        reuse.validate_package(target, baseline)

        def test_linked_directory_member_or_ancestor_is_rejected(self):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                linked = root/'linked'
                linked.symlink_to(package, target_is_directory=True)
                with self.assertRaises(ValueError):
                    reuse.validate_package(linked, baseline)
                ancestor = root/'ancestor'
                ancestor.symlink_to(package.parent, target_is_directory=True)
                with self.assertRaises(ValueError):
                    reuse.validate_package(ancestor/package.name, baseline)
                target = root/'copied'
                shutil.copytree(package, target)
                member = target/'MapServer-prefetch.exe'
                member.unlink()
                member.symlink_to(package/member.name)
                with self.assertRaises(ValueError):
                    reuse.validate_package(target, baseline)

        def test_wrong_retained_baseline_is_rejected(self):
            with tempfile.TemporaryDirectory() as temporary:
                with self.assertRaises(ValueError):
                    reuse.validate_package(package, Path(temporary))

    return unittest.defaultTestLoader.loadTestsFromTestCase(ActualArtifactTests)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path)
    parser.add_argument('--baseline', type=Path)
    args = parser.parse_args()
    if (args.package is None) != (args.baseline is None):
        parser.error('--package and --baseline must be supplied together')
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    if args.package is not None:
        suite.addTests(actual_artifact_suite(args.package.absolute(), args.baseline.absolute()))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
