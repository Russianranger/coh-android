#!/usr/bin/env python3
"""Run offline capture admission and its independent controls; start no server."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent


def source_hashes():
    paths = sorted(p for p in HERE.rglob('*') if p.is_file() and
                   p.suffix in ('.py', '.json', '.c', '.h', '.md') and
                   '__pycache__' not in p.parts and 'evidence' not in p.parts)
    return {p.relative_to(HERE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths}


def run(command, env):
    result = subprocess.run(command, text=True, capture_output=True, timeout=180,
                            cwd=HERE, env=env)
    if result.returncode:
        raise ValueError(result.stdout[-8192:] + result.stderr[-8192:])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture-zip', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    capture = args.capture_zip.resolve(strict=True)
    output = args.output.absolute()
    if output.exists() or output.is_symlink():
        parser.error('Output must be a new path')
    # No input extraction or archive-provided executable/source is used.
    initial = source_hashes()
    if capture.stat().st_size > 4 * 1024 * 1024:
        raise ValueError('Capture exceeds retained archive bound')
    capture_hash = hashlib.sha256(capture.read_bytes()).hexdigest()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
               COH_SNAPSHOT_CAPTURE=str(capture))
    admission = json.loads(run([sys.executable, '-B', str(HERE / 'admit.py'),
                                str(capture)], env).stdout)
    controls = run([sys.executable, '-B', str(HERE / 'test_admit.py'),
                    '--capture-zip', str(capture), '-v'], env)
    if 'Ran 0 tests' in controls.stderr or 'skipped=' in controls.stderr:
        raise ValueError('Incomplete control execution')
    with tempfile.TemporaryDirectory(prefix='coh-admission-controls-') as work:
        independent_receipt = Path(work) / 'independent.json'
        independent = run([sys.executable, '-B',
                           str(HERE / 'reviews/f/test_independent.py'),
                           '--admit', str(HERE / 'admit.py'),
                           '--capture-zip', str(capture),
                           '--receipt', str(independent_receipt)], env)
        independent_result = json.loads(independent_receipt.read_text())
    if (independent_result.get('passed') is not True or
            independent_result.get('source_stable') is not True or
            independent_result.get('tests_run') != 17):
        raise ValueError('Independent controls incomplete')
    if source_hashes() != initial:
        raise ValueError('Source changed during qualification')
    if (capture.stat().st_size > 4 * 1024 * 1024 or
            hashlib.sha256(capture.read_bytes()).hexdigest() != capture_hash):
        raise ValueError('Capture changed during qualification')
    receipt = dict(schema='coh-offline-admission-qualification-v1', passed=True,
                   source_sha256=initial, admission=admission,
                   capture_zip_sha256=capture_hash,
                   controls_stdout=controls.stdout, controls_stderr=controls.stderr,
                   independent_controls=independent_result,
                   independent_stderr=independent.stderr,
                   host_python=sys.version, server_started=False,
                   native_decoder_reexecuted=False, android_built=False,
                   android_executed=False, physical_thor_accepted=False,
                   world_authority=False)
    # Write a complete receipt through an exclusive hard-link publication. A
    # preexisting output (including a symlink) is never replaced, even on races.
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=output.parent,
                                         prefix='.admission-', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(receipt, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(json.dumps(dict(passed=True, output=str(output), world_authority=False)))


if __name__ == '__main__':
    main()
