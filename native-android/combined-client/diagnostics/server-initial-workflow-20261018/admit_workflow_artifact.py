#!/usr/bin/env python3
"""Admit only this workflow's successful changed-Map compile artifact."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import zipfile

REPO = 'Russianranger/coh-android'
WORKFLOW = '.github/workflows/native-server-initial-observer.yml'
MAX_ZIP = 64 * 1024**2
MAX_EXPANDED = 96 * 1024**2


def need(value, reason):
    if not value:
        raise ValueError(reason)


def metadata(artifact, run, jobs, ident, run_id, revision, digest, attempt):
    need(type(ident) is int and ident > 0 and type(run_id) is int and run_id > 0, 'IDS')
    need(type(attempt) is int and attempt > 0 and run['run_attempt'] == attempt, 'RUN_ATTEMPT')
    need(re.fullmatch('[0-9a-f]{40}', revision) is not None, 'REVISION')
    need(re.fullmatch('[0-9a-f]{64}', digest) is not None, 'DIGEST')
    need(run['id'] == run_id and run['head_sha'] == revision and run['head_branch'] == 'native-android', 'RUN_IDENTITY')
    need(run['path'] == WORKFLOW, 'WORKFLOW')
    need(run['repository']['id'] == run['head_repository']['id'] == 1368730125, 'RUN_REPOSITORY')
    found = [j for j in jobs['jobs'] if j['name'] == 'compile']
    need(len(found) == 1, 'COMPILE_JOB_UNIQUE')
    job = found[0]
    need(job['run_id'] == run_id and job['head_sha'] == revision and job['status'] == 'completed' and job['conclusion'] == 'success', 'COMPILE_JOB_SUCCESS')
    need(job['run_attempt'] == attempt, 'COMPILE_ATTEMPT')
    need(artifact['id'] == ident and artifact['expired'] is False, 'ARTIFACT_IDENTITY')
    need(artifact['name'] == 'server-initial-compile-' + revision + '-attempt-' + str(attempt), 'ARTIFACT_NAME')
    need(type(artifact['size_in_bytes']) is int and 0 < artifact['size_in_bytes'] <= MAX_ZIP, 'ZIP_BOUND')
    need(artifact['digest'] == 'sha256:' + digest, 'ARTIFACT_DIGEST')
    origin = artifact['workflow_run']
    need(origin['id'] == run_id and origin['head_sha'] == revision, 'ARTIFACT_RUN')
    need(origin['repository_id'] == origin['head_repository_id'] == 1368730125, 'ARTIFACT_REPOSITORY')
    return artifact['size_in_bytes']


def members(infos):
    need(0 < len(infos) <= 128 and len({i.filename for i in infos}) == len(infos), 'MEMBERS')
    total = 0
    for item in infos:
        name = item.filename
        path = PurePosixPath(name)
        need(name == path.as_posix() and not path.is_absolute() and not any(p in ('', '.', '..') for p in path.parts), 'MEMBER_PATH')
        need('\\' not in name and ':' not in name and '\x00' not in name and not item.is_dir(), 'MEMBER_NAME')
        need(not item.flag_bits & 1 and stat.S_IFMT(item.external_attr >> 16) in (0, stat.S_IFREG), 'MEMBER_KIND')
        need(0 < item.file_size <= 16 * 1024**2, 'MEMBER_BOUND')
        total += item.file_size
    need(total <= MAX_EXPANDED, 'EXPANDED_BOUND')
    return total


def api(suffix):
    return json.loads(subprocess.check_output(['gh', 'api', 'repos/' + REPO + '/' + suffix], timeout=60))


def main():
    if not __debug__ or os.environ.get('PYTHONOPTIMIZE'):
        raise ValueError('OPTIMIZED_ADMISSION')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact-id', type=int, required=True)
    parser.add_argument('--digest', required=True)
    parser.add_argument('--receipt-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    need(os.environ['GITHUB_REPOSITORY'] == REPO and os.environ['GITHUB_REF'] == 'refs/heads/native-android', 'CHECKOUT_CONTEXT')
    need(os.environ['RUNNER_ENVIRONMENT'] == 'github-hosted' and os.environ['RUNNER_OS'] == 'Linux' and os.environ['RUNNER_ARCH'] == 'X64', 'RUNNER_CONTEXT')
    revision = os.environ['GITHUB_SHA']
    run_id = int(os.environ['GITHUB_RUN_ID'])
    attempt = int(os.environ['GITHUB_RUN_ATTEMPT'])
    need(re.fullmatch('[0-9a-f]{64}', args.receipt_sha256) is not None, 'RECEIPT_PIN')
    artifact = api('actions/artifacts/' + str(args.artifact_id))
    run = api('actions/runs/' + str(run_id))
    jobs = api('actions/runs/' + str(run_id) + '/jobs?per_page=100&filter=latest')
    size = metadata(artifact, run, jobs, args.artifact_id, run_id, revision, args.digest, attempt)
    target = args.output.absolute()
    need(target.resolve() == target and not target.exists() and target.parent.is_dir(), 'OUTPUT_PATH')
    os.umask(0o077)
    archive = target.with_name(target.name + '.zip')
    with archive.open('xb') as stream:
        subprocess.run(['gh', 'api', 'repos/' + REPO + '/actions/artifacts/' + str(args.artifact_id) + '/zip'], stdout=stream, timeout=600, check=True)
    need(archive.stat().st_size == size, 'ZIP_SIZE')
    with archive.open('rb') as stream:
        need(hashlib.file_digest(stream, 'sha256').hexdigest() == args.digest, 'ZIP_DIGEST')
    target.mkdir(mode=0o700)
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
        total = members(infos)
        for item in infos:
            path = target / item.filename
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with z.open(item) as source, path.open('xb') as output:
                shutil.copyfileobj(source, output, 1024**2)
            need(path.stat().st_size == item.file_size, 'EXTRACTED_SIZE')
    receipt = target / 'compile-only-receipt.json'
    need(receipt.is_file() and hashlib.sha256(receipt.read_bytes()).hexdigest() == args.receipt_sha256, 'COMPILE_RECEIPT')
    archive.unlink()
    result = {'schema': 'coh-server-initial-same-run-artifact-admission-v1', 'source_revision': revision,
              'run_id': run_id, 'run_attempt': attempt, 'artifact_id': args.artifact_id, 'zip_bytes': size, 'zip_sha256': args.digest,
              'compile_receipt_sha256': args.receipt_sha256, 'members': len(infos), 'expanded_bytes': total,
              'same_run_successful_compile': True, 'runtime_executed': False, 'world_authority': False}
    output = target.with_name(target.name + '-admission.json')
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
