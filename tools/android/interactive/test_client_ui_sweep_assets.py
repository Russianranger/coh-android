#!/usr/bin/env python3
"""Native UI sweep, historical conservation and exact guest partition regressions."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest

import discover_client_ui_sweep_assets as discovery
import prepare_client_ui_sweep_assets as producer
import prepare_client_ui_repair_assets as ancestor

sys.path.insert(0, str(producer.ROOT/'android/guest'))
import client_visual_assets as guest
from diagnostic import DiagnosticError


class NativeInterfaceScope(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.requests = discovery.source_requests()

    def test_frozen_complete_source_graph_reproduces(self):
        frozen = json.loads(producer.requests_bytes(producer.ROOT/'assets'/producer.SOURCE_REQUESTS))
        self.assertEqual(json.loads(discovery.canonical(self.requests)), frozen)

    def test_all184_native_interface_modules_and2551_enhancement_definitions_are_audited(self):
        sources = self.requests['source_files']
        ui = [name for name in sources if name.startswith(discovery.UI_DIRECTORY + '/') and name.endswith('.c')]
        enhancements = [name for name in sources if '/powers/boosts_' in name]
        self.assertEqual(len(ui), 184)
        self.assertEqual(len(enhancements), 2551)
        self.assertFalse(self.requests['full_global_asset_closure'])

    def test_tip_variables_and_enhancement_overlay_rings_are_covered(self):
        keys = self.requests['textures']
        self.assertTrue({'pop_help_icon_on_alert', 'pop_help_icon_on_alert_glow',
            'pop_help_icon_off_blue', 'enhnctray_ring', 'enhnctray_ring_highlight',
            'e_icon_gen_accuracy_01', 'e_pog_accuracy'} <= set(keys))
        for key in ('pop_help_icon_on_alert', 'pop_help_icon_off_blue'):
            self.assertTrue(any(row.get('native_request') == 'variable_texture_literal' for row in keys[key]))

    def test_npc_name_bar_and_tooltip_shared_frame_dependencies_are_covered(self):
        keys = self.requests['textures']
        self.assertTrue({'conning_arrow', 'bar_health', 'bar_endurance', 'bar_gray',
            'bar_background', 'frame_2px_4r_ul', 'frame_2px_4r_background_ul'} <= set(keys))
        self.assertTrue(any(row.get('constructor_source', '').endswith('uiUtilGame.c')
            for row in keys['frame_2px_4r_ul']))

    def test_native_arrays_and_pressed_button_layers_are_covered(self):
        keys = self.requests['textures']
        self.assertIn('map_enticon_hospital', keys)
        self.assertTrue(any(row.get('native_array') == 'iconChoices'
            for row in keys['map_enticon_hospital']))
        for part in ('l', 'r', 'mid'):
            for layer in ('highlight', 'meat', 'shadow', 'dropshadow'):
                self.assertIn(f'genericbutton_press_{part}_{layer}', keys)

    def test_comment_markers_inside_filenames_do_not_erase_following_ui(self):
        text = 'load("texture_library/maps/*/%s"); /* removed */ load("next.tga"); // removed\n'
        clean = discovery.uncomment(text)
        self.assertIn('"texture_library/maps/*/%s"', clean)
        self.assertIn('"next.tga"', clean)
        self.assertNotIn('removed', clean)
        self.assertEqual(len(text), len(clean))

    def test_native_atlas_and_texfind_remove_two_tga_suffixes_in_order(self):
        keys = self.requests['textures']
        self.assertNotIn('costume_button_link_glow.tga', keys)
        self.assertTrue(any(row['target'] == 'costume_button_link_glow.tga.tga'
            for row in keys['costume_button_link_glow']))

    def test_blank_level2_training_third_pane_is_native_pool_epic_schedule(self):
        self.assertEqual(self.requests['training_third_pane'],
            'native_pool_and_epic_choices_first_available_at_display_levels_4_and_35')
        self.assertIn('upstream/i24/data/defs/schedules.def', self.requests['source_files'])

    def test_ui_contact_geometry_is_existing_exact_three_model_closure(self):
        audit = self.requests['ui_contact_geometry_audit']
        self.assertEqual(audit['geometry'], 'data/object_library/iconsandui/icons_contact.geo')
        self.assertEqual(len(audit['models']), 3)
        self.assertTrue(audit['existing_geometry_preserved'])
        self.assertFalse(audit['mesh_or_skinning_execution_validated'])
        composite = self.requests['stock_composite_aliases']['x_icon_contact_missioncompleted']
        self.assertTrue(composite['composite_generation']['composite_alias_can_be_created'])
        self.assertEqual({row['alias'] for row in composite['edges']},
            {'MissionCompleted', 'Generic_Scroll_Offset3.tga', 'Mission_BumpMap.tga'})


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

    def test_current_native_graph_closes788_original_texture_leaves(self):
        names = producer.ui_files(self.value)
        self.assertEqual(len(names), 788)
        self.assertTrue(all(name.endswith('.texture') for name in names))
        self.assertEqual(sum(self.value['files'][name]['bytes'] for name in names), 23704759)

    def test_all9613_ancestral_rows_requests_and_receipts_are_exact(self):
        self.assertEqual(producer.ancestor_projection(self.value, self.old), self.old)
        self.assertEqual(len(self.old['files']), 9613)

    def test_prior_texture_byte_identity_cannot_change(self):
        changed = copy.deepcopy(self.value)
        changed['files'][next(iter(self.old['files']))]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'exact accepted 0.13.13 recipe'):
            producer.ancestor_projection(changed, self.old)

    def test_prior_source_witness_cannot_change(self):
        changed = copy.deepcopy(self.value)
        changed['source_files'][next(iter(self.old['source_files']))]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'exact accepted 0.13.13 recipe'):
            producer.ancestor_projection(changed, self.old)

    def test_prior_native_geometry_proof_cannot_change(self):
        changed = copy.deepcopy(self.value)
        changed['appearance_extension']['requested_model_proof'].clear()
        with self.assertRaisesRegex(ValueError, 'exact accepted 0.13.13 recipe'):
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
                changed['ui_sweep_extension'][key] = True
                with self.assertRaisesRegex(ValueError, 'preservation policy'):
                    producer.ui_files(changed)

    def test_native_request_target_cannot_change(self):
        changed = copy.deepcopy(self.value)
        name = next(iter(changed['ui_sweep_extension']['files']))
        changed['requests'][name][0]['target'] = 'unrelated.tga'
        with self.assertRaisesRegex(ValueError, 'exact native source requests'):
            producer.ui_files(changed)

    def test_previous_five_exact_unavailable_stems_remain_visible(self):
        names = {row['target'] for row in self.value['ui_sweep_extension']['unresolved_dependencies']}
        self.assertEqual(len(names), 23)
        self.assertTrue({'checkbar_meat_base_underlight_l', 'checkbar_meat_base_underlight_mid',
            'checkbar_meat_base_underlight_r', 'checkbox_base_underlight', 'default_tray'} <= names)
        self.assertNotIn('x_icon_contact_missioncompleted', names)

    def test_new_ui_resources_are_additions_without_altering_existing_ringhole(self):
        stems = {Path(name).stem for name in producer.ui_files(self.value)}
        self.assertTrue({'enhnctray_ring', 'enhnctray_ring_highlight', 'pop_help_icon_on_alert',
            'pop_help_icon_on_alert_glow', 'pop_help_icon_off_blue', 'conning_arrow',
            'bar_health', 'bar_endurance', 'bar_gray'} <= stems)
        ringhole = 'data/texture_library/gui/creation/enhancements/enhnctray_ringhole.texture'
        self.assertEqual(self.value['files'][ringhole], self.old['files'][ringhole])
        self.assertNotIn(ringhole, producer.ui_files(self.value))

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

    def test_all_current_and_historical_partitions_remain_disjoint_and_complete(self):
        ui = guest.ui_sweep_files(self.value)
        old = guest.ui_sweep_ancestor(self.value)
        self.assertEqual(len(ui), 788)
        self.assertEqual(len(old['files']), 9613)
        self.assertFalse(ui.intersection(old['files']))
        self.assertEqual(ui | set(old['files']), set(self.value['files']))
        old_ui = guest.ui_repair_files(old)
        historical = guest.ui_repair_ancestor(old)
        self.assertEqual(len(old_ui), 123)
        self.assertEqual(len(historical['files']), 9490)
        self.assertEqual(len(guest.appearance_files(historical)), 4014)
        self.assertEqual(len(guest.sweep_files(historical)), 5147)
        self.assertEqual(len(guest.encounter_files(historical)), 6)

    def test_guest_packages_exact_plaintext_current_recipe(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = producer.manifest_bytes(producer.ROOT/'assets'/producer.SOURCE_MANIFEST)
            (Path(directory)/guest.MANIFEST).write_bytes(raw)
            value = guest.package(directory)
        self.assertEqual(value['files'], self.value['files'])

    def test_expanded_real_inventory_still_fits_persistent_receipt_bound(self):
        outputs = {name: {'path': name, 'stat': [2**64 - 1, 2**64 - 1, row['bytes'],
            guest.client.CACHE_EPOCH * 10**9, 2**63 - 1, stat.S_IFREG | 0o444,
            2**32 - 1, 2**32 - 1, 1]} for name, row in self.value['files'].items()}
        # Conservative maximum-width stat values and path overhead protect the
        # real 10,401-file expansion; small synthetic installer fixtures alone
        # cannot catch a receipt growing beyond its existing 4 MiB bound.
        receipt = {'outputs': outputs, 'identity': {'worktree': 'x' * 4096},
            'inputs': {guest.ARCHIVE: [2**64 - 1] * 9, guest.MANIFEST: [2**64 - 1] * 9}}
        self.assertLess(len(guest.canonical(receipt)), guest.MAX_RECEIPT_BYTES)

    def test_guest_rejects_ui_drift_with_top_current_identity_unchanged(self):
        changed = copy.deepcopy(self.value)
        name = next(iter(changed['ui_sweep_extension']['files']))
        changed['files'][name]['sha256'] = '0' * 64
        with self.assertRaisesRegex(DiagnosticError, 'Client UI sweep changes'):
            guest.ui_sweep_files(changed)

    def test_guest_rejects_ancestral_drift_with_top_current_identity_unchanged(self):
        changed = copy.deepcopy(self.value)
        names = set(changed['files']) - set(changed['ui_sweep_extension']['files'])
        changed['files'][next(iter(names))]['sha256'] = '0' * 64
        with self.assertRaisesRegex(DiagnosticError, 'Client UI sweep changes'):
            guest.ui_sweep_files(changed)

    def test_guest_missing_ui_partition_cannot_use_historical_policy(self):
        changed = copy.deepcopy(self.value)
        del changed['ui_sweep_extension']
        with self.assertRaisesRegex(DiagnosticError, 'Client UI sweep changes'):
            guest.ui_sweep_ancestor(changed)

    def test_guest_cannot_claim_physical_ui_success(self):
        changed = copy.deepcopy(self.value)
        changed['ui_sweep_extension']['runtime_visual_validated'] = True
        with self.assertRaisesRegex(DiagnosticError, 'Client UI sweep changes'):
            guest.ui_sweep_files(changed)



if __name__ == '__main__':
    unittest.main()
