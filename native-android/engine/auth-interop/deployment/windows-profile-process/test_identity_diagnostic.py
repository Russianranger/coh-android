"""New identity-only source/admission controls; no compiler, WinAPI or model."""

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


p = load('identity_preparation', 'prepare_identity_diagnostic.py')
s = load('identity_supervisor', 'supervise_inert.py')


class IdentityDiagnosticControls(unittest.TestCase):
    def test_exact_reversal_retains_actual_owner_successor_and_new_enums(self):
        original = p.source_bytes()
        generated = p.prepare(original)
        self.assertEqual(hashlib.sha256(original).hexdigest(), p.BASE_OWNER_SHA256)
        self.assertEqual(hashlib.sha256(generated).hexdigest(), s.IDENTITY_SOURCE_SHA256)
        self.assertEqual(len(generated), 49689)
        restored = generated.decode()
        for old, new in reversed(p.replacements()):
            self.assertEqual(restored.count(new), 1)
            restored = restored.replace(new, old, 1)
        self.assertEqual(restored.encode(), original)
        self.assertEqual(s.IDENTITY_FILE_PHASES, s.FILE_PHASES | set(p.EXTRA_PHASES))
        self.assertEqual(s.IDENTITY_FILE_OPERATIONS, s.FILE_OPERATIONS | set(p.EXTRA_OPERATIONS))
        for value in (original+b'\n', b'x'+original[1:], original[:-1]):
            with self.assertRaises(ValueError):
                p.prepare(value)

    def test_whole_equal_predicates_and_short_circuit_order_remain(self):
        original = p.source_bytes().decode()
        generated = p.prepare(original.encode()).decode()
        begin, end = '   bool Equal(', '   public void Same('
        before = original[original.index(begin):original.index(end)]
        after = generated[generated.index(begin):generated.index(end)]
        comparisons = re.findall(r'FileDiagnostic.Match\(([^,]+),FileOperation.(IDENTITY_[A-Z_]+)\)', after)
        self.assertEqual([operation for _, operation in comparisons], p.EXTRA_OPERATIONS[1:])
        self.assertEqual(len(comparisons), 6)
        stripped = re.sub(r'FileDiagnostic.Match\(([^,]+),FileOperation.IDENTITY_[A-Z_]+\)', r'\1', after)
        self.assertEqual(stripped, before)
        self.assertIn('if(!value&&Mismatch==FileOperation.NONE)Mismatch=operation;return value;', generated)
        self.assertIn('r.fileOperation=Mismatch==FileOperation.NONE?Operation:Mismatch;', generated)
        # The nested witness is selected at the pre-cleanup latch; no metadata
        # values or extra raw exception fields enter the public receipt.
        self.assertEqual(generated.count('FileDiagnostic.Match(N.GetFileInformationByHandle(h,out b),FileOperation.IDENTITY_QUERY)'), 1)
        self.assertEqual(generated.count('FileDiagnostic.Latch(r);'), 2)

    def value(self):
        return {'schema': 'coh-owned-profile-inert-process-file-identity-diagnostic-v1',
                **{key: key not in s.FALSE_ON_SUCCESS for key in s.BOOL_FIELDS},
                'passed': False, 'first_failure': 'FILES', 'first_cleanup_failure': 'NONE',
                'file_phase': 'COPY_SOURCE', 'file_operation': 'IDENTITY_QUERY'}

    def test_identity_scope_requires_new_schema_and_only_fixed_atoms(self):
        encoded = lambda value: json.dumps(value, separators=(',', ':')).encode()+b'\n'
        for operation in p.EXTRA_OPERATIONS:
            value = {**self.value(), 'file_operation': operation}
            self.assertEqual(s.parse_receipt(encoded(value), identity_diagnostic=True)['file_operation'], operation)
            for old in ({}, {'file_diagnostic': True}):
                with self.assertRaises(s.Refusal):
                    s.parse_receipt(encoded(value), **old)
        for field in ('file_phase', 'file_operation'):
            with self.assertRaises(s.Refusal):
                s.parse_receipt(encoded({**self.value(), field: 'PRIVATE_PATH_SID_ERROR_CANARY'}), identity_diagnostic=True)
        value = {**self.value(), 'passed': True, 'first_failure': 'NONE'}
        with self.assertRaises(s.Refusal):
            s.parse_receipt(encoded(value), identity_diagnostic=True)
        value.update(file_phase='NONE', file_operation='NONE')
        self.assertTrue(s.parse_receipt(encoded(value), identity_diagnostic=True)['passed'])

    def test_new_compilation_artifact_requires_exact_identity_observation(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            target = directory/'file-identity'
            target.mkdir()
            image = target/'OwnedProfileProcess.exe'
            image.write_bytes(b'identity-fixture-not-executed')
            value = dict(schema='coh-wpp-file-identity-build-v1', passed=True,
                         compiler_invocations=1, original_source_sha256=s.SOURCE_PINS['OwnedProfileProcess.cs'],
                         observed_source_sha256=s.DIAGNOSTIC_SOURCE_SHA256,
                         owner_source_sha256=s.FILE_OWNER_SOURCE_SHA256,
                         generated_source_sha256=s.IDENTITY_SOURCE_SHA256,
                         generated_source_bytes=49689, exact_reverse_verified=True,
                         selected_compiler_files_match_accepted_build=True,
                         explicit_file_security_at_create=True,
                         existing_owner_acl_identity_guards_preserved=True,
                         identity_observation_only=True, accepted_inert_probe_recompiled=False,
                         accepted_model_recompiled_or_executed=False, helper_executed=False,
                         source_generation_admitted=False, world_authority=False,
                         helper_image=dict(bytes=image.stat().st_size, sha256=s.sha(image)))
            receipt = target/'identity-build.json'
            receipt.write_text(json.dumps(value))
            self.assertEqual(s.admit_file_identity(directory), (image, s.sha(image)))
            mutations = [('schema', 'coh-wpp-file-owner-build-v1'), ('generated_source_bytes', 47790)]
            mutations += [(key, '0'*64) for key in ('original_source_sha256', 'observed_source_sha256',
                           'owner_source_sha256', 'generated_source_sha256')]
            mutations += [(key, not replacement) for key, replacement in value.items() if type(replacement) is bool]
            mutations += [('compiler_invocations', 3)]
            for key, replacement in mutations:
                receipt.write_text(json.dumps({**value, key: replacement}))
                with self.subTest(key=key), self.assertRaises(s.Refusal):
                    s.admit_file_identity(directory)
            receipt.write_text(json.dumps(value))
            image.write_bytes(b'replaced')
            with self.assertRaises(s.Refusal):
                s.admit_file_identity(directory)

    def test_identity_mode_conflicts_refuse_before_artifact_or_windows_calls(self):
        for old in ('file_diagnostic', 'file_owner'):
            with mock.patch.object(s, 'admit_artifact') as artifact, mock.patch.object(s, 'Native') as native:
                status, receipt = s.execute('UNREAD_ARTIFACT', 'UNCREATED_PARENT',
                                            identity_diagnostic=True, **{old: True})
            artifact.assert_not_called()
            native.assert_not_called()
            self.assertFalse(status['passed'])
            self.assertFalse(status['actual_helper_started'])
            self.assertIsNone(receipt)

    def test_actual_owner_result_preserves_new_account_cleanup_and_unknown_atom(self):
        directory = Path(__file__).parent.parent/'qualification'/'windows-profile-file-owner-20261018'/'run-39152328268'
        value = s.decode_json((directory/'inert-result.json').read_bytes())
        receipt = s.parse_receipt(json.dumps(value, separators=(',', ':')).encode()+b'\n', file_diagnostic=True)
        self.assertEqual((receipt['first_failure'], receipt['file_phase'], receipt['file_operation']),
                         ('FILES', 'NONE', 'SAME_IDENTITY'))
        self.assertTrue(receipt['cleanup_complete'])
        self.assertTrue(receipt['owned_account_created'])
        self.assertTrue(receipt['exact_sid_bound'])
        self.assertTrue(receipt['owned_account_absent'])
        self.assertFalse(receipt['created_suspended'])
        self.assertFalse(receipt['world_authority'])


if __name__ == '__main__':
    unittest.main()
