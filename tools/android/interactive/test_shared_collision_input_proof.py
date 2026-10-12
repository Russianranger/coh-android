"""Same-process collision byte proofs never authorize substituted providers.

Tiny native-manifest fixtures exercise production installers; these tests do not
claim real native collision parity, device startup speed or saved gameplay.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest
from unittest import mock
import zipfile

import test_atlas_beacon_package as fixture
sys.path.insert(0, str(fixture.ROOT / 'android/guest'))
import kings_row_beacon_package as kings


class SharedCollisionInputProofTests(unittest.TestCase):
    def setUp(self):
        self.atlas = fixture.AtlasBeaconPackageTests()
        self.atlas.setUp()
        self.addCleanup(self.atlas.doCleanups)
        self.root, self.owner = self.atlas.root, self.atlas.root
        self.source = self.root / 'owned-import'
        self.other = self.root / 'owned-work'
        self.source.mkdir(); self.other.mkdir()
        selected = {**self.atlas.inputs, **self.atlas.required_geometry_inputs}
        for name, raw in selected.items():
            target = self.atlas.runtime / name
            donor = self.source / name
            donor.parent.mkdir(parents=True, exist_ok=True)
            donor.write_bytes(raw); donor.chmod(0o400)
            target.unlink(); target.symlink_to(donor)
        self.identity = {'format': 2, 'native_closure_sha256': 'a' * 64,
            'source_roots': [{'path': str(root), 'identity': {'device': root.stat().st_dev,
                'inode': root.stat().st_ino, 'uid': root.stat().st_uid}} for root in (self.source, self.other)],
            'client_inputs': {'import': {'sha256': 'b' * 64}}}
        self.proofs = []
        patch = mock.patch.object(kings, 'atlas', fixture.package)
        patch.start(); self.addCleanup(patch.stop)
        self.mint()
        self.runtime = self.root / 'kings-runtime'; self.runtime.mkdir()
        common = {name: raw for name, raw in self.atlas.inputs.items()
                  if name.startswith('data/object_library/')}
        self.raws = {**common, 'data/' + kings.MAP: b'owned Kings map fixture'}
        for name, raw in self.raws.items():
            target = self.runtime / name; target.parent.mkdir(parents=True, exist_ok=True)
            if name in common:
                target.symlink_to(self.source / name)
            else:
                target.write_bytes(raw); target.chmod(0o400)
        (self.runtime / 'data/tricks').mkdir()
        self.payloads = {kings.GRAPH: self.atlas.payloads[fixture.package.GRAPH],
                         kings.DATE: self.atlas.payloads[fixture.package.DATE]}
        self.value = {'format': 1, 'role': 'authentic_native_kings_row_beacon_graph',
            'source_commit': fixture.package.SOURCE_COMMIT, 'data_commit': fixture.package.DATA_COMMIT,
            'map': kings.MAP, 'map_id': 5, 'files': {name: self.pin(raw) for name, raw in self.payloads.items()},
            'input_files': {name: self.pin(raw) for name, raw in self.raws.items()},
            'native': dict(self.atlas.value['native'], native_collision_load_verified=True,
                           missing_groups=0, missing_root_models=0),
            'runtime_graph_readback': True, 'physical_zoning_verified': False}
        self.assets = self.root / 'kings-assets'; self.assets.mkdir()
        self.freeze_kings()

    @staticmethod
    def pin(raw):
        return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

    def mint(self):
        return fixture.package.install(self.atlas.archive, self.atlas.manifest, self.atlas.runtime,
            context=fixture.Context(), imported_inputs_readonly=True, input_proof_sink=self.proofs.append,
            source_cache_identity=self.identity, owner_root=self.owner)

    def freeze_kings(self):
        self.value['input_files_sha256'] = hashlib.sha256(fixture.package.canonical(self.value['input_files'])).hexdigest()
        self.value['input_profiles'] = {name: {'native': copy.deepcopy(self.value['native']),
            'input_files_sha256': self.value['input_files_sha256']} for name in kings.PROFILES}
        raw = fixture.package.canonical(self.value)
        (self.assets / kings.MANIFEST).write_bytes(raw)
        with zipfile.ZipFile(self.assets / kings.ARCHIVE, 'w') as archive:
            archive.writestr(kings.MANIFEST, raw)
            for name, payload in self.payloads.items(): archive.writestr(name, payload)
        (self.assets / kings.LOCK).write_bytes(fixture.package.canonical({'format': 1, 'map_id': 5,
            'manifest': self.pin(raw), 'archive': fixture.package.pin(self.assets / kings.ARCHIVE)}))

    def install(self, **extra):
        options = {'context': fixture.Context(), 'imported_inputs_readonly': True,
            'source_input_proof': self.proofs[-1], 'source_cache_identity': self.identity, 'owner_root': self.owner}
        options.update(extra)
        return kings.install(self.assets / kings.ARCHIVE, self.assets / kings.MANIFEST, self.runtime, **options)

    def common_name(self):
        return next(name for name in self.raws if name.startswith('data/object_library/'))

    def test_full_byte_proved_shared_links_hash_only_destination_delta(self):
        original = kings.pin; opened = []
        def tracked(path, *args):
            opened.append(Path(path)); return original(path, *args)
        with mock.patch.object(kings, 'pin', side_effect=tracked): result = self.install()
        common = [name for name in self.raws if name.startswith('data/object_library/')]
        self.assertEqual(result['input_full_byte_proof_reused_files'], len(common))
        self.assertEqual(result['input_full_byte_proof_reused_bytes'], sum(len(self.raws[name]) for name in common))
        self.assertEqual(result['input_payload_bytes_hashed'], len(self.raws['data/' + kings.MAP]))
        self.assertFalse(any(path == self.runtime / name for path in opened for name in common))
        self.assertEqual(result['installed_files'], 2)
        self.assertFalse(result['physical_zoning_verified'])

    def test_validated_warm_atlas_receipt_mints_same_process_authority_without_payload_rehash(self):
        with mock.patch.object(fixture.package, 'pin', wraps=fixture.package.pin) as pin:
            result = self.mint()
        self.assertEqual(result['status'], 'reused_verified_graph')
        self.assertEqual(result['input_payload_bytes_hashed'], 0)
        self.assertFalse(any(Path(call.args[0]) == self.atlas.runtime / name
            for call in pin.call_args_list for name in self.atlas.inputs))
        self.assertGreater(self.install()['input_full_byte_proof_reused_files'], 0)

    def test_json_or_absent_certificate_requires_all_destination_hashes(self):
        for proof in ({'format': 1, 'providers': {}}, None):
            with self.subTest(proof=proof):
                targets = dict(self.value['input_files'])
                # Use a fresh runtime because complete durable graph reuse is an
                # independent, already qualified path after the first install.
                self.remove_graph_receipt()
                result = self.install(source_input_proof=proof)
                self.assertEqual(result['input_full_byte_proof_reused_files'], 0)
                self.assertEqual(result['input_payload_bytes_hashed'], sum(row['bytes'] for row in targets.values()))

    def remove_graph_receipt(self):
        for name in (kings.GRAPH, kings.DATE, kings.MARKER):
            path = self.runtime / name
            path.unlink(missing_ok=True)

    def test_copied_equal_bytes_and_equal_bytes_provider_substitution_are_rehashed(self):
        name = self.common_name(); target = self.runtime / name
        for copied in (True, False):
            self.remove_graph_receipt(); target.unlink()
            if copied:
                target.write_bytes(self.raws[name]); target.chmod(0o400)
            else:
                donor = self.source / 'substitute.geo'
                donor.write_bytes(self.raws[name]); donor.chmod(0o400)
                target.symlink_to(donor)
            result = self.install()
            self.assertEqual(result['input_full_byte_proof_reused_files'], 100)
            self.assertEqual(result['input_payload_bytes_hashed'], len(self.raws[name]) + len(self.raws['data/' + kings.MAP]))

    def test_changed_source_with_restored_mtime_rehashes_and_refuses(self):
        name = self.common_name(); source = self.source / name; old = source.stat()
        source.chmod(0o600); source.write_bytes(b'X' * old.st_size)
        os.utime(source, ns=(old.st_atime_ns, old.st_mtime_ns)); source.chmod(0o400)
        with self.assertRaisesRegex(ValueError, 'Kings collision input differs'):
            self.install()
        self.assertFalse((self.runtime / kings.MARKER).exists())

    def test_wrong_generation_owner_or_atlas_contract_falls_back_to_full_hashes(self):
        other_owner = self.root / 'another-owner'; other_owner.mkdir()
        for changes in ({'source_cache_identity': dict(self.identity, client_inputs={'import': {'sha256': 'c' * 64}})},
                        {'owner_root': other_owner}):
            with self.subTest(changes=changes):
                self.remove_graph_receipt(); result = self.install(**changes)
                self.assertEqual(result['input_full_byte_proof_reused_files'], 0)
        self.remove_graph_receipt()
        object.__setattr__(self.proofs[-1], 'manifest_sha256', 'f' * 64)
        self.assertEqual(self.install()['input_full_byte_proof_reused_files'], 0)

    def test_changed_expected_logical_pin_is_not_granted_old_leaf_authority(self):
        name = self.common_name(); self.value['input_files'][name] = self.pin(b'other logical data')
        self.freeze_kings()
        with self.assertRaisesRegex(ValueError, 'Kings collision input differs'):
            self.install()

    def test_extra_provider_and_directory_symlink_refuse_before_any_byte_reuse(self):
        extra = self.runtime / 'data/object_library/foreign.geo'
        extra.write_bytes(b'foreign'); extra.chmod(0o400)
        with self.assertRaisesRegex(ValueError, 'inventory'): self.install()
        extra.unlink(); directory = self.runtime / 'data/object_library/foreign'
        directory.symlink_to(self.source, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, '[Ll]inked'): self.install()
        self.assertFalse((self.runtime / kings.MARKER).exists())

    def test_reordered_manifest_input_inventory_keeps_exact_proofs(self):
        self.value['input_files'] = dict(reversed(list(self.value['input_files'].items())))
        self.freeze_kings()
        self.assertEqual(self.install()['input_full_byte_proof_reused_files'], 101)

    def test_certificate_cannot_be_modified_or_minted_from_json(self):
        proof = self.proofs[-1]
        with self.assertRaises(AttributeError): proof.manifest_sha256 = 'f' * 64
        with self.assertRaises(TypeError): proof.pins[self.common_name()]['sha256'] = 'f' * 64
        with self.assertRaises(TypeError): proof.providers[self.common_name()]['inode'] = 123
        with self.assertRaisesRegex(ValueError, 'completed Atlas proof'):
            fixture.package.VerifiedCollisionInputs(object(), 'f' * 64, 'f' * 64, {}, {}, {})

    def test_provider_retarget_to_existing_same_inode_alias_during_proof_is_refused(self):
        name = self.common_name(); alias = self.source / 'same-inode-alias.geo'
        os.link(self.source / name, alias)
        self.mint()  # Bind the preexisting shared inode link count before borrowing.
        original = kings.pin; changed = False
        def retarget(path, *args):
            nonlocal changed
            result = original(path, *args)
            if Path(path) == self.runtime / ('data/' + kings.MAP) and not changed:
                target = self.runtime / name; target.unlink(); target.symlink_to(alias)
                changed = True
            return result
        with mock.patch.object(kings, 'pin', side_effect=retarget):
            with self.assertRaisesRegex(ValueError, 'Kings inputs changed'):
                self.install()
        self.assertFalse((self.runtime / kings.MARKER).exists())

    def test_destination_mutation_after_byte_selection_is_refused_before_receipt(self):
        name = self.common_name(); source = self.source / name
        original = kings.pin; changed = False
        def mutate(path, *args):
            nonlocal changed
            result = original(path, *args)
            if Path(path) == self.runtime / ('data/' + kings.MAP) and not changed:
                source.chmod(0o600); source.write_bytes(b'X' * len(self.raws[name])); source.chmod(0o400)
                changed = True
            return result
        with mock.patch.object(kings, 'pin', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'Kings inputs changed'):
                self.install()
        self.assertFalse((self.runtime / kings.MARKER).exists())


if __name__ == '__main__': unittest.main()
