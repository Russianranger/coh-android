"""Mocked GET-only handoff controls; no live API, dispatch or real sleeps."""
import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit
import modern_wait_upstream as wait

SHA, BUILD, RUNTIME = 'a' * 40, 123, 456


def run(identifier, workflow, status='completed', conclusion='success'):
    return dict(id=identifier, path=workflow, event='workflow_dispatch', head_sha=SHA,
        head_branch=wait.BRANCH, repository={'full_name': wait.REPOSITORY}, head_repository={'full_name': wait.REPOSITORY},
        status=status, conclusion=conclusion)


class Scenario:
    def __init__(self, snapshots):
        self.snapshots, self.index, self.now, self.calls, self.sleeps = snapshots, 0, 100.0, [], []

    def api(self, path):
        self.calls.append(path)
        current = self.snapshots[min(self.index, len(self.snapshots) - 1)]
        if path == '/actions/runs/' + str(BUILD):
            value = current['native']
        elif path.startswith('/actions/workflows/'):
            page = int(parse_qs(urlsplit(path).query)['page'][0])
            pages = current.get('pages', [current.get('runtime_rows', [])])
            value = {'total_count': sum(len(rows) for rows in pages), 'workflow_runs': pages[page - 1]}
        elif path.startswith('/actions/runs/'):
            identifier = int(path.rsplit('/', 1)[1])
            value = current.get('runtime_get', {}).get(identifier)
            if value is None:
                value = next(row for rows in current.get('pages', [current.get('runtime_rows', [])])
                             for row in rows if row['id'] == identifier)
        else:
            raise AssertionError('Unexpected API path: ' + path)
        return copy.deepcopy(value)

    def clock(self): return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds); self.now += seconds; self.index += 1

    def execute(self, timeout_seconds=100):
        return wait.wait_for_upstreams(self.api, native_run_id=BUILD, commit=SHA,
            timeout_seconds=timeout_seconds, poll_seconds=10,
            clock=self.clock, sleeper=self.sleep, log=lambda _line: None)


class WaitTests(unittest.TestCase):
    def test_immediate_exact_success_emits_only_verified_runtime_id(self):
        fixture = Scenario([{'native': run(BUILD, wait.NATIVE_WORKFLOW),
                             'runtime_rows': [run(RUNTIME, wait.RUNTIME_WORKFLOW)]}])
        result = fixture.execute()
        self.assertEqual(result['runtime_run_id'], RUNTIME)
        self.assertTrue(result['both_completed_successfully'])
        self.assertEqual(fixture.sleeps, [])
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'github-output'
            wait.emit_output(output, result)
            self.assertEqual(output.read_text(), 'runtime_run_id=456\n')
            for bad in [dict(result, both_completed_successfully=False), dict(result, runtime_run_id='456\nother=1')]:
                with self.assertRaises(wait.UpstreamError): wait.emit_output(output, bad)
            self.assertEqual(output.read_text(), 'runtime_run_id=456\n')

    def test_waits_for_native_discovery_and_actual_runtime_success(self):
        fixture = Scenario([
            {'native': run(BUILD, wait.NATIVE_WORKFLOW, 'in_progress', None), 'runtime_rows': []},
            {'native': run(BUILD, wait.NATIVE_WORKFLOW), 'runtime_rows': [run(RUNTIME, wait.RUNTIME_WORKFLOW, 'queued', None)]},
            {'native': run(BUILD, wait.NATIVE_WORKFLOW), 'runtime_rows': [run(RUNTIME, wait.RUNTIME_WORKFLOW)]}])
        result = fixture.execute()
        self.assertEqual((result['runtime_run_id'], result['polls'], result['elapsed_seconds']), (RUNTIME, 3, 20))
        self.assertEqual(fixture.sleeps, [10, 10])

    def test_native_failure_stops_before_runtime_discovery(self):
        fixture = Scenario([{'native': run(BUILD, wait.NATIVE_WORKFLOW, 'completed', 'failure'), 'runtime_rows': []}])
        with self.assertRaisesRegex(wait.UpstreamError, 'completed with failure'): fixture.execute()
        self.assertEqual(fixture.calls, ['/actions/runs/123'])
        self.assertEqual(fixture.sleeps, [])

    def test_runtime_failure_stops_even_while_native_pending(self):
        fixture = Scenario([{'native': run(BUILD, wait.NATIVE_WORKFLOW, 'in_progress', None),
            'runtime_rows': [run(RUNTIME, wait.RUNTIME_WORKFLOW, 'completed', 'cancelled')]}])
        with self.assertRaisesRegex(wait.UpstreamError, 'completed with cancelled'): fixture.execute()
        self.assertEqual(fixture.sleeps, [])

    def test_duplicate_candidate_on_later_page_cannot_select_first_or_newest(self):
        fixture = Scenario([{'native': run(BUILD, wait.NATIVE_WORKFLOW), 'pages': [
            [run(RUNTIME, wait.RUNTIME_WORKFLOW)], [run(RUNTIME + 1, wait.RUNTIME_WORKFLOW)]]}])
        with self.assertRaisesRegex(wait.UpstreamError, 'Multiple matching'): fixture.execute()
        self.assertTrue(any('page=2' in path for path in fixture.calls))
        self.assertEqual(fixture.sleeps, [])

    def test_historical_sha_ignored_and_selected_get_rechecks_source(self):
        old = run(1, wait.RUNTIME_WORKFLOW); old['head_sha'] = 'b' * 40
        fixture = Scenario([{'native': run(BUILD, wait.NATIVE_WORKFLOW),
                             'runtime_rows': [old, run(RUNTIME, wait.RUNTIME_WORKFLOW)]}])
        self.assertEqual(fixture.execute()['runtime_run_id'], RUNTIME)
        for key, value in [('head_sha', 'b' * 40), ('head_branch', 'other'), ('event', 'push'),
                           ('path', wait.NATIVE_WORKFLOW), ('head_repository', {'full_name': 'other/repo'}), ('id', 1)]:
            changed = run(RUNTIME, wait.RUNTIME_WORKFLOW); changed[key] = value
            fixture = Scenario([{'native': run(BUILD, wait.NATIVE_WORKFLOW),
                'runtime_rows': [run(RUNTIME, wait.RUNTIME_WORKFLOW)], 'runtime_get': {RUNTIME: changed}}])
            with self.subTest(key=key), self.assertRaisesRegex(wait.UpstreamError, 'mismatch'): fixture.execute()

    def test_native_source_or_unknown_status_fails_closed(self):
        for key, value in [('head_sha', 'b' * 40), ('head_branch', 'other'), ('event', 'push'),
                           ('repository', None), ('status', 'unrecognized'), ('id', True)]:
            changed = run(BUILD, wait.NATIVE_WORKFLOW); changed[key] = value
            fixture = Scenario([{'native': changed, 'runtime_rows': []}])
            with self.subTest(key=key), self.assertRaises(wait.UpstreamError): fixture.execute()

    def test_discovered_runtime_cannot_disappear_or_be_replaced(self):
        first = {'native': run(BUILD, wait.NATIVE_WORKFLOW, 'in_progress', None),
                 'runtime_rows': [run(RUNTIME, wait.RUNTIME_WORKFLOW, 'queued', None)]}
        for rows in [[], [run(RUNTIME + 1, wait.RUNTIME_WORKFLOW)]]:
            fixture = Scenario([first, {'native': run(BUILD, wait.NATIVE_WORKFLOW), 'runtime_rows': rows}])
            with self.assertRaisesRegex(wait.UpstreamError, 'disappeared or changed'): fixture.execute()
            self.assertEqual(fixture.sleeps, [10])

    def test_no_runtime_timeout_is_bounded_without_real_sleep(self):
        fixture = Scenario([{'native': run(BUILD, wait.NATIVE_WORKFLOW), 'runtime_rows': []}])
        with self.assertRaisesRegex(wait.UpstreamError, 'Timed out'): fixture.execute(timeout_seconds=15)
        self.assertEqual(fixture.sleeps, [10, 5])
        self.assertEqual(fixture.now, 115)

    def test_temporary_transport_retries_inside_original_deadline(self):
        fixture = Scenario([{'native': run(BUILD, wait.NATIVE_WORKFLOW), 'runtime_rows': [run(RUNTIME, wait.RUNTIME_WORKFLOW)]}])
        calls = [0]
        def api(path):
            calls[0] += 1
            if calls[0] == 1: raise wait.RetryableApiError('temporary')
            return fixture.api(path)
        result = wait.wait_for_upstreams(api, native_run_id=BUILD, commit=SHA, timeout_seconds=20, poll_seconds=10,
            clock=fixture.clock, sleeper=fixture.sleep, log=lambda _line: None)
        self.assertEqual(result['elapsed_seconds'], 10)
        self.assertTrue(all(path.startswith('/actions/') and not any(word in path for word in ('dispatches', 'rerun', 'cancel')) for path in fixture.calls))

    def test_changing_page_count_restarts_instead_of_claiming_uniqueness(self):
        responses = [
            {'total_count': 2, 'workflow_runs': [run(RUNTIME, wait.RUNTIME_WORKFLOW)]},
            {'total_count': 3, 'workflow_runs': [run(RUNTIME, wait.RUNTIME_WORKFLOW)]}]
        with self.assertRaisesRegex(wait.RetryableApiError, 'changed during pagination'):
            wait.discover_runtime(lambda _path: responses.pop(0), SHA, wait.BRANCH)

    def test_cli_enforces_get_and_never_places_token_in_arguments(self):
        api = wait.GitHubReadOnly(wait.REPOSITORY, 'redacted-test-token')
        with mock.patch.object(wait.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='{"id":123}', stderr='')) as command:
            self.assertEqual(api('/actions/runs/123'), {'id': 123})
        self.assertEqual(command.call_args.args[0], ['gh', 'api', '--method', 'GET', 'repos/Russianranger/coh-android/actions/runs/123'])
        self.assertNotIn('redacted-test-token', repr(command.call_args))
        for invalid in ['/issues/1', 'https://other/actions/runs/1', '/actions/../dispatches']:
            with self.assertRaises(wait.UpstreamError): api(invalid)


if __name__ == '__main__': unittest.main()
