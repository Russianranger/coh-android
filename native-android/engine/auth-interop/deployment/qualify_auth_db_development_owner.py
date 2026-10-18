#!/usr/bin/env python3
"""Focused source-bound synthetic Auth/DB owner controls; no network or server."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess

PREFIX = 'native-android/engine/auth-interop/deployment/'
OWNER = PREFIX + 'windows/auth_db_development_owner.c'
TEST = PREFIX + 'windows/test_auth_db_development_owner.c'
SELF = PREFIX + 'qualify_auth_db_development_owner.py'
DOC = PREFIX + 'windows/AUTH-DB-DEVELOPMENT-OWNER.md'
REAL_SOURCES = [OWNER, *['native-android/' + p for p in (
    'engine/login/coh_login.c', 'engine/dbclient/coh_db_session.c',
    'engine/dbclient/coh_dbclient.c', 'engine/auth/coh_auth.c',
    'engine/auth/coh_auth_openssl.c', 'engine/session/coh_session_crypto.c',
    'engine/network/coh_net.c', 'engine/network/coh_net_frame.c',
    'engine/network/coh_net_udp.c', 'engine/network/coh_net_zip.c',
    'protocol/coh_protocol.c', 'src/coh_blowfish.c')]]
ORIGINAL = ['upstream/ouroboros/' + p for p in (
    'DBServer/src/clientcomm.c', 'DBServer/src/authcomm.c',
    'Common/comm_backend.h', 'Common/ClientLogin/clientcommLogin.c',
    'Game/src/clientcomm/authclient.c')]

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def run(command, *, cwd=None, env=None, timeout=60):
    result = subprocess.run([str(v) for v in command], cwd=cwd, env=env,
                            capture_output=True, timeout=timeout)
    if len(result.stdout) > 262144 or len(result.stderr) > 262144:
        raise ValueError('bounded_child_output_required')
    if result.returncode:
        raise RuntimeError('focused_command_failed\n' +
                           result.stdout.decode(errors='replace') +
                           result.stderr.decode(errors='replace'))
    return result.stdout

def committed(root, frozen, revision):
    if run(['git', 'rev-parse', 'HEAD'], cwd=root).decode().strip() != revision:
        raise ValueError('source_revision_changed')
    for name, digest in frozen.items():
        if sha((root / name).read_bytes()) != digest:
            raise ValueError('source_bytes_changed:' + name)
        if sha(run(['git', 'show', revision + ':' + name], cwd=root)) != digest:
            raise ValueError('source_not_exact_committed_blob:' + name)

def dependencies(root, cc, flags, sources):
    paths = set(sources)
    for name in sources:
        raw = run([cc, *flags, '-MM', root / name], cwd=root).decode()
        text = raw.replace('\\\n', ' ')
        if ':' not in text:
            raise ValueError('dependency_target_missing')
        for item in shlex.split(text.split(':', 1)[1]):
            p = Path(item)
            if not p.is_absolute():
                p = root / p
            paths.add(p.resolve().relative_to(root).as_posix())
    return sorted(paths)

def main():
    if not __debug__:
        raise SystemExit('optimized_python_refused')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True,
                        help='Fresh output directory; existing path is refused')
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    root = args.source_root.resolve()
    own = Path(__file__).resolve()
    if own != root / SELF:
        raise ValueError('helper_source_root_mismatch')
    initial_helper = sha(own.read_bytes())
    revision = run(['git', 'rev-parse', 'HEAD'], cwd=root).decode().strip()
    if sha(run(['git', 'show', revision + ':' + SELF], cwd=root)) != initial_helper:
        raise ValueError('helper_not_exact_committed_blob')
    output = args.output.resolve()
    if output.exists():
        raise ValueError('fresh_output_required')
    cc = shutil.which('cc')
    if not cc:
        raise ValueError('host_C_compiler_required')
    flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic',
             '-ffp-contract=off', '-I' + str(root / 'native-android/include')]
    paths = dependencies(root, cc, flags, REAL_SOURCES + [TEST])
    paths = sorted(set(paths + ORIGINAL + [SELF, DOC]))
    frozen = {name: sha((root / name).read_bytes()) for name in paths}
    if frozen[SELF] != initial_helper:
        raise ValueError('helper_changed_during_admission')
    committed(root, frozen, revision)
    output.mkdir(parents=True)
    snapshot = output / 'frozen-source'
    for name, digest in frozen.items():
        raw = (root / name).read_bytes()
        if sha(raw) != digest:
            raise ValueError('source_changed_during_copy:' + name)
        target = snapshot / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    compile_flags = flags[:-1] + ['-I' + str(snapshot / 'native-android/include')]
    modes = [('release', ['-O2'])]
    if args.sanitize:
        modes += [('asan', ['-O1', '-g', '-fsanitize=address',
                            '-fno-omit-frame-pointer', '-fno-pie', '-no-pie']),
                  ('ubsan', ['-O1', '-g', '-fsanitize=undefined',
                             '-fno-omit-frame-pointer', '-fno-pie', '-no-pie'])]
    results = {}
    environment = dict(os.environ, ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',
                       UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    for name, extra in modes:
        executable = output / ('owner-controls-' + name)
        run([cc, *compile_flags, *extra, snapshot / TEST, '-o', executable], cwd=snapshot)
        native = json.loads(run([executable], cwd=output, env=environment))
        if native.get('passed') is not True or native.get('live_allocations') != 0:
            raise ValueError('native_control_failure')
        if native.get('synthetic_api_controls_only') is not True or any(
                native.get(key) is not False for key in
                ('network_executed', 'crypto_executed', 'actual_auth_db_verified')):
            raise ValueError('native_scope_failure')
        results[name] = {'native': native, 'binary_sha256': sha(executable.read_bytes())}
    # Compile and link the ACTUAL unchanged native controllers/provider/network,
    # then do not execute them. This is a symbol/header closure, not another old
    # qualifier, wire replay, crypto run or real account login.
    objects = []
    for index, source in enumerate(REAL_SOURCES):
        obj = output / ('native-' + str(index) + '.o')
        extra = ['-O2']
        if source.endswith(('protocol/coh_protocol.c', 'src/coh_blowfish.c')):
            extra = ['-O0']  # Existing accepted kernel's GCC inline warning.
        run([cc, *compile_flags, *extra, '-fstack-usage', '-c', snapshot / source, '-o', obj], cwd=snapshot)
        objects.append(obj)
    link_only = output / 'native-link-only'
    # No generated test behavior is inserted into a production translation unit.
    main_source = output / 'link-only-main.c'
    main_source.write_text('int main(void) { return 0; }\n')
    run([cc, main_source, *objects, '-lcrypto', '-lz', '-lm', '-o', link_only], cwd=root)
    stack = []
    for path in sorted(output.glob('*.su')):
        for row in path.read_text().splitlines():
            cells = row.split('\t')
            if len(cells) != 3:
                raise ValueError('unrecognized_stack_usage_row')
            stack.append({'function': cells[0], 'bytes': int(cells[1]), 'kind': cells[2]})
    committed(root, frozen, revision)
    for name, digest in frozen.items():
        if sha((snapshot / name).read_bytes()) != digest:
            raise ValueError('frozen_build_source_changed:' + name)
    if sha(own.read_bytes()) != initial_helper:
        raise ValueError('helper_changed_before_publication')
    proof = {
        'schema': 'coh-auth-db-development-owner-host-v1', 'passed': True,
        'source_revision': revision, 'source_sha256': frozen,
        'compiled_from_exact_frozen_source_copies': True,
        'tests': results, 'native_link_only_source_count': len(REAL_SOURCES),
        'native_link_only_binary_sha256': sha(link_only.read_bytes()),
        'native_link_only_executed': False,
        'compiler': run([cc, '--version']).decode().splitlines()[0],
        'compiler_stack_usage': stack,
        'stack_scope': 'Per-function compiler estimates; no whole-callstack or global budget admission.',
        'allocation_scope': 'New owner and synthetic controller doubles only; all3 allocation failures and zero-before-free checked.',
        'transitive_real_controller_allocations_executed': False,
        'leak_sanitizer': 'disabled; explicit bounded allocation accounting for synthetic controls',
        'runtime_profile': 'Nonshipping original development skip requested; actual server predicate unobserved.',
        'ordinary_source_modified': False, 'network_executed': False,
        'real_crypto_executed': False, 'actual_auth_db_verified': False,
        'normal_version_admitted': False, 'checksum_reference_admitted': False,
        'character_selected': False, 'map_handoff_verified': False,
        'current_world_verified': False,
    }
    (output / 'qualification.json').write_text(json.dumps(proof, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'passed': True, 'source_revision': revision,
                      'source_pins': len(frozen), 'tests': results}, sort_keys=True))

if __name__ == '__main__':
    main()
