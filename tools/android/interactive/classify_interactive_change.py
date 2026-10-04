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
from classify_storage_cleanup_change import STARTUP_ALLOWED, RECEIPT_ALLOWED, SETUP_ALLOWED

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
    'android/guest/local_character_server.py',
    'tools/android/interactive/test_ground_repair.py',
    'tools/android/interactive/qualify_ground_repair.py',
    'tools/android/interactive/build_ground_repair_apk.py',
    'tools/android/interactive/test_ground_repair_package.py',
    'tools/android/interactive/fixtures/thor-ground-0.11.1-20261002.log',
    'tools/android/interactive/fixtures/thor-ground-0.11.1-20261002.json',
    '.github/workflows/android-ground-repair.yml',
    'docs/COH-Atlas-Gameplay-0.11.2-testing.txt',
    'docs/android-evidence/thor-0.11.1-ground-verifier-failed-20261002.json',
    'docs/android-evidence/thor-0.11.2-interior-movement-save-passed-20261002.json',
    'docs/android-evidence/thor-0.11.2-outdoor-observed-save-incomplete-20261002.json',
    'docs/COH-Atlas-Gameplay-0.11.2-saved-position-outdoor-testing.txt',
    'android/guest/client_interactive_diagnostic.py',
    'android/guest/character_reopen_diagnostic.py',
    'android/guest/character_session_budget.py',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientRuntime.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientService.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientSessionBudget.java',
    'tools/android/interactive/build_session_window_apk.py',
    'tools/android/interactive/qualify_session_window.py',
    'tools/android/interactive/test_session_window_package.py',
    'tools/android/interactive/test_session_budget_guest.py',
    'tools/android/interactive/test_session_budget_java.py',
    'tools/android/interactive/audit_atlas_beacon_inputs.py',
    'tools/android/interactive/test_atlas_beacon_inputs.py',
    '.github/workflows/android-session-window.yml',
    'docs/android-evidence/atlas-beacon-input-preflight.json',
    'docs/android-evidence/session-window-0.11.3-publication.json',
    'docs/android-evidence/thor-0.11.3-outdoor-movement-save-passed-20261002.json',
    'docs/COH-Atlas-Gameplay-0.11.3-testing.txt',
    'android/guest/character_creation_diagnostic.py',
    'android/guest/character_server_data_cache.py',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/InteractiveRfbClient.java',
    'tools/android/interactive/test_character_readiness.py',
    'tools/android/interactive/test_rfb_buffered_input.py',
    'tools/android/interactive/test_server_worktree_reuse.py',
    'tools/android/interactive/build_startup_perf_apk.py',
    'tools/android/interactive/qualify_startup_perf.py',
    'tools/android/interactive/test_startup_perf_package.py',
    '.github/workflows/android-startup-perf.yml',
    'docs/COH-Atlas-Gameplay-0.11.4-testing.txt',
    'docs/android-evidence/startup-perf-0.11.4-publication.json',
    'tools/android/interactive/fixtures/session-window-0.11.3-client_interactive_diagnostic.py',
    'tools/android/interactive/fixtures/session-window-0.11.3-character_reopen_diagnostic.py',
})

# These explicit paths use the separately receipted responsiveness or repair
# workflow. Repairs reuse the verified Game and MapServer build; the historical
# full donor pipeline must not publish over those dedicated releases.
RESPONSIVENESS_ONLY = frozenset({
    '.github/workflows/android-storage-recovery.yml',
    'android/app/src/main/java/io/github/russianranger/cohdiagnostic/DiagnosticRuntime.java',
    'tools/android/interactive/build_storage_recovery_apk.py',
    'tools/android/interactive/qualify_storage_recovery.py',
    'tools/android/interactive/test_storage_recovery_package.py',
    'tools/android/interactive/test_fresh_profile_recovery.py',
    'tools/android/interactive/test_runtime_setup_reuse.py',
    'tools/android/interactive/test_storage_recovery_ui.py',
    'docs/COH-Atlas-Gameplay-0.13.2-testing.txt',
    'docs/android-evidence/storage-recovery-0.13.2-publication.json',
    'docs/android-evidence/thor-0.13.1-reinstall-failure-20261003.json',
    '.github/workflows/android-storage-cleanup.yml',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/StorageAudit.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/StorageFiles.java',
    'tools/android/interactive/build_storage_cleanup_apk.py',
    'tools/android/interactive/qualify_storage_cleanup.py',
    'tools/android/interactive/test_storage_cleanup_package.py',
    'tools/android/interactive/test_storage_audit.py',
    'tools/android/interactive/test_storage_ui.py',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'docs/COH-Atlas-Gameplay-0.13.1-testing.txt',
    '.github/workflows/android-task-gate.yml',
    'android/guest/task_gate_evidence.py',
    'android/guest/task-gate.json',
    'android/guest/server_animation_package.py',
    'tools/android/atlasgame/prepare_server_animations.py',
    'tools/android/atlasgame/test_server_animations.py',
    'tools/android/interactive/build_task_gate_apk.py',
    'tools/android/interactive/qualify_task_gate.py',
    'tools/android/interactive/test_task_gate_package.py',
    'tools/android/interactive/test_task_gate_evidence.py',
    'tools/android/interactive/test_task_gate_native_contract.py',
    'tools/android/interactive/test_task_gate_integration.py',
    'tools/android/interactive/test_task_gate_java.py',
    'docs/COH-Atlas-Gameplay-0.13.0-testing.txt',
    '.github/workflows/android-contact-interaction.yml',
    'android/guest/stationary_contact_evidence.py',
    'tools/android/interactive/build_contact_interaction_apk.py',
    'tools/android/interactive/qualify_contact_interaction.py',
    'tools/android/interactive/test_contact_interaction_package.py',
    'tools/android/interactive/test_contact_capture.py',
    'tools/android/interactive/test_stationary_contact_evidence.py',
    'tools/android/interactive/test_acceptance.py',
    'tools/android/interactive/test_character_reopen_guest.py',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientAcceptance.java',
    'docs/COH-Atlas-Gameplay-0.12.0-testing.txt',
    'docs/android-evidence/thor-0.11.6-client-accepted-20261002.json',
    'docs/android-evidence/contact-interaction-0.12.0-publication.json',
    '.github/workflows/android-reopen-repair.yml',
    'tools/android/interactive/build_reopen_repair_apk.py',
    'tools/android/interactive/qualify_reopen_repair.py',
    'tools/android/interactive/test_reopen_repair_package.py',
    'tools/android/interactive/test_process_exit_history.py',
    'android/app/src/main/java/io/github/russianranger/cohdiagnostic/TarExtractor.java',
    'tools/android/test_archive.py',
    'tools/android/java/io/github/russianranger/cohdiagnostic/ExtractRuntimeHost.java',
    'docs/COH-Atlas-Gameplay-0.11.6-testing.txt',
    'docs/android-evidence/reopen-repair-0.11.6-publication.json',
    'docs/android-evidence/thor-0.11.5-reopen-preflight-failed-20261002.json',
    '.github/workflows/android-responsiveness.yml',
    '.github/workflows/android-responsiveness-native.yml',
    'android/guest/client_startup_diagnostic.py',
    'android/guest/game_diagnostic.py',
    'android/guest/native_responsiveness_contract.py',
    'android/guest/native_character_events.py',
    'android/guest/texture_header_index.py',
    'android/guest/client_attempt_retry.py',
    'android/native/client-launcher.c',
    'tools/prepare_character_events_source.py',
    'tools/test_prepare_character_events_source.py',
    'tools/prepare_client_graphics_source.py',
    'tools/prepare_client_texture_source.py',
    'tools/test_prepare_client_texture_source.py',
    'tools/android/game/test_character_events.py',
    'tools/android/interactive/build_responsiveness_apk.py',
    'tools/android/interactive/package_responsiveness_native.py',
    'tools/android/interactive/qualify_responsiveness.py',
    'tools/android/interactive/test_responsiveness_package.py',
    'tools/android/interactive/test_client_attempt_retry.py',
    'tools/android/interactive/test_graphics_profile.py',
    'tools/android/interactive/test_native_client_upgrade.py',
    'tools/android/interactive/test_texture_header_index.py',
    'patches/character-events/0001-character-events.patch',
    'database/character-events/overlay/MapServer/src/svr/wine_character_events.h',
    'database/character-events/overlay/MapServer/src/svr/wine_character_events.c',
    'database/character-events/tests/events_contract.c',
    'patches/client-graphics/0001-reversible-performance-profile.patch',
    'database/client-graphics/overlay/Game/src/graphics/cohAndroidGraphicsProfile.h',
    'patches/client-texture-index/0001-index-texture-headers.patch',
    'database/client-texture-index/overlay/Game/src/render/coh_texture_header_index.h',
    'docs/COH-Atlas-Gameplay-0.11.5-testing.txt',
    'docs/android-evidence/responsiveness-0.11.5-publication.json',
})
RESPONSIVENESS_ONLY |= STARTUP_ALLOWED | RECEIPT_ALLOWED | SETUP_ALLOWED


def runtime_required(event, before, head, parent, names):
    return not (event == 'push' and re.fullmatch('[0-9a-f]{40}', before or '')
        and before != '0' * 40 and before == parent and head != before
        and names and set(names) <= SHELL_ONLY | RESPONSIVENESS_ONLY)


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
