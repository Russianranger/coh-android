#!/usr/bin/env python3
"""Focused Python controls using an actual retained Huge rig/APK source."""
from pathlib import Path
import argparse
import hashlib
import json
import tempfile
import recover_huge_rig as original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--rig', type=Path)
    inputs.add_argument('--apk', type=Path)
    args = parser.parse_args()
    raw = original.read_rig(args.apk or args.rig, args.apk is not None)
    bodies = original.recover(raw)
    assert len(bodies['base.anim']) == 6171 and len(bodies['motion.anim']) == 5331
    controls = 1
    for offset in (0, 12, 16, 20, 24, 28, 32, 36, 44, 60, 128, len(raw) - 1 - 12):
        bad = bytearray(raw)
        bad[offset] ^= 0x40
        try:
            original.recover(bad)
            raise AssertionError('Corrupt rig accepted at ' + str(offset))
        except ValueError:
            controls += 1
    for size in (0, 127, len(raw) - 1):
        try:
            original.recover(raw[:size])
            raise AssertionError('Truncated rig accepted')
        except ValueError:
            controls += 1
    with tempfile.TemporaryDirectory(prefix='coh-huge-recovery-check-') as temporary:
        source, output = Path(temporary) / 'rig.bin', Path(temporary) / 'source'
        source.write_bytes(raw)
        result = original.publish(source, output)
        for name, body in bodies.items():
            assert (output / name).read_bytes() == body
            assert result[name]['sha256'] == hashlib.sha256(body).hexdigest()
            controls += 1
        try:
            original.publish(source, output)
            raise AssertionError('Existing output replaced')
        except ValueError:
            controls += 1
    print(json.dumps({'passed': True, 'controls': controls, 'original_animation_bytes': sum(map(len, bodies.values())),
                      'scope': 'Exact original Huge source spans from retained COHRIG01, not selected costume geometry'}))


if __name__ == '__main__':
    main()
