#!/usr/bin/env python3
"""Bounded native replay envelope validation and atomic private Java storage."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT / 'native-android/combined-client/app/src/main/java/org/coh/nativecombined/InitialReplayStore.java'
TEST = Path(__file__).with_name('TestInitialReplayStore.java')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=False)
    inputs = [Path(__file__).resolve(), JAVA, TEST]
    pins = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    compile_result = subprocess.run(['java', '-Xmx128m', 'com.sun.tools.javac.Main', '--release', '8', '-Xlint:all', '-Werror', '-d', str(work), str(JAVA), str(TEST)], capture_output=True, text=True)
    (work / 'compile.log').write_text(compile_result.stdout + compile_result.stderr)
    if compile_result.returncode:
        raise RuntimeError('Java replay store compile failed; see ' + str(work / 'compile.log'))
    execution = subprocess.run(['java', '-Xmx64m', '-cp', str(work), 'org.coh.nativecombined.TestInitialReplayStore', str(work)], capture_output=True, text=True, timeout=30)
    (work / 'run.log').write_text(execution.stdout + execution.stderr)
    if execution.returncode:
        raise RuntimeError('Java replay store test failed; see ' + str(work / 'run.log'))
    result = {'passed': True, 'inputs_sha256': pins, 'host': json.loads(execution.stdout), 'scope': 'Java framing/hash/bounds/atomic replacement/symlink/ZIP tests; no device execution or physical packet replay.'}
    assert pins == {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': True, 'host': result['host']}))


if __name__ == '__main__':
    main()
