#!/usr/bin/env python3
"""Package exact standalone suffix controls; never an application or actor permit."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SUFFIX = ROOT / 'native-android/engine/initial-suffix'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def call(args):
    return subprocess.check_output(list(map(str, args)), stderr=subprocess.STDOUT,
                                   text=True, timeout=600)


def load_suffix():
    sys.path.insert(0, str(SUFFIX))
    spec = importlib.util.spec_from_file_location('coh_suffix_check', SUFFIX / 'check.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ndk', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    properties = args.ndk / 'source.properties'
    if 'Pkg.Revision = 28.2.13676358' not in properties.read_text():
        parser.error('qualified NDK r28c required')
    if args.output.exists():
        parser.error('fresh output required')
    args.output.mkdir(parents=True)
    revision = call(['git', '-C', ROOT, 'rev-parse', 'HEAD']).strip()
    call([sys.executable, SUFFIX / 'check.py', '--sanitize', '--output', args.output / 'host.json'])
    host = json.loads((args.output / 'host.json').read_text())
    module = load_suffix()
    sources = [SUFFIX.parent / directory / name
               for directory, names in module.SOURCES.items() for name in names]
    sources.append(SUFFIX / 'test_suffix.c')
    with tempfile.TemporaryDirectory(prefix='coh-suffix-abi-') as work:
        fixture, _ = module.fixture_builder.build(ROOT, ROOT, Path(work))
    fixture_path = args.output / 'fixtures.h'
    fixture_path.write_text(fixture)
    if sha(fixture_path) != host['fixtures_sha256']:
        raise ValueError('regenerated fixtures differ from qualified host')
    inputs = {**host['source_sha256'], **host['provider_sha256']}
    for path in [Path(__file__), HERE / 'run.py', ROOT / 'native-android/engine/entities/run_character_android.py']:
        inputs[path.relative_to(ROOT).as_posix()] = sha(path)
    flags = ['-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic', '-O2',
             '-I' + str(args.output), *sources, '-lm', '-lz']
    builds = {}
    for abi, target, machine in [('arm64-v8a', 'aarch64', 183), ('x86_64', 'x86_64', 62)]:
        compiler = args.ndk / ('toolchains/llvm/prebuilt/linux-x86_64/bin/' + target + '-linux-android26-clang')
        directory = args.output / abi
        directory.mkdir()
        binary = directory / 'coh_initial_suffix_test'
        call([compiler, *flags, '-o', binary])
        receipt = dict(built=True, executed=False, abi=abi, machine=machine,
                       binary_sha256=sha(binary), fixture_sha256=sha(fixture_path),
                       compiler_sha256=sha(compiler.resolve()), api=26,
                       ndk_properties_sha256=sha(properties),
                       linked_android_platform_zlib=True,
                       external_dependency_stack_and_sanitizer_closure=False)
        (directory / 'build.json').write_text(json.dumps(receipt, indent=2) + '\n')
        builds[abi] = receipt
    for name, expected in inputs.items():
        if sha(ROOT / name) != expected:
            raise ValueError('input changed during build')
    if revision != call(['git', '-C', ROOT, 'rev-parse', 'HEAD']).strip():
        raise ValueError('revision changed during build')
    proof = dict(schema='coh-initial-suffix-android-package-v1', passed=True,
                 source_revision=revision, source_sha256=inputs,
                 host_sha256=sha(args.output / 'host.json'),
                 fixture_sha256=sha(fixture_path), builds=builds,
                 actor_publication=False, acknowledgments_enabled=False,
                 android_executed=False, physical_thor=False)
    (args.output / 'package.json').write_text(json.dumps(proof, indent=2) + '\n')


if __name__ == '__main__':
    main()
