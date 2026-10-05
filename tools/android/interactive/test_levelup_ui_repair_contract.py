"""Exercise the actual fresh-runtime installer for the typed DbServer repair."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import package_levelup_ui_repair_dbserver as producer
from test_startup_bundle_dbserver import character, guest_fixture


class LevelupUiRepairGuestContractTests(unittest.TestCase):
    def fixture(self, root):
        assets, runtime, package, manifest, original, image, library = guest_fixture(root)
        manifest['role'] = producer.ROLE
        manifest['base_startup_bundle_executable'] = producer.BASE_STARTUP_BUNDLE_EXECUTABLE
        manifest['levelup_ui_repair_build_input'] = producer.expected_receipt(
            base_startup_build_input=manifest['build_input'],
            base_startup_bundle_build_input=manifest['startup_bundle_build_input'])
        return assets, runtime, package, manifest, original, image, library

    def install(self, values):
        assets, runtime, package, manifest, *_ = values
        (assets/'startup-dbserver-manifest.json').write_text(json.dumps(manifest))
        return character.install_manual_atlas_dbserver(assets, runtime, package)

    def test_current_source_receipt_matches_guest_exactly(self):
        package = json.loads((producer.ROOT/producer.retained.retained.ACCEPTED_BASE_MANIFEST).read_text())
        base = producer.retained.retained.expected_receipt(base_wine_build_input=package['wine_build_input'])
        bundle = producer.retained.expected_receipt(base_startup_build_input=base)
        self.assertEqual(character.levelup_ui_repair_build_input(base, bundle),
                         producer.expected_receipt(base_startup_build_input=base,
                             base_startup_bundle_build_input=bundle))

    def test_only_fresh_owned_dbserver_is_replaced_and_all_prior_contracts_survive(self):
        with tempfile.TemporaryDirectory() as temporary:
            values = self.fixture(Path(temporary))
            assets, runtime, package, manifest, original, image, library = values
            before = copy.deepcopy(package)
            installed = self.install(values)
            self.assertEqual((runtime/'DbServer.exe').read_bytes(), image)
            self.assertEqual((runtime/'retained.dll').read_bytes(), library)
            self.assertEqual(package, before)
            self.assertEqual(installed['startup_bundle_save'], producer.retained.save_contract())
            self.assertEqual(installed['levelup_ui_repair_save'], producer.save_contract())
            self.assertFalse(installed['native_ack_observed'])
            self.assertFalse(installed['other_native_targets_changed'])
            self.assertFalse(installed['base_package_archive_changed'])
            with self.assertRaisesRegex(character.base.DiagnosticError, 'fresh accepted DbServer'):
                self.install(values)

    def test_mutated_reader_fifo_merger_or_ancestry_refused_before_replacement(self):
        for field in ('patch_sha256', 'unchanged_fifo_sha256', 'unchanged_merger_sha256',
                      'base_startup_build_input_canonical_sha256',
                      'base_startup_bundle_build_input_canonical_sha256'):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                values = self.fixture(Path(temporary))
                values[3]['levelup_ui_repair_build_input'][field] = 'f'*64
                with self.assertRaisesRegex(character.base.DiagnosticError, 'read repair layer'):
                    self.install(values)
                self.assertEqual((values[1]/'DbServer.exe').read_bytes(), values[4])

    def test_untyped_or_relabelled_layer_and_changed_physical_policy_are_refused(self):
        changes = [lambda v: v['levelup_ui_repair_build_input'].update(extra='unreviewed'),
                   lambda v: v['levelup_ui_repair_build_input']['save_contract'].update(UPSERT=True),
                   lambda v: v['levelup_ui_repair_build_input'].update(postgresql_persistence_fixture=0),
                   lambda v: v.update(role=producer.retained.ROLE),
                   lambda v: v.update(base_startup_bundle_executable={'bytes': 1, 'sha256': 'f'*64}),
                   lambda v: v.pop('levelup_ui_repair_build_input')]
        for index, change in enumerate(changes):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as temporary:
                values = self.fixture(Path(temporary)); change(values[3])
                with self.assertRaises(character.base.DiagnosticError): self.install(values)
                self.assertEqual((values[1]/'DbServer.exe').read_bytes(), values[4])

    def test_unchanged_published_dbserver_cannot_masquerade_as_new_reader(self):
        with tempfile.TemporaryDirectory() as temporary:
            values = self.fixture(Path(temporary))
            values[3]['files']['DbServer.exe']['sha256'] = producer.BASE_STARTUP_BUNDLE_EXECUTABLE['sha256']
            with self.assertRaises(character.base.DiagnosticError): self.install(values)
            self.assertEqual((values[1]/'DbServer.exe').read_bytes(), values[4])


if __name__ == '__main__': unittest.main()
