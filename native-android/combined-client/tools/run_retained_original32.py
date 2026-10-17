#!/usr/bin/env python3
"""Execute only reviewed retained v5/v7 freestanding original32 witnesses."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import struct
import subprocess
import tempfile
import zipfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(test, why):
    if not test:
        raise ValueError(why)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--expected-commit', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--validate-only', action='store_true', help='Admit retained inputs without executing ELF32')
    a = p.parse_args()
    root = a.source_root.resolve()
    out = a.output.resolve()
    require(not out.exists() and not out.is_relative_to(root), 'Fresh external output required')
    git = lambda *args: subprocess.check_output(['git', '--no-replace-objects', '-C', str(root), *args], timeout=30)
    require(git('rev-parse', 'HEAD').decode().strip() == a.expected_commit, 'Source revision differs')
    require(not git('status', '--porcelain', '--untracked-files=no'), 'Tracked source is dirty')
    out.mkdir(parents=True)
    proof = {'source_revision': a.expected_commit, 'passed': False, 'versions': {},
             'validation_only': a.validate_only,
             'scope': 'Two retained freestanding Linux i386 original readModel metadata witnesses only',
             'compiler_executed': False, 'server_executed': False, 'android_executed': False,
             'apk_rebuilt': False, 'material_authority': False, 'live_world': False, 'thor_accepted': False}
    frozen = {}
    def read(path):
        require(not path.is_symlink() and path.resolve().is_relative_to(root), 'Source owner path')
        raw = path.read_bytes()
        rel = path.relative_to(root).as_posix()
        require(raw == git('show', a.expected_commit + ':' + rel), 'Source bytes differ: ' + rel)
        frozen[rel] = digest(raw)
        return raw
    try:
        read(Path(__file__).resolve())
        for version, words in [(7, 52), (5, 55)]:
            base = root / ('native-android/engine/world-render-adapter/qualification/rigid-v%d-20261017' % version)
            stem = 'sealed-original32' if version == 7 else 'original-source'
            checksum_name = 'sealed-original32-checksums.json' if version == 7 else 'original-source-diagnostics-checksums.json'
            pins = json.loads(read(base / checksum_name))
            facts = json.loads(read(base / ('expected-v%d-facts.json' % version)))
            expected = read(base / ('expected-v%d-facts.bin' % version))
            raw = read(base / (stem + '-diagnostics.zip'))
            require(len(raw) == pins['zip_bytes'] and digest(raw) == pins['zip_sha256'], 'ZIP identity')
            require(len(expected) == words * 4 == facts['bytes'] and digest(expected) == facts['sha256'], 'Expected facts identity')
            require(expected == struct.pack('<' + 'I' * words, *facts['expected_u32_le']), 'Expected words differ')
            with tempfile.TemporaryDirectory(prefix='coh-original32-') as directory:
                temp = Path(directory)
                archive = temp / 'witness.zip'
                archive.write_bytes(raw)
                with zipfile.ZipFile(archive) as z:
                    require(len(z.infolist()) == len(pins['files']) <= 16
                            and set(z.namelist()) == set(pins['files'])
                            and sum(i.file_size for i in z.infolist()) <= 512 * 1024, 'ZIP membership/size')
                    require(all(z.getinfo(n).file_size == v['bytes'] <= 65536 for n, v in pins['files'].items()), 'ZIP member bound')
                    require(z.testzip() is None, 'ZIP CRC')
                    for name, item in pins['files'].items():
                        require('/' not in name and '\\' not in name and name not in ('.', '..'), 'Witness member path')
                        body = z.read(name)
                        require(len(body) == item['bytes'] <= 65536 and digest(body) == item['sha256'], 'Witness member identity')
                    binary = z.read('original-read-model')
                    source = z.read('original-read-model.c')
                require(digest(binary) == facts['original_readModel_binary_sha256']
                        and digest(source) == facts['generated_oracle_source_sha256'], 'Oracle binding')
                require(binary[:6] == b'\x7fELF\x01\x01' and struct.unpack_from('<HH', binary, 16) == (2, 3), 'Expected ELF32 i386 EXEC')
                phoff = struct.unpack_from('<I', binary, 28)[0]
                phsize, phcount = struct.unpack_from('<HH', binary, 42)
                require(phsize == 32 and 0 < phcount <= 32 and phoff + phsize * phcount <= len(binary), 'ELF program headers')
                require(all(struct.unpack_from('<I', binary, phoff + i * phsize)[0] != 3 for i in range(phcount)), 'Dynamic interpreter refused')
                if a.validate_only:
                    proof['versions'][str(version)] = {'original32_executed': False, 'retained_inputs_validated': True,
                        'expected_words': words, 'expected_stdout_sha256': digest(expected),
                        'binary_sha256': digest(binary), 'archive_sha256': digest(raw)}
                    continue
                executable = temp / 'original-read-model'
                executable.write_bytes(binary)
                executable.chmod(0o500)
                def limits():
                    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
                    resource.setrlimit(resource.RLIMIT_AS, (64 * 1024 * 1024,) * 2)
                    resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024,) * 2)
                    resource.setrlimit(resource.RLIMIT_NOFILE, (16, 16))
                result = subprocess.run([str(executable)], cwd=temp, env={}, capture_output=True,
                                        timeout=5, preexec_fn=limits, check=False)
                (out / ('v%d-stdout.bin' % version)).write_bytes(result.stdout)
                (out / ('v%d-stderr.bin' % version)).write_bytes(result.stderr)
                require(result.returncode == 0 and not result.stderr and result.stdout == expected, 'Original32 result differs')
                proof['versions'][str(version)] = {'original32_executed': True, 'facts_equal': True,
                    'words': words, 'bytes': len(expected), 'stdout_sha256': digest(result.stdout),
                    'binary_sha256': digest(binary), 'oracle_source_sha256': digest(source),
                    'archive_sha256': digest(raw), 'body_sha256': facts['body_sha256'],
                    'row': facts['row'], 'model': facts['model']}
        require(git('rev-parse', 'HEAD').decode().strip() == a.expected_commit
                and not git('status', '--porcelain', '--untracked-files=no'), 'Source changed during execution')
        for rel, sha in frozen.items():
            require(digest((root / rel).read_bytes()) == sha, 'Qualified input changed: ' + rel)
        proof.update(passed=True, source_inputs_unchanged=True, source_sha256=frozen)
    except Exception as error:
        proof['failure'] = type(error).__name__ + ': ' + str(error)
    (out / 'receipt.json').write_text(json.dumps(proof, indent=2, sort_keys=True) + '\n')
    print(json.dumps(proof))
    if not proof['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
