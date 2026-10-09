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
SETUP_SOURCES = frozenset({
    '.github/workflows/android-setup-memory.yml',
    'tools/android/interactive/build_setup_memory_apk.py',
    'tools/android/interactive/qualify_setup_memory.py',
    'tools/android/interactive/test_setup_memory_package.py',
    'tools/android/interactive/test_setup_service.py',
    'tools/android/test_setup_memory_guard.py',
    JAVA+'ClientRuntime.java', JAVA+'ClientService.java',
    JAVA+'ClientActivity.java', JAVA+'ClientSurface.java',
    'android/app/src/main/java/io/github/russianranger/cohdiagnostic/DiagnosticRuntime.java',
    'android/app/src/main/java/io/github/russianranger/cohdiagnostic/TarExtractor.java',
    'android/app/src/main/java/io/github/russianranger/cohdiagnostic/SetupMemoryGuard.java',
})
SETUP_ALLOWED = SETUP_SOURCES | frozenset({
    '.github/workflows/android-task-receipt-cleanup.yml',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'tools/android/test_archive.py',
    'tools/android/java/io/github/russianranger/cohdiagnostic/ExtractRuntimeHost.java',
    'tools/android/interactive/test_runtime_setup_reuse.py',
    'tools/android/interactive/test_storage_ui.py',
    'docs/COH-Atlas-Gameplay-0.13.5-testing.txt', 'docs/HANDOFF.md',
    'docs/android-evidence/setup-memory-0.13.4-user-report.json',
    'docs/android-evidence/setup-memory-0.13.5-publication.json',
})
BUNDLE_SOURCES = frozenset({
    '.github/workflows/android-startup-bundle.yml',
    'tools/android/interactive/build_startup_bundle_apk.py',
    'tools/android/interactive/qualify_startup_bundle.py',
    'tools/android/interactive/test_startup_bundle_package.py',
    'tools/android/interactive/package_startup_bundle_dbserver.py',
    'tools/android/interactive/test_startup_bundle_dbserver.py',
    'tools/android/interactive/test_startup_bundle_save.py',
    'tools/android/interactive/package_startup_bundle_client.py',
    'tools/android/interactive/test_startup_bundle_client.py',
    'patches/startup-bundle/0001-pg-cancelled-child-insert.patch',
    'patches/startup-bundle-client/0001-verified-texture-root.patch',
    'database/startup-bundle-client/overlay/Game/src/render/coh_texture_header_root.h',
    'android/guest/character_creation_diagnostic.py',
    'android/guest/character_server_data_cache.py',
    'android/guest/texture_header_index.py',
    'android/guest/client_interactive_diagnostic.py',
    'android/guest/client_startup_diagnostic.py',
    'android/guest/native_responsiveness_contract.py',
    'android/guest/local_character_server.py',
})
BUNDLE_ALLOWED = BUNDLE_SOURCES | frozenset({
    '.github/workflows/android-startup-schedule.yml',
    '.github/workflows/android-setup-memory.yml',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'tools/android/interactive/test_character_readiness.py',
    'tools/android/interactive/test_server_worktree_reuse.py',
    'tools/android/interactive/test_texture_header_index.py',
    'tools/android/interactive/test_native_client_upgrade.py',
    'tools/android/interactive/test_responsiveness_package.py',
    'tools/android/interactive/test_setup_memory_package.py',
    'docs/COH-Atlas-Gameplay-0.13.6-testing.txt', 'docs/HANDOFF.md',
    'docs/android-evidence/startup-bundle-0.13.5-device-result.json',
    'docs/android-evidence/startup-bundle-0.13.6-publication.json',
})
VISUAL_SOURCES = frozenset({
    '.github/workflows/android-client-visual.yml',
    'tools/android/interactive/build_client_visual_apk.py',
    'tools/android/interactive/qualify_client_visual.py',
    'tools/android/interactive/prepare_client_visual_assets.py',
    'tools/android/interactive/client_visual_geometry.py',
    'tools/android/interactive/test_client_visual_package.py',
    'tools/android/interactive/test_client_visual_assets.py',
    'tools/android/interactive/test_client_animation_package.py',
    'tools/android/interactive/test_client_visual_schedule.py',
    'android/guest/character_creation_diagnostic.py',
    'android/guest/client_animation_package.py',
    'android/guest/client_visual_assets.py',
    'assets/client-visual-manifest.json',
})
VISUAL_ALLOWED = VISUAL_SOURCES | frozenset({
    '.github/workflows/android-startup-bundle.yml',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'tools/android/interactive/test_server_worktree_reuse.py', '.gitignore',
    'docs/COH-Atlas-Gameplay-0.13.7-testing.txt', 'docs/HANDOFF.md',
    'docs/android-evidence/client-visual-0.13.6-device-result.json',
    'docs/android-evidence/client-visual-0.13.7-publication.json',
})
CLIENT_LOADING_SOURCES = frozenset({
    '.github/workflows/android-client-loading.yml',
    'tools/android/interactive/build_client_loading_apk.py',
    'tools/android/interactive/qualify_client_loading.py',
    'tools/android/interactive/test_client_loading_package.py',
    'tools/android/interactive/test_client_stage_acceptance.py',
    'tools/android/interactive/fixtures/client-stage-0.13.7.json',
    'tools/android/interactive/package_client_loading_native.py',
    'tools/android/interactive/test_client_loading_native.py',
    'tools/android/interactive/test_client_loading_contract.py',
    'patches/client-loading/0001-known-length-string-copy-and-profile.patch',
    'tools/android/interactive/prepare_client_visual_assets.py',
    'tools/android/interactive/client_visual_geometry.py',
    'tools/android/interactive/test_client_visual_assets.py',
    'android/guest/client_visual_assets.py', 'assets/client-visual-manifest.json',
    'android/guest/character_creation_diagnostic.py',
    'android/guest/native_responsiveness_contract.py',
    'android/guest/client_startup_diagnostic.py', 'android/guest/texture_header_index.py',
    JAVA+'ClientRuntime.java', JAVA+'ClientAcceptance.java',
})
CLIENT_LOADING_ALLOWED = CLIENT_LOADING_SOURCES | frozenset({
    '.github/workflows/android-client-visual.yml',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'tools/android/interactive/test_client_visual_package.py',
    'tools/android/interactive/test_acceptance.py', 'docs/HANDOFF.md',
    'docs/COH-Atlas-Gameplay-0.13.8-testing.txt',
    'docs/android-evidence/client-visual-0.13.7-device-result.json',
    'docs/android-evidence/client-loading-0.13.8-publication.json',
})
CLIENT_STREAMING_SOURCES = frozenset({
    '.github/workflows/android-client-streaming.yml',
    'tools/android/interactive/build_client_streaming_apk.py',
    'tools/android/interactive/qualify_client_streaming.py',
    'tools/android/interactive/test_client_streaming_package.py',
    'tools/android/interactive/prepare_client_visual_assets.py',
    'tools/android/interactive/test_client_visual_assets.py',
    'tools/android/interactive/test_texture_header_index.py',
    'tools/android/interactive/test_client_console_markers.py',
    'tools/android/interactive/benchmark_client_console_markers.py',
    'tools/android/interactive/benchmark_texture_inventory.py',
    'android/guest/client_visual_assets.py', 'assets/client-visual-manifest.json',
    'android/guest/client_startup_diagnostic.py', 'android/guest/texture_header_index.py',
})
CLIENT_STREAMING_ALLOWED = CLIENT_STREAMING_SOURCES | frozenset({
    '.github/workflows/android-client-loading.yml',
    'tools/android/interactive/test_client_loading_package.py',
    '.github/workflows/android-client-visual-candidates.yml',
    'tools/android/interactive/discover_client_visual_candidates.py',
    'tools/android/interactive/test_client_visual_candidates.py',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'docs/HANDOFF.md', 'docs/COH-Atlas-Gameplay-0.13.9-testing.txt',
    'docs/android-evidence/client-streaming-0.13.9-console-benchmark.json',
    'docs/android-evidence/client-streaming-0.13.9-texture-benchmark.json',
    'docs/android-evidence/client-streaming-0.13.9-assets.json',
    'docs/android-evidence/client-streaming-0.13.9-publication.json',
})
CLIENT_ASSET_CLOSURE_SOURCES = frozenset({
    '.github/workflows/android-client-asset-closure.yml',
    'tools/android/interactive/build_client_asset_closure_apk.py',
    'tools/android/interactive/qualify_client_asset_closure.py',
    'tools/android/interactive/test_client_asset_closure_package.py',
    'tools/android/interactive/test_client_asset_closure_limits.py',
    'tools/android/interactive/test_character_map_data.py',
    'tools/android/interactive/test_character_server.py',
    'tools/android/interactive/test_combat_reward_save.py',
    'tools/android/interactive/client_visual_tricks.py',
    'tools/android/interactive/test_client_visual_tricks.py',
    'tools/android/interactive/client_visual_geometry.py',
    'tools/android/interactive/test_client_visual_geometry.py',
    'tools/android/interactive/prepare_client_visual_assets.py',
    'tools/android/interactive/test_client_visual_assets.py',
    'tools/android/interactive/discover_client_visual_sweep.py',
    'tools/android/interactive/test_client_visual_sweep.py',
    '.github/workflows/android-client-visual-sweep.yml',
    'android/guest/client_visual_assets.py', 'android/guest/local_character_server.py',
    'android/guest/client_startup_diagnostic.py', 'assets/client-visual-manifest.json',
    'assets/client-visual-sweep-requests.json',
})
CLIENT_ASSET_CLOSURE_ALLOWED = CLIENT_ASSET_CLOSURE_SOURCES | frozenset({
    '.github/workflows/android-client-streaming.yml',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'docs/HANDOFF.md', 'docs/COH-Atlas-Gameplay-0.13.10-testing.txt',
    'docs/android-evidence/client-asset-closure-0.13.10-assets.json',
    'docs/android-evidence/client-asset-closure-0.13.10-publication.json',
    'docs/android-evidence/client-streaming-0.13.9-device-result.json',
    'docs/android-evidence/client-streaming-0.13.10-reward-save-validation.json',
})
CLIENT_STARTUP_FOLLOWUP_SOURCES = frozenset({
    '.github/workflows/android-client-startup-followup.yml',
    'tools/android/interactive/build_client_startup_followup_apk.py',
    'tools/android/interactive/qualify_client_startup_followup.py',
    'tools/android/interactive/test_client_startup_followup_package.py',
    'tools/android/interactive/test_client_startup_followup_guest.py',
    'tools/android/interactive/test_client_startup_followup_contract.py',
    'tools/android/interactive/test_client_startup_followup_limits.py',
    'tools/android/interactive/package_client_startup_followup_native.py',
    'tools/android/interactive/test_client_startup_followup_native.py',
    'patches/client-startup-followup/0001-preload-power-dependency-tree.patch',
    'tools/android/interactive/prepare_client_visual_followup.py',
    'tools/android/interactive/test_client_visual_followup.py',
    'tools/android/interactive/discover_client_appearance_assets.py',
    'tools/android/interactive/client_appearance_costumes.py',
    'tools/android/interactive/prepare_client_appearance_assets.py',
    'tools/android/interactive/test_client_appearance_assets.py',
    'tools/android/interactive/test_client_appearance_costumes.py',
    'tools/android/interactive/test_client_visual_assets.py',
    'assets/client-visual-followup-manifest.json',
    'assets/client-appearance-requests.json',
    'assets/client-appearance-manifest.json',
    'android/guest/client_visual_assets.py',
    'android/guest/client_startup_diagnostic.py',
    'android/guest/texture_header_index.py',
    'android/guest/native_responsiveness_contract.py',
})
CLIENT_STARTUP_FOLLOWUP_ALLOWED = CLIENT_STARTUP_FOLLOWUP_SOURCES | frozenset({
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'docs/HANDOFF.md', 'docs/COH-Atlas-Gameplay-0.13.11-testing.txt',
    'docs/android-evidence/client-startup-followup-0.13.11-assets.json',
    'docs/android-evidence/client-startup-followup-0.13.11-publication.json',
    'docs/android-evidence/client-startup-followup-0.13.11-device-result.json',
    'docs/android-evidence/client-startup-followup-0.13.11-startup.json',
    'docs/android-evidence/client-startup-followup-0.13.11-benchmark.json',
    'docs/android-evidence/client-asset-closure-0.13.10-device-result.json',
})
LEVELUP_UI_REPAIR_SOURCES = frozenset({
    '.github/workflows/android-levelup-ui-repair.yml',
    'patches/levelup-ui-repair/0001-pg-empty-row-witness.patch',
    'tools/android/interactive/build_levelup_ui_repair_apk.py',
    'tools/android/interactive/qualify_levelup_ui_repair.py',
    'tools/android/interactive/test_levelup_ui_repair_package.py',
    'tools/android/interactive/package_levelup_ui_repair_dbserver.py',
    'tools/android/interactive/test_levelup_ui_repair_dbserver.py',
    'tools/android/interactive/test_levelup_ui_repair_contract.py',
    'tools/android/interactive/discover_client_ui_repair_assets.py',
    'tools/android/interactive/prepare_client_ui_repair_assets.py',
    'tools/android/interactive/test_client_ui_repair_assets.py',
    'tools/android/interactive/test_client_preload_launch.py',
    'tools/android/interactive/test_training_save.py',
    'android/guest/native_training_save.py',
    'assets/client-ui-repair-requests.json', 'assets/client-ui-repair-manifest.json',
    'assets/client-ui-repair-plan.json',
    'android/guest/client_visual_assets.py', 'android/guest/local_character_server.py',
    'android/guest/client_interactive_diagnostic.py',
})
LEVELUP_UI_REPAIR_ALLOWED = LEVELUP_UI_REPAIR_SOURCES | frozenset({
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'docs/HANDOFF.md', 'docs/COH-Atlas-Gameplay-0.13.12-testing.txt',
    'docs/android-evidence/levelup-ui-repair-0.13.12-publication.json',
    'docs/android-evidence/levelup-ui-repair-0.13.11-device-result.json',
    'docs/android-evidence/levelup-ui-repair-0.13.12-assets.json',
})


REOPEN_STARTUP_REPAIR_SOURCES = frozenset({
    '.github/workflows/android-reopen-startup-repair.yml',
    'tools/android/interactive/build_reopen_startup_repair_apk.py',
    'tools/android/interactive/qualify_reopen_startup_repair.py',
    'tools/android/interactive/test_reopen_startup_repair_package.py',
    'tools/android/interactive/test_reopen_dbserver_thread_name.py',
    'patches/levelup-ui-repair/0001-pg-empty-row-witness.patch',
    'tools/android/interactive/package_levelup_ui_repair_dbserver.py',
    'tools/android/interactive/test_levelup_ui_repair_dbserver.py',
    'tools/android/interactive/test_levelup_ui_repair_contract.py',
    'android/guest/local_character_server.py',
    'tools/android/game/test_game_diagnostic.py',
})
REOPEN_STARTUP_REPAIR_DOCS = frozenset({
    'docs/HANDOFF.md', 'docs/ANDROID_REOPEN_STARTUP_REPAIR.md',
    'docs/COH-Atlas-Gameplay-0.13.13-testing.txt',
    'docs/ANDROID_CHARACTER_REOPEN.md', 'docs/ANDROID_THOR_ACCEPTANCE.md',
    'docs/ANDROID_INTERACTIVE_DIAGNOSTIC.md',
    'docs/android-evidence/reopen-startup-repair-0.13.12-device-result.json',
    'docs/android-evidence/reopen-startup-repair-0.13.13-publication.json',
})
REOPEN_STARTUP_REPAIR_ALLOWED = REOPEN_STARTUP_REPAIR_SOURCES | REOPEN_STARTUP_REPAIR_DOCS | frozenset({
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
})

UI_BEACON_SOURCES = frozenset({
    '.github/workflows/android-ui-beacon.yml',
    '.github/workflows/android-ui-beacon-public-audit.yml',
    '.github/workflows/android-atlas-beacon-generation.yml',
    '.github/workflows/android-atlas-beacon-verification.yml',
    'tools/android/interactive/build_ui_beacon_apk.py',
    'tools/android/interactive/qualify_ui_beacon.py',
    'tools/android/interactive/test_ui_beacon_package.py',
    'tools/android/interactive/discover_client_ui_sweep_assets.py',
    'tools/android/interactive/prepare_client_ui_sweep_assets.py',
    'tools/android/interactive/test_client_ui_sweep_assets.py',
    'tools/android/interactive/test_client_ui_repair_assets.py',
    'tools/prepare_atlas_beacon_generator_source.py',
    'patches/atlas-beacons/0001-host-only-atlas-generator.patch',
    'tools/android/interactive/fixtures/thor-training-normalization-0.13.13-20261005.json',
    'tools/android/interactive/generate_atlas_beacons.py',
    'tools/android/interactive/test_atlas_beacon_package.py',
    'tools/android/interactive/test_beacon_runtime_profiles.py',
    'tools/android/interactive/test_server_worktree_reuse.py',
    'tools/android/interactive/test_generate_atlas_beacons.py',
    'tools/test_prepare_atlas_beacon_generator_source.py',
    'android/guest/atlas_beacon_package.py',
    'assets/client-ui-sweep-manifest.json', 'assets/client-ui-sweep-requests.json',
    'assets/client-ui-sweep-plan.json',
    'android/guest/client_visual_assets.py', 'android/guest/native_training_save.py',
    'android/guest/local_character_server.py',
    'tools/android/interactive/test_training_save.py',
    'tools/android/interactive/test_character_reopen_guest.py',
    'tools/android/interactive/test_combat_reward_save.py',
})
UI_BEACON_DOCS = frozenset({
    'docs/HANDOFF.md', 'docs/ANDROID_UI_BEACON.md', 'docs/ANDROID_TRAINING_VALIDATION_REPAIR.md', 'docs/ANDROID_UI_BEACON_DEVICE_RESULT.md', 'docs/ANDROID_ATLAS_BEACONS.md', 'docs/ANDROID_UI_TEXTURE_SWEEP.md',
    'docs/COH-Atlas-Gameplay-0.13.14-testing.txt',
    'docs/ANDROID_CHARACTER_REOPEN.md', 'docs/ANDROID_THOR_ACCEPTANCE.md',
    'docs/ANDROID_INTERACTIVE_DIAGNOSTIC.md',
    'docs/android-evidence/ui-beacon-0.13.13-device-result.json',
    'docs/android-evidence/ui-beacon-0.13.14-assets.json',
    'docs/android-evidence/ui-beacon-0.13.14-publication.json',
})
UI_BEACON_ALLOWED = UI_BEACON_SOURCES | UI_BEACON_DOCS | frozenset({
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
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


# Exact guest-only performance scope. A mixed native/asset change falls back to
# historical full qualification; only an immediate-parent push may skip it.
PERFORMANCE_SOURCES = frozenset({
    '.github/workflows/android-thor-performance.yml',
    'tools/android/interactive/build_thor_performance_apk.py',
    'tools/android/interactive/qualify_thor_performance.py',
    'tools/android/interactive/test_thor_performance_package.py',
    'tools/android/interactive/analyze_thor_performance.py',
    'tools/android/interactive/test_thor_performance_report.py',
    'tools/android/interactive/test_character_readiness.py',
    'tools/android/interactive/test_character_server.py',
    'tools/android/interactive/test_character_map_data.py',
    'tools/android/interactive/test_server_worktree_reuse.py',
    'android/guest/client_interactive_diagnostic.py',
    'android/guest/local_character_server.py',
    'android/guest/local_login_server.py',
    'android/guest/character_server_data_cache.py',
})
PERFORMANCE_ALLOWED = PERFORMANCE_SOURCES | frozenset({
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'docs/HANDOFF.md', 'docs/COH-PERFORMANCE-0.13.15.md',
    'docs/COH-Atlas-Gameplay-0.13.15-testing.txt',
    'docs/android-evidence/performance-0.13.14-thor-20261006.json',
    'docs/android-evidence/performance-0.13.15-publication.json',
})


# Finite Game-only continuation: this scope never permits a server, renderer,
# runtime, Java, asset or imported-source mutation to bypass its owner workflow.
SCENE_PERFORMANCE_SOURCES = frozenset({
    '.github/workflows/android-client-scene-performance.yml',
    'tools/android/interactive/package_client_scene_performance_native.py',
    'tools/android/interactive/build_client_scene_performance_apk.py',
    'tools/android/interactive/qualify_client_scene_performance.py',
    'tools/android/interactive/test_client_scene_performance_package.py',
    'tools/android/interactive/test_client_scene_performance_native.py',
    'tools/android/interactive/test_client_scene_performance_contract.py',
    'tools/android/interactive/test_client_preload_launch.py',
    'tools/android/interactive/test_client_frame_timing_native.py',
    'tools/android/interactive/test_client_frame_timing_source.py',
    'patches/client-scene-performance/0001-scene-loading-phase-and-preload.patch',
    'patches/client-scene-performance/0002-native-frame-timing.patch',
    'android/native/client-scene-performance/cohClientSceneTiming.h',
    'database/client-scene-performance/overlay/Game/src/cohClientFrameTiming.h',
    'android/guest/client_interactive_diagnostic.py',
    'android/guest/native_responsiveness_contract.py',
    'android/guest/client_startup_diagnostic.py',
    'android/guest/texture_header_index.py',
    'tools/android/interactive/analyze_client_scene_performance.py',
    'tools/android/interactive/test_client_scene_performance_report.py',
    'tools/android/interactive/analyze_thor_performance.py',
    'tools/android/interactive/test_thor_performance_report.py',
})
SCENE_PERFORMANCE_ALLOWED = SCENE_PERFORMANCE_SOURCES | frozenset({
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'docs/HANDOFF.md', 'docs/COH-PERFORMANCE-0.13.16.md',
    'docs/COH-Atlas-Gameplay-0.13.16-testing.txt',
    'docs/android-evidence/performance-0.13.15-thor-20261007.json',
    'docs/android-evidence/performance-0.13.16-publication.json',
})


# The 30 FPS experiment is a separate, source-bound Game continuation. Directory
# globs deliberately do not belong here: an unreviewed patch/header or a mixed
# server/runtime/Java/asset change still requests historical full qualification.
GAMEPLAY_PERFORMANCE_SOURCES = frozenset({
    '.github/workflows/android-client-gameplay-performance.yml',
    'tools/android/interactive/package_client_gameplay_performance_native.py',
    'tools/android/interactive/build_client_gameplay_performance_apk.py',
    'tools/android/interactive/qualify_client_gameplay_performance.py',
    'tools/android/interactive/test_client_gameplay_performance_package.py',
    'tools/android/interactive/test_client_gameplay_performance_native.py',
    'tools/android/interactive/test_client_gameplay_performance_source.py',
    'tools/android/interactive/test_client_gameplay_performance_contract.py',
    'patches/client-gameplay-performance/0001-gameplay-cap-and-texture-diagnostics.patch',
    'database/client-gameplay-performance/overlay/Game/src/cohClientGameplayPerformance.h',
    'android/guest/client_interactive_diagnostic.py',
    'android/guest/native_responsiveness_contract.py',
    'android/guest/client_startup_diagnostic.py',
    'android/guest/texture_header_index.py',
})
GAMEPLAY_PERFORMANCE_ALLOWED = GAMEPLAY_PERFORMANCE_SOURCES | frozenset({
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'docs/HANDOFF.md', 'docs/COH-PERFORMANCE-0.13.17.md',
    'docs/COH-Atlas-Gameplay-0.13.17-testing.txt',
    'docs/android-evidence/performance-0.13.16-thor-20261007.json',
    'docs/android-evidence/performance-0.13.17-publication.json',
})


# Android sidebar/input repair owns exactly these five Java sources. Native,
# guest, runtime, resource and other Java mutations cannot join this lane.
SIDEBAR_SOURCES = frozenset({
    '.github/workflows/android-client-sidebar.yml',
    'tools/android/interactive/build_client_sidebar_apk.py',
    'tools/android/interactive/qualify_client_sidebar.py',
    'tools/android/interactive/test_client_sidebar_package.py',
    'tools/android/interactive/test_client_sidebar_commands.py',
    'tools/android/interactive/test_client_sidebar_runtime.py',
    'tools/android/interactive/test_input.py',
    JAVA+'ClientActivity.java', JAVA+'ClientInput.java', JAVA+'InteractiveRfbClient.java',
    JAVA+'ClientRuntime.java', JAVA+'ClientService.java',
})
SIDEBAR_ALLOWED = SIDEBAR_SOURCES | frozenset({
    # The retained host fixture must declare the new production pending-command
    # field. It is a reviewed companion, never a sidebar owner marker by itself.
    'tools/android/interactive/test_fresh_profile_recovery.py',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'docs/HANDOFF.md', 'docs/COH-CLIENT-SIDEBAR-0.13.18.md',
    'docs/COH-Atlas-Gameplay-0.13.18-testing.txt',
    'docs/android-evidence/client-sidebar-0.13.17-thor-20261007.json',
    'docs/android-evidence/client-sidebar-0.13.18-publication.json',
})


# This continuation appends one source-bound Game renderer attribution layer,
# four reviewed Android capture/report sources and the exact guest safety
# helpers. No directory glob or inherited broad scope can join this owner.
RENDERER_ATTRIBUTION_SOURCES = frozenset({
    '.github/workflows/android-client-renderer-attribution.yml',
    'tools/android/interactive/package_client_renderer_attribution_native.py',
    'tools/android/interactive/build_client_renderer_attribution_apk.py',
    'tools/android/interactive/qualify_client_renderer_attribution.py',
    'tools/android/interactive/test_client_renderer_attribution_package.py',
    'tools/android/interactive/test_client_renderer_attribution_native.py',
    'tools/android/interactive/test_client_renderer_attribution_source.py',
    'tools/android/interactive/test_client_renderer_attribution_contract.py',
    'patches/client-renderer-attribution/0001-renderer-attribution-and-visible-fps.patch',
    'database/client-renderer-attribution/overlay/Game/src/cohClientRendererAttribution.h',
    JAVA+'ClientActivity.java', JAVA+'ClientRuntime.java',
    JAVA+'ClientService.java', JAVA+'ClientSurface.java',
    'tools/android/interactive/test_client_surface_capture.py',
    'tools/android/interactive/test_client_capture_metrics.py',
    'android/guest/native_responsiveness_contract.py',
    'android/guest/client_startup_diagnostic.py',
    'android/guest/texture_header_index.py',
    'android/guest/local_character_server.py',
    'tools/android/interactive/test_stock_power_delta.py',
})
RENDERER_ATTRIBUTION_DOCS = frozenset({
    'docs/HANDOFF.md',
    'docs/android-evidence/renderer-attribution-0.13.19-publication.json',
})
RENDERER_ATTRIBUTION_ALLOWED = RENDERER_ATTRIBUTION_SOURCES | RENDERER_ATTRIBUTION_DOCS | frozenset({
    # This retained setup fixture now models the reviewed Surface cancellation
    # API. It may accompany this lane but keeps its old owner when edited alone.
    'tools/android/interactive/test_setup_service.py',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'docs/COH-PERFORMANCE-0.13.19.md',
    'docs/COH-Atlas-Gameplay-0.13.19-testing.txt',
    'docs/android-evidence/renderer-attribution-0.13.18-thor-20261008.json',
})



# The opt-in GPU experiment reuses the complete audited .19 Game/client stack.
# Only these exact Android/helper/driver-producer files may join this owner.
GPU_PROFILE_SOURCES = frozenset({
    '.github/workflows/android-client-gpu-profile.yml',
    'tools/android/interactive/build_client_gpu_profile_apk.py',
    'tools/android/interactive/qualify_client_gpu_profile.py',
    'tools/android/interactive/package_client_gpu_runtime.py',
    'tools/android/interactive/test_client_gpu_profile_package.py',
    'tools/android/interactive/test_client_gpu_profile.py',
    'tools/android/interactive/test_client_gpu_runtime_package.py',
    'tools/android/interactive/test_coh_vulkan_gpu_probe.py',
    'tools/android/interactive/test_coh_gpu_probe_native.py',
    'tools/android/gpu-runtime/Dockerfile',
    'tools/android/gpu-runtime/lock.json',
    'tools/android/gpu-runtime/base-abi.json',
    'tools/android/gpu-runtime/build.py',
    'android/native/coh-gpu-probe.c',
    'android/native/coh-vulkan-gpu-probe.c',
    JAVA+'ClientActivity.java', JAVA+'ClientRuntime.java',
    'android/guest/client_gpu_profile.py',
    'android/guest/client_startup_diagnostic.py',
    'android/guest/client_interactive_diagnostic.py',
})
# Existing shared Android/helper paths retain their prior owner when edited
# alone. An explicit new GPU source must accompany this new qualification lane.
GPU_PROFILE_MARKERS = GPU_PROFILE_SOURCES - frozenset({
    JAVA+'ClientActivity.java', JAVA+'ClientRuntime.java',
    'android/guest/client_startup_diagnostic.py',
    'android/guest/client_interactive_diagnostic.py',
})
GPU_PROFILE_DOCS = frozenset({'docs/HANDOFF.md',
    'docs/android-evidence/gpu-profile-0.13.20-publication.json'})
GPU_PROFILE_ALLOWED = GPU_PROFILE_SOURCES | GPU_PROFILE_DOCS | frozenset({
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'docs/COH-PERFORMANCE-0.13.20.md',
    'docs/COH-Atlas-Gameplay-0.13.20-testing.txt',
    'docs/android-evidence/gpu-profile-0.13.19-thor-20261008.json',
})


# Exact .22 Game/guest continuation and its host-only publication recovery.
# The owner authenticates retained .21 bytes and any reused native artifact;
# historical publishers must not rebuild those inputs. Shared guest helpers
# edited alone retain their previous owners, and unknown neighbors fail closed.
RENDER_PIPELINE_SOURCES = frozenset({
    '.github/workflows/android-client-render-pipeline.yml',
    'tools/android/interactive/package_client_render_pipeline_native.py',
    'tools/android/interactive/build_client_render_pipeline_apk.py',
    'tools/android/interactive/qualify_client_render_pipeline.py',
    'tools/android/interactive/analyze_client_render_pipeline.py',
    'tools/android/interactive/test_client_render_pipeline_contract.py',
    'tools/android/interactive/test_client_render_pipeline_guest.py',
    'tools/android/interactive/test_client_render_pipeline_native.py',
    'tools/android/interactive/test_client_render_pipeline_package.py',
    'tools/android/interactive/test_client_render_pipeline_report.py',
    'tools/android/interactive/test_client_render_pipeline_source.py',
    'patches/client-render-pipeline/0001-render-worker-wake-and-focused-timing.patch',
    'database/client-render-pipeline/overlay/Game/src/cohClientRenderPipeline.h',
    'android/guest/client_gpu_profile.py',
    'android/guest/client_startup_diagnostic.py',
    'android/guest/native_responsiveness_contract.py',
    'android/guest/texture_header_index.py',
})
RENDER_PIPELINE_MARKERS = RENDER_PIPELINE_SOURCES - frozenset({
    'android/guest/client_gpu_profile.py',
    'android/guest/client_startup_diagnostic.py',
    'android/guest/native_responsiveness_contract.py',
    'android/guest/texture_header_index.py',
})
RENDER_PIPELINE_DOCS = frozenset({
    'docs/HANDOFF.md',
    'docs/android-evidence/render-pipeline-0.13.22-publication.json',
})
RENDER_PIPELINE_ALLOWED = RENDER_PIPELINE_SOURCES | RENDER_PIPELINE_DOCS | frozenset({
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'docs/COH-PERFORMANCE-0.13.22.md',
    'docs/COH-Atlas-Gameplay-0.13.22-testing.txt',
    'docs/android-evidence/renderer-sync-0.13.21-thor-20261009.json',
})


# .23 is exactly a three-helper session repair over the completed .22 Game.
# A shared helper/test alone keeps its historical owner; unknown native, Android
# or asset neighbors cannot defer the historical qualification workflows.
SESSION_REPAIR_SOURCES = frozenset({
    '.github/workflows/android-client-session-repair.yml',
    'tools/android/interactive/build_client_session_repair_apk.py',
    'tools/android/interactive/qualify_client_session_repair.py',
    'tools/android/interactive/test_client_session_repair_package.py',
    'tools/android/interactive/test_client_session_repair_java.py',
    'tools/android/interactive/test_session_budget_guest.py',
    'tools/android/interactive/test_character_reopen_guest.py',
    'tools/android/interactive/test_client_render_pipeline_guest.py',
    'android/guest/client_interactive_diagnostic.py',
    'android/guest/character_reopen_diagnostic.py',
    'android/guest/character_session_budget.py',
})
SESSION_REPAIR_MARKERS = frozenset({
    '.github/workflows/android-client-session-repair.yml',
    'tools/android/interactive/build_client_session_repair_apk.py',
    'tools/android/interactive/qualify_client_session_repair.py',
    'tools/android/interactive/test_client_session_repair_package.py',
    'tools/android/interactive/test_client_session_repair_java.py',
})
SESSION_REPAIR_DOCS = frozenset({
    'docs/HANDOFF.md', 'docs/COH-PERFORMANCE-0.13.23.md',
    'docs/android-evidence/session-repair-0.13.23-publication.json',
})
SESSION_REPAIR_ALLOWED = SESSION_REPAIR_SOURCES | SESSION_REPAIR_DOCS | frozenset({
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'docs/COH-Atlas-Gameplay-0.13.23-testing.txt',
    'docs/android-evidence/session-repair-0.13.22-thor-20261009.json',
})


# .25 appends the reviewed Game queue layer over the exact .24 Android shell.
# Shared guest readers require a marker; Java/GPU/server/asset changes are excluded.
RENDER_QUEUE_HELPERS = frozenset({
    'android/guest/native_responsiveness_contract.py',
    'android/guest/client_startup_diagnostic.py',
    'android/guest/client_gpu_profile.py',
    'android/guest/texture_header_index.py',
})
RENDER_QUEUE_SOURCES = RENDER_QUEUE_HELPERS | frozenset({
    '.github/workflows/android-client-render-queue.yml',
    'patches/client-render-queue/0001-coalesce-render-worker-wake-and-sparse-queue-timing.patch',
    'database/client-render-queue/overlay/Game/src/cohClientRenderQueue.h',
    'tools/android/interactive/package_client_render_queue_native.py',
    'tools/android/interactive/build_client_render_queue_apk.py',
    'tools/android/interactive/qualify_client_render_queue.py',
    'tools/android/interactive/test_client_render_queue_native.py',
    'tools/android/interactive/test_client_render_queue_source.py',
    'tools/android/interactive/test_client_render_queue_worker.py',
    'tools/android/interactive/test_client_render_queue_contract.py',
    'tools/android/interactive/test_client_render_queue_package.py',
    'tools/android/interactive/test_client_render_queue_guest.py',
    'tools/android/interactive/analyze_client_render_queue.py',
    'tools/android/interactive/test_analyze_client_render_queue.py',
})
RENDER_QUEUE_MARKERS = RENDER_QUEUE_SOURCES - RENDER_QUEUE_HELPERS
# A source-equivalent host correction must explicitly reuse its completed Game.
# Only these finite native producer inputs permit an automatic new Game build.
RENDER_QUEUE_NATIVE_INPUTS = frozenset({
    'patches/client-render-queue/0001-coalesce-render-worker-wake-and-sparse-queue-timing.patch',
    'database/client-render-queue/overlay/Game/src/cohClientRenderQueue.h',
    'tools/android/interactive/package_client_render_queue_native.py',
    'tools/android/interactive/test_client_render_queue_native.py',
    'tools/android/interactive/test_client_render_queue_source.py',
    'tools/android/interactive/test_client_render_queue_worker.py',
})
RENDER_QUEUE_DOCS = frozenset({'docs/HANDOFF.md','docs/COH-PERFORMANCE-0.13.25.md',
    'docs/android-evidence/render-queue-0.13.25-publication.json'})
RENDER_QUEUE_ALLOWED = RENDER_QUEUE_SOURCES | RENDER_QUEUE_DOCS | frozenset({
    'tools/android/interactive/test_client_render_pipeline_package.py',
    'tools/android/interactive/test_client_session_repair_package.py',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'docs/COH-Atlas-Gameplay-0.13.25-testing.txt',
    'docs/android-evidence/render-queue-0.13.24-thor-20261009.json',
})


def render_queue_push(event,before,head,parent,names):
    return bool(bounded_push(event,before,head,parent,names,RENDER_QUEUE_ALLOWED)
        and set(names)&RENDER_QUEUE_MARKERS)


def render_queue_native_push(event,before,head,parent,names):
    return bool(render_queue_push(event,before,head,parent,names)
        and set(names)&RENDER_QUEUE_NATIVE_INPUTS)


def render_queue_docs(event,before,head,parent,names):
    return bool(bounded_push(event,before,head,parent,names,RENDER_QUEUE_DOCS)
        and 'docs/android-evidence/render-queue-0.13.25-publication.json' in names)


def render_queue_owned(event,before,head,parent,names):
    return render_queue_push(event,before,head,parent,names) or render_queue_docs(event,before,head,parent,names)


# .24 recompiles only the reviewed setup Java shell. Runtime/native/guest/asset
# mutations cannot join this lane; existing shared paths require a new marker.
SETUP_COPY_SOURCES = frozenset({
    '.github/workflows/android-setup-copy-repair.yml',
    'tools/android/interactive/build_setup_copy_repair_apk.py',
    'tools/android/interactive/qualify_setup_copy_repair.py',
    'tools/android/interactive/test_setup_copy_repair_package.py',
    'tools/android/interactive/test_setup_copy_memory.py',
    'tools/android/interactive/test_setup_io_memory.py',
    'tools/android/interactive/test_runtime_setup_reuse.py',
    'tools/android/interactive/test_setup_service.py',
    'tools/android/test_setup_memory_guard.py',
    JAVA+'ClientRuntime.java', JAVA+'ClientService.java',
    'android/app/src/main/java/io/github/russianranger/cohdiagnostic/DiagnosticRuntime.java',
    'android/app/src/main/java/io/github/russianranger/cohdiagnostic/SetupMemoryGuard.java',
})
SETUP_COPY_MARKERS = frozenset({
    '.github/workflows/android-setup-copy-repair.yml',
    'tools/android/interactive/build_setup_copy_repair_apk.py',
    'tools/android/interactive/qualify_setup_copy_repair.py',
    'tools/android/interactive/test_setup_copy_repair_package.py',
    'tools/android/interactive/test_setup_copy_memory.py',
    'tools/android/interactive/test_setup_io_memory.py',
})
SETUP_COPY_DOCS = frozenset({'docs/HANDOFF.md','docs/COH-SETUP-COPY-0.13.24.md',
    'docs/android-evidence/setup-copy-0.13.24-publication.json'})
SETUP_COPY_ALLOWED = SETUP_COPY_SOURCES | SETUP_COPY_DOCS | frozenset({
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'docs/COH-Atlas-Gameplay-0.13.24-testing.txt',
    'docs/android-evidence/setup-copy-0.13.23-thor-20261009.json',
})


def setup_copy_push(event,before,head,parent,names):
    return bool(bounded_push(event,before,head,parent,names,SETUP_COPY_ALLOWED)
        and set(names)&SETUP_COPY_MARKERS)


def setup_copy_docs(event,before,head,parent,names):
    return bool(bounded_push(event,before,head,parent,names,SETUP_COPY_DOCS)
        and 'docs/android-evidence/setup-copy-0.13.24-publication.json' in names)


def setup_copy_owned(event,before,head,parent,names):
    return setup_copy_push(event,before,head,parent,names) or setup_copy_docs(event,before,head,parent,names)


def session_repair_push(event, before, head, parent, names):
    return bool(bounded_push(event, before, head, parent, names, SESSION_REPAIR_ALLOWED)
        and set(names) & SESSION_REPAIR_MARKERS)


def session_repair_docs(event, before, head, parent, names):
    return bool(bounded_push(event, before, head, parent, names, SESSION_REPAIR_DOCS)
        and 'docs/android-evidence/session-repair-0.13.23-publication.json' in names)


def session_repair_owned(event, before, head, parent, names):
    return session_repair_push(event, before, head, parent, names) or session_repair_docs(
        event, before, head, parent, names)


def render_pipeline_push(event, before, head, parent, names):
    return bool(bounded_push(event, before, head, parent, names, RENDER_PIPELINE_ALLOWED)
        and set(names) & RENDER_PIPELINE_MARKERS)


def render_pipeline_docs(event, before, head, parent, names):
    return bool(bounded_push(event, before, head, parent, names, RENDER_PIPELINE_DOCS)
        and 'docs/android-evidence/render-pipeline-0.13.22-publication.json' in names)


def render_pipeline_owned(event, before, head, parent, names):
    return render_pipeline_push(event, before, head, parent, names) or render_pipeline_docs(
        event, before, head, parent, names)


def gpu_profile_push(event, before, head, parent, names):
    return bool(bounded_push(event, before, head, parent, names, GPU_PROFILE_ALLOWED)
        and set(names) & GPU_PROFILE_MARKERS)


def gpu_profile_docs(event, before, head, parent, names):
    return bool(bounded_push(event, before, head, parent, names, GPU_PROFILE_DOCS)
        and 'docs/android-evidence/gpu-profile-0.13.20-publication.json' in names)

def bounded_push(event, before, head, parent, names, allowed=ALLOWED):
    return bool(event == 'push' and re.fullmatch('[0-9a-f]{40}', before or '')
        and re.fullmatch('[0-9a-f]{40}', head or '')
        and before != '0'*40 and before == parent and head != before
        and names and set(names) <= allowed)


def renderer_attribution_push(event, before, head, parent, names):
    if gpu_profile_push(event, before, head, parent, names) or gpu_profile_docs(event, before, head, parent, names): return False
    return bool(bounded_push(event, before, head, parent, names, RENDERER_ATTRIBUTION_ALLOWED)
        and set(names) & RENDERER_ATTRIBUTION_SOURCES)


def renderer_attribution_docs(event, before, head, parent, names):
    return bool(bounded_push(event, before, head, parent, names, RENDERER_ATTRIBUTION_DOCS)
        and 'docs/android-evidence/renderer-attribution-0.13.19-publication.json' in names)


def sidebar_push(event, before, head, parent, names):
    if gpu_profile_push(event, before, head, parent, names) or gpu_profile_docs(event, before, head, parent, names): return False
    if renderer_attribution_push(event, before, head, parent, names) or renderer_attribution_docs(event, before, head, parent, names): return False
    return bool(bounded_push(event, before, head, parent, names, SIDEBAR_ALLOWED)
        and set(names) & SIDEBAR_SOURCES)


def sidebar_docs(event, before, head, parent, names):
    return bool(bounded_push(event, before, head, parent, names,
        {'docs/HANDOFF.md', 'docs/android-evidence/client-sidebar-0.13.18-publication.json'})
        and 'docs/android-evidence/client-sidebar-0.13.18-publication.json' in names)


def gameplay_performance_push(event, before, head, parent, names):
    if gpu_profile_push(event, before, head, parent, names) or gpu_profile_docs(event, before, head, parent, names): return False
    if renderer_attribution_push(event, before, head, parent, names) or renderer_attribution_docs(event, before, head, parent, names): return False
    return bool(bounded_push(event, before, head, parent, names, GAMEPLAY_PERFORMANCE_ALLOWED)
        and set(names) & GAMEPLAY_PERFORMANCE_SOURCES)


def gameplay_performance_docs(event, before, head, parent, names):
    return bool(bounded_push(event, before, head, parent, names,
        {'docs/HANDOFF.md', 'docs/android-evidence/performance-0.13.17-publication.json'})
        and 'docs/android-evidence/performance-0.13.17-publication.json' in names)


def scene_performance_push(event, before, head, parent, names):
    if gpu_profile_push(event, before, head, parent, names) or gpu_profile_docs(event, before, head, parent, names): return False
    if renderer_attribution_push(event, before, head, parent, names) or renderer_attribution_docs(event, before, head, parent, names): return False
    return bool(bounded_push(event, before, head, parent, names, SCENE_PERFORMANCE_ALLOWED)
        and set(names) & SCENE_PERFORMANCE_SOURCES)


def scene_performance_docs(event, before, head, parent, names):
    return bool(bounded_push(event, before, head, parent, names,
        {'docs/HANDOFF.md', 'docs/android-evidence/performance-0.13.16-publication.json'})
        and 'docs/android-evidence/performance-0.13.16-publication.json' in names)


def performance_push(event, before, head, parent, names):
    if gpu_profile_push(event, before, head, parent, names) or gpu_profile_docs(event, before, head, parent, names): return False
    if renderer_attribution_push(event, before, head, parent, names) or renderer_attribution_docs(event, before, head, parent, names): return False
    return bool(bounded_push(event, before, head, parent, names, PERFORMANCE_ALLOWED)
        and set(names) & PERFORMANCE_SOURCES)


def startup_push(event, before, head, parent, names):
    return bool(bounded_push(event, before, head, parent, names, STARTUP_ALLOWED)
        and set(names) & STARTUP_SOURCES)


def receipt_push(event, before, head, parent, names):
    return bool(bounded_push(event, before, head, parent, names, RECEIPT_ALLOWED)
        and set(names) & RECEIPT_SOURCES)


def setup_push(event, before, head, parent, names):
    return bool(bounded_push(event, before, head, parent, names, SETUP_ALLOWED)
        and set(names) & SETUP_SOURCES)


def bundle_push(event, before, head, parent, names):
    return bool(bounded_push(event, before, head, parent, names, BUNDLE_ALLOWED)
        and set(names) & BUNDLE_SOURCES)


def visual_push(event, before, head, parent, names):
    return bool(bounded_push(event, before, head, parent, names, VISUAL_ALLOWED)
        and set(names) & VISUAL_SOURCES)


def client_loading_push(event, before, head, parent, names):
    return bool(bounded_push(event, before, head, parent, names, CLIENT_LOADING_ALLOWED)
        and set(names) & CLIENT_LOADING_SOURCES)


def client_streaming_push(event, before, head, parent, names):
    return bool(bounded_push(event, before, head, parent, names, CLIENT_STREAMING_ALLOWED)
        and set(names) & CLIENT_STREAMING_SOURCES)


def client_asset_closure_push(event, before, head, parent, names):
    return bool(bounded_push(event, before, head, parent, names, CLIENT_ASSET_CLOSURE_ALLOWED)
        and set(names) & CLIENT_ASSET_CLOSURE_SOURCES)


def client_startup_followup_push(event, before, head, parent, names):
    return bool(bounded_push(event, before, head, parent, names, CLIENT_STARTUP_FOLLOWUP_ALLOWED)
        and set(names) & CLIENT_STARTUP_FOLLOWUP_SOURCES)


def levelup_ui_repair_docs(event, before, head, parent, names):
    reviewed = {'docs/HANDOFF.md', 'docs/COH-Atlas-Gameplay-0.13.12-testing.txt',
        'docs/android-evidence/levelup-ui-repair-0.13.12-publication.json'}
    return bool(bounded_push(event, before, head, parent, names, reviewed)
        and 'docs/android-evidence/levelup-ui-repair-0.13.12-publication.json' in names)



def ui_beacon_docs(event, before, head, parent, names):
    return bool(bounded_push(event, before, head, parent, names, UI_BEACON_DOCS)
        and 'docs/android-evidence/ui-beacon-0.13.14-publication.json' in names)


def ui_beacon_push(event, before, head, parent, names):
    return bool((bounded_push(event, before, head, parent, names, UI_BEACON_ALLOWED)
        and set(names) & UI_BEACON_SOURCES) or ui_beacon_docs(event, before, head, parent, names))


def ui_beacon_required(event, before, head, parent, names):
    if render_queue_owned(event, before, head, parent, names): return False
    if setup_copy_owned(event, before, head, parent, names): return False
    if session_repair_owned(event, before, head, parent, names): return False
    if render_pipeline_owned(event, before, head, parent, names): return False
    if gpu_profile_push(event, before, head, parent, names) or gpu_profile_docs(event, before, head, parent, names): return False
    if renderer_attribution_push(event, before, head, parent, names) or renderer_attribution_docs(event, before, head, parent, names): return False
    if sidebar_push(event, before, head, parent, names) or sidebar_docs(event, before, head, parent, names): return False
    if gameplay_performance_push(event, before, head, parent, names) or gameplay_performance_docs(event, before, head, parent, names): return False
    if scene_performance_push(event, before, head, parent, names) or scene_performance_docs(event, before, head, parent, names): return False
    if performance_push(event, before, head, parent, names): return False
    return not ui_beacon_docs(event, before, head, parent, names)


def reopen_startup_repair_docs(event, before, head, parent, names):
    return bool(bounded_push(event, before, head, parent, names, REOPEN_STARTUP_REPAIR_DOCS)
        and 'docs/android-evidence/reopen-startup-repair-0.13.13-publication.json' in names)


def reopen_startup_repair_push(event, before, head, parent, names):
    return bool((bounded_push(event, before, head, parent, names, REOPEN_STARTUP_REPAIR_ALLOWED)
        and set(names) & REOPEN_STARTUP_REPAIR_SOURCES)
        or reopen_startup_repair_docs(event, before, head, parent, names))


def reopen_startup_repair_required(event, before, head, parent, names):
    if render_queue_owned(event, before, head, parent, names): return False
    if setup_copy_owned(event, before, head, parent, names): return False
    if session_repair_owned(event, before, head, parent, names): return False
    if render_pipeline_owned(event, before, head, parent, names): return False
    if gpu_profile_push(event, before, head, parent, names) or gpu_profile_docs(event, before, head, parent, names): return False
    if renderer_attribution_push(event, before, head, parent, names) or renderer_attribution_docs(event, before, head, parent, names): return False
    if sidebar_push(event, before, head, parent, names) or sidebar_docs(event, before, head, parent, names): return False
    if gameplay_performance_push(event, before, head, parent, names) or gameplay_performance_docs(event, before, head, parent, names): return False
    if scene_performance_push(event, before, head, parent, names) or scene_performance_docs(event, before, head, parent, names): return False
    if performance_push(event, before, head, parent, names): return False
    return not (reopen_startup_repair_docs(event, before, head, parent, names)
        or ui_beacon_push(event, before, head, parent, names))


def levelup_ui_repair_push(event, before, head, parent, names):
    return bool((bounded_push(event, before, head, parent, names, LEVELUP_UI_REPAIR_ALLOWED)
        and set(names) & LEVELUP_UI_REPAIR_SOURCES)
        or levelup_ui_repair_docs(event, before, head, parent, names)
        or reopen_startup_repair_push(event, before, head, parent, names)
        or ui_beacon_push(event, before, head, parent, names))


def task_required(event, before, head, parent, names):
    if render_queue_owned(event, before, head, parent, names): return False
    if setup_copy_owned(event, before, head, parent, names): return False
    if session_repair_owned(event, before, head, parent, names): return False
    if render_pipeline_owned(event, before, head, parent, names): return False
    if gpu_profile_push(event, before, head, parent, names) or gpu_profile_docs(event, before, head, parent, names): return False
    if renderer_attribution_push(event, before, head, parent, names) or renderer_attribution_docs(event, before, head, parent, names): return False
    if sidebar_push(event, before, head, parent, names) or sidebar_docs(event, before, head, parent, names): return False
    if gameplay_performance_push(event, before, head, parent, names) or gameplay_performance_docs(event, before, head, parent, names): return False
    if scene_performance_push(event, before, head, parent, names) or scene_performance_docs(event, before, head, parent, names): return False
    if performance_push(event, before, head, parent, names): return False
    return not ((bounded_push(event, before, head, parent, names)
        and set(names) & (STORAGE_SOURCES | RECOVERY_SOURCES))
        or startup_push(event, before, head, parent, names)
        or receipt_push(event, before, head, parent, names)
        or setup_push(event, before, head, parent, names)
        or bundle_push(event, before, head, parent, names)
        or visual_push(event, before, head, parent, names)
        or client_loading_push(event, before, head, parent, names)
        or client_streaming_push(event, before, head, parent, names)
        or client_asset_closure_push(event, before, head, parent, names)
        or client_startup_followup_push(event, before, head, parent, names)
        or levelup_ui_repair_push(event, before, head, parent, names))


def cleanup_required(event, before, head, parent, names):
    if render_queue_owned(event, before, head, parent, names): return False
    if setup_copy_owned(event, before, head, parent, names): return False
    if session_repair_owned(event, before, head, parent, names): return False
    if render_pipeline_owned(event, before, head, parent, names): return False
    if gpu_profile_push(event, before, head, parent, names) or gpu_profile_docs(event, before, head, parent, names): return False
    if renderer_attribution_push(event, before, head, parent, names) or renderer_attribution_docs(event, before, head, parent, names): return False
    if sidebar_push(event, before, head, parent, names) or sidebar_docs(event, before, head, parent, names): return False
    if gameplay_performance_push(event, before, head, parent, names) or gameplay_performance_docs(event, before, head, parent, names): return False
    if scene_performance_push(event, before, head, parent, names) or scene_performance_docs(event, before, head, parent, names): return False
    if performance_push(event, before, head, parent, names): return False
    """Keep historical 0.13.1 publication out of a qualified recovery derivative."""
    return not ((bounded_push(event, before, head, parent, names)
        and set(names) & RECOVERY_SOURCES) or startup_push(event, before, head, parent, names)
        or receipt_push(event, before, head, parent, names)
        or setup_push(event, before, head, parent, names)
        or bundle_push(event, before, head, parent, names)
        or visual_push(event, before, head, parent, names)
        or client_loading_push(event, before, head, parent, names)
        or client_streaming_push(event, before, head, parent, names)
        or client_asset_closure_push(event, before, head, parent, names)
        or client_startup_followup_push(event, before, head, parent, names)
        or levelup_ui_repair_push(event, before, head, parent, names))


def recovery_required(event, before, head, parent, names):
    if render_queue_owned(event, before, head, parent, names): return False
    if setup_copy_owned(event, before, head, parent, names): return False
    if session_repair_owned(event, before, head, parent, names): return False
    if render_pipeline_owned(event, before, head, parent, names): return False
    if gpu_profile_push(event, before, head, parent, names) or gpu_profile_docs(event, before, head, parent, names): return False
    if renderer_attribution_push(event, before, head, parent, names) or renderer_attribution_docs(event, before, head, parent, names): return False
    if sidebar_push(event, before, head, parent, names) or sidebar_docs(event, before, head, parent, names): return False
    if gameplay_performance_push(event, before, head, parent, names) or gameplay_performance_docs(event, before, head, parent, names): return False
    if scene_performance_push(event, before, head, parent, names) or scene_performance_docs(event, before, head, parent, names): return False
    if performance_push(event, before, head, parent, names): return False
    """The newer source-bound startup derivative owns only its explicit scope."""
    return not (startup_push(event, before, head, parent, names) or receipt_push(event, before, head, parent, names)
        or setup_push(event, before, head, parent, names)
        or bundle_push(event, before, head, parent, names)
        or visual_push(event, before, head, parent, names)
        or client_loading_push(event, before, head, parent, names)
        or client_streaming_push(event, before, head, parent, names)
        or client_asset_closure_push(event, before, head, parent, names)
        or client_startup_followup_push(event, before, head, parent, names)
        or levelup_ui_repair_push(event, before, head, parent, names))


def receipt_required(event, before, head, parent, names):
    if render_queue_owned(event, before, head, parent, names): return False
    if setup_copy_owned(event, before, head, parent, names): return False
    if session_repair_owned(event, before, head, parent, names): return False
    if render_pipeline_owned(event, before, head, parent, names): return False
    if gpu_profile_push(event, before, head, parent, names) or gpu_profile_docs(event, before, head, parent, names): return False
    if renderer_attribution_push(event, before, head, parent, names) or renderer_attribution_docs(event, before, head, parent, names): return False
    if sidebar_push(event, before, head, parent, names) or sidebar_docs(event, before, head, parent, names): return False
    if gameplay_performance_push(event, before, head, parent, names) or gameplay_performance_docs(event, before, head, parent, names): return False
    if scene_performance_push(event, before, head, parent, names) or scene_performance_docs(event, before, head, parent, names): return False
    if performance_push(event, before, head, parent, names): return False
    """Keep the historical 0.13.4 release out of the bounded setup wrapper."""
    return not (setup_push(event, before, head, parent, names) or bundle_push(event, before, head, parent, names)
        or visual_push(event, before, head, parent, names)
        or client_loading_push(event, before, head, parent, names)
        or client_streaming_push(event, before, head, parent, names)
        or client_asset_closure_push(event, before, head, parent, names)
        or client_startup_followup_push(event, before, head, parent, names)
        or levelup_ui_repair_push(event, before, head, parent, names))


def schedule_required(event, before, head, parent, names):
    if render_queue_owned(event, before, head, parent, names): return False
    if setup_copy_owned(event, before, head, parent, names): return False
    if session_repair_owned(event, before, head, parent, names): return False
    if render_pipeline_owned(event, before, head, parent, names): return False
    if gpu_profile_push(event, before, head, parent, names) or gpu_profile_docs(event, before, head, parent, names): return False
    if renderer_attribution_push(event, before, head, parent, names) or renderer_attribution_docs(event, before, head, parent, names): return False
    if sidebar_push(event, before, head, parent, names) or sidebar_docs(event, before, head, parent, names): return False
    if gameplay_performance_push(event, before, head, parent, names) or gameplay_performance_docs(event, before, head, parent, names): return False
    if scene_performance_push(event, before, head, parent, names) or scene_performance_docs(event, before, head, parent, names): return False
    if performance_push(event, before, head, parent, names): return False
    return not (bundle_push(event, before, head, parent, names)
        or visual_push(event, before, head, parent, names)
        or client_loading_push(event, before, head, parent, names)
        or client_streaming_push(event, before, head, parent, names)
        or client_asset_closure_push(event, before, head, parent, names)
        or client_startup_followup_push(event, before, head, parent, names)
        or levelup_ui_repair_push(event, before, head, parent, names))


def setup_required(event, before, head, parent, names):
    if render_queue_owned(event, before, head, parent, names): return False
    if setup_copy_owned(event, before, head, parent, names): return False
    if session_repair_owned(event, before, head, parent, names): return False
    if render_pipeline_owned(event, before, head, parent, names): return False
    if gpu_profile_push(event, before, head, parent, names) or gpu_profile_docs(event, before, head, parent, names): return False
    if renderer_attribution_push(event, before, head, parent, names) or renderer_attribution_docs(event, before, head, parent, names): return False
    if sidebar_push(event, before, head, parent, names) or sidebar_docs(event, before, head, parent, names): return False
    if gameplay_performance_push(event, before, head, parent, names) or gameplay_performance_docs(event, before, head, parent, names): return False
    if scene_performance_push(event, before, head, parent, names) or scene_performance_docs(event, before, head, parent, names): return False
    if performance_push(event, before, head, parent, names): return False
    return not (bundle_push(event, before, head, parent, names)
        or visual_push(event, before, head, parent, names)
        or client_loading_push(event, before, head, parent, names)
        or client_streaming_push(event, before, head, parent, names)
        or client_asset_closure_push(event, before, head, parent, names)
        or client_startup_followup_push(event, before, head, parent, names)
        or levelup_ui_repair_push(event, before, head, parent, names))


def bundle_required(event, before, head, parent, names):
    if render_queue_owned(event, before, head, parent, names): return False
    if setup_copy_owned(event, before, head, parent, names): return False
    if session_repair_owned(event, before, head, parent, names): return False
    if render_pipeline_owned(event, before, head, parent, names): return False
    if gpu_profile_push(event, before, head, parent, names) or gpu_profile_docs(event, before, head, parent, names): return False
    if renderer_attribution_push(event, before, head, parent, names) or renderer_attribution_docs(event, before, head, parent, names): return False
    if sidebar_push(event, before, head, parent, names) or sidebar_docs(event, before, head, parent, names): return False
    if gameplay_performance_push(event, before, head, parent, names) or gameplay_performance_docs(event, before, head, parent, names): return False
    if scene_performance_push(event, before, head, parent, names) or scene_performance_docs(event, before, head, parent, names): return False
    if performance_push(event, before, head, parent, names): return False
    return not (visual_push(event, before, head, parent, names)
        or client_loading_push(event, before, head, parent, names)
        or client_streaming_push(event, before, head, parent, names)
        or client_asset_closure_push(event, before, head, parent, names)
        or client_startup_followup_push(event, before, head, parent, names)
        or levelup_ui_repair_push(event, before, head, parent, names))


def visual_required(event, before, head, parent, names):
    if render_queue_owned(event, before, head, parent, names): return False
    if setup_copy_owned(event, before, head, parent, names): return False
    if session_repair_owned(event, before, head, parent, names): return False
    if render_pipeline_owned(event, before, head, parent, names): return False
    if gpu_profile_push(event, before, head, parent, names) or gpu_profile_docs(event, before, head, parent, names): return False
    if renderer_attribution_push(event, before, head, parent, names) or renderer_attribution_docs(event, before, head, parent, names): return False
    if sidebar_push(event, before, head, parent, names) or sidebar_docs(event, before, head, parent, names): return False
    if gameplay_performance_push(event, before, head, parent, names) or gameplay_performance_docs(event, before, head, parent, names): return False
    if scene_performance_push(event, before, head, parent, names) or scene_performance_docs(event, before, head, parent, names): return False
    if performance_push(event, before, head, parent, names): return False
    return not (client_loading_push(event, before, head, parent, names)
        or client_streaming_push(event, before, head, parent, names)
        or client_asset_closure_push(event, before, head, parent, names)
        or client_startup_followup_push(event, before, head, parent, names)
        or levelup_ui_repair_push(event, before, head, parent, names))


def loading_required(event, before, head, parent, names):
    if render_queue_owned(event, before, head, parent, names): return False
    if setup_copy_owned(event, before, head, parent, names): return False
    if session_repair_owned(event, before, head, parent, names): return False
    if render_pipeline_owned(event, before, head, parent, names): return False
    if gpu_profile_push(event, before, head, parent, names) or gpu_profile_docs(event, before, head, parent, names): return False
    if renderer_attribution_push(event, before, head, parent, names) or renderer_attribution_docs(event, before, head, parent, names): return False
    if sidebar_push(event, before, head, parent, names) or sidebar_docs(event, before, head, parent, names): return False
    if gameplay_performance_push(event, before, head, parent, names) or gameplay_performance_docs(event, before, head, parent, names): return False
    if scene_performance_push(event, before, head, parent, names) or scene_performance_docs(event, before, head, parent, names): return False
    if performance_push(event, before, head, parent, names): return False
    return not (client_streaming_push(event, before, head, parent, names)
        or client_asset_closure_push(event, before, head, parent, names)
        or client_startup_followup_push(event, before, head, parent, names)
        or levelup_ui_repair_push(event, before, head, parent, names))


def streaming_required(event, before, head, parent, names):
    if render_queue_owned(event, before, head, parent, names): return False
    if setup_copy_owned(event, before, head, parent, names): return False
    if session_repair_owned(event, before, head, parent, names): return False
    if render_pipeline_owned(event, before, head, parent, names): return False
    if gpu_profile_push(event, before, head, parent, names) or gpu_profile_docs(event, before, head, parent, names): return False
    if renderer_attribution_push(event, before, head, parent, names) or renderer_attribution_docs(event, before, head, parent, names): return False
    if sidebar_push(event, before, head, parent, names) or sidebar_docs(event, before, head, parent, names): return False
    if gameplay_performance_push(event, before, head, parent, names) or gameplay_performance_docs(event, before, head, parent, names): return False
    if scene_performance_push(event, before, head, parent, names) or scene_performance_docs(event, before, head, parent, names): return False
    if performance_push(event, before, head, parent, names): return False
    return not (client_asset_closure_push(event, before, head, parent, names)
        or client_startup_followup_push(event, before, head, parent, names)
        or levelup_ui_repair_push(event, before, head, parent, names))


def asset_closure_required(event, before, head, parent, names):
    if render_queue_owned(event, before, head, parent, names): return False
    if setup_copy_owned(event, before, head, parent, names): return False
    if session_repair_owned(event, before, head, parent, names): return False
    if render_pipeline_owned(event, before, head, parent, names): return False
    if gpu_profile_push(event, before, head, parent, names) or gpu_profile_docs(event, before, head, parent, names): return False
    if renderer_attribution_push(event, before, head, parent, names) or renderer_attribution_docs(event, before, head, parent, names): return False
    if sidebar_push(event, before, head, parent, names) or sidebar_docs(event, before, head, parent, names): return False
    if gameplay_performance_push(event, before, head, parent, names) or gameplay_performance_docs(event, before, head, parent, names): return False
    if scene_performance_push(event, before, head, parent, names) or scene_performance_docs(event, before, head, parent, names): return False
    if performance_push(event, before, head, parent, names): return False
    return not (client_startup_followup_push(event, before, head, parent, names)
        or levelup_ui_repair_push(event, before, head, parent, names))


def startup_followup_required(event, before, head, parent, names):
    if render_queue_owned(event, before, head, parent, names): return False
    if setup_copy_owned(event, before, head, parent, names): return False
    if session_repair_owned(event, before, head, parent, names): return False
    if render_pipeline_owned(event, before, head, parent, names): return False
    if gpu_profile_push(event, before, head, parent, names) or gpu_profile_docs(event, before, head, parent, names): return False
    if renderer_attribution_push(event, before, head, parent, names) or renderer_attribution_docs(event, before, head, parent, names): return False
    if sidebar_push(event, before, head, parent, names) or sidebar_docs(event, before, head, parent, names): return False
    if gameplay_performance_push(event, before, head, parent, names) or gameplay_performance_docs(event, before, head, parent, names): return False
    if scene_performance_push(event, before, head, parent, names) or scene_performance_docs(event, before, head, parent, names): return False
    if performance_push(event, before, head, parent, names): return False
    return not levelup_ui_repair_push(event, before, head, parent, names)


def levelup_ui_repair_required(event, before, head, parent, names):
    if render_queue_owned(event, before, head, parent, names): return False
    if setup_copy_owned(event, before, head, parent, names): return False
    if session_repair_owned(event, before, head, parent, names): return False
    if render_pipeline_owned(event, before, head, parent, names): return False
    if gpu_profile_push(event, before, head, parent, names) or gpu_profile_docs(event, before, head, parent, names): return False
    if renderer_attribution_push(event, before, head, parent, names) or renderer_attribution_docs(event, before, head, parent, names): return False
    if sidebar_push(event, before, head, parent, names) or sidebar_docs(event, before, head, parent, names): return False
    if gameplay_performance_push(event, before, head, parent, names) or gameplay_performance_docs(event, before, head, parent, names): return False
    if scene_performance_push(event, before, head, parent, names) or scene_performance_docs(event, before, head, parent, names): return False
    if performance_push(event, before, head, parent, names): return False
    # Source candidates always qualify; an exact publication checkpoint is docs only.
    return not (levelup_ui_repair_docs(event, before, head, parent, names)
        or reopen_startup_repair_push(event, before, head, parent, names)
        or ui_beacon_push(event, before, head, parent, names))


def main():
    required = True
    cleanup = True
    recovery = True
    receipt = True
    schedule = True
    setup = True
    bundle = True
    visual = True
    loading = True
    streaming = True
    asset_closure = True
    startup_followup = True
    levelup_ui_repair = True
    reopen_startup_repair = True
    ui_beacon = True
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
        receipt = receipt_required(os.environ.get('GITHUB_EVENT_NAME'),
            os.environ.get('COH_PUSH_BEFORE'), head, parent, names)
        schedule = schedule_required(os.environ.get('GITHUB_EVENT_NAME'),
            os.environ.get('COH_PUSH_BEFORE'), head, parent, names)
        setup = setup_required(os.environ.get('GITHUB_EVENT_NAME'),
            os.environ.get('COH_PUSH_BEFORE'), head, parent, names)
        bundle = bundle_required(os.environ.get('GITHUB_EVENT_NAME'),
            os.environ.get('COH_PUSH_BEFORE'), head, parent, names)
        visual = visual_required(os.environ.get('GITHUB_EVENT_NAME'),
            os.environ.get('COH_PUSH_BEFORE'), head, parent, names)
        loading = loading_required(os.environ.get('GITHUB_EVENT_NAME'),
            os.environ.get('COH_PUSH_BEFORE'), head, parent, names)
        streaming = streaming_required(os.environ.get('GITHUB_EVENT_NAME'),
            os.environ.get('COH_PUSH_BEFORE'), head, parent, names)
        asset_closure = asset_closure_required(os.environ.get('GITHUB_EVENT_NAME'),
            os.environ.get('COH_PUSH_BEFORE'), head, parent, names)
        levelup_ui_repair = levelup_ui_repair_required(os.environ.get('GITHUB_EVENT_NAME'),
            os.environ.get('COH_PUSH_BEFORE'), head, parent, names)
        reopen_startup_repair = reopen_startup_repair_required(os.environ.get('GITHUB_EVENT_NAME'),
            os.environ.get('COH_PUSH_BEFORE'), head, parent, names)
        ui_beacon = ui_beacon_required(os.environ.get('GITHUB_EVENT_NAME'),
            os.environ.get('COH_PUSH_BEFORE'), head, parent, names)
        startup_followup = startup_followup_required(os.environ.get('GITHUB_EVENT_NAME'),
            os.environ.get('COH_PUSH_BEFORE'), head, parent, names)
    except (OSError, subprocess.CalledProcessError, UnicodeError):
        pass
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as output:
        output.write('task_required='+str(required).lower()+'\n')
        output.write('cleanup_required='+str(cleanup).lower()+'\n')
        output.write('recovery_required='+str(recovery).lower()+'\n')
        output.write('receipt_required='+str(receipt).lower()+'\n')
        output.write('schedule_required='+str(schedule).lower()+'\n')
        output.write('setup_required='+str(setup).lower()+'\n')
        output.write('bundle_required='+str(bundle).lower()+'\n')
        output.write('visual_required='+str(visual).lower()+'\n')
        output.write('loading_required='+str(loading).lower()+'\n')
        output.write('streaming_required='+str(streaming).lower()+'\n')
        output.write('asset_closure_required='+str(asset_closure).lower()+'\n')
        output.write('startup_followup_required='+str(startup_followup).lower()+'\n')
        output.write('levelup_ui_repair_required='+str(levelup_ui_repair).lower()+'\n')
        output.write('reopen_startup_repair_required='+str(reopen_startup_repair).lower()+'\n')
        output.write('ui_beacon_required='+str(ui_beacon).lower()+'\n')
    print('Retained Android storage workflow owns this update' if not required
          else 'Task and native animation workflow required')


if __name__ == '__main__':
    main()
