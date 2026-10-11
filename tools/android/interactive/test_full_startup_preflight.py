"""Full orchestration qualification rejects incomplete source/coverage claims."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).parent))
spec = importlib.util.spec_from_file_location('full_startup_preflight', Path(__file__).with_name('qualify_full_startup_preflight.py'))
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class FullStartupPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name); self.payloads = self.root/'payloads'; self.payloads.mkdir()

    @staticmethod
    def put(archive, name, payload):
        entry = zipfile.ZipInfo(name); entry.create_system = 3
        entry.external_attr = 0o100644 << 16
        archive.writestr(entry, payload)

    def source(self, archive_name, index_name, name, payload=b'original', extra=()):
        digest = hashlib.sha256(payload).hexdigest()
        (self.payloads/index_name).write_text(str(len(payload))+'\t'+digest+'\t'+name+'\n')
        with zipfile.ZipFile(self.payloads/archive_name, 'w') as archive:
            if name.startswith('assets/'):
                self.put(archive, 'asset-manifest.json', b'qualified by whole archive pin')
            self.put(archive, name, payload)
            for path, contents in extra:
                self.put(archive, path, contents)

    def small_import(self):
        self.source('atlas-assets.zip', 'atlas-assets-index.tsv', 'assets/defs/original.bin')
        self.source('atlas-text.zip', 'atlas-text-index.tsv', 'data/Defs/original.def', b'definition')

    def test_complete_original_import_checks_every_leaf_and_readonly_metadata(self):
        self.small_import()
        with patch.object(module, 'COUNT', 2), patch.object(module, 'BYTES', 18):
            data, proof = module.materialize_import(self.payloads, self.root/'import')
        self.assertEqual(proof['files'], 2); self.assertTrue(proof['all_leaf_sha256_checked'])
        self.assertFalse(proof['android_import_service_executed'])
        self.assertEqual((data/'Defs/original.def').read_bytes(), b'definition')
        self.assertEqual((data/'Defs/original.bin').stat().st_mode & 0o222, 0)
        self.assertEqual(int((data/'Defs/original.def').stat().st_mtime), module.EPOCH)
        self.assertFalse((data/'defs').exists())

    def test_missing_extra_or_hash_changed_original_input_fails_before_preparation(self):
        self.small_import()
        with zipfile.ZipFile(self.payloads/'atlas-text.zip', 'w') as archive:
            self.put(archive, 'data/Defs/original.def', b'changed___')
        with self.assertRaisesRegex(ValueError, 'member differs|hash differs'):
            module.materialize_import(self.payloads, self.root/'hash-changed')
        self.source('atlas-text.zip', 'atlas-text-index.tsv', 'data/defs/original.def', b'definition',
                    extra=(('data/defs/untracked.def', b'untracked'),))
        with self.assertRaisesRegex(ValueError, 'inventory differs'):
            module.materialize_import(self.payloads, self.root/'extra')
        with zipfile.ZipFile(self.payloads/'atlas-text.zip', 'w'):
            pass
        with self.assertRaisesRegex(ValueError, 'inventory differs'):
            module.materialize_import(self.payloads, self.root/'missing')

    def test_namespace_case_aliases_and_unordered_or_unsafe_indexes_are_rejected(self):
        good = '1\t'+'a'*64+'\tdata/defs/a\n'
        for raw in (good+good, good.replace('data/defs/a', 'data/../a'),
                    good.replace('data/defs/a', 'assets/a'), good.replace('1\t', '01\t', 1),
                    good.replace('a'*64, 'z'*64), good.replace('\tdata/', '\textra\tdata/')):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                list(module.index_rows(raw.encode(), 'data/'))
        self.source('atlas-assets.zip', 'atlas-assets-index.tsv', 'assets/defs/Original.def')
        self.source('atlas-text.zip', 'atlas-text-index.tsv', 'data/defs/original.def')
        with self.assertRaisesRegex(ValueError, 'Case-conflicting'):
            module.materialize_import(self.payloads, self.root/'case-alias')

    def test_original_import_cannot_overwrite_existing_fixture(self):
        target = self.root/'import'; target.mkdir(); (target/'keep').write_text('preserved')
        with self.assertRaisesRegex(ValueError, 'Fresh import fixture required'):
            module.materialize_import(self.payloads, target)
        self.assertEqual((target/'keep').read_text(), 'preserved')

    def test_missing_required_runtime_input_cannot_start_the_large_import_fixture(self):
        def missing(_assets):
            raise FileNotFoundError('client-visual-manifest.json')
        client = SimpleNamespace(verify_assets=missing)
        with patch.object(module, 'checked_import_fixture') as mirror:
            with self.assertRaisesRegex(FileNotFoundError, 'client-visual-manifest'):
                module.verify_inputs_before_import(client, self.root, self.payloads)
            mirror.assert_not_called()

    def test_complete_cached_fixture_is_rehashed_and_refuses_modified_leaf(self):
        self.small_import()
        with patch.object(module, 'COUNT', 2), patch.object(module, 'BYTES', 18):
            data, first = module.checked_import_fixture(self.payloads)
            with patch.object(module, 'materialize_import', side_effect=AssertionError('immutable source copied again')):
                reused, second = module.checked_import_fixture(self.payloads)
            self.assertEqual(reused, data); self.assertEqual(second, first)
            target = data/'Defs/original.def'; target.chmod(0o600); target.write_bytes(b'corrupted!')
            with self.assertRaisesRegex(ValueError, 'ownership changed'):
                module.checked_import_fixture(self.payloads)

    def proof(self):
        value = {'status': 'passed', 'scope': module.SCOPE, 'process_and_sql_boundary': 'not_executed',
            'gate_inventory': [{'stage': stage, 'execution': execution, 'regression_suites': suites}
                               for stage, execution, suites in module.GATES]}
        value['original_import'] = {'files': module.COUNT, 'bytes': module.BYTES, 'all_leaf_sha256_checked': True,
            'android_import_service_executed': False, 'inventory_sha256': 'a'*64,
            'contract_sha256': hashlib.sha256(module.IMPORT_CONTRACT).hexdigest()}
        value['production_methods_executed'] = {
            'client_startup_diagnostic.prepare_worktree': 2,
            'character_avatar_assets.install': 1, 'atlas_world_assets.install': 1,
            'LocalCharacterServer.payloads': 2, 'LocalCharacterServer.prepare_runtime': 2,
            'CharacterCreationDiagnostic.prepare_client_visual_inputs': 2,
            'LocalCharacterServer.prepare_kings_row_runtime': 2, 'LocalCharacterServer.cleanup_config': 2}
        value['preparation'] = {label: {'cache_reused': reuse, 'private_data_files': module.COUNT,
            'private_data_bytes': module.BYTES, 'animation_installed': True, 'animation_count': 5878,
            'graph_status': 'installed_verified_graph', 'prepared_cache_status': 'installed',
            'native_mapserver': module.RETAINED_MAPSERVER, 'manual_atlas_dbserver': module.ATLAS_MANUAL_DBSERVER,
            'kings_row': {'cache_reused': reuse, 'animation_count': 5878,
                'graph_status': 'installed_verified_graph', 'prepared_cache_status': 'installed',
                'native_mapserver': module.RETAINED_MAPSERVER, 'native_dbserver': module.ORIGINAL_DBSERVER,
                'authenticated_original_dbserver': module.ORIGINAL_DBSERVER}}
            for label, reuse in (('fresh_create', False), ('saved_reopen', True))}
        for flag in ('full_private_worktree_mirror_executed', 'full_prepare_runtime_executed',
                     'fresh_create_cold_preparation_verified', 'saved_reopen_warm_preparation_verified',
                     'full_kings_row_cold_and_reuse_preparation_verified', 'client_visual_orchestration_executed',
                     'client_visual_readiness_boundary_stubbed', 'owned_cache_return_and_credential_removal_executed',
                     'complete_runtime_asset_inventory_verified', 'client_audio_orchestration_executed',
                     'atlas_manual_and_kings_stock_dbserver_pins_verified',
                     'cache_cleanup_prerequisites_stubbed_no_native_processes_started'):
            value[flag] = True
        for flag in ('native_runtime_booted', 'physical_execution_validated', 'live_database_and_saved_character_executed'):
            value[flag] = False
        return value

    def test_receipt_cannot_claim_native_sql_or_physical_execution(self):
        proof = self.proof(); module.validate_proof(proof)
        for flag in ('native_runtime_booted', 'physical_execution_validated', 'live_database_and_saved_character_executed'):
            invalid = copy.deepcopy(proof); invalid[flag] = True
            with self.subTest(flag=flag), self.assertRaisesRegex(ValueError, 'cannot claim'):
                module.validate_proof(invalid)

    def test_receipt_requires_complete_orchestration_and_all_unexecuted_gates(self):
        proof = self.proof()
        for flag in ('full_private_worktree_mirror_executed', 'full_prepare_runtime_executed',
                     'full_kings_row_cold_and_reuse_preparation_verified',
                     'client_visual_readiness_boundary_stubbed'):
            invalid = copy.deepcopy(proof); invalid[flag] = False
            with self.subTest(flag=flag), self.assertRaisesRegex(ValueError, 'execution absent'):
                module.validate_proof(invalid)
        invalid = copy.deepcopy(proof); invalid['gate_inventory'].pop()
        with self.assertRaisesRegex(ValueError, 'gate inventory differs'): module.validate_proof(invalid)
        invalid = copy.deepcopy(proof); invalid['process_and_sql_boundary'] = 'passed'
        with self.assertRaisesRegex(ValueError, 'Native boundary'): module.validate_proof(invalid)

    def test_selected_leaf_fixture_cannot_claim_complete_cold_and_reopen_pipeline(self):
        proof = self.proof()
        for location, key, value in (('original_import', 'files', 5649), ('original_import', 'bytes', 1),
                ('original_import', 'all_leaf_sha256_checked', False),
                ('production_methods_executed', 'LocalCharacterServer.prepare_runtime', 0)):
            invalid = copy.deepcopy(proof); invalid[location][key] = value
            with self.subTest(location=location, key=key), self.assertRaises(ValueError):
                module.validate_proof(invalid)

    def test_receipt_rejects_manual_atlas_dbserver_copied_into_kings_or_changed_mapserver(self):
        proof = self.proof()
        for label in ('fresh_create', 'saved_reopen'):
            invalid = copy.deepcopy(proof)
            invalid['preparation'][label]['kings_row']['native_dbserver'] = module.ATLAS_MANUAL_DBSERVER
            with self.subTest(label=label), self.assertRaisesRegex(ValueError, 'native pins differ'):
                module.validate_proof(invalid)
            invalid = copy.deepcopy(proof)
            invalid['preparation'][label]['manual_atlas_dbserver'] = module.ORIGINAL_DBSERVER
            with self.subTest(label=label, target='Atlas'), self.assertRaisesRegex(ValueError, 'native pins differ'):
                module.validate_proof(invalid)
            invalid = copy.deepcopy(proof)
            invalid['preparation'][label]['kings_row']['native_mapserver']['sha256'] = 'a'*64
            with self.subTest(label=label, target='MapServer'), self.assertRaisesRegex(ValueError, 'native pins differ'):
                module.validate_proof(invalid)
        for label in ('fresh_create', 'saved_reopen'):
            invalid = copy.deepcopy(proof); invalid['preparation'][label]['kings_row']['cache_reused'] = not (
                label == 'saved_reopen')
            with self.subTest(label=label), self.assertRaisesRegex(ValueError, 'cold/reuse'):
                module.validate_proof(invalid)


if __name__ == '__main__':
    unittest.main()
