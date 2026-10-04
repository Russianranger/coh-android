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
STARTUP_SOURCES = frozenset({
    '.github/workflows/android-startup-schedule.yml',
    'tools/android/interactive/build_startup_schedule_apk.py',
    'tools/android/interactive/qualify_startup_schedule.py',
    'tools/android/interactive/package_startup_dbserver.py',
    'tools/android/interactive/test_startup_schedule_package.py',
    'tools/android/interactive/test_startup_schedule.py',
    'tools/android/interactive/test_world_asset_reuse.py',
    'tools/android/interactive/test_atlas_world_assets.py',
    'tools/android/interactive/test_local_launcher_wait.py',
    'tools/android/interactive/test_server_worktree_reuse.py',
    'android/guest/atlas_world_assets.py',
    'android/guest/character_creation_diagnostic.py',
    'android/guest/local_character_server.py',
    'android/guest/local_login_server.py',
    'patches/startup-dbserver/0001-manual-atlas-launcher-wait.patch',
    'database/startup-dbserver/overlay/DBServer/src/wine_manual_atlas.c',
    'database/startup-dbserver/overlay/DBServer/src/wine_manual_atlas.h',
})
STARTUP_ALLOWED = STARTUP_SOURCES | frozenset({
    '.github/workflows/android-storage-recovery.yml',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'docs/COH-Atlas-Gameplay-0.13.3-testing.txt', 'docs/HANDOFF.md',
    'docs/android-evidence/startup-schedule-0.13.3-baseline.json',
    'docs/android-evidence/startup-schedule-0.13.3-publication.json',
})
RECEIPT_SOURCES = frozenset({
    '.github/workflows/android-task-receipt-cleanup.yml',
    'tools/android/interactive/build_task_receipt_cleanup_apk.py',
    'tools/android/interactive/qualify_task_receipt_cleanup.py',
    'tools/android/interactive/test_task_receipt_cleanup_package.py',
    'tools/android/interactive/test_task_receipt_cleanup.py',
    JAVA+'ClientRuntime.java',
    'android/guest/character_reopen_diagnostic.py',
})
RECEIPT_ALLOWED = RECEIPT_SOURCES | frozenset({
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'docs/COH-Atlas-Gameplay-0.13.4-testing.txt', 'docs/HANDOFF.md',
    'docs/android-evidence/startup-schedule-0.13.3-reopen-blocked.json',
    'docs/android-evidence/task-receipt-cleanup-0.13.4-publication.json',
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


def bounded_push(event, before, head, parent, names, allowed=ALLOWED):
    return bool(event == 'push' and re.fullmatch('[0-9a-f]{40}', before or '')
        and before != '0'*40 and before == parent and head != before
        and names and set(names) <= allowed)


def startup_push(event, before, head, parent, names):
    return bool(bounded_push(event, before, head, parent, names, STARTUP_ALLOWED)
        and set(names) & STARTUP_SOURCES)


def receipt_push(event, before, head, parent, names):
    return bool(bounded_push(event, before, head, parent, names, RECEIPT_ALLOWED)
        and set(names) & RECEIPT_SOURCES)


def task_required(event, before, head, parent, names):
    return not ((bounded_push(event, before, head, parent, names)
        and set(names) & (STORAGE_SOURCES | RECOVERY_SOURCES))
        or startup_push(event, before, head, parent, names)
        or receipt_push(event, before, head, parent, names))


def cleanup_required(event, before, head, parent, names):
    """Keep historical 0.13.1 publication out of a qualified recovery derivative."""
    return not ((bounded_push(event, before, head, parent, names)
        and set(names) & RECOVERY_SOURCES) or startup_push(event, before, head, parent, names)
        or receipt_push(event, before, head, parent, names))


def recovery_required(event, before, head, parent, names):
    """The newer source-bound startup derivative owns only its explicit scope."""
    return not (startup_push(event, before, head, parent, names) or receipt_push(event, before, head, parent, names))


def main():
    required = True
    cleanup = True
    recovery = True
    try:
        parent = subprocess.check_output(['git','rev-parse','HEAD^'], text=True).strip()
        head = subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip()
        names = subprocess.check_output(['git','diff','--name-only','-z',parent,head]).decode().rstrip('\0').split('\0')
        required = task_required(os.environ.get('GITHUB_EVENT_NAME'),
            os.environ.get('COH_PUSH_BEFORE'), head, parent, names)
        cleanup = cleanup_required(os.environ.get('GITHUB_EVENT_NAME'),
            os.environ.get('COH_PUSH_BEFORE'), head, parent, names)
        recovery = recovery_required(os.environ.get('GITHUB_EVENT_NAME'),
            os.environ.get('COH_PUSH_BEFORE'), head, parent, names)
    except (OSError, subprocess.CalledProcessError, UnicodeError):
        pass
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as output:
        output.write('task_required='+str(required).lower()+'\n')
        output.write('cleanup_required='+str(cleanup).lower()+'\n')
        output.write('recovery_required='+str(recovery).lower()+'\n')
    print('Retained Android storage workflow owns this update' if not required
          else 'Task and native animation workflow required')


if __name__ == '__main__':
    main()
