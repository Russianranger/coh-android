#!/usr/bin/env python3
"""Route bounded host corrections and gameplay derivatives without rebuilding their donor.

The separate gameplay builder checks retained payloads and sources against the
exact qualified donor, permitting only walking UI, appended pinned world
resources and immutable world-pin constants. The dedicated retained-APK workflow
qualifies host-driver corrections using two real sessions. A dispatch or an
unknown history/file always requests the original full build and runtime.
"""
import os
from pathlib import Path
import re
import subprocess

SHELL_ONLY = frozenset({
    'tools/android/interactive/character_host_smoke.py',
    'tools/android/interactive/character_reopen_host_smoke.py',
    'tools/android/interactive/test_character_host.py',
    'tools/android/interactive/test_character_reopen_host.py',
    'tools/android/interactive/fixtures/character-name-36920583713.png',
    '.github/workflows/android-character-reopen-qualified-apk.yml',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientActivity.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientInput.java',
    'tools/android/interactive/test_input.py',
    'tools/android/interactive/build_atlas_gameplay_apk.py',
    'tools/android/interactive/test_atlas_gameplay_package.py',
    'tools/android/interactive/build_avatar_repair_apk.py',
    'tools/android/interactive/test_avatar_repair_package.py',
    'tools/android/interactive/qualify_avatar_repair.py',
    'android/guest/character_avatar_assets.py',
    'tools/android/interactive/test_character_avatar_assets.py',
    '.github/workflows/android-avatar-repair.yml',
    'docs/COH-Atlas-Gameplay-0.11.1-testing.txt',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    '.github/workflows/android-atlas-gameplay.yml',
    '.github/workflows/android-client-interactive.yml',
    '.github/workflows/android-diagnostic.yml',
    'docs/COH-Atlas-Gameplay-0.11.0-testing.txt',
    'docs/ANDROID_ATLAS_GAMEPLAY_TEST.md',
    'docs/HANDOFF.md',
    'docs/android-evidence/atlas-material-inputs-0.11.0.json',
    'docs/android-evidence/character-reopen-hosted-36913457461-failed.json',
    'assets/atlas-world-supplement-manifest.json',
    'android/guest/atlas_world_assets.py',
    'tools/android/interactive/prepare_atlas_world_assets.py',
    'tools/android/interactive/test_atlas_world_assets.py',
    'tools/android/interactive/test_atlas_world_package.py',
    'docs/android-evidence/atlas-world-reopen-reviewed.json',
    'docs/android-evidence/character-reopen-hosted-36920583713-ocr-failed.json',
    'docs/android-evidence/thor-0.11.0-reopen-failed-20261001.json',
})


def runtime_required(event, before, head, parent, names):
    return not (event == 'push' and re.fullmatch('[0-9a-f]{40}', before or '')
        and before != '0' * 40 and before == parent and head != before
        and names and set(names) <= SHELL_ONLY)


def main():
    required = True
    try:
        parent = subprocess.check_output(['git', 'rev-parse', 'HEAD^'], text=True).strip()
        head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        names = subprocess.check_output(['git', 'diff', '--name-only', '-z', parent, head]).decode().rstrip('\0').split('\0')
        required = runtime_required(os.environ.get('GITHUB_EVENT_NAME'),
            os.environ.get('COH_PUSH_BEFORE'), head, parent, names)
    except (OSError, subprocess.CalledProcessError, UnicodeError):
        pass
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as output:
        output.write('runtime_required=' + str(required).lower() + '\n')
    print('Full runtime qualification required' if required else
          'Dedicated workflows verify the retained APK or bounded gameplay derivative')


if __name__ == '__main__':
    main()
