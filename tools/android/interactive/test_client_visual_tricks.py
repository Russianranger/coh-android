#!/usr/bin/env python3
"""Check stock material generation boundaries and safe dependency discovery."""
import unittest
from client_visual_tricks import (texture_stem, trick_name, parse_texture_tricks_text,
    resolve_trick_closure)


class StockMaterialDependencies(unittest.TestCase):
    def parse(self, text, path='upstream/i24/data/tricks/fixture.txt'):
        rows = parse_texture_tricks_text(text, path)
        indexed = {}
        for row in rows:
            indexed.setdefault(trick_name(row['name']).casefold(), []).append(row)
        return indexed

    def aliases(self, indexed, name='x_fixture'):
        return [edge['alias'] for edge in indexed[name][0]['edges']]

    def test_enabled_fallback_requires_all_three_slots(self):
        indexed = self.parse('''Texture X_fixture
 Base1 first.tga
 Multiply1 detail.tga
 Fallback
  UseFallback 1
  Base fallback_base.tga
  Blend fallback_blend.tga
  BumpMap fallback_normal.tga
 End
End
Texture next
 Blend next_blend.tga
End''')
        self.assertEqual(self.aliases(indexed), ['first.tga', 'detail.tga',
            'fallback_base.tga', 'fallback_blend.tga', 'fallback_normal.tga'])
        self.assertEqual(self.aliases(indexed, 'next'), ['next_blend.tga'])

    def test_disabled_fallback_does_not_create_unneeded_donor_requests(self):
        indexed = self.parse('''Texture X_fixture
 Base1 first.tga
 Fallback
  UseFallback 0
  Base unused.tga
 End
End''')
        self.assertEqual(self.aliases(indexed), ['first.tga'])

    def test_white_or_absent_mask_clears_secondary_layers(self):
        for mask in ('', ' Mask WHITE.tga', ' Mask None', ' Mask white.foo',
                ' Mask WHITE.unrecognized'):
            with self.subTest(mask=mask):
                indexed = self.parse('''Texture X_fixture
 Base1 primary.tga
 AddGlow1 glow.tga
 Base2 unused_base.tga
 Multiply2 unused_multiply.tga
 DualColor2 unused_dual.tga
 BumpMap2 unused_normal.tga
''' + mask + '\nEnd')
                self.assertEqual(self.aliases(indexed), ['primary.tga', 'glow.tga'])

    def test_meaningful_mask_preserves_secondary_layers(self):
        indexed = self.parse('''Texture X_fixture
 Base1 primary.tga
 Mask mask.tga
 Base2 secondary.tga
End''')
        self.assertEqual(self.aliases(indexed), ['primary.tga', 'mask.tga', 'secondary.tga'])

    def test_fancy_water_retains_secondary_layers_without_mask(self):
        for mask in ('', ' Mask None'):
            indexed = self.parse('''Texture X_fixture
 Base1 primary.tga
 Base2 water_secondary.tga
 ObjFlags FancyWater
''' + mask + '\nEnd')
            self.assertEqual(self.aliases(indexed), ['primary.tga', 'water_secondary.tga'])

    def test_placeholder_and_comment_names_are_excluded(self):
        indexed = self.parse('''#Texture fake
Texture X_fixture // native material
 Base1 real.tga
 Multiply1 None
 DualColor1 SWAPPABLE
 CubeMap %dynamic%
 BumpMap1 TEXTURE_NAME_placeholder
 #Blend commented.tga
End''')
        self.assertEqual(self.aliases(indexed), ['real.tga'])

    def test_exact_extensions_and_bang_are_normalized_without_fuzzy_names(self):
        self.assertEqual(texture_stem('!Folder/Real.Texture'), 'real')
        self.assertEqual(texture_stem('Real.tga'), 'real')
        self.assertEqual(texture_stem('Real_normal'), 'real_normal')

    def test_original_non_tga_extensions_follow_native_lookup(self):
        for extension in ('psd', 'ifl', 'xyz', 'texture', 'abcdefg'):
            self.assertEqual(texture_stem('!Original.' + extension), 'original')
        self.assertEqual(texture_stem('Original.extension'), 'original.extension')
        self.assertEqual(texture_stem('!!Original.tga'), '!original')

    def test_nested_material_closure_retains_source_edges(self):
        indexed = self.parse('''Texture X_first
 Base1 X_second
 Multiply1 first_detail.tga
End
Texture X_second
 Base1 second_base.tga
 BumpMap1 second_normal.tga
End''')
        result = resolve_trick_closure(indexed, {'x_first': [{'scope': 'runtime_missing',
            'target': 'X_first', 'alias': 'X_first', 'console_line': 42}]})
        self.assertEqual(set(result['requests']), {'x_first', 'x_second',
            'first_detail', 'second_base', 'second_normal'})
        self.assertEqual(len(result['stock_definition_closure']), 2)
        self.assertEqual(result['requests']['second_normal'][0]['source_line'], 7)
        self.assertFalse(result['runtime_visual_success_claimed'])

    def test_ambiguous_stock_definitions_are_not_guessed(self):
        indexed = self.parse('Texture X_fixture\n Base1 first.tga\nEnd')
        other = self.parse('Texture X_fixture\n Base1 second.tga\nEnd', 'other.txt')
        indexed['x_fixture'].extend(other['x_fixture'])
        result = resolve_trick_closure(indexed, {'x_fixture': [{'alias': 'X_fixture'}]})
        self.assertEqual(set(result['requests']), {'x_fixture'})
        self.assertEqual(len(result['ambiguous_stock_definitions']), 1)

    def test_console_exact_source_can_disambiguate_definition(self):
        indexed = self.parse('Texture X_fixture\n Base1 first.tga\nEnd')
        other = self.parse('Texture X_fixture\n Base1 second.tga\nEnd', 'other.txt')
        indexed['x_fixture'].extend(other['x_fixture'])
        result = resolve_trick_closure(indexed, {'x_fixture': [{'alias': 'X_fixture',
            'source_path': 'OTHER.TXT'}]})
        self.assertEqual(set(result['requests']), {'x_fixture', 'second'})
        self.assertEqual(result['ambiguous_stock_definitions'], [])

    def test_cycle_is_bounded_and_reported(self):
        indexed = self.parse('''Texture X_first
 Base1 X_second
End
Texture X_second
 Base1 X_first
End''')
        result = resolve_trick_closure(indexed, {'x_first': [{'alias': 'X_first'}]})
        self.assertEqual(len(result['stock_definition_closure']), 2)
        self.assertEqual(len(result['cycles']), 1)

    def test_exact_native_leaf_backedge_is_not_an_unresolved_alias_cycle(self):
        indexed = self.parse('Texture native_base\n Base1 native_base.tga\nEnd')
        result = resolve_trick_closure(indexed,
            {'native_base': [{'alias': 'native_base'}]},
            native_texture_names=['native_base'])
        self.assertEqual(result['cycles'], [])
        self.assertEqual(len(result['native_leaf_backedges']), 1)
        self.assertTrue(result['native_leaf_backedges'][0]['exact_donor_leaf_present'])

    def test_native_extension_normalization_is_applied_once_to_original_aliases(self):
        indexed = self.parse('''Texture X_marker
 Base1 volumemarker._yellow.tga
End
Texture volumemarker._yellow.tga
 Base1 volumemarker._yellow.tga
End''')
        result = resolve_trick_closure(indexed, {
            'x_marker': [{'alias': 'X_marker'}],
            'volumemarker._yellow': [{'alias': 'volumemarker._yellow.tga'}]},
            native_texture_names=['volumemarker._yellow'])
        self.assertIn('volumemarker._yellow', result['requests'])
        self.assertNotIn('volumemarker', result['requests'])
        self.assertEqual(len(result['native_leaf_backedges']), 1)
        self.assertEqual(result['cycles'], [])

    def test_declaration_suffix_rule_differs_from_native_texture_binding_rule(self):
        indexed = self.parse('Texture Shield_Arctic_01.tg\n Blend detail.tga\nEnd')
        self.assertIn('shield_arctic_01', indexed)
        self.assertEqual(texture_stem('Shield_Arctic_01.tg'), 'shield_arctic_01.tg')
        self.assertEqual(trick_name('/ui/'), 'ui/')

    def test_trick_geometry_fields_do_not_become_texture_edges(self):
        indexed = self.parse('''Trick geometry
 LodFar 50
 AutoLOD
  ModelName geometry_model
 End
End
Texture X_fixture
 Base1 texture.tga
End''')
        self.assertEqual(set(indexed), {'x_fixture'})

    def test_repeated_slot_uses_last_native_value_including_none(self):
        indexed = self.parse('''Texture X_fixture
 Base1 obsolete.tga
 Base1 actual.tga
 AddGlow1 unused.tga
 AddGlow1 None
End''')
        self.assertEqual(self.aliases(indexed), ['actual.tga'])
        self.assertEqual(indexed['x_fixture'][0]['composite_generation']['base1'], 'actual.tga')

    def test_deprecated_and_current_bumpmap_names_write_the_same_native_slot(self):
        indexed = self.parse('''Texture X_fixture
 Base1 base.tga
 BumpMap obsolete.tga
 BumpMap1 None
 Fallback
  UseFallback 1
  BumpMap retained_fallback.tga
 End
End''')
        self.assertEqual(self.aliases(indexed), ['base.tga', 'retained_fallback.tga'])

    def test_source_definition_alone_does_not_prove_generated_material(self):
        indexed = self.parse('''Texture native_base.tga
 Base1 native_base.tga
End
Texture old_texture
 Blend detail.tga
End
Texture X_fixture
 Base1 real_base.tga
End''')
        for name in ('native_base', 'old_texture'):
            self.assertFalse(indexed[name][0]['composite_generation']['composite_alias_can_be_created'])
        self.assertTrue(indexed['x_fixture'][0]['composite_generation']['composite_alias_can_be_created'])

    def test_native_base_prefix_rule_is_retained(self):
        indexed = self.parse('Texture X_prefix\n Base1 X_prefix_longer.tga\nEnd')
        proof = indexed['x_prefix'][0]['composite_generation']
        self.assertTrue(proof['name_matches_base1_native_prefix_rule'])
        self.assertFalse(proof['composite_alias_can_be_created'])

    def test_directory_trick_name_is_not_reduced_to_a_basename_for_generation(self):
        indexed = self.parse('Texture /folder/old_texture.tga\n Blend detail.tga\nEnd')
        proof = indexed['folder/old_texture'][0]['composite_generation']
        self.assertTrue(proof['name_matches_base1_native_prefix_rule'])
        self.assertFalse(proof['composite_alias_can_be_created'])


if __name__ == '__main__':
    unittest.main()
