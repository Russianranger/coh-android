"""Fixed profile-path observation controls; no compiler, WinAPI or model."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


p = load('profile_preparation', 'prepare_profile_diagnostic.py')
s = load('profile_supervisor', 'supervise_inert.py')


class ProfileDiagnosticControls(unittest.TestCase):
    def test_exact_reversal_and_strict_predecessor(self):
        original = p.source_bytes()
        generated = p.prepare(original)
        self.assertEqual(hashlib.sha256(original).hexdigest(), p.BASE_IDENTITY_SHA256)
        self.assertEqual(hashlib.sha256(generated).hexdigest(), s.PROFILE_SOURCE_SHA256)
        self.assertEqual(len(generated), 50395)
        restored = generated.decode()
        for old, new in reversed(p.replacements()):
            self.assertEqual(restored.count(new), 1)
            restored = restored.replace(new, old, 1)
        self.assertEqual(restored.encode(), original)
        self.assertEqual(s.PROFILE_FILE_PHASES, s.IDENTITY_FILE_PHASES | set(p.EXTRA_PHASES))
        self.assertEqual(s.PROFILE_FILE_OPERATIONS, s.IDENTITY_FILE_OPERATIONS | set(p.EXTRA_OPERATIONS))
        for raw in (original+b'\n', original[:-1], b'x'+original[1:]):
            with self.assertRaises(ValueError):
                p.prepare(raw)

    def test_environment_and_existing_security_identity_lifecycle_exact(self):
        before = p.source_bytes().decode()
        after = p.prepare(before.encode()).decode()
        for a,b in [('  string Sddl(', '  FileStream NewFile('),
                    ('  FileStream NewFile(', '  void Journal('),
                    ('  public void Launch(', '  void Identity('),
                    ('  public void StopJob(', '  // Held native identities'),
                    ('   bool Equal(', '   public void Close(')]:
            # Whole spans preserve actual identity and all security predicates.
            if b not in before and a == '  public void StopJob(':
                b='  // closed before identity-checked deletion.'
            self.assertEqual(before[before.index(a):before.index(b)], after[after.index(a):after.index(b)])
        self.assertNotIn('SystemDrive', after)
        self.assertIn('FileDiagnostic.At(FilePhase.PROFILE_ROOT_QUERY);uint cap=', after)
        self.assertIn('FileDiagnostic.At(FilePhase.PROFILE_ROOT_PATH);string profiles=PathLocal', after)
        self.assertIn('FileDiagnostic.At(FilePhase.PROFILE_ROOT_CHAIN);Chain(profiles)', after)

    def value(self):
        return {'schema':'coh-owned-profile-inert-process-profile-path-diagnostic-v1',
                **{key:key not in s.FALSE_ON_SUCCESS for key in s.BOOL_FIELDS},
                'passed':False,'first_failure':'FILES','first_cleanup_failure':'NONE',
                'file_phase':'PROFILE_ROOT_PATH','file_operation':'PATH_FORM'}

    def test_fixed_predicates_require_distinct_schema_and_scope(self):
        encode=lambda value:json.dumps(value,separators=(',',':')).encode()+b'\n'
        for operation in p.EXTRA_OPERATIONS:
            value={**self.value(),'file_operation':operation}
            self.assertEqual(s.parse_receipt(encode(value),profile_diagnostic=True)['file_operation'],operation)
            for mode in ({},{'file_diagnostic':True},{'identity_diagnostic':True}):
                with self.assertRaises(s.Refusal):s.parse_receipt(encode(value),**mode)
        for field in ('file_phase','file_operation'):
            with self.assertRaises(s.Refusal):
                s.parse_receipt(encode({**self.value(),field:'PRIVATE_PATH_ERROR_SID_CANARY'}),profile_diagnostic=True)
        with self.assertRaises(s.Refusal):
            s.parse_receipt(encode({**self.value(),'passed':True,'first_failure':'NONE'}),profile_diagnostic=True)

    def test_compile_artifact_requires_exact_source_and_observation_scope(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary);target=directory/'profile-path';target.mkdir()
            image=target/'OwnedProfileProcess.exe';image.write_bytes(b'profile-observer-not-executed')
            value=dict(schema='coh-wpp-profile-path-build-v1',passed=True,compiler_invocations=1,
                original_source_sha256=s.SOURCE_PINS['OwnedProfileProcess.cs'],
                observed_source_sha256=s.DIAGNOSTIC_SOURCE_SHA256,owner_source_sha256=s.FILE_OWNER_SOURCE_SHA256,
                identity_source_sha256=s.IDENTITY_SOURCE_SHA256,generated_source_sha256=s.PROFILE_SOURCE_SHA256,
                generated_source_bytes=50395,exact_reverse_verified=True,selected_compiler_files_match_accepted_build=True,
                explicit_file_security_at_create=True,existing_owner_acl_identity_guards_preserved=True,
                profile_path_observation_only=True,accepted_inert_probe_recompiled=False,
                accepted_model_recompiled_or_executed=False,helper_executed=False,source_generation_admitted=False,
                world_authority=False,helper_image=dict(bytes=image.stat().st_size,sha256=s.sha(image)))
            receipt=target/'profile-build.json';receipt.write_text(json.dumps(value))
            self.assertEqual(s.admit_profile_path(directory),(image,s.sha(image)))
            changes=[('schema','coh-wpp-file-identity-build-v1'),('compiler_invocations',3),('generated_source_bytes',49689)]
            changes += [(key,'0'*64) for key in value if key.endswith('_sha256')]
            changes += [(key,not replacement) for key,replacement in value.items() if type(replacement) is bool]
            for key,replacement in changes:
                receipt.write_text(json.dumps({**value,key:replacement}))
                with self.subTest(key=key),self.assertRaises(s.Refusal):s.admit_profile_path(directory)
            receipt.write_text(json.dumps(value));image.write_bytes(b'replaced')
            with self.assertRaises(s.Refusal):s.admit_profile_path(directory)

    def test_mode_conflicts_refuse_before_artifact_and_windows_actions(self):
        for old in ('file_diagnostic','file_owner','identity_diagnostic'):
            with mock.patch.object(s,'admit_artifact') as artifact,mock.patch.object(s,'Native') as native:
                status,receipt=s.execute('UNREAD','UNCREATED',profile_diagnostic=True,**{old:True})
            artifact.assert_not_called();native.assert_not_called()
            self.assertFalse(status['passed']);self.assertFalse(status['actual_helper_started']);self.assertIsNone(receipt)

    def test_actual_context_is_retained_without_inventing_identity_mismatch(self):
        directory=Path(__file__).parent.parent/'qualification'/'windows-profile-identity-diagnostic-20261018'/'run-39153370534'
        value=s.decode_json((directory/'inert-result.json').read_bytes())
        receipt=s.parse_receipt(json.dumps(value,separators=(',',':')).encode()+b'\n',identity_diagnostic=True)
        self.assertEqual((receipt['first_failure'],receipt['file_phase'],receipt['file_operation']),
                         ('FILES','ACCOUNT_SID_JOURNAL','SAME_IDENTITY'))
        self.assertTrue(receipt['cleanup_complete']);self.assertTrue(receipt['owned_account_absent'])
        self.assertFalse(receipt['created_suspended']);self.assertFalse(receipt['world_authority'])


if __name__=='__main__':unittest.main()
