#!/usr/bin/env python3
"""Bootstrap the verified Gradle distribution inside this isolated project."""
import hashlib
import os
import pathlib
import subprocess
import sys
import urllib.request
import zipfile

VERSION = '8.9'
SHA256 = 'd725d707bfabd4dfdc958c624003b3c80accc03f7037b5122c4b1d0ef15cecab'
URL = 'https://services.gradle.org/distributions/gradle-8.9-bin.zip'
PROJECT = pathlib.Path(__file__).resolve().parent


def main():
    cache = PROJECT / '.tooling'
    binary = cache / ('gradle-' + VERSION) / 'bin' / 'gradle'
    if not binary.exists():
        cache.mkdir(parents=True, exist_ok=True)
        archive = cache / ('gradle-' + VERSION + '-bin.zip')
        temp = archive.with_suffix('.part')
        digest = hashlib.sha256()
        count = 0
        try:
            with urllib.request.urlopen(URL, timeout=60) as response, temp.open('wb') as output:
                while chunk := response.read(1 << 20):
                    count += len(chunk)
                    if count > 140 << 20:
                        raise RuntimeError('Gradle archive exceeds bounded download size')
                    digest.update(chunk)
                    output.write(chunk)
            if digest.hexdigest() != SHA256:
                raise RuntimeError('Gradle distribution SHA256 mismatch')
            temp.replace(archive)
            with zipfile.ZipFile(archive) as bundle:
                for member in bundle.infolist():
                    destination = (cache / member.filename).resolve()
                    if not destination.is_relative_to(cache.resolve()):
                        raise RuntimeError('Unsafe Gradle ZIP path')
                bundle.extractall(cache)
            binary.chmod(0o755)
        finally:
            temp.unlink(missing_ok=True)
    args = sys.argv[1:]
    if args and args[0] == '--':
        args.pop(0)
    if not args:
        args = ['--version']
    # Gradle state and downloaded distribution are confined to this probe.
    env = dict(os.environ)
    env['GRADLE_USER_HOME'] = str(PROJECT / '.tooling' / 'user-home')
    return subprocess.call([str(binary), '--no-daemon', '-p', str(PROJECT), *args], env=env)


if __name__ == '__main__':
    raise SystemExit(main())
