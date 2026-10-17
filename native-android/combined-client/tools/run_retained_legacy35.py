#!/usr/bin/env python3
"""Execute the 35 retained original32 v2/v3/v4 metadata witnesses, without rebuilding."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import resource
import struct
import subprocess
import tempfile
import zipfile

BASE = 'native-android/engine/world-render-adapter/qualification/rigid-v234-20261017/'
ARCHIVE_SHA = 'e5a064bacd57dc14de306c2bfbec7ca1b08f268b57d6b73e11ddaea1b670a4ee'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def execute_limits():
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
    resource.setrlimit(resource.RLIMIT_AS, (64 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_NOFILE, (16, 16))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def validate_elf(binary):
    require(len(binary) >= 52 and binary[:6] == b'\x7fELF\x01\x01'
            and struct.unpack_from('<HH', binary, 16) == (2, 3), 'Static i386 EXEC required')
    offset = struct.unpack_from('<I', binary, 28)[0]
    size, count = struct.unpack_from('<HH', binary, 42)
    require(size == 32 and 0 < count <= 32 and offset + size * count <= len(binary), 'ELF program headers')
    for i in range(count):
        fields = struct.unpack_from('<8I', binary, offset + i * size)
        require(fields[0] != 3, 'ELF dynamic interpreter refused')
        if fields[0] == 1:
            require(fields[1] + fields[4] <= len(binary) and fields[4] <= fields[5]
                    and fields[5] <= 64 * 1024 * 1024, 'ELF load segment bounds')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--expected-commit', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    root, output = args.source_root.resolve(), args.output.resolve()
    require(not output.exists() and not output.is_relative_to(root), 'Fresh external output required')
    git = lambda *argv: subprocess.check_output(['git', '--no-replace-objects', '-C', str(root), *argv], timeout=30)
    require(git('rev-parse', 'HEAD').decode().strip() == args.expected_commit, 'Source revision differs')
    require(not git('status', '--porcelain', '--untracked-files=no'), 'Tracked source dirty')
    output.mkdir(parents=True)
    frozen = {}
    proof = {'passed': False, 'source_revision': args.expected_commit,
             'validation_only': args.validate_only, 'cases': [],
             'scope': '35 retained Linux i386 original readModel metadata fixtures; no compiler, Win32 engine, CLIENT state or runtime game session',
             **{key: False for key in ('compiler_executed', 'server_executed', 'android_executed',
                                       'apk_rebuilt', 'material_authority', 'live_world', 'thor_accepted')}}

    def read(relative):
        path = root / relative
        require(not path.is_symlink() and path.resolve().is_relative_to(root), 'Source file ownership')
        raw = path.read_bytes()
        require(raw == git('show', args.expected_commit + ':' + relative), 'Source Git byte mismatch')
        frozen[relative] = sha(raw)
        return raw

    try:
        read(Path(__file__).resolve().relative_to(root).as_posix())
        pins = json.loads(read(BASE + 'all35-original-source-checksums.json'))
        host = json.loads(read(BASE + 'all35-host.json'))
        raw = read(BASE + 'all35-original-source-diagnostics.zip')
        require(host['passed'] is True and len(host['cases']) == 35, 'Qualified case domain')
        require(len(raw) == pins['zip_bytes'] == 615638 and sha(raw) == pins['zip_sha256'] == ARCHIVE_SHA,
                'Exact retained archive identity')
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            items = archive.infolist()
            require(len(items) == len(pins['files']) == 325 and set(archive.namelist()) == set(pins['files'])
                    and sum(item.file_size for item in items) <= 8 * 1024 * 1024, 'Archive member domain')
            for item in items:
                name = PurePosixPath(item.filename)
                require(not name.is_absolute() and '..' not in name.parts and '\\' not in item.filename
                        and len(name.parts) <= 2 and not item.is_dir()
                        and (item.external_attr >> 16) & 0o170000 != 0o120000, 'Archive member path/type')
                require(item.file_size == pins['files'][item.filename]['bytes'] <= 65536,
                        'Archive member bound')
                require(sha(archive.read(item)) == pins['files'][item.filename]['sha256'], 'Archive member SHA')
            require(archive.testzip() is None, 'Archive CRC')
            for index, case in enumerate(host['cases']):
                prefix = str(index) + '/'
                binary = archive.read(prefix + 'original-read-model')
                source = archive.read(prefix + 'original-read-model.c')
                expected = archive.read(prefix + 'expected-facts.bin')
                facts, fixture = case['original_readModel'], case['fixture']
                require(fixture['version'] in (2, 3, 4) and facts['source_layout_passed'] is True
                        and facts['source_version'] == fixture['version'], 'Qualified format fixture')
                require(len(expected) == facts['expected_bytes'] == 220
                        and sha(expected) == facts['expected_facts_sha256'], '55 exact expected words')
                require(sha(binary) == facts['binary_sha256']
                        and sha(source) == facts['generated_oracle_sha256'], 'Exact binary/source binding')
                validate_elf(binary)
                observed = {'index': index, 'version': fixture['version'], 'model': fixture['model'],
                            'row': fixture['disk_row'], 'body_sha256': fixture['sha256'],
                            'binary_sha256': sha(binary), 'oracle_source_sha256': sha(source),
                            'expected_stdout_sha256': sha(expected), 'words': 55,
                            'original32_executed': False, 'facts_equal': False}
                if not args.validate_only:
                    with tempfile.TemporaryDirectory(prefix='coh-legacy35-') as temporary:
                        executable = Path(temporary) / 'original-read-model'
                        executable.write_bytes(binary)
                        executable.chmod(0o500)
                        result = subprocess.run([str(executable)], cwd=temporary, env={}, capture_output=True,
                                                timeout=5, preexec_fn=execute_limits, check=False)
                    (output / ('case-%02d-stdout.bin' % index)).write_bytes(result.stdout)
                    (output / ('case-%02d-stderr.bin' % index)).write_bytes(result.stderr)
                    require(result.returncode == 0 and not result.stderr and result.stdout == expected,
                            'Original32 execution result differs: ' + str(index))
                    observed.update(original32_executed=True, facts_equal=True, stdout_sha256=sha(result.stdout))
                proof['cases'].append(observed)
        require({case['version'] for case in proof['cases']} == {2, 3, 4}, 'All three format versions required')
        require(git('rev-parse', 'HEAD').decode().strip() == args.expected_commit
                and not git('status', '--porcelain', '--untracked-files=no'), 'Source changed')
        require(all(sha((root / path).read_bytes()) == value for path, value in frozen.items()), 'Inputs changed')
        proof.update(passed=True, source_inputs_unchanged=True, source_sha256=frozen, archive_sha256=sha(raw))
    except Exception as error:
        proof['failure'] = type(error).__name__ + ': ' + str(error)
    (output / 'receipt.json').write_text(json.dumps(proof, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'passed': proof['passed'], 'cases': len(proof['cases']),
                      'validation_only': args.validate_only, 'failure': proof.get('failure')}))
    raise SystemExit(0 if proof['passed'] else 1)


if __name__ == '__main__':
    main()
