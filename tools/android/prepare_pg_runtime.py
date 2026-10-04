#!/usr/bin/env python3
"""Build a pinned PG-only ARM64/glibc overlay in Docker on an ARM64 runner."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile
import urllib.request
import uuid

from build_pg_runtime import check_source, digest, verify_overlay

HERE = Path(__file__).resolve().parent


def load_lock(path):
    lock = json.loads(path.read_text())
    if (lock.get('format') != 1 or lock.get('builder_platform') != 'linux/arm64'
            or not re.fullmatch(r'debian@sha256:[0-9a-f]{64}', lock.get('builder_image', ''))
            or not re.fullmatch(r'\d{8}T\d{6}Z', lock.get('debian_snapshot', ''))
            or not re.fullmatch(r'[0-9a-f]{64}', lock.get('runtime_base_sha256', ''))
            or not re.fullmatch(r'[0-9a-f]{64}', lock.get('source', {}).get('sha256', ''))
            or lock.get('prefix') != '/opt/coh/pgsql'):
        raise ValueError('Invalid PostgreSQL build lock')
    if lock['source']['url'] != 'https://ftp.postgresql.org/pub/source/v{0}/postgresql-{0}.tar.bz2'.format(lock['version']):
        raise ValueError('PostgreSQL source URL must be its versioned official release')
    return lock


def fetch_source(lock, destination):
    with urllib.request.urlopen(lock['source']['url'], timeout=60) as response, destination.open('wb') as output:
        if not response.url.startswith('https://'):
            raise ValueError('PostgreSQL source redirected outside HTTPS')
        size = 0
        while block := response.read(1024 * 1024):
            size += len(block)
            if size > lock['source']['bytes']:
                raise ValueError('PostgreSQL source exceeds pinned size')
            output.write(block)
    check_source(destination, lock)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repository-commit', required=True)
    parser.add_argument('--source-archive', type=Path)
    parser.add_argument('--run-url', default='')
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{40}', args.repository_commit):
        raise ValueError('Repository commit must be a full lowercase Git SHA')
    if platform.system() != 'Linux' or platform.machine().lower() not in ('aarch64', 'arm64'):
        raise ValueError('Use a native Linux ARM64 runner; CPU emulation is outside this build contract')
    lock_path = HERE / 'postgresql-lock.json'
    lock = load_lock(lock_path)
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError('Output directory must be empty; existing artifacts are not overwritten')
    args.output.mkdir(parents=True, exist_ok=True)
    image = 'coh-pg-runtime-build:' + uuid.uuid4().hex
    container = None
    try:
        with tempfile.TemporaryDirectory(prefix='coh-pg-build-') as directory:
            context = Path(directory)
            source = context / 'postgresql.tar.bz2'
            if args.source_archive:
                check_source(args.source_archive, lock)
                shutil.copyfile(args.source_archive, source)
            else:
                fetch_source(lock, source)
            names = ('postgresql-lock.json', 'build_pg_runtime.py', 'pg-runtime.Dockerfile')
            for name in names:
                shutil.copyfile(HERE / name, context / name)
            provenance = {'repository_commit': args.repository_commit, 'run_url': args.run_url,
                          'build_inputs': {name: digest(HERE / name) for name in (*names, 'prepare_pg_runtime.py')}}
            (context / 'provenance.json').write_text(json.dumps(provenance, sort_keys=True) + '\n')
            subprocess.run(['docker', 'build', '--platform', lock['builder_platform'], '--build-arg', 'BASE_IMAGE=' + lock['builder_image'], '--build-arg', 'DEBIAN_SNAPSHOT=' + lock['debian_snapshot'], '-f', str(context / 'pg-runtime.Dockerfile'), '-t', image, str(context)], check=True)
            container = subprocess.check_output(['docker', 'create', image], text=True).strip()
            subprocess.run(['docker', 'cp', container + ':/out/.', str(args.output.resolve())], check=True)
        receipt = json.loads((args.output / 'pg-runtime-build.json').read_text())
        if receipt['input_lock'] != lock or receipt['provenance'] != provenance or receipt['repository_commit'] != args.repository_commit:
            raise ValueError('Container output provenance differs from requested inputs')
        verify_overlay(args.output / 'pg-runtime-overlay.tar.gz', receipt)
        print(json.dumps({'archive': receipt['archive'], 'repository_commit': args.repository_commit, 'validation': receipt['validation']}))
    finally:
        if container:
            subprocess.run(['docker', 'rm', '-f', container], check=False)
        subprocess.run(['docker', 'image', 'rm', image], check=False, stdout=subprocess.DEVNULL)


if __name__ == '__main__':
    main()
