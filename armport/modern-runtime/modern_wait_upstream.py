#!/usr/bin/env python3
"""Read-only, bounded handoff from exact native build to unique app runtime.

Only GET requests are made. No dispatch, rerun, branch update or write API exists.
Success emits the discovered runtime ID only after both exact upstream runs
complete successfully. Historical other-SHA runs are not candidate matches.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.parse

REPOSITORY = 'Russianranger/coh-android'
BRANCH = 'armport/mapserver-startup-60s'
NATIVE_WORKFLOW = '.github/workflows/armport-build.yml'
RUNTIME_WORKFLOW = '.github/workflows/armport-app-runtime.yml'
PENDING = {'queued', 'in_progress', 'requested', 'waiting', 'pending'}
MAX_PAGES = 10
MAX_SECONDS = 198 * 60


class UpstreamError(RuntimeError):
    pass


class RetryableApiError(RuntimeError):
    pass


def require(value, message):
    if not value:
        raise UpstreamError(message)


def positive(value):
    return type(value) is int and value > 0


class GitHubReadOnly:
    """Use the same authenticated gh API mechanism as the existing workflows."""
    def __init__(self, repository, token):
        require(repository == REPOSITORY, 'Only the assigned repository is supported')
        require(isinstance(token, str) and bool(token), 'Configured read-only Actions token is required')
        self.repository = repository

    def __call__(self, path):
        require(path.startswith('/actions/') and '://' not in path and '..' not in path,
                'Only repository Actions reads are permitted')
        try:
            result = subprocess.run(['gh', 'api', '--method', 'GET', 'repos/' + self.repository + path],
                                    capture_output=True, text=True, timeout=45)
        except subprocess.TimeoutExpired:
            raise RetryableApiError('Temporary GitHub Actions GET timeout') from None
        if result.returncode:
            if re.search(r'HTTP (?:429|5[0-9][0-9])\b|API rate limit exceeded', result.stderr):
                raise RetryableApiError('Temporary GitHub Actions GET failure')
            raise UpstreamError('GitHub Actions GET failed; inspect workflow authorization/endpoint')
        require(len(result.stdout.encode()) <= 16 * 1024 * 1024, 'GitHub response exceeds bound')
        try:
            value = json.loads(result.stdout)
        except ValueError:
            raise UpstreamError('GitHub Actions response is not JSON') from None
        require(isinstance(value, dict), 'GitHub Actions response must be an object')
        return value


def validate_identity(run, identifier, workflow, commit, branch, repository=REPOSITORY):
    require(isinstance(run, dict) and positive(identifier)
            and type(run.get('id')) is int and run['id'] == identifier
            and run.get('path') == workflow and run.get('event') == 'workflow_dispatch'
            and run.get('head_sha') == commit and run.get('head_branch') == branch
            and isinstance(run.get('repository'), dict) and run['repository'].get('full_name') == repository
            and isinstance(run.get('head_repository'), dict) and run['head_repository'].get('full_name') == repository,
            'Upstream source, branch, workflow, event, repository or run ID mismatch')


def validate_run(run, identifier, workflow, commit, branch, repository=REPOSITORY):
    validate_identity(run, identifier, workflow, commit, branch, repository)
    status = run.get('status')
    require(status == 'completed' or status in PENDING, 'Unknown upstream run status')
    if status == 'completed':
        require(run.get('conclusion') == 'success',
                'Upstream run ' + str(identifier) + ' completed with ' + str(run.get('conclusion')))
        return True
    require(run.get('conclusion') is None, 'Incomplete upstream run already has a conclusion')
    return False


def discover_runtime(api, commit, branch):
    """Scan the complete bounded branch/event query, never choose newest run."""
    found = {}
    total = None
    observed = 0
    for page in range(1, MAX_PAGES + 1):
        query = urllib.parse.urlencode({'branch': branch, 'event': 'workflow_dispatch', 'per_page': 100, 'page': page})
        response = api('/actions/workflows/armport-app-runtime.yml/runs?' + query)
        count, runs = response.get('total_count'), response.get('workflow_runs')
        require(type(count) is int and 0 <= count <= MAX_PAGES * 100
                and isinstance(runs, list) and len(runs) <= 100,
                'Cannot establish unique runtime from bounded GitHub result')
        if total is None:
            total = count
        elif count != total:
            # A new first-page run can shift later pages. Restart this read
            # rather than missing a duplicate inserted before page two.
            raise RetryableApiError('Runtime query changed during pagination')
        observed += len(runs)
        for run in runs:
            require(isinstance(run, dict), 'Malformed runtime search result')
            identifier, observed_sha = run.get('id'), run.get('head_sha')
            require(isinstance(observed_sha, str) and re.fullmatch('[0-9a-f]{40}', observed_sha),
                    'Malformed runtime source commit')
            validate_identity(run, identifier, RUNTIME_WORKFLOW, observed_sha, branch)
            if observed_sha != commit:
                continue  # Historical source revisions are not this candidate.
            # The list result is itself source checked; GET below rechecks the
            # selected immutable ID and its current completion state.
            validate_run(run, identifier, RUNTIME_WORKFLOW, commit, branch)
            found[identifier] = run
        require(len(found) <= 1, 'Multiple matching candidate runtime runs; refusing ambiguous handoff')
        if observed >= total:
            break
        require(len(runs) > 0 and page < MAX_PAGES, 'Runtime pagination is incomplete; uniqueness is unknown')
    return next(iter(found)) if found else None


def wait_for_upstreams(api, *, native_run_id, commit, branch=BRANCH, repository=REPOSITORY,
                       timeout_seconds=MAX_SECONDS, poll_seconds=30, clock=time.monotonic,
                       sleeper=time.sleep, log=print):
    require(repository == REPOSITORY and branch == BRANCH and positive(native_run_id)
            and isinstance(commit, str) and re.fullmatch('[0-9a-f]{40}', commit), 'Exact assigned source/run/branch required')
    require(type(timeout_seconds) is int and 0 < timeout_seconds <= MAX_SECONDS
            and type(poll_seconds) is int and 0 < poll_seconds <= 60, 'Bounded wait and polling intervals required')
    started = clock()
    deadline = started + timeout_seconds
    pinned_runtime = None
    last_status = None
    polls = 0
    while True:
        require(clock() < deadline, 'Timed out waiting for exact native build and unique candidate runtime')
        polls += 1
        try:
            native = api('/actions/runs/' + str(native_run_id))
            native_done = validate_run(native, native_run_id, NATIVE_WORKFLOW, commit, branch, repository)
            runtime_id = discover_runtime(api, commit, branch)
            if pinned_runtime is not None:
                require(runtime_id == pinned_runtime, 'Previously discovered runtime disappeared or changed identity')
            if runtime_id is not None:
                pinned_runtime = runtime_id
                runtime = api('/actions/runs/' + str(runtime_id))
                runtime_done = validate_run(runtime, runtime_id, RUNTIME_WORKFLOW, commit, branch, repository)
            else:
                runtime, runtime_done = None, False
            require(clock() <= deadline, 'Upstream reads exceeded the bounded wait')
            state = (native['status'], runtime_id, runtime.get('status') if runtime else 'not_discovered')
            if state != last_status:
                log('Read-only upstream wait: native=' + str(native_run_id) + '/' + native['status']
                    + ' runtime=' + str(runtime_id) + '/' + str(state[2]))
                last_status = state
            if native_done and runtime_done:
                return {'native_run_id': native_run_id, 'runtime_run_id': runtime_id,
                        'candidate_commit': commit, 'candidate_branch': branch,
                        'both_completed_successfully': True, 'polls': polls,
                        'elapsed_seconds': round(clock() - started, 3)}
        except RetryableApiError as error:
            log(str(error) + '; retrying within the existing wait bound')
        remaining = deadline - clock()
        require(remaining > 0, 'Timed out waiting for exact native build and unique candidate runtime')
        sleeper(min(poll_seconds, remaining))


def emit_output(path, result):
    identifier = result.get('runtime_run_id')
    require(result.get('both_completed_successfully') is True and positive(identifier),
            'Cannot emit a runtime ID without both exact successful upstream stages')
    with Path(path).open('a', encoding='utf-8') as stream:
        stream.write('runtime_run_id=' + str(identifier) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', default=REPOSITORY)
    parser.add_argument('--branch', default=BRANCH)
    parser.add_argument('--candidate-commit', required=True)
    parser.add_argument('--native-build-run-id', type=int, required=True)
    parser.add_argument('--timeout-seconds', type=int, default=MAX_SECONDS)
    parser.add_argument('--poll-seconds', type=int, default=30)
    parser.add_argument('--github-output', type=Path, default=os.environ.get('GITHUB_OUTPUT'))
    args = parser.parse_args()
    try:
        api = GitHubReadOnly(args.repository, os.environ.get('GH_TOKEN'))
        result = wait_for_upstreams(api, native_run_id=args.native_build_run_id,
            commit=args.candidate_commit, branch=args.branch, repository=args.repository,
            timeout_seconds=args.timeout_seconds, poll_seconds=args.poll_seconds)
        if args.github_output:
            emit_output(args.github_output, result)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (UpstreamError, OSError) as error:
        print('::error title=Modern runtime upstream handoff::' + str(error).replace('\n', ' ')[:1000])
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
