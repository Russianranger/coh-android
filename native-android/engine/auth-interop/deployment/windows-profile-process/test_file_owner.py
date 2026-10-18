"""Focused successor admission controls; no compiler, WinAPI, model or service."""

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


p = load('file_owner_preparation', 'prepare_file_owner.py')
s = load('file_owner_supervisor', 'supervise_inert.py')


class FileOwnerControls(unittest.TestCase):
    def test_successor_reverses_to_exact_actually_observed_helper(self):
        observed = p.source_bytes()
        generated = p.prepare(observed)
        self.assertEqual(hashlib.sha256(observed).hexdigest(), p.BASE_DIAGNOSTIC_SHA256)
        self.assertEqual(hashlib.sha256(generated).hexdigest(), s.FILE_OWNER_SOURCE_SHA256)
        self.assertEqual(len(generated), 47790)
        reversed_source = generated.decode()
        for old, new in reversed(p.replacements()):
            self.assertEqual(reversed_source.count(new), 1)
            reversed_source = reversed_source.replace(new, old, 1)
        self.assertEqual(reversed_source.encode(), observed)
        # The only changed old expressions are four private CreateNew calls.
        self.assertEqual(len(p.replacements()), 5)
        self.assertTrue(all('new FileStream(' in old and 'FileMode.CreateNew' in old
                            for old, _ in p.replacements()[1:]))

    def test_changed_observation_source_refused_before_any_generation(self):
        observed = p.source_bytes()
        for replacement in (observed+b'\n', b'x'+observed[1:], observed[:-1]):
            with self.subTest(length=len(replacement)), self.assertRaises(ValueError):
                p.prepare(replacement)

    def test_original_owner_acl_identity_launch_and_cleanup_guards_byte_exact(self):
        observed = p.source_bytes().decode()
        generated = p.prepare(observed.encode()).decode()
        # Whole existing methods, not snippets, must remain byte exact.
        for begin, end in (
            ('  string Sddl(', '  void Acl('),
            ('  void Acl(', '  void MakeDir('),
            ('  void MakeDir(', '  void Journal('),
            ('  public void Launch(', '  void Identity('),
            ('  void Identity(', '  string TokenSid('),
            ('  public void StopJob(', '  public void RetireFiles('),
            ('  public void RetireFiles(', '  sealed class Pin'),
        ):
            original_method = observed[observed.index(begin):observed.index(end)]
            # NewFile is inserted after MakeDir; exclude precisely that new method.
            successor_method = generated[generated.index(begin):generated.index(end)]
            if begin == '  void MakeDir(':
                successor_method = successor_method[:successor_method.index('  FileStream NewFile(')]
            self.assertEqual(successor_method, original_method)
        self.assertNotIn('File.SetAccessControl(', generated)
        self.assertNotIn('SetTokenInformation(', generated)

    def value(self, image):
        return dict(schema='coh-wpp-file-owner-build-v1', passed=True,
                    compiler_invocations=1,
                    original_source_sha256=s.SOURCE_PINS['OwnedProfileProcess.cs'],
                    observed_source_sha256=s.DIAGNOSTIC_SOURCE_SHA256,
                    generated_source_sha256=s.FILE_OWNER_SOURCE_SHA256,
                    generated_source_bytes=47790, exact_reverse_verified=True,
                    selected_compiler_files_match_accepted_build=True,
                    explicit_file_security_at_create=True,
                    existing_owner_acl_identity_guards_preserved=True,
                    accepted_inert_probe_recompiled=False,
                    accepted_model_recompiled_or_executed=False,
                    helper_executed=False, source_generation_admitted=False,
                    world_authority=False,
                    helper_image=dict(bytes=image.stat().st_size, sha256=s.sha(image)))

    def test_new_artifact_identity_provenance_and_scope_refuse_mutations(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            target = directory/'file-owner'
            target.mkdir()
            image = target/'OwnedProfileProcess.exe'
            image.write_bytes(b'new-successor-not-executed-fixture')
            receipt = target/'owner-build.json'
            value = self.value(image)
            receipt.write_text(json.dumps(value))
            self.assertEqual(s.admit_file_owner(directory), (image, s.sha(image)))
            replacements = [
                ('schema', 'coh-wpp-file-diagnostic-build-v1'),
                ('original_source_sha256', '0'*64), ('observed_source_sha256', '0'*64),
                ('generated_source_sha256', s.DIAGNOSTIC_SOURCE_SHA256),
                ('generated_source_bytes', 47405), ('compiler_invocations', 3),
                ('passed', False), ('exact_reverse_verified', False),
                ('selected_compiler_files_match_accepted_build', False),
                ('explicit_file_security_at_create', False),
                ('existing_owner_acl_identity_guards_preserved', False),
                ('accepted_inert_probe_recompiled', True),
                ('accepted_model_recompiled_or_executed', True), ('helper_executed', True),
                ('source_generation_admitted', True), ('world_authority', True),
            ]
            for key, replacement in replacements:
                receipt.write_text(json.dumps({**value, key: replacement}))
                with self.subTest(key=key), self.assertRaises(s.Refusal):
                    s.admit_file_owner(directory)
            receipt.write_text(json.dumps(value))
            image.write_bytes(b'replaced')
            with self.assertRaises(s.Refusal):
                s.admit_file_owner(directory)

    def test_conflicting_modes_refused_before_artifact_or_windows_actions(self):
        with mock.patch.object(s, 'admit_artifact') as artifact, mock.patch.object(s, 'Native') as native:
            status, receipt = s.execute('UNREAD_PRIVATE_ARTIFACT', 'UNCREATED_PRIVATE_PARENT',
                                        file_diagnostic=True, file_owner=True)
        artifact.assert_not_called()
        native.assert_not_called()
        self.assertFalse(status['passed'])
        self.assertFalse(status['actual_helper_started'])
        self.assertIsNone(receipt)

    def test_preserved_actual_failure_retains_first_cause_and_cleanup_scope(self):
        directory = Path(__file__).parent.parent/'qualification'/'windows-profile-file-diagnostic-20261018'/'run-39124469057'
        value = s.decode_json((directory/'inert-result.json').read_bytes())
        receipt = s.parse_receipt(json.dumps(value, separators=(',', ':')).encode()+b'\n',
                                  file_diagnostic=True)
        self.assertEqual((receipt['first_failure'], receipt['file_phase'], receipt['file_operation']),
                         ('FILES', 'JOURNAL_ACL', 'ACL_OWNER'))
        self.assertTrue(receipt['cleanup_complete'])
        self.assertFalse(receipt['owned_account_created'])
        self.assertFalse(receipt['auth_db_map_or_service_authority_admitted'])
        self.assertFalse(receipt['world_authority'])


if __name__ == '__main__':
    unittest.main()
