#!/usr/bin/env python3
"""Probe-only packet-bound extension; retain all original observation policy.

One constant in each authenticated original source changes64→96MiB. Game,
native row/directory limits, Windows ABI, schema and admission remain unchanged.
The probe streams its packet; this raises disk/evidence capacity, not its native
directory-array allocation. No provider, replay or performance authority follows.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re

import package_native_client_metadata_capture as native

ROOT = Path(__file__).resolve().parents[1]
C_SOURCE, PARSER = 'native_client_wfd_probe.c', 'test_native_client_wfd_probe.py'
EXE = 'native-client-wfd-probe.exe'
PROBE = EXE
SDK = 'native-client-wfd-probe-windows-checks.json'
MANIFEST = 'native-client-wfd-probe-bound.json'
ROLE = 'nonshipping_probe_packet_bound_extension'
ORIGINAL_C_SHA = '60a3a4e558702bd8e35dc876a5fc94cf255bc60c4415a43d4facf88b8458af0b'
ORIGINAL_PARSER_SHA = 'eccf7452483b3b89680d442f6d9865f65500d3e95c8e6ce0f0ad49b70c30625a'
OLD_MAX_BYTES, MAX_BYTES = 64 * 1024**2, 96 * 1024**2
MAX_ROWS, MAX_DIRS = 200000, 16384
FINITE_WIRE_MAX_BYTES = MAX_ROWS * 424 + MAX_DIRS * 403 + 563
PAYLOADS = frozenset((C_SOURCE, PARSER, EXE, SDK))
MEMBERS = PAYLOADS | {MANIFEST}
SCOPE = {'Game_recompiled': False, 'Game_replaced': False, 'row_limit_changed': False,
    'directory_limit_changed': False, 'schema_changed': False, 'ABI_changed': False,
    'security_or_cleanup_changed': False, 'provider_copied': False,
    'native_Wine_executed_by_this_package': False, 'native_Game_executed': False,
    'physical_device_executed': False, 'provider_authority': False,
    'native_replay_allowed': False, 'performance_promotion_allowed': False, 'publication_allowed': False}
RETAINED_GAME_ARTIFACT = {'artifact_id': 11866594540,
    'archive_sha256': '5a8baf15df7f92baaecf0e861e5d9ec69128bfdf1e53e4f4304cf6362ef541db',
    'source_commit': '4e3188d7dffd2790bbc73e49f9e3fa55df90f016',
    'Game_bytes': 9484288, 'Game_sha256': '35c55889b6b6ec31336ba17813f3abc1cf082cc37012e0dd4e24064bec43693f',
    'Game_recompiled_by_this_extension': False, 'historical_probe_bytes': 125952,
    'historical_probe_sha256': 'a0abe86b938a13dcc0f1dd53d1707edc9d1427d23841e1e2483132fb17c5ebff'}
KEYS = frozenset(('format', 'role', 'producer_commit', 'run_url', 'original_sources', 'generated_sources',
    'packet_bound_bytes', 'row_bound', 'directory_bound', 'finite_wire_maximum_bytes',
    'source_change', 'schema', 'scope', 'files', 'artifact_members', 'actual_native_SDK_controls', 'retained_Game_artifact'))


def require(value, message):
    if not value:
        raise ValueError(message)


def regular(path, maximum=8 * 1024**2):
    path = Path(path)
    require(not any(p.is_symlink() for p in (path, *path.parents)) and path.is_file()
            and 0 < path.stat().st_size <= maximum, 'Bounded regular input required: ' + str(path))
    current_uid = getattr(os, 'geteuid', lambda: 0)()
    require(path.stat().st_uid == current_uid, 'Current owned input required: ' + str(path))
    return path


def pin(path):
    path = regular(path)
    return {'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def raw_pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def _equal(actual, expected, message):
    require(native.retained.typed_equal(actual, expected), message)


def identity(commit, run_url=None):
    require(type(commit) is str and re.fullmatch(r'[0-9a-f]{40}', commit), 'Exact probe producer commit required')
    if run_url is not None:
        require(type(run_url) is str and re.fullmatch(r'https://github\.com/Russianranger/coh-android/actions/runs/[1-9][0-9]*', run_url),
                'Exact probe Actions producer URL required')


def read(path):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate bound receipt key')
            result[key] = value
        return result
    return json.loads(regular(path).read_text(encoding='utf-8-sig'), object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite bound receipt')))


def generated(repository=ROOT):
    repository = Path(repository)
    c = regular(repository/'tools'/C_SOURCE).read_bytes()
    parser = regular(repository/'tools'/PARSER).read_bytes()
    require(hashlib.sha256(c).hexdigest() == ORIGINAL_C_SHA
            and hashlib.sha256(parser).hexdigest() == ORIGINAL_PARSER_SHA, 'Exact frozen original probe/parser pins required')
    old_c, new_c = b'#define PROBE_MAX_BYTES (64u * 1024u * 1024u)', b'#define PROBE_MAX_BYTES (96u * 1024u * 1024u)'
    old_py, new_py = b'MAX_BYTES, MAX_DIRS, MAX_ROWS = 64*1024**2, 16384, 200000', b'MAX_BYTES, MAX_DIRS, MAX_ROWS = 96*1024**2, 16384, 200000'
    require(c.count(old_c) == parser.count(old_py) == 1 and not c.count(new_c) and not parser.count(new_py),
            'One exact packet-bound constant per source required')
    changed = {C_SOURCE: c.replace(old_c, new_c, 1), PARSER: parser.replace(old_py, new_py, 1)}
    require(changed[C_SOURCE].replace(new_c, old_c, 1) == c and changed[PARSER].replace(new_py, old_py, 1) == parser,
            'Only the two packet constants may change')
    require(FINITE_WIRE_MAX_BYTES < MAX_BYTES and FINITE_WIRE_MAX_BYTES < 92_000_000,
            'Fixed finite native wire bounds must fit the new cap')
    return {'original': {C_SOURCE: raw_pin(c), PARSER: raw_pin(parser)},
            'pins': {name: raw_pin(raw) for name, raw in changed.items()}, 'bytes': changed}


def _fresh_directory(path):
    path = Path(path)
    require(not path.exists() and not path.is_symlink() and not any(p.is_symlink() for p in path.parents),
            'Fresh unlinked output directory required')
    parent = path.parent
    require(parent.is_dir() and parent.stat().st_uid == getattr(os, 'geteuid', lambda: 0)(), 'Owned output parent required')
    path.mkdir(mode=0o700)
    return path


def _exclusive(path, raw):
    require(not path.exists() and not path.is_symlink(), 'Existing output must be preserved')
    with path.open('xb') as stream:
        stream.write(raw)
    path.chmod(0o600)


def prepare(output, repository=ROOT):
    source = generated(repository)
    output = _fresh_directory(output)
    tools = output/'tools'; tools.mkdir(mode=0o700)
    for name, raw in source['bytes'].items():
        _exclusive(tools/name, raw)
    load_contract(tools, repository)
    return {'role': ROLE, 'generated_sources': source['pins'], 'packet_bound_bytes': MAX_BYTES,
            'row_bound': MAX_ROWS, 'directory_bound': MAX_DIRS, **SCOPE}


def load_contract(directory, repository=ROOT):
    """Import only authenticated generated bytes, with no global module reuse."""
    directory = Path(directory)
    source = generated(repository)
    for name, expected in source['pins'].items():
        _equal(pin(directory/name), expected, 'Exact generated source differs: ' + name)
    spec = importlib.util.spec_from_file_location('coh_wfd_bound_' + source['pins'][PARSER]['sha256'], directory/PARSER)
    require(spec is not None and spec.loader is not None, 'Generated parser loader unavailable')
    module = importlib.util.module_from_spec(spec)
    # Execute the already authenticated bytes directly: SourceFileLoader would
    # create __pycache__ inside the exact five-member native artifact directory.
    exec(compile(regular(directory/PARSER).read_bytes(), str(directory/PARSER), 'exec'), module.__dict__)
    for name, expected in source['pins'].items():
        _equal(pin(directory/name), expected, 'Generated source changed during import')
    require(module.MAX_BYTES == MAX_BYTES and module.MAX_ROWS == MAX_ROWS and module.MAX_DIRS == MAX_DIRS
            and module.SOURCE.resolve() == (directory/C_SOURCE).resolve(), 'Isolated generated parser contract differs')
    return module


def probe(path):
    path = regular(path)
    value = native.validate_probe(path)
    require(value['pe_machine'] == 332 and value['imports'] == ['KERNEL32.dll'] and not value['delay_imports'],
            'Probe-only exact PE32/KERNEL32 closure required')
    return value


def sdk_checks(path, exe, contract, source_pin):
    return native.validate_probe_checks(read(path), exe, contract=contract, source_pin=source_pin)


def _facts(source, commit, run_url):
    return {'format': 1, 'role': ROLE, 'producer_commit': commit, 'run_url': run_url,
            'original_sources': source['original'], 'generated_sources': source['pins'],
            'packet_bound_bytes': MAX_BYTES, 'row_bound': MAX_ROWS, 'directory_bound': MAX_DIRS,
            'finite_wire_maximum_bytes': FINITE_WIRE_MAX_BYTES,
            'source_change': 'one_64_to_96_MiB_packet_constant_in_each_exact_original_source',
            'schema': 'unchanged_COHWFD1_160byte_header_320byte_WFD_52byte_BY_HANDLE_TLV', 'scope': dict(SCOPE),
            'retained_Game_artifact': dict(RETAINED_GAME_ARTIFACT)}


def package(source_directory, exe, checks, output, commit, run_url, repository=ROOT):
    identity(commit, run_url)
    source = generated(repository)
    contract = load_contract(source_directory, repository)
    executable = probe(exe)
    controls = sdk_checks(checks, exe, contract, source['pins'][C_SOURCE])
    payload = {C_SOURCE: regular(Path(source_directory)/C_SOURCE).read_bytes(),
               PARSER: regular(Path(source_directory)/PARSER).read_bytes(),
               EXE: regular(exe).read_bytes(), SDK: regular(checks).read_bytes()}
    output = _fresh_directory(output)
    for name, raw in payload.items():
        _exclusive(output/name, raw)
    value = dict(_facts(source, commit, run_url), files={EXE: executable},
                 artifact_members={name: pin(output/name) for name in PAYLOADS}, actual_native_SDK_controls=controls)
    _exclusive(output/MANIFEST, (json.dumps(value, sort_keys=True, indent=2) + '\n').encode())
    return validate(output, commit, repository)


def validate(directory, commit, repository=ROOT):
    directory = Path(directory)
    identity(commit)
    require(directory.is_dir() and not any(p.is_symlink() for p in (directory, *directory.parents))
            and directory.stat().st_uid == getattr(os, 'geteuid', lambda: 0)()
            and {p.name for p in directory.iterdir()} == MEMBERS, 'Exact owned five-member probe-only package required')
    for name in MEMBERS:
        regular(directory/name)
    value = read(directory/MANIFEST)
    require(type(value) is dict and set(value) == KEYS, 'Typed probe-only artifact manifest required')
    identity(commit, value['run_url'])
    source = generated(repository)
    for name, expected in _facts(source, commit, value['run_url']).items():
        _equal(value[name], expected, 'Probe artifact contract differs: ' + name)
    _equal(value['artifact_members'], {name: pin(directory/name) for name in PAYLOADS}, 'Probe artifact bytes differ')
    contract = load_contract(directory, repository)
    executable = probe(directory/EXE)
    _equal(value['files'], {EXE: executable}, 'Actual probe PE record differs')
    controls = sdk_checks(directory/SDK, directory/EXE, contract, source['pins'][C_SOURCE])
    _equal(value['actual_native_SDK_controls'], controls, 'Actual SDK receipt/raw evidence differs')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, default=ROOT)
    commands = parser.add_subparsers(dest='command', required=True)
    command = commands.add_parser('prepare'); command.add_argument('--output', type=Path, required=True)
    command = commands.add_parser('package')
    for name in ('source-directory', 'exe', 'checks', 'output'):
        command.add_argument('--' + name, type=Path, required=True)
    command.add_argument('--producer-commit', required=True); command.add_argument('--run-url', required=True)
    command = commands.add_parser('validate'); command.add_argument('--directory', type=Path, required=True)
    command.add_argument('--producer-commit', required=True)
    args = parser.parse_args()
    if args.command == 'prepare': value = prepare(args.output, args.repository)
    elif args.command == 'package': value = package(args.source_directory, args.exe, args.checks, args.output,
                                                   args.producer_commit, args.run_url, args.repository)
    else: value = validate(args.directory, args.producer_commit, args.repository)
    print(json.dumps({'role': value['role'], 'packet_bound_bytes': MAX_BYTES, 'Game_recompiled': False,
                      'provider_authority': False, 'publication_allowed': False}))


if __name__ == '__main__': main()
