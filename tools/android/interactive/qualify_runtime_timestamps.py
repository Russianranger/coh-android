#!/usr/bin/env python3
"""Qualify the exact donor's external runtimes with the APK's Java extractor.

Downloads are hash pinned and extraction uses fresh owned roots and a bounded
Java heap. This host gate establishes real archive compatibility and stable
Wine INF dates; it does not claim an Android provider or native runtime boot.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, ROUND_FLOOR, localcontext
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[3]
SCOPE = 'exact_runtime_archives_and_preserved_modification_times'
DONOR = {'bytes': 595203099, 'sha256': '4a507d7d59b3af07be74de4bf47e39b8fd09ac86266a34c4fefd756fb442ee7c'}
LOCK = {'bytes': 1688, 'sha256': '025e9bf55b214be4ff4709ec917ba326648a78feae8e97cd0131b72adca4f760'}
ARCHIVES = {
    'base': {'url': 'https://github.com/Russianranger/lsb-android/releases/download/runtime-probe-v1/runtime-arm64.tar.gz',
             'bytes': 353710639, 'sha256': '08c639c26506dc6fbd15464bec475337087bb23cb7c0c5ace2db5240ee36424f'},
    'wine': {'url': 'https://github.com/Russianranger/lsb-android/releases/download/runtime-fex-v3/runtime-fex-arm64.tar.gz',
             'bytes': 318095727, 'sha256': '030f38066af7b786c142e199cb84adec037840b0f029338849e43f99203a93e1'},
}
EXTRACTOR = 'android/app/src/main/java/io/github/russianranger/cohdiagnostic/TarExtractor.java'
HOST_SOURCES = ('tools/android/java/android/system/Os.java',
                'tools/android/java/io/github/russianranger/cohdiagnostic/ExtractRuntimeHost.java')
SOURCE_FILES = frozenset((EXTRACTOR, *HOST_SOURCES, 'android/runtime-lock.json',
                         'tools/android/interactive/qualify_runtime_timestamps.py'))
HOST_CLASS = 'io.github.russianranger.cohdiagnostic.ExtractRuntimeHost'
JAVA_HEAP_MIB = 128
HEX64 = re.compile(r'[0-9a-f]{64}')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def stream_pin(source):
    digest, size = hashlib.sha256(), 0
    for block in iter(lambda: source.read(1024 * 1024), b''):
        digest.update(block)
        size += len(block)
    return {'bytes': size, 'sha256': digest.hexdigest()}


def file_pin(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'Expected regular qualification input: '+str(path))
    with path.open('rb') as source:
        return stream_pin(source)


def checked_file(path, expected):
    require(file_pin(path) == expected, 'Pinned qualification input differs: '+str(path))


def archive_time(member):
    value = member.pax_headers.get('mtime')
    if value:
        require(len(value) <= 64 and re.fullmatch(r'-?[0-9]+(?:\.[0-9]+)?', value),
                'Unsupported real PAX modification time')
        with localcontext() as context:
            context.prec = 80  # Every admitted decimal remains exact before flooring.
            nanos = int((Decimal(value) * 1000000000).to_integral_value(rounding=ROUND_FLOOR))
    else:
        require(isinstance(member.mtime, int), 'Unexpected real USTAR modification time')
        nanos = member.mtime * 1000000000
    require(0 <= nanos < 2**63, 'Real runtime modification time exceeds extractor range')
    return nanos


def safe_name(name):
    require(isinstance(name, str) and name and not name.startswith('/')
            and '\\' not in name and '\x00' not in name
            and '..' not in PurePosixPath(name).parts, 'Unsafe real archive name')
    return PurePosixPath(name).as_posix()


def no_follow_leaf(root, name):
    path = root
    parts = PurePosixPath(name).parts
    for part in parts[:-1]:
        path /= part
        require(stat.S_ISDIR(path.lstat().st_mode), 'Linked/non-directory extracted ancestor')
    return path / parts[-1] if parts else root


def verify_extracted(archive_path, root):
    """Compare every member without traversing guest absolute symlink targets."""
    records, explicit_dirs, links = {}, {}, {}
    counts = {'regular_files': 0, 'copied_hardlinks': 0, 'symlinks': 0,
              'explicit_directories': 0, 'fractional_timestamps': 0}
    with tarfile.open(archive_path, 'r:gz') as archive:
        members = archive.getmembers()
        require(0 < len(members) <= 400000, 'Unexpected real runtime member count')
        for member in members:
            name = safe_name(member.name)
            timestamp = archive_time(member)
            if timestamp % 1000000000:
                counts['fractional_timestamps'] += 1
            if member.isdir():
                explicit_dirs[name] = timestamp
            elif member.isreg() or member.islnk():
                require(name not in records and name not in links, 'Duplicate real runtime leaf')
                source = archive.extractfile(member)
                require(source is not None, 'Unreadable real runtime payload')
                with source:
                    payload = stream_pin(source)
                # Existing installer normalizes files to executable/nonexecutable
                # app-owned modes. Hard links are independent copies of targets.
                mode = 0o755 if member.mode & 0o111 else 0o644
                if member.islnk():
                    target = archive.getmember(member.linkname)
                    require(target.isreg() or target.islnk(), 'Unexpected real hardlink target')
                    mode = 0o755 if target.mode & 0o111 else 0o644
                records[name] = dict(payload, mtime_ns=timestamp, mode=mode)
                counts['copied_hardlinks' if member.islnk() else 'regular_files'] += 1
            elif member.issym():
                require(name not in records and name not in links, 'Duplicate real runtime link')
                links[name] = member.linkname
                counts['symlinks'] += 1
            else:
                raise ValueError('Unsupported real runtime member type: '+str(member.type))
    for name, record in records.items():
        path = no_follow_leaf(root, name)
        attributes = path.lstat()
        require(stat.S_ISREG(attributes.st_mode) and attributes.st_nlink == 1,
                'Real runtime payload was not an independent regular file: '+name)
        require(file_pin(path) == {key: record[key] for key in ('bytes', 'sha256')},
                'Real runtime payload bytes differ: '+name)
        require(stat.S_IMODE(attributes.st_mode) == record['mode'], 'Real runtime normalized mode differs: '+name)
        require(attributes.st_mtime_ns == record['mtime_ns'], 'Real runtime archive date differs: '+name)
    for name, timestamp in explicit_dirs.items():
        attributes = no_follow_leaf(root, name).lstat()
        require(stat.S_ISDIR(attributes.st_mode) and attributes.st_mtime_ns == timestamp,
                'Real runtime deferred directory date differs: '+name)
    for name, target in links.items():
        path = no_follow_leaf(root, name)
        require(stat.S_ISLNK(path.lstat().st_mode) and os.readlink(path) == target,
                'Real guest symlink target differs: '+name)
    # Account for implicit parent directories, but never follow guest symlinks.
    expected = set(records) | set(links) | set(explicit_dirs)
    for name in tuple(expected):
        expected.update(parent.as_posix() for parent in PurePosixPath(name).parents)
    actual = {'.'}
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            actual.add((Path(directory)/name).relative_to(root).as_posix())
    require(actual == expected, 'Unexpected or absent extracted real runtime leaf')
    counts['explicit_directories'] = len(explicit_dirs)
    tree = {'regular': records, 'directories': explicit_dirs, 'symlinks': links}
    digest = hashlib.sha256(json.dumps(tree, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {'status': 'passed', **counts, 'archive_members': len(members),
            'extracted_entries': len(actual), 'extracted_regular_bytes': sum(record['bytes'] for record in records.values()),
            'verified_tree_sha256': digest, 'payload_bytes_and_normalized_file_modes_verified': True,
            'archive_file_hardlink_and_directory_times_verified': True,
            'symlink_targets_verified_without_following': True}, records


def download_archive(name, work):
    pin = ARCHIVES[name]
    destination = work/(name+'.tar.gz')
    require(not destination.exists() and not destination.is_symlink(), 'Fresh real runtime download required')
    request = urllib.request.Request(pin['url'], headers={'User-Agent': 'COH-runtime-timestamp-qualification/1'})
    with urllib.request.urlopen(request, timeout=120) as source, destination.open('xb') as output:
        total, digest = 0, hashlib.sha256()
        for block in iter(lambda: source.read(1024 * 1024), b''):
            total += len(block)
            require(total <= pin['bytes'], 'Oversized real runtime download')
            output.write(block)
            digest.update(block)
    require({'bytes': total, 'sha256': digest.hexdigest()} == {key: pin[key] for key in ('bytes', 'sha256')},
            'Real runtime download pin differs: '+name)
    return destination


def extract(classes, archive, destination):
    require(not destination.exists() and not destination.is_symlink(), 'Fresh real runtime root required')
    result = subprocess.run(['java', '-Xmx'+str(JAVA_HEAP_MIB)+'m', '-cp', str(classes), HOST_CLASS,
                             str(archive), str(destination)], text=True, capture_output=True, timeout=600)
    require(result.returncode == 0 and 'COH_RUNTIME_EXTRACT_V1 PASS' in result.stdout,
            'Actual Java runtime extraction failed: '+result.stderr[-6000:])


def validate_receipt(receipt, commit):
    require(isinstance(commit, str) and re.fullmatch(r'[0-9a-f]{40}', commit), 'Exact qualification commit required')
    require(isinstance(receipt, dict) and receipt.get('format') == 1 and receipt.get('status') == 'passed'
            and receipt.get('scope') == SCOPE and receipt.get('repository_commit') == commit
            and receipt.get('donor_apk') == DONOR and receipt.get('runtime_lock') == LOCK
            and receipt.get('java_heap_max_mib') == JAVA_HEAP_MIB
            and all(receipt.get(key) is False for key in ('native_runtime_booted', 'physical_gameplay_validated',
                                                        'android_timestamp_provider_validated')),
            'Exact runtime timestamp qualification receipt differs')
    require(set(receipt.get('source_files', {})) == SOURCE_FILES, 'Runtime timestamp source closure differs')
    for name, pin in receipt['source_files'].items():
        checked_file(ROOT/name, pin)
    checked_file(ROOT/'android/runtime-lock.json', LOCK)
    lock = json.loads((ROOT/'android/runtime-lock.json').read_text())
    require({name: {key: lock[name][key] for key in pin} for name, pin in ARCHIVES.items()} == ARCHIVES,
            'Runtime lock/archive compatibility differs')
    require(set(receipt.get('archives', {})) == set(ARCHIVES), 'Real runtime archive closure differs')
    for name, pin in ARCHIVES.items():
        record = receipt['archives'][name]
        require(isinstance(record, dict) and {key: record.get(key) for key in pin} == pin
                and record.get('extraction_status') == 'passed', 'Exact real runtime extraction pin differs')
        tree = record.get('verification', {})
        require(tree.get('status') == 'passed' and type(tree.get('regular_files')) is int
                and tree['regular_files'] > 0 and type(tree.get('extracted_regular_bytes')) is int
                and tree['extracted_regular_bytes'] > 0 and HEX64.fullmatch(str(tree.get('verified_tree_sha256', '')))
                and all(tree.get(key) is True for key in ('payload_bytes_and_normalized_file_modes_verified',
                    'archive_file_hardlink_and_directory_times_verified', 'symlink_targets_verified_without_following')),
                'Real runtime byte/mode/date/link verification missing')
    inf = receipt.get('wine_inf', {})
    require(inf.get('path') == 'share/wine/wine.inf' and type(inf.get('bytes')) is int and inf['bytes'] > 0
            and HEX64.fullmatch(str(inf.get('sha256', ''))) and type(inf.get('archive_mtime_ns')) is int
            and inf['archive_mtime_ns'] >= 0 and inf.get('first_mtime_ns') == inf['archive_mtime_ns']
            and inf.get('second_mtime_ns') == inf['archive_mtime_ns']
            and inf.get('stable_across_fresh_identical_archive_extractions') is True,
            'Identical Wine runtime did not preserve the actual INF date')
    return receipt


def qualify(args):
    require(re.fullmatch(r'[0-9a-f]{40}', args.repository_commit or ''), 'Exact qualification commit required')
    require(not args.work.exists() and not args.work.is_symlink(), 'Fresh owned runtime qualification work required')
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh runtime qualification receipt required')
    checked_file(args.donor_apk, DONOR)
    with zipfile.ZipFile(args.donor_apk) as donor:
        require(len(donor.namelist()) == len(set(donor.namelist())), 'Duplicate exact donor APK member')
        lock_bytes = donor.read('assets/runtime/runtime-lock.json')
    require({'bytes': len(lock_bytes), 'sha256': hashlib.sha256(lock_bytes).hexdigest()} == LOCK,
            'Actual donor runtime lock differs')
    checked_file(ROOT/'android/runtime-lock.json', LOCK)
    pins = {name: file_pin(ROOT/name) for name in sorted(SOURCE_FILES)}
    args.work.mkdir(parents=True)
    classes = args.work/'classes'
    classes.mkdir()
    subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                    '-d', str(classes), str(ROOT/EXTRACTOR), *(str(ROOT/name) for name in HOST_SOURCES)], check=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        downloads = {name: pool.submit(download_archive, name, args.work) for name in ARCHIVES}
        archives = {name: result.result() for name, result in downloads.items()}
    results, payloads = {}, {}
    for name, archive in archives.items():
        destination = args.work/(name+'-first')
        extract(classes, archive, destination)
        verification, records = verify_extracted(archive, destination)
        results[name] = dict(ARCHIVES[name], extraction_status='passed', verification=verification)
        payloads[name] = records
        print('Verified actual '+name+' runtime:', verification['archive_members'], 'members; exact bytes/modes/dates/links', flush=True)
    inf_name = 'share/wine/wine.inf'
    require(inf_name in payloads['wine'], 'Actual Wine INF is absent')
    second = args.work/'wine-second'
    extract(classes, archives['wine'], second)
    original = payloads['wine'][inf_name]
    checked_file(no_follow_leaf(second, inf_name), {key: original[key] for key in ('bytes', 'sha256')})
    inf = {'path': inf_name, **{key: original[key] for key in ('bytes', 'sha256')},
           'archive_mtime_ns': original['mtime_ns'],
           'first_mtime_ns': no_follow_leaf(args.work/'wine-first', inf_name).lstat().st_mtime_ns,
           'second_mtime_ns': no_follow_leaf(second, inf_name).lstat().st_mtime_ns,
           'stable_across_fresh_identical_archive_extractions': True}
    receipt = {'format': 1, 'status': 'passed', 'scope': SCOPE, 'repository_commit': args.repository_commit,
               'donor_apk': DONOR, 'runtime_lock': LOCK, 'source_files': pins, 'archives': results, 'wine_inf': inf,
               'java_heap_max_mib': JAVA_HEAP_MIB, 'native_runtime_booted': False,
               'physical_gameplay_validated': False, 'android_timestamp_provider_validated': False,
               'precision_scope': 'Exact Linux host archive nanoseconds. Android may retain microseconds; Wine checks whole INF seconds.'}
    validate_receipt(receipt, args.repository_commit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2)+'\n')
    print('Qualified exact runtime archives and stable actual Wine INF date', flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--donor-apk', type=Path, required=True)
    parser.add_argument('--repository-commit', required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    for name in ('donor_apk', 'work', 'output'):
        setattr(args, name, getattr(args, name).absolute())
    qualify(args)


if __name__ == '__main__':
    main()
