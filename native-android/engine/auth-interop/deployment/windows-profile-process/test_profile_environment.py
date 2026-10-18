"""Normal environment repair and retained-helper admission controls only."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

spec=importlib.util.spec_from_file_location('profile_environment_supervisor',Path(__file__).with_name('supervise_inert.py'))
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
EVIDENCE=Path(__file__).parent.parent/'qualification'/'windows-profile-path-diagnostic-20261018'/'run-39154121730'


class ProfileEnvironmentControls(unittest.TestCase):
    def source(self):
        return dict(SystemRoot='C:\\Windows',WINDIR='c:\\Windows',SystemDrive='C:',TEMP='D:\\temp',TMP='D:\\tmp',
                    USERPROFILE='PRIVATE_USER',TOKEN='PRIVATE_CREDENTIAL',PATH='PRIVATE_PATH')

    def test_new_mode_inherits_only_validated_normal_drive_and_original_four(self):
        source=self.source();old={key:source[key] for key in ('SystemRoot','WINDIR','TEMP','TMP')}
        self.assertEqual(s.helper_environment(source),old)
        self.assertEqual(s.helper_environment(source,system_drive=True),{**old,'SystemDrive':'C:'})
        self.assertEqual(source,self.source())
        self.assertNotIn('USERPROFILE',s.helper_environment(source,system_drive=True))
        self.assertNotIn('TOKEN',s.helper_environment(source,system_drive=True))
        self.assertNotIn('PATH',s.helper_environment(source,system_drive=True))
        source['SystemDrive']='c:'
        self.assertEqual(s.helper_environment(source,system_drive=True)['SystemDrive'],'c:')

    def test_drive_form_and_both_root_drive_agreements_refuse(self):
        for drive in (None,1,'C','C:\\','\\\\host\\share','%SystemDrive%','C:$','C:\x00'):
            with self.subTest(drive_type=type(drive).__name__),self.assertRaises(s.Refusal):
                s.helper_environment({**self.source(),'SystemDrive':drive},system_drive=True)
        for name in ('SystemRoot','WINDIR'):
            for value in (None,1,'D:\\Windows','C:Windows','\\\\host\\Windows','C:\\'):
                with self.subTest(name=name,value_type=type(value).__name__),self.assertRaises(s.Refusal):
                    s.helper_environment({**self.source(),name:value},system_drive=True)
            source=self.source();del source[name]
            with self.assertRaises(s.Refusal):s.helper_environment(source,system_drive=True)

    def test_exact_actual_retained_observer_admitted_without_compile_claim(self):
        raw=(EVIDENCE/'helper-artifact.zip').read_bytes()
        self.assertEqual(len(raw),33239)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'0d9a6e2870c18f463a73df37b8c16dc27b793cafa52d7c9d941efe5551720cf5')
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary);target=directory/'profile-path';target.mkdir()
            with zipfile.ZipFile(EVIDENCE/'helper-artifact.zip') as archive:
                self.assertEqual(set(archive.namelist()),{'OwnedProfileProcess.exe','OwnedProfileProcessProfileDiagnostic.cs','preparation.json','profile-build.json'})
                for name in archive.namelist():(target/name).write_bytes(archive.read(name))
            image,pin=s.admit_profile_path(directory)
            self.assertEqual(image.stat().st_size,38400)
            self.assertEqual(pin,'c6df10d121ea73e2ed8675465593b704f2a97b35289bc00d24ac1b7ee4219069')
            original={'OwnedProfileProcess.exe':(directory/'old.exe','0'*64),
                      'InertProfileProbe.exe':(directory/'probe.exe','1'*64)}
            with mock.patch.object(s,'admit_artifact',return_value=original),mock.patch.object(s,'Native',side_effect=s.Refusal('PLATFORM')),mock.patch.object(s.subprocess,'Popen') as process:
                status,receipt=s.execute(directory,directory/'uncreated',profile_system_drive=True)
            process.assert_not_called();self.assertIsNone(receipt)
            self.assertTrue(status['retained_profile_helper_reused'])
            self.assertTrue(status['system_drive_environment_requested'])
            self.assertFalse(status['compiler_or_model_reexecuted'])
            self.assertFalse(status['changed_helper_compiled_only'])
            self.assertEqual(status['new_helper_compiler_invocations'],0)
            self.assertFalse(status['passed'])

    def test_all_other_modes_conflict_before_artifact_or_windows_actions(self):
        for old in ('file_diagnostic','file_owner','identity_diagnostic','profile_diagnostic'):
            with mock.patch.object(s,'admit_artifact') as artifact,mock.patch.object(s,'Native') as native:
                status,receipt=s.execute('UNREAD','UNCREATED',profile_system_drive=True,**{old:True})
            artifact.assert_not_called();native.assert_not_called();self.assertIsNone(receipt)
            self.assertFalse(status['passed']);self.assertFalse(status['actual_helper_started'])

    def test_observed_path_form_failure_retains_cleanup_and_no_causality_claim(self):
        value=s.decode_json((EVIDENCE/'inert-result.json').read_bytes())
        receipt=s.parse_receipt(json.dumps(value,separators=(',',':')).encode()+b'\n',profile_diagnostic=True)
        self.assertEqual((receipt['first_failure'],receipt['file_phase'],receipt['file_operation']),('FILES','PROFILE_ROOT_PATH','PATH_FORM'))
        self.assertTrue(receipt['cleanup_complete']);self.assertTrue(receipt['owned_account_absent'])
        self.assertFalse(receipt['created_suspended']);self.assertFalse(receipt['world_authority'])
        for name,pin in s.SOURCE_PINS.items():
            self.assertEqual(hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest(),pin)


if __name__=='__main__':unittest.main()
