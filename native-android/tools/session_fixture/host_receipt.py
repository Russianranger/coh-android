#!/usr/bin/env python3
"""Retain started/qualified source stages without interpreting partial work as pass."""
import argparse
import hashlib
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('native-android/results/session-client'))
    parser.add_argument('--status', choices=['started', 'completed'], required=True)
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    proofs = []
    if args.status == 'completed':
        for name in ['host-motion-proof.json', 'host-locomotion-proof.json', 'host-character-proof.json']:
            raw = (args.output / name).read_bytes(); value = json.loads(raw)
            assert value['passed'] is True, name
            proofs.append({'file': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
        prepared = json.loads((args.output / 'session-fixture.json').read_text())
        assert prepared['passed'] is True and prepared['runtime_motion_scripted_by_fixture'] is False
    receipt = {'schema': 1, 'gates': [16, 17, 18], 'stage': 'authored assets and source host qualification',
               'status': args.status, 'passed': args.status == 'completed',
               'source_commit': os.environ.get('GITHUB_SHA', 'local-uncommitted'),
               'workflow_run_id': os.environ.get('GITHUB_RUN_ID', 'local'), 'proofs': proofs,
               'full_client_execution_verified': False, 'thor_device_execution_verified': False}
    (args.output / 'source-validation-stage.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
