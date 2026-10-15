"""Focused refusal controls; never execute or compile the historical suites."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('recovered_fixture_replay', HERE / 'replay.py')
replay = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(replay)


class DestinationSafetyTests(unittest.TestCase):
    def refused_main(self, layout, output):
        with patch.object(sys, 'argv', ['replay.py', '--artifact-root', '/unused/artifact',
                                       '--layout', str(layout), '--output', str(output)]), \
                patch.object(replay, 'source_map') as source, \
                patch.object(replay, 'authenticate_ci') as native:
            with self.assertRaises(ValueError):
                replay.main()
            source.assert_not_called()
            native.assert_not_called()

    def test_existing_output_refused_before_layout_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / 'evidence'
            output.mkdir()
            sentinel = output / 'original.json'
            sentinel.write_bytes(b'original receipt\n')
            layout = root / 'layout'
            self.refused_main(layout, output)
            self.assertFalse(layout.exists())
            self.assertEqual(sentinel.read_bytes(), b'original receipt\n')
            self.assertEqual(list(output.iterdir()), [sentinel])

    def test_existing_layout_refused_before_output_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            layout = root / 'layout'
            layout.mkdir()
            sentinel = layout / 'retained.java'
            sentinel.write_bytes(b'existing source\n')
            output = root / 'evidence'
            self.refused_main(layout, output)
            self.assertFalse(output.exists())
            self.assertEqual(sentinel.read_bytes(), b'existing source\n')

    def test_same_destination_refused_before_any_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'new'
            self.refused_main(path, path)
            self.assertFalse(path.exists())

    def test_output_inside_layout_refused_before_any_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            layout = Path(temporary) / 'new'
            self.refused_main(layout, layout / 'evidence')
            self.assertFalse(layout.exists())

    def test_layout_inside_output_refused_before_any_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'new'
            self.refused_main(output / 'layout', output)
            self.assertFalse(output.exists())

    def test_dangling_destination_symlink_refused_before_target_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / 'linked-evidence'
            target = root / 'uncreated-target'
            output.symlink_to(target)
            layout = root / 'layout'
            self.refused_main(layout, output)
            self.assertFalse(target.exists())
            self.assertFalse(layout.exists())
            self.assertTrue(output.is_symlink())

    def test_explicit_output_argument_required(self):
        with patch.object(sys, 'argv', ['replay.py', '--artifact-root', '/unused/artifact',
                                       '--layout', '/unused/layout']), \
                patch.object(replay, 'source_map') as source, \
                patch.object(replay, 'authenticate_ci') as native, \
                patch.object(sys, 'stderr'):
            with self.assertRaises(SystemExit) as error:
                replay.main()
            self.assertEqual(error.exception.code, 2)
            source.assert_not_called()
            native.assert_not_called()


class AuthenticationRefusalTests(unittest.TestCase):
    def test_tampered_original_receipt_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / 'out/native-live-directory-037'
            output.mkdir(parents=True)
            raw = (HERE / 'evidence/original-ci-qualification.failed.json').read_bytes()
            (output / 'qualification.json').write_bytes(raw + b'\n')
            with self.assertRaisesRegex(ValueError, 'Authentication failed:.*qualification.json'):
                replay.authenticate_ci(root)

    def synthetic_refusal_fixture(self, root):
        """Minimal explicitly controlled receipt reaches source/helper refusals.

        Only the expected raw-receipt pin is patched in these negative tests.
        The source pin and helper pin remain the original CI values, and no
        synthetic receipt is ever accepted or used to load a native library.
        """
        original = json.loads((HERE / 'evidence/original-ci-qualification.failed.json').read_text())
        name = 'coh_live_directory_core.c'
        original['source_files'] = {name: original['source_files'][name]}
        original['artifacts'] = {'libcoh_live_directory-host.so': replay.PINS['original_ci_host_helper']}
        output = root / 'out/native-live-directory-037'
        sources = root / 'tools/native_live_directory'
        output.mkdir(parents=True)
        sources.mkdir(parents=True)
        (sources / name).write_bytes((replay.REPO / 'tools/native_live_directory' / name).read_bytes())
        (output / 'libcoh_live_directory-host.so').write_bytes(b'tampered retained helper\n')
        receipt = output / 'qualification.json'
        receipt.write_text(json.dumps(original))
        pins = copy.deepcopy(replay.PINS)
        pins['original_ci_receipt'] = replay.pin(receipt)
        return sources, pins

    def test_tampered_recovered_source_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources, pins = self.synthetic_refusal_fixture(root)
            (sources / 'coh_live_directory_core.c').write_bytes(b'tampered source\n')
            with patch.object(replay, 'PINS', pins), self.assertRaisesRegex(
                    ValueError, 'Authentication failed:.*coh_live_directory_core.c'):
                replay.authenticate_ci(root)

    def test_tampered_retained_helper_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, pins = self.synthetic_refusal_fixture(root)
            with patch.object(replay, 'PINS', pins), self.assertRaisesRegex(
                    ValueError, 'Authentication failed:.*libcoh_live_directory-host.so'):
                replay.authenticate_ci(root)


if __name__ == '__main__':
    unittest.main()
