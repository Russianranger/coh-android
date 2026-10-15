"""Dependency and provenance boundaries; synthetic assets never qualify map 5."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import audit_kings_row_foundation as audit
import client_appearance_costumes as costumes
import test_client_appearance_costumes as costume_tests


class MemorySources:
    def __init__(self, files):
        self.files = files
        self.entries = {name: {} for name in files}
        self.pins = {'upstream/i24/data/' + name: audit.pin_bytes(text.encode()) for name, text in files.items()}

    def read(self, name):
        return list(audit.source_tokens(self.files[name]))

    def identity(self, name):
        name = 'upstream/i24/data/' + name
        return name, self.pins[name]


class SourceGraphTests(unittest.TestCase):
    def fixture(self):
        return {audit.MAP: 'Import maps/layer.txt\nScenefile scenes/kings.txt\n',
            'maps/layer.txt': 'Def local\n Group ignored/path/house__variant\n End\nEnd\nGroup local\n',
            'object_library/a/a.rootnames': 'Def house\n Obj house\nDefEnd\n',
            'object_library/a/a.txt': 'RootMod house\n Group decoration\nEnd\n',
            'object_library/b/b.rootnames': 'Def decoration\n Obj decoration\nDefEnd\n',
            'object_library/b/b.txt': 'RootMod decoration\n Group house\nEnd\nReplaceTex 0 exact.tga\n',
            'scenes/kings.txt': 'Sky kings.txt\nTexSwap\n{\nSource old\nDest original\n}\n',
            'scenes/skies/kings.txt': 'sun\n MoonName sun__\nEnd\ncloud\n Name clouds__\nEnd\n',
            'object_library/sky/sky.rootnames': 'Def sun\nObj sun\nDefEnd\nDef sunglow\nObj sunglow\nDefEnd\nDef clouds\nObj clouds\nDefEnd\n'}

    def test_recursive_library_and_scene_cycle_terminate_without_losing_edges(self):
        result = audit.group_requests(MemorySources(self.fixture()))
        self.assertEqual(result['unresolved_source_edges'], [])
        self.assertEqual(set(result['geometry']), {'data/object_library/a/a.geo',
            'data/object_library/b/b.geo', 'data/object_library/sky/sky.geo'})
        self.assertEqual(set(result['textures']), {'exact', 'original'})
        self.assertEqual(result['sky_files'], ['scenes/skies/kings.txt'])
        models = {row['model'] for row in result['geometry']['data/object_library/sky/sky.geo']}
        self.assertEqual(models, {'sun', 'sunglow', 'clouds'})

    def test_ambiguous_public_basename_is_gap_not_path_guess(self):
        files = self.fixture()
        files['object_library/other/other.rootnames'] = 'Def house\nObj house\nDefEnd\n'
        result = audit.group_requests(MemorySources(files))
        gaps = [row for row in result['unresolved_source_edges'] if row['kind'] == 'ambiguous_library_name']
        self.assertTrue(gaps)
        self.assertNotIn('data/object_library/a/a.geo', result['geometry'])

    def test_missing_model_cannot_hide_behind_local_definition(self):
        files = self.fixture()
        files['maps/layer.txt'] += 'Def absent\n Obj absent\nEnd\n'
        result = audit.group_requests(MemorySources(files))
        self.assertTrue(any(row['target'] == 'absent' for row in result['unresolved_source_edges']))

    def test_literal_declaration_with_trick_suffix_does_not_invent_native_basename(self):
        files = self.fixture()
        files['object_library/trick/trick.rootnames'] = 'Def only__trick\nObj only__trick\nDefEnd\n'
        files['maps/layer.txt'] += 'Obj only__trick\n'
        result = audit.group_requests(MemorySources(files))
        self.assertTrue(any(row['target'] == 'only__trick' for row in result['unresolved_source_edges']))
        self.assertNotIn('data/object_library/trick/trick.geo', result['geometry'])

    def test_comments_and_quoted_comment_markers_preserve_source_lines(self):
        rows = list(audit.source_tokens('// Group fake\n/* Obj fake */\nGroup "real//name"\n# Import escape\n'))
        self.assertEqual(rows, [(3, ['Group', 'real//name'])])

    def test_map_interface_uses_exact_zone_icon_and_native_map_names(self):
        sources = MemorySources({'menu/zones.map':
            'Name maps/city_zones/city_01_01/city_01_01.txt\nIcon atlas\nEnd\n'
            'Name MAPS/CITY_ZONES/CITY_01_02/CITY_01_02.TXT\nIcon City_01_02_KingsRow\nEnd\n'
            'Name maps/city_zones/city_01_03/city_01_03.txt\nIcon adjacent\nEnd\n'})
        request = {'textures': {}, 'source_files': {}}
        audit.map_interface_requests(sources, request)
        self.assertEqual(set(request['textures']),
            {'city_01_02', 'map_city_01_02', 'city_01_02_kingsrow'})
        self.assertEqual(request['textures']['city_01_02_kingsrow'][0]['source_line'], 5)
        self.assertIn('upstream/i24/data/menu/zones.map', request['source_files'])

    def test_unsafe_import_and_linked_changed_sources_are_rejected(self):
        for value in ('../escape', '/escape', 'maps//x', 'maps/./x', 'maps\\x', 'C:/escape'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                audit.data_path(value)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); target = root / 'upstream/i24/data/maps/test.txt'
            target.parent.mkdir(parents=True); target.write_text('original')
            manifest = root / 'docs/data-manifest.json'; manifest.parent.mkdir()
            manifest.write_text(json.dumps({'commit': audit.DATA, 'entries': [{
                'path': 'data/maps/test.txt', 'size': 8, 'sha256': hashlib.sha256(b'original').hexdigest()}]}))
            sources = audit.Sources(root); target.write_text('modified')
            with self.assertRaisesRegex(ValueError, 'differs from pinned'):
                sources.read('maps/test.txt')
            target.unlink(); target.symlink_to(manifest)
            with self.assertRaises(OSError):
                sources.read('maps/test.txt')


class ProvenanceTests(unittest.TestCase):
    def test_existing_output_is_preserved_before_reading_sources_or_network(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(audit, 'audit') as inspect:
            path = Path(folder) / 'previous.json'; path.write_text('previous evidence')
            with self.assertRaisesRegex(ValueError, 'Existing output is preserved'):
                audit.main(['--output', str(path)])
            self.assertEqual(path.read_text(), 'previous evidence')
            inspect.assert_not_called()

    def test_native_model_suffix_and_authored_fx_prefix_normalization(self):
        request = {'geometry': {'data/object_library/a.geo': [{'model': 'beam__CarLights'}]}}
        audit.normalize_native_requests(request)
        self.assertEqual(request['geometry']['data/object_library/a.geo'], [
            {'model': 'beam', 'native_model_literal': 'beam__CarLights'}])
        self.assertEqual(audit.native_fx_root('data/fx/game/data/fx/world/crystal.fx'), 'fx/world/crystal.fx')
        self.assertEqual(audit.native_fx_root('data/fx/world/crystal.fx'), 'fx/world/crystal.fx')

    def test_retained_geo_uses_its_own_frozen_header_and_does_not_mutate_donors(self):
        name = 'data/object_library/test.geo'
        old = {'bytes': 10, 'offset': 20, 'md5_table': 'a' * 32, 'cached_header': b'old'}
        new = old | {'cached_header': b'new'}
        files = {name[5:]: new}
        result = audit.preserve_retained_headers(files, {'old.pigg': {name[5:]: old}},
            {name: {'bytes': 10}}, {}, {name: {'donor': 'old.pigg'}})
        self.assertEqual(result[name[5:]]['cached_header'], b'old')
        self.assertEqual(files[name[5:]]['cached_header'], b'new')
        with self.assertRaisesRegex(ValueError, 'missing or size differs'):
            audit.preserve_retained_headers(files, {}, {name: {'bytes': 10}}, {}, {name: {'donor': 'old.pigg'}})

    def test_offline_geometry_verification_refuses_linked_cache(self):
        name = 'data/object_library/test.geo'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / hashlib.sha256(name.encode()).hexdigest()
            original = Path(folder) / 'original'; original.write_bytes(b'not actual geometry')
            path.symlink_to(original)
            with mock.patch.object(audit.sweep, 'verified_payload') as validate:
                with self.assertRaises(OSError):
                    audit.verify_world_geometry_cache({name[5:]: {}}, [name], folder)
                validate.assert_not_called()

    def test_metadata_network_is_explicit_and_missing_or_linked_cache_fails(self):
        current = {'provenance': {'metadata_archives': [{'archive': 'test.pigg', 'source_metadata_bytes': 10}]}}
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(audit.sweep, 'metadata') as fetch:
            with self.assertRaisesRegex(ValueError, 'explicit --fetch-metadata'):
                audit.donor_metadata(current, folder)
            fetch.assert_not_called()
            path = Path(folder) / 'test.pigg'; original = Path(folder) / 'real'; original.write_bytes(b'original')
            path.symlink_to(original)
            with self.assertRaisesRegex(ValueError, 'Linked'):
                audit.donor_metadata(current, folder, fetch=True)
            fetch.assert_not_called()

    def test_explicit_map_spawnarea_overrides_global_without_using_atlas(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); costume_tests.FiniteAtlasClosure().fixture(root)
            path = root / 'server/spawnarea/city_01_02.txt'
            path.write_text('SpawnArea Kings\nNPC CivilianGroup\n Type Hero\nEnd\nEnd\n')
            result = costumes.atlas_requests(root, {'texture_library/sm_chest_base.texture': {}},
                spawnarea_file='server/spawnarea/city_01_02.txt')
            self.assertEqual(result['closure']['selected_npcs'], ['Hero'])
            for name in ('server/spawnarea/../escape.txt', 'server/spawnarea/missing.txt'):
                with self.assertRaises(ValueError):
                    costumes.atlas_requests(root, {}, spawnarea_file=name)


if __name__ == '__main__':
    unittest.main()
