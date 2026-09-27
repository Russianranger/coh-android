#!/usr/bin/env python3
"""Container-side ARM64/glibc PostgreSQL build and regular-file-only overlay."""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import struct
import subprocess
import tarfile
import tempfile

REQUIRED_BINS = ('postgres', 'initdb', 'pg_ctl', 'psql', 'pg_isready', 'pg_dump', 'pg_restore')
PREFIX = '/opt/coh/pgsql'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check_source(path, lock):
    if path.stat().st_size != lock['source']['bytes'] or digest(path) != lock['source']['sha256']:
        raise ValueError('PostgreSQL source size/hash differs from lock')


def extract_source(path, destination, version):
    root = 'postgresql-' + version
    with tarfile.open(path, 'r:bz2') as archive:
        for member in archive.getmembers():
            parts = PurePosixPath(member.name).parts
            if not parts or parts[0] != root or '..' in parts or member.name.startswith('/'):
                raise ValueError('Source archive member escapes pinned source root')
            if not member.isfile() and not member.isdir():
                raise ValueError('Source archive contains a link or special file')
        archive.extractall(destination)
    return destination / root


def elf_header(data):
    if data[:4] != b'\x7fELF':
        return None
    if len(data) < 64 or data[4:6] != b'\x02\x01' or struct.unpack_from('<H', data, 18)[0] != 183:
        raise ValueError('Overlay ELF must be little-endian ELF64 AArch64')
    return {'class': 64, 'machine': 'AArch64', 'endian': 'little'}


def collect_files(prefix):
    """Flatten internal install symlinks; APK extraction needs no hardlinks."""
    prefix = prefix.resolve()
    files = {}
    for path in sorted(prefix.rglob('*')):
        if path.is_symlink() and not path.resolve().is_relative_to(prefix):
            raise ValueError('Installed symlink escapes PostgreSQL prefix')
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError('Installed prefix contains a special file')
        data = path.read_bytes()
        name = 'opt/coh/pgsql/' + path.relative_to(prefix).as_posix()
        mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
        record = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'mode': mode}
        elf = elf_header(data)
        if elf:
            record['elf'] = elf
        files[name] = (record, data)
    for name in REQUIRED_BINS:
        record, _ = files['opt/coh/pgsql/bin/' + name]
        if 'elf' not in record or record['mode'] != 0o755:
            raise ValueError('Required PostgreSQL binary is not executable ARM64 ELF: ' + name)
    return files


def write_overlay(path, files):
    with path.open('wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode='w', format=tarfile.PAX_FORMAT) as archive:
            for name, (record, data) in sorted(files.items()):
                member = tarfile.TarInfo(name)
                member.mode = record['mode']
                member.uid = member.gid = 1000
                member.uname = member.gname = 'coh'
                member.mtime = 0
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))


def verify_overlay(path, receipt):
    if digest(path) != receipt['archive']['sha256'] or path.stat().st_size != receipt['archive']['bytes']:
        raise ValueError('Overlay archive hash/size mismatch')
    seen = set()
    with tarfile.open(path, 'r:gz') as archive:
        for member in archive:
            parts = PurePosixPath(member.name).parts
            if parts[:3] != ('opt', 'coh', 'pgsql') or '..' in parts or not member.isfile() or member.name in seen:
                raise ValueError('Overlay contains an unsafe or duplicate member')
            seen.add(member.name)
            expected = receipt['files'].get(member.name)
            if expected is None or member.size != expected['bytes'] or member.mode != expected['mode']:
                raise ValueError('Overlay member metadata differs from receipt')
            data = archive.extractfile(member).read()
            if hashlib.sha256(data).hexdigest() != expected['sha256']:
                raise ValueError('Overlay member hash differs from receipt')
            if elf_header(data) != expected.get('elf'):
                raise ValueError('Overlay ELF architecture differs from receipt')
    if seen != set(receipt['files']):
        raise ValueError('Overlay file inventory differs from receipt')
    for name in REQUIRED_BINS:
        record = receipt['files'].get('opt/coh/pgsql/bin/' + name, {})
        if record.get('elf', {}).get('machine') != 'AArch64' or record.get('mode') != 0o755:
            raise ValueError('Overlay lacks a required ARM64 PostgreSQL executable')


def inspect_dependencies(prefix, files):
    result = {}
    allowed = {'libc.so.6', 'libm.so.6', 'libgcc_s.so.1', 'libpq.so.5', 'libpthread.so.0', 'libdl.so.2', 'librt.so.1'}
    for name, (record, _) in files.items():
        if 'elf' not in record:
            continue
        path = prefix / PurePosixPath(name).relative_to('opt/coh/pgsql')
        dynamic = subprocess.check_output(['readelf', '-d', str(path)], text=True)
        needed = re.findall(r'\(NEEDED\).*?\[(.*?)\]', dynamic)
        if set(needed) - allowed:
            raise ValueError('Unqualified shared dependency for ' + name + ': ' + repr(needed))
        versions = subprocess.check_output(['readelf', '--version-info', str(path)], text=True)
        glibc = sorted(set(re.findall(r'\bGLIBC_(\d+\.\d+)', versions)), key=lambda s: tuple(map(int, s.split('.'))))
        if any(tuple(map(int, v.split('.'))) > (2, 36) for v in glibc):
            raise ValueError('ELF needs glibc newer than the pinned runtime base')
        linked = subprocess.run(['ldd', str(path)], text=True, capture_output=True, env={**os.environ, 'LD_LIBRARY_PATH': str(prefix / 'lib')})
        if linked.returncode or 'not found' in linked.stdout + linked.stderr:
            raise ValueError('PostgreSQL ELF dependency resolution failed: ' + name)
        result[name] = {'needed': needed, 'glibc_versions': glibc}
    return result


def smoke(prefix):
    """Prove installed tools/durability on Linux; Android/PRoot is a later gate."""
    # The container has no service account. Give initdb's getpwuid an explicit identity.
    import pwd
    try:
        pwd.getpwuid(1000)
    except KeyError:
        with open('/etc/passwd', 'a') as stream:
            stream.write('coh:x:1000:1000::/tmp:/bin/sh\n')
        with open('/etc/group', 'a') as stream:
            stream.write('coh:x:1000:\n')
    with tempfile.TemporaryDirectory(prefix='pg-native-smoke-') as directory:
        state = Path(directory)
        os.chown(state, 1000, 1000)
        def identity():
            os.setgroups([])
            os.setgid(1000)
            os.setuid(1000)
        env = {**os.environ, 'LANG': 'C', 'LC_ALL': 'C', 'HOME': directory, 'LD_LIBRARY_PATH': str(prefix / 'lib')}
        def run(binary, *args):
            return subprocess.check_output([str(prefix / 'bin' / binary), *map(str, args)], text=True, env=env, preexec_fn=identity, timeout=90).strip()
        run('initdb', '-D', state / 'data', '--no-locale', '--encoding=UTF8', '--auth-local=trust', '--auth-host=scram-sha-256', '-c', 'shared_memory_type=mmap', '-c', 'dynamic_shared_memory_type=mmap')
        options = '-h "" -k ' + directory + ' -p 55439'
        def start():
            run('pg_ctl', '-D', state / 'data', '-l', state / 'postgres.log', '-w', '-t', '30', '-o', options, 'start')
        start()
        try:
            sql = ['-X', '-h', directory, '-p', '55439', '-U', 'coh', '-d', 'postgres', '-At', '-c']
            run('psql', *sql, 'CREATE TABLE runtime_probe(value integer); INSERT INTO runtime_probe VALUES(42)')
            run('pg_ctl', '-D', state / 'data', '-w', '-m', 'fast', 'stop')
            start()
            if run('psql', *sql, 'SELECT value FROM runtime_probe') != '42':
                raise ValueError('Native PostgreSQL restart durability probe failed')
            return {'host': 'native_linux_arm64', 'uid': 1000, 'initdb': True, 'transaction_restart': True, 'shared_memory_type': 'mmap', 'dynamic_shared_memory_type': 'mmap', 'android_or_proot_execution': False}
        finally:
            run('pg_ctl', '-D', state / 'data', '-w', '-m', 'fast', 'stop')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--provenance', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if platform.machine().lower() not in ('aarch64', 'arm64'):
        raise ValueError('Build must execute on native ARM64 Linux')
    lock = json.loads(args.lock.read_text())
    check_source(args.source, lock)
    prefix = Path(lock['prefix'])
    if str(prefix) != PREFIX or prefix.exists():
        raise ValueError('Build requires its fresh dedicated PostgreSQL prefix')
    source = extract_source(args.source, Path('/build'), lock['version'])
    env = {**os.environ, **lock['configure_environment'], 'LC_ALL': 'C', 'LANG': 'C', 'TZ': 'UTC', 'SOURCE_DATE_EPOCH': '0'}
    subprocess.run(['./configure', *lock['configure']], cwd=source, env=env, check=True)
    config = (source / 'src/include/pg_config.h').read_text()
    if '#define USE_UNNAMED_POSIX_SEMAPHORES 1' not in config:
        raise ValueError('Build did not select unnamed POSIX semaphores')
    for command in (['make', '-j' + str(min(os.cpu_count() or 2, 4))], ['make', 'install']):
        subprocess.run(command, cwd=source, env=env, check=True)
    shutil.rmtree(prefix / 'include')
    for path in (prefix / 'lib').rglob('*.a'):
        path.unlink()
    shutil.rmtree(prefix / 'lib/pkgconfig', ignore_errors=True)
    license_dir = prefix / 'share/licenses'
    license_dir.mkdir(parents=True)
    shutil.copyfile(source / 'COPYRIGHT', license_dir / 'PostgreSQL-COPYRIGHT')
    files = collect_files(prefix)
    dependencies = inspect_dependencies(prefix, files)
    validation = smoke(prefix)
    args.output.mkdir(parents=True)
    archive = args.output / 'pg-runtime-overlay.tar.gz'
    write_overlay(archive, files)
    if archive.stat().st_size > 30 * 1024 * 1024:
        raise ValueError('PG overlay exceeds the 30 MiB APK asset budget')
    receipt = {
        'format': 1, 'role': 'android_arm64_glibc_postgresql_overlay',
        'repository_commit': json.loads(args.provenance.read_text())['repository_commit'],
        'provenance': json.loads(args.provenance.read_text()), 'input_lock': lock,
        'archive': {'name': archive.name, 'bytes': archive.stat().st_size, 'sha256': digest(archive)},
        'runtime': {'prefix': PREFIX, 'abi': lock['runtime_abi'], 'base_sha256': lock['runtime_base_sha256'], 'uid': 1000, 'requires_single_proot_sysvipc_session': True, 'requires_passwd_entry': 'coh:x:1000:1000::/state:/bin/sh', 'shared_memory_type': 'mmap', 'dynamic_shared_memory_type': 'mmap', 'semaphores': 'unnamed_posix', 'bionic_native': False},
        'compiler': subprocess.check_output(['cc', '--version'], text=True).splitlines()[0],
        'builder_packages': subprocess.check_output(['dpkg-query', '-W', '-f=${binary:Package}\t${Version}\n'], text=True).splitlines(),
        'postgres_version': subprocess.check_output([str(prefix / 'bin/postgres'), '--version'], text=True).strip(),
        'files': {name: record for name, (record, _) in files.items()},
        'elf_dependencies': dependencies, 'validation': validation,
        'scope': 'Native ARM64/glibc build and Linux smoke; Thor Android/PRoot execution remains a separate acceptance gate.'
    }
    verify_overlay(archive, receipt)
    (args.output / 'pg-runtime-build.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    # Keep the exact corresponding source beside the distributable for compliance/rebuilding.
    shutil.copyfile(args.source, args.output / ('postgresql-' + lock['version'] + '.tar.bz2'))


if __name__ == '__main__':
    main()
