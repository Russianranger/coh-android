#!/usr/bin/env python3
"""Finite .36 guest startup/progression owner; native and assets remain .35 bytes.
Unknown paths and ambiguous ancestry retain every historical gate.
"""
import re

CLIENT_STARTUP_LATENCY_MARKER = 'tools/android/interactive/release-client-startup-latency-0.13.36.json'
CLIENT_STARTUP_LATENCY_PUBLICATION = 'docs/android-evidence/client-startup-latency-0.13.36-publication.json'
CLIENT_STARTUP_LATENCY_DOCS = frozenset({
    'docs/COH-Atlas-Gameplay-0.13.36-testing.txt',
    'docs/COH-NATIVE-STARTUP-RESEARCH-0.13.36.md',
    'docs/COH-PHYSICAL-STARTUP-0.13.35.md',
    'docs/COH-STARTUP-LATENCY-0.13.36.md',
    'docs/HANDOFF.md',
    'docs/android-evidence/client-startup-latency-0.13.36-host-tests.json',
    'docs/android-evidence/client-startup-latency-0.13.36-publication.json',
    'docs/android-evidence/client-startup-latency-0.13.36-routing.json',
    'docs/android-evidence/coh-physical-startup-0.13.35-analysis.json',
})
CLIENT_STARTUP_LATENCY_ALLOWED = CLIENT_STARTUP_LATENCY_DOCS | frozenset({
    '.github/workflows/android-client-startup-latency.yml',
    '.github/workflows/android-native-startup-profile.yml',
    'android/guest/atlas_beacon_package.py',
    'android/guest/character_creation_diagnostic.py',
    'android/guest/character_server_data_cache.py',
    'android/guest/character_zoning.py',
    'android/guest/client_gpu_profile.py',
    'android/guest/kings_row_beacon_package.py',
    'android/guest/local_character_server.py',
    'android/guest/task_gate_evidence.py',
    'android/native/client-launcher.c',
    'database/native-startup-profile/overlay/coh_native_cg_profile.h',
    'tools/android/interactive/build_client_startup_latency_apk.py',
    'tools/android/interactive/classify_client_animation_repair_change.py',
    'tools/android/interactive/classify_client_map_startup_change.py',
    'tools/android/interactive/classify_client_profile_recovery_change.py',
    'tools/android/interactive/classify_client_startup_latency_change.py',
    'tools/android/interactive/fixtures/minimal-db-native-inputs-0.13.34.json',
    'tools/android/interactive/fixtures/thor-save-lifecycle-0.13.35-20261013.json',
    'tools/android/interactive/manual_launcher_contract.py',
    'tools/android/interactive/package_manual_launcher.py',
    'tools/android/interactive/qualify_client_startup_latency.py',
    'tools/android/interactive/qualify_manual_launcher_windows.py',
    'tools/android/interactive/qualify_minimal_db_runtime.py',
    'tools/android/interactive/qualify_saved_map_preparation.py',
    'tools/android/interactive/qualify_startup_latency_preparation.py',
    'tools/android/interactive/release-client-startup-latency-0.13.36.json',
    'tools/android/interactive/test_character_map_data.py',
    'tools/android/interactive/test_character_monorail.py',
    'tools/android/interactive/test_character_reopen_guest.py',
    'tools/android/interactive/test_character_zoning.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/test_client_gpu_profile.py',
    'tools/android/interactive/test_client_preload_launch.py',
    'tools/android/interactive/test_client_startup_latency_package.py',
    'tools/android/interactive/test_manual_launcher_contract.py',
    'tools/android/interactive/test_minimal_db_runtime_contract.py',
    'tools/android/interactive/test_saved_gameplay_lifecycle.py',
    'tools/android/interactive/test_saved_map_preparation.py',
    'tools/android/interactive/test_saved_map_preparation_proof.py',
    'tools/android/interactive/test_saved_map_startup.py',
    'tools/android/interactive/test_saved_map_postgresql.py',
    'tools/android/interactive/test_shared_collision_input_proof.py',
    'tools/android/interactive/test_startup_latency_preparation_proof.py',
    'tools/package_native_startup_profile.py',
    'tools/prepare_native_cg_profile_source.py',
    'tools/qualify_native_startup_profile.py',
    'tools/test_native_cg_profile_source.py',
    'tools/test_qualify_native_startup_profile.py',
})

def client_startup_latency_owned(event, before, head, parent, names):
    paths = set(names)
    direct = (event == "push" and re.fullmatch("[0-9a-f]{40}", before or "")
        and re.fullmatch("[0-9a-f]{40}", head or "")
        and re.fullmatch("[0-9a-f]{40}", parent or "")
        and before != "0"*40 and head != "0"*40
        and before == parent and head != before and bool(paths)
        and all(type(name) is str for name in paths))
    return bool(direct and ((paths <= CLIENT_STARTUP_LATENCY_ALLOWED
        and CLIENT_STARTUP_LATENCY_MARKER in paths)
        or (paths <= CLIENT_STARTUP_LATENCY_DOCS and CLIENT_STARTUP_LATENCY_PUBLICATION in paths)))
