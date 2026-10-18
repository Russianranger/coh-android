#!/usr/bin/env python3
"""Focused pure metadata/ZIP-name controls; no network, extraction or runtime."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import zipfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('new_artifact_admission', HERE / 'admit_workflow_artifact.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
revision = 'a' * 40
digest = 'b' * 64
run = {'id': 11, 'head_sha': revision, 'head_branch': 'native-android', 'path': module.WORKFLOW,
       'repository': {'id': 1368730125}, 'head_repository': {'id': 1368730125}, 'run_attempt': 1}
jobs = {'jobs': [{'name': 'compile', 'run_id': 11, 'head_sha': revision, 'status': 'completed',
                  'conclusion': 'success', 'run_attempt': 1}]}
artifact = {'id': 22, 'expired': False, 'name': 'server-initial-compile-' + revision + '-attempt-1', 'size_in_bytes': 100,
            'digest': 'sha256:' + digest, 'workflow_run': {'id': 11, 'head_sha': revision,
            'repository_id': 1368730125, 'head_repository_id': 1368730125}}
cases = []


def check(name, callback, refuse=False):
    try:
        callback()
    except (ValueError, KeyError, TypeError):
        if not refuse:
            raise
    else:
        if refuse:
            raise AssertionError(name + ': missing refusal')
    cases.append(name)


def meta(a=artifact, r=run, j=jobs):
    return module.metadata(a, r, j, 22, 11, revision, digest, 1)


check('same-current-run-successful-build', lambda: meta() == 100 or (_ for _ in ()).throw(AssertionError()))
for path, value in [
    (('artifact', 'id'), 23), (('artifact', 'expired'), True), (('artifact', 'name'), 'other'),
    (('artifact', 'size_in_bytes'), 0), (('artifact', 'size_in_bytes'), module.MAX_ZIP + 1),
    (('artifact', 'digest'), 'sha256:' + 'c' * 64), (('artifact', 'workflow_run', 'id'), 12),
    (('artifact', 'workflow_run', 'head_sha'), 'c' * 40),
    (('artifact', 'workflow_run', 'head_repository_id'), 1),
    (('run', 'id'), 12), (('run', 'head_sha'), 'c' * 40), (('run', 'head_branch'), 'other'),
    (('run', 'path'), '.github/workflows/other.yml'), (('run', 'repository', 'id'), 1), (('run', 'run_attempt'), 2),
    (('jobs', 'jobs', 0, 'conclusion'), 'failure'), (('jobs', 'jobs', 0, 'status'), 'in_progress'),
    (('jobs', 'jobs', 0, 'run_attempt'), 2), (('jobs', 'jobs', 0, 'head_sha'), 'c' * 40),
    (('jobs', 'jobs', 0, 'run_id'), 12), (('jobs', 'jobs', 0, 'name'), 'other'),
]:
    values = copy.deepcopy({'artifact': artifact, 'run': run, 'jobs': jobs})
    at = values
    for part in path[:-1]:
        at = at[part]
    at[path[-1]] = value
    check('/'.join(map(str, path)) + '=' + str(value), lambda v=values: meta(v['artifact'], v['run'], v['jobs']), True)
check('prior-attempt-artifact-name', lambda: meta(a={**artifact, 'name': 'server-initial-compile-' + revision + '-attempt-2'}), True)
duplicated = copy.deepcopy(jobs)
duplicated['jobs'] += copy.deepcopy(jobs['jobs'])
check('duplicate-compile-jobs', lambda: meta(j=duplicated), True)


def item(name, size=20, mode=stat.S_IFREG, encrypted=False):
    entry = zipfile.ZipInfo(name)
    entry.file_size = size
    entry.external_attr = mode << 16
    entry.flag_bits = int(encrypted)
    return entry


check('safe-nested-files', lambda: module.members([item('MapServer.exe'), item('source/path.c')]) == 40 or (_ for _ in ()).throw(AssertionError()))
for name in ['../escape', '/absolute', 'a/../b', 'a//b', 'a/./b', 'a\\b', 'C:/file', 'directory/']:
    check('unsafe-name:' + name, lambda n=name: module.members([item(n)]), True)
check('duplicate-members', lambda: module.members([item('same'), item('same')]), True)
check('symlink-member', lambda: module.members([item('link', mode=stat.S_IFLNK)]), True)
check('encrypted-member', lambda: module.members([item('file', encrypted=True)]), True)
check('empty-member', lambda: module.members([item('file', size=0)]), True)
check('oversized-member', lambda: module.members([item('file', size=16 * 1024**2 + 1)]), True)
check('too-many-members', lambda: module.members([item(str(i)) for i in range(129)]), True)
check('expanded-total', lambda: module.members([item(str(i), size=16 * 1024**2) for i in range(7)]), True)
print(json.dumps({'schema': 'coh-server-initial-artifact-admission-controls-v1', 'passed': True,
                  'checks': len(cases), 'cases': cases, 'helper_sha256': hashlib.sha256((HERE / 'admit_workflow_artifact.py').read_bytes()).hexdigest(),
                  'explicit_metadata_doubles': True, 'network_extraction_native_or_original_server_executed': False,
                  'world_authority': False}, indent=2))
