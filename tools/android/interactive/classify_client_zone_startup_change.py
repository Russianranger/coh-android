#!/usr/bin/env python3
"""Finite direct-parent .37 owner. Unknown scope retains historical gates."""
import re

CLIENT_ZONE_STARTUP_MARKER = 'tools/android/interactive/release-client-zone-startup-0.13.37.json'
CLIENT_ZONE_STARTUP_PUBLICATION = 'docs/android-evidence/client-zone-startup-0.13.37-publication.json'
CLIENT_ZONE_STARTUP_DOCS = frozenset({
    'docs/COH-Atlas-Gameplay-0.13.37-testing.txt',
    'docs/COH-STARTUP-0.13.37-PACKAGING-PLAN.md',
    'docs/COH-STARTUP-LATENCY-0.13.37.md',
    'docs/HANDOFF.md',
    'docs/android-evidence/client-zone-startup-0.13.37-host-tests.json',
    'docs/android-evidence/client-zone-startup-0.13.37-publication.json',
    'docs/android-evidence/coh-physical-startup-0.13.36-analysis.json',
    'docs/android-evidence/manual-report-cleanup-0.13.37-qualification.json',
    'docs/COH-CLIENT-STARTUP-PRIORITY-0.13.37.md',
    'docs/android-evidence/client-startup-priority-investigation-0.13.37.json',
    'docs/android-evidence/native-startup-metadata-0.13.37-dormant-review.json',
    'docs/android-evidence/native-map-metadata-source-boundary-0.13.37.json',
    'docs/android-evidence/native-map-world-console-failure-0.13.37.json',
    'docs/android-evidence/native-client-folder-sort-0.13.37-qualification.json',
    'docs/android-evidence/native-map-world-buffering-failure-0.13.37.json',
    'docs/android-evidence/original-cache-components-0.13.37-recovery.json',
    'docs/android-evidence/native-map-world-bounds-failure-0.13.37.json',
    'docs/android-evidence/native-client-metadata-census-0.13.37-prototype.json',
    'docs/android-evidence/native-metadata-adapter-0.13.37-source-checkpoint.json',
    'docs/android-evidence/native-client-metadata-adapter-0.13.37-review.json',
    'docs/android-evidence/native-client-material-reader-0.13.37-review.json',
    'docs/android-evidence/native-map-metadata-adapter-0.13.37-review.json',
    'docs/android-evidence/native-map-metadata-adapter-0.13.37-host-tests.json',
    'docs/android-evidence/native-cache-normalizer-0.13.37-review.json',
    'docs/android-evidence/native-startup-material-facts-0.13.37.json',
    'docs/android-evidence/native-map-cache-subset-0.13.37-research.json',
    'docs/android-evidence/native-metadata-adapter-0.13.37-root-integration.json',
})
CLIENT_ZONE_STARTUP_ALLOWED = CLIENT_ZONE_STARTUP_DOCS | frozenset({
    '.github/workflows/android-map-startup-native.yml',
    'tools/android/interactive/classify_map_startup_native_change.py',
    'tools/android/interactive/test_map_startup_native_change.py',
    '.github/workflows/android-client-zone-startup.yml',
    'android/guest/game_device_diagnostic.py',
    'android/guest/client_startup_diagnostic.py',
    'android/guest/client_interactive_diagnostic.py',
    'android/guest/client_gpu_profile.py',
    'android/guest/texture_header_index.py',
    'android/guest/native_map_startup_contract.py',
    'android/guest/local_character_server.py',
    'android/guest/server_cache_package.py',
    'android/guest/server_animation_package.py',
    'android/guest/atlas_beacon_package.py',
    'android/guest/character_zoning.py',
    'android/guest/game_diagnostic.py',
    'android/guest/server_fx_catalog.py',

    'android/guest/native_startup_metadata_contract.py',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientAcceptance.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientRuntime.java',
    'tools/android/atlasgame/test_device_cleanup_lineage.py',
    'tools/android/interactive/build_client_zone_startup_apk.py',
    'tools/android/interactive/classify_client_animation_repair_change.py',
    'tools/android/interactive/classify_client_map_startup_change.py',
    'tools/android/interactive/classify_client_profile_recovery_change.py',
    'tools/android/interactive/classify_client_zone_startup_change.py',
    'tools/android/interactive/fixtures/thor-manual-report-0.13.36-20261013.json',
    'tools/android/interactive/native_startup_metadata_admission.py',
    'tools/android/interactive/native_startup_component_migration.py',
    'tools/android/interactive/qualify_client_zone_startup.py',
    'tools/android/interactive/release-client-zone-startup-0.13.37.json',
    'tools/android/interactive/test_client_zone_startup_package.py',
    'tools/android/interactive/test_manual_report_acceptance.py',
    'tools/android/interactive/test_native_startup_metadata_admission.py',
    'tools/android/interactive/test_native_startup_metadata_contract.py',
    'tools/android/interactive/test_native_startup_component_migration.py',
    'tools/android/interactive/test_native_metadata_runtime_activation.py',
    'tools/android/interactive/test_native_metadata_map_activation.py',
    'tools/android/interactive/derive_native_metadata_cache_proof.py',
    'tools/android/interactive/test_derive_native_metadata_cache_proof.py',
})


def client_zone_startup_owned(event, before, head, parent, names):
    if not isinstance(names, (list, tuple, set, frozenset)) or not names:
        return False
    if any(type(name) is not str or not name or name.startswith('/')
        or '..' in name.split('/') or '\\' in name for name in names):
        return False
    paths = set(names)
    direct = (event == 'push' and all(type(value) is str
        and re.fullmatch('[0-9a-f]{40}', value) for value in (before, head, parent))
        and before != '0'*40 and head != '0'*40 and before == parent and head != before)
    return bool(direct and ((paths <= CLIENT_ZONE_STARTUP_ALLOWED
        and CLIENT_ZONE_STARTUP_MARKER in paths)
        or (paths <= CLIENT_ZONE_STARTUP_DOCS and CLIENT_ZONE_STARTUP_PUBLICATION in paths)))
