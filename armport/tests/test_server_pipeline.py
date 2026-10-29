#!/usr/bin/env python3
"""Pipeline identity/claim regressions; metadata fixtures never execute a server.

The package reader's byte, source and PE checks live in test_server_package.
These tests run the real admission/qualification functions and host failure
summary, including deliberately replayed receipts from another guest session.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'armport/app'))
import interactive_host
import server_pipeline as pipeline


class ServerPipelineTests(unittest.TestCase):
    COMMIT = 'a' * 40
    BUILD_RUN = 123
    RUNTIME_RUN = 456
    CREATION = '1' * 32
    REOPEN = '2' * 32

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.build_run = {'id': self.BUILD_RUN,
            'path': '.github/workflows/armport-build.yml', 'event': 'workflow_dispatch',
            'status': 'completed', 'conclusion': 'success', 'head_sha': self.COMMIT,
            'repository': {'full_name': pipeline.REPOSITORY},
            'head_repository': {'full_name': pipeline.REPOSITORY}}
        self.packages, self.builds, self.members = {}, {}, {}
        for variant, filename in pipeline.PACKAGES.items():
            raw = ('synthetic archive metadata fixture: ' + variant).encode()
            (self.work / filename).write_bytes(raw)
            build = {'variant': variant, 'repository_commit': self.COMMIT,
                'run_id': self.BUILD_RUN, 'files': {'MapServer.exe':
                    pipeline.native.pin(('synthetic PE identity ' + variant).encode())},
                'predecessor': {'mapserver': pipeline.native.pin(('ancestor ' + variant).encode())},
                'build_input': {'fixture_only': True, 'variant': variant}}
            members = {pipeline.native.BUILD: pipeline.native.canonical(build)}
            self.builds[variant], self.members[variant] = build, members
            self.packages[variant] = {'filename': filename, **pipeline.native.pin(raw),
                'mapserver': copy.deepcopy(build['files']['MapServer.exe']),
                'build_manifest_sha256': pipeline.native.digest(members[pipeline.native.BUILD]),
                'source_receipt_sha256': pipeline.native.digest(pipeline.native.canonical(build['build_input'])),
                'package_receipt_sha256': pipeline.native.digest(pipeline.native.canonical(build)),
                'previous_mapserver_sha256': build['predecessor']['mapserver']['sha256']}
        retained = self.packages['retained_progress']
        self.expected = {'format': 1, 'variant': 'retained_progress',
            'repository_commit': self.COMMIT, 'run_id': self.BUILD_RUN,
            'server_package': {key: retained[key] for key in ('bytes', 'sha256')},
            'mapserver': copy.deepcopy(retained['mapserver']),
            'build_manifest': pipeline.native.pin(self.members['retained_progress'][pipeline.native.BUILD]),
            'source_receipt_sha256': retained['source_receipt_sha256'],
            'runtime_execution_validated': False, 'physical_device_validated': False}
        self.proof = {**copy.deepcopy(self.expected),
            'policy': 'authenticated_metrics_only_overlay',
            'actual_mapserver_sha256': retained['mapserver']['sha256'],
            'previous_mapserver_sha256': retained['previous_mapserver_sha256'],
            'package_receipt_sha256': retained['package_receipt_sha256'],
            'parser_or_definition_sources_changed': False, 'gameplay_decisions_changed': False}
        self.manifest = {'armport_server_metrics': self.expected,
                         'armport_server_metrics_build': self.builds['retained_progress']}
        self.host = {'scope': 'arm64_app_guest_creation_and_reopen',
            'repository_commit': self.COMMIT, 'passed': True, 'same_persistent_profile': True,
            'same_character_id': True, 'error': None, 'android_surface_validated': False,
            'm4_complete': False, 'armport_client': {'client_run_id': self.BUILD_RUN,
                                                   'data_run_id': self.BUILD_RUN},
            'creation_session_id': self.CREATION, 'reopen_session_id': self.REOPEN,
            'server_metrics_native_execution': {phase: pipeline.guest_admission(
                self.guest(phase), self.manifest) for phase in ('creation', 'reopen')},
            'guest_failures': {phase: self.failure_summary(phase) for phase in ('creation', 'reopen')}}

    def guest(self, phase='creation'):
        session = self.CREATION if phase == 'creation' else self.REOPEN
        return {'scope': 'actual_character_' + phase + '_guest', 'session_id': session,
            'character_' + phase: {'session_id': session, 'mapserver_producer': {
                'mapserver_sha256': self.expected['mapserver']['sha256'],
                'repository_commit': self.COMMIT, 'run_id': self.BUILD_RUN,
                'manifest_sha256': self.expected['build_manifest']['sha256'],
                'armport_server_metrics': copy.deepcopy(self.proof)}}}

    def failure_summary(self, phase, *, failures=None, stages=None, console='normal exit 0\n'):
        directory = self.work / phase
        directory.mkdir(exist_ok=True)
        (directory / 'latest-report.json').write_text(json.dumps({
            'failures': failures or [], 'stages': stages or []}))
        with zipfile.ZipFile(directory / 'report.zip', 'w') as archive:
            archive.writestr('client-evidence/client-console.log', console)
        return interactive_host.guest_failure_summary(directory)

    def qualify(self, host=None, **kwargs):
        arguments = dict(repository_commit=self.COMMIT, run_id=self.BUILD_RUN,
                         runtime_run_id=self.RUNTIME_RUN)
        arguments.update(kwargs)
        return pipeline.qualification(self.host if host is None else host, self.packages, **arguments)

    def validate(self, value, **kwargs):
        arguments = dict(repository_commit=self.COMMIT, runtime_run_id=self.RUNTIME_RUN)
        arguments.update(kwargs)
        return pipeline.validate_qualification(value, self.packages, **arguments)

    def test_same_explicit_build_required_for_client_data_and_servers(self):
        arguments = dict(repository_commit=self.COMMIT, server_run_id=self.BUILD_RUN,
                         client_run_id=self.BUILD_RUN, data_run_id=self.BUILD_RUN)
        pipeline.check_build_run(self.build_run, **arguments)
        for key in ('server_run_id', 'client_run_id', 'data_run_id'):
            for value in (self.BUILD_RUN + 1, str(self.BUILD_RUN), True, 0, -1):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    pipeline.check_build_run(self.build_run, **dict(arguments, **{key: value}))

    def test_build_run_requires_same_head_repository_workflow_and_success(self):
        changes = {'id': self.BUILD_RUN + 1, 'head_sha': 'b' * 40,
            'path': '.github/workflows/armport-app-runtime.yml', 'event': 'push',
            'status': 'in_progress', 'conclusion': 'failure',
            'repository': {'full_name': 'other/coh-android'},
            'head_repository': {'full_name': 'other/coh-android'}}
        for key, value in changes.items():
            with self.subTest(key=key), self.assertRaises(ValueError):
                pipeline.check_build_run(dict(self.build_run, **{key: value}),
                    repository_commit=self.COMMIT, server_run_id=self.BUILD_RUN,
                    client_run_id=self.BUILD_RUN, data_run_id=self.BUILD_RUN)

    def test_guest_receipt_binds_actual_report_and_character_session(self):
        for phase, session in (('creation', self.CREATION), ('reopen', self.REOPEN)):
            report = self.guest(phase)
            receipt = pipeline.guest_admission(report, self.manifest)
            self.assertEqual(receipt, {'session_id': session, 'producer': self.proof})
            report['character_' + phase]['mapserver_producer']['armport_server_metrics']['run_id'] = -1
            self.assertEqual(receipt['producer']['run_id'], self.BUILD_RUN)
        self.assertIsNone(pipeline.guest_admission({}, {}))

    def test_guest_rejects_missing_stale_or_wrong_scope_session_identity(self):
        changes = [lambda r: r.pop('session_id'),
            lambda r: r.update(session_id='not-a-session'),
            lambda r: r['character_creation'].update(session_id=self.REOPEN),
            lambda r: r.update(scope='actual_character_startup_timing_guest'),
            lambda r: r.update(scope='actual_character_reopen_guest')]
        for index, change in enumerate(changes):
            with self.subTest(index=index), self.assertRaises(ValueError):
                report = self.guest(); change(report)
                pipeline.guest_admission(report, self.manifest)

    def test_guest_rejects_wrong_actual_binary_run_manifest_or_overlay_ancestry(self):
        for key, value in {'mapserver_sha256': 'f' * 64, 'repository_commit': 'b' * 40,
                           'run_id': str(self.BUILD_RUN), 'manifest_sha256': 'f' * 64}.items():
            with self.subTest(producer=key), self.assertRaises(ValueError):
                report = self.guest(); report['character_creation']['mapserver_producer'][key] = value
                pipeline.guest_admission(report, self.manifest)
        for key, value in {'actual_mapserver_sha256': 'f' * 64,
                'previous_mapserver_sha256': 'f' * 64, 'package_receipt_sha256': 'f' * 64,
                'policy': 'unverified_overlay', 'parser_or_definition_sources_changed': True,
                'gameplay_decisions_changed': True, 'variant': 'thor_certified_startup'}.items():
            with self.subTest(proof=key), self.assertRaises(ValueError):
                report = self.guest()
                report['character_creation']['mapserver_producer']['armport_server_metrics'][key] = value
                pipeline.guest_admission(report, self.manifest)

    def test_qualified_retained_execution_preserves_both_ids_and_thor_limit(self):
        value = self.qualify()
        self.assertIs(self.validate(value), value)
        self.assertEqual(value['creation_session_id'], self.CREATION)
        self.assertEqual(value['reopen_session_id'], self.REOPEN)
        self.assertTrue(value['retained_runtime_executed'])
        self.assertFalse(value['thor_runtime_executed'])
        self.assertFalse(value['physical_device_validated'])
        self.assertEqual(set(value['packages']), {'retained_progress', 'thor_certified_startup'})
        self.host['server_metrics_native_execution']['creation']['producer']['run_id'] = -1
        self.assertEqual(value['retained_sessions']['creation']['producer']['run_id'], self.BUILD_RUN)

    def test_copied_swapped_or_stale_guest_receipts_cannot_qualify(self):
        for case in ('copied', 'swapped', 'stale', 'missing', 'bare_proof'):
            with self.subTest(case=case), self.assertRaises(ValueError):
                host = copy.deepcopy(self.host)
                sessions = host['server_metrics_native_execution']
                if case == 'copied': sessions['reopen'] = copy.deepcopy(sessions['creation'])
                elif case == 'swapped': sessions['creation'], sessions['reopen'] = sessions['reopen'], sessions['creation']
                elif case == 'stale': sessions['creation']['session_id'] = '3' * 32
                elif case == 'missing': sessions.pop('reopen')
                else: sessions['creation'] = sessions['creation']['producer']
                self.qualify(host)

    def test_host_ids_must_be_present_distinct_and_match_guest_receipts(self):
        for key in ('creation_session_id', 'reopen_session_id'):
            for bad in (None, '', '0' * 31, 'g' * 32, '3' * 32):
                with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                    self.qualify(dict(self.host, **{key: bad}))
        with self.assertRaises(ValueError):
            host = copy.deepcopy(self.host)
            host['reopen_session_id'] = self.CREATION
            host['server_metrics_native_execution']['reopen']['session_id'] = self.CREATION
            self.qualify(host)

    def test_failed_or_cross_build_host_cannot_qualify(self):
        for key, value in {'passed': False, 'same_persistent_profile': False, 'same_character_id': False,
                'repository_commit': 'b' * 40, 'error': {'message': 'failed'},
                'scope': 'server_startup_only', 'android_surface_validated': True,
                'm4_complete': True}.items():
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.qualify(dict(self.host, **{key: value}))
        for key in ('client_run_id', 'data_run_id'):
            for bad in (self.BUILD_RUN + 1, str(self.BUILD_RUN), True):
                with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                    host = copy.deepcopy(self.host); host['armport_client'][key] = bad
                    self.qualify(host)
        for bad in (self.BUILD_RUN, str(self.RUNTIME_RUN), True, 0):
            with self.subTest(runtime_run=bad), self.assertRaises(ValueError):
                self.qualify(runtime_run_id=bad)

    def test_actual_exported_failures_faults_and_read_errors_reject_qualification(self):
        for arguments in ({'failures': ['save failed']},
                {'stages': [{'stage': 'cleanup', 'status': 'failed'}]},
                {'console': 'Unhandled page fault on read access\n'}):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                host = copy.deepcopy(self.host)
                host['guest_failures']['reopen'] = self.failure_summary('reopen', **arguments)
                self.qualify(host)
        for summary in ({}, {'failures': [], 'failed_stages': [], 'client_faults': [],
                             'evidence_read_error': 'missing console'}):
            with self.subTest(summary=summary), self.assertRaises(ValueError):
                host = copy.deepcopy(self.host); host['guest_failures']['reopen'] = summary
                self.qualify(host)

    def test_qualification_rejects_changed_package_or_session_source_receipt(self):
        qualified = self.qualify()
        for variant in pipeline.PACKAGES:
            for field in ('sha256', 'build_manifest_sha256', 'source_receipt_sha256', 'package_receipt_sha256'):
                with self.subTest(variant=variant, field=field), self.assertRaises(ValueError):
                    changed = copy.deepcopy(qualified); changed['packages'][variant][field] = 'f' * 64
                    self.validate(changed)
        for field in ('source_receipt_sha256', 'package_receipt_sha256', 'previous_mapserver_sha256'):
            with self.subTest(session_field=field), self.assertRaises(ValueError):
                changed = copy.deepcopy(qualified)
                changed['retained_sessions']['reopen']['producer'][field] = 'f' * 64
                self.validate(changed)

    def test_qualification_rejects_claim_escalation_other_heads_or_runtime_runs(self):
        qualified = self.qualify()
        for field in ('thor_runtime_executed', 'physical_device_validated'):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.validate(dict(qualified, **{field: True}))
        for field in ('runtime_passed', 'retained_runtime_executed'):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.validate(dict(qualified, **{field: False}))
        for arguments in ({'runtime_run_id': self.RUNTIME_RUN + 1}, {'repository_commit': 'b' * 40}):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                self.validate(qualified, **arguments)
        for field in ('runtime_execution_validated', 'physical_device_validated'):
            with self.subTest(producer=field), self.assertRaises(ValueError):
                changed = copy.deepcopy(qualified)
                changed['retained_sessions']['creation']['producer'][field] = True
                self.validate(changed)
        with self.assertRaises(ValueError):
            changed = copy.deepcopy(qualified)
            changed['retained_sessions']['reopen']['producer']['variant'] = 'thor_certified_startup'
            self.validate(changed)

    def test_native_reader_receives_pinned_baseline_for_each_actual_archive(self):
        baseline = self.work / 'immutable-baseline'
        def read(path, *, variant, repository_commit, run_id, upstream_root):
            self.assertEqual(Path(path), self.work / pipeline.PACKAGES[variant])
            self.assertEqual((repository_commit, run_id, upstream_root),
                             (self.COMMIT, self.BUILD_RUN, baseline))
            return self.builds[variant], {}, self.members[variant]
        with mock.patch.object(pipeline.native, 'read_package', side_effect=read) as reader:
            self.assertEqual(pipeline.native_inputs(self.work, self.COMMIT, self.BUILD_RUN, baseline),
                             self.packages)
        self.assertEqual(reader.call_count, 2)

    def test_reloading_qualification_revalidates_packages_and_preserves_baseline(self):
        qualified = self.qualify(); baseline = self.work / 'immutable-baseline'
        (self.work / pipeline.QUALIFICATION).write_bytes(pipeline.native.canonical(qualified))
        with mock.patch.object(pipeline, 'native_inputs', return_value=self.packages) as reader:
            self.assertEqual(pipeline.read_qualification(self.work, self.COMMIT, self.RUNTIME_RUN,
                                                        baseline), qualified)
        reader.assert_called_once_with(self.work, self.COMMIT, self.BUILD_RUN, baseline)
        with mock.patch.object(pipeline, 'native_inputs', side_effect=ValueError('bad actual package')):
            with self.assertRaisesRegex(ValueError, 'bad actual package'):
                pipeline.read_qualification(self.work, self.COMMIT, self.RUNTIME_RUN, baseline)


if __name__ == '__main__':
    unittest.main()
