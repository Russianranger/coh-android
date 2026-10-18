#!/usr/bin/env python3
"""New recipe admission controls; synthetic files do not qualify a real PE."""
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('initial_recipe_controls', HERE / 'recipe.py')
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)


def fake_pe():
    raw = bytearray(1024)
    raw[:2] = b'MZ'
    struct.pack_into('<I', raw, 60, 64)
    raw[64:68] = b'PE\0\0'
    struct.pack_into('<HH', raw, 68, 0x14c, 1)
    struct.pack_into('<HH', raw, 84, 96, 2)
    struct.pack_into('<H', raw, 88, 0x10b)
    struct.pack_into('<I', raw, 104, 1)
    return bytes(raw)


def cache():
    return (b'CMAKE_GENERATOR:INTERNAL=Visual Studio 18 2026\n'
            b'CMAKE_GENERATOR_PLATFORM:INTERNAL=Win32\n'
            b'CMAKE_HOME_DIRECTORY:INTERNAL=C:/isrc\n'
            b'CMAKE_CONFIGURATION_TYPES:UNINITIALIZED=OptDebug\n')


class AdmissionControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='initial-recipe-controls-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_exact_inventory_accepts_only_selected_files_and_parents(self):
        (self.root / 'source').mkdir()
        (self.root / 'source' / 'x.c').write_bytes(b'x')
        r.exact_inventory(self.root, {'source/x.c'})

    def test_extra_file_refused(self):
        (self.root / 'x').write_bytes(b'x')
        (self.root / 'raw.log').write_bytes(b'private')
        with self.assertRaisesRegex(ValueError, 'INITIAL_ARTIFACT_INVENTORY'):
            r.exact_inventory(self.root, {'x'})

    def test_extra_empty_directory_refused(self):
        (self.root / 'x').write_bytes(b'x')
        (self.root / 'extra').mkdir()
        with self.assertRaisesRegex(ValueError, 'INITIAL_ARTIFACT_DIRECTORIES'):
            r.exact_inventory(self.root, {'x'})

    def test_missing_file_refused(self):
        with self.assertRaisesRegex(ValueError, 'INITIAL_ARTIFACT_INVENTORY'):
            r.exact_inventory(self.root, {'x'})

    def test_symlink_file_refused(self):
        (self.root / 'x').write_bytes(b'x')
        (self.root / 'alias').symlink_to(self.root / 'x')
        with self.assertRaisesRegex(ValueError, 'INITIAL_PATH_LINK'):
            r.exact_inventory(self.root, {'x', 'alias'})

    def test_symlink_directory_refused(self):
        (self.root / 'target').mkdir()
        (self.root / 'alias').symlink_to(self.root / 'target', target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'INITIAL_PATH_LINK'):
            r.exact_inventory(self.root, set())

    def test_hardlink_file_refused(self):
        import os
        (self.root / 'x').write_bytes(b'x')
        os.link(self.root / 'x', self.root / 'alias')
        with self.assertRaisesRegex(ValueError, 'INITIAL_REGULAR_BOUND'):
            r.exact_inventory(self.root, {'x', 'alias'})

    def test_json_duplicate_and_nonfinite_refused(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'[]'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                r.decode(raw)

    def test_member_traversal_and_alias_forms_refused(self):
        for value in ('../x', '/x', 'x/../y', 'x//y', 'x/./y', 'C:/x', 'x\\y', ''):
            with self.subTest(value=value), self.assertRaises(ValueError):
                r.relative_name(value)

    def test_synthetic_pe_shape_control_and_changed_machine_refusal(self):
        raw = fake_pe()
        r.pe_identity(raw)
        for offset, value in ((0, b'XX'), (68, b'\x64\x86'), (88, b'\x0b\x02'), (84, b'\x01\x00')):
            changed = bytearray(raw)
            changed[offset:offset + len(value)] = value
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                r.pe_identity(bytes(changed))

    def test_pe_dll_and_missing_entrypoint_refused(self):
        for offset, value in ((86, 0x2002), (104, 0)):
            raw = bytearray(fake_pe())
            struct.pack_into('<H' if offset == 86 else '<I', raw, offset, value)
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                r.pe_identity(bytes(raw))

    def test_cache_configuration_control_and_changed_fields_refusal(self):
        raw = cache()
        r.cmake_identity(raw, 'C:/isrc')
        for before, after in ((b'Win32', b'x64'), (b'OptDebug', b'Release'),
                              (b'2026', b'2022'), (b'C:/isrc', b'C:/elsewhere')):
            with self.subTest(before=before), self.assertRaises(ValueError):
                r.cmake_identity(raw.replace(before, after), 'C:/isrc')

    def test_cache_duplicate_or_conflicting_alias_refused(self):
        for extra in (b'CMAKE_GENERATOR_PLATFORM:INTERNAL=Win32\n',
                      b'CMAKE_CONFIGURATION_TYPES:STRING=OptDebug\n'):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                r.cmake_identity(cache() + extra, 'C:/isrc')

    def test_hooked_inherited_baseline_control_and_drift_refusal(self):
        fresh = types.SimpleNamespace(old=types.SimpleNamespace(PRIOR='prior.json'),
                base=types.SimpleNamespace(inherited_hashes=lambda _: {'tick.c': r.sha(b'prepared')}))
        getter = lambda _: b'{}'
        self.assertEqual(r.inherited_hook_sources(fresh, getter, {'tick.c': b'prepared'}),
                         {'tick.c': r.sha(b'prepared')})
        with self.assertRaisesRegex(ValueError, 'INITIAL_HOOK_INHERITED_BASELINE'):
            r.inherited_hook_sources(fresh, getter, {'tick.c': b'raw upstream'})

    def test_all_hooked_inherited_baselines_are_checked(self):
        hashes = {name: r.sha(name.encode()) for name in ('first.c', 'second.c')}
        fresh = types.SimpleNamespace(old=types.SimpleNamespace(PRIOR='prior.json'),
                base=types.SimpleNamespace(inherited_hashes=lambda _: hashes))
        with self.assertRaisesRegex(ValueError, 'INITIAL_HOOK_INHERITED_BASELINE'):
            r.inherited_hook_sources(fresh, lambda _: b'{}',
                                     {'first.c': b'first.c', 'second.c': b'changed'})

    def fixture(self):
        # Only the new recipe's admission envelope is under test. The actual
        # inherited source/reversal checker is an explicit test double here.
        files = {'MapServer.exe': fake_pe(), 'CMakeCache.txt': cache()}
        for name, raw in files.items():
            (self.root / name).write_bytes(raw)
        receipt = {'schema': r.SCHEMA, 'passed': True, 'build_role': r.ROLE,
                   'source_revision': 'a' * 40, 'source_git_status_porcelain': [],
                   'compile_only': True, 'runtime_executed': False,
                   'source_stage_verified': True, 'inherited_source_closure_reverified': True,
                   'external_input_archive_verification_claimed': False,
                   'platform': 'Win32', 'pe_machine': 'i386', 'configuration': 'OptDebug',
                   'generator': 'Visual Studio 18 2026', 'staged_source_root': 'C:/isrc',
                   'artifacts': {n: r.pin(raw) for n, raw in files.items()},
                   'source_closure_sha256': {'supplier': 'b' * 64},
                   'accepted_observer_equivalence': False, 'accepted_qualifiers_reexecuted': False,
                   'object_cache_reused': False, 'normal_authentication_qualified': False,
                   'world_authority': False}
        fake_fresh = types.SimpleNamespace(RECEIPT='fresh.json', old=types.SimpleNamespace(RECEIPT='old.json', PRIOR='prior.json'))
        for name, value in (('context', lambda _: (self.root, fake_fresh, None)),
                            ('checkout_closure', lambda _: {'supplier': 'b' * 64}),
                            ('unchanged_checkout', lambda *_: None),
                            ('artifact_names', lambda _: set(files)),
                            ('verify_bytes', lambda *_args, **_kwargs: {'test_double': True}),
                            ('git', lambda *_: ('a' * 40 + '\n').encode())):
            replacement = patch.object(r, name, value)
            replacement.start()
            self.addCleanup(replacement.stop)
        return receipt

    def verify_fixture(self, receipt, expected='a' * 40, checksum=None):
        raw = r.encoded(receipt)
        (self.root / r.RECEIPT).write_bytes(raw)
        return r.verify_artifact(self.root, self.root, expected, checksum or r.sha(raw))

    def test_admission_envelope_control(self):
        receipt = self.fixture()
        actual, stage = self.verify_fixture(receipt)
        self.assertEqual(actual, receipt)
        self.assertEqual(stage, {'test_double': True})

    def test_admission_receipt_external_pin_refused(self):
        with self.assertRaisesRegex(ValueError, 'INITIAL_COMPILE_RECEIPT_PIN'):
            self.verify_fixture(self.fixture(), checksum='0' * 64)

    def test_admission_expected_checkout_revision_refused(self):
        with self.assertRaisesRegex(ValueError, 'INITIAL_EXPECTED_CHECKOUT_REVISION'):
            self.verify_fixture(self.fixture(), expected='c' * 40)

    def test_admission_final_checkout_revision_change_refused(self):
        receipt = self.fixture()
        with patch.object(r, 'git', side_effect=[('a' * 40 + '\n').encode(), ('c' * 40 + '\n').encode()]):
            with self.assertRaisesRegex(ValueError, 'INITIAL_CHECKOUT_REVISION_CHANGED'):
                self.verify_fixture(receipt)

    def test_admission_source_revision_and_role_refused(self):
        receipt = self.fixture()
        for key, value in (('source_revision', 'c' * 40), ('build_role', 'accepted_old_role'),
                           ('passed', 1), ('runtime_executed', 0), ('world_authority', True)):
            changed = {**receipt, key: value}
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'INITIAL_COMPILE_SCOPE'):
                self.verify_fixture(changed)

    def test_admission_unknown_field_refused(self):
        receipt = self.fixture()
        with self.assertRaisesRegex(ValueError, 'INITIAL_COMPILE_FIELDS'):
            self.verify_fixture({**receipt, 'private_log': 'unexpected'})

    def test_admission_supplier_and_artifact_hash_refused(self):
        receipt = self.fixture()
        changed = {**receipt, 'source_closure_sha256': {'supplier': 'c' * 64}}
        with self.assertRaisesRegex(ValueError, 'INITIAL_COMPILE_SOURCE_CLOSURE'):
            self.verify_fixture(changed)
        receipt['artifacts']['MapServer.exe']['sha256'] = 'd' * 64
        with self.assertRaisesRegex(ValueError, 'INITIAL_COMPILE_ARTIFACT_HASH'):
            self.verify_fixture(receipt)


if __name__ == '__main__':
    unittest.main(verbosity=2)
