"""Hostile server cache envelopes and missing-only private installation checks.

Synthetic native receipts are test fixtures, never generation evidence.
"""
import copy
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import server_cache_package as package


def pascal(data):
    value = struct.pack('<H', len(data)) + data
    return value + b'\0' * (-len(value) % 4)


def parse6(dependencies=((b'defs/powers/test.powers', package.EPOCH),), body=b'\0' * 4):
    records = struct.pack('<I', len(dependencies))
    for name, timestamp in dependencies:
        records += pascal(name) + struct.pack('<I', timestamp)
    return (b'CrypticS' + struct.pack('<I', 0x12345678) + pascal(b'Parse6') + pascal(b'Files1')
            + struct.pack('<I', len(records)) + records + struct.pack('<I', len(body)) + body)


def message_store():
    return (struct.pack('<I', 20090521) + struct.pack('<II', 1, 5) + b'text\0'
            + struct.pack('<II', 0, 0) + struct.pack('<I', 1)
            + struct.pack('<I', 2) + b'ID' + struct.pack('<III', 0, 0, 0))


def synthetic_archive(path, identity=None, mutate=None):
    """Public fixture helper for cross-feature installer integration tests."""
    identity = identity or {**package.compatibility_identity(), 'identifier_files': {
        'data/server/db/templates/vars.attribute': package.pin_bytes(b'accepted identifiers\n')}}
    payloads = {name: parse6() for name in package.REQUIRED_PARSE6}
    payloads.update({name: message_store() for name in package.REQUIRED_MESSAGES})
    files = {name: {**package.pin_bytes(data), 'kind': ('Parse6' if name in package.REQUIRED_PARSE6
             else 'MessageStore20090521'), 'structure': package.inspect_payload(data,
             'Parse6' if name in package.REQUIRED_PARSE6 else 'MessageStore20090521')}
             for name, data in payloads.items()}
    def native(stage):
        value = {'format': 1, 'stage': stage, 'session_id': '1' * 32, 'mapserver_pid': 1234,
                 'mapserver_sha256': package.MAPSERVER_SHA256, 'native_exit_code': 0,
                 'launcher_exit_code': 0, 'completed_preload': True, 'console_owned': True,
                 'escape_sent': True, 'identifier_files_unchanged': True, 'timed_out': False,
                 'native_errors': {'status': 'no_native_data_errors'}}
        if stage == 'consumption':
            value.update(cache_writes=[], source_content_reads=[], cache_files_unchanged=True,
                         cache_content_reads={name: len(data) for name, data in payloads.items()},
                         trace_receipt_sha256='2' * 64)
        return value
    manifest = {'format': 1, 'role': package.ROLE, 'repository_commit': '3' * 40,
                'identity': identity, 'files': files, 'native_generation': native('generation'),
                'native_consumption': native('consumption'), 'native_client_or_server_recompiled': False,
                'generated_noncache_outputs': [], 'android_execution_validated': False,
                'physical_gameplay_validated': False}
    if mutate:
        mutate(manifest, payloads)
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(package.MANIFEST, package.canonical(manifest))
        for name, data in payloads.items():
            archive.writestr(name, data)
    return manifest


class ServerCachePackageTests(unittest.TestCase):
    def test_binary_signature_crc_dependencies_and_body_bounds(self):
        result = package.inspect_parse6(parse6())
        self.assertEqual(result['schema_crc'], '12345678')
        self.assertEqual(result['dependency_count'], 1)
        self.assertEqual(result['body_bytes'], 4)

    def test_every_truncated_parse6_prefix_rejected(self):
        data = parse6()
        for end in range(len(data)):
            with self.subTest(end=end), self.assertRaises((ValueError, UnicodeError, struct.error)):
                package.inspect_parse6(data[:end])

    def test_unsafe_duplicate_and_unnormalized_dependencies_rejected(self):
        for entries in (((b'../bad', package.EPOCH),), ((b'/bad', package.EPOCH),),
                        ((b'Z:bad', package.EPOCH),), ((b'good', 123),),
                        ((b'good', package.EPOCH), (b'GOOD', package.EPOCH))):
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                package.inspect_parse6(parse6(entries))

    def test_manifest_requires_complete_coverage_and_native_receipts(self):
        mutations = [lambda m, p: m.update(role='actual_client_generated_caches'),
                     lambda m, p: m['identity'].update(mapserver_sha256='0' * 64),
                     lambda m, p: m['native_consumption'].update(source_content_reads=['reparsed.powers']),
                     lambda m, p: m['native_generation'].update(timed_out=True),
                     lambda m, p: m['native_consumption']['cache_content_reads'].pop(next(iter(m['files']))),
                     lambda m, p: m['files'].pop(next(iter(m['files'])))]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / package.ARCHIVE
            for mutate in mutations:
                with self.subTest(mutate=mutate):
                    synthetic_archive(path, mutate=mutate)
                    with self.assertRaises(ValueError):
                        package.verify_archive(path)

    def test_payload_hash_and_kind_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / package.ARCHIVE
            synthetic_archive(path, mutate=lambda m, p: m['files'][next(iter(m['files']))].update(sha256='0'*64))
            with self.assertRaises(ValueError):
                package.verify_archive(path)

    def test_duplicate_archive_names_and_schema_payload_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / package.ARCHIVE
            synthetic_archive(path)
            with zipfile.ZipFile(path, 'a') as archive:
                archive.writestr('data/server/db/templates/vars.attribute', b'never replace IDs')
            with self.assertRaises(ValueError):
                package.verify_archive(path)

    def test_missing_only_installation_preserves_generated_bin_and_identifiers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / 'data'; data.mkdir()
            identifiers = data / 'server/db/templates/vars.attribute'
            identifiers.parent.mkdir(parents=True); identifiers.write_bytes(b'accepted identifiers\n')
            identity = {**package.compatibility_identity(), 'identifier_files': package.identifier_snapshot(data)}
            archive = root / package.ARCHIVE; synthetic_archive(archive, identity)
            generated = data / 'server/bin/powers.bin'; generated.parent.mkdir(); generated.write_bytes(b'device-generated')
            before = package.file_pin(identifiers)
            result = package.install(archive, data, identity)
            self.assertEqual(result['installed_files'], 10)
            self.assertEqual(result['preserved_existing_files'], 1)
            self.assertEqual(generated.read_bytes(), b'device-generated')
            self.assertEqual(package.file_pin(identifiers), before)
            for path in generated.parent.iterdir():
                self.assertEqual(path.lstat().st_nlink, 1)
            self.assertEqual(package.install(archive, data, identity)['installed_files'], 0)

    def test_invalid_identity_falls_back_before_any_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); data = root / 'data'; data.mkdir()
            path = root / package.ARCHIVE; manifest = synthetic_archive(path)
            different = copy.deepcopy(manifest['identity']); different['identifier_files'] = {}
            result = package.install(path, data, different)
            self.assertEqual(result['status'], 'skipped_native_fallback')
            self.assertEqual(list(data.iterdir()), [])

    def test_symlink_ancestor_falls_back_without_external_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); data = root/'data'; data.mkdir(); outside = root/'outside'; outside.mkdir()
            (data/'server').symlink_to(outside, target_is_directory=True)
            path = root/package.ARCHIVE; manifest = synthetic_archive(path)
            result = package.install(path, data, manifest['identity'])
            self.assertEqual(result['status'], 'skipped_native_fallback')
            self.assertEqual(list(outside.iterdir()), [])

    def test_atomic_publisher_does_not_replace_a_concurrent_native_cache(self):
        import client_startup_diagnostic as client
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); temporary = root/'pending'; target = root/'powers.bin'
            temporary.write_bytes(b'donor'); target.write_bytes(b'generated')
            with self.assertRaises(FileExistsError):
                client.publish_new_regular_file(temporary, target)
            self.assertEqual(target.read_bytes(), b'generated')
            self.assertEqual(target.lstat().st_nlink, 1)


if __name__ == '__main__':
    unittest.main()
