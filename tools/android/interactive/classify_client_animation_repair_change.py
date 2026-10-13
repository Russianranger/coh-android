#!/usr/bin/env python3
"""Select the exact .30 animation compatibility repair or its final evidence.

Only the two reviewed guest helpers may change; native, Java, asset and unknown
paths cannot enter this lane. Dispatches and anything except one direct parent
remain fail closed. The dedicated workflow qualifies the complete real assets.
"""
import os
from pathlib import Path
import re
import subprocess


CLIENT_ANIMATION_REPAIR_MARKER = 'tools/android/interactive/release-client-animation-repair-0.13.30.json'
CLIENT_ANIMATION_REPAIR_PUBLICATION = 'docs/android-evidence/client-animation-repair-0.13.30-publication.json'
CLIENT_ANIMATION_REPAIR_DOCS = frozenset({
    'docs/HANDOFF.md',
    'docs/COH-Atlas-Gameplay-0.13.30-testing.txt',
    'docs/android-evidence/client-animation-repair-0.13.30-device-failure.json',
    CLIENT_ANIMATION_REPAIR_PUBLICATION,
})
CLIENT_ANIMATION_REPAIR_ALLOWED = CLIENT_ANIMATION_REPAIR_DOCS | frozenset({
    CLIENT_ANIMATION_REPAIR_MARKER,
    '.github/workflows/android-client-animation-repair.yml',
    'android/guest/server_animation_package.py',
    'android/guest/local_character_server.py',
    'tools/android/interactive/build_client_animation_repair_apk.py',
    'tools/android/interactive/test_client_animation_repair_package.py',
    'tools/android/interactive/qualify_client_animation_repair.py',
    'tools/android/interactive/qualify_runtime_asset_preflight.py',
    'tools/android/interactive/test_runtime_asset_preflight.py',
    'tools/android/interactive/test_animation_runtime_compatibility.py',
    'tools/android/interactive/test_client_receipt_repair_package.py',
    'tools/android/interactive/classify_client_animation_repair_change.py',
    'tools/android/interactive/classify_client_receipt_repair_change.py',
    'tools/android/interactive/classify_client_assets_change.py',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
})


def client_animation_repair_owned(event, before, head, parent, names):
    paths = set(names)
    direct = (event == 'push' and re.fullmatch('[0-9a-f]{40}', before or '')
        and re.fullmatch('[0-9a-f]{40}', head or '')
        and re.fullmatch('[0-9a-f]{40}', parent or '')
        and before != '0'*40 and head != '0'*40
        and before == parent and head != before and bool(paths))
    return bool(direct and ((paths <= CLIENT_ANIMATION_REPAIR_ALLOWED
        and CLIENT_ANIMATION_REPAIR_MARKER in paths)
        or (paths <= CLIENT_ANIMATION_REPAIR_DOCS
            and CLIENT_ANIMATION_REPAIR_PUBLICATION in paths)))


def historical_repair_owned(*context):
    # Preserve each historical owner; the marker-approved .33 APK derivative
    # has its own finite source closure and reuses the qualified .32 natives.
    from classify_client_profile_recovery_change import client_profile_recovery_owned
    from classify_client_map_startup_change import client_map_startup_owned
    from classify_client_report_loading_change import client_report_loading_owned
    from classify_client_saved_map_reopen_change import client_saved_map_reopen_owned
    from classify_client_manual_session_change import client_manual_session_owned
    from classify_client_startup_latency_change import client_startup_latency_owned
    from classify_client_zone_startup_change import client_zone_startup_owned
    return (client_animation_repair_owned(*context) or client_profile_recovery_owned(*context)
        or client_map_startup_owned(*context) or client_report_loading_owned(*context) or client_saved_map_reopen_owned(*context) or client_manual_session_owned(*context) or client_startup_latency_owned(*context) or client_zone_startup_owned(*context))


def main():
    required = True
    try:
        # HEAD^@ returns every parent. More than one cannot match the SHA gate.
        parent = subprocess.check_output(['git', 'rev-parse', 'HEAD^@'], text=True).strip()
        head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        names = subprocess.check_output(['git', 'diff', '--name-only', '-z', parent, head]).decode().rstrip('\0').split('\0')
        required = not historical_repair_owned(os.environ.get('GITHUB_EVENT_NAME'),
            os.environ.get('COH_PUSH_BEFORE'), head, parent, names)
    except (OSError, subprocess.CalledProcessError, UnicodeError):
        pass
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as output:
        output.write('legacy_native_required='+str(required).lower()+'\n')
    print('Historical qualification required' if required else
        'Dedicated finite derivative qualification owns this exact push')


if __name__ == '__main__':
    main()
