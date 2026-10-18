"""New supervisor boundary controls; no accepted model or Windows APIs run."""

import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


SPEC = importlib.util.spec_from_file_location('wpp_supervisor', Path(__file__).with_name('supervise_inert.py'))
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def receipt(passed=True):
    value = {'schema': 'coh-owned-profile-inert-process-v1',
             **{key: key not in m.FALSE_ON_SUCCESS for key in m.BOOL_FIELDS},
             'first_failure': 'NONE', 'first_cleanup_failure': 'NONE'}
    value['passed'] = passed
    if not passed:
        value['first_failure'] = 'LAUNCH'
        value['inert_hkcu_probe_verified'] = False
    return value


def encode(value):
    return json.dumps(value, separators=(',', ':')).encode('ascii')+b'\n'


class ReceiptControls(unittest.TestCase):
    def test_fixed_success_and_failed_native_result_preserved(self):
        for passed in (True, False):
            value = m.parse_receipt(encode(receipt(passed)))
            self.assertIs(value['passed'], passed)
            self.assertFalse(value['probe_build_provenance_verified'])

    def test_extra_missing_duplicate_and_nonbool_refused(self):
        original = receipt()
        for value in ({**original, 'private_path': 'never export'},
                      {key: item for key, item in original.items() if key != 'world_authority'},
                      {**original, 'passed': 1}, {**original, 'owned_job_empty_observed': 1}):
            with self.assertRaises(m.Refusal):
                m.parse_receipt(encode(value))
        raw = encode(original).replace(b'{', b'{"passed":true,', 1)
        with self.assertRaises(m.Refusal):
            m.parse_receipt(raw)

    def test_false_cleanup_or_absence_never_pass(self):
        for field in m.BOOL_FIELDS-m.FALSE_ON_SUCCESS:
            if field == 'passed':
                continue
            with self.subTest(field=field), self.assertRaises(m.Refusal):
                m.parse_receipt(encode({**receipt(), field: False}))

    def test_scope_and_failure_cause_never_promoted(self):
        for field in m.FALSE_ON_SUCCESS:
            with self.subTest(field=field), self.assertRaises(m.Refusal):
                m.parse_receipt(encode({**receipt(), field: True}))
        with self.assertRaises(m.Refusal):
            m.parse_receipt(encode({**receipt(), 'first_failure': 'private path'}))

    def test_output_boundary_refuses_extra_lines_unicode_or_size(self):
        raw = encode(receipt())
        for value in (raw+raw, raw+b'private', b'\n'+raw,
                      raw.replace(b'NONE', b'\xc3\xa9', 1), b'x'*(m.OUTPUT_LIMIT+1)):
            with self.assertRaises((m.Refusal, ValueError)):
                m.parse_receipt(value)


class AdmissionControls(unittest.TestCase):
    def fixture(self, directory):
        source = Path(__file__).parent
        build = dict(schema='coh-owned-profile-inert-build-v1', passed=True,
                     compiler_invocations=3, target='x64',
                     output_executable_or_model_tests_executed=False,
                     account_or_profile_or_gui_api_executed=False,
                     inputs={name: {'sha256': digest, 'bytes': (source/name).stat().st_size}
                             for name, digest in m.SOURCE_PINS.items()}, outputs={})
        for name in ('OwnedProfileProcess.exe', 'InertProfileProbe.exe'):
            path = directory/name
            path.write_bytes(b'fixture-not-executed-'+name.encode())
            build['outputs'][name] = dict(bytes=path.stat().st_size, sha256=m.sha(path))
        documents = {
            'build.json': build,
            'source-admission.json': dict(schema='coh-owned-profile-model-source-admission-v1',
                passed=True, source_revision=m.BUILD_REVISION,
                source_sha256={'native-android/engine/auth-interop/deployment/windows-profile-process/'+name: digest
                               for name, digest in m.SOURCE_PINS.items()}),
            'summary.json': dict(schema='coh-owned-profile-build-model-public-summary-v1',
                source_admission_passed=True, compile_passed=True, new_model_passed=True,
                actual_profile_helper_executed=False),
            'model-status.json': dict(schema='coh-owned-profile-process-model-controls-v1',
                passed=True, model_result_valid=True, scenarios=36, actual_windows_api_executed=False),
        }
        for name, value in documents.items():
            (directory/name).write_bytes(encode(value))
        return documents

    def test_exact_source_artifact_identity_then_image_mutation_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.fixture(directory)
            self.assertEqual(set(m.admit_artifact(directory)),
                             {'OwnedProfileProcess.exe', 'InertProfileProbe.exe'})
            (directory/'InertProfileProbe.exe').write_bytes(b'replaced')
            with self.assertRaises(m.Refusal):
                m.admit_artifact(directory)

    def test_prior_api_execution_or_wrong_revision_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            docs = self.fixture(directory)
            for name, key, replacement in (
                ('source-admission.json', 'source_revision', '0'*40),
                ('model-status.json', 'actual_windows_api_executed', True),
                ('summary.json', 'actual_profile_helper_executed', True),
                ('build.json', 'account_or_profile_or_gui_api_executed', True),
            ):
                old = docs[name][key]
                docs[name][key] = replacement
                (directory/name).write_bytes(encode(docs[name]))
                with self.subTest(name=name), self.assertRaises(m.Refusal):
                    m.admit_artifact(directory)
                docs[name][key] = old
                (directory/name).write_bytes(encode(docs[name]))

    def test_platform_refusal_does_not_launch_or_invent_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.fixture(directory)
            with mock.patch.object(m, 'Native', side_effect=m.Refusal('PLATFORM')), mock.patch.object(m.subprocess, 'Popen') as launch:
                status, native = m.execute(directory, directory/'new-private-parent')
            launch.assert_not_called()
            self.assertEqual(status['first_failure'], 'PLATFORM')
            self.assertIsNone(native)
            self.assertFalse(status['passed'])
            self.assertFalse(status['inner_cleanup_observed'])
            self.assertTrue(status['private_journal_may_remain'])


class ExecutionControls(unittest.TestCase):
    """Platform double exercises new orchestration, never native API behavior."""
    fixture = AdmissionControls.fixture

    def run_double(self, directory, value, timeout=False):
        events = []

        class Handle(int):
            def Close(self):
                events.append('process_close')

        class Process:
            def __init__(self, *args, **kwargs):
                events.append('suspended_launch')
                assert kwargs['creationflags'] & 4
                self.stdout, self.stderr = io.BytesIO(encode(value)), io.BytesIO()
                self._handle = Handle(42)
                self.pid, self.returncode = 7, None if timeout else (0 if value['passed'] else 1)

            def poll(self):
                return self.returncode

            def kill(self):
                events.append('direct_kill')
                self.returncode = 2

            def wait(self, timeout):
                return self.returncode

        class Platform:
            def __init__(self):
                self.k = self

            def pin(self, path):
                return 10 if path.name == 'OwnedProfileProcess.exe' else 11

            def create_parent(self, path):
                path.mkdir()
                events.append('parent')
                if not value['cleanup_complete']:
                    (path/'must-not-delete.private').write_text('private')

            def job(self):
                events.append('job')
                return 20

            def assign(self, job, process):
                events.append('assign')

            def empty(self, job):
                return True

            def close(self, handle):
                events.append('close_'+str(handle))

            def TerminateJobObject(self, handle, code):
                return True

        def resume(process):
            events.append('resume')
            return {'passed': True, 'resume_observed': True}

        parent = directory/'private-parent'
        with mock.patch.object(m, 'Native', Platform), mock.patch.object(m.subprocess, 'Popen', Process), mock.patch.dict('sys.modules', {'windows_suspended_thread': SimpleNamespace(resume_primary=resume)}):
            if timeout:
                with mock.patch.object(m.time, 'monotonic', side_effect=[0, 181, 182]):
                    status, native = m.execute(directory, parent)
            else:
                status, native = m.execute(directory, parent)
        self.assertLess(events.index('assign'), events.index('resume'))
        self.assertIn('process_close', events)
        for handle in (10, 11, 20):
            self.assertIn('close_'+str(handle), events)
        return status, native, parent

    def test_new_orchestration_success_requires_outer_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.fixture(directory)
            status, native, parent = self.run_double(directory, receipt())
            self.assertTrue(status['passed'])
            self.assertTrue(native['passed'])
            self.assertFalse(parent.exists())
            self.assertFalse(status['service_readiness_qualified'])

    def test_inner_failure_preserves_journal_and_never_claims_rollback(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.fixture(directory)
            value = {**receipt(False), 'cleanup_complete': False,
                     'private_journal_retained': True, 'first_cleanup_failure': 'CLEANUP'}
            status, native, parent = self.run_double(directory, value)
            self.assertFalse(status['passed'])
            self.assertFalse(native['cleanup_complete'])
            self.assertEqual(status['first_failure'], 'HELPER_RESULT')
            self.assertTrue((parent/'must-not-delete.private').exists())
            self.assertTrue(status['private_journal_may_remain'])

    def test_outer_timeout_retains_unobserved_inner_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.fixture(directory)
            status, native, parent = self.run_double(directory, receipt(), timeout=True)
            self.assertFalse(status['passed'])
            self.assertIsNone(native)
            self.assertTrue(status['timeout'])
            self.assertEqual(status['first_failure'], 'HELPER_WAIT')
            self.assertFalse(status['inner_cleanup_observed'])
            self.assertTrue(parent.exists())


if __name__ == '__main__':
    unittest.main()
