"""Cross-language header equivalence, corruption fallback and generation reuse."""
from pathlib import Path
import hashlib
import copy
import importlib.util
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
spec = importlib.util.spec_from_file_location('texture_header_index', ROOT / 'android/guest/texture_header_index.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Context:
    def __init__(self, report=None): self.report = report or {}
    def check(self): pass
    def event(self, *args, **kwargs): pass


def texture(name, mip=b''):
    extra = ('texture_library/test/' + name).encode() + b'\0' + mip
    return struct.pack('<IIIIIffB3s', 32 + len(extra), 8, 16, 32, 0, 0.1, 0.2, 1, b'TX2') + extra + b'original'


class TextureIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.work = self.root / 'work'
        self.imported = self.root / 'imported'
        self.imported.mkdir()
        folder = self.work / 'data/texture_library/test'
        folder.mkdir(parents=True)
        for name, mip in [('a', b'\x10\x00\x01mip-data'), ('b', b'')]:
            target = self.imported / (name + '.texture')
            target.write_bytes(texture(name, mip))
            target.chmod(0o444)
            (folder / target.name).symlink_to(target)
        self.identity = {'generation': 'generation-' + 'a' * 32}
        self.client = {'source_data': str(self.imported), 'format': 1, 'import': self.identity,
            'package_sha256': '0' * 64, 'cache_archive_sha256': '1' * 64,
            'prerequisites_archive_sha256': '2' * 64, 'prerequisites_manifest_sha256': '3' * 64,
            'normalized_mtime_epoch': 1767225600, 'content_identity_sha256': '4' * 64,
            'worktree_key': self.work.name, 'verified_legacy_receipts': []}
        self.write_client()
    def tearDown(self): self.temp.cleanup()

    def write_client(self):
        (self.work / 'client-work.json').write_text(json.dumps(self.client))

    def prepare(self, exe='b' * 64, context=None):
        return module.prepare(self.work, self.identity, exe, context or Context())

    def test_wrapper_and_lineage_changes_preserve_stable_index(self):
        first, env = self.prepare()
        before = (self.work / module.PACK).read_bytes()
        self.client.update(package_sha256='5' * 64, verified_legacy_receipts=['6' * 64],
                           report_metadata='new wrapper receipt')
        self.write_client()
        with mock.patch.object(module, 'make_pack', side_effect=AssertionError('Unexpected reindex')):
            after, new_env = self.prepare()
        self.assertTrue(after['reused'])
        self.assertEqual(first['identity'], after['identity'])
        self.assertEqual(env, new_env)
        self.assertEqual(before, (self.work / module.PACK).read_bytes())

    def test_every_stable_contract_change_invalidates(self):
        for key, value in (('content_identity_sha256', '7' * 64),
                           ('cache_archive_sha256', '8' * 64),
                           ('prerequisites_archive_sha256', '9' * 64),
                           ('prerequisites_manifest_sha256', 'a' * 64),
                           ('normalized_mtime_epoch', 1767225601)):
            with self.subTest(key=key):
                before, _ = self.prepare()
                self.client[key] = value
                self.write_client()
                after, _ = self.prepare()
                self.assertFalse(after['reused'])
                self.assertNotEqual(before['identity'], after['identity'])

    def legacy_index(self):
        previous = {key: value for key, value in self.client.items()
                    if key not in ('content_identity_sha256', 'worktree_key', 'verified_legacy_receipts')}
        records, inventory, _ = module.texture_inputs(self.work, Context())
        identity = module.pack_identity(previous, self.identity, 'b' * 64, inventory)
        contents, headers = module.make_pack(records, identity, Context())
        saved = {'format': 1, 'identity': identity, 'records': len(records),
            'inventory_sha256': inventory, 'client_executable_sha256': 'b' * 64,
            'bytes': len(contents), 'sha256': hashlib.sha256(contents).hexdigest(),
            'original_header_bytes_sha256': headers}
        module.atomic_write(self.work / module.PACK, contents)
        module.atomic_write(self.work / module.MARKER, module.canonical(saved))
        return previous, contents

    def test_verified_legacy_index_rebinds_envelope_without_reindex(self):
        previous, contents = self.legacy_index()
        context = Context({'client_worktree': {'previous_verified_client_worktree': previous,
            'wrapper_only_migration': True, 'source_root_preserved': True}})
        with mock.patch.object(module, 'make_pack', side_effect=AssertionError('Unexpected reindex')):
            after, env = self.prepare(context=context)
        rebound = (self.work / module.PACK).read_bytes()
        self.assertTrue(after['reused'])
        self.assertTrue(after['legacy_identity_migrated'])
        self.assertEqual(contents[:32], rebound[:32])
        self.assertEqual(contents[64:], rebound[64:])
        self.assertEqual(bytes.fromhex(env['COH_TEXTURE_HEADER_ID']), rebound[32:64])
        self.assertNotEqual(contents[32:64], rebound[32:64])
        self.assertTrue(self.prepare()[0]['reused'])

    def test_unproved_legacy_index_reindexes_conservatively(self):
        self.legacy_index()
        after, _ = self.prepare()
        self.assertFalse(after['reused'])
        self.assertFalse(after['legacy_identity_migrated'])

    def native_upgrade_index(self):
        first, _ = self.prepare()
        contents = (self.work / module.PACK).read_bytes()
        old = module.worktree_identity(self.client)
        self.client['content_identity_sha256'] = 'c' * 64
        self.write_client()
        proof = {'format': 1, 'policy': 'verified_startup_client_layer_v1',
            'previous_client_identity': old, 'previous_executable_sha256': 'b' * 64,
            'client_executable_sha256': 'd' * 64, 'content_identity_sha256': 'c' * 64,
            'layer_manifest_sha256': 'e' * 64, 'texture_header_struct_bytes': 32,
            'native_source_closure_verified': True}
        return first, contents, Context({'client_worktree': {'source_root_preserved': True,
            'native_texture_index_migration': proof}})

    def test_exact_native_layer_rebinds_existing_header_payload_without_decoding(self):
        first, contents, context = self.native_upgrade_index()
        with mock.patch.object(module, 'make_pack', side_effect=AssertionError('Unexpected header reads')):
            after, env = self.prepare(exe='d' * 64, context=context)
        rebound = (self.work / module.PACK).read_bytes()
        self.assertTrue(after['reused'])
        self.assertTrue(after['native_layer_identity_migrated'])
        self.assertEqual(contents[:32], rebound[:32])
        self.assertEqual(contents[64:], rebound[64:])
        self.assertEqual(first['original_header_bytes_sha256'], after['original_header_bytes_sha256'])
        self.assertEqual(bytes.fromhex(env['COH_TEXTURE_HEADER_ID']), rebound[32:64])

    def test_native_rebind_requires_exact_executable_inventory_and_data_proof(self):
        for changed in ('oldexe', 'newexe', 'oldidentity', 'data', 'schema', 'policy', 'source', 'root', 'inventory'):
            with self.subTest(changed=changed):
                self.client['content_identity_sha256'] = '4' * 64
                self.write_client()
                first, contents, context = self.native_upgrade_index()
                proof = context.report['client_worktree']['native_texture_index_migration']
                if changed == 'oldexe': proof['previous_executable_sha256'] = 'a' * 64
                if changed == 'newexe': proof['client_executable_sha256'] = 'a' * 64
                if changed == 'oldidentity': proof['previous_client_identity']['content_identity_sha256'] = 'a' * 64
                if changed == 'data': proof['previous_client_identity']['data_contract']['cache_archive_sha256'] = 'a' * 64
                if changed == 'schema': proof['texture_header_struct_bytes'] = 64
                if changed == 'policy': proof['policy'] = 'generic_same_schema'
                if changed == 'source': proof['native_source_closure_verified'] = False
                if changed == 'root': context.report['client_worktree']['source_root_preserved'] = False
                if changed == 'inventory': (self.work / 'data/texture_library/changed').mkdir(exist_ok=True)
                after, _ = self.prepare(exe='d' * 64, context=context)
                self.assertFalse(after['reused'])
                self.assertFalse(after['native_layer_identity_migrated'])

    def test_interrupted_native_envelope_rename_recovers_without_header_reads(self):
        first, contents, context = self.native_upgrade_index()
        atomic_write = module.atomic_write
        def interrupt(path, data):
            if path.name == module.MARKER: raise OSError('Interrupted marker publication')
            return atomic_write(path, data)
        with mock.patch.object(module, 'atomic_write', side_effect=interrupt), \
                mock.patch.object(module, 'make_pack', side_effect=AssertionError('Unexpected header reads')):
            self.prepare(exe='d' * 64, context=context)
        with mock.patch.object(module, 'make_pack', side_effect=AssertionError('Unexpected header reads')):
            after, _ = self.prepare(exe='d' * 64, context=context)
        self.assertTrue(after['reused'])
        self.assertTrue(after['native_layer_identity_migrated'])
        self.assertTrue(after['interrupted_envelope_recovered'])
        self.assertEqual(contents[64:], (self.work / module.PACK).read_bytes()[64:])

    def test_legacy_snapshot_or_payload_change_refuses_rebinding(self):
        for changed in ('snapshot', 'payload', 'native_upgrade', 'missing_contract', 'envelope'):
            with self.subTest(changed=changed):
                previous, _ = self.legacy_index()
                report = {'previous_verified_client_worktree': previous,
                          'wrapper_only_migration': True, 'source_root_preserved': True}
                if changed == 'snapshot': previous['package_sha256'] = 'f' * 64
                if changed == 'native_upgrade': report['wrapper_only_migration'] = False
                if changed == 'missing_contract': del previous['source_data']
                if changed == 'payload':
                    pack = self.work / module.PACK
                    pack.chmod(0o600)
                    pack.write_bytes(pack.read_bytes()[:-1] + b'x')
                if changed == 'envelope':
                    pack = self.work / module.PACK
                    contents = bytearray(pack.read_bytes())
                    contents[8] ^= 1
                    module.atomic_write(pack, contents)
                    marker = self.work / module.MARKER
                    saved = json.loads(marker.read_bytes())
                    saved['sha256'] = hashlib.sha256(contents).hexdigest()
                    module.atomic_write(marker, module.canonical(saved))
                after, _ = self.prepare(context=Context({'client_worktree': report}))
                self.assertFalse(after['reused'])
                self.assertFalse(after['legacy_identity_migrated'])

    def test_missing_stable_identity_falls_back_to_normal_native_reads(self):
        del self.client['content_identity_sha256']
        self.write_client()
        with self.assertRaisesRegex(ValueError, 'verified client content'):
            self.prepare()

    def test_import_and_directory_changes_invalidate(self):
        first, _ = self.prepare()
        self.identity['generation'] = 'generation-' + 'b' * 32
        self.write_client()
        after, _ = self.prepare()
        self.assertFalse(after['reused'])
        self.assertNotEqual(first['identity'], after['identity'])
        (self.work / 'data/texture_library/added').mkdir()
        directory, _ = self.prepare()
        self.assertFalse(directory['reused'])
        self.assertNotEqual(after['identity'], directory['identity'])

    def test_mutation_while_indexing_is_refused(self):
        original = module.make_pack
        def mutate(*args):
            result = original(*args)
            (self.work / 'data/texture_library/changed').mkdir()
            return result
        with mock.patch.object(module, 'make_pack', side_effect=mutate), \
                self.assertRaisesRegex(ValueError, 'generation changed'):
            self.prepare()
        self.assertFalse((self.work / module.PACK).exists())

    def test_exact_mip_and_warm_reuse(self):
        first, env = self.prepare()
        self.assertFalse(first['reused'])
        second, _ = self.prepare()
        self.assertTrue(second['reused'])
        self.assertEqual(2, second['native_file_opens_avoidable'])
        records, _, _ = module.texture_inputs(self.work, Context())
        pack = (self.work / module.PACK).read_bytes()
        expected, _ = module.make_pack(records, env['COH_TEXTURE_HEADER_ID'], Context())
        self.assertEqual(expected, pack)
        self.assertIn(b'mip-data', pack)
        self.assertEqual('Z:' + str(self.work / 'data').replace('/', '\\'), env['COH_TEXTURE_HEADER_ROOT'])
        self.assertEqual('1', env['COH_STARTUP_DIAGNOSTIC_BOUND'])
        self.assertNotIn(b'original', pack)

    def test_each_leaf_keeps_strict_resolution_with_one_shared_root_proof(self):
        folder = self.work / 'data/texture_library/test'
        for index in range(40):
            target = folder / ('local-%02d.texture' % index)
            target.write_bytes(texture(target.stem))
            target.chmod(0o444)
        original = Path.resolve
        calls = []
        def resolve(path, *args, **kwargs):
            calls.append((path, args, kwargs))
            return original(path, *args, **kwargs)
        with mock.patch.object(Path, 'resolve', resolve):
            records, inventory, client = module.texture_inputs(self.work, Context())
        leaves = [call for call in calls if call[0].suffix == '.texture']
        self.assertEqual(42, len(records))
        self.assertEqual({path for _, path in records}, {path for path, _, _ in leaves})
        self.assertEqual(42, len(leaves))
        self.assertTrue(all(arguments == () and keywords == {'strict': True}
                            for _, arguments, keywords in leaves))
        roots = [call for call in calls if call[0] == self.work / 'data']
        self.assertEqual(2, len(roots))
        self.assertTrue(all(keywords == {'strict': True} for _, _, keywords in roots))
        self.assertEqual(64, len(inventory))
        self.assertEqual(self.client, client)

    def test_cached_private_root_cannot_accept_an_ancestor_replacement(self):
        original = Path.resolve
        replaced = False
        data = self.work / 'data'
        moved = self.work / 'moved-data'
        def resolve(path, *args, **kwargs):
            nonlocal replaced
            result = original(path, *args, **kwargs)
            if path.suffix == '.texture' and not replaced:
                data.rename(moved)
                data.symlink_to(moved, target_is_directory=True)
                replaced = True
            return result
        with mock.patch.object(Path, 'resolve', resolve), \
                self.assertRaisesRegex(ValueError, 'root changed'):
            module.texture_inputs(self.work, Context())
        self.assertTrue(replaced)

    def test_preparation_phase_timings_partition_cold_and_warm_work(self):
        first, _ = self.prepare()
        marker = (self.work / module.MARKER).read_bytes()
        second, _ = self.prepare()
        self.assertEqual(marker, (self.work / module.MARKER).read_bytes())
        self.assertEqual(2, first['inventory_scan_passes'])
        self.assertEqual(1, second['inventory_scan_passes'])
        for receipt in (first, second):
            phases = receipt['preparation_phase_seconds']
            self.assertEqual({'complete_inventory', 'original_header_reads',
                              'validation_and_publication'}, set(phases))
            self.assertTrue(all(type(value) is float and value >= 0 for value in phases.values()))
            self.assertAlmostEqual(receipt['preparation_seconds'], sum(phases.values()), delta=.002)
        self.assertEqual(0, second['preparation_phase_seconds']['original_header_reads'])
        self.assertNotIn('preparation_phase_seconds', json.loads(marker))
        self.assertNotIn('inventory_scan_passes', json.loads(marker))

    def test_executable_and_content_changes_invalidate(self):
        before, _ = self.prepare()
        changed, _ = self.prepare('c' * 64)
        self.assertFalse(changed['reused'])
        self.assertNotEqual(before['identity'], changed['identity'])
        target = self.imported / 'a.texture'
        old_mtime = target.stat().st_mtime_ns
        target.chmod(0o644)
        target.write_bytes(texture('a', b'changed!'))
        target.chmod(0o444)
        os.utime(target, ns=(old_mtime, old_mtime))
        after, _ = self.prepare('c' * 64)
        self.assertFalse(after['reused'])
        self.assertNotEqual(changed['identity'], after['identity'])

    def test_corrupt_pack_regenerated(self):
        first, _ = self.prepare()
        pack = self.work / module.PACK
        pack.chmod(0o600)
        data = bytearray(pack.read_bytes()); data[-1] ^= 1; pack.write_bytes(data)
        after, _ = self.prepare()
        self.assertFalse(after['reused'])
        self.assertEqual(first['sha256'], after['sha256'])

    def test_link_escape_refused(self):
        target = self.work / 'data/texture_library/test/a.texture'
        target.unlink()
        outside = self.root / 'outside.texture'; outside.write_bytes(texture('a')); outside.chmod(0o444)
        target.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'escapes'):
            self.prepare()

    def test_native_decoder_equivalence_and_rejection(self):
        compiler = shutil.which('cc') or shutil.which('gcc')
        self.assertIsNotNone(compiler, 'Native parser qualification requires a C compiler')
        previous, _ = self.legacy_index()
        context = Context({'client_worktree': {'previous_verified_client_worktree': previous,
            'wrapper_only_migration': True, 'source_root_preserved': True}})
        _, env = self.prepare(context=context)
        pack = self.work / module.PACK
        source = self.root / 'decoder.c'
        header = ROOT / 'database/client-texture-index/overlay/Game/src/render/coh_texture_header_index.h'
        source.write_text('#include <stdio.h>\n#include "' + str(header) + '"\n' + r'''
int main(int argc, char **argv) {
    FILE *f; unsigned char *p; long size; CohTextureHeaderIndex index;
    const CohTextureHeaderEntry *entry; int valid;
    if (argc != 4) return 2;
    f = fopen(argv[1], "rb"); if (!f) return 3;
    fseek(f, 0, SEEK_END); size = ftell(f); fseek(f, 0, SEEK_SET);
    p = malloc(size); if (!p || fread(p, 1, size, f) != (size_t)size) return 4; fclose(f);
    valid = cohThiParse(&index, p, size, argv[2]);
    if (!valid) { free(p); return 1; }
    entry = cohThiFind(&index, argv[3]);
    if (entry) fwrite(entry->header, 1, entry->bytes, stdout);
    cohThiFree(&index); free(p); return entry ? 0 : 5;
}
''')
        executable = self.root / 'decoder'
        subprocess.run([compiler, '-std=c11', '-Wall', '-Wextra', '-Werror', str(source), '-o', str(executable)], check=True)
        identity = env['COH_TEXTURE_HEADER_ID']
        def run(path=pack, digest=identity, search='TEXTURE_LIBRARY\\TEST\\A.TEXTURE'):
            return subprocess.run([str(executable), str(path), digest, search], capture_output=True)
        result = run()
        original = (self.imported / 'a.texture').read_bytes()
        self.assertEqual(0, result.returncode)
        self.assertEqual(original[:struct.unpack_from('<I', original)[0]], result.stdout)
        self.assertEqual(5, run(search='texture_library/test/absent.texture').returncode)
        self.assertEqual(1, run(digest='d' * 64).returncode)
        for offset in (0, 8, 12, 16, 20, 24, 28, 65, len(pack.read_bytes()) - 1):
            altered = bytearray(pack.read_bytes()); altered[offset] ^= 128
            corrupt = self.root / ('bad-' + str(offset)); corrupt.write_bytes(altered)
            self.assertEqual(1, run(path=corrupt).returncode, offset)
        # Valid checksum must not admit duplicate/unsorted or traversing paths.
        altered = bytearray(pack.read_bytes())
        altered[68:84] = b'texture_library/'  # unchanged prefix
        altered[84:89] = b'../x/'
        struct.pack_into('<I', altered, 24, zlib.crc32(altered[64:]))
        corrupt = self.root / 'traversal'; corrupt.write_bytes(altered)
        self.assertEqual(1, run(path=corrupt).returncode)


if __name__ == '__main__': unittest.main()
