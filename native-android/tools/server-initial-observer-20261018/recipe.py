#!/usr/bin/env python3
"""Stage and admit one new nonshipping original Map initial-send observer.

No entrypoint invokes a compiler, launches a server, deploys a PE or runs an
accepted qualifier. The workflow builds the staged MapServer target separately.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HOOKS = 'native-android/engine/initial-capture/server-initial-observer'
FRESH = 'native-android/engine/scenecatalog-server/fresh_callback_observer'
ROLE = 'nonshipping_same_owner_initial_send_observer'
SCHEMA = 'coh-server-initial-observer-compile-v1'
STAGE_SCHEMA = 'coh-server-initial-observer-stage-v1'
RECEIPT = 'compile-only-receipt.json'
STAGE_RECEIPT = 'native-server-initial-observer-build-input.json'
LIMIT = 16 * 1024 * 1024


def require(ok, code):
    if not ok:
        raise ValueError(code)


def path(value):
    result = Path(os.path.abspath(value))
    require(not any(p.is_symlink() for p in (result, *result.parents)), 'INITIAL_PATH_LINK')
    return result


def read(value, maximum=LIMIT):
    source = path(value)
    before = source.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
            and 0 <= before.st_size <= maximum, 'INITIAL_REGULAR_BOUND')
    with source.open('rb') as stream:
        raw = stream.read(maximum + 1)
    after = source.stat()
    require(len(raw) == before.st_size and len(raw) <= maximum
            and (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), 'INITIAL_READ_CHANGED')
    return raw


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(raw):
    return {'bytes': len(raw), 'sha256': sha(raw)}


def digest(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value), 'INITIAL_DIGEST')
    return value


def revision(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{40}', value), 'INITIAL_REVISION')
    return value


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'INITIAL_JSON_DUPLICATE')
            result[key] = value
        return result
    result = json.loads(raw, object_pairs_hook=pairs,
                        parse_constant=lambda _: require(False, 'INITIAL_JSON_FINITE'))
    require(type(result) is dict, 'INITIAL_JSON_OBJECT')
    return result


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def load(name, filename):
    filename = path(filename)
    existing = sys.modules.get(name)
    if existing is not None:
        require(Path(existing.__file__).resolve() == filename, 'INITIAL_FOREIGN_MODULE')
        return existing
    spec = importlib.util.spec_from_file_location(name, filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        del sys.modules[name]
        raise
    return module


def context(root):
    root = path(root)
    require(HERE == root / 'native-android/tools/server-initial-observer-20261018', 'INITIAL_OWN_CHECKOUT')
    fresh = load('coh_server_initial_fresh_stage', root / FRESH / 'stage.py')
    hooks = load('coh_server_initial_hooks', root / HOOKS / 'sourcehooks.py')
    require(type(hooks.PATCHED) is tuple and 1 <= len(hooks.PATCHED) <= 8
            and len(set(hooks.PATCHED)) == len(hooks.PATCHED), 'INITIAL_HOOK_TUS')
    for name in hooks.PATCHED:
        relative_name(name)
    return root, fresh, hooks


def relative_name(name):
    require(type(name) is str and name and '\\' not in name and ':' not in name, 'INITIAL_MEMBER_NAME')
    relative = Path(name)
    require(not relative.is_absolute() and all(x not in ('', '.', '..') for x in name.split('/')),
            'INITIAL_MEMBER_NAME')
    return name


def git(root, *args):
    return subprocess.run(['git', *args], cwd=root, check=True, capture_output=True).stdout


def checkout_closure(root):
    root, fresh, _ = context(root)
    result = fresh.checkout_closure(root)
    files = [p for p in HERE.iterdir()
             if p.is_file() and p.suffix in ('.py', '.json')]
    files.extend(p for p in (root / HOOKS).iterdir()
                 if p.is_file() and p.suffix in ('.py', '.h', '.c', '.inc', '.json'))
    names = sorted({p.relative_to(root).as_posix() for p in files})
    tree = git(root, 'ls-tree', '-r', '-z', 'HEAD', '--', *names)
    blobs = {}
    for row in tree.split(b'\0'):
        if row:
            meta, name = row.split(b'\t', 1)
            mode, kind, blob = meta.split()
            require(mode in (b'100644', b'100755') and kind == b'blob', 'INITIAL_GIT_MODE')
            blobs[name.decode()] = blob.decode()
    require(set(blobs) == set(names), 'INITIAL_UNTRACKED_SUPPLIER')
    for name in names:
        raw = read(root / name)
        require(hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
                == blobs[name], 'INITIAL_CHANGED_SUPPLIER')
        result[name] = sha(raw)
    return result


def unchanged_checkout(root, closure):
    require(checkout_closure(root) == closure, 'INITIAL_CHECKOUT_CHANGED')


def hook_overlay(root, hooks):
    result = hooks.overlays(root)
    require(type(result) is dict and 1 <= len(result) <= 24, 'INITIAL_OVERLAY_BOUND')
    require(not set(result).intersection(hooks.PATCHED), 'INITIAL_OVERLAY_TU_COLLISION')
    for name, raw in result.items():
        relative_name(name)
        require(type(raw) is bytes and len(raw) <= LIMIT, 'INITIAL_OVERLAY_BYTES')
    return result


def stage_expected(root, prior, originals, output, overlay):
    return {'schema': STAGE_SCHEMA, 'build_role': ROLE, 'build_targets': ['MapServer'],
            'prior_fresh_build_input': prior,
            'prior_fresh_build_input_canonical_sha256': sha(json.dumps(prior, sort_keys=True, separators=(',', ':')).encode()),
            'source_sha256': {n: sha(v) for n, v in originals.items()},
            'patched_sha256': {n: sha(v) for n, v in output.items()},
            'overlay_sha256': {n: sha(v) for n, v in overlay.items()},
            'supplier_sha256': {n: v for n, v in checkout_closure(root).items()
                                if n.startswith(HOOKS + '/') or n.startswith('native-android/tools/server-initial-observer-20261018/')},
            'mechanically_reversible_to_fresh_role': True,
            'original_protocol_state_timing_predicates_preserved': True,
            'runtime_executed': False, 'accepted_observer_equivalence': False,
            'normal_authentication_qualified': False, 'world_authority': False}


def inherited_hook_sources(fresh, getter, originals):
    """Every newly hooked inherited file retains its actual prepared baseline."""
    inherited = fresh.base.inherited_hashes(decode(getter(fresh.old.PRIOR)))
    matched = {}
    for name, raw in originals.items():
        if name in inherited:
            require(sha(raw) == inherited[name], 'INITIAL_HOOK_INHERITED_BASELINE')
            matched[name] = inherited[name]
    return matched


def verify_bytes(root, getter, all_inherited=False):
    root, fresh, hooks = context(root)
    actual = {n: getter(n) for n in hooks.PATCHED}
    original = hooks.reverse(actual)
    require(type(original) is dict and set(original) == set(hooks.PATCHED), 'INITIAL_REVERSE_KEYS')
    output = hooks.transform(original)
    require(type(output) is dict and output == actual, 'INITIAL_HOOK_REVERSAL')
    prior = fresh.verify_bytes(root, lambda n: original[n] if n in original else getter(n),
                               all_inherited=all_inherited)
    inherited_hook_sources(fresh, getter, original)
    overlay = hook_overlay(root, hooks)
    require(all(getter(n) == raw for n, raw in overlay.items()), 'INITIAL_OVERLAY_CHANGED')
    result = stage_expected(root, prior, original, output, overlay)
    require(fresh.base.json_equal(decode(getter(STAGE_RECEIPT)), result), 'INITIAL_STAGE_RECEIPT')
    return result


def verify_stage(source_root, staged):
    root, fresh, _ = context(source_root)
    root, staged = fresh.base.private_stage(root, staged)
    closure = checkout_closure(root)
    result = verify_bytes(root, lambda n: read(staged / n), all_inherited=True)
    unchanged_checkout(root, closure)
    return result


def stage(source_root, staged):
    root, fresh, hooks = context(source_root)
    root, staged = fresh.base.private_stage(root, staged)
    closure = checkout_closure(root)
    prior = fresh.verify_staged(root, staged)
    originals = {n: read(staged / n) for n in hooks.PATCHED}
    output = hooks.transform(originals)
    require(type(output) is dict and set(output) == set(originals)
            and hooks.reverse(output) == originals, 'INITIAL_STAGE_REVERSAL')
    overlay = hook_overlay(root, hooks)
    require(not (staged / STAGE_RECEIPT).exists(), 'INITIAL_STAGE_EXISTS')
    for name in overlay:
        require(not (staged / name).exists(), 'INITIAL_OVERLAY_EXISTS')
    receipt = stage_expected(root, prior, originals, output, overlay)
    created, changed = [], []
    try:
        for name, raw in overlay.items():
            target = path(staged / name)
            require(target.parent.is_dir(), 'INITIAL_OVERLAY_PARENT')
            with target.open('xb') as stream:
                created.append(target)
                stream.write(raw)
        for name, raw in output.items():
            changed.append(name)
            (staged / name).write_bytes(raw)
        unchanged_checkout(root, closure)
        with (staged / STAGE_RECEIPT).open('xb') as stream:
            created.append(staged / STAGE_RECEIPT)
            stream.write(encoded(receipt))
        require(verify_stage(root, staged) == receipt, 'INITIAL_STAGE_VERIFY')
        return receipt
    except BaseException:
        for name in reversed(changed):
            (staged / name).write_bytes(originals[name])
        for target in reversed(created):
            target.unlink()
        raise


def artifact_names(root):
    root, fresh, hooks = context(root)
    sources = set(fresh.PATCHED) | set(fresh.old.overlays(root)) | set(fresh.overlays(root))
    sources |= set(hooks.PATCHED) | set(hook_overlay(root, hooks))
    return {'MapServer.exe', 'CMakeCache.txt', fresh.RECEIPT, fresh.old.RECEIPT,
            fresh.old.PRIOR, 'map-startup-inputs.json', STAGE_RECEIPT,
            *('source/' + n for n in sources)}


def exact_inventory(directory, expected):
    directory = path(directory)
    require(directory.is_dir(), 'INITIAL_ARTIFACT_DIRECTORY')
    files, directories, total = set(), set(), 0
    for current, folders, names in os.walk(directory, followlinks=False):
        for name in folders:
            target = path(Path(current) / name)
            directories.add(target.relative_to(directory).as_posix())
        for name in names:
            target = path(Path(current) / name)
            relative = target.relative_to(directory).as_posix()
            relative_name(relative)
            total += len(read(target))
            require(total <= 64 * 1024 * 1024, 'INITIAL_ARTIFACT_TOTAL_BOUND')
            files.add(relative)
    require(files == expected, 'INITIAL_ARTIFACT_INVENTORY')
    parents = {p.as_posix() for n in expected for p in Path(n).parents if p != Path('.')}
    require(directories == parents, 'INITIAL_ARTIFACT_DIRECTORIES')


def pe_identity(raw):
    require(1024 <= len(raw) <= LIMIT and raw[:2] == b'MZ', 'INITIAL_PE_DOS')
    offset = struct.unpack_from('<I', raw, 60)[0]
    require(64 <= offset <= min(1024 * 1024, len(raw) - 120), 'INITIAL_PE_OFFSET')
    header = raw[offset:offset + 120]
    machine, sections = struct.unpack_from('<HH', header, 4)
    optional_size, flags = struct.unpack_from('<HH', header, 20)
    require(header[:4] == b'PE\0\0' and machine == 0x14c and 0 < sections <= 96
            and optional_size >= 96 and not flags & 0x2000 and flags & 0x0002
            and offset + 24 + optional_size + sections * 40 <= len(raw)
            and struct.unpack_from('<H', header, 24)[0] == 0x10b
            and struct.unpack_from('<I', header, 40)[0] != 0, 'INITIAL_PE32_I386_EXECUTABLE')


def cmake_identity(raw, staged_root):
    require(type(staged_root) is str and re.fullmatch(r'[A-Za-z]:/[^\\\r\n]+', staged_root), 'INITIAL_STAGE_ROOT')
    fields = {}
    for line in raw.decode().splitlines():
        if line and not line.startswith(('#', '//')) and '=' in line:
            key, value = line.split('=', 1)
            require(key not in fields, 'INITIAL_CACHE_DUPLICATE')
            fields[key] = value
    configurations = [(n, v) for n, v in fields.items()
                      if n == 'CMAKE_CONFIGURATION_TYPES' or n.startswith('CMAKE_CONFIGURATION_TYPES:')]
    require(fields.get('CMAKE_GENERATOR:INTERNAL') == 'Visual Studio 18 2026'
            and fields.get('CMAKE_GENERATOR_PLATFORM:INTERNAL') == 'Win32'
            and fields.get('CMAKE_HOME_DIRECTORY:INTERNAL') == staged_root
            and len(configurations) == 1
            and configurations[0][0] in ('CMAKE_CONFIGURATION_TYPES:STRING', 'CMAKE_CONFIGURATION_TYPES:UNINITIALIZED')
            and 'OptDebug' in configurations[0][1].split(';'), 'INITIAL_CACHE_CONFIGURATION')


def verify_artifact(compile_directory, source_root, expected_source_revision, receipt_sha256):
    root, _, _ = context(source_root)
    source = path(compile_directory)
    expected_source_revision = revision(expected_source_revision)
    require(git(root, 'rev-parse', 'HEAD').decode().strip() == expected_source_revision,
            'INITIAL_EXPECTED_CHECKOUT_REVISION')
    digest(receipt_sha256)
    closure = checkout_closure(root)
    names = artifact_names(root)
    exact_inventory(source, names | {RECEIPT})
    raw_receipt = read(source / RECEIPT)
    require(sha(raw_receipt) == receipt_sha256, 'INITIAL_COMPILE_RECEIPT_PIN')
    receipt = decode(raw_receipt)
    fields = {'schema', 'passed', 'build_role', 'source_revision', 'source_git_status_porcelain',
              'compile_only', 'runtime_executed', 'source_stage_verified', 'inherited_source_closure_reverified',
              'external_input_archive_verification_claimed', 'platform', 'pe_machine', 'configuration', 'generator',
              'staged_source_root', 'artifacts', 'source_closure_sha256', 'accepted_observer_equivalence',
              'accepted_qualifiers_reexecuted', 'object_cache_reused', 'normal_authentication_qualified', 'world_authority'}
    require(set(receipt) == fields, 'INITIAL_COMPILE_FIELDS')
    require(receipt['schema'] == SCHEMA and receipt['build_role'] == ROLE
            and receipt['source_revision'] == expected_source_revision
            and receipt['source_git_status_porcelain'] == []
            and receipt['platform'] == 'Win32' and receipt['pe_machine'] == 'i386'
            and receipt['configuration'] == 'OptDebug' and receipt['generator'] == 'Visual Studio 18 2026'
            and all(receipt[n] is True for n in ('passed', 'compile_only', 'source_stage_verified',
                                                'inherited_source_closure_reverified'))
            and all(receipt[n] is False for n in ('runtime_executed', 'external_input_archive_verification_claimed',
                                                'accepted_observer_equivalence', 'accepted_qualifiers_reexecuted',
                                                'object_cache_reused', 'normal_authentication_qualified', 'world_authority')),
            'INITIAL_COMPILE_SCOPE')
    require(receipt['source_closure_sha256'] == closure, 'INITIAL_COMPILE_SOURCE_CLOSURE')
    require(type(receipt['artifacts']) is dict and set(receipt['artifacts']) == names, 'INITIAL_COMPILE_ARTIFACTS')
    for name in names:
        value = receipt['artifacts'][name]
        require(type(value) is dict and set(value) == {'bytes', 'sha256'}
                and type(value['bytes']) is int and 0 <= value['bytes'] <= LIMIT
                and type(value['sha256']) is str and value == pin(read(source / name)),
                'INITIAL_COMPILE_ARTIFACT_HASH')
    pe_identity(read(source / 'MapServer.exe'))
    cmake_identity(read(source / 'CMakeCache.txt'), receipt['staged_source_root'])
    _, fresh, _ = context(root)
    stage_receipt = verify_bytes(root, lambda n: read(source / (n if n in
                                  (STAGE_RECEIPT, fresh.RECEIPT, fresh.old.RECEIPT, fresh.old.PRIOR)
                                  else 'source/' + n)))
    for name in names:
        require(receipt['artifacts'][name] == pin(read(source / name)), 'INITIAL_COMPILE_ARTIFACT_CHANGED')
    require(read(source / RECEIPT) == raw_receipt, 'INITIAL_COMPILE_RECEIPT_CHANGED')
    exact_inventory(source, names | {RECEIPT})
    unchanged_checkout(root, closure)
    require(git(root, 'rev-parse', 'HEAD').decode().strip() == expected_source_revision,
            'INITIAL_CHECKOUT_REVISION_CHANGED')
    return receipt, stage_receipt


def record(source_root, staged, binary, cache, output):
    root, _, _ = context(source_root)
    staged, binary, cache, output = (path(p) for p in (staged, binary, cache, output))
    closure = checkout_closure(root)
    declared = verify_stage(root, staged)
    head = revision(git(root, 'rev-parse', 'HEAD').decode().strip())
    require(git(root, 'status', '--porcelain') == b'', 'INITIAL_SOURCE_DIRTY')
    require(binary == staged / 'out/build/vs2026/bin/OptDebug/MapServer.exe'
            and cache == staged / 'out/build/vs2026/CMakeCache.txt', 'INITIAL_BUILD_PATHS')
    pe_identity(read(binary))
    cmake_identity(read(cache), staged.as_posix())
    require(not output.exists() and output.parent.is_dir(), 'INITIAL_OUTPUT_EXISTS')
    output.mkdir(mode=0o700)
    # Keep partial fixed evidence on refusal. Never replace an earlier receipt.
    artifacts = {}
    for name in sorted(artifact_names(root)):
        original = binary if name == 'MapServer.exe' else cache if name == 'CMakeCache.txt' else staged / name.removeprefix('source/')
        raw = read(original)
        target = path(output / name)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        require(read(target) == raw and read(original) == raw, 'INITIAL_COPY_CHANGED')
        artifacts[name] = pin(raw)
    require(verify_stage(root, staged) == declared, 'INITIAL_STAGE_CHANGED')
    require(git(root, 'rev-parse', 'HEAD').decode().strip() == head
            and git(root, 'status', '--porcelain') == b'', 'INITIAL_SOURCE_CHANGED')
    unchanged_checkout(root, closure)
    receipt = {'schema': SCHEMA, 'passed': True, 'build_role': ROLE, 'source_revision': head,
               'source_git_status_porcelain': [], 'compile_only': True, 'runtime_executed': False,
               'source_stage_verified': True, 'inherited_source_closure_reverified': True,
               'external_input_archive_verification_claimed': False, 'platform': 'Win32', 'pe_machine': 'i386',
               'configuration': 'OptDebug', 'generator': 'Visual Studio 18 2026',
               'staged_source_root': staged.as_posix(), 'artifacts': artifacts, 'source_closure_sha256': closure,
               'accepted_observer_equivalence': False, 'accepted_qualifiers_reexecuted': False,
               'object_cache_reused': False, 'normal_authentication_qualified': False, 'world_authority': False}
    raw = encoded(receipt)
    with (output / RECEIPT).open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    verify_artifact(output, root, head, sha(raw))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('stage', 'verify-stage', 'record', 'verify-artifact'):
        item = sub.add_parser(action)
        item.add_argument('--source-root', type=Path, required=True)
        if action == 'verify-artifact':
            item.add_argument('--compile-directory', type=Path, required=True)
            item.add_argument('--expected-source-revision', required=True)
            item.add_argument('--receipt-sha256', required=True)
        else:
            item.add_argument('--already-staged', type=Path, required=True)
        if action == 'record':
            item.add_argument('--binary', type=Path, required=True)
            item.add_argument('--cmake-cache', type=Path, required=True)
            item.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.action == 'stage':
        value = stage(args.source_root, args.already_staged)
    elif args.action == 'verify-stage':
        value = verify_stage(args.source_root, args.already_staged)
    elif args.action == 'record':
        value = record(args.source_root, args.already_staged, args.binary, args.cmake_cache, args.output)
    else:
        value, _ = verify_artifact(args.compile_directory, args.source_root, args.expected_source_revision, args.receipt_sha256)
    print(json.dumps({'passed': True, 'build_role': ROLE, 'compile_only': True, 'runtime_executed': False,
                      'source_revision': value.get('source_revision'), 'world_authority': False}, sort_keys=True))


if __name__ == '__main__':
    main()
