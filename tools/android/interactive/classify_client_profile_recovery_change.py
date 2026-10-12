#!/usr/bin/env python3
"""Select the exact .31 explicit profile recovery or its final evidence.

Only two guest helpers and three reviewed Java sources may change; native, asset
and unknown paths cannot enter this lane. Dispatches and anything except one direct parent
remain fail closed. The dedicated workflow qualifies the complete real assets.
"""
import os
from pathlib import Path
import re
import subprocess


CLIENT_PROFILE_RECOVERY_MARKER = 'tools/android/interactive/release-client-profile-recovery-0.13.31.json'
CLIENT_PROFILE_RECOVERY_PUBLICATION = 'docs/android-evidence/client-profile-recovery-0.13.31-publication.json'
CLIENT_PROFILE_RECOVERY_DOCS = frozenset({
    'docs/HANDOFF.md',
    'docs/COH-Atlas-Gameplay-0.13.31-testing.txt',
    'docs/android-evidence/client-profile-recovery-0.13.30-device-result.json',
    'docs/android-evidence/client-profile-recovery-0.13.30-full-startup-negative.json',
    CLIENT_PROFILE_RECOVERY_PUBLICATION,
})
CLIENT_PROFILE_RECOVERY_ALLOWED = CLIENT_PROFILE_RECOVERY_DOCS | frozenset({
    CLIENT_PROFILE_RECOVERY_MARKER,
    '.github/workflows/android-client-profile-recovery.yml',
    'android/guest/character_creation_diagnostic.py', 'android/guest/local_character_server.py',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientActivity.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientService.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientRuntime.java',
    'tools/android/interactive/build_client_profile_recovery_apk.py',
    'tools/android/interactive/test_client_profile_recovery_package.py',
    'tools/android/interactive/qualify_client_profile_recovery.py',
    'tools/android/interactive/qualify_full_startup_preflight.py',
    'tools/android/interactive/test_full_startup_preflight.py',
    'tools/android/interactive/test_character_profile_eligibility.py',
    'tools/android/interactive/test_profile_failure_presentation.py',
    'tools/android/interactive/test_kings_row_runtime_dependencies.py',
    'tools/android/interactive/test_fresh_profile_recovery.py',
    'tools/android/interactive/test_storage_recovery_ui.py',
    'tools/android/interactive/test_storage_ui.py',
    'tools/android/interactive/test_character_server.py',
    'tools/android/interactive/test_client_asset_closure_limits.py',
    'tools/android/interactive/test_runtime_timestamps.py',
    'tools/android/interactive/qualify_runtime_timestamps.py',
    'tools/android/interactive/test_client_animation_repair_package.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_client_profile_recovery_change.py',
    'tools/android/interactive/classify_client_animation_repair_change.py',
    'tools/android/interactive/classify_client_receipt_repair_change.py',
    'tools/android/interactive/classify_client_assets_change.py',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
})


def client_profile_recovery_owned(event, before, head, parent, names):
    paths = set(names)
    direct = (event == 'push' and re.fullmatch('[0-9a-f]{40}', before or '')
        and re.fullmatch('[0-9a-f]{40}', head or '')
        and re.fullmatch('[0-9a-f]{40}', parent or '')
        and before != '0'*40 and head != '0'*40
        and before == parent and head != before and bool(paths))
    return bool(direct and ((paths <= CLIENT_PROFILE_RECOVERY_ALLOWED
        and CLIENT_PROFILE_RECOVERY_MARKER in paths)
        or (paths <= CLIENT_PROFILE_RECOVERY_DOCS
            and CLIENT_PROFILE_RECOVERY_PUBLICATION in paths)))


def main():
    required = True
    try:
        # HEAD^@ returns every parent. More than one cannot match the SHA gate.
        parent = subprocess.check_output(['git', 'rev-parse', 'HEAD^@'], text=True).strip()
        head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        names = subprocess.check_output(['git', 'diff', '--name-only', '-z', parent, head]).decode().rstrip('\0').split('\0')
        from classify_client_map_startup_change import client_map_startup_owned
        context = (os.environ.get('GITHUB_EVENT_NAME'), os.environ.get('COH_PUSH_BEFORE'), head, parent, names)
        required = not (client_profile_recovery_owned(*context) or client_map_startup_owned(*context))
    except (OSError, subprocess.CalledProcessError, UnicodeError):
        pass
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as output:
        output.write('legacy_native_required='+str(required).lower()+'\n')
    print('Historical qualification required' if required else
        'Dedicated .31 explicit profile recovery owns this exact push')


if __name__ == '__main__':
    main()
