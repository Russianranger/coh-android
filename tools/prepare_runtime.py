#!/usr/bin/env python3
"""Stage a NEW runtime from pinned text, extracted base assets and a verified build.

Repeat --asset-data for coherent base-asset donors. Generated caches and arbitrary
text from donors are excluded; conflicting binary paths fail before anything is
copied. Does not execute game programs or change the imported snapshots.
"""

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile

from package_reference_runtime import DYNAMIC_DLLS, PRODUCTS, dependency_report, pe_info

ROOT = Path(__file__).resolve().parents[1]
LAUNCHERS = ('client.ps1', 'db.ps1', 'map.ps1', 'templates.ps1',
             'create-bins.ps1', 'start-local.ps1')
ASSET_SUFFIXES = frozenset(('.geo', '.texture', '.ogg', '.wav', '.anim', '.ttf', '.ttc', '.otf'))
METADATA = frozenset(('build-info.json', 'build-info.txt'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def copy_file(source, destination):
    require(not Path(source).is_symlink() and Path(source).is_file(),
            'Not a regular runtime input: ' + str(source))
    return shutil.copy2(source, destination)


def safe_relative(name):
    require(isinstance(name, str) and name and '\\' not in name and ':' not in name,
            'Unsafe runtime path: ' + str(name))
    path = PurePosixPath(name)
    require(not path.is_absolute() and all(p not in ('', '.', '..') for p in name.split('/')),
            'Unsafe runtime path: ' + name)
    return path


def input_files(directory):
    require(directory.is_dir() and not directory.is_symlink(),
            'Input must be a real directory: ' + str(directory))
    for current, directories, files in os.walk(directory, followlinks=False):
        for name in directories + files:
            require(not (Path(current) / name).is_symlink(),
                    'Symlinks are not allowed in runtime inputs: ' + str(Path(current) / name))
        directories.sort()
        for name in sorted(files):
            path = Path(current) / name
            require(path.is_file(), 'Not a regular runtime input: ' + str(path))
            relative = path.relative_to(directory).as_posix()
            safe_relative(relative)
            yield relative, path


def excluded_reason(name):
    parts = safe_relative(name).parts
    lower = name.casefold()
    if any(p.casefold() in ('.git', 'bin', 'geobin', '_devonly', 'markerfiles') for p in parts):
        return 'generated_or_development_directory'
    if lower.endswith(('.bin', '.bin.meta', '.bounds')):
        return 'generated_cache'
    return None


class FilePlan:
    """One unambiguous Windows namespace, also represented consistently on Linux."""
    def __init__(self):
        self.files = {}
        self.directories = {}

    def add(self, name, source, replace=False):
        parts = safe_relative(name).parts
        parent = PurePosixPath()
        for index, part in enumerate(parts[:-1], 1):
            key = '/'.join(parts[:index]).casefold()
            require(key not in self.files, 'File/directory conflict at ' + name)
            if key not in self.directories:
                self.directories[key] = parent / part
            parent = self.directories[key]
        key = name.casefold()
        require(key not in self.directories, 'File/directory conflict at ' + name)
        if key in self.files:
            old_name, old_source = self.files[key]
            if not replace:
                require(sha256(source) == sha256(old_source),
                        'Conflicting case-insensitive runtime path: ' + name)
                return False
            self.files[key] = old_name, source
        else:
            self.files[key] = parent / parts[-1], source
        return True


def asset_plan(donors):
    plan, hashes, reports = FilePlan(), {}, []
    for donor in donors:
        # A failed/in-progress archive inspection cannot become an accepted donor.
        require(not (donor / '.inspection-incomplete').exists(),
                'Asset inspection is incomplete: ' + str(donor))
        excluded, selected, repeated = Counter(), 0, 0
        for name, path in input_files(donor):
            require(path.name.casefold() != '.inspection-incomplete',
                    'Asset inspection is incomplete: ' + str(donor))
            reason = excluded_reason(name)
            if reason is None and path.suffix.casefold() not in ASSET_SUFFIXES:
                reason = 'not_a_binary_asset'
            if reason:
                excluded[reason] += 1
                continue
            digest = sha256(path)
            key = name.casefold()
            require(key not in hashes or hashes[key] == digest,
                    'Conflicting case-insensitive asset path: ' + name + ' in ' + str(donor))
            if plan.add(name, path):
                selected += 1
                hashes[key] = digest
            else:
                repeated += 1
        reports.append({'directory': str(donor.resolve()), 'selected_files': selected,
                        'identical_duplicate_files': repeated, 'excluded_files': dict(excluded)})
    return plan, hashes, reports


def expected_pg_receipt(root, source_lock):
    """Reapply only the touched files in a temporary tree; never patch upstream."""
    patch = (root / 'patches/postgresql/0001-dbserver-postgresql.patch').read_bytes().replace(b'\r\n', b'\n')
    names = [line[6:] for line in patch.decode('utf-8').splitlines() if line.startswith('+++ b/')]
    require(names and len(names) == len(set(names)), 'Unexpected PostgreSQL patch file list')
    with tempfile.TemporaryDirectory(prefix='coh-pg-receipt-') as temporary:
        staging = Path(temporary)
        for name in names:
            safe_relative(name)
            target = staging / name
            target.parent.mkdir(parents=True, exist_ok=True)
            copy_file(root / source_lock['destination'] / name, target)
        env = os.environ.copy()
        for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE'):
            env.pop(key, None)
        env['GIT_CEILING_DIRECTORIES'] = str(staging.parent)
        subprocess.run(['git', '-c', 'core.autocrlf=false', 'apply', '-'],
                       input=patch, cwd=staging, env=env, check=True, capture_output=True)
        patched = {name: sha256(staging / name) for name in names}
    overlays = {name: sha256(path) for name, path in input_files(root / 'database/postgresql/overlay')}
    return {'source_commit': source_lock['commit'], 'patch_sha256': hashlib.sha256(patch).hexdigest(),
            'overlay_sha256': overlays, 'patched_sha256': patched}



def pg_receipt_matches(received, expected, root=ROOT):
    """Accept only proven Git LF/CRLF overlay variants; all other hashes exact.

    Overlay C sources can have platform checkout line endings even though the
    imported immutable source and the normalized patch are identical. Preserve
    their raw receipt hashes for provenance; never waive an overlay mismatch.
    """
    if not isinstance(received, dict) or set(received) != set(expected):
        return False
    if any(received[key] != expected[key] for key in expected if key != 'overlay_sha256'):
        return False
    actual = received.get('overlay_sha256')
    wanted = expected['overlay_sha256']
    if not isinstance(actual, dict) or set(actual) != set(wanted):
        return False
    overlay = root / 'database/postgresql/overlay'
    for name in wanted:
        path = overlay / safe_relative(name)
        if path.is_symlink() or not path.is_file():
            return False
        data = path.read_bytes()
        allowed = {hashlib.sha256(data).hexdigest()}
        # Only explicitly textual C source/header overlay files can vary by EOL.
        if path.suffix.casefold() in ('.c', '.h'):
            try:
                data.decode('utf-8')
            except UnicodeDecodeError:
                return False
            lf = data.replace(b'\r\n', b'\n')
            allowed.update((hashlib.sha256(lf).hexdigest(),
                            hashlib.sha256(lf.replace(b'\n', b'\r\n')).hexdigest()))
        if actual[name] not in allowed:
            return False
    return True


def verify_binaries(directory, root, source_lock):
    info_path = directory / 'build-info.json'
    require(info_path.is_file(),
            'Binaries need build-info.json from the PostgreSQL reference-runtime package; '
            'the older source-only build-info.txt is insufficient. Rebuild/package the pinned PostgreSQL source.')
    files = dict(input_files(directory))
    require(all('/' not in name for name in files), 'Reference-runtime package must have a flat file layout')
    info = json.loads(info_path.read_text(encoding='utf-8'))
    require(info.get('schema_version') == 1, 'Unsupported build-info.json schema')
    require(info.get('source_commit') == source_lock['commit'], 'Binary source commit differs from lock')
    require(re.fullmatch(r'[0-9a-f]{40}', str(info.get('repository_commit', ''))),
            'Missing full repository_commit in build-info.json')
    require(info.get('configuration') == 'OptDebug' and info.get('architecture') == 'Win32',
            'Expected OptDebug / Win32 reference runtime')
    require(info.get('postgresql_persistence_fixture') is False,
            'Reference runtime must have PostgreSQL persistence fixture mode OFF')
    require(pg_receipt_matches(info.get('postgresql_build_input'), expected_pg_receipt(root, source_lock), root),
            'PostgreSQL build receipt differs from the pinned source, patch, overlay or patched files; rebuild the reference package')
    records = info.get('files')
    require(isinstance(records, dict) and records, 'Missing packaged-file hash records')
    folded = set()
    for name, record in records.items():
        safe_relative(name)
        require('/' not in name and name.casefold() not in folded and name not in METADATA,
                'Duplicate, nested or reserved package file: ' + name)
        folded.add(name.casefold())
        path = files.get(name)
        require(path is not None, 'Missing packaged file: ' + name)
        require(isinstance(record, dict) and record.get('size') == path.stat().st_size and
                record.get('sha256') == sha256(path), 'Packaged file size/SHA-256 mismatch: ' + name)
        if path.suffix.casefold() in ('.exe', '.dll'):
            actual = pe_info(path.read_bytes())
            require(all(record.get(key) == value for key, value in actual.items()),
                    'Packaged PE metadata mismatch: ' + name)
    required = set(PRODUCTS + DYNAMIC_DLLS)
    require(required.issubset(records), 'Missing required build outputs: ' + ', '.join(sorted(required - set(records))))
    require(not (set(files) - set(records) - METADATA),
            'Unlisted package files: ' + ', '.join(sorted(set(files) - set(records) - METADATA)))
    deps = dependency_report(records)
    require(not deps['unresolved'], 'Unresolved packaged imports: ' + '; '.join(deps['unresolved']))
    require('postgresql-build-input.json' in records, 'Missing packaged PostgreSQL build receipt')
    require(json.loads(files['postgresql-build-input.json'].read_text()) == info['postgresql_build_input'],
            'Packaged and embedded PostgreSQL receipts differ')
    return info, files, {name: sha256(path) for name, path in files.items()}


def stage(output, asset_data=(), binaries=None, root=ROOT):
    require(not output.exists() and not output.is_symlink(),
            'Output already exists; use a new directory to preserve existing data')
    output = output.resolve()
    require(output != root.resolve() and output != (root / 'upstream').resolve() and
            (root / 'upstream').resolve() not in output.parents,
            'Output must be outside the immutable upstream snapshots')
    for directory in tuple(asset_data) + ((binaries,) if binaries else ()):
        require(directory.is_dir() and not directory.is_symlink(), 'Input is not a real directory: ' + str(directory))
        require(output != directory.resolve() and directory.resolve() not in output.parents,
                'Output must not be inside an input directory')
    source_lock = json.loads((root / 'upstream-lock.json').read_text())
    data_lock = json.loads((root / 'content-lock.json').read_text())
    for lock in ('upstream-lock.json', 'content-lock.json'):
        subprocess.run([sys.executable, str(root / 'tools/verify_source.py'), '--lock', lock],
                       cwd=root, check=True)
    donors, asset_hashes, donor_reports = asset_plan(asset_data)
    package, binary_files, hashes = None, {}, {}
    if binaries:
        package, binary_files, hashes = verify_binaries(binaries, root, source_lock)
    plan, source_exclusions = FilePlan(), Counter()
    for name, path in input_files(root / data_lock['destination'] / 'data'):
        reason = excluded_reason(name)
        if reason:
            source_exclusions[reason] += 1
        else:
            plan.add(name, path)
    # Source DB configuration wins over companion configuration, case-insensitively.
    for name, path in input_files(root / source_lock['destination'] / 'data/server/db'):
        if path.suffix.casefold() == '.cfg':
            plan.add('server/db/' + name, path, replace=True)
    authoritative_skips = 0
    selected_asset_hashes = {}
    for key, (name, path) in donors.files.items():
        if key in plan.files:
            authoritative_skips += 1
            continue
        plan.add(name.as_posix(), path)
        selected_asset_hashes[plan.files[key][0].as_posix()] = asset_hashes[key]
    launchers = {}
    for name in LAUNCHERS:
        path = root / data_lock['destination'] / 'tools' / name
        require(path.is_file() and not path.is_symlink(), 'Missing pinned launcher: ' + name)
        launchers[name] = path.read_text().replace('Game.exe', 'CityOfHeroes.exe')
    # Every foreseeable input error was checked before creating the output.
    output.mkdir(parents=True)
    try:
        (output / '.runtime-staging-incomplete').write_text('Do not execute this incomplete runtime.\n')
        for name, path in plan.files.values():
            target = output / 'data' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            copy_file(path, target)
        for name, digest in selected_asset_hashes.items():
            require(sha256(output / 'data' / name) == digest, 'Asset changed while staging: ' + name)
        (output / 'tools').mkdir()
        for name, text in launchers.items():
            (output / 'tools' / name).write_text(text, encoding='utf-8')
        for name, path in binary_files.items():
            copy_file(path, output / name)
            require(sha256(output / name) == hashes[name], 'Build file changed while staging: ' + name)
        manifest = {
            'status': 'staged_not_gameplay_validated',
            'source_commit': source_lock['commit'], 'data_commit': data_lock['commit'],
            'binary_assets_supplied': bool(asset_data), 'binary_asset_compatibility': 'unverified',
            'asset_donors': donor_reports, 'binary_asset_files': selected_asset_hashes,
            'authoritative_source_collisions_skipped': authoritative_skips,
            'source_generated_files_excluded': dict(source_exclusions),
            'executables_supplied': bool(binaries), 'build_file_sha256': hashes,
            'reference_repository_commit': package['repository_commit'] if package else None,
            'postgresql_build_input': package['postgresql_build_input'] if package else None,
            'templates_and_bins_generated': False, 'database_installed': False,
            'launcher_changes': 'Game.exe -> CityOfHeroes.exe; source-pinned DB configs',
        }
        (output / 'runtime-inputs.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        (output / '.runtime-staging-incomplete').unlink()
    except BaseException:
        shutil.rmtree(output)
        raise
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Must not already exist')
    parser.add_argument('--asset-data', type=Path, action='append', default=[],
                        help='Extracted binary asset data root; repeat for coherent base donors')
    parser.add_argument('--binaries', type=Path,
                        help='Extracted PostgreSQL reference-runtime package including build-info.json')
    args = parser.parse_args()
    try:
        stage(args.output, args.asset_data, args.binaries)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.error(str(exc))
    print('Staged ' + str(args.output.resolve()) + '; database and gameplay still require validation.')


if __name__ == '__main__':
    main()
