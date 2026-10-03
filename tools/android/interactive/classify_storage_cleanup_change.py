#!/usr/bin/env python3
"""Route the Android-only storage derivative without rerunning native packing.

Unknown files/history and explicit task workflow dispatch remain fail-closed.
The separate storage workflow verifies every retained runtime payload and runs
all task/input/save host guards before its own new-version publication.
"""
import os
from pathlib import Path
import re
import subprocess

JAVA = 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/'
STORAGE_SOURCES = frozenset({
    JAVA+'StorageAudit.java', JAVA+'StorageFiles.java',
    '.github/workflows/android-storage-cleanup.yml',
    'tools/android/interactive/build_storage_cleanup_apk.py',
    'tools/android/interactive/qualify_storage_cleanup.py',
    'tools/android/interactive/test_storage_cleanup_package.py',
    'tools/android/interactive/test_storage_audit.py',
    'tools/android/interactive/test_storage_ui.py',
})
RECOVERY_SOURCES = frozenset({
    '.github/workflows/android-storage-recovery.yml',
    'tools/android/interactive/build_storage_recovery_apk.py',
    'tools/android/interactive/qualify_storage_recovery.py',
    'tools/android/interactive/test_storage_recovery_package.py',
    'tools/android/interactive/test_fresh_profile_recovery.py',
    'tools/android/interactive/test_runtime_setup_reuse.py',
    'tools/android/interactive/test_storage_recovery_ui.py',
})
ALLOWED = STORAGE_SOURCES | RECOVERY_SOURCES | frozenset({
    JAVA+'ClientActivity.java', JAVA+'ClientRuntime.java', JAVA+'ClientService.java',
    'android/app/src/main/java/io/github/russianranger/cohdiagnostic/DiagnosticRuntime.java',
    '.github/workflows/android-task-gate.yml',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'docs/COH-Atlas-Gameplay-0.13.1-testing.txt', 'docs/HANDOFF.md',
    'docs/android-evidence/storage-cleanup-0.13.1-publication.json',
    'docs/COH-Atlas-Gameplay-0.13.2-testing.txt',
    'docs/android-evidence/storage-recovery-0.13.2-publication.json',
    'docs/android-evidence/thor-0.13.1-reinstall-failure-20261003.json',
})


def bounded_push(event, before, head, parent, names):
    return bool(event == 'push' and re.fullmatch('[0-9a-f]{40}', before or '')
        and before != '0'*40 and before == parent and head != before
        and names and set(names) <= ALLOWED)


def task_required(event, before, head, parent, names):
    return not (bounded_push(event, before, head, parent, names)
        and set(names) & (STORAGE_SOURCES | RECOVERY_SOURCES))


def cleanup_required(event, before, head, parent, names):
    """Keep historical 0.13.1 publication out of a qualified recovery derivative."""
    return not (bounded_push(event, before, head, parent, names)
        and set(names) & RECOVERY_SOURCES)


def main():
    required = True
    cleanup = True
    try:
        parent = subprocess.check_output(['git','rev-parse','HEAD^'], text=True).strip()
        head = subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip()
        names = subprocess.check_output(['git','diff','--name-only','-z',parent,head]).decode().rstrip('\0').split('\0')
        required = task_required(os.environ.get('GITHUB_EVENT_NAME'),
            os.environ.get('COH_PUSH_BEFORE'), head, parent, names)
        cleanup = cleanup_required(os.environ.get('GITHUB_EVENT_NAME'),
            os.environ.get('COH_PUSH_BEFORE'), head, parent, names)
    except (OSError, subprocess.CalledProcessError, UnicodeError):
        pass
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as output:
        output.write('task_required='+str(required).lower()+'\n')
        output.write('cleanup_required='+str(cleanup).lower()+'\n')
    print('Retained Android storage workflow owns this update' if not required
          else 'Task and native animation workflow required')


if __name__ == '__main__':
    main()
