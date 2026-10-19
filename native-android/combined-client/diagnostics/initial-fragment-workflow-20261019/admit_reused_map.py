#!/usr/bin/env python3
"""Recover one pinned historical successful Map compile; never rebuild it.

The original metadata/member validators remain unchanged. Their explicit origin
arguments describe the historical compile, independently of this execution run.
The separate reuse verifier must still admit historical/current compiler bytes.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[4]
VALIDATOR = ROOT / 'native-android/combined-client/diagnostics/server-initial-workflow-20261018/admit_workflow_artifact.py'


def load():
    spec = importlib.util.spec_from_file_location('coh_historical_map_artifact_validator', VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    if not __debug__ or os.environ.get('PYTHONOPTIMIZE'):
        raise ValueError('OPTIMIZED_REUSE_ADMISSION')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--origin', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    v = load()
    v.need(os.environ['GITHUB_REPOSITORY'] == v.REPO and os.environ['GITHUB_REF'] == 'refs/heads/native-android', 'EXECUTION_CONTEXT')
    v.need(os.environ['RUNNER_ENVIRONMENT'] == 'github-hosted' and os.environ['RUNNER_OS'] == 'Linux' and os.environ['RUNNER_ARCH'] == 'X64', 'RUNNER_CONTEXT')
    origin = json.loads(a.origin.read_bytes())
    v.need(set(origin) == {'artifact_id', 'run_id', 'revision', 'attempt', 'zip_sha256', 'receipt_sha256'}, 'ORIGIN_FIELDS')
    v.need(all(type(origin[k]) is int and origin[k] > 0 for k in ('artifact_id', 'run_id', 'attempt')), 'ORIGIN_IDS')
    v.need(all(type(origin[k]) is str and len(origin[k]) == 64 and all(c in '0123456789abcdef' for c in origin[k]) for k in ('zip_sha256', 'receipt_sha256')), 'ORIGIN_HASHES')
    artifact = v.api('actions/artifacts/' + str(origin['artifact_id']))
    run = v.api('actions/runs/' + str(origin['run_id']))
    jobs = v.api('actions/runs/' + str(origin['run_id']) + '/attempts/' + str(origin['attempt']) + '/jobs?per_page=100')
    size = v.metadata(artifact, run, jobs, origin['artifact_id'], origin['run_id'], origin['revision'], origin['zip_sha256'], origin['attempt'])
    target = a.output.absolute()
    v.need(target.resolve() == target and not target.exists() and target.parent.is_dir(), 'OUTPUT_PATH')
    os.umask(0o077)
    archive = target.with_name(target.name + '.zip')
    with archive.open('xb') as output:
        subprocess.run(['gh', 'api', 'repos/' + v.REPO + '/actions/artifacts/' + str(origin['artifact_id']) + '/zip'], stdout=output, timeout=600, check=True)
    v.need(archive.stat().st_size == size, 'ZIP_SIZE')
    with archive.open('rb') as stream:
        v.need(hashlib.file_digest(stream, 'sha256').hexdigest() == origin['zip_sha256'], 'ZIP_DIGEST')
    target.mkdir(mode=0o700)
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
        expanded = v.members(infos)
        for item in infos:
            file = target / item.filename
            file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with z.open(item) as source, file.open('xb') as output:
                shutil.copyfileobj(source, output, 1024**2)
            v.need(file.stat().st_size == item.file_size, 'EXTRACTED_SIZE')
    v.need(hashlib.sha256((target / 'compile-only-receipt.json').read_bytes()).hexdigest() == origin['receipt_sha256'], 'COMPILE_RECEIPT')
    archive.unlink()
    result = {'schema': 'coh-historical-map-artifact-recovery-v1', 'origin': origin,
              'current_execution_revision': os.environ['GITHUB_SHA'], 'zip_bytes': size,
              'members': len(infos), 'expanded_bytes': expanded,
              'historical_successful_compile_job_verified': True,
              'same_execution_run_claimed': False, 'compiler_reexecuted': False,
              'runtime_executed': False, 'world_authority': False}
    receipt = target.with_name(target.name + '-recovery.json')
    with receipt.open('x') as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write('\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
