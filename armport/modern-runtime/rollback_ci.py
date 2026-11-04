#!/usr/bin/env python3
"""Build one real server rollback APK through the existing authorized workflow.

The original coordinator must finish successfully before a second APK run exists.
Only this workflow's ordinary Actions token dispatches armport-thor-apk.yml; no
native build, candidate source edit, release or signing implementation is added.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.parse

import modern_wait_upstream as upstream

REPOSITORY, SOURCE_BRANCH = upstream.REPOSITORY, upstream.BRANCH
SOURCE = '1f75894db9117f3567b76d087d7cc5ddce87b3e6'
PARENT = 41378023882
SUPPORT_BRANCH = 'armport/mapserver-modern-runtime-qualification'
PARENT_PATH = '.github/workflows/mapserver-startup-ci.yml'
OWN_PATH = '.github/workflows/mapserver-rollback-corrected-ci.yml'
OWN_WORKFLOW = Path(OWN_PATH).name
OWN_WORKFLOW_REF = REPOSITORY + '/' + OWN_PATH + '@refs/heads/' + SUPPORT_BRANCH
APK_PATH = '.github/workflows/armport-thor-apk.yml'
APK_WORKFLOW = 'armport-thor-apk.yml'
ARTIFACT = 'coh-atlas-gameplay-0.13.52-apk'
METRICS_STEP = 'Authenticate server qualification and both variant byte inventories'
SIGN_STEP = 'Build and sign COH Atlas Gameplay 0.13.52'
ROLLBACK_MAP = 'fea96d0a20f5e245930abd0a97e8cc1da7c4ef4c83ff8a7d5a5c283ba8071363'
require = upstream.require


class ActionsApi:
    """GET metadata; the sole permitted POST is the exact rollback dispatch."""
    def __call__(self, endpoint, payload=None):
        require(endpoint.startswith('/actions/') or endpoint == '/git/ref/heads/' + SOURCE_BRANCH,
                'Unexpected rollback API endpoint')
        require('://' not in endpoint and '..' not in endpoint, 'Unsafe rollback API endpoint')
        if payload is not None:
            inputs = payload.get('inputs', {}) if isinstance(payload, dict) else {}
            runtime = inputs.get('m4_run_id')
            require(endpoint == '/actions/workflows/' + APK_WORKFLOW + '/dispatches'
                    and set(payload) == {'ref', 'inputs'} and payload['ref'] == SOURCE_BRANCH
                    and set(inputs) == {'m4_run_id', 'server_metrics'}
                    and isinstance(runtime, str) and runtime.isdigit() and int(runtime) > 0
                    and inputs['server_metrics'] is False, 'Only the exact server_metrics=false rollback dispatch is allowed')
        command = ['gh', 'api', '--method', 'GET' if payload is None else 'POST', 'repos/' + REPOSITORY + endpoint]
        if payload is not None: command += ['--input', '-']
        try:
            result = subprocess.run(command, input=None if payload is None else json.dumps(payload),
                                    capture_output=True, text=True, timeout=45)
        except subprocess.TimeoutExpired:
            if payload is not None:
                raise upstream.UpstreamError('Rollback POST result uncertain; inspect Actions and do not blindly redispatch') from None
            raise upstream.RetryableApiError('Temporary rollback metadata GET timeout') from None
        if result.returncode:
            if payload is None and re.search(r'HTTP (?:429|5[0-9][0-9])\b|API rate limit exceeded', result.stderr):
                raise upstream.RetryableApiError('Temporary rollback metadata GET failure')
            message = ('Rollback POST result uncertain; inspect Actions and do not blindly redispatch'
                       if payload is not None else 'Rollback metadata GET failed; inspect authorization/endpoint')
            raise upstream.UpstreamError(message)
        require(len(result.stdout.encode()) <= 16 * 1024 * 1024, 'Rollback API response exceeds bound')
        return json.loads(result.stdout) if result.stdout.strip() else None


class Rollback:
    def __init__(self, *, current_run_id, supporting_sha, attempt=1, api=None, clock=time.monotonic,
                 sleep=time.sleep, timeout_seconds=290 * 60, poll_seconds=30):
        require(upstream.positive(current_run_id) and re.fullmatch('[0-9a-f]{40}', supporting_sha), 'Supporting workflow identity required')
        require(attempt == 1 and type(attempt) is int, 'Rollback coordinator reruns are refused; inspect existing APK runs')
        require(type(timeout_seconds) is int and 0 < timeout_seconds <= 290 * 60
                and type(poll_seconds) is int and 0 < poll_seconds <= 60, 'Bounded rollback coordinator required')
        self.current, self.supporting_sha = current_run_id, supporting_sha
        self.api, self.clock, self.sleep = api or ActionsApi(), clock, sleep
        self.deadline, self.poll = clock() + timeout_seconds, poll_seconds

    def check_time(self):
        require(self.clock() < self.deadline, 'Rollback wait exceeded bound; inspect the observed APK run instead of redispatching')

    def read(self, endpoint):
        while True:
            self.check_time()
            try: return self.api(endpoint)
            except upstream.RetryableApiError:
                self.pause(self.poll)

    def pause(self, seconds):
        self.check_time()
        self.sleep(min(seconds, self.deadline - self.clock()))

    def checked(self, run, identifier, path, *, branch=SOURCE_BRANCH, sha=SOURCE, event='workflow_dispatch'):
        require(isinstance(run, dict) and type(run.get('id')) is int and run['id'] == identifier
                and run.get('head_sha') == sha and run.get('head_branch') == branch
                and run.get('path') == path and run.get('event') == event
                and isinstance(run.get('repository'), dict) and run['repository'].get('full_name') == REPOSITORY
                and isinstance(run.get('head_repository'), dict) and run['head_repository'].get('full_name') == REPOSITORY, 'Rollback stage source identity differs')
        state = run.get('status')
        require(state == 'completed' or state in upstream.PENDING, 'Unknown rollback stage status')
        if state == 'completed':
            require(run.get('conclusion') == 'success', 'Required run failed: ' + str(identifier) + ' ' + str(run.get('conclusion')))
            return True
        require(run.get('conclusion') is None, 'Pending rollback stage has a conclusion')
        return False

    def frozen(self):
        ref = self.read('/git/ref/heads/' + SOURCE_BRANCH)
        require(ref.get('object', {}).get('sha') == SOURCE, 'Startup branch moved; refusing mixed-source rollback')

    def runs(self, workflow, *, branch=SOURCE_BRANCH, sha=SOURCE, event='workflow_dispatch'):
        query = urllib.parse.urlencode({'branch': branch, 'event': event, 'per_page': 100})
        value = self.read('/actions/workflows/' + workflow + '/runs?' + query)
        require(type(value.get('total_count')) is int and 0 <= value['total_count'] <= 100
                and isinstance(value.get('workflow_runs'), list) and len(value['workflow_runs']) == value['total_count'],
                'Rollback workflow discovery is incomplete or exceeds bound')
        return [r for r in value['workflow_runs'] if (sha is None or r.get('head_sha') == sha)
                and r.get('head_branch') == branch and r.get('event') == event]

    def artifact(self, identifier):
        inventory = self.read('/actions/runs/' + str(identifier) + '/artifacts?per_page=100')
        require(type(inventory.get('total_count')) is int and 0 <= inventory['total_count'] <= 100
                and isinstance(inventory.get('artifacts'), list) and len(inventory['artifacts']) == inventory['total_count'],
                'Rollback artifact inventory is incomplete or exceeds bound')
        records = [a for a in inventory.get('artifacts', []) if a.get('name') == ARTIFACT]
        require(len(records) == 1 and records[0].get('expired') is False
                and upstream.positive(records[0].get('id')) and upstream.positive(records[0].get('size_in_bytes')),
                'Exact live APK artifact missing, duplicate or expired')
        return {key: records[0].get(key) for key in ('id', 'name', 'size_in_bytes', 'digest', 'archive_download_url')}

    def metrics_path(self, identifier, enabled):
        value = self.read('/actions/runs/' + str(identifier) + '/jobs?filter=latest&per_page=100')
        require(value.get('total_count') == 1 and len(value.get('jobs', [])) == 1, 'Expected one exact APK packaging job')
        steps = value['jobs'][0].get('steps', [])
        metrics = [s for s in steps if s.get('name') == METRICS_STEP]
        signing = [s for s in steps if s.get('name') == SIGN_STEP]
        require(len(metrics) == len(signing) == 1 and signing[0].get('conclusion') == 'success'
                and metrics[0].get('conclusion') == ('success' if enabled else 'skipped'),
                'APK metrics input path or successful authorized signing differs')

    def execute(self):
        # Existing workflow history is the ambiguity check; no new receipt or
        # lease system is introduced. A failed earlier coordinator may have sent
        # a POST, so a new kickoff must not blindly send another one.
        others = self.runs(OWN_WORKFLOW, branch=SUPPORT_BRANCH, sha=None, event='push')
        require(all(r.get('id') == self.current for r in others), 'Another rollback coordinator exists; inspect its run before a new kickoff')
        while not self.checked(self.read('/actions/runs/' + str(PARENT)), PARENT, PARENT_PATH, event='push'):
            self.pause(self.poll)
        self.frozen()
        runtime_id = upstream.discover_runtime(self.read, SOURCE, SOURCE_BRANCH)
        require(runtime_id is not None and self.checked(self.read('/actions/runs/' + str(runtime_id)),
            runtime_id, upstream.RUNTIME_WORKFLOW), 'Unique successful same-source app runtime required')
        primary = self.runs(APK_WORKFLOW)
        require(len(primary) == 1 and self.checked(primary[0], primary[0].get('id'), APK_PATH),
                'Exactly one successful primary APK run is required; refusing blind duplicate')
        primary_id = primary[0]['id']
        self.metrics_path(primary_id, True)
        self.artifact(primary_id)
        # Recheck parent and frozen branch immediately before the sole POST.
        require(self.checked(self.read('/actions/runs/' + str(PARENT)), PARENT, PARENT_PATH, event='push'), 'Parent coordinator became active again')
        require(self.checked(self.read('/actions/runs/' + str(primary_id)), primary_id, APK_PATH),
                'Primary APK run became active again')
        self.frozen(); self.check_time()
        self.api('/actions/workflows/' + APK_WORKFLOW + '/dispatches',
                 {'ref': SOURCE_BRANCH, 'inputs': {'m4_run_id': str(runtime_id), 'server_metrics': False}})
        observation_deadline = min(self.deadline, self.clock() + 120)
        while True:
            runs = self.runs(APK_WORKFLOW)
            identifiers = {r['id'] for r in runs}
            require(primary_id in identifiers and len(identifiers) <= 2, 'APK run set became ambiguous after rollback POST')
            new = identifiers - {primary_id}
            if new:
                require(len(new) == 1 and len(runs) == 2, 'Expected exactly one new rollback APK run')
                rollback_id = next(iter(new)); break
            require(self.clock() < observation_deadline, 'Rollback POST did not become observable; do not blindly redispatch')
            self.pause(2)
        print('Rollback APK run: https://github.com/' + REPOSITORY + '/actions/runs/' + str(rollback_id), flush=True)
        while True:
            runs = self.runs(APK_WORKFLOW)
            require({r['id'] for r in runs} == {primary_id, rollback_id} and len(runs) == 2,
                    'Additional or missing APK runs make rollback identity ambiguous')
            run = self.read('/actions/runs/' + str(rollback_id))
            if self.checked(run, rollback_id, APK_PATH): break
            self.pause(self.poll)
        self.metrics_path(rollback_id, False)
        artifact = self.artifact(rollback_id)
        self.frozen()
        return {'candidate_commit': SOURCE, 'parent_coordinator_run_id': PARENT, 'runtime_run_id': runtime_id,
            'primary_apk_run_id': primary_id, 'rollback_apk_run_id': rollback_id, 'artifact': artifact,
            'server_metrics': False, 'expected_mapserver_sha256': ROLLBACK_MAP, 'apk_payload_independently_verified': False}


def main():
    require(os.environ.get('GITHUB_REPOSITORY') == REPOSITORY
            and os.environ.get('GITHUB_REF_NAME') == SUPPORT_BRANCH
            and os.environ.get('GITHUB_WORKFLOW_REF') == OWN_WORKFLOW_REF and bool(os.environ.get('GH_TOKEN')),
            'Rollback coordinator requires the exact corrected workflow on the authorized supporting branch')
    result = Rollback(current_run_id=int(os.environ['GITHUB_RUN_ID']), supporting_sha=os.environ['GITHUB_SHA'],
                      attempt=int(os.environ.get('GITHUB_RUN_ATTEMPT', '0'))).execute()
    text = json.dumps(result, sort_keys=True)
    print(text, flush=True)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with Path(os.environ['GITHUB_STEP_SUMMARY']).open('a') as stream:
            stream.write('Rollback packaging result: `' + text + '`\n')


if __name__ == '__main__':
    main()
