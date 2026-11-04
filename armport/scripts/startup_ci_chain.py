#!/usr/bin/env python3
"""Dispatch the existing build -> runtime -> APK workflows at one frozen head.

Only the explicitly authorized isolated experiment uses this coordinator. It
runs no compiler and makes no runtime/performance qualification of its own.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import time

REPOSITORY = 'Russianranger/coh-android'
BRANCH = 'armport/mapserver-startup-60s'


def require(value, message):
    if not value:
        raise RuntimeError(message)


class Chain:
    def __init__(self, sha, *, api=None, clock=time.monotonic, sleep=time.sleep):
        require(re.fullmatch('[0-9a-f]{40}', sha) is not None, 'Exact source SHA required')
        self.sha, self.api, self.clock, self.sleep = sha, api or self.github, clock, sleep

    @staticmethod
    def github(endpoint, payload=None):
        command = ['gh', 'api', '--method', 'GET' if payload is None else 'POST',
                   'repos/' + REPOSITORY + '/' + endpoint]
        if payload is not None:
            command += ['--input', '-']
        result = subprocess.run(command, input=None if payload is None else json.dumps(payload),
                                capture_output=True, text=True, timeout=60)
        require(result.returncode == 0, 'GitHub operation failed: ' + endpoint + '\n' + result.stderr[-1500:])
        return json.loads(result.stdout) if result.stdout.strip() else None

    def frozen(self):
        current = self.api('git/ref/heads/' + BRANCH)
        require(current['object']['sha'] == self.sha, 'Experiment branch moved; refusing mixed-head dispatch')

    def runs(self, workflow):
        result = self.api('actions/workflows/' + workflow + '/runs?event=workflow_dispatch&head_sha='
                          + self.sha + '&per_page=100')
        require(result['total_count'] <= 100, 'Workflow discovery exceeded bound')
        runs = [r for r in result['workflow_runs'] if r['head_sha'] == self.sha
                and r['head_branch'] == BRANCH and r['event'] == 'workflow_dispatch']
        require(len(runs) <= 1, 'Duplicate stage runs require investigation; refusing another dispatch')
        return runs

    def stage(self, workflow, inputs, artifacts):
        self.frozen()
        runs = self.runs(workflow)
        if not runs:
            self.api('actions/workflows/' + workflow + '/dispatches',
                     {'ref': BRANCH, 'inputs': inputs})
            for _ in range(30):
                runs = self.runs(workflow)
                if runs:
                    break
                self.sleep(2)
        require(runs, 'Dispatched stage did not become observable; do not blindly redispatch')
        run_id = runs[0]['id']
        url = 'https://github.com/' + REPOSITORY + '/actions/runs/' + str(run_id)
        print(workflow + ': ' + url, flush=True)
        summary = os.environ.get('GITHUB_STEP_SUMMARY')
        if summary:
            with Path(summary).open('a') as stream:
                stream.write('- [' + workflow + '](' + url + '), source `' + self.sha + '`\n')
        deadline, previous = self.clock() + 3 * 60 * 60, None
        while True:
            run = self.api('actions/runs/' + str(run_id))
            require(run['head_sha'] == self.sha and run['head_branch'] == BRANCH
                    and run['event'] == 'workflow_dispatch', 'Stage source identity differs')
            state = (run['status'], run.get('conclusion'))
            if state != previous:
                print(workflow + ': ' + str(state), flush=True)
                previous = state
            if run['status'] == 'completed':
                require(run['conclusion'] == 'success', 'Stage failed: ' + url)
                break
            require(self.clock() < deadline, 'Stage wait exceeded bound: ' + url)
            self.sleep(20)
        inventory = self.api('actions/runs/' + str(run_id) + '/artifacts?per_page=100')
        require(inventory['total_count'] <= 100, 'Artifact inventory exceeded bound')
        available = {a['name'] for a in inventory['artifacts'] if a.get('expired') is False}
        require(set(artifacts) <= available, 'Required stage artifacts absent: ' + str(set(artifacts) - available))
        self.frozen()
        return run_id

    def execute(self):
        build = self.stage('armport-build.yml', {'build_server_metrics': True},
                           ['armport-server-metrics-native', 'armport-client-Release'])
        runtime = self.stage('armport-app-runtime.yml', {'client_run_id': str(build),
            'data_run_id': str(build), 'server_run_id': str(build)},
            ['armport-app-client-package', 'armport-app-server-metrics'])
        apk = self.stage('armport-thor-apk.yml', {'m4_run_id': str(runtime), 'server_metrics': True},
                         ['coh-atlas-gameplay-0.13.52-apk'])
        print(json.dumps({'source': self.sha, 'build': build, 'runtime': runtime, 'apk': apk,
                          'modern_thor_runtime_qualified': False, 'thor_60_second_target_proven': False}), flush=True)
        return build, runtime, apk


if __name__ == '__main__':
    require(os.environ.get('GITHUB_REPOSITORY') == REPOSITORY
            and os.environ.get('GITHUB_REF_NAME') == BRANCH, 'Coordinator is isolated to its authorized repository/branch')
    Chain(os.environ['GITHUB_SHA']).execute()
