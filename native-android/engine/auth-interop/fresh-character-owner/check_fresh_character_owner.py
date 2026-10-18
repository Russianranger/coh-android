#!/usr/bin/env python3
"""NEW owner-only doubles or real-public-controller synthetic wire qualification."""
import argparse
import gzip
import hashlib
import importlib.abc
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PRIMITIVE_COMMIT = '6b7fac8e80e375b7a1435fec2743d873580a8955'
PRIMITIVE_SOURCE = 'c684178120693c19b255713ca62b595d2113a3b4'
PRIMITIVE_PATH = 'native-android/engine/dbclient/qualification/empty-creation-c68417812.json.gz'
PRIMITIVE_GZIP_SHA = 'c81fadfa75f60bb9fe458dfce542a8d8db05b2ee61a23914af1963e5a9f98948'
PRIMITIVE_RAW_SHA = 'b642ae53cb0f162aaca2e77b7035cc28b7503180869b067d19b52ee521c5f182'

def need(ok, reason):
    if not ok:
        raise ValueError(reason)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args])

def main():
    need(__debug__ and not os.environ.get('PYTHONOPTIMIZE'), 'optimized Python refused')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scope', choices=('doubles', 'wire'), required=True)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    root = args.source_root.resolve(strict=True)
    native = root / 'native-android'
    need(HERE == native / 'engine/auth-interop/fresh-character-owner', 'canonical checker checkout')
    output = args.output.absolute()
    need(not output.exists() and not output.is_symlink() and root not in output.parents and
         output != root and output.parent.resolve() == output.parent, 'fresh external output required')
    revision = git(root, 'rev-parse', 'HEAD').decode().strip()
    project = [HERE / 'fresh_character_owner.c']
    if args.scope == 'wire':
        project += [native / 'engine' / name for name in (
            'login/coh_login.c', 'auth/coh_auth.c', 'auth/coh_auth_openssl.c',
            'session/coh_session_crypto.c', 'dbclient/coh_db_session.c',
            'dbclient/coh_dbclient.c', 'dbclient/coh_db_account_controls.c',
            'network/coh_net.c', 'network/coh_net_frame.c', 'network/coh_net_udp.c',
            'network/coh_net_zip.c')]
        project += [native / 'protocol/coh_protocol.c', native / 'src/coh_blowfish.c']
    test = HERE / ('test_fresh_character_owner.c' if args.scope == 'doubles' else 'test_fresh_character_wire.c')
    files = set(project + [test, Path(__file__).resolve(), HERE / 'fresh_character_owner.h',
        HERE / 'OWNER-PLAN.md', native / 'engine/coh_contracts.h', native / 'src/byte_reader.h',
        native / 'protocol/coh_protocol.h'])
    for directory in ('auth', 'login', 'dbclient', 'network', 'session'):
        files.update((native / 'engine' / directory).glob('*.h'))
    files.update((native / 'include').glob('*.h'))
    if args.scope == 'wire':
        files.update([HERE / 'fresh_character_wire_oracle.py', native / 'engine/dbclient/check.py',
                      native / 'engine/dbclient/source-pins.json', native / 'tools/protocol_fixture/prepare.py'])
        pins = json.loads((native / 'engine/dbclient/source-pins.json').read_bytes())['sha256_lf']
        files.update(root / 'upstream/ouroboros' / name for name in pins)
    # The prior primitive qualifier is admitted as fixed historical data. Its
    # suite, oracle, compiler and entrypoint are NEVER invoked by this checker.
    packed = git(root, 'show', PRIMITIVE_COMMIT + ':' + PRIMITIVE_PATH)
    need(len(packed) == 8667 and sha(packed) == PRIMITIVE_GZIP_SHA, 'fixed primitive proof bytes')
    raw = gzip.decompress(packed)
    need(len(raw) == 37873 and sha(raw) == PRIMITIVE_RAW_SHA, 'fixed primitive proof raw bytes')
    primitive = json.loads(raw)
    need(primitive['schema'] == 'coh-db-empty-creation-focused-tests-v1' and
         primitive['passed'] is True and primitive['source_revision'] == PRIMITIVE_SOURCE and
         len(primitive['source_sha256']) == 84 and set(primitive['modes']) == {'release', 'asan', 'ubsan'},
         'fixed primitive proof schema')
    for name, digest in primitive['source_sha256'].items():
        need(sha(git(root, 'show', PRIMITIVE_SOURCE + ':' + name)) == digest,
             'primitive historical Git binding')
    for name in ('coh_db_session.c', 'coh_db_session.h'):
        path = native / 'engine/dbclient' / name
        need(sha(path.read_bytes()) == primitive['source_sha256'][str(path.relative_to(root))],
             'new primitive current core differs')
        files.add(path)
    frozen = {}
    for path in files:
        need(path.is_file() and not path.is_symlink() and path.resolve() == path, 'canonical source input')
        frozen[path] = path.read_bytes()
    def committed():
        need(git(root, 'rev-parse', 'HEAD').decode().strip() == revision, 'HEAD changed')
        for path, data in frozen.items():
            need(path.read_bytes() == data and git(root, 'show', revision + ':' + str(path.relative_to(root))) == data,
                 'untracked or changed source input')
    committed()
    output.mkdir(mode=0o700)
    serial = 0
    commands = []
    def run(argv, **kwargs):
        nonlocal serial
        serial += 1
        p = subprocess.run(list(map(str, argv)), capture_output=True, timeout=120, **kwargs)
        stem = str(serial).zfill(3)
        (output / (stem + '-stdout')).write_bytes(p.stdout)
        (output / (stem + '-stderr')).write_bytes(p.stderr)
        commands.append({'argv': list(map(str, argv)), 'returncode': p.returncode,
                         'stdout': stem + '-stdout', 'stdout_sha256': sha(p.stdout),
                         'stderr': stem + '-stderr', 'stderr_sha256': sha(p.stderr)})
        need(p.returncode == 0, 'new focused command failed; retained ' + stem)
        return p.stdout.decode()
    fixture = None
    fixture_raw = None
    fixture_proof = None
    loaded = []
    if args.scope == 'wire':
        directory = output / 'fixture'
        directory.mkdir(mode=0o700)
        original_spec = importlib.util.spec_from_file_location
        class Loader(importlib.abc.Loader):
            def __init__(self, path): self.path = path
            def create_module(self, spec): return None
            def exec_module(self, module):
                committed()
                need(self.path in frozen and self.path.suffix == '.py', 'unadmitted project import')
                module.__file__ = str(self.path)
                module.__cached__ = None
                exec(compile(frozen[self.path], str(self.path), 'exec', dont_inherit=True), module.__dict__)
                loaded.append(str(self.path.relative_to(root)))
                committed()
        def spec(name, path, *a, **kw):
            path = Path(path).resolve()
            return original_spec(name, path, loader=Loader(path)) if path.is_relative_to(root) else original_spec(name, path, *a, **kw)
        importlib.util.spec_from_file_location = spec
        try:
            module_spec = spec('fresh_character_new_wire_oracle', HERE / 'fresh_character_wire_oracle.py')
            helper = importlib.util.module_from_spec(module_spec)
            module_spec.loader.exec_module(helper)
            fixture_proof = helper.produce(root, directory)
        finally:
            importlib.util.spec_from_file_location = original_spec
        fixture = directory / 'fresh-character-wire-fixtures.h'
        fixture_raw = fixture.read_bytes()
    flags = ['-std=c99', '-pedantic', '-Wall', '-Wextra', '-Werror', '-fstack-usage', '-I' + str(native / 'include')]
    if fixture:
        flags += ['-I' + str(fixture.parent)]
    dependencies = set()
    for source in [*project, test]:
        words = run(['cc', *flags, '-MM', source]).replace('\\\n', ' ').split(':', 1)[1]
        for word in shlex.split(words):
            path = Path(word).resolve()
            need(path in frozen or path == fixture, 'unadmitted compiler project dependency')
            dependencies.add(path)
    modes = [('release', ['-O2'])]
    if args.sanitize:
        modes += [('asan', ['-O1', '-g', '-fsanitize=address', '-fno-omit-frame-pointer', '-no-pie']),
                  ('ubsan', ['-O1', '-g', '-fsanitize=undefined', '-fno-sanitize-recover=all'])]
    results = {}
    binaries = {}
    env = dict(os.environ, ASAN_OPTIONS='detect_leaks=0:halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    for mode, options in modes:
        committed()
        if fixture:
            need(fixture.read_bytes() == fixture_raw, 'fixture changed')
        objects = []
        for i, source in enumerate(project):
            target = output / (mode + '-' + str(i) + '.o')
            accepted = ['-O0'] if source.name in ('coh_auth.c', 'coh_protocol.c', 'coh_blowfish.c') else []
            run(['cc', *flags, *options, *accepted, '-c', source, '-o', target])
            objects.append(target)
        exe = output / ('fresh-character-' + args.scope + '-' + mode)
        link = ['-Wl,--wrap=calloc,--wrap=free'] if args.scope == 'doubles' else ['-lcrypto', '-lz', '-lm']
        run(['cc', *flags, *options, test, *objects, *link, '-o', exe])
        binary = exe.read_bytes()
        result = json.loads(run([exe], env=env))
        need(result['passed'] is True and exe.read_bytes() == binary, 'new focused run or binary identity')
        if fixture:
            need(fixture.read_bytes() == fixture_raw, 'fixture mutated')
        committed()
        results[mode] = result
        binaries[mode] = {'file': exe.name, 'bytes': len(binary), 'sha256': sha(binary)}
    need(all(result == results['release'] for result in results.values()), 'cross-mode result mismatch')
    committed()
    proof = {'schema': 'coh-fresh-character-owner-focused-tests-v1', 'passed': True,
        'scope': args.scope, 'source_revision': revision,
        'source_sha256': {str(path.relative_to(root)): sha(data) for path, data in sorted(frozen.items())},
        'all_current_inputs_equal_committed_HEAD': True,
        'compiler_dependency_sha256': {str(p.relative_to(root)): sha(frozen[p]) for p in sorted(dependencies) if p in frozen},
        'project_compilation_inputs': len(project) + 1, 'loaded_frozen_helpers': loaded,
        'primitive_proof': {'commit': PRIMITIVE_COMMIT, 'path': PRIMITIVE_PATH,
            'gzip_sha256': sha(packed), 'raw_sha256': sha(raw), 'historical_source_inputs': 84,
            'current_two_core_bytes_equal_qualified': True, 'old_entrypoints_executed': False},
        'original_writer_fixture': fixture_proof, 'modes': results, 'binaries': binaries,
        'commands': commands, 'compiler': run(['cc', '--version']).splitlines()[0],
        'owner_stack_usage': [line for p in sorted(output.glob('*.su')) for line in p.read_text().splitlines() if 'fresh_character_owner.c:' in line],
        'actual_server_Auth_DB_Map_SQL': False, 'actual_windows_or_android': False,
        'old_Auth_list_C50_primitive_suite_or_main_executed': False,
        'persistent_rollback_observed': False, 'normal_version_or_reference_checksum_admitted': False,
        'world_or_ACK_authority': False, 'leak_sanitizer_enabled': False}
    data = (json.dumps(proof, indent=2) + '\n').encode()
    with (output / 'proof.json').open('xb') as stream:
        stream.write(data)
    committed()
    print(json.dumps({'passed': True, 'scope': args.scope, 'source_inputs': len(frozen),
                      'proof_bytes': len(data), 'proof_sha256': sha(data), 'modes': results}))

if __name__ == '__main__':
    main()
