"""Mock rollback ordering/attribution; no API calls, signing or real sleeps."""
import copy
import json
from types import SimpleNamespace
import unittest
from unittest import mock
import rollback_ci as ci

RUNTIME, PRIMARY, ROLLBACK, CURRENT = 77, 88, 99, 1000
SUPPORT_SHA = 'f' * 40


def run(identifier, path, *, event='workflow_dispatch', branch=ci.SOURCE_BRANCH, sha=ci.SOURCE):
    return {'id': identifier, 'path': path, 'event': event, 'head_branch': branch, 'head_sha': sha,
        'status': 'completed', 'conclusion': 'success', 'repository': {'full_name': ci.REPOSITORY},
        'head_repository': {'full_name': ci.REPOSITORY}}


class Fake:
    def __init__(self):
        self.now, self.calls, self.posts, self.parent_reads = 0.0, [], 0, 0
        self.parent_pending, self.parent_failed, self.moved, self.runtime_duplicate = 0, False, False, False
        self.primary_count, self.primary_metrics = 1, True
        self.no_observation, self.extra_after_post, self.post_uncertain = False, False, False
        self.rollback_failed, self.rollback_metrics, self.artifact_issue = False, False, None
        self.prior_coordinator = False

    def clock(self): return self.now
    def sleep(self, seconds): self.now += seconds

    def api(self, endpoint, payload=None):
        self.calls.append((endpoint, copy.deepcopy(payload)))
        if payload is not None:
            assert endpoint == '/actions/workflows/armport-thor-apk.yml/dispatches'
            assert payload == {'ref': ci.SOURCE_BRANCH, 'inputs': {'m4_run_id': '77', 'server_metrics': False}}
            self.posts += 1
            if self.post_uncertain: raise ci.upstream.UpstreamError('POST result uncertain; do not blindly redispatch')
            return None
        if endpoint.startswith('/git/ref/'):
            return {'object': {'sha': 'b' * 40 if self.moved else ci.SOURCE}}
        if endpoint.startswith('/actions/workflows/'):
            workflow = endpoint.split('/')[3]
            if workflow == ci.OWN_WORKFLOW:
                rows = [run(CURRENT, ci.OWN_PATH, event='push', branch=ci.SUPPORT_BRANCH, sha=SUPPORT_SHA)]
                if self.prior_coordinator: rows.append(run(CURRENT - 1, ci.OWN_PATH, event='push', branch=ci.SUPPORT_BRANCH, sha='e' * 40))
            elif workflow == 'armport-app-runtime.yml':
                rows = [run(RUNTIME, ci.upstream.RUNTIME_WORKFLOW)]
                if self.runtime_duplicate: rows.append(run(RUNTIME + 1, ci.upstream.RUNTIME_WORKFLOW))
            elif workflow == ci.APK_WORKFLOW:
                rows = [run(PRIMARY + index, ci.APK_PATH) for index in range(self.primary_count)]
                if self.posts and not self.no_observation:
                    rows.append(run(ROLLBACK, ci.APK_PATH))
                    if self.extra_after_post: rows.append(run(ROLLBACK + 1, ci.APK_PATH))
            else:
                raise AssertionError(endpoint)
            return {'total_count': len(rows), 'workflow_runs': rows}
        identifier = int(endpoint.split('/')[3])
        if '/jobs?' in endpoint:
            enabled = self.primary_metrics if identifier == PRIMARY else self.rollback_metrics
            return {'total_count': 1, 'jobs': [{'steps': [
                {'name': ci.METRICS_STEP, 'conclusion': 'success' if enabled else 'skipped'},
                {'name': ci.SIGN_STEP, 'conclusion': 'success'}]}]}
        if '/artifacts?' in endpoint:
            rows = [{'id': 300 + identifier, 'name': ci.ARTIFACT, 'expired': False, 'size_in_bytes': 100,
                     'digest': 'sha256:' + 'a' * 64, 'archive_download_url': 'https://api.github.com/artifact'}]
            if identifier == ROLLBACK:
                if self.artifact_issue == 'missing': rows = []
                if self.artifact_issue == 'expired': rows[0]['expired'] = True
                if self.artifact_issue == 'duplicate': rows += copy.deepcopy(rows)
            return {'total_count': len(rows), 'artifacts': rows}
        if identifier == ci.PARENT:
            self.parent_reads += 1
            row = run(ci.PARENT, ci.PARENT_PATH, event='push')
            if self.parent_reads <= self.parent_pending: row.update(status='in_progress', conclusion=None)
            if self.parent_failed: row['conclusion'] = 'failure'
            return row
        if identifier == RUNTIME: return run(RUNTIME, ci.upstream.RUNTIME_WORKFLOW)
        if identifier == PRIMARY: return run(PRIMARY, ci.APK_PATH)
        if identifier == ROLLBACK:
            row = run(ROLLBACK, ci.APK_PATH)
            if self.rollback_failed: row['conclusion'] = 'failure'
            return row
        raise AssertionError(endpoint)

    def coordinator(self, timeout=300, attempt=1):
        return ci.Rollback(current_run_id=CURRENT, supporting_sha=SUPPORT_SHA, attempt=attempt,
            api=self.api, clock=self.clock, sleep=self.sleep, timeout_seconds=timeout, poll_seconds=10)


class RollbackTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(mock.patch.stopall)
        mock.patch('builtins.print').start()

    def test_parent_finishes_before_one_false_metrics_dispatch_and_exact_artifact(self):
        fake = Fake(); fake.parent_pending = 1
        result = fake.coordinator().execute()
        self.assertEqual(fake.posts, 1)
        post = next(i for i, call in enumerate(fake.calls) if call[1] is not None)
        parent_reads = [i for i, call in enumerate(fake.calls) if call[0] == '/actions/runs/' + str(ci.PARENT)]
        self.assertGreaterEqual(len(parent_reads), 3)
        self.assertTrue(all(i < post for i in parent_reads))
        self.assertEqual((result['primary_apk_run_id'], result['rollback_apk_run_id'], result['runtime_run_id']), (PRIMARY, ROLLBACK, RUNTIME))
        self.assertFalse(result['server_metrics'])
        self.assertFalse(result['apk_payload_independently_verified'])
        self.assertEqual(result['expected_mapserver_sha256'], ci.ROLLBACK_MAP)

    def test_parent_failure_never_dispatches(self):
        fake = Fake(); fake.parent_failed = True
        with self.assertRaisesRegex(ci.upstream.UpstreamError, 'Required run failed'): fake.coordinator().execute()
        self.assertEqual(fake.posts, 0)

    def test_moved_source_never_dispatches(self):
        fake = Fake(); fake.moved = True
        with self.assertRaisesRegex(ci.upstream.UpstreamError, 'branch moved'): fake.coordinator().execute()
        self.assertEqual(fake.posts, 0)

    def test_duplicate_runtime_never_dispatches(self):
        fake = Fake(); fake.runtime_duplicate = True
        with self.assertRaisesRegex(ci.upstream.UpstreamError, 'Multiple matching'): fake.coordinator().execute()
        self.assertEqual(fake.posts, 0)

    def test_zero_or_multiple_existing_primary_runs_refuse_blind_retry(self):
        for count in (0, 2):
            fake = Fake(); fake.primary_count = count
            with self.subTest(count=count), self.assertRaisesRegex(ci.upstream.UpstreamError, 'Exactly one successful primary'): fake.coordinator().execute()
            self.assertEqual(fake.posts, 0)

    def test_existing_metrics_false_apk_is_not_mistaken_for_primary(self):
        fake = Fake(); fake.primary_metrics = False
        with self.assertRaisesRegex(ci.upstream.UpstreamError, 'metrics input path'): fake.coordinator().execute()
        self.assertEqual(fake.posts, 0)

    def test_attempt_two_or_another_prior_coordinator_refuses_new_post(self):
        fake = Fake()
        with self.assertRaisesRegex(ci.upstream.UpstreamError, 'reruns are refused'): fake.coordinator(attempt=2)
        self.assertEqual(fake.calls, [])
        fake.prior_coordinator = True
        with self.assertRaisesRegex(ci.upstream.UpstreamError, 'Another rollback coordinator'): fake.coordinator().execute()
        self.assertEqual(fake.posts, 0)

    def test_uncertain_post_is_never_retried(self):
        fake = Fake(); fake.post_uncertain = True
        with self.assertRaisesRegex(ci.upstream.UpstreamError, 'uncertain'): fake.coordinator().execute()
        self.assertEqual(fake.posts, 1)

    def test_unobservable_or_ambiguous_new_run_never_redispatches(self):
        for option in ('no_observation', 'extra_after_post'):
            fake = Fake(); setattr(fake, option, True)
            with self.subTest(option=option), self.assertRaises(ci.upstream.UpstreamError): fake.coordinator().execute()
            self.assertEqual(fake.posts, 1)

    def test_wrong_metrics_rollback_or_failed_run_is_not_accepted(self):
        for option in ('rollback_metrics', 'rollback_failed'):
            fake = Fake(); setattr(fake, option, True)
            with self.subTest(option=option), self.assertRaises(ci.upstream.UpstreamError): fake.coordinator().execute()
            self.assertEqual(fake.posts, 1)

    def test_missing_expired_duplicate_artifact_is_not_accepted(self):
        for option in ('missing', 'expired', 'duplicate'):
            fake = Fake(); fake.artifact_issue = option
            with self.subTest(option=option), self.assertRaisesRegex(ci.upstream.UpstreamError, 'artifact missing'): fake.coordinator().execute()
            self.assertEqual(fake.posts, 1)

    def test_direct_get_rechecks_parent_runtime_and_primary_source_before_post(self):
        for identifier in (ci.PARENT, RUNTIME, PRIMARY):
            fake = Fake(); original = fake.api
            def changed(endpoint, payload=None):
                result = original(endpoint, payload)
                if payload is None and endpoint == '/actions/runs/' + str(identifier):
                    result['head_sha'] = 'b' * 40
                return result
            coordinator = ci.Rollback(current_run_id=CURRENT, supporting_sha=SUPPORT_SHA,
                api=changed, clock=fake.clock, sleep=fake.sleep, timeout_seconds=300, poll_seconds=10)
            with self.subTest(identifier=identifier), self.assertRaises(ci.upstream.UpstreamError): coordinator.execute()
            self.assertEqual(fake.posts, 0)

    def test_parent_wait_stays_bounded_without_dispatch(self):
        fake = Fake(); fake.parent_pending = 100
        with self.assertRaisesRegex(ci.upstream.UpstreamError, 'exceeded bound'):
            fake.coordinator(timeout=15).execute()
        self.assertEqual(fake.now, 15)
        self.assertEqual(fake.posts, 0)

    def test_main_refuses_legacy_missing_or_foreign_workflow_ref_before_api(self):
        environment = {'GITHUB_REPOSITORY': ci.REPOSITORY, 'GITHUB_REF_NAME': ci.SUPPORT_BRANCH,
            'GH_TOKEN': 'ordinary-ephemeral-fixture', 'GITHUB_RUN_ID': str(CURRENT),
            'GITHUB_SHA': SUPPORT_SHA, 'GITHUB_RUN_ATTEMPT': '1'}
        wrong = (None, ci.REPOSITORY + '/.github/workflows/mapserver-rollback-ci.yml@refs/heads/' + ci.SUPPORT_BRANCH,
            ci.OWN_WORKFLOW_REF.replace('@refs/heads/' + ci.SUPPORT_BRANCH, '@refs/heads/main'))
        for workflow_ref in wrong:
            selected = dict(environment)
            if workflow_ref is not None: selected['GITHUB_WORKFLOW_REF'] = workflow_ref
            with self.subTest(workflow_ref=workflow_ref), mock.patch.dict(ci.os.environ, selected, clear=True), \
                    mock.patch.object(ci, 'Rollback') as coordinator:
                with self.assertRaisesRegex(ci.upstream.UpstreamError, 'exact corrected workflow'):
                    ci.main()
                coordinator.assert_not_called()

    def test_main_exact_corrected_workflow_ref_reaches_existing_coordinator(self):
        environment = {'GITHUB_REPOSITORY': ci.REPOSITORY, 'GITHUB_REF_NAME': ci.SUPPORT_BRANCH,
            'GITHUB_WORKFLOW_REF': ci.OWN_WORKFLOW_REF, 'GH_TOKEN': 'ordinary-ephemeral-fixture',
            'GITHUB_RUN_ID': str(CURRENT), 'GITHUB_SHA': SUPPORT_SHA, 'GITHUB_RUN_ATTEMPT': '1'}
        self.assertEqual(ci.OWN_WORKFLOW, ci.Path(ci.OWN_PATH).name)
        self.assertEqual(ci.OWN_WORKFLOW, 'mapserver-rollback-corrected-ci.yml')
        with mock.patch.dict(ci.os.environ, environment, clear=True), mock.patch.object(ci, 'Rollback') as coordinator:
            coordinator.return_value.execute.return_value = {'fixture_only': True}
            ci.main()
        coordinator.assert_called_once_with(current_run_id=CURRENT, supporting_sha=SUPPORT_SHA, attempt=1)
        coordinator.return_value.execute.assert_called_once_with()

    def test_api_allows_only_exact_false_metrics_post(self):
        api = ci.ActionsApi()
        endpoint = '/actions/workflows/armport-thor-apk.yml/dispatches'
        payload = {'ref': ci.SOURCE_BRANCH, 'inputs': {'m4_run_id': '77', 'server_metrics': False}}
        with mock.patch.object(ci.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='', stderr='')) as command:
            api(endpoint, payload)
        self.assertEqual(command.call_args.args[0][2:4], ['--method', 'POST'])
        self.assertEqual(json.loads(command.call_args.kwargs['input']), payload)
        for bad_endpoint, bad in [(endpoint, {**payload, 'inputs': {'m4_run_id': '77', 'server_metrics': True}}),
                                   ('/actions/workflows/armport-build.yml/dispatches', payload),
                                   (endpoint, {**payload, 'ref': 'main'})]:
            with self.assertRaises(ci.upstream.UpstreamError): api(bad_endpoint, bad)


if __name__ == '__main__': unittest.main()
