#!/usr/bin/env python3
"""Package/stage the ARM64 executable, DLLs, generated bins and ARB shaders.

Imported game data stays in the existing app worktree. This small overlay
has its own directory; no x86 executable, DLL or generated bin is reused.
The outer app runtime manifest pins the ZIP, as for its existing packages.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import struct
import tempfile
import time
import zipfile

ARCHIVE = 'armport-client.zip'
MANIFEST = 'client-package.json'
BINARIES = {'CityOfHeroes.exe', 'libc++.dll', 'libunwind.dll', 'armport-launcher.exe'}
MAX_BYTES = 512 * 1024 * 1024


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def arm64_pe(path):
    with path.open('rb') as stream:
        dos = stream.read(64)
        require(len(dos) == 64 and dos[:2] == b'MZ', 'Missing DOS header: ' + path.name)
        offset = struct.unpack_from('<I', dos, 60)[0]
        require(64 <= offset <= 1024 * 1024, 'PE header offset')
        stream.seek(offset)
        header = stream.read(26)
    require(len(header) == 26 and header[:4] == b'PE\0\0'
            and struct.unpack_from('<H', header, 4)[0] == 0xaa64
            and struct.unpack_from('<H', header, 24)[0] == 0x20b,
            'Expected ARM64 PE32+: ' + path.name)


def allowed(name):
    if name in BINARIES:
        return True
    path = PurePosixPath(name)
    return ((len(path.parts) == 3 and path.parts[:2] == ('data', 'bin')
             and path.suffix.lower() == '.bin') or
            (len(path.parts) == 2 and path.parts[0] == 'armport_cg'
             and path.suffix == '.arb')) and bool(re.fullmatch(r'[A-Za-z0-9_./-]+', name))


def package(client, bins, shaders, launcher, output, client_run, data_run):
    require(not output.exists(), 'Package output already exists')
    require({p.name for p in client.iterdir()} == BINARIES - {'armport-launcher.exe'},
            'Expected the exact ARM64 Release artifact binary closure')
    sources = {p.name: p for p in client.iterdir()}
    sources['armport-launcher.exe'] = launcher
    for binary in sources.values():
        require(binary.is_file() and not binary.is_symlink(), 'Invalid binary')
        arm64_pe(binary)
    for root, prefix, suffix in ((bins, 'data/bin/', '.bin'), (shaders, 'armport_cg/', '.arb')):
        selected = sorted(root.glob('*' + suffix))
        require(selected, 'Missing bins or shaders')
        for source in selected:
            require(source.is_file() and not source.is_symlink(), 'Invalid overlay input')
            sources[prefix + source.name] = source
    require(all(allowed(name) for name in sources), 'Unexpected overlay path')
    require(sum(p.stat().st_size for p in sources.values()) <= MAX_BYTES, 'Overlay too large')
    document = {'format': 1, 'role': 'arm64_graphical_client', 'machine': 'ARM64',
                'client_run_id': client_run, 'data_run_id': data_run,
                'files': {name: {'size': p.stat().st_size, 'sha256': digest(p)}
                          for name, p in sorted(sources.items())}}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED) as archive:
        for name, source in sorted(sources.items()):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())
        archive.writestr(MANIFEST, json.dumps(document, sort_keys=True, indent=2) + '\n')
    return document


def unpack(archive_path, destination):
    require(not destination.exists(), 'Fresh overlay directory required')
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)) and 6 <= len(names) <= 4096, 'Overlay member count')
        require(MANIFEST in names and archive.getinfo(MANIFEST).file_size <= 1024 * 1024,
                'Missing/bounded client package manifest')
        document = json.loads(archive.read(MANIFEST))
        require(document.get('format') == 1 and document.get('role') == 'arm64_graphical_client'
                and document.get('machine') == 'ARM64', 'ARM64 package identity')
        files = document.get('files')
        require(isinstance(files, dict) and BINARIES <= files.keys()
                and set(names) == files.keys() | {MANIFEST}, 'ARM64 package inventory')
        require(all(allowed(name) for name in files), 'Unexpected/unsafe overlay path')
        require(len({name.casefold() for name in files}) == len(files), 'Case-colliding overlay paths')
        require(sum(i.file_size for i in archive.infolist()) <= MAX_BYTES, 'Overlay exceeds size limit')
        destination.mkdir(mode=0o700, parents=True)
        for name, expected in files.items():
            info = archive.getinfo(name)
            require(not info.is_dir() and not info.flag_bits & 1
                    and not stat.S_ISLNK(info.external_attr >> 16), 'Invalid overlay member')
            require(info.file_size == expected['size'], 'Overlay size differs: ' + name)
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open('xb') as output:
                shutil.copyfileobj(source, output)
            require(digest(target) == expected['sha256'], 'Overlay digest differs: ' + name)
        for name in BINARIES:
            arm64_pe(destination / name)
    return document



VALIDATION_RECEIPT = 'armport-data-validation.json'
# Format 2 = one-hop links (final file in the recorded directory). Records of
# any other format or policy, such as format 1 written before that check,
# never skip validation.
VALIDATION_FORMAT, VALIDATION_POLICY = 2, 'one_hop_regular_link_targets'


def identity(path):
    info = os.stat(path)
    return [info.st_dev, info.st_ino, info.st_mtime_ns, info.st_ctime_ns]


def identity_digest(records):
    return hashlib.sha256(json.dumps(records, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def validate_links(source_data, links, tree, receipt):
    """Per-file rules for linked entries, reused while no directory changed.

    Real files, directories and special files are classified by the walk from
    d_type. Linked files need a stat of their target: 212k stats under PRoot
    took 111 s on Thor. A passed full check records the identity (device,
    inode, mtime, ctime) of every source directory and of each directory the
    links point into. Adding, removing, renaming or replacing any entry changes
    its directory's identity, so a later identical record proves the same
    validated entries without visiting them; anything else rechecks all links.
    """
    if receipt is not None and receipt.is_file() and not receipt.is_symlink():
        try:
            saved = json.loads(receipt.read_text())
            if (saved.get('format') == VALIDATION_FORMAT and saved.get('policy') == VALIDATION_POLICY
                    and saved.get('source') == str(source_data)
                    and saved.get('tree') == tree and saved.get('links') == len(links)):
                targets = [[name, *identity(name)] for name in saved['target_directories']]
                if identity_digest(targets) == saved.get('targets'):
                    return {'mode': 'unchanged_directory_receipt', 'links_checked': 0,
                            'target_directories': len(targets)}
        except (OSError, ValueError, KeyError, TypeError):
            pass
    directories = set()
    for path in links:
        try:
            info = os.stat(path)
        except OSError:
            info = None
        mode = info.st_mode if info else 0
        require(not stat.S_ISDIR(mode), 'Linked data directory refused')
        require(stat.S_ISREG(mode), 'Nonregular app data')
        # One hop only (the app worktree links straight to verified imports):
        # the recorded directory must hold the final file, or a later change
        # at the end of a chain would not change any recorded identity.
        target = os.path.join(os.path.dirname(path), os.readlink(path))
        try:
            final = os.lstat(target)
        except OSError:
            final = None
        require(final is not None and stat.S_ISREG(final.st_mode)
                and (final.st_dev, final.st_ino) == (info.st_dev, info.st_ino),
                'Chained data link refused')
        directories.add(os.path.dirname(target))
    names = sorted(directories)
    targets = [[name, *identity(name)] for name in names]
    if receipt is not None:
        pending = receipt.with_name(receipt.name + '.pending')
        pending.write_text(json.dumps({'format': VALIDATION_FORMAT, 'policy': VALIDATION_POLICY,
            'source': str(source_data), 'tree': tree,
            'links': len(links), 'target_directories': names, 'targets': identity_digest(targets)}))
        pending.replace(receipt)
    return {'mode': 'complete_link_check', 'links_checked': len(links), 'target_directories': len(names)}


def merge_links(source_data, target_root, receipt=None):
    """Expose the verified app data under one case-insensitive view, by symlink.

    Wine resolves Windows paths case-insensitively, so case-alias directories
    (Maps/ and maps/) must be merged. Merged directories are real here;
    everything else is a single symlink to its source directory or file. The
    top-level bin/ is excluded: the ARM64 overlay owns it. Copying 8.5 GB per
    launch (0.13.37 on Thor: 419 s) is replaced by a walk of directory names.
    Every descendant passes the per-file rules before any link is published.
    """
    source_data = source_data.resolve()
    # casefold relative directory -> actual relative paths (aliases).
    aliases, total = {}, 0
    conflicts = set()
    tree, links = [], []
    pending = [source_data]
    while pending:
        directory = pending.pop()
        relative = directory.relative_to(source_data)
        tree.append([relative.as_posix(), *identity(directory)])
        with os.scandir(directory) as scan:
            entries = sorted(scan, key=lambda entry: entry.name)
        dirs, files = [], []
        for entry in entries:
            if entry.is_symlink():
                links.append(entry.path)
                files.append(entry.name)
            elif entry.is_dir(follow_symlinks=False):
                if relative == Path('.') and entry.name.casefold() == 'bin':
                    continue
                dirs.append(entry.name)
            else:
                require(entry.is_file(follow_symlinks=False), 'Nonregular app data')
                files.append(entry.name)
        for name in files:
            require(Path(name).suffix.lower() not in ('.exe', '.dll'), 'Executable in game data')
        for name in dirs:
            aliases.setdefault((relative / name).as_posix().casefold(), []).append(relative / name)
            pending.append(directory / name)
        total += len(files)
        names = [name.casefold() for name in files] + [name.casefold() for name in dirs]
        if len(names) != len(set(names)):
            # File case aliases or file/directory clashes: merge here so the
            # per-entry checks below reject them explicitly.
            conflicts.add(relative.as_posix().casefold() if relative != Path('.') else '')
    validation = validate_links(source_data, links, identity_digest(sorted(tree)), receipt)
    conflicts |= {key for key, paths in aliases.items() if len(paths) > 1}
    dirty = {''}
    for key in conflicts:
        if not key:
            continue
        parts = key.split('/')
        for i in range(1, len(parts) + 1):
            dirty.add('/'.join(parts[:i]))
    stats = {'directories': 0, 'file_links': 0, 'merged': 0, 'files': 0}

    def populate(sources, target, key):
        # sources: actual source directories merged into target (a real dir).
        index = {child.name.casefold(): child for child in target.iterdir()}
        children = {}
        for source in sources:
            for child in sorted(source.iterdir(), key=lambda p: p.name):
                ckey = child.name.casefold()
                if not key and ckey == 'bin' and child.is_dir() and not child.is_symlink():
                    continue
                if child.is_dir() and not child.is_symlink():
                    children.setdefault(ckey, []).append(child)
                    continue
                require(child.is_file(), 'Nonregular app data')
                require(child.suffix.lower() not in ('.exe', '.dll'), 'Executable in game data')
                require(ckey not in index and ckey not in children,
                        'Data collides with ARM64 overlay or case alias')
                link = target / child.name
                os.symlink(child, link)
                index[ckey] = link
                stats['file_links'] += 1
        for ckey, dirs in sorted(children.items()):
            child_key = (key + '/' + ckey) if key else ckey
            existing = index.get(ckey)
            if child_key in dirty or existing is not None:
                if existing is None:
                    existing = target / dirs[0].name
                    existing.mkdir()
                    index[ckey] = existing
                require(existing.is_dir() and not existing.is_symlink(),
                        'ARM64 data directory conflicts with existing entry')
                stats['merged'] += 1
                populate(dirs, existing, child_key)
            else:
                require(len(dirs) == 1, 'Unmerged case alias')
                link = target / dirs[0].name
                os.symlink(dirs[0], link, target_is_directory=True)
                index[ckey] = link
                stats['directories'] += 1

    target_root.mkdir(exist_ok=True)
    populate([source_data], target_root, '')
    stats['files'] = total
    stats['validation'] = validation
    return stats


def walk_links(root):
    """Every entry of the real (merged) directories of the view, by d_type.

    Linked directories are not followed: each is one case-unique source
    directory whose names merge_links already checked casefold-unique (any
    alias or file/directory clash makes its parent a merged real directory).
    Following them stat'ed all 173k linked files (about 60 s on Thor).
    """
    pending = [Path(root)]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as scan:
            for entry in scan:
                path = Path(entry.path)
                yield path
                if entry.is_dir(follow_symlinks=False):
                    pending.append(path)

def prepare(archive, source_data, destination):
    """Clone only data, then install ARM64 bins. Binary roots never overlap."""
    started = time.monotonic()
    require(source_data.is_dir() and not source_data.is_symlink(), 'Verified app data required')
    require(not destination.exists(), 'Fresh ARM64 worktree required')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.armport-stage-', dir=destination.parent) as temp:
        pending = Path(temp) / 'client'
        document = unpack(archive, pending)
        count = copied_bytes = 0
        copy_started = time.monotonic()
        linked = merge_links(source_data, pending / 'data', destination.parent / VALIDATION_RECEIPT)
        count, copied_bytes = linked['files'], 0
        entries = [p.relative_to(pending / 'data').as_posix().casefold()
                   for p in walk_links(pending / 'data')]
        require(len(entries) == len(set(entries)), 'Case-equivalent ARM64 data paths')
        copy_seconds = time.monotonic() - copy_started
        (pending / 'tools').mkdir()
        pending.rename(destination)
    return {'machine': 'ARM64', 'archive_sha256': digest(archive),
            'executable_sha256': document['files']['CityOfHeroes.exe']['sha256'],
            'client_run_id': document['client_run_id'], 'data_run_id': document['data_run_id'],
            'shared_data_files': count, 'linked_directories': linked['directories'],
            'linked_file_entries': linked['file_links'], 'merged_directories': linked['merged'],
            'data_copy_seconds': round(copy_seconds, 6),
            'preparation_seconds': round(time.monotonic() - started, 6), 'x86_bins_reused': False,
            'data_materialization': 'case_merged_symlinks', 'data_validation': linked['validation'],
            'data_case_duplicates': 0,
            'work_directory': str(destination)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('client', 'bins', 'shaders', 'launcher', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('client-run', 'data-run'):
        parser.add_argument('--' + name, type=int, required=True)
    parser.add_argument('--source-data', type=Path)
    parser.add_argument('--stage', type=Path)
    args = vars(parser.parse_args())
    source_data, stage = args.pop('source_data'), args.pop('stage')
    require(bool(source_data) == bool(stage), '--source-data and --stage must be used together')
    document = package(**args)
    result = {'files': len(document['files']), 'machine': document['machine']}
    if stage:
        result['staged'] = prepare(args['output'], source_data, stage)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
