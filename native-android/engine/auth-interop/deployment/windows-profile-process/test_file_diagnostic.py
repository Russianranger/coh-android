"""Focused new diagnostic source/receipt controls; no compiler/WinAPI/model."""

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


p = load('file_preparation', 'prepare_file_diagnostic.py')
s = load('diagnostic_supervisor', 'supervise_inert.py')


class DiagnosticControls(unittest.TestCase):
    def test_exact_reversible_generation_preserves_accepted_source(self):
        original = Path(__file__).with_name('OwnedProfileProcess.cs').read_bytes()
        generated = p.prepare(original)
        self.assertEqual(hashlib.sha256(original).hexdigest(), p.BASE_SHA256)
        self.assertEqual(hashlib.sha256(generated).hexdigest(), s.DIAGNOSTIC_SOURCE_SHA256)
        self.assertEqual(len(generated), 47405)
        restored = generated.decode()
        for old, new in reversed(p.replacements()):
            self.assertEqual(restored.count(new), 1)
            restored = restored.replace(new, old, 1)
        self.assertEqual(restored.encode(), original)
        self.assertEqual(set(p.PHASES), s.FILE_PHASES)
        self.assertEqual(set(p.OPERATIONS), s.FILE_OPERATIONS)

    def test_changed_baseline_refused_before_generation(self):
        original = Path(__file__).with_name('OwnedProfileProcess.cs').read_bytes()
        with self.assertRaises(ValueError):
            p.prepare(original+b'\n')

    def value(self):
        return {'schema': 'coh-owned-profile-inert-process-file-diagnostic-v1',
                **{key: key not in s.FALSE_ON_SUCCESS for key in s.BOOL_FIELDS},
                'passed': False, 'first_failure': 'FILES', 'first_cleanup_failure': 'NONE',
                'file_phase': 'PARENT_ACL', 'file_operation': 'ACL_RULE'}

    def test_diagnostic_role_preserves_failure_and_requires_exact_enum(self):
        value = self.value()
        encoded = lambda item: json.dumps(item, separators=(',', ':')).encode()+b'\n'
        result = s.parse_receipt(encoded(value), file_diagnostic=True)
        self.assertEqual(result['file_phase'], 'PARENT_ACL')
        self.assertEqual(result['file_operation'], 'ACL_RULE')
        self.assertFalse(result['passed'])
        with self.assertRaises(s.Refusal):
            s.parse_receipt(encoded(value))
        for key in ('file_phase', 'file_operation'):
            with self.subTest(key=key), self.assertRaises(s.Refusal):
                s.parse_receipt(encoded({**value, key: 'PRIVATE_PATH_CANARY'}), file_diagnostic=True)
        success = {**value, 'passed': True, 'first_failure': 'NONE'}
        with self.assertRaises(s.Refusal):
            s.parse_receipt(encoded(success), file_diagnostic=True)
        success.update(file_phase='NONE', file_operation='NONE')
        self.assertTrue(s.parse_receipt(encoded(success), file_diagnostic=True)['passed'])

    def test_diagnostic_build_binds_exact_successor_image_and_scope(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            target = directory/'file-diagnostic'
            target.mkdir()
            image = target/'OwnedProfileProcess.exe'
            image.write_bytes(b'not-executed-diagnostic-fixture')
            value = dict(schema='coh-wpp-file-diagnostic-build-v1', passed=True,
                         compiler_invocations=1, original_source_sha256=p.BASE_SHA256,
                         generated_source_sha256=s.DIAGNOSTIC_SOURCE_SHA256,
                         generated_source_bytes=47405, exact_reverse_verified=True,
                         selected_compiler_files_match_accepted_build=True,
                         accepted_inert_probe_recompiled=False,
                         accepted_model_recompiled_or_executed=False,
                         helper_executed=False, source_generation_admitted=False,
                         world_authority=False,
                         helper_image=dict(bytes=image.stat().st_size, sha256=s.sha(image)))
            receipt = target/'diagnostic-build.json'
            receipt.write_text(json.dumps(value))
            self.assertEqual(s.admit_file_diagnostic(directory)[0], image)
            for key, replacement in (
                ('generated_source_sha256', '0'*64),
                ('accepted_model_recompiled_or_executed', True),
                ('compiler_invocations', 3), ('helper_executed', True),
            ):
                receipt.write_text(json.dumps({**value, key: replacement}))
                with self.subTest(key=key), self.assertRaises(s.Refusal):
                    s.admit_file_diagnostic(directory)
            receipt.write_text(json.dumps(value))
            image.write_bytes(b'replaced')
            with self.assertRaises(s.Refusal):
                s.admit_file_diagnostic(directory)


if __name__ == '__main__':
    unittest.main()
