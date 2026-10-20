#!/usr/bin/env python3
"""Admit unchanged protected inputs for the bounded reporting-only candidate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
BASELINE = ROOT / 'native-android/integration/three-workstreams-20261019/recovery.json'


def audit(root=ROOT):
    if not __debug__ or os.environ.get('PYTHONOPTIMIZE'):
        raise ValueError('OPTIMIZED_PROTECTED_INPUT_GATE')
    baseline = json.loads(BASELINE.read_bytes())
    expected = baseline['protected_input_sha256']
    assert len(expected) == 9
    actual = {}
    for name, digest in expected.items():
        path = root / name
        assert path.is_file() and not path.is_symlink() and path.resolve() == path
        actual[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual[name] == digest, 'PROTECTED_INPUT_CHANGED: ' + name
    return {'schema': 'coh-report-diagnostic-protected-inputs-v1', 'passed': True,
            'source_revision': subprocess.check_output(['git', '-C', root, 'rev-parse', 'HEAD'], text=True).strip(),
            'baseline_sha256': hashlib.sha256(BASELINE.read_bytes()).hexdigest(),
            'protected_input_sha256': actual, 'memory_policy_changed': False,
            'runtime_import_and_signing_inputs_changed': False, 'world_authority': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    proof = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(proof, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'passed': True, 'protected_inputs': len(proof['protected_input_sha256'])}))


if __name__ == '__main__':
    main()
