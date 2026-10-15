#!/usr/bin/env python3
"""Select only the marked .29 receipt-order packaging repair or its final evidence.

The dedicated owner reuses every published native/runtime and external asset
payload. Guest, Java, native, asset and unknown source paths cannot enter this
lane. Dispatches and anything except one direct parent remain fail closed.
"""
import os
from pathlib import Path
import re
import subprocess
from classify_client_animation_repair_change import historical_repair_owned as client_animation_repair_owned


CLIENT_RECEIPT_REPAIR_MARKER = 'tools/android/interactive/release-client-receipt-repair-0.13.29.json'
CLIENT_RECEIPT_REPAIR_PUBLICATION = 'docs/android-evidence/client-receipt-repair-0.13.29-publication.json'
CLIENT_RECEIPT_REPAIR_DOCS = frozenset({
    'docs/HANDOFF.md',
    'docs/COH-Atlas-Gameplay-0.13.29-testing.txt',
    'docs/android-evidence/client-receipt-repair-0.13.29-device-failure.json',
    CLIENT_RECEIPT_REPAIR_PUBLICATION,
})
CLIENT_RECEIPT_REPAIR_ALLOWED = CLIENT_RECEIPT_REPAIR_DOCS | frozenset({
    CLIENT_RECEIPT_REPAIR_MARKER,
    '.github/workflows/android-client-receipt-repair.yml',
    'tools/android/interactive/build_client_receipt_repair_apk.py',
    'tools/android/interactive/qualify_client_receipt_repair.py',
    'tools/android/interactive/repair_game_receipt_order.py',
    'tools/android/interactive/test_client_receipt_repair_package.py',
    'tools/android/interactive/test_game_receipt_order.py',
    'tools/android/interactive/classify_client_receipt_repair_change.py',
    'tools/android/interactive/classify_client_assets_change.py',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'docs/android-evidence/client-receipt-repair-0.13.29-donor-game-package.json',
    'docs/android-evidence/client-receipt-repair-0.13.29-mapserver-progress-original.json',
    'docs/android-evidence/client-receipt-repair-0.13.29-native-responsiveness.json',
})


def client_receipt_repair_owned(event, before, head, parent, names):
    paths = set(names)
    direct = (event == 'push' and re.fullmatch('[0-9a-f]{40}', before or '')
        and re.fullmatch('[0-9a-f]{40}', head or '')
        and re.fullmatch('[0-9a-f]{40}', parent or '')
        and before != '0'*40 and head != '0'*40
        and before == parent and head != before and bool(paths))
    return bool(direct and ((paths <= CLIENT_RECEIPT_REPAIR_ALLOWED
        and CLIENT_RECEIPT_REPAIR_MARKER in paths)
        or (paths <= CLIENT_RECEIPT_REPAIR_DOCS
            and CLIENT_RECEIPT_REPAIR_PUBLICATION in paths)))


def main():
    required = True
    try:
        # HEAD^@ returns every parent. More than one cannot match the SHA gate.
        parent = subprocess.check_output(['git', 'rev-parse', 'HEAD^@'], text=True).strip()
        head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        names = subprocess.check_output(['git', 'diff', '--name-only', '-z', parent, head]).decode().rstrip('\0').split('\0')
        context = (os.environ.get('GITHUB_EVENT_NAME'),
            os.environ.get('COH_PUSH_BEFORE'), head, parent, names)
        required = not (client_receipt_repair_owned(*context) or client_animation_repair_owned(*context))
    except (OSError, subprocess.CalledProcessError, UnicodeError):
        pass
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as output:
        output.write('legacy_native_required='+str(required).lower()+'\n')
    print('Historical qualification required' if required else
        'Dedicated repair publication owns this exact push')


if __name__ == '__main__':
    main()
