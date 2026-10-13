#!/usr/bin/env python3
"""Dormant exact Game/Map archive migration from independently pinned materials.

No network, build, process launch, player database access or cache deletion is
performed. Authorities are frozen in the APK guest contract; absent authorities
stop migration before reading candidate materials. Output is nonshipping.
"""
from __future__ import annotations
import copy
import hashlib
import io
import os
from pathlib import Path
import re
import stat
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'android/guest'), str(ROOT/'tools')]
import native_startup_metadata_contract as contract
from package_reference_runtime import pe_info

APK_PIN = {'bytes': 42076692,
    'sha256': '14d88da1796d155dc1b98e45ac642c7702ff3286e7ef0f2a0772f8e48693b12f'}
ARCHIVES = {'game': 'assets/runtime/client-runtime.zip',
    'mapserver': 'assets/runtime/game-package.tar.gz'}
MAXIMUM_ARCHIVE = 256*1024**2
MAXIMUM_NATIVE_LEAF = 64*1024**2


def content_pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def read_regular(path, maximum=MAXIMUM_ARCHIVE):
    path = Path(path)
    contract.require(path.is_absolute() and not any(part.is_symlink() for part in (path, *path.parents)),
        'Absolute nonlinked native material required')
    before = path.lstat()
    contract.require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= maximum,
        'Bounded regular native material required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        identity = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns)
        contract.require(identity(os.fstat(stream.fileno())) == identity(before), 'Native material changed before opening')
        raw = stream.read(maximum+1)
        contract.require(len(raw) == before.st_size and identity(os.fstat(stream.fileno())) == identity(before)
            and identity(path.lstat()) == identity(before), 'Native material changed while reading')
    return raw


def safe_names(names):
    contract.require(0 < len(names) <= 128 and len(set(names)) == len(names)
        and len({name.casefold() for name in names}) == len(names)
        and all(type(name) is str and re.fullmatch('[A-Za-z0-9_.-]+', name)
            and name not in ('.', '..') for name in names), 'Unsafe/duplicate/aliased native archive names')


def zip_members(raw):
    contract.require(0 < len(raw) <= MAXIMUM_ARCHIVE, 'Bounded native ZIP required')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        rows = archive.infolist(); safe_names([row.filename for row in rows])
        contract.require(all(not row.is_dir() and not row.flag_bits & 1
            and stat.S_IFMT(row.external_attr >> 16) in (0, stat.S_IFREG)
            and 0 < row.file_size <= MAXIMUM_NATIVE_LEAF for row in rows)
            and sum(row.file_size for row in rows) <= MAXIMUM_ARCHIVE,
            'Linked/encrypted/oversized native ZIP member')
        return {row.filename: archive.read(row) for row in rows}, rows


def game_members(raw):
    contract.require(0 < len(raw) <= MAXIMUM_ARCHIVE, 'Bounded native Game tar archive required')
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        rows = archive.getmembers(); safe_names([row.name for row in rows])
        contract.require(all(row.isfile() and not row.issparse() and not row.pax_headers
            and 0 < row.size <= MAXIMUM_NATIVE_LEAF for row in rows)
            and sum(row.size for row in rows) <= MAXIMUM_ARCHIVE,
            'Linked/sparse/extended/oversized native tar member')
        return {row.name: archive.extractfile(row).read() for row in rows}, rows


def authenticated_donor(apk):
    raw = read_regular(Path(apk).absolute())
    contract.require(content_pin(raw) == APK_PIN, 'Exact independently audited .36 public donor required')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        contract.require(len(archive.namelist()) == len(set(archive.namelist())), 'Duplicate donor APK member')
        result = {kind: archive.read(name) for kind, name in ARCHIVES.items()}
    return result


def authenticate_materials(kind, paths):
    """Bind actual whole ZIPs and every member to fixed source/run/artifact pins.

    The authority also names exact required receipt values; those values are
    inspected only after actual bytes match the frozen artifact fingerprints.
    Source-recipe/native fixture validators run in the owning qualification
    lane before these independent authority pins are frozen.
    """
    expected = contract.authority(kind)
    contract.require(set(paths) == set(contract.MATERIAL_ROLES), 'Producer, recovery and qualification materials required')
    material = {}
    for role in contract.MATERIAL_ROLES:
        identity = expected['materials'][role]
        contract.require(type(identity.get('repository_commit')) is str
            and re.fullmatch('[0-9a-f]{40}', identity['repository_commit'])
            and type(identity.get('run_id')) is int and identity['run_id'] > 0
            and type(identity.get('artifact_id')) is int and identity['artifact_id'] > 0,
            'Original material source/job owner required')
        raw = read_regular(Path(paths[role]).absolute())
        contract.require(content_pin(raw) == identity['artifact_zip'], 'Actual '+role+' artifact bytes differ')
        members, _ = zip_members(raw)
        contract.require(set(members) == set(identity['members'])
            and all(content_pin(members[name]) == identity['members'][name] for name in members),
            'Exact authenticated '+role+' artifact member closure required')
        for name, fields in identity.get('required_receipt_values', {}).items():
            receipt = contract.unique_json(members[name])
            for field, value in fields.items():
                contract.require(type(receipt.get(field)) is type(value) and receipt.get(field) == value,
                    'Pinned '+role+' receipt scope/identity differs: '+field)
        material[role] = members
    executable = contract.COMPONENTS[kind]['executable']
    native = material['producer'].get(executable)
    contract.require(type(native) is bytes and content_pin(native)
        == contract.native_record_pin(expected['native_record']),
        'Exact candidate native executable missing from original producer artifact')
    contract.require(pe_info(native) == {key: expected['native_record'][key]
        for key in ('pe_machine', 'imports', 'delay_imports')}, 'Actual candidate native imports/machine differ')
    return expected, native


def wrap_manifest(previous_raw, kind, expected):
    contract.require(content_pin(previous_raw) == contract.COMPONENTS[kind]['base_manifest'],
        'Exact old raw native receipt required')
    previous = contract.unique_json(previous_raw)
    contract.require(contract.encoded(previous) == previous_raw and contract.WRAPPER not in previous,
        'Retained raw receipt order/serialization must be reversible')
    executable = contract.COMPONENTS[kind]['executable']
    result = copy.deepcopy(previous)
    result['files'][executable] = copy.deepcopy(expected['native_record'])
    receipt = {'format': 1, 'role': contract.ROLE, 'kind': kind,
        'previous_manifest': content_pin(previous_raw),
        'previous_native_record': copy.deepcopy(previous['files'][executable]),
        'native_record': copy.deepcopy(expected['native_record']),
        'authority_sha256': contract.canonical_sha(expected),
        'materials': copy.deepcopy(expected['materials']),
        'compatibility': copy.deepcopy(expected['compatibility']),
        'scope': {'shipping_allowed': False, 'runtime_activation_allowed': False,
            'behavioral_collision_validated': False, 'physical_timing_validated': False,
            'old_native_producer_relabelled': False}}
    result[contract.WRAPPER] = {'receipt': receipt, 'receipt_sha256': contract.canonical_sha(receipt)}
    contract.validate_package(result, kind)
    restored, _ = contract.previous_package(result, kind)
    contract.require(contract.encoded(restored) == previous_raw, 'Raw historical receipt restoration differs')
    return contract.encoded(result)


def migrate_archive(previous_raw, kind, native, expected):
    """Replace only one executable and its additive manifest; preserve all else."""
    contract.require(contract.same(expected, contract.authority(kind)), 'Caller cannot provide an arbitrary candidate authority')
    reader = zip_members if kind == 'game' else game_members
    before, rows = reader(previous_raw)
    names = contract.COMPONENTS[kind]
    manifest_name, executable = names['manifest'], names['executable']
    manifest = contract.unique_json(before[manifest_name])
    contract.require(set(before) == set(manifest['files']) | {manifest_name}, 'Exact retained native archive closure required')
    for name, row in manifest['files'].items():
        contract.require(content_pin(before[name]) == {'bytes': row.get('bytes', row.get('size')), 'sha256': row['sha256']},
            'Retained native member differs: '+name)
    contract.require(content_pin(native) == contract.native_record_pin(expected['native_record']),
        'Candidate executable differs from frozen producer')
    contract.require(pe_info(native) == {key: expected['native_record'][key]
        for key in ('pe_machine', 'imports', 'delay_imports')}, 'Actual candidate PE import ABI differs')
    after = dict(before)
    after[executable] = native
    after[manifest_name] = wrap_manifest(before[manifest_name], kind, expected)
    target = io.BytesIO()
    if kind == 'game':
        with zipfile.ZipFile(target, 'w') as archive:
            for row in rows: archive.writestr(copy.copy(row), after[row.filename])
    else:
        import gzip
        with gzip.GzipFile(fileobj=target, mode='wb', mtime=0) as stream:
            with tarfile.open(fileobj=stream, mode='w', format=tarfile.USTAR_FORMAT) as archive:
                for row in rows:
                    info = copy.copy(row); info.size = len(after[row.name])
                    archive.addfile(info, io.BytesIO(after[row.name]))
    raw = target.getvalue()
    checked, _ = reader(raw)
    contract.require(set(checked) == set(before) and checked == after
        and {name for name in checked if checked[name] != before[name]} == {executable, manifest_name},
        'Native archive migration changed a non-admitted member')
    return raw, {'format': 1, 'role': 'nonshipping_exact_native_archive_migration',
        'kind': kind, 'previous_archive': content_pin(previous_raw), 'archive': content_pin(raw),
        'previous_manifest': content_pin(before[manifest_name]),
        'manifest': content_pin(after[manifest_name]), 'native': content_pin(native),
        'unchanged_native_members': len(manifest['files'])-1,
        'authority_sha256': contract.canonical_sha(expected),
        'shipping_allowed': False, 'runtime_activation_allowed': False,
        'physical_timing_validated': False, 'behavioral_collision_validated': False}
