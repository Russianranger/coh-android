"""Runtime assembly must reject ambiguous donors and unverifiable executables."""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest

import prepare_runtime as runtime
from package_reference_runtime import DYNAMIC_DLLS, PRODUCTS, pe_info


def digest(data):
    return hashlib.sha256(data).hexdigest()


def minimal_pe():
    # Minimal x86 PE32 with no imports; never executed by these tests.
    data = bytearray(512)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 60, 128)
    data[128:132] = b'PE\0\0'
    struct.pack_into('<HH', data, 132, 332, 0)
    struct.pack_into('<H', data, 148, 96)
    struct.pack_into('<H', data, 152, 0x10b)
    struct.pack_into('<I', data, 152 + 60, len(data))
    return bytes(data)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode())


class RuntimeStagingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'project'
        self.root.mkdir()
        self.source = self.root / 'upstream/source'
        self.content = self.root / 'upstream/content'
        write(self.source / 'Common/sql/sqlconn.c', 'old\n')
        write(self.source / 'data/server/db/shard.cfg', 'source DB config\n')
        write(self.content / 'data/Defs/powers.txt', 'pinned powers\n')
        write(self.content / 'data/server/db/shard.cfg', 'companion DB config\n')
        for name in runtime.LAUNCHERS:
            write(self.content / 'tools' / name, 'Game.exe -example\n')
        (self.root / 'tools').mkdir()
        shutil.copy2(runtime.ROOT / 'tools/verify_source.py', self.root / 'tools/verify_source.py')
        self.source_lock = self.lock_snapshot(self.source, '1' * 40, 'upstream-lock.json')
        self.lock_snapshot(self.content, '2' * 40, 'content-lock.json')
        self.donor1 = self.root / 'donor1'
        self.donor2 = self.root / 'donor2'
        self.donor1.mkdir()
        self.donor2.mkdir()
        self.output = self.root / 'runtime'
        self.before = self.snapshot()

    def snapshot(self):
        return {str(path.relative_to(self.root)): path.read_bytes()
                for path in (self.root / 'upstream').rglob('*') if path.is_file()}

    def lock_snapshot(self, directory, commit, lock_name):
        entries = []
        for path in directory.rglob('*'):
            if not path.is_file():
                continue
            data = path.read_bytes()
            entries.append({'path': path.relative_to(directory).as_posix(), 'size': len(data),
                            'sha256': digest(data), 'mode': '100644',
                            'git_blob': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()})
        manifest_name = lock_name + '.manifest.json'
        lock = {'commit': commit, 'destination': directory.relative_to(self.root).as_posix(),
                'manifest': manifest_name, 'files': len(entries), 'bytes': sum(e['size'] for e in entries)}
        write(self.root / lock_name, json.dumps(lock))
        write(self.root / manifest_name, json.dumps({'commit': commit, 'entries': entries}))
        return lock

    def package(self):
        write(self.root / 'patches/postgresql/0001-dbserver-postgresql.patch',
              'diff --git a/Common/sql/sqlconn.c b/Common/sql/sqlconn.c\n'
              '--- a/Common/sql/sqlconn.c\n+++ b/Common/sql/sqlconn.c\n@@ -1 +1 @@\n-old\n+new\n')
        write(self.root / 'database/postgresql/overlay/DBServer/src/postgresql.c', 'overlay\n')
        receipt = runtime.expected_pg_receipt(self.root, self.source_lock)
        directory = self.root / 'package'
        directory.mkdir()
        records = {}
        for name in PRODUCTS + DYNAMIC_DLLS:
            data = minimal_pe()
            write(directory / name, data)
            records[name] = {'size': len(data), 'sha256': digest(data), **pe_info(data)}
        data = (json.dumps(receipt) + '\n').encode()
        write(directory / 'postgresql-build-input.json', data)
        records['postgresql-build-input.json'] = {'size': len(data), 'sha256': digest(data)}
        manifest = {'schema_version': 1, 'source_commit': self.source_lock['commit'],
                    'repository_commit': '3' * 40, 'configuration': 'OptDebug', 'architecture': 'Win32',
                    'postgresql_persistence_fixture': False, 'postgresql_build_input': receipt, 'files': records}
        write(directory / 'build-info.json', json.dumps(manifest))
        return directory, manifest

    def test_text_only_remains_supported_and_does_not_modify_snapshots(self):
        result = runtime.stage(self.output, root=self.root)
        self.assertFalse(result['executables_supplied'])
        self.assertFalse(result['binary_assets_supplied'])
        self.assertFalse(result['templates_and_bins_generated'])
        self.assertEqual((self.output / 'data/server/db/shard.cfg').read_text(), 'source DB config\n')
        self.assertIn('CityOfHeroes.exe', (self.output / 'tools/map.ps1').read_text())
        self.assertEqual(self.before, self.snapshot())
        self.assertFalse((self.output / '.runtime-staging-incomplete').exists())

    def test_identical_mixed_case_donors_merge_and_share_directory_spelling(self):
        write(self.donor1 / 'Player_Library/male/test.anim', b'animation')
        write(self.donor2 / 'player_library/MALE/TEST.anim', b'animation')
        write(self.donor2 / 'player_library/MALE/other.anim', b'other')
        result = runtime.stage(self.output, (self.donor1, self.donor2), root=self.root)
        self.assertEqual(len(result['binary_asset_files']), 2)
        self.assertEqual(result['asset_donors'][1]['identical_duplicate_files'], 1)
        self.assertEqual(len(list((self.output / 'data/Player_Library/male').iterdir())), 2)
        self.assertFalse((self.output / 'data/player_library').exists())
        self.assertEqual(self.before, self.snapshot())

    def test_differing_casefold_assets_fail_before_output_exists(self):
        write(self.donor1 / 'World/black.texture', b'first')
        write(self.donor2 / 'world/BLACK.texture', b'second')
        with self.assertRaisesRegex(ValueError, 'Conflicting case-insensitive asset'):
            runtime.stage(self.output, (self.donor1, self.donor2), root=self.root)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.before, self.snapshot())
        self.assertEqual((self.donor1 / 'World/black.texture').read_bytes(), b'first')

    def test_donor_cache_and_text_exclusion_are_reported(self):
        write(self.donor1 / 'Defs/POWERS.txt', 'untrusted text')
        write(self.donor1 / 'BIN/powers.bin', b'Parse7')
        write(self.donor1 / 'geobin/hidden.geo', b'old geometry cache')
        write(self.donor1 / 'elsewhere/cache.bin.meta', b'old metadata')
        write(self.donor1 / 'markerfiles/hidden.anim', b'marker data')
        write(self.donor1 / 'texture_library/black.texture', b'asset')
        result = runtime.stage(self.output, (self.donor1,), root=self.root)
        self.assertEqual((self.output / 'data/Defs/powers.txt').read_text(), 'pinned powers\n')
        self.assertEqual(sum(result['asset_donors'][0]['excluded_files'].values()), 5)
        self.assertEqual(len(result['binary_asset_files']), 1)
        self.assertFalse((self.output / 'data/BIN').exists())
        self.assertFalse((self.output / 'data/geobin').exists())
        self.assertEqual(self.before, self.snapshot())

    def test_incomplete_inspection_and_symlinks_fail_closed(self):
        write(self.donor1 / '.inspection-incomplete', 'incomplete')
        with self.assertRaisesRegex(ValueError, 'inspection is incomplete'):
            runtime.asset_plan((self.donor1,))
        (self.donor1 / '.inspection-incomplete').unlink()
        try:
            (self.donor1 / 'data.anim').symlink_to(self.content / 'data/Defs/powers.txt')
        except (OSError, NotImplementedError):
            self.skipTest('Host does not permit symlink creation')
        with self.assertRaisesRegex(ValueError, 'Symlinks'):
            runtime.asset_plan((self.donor1,))
        self.assertFalse(self.output.exists())

    def test_file_directory_collision_fails_before_output(self):
        write(self.donor1 / 'same.anim', b'asset')
        write(self.donor2 / 'SAME.ANIM/other.anim', b'asset')
        with self.assertRaisesRegex(ValueError, 'File/directory conflict'):
            runtime.stage(self.output, (self.donor1, self.donor2), root=self.root)
        self.assertFalse(self.output.exists())

    def test_valid_postgresql_receipt_and_manifest_hashes_survive_staging(self):
        directory, manifest = self.package()
        # Patch line endings are deliberately normalized in its receipt.
        path = self.root / 'patches/postgresql/0001-dbserver-postgresql.patch'
        path.write_bytes(path.read_bytes().replace(b'\n', b'\r\n'))
        result = runtime.stage(self.output, binaries=directory, root=self.root)
        self.assertEqual(result['postgresql_build_input'], manifest['postgresql_build_input'])
        self.assertEqual(result['build_file_sha256']['DbServer.exe'], digest((directory / 'DbServer.exe').read_bytes()))
        self.assertEqual(self.before, self.snapshot())
        self.assertFalse(result['templates_and_bins_generated'])

    def test_receipt_accepts_only_proven_overlay_line_ending_variants(self):
        directory, manifest = self.package()
        overlay_name = 'DBServer/src/postgresql.c'
        data = (self.root / 'database/postgresql/overlay' / overlay_name).read_bytes()
        manifest['postgresql_build_input']['overlay_sha256'][overlay_name] = digest(data.replace(b'\n', b'\r\n'))
        receipt = json.dumps(manifest['postgresql_build_input']).encode()
        write(directory / 'postgresql-build-input.json', receipt)
        manifest['files']['postgresql-build-input.json'] = {'sha256': digest(receipt), 'size': len(receipt)}
        write(directory / 'build-info.json', json.dumps(manifest))
        result = runtime.stage(self.output, binaries=directory, root=self.root)
        self.assertEqual(result['postgresql_build_input'], manifest['postgresql_build_input'])
        self.assertEqual(self.before, self.snapshot())
        manifest['postgresql_build_input']['overlay_sha256'][overlay_name] = digest(data + b'changed')
        write(directory / 'build-info.json', json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'PostgreSQL build receipt differs'):
            runtime.verify_binaries(directory, self.root, self.source_lock)

    def test_changed_executable_rejected_before_staging(self):
        directory, _ = self.package()
        with (directory / 'DbServer.exe').open('ab') as file:
            file.write(b'modified')
        with self.assertRaisesRegex(ValueError, 'size/SHA-256 mismatch'):
            runtime.stage(self.output, binaries=directory, root=self.root)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.before, self.snapshot())

    def test_forged_patch_receipt_and_unlisted_payload_are_rejected(self):
        directory, manifest = self.package()
        manifest['postgresql_build_input']['patched_sha256']['Common/sql/sqlconn.c'] = '0' * 64
        write(directory / 'build-info.json', json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'PostgreSQL build receipt differs'):
            runtime.verify_binaries(directory, self.root, self.source_lock)
        manifest['postgresql_build_input'] = runtime.expected_pg_receipt(self.root, self.source_lock)
        write(directory / 'build-info.json', json.dumps(manifest))
        write(directory / 'sneaked.dll', minimal_pe())
        with self.assertRaisesRegex(ValueError, 'Unlisted package files'):
            runtime.verify_binaries(directory, self.root, self.source_lock)

    def test_altered_pe_metadata_and_fixture_package_are_rejected(self):
        directory, manifest = self.package()
        manifest['files']['DbServer.exe']['pe_machine'] = 0x8664
        write(directory / 'build-info.json', json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'PE metadata mismatch'):
            runtime.verify_binaries(directory, self.root, self.source_lock)
        manifest['files']['DbServer.exe']['pe_machine'] = 332
        manifest['postgresql_persistence_fixture'] = True
        write(directory / 'build-info.json', json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'fixture mode OFF'):
            runtime.verify_binaries(directory, self.root, self.source_lock)

    def test_missing_dynamic_dll_cannot_be_hidden_by_editing_manifest(self):
        directory, manifest = self.package()
        name = DYNAMIC_DLLS[0]
        del manifest['files'][name]
        (directory / name).unlink()
        write(directory / 'build-info.json', json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'Missing required build outputs'):
            runtime.verify_binaries(directory, self.root, self.source_lock)

    def test_legacy_source_only_receipt_is_insufficient(self):
        write(self.donor1 / 'build-info.txt', 'Commit: ' + self.source_lock['commit'])
        with self.assertRaisesRegex(ValueError, 'older source-only'):
            runtime.verify_binaries(self.donor1, self.root, self.source_lock)

    def test_existing_output_or_changed_snapshot_prevents_overwrite(self):
        self.output.mkdir()
        write(self.output / 'precious-save', 'keep')
        with self.assertRaisesRegex(ValueError, 'Output already exists'):
            runtime.stage(self.output, root=self.root)
        self.assertEqual((self.output / 'precious-save').read_text(), 'keep')
        other = self.root / 'new-runtime'
        write(self.content / 'data/Defs/powers.txt', 'changed snapshot')
        with self.assertRaises(subprocess.CalledProcessError):
            runtime.stage(other, root=self.root)
        self.assertFalse(other.exists())


if __name__ == '__main__':
    unittest.main()
