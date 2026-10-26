#!/usr/bin/env python3
"""Exercise the original entry/animation code across the deferred menu change.

The negative control changes only 0074's reset call back to immediate restart.
Real initialization, selection, queue construction and the gLoopNow block are
extracted; unrelated renderer/entity operations are stubbed. ASan/UBSan must
reject the old costume-menu index and the fixed path must retain all three
valid selections, including an empty selection, on the destination frame.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile


def function(text, signature):
    start = text.index(signature)
    opening = text.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def harness(source, original=False):
    text = (source / 'Game/src/UI/uiPowerCust.c').read_text()
    initialize = function(text, 'static void initializeMenu()')
    if original:
        assert initialize.count('resetPowerCustomizationPreview();') == 1
        initialize = initialize.replace('resetPowerCustomizationPreview();',
                                        'restartPowerCustomizationAnimation();')
    animation = function(text, 'void powerCust_handleAnimation()')
    # Keep the actual selection and restart block; do not simulate its index.
    animation = animation[:animation.index('    seqClearState(e->seq->state);')] + '}\n'
    fixture = Path(__file__).with_name('power_preview_transition_fixture.c').read_text()
    code = '\n'.join((
        function(text, 'static void createAnimationQueue()'),
        function(text, 'void restartPowerCustomizationAnimation()'),
        function(text, 'void resetPowerCustomizationPreview()'),
        initialize,
        function(text, 'void powerCustMenuEnter()'),
        animation,
    ))
    return fixture.replace('/* SOURCE_FUNCTIONS */', code)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        c, exe = Path(tmp) / 'control.c', Path(tmp) / 'control'
        for original in (True, False):
            c.write_text(harness(args.source, original))
            subprocess.run(['cc', '-std=c11', '-g', '-O1', '-fsanitize=address,undefined',
                            '-fno-sanitize-recover=all', str(c), '-o', str(exe)], check=True)
            if original:
                result = subprocess.run([str(exe), '8', '24', '0'], capture_output=True, text=True)
                if not result.returncode or 'index -16 out of bounds' not in result.stderr:
                    raise AssertionError('old entry must fail at the exact array index: ' + result.stderr)
                print('original costume entry: UBSan rejects sSelectedPowers[-16]', flush=True)
            else:
                for old in (0, 5, 8, 24, 25, 26):
                    for target in (24, 25, 26):
                        for empty in (0, 1):
                            subprocess.run([str(exe), str(old), str(target), str(empty)], check=True,
                                           stdout=subprocess.DEVNULL)
                print('patched entry: 36 old/destination/empty cases; no pre-transition selection; '
                      'one destination-frame queue; selected pointer preserved', flush=True)


if __name__ == '__main__':
    main()
