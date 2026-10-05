#!/usr/bin/env python3
"""Finite UI dependency, append conservation and original-stream regressions."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import discover_client_ui_repair_assets as discovery
import prepare_client_ui_repair_assets as producer
import prepare_client_appearance_assets as ancestor

sys.path.insert(0, str(producer.ROOT/'android/guest'))
import client_visual_assets as guest
from diagnostic import DiagnosticError


class FiniteNativeRequests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.requests = discovery.source_requests()

    def test_frozen_source_graph_reproduces_exact_requests(self):
        frozen = json.loads(producer.requests_bytes(producer.ROOT/'assets'/producer.SOURCE_REQUESTS))
        self.assertEqual(json.loads(discovery.canonical(self.requests)), frozen)

    def test_xp_filled_and_empty_native_ranges_close(self):
        keys = self.requests['textures']
        for prefix in ('healthbar_exp_dot_', 'healthbar_exp_dot_empty_'):
            actual = {key for key in keys if key.startswith(prefix) and key[len(prefix):].isdigit()}
            self.assertEqual(actual, {prefix + f'{number:02d}' for number in range(1, 11)})

    def test_all_five_inspiration_columns_have_native_key_labels(self):
        keys = {key for key in self.requests['textures'] if key.startswith('tray_ring_number_f')}
        self.assertEqual(keys, {'tray_ring_number_f' + str(number) for number in range(1, 6)})

    def test_standard_inspiration_icons_have_definition_witnesses(self):
        icons = {key: rows for key, rows in self.requests['textures'].items()
            if key.startswith('inspiration_')}
        self.assertEqual(len(icons), 27)
        for rows in icons.values():
            self.assertTrue(all(row['definition_field'] == 'IconName' for row in rows))
            self.assertTrue(all('inspirations_' in row['source_path'] for row in rows))

    def test_existing_archery_and_devices_remain_definitions_only(self):
        definitions = {row['source_path'] for rows in self.requests['textures'].values()
            for row in rows if row.get('definition_field') == 'IconName'}
        self.assertIn('upstream/i24/data/defs/powers/blaster_ranged_archery.powers', definitions)
        self.assertIn('upstream/i24/data/defs/powers/blaster_support_gadgets.powers', definitions)
        self.assertTrue(self.requests['no_per_row_power_icon_change'])

    def test_comment_and_string_braces_do_not_escape_function_scope(self):
        text = 'void target() { /* } */ if (ok) { use("{"); } }\nvoid other() { }'
        body, first = discovery.function_span(text, 'target')
        self.assertEqual(first, 1)
        self.assertIn('use("{")', body)
        self.assertNotIn('other', body)

    def test_missing_finite_function_is_not_silently_skipped(self):
        with self.assertRaisesRegex(ValueError, 'Missing finite native UI function'):
            discovery.function_span('void other() {}', 'target')

    def test_unclosed_native_function_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unclosed finite native UI function'):
            discovery.function_span('void target() { if (ok) {}', 'target')


class ExactNamespacePlan(unittest.TestCase):
    def rows(self, **sizes):
        return {'texture_library/gui/' + stem + '.texture': {'bytes': size}
            for stem, size in sizes.items()}

    def requests(self, *stems):
        return {'textures': {stem: [{'source': 'exact'}] for stem in stems}}

    def test_missing_only_plan_does_not_replace_existing_leaf(self):
        value = discovery.plan(self.rows(old=10, new=20), self.requests('old', 'new'),
            {'data/texture_library/gui/old.texture'})
        self.assertEqual(set(value['selected']), {'data/texture_library/gui/new.texture'})
        self.assertEqual(value['existing_leaf_dependencies'][0]['target'], 'old')

    def test_absent_exact_original_stays_visible_without_substitution(self):
        value = discovery.plan(self.rows(new=10, nearly_missing=20), self.requests('new', 'missing'), set())
        self.assertEqual(set(value['selected']), {'data/texture_library/gui/new.texture'})
        self.assertEqual(value['unresolved_dependencies'][0]['target'], 'missing')

    def test_ambiguous_native_basename_is_rejected(self):
        files = self.rows(new=10) | {'texture_library/other/new.texture': {'bytes': 10}}
        with self.assertRaisesRegex(ValueError, 'Ambiguous exact UI basename'):
            discovery.plan(files, self.requests('new'), set())

    def test_payload_bound_rejects_unbounded_reimport(self):
        with self.assertRaisesRegex(ValueError, 'exceeds finite reviewed bounds'):
            discovery.plan(self.rows(new=discovery.MAX_NEW_PAYLOAD_BYTES + 1), self.requests('new'), set())

    def test_leaf_count_bound_rejects_scope_expansion(self):
        names = {'t' + str(number): 1 for number in range(discovery.MAX_ADDITIONS + 1)}
        with self.assertRaisesRegex(ValueError, 'exceeds finite reviewed bounds'):
            discovery.plan(self.rows(**names), self.requests(*names), set())


class FrozenAppend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = producer.read_manifest(producer.ROOT/'assets'/producer.SOURCE_MANIFEST)
        cls.old = ancestor.read_manifest(producer.ROOT/'assets'/ancestor.SOURCE_MANIFEST)

    def test_current_native_graph_closes123_original_texture_leaves(self):
        names = producer.ui_files(self.value)
        self.assertEqual(len(names), 123)
        self.assertTrue(all(name.endswith('.texture') for name in names))
        self.assertEqual(sum(self.value['files'][name]['bytes'] for name in names), 5384150)

    def test_all9490_ancestral_rows_requests_and_receipts_are_exact(self):
        self.assertEqual(producer.ancestor_projection(self.value, self.old), self.old)
        self.assertEqual(len(self.old['files']), 9490)

    def test_prior_texture_byte_identity_cannot_change(self):
        changed = copy.deepcopy(self.value)
        changed['files'][next(iter(self.old['files']))]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'exact accepted 0.13.11 recipe'):
            producer.ancestor_projection(changed, self.old)

    def test_prior_source_witness_cannot_change(self):
        changed = copy.deepcopy(self.value)
        changed['source_files'][next(iter(self.old['source_files']))]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'exact accepted 0.13.11 recipe'):
            producer.ancestor_projection(changed, self.old)

    def test_prior_native_geometry_proof_cannot_change(self):
        changed = copy.deepcopy(self.value)
        changed['appearance_extension']['requested_model_proof'].clear()
        with self.assertRaisesRegex(ValueError, 'exact accepted 0.13.11 recipe'):
            producer.ancestor_projection(changed, self.old)

    def test_dropping_an_old_leaf_is_rejected(self):
        changed = copy.deepcopy(self.value)
        del changed['files'][next(iter(self.old['files']))]
        with self.assertRaisesRegex(ValueError, 'ancestor leaf partition'):
            producer.ancestor_projection(changed, self.old)

    def test_adding_unreviewed_archive_leaf_is_rejected(self):
        changed = copy.deepcopy(self.value)
        changed['files']['data/texture_library/gui/unreviewed.texture'] = {'bytes': 1, 'sha256': '0'*64}
        with self.assertRaisesRegex(ValueError, 'ancestor leaf partition'):
            producer.ancestor_projection(changed, self.old)

    def test_policy_flags_cannot_claim_visual_or_gameplay_qualification(self):
        for key in ('runtime_visual_validated', 'native_renderer_changed', 'native_gameplay_changed',
                'full_global_asset_closure', 'preloading', 'full_archive_verified'):
            with self.subTest(key=key):
                changed = copy.deepcopy(self.value)
                changed['ui_repair_extension'][key] = True
                with self.assertRaisesRegex(ValueError, 'preservation policy'):
                    producer.ui_files(changed)

    def test_native_request_target_cannot_change(self):
        changed = copy.deepcopy(self.value)
        name = next(iter(changed['ui_repair_extension']['files']))
        changed['requests'][name][0]['target'] = 'unrelated.tga'
        with self.assertRaisesRegex(ValueError, 'exact native source requests'):
            producer.ui_files(changed)

    def test_unresolved_exact_names_remain_finite_and_explicit(self):
        names = {row['target'] for row in self.value['ui_repair_extension']['unresolved_dependencies']}
        self.assertEqual(names, {'checkbar_meat_base_underlight_l', 'checkbar_meat_base_underlight_mid',
            'checkbar_meat_base_underlight_r', 'checkbox_base_underlight', 'default_tray'})

    def test_source_envelope_reproduces_exact_plaintext(self):
        raw = producer.manifest_bytes(producer.ROOT/'assets'/producer.SOURCE_MANIFEST)
        self.assertEqual({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}, producer.MANIFEST_PIN)

    def test_changed_frozen_request_bytes_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'requests.json'
            path.write_bytes(b'{"unreviewed":true}\n')
            with self.assertRaisesRegex(ValueError, 'frozen requests differ'):
                producer.requests_bytes(path)


class GuestCurrentPartition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = json.loads(producer.manifest_bytes(producer.ROOT/'assets'/producer.SOURCE_MANIFEST))

    def test_guest_identity_is_exact_current_producer_identity(self):
        self.assertEqual((guest.FILE_COUNT, guest.PAYLOAD_BYTES, guest.ARCHIVE_BYTES,
            guest.ARCHIVE_SHA256, guest.MANIFEST_SHA256, guest.FILES_SHA256),
            (producer.FILE_COUNT, producer.PAYLOAD_BYTES, producer.ARCHIVE_PIN['bytes'],
             producer.ARCHIVE_PIN['sha256'], producer.MANIFEST_PIN['sha256'], producer.FILES_SHA256))

    def test_guest123_ui_and9490_ancestor_partition_is_disjoint_and_complete(self):
        ui = guest.ui_repair_files(self.value)
        old = guest.ui_repair_ancestor(self.value)
        self.assertEqual(len(ui), 123)
        self.assertEqual(len(old['files']), 9490)
        self.assertFalse(ui.intersection(old['files']))
        self.assertEqual(ui | set(old['files']), set(self.value['files']))
        self.assertEqual(len(guest.appearance_files(old)), 4014)
        self.assertEqual(len(guest.sweep_files(old)), 5147)
        self.assertEqual(len(guest.encounter_files(old)), 6)

    def test_guest_packages_exact_plaintext_recipe(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = producer.manifest_bytes(producer.ROOT/'assets'/producer.SOURCE_MANIFEST)
            (Path(directory)/guest.MANIFEST).write_bytes(raw)
            value = guest.package(directory)
        self.assertEqual(value['files'], self.value['files'])

    def test_guest_rejects_ui_byte_drift_with_top_current_identity_unchanged(self):
        changed = copy.deepcopy(self.value)
        name = next(iter(changed['ui_repair_extension']['files']))
        changed['files'][name]['sha256'] = '0' * 64
        with self.assertRaisesRegex(DiagnosticError, 'Client UI repair changes'):
            guest.ui_repair_files(changed)

    def test_guest_rejects_ancestral_byte_drift_with_top_current_identity_unchanged(self):
        changed = copy.deepcopy(self.value)
        names = set(changed['files']) - set(changed['ui_repair_extension']['files'])
        changed['files'][next(iter(names))]['sha256'] = '0' * 64
        with self.assertRaisesRegex(DiagnosticError, 'Client UI repair changes'):
            guest.ui_repair_files(changed)

    def test_guest_missing_ui_partition_cannot_silently_use_historical_policy(self):
        changed = copy.deepcopy(self.value)
        del changed['ui_repair_extension']
        with self.assertRaisesRegex(DiagnosticError, 'Client UI repair changes'):
            guest.ui_repair_ancestor(changed)

    def test_guest_cannot_claim_physical_ui_success(self):
        changed = copy.deepcopy(self.value)
        changed['ui_repair_extension']['runtime_visual_validated'] = True
        with self.assertRaisesRegex(DiagnosticError, 'Client UI repair changes'):
            guest.ui_repair_files(changed)


if __name__ == '__main__':
    unittest.main()
