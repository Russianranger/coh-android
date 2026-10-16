#!/usr/bin/env python3
"""Qualify isolated immutable world/render adapter. No production authority.

Executes unchanged pinned original mulMat44Inline with deterministic inputs.
The source server, GLES driver, real catalog and full-update decoder are NOT
executed by this test. --ndk builds retained standalone API26 ARM64/x86_64 tests;
build receipt execution remains false until an independent Android run exists.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, **kwargs):
    kwargs.setdefault('timeout', 120)
    result = subprocess.run([str(x) for x in command], text=True,
                            capture_output=True, **kwargs)
    if result.returncode:
        raise RuntimeError(f'{command!r}\n{result.stdout}\n{result.stderr}')
    return result.stdout


def original_header(root, target):
    pins = json.loads((HERE / 'source-pins.json').read_text())['sha256']
    for relative, expected in pins.items():
        if sha(root / relative) != expected:
            raise ValueError(f'Original source drift: {relative}')
    text = (root / next(iter(pins))).read_text()
    start = text.index('static INLINEDBG void mulMat44Inline(')
    brace = text.index('{', start)
    end, depth = brace + 1, 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    function = text[start:end]
    target.write_text('#define INLINEDBG\ntypedef float Mat44[4][4];\n' + function + '\n')
    return {'sha256': pins, 'function': 'mulMat44Inline',
            'function_sha256_lf': hashlib.sha256(function.encode()).hexdigest(),
            'unchanged_original_function_executed': True,
            'server_executed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sanitize', action='store_true')
    parser.add_argument('--ndk', type=Path)
    parser.add_argument('--android-output', type=Path)
    args = parser.parse_args()
    if args.source_root.resolve() != ROOT:
        parser.error('--source-root must identify this exact worktree; mixed native/original trees are not admitted')
    revision = run(['git', '-C', ROOT, 'rev-parse', 'HEAD']).strip()
    tree = run(['git', '-C', ROOT, 'rev-parse', 'HEAD^{tree}']).strip()
    dirty_before = run(['git', '-C', ROOT, 'status', '--porcelain', '--untracked-files=no']).strip()
    sources = [HERE / 'coh_world_render.c', HERE / 'tests/test_world_render.c',
               ROOT / 'native-android/engine/renderer/coh_renderer.c']
    pin_files = [HERE / 'coh_world_render.h', *sources, HERE / 'check.py',
                 HERE / 'source-pins.json', ROOT / 'native-android/engine/renderer/coh_renderer.h',
                 ROOT / 'native-android/engine/renderer/coh_renderer_shaders.h',
                 ROOT / 'native-android/engine/coh_contracts.h',
                 ROOT / 'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/mathutil.h']
    untracked_sources = run(['git', '-C', ROOT, 'ls-files', '--others', '--exclude-standard',
                             '--', *pin_files]).strip().splitlines()
    flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic',
             '-ffp-contract=off', '-pthread']
    wrappers = ['-Wl,--wrap=' + name for name in ('calloc', 'malloc', 'realloc', 'free')]
    result = {
        'module': 'world-render-adapter',
        'source_revision': revision, 'source_tree': tree,
        'clean_worktree_before': not bool(dirty_before or untracked_sources),
        'tracked_changes_before': dirty_before.splitlines(),
        'untracked_source_inputs': untracked_sources,
        'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in pin_files},
        'fixture_only': True, 'authentic_server_interoperability': False,
        'physical_thor_accepted': False, 'android_emulator_qualified': False,
        'limits': {'aggregate_owned_and_reserved_bytes': 96 * 1024 * 1024,
                   'draws': 4096, 'vertices_per_draw': 65536,
                   'indices_per_draw': 196608},
        'prerequisites_available': False,
        'scope': 'Immutable CPU adapter/source-matrix/lifecycle contracts only; no real world render',
    }
    with tempfile.TemporaryDirectory(prefix='coh-world-render-') as directory:
        temp = Path(directory)
        result['source_oracle'] = original_header(args.source_root, temp / 'original_matrix.h')
        result['fixtures_sha256'] = {'original_matrix.h': sha(temp / 'original_matrix.h')}
        command = [os.environ.get('CC', 'cc'), *flags, '-I' + str(temp), *sources,
                   '-lm', *wrappers]
        run([*command, '-O2', '-o', temp / 'release'])
        result['host'] = json.loads(run([temp / 'release']))
        if args.sanitize:
            for mode in ('address', 'undefined'):
                executable = temp / mode
                run([*command, '-O1', '-g', '-fno-omit-frame-pointer',
                     '-fsanitize=' + mode, '-no-pie', '-o', executable])
                env = dict(os.environ, ASAN_OPTIONS='detect_leaks=0:abort_on_error=1',
                           UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
                native = json.loads(run([executable], env=env))
                if native != result['host']:
                    raise ValueError('Native result differs across sanitizer modes')
                result[mode] = native
            result['leak_sanitizer'] = {'executed': False,
                'reason': 'LSan /proc task inspection is unavailable in traced executor; ASan remains enabled. Exact budget release/retirement tests passed.'}
        if args.ndk:
            output = (args.android_output or args.output.parent / 'android').resolve()
            output.mkdir(parents=True, exist_ok=True)
            result['android_builds'] = {}
            toolchain = args.ndk / 'toolchains/llvm/prebuilt/linux-x86_64/bin'
            for abi, triple in [('arm64-v8a', 'aarch64-linux-android26'),
                                ('x86_64', 'x86_64-linux-android26')]:
                binary = output / abi / 'world-render-adapter-test'
                binary.parent.mkdir(parents=True, exist_ok=True)
                run([toolchain / (triple + '-clang'), *flags, '-I' + str(temp),
                     *sources, '-lm', *wrappers, '-O2', '-fPIE', '-pie', '-o', binary])
                receipt = {'passed': True, 'abi': abi, 'api': 26, 'executed': False,
                           'binary': binary.name, 'binary_sha256': sha(binary),
                           'source_revision': revision, 'source_tree': tree,
                           'source_sha256': result['source_sha256'],
                           'fixtures_sha256': result['fixtures_sha256'],
                           'expected_native_result': result['host']}
                (binary.parent / 'build.json').write_text(json.dumps(receipt, indent=2) + '\n')
                result['android_builds'][abi] = receipt
        else:
            result['android_builds'] = {'passed': False, 'reason': 'NDK not supplied; no Android build claimed'}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(temp / 'original_matrix.h', args.output.parent / 'original_matrix.h')
    dirty_after = run(['git', '-C', ROOT, 'status', '--porcelain', '--untracked-files=no']).strip()
    result['clean_worktree_after'] = not bool(dirty_after or untracked_sources)
    result['tracked_changes_after'] = dirty_after.splitlines()
    result['source_inputs_unchanged'] = result['source_sha256'] == {
        str(p.relative_to(ROOT)): sha(p) for p in pin_files}
    if not result['source_inputs_unchanged'] or dirty_before != dirty_after:
        raise ValueError('Source changed during qualification')
    result['passed'] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
