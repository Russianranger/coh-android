#!/usr/bin/env python3
"""Own the exact .35 manual/text/startup and native-launcher qualification scope without rebuilding retained native payloads.

An explicit successor marker and direct single-parent push are mandatory.
Unknown files and ambiguous ancestry continue through every historical gate.
"""
import os
from pathlib import Path
import re
import subprocess

CLIENT_MANUAL_SESSION_MARKER = 'tools/android/interactive/release-client-manual-session-0.13.35.json'
CLIENT_MANUAL_SESSION_PUBLICATION = 'docs/android-evidence/client-manual-session-0.13.35-publication.json'
CLIENT_MANUAL_SESSION_DOCS = frozenset({
    'docs/COH-Atlas-Gameplay-0.13.35-testing.txt',
    'docs/COH-CLIENT-PREPARATION-0.13.35.md',
    'docs/COH-NATIVE-STARTUP-RESEARCH-0.13.35.md',
    'docs/COH-PHYSICAL-STARTUP-0.13.34.md',
    'docs/COH-SAVED-KINGS-STARTUP-0.13.35.md',
    'docs/HANDOFF.md',
    'docs/android-evidence/client-manual-session-0.13.35-publication.json',
    'docs/android-evidence/client-manual-session-0.13.35-routing.json',
    'docs/android-evidence/client-preparation-0.13.35-host-metadata.json',
    'docs/android-evidence/client-preparation-0.13.35-host-tests.json',
    'docs/android-evidence/coh-physical-startup-0.13.34-analysis.json',
    'docs/android-evidence/saved-kings-startup-0.13.35-host-tests.json',
})
CLIENT_MANUAL_SESSION_ALLOWED = CLIENT_MANUAL_SESSION_DOCS | frozenset({
    '.github/workflows/android-client-manual-session.yml',
    'android/app/src/main/java/io/github/russianranger/cohdiagnostic/SetupMemoryGuard.java',
    'android/guest/atlas_world_assets.py',
    'android/guest/character_creation_diagnostic.py',
    'android/guest/character_reopen_diagnostic.py',
    'android/guest/character_server_data_cache.py',
    'android/guest/character_session_budget.py',
    'android/guest/character_zoning.py',
    'android/guest/client_animation_package.py',
    'android/guest/client_gpu_profile.py',
    'android/guest/client_interactive_diagnostic.py',
    'android/guest/client_visual_assets.py',
    'android/guest/game_device_diagnostic.py',
    'android/guest/local_character_server.py',
    'android/guest/server_fx_catalog.py',
    'android/guest/texture_header_index.py',
    'android/guest/zone_asset_package.py',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientAcceptance.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientActivity.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientRuntime.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientService.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientSessionBudget.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/InteractiveRfbClient.java',
    'android/native/client-launcher.c',
    'database/native-startup-profile/overlay/coh_native_startup_profile.h',
    'docs/COH-Atlas-Gameplay-0.13.35-testing.txt',
    'tools/android/atlasgame/test_device_cleanup_lineage.py',
    'tools/android/interactive/build_client_manual_session_apk.py',
    'tools/android/interactive/classify_client_animation_repair_change.py',
    'tools/android/interactive/classify_client_manual_session_change.py',
    'tools/android/interactive/classify_client_map_startup_change.py',
    'tools/android/interactive/classify_client_profile_recovery_change.py',
    'tools/android/interactive/fixtures/minimal-db-native-inputs-0.13.34.json',
    'tools/android/interactive/generate_atlas_beacons.py',
    'tools/android/interactive/manual_launcher_contract.py',
    'tools/android/interactive/package_manual_launcher.py',
    'tools/android/interactive/qualify_client_manual_session.py',
    'tools/android/interactive/qualify_manual_launcher_windows.py',
    'tools/android/interactive/qualify_minimal_db_runtime.py',
    'tools/android/interactive/qualify_saved_map_preparation.py',
    'tools/android/interactive/release-client-manual-session-0.13.35.json',
    'tools/android/interactive/test_animation_runtime_compatibility.py',
    'tools/android/interactive/test_atlas_world_assets.py',
    'tools/android/interactive/test_character_monorail.py',
    'tools/android/interactive/test_character_profile_eligibility.py',
    'tools/android/interactive/test_character_reopen_guest.py',
    'tools/android/interactive/test_character_zoning.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/test_client_animation_package.py',
    'tools/android/interactive/test_client_gpu_profile.py',
    'tools/android/interactive/test_client_manual_session_package.py',
    'tools/android/interactive/test_client_preload_launch.py',
    'tools/android/interactive/test_client_report_controls_java.py',
    'tools/android/interactive/test_client_report_lifecycle_java.py',
    'tools/android/interactive/test_client_report_recovery_java.py',
    'tools/android/interactive/test_client_sidebar_commands.py',
    'tools/android/interactive/test_client_text_entry.py',
    'tools/android/interactive/test_client_visual_assets.py',
    'tools/android/interactive/test_client_visual_schedule.py',
    'tools/android/interactive/test_client_zoning_java.py',
    'tools/android/interactive/test_completed_guest_report_java.py',
    'tools/android/interactive/test_collision_input_snapshot.py',
    'tools/android/interactive/test_full_startup_preflight.py',
    'tools/android/interactive/test_input.py',
    'tools/android/interactive/test_login_guest.py',
    'tools/android/interactive/test_manual_launcher_contract.py',
    'tools/android/interactive/test_manual_session.py',
    'tools/android/interactive/test_minimal_db_runtime_contract.py',
    'tools/android/interactive/test_saved_map_preparation.py',
    'tools/android/interactive/test_saved_map_preparation_proof.py',
    'tools/android/interactive/test_session_budget_guest.py',
    'tools/android/interactive/test_session_budget_java.py',
    'tools/android/interactive/test_task_receipt_cleanup.py',
    'tools/android/interactive/test_texture_header_index.py',
    'tools/android/interactive/test_zone_asset_package.py',
    'tools/android/test_setup_memory_guard.py',
    'tools/prepare_native_startup_profile_source.py',
    'tools/test_native_startup_profile_source.py',
})

def client_manual_session_owned(event, before, head, parent, names):
    paths = set(names)
    direct = (event == 'push' and re.fullmatch('[0-9a-f]{40}', before or '')
        and re.fullmatch('[0-9a-f]{40}', head or '')
        and re.fullmatch('[0-9a-f]{40}', parent or '')
        and before != '0'*40 and head != '0'*40
        and before == parent and head != before and bool(paths)
        and all(type(name) is str for name in paths))
    return bool(direct and ((paths <= CLIENT_MANUAL_SESSION_ALLOWED
        and CLIENT_MANUAL_SESSION_MARKER in paths)
        or (paths <= CLIENT_MANUAL_SESSION_DOCS and CLIENT_MANUAL_SESSION_PUBLICATION in paths)))
