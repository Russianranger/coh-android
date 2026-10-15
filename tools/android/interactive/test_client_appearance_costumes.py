#!/usr/bin/env python3
"""Native naming and finite stock appearance closure qualification."""
from pathlib import Path
import tempfile
import unittest

import client_appearance_costumes as costumes


CHEST = {'name': 'Chest', 'basename': 'SHIRT', 'geoname': 'CHEST', 'texname': 'CHEST', 'bonecount': '1'}
GLOVES = {'name': 'Gloves', 'basename': 'GLOVE', 'geoname': 'LARM', 'texname': 'GLOVE', 'bonecount': '2'}
COLLAR = {'name': 'Collar', 'basename': 'Collar', 'geoname': 'Collar', 'texname': 'Collar', 'bonecount': '1'}


class NativeNaming(unittest.TestCase):
    def test_native_body_info_and_geometry_override(self):
        for enttype, expected in [('male', 'SM'), ('fem', 'SF'), ('bm_bum', 'BM'), ('bf_fat', 'BF'), ('huge', 'SH')]:
            self.assertEqual(costumes.appearance(enttype)['texture_prefix'], expected)
        app = costumes.appearance('huge', 'COSTUME_OVERRIDE')
        self.assertEqual(app['costume_prefix'], 'COSTUME_OVERRIDE')
        self.assertEqual(app['texture_prefix'], 'SH')

    def test_explicit_texture_bypasses_gender_probe(self):
        app = costumes.appearance('male')
        edges = costumes.texture_names(CHEST, app, '!Mask', '!Second', {'sm_mask', 'sm_second'})
        self.assertEqual([edge['target'] for edge in edges], ['Mask', 'Second'])
        self.assertTrue(all(edge['explicit'] for edge in edges))

    def test_gender_prefix_is_only_used_when_original_probe_exists(self):
        app = costumes.appearance('fem')
        self.assertEqual(costumes.texture_names(CHEST, app, 'Base', None, set())[0]['target'], 'CHEST_Base')
        self.assertEqual(costumes.texture_names(CHEST, app, 'Base', None, {'sf_chest_base'})[0]['target'], 'SF_CHEST_Base')

    def test_dual_texture_uses_original_prefix_field_not_fallback(self):
        app = costumes.appearance('male', 'male')
        self.assertEqual(costumes.texture_names(CHEST, app, 'Skin_01a', 'Other', set())[1]['target'], 'CHEST_Skin_01B')
        app = costumes.appearance('male')
        self.assertEqual(costumes.texture_names(CHEST, app, 'Skin_01a', 'Other', set())[1]['target'], 'CHEST_Other')

    def test_explicit_second_slot_overrides_dual_hack(self):
        app = costumes.appearance('bf', 'bf')
        edges = costumes.texture_names(GLOVES, app, 'Skin_01a', '!ExactB', set())
        self.assertEqual(edges[1]['target'], 'ExactB')

    def test_single_texture_suppresses_second_slot(self):
        self.assertEqual(len(costumes.texture_names(CHEST, costumes.appearance('male'), '!CombinedX', '!Unused', set())), 1)

    def test_automatic_paired_geometry(self):
        edges = costumes.geometry_names(GLOVES, costumes.appearance('bm', 'bm'), 'Hand')
        self.assertEqual([(edge['file'], edge['model']) for edge in edges], [
            ('data/player_library/bm_glove.geo', 'GEO_LARMR_Hand'),
            ('data/player_library/bm_glove.geo', 'GEO_LARML_Hand')])

    def test_explicit_wildcard_paired_geometry(self):
        edges = costumes.geometry_names(GLOVES, costumes.appearance('male'), 'V_MALE_GLOVE.GEO/GEO_Larm*_Magic')
        self.assertEqual([edge['model'] for edge in edges], ['GEO_LarmR_Magic', 'GEO_LarmL_Magic'])
        self.assertEqual({edge['file'] for edge in edges}, {'data/player_library/v_male_glove.geo'})

    def test_explicit_single_sided_geometry_does_not_invent_other_side(self):
        self.assertEqual(len(costumes.geometry_names(GLOVES, costumes.appearance('male'), 'Custom.geo/GEO_LarmR_Only')), 1)
        self.assertEqual(costumes.geometry_names(GLOVES, costumes.appearance('male'), 'Custom.geo/GEO_Unknown'), [])

    def test_chest_link_candidate_order_and_exact_fallback(self):
        app = costumes.appearance('male')
        supported = lambda file, model: model == 'GEO_Collar_jackets_Magic'
        edges = costumes.geometry_names(COLLAR, app, 'Magic', ('shirt', 'jackets'), supported)
        self.assertEqual(edges[0]['model'], 'GEO_Collar_jackets_Magic')
        edges = costumes.geometry_names(COLLAR, app, 'Magic', ('shirt', 'jackets'), lambda *_: False)
        self.assertEqual(edges[0]['model'], 'GEO_Collar_Magic')
        edges = costumes.geometry_names(COLLAR, app, 'Male_Collar.geo/GEO_Collar_Magic', ('tight',),
            lambda file, model: model == 'GEO_Collar_Magic_tight')
        self.assertEqual(edges[0]['model'], 'GEO_Collar_Magic_tight')

    def test_balanced_parts_and_comment_braces(self):
        text = '''// { harmless
NPC "Hero" { // trailing comment }
 Costume {
  EntTypeFile male
  CostumePart "Chest" {
   Geometry tight
   Texture1 "!Face{Literal}"
  }
 }
}
'''
        nodes = costumes.brace_nodes(text)
        self.assertEqual(nodes[0].args, ['Hero'])
        self.assertEqual(costumes.value(nodes[0].children[0].children[1], 'Texture1'), '!Face{Literal}')
        with self.assertRaises(ValueError):
            costumes.brace_nodes('NPC "Hero" { Costume { }')

    def test_malformed_unselected_npc_does_not_lend_parts(self):
        text = '''NPC "Bad" { Costume {
NPC "Good" { Costume { EntTypeFile male } }
'''
        selected = list(costumes.named_brace_nodes(text, 'npc', {'good'}))
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0][0], 'Good')
        self.assertIsNone(selected[0][3])


class FiniteAtlasClosure(unittest.TestCase):
    def fixture(self, root):
        content = {
            'defs/ui/bodyparts.bp': '''BodyPart
 Name Chest
 BoneCount 1
 GeoName CHEST
 TexName CHEST
 BaseName SHIRT
End
''',
            'defs/chestgeolink.def': '''ChestGeoLink {
 BonesetName Tight
 GeoStrings tight
}
''',
            'maps/city_zones/city_01_01/city_01_01.txt': '''Def Atlas
 Group object_library/Omni/EncounterSpawns/Shared/Selected
 End
 Property PersistentNPC "Short/contact.npc" 0
 Property Generator NPCGenerator 0
End
''',
            'object_library/Omni/EncounterSpawns/Shared/all.txt': '''Def Selected
 Property CanSpawn0 SpawnDefs/Relevant.spawndef 0
End
Def Unrelated
 Property CanSpawn0 SpawnDefs/Unrelated.spawndef 0
End
''',
            'scripts.loc/contacts/short/contact.npc': '''NPCDef Contact {
 Model Hero
}
''',
            'scripts.loc/spawndefs/relevant.spawndef': '''SpawnDef {
 var ALIAS volatile = <<HeroGroup>>
 Actor {
  Model ALIAS
 }
}
''',
            'scripts.loc/spawndefs/unrelated.spawndef': '''SpawnDef {
 Actor {
  Model UnrelatedHero
  VillainGroup UnrelatedFaction
 }
}
''',
            'server/spawnarea/globals.txt': '''SpawnArea Global
 NPC HeroGroup
  Type Hero
 End
 NPC CivilianGroup
  Type Civilian
 End
 NPC NPCGenerator
  Type Civilian
 End
 Generator NPCGenerator
  GeneratedTypes CivilianGroup
 End
End
''',
            'defs/npc/shared.nd': '''NPC Hero {
 Costume {
  EntTypeFile male
  CostumeFilePrefix male
  CostumePart Chest {
   Geometry Tight
   Texture1 Base
  }
 }
}
NPC Civilian {
 Costume {
  EntTypeFile male
  CostumePart Chest {
   Geometry Tight
   Texture1 !Civilian
  }
 }
}
NPC UnrelatedHero {
 Costume {
  EntTypeFile male
  CostumePart Chest {
   Geometry Unrelated
   Texture1 !Unrelated
  }
 }
}
NPC Bad { Costume {
''',
            'ent_types/male.txt': '''Type
 Graphics player_library/g_male.geo
End
''',
        }
        for name, text in content.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)

    def test_exact_referenced_def_and_all_generator_choices(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            result = costumes.atlas_requests(root, {'texture_library/sm_chest_base.texture': {}})
            self.assertEqual(result['closure']['selected_npcs'], ['Civilian', 'Hero'])
            self.assertEqual(result['closure']['spawn_source_files'], 1)
            self.assertEqual(result['closure']['persistent_npc_files'], 1)
            self.assertEqual(result['unresolved'], [])
            self.assertEqual(set(result['textures']), {'civilian', 'sm_chest_base'})
            self.assertIn('data/player_library/g_male.geo', result['geometry'])
            self.assertNotIn('unrelated', result['textures'])
            self.assertTrue(all('unrelated.spawndef' not in pin['path'] for pin in result['source_files']))
            self.assertTrue(all(row['source_sha256'] for rows in result['textures'].values() for row in rows))


if __name__ == '__main__':
    unittest.main()
