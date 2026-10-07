"""Prove the new Game layer preserves native loading and every prior hook."""
from pathlib import Path
import hashlib
import re
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'tools')]
import package_client_gameplay_performance_native as producer
import package_client_loading_native as loading
import test_client_frame_timing_source as frame
from prepare_resume_client_source import apply_patch


def sources():
    original = {producer.FILES[0]: frame.sources(after_scene=True)[1][producer.FILES[0]],
        producer.FILES[1]: (ROOT/'upstream/ouroboros'/producer.FILES[1]).read_bytes()
            .replace(b'\r\n', b'\n').decode('utf-8')}
    with tempfile.TemporaryDirectory(prefix='coh-gameplay-source-') as temporary:
        source = Path(temporary)
        for name, text in original.items():
            target = source/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(text.encode('utf-8'))
        for name in producer.PATCHES:
            apply_patch(source, producer.normalized_patch(name)[0])
        current = {name: (source/name).read_bytes().decode('utf-8') for name in producer.FILES}
        for name in reversed(producer.PATCHES):
            loading.reverse_patch(source, producer.normalized_patch(name)[0])
        if any((source/name).read_bytes() != text.encode('utf-8') for name, text in original.items()):
            raise ValueError('Gameplay reverse proof did not reproduce the complete accepted source')
    return original, current


def strip_hooks(text):
    text = text.replace('#include "cohClientGameplayPerformance.h"\n', '')
    text = text.replace('    cohGpApplyProfile(&game_state.maxfps, game_state.create_bins,\n'
        '        game_state.maxMenuFps, game_state.maxInactiveFps);\n', '')
    for slot in (1, 2):
        text = text.replace('                    if (cohGpTextureError('+str(slot)+'u, '
            'e->seq->type->name, newtexture'+str(slot)+', bone_NameFromId(bone)))\n'
            '                        Errorf(', '                    Errorf(')
    return text


def source_proof():
    original, current = sources()
    expected = producer.expected_receipt()
    for field, values in (('source_sha256', original), ('patched_sha256', current)):
        if {name: hashlib.sha256(text.encode('utf-8')).hexdigest() for name, text in values.items()} != expected[field]:
            raise ValueError('Gameplay fixture differs from the actual staged native ancestry')
    for name in producer.FILES:
        if strip_hooks(current[name]) != original[name]:
            raise ValueError('Gameplay layer changes accepted native behavior outside its exact hooks: '+name)
    parsed = loading.function(current[producer.FILES[0]], 'void parseArgs(')
    if parsed.index('cohGpApplyProfile(') < parsed.index('cmdAccessOverride(0);'):
        raise ValueError('Cap override must follow command-line parsing')
    texture = loading.function(current[producer.FILES[1]], 'void changeTexture(')
    for slot, load in ((1, 'texture1 = texLoad('), (2, 'texture = texLoadBasic(')):
        if texture.index('cohGpTextureError('+str(slot)+'u') < texture.index(load):
            raise ValueError('Texture attempt must precede diagnostic suppression')
    return True


class GameplaySourceTests(unittest.TestCase):
    def test_complete_accepted_sources_remain_exact_except_cap_and_error_predicates(self):
        self.assertTrue(source_proof())

    def test_windows_text_translation_cannot_change_apply_reverse_proofs(self):
        ordinary = Path.write_text
        def translated(path, text, *args, **kwargs):
            kwargs.setdefault('newline', '\r\n')
            return ordinary(path, text, *args, **kwargs)
        with mock.patch.object(Path, 'write_text', translated):
            self.assertTrue(source_proof())

    def test_receipt_wraps_exact_scene_frame_parent_without_schema_or_renderer_changes(self):
        document = producer.expected_receipt()
        self.assertEqual(document['base_client_scene_performance_build_input'], producer.base.expected_receipt())
        self.assertEqual(set(document['source_sha256']), set(producer.FILES))
        self.assertEqual(set(document['overlay_sha256']), set(producer.OVERLAYS))
        self.assertTrue(document['reverse_patch_exact_base_verified'])
        self.assertTrue(document['gameplay_frame_cap_changed'])
        for name in ('cache_encoding_changed', 'parse6_schema_changes', 'source_freshness_changed',
                'graphics_profile_changes', 'renderer_changed', 'gameplay_validation_changes',
                'runtime_execution_validated'):
            self.assertIs(document[name], False)

    def test_staged_source_rejects_changed_prior_headers_current_hooks_and_cache_schema(self):
        with tempfile.TemporaryDirectory(prefix='coh-gameplay-stage-proof-') as temporary:
            source = Path(temporary)/'source'
            producer.stage(SimpleNamespace(output=source))
            self.assertEqual(producer.validate_source(source)[0], producer.expected_receipt())
            targets = ('Game/src/cohClientSceneTiming.h', 'Game/src/cohClientFrameTiming.h',
                'Game/src/cohClientGameplayPerformance.h', 'Game/src/entity/entclient.c',
                next(iter(producer.baseline.schema_pins())))
            for name in targets:
                path = source/name
                original = path.read_bytes()
                path.write_bytes(original+b'\n/* unexpected native change */\n')
                try:
                    with self.subTest(name=name), self.assertRaises(ValueError):
                        producer.validate_source(source)
                finally:
                    path.write_bytes(original)

    def test_header_has_fixed_bounds_and_no_loading_allocation_wait_or_frame_enforcement(self):
        header = (ROOT/next(iter(producer.OVERLAYS.values()))).read_text()
        self.assertIn('#define COH_GP_TEXTURE_KEYS 64u', header)
        self.assertIn('#define COH_GP_MAX_TEXTURE_REPORTS 32u', header)
        self.assertNotRegex(header, r'\b(?:malloc|calloc|realloc|Sleep|WaitFor|texLoad|texLoadBasic|waitFps)\s*\(')
        original, current = sources()
        self.assertEqual(loading.function(original[producer.FILES[0]], 'void engine_update('),
            loading.function(current[producer.FILES[0]], 'void engine_update('))
        self.assertEqual(loading.function(original[producer.FILES[0]], 'int game_mainLoop('),
            loading.function(current[producer.FILES[0]], 'int game_mainLoop('))
        self.assertEqual(loading.function(original[producer.FILES[0]], 'void game_loadData('),
            loading.function(current[producer.FILES[0]], 'void game_loadData('))


if __name__ == '__main__':
    unittest.main()
