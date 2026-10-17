#!/usr/bin/env python3
"""Small refusal controls; no project bytecode, tool or Windows execution."""
from pathlib import Path
import tempfile
import types
import unittest

path = Path(__file__).with_name('run_reviewed_manual_controls.py')
raw = path.read_bytes()
module = types.ModuleType('checked_manual_controls')
exec(compile(raw, str(path), 'exec'), module.__dict__)


class BytecodeControls(unittest.TestCase):
    def test_source_only_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary).resolve()
            (directory / 'source.py').write_text('value = 1\n')
            module.reject_project_bytecode(directory)

    def test_legacy_bytecode_refuses(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary).resolve()
            (directory / 'source.pyc').write_bytes(b'not admitted source')
            with self.assertRaises(ValueError):
                module.reject_project_bytecode(directory)

    def test_empty_cache_directory_refuses(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary).resolve()
            (directory / '__pycache__').mkdir()
            with self.assertRaises(ValueError):
                module.reject_project_bytecode(directory)

    def test_nested_case_variant_refuses(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary).resolve()
            (directory / 'nested').mkdir()
            (directory / 'nested/source.PYC').write_bytes(b'not admitted source')
            with self.assertRaises(ValueError):
                module.reject_project_bytecode(directory)

    def test_cache_directory_alias_refuses(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary).resolve()
            outside = directory / 'outside'
            outside.mkdir()
            (directory / '__pycache__').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                module.reject_project_bytecode(directory)


if __name__ == '__main__':
    unittest.main()
