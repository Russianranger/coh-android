"""Meaningful admission controls: historical counts cannot qualify new frames."""
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest import mock
import tempfile
import json

spec = importlib.util.spec_from_file_location('frames', Path(__file__).parents[1] / 'run_frames_android.py')
frames = importlib.util.module_from_spec(spec)
spec.loader.exec_module(frames)


class FrameAdmission(unittest.TestCase):
    def setUp(self):
        self.value = dict(passed=True, checks=32284, ordered_batch_draws=1025,
                          ordered_batches=3, selective_binding=True, original_matrix_cases=512,
                          bounded_mutations=5000, published_generations=2000, concurrent_readers=3,
                          max_draws_tested=4096, render_allocations=0, render_frees=0,
                          fixture_only=True, authentic_world_entry=False)

    def test_current_corpus(self):
        self.assertEqual(frames.frame_result(self.value), self.value)

    def test_historical_or_missing_corpus(self):
        for key in self.value:
            changed = copy.deepcopy(self.value)
            del changed[key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                frames.frame_result(changed)

    def test_failed_or_inflated_authority(self):
        for key, value in [('checks', 32283), ('checks', True), ('passed', False),
                           ('ordered_batch_draws', 1024), ('ordered_batches', 2),
                           ('selective_binding', False), ('fixture_only', False),
                           ('authentic_world_entry', True), ('render_allocations', 1),
                           ('render_frees', 1), ('original_matrix_cases', 511)]:
            changed = dict(self.value, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                frames.frame_result(changed)

    def test_admission_mode_never_calls_adb(self):
        proof = dict(source_revision='a'*40, source_tree='b'*40, source_sha256={})
        entries = {'x86_64': {'sha256': 'c'*64}, 'arm64-v8a': {'sha256': 'd'*64}}
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'receipt.json'
            args = ['frames', '--artifacts', temporary, '--output', str(output), '--validate-only']
            with mock.patch.object(frames.sys, 'argv', args), \
                    mock.patch.object(frames, 'validate', return_value=(proof,self.value,entries)), \
                    mock.patch.object(frames.subprocess, 'run') as command:
                self.assertEqual(frames.main(), 0)
                command.assert_not_called()
            receipt = json.loads(output.read_text())
            self.assertTrue(receipt['artifact_admitted'])
            for flag in ('android_executed', 'emulator_qualified', 'native_result_validated',
                         'physical_thor_accepted', 'authentic_world_entry', 'gpu_execution'):
                self.assertIs(receipt[flag], False)

    def test_executing_python_sources_must_match(self):
        paths = (Path(frames.__file__).resolve(), frames.DRIVER.resolve(),
                 Path(frames.c.__file__).resolve())
        sources = {p.relative_to(frames.ROOT).as_posix(): frames.c.digest(p) for p in paths}
        frames.validate_runner_sources(frames.ROOT, {'source_sha256': sources})
        for relative in sources:
            for mutate in ('omit', 'alter'):
                changed = dict(sources)
                if mutate == 'omit':
                    del changed[relative]
                else:
                    changed[relative] = '0'*64
                with self.subTest(relative=relative, mutate=mutate), self.assertRaises(ValueError):
                    frames.validate_runner_sources(frames.ROOT, {'source_sha256': changed})

    def test_non_mapping(self):
        for value in (None, [], 'passed', True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                frames.frame_result(value)


if __name__ == '__main__':
    unittest.main()
