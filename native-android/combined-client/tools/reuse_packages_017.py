#!/usr/bin/env python3
"""Reuse exact 0.1.7 packages and Android peers for driver-only qualification."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import re
import stat
import subprocess
import zipfile
from prepare import safe_zip, pin, verify

SOURCE = 'fe037348c9a184d98aff96f0803b2afc0e631b71'
SOURCE_TREE = '93390b9fb6f765e4b864669eac66995e56c1f955'
WORKFLOW = '38836479975'
ARTIFACT = '12018934207'
ARCHIVE_SHA = '18057b8aa24df3457cc4fc6c547abc8c66a3d8973fd3bc44c6fbe87ac1d44970'
APKS = {
    'arm64-v8a': ('CoH-Native-Combined-0.1.7-arm64.apk',
        '58c45d44501373309788d70e2483786e412d9b0593e86ba1bae94140a8147475'),
    'x86_64': ('CoH-Native-Combined-0.1.7-emulator-x86_64.apk',
        '9ff5c3393477f71175729b6f9e4e3bae1c8860b4e63a9f4436cefe570ec6165f'),
}
MAIN_WORKFLOW = '.github/workflows/native-combined-client.yml'
OLD_CONDITION = "    if: github.ref == 'refs/heads/native-android' && !contains(github.event.head_commit.message, '[combined-requalify]')"
NEW_CONDITION = OLD_CONDITION + " && !contains(github.event.head_commit.message, '[combined-017-requalify]')"
ALLOWED = {
    'native-android/combined-client/tools/emulator_check.py',
    'native-android/combined-client/tools/driver_controls.py',
    'native-android/combined-client/tools/reuse_packages_017.py',
    'native-android/combined-client/tools/reuse_packages_017_controls.py',
    MAIN_WORKFLOW,
    '.github/workflows/native-combined-requalify-017.yml',
    'native-android/combined-client/README.md',
    'native-android/combined-client/THOR-TEST.md',
    'native-android/combined-client/QUALIFICATION.md',
    'native-android/README.md',
}
EVIDENCE_PREFIX = 'native-android/combined-client/evidence/'
HASH = re.compile(r'^[0-9a-f]{64}$')
SIGNER = '9aec9a8635d33dabd676748c3287e035e00d676546b4da18469dd48eecf5c522'


def git_bytes(root, *args):
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True)
    if result.returncode:
        raise ValueError('Git source closure command failed: ' + repr(args))
    return result.stdout


def git(root, *args):
    return git_bytes(root, *args).decode().strip()


def permitted(path):
    return path in ALLOWED or path.startswith(EVIDENCE_PREFIX)


def source_blob(root, path):
    p = PurePosixPath(path)
    if p.is_absolute() or '..' in p.parts or '\\' in path or str(p) != path:
        raise ValueError('Unsafe receipt source path')
    return git_bytes(root, 'show', SOURCE + ':' + path)


def validate_source(root, require_clean):
    """Pin all tracked production/build blobs, including sparse source trees."""
    git(root, 'merge-base', '--is-ancestor', SOURCE, 'HEAD')
    if git(root, 'rev-parse', SOURCE + '^{tree}') != SOURCE_TREE:
        raise ValueError('Qualified source tree differs')
    changed = git_bytes(root, 'diff', '--name-only', '--no-renames', '-z', SOURCE, 'HEAD')
    changed = [v.decode() for v in changed.split(b'\0') if v]
    dirty_paths = git_bytes(root, 'diff', 'HEAD', '--name-only', '--no-renames', '-z')
    dirty_paths = [v.decode() for v in dirty_paths.split(b'\0') if v]
    untracked = git_bytes(root, 'ls-files', '--others', '--exclude-standard', '-z')
    untracked = [v.decode() for v in untracked.split(b'\0') if v]
    rejected = [v for v in [*changed, *dirty_paths, *untracked] if not permitted(v)]
    if rejected:
        raise ValueError('Qualified production/build source changed: ' + repr(sorted(set(rejected))))
    baseline = source_blob(root, MAIN_WORKFLOW)
    current = root / MAIN_WORKFLOW
    if current.is_symlink() or not current.is_file():
        raise ValueError('Main workflow is not a regular file')
    body = current.read_bytes()
    if body != baseline:
        old = OLD_CONDITION.encode()
        if baseline.count(old) != 1 or body != baseline.replace(old, NEW_CONDITION.encode(), 1):
            raise ValueError('Only the exact 0.1.7 continuation condition may change in the main workflow')
    # Filtering both immutable trees pins every production and build path, not
    # just a sample of CMake/Gradle files. Sparse files need not be hydrated.
    closures = []
    for revision in (SOURCE, 'HEAD'):
        records = git_bytes(root, 'ls-tree', '-r', '-z', revision).split(b'\0')
        kept = [v for v in records if v and not permitted(v.split(b'\t', 1)[1].decode())]
        closures.append((len(kept), hashlib.sha256(b'\0'.join(kept) + b'\0').hexdigest()))
    if closures[0] != closures[1]:
        raise ValueError('Whole production/build tree closure differs')
    dirty = bool(git_bytes(root, 'status', '--porcelain', '--untracked-files=all').strip())
    if require_clean and dirty:
        raise ValueError('Qualification source is modified or has untracked files')
    return dict(driver_source=git(root, 'rev-parse', 'HEAD'), driver_source_clean=not dirty,
        changed_paths_since_qualified_apk=changed,
        qualified_source_tree=SOURCE_TREE,
        unchanged_production_build_paths=closures[0][0],
        unchanged_production_build_manifest_sha256=closures[0][1])


def validate_zip(z):
    safe_zip(z)
    canonical = set()
    total = 0
    if len(z.infolist()) > 128:
        raise ValueError('Too many package archive entries')
    files = set()
    for info in z.infolist():
        path = PurePosixPath(info.filename)
        name = info.filename.rstrip('/')
        if not name or str(path) != name or ':' in path.parts[0] or name in canonical:
            raise ValueError('Noncanonical or conflicting package archive path')
        canonical.add(name)
        mode = info.external_attr >> 16
        if stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
            raise ValueError('Nonregular package archive entry')
        if not info.is_dir():
            files.add(name)
        total += info.file_size
        if info.file_size > 32 << 20 or total > 128 << 20:
            raise ValueError('Qualified package artifact exceeds bounds')
    for name in canonical:
        if any(str(parent) in files for parent in PurePosixPath(name).parents):
            raise ValueError('Package file conflicts with a parent directory')


def json_file(root, name):
    return json.loads((root / name).read_text())


def check_hash(data, digest, label):
    if not isinstance(digest, str) or not HASH.fullmatch(digest) or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError('Qualified pin differs: ' + label)


def check_elf(path, abi, digest, length=None):
    verify(path, digest, length)
    data = path.read_bytes()
    if len(data) < 20 or data[:6] != b'\x7fELF\x02\x01' or int.from_bytes(data[18:20], 'little') != (183 if abi == 'arm64-v8a' else 62):
        raise ValueError('Qualified executable is not the expected ELF64 ABI')
    return dict(file=path.name, **pin(data))


def check_source_hashes(root, values, prefix='', normalized=False):
    if not isinstance(values, dict) or not values:
        raise ValueError('Missing archived source pins')
    for relative, digest in values.items():
        raw = source_blob(root, prefix + relative)
        if normalized:
            raw = raw.replace(b'\r\n', b'\n')
        check_hash(raw, digest, prefix + relative)
    return len(values)


def validate_payload(output, root):
    packages = {}
    for abi, (name, digest) in APKS.items():
        apk = output / name
        verify(apk, digest)
        receipt_name = 'arm64-package.json' if abi == 'arm64-v8a' else 'x86_64-package.json'
        receipt = json_file(output, receipt_name)
        expected = {'name': name, **pin(apk.read_bytes())}
        if (receipt.get('status') != 'passed' or receipt.get('abi') != abi
                or receipt.get('source_commit') != SOURCE or receipt.get('tracked_source_clean') is not True
                or receipt.get('apk') != expected or receipt.get('package') != 'org.coh.nativecombined'
                or receipt.get('version_code') != '8' or receipt.get('version_name') != '0.1.7-local-server-native'
                or receipt.get('signer_certificate_sha256') != SIGNER):
            raise ValueError('Package receipt is not the exact qualified identity/source/binary')
        with zipfile.ZipFile(apk) as z:
            validate_zip(z)
            actual = {i.filename for i in z.infolist() if i.filename.startswith('lib/') and not i.is_dir()}
            libraries = receipt.get('native_libraries')
            if not isinstance(libraries, dict) or set(libraries) != actual:
                raise ValueError('Package native ELF inventory differs')
            for path, value in libraries.items():
                if pin(z.read(path)) != value:
                    raise ValueError('Qualified native ELF changed')
        packages[abi] = dict(apk=expected, build_receipt=receipt_name,
            build_receipt_sha256=pin((output / receipt_name).read_bytes())['sha256'])
    local = json_file(output, 'host/local-protocol.json')
    maps = json_file(output, 'host/map-protocol.json')
    structure = json_file(output, 'host/scene-structure.json')
    if not all(v.get('passed') is True for v in (local, maps, structure)):
        raise ValueError('Archived protocol/structure qualification did not pass')
    source_pins = check_source_hashes(root, local['implementation_sha256'], 'native-android/')
    source_pins += check_source_hashes(root, local['source_sha256_lf'], normalized=True)
    source_pins += check_source_hashes(root, maps['implementation_sha256'], 'native-android/')
    local_android = json_file(output, 'host/local-android/android-build.json')
    if local_android['artifacts'] != local['android']['artifacts'] or local_android['scripted_ui_peer_artifacts'] != local['android']['scripted_ui_peer_artifacts']:
        raise ValueError('Android local protocol and UI peer receipts differ')
    executables = {}
    for key, stem in [('artifacts', 'coh-local-'), ('scripted_ui_peer_artifacts', 'coh-local-peer-')]:
        entries = local_android[key]
        if len(entries) != 2 or {v['abi'] for v in entries} != set(APKS):
            raise ValueError('Missing Android local protocol/UI peer ABI')
        for entry in entries:
            abi = entry['abi']
            if entry['file'] != stem + abi or entry['built'] is not True or entry['executed'] is not False:
                raise ValueError('Android local executable provenance differs')
            path = output / 'host/local-android' / entry['file']
            executables[str(path.relative_to(output))] = check_elf(path, abi, entry['sha256'])
    map_android = json_file(output, 'host/map-android/android-build.json')
    if map_android.get('passed') is not True or map_android['executables'] != maps['android_executables']:
        raise ValueError('Android Map executable receipt differs')
    source_pins += check_source_hashes(root, map_android['source_files_sha256'], 'native-android/')
    if set(map_android['executables']) != set(APKS):
        raise ValueError('Missing Android Map ABI')
    for abi, entry in map_android['executables'].items():
        path = abi + '/test_mapclient_android'
        if entry['file'] != path or entry['executed'] is not False:
            raise ValueError('Android Map executable path/provenance differs')
        per_abi = json_file(output, 'host/map-android/' + abi + '/receipt.json')
        if (per_abi.get('passed') is not True or per_abi['abi'] != abi
                or per_abi['binary'] != 'test_mapclient_android'
                or per_abi['binary_sha256'] != entry['sha256'] or per_abi['bytes'] != entry['bytes']
                or per_abi['source_fixtures_sha256'] != map_android['fixtures_sha256']):
            raise ValueError('Android Map per-ABI receipt differs')
        executable = output / 'host/map-android' / path
        executables[str(executable.relative_to(output))] = check_elf(executable, abi, entry['sha256'], entry['bytes'])
    headers = {
        'fixtures.h': map_android['fixtures_sha256'],
        'groups-fixtures.h': map_android['groups_fixtures_sha256'],
        'server-command-fixtures.h': maps['server_command_fixtures_sha256'],
        'source-oracle.c': map_android['source_oracle_sha256'],
    }
    for name, digest in headers.items():
        check_hash((output / 'host/map-android' / name).read_bytes(), digest, name)
    if (headers['fixtures.h'] != maps['android_fixtures_sha256']
            or headers['groups-fixtures.h'] != local['groups_fixtures_sha256']
            or headers['groups-fixtures.h'] != maps['groups_fixtures_sha256']
            or headers['server-command-fixtures.h'] != local['server_command_fixtures_sha256']):
        raise ValueError('Protocol/UI peer generated-header pins differ')
    source_header = source_blob(root, 'native-android/engine/replication/coh_groups.h')
    check_hash(source_header, map_android['groups_decoder_header_sha256'], 'coh_groups.h')
    for oracle in (local['groups_producer_oracle'], maps['groups_producer_oracle'], structure['source_oracle']):
        if oracle != local['groups_producer_oracle'] or oracle.get('passed') is not True:
            raise ValueError('Protocol/UI peer GROUPS source-oracle provenance differs')
        check_hash(source_blob(root, 'native-android/engine/replication/groups-source-pins.json'),
            oracle['source_pin_sha256'], 'GROUPS source pins')
    return dict(packages=packages, android_executables=executables,
        checked_source_pin_entries=source_pins, generated_fixture_pins=headers)


def admit(archive, output, root, require_clean=False):
    verify(archive, ARCHIVE_SHA)
    source = validate_source(root, require_clean)
    if output.exists():
        raise ValueError('Preserve existing qualification output; choose a fresh directory')
    # Validate the complete directory before the first write. Exact archive
    # bytes plus safe_zip prevent traversal, duplicates, symlinks and zip bombs.
    with zipfile.ZipFile(archive) as z:
        validate_zip(z)
        output.mkdir(parents=True)
        for info in z.infolist():
            if info.is_dir():
                continue
            path = output / info.filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(z.read(info))
    payload = validate_payload(output, root)
    value = dict(format=1, status='passed', qualified_apk_source=SOURCE,
        qualified_workflow=WORKFLOW, artifact_id=ARTIFACT, archive_sha256=ARCHIVE_SHA,
        **source, **payload, rebuilt=False, actual_server_interoperability_verified=False,
        source_closure_boundary='Every tracked production/build blob is unchanged; only exact driver/helper/test, documentation/evidence and continuation workflow paths are admitted.',
        scope='Exact archived ARM64/x86 APKs, native ELF libraries, Android local protocol/UI peer/Map binaries and source/header pins reused for framework-driver continuation only.')
    (output / 'package-reuse-proof.json').write_text(json.dumps(value, indent=2) + '\n')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument('--require-clean', action='store_true')
    args = parser.parse_args()
    value = admit(args.archive, args.output, args.source_root.resolve(), args.require_clean)
    print(json.dumps({key: value[key] for key in ['status', 'rebuilt', 'qualified_apk_source', 'driver_source']}))


if __name__ == '__main__':
    main()
