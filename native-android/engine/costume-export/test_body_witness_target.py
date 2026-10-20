#!/usr/bin/env python3
"""Focused source-authentic composition and nonexecuting preflight controls."""
from pathlib import Path
import importlib.util
import json
import os
import tempfile
import unittest
from unittest.mock import patch
import body_witness_target as target

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'upstream/ouroboros'


class TargetControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def refuses(self, code, action):
        with self.assertRaisesRegex(ValueError, code): action()

    def test_duplicate_and_nonfinite_json(self):
        self.refuses('TARGET_JSON_DUPLICATE', lambda: target.decode(b'{"a":1,"a":2}'))
        self.refuses('TARGET_JSON_NONFINITE', lambda: target.decode(b'{"a":NaN}'))
        self.refuses('TARGET_JSON_OBJECT', lambda: target.decode(b'[]'))

    def test_bound_regular_file_alias_and_symlink(self):
        original = self.directory / 'source'; original.write_bytes(b'1234')
        self.assertEqual(target.read(original, 4), b'1234')
        self.refuses('TARGET_FILE_BOUND', lambda: target.read(original, 3))
        self.refuses('TARGET_FILE_BOUND', lambda: target.read(self.directory))
        hard = self.directory / 'hard'; os.link(original, hard)
        self.refuses('TARGET_FILE_BOUND', lambda: target.read(original))
        hard.unlink()
        link = self.directory / 'link'
        try: link.symlink_to(original)
        except (OSError, NotImplementedError): return  # Windows ordinary account may lack symlink permission.
        self.refuses('TARGET_PATH_LINK', lambda: target.read(link))

    def test_exact_original_startup_reversible(self):
        original = (SOURCE / 'MapServer/src/svr/svr_init.c').read_bytes().replace(b'\r\n', b'\n')
        output = target.startup_patch(original)
        self.assertEqual(target.startup_unpatch(output), original)
        self.assertEqual(output.count(target.HOOK), 1)
        self.refuses('TARGET_STARTUP_ANCHOR', lambda: target.startup_patch(output))
        self.refuses('TARGET_STARTUP_ANCHOR', lambda: target.startup_patch(original + b'    loadCostumes();\n'))
        self.refuses('TARGET_STARTUP_REVERSAL', lambda: target.startup_unpatch(original))
        self.refuses('TARGET_STARTUP_REVERSAL', lambda: target.startup_unpatch(output + target.HOOK))

    def test_inherited_progress_startup_is_preserved(self):
        original = (SOURCE / 'MapServer/src/svr/svr_init.c').read_bytes().replace(b'\r\n', b'\n')
        inherited = original.replace(b'    loadCostumes();\n', b'    /* explicit inherited synthetic preflight marker */\n    loadCostumes();\n')
        self.assertEqual(target.startup_unpatch(target.startup_patch(inherited)), inherited)

    def test_exact_loader_instrumentation_render(self):
        witness = target.load('target_controls_witness', Path(target.__file__).with_name('stage_body_witness.py'))
        names = (witness.BODY, witness.PARSER, witness.SERVER, witness.BODY_H, witness.BONES_H)
        originals = {n: (SOURCE / n).read_bytes() for n in names}
        labels = {n: str(i) * 64 for i, n in enumerate(('build_sha256', 'profile_sha256', 'run_sha256'), 1)}
        rendered, receipt = witness.render(originals, labels)
        self.assertFalse(receipt['runtime_executed'])
        self.assertFalse(receipt['server_compiled'])
        self.assertFalse(receipt['runtime_generation_admitted'])
        self.assertFalse(receipt['enabled_by_default'])
        self.assertEqual(rendered[witness.SERVER], target.startup_patch(originals[witness.SERVER].replace(b'\r\n', b'\n')))
        self.assertEqual(rendered[witness.BODY].count(b'coh_body_witness_begin(&bodyPartList)'), 1)
        self.assertEqual(rendered[witness.PARSER].count(b'coh_source_body_witness_binary(structptr,ParserReadBinaryFile('), 1)
        invalid = dict(labels, generation=1)
        with self.assertRaises(ValueError): witness.render(originals, invalid)
        changed = dict(originals); changed[witness.BODY] += b'\n'
        with self.assertRaises(ValueError): witness.render(changed, labels)

    def test_source_and_stage_aliases_refuse(self):
        self.refuses('TARGET_EXTERNAL_STAGE_REQUIRED', lambda: target.paths(self.directory, self.directory))
        child = self.directory / 'child'; child.mkdir()
        self.refuses('TARGET_EXTERNAL_STAGE_REQUIRED', lambda: target.paths(self.directory, child))
        self.refuses('TARGET_EXTERNAL_STAGE_REQUIRED', lambda: target.paths(child, self.directory))

    def test_dependencies_bounded_streaming_and_changes(self):
        self.refuses('TARGET_DEPENDENCIES_MISSING', lambda: target.dependency_manifest(self.directory))
        cache = self.directory / 'out/build/CPM/pkg'; cache.mkdir(parents=True)
        self.refuses('TARGET_DEPENDENCIES_EMPTY', lambda: target.dependency_manifest(self.directory))
        source = cache / 'a.c'; source.write_bytes(b'int a;\n')
        manifest = target.dependency_manifest(self.directory)
        self.assertEqual(manifest['total_bytes'], 7)
        self.assertEqual(set(manifest['files']), {'pkg/a.c'})
        with patch.object(target, 'MAX_MANIFEST', 0):
            self.refuses('TARGET_DEPENDENCY_BUDGET', lambda: target.dependency_manifest(self.directory))
        with patch.object(target, 'MAX_TOTAL', 6):
            self.refuses('TARGET_DEPENDENCY_BUDGET', lambda: target.dependency_manifest(self.directory))
        source.write_bytes(b'int b;\n')
        self.assertNotEqual(target.dependency_manifest(self.directory), manifest)

    def test_workflow_never_invokes_a_server(self):
        text = (ROOT / '.github/workflows/native-body-runtime-target.yml').read_text()
        self.assertIn('--parallel 2 --target MapServer', text)
        self.assertNotIn('wine ', text)
        self.assertNotIn('Start-Process', text)
        self.assertNotIn('./MapServer', text)
        self.assertIn('contents: read', text)
        self.assertIn('cancel-in-progress: false', text)


if __name__ == '__main__':
    unittest.main(verbosity=1)
