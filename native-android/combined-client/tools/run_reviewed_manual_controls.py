#!/usr/bin/env python3
"""Rehash reviewed tools before running the 15 Windows source controls."""
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import unittest

sys.dont_write_bytecode = True
AUTH = 'native-android/engine/auth-interop/'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def reject_project_bytecode(directory):
    # dont_write_bytecode prevents new caches; it does not prevent importing
    # existing caches. Refuse those before any admitted project source import.
    require(directory.resolve() == directory, 'Project source directory alias')
    for path in directory.rglob('*'):
        require(path.name != '__pycache__' and path.suffix.lower() not in ('.pyc', '.pyo'),
                'Project bytecode/cache present before source import')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--expected-commit', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-driver-qualification-sha256', required=True)
    parser.add_argument('--expected-toolchain-sha256', required=True)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    root, output = args.source_root.resolve(), args.output.resolve()
    git = lambda *argv: subprocess.check_output(['git', '--no-replace-objects', '-C', str(root), *argv], timeout=30)
    require(git('rev-parse', 'HEAD').decode().strip() == args.expected_commit, 'Source revision differs')
    require(not git('status', '--porcelain', '--untracked-files=no'), 'Tracked source dirty')
    require(not output.exists() and not output.is_relative_to(root), 'Fresh external output required')
    output.mkdir(parents=True)
    proof = {'passed': False, 'source_revision': args.expected_commit,
             'validation_only': args.validate_only, 'tests_run': 0,
             'cmake_interpreter_executed': False, 'compiler_executed': False,
             'service_executed': False, 'shipping_runtime_replacement_permit': False}
    frozen = {}

    def read(relative):
        name = PurePosixPath(relative)
        require(not name.is_absolute() and '..' not in name.parts, 'Relative source path required')
        path = root / relative
        require(not path.is_symlink() and path.resolve() == path, 'Source owner differs')
        raw = path.read_bytes()
        require(raw == git('show', args.expected_commit + ':' + relative), 'Source Git bytes differ')
        frozen[relative] = sha(raw)
        return raw

    try:
        read(Path(__file__).resolve().relative_to(root).as_posix())
        qualification_raw = read(AUTH + 'evidence/manual-atlas-compile-driver-20261017/qualification.json')
        require(sha(qualification_raw) == args.expected_driver_qualification_sha256, 'Driver qualification pin')
        qualification = json.loads(qualification_raw)
        require(qualification['passed'] is True and qualification['suites'] == 15
                and qualification['executed_suites'] == 14 and qualification['skips'] == 1,
                'Prior local qualification scope differs')
        for path, digest in qualification['inputs'].items():
            require(sha(read(AUTH + path)) == digest, 'Qualified source pin differs')
        deployment = root / AUTH / 'deployment'
        for path in sorted(deployment.glob('*.py')):
            read(path.relative_to(root).as_posix())
        read(AUTH + 'source_oracle.py')
        lock_path = root / AUTH / 'evidence/windows-tool-inventory-39005570623/reviewed-toolchain-lock.json'
        require(sha(read(lock_path.relative_to(root).as_posix())) == args.expected_toolchain_sha256,
                'Reviewed tool lock pin differs')
        reject_project_bytecode(root / AUTH)
        if not args.validate_only:
            require(os.name == 'nt', 'Actual controls require the reviewed Windows environment')
            sys.path.insert(0, str(deployment))
            import hosted_manual_atlas_compile as driver
            lock = driver.tool_lock(lock_path, args.expected_toolchain_sha256)
            require(Path(shutil.which('cmake') or '').resolve() == Path(lock['tools']['cmake']['path']).resolve(),
                    'CMake on PATH must be the exact rehashed reviewed executable')
            spec = importlib.util.spec_from_file_location('reviewed_manual_compile_controls',
                                                         deployment / 'test_hosted_manual_atlas_compile.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            stream = io.StringIO()
            result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
                unittest.defaultTestLoader.loadTestsFromModule(module))
            (output / 'controls.log').write_text(stream.getvalue())
            proof['tests_run'] = result.testsRun
            require(result.testsRun == 15 and result.wasSuccessful() and not result.skipped,
                    'All 15 source controls, including real CMake parser replay, must pass without skips')
            require(driver.tool_lock(lock_path, args.expected_toolchain_sha256) == lock,
                    'Reviewed tools changed during source controls')
            proof.update(cmake_interpreter_executed=True, exact_tools_rehashed_before_and_after=True)
        reject_project_bytecode(root / AUTH)
        require(git('rev-parse', 'HEAD').decode().strip() == args.expected_commit
                and not git('status', '--porcelain', '--untracked-files=no'), 'Source state changed')
        require(all(sha((root / path).read_bytes()) == digest for path, digest in frozen.items()),
                'Frozen source inputs changed')
        proof.update(passed=True, source_sha256=frozen, source_inputs_unchanged=True,
                     driver_qualification_sha256=sha(qualification_raw),
                     toolchain_lock_sha256=args.expected_toolchain_sha256)
    except Exception as error:
        proof['failure'] = type(error).__name__ + ': ' + str(error)
    (output / 'receipt.json').write_text(json.dumps(proof, indent=2, sort_keys=True) + '\n')
    print(json.dumps({key: proof.get(key) for key in ('passed', 'tests_run', 'validation_only', 'failure')}))
    raise SystemExit(0 if proof['passed'] else 1)


if __name__ == '__main__':
    main()
