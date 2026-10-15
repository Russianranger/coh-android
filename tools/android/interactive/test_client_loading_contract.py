"""Exercise the exact immediate Game upgrade and real texture-index migration.

Small native fixtures retain the production receipt chain and filesystem paths.
The tests preserve generated caches, supplements and absolute server links while
changing only Game, then run the actual texture-index producer against that tree.
"""
import copy
import functools
import hashlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import zipfile

import package_client_loading_native as loading
import test_native_client_upgrade as prior
import test_texture_header_index as textures

fixtures, guest = prior.fixtures, prior.guest
contract = guest.native_candidate
index = textures.module


@functools.lru_cache(maxsize=1)
def client_loading_build_input():
    return loading.expected_receipt()


def client_loading_manifest(startup_package, new_game_record, repository_commit='d' * 40):
    """Typed synthetic producer for guest/ZIP guards, never real qualification."""
    native = copy.deepcopy(startup_package['startup_bundle_client']['manifest'])
    build = copy.deepcopy(client_loading_build_input())
    previous = startup_package['files']['CityOfHeroes.exe']
    checks = {'format': 1, 'status': 'passed', 'platform': 'windows', 'architecture': 'Win32',
        'configuration': 'OptDebug', 'build_input': copy.deepcopy(build),
        'equivalence_verified': True, 'explicit_length_behavior_verified': True,
        'thread_local_flags_verified': True, 'opt_in_and_fallback_verified': True,
        'known_length_path_secure_crt_call_eliminated': True,
        'physical_startup_savings_validated': False,
        'assembly_sha256': 'a' * 64, 'harness_sha256': 'b' * 64,
        'compiler_options': ['/O2', '/Oy-', '/MT', '/TC'],
        'benchmarks': [{'length': size, 'stock_seconds': 2.0, 'candidate_seconds': 1.0, 'rounds': 5}
                       for size in (8, 48, 128, 512, 11999)]}
    native.update(role=loading.ROLE, repository_commit=repository_commit,
        build_input=build, files={'CityOfHeroes.exe': copy.deepcopy(new_game_record)},
        decoder_source_sha256=copy.deepcopy(build['patched_sha256']),
        base_client_executable=copy.deepcopy(previous), cache_encoding_changed=False,
        windows_qualification=checks, cmake_cache={'bytes': 64, 'sha256': 'c' * 64},
        run_url='https://github.com/Russianranger/coh-android/actions/runs/1234')
    return native


class ClientLoadingContractTests(unittest.TestCase):
    def setUp(self):
        fixtures.WorktreeTests.setUp(self)
        source = self.data / 'texture_library/test/a.texture'
        source.parent.mkdir(parents=True)
        source.write_bytes(textures.texture('a', b'original-mip'))
        for name, value in (('DATA_COUNT', 6), ('DATA_BYTES', 25 + source.stat().st_size)):
            patched = patch.object(guest, name, value)
            patched.start(); self.addCleanup(patched.stop)
        prior.NativeClientUpgradeTests.candidate(self)
        contents, package = self.read_archive()
        frozen = package['native_responsiveness']['receipt']
        frozen['retained_cache']['schema_sources_sha256'] = loading.base.baseline.schema_pins()
        package['native_responsiveness']['receipt_sha256'] = contract.canonical_sha(frozen)
        self.write_archive(contents, package)
        (self.assets / 'native-responsiveness.json').write_text(json.dumps(frozen))
        self.donor = prior.NativeClientUpgradeTests.startup_derivative(self)
        self.donor_game = copy.deepcopy(self.donor['files']['CityOfHeroes.exe'])
        self.runtime, self.donor_report = self.prepare()
        self.generated = self.runtime / 'data/bin/after-play.bin'
        self.generated.write_bytes(b'valuable generated private runtime cache')
        self.supplement = self.runtime / 'data/object_library/current-world.geo'
        self.supplement.parent.mkdir()
        self.supplement.write_bytes(b'private verified world leaf')
        self.supplement.chmod(0o400)
        self.server = self.root / 'owned-server-data'
        self.server.mkdir()
        self.server_leaf = self.server / 'current-world.geo'
        self.server_leaf.symlink_to(self.supplement)

    def prepare(self):
        return guest.prepare_worktree(self.work, self.data, self.assets, self.identity, self.context)

    def read_archive(self):
        with zipfile.ZipFile(self.assets / 'client-runtime.zip') as archive:
            contents = {name: archive.read(name) for name in archive.namelist()}
        manifest = json.loads(contents.pop('client-package.json'))
        return contents, manifest

    def write_archive(self, contents, manifest):
        with zipfile.ZipFile(self.assets / 'client-runtime.zip', 'w') as archive:
            for name, raw in contents.items(): archive.writestr(name, raw)
            archive.writestr('client-package.json', json.dumps(manifest))

    def loading_derivative(self):
        contents, manifest = self.read_archive()
        raw = fixtures.pe_bytes() + b'client-binary-loading-native-Game'
        record = dict(self.donor_game, size=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        frozen = manifest['native_responsiveness']['receipt']
        native = client_loading_manifest(manifest, record)
        manifest['client_loading'] = {
            'manifest': native,
            'manifest_sha256': contract.canonical_sha(native),
            'base_startup_client_manifest_sha256': manifest['startup_bundle_client']['manifest_sha256'],
            'base_client_executable': copy.deepcopy(self.donor_game)}
        manifest['files']['CityOfHeroes.exe'] = record
        contents['CityOfHeroes.exe'] = raw
        self.write_archive(contents, manifest)
        self.assertEqual(frozen, manifest['native_responsiveness']['receipt'])
        return manifest

    def old_index(self):
        context = textures.Context({'client_worktree': self.donor_report})
        receipt, _ = index.prepare(self.runtime, self.identity, self.donor_game['sha256'], context)
        return receipt, (self.runtime / index.PACK).read_bytes()

    def upgraded_index(self, report, executable, context=None):
        context = context or textures.Context({'client_worktree': report})
        return index.prepare(self.runtime, self.identity, executable['sha256'], context)

    def preserved(self):
        paths = [self.generated, self.supplement, self.runtime / 'data/texture_library/test/a.texture',
                 self.runtime / 'fixture0.dll', self.server_leaf]
        return {str(path): (path.lstat().st_ino, path.lstat().st_mtime_ns,
                           path.read_bytes(), os.readlink(path) if path.is_symlink() else None)
                for path in paths}

    def test_immediate_donor_upgrade_preserves_live_root_and_existing_server_links(self):
        before = self.preserved()
        expected = self.loading_derivative()
        with patch.object(guest.os, 'scandir', side_effect=AssertionError('Cold input tree recreated')):
            runtime, report = self.prepare()
        self.assertEqual(self.runtime, runtime)
        self.assertEqual(before, self.preserved())
        self.assertEqual(self.supplement, self.server_leaf.resolve(strict=True))
        self.assertTrue(report['reused'])
        self.assertTrue(report['native_executable_upgraded'])
        self.assertTrue(report['source_root_preserved'])
        self.assertTrue(report['generated_cache_bytes_preserved'])
        self.assertFalse(report['wrapper_only_migration'])
        self.assertEqual(expected['files']['CityOfHeroes.exe']['sha256'],
                         guest.base.file_hash(runtime / 'CityOfHeroes.exe'))
        proof = report['native_texture_index_migration']
        self.assertEqual('verified_client_loading_layer_v1', proof['policy'])
        self.assertEqual(self.donor_game['sha256'], proof['previous_executable_sha256'])
        self.assertEqual(self.donor_report['content_identity_sha256'],
                         proof['previous_client_identity']['content_identity_sha256'])
        self.assertEqual(expected['client_loading']['manifest_sha256'], proof['layer_manifest_sha256'])
        self.assertNotIn('native_texture_index_migration',
                         json.loads((runtime / 'client-work.json').read_text()))
        retry = self.prepare()[1]
        self.assertTrue(retry['reused'])
        self.assertEqual(proof, retry['native_texture_index_migration'])

    def test_new_layer_also_prepares_a_fresh_private_root_with_stock_cache_donor(self):
        expected = self.loading_derivative()
        root = self.root / 'fresh-private-worktrees'
        root.mkdir()
        runtime, report = guest.prepare_worktree(root, self.data, self.assets, self.identity, self.context)
        self.assertFalse(report['reused'])
        self.assertNotIn('native_texture_index_migration', report)
        self.assertEqual(expected['files']['CityOfHeroes.exe']['sha256'],
                         guest.base.file_hash(runtime / 'CityOfHeroes.exe'))
        self.assertEqual(self.data / 'texture_library/test/a.texture',
                         (runtime / 'data/texture_library/test/a.texture').resolve(strict=True))
        self.assertEqual(b'input', (self.data / 'bin/cache.bin').read_bytes())
        self.assertFalse((runtime / 'data/bin/sequencers.bin').is_symlink())

    def test_exact_immediate_donor_index_rebind_changes_only_owned_envelope(self):
        previous, raw = self.old_index()
        expected = self.loading_derivative()
        _, report = self.prepare()
        with patch.object(index, 'make_pack', side_effect=AssertionError('Unexpected header decoding')):
            after, env = self.upgraded_index(report, expected['files']['CityOfHeroes.exe'])
        rebound = (self.runtime / index.PACK).read_bytes()
        self.assertTrue(after['reused'])
        self.assertTrue(after['native_layer_identity_migrated'])
        self.assertFalse(after['legacy_identity_migrated'])
        self.assertEqual(raw[:32], rebound[:32])
        self.assertEqual(raw[64:], rebound[64:])
        self.assertNotEqual(raw[32:64], rebound[32:64])
        self.assertEqual(bytes.fromhex(env['COH_TEXTURE_HEADER_ID']), rebound[32:64])
        self.assertEqual(previous['original_header_bytes_sha256'], after['original_header_bytes_sha256'])
        with patch.object(index, 'make_pack', side_effect=AssertionError('Warm index unnecessarily regenerated')):
            retry, _ = self.upgraded_index(self.prepare()[1], expected['files']['CityOfHeroes.exe'])
        self.assertTrue(retry['reused'])
        self.assertEqual(rebound, (self.runtime / index.PACK).read_bytes())

    def test_interrupted_worktree_receipt_recovers_exact_immediate_donor_proof(self):
        previous = self.preserved()
        self.loading_derivative()
        with patch.object(guest.base, 'private_write', side_effect=OSError('Interrupted worktree marker')):
            with self.assertRaises(OSError): self.prepare()
        with patch.object(guest.os, 'scandir', side_effect=AssertionError('Cold input tree recreated')):
            runtime, report = self.prepare()
        self.assertEqual(self.runtime, runtime)
        self.assertEqual(previous, self.preserved())
        self.assertEqual(self.donor_game['sha256'],
                         report['native_texture_index_migration']['previous_executable_sha256'])
        self.assertEqual(self.donor_report['content_identity_sha256'],
                         report['native_texture_index_migration']['previous_client_identity']['content_identity_sha256'])

    def test_ancestral_game_cannot_replace_the_immediate_donor(self):
        target = self.runtime / 'CityOfHeroes.exe'
        ancestor = fixtures.pe_bytes() + b'candidate-native-client'
        target.chmod(0o600); target.write_bytes(ancestor)
        expected = guest.base.file_hash(target)
        self.loading_derivative()
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'Cached client binary'):
            self.prepare()
        self.assertEqual(expected, guest.base.file_hash(target))

    def test_foreign_immediate_game_rejected_before_replacing_any_files(self):
        target = self.runtime / 'CityOfHeroes.exe'
        target.chmod(0o600); target.write_bytes(target.read_bytes() + b'foreign suffix')
        original = target.read_bytes(); preserved = self.preserved()
        self.loading_derivative()
        with self.assertRaises(guest.base.DiagnosticError): self.prepare()
        self.assertEqual(original, target.read_bytes())
        self.assertEqual(preserved, self.preserved())

    def test_changed_retained_dll_refused_before_client_upgrade(self):
        target = self.runtime / 'fixture0.dll'
        target.chmod(0o600); target.write_bytes(target.read_bytes() + b'foreign suffix')
        self.loading_derivative()
        with self.assertRaises(guest.base.DiagnosticError): self.prepare()
        self.assertEqual(self.donor_game['sha256'], guest.base.file_hash(self.runtime / 'CityOfHeroes.exe'))

    def test_installed_frozen_receipt_and_cache_pins_remain_required(self):
        self.loading_derivative()
        for name in ('native-responsiveness.json', 'client-caches.zip', 'client-prerequisites.zip'):
            path = self.assets / name; original = path.read_bytes()
            if name == 'native-responsiveness.json':
                value = json.loads(original); value['repository_commit'] = 'f' * 40
                path.write_text(json.dumps(value))
            elif name == 'client-prerequisites.zip':
                with zipfile.ZipFile(path) as archive:
                    contents = {entry: archive.read(entry) for entry in archive.namelist()}
                leaf = next(iter(self.prerequisite_contents))
                contents[leaf] += b'changed prepared prerequisite'
                with zipfile.ZipFile(path, 'w') as archive:
                    for entry, payload in contents.items(): archive.writestr(entry, payload)
            else:
                path.write_bytes(original + b'changed prepared data')
            try:
                with self.subTest(name=name), self.assertRaises((ValueError, guest.base.DiagnosticError)):
                    self.prepare()
                self.assertEqual(self.donor_game['sha256'],
                                 guest.base.file_hash(self.runtime / 'CityOfHeroes.exe'))
            finally:
                path.write_bytes(original)

    def test_loading_layer_requires_exact_base_manifest_record_and_scope(self):
        original = self.loading_derivative()
        for name in ('base_pin', 'base_manifest', 'extra_wrapper', 'missing_startup', 'native_target',
                     'retained_source', 'schema', 'dll', 'runtime_claim', 'schema_change', 'source_commit'):
            changed = copy.deepcopy(original)
            wrapper = changed['client_loading']; native = wrapper['manifest']
            if name == 'base_pin': wrapper['base_client_executable']['sha256'] = 'f' * 64
            if name == 'base_manifest': wrapper['base_startup_client_manifest_sha256'] = 'f' * 64
            if name == 'extra_wrapper': wrapper['trust_previous_game'] = True
            if name == 'missing_startup': del changed['startup_bundle_client']
            if name == 'native_target': native['files']['MapServer.exe'] = native['files']['CityOfHeroes.exe']
            if name == 'retained_source': native['retained_source_inputs']['client_texture']['patch_sha256'] = 'f' * 64
            if name == 'schema': native['schema_sources_sha256'] = {'foreign': 'f' * 64}
            if name == 'dll': changed['files']['fixture0.dll']['sha256'] = 'f' * 64
            if name == 'runtime_claim': native['runtime_execution_validated'] = True
            if name == 'schema_change': native['build_input']['parse6_schema_changes'] = True
            if name == 'source_commit': native['source_commit'] = 'f' * 40
            wrapper['manifest_sha256'] = contract.canonical_sha(native)
            with self.subTest(name=name), self.assertRaises(ValueError): contract.client_contract(changed)

    def test_modified_ancestor_manifest_cannot_hide_behind_new_layer_pins(self):
        original = self.loading_derivative()
        for name in ('ancestor_game', 'ancestor_source', 'frozen_receipt'):
            changed = copy.deepcopy(original)
            startup = changed['startup_bundle_client']
            if name == 'ancestor_game': startup['manifest']['files']['CityOfHeroes.exe']['sha256'] = 'f' * 64
            if name == 'ancestor_source': startup['manifest']['schema_sources_sha256'] = {'foreign': 'f' * 64}
            if name == 'frozen_receipt':
                changed['native_responsiveness']['receipt']['retained_cache']['schema_changed'] = True
                changed['native_responsiveness']['receipt_sha256'] = contract.canonical_sha(
                    changed['native_responsiveness']['receipt'])
            startup['manifest_sha256'] = contract.canonical_sha(startup['manifest'])
            changed['client_loading']['base_startup_client_manifest_sha256'] = startup['manifest_sha256']
            changed['client_loading']['base_client_executable'] = copy.deepcopy(
                startup['manifest']['files']['CityOfHeroes.exe'])
            with self.subTest(name=name), self.assertRaises(ValueError): contract.client_contract(changed)

    def test_new_layer_cannot_claim_an_unchanged_or_ancestral_game(self):
        original = self.loading_derivative()
        records = (original['client_loading']['base_client_executable'],
                   original['native_responsiveness']['receipt']['files']['CityOfHeroes.exe'])
        for record in records:
            changed = copy.deepcopy(original)
            changed['files']['CityOfHeroes.exe'] = copy.deepcopy(record)
            native = changed['client_loading']['manifest']
            native['files']['CityOfHeroes.exe'] = copy.deepcopy(record)
            changed['client_loading']['manifest_sha256'] = contract.canonical_sha(native)
            with self.subTest(record=record['sha256']), self.assertRaises(ValueError):
                contract.client_contract(changed)

    def test_native_build_contract_preserves_freshness_crc_and_memory_semantics(self):
        original = self.loading_derivative()
        for name in ('freshness', 'encoding', 'graphics', 'copy_scope', 'explicit_length', 'ownership',
                     'thread_local', 'profile_phases', 'reverse_patch', 'original_source', 'source_scope',
                     'crc_proof', 'startup_source', 'build_target'):
            changed = copy.deepcopy(original)
            wrapper = changed['client_loading']; native = wrapper['manifest']; build = native['build_input']
            if name == 'freshness': build['source_freshness_changed'] = True
            if name == 'encoding': build['cache_encoding_changed'] = True
            if name == 'graphics': build['graphics_profile_changes'] = True
            if name == 'copy_scope': build['known_length_copy']['negative_length_only'] = False
            if name == 'explicit_length': build['known_length_copy']['explicit_length_secure_crt_preserved'] = False
            if name == 'ownership': build['known_length_copy']['allocation_and_free_behavior_preserved'] = False
            if name == 'thread_local': build['bin_profile']['thread_local_flags_and_counters'] = False
            if name == 'profile_phases': build['bin_profile']['phases'] += ['render']
            if name == 'reverse_patch': build['reverse_patch_exact_base_verified'] = False
            if name == 'original_source': build['source_sha256'][loading.FILE] = 'f' * 64
            if name == 'source_scope': build['patched_sha256']['Game/src/render/tex.c'] = 'f' * 64
            if name == 'crc_proof': del build['preserved_functions_sha256']['int ParseTableCRC(']
            if name == 'startup_source': build['base_startup_client_build_input']['patch_sha256'] = 'f' * 64
            if name == 'build_target': build['build_targets'] = ['MapServer']
            native['decoder_source_sha256'] = copy.deepcopy(build['patched_sha256'])
            native['windows_qualification']['build_input'] = copy.deepcopy(build)
            wrapper['manifest_sha256'] = contract.canonical_sha(native)
            with self.subTest(name=name), self.assertRaises(ValueError): contract.client_contract(changed)

    def test_windows_qualification_refuses_missing_equivalence_or_unmeasured_speedup(self):
        original = self.loading_derivative()
        for name in ('platform', 'thread_local', 'equivalence', 'fallback', 'explicit_length', 'physical_claim',
                     'missing_length', 'duplicate_length', 'boolean_time', 'nan_time', 'inf_time', 'no_speedup',
                     'missing_assembly', 'bad_assembly', 'missing_harness', 'bad_harness',
                     'missing_rounds', 'fractional_rounds', 'boolean_rounds',
                     'missing_compiler_options', 'changed_compiler_options'):
            changed = copy.deepcopy(original)
            wrapper = changed['client_loading']; native = wrapper['manifest']; checks = native['windows_qualification']
            if name == 'platform': checks['platform'] = 'linux'
            if name == 'thread_local': checks['thread_local_flags_verified'] = False
            if name == 'equivalence': checks['equivalence_verified'] = False
            if name == 'fallback': checks['opt_in_and_fallback_verified'] = False
            if name == 'explicit_length': checks['explicit_length_behavior_verified'] = False
            if name == 'physical_claim': checks['physical_startup_savings_validated'] = True
            if name == 'missing_length': checks['benchmarks'].pop()
            if name == 'duplicate_length': checks['benchmarks'][-1]['length'] = 8
            if name == 'boolean_time': checks['benchmarks'][0]['candidate_seconds'] = True
            if name == 'nan_time': checks['benchmarks'][0]['candidate_seconds'] = float('nan')
            if name == 'inf_time': checks['benchmarks'][0]['stock_seconds'] = float('inf')
            if name == 'missing_assembly': del checks['assembly_sha256']
            if name == 'bad_assembly': checks['assembly_sha256'] = 'A' * 64
            if name == 'missing_harness': del checks['harness_sha256']
            if name == 'bad_harness': checks['harness_sha256'] = 'not-a-pin'
            if name == 'missing_rounds': del checks['benchmarks'][0]['rounds']
            if name == 'fractional_rounds': checks['benchmarks'][0]['rounds'] = 5.0
            if name == 'boolean_rounds': checks['benchmarks'][0]['rounds'] = True
            if name == 'missing_compiler_options': del checks['compiler_options']
            if name == 'changed_compiler_options': checks['compiler_options'] = ['/Od', '/MT', '/TC']
            if name == 'no_speedup':
                for row in checks['benchmarks']: row['candidate_seconds'] = row['stock_seconds']
            wrapper['manifest_sha256'] = contract.canonical_sha(native)
            with self.subTest(name=name), self.assertRaises(ValueError): contract.client_contract(changed)

    def test_foreign_archive_bytes_rejected_before_touching_the_donor_game(self):
        self.loading_derivative()
        contents, manifest = self.read_archive()
        contents['CityOfHeroes.exe'] += b'not covered by producer record'
        self.write_archive(contents, manifest)
        with self.assertRaises(guest.base.DiagnosticError): self.prepare()
        self.assertEqual(self.donor_game['sha256'], guest.base.file_hash(self.runtime / 'CityOfHeroes.exe'))

    def test_missing_or_ancestral_index_proof_conservatively_rebuilds(self):
        self.old_index()
        expected = self.loading_derivative(); _, report = self.prepare()
        raw = (self.runtime / index.PACK).read_bytes()
        marker = (self.runtime / index.MARKER).read_bytes()
        for change in ('missing', 'ancestor_policy', 'ancestor_game', 'wrong_schema', 'unverified_source', 'wrong_root'):
            index.atomic_write(self.runtime / index.PACK, raw)
            index.atomic_write(self.runtime / index.MARKER, marker)
            changed = copy.deepcopy(report)
            proof = changed['native_texture_index_migration']
            if change == 'missing': del changed['native_texture_index_migration']
            if change == 'ancestor_policy': proof['policy'] = 'generic_same_schema'
            if change == 'ancestor_game': proof['previous_executable_sha256'] = self.exesha
            if change == 'wrong_schema': proof['texture_header_struct_bytes'] = 64
            if change == 'unverified_source': proof['native_source_closure_verified'] = False
            if change == 'wrong_root': changed['source_root_preserved'] = False
            with self.subTest(change=change), patch.object(index, 'make_pack', wraps=index.make_pack) as rebuild:
                after, _ = self.upgraded_index(changed, expected['files']['CityOfHeroes.exe'])
            self.assertEqual(1, rebuild.call_count)
            self.assertFalse(after['reused'])
            self.assertFalse(after['native_layer_identity_migrated'])

    def test_inventory_mutation_rebuilds_instead_of_rebinding_stale_headers(self):
        _, original = self.old_index()
        expected = self.loading_derivative(); _, report = self.prepare()
        source = self.data / 'texture_library/test/a.texture'
        timestamp = source.stat().st_mtime_ns
        source.chmod(0o600)
        source.write_bytes(textures.texture('a', b'different-mip'))
        os.utime(source, ns=(timestamp, timestamp)); source.chmod(0o400)
        with patch.object(index, 'make_pack', wraps=index.make_pack) as rebuild:
            after, _ = self.upgraded_index(report, expected['files']['CityOfHeroes.exe'])
        self.assertEqual(1, rebuild.call_count)
        self.assertFalse(after['reused'])
        self.assertFalse(after['native_layer_identity_migrated'])
        rebound = (self.runtime / index.PACK).read_bytes()
        self.assertNotEqual(original[64:], rebound[64:])
        self.assertIn(b'different-mip', rebound[64:])

    def test_corrupt_owned_pack_rebuilds_instead_of_rebinding(self):
        self.old_index(); expected = self.loading_derivative(); _, report = self.prepare()
        path = self.runtime / index.PACK
        raw = path.read_bytes()
        index.atomic_write(path, raw[:-1] + bytes([raw[-1] ^ 1]))
        with patch.object(index, 'make_pack', wraps=index.make_pack) as rebuild:
            after, _ = self.upgraded_index(report, expected['files']['CityOfHeroes.exe'])
        self.assertEqual(1, rebuild.call_count)
        self.assertFalse(after['reused'])
        self.assertFalse(after['native_layer_identity_migrated'])

    def test_interrupted_index_envelope_recovers_without_header_decoding(self):
        _, raw = self.old_index(); expected = self.loading_derivative(); _, report = self.prepare()
        original = index.atomic_write
        def interrupt(path, data):
            if path.name == index.MARKER: raise OSError('Interrupted index marker')
            return original(path, data)
        with patch.object(index, 'atomic_write', side_effect=interrupt), \
                patch.object(index, 'make_pack', side_effect=AssertionError('Unexpected header decoding')):
            self.upgraded_index(report, expected['files']['CityOfHeroes.exe'])
        with patch.object(index, 'make_pack', side_effect=AssertionError('Unexpected header decoding')):
            after, _ = self.upgraded_index(self.prepare()[1], expected['files']['CityOfHeroes.exe'])
        self.assertTrue(after['reused'])
        self.assertTrue(after['native_layer_identity_migrated'])
        self.assertTrue(after['interrupted_envelope_recovered'])
        self.assertEqual(raw[64:], (self.runtime / index.PACK).read_bytes()[64:])


if __name__ == '__main__': unittest.main()
