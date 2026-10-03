"""Cold/warm Atlas data preparation with owned-process and immutable guards."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import character_server_data_cache as cache
import local_character_server as server


class ServerWorktreeReuseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.work = self.root / 'client-work'; self.data = self.work / 'data'
        self.data.mkdir(parents=True)
        for name in ('bin', 'geobin', 'server/db'):
            (self.data / name).mkdir(parents=True)
        self.imported = self.root / 'import'; self.imported.mkdir()
        self.schema_dir = self.root / 'schema'
        self.schema_files = ('data/server/db/servers.cfg', 'data/server/db/schema.def')
        for name in self.schema_files:
            p = self.schema_dir / name; p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('qualified ' + name)
        self.source('defs/powers/set.def', 'qualified powers')
        self.source('maps/Atlas/a.txt', 'qualified geometry')
        self.source('server/db/servers.cfg', 'import config overridden by pinned schema')
        self.source('server/db/schema.def', 'import schema overridden by pinned schema')
        (self.data / 'bin/powers.bin').write_bytes(b'initial client cache')
        (self.work / 'client-work.json').write_text('{"verified":"client"}\n')
        self.map_dir = self.root / 'map'; self.map_dir.mkdir()
        (self.map_dir / 'MapServer.exe').write_bytes(b'qualified binary')
        self.receipt = {'imported_inputs_readonly': True, 'import': {'receipt_sha256': 'a' * 64},
            'cache_archive_sha256': 'b' * 64, 'prerequisites_archive_sha256': 'c' * 64,
            'prerequisites_manifest_sha256': 'd' * 64, 'normalized_mtime_epoch': 1767225600}

    def source(self, name, text='immutable'):
        original = self.imported / name; original.parent.mkdir(parents=True, exist_ok=True)
        original.write_text(text); original.chmod(0o444)
        target = self.data / name; target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(original)
        return original

    def make(self, sequence):
        value = server.LocalCharacterServer.__new__(server.LocalCharacterServer)
        args = SimpleNamespace(game_data=self.imported, assets=self.root / 'assets', session_id=f'{sequence:032x}')
        value.owner = SimpleNamespace(root=self.root, work=self.work, args=args,
            cleanup_status={'wine_prefix_stopped': True, 'owned_processes_reaped': True})
        value.ctx = SimpleNamespace(report={'client_worktree': dict(self.receipt)}, check=Mock(), event=Mock())
        value.creation_report = {}
        value.schema = {'files': {name: {} for name in self.schema_files}}
        value.schema_dir = self.schema_dir
        value.map_package = {'files': {'MapServer.exe': {'sha256':
            hashlib.sha256((self.map_dir / 'MapServer.exe').read_bytes()).hexdigest()}}}
        value.map_package_dir = self.map_dir
        return value

    def base_prepare(self, value):
        value.runtime = self.root / ('local-login-server-' + value.owner.args.session_id)
        value.runtime.mkdir(); (value.runtime / 'data').mkdir(); (value.runtime / 'tools').mkdir()
        for name in self.schema_files:
            p = value.runtime / name; p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes((self.schema_dir / name).read_bytes())

    def prepare(self, value):
        with patch.object(server.login.LocalLoginServer, 'prepare_runtime', lambda actual: self.base_prepare(actual)):
            value.prepare_runtime()
        return value.creation_report['private_map_data']

    def close(self, value):
        value.config = value.runtime / 'data/server/db/servers.cfg'
        value.config.write_text('Password=owned-secret')
        value.cleanup_config()

    def make_legacy_cache(self, value):
        """Represent the actual v1 closed receipt, without a fresh input mirror."""
        record = json.loads(value.data_cache.marker.read_text())
        identity = dict(record['identity'], format=1,
            client_work_receipt_sha256=server.base.file_hash(self.work / 'client-work.json'),
            map_manifest_sha256=getattr(value, 'map_manifest_sha256', server.device.MAP_PROGRESS_PACKAGE_SHA256))
        identity.pop('native_closure_sha256'); identity.pop('server_cache_compatibility_sha256')
        key = hashlib.sha256(cache.canonical(identity)).hexdigest()[:24]
        record.update(identity=identity, key=key)
        old = self.root / ('character-server-data-' + key)
        value.data_cache.path.rename(old)
        (old / 'cache.json').write_text(json.dumps(record))
        value.data_cache.pointer.unlink()
        return old, record

    def test_wrapper_receipt_refresh_keeps_server_key_and_generated_private_bins(self):
        supplement = self.data / 'texture_library/msliberty.texture'
        supplement.parent.mkdir(); supplement.write_bytes(b'immutable supplement'); supplement.chmod(0o444)
        first = self.make(1); self.prepare(first)
        data_inode = (first.runtime / 'data').stat().st_ino
        (first.runtime / 'data/server/bin').mkdir(exist_ok=True)
        generated = first.runtime / 'data/server/bin/contacts.bin'; generated.write_bytes(b'private generated contacts')
        self.close(first)
        (self.work / 'client-work.json').write_text('{"verified":"new-wrapper"}\n')
        second = self.make(2)
        with patch.object(second, 'stage_map_data', side_effect=AssertionError('wrapper rebuilt server data')):
            result = self.prepare(second)
        self.assertEqual(first.data_cache.key, second.data_cache.key)
        self.assertEqual((second.runtime / 'data').stat().st_ino, data_inode)
        self.assertEqual((second.runtime / 'data/server/bin/contacts.bin').read_bytes(), b'private generated contacts')
        self.assertEqual((second.runtime / 'data/texture_library/msliberty.texture').read_bytes(), b'immutable supplement')
        self.assertTrue(result['server_data_cache']['reused'])
        self.close(second)

    def test_clean_legacy_cache_migrates_in_place_and_keeps_original_source_links(self):
        supplement = self.data / 'texture_library/a.texture'
        supplement.parent.mkdir(); supplement.write_bytes(b'root-stays'); supplement.chmod(0o444)
        first = self.make(1); self.prepare(first)
        (first.runtime / 'data/bin/native.bin').write_bytes(b'native private bytes')
        data_inode = (first.runtime / 'data').stat().st_ino
        self.close(first)
        old, record = self.make_legacy_cache(first)
        self.receipt['verified_legacy_receipts'] = [record['identity']['client_work_receipt_sha256']]
        (self.work / 'client-work.json').write_text('{"verified":"wrapper-refreshed"}\n')
        second = self.make(2)
        with patch.object(second, 'stage_map_data', side_effect=AssertionError('legacy donor mirrored inputs')):
            result = self.prepare(second)
        self.assertTrue(result['server_data_cache']['legacy_generation_migrated'])
        self.assertEqual(second.data_cache.path, old)
        self.assertEqual((second.runtime / 'data').stat().st_ino, data_inode)
        self.assertEqual((second.runtime / 'data/bin/native.bin').read_bytes(), b'native private bytes')
        self.assertEqual((second.runtime / 'data/texture_library/a.texture').resolve(), supplement)
        self.assertEqual((second.runtime / 'data/server/db/schema.def').read_bytes(),
                         (self.schema_dir / 'data/server/db/schema.def').read_bytes())
        self.close(second)
        third = self.make(3)
        with patch.object(third, 'stage_map_data', side_effect=AssertionError('new pointer lost migrated donor')):
            self.assertTrue(self.prepare(third)['server_data_cache']['reused'])
        self.assertEqual(third.data_cache.path, old)
        self.close(third)

    def test_interrupted_legacy_rekey_before_checkout_recovers_closed_generation(self):
        first = self.make(1); self.prepare(first); self.close(first)
        old, record = self.make_legacy_cache(first)
        current = self.make(2)
        # Construct the same new identity through the real orchestration, but
        # interrupt after the atomic migration marker and before taking a lease.
        original = cache.ServerDataCache.read
        def interrupt_after_rekey(value):
            if value.path == old and value.identity.get('format') == 2:
                raise server.base.Cancelled('interrupted before checkout')
            return original(value)
        with patch.object(cache.ServerDataCache, 'read', interrupt_after_rekey):
            with self.assertRaises(server.base.Cancelled): self.prepare(current)
        changed = json.loads((old / 'cache.json').read_text())
        self.assertEqual(changed['status'], 'closed'); self.assertIsNone(changed['owner'])
        self.assertEqual(changed['identity']['format'], 2)
        again = self.make(3)
        with patch.object(again, 'stage_map_data', side_effect=AssertionError('interrupted migration rebuilt inputs')):
            result = self.prepare(again)
        self.assertTrue(result['server_data_cache']['interrupted_migration_recovered'])
        self.assertEqual(again.data_cache.path, old)
        self.close(again)

    def test_legacy_map_wrapper_is_qualified_by_actual_old_native_closure_and_corruption_refuses_it(self):
        for sequence, corrupt in enumerate((False, True), start=1):
            with self.subTest(corrupt=corrupt):
                self.receipt['cache_archive_sha256'] = f'{sequence + 20:064x}'
                old_payload = self.root / ('character-map-payload-' + f'{sequence:016x}')
                old_payload.mkdir()
                binary = (self.map_dir / 'MapServer.exe').read_bytes()
                (old_payload / 'MapServer.exe').write_bytes(binary)
                old_package = {'format': 1, 'repository_commit': f'{sequence:040x}',
                    'source_commit': server.device.SOURCE_COMMIT, 'data_commit': server.device.DATA_COMMIT,
                    'files': {'MapServer.exe': {'bytes': len(binary), 'sha256': hashlib.sha256(binary).hexdigest()}}}
                marker = old_payload / 'game-package.json'; marker.write_text(json.dumps(old_package))
                first = self.make(sequence * 2)
                first.map_package = old_package
                first.map_manifest_sha256 = server.base.file_hash(marker)
                self.prepare(first)
                (first.runtime / 'data/bin/native.bin').write_bytes(b'kept across wrapper')
                self.close(first); old, record = self.make_legacy_cache(first)
                if corrupt:
                    (old_payload / 'MapServer.exe').write_bytes(b'foreign old native payload')
                second = self.make(sequence * 2 + 1)
                second.map_package = dict(old_package, repository_commit='f' * 40)
                second.map_manifest_sha256 = 'd' * 64
                result = self.prepare(second)
                self.assertEqual(result['server_data_cache']['reused'], not corrupt)
                if corrupt:
                    self.assertTrue((old / 'data').is_dir())
                    self.assertFalse((second.runtime / 'data/bin/native.bin').exists())
                else:
                    self.assertEqual((second.runtime / 'data/bin/native.bin').read_bytes(), b'kept across wrapper')
                    self.assertEqual(second.data_cache.path, old)
                self.close(second)

    def test_changed_native_or_unproved_legacy_client_receipt_preserves_donor_and_stages_fresh(self):
        for sequence, mutation in enumerate(('native', 'client_receipt', 'owner'), start=1):
            with self.subTest(mutation=mutation):
                self.receipt['cache_archive_sha256'] = f'{sequence:064x}'
                first = self.make(sequence * 2); self.prepare(first); self.close(first)
                old, record = self.make_legacy_cache(first)
                if mutation == 'native':
                    (self.map_dir / 'MapServer.exe').write_bytes(b'new actual native bytes')
                    # Different actual wrapper hash forces bounded native proof,
                    # with no qualified matching old payload available.
                    record['identity']['map_manifest_sha256'] = 'a' * 64
                elif mutation == 'client_receipt':
                    record['identity']['client_work_receipt_sha256'] = 'e' * 64
                else:
                    record.update(status='checked_out', owner={'session_id': 'f' * 32, 'target': '/old-owned-session'})
                record['key'] = hashlib.sha256(cache.canonical(record['identity'])).hexdigest()[:24]
                (old / 'cache.json').write_text(json.dumps(record))
                preserved = (old / 'cache.json').read_bytes()
                second = self.make(sequence * 2 + 1); result = self.prepare(second)
                self.assertFalse(result['server_data_cache']['reused'])
                self.assertEqual((old / 'cache.json').read_bytes(), preserved)
                self.assertTrue((old / 'data').is_dir())
                self.close(second)

    def test_clean_second_session_reuses_directory_and_generated_cache_but_resets_schema(self):
        first = self.make(1); cold = self.prepare(first)
        self.assertFalse(cold['server_data_cache']['reused'])
        identity = (first.runtime / 'data').stat().st_ino
        binary = first.runtime / 'data/bin/native.bin'; binary.write_bytes(b'native generated body')
        (first.runtime / 'data/server/db/schema.def').write_text('native writable mutation')
        (first.runtime / 'logs').mkdir(); (first.runtime / 'logs/old.log').write_text('old evidence')
        self.close(first)
        self.assertFalse((first.data_cache.path / 'data/server/db/servers.cfg').exists())
        self.assertNotIn(cache.CONFIG, first.data_cache.record['private_files'])
        self.assertTrue(all(row['path'] != cache.CONFIG for row in first.data_cache.record['anchors']))
        second = self.make(2)
        with patch.object(second, 'stage_map_data', side_effect=AssertionError('warm must not mirror inputs')):
            warm = self.prepare(second)
        self.assertTrue(warm['server_data_cache']['reused'])
        self.assertEqual((second.runtime / 'data').stat().st_ino, identity)
        self.assertEqual((second.runtime / 'data/bin/native.bin').read_bytes(), b'native generated body')
        for name in self.schema_files:
            self.assertEqual((second.runtime / name).read_bytes(), (self.schema_dir / name).read_bytes())
            self.assertFalse((second.runtime / name).is_symlink())
        self.assertFalse((second.runtime / 'logs').exists())
        self.assertEqual((second.runtime / 'MapServer.exe').read_bytes(), b'qualified binary')
        self.assertEqual(warm['linked_immutable_files'], 0)
        self.close(second)

    def test_missing_cleanup_proof_never_returns_tree_and_next_session_stages_fresh(self):
        first = self.make(1); self.prepare(first)
        first.owner.cleanup_status['wine_prefix_stopped'] = False
        with self.assertRaisesRegex(server.base.DiagnosticError, 'proved owned Wine cleanup'):
            self.close(first)
        old = first.data_cache.path; original_inode = (first.runtime / 'data').stat().st_ino
        second = self.make(2); result = self.prepare(second)
        self.assertFalse(result['server_data_cache']['reused'])
        self.assertIn('prior owner', result['server_data_cache']['reuse_refused'])
        self.assertNotEqual((second.runtime / 'data').stat().st_ino, original_inode)
        self.assertEqual(json.loads((old / 'cache.json').read_text())['status'], 'checked_out')
        self.close(second)
        third = self.make(3); self.assertTrue(self.prepare(third)['server_data_cache']['reused'])
        self.close(third)

    def test_changed_input_identity_uses_original_staging_without_adopting_prior_tree(self):
        first = self.make(1); self.prepare(first); self.close(first)
        old = first.data_cache.path
        self.receipt['cache_archive_sha256'] = 'e' * 64
        second = self.make(2); result = self.prepare(second)
        self.assertFalse(result['server_data_cache']['reused'])
        self.assertNotEqual(first.data_cache.key, second.data_cache.key)
        self.assertTrue((old / 'data').is_dir())
        self.close(second)

    def test_changed_immutable_directory_or_missing_anchor_refuses_donor_and_recovers(self):
        for damage in ('entry', 'anchor', 'linked_directory', 'private_link'):
            with self.subTest(damage=damage):
                first = self.make(10 + len(list(self.root.glob('local-login-server-*'))))
                self.prepare(first); self.close(first)
                tree = first.data_cache.path / 'data'
                if damage == 'entry':
                    (tree / 'defs/powers/extra.def').write_text('unexpected')
                elif damage == 'anchor':
                    (tree / 'defs/powers/set.def').unlink()
                elif damage == 'linked_directory':
                    (tree / 'maps/Atlas/a.txt').unlink(); (tree / 'maps/Atlas').rmdir()
                    (tree / 'maps/Atlas').symlink_to(self.imported / 'maps/Atlas', target_is_directory=True)
                else:
                    (tree / 'bin/powers.bin').unlink()
                    (tree / 'bin/powers.bin').symlink_to(self.imported / 'defs/powers/set.def')
                second = self.make(10 + len(list(self.root.glob('local-login-server-*'))))
                self.assertFalse(self.prepare(second)['server_data_cache']['reused'])
                self.assertTrue(tree.exists())
                self.close(second)

    def test_malformed_pointer_and_marker_do_not_block_fresh_session(self):
        first = self.make(1); self.prepare(first); self.close(first)
        first.data_cache.pointer.write_text('{broken')
        second = self.make(2); result = self.prepare(second)
        self.assertFalse(result['server_data_cache']['reused'])
        self.assertEqual(result['server_data_cache']['reuse_refused'], 'invalid_cache_pointer')
        self.close(second)
        self.assertTrue(list(self.root.glob('*.json-invalid-*')))
        third = self.make(3); self.assertTrue(self.prepare(third)['server_data_cache']['reused']); self.close(third)
        third.data_cache.marker.write_text('{}')
        fourth = self.make(4); self.assertFalse(self.prepare(fourth)['server_data_cache']['reused']); self.close(fourth)

    def test_imported_anchor_metadata_change_and_linked_pointer_are_detected(self):
        first = self.make(1); self.prepare(first); self.close(first)
        original = self.imported / 'defs/powers/set.def'
        original.chmod(0o644)
        second = self.make(2); result = self.prepare(second)
        self.assertFalse(result['server_data_cache']['reused'])
        self.assertIn('anchor changed', result['server_data_cache']['reuse_refused'])
        original.chmod(0o444)
        self.close(second)
        pointer = second.data_cache.pointer
        pointer.unlink(); pointer.symlink_to(self.work / 'client-work.json')
        third = self.make(3); self.assertFalse(self.prepare(third)['server_data_cache']['reused']); self.close(third)
        self.assertEqual((self.work / 'client-work.json').read_text(), '{"verified":"client"}\n')

    def test_host_metric_warm_preparation_avoids_all_input_leaf_recreation(self):
        for i in range(4000):
            self.source(f'defs/bucket-{i % 20}/input-{i}.def')
        first = self.make(1)
        before = time.perf_counter()
        with patch.object(Path, 'symlink_to', autospec=True, wraps=Path.symlink_to) as links:
            # wraps+autospec does not perform the write on every Python version.
            links.side_effect = lambda path, target, **kw: __import__('os').symlink(target, path, **kw)
            cold = self.prepare(first); cold_links = links.call_count
        cold_seconds = time.perf_counter() - before
        self.close(first)
        second = self.make(2); before = time.perf_counter()
        with patch.object(Path, 'symlink_to', side_effect=AssertionError('warm created input link')):
            warm = self.prepare(second)
        warm_seconds = time.perf_counter() - before
        self.assertEqual(cold_links, 4002)
        self.assertTrue(warm['server_data_cache']['reused'])
        self.assertLess(warm['server_data_cache']['immutable_directory_checks'], 30)
        self.assertEqual(warm['linked_immutable_files'], 0)
        self.assertLess(warm_seconds, cold_seconds)
        print('SERVER_DATA_HOST_METRIC', json.dumps({'fixture_immutable_leaves': cold_links,
            'cold_seconds': round(cold_seconds, 6), 'warm_seconds': round(warm_seconds, 6),
            'cold_symlink_creations': cold_links, 'warm_symlink_creations': 0,
            'warm_immutable_directory_checks': warm['server_data_cache']['immutable_directory_checks']}))
        self.close(second)

    def test_cache_generation_cap_preserves_existing_trees_and_uses_fresh_nonpersistent_data(self):
        for sequence in range(16):
            (self.root / ('character-server-data-' + f'{sequence:024x}')).mkdir()
        first = self.make(99); result = self.prepare(first)
        self.assertFalse(result['server_data_cache']['reused'])
        self.assertFalse(result['server_data_cache']['cache_created'])
        self.assertEqual(result['server_data_cache']['reuse_refused'], 'cache_generation_limit_reached')
        self.assertFalse(first.data_cache.path.exists())
        self.close(first)
        self.assertEqual(len(list(self.root.glob('character-server-data-*'))), 16)
        self.assertTrue((first.runtime / 'data').is_dir())

    def test_forged_anchor_outside_verified_roots_and_owner_record_are_not_reused(self):
        first = self.make(1); self.prepare(first); self.close(first)
        record = json.loads(first.data_cache.marker.read_text())
        record['directories'][0]['uid'] += 1
        first.data_cache.marker.write_text(json.dumps(record))
        second = self.make(2); self.assertFalse(self.prepare(second)['server_data_cache']['reused']); self.close(second)
        record = json.loads(second.data_cache.marker.read_text())
        anchor = record['anchors'][0]
        path = second.data_cache.path / 'data' / anchor['path']
        outside = self.root / 'outside.def'; outside.write_text('foreign immutable'); outside.chmod(0o444)
        path.unlink(); path.symlink_to(outside)
        anchor.update(source=str(outside), source_identity=cache.fingerprint(outside),
                      sha256=hashlib.sha256(outside.read_bytes()).hexdigest())
        for row in record['directories']:
            row['mtime_ns'] = (second.data_cache.path / 'data' / row['path']).stat().st_mtime_ns
        second.data_cache.marker.write_text(json.dumps(record))
        third = self.make(3); result = self.prepare(third)
        self.assertFalse(result['server_data_cache']['reused'])
        self.assertIn('anchor changed', result['server_data_cache']['reuse_refused'])
        self.close(third)

    def test_missing_root_or_middle_directory_receipt_preserves_donor_and_stages_fresh(self):
        for sequence, omitted in enumerate(('', 'defs'), start=1):
            with self.subTest(omitted=omitted):
                first = self.make(sequence * 2); self.prepare(first); self.close(first)
                donor = first.data_cache.path / 'data'
                donor_inode = donor.stat().st_ino
                record = json.loads(first.data_cache.marker.read_text())
                self.assertTrue(any(row['path'] == omitted for row in record['directories']))
                record['directories'] = [row for row in record['directories'] if row['path'] != omitted]
                first.data_cache.marker.write_text(json.dumps(record))
                refused_receipt = first.data_cache.marker.read_bytes()
                second = self.make(sequence * 2 + 1); result = self.prepare(second)
                self.assertFalse(result['server_data_cache']['reused'])
                self.assertIn('Incomplete immutable', result['server_data_cache']['reuse_refused'])
                self.assertEqual(donor.stat().st_ino, donor_inode)
                self.assertEqual(first.data_cache.marker.read_bytes(), refused_receipt)
                self.assertNotEqual((second.runtime / 'data').stat().st_ino, donor_inode)
                self.close(second)


if __name__ == '__main__':
    unittest.main()
